---
phase: 02-ground-truth-simulator
plan: 04
subsystem: simulate
tags: [dgp, adstock, hill, seasonality, hypothesis]

requires:
  - phase: 02-ground-truth-simulator (plans 02-01, 02-03)
    provides: "hypothesis, ScenarioConfig, season_windows.csv, scenario YAMLs"
provides:
  - "simulate/dgp.py week_index, season_index, baseline_demand, adstock_recursive, hill, round_half_up"
  - "tests/unit/test_dgp.py SIM-073/074 point tests plus D-03 property tests"
affects: [02-05-spend-patterns, 02-06-assemble]

key-files:
  created:
    - src/ambo/simulate/dgp.py
    - tests/unit/test_dgp.py
  modified:
    - docs/MODULE_CONTRACTS.md
    - pyproject.toml

key-decisions:
  - "Copied from m0-bootstrap 3aa18c9 / 9817b3a / 5780c3f (2A)"
  - "pandas.* mypy override, no pandas-stubs (EB-030 / yaml precedent)"
  - "Impulse test before closed-form limit (02-RESEARCH Pitfall 4)"
  - "season_index signature promotion over 03_MODULES.md §2.3 — BUILD_LOG at M1"

requirements-completed: [REQ-q1-truth-recovery, REQ-grain-and-windows]
duration: 20min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 04: DGP Core Summary

**Week spine, seasonality, baseline demand, and simulator-owned adstock/Hill (SIM-003 independence).**

## Task Commits

1. **Task 1** — `f44b87e` week spine / season / baseline / rounding + pandas mypy override (from m0 `3aa18c9`)
2. **Task 2** — `dfb4b07` adstock + Hill, impulse before closed-form (from m0 `9817b3a`)
3. **Task 3** — `acef526` D-03 Hypothesis invariants (from m0 `5780c3f`)

**Plan metadata:** (this commit)

## Accomplishments

- `week_index` reads `dbt/seeds/season_windows.csv` only (AD-020).
- `adstock_recursive` causal; closed-form limit; `hill(K,K,s)==0.5`.
- 51 tests in `test_dgp.py`. `make lint && make test` — **160 passed**.

## Deviations from Plan

**1. [Process] 2A copy.** Did not copy m0 `deferred-items.md` (this lineage already formatted the planning docs in 02-01).
**2. [Process] 4B.**
**3. [Observed] NumPy DeprecationWarning** on `pd.Timedelta(days=7)` vs generic timedelta unit — present in copied `dgp.py`; not fixed here (would be an unplanned edit to copied science). Record for a later plan if it becomes an error.

REQ-q1 / REQ-grain-and-windows not marked complete in REQUIREMENTS.md.

## Next Phase Readiness

02-05 `generate_spend`.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*
