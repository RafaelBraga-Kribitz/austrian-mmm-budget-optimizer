---
phase: 04-mmm-on-s-a
plan: 07
subsystem: model-fit
tags: [md-050, md-071, md-072, md-073, nuts]

duration: 16min-fit
completed: 2026-09-03
status: complete
---

# Phase 4 Plan 7: P-SA full-budget fit Summary

**T-307 is green. `make fit-synthetic` runs MD-050 NUTS on P-SA. The committed
posterior is MD-071/072 all-green after ADR-011 (`target_accept` 0.99). Wall time
of the green attempt is 7.4 min (≤ 35).**

## Task Commits

1. **Task 1: CLI + make target** — `bad1b4b` (feat)
2. **MD-073 rung 1 (0.95)** — `d7ef886` (fix)
3. **Rebuild model before retry** — `a9b6d52` (fix)
4. **ADR-005 non-centered Fourier** — `70c261a` (fix)
5. **ADR-009 tighten s helper** — `2eeac44` (fix)
6. **ADR-010 s=1 (later superseded)** — `8692ac6` (fix)
7. **ADR-011 free s + 0.99** — `de3d78c` (fix)
8. **Task 2: parquet + diag + BUILD_LOG** — (this commit)

## Accomplishments

- `run_fit` / `python -m ambo.model.fit --layer P-SA`; variants parsed then refused.
- `pm.sample` still only in `sample_model`. Model rebuilt each retry.
- Committed `data/posteriors/P-SA.parquet`, `reports/model/diag_P-SA.md`, `ppc_P-SA.png`.
- Green gates: R-hat 1.003, ESS 1966/1503, divergences 0, BFMI 0.76, PPC 93%.

## Deviations from Plan

**1. [Sampler] MD-073 was required.** Default MD-050 `target_accept` 0.9 had 32
divergences. Ladder + ADR-011 0.99 reached 0. Settings.sampler unchanged.

**2. [ADR-010] Rung 4 (s=1) was attempted and superseded.** It did not reach 0
divergences and produced NaN R-hat on constant `s`. Hill `s` remains a free RV.

**3. [Process] 4B** one PR per plan; several task-2 ladder commits.

## Next Phase Readiness

04-08 (`elicit.py` converters + Phase 4 close) is unblocked. Do not invent
`PRIOR_ELICITATION.md` or `priors_real.yaml`.

---
*Phase: 04-mmm-on-s-a*
*Completed: 2026-09-03*

## Self-Check: PASSED
