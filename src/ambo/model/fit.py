"""The only legal `pm.sample` home (D-11 / MD-050) and the fit CLI.

Implements: MD-050, MD-051, MD-071, MD-072, MD-073, EB-050, VR-401

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
# VR-401: last 13 weeks held out; naive baseline needs t−52 ⇒ T ≥ 65.
HOLDOUT_HORIZON = 13
HOLDOUT_MIN_WEEKS = 65
# MD-073 rung 1. Not an MD-050 setting. Leaving this rung requires ADR-005.
MD073_RUNG1_TARGET_ACCEPT = 0.95
# ADR-011: same rung-1 mechanism after 0.95 still diverges. Not an MD-050 edit.
MD073_RUNG1B_TARGET_ACCEPT = 0.99
# MD-073 rung 3. YAML on disk stays MD-040 (ADR-009).
MD073_RUNG3_S = TruncGammaParams(shape=4.0, rate=3.0, lower=0.5, upper=2.5)
_RUNG1_NOTE = (
    "MD-073 rung 1 applied: target_accept raised to 0.95 "
    "(Settings.sampler unchanged; not an MD-050 edit)."
)
_RUNG1B_NOTE = (
    "MD-073 rung 1 extended (ADR-011): target_accept raised to 0.99 after 0.95 "
    "still left divergences (Settings.sampler unchanged; ADR-010 superseded)."
)
_MODEL_NOTES = (
    "MD-073 rung 2 (ADR-005): non-centered Fourier; reported names gamma_sin/gamma_cos.",
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


def holdout_train_slice(frame: pd.DataFrame) -> pd.DataFrame:
    """First T−13 rows. Scale factors must be computed on this slice (RK-M2-4).

    Implements: VR-401
    """
    n_weeks = len(frame)
    if n_weeks < HOLDOUT_MIN_WEEKS:
        raise FitError(
            f"holdout requires T >= {HOLDOUT_MIN_WEEKS} weeks (VR-401 naive t-52); got {n_weeks}"
        )
    return frame.iloc[:-HOLDOUT_HORIZON].copy()


def run_fit(layer: str, *, variant: str | None = None) -> Path:
    """Mart → scale → build → sample → posterior_io → diag report.

    Implements: MD-050, MD-051, MD-071, MD-072, MD-073, EB-050, VR-401
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
    artifact_name = layer
    if variant == "holdout":
        frame = holdout_train_slice(frame)
        artifact_name = f"{layer}__holdout"
    priors_path = repo_root() / SYNTHETIC_PRIORS_RELATIVE
    priors = load_priors(priors_path)
    scale_factors = compute_scale_factors(frame, channels)
    scaled = to_model_scale(frame, scale_factors)
    return _run_md073_ladder(
        layer=layer,
        artifact_name=artifact_name,
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
    artifact_name: str,
    scaled: pd.DataFrame,
    channels: list[str],
    priors: PriorConfig,
    sampler: Any,
    scale_factors: ScaleFactors,
    frame: pd.DataFrame,
    priors_path: Path,
) -> Path:
    """MD-050 sample, then MD-073 rung 1 (0.95, then 0.99) if eligible.

    Rebuild the PyMC model each attempt: a second `pm.sample` on the same
    instance fails (`logp` is None). Rung 2 is already the `build_model`
    parameterization (ADR-005). ADR-010 (s=1) is superseded; s is sampled.
    Rung 1 retries when divergences fail, optionally with ESS_tail (S-C;
    D-07 interpretation of MD-073 — not a gate widening).
    """
    LOGGER.info("MD-073 ladder: layer=%s artifact=%s", layer, artifact_name)
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
            "MD-071 red on divergences (ESS_tail may fail with them); "
            "MD-073 rung 1 retry (raised target_accept)",
            "fit %s all-green after MD-073 rung 1; posterior %s",
        ),
        (
            priors,
            MD073_RUNG1B_TARGET_ACCEPT,
            (*_MODEL_NOTES, _RUNG1_NOTE, _RUNG1B_NOTE),
            "MD-071 red on divergences (ESS_tail may fail with them); "
            "ADR-011 retry (target_accept 0.99)",
            "fit %s all-green after ADR-011 target_accept 0.99; posterior %s",
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
            artifact_name,
            frame,
            priors_path,
            notes=notes,
        )
        if result.all_green:
            LOGGER.info(ok_fmt, artifact_name, dest)
            return dest
        if i < len(attempts) - 1:
            _require_rung1_retry_eligible(result, artifact_name, report)
    raise FitError(f"MD-071/072 red for {artifact_name}; see {report}")


def _try_fit(
    scaled: pd.DataFrame,
    channels: list[str],
    priors: PriorConfig,
    sampler: Any,
    target_accept: float,
    scale_factors: ScaleFactors,
    artifact_name: str,
    frame: pd.DataFrame,
    priors_path: Path,
    notes: tuple[str, ...],
) -> tuple[Path, DiagResult, Path]:
    model = build_model(scaled, channels, priors)
    idata = _draw_posterior(model, sampler, target_accept=target_accept)
    return _persist(idata, scale_factors, artifact_name, frame, priors_path, notes=notes)


def _require_rung1_retry_eligible(result: DiagResult, layer: str, report: Path) -> None:
    if not _rung1_retry_eligible(result):
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
    artifact_name: str,
    frame: pd.DataFrame,
    priors_path: Path,
    notes: tuple[str, ...],
) -> tuple[Path, DiagResult, Path]:
    dest = save_posterior(
        idata,
        scale_factors,
        artifact_name,
        data_hash=_sha256_frame(frame),
        prior_sha256=_sha256_file(priors_path),
    )
    result = run_diagnostics(idata, DiagGates.standard())
    report = write_diag_report(result, artifact_name, idata=idata, notes=notes)
    return dest, result, report


_RUNG1_RETRY_GATES = frozenset({"divergences", "ESS_tail"})


def _rung1_retry_eligible(result: DiagResult) -> bool:
    """True when rung-1 `target_accept` retries are still the right move.

    Divergences may poison ESS_tail (S-C: 66 divergences, ESS_tail 317.5) while
    R-hat, ESS_bulk, BFMI, and PPC stay green. That pair is still a sampler
    step-size problem, not a new parameterization. Any other red gate stops
    the ladder.
    """
    failed = {check.name for check in result.checks if not check.passed}
    return "divergences" in failed and failed <= _RUNG1_RETRY_GATES


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
        help="holdout (VR-401) or flat|nopromo|loco-<channel> (parsed; wired later)",
    )
    return parser.parse_args(argv)


def _reject_unwired_variant(variant: str | None) -> None:
    if variant is None or variant == "holdout":
        return
    if _VARIANT_RE.fullmatch(variant) is None:
        raise FitError(f"unknown fit variant {variant!r}")
    raise FitError(f"fit variant {variant!r} is parsed but not wired until Phase 6")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_frame(frame: pd.DataFrame) -> str:
    return hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
