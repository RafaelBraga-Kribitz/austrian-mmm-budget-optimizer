---
phase: 03-warehouse
plan: 08
subsystem: database
tags: [csv-export, duckdb, pandas, byte-stable, ad-050, pytest]

# Dependency graph
requires:
  - phase: 03-warehouse (plan 07)
    provides: "src/ambo/common/db.py — the AD-030 doorway (read_mmm_input, read_dim_layer) this script reads exclusively through, never a second SQL layer"
  - phase: 03-warehouse (plan 04)
    provides: "fct_mmm_input, the frozen 17-column contract this export's rows and header derive from"
provides:
  - "scripts/export_marts.py — a registry-driven (D-03), byte-stable (D-02/D-04) CSV export writer, with a CLI (`main`), EXPORT_REGISTRY dict, ExportSpec dataclass, and the AD-050 duplicate-grain-key validation path"
  - "exports/mmm_input_weekly.csv — the first committed export (D-01), 339 lines, LF-only, six-decimal floats, sorted by layer then week_start"
  - "make export — real target, wired to scripts/export_marts.py"
  - "tests/unit/test_export_marts.py — the AD-050 contract test in both directions plus D-02's local byte-identical-regeneration proof"
  - "docs/MODULE_CONTRACTS.md's scripts/export_marts.py entry"
affects: [03-09, phase-8, phase-9]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registry-as-dict-of-frozen-specs (D-03): EXPORT_REGISTRY[filename] -> ExportSpec(reader, columns, dtype_casts, sort_keys) — a later phase adds an entry, never touches the writing code path."
    - "Column order derived from the reader's own frame (columns: Callable[[pd.DataFrame], list[str]]), never restated as a literal — the same D-08 discipline db.py established, applied to a scripts/ file."
    - "dtype_casts as a {column: 'date'|'Int64'} mapping applied by one small dispatcher, generalizing _write_media_csv's per-column cast-then-write shape without hard-coding which columns exist."
    - "sort_keys doubles as the grain key for the AD-050 duplicate check — no separate grain-columns field needed."
    - "Atomic byte-stable CSV write (.tmp-<pid> + os.replace, %.6f float format, LF-only) reproduced verbatim from ambo.simulate.__main__._atomic_write_csv rather than imported, since scripts/ files are self-contained (matching leak_scan.py/check_layer_order.py precedent)."

key-files:
  created:
    - scripts/export_marts.py
    - tests/unit/test_export_marts.py
    - exports/mmm_input_weekly.csv
  modified:
    - Makefile
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "ExportSpec.columns is a callable (frame -> ordered column list) rather than a stored literal list, so the mart's 17-column order is never restated in Python — the frame read_mmm_input() already returns is the single source, matching D-08's mechanism for db.py."
  - "ExportSpec.sort_keys is reused as the AD-050 grain-key check's subset columns (frame.duplicated(subset=sort_keys)) instead of adding a fifth registry field — the sort order and the grain key are the same columns for every registry entry envisioned so far (mmm_input_weekly.csv, and the SPEC-03 section 5 files Phase 8/9 add)."
  - "_atomic_write_csv is reproduced verbatim inside scripts/export_marts.py rather than imported from ambo.simulate.__main__ — scripts/ is outside the src/ambo dependency-direction table, and every existing scripts/ file (leak_scan.py, check_layer_order.py) is self-contained; importing a private (_-prefixed) function across that boundary would be more coupled than the plan's 'reuse verbatim' wording requires."

patterns-established:
  - "scripts/*.py needing a docs/MODULE_CONTRACTS.md entry: CONTEXT.md names export_marts.py explicitly even though test_repo_layout.py's module-contract guard is scoped to src/ambo/ only (the heading regex ^### (src/ambo/\\S+\\.py)$ does not match scripts/export_marts.py) — the entry is a plan-level obligation, not a build-time-enforced one, for scripts/ files."

requirements-completed: []  # REQ-dl1-reproducible-pipeline is Phase-9-owned (DL-1 probe); REQ-grain-and-windows is Phase-5/6-owned. This plan contributes to both without owning either, matching 03-01/03-02/03-04/03-06/03-07 precedent.

coverage:
  - id: D1
    description: "scripts/export_marts.py ships a registry-driven writer: EXPORT_REGISTRY is a non-empty dict keyed by output filename, each value a frozen ExportSpec (reader, columns, dtype_casts, sort_keys); make export exits 0 and writes exports/mmm_input_weekly.csv; --help names the optional registry-entry argument; importing the module performs no file writes"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: unit
        ref: "tests/unit/test_export_marts.py::test_export_registry_shape"
        status: pass
      - kind: unit
        ref: "tests/unit/test_export_marts.py::test_mmm_input_weekly_entry_reads_every_layer_via_read_dim_layer"
        status: pass
      - kind: other
        ref: "make export && test -f exports/mmm_input_weekly.csv && uv run python scripts/export_marts.py --help"
        status: pass
    human_judgment: false
  - id: D2
    description: "exports/mmm_input_weekly.csv is committed (not gitignored), 339 lines (header + 338 data rows), header exactly the 17 mart columns in contract order, layer column exactly {P-SA, P-SB, P-SC}, sorted by layer then week_start"
    requirement: "REQ-grain-and-windows"
    verification:
      - kind: unit
        ref: "tests/unit/test_export_marts.py::test_committed_export_matches_the_mart_contract"
        status: pass
      - kind: unit
        ref: "tests/unit/test_gitignore.py::test_generated_paths_ignored_but_exports_csv_committed_by_design"
        status: pass
    human_judgment: false
  - id: D3
    description: "Byte-stability: fixed six-decimal float format on every float value, LF-only bytes, and two fresh regenerations plus the committed file are byte-for-byte identical; make transform && make export produces zero git diff on exports/"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: unit
        ref: "tests/unit/test_export_marts.py::test_float_format_is_fixed_six_decimals"
        status: pass
      - kind: unit
        ref: "tests/unit/test_export_marts.py::test_export_is_lf_only"
        status: pass
      - kind: unit
        ref: "tests/unit/test_export_marts.py::test_regenerating_the_export_is_byte_identical"
        status: pass
      - kind: unit
        ref: "tests/unit/test_line_endings.py::test_no_tracked_text_file_contains_a_carriage_return"
        status: pass
      - kind: other
        ref: "make transform && make export && git diff --exit-code exports/"
        status: pass
    human_judgment: false
  - id: D4
    description: "AD-050 negative side: a duplicated (week_start, layer) pair in the frame about to be exported raises DataContractError naming the duplicated key(s), never silently deduplicated"
    requirement: "REQ-grain-and-windows"
    verification:
      - kind: unit
        ref: "tests/unit/test_export_marts.py::test_duplicate_grain_key_in_export_fails_the_contract_test"
        status: pass
    human_judgment: false
  - id: D5
    description: "make lint (ruff check ., ruff format --check src tests scripts, mypy) and the leak scan both exit 0 with the export committed; docs/MODULE_CONTRACTS.md carries a scripts/export_marts.py entry"
    verification:
      - kind: other
        ref: "uv run ruff check . && uv run ruff format --check src tests scripts && uv run mypy && uv run python scripts/leak_scan.py"
        status: pass
      - kind: unit
        ref: "uv run pytest -q (full suite, 316 tests)"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-08-06
status: complete
---

# Phase 3 Plan 8: The Registry-Driven Byte-Stable Export Writer Summary

**`scripts/export_marts.py` — a registry-driven (D-03), byte-stable (D-02/D-04) CSV export writer reading exclusively through `ambo.common.db`, `make export` wired to it, and `exports/mmm_input_weekly.csv` committed as the first entry with a contract test that proves both directions of AD-050 and D-02's local byte-identical-regeneration guarantee.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-06T09:15:00Z (approximate — session start)
- **Completed:** 2026-08-06T09:50:00Z (Task 2 commit)
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- `scripts/export_marts.py`'s `EXPORT_REGISTRY: dict[str, ExportSpec]` holds exactly one entry today, `mmm_input_weekly.csv`, whose reader (`_read_mmm_input_all_layers`) iterates every layer `read_dim_layer()` reports (no hard-coded `["P-SA", "P-SB", "P-SC"]` literal anywhere) and concatenates `read_mmm_input(layer)` per layer — a future Layer R row is picked up automatically once it exists in `dim_layer`.
- `ExportSpec.columns` is a callable over the reader's own returned frame, not a restated 17-column literal — the same D-08 single-home discipline `db.py` established for the mart contract, now applied to the export script.
- `validate_no_duplicate_grain_keys(frame, sort_keys)` is the AD-050 negative-side mechanism: it checks `frame.duplicated(subset=sort_keys)` and raises `DataContractError` naming every duplicated key tuple — `sort_keys` (`["layer", "week_start"]`) doubles as both the row-sort order and the grain-key check, so no fifth registry field was needed.
- `_atomic_write_csv` reproduces `ambo.simulate.__main__._atomic_write_csv` verbatim: a `.tmp-<pid>` sibling opened with `newline=""`, `%.6f` fixed float format, explicit `lineterminator="\n"`, `na_rep=""`, `index=False`, then `os.replace`, with the temp file removed on any exception (T-03-35).
- `main(argv)` is a small argparse CLI: zero positional arguments writes every registry entry; one or more filenames writes only those; `--help` names the optional argument and lists the current registry keys; an unknown name exits 2 via `parser.error`. Importing the module performs no file writes (no reader is called at import time — only referenced).
- The module header docstring records D-05's four required points verbatim: committed by design (SPEC-08 section 2, EB-081), the DL-1 comparison, the future Layer R a-euro interaction once `layer_r_present` flips, and the `docs/RISK_REGISTER.md` entry plan 03-09 adds so the revisit does not depend on memory.
- `Makefile`'s `export:` target is now a single bare `uv run python scripts/export_marts.py` line, matching `simulate:`'s shape; the `SHELL`/`.SHELLFLAGS` pin and the closed 18-target `.PHONY` list are untouched.
- `docs/MODULE_CONTRACTS.md` gained a `### scripts/export_marts.py` entry (inserted after `src/ambo/simulate/__main__.py`, before "Dependency directions") with all five sections, citing `dbt/models/marts/_fct_mmm_input__schema.yml` by path rather than restating the column list.
- `tests/unit/test_export_marts.py` (7 tests): the registry shape (non-empty, every entry carrying a callable reader, a callable column source, a dtype_casts dict, and a non-empty sort_keys list); the layer-derivation proof; the committed export's exact header/row-count/date-format/layer-set/sort-order match against `_contract_columns('fct_mmm_input')`; the AD-050 negative proof (a poisoned 2-row frame with a duplicated `(P-SA, 2021-01-04)` key raises `DataContractError` naming `P-SA`); the six-decimal float format on every value in every float column; the no-carriage-return byte proof; and two fresh regenerations plus the committed file all byte-identical.
- `exports/mmm_input_weekly.csv` committed: 339 lines (header + 338 data rows: 156 + 104 + 78 across P-SA/P-SB/P-SC), header exactly the 17 `fct_mmm_input` columns in contract order, no `\r` byte anywhere, verified `git diff --exit-code exports/` clean after a fresh `make transform && make export`.

## Task Commits

Each task was committed atomically:

1. **Task 1: The registry-driven byte-stable export writer and `make export`** — `36191fd` (feat)
2. **Task 2: The AD-050 contract test and the committed export** — `c66f971` (test)

**Plan metadata:** pending (docs: complete plan, committed after this SUMMARY)

## Files Created/Modified

- `scripts/export_marts.py` — `ExportSpec`, `EXPORT_REGISTRY`, `validate_no_duplicate_grain_keys`, `build_export_frame`, `write_export`, `main`
- `tests/unit/test_export_marts.py` — 7 tests covering registry shape, contract match, AD-050 negative proof, byte-format and regeneration
- `exports/mmm_input_weekly.csv` — the first committed export (D-01)
- `Makefile` — `export:` target rewritten from a loud-failing stub to the real recipe
- `docs/MODULE_CONTRACTS.md` — new `scripts/export_marts.py` entry

## Decisions Made

- `ExportSpec.columns` is a callable over the produced frame rather than a stored column list, keeping the 17-column order single-homed in the dbt schema yml (via `db.py`'s `_contract_columns`), never restated in this script.
- `ExportSpec.sort_keys` is reused as the AD-050 duplicate-grain-key check's subset columns instead of adding a separate grain-columns field — every registry entry envisioned (this one, and the Phase 8/9 additions CONTEXT.md names) has an identical sort-order/grain-key relationship.
- `_atomic_write_csv` is duplicated verbatim inside `scripts/export_marts.py` rather than imported from `ambo.simulate.__main__` — `scripts/` sits outside the `src/ambo` dependency-direction table in `docs/MODULE_CONTRACTS.md`, and the two existing precedent scripts (`leak_scan.py`, `check_layer_order.py`) are both self-contained rather than importing from `src/ambo/simulate`. Importing a private, underscore-prefixed function across that boundary would be tighter coupling than the plan's "reuse verbatim" instruction calls for.

## Deviations from Plan

None — plan executed exactly as written. The two acceptance-criteria items that reference `docs/MODULE_CONTRACTS.md`'s guard test (`test_module_contracts_match_src_ambo_modules_exactly`) were double-checked: that guard's heading regex is scoped to `src/ambo/\S+\.py`, so it does not (and cannot) enforce the `scripts/export_marts.py` entry — the entry was added anyway per CONTEXT.md's explicit instruction and this plan's own acceptance criteria, and the whole-suite run above confirms nothing else broke.

## Issues Encountered

None. `uv run ruff format` needed one pass to reformat a multi-line expression in `export_marts.py` (a chained pandas expression that exceeded the line-length rule when written on one line) and one in `test_export_marts.py` (an overlong assert message) — routine formatting, not a logic change, applied before either commit.

The whole-repo `uv run ruff format --check .` still fails on the same 4 pre-existing `.planning/phases/{02,03}-*/{PATTERNS,RESEARCH}.md` files logged in `deferred-items.md` since plan 03-01 (markdown-embedded-code-fence reformatting) — confirmed unrelated to this plan's five files and already documented; not fixed here, matching the established precedent. `ruff check .`, `ruff format --check src tests scripts`, and `uv run mypy` are all clean.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `exports/mmm_input_weekly.csv` is committed and byte-stable; plan 03-09's CI diff-check (`make transform && make export && git diff --exit-code exports/`) has been proven locally to pass on an unchanged warehouse.
- The `EXPORT_REGISTRY` dict is ready for Phase 8 (`allocation_scenarios.csv`, `attribution_gap.csv`) and Phase 9 (the remaining SPEC-03 section 5 files) to extend with new entries — no change to `write_export`, `main`, or the atomic-write path is anticipated.
- `uv run dbt build --project-dir dbt --profiles-dir dbt` is unaffected by this plan (green, 72 PASS / 0 ERROR, unchanged from plan 03-07).
- `uv run pytest -q` (full suite, 316 tests) is green with no failures.
- `uv run ruff check .`, `uv run mypy`, and `uv run ruff format --check src tests scripts` are all clean.
- `uv run python scripts/leak_scan.py` exits 0 with the export committed — the D-05 header comment and the plan 03-09 `RISK_REGISTER.md` entry are the tracking mechanism for the future Layer R a-euro / leak-scan-scope revisit, not acted on in this plan.
- No blockers for plan 03-09.

---
*Phase: 03-warehouse*
*Completed: 2026-08-06*

## Self-Check: PASSED

- FOUND: scripts/export_marts.py
- FOUND: tests/unit/test_export_marts.py
- FOUND: exports/mmm_input_weekly.csv
- FOUND: Makefile
- FOUND: docs/MODULE_CONTRACTS.md
- FOUND: 36191fd (Task 1 commit)
- FOUND: c66f971 (Task 2 commit)
