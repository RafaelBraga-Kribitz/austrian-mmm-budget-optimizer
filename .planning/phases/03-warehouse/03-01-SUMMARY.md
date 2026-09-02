---
phase: 03-warehouse
plan: 01
subsystem: database
tags: [dbt, duckdb, warehouse, data-pipeline]

# Dependency graph
requires:
  - phase: 02-ground-truth-simulator
    provides: committed synthetic CSVs (data/synthetic/{s_a,s_b,s_c}/{media_weekly,outcome_weekly}.csv)
provides:
  - dbt project scaffold (dbt_project.yml, profiles.yml) with the trusted-var block
  - unconditional make transform target running a real dbt build
  - five source-path-parameterized raw dbt views (Layer P built, Layer R dormant-but-written)
  - two pytest files pinning the taxonomy-equality and warehouse-path facts
affects: [03-02, 03-03, 03-04, 03-05, 03-06, phase-6-intake]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dbt var-parameterized read_csv_auto path for every raw-layer source"
    - "jinja-guarded Layer R branch: true branch reads real data, false branch is an identically-shaped zero-row select"
    - "committed dbt profiles.yml with no user-specific paths"

key-files:
  created:
    - dbt/dbt_project.yml
    - dbt/profiles.yml
    - dbt/models/raw/raw_media_p.sql
    - dbt/models/raw/raw_outcome_p.sql
    - dbt/models/raw/raw_media_r.sql
    - dbt/models/raw/raw_outcome_r.sql
    - dbt/models/raw/raw_promo_r.sql
    - tests/unit/test_dbt_config.py
    - tests/unit/test_warehouse_build.py
    - .planning/phases/03-warehouse/deferred-items.md
  modified:
    - Makefile
    - docs/BUILD_LOG.md
    - .gitignore
    - .planning/phases/03-warehouse/03-PATTERNS.md
    - .planning/phases/03-warehouse/03-RESEARCH.md

key-decisions:
  - "profiles.yml dev.path is the bare `data/warehouse/ambo.duckdb` string (no `../` prefix), per RESEARCH.md Pitfall 1's empirical CWD-relative path-resolution finding for the --project-dir/--profiles-dir invocation pattern"
  - "make transform's D-17 conditional removed entirely (D-21) -- the target is now one unconditional dbt build line"
  - "dbt/.user.yml (dbt's per-machine random-UUID usage-stats file) added to .gitignore -- discovered generated during Task 1's first dbt invocation, not anticipated by the plan's own .gitignore read_first note"

patterns-established:
  - "Pattern 1 (RESEARCH.md): every raw-layer read_csv_auto path is built from a dbt var, never a hard-coded prefix -- the single parameterization plans 03-03, 03-06, and Phase 6 all depend on"

requirements-completed: []  # REQ-dl1-reproducible-pipeline is Phase-9-owned (contributing only from Phase 3); not marked complete here, matching the 02-02/02-09 precedent for contributing-only requirements

coverage:
  - id: D1
    description: "dbt project scaffold, committed profile, unconditional make transform target"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: integration
        ref: "make transform (uv run dbt build --project-dir dbt --profiles-dir dbt)"
        status: pass
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_make_transform_builds_the_project"
        status: pass
    human_judgment: false
  - id: D2
    description: "Warehouse file lands at exactly settings.paths.warehouse, never above the repo root"
    requirement: "REQ-dl1-reproducible-pipeline"
    verification:
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_warehouse_file_lands_at_settings_path"
        status: pass
    human_judgment: false
  - id: D3
    description: "Five raw dbt views: Layer P built (2028 media rows, 338 outcome rows across P-SA/P-SB/P-SC), Layer R structurally present and empty under the default flag, every source path flowing through a dbt var"
    verification:
      - kind: integration
        ref: "uv run dbt build --project-dir dbt --profiles-dir dbt (5 view models OK)"
        status: pass
      - kind: other
        ref: "duckdb query: raw_media_p count=2028, raw_outcome_p count=338, raw_media_r/raw_outcome_r/raw_promo_r count=0"
        status: pass
    human_judgment: false
  - id: D4
    description: "dbt/Python taxonomy equality (BP-G-03) and profiles.yml/settings.yaml warehouse-path equality, both proven red-then-green"
    verification:
      - kind: unit
        ref: "tests/unit/test_dbt_config.py::test_dbt_channel_taxonomy_var_equals_settings_channels"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dbt_config.py::test_profiles_dev_path_matches_settings_warehouse"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 1: dbt Project Scaffold and Raw Layer Summary

**dbt project stood up (dbt_project.yml, committed profiles.yml, unconditional `make transform`) plus five source-path-parameterized raw views over the Phase 2 synthetic CSVs, with the Layer R branch written but dormant, and two pytest files pinning the taxonomy and warehouse-path facts against a version bump.**

## Performance

- **Duration:** ~25 min on this lineage (2A copy of m0 science; format + SUMMARY here)
- **Completed:** 2026-09-02
- **Tasks:** 3
- **Files modified:** 11 plan files plus 03-PATTERNS/03-RESEARCH format

## Accomplishments

- `dbt/dbt_project.yml` and `dbt/profiles.yml` copied from verified `m0-bootstrap` `7dcbbcc` (2A): trusted-input vars (`layer_r_present`, `intake_manifest_present`, `channel_taxonomy`, `data_synthetic_path`, `data_real_anon_path`), raw/staging/marts materialization, `season_windows` seed pins, committed `dev`/`test` duckdb profile with no user-specific paths.
- `make transform`'s D-17 conditional stub replaced with the unconditional `uv run dbt build --project-dir dbt --profiles-dir dbt` recipe line (D-21).
- Five raw dbt views: `raw_media_p`/`raw_outcome_p` (jinja for-loop union over the three Layer P scenarios) and `raw_media_r`/`raw_outcome_r`/`raw_promo_r` (jinja-guarded Layer R branch, dormant by default, identically-shaped zero-row false branch).
- `tests/unit/test_dbt_config.py` and `tests/unit/test_warehouse_build.py` pinning taxonomy-equality (BP-G-03) and warehouse-path (D-23).
- Formatted `03-PATTERNS.md` and `03-RESEARCH.md` so `make lint` is green (same 02-01 precedent; those files arrived in this plan's 2A context copy).

## Task Commits

1. **Task 1: dbt project scaffold, committed profile, and the unconditional make transform target** — `c38cacf` (feat)
2. **Task 2: Raw layer as source-path-parameterized external views, with the Layer R branch written but dormant** — `e33f9ce` (feat)
3. **Task 3: Pin the two facts a version bump could silently break — warehouse location and taxonomy equality** — `31264bd` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `dbt/dbt_project.yml` — dbt project definition: vars block, model materialization config, seed column-type pins
- `dbt/profiles.yml` — committed profile: `dev` (real warehouse) and `test` (throwaway, `AMBO_TEST_WAREHOUSE`-overridable) outputs
- `dbt/models/raw/raw_media_p.sql` — Layer P media, jinja for-loop union over s_a/s_b/s_c
- `dbt/models/raw/raw_outcome_p.sql` — Layer P outcome, same loop shape
- `dbt/models/raw/raw_media_r.sql` — Layer R media, `layer_r_present`-guarded, dormant zero-row false branch
- `dbt/models/raw/raw_outcome_r.sql` — Layer R outcome, same guard pattern
- `dbt/models/raw/raw_promo_r.sql` — Layer R promo, same guard pattern
- `Makefile` — `transform:` target rewritten from a D-17 conditional stub to the unconditional real recipe
- `docs/BUILD_LOG.md` — M2 opening entry: 1d+1d Phase 3/4 budget split, D-19 shed order, never-shed list, three deliberate departures
- `.gitignore` — `dbt/.user.yml` added (dbt's per-machine random-UUID usage-stats file)
- `tests/unit/test_dbt_config.py` — BP-G-03 taxonomy-equality test + static warehouse-path equality test
- `tests/unit/test_warehouse_build.py` — `_run_dbt` shared subprocess helper + make-transform-builds-green test + dynamic warehouse-path test
- `.planning/phases/03-warehouse/03-PATTERNS.md`, `03-RESEARCH.md` — ruff format so `make lint` is green
- `.planning/phases/03-warehouse/deferred-items.md` — records that the m0 lint deferral was resolved here by formatting those two files

## Decisions Made

- **`profiles.yml` `dev.path` is the bare `data/warehouse/ambo.duckdb` string, no `../` prefix.** RESEARCH.md Pitfall 1: for `--project-dir dbt --profiles-dir dbt` with CWD = repo root, the path resolves against the process CWD, not the profile dir.
- **`make transform`'s D-17 conditional removed entirely (D-21).** A "nothing-to-build" branch would let a deleted `dbt_project.yml` report a green CI job.
- **`dbt/.user.yml` added to `.gitignore`.** dbt writes this file on first invocation with a random per-machine anonymous-usage-stats UUID.
- **REQ-dl1-reproducible-pipeline not marked complete.** Phase-9-owned; Phase 3 contributes only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Lineage] `make lint` on 03-PATTERNS.md / 03-RESEARCH.md**
- **Found during:** Task 3 verification (`ruff format --check .`)
- **Issue:** On m0 those files were deferred (not in `files_modified`). Here they arrived in `dabdb6f` (this plan's 2A context copy).
- **Fix:** `uv run ruff format` on the two files. `make lint` exits 0.
- **Verification:** `make lint && make test` — **285 passed**, 93% coverage.

### Process

**2. [Process] 2A copy** of dbt science from `m0-bootstrap` (`7dcbbcc` / `aa68796` / `4574baa`). BUILD_LOG appended on this lineage, never wholesale-checked-out.

**3. [Process] 4B** one PR per plan. CI against `main` deferred (D-19).

**Total deviations:** 1 auto-fixed (format), 2 process. No scope creep.

## Issues Encountered

None beyond the format fix above.

## User Setup Required

None.

## Next Phase Readiness

- The dbt project builds green on seeds + five raw views; `make transform` is unconditional.
- Every raw-layer source path flows through a dbt var, unblocking 03-02 (mart-only guard), 03-03 (staging / poisoned fixture), 03-06 (Layer R fixture), and Phase 6 intake.
- Next plan: **03-02** (`DataContractError` + AD-030 mart-only guard).

---
*Phase: 03-warehouse*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 9 created files verified present on disk; task commit hashes `c38cacf`, `e33f9ce`, `31264bd` are on `cursor/dbt-scaffold-9588`.
