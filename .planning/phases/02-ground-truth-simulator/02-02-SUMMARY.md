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
  - "Window-membership checks compare (iso_year, iso_week) tuples directly (per the plan's own action step), which only bounds the first/last covered year precisely; a mid-window year's out-of-range week number would not be caught by this check alone — accepted as specified, not a deviation"
  - "requirements.mark-complete NOT invoked for REQ-q1-truth-recovery/REQ-grain-and-windows — 02-01's SUMMARY already demonstrated it prematurely marks Phase-5/6-owned requirements complete from a contributing phase; those requirements stay Pending in REQUIREMENTS.md until their owning phase lands"

patterns-established:
  - "Pattern: simulate/ modules raise SimulationError only at their own module boundary, converting ValidationError/KeyError/FileNotFoundError there — internal field_validator/model_validator code keeps using plain ValueError, which is the pydantic idiom, not a violation of the typed-exception rule"

requirements-completed: [REQ-q1-truth-recovery, REQ-grain-and-windows]

# Metrics
duration: 20min
completed: 2026-08-05
status: complete
---

# Phase 02 Plan 02: ScenarioConfig Model Tree Summary

**Pydantic `ScenarioConfig` model tree (six nested models, six cross-field validators) that makes SPEC-01's scenario YAML schema mechanically checkable, plus `SimulationError` and its `docs/MODULE_CONTRACTS.md` entries.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-05T09:26:37Z
- **Completed:** 2026-08-05T09:43:05Z
- **Tasks:** 2 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `src/ambo/simulate/config.py`: `TrueParams`, `SpendPattern`, `PlatformBiasParams`, `ChannelConfig`, `SeasonWeights`, `ScenarioConfig` — every model `extra='forbid'`/`frozen=True`, matching `common/config.py`'s established shape.
- `ScenarioConfig` enforces all six SPEC-01 invariants at load time: exact channel order/membership, the `{156,104,78}` weeks grain, the pinned `(id, weeks, seed)` triple, the S-C zero-effect `display_video` channel, schedule-window membership, and burst non-overlap with adjacency accepted.
- `SimulationError(AmboError)` added as the `src/ambo/simulate/` package's error root; `load_scenario()` converts every `KeyError`/`FileNotFoundError`/pydantic `ValidationError` into it at the module boundary.
- `tests/unit/test_scenario_config.py`: 26 collected tests (positive/negative pair per validator, single-home taxonomy guard, frozen-model assertion, `load_scenario()` boundary-conversion tests), every `pytest.raises` carrying a `match=`.
- Two `docs/MODULE_CONTRACTS.md` edits landed in the same commit as the module (D-23): extended `errors.py`'s entry, new `simulate/config.py` entry.

## Task Commits

Each task was committed atomically:

1. **Task 1: SimulationError, the ScenarioConfig model tree, and their module contracts** - `29f3050` (feat)
2. **Task 2: Structural validation tests for ScenarioConfig** - `746e570` (test)

**Plan metadata:** (this commit, following)

## Files Created/Modified

- `src/ambo/simulate/config.py` - `SPEC_CHANNEL_ORDER`, the six nested models, `load_scenario()`, `covered_iso_years()`/`covered_week_count()`
- `src/ambo/common/errors.py` - `SimulationError(AmboError)` added, `AmboError`/`ConfigError` untouched
- `docs/MODULE_CONTRACTS.md` - `errors.py` entry extended; new `simulate/config.py` entry (five labelled sections)
- `tests/unit/test_scenario_config.py` - 26 tests covering every validator, the taxonomy single-home guard, and `load_scenario()`'s boundary conversion

## Decisions Made

- `SimulationError` supersedes `03_MODULES.md` section 2.2/2.3's `ValueError` reading (recorded here for `docs/BUILD_LOG.md` at M1 close, per the plan's `<output>` instruction).
- Exactly-adjacent bursts are accepted as two distinct bursts, never merged (second BUILD_LOG interpretation, per the plan's `<output>` instruction).
- `functools.cache` used instead of the plan text's literal `functools.lru_cache(maxsize=None)` — behaviorally identical (an unbounded cache), required by the repo's `ruff` `UP033` rule (`make lint`'s `ruff check` blocks on the old spelling). Not treated as a plan deviation requiring escalation — it is the same caching semantics via the modern spelling ruff itself recommends.
- `requirements.mark-complete` was not invoked for either `REQ-q1-truth-recovery` or `REQ-grain-and-windows`. Both requirements are Phase-5/Phase-6-owned per `.planning/REQUIREMENTS.md`'s traceability table, with Phase 2 listed only as a contributing phase. Plan 02-01's SUMMARY already discovered and documented that calling `mark-complete` here would prematurely flip the checkbox and traceability status to "Complete" and then require a same-session revert; skipping the call entirely avoids that no-op round trip. `requirements-completed:` in this SUMMARY's frontmatter still lists both IDs, copied verbatim from the plan's own `requirements:` field, per the template's contract (records contribution, not completion).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `functools.lru_cache(maxsize=None)` replaced with `functools.cache`**
- **Found during:** Task 1 verification (`make lint` / `ruff check .`)
- **Issue:** Ruff's `UP033` rule (part of the project's selected `UP` rule set) flags `@functools.lru_cache(maxsize=None)` and requires the equivalent `@functools.cache` spelling. `make lint` failed with this as a fixable error.
- **Fix:** Changed the decorator on `load_scenario()` to `@functools.cache`; behavior is identical (unbounded memoization keyed on `name`).
- **Files modified:** `src/ambo/simulate/config.py`
- **Verification:** `uv run ruff check .` → "All checks passed!"; `uv run mypy` → "Success: no issues found in 12 source files"
- **Committed in:** `29f3050` (Task 1 commit)

**2. [Rule 3 - Blocking] Unused `pathlib.Path` import removed; `zip()` given explicit `strict=False`**
- **Found during:** Task 1 verification (`make lint` / `ruff check .`)
- **Issue:** `ruff check .` flagged `F401` (unused `Path` import, superseded once `repo_root()`'s return type no longer needed a local annotation) and `B905` (`zip()` without an explicit `strict=` parameter in `_validate_bursts_do_not_overlap`, where the two sequences being zipped are deliberately different lengths by one — `ordered` and `ordered[1:]` — so `strict=True` would always raise).
- **Fix:** Removed the unused import; added `strict=False` to the `zip()` call.
- **Files modified:** `src/ambo/simulate/config.py`
- **Verification:** `uv run ruff check .` → "All checks passed!"
- **Committed in:** `29f3050` (Task 1 commit)

**3. [Rule 1 - Bug] Test helper's `_deep_merge`-based scenario builders needed per-scenario base construction, not deep-merge-over-a-shared-base**
- **Found during:** Task 2, writing `_valid_s_b_dict`/`_valid_s_c_dict`
- **Issue:** An initial implementation built `_valid_s_b_dict()`/`_valid_s_c_dict()` by deep-merging window/identity changes onto `_base_s_a_dict()`'s output. `_deep_merge` only adds/overrides dict keys, never deletes one — so `_base_s_a_dict()`'s `promo_weeks={2021:.., 2022:.., 2023:..}` and its burst years anchored to 2021 survived the merge for s_b/s_c, leaving stale entries outside the new scenario's window and failing `test_valid_scenario_identity_constructs[s_b]` with a real `ValidationError` (`promo_weeks year 2023 is outside the declared window [2021..2022]`).
- **Fix:** Refactored to a single parameterized `_base_scenario_dict(*, scenario_id, weeks, seed, ..., burst_year, display_video_beta)` builder that every one of `_valid_scenario_dict`/`_valid_s_b_dict`/`_valid_s_c_dict` calls fresh with its own window/promo_weeks/burst_year/beta — no scenario's base payload is ever built by deep-merging onto a different scenario's base.
- **Files modified:** `tests/unit/test_scenario_config.py`
- **Verification:** `uv run pytest tests/unit/test_scenario_config.py -v` → 26 passed (including all three `test_valid_scenario_identity_constructs` parametrizations)
- **Committed in:** `746e570` (Task 2 commit, discovered and fixed before that commit)

**4. [Rule 1 - Bug] Adjacency test renamed so `pytest -k adjacency` selects it**
- **Found during:** Task 2 acceptance-criteria verification
- **Issue:** The plan's acceptance criteria require `uv run pytest tests/unit/test_scenario_config.py -k adjacency -x` to collect at least 1 test. The initial test name `test_adjacent_bursts_are_two_distinct_bursts` contains "adjacent", not the substring "adjacency", so `-k adjacency` matched zero tests.
- **Fix:** Renamed to `test_burst_adjacency_is_accepted_as_two_distinct_bursts`.
- **Files modified:** `tests/unit/test_scenario_config.py`
- **Verification:** `uv run pytest tests/unit/test_scenario_config.py -k adjacency -v` → "1 passed, 25 deselected"
- **Committed in:** `746e570` (Task 2 commit, discovered and fixed before that commit)

---

**Total deviations:** 4 auto-fixed (2 blocking/lint, 2 bugs in test helper code — none in `src/ambo/simulate/config.py`'s actual validation logic)
**Impact on plan:** All four were caught and fixed before their respective task commits landed, so no follow-up commit was needed. No scope creep — every fix stayed inside this plan's two `files_modified` source files plus the test file.

## Issues Encountered

None beyond the four auto-fixed items above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 02-03 can now author `config/scenarios/{s_a,s_b,s_c}.yaml` against a schema that rejects every SPEC-01 sections 3-6 violation this plan's `must_haves.truths` list enumerates. `docs/MODULE_CONTRACTS.md` and all four Phase 1 architectural guards (`test_repo_layout.py`, `test_import_independence.py`, `test_forbidden_deps.py`, `uv run mypy` strict) remain green.

**Known pre-existing, out-of-scope item (unchanged from 02-01):** `make lint`'s `ruff format --check .` step still fails on two markdown files (`02-PATTERNS.md`, `02-RESEARCH.md`) authored during Phase 2 planning, unrelated to this plan's `files_modified`. Logged in `.planning/phases/02-ground-truth-simulator/deferred-items.md`; `ruff check .` (lint proper) and `uv run mypy` both pass cleanly, and `make test` passes fully (99 passed).

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: src/ambo/simulate/config.py
- FOUND: tests/unit/test_scenario_config.py
- FOUND: src/ambo/common/errors.py (modified)
- FOUND: docs/MODULE_CONTRACTS.md (modified)
- FOUND commit: 29f3050
- FOUND commit: 746e570
