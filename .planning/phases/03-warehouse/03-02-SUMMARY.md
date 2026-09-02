---
phase: 03-warehouse
plan: 02
subsystem: testing
tags: [ast-guard, exception-hierarchy, architectural-guard, ad-030, pytest]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: the AmboError typed-exception root, and the four-guard AST-walk idiom (test_forbidden_deps.py, test_import_independence.py, test_repo_layout.py) this plan's fifth guard mirrors
provides:
  - "DataContractError(AmboError) — the exception class plan 03-07's db.py will raise"
  - "tests/unit/test_mart_only_access.py — the fifth standing architectural guard (D-09), enforcing AD-030's mart-only rule for the life of the project"
affects: [03-07-db-accessor, 04-model (any plan writing src/ambo/model/), 08-decide (src/ambo/decide/), 09-report (src/ambo/report/)]

# Tech tracking
tech-stack:
  added: []
  patterns: [ast-walk-collect-all-offenders-guard, vacuous-scan-non-vacuity-proof]

key-files:
  created: [tests/unit/test_mart_only_access.py]
  modified: [src/ambo/common/errors.py, docs/MODULE_CONTRACTS.md]

key-decisions:
  - "DataContractError docstring restates the AmboError redaction invariant explicitly, matching SimulationError's precedent, even though no warehouse input is private today"
  - "_forbidden_calls() and _forbidden_path_literals() are the only two detector helpers (plus _py_files); test_only_db_module_opens_duckdb's bare-import check is inlined in the test body rather than promoted to a fourth module-level helper"
  - "_FORBIDDEN_DATA_PATH_PREFIXES deliberately excludes exports/ — report/ has 03_MODULES section 10-granted legitimate access to it"

patterns-established:
  - "Guard-test idiom (AST walk, collect-all-offenders into a list, one joined assertion message, trailing scan-count print, vacuous-scan guard) extended to a fifth standing test"

requirements-completed: []  # REQ-dl1-reproducible-pipeline is Phase-9-owned; this plan contributes only

coverage:
  - id: D1
    description: "DataContractError exists as a third AmboError subclass in src/ambo/common/errors.py, importable and documented"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: unit
        ref: "uv run python -c \"from ambo.common.errors import AmboError, DataContractError\""
        status: pass
      - kind: unit
        ref: "tests/unit/test_repo_layout.py::test_module_contracts_match_src_ambo_modules_exactly"
        status: pass
    human_judgment: false
  - id: D2
    description: "The fifth standing architectural guard (D-09) enforces AD-030's mart-only rule and is non-vacuous"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: unit
        ref: "tests/unit/test_mart_only_access.py"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-09-02
status: complete
---

# Phase 03 Plan 02: DataContractError + the mart-only architectural guard (D-09) Summary

**Added `DataContractError(AmboError)` and the fifth standing architectural guard test — an AST-walk that fails the build the moment `model/`, `decide/`, or `report/` code reaches around `ambo.common.db` for data.**

## Performance

- **Duration:** ~15 min on this lineage (2A copy)
- **Completed:** 2026-09-02
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `DataContractError` is the third `AmboError` subclass, named as `ambo.common.db`'s raiser (03_MODULES §1.3), unblocking plan 03-07.
- `docs/MODULE_CONTRACTS.md`'s `errors.py` entry extended (D-23 contract-first).
- `tests/unit/test_mart_only_access.py` — fifth standing guard, converting AD-030 from a one-time grep into a permanent CI check.
- Guard is non-vacuous: `test_guard_detects_a_known_offender` fires all three detector shapes against synthetic offenders.

## Task Commits

1. **Task 1: Add DataContractError to the typed exception hierarchy and its contract entry** — `2f035e8` (feat)
2. **Task 2: The fifth standing architectural guard — the mart-only rule (D-09)** — `ca06b4b` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `src/ambo/common/errors.py` — `class DataContractError(AmboError)`
- `docs/MODULE_CONTRACTS.md` — Public API + Failure modes for `DataContractError`
- `tests/unit/test_mart_only_access.py` — four tests, two detector helpers

## Decisions Made

Copied from m0 `c36ff85` / `6579734` (2A). Redaction invariant restated on `DataContractError`. `exports/` excluded from forbidden prefixes.

## Deviations from Plan

**1. [Process] 2A copy** of science from `m0-bootstrap`. Red-then-green proofs were recorded on m0 (SUMMARY `5e1bec9`); not re-run as live probes here.

**2. [Process] 4B** one PR per plan.

**Total deviations:** 2 process. No scope creep.

## Issues Encountered

None. `make lint && make test` — **289 passed**, 93% coverage.

## Next Phase Readiness

- `DataContractError` exists and is documented — 03-07 can raise it.
- The mart-only guard is standing for Phase 4/8/9.
- Next plan: **03-03** (staging layer + poisoned-fixture proof).

---
*Phase: 03-warehouse*
*Completed: 2026-09-02*

## Self-Check: PASSED

Files on disk; hashes `2f035e8` and `ca06b4b` are on `cursor/mart-only-guard-9588`.
