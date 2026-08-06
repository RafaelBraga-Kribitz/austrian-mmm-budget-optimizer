---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 03
current_phase_name: warehouse
status: executing
stopped_at: Completed 03-08-PLAN.md
last_updated: "2026-08-06T09:39:21.630Z"
last_activity: 2026-08-05
last_activity_desc: Phase 03 execution started
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 28
  completed_plans: 27
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** A reviewer can verify from git history alone that the model recovered known truth before it touched real data, and that the priors preceded the results.
**Current focus:** Phase 03 — warehouse

## Current Position

Phase: 03 (warehouse) — EXECUTING
Plan: 9 of 9
Status: Ready to execute
Last activity: 2026-08-05 — Phase 03 execution started

Progress: [██████████] 96%

## Performance Metrics

**Velocity:**

- Total plans completed: 19
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 9 | - | - |
| 02 | 10 | - | - |

**Recent Trend:** No data yet.

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 20min | 3 tasks | 4 files |
| Phase 01 P02 | 8min | 3 tasks | 30 files |
| Phase 01 P03 | 13min | 3 tasks | 5 files |
| Phase 01 P04 | 12min | 3 tasks | 9 files |
| Phase 01 P05 | 8min | 2 tasks | 2 files |
| Phase 01 P06 | ~15min | 2 tasks | 4 files |
| Phase 01 P07 | 24min | 3 tasks | 8 files |
| Phase 01 P08 | ~30min | 3 tasks | 3 files |
| Phase 01 P09 | ~64min | 3 tasks | 9 files |
| Phase 02 P01 | 33min | 3 tasks | 6 files |
| Phase 02 P02 | 20min | 2 tasks | 4 files |
| Phase 02 P03 | 55min | 3 tasks | 5 files |
| Phase 02 P04 | 25min | 3 tasks | 4 files |
| Phase 02 P05 | ~35min | 2 tasks | 3 files |
| Phase 02 P06 | ~45min | 2 tasks | 3 files |
| Phase 02 P07 | 35min | 2 tasks | 3 files |
| Phase 02-ground-truth-simulator P08 | ~40min | 3 tasks | 3 files |
| Phase 02 P09 | ~40min | 3 tasks | 4 files |
| Phase 02 P10 | 20min | 3 tasks | 10 files |
| Phase 03 P01 | 15min | 3 tasks | 11 files |
| Phase 03 P02 | 18min | 2 tasks | 3 files |
| Phase 03 P03 | ~18min | 3 tasks | 7 files |
| Phase 03 P04 | 18min | 3 tasks | 6 files |
| Phase 03 P05 | 55min | 3 tasks | 5 files |
| Phase 03 P06 | 18min | 3 tasks | 9 files |
| Phase 03-warehouse P07 | 30min | 3 tasks | 3 files |
| Phase 03-warehouse P08 | 35min | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Full log in PROJECT.md. `docs/ADR/` now exists and **ADR-000 is ratified**, covering document
precedence, the twenty BP-D blueprint defaults (accepted wholesale), and the ingest cycle
deviation. The eight Group A design commitments asserted by SPEC text remain formally
unratified and are candidates for ADR-001+ as they are exercised.

- [Ingest]: Roadmap mirrors blueprint P0–P8 1:1 as Phases 1–9 — re-deriving would orphan the T-001…T-806 WBS and the traceability matrix.
- [Ingest]: All 25 REQ IDs carried verbatim; no new IDs invented for Phases 2–4.
- [2026-08-04]: All 7 ingest warnings resolved at source rather than deferred into phases — the source SPECs were contradictory independently of the ingest, so fixing the documents (not annotating the plan) was the only resolution that survives into implementation. See ADR-000 and the INGEST-CONFLICTS resolution log.
- [2026-08-04, ADR-000 D-1]: Precedence is scoped, not ranked — Charter governs goals/scope/acceptance, SPEC governs operative detail, ADR outranks both. The Charter's own passages were corrected where they restated SPEC values wrongly.
- [Phase ?]: 01-01: Audited T-001/T-003/T-012 against running probes rather than trusting the D-29 known-state table; all verdicts confirmed, with the exports/foo.csv untracked-not-ignored result clarified as correct per W5
- [Phase ?]: 01-01: git add --renormalize . implies -u; left .planning/STATE.md's pre-existing out-of-scope content edit out of the .gitattributes commit
- [Phase ?]: Charter O-3 is import-scoped, not tree-scoped: scikit-learn transitive via pymc-marketing does not violate O-3 (binding, from human checkpoint approval on 01-02)
- [Phase ?]: 134-package uv.lock count accepted as correct — RESEARCH.md's 112 baseline omitted the dev dependency group
- [Phase ?]: [Phase 1] 01-03: Owner-phase for each risk resolved via ROADMAP.md's M0-M7 to Phase 1-9 mapping table (R-1/R-6 to Phase 6, R-2/R-9 to Phase 7, R-3/R-5 to Phase 5, R-4 to Phase 8, R-7 to Phase 4, R-8/R-12 standing)
- [Phase ?]: [Phase 1] 01-03: docs/ADR/README.md updated beyond files_modified to move ADR-006 into the ratified table (Rule 2) — the README's own prior text promised this once ratified
- [Phase ?]: [Phase 1] 01-04: Settings is pydantic BaseModel not BaseSettings (BaseSettings needs the separate pydantic-settings distribution, not in SPEC-08 3, EB-030 makes adding it an ADR event); MODULE_CONTRACTS.md corrected to match plus seed -> random_seed to match MD-050/D-25 verbatim
- [Phase ?]: [Phase 1] 01-04: Added a mypy override for yaml.* instead of the types-PyYAML dev dependency -- PyYAML is already a pinned SPEC-08 3 runtime dependency, so extending the existing ignore_missing_imports pattern needs no new package and triggers no ADR
- [Phase ?]: Sampling-target EB-050 runtime strings scoped to fit-synthetic/fit-real/sensitivity (the targets that write posteriors), not the read-only downstream targets
- [Phase ?]: Implemented 13 stub Makefile targets per the plan's own explicit phase-mapping list, correcting the plan prose's miscounted 'twelve' (Rule 1)
- [Phase ?]: 01-06: Advent read as exactly 4 flagged weeks total ending at the Dec-24 week inclusive, per Guide section 1.2 (D-07)
- [Phase ?]: 01-06: Schulbeginn read as the second Monday of September (holidays package has no AT-6 school subdivision), per Guide section 1.2 (D-07)
- [Phase ?]: 01-06: No holidays import in generate_season_windows.py -- none of the five window rules needs a holiday lookup; Phase 2 simulator is the actual future consumer
- [Phase ?]: 01-07: test_forbidden_deps.py is import-scoped only, does not parse uv.lock -- follows the binding O-3 import-scope ruling from 01-02's human checkpoint (scikit-learn arrives transitively via the sanctioned pymc-marketing chain)
- [Phase ?]: 01-07: fixed working-tree-only CRLF drift in 12 already-tracked files (committed blobs were already LF-clean) discovered by test_line_endings.py; root cause is core.autocrlf=true short-circuiting a plain git checkout --, fixed via delete + git checkout HEAD --, no commit needed
- [Phase ?]: 01-07: all four D-23 architectural guards proven red-then-green on a scratch branch with zero commits ever made on it (deleted via safe git branch -d), evidence recorded in docs/BUILD_LOG.md per T-010 AC-1
- [Phase ?]: 01-08: leak-scan generic private-drop shape requires an explicit [:=] assignment operator (not bare adjacency) -- excludes this repo's own $AMBO_PRIVATE_DROP/staged/-style shell-interpolation documentation
- [Phase ?]: 01-08: .env.example excluded from the leak scanner's generic private-drop shape check only (01-02's sanctioned fictional example line); the dynamic literal-value check still covers it
- [Phase ?]: 01-08: pre-commit hook revisions pinned to verified upstream tags -- ruff-pre-commit v0.16.1, pre-commit-hooks v6.0.0, nbstripout 0.9.1; mypy deliberately not a hook (make lint already runs it)
- [Phase ?]: [Phase 1] 01-09: leak_scan.py doc-comment self-matched its own regex, fixed with an <abs-path> placeholder; scanner is never exempted from scanning its own file
- [Phase ?]: [Phase 1] 01-09: private-drop test fixtures were Windows-only absolute; now branch on sys.platform so redaction/leak-scan logic is genuinely exercised on every CI leg
- [Phase ?]: [Phase 1] 01-09: _resolve_private_drop_needles() deduplicates its three separator-form candidates -- an un-deduplicated list double-counted one real match as two Findings on POSIX, masked on Windows
- [Phase ?]: [Phase 1] 01-09: Phase 1 complete -- all six EB-060 CI jobs confirmed green with none skipped on draft PR #1 (run 30951615385); PR left in draft per D-11
- [Phase ?]: 02-01: hypothesis added to [dependency-groups] dev only (never [project] dependencies) per EB-030/O-3, ADR-007 ratified
- [Phase ?]: 02-01: SUS package-legitimacy verdict for hypothesis treated as a checker data artifact only after explicit human checkpoint approval, not researcher confidence alone
- [Phase ?]: 02-02: SimulationError promoted over 03_MODULES.md section 2.2/2.3's ValueError; exactly-adjacent bursts accepted as two distinct bursts, never merged (both recorded for docs/BUILD_LOG.md at M1 close)
- [Phase ?]: 02-02: functools.cache used instead of the plan text's literal functools.lru_cache(maxsize=None) -- behaviorally identical, required by ruff UP033
- [Phase ?]: 02-02: requirements.mark-complete not invoked for REQ-q1-truth-recovery/REQ-grain-and-windows -- both are Phase-5/6-owned per REQUIREMENTS.md traceability table; 02-01 already showed calling it here requires an immediate revert
- [Phase ?]: 02-03: spring promo-week anchors set to the spring window's own 1/3 and 2/3 index points (weeks 17,20), not hard-coded week numbers -- adapts if the spring window length ever changes (CONTEXT.md D-01)
- [Phase ?]: 02-03: radio's 2 Advent-anchored bursts authored as a lead-in burst (A-3) plus an in-Advent burst (A) -- two 3-week bursts cannot both fit inside the 4-week Advent window without overlapping
- [Phase ?]: 02-03: meta.spend.advent_factor read as 0.5(S-A)/0.9(S-B,S-C), mirroring search_generic's SIM-030 switch, since SPEC-01 section 3's meta row states no seasonal multiplier by itself but SIM-030 presupposes a 0.5 baseline
- [Phase ?]: 02-03: four online-channel cpm constants authored (not spec-given, BP-D-02): search_brand=12.0, search_generic=20.0, meta=6.0, display_video=4.0, identical across S-A/B/C
- [Phase ?]: 02-03: test_promo_week_counting_rules asserts spring-anchor presence directly plus a >=2 sanity count, not ==2 -- an unconstrained spread pick can coincidentally also land inside the spring window (observed s_b 2022), which is correct authoring-aid behavior not a bug
- [Phase ?]: 02-04: season_index(weeks, season_weights) promotes 03_MODULES.md section 2.3's signature to a (week-index frame, SeasonWeights) pair -- the five weights are SIM-002 YAML values, never hard-coded in code
- [Phase ?]: 02-04: SimulationError replaces 03_MODULES.md's implicit ValueError on every domain violation in dgp.py, consistent with 02-02's identical promotion
- [Phase ?]: 02-04: _expected_keys() reconstructs the declared week spine via date.fromisocalendar()/isocalendar() independent of the (possibly corrupted) seed file, rather than re-reading the same file being diagnosed -- plain ISO-calendar arithmetic, not a reimplementation of the five AD-020 window-classification rules
- [Phase ?]: 02-04: pyproject.toml mypy override added for pandas.* (ignore_missing_imports), same precedent as the existing yaml.* override -- pandas is a pinned runtime dependency, not a new one, so no EB-030 ADR event
- [Phase ?]: 02-05: literal floor/round swap acceptance criterion is mathematically a no-op (integer floor_eur makes round/floor commute) -- red-then-green evidence produced instead via a mean-multiplier/draw order swap (Pitfall 6's other named example)
- [Phase ?]: 02-05: generate_spend(cfg, rng, weeks) promotes 03_MODULES.md section 2.2's two-argument signature to three -- week-index frame injected since this module performs no I/O
- [Phase ?]: 02-06: generate_spend imported inside assemble_scenario's function body (not at module level) to break an A-15 import cycle -- spend_patterns.py already imports round_half_up from dgp.py
- [Phase ?]: 02-06: SIM-071 decomposition invariant enforced as a SimulationResult constructor precondition (raises in __post_init__), proven by both a perturbation test and all-scenario green audits
- [Phase ?]: 02-06: peak_week_audit records a skipped ISO year (Advent window not fully covered, e.g. S-C's 2023 half-year) under a documented sentinel (-1, True) rather than omitting it silently
- [Phase ?]: 02-06: test_assemble_zero_beta_channel_contributes_exactly_zero uses the plan's own sanctioned fallback (exact-zero plus exact five-channel-sum equality) since ScenarioConfig pins (id, weeks, seed) to the three frozen SPEC-01 section 5 triples, making a bit-identical S-B-windowed control run unconstructible
- [Phase ?]: 02-07: share_c and platform_revenue_eur computed from result.spend/result.components directly (not media's own placeholder spend_eur), per the plan's read_first sources -- numerically identical either way
- [Phase ?]: 02-07: zero-total-spend-week test zeroes only result.spend for one week and reuses components unchanged -- SIM-071's decomposition invariant re-sums components alone, so no adjustment is needed to satisfy the SimulationResult constructor precondition
- [Phase ?]: 02-07: config-not-code test uses pydantic model_copy(update=...) up the frozen ScenarioConfig/ChannelConfig/PlatformBiasParams chain instead of a direct attribute monkeypatch, since frozen=True blocks __setattr__ and model_copy does not re-run validators
- [Phase ?]: 02-08: Assumption A3 resolved -- float precision pinned via pre-normalisation through %.10g before json.dumps, not a custom JSONEncoder subclass (json's default= never fires for a native float)
- [Phase ?]: 02-08: SPEC-01 section 8's grid question required no new decision -- response_curve_at is generic over a caller-supplied grid, proven against an independent MD-082-style 1.5x recomputation
- [Phase ?]: 02-08: marginal_roas_at's a==0 branch returns 0.0 for s>=1.0, raises SimulationError for s<1.0 -- defensive only, never exercised since compute_truth rejects zero-total-spend channels first
- [Phase ?]: 02-09: Tasks 1+2 landed in a single commit (964bcf8), mirroring 02-08's precedent -- CLI, byte-stable writers and the full SIM-070..075+BP-G-02 gate runner share the _generate_scenario helper so there was no meaningful intermediate diff to split
- [Phase ?]: 02-09: validate_sim's own PASS/FAIL exit code covers only the six in-process SIM-0xx rows; BP-G-02's DELEGATED row is composed at the Makefile level (gate runner then the pytest selector), per the plan's own explicit two-line validate-sim recipe
- [Phase ?]: 02-09: zero occurrences of the literal substring 'pytest' anywhere in __main__.py (grep -c returns 0) -- the BP-G-02 evidence text names the selector without spelling the test-runner's name, satisfying Task 2's literal-substring acceptance criterion
- [Phase ?]: M1 closed: nine Layer P artifacts committed, git round-trip proven, BUILD_LOG M1 entry finalized (348min total vs 720/1440min budget/tripwire), human approved via checkpoint sign-off
- [Phase ?]: requirements mark-complete not invoked for REQ-q1-truth-recovery/REQ-grain-and-windows in 02-10 -- both Phase 5/6-owned per REQUIREMENTS.md traceability table
- [Phase ?]: 03-01: profiles.yml dev.path is the bare data/warehouse/ambo.duckdb string (no ../ prefix) per RESEARCH.md Pitfall 1's empirical CWD-relative path-resolution finding, red-then-green proven this session
- [Phase ?]: 03-01: make transform's D-17 conditional removed entirely (D-21) -- unconditional single-line dbt build recipe, matching simulate:'s bare-uv-run shape
- [Phase ?]: 03-01: dbt/.user.yml (per-machine random-UUID usage-stats file) added to .gitignore -- discovered generated during Task 1's first dbt invocation, not anticipated by the plan's own read_first note
- [Phase ?]: 03-01: REQ-dl1-reproducible-pipeline not marked complete -- Phase-9-owned per REQUIREMENTS.md traceability, Phase 3 contributing only, matching 02-02/02-09 precedent
- [Phase ?]: 03-01: whole-repo ruff format --check . failure on 4 planning markdown files (02-PATTERNS/RESEARCH.md, 03-PATTERNS/RESEARCH.md) logged to deferred-items.md as out of scope, not fixed -- ruff check/mypy pass repo-wide, ruff format scoped to src/tests/scripts passes
- [Phase ?]: 03-02: DataContractError docstring restates the AmboError redaction invariant explicitly, matching SimulationError's precedent, even though no warehouse input is private today
- [Phase ?]: 03-02: _forbidden_calls()/_forbidden_path_literals()/_py_files() are the only three detector helpers; test_only_db_module_opens_duckdb's bare-import check is inlined in the test body rather than promoted to a fourth module-level helper, per the plan's exact artifacts_this_phase_produces symbol list
- [Phase ?]: 03-02: _FORBIDDEN_DATA_PATH_PREFIXES deliberately excludes exports/ -- report/ has 03_MODULES section 10-granted legitimate access, verified live by an exports/-prefixed positive-control probe
- [Phase ?]: 03-03: AD-043 test uses DuckDB starts_with()/ends_with() instead of LIKE with escaped underscores -- underscore is a LIKE wildcard, native functions avoid escaping entirely
- [Phase ?]: 03-03: accepted_values on stg_promo.promo_flag uses the nested arguments: property -- dbt 1.12 flags the top-level values: form as a deprecation, fixed inline before it breaks in a future version
- [Phase ?]: 03-03: poisoned-fixture harness (synthetic_tree_copy, _dbt_env, _run_dbt_on_tree) proves a duplicate grain key fails dbt build by making it happen -- FAIL 1 unique_stg_media_weekly__..., real warehouse mtime unchanged
- [Phase ?]: 03-04: AD-042 red-then-green proof must build the mart from a clean tree first, then perturb the CSV, then re-run only the test node with --select -- perturbing before the first build moves both the mart and the test's own CSV read identically and never surfaces drift
- [Phase ?]: 03-04: itertools.pairwise used instead of zip(seq, seq[1:], strict=True) for the spine's consecutive-gap check -- strict=True unconditionally raises for a self-offset pairwise zip since the second sequence is always one shorter by construction
- [Phase ?]: 03-04: plan's Task 1 verify-script literal count==2 for week_start=2022-01-03 does not match committed data (P-SA also spans that date); correct count is 3, verified as a plan-text error not a modeling defect -- P-SB/P-SC remain two distinct non-merged rows as intended
- [Phase ?]: Layer identity model promoted, not bolted on: layer is a first-class key on every mart grain, dim_layer is the identity table those grains reference (plan 03-05 assumption-delta decision)
- [Phase ?]: channels_present derived strictly from stg_media_weekly source-row presence, never nonzero spend, and inner-joined to the taxonomy ordinal so out-of-taxonomy channels are dropped for AD-044 to catch later
- [Phase ?]: 03-06: fct_platform_reported built as the third contract-enforced mart, frozen Layer P surface with D-24 clicks-at-M4 pre-declaration
- [Phase ?]: 03-06: AD-044 shipped dormant, gated on intake_manifest_present independently of layer_r_present; dbt's default missing-ref behavior is a WARNING not a failure, --warn-error needed to observe the parse-time gate proof
- [Phase ?]: 03-06: layer_r_present jinja branch executed end-to-end for the first time against tests/fixtures/real_anon_fake/ (round-constant, obviously-fake data per AGENTS A-4) -- Phase 6 inherits a proven path
- [Phase ?]: 03-07: kept exactly the plan's six named db.py symbols (no seventh _valid_layers helper); the D-10 multi-violation test drives the real read_mmm_input() path via a minimal fake connection rather than a new testable helper
- [Phase ?]: 03-07: split Tasks 1/2 into two atomic commits against the same new db.py file by staging an intermediate Task-1-only version, preserving per-task commit discipline
- [Phase ?]: 03-08: ExportSpec.columns is a callable over the reader's own frame (not a stored literal list) so the mart's 17-column order stays single-homed via db.py's _contract_columns (D-08 applied to a scripts/ file)
- [Phase ?]: 03-08: ExportSpec.sort_keys doubles as the AD-050 duplicate-grain-key check's subset columns instead of a separate grain-columns field
- [Phase ?]: 03-08: _atomic_write_csv reproduced verbatim inside scripts/export_marts.py rather than imported from ambo.simulate.__main__ -- scripts/ files are self-contained (leak_scan.py/check_layer_order.py precedent), outside the src/ambo dependency-direction table

### Pending Todos

None yet.

### Blockers/Concerns

**Closed 2026-08-04 — all seven ingest warnings resolved at source.** W1–W7 were fixed by
editing the source documents (see `.planning/INGEST-CONFLICTS.md` resolution log and
`docs/ADR/ADR-000`). None is carried into any phase. The intel count discrepancy is also
corrected. What remains:

1. **[Phase 1] Branch name.** Repository is on **`master`**; the blueprint, EB-080 branch
   protection, `check_layer_order.py`, and CI config all assume **`main`**, and each gets
   written against it once. Renamed to `main` on 2026-08-04 — no remote exists, so the rename
   was local and lossless. Verify before the first push that any forge default branch matches.
   *(The rest of the original blocker is stale: the baseline commit already exists — `1851f39`,
   documentation-only, zero code — so the layer-order argument does start clean.)*

2. **[Phase 6] External dependency.** The private agency drop plus written permission is the
   only external blocker. Phases 1–5 are fully drop-independent; fill any wait window with the
   intake codebase (T-501…T-506), the decision layer against Layer P (T-701…T-704), and
   reporting infrastructure (T-801, T-802).

3. **[M3 exit — ACTION REQUIRED, no natural trigger] Repository is PRIVATE; make it public
   when the recovery report exists.** The repo was public from 2026-08-04 13:53 until 16:0x
   with 39k words of specs, zero code and no README. Set private on 2026-08-04 by decision:
   go public at **M3**, when `reports/recovery/RECOVERY_REPORT.md` proves the model recovers
   known truth. That is the moment the project's central claim stops being a promise. Git
   history is untouched, so the layer-order argument (Charter §5) still verifies on release.

   **Before flipping back to public, do all of:**

   - [ ] `RECOVERY_REPORT.md` exists with SPEC-05 §3 gates green
   - [ ] `README.md` exists per SPEC-07 §6 (DL-10: leads with the recovery result)
   - [ ] `LICENSE` (MIT, per SPEC-08 §2) present
   - [ ] `gh repo edit --visibility public`

   *Done 2026-08-04:* `docs/EXECUTION_BLUEPRINT/` untracked and gitignored as internal build
   scaffolding (files remain on disk, and remain in history from commit `1851f39` — EB-082
   forbids rewriting, which is accepted). Published tree is now `PROJECT_CHARTER.md`,
   `AGENTS.md`, `docs/ADR/`, `docs/SPEC-01..09`, `.planning/`. `.planning/` was kept tracked
   deliberately: it is version-controlled backup for ROADMAP/STATE, and INGEST-CONFLICTS.md
   with its resolution log is a defensible artifact rather than noise.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-08-06T09:39:21.620Z
Stopped at: Completed 03-08-PLAN.md
Resume file: None

Next: `/gsd-plan-phase 1`. Both original Phase-1 blockers are cleared — the branch is now
`main` and WARNING 3 is fixed in SPEC-08 §2 plus the [STD] checklist — so Phase 1 can plan
against a consistent spec set. The next artifact this repository needs is code.
