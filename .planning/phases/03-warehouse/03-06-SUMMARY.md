---
phase: 03-warehouse
plan: 06
subsystem: database
tags: [dbt, duckdb, warehouse, contract, data-pipeline, testing, layer-r, fixture]

# Dependency graph
requires:
  - phase: 03-warehouse (plan 05)
    provides: dim_layer with source-presence-derived channels_present, the channels_present_both_directions test shape AD-044 inherits, and the ad043_no_unit_suffix_columns.sql hint-extension pattern
provides:
  - fct_platform_reported — the third contract-enforced mart (D-07, SPEC-03 section 3), grain week x layer x channel, frozen Layer P surface with the D-24 clicks-at-M4 pre-declaration, offline-channel NULLs preserved unchanged
  - ad044_layer_r_channel_presence — AD-044 shipped dormant, gated independently on intake_manifest_present so it does not collide with this plan's own layer_r_present fixture run; true branch unproven text, documented as such
  - the layer_r_present jinja branch executed end-to-end for the first time in the project's history, against tests/fixtures/real_anon_fake/ — a small, obviously-fake fixture — proving raw/staging/marts, every contract, and AD-040/041/043/both-directions green on a four-layer warehouse
  - test_layer_r_branch_builds_green_against_fixture — the pytest proof, isolated to a tmp warehouse, asserting dim_layer's 4th row, fct_mmm_input's 350-row/spend_other>0 shape, and fct_platform_reported's 2064-row count
affects: [03-07, 03-08, 03-09, phase-6, phase-8]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "straight column projection with zero aggregation/coalescing as the mechanism that preserves an upstream NULL unchanged -- fct_platform_reported never coalesces platform_conversions/platform_conv_value/impressions, so a platform-absent channel stays structurally distinct from a platform-reported-zero channel (AGENTS T-8)"
    - "jinja-conditional dormant singular test, two-branch shape: a zero-row false branch that compiles and passes inert, a symmetric-difference (full outer join) true branch that is written but has never executed -- the shape a manifest-gated test takes before its manifest exists (BP-D-05, T-203 AC-1)"
    - "a second, independent dbt var (intake_manifest_present) gates a test's true branch separately from the var (layer_r_present) that gates the data path it reads -- lets a fixture run exercise the data path now without a parse-time failure from a seed a later phase owns"
    - "--warn-error (CLI flag, not a project setting) as the one-time proof mechanism for a missing-ref gate: dbt-core's default behavior for a ref() naming a nonexistent node is a WARNING plus silent node exclusion from the DAG, and dbt build itself still exits 0 -- only --warn-error converts it into a hard Compilation Error naming the missing node"

key-files:
  created:
    - dbt/models/marts/fct_platform_reported.sql
    - dbt/models/marts/_fct_platform_reported__schema.yml
    - dbt/tests/ad044_layer_r_channel_presence.sql
    - tests/fixtures/real_anon_fake/media_weekly.csv
    - tests/fixtures/real_anon_fake/outcome_weekly.csv
    - tests/fixtures/real_anon_fake/promo_calendar.csv
    - tests/fixtures/real_anon_fake/README.md
  modified:
    - dbt/tests/ad043_no_unit_suffix_columns.sql
    - tests/unit/test_warehouse_build.py

key-decisions:
  - "fct_platform_reported's model-level description carries the full D-24 pre-declaration in three parts (frozen six-column Layer P surface, clicks arriving at M4, that addition being a planned amendment rather than an ADR-worthy break) -- Phase 8 builds DC-702 against this frozen surface during the drop-blocked window and must not be surprised by a seventh column."
  - "AD-044 gated on intake_manifest_present, never on layer_r_present -- the plan's own design point, restated here because it is what let this plan's D-20 fixture run set layer_r_present true without also needing Phase 6's intake_channels seed to exist. dbt/seeds/intake_channels.csv deliberately not created."
  - "The plan's own acceptance criterion ('setting intake_manifest_present to true without the seed present makes dbt build fail at parse time') does not hold under dbt's default CLI behavior -- a missing ref() is a WARNING plus silent node exclusion, and dbt build exits 0. Verified directly (dbt parse --no-partial-parse --debug) rather than assumed. The actual proof requires the standard --warn-error CLI flag, which converts the same condition into a hard Compilation Error naming intake_channels and a non-zero exit. This is a proof-mechanism clarification, not a weakened gate: no project default was changed, and the missing-node condition is exactly as real either way -- --warn-error only changes whether dbt's own exit code reports it. Recorded in the test file's own header comment as the parse-time gate proof Phase 6 must reproduce."
  - "Fixture fabricated solely from the SPEC-02 section 5.2 taxonomy and BP-D-03 column names, per AGENTS A-4: twelve consecutive ISO Mondays from 2024-01-01 (verified present in the committed season_windows.csv seed, so the gapless-spine test passes for layer R with no special-casing), three channels (search_brand, meta, other -- other is the Layer-R-only channel under BP-D-04, chosen deliberately to prove spend_other becomes nonzero and channels_present lists it), every value a round constant identical across all twelve weeks per channel/metric. No value is derived from, shaped by, or proportional to anything real."
  - "requirements mark-complete not invoked for REQ-q1-truth-recovery -- it is Phase-5-owned per REQUIREMENTS.md's traceability table and was already marked Complete during Phase 2's M1 close, before this plan ran; re-invoking would be a no-op. Matches 03-01/03-02/03-04's precedent for a phase-owned-elsewhere requirement."

patterns-established:
  - "Pattern 2 (columns-only enforced contract) applied a third time to fct_platform_reported -- confirms the pattern generalizes across all three marts, not just the first two."
  - "The dormant-test shape (jinja-conditional, inert false branch, unproven-but-written true branch, header comment stating plainly that the true branch has never executed) is now the template Phase 6 follows when it activates AD-044 and needs to add its own new-code verification rather than assuming this plan already proved it."

requirements-completed: []  # REQ-q1-truth-recovery is Phase-5-owned; already marked Complete during Phase 2's M1 close (see key-decisions), not re-invoked here -- matches 03-01/03-02/03-04 precedent.

coverage:
  - id: D1
    description: "fct_platform_reported built as a contract-enforced table, grain week x layer x channel, exactly six columns in order (week_start, layer, channel, platform_conversions, platform_conv_value, impressions), 2028 rows, offline-channel platform NULLs preserved (print_regional platform_conversions NULL on 338 rows, never coerced to 0), model description carrying the full D-24 pre-declaration"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: integration
        ref: "uv run dbt build --project-dir dbt --profiles-dir dbt (71 PASS, 0 ERROR, including fct_platform_reported's grain unique test)"
        status: pass
      - kind: other
        ref: "duckdb query: 2028 rows, 6 columns in order, print_regional platform_conversions NULL count=338 (>0), print_regional platform_conversions=0 count=0"
        status: pass
    human_judgment: false
  - id: D2
    description: "AD-044 present and dormant, gated on intake_manifest_present independently of layer_r_present, without dbt/seeds/intake_channels.csv existing; header comment states both required design points plus the parse-time gate proof; dbt build passes with ad044_layer_r_channel_presence named PASS"
    verification:
      - kind: integration
        ref: "dbt build --select ad044_layer_r_channel_presence (1 of 1 PASS)"
        status: pass
      - kind: integration
        ref: "manual proof (recorded in key-decisions and the test file's header): rm -rf dbt/target then dbt build --vars intake_manifest_present=true --warn-error -> Compilation Error naming 'intake_channels' node, exit 2; without --warn-error, same vars -> WARNING only, exit 0 (dbt-core default); dbt/seeds/intake_channels.csv confirmed absent throughout"
        status: pass
    human_judgment: false
  - id: D3
    description: "The layer_r_present branch executed end-to-end against tests/fixtures/real_anon_fake/ -- one dbt build with layer_r_present true and data_real_anon_path pointed at the fixture builds every raw/staging/mart model, every contract, and AD-040/041/043/both-directions green on a four-layer warehouse; dim_layer's 4th row reads weeks=12, monetary_unit=aEUR, source_tag=REAL-ANON, channels_present='search_brand,meta,other'; fct_mmm_input reaches 350 rows (12 layer R) with spend_other>0 and the other four taxonomy channels exactly 0.0 on every layer R row; fct_platform_reported reaches 2064 rows; the real warehouse's mtime is unchanged"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_warehouse_build.py::test_layer_r_branch_builds_green_against_fixture"
        status: pass
      - kind: other
        ref: "uv run pytest tests/unit/test_warehouse_build.py tests/unit/test_repo_layout.py tests/unit/test_line_endings.py -q (14 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The fixture is obviously fake and leak-scan clean: media_weekly.csv 37 lines, outcome_weekly.csv and promo_calendar.csv 13 lines each, all LF-only, README.md states the fabricated nature; uv run python scripts/leak_scan.py exits 0 with the fixture committed"
    verification:
      - kind: other
        ref: "wc -l on all three CSVs matched the plan's literal line counts; a Python byte-scan confirmed zero carriage-return bytes across all four fixture files; uv run python scripts/leak_scan.py exit 0"
        status: pass
    human_judgment: false

duration: ~18min
completed: 2026-08-06
status: complete
---

# Phase 3 Plan 6: fct_platform_reported, Dormant AD-044, and the Layer R Fixture Run Summary

**The third contract-enforced mart (`fct_platform_reported`, frozen Layer P surface with the D-24 `clicks`-at-M4 pre-declaration), AD-044 shipped dormant and gated independently of `layer_r_present`, and — the plan's own point — the `layer_r_present` jinja branch executed end-to-end for the first time against a small, obviously-fake fixture, proving a four-layer warehouse builds green before Phase 6 ever flips the flag for real.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-08-06T08:31:20Z (Task 1 commit)
- **Completed:** 2026-08-06T08:48:53Z (Task 3 commit)
- **Tasks:** 3
- **Files modified:** 9 (7 created, 2 modified)

## Accomplishments

- `fct_platform_reported.sql` built as a straight six-column projection of `stg_media_weekly` — no aggregation, no filtering, no coalescing — so an offline channel's NULL platform metrics survive unchanged rather than being coerced to a reported zero (AGENTS T-8). `clicks` deliberately not projected.
- `_fct_platform_reported__schema.yml` declares `contract: {enforced: true}`, six columns with `name`/`data_type`, a model-level `unique` grain test, `not_null` on the three grain columns only, and full descriptions — the model description carries all three parts of the D-24 pre-declaration (frozen surface, `clicks` at M4, planned-amendment framing).
- `ad043_no_unit_suffix_columns.sql` extended with the `fct_platform_reported` dependency hint, completing coverage of all four staging models and all three marts.
- `ad044_layer_r_channel_presence.sql` shipped in its dormant form: a jinja-conditional singular test gated on `intake_manifest_present` (default false), with a zero-row false branch and a written-but-never-executed true branch (a full-outer-join symmetric difference between `dim_layer`'s Layer R `channels_present` and the Phase-6-owned `intake_channels` seed). Header comment records both required design points plus a parse-time gate proof.
- `tests/fixtures/real_anon_fake/{media,outcome,promo_calendar}_weekly.csv` + `README.md`: twelve consecutive ISO Mondays from 2024-01-01, three SPEC-02 taxonomy channels (`search_brand`, `meta`, `other`), every value a round constant — an obviously-fake fixture authored solely from the taxonomy and BP-D-03 column names.
- `test_layer_r_branch_builds_green_against_fixture` added to `tests/unit/test_warehouse_build.py`: one isolated `dbt build` with `layer_r_present: true` and `data_real_anon_path` pointed at the fixture, asserting the full green build, `dim_layer`'s new Layer R row, `fct_mmm_input`'s 350-row/`spend_other`>0 shape, `fct_platform_reported`'s 2064 rows, and the real warehouse's untouched mtime.
- Full verification re-run at close-out: `uv run dbt build` — 72 PASS / 0 ERROR; `uv run pytest tests/unit/test_warehouse_build.py tests/unit/test_repo_layout.py tests/unit/test_line_endings.py -q` — 14 passed; `uv run python scripts/leak_scan.py` — exit 0; `uv run ruff check .` and `uv run mypy` — clean; `uv run ruff format --check src tests scripts` — clean; `make test` — 297 passed.

## Task Commits

1. **Task 1: fct_platform_reported with a frozen Layer P surface and a pre-declared Layer R extension** — `055396f` (feat)
2. **Task 2: AD-044 in its dormant form, gated independently of layer_r_present** — `55ba37a` (test)
3. **Task 3: The obviously-fake Layer R fixture and one dbt build with the flag on** — `6ead118` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `dbt/models/marts/fct_platform_reported.sql` — third contract-enforced mart, week x layer x channel grain, zero-aggregation six-column projection
- `dbt/models/marts/_fct_platform_reported__schema.yml` — enforced contract, D-24 pre-declaration, grain unique + three not_null tests
- `dbt/tests/ad043_no_unit_suffix_columns.sql` — extended with the fct_platform_reported dependency hint
- `dbt/tests/ad044_layer_r_channel_presence.sql` — AD-044 dormant, gated on intake_manifest_present, symmetric-difference true branch (unproven, documented as such)
- `tests/fixtures/real_anon_fake/media_weekly.csv` — 36 rows, 3 channels x 12 weeks, round-constant fake values
- `tests/fixtures/real_anon_fake/outcome_weekly.csv` — 12 rows, flat revenue/orders
- `tests/fixtures/real_anon_fake/promo_calendar.csv` — 12 rows, 0/1 promo flag
- `tests/fixtures/real_anon_fake/README.md` — states the fixture's fabricated nature and leak-scan coverage
- `tests/unit/test_warehouse_build.py` — `test_layer_r_branch_builds_green_against_fixture`, the D-20 proof

## Decisions Made

- **fct_platform_reported's description carries the full D-24 pre-declaration** in one place, so Phase 8's DC-702 work reads the frozen contract's own text rather than relying on this plan's SUMMARY surviving five phases.
- **AD-044 gated on `intake_manifest_present`, never `layer_r_present`** — the plan's own design, restated in the test file's header so a future reader does not need to reconstruct the reasoning from this SUMMARY alone.
- **The plan's literal parse-time-failure acceptance criterion needed a CLI-flag clarification, not a code change.** dbt-core's default response to a `ref()` naming a missing node is a WARNING plus silent exclusion of the depending node from the DAG — `dbt build` exits 0 either way. Verified directly with `dbt parse --no-partial-parse --debug` (surfaces the WARNING) and then `dbt build --warn-error` against a freshly cleared `dbt/target/` (surfaces a hard Compilation Error, exit 2, naming `intake_channels`). No dbt project setting, gate, or test was weakened or added to force this — `--warn-error` is a standard, unmodified dbt CLI flag used once for the proof itself, not committed anywhere. The gate is exactly as real either way; only the observed exit code needed the correct invocation to see it.
- **Fixture design choices**: twelve consecutive Mondays from 2024-01-01 (independently confirmed present in `dbt/seeds/season_windows.csv`), three of the seven taxonomy channels including `other` (the Layer-R-only channel under BP-D-04, chosen specifically to exercise the presence-derivation pivot), and identical round-constant values across all twelve weeks per channel — shape, not values, per AGENTS A-4.
- **`requirements mark-complete` not invoked** for `REQ-q1-truth-recovery` — already `Complete` in `.planning/REQUIREMENTS.md`'s traceability table since Phase 2's M1 close; this plan is contributing-only per that table (Phase 5-owned), matching 03-01/03-02/03-04 precedent.

## Deviations from Plan

### Verification evidence (not fixes)

**1. Task 2's literal parse-time-failure acceptance criterion required `--warn-error` to actually observe**

- The plan's Task 2 acceptance criteria state: "Setting `intake_manifest_present` to true without the seed present makes `dbt build` fail at parse time with a message naming the missing `intake_channels` node." Under dbt-core 1.12.0's default CLI behavior, this is a WARNING plus silent node exclusion — `dbt build --vars '{"intake_manifest_present": true}'` exits 0 with no error text at all (confirmed both via plain invocation and via `--debug` parse output).
- Root cause: dbt-core's default `ref()`-not-found handling downgrades what would be a hard parse error into a non-fatal warning unless `--warn-error` (a standard CLI flag) is passed, which converts every warning for that invocation into an error. This is documented dbt behavior, not a defect in the test file.
- Verified with a clean reparse (`rm -rf dbt/target` to eliminate partial-parse caching, which was itself found to mask the warning on a second invocation with unchanged vars): `dbt build --vars '{"intake_manifest_present": true}' --warn-error` reliably produces `Compilation Error ... Test 'test.ambo.ad044_layer_r_channel_presence' ... depends on a node named 'intake_channels' ... which was not found`, exit code 2.
- No code change made to the test, the project, or any gate. This is a proof-mechanism clarification recorded in both this SUMMARY and the test file's own header comment (for Phase 6's benefit), not a weakened acceptance criterion — the underlying condition (the true branch is genuinely wired to a seed that does not exist) is exactly what both the warning and the `--warn-error`-forced error report.

---

**Total deviations:** 0 code fixes; 1 verification-evidence note (a CLI-flag clarification needed to observe the plan's literal parse-time-failure criterion, with no gate, test, or threshold touched)
**Impact on plan:** No scope creep, no code weakened, no gate loosened. All must-have truths, prohibitions, and acceptance criteria satisfied; the one plan-text mechanism note was verified directly rather than assumed and is now recorded for Phase 6.

## Issues Encountered

- The `--warn-error` finding above was the only surprise; resolved by direct verification (never assumed) and documented rather than silently worked around.
- No dbt test, contract, or threshold was weakened at any point; `dbt build`, `pytest`, `ruff`, `mypy`, and `make test` were all run to green from genuinely clean state.
- The Layer R fixture is synthetic and obviously fake throughout — round constants only, authored solely from the SPEC-02 taxonomy and BP-D-03 column names, never touching real magnitudes, client identity, or anonymization factors (AGENTS A-4). The Layer R branch was never executed against a real private drop (`data/real_anon/` stayed empty this phase; AGENTS A-2).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All three D-07 marts are now contract-enforced: `fct_mmm_input` (338 rows), `dim_layer` (3 rows on the default build), `fct_platform_reported` (2028 rows) — the warehouse's mart layer is complete for Layer P.
- Phase 8's DC-702 attribution-gap module can build against `fct_platform_reported`'s frozen six-column contract during the drop-blocked window with the `clicks`-at-M4 addition already pre-declared in the model's own description — no surprise seventh column.
- AD-044 is present, dormant, and independently gated; Phase 6 must treat its true branch as unproven new code needing its own verification (stated in the test file's header) and must reproduce (or make permanent via a project `warn_error` flag) the `--warn-error` proof mechanism this plan used, or accept that a missing/renamed seed column will otherwise only warn, not fail, `dbt build`.
- The `layer_r_present` jinja branch (raw -> staging -> marts, every contract, AD-040/041/043/both-directions) has now executed green once, against `tests/fixtures/real_anon_fake/`. Phase 6 inherits a path that has run, not dead SQL exercised for the first time in the phase that also carries a permission gate, a prior freeze, and real client data.
- `dbt build --project-dir dbt --profiles-dir dbt` is green with 72 PASS / 0 ERROR (1 seed, 3 table models, 59 data tests, 9 view models).
- `uv run pytest tests/unit/test_warehouse_build.py -q` is green (10 passed); the broader `tests/unit/test_warehouse_build.py tests/unit/test_repo_layout.py tests/unit/test_line_endings.py` selection is green (14 passed).
- `make test` (297 passed) is green; `ruff check .`, `mypy`, and `ruff format --check` scoped to `src tests scripts` are all clean. `make lint`'s whole-repo `ruff format --check .` still fails on the same 4 pre-existing `.planning/phases/{02,03}-*/{PATTERNS,RESEARCH}.md` files logged in `deferred-items.md` since plan 03-01 — untouched by this plan's three tasks, confirmed out of scope again this session.
- No blockers for plan 03-07.

---
*Phase: 03-warehouse*
*Completed: 2026-08-06*

## Self-Check: PASSED

All 9 created/modified files verified present on disk (`fct_platform_reported.sql`,
`_fct_platform_reported__schema.yml`, `ad044_layer_r_channel_presence.sql`, the
three fixture CSVs, `README.md`, `ad043_no_unit_suffix_columns.sql`,
`tests/unit/test_warehouse_build.py`) plus this SUMMARY; all 3 task commit hashes
(`055396f`, `55ba37a`, `6ead118`) verified present in `git log --oneline --all`.
