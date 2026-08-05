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

duration: ~15min
completed: 2026-08-05
status: complete
---

# Phase 3 Plan 1: dbt Project Scaffold and Raw Layer Summary

**dbt project stood up from scratch (dbt_project.yml, committed profiles.yml, unconditional `make transform`) plus five source-path-parameterized raw views over the Phase 2 synthetic CSVs, with the Layer R branch written but dormant, and two pytest files pinning the taxonomy and warehouse-path facts against a version bump.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-08-05
- **Tasks:** 3
- **Files modified:** 11 (8 created, 3 modified)

## Accomplishments

- `dbt/dbt_project.yml` and `dbt/profiles.yml` created from scratch: the five-var trusted-input block (`layer_r_present`, `intake_manifest_present`, `channel_taxonomy`, `data_synthetic_path`, `data_real_anon_path`), raw/staging/marts materialization config, `season_windows` seed column-type pins, and a committed `dev`/`test` duckdb profile with no user-specific paths.
- `make transform`'s D-17 conditional stub replaced with the unconditional `uv run dbt build --project-dir dbt --profiles-dir dbt` recipe line (D-21) — it can no longer report success by finding nothing to build.
- Five raw dbt views built over the committed synthetic CSVs: `raw_media_p`/`raw_outcome_p` (jinja for-loop union over the three Layer P scenario/layer pairs) and `raw_media_r`/`raw_outcome_r`/`raw_promo_r` (jinja-guarded Layer R branch, dormant by default, identically-shaped zero-row false branch).
- `tests/unit/test_dbt_config.py` and `tests/unit/test_warehouse_build.py` created, pinning the taxonomy-equality (BP-G-03) and warehouse-path (D-23) facts a dbt version bump could silently break.

## Task Commits

1. **Task 1: dbt project scaffold, committed profile, and the unconditional make transform target** — `7dcbbcc` (feat)
2. **Task 2: Raw layer as source-path-parameterized external views, with the Layer R branch written but dormant** — `aa68796` (feat)
3. **Task 3: Pin the two facts a version bump could silently break — warehouse location and taxonomy equality** — `4574baa` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `dbt/dbt_project.yml` — dbt project definition: vars block, model materialization config, seed column-type pins
- `dbt/profiles.yml` — committed profile: `dev` (real warehouse) and `test` (throwaway, `AMBO_TEST_WAREHOUSE`-overridable) outputs
- `dbt/models/raw/raw_media_p.sql` — Layer P media, jinja for-loop union over s_a/s_b/s_c
- `dbt/models/raw/raw_outcome_p.sql` — Layer P outcome, same loop shape
- `dbt/models/raw/raw_media_r.sql` — Layer R media, `layer_r_present`-guarded, dormant zero-row false branch
- `dbt/models/raw/raw_outcome_r.sql` — Layer R outcome, same guard pattern
- `dbt/models/raw/raw_promo_r.sql` — Layer R promo, same guard pattern
- `Makefile` — `transform:` target rewritten from a D-17 conditional stub to the unconditional real recipe; `DBT_PROJECT_FILE` variable removed
- `docs/BUILD_LOG.md` — M2 opening entry: 1d+1d Phase 3/4 budget split, D-19 shed order, never-shed list, three deliberate departures
- `.gitignore` — `dbt/.user.yml` added (dbt's per-machine random-UUID usage-stats file)
- `tests/unit/test_dbt_config.py` — BP-G-03 taxonomy-equality test + static warehouse-path equality test
- `tests/unit/test_warehouse_build.py` — `_run_dbt` shared subprocess helper + make-transform-builds-green test + dynamic warehouse-path test
- `.planning/phases/03-warehouse/deferred-items.md` — new: logs the pre-existing whole-repo `ruff format --check .` markdown-fence issue as out of scope

## Decisions Made

- **`profiles.yml` `dev.path` is the bare `data/warehouse/ambo.duckdb` string, no `../` prefix.** RESEARCH.md Pitfall 1 empirically disproved the implementation guide's "resolves relative to the profile dir" claim for the mandated `--project-dir dbt --profiles-dir dbt` invocation with CWD = repo root: the path resolves against the process's current working directory at invocation. Confirmed live in this session's red-then-green proof (see Deviations).
- **`make transform`'s D-17 conditional removed entirely (D-21).** A "nothing-to-build" branch would let a deleted `dbt_project.yml` report a green CI job; dbt already fails loudly on a missing project, and `test_repo_layout.py` already asserts `dbt/` against SPEC-08 §2.
- **`dbt/.user.yml` added to `.gitignore`.** dbt writes this file on first invocation with a random per-machine anonymous-usage-stats UUID; not reproducible, not meaningful to commit. Discovered during Task 1's first `dbt build` — not anticipated by the plan's own `.gitignore` `read_first` note, which named only `dbt/target/*` and `dbt/logs/`.
- **REQ-dl1-reproducible-pipeline not marked complete.** REQUIREMENTS.md's traceability table shows this requirement as Phase-9-owned, with Phases 3 and 5 contributing only — matching the 02-02/02-09 precedent of not invoking `requirements mark-complete` for contributing-only requirements.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `dbt/.user.yml` gitignored**
- **Found during:** Task 1 (first `uv run dbt build` invocation)
- **Issue:** dbt writes a per-machine random-UUID anonymous-usage-stats file (`dbt/.user.yml`) on first invocation. Left untracked, it would either pollute `git status` forever or get accidentally committed as non-reproducible content.
- **Fix:** Added `dbt/.user.yml` to `.gitignore` alongside the existing `dbt/target/*`/`dbt/logs/` entries.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` no longer lists `dbt/.user.yml` as untracked after the fix.
- **Committed in:** `7dcbbcc` (Task 1 commit)

**2. [Rule 3-adjacent, out-of-scope, not fixed] Pre-existing whole-repo `ruff format --check .` failure on 4 planning markdown files**
- **Found during:** Task 1 verification (`make lint`)
- **Issue:** `.planning/phases/02-ground-truth-simulator/{02-PATTERNS,02-RESEARCH}.md` and `.planning/phases/03-warehouse/{03-PATTERNS,03-RESEARCH}.md` fail `ruff format --check .` because ruff's markdown-embedded-code-fence formatter reformats fenced Python snippets inside these docs. The 02-* pair is already documented as out of scope in `docs/BUILD_LOG.md`'s M1 close entry (02-01); the 03-* pair is new but neither file is in this plan's `files_modified`, and neither was touched by any of its three tasks.
- **Not fixed** — logged per the executor's scope-boundary rule to `.planning/phases/03-warehouse/deferred-items.md` instead. `ruff check .` and `uv run mypy` both pass cleanly repo-wide; `ruff format --check` scoped to `src tests scripts` (the actual Python surface, matching what this plan's own tasks touch) passes cleanly.
- **Files modified:** none (deferred-items.md is a new log file, not a fix)
- **Verification:** `uv run ruff format --check src tests scripts` — "40 files already formatted" (later "42 files already formatted" after Task 3's two new test files land) — pass.

**3. [Verification evidence, not a fix] Red-then-green proofs required by acceptance criteria**
- **Found during:** Task 3
- **Action:** Per the plan's own acceptance criteria, both taxonomy-equality and warehouse-path facts were proven to fail before being trusted to pass:
  - Swapping `radio`/`other` in `dbt/dbt_project.yml`'s `channel_taxonomy` produced a clear index-diff failure (`At index 5 diff: 'other' != 'radio'`) from `test_dbt_channel_taxonomy_var_equals_settings_channels`; reverted, confirmed green.
  - Prefixing `dbt/profiles.yml`'s `dev.path` with `../` reproduced RESEARCH.md Pitfall 1's exact wrong-resolution outcome: `dbt build` errored with `_duckdb.IOException: IO Error: Cannot open file "...\IDEAS_YET_NOT_PLANNED\data\warehouse\ambo.duckdb"` — one directory ABOVE the repository root, exactly as predicted — failing both `test_profiles_dev_path_matches_settings_warehouse` and `test_warehouse_file_lands_at_settings_path`. Reverted, confirmed green.
- **Files modified:** `dbt/dbt_project.yml`, `dbt/profiles.yml` (temporarily, both reverted with `git diff` confirming zero residual change before the Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 missing-critical), 1 logged-but-not-fixed (out of scope), 1 verification exercise (no code change survives it)
**Impact on plan:** No scope creep. The gitignore fix is necessary for repo hygiene; the deferred markdown-lint issue is genuinely pre-existing and outside this plan's file scope; the red-then-green proofs are the plan's own explicitly required evidence, both reverted cleanly.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The dbt project builds green on seeds + five raw views; `make transform` is unconditional and cannot pass by finding nothing to do.
- Every raw-layer source path flows through a dbt var, unblocking plan 03-02 (staging layer, BP-D-03 renames), 03-03 (poisoned-fixture harness), 03-06 (Layer R fixture run), and Phase 6 (agency intake).
- The warehouse file is provably at `settings.paths.warehouse`, asserted by a test rather than by observation — the `dbt/.user.yml` gitignore fix keeps `git status` clean for the next plan.
- `docs/BUILD_LOG.md`'s M2 opening entry gives plan 03-02 onward the standing shed-order and never-shed reference without needing to re-derive it.
- No blockers.

---
*Phase: 03-warehouse*
*Completed: 2026-08-05*

## Self-Check: PASSED

All 9 created files verified present on disk (`dbt/dbt_project.yml`, `dbt/profiles.yml`,
5 raw model `.sql` files, 2 test files, plus `deferred-items.md`); all 3 task commit
hashes (`7dcbbcc`, `aa68796`, `4574baa`) verified present in `git log --oneline --all`.
