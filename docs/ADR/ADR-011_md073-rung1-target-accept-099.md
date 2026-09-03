# ADR-011 — Restore free `s`; extend MD-073 rung 1 to `target_accept` 0.99

- **Status:** Ratified
- **Date:** 2026-09-03
- **Deciders:** —
- **Supersedes:** ADR-010
- **Related:** MD-073, MD-071, SPEC-04 §2 and §7, WBS T-307, ADR-005, ADR-009, ADR-010

---

## Context

MD-073 rung 4 (ADR-010, `s_c = 1`) was applied after rungs 1–3 left 2 divergences.
At `target_accept` 0.95 the s=1 fit still had **2 divergences in 4000 draws**. Other
MD-071/072 gates stayed green. Constant `s` produced NaN R-hat (zero within-chain
variance). The two remaining divergences were heterogeneous boundary visits
(`search_brand` `k` → 0 on one draw, `lam` → 0 on the other), not a single Hill
slope funnel that fixing `s` would remove.

Rung 4 therefore changed the model class without discharging MD-071, and would have
forced Phase 5 to recover a DGP that still has free Hill `s` against a logistic
saturation model. The letter of rung 1 stops at 0.95; 2/4000 divergences at 0.95
is the regime where a further `target_accept` raise is the same mechanism, not a
new parameterization.

## Decision

1. Supersede ADR-010. `s` is again a truncated-Gamma free RV (MD-040 YAML /
   SPEC-04 §2). `build_model` is not a logistic-saturation model class.
2. After a divergences-only red at `target_accept` 0.95, retry once at
   `target_accept` 0.99. `Settings.sampler` stays at the MD-050 value (0.9).
   Rung 2 (ADR-005 non-centered Fourier) remains the standing Fourier block.

## Consequences

A third NUTS attempt is possible on `make fit-synthetic` (~4–5 min each here).
If 0.99 is still divergences-only red, the written MD-073 ladder plus this
rung-1 extension is exhausted and the next record is a gate-widening ADR or a
human stop (AGENTS §2).

## Spec deviations

| Document | Section | Change | REQ IDs |
|----------|---------|--------|---------|
| `docs/SPEC-04_mmm_model.md` | MD-073 (1) | Allows a second `target_accept` raise to 0.99 after 0.95. Sampler config unchanged. | REQ-q1-truth-recovery |
