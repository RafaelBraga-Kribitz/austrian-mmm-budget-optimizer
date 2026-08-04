# SPEC-06 — Decision Layer: Budget Optimizer & Attribution Gap

Answers Q3 and Q4. Requirement IDs: `DC-xxx`. Code in `src/ambo/decide/`
(`optimizer.py`, `attribution_gap.py`, `scenarios.py`). Consumes committed thinned
posteriors (MD-051) and marts — never refits.

---

## 1. The decision being modeled

Given the fitted Layer R model: reallocate the SAME total weekly budget B across
channels to maximize expected media contribution, under constraints that keep the
answer inside what the data can support.

## 2. Optimizer formulation (implement exactly)

- DC-201: Objective: maximize
  `E_posterior [ Σ_c β_c · Hill(x_c^ss; K_c, s_c) ]`
  where `x_c^ss` is the steady-state adstocked spend of a constant weekly allocation
  x_c (with normalized adstock weights, steady state = x_c itself — state this
  simplification in the artifact caption: "constant-spend steady state").
- DC-202: Estimation: Sample-Average Approximation over D = 500 posterior draws
  (thinned file, first 500 rows, deterministic). One optimization on the averaged
  objective; uncertainty of the OUTCOME reported by evaluating the optimal x* under
  all 1000 draws (mean + 90% HDI of expected contribution).
- DC-203: Constraints:
  (a) Σ_c x_c = B (equality);
  (b) 0 ≤ x_c ≤ 1.3 × max observed weekly spend of channel c (extrapolation guard —
  hard bound, visible in every output);
  (c) `search_brand` FIXED at its historical mean (Charter R-4 / AGENTS T-7: modeled
  but not reallocatable);
  (d) offline channels (print_regional, radio) reallocate in weekly-equivalent terms
  with a caption noting real-world flighting granularity.
- DC-204: Solver: `scipy.optimize.minimize(method='SLSQP')`, 20 restarts from seeded
  Dirichlet-random feasible points, keep best; convergence report (restart spread ≤
  1% of objective, else warn in artifact).
- DC-205: Budget scenarios: B ∈ {0.8, 1.0, 1.2} × historical mean weekly budget →
  `exports/allocation_scenarios.csv`: per scenario × channel: historical share,
  optimal share, spend a€, expected contribution mean + HDI, binding constraints
  flags.

## 3. Headline gain metric (Q3)

- DC-301: `expected_gain_pct` = (E[contribution at x*_B=1.0] − E[contribution at
  historical mean allocation]) / E[total revenue] × 100, with 90% HDI over draws;
  plus `expected_gain_aeur_annual` = gain/week × 52. Both to SSOT (MODELED).
- DC-302: Caption (from `captions.py`, mandatory on every artifact showing the gain):
  "In-sample counterfactual under the fitted model; assumes response curves hold and
  competitors do not react. Guard rails: no channel is pushed beyond 1.3× its
  historically observed spend."

## 4. Optimizer recovery test (part of M6 gates, runs on Layer P)

- DC-401: On S-A: run the optimizer on (i) the true parameters and (ii) the
  posterior. Gates: allocation cosine similarity ≥ 0.90 between (i) and (ii); regret
  = (true-optimal contribution − contribution of posterior-optimal allocation
  evaluated under TRUE params) ≤ 5% of true-optimal. On S-B: cosine ≥ 0.80, regret
  ≤ 10%. → RECOVERY_REPORT addendum + SSOT (`optimizer_regret_sb`).

## 5. Attribution-gap module (Q4)

- DC-501: For every channel with platform reporting: `platform_roas` =
  Σ platform_conv_value / Σ spend (masked units cancel); `mmm_roas` = MD-081
  posterior. Output per channel: platform ROAS, MMM ROAS (mean + HDI),
  `overcredit_ratio` = platform/MMM-median, P(platform > MMM).
- DC-502: Layer P check: on S-B the recovered overcredit ratios must reproduce the
  ORDERING of the simulated φ_c (SIM-060): display_video > meta > search_generic >
  search_brand. This gate makes the Layer R gap table credible.
- DC-503: Layer R output: `exports/attribution_gap.csv` + chart
  `reports/decide/dc_attribution_gap.png` (dumbbell plot: platform dot vs MMM dot +
  HDI whisker, per channel). Whatever the real result is, it ships — including
  channels where platforms UNDER-credit (possible for offline-assisted channels).
- DC-504: One interpretation paragraph written from the marketing chair (why platform
  measurement over-credits: view-through counting, brand-search claiming, last-click
  position) — ≥ 500 chars, referenced to the numbers, no vendor-bashing tone.

## 6. What-if table (the Power BI feed)

- DC-601: `scenarios.py` also emits a marginal-ROAS ladder: for each reallocatable
  channel, expected contribution change for ±€500/week around current spend
  (posterior mean + HDI) — the "where does the next euro go" table that names the
  project. SSOT: `next_euro_best_channel`, `next_euro_marginal_roas`.

## 7. Gates (M6 exit)

- DC-701: DC-401 optimizer-recovery gates green.
- DC-702: DC-502 ordering gate green.
- DC-703: Determinism: two runs → identical CSVs (seeded restarts, fixed draw
  subset).
- DC-704: Constraint audit test: optimal allocations respect bounds exactly;
  search_brand unchanged; Σ = B to 1e-6.
- DC-705: Every § artifact exists and regenerates via `make decide` from committed
  posteriors (no sampling).
