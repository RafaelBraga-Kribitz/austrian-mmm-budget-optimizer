"""Per-channel weekly spend series for SPEC-01 section 3's disclosed spend patterns
(SIM-030, SIM-031; Guide section 1.3).

Implements: REQ-q1-truth-recovery, REQ-grain-and-windows

This module promotes `03_MODULES.md` section 2.2's two-argument
`generate_spend(cfg, rng)` signature to three arguments,
`generate_spend(cfg, rng, weeks)`: SPEC-01 section 3's seasonal planning
multipliers need the Advent and spring flags carried by `weeks`, AD-020 forbids
recomputing those window flags here, and the Functional-Core/Imperative-Shell
rule forbids this module doing any I/O -- so `dgp.week_index`'s output frame is
injected by the caller rather than read here. Recorded for `docs/BUILD_LOG.md`.

**Draw order (SIM-001, SIM-070, Guide section 1.3, 02-RESEARCH.md Pattern 2).**
`generate_spend` consumes its `rng` argument as exactly six `rng.normal` calls,
one per channel, in `SPEC_CHANNEL_ORDER` (taxonomy order), each call drawing one
full length-T vector -- including for a flighted channel's non-burst weeks, so
stream consumption stays independent of a scenario's burst-schedule length.
`assemble_scenario` (plan 02-06) draws the revenue noise vector from this same
generator immediately afterward, so this module's six calls are always the
*first* six draws of any scenario's generator. Adding a seventh channel later
shifts only the streams after it, never the six documented here. The global
NumPy RNG (`np.random.seed`/`np.random.normal` module-level entry points) is
never seeded or read anywhere in `src/ambo/simulate/` (anti-pattern A-5) --
every stochastic draw goes through an explicitly injected `Generator`.

Per channel, the four SPEC-01 section 3 steps happen in exactly this order
(Guide section 1.3; 02-RESEARCH.md Pitfall 6 -- a mis-ordering biases SIM-031's
statistics by a small, easy-to-miss margin rather than crashing):

1. seasonal planning multipliers (and, for `meta`, the six-week pulse
   multiplier) apply to the *mean* of the Normal, never to the draw;
2. the draw -- one `rng.normal` call, full length-T;
3. the flighting mask (flighted channels only) zeroes every week not covered by
   an authored burst span;
4. the floor clamp, applied only to weeks the flighting mask kept, so a
   masked-zero week is never lifted back up to a floor;
5. whole-euro rounding, via `round_half_up` (`ambo.simulate.dgp`, the single
   home of the convention, A-8).

This module contains no scenario-name branch (MD-002-style discipline): SIM-030's
spend-season collinearity switch enters only as whatever `advent_factor` and
`spring_factor` a scenario's YAML carries -- there is no `if cfg.id == ...`
anywhere in this file.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ambo.common.errors import SimulationError
from ambo.simulate.config import SPEC_CHANNEL_ORDER, ScenarioConfig, SpendPattern
from ambo.simulate.dgp import round_half_up


def generate_spend(
    cfg: ScenarioConfig, rng: np.random.Generator, weeks: pd.DataFrame
) -> pd.DataFrame:
    """Return `cfg`'s six per-channel weekly spend series (SPEC-01 section 3).

    Consumes `rng` as exactly six `rng.normal` calls, one per channel, in
    `SPEC_CHANNEL_ORDER` -- see the module docstring's **Draw order** section.
    Two calls with generators freshly seeded from the same `cfg.seed` return
    elementwise-equal frames (SIM-001).

    Returns a `pd.DataFrame` indexed by `weeks`'s `t` column (`1..T`), with
    columns exactly `SPEC_CHANNEL_ORDER` in that order, dtype `int64`, every
    value `>= 0` (`search_brand` additionally never below its declared floor).

    Raises `SimulationError` if `weeks` has a row count other than `cfg.weeks`,
    or if any channel's burst span in `cfg` falls outside the `(iso_year,
    iso_week)` set `weeks` carries -- `ScenarioConfig`'s own validator already
    rejects an out-of-window schedule at load time, so this is the
    defence-in-depth restatement `03_MODULES.md` section 2.2 asks for.
    """
    if len(weeks) != cfg.weeks:
        raise SimulationError(
            f"generate_spend(): expected {cfg.weeks} week(s) (cfg.weeks), got "
            f"{len(weeks)} row(s) in weeks"
        )

    _validate_bursts_inside_weeks(cfg, weeks)

    columns: dict[str, np.ndarray] = {}
    for channel_id in SPEC_CHANNEL_ORDER:
        pattern = cfg.channels[channel_id].spend
        columns[channel_id] = _draw_channel_spend(rng, pattern, weeks)

    frame = pd.DataFrame(columns, index=weeks["t"].to_numpy())
    return frame[list(SPEC_CHANNEL_ORDER)].astype(np.int64)


def _draw_channel_spend(
    rng: np.random.Generator, pattern: SpendPattern, weeks: pd.DataFrame
) -> np.ndarray:
    """The four-step draw for one channel, in Guide section 1.3's exact order."""
    t = weeks["t"].to_numpy()
    advent_flag = weeks["advent_flag"].to_numpy()
    spring_flag = weeks["spring_flag"].to_numpy()

    # 1. Mean vector: seasonal planning multipliers, then the meta pulse -- both
    #    applied to the *mean*, never to the draw (Guide section 1.3).
    mean_vector = pattern.mean * (
        1.0 + pattern.advent_factor * advent_flag + pattern.spring_factor * spring_flag
    )
    if pattern.pulse_every is not None:
        assert pattern.pulse_multiplier is not None  # paired field, enforced by SpendPattern
        pulse_mask = (t % pattern.pulse_every) == 0
        mean_vector = np.where(pulse_mask, mean_vector * pattern.pulse_multiplier, mean_vector)

    # 2. Draw: one full length-T vector, always -- even for a flighted channel,
    #    whose non-burst weeks step 3 below discards. This keeps stream
    #    consumption independent of a scenario's burst-schedule length.
    draw = rng.normal(loc=mean_vector, scale=pattern.sd)

    # 3. Flighting mask: zero every week not covered by an authored burst span.
    if pattern.burst_length is not None and pattern.burst_starts is not None:
        covered = _burst_coverage_mask(weeks, pattern.burst_length, pattern.burst_starts)
        draw = np.where(covered, draw, 0.0)
    else:
        covered = np.ones(len(weeks), dtype=bool)

    # 4. Floor clamp -- spend can never be negative -- applied only to weeks the
    #    flighting mask kept, so a masked-zero week stays exactly 0 rather than
    #    being lifted to the floor.
    floor = float(pattern.floor_eur) if pattern.floor_eur is not None else 0.0
    clamped = np.where(covered, np.maximum(draw, floor), draw)

    # 5. Whole-euro rounding -- the single project-wide convention (A-8).
    result: np.ndarray = round_half_up(clamped)
    return result


def _burst_coverage_mask(
    weeks: pd.DataFrame, burst_length: int, burst_starts: dict[int, tuple[int, ...]]
) -> np.ndarray:
    """The boolean mask of `weeks` rows covered by any authored burst span."""
    iso_year = weeks["iso_year"].to_numpy()
    iso_week = weeks["iso_week"].to_numpy()
    mask = np.zeros(len(weeks), dtype=bool)
    for year, starts in burst_starts.items():
        for start in starts:
            covered_weeks = list(range(start, start + burst_length))
            mask |= (iso_year == year) & np.isin(iso_week, covered_weeks)
    return mask


def _validate_bursts_inside_weeks(cfg: ScenarioConfig, weeks: pd.DataFrame) -> None:
    """Defense-in-depth restatement of `ScenarioConfig`'s own schedule-in-window
    validator (`03_MODULES.md` section 2.2): every burst span must fall inside
    the `(iso_year, iso_week)` set `weeks` actually carries. `ScenarioConfig`
    already rejects an out-of-window schedule at load time, so this should never
    fire in normal use -- it exists so a future caller that builds `weeks` some
    other way fails loudly here rather than silently zero-filling an
    out-of-range burst.
    """
    known_keys = set(zip(weeks["iso_year"], weeks["iso_week"], strict=True))
    for channel_id in SPEC_CHANNEL_ORDER:
        pattern = cfg.channels[channel_id].spend
        if pattern.burst_length is None or pattern.burst_starts is None:
            continue
        for year, starts in pattern.burst_starts.items():
            for start in starts:
                for week in range(start, start + pattern.burst_length):
                    if (year, week) not in known_keys:
                        raise SimulationError(
                            f"generate_spend(): channel {channel_id!r} burst starting "
                            f"({year}, {start}) (length {pattern.burst_length}) covers week "
                            f"({year}, {week}), which is outside the supplied weeks frame"
                        )
