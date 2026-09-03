"""VR-401 holdout: refit on first T−13, predict last 13 with actual spend.

Implements: VR-401

Conditional forecast: adstock runs on the full scaled spend series so carryover
from train into the holdout window is kept. Scale factors come from the holdout
posterior (computed on the train slice at fit time — RK-M2-4). This module does
not call `pm.sample`.
"""

from __future__ import annotations

import argparse
import functools
import os
import sys
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
import pandas as pd
import pytensor
import pytensor.tensor as pt

from ambo.common.config import SPEC_CHANNEL_ORDER, load_settings
from ambo.common.db import read_mmm_input
from ambo.common.errors import FitError, ValidationError
from ambo.common.logging import get_logger
from ambo.model.mmm import FOURIER_ORDER, control_mean_scaled, fourier_features_for_weeks
from ambo.model.posterior_io import PosteriorBundle, load_posterior
from ambo.model.transforms import adstock_convolve, hill_saturation, to_model_scale

# mypy: disable-error-code="no-untyped-call,attr-defined,no-any-return"

LOGGER = get_logger(__name__)
# VR-401; kept equal to `ambo.model.fit` via test_holdout_horizon_matches_fit.
HOLDOUT_HORIZON = 13
HOLDOUT_MIN_WEEKS = 65
_HDI_PROB = 0.9
CSV_COLUMNS = (
    "week_start",
    "revenue",
    "yhat_median",
    "hdi_low",
    "hdi_high",
    "naive",
    "covered",
    "model_mape",
    "naive_mape",
    "coverage_90",
)


def run_holdout(
    layer: str,
    *,
    bundle: PosteriorBundle | None = None,
    frame: pd.DataFrame | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Write `holdout_<layer>.csv` with MAPE, naive MAPE, and 90% coverage.

    Implements: VR-401
    """
    loaded = frame if frame is not None else read_mmm_input(layer)
    n_weeks = len(loaded)
    if n_weeks < HOLDOUT_MIN_WEEKS:
        raise ValidationError(
            f"holdout requires T >= {HOLDOUT_MIN_WEEKS} (VR-401); {layer} has {n_weeks}"
        )
    posterior = bundle if bundle is not None else load_posterior(f"{layer}__holdout")
    table = _holdout_table(loaded, posterior)
    dest = _csv_path(layer, output_dir)
    _atomic_write_csv(table, dest)
    LOGGER.info("Wrote holdout table %s", dest)
    return dest


def _holdout_table(frame: pd.DataFrame, bundle: PosteriorBundle) -> pd.DataFrame:
    n_weeks = len(frame)
    n_train = n_weeks - HOLDOUT_HORIZON
    holdout = frame.iloc[n_train:]
    y_eur = holdout["revenue"].to_numpy(dtype=np.float64)
    naive = frame["revenue"].to_numpy(dtype=np.float64)[n_train - 52 : n_weeks - 52]
    mu_eur, y_rep = _predictive(frame, bundle, n_train)
    yhat = np.median(mu_eur, axis=0)
    lows = np.empty(HOLDOUT_HORIZON, dtype=np.float64)
    highs = np.empty(HOLDOUT_HORIZON, dtype=np.float64)
    for week in range(HOLDOUT_HORIZON):
        lows[week], highs[week] = _hdi90(y_rep[:, week])
    covered = (y_eur >= lows) & (y_eur <= highs)
    model_mape = _mape(y_eur, yhat)
    naive_mape = _mape(y_eur, naive)
    coverage = float(covered.mean())
    return pd.DataFrame(
        {
            "week_start": _week_start_strings(holdout),
            "revenue": y_eur,
            "yhat_median": yhat,
            "hdi_low": lows,
            "hdi_high": highs,
            "naive": naive,
            "covered": covered.astype(int),
            "model_mape": model_mape,
            "naive_mape": naive_mape,
            "coverage_90": coverage,
        }
    )


def _predictive(
    frame: pd.DataFrame, bundle: PosteriorBundle, n_train: int
) -> tuple[np.ndarray, np.ndarray]:
    n_weeks = len(frame)
    channels = [name for name in SPEC_CHANNEL_ORDER if name in bundle.scale_factors.spend_means]
    scaled = to_model_scale(frame, bundle.scale_factors)
    t_hold = np.arange(n_train + 1, n_weeks + 1, dtype=np.float64)
    sin_feat, cos_feat = fourier_features_for_weeks(t_hold)
    mu_scaled = control_mean_scaled(
        alpha=_col(bundle.draws, "alpha"),
        tau=_col(bundle.draws, "tau"),
        t_over_t=t_hold / float(n_train),
        gamma_sin=_gamma(bundle.draws, "gamma_sin"),
        gamma_cos=_gamma(bundle.draws, "gamma_cos"),
        sin_feat=sin_feat,
        cos_feat=cos_feat,
        delta_promo=_col(bundle.draws, "delta_promo"),
        promo=scaled["promo_flag"].to_numpy(dtype=np.float64)[n_train:],
        delta_advent=_col(bundle.draws, "delta_advent"),
        advent=scaled["advent_flag"].to_numpy(dtype=np.float64)[n_train:],
        delta_jan=_col(bundle.draws, "delta_jan"),
        jan=scaled["jan_dip_flag"].to_numpy(dtype=np.float64)[n_train:],
    )
    length = load_settings().adstock_length
    mu_scaled = mu_scaled + _media_holdout(scaled, bundle, channels, n_train, length)
    revenue_mean = float(bundle.scale_factors.revenue_mean)
    mu_eur = mu_scaled * revenue_mean
    sigma_eur = _col(bundle.draws, "sigma") * revenue_mean
    rng = np.random.default_rng(load_settings().sampler.random_seed)
    noise = rng.normal(size=mu_eur.shape) * sigma_eur[:, None]
    return mu_eur, mu_eur + noise


def _media_holdout(
    scaled: pd.DataFrame,
    bundle: PosteriorBundle,
    channels: list[str],
    n_train: int,
    length: int,
) -> np.ndarray:
    n_draws = len(bundle.draws)
    media = np.zeros((n_draws, HOLDOUT_HORIZON), dtype=np.float64)
    series_fn = _series_fn(length)
    for channel in channels:
        x = scaled[f"spend_{channel}"].to_numpy(dtype=np.float64)
        lam = _param(bundle.draws, "lam", channel)
        k = _param(bundle.draws, "k", channel)
        s = _param(bundle.draws, "s", channel)
        beta = _param(bundle.draws, "beta", channel)
        for draw in range(n_draws):
            full = np.asarray(
                series_fn(x, lam[draw], k[draw], s[draw], beta[draw]),
                dtype=np.float64,
            )
            media[draw] += full[n_train:]
    return media


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    if np.any(actual == 0.0):
        raise ValidationError("holdout MAPE: revenue is zero on a holdout week")
    return float(np.mean(np.abs(actual - predicted) / np.abs(actual)))


def _hdi90(values: np.ndarray) -> tuple[float, float]:
    interval = np.asarray(az.hdi(values, hdi_prob=_HDI_PROB), dtype=np.float64)
    return float(interval[0]), float(interval[1])


def _col(draws: pd.DataFrame, name: str) -> np.ndarray:
    if name not in draws.columns:
        raise ValidationError(f"posterior missing column {name}")
    return np.asarray(draws.loc[:, name], dtype=np.float64)


def _param(draws: pd.DataFrame, name: str, channel: str) -> np.ndarray:
    column = f"{name}__{channel}"
    if column not in draws.columns:
        raise ValidationError(f"posterior missing column {column}")
    return np.asarray(draws.loc[:, column], dtype=np.float64)


def _gamma(draws: pd.DataFrame, name: str) -> np.ndarray:
    cols = [f"{name}__{order}" for order in range(1, FOURIER_ORDER + 1)]
    missing = [col for col in cols if col not in draws.columns]
    if missing:
        raise ValidationError(f"posterior missing Fourier columns {missing}")
    return draws.loc[:, cols].to_numpy(dtype=np.float64)


def _week_start_strings(holdout: pd.DataFrame) -> list[str]:
    if "week_start" not in holdout.columns:
        raise ValidationError("holdout frame missing week_start")
    values = pd.to_datetime(holdout["week_start"])
    return [stamp.strftime("%Y-%m-%d") for stamp in values]


def _csv_path(layer: str, output_dir: Path | None) -> Path:
    directory = output_dir if output_dir is not None else load_settings().paths.reports / "model"
    return Path(directory) / f"holdout_{layer}.csv"


def _atomic_write_csv(frame: pd.DataFrame, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
    try:
        ordered = frame.loc[:, list(CSV_COLUMNS)]
        ordered.to_csv(tmp, index=False, lineterminator="\n", float_format="%.6f")
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()


@functools.lru_cache(maxsize=4)
def _series_fn(length: int) -> Any:
    x = pt.dvector("x")
    lam = pt.dscalar("lam")
    k = pt.dscalar("k")
    s = pt.dscalar("s")
    beta = pt.dscalar("beta")
    contrib = beta * hill_saturation(adstock_convolve(x, lam, length), k, s)
    return pytensor.function([x, lam, k, s, beta], contrib)


def main(argv: list[str] | None = None) -> int:
    """CLI: fit holdout (optional) then write the CSV. Sampling stays in fit.py."""
    parser = argparse.ArgumentParser(prog="python -m ambo.validate.holdout")
    parser.add_argument("--layer", required=True)
    parser.add_argument(
        "--no-fit",
        action="store_true",
        help="skip sampling; load an existing {layer}__holdout parquet",
    )
    args = parser.parse_args(argv)
    try:
        if not args.no_fit:
            from ambo.model.fit import run_fit

            run_fit(args.layer, variant="holdout")
        run_holdout(args.layer)
    except (ValidationError, FitError, OSError) as exc:
        LOGGER.exception("holdout failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
