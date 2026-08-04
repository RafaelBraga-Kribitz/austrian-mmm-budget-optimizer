---
phase: 01-repository-foundation
plan: 06
subsystem: infra
tags: [season-windows, calendar, dbt-seed, generator, D-07]

# Dependency graph
requires:
  - phase: 01-02
    provides: "pyproject.toml (holidays pinned in uv.lock, mypy files=[\"src/ambo\"] scope excluding scripts/), importable repo tree"
provides:
  - "scripts/generate_season_windows.py — deterministic generator for the Austrian season-window calendar (AD-020): YEAR_RANGE, SEED_PATH, JAN_DIP_WEEKS, SPRING_WEEKS, SUMMER_LULL_WEEKS, advent_weeks(), schulbeginn_weeks(), build_rows(), main()"
  - "dbt/seeds/season_windows.csv — the committed, byte-stable, single calendar shared across the W-2 simulator-versus-model firewall: 470 rows, ISO years 2019-2027, LF-only, no index column"
  - "tests/unit/test_season_windows.py — 10 tests enumerating all five window rules, coverage (including 53-week years 2020/2026), 2022 literal spot values, and idempotence against the committed bytes"
  - "docs/BUILD_LOG.md — D-07 entry recording both spec interpretations (advent, schulbeginn), append-only"
affects: [01-07, 01-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ISO-week enumeration walks Mondays via date.fromisocalendar(year, 1, 1) stepped by 7 days until the ISO year changes, rather than assuming 52 weeks — the only way to correctly include the 53rd week in 2020 and 2026 within the 2019-2027 range"
    - "Window-rule date arithmetic operates on dates (Monday of the Dec-24 week, stepped back 7/14/21 days; the second Monday of September computed from Sept 1's weekday) rather than on week numbers directly, so an ISO-year boundary can never produce a week 0 or a wrapped number"
    - "CSV byte-determinism achieved at the writer level, not via .gitattributes: file opened with newline=\"\" and csv.DictWriter's lineterminator pinned to a bare \"\\n\", so the working-tree bytes are already LF-only before git's checkout filters ever run — matters because CI job 1's regeneration diff-check (D-20, wired in 01-09) compares the working tree pre-filter"
    - "No holidays package import in this script: all five window rules reduce to fixed ISO-week ranges or fixed calendar dates (Dec 24, second Monday of September), so importing holidays here would be decorative; documented in the module docstring, with the Phase 2 simulator named as the actual future consumer"
    - "Test-file import of a scripts/ module (no package, no conftest.py yet — that lands in 01-07) via an explicit sys.path insertion of scripts/ ahead of `import generate_season_windows`, scoped to the test file itself rather than depending on pytest's rootdir-based import mode"

key-files:
  created:
    - scripts/generate_season_windows.py
    - dbt/seeds/season_windows.csv
    - tests/unit/test_season_windows.py
  modified:
    - docs/BUILD_LOG.md

key-decisions:
  - "Advent read as exactly 4 flagged weeks total, ending at the ISO week containing Dec 24 inclusive (not 5 weeks) — SPEC-01 section 2.1's phrasing is compatible with either reading; docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md section 1.2 resolves it explicitly toward 4. D-07 interpretation, recorded in docs/BUILD_LOG.md and in advent_weeks()'s own source comment, not an ADR."
  - "Schulbeginn read as the second Monday of September, fixed every year — the holidays package carries no AT-6 (Styria) school-holiday subdivision, so there is no calendar data source for the true first school day. D-07 interpretation per the Guide's fixed rule, recorded in docs/BUILD_LOG.md and in schulbeginn_weeks()'s own source comment."
  - "holidays package not imported in this script — none of the five window rules needs a public-holiday lookup, only fixed ISO-week ranges or fixed calendar dates. Documented in the module docstring rather than importing for appearance, per the plan's own instruction; the Phase 2 simulator is named as the actual consumer."

requirements-completed: [REQ-dl8-quality]

coverage:
  - id: D1
    description: "dbt/seeds/season_windows.csv committed, ISO years 2019-2027, every ISO week of every year present exactly once including 53-week years, regeneration byte-idempotent, no carriage return bytes"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: unit
        ref: "task-1 automated verify: header exact match; git diff --exit-code clean after second run; no \\r byte; year set == range(2019,2028); row count == sum of true ISO-week counts (470 == 470)"
        status: pass
      - kind: unit
        ref: "tests/unit/test_season_windows.py::test_every_iso_year_and_week_present_exactly_once"
        status: pass
    human_judgment: false
  - id: D2
    description: "Five window rules enumerated as independent tests with 2022 literal spot values, plus flag-column binary-integer and week_start/ISO-calendar consistency checks"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: unit
        ref: "tests/unit/test_season_windows.py (10 tests): advent, schulbeginn, jan_dip, spring, summer_lull, binary-flags, week_start-consistency, 2022-literal-spot-values, coverage, idempotence"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both spec interpretations (advent, schulbeginn) documented in-script with SPEC-01 section 2.1 + Guide section 1.2 citations, and recorded as a D-07 append-only build-log entry, not an ADR"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "grep -qi 'advent'/'schulbeginn' docs/BUILD_LOG.md; git diff --stat docs/BUILD_LOG.md shows insertions-only (28 insertions, 0 deletions)"
        status: pass
    human_judgment: false
  - id: D4
    description: "uv run ruff check/format --check and uv run mypy stay clean after both tasks; full unit suite (26 tests) green"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "uv run ruff check . — All checks passed; uv run ruff format --check . — 63 files already formatted; uv run mypy — Success (11 source files, scripts/ out of scope by files=[\"src/ambo\"]); uv run pytest tests/unit -q — 26 passed"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 6: Austrian Season-Window Calendar (generator, committed seed, tests) Summary

**One deterministic generator, one byte-stable committed CSV seed covering ISO years 2019-2027, and ten enumerated tests — the single sanctioned shared-CONFIG exception across the Phase 2 simulator / Phase 3 dbt-staging W-2 firewall (AD-020), with both spec-gap interpretations recorded per D-07.**

## Performance

- **Duration:** ~15 min (context reading through final self-check)
- **Started:** 2026-08-04T19:10:00Z (approx., prior plan's close)
- **Completed:** 2026-08-04T19:25:45Z
- **Tasks:** 2 (both `type="auto"`, no checkpoints)
- **Files modified:** 4 (2 created in Task 1, 1 created + 1 modified in Task 2)

## Accomplishments
- `scripts/generate_season_windows.py`: `YEAR_RANGE` (2019-2027), `SEED_PATH` (resolved against the repo root, not cwd), `JAN_DIP_WEEKS`/`SPRING_WEEKS`/`SUMMER_LULL_WEEKS` fixed ranges, `advent_weeks(year)` and `schulbeginn_weeks(year)` deriving ISO `(year, week)` pairs from date arithmetic (never week-number arithmetic), `build_rows(year_range)` walking Mondays per ISO year (so 53-week years are complete), and `main()` writing the seed with an explicit LF line terminator and `newline=""`, no index column, sorted by `iso_year` then `iso_week`
- `dbt/seeds/season_windows.csv`: 470 rows (ISO years 2019-2027, including the 53-week years 2020 and 2026), header `iso_year,iso_week,week_start,advent_flag,schulbeginn_flag,jan_dip_flag,spring_flag,summer_lull_flag`, no carriage-return bytes, confirmed byte-idempotent by running the generator a second time after committing and getting a clean `git diff`
- `tests/unit/test_season_windows.py`: 10 test functions — coverage (every ISO year/week present exactly once, computed per-year expected count via the `date(year, 12, 28).isocalendar()[1]` trick, not hardcoded 52), advent (exactly 4 weeks/year including the Dec-24 week, cross-checked against an independently-written date computation), schulbeginn (exactly 2 weeks/year, later one is the second-Monday-of-September week), the three fixed-range rules, flag-column binary-integer validation, `week_start`/ISO-calendar self-consistency, a fully literal 2022 spot-value test (advent weeks 48-51, schulbeginn weeks 36-37, one week each from jan_dip/spring/summer_lull — all hardcoded, no re-derivation), and an idempotence test that regenerates into `tmp_path` (via `monkeypatch.setattr(gsw, "SEED_PATH", ...)`) and compares bytes against the committed seed
- `docs/BUILD_LOG.md`: one new D-07 entry under the M0 section recording both interpretations (advent = 4 weeks total; schulbeginn = second Monday of September) with their SPEC-01 section 2.1 and Guide section 1.2 citations — additions only, no existing entry touched

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the generator and commit the byte-stable seed** - `d9da91e` (feat)
2. **Task 2: Enumerate the five window rules as tests and record the interpretation** - `1b66ed3` (test)

**Plan metadata:** committed separately after this summary is written.

## Files Created/Modified
- `scripts/generate_season_windows.py` - Deterministic generator: `YEAR_RANGE`, `SEED_PATH`, `JAN_DIP_WEEKS`, `SPRING_WEEKS`, `SUMMER_LULL_WEEKS`, `advent_weeks()`, `schulbeginn_weeks()`, `_iso_week_mondays()`, `build_rows()`, `main()`
- `dbt/seeds/season_windows.csv` - Committed seed, 470 rows, ISO years 2019-2027
- `tests/unit/test_season_windows.py` - 10 tests: coverage, advent, schulbeginn, jan_dip, spring, summer_lull, binary flags, week_start consistency, 2022 literal spot values, idempotence
- `docs/BUILD_LOG.md` - D-07 entry (advent + schulbeginn interpretations), append-only

## Decisions Made
- **Advent = 4 flagged weeks total, ending at the Dec-24 week inclusive** — see key-decisions above; the Guide's own explicit disambiguation of an otherwise-ambiguous SPEC-01 sentence.
- **Schulbeginn = second Monday of September, fixed every year** — the `holidays` package has no AT-6 school-calendar subdivision; the Guide's fixed rule is the only encodable reading.
- **No `holidays` import in this script** — none of the five rules needs a public-holiday lookup; documented in the module docstring per the plan's own instruction rather than importing for appearance.

## Deviations from Plan

None — plan executed exactly as written. Both `<read_first>` citations (SPEC-01 section 2.1, Guide section 1.2) were verified directly against the source documents before writing code, and both D-07 interpretations match the Guide's explicit text.

## Issues Encountered

One minor formatting-only correction during Task 2: `uv run ruff format --check .` flagged one line in `tests/unit/test_season_windows.py` as exceeding the preferred single-line width; `uv run ruff format` reflowed it before commit. No logic change, not tracked as a deviation (pure formatting, caught by the project's own toolchain before the commit was made — not a bug, missing functionality, or blocker under Rules 1-3).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `dbt/seeds/season_windows.csv` is now the single, committed, byte-stable calendar that Phase 2's simulator and Phase 3's dbt staging layer will both read — the one sanctioned shared-CONFIG exception to the W-2 simulator/model firewall (SIM-003, A-1)
- CI job 1's regeneration diff-check (D-20) — to be wired in plan 01-09 — has a real generator and a real committed artifact to diff against; both were proven idempotent by hand in this plan (`uv run python scripts/generate_season_windows.py && git diff --exit-code` clean, run twice)
- The D-07 pattern (in-script source comment + dated BUILD_LOG.md entry, no ADR) is now demonstrated end-to-end and is the template for any future spec-gap interpretation
- The `sys.path` insertion pattern in `tests/unit/test_season_windows.py` for importing a `scripts/` module without a package `__init__.py` is a candidate for consolidation into `tests/conftest.py` once plan 01-07 creates it — not required now, since only this one test module needs it
- `scripts/generate_season_windows.py` stays outside mypy's `strict` scope (`files = ["src/ambo"]`), consistent with T-002's original scoping; no mypy override was needed

---
*Phase: 01-repository-foundation*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 4 created/modified artifacts found on disk (scripts/generate_season_windows.py,
dbt/seeds/season_windows.csv, tests/unit/test_season_windows.py, docs/BUILD_LOG.md);
both task commits verified present in git history (d9da91e, 1b66ed3).
