---
phase: 03-warehouse
plan: 06
subsystem: database
tags: [dbt, fct-platform-reported, ad-044, layer-r-fixture]

duration: 20min
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 6: fct_platform_reported, dormant AD-044, Layer R fixture Summary

**Third contract-enforced mart (`fct_platform_reported`), AD-044 compiled but inert under the default flags, and a disclosed fake Layer R fixture that actually executes the `layer_r_present` branch once (D-20).**

## Task Commits

1. **Task 1: fct_platform_reported** — `691563f` (feat)
2. **Task 2: dormant AD-044** — `a268b74` (test)
3. **Task 3: D-20 fake fixture run** — `16b5ddf` (test)

**Plan metadata:** (this commit)

## Accomplishments

- Grain week × layer × channel; six columns from `stg_media_weekly`; offline-channel NULLs survive.
- AD-044 gated on `intake_manifest_present` (independent of `layer_r_present`) so this plan's fixture can run without a Phase-6 seed.
- Fake fixture under `tests/fixtures/real_anon_fake/` — obviously fabricated (A-4/A-5); leak-scanned like every other tracked file.

## Deviations from Plan

**1. [Process] 2A copy** from m0 `055396f` / `55ba37a` / `6ead118`.

**2. [Process] 4B** one PR per plan.

## Issues Encountered

None. `make lint && make test` — **297 passed**, 93% coverage.

## Next Phase Readiness

Next: **03-07** (`ambo.common.db` accessors).

---
*Phase: 03-warehouse*
*Completed: 2026-09-02*

## Self-Check: PASSED
