---
phase: 03-warehouse
plan: 04
subsystem: database
tags: [dbt, duckdb, warehouse, contract, data-pipeline, testing]

# Dependency graph
requires:
  - phase: 03-warehouse (plan 03)
    provides: four staging views (stg_media_weekly, stg_outcome_weekly, stg_promo, stg_calendar_weekly) with BP-D-03 unit-neutral renames, native grain tests, AD-043 unit-suffix test, poisoned-fixture pytest harness (synthetic_tree_copy, _dbt_env, _run_dbt_on_tree)
provides:
  - fct_mmm_input — the single model input contract (AD-030), week x layer grain, exactly seventeen columns in the binding 03_MODULES section 8/1.3 order, materialized as a table
  - dbt-enforced columns-only contract (contract: {enforced: true}) on fct_mmm_input, proven red-then-green against three drift shapes (type mismatch, missing column, extra column)
  - AD-040 (seed-derived gapless spine), AD-041 (value ranges), AD-042 (three-layer revenue reconciliation) singular tests, all proven to fire on a poisoned fixture then reverted
  - two new pytest tests (test_mart_revenue_matches_simulator_csv_sums, test_weekly_spine_is_gapless_and_ascending) as an independent Python-side check against literal planning-time-verified sums
affects: [03-05, 03-06, 03-07, 03-08, phase-4]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "columns-only dbt model contract (contract: {enforced: true} + columns:/data_type:, no constraints: block) -- DuckDB's constraint-DDL support is unconfirmed per adapter, so grain uniqueness stays an ordinary generic test"
    - "jinja loop over var('channel_taxonomy') generates both the pivot aggregates and the final select's spend_<channel> casts -- never hand-written per-channel SQL, so taxonomy reordering cannot silently reorder mart columns without the loop reflecting it"
    - "AD-040 spine test derives expected weeks from the mart's own per-layer min/max bounds anti-joined against stg_calendar_weekly -- empty-layer-safe by construction (no bounds row means no expected row means no false gap)"
    - "AD-042 CSV union built by a jinja loop over the same scenario/layer pair list raw_outcome_p.sql established -- never a third hand-copied list of (dir, layer) pairs"
    - "red-then-green proof for a value that both the mart AND a singular test's own CSV read would source from the same perturbed file: build the mart from a clean tree first, THEN perturb the CSV, THEN re-run only the singular test node (--select) so the mart's stored values and the test's live CSV read diverge"

key-files:
  created:
    - dbt/models/marts/fct_mmm_input.sql
    - dbt/models/marts/_fct_mmm_input__schema.yml
    - dbt/tests/ad040_gapless_week_spine.sql
    - dbt/tests/ad041_value_ranges.sql
    - dbt/tests/ad042_revenue_reconciliation.sql
  modified:
    - tests/unit/test_warehouse_build.py

key-decisions:
  - "AD-042's red-then-green proof cannot perturb a CSV value in the same tree copy the mart is about to be built from -- both the mart's build and the test's own inline CSV read would see the identical perturbed value and stay in sync, producing a false green. Fixed by building the mart from a clean tree first, perturbing the CSV afterward, then re-running only the ad042_revenue_reconciliation test node (--select) against the already-materialized table -- this is what actually exercises drift between a stored aggregate and a live reconciliation source."
  - "itertools.pairwise(weeks) used instead of zip(weeks, weeks[1:], strict=True) in test_weekly_spine_is_gapless_and_ascending -- strict=True raises ValueError by construction for any deliberately-offset pairwise zip (the second iterable is always one element shorter), so it was never the correct tool here despite ruff's B905 nudging toward an explicit strict= argument."
  - "The plan's own <verify> block for Task 1 asserts a count of 2 rows at week_start = 2022-01-03 (P-SB and P-SC sharing that Monday); the committed s_a/outcome_weekly.csv also has a row on that date (P-SA spans 2021-2023, comfortably including it), so the correct built mart returns 3, not 2. Verified this is a factual error in the plan's illustrative literal, not a modeling defect: P-SB and P-SC's rows on that date remain two separate, non-merged rows as the surrounding must_haves text actually requires, and P-SA's third row is expected given its own date range."

patterns-established:
  - "Pattern 2 applied: columns-only contract with model + per-column descriptions, no constraints: block -- reused identically for dim_layer and fct_platform_reported if plan 03-05 exercises D-07's secondary-mart contracts"
  - "Pattern 4 applied: AD-042 singular test with abs-difference tolerance and jinja-looped CSV union -- the scenario_layers loop shape now has two independent authors (raw_outcome_p.sql, ad042_revenue_reconciliation.sql) agreeing on the same three (dir, layer) pairs"

requirements-completed: []  # REQ-q1-truth-recovery / REQ-grain-and-windows remain Phase 5/6-owned per REQUIREMENTS.md traceability; Phase 3 is contributing only, matching 03-01/03-02/03-03 precedent

coverage:
  - id: D1
    description: "fct_mmm_input built as a contract-enforced table, week x layer grain, exactly 17 columns in the binding order, 338 rows (156/104/78 per P-SA/P-SB/P-SC), spend_other exactly 0.0 on every row, no NULL spend"
    requirement: "REQ-grain-and-windows"
    verification:
      - kind: integration
        ref: "uv run dbt build --project-dir dbt --profiles-dir dbt (56 PASS, 0 ERROR)"
        status: pass
      - kind: other
        ref: "duckdb query: 338 rows, 17 columns in order, per-layer counts 156/104/78, spend_other<>0.0 count=0, all spend columns NULL count=0"
        status: pass
    human_judgment: false
  - id: D2
    description: "dbt-enforced columns/data_type contract on fct_mmm_input, proven to reject a type mismatch, a missing declared column, and an extra declared column, each reverted to green"
    verification:
      - kind: integration
        ref: "manual red-then-green: revenue declared integer (mismatch) -> exit 1; spend_other removed from columns (missing) -> exit 1; spend_bogus_extra_column added (extra) -> exit 1; each reverted -> dbt build exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "AD-040 gapless seed-derived spine and AD-041 value-range singular tests, proven to fire on a poisoned fixture"
    verification:
      - kind: integration
        ref: "dbt build (ad040_gapless_week_spine, ad041_value_ranges both PASS on clean data)"
        status: pass
      - kind: integration
        ref: "manual red-then-green: interior week deleted from tmp-copied s_a/outcome_weekly.csv -> ad040_gapless_week_spine FAIL 1, exit 1; reverted -> exit 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "AD-042 three-layer revenue reconciliation (abs-diff <= 1e-6) as a dbt singular test plus an independent Python-side check against three literal sums verified at planning time"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: integration
        ref: "dbt build (ad042_revenue_reconciliation PASS)"
        status: pass
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_mart_revenue_matches_simulator_csv_sums"
        status: pass
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_weekly_spine_is_gapless_and_ascending"
        status: pass
      - kind: integration
        ref: "manual red-then-green: mart built from clean tmp tree, then revenue_eur perturbed by 1.0 in the same tree, then ad042_revenue_reconciliation re-run in isolation -> FAIL 1, exit 1; reverted -> exit 0"
        status: pass
    human_judgment: false

duration: ~18min
completed: 2026-08-05
status: complete
---

# Phase 3 Plan 4: fct_mmm_input Contract, AD-040/041/042 Test Set Summary

**`fct_mmm_input` — the frozen single model input contract — built as a dbt-enforced-schema table (338 rows x 17 columns, week x layer grain) with AD-040 seed-derived spine, AD-041 range, and AD-042 three-layer revenue reconciliation tests, each proven to fail on a poisoned fixture before being trusted green.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-08-05
- **Tasks:** 3
- **Files modified:** 6 (5 created, 1 modified)

## Accomplishments

- `fct_mmm_input` built via a jinja-pivoted `media_pivot` CTE (one aggregate per `var('channel_taxonomy')` entry) joined to a `base` CTE (outcome drives the grain, inner-joined to promo/calendar, left-joined to the pivot with zero-fill) — zero hand-written per-channel SQL anywhere in the model.
- `_fct_mmm_input__schema.yml` declares `contract: {enforced: true}` with all seventeen columns' `name`/`data_type`, a model-level `unique` grain test, `not_null` on every column, `accepted_values` on `promo_flag`, and a `description:` on the model and every column — the single normative home D-08 requires.
- Three red-then-green contract-drift proofs, each run then reverted: `revenue` declared `integer` against a `double` SELECT (type mismatch), `spend_other` removed from the declared columns while still selected (missing column), and a bogus `spend_bogus_extra_column` declared but never selected (extra column) — all three produced a DuckDB-level `assert_columns_equivalent` compilation error and a non-zero `dbt build` exit; all three reverted to a clean green build.
- `ad040_gapless_week_spine.sql` anti-joins each layer's own min/max `week_start` bounds (from `fct_mmm_input`) against `stg_calendar_weekly`, with zero week arithmetic — seed-derived per D-15, empty-layer-safe because an empty layer contributes no bounds row.
- `ad041_value_ranges.sql` is a labeled singular test covering `revenue <= 0` and all seven `spend_<channel> < 0` predicates, jinja-looped over the taxonomy var.
- `ad042_revenue_reconciliation.sql` reconciles `fct_mmm_input`'s per-layer revenue sum against the three synthetic CSVs' `revenue_eur` sums (`abs(diff) <= 1e-6`, never float equality), with the three-way CSV union generated by the same `scenario_layers` jinja loop shape `raw_outcome_p.sql` already established.
- `tests/unit/test_warehouse_build.py` extended with `test_mart_revenue_matches_simulator_csv_sums` (three literal sums — P-SA 14893565.459516, P-SB 9794127.034897, P-SC 6992687.768258 — plus row counts 156/104/78, verified independently of the dbt test's own CSV read) and `test_weekly_spine_is_gapless_and_ascending` (uniform seven-day step across all three layers, via `itertools.pairwise`).
- Two more red-then-green proofs, both run against tmp-copied synthetic trees and reverted: an interior week deleted from `s_a/outcome_weekly.csv` failed `ad040_gapless_week_spine` naming the missing week; a `revenue_eur` value perturbed by 1.0 (after the mart was already built from the clean tree, then only the singular test node re-run) failed `ad042_revenue_reconciliation`, printing the offending layer and a delta of `1.0`.

## Task Commits

1. **Task 1: fct_mmm_input — the jinja-pivoted week x layer modeling matrix** — `9d75549` (feat)
2. **Task 2: The enforced contract, its grain and range tests, and the type-mismatch proof** — `739d3b5` (test)
3. **Task 3: AD-040 seed-derived gapless spine and AD-042 three-layer reconciliation** — `8f4fdca` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `dbt/models/marts/fct_mmm_input.sql` — week x layer modeling matrix, 17-column binding order, jinja-pivoted spend columns, zero-filled absent channels
- `dbt/models/marts/_fct_mmm_input__schema.yml` — enforced columns-only contract, grain uniqueness test, full descriptions
- `dbt/tests/ad040_gapless_week_spine.sql` — seed-derived gapless spine singular test, empty-layer-safe
- `dbt/tests/ad041_value_ranges.sql` — revenue/spend range singular test, jinja-looped, labeled failures
- `dbt/tests/ad042_revenue_reconciliation.sql` — three-layer revenue reconciliation singular test, abs-diff tolerance
- `tests/unit/test_warehouse_build.py` — two new tests: `test_mart_revenue_matches_simulator_csv_sums`, `test_weekly_spine_is_gapless_and_ascending`

## Decisions Made

- **AD-042's red-then-green proof required building the mart before perturbing the CSV, not perturbing then building.** Both the model's own build and the singular test's inline `read_csv_auto` read from the exact same tree copy — perturbing the CSV before the first build would move both sides identically and never surface a discrepancy. The correct proof builds the full project against a clean tree (materializing `fct_mmm_input` with the original totals), perturbs the CSV afterward, then re-runs only `ad042_revenue_reconciliation` with `--select` against the already-built table, so the mart's stored aggregate and the test's live CSV read genuinely diverge.
- **`itertools.pairwise` instead of `zip(..., strict=True)`** for the spine's consecutive-gap check — `strict=True` unconditionally raises for a self-offset `zip(seq, seq[1:])` pattern, since the second sequence is always one element shorter by construction; it was never the right tool for this loop shape.
- **The plan's Task 1 `<verify>` block's literal `count == 2` assertion for `week_start = 2022-01-03` does not match the committed data** — P-SA's own 2021-2023 span also includes that Monday, so the correct count is 3, not 2. Confirmed via direct inspection of `data/synthetic/s_a/outcome_weekly.csv` (which has a row on `2022-01-03`) that this is a factual error in the plan's illustrative acceptance-criterion literal, not a defect in the model: P-SB and P-SC's rows on that date remain two distinct, non-merged rows exactly as the surrounding `must_haves` prose requires, and the model was verified correct against every other stated criterion (row counts, column order, spend_other zero-fill, no-NULL-spend, no-literal-channel-name).

## Deviations from Plan

### Verification evidence (not fixes)

**1. Plan's Task 1 verify-script literal count discrepancy at week_start = 2022-01-03**
- The plan's automated `<verify>` block asserts `select count(*) from fct_mmm_input where week_start = DATE '2022-01-03'` returns 2. The built mart returns 3.
- Root cause: P-SA's committed `outcome_weekly.csv` spans 2021-01-04 through 2023-12-25 (156 weeks, 3 years), which necessarily includes 2022-01-03 — confirmed directly in the source CSV (`grep "2022-01-03" data/synthetic/s_a/outcome_weekly.csv` returns a row).
- This is not a modeling defect: the frontmatter's `must_haves.truths` describes the same fact correctly ("P-SB and P-SC both begin on 2022-01-03... the grain is the (week_start, layer) pair... never merge") without claiming P-SA is excluded from that date. Verified all other Task 1 acceptance criteria pass exactly as written (338 rows, 17 columns in binding order, per-layer counts 156/104/78, `spend_other` zero everywhere, zero NULL spend, zero literal channel names outside the jinja loop).
- No code change made; documented here per Rule 1's "found a bug, verified, moved on" discipline applied to a planning-artifact error rather than a code defect.

**2. AD-042/AD-040 red-then-green proof mechanics (Task 3), not scripted as permanent pytest fixtures**
- Per the plan's `<action>` text ("recorded in the plan SUMMARY," reusing the `synthetic_tree_copy`-style pattern from plan 03-03 rather than adding new committed pytest tests for the perturbation proofs themselves), both proofs were run manually against tmp-copied synthetic trees using the same `AMBO_TEST_WAREHOUSE`/`DBT_TARGET_PATH` isolation pattern `tests/unit/test_warehouse_build.py` already establishes, then reverted. Full commands and exit codes captured above under Accomplishments.

---

**Total deviations:** 0 code fixes; 2 verification-evidence notes (a planning-literal discrepancy confirmed harmless, and the manual red-then-green proof mechanics)
**Impact on plan:** No scope creep, no code weakened. All must-have truths, prohibitions, and acceptance criteria satisfied; the one plan-text literal error was verified not to indicate a modeling problem.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `fct_mmm_input` is now the frozen model input contract (AD-030): 338 rows, 17 columns, contract-enforced, all five gates (three contract-drift shapes, AD-040 spine gap, AD-042 reconciliation perturbation) proven to fire before being trusted green. Per the ROADMAP Phase 3 rollback rule, any schema change to this mart after Phase 4 begins is now an ADR-worthy contract break.
- `dbt build --project-dir dbt --profiles-dir dbt` is green with 56 PASS / 0 ERROR (1 seed, 1 table model, 45 data tests, 9 view models).
- `uv run pytest tests/unit/test_warehouse_build.py -q` is green (6 passed).
- `make test` (293 passed) is green; `make lint`'s Python-surface scope (`ruff check .`, `mypy`, `ruff format --check src tests scripts`) is clean. `make lint`'s whole-repo `ruff format --check .` still fails on the same 4 pre-existing `.planning/phases/{02,03}-*/{PATTERNS,RESEARCH}.md` files logged in `deferred-items.md` — untouched by this plan's three tasks, confirmed out of scope again this session.
- `dim_layer.channels_present` (D-13/D-14, plan 03-05) is the next consumer of this mart's column contract and the taxonomy var; the `_fct_mmm_input__schema.yml` contract is ready to be cited by path from `docs/MODULE_CONTRACTS.md` and derived from directly by `db.py` (plan 03-07).
- No blockers.

---
*Phase: 03-warehouse*
*Completed: 2026-08-05*

## Self-Check: PASSED

All 6 created/modified files verified present on disk (`fct_mmm_input.sql`,
`_fct_mmm_input__schema.yml`, `ad040_gapless_week_spine.sql`,
`ad041_value_ranges.sql`, `ad042_revenue_reconciliation.sql`,
`tests/unit/test_warehouse_build.py`); all 3 task commit hashes (`9d75549`,
`739d3b5`, `8f4fdca`) verified present in `git log --oneline --all`.
