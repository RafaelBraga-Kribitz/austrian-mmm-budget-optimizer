"""OLS + HC1 baseline: adstock at prior-mode λ, no Hill (VR-601). numpy only."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ambo.config import ADSTOCK_LENGTH, CHANNEL_IDS, FOURIER_ORDER, LAM_A, LAM_B
from ambo.model import fourier_features
from ambo.transforms import adstock


@dataclass(frozen=True)
class OLSResult:
    n_obs: int
    n_params: int
    lambda_mode: dict[str, float]
    names: tuple[str, ...]
    coef: dict[str, float]
    se_hc1: dict[str, float]
    bayesian_roas_median: dict[str, float]
    sign_stable: dict[str, bool]


def beta_mode(a: float, b: float) -> float:
    if a > 1.0 and b > 1.0:
        return (a - 1.0) / (a + b - 2.0)
    return a / (a + b)


def ols_hc1(design: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_obs, n_params = design.shape
    if n_obs <= n_params:
        raise ValueError(f"OLS needs n > k, got n={n_obs} k={n_params}")
    coef, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ coef
    scale = n_obs / (n_obs - n_params)
    meat = (design * (resid**2 * scale)[:, None]).T @ design
    xtx_inv = np.linalg.pinv(design.T @ design)
    cov = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    return np.asarray(coef, dtype=float), np.asarray(se, dtype=float)


def fit_ols_baseline(
    frame: pd.DataFrame,
    *,
    channels: tuple[str, ...] = CHANNEL_IDS,
    length: int = ADSTOCK_LENGTH,
    bayesian_roas: dict[str, float] | None = None,
) -> OLSResult:
    lam = beta_mode(LAM_A, LAM_B)
    lambdas = {name: lam for name in channels}
    design, names = _design_matrix(frame, channels, lambdas, length)
    y = frame["revenue"].to_numpy(dtype=float)
    coef, se = ols_hc1(design, y)
    coef_map = {name: float(coef[i]) for i, name in enumerate(names)}
    se_map = {name: float(se[i]) for i, name in enumerate(names)}
    roas = bayesian_roas or {}
    stable = {
        channel: _same_sign(coef_map[f"adstock_{channel}"], roas.get(channel, 0.0))
        for channel in channels
    }
    return OLSResult(
        n_obs=int(design.shape[0]),
        n_params=int(design.shape[1]),
        lambda_mode=lambdas,
        names=names,
        coef=coef_map,
        se_hc1=se_map,
        bayesian_roas_median={k: float(v) for k, v in roas.items()},
        sign_stable=stable,
    )


def _design_matrix(
    frame: pd.DataFrame,
    channels: tuple[str, ...],
    lambdas: dict[str, float],
    length: int,
) -> tuple[np.ndarray, tuple[str, ...]]:
    n_weeks = len(frame)
    t = np.arange(1, n_weeks + 1, dtype=float)
    sin_feat, cos_feat = fourier_features(n_weeks)
    blocks = [
        np.ones((n_weeks, 1)),
        (t / n_weeks)[:, None],
        sin_feat,
        cos_feat,
        frame["holiday_flag"].to_numpy(dtype=float)[:, None],
    ]
    names: list[str] = (
        ["intercept", "t_over_t"]
        + [f"sin_{k}" for k in range(1, FOURIER_ORDER + 1)]
        + [f"cos_{k}" for k in range(1, FOURIER_ORDER + 1)]
        + ["holiday_flag"]
    )
    for channel in channels:
        spend = frame[f"spend_{channel}"].to_numpy(dtype=float)
        blocks.append(adstock(spend, lambdas[channel], length)[:, None])
        names.append(f"adstock_{channel}")
    return np.hstack(blocks), tuple(names)


def _same_sign(ols_coef: float, roas: float) -> bool:
    if ols_coef == 0.0 or roas == 0.0:
        return False
    return bool(np.sign(ols_coef) == np.sign(roas))
