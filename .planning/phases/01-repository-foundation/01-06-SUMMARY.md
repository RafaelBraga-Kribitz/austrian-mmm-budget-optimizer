---
phase: 01-repository-foundation
plan: 06
subsystem: data
tags: [season-windows, ad-020, d-07, dbt-seed]
requires:
  - phase: 01-02
    provides: "scripts/ and dbt/seeds/ skeleton, holidays in lockfile"
provides:
  - "scripts/generate_season_windows.py — byte-stable Austrian calendar generator"
  - "dbt/seeds/season_windows.csv — 470 rows, ISO 2019-2027, LF-only"
  - "tests/unit/test_season_windows.py — five rules + 2022 spots + idempotence"
  - "D-07 BUILD_LOG interpretations (advent 4 weeks; schulbeginn second Monday of September)"
affects: [01-09, 02, 03]
key-files:
  created:
    - scripts/generate_season_windows.py
    - dbt/seeds/season_windows.csv
    - tests/unit/test_season_windows.py
  modified:
    - docs/BUILD_LOG.md
key-decisions:
  - "Copied from verified m0-bootstrap d9da91e / 1b66ed3 (2A)"
  - "No holidays import in the generator (none of the five rules needs it)"
requirements-completed: [REQ-dl8-quality]
duration: 10min
completed: 2026-09-01
status: complete
---

# Phase 1 Plan 6: Season-windows Summary

**Committed AD-020 calendar (2019–2027, 470 ISO weeks including 53-week years) with enumerated rule tests and D-07 interpretation record.**

## Task Commits

1. **Task 1** — `21cca91` generator + seed (from m0 `d9da91e`)
2. **Task 2** — `5130a4f` tests + D-07 BUILD_LOG (from m0 `1b66ed3`)

**Plan metadata:** this commit.

## Deviations from Plan

**1. [Process] One PR per plan (4B)** not per task.

**Total deviations:** 1 process. No scope creep.

## Self-Check: PASSED

- Second generator run: `git diff --exit-code dbt/seeds/season_windows.csv` clean
- Header exact; no CR; 470 rows = true ISO week count 2019–2027
- 10 tests pass; BUILD_LOG Task 2 diff additions-only (0 deletions)

---
*Phase: 01-repository-foundation*
*Completed: 2026-09-01*
