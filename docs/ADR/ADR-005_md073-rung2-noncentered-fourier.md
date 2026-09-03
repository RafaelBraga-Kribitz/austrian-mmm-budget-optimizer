# ADR-005 — MD-073 rung 2: non-centered Fourier block

- **Status:** Ratified
- **Date:** 2026-09-03
- **Deciders:** —
- **Supersedes:** —
- **Related:** MD-073, MD-071, SPEC-04 §7, WBS T-307, ADR-006 (reserved slot)

---

## Context

The P-SA full-budget fit at MD-050 (`target_accept` from `Settings.sampler`) produced
31 divergences. All other MD-071/072 gates were green (R-hat 1.004, ESS bulk/tail
> 400, BFMI > 0.3, PPC 93%). MD-073 rung 1 (raise `target_accept` to 0.95, without
editing `Settings.sampler`) reduced divergences to 17 and left every other gate
green. MD-073 requires an ADR when leaving rung 1. The next prescribed rung is a
non-centered Fourier block.

## Decision

Adopt MD-073 rung 2 as the model parameterization: `gamma_sin` and `gamma_cos` are
`Deterministic` reconstructions `μ + σ · offset` of unit-normal free RVs
`gamma_sin_offset` and `gamma_cos_offset`. The reported Fourier coefficient names
remain `gamma_sin` / `gamma_cos` in the posterior (D-06 output contract). The
centered normals are no longer free RVs.

Rung 1 remains available as a retry when the only red gate is divergences.
`Settings.sampler.target_accept` stays the MD-050 value.

## Consequences

`build_model` is still one definition. Free-RV tests list the offset names.
If rung 2 plus optional rung-1 retry still leaves divergences, the next rungs
(tighten `s`, then fix `s = 1`) require a new ADR and, for rung 4, a Layer P
recovery rerun.

## Spec deviations

| Document | Section | Change | REQ IDs |
|----------|---------|--------|---------|
| — | — | Fourier sampling is non-centered; reported names unchanged. Interpretation of MD-073, not a gate widening. | REQ-q1-truth-recovery |
