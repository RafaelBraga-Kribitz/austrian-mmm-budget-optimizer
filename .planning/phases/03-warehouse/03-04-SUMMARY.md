---
phase: 03-warehouse
plan: 04
subsystem: database
tags: [dbt, duckdb, warehouse, fct-mmm-input, contract]

requires:
  - phase: 03-warehouse (plan 03)
    provides: staging views and poisoned-fixture harness
provides:
  - fct_mmm_input as the sole model input contract (17 columns, enforced)
  - AD-040 seed-derived gapless week spine
  - AD-041 value ranges
  - AD-042 three-layer revenue reconciliation
affects: [03-05, 03-07, 04-model]

duration: 20min
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 4: fct_mmm_input Contract Summary

**`fct_mmm_input` is the week × layer modeling matrix with an enforced 17-column contract, AD-040/041/042 tests, and pytest reconciliation against the simulator CSVs.**

## Task Commits

1. **Task 1: jinja-pivoted matrix** — `57938ae` (feat)
2. **Task 2: enforced contract + AD-041** — `eebb193` (test)
3. **Task 3: AD-040 spine + AD-042 reconciliation** — `09d046f` (test)

**Plan metadata:** (this commit)

## Accomplishments

- `fct_mmm_input.sql` pivots spend via `var('channel_taxonomy')`, inner-joins outcome/promo/calendar, zero-fills missing media.
- Schema YAML: `contract: {enforced: true}`, unique grain, not_null, `promo_flag` accepted_values.
- AD-040 anti-join against `stg_calendar_weekly` (D-15 seed-derived spine). AD-041 spend ≥ 0 / revenue > 0. AD-042 mart vs CSV sums within 1e-6 for P-SA/P-SB/P-SC.

## Deviations from Plan

**1. [Process] 2A copy** from m0 `9d75549` / `739d3b5` / `8f4fdca`. Contract red-then-green proofs recorded on m0.

**2. [Process] 4B** one PR per plan.

## Issues Encountered

None. `make lint && make test` — **293 passed**, 93% coverage.

## Next Phase Readiness

Next: **03-05** (`dim_layer` + `channels_present`).

---
*Phase: 03-warehouse*
*Completed: 2026-09-02*

## Self-Check: PASSED

Hashes `57938ae`, `eebb193`, `09d046f` are on `cursor/fct-mmm-input-9588`.
