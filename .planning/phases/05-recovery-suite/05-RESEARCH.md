# Phase 5: Recovery Suite - Research

**Researched:** 2026-09-03
**Domain:** SPEC-05 recovery gates; model-side ROAS; MD-082 curves; holdout; OLS+HC1;
pymc-marketing 0.19.4; SSOT; git-ancestry
**Confidence:** HIGH on contracts, truth schema, posterior_io, existing checkers, and
the WARNING-4 grid rule (read in full). MEDIUM on P-SB/P-SC sampler health until 05-02
runs (S-C is the named stress case). MEDIUM on pymc-marketing 0.19.4 API match-up until
T-405's mapping doc is written against the installed package.

<user_constraints>
Locked 1A 2A 3A 4B. D-01…D-26 from CONTEXT.md are in force. Do not re-litigate WARNING 4,
MD-020's deliberate parameterization mismatch, or Layer R. Do not import `ambo.simulate`
from `ambo.model`. Do not checksum draws.
</user_constraints>

<phase_requirements>
| ID | Description | Research support |
|----|-------------|------------------|
| REQ-q1-truth-recovery (owning) | VR-3xx green per scenario at spec thresholds | Gate table is DATA (`config/recovery_gates.yaml`); metrics from model transforms + `truth.json` |
| REQ-dl2-recovery-report | Generated report, §8 order, all-green table, VR-304 section | T-406 templates with slots; doc-structure test |
| REQ-e2-layer-order | GB-501/502 in CI | Script + CI job 5 already exist; T-409 extends tests |
| REQ-e4-numeric-ssot | GB-301…303 | Checker exists; T-408 adds generator + real rows |
| REQ-dl1-reproducible-pipeline (contributing) | `make recover` from committed parquets, zero sampling | VR-703; D-24 |
</phase_requirements>

## Summary

Phase 5 is the hinge: a generated report that a reviewer can regenerate without NUTS,
plus a commit that GB-501 will point at forever. Three findings change the plans:

1. **The truth curve evaluator already exists and must be called, not copied.**
   `response_curve_at` is the single home (`test_curve_formula_has_a_single_home`).
   Validate importing `ambo.simulate.truth` is the designed consumption path for
   VR-303. Interpolating `truth.json`'s 0…2× array would both violate SPEC-01 §8 and
   inject regridding error into an M3 exit gate.

2. **ROAS cannot go through the simulator.** WBS T-401: "Σm_c/Σx_c computed from
   posterior draws through model-side transforms + back-transform". MD-020 normalized
   finite convolution vs SPEC-01 raw recursion is the mismatch that makes recovery
   *evidence*. Using `dgp.hill` to score the posterior would make VR-301 circular.

3. **The governance scripts are already real.** `check_layer_order.py` and
   `check_ssot_consistency.py` are vacuously-correct M0 predicates with planted-violation
   tests. T-408/T-409 fill them with work; they do not replace them. CI jobs 4 and 5
   already invoke them. `generate_ssot.py` is the missing producer.

**Primary recommendation:** Execute D-01's ten stacked plans. Land the metrics engine
on fixtures first (05-01). Commit P-SB/P-SC posteriors next (05-02), expecting MD-073
on S-C. Do not invent Layer R. Do not widen a red gate.

## Standard stack

| Piece | Version / pin | Role this phase |
|-------|---------------|-----------------|
| Python | 3.12 | runtime |
| numpy / scipy | locked | ROAS vectorization, Spearman, OLS+HC1 |
| pytensor | via pymc; `cxx=/usr/bin/g++` | compiled model adstock/Hill for recovery |
| pymc / arviz | 5.28.5 / 0.23.4 | holdout refit; `az.hdi` |
| pyarrow | 22.0.0 (ADR-008) | load committed parquets |
| pydantic | already | frozen RecoveryMetrics / GateResults |
| pymc-marketing | **0.19.4** | T-405 only |
| matplotlib | already (arviz extra) | recovery plots in T-406 |

No new direct dependency (EB-030). statsmodels is explicitly forbidden (T-404 notes).

## Architecture (this repo)

1. **PosteriorBundle** (`posterior_io.py`) already carries `ScaleFactors` in parquet
   schema metadata. Recovery never accepts a parquet without them (existing `FitError`).
2. **`from_model_scale`** multiplies `revenue` by `revenue_mean`. Media contribution in
   the model is in scaled-revenue units (`beta * Hill(adstock(x_scaled))`), so
   `m_eur = m_scaled * revenue_mean` is the MD-030 inverse. Do not invent a second
   scaling pair.
3. **Normalized adstock SS.** Weights sum to 1 ⇒ constant spend `x` has steady-state
   adstock `x`. That is the model-side response-curve evaluation (D-08). The DGP curve
   uses `a = x / (1-λ)`. Different on purpose (MD-020). VR-303 gates *shape* as % of
   true-curve max, not parameter recovery (T-5).
4. **Fit ladder** already in `fit.py`: 0.9 → 0.95 → 0.99, rebuild model each attempt
   (logp None otherwise). T-402 reuses it. Do not add rung 3/4 to the automatic path.
5. **Holdout scale factors** must be computed on the training slice (RK-M2-4). Reusing
   full-window means leaks the holdout spend distribution into scaling.
6. **BP-D-06 names.** Full-budget: `P-SA`, `P-SB`, `P-SC`. Holdout local:
   `P-SA__holdout` etc. — extend `_PRIMARY_NAMES`; do not commit those parquets.
7. **AD-030.** Validate reads spend via `read_mmm_input`, not by opening DuckDB itself
   and not by reading `data/synthetic/*.csv` in production (tests may inject frames).

## Pitfalls

| ID | Pitfall | Mitigation |
|----|---------|------------|
| P1 | Using DGP Hill/adstock to compute model ROAS | D-06; independence test already forbids model↔simulate; validate must not import `dgp.py` |
| P2 | Interpolating the 2× truth grid onto MD-082 | Call `response_curve_at` (D-03, D-08) |
| P3 | Equal-tail 5/95 as "HDI" | `az.hdi` (D-07) |
| P4 | `max(truth)==0` MAE% → NaN fails YAML/JSON and the median | Report `null`; exclude from median (D-08) |
| P5 | Including `other` (absent on Layer P) in "6 of 6" | Channels from bundle `spend_means` keys (D-05) |
| P6 | Checksum of parquet bytes / draws | T-6; golden bands are ±0.15·SD on medians |
| P7 | `pm.sample` twice on one `pm.Model` | Already handled in `fit.py`; holdout builds a fresh model |
| P8 | Holdout scale factors from full window | Compute on first T−13 only |
| P9 | `make recover` silently sampling | D-24; no import of `sample_model` from `validate/report.py` |
| P10 | Replacing layer-order / SSOT checkers | D-16, D-17 |
| P11 | statsmodels as a new dep | D-22 |
| P12 | pymc-marketing import leaking | existing `test_pymc_marketing_imported_only_in_validate_crosscheck` |
| P13 | S-C divergences → widen MD-071 | MD-073 ladder; stop after two focused attempts |
| P14 | Shared DuckDB with `make test` during a fit | Do not run tests that write the warehouse in parallel with NUTS |
| P15 | `core.hooksPath` eof fixer on BUILD_LOG | trailing newline; do not amend |

## SPEC-05 §3 thresholds (copied into YAML; do not restate in Python)

| Gate | S-A | S-B | S-C |
|------|-----|-----|-----|
| VR-301 coverage | ≥5/6 | ≥4/6 | ≥4/6 incl. zero channel |
| VR-302 Spearman | ≥0.83 | ≥0.7 | not gated |
| VR-303 MAE% | ≤15 / median ≤10 | ≤25 / ≤15 | reported, not gated |
| VR-304 zero-effect | — | — | P(ROAS<0.2)≥0.7 and share≤3% |
| VR-305 HL direction | required | required | required |
| VR-306 media share | ±10 pp | ±10 pp | ±10 pp |

## Open questions (resolved in CONTEXT)

| Q | Resolution |
|---|------------|
| May validate import simulate.truth? | Yes (D-03) |
| HDI vs quantile? | HDI (D-07) |
| Model response-curve formula? | SS adstock = x_scaled (D-08) |
| T-801 this phase? | No (D-14) |
| VR-503 this phase? | No (D-15) |
| Skip existing parquet in fit-synthetic? | No (D-18) |

## References

- `docs/SPEC-05_validation_recovery.md` (whole)
- `docs/SPEC-04_mmm_model.md` MD-080…083, MD-020
- `docs/SPEC-01_ground_truth_simulator.md` §8 grid note
- `docs/SPEC-09_governance_quality.md` §3–§5
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` T-401…T-410
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` §5, §9–§10
- `src/ambo/model/{transforms,posterior_io,fit,mmm}.py`
- `src/ambo/simulate/truth.py` `response_curve_at`
- `scripts/check_{layer_order,ssot_consistency}.py`
- Phase 2 02-08 (caller-supplied grid); Phase 4 04-07 (P-SA ladder)
