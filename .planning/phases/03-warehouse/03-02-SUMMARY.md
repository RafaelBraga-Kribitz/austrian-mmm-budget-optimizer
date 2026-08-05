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
  - "_forbidden_calls() and _forbidden_path_literals() are the only two detector helpers (plus _py_files); test_only_db_module_opens_duckdb's bare-import check is inlined in the test body rather than promoted to a fourth module-level helper, keeping the symbol list to exactly what the plan's artifacts_this_phase_produces names"
  - "_FORBIDDEN_DATA_PATH_PREFIXES deliberately excludes exports/ — report/ has 03_MODULES section 10-granted legitimate access to it, verified by an explicit positive-control probe"

patterns-established:
  - "Guard-test idiom (AST walk, collect-all-offenders into a list, one joined assertion message, trailing scan-count print, vacuous-scan guard) extended to a fifth standing test — the same shape any future architectural guard should follow"

requirements-completed: []  # REQ-dl1-reproducible-pipeline is Phase-9-owned per REQUIREMENTS.md traceability; this plan contributes only (matches 02-02/02-09/03-01 precedent)

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
    description: "The fifth standing architectural guard (D-09) enforces AD-030's mart-only rule and is non-vacuous, proven against synthetic offenders in three shapes plus an exports/ positive control"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: unit
        ref: "tests/unit/test_mart_only_access.py::test_model_and_decide_never_read_data_files_directly"
        status: pass
      - kind: unit
        ref: "tests/unit/test_mart_only_access.py::test_only_db_module_opens_duckdb"
        status: pass
      - kind: unit
        ref: "tests/unit/test_mart_only_access.py::test_report_may_read_exports_but_no_other_data_directory"
        status: pass
      - kind: unit
        ref: "tests/unit/test_mart_only_access.py::test_guard_detects_a_known_offender"
        status: pass
    human_judgment: false

# Metrics
duration: 18min
completed: 2026-08-05
status: complete
---

# Phase 03 Plan 02: DataContractError + the mart-only architectural guard (D-09) Summary

**Added `DataContractError(AmboError)` and the fifth standing architectural guard test — an AST-walk that fails the build the moment `model/`, `decide/`, or `report/` code reaches around `ambo.common.db` for data.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-05T18:38:00Z
- **Completed:** 2026-08-05T18:56:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `DataContractError` is now the third `AmboError` subclass, named as `ambo.common.db`'s raiser (03_MODULES §1.3), unblocking plan 03-07
- `docs/MODULE_CONTRACTS.md`'s `errors.py` entry extended in the same PR (D-23 contract-first rule)
- `tests/unit/test_mart_only_access.py` — the fifth standing guard (joining Phase 1's four), converting AD-030's mart-only rule from a one-time grep into a permanent CI check
- Guard proven non-vacuous today, before `model/`, `decide/`, or `report/` exist for real: `test_guard_detects_a_known_offender` fires all three detector shapes against synthetic offenders
- All three offender shapes red-then-green proven live against the real package directories, plus an `exports/` positive control confirming `report/`'s legitimate access is not collateral damage

## Task Commits

Each task was committed atomically:

1. **Task 1: Add DataContractError to the typed exception hierarchy and its contract entry** - `c36ff85` (feat)
2. **Task 2: The fifth standing architectural guard — the mart-only rule (D-09)** - `6579734` (test)

**Plan metadata:** pending (docs: complete plan, committed after this SUMMARY)

## Files Created/Modified
- `src/ambo/common/errors.py` - Added `class DataContractError(AmboError)`, third subclass, naming `ambo.common.db` as raiser and restating the redaction invariant
- `docs/MODULE_CONTRACTS.md` - Extended the existing `src/ambo/common/errors.py` entry's `Public API` and `Failure modes` sections
- `tests/unit/test_mart_only_access.py` - New file: the fifth standing guard, four tests, two shared detector helpers (`_forbidden_calls`, `_forbidden_path_literals`) plus `_py_files`

## Decisions Made
- `DataContractError`'s docstring restates the `AmboError` redaction invariant explicitly (matching `SimulationError`'s precedent) even though warehouse data is Layer P and never private today — plan 03-06's fake Layer R fixture and Phase 6's real anonymized data mean the invariant must already be on record.
- Kept exactly three module-level symbols (`_py_files`, `_forbidden_calls`, `_forbidden_path_literals`) per the plan's `artifacts_this_phase_produces` list — `test_only_db_module_opens_duckdb`'s bare `import duckdb` / `from duckdb import ...` check is inlined directly in that test's body rather than promoted to a fourth helper, since `_forbidden_calls` only catches `ast.Call` nodes (a bare import statement has no `Call` node to match).
- `_FORBIDDEN_DATA_PATH_PREFIXES` deliberately excludes `exports/` — verified live with a positive-control probe (a `report/`-scoped file with an `exports/`-prefixed string literal does not trip the guard).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The whole-repo `ruff format --check .` failure on four `.planning/phases/{02,03}-*/{PATTERNS,RESEARCH}.md` files (pre-existing, logged by plan 03-01 in `deferred-items.md`) was re-confirmed as out of scope and not touched; `make lint`'s three commands were run scoped to `src tests scripts` instead of the whole-repo `make lint` target, matching 03-01's precedent, and all passed clean.

## Red-then-Green Proofs (plan-required evidence)

All four proofs performed live against this repository's real `src/ambo/model/`, `src/ambo/decide/`, and `src/ambo/report/` package stubs (each currently holding only an `__init__.py`), then reverted — no probe file was ever committed.

**1. CSV read call under `src/ambo/model/`** (`test_model_and_decide_never_read_data_files_directly`)
- Probe: `src/ambo/model/_scratch_probe.py` containing `df = pd.read_csv("data/synthetic/s_a/media_weekly.csv")`
- Red: `AssertionError: AD-030: model/ and decide/ code reaches data only through ambo.common.db, never a direct read call or a hardcoded data path -- offender(s): src/ambo/model/_scratch_probe.py:3: read_csv; src/ambo/model/_scratch_probe.py:3: 'data/synthetic/s_a/media_weekly.csv'`
- Green: probe deleted, `test_model_and_decide_never_read_data_files_directly` passes.

**2. `duckdb.connect` call under `src/ambo/decide/`** (`test_only_db_module_opens_duckdb`)
- Probe: `src/ambo/decide/_scratch_probe.py` containing `import duckdb` and `con = duckdb.connect("data/warehouse/ambo.duckdb")`
- Red: `AssertionError: AD-030: src/ambo/common/db.py is the single permitted home for opening a duckdb connection or importing duckdb -- offender(s): src/ambo/decide/_scratch_probe.py:3: duckdb.connect; src/ambo/decide/_scratch_probe.py:1: import duckdb`
- Green: probe deleted, `test_only_db_module_opens_duckdb` passes.

**3. `data/warehouse`-prefixed string literal under `src/ambo/report/`** (`test_report_may_read_exports_but_no_other_data_directory`)
- Probe: `src/ambo/report/_scratch_probe.py` containing `WAREHOUSE_PATH = "data/warehouse/ambo.duckdb"`
- Red: `AssertionError: AD-030: report/ may read only exports/, never a data/synthetic, data/real_anon, data/warehouse, or data/cache path directly -- offender(s): src/ambo/report/_scratch_probe.py:1: 'data/warehouse/ambo.duckdb'`
- Green: probe deleted, `test_report_may_read_exports_but_no_other_data_directory` passes.

**4. Positive control — `exports/`-prefixed literal under `src/ambo/report/`** (`test_report_may_read_exports_but_no_other_data_directory`)
- Probe: `src/ambo/report/_scratch_probe.py` containing `EXPORT_PATH = "exports/ssot/numeric_ssot.csv"`
- Result: test passed immediately (no offender reported) — `report/`'s legitimate `exports/` access is not collateral damage.
- Probe deleted after confirming pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `DataContractError` exists and is documented — plan 03-07 (`src/ambo/common/db.py`) can raise it as its sole error type without any further Phase 3 work.
- The mart-only guard is standing and will start catching real violations the moment Phase 4 (`model/`), Phase 8 (`decide/`), or Phase 9 (`report/`) writes its first module — no further action needed to activate it.
- No blockers for the remaining Phase 3 plans.

---
*Phase: 03-warehouse*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: src/ambo/common/errors.py
- FOUND: tests/unit/test_mart_only_access.py
- FOUND: docs/MODULE_CONTRACTS.md
- FOUND: c36ff85 (Task 1 commit)
- FOUND: 6579734 (Task 2 commit)
