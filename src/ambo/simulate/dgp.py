"""The disclosed data-generating process's mathematical core (SPEC-01 section 2.1,
2.2, 2.3; SIM-003; SIM-071...074; AD-020).

Implements: REQ-q1-truth-recovery, REQ-grain-and-windows

This module reads the committed calendar seed `dbt/seeds/season_windows.csv` and
never recomputes any window rule -- the five window rules (advent, schulbeginn,
jan_dip, spring, summer_lull) live in `scripts/generate_season_windows.py` and are
frozen there (AD-020, the single sanctioned shared-CONFIG exception to the
simulator-versus-model firewall).

Nothing in this module is imported from or shared with `ambo.model`: the simulator
implements its own adstock and Hill saturation, independently derived and
independently tested, so the Phase 5 recovery result -- "the model recovered the
true parameters" -- is evidence rather than a tautology (SIM-003, 09_ANTI_PATTERNS
A-1). `tests/unit/test_import_independence.py` enforces this mechanically.

This is the first half of `dgp.py` (T-103, T-104): the calendar spine, the
seasonal index, baseline demand, the rounding convention, and (added by Task 2 in
this same plan) the simulator's own adstock/Hill. `assemble_scenario`,
`SimulationResult` and the SIM-071/072 audits are plan 02-06's second half of this
same file.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from ambo.common.config import repo_root
from ambo.common.errors import SimulationError
from ambo.simulate.config import ScenarioConfig, SeasonWeights

# The committed calendar seed (AD-020): the sole calendar authority for this
# module. Never recomputed here -- see the module docstring.
SEED_PATH = repo_root() / "dbt" / "seeds" / "season_windows.csv"

# The five window-flag columns, copied through `week_index()` untouched.
_FLAG_COLUMNS: tuple[str, ...] = (
    "advent_flag",
    "schulbeginn_flag",
    "jan_dip_flag",
    "spring_flag",
    "summer_lull_flag",
)


def round_half_up(values: np.ndarray) -> np.ndarray:
    """Round `values` to the nearest whole unit, half away from zero.

    This is the single project-wide rounding convention for whole-euro and
    whole-order quantities in this phase (A-8): every other `simulate/` module
    that needs whole-unit rounding (`spend_patterns.py`'s spend floor/round step,
    the orders computation) imports `round_half_up` from here rather than
    reimplementing it. Deliberately not `np.rint`, whose half-to-even
    ("banker's rounding") behaviour would round `0.5 -> 0` and `2.5 -> 2`; this
    function rounds `0.5 -> 1` and `2.5 -> 3`, matching BP-D-09's pro-rating
    convention. Assumes non-negative input, as every caller in this phase's
    domain guarantees (spend and revenue are never negative here).
    """
    return np.floor(values + 0.5).astype(np.int64)


def week_index(cfg: ScenarioConfig) -> pd.DataFrame:
    """Return the gapless, ISO-Monday-aligned weekly spine for `cfg`'s window.

    Reads `SEED_PATH` and filters to rows whose `(iso_year, iso_week)` tuple lies
    inclusively between `cfg`'s start and end endpoints, under plain tuple
    comparison. Raises `SimulationError` -- naming the offending key -- if any of
    the following does not hold: the filtered row count equals `cfg.weeks`; no
    duplicate `(iso_year, iso_week)` key; `week_start` strictly increasing; every
    consecutive `week_start` difference is exactly 7 days; every `week_start` is a
    Monday. A missing or duplicated calendar row is never silently defaulted to an
    unflagged week (AD-020).

    Returns a frame with `iso_year`, `iso_week`, `week_start` (datetime64), a new
    1-indexed `t` column (`1..T`, SPEC-01 section 2's weekly index), and the five
    window-flag columns as `int64` -- copied through untouched, since this
    function classifies nothing. Index is reset.
    """
    seed = pd.read_csv(SEED_PATH, parse_dates=["week_start"])

    window_start = (cfg.start_iso_year, cfg.start_iso_week)
    window_end = (cfg.end_iso_year, cfg.end_iso_week)
    keys = list(zip(seed["iso_year"], seed["iso_week"], strict=True))
    in_window = [window_start <= key <= window_end for key in keys]
    weeks = seed.loc[in_window].reset_index(drop=True)

    if weeks.empty:
        raise SimulationError(
            f"week_index(): no season_windows.csv rows found for window "
            f"[{window_start}..{window_end}]"
        )

    duplicate_mask = weeks.duplicated(subset=["iso_year", "iso_week"], keep=False)
    if duplicate_mask.any():
        duplicate_keys = sorted(
            set(
                zip(
                    weeks.loc[duplicate_mask, "iso_year"],
                    weeks.loc[duplicate_mask, "iso_week"],
                    strict=True,
                )
            )
        )
        raise SimulationError(
            f"week_index(): duplicate (iso_year, iso_week) key(s) in {SEED_PATH}: {duplicate_keys}"
        )

    weeks = weeks.sort_values(["iso_year", "iso_week"]).reset_index(drop=True)

    if len(weeks) != cfg.weeks:
        found_keys = sorted(set(zip(weeks["iso_year"], weeks["iso_week"], strict=True)))
        expected_keys = _expected_keys(cfg.start_iso_year, cfg.start_iso_week, cfg.weeks)
        missing = sorted(set(expected_keys) - set(found_keys))
        raise SimulationError(
            f"week_index(): expected {cfg.weeks} week(s) for window "
            f"[{window_start}..{window_end}], found {len(weeks)} in {SEED_PATH}"
            + (f"; missing key(s): {missing}" if missing else "")
        )

    if not weeks["week_start"].is_monotonic_increasing:
        raise SimulationError(
            f"week_index(): week_start is not strictly increasing for window "
            f"[{window_start}..{window_end}]"
        )

    diffs = weeks["week_start"].diff().dropna()
    bad_gap_mask = diffs != pd.Timedelta(days=7)
    if bad_gap_mask.any():
        bad_index = diffs.index[bad_gap_mask][0]
        prev_key = (
            weeks.loc[bad_index - 1, "iso_year"],
            weeks.loc[bad_index - 1, "iso_week"],
        )
        bad_key = (weeks.loc[bad_index, "iso_year"], weeks.loc[bad_index, "iso_week"])
        raise SimulationError(
            f"week_index(): non-7-day gap between {prev_key} and {bad_key} in {SEED_PATH}"
        )

    non_monday_mask = weeks["week_start"].dt.dayofweek != 0
    if non_monday_mask.any():
        bad_index = non_monday_mask.idxmax()
        bad_key = (weeks.loc[bad_index, "iso_year"], weeks.loc[bad_index, "iso_week"])
        raise SimulationError(
            f"week_index(): week_start for key {bad_key} in {SEED_PATH} is not a Monday"
        )

    weeks["t"] = np.arange(1, len(weeks) + 1, dtype=np.int64)
    for column in _FLAG_COLUMNS:
        weeks[column] = weeks[column].astype(np.int64)

    return weeks[["iso_year", "iso_week", "week_start", "t", *_FLAG_COLUMNS]].reset_index(drop=True)


def _expected_keys(start_iso_year: int, start_iso_week: int, count: int) -> list[tuple[int, int]]:
    """The `count` consecutive `(iso_year, iso_week)` keys starting at
    `(start_iso_year, start_iso_week)`, one per week, used only to name a missing
    key in a `SimulationError` message when the seed itself is short a row.

    Computed via `date.fromisocalendar`/`isocalendar()` -- plain ISO-calendar
    arithmetic to reconstruct the gapless spine `cfg` declares, independent of
    whatever the (possibly short) seed file actually contains. This is not a
    window-rule reimplementation (AD-020 forbids recomputing advent/schulbeginn/
    jan_dip/spring/summer_lull, not the plain weekly count); it is the only way
    to name a key that is, by definition, absent from the seed being diagnosed.
    """
    monday = date.fromisocalendar(start_iso_year, start_iso_week, 1)
    keys: list[tuple[int, int]] = []
    for _ in range(count):
        iso_year, iso_week, _ = monday.isocalendar()
        keys.append((iso_year, iso_week))
        monday += timedelta(days=7)
    return keys


def season_index(weeks: pd.DataFrame, season_weights: SeasonWeights) -> np.ndarray:
    """Return the multiplicative season index for each row of `weeks` (SPEC-01
    section 2.1).

    `1.0 + advent*advent_flag + schulbeginn*schulbeginn_flag + spring*spring_flag
    + jan_dip*jan_dip_flag + summer_lull*summer_lull_flag`. The YAML stores
    `jan_dip` and `summer_lull` **signed negative** (matching SPEC-01 section
    2.1's `- 0.20 x` / `- 0.10 x` notation), so all five terms are added here with
    no sign flip in code -- negating a value that is already negative in
    configuration would double-apply the sign, which is the obvious silent bug
    this function's tests guard against. A week with all five flags 0 returns
    exactly `1.0`; an adjacent flagged window never bleeds across its boundary
    because each term is gated by its own flag column, not by proximity.
    """
    w = season_weights
    result = (
        1.0
        + w.advent * weeks["advent_flag"].to_numpy()
        + w.schulbeginn * weeks["schulbeginn_flag"].to_numpy()
        + w.spring * weeks["spring_flag"].to_numpy()
        + w.jan_dip * weeks["jan_dip_flag"].to_numpy()
        + w.summer_lull * weeks["summer_lull_flag"].to_numpy()
    )
    return np.asarray(result, dtype=np.float64)


def baseline_demand(cfg: ScenarioConfig, weeks: pd.DataFrame) -> pd.DataFrame:
    """Return `cfg`'s baseline-demand components for each row of `weeks` (SPEC-01
    section 2.1): `base_t = b0 * (1 + g)^t * season_t * promo_mult_t`.

    Every component is returned as its own column, not just `base` -- T-103's
    second acceptance criterion, and what plan 02-06's SIM-071 decomposition
    audit re-sums: `trend` (`(1 + cfg.growth) ** t`), `season` (from
    `season_index`), `promo_mult` (`cfg.promo_multiplier` where `(iso_year,
    iso_week)` is listed in `cfg.promo_weeks`, else `1.0`), `promo_flag` (the
    same condition as an int 0/1), and `base` (`cfg.b0 * trend * season *
    promo_mult`).
    """
    t = weeks["t"].to_numpy()
    trend = (1.0 + cfg.growth) ** t
    season = season_index(weeks, cfg.season_weights)

    promo_flag = np.array(
        [
            1 if iso_week in cfg.promo_weeks.get(iso_year, ()) else 0
            for iso_year, iso_week in zip(weeks["iso_year"], weeks["iso_week"], strict=True)
        ],
        dtype=np.int64,
    )
    promo_mult = np.where(promo_flag == 1, cfg.promo_multiplier, 1.0)

    base = cfg.b0 * trend * season * promo_mult

    return pd.DataFrame(
        {
            "trend": trend,
            "season": season,
            "promo_mult": promo_mult,
            "promo_flag": promo_flag,
            "base": base,
        }
    )
