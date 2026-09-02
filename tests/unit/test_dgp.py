"""Point tests for `ambo.simulate.dgp` (T-103, T-104).

Implements: REQ-q1-truth-recovery, REQ-grain-and-windows

Covers, in this order: the calendar spine (`week_index`), the seasonal index
(`season_index`, SIM-073), baseline demand (`baseline_demand`), and the rounding
convention (`round_half_up`) -- Task 1. Task 2 appends the adstock/Hill point
tests (SIM-074), impulse test before closed-form test per 02-RESEARCH.md
Pitfall 4 (trap T-2). Task 3 appends D-03's five bounded `hypothesis` property
tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ambo.common.errors import SimulationError
from ambo.simulate import dgp
from ambo.simulate.config import SeasonWeights, load_scenario
from ambo.simulate.dgp import baseline_demand, round_half_up, season_index, week_index


@pytest.fixture(autouse=True)
def _clear_scenario_cache() -> Iterator[None]:
    """Every test starts and ends with a cold `load_scenario` cache, mirroring
    `test_scenario_config.py`'s `_clear_scenario_cache`."""
    load_scenario.cache_clear()
    yield
    load_scenario.cache_clear()


def _spec01_season_weights() -> SeasonWeights:
    """SPEC-01 section 2.1's five weights, literal and signed exactly as the
    scenario YAMLs declare them -- not imported from config.py, so this test
    module cannot pass by re-running the same values under another name."""
    return SeasonWeights(
        advent=0.55, schulbeginn=0.25, spring=0.15, jan_dip=-0.20, summer_lull=-0.10
    )


# ---------------------------------------------------------------------------
# week_index -- row counts, spine shape, ordering (SIM-073's grain half)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("scenario_id", "expected_weeks"),
    [("s_a", 156), ("s_b", 104), ("s_c", 78)],
)
def test_week_index_row_count_matches_scenario_weeks(scenario_id: str, expected_weeks: int) -> None:
    weeks = week_index(load_scenario(scenario_id))
    assert len(weeks) == expected_weeks


def test_week_index_first_week_start_s_a() -> None:
    weeks = week_index(load_scenario("s_a"))
    assert not weeks.empty, "non-vacuous scan guard: the filtered frame must not be empty"
    assert str(weeks["week_start"].iloc[0].date()) == "2021-01-04"


@pytest.mark.parametrize("scenario_id", ["s_b", "s_c"])
def test_week_index_first_week_start_s_b_s_c(scenario_id: str) -> None:
    weeks = week_index(load_scenario(scenario_id))
    assert not weeks.empty, "non-vacuous scan guard: the filtered frame must not be empty"
    assert str(weeks["week_start"].iloc[0].date()) == "2022-01-03"


def test_week_index_last_week_start_s_c() -> None:
    weeks = week_index(load_scenario("s_c"))
    assert not weeks.empty, "non-vacuous scan guard: the filtered frame must not be empty"
    assert str(weeks["week_start"].iloc[-1].date()) == "2023-06-26"


@pytest.mark.parametrize("scenario_id", ["s_a", "s_b", "s_c"])
def test_week_index_is_a_gapless_iso_monday_spine(scenario_id: str) -> None:
    weeks = week_index(load_scenario(scenario_id))
    assert not weeks.empty, "non-vacuous scan guard: the filtered frame must not be empty"
    assert (weeks["week_start"].dt.dayofweek == 0).all()
    diffs = weeks["week_start"].diff().dropna()
    assert (diffs.dt.days == 7).all()


@pytest.mark.parametrize("scenario_id", ["s_a", "s_b", "s_c"])
def test_week_index_t_column_is_1_indexed_and_ascending(scenario_id: str) -> None:
    weeks = week_index(load_scenario(scenario_id))
    assert list(weeks["t"]) == list(range(1, len(weeks) + 1))


# ---------------------------------------------------------------------------
# week_index -- SimulationError on a missing or duplicated calendar row (AD-020)
# ---------------------------------------------------------------------------


def _s_a_seed_slice(repo_root: Path) -> pd.DataFrame:
    """The real committed seed's s_a-window rows (2021-W01..2023-W52), read once
    from `dbt/seeds/season_windows.csv` so the missing/duplicate-key tests below
    mutate a real slice under `tmp_path` rather than a fabricated one."""
    seed = pd.read_csv(
        repo_root / "dbt" / "seeds" / "season_windows.csv", parse_dates=["week_start"]
    )
    in_window = [
        (2021, 1) <= (year, week) <= (2023, 52)
        for year, week in zip(seed["iso_year"], seed["iso_week"], strict=True)
    ]
    return seed.loc[in_window].reset_index(drop=True)


def test_week_index_raises_on_missing_calendar_row(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = _s_a_seed_slice(repo_root)
    missing_key = (int(rows.loc[10, "iso_year"]), int(rows.loc[10, "iso_week"]))
    short_rows = rows.drop(index=10)
    seed_path = tmp_path / "season_windows.csv"
    short_rows.to_csv(seed_path, index=False)
    monkeypatch.setattr(dgp, "SEED_PATH", seed_path)

    with pytest.raises(SimulationError) as exc_info:
        week_index(load_scenario("s_a"))
    assert str(missing_key) in str(exc_info.value)


def test_week_index_raises_on_duplicate_calendar_row(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = _s_a_seed_slice(repo_root)
    duplicate_key = (int(rows.loc[20, "iso_year"]), int(rows.loc[20, "iso_week"]))
    duplicated_rows = pd.concat([rows, rows.loc[[20]]], ignore_index=True)
    seed_path = tmp_path / "season_windows.csv"
    duplicated_rows.to_csv(seed_path, index=False)
    monkeypatch.setattr(dgp, "SEED_PATH", seed_path)

    with pytest.raises(SimulationError) as exc_info:
        week_index(load_scenario("s_a"))
    assert str(duplicate_key) in str(exc_info.value)


# ---------------------------------------------------------------------------
# season_index -- SPEC-01 section 2.1's five signed weights (SIM-073)
# ---------------------------------------------------------------------------


def test_season_index_all_flags_zero_returns_exactly_one() -> None:
    weeks = pd.DataFrame(
        {
            "advent_flag": [0],
            "schulbeginn_flag": [0],
            "jan_dip_flag": [0],
            "spring_flag": [0],
            "summer_lull_flag": [0],
        }
    )
    result = season_index(weeks, _spec01_season_weights())
    assert result[0] == 1.0


@pytest.mark.parametrize(
    ("flag_column", "expected"),
    [
        ("advent_flag", 1.55),
        ("jan_dip_flag", 0.80),
        ("summer_lull_flag", 0.90),
        ("schulbeginn_flag", 1.25),
        ("spring_flag", 1.15),
    ],
)
def test_season_index_single_flag_matches_spec01_weight(flag_column: str, expected: float) -> None:
    flags = {
        "advent_flag": 0,
        "schulbeginn_flag": 0,
        "jan_dip_flag": 0,
        "spring_flag": 0,
        "summer_lull_flag": 0,
    }
    flags[flag_column] = 1
    weeks = pd.DataFrame({key: [value] for key, value in flags.items()})
    result = season_index(weeks, _spec01_season_weights())
    assert abs(result[0] - expected) < 1e-12


# ---------------------------------------------------------------------------
# baseline_demand -- SPEC-01 section 2.1's base formula
# ---------------------------------------------------------------------------


def test_baseline_demand_base_matches_spec01_formula() -> None:
    cfg = load_scenario("s_a")
    weeks = week_index(cfg)
    result = baseline_demand(cfg, weeks)
    expected = (
        cfg.b0
        * result["trend"].to_numpy()
        * result["season"].to_numpy()
        * result["promo_mult"].to_numpy()
    )
    assert np.allclose(result["base"].to_numpy(), expected, atol=1e-12)


def test_baseline_demand_promo_week_carries_the_promo_multiplier() -> None:
    cfg = load_scenario("s_a")
    weeks = week_index(cfg)
    result = baseline_demand(cfg, weeks)
    promo_position = weeks.index[(weeks["iso_year"] == 2021) & (weeks["iso_week"] == 6)][0]
    assert result.loc[promo_position, "promo_mult"] == pytest.approx(1.15)
    assert result.loc[promo_position, "promo_flag"] == 1


def test_baseline_demand_non_promo_week_carries_no_multiplier() -> None:
    cfg = load_scenario("s_a")
    weeks = week_index(cfg)
    result = baseline_demand(cfg, weeks)
    non_promo_position = weeks.index[(weeks["iso_year"] == 2021) & (weeks["iso_week"] == 1)][0]
    assert result.loc[non_promo_position, "promo_mult"] == 1.0
    assert result.loc[non_promo_position, "promo_flag"] == 0


# ---------------------------------------------------------------------------
# round_half_up -- the single project-wide whole-unit rounding convention (A-8)
# ---------------------------------------------------------------------------


def test_round_half_up_rounding_is_half_away_from_zero_not_banker() -> None:
    result = round_half_up(np.array([0.5, 1.5, 2.5]))
    assert list(result) == [1, 2, 3]
