---
phase: 01-repository-foundation
plan: 02
subsystem: infra
tags: [uv, pyproject, lockfile, pymc, ruff, mypy, pytest, gitignore, license]

requires:
  - phase: 01-01
    provides: "docs/BUILD_LOG.md, .gitattributes LF pin, ADR template"
provides:
  - "pyproject.toml — SPEC-08 section 3 bounds, sole tool-config home"
  - "uv.lock — committed, human-reviewed (1A), universal, 135 packages, EB-030 pin"
  - "SPEC-08 §2 directory skeleton, .env.example, LICENSE"
affects: [01-03, 01-04, 01-05, 01-06, 01-07, 01-08, 01-09]

tech-stack:
  added: [uv, pandas, numpy, pymc, arviz, pymc-marketing, scipy, duckdb, dbt-core, dbt-duckdb, holidays, matplotlib, pydantic, PyYAML, python-dotenv, pytest, pytest-cov, ruff, mypy, pre-commit, nbstripout]
  patterns:
    - "Charter O-3 is import-scoped, not tree-scoped"
    - "gitignore dir/* + !dir/.gitkeep for placeholders inside ignored dirs"
    - "One PR per GSD plan (decision 4B)"

key-files:
  created:
    - pyproject.toml
    - uv.lock
    - src/ambo/__init__.py
    - .env.example
    - LICENSE
  modified:
    - .gitignore
    - docs/BUILD_LOG.md

key-decisions:
  - "O-3 import-scoped: sklearn 1.9.0 via pymc-marketing is not a violation (human 1A)"
  - "Reuse m0-bootstrap artifacts (human 2A); one PR per plan (human 4B); degrade at M4 if no drop (human 3A)"

requirements-completed: [REQ-dl8-quality, REQ-scope-out]
duration: 40min
completed: 2026-09-01
status: complete
---

# Phase 1 Plan 2: Project bootstrap Summary

**SPEC-08 bounds in pyproject.toml, human-approved universal uv.lock (135 packages), and the section 2 directory skeleton with MIT LICENSE and AMBO_PRIVATE_DROP-only .env.example.**

## Performance

- **Duration:** ~40 min across Task 1 (earlier) + Tasks 2–3 after human 1A
- **Started:** 2026-09-01T16:56:00Z
- **Completed:** 2026-09-01T19:45:00Z
- **Tasks:** 3
- **Files modified:** pyproject, lock, package inits, skeleton, gitignore, env, LICENSE, BUILD_LOG

## Accomplishments

- Authored `pyproject.toml` with SPEC-08 §3 bounds; D-15 coverage gate non-blocking (both `--cov-fail-under` and `fail_under` commented)
- Human legitimacy checkpoint (1A) approved the pin; `uv.lock` committed as EB-030
- Skeleton, `.env.example`, LICENSE copied from verified m0-bootstrap commit `7fa3285` (2A)

## Task Commits

1. **Task 1: Author pyproject.toml** — `2c5cf4c` (feat)
2. **Task 2: Legitimacy review** — human 1A; lock uncommitted at review; pin is `5a71c74`
3. **Task 3: Skeleton / env / LICENSE** — `77ebcb7` (feat)

**Plan metadata:** this commit.

## Deviations from Plan

**1. [Rule 1] Comment `[tool.coverage.report] fail_under`**
- pytest-cov honours it, which would block M0 contrary to D-15. Same fix as m0 commit `727de22`.

**2. [Process] One PR per plan (4B)** not per task.

**Total deviations:** 2. No scope creep.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

Ready for 01-03 (MODULE_CONTRACTS, RISK_REGISTER, ADR-006, PR template), copying from m0-bootstrap.

## Self-Check: PASSED

Task 1 and Task 3 automated verify blocks PASS. Task 2 human-approved 1A.

---
*Phase: 01-repository-foundation*
*Completed: 2026-09-01*
