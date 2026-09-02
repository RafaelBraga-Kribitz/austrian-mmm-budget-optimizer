---
phase: 02-ground-truth-simulator
plan: 09
subsystem: simulate
tags: [cli, make-simulate, sim-070]

requires:
  - phase: 02-ground-truth-simulator (plans 02-06, 02-07, 02-08)
    provides: "assemble_scenario, platform_report, write_truth"
provides:
  - "simulate/__main__.py CLI; Makefile simulate and validate-sim targets"
affects: [02-10-artifacts]

key-files:
  created:
    - src/ambo/simulate/__main__.py
    - tests/unit/test_simulate_cli.py
  modified:
    - Makefile
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "Copied from m0-bootstrap 964bcf8 / 27072fc (2A)"

requirements-completed: [REQ-q1-truth-recovery, REQ-dl1-reproducible-pipeline]
duration: 12min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 09: Simulator CLI Summary

**CLI + `make simulate`/`validate-sim` replace Phase 1 stubs. SIM-070 determinism tests.**

## Task Commits

1. **Task 1** — `816761e` CLI + Makefile (from m0 `964bcf8`)
2. **Task 2** — `aecdd7a` SIM-070 tests (from m0 `27072fc`)

**Plan metadata:** (this commit)

`make lint && make test` — **281 passed**.

## Deviations from Plan

**1. [Process] 2A copy.** **2. [Process] 4B.**

## Next Phase Readiness

02-10 commit synthetic artifacts + M1 BUILD_LOG.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*
