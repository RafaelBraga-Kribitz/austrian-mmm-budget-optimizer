"""Sampler-health and PPC gates (MD-071 / MD-072 / MD-074).

`DiagGates.standard()` and `DiagGates.layer_r()` are explicit constructors —
`run_diagnostics` never picks a profile from series length or layer name.
PPC 90% coverage is always evaluated; a missing posterior predictive is a
failed MD-072 gate, not a skipped one.

Implements: MD-071, MD-072, MD-074
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np

from ambo.common.config import load_settings
from ambo.common.errors import FitError
from ambo.common.logging import get_logger

# arviz is untyped; numeric results are checked in tests (T-306).
# mypy: disable-error-code="no-untyped-call"

LOGGER = get_logger(__name__)

_PPC_MASS = 0.90
_PPC_LOWER = (1.0 - _PPC_MASS) / 2.0
_PPC_UPPER = 1.0 - _PPC_LOWER


@dataclass(frozen=True)
class DiagGates:
    """Thresholds for one diagnostic profile. Construct explicitly at the call site.

    Implements: MD-071, MD-074
    """

    rhat_max: float
    ess_min: float
    divergences_max: int
    bfmi_min: float
    ppc_coverage_min: float

    @classmethod
    def standard(cls) -> DiagGates:
        """MD-071: R-hat < 1.01, ESS > 400, divergences = 0, BFMI > 0.3; PPC ≥ 85%."""
        return cls(
            rhat_max=1.01,
            ess_min=400.0,
            divergences_max=0,
            bfmi_min=0.3,
            ppc_coverage_min=0.85,
        )

    @classmethod
    def layer_r(cls) -> DiagGates:
        """MD-074: ESS > 300, divergences ≤ 5; other MD-071/072 thresholds unchanged."""
        return cls(
            rhat_max=1.01,
            ess_min=300.0,
            divergences_max=5,
            bfmi_min=0.3,
            ppc_coverage_min=0.85,
        )


@dataclass(frozen=True)
class GateCheck:
    """One row of the diagnostic table."""

    name: str
    passed: bool
    statistic: float | None
    threshold: str
    detail: str


@dataclass(frozen=True)
class DiagResult:
    """Pure diagnostic evaluation. Plots are written separately.

    Implements: MD-071, MD-072, MD-074
    """

    profile: str
    gates: DiagGates
    checks: tuple[GateCheck, ...]
    all_green: bool
    n_divergences: int
    ppc_coverage: float | None


def run_diagnostics(idata: az.InferenceData, gates: DiagGates) -> DiagResult:
    """Evaluate MD-071/072/074 against `gates`. Pure: no files, no profile heuristic.

    Implements: MD-071, MD-072, MD-074
    """
    rhat_max = _rhat_max(idata)
    ess_bulk_min = _ess_min(idata, method="bulk")
    ess_tail_min = _ess_min(idata, method="tail")
    n_div = _n_divergences(idata)
    bfmi_min = _bfmi_min(idata)
    ppc = _ppc_coverage(idata)
    checks = (
        _check("R-hat", rhat_max, f"< {gates.rhat_max}", _finite_lt(rhat_max, gates.rhat_max)),
        _check(
            "ESS_bulk",
            ess_bulk_min,
            f"> {gates.ess_min:g}",
            _finite_gt(ess_bulk_min, gates.ess_min),
        ),
        _check(
            "ESS_tail",
            ess_tail_min,
            f"> {gates.ess_min:g}",
            _finite_gt(ess_tail_min, gates.ess_min),
        ),
        _check(
            "divergences",
            float(n_div),
            f"<= {gates.divergences_max}",
            n_div <= gates.divergences_max,
        ),
        _check("BFMI", bfmi_min, f"> {gates.bfmi_min}", _finite_gt(bfmi_min, gates.bfmi_min)),
        _ppc_check(ppc, gates.ppc_coverage_min),
    )
    return DiagResult(
        profile=_profile_name(gates),
        gates=gates,
        checks=checks,
        all_green=all(item.passed for item in checks),
        n_divergences=n_div,
        ppc_coverage=ppc,
    )


def write_diag_report(
    res: DiagResult,
    layer: str,
    *,
    idata: az.InferenceData,
    directory: Path | None = None,
) -> Path:
    """Write `diag_<layer>.md` plus PPC PNG; energy PNG when divergences > 0.

    Implements: MD-071, MD-072, MD-074
    """
    if not layer or layer != Path(layer).name:
        raise FitError(f"diag layer {layer!r} must be a basename")
    out_dir = directory if directory is not None else load_settings().paths.reports / "model"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ppc_path = out_dir / f"ppc_{layer}.png"
    _write_ppc_plot(idata, ppc_path)
    energy_path: Path | None = None
    if res.n_divergences > 0:
        energy_path = out_dir / f"energy_{layer}.png"
        _write_energy_plot(idata, energy_path)
    dest = out_dir / f"diag_{layer}.md"
    _atomic_write_text(_render_markdown(res, layer, ppc_path, energy_path), dest)
    LOGGER.info("Wrote diag report %s (all_green=%s)", dest, res.all_green)
    return dest


def _profile_name(gates: DiagGates) -> str:
    if gates == DiagGates.standard():
        return "standard"
    if gates == DiagGates.layer_r():
        return "layer_r"
    return "custom"


def _check(name: str, statistic: float, threshold: str, passed: bool) -> GateCheck:
    detail = "PASS" if passed else "FAIL"
    return GateCheck(
        name=name, passed=passed, statistic=statistic, threshold=threshold, detail=detail
    )


def _ppc_check(coverage: float | None, minimum: float) -> GateCheck:
    if coverage is None:
        return GateCheck(
            name="PPC_90",
            passed=False,
            statistic=None,
            threshold=f">= {minimum:.0%}",
            detail="posterior predictive missing — MD-072 evaluated, not dropped",
        )
    passed = coverage >= minimum
    return GateCheck(
        name="PPC_90",
        passed=passed,
        statistic=coverage,
        threshold=f">= {minimum:.0%}",
        detail="PASS" if passed else "FAIL",
    )


def _finite_lt(value: float, limit: float) -> bool:
    return bool(np.isfinite(value) and value < limit)


def _finite_gt(value: float, limit: float) -> bool:
    return bool(np.isfinite(value) and value > limit)


def _rhat_max(idata: az.InferenceData) -> float:
    return _dataset_extreme(az.rhat(idata), np.nanmax)


def _ess_min(idata: az.InferenceData, *, method: str) -> float:
    return _dataset_extreme(az.ess(idata, method=method), np.nanmin)


def _dataset_extreme(dataset: Any, reducer: Any) -> float:
    values = np.asarray(dataset.to_array(), dtype=float).ravel()
    if values.size == 0:
        return float("nan")
    return float(reducer(values))


def _n_divergences(idata: az.InferenceData) -> int:
    stats = getattr(idata, "sample_stats", None)
    if stats is None or "diverging" not in stats:
        raise FitError("InferenceData sample_stats.diverging is required for MD-071")
    return int(np.asarray(stats["diverging"]).sum())


def _bfmi_min(idata: az.InferenceData) -> float:
    try:
        values = np.asarray(az.bfmi(idata), dtype=np.float64).ravel()
    except (TypeError, ValueError, KeyError) as exc:
        raise FitError("InferenceData sample_stats.energy is required for MD-071") from exc
    if values.size == 0:
        return float("nan")
    return float(np.nanmin(values))


def _ppc_coverage(idata: az.InferenceData) -> float | None:
    ppc_group = getattr(idata, "posterior_predictive", None)
    obs_group = getattr(idata, "observed_data", None)
    if ppc_group is None or obs_group is None:
        return None
    name = "y" if "y" in ppc_group else next(iter(ppc_group.data_vars), None)
    if name is None or name not in obs_group:
        return None
    stacked = ppc_group[name].stack(sample=("chain", "draw"))
    lower = stacked.quantile(_PPC_LOWER, dim="sample")
    upper = stacked.quantile(_PPC_UPPER, dim="sample")
    obs = obs_group[name]
    inside = (obs >= lower) & (obs <= upper)
    return float(np.asarray(inside, dtype=float).mean())


def _write_ppc_plot(idata: az.InferenceData, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ppc_group = getattr(idata, "posterior_predictive", None)
    obs_group = getattr(idata, "observed_data", None)
    fig, ax = plt.subplots(figsize=(8, 4))
    if ppc_group is None or obs_group is None or "y" not in getattr(ppc_group, "data_vars", []):
        ax.set_title("PPC unavailable")
    else:
        stacked = ppc_group["y"].stack(sample=("chain", "draw"))
        lower = np.asarray(stacked.quantile(_PPC_LOWER, dim="sample"))
        upper = np.asarray(stacked.quantile(_PPC_UPPER, dim="sample"))
        obs = np.asarray(obs_group["y"])
        weeks = np.arange(obs.size)
        ax.fill_between(weeks, lower.ravel(), upper.ravel(), alpha=0.3, label="90% PPC")
        ax.plot(weeks, obs.ravel(), color="black", label="observed")
        ax.set_xlabel("week")
        ax.set_ylabel("y (scaled)")
        ax.legend()
        ax.set_title("Posterior predictive (90% band)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _write_energy_plot(idata: az.InferenceData, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    az.plot_energy(idata)
    plt.savefig(path, dpi=120)
    plt.close()


def _render_markdown(res: DiagResult, layer: str, ppc_path: Path, energy_path: Path | None) -> str:
    rows = [
        "| Gate | Threshold | Statistic | Result |",
        "|------|-----------|-----------|--------|",
    ]
    for check in res.checks:
        stat = "—" if check.statistic is None else f"{check.statistic:.4g}"
        mark = "PASS" if check.passed else "FAIL"
        rows.append(f"| {check.name} | {check.threshold} | {stat} | {mark} |")
    energy_note = ""
    if energy_path is not None:
        energy_note = (
            f"\nEnergy plot (divergences={res.n_divergences}): `{energy_path.name}`.\n"
            "MD-074 funnel review of pair plots is a human note, not auto-generated.\n"
        )
    verdict = "all-green" if res.all_green else "RED"
    return (
        f"# Diagnostics — {layer}\n\n"
        f"Profile: `{res.profile}` ({verdict}).\n\n"
        + "\n".join(rows)
        + f"\n\nPPC plot: `{ppc_path.name}`.\n"
        + energy_note
        + "\n"
    )


def _atomic_write_text(text: str, dest: Path) -> None:
    tmp_path = dest.with_suffix(dest.suffix + f".tmp-{os.getpid()}")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, dest)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
