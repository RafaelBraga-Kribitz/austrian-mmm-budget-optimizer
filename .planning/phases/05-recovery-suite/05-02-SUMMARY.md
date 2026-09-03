---
phase: 05-recovery-suite
plan: 02
subsystem: model-fit
tags: [md-050, md-071, md-072, md-073, p-sb, p-sc]

duration: 13min-sb-10min-sc
completed: 2026-09-03
status: complete
---

# Phase 5 Plan 2: P-SB and P-SC full fits Summary

**T-402 is green.** `make fit-synthetic` runs P-SA, P-SB, and P-SC. Both new
layers are MD-071/072 all-green after ADR-011 (`target_accept` 0.99). Wall times
are 13.0 min (P-SB) and 10.0 min (P-SC), each ≤ 35.

## Task Commits

1. **Task 1: three-layer `fit-synthetic`** — `8ef9b3f` (feat)
2. **Rung-1 eligibility: ESS_tail with divergences** — `b9425f2` (fix)
3. **Task 2: parquets + diag + PPC + BUILD_LOG** — (this commit)

## Accomplishments

- D-18: Makefile invokes `--layer P-SA`, `P-SB`, `P-SC` with no skip-if-exists.
- P-SB: 31 → 4 → 0 divergences across 0.9 / 0.95 / 0.99; R-hat 1.004; PPC 95.19%.
- P-SC: 66 → 3 → 0; first abort was ESS_tail+divergences; after D-07 eligibility
  the 0.99 attempt is all-green (R-hat 1.003, PPC 96.15%).
- MD-071 thresholds unchanged. `priors_synthetic.yaml` unchanged. No Layer R.

## Deviations from Plan

**1. [Sampler] MD-073 was required on both layers**, as the plan expected for S-C
and as P-SA already showed. Default 0.9 is not all-green; 0.99 is.

**2. [D-07] Rung-1 retry allows ESS_tail to fail alongside divergences.** Not in
the original 05-02 task text; forced by S-C's first 0.9 attempt. Not a gate
widening.

## Next Phase Readiness

05-03 (T-403 holdout VR-401) is unblocked. Do not commit `{layer}__holdout`
parquets. Do not invent Layer R.

---
*Phase: 05-recovery-suite*
*Completed: 2026-09-03*

## Self-Check: PASSED
