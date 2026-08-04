# PROJECT CHARTER — Austrian MMM & Budget Optimizer (AMBO)

**Repo name:** `austrian-mmm-budget-optimizer`
**Python package name:** `ambo`
**Author:** Rafael Braga-Kribitz, Seiersberg-Pirka, Austria
**Status:** Charter v1.0 — 2026-07-18
**Authority:** Single Source of Truth for goals, scope, acceptance. Charter beats specs;
specs beat code; deviations require ADRs (`docs/SPEC-09_governance_quality.md`).

---

## 1. The business problem (read this first)

Every Austrian advertiser above ~€200k/year media spend faces the same question:
**where should the next euro go?** Since iOS14 and the death of third-party cookies,
the platform dashboards that used to answer it (Google Ads, Meta Ads Manager, GA4
last-click) systematically over-credit their own channels and cannot see offline media
at all. Marketing Mix Modeling — estimating each channel's *incremental* contribution
from spend and outcome time series — is the industry's answer, and almost nobody in
the Austrian mid-market or its agencies can build one.

**Headline question:**

> *For a real (anonymized) Austrian advertiser: what did each marketing channel
> actually contribute incrementally, how far off were the platform-reported numbers,
> and how much better could the same budget perform if reallocated — with honest
> uncertainty on every claim?*

**The credibility architecture (three layers — the project's core idea):**

| Layer | Data | Purpose |
|-------|------|---------|
| P — Proof | Synthetic advertiser with **known ground truth** (disclosed, SPEC-01) | Prove the model recovers known ROAS/adstock/saturation before anyone trusts it on real data |
| R — Reality | **Real agency data**, anonymized per protocol (SPEC-02) | The actual business answer, with real-world messiness and short-data honesty |
| D — Decision | Posterior of Layer R | Budget optimizer + attribution-gap analysis, in (anonymized) euros |

Synthetic data here is not a stand-in for missing real data; it is a **validation
instrument** — the model must pass Layer P's recovery gates before Layer R results are
reported at all.

### 1.1 The four analytical questions (Q1–Q4)

| ID | Question | Answered by |
|----|----------|-------------|
| Q1 | Does the model recover known truth? (ROAS, adstock half-lives, saturation, optimal allocation — within stated tolerances, incl. a zero-effect channel it must NOT hallucinate) | SPEC-05 recovery suite on SPEC-01 scenarios |
| Q2 | What drives the real client's revenue: incremental ROAS and response curves per channel, with credible intervals? | SPEC-04 model on SPEC-02 data |
| Q3 | At the same total budget, what is the optimal allocation and the expected contribution gain vs. the historical allocation? | SPEC-06 optimizer |
| Q4 | How large is the gap between platform-reported ROAS and MMM incremental ROAS, per channel? | SPEC-06 attribution-gap module |

### 1.2 The audience

1. **Primary:** marketing leaders and analytics hiring managers — Austrian agencies,
   in-house marketing teams (retail, e-commerce, telco, banking), consultancies.
   These readers know adstock and saturation by *effect*, not by name; every artifact
   must be readable at that level.
2. **Secondary:** technical reviewers (the PyMC model, priors, and diagnostics must
   survive expert scrutiny).

This is the portfolio's **marketing-domain flagship**: the prior-elicitation documents
(SPEC-04 §6) are written from agency experience and are as much a deliverable as the
model itself.

---

## 2. Scope

### 2.1 In scope

1. Ground-truth simulator: a documented data-generating process for a fictional
   Austrian outdoor-gear e-tailer ("AlpenTrek GmbH", Graz), 3 scenarios (SPEC-01).
2. Agency-data pipeline: permission gate, PII scrub, dual-factor rescaling
   anonymization, standardized schema, validation (SPEC-02).
3. DuckDB + dbt warehouse, weekly grain, two modeling matrices (SPEC-03).
4. Bayesian MMM in raw PyMC (geometric adstock + Hill saturation + seasonality +
   promo), elicited priors, full diagnostics; `pymc-marketing` as cross-check only
   (SPEC-04).
5. Validation: recovery gates per scenario, false-positive control, holdout, prior
   sensitivity, OLS-baseline comparison (SPEC-05).
6. Decision layer: constrained budget optimizer over posterior draws (with
   extrapolation guards) + attribution-gap analysis (SPEC-06).
7. Reporting: exec summary, exec charts, Power BI on exports, SSOT (SPEC-07).
8. Engineering: uv/Python 3.12, Makefile, pytest, ruff, CI with smoke-fit (SPEC-08).
   Light governance incl. prior-freeze enforcement (SPEC-09).

### 2.2 Explicitly OUT of scope (do not build)

- O-1: Geo-experiments / lift tests / MMM calibration against experiments. One line in
  Future work ("the correct next step for a real engagement").
- O-2: Daily-grain MMM, intra-week effects, auction/bid modeling.
- O-3: Additional MMM frameworks (Robyn, Meridian, lightweight_mmm) or model-averaging.
  Exactly two implementations exist: raw PyMC (primary) + pymc-marketing (cross-check).
- O-4: Customer-level modeling (CLV, churn), funnel analytics, creative analysis.
- O-5: Hosted apps. The what-if deliverable is Power BI + exported scenario tables.
- O-6: Multi-KPI modeling (revenue only; orders reported descriptively).
- O-7: Automated data refresh crons — this project has no live feed. CI is the only
  automation.
- O-8: Competitor spend estimation, share-of-voice data purchases.

### 2.3 Grain and windows

- Grain: **ISO weeks** (Mon–Sun, Europe/Vienna civil dates). Everything weekly.
- Layer P: 156 weeks per scenario (S-C: 78) — synthetic dates 2022-W01 … 2024-W52.
- Layer R: whatever the agency data covers (expected 52–104 weeks) — exact window
  documented at intake (SPEC-02 §5) and reported with every Layer R result.

---

## 3. Epistemic framework

| Tag | Meaning | Examples |
|-----|---------|----------|
| GROUND-TRUTH | Synthetic data whose generating parameters are disclosed in-repo | Layer P datasets + `truth.json` |
| REAL-ANON | Real agency data transformed by the SPEC-02 anonymization (masked units: **a€**) | Layer R spend/revenue series |
| MODELED | Posterior quantities, recovery statistics, forecasts, optimizer outputs | ROAS posteriors, allocation gains |
| CALIBRATED | Judgment-based inputs with documented rationale | All priors; reconstructed promo calendar |

Rules:

- E-1: Every headline number carries its tag in README/exec summary.
- E-2: Layer R results are published ONLY if Layer P gates passed (SPEC-05 §2) — this
  ordering is a CI-checked fact, not a promise (SPEC-09 §5).
- E-3: **Prior freeze:** `config/priors_real.yaml` (Layer R priors + rationales) is
  committed BEFORE any Layer R fit artifact exists; enforced by git-ancestry check
  (SPEC-09 §5). Priors are marketing judgments — they must demonstrably precede results.
- E-4: `reports/NUMERIC_SSOT.md` is generated only by `scripts/generate_ssot.py`; it is
  the sole source for numbers in README/exec summary (CI-gated).
- E-5: Anonymized euros are always written **a€** and every Layer R artifact carries:
  "Values in anonymized euros (a€): real client data rescaled by undisclosed factors;
  ratios and shapes are preserved, absolute levels are masked." (single caption source,
  SPEC-07 §7).

---

## 4. Deliverables & Definition of Done

| # | Deliverable | Acceptance criterion |
|---|-------------|----------------------|
| DL-1 | Reproducible pipeline | Fresh clone + `make setup && make all` reproduces every Layer P artifact bit-for-bit-in-tolerance (MCMC tolerance doctrine, SPEC-05 §7) without any private inputs; Layer R artifacts reproduce given the private data drop (SPEC-02 §3) |
| DL-2 | Answer to Q1 | `reports/recovery/RECOVERY_REPORT.md` with all SPEC-05 §3 gates green, incl. the zero-effect channel test |
| DL-3 | Answer to Q2 | Layer R posterior report: ROAS table with 90% HDIs, response curves, contribution decomposition (SPEC-04 §8) |
| DL-4 | Answer to Q3 | Optimizer output: optimal vs. historical allocation, expected gain in a€ and %, extrapolation guards visibly active (SPEC-06 §3) |
| DL-5 | Answer to Q4 | Attribution-gap table + chart: platform ROAS vs MMM ROAS per channel (SPEC-06 §5) |
| DL-6 | Priors as deliverable | `docs/PRIOR_ELICITATION.md` — every prior with a ≥100-character marketing rationale (SPEC-04 §6), frozen pre-fit |
| DL-7 | Dashboard | Power BI `dashboards/ambo.pbix` per SPEC-07 §4 + screenshots |
| DL-8 | Quality | `make test` green; ruff+mypy clean; CI green (incl. smoke-fit); coverage ≥ 80% of `src/` |
| DL-9 | Honesty | `LIMITATIONS.md` ≥ SPEC-09 §6 list; anonymization protocol published (without secrets); no absolute real € anywhere |
| DL-10 | README | Leads with the recovery result and the Layer R answer, per SPEC-07 §6 |

---

## 5. Milestones

| Milestone | Content | Exit gate |
|-----------|---------|-----------|
| M0 | Bootstrap per SPEC-08 | make setup/lint/test green + CI |
| M1 | Simulator + 3 scenarios + truth files | SPEC-01 §7 gates |
| M2 | Raw-PyMC model, fit on S-A, diagnostics clean | SPEC-04 §7 gates on S-A |
| M3 | Full recovery suite (all scenarios), OLS baseline, pymc-marketing cross-check | SPEC-05 §3–§6 gates; RECOVERY_REPORT.md |
| M4 | Agency data intake: permission confirmed, anonymization executed, validation | SPEC-02 §6 gates; **then freeze `config/priors_real.yaml` + `docs/PRIOR_ELICITATION.md`** |
| M5 | Layer R fit + diagnostics + prior-sensitivity + short-data analysis | SPEC-04 §7 on Layer R; SPEC-05 §5 sensitivity artifacts |
| M6 | Decision layer: optimizer + attribution gap | SPEC-06 §7 gates |
| M7 | Reporting, dashboard, README, LIMITATIONS | DL-1…DL-10 |

Effort budget: M0 0.5d, M1 1.5d, M2 2d, M3 2.5d, M4 1.5d (human-heavy), M5 2d, M6 2d,
M7 2d. >2× budget ⇒ stop, ADR.

Build-order rationale: the model is proven on synthetic truth (M2–M3) BEFORE it ever
sees real data (M5) — reviewers can verify this order in git history; it is the
project's argument.

---

## 6. Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-1 | Client permission falls through | Medium | Layer R dies | Charter §7 degradation path: project ships as Layers P+D on synthetic with full recovery story; README framing pre-written for both cases (SPEC-07 §6.1) |
| R-2 | Adstock/saturation weakly identified on 52–104 real weeks | High | Wide posteriors | That IS the finding: informative-priors-vs-flat comparison (SPEC-05 §5) becomes the centerpiece; never hidden |
| R-3 | Collinearity: spend planned on the demand calendar | Certain | Confounded estimates | S-B scenario tests exactly this; seasonality controls; honesty in LIMITATIONS |
| R-4 | Brand-search endogeneity (brand search is partly an outcome of other media) | High | Over-credited brand search | `search_brand` is modeled but EXCLUDED from optimizer reallocation advice (SPEC-06 §3.6); trap documented |
| R-5 | MCMC non-reproducibility across platforms | Certain | Golden tests break | Tolerance-band doctrine (SPEC-05 §7), committed thinned posteriors for report regeneration |
| R-6 | Anonymization leak (secret factors, client identity, absolute €) | Low | Serious | SPEC-02 §4 secrets protocol + CI leak-scan (SPEC-09 §5); factors never touch the repo or git history |
| R-7 | Divergences / sampler pathologies | Medium | Blocked fits | SPEC-04 §7 reparameterization ladder, prescribed in order |
| R-8 | Scope creep (more frameworks, daily grain, lift tests) | High | Never ships | §2.2 + AGENTS A-3 |
| R-9 | Promo calendar reconstruction is imperfect memory | Certain | Omitted-variable bias | Tagged CALIBRATED; sensitivity fit without promo regressor (SPEC-05 §5.4) |

## 7. Degradation path (if Layer R becomes impossible)

The repo remains shippable: Layers P + D on scenario S-B become the showcase
("a validated MMM + optimizer, demonstrated end-to-end on disclosed ground truth"),
the attribution-gap module runs on simulated platform-reporting bias (SPEC-01 §6
generates platform-attributed conversions WITH known over-credit), and the README uses
its alternate framing (SPEC-07 §6.1). Decide via ADR by end of M4, not later.

---

## 8. Document map (read order)

| Order | File | Contents |
|-------|------|----------|
| 1 | `PROJECT_CHARTER.md` | This file |
| 2 | `AGENTS.md` | Agent rules, build order, traps |
| 3 | `docs/SPEC-01_ground_truth_simulator.md` | Exact DGP, parameters, scenarios, truth files |
| 4 | `docs/SPEC-02_agency_data_pipeline.md` | Permission, PII scrub, anonymization recipe, schema, gates |
| 5 | `docs/SPEC-03_data_model.md` | DuckDB/dbt, tables, tests |
| 6 | `docs/SPEC-04_mmm_model.md` | Model math, priors & elicitation, sampling, diagnostics |
| 7 | `docs/SPEC-05_validation_recovery.md` | Recovery gates, sensitivity, baselines, MCMC tolerance doctrine |
| 8 | `docs/SPEC-06_decision_layer.md` | Optimizer, extrapolation guards, attribution gap |
| 9 | `docs/SPEC-07_reporting_dashboard.md` | Exec artifacts, Power BI, README structure, captions |
| 10 | `docs/SPEC-08_engineering.md` | Layout, deps, Makefile, CI (smoke-fit) |
| 11 | `docs/SPEC-09_governance_quality.md` | Tags, SSOT, ADRs, prior-freeze & leak-scan enforcement |

## 9. Glossary

| Term | Definition |
|------|-----------|
| MMM | Marketing Mix Modeling: regression-based estimation of channels' incremental contribution to an outcome from aggregate time series |
| Adstock | Carryover of advertising effect over time; geometric decay rate λ per channel; half-life = ln(0.5)/ln(λ) weeks |
| Saturation / Hill | Diminishing returns: Hill(a) = aˢ/(aˢ+Kˢ); K = half-saturation spend, s = shape |
| ROAS | Return on ad spend = incremental revenue ÷ spend. "Platform ROAS" = what dashboards claim; "MMM ROAS" = model-estimated incremental |
| Contribution | Revenue attributable to a channel in the model decomposition, a€/week |
| Response curve | Expected contribution vs. spend level, from the fitted Hill × β |
| a€ | Anonymized euros (Charter E-5) |
| HDI | Highest-density interval of a posterior (we use 90%) |
| Flighting | On/off spend pattern (bursts), typical for print/radio |
| SSOT | `reports/NUMERIC_SSOT.md` |

## 10. Charter change log

| Date | Version | Change |
|------|---------|--------|
| 2026-07-18 | 1.0 | Initial charter |
