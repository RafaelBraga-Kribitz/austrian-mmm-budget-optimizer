---
phase: 04-mmm-on-s-a
plan: 04
subsystem: model-builder
tags: [pymc, nuts, smoke, md-002]

duration: 90min
completed: 2026-09-03
status: complete
---

# Phase 4 Plan 4: build_model, sample_model, and CI smoke Summary

**T-304 is green. One model definition serves every dataset. `pm.sample` lives only in `fit.sample_model`. The CI smoke fit completes with finite split-R-hat.**

## Task Commits

1. **Task 1: build_model + sample_model + D-05** — `563a17f` (feat)
2. **Task 2: smoke test (first revision)** — `67b299f` (test)
3. **Task 2b: stable Hill + prior-mean initvals + split-R-hat smoke** — (this commit)

## Accomplishments

- SPEC-04 §2 linear predictor; Fourier 52.18 / order 4 named constants (D-12).
- Free RVs match D-06; no `P-SA` / `S-A` / `layer` in `mmm.py`.
- D-05 sampler-key guard rewritten.
- Smoke: P-SA first 60 weeks, 1 chain, 200/200, ~23 s locally.
- Hill log-space + 1e-8 floor (Pitfall 8) so NUTS does not collapse to step size ~1e-24.

## Deviations from Plan

**1. [Science] Hill evaluation is log-space with a positive floor.** Same formula; finite gradients at zero adstock when s<1. Required for sampler health. No ADR (output contract unchanged).

**2. [Test] 1-chain R-hat.** ArviZ 0.23 requires 2 chains. Smoke splits 200 draws into two 100-draw halves and asserts those R-hat values are finite.

**3. [Smoke] Does not force `pytensor.config.cxx = ""`.** Unit transform tests still do. Smoke needs the C linker so real NUTS finishes inside the 15 min CI budget.

## Next Phase Readiness

04-05 posterior_io can stack. Full S-A MD-050 fit stays 04-07.

---
*Phase: 04-mmm-on-s-a*
*Completed: 2026-09-03*

## Self-Check: PASSED
