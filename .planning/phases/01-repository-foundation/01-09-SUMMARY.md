---
phase: 01-repository-foundation
plan: 09
subsystem: infra
tags: [ci, github-actions, governance, layer-order, ssot, leak-scan, pytest]

# Dependency graph
requires:
  - phase: 01-05
    provides: "Makefile targets (lint, test, transform) the CI jobs invoke rather than reimplementing"
  - phase: 01-06
    provides: "scripts/generate_season_windows.py, the D-20 seed diff-check the lint job runs"
  - phase: 01-07
    provides: "The four architectural guard tests and line-ending/gitignore tests the test job runs"
  - phase: 01-08
    provides: "scripts/leak_scan.py and the pre-commit toolchain the leak job runs; also the source of two bugs fixed in this plan"
provides:
  - "scripts/check_layer_order.py -- real GB-501/GB-502 git-ancestry predicate, vacuously correct at M0 (D-17)"
  - "scripts/check_ssot_consistency.py -- real GB-301 numeric-SSOT reconciliation, vacuously correct at M0 (D-17)"
  - "tests/unit/test_governance_checks.py -- throwaway-repository proofs for both checks"
  - ".github/workflows/ci.yml -- the single six-job EB-060 workflow (lint, test x2 matrix legs, dbt, ssot, layer-order, leak)"
  - "The M0 close entry in docs/BUILD_LOG.md, consolidating all eight prior plans' evidence plus the real CI run"
  - "R-13 closed on docs/RISK_REGISTER.md (Chocolatey make provenance confirmed GNU Make 4.4.1)"
  - "Two bug fixes in scripts/leak_scan.py originating in plan 01-08: a self-matching doc comment, and a duplicate-needle double-count"
  - "Platform-appropriate test fixtures in tests/unit/test_logging.py and tests/unit/test_leak_scan.py"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vacuously-correct governance checks (D-17): both scripts implement their real predicate and print an explicit nothing-to-check notice when the subject does not exist yet, rather than stubbing or skip-guarding -- Phase 5 extends, never replaces"
    - "No job-level `if:` in CI (D-16): every one of the six jobs runs to completion and reports a real pass/fail; the only `if:` in the workflow is a step-level OS conditional inside the test job's matrix, selecting setup steps rather than gating the job"
    - "Matrix-leg-is-not-a-seventh-job (D-21): the test job's job id/name stays `test` across both ubuntu-latest and windows-latest, producing two check runs (`test (ubuntu-latest)`, `test (windows-latest)`) that both count as one of EB-060's six job identities -- GitHub's own check-run naming, not the workflow file, appends the `(os)` suffix"
    - "Self-covering leak scanner: scripts/leak_scan.py is never exempted from its own scan; documentation that needs to illustrate a matched shape uses a placeholder token instead of a literal example"
    - "Platform-appropriate absolute-path test fixtures: any fixture whose value flows through Path(...).resolve() must be constructed as genuinely absolute on the runner's own OS (sys.platform branch), not hardcoded to one OS's separator style"

key-files:
  created:
    - scripts/check_layer_order.py
    - scripts/check_ssot_consistency.py
    - tests/unit/test_governance_checks.py
    - .github/workflows/ci.yml
  modified:
    - docs/BUILD_LOG.md
    - docs/RISK_REGISTER.md
    - scripts/leak_scan.py
    - tests/unit/test_logging.py
    - tests/unit/test_leak_scan.py

key-decisions:
  - "GB-501/GB-502 implemented as a real git-ancestry predicate over LAYER_R_GLOBS and the prior-freeze-v1 tag, not a stub -- exits 0 today with an explicit 'no Layer R artifact and no prior-freeze tag found' notice, proven on throwaway git repositories built inside tmp_repo"
  - "GB-301 implemented as a real reconciliation over reports/NUMERIC_SSOT.md's six-column table contract, not a stub -- exits 0 today with an explicit 'no NUMERIC_SSOT.md found' notice"
  - "CI workflow declares no job-level if: anywhere (D-16); the D-20 seed diff-check is folded into the lint job rather than becoming a seventh job; layer-order and leak both check out with fetch-depth: 0 because their predicates are whole-history/whole-tree claims"
  - "leak_scan.py's own PRIVATE_DROP_PATTERNS doc-comment examples were rewritten to use an <abs-path> placeholder instead of literal Windows/POSIX paths, so the scanner no longer flags its own source -- the scanner itself is NOT exempted from being scanned"
  - "_resolve_private_drop_needles() now deduplicates its three separator-form candidates with dict.fromkeys(); the un-deduplicated version silently double-counted a single real match into two Finding rows whenever the resolved path's native separator style made two of the three candidates identical (always true on POSIX, never true on the Windows-canonical form that originally masked this)"
  - "FAKE_PRIVATE_DROP / FICTIONAL_DROP_PATH test fixtures now branch on sys.platform so the fixture is genuinely absolute (and therefore Path(...).resolve() is a true no-op) on whichever OS the test suite runs on, instead of a fixed Windows-style drive-letter literal that was only absolute on Windows"

patterns-established:
  - "A CI failure diagnosed on the runner's actual log, not re-derived from local (single-platform) behavior -- both bugs fixed here were invisible in Windows-only local verification and only surfaced on the ubuntu-latest leg"

requirements-completed: [REQ-dl8-quality, REQ-scope-out, REQ-milestones]

coverage:
  - id: D1
    description: "scripts/check_layer_order.py and scripts/check_ssot_consistency.py implement real GB-501/GB-502/GB-301 predicates, exit 0 with an explicit nothing-to-check notice today, and are proven to fail on a genuine ordering/malformed-table violation via throwaway git repositories"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: unit
        ref: "tests/unit/test_governance_checks.py (7+ test functions, throwaway tmp_repo fixtures)"
        status: pass
      - kind: other
        ref: "uv run python scripts/check_layer_order.py (exit 0, notice); uv run python scripts/check_ssot_consistency.py (exit 0, notice)"
        status: pass
    human_judgment: false
  - id: D2
    description: ".github/workflows/ci.yml declares exactly the six EB-060 jobs (lint, test, dbt, ssot, layer-order, leak) with no job-level if:, no cron, fetch-depth 0 on layer-order/leak, and the test job matrixed with a 15-minute timeout"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "uv run python -c \"import yaml; ...\" schema assertions from 01-09-PLAN.md Task 2's <verify> block; all passed prior to push"
        status: pass
    human_judgment: false
  - id: D3
    description: "A real CI run on draft PR #1 shows all six EB-060 job identities green with none skipped, after fixing two independent bugs the first run surfaced"
    requirement: "REQ-milestones"
    verification:
      - kind: e2e
        ref: "https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer/actions/runs/30951615385 and confirming run 30951952211 -- gh pr checks: lint, test (ubuntu-latest), test (windows-latest), dbt, ssot, layer-order, leak all SUCCESS"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/BUILD_LOG.md carries the M0 close entry with CI run evidence, and docs/RISK_REGISTER.md R-13 is struck through against that reference"
    requirement: "REQ-milestones"
    verification:
      - kind: other
        ref: "docs/BUILD_LOG.md M0 close entry 'CI run evidence' paragraph; docs/RISK_REGISTER.md R-13 row (struck through) and Review log entry"
        status: pass
    human_judgment: false

duration: ~64min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 9: CI Workflow, Governance Checks, and M0 Close Summary

**Six-job EB-060 CI workflow (`lint`, `test` matrixed ubuntu/windows, `dbt`, `ssot`, `layer-order`, `leak`) confirmed green with none skipped on draft PR #1, after fixing two 01-08-originated bugs the first CI run surfaced that Windows-only local verification could not catch — a self-matching doc-comment in `leak_scan.py` and a duplicate-needle double-count in its private-drop matcher.**

## Performance

- **Duration:** ~64 min (22:16 plan start through 23:20 checkpoint close)
- **Started:** 2026-08-04T22:16:39+02:00 (approx., following 01-08's close)
- **Completed:** 2026-08-04T23:20:41+02:00
- **Tasks:** 3 (2 `type="auto"` + 1 `type="checkpoint:human-verify"`)
- **Files modified:** 9 (4 created: `scripts/check_layer_order.py`, `scripts/check_ssot_consistency.py`, `tests/unit/test_governance_checks.py`, `.github/workflows/ci.yml`; 5 modified: `docs/BUILD_LOG.md`, `docs/RISK_REGISTER.md`, `scripts/leak_scan.py`, `tests/unit/test_logging.py`, `tests/unit/test_leak_scan.py`)

## Accomplishments

- `scripts/check_layer_order.py`: real GB-501 (recovery-report-precedes-Layer-R-artifact ancestry) and GB-502 (freeze-tag ancestry, post-tag priors immutability, append-only amendment) predicates over git history. Exits 0 today with `check_layer_order: no Layer R artifact matching (data/posteriors/R*.parquet, reports/model/diag_R.md) and no 'prior-freeze-v1' tag found -- nothing to check yet`. Proven against throwaway git repositories: correct ordering passes, fit-before-report ordering fails, artifact-free repo passes with its notice, artifact-with-no-freeze-tag fails.
- `scripts/check_ssot_consistency.py`: real GB-301 six-column (`key`, `value`, `unit`, `tag`, `produced_by`, `updated_at`) table reconciliation. Exits 0 today with `check_ssot_consistency: no reports/NUMERIC_SSOT.md found ... -- nothing to reconcile`. A malformed table (missing column) exits non-zero; an absent file does not.
- `.github/workflows/ci.yml`: the single workflow, exactly six job ids (`lint`, `test`, `dbt`, `ssot`, `layer-order`, `leak`), push/pull_request-to-main triggers only (no cron, Charter O-7), a concurrency group that never cancels a run on `main`, no job-level `if:` anywhere, `fetch-depth: 0` on `layer-order` and `leak`, the D-20 seed diff-check folded into `lint`, and `test` matrixed over `ubuntu-latest`/`windows-latest` with a 15-minute timeout and a step-level (not job-level) OS conditional for the Chocolatey `make` install.
- **CI evidence, across three runs on draft PR #1:**
  1. Run [30948579395](https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer/actions/runs/30948579395) — 5/7 checks green, `leak` and `test (ubuntu-latest)` failed. Diagnosed as two independent, pre-existing bugs in `scripts/leak_scan.py` and its test fixtures, both originating in plan 01-08, both invisible to this plan's Windows-only local verification.
  2. Run [30951320145](https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer/actions/runs/30951320145) — 6/7 checks green after the first two fixes; `test (ubuntu-latest)` still failed, on a third, previously-masked bug in the same code path (duplicate-needle double-counting).
  3. Run [30951615385](https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer/actions/runs/30951615385) and its confirming successor [30951952211](https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer/actions/runs/30951952211) — all six EB-060 job identities SUCCESS, none skipped (7 check runs including the two `test` matrix legs). Windows leg's `make --version` reads `GNU Make 4.4.1 / Built for x86_64-w64-mingw32`, matching the development machine's independently-verified 4.4.1 build — closing evidence for R-13.
- `docs/BUILD_LOG.md`: the M0 close entry gained the CI run evidence paragraph (filling the pending placeholder the entry itself deliberately left for this exact append), consolidating all eight prior plans' handoffs plus this plan's own bug-fix account. No prior entry content was edited.
- `docs/RISK_REGISTER.md`: R-13 (Chocolatey `make` provenance) struck through and closed against the build-log reference, with a new dated Review log line recording 12 open / 1 closed.
- PR #1 remains in **draft** — D-11 reserves ready-for-review for the milestone exit gate; it was neither marked ready nor merged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement the two governance checks as real, vacuously-correct predicates** - `60e8a74` (feat)
2. **Task 2: Land the six-job CI workflow and write the M0 close entry** - `004e2a2` (feat)
3. **Task 3: Confirm all six CI jobs run green with none skipped** — checkpoint, resumed and closed across four commits:
   - `2bb8b7c` (fix) — stop `leak_scan.py` self-matching its own documentation comment
   - `a05d4ee` (fix) — make `FAKE_PRIVATE_DROP`/`FICTIONAL_DROP_PATH` test fixtures platform-appropriate
   - `60c3f04` (fix) — deduplicate private-drop needles to stop double-counted findings
   - `7b42a7c` (feat) — record CI evidence in the M0 close entry and close R-13

**Plan metadata:** committed separately after this summary is written.

## Files Created/Modified

- `scripts/check_layer_order.py` - Real GB-501/GB-502 git-ancestry predicate, vacuously correct at M0
- `scripts/check_ssot_consistency.py` - Real GB-301 numeric-SSOT reconciliation, vacuously correct at M0
- `tests/unit/test_governance_checks.py` - Throwaway-repository proofs for both governance checks
- `.github/workflows/ci.yml` - The single six-job EB-060 workflow
- `docs/BUILD_LOG.md` - M0 close entry, now including the CI run evidence paragraph
- `docs/RISK_REGISTER.md` - R-13 struck through and closed; Review log updated
- `scripts/leak_scan.py` - Fixed a self-matching doc-comment example and deduplicated private-drop needles
- `tests/unit/test_logging.py` - `FAKE_PRIVATE_DROP` now platform-appropriate (`sys.platform` branch)
- `tests/unit/test_leak_scan.py` - `FICTIONAL_DROP_PATH` now platform-appropriate (`sys.platform` branch)

## Decisions Made

See `key-decisions` in the frontmatter. The two load-bearing ones from the fix-forward: (1) the leak scanner's own documentation must use a non-matching placeholder rather than a literal example, because the scanner is deliberately never exempted from scanning its own source; (2) `_resolve_private_drop_needles()` must deduplicate its candidate list, because `str(Path(...).resolve())` always produces exactly one native-separator form, making one of its two `.replace()` transformations a guaranteed no-op that silently duplicated a needle.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `leak_scan.py`'s own doc-comment matched its own leak-detection regex**
- **Found during:** Task 3 checkpoint, first CI run (30948579395) — the `leak` job failed scanning its own source
- **Issue:** The two illustrative examples in the `PRIVATE_DROP_PATTERNS` doc comment paired the `AMBO_PRIVATE_DROP` env-var name with an `[:=]` operator and a literal absolute Windows path, then a literal absolute POSIX path — the exact assignment shape the regex below them was written to catch, so both examples matched their own documentation subject. This is a defect in plan 01-08 (commit `dc6ddfa`); 01-08's SUMMARY claim that the scanner "exits 0 on the clean repository" was not accurate as originally written — it was only ever run locally against a tree that happened not to re-scan this comment as a `leak` CI job would.
- **Fix:** Rewrote both examples with an `<abs-path>` placeholder (the pattern's own character class already excludes `<`/`>`), preserving the comment's explanatory value without matching. The scanner is explicitly NOT exempted from scanning `scripts/leak_scan.py` itself.
- **Files modified:** `scripts/leak_scan.py`
- **Verification:** `uv run python scripts/leak_scan.py` exits 0
- **Committed in:** `2bb8b7c`

**2. [Rule 1 - Bug] Private-drop test fixtures were absolute on Windows only, not on Linux**
- **Found during:** Task 3 checkpoint, first CI run (30948579395) — 4 tests failed on `test (ubuntu-latest)` only
- **Issue:** `config.py`'s `load_settings()` resolves `AMBO_PRIVATE_DROP` via `Path(private_drop_raw).resolve()`. The fixed literal `"D:/private/ambo_drop_fake"` / `"D:/fictional/never-real/ambo_drop_fixture"` values are absolute on Windows (so `.resolve()` is a no-op and redaction/leak-scan matching worked) but relative on POSIX (so `.resolve()` prefixed the runner's cwd, and the literal-value check never matched). This is a test-fixture bug, not a product bug — `config.py`, `logging.py`, and `leak_scan.py` were already correct; a real private-drop path is absolute on its own platform by construction.
- **Fix:** Branched `FAKE_PRIVATE_DROP` (`tests/unit/test_logging.py`) and `FICTIONAL_DROP_PATH` (`tests/unit/test_leak_scan.py`) on `sys.platform`, so each fixture is genuinely absolute — and the redaction/leak-scan logic under test is genuinely exercised — on whichever OS runs the suite. No test was xfailed or skipped; `config.py`'s `.resolve()` semantics are unchanged.
- **Files modified:** `tests/unit/test_logging.py`, `tests/unit/test_leak_scan.py`
- **Verification:** Local Windows run of the full suite passed both before and after (61/61); the CI Linux leg is the real gate for the POSIX branch
- **Committed in:** `a05d4ee`

**3. [Rule 1 - Bug] `_resolve_private_drop_needles()` produced a duplicate needle that double-counted one real match as two `Finding`s**
- **Found during:** Task 3 checkpoint, second CI run (30951320145) — the same 2 tests that fixture deviation 2 targeted still failed on `test (ubuntu-latest)`, now with `assert 2 == 1` instead of a missing match
- **Issue:** `_resolve_private_drop_needles()` unconditionally built `[raw, raw.replace("\\", "/"), raw.replace("/", "\\")]`. `raw = str(private_drop)` is already in the runner's native separator style, so exactly one of the two `.replace()` calls is a no-op that reproduces `raw` verbatim, and `_scan_single_line`'s per-needle loop then matched that duplicate needle twice against the same line. This was invisible on Windows: the resolved value there is backslash-form, so the no-op duplicate was the backslash needle, which never matched the forward-slash-written test line anyway (only 1 of 3 needles matched). On Linux the resolved value is forward-slash-form (POSIX `Path.resolve()` never introduces backslashes), so the no-op duplicate is the forward-slash needle that *does* match the test line — surfacing the bug as a genuine double-count. Neither this behavior nor deviation 2's fixture bug was discoverable from Windows-only local testing.
- **Fix:** `list(dict.fromkeys((raw, raw.replace("\\", "/"), raw.replace("/", "\\"))))` deduplicates the three candidates while preserving scan order. No matching behavior is weakened — this only removes double-counting of an already-matched needle.
- **Files modified:** `scripts/leak_scan.py`
- **Verification:** Local Windows suite green (61/61); confirmed on the third CI run (30951615385) that both previously-failing Linux tests now pass
- **Committed in:** `60c3f04`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs surfaced by the CI checkpoint that local single-platform verification could not catch). All three originate in or adjacent to plan 01-08's `scripts/leak_scan.py`; none is scope creep, and none weakens a check, exempts a file from a scan, or skips/xfails a test.
**Impact on plan:** Required two additional fix-forward CI round-trips beyond the plan's original two-task shape, all inside Task 3's checkpoint resume. No architectural change; every fix is a same-file correction to existing logic.

## Issues Encountered

The plan's Task 3 automated `<verify>` script (`gh pr checks --json name,state`) compares check names against a literal `["dbt","layer-order","leak","lint","ssot","test"]` list, but GitHub Actions names matrix-leg check runs `test (ubuntu-latest)` / `test (windows-latest)`, not bare `test` — so the script as written can never pass once the matrix produces two check runs, which the plan's own text elsewhere describes as expected (D-21). Verified manually instead: `gh run view` confirmed all seven check runs (five singleton jobs + two `test` matrix legs) report SUCCESS, and a corrected one-off script normalizing the `(os)` suffix before comparing confirmed the same six job identities with none skipped. Not treated as a plan defect requiring a PLAN.md edit — the underlying six-job-identity requirement (Success Criterion 2) is unambiguously met; only the plan's embedded verification snippet has a latent naming assumption.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Phase 1 (repository-foundation) is complete.** All four success criteria are met: the two governance checks are real predicates (not stubs); the CI workflow has one file, six job identities, no cron, no job-level conditional, and full history where the predicates need it; the season-window seed is policed by the D-20 diff-check inside `lint`; and a human (via this checkpoint's resume) has observed all six checks green with none skipped on a real run, recorded as evidence rather than intention in `docs/BUILD_LOG.md`.
- Effort tripwire: per the M0 close entry, plans 01-01..01-08 totaled ~130 min; this plan's ~64 min brings Phase 1's total measured effort to ~194 min (~3.2h, ~0.4d) against the 0.5d budget — well under the 1.0d (2x) strictly-greater tripwire. **The tripwire is not tripped.**
- PR #1 stays in draft. The next natural action is Phase 2 planning; branch protection with all six required checks is deferred to the M3 go-public checklist already tracked in `.planning/STATE.md`.
- `.planning/config.json` and `.planning/research/` appear as untracked in `git status` throughout this plan's execution — pre-existing GSD tooling scaffolding unrelated to this plan's `files_modified` scope, left untouched.

---
*Phase: 01-repository-foundation*
*Completed: 2026-08-04*
