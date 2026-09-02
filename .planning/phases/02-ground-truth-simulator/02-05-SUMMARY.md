---
phase: 02-ground-truth-simulator
plan: 05
subsystem: simulate
tags: [spend-patterns, sim-030, sim-031]

requires:
  - phase: 02-ground-truth-simulator (plans 02-03, 02-04)
    provides: "ScenarioConfig YAMLs, week_index, round_half_up"
provides:
  - "simulate/spend_patterns.py generate_spend"
  - "tests/unit/test_spend_patterns.py SIM-030/031"
affects: [02-06-assemble]

key-files:
  created:
    - src/ambo/simulate/spend_patterns.py
    - tests/unit/test_spend_patterns.py
  modified:
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "Copied from m0-bootstrap c080b25 / 8588ca4 (2A)"

requirements-completed: [REQ-q1-truth-recovery, REQ-grain-and-windows]
duration: 15min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 05: Spend Patterns Summary

**`generate_spend` implements SIM-030/031 spend series with determinism and draw-order tests.**

## Task Commits

1. **Task 1** — `4831cc8` `generate_spend` + contract (from m0 `c080b25`)
2. **Task 2** — `04feb95` SIM-030/031 tests (from m0 `8588ca4`)

**Plan metadata:** (this commit)

## Accomplishments

- 26 tests in `test_spend_patterns.py`.
- `make lint && make test` — **186 passed**.

## Deviations from Plan

**1. [Process] 2A copy.** **2. [Process] 4B.**

REQ-q1 / REQ-grain-and-windows not marked complete in REQUIREMENTS.md.

## Next Phase Readiness

02-06 `assemble_scenario` and SIM-071/072/073 audits.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*
