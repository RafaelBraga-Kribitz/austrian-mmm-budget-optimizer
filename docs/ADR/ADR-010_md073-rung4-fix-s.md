# ADR-010 — MD-073 rung 4: fix Hill slope `s_c = 1`

- **Status:** Ratified
- **Date:** 2026-09-03
- **Deciders:** —
- **Supersedes:** —
- **Related:** MD-073, MD-071, MD-040, SPEC-04 §2 and §7, WBS T-307, ADR-005, ADR-009

---

## Context

MD-073 rungs 1–3 left P-SA with 2 divergences on Layer P (MD-071 requires 0). Other
gates stayed green (R-hat 1.004, ESS bulk/tail > 400, BFMI > 0.3, PPC 93%).

The two divergent draws (chain 0, draws 59 and 311) sit in a Hill funnel on
`search_brand`: `k` collapsed toward 0.13–0.24 (non-divergent mean ≈ 1.61) while `s`
was steep (≈ 2.15–2.29 vs non-divergent mean ≈ 1.31). That is the K/s/β tradeoff
SPEC-04 §7 and trap T-5 describe. The prescribed next rung is fix `s_c = 1`
(logistic / Michaelis–Menten saturation). It changes the model class. Phase 5
recovery has not run yet, so the required Layer P recovery rerun is still ahead,
not a rewrite of completed work.

`config/priors_synthetic.yaml` still records MD-040's truncated-Gamma `s` so the
channel-agnostic prior test is unchanged. That hyperparameter is not sampled.

## Decision

`s` is no longer a free RV. `build_model` registers `s` as a `Deterministic` of
ones (one per channel) so the D-06 reported name remains in the posterior. Hill
therefore uses `a / (a + K)` (the existing log-space Hill at `s = 1`). Rungs 2
(ADR-005 non-centered Fourier) and 4 are the standing parameterization. Rung 1
(`target_accept` 0.95) remains a divergences-only retry. Rung 3's fit-time `s`
copy (ADR-009) is retained as a tested helper but is not applied, because `s` is
not sampled.

## Consequences

Recovery gates (SPEC-05) stay on ROAS and response-curve *shape* at observed
spend, not on point recovery of `K`/`s` (T-5). If this parameterization still
diverges after rung 1, the MD-073 ladder is exhausted and the human is asked
(AGENTS §2).

## Spec deviations

| Document | Section | Change | REQ IDs |
|----------|---------|--------|---------|
| `docs/SPEC-04_mmm_model.md` | §2 / MD-073 | `s_c` is fixed at 1 instead of truncated Gamma. Prescribed rung 4, not a silent gate widening. | REQ-q1-truth-recovery |
