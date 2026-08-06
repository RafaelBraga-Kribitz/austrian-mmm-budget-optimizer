---
phase: 03-warehouse
plan: 07
subsystem: database
tags: [duckdb, data-access, contract, ad-030, pytest]

# Dependency graph
requires:
  - phase: 03-warehouse (plan 02)
    provides: DataContractError(AmboError) and the mart-only architectural guard (D-09) this module is the subject of
  - phase: 03-warehouse (plan 04)
    provides: fct_mmm_input, the frozen 17-column contract-enforced mart this module's read_mmm_input derives its column set from
  - phase: 03-warehouse (plan 05)
    provides: dim_layer, the layer-grain dimension this module's unknown-layer check queries
  - phase: 03-warehouse (plan 06)
    provides: fct_platform_reported, the third contract-enforced mart this module's read_platform_reported reads
provides:
  - "src/ambo/common/db.py — the single AD-030 doorway: connect(read_only=True), read_mmm_input(layer), read_platform_reported(layer), read_dim_layer(), all deriving their column contracts from the dbt schema ymls at runtime (D-08) and collecting every postcondition violation into one DataContractError (D-10)"
  - "tests/unit/test_db.py — the round trip against committed simulator CSVs, shape/order pinning, offline-null preservation, the read-only write-rejection proof, and the collect-all-raise-once proof"
  - "docs/MODULE_CONTRACTS.md's src/ambo/common/db.py entry, citing the three mart schema ymls by path rather than restating their column lists"
affects: [03-08, 03-09, phase-4, phase-8, phase-9]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "config.py-analog module shape: module docstring naming the requirement (Implements: AD-030), functools.cache on the yml-derived constant, raise-DataContractError-naming-the-fix-command on a missing input"
    - "column projection and column-set check share one source (_contract_columns) so the SQL SELECT and the postcondition check cannot drift apart"
    - "collect-all-raise-once: a violations: list[str] accumulator, every check appended independently (not short-circuited on the first failure), one terminal raise joining the full list"
    - "fake-connection test double (duck-typed .execute()/.close()) to drive the real read_mmm_input() validation path against a synthetic poisoned frame, without a dedicated testable helper function and without touching the real warehouse"

key-files:
  created:
    - src/ambo/common/db.py
    - tests/unit/test_db.py
  modified:
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "Kept exactly the six module-level symbols the plan's artifacts_this_phase_produces list names (connect, read_mmm_input, read_platform_reported, read_dim_layer, _contract_columns, _check_columns) — no seventh _valid_layers helper; the distinct-layer query is inlined identically in both read_mmm_input and read_platform_reported, mirroring plan 03-02's precedent of not promoting an inlinable check to a new named symbol outside the plan's own list."
  - "test_all_postcondition_violations_are_reported_at_once drives the real production read_mmm_input() code path with a minimal duck-typed fake connection (matching only the .execute()/.close() surface it calls) rather than adding a dedicated testable validation helper to db.py — keeps the module's public/private surface exactly as specified while still proving D-10 against genuine application logic, not a reimplementation of it in the test."
  - "Split Tasks 1 and 2 into two commits against the same new file by writing an intermediate Task-1-only version of db.py (connect/_contract_columns/_check_columns), committing, then restoring the full file for Task 2's commit — same atomic-per-task discipline as a multi-file plan, applied to a single-file plan."

patterns-established:
  - "Contract-derived column set: a mart's expected columns are never restated as a literal in Python — _contract_columns() parses the dbt schema yml at runtime and both the SELECT projection and the postcondition check consume that one derivation (D-08's mechanism, now demonstrated end to end)."

requirements-completed: []  # REQ-q1-truth-recovery is Phase-5-owned (already Complete since Phase 2's M1 close); REQ-dl1-reproducible-pipeline is Phase-9-owned. This plan contributes to both without owning either, matching 03-01/03-02/03-04/03-06 precedent.

coverage:
  - id: D1
    description: "db.py exposes exactly four public functions (connect, read_mmm_input, read_platform_reported, read_dim_layer) plus the two private helpers the plan names (_contract_columns, _check_columns); connect() defaults to read_only=True and a write through it raises without mutating the warehouse"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: unit
        ref: "uv run python -c \"from ambo.common.db import connect; c = connect(); c.execute('select count(*) from fct_mmm_input').fetchone()\" — prints a tuple containing 338"
        status: pass
      - kind: unit
        ref: "tests/unit/test_db.py::test_read_only_connection_rejects_a_write"
        status: pass
    human_judgment: false
  - id: D2
    description: "_contract_columns derives each mart's column set from the dbt schema ymls at runtime — 17 for fct_mmm_input, 5 for dim_layer, 6 for fct_platform_reported — with no literal column list anywhere in db.py; an undeclared model name raises DataContractError naming the model and searched directory"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: unit
        ref: "uv run python -c \"from ambo.common.db import _contract_columns; assert len(_contract_columns('fct_mmm_input'))==17; assert len(_contract_columns('dim_layer'))==5\""
        status: pass
      - kind: unit
        ref: "tests/unit/test_db.py::test_read_mmm_input_shape_and_order"
        status: pass
    human_judgment: false
  - id: D3
    description: "read_mmm_input/read_platform_reported/read_dim_layer return contract-shaped, deterministically ordered frames (156/104/78 rows for P-SA/P-SB/P-SC, 936 platform rows for P-SA, 3x5 dim_layer); an unknown layer raises DataContractError listing the three valid layers; a frame violating two postconditions simultaneously raises one DataContractError naming both"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_db.py::test_read_mmm_input_totals_match_simulator_csvs (parametrized over P-SA/P-SB/P-SC)"
        status: pass
      - kind: unit
        ref: "tests/unit/test_db.py::test_unknown_layer_lists_valid_layers"
        status: pass
      - kind: unit
        ref: "tests/unit/test_db.py::test_all_postcondition_violations_are_reported_at_once"
        status: pass
      - kind: unit
        ref: "tests/unit/test_db.py::test_read_platform_reported_preserves_offline_nulls"
        status: pass
      - kind: unit
        ref: "tests/unit/test_db.py::test_read_dim_layer_shape"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/MODULE_CONTRACTS.md's src/ambo/common/db.py entry cites the three mart schema ymls by path and does not restate their column lists; tests/unit/test_repo_layout.py and tests/unit/test_mart_only_access.py both pass with db.py present"
    verification:
      - kind: unit
        ref: "uv run pytest tests/unit/test_db.py tests/unit/test_repo_layout.py tests/unit/test_mart_only_access.py -q (19 passed)"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-08-06
status: complete
---

# Phase 3 Plan 7: The AD-030 Data Doorway (`db.py`) Summary

**`src/ambo/common/db.py` — the single data doorway every downstream module reaches the warehouse through — built with a read-only-by-default connection, a mart column contract derived at runtime from the dbt schema ymls (never restated as a literal), and collect-all-raise-once postconditions on every accessor, so a broken build produces one exception listing everything wrong rather than the first thing found.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-08-06T10:35:00Z (approximate — session start)
- **Completed:** 2026-08-06T11:06:00Z (Task 3 commit)
- **Tasks:** 3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `connect(read_only: bool = True)` resolves the warehouse exclusively through `load_settings().paths.warehouse` (never a hard-coded path) and raises `DataContractError` naming the `make transform` command when the file is missing, rather than a raw duckdb IO error or a silently returned connection.
- `_contract_columns(model_name)` parses `dbt/models/marts/*.yml` at runtime (cached with `functools.cache`) and returns each mart's declared `(name, data_type)` pairs in declared order — 17 for `fct_mmm_input`, 5 for `dim_layer`, 6 for `fct_platform_reported` — with zero literal column lists anywhere in `db.py`. An undeclared model name raises `DataContractError` naming the model and the searched directory.
- `read_mmm_input(layer)`, `read_platform_reported(layer)`, and `read_dim_layer()` project exactly the contract-derived column set (SELECT and postcondition check share one source, so they cannot drift apart), and each accumulates every postcondition violation into a single `violations: list[str]` before raising exactly once with the full list (D-10) — never returning on the first failure.
- An unknown `layer` argument is resolved explicitly against `dim_layer`'s distinct layers before the main query runs, and raises `DataContractError` listing the valid layers rather than returning an empty frame.
- `read_platform_reported` deliberately asserts non-null only on the three grain columns (`week_start`, `layer`, `channel`) — `platform_conversions`, `platform_conv_value`, and `impressions` stay nullable, preserving the offline-channel distinction plan 03-06 established (AGENTS T-8).
- Every public function's docstring carries an `Implements: AD-030` marker (AGENTS W-1) and states its grain, ordering guarantee, and postconditions.
- `tests/unit/test_db.py` (12 tests): the round trip against the three committed simulator CSVs (revenue sums computed at test time, not hard-coded, within 1e-6), shape/column-order pinning, `fct_platform_reported`'s offline-NULL preservation, `dim_layer`'s taxonomy-ordered `channels_present`, the missing-warehouse message, the unknown-layer message, the read-only write-rejection proof (with a follow-up query confirming the warehouse is genuinely unmodified), and the collect-all-raise-once proof — a synthetic frame with a non-ascending `week_start` *and* a NaN in `spend_meta` simultaneously, driven through the real `read_mmm_input()` validation logic via a minimal fake connection, produces one `DataContractError` naming both violations.
- `docs/MODULE_CONTRACTS.md` gained a `### src/ambo/common/db.py` entry (inserted alphabetically between `config.py` and `errors.py`) citing the three mart schema ymls by path — no mart's column list is copied into the document, the same repoint D-08 requires.

## Task Commits

Each task was committed atomically:

1. **Task 1: connect() and the contract-derived column set** — `ffe6f41` (feat)
2. **Task 2: The three accessors with collect-all-raise-once postconditions** — `3149e36` (feat)
3. **Task 3: test_db.py and the MODULE_CONTRACTS entry** — `5c204cb` (test)

**Plan metadata:** pending (docs: complete plan, committed after this SUMMARY)

## Files Created/Modified

- `src/ambo/common/db.py` — the AD-030 doorway: `connect`, `read_mmm_input`, `read_platform_reported`, `read_dim_layer`, `_contract_columns`, `_check_columns`
- `tests/unit/test_db.py` — 12 tests covering the round trip and every named failure mode
- `docs/MODULE_CONTRACTS.md` — new `src/ambo/common/db.py` entry citing the mart schema ymls by path

## Decisions Made

- Kept exactly the six module-level symbols the plan's `artifacts_this_phase_produces` list names. The distinct-layer lookup (`select distinct layer from dim_layer`) is inlined identically in both `read_mmm_input` and `read_platform_reported` rather than factored into a seventh `_valid_layers` helper — matching plan 03-02's established precedent of not promoting an inlinable check to a new named symbol outside the plan's own artifact list.
- `test_all_postcondition_violations_are_reported_at_once` drives the real production `read_mmm_input()` code path through a minimal duck-typed fake connection (only `.execute()`/`.close()`, matching exactly what the function calls) rather than adding a dedicated testable validation helper to `db.py`. This proves D-10 against genuine application logic — not a reimplementation of it in the test — while keeping the module's public/private surface exactly as the plan specifies.
- Split Task 1 and Task 2 into two atomic commits against the same new file by writing an intermediate Task-1-only version of `db.py` (module docstring, `connect`, `_contract_columns`, `_check_columns`), verifying and committing it, then restoring the full file (adding the three accessors) for Task 2's commit — preserving per-task commit discipline even though both tasks share one file.

## Deviations from Plan

None — plan executed exactly as written. The MODULE_CONTRACTS.md guard test (`test_module_contracts_match_src_ambo_modules_exactly`) and the mart-only guard (`test_mart_only_access.py`) are both green with `db.py` now present; neither required any adjustment.

## Issues Encountered

None. `uv run ruff format` needed one pass to reformat two multi-line expressions in `db.py` and one in `test_db.py` after initial authoring — routine formatting, not a logic change, applied before either commit.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The AD-030 doorway is complete: `model` (Phase 4), `decide` (Phase 8), and `report` (Phase 9) code has exactly one way to reach the warehouse, with the mart-only guard test (plan 03-02) now enforcing it against a real file instead of an empty scan.
- `read_mmm_input(layer)` is ready as Phase 4's sole model-input entry point; `dim_layer.channels_present` (plan 03-05) and `read_mmm_input`'s zero-filled `spend_*` columns are consistent by construction (both trace to the same `fct_mmm_input` mart).
- `uv run dbt build --project-dir dbt --profiles-dir dbt` is unaffected by this plan (green, 72 PASS / 0 ERROR, unchanged from plan 03-06).
- `uv run pytest tests/unit/test_db.py tests/unit/test_repo_layout.py tests/unit/test_mart_only_access.py -q` is green (19 passed).
- `uv run pytest -q` (full suite) is green with no failures.
- `uv run ruff check .`, `uv run mypy`, and `uv run ruff format --check src tests scripts` are all clean. The whole-repo `ruff format --check .` still fails on the same 4 pre-existing `.planning/phases/{02,03}-*/{PATTERNS,RESEARCH}.md` files logged in `deferred-items.md` since plan 03-01 — untouched by this plan's three tasks, confirmed out of scope again this session.
- No blockers for plan 03-08.

---
*Phase: 03-warehouse*
*Completed: 2026-08-06*

## Self-Check: PASSED

- FOUND: src/ambo/common/db.py
- FOUND: tests/unit/test_db.py
- FOUND: docs/MODULE_CONTRACTS.md
- FOUND: ffe6f41 (Task 1 commit)
- FOUND: 3149e36 (Task 2 commit)
- FOUND: 5c204cb (Task 3 commit)
