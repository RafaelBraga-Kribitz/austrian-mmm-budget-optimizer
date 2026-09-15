# ADR-014 — Roll back MD-073 rung 4

- **Status:** Accepted
- **Date:** 2026-09-15
- **Deciders:** recorded after the rung-4 Layer P refit; sampler pathology is
  reported rather than papered over.
- **Supersedes:** ADR-013
- **Related:** ADR-012; SPEC-04 MD-073; AGENTS §2 item 4

---

## Context

ADR-013 fixed `s_c = 1` because the MD-020 graph left one NUTS divergence
after rungs 1–3. That is the last prescribed ladder step. The 4×1000 nutpie
refit on the `s=1` graph produced **three** divergences (worse), the same
RED recovery pattern (VR-302 Spearman 0.600, VR-305 half-life rank, VR-303
curve MAE), and an ArviZ R-hat warning on the constant `s` Deterministic.

AGENTS §2: sampler pathologies that persist after the full ladder stop the
agent; they are not an invitation to invent a fifth rung or to widen
MD-071.

## Decision

1. **Rung 4 is rolled back.** Hill slope is sampled again as
   Truncated-Gamma(4, 3) on [0.5, 2.5] (rung 3). The reported model class
   stays the SPEC-04 Hill family.
2. **MD-020 and calendar dummies stay.** Those are spec, not ladder
   experiments. The reported graph is: normalised truncated adstock,
   promo/Advent/January + holiday, `target_accept=0.95`, non-centred
   Fourier, sampled `s`.
3. **Do not widen MD-071 or recovery gates.** A one-divergence MD-020 fit
   is reported as MD-071 RED. Energy plot is committed when divergences
   > 0. Recovery RED on VR-302/303/305 is reported as RED.
4. **No further identification attempts in this build.** Calendar (attempt
   1) and MD-020 (attempt 2) were the two focused VR-310 tries. The
   remaining miss is T-4/T-5: TV λ pulled down, paid-search half-life
   outranking TV, print curve MAE from DGP recursion vs model unit-sum
   weights on flighted spend.

## Consequences

- The reported posterior may fail MD-071 by a handful of divergences. That
  is a limitation, not a silent pass.
- Reviewers who want rung 4 on the record can read ADR-013; it is
  superseded, not deleted (EB-082).

## Spec deviations

| REQ / clause | Spec said | This ADR | Output contract preserved |
|---|---|---|---|
| MD-073 rung 4 | fix s=1 if earlier rungs fail | tried; rolled back after 1→3 divergences | Hill family restored; ladder is documented |
