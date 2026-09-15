"""Optimiser: budget constraint, bounds, and the decision rule on a made-up posterior."""

import numpy as np

from ambo import optimize


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
