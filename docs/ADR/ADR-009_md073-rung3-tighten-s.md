# ADR-009 — MD-073 rung 3: tighten the Hill slope prior at fit time

- **Status:** Ratified
- **Date:** 2026-09-03
- **Deciders:** —
- **Supersedes:** —
- **Related:** MD-073, MD-071, MD-040, SPEC-04 §4 and §7, WBS T-307, ADR-005

---

## Context

The P-SA full-budget fit still had 3 divergences after MD-073 rungs 1 and 2: raised
`target_accept` 0.95 (Settings.sampler unchanged) plus the non-centered Fourier block
(ADR-005). Every other MD-071/072 gate was green (R-hat 1.004, ESS bulk/tail > 400,
BFMI > 0.3, PPC 93%). MD-071 on Layer P requires divergences = 0; MD-074's ≤ 5
tolerance is Layer R only. The next prescribed rung is a tighter Hill slope prior:
Gamma(4, 3) truncated to [0.5, 2.5], versus the MD-040 YAML of Gamma(3, 2) truncated
to [0.3, 3.0].

`config/priors_synthetic.yaml` is the frozen Layer P prior file. Editing it would
silently retune MD-040 in response to a sampler-health failure (A-6's cousin on
Layer P: priors are not knobs). The override must be a documented fit-time copy.

## Decision

Apply MD-073 rung 3 as a frozen `PriorConfig.model_copy` that sets every channel's
`s` to Gamma(4, 3) truncated [0.5, 2.5]. The YAML on disk is unchanged; MD-040 unit
tests continue to assert Gamma(3, 2) on [0.3, 3.0]. The parquet provenance hash
remains the YAML sha256; the diag report notes record the override.

Rungs 1 and 2 stay in force on this attempt (`target_accept` 0.95, non-centered
Fourier). `Settings.sampler` is not edited.

## Consequences

`run_fit` retries once more when the only red gate is divergences. If this attempt
is still red, the next prescribed rung is fix `s = 1` (logistic saturation). That
changes the model class and forces a Layer P recovery rerun (Phase 5); it is a
separate ADR, not this one.

## Spec deviations

| Document | Section | Change | REQ IDs |
|----------|---------|--------|---------|
| — | — | Fit-time s prior is tighter than MD-040 YAML. Interpretation of MD-073 rung 3, not a YAML or gate edit. | REQ-q1-truth-recovery |
