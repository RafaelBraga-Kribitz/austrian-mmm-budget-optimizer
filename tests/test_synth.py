"""Simulator unit tests: adstock closed form, Hill at K, seasonality, determinism.

Implements: SIM-001, SIM-071, SIM-073, SIM-074.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from ambo.synth import (
    CHANNEL_SPECS,
    adstock_recursive,
    generate,
    half_life,
    hill,
    modeling_frame,
    round_half_up,
    week_spine,
    write_artifacts,
)


def test_adstock_closed_form_constant_spend():
    x = np.full(40, 10.0)
    decay = 0.5
    a = adstock_recursive(x, decay)
    assert a[-1] == pytest.approx(10.0 / (1.0 - decay), rel=1e-6)


def test_adstock_impulse_carries_forward():
    x = np.array([8.0, 0.0, 0.0, 0.0])
    a = adstock_recursive(x, 0.5)
    np.testing.assert_allclose(a, [8.0, 4.0, 2.0, 1.0])


def test_hill_is_one_half_at_k():
    for k in (500.0, 2_000.0, 4_000.0):
        for s in (0.9, 1.0, 1.3):
            assert hill(np.array([k]), k, s)[0] == pytest.approx(0.5)


def test_hill_zero_at_zero():
    assert hill(np.array([0.0]), 100.0, 1.2)[0] == pytest.approx(0.0)


def test_half_life_of_one_half_decay_is_one_week():
    assert half_life(0.5) == pytest.approx(1.0)


def test_round_half_up_not_bankers():
    np.testing.assert_array_equal(round_half_up(np.array([0.5, 2.5])), np.array([1, 3]))


def test_week_spine_is_gapless_mondays():
    weeks = week_spine(156)
    assert len(weeks) == 156
    starts = pd.to_datetime(weeks["week_start"])
    assert (starts.dt.dayofweek == 0).all()
    assert (starts.diff().dt.days.dropna() == 7).all()


def test_advent_peak_week_is_flagged():
    weeks = week_spine(156)
    # 2022-12-19 is the Monday of the week containing 24 Dec 2022 (Saturday).
    xmas_week = weeks.loc[weeks["week_start"] == date(2022, 12, 19)]
    assert not xmas_week.empty
    assert int(xmas_week["advent_flag"].iloc[0]) == 1


def test_generate_is_deterministic():
    a = generate(seed=101)
    b = generate(seed=101)
    np.testing.assert_array_equal(a.spend.to_numpy(), b.spend.to_numpy())
    np.testing.assert_allclose(a.outcome["revenue_eur"], b.outcome["revenue_eur"])


def test_decomposition_adds_to_revenue():
    sim = generate(seed=101)
    media = sim.contributions.to_numpy().sum(axis=1)
    rebuilt = sim.outcome["base"].to_numpy() + media + sim.outcome["noise"].to_numpy()
    np.testing.assert_allclose(rebuilt, sim.outcome["revenue_eur"].to_numpy(), atol=1e-8)


def test_media_share_in_plausible_band():
    sim = generate(seed=101)
    share = float(sim.truth["media_share"])
    assert 0.15 <= share <= 0.45


def test_max_revenue_week_falls_in_advent():
    sim = generate(seed=101)
    joined = sim.weeks.copy()
    joined["revenue"] = sim.outcome["revenue_eur"].to_numpy()
    for year, group in joined.groupby("iso_year"):
        if len(group) < 40:
            continue
        peak = group.loc[group["revenue"].idxmax()]
        assert int(peak["advent_flag"]) == 1, f"{year} peak not in Advent"


def test_flighted_channels_have_zero_weeks():
    sim = generate(seed=101)
    for spec in CHANNEL_SPECS:
        if spec.burst_length is None:
            continue
        zeros = float((sim.spend[spec.channel_id] == 0).mean())
        assert zeros > 0.4


def test_offline_platform_columns_are_null():
    sim = generate(seed=101)
    tv = sim.media.loc[sim.media["channel"] == "tv"]
    assert tv["platform_revenue_eur"].isna().all()


def test_online_platform_overcredits_true_contribution():
    sim = generate(seed=101)
    social = sim.media.loc[sim.media["channel"] == "paid_social"]
    plat = float(pd.to_numeric(social["platform_revenue_eur"]).sum())
    true = float(sim.contributions["paid_social"].sum())
    assert plat > true


def test_modeling_frame_has_spend_columns():
    frame = modeling_frame(generate(seed=101))
    assert "spend_tv" in frame.columns
    assert len(frame) == 156


def test_write_artifacts(tmp_path):
    sim = generate(seed=101, n_weeks=20)
    write_artifacts(sim, directory=tmp_path)
    assert (tmp_path / "truth.json").exists()
    assert (tmp_path / "media_weekly.csv").exists()
    assert (tmp_path / "outcome_weekly.csv").exists()


def test_zero_channel_has_zero_contribution():
    sim = generate(seed=101, n_weeks=40, zero_channel="tv")
    np.testing.assert_allclose(sim.contributions["tv"].to_numpy(), 0.0)
