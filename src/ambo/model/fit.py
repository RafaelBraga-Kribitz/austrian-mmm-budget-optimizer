"""The only legal `pm.sample` home (D-11 / MD-050) and the fit CLI.

Implements: MD-050, MD-051, MD-071, MD-072, MD-073, EB-050

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

from ambo.common.config import SPEC_CHANNEL_ORDER, load_settings, repo_root
from ambo.common.db import read_dim_layer, read_mmm_input
from ambo.common.errors import FitError
from ambo.common.logging import get_logger
from ambo.model.diagnostics import DiagGates, DiagResult, run_diagnostics, write_diag_report
from ambo.model.mmm import build_model
from ambo.model.posterior_io import save_posterior
from ambo.model.priors import (
    SYNTHETIC_PRIORS_RELATIVE,
    PriorConfig,
    TruncGammaParams,
    load_priors,
)
from ambo.model.transforms import ScaleFactors, compute_scale_factors, to_model_scale

LOGGER = get_logger(__name__)

_VARIANT_RE = re.compile(r"^(flat|nopromo|holdout|loco-[a-z][a-z0-9_]*)$")
# MD-073 rung 1. Not an MD-050 setting. Leaving this rung requires ADR-005.
MD073_RUNG1_TARGET_ACCEPT = 0.95
# MD-073 rung 3. YAML on disk stays MD-040 (ADR-009).
MD073_RUNG3_S = TruncGammaParams(shape=4.0, rate=3.0, lower=0.5, upper=2.5)
_RUNG1_NOTE = (
    "MD-073 rung 1 applied: target_accept raised to 0.95 "
    "(Settings.sampler unchanged; not an MD-050 edit)."
)
_MODEL_NOTES = (
    "MD-073 rung 2 (ADR-005): non-centered Fourier; reported names gamma_sin/gamma_cos.",
    "MD-073 rung 4 (ADR-010): s_c fixed at 1 (logistic saturation). YAML s prior is not sampled.",
)


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


def tighten_s_c_prior(priors: PriorConfig) -> PriorConfig:
    """MD-073 rung 3: Gamma(4, 3) trunc [0.5, 2.5]. YAML on disk is unchanged.

    Implements: MD-073
    """
    channels = {
        name: priors.channels[name].model_copy(update={"s": MD073_RUNG3_S})
        for name in SPEC_CHANNEL_ORDER
    }
    return priors.model_copy(update={"channels": channels})


def run_fit(layer: str, *, variant: str | None = None) -> Path:
    """Mart → scale → build → sample → posterior_io → diag report.

    Implements: MD-050, MD-051, MD-071, MD-072, MD-073, EB-050
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
    scaled = to_model_scale(frame, scale_factors)
    return _run_md073_ladder(
        layer=layer,
        scaled=scaled,
        channels=channels,
        priors=priors,
        sampler=sampler,
        scale_factors=scale_factors,
        frame=frame,
        priors_path=priors_path,
    )


def _run_md073_ladder(
    *,
    layer: str,
    scaled: pd.DataFrame,
    channels: list[str],
    priors: PriorConfig,
    sampler: Any,
    scale_factors: ScaleFactors,
    frame: pd.DataFrame,
    priors_path: Path,
) -> Path:
    """MD-050 sample, then MD-073 rung 1 if only divergences fail.

    Rebuild the PyMC model each attempt: a second `pm.sample` on the same
    instance fails (`logp` is None). Rungs 2 and 4 are already the
    `build_model` parameterization (ADR-005, ADR-010). Rung 3's s-prior copy
    is not applied because s is not sampled.
    """
    attempts: tuple[tuple[PriorConfig, float, tuple[str, ...], str | None, str], ...] = (
        (
            priors,
            sampler.target_accept,
            _MODEL_NOTES,
            None,
            "fit %s all-green; posterior %s",
        ),
        (
            priors,
            MD073_RUNG1_TARGET_ACCEPT,
            (*_MODEL_NOTES, _RUNG1_NOTE),
            "MD-071 red on divergences only; MD-073 rung 1 retry (raised target_accept)",
            "fit %s all-green after MD-073 rung 1; posterior %s",
        ),
    )
    report = Path()
    for i, (attempt_priors, target_accept, notes, warning, ok_fmt) in enumerate(attempts):
        if warning is not None:
            LOGGER.warning(warning)
        dest, result, report = _try_fit(
            scaled,
            channels,
            attempt_priors,
            sampler,
            target_accept,
            scale_factors,
            layer,
            frame,
            priors_path,
            notes=notes,
        )
        if result.all_green:
            LOGGER.info(ok_fmt, layer, dest)
            return dest
        if i < len(attempts) - 1:
            _require_divergences_only(result, layer, report)
    raise FitError(f"MD-071/072 red for {layer}; see {report}")


def _try_fit(
    scaled: pd.DataFrame,
    channels: list[str],
    priors: PriorConfig,
    sampler: Any,
    target_accept: float,
    scale_factors: ScaleFactors,
    layer: str,
    frame: pd.DataFrame,
    priors_path: Path,
    notes: tuple[str, ...],
) -> tuple[Path, DiagResult, Path]:
    model = build_model(scaled, channels, priors)
    idata = _draw_posterior(model, sampler, target_accept=target_accept)
    return _persist(idata, scale_factors, layer, frame, priors_path, notes=notes)


def _require_divergences_only(result: DiagResult, layer: str, report: Path) -> None:
    if not _only_divergences_failed(result):
        raise FitError(f"MD-071/072 red for {layer}; see {report}")


def _draw_posterior(model: pm.Model, sampler: Any, *, target_accept: float) -> az.InferenceData:
    idata = sample_model(
        model,
        draws=sampler.draws,
        tune=sampler.tune,
        chains=sampler.chains,
        target_accept=target_accept,
        random_seed=sampler.random_seed,
        init=sampler.init,
    )
    return add_posterior_predictive(model, idata, random_seed=sampler.random_seed)


def _persist(
    idata: az.InferenceData,
    scale_factors: ScaleFactors,
    layer: str,
    frame: pd.DataFrame,
    priors_path: Path,
    notes: tuple[str, ...],
) -> tuple[Path, DiagResult, Path]:
    dest = save_posterior(
        idata,
        scale_factors,
        layer,
        data_hash=_sha256_frame(frame),
        prior_sha256=_sha256_file(priors_path),
    )
    result = run_diagnostics(idata, DiagGates.standard())
    report = write_diag_report(result, layer, idata=idata, notes=notes)
    return dest, result, report


def _only_divergences_failed(result: DiagResult) -> bool:
    failed = [check.name for check in result.checks if not check.passed]
    return failed == ["divergences"]


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
