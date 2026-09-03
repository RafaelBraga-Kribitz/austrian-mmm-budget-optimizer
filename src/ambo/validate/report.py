"""Generate `RECOVERY_REPORT.md` from committed posteriors (VR-703 / SPEC-05 §8).

Implements: VR-703

Templates with slots. Plots from parquets. Does not call `pm.sample`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import arviz as az
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytensor
import pytensor.tensor as pt

from ambo.common.config import SPEC_CHANNEL_ORDER, load_settings
from ambo.common.db import read_mmm_input
from ambo.common.errors import FitError, ValidationError
from ambo.common.logging import get_logger
from ambo.model.posterior_io import PosteriorBundle, load_posterior
from ambo.model.transforms import hill_saturation
from ambo.simulate.config import TrueParams
from ambo.simulate.truth import TruthFile, response_curve_at
from ambo.validate.baseline_ols import OLSResult
from ambo.validate.crosscheck import CrosscheckResult
from ambo.validate.holdout import CSV_COLUMNS
from ambo.validate.recovery import (
    LAYER_TO_SCENARIO,
    GateResults,
    RecoveryMetrics,
    compute_recovery,
    evaluate_gates,
)

# mypy: disable-error-code="no-untyped-call,attr-defined,no-any-return"

LOGGER = get_logger(__name__)

LAYERS: tuple[str, ...] = ("P-SA", "P-SB", "P-SC")
SECTION_HEADINGS: tuple[str, ...] = (
    "## Verdict",
    "## Gate table",
    "## Recovery plots",
    "## Zero-effect channel (S-C)",
    "## Holdout",
    "## OLS baseline",
    "## pymc-marketing cross-check",
    "## What this does and does not prove",
)
_GRID_POINTS = 21
_GRID_MAX_MULTIPLE = 1.5
_HDI_PROB = 0.9
_CLOSING_MIN_CHARS = 500

VERDICT_TEMPLATE = (
    "The model recovers known truth under {conditions}; it fails gracefully under "
    "{stress}. Gated SPEC-05 §3 cells: S-A {sa_status}; S-B {sb_status}; "
    "S-C {sc_status}."
)

CLOSING_TEMPLATE = (
    "This recovery suite shows that the raw-PyMC MMM recovers disclosed simulator "
    "truth it was never shown, under the Layer-P conditions encoded in "
    "config/recovery_gates.yaml (S-A clean, S-B flighted, S-C zero-effect). That "
    "is not a guarantee on an unknown real-world data-generating process: S-B "
    "already pairs spend with the demand calendar so Fourier terms compete with "
    "media (AGENTS T-4), and Layer R will be shorter and messier. Recovery is "
    "gated on ROAS and response-curve shape at observed spend, not on point "
    "recovery of Hill K and s (T-5). The MD-020 parameterization mismatch is "
    "load-bearing: the simulator uses raw geometric recursion while the model "
    "uses a finite-length normalized convolution, so agreement is evidence rather "
    "than a circular identity. Real-world validation would require lift tests "
    "(Charter O-1, Future work), which this project does not run. Brand search "
    "is modelled because it absorbs demand-correlated variance, but it is not "
    "an optimizer lever (T-7). Platform-reported conversions remain the object "
    "of the attribution-gap study, never a calibration target (T-8)."
)


def generate_recovery_report(*, output_dir: Path | None = None) -> Path:
    """Write RECOVERY_REPORT.md and recovery plots. Zero sampling (VR-703)."""
    _apply_style()
    dest_dir = output_dir if output_dir is not None else load_settings().paths.reports / "recovery"
    dest_dir.mkdir(parents=True, exist_ok=True)
    packed = [_load_layer(layer, dest_dir) for layer in LAYERS]
    plot_rel: list[str] = []
    for item in packed:
        plot_rel.extend(_write_layer_plots(item, dest_dir))
    markdown = _render(packed, plot_rel)
    _assert_section_order(markdown)
    if len(_closing_body(markdown)) < _CLOSING_MIN_CHARS:
        raise ValidationError("closing section must be >= 500 characters")
    report = dest_dir / "RECOVERY_REPORT.md"
    report.write_text(markdown, encoding="utf-8")
    LOGGER.info("Wrote %s", report)
    return report


def section_headings_in(markdown: str) -> list[str]:
    """Level-2 headings in document order (test helper)."""
    return [line.strip() for line in markdown.splitlines() if line.startswith("## ")]


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m ambo.validate.report``."""
    parser = argparse.ArgumentParser(prog="python -m ambo.validate.report")
    parser.parse_args(argv)
    try:
        generate_recovery_report()
    except (ValidationError, FitError, OSError):
        LOGGER.exception("recover failed")
        return 1
    return 0


def _load_layer(layer: str, output_dir: Path) -> dict[str, Any]:
    _require_parquet(layer)
    metrics = compute_recovery(layer, output_dir=output_dir)
    gates = evaluate_gates(metrics, output_dir=output_dir)
    bundle = load_posterior(layer)
    frame = read_mmm_input(layer)
    truth = _load_truth(layer)
    return {
        "layer": layer,
        "scenario": LAYER_TO_SCENARIO[layer],
        "metrics": metrics,
        "gates": gates,
        "bundle": bundle,
        "frame": frame,
        "truth": truth,
    }


def _require_parquet(layer: str) -> None:
    path = load_settings().paths.posteriors / f"{layer}.parquet"
    if not path.is_file():
        raise ValidationError(
            f"missing {path}; run make fit-synthetic before make recover (VR-703)"
        )


def _load_truth(layer: str) -> TruthFile:
    scenario = LAYER_TO_SCENARIO[layer]
    settings = load_settings()
    path = settings.paths.data_synthetic / scenario / "truth.json"
    if not path.is_file():
        raise ValidationError(f"truth file not found for {layer}")
    return TruthFile.model_validate_json(path.read_text(encoding="utf-8"))


def _write_layer_plots(item: dict[str, Any], dest_dir: Path) -> tuple[str, str]:
    layer = item["layer"]
    roas_name = f"roas_{layer}.png"
    curve_name = f"curves_{layer}.png"
    _plot_roas(item, dest_dir / roas_name)
    _plot_curves(item, dest_dir / curve_name)
    return roas_name, curve_name


def _plot_roas(item: dict[str, Any], dest: Path) -> None:
    metrics: RecoveryMetrics = item["metrics"]
    names = [row.channel for row in metrics.channels]
    med = np.array([row.roas_median for row in metrics.channels])
    low = np.array([row.roas_hdi_low for row in metrics.channels])
    high = np.array([row.roas_hdi_high for row in metrics.channels])
    truth = np.array([row.true_avg_roas for row in metrics.channels])
    xpos = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    ax.errorbar(
        xpos,
        med,
        yerr=[med - low, high - med],
        fmt="o",
        capsize=4,
        label="posterior median + 90% HDI",
    )
    ax.scatter(xpos, truth, marker="x", s=80, color="black", label="truth", zorder=3)
    ax.set_xticks(xpos)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("average ROAS")
    ax.set_title(f"{item['layer']} ROAS recovery")
    ax.legend()
    fig.tight_layout()
    fig.savefig(dest, dpi=120)
    plt.close(fig)


def _plot_curves(item: dict[str, Any], dest: Path) -> None:
    metrics: RecoveryMetrics = item["metrics"]
    bundle: PosteriorBundle = item["bundle"]
    frame: pd.DataFrame = item["frame"]
    truth: TruthFile = item["truth"]
    truth_by = {row.channel: row for row in truth.channels}
    n_ch = len(metrics.channels)
    cols = 3
    rows = int(np.ceil(n_ch / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(11.0, 3.2 * rows), squeeze=False)
    hill_fn = _hill_fn()
    for i, rec in enumerate(metrics.channels):
        ax = axes[i // cols][i % cols]
        _one_curve(ax, rec.channel, bundle, frame, truth_by[rec.channel], hill_fn)
    for j in range(n_ch, rows * cols):
        axes[j // cols][j % cols].set_visible(False)
    fig.suptitle(f"{item['layer']} response curves (MD-082 grid)")
    fig.tight_layout()
    fig.savefig(dest, dpi=120)
    plt.close(fig)


def _one_curve(
    ax: Any,
    channel: str,
    bundle: PosteriorBundle,
    frame: pd.DataFrame,
    truth_row: Any,
    hill_fn: Any,
) -> None:
    x_eur = frame[f"spend_{channel}"].to_numpy(dtype=np.float64)
    grid = np.linspace(0.0, _GRID_MAX_MULTIPLE * float(np.max(x_eur)), _GRID_POINTS)
    params = TrueParams(lam=truth_row.lam, K=truth_row.K, s=truth_row.s, beta=truth_row.beta)
    true_curve = np.asarray(response_curve_at(params, grid), dtype=np.float64)
    spend_mean = float(bundle.scale_factors.spend_means[channel])
    revenue_mean = float(bundle.scale_factors.revenue_mean)
    k = bundle.draws[f"k__{channel}"].to_numpy(dtype=np.float64)
    s = bundle.draws[f"s__{channel}"].to_numpy(dtype=np.float64)
    beta = bundle.draws[f"beta__{channel}"].to_numpy(dtype=np.float64)
    x_scaled = grid / spend_mean
    stacked = np.stack(
        [
            np.asarray(hill_fn(x_scaled, k[i], s[i], beta[i]), dtype=np.float64)
            for i in range(beta.shape[0])
        ]
    )
    band = stacked * revenue_mean
    median = np.median(band, axis=0)
    hdi = np.vstack([az.hdi(band[:, j], hdi_prob=_HDI_PROB) for j in range(band.shape[1])])
    ax.fill_between(grid, hdi[:, 0], hdi[:, 1], alpha=0.25, label="90% HDI")
    ax.plot(grid, median, label="posterior median")
    ax.plot(grid, true_curve, linestyle="--", color="black", label="truth")
    ax.set_title(channel)
    ax.set_xlabel("weekly spend")
    ax.set_ylabel("contribution")


def _render(packed: list[dict[str, Any]], plot_rel: list[str]) -> str:
    by_layer = {item["layer"]: item for item in packed}
    lines = [
        "# Recovery report",
        "",
        "> Generated by `make recover` from committed thinned posteriors (VR-703).",
        "> Do not hand-edit.",
        "",
        SECTION_HEADINGS[0],
        "",
        _verdict(by_layer),
        "",
        SECTION_HEADINGS[1],
        "",
        _gate_table(by_layer),
        "",
        SECTION_HEADINGS[2],
        "",
        "True average ROAS is ×; posterior median is a dot with 90% HDI whiskers.",
        "Response curves use the MD-082 21-point grid on 0…1.5× max observed weekly spend.",
        "",
        *_plot_links(plot_rel),
        "",
        SECTION_HEADINGS[3],
        "",
        _zero_effect(by_layer["P-SC"]),
        "",
        SECTION_HEADINGS[4],
        "",
        _holdout_table(),
        "",
        SECTION_HEADINGS[5],
        "",
        _ols_section(),
        "",
        SECTION_HEADINGS[6],
        "",
        _crosscheck_section(),
        "",
        SECTION_HEADINGS[7],
        "",
        CLOSING_TEMPLATE,
        "",
    ]
    return "\n".join(lines)


def _verdict(by_layer: dict[str, dict[str, Any]]) -> str:
    return VERDICT_TEMPLATE.format(
        conditions="clean S-A and flighted S-B (Layer P, disclosed DGP)",
        stress="S-C's zero-effect `display_video` channel",
        sa_status=_status_slot(by_layer["P-SA"]["gates"]),
        sb_status=_status_slot(by_layer["P-SB"]["gates"]),
        sc_status=_status_slot(by_layer["P-SC"]["gates"]),
    )


def _status_slot(gates: GateResults) -> str:
    if gates.all_green:
        return "all-green"
    failed = [item.gate for item in gates.checks if item.gated and not item.passed]
    return "red (" + ", ".join(failed) + ")" if failed else "all-green"


def _gate_table(by_layer: dict[str, dict[str, Any]]) -> str:
    names = ("VR-301", "VR-302", "VR-303", "VR-304", "VR-305", "VR-306")
    header = "| Gate | S-A | S-B | S-C |"
    sep = "|---|---|---|---|"
    rows = [header, sep]
    for name in names:
        cells = [_cell(by_layer[layer]["gates"], name) for layer in LAYERS]
        rows.append("| " + " | ".join([name, *cells]) + " |")
    return "\n".join(rows)


def _cell(gates: GateResults, name: str) -> str:
    for item in gates.checks:
        if item.gate == name:
            if not item.gated:
                return f"n/a ({item.detail})"
            mark = "PASS" if item.passed else "FAIL"
            return f"{mark}: {item.detail}"
    return "missing"


def _plot_links(plot_rel: list[str]) -> list[str]:
    lines: list[str] = []
    for name in plot_rel:
        lines.append(f"![{name}]({name})")
        lines.append("")
    return lines


def _zero_effect(item: dict[str, Any]) -> str:
    metrics: RecoveryMetrics = item["metrics"]
    gates: GateResults = item["gates"]
    vr304 = next(check for check in gates.checks if check.gate == "VR-304")
    p_roas = metrics.vr304_p_roas_lt
    share = metrics.vr304_median_share
    p_txt = "n/a" if p_roas is None else f"{p_roas:.3f}"
    share_txt = "n/a" if share is None else f"{share:.3f}"
    headline = "PASS" if vr304.passed else "FAIL"
    return (
        f"**{headline}.** S-C `display_video` is the zero-effect channel: "
        f"P(ROAS < 0.2) = {p_txt}; median contribution share = {share_txt}. "
        f"{vr304.detail}."
    )


def _holdout_table() -> str:
    reports = load_settings().paths.reports
    header = "| Layer | model MAPE | naive MAPE | 90% coverage | beats naive |"
    sep = "|---|---:|---:|---:|:---:|"
    rows = [header, sep]
    for layer in LAYERS:
        path = reports / "model" / f"holdout_{layer}.csv"
        if not path.is_file():
            raise ValidationError(f"missing {path}; run holdout before make recover")
        frame = pd.read_csv(path)
        missing = [col for col in CSV_COLUMNS if col not in frame.columns]
        if missing:
            raise ValidationError(f"{path} missing columns {missing}")
        model = float(frame["model_mape"].iloc[0])
        naive = float(frame["naive_mape"].iloc[0])
        cov = float(frame["coverage_90"].iloc[0])
        beat = "yes" if model < naive else "no"
        rows.append(f"| `{layer}` | {model:.4f} | {naive:.4f} | {cov:.3f} | {beat} |")
    return "\n".join(rows)


def _ols_section() -> str:
    path = load_settings().paths.reports / "recovery" / "ols_P-SB.json"
    if not path.is_file():
        raise ValidationError(f"missing {path}")
    result = OLSResult.model_validate_json(path.read_text(encoding="utf-8"))
    lines = [
        "OLS+HC1 on P-SB (adstock at prior-mode λ, no Hill). Signs ship as they are (VR-601).",
        "",
        "| Channel | OLS coef | HC1 se | Bayesian median ROAS | same sign |",
        "|---|---:|---:|---:|:---:|",
    ]
    for name in SPEC_CHANNEL_ORDER:
        key = f"adstock_{name}"
        if key not in result.coef:
            continue
        same = "yes" if result.sign_stable.get(name, False) else "no"
        roas = result.bayesian_roas_median.get(name, float("nan"))
        se = result.se_hc1[key]
        lines.append(f"| `{name}` | {result.coef[key]:.3f} | {se:.3f} | {roas:.3f} | {same} |")
    return "\n".join(lines)


def _crosscheck_section() -> str:
    path = load_settings().paths.reports / "recovery" / "crosscheck_P-SB.json"
    if not path.is_file():
        raise ValidationError(f"missing {path}")
    result = CrosscheckResult.model_validate_json(path.read_text(encoding="utf-8"))
    mark = "PASS" if result.gate_passed else "FAIL"
    return (
        f"**{mark}.** pymc-marketing {result.pymc_marketing_version} on P-SB: "
        f"Pearson {result.pearson:.4f}, Spearman {result.spearman:.4f} "
        f"(gate both ≥ {result.gate}). Their NUTS divergences: {result.n_divergences}. "
        "See `crosscheck_mapping.md` for matched and unmatched API pieces."
    )


def _assert_section_order(markdown: str) -> None:
    found = section_headings_in(markdown)
    if found != list(SECTION_HEADINGS):
        raise ValidationError(f"SPEC-05 §8 heading order mismatch: {found}")


def _closing_body(markdown: str) -> str:
    marker = SECTION_HEADINGS[-1]
    idx = markdown.find(marker)
    return markdown[idx + len(marker) :].strip()


def _apply_style() -> None:
    mpl.use("Agg")
    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.grid": True,
            "font.size": 10,
            "axes.titlesize": 11,
        }
    )


def _hill_fn() -> Any:
    a = pt.dvector("a")
    k = pt.dscalar("k")
    s = pt.dscalar("s")
    beta = pt.dscalar("beta")
    return pytensor.function([a, k, s, beta], beta * hill_saturation(a, k, s))


if __name__ == "__main__":
    sys.exit(main())
