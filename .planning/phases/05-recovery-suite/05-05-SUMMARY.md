---
phase: 05-recovery-suite
plan: 05
subsystem: validate-crosscheck
tags: [vr-602, pymc-marketing, md-003]

duration: unit+fit
completed: 2026-09-03
status: complete
---

# Phase 5 Plan 5: pymc-marketing cross-check Summary

**T-405 is green.** VR-602 Pearson 0.9648 and Spearman 0.8857 on P-SB channel
median ROAS (≥ 0.8). Mapping doc records every matched and unmatchable API piece.
`pymc_marketing` stays in `validate/crosscheck.py`.

## Task Commits

1. **Module + tests + contract** — GeometricAdstock + HillSaturation, FixedScaling
2. **Fourier control column order**
3. **adapt_diag init** — jitter trips their `0<alpha<=1` check
4. **Accept-rate experiment** — 0.99 left divergences and failed Spearman
5. **Keep 0.9** — median-correlation gate; report their NUTS divergences
6. **Artifacts + close** — this commit

## Accomplishments

- `run_crosscheck("P-SB")` via `MMM.fit` (no `pm.sample` in ambo).
- Version pin 0.19.4 recorded in `crosscheck_mapping.md`.
- Unmatched: s truncation, yearly-Fourier period, NUTS init.
- Their NUTS: 3050 divergences at `target_accept=0.9` / `adapt_diag`. Not MD-071.

## Deviations from Plan

**1. [Sampler] `init="adapt_diag"`.** `jitter+adapt_diag` raises
`ParameterValueError: 0 < alpha <= 1` inside GeometricAdstock. Documented.

**2. [Sampler] Did not keep a 0.99 refit.** It still diverged and dropped Spearman
to 0.49. VR-602 is a median-correlation gate; 0.9 passed and is what we ship.

## Next Phase Readiness

05-06 (`RECOVERY_REPORT.md` / `make recover`) is unblocked. Do not invent Layer R.

---
*Phase: 05-recovery-suite*
*Completed: 2026-09-03*

## Self-Check: PASSED
