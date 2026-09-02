"""Tests for `ambo.common.db` (T-204, plan 03-07).

Implements: AD-030

All tests read the warehouse built by the phase's own `make transform`. No test in
this file skips when the warehouse is absent -- absence produces a `DataContractError`
failure naming the transform command, per D-20's "no test in this file skips" rule. A
skipped contract test would be a silent pass.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import duckdb
import pandas as pd
import pytest

from ambo.common import db
from ambo.common.config import load_settings
from ambo.common.db import (
    _contract_columns,
    connect,
    read_dim_layer,
    read_mmm_input,
    read_platform_reported,
)
from ambo.common.errors import DataContractError

# The three Layer P layers and their producing scenario directories -- read here
# independently of both the mart and the dbt singular test's own CSV read, so the
# round trip is genuine rather than a restatement of a literal (03-RESEARCH.md
# Pattern 4's precedent, matching test_warehouse_build.py's own reasoning).
_LAYER_TO_SCENARIO_DIR: dict[str, str] = {"P-SA": "s_a", "P-SB": "s_b", "P-SC": "s_c"}
_EXPECTED_ROW_COUNTS: dict[str, int] = {"P-SA": 156, "P-SB": 104, "P-SC": 78}


# --- Round-trip tests ---------------------------------------------------------------


@pytest.mark.parametrize("layer", ["P-SA", "P-SB", "P-SC"])
def test_read_mmm_input_totals_match_simulator_csvs(layer: str, repo_root: Path) -> None:
    """The WBS T-204 round-trip: per-layer revenue totals equal the sum of
    `revenue_eur` in the corresponding committed `outcome_weekly.csv`, computed at
    test time from the CSV rather than hard-coded, so this is a genuine round trip."""
    scenario_dir = _LAYER_TO_SCENARIO_DIR[layer]
    csv_path = repo_root / "data" / "synthetic" / scenario_dir / "outcome_weekly.csv"
    expected_sum = pd.read_csv(csv_path)["revenue_eur"].sum()

    frame = read_mmm_input(layer)
    actual_sum = frame["revenue"].sum()

    assert abs(actual_sum - expected_sum) <= 1e-6, (
        f"layer={layer!r}: mart revenue sum {actual_sum} does not match the CSV-computed "
        f"sum {expected_sum} within 1e-6 (delta={abs(actual_sum - expected_sum)})"
    )


@pytest.mark.parametrize(("layer", "expected_rows"), sorted(_EXPECTED_ROW_COUNTS.items()))
def test_read_mmm_input_shape_and_order(layer: str, expected_rows: int) -> None:
    """156 / 104 / 78 row counts, the seventeen-column order derived from the yml,
    strict `week_start` ascent, and the uniform seven-day step."""
    frame = read_mmm_input(layer)

    assert len(frame) == expected_rows, (
        f"layer={layer!r}: expected {expected_rows} rows, got {len(frame)}"
    )

    expected_columns = [name for name, _ in _contract_columns("fct_mmm_input")]
    assert len(expected_columns) == 17, f"expected 17 contract columns, got {len(expected_columns)}"
    assert list(frame.columns) == expected_columns

    assert frame["week_start"].is_monotonic_increasing
    gaps = pd.to_datetime(frame["week_start"]).diff().dropna()
    assert set(gaps.unique()) == {pd.Timedelta(days=7)}, (
        f"layer={layer!r}: non-seven-day gap(s) present in week_start sequence"
    )


def test_read_platform_reported_preserves_offline_nulls() -> None:
    """`print_regional` rows retain NULL `platform_conversions`; no such value is
    coerced to zero."""
    frame = read_platform_reported("P-SA")
    offline = frame[frame["channel"] == "print_regional"]

    assert not offline.empty, "no print_regional rows returned for P-SA"
    assert offline["platform_conversions"].isna().all(), (
        "print_regional platform_conversions is not NULL on every row"
    )
    assert not (offline["platform_conversions"].fillna(-1) == 0).any(), (
        "a print_regional platform_conversions value was coerced to 0 instead of staying NULL"
    )


def test_read_dim_layer_shape() -> None:
    """Three rows, five columns, and the taxonomy-ordered `channels_present` string
    (all six non-`other` channels present for every Layer P layer)."""
    frame = read_dim_layer()

    assert frame.shape == (3, 5), f"expected (3, 5), got {frame.shape}"

    expected_columns = [name for name, _ in _contract_columns("dim_layer")]
    assert len(expected_columns) == 5
    assert list(frame.columns) == expected_columns

    expected_channels_present = ",".join(load_settings().channels[:6])
    by_layer = frame.set_index("layer")["channels_present"]
    for layer in ("P-SA", "P-SB", "P-SC"):
        assert by_layer[layer] == expected_channels_present, (
            f"layer={layer!r}: channels_present {by_layer[layer]!r} does not equal "
            f"the taxonomy-ordered six-channel string {expected_channels_present!r}"
        )


# --- Failure-mode tests ---------------------------------------------------------------


def test_missing_warehouse_raises_with_transform_instruction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing warehouse file raises `DataContractError` naming the `make
    transform` command, rather than a raw duckdb IO error or a connection."""
    fake_settings = SimpleNamespace(paths=SimpleNamespace(warehouse=tmp_path / "missing.duckdb"))
    monkeypatch.setattr(db, "load_settings", lambda: fake_settings)

    with pytest.raises(DataContractError, match="make transform"):
        connect()


def test_unknown_layer_lists_valid_layers() -> None:
    """An unknown layer argument raises `DataContractError` enumerating the three
    valid Layer P layers, rather than returning an empty frame."""
    with pytest.raises(DataContractError) as exc_info:
        read_mmm_input("does-not-exist")

    message = str(exc_info.value)
    for layer in ("P-SA", "P-SB", "P-SC"):
        assert layer in message, f"valid layer {layer!r} missing from error message: {message}"


def test_read_only_connection_rejects_a_write() -> None:
    """A write statement issued through the default connection raises, and the
    warehouse content is unchanged afterward (the ASVS V4 access-control proof,
    T-204 AC-3)."""
    con = connect()
    try:
        with pytest.raises(duckdb.Error):
            con.execute(
                "insert into dim_layer values ('__test_write_probe__', 1, '', 'EUR', "
                "'GROUND-TRUTH')"
            )
    finally:
        con.close()

    verify_con = connect()
    try:
        count = verify_con.execute(
            "select count(*) from dim_layer where layer = '__test_write_probe__'"
        ).fetchone()[0]
    finally:
        verify_con.close()

    assert count == 0, "a write through the default read-only connection mutated the warehouse"


class _FakeResult:
    """A minimal stand-in for duckdb's cursor/result object, returning either a
    canned row list (`.fetchall()`) or a canned frame (`.df()`), enough to drive
    `read_mmm_input`'s real validation logic against a synthetic frame without
    touching the real warehouse."""

    def __init__(
        self, rows: list[tuple[str]] | None = None, frame: pd.DataFrame | None = None
    ) -> None:
        self._rows = rows
        self._frame = frame

    def fetchall(self) -> list[tuple[str]]:
        assert self._rows is not None
        return self._rows

    def df(self) -> pd.DataFrame:
        assert self._frame is not None
        return self._frame


class _FakeConnection:
    """Answers the two queries `read_mmm_input` issues: the `dim_layer` distinct-
    layer lookup (real valid layers, so the unknown-layer check passes) and the
    `fct_mmm_input` select (the poisoned frame under test)."""

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame
        self.closed = False

    def execute(self, sql: str, params: list[str] | None = None) -> _FakeResult:
        if "distinct layer" in sql:
            return _FakeResult(rows=[("P-SA",), ("P-SB",), ("P-SC",)])
        return _FakeResult(frame=self._frame)

    def close(self) -> None:
        self.closed = True


def test_all_postcondition_violations_are_reported_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A frame injected with two simultaneous violations (a non-ascending week and a
    NaN in a spend column) produces one raised `DataContractError` whose message
    contains both violation descriptions -- D-10's proof, not two separate raises
    and not only the first."""
    poisoned = read_mmm_input("P-SA").copy()
    poisoned.loc[0, "week_start"], poisoned.loc[1, "week_start"] = (
        poisoned.loc[1, "week_start"],
        poisoned.loc[0, "week_start"],
    )
    poisoned.loc[2, "spend_meta"] = float("nan")

    monkeypatch.setattr(db, "connect", lambda read_only=True: _FakeConnection(poisoned))

    with pytest.raises(DataContractError) as exc_info:
        db.read_mmm_input("P-SA")

    message = str(exc_info.value)
    assert "not strictly increasing" in message, (
        f"non-ascending week_start violation missing from message: {message}"
    )
    assert "spend_meta" in message, f"NaN spend-column violation missing from message: {message}"
