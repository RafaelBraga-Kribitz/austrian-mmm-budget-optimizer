---
phase: 04-mmm-on-s-a
plan: 06
subsystem: model-diagnostics
tags: [md-071, md-072, md-074, arviz]

duration: 35min
completed: 2026-09-03
status: complete
---

# Phase 4 Plan 6: diagnostics Summary

**T-306 is green. Injected divergences fail `DiagGates.standard()` and pass `layer_r()`. Missing PPC fails MD-072 instead of being dropped. The report writer is ready for 04-07.**

## Task Commits

1. **Task 1: diagnostics module** — `6cf793c` (feat)
2. **mypy untyped ArviZ calls** — `86f68f6` (fix)
3. **BUILD_LOG / ROADMAP / STATE** — (this commit)

## Accomplishments

- Explicit `standard()` / `layer_r()` constructors; no n_obs heuristic.
- Pure `run_diagnostics`; writer emits markdown + PPC PNG + energy PNG when divergences > 0.
- `reports/model/.gitkeep`.

## Deviations from Plan

**1. [API] `write_diag_report` takes `idata=`.** 03_MODULES listed `(res, layer)` only; plots need the InferenceData. Documented in MODULE_CONTRACTS. Not an ADR (output path unchanged).

**2. [Process] 4B** one PR per plan.

## Next Phase Readiness

04-07 can run the real P-SA MD-050 fit, write `P-SA.parquet` + `diag_P-SA.md`, and apply MD-073 only if MD-071 is red.

---
*Phase: 04-mmm-on-s-a*
*Completed: 2026-09-03*

## Self-Check: PASSED
