"""The ONLY data doorway for model/decide/report code (AD-030).

Implements: AD-030

`src/ambo/common/db.py` is the single module in `src/ambo/` that opens a duckdb
connection (plan 03-02's mart-only guard test, `tests/unit/test_mart_only_access.py`,
enforces the surrounding half of that rule for `model/`, `decide/` and `report/`).
Four public functions: `connect()`, `read_mmm_input(layer)`,
`read_platform_reported(layer)`, `read_dim_layer()`. Every accessor validates its
returned frame against the mart's own dbt schema yml contract and raises a single
`DataContractError` carrying every violation found, never one violation per run
(D-10) -- Phase 5's VR-310 debug ladder is what actually reads that message, and a
single join bug can trip four assertions at once.

The expected column set for a mart is never restated as a literal list here (D-08):
`_contract_columns()` derives it at runtime from the dbt schema yml files under
`dbt/models/marts/`, the single normative home for the mart column contracts.
"""

from __future__ import annotations

import functools

import duckdb
import pandas as pd
import yaml

from ambo.common.config import load_settings, repo_root
from ambo.common.errors import DataContractError


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Open a connection to the dbt-built warehouse (AD-030).

    Implements: AD-030

    Resolves the warehouse path through `load_settings().paths.warehouse` -- never
    a hard-coded path and never independent path logic, since `config.py` already
    anchors every settings path to `repo_root()`. Raises `DataContractError` naming
    the resolved path's role and the exact command that creates it (`make
    transform`) if the warehouse file does not exist, so the caller's next action is
    unambiguous.

    `read_only=True` is the default and is the access-control mechanism this phase
    depends on: the only write path to the warehouse is `dbt build` itself.
    Passing `read_only=False` is reserved for tooling -- `model`, `decide` and
    `report` code must never do so; plan 03-02's guard test
    (`tests/unit/test_mart_only_access.py`) enforces the surrounding half of that
    rule (that no module outside this one may open duckdb at all).
    """
    warehouse_path = load_settings().paths.warehouse
    if not warehouse_path.is_file():
        raise DataContractError(
            f"connect(): the warehouse file (the dbt build's transform target) is "
            f"missing at {warehouse_path} -- run `make transform` to build it."
        )
    return duckdb.connect(str(warehouse_path), read_only=read_only)


@functools.cache
def _contract_columns(model_name: str) -> tuple[tuple[str, str], ...]:
    """The declared (column name, data type) pairs for a mart, in declared order.

    Parsed with `yaml.safe_load` from the mart schema yml files under
    `dbt/models/marts/`, resolved through `repo_root()`. Scans the directory rather
    than hard-coding one filename per mart, so a later phase adding a new mart does
    not have to touch this function. Cached with `functools.cache`, following
    `load_settings()`'s single-read discipline.

    This function is D-08's mechanism: a mart's column list is never written out as
    a literal list anywhere else in `src/` -- the yml is the single normative home,
    and this function derives from it so a contract change propagates instead of
    drifting.

    Raises `DataContractError` naming the model and the directory searched if the
    named model is absent from every yml -- a missing declaration is a contract
    error, not a `KeyError`.
    """
    marts_dir = repo_root() / "dbt" / "models" / "marts"
    for yml_path in sorted(marts_dir.glob("*.yml")):
        with yml_path.open("r", encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
        if not isinstance(doc, dict):
            continue
        for model in doc.get("models", []):
            if model.get("name") == model_name:
                return tuple((column["name"], column["data_type"]) for column in model["columns"])
    raise DataContractError(
        f"_contract_columns(): model {model_name!r} is not declared in any schema "
        f"yml under {marts_dir}"
    )


def _check_columns(frame: pd.DataFrame, model_name: str) -> list[str]:
    """Human-readable violation strings comparing `frame`'s columns against
    `_contract_columns(model_name)`. Returns rather than raises -- this is what
    makes the collect-all-raise-once behaviour in the public accessors possible."""
    expected = [name for name, _ in _contract_columns(model_name)]
    actual = list(frame.columns)
    if actual != expected:
        return [f"{model_name}: column set/order mismatch -- expected {expected}, got {actual}"]
    return []


def read_mmm_input(layer: str) -> pd.DataFrame:
    """The single model input contract (AD-030) -- grain week x layer.

    Implements: AD-030

    Grain: one row per (week_start, layer). Ordering: `week_start` strictly
    ascending, no ties -- (week_start, layer) is unique in the mart. Postconditions
    (03_MODULES section 1.3), all checked on every call and collected into a single
    `DataContractError` if any fail (D-10): the frame is non-empty; the column names
    and order match `_contract_columns('fct_mmm_input')`; `week_start` is strictly
    increasing; every consecutive `week_start` difference is exactly seven days; no
    spend column contains NaN; `revenue` is strictly greater than zero on every row.

    An unknown `layer` argument raises `DataContractError` listing the valid layers
    read from `dim_layer`, rather than returning an empty frame.
    """
    con = connect(read_only=True)
    try:
        valid_layers = sorted(
            row[0] for row in con.execute("select distinct layer from dim_layer").fetchall()
        )
        if layer not in valid_layers:
            raise DataContractError(
                f"read_mmm_input(): unknown layer {layer!r} -- valid layers are {valid_layers}"
            )
        columns = [name for name, _ in _contract_columns("fct_mmm_input")]
        column_list_sql = ", ".join(columns)
        frame = con.execute(
            f"select {column_list_sql} from fct_mmm_input where layer = ? order by week_start asc",
            [layer],
        ).df()
    finally:
        con.close()

    violations: list[str] = []
    if frame.empty:
        violations.append(f"layer={layer!r}: no rows returned")
    else:
        violations.extend(_check_columns(frame, "fct_mmm_input"))

        week_start = frame["week_start"]
        if not week_start.is_monotonic_increasing:
            bad_positions = [
                i for i in range(1, len(week_start)) if week_start.iloc[i] <= week_start.iloc[i - 1]
            ]
            violations.append(
                f"layer={layer!r}: week_start is not strictly increasing at index "
                f"position(s) {bad_positions}"
            )

        gaps = pd.to_datetime(week_start).diff().dropna()
        bad_gaps = gaps[gaps != pd.Timedelta(days=7)]
        if not bad_gaps.empty:
            bad_weeks = week_start.loc[bad_gaps.index].tolist()
            violations.append(f"layer={layer!r}: non-seven-day gap before week(s) {bad_weeks}")

        spend_cols = [c for c in frame.columns if c.startswith("spend_")]
        nan_spend_cols = [c for c in spend_cols if frame[c].isna().any()]
        if nan_spend_cols:
            violations.append(f"layer={layer!r}: NaN in spend column(s) {nan_spend_cols}")

        if (frame["revenue"] <= 0).any():
            bad_weeks = frame.loc[frame["revenue"] <= 0, "week_start"].tolist()
            violations.append(f"layer={layer!r}: revenue <= 0 at week(s) {bad_weeks}")

    if violations:
        raise DataContractError(
            "read_mmm_input() postcondition violation(s):\n" + "\n".join(violations)
        )
    return frame


def read_platform_reported(layer: str) -> pd.DataFrame:
    """The third contract-enforced mart (D-07) -- grain week x layer x channel.

    Implements: AD-030

    Grain: one row per (week_start, layer, channel). Ordering: `week_start`
    ascending, then `channel` ascending, so the returned order is total and stable
    even though the grain has three keys. Postconditions: the column names and
    order match `_contract_columns('fct_platform_reported')`; the frame is
    non-empty; `week_start`, `layer` and `channel` (the three grain columns) carry
    no NaN. `platform_conversions`, `platform_conv_value` and `impressions` are
    deliberately NOT asserted non-null -- they are legitimately NULL for offline
    channels, and coercing or rejecting them would destroy the distinction plan
    03-06 preserved (AGENTS T-8).

    An unknown `layer` argument raises `DataContractError` listing the valid layers
    read from `dim_layer`, rather than returning an empty frame.
    """
    con = connect(read_only=True)
    try:
        valid_layers = sorted(
            row[0] for row in con.execute("select distinct layer from dim_layer").fetchall()
        )
        if layer not in valid_layers:
            raise DataContractError(
                f"read_platform_reported(): unknown layer {layer!r} -- valid layers "
                f"are {valid_layers}"
            )
        columns = [name for name, _ in _contract_columns("fct_platform_reported")]
        column_list_sql = ", ".join(columns)
        frame = con.execute(
            f"select {column_list_sql} from fct_platform_reported where layer = ? "
            "order by week_start asc, channel asc",
            [layer],
        ).df()
    finally:
        con.close()

    violations: list[str] = []
    if frame.empty:
        violations.append(f"layer={layer!r}: no rows returned")
    else:
        violations.extend(_check_columns(frame, "fct_platform_reported"))
        for grain_col in ("week_start", "layer", "channel"):
            if frame[grain_col].isna().any():
                violations.append(f"layer={layer!r}: NaN in grain column {grain_col!r}")

    if violations:
        raise DataContractError(
            "read_platform_reported() postcondition violation(s):\n" + "\n".join(violations)
        )
    return frame


def read_dim_layer() -> pd.DataFrame:
    """The layer-grain dimension (D-07, SPEC-03 section 3).

    Implements: AD-030

    Grain: one row per layer. Ordering: `layer` ascending. Takes no layer argument.
    Postconditions: the column names and order match
    `_contract_columns('dim_layer')`; the frame is non-empty.
    """
    con = connect(read_only=True)
    try:
        columns = [name for name, _ in _contract_columns("dim_layer")]
        column_list_sql = ", ".join(columns)
        frame = con.execute(f"select {column_list_sql} from dim_layer order by layer asc").df()
    finally:
        con.close()

    violations: list[str] = []
    violations.extend(_check_columns(frame, "dim_layer"))
    if frame.empty:
        violations.append("dim_layer: no rows returned")

    if violations:
        raise DataContractError(
            "read_dim_layer() postcondition violation(s):\n" + "\n".join(violations)
        )
    return frame
