# ADR-013 — MD-073 rung 4: Hill slope fixed at 1

- **Status:** Accepted
- **Date:** 2026-09-15
- **Deciders:** recorded on the Layer P pipeline branch after MD-071 failed with
  one divergence on the MD-020 graph; the reparameterisation ladder (SPEC-04
  §7 / MD-073) is exhausted at this rung.
- **Supersedes:** —
- **Related:** ADR-012; SPEC-04 MD-021, MD-073; AGENTS T-5

---

## Context

MD-073 requires that if MD-071 fails, the reparameterisation ladder is applied
in order, one rung per attempt:

1. `target_accept=0.95`
2. non-centred Fourier
3. tighten `s_c` to Gamma(4, 3) truncated to [0.5, 2.5]
4. fix `s_c = 1` (logistic saturation) — this changes the model class

Rungs 2 and 3 were already in the rebuilt package. Rung 1 cleared 53
divergences on the calendar-controlled unnormalised graph (0 divergences,
MD-071 green). Enabling MD-020 normalised adstock (spec, not a ladder skip)
reintroduced **one** divergence in 4×1000 draws, at a low search `K` with
`s ≈ 1.53` — the Hill `K`/`s`/`β` funnel (T-5).

Rungs 1–3 are already applied. The remaining prescribed step is rung 4.

## Decision

1. **Hill slope is not sampled.** `s_c = 1` for every channel, stored as a
   PyMC `Deterministic` so evaluate / optimiser still read `s` from the
   posterior. The DGP keeps its disclosed slopes (0.9–1.3); the mismatch is
   the point of the ladder.
2. **Recovery gates are not widened.** VR-301…306 stay at the five-channel
   analogue in `ambo.evaluate`. If they stay RED, the report says RED.
3. **MD-020 stays.** Unit-sum truncated weights are SPEC-04, not a tuning
   knob. Calendar dummies stay (SPEC-04 §2).

## Consequences

- The reported model is logistic saturation, not the full Hill family.
  Curve-shape recovery (VR-303) is the gate that must still pass; point
  recovery of `s` is not a gate (T-5) and is now impossible by construction.
- Layer P recovery must be regenerated on this graph. A 4×1000 posterior
  from a sampled-`s` model is not comparable and must not be reported.

## Spec deviations

| REQ / clause | Spec said | This ADR | Output contract preserved |
|---|---|---|---|
| SPEC-04 §4 `s_c` | Gamma(3, 2) trunc [0.3, 3.0] | `s_c = 1` (MD-073 rung 4) | Hill formula unchanged at s=1; β still a contribution |
| MD-021 | Hill exactly as SPEC-01 §2.2 | Same formula, slope locked | Evaluators still call `hill` / `hill_pt` |
