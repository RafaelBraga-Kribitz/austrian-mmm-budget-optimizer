"""Budget optimiser: SLSQP over posterior draws at constant-spend steady state.

Implements: DC-201…DC-205, DC-301. No brand-search line on this five-channel
mix (STATUS §12), so every channel is reallocatable. Offline channels move in
weekly-equivalent euros; real flighting granularity is a caption, not a constraint.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from ambo.config import (
    ADSTOCK_LENGTH,
    CHANNEL_IDS,
    EXTRAPOLATION_MULT,
    OPTIMIZER_DRAWS,
    OPTIMIZER_RESTARTS,
    SAMPLER_SEED,
)
from ambo.evaluate import hdi_interval
from ambo.model import ScaleFactors
from ambo.transforms import hill


@dataclass(frozen=True)
class Allocation:
    spends: dict[str, float]
    expected_contribution: float
    contribution_hdi: tuple[float, float]
    historical: dict[str, float]
    gain_vs_historical: float
    gain_hdi: tuple[float, float]
    binding: dict[str, bool]
    restart_spread: float


def _ss_factor(lam: float, length: int) -> float:
    return float(np.sum(lam ** np.arange(length)))


def contribution_ss(
    spend_eur: np.ndarray,
    lam: np.ndarray,
    k: np.ndarray,
    slope: np.ndarray,
    beta: np.ndarray,
    spend_means: np.ndarray,
    revenue_mean: float,
    *,
    length: int = ADSTOCK_LENGTH,
) -> np.ndarray:
    """Media contribution (euros / week) at constant spend, one draw, all channels."""
    total = 0.0
    for i, x in enumerate(spend_eur):
        adstocked = (x / spend_means[i]) * _ss_factor(float(lam[i]), length)
        total = total + float(beta[i]) * float(
            hill(np.array([adstocked]), float(k[i]), float(slope[i]))[0]
        )
    return np.array([total * revenue_mean])


def _objective_factory(
    lam: np.ndarray,
    k: np.ndarray,
    slope: np.ndarray,
    beta: np.ndarray,
    spend_means: np.ndarray,
    revenue_mean: float,
    length: int,
):
    n_used = lam.shape[0]

    def objective(x: np.ndarray) -> float:
        acc = 0.0
        for draw in range(n_used):
            acc += float(
                contribution_ss(
                    x,
                    lam[draw],
                    k[draw],
                    slope[draw],
                    beta[draw],
                    spend_means,
                    revenue_mean,
                    length=length,
                )[0]
            )
        return -acc / n_used

    return objective


def optimize_budget(
    historical_weekly: np.ndarray,
    max_weekly: np.ndarray,
    draws: dict[str, np.ndarray],
    scales: ScaleFactors,
    *,
    budget_mult: float = 1.0,
    n_draws: int = OPTIMIZER_DRAWS,
    n_restarts: int = OPTIMIZER_RESTARTS,
    seed: int = SAMPLER_SEED,
    length: int = ADSTOCK_LENGTH,
) -> Allocation:
    """Max expected media contribution s.t. sum x = B and 0 ≤ x ≤ 1.3× max observed."""
    channels = scales.channels
    n_ch = len(channels)
    B = float(historical_weekly.sum() * budget_mult)
    upper = EXTRAPOLATION_MULT * max_weekly
    lam = draws["lam"][:n_draws]
    k = draws["k"][:n_draws]
    slope = draws["s"][:n_draws]
    beta = draws["beta"][:n_draws]
    means = np.array([scales.spend_means[c] for c in channels], dtype=float)
    objective = _objective_factory(lam, k, slope, beta, means, scales.revenue_mean, length)
    bounds = [(0.0, float(upper[i])) for i in range(n_ch)]
    constraints = {"type": "eq", "fun": lambda x, b=B: float(x.sum() - b)}
    rng = np.random.default_rng(seed)
    best_x = historical_weekly * budget_mult
    best_val = objective(best_x)
    values = [best_val]
    for _ in range(n_restarts):
        raw = rng.dirichlet(np.ones(n_ch)) * B
        clipped = np.minimum(raw, upper)
        if clipped.sum() <= 0:
            continue
        x0 = clipped * (B / clipped.sum())
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 200, "ftol": 1e-9},
        )
        if not result.success:
            continue
        values.append(float(result.fun))
        if result.fun < best_val:
            best_val = float(result.fun)
            best_x = np.asarray(result.x, dtype=float)
    contrib_star = _eval_all_draws(best_x, draws, means, scales.revenue_mean, length)
    contrib_hist = _eval_all_draws(historical_weekly, draws, means, scales.revenue_mean, length)
    gain = contrib_star - contrib_hist
    binding = {channels[i]: bool(best_x[i] >= 0.999 * upper[i]) for i in range(n_ch)}
    spread = float(np.ptp(values) / max(abs(best_val), 1e-9))
    return Allocation(
        spends={channels[i]: float(best_x[i]) for i in range(n_ch)},
        expected_contribution=float(np.mean(contrib_star)),
        contribution_hdi=hdi_interval(contrib_star),
        historical={channels[i]: float(historical_weekly[i]) for i in range(n_ch)},
        gain_vs_historical=float(np.mean(gain)),
        gain_hdi=hdi_interval(gain),
        binding=binding,
        restart_spread=spread,
    )


def _eval_all_draws(
    x: np.ndarray,
    draws: dict[str, np.ndarray],
    means: np.ndarray,
    revenue_mean: float,
    length: int,
) -> np.ndarray:
    n_draws = draws["lam"].shape[0]
    out = np.empty(n_draws)
    for draw in range(n_draws):
        out[draw] = float(
            contribution_ss(
                x,
                draws["lam"][draw],
                draws["k"][draw],
                draws["s"][draw],
                draws["beta"][draw],
                means,
                revenue_mean,
                length=length,
            )[0]
        )
    return out


def historical_means(frame, channels: tuple[str, ...] = CHANNEL_IDS) -> np.ndarray:
    return np.array([frame[f"spend_{c}"].to_numpy(dtype=float).mean() for c in channels])


def historical_max(frame, channels: tuple[str, ...] = CHANNEL_IDS) -> np.ndarray:
    return np.array([frame[f"spend_{c}"].to_numpy(dtype=float).max() for c in channels])
