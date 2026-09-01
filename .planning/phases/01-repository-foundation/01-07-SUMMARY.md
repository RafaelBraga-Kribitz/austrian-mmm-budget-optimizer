---
phase: 01-repository-foundation
plan: 07
subsystem: infra
tags: [guards, layout, o-3, import-independence, line-endings]
requires:
  - phase: 01-02
    provides: "src/ambo layout, uv.lock"
  - phase: 01-03
    provides: "MODULE_CONTRACTS.md"
  - phase: 01-04
    provides: "common modules under contract"
provides:
  - "tests/conftest.py — repo_root, seeded_rng, tmp_repo, empty-collection hook"
  - "Four architectural guards: layout, forbidden-deps, import-independence, no-requests"
  - "Line-ending and gitignore tests"
  - "T-010 AC-1 planted-violation BUILD_LOG evidence"
affects: [01-08, 01-09]
key-files:
  created:
    - tests/conftest.py
    - tests/unit/test_repo_layout.py
    - tests/unit/test_forbidden_deps.py
    - tests/unit/test_import_independence.py
    - tests/unit/test_no_requests.py
    - tests/unit/test_line_endings.py
    - tests/unit/test_gitignore.py
  modified:
    - docs/BUILD_LOG.md
key-decisions:
  - "Copied from verified m0-bootstrap a853dbc / 009f56f / 7f62340 (2A)"
  - "O-3 import-scoped: forbidden-deps does not parse uv.lock (human 1A; plan lockfile scan superseded)"
requirements-completed: [REQ-scope-out, REQ-scope-in, REQ-dl8-quality]
duration: 20min
completed: 2026-09-01
status: complete
---

# Phase 1 Plan 7: Architectural guards Summary

**Test scaffold plus four standing guards, LF/gitignore tests, and planted-violation evidence.**

## Task Commits

1. **Task 1** — `ba11f6f` conftest + layout guard (from m0 `a853dbc`)
2. **Task 2** — `16e5019` forbidden-deps / import-independence / no-requests (from m0 `009f56f`)
3. **Task 3** — `eae5927` line-endings + gitignore; `8f2c17a` BUILD_LOG T-010 AC-1 (tests from m0 `7f62340`)

**Plan metadata:** this commit.

## Deviations from Plan

**1. [Rule 2 / human 1A] Forbidden-deps does not scan `uv.lock`.** Charter O-3 is import-scoped. Transitive sklearn via pymc-marketing is accepted. Matches m0 `009f56f`.

**2. [Process] HEAD is `cursor/architectural-guards-9588`, not `m0-bootstrap`.** Human 4B. Scratch branch `scratch-01-07-planted-violations` was still created, used with zero commits, and deleted via `git branch -d`.

**3. [Process] BUILD_LOG T-010 entry landed in a follow-up commit** (`8f2c17a`) because a parallel write raced the Task 3 test commit. Not amended (EB-082). Additions-only.

**4. [Process] One PR per plan (4B)** not per task.

**Total deviations:** 4. No scope creep.

## Self-Check: PASSED

- Layout: tracked top-level plant, missing contract, duplicate heading all red then green
- Forbidden import `robyn` red; `sklearn_extra_fake_pkg` fragment does not trip
- simulate→model plant red
- Four T-010 plants on scratch branch, all red, branch deleted
- `uv run pytest tests -q --no-cov` — 42 passed
- BUILD_LOG Task 3 evidence commit: 48 insertions, 0 deletions

---
*Phase: 01-repository-foundation*
*Completed: 2026-09-01*
