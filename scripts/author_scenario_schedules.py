"""Deterministic promo/burst placement authoring aid for SPEC-01's three scenarios.

This is a **dev-only, one-off authoring aid** (CONTEXT.md D-02): its stdout is copied
by hand into `config/scenarios/{s_a,s_b,s_c}.yaml` as frozen constants and is never
executed at simulate time (docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md
section 1.1: "seeded-random placement for the unanchored [weeks] happens ONCE at
authoring time [...], not at runtime"). It lives outside `src/` deliberately so it
can never become importable production code (09_ANTI_PATTERNS.md A-13 speculative
generality) -- `grep -rn "author_scenario_schedules" src/` must always return
nothing.

Owning spec: SPEC-01_ground_truth_simulator.md section 3 (per-channel spend-pattern
composition and counts); docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md section
1.1 (promo-week composition, burst-count rules, the frozen-at-authoring-time rule);
docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md line 113 (BP-D-09, round-half-up
pro-rating for a partial year).

Implements: REQ-grain-and-windows

Reads `dbt/seeds/season_windows.csv` (AD-020, the single sanctioned shared-CONFIG
exception) to locate Advent/Schulbeginn/spring anchors -- this script never
recomputes calendar-window logic itself; that logic's single home is
`scripts/generate_season_windows.py`, which is not imported here (a one-off script
carries nothing importable) and is treated as a frozen, read-only calendar seed.

Writes no files: every scenario's placements print to stdout as a YAML fragment
(`promo_weeks`, `burst_starts`) for hand-copy into the matching scenario YAML in
plan 02-03's Task 2. This is what keeps the "frozen into YAML, not computed at
simulate time" boundary literal -- there is no code path from here into
`src/ambo/simulate/`.
"""

from __future__ import annotations

import argparse
import csv
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import yaml

# Resolved the same way scripts/generate_season_windows.py resolves its own
# SEED_PATH: relative to this file, never the caller's cwd.
SEED_PATH: Path = Path(__file__).resolve().parent.parent / "dbt" / "seeds" / "season_windows.csv"

# The aid's RNG is seeded `scenario_seed + _AUTHORING_SEED_OFFSET` -- deliberately
# distinct from the simulator's own runtime stream (which seeds directly from
# `cfg.seed`), so nobody mistakes this authoring-time-only stream for a runtime one.
_AUTHORING_SEED_OFFSET = 900_000

# SPEC-01 section 5, verbatim: the three scenarios' (seed, window) pairs.
SCENARIOS: dict[str, dict[str, object]] = {
    "s_a": {"seed": 101, "start": (2021, 1), "end": (2023, 52)},
    "s_b": {"seed": 202, "start": (2022, 1), "end": (2023, 52)},
    "s_c": {"seed": 303, "start": (2022, 1), "end": (2023, 26)},
}

PROMO_WEEKS_PER_YEAR = 10
PRINT_BURSTS_PER_YEAR = 8
PRINT_BURST_LENGTH = 2
RADIO_BURSTS_PER_YEAR = 5
RADIO_BURST_LENGTH = 3


def read_windows(path: Path) -> dict[int, dict[str, tuple[int, ...]]]:
    """Per ISO year: the flagged `advent`/`schulbeginn`/`spring` week numbers,
    plus that year's total ISO week count under `weeks_in_year` (a 1-tuple, to
    keep every value in this mapping a `tuple[int, ...]`)."""
    advent: dict[int, list[int]] = {}
    schulbeginn: dict[int, list[int]] = {}
    spring: dict[int, list[int]] = {}
    max_week: dict[int, int] = {}

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            year = int(row["iso_year"])
            week = int(row["iso_week"])
            advent.setdefault(year, [])
            schulbeginn.setdefault(year, [])
            spring.setdefault(year, [])
            if row["advent_flag"] == "1":
                advent[year].append(week)
            if row["schulbeginn_flag"] == "1":
                schulbeginn[year].append(week)
            if row["spring_flag"] == "1":
                spring[year].append(week)
            max_week[year] = max(max_week.get(year, 0), week)

    return {
        year: {
            "advent": tuple(sorted(advent[year])),
            "schulbeginn": tuple(sorted(schulbeginn[year])),
            "spring": tuple(sorted(spring[year])),
            "weeks_in_year": (max_week[year],),
        }
        for year in max_week
    }


def prorate(full_count: int, covered_weeks: int, weeks_in_year: int) -> int:
    """`floor(full_count * covered_weeks / weeks_in_year + 0.5)` -- round half UP
    (BP-D-09). Never `round()`, whose banker's rounding would turn 2.5 into 2."""
    return math.floor(full_count * covered_weeks / weeks_in_year + 0.5)


def black_friday_week(iso_year: int, windows: dict[int, dict[str, tuple[int, ...]]]) -> int:
    """The ISO week containing the 4th Friday of November of `iso_year`.

    Computed directly from `datetime.date`/`isocalendar()`, never by hand-rolled
    week arithmetic. `windows` is accepted for signature symmetry with the other
    anchor functions below even though this particular anchor needs no seed
    lookup.
    """
    del windows  # unused: Black Friday is a fixed calendar rule, not a seed lookup
    fridays_seen = 0
    day = date(iso_year, 11, 1)
    while True:
        if day.weekday() == 4:  # Monday=0 .. Friday=4
            fridays_seen += 1
            if fridays_seen == 4:
                _, iso_week, _ = day.isocalendar()
                return iso_week
        day += timedelta(days=1)


def anchored_promo_weeks(
    iso_year: int,
    windows: dict[int, dict[str, tuple[int, ...]]],
    covered: tuple[int, int],
) -> tuple[int, ...]:
    """The Black Friday week, the 2 Advent-flagged weeks nearest Dec 24 (excluding
    Black Friday), and 2 weeks inside the spring window -- each included only if
    it falls inside `covered` = (first_week, last_week) inclusive for this year.

    Guide section 1.1: "2 Advent weeks (choose the 2 advent-flagged weeks nearest
    Dec 24 that are not the BF week), 2 spring weeks (inside W14-22)". The exact
    pair of spring weeks is implementer discretion (CONTEXT.md D-01): this reads
    "2 weeks inside the spring window" as the window's own 1/3 and 2/3 points, so
    they sit apart from each other and from the window edges regardless of the
    window's length.
    """
    covered_start, covered_end = covered
    year_windows = windows[iso_year]
    anchors: list[int] = []

    bf_week = black_friday_week(iso_year, windows)
    if covered_start <= bf_week <= covered_end:
        anchors.append(bf_week)

    # advent weeks are stored ascending; the ones nearest Dec 24 are the highest
    # (season_windows.csv's advent_flag ends at the ISO week containing Dec 24).
    nearest_to_dec24 = list(reversed(year_windows["advent"]))
    fallback_candidates = [week for week in nearest_to_dec24 if week != bf_week]
    for week in fallback_candidates[:2]:
        if covered_start <= week <= covered_end and week not in anchors:
            anchors.append(week)

    spring_weeks = year_windows["spring"]
    n = len(spring_weeks)
    for idx in (n // 3, (2 * n) // 3):
        week = spring_weeks[idx]
        if covered_start <= week <= covered_end and week not in anchors:
            anchors.append(week)

    return tuple(sorted(set(anchors)))


def anchored_burst_starts(
    channel: str,
    iso_year: int,
    windows: dict[int, dict[str, tuple[int, ...]]],
    covered: tuple[int, int],
) -> tuple[int, ...]:
    """The fixed-rule (non-spread) burst starts for `channel`, each included only
    if its *whole span* lies inside `covered` = (first_week, last_week) inclusive.

    With `A` = the first Advent-flagged week and `S` = the first Schulbeginn-
    flagged week of the year: `print_regional` anchors at `(A, A+2, S)` (2 in
    Advent, 1 in Schulbeginn, per Guide section 1.1); `radio` anchors at
    `(A-3, A)`. Two 3-week radio bursts cannot both fit inside the 4-week Advent
    window without overlapping, so the pair is authored as a lead-in burst
    (`A-3`, ending the week before Advent starts) plus an in-Advent burst (`A`),
    both anchored to the Advent demand peak -- this reading is recorded for
    docs/BUILD_LOG.md at M1 close.
    """
    covered_start, covered_end = covered
    year_windows = windows[iso_year]
    advent_start = year_windows["advent"][0]
    schulbeginn_start = year_windows["schulbeginn"][0]

    if channel == "print_regional":
        length = PRINT_BURST_LENGTH
        raw_starts: tuple[int, ...] = (advent_start, advent_start + 2, schulbeginn_start)
    elif channel == "radio":
        length = RADIO_BURST_LENGTH
        raw_starts = (advent_start - 3, advent_start)
    else:
        raise ValueError(f"anchored_burst_starts(): no anchoring rule for channel {channel!r}")

    starts = [
        start
        for start in raw_starts
        if covered_start <= start and start + length - 1 <= covered_end
    ]
    return tuple(sorted(set(starts)))


def spread_placements(
    rng: np.random.Generator,
    needed: int,
    forbidden: tuple[tuple[int, int], ...],
    span: tuple[int, int],
    length: int,
) -> tuple[int, ...]:
    """Draw `needed` non-overlapping start weeks for spans of `length` weeks from
    `span` = (first_week, last_week) inclusive, deterministic given `rng`.

    `forbidden` is a tuple of `(start, length)` spans already placed in the same
    channel-year (typically the anchored weeks) -- a candidate start is rejected
    if its own span `[start, start+length-1]` intersects any forbidden or
    already-chosen span. For single-week spans (`length == 1`, i.e. promo weeks)
    a candidate immediately touching an existing span is also avoided when a
    non-touching candidate remains (Guide section 1.1: "avoiding adjacency where
    possible"); multi-week bursts only forbid overlap, matching "bursts must not
    overlap" (not "must not touch"). Returns weeks sorted ascending.
    """
    if needed <= 0:
        return ()

    first_week, last_week = span
    candidates = list(range(first_week, last_week - length + 2))
    rng.shuffle(candidates)

    placed: list[tuple[int, int]] = list(forbidden)
    chosen: list[int] = []

    def overlaps(start: int) -> bool:
        return any(
            start < p_start + p_length and p_start < start + length for p_start, p_length in placed
        )

    def touches(start: int) -> bool:
        return any(
            start == p_start + p_length or p_start == start + length for p_start, p_length in placed
        )

    # Pass 1: non-overlapping, and non-adjacent for single-week spans.
    for start in candidates:
        if len(chosen) >= needed:
            break
        if overlaps(start):
            continue
        if length == 1 and touches(start):
            continue
        chosen.append(start)
        placed.append((start, length))

    # Pass 2 (only if pass 1 fell short): relax adjacency, overlap stays forbidden.
    if len(chosen) < needed:
        for start in candidates:
            if len(chosen) >= needed:
                break
            if start in chosen or overlaps(start):
                continue
            chosen.append(start)
            placed.append((start, length))

    if len(chosen) < needed:
        raise RuntimeError(
            f"spread_placements(): could not place {needed} non-overlapping span(s) of "
            f"length {length} in span {span} avoiding {forbidden!r} (only placed "
            f"{len(chosen)})"
        )

    return tuple(sorted(chosen))


def _covered_span(
    iso_year: int, start: tuple[int, int], end: tuple[int, int], weeks_in_year: int
) -> tuple[int, int]:
    start_year, start_week = start
    end_year, end_week = end
    covered_start = start_week if iso_year == start_year else 1
    covered_end = end_week if iso_year == end_year else weeks_in_year
    return covered_start, covered_end


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dev-only authoring aid (CONTEXT.md D-02): prints a deterministic "
            "promo_weeks/burst_starts YAML fragment for one or all SPEC-01 "
            "scenarios. Writes no files -- copy the printed fragment by hand into "
            "config/scenarios/<scenario>.yaml."
        )
    )
    parser.add_argument(
        "--scenario",
        choices=("s_a", "s_b", "s_c", "all"),
        default="all",
        help="which scenario to print (default: all three, in s_a/s_b/s_c order)",
    )
    args = parser.parse_args(argv)

    windows = read_windows(SEED_PATH)
    requested = ("s_a", "s_b", "s_c") if args.scenario == "all" else (args.scenario,)

    for name in requested:
        cfg = SCENARIOS[name]
        seed = int(cfg["seed"])  # type: ignore[arg-type]
        start = cfg["start"]
        end = cfg["end"]
        assert isinstance(start, tuple) and isinstance(end, tuple)
        start_year, _start_week = start
        end_year, _end_week = end
        rng = np.random.default_rng(seed + _AUTHORING_SEED_OFFSET)

        promo_weeks: dict[int, list[int]] = {}
        burst_starts: dict[str, dict[int, list[int]]] = {"print_regional": {}, "radio": {}}

        for year in range(start_year, end_year + 1):
            weeks_in_year = windows[year]["weeks_in_year"][0]
            covered = _covered_span(year, start, end, weeks_in_year)
            covered_weeks = covered[1] - covered[0] + 1

            promo_count = prorate(PROMO_WEEKS_PER_YEAR, covered_weeks, weeks_in_year)
            promo_anchors = anchored_promo_weeks(year, windows, covered)
            promo_spread = spread_placements(
                rng,
                promo_count - len(promo_anchors),
                tuple((week, 1) for week in promo_anchors),
                covered,
                1,
            )
            promo_weeks[year] = sorted({*promo_anchors, *promo_spread})

            for channel, per_year_count, length in (
                ("print_regional", PRINT_BURSTS_PER_YEAR, PRINT_BURST_LENGTH),
                ("radio", RADIO_BURSTS_PER_YEAR, RADIO_BURST_LENGTH),
            ):
                count = prorate(per_year_count, covered_weeks, weeks_in_year)
                anchors = anchored_burst_starts(channel, year, windows, covered)
                spread = spread_placements(
                    rng,
                    count - len(anchors),
                    tuple((start_week, length) for start_week in anchors),
                    covered,
                    length,
                )
                burst_starts[channel][year] = sorted({*anchors, *spread})

        fragment = {"promo_weeks": promo_weeks, "burst_starts": burst_starts}
        print(f"# {name}")
        print(yaml.safe_dump(fragment, sort_keys=True, default_flow_style=False), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
