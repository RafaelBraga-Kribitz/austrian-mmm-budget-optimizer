---
phase: 05-recovery-suite
plan: 01
subsystem: validate-recovery
tags: [recovery, vr-301, gates, truth]

duration: 90min
completed: 2026-09-03
status: complete
---

# Phase 5 Plan 1: Recovery metrics engine Summary

**T-401 is green.** VR-301…306 statistics are computed from model-side transforms
and `truth.json`, and scored against a YAML table that mirrors SPEC-05 §3
cell-for-cell. Constructed-posterior ROAS matches an independent numpy reference
to 1e-8. P-SB/P-SC parquets are **not** in this PR (05-02).

## Task Commits

1. **Planning corpus** — `725903e` (docs)
2. **Task 2: ValidationError + gates YAML + recovery.py + tests + contracts** — (this commit)

## Accomplishments

- Phase 5 CONTEXT D-01…D-26 and 05-01…05-10 plans on ROADMAP.
- `config/recovery_gates.yaml` is the only home of SPEC-05 §3 thresholds.
- `compute_recovery` / `evaluate_gates` write JSON side-files; tests inject bundle/frame/truth.
- `response_curve_at` is used for VR-303 (no interpolation, no `simulate.dgp`).
- `arviz.hdi` for 90% intervals. Zero-max true curves report `mae_pct=None`.
- `make lint && make test` — **390 passed**, 1 deselected (smoke), 91% coverage.

## Deviations from Plan

None that change the output contract. `pytensor.function` is compiled in this
module (not in `transforms.py`) so recovery can evaluate 1000 draws without a
second Hill implementation.

## Next Phase Readiness

05-02 (T-402 P-SB/P-SC full fits) is unblocked. A P-SB MD-050 fit already
completed on this machine (all-green at `target_accept` 0.99, 778 s) and must be
committed only in 05-02, not here.

---
*Phase: 05-recovery-suite*
*Completed: 2026-09-03*

## Self-Check: PASSED
