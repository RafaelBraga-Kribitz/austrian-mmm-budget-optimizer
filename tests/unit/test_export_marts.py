"""Tests for `scripts/export_marts.py` (T-205, plan 03-08).

Implements: REQ-dl1-reproducible-pipeline, REQ-grain-and-windows

AD-050's contract test for the one implemented file, `mmm_input_weekly.csv`: the
registry shape (so a Phase 8 addition that omits a required field fails
immediately), the committed export's exact match against the mart contract, the
negative-side duplicate-grain-key proof, the six-decimal float format, the LF-only
byte precondition, and byte-identical regeneration (D-02's local half; plan 03-09
adds the CI half).

No test in this file skips when the committed export or the warehouse is absent --
absence is a real failure (an assertion error or a `DataContractError` naming the
`make transform`/`make export` command), matching `test_db.py`'s D-20 "no skip" rule.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

from ambo.common.db import _contract_columns
from ambo.common.errors import DataContractError

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import export_marts  # noqa: E402

_EXPORT_PATH = _REPO_ROOT / "exports" / "mmm_input_weekly.csv"
_EXPECTED_DATA_ROWS = 338
_LAYER_P_VALUES = {"P-SA", "P-SB", "P-SC"}
_WEEK_START_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SIX_DECIMAL_RE = re.compile(r"^-?\d+\.\d{6}$")


# --- Registry shape -------------------------------------------------------------


def test_export_registry_shape() -> None:
    registry = export_marts.EXPORT_REGISTRY
    assert isinstance(registry, dict), "EXPORT_REGISTRY must be a dict (D-03)."
    assert registry, (
        "EXPORT_REGISTRY is empty -- this means the test is broken, not that the "
        "registry vacuously passes: it must carry at least the mmm_input_weekly.csv "
        "entry this phase adds."
    )

    for name, spec in registry.items():
        assert name.endswith(".csv"), f"registry key {name!r} does not end in .csv"
        assert callable(spec.reader), f"{name}: reader must be callable"
        assert callable(spec.columns), (
            f"{name}: columns (the ordered column list source) must be callable"
        )
        assert isinstance(spec.dtype_casts, dict), f"{name}: dtype_casts must be a dict"
        assert isinstance(spec.sort_keys, list) and spec.sort_keys, (
            f"{name}: sort_keys must be a non-empty list"
        )

    print(f"export registry guard: scanned {len(registry)} entr(y/ies), 0 offenders.")


def test_mmm_input_weekly_entry_reads_every_layer_via_read_dim_layer() -> None:
    """No hard-coded layer name list in the registry entry's reader -- it derives
    the layer set from `read_dim_layer()` at call time."""
    frame = export_marts._read_mmm_input_all_layers()
    assert set(frame["layer"].unique()) == _LAYER_P_VALUES


# --- Committed export vs. the mart contract --------------------------------------


def test_committed_export_matches_the_mart_contract() -> None:
    assert _EXPORT_PATH.is_file(), (
        f"{_EXPORT_PATH} is missing -- run `make transform && make export` to "
        "produce and commit it."
    )

    expected_header = [name for name, _ in _contract_columns("fct_mmm_input")]
    lines = _EXPORT_PATH.read_text(encoding="utf-8").splitlines()

    assert lines, "committed export is empty -- the scan itself is broken."
    header = lines[0].split(",")
    assert header == expected_header, f"header mismatch: expected {expected_header}, got {header}"

    data_lines = lines[1:]
    assert len(data_lines) == _EXPECTED_DATA_ROWS, (
        f"expected {_EXPECTED_DATA_ROWS} data rows, found {len(data_lines)}"
    )

    frame = pd.read_csv(_EXPORT_PATH, dtype={"week_start": str, "layer": str})

    bad_week_starts = [w for w in frame["week_start"] if not _WEEK_START_RE.match(w)]
    assert not bad_week_starts, f"week_start value(s) not YYYY-MM-DD: {bad_week_starts}"

    assert set(frame["layer"].unique()) == _LAYER_P_VALUES, (
        f"layer column does not contain exactly the three Layer P values, got "
        f"{sorted(frame['layer'].unique())}"
    )

    sorted_frame = frame.sort_values(by=["layer", "week_start"], kind="mergesort").reset_index(
        drop=True
    )
    pd.testing.assert_frame_equal(frame.reset_index(drop=True), sorted_frame)


# --- AD-050 negative side: duplicate grain key fails, never deduplicates --------


def test_duplicate_grain_key_in_export_fails_the_contract_test() -> None:
    poisoned = pd.DataFrame(
        {
            "week_start": ["2021-01-04", "2021-01-04", "2021-01-11"],
            "layer": ["P-SA", "P-SA", "P-SA"],
            "revenue": [1.0, 2.0, 3.0],
        }
    )

    with pytest.raises(DataContractError, match=r"duplicate grain key"):
        export_marts.validate_no_duplicate_grain_keys(poisoned, ["layer", "week_start"])

    # The negative proof must also name the duplicated key itself, not just report
    # a generic failure.
    with pytest.raises(DataContractError, match=re.escape("P-SA")):
        export_marts.validate_no_duplicate_grain_keys(poisoned, ["layer", "week_start"])


# --- Byte-format preconditions ---------------------------------------------------


def test_float_format_is_fixed_six_decimals() -> None:
    frame = pd.read_csv(_EXPORT_PATH, dtype={"week_start": str, "layer": str})
    float_columns = [c for c in frame.columns if frame[c].dtype == "float64"]
    assert float_columns, "no float-typed column found -- the scan is broken."

    raw_text = _EXPORT_PATH.read_text(encoding="utf-8")
    lines = raw_text.splitlines()
    header = lines[0].split(",")
    float_positions = [header.index(c) for c in float_columns]

    offenders: list[str] = []
    for line in lines[1:]:
        fields = line.split(",")
        for pos in float_positions:
            value = fields[pos]
            if not _SIX_DECIMAL_RE.match(value):
                offenders.append(f"{header[pos]}={value!r}")

    assert not offenders, f"non-six-decimal float value(s) found: {offenders[:10]}"


def test_export_is_lf_only() -> None:
    data = _EXPORT_PATH.read_bytes()
    assert b"\r" not in data, "committed export contains a carriage-return byte"


# --- D-02's local half: byte-identical regeneration ------------------------------


def test_regenerating_the_export_is_byte_identical(tmp_path: Path) -> None:
    outdir_a = tmp_path / "run_a"
    outdir_b = tmp_path / "run_b"
    outdir_a.mkdir()
    outdir_b.mkdir()

    path_a = export_marts.write_export("mmm_input_weekly.csv", outdir_a)
    path_b = export_marts.write_export("mmm_input_weekly.csv", outdir_b)

    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()
    assert bytes_a == bytes_b, "two consecutive regenerations are not byte-identical"

    committed_bytes = _EXPORT_PATH.read_bytes()
    assert bytes_a == committed_bytes, (
        "regenerated export does not match the committed exports/mmm_input_weekly.csv "
        "byte-for-byte -- run `make transform && make export` and commit the result."
    )
