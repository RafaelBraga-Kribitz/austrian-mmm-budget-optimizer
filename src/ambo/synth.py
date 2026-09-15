"""Layer P data-generating process for a disclosed five-channel advertiser.

Implements: SIM-001, SIM-003, SIM-060, SIM-071, SIM-074. Channel set: ADR-012.

This module owns its own geometric adstock (forward recursion) and Hill formula.
It must not import ``ambo.transforms`` or ``ambo.model`` — recovery is evidence
only if the simulator and the model do not share transform code (AGENTS T-3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from ambo.austrian_calendar import holiday_flag
from ambo.config import (
    AOV_ADVENT_BONUS,
    AOV_BASE,
    B0,
    CHANNEL_IDS,
    CHANNEL_LABELS,
    DATA_DIR,
    GROWTH,
    N_WEEKS,
    NOISE_SHARE,
    PROMO_MULTIPLIER,
    RESPONSE_GRID_MAX_MULT,
    RESPONSE_GRID_POINTS,
    SEED,
    START_ISO_WEEK,
    START_ISO_YEAR,
)

# Promo ISO weeks, repeated every year in the window (SPEC-01 §2.1 analogue).
PROMO_ISO_WEEKS: frozenset[int] = frozenset({8, 14, 18, 22, 36, 47, 48, 49, 50, 51})


@dataclass(frozen=True)
class ChannelSpec:
    """Disclosed media parameters plus the spend-pattern knobs."""

    channel_id: str
    decay: float
    k: float
    slope: float
    beta: float
    mean: float
    sd: float
    floor: float
    pulse_every: int | None = None
    pulse_multiplier: float | None = None
    burst_length: int | None = None
    burst_iso_weeks: tuple[int, ...] | None = None
    phi: float | None = None
    theta: float | None = None
    cpm: float | None = None


# Mapped from SPEC-01 §4/§3 onto STATUS D-05 names (ADR-012).
CHANNEL_SPECS: tuple[ChannelSpec, ...] = (
    ChannelSpec(
        "tv",
        decay=0.50,
        k=2_000,
        slope=1.1,
        beta=6_000,
        mean=8_000,
        sd=600,
        floor=0,
        burst_length=2,
        burst_iso_weeks=(10, 16, 22, 36, 47, 50),
    ),
    ChannelSpec(
        "radio",
        decay=0.55,
        k=3_500,
        slope=1.2,
        beta=5_000,
        mean=3_500,
        sd=300,
        floor=0,
        burst_length=3,
        burst_iso_weeks=(12, 20, 47),
    ),
    ChannelSpec(
        "print",
        decay=0.60,
        k=4_000,
        slope=1.3,
        beta=8_000,
        mean=5_000,
        sd=500,
        floor=0,
        burst_length=2,
        burst_iso_weeks=(11, 18, 35, 47, 49),
    ),
    ChannelSpec(
        "paid_search",
        decay=0.20,
        k=3_000,
        slope=1.0,
        beta=15_000,
        mean=2_500,
        sd=200,
        floor=400,
        phi=1.3,
        theta=0.01,
        cpm=2.0,
    ),
    ChannelSpec(
        "paid_social",
        decay=0.35,
        k=2_500,
        slope=0.9,
        beta=12_000,
        mean=2_000,
        sd=300,
        floor=0,
        pulse_every=6,
        pulse_multiplier=1.8,
        phi=1.5,
        theta=0.01,
        cpm=8.0,
    ),
)


def round_half_up(values: np.ndarray) -> np.ndarray:
    """Whole units, half away from zero. Not banker's rounding."""
    return np.floor(np.asarray(values, dtype=float) + 0.5).astype(np.int64)


def adstock_recursive(x: np.ndarray, decay: float) -> np.ndarray:
    """Forward geometric adstock: ``a[t] = x[t] + decay * a[t-1]``, ``a[0] = x[0]``."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError("adstock_recursive expects a 1-d series")
    if not (0.0 <= decay < 1.0):
        raise ValueError(f"decay must satisfy 0 <= decay < 1, got {decay}")
    out = np.empty_like(x, dtype=float)
    carry = 0.0
    for t, value in enumerate(x):
        carry = value + decay * carry
        out[t] = carry
    return out


def hill(adstocked: np.ndarray, k: float, slope: float) -> np.ndarray:
    """Hill saturation: ``a^s / (a^s + K^s)``. Equals 0.5 at ``a == K``."""
    if k <= 0.0 or slope <= 0.0:
        raise ValueError("k and slope must be > 0")
    a = np.maximum(np.asarray(adstocked, dtype=float), 0.0)
    num = a**slope
    return num / (num + k**slope)


def half_life(decay: float) -> float:
    """Weeks until a unit impulse has decayed to one half."""
    if not (0.0 < decay < 1.0):
        raise ValueError(f"half_life needs 0 < decay < 1, got {decay}")
    return float(np.log(0.5) / np.log(decay))


def week_spine(n_weeks: int = N_WEEKS) -> pd.DataFrame:
    """Gapless ISO-Monday spine starting at 2022-W01, with Austrian season flags."""
    monday = date.fromisocalendar(START_ISO_YEAR, START_ISO_WEEK, 1)
    rows: list[dict[str, object]] = []
    advent = _advent_keys(range(START_ISO_YEAR, START_ISO_YEAR + 5))
    for t in range(1, n_weeks + 1):
        iso_year, iso_week, _ = monday.isocalendar()
        key = (iso_year, iso_week)
        rows.append(
            {
                "t": t,
                "week_start": monday,
                "iso_year": iso_year,
                "iso_week": iso_week,
                "advent_flag": int(key in advent),
                "schulbeginn_flag": int(iso_week in (36, 37)),
                "jan_dip_flag": int(iso_week in (2, 3, 4, 5)),
                "spring_flag": int(14 <= iso_week <= 22),
                "summer_lull_flag": int(29 <= iso_week <= 33),
                "promo_flag": int(iso_week in PROMO_ISO_WEEKS),
            }
        )
        monday += timedelta(days=7)
    weeks = pd.DataFrame(rows)
    weeks["holiday_flag"] = holiday_flag(weeks["week_start"]).astype(int)
    return weeks


def _advent_keys(years: range) -> set[tuple[int, int]]:
    keys: set[tuple[int, int]] = set()
    for year in years:
        xmas = date(year, 12, 24)
        iso_year, iso_week, _ = xmas.isocalendar()
        monday = date.fromisocalendar(iso_year, iso_week, 1)
        for offset in range(4):
            day = monday - timedelta(days=7 * offset)
            iy, iw, _ = day.isocalendar()
            keys.add((iy, iw))
    return keys


def season_index(weeks: pd.DataFrame) -> np.ndarray:
    """SPEC-01 §2.1 multiplicative season. jan_dip / summer_lull enter as negatives."""
    return (
        1.0
        + 0.55 * weeks["advent_flag"].to_numpy()
        + 0.25 * weeks["schulbeginn_flag"].to_numpy()
        + 0.15 * weeks["spring_flag"].to_numpy()
        - 0.20 * weeks["jan_dip_flag"].to_numpy()
        - 0.10 * weeks["summer_lull_flag"].to_numpy()
    ).astype(float)


def baseline_demand(weeks: pd.DataFrame) -> pd.DataFrame:
    t = weeks["t"].to_numpy(dtype=float)
    trend = (1.0 + GROWTH) ** t
    season = season_index(weeks)
    promo_mult = np.where(weeks["promo_flag"].to_numpy() == 1, PROMO_MULTIPLIER, 1.0)
    base = B0 * trend * season * promo_mult
    return pd.DataFrame({"trend": trend, "season": season, "promo_mult": promo_mult, "base": base})


def generate_spend(
    weeks: pd.DataFrame,
    rng: np.random.Generator,
    *,
    collinear: bool = False,
) -> pd.DataFrame:
    """One Normal draw per channel, in CHANNEL_IDS order, then mask / floor / round."""
    columns: dict[str, np.ndarray] = {}
    for spec in CHANNEL_SPECS:
        columns[spec.channel_id] = _draw_channel(spec, weeks, rng, collinear=collinear)
    return pd.DataFrame(columns, index=weeks["t"].to_numpy()).astype(np.int64)


def _draw_channel(
    spec: ChannelSpec,
    weeks: pd.DataFrame,
    rng: np.random.Generator,
    *,
    collinear: bool,
) -> np.ndarray:
    t = weeks["t"].to_numpy()
    mean = np.full(len(weeks), spec.mean, dtype=float)
    if collinear:
        mean = mean * (
            1.0 + 0.5 * weeks["advent_flag"].to_numpy() + 0.2 * weeks["spring_flag"].to_numpy()
        )
    if spec.pulse_every is not None and spec.pulse_multiplier is not None:
        pulse = (t % spec.pulse_every) == 0
        mean = np.where(pulse, mean * spec.pulse_multiplier, mean)
    draw = rng.normal(loc=mean, scale=spec.sd)
    covered = np.ones(len(weeks), dtype=bool)
    if spec.burst_length is not None and spec.burst_iso_weeks is not None:
        covered = _burst_mask(weeks, spec.burst_length, spec.burst_iso_weeks)
        draw = np.where(covered, draw, 0.0)
    clamped = np.where(covered, np.maximum(draw, spec.floor), draw)
    return round_half_up(clamped)


def _burst_mask(weeks: pd.DataFrame, length: int, starts: tuple[int, ...]) -> np.ndarray:
    iso_week = weeks["iso_week"].to_numpy()
    mask = np.zeros(len(weeks), dtype=bool)
    for start in starts:
        covered = list(range(start, start + length))
        mask |= np.isin(iso_week, covered)
    return mask


@dataclass
class SyntheticAdvertiser:
    """In-memory Layer P: weekly frame, long media, truth dict."""

    weeks: pd.DataFrame
    spend: pd.DataFrame
    outcome: pd.DataFrame
    media: pd.DataFrame
    contributions: pd.DataFrame
    truth: dict[str, object]
    seed: int


def generate(
    *,
    n_weeks: int = N_WEEKS,
    seed: int = SEED,
    collinear: bool = False,
    zero_channel: str | None = None,
) -> SyntheticAdvertiser:
    """Simulate the disclosed advertiser. Deterministic in ``seed`` (SIM-001)."""
    rng = np.random.default_rng(seed)
    weeks = week_spine(n_weeks)
    demand = baseline_demand(weeks)
    spend = generate_spend(weeks, rng, collinear=collinear)
    contrib, media_terms = _media_contributions(spend, zero_channel=zero_channel)
    base = demand["base"].to_numpy()
    sigma = NOISE_SHARE * float(base.mean())
    noise = rng.normal(0.0, sigma, size=n_weeks)
    revenue = np.maximum(base + media_terms.sum(axis=1) + noise, 0.0)
    advent = weeks["advent_flag"].to_numpy(dtype=float)
    aov = AOV_BASE + AOV_ADVENT_BONUS * advent
    orders = round_half_up(revenue / aov)
    outcome = pd.DataFrame(
        {
            "week_start": weeks["week_start"],
            "revenue_eur": revenue,
            "orders": orders,
            "promo_flag": weeks["promo_flag"],
            "holiday_flag": weeks["holiday_flag"],
            "advent_flag": weeks["advent_flag"],
            "jan_dip_flag": weeks["jan_dip_flag"],
            "base": base,
            "noise": noise,
        }
    )
    media = _platform_report(weeks, spend, contrib, base, aov)
    truth = _truth_payload(weeks, spend, contrib, outcome, sigma, collinear, zero_channel, seed)
    return SyntheticAdvertiser(
        weeks=weeks,
        spend=spend,
        outcome=outcome,
        media=media,
        contributions=contrib,
        truth=truth,
        seed=seed,
    )


def _media_contributions(
    spend: pd.DataFrame, *, zero_channel: str | None
) -> tuple[pd.DataFrame, np.ndarray]:
    terms = []
    columns: dict[str, np.ndarray] = {}
    for spec in CHANNEL_SPECS:
        beta = 0.0 if spec.channel_id == zero_channel else spec.beta
        adstocked = adstock_recursive(spend[spec.channel_id].to_numpy(dtype=float), spec.decay)
        contribution = beta * hill(adstocked, spec.k, spec.slope)
        columns[spec.channel_id] = contribution
        terms.append(contribution)
    stacked = np.column_stack(terms)
    return pd.DataFrame(columns, index=spend.index), stacked


def _platform_report(
    weeks: pd.DataFrame,
    spend: pd.DataFrame,
    contrib: pd.DataFrame,
    base: np.ndarray,
    aov: np.ndarray,
) -> pd.DataFrame:
    """Own-effect inflation plus demand-claiming leak (SIM-060). Offline → NA."""
    total = spend[list(CHANNEL_IDS)].sum(axis=1).to_numpy(dtype=float)
    safe = np.where(total > 0.0, total, 1.0)
    frames: list[pd.DataFrame] = []
    week_start = weeks["week_start"].to_numpy()
    for spec in CHANNEL_SPECS:
        x = spend[spec.channel_id].to_numpy(dtype=float)
        share = np.where(total > 0.0, x / safe, 0.0)
        if spec.phi is None:
            impressions = pd.array([pd.NA] * len(weeks), dtype="Int64")
            conversions = pd.array([pd.NA] * len(weeks), dtype="Int64")
            revenue = pd.array([pd.NA] * len(weeks), dtype="Float64")
        else:
            platform_rev = (
                contrib[spec.channel_id].to_numpy() * spec.phi + spec.theta * base * share
            )
            assert spec.cpm is not None
            impressions = pd.array(round_half_up(x / spec.cpm * 1000.0), dtype="Int64")
            conversions = pd.array(round_half_up(platform_rev / aov), dtype="Int64")
            revenue = pd.array(platform_rev, dtype="Float64")
        frames.append(
            pd.DataFrame(
                {
                    "week_start": week_start,
                    "channel": spec.channel_id,
                    "spend_eur": x.astype(np.int64),
                    "impressions": impressions,
                    "platform_conversions": conversions,
                    "platform_revenue_eur": revenue,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def _truth_payload(
    weeks: pd.DataFrame,
    spend: pd.DataFrame,
    contrib: pd.DataFrame,
    outcome: pd.DataFrame,
    sigma: float,
    collinear: bool,
    zero_channel: str | None,
    seed: int,
) -> dict[str, object]:
    revenue = outcome["revenue_eur"].to_numpy()
    channels: dict[str, object] = {}
    for spec in CHANNEL_SPECS:
        x = spend[spec.channel_id].to_numpy(dtype=float)
        m = contrib[spec.channel_id].to_numpy()
        denom = float(x.sum())
        roas = float(m.sum() / denom) if denom > 0 else 0.0
        grid_x, grid_y = _response_curve(spec, float(x.max()) if x.max() > 0 else spec.mean)
        plat = _platform_roas(outcome, spend, spec)
        channels[spec.channel_id] = {
            "label": CHANNEL_LABELS[spec.channel_id],
            "decay": spec.decay,
            "half_life": None if spec.decay <= 0 else half_life(spec.decay),
            "K": spec.k,
            "slope": spec.slope,
            "beta": 0.0 if spec.channel_id == zero_channel else spec.beta,
            "true_avg_roas": roas,
            "contribution_total": float(m.sum()),
            "contribution_share": float(m.sum() / revenue.sum()),
            "platform_phi": spec.phi,
            "platform_theta": spec.theta,
            "platform_roas": plat,
            "response_curve_spend": grid_x,
            "response_curve_contribution": grid_y,
        }
    media_total = float(contrib.to_numpy().sum())
    return {
        "seed": seed,
        "n_weeks": int(len(weeks)),
        "collinear": collinear,
        "zero_channel": zero_channel,
        "b0": B0,
        "growth": GROWTH,
        "sigma": sigma,
        "channels": channels,
        "media_share": media_total / float(revenue.sum()),
        "revenue_total": float(revenue.sum()),
        "media_total": media_total,
    }


def _response_curve(spec: ChannelSpec, max_weekly: float) -> tuple[list[float], list[float]]:
    """Closed-form DGP curve at steady-state adstock on the MD-082 grid."""
    xs = np.linspace(0.0, RESPONSE_GRID_MAX_MULT * max_weekly, RESPONSE_GRID_POINTS)
    ss = xs / (1.0 - spec.decay)
    ys = spec.beta * hill(ss, spec.k, spec.slope)
    return [float(v) for v in xs], [float(v) for v in ys]


def _platform_roas(outcome: pd.DataFrame, spend: pd.DataFrame, spec: ChannelSpec) -> float | None:
    if spec.phi is None:
        return None
    # Computed later from the media frame in write_artifacts; placeholder here.
    x = float(spend[spec.channel_id].sum())
    if x <= 0:
        return None
    return None


def modeling_frame(sim: SyntheticAdvertiser) -> pd.DataFrame:
    """Wide weekly frame the model builder consumes."""
    frame = pd.DataFrame(
        {
            "week_start": sim.weeks["week_start"],
            "t": sim.weeks["t"],
            "revenue": sim.outcome["revenue_eur"],
            "promo_flag": sim.weeks["promo_flag"],
            "holiday_flag": sim.weeks["holiday_flag"],
            "advent_flag": sim.weeks["advent_flag"],
            "jan_dip_flag": sim.weeks["jan_dip_flag"],
        }
    )
    for channel_id in CHANNEL_IDS:
        frame[f"spend_{channel_id}"] = sim.spend[channel_id].to_numpy()
    return frame


def write_artifacts(sim: SyntheticAdvertiser, directory: Path | None = None) -> Path:
    """Commit-sized CSVs + truth.json under ``data/synthetic/`` (SIM-004)."""
    out = Path(directory) if directory is not None else DATA_DIR
    out.mkdir(parents=True, exist_ok=True)
    media = sim.media.copy()
    media["week_start"] = pd.to_datetime(media["week_start"]).dt.strftime("%Y-%m-%d")
    _fill_platform_roas(sim)
    media.to_csv(out / "media_weekly.csv", index=False, lineterminator="\n")
    outcome = sim.outcome[
        ["week_start", "revenue_eur", "orders", "promo_flag", "holiday_flag"]
    ].copy()
    outcome["week_start"] = pd.to_datetime(outcome["week_start"]).dt.strftime("%Y-%m-%d")
    outcome.to_csv(out / "outcome_weekly.csv", index=False, lineterminator="\n")
    modeling_frame(sim).assign(
        week_start=lambda d: pd.to_datetime(d["week_start"]).dt.strftime("%Y-%m-%d")
    ).to_csv(out / "mmm_input_weekly.csv", index=False, lineterminator="\n")
    (out / "truth.json").write_text(
        json.dumps(sim.truth, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return out


def _fill_platform_roas(sim: SyntheticAdvertiser) -> None:
    channels = sim.truth["channels"]
    assert isinstance(channels, dict)
    for spec in CHANNEL_SPECS:
        if spec.phi is None:
            continue
        slice_ = sim.media.loc[sim.media["channel"] == spec.channel_id]
        spend = float(pd.to_numeric(slice_["spend_eur"], errors="coerce").sum())
        plat = pd.to_numeric(slice_["platform_revenue_eur"], errors="coerce").sum()
        if spend > 0 and pd.notna(plat):
            channels[spec.channel_id]["platform_roas"] = float(plat) / spend
