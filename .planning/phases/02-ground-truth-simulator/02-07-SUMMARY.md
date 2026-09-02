---
phase: 02-ground-truth-simulator
plan: 07
subsystem: simulate
tags: [platform-bias, sim-060, sim-061]

requires:
  - phase: 02-ground-truth-simulator (plan 02-06)
    provides: "SimulationResult, assemble_scenario"
provides:
  - "simulate/platform_bias.py platform_report"
affects: [02-09-cli]

key-files:
  created:
    - src/ambo/simulate/platform_bias.py
    - tests/unit/test_platform_bias.py
  modified:
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "Copied from m0-bootstrap 4b8e2cc / a42f8a6 (2A)"
  - "Platform conversions are the object of study, never a calibration target (T-8)"

requirements-completed: [REQ-q1-truth-recovery]
duration: 12min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 07: Platform Reporting Bias Summary

**`platform_report` implements SIM-060/061 simulated platform over-credit.**

## Task Commits

1. **Task 1** — `cc01abf` `platform_report` + contract (from m0 `4b8e2cc`)
2. **Task 2** — `fc55709` SIM-060/061 tests (from m0 `a42f8a6`)

**Plan metadata:** (this commit)

`make lint && make test` — **235 passed**.

## Deviations from Plan

**1. [Process] 2A copy.** **2. [Process] 4B.**

## Next Phase Readiness

02-08 `truth.py`.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*
