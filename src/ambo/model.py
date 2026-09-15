"""Raw PyMC MMM: geometric adstock, Hill saturation, trend, Fourier, one control.

Implements: MD-001, MD-002, MD-020, MD-021, MD-030, MD-040, MD-050, ADR-005
(non-centred Fourier). Sampler: nutpie with PyMC NUTS fallback (STATUS D-08).

The builder has no scenario branches. Channel list + scaled data are the knobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import pymc as pm

from ambo.config import (
    ADSTOCK_LENGTH,
    ALPHA_MU,
    ALPHA_SIGMA,
    BETA_SIGMA,
    CHANNEL_IDS,
    DELTA_HOLIDAY_MU,
    DELTA_HOLIDAY_SIGMA,
    FOURIER_ORDER,
    FOURIER_PERIOD_WEEKS,
    GAMMA_SIGMA,
    K_RATE,
    K_SHAPE,
    LAM_A,
    LAM_B,
    S_LOWER,
    S_RATE,
    S_SHAPE,
    S_UPPER,
    SAMPLER_CHAINS,
    SAMPLER_DRAWS,
    SAMPLER_SEED,
    SAMPLER_TUNE,
    SIGMA_SIGMA,
    TARGET_ACCEPT,
    TAU_SIGMA,
)
from ambo.transforms import adstock_pt, hill_pt


@dataclass(frozen=True)
class ScaleFactors:
    """MD-030 scale pair. Reporting code back-transforms with these only."""

    revenue_mean: float
    spend_means: dict[str, float]
    channels: tuple[str, ...]


def scale_frame(
    df: pd.DataFrame, channels: tuple[str, ...] = CHANNEL_IDS
) -> tuple[pd.DataFrame, ScaleFactors]:
    """Divide revenue by its mean and each spend series by its nonzero mean."""
    if df.empty:
        raise ValueError("scale_frame: empty frame")
    revenue = df["revenue"].to_numpy(dtype=float)
    revenue_mean = float(np.mean(revenue))
    if revenue_mean <= 0:
        raise ValueError("scale_frame: revenue mean must be positive")
    out = df.copy()
    out["revenue"] = revenue / revenue_mean
    spend_means: dict[str, float] = {}
    for channel in channels:
        col = f"spend_{channel}"
        x = df[col].to_numpy(dtype=float)
        nonzero = x[x > 0]
        mean = float(np.mean(nonzero)) if nonzero.size else 1.0
        if mean <= 0:
            mean = 1.0
        spend_means[channel] = mean
        out[col] = x / mean
    factors = ScaleFactors(
        revenue_mean=revenue_mean, spend_means=spend_means, channels=tuple(channels)
    )
    return out, factors


def fourier_features(n_weeks: int) -> tuple[np.ndarray, np.ndarray]:
    """sin/cos design, shape (T, 4), t = 1…T (SPEC-04 §2)."""
    t = np.arange(1, n_weeks + 1, dtype=float)
    orders = np.arange(1, FOURIER_ORDER + 1, dtype=float)
    angle = 2.0 * np.pi * np.outer(t, orders) / FOURIER_PERIOD_WEEKS
    return np.sin(angle), np.cos(angle)


def fourier_features_for_weeks(t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    orders = np.arange(1, FOURIER_ORDER + 1, dtype=float)
    angle = 2.0 * np.pi * np.outer(np.asarray(t, dtype=float), orders) / FOURIER_PERIOD_WEEKS
    return np.sin(angle), np.cos(angle)


def build_model(
    df: pd.DataFrame,
    channels: tuple[str, ...] = CHANNEL_IDS,
    *,
    adstock_length: int = ADSTOCK_LENGTH,
) -> pm.Model:
    """SPEC-04 §2 on already-scaled data (MD-002). One holiday control (STATUS §6)."""
    _require(df, channels)
    n_weeks = int(len(df))
    n_channels = len(channels)
    sin_feat, cos_feat = fourier_features(n_weeks)
    t_over_t = np.arange(1, n_weeks + 1, dtype=float) / n_weeks
    spend = np.column_stack([df[f"spend_{c}"].to_numpy(dtype=float) for c in channels])
    holiday = df["holiday_flag"].to_numpy(dtype=float)
    y_obs = df["revenue"].to_numpy(dtype=float)
    coords = {
        "channel": list(channels),
        "week": list(range(n_weeks)),
        "fourier": list(range(1, FOURIER_ORDER + 1)),
    }
    with pm.Model(coords=coords) as model:
        spend_data = pm.Data("spend", spend, dims=("week", "channel"))
        alpha = pm.Normal("alpha", mu=ALPHA_MU, sigma=ALPHA_SIGMA, initval=ALPHA_MU)
        tau = pm.Normal("tau", mu=0.0, sigma=TAU_SIGMA, initval=0.0)
        g_sin_off = pm.Normal("gamma_sin_offset", mu=0.0, sigma=1.0, dims="fourier")
        g_cos_off = pm.Normal("gamma_cos_offset", mu=0.0, sigma=1.0, dims="fourier")
        gamma_sin = pm.Deterministic("gamma_sin", g_sin_off * GAMMA_SIGMA, dims="fourier")
        gamma_cos = pm.Deterministic("gamma_cos", g_cos_off * GAMMA_SIGMA, dims="fourier")
        delta_holiday = pm.Normal(
            "delta_holiday",
            mu=DELTA_HOLIDAY_MU,
            sigma=DELTA_HOLIDAY_SIGMA,
            initval=DELTA_HOLIDAY_MU,
        )
        lam = pm.Beta(
            "lam",
            alpha=np.full(n_channels, LAM_A),
            beta=np.full(n_channels, LAM_B),
            dims="channel",
            initval=np.full(n_channels, LAM_A / (LAM_A + LAM_B)),
        )
        k = pm.Gamma(
            "k",
            alpha=np.full(n_channels, K_SHAPE),
            beta=np.full(n_channels, K_RATE),
            dims="channel",
            initval=np.full(n_channels, K_SHAPE / K_RATE),
        )
        s_mean = float(np.clip(S_SHAPE / S_RATE, S_LOWER, S_UPPER))
        s = pm.Truncated(
            "s",
            pm.Gamma.dist(alpha=S_SHAPE, beta=S_RATE),
            lower=S_LOWER,
            upper=S_UPPER,
            dims="channel",
            initval=np.full(n_channels, s_mean),
        )
        beta = pm.HalfNormal(
            "beta",
            sigma=np.full(n_channels, BETA_SIGMA),
            dims="channel",
            initval=np.full(n_channels, 0.5 * BETA_SIGMA),
        )
        sigma = pm.HalfNormal("sigma", sigma=SIGMA_SIGMA, initval=SIGMA_SIGMA)
        media = _media_mu(spend_data, lam, k, s, beta, adstock_length, n_channels)
        mu = (
            alpha
            + tau * t_over_t
            + pm.math.dot(sin_feat, gamma_sin)
            + pm.math.dot(cos_feat, gamma_cos)
            + delta_holiday * holiday
            + media
        )
        pm.Deterministic("mu", mu, dims="week")
        pm.Normal("y", mu=mu, sigma=sigma, observed=y_obs, dims="week")
    return model


def _require(df: pd.DataFrame, channels: tuple[str, ...]) -> None:
    if not channels:
        raise ValueError("build_model: channels must be non-empty")
    if df.empty:
        raise ValueError("build_model: empty frame")
    for column in ("revenue", "holiday_flag"):
        if column not in df.columns:
            raise ValueError(f"build_model: missing column {column}")
    for channel in channels:
        if f"spend_{channel}" not in df.columns:
            raise ValueError(f"build_model: missing spend_{channel}")


def _media_mu(spend: Any, lam: Any, k: Any, s: Any, beta: Any, length: int, n_channels: int) -> Any:
    terms = []
    for index in range(n_channels):
        adstocked = adstock_pt(spend[:, index], lam[index], length)
        saturated = hill_pt(adstocked, k[index], s[index])
        terms.append(beta[index] * saturated)
    return pm.math.sum(pm.math.stack(terms), axis=0)


def sample_model(
    model: pm.Model,
    *,
    draws: int = SAMPLER_DRAWS,
    tune: int = SAMPLER_TUNE,
    chains: int = SAMPLER_CHAINS,
    seed: int = SAMPLER_SEED,
    target_accept: float = TARGET_ACCEPT,
    progressbar: bool = False,
) -> Any:
    """NUTS via nutpie; fall back to PyMC if nutpie cannot compile the model (D-08)."""
    kwargs: dict[str, Any] = {
        "draws": draws,
        "tune": tune,
        "chains": chains,
        "random_seed": seed,
        "progressbar": progressbar,
        "idata_kwargs": {"log_likelihood": False},
    }
    with model:
        try:
            idata = pm.sample(nuts_sampler="nutpie", **kwargs)
        except Exception:
            idata = pm.sample(
                nuts_sampler="pymc",
                target_accept=target_accept,
                init="adapt_diag",
                **kwargs,
            )
        pm.sample_posterior_predictive(
            idata, extend_inferencedata=True, random_seed=seed, progressbar=progressbar
        )
    return idata
