---
phase: 05-recovery-suite
plan: 04
subsystem: validate-ols
tags: [vr-601, ols, hc1]

duration: unit
completed: 2026-09-03
status: complete
---

# Phase 5 Plan 4: OLS+HC1 baseline Summary

**T-404 is green.** OLS+HC1 exists without statsmodels. The S-B table ships
unstable brand-search sign — that is the point of VR-601.

## Task Commits

1. **OLS engine + textbook test + P-SB JSON** — (this commit)

## Accomplishments

- `ols_hc1` textbook 2-regressor to 1e-8; `pinv` for collinear designs.
- Prior-mode λ = 0.25 from Beta(2, 4). Adstock via model transforms; no Hill.
- `ols_P-SB.json`: search_brand OLS sign disagrees with Bayesian ROAS.
- AST guard: no `statsmodels` in `src/`.

## Deviations from Plan

**1. [Numerics] `pinv` instead of `inv`.** Full-rank inv failed on P-SB because
Fourier + calendar flags + media are collinear. Documented; output contract
unchanged (a finite HC1 table).

## Next Phase Readiness

05-05 (pymc-marketing) is unblocked. Do not invent Layer R.

---
*Phase: 05-recovery-suite*
*Completed: 2026-09-03*

## Self-Check: PASSED
