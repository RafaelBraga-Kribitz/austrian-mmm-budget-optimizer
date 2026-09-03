"""The only legal `pm.sample` home (D-11 / MD-050) and the fit CLI.

Implements: MD-050, MD-051, MD-071, MD-072, EB-050

Sampler kwargs come from `Settings.sampler`. This module does not restate
MD-050 literals. `channels_present` is parsed here, not in `mmm.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

import arviz as az
import pandas as pd
import pymc as pm

from ambo.common.config import load_settings, repo_root
from ambo.common.db import read_dim_layer, read_mmm_input
from ambo.common.errors import FitError
from ambo.common.logging import get_logger
from ambo.model.diagnostics import DiagGates, run_diagnostics, write_diag_report
from ambo.model.mmm import build_model
from ambo.model.posterior_io import save_posterior
from ambo.model.priors import SYNTHETIC_PRIORS_RELATIVE, load_priors
from ambo.model.transforms import compute_scale_factors, to_model_scale

LOGGER = get_logger(__name__)

_VARIANT_RE = re.compile(r"^(flat|nopromo|holdout|loco-[a-z][a-z0-9_]*)$")


def sample_model(
    model: pm.Model,
    *,
    draws: int,
    tune: int,
    chains: int,
    target_accept: float,
    random_seed: int,
    init: str,
    **kwargs: Any,
) -> az.InferenceData:
    """Run NUTS via the single `pm.sample` call site."""
    LOGGER.info(
        "sample_model: starting NUTS (chains=%s tune=%s draws=%s)",
        chains,
        tune,
        draws,
    )
    with model:
        idata: az.InferenceData = pm.sample(
            draws=draws,
            tune=tune,
            chains=chains,
            target_accept=target_accept,
            random_seed=random_seed,
            init=init,
            **kwargs,
        )
    LOGGER.info("sample_model: NUTS finished")
    return idata


def add_posterior_predictive(
    model: pm.Model, idata: az.InferenceData, *, random_seed: int
) -> az.InferenceData:
    """Draw posterior predictive `y` into `idata` (MD-072). Not `pm.sample`."""
    with model:
        pm.sample_posterior_predictive(idata, extend_inferencedata=True, random_seed=random_seed)
    return idata


def channels_present_for_layer(layer: str) -> list[str]:
    """Parse `dim_layer.channels_present` (comma-joined varchar, taxonomy order)."""
    dim = read_dim_layer()
    keyed = dim.set_index("layer")
    if layer not in keyed.index:
        raise FitError(f"unknown layer {layer!r}")
    raw = str(keyed.loc[layer, "channels_present"])
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    if not tokens:
        raise FitError(f"layer {layer!r} has empty channels_present")
    return tokens


def run_fit(layer: str, *, variant: str | None = None) -> Path:
    """Mart → scale → build → sample → posterior_io → diag report.

    Implements: MD-050, MD-051, MD-071, MD-072, EB-050
    """
    settings = load_settings()
    LOGGER.info(
        "expected runtime: <= %s min/fit at MD-050 on 4 cores (Settings.max_fit_minutes)",
        settings.max_fit_minutes,
    )
    _reject_unwired_variant(variant)
    sampler = settings.sampler
    frame = read_mmm_input(layer)
    channels = channels_present_for_layer(layer)
    priors_path = repo_root() / SYNTHETIC_PRIORS_RELATIVE
    priors = load_priors(priors_path)
    scale_factors = compute_scale_factors(frame, channels)
    model = build_model(to_model_scale(frame, scale_factors), channels, priors)
    idata = sample_model(
        model,
        draws=sampler.draws,
        tune=sampler.tune,
        chains=sampler.chains,
        target_accept=sampler.target_accept,
        random_seed=sampler.random_seed,
        init=sampler.init,
    )
    add_posterior_predictive(model, idata, random_seed=sampler.random_seed)
    dest = save_posterior(
        idata,
        scale_factors,
        layer,
        data_hash=_sha256_frame(frame),
        prior_sha256=_sha256_file(priors_path),
    )
    result = run_diagnostics(idata, DiagGates.standard())
    report = write_diag_report(result, layer, idata=idata)
    if not result.all_green:
        raise FitError(f"MD-071/072 red for {layer}; see {report}")
    LOGGER.info("fit %s all-green; posterior %s", layer, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m ambo.model.fit --layer P-SA``."""
    args = _parse_args(argv)
    try:
        run_fit(args.layer, variant=args.variant)
    except FitError:
        LOGGER.exception("fit failed")
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m ambo.model.fit")
    parser.add_argument("--layer", required=True, help="BP-D-06 layer name, e.g. P-SA")
    parser.add_argument(
        "--variant",
        default=None,
        help="flat|nopromo|holdout|loco-<channel> (parsed now; wired later)",
    )
    return parser.parse_args(argv)


def _reject_unwired_variant(variant: str | None) -> None:
    if variant is None:
        return
    if _VARIANT_RE.fullmatch(variant) is None:
        raise FitError(f"unknown fit variant {variant!r}")
    raise FitError(f"fit variant {variant!r} is parsed but not wired until T-402 / Phase 6")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_frame(frame: pd.DataFrame) -> str:
    return hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
