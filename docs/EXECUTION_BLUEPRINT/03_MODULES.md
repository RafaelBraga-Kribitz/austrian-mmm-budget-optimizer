# 03 — MODULE CONTRACTS

Contract per module, class, and load-bearing function. Signatures are **contracts,
not implementations** — types and semantics are binding; bodies are the implementer's
job under [07_QUALITY_STANDARDS.md](07_QUALITY_STANDARDS.md). Any function not listed
here must still satisfy its module's standards; if a new *public* function is needed,
add it to this document in the same PR (contract-first rule).

Conventions that apply to **every** module unless overridden:

- **Config:** read only via `ambo.common.config.load_settings()`; no module reads
  YAML/env directly (exceptions: config.py itself; intake mapping rules by design).
- **Logging:** `ambo.common.logging.get_logger(__name__)`; no `print` in `src/`.
- **Errors:** raise typed exceptions (`AmboError` root, subclasses per module:
  `ConfigError`, `DataContractError`, `GateFailure`, `IntakeError`, `LeakDetected`,
  `FitError`); never catch-and-continue silently ([09 §A-7](09_ANTI_PATTERNS.md));
  error messages never contain private-drop content or paths (redaction via the
  logging filter; exceptions from intake carry counts, not values).
- **Determinism:** every stochastic entry point takes/derives an explicit seed;
  library-global RNG state is never used ([09 §A-5](09_ANTI_PATTERNS.md)).
- **Thread safety:** the project is single-process, single-threaded by design; no
  module may spawn threads/processes except PyMC's own chain parallelism. Modules
  must be import-safe (no side effects at import).
- **Metrics/observability:** long-running entry points log start/end + wall time;
  sampling targets print expected runtime up front (EB-050).
- **Testing:** unit tests colocated under `tests/unit/test_<module>.py`; every
  public function has ≥1 direct test; property/round-trip tests where the contract
  states an invariant.
- **Reproducibility:** any artifact writer embeds provenance (inputs' hashes, config
  hash, git commit, seed) — implemented once in `posterior_io`/report writers, reused.

---

## 1. `ambo/common/`

### 1.1 `config.py`
**Purpose.** Typed, validated, single-read configuration (EB-040).
**Public API.**
- `class Settings(BaseSettings)` — fields: `channels: list[str]` (7, taxonomy order),
  `adstock_length: int` (=8), `paths: PathsConfig` (data_synthetic, data_real_anon,
  posteriors, warehouse, exports, reports), `sampler: SamplerConfig`
  (chains=4, tune=1000, draws=1000, target_accept=0.9, seed=42, init string),
  `private_drop: Path | None` (from `AMBO_PRIVATE_DROP`).
  Invariants: `extra='forbid'`; channels exactly SPEC-02 §5.2; lists immutable
  (tuples after validation).
- `load_settings() -> Settings` — cached; idempotent; raises `ConfigError` with the
  failing key path on invalid YAML.
**Failure modes.** Missing YAML → `ConfigError` naming the expected path; unset
`AMBO_PRIVATE_DROP` → `None` (only intake raises, AG-020).
**Extension points.** New settings keys require: schema field + YAML + test, one PR.
**Testing.** Round-trip, forbid-extra, env-var both states.

### 1.2 `logging.py`
**Public API.** `get_logger(name: str) -> logging.Logger`;
`class PrivatePathFilter(logging.Filter)` — redacts the resolved private-drop path
to `<PRIVATE_DROP>` in every record (EB-041).
**Invariants.** Filter installed on every logger the factory returns; format
`%(asctime)s %(levelname)s %(name)s %(message)s`; level from env `AMBO_LOG_LEVEL`
default INFO.
**Testing.** Redaction proven with a fake path; no-op when unset.

### 1.3 `db.py`
**Purpose.** The ONLY data doorway for model/decide/report code (AD-030).
**Public API.**
- `connect(read_only: bool = True) -> duckdb.DuckDBPyConnection` — raises
  `DataContractError("run make transform")` if warehouse missing.
- `read_mmm_input(layer: str) -> pd.DataFrame` — postconditions: gapless weekly
  `week_start` ascending; columns: `week_start, layer, revenue, orders, promo_flag,
  advent_flag, jan_dip_flag, spring_flag, schulbeginn_flag, summer_lull_flag,
  spend_<channel>×7`; no NaN in spends (0-filled); revenue > 0; raises
  `DataContractError` listing violated assertions otherwise.
- `read_platform_reported(layer: str) -> pd.DataFrame` — week × channel rows,
  NULLs allowed for offline channels.
- `read_dim_layer() -> pd.DataFrame`.
**Failure modes.** Unknown layer → `DataContractError` listing valid layers.
**Testing.** Round-trip totals vs simulator CSVs; contract-violation fixtures.

---

## 2. `ambo/simulate/` — Layer P generator (SPEC-01)

**Purpose.** Deterministic disclosed DGP. **Never imports `ambo.model`** (SIM-003).
**Data flow.** ScenarioConfig → spend patterns → baseline/seasonality → media
effects (own adstock/Hill) → revenue + noise → platform bias → CSVs + truth.json.
**Outputs.** `data/synthetic/<scenario>/{media_weekly.csv,outcome_weekly.csv,truth.json}`.
**Performance.** Full 3-scenario build < 30 s. **Security.** None (all disclosed).
**Reproducibility.** SIM-001 byte-identity; single seeded Generator, documented
consumption order (spend by channel order, then noise).

### 2.1 `config.py` (simulate)
- `class ScenarioConfig(BaseModel)` — id, weeks, seed, channels with per-channel
  `TrueParams(lam, K, s, beta)`, spend-pattern params, promo weeks (explicit ISO
  list), burst schedules, collinearity flag, `platform: PlatformBiasParams (phi,
  theta per channel, cpm per channel)`, B0, g, noise_share, AOV rules.
  Invariants: weeks ∈ {156, 104, 78}; S-C ⇔ `display_video.beta == 0`.
- `load_scenario(name: str) -> ScenarioConfig`.

### 2.2 `spend_patterns.py`
- `generate_spend(cfg: ScenarioConfig, rng: np.random.Generator) -> pd.DataFrame`
  (week × channel, int €). Pre: rng fresh for scenario. Post: SIM-031 statistics
  hold; deterministic given (cfg, seed). Failure: schedule referencing weeks outside
  window → `ValueError` at config validation, not runtime.

### 2.3 `dgp.py`
- `season_index(weeks: pd.DatetimeIndex, windows: pd.DataFrame) -> np.ndarray` —
  pure; SPEC-01 §2.1 weights; windows = season_windows seed slice.
- `adstock_recursive(x: np.ndarray, lam: float) -> np.ndarray` — pure; O(T);
  causal; a_0 = 0. Tests: closed form, impulse (SIM-074).
- `hill(a: np.ndarray, K: float, s: float) -> np.ndarray` — pure; Hill(K)=0.5 exact;
  domain a ≥ 0 else `ValueError`.
- `assemble_scenario(cfg) -> SimulationResult` — orchestrator; returns frames +
  `components` (base, season, promo, m_c per channel, eps) for SIM-071 audit.
- `class SimulationResult` — frozen dataclass: media, outcome, components, cfg.
  Invariant: `components` re-sums to revenue within 1e-6 (checked at construction).

### 2.4 `platform_bias.py`
- `platform_report(result: SimulationResult) -> pd.DataFrame` — SIM-060 formulas +
  BP-D-02 impressions/conversions; offline → NULL. Pure given result.

### 2.5 `truth.py`
- `class TruthFile(BaseModel)` — SIM-075 schema: all §4/§6 params + §8 derived.
- `compute_truth(result: SimulationResult) -> TruthFile` — includes analytic
  marginal ROAS (Guide §1.5) and 21-point curves. Determinism: byte-stable JSON
  (sorted keys, fixed float format).
- `write_truth(t: TruthFile, path: Path) -> None` — atomic write.

### 2.6 `__main__.py`
- CLI `python -m ambo.simulate {all|s_a|s_b|s_c} [--outdir]`; exit 0/1; logs
  per-scenario timing. `validate_sim()` gate-runner: prints SIM-070..075 table.

---

## 3. `ambo/intake/` — Layer R pipeline (SPEC-02)

**Purpose.** Two-stage privacy-by-construction intake. **The only package allowed to
read `$AMBO_PRIVATE_DROP`** (EB-041); stage 1 may write only under the drop;
stage 2 may write only `data/real_anon/` + the intake-channel seed.
**Failure philosophy.** Every ambiguity is a hard stop with a count-only message —
never proceed on guessed mappings (AGENTS §2.1).
**Security.** No campaign strings, no factors, no absolute pre-scale values in any
output/log/exception. Test fixtures synthetic only (AG-032).

### 3.1 `standardize.py`
- `run_standardize(drop: Path, mapping_rules: Path) -> StagedData` — reads §2 input
  classes present, maps campaigns → taxonomy via ordered regex rules, aggregates
  daily→ISO weeks (partial edge weeks dropped, AG-050), writes
  `<drop>/staged/*.parquet`. Pre: drop exists, rules parse. Post: staged files
  canonical-schema'd; every source row either mapped or counted in the rejection
  report. Failures: unmapped campaigns → `IntakeError(count)`; repo-path write →
  `AssertionError` (guard).
- `class StagedData` — paths + summary stats (counts, window) only; no values.

### 3.2 `anonymize.py`
- `run_anonymize(staged: StagedData, factors: RescaleFactors) -> None` — applies
  AG-040..044; writes public files + `INTAKE_MANIFEST.yaml` + intake-channel seed.
- `class RescaleFactors` — `k_spend, k_rev (float)`; constructor enforces
  Uniform(0.4, 2.5) bounds + |k_spend−k_rev| ≥ 0.15; `__repr__` REDACTED (never
  prints values); never serialized. Collected via interactive prompt only.
- `scrub_check(df: pd.DataFrame) -> list[Violation]` — regex PII pass (emails,
  URLs, phones); any violation → `LeakDetected` (hard fail, AG-044).
- `class IntakeManifest(BaseModel)` — §5.4 fields; forbidden fields structurally
  absent (no factor fields exist on the model).

### 3.3 `validate.py`
- `run_intake_gates(dir: Path) -> GateReport` — AG-060..066; writes
  `reports/ingestion/intake_validation.md`; exit-code semantics via CLI wrapper.
  Each gate pure given loaded frames; thresholds from a module-level table mirroring
  SPEC-02 §6 (data, not code).

---

## 4. `ambo/model/` — the MMM (SPEC-04)

**Purpose.** One model definition for all layers (MD-002). **Never imports
`ambo.simulate`.** `pymc_marketing` forbidden here (MD-003).
**Data flow.** `db.read_mmm_input` → `transforms.compute_scale_factors` →
`mmm.build_model` → `pm.sample` (fit runner) → `posterior_io.save` →
`diagnostics.run`.
**Performance.** Full fit (MD-050) ≤ ~30 min/scenario on a modern laptop; smoke
< 15 min in CI. **Reproducibility.** Same machine+seed ⇒ 3-decimal summary equality
(VR-701); cross-platform via tolerance bands only (VR-702).

### 4.1 `transforms.py`
- `geometric_adstock_weights(lam: float | TensorVariable, L: int) ->` weights,
  normalized Σ=1 (MD-020).
- `adstock_convolve(x, lam, L)` — causal length-L convolution; pytensor-graph-safe
  AND numpy-callable (dual dispatch or twin functions with equality test). Pre:
  x ≥ 0. Post: output[t] depends only on x[max(0,t−L+1)..t]. Complexity O(T·L).
- `hill_saturation(a, K, s)` — as SPEC-01 math; shares NO code with simulate
  (independent implementation).
- `class ScaleFactors` — frozen: `revenue_mean: float`,
  `spend_means: dict[channel, float]` (nonzero-week means). Invariant: all > 0;
  all-zero channel → `FitError` at construction.
- `compute_scale_factors(df, channels) -> ScaleFactors`
- `to_model_scale(df, sf) -> pd.DataFrame` / `from_model_scale(obj, sf)` —
  exact inverse pair (property-tested to 1e-12); `from_model_scale` also maps
  posterior contribution/ROAS quantities back to level units (the ONLY place
  back-transformation lives — trap T-1).

### 4.2 `priors.py` (schema; file `config/priors_*.yaml`)
- `class ChannelPrior(BaseModel)` — `lam: BetaParams`, `K: GammaParams` (scaled
  units), `s: TruncGammaParams`, `beta: HalfNormalParams`.
- `class PriorConfig(BaseModel)` — `channels: dict[str, ChannelPrior]`,
  `globals: GlobalPriors` (α, τ, γ scale, δs, σ per SPEC-04 §4).
- `load_priors(path: Path) -> PriorConfig`.
  Invariant (synthetic file only, MD-040): all channel entries value-equal —
  enforced by test, not schema.

### 4.3 `mmm.py`
- `build_model(df: pd.DataFrame, channels: list[str], priors: PriorConfig)
  -> pm.Model` — MD-002. Pre: df satisfies db.py contract and is already SCALED.
  Post: free RVs exactly the documented name set (Guide §2.2 table); coords
  `channel`, `week`; no layer/scenario branching (grep-tested). Deterministic
  graph construction. Failure: channel in list absent from df → `FitError`.

### 4.4 `fit.py` (runner, `__main__`-style CLI)
- `run_fit(layer: str, variant: str | None = None) -> FitResult` — orchestrates;
  variants: `flat` (priors_synthetic), `nopromo` (drop promo regressor),
  `loco-<channel>`, `holdout` (first T−13 weeks). Prints expected runtime
  (EB-050). Sampler settings ONLY from Settings (MD-050). Seed fixed 42.
- `class FitResult` — idata handle + paths + diag summary.

### 4.5 `posterior_io.py`
- `save_posterior(idata, sf: ScaleFactors, name: str) -> Path` — netCDF (local,
  gitignored) + thinned parquet (every 4th draw → 1000 rows; columns
  `<var>` or `<var>__<channel>`) with embedded metadata: scale factors, data hash,
  prior file sha256, sampler settings, git commit, seed. Atomic (EB-050).
- `load_posterior(name: str) -> PosteriorBundle` — refuses files lacking metadata.
- `class PosteriorBundle` — frozen: draws df, metadata dict, `sf: ScaleFactors`.
  Naming per BP-D-06 (`P-SA`, `R`, `R__flat`, …).

### 4.6 `diagnostics.py`
- `class DiagGates` — thresholds; constructors `standard()` (MD-071) /
  `layer_r()` (MD-074). Explicit at call site, never auto-selected.
- `run_diagnostics(idata, gates: DiagGates) -> DiagResult` — pure computation.
- `write_diag_report(res: DiagResult, layer: str) -> Path` —
  `reports/model/diag_<layer>.md` + PPC plot + energy plot when divergences > 0.
- `class DiagResult` — per-gate pass/fail + stats; `all_green: bool`.

### 4.7 `elicit.py`
- `beta_params_from_halflife_range(lo_wk: float, hi_wk: float) -> BetaParams` —
  mode at λ(mid), ≥ ~90% mass within [λ(hi), λ(lo)] (note inversion: longer
  half-life ⇒ larger λ). Pure, deterministic, brentq-solved (Guide §3).
- `gamma_params_from_k_range(lo: float, hi: float) -> GammaParams` (scaled units).
- `sigma_beta_from_max_effect_share(share: float) -> float`.
  All: documented worked examples (doctests) referenced by PRIOR_ELICITATION.md;
  MD-061's lint uses these to verify doc↔YAML consistency.

---

## 5. `ambo/validate/` — recovery, sensitivity, baselines (SPEC-05)

**Purpose.** Everything that argues the model can be trusted. Reads truth.json +
PosteriorBundles + marts; never fits (fits go through `model/fit.py`).
**Reproducibility.** All reports regenerate from committed thinned posteriors
(VR-703) — module-level test deletes netCDF and regenerates.

### 5.1 `recovery.py`
- `compute_recovery(scenario: str) -> RecoveryMetrics` — loads truth + bundle;
  computes VR-301..306 statistics. ROAS draws via model-side back-transform only.
- `evaluate_gates(m: RecoveryMetrics) -> GateResults` — against the VR §3 table
  (module-level data constant, cell-per-cell equal to spec).
- `class RecoveryMetrics` / `class GateResults` — frozen; serialize to JSON
  side-files consumed by report + SSOT (no recomputation downstream).

### 5.2 `holdout.py`
- `run_holdout(layer: str) -> HoldoutResult` — invokes fit variant `holdout`,
  conditional forecast last 13 weeks, MAPE + coverage vs seasonal-naive. Gate
  (beat naive) applies to S-A/S-B only; Layer R reported either way (VR-401).

### 5.3 `sensitivity.py`
- `run_prior_influence(layer)` (VR-501/503), `run_loco(layer)` (VR-502),
  `run_no_promo(layer)` (VR-504) — thin orchestrations over fit variants +
  comparison frames + forest-plot data. Each emits a JSON side-file + PNG.

### 5.4 `baseline_ols.py`
- `fit_ols_baseline(df, channels, prior_mode_lambdas) -> OLSResult` — numpy/scipy
  OLS + HC1 sandwich (no new deps, EB-030); adstock at prior-mode λ, no saturation.
  Textbook-verified in tests.

### 5.5 `crosscheck.py`
- `run_crosscheck(layer) -> CrosscheckResult` — the ONLY module importing
  `pymc_marketing` (MD-003, guard-tested); emits correlation stat + mapping doc.

### 5.6 `report.py`
- `generate_recovery_report() -> Path` — VR §8 mandatory order; verdict/closing
  are templates with slots (no free text); embeds PNGs; appends DC-401 addendum
  when present. Doc-structure test asserts section order.

---

## 6. `ambo/decide/` — optimizer & attribution gap (SPEC-06)

**Purpose.** Q3/Q4 from committed posteriors; **never refits** (module has no
import path to `pm.sample` — reviewed). Deterministic (DC-703).

### 6.1 `optimizer.py`
- `expected_contribution(x: np.ndarray, draws: pd.DataFrame, channels) ->
  np.ndarray` — steady-state β·Hill(x) per draw (DC-201 simplification; caption
  duty on artifacts). Vectorized over draws; O(D·C).
- `optimize_allocation(bundle: PosteriorBundle, B: float, constraints:
  AllocationConstraints, seed: int) -> AllocationResult` — SAA over first 500
  draws (deterministic subset), SLSQP, 20 seeded Dirichlet restarts, best-of;
  outcome uncertainty from all 1000 draws. Post: Σx=B ±1e-6; bounds exact; fixed
  channels (search_brand, other) at historical mean. Restart spread > 1% ⇒
  `converged_clean=False` flag (never silent).
- `class AllocationConstraints` — B, per-channel bounds (1.3×max observed), fixed
  set; built by a factory from mart + settings (single construction path).
- `class AllocationResult` — frozen: x*, objective draws, binding flags,
  convergence report. 
- `true_params_contribution(x, truth: TruthFile)` — truth-side objective for
  DC-401 (SPEC-01 parameterization, BP-D-16); lives here but reads truth.json
  (not simulate code — independence preserved).

### 6.2 `scenarios.py`
- `run_budget_scenarios(bundle) -> pd.DataFrame` — DC-205 (B multipliers 0.8/1.0/
  1.2) → allocation_scenarios export frame.
- `gain_metric(bundle, result) -> GainMetric` — DC-301 exact formula + HDI +
  annualization; SSOT feed.
- `marginal_roas_ladder(bundle) -> pd.DataFrame` — DC-601 ±a€500 ladder,
  reallocatable channels only.

### 6.3 `attribution_gap.py`
- `compute_gap(layer: str) -> pd.DataFrame` — DC-501 per-channel stats
  (platform ROAS, MMM ROAS+HDI, overcredit ratio, P(platform>MMM)).
- `check_phi_ordering(gap_sb: pd.DataFrame) -> bool` — DC-502 gate.
- `render_dumbbell(df) -> Path` — chart via report.style.

---

## 7. `ambo/report/` — presentation layer (SPEC-07)

**Purpose.** Everything a reader sees; reads exports + SSOT side-files + committed
posteriors; no computation that changes numbers (RB-301 enforces for RB-201).

- `style.py` — `apply() -> None` (rcParams: Agg, 12×6, dpi 150);
  `CHANNEL_COLORS: dict[str, str]` (Okabe-Ito, total over taxonomy, fixed).
- `format.py` — `aeur(x) -> str` ("a€1.2 M"), `roas(x) -> str` ("3.4×"),
  `pct(x) -> str` (1 decimal). Pure; tested on edge cases.
- `captions.py` — constants: `AEUR_CAPTION` (Charter E-5 wording),
  `COUNTERFACTUAL_CAPTION` (DC-302), `ANON_PARAGRAPH` (AG-070). Single-occurrence
  grep-test (GB-102).
- `charts.py` — `render_all(out: Path) -> list[Path]` — RB-201..205; each chart
  function documents its data source file; chart metadata helper stamps title/
  source-note/epistemic-tag (reviewable programmatically).

## 8. `dbt/` — warehouse (SPEC-03)

**Models and tests exactly as SPEC-03 §2–§4 + BP-D-03/05/19** (see
[05 §8](05_IMPLEMENTATION_GUIDES.md) for SQL-level guidance).
`fct_mmm_input` column contract (binding for db.py): `week_start DATE`,
`layer TEXT`, `revenue DOUBLE`, `orders BIGINT`, `promo_flag INT`,
5 calendar flags INT, `spend_<channel> DOUBLE ×7` (0-filled).
**Config.** vars: `layer_r_present` (bool), `channel_taxonomy` (list, must equal
settings.yaml — cross-checked by a pytest).
**Failure modes.** Duplicate grain keys FAIL (never dedup); missing seed FAIL.

## 9. `scripts/` — governance & IO executables

| Script | Contract |
|---|---|
| `generate_season_windows.py` | idempotent; writes seed 2019–2027; exit 0 |
| `leak_scan.py` | modes: default (repo), `--staged`; blocklist auto-detected via env; exit 0 clean / 1 findings / 2 usage; findings never echo secret text |
| `generate_ssot.py` | collects registered side-files → NUMERIC_SSOT.md; deterministic ordering; never computes analytics |
| `check_ssot_consistency.py` | doc literals vs SSOT within documented rounding; whitelist with justifications; exit 0/1 |
| `check_layer_order.py` | GB-501/502 git-ancestry assertions (Guide §5); trivially green pre-Layer-R; exit 0/1 |
| `generate_golden_metrics.py` | writes `tests/golden/recovery_bands.json` (±0.15·SD bands); stable ordering |
| `export_marts.py` | registry-driven export writer; per-file schema contracts (AD-050) |

**All scripts:** argparse CLI, `--help` accurate, importable main() for tests,
no side effects at import.

## 10. Cross-module dependency rules (enforced)

```
simulate  →  (nothing in ambo except common)
intake    →  common
model     →  common
validate  →  common, model (fit/posterior_io/transforms), truth.json files
decide    →  common, model.posterior_io/transforms (read-only)
report    →  common, exports/SSOT side-files, model.posterior_io (read-only)
common    →  (nothing in ambo)
FORBIDDEN: simulate↔model (any direction, guard test T-010);
           pymc_marketing outside validate.crosscheck;
           requests anywhere; sample() outside model.fit.
```
