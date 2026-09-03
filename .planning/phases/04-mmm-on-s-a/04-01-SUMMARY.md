---
phase: 04-mmm-on-s-a
plan: 01
subsystem: model-transforms
tags: [pymc, transforms, numpy, fiterror]

duration: 45min
completed: 2026-09-03
status: complete
---

# Phase 4 Plan 1: Transforms, FitError, numpy pin Summary

**T-301 is green. `import pymc` works after a lock-only numpy `<2.4` constraint. Model-side adstock/Hill/scaling live in `transforms.py` with no simulator imports and no `np.convolve` in `src/`. `FitError` is the model-package `AmboError` subclass.**

## Task Commits

1. **Planning corpus** — `8260a20` (docs)
2. **Task 1: numpy `<2.4` lock constraint (D-02)** — `409db73` (chore)
3. **Task 2–3: FitError + transforms + tests + contracts** — `fc53a84` (feat)
4. **Task 4: BUILD_LOG, ROADMAP, STATE** — (this commit)

## Accomplishments

- `[tool.uv] constraint-dependencies = ["numpy>=1.26,<2.4"]`. Locked: numpy 2.3.5, numba 0.65.1 (transitive), pymc 5.28.5, pytensor 2.38.3. SPEC-08 `[project]` range unchanged.
- `FitError(AmboError)` for all-zero channels, missing spend columns, invalid `L`.
- `geometric_adstock_weights` / `adstock_convolve` (unrolled causal pytensor graph) / `hill_saturation` / `ScaleFactors` / `compute_scale_factors` / `to_model_scale` / `from_model_scale`.
- Unit tests: impulse-first causality, pytensor vs numpy 1e-10, Hill(K)=0.5, scaling round-trip, grep guards against `convolve`, `ambo.simulate`, `load_settings`.
- `make lint && make test` — **332 passed**, 92% coverage.

## Deviations from Plan

**1. [Lock] numpy cap is `<2.4`, not CONTEXT D-02's sketched `<2.5`.** NumPy 2.4 removed `trapz`; the previously locked Numba still overloaded it. Tighter lock-only constraint, same declared SPEC-08 range. No ADR.

**2. [Tests] `pytensor.config.cxx = ""` in `test_transforms.py`.** Unit tests must not require `Python.h`. Production sampling may still use C when cxx is available.

**3. [Tests] Hypothesis round-trip uses rtol=atol=1e-12**, not pure atol — large revenues fail a 1e-12 absolute check.

**4. [Process] 4B** one PR per plan. Phase 4 is not on `m0-bootstrap`.

## Next Phase Readiness

04-02 (T-303 PriorConfig + D-01 `max_fit_minutes`) is unblocked. Do not author `priors_real.yaml`. MD-070 stays in 04-03, before any fit.

---
*Phase: 04-mmm-on-s-a*
*Completed: 2026-09-03*

## Self-Check: PASSED
