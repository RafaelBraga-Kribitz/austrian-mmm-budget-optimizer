# Phase 5: Recovery Suite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-03
**Phase:** 5-recovery-suite
**Areas discussed:** validate→simulate.truth, plan order vs T-402 compute, HDI vs
quantiles, model curve formula, T-801 pull-forward, sensitivity scope, checker replace

---

## validate importing `simulate.truth`

| Option | Description | Selected |
|--------|-------------|----------|
| Import `response_curve_at` + `TruthFile` (Recommended) | Single home for the closed form; SIM-003 is simulate↔model | ✓ |
| Interpolate the 2× diagnostic array | Forbidden by SPEC-01 §8; injects regridding error into VR-303 | |
| Re-implement Hill in validate | Fails `test_curve_formula_has_a_single_home`; third copy of the formula | |
| Precompute MD-082 truth in a new JSON at simulate time | Extra artifact; Phase 2 already exposed a caller-supplied grid for this | |

**Notes:** → CONTEXT D-03.

---

## Plan order: metrics vs fits first

| Option | Description | Selected |
|--------|-------------|----------|
| T-401 then T-402 (Recommended) | Fixture-tested engine; fits are a separate compute PR | ✓ |
| T-402 then T-401 | Blocks metrics on 30–70 min of NUTS; worse review surface | |
| Combine T-401+T-402 | Violates 4B; one PR would mix science code and 6 MB of parquet | |

**Notes:** → CONTEXT D-01, D-02. NUTS for P-SB may run in the background during 05-01
and is committed only in 05-02.

---

## 90% HDI implementation

| Option | Description | Selected |
|--------|-------------|----------|
| `arviz.hdi` (Recommended) | Matches the spec's word "HDI" | ✓ |
| Equal-tail 5th/95th percentiles | Common but is not an HDI | |

**Notes:** → CONTEXT D-07.

---

## Model-side response curve

| Option | Description | Selected |
|--------|-------------|----------|
| Steady-state: adstock(constant x_scaled) = x_scaled because weights sum to 1 (Recommended) | Matches MD-020; cheap; comparable to DGP `x/(1-λ)` via VR-303 shape metric | ✓ |
| Simulate T weeks of constant spend and take the last week | Finite-L burn-in; more code; same SS limit | |
| Use DGP `x/(1-λ)` on posterior λ | Scores the model with the simulator's saturation input — circular | |

**Notes:** → CONTEXT D-08.

---

## T-801 style pull-forward

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal local rcParams in `validate/report.py` (Recommended) | WBS allows it; T-801 stays Phase 9 | ✓ |
| Pull T-801 into this phase | Extra plan in a 2.5 d budget; not required for M3 | |

**Notes:** → CONTEXT D-14.

---

## VR-503 / sensitivity.py this phase

| Option | Description | Selected |
|--------|-------------|----------|
| Defer all VR-501…504 including VR-503 (Recommended) | ROADMAP success criterion 3 names VR-401 and VR-602 only | ✓ |
| Run VR-503 on S-B now | Extra full-budget fit (`P-SB__flat`); Phase 7 centrepiece | |
| Empty `sensitivity.py` stub | New module ⇒ contract + layout test for a function that only raises | |

**Notes:** → CONTEXT D-15.

---

## `make fit-synthetic` skip-if-exists

| Option | Description | Selected |
|--------|-------------|----------|
| Always run all three layers (Recommended) | No silent stale parquet | ✓ |
| Skip when parquet exists | Hides a bad artifact; operators can still call the CLI for one layer | |

**Notes:** → CONTEXT D-18.
