# 05 — IMPLEMENTATION GUIDES (deep dives)

Technical guidance for the tasks where a wrong-but-plausible implementation is
likely. Math and pseudocode-level descriptions only — no implementation code (the
tasking forbids it); signatures live in [03_MODULES.md](03_MODULES.md).

---

## §1 Simulator (P1)

### §1.1 Scenario YAML authoring (T-101)
- The YAML is authoritative (SIM-002); the SPEC-01 §4 table is duplicated into a
  test constant, and a test asserts YAML == table. If they ever diverge, the test
  fails and a human reconciles — never "fix" silently toward either side.
- Promo weeks (BP-D-09): for each simulated ISO year list exactly 10 weeks:
  Black-Friday week (the ISO week containing the 4th Friday of November), 2 Advent
  weeks (choose the 2 advent-flagged weeks nearest Dec 24 that are not the BF
  week), 2 spring weeks (inside W14–22), 5 spread (author them roughly evenly in
  the remaining space, avoiding adjacency where possible). S-C's half year 2023:
  pro-rate → 5 weeks (26/52 × 10).
- Burst schedules: author start weeks so that per year: print 8 bursts × 2 weeks
  (3 anchored: 2 in Advent, 1 in Schulbeginn), radio 5 bursts × 3 weeks (2 anchored
  in Advent). Bursts must not overlap within a channel; seeded-random placement for
  the unanchored ones happens ONCE at authoring time (values frozen into YAML), not
  at runtime — runtime randomness stays limited to spend-level noise, which keeps
  SIM-001 byte-determinism trivially auditable.

### §1.2 Season windows (T-011)
Exact rules encoded in the generator (documented in-script with SPEC-01 §2.1
citations):
- `advent_flag`: the ISO week containing Dec 24 and the 3 preceding ISO weeks
  (total 4 weeks — "the 4 ISO weeks before and incl. the week of Dec 24" reads as
  4 flagged weeks; if the human intends 5, that is a one-line change + test update;
  record the reading in BUILD_LOG).
- `schulbeginn_flag`: Styrian school start = second Monday of September (fixed rule,
  source comment in script; the `holidays` package lacks school calendars); flag
  that ISO week and the preceding one ("2 weeks around").
- `jan_dip_flag`: ISO W02–W05. `spring_flag`: W14–W22. `summer_lull_flag`: W29–W33.
- Output covers ISO years 2019–2027 so any plausible Layer R window is covered
  (BP-D-10). One row per (iso_year, iso_week); `week_start` = that ISO week's Monday.

### §1.3 Spend patterns (T-102)
- One `np.random.Generator` per scenario, seeded from the scenario seed. Draw order
  fixed and documented: iterate channels in taxonomy order, draw the full weekly
  vector per channel, then the noise vector (T-105). Never reuse the generator
  across scenarios.
- Seasonal planning multipliers apply to the *mean* of the Normal, then draw, then
  floor, then round to whole €.
- Meta pulse: weeks where `(t-1) % 6 == 5` (i.e., every 6th week, first pulse at
  week 6) ×1.8 — pick one convention, document it in the docstring, test it.
- Collinearity switch (SIM-030): S-B/S-C advent factor 0.5→0.9 for
  search_generic/meta; all print/radio bursts anchored to demand peaks (the YAML
  schedules already encode this — the switch is expressed in data, the code just
  applies whatever the YAML says; the *test* asserts the S-B/S-C YAMLs actually
  differ from S-A in exactly this way).

### §1.4 Simulator adstock/Hill (T-104)
- Recursion `a_t = x_t + λ·a_{t−1}`, `a_0 = 0` — a plain forward loop over t is
  correct and clear; do not vectorize cleverly at the cost of the causality
  property. Closed-form check: constant x ⇒ `a_t = x·(1−λ^t)/(1−λ) → x/(1−λ)`.
- Impulse test: x = e_k ⇒ `a_t = λ^{t−k}` for t ≥ k, 0 before — this is the test
  that kills the reversed-convolution bug (trap T-2) at the simulator level.

### §1.5 Truth derivations (T-107)
- True average ROAS_c = Σ_t m_{c,t} / Σ_t x_{c,t} over the full window.
- True marginal ROAS at mean spend x̄_c (steady-state):
  `a = x̄_c/(1−λ_c)`, `dm/dx = β_c · s_c·K_c^{s_c}·a^{s_c−1}/(a^{s_c}+K_c^{s_c})^2 · 1/(1−λ_c)`.
- Response-curve samples: 21 grid points x ∈ [0, 2×max weekly spend], steady-state
  adstock `a = x/(1−λ)`, contribution `β·Hill(a)`. (Model-side curves later use
  1.5× max per MD-082 — the truth file's 2× grid is a superset; recovery comparisons
  restrict to the observed-spend range, VR-303.)
- Platform ROAS_c = Σ platform_revenue_c / Σ x_c (from §6 outputs).
- JSON: `sort_keys=True`, fixed `%.10g` float formatting, LF endings → byte-stable.

---

## §2 Model (P3)

### §2.1 transforms.py (T-301) — the highest-risk module
- Weights: `w_i = λ^i / Σ_{j=0}^{L−1} λ^j`, i = 0…L−1; adstocked
  `ã_t = Σ_i w_i · x_{t−i}` with x_{t<1} = 0. Normalization keeps β interpretable
  as saturated weekly contribution (MD-020) — this is deliberately NOT the
  simulator's parameterization.
- Causality invariant to test: changing x_{t+1} must not change ã_t (numpy
  reference); pytensor and numpy paths equal to 1e-10 on random input.
- In pytensor, implement via padded stack/roll of lagged views or conv1d with
  causal padding; whichever is chosen, the numpy twin in tests is the semantics
  oracle.
- Scaling (T-1): `ScaleFactors` computed ONCE per fit from the fitting slice (for
  holdout: from the training window only — leakage guard, test this), stored in
  posterior metadata, applied inversely by `from_model_scale` only. Grep-rule: no
  other module multiplies/divides by means.

### §2.2 build_model (T-304) — variable naming contract
| RV | Name | Prior (SPEC-04 §4) |
|---|---|---|
| Intercept | `alpha` | Normal(1.0, 0.3) |
| Trend | `tau` | Normal(0, 0.1) |
| Fourier | `gamma_sin`, `gamma_cos` (dim 4) | Normal(0, 0.15) |
| Promo | `delta_promo` | Normal(0.1, 0.05) |
| Advent | `delta_advent` | Normal(0.3, 0.15) |
| Jan | `delta_jan` | Normal(−0.1, 0.1) |
| Adstock decay | `lam` (dim channel) | Beta(a_c, b_c) |
| Half-sat | `k` (dim channel) | Gamma (scaled units) |
| Shape | `s` (dim channel) | Gamma(3,2) trunc [0.3, 3.0] |
| Effect | `beta` (dim channel) | HalfNormal(σβ_c) |
| Noise | `sigma` | HalfNormal(0.1) |

- Fourier design matrix: `sin(2πjt/52.18)`, `cos(2πjt/52.18)`, j = 1..4, t = 1..T —
  precomputed as `pm.Data`/np constants, not RV-dependent.
- Deterministic nodes to register (downstream reads them by name):
  `contribution` (week × channel, scaled), `mu`. Additivity test MD-080: sum of
  registered components equals `mu` within 1e-6 (posterior-mean level).
- Truncated Gamma for `s`: `pm.Truncated(pm.Gamma(...), lower=0.3, upper=3.0)`.
- No `if scenario == ...` anywhere — the channel list and priors object carry all
  variation (MD-002).

### §2.3 posterior_io (T-305)
- Thinning: stack (chain, draw) → 4000 rows → take every 4th → 1000 rows.
  Columns flat: scalars as `alpha`, vectors as `beta__meta` etc. (double
  underscore separator — parses back unambiguously since channel names contain
  single underscores).
- Metadata (parquet file metadata, JSON-encoded): schema_version, layer, variant,
  scale_factors, data sha256 (of the mart slice as CSV bytes), priors file sha256,
  sampler settings dict, git HEAD, seed, created_at. Loader hard-fails on missing
  scale_factors (T-1 guard).
- Atomic write: write to `<path>.tmp-<pid>` then `os.replace` (EB-050).

## §3 Elicitation converters (T-308)
- λ↔half-life: `λ = 2^(−1/h)` (h in weeks; check against SPEC-01 §4: h = ln0.5/lnλ).
  Note inversion: longer half-life ⇒ λ closer to 1.
- Beta from range [h_lo, h_hi]: target mode m = λ(h_mid) and
  P(λ(h_hi_mapped_lo) ≤ λ ≤ λ(h_lo_mapped_hi)) ≈ 0.9. Parameterize by concentration
  κ: `a = m·(κ−2)+1`, `b = (1−m)·(κ−2)+1` (mode-preserving family); solve κ via
  `scipy.optimize.brentq` on mass(κ) − 0.9 over κ ∈ (2.01, 500]. Deterministic,
  pure; tolerance ±1% mass asserted in tests.
- Gamma from K range (scaled units): same pattern — mode at midpoint,
  ~90% mass in range; parameterize shape k > 1 with rate θ = (k−1)/mode.
- σβ from "max plausible weekly effect share q of average weekly revenue": in
  scaled revenue units average week ≈ 1.0, so choose σβ such that
  P(β ≤ q) ≈ 0.95 ⇒ `σβ = q / 1.645` (HalfNormal 95th percentile ≈ 1.645σ).
  Document this formula in the elicitation doc.

## §4 Validation suite (P4)

### §4.1 Recovery metrics (T-401)
- ROAS draws: for each posterior draw, reconstruct weekly contributions m_{c,t}
  (model parameterization, model transforms, back-transformed to level units via
  ScaleFactors) then ROAS_c = Σm/Σx. Never use truth-side code (independence).
- Coverage: is truth ROAS inside the central 90% HDI of those draws
  (`arviz.hdi`)? Count channels covered per scenario vs the VR-301 row.
- Curve MAE%: evaluate posterior-mean curve on the truth grid points restricted to
  the observed spend range (min→max observed weekly spend); MAE / max(true curve)
  × 100 vs VR-303 thresholds.
- Zero-effect (VR-304, S-C `display_video`): P(ROAS < 0.2) ≥ 0.7 AND median
  contribution share ≤ 3%.
- Half-life ranking (VR-305): posterior median implied half-lives
  h = −1/log2(λ_median); require min(h_print, h_radio) > max(h_search_brand,
  h_search_generic).
- Total media share (VR-306): |Σ_c share_c − true| ≤ 10 pp.

### §4.2 Holdout (T-403)
- Split: fit weeks 1..T−13; forecast weeks T−12..T conditional on actual spend
  (posterior predictive with the trained parameters and the held-out design
  matrix; trend/Fourier extend naturally by t).
- Seasonal naive: ŷ_t = y_{t−52}; requires T ≥ 65 — assert.
- Report MAPE + share of held-out weeks inside the 90% predictive interval.
- Leakage guard: ScaleFactors from training window only (test asserts the
  metadata's factors differ from full-window factors).

### §4.3 OLS + HC1 (T-404)
- Design: same regressors, adstock at prior-mode λ (mode of the Beta in
  priors_synthetic), NO Hill. `β̂ = (X'X)^{-1}X'y`;
  HC1: `V = n/(n−k) · (X'X)^{-1} X' diag(e²) X (X'X)^{-1}`.
  Verify against a published textbook example in tests (assert to 1e-8).

### §4.4 pymc-marketing crosscheck (T-405)
- Use their `MMM` with geometric adstock + Hill/logistic saturation as available;
  match priors where the API exposes them; document every mismatch in
  `crosscheck_mapping.md` (this doc is a deliverable of VR-602 — reviewers judge
  the comparison by it). Compute channel-ROAS medians in the same units before
  correlating (their ROAS definition may differ — recompute from their posterior
  contributions rather than trusting a convenience method; state which you did).

## §5 Decision layer numerics (T-701/702)
- Optimize over shares p (Σp = 1, x = B·p) — better conditioned; bounds transform
  accordingly; fixed channels removed from the free vector and their spend
  subtracted from B before solving.
- Objective per draw d: `Σ_c β_c^d · Hill(x_c; K_c^d, s_c^d)` (steady state = x
  under normalized weights, DC-201); SAA mean over the FIRST 500 thinned rows
  (deterministic subset, DC-202). Supply the analytic gradient
  (∂Hill/∂x = s·K^s·x^{s−1}/(x^s+K^s)^2, averaged over draws) to SLSQP — better
  convergence, fewer restarts needed, still keep 20 (DC-204).
- Restarts: Dirichlet(1,…,1) over free channels via seeded Generator; keep best
  objective; restart spread = (best − worst_of_converged)/|best|; > 1% ⇒ flag.
- Regret (DC-401): evaluate BOTH allocations under TRUE params with the TRUTH-side
  steady state `a = x/(1−λ)` (BP-D-16):
  `regret = [f_true(x*_true) − f_true(x*_posterior)] / f_true(x*_true)`.
- Determinism (DC-703): fixed draw subset + fixed restart seeds + fixed scipy
  version (locked) ⇒ byte-identical CSVs; the gate test runs the pipeline twice.

## §6 SSOT mechanism (T-408)
- Producers (recovery, holdout, scenarios, gap, diagnostics) each emit a JSON
  side-file under `reports/**/ssot_fragments/<producer>.json` with rows
  `{key, value, unit, tag, produced_by}`. `generate_ssot.py` = collect + sort +
  render; zero analytics (single-writer principle, GB-301).
- Consistency checker: extract numeric literals with adjacent units (a€, %, ×,
  weeks) from README/EXEC_SUMMARY/RECOVERY_REPORT via regex; for each, find a
  matching SSOT key within documented rounding (round-half-even to the printed
  precision); unmatched literal ⇒ error unless whitelisted
  (`config/ssot_whitelist.yaml`, each entry with a justification comment —
  parse-enforced).

## §7 Leak scan (T-008/T-505)
- Pattern subset (CI-safe): (a) the private-drop path literal (from env if set,
  plus the generic pattern `AMBO_PRIVATE_DROP`-adjacent Windows/Unix path strings
  in committed files); (b) email/URL/phone regexes scoped to `data/real_anon/` and
  `reports/ingestion/`; (c) currency-formatted literals inside `*.ipynb` (any
  notebook with output cells also fails via nbstripout expectations).
- Full mode: + blocklist values from `$AMBO_PRIVATE_DROP/blocklist.txt` (one
  distinctive real value per line) scanned across the working tree AND staged
  diff. Findings print `path:line pattern-class sha8(match)` — never the match.
- `--staged` mode diffs `git diff --cached -U0` only (fast pre-commit).

## §8 dbt specifics (P2)
### §8.1 Scaffold
- `profiles.yml` in-repo with relative path `../data/warehouse/ambo.duckdb`
  (dbt-duckdb resolves relative to the profile dir); target `dev` only.
- vars: `layer_r_present: false`, `channel_taxonomy: [search_brand, …, other]`.
  A pytest asserts this list == settings.yaml channels (config duplication is
  unavoidable across languages — so it is *tested*, per the SSOT-violation rule).
### §8.2 Staging
- Layer P sources: three `read_csv_auto` external views with `layer` literals
  'P-SA'/'P-SB'/'P-SC'; unit-neutral renames per BP-D-03; add NULL `clicks`.
- Layer R source wrapped in jinja `{% if var('layer_r_present') %}` union branch.
- `stg_calendar_weekly` from the seed — no recomputation of windows in SQL ever.
### §8.3 Marts
- Pivot `fct_mmm_input` spends via jinja loop over `var('channel_taxonomy')` —
  `coalesce(sum(case when channel = '<c>' then spend end), 0) as spend_<c>`.
- Gapless spine test: recursive/`generate_series` week spine per layer between
  dim_layer min/max, anti-join must be empty.
- AD-042 reconciliation as a singular test comparing mart sum vs
  `read_csv_auto` of the P-SA outcome file (tolerance 1e-6).

## §9 CI mechanics (T-009)
- Jobs: lint / test / dbt / ssot / layer-order / leak. `fetch-depth: 0` on the
  last two (BP-D-13). Cache: uv (`~/.cache/uv` keyed on uv.lock) + pytensor
  compiledir (`~/.pytensor` keyed on pytensor version + runner OS).
- Smoke fit (EB-060): `@pytest.mark.smoke`, S-A first 60 weeks, 1×200/200,
  asserts sampling completes and R-hat finite (NOT small — finiteness only);
  `pytest -m smoke` in the CI test job after the plain suite; locally skipped
  unless `SMOKE=1`. Budget guard: pytest-timeout 900 s on the marker.
- dbt job: `dbt build` with `layer_r_present` from a repo-state check — keep it
  simply `false` until the M4 PR flips the default in `dbt_project.yml` (the PR
  that adds real_anon flips it; CI needs no branching logic).

## §10 Layer-order git checks (T-409)
- First-commit-adding-path: `git log --diff-filter=A --format=%H -- <path>` last
  line (initial add), verify with `--follow` off (paths are stable by design).
- GB-501: for every existing `data/posteriors/R*.parquet` or
  `reports/model/diag_R.md`: `git merge-base --is-ancestor <recovery_commit>
  <artifact_first_commit>` must hold, where recovery_commit = first commit adding
  `reports/recovery/RECOVERY_REPORT.md`.
- GB-502: freeze commit = commit of tag `prior-freeze-v1` (BP-D-07); assert
  (a) tag exists once any R artifact exists; (b) is-ancestor of every R artifact
  commit; (c) `git log <tag>..HEAD -- config/priors_real.yaml` empty; (d) any
  post-tag commit touching `docs/PRIOR_ELICITATION.md` has an append-only diff
  whose added lines fall under a `## Amendment` heading, and an ADR referencing
  it exists in the same commit range.
- Pre-conditions absent (no R artifacts, no tag) ⇒ exit 0 with notice — the
  script is installed from M3 but must not block M0–M3 CI.
- Test strategy: build throwaway repos in tmp dirs inside tests (git init +
  scripted commits) exercising: correct order (pass), fit-before-report (fail),
  post-freeze prior edit (fail), legitimate amendment (pass).
