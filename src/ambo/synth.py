"""Layer P generator: a synthetic advertiser whose truth is written down.

Weekly data for a fixed number of weeks and five channels. Spend has yearly
seasonality and flighted campaigns rather than white noise; revenue is a baseline
(intercept, linear trend, two yearly Fourier pairs, a public-holiday control) plus
the media effects (geometric adstock, then Hill saturation, times an effect size)
plus Gaussian noise. A platform-reported number per online channel is generated
alongside: a naive attribution that inflates the channel's own effect and credits it
with a slice of baseline demand in proportion to its spend share, which is how
last-touch dashboards end up over-crediting search.

The adstock and Hill functions here are written independently of ``ambo.transforms``
(recursion instead of convolution) so that parameter recovery by the model is
evidence, not a tautology.

Every parameter comes from the ``synthetic`` block of the YAML config and is written
to ``truth.json`` next to the data. The generator is seeded and deterministic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from ambo.austrian_calendar import holiday_flag

WEEKS_PER_YEAR = 52.18


@dataclass
class SyntheticResult:
    data: pd.DataFrame
    truth: dict
    contributions: pd.DataFrame  # true weekly contribution per channel, euros


# ---------------------------------------------------------------------------
# Independent transforms (recursion form)
# ---------------------------------------------------------------------------


def adstock_recursive(spend: np.ndarray, decay: float) -> np.ndarray:
    """``a[t] = spend[t] + decay * a[t-1]`` with ``a[-1] = 0``."""
    out = np.zeros(len(spend), dtype=float)
    carry = 0.0
    for t, value in enumerate(spend):
        carry = float(value) + decay * carry
        out[t] = carry
    return out


def hill_curve(a: np.ndarray, half_saturation: float, slope: float) -> np.ndarray:
    """``a^s / (a^s + K^s)``; one half at ``a == K``."""
    a = np.maximum(np.asarray(a, dtype=float), 0.0)
    return a**slope / (a**slope + half_saturation**slope)


# ---------------------------------------------------------------------------
# Calendar and baseline
# ---------------------------------------------------------------------------


def week_starts(start: str, weeks: int) -> list[date]:
    first = pd.Timestamp(start).date()
    if first.weekday() != 0:
        raise ValueError("start must be a Monday")
    return [first + timedelta(days=7 * i) for i in range(weeks)]


def fourier_terms(weeks: int, order: int, period: float = WEEKS_PER_YEAR) -> np.ndarray:
    """Columns sin1, cos1, sin2, cos2, ... for t = 1..weeks."""
    t = np.arange(1, weeks + 1, dtype=float)
    cols = []
    for j in range(1, order + 1):
        angle = 2.0 * np.pi * j * t / period
        cols.append(np.sin(angle))
        cols.append(np.cos(angle))
    return np.column_stack(cols)


def _seasonal_index(weeks: int) -> np.ndarray:
    """Demand index in [0, 1] peaking in the Advent weeks (first Fourier pair, phase shifted)."""
    t = np.arange(1, weeks + 1, dtype=float)
    # peak near ISO week 49 when the window starts in the first week of January
    return 0.5 * (1.0 + np.cos(2.0 * np.pi * (t - 49.0) / WEEKS_PER_YEAR))


# ---------------------------------------------------------------------------
# Spend patterns
# ---------------------------------------------------------------------------


def _burst_schedule(
    weeks: int, burst_weeks: int, bursts_per_year: int, season: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """0/1 mask of flighted campaign weeks: bursts favour high-season weeks."""
    mask = np.zeros(weeks, dtype=float)
    n_bursts = int(round(bursts_per_year * weeks / WEEKS_PER_YEAR))
    candidates = np.arange(0, weeks - burst_weeks + 1)
    # sample burst starts without overlap, weighted toward the demand season
    weights = 0.3 + season[candidates]
    chosen: list[int] = []
    available = np.ones(len(candidates), dtype=bool)
    for _ in range(n_bursts):
        if not available.any():
            break
        p = weights * available
        p = p / p.sum()
        start = int(rng.choice(candidates, p=p))
        chosen.append(start)
        lo, hi = start - burst_weeks, start + burst_weeks
        available[(candidates > lo) & (candidates < hi)] = False
    for start in chosen:
        mask[start : start + burst_weeks] = 1.0
    return mask


def generate_spend(channel_cfg: dict, weeks: int, rng: np.random.Generator) -> np.ndarray:
    """Weekly spend for one channel in whole euros."""
    spec = channel_cfg["spend"]
    season = _seasonal_index(weeks)
    level = float(spec["level"]) * (1.0 + float(spec.get("seasonal", 0.0)) * season)
    draw = rng.normal(level, float(spec["sd"]), size=weeks)
    if spec["pattern"] == "flighted":
        mask = _burst_schedule(
            weeks, int(spec["burst_weeks"]), int(spec["bursts_per_year"]), season, rng
        )
        draw = draw * mask
    elif spec["pattern"] == "always_on":
        every = int(spec.get("pulse_every", 0) or 0)
        if every > 0:
            pulse = np.ones(weeks)
            pulse[every - 1 :: every] = float(spec.get("pulse_factor", 1.0))
            draw = draw * pulse
    else:
        raise ValueError(f"unknown spend pattern {spec['pattern']!r}")
    draw = np.where(draw > 0, np.maximum(draw, 0.25 * float(spec["level"])), 0.0)
    return np.round(draw)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def generate(config: dict) -> SyntheticResult:
    """Build the synthetic weekly dataset and its truth from the ``synthetic`` block."""
    synth = config["synthetic"]
    channels = list(config["channels"])
    weeks = int(synth["weeks"])
    rng = np.random.default_rng(int(synth["seed"]))
    starts = week_starts(synth["start"], weeks)
    holiday = holiday_flag(starts)

    base_cfg = synth["baseline"]
    t_over_t = np.arange(1, weeks + 1, dtype=float) / weeks
    fourier = fourier_terms(weeks, len(base_cfg["seasonality"]) // 2)
    seasonality = fourier @ np.asarray(base_cfg["seasonality"], dtype=float)
    baseline = (
        float(base_cfg["intercept"])
        + float(base_cfg["trend"]) * t_over_t
        + seasonality
        + float(base_cfg["control"]) * holiday
    )

    spend: dict[str, np.ndarray] = {}
    contrib: dict[str, np.ndarray] = {}
    for name in channels:
        ch = synth["channels"][name]
        spend[name] = generate_spend(ch, weeks, rng)
        a = adstock_recursive(spend[name], float(ch["decay"]))
        contrib[name] = float(ch["effect"]) * hill_curve(
            a, float(ch["half_saturation"]), float(ch["slope"])
        )

    noise = rng.normal(0.0, float(base_cfg["noise_sigma"]), size=weeks)
    media_total = sum(contrib.values())
    revenue = baseline + media_total + noise
    if (revenue <= 0).any():
        raise ValueError("synthetic revenue went non-positive; check the truth block")

    total_spend = sum(spend.values())
    platform: dict[str, np.ndarray] = {}
    for name in channels:
        pf = synth["channels"][name].get("platform")
        if pf is None:
            continue
        safe_total = np.where(total_spend > 0, total_spend, 1.0)
        share = np.where(total_spend > 0, spend[name] / safe_total, 0.0)
        platform[name] = (
            float(pf["own_inflation"]) * contrib[name]
            + float(pf["demand_claim"]) * baseline * share
        )

    data = pd.DataFrame(
        {"week": np.arange(1, weeks + 1), "week_start": [d.isoformat() for d in starts]}
    )
    for name in channels:
        data[f"spend_{name}"] = spend[name]
    data["revenue"] = np.round(revenue, 2)
    data["holiday"] = holiday
    for name in channels:
        if name in platform:
            data[f"platform_{name}"] = np.round(platform[name], 2)

    contributions = pd.DataFrame({"week": data["week"]})
    for name in channels:
        contributions[name] = contrib[name]
    contributions["baseline"] = baseline
    contributions["noise"] = noise

    truth = _truth_record(config, spend, contrib, platform, revenue, baseline)
    return SyntheticResult(data=data, truth=truth, contributions=contributions)


def _truth_record(
    config: dict,
    spend: dict[str, np.ndarray],
    contrib: dict[str, np.ndarray],
    platform: dict[str, np.ndarray],
    revenue: np.ndarray,
    baseline: np.ndarray,
) -> dict:
    synth = config["synthetic"]
    channels = list(config["channels"])
    total_revenue = float(revenue.sum())
    total_media = float(sum(c.sum() for c in contrib.values()))
    total_platform = float(sum(p.sum() for p in platform.values()))
    per_channel = {}
    for name in channels:
        ch = synth["channels"][name]
        spend_total = float(spend[name].sum())
        contrib_total = float(contrib[name].sum())
        platform_total = float(platform[name].sum()) if name in platform else 0.0
        per_channel[name] = {
            "decay": float(ch["decay"]),
            "half_saturation": float(ch["half_saturation"]),
            "slope": float(ch["slope"]),
            "effect": float(ch["effect"]),
            "platform": ch.get("platform"),
            "spend_total": spend_total,
            "spend_mean_positive_weeks": float(spend[name][spend[name] > 0].mean()),
            "contribution_total": contrib_total,
            "contribution_share_of_revenue": contrib_total / total_revenue,
            "contribution_share_of_media": contrib_total / total_media,
            "roas": contrib_total / spend_total if spend_total > 0 else None,
            "platform_reported_total": platform_total,
            "platform_share_of_reported": (
                platform_total / total_platform if total_platform > 0 else 0.0
            ),
        }
    return {
        "layer": config["layer"],
        "seed": int(synth["seed"]),
        "weeks": int(synth["weeks"]),
        "start": synth["start"],
        "channels": channels,
        "control": config["control"],
        "baseline": {
            "intercept": float(synth["baseline"]["intercept"]),
            "trend": float(synth["baseline"]["trend"]),
            "seasonality": [float(v) for v in synth["baseline"]["seasonality"]],
            "control": float(synth["baseline"]["control"]),
            "noise_sigma": float(synth["baseline"]["noise_sigma"]),
            "fourier_period": WEEKS_PER_YEAR,
        },
        "channel_truth": per_channel,
        "totals": {
            "revenue": total_revenue,
            "revenue_mean": float(revenue.mean()),
            "baseline": float(baseline.sum()),
            "media": total_media,
            "media_share_of_revenue": total_media / total_revenue,
            "platform_reported": total_platform,
        },
    }


def write(result: SyntheticResult, data_dir: Path) -> None:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    result.data.to_csv(data_dir / "weekly.csv", index=False, lineterminator="\n")
    result.contributions.round(4).to_csv(
        data_dir / "true_contributions.csv", index=False, lineterminator="\n"
    )
    with open(data_dir / "truth.json", "w", encoding="utf-8") as fh:
        json.dump(result.truth, fh, indent=2, sort_keys=True)
        fh.write("\n")


def load(data_dir: Path) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    data_dir = Path(data_dir)
    data = pd.read_csv(data_dir / "weekly.csv")
    with open(data_dir / "truth.json", encoding="utf-8") as fh:
        truth = json.load(fh)
    contributions = pd.read_csv(data_dir / "true_contributions.csv")
    return data, truth, contributions
