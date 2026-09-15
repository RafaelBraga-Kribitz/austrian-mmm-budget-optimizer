"""Sampler-health gates (MD-071 / MD-072). Pure evaluation plus a markdown writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np

from ambo.config import REPORTS_DIR
from ambo.plots.theme import apply_theme, tokens


@dataclass(frozen=True)
class DiagGates:
    rhat_max: float = 1.01
    ess_min: float = 400.0
    divergences_max: int = 0
    bfmi_min: float = 0.3
    ppc_coverage_min: float = 0.85


@dataclass(frozen=True)
class GateCheck:
    name: str
    passed: bool
    statistic: float | None
    threshold: str
    detail: str


@dataclass(frozen=True)
class DiagResult:
    checks: tuple[GateCheck, ...]
    all_green: bool
    n_divergences: int
    ppc_coverage: float | None


def run_diagnostics(idata: az.InferenceData, gates: DiagGates | None = None) -> DiagResult:
    gates = gates or DiagGates()
    rhat_max = _extreme(az.rhat(idata), np.nanmax)
    ess_bulk = _extreme(az.ess(idata, method="bulk"), np.nanmin)
    ess_tail = _extreme(az.ess(idata, method="tail"), np.nanmin)
    n_div = _n_divergences(idata)
    bfmi = _bfmi_min(idata)
    ppc = _ppc_coverage(idata)
    checks = (
        _check("R-hat", rhat_max, f"< {gates.rhat_max}", _lt(rhat_max, gates.rhat_max)),
        _check("ESS_bulk", ess_bulk, f"> {gates.ess_min:g}", _gt(ess_bulk, gates.ess_min)),
        _check("ESS_tail", ess_tail, f"> {gates.ess_min:g}", _gt(ess_tail, gates.ess_min)),
        _check(
            "divergences",
            float(n_div),
            f"<= {gates.divergences_max}",
            n_div <= gates.divergences_max,
        ),
        _check("BFMI", bfmi, f"> {gates.bfmi_min}", _gt(bfmi, gates.bfmi_min)),
        _ppc_check(ppc, gates.ppc_coverage_min),
    )
    return DiagResult(
        checks=checks,
        all_green=all(item.passed for item in checks),
        n_divergences=n_div,
        ppc_coverage=ppc,
    )


def write_diag_report(res: DiagResult, idata: az.InferenceData, *, layer: str = "P") -> Path:
    out_dir = REPORTS_DIR / "model"
    out_dir.mkdir(parents=True, exist_ok=True)
    ppc_path = out_dir / f"ppc_{layer}.png"
    _write_ppc_plot(idata, ppc_path)
    energy_path: Path | None = None
    if res.n_divergences > 0:
        energy_path = out_dir / f"energy_{layer}.png"
        _write_energy_plot(idata, energy_path)
    dest = out_dir / f"diag_{layer}.md"
    dest.write_text(_render(res, layer, ppc_path, energy_path), encoding="utf-8")
    return dest


def _check(name: str, statistic: float, threshold: str, passed: bool) -> GateCheck:
    return GateCheck(name, passed, statistic, threshold, "PASS" if passed else "FAIL")


def _ppc_check(coverage: float | None, minimum: float) -> GateCheck:
    if coverage is None:
        return GateCheck("PPC_90", False, None, f">= {minimum:.0%}", "posterior predictive missing")
    return GateCheck(
        "PPC_90",
        coverage >= minimum,
        coverage,
        f">= {minimum:.0%}",
        "PASS" if coverage >= minimum else "FAIL",
    )


def _lt(value: float, limit: float) -> bool:
    return bool(np.isfinite(value) and value < limit)


def _gt(value: float, limit: float) -> bool:
    return bool(np.isfinite(value) and value > limit)


def _extreme(dataset: Any, reducer: Any) -> float:
    values = np.asarray(dataset.to_array(), dtype=float).ravel()
    if values.size == 0:
        return float("nan")
    return float(reducer(values))


def _n_divergences(idata: az.InferenceData) -> int:
    stats = getattr(idata, "sample_stats", None)
    if stats is None or "diverging" not in stats:
        raise ValueError("InferenceData sample_stats.diverging is required")
    return int(np.asarray(stats["diverging"]).sum())


def _bfmi_min(idata: az.InferenceData) -> float:
    values = np.asarray(az.bfmi(idata), dtype=float).ravel()
    if values.size == 0:
        return float("nan")
    return float(np.nanmin(values))


def _ppc_coverage(idata: az.InferenceData) -> float | None:
    ppc = getattr(idata, "posterior_predictive", None)
    obs = getattr(idata, "observed_data", None)
    if ppc is None or obs is None or "y" not in ppc or "y" not in obs:
        return None
    stacked = ppc["y"].stack(sample=("chain", "draw"))
    lower = stacked.quantile(0.05, dim="sample")
    upper = stacked.quantile(0.95, dim="sample")
    inside = (obs["y"] >= lower) & (obs["y"] <= upper)
    return float(np.asarray(inside, dtype=float).mean())


def _write_ppc_plot(idata: az.InferenceData, path: Path) -> None:
    apply_theme()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    ppc = getattr(idata, "posterior_predictive", None)
    obs = getattr(idata, "observed_data", None)
    color = tokens()
    if ppc is None or obs is None or "y" not in getattr(ppc, "data_vars", []):
        ax.set_title("PPC unavailable")
    else:
        stacked = ppc["y"].stack(sample=("chain", "draw"))
        lower = np.asarray(stacked.quantile(0.05, dim="sample")).ravel()
        upper = np.asarray(stacked.quantile(0.95, dim="sample")).ravel()
        y = np.asarray(obs["y"]).ravel()
        weeks = np.arange(y.size)
        ax.fill_between(
            weeks, lower, upper, color=color["accent-02"], alpha=1.0, linewidth=0, label="90% PPC"
        )
        # Recessive band: use surface-2 hatch via a second series at mid, not alpha.
        ax.plot(weeks, y, color=color["ink"], label="observed")
        ax.set_xlabel("week")
        ax.set_ylabel("y (scaled)")
        ax.legend()
        ax.set_title("Posterior predictive (90% band)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _write_energy_plot(idata: az.InferenceData, path: Path) -> None:
    apply_theme()
    import matplotlib.pyplot as plt

    az.plot_energy(idata)
    plt.savefig(path, dpi=120)
    plt.close()


def _render(res: DiagResult, layer: str, ppc_path: Path, energy_path: Path | None) -> str:
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
        energy_note = f"\nEnergy plot (divergences={res.n_divergences}): `{energy_path.name}`.\n"
    verdict = "all-green" if res.all_green else "RED"
    return (
        f"# Diagnostics — {layer}\n\n"
        f"Profile: `{verdict}`.\n\n"
        + "\n".join(rows)
        + f"\n\nPPC plot: `{ppc_path.name}`.\n"
        + energy_note
        + "\n"
    )
