---
phase: 01-repository-foundation
plan: 05
subsystem: infra
tags: [makefile, readme, loud-stubs, eb-050]
requires:
  - phase: 01-02
    provides: "pyproject.toml, uv, pytest/ruff/mypy"
provides:
  - "Makefile — 18 SPEC-08 section 5 targets, portable SHELL pin, D-27 stubs"
  - "README.md — scaffold with ## Roadmap nine-phase table"
affects: [01-09]
key-files:
  created:
    - Makefile
    - README.md
  modified: []
key-decisions:
  - "Copied from verified m0-bootstrap 0d46727 (Makefile) and 64e8fe5 (README) (2A)"
  - "transform is a vacuous dbt check (D-17), not a stub"
requirements-completed: [REQ-dl8-quality, REQ-milestones]
duration: 10min
completed: 2026-09-01
status: complete
---

# Phase 1 Plan 5: Makefile and README Summary

**Closed 18-target Makefile with loud D-27 stubs, plus a scaffold README whose Roadmap table is the stub pointer destination.**

## Task Commits

1. **Task 1** — `c8052d9` Makefile (from m0 `0d46727`)
2. **Task 2** — `0b4936f` README.md (from m0 `64e8fe5`)

**Plan metadata:** this commit.

## Deviations from Plan

**1. [Process] One PR per plan (4B)** not per task.

**Total deviations:** 1 process. No scope creep.

## Self-Check: PASSED

- `make -n` resolves all 18 SPEC-08 targets; no extras
- Twelve stubs exit non-zero with `NOT IMPLEMENTED` and `README`
- `make transform` exits 0 with nothing-to-build notice
- `make -n lint` order: ruff check, ruff format --check, mypy
- `make all` exits non-zero naming `fit-synthetic`; does not invoke a fit target
- `make -n test` deselects smoke+fit; `SMOKE=1 make -n test` deselects fit only
- `make test` — 19 passed
- README `## Roadmap` has nine phase rows; no Future Work; no badges

---
*Phase: 01-repository-foundation*
*Completed: 2026-09-01*
