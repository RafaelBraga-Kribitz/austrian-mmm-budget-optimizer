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
from hypothesis import given, settings
from hypothesis import strategies as st

from ambo.common.errors import SimulationError
from ambo.simulate import dgp
from ambo.simulate.config import SPEC_CHANNEL_ORDER, SeasonWeights, load_scenario
from ambo.simulate.dgp import (
    SimulationResult,
    adstock_recursive,
    assemble_scenario,
    baseline_demand,
    decomposition_audit,
    hill,
    peak_week_audit,
    plausibility_audit,
    round_half_up,
    season_index,
    week_index,
)

# SPEC-01 section 4, verbatim: (K, s) per channel -- the boundary table for the
# hill(K)=0.5 exactness test below.
_SPEC01_HILL_TABLE: tuple[tuple[str, float, float], ...] = (
    ("search_brand", 800.0, 1.2),
    ("search_generic", 3000.0, 1.0),
    ("meta", 2500.0, 0.9),
    ("display_video", 2000.0, 1.1),
    ("print_regional", 4000.0, 1.3),
    ("radio", 3500.0, 1.2),
)


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


# ---------------------------------------------------------------------------
# adstock_recursive -- impulse test FIRST (02-RESEARCH.md Pitfall 4, trap T-2),
# then the closed-form limit test, per the project's own written-before-trusted
# ordering discipline.
# ---------------------------------------------------------------------------


def test_adstock_impulse_response_is_causal() -> None:
    x = np.zeros(50)
    x[10] = 1000.0
    a = adstock_recursive(x, lam=0.6)
    assert (a[:10] == 0).all()
    for t in range(10, 50):
        assert abs(a[t] - 1000.0 * 0.6 ** (t - 10)) < 1e-9


def test_adstock_closed_form_limit() -> None:
    x = np.full(200, 1000.0)
    a = adstock_recursive(x, lam=0.6)
    assert abs(a[-1] - 1000.0 / (1 - 0.6)) < 1e-9


def test_adstock_finite_t_exactness() -> None:
    x = np.full(200, 1000.0)
    a = adstock_recursive(x, lam=0.6)
    for t in range(200):
        expected = 1000.0 * (1 - 0.6 ** (t + 1)) / (1 - 0.6)
        assert abs(a[t] - expected) < 1e-9


def test_adstock_all_zero_input_is_exactly_all_zero() -> None:
    a = adstock_recursive(np.zeros(52), 0.6)
    assert (a == 0.0).all()


def test_adstock_single_element_input_is_exact() -> None:
    a = adstock_recursive(np.array([1234.0]), 0.6)
    assert list(a) == [1234.0]


def test_adstock_empty_input_returns_empty_without_raising() -> None:
    a = adstock_recursive(np.array([]), 0.6)
    assert a.shape == (0,)


@pytest.mark.parametrize("channel", [row[0] for row in _SPEC01_HILL_TABLE])
def test_hill_at_k_is_exactly_half_across_spec01_table(channel: str) -> None:
    table = dict((row[0], (row[1], row[2])) for row in _SPEC01_HILL_TABLE)
    k, s = table[channel]
    result = hill(np.array([k]), K=k, s=s)
    assert abs(result[0] - 0.5) < 1e-12


def test_hill_at_zero_spend_is_exactly_zero() -> None:
    result = hill(np.array([0.0]), K=2500.0, s=0.9)
    assert result[0] == 0.0


def test_adstock_raises_on_negative_element() -> None:
    with pytest.raises(SimulationError):
        adstock_recursive(np.array([1.0, -1.0]), 0.6)


def test_adstock_raises_on_nan() -> None:
    with pytest.raises(SimulationError):
        adstock_recursive(np.array([1.0, float("nan")]), 0.6)


def test_adstock_raises_on_infinity() -> None:
    with pytest.raises(SimulationError):
        adstock_recursive(np.array([1.0, float("inf")]), 0.6)


def test_adstock_raises_on_lam_equal_to_one() -> None:
    with pytest.raises(SimulationError):
        adstock_recursive(np.array([1.0, 2.0]), 1.0)


def test_adstock_raises_on_negative_lam() -> None:
    with pytest.raises(SimulationError):
        adstock_recursive(np.array([1.0, 2.0]), -0.1)


def test_hill_raises_on_negative_a() -> None:
    with pytest.raises(SimulationError):
        hill(np.array([-1.0]), K=1000.0, s=1.0)


def test_hill_raises_on_non_positive_k() -> None:
    with pytest.raises(SimulationError):
        hill(np.array([1.0]), K=0.0, s=1.0)


def test_hill_raises_on_non_positive_s() -> None:
    with pytest.raises(SimulationError):
        hill(np.array([1.0]), K=1000.0, s=0.0)


# ---------------------------------------------------------------------------
# Property-based invariants (D-03) -- exactly five, bounded strategies only.
#
# `@settings(max_examples=100)` is applied explicitly rather than relying on
# Hypothesis's implicit default, and no project-wide Hypothesis profile is
# registered in conftest.py: if suite runtime ever becomes a problem, the fix
# is a profile there, not a per-test tweak (02-RESEARCH.md Code Examples).
# Every float strategy passes allow_nan=False, allow_infinity=False plus
# explicit min_value/max_value so generated inputs stay in-bounds directly
# rather than via assume() filtering, which trips Hypothesis's
# too-much-filtering health check (02-RESEARCH.md Pitfall 5). st.integers is
# used for the one index-valued strategy below, never a float cast.
# ---------------------------------------------------------------------------


@given(
    x=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    lam=st.floats(min_value=0, max_value=0.99, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_adstock_is_bounded_by_the_geometric_limit(x: float, lam: float) -> None:
    a = adstock_recursive(np.full(52, x), lam)
    assert (a >= 0).all()
    assert (a <= x / (1 - lam) + 1e-6).all()


@given(
    base=st.lists(
        st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=5,
        max_size=20,
    ),
    k=st.integers(min_value=0, max_value=4),
    delta=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    lam=st.floats(min_value=0, max_value=0.99, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_adstock_is_monotone_in_a_single_spend_value(
    base: list[float], k: int, delta: float, lam: float
) -> None:
    x = np.array(base)
    a_before = adstock_recursive(x, lam)
    x_after = x.copy()
    x_after[k] = x_after[k] + delta
    a_after = adstock_recursive(x_after, lam)
    assert (a_after >= a_before - 1e-9).all()


@given(
    base=st.lists(
        st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=5,
        max_size=20,
    ),
    k=st.integers(min_value=1, max_value=4),
    delta=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    lam=st.floats(min_value=0, max_value=0.99, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_adstock_is_causal_under_a_future_perturbation(
    base: list[float], k: int, delta: float, lam: float
) -> None:
    """The property-based twin of the impulse test: perturbing `x[k]` never
    changes any `a[j]` for `j < k` -- the strongest available guard against
    trap T-2 (convolution-direction reversal)."""
    x = np.array(base)
    a_before = adstock_recursive(x, lam)
    x_after = x.copy()
    x_after[k] = x_after[k] + delta
    a_after = adstock_recursive(x_after, lam)
    assert np.array_equal(a_before[:k], a_after[:k])


@given(
    a=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    K=st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False),
    s=st.floats(min_value=0.1, max_value=5, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_hill_output_is_a_unit_fraction(a: float, K: float, s: float) -> None:
    h = hill(np.array([a]), K, s)
    assert 0 <= h[0] <= 1


@given(
    a1=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    delta=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    K=st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False),
    s=st.floats(min_value=0.1, max_value=5, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_hill_is_monotone_non_decreasing_in_adstocked_spend(
    a1: float, delta: float, K: float, s: float
) -> None:
    a2 = a1 + delta
    h1 = hill(np.array([a1]), K, s)[0]
    h2 = hill(np.array([a2]), K, s)[0]
    assert h1 <= h2 + 1e-12


# ---------------------------------------------------------------------------
# assemble_scenario / SimulationResult / SIM-071, SIM-072, SIM-073 audits
# (plan 02-06 Task 2). `-k assemble` selects this whole group.
# ---------------------------------------------------------------------------

_ALL_SCENARIOS = ["s_a", "s_b", "s_c"]


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_decomposition_audit_within_tolerance(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    max_deviation = decomposition_audit(result)
    assert max_deviation <= 1e-6, (
        f"SIM-071: {scenario_id} max abs deviation {max_deviation!r} exceeds tolerance 1e-6"
    )


def test_assemble_decomposition_violation_raises_at_construction() -> None:
    cfg = load_scenario("s_a")
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    perturbed = result.components.copy()
    perturb_position = 5
    perturbed.loc[perturbed.index[perturb_position], "base"] += 1.0
    expected_week = str(result.weeks["week_start"].iloc[perturb_position].date())

    with pytest.raises(SimulationError, match=expected_week):
        SimulationResult(
            cfg=result.cfg,
            weeks=result.weeks,
            spend=result.spend,
            components=perturbed,
            media=result.media,
            outcome=result.outcome,
        )


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_plausibility_bounds(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    stats = plausibility_audit(result)

    assert stats["min_revenue_pre_clip"] >= 0.0, (
        f"SIM-072: {scenario_id} min_revenue_pre_clip {stats['min_revenue_pre_clip']!r} "
        "is negative -- the clip bound"
    )
    assert 0.02 <= stats["noise_variance_share"] <= 0.10, (
        f"SIM-072: {scenario_id} noise_variance_share {stats['noise_variance_share']!r} "
        "outside [0.02, 0.10]"
    )
    media_shares = {k: v for k, v in stats.items() if k.startswith("media_share_")}
    assert media_shares, f"SIM-072: {scenario_id} returned no media_share_<year> entries"
    for key, value in media_shares.items():
        assert 0.15 <= value <= 0.45, f"SIM-072: {scenario_id} {key}={value!r} outside [0.15, 0.45]"


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_peak_revenue_week_is_in_advent(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    audit = peak_week_audit(result)

    audited_years = {year: value for year, value in audit.items() if value[0] != -1}
    assert audited_years, (
        f"SIM-073: {scenario_id} audited zero ISO years -- the audit must not pass vacuously"
    )
    for iso_year, (peak_week, is_advent) in audited_years.items():
        assert is_advent, (
            f"SIM-073: {scenario_id} {iso_year}'s peak-revenue week (ISO week {peak_week}) "
            "does not carry advent_flag == 1"
        )


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_frame_shapes_and_column_order(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))

    assert len(result.outcome) == cfg.weeks
    assert len(result.media) == 6 * cfg.weeks
    assert list(result.outcome.columns) == ["week_start", "revenue_eur", "orders", "promo_flag"]
    assert list(result.media.columns) == [
        "week_start",
        "channel",
        "spend_eur",
        "impressions",
        "platform_conversions",
        "platform_revenue_eur",
    ]


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_week_spine_is_iso_monday_and_gapless(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    weeks = result.weeks

    assert (result.media["week_start"].dt.dayofweek == 0).all()
    assert (result.outcome["week_start"].dt.dayofweek == 0).all()

    outcome_starts = result.outcome["week_start"]
    assert outcome_starts.is_unique
    assert outcome_starts.is_monotonic_increasing
    diffs = outcome_starts.diff().dropna()
    assert (diffs.dt.days == 7).all()
    assert outcome_starts.iloc[0] == weeks["week_start"].iloc[0]
    assert outcome_starts.iloc[-1] == weeks["week_start"].iloc[-1]


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_media_row_order_is_week_then_taxonomy(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = result.media

    pairs = list(zip(media["week_start"], media["channel"], strict=True))
    assert len(pairs) == len(set(pairs)), "(week_start, channel) pairs are not unique"

    channel_position = {channel: i for i, channel in enumerate(SPEC_CHANNEL_ORDER)}
    sort_keys = [(week, channel_position[channel]) for week, channel in pairs]
    assert sort_keys == sorted(sort_keys), (
        "media rows are not sorted by week_start ascending then SPEC_CHANNEL_ORDER position"
    )

    first_week = media["week_start"].iloc[0]
    first_week_rows = media[media["week_start"] == first_week]
    meta_position = first_week_rows.index[first_week_rows["channel"] == "meta"][0]
    display_video_position = first_week_rows.index[first_week_rows["channel"] == "display_video"][0]
    assert meta_position < display_video_position, (
        "display_video must sort after meta (SPEC_CHANNEL_ORDER order), not before it "
        "alphabetically -- this is the assertion that catches an accidental alphabetical sort"
    )


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_orders_follow_the_aov_rule(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    advent_flag = result.weeks["advent_flag"].to_numpy()
    aov = cfg.aov_base + cfg.aov_advent_bonus * advent_flag
    expected_orders = round_half_up(result.outcome["revenue_eur"].to_numpy() / aov)
    assert list(result.outcome["orders"]) == list(expected_orders)


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_promo_flag_matches_the_yaml(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    weeks = result.weeks

    expected_flagged = {
        (iso_year, iso_week)
        for iso_year, iso_weeks in cfg.promo_weeks.items()
        for iso_week in iso_weeks
    }
    actual_flagged = {
        (int(iso_year), int(iso_week))
        for iso_year, iso_week, flag in zip(
            weeks["iso_year"], weeks["iso_week"], result.outcome["promo_flag"], strict=True
        )
        if flag == 1
    }
    assert actual_flagged == expected_flagged


def test_assemble_zero_beta_channel_contributes_exactly_zero() -> None:
    """S-C's `display_video` has `true_params.beta == 0.0` (SPEC-01 section 4's
    footnote), so `m_display_video` must be exactly 0.0 every week, and the sum
    over the five nonzero channels must equal the total channel sum exactly.

    The plan's literal first choice -- a bit-identical comparison against a
    "control" run built from a copy of the S-B config restricted to S-C's window
    with `display_video.beta` monkeypatched to 0.0 -- is not achievable here:
    `ScenarioConfig._validate_scenario_identity` pins `(id, weeks, seed)` to one
    of exactly the three frozen SPEC-01 section 5 triples, so no such hybrid
    config can be constructed without bypassing validation. Falling back to the
    plan's own sanctioned alternative instead.
    """
    cfg = load_scenario("s_c")
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))

    m_display_video = result.components["m_display_video"].to_numpy()
    assert (m_display_video == 0.0).all()

    channel_sum = result.components[[f"m_{c}" for c in SPEC_CHANNEL_ORDER]].sum(axis=1).to_numpy()
    nonzero_channels = [c for c in SPEC_CHANNEL_ORDER if c != "display_video"]
    nonzero_sum = result.components[[f"m_{c}" for c in nonzero_channels]].sum(axis=1).to_numpy()
    assert np.array_equal(channel_sum, nonzero_sum)


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_assemble_determinism_same_seed(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    first = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    second = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    assert first.media.equals(second.media)
    assert first.outcome.equals(second.outcome)
    assert first.components.equals(second.components)
