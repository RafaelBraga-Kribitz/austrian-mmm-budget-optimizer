---
phase: 03-warehouse
plan: 07
subsystem: database
tags: [db, ad-030, data-doorway]

duration: 15min
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 7: AD-030 data doorway (db.py) Summary

**`ambo.common.db` is the only data doorway: read-only `connect()`, contract-derived columns from mart YAML, three accessors with collect-all-raise-once `DataContractError` postconditions.**

## Task Commits

1. **Task 1: connect + contract columns** — `a5320d1` (feat)
2. **Task 2: three accessors** — `5e55ea1` (feat)
3. **Task 3: test_db.py + MODULE_CONTRACTS** — `be5a0ba` (test)

**Plan metadata:** (this commit)

## Accomplishments

- Missing warehouse names `make transform`. Unknown layer lists valid layers from `dim_layer`.
- Column lists derived from `dbt/models/marts/*.yml` (D-08), never restated.
- Round trip vs simulator CSVs within 1e-6; offline NULLs preserved; two simultaneous postcondition violations in one message (D-10).

## Deviations from Plan

**1. [Process] 2A copy** from m0 `ffe6f41` / `3149e36` / `5c204cb`.

**2. [Process] 4B** one PR per plan.

## Issues Encountered

None. `make lint && make test` — **309 passed**, 93% coverage.

## Next Phase Readiness

Next: **03-08** (`export_marts.py` + committed `exports/mmm_input_weekly.csv`).

---
*Phase: 03-warehouse*
*Completed: 2026-09-02*

## Self-Check: PASSED
