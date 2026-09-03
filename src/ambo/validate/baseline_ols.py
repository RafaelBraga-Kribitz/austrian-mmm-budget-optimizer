"""OLS + HC1 baseline with adstock fixed at prior-mode λ and no Hill (VR-601).

Implements: VR-601

numpy/scipy only — no statsmodels. Whatever signs emerge, they ship.
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytensor
import pytensor.tensor as pt
from pydantic import BaseModel, ConfigDict

from ambo.common.config import SPEC_CHANNEL_ORDER, load_settings, repo_root
from ambo.common.db import read_mmm_input
from ambo.common.errors import ValidationError
from ambo.common.logging import get_logger
from ambo.model.mmm import FOURIER_ORDER, fourier_features_for_weeks
from ambo.model.priors import SYNTHETIC_PRIORS_RELATIVE, PriorConfig, load_priors
from ambo.model.transforms import adstock_convolve

# mypy: disable-error-code="no-untyped-call,attr-defined,no-any-return"

LOGGER = get_logger(__name__)


class OLSResult(BaseModel):
    """VR-601 side-by-side payload. Frozen."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    layer: str
    n_obs: int
    n_params: int
    lambda_mode: dict[str, float]
    names: tuple[str, ...]
    coef: dict[str, float]
    se_hc1: dict[str, float]
    bayesian_roas_median: dict[str, float]
    sign_stable: dict[str, bool]


def beta_mode(a: float, b: float) -> float:
    """Mode of Beta(a, b) when a,b > 1; otherwise the mean."""
    if a > 1.0 and b > 1.0:
        return (a - 1.0) / (a + b - 2.0)
    return a / (a + b)


def ols_hc1(design: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS coefficients and HC1 standard errors (Guide §4.3).

    Implements: VR-601
    """
    n_obs, n_params = design.shape
    if n_obs <= n_params:
        raise ValidationError(f"OLS needs n > k, got n={n_obs} k={n_params}")
    coef, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ coef
    scale = n_obs / (n_obs - n_params)
    meat = (design * (resid**2 * scale)[:, None]).T @ design
    # pinv: Fourier + calendar flags + media are collinear on Layer P (VR-601).
    xtx_inv = np.linalg.pinv(design.T @ design)
    cov = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    return np.asarray(coef, dtype=np.float64), np.asarray(se, dtype=np.float64)


def prior_mode_lambdas(priors: PriorConfig, channels: list[str]) -> dict[str, float]:
    return {
        name: beta_mode(priors.channels[name].lam.a, priors.channels[name].lam.b)
        for name in channels
    }


def fit_ols_baseline(
    frame: pd.DataFrame,
    channels: list[str],
    lambdas: dict[str, float],
    *,
    length: int,
    bayesian_roas: dict[str, float],
    layer: str,
) -> OLSResult:
    """Revenue ~ intercept, t/T, Fourier-4, flags, adstocked spend (no Hill)."""
    design, names = _design_matrix(frame, channels, lambdas, length)
    y = frame["revenue"].to_numpy(dtype=np.float64)
    coef, se = ols_hc1(design, y)
    coef_map = {name: float(coef[i]) for i, name in enumerate(names)}
    se_map = {name: float(se[i]) for i, name in enumerate(names)}
    stable = {
        channel: _same_sign(coef_map[f"adstock_{channel}"], bayesian_roas.get(channel, 0.0))
        for channel in channels
    }
    return OLSResult(
        layer=layer,
        n_obs=int(design.shape[0]),
        n_params=int(design.shape[1]),
        lambda_mode={name: float(lambdas[name]) for name in channels},
        names=names,
        coef=coef_map,
        se_hc1=se_map,
        bayesian_roas_median={name: float(bayesian_roas[name]) for name in channels},
        sign_stable=stable,
    )


def run_ols(
    layer: str,
    *,
    frame: pd.DataFrame | None = None,
    bayesian_roas: dict[str, float] | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Fit OLS+HC1 on a layer and write `ols_<layer>.json`.

    Implements: VR-601
    """
    loaded = frame if frame is not None else read_mmm_input(layer)
    priors = load_priors(repo_root() / SYNTHETIC_PRIORS_RELATIVE)
    channels = _channels_with_positive_spend(loaded, priors)
    if not channels:
        raise ValidationError(f"OLS: no spend channels on {layer}")
    roas = bayesian_roas if bayesian_roas is not None else _bayesian_roas(layer)
    result = fit_ols_baseline(
        loaded,
        channels,
        prior_mode_lambdas(priors, channels),
        length=load_settings().adstock_length,
        bayesian_roas=roas,
        layer=layer,
    )
    dest = _json_path(layer, output_dir)
    _atomic_write_json(result.model_dump(mode="json"), dest)
    LOGGER.info("Wrote OLS table %s", dest)
    return dest


def _channels_with_positive_spend(frame: pd.DataFrame, priors: PriorConfig) -> list[str]:
    names: list[str] = []
    for name in SPEC_CHANNEL_ORDER:
        column = f"spend_{name}"
        if column not in frame.columns or name not in priors.channels:
            continue
        spend = frame[column].to_numpy(dtype=np.float64)
        if np.any(spend > 0.0):
            names.append(name)
    return names


def _design_matrix(
    frame: pd.DataFrame,
    channels: list[str],
    lambdas: dict[str, float],
    length: int,
) -> tuple[np.ndarray, tuple[str, ...]]:
    n_weeks = len(frame)
    t = np.arange(1, n_weeks + 1, dtype=np.float64)
    sin_feat, cos_feat = fourier_features_for_weeks(t)
    blocks = [
        np.ones((n_weeks, 1)),
        (t / n_weeks)[:, None],
        sin_feat,
        cos_feat,
        frame["promo_flag"].to_numpy(dtype=np.float64)[:, None],
        frame["advent_flag"].to_numpy(dtype=np.float64)[:, None],
        frame["jan_dip_flag"].to_numpy(dtype=np.float64)[:, None],
    ]
    names: list[str] = (
        ["intercept", "t_over_t"]
        + [f"sin_{k}" for k in range(1, FOURIER_ORDER + 1)]
        + [f"cos_{k}" for k in range(1, FOURIER_ORDER + 1)]
        + ["promo_flag", "advent_flag", "jan_dip_flag"]
    )
    adstock_fn = _adstock_fn(length)
    for channel in channels:
        spend = frame[f"spend_{channel}"].to_numpy(dtype=np.float64)
        adstocked = np.asarray(adstock_fn(spend, lambdas[channel]), dtype=np.float64)
        blocks.append(adstocked[:, None])
        names.append(f"adstock_{channel}")
    return np.hstack(blocks), tuple(names)


def _bayesian_roas(layer: str) -> dict[str, float]:
    import tempfile

    from ambo.validate.recovery import compute_recovery

    with tempfile.TemporaryDirectory() as tmp:
        metrics = compute_recovery(layer, output_dir=Path(tmp))
    return {row.channel: row.roas_median for row in metrics.channels}


def _same_sign(ols_coef: float, roas: float) -> bool:
    if ols_coef == 0.0 or roas == 0.0:
        return False
    return bool(np.sign(ols_coef) == np.sign(roas))


def _json_path(layer: str, output_dir: Path | None) -> Path:
    directory = output_dir if output_dir is not None else load_settings().paths.reports / "recovery"
    return Path(directory) / f"ols_{layer}.json"


def _atomic_write_json(payload: dict[str, Any], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()


@functools.lru_cache(maxsize=4)
def _adstock_fn(length: int) -> Any:
    x = pt.dvector("x")
    lam = pt.dscalar("lam")
    return pytensor.function([x, lam], adstock_convolve(x, lam, length))
