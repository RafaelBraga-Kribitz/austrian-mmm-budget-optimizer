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
