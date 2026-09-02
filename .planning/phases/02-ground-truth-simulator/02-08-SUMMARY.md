---
phase: 02-ground-truth-simulator
plan: 08
subsystem: simulate
tags: [truth-file, sim-075, response-curve]

requires:
  - phase: 02-ground-truth-simulator (plans 02-03, 02-06)
    provides: "ScenarioConfig, assemble_scenario"
provides:
  - "simulate/truth.py TruthFile, response_curve_at, marginal_roas_at, compute_truth, write_truth"
affects: [02-09-cli, 02-10-artifacts]

key-files:
  created:
    - src/ambo/simulate/truth.py
    - tests/unit/test_truth.py
  modified:
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "Copied from m0-bootstrap e3e6ffc / af085e1 (2A)"
  - "response_curve_at takes a caller-supplied grid (WARNING 4)"

requirements-completed: [REQ-q1-truth-recovery]
duration: 12min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 08: Truth Files Summary

**`TruthFile` schema, closed-form curves, analytic marginal ROAS, byte-stable JSON.**

## Task Commits

1. **Task 1** — `6a85108` truth.py + contract (from m0 `e3e6ffc`)
2. **Task 2** — `5a3e225` SIM-075 tests (from m0 `af085e1`)

**Plan metadata:** (this commit)

`make lint && make test` — **267 passed**.

## Deviations from Plan

**1. [Process] 2A copy.** **2. [Process] 4B.**

## Next Phase Readiness

02-09 CLI and `make simulate`.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*
