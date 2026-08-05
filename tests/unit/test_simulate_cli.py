"""Tests for `ambo.simulate.__main__` (T-108).

Implements: SIM-001, SIM-004, SIM-070, REQ-grain-and-windows

`main(["all", "--outdir", str(tmp_path)])` is called in-process throughout --
faster than a subprocess, and it keeps coverage measurement honest. A subprocess
is used exactly once, in `test_module_entry_point_raises_system_exit`, to prove
the `if __name__ == "__main__":` wiring itself, which an in-process call can
never exercise.

The byte-identity test mirrors `tests/unit/test_import_independence.py`'s own
non-vacuous-scan discipline (lines 55-64): every expected file's existence and
non-zero size is asserted **before** any byte comparison, so a silently-empty
regeneration can never pass vacuously.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from ambo.simulate.__main__ import main, validate_sim
from ambo.simulate.config import SPEC_CHANNEL_ORDER, load_scenario

_SCENARIOS: tuple[str, ...] = ("s_a", "s_b", "s_c")
_ARTIFACTS: tuple[str, ...] = ("media_weekly.csv", "outcome_weekly.csv", "truth.json")
_EXPECTED_RELATIVE_PATHS: tuple[str, ...] = tuple(
    f"{scenario}/{artifact}" for scenario in _SCENARIOS for artifact in _ARTIFACTS
)
_MEDIA_HEADER = "week_start,channel,spend_eur,impressions,platform_conversions,platform_revenue_eur"
_OUTCOME_HEADER = "week_start,revenue_eur,orders,promo_flag"
_OFFLINE_CHANNELS = ("print_regional", "radio")


# ---------------------------------------------------------------------------
# SIM-070 determinism
# ---------------------------------------------------------------------------


def test_determinism_two_runs_are_byte_identical(tmp_path: Path) -> None:
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"
    assert main(["all", "--outdir", str(dir_a)]) == 0
    assert main(["all", "--outdir", str(dir_b)]) == 0

    for rel in _EXPECTED_RELATIVE_PATHS:
        path_a, path_b = dir_a / rel, dir_b / rel
        assert path_a.is_file() and path_a.stat().st_size > 0, f"{path_a} missing or empty"
        assert path_b.is_file() and path_b.stat().st_size > 0, f"{path_b} missing or empty"

    for rel in _EXPECTED_RELATIVE_PATHS:
        assert (dir_a / rel).read_bytes() == (dir_b / rel).read_bytes(), f"{rel} differs"


# ---------------------------------------------------------------------------
# Artifact shape
# ---------------------------------------------------------------------------


def test_all_nine_artifacts_are_created(tmp_path: Path) -> None:
    assert main(["all", "--outdir", str(tmp_path)]) == 0
    written = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert written == sorted(_EXPECTED_RELATIVE_PATHS)
    assert not any(".tmp-" in name for name in written), "a temp file was left behind"


def test_csv_headers_match_sim_004_exactly(tmp_path: Path) -> None:
    assert main(["all", "--outdir", str(tmp_path)]) == 0
    for scenario in _SCENARIOS:
        media_text = (tmp_path / scenario / "media_weekly.csv").read_text(encoding="utf-8")
        outcome_text = (tmp_path / scenario / "outcome_weekly.csv").read_text(encoding="utf-8")
        assert media_text.splitlines()[0] == _MEDIA_HEADER
        assert outcome_text.splitlines()[0] == _OUTCOME_HEADER


def test_offline_channels_render_as_empty_fields(tmp_path: Path) -> None:
    assert main(["s_a", "--outdir", str(tmp_path)]) == 0
    text = (tmp_path / "s_a" / "media_weekly.csv").read_text(encoding="utf-8")
    rows = text.splitlines()[1:]
    offline_rows = [row for row in rows if row.split(",")[1] in _OFFLINE_CHANNELS]
    online_rows = [row for row in rows if row.split(",")[1] not in _OFFLINE_CHANNELS]

    assert offline_rows, "no offline-channel rows found -- the scan is broken"
    assert online_rows, "no online-channel rows found -- the scan is broken"
    assert all(row.endswith(",,,") for row in offline_rows)
    assert not any(row.endswith(",,,") for row in online_rows)
    for token in ("nan", "NaN", "None", "NULL"):
        assert token not in text


def test_integer_columns_have_no_decimal_point(tmp_path: Path) -> None:
    assert main(["s_a", "--outdir", str(tmp_path)]) == 0

    media_rows = (
        (tmp_path / "s_a" / "media_weekly.csv").read_text(encoding="utf-8").splitlines()[1:]
    )
    for row in media_rows:
        spend_eur, impressions, platform_conversions = row.split(",")[2:5]
        assert "." not in spend_eur
        assert "." not in impressions
        assert "." not in platform_conversions

    outcome_rows = (
        (tmp_path / "s_a" / "outcome_weekly.csv").read_text(encoding="utf-8").splitlines()[1:]
    )
    for row in outcome_rows:
        orders, promo_flag = row.split(",")[2:4]
        assert "." not in orders
        assert "." not in promo_flag


def test_no_cr_bytes_in_any_written_file(tmp_path: Path) -> None:
    assert main(["all", "--outdir", str(tmp_path)]) == 0
    for rel in _EXPECTED_RELATIVE_PATHS:
        data = (tmp_path / rel).read_bytes()
        assert b"\r" not in data, f"{rel} contains a CR byte"


def test_week_start_is_iso_date_and_spine_is_gapless(tmp_path: Path) -> None:
    assert main(["s_a", "--outdir", str(tmp_path)]) == 0
    cfg = load_scenario("s_a")
    rows = (tmp_path / "s_a" / "outcome_weekly.csv").read_text(encoding="utf-8").splitlines()[1:]
    week_starts = [row.split(",")[0] for row in rows]

    assert len(week_starts) == cfg.weeks
    assert len(set(week_starts)) == len(week_starts), "week_start must be unique"

    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    assert all(date_re.match(value) for value in week_starts)

    dates = [date.fromisoformat(value) for value in week_starts]
    assert dates == sorted(dates), "week_start must be strictly increasing"
    for prev, nxt in zip(dates, dates[1:], strict=False):
        assert (nxt - prev).days == 7

    expected_start = date.fromisocalendar(cfg.start_iso_year, cfg.start_iso_week, 1)
    expected_end = date.fromisocalendar(cfg.end_iso_year, cfg.end_iso_week, 1)
    assert dates[0] == expected_start
    assert dates[-1] == expected_end


def test_media_row_order_is_week_then_taxonomy(tmp_path: Path) -> None:
    assert main(["s_a", "--outdir", str(tmp_path)]) == 0
    rows = [
        row.split(",")
        for row in (tmp_path / "s_a" / "media_weekly.csv")
        .read_text(encoding="utf-8")
        .splitlines()[1:]
    ]
    keys = [(row[0], row[1]) for row in rows]
    assert len(set(keys)) == len(keys), "(week_start, channel) must be unique"

    for week_start in dict.fromkeys(row[0] for row in rows):
        channel_sequence = [row[1] for row in rows if row[0] == week_start]
        assert channel_sequence == list(SPEC_CHANNEL_ORDER)

    # The assertion that catches an accidental alphabetical sort: display_video
    # sits between meta and print_regional in SPEC_CHANNEL_ORDER, not adjacent to
    # them alphabetically.
    meta_index = SPEC_CHANNEL_ORDER.index("meta")
    display_video_index = SPEC_CHANNEL_ORDER.index("display_video")
    print_regional_index = SPEC_CHANNEL_ORDER.index("print_regional")
    assert meta_index < display_video_index < print_regional_index


# ---------------------------------------------------------------------------
# CLI target selection
# ---------------------------------------------------------------------------


def test_single_scenario_target_writes_only_that_scenario(tmp_path: Path) -> None:
    assert main(["s_b", "--outdir", str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["s_b"]


def test_unknown_target_exits_non_zero_and_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["s_z", "--outdir", str(tmp_path)])
    assert exc_info.value.code != 0
    assert list(tmp_path.iterdir()) == [], "argparse rejection must not create any output"


# ---------------------------------------------------------------------------
# validate_sim
# ---------------------------------------------------------------------------


def test_validate_sim_passes_on_a_fresh_generation(tmp_path: Path) -> None:
    assert main(["all", "--outdir", str(tmp_path)]) == 0
    assert validate_sim(tmp_path) == 0


def test_validate_sim_fails_on_a_corrupted_artifact(tmp_path: Path) -> None:
    assert main(["all", "--outdir", str(tmp_path)]) == 0
    truth_path = tmp_path / "s_a" / "truth.json"
    with truth_path.open("ab") as handle:
        handle.write(b"x")
    assert validate_sim(tmp_path) != 0


def test_validate_sim_fails_on_a_missing_artifact(tmp_path: Path) -> None:
    assert main(["all", "--outdir", str(tmp_path)]) == 0
    (tmp_path / "s_b" / "outcome_weekly.csv").unlink()
    assert validate_sim(tmp_path) != 0


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------


def test_module_entry_point_raises_system_exit(tmp_path: Path, repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ambo.simulate", "s_a", "--outdir", str(tmp_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "s_a" / "truth.json").is_file()
