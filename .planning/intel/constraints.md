# Constraints (synthesized intel)

Source tier: SPEC (20 documents). With no ADRs present, this is the top-authority
tier — SPEC beats PRD (PROJECT_CHARTER.md) and DOC (00_MASTER_PLAN, 01_PHASES,
13_TRACEABILITY_MATRIX) on any contradiction.

Two SPEC families:
- `docs/SPEC-01..09` — the system specs (requirement IDs SIM / AG / AD / MD / VR / DC / RB / EB / GB)
- `docs/EXECUTION_BLUEPRINT/02..12` — implementation-level contracts (task cards, module contracts, import edges, thresholds, gate catalog, DoR/DoD, risk controls)

Overlap between the two families is deliberate restatement, not conflict. Genuine
contradictions are recorded in `.planning/INGEST-CONFLICTS.md`.

---

## SIM-001..004 — Simulator principles and output contract
- source: docs/SPEC-01_ground_truth_simulator.md §1
- type: schema
- content: Fully deterministic given (scenario config, seed); two runs produce byte-identical CSVs. All parameters live in `config/scenarios/<scenario>.yaml`, which is authoritative if it ever diverges from the §4 tables. Simulator and model share NO code (import-tested). Outputs per scenario under `data/synthetic/<scenario>/`: `media_weekly.csv` (`week_start` ISO Monday, `channel`, `spend_eur`, `impressions`, `platform_conversions`, `platform_revenue_eur`), `outcome_weekly.csv` (`week_start`, `revenue_eur`, `orders`, `promo_flag`), `truth.json`. All three are committed.

## SPEC-01 §2 — Data-generating process (implement exactly)
- source: docs/SPEC-01_ground_truth_simulator.md §2
- type: protocol
- content: `base_t = B0 x (1+g)^t x season_t x promo_mult_t` with B0 = 60,000 € weekly base, g = 0.001. `season_t` = 1 + 0.55·advent − 0.20·jan_dip + 0.25·schulbeginn + 0.15·spring − 0.10·summer_lull, windows from the real Austrian calendar (holidays package plus fixed ISO-week rules, unit-tested). 10 pre-scheduled promo weeks/year, `promo_mult = 1.15` when flagged. Geometric adstock `a_ct = x_ct + λ_c·a_c,t−1` with `a_c0 = 0`. Hill on ADSTOCKED spend: `h = a^s / (a^s + K^s)`. Contribution `m_ct = β_c·h_ct`. `revenue_t = base_t + Σ_c m_ct + ε_t`, `ε ~ Normal(0, σ)` with σ = 0.04 × mean(base), clipped at >= 0. `orders_t = round(revenue_t / AOV_t)`, `AOV_t = 95 € + 10 € × advent(t)` (descriptive only).

## SPEC-01 §3 — Per-channel spend patterns
- source: docs/SPEC-01_ground_truth_simulator.md §3
- type: protocol
- content: Six channels, spends drawn once per scenario seed in whole €. `search_brand` always-on Normal(700, 60) floor 400. `search_generic` always-on Normal(2500, 200) × (1 + 0.5·advent + 0.2·spring). `meta` always-on pulsed Normal(2000, 300), every 6th week ×1.8. `display_video` always-on Normal(1200, 150). `print_regional` flighted, 0 in ~70% of weeks, 2-week bursts at Normal(5000, 500), 8 bursts/year, 3 fixed in Advent/Schulbeginn. `radio` flighted, 0 in ~75% of weeks, 3-week bursts at Normal(3500, 300), 5 bursts/year, 2 fixed in Advent. SIM-030: in S-B and S-C seasonal spend multipliers are stronger (advent 0.5→0.9 for search_generic/meta; all print/radio bursts anchored to demand peaks) creating deliberate spend↔season collinearity. SIM-031: annual totals within ±10% of design means × weeks; flighting zero-week share within ±10 pp of design.

## SPEC-01 §4 — True media parameters (the recovery target)
- source: docs/SPEC-01_ground_truth_simulator.md §4
- type: schema
- content: Per channel (λ decay, derived half-life wk, K € half-sat adstock, s shape, β €/wk max): search_brand 0.10 / 0.30 / 800 / 1.2 / 6,000; search_generic 0.20 / 0.43 / 3,000 / 1.0 / 15,000; meta 0.35 / 0.66 / 2,500 / 0.9 / 12,000; display_video 0.50 / 1.00 / 2,000 / 1.1 / 6,000; print_regional 0.60 / 1.36 / 4,000 / 1.3 / 8,000; radio 0.55 / 1.16 / 3,500 / 1.2 / 5,000. In scenario S-C `display_video` β = 0 (the zero-effect channel; spend pattern unchanged, everything else identical to S-B).

## SPEC-01 §5 — Scenario definitions
- source: docs/SPEC-01_ground_truth_simulator.md §5
- type: schema
- content: S-A — 156 weeks, collinearity OFF, no zero-effect channel, seed 101, clean identification (model's best case). S-B — 104 weeks, collinearity ON, no zero-effect channel, seed 202, realistic (spend follows demand calendar). S-C — 78 weeks, collinearity ON, zero-effect channel `display_video`, seed 303, hostile (short plus collinear plus a channel that does nothing).

## SIM-060/061 — Simulated platform reporting (known over-credit)
- source: docs/SPEC-01_ground_truth_simulator.md §6
- type: protocol
- content: `platform_revenue_ct = m_ct × φ_c + θ_c × base_t × share_c` where φ is own-effect inflation and θ is demand-claiming leak: search_brand φ=1.1 θ=0.05; search_generic φ=1.3 θ=0.01; meta φ=1.5 θ=0.01; display_video φ=2.0 θ=0.005; print/radio NULL (offline, no platform reporting). `share_c` is the channel's share of total spend that week. Parameters recorded in truth.json. This makes "platform ROAS vs true ROAS" a KNOWN quantity in Layer P; the attribution-gap module must recover the direction and rough magnitude of the φ distortions.

## SIM-070..075 — Simulator gates
- source: docs/SPEC-01_ground_truth_simulator.md §7
- type: nfr
- content: SIM-070 determinism, two runs byte-identical. SIM-071 decomposition audit, base + Σ contributions + noise = revenue re-summed from internal components within tolerance 1e-6. SIM-072 plausibility, no negative revenue pre-clip, media share of total revenue annually in [15%, 45%], noise share of variance in [2%, 10%]. SIM-073 seasonality, the max revenue week of each simulated year falls in the Advent window. SIM-074 adstock closed form, for constant spend x, `a_t → x/(1−λ)`; `Hill(K) = 0.5` exactly. SIM-075 truth.json completeness, every §4/§6 parameter plus §8 derived quantities present, schema-validated by a committed pydantic model. Failure protocol: an implementation bug until proven otherwise — never tune the §4 parameter table.

## SPEC-01 §8 — truth.json derived quantities
- source: docs/SPEC-01_ground_truth_simulator.md §8
- type: schema
- content: Per channel — true total contribution (a€ and share), true average ROAS = Σm_c/Σx_c over the full window, true marginal ROAS at mean historical weekly spend (analytic derivative of β·Hill at mean adstock), response-curve sample at 21 spend grid points from 0 to 2× max weekly spend at steady-state adstock, and platform ROAS from §6. Plus scenario metadata (seed, weeks, flags).

## AG-001/002 — Legal and ethical permission gate
- source: docs/SPEC-02_agency_data_pipeline.md §1
- type: protocol
- content: Before any private file is processed, written permission from the data owner covering "publication of anonymized, rescaled aggregates for portfolio purposes" must exist, stored PRIVATELY and never in the repo. The repo gets `docs/DATA_PERMISSION.md` stating that permission exists, from whom in role terms only, the date, and the scope — no names. If permission cannot be confirmed by end of M4, the Charter §7 degradation path is taken by ADR. No gray-zone processing "while we wait".

## AG-020/030..032 — Private drop and two-stage pipeline architecture
- source: docs/SPEC-02_agency_data_pipeline.md §2-§3
- type: protocol
- content: The private drop lives OUTSIDE the repo, referenced only via env var `AMBO_PRIVATE_DROP`; code fails fast with a clear message if unset when intake targets run. Stage 1 `python -m ambo.intake.standardize` maps the drop to the canonical schema and writes still-private intermediates to `$AMBO_PRIVATE_DROP/staged/`. Stage 2 `python -m ambo.intake.anonymize` writes public outputs to `data/real_anon/` (committed). Only stage-2 outputs may ever enter the repo. Public files: `media_weekly.csv`, `outcome_weekly.csv`, `promo_calendar.csv`, `INTAKE_MANIFEST.yaml`. Test fixtures are synthetic lookalikes generated by a labeled fixture script, never excerpts of the private drop.

## AG-040..045 — Anonymization recipe (exact)
- source: docs/SPEC-02_agency_data_pipeline.md §4
- type: protocol
- content: Identity — client becomes "Client A, an Austrian <sector> advertiser"; no brand, product, city, or URL strings anywhere; campaign names dropped after channel mapping. Dual-factor rescaling — the human draws two secret factors once, `k_spend ~ Uniform(0.4, 2.5)` and `k_rev ~ Uniform(0.4, 2.5)` independently, redrawn if |k_spend − k_rev| < 0.15 so ROAS is not approximately preserved; all spend × k_spend, all revenue/conversion-value × k_rev, rounded to whole a€; factors recorded only in the human's private notes. Counts (impressions, clicks, platform conversions) × k_spend, rounded. Dates kept (seasonality is analytically essential). PII scrub checklist hard-fails stage 2 on any person name, email, phone, search-term/keyword string, URL, geo finer than Bundesland, or free-text field. Leak scan `scripts/leak_scan.py` runs in CI over the repo plus staged changes; local pre-commit runs the full scan, CI runs the pattern subset. Preserved and publishable: all ratios among spends, all ratios among revenues, response-curve shapes, adstock timing, allocation shares, relative ROAS ranking, and the platform-vs-MMM gap ratio per channel. Masked: absolute a€ and absolute ROAS.

## AG-050 and SPEC-02 §5 — Canonical public schema
- source: docs/SPEC-02_agency_data_pipeline.md §5
- type: schema
- content: Daily inputs aggregate to ISO weeks (Mon-Sun, Europe/Vienna); partial edge weeks are DROPPED, not padded; spend/revenue/counts summed. Fixed channel taxonomy — `search_brand`, `search_generic`, `meta`, `display_video`, `print_regional`, `radio`, `other`; every campaign maps to exactly one; `other` must stay < 10% of total spend or the taxonomy is revisited via ADR; absent channels simply do not appear (the model is channel-list-driven). Exact public columns, nothing else permitted: `media_weekly.csv` = `week_start, channel, spend_aeur, impressions, clicks, platform_conversions, platform_conv_value_aeur` (NULLs allowed for offline); `outcome_weekly.csv` = `week_start, revenue_aeur, orders`; `promo_calendar.csv` = `week_start, promo_flag (0/1), promo_type ('price'|'content'|'unknown')` tagged CALIBRATED. `INTAKE_MANIFEST.yaml` records window covered, channels present, weeks count, mapping rule summaries, aggregation decisions, known data issues, permission doc reference, and anonymization recipe version — and never records factors, client identity, or absolute totals.

## AG-060..066 — Intake validation gates
- source: docs/SPEC-02_agency_data_pipeline.md §6
- type: nfr
- content: AG-060 continuity — gapless ISO weeks within the covered window per file; window length >= 52 weeks (else Layer R is descriptive-only, ADR plus Charter §7 consult). AG-061 consistency — every media week exists in outcome weeks and vice versa. AG-062 shares — `other` < 10% of spend; no single week > 15% of total-window spend; zero-spend weeks allowed only for flighted channels; `search_*` > 0 in >= 95% of weeks. AG-063 ratio sanity — weekly revenue/spend ratio in [1.5, 50] for all weeks; platform CTR in [0.1%, 15%] where present. AG-064 seasonality visibility — if the window includes a December, Dec revenue mean must exceed the annual weekly mean. AG-065 PII scrub automated checks pass and leak scan clean. AG-066 manifest complete and schema-validated. Every failure here is a STOP-and-ask; relaxations only via the specific ADRs the spec names.

## AG-070 — Published pipeline disclosure
- source: docs/SPEC-02_agency_data_pipeline.md §7
- type: protocol
- content: This spec file, the manifest, `docs/DATA_PERMISSION.md`, and a fixed README paragraph are published. The paragraph wording lives in `ambo/report/captions.py` as the single caption source.

## AD-001/002 — Warehouse stack and universal keys
- source: docs/SPEC-03_data_model.md §1
- type: schema
- content: DuckDB file `data/warehouse/ambo.duckdb` (gitignored); dbt plus `dbt-duckdb`, project at `dbt/`. Layers raw (external views over committed CSVs) → staging (views) → marts (tables). Units in suffixes `_eur` (Layer P) and `_aeur` (Layer R); the suffix difference is intentional and enforced — a dbt test fails if a mart mixes them. Universal keys: `week_start` (DATE, ISO Monday) plus `layer` ('P-SA'|'P-SB'|'P-SC'|'R') plus `channel` where applicable.

## AD-020 — season_windows.csv is the single calendar source
- source: docs/SPEC-03_data_model.md §2
- type: schema
- content: `dbt/seeds/season_windows.csv` is the single source of Austrian-calendar window definitions (`advent_flag`, `schulbeginn_flag`, `jan_dip_flag`, `spring_flag`, `summer_lull_flag`); the simulator reads it too. This is the explicit exception to the no-shared-code rule — shared CONFIG is allowed, shared TRANSFORM code is not. Staging models: `stg_media_weekly` (week × layer × channel, union of three scenario CSVs plus real_anon, dedup forbidden — duplicate keys FAIL and are never silently resolved), `stg_outcome_weekly`, `stg_promo`, `stg_calendar_weekly`.

## AD-030 — `fct_mmm_input` is THE model input contract
- source: docs/SPEC-03_data_model.md §3
- type: api-contract
- content: `ambo/model/` reads only the `fct_mmm_input` mart via `ambo/common/db.py`, never CSVs. Marts: `fct_mmm_input` (week × layer: `week_start, layer, revenue, orders, promo_flag`, calendar flags, one pivoted spend column per channel, NULL→0 for absent channels); `dim_layer` (layer: `layer, weeks, channels_present, monetary_unit ('EUR'|'aEUR'), source_tag ('GROUND-TRUTH'|'REAL-ANON')`); `fct_platform_reported` (week × layer × channel, feeds the attribution gap).

## AD-040..044 — dbt tests
- source: docs/SPEC-03_data_model.md §4
- type: nfr
- content: AD-040 unique plus not_null on all grain keys, gapless week spine per layer. AD-041 ranges — spend >= 0, revenue > 0, promo_flag in (0,1). AD-042 reconciliation — Layer P-SA total revenue in `fct_mmm_input` equals the simulator CSV sum within 1e-6. AD-043 unit-suffix segregation test. AD-044 Layer R channel presence matches `INTAKE_MANIFEST.yaml`, via a singular test.

## AD-050 — BI export contract
- source: docs/SPEC-03_data_model.md §5
- type: schema
- content: `make export` writes six files to `exports/`, and Power BI reads only these: `mmm_input_weekly.csv`, `contributions_weekly.csv`, `roas_summary.csv`, `response_curves.csv`, `allocation_scenarios.csv`, `attribution_gap.csv`. Export schemas are contract-tested on fixtures.

## MD-001..003 — MMM design commitments
- source: docs/SPEC-04_mmm_model.md §1
- type: api-contract
- content: Additive in revenue LEVEL, not log. Model builder signature `build_model(df: fct_mmm_input slice, channels: list[str], priors: PriorConfig) -> pm.Model` with no scenario-specific branches inside — the channel list drives everything. `pymc-marketing` appears ONLY in `src/ambo/validate/crosscheck.py`, never in the primary model path. One model definition serves all layers and scenarios; only data and prior YAML differ.

## SPEC-04 §2 — Model math (implement exactly)
- source: docs/SPEC-04_mmm_model.md §2
- type: protocol
- content: On SCALED variables — `μ_t = α + τ·t/T + Σ_{j=1..4}[γ_sj sin(2πjt/52.18) + γ_cj cos(2πjt/52.18)] + δ_promo·promo_t + δ_advent·advent_t + δ_jan·jan_dip_t + Σ_c β_c·Hill(adstock(x_c; λ_c); K_c, s_c)`, with `y_t ~ Normal(μ_t, σ)`. Yearly Fourier order 4; Austrian calendar dummies sit ON TOP of the Fourier block.

## MD-020..022 — Transforms
- source: docs/SPEC-04_mmm_model.md §2
- type: protocol
- content: Adstock is geometric, implemented as a fixed-length convolution with normalized weights `w_i = λ^i / Σ_{i=0..L−1} λ^i`, L = 8 weeks, L in config not code. Normalized weights (unlike SPEC-01's raw recursion) keep β interpretable as saturated contribution — the simulator/model parameterization mismatch is deliberate; MD-070 checks correlation of transform outputs, not equality. Hill exactly as SPEC-01 §2.2. Both transforms live in `transforms.py` as vectorized pytensor ops, unit-tested against numpy references. Calendar dummies use the same `season_windows.csv` seed.

## MD-030 — Scaling
- source: docs/SPEC-04_mmm_model.md §3
- type: protocol
- content: `y_scaled = revenue / mean(revenue)`; per-channel `x_scaled = spend / mean(nonzero spend of that channel)`. Scale factors are stored alongside the posterior and applied inversely by ALL reporting code through one tested pair `to_model_scale` / `from_model_scale`. K priors are specified in SCALED spend units in the YAML; the elicitation doc talks €, and the YAML writer converts and records both.

## MD-040/041 and SPEC-04 §4 — Prior structure and layer split
- source: docs/SPEC-04_mmm_model.md §4
- type: schema
- content: Per channel `lambda_c ~ Beta(a_c, b_c)`, `K_c ~ Gamma(shape, rate)` in scaled units, `s_c ~ Gamma(3, 2)` truncated to [0.3, 3.0], `beta_c ~ HalfNormal(σβ_c)`. Globals `α ~ Normal(1.0, 0.3)`, `τ ~ Normal(0, 0.1)`, Fourier `γ ~ Normal(0, 0.15)`, `δ_promo ~ Normal(0.1, 0.05)`, `δ_advent ~ Normal(0.3, 0.15)`, `δ_jan ~ Normal(−0.1, 0.1)`, `σ ~ HalfNormal(0.1)`. Layer P priors (`config/priors_synthetic.yaml`) are WEAKLY informative and channel-agnostic — same Beta(2,4) on all λ, same HalfNormal(0.15) on all β, K ~ Gamma(2, 1.3) around 1.5× mean spend — so recovery comes from data plus structure, not priors that encode the truth table; a test asserts no channel-differentiated values. Layer R priors (`config/priors_real.yaml`) are elicited per channel and frozen at M4.

## MD-050/051 — Sampling settings (fixed)
- source: docs/SPEC-04_mmm_model.md §5
- type: nfr
- content: NUTS via `pm.sample` with 4 chains, tune=1000, draws=1000, `target_accept=0.9`, `random_seed=42`, `init='jitter+adapt_diag'`. Full budget for all reported fits. The CI smoke-fit profile (chains=1, tune=200, draws=200, S-A first 60 weeks) exists only in `tests/` and is never reported. Posterior saved via ArviZ to netCDF locally (gitignored) AND as a thinned parquet (every 4th draw, 1000 rows × parameters) committed under `data/posteriors/<layer>.parquet` for report regeneration without refitting.

## MD-060..062 — Prior elicitation deliverable
- source: docs/SPEC-04_mmm_model.md §6
- type: protocol
- content: `docs/PRIOR_ELICITATION.md` has one section per Layer R channel with exactly five fields — half-life guess (weeks, a range) converted to Beta(a,b) for λ with mode at the implied λ and ~90% mass inside the range; half-saturation spend guess (pre-masking € units FORBIDDEN, the human reasons relatively) converted to Gamma for K in scaled units; plausible max weekly effect converted to σβ; rationale as free text >= 100 characters, first person, grounded in agency practice; and source (`experience` | `literature` | `benchmark` with citation if not experience). MD-061 doc-lint parses the doc — every channel present, every rationale >= 100 chars and not boilerplate, YAML values match the stated ranges via the conversion helper. MD-062 the doc explicitly states it was frozen before fitting, with the freeze commit hash.

## MD-070..074 — Diagnostics gates
- source: docs/SPEC-04_mmm_model.md §7
- type: nfr
- content: MD-070 transform sanity (pre-fit, once) — model transforms vs simulator transforms on S-A spend series correlate > 0.95 per channel. MD-071 R-hat < 1.01 all parameters, ESS_bulk > 400 and ESS_tail > 400, divergences = 0, BFMI > 0.3 all chains. MD-072 posterior predictive check — PPC plot committed, observed y within the 90% PPC band for >= 85% of weeks. MD-073 on MD-071 failure apply the reparameterization ladder IN ORDER, one rung per attempt, ADR if leaving rung 1: (1) raise target_accept to 0.95; (2) non-centered Fourier block; (3) tighten s_c prior to Gamma(4,3) truncated [0.5, 2.5]; (4) fix s_c = 1 — rung 4 changes the model class and requires rerunning Layer P recovery. MD-074 Layer R relaxations (short data, expected) — ESS threshold 300, divergences <= 5 tolerated IF the energy plot is committed and pair-plots show no funnel with a human review note; wide HDIs are NOT a failure, they are content. Diagnostics write `reports/model/diag_<layer>.md`.

## MD-080..083 — Model outputs
- source: docs/SPEC-04_mmm_model.md §8
- type: schema
- content: MD-080 decomposition — posterior mean plus HDI weekly contributions per channel plus base plus seasonality plus promo into `contributions_weekly` (waterfall-ready; additivity test asserts components sum to fitted μ within tolerance). MD-081 ROAS table — total-window average ROAS per channel from draws of Σm_c/Σx_c, reporting mean, 5%, 50%, 95%, and P(ROAS < 1). MD-082 response curves — contribution at 21 grid points from 0 to 1.5× max observed weekly spend (NOT 2×; the extrapolation guard starts here) per channel, mean plus 90% HDI. MD-083 marginal ROAS at current mean spend per channel (the "next €1000" table).

## VR-301..306 and VR-310 — Recovery gates
- source: docs/SPEC-05_validation_recovery.md §3
- type: nfr
- content: Per scenario, all must pass at M3. VR-301 ROAS coverage (true average ROAS inside the 90% HDI): S-A >= 5 of 6 channels, S-B >= 4 of 6, S-C >= 4 of 6 including the zero channel. VR-302 ROAS ranking, Spearman(posterior-median ROAS, true ROAS): S-A >= 0.83, S-B >= 0.7, S-C not gated. VR-303 response-curve shape, mean absolute error between posterior-mean and true curve over the observed-spend grid as % of true curve max: S-A <= 15% per channel and <= 10% median, S-B <= 25% / <= 15%, S-C reported not gated. VR-304 false-positive control (S-C only, `display_video`): posterior P(average ROAS < 0.2) >= 0.7 AND median contribution share <= 3%. VR-305 half-life direction: posterior median half-lives rank print/radio above search channels — required on all three. VR-306 contribution decomposition: total media share of revenue within ±10 pp of truth — required on all three. VR-310: gates are tuned to be passable by a correct implementation and failed by the classic bugs; debug order on failure is transforms (MD-070) → scaling round-trip → data joins → sampler health; widening any gate requires an ADR that names the suspected structural cause. Comparisons are on OBSERVABLE quantities (ROAS, curves, shares), never on raw K/s parameters.

## VR-401 — Holdout
- source: docs/SPEC-05_validation_recovery.md §4
- type: nfr
- content: Refit on the first T−13 weeks and predict the last 13 with actual spend as input (conditional forecast); report MAPE plus 90%-interval coverage against a seasonal-naive baseline (`revenue_{t−52}`). The model must beat naive MAPE on S-A and S-B; on Layer R the result is reported either way with a mandatory n=13 caveat.

## VR-501..504 — Sensitivity suite
- source: docs/SPEC-05_validation_recovery.md §5
- type: protocol
- content: VR-501 prior-influence — refit Layer R with `priors_synthetic.yaml` (weak) vs frozen `priors_real.yaml` (elicited); artifact is a forest plot of ROAS posteriors under both per channel plus one paragraph on where elicitation moved or narrowed estimates, written to `reports/recovery/vr_prior_influence.png` — THE portfolio artifact of this project. VR-502 leave-one-channel-out — drop the largest-spend channel, refit, report how its contribution is re-attributed. VR-503 (Layer P S-B) same prior swap, contrasted with Layer R in one combined figure. VR-504 no-promo sensitivity — Layer R refit without the promo regressor, report ROAS shifts, feeds LIMITATIONS.

## VR-601/602 — Baseline and cross-check
- source: docs/SPEC-05_validation_recovery.md §6
- type: nfr
- content: VR-601 OLS baseline — revenue on the same regressors with adstock fixed at prior-mode λ and no saturation, HC1 errors, reported side by side with Bayesian results on S-B; whatever happens is reported. VR-602 pymc-marketing cross-check on S-B and Layer R — fit their `MMM` class with matched transforms/priors as closely as the API allows; gate: channel ROAS posterior medians correlate >= 0.8 with the raw-PyMC model on S-B; differences discussed in one paragraph; any API impossibility must document what was matched.

## VR-701..703 — MCMC reproducibility doctrine
- source: docs/SPEC-05_validation_recovery.md §7
- type: nfr
- content: VR-701 same machine plus same seed — ArviZ summaries must match to 3 decimals via a regression test using cached fits. VR-702 cross-platform (CI vs local) — golden tests compare posterior medians of ROAS per channel within tolerance bands of ±0.15 × posterior SD, stored in `tests/golden/recovery_bands.json`, generated by `scripts/generate_golden_metrics.py`, regeneration only with PR justification; NEVER checksum draws. VR-703 reports regenerate from the committed thinned posteriors without refitting — `make report` must not require sampling.

## SPEC-05 §8 — RECOVERY_REPORT.md structure (order mandatory)
- source: docs/SPEC-05_validation_recovery.md §8
- type: schema
- content: 1 one-paragraph verdict from a slotted template with no free-form spin; 2 gate table with pass/fail per scenario; 3 recovery plots (true vs posterior ROAS dot plus HDI whiskers with truth as ×, response-curve overlays, one grid per scenario); 4 zero-effect channel result for S-C with its own headline; 5 holdout table; 6 OLS baseline comparison; 7 cross-check summary; 8 "What this does and does not prove" closing paragraph >= 500 characters noting that recovery on a disclosed DGP family is not a guarantee on reality, that the parameterization mismatch partially mitigates, and that real-world validation would require lift tests.

## DC-201..205 — Optimizer formulation (implement exactly)
- source: docs/SPEC-06_decision_layer.md §2
- type: protocol
- content: DC-201 objective — maximize `E_posterior[Σ_c β_c·Hill(x_c^ss; K_c, s_c)]` where `x_c^ss` is the steady-state adstocked spend of a constant weekly allocation; with normalized adstock weights the steady state equals x_c itself, and this simplification must be stated in the artifact caption. DC-202 estimation — Sample-Average Approximation over D = 500 posterior draws (thinned file, first 500 rows, deterministic); one optimization on the averaged objective; outcome uncertainty from evaluating the optimal x* under all 1000 draws (mean plus 90% HDI). DC-203 constraints — (a) Σ_c x_c = B equality; (b) 0 <= x_c <= 1.3 × max observed weekly spend per channel as a hard extrapolation guard visible in every output; (c) `search_brand` FIXED at its historical mean; (d) offline channels reallocate in weekly-equivalent terms with a caption noting real-world flighting granularity. DC-204 solver — `scipy.optimize.minimize(method='SLSQP')` with 20 restarts from seeded Dirichlet-random feasible points, keep best, convergence report warns in the artifact if restart spread exceeds 1% of the objective. DC-205 budget scenarios — B in {0.8, 1.0, 1.2} × historical mean weekly budget into `exports/allocation_scenarios.csv` with historical share, optimal share, spend a€, expected contribution mean plus HDI, and binding-constraint flags per scenario × channel.

## DC-301/302 — Headline gain metric and mandatory caption
- source: docs/SPEC-06_decision_layer.md §3
- type: schema
- content: `expected_gain_pct` = (E[contribution at x* with B=1.0] − E[contribution at historical mean allocation]) / E[total revenue] × 100, with 90% HDI over draws, plus `expected_gain_aeur_annual` = gain/week × 52; both go to SSOT tagged MODELED. The DC-302 caption is mandatory on every artifact showing the gain: "In-sample counterfactual under the fitted model; assumes response curves hold and competitors do not react. Guard rails: no channel is pushed beyond 1.3× its historically observed spend." — sourced from `captions.py`.

## DC-401 — Optimizer recovery test
- source: docs/SPEC-06_decision_layer.md §4
- type: nfr
- content: On S-A, run the optimizer on (i) the true parameters and (ii) the posterior; gates are allocation cosine similarity >= 0.90 between (i) and (ii) and regret <= 5% of true-optimal, where regret = true-optimal contribution minus contribution of the posterior-optimal allocation evaluated under TRUE parameters. On S-B: cosine >= 0.80, regret <= 10%. Results go to a RECOVERY_REPORT addendum plus SSOT key `optimizer_regret_sb`.

## DC-501..504 — Attribution-gap module
- source: docs/SPEC-06_decision_layer.md §5
- type: protocol
- content: DC-501 for every channel with platform reporting — `platform_roas` = Σ platform_conv_value / Σ spend (masked units cancel), `mmm_roas` = the MD-081 posterior; output per channel is platform ROAS, MMM ROAS (mean plus HDI), `overcredit_ratio` = platform/MMM-median, and P(platform > MMM). DC-502 Layer P check — on S-B the recovered overcredit ratios must reproduce the ORDERING of the simulated φ_c: display_video > meta > search_generic > search_brand. DC-503 Layer R output — `exports/attribution_gap.csv` plus a dumbbell chart at `reports/decide/dc_attribution_gap.png`; whatever the real result is, it ships, including channels where platforms UNDER-credit. DC-504 one interpretation paragraph >= 500 characters written from the marketing chair (view-through counting, brand-search claiming, last-click position), referenced to the numbers, with no vendor-bashing tone.

## DC-601 — Marginal-ROAS ladder (the Power BI what-if feed)
- source: docs/SPEC-06_decision_layer.md §6
- type: schema
- content: `scenarios.py` emits a marginal-ROAS ladder — for each reallocatable channel, the expected contribution change for ±€500/week around current spend (posterior mean plus HDI). This is the "where does the next euro go" table that names the project. SSOT keys: `next_euro_best_channel`, `next_euro_marginal_roas`.

## DC-701..705 — M6 exit gates
- source: docs/SPEC-06_decision_layer.md §7
- type: nfr
- content: DC-701 DC-401 optimizer-recovery gates green. DC-702 DC-502 ordering gate green. DC-703 determinism — two runs produce identical CSVs (seeded restarts, fixed draw subset). DC-704 constraint audit test — optimal allocations respect bounds exactly, `search_brand` unchanged, Σ = B to 1e-6. DC-705 every artifact exists and regenerates via `make decide` from committed posteriors with no sampling. The decision layer consumes committed thinned posteriors and marts and never refits.

## SPEC-07 §1 — Artifact inventory
- source: docs/SPEC-07_reporting_dashboard.md §1
- type: schema
- content: `reports/EXEC_SUMMARY.md` hand-written from SSOT numbers only; `reports/recovery/RECOVERY_REPORT.md` generated; `docs/PRIOR_ELICITATION.md` human plus agent, frozen at M4; `reports/executive_charts/*.png` from `make report`; `reports/NUMERIC_SSOT.md` from `scripts/generate_ssot.py`; `exports/*.csv` from `scripts/export_marts.py`; `dashboards/ambo.pbix` plus `docs/assets/dashboard_p*.png` manual; README and LIMITATIONS hand-written.

## RB-201..205 — Executive charts (exactly five)
- source: docs/SPEC-07_reporting_dashboard.md §2
- type: schema
- content: RB-201 `01_where_next_euro.png` — the money chart, marginal-ROAS ladder as horizontal bars with HDI whiskers, best channel highlighted, extrapolation-guard note, title "Where the next advertising euro works hardest (Client A)". RB-202 `02_truth_recovery.png` — S-B true-vs-posterior ROAS dot plot, the credibility chart. RB-203 `03_attribution_gap.png` — Layer R dumbbell, executive restyling of DC-503. RB-204 `04_contribution_waterfall.png` — Layer R average-week decomposition (base, seasonality, promo, each channel; posterior means, additive, a€). RB-205 `05_prior_value.png` — VR-501 forest plot restyled, elicited vs flat priors on Layer R.

## RB-301/302 — Chart data flow
- source: docs/SPEC-07_reporting_dashboard.md §3
- type: nfr
- content: Exec charts read only exports and SSOT-backed frames; a pytest recomputes RB-201's bars from `allocation_scenarios.csv` / posterior parquet and asserts a match. All charts regenerate WITHOUT sampling.

## RB-401..406 — Power BI dashboard (manual, specified)
- source: docs/SPEC-07_reporting_dashboard.md §4
- type: schema
- content: Source is the six `exports/` CSVs. Page 1 "Empfehlung" — optimal vs historical allocation clustered bars, expected-gain card with HDI, next-euro table, guard-rail note. Page 2 "Beiträge" — stacked area weekly decomposition, channel slicer, ROAS matrix with HDI columns. Page 3 "Kurven" — line charts per channel from `response_curves.csv` with HDI bands, current-spend marker, 1.3× guard line. Page 4 "Beweis" — recovery dot plot from `roas_summary.csv` with truth column where present, gate-status table, attribution-gap dumbbell. RB-405 German one-sentence subtitle per page and an a€ footer text box copied verbatim from `captions.py`. RB-406 screenshots to `docs/assets/dashboard_p1..p4.png`, `.pbix` committed, rebuild instructions in `dashboards/README.md`.

## SPEC-07 §5/§6/§6.1 — EXEC_SUMMARY and README structure
- source: docs/SPEC-07_reporting_dashboard.md §5-§6
- type: schema
- content: EXEC_SUMMARY <= 2 pages, mandatory order — the answer (<= 4 sentences: expected gain at same budget in a€ and % with HDI, the next-euro channel, the largest attribution gap, the recovery verdict in one clause); why trust this; what each channel does (table); platform numbers vs reality; recommendation with the two caveat sentences and a number attached to every claim; what would change this (<= 3 bullets from LIMITATIONS). README mandatory order — H1 plus one-sentence definition naming Bayesian MMM, a real anonymized Austrian advertiser, and PyMC; headline question blockquote then answer paragraph with epistemic tags; RB-201 then RB-202 (money first, credibility second); real vs synthetic vs modeled table; three-layer architecture explainer including the git-history claim linked to `scripts/check_layer_order.py`; results tables; dashboard screenshots; reproduce in <= 5 commands; anonymization protocol summary; architecture sketch, data statement, LIMITATIONS link, license, author block. §6.1 alternate framing for the Charter §7 degradation case lives in the spec so the outcome cannot tempt improvisation.

## RB-601 and SPEC-07 §7 — Chart and number standards
- source: docs/SPEC-07_reporting_dashboard.md §6-§7
- type: nfr
- content: No number outside SSOT (CI-checked); stack talk first appears in README §8. matplotlib >= 3.8 Agg, 12×6 in, dpi 150, Okabe-Ito palette via `ambo/report/style.py` with fixed channel colors across ALL charts; formatter module `ambo/report/format.py` ("a€1.2 M", ROAS "3.4×", percentages 1 decimal, tested). Every chart carries a business-English title, unit-labeled axes, a source note bottom-left, and an epistemic tag bottom-right. `captions.py` is the single home of the a€ caption, the DC-302 counterfactual caption, and the AG-070 anonymization paragraph — grep-enforced single occurrence in `src/`.

## EB-001/002 — Toolchain
- source: docs/SPEC-08_engineering.md §1
- type: nfr
- content: Python 3.12 plus `uv`; `ruff` for lint and format at line 100; `mypy --strict` on `src/ambo/` with `ignore_missing_imports` for pymc/arviz/pytensor. Pre-commit hooks: ruff, ruff-format, end-of-file-fixer, check-yaml, detect-private-key, `scripts/leak_scan.py --staged`, nbstripout (notebook outputs never committed — leak surface).

## SPEC-08 §2 — Repository layout (declared exact)
- source: docs/SPEC-08_engineering.md §2
- type: schema
- content: Root carries PROJECT_CHARTER.md, AGENTS.md, README.md, LIMITATIONS.md, LICENSE (MIT), Makefile, pyproject.toml, .pre-commit-config.yaml, .gitignore, .env.example (AMBO_PRIVATE_DROP only). `config/` holds settings.yaml, scenarios/, priors_synthetic.yaml, priors_real.yaml. `src/ambo/` holds simulate/ (dgp.py, spend_patterns.py, platform_bias.py, truth.py), intake/ (standardize.py, anonymize.py, validate.py), model/ (mmm.py, transforms.py, elicit.py, diagnostics.py, posterior_io.py), validate/ (recovery.py, holdout.py, sensitivity.py, baseline_ols.py, crosscheck.py, report.py), decide/ (optimizer.py, attribution_gap.py, scenarios.py), report/ (charts.py, format.py, style.py, captions.py), common/ (config.py, db.py, logging.py). Plus dbt/, scripts/, data/, exports/ (gitignored except .gitkeep), reports/, dashboards/, docs/, tests/. Empty dirs get `.gitkeep`. NOTE: this list omits `model/fit.py` and `model/priors.py`, which 03_MODULES.md defines as binding contracts — see conflicts WARNING 3.

## EB-030 — Pinned dependencies
- source: docs/SPEC-08_engineering.md §3
- type: nfr
- content: Runtime pins — `pandas>=2.2,<3`, `numpy>=1.26,<3`, `pymc>=5.15,<6`, `arviz>=0.18`, `pytensor` as pinned by pymc, `pymc-marketing>=0.8` (crosscheck only), `scipy>=1.13`, `duckdb>=1.0`, `dbt-core>=1.8,<2`, `dbt-duckdb>=1.8,<2`, `holidays>=0.50`, `matplotlib>=3.8`, `pydantic>=2.7`, `PyYAML>=6`, `python-dotenv>=1`. Dev — `pytest>=8`, `pytest-cov`, `ruff`, `mypy`, `pre-commit`, `nbstripout`. `uv.lock` committed. Forbidden-deps test blocks robyn, lightweight_mmm, prophet, and sklearn. Any upgrade or new dependency requires an ADR, including small ones.

## EB-040/041 — Configuration and secrets
- source: docs/SPEC-08_engineering.md §4
- type: protocol
- content: All non-secret settings live in `config/` and are loaded once via pydantic Settings. The ONLY env var is `AMBO_PRIVATE_DROP` (a path); its CONTENTS are secret — no code may copy from it except `intake/standardize.py`, and nothing under it is ever logged (a logger filter asserts the path is absent from messages). Adding another env var is a spec deviation requiring an ADR.

## SPEC-08 §5 — Makefile canonical interface
- source: docs/SPEC-08_engineering.md §5
- type: api-contract
- content: Targets — `setup`, `simulate`, `validate-sim`, `intake` [human], `anonymize` [human], `validate-intake`, `transform`, `fit-synthetic`, `fit-real`, `recover`, `sensitivity`, `decide`, `ssot`, `export`, `report`, `test`, `lint`, `all`. `all` = transform → recover → sensitivity → decide → ssot → export → report and assumes fits exist; fits are explicit targets because they cost 30-90 min total. EB-050: sampling targets print expected runtime up front and write posteriors atomically (temp plus rename) so an interrupted fit never leaves partial files.

## EB-060/061 — CI
- source: docs/SPEC-08_engineering.md §6
- type: nfr
- content: `ci.yml` is the only workflow (no cron). Six required jobs: (1) lint; (2) test including the smoke-fit — S-A 60-week subset, 1 chain × 200/200 draws, asserting it samples without error and R-hat is finite, under a 15-minute budget, marked `@pytest.mark.smoke`, running in CI and skipped locally unless `SMOKE=1`; (3) dbt build on committed data (synthetic and real_anon are in-repo so CI needs no private inputs); (4) `check_ssot_consistency.py`; (5) `check_layer_order.py`; (6) `leak_scan.py` pattern subset. Full fits NEVER run in CI; golden comparisons in CI run against committed thinned posteriors with VR-702 tolerance bands.

## EB-070..073 — Testing policy
- source: docs/SPEC-08_engineering.md §7
- type: nfr
- content: No network in any test — assert no `requests` import outside intake, which itself only reads local files. Synthetic test fixtures live under `tests/fixtures/` only; intake fixtures are generated lookalikes, never real excerpts. Coverage >= 80%; every post-M2 bug gets a regression test in its fix PR. Golden artifacts are the VR-702 bands plus DC determinism, regenerated via `scripts/generate_golden_metrics.py` with PR justification.

## EB-080..082 — Git conventions
- source: docs/SPEC-08_engineering.md §8
- type: protocol
- content: Conventional commits carrying REQ IDs; one milestone equals one PR; `main` protected by all six CI jobs. `.gitignore` covers `.venv/`, `data/warehouse/`, `data/cache/`, `*.nc`, `exports/*.csv`, `.env`, `__pycache__/`, `.pytest_cache/`, `dbt/target/`, `dbt/logs/`, `.ipynb_checkpoints/`; committed by design are `data/synthetic/`, `data/real_anon/`, `data/posteriors/*.parquet`. History is append-only — no force-push, no history rewriting, ever, because the layer-order argument depends on trustworthy history; if something private lands in a commit, the remedy is credential/data rotation plus repo surgery performed BY THE HUMAN with the leak documented, and agents never rewrite history themselves.

## GB-101..103 — Epistemic tags
- source: docs/SPEC-09_governance_quality.md §1
- type: protocol
- content: Four tags — GROUND-TRUTH, REAL-ANON, MODELED, CALIBRATED. The a€ caption and the DC-302 counterfactual caption live in `ambo/report/captions.py` only, with a grep-test enforcing single occurrence in `src/`. SSOT rows carry a `tag` column and README/exec numbers carry tags inline.

## GB-201/202 — ADR process
- source: docs/SPEC-09_governance_quality.md §2
- type: protocol
- content: ADRs live at `docs/ADR/ADR-NNN_short-title.md`, append-only, with a Context / Decision / Consequences / Spec-deviations-with-REQ-IDs template. Pre-planned slots: ADR-001 permission outcome plus sector labeling; ADR-002 channel-mapping decisions including the `other` share; ADR-003 anonymization recipe version confirmation (records that factors were drawn and where they are kept, never their values); ADR-004 Layer R window plus any data reconstructions; ADR-005 reparameterization ladder rung if beyond 1. Standard triggers: spec deviation, new dependency, gate widening, charter change, degradation decision.

## GB-301..303 — Numeric SSOT mechanism
- source: docs/SPEC-09_governance_quality.md §3
- type: protocol
- content: `reports/NUMERIC_SSOT.md` is generated only by `scripts/generate_ssot.py` with columns `key | value | unit | tag | produced_by | updated_at`. Minimum keys: recovery gate results per scenario (`recovery_pass_sa/sb/sc`, `roas_coverage_<scenario>`), `zero_channel_verdict`, `roas_<channel>_median` and `roas_<channel>_hdi90` (Layer R), `expected_gain_pct` plus HDI bounds, `expected_gain_aeur_annual`, `next_euro_best_channel`, `next_euro_marginal_roas`, `overcredit_ratio_<channel>`, `optimizer_regret_sb`, `holdout_mape_real`, `prior_freeze_commit`, `layer_r_weeks`, `media_share_of_revenue_real`, `divergences_real_fit`. `scripts/check_ssot_consistency.py` runs in CI — README, EXEC_SUMMARY, and RECOVERY_REPORT numeric literals with SSOT-adjacent units must match SSOT within documented rounding, with a whitelist file carrying per-entry justification comments.

## GB-501..503 — Layer-order and prior-freeze enforcement
- source: docs/SPEC-09_governance_quality.md §5
- type: protocol
- content: `scripts/check_layer_order.py` asserts in CI via git history (which is append-only): GB-501 the commit adding `reports/recovery/RECOVERY_REPORT.md` with all M3 gates green is an ancestor of any commit adding files matching `data/posteriors/R*.parquet` or `reports/model/diag_R.md`. GB-502 the commit freezing `config/priors_real.yaml` plus `docs/PRIOR_ELICITATION.md` (hash recorded in SSOT `prior_freeze_commit`) is an ancestor of any Layer R fit artifact commit, and neither file is modified after the freeze commit; a legitimate impossibility such as a channel absent from real data requires an APPENDED amendment section created BEFORE the fit plus an ADR — the frozen ranges themselves never change. GB-503 the README three-layer explainer links this script so reviewers can verify the mechanism, not just the claim.

## GB §6 — LIMITATIONS.md minimum contents
- source: docs/SPEC-09_governance_quality.md §6
- type: schema
- content: Nine required items — 1 recovery is on a disclosed DGP family and bounds implementation error, not model-misspecification error on reality; 2 Layer R window is short, stating `layer_r_weeks`, which parameters are prior-dominated and what that means; 3 anonymization, what a€ masking preserves and destroys (AG-041 list verbatim), absolute ROAS not interpretable; 4 in-sample counterfactual caveat for the gain metric, no competitive reaction, no creative quality, no cross-channel synergies; 5 brand-search endogeneity, why it is modeled but excluded from reallocation; 6 promo calendar reconstructed from memory (CALIBRATED) plus the VR-504 outcome; 7 weekly grain hides within-week dynamics and adstock length L=8 caps measurable carryover; 8 platform-reported metrics are themselves modeled objects; 9 MCMC reproducibility doctrine and what "reproducible" means here.

## GB §7/§8 — Gate index and deliberate non-existence
- source: docs/SPEC-09_governance_quality.md §7-§8
- type: nfr
- content: Data quality gates by domain — simulator SIM-070..075, agency intake AG-060..066, dbt models AD-040..044, model diagnostics MD-070..074, recovery VR-301..306 and VR-401, sensitivity VR-501..504, baselines/cross-check VR-601..602, decision layer DC-701..705. Deliberately absent: audit-finding registry, session handouts, re-verification matrix, cron. The governance showpieces are the layer-order proof, the prior freeze, the published anonymization protocol, and the leak scan — four mechanisms, each enforced by a script a reviewer can run.

## 02_WBS — Task card contract (46 tasks, T-001..T-806)
- source: docs/EXECUTION_BLUEPRINT/02_WBS.md
- type: protocol
- content: 46 tasks each sized to roughly one focused coding session (0.5-4 h), executed in ID order unless 04_DEPENDENCIES marks a parallel track. Every task card carries objective, rationale, prerequisites, inputs, outputs, depends-on/blocks, implementation notes, a validation command, objective acceptance criteria, and a traceability line of REQ IDs plus Charter refs plus deliverables. Cards list only deltas from the global DoR/DoD. `[HUMAN]` marks tasks an agent must not perform alone. Example binding detail (T-001): the baseline commit contains documentation only with zero code, and `.gitattributes` or git config pins LF for `*.csv`, `*.py`, `*.yaml`, `*.md` because byte-identical CSV gates depend on stable EOLs.

## 03_MODULES — Cross-cutting module conventions
- source: docs/EXECUTION_BLUEPRINT/03_MODULES.md §preamble
- type: api-contract
- content: Signatures are contracts, not implementations; a new public function must be added to the contract document in the same PR (contract-first rule). Config read only via `ambo.common.config.load_settings()`. Logging only via `get_logger(__name__)`; no `print` in `src/`. Typed exceptions with `AmboError` root and subclasses `ConfigError`, `DataContractError`, `GateFailure`, `IntakeError`, `LeakDetected`, `FitError`; never catch-and-continue silently; error messages never contain private-drop content or paths, and intake exceptions carry counts, not values. Every stochastic entry point takes or derives an explicit seed; library-global RNG state is never used. Single-process and single-threaded by design except PyMC's own chain parallelism; modules must be import-safe with no side effects at import. Long-running entry points log start/end plus wall time. Unit tests colocated at `tests/unit/test_<module>.py`; every public function has at least one direct test. Every artifact writer embeds provenance (input hashes, config hash, git commit, seed).

## 03_MODULES — `ambo/common/` contracts
- source: docs/EXECUTION_BLUEPRINT/03_MODULES.md §1
- type: api-contract
- content: `Settings(BaseSettings)` fields — `channels: list[str]` (7, taxonomy order), `adstock_length: int` (=8), `paths: PathsConfig`, `sampler: SamplerConfig` (chains=4, tune=1000, draws=1000, target_accept=0.9, seed=42, init string), `private_drop: Path | None`; invariants `extra='forbid'`, channels exactly the SPEC-02 §5.2 taxonomy, lists immutable after validation. `load_settings() -> Settings` cached and idempotent, raising `ConfigError` with the failing key path. `PrivatePathFilter` redacts the resolved private-drop path to `<PRIVATE_DROP>` in every record. `db.py` is the ONLY data doorway for model/decide/report: `connect(read_only=True)` raising `DataContractError("run make transform")` if the warehouse is missing; `read_mmm_input(layer)` with postconditions gapless ascending weekly `week_start`, the documented column set, no NaN in spends (0-filled), revenue > 0; `read_platform_reported(layer)`; `read_dim_layer()`.

## 03_MODULES — `ambo/simulate/`, `intake/`, `model/`, `validate/`, `decide/`, `report/` contracts
- source: docs/EXECUTION_BLUEPRINT/03_MODULES.md §2-§7
- type: api-contract
- content: simulate — `ScenarioConfig` invariants weeks in {156, 104, 78} and S-C iff `display_video.beta == 0`; `adstock_recursive` pure, causal, `a_0 = 0`; `hill` with `Hill(K)=0.5` exact and domain a >= 0; `SimulationResult` frozen with components re-summing to revenue within 1e-6 at construction; byte-stable JSON truth files (sorted keys, fixed float format) written atomically; full 3-scenario build under 30 s. intake — the only package allowed to read `$AMBO_PRIVATE_DROP`; `RescaleFactors` enforces the Uniform(0.4, 2.5) bounds and the 0.15 separation, has a REDACTED `__repr__`, and is never serialized; `IntakeManifest` has no factor fields structurally; every ambiguity is a hard stop with a count-only message. model — `transforms.py` holds the only back-transformation site with `to_model_scale`/`from_model_scale` property-tested as an exact inverse pair to 1e-12; `ScaleFactors` frozen with all values > 0 and an all-zero channel raising `FitError`; `build_model` post-condition is the documented free-RV name set with no layer/scenario branching (grep-tested); `fit.py` runner exposes variants `flat`, `nopromo`, `loco-<channel>`, `holdout` with sampler settings only from Settings; `posterior_io` embeds scale factors, data hash, prior sha256, sampler settings, git commit, and seed, and the loader refuses files lacking metadata; `DiagGates.standard()`/`layer_r()` are explicit at the call site and never auto-selected. validate — never fits; all reports regenerate from committed thinned posteriors, with a module-level test that deletes the netCDF and regenerates. decide — never refits, has no import path to `pm.sample`, and `optimize_allocation` post-conditions are Σx = B ±1e-6, exact bounds, fixed channels at historical mean, and a `converged_clean=False` flag when restart spread exceeds 1% (never silent). report — reads exports, SSOT side-files, and committed posteriors, performing no computation that changes numbers.

## 04_DEPENDENCIES — Forbidden import edges (guard-tested)
- source: docs/EXECUTION_BLUEPRINT/04_DEPENDENCIES.md §1, docs/EXECUTION_BLUEPRINT/03_MODULES.md §10
- type: api-contract
- content: Allowed edges — simulate → common only; intake → common; model → common; validate → common plus model (fit/posterior_io/transforms) plus truth.json files; decide → common plus model.posterior_io/transforms read-only; report → common plus exports/SSOT side-files plus model.posterior_io read-only; common → nothing in ambo. FORBIDDEN and guard-tested by T-010: `simulate ↔ model` in either direction; `pymc_marketing` outside `validate/crosscheck.py`; `requests` anywhere; `pm.sample` outside `model/fit.py`; CSV reads inside `model/` or `decide/` (mart-only per AD-030).

## 04_DEPENDENCIES — Critical path and compute ledger
- source: docs/EXECUTION_BLUEPRINT/04_DEPENDENCIES.md §4, §7
- type: nfr
- content: Critical path runs T-001 → T-002 → T-003 → T-004 → the T-006..T-011 cluster → T-101 → T-102/103/104 → T-105 → T-106 → T-107 → T-108 → T-109 → T-201 → T-202 → T-203 → T-204 → T-301 → T-302/304 → T-305 → T-306 → T-307 (S-A fit) → T-402 (S-B/S-C fits) → T-401/406/407/408/409 → T-410 → the external drop-and-permission wait → T-510 freeze → T-601 → T-602..605 → T-705 → T-803 → T-804/805 → T-806. The single external wait sits after T-410. Compute ledger: 14 full-budget fits estimated at 15-35 min each on 4 cores — P-SA, P-SB, P-SC, three holdouts, P-SB__flat, R, R__flat, R__loco, R__nopromo, R holdout, and two crosschecks. Fits are explicit make targets, never CI, never implicit in `make all`; posteriors written atomically; wall-times logged to BUILD_LOG, and cumulative compute exceeding 2× the estimate is an effort-budget event.

## 05_IMPLEMENTATION_GUIDES — Simulator authoring rules
- source: docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md §1
- type: protocol
- content: The scenario YAML is authoritative; the SPEC-01 §4 table is duplicated into a test constant and a test asserts YAML equals table — divergence fails the test and a human reconciles, never a silent fix toward either side. Promo weeks per simulated ISO year: exactly 10 — the Black-Friday week (ISO week containing the 4th Friday of November), 2 Advent weeks nearest Dec 24 that are not the BF week, 2 spring weeks inside W14-22, and 5 spread evenly avoiding adjacency; S-C's half year 2023 pro-rates to 5. Burst schedules per year: print 8 bursts × 2 weeks (3 anchored — 2 Advent, 1 Schulbeginn), radio 5 bursts × 3 weeks (2 anchored in Advent); bursts must not overlap within a channel; seeded-random placement of unanchored bursts happens ONCE at authoring time and is frozen into YAML, so runtime randomness is limited to spend-level noise. Season windows: `advent_flag` is the ISO week containing Dec 24 plus the 3 preceding weeks (4 total); `schulbeginn_flag` is the second Monday of September plus the preceding ISO week; `jan_dip_flag` W02-W05; `spring_flag` W14-W22; `summer_lull_flag` W29-W33; output covers ISO years 2019-2027. Spend patterns: one `np.random.Generator` per scenario with a fixed documented draw order (channels in taxonomy order, then the noise vector), never reused across scenarios; seasonal multipliers apply to the mean, then draw, then floor, then round; the meta pulse convention must be picked, documented, and tested.

## 06_CHECKLISTS — Per-milestone acceptance checklists
- source: docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md
- type: nfr
- content: Seven checklist classes per milestone — implementation, code review, QA, scientific validation, documentation, repository hygiene, and release (full class at M7, a mini merge-readiness version earlier). Unticked equals not done; blocks are pasted into the milestone PR and ticked item-by-item with evidence links. The shared `[STD]` merge-readiness block requires: `make lint && make test` green locally with output pasted; all six CI jobs green on the PR head commit; coverage >= 80% of `src/ambo/` linked; no TODO/FIXME/XXX in touched files; no new pytest warnings and no unjustified ruff/mypy suppressions; conventional commits with REQ IDs; a `docs/BUILD_LOG.md` entry appended; SSOT regenerated in the PR if any reported number changed; no file added outside the SPEC-08 §2 layout and no gitignored-by-design artifact committed; and an explicit reviewer statement that 07_QUALITY_STANDARDS and 09_ANTI_PATTERNS were checked.

## 07 Part A — Measurable quality thresholds
- source: docs/EXECUTION_BLUEPRINT/07_QUALITY_STANDARDS.md Part A
- type: nfr
- content: Test coverage >= 80% of `src/ambo/` lines with no module below 60%. Function length <= ~60 lines with a hard review flag above 80. Cyclomatic complexity <= 10 per function (ruff C901, mccabe max 10). Module size <= ~500 lines. mypy `--strict` clean. ruff clean at line 100. Simulator runtime: 3 scenarios under 30 s. Full fit: <= ~35 min/fit at MD-050 on 4 cores, measured and logged to BUILD_LOG. CI smoke: under 15 min wall (pytest-timeout 900 s). `make report`: under 2 min with zero sampling. Memory: full fit under 8 GB RSS, thinned parquet under 5 MB each. Determinism: simulator byte-identical, optimizer/exports byte-identical two-run, MCMC to 3 decimals same machine plus seed and ±0.15·SD bands cross-platform with draw checksums never used. Sampler health, PPC, and recovery thresholds as per the SPEC gates. No point estimate without an HDI; every headline number tagged. Docs completeness per RB §6, GB §6, RB §5, MD-060. 100% of unit-bearing literals traceable to SSOT or whitelisted with justification. Visualization at 12×6 in, dpi 150, Okabe-Ito fixed channel colors, with title/axes/source/tag on every chart. Leak scan green with zero real values, names, or factors in the repo forever.

## 07 Part B — Coding standards
- source: docs/EXECUTION_BLUEPRINT/07_QUALITY_STANDARDS.md Part B
- type: protocol
- content: snake_case modules/functions/variables, PascalCase classes, UPPER_SNAKE constants; channel identifiers appear only as the canonical taxonomy strings, never abbreviated or re-cased; unit suffixes `_eur`, `_aeur`, `_scaled`, `_wk` at boundaries; test names `test_<unit>__<behavior>`. Each `src/ambo/<pkg>/` belongs to exactly one SPEC and no file exists without an owning SPEC. Absolute imports only, no relative imports beyond one dot, no wildcards, no imports inside functions except documented guarded heavy deps; any new third-party dependency requires an ADR without exception. All non-secret config flows `config/*.yaml` → pydantic schema → `load_settings()` with `extra='forbid'`; no module-level tunables and no argv-driven science parameters — the CLI selects what to run and config defines how. Logging: INFO for phase progress, DEBUG for internals, WARNING for tolerated anomalies which must also surface in artifacts (a warning that only lands in a log is a silent failure), ERROR before raising; never log private-drop contents or paths, factor values, campaign names, or absolute real €. Error handling: typed exceptions carrying machine-usable fields, never `except Exception: pass`, never sentinel returns, fail fast at the richest-context boundary, and `GateFailure` lists every failed gate rather than the first. Testing: test the requirement in the same commit named by it; prefer property/round-trip/closed-form tests for math; deterministic synthetic fixtures with poisoned fixtures for every gate's failure direction; markers `smoke` and `fit`; `--strict-markers`; no network, no sleeps, no wall-clock dependence. Documentation: every public function documents purpose, args/returns semantics, raised exceptions, and `Implements: <REQ-IDs>`; generated docs are never hand-edited and hand-written docs take numbers only from SSOT. Commits and PRs: conventional commits, one milestone one PR, ticked checklist with evidence, no force-push or rebase or amend of pushed history, and merge commits rather than squash because task-level commits are part of the layer-order evidence trail. ADR triggers and append-only rule. Refactors ride behind green tests only and never touch frozen priors, the elicitation doc, or committed posteriors post-M4. Debt is recorded in BUILD_LOG with owner and planned phase; TODO comments in code are forbidden; debt that would violate privacy, determinism, or layer order is a defect that blocks merge, not debt.

## 08_PATTERNS — Prescribed design patterns and their locations
- source: docs/EXECUTION_BLUEPRINT/08_PATTERNS.md
- type: protocol
- content: Functional Core / Imperative Shell governs everywhere — pure computation wrapped by thin IO shells, because the determinism gates are only achievable with all randomness and IO at the edges. Pure functions for all math. Configuration Objects as pydantic models with `extra='forbid'`, frozen where possible. Repository pattern with `common/db.py` as the single mart doorway and `posterior_io` as the single posterior doorway. Factory for `DiagGates.standard()`/`layer_r()`, `AllocationConstraints`, and `build_model`, so the choice is explicit and greppable. Strategy for fit variants inside one parameterized runner. Builder for `pm.Model` construction step-by-step inside one function, not a class hierarchy. Dependency Injection by passing Settings, PriorConfig, ScaleFactors, RNG Generator, and connections as arguments, constructed only in shells. Pipeline via Makefile targets with artifact handoffs and no in-memory handoffs across stages. Registry for the export writer and SSOT fragment producers. Template Method for generated prose with numeric slots. Atomic write via temp-plus-rename for posteriors, truth, exports, and SSOT. Bounded prescribed Retry ONLY for the MD-073 ladder and the DC-204 solver restarts. Guard clause / fail-fast at intake env check, db contract assertions, posterior loader metadata refusal, and gate runners. Caching limited to committed thinned posteriors, the pytensor compiledir in CI, and memoized `load_settings()`. Implicit state machine encoded in git history and checked by `check_layer_order.py`. Composition over inheritance everywhere. Deliberately NOT used: ORM layers, plugin systems, event buses, async, DI containers, abstract base classes for future flexibility, and microservice/service-layer splits.

## 09_ANTI_PATTERNS — Forbidden implementations A-1..A-20
- source: docs/EXECUTION_BLUEPRINT/09_ANTI_PATTERNS.md
- type: protocol
- content: A-1 simulator-model incest (sharing transform code) collapses the recovery argument — AST guard test. A-2 magic numbers make spec drift invisible — settings objects plus grep review. A-3 hardcoded paths break fresh-clone reproduction and leak private paths — paths config plus pathlib plus leak scan. A-4 notebook-driven production — nbstripout, leak scan, notebooks read make-produced artifacts only. A-5 hidden state and mutable globals break determinism gates intermittently — explicit Generator injection. A-6 scientific data leakage (scale factors on the full window for a holdout fit, future weeks in features, truth.json steering Layer P priors, calibrating against platform conversions) makes results fake-good — leakage tests plus the MD-040 channel-agnostic test. A-7 silent failures ship a red gate as green — exit-code tests plus poisoned fixtures per gate. A-8 copy-paste logic causes SSOT violations — single-home rules for back-transform, captions, ROAS computation, and numbers. A-9 spec drift — spec-table equality tests plus ADR requirement. A-10 prior tampering after freeze destroys the central epistemic claim — GB-502. A-11 point estimates without uncertainty. A-12 unsanctioned caching or memoization of results — posterior metadata hashes plus loader refusal. A-13 over-engineering — patterns-not-used list plus the scope walls plus the review question "which gate does this abstraction serve?". A-14 premature optimization — optimize only on a measured breach. A-15 circular imports. A-16 configuration duplication, with the live risk being taxonomy drift between Python and dbt — a pytest equality check. A-17 history rewriting makes the layer-order proof unverifiable. A-18 gate gaming (widening thresholds, cherry-picking seeds, re-running until green, marking S-C expected-fail). A-19 unit-masking mistakes in a€ discipline. A-20 compute in CI.

## 10_VALIDATION_GATES — Gate classes and milestone mapping
- source: docs/EXECUTION_BLUEPRINT/10_VALIDATION_GATES.md
- type: nfr
- content: Eleven gate classes with milestone mapping — G-ARCH (P2 and standing from P3), G-DATA-P (M1), G-DATA-W (P2 inside the M2 PR), G-DATA-R (M4), G-ENG (every milestone), G-SCI-1..5 (M1, M2, M3, M5, M6), G-VIZ (M7), G-DOC (M4 elicitation and M7 all), G-GOV (M0 scaffold, M3 mechanisms, M4 freeze/leak, standing), G-PORT (M7), G-REL (M7 final). Gate IDs from the SPECs are authoritative; this catalog adds the class grouping and the blueprint-level gates BP-G-01 guard tests, BP-G-02 scenario-YAML equality with minimal S-C/S-B diff, BP-G-03 taxonomy equality between dbt vars and settings.yaml, and BP-G-04 permission documentation before any private file is processed. Each gate carries a trigger, a runner command, an evidence artifact, and a failure protocol. Notable failure protocols: a red simulator gate is an implementation bug until proven otherwise and the §4 table is never tuned; a red layer-order gate is NEVER fixed by history edits — the process was violated, so stop and tell the human; a leak-scan hit means STOP with human-led remediation; every intake gate failure is a stop-and-ask; at G-PORT only wording may change because numbers are SSOT-locked.

## 11_ACCEPTANCE_CRITERIA — Global Definition of Ready and Definition of Done
- source: docs/EXECUTION_BLUEPRINT/11_ACCEPTANCE_CRITERIA.md §1-§3, §5
- type: nfr
- content: Acceptance criteria are objective — verifiable by a command, test name, file inspection, or numeric threshold; the words "clean", "good", and "reasonable" are banned from criteria. DoR requires: dependencies merged; spec basis identified by reading the REQ IDs in the actual SPEC, not the blueprint paraphrase; the module contract read for every file to be touched with new public APIs drafted contract-first; any BP-D decision the task exercises either accepted as default or explicitly overridden by the human and recorded, never silently re-decided; all input artifacts existing at canonical paths on `main`; human availability where the card says [HUMAN]; and `make lint && make test` green on `main` before branching. DoD requires: code complete per objective and contract; tests for the task's REQ IDs in the same commit with full suite green and coverage not reduced; every named gate plus all standing CI gates green; docstrings with `Implements:` tags and the contract doc updated if the public API changed; all affected committed artifacts regenerated in the same PR; zero TODO/FIXME in touched files and warning-free pytest output; single-home rules held; guard tests green; an explicit review pass stated in the PR; and every acceptance criterion ticked with evidence. Milestone acceptance requires phase exit criteria, a fully ticked checklist with evidence, green gate classes, and a merge without history rewriting — there is no "accepted with exceptions" state, since an exception is an ADR merged first.

## 11_ACCEPTANCE_CRITERIA §4 — DL-1..DL-10 expanded to objective verification
- source: docs/EXECUTION_BLUEPRINT/11_ACCEPTANCE_CRITERIA.md §4
- type: nfr
- content: DL-1 probe protocol — clean clone, then `make setup && make transform && make recover && make decide && make ssot && make export && make report` using only committed artifacts with no fits, expecting zero errors, then compare regenerated reports and exports to committed versions with text artifacts byte-equal and MCMC-derived numbers within VR-702 bands, with the log attached to the release PR; separately `make simulate && make validate-sim` must byte-reproduce `data/synthetic/`. DL-2 through DL-10 each map to a named file, a named test, a named SSOT key, or a structure test, as recorded in the deliverable requirement entries in `requirements.md`.

## 12_RISK_REGISTER — Per-milestone risk controls
- source: docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md
- type: protocol
- content: Charter R-1..R-9 remain authoritative and are expanded per milestone with mitigation, fallback, and detection triads, reviewed at each phase entry. Load-bearing controls: M0 — LF pinned at T-001 and pathlib only, with CI-versus-local hash comparison at T-108. M1 — SIM-074 closed-form and impulse tests written BEFORE dgp assembly; fixed float format, LF, and sorted JSON keys for determinism. P2 — the `fct_mmm_input` contract frozen at T-203 with an ADR required for any later change; BP-G-03 taxonomy equality test. M2 — scaling enforced by design plus prior-predictive sanity before MCMC; log-space Hill where needed for numerics at the domain edges; scale factors computed per fitting slice by construction with a leakage test at T-403. M3 — gates already calibrated for collinearity so seasonality is not removed; tolerance bands rather than checksums; a false-positive-control failure is a STOP, not a tuning opportunity. M4 — privacy by construction with factors never serialized, T-507 started immediately, a drop-independent backlog filling the wait, and the freeze deadline allowed to slip but a fit before freeze never allowed. M5 — freeze enforcement in CI with VR-501 as the only sanctioned outlet for prior pressure. M6 — fixed-set constraint by construction with a DC-704 audit; seeded restarts and a fixed draw subset for determinism; hard 1.3× bounds with binding flags. M7 — SSOT pipeline plus checker plus RB-301 recompute test; exports frozen early; scope walls plus forbidden-deps test; G-PORT tone review. Cross-cutting — CI enforcement of layer order from M3 rather than an honor system, with no history rewrite as remediation; per-phase effort tracking against the Charter tripwire; the blueprint plus BUILD_LOG as the multi-agent handoff artifacts.
