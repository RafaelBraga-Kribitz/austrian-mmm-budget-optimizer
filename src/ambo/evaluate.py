"""Evaluation: parameter and contribution recovery, attribution gap, holdout protocol.

Every table here is what the README and the charts read. Money is in the units of
the input data (euros for Layer P). Intervals are 5th to 95th percentile of the
posterior draws, a 90 percent interval.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ambo import baselines, model
from ambo.model import ModelData, Posterior

LO, HI = 5, 95


def _q(a: np.ndarray, axis=0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.percentile(a, 50, axis=axis),
        np.percentile(a, LO, axis=axis),
        np.percentile(a, HI, axis=axis),
    )


# ---------------------------------------------------------------------------
# Parameter recovery
# ---------------------------------------------------------------------------


def parameter_recovery(post: Posterior, md: ModelData, truth: dict) -> pd.DataFrame:
    """True value versus posterior median and 90 percent interval for every parameter.

    Half-saturation is compared as a multiple of the channel's average positive
    weekly spend, which is the unit the model works in; money parameters are
    compared in money units.
    """
    rows = []
    rev = md.revenue_mean
    d = post.draws
    for i, ch in enumerate(md.channels):
        ct = truth["channel_truth"][ch]
        rows.append(_row("Adstock decay", ch, ch, "share carried to next week",
                         ct["decay"], d["decay"][:, i]))
    for i, ch in enumerate(md.channels):
        ct = truth["channel_truth"][ch]
        rows.append(_row("Saturation", f"{ch} half-saturation", ch,
                         "multiple of average weekly spend",
                         ct["half_saturation"] / md.spend_means[i], d["half_saturation"][:, i]))
    for i, ch in enumerate(md.channels):
        ct = truth["channel_truth"][ch]
        rows.append(_row("Saturation", f"{ch} slope", ch, "Hill slope",
                         ct["slope"], d["slope"][:, i]))
    for i, ch in enumerate(md.channels):
        ct = truth["channel_truth"][ch]
        rows.append(_row("Coefficients", f"{ch} effect", ch, "money per week",
                         ct["effect"], d["effect"][:, i] * rev))
    base = truth["baseline"]
    rows.append(_row("Coefficients", "Baseline level", "", "money per week",
                     base["intercept"], d["intercept"] * rev))
    rows.append(_row("Coefficients", "Trend over the window", "", "money per week",
                     base["trend"], d["trend"] * rev))
    seas = base["seasonality"]
    for j in range(md.fourier_order):
        rows.append(_row("Coefficients", f"Season sine {j + 1}", "", "money per week",
                         seas[2 * j], d["seasonality_sin"][:, j] * rev))
        rows.append(_row("Coefficients", f"Season cosine {j + 1}", "", "money per week",
                         seas[2 * j + 1], d["seasonality_cos"][:, j] * rev))
    rows.append(_row("Coefficients", md.control_name, "", "money per week",
                     base["control"], d["control"] * rev))
    rows.append(_row("Coefficients", "Noise (standard deviation)", "", "money per week",
                     base["noise_sigma"], d["noise"] * rev))
    table = pd.DataFrame(rows)
    table["covered"] = (table["true"] >= table["lo"]) & (table["true"] <= table["hi"])
    return table


def _row(family: str, label: str, channel: str, unit: str, true: float, draws: np.ndarray) -> dict:
    med, lo, hi = _q(draws)
    return {
        "family": family,
        "parameter": label,
        "channel": channel,
        "unit": unit,
        "true": float(true),
        "median": float(med),
        "lo": float(lo),
        "hi": float(hi),
    }


# ---------------------------------------------------------------------------
# Contributions and attribution gap
# ---------------------------------------------------------------------------


def contribution_recovery(
    contribs: np.ndarray, md: ModelData, truth: dict
) -> pd.DataFrame:
    """True versus estimated share of revenue and ROAS per channel."""
    total_revenue = float(md.revenue.sum())
    totals = contribs.sum(axis=1)  # (S, C)
    rows = []
    for i, ch in enumerate(md.channels):
        ct = truth["channel_truth"][ch]
        share = totals[:, i] / total_revenue
        spend_total = float(md.spend[:, i].sum())
        roas = totals[:, i] / spend_total if spend_total > 0 else np.zeros(totals.shape[0])
        s_med, s_lo, s_hi = _q(share)
        r_med, r_lo, r_hi = _q(roas)
        rows.append(
            {
                "channel": ch,
                "true_share_of_revenue": ct["contribution_share_of_revenue"],
                "share_median": float(s_med),
                "share_lo": float(s_lo),
                "share_hi": float(s_hi),
                "true_roas": ct["roas"],
                "roas_median": float(r_med),
                "roas_lo": float(r_lo),
                "roas_hi": float(r_hi),
                "spend_total": spend_total,
            }
        )
    table = pd.DataFrame(rows)
    table["covered"] = (table["true_share_of_revenue"] >= table["share_lo"]) & (
        table["true_share_of_revenue"] <= table["share_hi"]
    )
    return table


def attribution_gap(
    data: pd.DataFrame, contribs: np.ndarray, md: ModelData, truth: dict
) -> pd.DataFrame:
    """Platform-reported share of attributed revenue versus true incremental share.

    Channels without platform reporting (offline media) get zero platform credit,
    which is what a last-touch dashboard shows for them.
    """
    platform_totals = {}
    for ch in md.channels:
        col = f"platform_{ch}"
        platform_totals[ch] = float(data[col].sum()) if col in data.columns else 0.0
    platform_sum = sum(platform_totals.values())
    est_totals = contribs.sum(axis=1)  # (S, C)
    est_share = est_totals / est_totals.sum(axis=1, keepdims=True)
    rows = []
    for i, ch in enumerate(md.channels):
        ct = truth["channel_truth"][ch]
        platform_share = platform_totals[ch] / platform_sum if platform_sum > 0 else 0.0
        true_share = ct["contribution_share_of_media"]
        e_med, e_lo, e_hi = _q(est_share[:, i])
        rows.append(
            {
                "channel": ch,
                "platform_share": platform_share,
                "true_share": true_share,
                "gap_pp": 100.0 * (platform_share - true_share),
                "abs_gap_pp": abs(100.0 * (platform_share - true_share)),
                "estimated_share_median": float(e_med),
                "estimated_share_lo": float(e_lo),
                "estimated_share_hi": float(e_hi),
                "platform_reported_total": platform_totals[ch],
                "true_contribution_total": ct["contribution_total"],
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Holdout
# ---------------------------------------------------------------------------


def holdout(
    data: pd.DataFrame, config: dict
) -> tuple[pd.DataFrame, pd.DataFrame, dict, object]:
    """Fit on the first ``train_weeks`` rows, forecast the rest with actual spend.

    Returns the metrics table (one row per model), the week-level predictions,
    the fit record and the holdout InferenceData for diagnostics.
    """
    train_weeks = int(config["holdout"]["train_weeks"])
    md_full = model.prepare(data, config, train_weeks=train_weeks)
    md_train = md_full.slice(0, train_weeks)
    idata, info, diag = model.fit_with_ladder(md_train, config)
    info = dict(info, diagnostics=diag)
    post = model.extract(idata)
    mu, yrep = model.predict(post, md_full, seed=int(config["sampling"]["seed"]))
    mu_test, yrep_test = mu[:, train_weeks:], yrep[:, train_weeks:]
    actual = md_full.revenue[train_weeks:]
    mmm = baselines.Forecast(
        "Bayesian MMM",
        np.median(mu_test, axis=0),
        np.percentile(yrep_test, LO, axis=0),
        np.percentile(yrep_test, HI, axis=0),
    )
    naive = baselines.seasonal_naive(md_full.revenue, train_weeks)
    ridge = baselines.ridge(
        data,
        md_full.channels,
        config["control"]["column"],
        train_weeks,
        [float(a) for a in config["holdout"]["ridge_alphas"]],
    )
    forecasts = [naive, ridge, mmm]
    metrics = pd.DataFrame([f.metrics(actual) for f in forecasts])
    metrics["train_weeks"] = train_weeks
    preds = pd.DataFrame(
        {
            "week": md_full.weeks[train_weeks:],
            "week_start": md_full.week_start[train_weeks:] if md_full.week_start else "",
            "actual": actual,
        }
    )
    for f in forecasts:
        key = f.name.split(" (")[0].lower().replace(" ", "_")
        preds[f"{key}_yhat"] = f.yhat
        preds[f"{key}_lo"] = f.lo
        preds[f"{key}_hi"] = f.hi
    return metrics, preds, info, idata
