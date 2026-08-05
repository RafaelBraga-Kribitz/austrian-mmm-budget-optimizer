---
phase: 02-ground-truth-simulator
plan: 09
subsystem: simulate
tags: [cli, gate-runner, sim-070, byte-stable-csv, makefile]

# Dependency graph
requires:
  - phase: 02-06
    provides: "assemble_scenario(cfg, rng) -> SimulationResult, decomposition_audit, plausibility_audit, peak_week_audit, adstock_recursive, hill"
  - phase: 02-07
    provides: "platform_report(result) -- the platform-completed media frame this plan writes to media_weekly.csv"
  - phase: 02-08
    provides: "compute_truth(result, media) -> TruthFile and write_truth(t, path) -- the truth.json this plan orchestrates and re-validates in SIM-075"
provides:
  - "python -m ambo.simulate {all|s_a|s_b|s_c|validate} [--outdir PATH] -- the end-to-end simulator CLI"
  - "validate_sim(outdir) -- the SIM-070...075 + BP-G-02 gate runner, seven-row table, exit 0 iff every SIM-0xx row is PASS"
  - "real make simulate / make validate-sim targets, replacing the Phase 1 stubs"
affects: [02-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared _generate_scenario(name, outdir) helper called by both main()'s generation targets and _gate_sim_070's SIM-070 regeneration -- the two call sites can never independently drift"
    - "SHA-256-over-concatenated-fixed-order-files as SIM-070's byte-identity evidence, with an explicit exists-and-non-empty precondition checked before hashing (never folded silently into a hash mismatch)"
    - "Nullable pandas Int64/plain float64 dtype split before to_csv: integer columns cast to Int64 so they render with no decimal point and NULL survives as an empty field; float columns cast to plain float64 so the writer's %.6f format applies uniformly"
    - "SIM-074's three closed-form checks (constant-spend limit, impulse response, hill(K,K,s)==0.5) run in-process against dgp.adstock_recursive/dgp.hill directly -- src/ must not depend on the test framework"

key-files:
  created:
    - src/ambo/simulate/__main__.py
    - tests/unit/test_simulate_cli.py
  modified:
    - docs/MODULE_CONTRACTS.md
    - Makefile

key-decisions:
  - "Tasks 1 and 2 landed in a single commit (964bcf8), mirroring 02-08's precedent -- the CLI, both CSV writers, and the full seven-row validate_sim gate runner were authored as one coherent module in a single pass (the writers and the gate runner's SIM-070 regeneration share the same _generate_scenario helper, so splitting them would have left an intermediate commit calling a function that didn't exist yet). The commit message's 'validate_sim stub, Task 2 fills it in' phrasing is inaccurate -- validate_sim was already fully implemented in that commit; recorded here as a correction. Task 3's tests remain their own commit (27072fc)."
  - "BP-G-02's DELEGATED row is excluded from validate_sim's own PASS/FAIL exit-code computation (only the six SIM-0xx rows count) -- the plan's 'returns 0 iff every row is PASS' and 'prints a DELEGATED status' instructions are reconciled by reading 'every row' as every row this function can itself evaluate; the Makefile composes the two exit codes (python -m ambo.simulate validate; then the pytest selector), so make validate-sim as a whole still cannot go green without both."
  - "The BP-G-02 selector string and every docstring/comment in __main__.py were written to avoid the literal substring 'pytest' entirely (referring to it as 'the selector' / 'the test suite' instead) -- Task 2's own acceptance criterion (grep -c 'pytest' src/ambo/simulate/__main__.py returns 0) is stricter than 'no import statement': it is a literal substring scan, so the BP-G-02 evidence text names the test file and -k expression without ever spelling the runner's name."
  - "SIM-074's lam/(K,s) sweep set-deduplicates over all three scenarios' six channels rather than testing one representative value -- since S-A/S-B/S-C share identical SPEC-01 section 4 true parameters (S-C's zero-beta display_video still has the same lam/K/s), this is a small set (6 distinct lam values, 6 distinct (K,s) pairs), not 18 redundant evaluations, and it means a future scenario introducing a genuinely new parameter value is swept automatically."

requirements-completed: []  # REQ-q1-truth-recovery / REQ-grain-and-windows are Phase-5/6-owned per REQUIREMENTS.md traceability table, same decision as every prior 02-0x plan.

coverage:
  - id: D1
    description: "python -m ambo.simulate all writes all nine SIM-004 artifacts (media_weekly.csv, outcome_weekly.csv, truth.json per scenario) into --outdir or the data/synthetic/ default, and exits 0"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_all_nine_artifacts_are_created"
        status: pass
      - kind: manual
        ref: "make simulate; ls data/synthetic/*/ (9 files across 3 scenario dirs)"
        status: pass
    human_judgment: false
  - id: D2
    description: "SIM-070: two full runs into two different output directories are byte-identical, proven by a non-vacuous nine-file existence+size check before any byte comparison"
    verification:
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_determinism_two_runs_are_byte_identical"
        status: pass
      - kind: manual
        ref: "python -m ambo.simulate validate -- SIM-070 row: committed=016aad7d... regenerated=016aad7d... (equal)"
        status: pass
    human_judgment: false
  - id: D3
    description: "make validate-sim prints exactly one row per gate (SIM-070..075, BP-G-02) with its evidence value, and exits non-zero if any row fails"
    verification:
      - kind: manual
        ref: "make simulate && make validate-sim -- seven-row table, exit 0 (full table pasted below)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The determinism gate is proven to bite: a deleted CSV and a one-byte truth.json edit each make validate_sim exit non-zero with SIM-070 naming the failure, then exit 0 again after restore"
    verification:
      - kind: manual
        ref: "red-then-green evidence pasted below (missing s_b/outcome_weekly.csv; +1 byte on s_a/truth.json)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both CSV writers are byte-stable by construction (UTF-8, LF-only, %.6f float format, na_rep=\"\" for offline-channel NULL, no index column) and emit SIM-004's exact header/column order, read from written bytes not an in-memory frame"
    verification:
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_csv_headers_match_sim_004_exactly"
        status: pass
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_offline_channels_render_as_empty_fields"
        status: pass
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_integer_columns_have_no_decimal_point"
        status: pass
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_no_cr_bytes_in_any_written_file"
        status: pass
    human_judgment: false
  - id: D6
    description: "Row order in every written CSV is total: outcome_weekly.csv ascending by unique week_start; media_weekly.csv ascending by week_start then SPEC_CHANNEL_ORDER, with (week_start, channel) unique"
    verification:
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_week_start_is_iso_date_and_spine_is_gapless"
        status: pass
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_media_row_order_is_week_then_taxonomy"
        status: pass
    human_judgment: false
  - id: D7
    description: "An unknown scenario argument exits non-zero naming the four valid choices, and never writes a partial output directory; --outdir redirects every write so the pipeline is tmp_path-testable"
    verification:
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_unknown_target_exits_non_zero_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/unit/test_simulate_cli.py#test_single_scenario_target_writes_only_that_scenario"
        status: pass
    human_judgment: false
  - id: D8
    description: "The gate runner imports nothing from the test framework or tests/ -- SIM-074's closed-form checks call dgp functions directly"
    verification:
      - kind: manual
        ref: "grep -c 'pytest' src/ambo/simulate/__main__.py returns 0"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min
completed: 2026-08-05
status: complete
---

# Phase 2 Plan 9: Simulator CLI, `make simulate`/`validate-sim`, Determinism Gate Summary

**`src/ambo/simulate/__main__.py` orchestrates config -> dgp -> spend_patterns -> platform_bias -> truth into the nine SIM-004 artifacts via a byte-stable CLI, and `validate_sim` turns SIM-070...075 + BP-G-02 into a seven-row pass/fail gate table that `make simulate && make validate-sim` runs for real, replacing the Phase 1 stubs.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-08-05
- **Tasks:** 3 completed
- **Files modified:** 4 (`src/ambo/simulate/__main__.py` new, `tests/unit/test_simulate_cli.py` new, `docs/MODULE_CONTRACTS.md` extended, `Makefile` extended)

## Accomplishments

- `main(argv: list[str] | None = None) -> int` -- CLI grammar `python -m ambo.simulate {all|s_a|s_b|s_c|validate} [--outdir PATH]`. One fresh `np.random.default_rng(cfg.seed)` per scenario, never reused. `--outdir` defaults to `repo_root() / "data" / "synthetic"`. An unrecognised target is rejected by `argparse` itself (exit 2, names the five valid choices) before any directory is created.
- `_write_media_csv`/`_write_outcome_csv` -- byte-stable by construction: UTF-8, `newline=""` plus an explicit `lineterminator="\n"` (never `.gitattributes`), fixed `%.6f` float format, `na_rep=""`, `index=False`, integer columns cast to nullable `Int64` so they render with no decimal point and an offline channel's platform fields render as genuinely empty. Both writers go through `_atomic_write_csv`'s `.tmp-<pid>`/`os.replace` pattern, mirroring `truth.write_truth`.
- `validate_sim(outdir: Path) -> int` -- the SIM-070...075 + BP-G-02 gate runner. Six PASS/FAIL rows evaluated in-process (SIM-070 regenerates into a fresh temp dir and SHA-256-compares against `outdir`, with an exists-and-non-empty precondition checked before hashing; SIM-071/072/073 call `dgp.decomposition_audit`/`plausibility_audit`/`peak_week_audit`; SIM-074 evaluates the constant-spend limit, the impulse response, and `hill(K,K,s)==0.5` directly against `dgp.adstock_recursive`/`dgp.hill`, over every distinct `lam`/`(K,s)` pair the three scenario configs declare; SIM-075 re-reads and re-validates each `truth.json` against `ScenarioConfig`), plus a seventh `DELEGATED` row naming BP-G-02's real home. Returns 0 iff all six SIM-0xx rows are PASS; performs no remediation on a red gate.
- `Makefile`: `simulate` runs `uv run python -m ambo.simulate all`; `validate-sim` runs the gate runner then the BP-G-02 selector, composed so the target fails if either does.
- `docs/MODULE_CONTRACTS.md`: contract-first entry for `__main__.py` (Purpose, Public API, Invariants, Failure modes, Testing), landed in the same commit as the module (D-23).
- 14 tests in `tests/unit/test_simulate_cli.py` (5.6s, well under the 120s ceiling): SIM-070 byte-identity (non-vacuous nine-file check before comparison), all-nine-artifacts creation, SIM-004 header/NULL/no-decimal/no-CR/gapless-spine/taxonomy-order assertions read from written bytes, single-scenario/unknown-target CLI behavior, and `validate_sim` pass/fail on a fresh generation, a corrupted `truth.json`, and a missing CSV.

## Task Commits

1. **Task 1+2: CLI, byte-stable CSV writers, and the full SIM-070...075 + BP-G-02 gate runner** - `964bcf8` (feat) -- see Deviations below: both tasks' functionality landed here in one pass.
2. **Task 3: SIM-070 determinism and CLI/gate-runner contract tests** - `27072fc` (test)

**Plan metadata:** committed as part of this summary's own commit.

## Files Modified

- `src/ambo/simulate/__main__.py` -- new module: `main`, `validate_sim`, `_generate_scenario`, `_write_media_csv`, `_write_outcome_csv`, `_atomic_write_csv`, `_hash_tree`, `_gate_sim_070`..`_gate_sim_075`.
- `tests/unit/test_simulate_cli.py` -- new: 14 tests.
- `docs/MODULE_CONTRACTS.md` -- new `### src/ambo/simulate/__main__.py` entry.
- `Makefile` -- `simulate`/`validate-sim` targets replaced from `$(call STUB,2)` to real recipes.

## Decisions Made

- **Tasks 1+2 landed in a single commit** (`964bcf8`), mirroring 02-08's precedent for the same reason: the CLI, the writers, and the gate runner's SIM-070 regeneration all share the `_generate_scenario` helper, so there was no meaningful point to split a working intermediate commit at. The commit message's phrase "validate_sim(outdir) stub wired into main's dispatch (Task 2 fills it in)" is a leftover from the plan's task split and is **inaccurate** -- `validate_sim` was fully implemented with all seven gate rows in that same commit. Recorded here as the correction; no functional gap exists.
- **BP-G-02's row is `DELEGATED`, not counted in `validate_sim`'s own exit code** -- read literally, the plan's "returns 0 iff every row is PASS" and "prints a DELEGATED status for BP-G-02" instructions are in tension. Resolved by scoping "every row" to the six rows `validate_sim` can itself evaluate in-process; `make validate-sim`'s two-line recipe (gate runner, then the BP-G-02 pytest selector) is where the two exit codes actually compose, per the plan's own explicit statement that "the make validate-sim target runs that selector in the same invocation so the target as a whole cannot go green without it."
- **Zero occurrences of the literal substring `pytest` anywhere in `__main__.py`** -- Task 2's acceptance criterion (`grep -c 'pytest' ... returns 0`) is a literal substring scan, not just an import check, so the BP-G-02 evidence string and every docstring refer to "the selector" / "the test suite" rather than naming the runner. Verified: `grep -c "pytest" src/ambo/simulate/__main__.py` returns `0`.
- **SIM-074's closed-form checks sweep every distinct `lam`/`(K, s)` pair across all three loaded scenario configs** (deduplicated via `set`), not one representative value -- cheap (6 distinct values each, since S-A/S-B/S-C share identical SPEC-01 section 4 parameters) and automatically covers a future scenario that introduces a new parameter value.

## Deviations from Plan

**1. [Commit-granularity note, not a Rule 1-4 deviation]** Tasks 1 and 2 landed in a single commit rather than two, per the "Decisions Made" entry above. No code behavior differs from the plan; only the task-to-commit mapping does, exactly the same shape of deviation 02-08 recorded for its own Tasks 1+2.

No Rule 1-4 code deviations: every acceptance criterion across all three tasks passed on first implementation after one mypy fix (a local variable name reused across two loop bodies with incompatible inferred types -- `expected` renamed to `expected_limit`/`expected_impulse`) and one `ruff format` pass.

## Issues Encountered

`uv run ruff format --check .` (whole-repo) still fails on the same pre-existing, already-deferred `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`/`02-RESEARCH.md` markdown-embedded-code-fence issue first logged by 02-01 and re-confirmed by every plan since (02-04 through 02-08) -- re-confirmed here as still out of scope (neither file is in this plan's `files_modified`, neither was touched by any task). `uv run ruff check .` (lint proper), `uv run ruff format --check` scoped to this plan's own files, and `uv run mypy` (strict, whole `src/ambo`) all pass cleanly. `make test` passes fully (281 passed, up from 267 before this plan; coverage 93%).

## Evidence

### `make simulate && make validate-sim` -- full green gate table

```
uv run python -m ambo.simulate all
scenario s_a written to .../data/synthetic/s_a in 0.06s
scenario s_b written to .../data/synthetic/s_b in 0.05s
scenario s_c written to .../data/synthetic/s_c in 0.05s
uv run python -m ambo.simulate validate
GATE     STATUS     EVIDENCE
SIM-070  PASS       committed=016aad7d5e8c3c629fd23cc99abb2f8d655f50173ab9f2e757401e4c30cccfd1 regenerated=016aad7d5e8c3c629fd23cc99abb2f8d655f50173ab9f2e757401e4c30cccfd1
SIM-071  PASS       s_a=0.0, s_b=0.0, s_c=0.0 (max=0.0, bound<=1e-6)
SIM-072  PASS       s_a: {'min_revenue_pre_clip': 64094.84287664617, 'noise_variance_share': 0.03113949883141409, 'media_share_2021': 0.2730426362263659, 'media_share_2022': 0.26633491313334523, 'media_share_2023': 0.25753447781321676}; s_b: {'min_revenue_pre_clip': 70242.79391112749, 'noise_variance_share': 0.026355908286650902, 'media_share_2022': 0.27442453188862836, 'media_share_2023': 0.26245675624176334}; s_c: {'min_revenue_pre_clip': 62307.90535157751, 'noise_variance_share': 0.03959346809337588, 'media_share_2022': 0.2472965119066494, 'media_share_2023': 0.255949800658689}
SIM-073  PASS       s_a 2021: peak_week=50 advent_flag=True; s_a 2022: peak_week=51 advent_flag=True; s_a 2023: peak_week=50 advent_flag=True; s_b 2022: peak_week=50 advent_flag=True; s_b 2023: peak_week=50 advent_flag=True; s_c 2022: peak_week=50 advent_flag=True; s_c 2023: skipped (Advent window not fully covered)
SIM-074  PASS       constant_spend_residual=9.094947017729282e-13 (bound<=1e-9), impulse_residual=2.7755575615628914e-17 (bound<=1e-9), hill_at_K_residual=0.0 (bound<=1e-12)
SIM-075  PASS       all three truth.json files re-validated and match ScenarioConfig
BP-G-02  DELEGATED  scenario YAML == SPEC-01 section 4 table (SIM-002 single home); checked by the selector `tests/unit/test_scenario_config.py -k "spec_parameter_table or rule_level"`, run by make validate-sim in the same invocation so the target cannot go green without it.
uv run pytest tests/unit/test_scenario_config.py -k "spec_parameter_table or rule_level" -q
2 passed
```

Exit code: `0`. Note: SPEC-01's Advent flag is only 4 ISO weeks/year, so `s_c`'s 2023 half-year window (weeks 01-26) never carries an `advent_flag == 1` row -- correctly reported as a skipped year (the `(-1, True)` sentinel), not silently omitted, per `peak_week_audit`'s documented convention.

### SIM-070 red-then-green evidence

**Case 1 -- deleted file** (`data/synthetic/s_b/outcome_weekly.csv` removed):
```
SIM-070  FAIL  missing or empty file(s) in the committed tree: ['s_b/outcome_weekly.csv']
```
Exit code: `1`. Restored, re-ran: `SIM-070  PASS  committed=016aad7d... regenerated=016aad7d...`, exit code `0`.

**Case 2 -- one-byte edit** (`X` appended to `data/synthetic/s_a/truth.json`):
```
SIM-070  FAIL  committed=a8e886855c14c6cbd3e5c49b1bb726d4618ce739ceae48e044986bf385e44478 regenerated=016aad7d5e8c3c629fd23cc99abb2f8d655f50173ab9f2e757401e4c30cccfd1
```
Exit code: `1`. Restored (byte removed), re-ran: `SIM-070  PASS  committed=016aad7d... regenerated=016aad7d...`, exit code `0`.

### `test_simulate_cli.py` measured runtime and coverage

- `uv run pytest tests/unit/test_simulate_cli.py -q`: 14 passed in **5.6s** (well under the 120s ceiling from `02-VALIDATION.md`'s latency target -- no trimming needed).
- `make test` (full suite, 281 tests): **21.79s**, `src/ambo/` coverage **93%** (well above the 80% `[STD]` merge-readiness threshold), up from 267 tests / no regression in coverage before this plan.

### Elapsed plan duration (Charter section 5 effort tally)

~40 minutes, comparable to 02-07 (35 min) and 02-08 (~40 min), the two most similarly-scoped prior plans in this phase.

## Next Phase Readiness

- `python -m ambo.simulate all` and `python -m ambo.simulate validate` are both fully wired and proven green against the committed calendar seed and the three scenario YAMLs.
- `data/synthetic/{s_a,s_b,s_c}/` (9 files) exist on disk from this plan's manual verification runs but are **deliberately left untracked** -- committing them is 02-10's job per the phase's own artifact-ownership table (`data/synthetic/{s_a,s_b,s_c}/ (02-10)`), so `git add`ing them here would pre-empt that plan's own commit.
- Plan 02-10 can now run `make simulate && make validate-sim`, inspect the green table, and commit the nine artifacts plus the M1 checklist evidence.
- No blockers for 02-10.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: src/ambo/simulate/__main__.py
- FOUND: tests/unit/test_simulate_cli.py
- FOUND: docs/MODULE_CONTRACTS.md (entry present)
- FOUND: Makefile (simulate/validate-sim targets present)
- FOUND: 964bcf8 (Task 1+2 commit)
- FOUND: 27072fc (Task 3 commit)
