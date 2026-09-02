---
phase: 02-ground-truth-simulator
plan: 02
subsystem: simulate
tags: [pydantic, validation, scenario-config, spec-01, simulation-error]

# Dependency graph
requires:
  - phase: 01-repository-foundation
    provides: "ambo.common.config.load_settings()/repo_root(), ambo.common.errors.AmboError, docs/MODULE_CONTRACTS.md contract-first convention (D-23), test_repo_layout.py/test_import_independence.py guards"
provides:
  - "SimulationError(AmboError) — the src/ambo/simulate/ package error root"
  - "ScenarioConfig model tree (TrueParams, SpendPattern, PlatformBiasParams, ChannelConfig, SeasonWeights, ScenarioConfig) with six validators covering SPEC-01 sections 3-6"
  - "load_scenario(name) -> ScenarioConfig, cached, boundary-converts to SimulationError"
  - "covered_iso_years()/covered_week_count() read-only helpers for later simulate/ modules"
affects: [02-03-scenario-yaml-authoring, 02-04-spend-patterns, 02-05-dgp, 02-06-dgp-gates, 02-08-truth]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic model tree with extra='forbid', frozen=True on every model, field_validator for single-field domain checks, model_validator(mode='after') for cross-field/cross-model invariants, all mirroring src/ambo/common/config.py's shape"
    - "ValueError inside field_validator/model_validator (pydantic idiom) converted to a typed SimulationError only at the module boundary (load_scenario()), never raised as a bare built-in past that boundary"
    - "Test-file deep-merge override pattern (_deep_merge over a fresh base-dict builder) so every negative test isolates exactly one deviation from a minimal valid payload"

key-files:
  created:
    - src/ambo/simulate/config.py
    - tests/unit/test_scenario_config.py
  modified:
    - src/ambo/common/errors.py
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "SimulationError promoted over 03_MODULES.md section 2.2/2.3's ValueError reading — recorded as a BUILD_LOG interpretation at M1 close, per the plan's own instruction"
  - "Exactly-adjacent bursts (next_start == prev_start + burst_length) accepted as two distinct bursts, never merged — second BUILD_LOG interpretation"
  - "Copied from m0-bootstrap 29f3050 / 746e570 (2A); lockfile not copied"

patterns-established:
  - "Pattern: simulate/ modules raise SimulationError only at their own module boundary, converting ValidationError/KeyError/FileNotFoundError there — internal field_validator/model_validator code keeps using plain ValueError, which is the pydantic idiom, not a violation of the typed-exception rule"

requirements-completed: [REQ-q1-truth-recovery, REQ-grain-and-windows]

# Metrics
duration: 15min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 02: ScenarioConfig Model Tree Summary

**Pydantic `ScenarioConfig` model tree (six nested models, six cross-field validators) that makes SPEC-01's scenario YAML schema mechanically checkable, plus `SimulationError` and its `docs/MODULE_CONTRACTS.md` entries.**

## Performance

- **Duration:** ~15 min on this lineage (2A copy of verified m0 artifacts)
- **Completed:** 2026-09-02
- **Tasks:** 2 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `src/ambo/simulate/config.py`: `TrueParams`, `SpendPattern`, `PlatformBiasParams`, `ChannelConfig`, `SeasonWeights`, `ScenarioConfig` — every model `extra='forbid'`/`frozen=True`.
- Six SPEC-01 invariants at load time: channel order, `{156,104,78}` weeks, pinned `(id, weeks, seed)`, S-C zero-effect `display_video`, schedule-window membership, burst non-overlap with adjacency accepted.
- `SimulationError(AmboError)` as the simulate-package error root; `load_scenario()` converts `KeyError`/`FileNotFoundError`/`ValidationError` at the boundary.
- `tests/unit/test_scenario_config.py`: 26 tests; every `pytest.raises` has `match=`.
- Two `docs/MODULE_CONTRACTS.md` edits in the same commit as the module (D-23).

## Task Commits

1. **Task 1** - `f711b66` (feat) — copied from m0 `29f3050`
2. **Task 2** - `6216ac4` (test) — copied from m0 `746e570`

**Plan metadata:** (this commit)

## Files Created/Modified

- `src/ambo/simulate/config.py`
- `src/ambo/common/errors.py` — `SimulationError` added
- `docs/MODULE_CONTRACTS.md`
- `tests/unit/test_scenario_config.py`

## Decisions Made

- `SimulationError` supersedes `03_MODULES.md` §2.2/§2.3's `ValueError` (BUILD_LOG interpretation at M1 close).
- Exactly-adjacent bursts are two distinct bursts, never merged (second BUILD_LOG interpretation).
- `functools.cache` rather than `lru_cache(maxsize=None)` (ruff UP033) — already in the copied source.
- `requirements.mark-complete` not invoked for REQ-q1 / REQ-grain-and-windows (contributing only).

## Deviations from Plan

**1. [Process] Copied from `origin/m0-bootstrap` (2A)** rather than rewriting. m0's four auto-fixes (UP033, F401/B905, `_base_scenario_dict`, `-k adjacency` rename) are already in the copied files.

**2. [Process] One PR per plan (4B).**

**Total deviations:** 2 process. No scope creep.

## Issues Encountered

None on this lineage. `make lint && make test` — 99 passed.

## User Setup Required

None.

## Next Phase Readiness

Plan 02-03 can author `config/scenarios/{s_a,s_b,s_c}.yaml` against this schema.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: src/ambo/simulate/config.py
- FOUND: tests/unit/test_scenario_config.py
- FOUND commit: f711b66
- FOUND commit: 6216ac4
