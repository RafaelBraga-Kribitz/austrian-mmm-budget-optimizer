---
phase: 02-ground-truth-simulator
plan: 03
subsystem: simulate
tags: [scenario-yaml, spec-01, bp-g-02, authoring-aid, spend-patterns]

requires:
  - phase: 02-ground-truth-simulator (plan 02)
    provides: "ScenarioConfig model tree, load_scenario(), SimulationError"
provides:
  - "config/scenarios/{s_a,s_b,s_c}.yaml — authoritative SPEC-01 parameter source (SIM-002)"
  - "scripts/author_scenario_schedules.py — D-02 promo/burst authoring aid"
  - "tests/unit/test_scenario_config.py extended with BP-G-02 tests"
affects: [02-04-spend-patterns, 02-05-dgp, 02-06-dgp-gates, 02-08-truth, 02-09-cli-gates]

key-files:
  created:
    - scripts/author_scenario_schedules.py
    - config/scenarios/s_a.yaml
    - config/scenarios/s_b.yaml
    - config/scenarios/s_c.yaml
  modified:
    - tests/unit/test_scenario_config.py

key-decisions:
  - "Copied from m0-bootstrap 9c268f1 / 320e8e2 / b15b51e (2A)"
  - "Spring promo anchors are the spring window's 1/3 and 2/3 index points (CONTEXT.md D-01)"
  - "Radio's 2 Advent-anchored bursts: lead-in (A-3) plus in-Advent (A) — BUILD_LOG at M1"
  - "meta.spend.advent_factor 0.5 (S-A) / 0.9 (S-B/S-C) per SIM-030 — BUILD_LOG at M1"
  - "Four online cpm values authored, not spec-given (BP-D-02) — BUILD_LOG at M1"

requirements-completed: [REQ-q1-truth-recovery, REQ-grain-and-windows]
duration: 20min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 03: Scenario YAML Authoring Summary

**Three SPEC-01 scenario YAMLs as the single authoritative parameter source, plus the D-02 placement aid and BP-G-02 equality tests.**

## Task Commits

1. **Task 1** — `e38d211` authoring aid (from m0 `9c268f1`)
2. **Task 2** — `b20b539` `config/scenarios/{s_a,s_b,s_c}.yaml` (from m0 `320e8e2`)
3. **Task 3** — `38fd1a7` BP-G-02 tests (from m0 `b15b51e`)

**Plan metadata:** (this commit)

## Accomplishments

- Authoring aid reads `dbt/seeds/season_windows.csv`, prints YAML fragments, is unreachable from `src/ambo/`.
- All three scenarios load through `load_scenario()`. S-C `display_video.beta=0.0`.
- 36 tests in `test_scenario_config.py`. `make lint && make test` — **109 passed**.

## Decisions Made (carry to BUILD_LOG at M1)

1. `SimulationError` still the simulate error root (from 02-02).
2. Adjacent bursts remain distinct (from 02-02).
3. Radio Advent bursts: lead-in + in-Advent.
4. `meta.advent_factor` follows SIM-030 (0.5 / 0.9).
5. Online `cpm` values are authored (BP-D-02 names none).

## Deviations from Plan

**1. [Process] 2A copy** from `origin/m0-bootstrap`.
**2. [Process] 4B** one PR per plan.

REQ-q1 / REQ-grain-and-windows not marked complete in REQUIREMENTS.md.

## Next Phase Readiness

02-04 can implement DGP against these YAMLs.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*
