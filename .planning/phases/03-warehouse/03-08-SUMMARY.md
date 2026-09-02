---
phase: 03-warehouse
plan: 08
subsystem: database
tags: [export, ad-050, registry]

duration: 15min
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 8: registry-driven export writer Summary

**`scripts/export_marts.py` writes `exports/mmm_input_weekly.csv` from `ambo.common.db` (AD-030). The committed CSV is byte-identical with m0 and with two local regenerations.**

## Task Commits

1. **Task 1: registry writer + make export** — `7b8fdb7` (feat)
2. **Task 2: AD-050 contract test + committed CSV** — `a06d083` (test)

**Plan metadata:** (this commit)

## Accomplishments

- `EXPORT_REGISTRY` keyed by output filename; layers from `read_dim_layer()` (no hard-coded list).
- Atomic write, six-decimal floats, LF-only. Duplicate grain keys FAIL rather than silently deduplicate.
- CSV regenerated here via `make export` (A-5); `cmp` vs m0 `c66f971` is byte-identical (339 lines).

## Deviations from Plan

**1. [Process] 2A copy** of writer/test from m0 `36191fd` / `c66f971`. CSV regenerated here, not copied as a blob.

**2. [Process] 4B** one PR per plan.

## Issues Encountered

None. `make lint && make test` — **316 passed**, 93% coverage.

## Next Phase Readiness

Next: **03-09** (CI job 3 Windows matrix, warehouse-before-pytest, ruff format scoped to Python, M2 BUILD_LOG close).

---
*Phase: 03-warehouse*
*Completed: 2026-09-02*

## Self-Check: PASSED
