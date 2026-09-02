---
phase: 03-warehouse
plan: 03
subsystem: database
tags: [dbt, duckdb, warehouse, data-pipeline, testing]

# Dependency graph
requires:
  - phase: 03-warehouse (plan 01)
    provides: dbt project scaffold, committed profiles.yml (dev/test targets), five source-path-parameterized raw views over the Phase 2 synthetic CSVs
provides:
  - four staging views with BP-D-03's unit-neutral renames applied
  - native unique/not_null/accepted_values grain tests, no dbt_utils
  - the one authored home for the strict AD-043 unit-suffix singular test
  - the poisoned-fixture pytest harness proving a duplicate grain key fails dbt build
affects: [03-04, 03-05, 03-06, phase-6-intake]

key-files:
  created:
    - dbt/models/staging/stg_media_weekly.sql
    - dbt/models/staging/stg_outcome_weekly.sql
    - dbt/models/staging/stg_promo.sql
    - dbt/models/staging/stg_calendar_weekly.sql
    - dbt/models/staging/_staging__schema.yml
    - dbt/tests/ad043_no_unit_suffix_columns.sql
  modified:
    - tests/unit/test_warehouse_build.py

requirements-completed: []

duration: 20min
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 3: Staging Layer, AD-043, and Poisoned-Fixture Proof Summary

**Four staging views with BP-D-03 unit-neutral renames, native grain tests plus the AD-043 unit-suffix singular test, and a poisoned-fixture harness that proves a duplicate grain key fails `dbt build`.**

## Task Commits

1. **Task 1: four staging models** — `55da8f1` (feat)
2. **Task 2: grain tests + AD-043** — `c3b4759` (test)
3. **Task 3: poisoned-fixture harness** — `bcd40b6` (test)

**Plan metadata:** (this commit)

## Accomplishments

- `stg_media_weekly`, `stg_outcome_weekly`, `stg_promo`, `stg_calendar_weekly` with BP-D-03 renames (`spend_eur`/`spend_aeur` → `spend`, etc.). No `distinct`/`group by`/`row_number`.
- Native unique/not_null/accepted_values on all four models; AD-043 singular test on `information_schema.columns` scoped to `stg_`/`fct_`/`dim_`.
- Poisoned fixture: throwaway `shutil.copytree` of `data/synthetic/`; isolated `--target test` via `AMBO_TEST_WAREHOUSE` / `DBT_TARGET_PATH`; duplicate `(week_start, channel)` fails `unique_stg_media_weekly`.

## Deviations from Plan

**1. [Process] 2A copy** from m0 `92d08d5` / `ec2d119` / `f91e405`. Red-then-green AD-043 probe recorded on m0, not re-run as a live rename here.

**2. [Process] 4B** one PR per plan.

## Issues Encountered

None. `make lint && make test` — **291 passed**, 93% coverage.

## Next Phase Readiness

Next: **03-04** (`fct_mmm_input` contract, AD-040/041/042).

---
*Phase: 03-warehouse*
*Completed: 2026-09-02*

## Self-Check: PASSED

Hashes `55da8f1`, `c3b4759`, `bcd40b6` are on `cursor/staging-layer-9588`.
