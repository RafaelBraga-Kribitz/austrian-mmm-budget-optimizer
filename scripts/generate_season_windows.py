"""Generate the Austrian season-window calendar seed (AD-020, T-011).

Owning SPEC: SPEC-01_ground_truth_simulator.md section 2.1 (the multiplicative
seasonality index and its five window definitions), disambiguated by
docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md section 1.2. Writes
dbt/seeds/season_windows.csv: one row per ISO week of every ISO year 2019-2027, with the
five boolean-as-integer window flags. This is the single sanctioned shared-CONFIG
exception to the W-2 simulator-versus-model firewall (SIM-003, A-1): both the Phase 2
simulator and the Phase 3 dbt staging layer read this seed, never each other's code.

Implements: REQ-dl8-quality

Two of the five rules read a gap the spec text leaves open, not a change to it (D-07,
docs/BUILD_LOG.md carries the dated entry):

- advent_flag (SPEC-01 section 2.1: "the 4 ISO weeks before and incl. the week of
  Dec 24"). Guide section 1.2 disambiguates this as exactly 4 flagged weeks total,
  ending at the Dec-24 week inclusive -- not 4 weeks before plus a 5th week of Dec 24.
  See advent_weeks() below for the source comment and the citation.
- schulbeginn_flag (SPEC-01 section 2.1: "around Styrian school start, early Sep").
  The `holidays` package carries no AT-6 (Styria) school-holiday subdivision, so there
  is no data source encoding the actual first school day. Guide section 1.2 fixes the
  reading as "second Monday of September": flag that ISO week and the week before it.
  See schulbeginn_weeks() below for the source comment and the citation.

This module does not import `holidays`: none of the five window rules needs a
public-holiday lookup -- three are fixed ISO-week ranges and the other two are derived
from fixed calendar dates (December 24, the second Monday of September) via
`date.isocalendar()`. The Phase 2 simulator is the consumer that will need `holidays`
(SPEC-01 section 2, AOV/media-effect calendar lookups), not this generator.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path

# ISO years covered by the seed: 2019 through 2027 inclusive (T-011 / WBS 02_WBS.md
# lines 224-250), wide enough to cover any plausible Layer R window.
YEAR_RANGE: range = range(2019, 2028)

# Resolved against the repository root (parent of scripts/), never the caller's cwd, so
# `uv run python scripts/generate_season_windows.py` writes the same path regardless of
# where it is invoked from.
SEED_PATH: Path = Path(__file__).resolve().parent.parent / "dbt" / "seeds" / "season_windows.csv"

# Fixed ISO-week ranges (SPEC-01 section 2.1; Guide section 1.2 lines 38).
JAN_DIP_WEEKS: range = range(2, 6)  # ISO weeks 2-5 inclusive
SPRING_WEEKS: range = range(14, 23)  # ISO weeks 14-22 inclusive
SUMMER_LULL_WEEKS: range = range(29, 34)  # ISO weeks 29-33 inclusive

FIELDNAMES: list[str] = [
    "iso_year",
    "iso_week",
    "week_start",
    "advent_flag",
    "schulbeginn_flag",
    "jan_dip_flag",
    "spring_flag",
    "summer_lull_flag",
]


def advent_weeks(year: int) -> list[tuple[int, int]]:
    """Return the four ISO (iso_year, iso_week) pairs flagged as advent for `year`.

    Source: SPEC-01 section 2.1 defines advent as "the 4 ISO weeks before and incl. the
    week of Dec 24". docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md section 1.2
    disambiguates this reading as exactly 4 flagged weeks total, ending at the Dec-24
    week inclusive (not 4 weeks before Dec 24 plus a 5th week containing Dec 24 itself).
    This is a D-07 interpretation, not a spec edit -- the spec text is unchanged, and the
    reading fills a gap it left open; recorded in docs/BUILD_LOG.md under M0.

    The arithmetic walks calendar dates (the Monday of the Dec-24 ISO week, stepped back
    7/14/21 days), never week numbers directly, so an ISO-year boundary can never yield a
    week 0 or a wrapped week number.
    """
    dec24 = date(year, 12, 24)
    dec24_monday = dec24 - timedelta(days=dec24.weekday())
    pairs: list[tuple[int, int]] = []
    for offset_days in (21, 14, 7, 0):
        monday = dec24_monday - timedelta(days=offset_days)
        iso_year, iso_week, _ = monday.isocalendar()
        pairs.append((iso_year, iso_week))
    return pairs


def schulbeginn_weeks(year: int) -> list[tuple[int, int]]:
    """Return the two ISO (iso_year, iso_week) pairs flagged as schulbeginn for `year`.

    Source: SPEC-01 section 2.1 defines schulbeginn as "1 in the 2 weeks around Styrian
    school start, early Sep", without a precise date. The `holidays` package's Austria
    calendar carries no AT-6 (Styria) school-holiday subdivision, so there is no data
    source encoding the actual first school day. docs/EXECUTION_BLUEPRINT/
    05_IMPLEMENTATION_GUIDES.md section 1.2 fixes the reading as "second Monday of
    September" (fixed rule): flag the ISO week containing that Monday and the ISO week
    before it. This is a D-07 interpretation, not a spec edit -- the spec text is
    unchanged, and the reading fills a gap it left open; recorded in docs/BUILD_LOG.md
    under M0.
    """
    sept1 = date(year, 9, 1)
    first_monday = sept1 + timedelta(days=(7 - sept1.weekday()) % 7)
    second_monday = first_monday + timedelta(days=7)
    pairs: list[tuple[int, int]] = []
    for monday in (second_monday - timedelta(days=7), second_monday):
        iso_year, iso_week, _ = monday.isocalendar()
        pairs.append((iso_year, iso_week))
    return pairs


def _iso_week_mondays(iso_year: int) -> list[date]:
    """Return the Monday date of every ISO week belonging to `iso_year`.

    Walks forward from the Monday of ISO week 1 in 7-day steps until the ISO year
    changes, rather than assuming 52 weeks, so ISO years carrying a 53rd week (2020,
    2026 in this range) are complete.
    """
    mondays: list[date] = []
    monday = date.fromisocalendar(iso_year, 1, 1)
    while monday.isocalendar()[0] == iso_year:
        mondays.append(monday)
        monday += timedelta(days=7)
    return mondays


def build_rows(year_range: Iterable[int]) -> list[dict[str, int | str]]:
    """Build one row per ISO week of every ISO year in `year_range`.

    Key order matches FIELDNAMES exactly. Flags are always the integers 0 or 1, never
    booleans and never blanks. Rows are returned sorted by iso_year then iso_week.
    """
    rows: list[dict[str, int | str]] = []
    for year in year_range:
        advent_set = set(advent_weeks(year))
        schulbeginn_set = set(schulbeginn_weeks(year))
        for monday in _iso_week_mondays(year):
            iso_year, iso_week, _ = monday.isocalendar()
            key = (iso_year, iso_week)
            rows.append(
                {
                    "iso_year": iso_year,
                    "iso_week": iso_week,
                    "week_start": monday.isoformat(),
                    "advent_flag": 1 if key in advent_set else 0,
                    "schulbeginn_flag": 1 if key in schulbeginn_set else 0,
                    "jan_dip_flag": 1 if iso_week in JAN_DIP_WEEKS else 0,
                    "spring_flag": 1 if iso_week in SPRING_WEEKS else 0,
                    "summer_lull_flag": 1 if iso_week in SUMMER_LULL_WEEKS else 0,
                }
            )
    rows.sort(key=lambda row: (row["iso_year"], row["iso_week"]))
    return rows


def main() -> int:
    """Write the season-window seed to SEED_PATH and return an exit code.

    Determinism is the whole contract: the file is opened with `newline=""` and the CSV
    writer's line terminator is pinned to a bare `"\\n"`, so Windows never emits a
    carriage return regardless of platform default. This does not lean on the
    `.gitattributes` LF pin from plan 01-01 -- CI job 1's regeneration diff-check (D-20)
    compares the working tree before git's checkout filters run, so the writer itself
    must be byte-stable. No index column is written; the header is the FIELDNAMES order;
    rows are sorted by iso_year then iso_week; there is no trailing blank line beyond the
    final record's own terminator.
    """
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows(YEAR_RANGE)
    with SEED_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
