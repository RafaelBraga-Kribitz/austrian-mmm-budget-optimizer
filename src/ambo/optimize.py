"""Layer D: allocate a fixed weekly budget across channels on the Layer R posterior.

Objective, per posterior draw: the total weekly incremental revenue of a constant
weekly allocation, using the steady-state adstock and the Hill response of that
draw. The recommendation maximises the posterior mean of that objective (sample
average over the draws); its gain is then evaluated under every draw so the gain
has a distribution, not a point. The same optimisation is also run draw by draw
so the allocation itself has a distribution.

Constraints: the total equals the scenario budget; each channel stays within plus
or minus ``bound_share`` of its current average weekly spend (the extrapolation
guard). Solver: SLSQP with seeded restarts.

Decision rule (also stated in prose in the artifacts): shift budget toward a
channel only while the lower bound of its marginal ROAS 90 percent interval stays
above the breakeven ROAS, and only if the 10th percentile of the reallocation gain
is positive. Breakeven ROAS is 1 divided by the contribution margin in the config.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ambo.transforms import adstock_weights, hill, hill_marginal

LO, HI = 5, 95


@dataclass
class ResponseSet:
    """Posterior draws of the response parameters plus the scaling of the data."""

    channels: list[str]
    decay: np.ndarray  # (D, C)
    half_sat: np.ndarray  # (D, C)
    slope: np.ndarray  # (D, C)
    effect: np.ndarray  # (D, C)
    spend_means: np.ndarray  # (C,)
    revenue_mean: float
    current: np.ndarray  # (C,) current average weekly spend
    carry: np.ndarray = None  # (D, C) steady-state adstock multiplier

    def __post_init__(self):
        if self.carry is None:
            self.carry = np.zeros_like(self.decay)

    @property
    def n_draws(self) -> int:
        return int(self.decay.shape[0])

    def subset(self, n: int, seed: int = 0) -> ResponseSet:
        rng = np.random.default_rng(seed)
        idx = np.sort(rng.choice(self.n_draws, size=min(n, self.n_draws), replace=False))
        return ResponseSet(
            self.channels, self.decay[idx], self.half_sat[idx], self.slope[idx],
            self.effect[idx], self.spend_means, self.revenue_mean, self.current, self.carry[idx],
        )

    def contribution(self, x: np.ndarray) -> np.ndarray:
        """Weekly incremental revenue per draw and channel at constant spend x. (D, C)."""
        a = (np.asarray(x, dtype=float) / self.spend_means)[None, :] * self.carry
        return self.effect * hill(a, self.half_sat, self.slope) * self.revenue_mean

    def marginal(self, x: np.ndarray) -> np.ndarray:
        """Marginal ROAS per draw and channel: extra revenue per extra unit of weekly spend."""
        a = (np.asarray(x, dtype=float) / self.spend_means)[None, :] * self.carry
        da_dx = self.carry / self.spend_means[None, :]
        return self.effect * hill_marginal(a, self.half_sat, self.slope) * da_dx * self.revenue_mean


def load_response_set(layer_r_dir: Path) -> ResponseSet:
    layer_r_dir = Path(layer_r_dir)
    draws = pd.read_csv(layer_r_dir / "posterior_draws.csv")
    with open(layer_r_dir / "model_data.json", encoding="utf-8") as fh:
        meta = json.load(fh)
    channels = list(meta["channels"])

    def stack(name: str) -> np.ndarray:
        return np.column_stack([draws[f"{name}__{c}"].to_numpy() for c in channels])

    decay = stack("decay")
    length = int(meta["adstock_length"])
    carry = np.vectorize(lambda d: adstock_weights(d, length).sum())(decay)
    return ResponseSet(
        channels=channels,
        decay=decay,
        half_sat=stack("half_saturation"),
        slope=stack("slope"),
        effect=stack("effect"),
        spend_means=np.array([meta["spend_means"][c] for c in channels]),
        revenue_mean=float(meta["revenue_mean"]),
        current=np.array([meta["spend_mean_week"][c] for c in channels]),
        carry=carry,
    )


# ---------------------------------------------------------------------------
# Optimisation
# ---------------------------------------------------------------------------


def _solve(rs: ResponseSet, total: float, lower: np.ndarray, upper: np.ndarray,
           seed: int = 0, restarts: int = 8) -> np.ndarray:
    """Maximise the mean contribution over the draws of ``rs`` under the constraints."""
    rng = np.random.default_rng(seed)
    n = len(rs.channels)

    def objective(x):
        return -float(rs.contribution(x).sum(axis=1).mean())

    def gradient(x):
        return -rs.marginal(x).mean(axis=0)

    cons = [{"type": "eq", "fun": lambda x: x.sum() - total, "jac": lambda x: np.ones(n)}]
    bounds = list(zip(lower, upper, strict=True))
    best_x, best_f = None, np.inf
    starts = [np.clip(rs.current * total / rs.current.sum(), lower, upper)]
    for _ in range(restarts - 1):
        w = rng.dirichlet(np.ones(n))
        starts.append(lower + w * (upper - lower))
    for x0 in starts:
        x0 = _project(x0, total, lower, upper)
        res = minimize(objective, x0, jac=gradient, bounds=bounds, constraints=cons,
                       method="SLSQP", options={"maxiter": 300, "ftol": 1e-10})
        if res.fun < best_f and abs(res.x.sum() - total) < 1e-6 * max(total, 1.0):
            best_x, best_f = res.x, res.fun
    if best_x is None:
        raise RuntimeError("SLSQP found no feasible allocation")
    return np.clip(best_x, lower, upper)


def _project(x: np.ndarray, total: float, lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    """Scale a start point onto the budget plane inside the box (simple iterative fix)."""
    x = np.clip(x, lower, upper)
    for _ in range(50):
        gap = total - x.sum()
        if abs(gap) < 1e-9:
            break
        room = (upper - x) if gap > 0 else (x - lower)
        if room.sum() <= 0:
            break
        x = x + gap * room / room.sum()
        x = np.clip(x, lower, upper)
    return x


@dataclass
class Scenario:
    name: str
    total: float
    recommended: np.ndarray
    gain: np.ndarray  # per draw, weekly revenue units
    contribution_current: np.ndarray  # per draw
    contribution_recommended: np.ndarray  # per draw
    per_draw_allocations: np.ndarray  # (n, C)
    rule_holds: dict


def run_scenario(rs: ResponseSet, multiplier: float, bound_share: float, breakeven: float,
                 n_per_draw: int, seed: int, name: str) -> Scenario:
    total = float(rs.current.sum() * multiplier)
    lower = rs.current * (1.0 - bound_share)
    upper = rs.current * (1.0 + bound_share)
    if multiplier > 1.0:
        # a bigger budget may lift every channel by up to the extra share on top
        upper = rs.current * (1.0 + bound_share + (multiplier - 1.0))
    x_star = _solve(rs, total, lower, upper, seed=seed)
    x_star, rule = apply_decision_rule(rs, x_star, total, lower, upper, breakeven, seed)
    contrib_now = rs.contribution(rs.current).sum(axis=1)
    contrib_star = rs.contribution(x_star).sum(axis=1)
    gain = contrib_star - contrib_now
    sub = rs.subset(n_per_draw, seed=seed)
    per_draw = np.empty((sub.n_draws, len(rs.channels)))
    for d in range(sub.n_draws):
        single = ResponseSet(
            rs.channels, sub.decay[d : d + 1], sub.half_sat[d : d + 1], sub.slope[d : d + 1],
            sub.effect[d : d + 1], rs.spend_means, rs.revenue_mean, rs.current,
            sub.carry[d : d + 1],
        )
        per_draw[d] = _solve(single, total, lower, upper, seed=seed + d, restarts=3)
    rule["gain_p10_positive"] = bool(np.percentile(gain, 10) > 0)
    rule["recommend"] = bool(rule["gain_p10_positive"] and rule["all_increases_pass_roas"])
    return Scenario(name, total, x_star, gain, contrib_now, contrib_star, per_draw, rule)


def apply_decision_rule(rs: ResponseSet, x: np.ndarray, total: float, lower: np.ndarray,
                        upper: np.ndarray, breakeven: float, seed: int):
    """Hold any channel whose increase is not backed by the lower bound of its marginal ROAS.

    Repeats the optimisation with that channel capped at its current spend until every
    remaining increase passes. Records which channels were held and why.
    """
    held: list[str] = []
    upper = upper.copy()
    for _ in range(len(rs.channels) + 1):
        marg_lo = np.percentile(rs.marginal(x), LO, axis=0)
        failing = [
            i for i in range(len(rs.channels))
            if x[i] > rs.current[i] * (1 + 1e-9) and marg_lo[i] <= breakeven
            and rs.channels[i] not in held
        ]
        if not failing:
            break
        for i in failing:
            held.append(rs.channels[i])
            upper[i] = rs.current[i]
        if np.all(upper <= rs.current + 1e-9) and total > rs.current.sum() + 1e-9:
            break  # nothing may grow, the extra budget has no home under the rule
        x = _solve(rs, min(total, upper.sum()), lower, upper, seed=seed)
    increases = [i for i in range(len(rs.channels)) if x[i] > rs.current[i] * (1 + 1e-9)]
    marg_lo = np.percentile(rs.marginal(x), LO, axis=0)
    return x, {
        "breakeven_roas": breakeven,
        "held_channels": held,
        "all_increases_pass_roas": bool(all(marg_lo[i] > breakeven for i in increases)),
    }


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


def reallocation_table(rs: ResponseSet, sc: Scenario) -> pd.DataFrame:
    m_now = rs.marginal(rs.current)
    m_star = rs.marginal(sc.recommended)
    c_star = rs.contribution(sc.recommended)
    c_now = rs.contribution(rs.current)
    rows = []
    for i, ch in enumerate(rs.channels):
        rows.append(
            {
                "scenario": sc.name,
                "channel": ch,
                "current_spend": float(rs.current[i]),
                "recommended_spend": float(sc.recommended[i]),
                "delta": float(sc.recommended[i] - rs.current[i]),
                "delta_pct": float(100.0 * (sc.recommended[i] / rs.current[i] - 1.0)),
                "share_current": float(rs.current[i] / rs.current.sum()),
                "share_recommended": float(sc.recommended[i] / sc.recommended.sum()),
                "marginal_roas_current_median": float(np.median(m_now[:, i])),
                "marginal_roas_current_lo": float(np.percentile(m_now[:, i], LO)),
                "marginal_roas_current_hi": float(np.percentile(m_now[:, i], HI)),
                "marginal_roas_recommended_median": float(np.median(m_star[:, i])),
                "marginal_roas_recommended_lo": float(np.percentile(m_star[:, i], LO)),
                "marginal_roas_recommended_hi": float(np.percentile(m_star[:, i], HI)),
                "contribution_current_median": float(np.median(c_now[:, i])),
                "contribution_recommended_median": float(np.median(c_star[:, i])),
                "contribution_recommended_lo": float(np.percentile(c_star[:, i], LO)),
                "contribution_recommended_hi": float(np.percentile(c_star[:, i], HI)),
                "per_draw_share_median": float(np.median(sc.per_draw_allocations[:, i]
                                                         / sc.per_draw_allocations.sum(axis=1))),
                "held_by_rule": ch in sc.rule_holds["held_channels"],
            }
        )
    return pd.DataFrame(rows)


def gain_summary(sc: Scenario) -> dict:
    g = sc.gain
    rel = g / sc.contribution_current
    return {
        "scenario": sc.name,
        "total_budget": sc.total,
        "gain_median": float(np.median(g)),
        "gain_p10": float(np.percentile(g, 10)),
        "gain_p90": float(np.percentile(g, 90)),
        "gain_pct_of_current_contribution_median": float(100 * np.median(rel)),
        "gain_pct_of_current_contribution_p10": float(100 * np.percentile(rel, 10)),
        "probability_gain_negative": float(np.mean(g < 0)),
        "recommend": sc.rule_holds["recommend"],
        "held_channels": sc.rule_holds["held_channels"],
        "breakeven_roas": sc.rule_holds["breakeven_roas"],
    }


RULE_SENTENCE = (
    "Shift budget toward a channel only while the lower bound of its marginal ROAS 90 percent "
    "interval stays above the breakeven ROAS, and only if the 10th percentile of the "
    "reallocation gain is positive."
)


def next_budget_note(rs: ResponseSet, base: Scenario, plus: Scenario, margin: float,
                     extra_year: float = 0.0) -> str:
    extra = plus.total - base.total
    delta = plus.recommended - rs.current
    inc = np.maximum(delta, 0)
    shares = inc / inc.sum() if inc.sum() > 0 else np.zeros_like(inc)
    m_plus = rs.marginal(plus.recommended)
    best = int(np.argmax(np.median(m_plus, axis=0)))
    ranks_best = np.argmax(m_plus, axis=1)
    p_wrong_channel = float(np.mean(ranks_best != best))
    gain_extra = plus.gain - base.gain
    if extra_year > 0:
        title = f"# If the advertiser gets {extra_year:,.0f} more per year, where does it go?"
        framing = (
            f"The extra budget is spread evenly over 52 weeks ({extra:,.0f} per week on top of "
            f"the current {base.total:,.0f} per week, a {100 * (plus.total / base.total - 1):.1f} "
            f"percent increase). Money is in the dataset's units; the same rule applies to euros "
            f"once euro-denominated data is used."
        )
    else:
        title = "# If the advertiser gets 25 percent more budget, where does it go?"
        framing = (
            f"Current weekly budget: {base.total:,.3f}. Scenario budget: {plus.total:,.3f} "
            f"(extra {extra:,.3f})."
        )
    lines = [
        title,
        "",
        "Numbers come from the Layer R posterior (reports/layer_r/posterior_draws.csv) through "
        "python -m ambo.run layer_d.",
        "",
        framing,
        "",
        "## Where the extra budget goes",
        "",
    ]
    for i, ch in enumerate(rs.channels):
        lines.append(
            f"- {ch}: {100 * shares[i]:.0f} percent of the increase "
            f"(from {rs.current[i]:,.0f} to {plus.recommended[i]:,.0f} per week); "
            f"marginal ROAS at the new spend {np.median(m_plus[:, i]):.2f} "
            f"(90 percent interval {np.percentile(m_plus[:, i], LO):.2f} to "
            f"{np.percentile(m_plus[:, i], HI):.2f})."
        )
    lines += [
        "",
        "## How likely is this call wrong?",
        "",
        f"- Probability that the extra budget adds less than nothing: "
        f"{100 * np.mean(gain_extra < 0):.1f} percent.",
        f"- Probability that {rs.channels[best]} is not the channel with the highest marginal "
        f"return at the new allocation: {100 * p_wrong_channel:.1f} percent.",
        f"- Breakeven ROAS at a contribution margin of {100 * margin:.0f} percent: "
        f"{1 / margin:.2f}. Channels held at current spend by the rule: "
        f"{', '.join(plus.rule_holds['held_channels']) or 'none'}.",
        "- Verdict under the decision rule: "
        f"{'recommend' if plus.rule_holds['recommend'] else 'hold'}.",
        "",
        "## Decision rule",
        "",
        RULE_SENTENCE,
        "",
    ]
    return "\n".join(lines)


def run_layer_d(config_path=None, out_dir=None) -> dict:
    from ambo.plots import charts
    from ambo.run import load_config

    t_start = time.time()
    config = load_config(config_path, "layer_r.yaml")
    dec = config["decision"]
    layer_r_dir = Path(config["output_dir"])
    out = Path(out_dir or "reports/layer_d")
    out.mkdir(parents=True, exist_ok=True)
    rs_full = load_response_set(layer_r_dir)
    rs = rs_full.subset(int(dec["posterior_draws"]), seed=int(config["sampling"]["seed"]))
    margin = float(dec["contribution_margin"])
    breakeven = 1.0 / margin
    seed = int(config["sampling"]["seed"])
    multipliers = {name: float(mult) for name, mult in dec["scenarios"].items()}
    extra_year = float(dec.get("extra_budget_per_year", 0) or 0)
    if extra_year > 0:
        weekly_total = float(rs.current.sum())
        multipliers["plus_extra_budget"] = 1.0 + (extra_year / 52.0) / weekly_total
    scenarios = {}
    for name, mult in multipliers.items():
        scenarios[name] = run_scenario(
            rs, mult, float(dec["bound_share"]), breakeven,
            n_per_draw=max(200, int(dec.get("per_draw_optimisations", 200))), seed=seed,
            name=name,
        )
    base = scenarios["same_total"]
    plus = scenarios.get("plus_extra_budget", scenarios["plus_25_percent"])
    table = pd.concat([reallocation_table(rs, sc) for sc in scenarios.values()], ignore_index=True)
    table.to_csv(out / "reallocation_table.csv", index=False, lineterminator="\n")
    gains = pd.DataFrame({name: sc.gain for name, sc in scenarios.items()})
    gains.to_csv(out / "reallocation_gain_draws.csv", index=False, lineterminator="\n")
    summary = {name: gain_summary(sc) for name, sc in scenarios.items()}
    summary["decision_rule"] = RULE_SENTENCE
    summary["extra_budget_per_year"] = extra_year
    summary["extra_budget_scenario"] = plus.name
    summary["contribution_margin"] = margin
    summary["breakeven_roas"] = breakeven
    summary["posterior_draws_used"] = rs.n_draws
    summary["elapsed_seconds"] = round(time.time() - t_start, 1)
    with open(out / "decision.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
        fh.write("\n")
    source = f"{config['title']}; python -m ambo.run layer_d"
    charts.reallocation_gain(base.gain, base.contribution_current, out / "reallocation_gain.png",
                             source)
    (out / "next_200k.md").write_text(
        next_budget_note(rs, base, plus, margin, extra_year), encoding="utf-8"
    )
    return summary
