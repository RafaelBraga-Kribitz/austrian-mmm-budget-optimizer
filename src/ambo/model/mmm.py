"""Raw PyMC MMM builder (SPEC-04 §2).

Implements: MD-001, MD-002, MD-073, ADR-005

One definition serves every dataset: the channel list and the prior YAML are the
only knobs. Additive in revenue *level*, not log (T-9). Fourier period 52.18 and
order 4 are SPEC-04 §2 math, not configuration (D-12).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pymc as pm
import pytensor.tensor as pt

from ambo.common.config import load_settings
from ambo.common.errors import FitError
from ambo.model.priors import GlobalPriors, PriorConfig
from ambo.model.transforms import adstock_convolve, hill_saturation

# mypy: disable-error-code="no-untyped-call"

# SPEC-04 §2 — yearly Fourier, order 4, ISO-week period. Not Settings.
FOURIER_PERIOD_WEEKS = 52.18
FOURIER_ORDER = 4

_REQUIRED_COLUMNS = ("revenue", "promo_flag", "advent_flag", "jan_dip_flag")


def _require_media_frame(df: pd.DataFrame, channels: list[str]) -> None:
    if not channels:
        raise FitError("build_model(): channels must be non-empty")
    if df.empty:
        raise FitError("build_model(): frame is empty")
    for column in _REQUIRED_COLUMNS:
        if column not in df.columns:
            raise FitError(f"build_model(): missing column {column}")
    for channel in channels:
        spend_col = f"spend_{channel}"
        if spend_col not in df.columns:
            raise FitError(f"build_model(): missing column {spend_col}")


def _fourier_features(n_weeks: int) -> tuple[np.ndarray, np.ndarray]:
    """sin/cos design matrices, shape (T, 4), t = 1…T (SPEC-04 §2)."""
    t = np.arange(1, n_weeks + 1, dtype=np.float64)
    orders = np.arange(1, FOURIER_ORDER + 1, dtype=np.float64)
    angle = 2.0 * np.pi * np.outer(t, orders) / FOURIER_PERIOD_WEEKS
    return np.sin(angle), np.cos(angle)


def _stack_channel_params(channels: list[str], priors: PriorConfig) -> dict[str, np.ndarray]:
    missing = [name for name in channels if name not in priors.channels]
    if missing:
        raise FitError(f"build_model(): no prior entry for channel(s) {missing}")
    rows = [priors.channels[name] for name in channels]
    return {
        "lam_a": np.array([row.lam.a for row in rows], dtype=np.float64),
        "lam_b": np.array([row.lam.b for row in rows], dtype=np.float64),
        "k_shape": np.array([row.K.shape for row in rows], dtype=np.float64),
        "k_rate": np.array([row.K.rate for row in rows], dtype=np.float64),
        "s_shape": np.array([row.s.shape for row in rows], dtype=np.float64),
        "s_rate": np.array([row.s.rate for row in rows], dtype=np.float64),
        "s_lower": np.array([row.s.lower for row in rows], dtype=np.float64),
        "s_upper": np.array([row.s.upper for row in rows], dtype=np.float64),
        "beta_sigma": np.array([row.beta.sigma for row in rows], dtype=np.float64),
    }


def _media_mu(
    spend: Any,
    lam: Any,
    k: Any,
    s: Any,
    beta: Any,
    length: int,
    n_channels: int,
) -> Any:
    terms = []
    for index in range(n_channels):
        adstocked = adstock_convolve(spend[:, index], lam[index], length)
        saturated = hill_saturation(adstocked, k[index], s[index])
        terms.append(beta[index] * saturated)
    return pt.sum(pt.stack(terms), axis=0)


def _linear_predictor(
    *,
    alpha: Any,
    tau: Any,
    t_over_t: np.ndarray,
    gamma_sin: Any,
    gamma_cos: Any,
    sin_feat: np.ndarray,
    cos_feat: np.ndarray,
    delta_promo: Any,
    promo: np.ndarray,
    delta_advent: Any,
    advent: np.ndarray,
    delta_jan: Any,
    jan: np.ndarray,
    media: Any,
) -> Any:
    fourier = pt.dot(sin_feat, gamma_sin) + pt.dot(cos_feat, gamma_cos)
    return (
        alpha
        + tau * t_over_t
        + fourier
        + delta_promo * promo
        + delta_advent * advent
        + delta_jan * jan
        + media
    )


def build_model(df: pd.DataFrame, channels: list[str], priors: PriorConfig) -> pm.Model:
    """Construct the SPEC-04 §2 model on already-scaled data (MD-002)."""
    _require_media_frame(df, channels)
    n_weeks = int(len(df))
    n_channels = len(channels)
    length = load_settings().adstock_length
    hyper = _stack_channel_params(channels, priors)
    sin_feat, cos_feat = _fourier_features(n_weeks)
    t_over_t = np.arange(1, n_weeks + 1, dtype=np.float64) / n_weeks
    spend = np.column_stack([df[f"spend_{name}"].to_numpy(dtype=np.float64) for name in channels])
    coords = {
        "channel": list(channels),
        "week": list(range(n_weeks)),
        "fourier": list(range(1, FOURIER_ORDER + 1)),
    }
    globals_ = priors.globals
    with pm.Model(coords=coords) as model:
        _register_nodes(
            df=df,
            spend=spend,
            hyper=hyper,
            globals_=globals_,
            sin_feat=sin_feat,
            cos_feat=cos_feat,
            t_over_t=t_over_t,
            length=length,
            n_channels=n_channels,
        )
    return model


def _register_nodes(
    *,
    df: pd.DataFrame,
    spend: np.ndarray,
    hyper: dict[str, np.ndarray],
    globals_: GlobalPriors,
    sin_feat: np.ndarray,
    cos_feat: np.ndarray,
    t_over_t: np.ndarray,
    length: int,
    n_channels: int,
) -> None:
    """Free RVs + likelihood. Must run inside `with pm.Model`."""
    promo = df["promo_flag"].to_numpy(dtype=np.float64)
    advent = df["advent_flag"].to_numpy(dtype=np.float64)
    jan = df["jan_dip_flag"].to_numpy(dtype=np.float64)
    y_obs = df["revenue"].to_numpy(dtype=np.float64)
    spend_data = pm.Data("spend", spend, dims=("week", "channel"))
    k_mean = hyper["k_shape"] / hyper["k_rate"]
    lam_mean = hyper["lam_a"] / (hyper["lam_a"] + hyper["lam_b"])
    s_mean = np.clip(hyper["s_shape"] / hyper["s_rate"], hyper["s_lower"], hyper["s_upper"])
    alpha = pm.Normal(
        "alpha", mu=globals_.alpha.mu, sigma=globals_.alpha.sigma, initval=globals_.alpha.mu
    )
    tau = pm.Normal("tau", mu=globals_.tau.mu, sigma=globals_.tau.sigma, initval=0.0)
    gamma_sin_offset = pm.Normal(
        "gamma_sin_offset",
        mu=0.0,
        sigma=1.0,
        dims="fourier",
        initval=np.zeros(FOURIER_ORDER),
    )
    gamma_cos_offset = pm.Normal(
        "gamma_cos_offset",
        mu=0.0,
        sigma=1.0,
        dims="fourier",
        initval=np.zeros(FOURIER_ORDER),
    )
    # MD-073 rung 2 / ADR-005: reported names stay gamma_sin / gamma_cos (D-06).
    gamma_sin = pm.Deterministic(
        "gamma_sin",
        globals_.gamma.mu + globals_.gamma.sigma * gamma_sin_offset,
        dims="fourier",
    )
    gamma_cos = pm.Deterministic(
        "gamma_cos",
        globals_.gamma.mu + globals_.gamma.sigma * gamma_cos_offset,
        dims="fourier",
    )
    delta_promo = pm.Normal(
        "delta_promo",
        mu=globals_.delta_promo.mu,
        sigma=globals_.delta_promo.sigma,
        initval=globals_.delta_promo.mu,
    )
    delta_advent = pm.Normal(
        "delta_advent",
        mu=globals_.delta_advent.mu,
        sigma=globals_.delta_advent.sigma,
        initval=globals_.delta_advent.mu,
    )
    delta_jan = pm.Normal(
        "delta_jan",
        mu=globals_.delta_jan.mu,
        sigma=globals_.delta_jan.sigma,
        initval=globals_.delta_jan.mu,
    )
    lam = pm.Beta(
        "lam", alpha=hyper["lam_a"], beta=hyper["lam_b"], dims="channel", initval=lam_mean
    )
    k = pm.Gamma("k", alpha=hyper["k_shape"], beta=hyper["k_rate"], dims="channel", initval=k_mean)
    s = pm.Truncated(
        "s",
        pm.Gamma.dist(alpha=hyper["s_shape"], beta=hyper["s_rate"]),
        lower=hyper["s_lower"],
        upper=hyper["s_upper"],
        dims="channel",
        initval=s_mean,
    )
    beta = pm.HalfNormal(
        "beta",
        sigma=hyper["beta_sigma"],
        dims="channel",
        initval=0.5 * hyper["beta_sigma"],
    )
    sigma = pm.HalfNormal("sigma", sigma=globals_.sigma.sigma, initval=float(globals_.sigma.sigma))
    media = _media_mu(spend_data, lam, k, s, beta, length, n_channels)
    mu = _linear_predictor(
        alpha=alpha,
        tau=tau,
        t_over_t=t_over_t,
        gamma_sin=gamma_sin,
        gamma_cos=gamma_cos,
        sin_feat=sin_feat,
        cos_feat=cos_feat,
        delta_promo=delta_promo,
        promo=promo,
        delta_advent=delta_advent,
        advent=advent,
        delta_jan=delta_jan,
        jan=jan,
        media=media,
    )
    pm.Normal("y", mu=mu, sigma=sigma, observed=y_obs, dims="week")
