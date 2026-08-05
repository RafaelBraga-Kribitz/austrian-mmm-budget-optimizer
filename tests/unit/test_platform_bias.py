"""Tests for `ambo.simulate.platform_bias` (T-106).

Implements: REQ-q1-truth-recovery

Covers SIM-060's platform-reporting over-credit formula (a hand-computed identity
to 1e-9, re-derived here with literal arithmetic rather than by calling
`platform_report` a second time), BP-D-02's impressions/conversions rules,
offline-NULL handling for all three scenarios, the zero-total-spend-week
no-NaN/no-infinity guarantee, a config-not-code proof, SIM-061's known
over-credit ordering on S-A/S-B, and row-order preservation.
"""

from __future__ import annotations

import numpy as np
import pytest

from ambo.simulate.config import SPEC_CHANNEL_ORDER, load_scenario
from ambo.simulate.dgp import SimulationResult, assemble_scenario, round_half_up
from ambo.simulate.platform_bias import platform_report

_ALL_SCENARIOS = ["s_a", "s_b", "s_c"]
_OFFLINE_CHANNELS = ("print_regional", "radio")
_ONLINE_CHANNELS = tuple(c for c in SPEC_CHANNEL_ORDER if c not in _OFFLINE_CHANNELS)


def test_hand_computed_example_matches_to_1e_9() -> None:
    """SIM-060 identity check: the expected value is computed here with literal
    arithmetic directly from `result.components`, `result.spend` and `cfg`'s own
    declared `phi`/`theta`, never by calling `platform_report` a second time."""
    cfg = load_scenario("s_a")
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    week_position = 10
    channel_id = "meta"

    m_c = float(result.components[f"m_{channel_id}"].iloc[week_position])
    base_t = float(result.components["base"].iloc[week_position])
    spends = {c: float(result.spend[c].iloc[week_position]) for c in SPEC_CHANNEL_ORDER}
    total_spend = sum(spends.values())
    share_c = spends[channel_id] / total_spend if total_spend > 0.0 else 0.0

    platform = cfg.channels[channel_id].platform
    assert platform.phi is not None
    assert platform.theta is not None
    expected = m_c * platform.phi + platform.theta * base_t * share_c

    media = platform_report(result)
    week_start = result.weeks["week_start"].iloc[week_position]
    row = media[(media["week_start"] == week_start) & (media["channel"] == channel_id)]
    assert len(row) == 1
    actual = float(row["platform_revenue_eur"].iloc[0])
    assert abs(actual - expected) < 1e-9


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_offline_channels_are_null_everywhere(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = platform_report(result)

    offline = media[media["channel"].isin(_OFFLINE_CHANNELS)]
    assert len(offline) == 2 * cfg.weeks, (
        f"{scenario_id}: expected {2 * cfg.weeks} offline row(s), got {len(offline)} -- "
        "this assertion must not pass vacuously on zero rows"
    )
    platform_columns = ["impressions", "platform_conversions", "platform_revenue_eur"]
    assert offline[platform_columns].isna().all().all()


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_online_channels_are_never_null_or_non_finite(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = platform_report(result)

    online = media[media["channel"].isin(_ONLINE_CHANNELS)]
    assert len(online) == 4 * cfg.weeks, (
        f"{scenario_id}: expected {4 * cfg.weeks} online row(s), got {len(online)} -- "
        "this assertion must not pass vacuously on zero rows"
    )
    platform_columns = ["impressions", "platform_conversions", "platform_revenue_eur"]
    assert online[platform_columns].notna().all().all()
    assert np.isfinite(online["platform_revenue_eur"].astype(float)).all()
    assert np.isfinite(online["impressions"].astype(float)).all()
    assert np.isfinite(online["platform_conversions"].astype(float)).all()


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_impressions_follow_the_cpm_rule(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = platform_report(result)

    for channel_id in _ONLINE_CHANNELS:
        platform = cfg.channels[channel_id].platform
        assert platform.cpm is not None
        rows = media[media["channel"] == channel_id].sort_values("week_start")
        assert len(rows) == cfg.weeks, (
            f"{scenario_id}/{channel_id}: expected {cfg.weeks} row(s), got {len(rows)}"
        )
        spend = rows["spend_eur"].to_numpy(dtype=np.float64)
        expected = round_half_up(spend / platform.cpm * 1000.0)
        actual = rows["impressions"].to_numpy(dtype=np.int64)
        assert np.array_equal(actual, expected), f"{scenario_id}/{channel_id}: impressions mismatch"


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_platform_conversions_follow_the_aov_rule(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = platform_report(result)

    advent_flag = result.weeks["advent_flag"].to_numpy(dtype=np.float64)
    aov = cfg.aov_base + cfg.aov_advent_bonus * advent_flag

    for channel_id in _ONLINE_CHANNELS:
        rows = media[media["channel"] == channel_id].sort_values("week_start")
        assert len(rows) == cfg.weeks, (
            f"{scenario_id}/{channel_id}: expected {cfg.weeks} row(s), got {len(rows)}"
        )
        revenue = rows["platform_revenue_eur"].to_numpy(dtype=np.float64)
        expected = round_half_up(revenue / aov)
        actual = rows["platform_conversions"].to_numpy(dtype=np.int64)
        assert np.array_equal(actual, expected), f"{scenario_id}/{channel_id}: conversions mismatch"


def test_zero_total_spend_week_gives_zero_share_and_no_nan() -> None:
    """Zeroing every channel's spend for one week only touches `result.spend` --
    the SIM-071 decomposition invariant re-sums `components` alone, so this
    construction never needs `components` to be adjusted to keep the constructor
    precondition satisfied."""
    cfg = load_scenario("s_a")
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    week_position = 20

    zeroed_spend = result.spend.copy()
    for channel_id in SPEC_CHANNEL_ORDER:
        zeroed_spend.loc[zeroed_spend.index[week_position], channel_id] = 0

    zeroed_result = SimulationResult(
        cfg=result.cfg,
        weeks=result.weeks,
        spend=zeroed_spend,
        components=result.components,
        media=result.media,
        outcome=result.outcome,
    )

    media = platform_report(zeroed_result)
    week_start = result.weeks["week_start"].iloc[week_position]

    checked_any = False
    for channel_id in _ONLINE_CHANNELS:
        platform = cfg.channels[channel_id].platform
        assert platform.phi is not None
        assert platform.theta is not None
        m_c = float(result.components[f"m_{channel_id}"].iloc[week_position])

        row = media[(media["week_start"] == week_start) & (media["channel"] == channel_id)]
        assert len(row) == 1
        actual = float(row["platform_revenue_eur"].iloc[0])
        assert np.isfinite(actual), f"{channel_id}: platform_revenue_eur is not finite"

        # The demand-claiming term (theta * base_t * share_c) must vanish exactly,
        # since share_c is 0.0 for a zero-total-spend week -- not NaN, not
        # infinity, and not merely close to zero from a near-zero denominator.
        demand_claiming_term = actual - m_c * platform.phi
        assert abs(demand_claiming_term) < 1e-9, (
            f"{channel_id}: demand-claiming term {demand_claiming_term!r} did not vanish"
        )
        checked_any = True

    assert checked_any, "no online channel was checked -- the test must not pass vacuously"


def test_phi_theta_come_from_config_not_code() -> None:
    """Proves the formula reads `phi` from `result.cfg`, not a hard-coded literal:
    a monkeypatched `ScenarioConfig` copy with `display_video.platform.phi`
    patched to 3.0 changes `platform_revenue_eur` by exactly `m_c * (3.0 -
    original_phi)` -- the module could not produce this delta from a literal."""
    cfg = load_scenario("s_a")
    channel_id = "display_video"
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    baseline = platform_report(result)

    original_platform = cfg.channels[channel_id].platform
    assert original_platform.phi is not None
    patched_phi = 3.0

    patched_platform = original_platform.model_copy(update={"phi": patched_phi})
    patched_channel = cfg.channels[channel_id].model_copy(update={"platform": patched_platform})
    patched_channels = dict(cfg.channels)
    patched_channels[channel_id] = patched_channel
    patched_cfg = cfg.model_copy(update={"channels": patched_channels})

    patched_result = SimulationResult(
        cfg=patched_cfg,
        weeks=result.weeks,
        spend=result.spend,
        components=result.components,
        media=result.media,
        outcome=result.outcome,
    )
    patched = platform_report(patched_result)

    week_position = 10
    week_start = result.weeks["week_start"].iloc[week_position]
    m_c = float(result.components[f"m_{channel_id}"].iloc[week_position])

    baseline_mask = (baseline["week_start"] == week_start) & (baseline["channel"] == channel_id)
    patched_mask = (patched["week_start"] == week_start) & (patched["channel"] == channel_id)
    baseline_row = baseline[baseline_mask]
    patched_row = patched[patched_mask]
    baseline_revenue = float(baseline_row["platform_revenue_eur"].iloc[0])
    patched_revenue = float(patched_row["platform_revenue_eur"].iloc[0])

    expected_delta = m_c * (patched_phi - original_platform.phi)
    assert abs((patched_revenue - baseline_revenue) - expected_delta) < 1e-6


@pytest.mark.parametrize("scenario_id", ["s_a", "s_b"])
def test_over_credit_ordering_matches_phi_ordering(scenario_id: str) -> None:
    """SIM-061: S-C is excluded because its `display_video` true ROAS is exactly
    0 (`true_params.beta == 0.0`, the scenario's zero-effect channel), so
    `platform_roas / true_roas` is undefined there by construction -- SIM-061's
    ordering claim is about the injected over-credit, not about the zero-effect
    scenario."""
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = platform_report(result)

    ratios: dict[str, float] = {}
    for channel_id in _ONLINE_CHANNELS:
        rows = media[media["channel"] == channel_id]
        assert len(rows) == cfg.weeks, f"{scenario_id}/{channel_id}: expected {cfg.weeks} row(s)"
        total_spend = float(rows["spend_eur"].sum())
        total_platform_revenue = float(rows["platform_revenue_eur"].astype(float).sum())
        total_true_contribution = float(result.components[f"m_{channel_id}"].sum())

        platform_roas = total_platform_revenue / total_spend
        true_roas = total_true_contribution / total_spend
        assert true_roas > 0.0, f"{scenario_id}/{channel_id}: true_roas is not positive"
        ratios[channel_id] = platform_roas / true_roas

    assert (
        ratios["display_video"] > ratios["meta"] > ratios["search_generic"] > ratios["search_brand"]
    ), f"{scenario_id}: over-credit ordering {ratios!r} does not match the phi ordering"


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_row_order_is_preserved(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = platform_report(result)

    expected = list(zip(result.media["week_start"], result.media["channel"], strict=True))
    actual = list(zip(media["week_start"], media["channel"], strict=True))
    assert len(actual) == 6 * cfg.weeks
    assert actual == expected
