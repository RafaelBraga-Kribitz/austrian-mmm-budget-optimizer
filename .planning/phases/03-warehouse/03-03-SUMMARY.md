---
phase: 03-warehouse
plan: 03
subsystem: database
tags: [dbt, duckdb, warehouse, data-pipeline, testing]

# Dependency graph
requires:
  - phase: 03-warehouse (plan 01)
    provides: dbt project scaffold, committed profiles.yml (dev/test targets), five source-path-parameterized raw views over the Phase 2 synthetic CSVs
provides:
  - four staging views (stg_media_weekly, stg_outcome_weekly, stg_promo, stg_calendar_weekly) with BP-D-03's unit-neutral renames applied
  - native unique/not_null/accepted_values grain tests on all four staging models, no dbt_utils
  - the one authored home for the strict AD-043 unit-suffix singular test (dbt/tests/ad043_no_unit_suffix_columns.sql), extended by plan 03-05 for marts
  - the poisoned-fixture pytest harness (synthetic_tree_copy, _dbt_env, _run_dbt_on_tree) proving a duplicate grain key fails dbt build, reusable by plan 03-06 and Phase 6
affects: [03-04, 03-05, 03-06, phase-6-intake]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "raw-to-staging boundary is the only place a `_eur`/`_aeur` suffix may be dropped (BP-D-03)"
    - "native expression-based `unique` test as model-level `data_tests`, no `dbt_utils` package"
    - "singular test on `information_schema.columns` with `-- depends_on:` hints, since dbt cannot infer deps from a non-`ref()` query"
    - "poisoned-fixture pytest: `shutil.copytree` into `tmp_path`, corrupt one CSV, run dbt on the `test` target with `AMBO_TEST_WAREHOUSE`/`DBT_TARGET_PATH` env isolation and a `Path.as_posix()`-rendered `--vars` JSON"

key-files:
  created:
    - dbt/models/staging/stg_media_weekly.sql
    - dbt/models/staging/stg_outcome_weekly.sql
    - dbt/models/staging/stg_promo.sql
    - dbt/models/staging/stg_calendar_weekly.sql
    - dbt/models/staging/_staging__schema.yml
    - dbt/tests/ad043_no_unit_suffix_columns.sql
  modified:
    - tests/unit/test_warehouse_build.py

key-decisions:
  - "AD-043 singular test uses DuckDB's starts_with()/ends_with() functions instead of LIKE with escaped underscores -- underscore is a LIKE wildcard character, so a naive `'%_eur'` pattern would match any single char + eur, not the literal underscore; starts_with/ends_with avoid escaping entirely"
  - "accepted_values test on stg_promo.promo_flag uses the nested `arguments:` property (`arguments: {values: [0, 1]}`) rather than top-level `values:` -- dbt 1.12 flags the top-level form as a deprecation (MissingArgumentsPropertyInGenericTestDeprecation), fixed inline as a Rule 1 bug before it became a future-version break"
  - "poisoned-fixture duplicate row is the first data row of the copied s_a/media_weekly.csv, appended verbatim -- an exact duplicate (week_start, channel) pair under the constant 'P-SA' layer literal, matching the plan's concrete-form discretion under D-11"
  - "negative-test error-marker guard checks for 'Compilation Error', 'Parsing Error', 'IO Error', 'No such file' -- distinguishes a red exit caused by the intended unique-test failure from one caused by a broken fixture path or JSON malformation (T-03-09)"

patterns-established:
  - "Pattern 3 applied: dbt's bundled unique test accepts a composite SQL expression as column_name, no dbt_utils needed -- reused identically for marts in plan 03-05"

requirements-completed: []  # REQ-grain-and-windows already marked [x] complete (owner Phase 6, contributing Phases 2,3) prior to this plan; not re-invoked, matching 02-02/02-09 precedent for contributing-only requirements

coverage:
  - id: D1
    description: "Four staging views (stg_media_weekly, stg_outcome_weekly, stg_promo, stg_calendar_weekly) with BP-D-03 unit-neutral renames, no dedup construct anywhere"
    requirement: "REQ-grain-and-windows"
    verification:
      - kind: integration
        ref: "uv run dbt build --project-dir dbt --profiles-dir dbt (33 PASS, 0 ERROR)"
        status: pass
      - kind: other
        ref: "duckdb query: stg_media_weekly=2028 rows/6 channels, stg_outcome_weekly=338, stg_promo=338, stg_calendar_weekly=470"
        status: pass
    human_judgment: false
  - id: D2
    description: "Native unique/not_null/accepted_values grain tests on all four staging models, every model and column described, no dbt_utils package"
    verification:
      - kind: integration
        ref: "uv run dbt build --project-dir dbt --profiles-dir dbt (23 data tests, all PASS)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Strict AD-043 unit-suffix singular test with one authored home, proven red-then-green, and the raw-layer exclusion proven deliberate"
    verification:
      - kind: integration
        ref: "manual red proof: renamed stg_outcome_weekly.revenue to revenue_eur -> AD-043 test FAIL 1 naming (stg_outcome_weekly, revenue_eur); reverted -> green again"
        status: pass
      - kind: other
        ref: "duckdb query: raw_media_p keeps spend_eur/platform_revenue_eur; AD-043 candidate query on stg_/fct_/dim_ returns zero rows"
        status: pass
    human_judgment: false
  - id: D4
    description: "Poisoned-fixture harness proves a duplicate grain key fails dbt build, not merely that the unique test exists; real warehouse never touched"
    verification:
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_clean_fixture_tree_builds_green"
        status: pass
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_duplicate_grain_key_fails_dbt_build"
        status: pass
    human_judgment: false

duration: ~18min
completed: 2026-08-05
status: complete
---

# Phase 3 Plan 3: Staging Layer, AD-043 Unit-Suffix Test, and Poisoned-Fixture Proof Summary

**Four staging views with BP-D-03's unit-neutral renames, native (no-dbt_utils) grain tests plus the one authored AD-043 unit-suffix singular test, and a poisoned-fixture pytest harness that proves — by making it happen — a duplicate grain key fails `dbt build`.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-08-05
- **Tasks:** 3
- **Files modified:** 7 (6 created, 1 modified)

## Accomplishments

- Four staging views built as plain unions with BP-D-03's renames (`spend_eur`/`spend_aeur` → `spend`, `platform_revenue_eur`/`platform_conv_value` → `platform_conv_value`, `revenue_eur`/`revenue_aeur` → `revenue`), zero `distinct`/`group by`/`row_number()` anywhere — a duplicate grain key reaches the `unique` test intact.
- `_staging__schema.yml` declares native `unique` (composite-expression `column_name`), `not_null`, and `accepted_values` tests on all four models — no `dbt_utils` package, `dbt/packages.yml` absent. Every model and column carries a `description:`.
- `dbt/tests/ad043_no_unit_suffix_columns.sql` — the one authored home for the strict AD-043 rule, scanning `information_schema.columns` for any `_eur`/`_aeur`-suffixed column on a `stg_`/`fct_`/`dim_`-prefixed table. Proven red (renamed `revenue` to `revenue_eur`, got `FAIL 1` naming `stg_outcome_weekly.revenue_eur`) then green (reverted), and proven that the raw-layer exclusion is deliberate (`raw_media_p.spend_eur` survives; the test still returns zero rows).
- `tests/unit/test_warehouse_build.py` extended with `synthetic_tree_copy`, `_dbt_env`, `_run_dbt_on_tree`, and two tests: a clean-tree control (`test_clean_fixture_tree_builds_green`) and the poisoned-tree proof (`test_duplicate_grain_key_fails_dbt_build`) that appends an exact duplicate `(week_start, channel)` row and asserts the build fails specifically on `stg_media_weekly`'s `unique` test node, with no compilation/IO error string in the output and the real warehouse's mtime unchanged.

## Task Commits

1. **Task 1: Four staging models with BP-D-03 unit-neutral renames and no dedup anywhere** — `92d08d5` (feat)
2. **Task 2: Staging grain tests and the strict AD-043 unit-suffix test** — `ec2d119` (test)
3. **Task 3: The poisoned-fixture harness — prove a duplicate grain key fails the build** — `f91e405` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `dbt/models/staging/stg_media_weekly.sql` — grain week × layer × channel; union of `raw_media_p`/`raw_media_r` with unit-neutral renames, `NULL` clicks for Layer P
- `dbt/models/staging/stg_outcome_weekly.sql` — grain week × layer; union of `raw_outcome_p`/`raw_outcome_r`, `revenue_eur`/`revenue_aeur` → `revenue`
- `dbt/models/staging/stg_promo.sql` — grain week × layer; Layer P from the outcome CSV's `promo_flag`, Layer R from the separate promo calendar
- `dbt/models/staging/stg_calendar_weekly.sql` — grain week; typed passthrough of the `season_windows` seed, no date arithmetic
- `dbt/models/staging/_staging__schema.yml` — grain uniqueness/not-null/accepted-values tests plus full model/column descriptions for all four staging models
- `dbt/tests/ad043_no_unit_suffix_columns.sql` — singular test enforcing the strict AD-043 unit-suffix rule with `-- depends_on:` hints on all four staging models
- `tests/unit/test_warehouse_build.py` — poisoned-fixture harness: `synthetic_tree_copy` fixture, `_dbt_env`/`_run_dbt_on_tree` helpers, `test_clean_fixture_tree_builds_green`, `test_duplicate_grain_key_fails_dbt_build`

## Decisions Made

- **AD-043 test uses `starts_with()`/`ends_with()` instead of `LIKE` with escaped underscores.** `LIKE`'s `_` is a single-character wildcard, so a naive `'%_eur'` pattern would match any-char-plus-`eur`, not the literal underscore in `_eur`. DuckDB's `starts_with`/`ends_with` functions sidestep escaping entirely and read more directly against the plan's prose spec.
- **`accepted_values` on `stg_promo.promo_flag` uses the nested `arguments:` property.** dbt 1.12's `MissingArgumentsPropertyInGenericTestDeprecation` flagged the plan's literal top-level `values:` form as deprecated; fixed inline (Rule 1) to `arguments: {values: [0, 1]}` before it becomes a hard break in a future dbt version. Build output confirmed the deprecation warning is gone and all 33 tests still PASS.
- **Poisoned-fixture duplicate row is the copied tree's first data row, appended verbatim.** Concrete form was Claude's Discretion under D-11; the first row of `s_a/media_weekly.csv` (`2021-01-04,search_brand,...`) is an existing `(week_start, channel)` pair under the constant `'P-SA'` layer literal, so appending it verbatim produces exactly one duplicate grain key with no further construction needed.
- **Negative-test error-marker guard: `Compilation Error`, `Parsing Error`, `IO Error`, `No such file`.** These are the dbt/DuckDB error-class strings that would indicate a red exit from a broken fixture path or malformed `--vars` JSON rather than the intended `unique` test firing (T-03-09, RESEARCH.md Pitfall 4).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `accepted_values` deprecation warning on `stg_promo.promo_flag`**
- **Found during:** Task 2 (`uv run dbt build` after authoring `_staging__schema.yml`)
- **Issue:** dbt 1.12.0 emitted `MissingArgumentsPropertyInGenericTestDeprecation` for the plan's literal `accepted_values: values: [0, 1]` top-level form — arguments to generic tests are being moved under a nested `arguments:` property, and the old form will stop working in a future dbt version.
- **Fix:** Changed to `accepted_values: arguments: {values: [0, 1]}`.
- **Files modified:** `dbt/models/staging/_staging__schema.yml`
- **Verification:** Rebuilt — deprecation warning gone, `accepted_values_stg_promo_promo_flag__0__1` still PASS, 33/33 total PASS.
- **Committed in:** `ec2d119` (Task 2 commit)

### Verification evidence (not fixes)

**2. Red-then-green proof for AD-043, as required by Task 2's acceptance criteria**
- Temporarily renamed `stg_outcome_weekly`'s output column from `revenue` to `revenue_eur` in both union branches.
- `dbt build` reported `FAIL 1 ad043_no_unit_suffix_columns`; a direct DuckDB query confirmed the exact failing row: `('stg_outcome_weekly', 'revenue_eur')`.
- Reverted; `git diff` confirmed zero residual change; rebuilt — 33/33 PASS.

**3. Red-then-green proof for the raw-layer exclusion control**
- With the build green, queried `information_schema.columns` directly: `raw_media_p` still exposes `spend_eur` and `platform_revenue_eur` (the raw layer is untouched — a typed passthrough, per plan 03-01), while the same AD-043 candidate query scoped to `stg_`/`fct_`/`dim_` tables returns zero rows.
- Proves the `stg_`/`fct_`/`dim_` prefix filter is deliberately excluding the raw layer, not accidentally passing because no suffix exists anywhere.

**4. Poisoned-fixture negative-test node-name confirmation (Task 3)**
- Ran the poisoned build manually (outside pytest) before finalizing the assertion string: confirmed the actual dbt-generated test node name is `unique_stg_media_weekly__cast_week_start_as_varchar_layer_channel_`, which contains the literal substring `unique_stg_media_weekly` asserted in `test_duplicate_grain_key_fails_dbt_build`. Output showed `FAIL 1 unique_stg_media_weekly__cast_week_start_as_varchar_layer_channel_`, returncode 1, no compilation/IO error string present.

---

**Total deviations:** 1 auto-fixed (1 bug), 3 verification exercises (no code change survives the two red-then-green cycles; the fourth is a manual pre-check of the pytest assertion string)
**Impact on plan:** No scope creep. The `accepted_values` fix is necessary to keep the build clean of a deprecation that would eventually break; the red-then-green proofs are the plan's own explicitly required evidence.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Four staging views build green with BP-D-03's renames applied; `stg_media_weekly` carries exactly 2028 rows, three layers, six channels (never `other`); offline-channel NULLs are preserved (not coerced to 0), confirmed live for `print_regional`/`P-SA`/`2021-01-04`.
- The AD-043 rule has exactly one authored home (`dbt/tests/ad043_no_unit_suffix_columns.sql`) with `-- depends_on:` hints on all four staging models; plan 03-05 extends this same file with mart hints rather than restating the rule.
- The poisoned-fixture harness (`synthetic_tree_copy`, `_dbt_env`, `_run_dbt_on_tree`) is generic over any source tree and any `--vars` override, ready for plan 03-06's Layer R fixture run (swap `data_synthetic_path` for `data_real_anon_path`, flip `layer_r_present`) and Phase 6's intake tests without modification.
- `make test` (291 passed) and `make lint`'s Python-surface scope (`ruff check .`, `mypy`, `ruff format --check src tests scripts`) are all clean. `make lint`'s whole-repo `ruff format --check .` still fails on the same 4 pre-existing `.planning/phases/{02,03}-*/{PATTERNS,RESEARCH}.md` files logged in `deferred-items.md` from plan 03-01 — untouched by this plan's three tasks, confirmed out of scope again this session.
- No blockers.

---
*Phase: 03-warehouse*
*Completed: 2026-08-05*

## Self-Check: PASSED

All 7 created/modified files verified present on disk (4 staging `.sql` models,
`_staging__schema.yml`, `ad043_no_unit_suffix_columns.sql`,
`tests/unit/test_warehouse_build.py`); all 3 task commit hashes (`92d08d5`,
`ec2d119`, `f91e405`) verified present in `git log --oneline --all`.
