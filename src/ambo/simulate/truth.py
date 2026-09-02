"""`truth.json`'s schema, closed-form curve evaluator, and byte-stable emission
(SPEC-01 section 4, section 6, section 8; SIM-060, SIM-070, SIM-075; Guide section
1.5; BP-D-02, BP-D-16; T-107).

Implements: REQ-q1-truth-recovery

This is the single home of two things: the closed-form true-response-curve formula
(A-8 -- `response_curve_at`/`marginal_roas_at` are the only place `beta * Hill` at
steady-state adstock is evaluated anywhere in `src/ambo/`) and the `truth.json`
serialisation format (sorted keys, fixed float precision, LF endings, atomic
replace -- SIM-070). Both functions reuse `dgp.hill` so the truth curve and the
generated per-week contributions can never diverge; this is intra-package reuse
inside `simulate/`, not a violation of the SIM-003 firewall, which is about
`simulate` <-> `model`, never about `simulate`'s own internals. This module
imports nothing from `ambo.model`.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from ambo.common.errors import SimulationError
from ambo.simulate.config import SPEC_CHANNEL_ORDER, SeasonWeights, TrueParams
from ambo.simulate.dgp import SimulationResult, hill

# SPEC-01 section 8: the diagnostic response-curve sample is always 21 points.
_RESPONSE_CURVE_POINTS = 21


def response_curve_at(params: TrueParams, x_grid: np.ndarray) -> np.ndarray:
    """The true response curve (SPEC-01 section 2.2/section 8), evaluated at
    steady-state adstock for every spend level in the caller-supplied `x_grid`.

    For each `x` in `x_grid`, the steady-state adstock is `a = x / (1 - lam)` and
    the contribution is `beta * hill(a, K, s)` (reusing `dgp.hill`, never a second
    implementation of Hill saturation). Validates that `x_grid` is 1-D, all-finite
    and all non-negative, raising `SimulationError` -- naming the offending value
    -- otherwise.

    **Grid note (SPEC-01 section 8, resolves INGEST-CONFLICTS WARNING 4):** the
    grid is supplied by the caller -- this function is deliberately not hard-coded
    to any one horizon. This phase's `compute_truth` calls it once with the
    21-point *diagnostic* grid over 0...2x max weekly spend, kept in `truth.json`
    only and never used for comparison. Phase 3/8's `exports/response_curves.csv`
    will call this same function again with MD-082's 21-point 0...1.5x max
    *observed* weekly spend grid -- the true curve is closed-form, so it is
    evaluated exactly at whatever grid a caller supplies, with no interpolation
    error and no second home for the formula.

    `response_curve_at(params, np.array([0.0]))` is exactly `[0.0]` for every
    channel (`hill(0, K, s) == 0.0` exactly). The curve is identically `0.0` when
    `beta == 0.0` (S-C's `display_video`), since `0.0 * hill(...)` is exact.
    """
    if x_grid.ndim != 1:
        raise SimulationError(f"response_curve_at(): x_grid must be 1-D, got ndim={x_grid.ndim!r}")
    if not np.all(np.isfinite(x_grid)):
        raise SimulationError(
            "response_curve_at(): x_grid must be all-finite, found NaN or infinity"
        )
    if x_grid.size > 0 and np.any(x_grid < 0.0):
        raise SimulationError(
            f"response_curve_at(): x_grid must be all non-negative, found min={x_grid.min()!r}"
        )

    a = x_grid / (1.0 - params.lam)
    result: np.ndarray = params.beta * hill(a, params.K, params.s)
    return result


def marginal_roas_at(params: TrueParams, x_mean: float) -> float:
    """The analytic true marginal ROAS at mean weekly spend `x_mean` (Guide
    section 1.5, BP-D-16): with steady-state adstock `a = x_mean / (1 - lam)`,

    `dm/dx = beta * s * K**s * a**(s-1) / (a**s + K**s)**2 * (1 / (1 - lam))`.

    This is **truth-side**: it uses SPEC-01's raw geometric-recursion steady
    state (`a = x/(1-lam)`), never the model's fixed-length normalized-weight
    convolution steady state (MD-020, BP-D-16) -- the two are deliberately
    different parameterizations, and this function is never called with, nor
    produces, a model-side quantity.

    `x_mean` must be finite and non-negative, or `SimulationError` is raised.
    Returns exactly `0.0` when `beta == 0.0` (no need to evaluate the derivative
    of a curve that is identically zero). When `x_mean == 0.0` (so `a == 0.0`),
    returns exactly `0.0` for `s >= 1.0` (the derivative is well-defined and
    finite there); raises `SimulationError` for `s < 1.0`, where the derivative
    is unbounded at the origin -- this branch is defensive, since every SPEC-01
    section 4 channel's total spend over the window is strictly positive by
    construction (`compute_truth` raises before ever reaching a zero-spend mean).
    """
    if not math.isfinite(x_mean):
        raise SimulationError(f"marginal_roas_at(): x_mean must be finite, got {x_mean!r}")
    if x_mean < 0.0:
        raise SimulationError(f"marginal_roas_at(): x_mean must be >= 0, got {x_mean!r}")

    if params.beta == 0.0:
        return 0.0

    a = x_mean / (1.0 - params.lam)
    if a == 0.0:
        if params.s >= 1.0:
            return 0.0
        raise SimulationError(
            f"marginal_roas_at(): derivative is unbounded at a=0 for s={params.s!r} < 1.0 "
            f"(x_mean={x_mean!r})"
        )

    K, s, lam, beta = params.K, params.s, params.lam, params.beta
    numerator = beta * s * K**s * a ** (s - 1.0)
    denominator = (a**s + K**s) ** 2
    return float(numerator / denominator * (1.0 / (1.0 - lam)))


class ChannelTruth(BaseModel):
    """One channel's disclosed ground truth (SPEC-01 section 4, section 6,
    section 8). `lam`, `K`, `s`, `beta` are the section 4 parameters the model
    must recover; `platform_phi`/`platform_theta`/`platform_cpm`/`platform_roas`
    are the section 6 platform-reporting quantities, `None` for the two offline
    channels (`print_regional`, `radio`) -- never a fabricated zero. Frozen,
    `extra='forbid'`: an unknown key is a load-time failure, never silently
    ignored.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: str
    lam: float
    K: float
    s: float
    beta: float
    half_life_weeks: float
    total_spend_eur: float
    mean_weekly_spend_eur: float
    max_weekly_spend_eur: float
    total_contribution_eur: float
    contribution_share: float
    true_avg_roas: float
    true_marginal_roas_at_mean_spend: float
    response_curve_spend_eur: tuple[float, ...]
    response_curve_contribution_eur: tuple[float, ...]
    platform_phi: float | None
    platform_theta: float | None
    platform_cpm: float | None
    platform_roas: float | None


class TruthFile(BaseModel):
    """The full disclosed ground truth for one SPEC-01 scenario (SIM-075):
    scenario metadata, the section 2.1/section 2.3 scalars, window aggregates,
    and one `ChannelTruth` per channel in `SPEC_CHANNEL_ORDER`. Frozen,
    `extra='forbid'`, matching every model in `ambo.simulate.config`.

    `response_curve_grid_max_multiple` (always `2.0`) tells a reader which
    horizon the stored `response_curve_*` arrays cover, per SPEC-01 section 8's
    explicit horizon ordering: `1.3x optimizer bound < 1.5x reporting horizon <
    2.0x truth diagnostic`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    scenario_id: str
    weeks: int
    seed: int
    collinearity: bool
    start_iso_year: int
    start_iso_week: int
    end_iso_year: int
    end_iso_week: int
    zero_effect_channel: str | None
    b0: float
    growth: float
    noise_share: float
    aov_base: float
    aov_advent_bonus: float
    promo_multiplier: float
    season_weights: SeasonWeights
    total_revenue_eur: float
    total_media_contribution_eur: float
    media_share_of_revenue: float
    response_curve_grid_max_multiple: float
    channels: tuple[ChannelTruth, ...]


def compute_truth(result: SimulationResult, media: pd.DataFrame) -> TruthFile:
    """Assemble `result` (and `media`, the platform-completed frame from
    `platform_bias.platform_report`) into a `TruthFile` (SIM-075, T-107). Pure --
    no I/O.

    Per channel in `SPEC_CHANNEL_ORDER`: `total_spend_eur` is the window sum of
    `result.spend[channel]`; a channel whose total spend is `0.0` raises
    `SimulationError` naming the channel -- a `0/0` average ROAS must never reach
    a committed artifact. `total_contribution_eur` is the window sum of
    `result.components["m_" + channel]`; `contribution_share` and
    `media_share_of_revenue` both divide by the same `total_revenue_eur`
    (`result.components["revenue"]`'s window sum, post-clip), so the six
    `contribution_share` values sum to `media_share_of_revenue` exactly.
    `true_marginal_roas_at_mean_spend` and the 21-point
    `response_curve_spend_eur`/`response_curve_contribution_eur` arrays call
    `marginal_roas_at`/`response_curve_at` rather than recomputing the curve
    inline -- this is the one home for the formula (A-8). The diagnostic grid is
    `np.linspace(0.0, 2.0 * max_weekly_spend_eur, 21)`, matching SPEC-01 section
    8. `half_life_weeks` is `log(0.5) / log(lam)`, with the defensive `lam == 0.0`
    case yielding `0.0` (every SPEC-01 section 4 lambda is strictly positive, so
    this branch is never exercised by a real scenario). `platform_roas` is
    `Sigma(platform_revenue_eur) / total_spend_eur` for the four online channels
    (from `media`, the already-completed frame) and `None` for the two offline
    channels, whose `platform_phi`/`platform_theta`/`platform_cpm` are also
    `None`, carried straight through from `result.cfg`.

    `zero_effect_channel` is `"display_video"` when `result.cfg.id == "s_c"`,
    else `None`. `response_curve_grid_max_multiple` is always `2.0`.
    `schema_version` is `"1.0"`.
    """
    cfg = result.cfg
    spend = result.spend
    components = result.components

    total_revenue_eur = float(components["revenue"].sum())
    zero_effect_channel = "display_video" if cfg.id == "s_c" else None

    channel_truths: list[ChannelTruth] = []
    total_media_contribution_eur = 0.0
    for channel_id in SPEC_CHANNEL_ORDER:
        channel_cfg = cfg.channels[channel_id]
        params = channel_cfg.true_params

        total_spend_eur = float(spend[channel_id].sum())
        if total_spend_eur == 0.0:
            raise SimulationError(
                f"compute_truth(): channel {channel_id!r} has zero total spend over the "
                "window -- a 0/0 average ROAS must never reach a committed truth file"
            )
        mean_weekly_spend_eur = float(spend[channel_id].mean())
        max_weekly_spend_eur = float(spend[channel_id].max())

        total_contribution_eur = float(components[f"m_{channel_id}"].sum())
        contribution_share = total_contribution_eur / total_revenue_eur
        true_avg_roas = total_contribution_eur / total_spend_eur
        true_marginal_roas_at_mean_spend = marginal_roas_at(params, mean_weekly_spend_eur)

        grid = np.linspace(0.0, 2.0 * max_weekly_spend_eur, _RESPONSE_CURVE_POINTS)
        curve = response_curve_at(params, grid)

        half_life_weeks = 0.0 if params.lam == 0.0 else math.log(0.5) / math.log(params.lam)

        platform = channel_cfg.platform
        if platform.phi is None:
            platform_roas: float | None = None
        else:
            channel_media = media.loc[media["channel"] == channel_id]
            platform_revenue_total = float(channel_media["platform_revenue_eur"].sum())
            platform_roas = platform_revenue_total / total_spend_eur

        channel_truths.append(
            ChannelTruth(
                channel=channel_id,
                lam=params.lam,
                K=params.K,
                s=params.s,
                beta=params.beta,
                half_life_weeks=half_life_weeks,
                total_spend_eur=total_spend_eur,
                mean_weekly_spend_eur=mean_weekly_spend_eur,
                max_weekly_spend_eur=max_weekly_spend_eur,
                total_contribution_eur=total_contribution_eur,
                contribution_share=contribution_share,
                true_avg_roas=true_avg_roas,
                true_marginal_roas_at_mean_spend=true_marginal_roas_at_mean_spend,
                response_curve_spend_eur=tuple(float(v) for v in grid),
                response_curve_contribution_eur=tuple(float(v) for v in curve),
                platform_phi=platform.phi,
                platform_theta=platform.theta,
                platform_cpm=platform.cpm,
                platform_roas=platform_roas,
            )
        )
        total_media_contribution_eur += total_contribution_eur

    media_share_of_revenue = total_media_contribution_eur / total_revenue_eur

    return TruthFile(
        schema_version="1.0",
        scenario_id=cfg.id,
        weeks=cfg.weeks,
        seed=cfg.seed,
        collinearity=cfg.collinearity,
        start_iso_year=cfg.start_iso_year,
        start_iso_week=cfg.start_iso_week,
        end_iso_year=cfg.end_iso_year,
        end_iso_week=cfg.end_iso_week,
        zero_effect_channel=zero_effect_channel,
        b0=cfg.b0,
        growth=cfg.growth,
        noise_share=cfg.noise_share,
        aov_base=cfg.aov_base,
        aov_advent_bonus=cfg.aov_advent_bonus,
        promo_multiplier=cfg.promo_multiplier,
        season_weights=cfg.season_weights,
        total_revenue_eur=total_revenue_eur,
        total_media_contribution_eur=total_media_contribution_eur,
        media_share_of_revenue=media_share_of_revenue,
        response_curve_grid_max_multiple=2.0,
        channels=tuple(channel_truths),
    )


def _normalize_floats(value: Any) -> Any:
    """Recursively replace every `float` in `value` with its `%.10g`-formatted
    equivalent (SIM-070, Guide section 1.5). `json.dump`/`json.dumps` exposes no
    per-float format hook -- there is no keyword that reformats a `float`'s
    string representation, and `default=` is never invoked for a plain `float`
    (it only fires for objects the encoder does not natively know how to
    serialise). Pre-normalising the values before serialisation is therefore the
    only mechanism available, confirmed against Python 3.12's `json` module
    (closes 02-RESEARCH.md Assumption A3): a custom `JSONEncoder` subclass would
    hit the identical limitation, since overriding `default()` still never sees a
    native `float`.
    """
    if isinstance(value, float):
        return float(f"{value:.10g}")
    if isinstance(value, dict):
        return {key: _normalize_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_floats(item) for item in value]
    return value


def write_truth(t: TruthFile, path: Path) -> None:
    """Write `t` to `path` as byte-stable JSON (SIM-070): `sort_keys=True`
    (total ordering, independent of construction order), 2-space indent, every
    float pre-normalised through `_normalize_floats`'s fixed `%.10g` format, a
    single trailing newline, and LF line endings pinned in the writer itself
    (`newline="\\n"` on the open call) -- not left to `.gitattributes`, matching
    `scripts/generate_season_windows.py`'s stated reason: a CI diff-check may run
    before git's checkout filters apply.

    Atomic (EB-050): writes to a `<path>.tmp-<pid>` sibling, flushes, then
    `os.replace`s onto `path`. On any exception the temp file is removed before
    re-raising, so an interrupted run never leaves debris and never leaves the
    original file partially written.
    """
    payload = _normalize_floats(t.model_dump(mode="json"))
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
