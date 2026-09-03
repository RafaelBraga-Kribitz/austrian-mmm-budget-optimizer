---
phase: 05-recovery-suite
plan: 03
subsystem: validate-holdout
tags: [vr-401, holdout, mape]

duration: 14min-sa-11min-sb-10min-sc
completed: 2026-09-03
status: complete
---

# Phase 5 Plan 3: Holdout VR-401 Summary

**T-403 is green.** Conditional holdout beats seasonal-naive MAPE on P-SA and
P-SB. Every CSV row carries 90% HDI bounds and a coverage number (A-7).

## Task Commits

1. **Implementation + unit tests** — `2b6910f` (feat)
2. **CSVs + BUILD_LOG** — (this commit)

## Accomplishments

- `run_fit(..., variant="holdout")` slices first T−13; scale on the slice.
- `{layer}__holdout` names allowed; gitignored.
- `run_holdout` writes `holdout_<layer>.csv` (MAPE, naive MAPE, coverage_90).
- P-SA MAPE 0.0281 < 0.0390 (coverage 100%); P-SB 0.0334 < 0.0586 (100%).
- P-SC reported (MAPE 0.0569 < 0.0911, coverage 69.2%) — not a gate.

## Deviations from Plan

None that change the output contract. Holdout NUTS needed the same 0.99 ladder
as the full-budget fits.

## Next Phase Readiness

05-04 (OLS+HC1) and 05-05 (pymc-marketing) are unblocked in parallel with each
other. Do not invent Layer R.

---
*Phase: 05-recovery-suite*
*Completed: 2026-09-03*

## Self-Check: PASSED
