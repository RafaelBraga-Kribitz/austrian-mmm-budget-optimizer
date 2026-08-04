# SPEC-04 — The MMM (raw PyMC): Math, Priors, Sampling, Diagnostics

Requirement IDs: `MD-xxx`. Code in `src/ambo/model/` (`mmm.py` model builder,
`transforms.py` scaling, `diagnostics.py`, `posterior_io.py`). One model definition
serves ALL layers/scenarios — only data + prior YAML differ.

---

## 1. Design commitments

- MD-001: Additive in revenue LEVEL (a€/€), not log (AGENTS T-9): contributions must
  decompose additively for the waterfall and optimizer.
- MD-002: The model builder signature:
  `build_model(df: fct_mmm_input slice, channels: list[str], priors: PriorConfig) -> pm.Model`.
  No scenario-specific branches inside; channel list drives everything.
- MD-003: `pymc-marketing` appears ONLY in `src/ambo/validate/crosscheck.py`
  (SPEC-05 §6), never in the primary model path.

## 2. Model math (implement exactly)

With t = 1…T weeks, c = channels, all on SCALED variables (§3):

```
μ_t = α                                   # intercept (scaled base)
    + τ · t/T                             # linear trend
    + Σ_{j=1..4} [ γ_sj sin(2πjt/52.18) + γ_cj cos(2πjt/52.18) ]   # yearly Fourier, order 4
    + δ_promo · promo_t
    + δ_advent · advent_t                 # Austrian calendar dummies ON TOP of Fourier
    + δ_jan · jan_dip_t
    + Σ_c β_c · Hill(adstock(x_c; λ_c); K_c, s_c)

y_t ~ Normal(μ_t, σ)
```

- MD-020: Adstock: geometric, implemented as a fixed-length convolution with
  normalized weights `w_i = λ^i / Σ_{i=0..L−1} λ^i`, L = 8 weeks (covers half-lives
  up to ~2.5 wk; L is config, not code). Normalized weights (unlike SPEC-01's raw
  recursion) keep β interpretable as saturated contribution — the DELIBERATE
  simulator/model mismatch in parameterization is part of the realism (the model
  never sees the true DGP form exactly); the shared-shape unit test (MD-070) checks
  correlation of transform outputs, not equality.
- MD-021: Hill exactly as SPEC-01 §2.2. Both transforms in `transforms.py`, vectorized
  pytensor ops, unit-tested against numpy references.
- MD-022: Calendar dummies use the SAME `season_windows.csv` seed (AD-020).

## 3. Scaling (AGENTS T-1)

- MD-030: `y_scaled = revenue / mean(revenue)`; per-channel `x_scaled = spend /
  mean(nonzero spend of that channel)`. Scale factors stored alongside the posterior
  (posterior_io) and applied inversely by ALL reporting code via one tested pair
  `to_model_scale` / `from_model_scale`. K priors are specified in SCALED spend units
  in the YAML (the elicitation doc talks €; the YAML writer converts and records both).

## 4. Priors — structure (`PriorConfig`, pydantic, loaded from YAML)

Per channel: `lambda_c ~ Beta(a_c, b_c)`; `K_c ~ Gamma(shape, rate)` (scaled units);
`s_c ~ Gamma(3, 2)` truncated to [0.3, 3.0]; `beta_c ~ HalfNormal(σβ_c)`.
Globals: `α ~ Normal(1.0, 0.3)` (scaled); `τ ~ Normal(0, 0.1)`; Fourier γ ~
Normal(0, 0.15); `δ_promo ~ Normal(0.1, 0.05)`; `δ_advent ~ Normal(0.3, 0.15)`;
`δ_jan ~ Normal(−0.1, 0.1)`; `σ ~ HalfNormal(0.1)`.

- MD-040: Layer P priors (`config/priors_synthetic.yaml`): WEAKLY informative,
  channel-agnostic (same Beta(2,4) on all λ, same HalfNormal(0.15) on all β, K ~
  Gamma(2, 1.3) around 1.5× mean spend). Rationale: recovery must come from data +
  structure, not from priors that encode the truth table. A test asserts
  priors_synthetic contains NO channel-differentiated values.
- MD-041: Layer R priors (`config/priors_real.yaml`): ELICITED per channel from agency
  experience via §6, frozen at M4 (Charter E-3).

## 5. Sampling settings (fixed)

- MD-050: NUTS via `pm.sample`: 4 chains, tune=1000, draws=1000, `target_accept=0.9`,
  `random_seed=42`, `init='jitter+adapt_diag'`. Full budget for all reported fits;
  the CI smoke-fit profile (chains=1, tune=200, draws=200, S-A first 60 weeks) exists
  only in `tests/` and is never reported.
- MD-051: Posterior saved via ArviZ to netCDF locally (gitignored) AND a thinned
  parquet (every 4th draw, ⇒ 1000 rows × parameters) committed under
  `data/posteriors/<layer>.parquet` for report regeneration without refitting.

## 6. Prior elicitation (the marketing-knowledge deliverable)

- MD-060: `docs/PRIOR_ELICITATION.md` — one section per Layer R channel with EXACTLY
  these fields:
  1. *Half-life guess* (weeks, a range) → converted to Beta(a,b) for λ with mode at
     the implied λ and ~90% mass inside the range (conversion helper
     `ambo/model/elicit.py`, unit-tested).
  2. *Half-saturation spend guess* (€/week range, pre-masking units are FORBIDDEN
     here — the human reasons in relative terms: "around 1.5× our typical weekly
     spend") → Gamma for K in scaled units.
  3. *Plausible max weekly effect* ("if we saturated this channel, could it plausibly
     add more than X% of an average week's revenue?") → σβ.
  4. **Rationale** — free text, ≥ 100 characters, first person, grounded in agency
     practice ("in my experience regional print for this segment keeps working for
     ~2 weeks after insertion because…"). This field is the portfolio signal;
     placeholder text fails the doc-lint test (MD-061).
  5. *Source*: `experience` | `literature` | `benchmark` (+ citation if not experience).
- MD-061: `tests/test_elicitation_doc.py`: parses the doc; every channel present;
  every rationale ≥ 100 chars and not matching boilerplate patterns; YAML values match
  the doc's stated ranges via the conversion helper.
- MD-062: The elicitation doc explicitly states it was frozen before fitting, with the
  freeze commit hash (SPEC-09 §5 verifies).

## 7. Diagnostics gates (per reported fit; `diagnostics.py` writes
`reports/model/diag_<layer>.md`)

- MD-070: Transform sanity (pre-fit, once): model transforms vs simulator transforms
  on S-A spend series correlate > 0.95 per channel (catches T-2 convolution bugs
  without sharing code).
- MD-071: R-hat < 1.01 all parameters; ESS_bulk > 400 & ESS_tail > 400; divergences
  = 0; BFMI > 0.3 all chains.
- MD-072: Posterior predictive check: PPC plot committed; observed y within the 90%
  PPC band for ≥ 85% of weeks.
- MD-073: If MD-071 fails, apply the reparameterization ladder IN ORDER, one rung per
  attempt, ADR if you leave rung 1: (1) raise target_accept to 0.95; (2) non-centered
  Fourier block; (3) tighten s_c prior to Gamma(4,3) trunc [0.5, 2.5]; (4) fix s_c = 1
  (logistic saturation) — rung 4 changes the model class and requires rerunning
  Layer P recovery.
- MD-074: Layer R relaxations (short data, expected): ESS threshold 300; divergences
  ≤ 5 tolerated IF energy plot committed and pair-plots show no funnel (human review
  note in diag report). Wide HDIs are NOT a failure — they are §8 content.

## 8. Model outputs (per layer; feed SPEC-03 exports and SPEC-05/06)

- MD-080: Decomposition: posterior mean + HDI weekly contributions per channel + base
  + seasonality + promo → `contributions_weekly` (waterfall-ready; additivity test:
  components sum to fitted μ within tolerance).
- MD-081: ROAS table: total-window average ROAS per channel (draws of Σm_c/Σx_c) —
  mean, 5%, 50%, 95%, P(ROAS < 1).
- MD-082: Response curves: contribution at 21 grid points (0…1.5× max observed weekly
  spend — NOT 2×; extrapolation guard starts here) per channel, mean + 90% HDI.
- MD-083: Marginal ROAS at current mean spend per channel (the "next €1000" table).
