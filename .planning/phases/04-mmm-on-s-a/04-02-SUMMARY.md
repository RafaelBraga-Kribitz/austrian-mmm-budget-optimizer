---
phase: 04-mmm-on-s-a
plan: 02
subsystem: model-priors
tags: [priors, settings, md-040]

duration: 25min
completed: 2026-09-03
status: complete
---

# Phase 4 Plan 2: PriorConfig and max_fit_minutes Summary

**T-303 is green. `max_fit_minutes: 35` lives on `Settings` (D-01 / ADR-006). Layer P priors are an explicit seven-channel YAML with identical MD-040 values. `priors_real.yaml` was not created.**

## Task Commits

1. **Task 1: max_fit_minutes on Settings** — `6347ec1` (feat)
2. **Task 2: PriorConfig + priors_synthetic.yaml + MD-040** — (this commit)

## Accomplishments

- Top-level `max_fit_minutes: 35`; `SamplerConfig` unchanged.
- `load_priors` → frozen `PriorConfig`; extra keys fail; taxonomy order enforced.
- Seven channels value-equal: Beta(2,4) / Gamma(2, 1.3) / trunc Gamma(3,2)[0.3, 3.0] / HalfNormal(0.15).
- Globals match SPEC-04 §4.

## Deviations from Plan

**1. [Schema] `NormalParams` added** for SPEC-04 §4 globals. The plan listed Beta/Gamma/TruncGamma/HalfNormal; globals are Normal and need a type. Not an ADR (output contract unchanged).

**2. [Process] 4B** one PR per plan.

## Next Phase Readiness

04-03 (MD-070) can stack in parallel with 04-04 once this merges into the stack. Do not author `priors_real.yaml`.

---
*Phase: 04-mmm-on-s-a*
*Completed: 2026-09-03*

## Self-Check: PASSED
