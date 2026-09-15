"""Posterior quantities: contributions, ROAS, recovery vs truth, holdout.

Implements: MD-080, MD-081, MD-082, VR-301…306 (five-channel adaptation, ADR-012),
VR-401. Uses the *model* transforms, never ``ambo.synth``'s adstock/Hill.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import arviz as az
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from ambo.config import (
    ADSTOCK_LENGTH,
    HDI_PROB,
    HOLDOUT_START_WEEK,
    RESPONSE_GRID_MAX_MULT,
    RESPONSE_GRID_POINTS,
)
from ambo.model import ScaleFactors, fourier_features
from ambo.transforms import adstock, adstock_steady_state_gain, hill, hill_marginal


@dataclass
class ChannelRecovery:
    channel: str
    true_avg_roas: float
    roas_median: float
    roas_hdi_low: float
    roas_hdi_high: float
    in_hdi: bool
    contribution_share_median: float
    half_life_median: float
    mae_pct: float


@dataclass
class RecoveryResult:
    channels: list[ChannelRecovery]
    spearman: float
    media_share_truth: float
    media_share_posterior_median: float
    media_share_delta: float
    half_life_rank_ok: bool
    vr303_median_mae_pct: float
    n_draws: int
    gates: dict[str, bool] = field(default_factory=dict)
    gate_detail: dict[str, str] = field(default_factory=dict)


def hdi_interval(values: np.ndarray, prob: float = HDI_PROB) -> tuple[float, float]:
    interval = np.asarray(az.hdi(np.asarray(values, dtype=float), hdi_prob=prob))
    return float(interval[0]), float(interval[1])


def stacked_posterior(idata: az.InferenceData) -> dict[str, np.ndarray]:
    """Map free/deterministic names to arrays with a leading ``draw`` axis."""
    post = idata.posterior
    out: dict[str, np.ndarray] = {}
    for name in post.data_vars:
        stacked = post[name].stack(sample=("chain", "draw"))
        values = np.asarray(stacked)
        # Move sample to axis 0.
        sample_axis = list(stacked.dims).index("sample")
        out[name] = np.moveaxis(values, sample_axis, 0)
    return out


def contribution_draws(
    spend_eur: dict[str, np.ndarray],
    draws: dict[str, np.ndarray],
    scales: ScaleFactors,
    *,
    length: int = ADSTOCK_LENGTH,
) -> dict[str, np.ndarray]:
    """Per-channel weekly contribution in euros, shape (n_draws, T)."""
    n_draws = draws["lam"].shape[0]
    contrib: dict[str, np.ndarray] = {}
    for index, channel in enumerate(scales.channels):
        x_scaled = spend_eur[channel] / scales.spend_means[channel]
        weekly = np.empty((n_draws, x_scaled.size), dtype=float)
        for draw in range(n_draws):
            adstocked = adstock(x_scaled, float(draws["lam"][draw, index]), length)
            saturated = hill(
                adstocked, float(draws["k"][draw, index]), float(draws["s"][draw, index])
            )
            weekly[draw] = draws["beta"][draw, index] * saturated * scales.revenue_mean
        contrib[channel] = weekly
    return contrib


def average_roas(
    contrib: dict[str, np.ndarray], spend_eur: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for channel, weekly in contrib.items():
        denom = float(np.asarray(spend_eur[channel], dtype=float).sum())
        out[channel] = weekly.sum(axis=1) / denom if denom > 0 else np.zeros(weekly.shape[0])
    return out


def compute_recovery(
    frame: pd.DataFrame,
    idata: az.InferenceData,
    scales: ScaleFactors,
    truth: dict[str, object],
    *,
    length: int = ADSTOCK_LENGTH,
) -> RecoveryResult:
    draws = stacked_posterior(idata)
    spend = {c: frame[f"spend_{c}"].to_numpy(dtype=float) for c in scales.channels}
    contrib = contribution_draws(spend, draws, scales, length=length)
    roas = average_roas(contrib, spend)
    revenue = frame["revenue"].to_numpy(dtype=float)
    rev_sum = float(revenue.sum())
    truth_channels = truth["channels"]
    assert isinstance(truth_channels, dict)
    rows: list[ChannelRecovery] = []
    maes: list[float] = []
    for index, channel in enumerate(scales.channels):
        true_roas = float(truth_channels[channel]["true_avg_roas"])
        samples = roas[channel]
        lo, hi = hdi_interval(samples)
        median = float(np.median(samples))
        share = contrib[channel].sum(axis=1) / rev_sum
        lam = draws["lam"][:, index]
        hl = np.log(0.5) / np.log(np.clip(lam, 1e-6, 0.999))
        mae = _curve_mae_pct(
            spend[channel], draws, scales, index, channel, truth_channels[channel], length
        )
        maes.append(mae)
        rows.append(
            ChannelRecovery(
                channel=channel,
                true_avg_roas=true_roas,
                roas_median=median,
                roas_hdi_low=lo,
                roas_hdi_high=hi,
                in_hdi=lo <= true_roas <= hi,
                contribution_share_median=float(np.median(share)),
                half_life_median=float(np.median(hl)),
                mae_pct=mae,
            )
        )
    true_roas_vec = [row.true_avg_roas for row in rows]
    med_roas_vec = [row.roas_median for row in rows]
    rho = float(spearmanr(true_roas_vec, med_roas_vec).statistic)
    media_share_draws = sum(contrib[c].sum(axis=1) for c in scales.channels) / rev_sum
    media_share_med = float(np.median(media_share_draws))
    media_truth = float(truth["media_share"])
    half_ok = _half_life_rank_ok(rows)
    result = RecoveryResult(
        channels=rows,
        spearman=rho,
        media_share_truth=media_truth,
        media_share_posterior_median=media_share_med,
        media_share_delta=media_share_med - media_truth,
        half_life_rank_ok=half_ok,
        vr303_median_mae_pct=float(np.median(maes)),
        n_draws=int(draws["lam"].shape[0]),
    )
    result.gates, result.gate_detail = _evaluate_gates(result)
    return result


def _curve_mae_pct(
    spend: np.ndarray,
    draws: dict[str, np.ndarray],
    scales: ScaleFactors,
    index: int,
    channel: str,
    truth_ch: dict[str, object],
    length: int,
) -> float:
    max_x = float(np.max(spend)) if np.max(spend) > 0 else 1.0
    grid = np.linspace(0.0, RESPONSE_GRID_MAX_MULT * max_x, RESPONSE_GRID_POINTS)
    true_x = np.asarray(truth_ch["response_curve_spend"], dtype=float)
    true_y = np.asarray(truth_ch["response_curve_contribution"], dtype=float)
    true_on_grid = np.interp(grid, true_x, true_y)
    n_draws = draws["lam"].shape[0]
    pred = np.empty((n_draws, grid.size), dtype=float)
    mean = scales.spend_means[channel]
    for draw in range(n_draws):
        pred[draw] = _steady_state_curve(
            grid,
            mean,
            float(draws["lam"][draw, index]),
            float(draws["k"][draw, index]),
            float(draws["s"][draw, index]),
            float(draws["beta"][draw, index]),
            scales.revenue_mean,
            length,
        )
    pred_mean = pred.mean(axis=0)
    denom = float(np.max(np.abs(true_on_grid))) if np.max(np.abs(true_on_grid)) > 0 else 1.0
    return float(np.mean(np.abs(pred_mean - true_on_grid)) / denom * 100.0)


def _steady_state_curve(
    spend_eur: np.ndarray,
    spend_mean: float,
    lam: float,
    k: float,
    slope: float,
    beta: float,
    revenue_mean: float,
    length: int,
) -> np.ndarray:
    gain = adstock_steady_state_gain(lam, length)
    adstocked = (spend_eur / spend_mean) * gain
    return beta * hill(adstocked, k, slope) * revenue_mean


def _half_life_rank_ok(rows: list[ChannelRecovery]) -> bool:
    """Offline (tv/print/radio) median half-lives should outrank paid_search."""
    by_name = {row.channel: row.half_life_median for row in rows}
    search = by_name.get("paid_search")
    if search is None:
        return False
    offline = [by_name[name] for name in ("tv", "radio", "print") if name in by_name]
    return bool(offline) and all(value > search for value in offline)


def _evaluate_gates(result: RecoveryResult) -> tuple[dict[str, bool], dict[str, str]]:
    """Five-channel adaptation of SPEC-05 §3 for the 156-week clean Layer P."""
    in_hdi = sum(1 for row in result.channels if row.in_hdi)
    n_ch = len(result.channels)
    g301 = in_hdi >= max(n_ch - 1, 1)
    g302 = result.spearman >= 0.70
    per_ok = all(row.mae_pct <= 25.0 for row in result.channels)
    g303 = per_ok and result.vr303_median_mae_pct <= 15.0
    g305 = result.half_life_rank_ok
    g306 = abs(result.media_share_delta) <= 0.10
    gates = {
        "VR-301": g301,
        "VR-302": g302,
        "VR-303": g303,
        "VR-305": g305,
        "VR-306": g306,
    }
    detail = {
        "VR-301": f"{in_hdi}/{n_ch} channels in 90% HDI (need ≥ {max(n_ch - 1, 1)})",
        "VR-302": f"Spearman {result.spearman:.3f} (need ≥ 0.70)",
        "VR-303": f"MAE% median {result.vr303_median_mae_pct:.2f} (median≤15, per≤25)",
        "VR-305": "offline half-lives rank above paid_search"
        if g305
        else "half-life ranking failed",
        "VR-306": f"|media share Δ|={abs(result.media_share_delta):.4f} (need ≤ 0.10)",
    }
    return gates, detail


def holdout_table(
    frame: pd.DataFrame,
    idata: az.InferenceData,
    scales: ScaleFactors,
    *,
    start_week: int = HOLDOUT_START_WEEK,
    length: int = ADSTOCK_LENGTH,
) -> pd.DataFrame:
    """Conditional forecast on weeks ``start_week``…T with actual spend (VR-401)."""
    n_weeks = len(frame)
    n_train = start_week - 1
    if n_train < 52 or n_train >= n_weeks:
        raise ValueError(f"holdout start_week={start_week} incompatible with T={n_weeks}")
    draws = stacked_posterior(idata)
    spend = {c: frame[f"spend_{c}"].to_numpy(dtype=float) for c in scales.channels}
    contrib = contribution_draws(spend, draws, scales, length=length)
    mu = _control_mean(frame, draws, scales) + sum(contrib.values())
    y = frame["revenue"].to_numpy(dtype=float)
    y_hold = y[n_train:]
    yhat = np.median(mu[:, n_train:], axis=0)
    sigma = draws["sigma"] * scales.revenue_mean
    rng = np.random.default_rng(0)
    y_rep = mu[:, n_train:] + rng.normal(size=mu[:, n_train:].shape) * sigma[:, None]
    lows = np.empty(n_weeks - n_train)
    highs = np.empty(n_weeks - n_train)
    for week in range(n_weeks - n_train):
        lows[week], highs[week] = hdi_interval(y_rep[:, week])
    naive = y[n_train - 52 : n_weeks - 52]
    covered = (y_hold >= lows) & (y_hold <= highs)
    return pd.DataFrame(
        {
            "week_start": pd.to_datetime(frame["week_start"])
            .iloc[n_train:]
            .dt.strftime("%Y-%m-%d")
            .to_numpy(),
            "revenue": y_hold,
            "yhat_median": yhat,
            "hdi_low": lows,
            "hdi_high": highs,
            "naive": naive,
            "covered": covered.astype(int),
            "model_mape": float(np.mean(np.abs(y_hold - yhat) / np.abs(y_hold))),
            "naive_mape": float(np.mean(np.abs(y_hold - naive) / np.abs(y_hold))),
            "coverage_90": float(covered.mean()),
        }
    )


def _control_mean(
    frame: pd.DataFrame, draws: dict[str, np.ndarray], scales: ScaleFactors
) -> np.ndarray:
    n_weeks = len(frame)
    t_over_t = np.arange(1, n_weeks + 1, dtype=float) / n_weeks
    sin_feat, cos_feat = fourier_features(n_weeks)
    holiday = frame["holiday_flag"].to_numpy(dtype=float)
    mu = np.outer(draws["alpha"], np.ones(n_weeks))
    mu = mu + np.outer(draws["tau"].ravel(), t_over_t)
    mu = mu + draws["gamma_sin"] @ sin_feat.T
    mu = mu + draws["gamma_cos"] @ cos_feat.T
    mu = mu + np.outer(draws["delta_holiday"].ravel(), holiday)
    for name, column in (
        ("delta_promo", "promo_flag"),
        ("delta_advent", "advent_flag"),
        ("delta_jan", "jan_dip_flag"),
    ):
        if name in draws and column in frame.columns:
            mu = mu + np.outer(draws[name].ravel(), frame[column].to_numpy(dtype=float))
    return mu * scales.revenue_mean


def marginal_roas_at_mean(
    spend_eur: np.ndarray,
    draws: dict[str, np.ndarray],
    scales: ScaleFactors,
    index: int,
    channel: str,
    *,
    length: int = ADSTOCK_LENGTH,
) -> np.ndarray:
    """Analytic d(contribution)/d(spend) at mean weekly spend, per draw."""
    mean_spend = float(np.mean(spend_eur[spend_eur > 0])) if np.any(spend_eur > 0) else 1.0
    n_draws = draws["lam"].shape[0]
    out = np.empty(n_draws)
    spend_mean = scales.spend_means[channel]
    for draw in range(n_draws):
        lam = float(draws["lam"][draw, index])
        gain = adstock_steady_state_gain(lam, length)
        a = (mean_spend / spend_mean) * gain
        deriv_h = hill_marginal(
            np.array([a]), float(draws["k"][draw, index]), float(draws["s"][draw, index])
        )[0]
        # d a / d x_eur = gain / spend_mean; contribution = beta * h * revenue_mean
        out[draw] = (
            draws["beta"][draw, index] * deriv_h * (gain / spend_mean) * scales.revenue_mean
        )
    return out


__all__ = [
    "ChannelRecovery",
    "RecoveryResult",
    "average_roas",
    "compute_recovery",
    "contribution_draws",
    "hdi_interval",
    "holdout_table",
    "marginal_roas_at_mean",
    "stacked_posterior",
]
