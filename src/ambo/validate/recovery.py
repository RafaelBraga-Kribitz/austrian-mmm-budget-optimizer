"""Recovery metrics VR-301…306 vs disclosed `truth.json` (SPEC-05 §3).

Implements: VR-301, VR-302, VR-303, VR-304, VR-305, VR-306, VR-310

ROAS draws use model-side adstock/Hill and the MD-030 revenue inverse, never
simulator transforms. Truth curves at the MD-082 grid call `response_curve_at`
(the single closed-form home). Gate thresholds live in
`config/recovery_gates.yaml` (DATA, not code).
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
import pandas as pd
import pytensor
import pytensor.tensor as pt
import yaml
from pydantic import BaseModel, ConfigDict
from scipy.stats import spearmanr

from ambo.common.config import SPEC_CHANNEL_ORDER, load_settings, repo_root
from ambo.common.db import read_mmm_input
from ambo.common.errors import ValidationError
from ambo.model.posterior_io import PosteriorBundle, load_posterior
from ambo.model.transforms import (
    ScaleFactors,
    adstock_convolve,
    hill_saturation,
    to_model_scale,
)
from ambo.simulate.config import TrueParams
from ambo.simulate.truth import TruthFile, response_curve_at

# mypy: disable-error-code="no-untyped-call,attr-defined"

LAYER_TO_SCENARIO: dict[str, str] = {"P-SA": "s_a", "P-SB": "s_b", "P-SC": "s_c"}
GATES_RELATIVE = "config/recovery_gates.yaml"
_GRID_POINTS = 21
_GRID_MAX_MULTIPLE = 1.5
_HDI_PROB = 0.9
_SEARCH = ("search_brand", "search_generic")
_LONG = ("print_regional", "radio")


class ChannelRecovery(BaseModel):
    """Per-channel VR-301/303/305 quantities. Frozen."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: str
    true_avg_roas: float
    roas_median: float
    roas_hdi_low: float
    roas_hdi_high: float
    in_hdi: bool
    mae_pct: float | None
    half_life_median: float
    contribution_share_median: float


class RecoveryMetrics(BaseModel):
    """VR-301…306 statistics for one layer. Frozen; JSON side-file payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    layer: str
    n_draws: int
    channels: tuple[ChannelRecovery, ...]
    spearman: float | None
    vr303_median_mae_pct: float | None
    media_share_posterior_median: float
    media_share_truth: float
    media_share_delta: float
    half_life_rank_ok: bool | None
    vr304_p_roas_lt: float | None
    vr304_median_share: float | None


class GateCheck(BaseModel):
    """One SPEC-05 §3 cell evaluated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gate: str
    gated: bool
    passed: bool
    detail: str


class GateResults(BaseModel):
    """evaluate_gates output. `all_green` is only over gated checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    layer: str
    checks: tuple[GateCheck, ...]
    all_green: bool


def compute_recovery(
    layer: str,
    *,
    bundle: PosteriorBundle | None = None,
    frame: pd.DataFrame | None = None,
    truth: TruthFile | None = None,
    output_dir: Path | None = None,
    adstock_length: int | None = None,
) -> RecoveryMetrics:
    """Load truth + posterior and compute VR-301…306 statistics (D-05, D-25)."""
    _require_known_layer(layer)
    settings = load_settings()
    loaded_bundle = bundle if bundle is not None else load_posterior(layer)
    loaded_frame = frame if frame is not None else read_mmm_input(layer)
    loaded_truth = truth if truth is not None else _load_truth(layer)
    length = settings.adstock_length if adstock_length is None else adstock_length
    if length < 1:
        raise ValidationError(f"adstock_length must be >= 1, got {length!r}")
    metrics = _metrics_from_inputs(
        layer,
        bundle=loaded_bundle,
        frame=loaded_frame,
        truth=loaded_truth,
        length=length,
    )
    _write_json(metrics.model_dump(mode="json"), _side_path(layer, "metrics", output_dir))
    return metrics


def evaluate_gates(
    metrics: RecoveryMetrics,
    *,
    output_dir: Path | None = None,
    gates_path: Path | None = None,
) -> GateResults:
    """Score `metrics` against `config/recovery_gates.yaml` (D-04)."""
    spec = _layer_gates(metrics.layer, gates_path)
    checks = (
        _check_vr301(metrics, spec),
        _check_vr302(metrics, spec),
        _check_vr303(metrics, spec),
        _check_vr304(metrics, spec),
        _check_vr305(metrics, spec),
        _check_vr306(metrics, spec),
    )
    result = GateResults(
        layer=metrics.layer,
        checks=checks,
        all_green=all(item.passed for item in checks if item.gated),
    )
    _write_json(result.model_dump(mode="json"), _side_path(metrics.layer, "gates", output_dir))
    return result


def load_gate_table(path: Path | None = None) -> dict[str, Any]:
    """Parse the SPEC-05 §3 YAML. Raises ValidationError on a malformed file."""
    gates_path = path if path is not None else repo_root() / GATES_RELATIVE
    raw = yaml.safe_load(gates_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValidationError(f"{gates_path}: expected a non-empty mapping of layers")
    return raw


def _require_known_layer(layer: str) -> None:
    if layer not in LAYER_TO_SCENARIO:
        raise ValidationError(
            f"unknown layer {layer!r}; expected one of {sorted(LAYER_TO_SCENARIO)}"
        )


def _load_truth(layer: str) -> TruthFile:
    scenario = LAYER_TO_SCENARIO[layer]
    settings = load_settings()
    path = repo_root() / settings.paths.data_synthetic / scenario / "truth.json"
    if not path.is_file():
        raise ValidationError(f"truth file not found for {layer}")
    return TruthFile.model_validate_json(path.read_text(encoding="utf-8"))


def _metrics_from_inputs(
    layer: str,
    *,
    bundle: PosteriorBundle,
    frame: pd.DataFrame,
    truth: TruthFile,
    length: int,
) -> RecoveryMetrics:
    channels = _channels_present(bundle.scale_factors)
    truth_by_ch = {row.channel: row for row in truth.channels}
    recovered: list[ChannelRecovery] = []
    share_draw_sum = np.zeros(len(bundle.draws), dtype=np.float64)
    vr304_p: float | None = None
    for channel in channels:
        if channel not in truth_by_ch:
            raise ValidationError(f"{layer}: truth.json missing channel {channel!r}")
        item, totals, roas = _one_channel(channel, bundle, frame, truth_by_ch[channel], length)
        recovered.append(item)
        share_draw_sum += totals
        if channel == "display_video":
            vr304_p = float(np.mean(roas < 0.2))
    revenue_total = float(frame["revenue"].to_numpy(dtype=np.float64).sum())
    if revenue_total <= 0.0:
        raise ValidationError(f"{layer}: observed revenue sum must be > 0")
    share_draws = share_draw_sum / revenue_total
    share_median = float(np.median(share_draws))
    maes = [item.mae_pct for item in recovered if item.mae_pct is not None]
    median_mae = float(np.median(np.asarray(maes, dtype=np.float64))) if maes else None
    return RecoveryMetrics(
        layer=layer,
        n_draws=len(bundle.draws),
        channels=tuple(recovered),
        spearman=_spearman(recovered),
        vr303_median_mae_pct=median_mae,
        media_share_posterior_median=share_median,
        media_share_truth=float(truth.media_share_of_revenue),
        media_share_delta=share_median - float(truth.media_share_of_revenue),
        half_life_rank_ok=_half_life_rank_ok(recovered),
        vr304_p_roas_lt=vr304_p,
        vr304_median_share=_named_share(recovered, "display_video"),
    )


def _one_channel(
    channel: str,
    bundle: PosteriorBundle,
    frame: pd.DataFrame,
    truth_row: Any,
    length: int,
) -> tuple[ChannelRecovery, np.ndarray, np.ndarray]:
    x_eur = _spend_eur(frame, channel)
    spend_total = float(x_eur.sum())
    if spend_total <= 0.0:
        raise ValidationError(f"channel {channel!r} has zero total spend")
    x_scaled = to_model_scale(frame, bundle.scale_factors)[f"spend_{channel}"].to_numpy(
        dtype=np.float64
    )
    lam = _param(bundle.draws, "lam", channel)
    k = _param(bundle.draws, "k", channel)
    s = _param(bundle.draws, "s", channel)
    beta = _param(bundle.draws, "beta", channel)
    roas, totals = _roas_draws(x_scaled, lam, k, s, beta, bundle.scale_factors, spend_total, length)
    low, high = _hdi90(roas)
    true_roas = float(truth_row.true_avg_roas)
    params = TrueParams(lam=truth_row.lam, K=truth_row.K, s=truth_row.s, beta=truth_row.beta)
    spend_mean = float(bundle.scale_factors.spend_means[channel])
    revenue_mean = float(bundle.scale_factors.revenue_mean)
    revenue_total = float(frame["revenue"].to_numpy(dtype=np.float64).sum())
    mae = _curve_mae_pct(x_eur, spend_mean, revenue_mean, k, s, beta, params)
    return (
        ChannelRecovery(
            channel=channel,
            true_avg_roas=true_roas,
            roas_median=float(np.median(roas)),
            roas_hdi_low=low,
            roas_hdi_high=high,
            in_hdi=bool(low <= true_roas <= high),
            mae_pct=mae,
            half_life_median=_median_half_life(lam),
            contribution_share_median=float(np.median(totals / revenue_total)),
        ),
        totals,
        roas,
    )


def _roas_draws(
    x_scaled: np.ndarray,
    lam: np.ndarray,
    k: np.ndarray,
    s: np.ndarray,
    beta: np.ndarray,
    scale_factors: ScaleFactors,
    spend_total: float,
    length: int,
) -> tuple[np.ndarray, np.ndarray]:
    fn = _series_fn(length)
    n_draws = int(lam.shape[0])
    roas = np.empty(n_draws, dtype=np.float64)
    totals = np.empty(n_draws, dtype=np.float64)
    for i in range(n_draws):
        m_scaled = np.asarray(fn(x_scaled, lam[i], k[i], s[i], beta[i]), dtype=np.float64)
        total = float((m_scaled * scale_factors.revenue_mean).sum())
        totals[i] = total
        roas[i] = total / spend_total
    return roas, totals


def _curve_mae_pct(
    x_eur: np.ndarray,
    spend_mean: float,
    revenue_mean: float,
    k: np.ndarray,
    s: np.ndarray,
    beta: np.ndarray,
    params: TrueParams,
) -> float | None:
    max_obs = float(np.max(x_eur))
    grid = np.linspace(0.0, _GRID_MAX_MULTIPLE * max_obs, _GRID_POINTS)
    true_curve = np.asarray(response_curve_at(params, grid), dtype=np.float64)
    true_max = float(np.max(true_curve))
    if true_max <= 0.0:
        return None
    x_scaled = grid / spend_mean
    hill_fn = _hill_fn()
    curves = [
        np.asarray(hill_fn(x_scaled, k[i], s[i], beta[i]), dtype=np.float64)
        for i in range(beta.shape[0])
    ]
    post_mean = np.stack(curves).mean(axis=0) * revenue_mean
    return float(np.mean(np.abs(post_mean - true_curve)) / true_max * 100.0)


def _channels_present(scale_factors: ScaleFactors) -> list[str]:
    present = set(scale_factors.spend_means)
    return [name for name in SPEC_CHANNEL_ORDER if name in present]


def _spend_eur(frame: pd.DataFrame, channel: str) -> np.ndarray:
    column = f"spend_{channel}"
    if column not in frame.columns:
        raise ValidationError(f"frame missing column {column}")
    return np.asarray(frame.loc[:, column], dtype=np.float64)


def _param(draws: pd.DataFrame, name: str, channel: str) -> np.ndarray:
    column = f"{name}__{channel}"
    if column not in draws.columns:
        raise ValidationError(f"posterior missing column {column}")
    return np.asarray(draws.loc[:, column], dtype=np.float64)


def _hdi90(values: np.ndarray) -> tuple[float, float]:
    interval = np.asarray(az.hdi(values, hdi_prob=_HDI_PROB), dtype=np.float64)
    return float(interval[0]), float(interval[1])


def _spearman(rows: list[ChannelRecovery]) -> float | None:
    if len(rows) < 2:
        return None
    result = spearmanr([row.roas_median for row in rows], [row.true_avg_roas for row in rows])
    value = float(result.statistic)
    return None if not np.isfinite(value) else value


def _median_half_life(lam: np.ndarray) -> float:
    med = float(np.median(lam))
    if not (0.0 < med < 1.0):
        raise ValidationError(f"median λ out of (0, 1): {med!r}")
    return float(np.log(0.5) / np.log(med))


def _half_life_rank_ok(rows: list[ChannelRecovery]) -> bool | None:
    by_name = {row.channel: row.half_life_median for row in rows}
    if any(name not in by_name for name in (*_SEARCH, *_LONG)):
        return None
    long_vals = [by_name[name] for name in _LONG]
    search_vals = [by_name[name] for name in _SEARCH]
    return bool(min(long_vals) > max(search_vals))


def _named_share(rows: list[ChannelRecovery], channel: str) -> float | None:
    for row in rows:
        if row.channel == channel:
            return row.contribution_share_median
    return None


@functools.lru_cache(maxsize=4)
def _series_fn(length: int) -> Any:
    x = pt.dvector("x")
    lam = pt.dscalar("lam")
    k = pt.dscalar("k")
    s = pt.dscalar("s")
    beta = pt.dscalar("beta")
    contrib = beta * hill_saturation(adstock_convolve(x, lam, length), k, s)
    return pytensor.function([x, lam, k, s, beta], contrib)


@functools.lru_cache(maxsize=1)
def _hill_fn() -> Any:
    a = pt.dvector("a")
    k = pt.dscalar("k")
    s = pt.dscalar("s")
    beta = pt.dscalar("beta")
    return pytensor.function([a, k, s, beta], beta * hill_saturation(a, k, s))


def _layer_gates(layer: str, gates_path: Path | None) -> dict[str, Any]:
    table = load_gate_table(gates_path)
    spec = table.get(layer)
    if not isinstance(spec, dict):
        raise ValidationError(f"recovery_gates.yaml missing layer {layer!r}")
    return spec


def _check_vr301(metrics: RecoveryMetrics, spec: dict[str, Any]) -> GateCheck:
    needed = int(spec["vr_301_min_in_hdi"])
    n_in = sum(1 for row in metrics.channels if row.in_hdi)
    n_ch = len(metrics.channels)
    return GateCheck(
        gate="VR-301",
        gated=True,
        passed=n_in >= needed,
        detail=f"{n_in}/{n_ch} channels in 90% HDI (need ≥ {needed})",
    )


def _check_vr302(metrics: RecoveryMetrics, spec: dict[str, Any]) -> GateCheck:
    gated = bool(spec["vr_302_gated"])
    floor = float(spec["vr_302_min_spearman"])
    value = metrics.spearman
    passed = (not gated) or (value is not None and value >= floor)
    shown = "n/a" if value is None else f"{value:.3f}"
    return GateCheck(
        gate="VR-302",
        gated=gated,
        passed=passed,
        detail=f"Spearman {shown} (need ≥ {floor})" + ("" if gated else "; not gated"),
    )


def _check_vr303(metrics: RecoveryMetrics, spec: dict[str, Any]) -> GateCheck:
    gated = bool(spec["vr_303_gated"])
    per = float(spec["vr_303_max_mae_pct_per_channel"])
    med_max = float(spec["vr_303_max_mae_pct_median"])
    maes = [row.mae_pct for row in metrics.channels if row.mae_pct is not None]
    per_ok = all(value <= per for value in maes)
    med_ok = metrics.vr303_median_mae_pct is None or metrics.vr303_median_mae_pct <= med_max
    passed = (not gated) or (per_ok and med_ok)
    med = metrics.vr303_median_mae_pct
    med_shown = "n/a" if med is None else f"{med:.2f}"
    return GateCheck(
        gate="VR-303",
        gated=gated,
        passed=passed,
        detail=f"MAE% median {med_shown} (per≤{per}, median≤{med_max})"
        + ("" if gated else "; not gated"),
    )


def _check_vr304(metrics: RecoveryMetrics, spec: dict[str, Any]) -> GateCheck:
    gated = bool(spec["vr_304_gated"])
    if not gated:
        return GateCheck(gate="VR-304", gated=False, passed=True, detail="not gated")
    p_floor = float(spec["vr_304_min_prob"])
    share_cap = float(spec["vr_304_max_median_share"])
    prob = metrics.vr304_p_roas_lt
    share = metrics.vr304_median_share
    passed = prob is not None and share is not None and prob >= p_floor and share <= share_cap
    return GateCheck(
        gate="VR-304",
        gated=True,
        passed=passed,
        detail=f"P(ROAS<0.2)={prob} share={share} (need P≥{p_floor} and share≤{share_cap})",
    )


def _check_vr305(metrics: RecoveryMetrics, spec: dict[str, Any]) -> GateCheck:
    required = bool(spec["vr_305_required"])
    ok = metrics.half_life_rank_ok is True
    return GateCheck(
        gate="VR-305",
        gated=required,
        passed=(not required) or ok,
        detail="print/radio half-lives rank above search" if ok else "half-life ranking failed",
    )


def _check_vr306(metrics: RecoveryMetrics, spec: dict[str, Any]) -> GateCheck:
    cap = float(spec["vr_306_max_share_delta"])
    delta = abs(metrics.media_share_delta)
    return GateCheck(
        gate="VR-306",
        gated=True,
        passed=delta <= cap,
        detail=f"|media share Δ|={delta:.4f} (need ≤ {cap})",
    )


def _side_path(layer: str, kind: str, output_dir: Path | None) -> Path:
    directory = output_dir if output_dir is not None else repo_root() / "reports" / "recovery"
    return directory / f"{kind}_{layer}.json"


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    tmp_path = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
