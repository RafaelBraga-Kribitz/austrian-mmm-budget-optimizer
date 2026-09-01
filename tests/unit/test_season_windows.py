"""Tests for the committed Austrian season-window seed (T-011, AD-020).

Implements: REQ-dl8-quality

One test function per window rule, so a failure names the rule that broke, plus a
coverage test, a literal 2022 spot-value test, and an idempotence test. The per-rule
assertions (except the 2022 spot values) recompute the expected ISO-week keys with their
own date arithmetic rather than importing `advent_weeks`/`schulbeginn_weeks` from the
generator, so a regression in the generator's own logic is still caught. The 2022
spot-value test goes further: it asserts against literal expected values with no
computation at all, so it cannot pass by re-running the generator's logic under another
name.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_SEED_PATH = _REPO_ROOT / "dbt" / "seeds" / "season_windows.csv"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import generate_season_windows as gsw  # noqa: E402

EXPECTED_ISO_YEARS = list(range(2019, 2028))


def _read_seed_rows() -> list[dict[str, str]]:
    with _SEED_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _rows_by_year(rows: list[dict[str, str]]) -> dict[int, list[dict[str, str]]]:
    by_year: dict[int, list[dict[str, str]]] = {year: [] for year in EXPECTED_ISO_YEARS}
    for row in rows:
        by_year[int(row["iso_year"])].append(row)
    return by_year


def _expected_advent_keys(year: int) -> set[tuple[int, int]]:
    """Independent recomputation of the D-07 advent reading: 4 weeks ending at, and
    including, the ISO week containing Dec 24 (SPEC-01 section 2.1, Guide section 1.2)."""
    dec24_monday = date(year, 12, 24)
    dec24_monday -= timedelta(days=dec24_monday.weekday())
    return {(dec24_monday - timedelta(days=offset)).isocalendar()[:2] for offset in (0, 7, 14, 21)}


def _expected_schulbeginn_keys(year: int) -> set[tuple[int, int]]:
    """Independent recomputation of the D-07 schulbeginn reading: the ISO week of the
    second Monday of September, plus the week before it (Guide section 1.2)."""
    sept1 = date(year, 9, 1)
    first_monday = sept1 + timedelta(days=(7 - sept1.weekday()) % 7)
    second_monday = first_monday + timedelta(days=7)
    return {
        (second_monday - timedelta(days=7)).isocalendar()[:2],
        second_monday.isocalendar()[:2],
    }


def test_every_iso_year_and_week_present_exactly_once() -> None:
    rows = _read_seed_rows()
    seen_years = sorted({int(row["iso_year"]) for row in rows})
    assert seen_years == EXPECTED_ISO_YEARS

    by_year = _rows_by_year(rows)
    for year in EXPECTED_ISO_YEARS:
        # date(year, 12, 28) always falls in that ISO year's final week, so its own
        # ISO week number is the true week count for the year (52 or 53).
        expected_week_count = date(year, 12, 28).isocalendar()[1]
        year_weeks = sorted(int(row["iso_week"]) for row in by_year[year])
        assert year_weeks == list(range(1, expected_week_count + 1)), year


def test_advent_flag_exactly_four_weeks_per_year_including_dec24_week() -> None:
    rows = _read_seed_rows()
    by_year = _rows_by_year(rows)
    for year in EXPECTED_ISO_YEARS:
        flagged = {
            (int(row["iso_year"]), int(row["iso_week"]))
            for row in by_year[year]
            if row["advent_flag"] == "1"
        }
        assert len(flagged) == 4, year
        assert flagged == _expected_advent_keys(year), year

        dec24 = date(year, 12, 24)
        dec24_key = dec24.isocalendar()[:2]
        assert dec24_key in flagged, year


def test_schulbeginn_flag_exactly_two_weeks_per_year_including_second_monday() -> None:
    rows = _read_seed_rows()
    by_year = _rows_by_year(rows)
    for year in EXPECTED_ISO_YEARS:
        flagged = {
            (int(row["iso_year"]), int(row["iso_week"]))
            for row in by_year[year]
            if row["schulbeginn_flag"] == "1"
        }
        assert len(flagged) == 2, year
        assert flagged == _expected_schulbeginn_keys(year), year

        sept1 = date(year, 9, 1)
        first_monday = sept1 + timedelta(days=(7 - sept1.weekday()) % 7)
        second_monday = first_monday + timedelta(days=7)
        later_key = second_monday.isocalendar()[:2]
        assert later_key == max(flagged), year


def test_jan_dip_flag_exact_iso_week_range() -> None:
    rows = _read_seed_rows()
    flagged_weeks = {int(row["iso_week"]) for row in rows if row["jan_dip_flag"] == "1"}
    unflagged_weeks = {int(row["iso_week"]) for row in rows if row["jan_dip_flag"] == "0"}
    assert flagged_weeks == {2, 3, 4, 5}
    assert flagged_weeks.isdisjoint(unflagged_weeks)


def test_spring_flag_exact_iso_week_range() -> None:
    rows = _read_seed_rows()
    flagged_weeks = {int(row["iso_week"]) for row in rows if row["spring_flag"] == "1"}
    unflagged_weeks = {int(row["iso_week"]) for row in rows if row["spring_flag"] == "0"}
    assert flagged_weeks == set(range(14, 23))
    assert flagged_weeks.isdisjoint(unflagged_weeks)


def test_summer_lull_flag_exact_iso_week_range() -> None:
    rows = _read_seed_rows()
    flagged_weeks = {int(row["iso_week"]) for row in rows if row["summer_lull_flag"] == "1"}
    unflagged_weeks = {int(row["iso_week"]) for row in rows if row["summer_lull_flag"] == "0"}
    assert flagged_weeks == set(range(29, 34))
    assert flagged_weeks.isdisjoint(unflagged_weeks)


def test_flag_columns_are_binary_integers() -> None:
    rows = _read_seed_rows()
    flag_columns = [
        "advent_flag",
        "schulbeginn_flag",
        "jan_dip_flag",
        "spring_flag",
        "summer_lull_flag",
    ]
    for row in rows:
        for column in flag_columns:
            raw_value = row[column]
            assert raw_value in {"0", "1"}, (row["iso_year"], row["iso_week"], column)
            assert int(raw_value) in {0, 1}


def test_week_start_is_monday_matching_own_iso_year_and_week() -> None:
    rows = _read_seed_rows()
    for row in rows:
        week_start = date.fromisoformat(row["week_start"])
        assert week_start.weekday() == 0, row
        iso_year, iso_week, _ = week_start.isocalendar()
        assert iso_year == int(row["iso_year"]), row
        assert iso_week == int(row["iso_week"]), row


def test_2022_spot_values_literal() -> None:
    """Literal expected values for 2022 (WBS 02_WBS.md T-011 validation), asserted with
    no re-derivation from the generator's own logic."""
    rows = _read_seed_rows()
    by_key = {(int(r["iso_year"]), int(r["iso_week"])): r for r in rows if r["iso_year"] == "2022"}

    # Advent: ISO weeks 48-51 of 2022, week_start Mondays 2022-11-28 .. 2022-12-19.
    expected_advent = {
        (2022, 48): "2022-11-28",
        (2022, 49): "2022-12-05",
        (2022, 50): "2022-12-12",
        (2022, 51): "2022-12-19",
    }
    for key, expected_week_start in expected_advent.items():
        row = by_key[key]
        assert row["advent_flag"] == "1", key
        assert row["week_start"] == expected_week_start, key
    for key in ((2022, 47), (2022, 52)):
        assert by_key[key]["advent_flag"] == "0", key

    # Schulbeginn: ISO weeks 36-37 of 2022, week_start Mondays 2022-09-05, 2022-09-12.
    expected_schulbeginn = {
        (2022, 36): "2022-09-05",
        (2022, 37): "2022-09-12",
    }
    for key, expected_week_start in expected_schulbeginn.items():
        row = by_key[key]
        assert row["schulbeginn_flag"] == "1", key
        assert row["week_start"] == expected_week_start, key
    for key in ((2022, 35), (2022, 38)):
        assert by_key[key]["schulbeginn_flag"] == "0", key

    # One literal spot value from each fixed-range rule.
    assert by_key[(2022, 3)]["jan_dip_flag"] == "1"
    assert by_key[(2022, 3)]["week_start"] == "2022-01-17"
    assert by_key[(2022, 18)]["spring_flag"] == "1"
    assert by_key[(2022, 18)]["week_start"] == "2022-05-02"
    assert by_key[(2022, 31)]["summer_lull_flag"] == "1"
    assert by_key[(2022, 31)]["week_start"] == "2022-08-01"


def test_regeneration_is_idempotent_against_committed_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    regenerated_path = tmp_path / "season_windows.csv"
    monkeypatch.setattr(gsw, "SEED_PATH", regenerated_path)

    exit_code = gsw.main()

    assert exit_code == 0
    assert regenerated_path.read_bytes() == _SEED_PATH.read_bytes()
