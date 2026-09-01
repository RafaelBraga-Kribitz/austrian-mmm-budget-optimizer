---
phase: 01-repository-foundation
plan: 04
subsystem: infra
tags: [config, settings, logging, redaction, pydantic]
requires:
  - phase: 01-02
    provides: "pyproject.toml, src/ambo package, yaml/pydantic/dotenv deps"
  - phase: 01-03
    provides: "MODULE_CONTRACTS.md entries for config/errors/logging"
provides:
  - "config/settings.yaml — seven channels, L=8, paths, MD-050 sampler, scenario registry"
  - "src/ambo/common/config.py — cached Settings with extra=forbid"
  - "src/ambo/common/logging.py — get_logger + PrivatePathFilter"
  - "src/ambo/common/errors.py — AmboError / ConfigError"
affects: [01-05, 01-07, 01-08]
key-files:
  created:
    - config/settings.yaml
    - src/ambo/common/config.py
    - src/ambo/common/errors.py
    - src/ambo/common/logging.py
    - tests/unit/test_config.py
    - tests/unit/test_logging.py
  modified:
    - docs/MODULE_CONTRACTS.md
    - pyproject.toml
    - .gitignore
key-decisions:
  - "Files copied from verified m0-bootstrap 5f12504 (2A), including CR-02 traceback redaction"
  - "Settings is BaseModel not BaseSettings (no pydantic-settings; EB-030)"
  - "yaml mypy override rather than types-PyYAML (EB-030)"
requirements-completed: [REQ-dl8-quality, REQ-scope-out]
duration: 20min
completed: 2026-09-01
status: complete
---

# Phase 1 Plan 4: Settings and logging Summary

**Single configuration home (`config/settings.yaml`) plus typed `load_settings()` and a logger factory that redacts the private-drop path.**

## Task Commits

1. **Task 1** — `18cfa31` settings.yaml (also accidentally staged Task 2–3 modules; EB-082, not amended)
2. **Task 2** — `dccbeae` yaml mypy override + `.coverage` gitignore (implementation files already in `18cfa31`)
3. **Task 3** — no separate commit; logging landed in `18cfa31` from the m0 tree (CR-02 included)

**Plan metadata:** this commit.

## Deviations from Plan

**1. [Process] Combined first commit.** `git add` for Task 1 included config/errors/logging and both unit tests. Task 3 then had nothing left to commit. Content matches m0 `5f12504` (diff empty). Not rewritten.

**2. [Process] One PR per plan (4B)** not per task.

**Total deviations:** 2 process. No scope creep.

## Self-Check: PASSED

- Task 1 YAML probe: five keys, SPEC-02 channel order, L=8, six sampler keys, s_a/s_b/s_c
- `uv run pytest tests/unit/test_config.py tests/unit/test_logging.py -q --no-cov` — 19 passed
- `uv run mypy src/ambo` — Success, 11 source files
- `load_settings()` identity cache: ok
- Plant `target_accept` in `errors.py` → `test_sampler_keys_appear_nowhere_else_in_src_ambo` FAIL; reverted → PASS
- MODULE_CONTRACTS names `BaseModel`, not `BaseSettings`

---
*Phase: 01-repository-foundation*
*Completed: 2026-09-01*
