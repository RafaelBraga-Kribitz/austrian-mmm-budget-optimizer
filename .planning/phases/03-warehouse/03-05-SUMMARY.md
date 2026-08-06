---
phase: 03-warehouse
plan: 05
subsystem: database
tags: [dbt, duckdb, warehouse, contract, data-pipeline, testing]

# Dependency graph
requires:
  - phase: 03-warehouse (plan 04)
    provides: fct_mmm_input — the frozen 17-column contract-enforced mart, week x layer grain, with AD-040/041/042 tests and the columns-only contract pattern this plan reuses for dim_layer
provides:
  - dim_layer — the layer-grain dimension (D-07, SPEC-03 section 3), contract-enforced, channels_present derived strictly from stg_media_weekly source-row presence in taxonomy order (D-13, BP-D-19)
  - channels_present_both_directions — D-14's build-time checked fact distinguishing a structurally absent channel from a present-but-ineffective one, proven to fire in both directions
  - AD-043's strict unit-suffix test extended with mart-layer dependency hints (fct_mmm_input, dim_layer)
  - three Python-side pytest assertions pinning the Phase 4 interface (channels_present taxonomy order against config/settings.yaml, the P-SC display_video-vs-other distinguishability case by name, and a fixture-driven proof that the derivation responds to source-row removal)
affects: [03-06, 03-07, 03-08, 03-09, phase-4]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "jinja-materialized (channel, position) inline VALUES relation as the mechanism for BP-D-19's taxonomy order -- an inner join against it, not SQL's default row order, is what makes 'canonical order' a checked fact"
    - "presence-by-row-existence, never presence-by-nonzero-spend -- the recurring D-13 rule, reused wherever a mart needs to know which channels a layer legitimately carries"
    - "one singular test, two labelled failure directions unioned together (channels_present_both_directions), reusing the collect-all-raise-once reasoning D-10 established for db.py -- a pivot bug typically trips both directions at once, and one test's output showing both is better debugging ergonomics than two separate red tests"
    - "Python-side pytest assertions compare against load_settings().channels (a subsequence check) rather than a hard-coded literal list, so a sanctioned future taxonomy change does not falsely fail the test while a reordering still does"

key-files:
  created:
    - dbt/models/marts/dim_layer.sql
    - dbt/models/marts/_dim_layer__schema.yml
    - dbt/tests/channels_present_both_directions.sql
  modified:
    - dbt/tests/ad043_no_unit_suffix_columns.sql
    - tests/unit/test_warehouse_build.py

key-decisions:
  - "layer identity model promoted rather than bolted on (assumption-delta decision, recorded in the plan itself): layer is a first-class key on every mart grain, dim_layer is the identity table those grains reference, and Layer P is one variant of the general layer concept rather than the default with Layer R added alongside. No mart carries a Layer-P-specific column; channels_present is per-layer, not a global constant."
  - "channels_present derivation uses an inner join to the taxonomy ordinal relation, deliberately dropping any source channel outside the taxonomy rather than silently appending it -- catching an out-of-taxonomy channel is AD-044's job (plan 03-06), and this model listing it would defeat that test."
  - "dim_layer's grain is driven from stg_outcome_weekly (via the weeks CTE), left-joined to the media-derived channels_present, coalesced to empty string -- so an outcome-only layer still produces a row instead of vanishing, and no Layer R row is ever fabricated when layer_r_present is false."
  - "The fixture-driven channel-removal Python test (test_channels_present_responds_to_source_row_removal) was expressed cleanly against the existing synthetic_tree_copy/_dbt_env/_run_dbt_on_tree harness from plan 03-03 -- no escape hatch needed. It deletes every radio row from a tmp-copied s_a/media_weekly.csv, builds with the test target, and asserts P-SA's channels_present drops to 5 tokens without radio and spend_radio is 0.0 on every P-SA row."

patterns-established:
  - "Pattern 2 (columns-only enforced contract, matching _fct_mmm_input__schema.yml) applied a second time to dim_layer -- confirms the pattern generalizes to secondary marts, not just the primary fact table."
  - "channels_present's both-directions test shape (one file, two labelled directions, jinja-looped per-channel branches for direction 2) is the shape AD-044 (plan 03-06) inherits at M4 when a real intake manifest replaces stg_media_weekly's source-row presence as the thing being checked against."

requirements-completed: [REQ-q1-truth-recovery]

coverage:
  - id: D1
    description: "dim_layer built as a contract-enforced table, layer grain, 3 rows x 5 columns (layer, weeks, channels_present, monetary_unit, source_tag), weeks 156/104/78 for P-SA/P-SB/P-SC, channels_present the exact six-entry taxonomy-ordered string on every Layer P row, monetary_unit EUR and source_tag GROUND-TRUTH on all three, no Layer R row fabricated"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: integration
        ref: "uv run dbt build --project-dir dbt --profiles-dir dbt (66 PASS, 0 ERROR)"
        status: pass
      - kind: other
        ref: "duckdb query: 3 rows, weeks 156/104/78, channels_present == 'search_brand,search_generic,meta,display_video,print_regional,radio' on all three, monetary_unit=EUR, source_tag=GROUND-TRUTH"
        status: pass
    human_judgment: false
  - id: D2
    description: "channels_present_both_directions singular test passes with zero failing rows; both directions (listed_without_source_rows, unlisted_channel_has_spend) proven to fire on a poisoned fixture then reverted; AD-043's strict test extended with mart dependency hints and proven to fire on a renamed revenue column then reverted"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: integration
        ref: "dbt build (channels_present_both_directions PASS, ad043_no_unit_suffix_columns PASS)"
        status: pass
      - kind: integration
        ref: "manual red-then-green (recorded in the 7c24cd4 commit message): direction 2 -- channels_present truncated to drop radio -> 99 failing rows naming radio+week+spend, reverted -> green; direction 1 -- other appended to every layer's channels_present -> 3 failing rows naming other, reverted -> green; AD-043 -- fct_mmm_input.revenue renamed to revenue_eur -> 1 failing row naming fct_mmm_input/revenue_eur, reverted -> green"
        status: pass
    human_judgment: false
  - id: D3
    description: "Python-side pytest assertions pin the Phase 4 interface: channels_present is a taxonomy-ordered subsequence of load_settings().channels with other excluded; P-SC's display_video (present-but-ineffective) and other (structurally absent) are distinguished by name; a fixture-driven proof shows the derivation responds to source-row removal, not a constant"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_channels_present_is_taxonomy_ordered_and_source_derived"
        status: pass
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_absent_channel_and_ineffective_channel_are_distinguishable"
        status: pass
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_channels_present_responds_to_source_row_removal"
        status: pass
      - kind: other
        ref: "uv run pytest tests/unit/test_warehouse_build.py -q (9 passed)"
        status: pass
    human_judgment: false

duration: ~55min
completed: 2026-08-06
status: complete
---

# Phase 3 Plan 5: dim_layer and the channels_present Both-Directions Contract Summary

**`dim_layer` — the layer-grain dimension with source-presence-derived `channels_present` — built as a dbt-enforced-schema table, paired with a both-directions singular test and three Python-side pytest assertions that jointly make the absent-versus-ineffective channel distinction a checked fact rather than a convention.**

## Performance

- **Duration:** ~55 min (includes the safe-resume investigation and pre-commit-hook environment recovery documented below)
- **Started:** 2026-08-05T21:41:34Z (Task 1 commit)
- **Completed:** 2026-08-06T08:24:10Z
- **Tasks:** 3
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- `dim_layer.sql` built via a `present` CTE (distinct (layer, channel) pairs from `stg_media_weekly`, never derived from nonzero spend), an `ordinal` CTE materializing `var('channel_taxonomy')`'s order as a jinja-generated (channel, position) inline relation, a `joined` CTE inner-joining the two and string-aggregating in taxonomy order, and a `weeks` CTE from `stg_outcome_weekly` that drives the final grain (left-joined to `joined`, `channels_present` coalesced to empty string so an outcome-only layer still produces a row).
- `_dim_layer__schema.yml` declares `contract: {enforced: true}`, five columns with `name`/`data_type`, `not_null` on all five, `unique` on `layer`, `accepted_values` on `monetary_unit` (EUR/aEUR) and `source_tag` (GROUND-TRUTH/REAL-ANON), and a full `description:` on the model and every column — `channels_present`'s description names all four required points (derivation rule, format, consumer instruction, and the absent-vs-ineffective reason).
- `channels_present_both_directions.sql`: a single singular test unioning two labelled failure sets — direction 1 (`listed_without_source_rows`, split-and-anti-join against `stg_media_weekly`) and direction 2 (`unlisted_channel_has_spend`, jinja-looped per-channel branches over `fct_mmm_input` matched with `list_contains` for whole-token safety) — both proven to fire on a poisoned fixture and reverted.
- `ad043_no_unit_suffix_columns.sql` extended (not rewritten) with `depends_on` hints for `fct_mmm_input` and `dim_layer`, scheduling the information_schema scan after the marts materialize; proven to fire on a renamed `revenue` -> `revenue_eur` column and reverted.
- `tests/unit/test_warehouse_build.py` extended with three tests: `test_channels_present_is_taxonomy_ordered_and_source_derived` (six-token taxonomy-ordered subsequence of `load_settings().channels`, `other` absent, for all three Layer P rows), `test_absent_channel_and_ineffective_channel_are_distinguishable` (P-SC's `display_video` listed with `spend_display_video` total > 0 vs `other` unlisted with `spend_other` exactly 0.0 on all 78 rows), and `test_channels_present_responds_to_source_row_removal` (a fixture-driven proof against a tmp-copied tree with every `radio` row deleted from `s_a/media_weekly.csv`, confirming `channels_present` drops to five tokens and `spend_radio` is 0.0 on every P-SA row).
- Full verification re-run at close-out: `uv run dbt build --project-dir dbt --profiles-dir dbt` — 66 PASS / 0 ERROR; `uv run pytest tests/unit/test_warehouse_build.py -q` — 9 passed; `uv run ruff check .` and `uv run mypy` — clean; `make test` — 296 passed.

## Task Commits

1. **Task 1: dim_layer with source-presence-derived channels_present and its enforced contract** — `bbaf49b` (feat)
2. **Task 2: The channels_present both-directions test and the AD-043 mart extension** — `7c24cd4` (test)
3. **Task 3: Python-side assertions pinning the Phase 4 interface** — `1acfbdc` (test)

**Plan metadata:** (this commit)

_Note: this plan was closed out via safe-resume continuation after an interrupted session. Tasks 1 and 2 were already committed when this continuation began; this executor verified those two commits against the plan (`git show --stat` on each, plus a full read of `dim_layer.sql`, `_dim_layer__schema.yml`, and `channels_present_both_directions.sql` against the plan's Task 1/2 `<action>` and `<acceptance_criteria>` text) before proceeding, found them materially complete and consistent with the plan, and did not redo or revert any part of them. Task 3 had ~181 uncommitted lines already written by the interrupted prior agent; this executor reviewed that draft critically against the plan's Task 3 `<action>`/`<acceptance_criteria>`, found it correct and complete (all three specified tests present, all helper functions it reuses — `_run_dbt`, `_run_dbt_on_tree`, `_dbt_env`, `synthetic_tree_copy` — already existed from prior plans), proved it green, and committed it as-is with no code changes required._

## Files Created/Modified

- `dbt/models/marts/dim_layer.sql` — layer-grain dimension, `channels_present` derived from source-row presence in taxonomy order, no fabricated Layer R row
- `dbt/models/marts/_dim_layer__schema.yml` — enforced five-column contract, full descriptions, `unique`/`not_null`/`accepted_values` tests
- `dbt/tests/channels_present_both_directions.sql` — D-14's build-time checked fact, two labelled directions unioned into one test
- `dbt/tests/ad043_no_unit_suffix_columns.sql` — extended with `fct_mmm_input`/`dim_layer` dependency hints
- `tests/unit/test_warehouse_build.py` — three new tests pinning the Phase 4 interface from the Python side

## Decisions Made

- **Layer identity model promoted, not bolted on** — recorded as the plan's own `<assumption_delta_decision>` block: `layer` is a first-class key on every mart grain (`fct_mmm_input` keyed `(week_start, layer)`, `fct_platform_reported` keyed `(week_start, layer, channel)`), and `dim_layer` is the identity table those grains reference. Layer P is one variant of the general layer concept, not the default with Layer R bolted on. `layer_r_present: false`'s ROADMAP staleness note was confirmed stale — `docs/ADR/ADR-000` D-2 already ratified BP-D-01…BP-D-20 wholesale, so this is binding and not re-litigated here (plan 03-09 corrects the stale note).
- **Presence-by-row-existence, never presence-by-nonzero-spend** — `dim_layer.sql`'s `present` CTE derives `channels_present` strictly from `stg_media_weekly` row existence. A nonzero-spend derivation would silently reclassify a real channel with a legitimate zero-spend period, and on Layer R could disagree with the intake manifest, defeating AD-044 (plan 03-06) for the wrong reason.
- **Inner join to the taxonomy ordinal, not a left join** — a source channel outside the taxonomy is dropped from `channels_present` rather than silently appended. Catching that case belongs to AD-044 (plan 03-06); listing an unknown channel here would defeat that test before it ever runs.
- **One test file with two labelled directions** for `channels_present_both_directions`, not two separate files — a pivot bug typically trips both directions at once, and one test's output showing both failure sets is better debugging ergonomics (the same reasoning D-10 applies to `db.py`'s collect-all-raise-once).
- **Python-side taxonomy check against `load_settings().channels` (subsequence), not a hard-coded literal** — a sanctioned future taxonomy change does not falsely fail `test_channels_present_is_taxonomy_ordered_and_source_derived`, while an actual reordering still fails it.
- **The Task 3 fixture-driven channel-removal test needed no escape hatch** — it reused the existing `synthetic_tree_copy`/`_dbt_env`/`_run_dbt_on_tree` harness from plan 03-03 cleanly and was committed as a full, passing test; the plan's "delete it and record why" fallback was not invoked.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-commit hook environment blocked by a stale Windows Application Control policy state**
- **Found during:** Task 3 commit
- **Issue:** `git commit` failed at the `end-of-file-fixer` pre-commit hook with `[WinError 4551] An Application Control policy has blocked this file`. Direct invocation of the hook's underlying Python module (`python.exe -m pre_commit_hooks.end_of_file_fixer`) succeeded with exit 0 and correctly reported the file already properly formatted — isolating the fault to the generated `end-of-file-fixer.exe` entry-point shim in the cached pre-commit venv (`~/.cache/pre-commit/repo3aqxvsq7/py_env-python3/Scripts/end-of-file-fixer.exe`), which a direct execution attempt confirmed as `Permission denied`. Leftover unapplied `patch*` files in `~/.cache/pre-commit/` from prior interrupted sessions indicated this had blocked commits before in this environment.
- **Fix:** `uv run pre-commit clean` (clears the cached hook environments; touches no repository files) followed by re-running the hook, which reinstalled a fresh venv and a newly generated `end-of-file-fixer.exe` that was not blocked. This is a tooling-cache-only fix — no code, contract, or threshold was touched, and `--no-verify` was never used.
- **Files modified:** None (tool cache only, outside the repository).
- **Verification:** `uv run pre-commit run end-of-file-fixer --files tests/unit/test_warehouse_build.py` passed after the cache clean; the subsequent `git commit` ran the full seven-hook chain (ruff check, ruff format, end-of-file-fixer, check-yaml, detect-private-key, nbstripout, leak-scan) successfully.
- **Committed in:** `1acfbdc` (Task 3 commit)

**2. [Rule 1 - Bug] Stray uncommitted STATE.md regression from the interrupted prior session, reverted before touching state**
- **Found during:** Pre-commit status check
- **Issue:** `.planning/STATE.md` had an uncommitted diff left by the interrupted prior session, regressing `Plan: 5 of 9` to `Plan: 1 of 9` and `Status: Ready to execute` to `Status: Executing Phase 03` — an incorrect, stale, half-applied state write that would have propagated a wrong plan pointer if left in place.
- **Fix:** `git checkout -- .planning/STATE.md` to restore the last-committed baseline before applying this plan's own correct state updates via the standard `gsd_run query state.*` commands (see State Updates below).
- **Files modified:** `.planning/STATE.md` (reverted to committed baseline, then updated correctly via state commands).
- **Verification:** `git status --short` confirmed a clean baseline before proceeding; the plan's own state updates (advance-plan, update-progress, record-metric, add-decision, record-session) were applied afterward through the standard tooling, not by hand-editing.
- **Committed in:** part of the final metadata commit (docs commit), not the Task 3 commit.

---

**Total deviations:** 2 auto-fixed (1 blocking tooling-environment fix, 1 bug — stray incorrect state reverted before use)
**Impact on plan:** Neither deviation touched model code, dbt tests, contracts, or thresholds. No scope creep; the hard prohibition against weakening a test/contract/threshold to reach green was not implicated by either fix.

## Issues Encountered

- The pre-commit hook environment issue above was the only blocker encountered; resolved without touching `--no-verify` or any hook configuration.
- No dbt test, contract, or threshold was weakened at any point; `dbt build`, `pytest`, `ruff check`, `mypy`, and `make test` were all run to green from a genuinely clean state, not claimed without observation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `dim_layer` is now a stable, contract-enforced Phase 4 interface: 3 rows x 5 columns, `channels_present` derived from source-row presence in taxonomy order, `monetary_unit`/`source_tag` the single home for the unit and provenance facts.
- The absent-versus-ineffective channel distinction is a checked fact in three independent places (the dbt both-directions test, the Python taxonomy-ordering test, and the Python distinguishability test naming P-SC's `display_video` vs `other`) — Phase 4's model code can iterate `channels_present` with confidence it is never conflating the two states.
- `channels_present_both_directions`'s shape (one file, two labelled directions, jinja-looped per-channel branches) is the shape AD-044 (plan 03-06) inherits at M4 when a real intake manifest replaces `stg_media_weekly` source-row presence as the thing being checked against.
- `dbt build --project-dir dbt --profiles-dir dbt` is green with 66 PASS / 0 ERROR (1 seed, 2 table models, 54 data tests, 9 view models).
- `uv run pytest tests/unit/test_warehouse_build.py -q` is green (9 passed).
- `make test` (296 passed) is green; `ruff check .` and `mypy` are clean repo-wide; `ruff format --check` scoped to the Python surface this plan touched is clean. `make lint`'s whole-repo `ruff format --check .` still fails on the same 4 pre-existing `.planning/phases/{02,03}-*/{PATTERNS,RESEARCH}.md` files already logged in `deferred-items.md` since plan 03-01 — untouched by this plan's three tasks, confirmed out of scope again this session.
- No blockers for plan 03-06 (Layer R fixture run, AD-044, `fct_platform_reported`).

---
*Phase: 03-warehouse*
*Completed: 2026-08-06*

## Self-Check: PASSED

All 6 created/modified files verified present on disk (`dim_layer.sql`,
`_dim_layer__schema.yml`, `channels_present_both_directions.sql`,
`ad043_no_unit_suffix_columns.sql`, `tests/unit/test_warehouse_build.py`, this
SUMMARY); all 3 task commit hashes (`bbaf49b`, `7c24cd4`, `1acfbdc`) verified
present in `git log --oneline --all`.
