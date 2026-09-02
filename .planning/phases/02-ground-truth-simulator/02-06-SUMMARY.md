---
phase: 02-ground-truth-simulator
plan: 06
subsystem: simulate
tags: [assemble, sim-071, sim-072, sim-073]

requires:
  - phase: 02-ground-truth-simulator (plans 02-04, 02-05)
    provides: "dgp primitives, generate_spend"
provides:
  - "SimulationResult, assemble_scenario, decomposition/plausibility/peak-week audits"
affects: [02-07-platform-bias, 02-08-truth, 02-09-cli]

key-files:
  modified:
    - src/ambo/simulate/dgp.py
    - tests/unit/test_dgp.py
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "Copied from m0-bootstrap acaf4bd / b5f51ce (2A)"

requirements-completed: [REQ-q1-truth-recovery]
duration: 15min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 06: Revenue Assembly Summary

**`assemble_scenario` plus SIM-071/072/073 audits.**

## Task Commits

1. **Task 1** — `bb171ac` SimulationResult + assemble_scenario (from m0 `acaf4bd`)
2. **Task 2** — `ca379d8` audit tests (from m0 `b5f51ce`)

**Plan metadata:** (this commit)

`make lint && make test` — **215 passed**.

## Deviations from Plan

**1. [Process] 2A copy.** **2. [Process] 4B.**

## Next Phase Readiness

02-07 `platform_report`.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*
