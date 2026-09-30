"""Optimiser: budget constraint, bounds, and the decision rule on a made-up posterior."""

import json

import numpy as np
import pandas as pd
import pytest
import yaml

from ambo import optimize
from ambo.run import load_config


def _response_set(n_draws: int = 50, seed: int = 3) -> optimize.ResponseSet:
    rng = np.random.default_rng(seed)
    channels = ["A", "B", "C"]
    decay = rng.uniform(0.1, 0.6, size=(n_draws, 3))
    length = 13
    carry = np.vectorize(lambda d: optimize.adstock_weights(d, length).sum())(decay)
    return optimize.ResponseSet(
        channels=channels,
        decay=decay,
        half_sat=rng.uniform(0.8, 2.0, size=(n_draws, 3)),
        slope=rng.uniform(0.8, 1.5, size=(n_draws, 3)),
        # channel A is clearly the most productive, channel C the least
        effect=np.column_stack(
            [rng.normal(0.4, 0.02, n_draws), rng.normal(0.2, 0.02, n_draws),
             rng.normal(0.02, 0.005, n_draws)]
        ),
        spend_means=np.array([100.0, 100.0, 100.0]),
        revenue_mean=10000.0,
        current=np.array([100.0, 100.0, 100.0]),
        carry=carry,
    )


def test_allocation_respects_budget_and_bounds():
    rs = _response_set()
    sc = optimize.run_scenario(rs, 1.0, 0.5, breakeven=1.0, n_per_draw=5, seed=0, name="same")
    assert abs(sc.recommended.sum() - rs.current.sum()) < 1e-6
    assert np.all(sc.recommended >= 0.5 * rs.current - 1e-9)
    assert np.all(sc.recommended <= 1.5 * rs.current + 1e-9)
    # money moves from the weak channel toward the strong one
    assert sc.recommended[0] > rs.current[0]
    assert sc.recommended[2] < rs.current[2]
    assert np.median(sc.gain) > 0


def test_decision_rule_holds_channels_below_breakeven():
    rs = _response_set()
    # an absurd breakeven means no increase can be justified
    sc = optimize.run_scenario(rs, 1.0, 0.5, breakeven=1e9, n_per_draw=5, seed=0, name="same")
    assert not sc.rule_holds["all_increases_pass_roas"] or not sc.rule_holds["recommend"]
    increased = [c for c, x, x0 in zip(rs.channels, sc.recommended, rs.current, strict=True)
                 if x > x0 * (1 + 1e-9)]
    assert not increased or not sc.rule_holds["recommend"]


def test_plus_budget_scenario_spends_the_extra_money():
    rs = _response_set()
    sc = optimize.run_scenario(rs, 1.25, 0.5, breakeven=1.0, n_per_draw=5, seed=0, name="plus")
    assert abs(sc.recommended.sum() - 1.25 * rs.current.sum()) < 1e-6
    table = optimize.reallocation_table(rs, sc)
    assert set(table["channel"]) == set(rs.channels)
    assert (table["marginal_roas_current_median"] > 0).all()


def test_response_set_without_carry_is_refused():
    rs = _response_set()
    with pytest.raises(ValueError, match="carry"):
        optimize.ResponseSet(rs.channels, rs.decay, rs.half_sat, rs.slope, rs.effect,
                             rs.spend_means, rs.revenue_mean, rs.current)


def test_extra_budget_with_every_channel_held_keeps_current_spend():
    rs = _response_set()
    # nothing clears an absurd breakeven, so no channel may grow and the extra has no home
    sc = optimize.run_scenario(rs, 1.25, 0.5, breakeven=1e9, n_per_draw=3, seed=0, name="plus")
    assert sorted(sc.rule_holds["held_channels"]) == sorted(rs.channels)
    assert np.all(sc.recommended <= rs.current + 1e-9)
    table = optimize.reallocation_table(rs, sc)
    held = table[table["held_by_rule"]]
    assert (held["recommended_spend"] <= held["current_spend"] + 1e-9).all()
    assert not sc.rule_holds["recommend"]


def test_next_budget_title_and_filename_follow_the_config():
    rs = _response_set()
    base = optimize.run_scenario(rs, 1.0, 0.5, breakeven=1.0, n_per_draw=2, seed=0, name="b")
    plus = optimize.run_scenario(rs, 1.4, 0.5, breakeven=1.0, n_per_draw=2, seed=0, name="p")
    note = optimize.next_budget_note(rs, base, plus, 0.4, 0.0, 1.4)
    assert note.startswith("# If the advertiser gets 40 percent more budget")
    assert optimize.next_budget_filename(200000) == "next_200k.md"
    assert optimize.next_budget_filename(150000) == "next_150k.md"
    assert optimize.next_budget_filename(0) == "next_budget.md"


def _layer_r_dir(tmp_path, rs):
    cols = {}
    for i, ch in enumerate(rs.channels):
        cols[f"decay__{ch}"] = rs.decay[:, i]
        cols[f"half_saturation__{ch}"] = rs.half_sat[:, i]
        cols[f"slope__{ch}"] = rs.slope[:, i]
        cols[f"effect__{ch}"] = rs.effect[:, i]
    src = tmp_path / "layer_r_out"
    src.mkdir()
    pd.DataFrame(cols).to_csv(src / "posterior_draws.csv", index=False)
    meta = {
        "channels": rs.channels,
        "spend_means": dict(zip(rs.channels, rs.spend_means.tolist(), strict=True)),
        "spend_mean_week": dict(zip(rs.channels, rs.current.tolist(), strict=True)),
        "revenue_mean": rs.revenue_mean,
        "adstock_length": 13,
    }
    (src / "model_data.json").write_text(json.dumps(meta))
    return src


def _config(tmp_path, **decision):
    cfg = load_config(None, "layer_r.yaml")
    cfg["output_dir"] = str(tmp_path / "not_used")
    cfg["decision"].update(posterior_draws=20, per_draw_optimisations=4,
                           extra_budget_per_year=0, **decision)
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_run_layer_d_reads_the_given_dir_and_honours_small_settings(tmp_path):
    rs = _response_set()
    src = _layer_r_dir(tmp_path, rs)
    out = tmp_path / "d"
    summary = optimize.run_layer_d(_config(tmp_path, bound_share=0.3), out, src)
    assert summary["posterior_draws_used"] == 20
    draws = pd.read_csv(out / "reallocation_gain_draws.csv")
    assert len(draws) == 20
    table = pd.read_csv(out / "reallocation_table.csv")
    same = table[table["scenario"] == "same_total"]
    assert (same["recommended_spend"] <= 1.3 * same["current_spend"] + 1e-6).all()
    note = (out / "next_budget.md").read_text()
    assert note.startswith("# If the advertiser gets 25 percent more budget")


def test_run_layer_d_scenario_names_come_from_the_config(tmp_path):
    rs = _response_set()
    src = _layer_r_dir(tmp_path, rs)
    renamed = {"scenarios": {"now": 1.0, "more": 1.1}}
    with pytest.raises(KeyError, match="base_scenario"):
        optimize.run_layer_d(_config(tmp_path, **renamed), tmp_path / "d1", src)
    summary = optimize.run_layer_d(
        _config(tmp_path, base_scenario="now", extra_scenario="more", **renamed),
        tmp_path / "d2", src,
    )
    assert summary["extra_budget_scenario"] == "more"
    assert set(summary) >= {"now", "more"}
