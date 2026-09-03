"""pymc-marketing MMM cross-check on S-B (VR-602).

Implements: VR-602, MD-003

Imports of `pymc_marketing` are confined to this module. Sampling goes through
their `MMM.fit` API, not a second `pm.sample` call site in ambo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict
from scipy.stats import pearsonr, spearmanr

from ambo.common.config import SPEC_CHANNEL_ORDER, load_settings
from ambo.common.db import read_mmm_input
from ambo.common.errors import ValidationError
from ambo.common.logging import get_logger
from ambo.model.mmm import FOURIER_ORDER, fourier_features_for_weeks
from ambo.model.transforms import ScaleFactors, compute_scale_factors

# mypy: disable-error-code="no-untyped-call,attr-defined,no-any-return,import-untyped"

LOGGER = get_logger(__name__)

EXPECTED_PYMC_MARKETING_VERSION = "0.19.4"
CORRELATION_GATE = 0.8
CONTROL_COLUMNS: tuple[str, ...] = (
    "t_over_t",
    "sin_1",
    "sin_2",
    "sin_3",
    "sin_4",
    "cos_1",
    "cos_2",
    "cos_3",
    "cos_4",
    "promo_flag",
    "advent_flag",
    "jan_dip_flag",
)
# Matches SPEC-04 globals: tau, gamma×8, delta_promo/advent/jan.
CONTROL_MU: tuple[float, ...] = (0.0,) + (0.0,) * 8 + (0.1, 0.3, -0.1)
CONTROL_SIGMA: tuple[float, ...] = (0.1,) + (0.15,) * 8 + (0.05, 0.15, 0.1)


class MappingRow(BaseModel):
    """One VR-602 mapping-doc row. Frozen."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    element: str
    ambo: str
    marketing: str
    status: Literal["matched", "unmatched"]
    note: str


class CrosscheckResult(BaseModel):
    """VR-602 JSON payload. Frozen."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    layer: str
    pymc_marketing_version: str
    n_channels: int
    n_obs: int
    wall_seconds: float | None
    n_divergences: int | None
    ambo_roas_median: dict[str, float]
    marketing_roas_median: dict[str, float]
    pearson: float
    spearman: float
    gate: float
    gate_passed: bool
    mapping: tuple[MappingRow, ...]


def installed_version() -> str:
    """Installed `pymc_marketing.__version__` (imported only here)."""
    import pymc_marketing

    return str(pymc_marketing.__version__)


def require_pinned_version() -> str:
    """Refuse to run against a different pin than 0.19.4 (RK-M3-2)."""
    got = installed_version()
    if got != EXPECTED_PYMC_MARKETING_VERSION:
        raise ValidationError(
            f"pymc-marketing {got} != pinned {EXPECTED_PYMC_MARKETING_VERSION} (VR-602)"
        )
    return got


def mapping_table() -> tuple[MappingRow, ...]:
    """Matched and unmatchable elements for the mapping doc (VR-602)."""
    return (
        MappingRow(
            element="adstock form",
            ambo="normalized geometric, L=8, causal (MD-020)",
            marketing="GeometricAdstock(l_max=8, normalize=True, mode=After)",
            status="matched",
            note="alpha is λ; Beta(2, 4) on both.",
        ),
        MappingRow(
            element="saturation form",
            ambo="Hill a^s/(a^s+K^s) then ×β (MD-021)",
            marketing="HillSaturation: β × hill_function(x, slope, kappa)",
            status="matched",
            note="slope=s, kappa=K, saturation_beta=β. Same closed form.",
        ),
        MappingRow(
            element="adstock then Hill",
            ambo="adstock_convolve then hill_saturation",
            marketing="adstock_first=True",
            status="matched",
            note="",
        ),
        MappingRow(
            element="λ / alpha prior",
            ambo="Beta(2, 4)",
            marketing="Prior('Beta', alpha=2, beta=4, dims=channel)",
            status="matched",
            note="",
        ),
        MappingRow(
            element="K / kappa prior",
            ambo="Gamma(shape=2, rate=1.3)",
            marketing="Prior('Gamma', alpha=2, beta=1.3, dims=channel)",
            status="matched",
            note="PyMC Gamma beta is the rate.",
        ),
        MappingRow(
            element="s / slope prior",
            ambo="Truncated Gamma(3, 2) on [0.3, 3.0]",
            marketing="untruncated Gamma(3, 2) on saturation_slope",
            status="unmatched",
            note="Prior('Truncated', dist=Prior('Gamma', ...)) names the inner RV; API refuses it.",
        ),
        MappingRow(
            element="β prior",
            ambo="HalfNormal(0.15)",
            marketing="Prior('HalfNormal', sigma=0.15, dims=channel)",
            status="matched",
            note="",
        ),
        MappingRow(
            element="intercept",
            ambo="Normal(1.0, 0.3) on mean-scaled revenue",
            marketing="Prior('Normal', mu=1.0, sigma=0.3) after FixedScaling",
            status="matched",
            note="",
        ),
        MappingRow(
            element="observation noise",
            ambo="HalfNormal(0.1) on scaled revenue",
            marketing="likelihood Normal with HalfNormal(0.1) sigma",
            status="matched",
            note="",
        ),
        MappingRow(
            element="scaling",
            ambo="MD-030: revenue mean; per-channel mean of positive spend weeks",
            marketing="FixedScaling with those exact ScaleFactors",
            status="matched",
            note="Default MMM max-abs is not used.",
        ),
        MappingRow(
            element="linear trend t/T",
            ambo="τ ~ Normal(0, 0.1) times t/T",
            marketing="t_over_t as a control; gamma_control μ=0 σ=0.1 at that slot",
            status="matched",
            note="MMM has no dedicated τ; HSGP time-varying intercept is a different model.",
        ),
        MappingRow(
            element="yearly Fourier",
            ambo="order 4, period 52.18 weeks, non-centered (ADR-005)",
            marketing="sin/cos injected as controls with Normal(0, 0.15)",
            status="unmatched",
            note="yearly_seasonality is day-of-year/365.25 + Laplace; no 52.18 knob.",
        ),
        MappingRow(
            element="promo / advent / jan",
            ambo="separate Normal priors with distinct μ, σ",
            marketing="same three flags as controls; per-slot μ, σ arrays on gamma_control",
            status="matched",
            note="Controls are unscaled in MMM; flags are already 0/1.",
        ),
        MappingRow(
            element="MMM class",
            ambo="raw PyMC in ambo.model.mmm",
            marketing="pymc_marketing.mmm.MMM (legacy in 0.19.4)",
            status="matched",
            note="VR-602 names MMM. Multidimensional MMM is the 0.20 replacement; not used.",
        ),
    )


def design_frame(frame: pd.DataFrame, channels: list[str]) -> pd.DataFrame:
    """Date, raw spend columns, t/T, SPEC-04 Fourier, and calendar flags."""
    n_weeks = len(frame)
    week_index = np.arange(1, n_weeks + 1, dtype=np.float64)
    sin_feat, cos_feat = fourier_features_for_weeks(week_index)
    out = pd.DataFrame({"week_start": pd.to_datetime(frame["week_start"])})
    for name in channels:
        out[name] = frame[f"spend_{name}"].to_numpy(dtype=np.float64)
    out["t_over_t"] = week_index / float(n_weeks)
    for order in range(FOURIER_ORDER):
        out[f"sin_{order + 1}"] = sin_feat[:, order]
    for order in range(FOURIER_ORDER):
        out[f"cos_{order + 1}"] = cos_feat[:, order]
    for flag in ("promo_flag", "advent_flag", "jan_dip_flag"):
        if flag not in frame.columns:
            raise ValidationError(f"crosscheck frame missing column {flag}")
        out[flag] = frame[flag].to_numpy(dtype=np.float64)
    return out


def channels_with_positive_spend(frame: pd.DataFrame) -> list[str]:
    """Taxonomy order, skip all-zero (Layer P `other`)."""
    names: list[str] = []
    for name in SPEC_CHANNEL_ORDER:
        column = f"spend_{name}"
        if column not in frame.columns:
            continue
        if np.any(frame[column].to_numpy(dtype=np.float64) > 0.0):
            names.append(name)
    return names


def median_correlations(ambo: dict[str, float], marketing: dict[str, float]) -> tuple[float, float]:
    """Pearson and Spearman of per-channel posterior-median ROAS."""
    keys = [name for name in SPEC_CHANNEL_ORDER if name in ambo and name in marketing]
    if len(keys) < 2:
        raise ValidationError("need >= 2 shared channels to correlate ROAS medians")
    left = np.asarray([ambo[name] for name in keys], dtype=np.float64)
    right = np.asarray([marketing[name] for name in keys], dtype=np.float64)
    pearson = float(pearsonr(left, right).statistic)
    spearman = float(spearmanr(left, right).statistic)
    if not np.isfinite(pearson) or not np.isfinite(spearman):
        raise ValidationError("ROAS-median correlation is not finite")
    return pearson, spearman


def channel_roas_medians(idata: Any, spend_totals: dict[str, float]) -> dict[str, float]:
    """Average ROAS = Σ contribution_original_scale / Σ spend, posterior median."""
    if (
        not hasattr(idata, "posterior")
        or "channel_contribution_original_scale" not in idata.posterior
    ):
        raise ValidationError("idata missing posterior.channel_contribution_original_scale")
    contrib = idata.posterior["channel_contribution_original_scale"]
    totals = _sum_over_time(contrib)
    medians = totals.median(dim=("chain", "draw"))
    out: dict[str, float] = {}
    for name, spend in spend_totals.items():
        if spend <= 0.0:
            raise ValidationError(f"channel {name!r} has zero total spend")
        out[name] = float(medians.sel(channel=name).item()) / spend
    return out


def build_crosscheck_mmm(channels: list[str], scale_factors: ScaleFactors, length: int) -> Any:
    """Construct (do not sample) a 0.19.4 MMM matched to SPEC-04 as far as the API goes."""
    from pymc_extras.prior import Prior
    from pymc_marketing.mmm import MMM, GeometricAdstock, HillSaturation
    from pymc_marketing.mmm.scaling import FixedScaling, Scaling

    if length < 1:
        raise ValidationError(f"adstock length must be >= 1, got {length!r}")
    _require_control_prior_len()
    channel_scales = {name: float(scale_factors.spend_means[name]) for name in channels}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        return MMM(
            date_column="week_start",
            channel_columns=list(channels),
            adstock=GeometricAdstock(
                l_max=length,
                normalize=True,
                priors={"alpha": Prior("Beta", alpha=2.0, beta=4.0)},
            ),
            saturation=HillSaturation(
                priors={
                    "slope": Prior("Gamma", alpha=3.0, beta=2.0),
                    "kappa": Prior("Gamma", alpha=2.0, beta=1.3),
                    "beta": Prior("HalfNormal", sigma=0.15),
                }
            ),
            control_columns=list(CONTROL_COLUMNS),
            yearly_seasonality=None,
            adstock_first=True,
            scaling=Scaling(
                target=FixedScaling(dims=(), value=float(scale_factors.revenue_mean)),
                channel=FixedScaling(dims=(), value=channel_scales),
            ),
            model_config=_model_config(Prior),
        )


def run_crosscheck(
    layer: str,
    *,
    frame: pd.DataFrame | None = None,
    bayesian_roas: dict[str, float] | None = None,
    idata: Any | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Fit (or accept) a marketing MMM and write JSON + mapping markdown.

    Implements: VR-602
    """
    version = require_pinned_version()
    loaded = frame if frame is not None else read_mmm_input(layer)
    channels = channels_with_positive_spend(loaded)
    if not channels:
        raise ValidationError(f"crosscheck: no spend channels on {layer}")
    ambo_roas = bayesian_roas if bayesian_roas is not None else _bayesian_roas(layer)
    spend_totals = {name: float(loaded[f"spend_{name}"].sum()) for name in channels}
    wall: float | None = None
    n_div: int | None = None
    fitted = idata
    if fitted is None:
        fitted, wall, n_div = _fit_marketing(loaded, channels)
    marketing_roas = channel_roas_medians(fitted, spend_totals)
    pearson, spearman = median_correlations(ambo_roas, marketing_roas)
    result = CrosscheckResult(
        layer=layer,
        pymc_marketing_version=version,
        n_channels=len(channels),
        n_obs=len(loaded),
        wall_seconds=wall,
        n_divergences=n_div,
        ambo_roas_median={name: float(ambo_roas[name]) for name in channels},
        marketing_roas_median={name: float(marketing_roas[name]) for name in channels},
        pearson=pearson,
        spearman=spearman,
        gate=CORRELATION_GATE,
        gate_passed=bool(pearson >= CORRELATION_GATE and spearman >= CORRELATION_GATE),
        mapping=mapping_table(),
    )
    dest = _json_path(layer, output_dir)
    _atomic_write_json(result.model_dump(mode="json"), dest)
    md_path = dest.with_name("crosscheck_mapping.md")
    md_path.write_text(render_mapping_markdown(result), encoding="utf-8")
    LOGGER.info("Wrote cross-check %s and %s", dest, md_path)
    return dest


def render_mapping_markdown(result: CrosscheckResult) -> str:
    """SPEC-05 VR-602 mapping document."""
    lines = [
        "# pymc-marketing cross-check mapping (VR-602)",
        "",
        f"Installed `pymc_marketing.__version__`: **{result.pymc_marketing_version}**",
        f"(pin `{EXPECTED_PYMC_MARKETING_VERSION}`).",
        "",
        f"Layer: `{result.layer}`. Channels: {result.n_channels}. Weeks: {result.n_obs}.",
        "",
        "## Correlation gate",
        "",
        f"- Pearson of channel posterior-median ROAS: {result.pearson:.4f}",
        f"- Spearman of channel posterior-median ROAS: {result.spearman:.4f}",
        f"- Gate: both ≥ {result.gate}. **{'PASS' if result.gate_passed else 'FAIL'}**.",
        "",
        "## Per-channel median ROAS",
        "",
        "| Channel | ambo (raw PyMC) | pymc-marketing |",
        "|---|---:|---:|",
    ]
    for name in result.ambo_roas_median:
        left = result.ambo_roas_median[name]
        right = result.marketing_roas_median[name]
        lines.append(f"| `{name}` | {left:.4f} | {right:.4f} |")
    lines.extend(
        [
            "",
            "## Transform and prior mapping",
            "",
            "| Element | ambo | pymc-marketing 0.19.4 | Status | Note |",
            "|---|---|---|---|---|",
        ]
    )
    for row in result.mapping:
        note = row.note.replace("|", "\\|")
        lines.append(f"| {row.element} | {row.ambo} | {row.marketing} | {row.status} | {note} |")
    lines.extend(
        [
            "",
            "## What this does and does not prove",
            "",
            "A high correlation says two independently implemented Hill-adstock MMMs",
            "rank channels similarly on S-B. It is not a claim that pymc-marketing is",
            "calibrated to truth (that is SPEC-05 §3 against `truth.json`), and it is",
            "not a reason to replace the raw-PyMC model. Unmatched rows above are API",
            "limits, not silent deviations (A-1).",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m ambo.validate.crosscheck --layer P-SB``."""
    parser = argparse.ArgumentParser(prog="python -m ambo.validate.crosscheck")
    parser.add_argument("--layer", default="P-SB")
    args = parser.parse_args(argv)
    try:
        run_crosscheck(args.layer)
    except ValidationError:
        LOGGER.exception("crosscheck failed")
        return 1
    return 0


def _model_config(prior_cls: Any) -> dict[str, Any]:
    return {
        "intercept": prior_cls("Normal", mu=1.0, sigma=0.3),
        "likelihood": prior_cls("Normal", sigma=prior_cls("HalfNormal", sigma=0.1)),
        "gamma_control": prior_cls(
            "Normal",
            mu=list(CONTROL_MU),
            sigma=list(CONTROL_SIGMA),
            dims="control",
        ),
    }


def _require_control_prior_len() -> None:
    n_ctrl = len(CONTROL_COLUMNS)
    if len(CONTROL_MU) != n_ctrl or len(CONTROL_SIGMA) != n_ctrl:
        raise ValidationError("CONTROL_MU/SIGMA length must equal CONTROL_COLUMNS")


def _fit_marketing(frame: pd.DataFrame, channels: list[str]) -> tuple[Any, float, int]:
    settings = load_settings()
    scale_factors = compute_scale_factors(frame, channels)
    mmm = build_crosscheck_mmm(channels, scale_factors, settings.adstock_length)
    x_design = design_frame(frame, channels)
    y = frame["revenue"].to_numpy(dtype=np.float64)
    sampler = settings.sampler
    started = time.perf_counter()
    idata = mmm.fit(
        x_design,
        y,
        draws=sampler.draws,
        tune=sampler.tune,
        chains=sampler.chains,
        target_accept=sampler.target_accept,
        random_seed=sampler.random_seed,
        init=sampler.init,
    )
    wall = time.perf_counter() - started
    n_div = _count_divergences(idata)
    LOGGER.info("pymc-marketing fit wall %.1fs, divergences=%s", wall, n_div)
    return idata, wall, n_div


def _count_divergences(idata: Any) -> int:
    if not hasattr(idata, "sample_stats") or "diverging" not in idata.sample_stats:
        return 0
    return int(np.asarray(idata.sample_stats["diverging"]).sum())


def _sum_over_time(contrib: Any) -> Any:
    skip = {"chain", "draw", "channel"}
    time_dims = [dim for dim in contrib.dims if dim not in skip]
    return contrib.sum(dim=time_dims) if time_dims else contrib


def _bayesian_roas(layer: str) -> dict[str, float]:
    import tempfile

    from ambo.validate.recovery import compute_recovery

    with tempfile.TemporaryDirectory() as tmp:
        metrics = compute_recovery(layer, output_dir=Path(tmp))
    return {row.channel: row.roas_median for row in metrics.channels}


def _json_path(layer: str, output_dir: Path | None) -> Path:
    directory = output_dir if output_dir is not None else load_settings().paths.reports / "recovery"
    return Path(directory) / f"crosscheck_{layer}.json"


def _atomic_write_json(payload: dict[str, Any], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.tmp-{os.getpid()}")
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()


if __name__ == "__main__":
    sys.exit(main())
