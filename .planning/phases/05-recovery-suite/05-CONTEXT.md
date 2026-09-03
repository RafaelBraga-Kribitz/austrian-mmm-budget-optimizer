# Phase 5: Recovery Suite - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Proof that the raw-PyMC model recovers disclosed simulator truth it was never shown
(SPEC-05), plus the git-ancestry unlock that makes that proof load-bearing for every
Layer R artifact that follows (Charter E-2, GB-501).

Scope is WBS **T-401…T-410** (`docs/EXECUTION_BLUEPRINT/02_WBS.md`, Phase P4 / M3):
metrics engine VR-301…306; full P-SB and P-SC fits; holdout VR-401; OLS+HC1 baseline;
pymc-marketing cross-check; generated `RECOVERY_REPORT.md`; golden bands; SSOT
generator; layer-order extension; M3 close.

Critical path: T-402 (posteriors) enables T-401's *full* evaluation and T-403…T-407;
T-401 the module can land on constructed fixtures first. T-406 needs T-401 + T-403 +
T-404 + T-405. T-408 needs T-401 + T-406. T-409 extends the already-wired checker.
T-410 is the close.

**Not in scope:** Layer R fits or posteriors (A-2, A-5, locked 3A); `priors_real.yaml`
or `PRIOR_ELICITATION.md` (human, M4); VR-501/502/504 sensitivity (Phase 7; VR-503 S-B
prior-swap is a SPEC-05 §5 reference, not a T-410 gate); Power BI; merging the stack;
inventing CI `"Approved"` (D-19 from Phase 1); copying `m0-bootstrap` science or
`uv.lock`; pulling T-801 `report/style.py` (minimal local style in `validate/report.py`).

### Corrections to upstream documents applied during this discussion

1. **ROADMAP Phase 5 still flags INGEST-CONFLICTS WARNING 4 as open.** It is not.
   SPEC-01 §8's grid note, Phase 2's `response_curve_at(params, x_grid)`, and CONTEXT
   D-08 here implement one grid: MD-082's 21 points over 0…1.5× max *observed* weekly
   spend, truth evaluated closed-form at those same points. The 0…2× array in
   `truth.json` is diagnostic only. The stale ROADMAP paragraph is cleaned in 05-10,
   same interpretation-not-spec-edit pattern as 03-09 / 04-08.

2. **03_MODULES §10 lists `validate → common, model, truth.json files` and does not
   name `simulate.truth`.** VR-303 and SPEC-01 §8 require calling `response_curve_at`
   at the MD-082 grid. Duplicating the formula fails `test_curve_formula_has_a_single_home`.
   Interpolating the 2× diagnostic array is forbidden. SIM-003 forbids simulate↔model,
   not validate→simulate.truth. Settled by D-03.

3. **`make fit-synthetic` is still P-SA only (Phase 4 D-20 / T-307).** T-402 extends it
   to P-SA, P-SB, P-SC. SPEC-08 §5's three-scenario listing is the T-402 reading.

4. **`scripts/check_layer_order.py` and `check_ssot_consistency.py` already exist and
   are CI jobs 5 and 4.** T-408/T-409 *extend* them (Phase 1 D-17). They are not
   rewritten, not stubbed, not replaced.

5. **`sensitivity.py` is listed in SPEC-08 §2 and 03_MODULES §5.3.** Those lists are
   authoring-time contracts, not closed sets. VR-501/502/504 are Phase 7. This phase
   does not add an empty `sensitivity.py`.
</domain>

<decisions>
## Implementation Decisions

### Plan granularity

- **D-01:** Ten stacked plans, 1:1 with T-401…T-410 (4B). Waves: 05-01 T-401 (metrics,
  fixture-tested); 05-02 T-402 (P-SB/P-SC fits); 05-03 T-403 holdout; 05-04 T-404 OLS;
  05-05 T-405 cross-check; 05-06 T-406 report; 05-07 T-407 golden; 05-08 T-408 SSOT;
  05-09 T-409 layer-order tests; 05-10 T-410 M3 close.

### T-401 before T-402 in git; compute may overlap

- **D-02:** 05-01 lands `recovery.py` with constructed-posterior unit tests (WBS AC-1)
  so the metrics engine exists before real S-B/S-C parquets. 05-02 commits those
  parquets. A P-SB/P-SC NUTS run may start on this machine during planning — the
  artifacts are committed only in 05-02. Do not block 05-01 on sampler wall time.

### validate → simulate.truth is allowed; validate → simulate.dgp is not

- **D-03:** `ambo.validate.recovery` may import `TruthFile`, `ChannelTruth`,
  `response_curve_at` from `ambo.simulate.truth` and `TrueParams` from
  `ambo.simulate.config` (needed to call the evaluator). It must not import
  `ambo.simulate.dgp`, `spend_patterns`, `platform_bias`, or `ambo.simulate.__main__`.
  SIM-003 / W-2 still forbids simulate↔model. A unit test greps `src/ambo/validate/`
  for those forbidden imports. MODULE_CONTRACTS dependency-directions table is updated
  in 05-01 to name this edge.

### Gate table is data

- **D-04:** `config/recovery_gates.yaml` mirrors SPEC-05 §3 cell-for-cell. Thresholds
  are not literals inside `evaluate_gates`. Widening a gate still requires an ADR
  (VR-310) — changing the YAML without an ADR is a review finding, not a silent knob.

### Layer names

- **D-05:** `compute_recovery(layer: str)` takes BP-D-06 names `P-SA` / `P-SB` / `P-SC`.
  Scenario id mapping: `P-SA→s_a`, `P-SB→s_b`, `P-SC→s_c`. Truth path
  `{data_synthetic}/{scenario_id}/truth.json`. Posterior `load_posterior(layer)`.
  Six channels on Layer P (`other` absent). Gate "6 channels" means channels present,
  not the seven-row taxonomy.

### ROAS draws are model-side only

- **D-06:** Per draw, per channel: scaled spend from the mart + `ScaleFactors`;
  adstock + Hill via the **model** pytensor graphs (`adstock_convolve`,
  `hill_saturation`) compiled once; `m_eur = m_scaled * revenue_mean` (the MD-030
  revenue inverse — same multiply `from_model_scale` applies to a `revenue` column).
  Average ROAS = `Σ_t m_eur / Σ_t x_eur`. Never call simulator `adstock_recursive` /
  `dgp.hill` for this quantity. A property test on a constructed posterior with known
  β, K, s, λ and a known spend series asserts the computed ROAS.

### 90% interval is HDI

- **D-07:** VR-301 "inside 90% HDI" uses `arviz.hdi(..., hdi_prob=0.9)` (highest
  density), not equal-tail 5/95 percentiles.

### VR-303 grid and model curve

- **D-08:** Grid = `np.linspace(0.0, 1.5 * max_observed_weekly_spend, 21)` per channel
  from the fitting mart (observed, not the truth.json 2× diagnostic array).
  Truth = `response_curve_at(TrueParams(lam, K, s, beta), grid)` (D-03).
  Model posterior-mean curve: because MD-020 weights sum to 1, steady-state adstock of
  a constant scaled spend `x / spend_mean` is that scaled spend; contribution_eur =
  `beta * hill_saturation(x_scaled, k, s) * revenue_mean`, mean over draws.
  MAE% = mean_i |μ_post(x_i) − truth(x_i)| / max_i truth(x_i) × 100.
  If `max(truth) == 0` (S-C `display_video`), MAE% is reported as `null` and excluded
  from the median-across-channels statistic; VR-303 is not gated on S-C.

### VR-305 ranking

- **D-09:** Posterior median half-life `log(0.5) / log(λ)` (same identity as
  `elicit.halflife_from_lambda`). Pass iff both `print_regional` and `radio` strictly
  exceed both `search_brand` and `search_generic`. `meta` / `display_video` are
  unconstrained. Required on S-A, S-B, and S-C.

### VR-306 share

- **D-10:** Posterior median of `(Σ_c Σ_t m_c,t) / (Σ_t revenue_observed)` versus
  `TruthFile.media_share_of_revenue`. Pass iff absolute difference ≤ 0.10 (10 pp).

### ValidationError

- **D-11:** `ValidationError(AmboError)` in `errors.py` for this package: unknown
  layer, missing truth/posterior, malformed gate YAML. Fit failures stay `FitError`.

### JSON side-files (no recomputation downstream)

- **D-12:** `RecoveryMetrics` / `GateResults` are frozen pydantic models. Writing
  `reports/recovery/metrics_<layer>.json` and `reports/recovery/gates_<layer>.json`
  is part of `compute_recovery` / `evaluate_gates` (atomic replace, LF, sorted keys).
  T-406 and T-408 read these files; they do not recompute ROAS.

### WARNING 4

- **D-13:** One grid, MD-082, closed-form truth, no interpolation. ROADMAP stale
  "must resolve" blurb removed in 05-10.

### Report style

- **D-14:** Do not pull T-801. `validate/report.py` uses a local matplotlib rc
  (Agg, 12×6, dpi 150) in this phase; a later swap to `report/style.py` is one line.

### Sensitivity out of this phase

- **D-15:** No `sensitivity.py`. VR-503 is not a T-410 success criterion (ROADMAP
  criterion 3 names VR-401 and VR-602). Phase 7 owns VR-501…504.

### Extend, do not replace, the M0 checkers

- **D-16:** T-409 adds throwaway-repo tests for both GB-501 failure modes if the
  existing `tests/unit/test_governance_checks.py` coverage is incomplete; CI job 5
  already runs the script with `fetch-depth: 0`. Do not rewrite the script's
  vacuous-success path.
- **D-17:** T-408 adds `scripts/generate_ssot.py`. The checker gains a real SSOT to
  reconcile; its M0 parser/whitelist contract stays. Artifact mtimes (not wall clock)
  for `updated_at`. Registry of JSON side-files; the generator never computes
  analytics. Keys that do not exist yet (Layer R, optimizer) are omitted (BP-D-08),
  not filled with placeholders.

### fit-synthetic becomes three layers

- **D-18:** In 05-02, `make fit-synthetic` prints expected runtime for **3 fits**,
  then runs `--layer P-SA`, `P-SB`, `P-SC` in that order. Each call may take the
  MD-073 ladder (≤ 35 min each). Re-running P-SA is accepted (deterministic seed);
  do not add a "skip if parquet exists" branch — silent skip would hide a stale
  artifact. Operators who want one layer use the CLI.

### Holdout artifacts

- **D-19:** T-403 wires `variant=holdout` in `fit.py` (first T−13 weeks; scale
  factors computed on that slice only — RK-M2-4). Posterior basename
  `{layer}__holdout` is added to `posterior_io` allowed names so local debug parquet
  can be written; **it is not committed** (BP-D-06). Committed output is
  `reports/model/holdout_<layer>.csv` with MAPE, naive MAPE, and 90% coverage (A-7).
  Naive baseline `revenue_{t-52}` requires ≥ 65 weeks — assert it. Gate (beat naive
  MAPE) on P-SA and P-SB only.

### Standing prohibitions

- **D-20:** No Layer R data or fits. No `priors_real.yaml`. No `PRIOR_ELICITATION.md`.
  No m0 `uv.lock`. No history rewrite. No merging stacked PRs unless asked. No
  invented CI `"Approved"`. No checksum of posterior draws (T-6). No widening VR-3xx
  without ADR. Do not restore ADR-010 (`s=1`). Do not change `priors_synthetic.yaml`
  to "fix" recovery.

### Golden bands are a first generation, not a regen

- **D-21:** T-407's first `tests/golden/recovery_bands.json` is the deliverable.
  AGENTS §2 item 7 (human-approved regen) applies to *later* regenerations after the
  file exists. Schema: per scenario × channel, median ROAS ± 0.15 × posterior SD.
  Sorted keys. Generator header documents the regen path.

### OLS has no new dependency

- **D-22:** `numpy.linalg.lstsq` + HC1 sandwich in numpy/scipy. Textbook fixture to
  1e-8. Whatever signs come out, they ship (VR-601 purpose).

### pymc-marketing 0.19.4

- **D-23:** Locked version is 0.19.4 (`>=0.8`). T-405 records that version in
  `reports/recovery/crosscheck_mapping.md`. Gate is Spearman/Pearson of channel ROAS
  *medians* ≥ 0.8 on S-B. Unmatchable API pieces are listed, not papered over
  (VR-602, RK-M3-2). Imports confined to `validate/crosscheck.py`.

### `make recover` does not sample

- **D-24:** From 05-06, `make recover` loads committed parquets + side-files + holdout
  CSVs, writes the report and plots, exits 0. It must not call `pm.sample` (VR-703).
  Missing P-SB/P-SC parquet is a loud failure naming `make fit-synthetic`.

### Injected I/O for tests

- **D-25:** `compute_recovery` accepts optional `bundle`, `frame`, `truth` so unit
  tests never require DuckDB or a 1000-row parquet. Production path loads them.

### VR-304

- **D-26:** S-C `display_video` only. `P(ROAS < 0.2) ≥ 0.7` (share of draws) AND
  posterior median contribution share ≤ 0.03. Both conjuncts required.
</decisions>

<specifics>
## Specifics

| Item | Value |
|------|--------|
| Effort budget | 2.5 d (>2× ⇒ stop + ADR) |
| Layers | P-SA, P-SB, P-SC. Never R. |
| Channels on Layer P | 6 (taxonomy minus `other`) |
| MD-082 grid | 21 points, 0…1.5× max observed weekly spend |
| Adstock L | `Settings.adstock_length` (8), passed as argument |
| Sampler | unchanged MD-050 + existing MD-073 ladder in `fit.py` |
| pymc-marketing | 0.19.4, `crosscheck.py` only |
| Holdout | last 13 weeks; naive `t-52`; ≥ 65 weeks required |
| SSOT columns | `key\|value\|unit\|tag\|produced_by\|updated_at` |
| Report order | SPEC-05 §8 1…8, machine-checked |
| Closing paragraph | template, ≥ 500 chars, MD-020 + lift-test |
</specifics>

<ignored>
## Explicitly deferred

- VR-501/502/504 and `validate/sensitivity.py` — Phase 7
- VR-503 S-B prior-swap figure — Phase 7 unless T-406 has spare capacity; not gated
- `ambo/report/style.py` (T-801) — Phase 9
- Layer R SSOT keys, optimizer keys — omitted until those producers exist
- `priors_real.yaml` / elicitation rationales — human, M4
- Merging this stack to `main`; enabling GitHub branch protection — human / D-19
- Repo visibility flip to public — human, after RECOVERY_REPORT exists (STATE.md)
- Golden-band *regeneration* after T-407 — human (AGENTS §2)
</ignored>
