---
phase: 01-repository-foundation
verified: 2026-08-04T22:55:00Z
status: passed
score: 5/5 roadmap success criteria verified; 5/5 phase requirements satisfied
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5 roadmap success criteria verified (1 currently failing on HEAD); 5/5 phase requirements satisfied
  gaps_closed:
    - "make setup && make lint && make test runs green on a fresh clone (ROADMAP Success Criterion 1) — make lint now passes; ruff format --check . reports 81 files already formatted (0 issues)"
  gaps_remaining: []
  regressions: []
---

# Phase 1: Repository Foundation Verification Report

**Phase Goal:** A clone-and-run engineering shell where the quality bar, the scope walls, and the
governance mechanisms all exist and are enforced before a single line of science is written.
**Verified:** 2026-08-04
**Status:** passed
**Re-verification:** Yes — after gap closure

## What Changed Since The Prior Pass

The prior verification (commit `fe0bd42`, superseded by this report) found 4/5 ROADMAP success
criteria verified, with exactly one gap: `make lint` failed on HEAD because
`.planning/phases/01-repository-foundation/01-REVIEW.md` contained an embedded Python code fence
that `ruff format --check .` flagged (79 files formatted, 1 needing reformatting). The prescribed
remedy — `uv run ruff format .planning/phases/01-repository-foundation/01-REVIEW.md` — was applied
in commit `046a28c` ("style(01): ruff-format the embedded python fence in the review report").

Independently re-ran the fix and inspected the diff directly (not taking the SUMMARY/orchestrator
claim on trust):

- `git show 046a28c -- .planning/phases/01-repository-foundation/01-REVIEW.md` shows a purely
  mechanical change: 4 blank-line insertions between function definitions inside the embedded
  Python fences, plus one multi-line `subprocess.run(...)` argument wrap. No prose, finding, or
  code-review content was altered — the review report's substance is unchanged.
- `git diff --stat 3989259..HEAD -- src/ scripts/ tests/ Makefile pyproject.toml config/ dbt/
  .github/` returns empty — confirms nothing in the phase's actual engineering surface changed
  between the CI-proven commit and current HEAD; only `.planning/` documentation artifacts (the
  review report and its own formatting fix, plus the now-superseded verification report) changed.

The second suggested remedy from the prior report — adding `.planning/` to
`[tool.ruff] extend-exclude` — was deliberately **not** applied, per explicit user instruction to
defer that as a separate governance decision. Its absence is not treated as a gap here (see Anti-
Patterns / Observations below for the recurrence-risk note carried forward).

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the roadmap contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `make setup && make lint && make test` runs green on a fresh clone, on both Windows Git Bash and Linux | ✓ VERIFIED | Re-ran directly on current HEAD (`fe0bd42` + working tree with the fix committed): `make lint` → `ruff check .` "All checks passed!", `ruff format --check .` "81 files already formatted" (up from 79 in the prior pass — confirms both the review report and the prior verification report are now included and clean), `mypy` "Success: no issues found in 11 source files", exit 0. `make test` → 61 passed, 95% coverage on scoped modules, exit 0. `uv run mypy` and `uv run python scripts/leak_scan.py` independently re-run and clean (exit 0). `make setup` was not re-run live in this pass (no dependency/toolchain changes occurred between passes — only a `.planning/` doc reformat), but was CI-proven green on both `ubuntu-latest` and `windows-latest` at commit `3989259` (runs 30951615385/30951952211/30952418680), and nothing in the fix commit touches `pyproject.toml`, `uv.lock`, or any setup-relevant file. |
| 2 | CI `ci.yml` runs all six required jobs and all six pass — phase-gated jobs pass with an explicit "nothing to check yet" exit, never by being absent | ✓ VERIFIED (carried forward, unaffected by the fix) | Unchanged since prior pass: `.github/workflows/ci.yml` parses to exactly `{lint, test, dbt, ssot, layer-order, leak}`; `gh run view 30952418680 --json jobs` showed all 7 check runs `success`. `git diff --stat 3989259..HEAD -- .github/` confirms zero changes to the workflow since that CI-proven commit. |
| 3 | Git history begins with a documentation-only baseline commit (charter + specs + blueprint, zero code) that every later commit descends from | ✓ VERIFIED (carried forward, unaffected by the fix) | Unchanged since prior pass — no history rewrite occurred; the fix is an ordinary new commit on top. |
| 4 | `dbt/seeds/season_windows.csv` is committed with passing unit tests, so the simulator and dbt read one calendar (AD-020) | ✓ VERIFIED (carried forward, unaffected by the fix) | `git diff --stat 3989259..HEAD -- dbt/` empty — file untouched. `uv run python -m pytest -o addopts="" -q` includes `tests/unit/test_season_windows.py` in the 61 collected/passed tests. |
| 5 | The two architectural guard tests exist and fail loudly when violated: forbidden dependencies (robyn, lightweight_mmm, prophet, sklearn) and simulate↔model import independence | ✓ VERIFIED (carried forward, unaffected by the fix) | `git diff --stat 3989259..HEAD -- tests/` empty — guard tests untouched. Re-ran `uv run pytest tests/unit/test_forbidden_deps.py tests/unit/test_import_independence.py -q` — 4 passed. |

**Score:** 5/5 roadmap success criteria verified. The single gap from the prior pass (Criterion 1)
is closed and independently reproduced as fixed.

### Requirements Coverage (Phase 1's five REQ IDs)

| Requirement | Owning Plan(s) | Status | Evidence |
|---|---|---|---|
| REQ-dl8-quality | 01-01, 01-02, 01-04, 01-05, 01-06, 01-07, 01-08, 01-09 | ✓ SATISFIED | `make lint` now fully green (no caveat remaining); `make test` green (61 passed, 95% coverage on scoped modules); coverage gate present but intentionally non-blocking per D-15 (`--cov-fail-under` commented out in both `addopts` and `[tool.coverage.report]`, confirmed still commented out — untouched by the fix). |
| REQ-scope-in | 01-03, 01-07 | ✓ SATISFIED (carried forward) | `tests/unit/test_repo_layout.py` untouched by the fix (`git diff --stat` confirms), mechanism unchanged from prior pass. |
| REQ-scope-out | 01-02, 01-04, 01-07, 01-08 | ✓ SATISFIED (carried forward) | `tests/unit/test_forbidden_deps.py` untouched; import-scoped enforcement of O-3 per the ratified 01-02 checkpoint decision remains correct — `tests/unit/test_forbidden_deps.py` correctly does not parse `uv.lock` (Charter O-3 is import-scoped, not tree-scoped, per the binding ruling). Single CI workflow, `grep -c cron .github/workflows/ci.yml` = 0, enforces O-7. |
| REQ-milestones | 01-01, 01-03, 01-05, 01-09 | ✓ SATISFIED (carried forward) | `docs/BUILD_LOG.md` untouched by the fix; M0 close entry with real CI-run evidence and elapsed-effort accounting stands as previously verified. |
| REQ-risk-register | 01-03, 01-09 | ✓ SATISFIED (carried forward) | `docs/RISK_REGISTER.md` untouched by the fix; all nine Charter risks R-1…R-9 present, verified previously. |

No orphaned requirements: all five phase requirement IDs declared in ROADMAP.md appear in at
least one plan's `requirements:` frontmatter field — re-confirmed: `grep -l "requirements:"
.planning/phases/01-repository-foundation/*-PLAN.md` returns all 9 plan files, and
`.planning/REQUIREMENTS.md` marks all five IDs `Complete` with Phase 1 as owning phase.

### Required Artifacts

All artifacts previously verified at all three/four levels (exists, substantive, wired, behaves)
are carried forward unchanged — `git diff --stat 3989259..HEAD` across every source-relevant path
(`src/`, `scripts/`, `tests/`, `Makefile`, `pyproject.toml`, `config/`, `dbt/`, `.github/`) is
empty, so none of those artifacts could have regressed. Only `.planning/` documentation changed.
See the prior verification report (superseded, but its artifact table's findings are unaffected)
for the full per-artifact evidence; not re-derived here since nothing changed.

The one artifact directly touched by the fix:

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/phases/01-repository-foundation/01-REVIEW.md` | ruff-format-clean embedded Python fences | ✓ VERIFIED | `git show 046a28c` diff inspected directly: purely whitespace (blank-line insertions, one arg-wrap) inside the three embedded Python code fences; findings/prose content unchanged. `ruff format --check .` now reports this file among the "81 files already formatted" with zero issues. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `make lint` end-to-end | `make lint` | `ruff check .` → "All checks passed!"; `ruff format --check .` → "81 files already formatted"; `mypy` → "Success: no issues found in 11 source files"; exit 0 | ✓ PASS |
| `make test` | `make test` | 61 passed, 95% coverage on scoped modules, exit 0 | ✓ PASS |
| Standalone `ruff check .` | `uv run ruff check .` | "All checks passed!" | ✓ PASS |
| Standalone `ruff format --check .` | `uv run ruff format --check .` | "81 files already formatted" (0 issues; up from 79 in the prior failing pass) | ✓ PASS |
| Standalone `mypy` | `uv run mypy` | "Success: no issues found in 11 source files" | ✓ PASS |
| Leak scanner clean-tree exit | `uv run python scripts/leak_scan.py` | exit 0, no findings | ✓ PASS |
| Forbidden-deps / import-independence guards | `uv run pytest tests/unit/test_forbidden_deps.py tests/unit/test_import_independence.py -q` | 4 passed | ✓ PASS |
| No source-surface drift since CI-proven commit | `git diff --stat 3989259..HEAD -- src/ scripts/ tests/ Makefile pyproject.toml config/ dbt/ .github/` | empty output | ✓ PASS (confirms carried-forward criteria could not have regressed) |

Note: a minor, pre-existing discrepancy was observed and is flagged for transparency, not treated
as a gap — the prior verification report's claim of "75 passed" for bare `uv run python -m pytest
-q` does not reproduce; both a clean-addopts run and `make test` collect and pass exactly 61 tests
(smoke/fit-marked tests are excluded via the `test` Makefile target's marker expression, and no
other test files exist beyond what's collected). This is a reporting artifact in the superseded
report, not a functional regression — no test file changed since the CI-proven commit
(`git diff --stat 3989259..HEAD -- tests/` is empty), and 61 is what both the raw run and `make
test` consistently report today.

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention exists in this project (unchanged from prior pass;
`find scripts -path '*/tests/probe-*.sh'` empty). Not applicable.

### Anti-Patterns Found / Carried-Forward Observations

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/phases/01-repository-foundation/01-REVIEW.md` | — | Unformatted embedded Python code fences | ~~Warning~~ RESOLVED | Fixed in `046a28c`; `ruff format --check .` now clean on this file. |
| `pyproject.toml` `[tool.ruff]` | — | No `extend-exclude` for `.planning/` | Info (deferred by explicit user decision) | The recurrence risk remains: any future `.planning/` artifact with an embedded, non-ruff-formatted code fence will break `make lint`/CI job 1 again. The user has explicitly deferred this as a separate governance decision (possibly warranting an ADR), not a Phase 1 gap. Recording as a non-blocking observation per the verification stance instructions. |
| `scripts/leak_scan.py` (per code review CR-01) | 117-139 | `.env.example` generic-shape carve-out + CI never sets `AMBO_PRIVATE_DROP` → a real path pasted into `.env.example` is never caught by CI's `leak` job | Warning | Carried forward unchanged; pre-existing design gap flagged by `01-REVIEW.md`, not a violation of any stated must-have. |
| `src/ambo/common/logging.py` (per code review CR-02) | 66-88 | `PrivatePathFilter._redact` only redacts `str` `msg`/`args`; never touches `record.exc_info`/traceback text | Warning | Carried forward unchanged; not exercised at M0 (no code calls `logger.exception` yet). |
| `scripts/check_ssot_consistency.py` (per code review WR-01/WR-02) | 119-143 | Unit-symbol asymmetry (`×` vs `x`); Austrian comma-decimal parsing not supported | Info | Carried forward unchanged; inert at M0. |
| `scripts/check_layer_order.py` (per code review WR-03) | 59-61, 120-132 | Uncaught `CalledProcessError` on a root-commit edge case | Info | Carried forward unchanged; untested edge case, not reachable at M0. |
| `tests/unit/test_config.py` (per code review WR-04) | 87-94 | One test's Windows-literal fixture doesn't exercise absolute-path resolution on POSIX | Info | Carried forward unchanged; test-quality gap, not a functional defect. |

No `TBD`/`FIXME`/`XXX` debt markers found in any phase-modified file (re-confirmed:
`grep -rnE 'TBD|FIXME|XXX' src/ scripts/ tests/ Makefile pyproject.toml config/` returns nothing).
No `TODO`/`HACK`/`PLACEHOLDER` markers either.

### Human Verification Required

None. All items resolved programmatically by direct command execution against the current tree.

### Gaps Summary

None remaining. The single gap identified in the prior verification pass — `make lint` failing on
HEAD because `.planning/phases/01-repository-foundation/01-REVIEW.md` was not ruff-format-clean —
was closed by commit `046a28c`, a purely mechanical, content-preserving reformat verified directly
via `git show`. Independently re-running the full quality gate (`ruff check`, `ruff format
--check`, `mypy`, `pytest`, `leak_scan.py`) on the current tree confirms all pass. No other file
in the phase's engineering surface changed since the CI-proven commit `3989259`
(`git diff --stat` across `src/`, `scripts/`, `tests/`, `Makefile`, `pyproject.toml`, `config/`,
`dbt/`, `.github/` is empty), so the four previously-verified criteria and five previously-
satisfied requirements could not have regressed and are carried forward.

Phase 1's engineering shell — the quality bar (ruff + mypy + pytest, all clean; coverage gate
present, intentionally non-blocking per D-15), the scope walls (import-scoped forbidden-deps guard
per the ratified O-3 decision, contract-first module layout guard), and the governance mechanisms
(ADR template + registry, build log, risk register, CI workflow with six always-present jobs,
leak scanner, layer-order and SSOT-consistency checks) — all exist, are wired, and are now proven
to run green end-to-end on the current tracked tree. The phase goal is achieved.

The deferred `.planning/` ruff-exclude decision and the 6 code-review findings (2 Critical design
gaps not yet exercised at M0, 4 Warning/Info) remain open observations, correctly not promoted to
blocking gaps since none contradicts a stated Phase 1 must-have.

---

_Verified: 2026-08-04_
_Verifier: Claude (gsd-verifier)_
