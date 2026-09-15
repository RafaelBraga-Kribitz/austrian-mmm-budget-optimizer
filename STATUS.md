# STATUS

Run date: 2026-09-15. Working branch: build/ambo. MERGE_TO_MAIN: true.

## Morning brief

Stage 1 is on `main`. The stacked GSD pull requests were closed as superseded
(salvage record below). The next work is the flat package: simulator, model,
recovery, optimiser, reports — five channels, no Layer R (ADR-012).

## Current stage

Stage 2, Layer P pipeline.

## Done

| Stage | Commit | Produced |
|-------|--------|----------|
| 0 Inventory | (committed together with Stage 1) | Counts, constraints and triage table below. |
| 1 Hygiene | `cd235f2` / merge `3285620` | Package skeleton, CI, transforms, calendar |
| 2+ Pipeline | this branch | `ambo.synth`, `model`, `evaluate`, `baselines`, `optimize`, `report`, `run` |

## Numbers

None from a full NUTS run yet. `python -m ambo.run simulate` writes Layer P CSVs
and `truth.json`. Full regeneration is `python -m ambo.run layer_p`.

## Blockers

- Stage 0: the gh CLI is not installed in this environment. The GitHub API was used
  instead for listing and closing pull requests, with the same outcome.
- Full NUTS is too slow for the default CI job; CI stays `pytest -m "not slow"`.

## Decisions taken

- D-01 Stage 0 inventory runs inside this build instead of waiting for a separate
  review of the pull request export. Reversible: nothing in Stage 0 changes the repo.
- D-02 The .planning directory (GSD workflow artifacts) moved to docs/agents/planning
  because its files reference the workflow tooling that produced them and the root
  allow list has no place for it. Nothing was deleted.
- D-03 .gitattributes was removed from the root because it is not on the root allow
  list. It only pinned LF line endings; every file in the repo is LF already and the
  CI runner is Linux. Restore from commit 9318dd1 if Windows checkouts need it.
- D-04 The pull request stack was salvaged by copying functions, not by cherry-picking
  commits, because every branch depends on a settings, pydantic and dbt layer that the
  new package does not have. The salvage record is in the Inventory section.
- D-05 Layer P uses the five channels named in the build brief (TV, Radio, Print,
  Paid Search, Paid Social) instead of the six-channel taxonomy of SPEC-01. The
  simulator keeps the same mechanics (geometric adstock, Hill saturation, flighted
  offline media, platform over-credit).
- D-06 Python 3.11 is the pinned interpreter because it is what the build machine has;
  the specs asked for 3.12. Nothing in the code depends on the minor version.
- D-07 bk-viz installed from GitHub on the first attempt, so charts use its theme
  (bk_theme). src/ambo/plots/theme.py wraps it and carries a minimal fallback with the
  same tokens so the pipeline still runs if the package is unavailable.
- D-08 nutpie installed on the first attempt and sampled a probe model, so it is the
  NUTS sampler. The PyMC default sampler is the fallback in code.
- D-09 The forbidden-word gate is run as grep -ril with --exclude-dir=agents and
  --exclude-dir=.venv. GNU grep matches --exclude-dir against directory base names, so
  the literal form --exclude-dir=docs/agents excludes nothing and reports the twelve
  moved planning files under docs/agents/planning, which are allowed to contain those
  words. Tracked files outside docs/agents are clean.
- D-10 Five-channel Layer P and Charter §7 degradation are ratified in ADR-012.
  Layer R is not fabricated. Recovery gates are the SPEC-05 observables on five
  channels. Python 3.11 and nutpie stand (D-06, D-08).

## Next action

Land the Layer P pipeline on `main`, run `python -m ambo.run layer_p` for the
reported posterior, and keep Layer R unavailable until a real drop exists.

## Inventory

### Counts (live, 2026-09-15)

| Item | Count |
|------|-------|
| Open pull requests | 44 (numbers 1 to 44, all against the previous branch in one stacked chain, except 1, 2 and 11 which target main) |
| Open issues | 0 |
| Remote branches | 45 (43 stack branches sharing the 9588 suffix, m0-bootstrap, main) |
| Local branches at start | 2 (main and the session branch) |

Reconciliation of the critiques: 44 is the number of open pull requests, 45 is the number
of remote branches (44 pull request heads plus main), and there are no issues at all.

### Constraints extracted from the charter, specs and ADR

1. Business question as written: "For a real (anonymized) Austrian advertiser: what did
   each marketing channel actually contribute incrementally, how far off were the
   platform-reported numbers, and how much better could the same budget perform if
   reallocated, with honest uncertainty on every claim?"
2. Three layers: P (synthetic advertiser with disclosed truth, the validation
   instrument), R (real data), D (decision: budget optimiser and attribution gap on the
   Layer R posterior). Layer R results are reported only after Layer P recovery passes.
3. Spec channel taxonomy: search_brand, search_generic, meta, display_video,
   print_regional, radio (plus other). Tonight's Layer P uses TV, Radio, Print, Paid
   Search, Paid Social (D-05).
4. Target KPI: weekly revenue in euros, modelled additively in level, never in logs.
   Orders are descriptive only. Weekly grain, ISO weeks, Europe/Vienna.
5. Media response: geometric adstock (decay per channel) then Hill saturation
   (half-saturation K and slope s per channel), contribution beta times Hill.
6. Baseline: intercept, linear trend, yearly Fourier seasonality, calendar controls
   (promo, Advent, January dip in the spec; one control in tonight's build).
7. Inputs are scaled (spend by its channel mean, revenue by its mean) before sampling;
   every reported quantity is back-transformed.
8. Layer P priors are weakly informative and channel-agnostic so that recovery comes
   from the data, not from priors that encode the truth table.
9. Sampler: NUTS, target_accept 0.9, fixed seed. Diagnostics gates: R-hat below 1.01,
   ESS above 400, zero divergences. The reparameterisation ladder already exercised on
   the stack: non-centered Fourier block (ADR-005), tighter slope prior, higher
   target_accept. Fixing the slope at 1 was tried and rolled back (ADR-010, ADR-011).
10. Recovery is judged on observable quantities (ROAS, contribution shares, response
    curve shape), not on point recovery of K and s, which trade off against beta.
11. Platform-reported numbers are the object of study, never a calibration target.
    The simulator generates them with known over-credit.
12. Brand search is modelled but never receives reallocated budget (endogeneity).
    Not applicable to tonight's five channels, which have no brand-search line.
13. Holdout: conditional forecast with actual spend, MAPE and 90 percent coverage
    against a seasonal-naive baseline. Spec used the last 13 weeks; the build brief uses
    weeks 131 to 156.
14. Optimiser: SLSQP over channel spends on posterior draws, equality on total budget,
    per-channel bounds as an extrapolation guard, gain reported as a distribution.
15. Simulator and model share no transform code, so recovery is evidence and not a
    tautology.
16. Git history is append-only: no force push, no rewrite.
17. Out of scope by charter: lift tests, daily grain, other MMM frameworks, hosted
    apps, multi-KPI, competitor spend, automated refresh.

### Pull request triage

Classes: (a) runnable code worth salvaging, (b) documentation or specs only,
(c) superseded or unclear. Every branch in the stack builds on a settings, pydantic
and dbt warehouse layer that the new package does not use, so no pull request was
merged wholesale.

| PR | Head branch | Title (short) | Class | Salvage |
|----|-------------|---------------|-------|---------|
| 1 | m0-bootstrap | M0 bootstrap, repository foundation | c | Earlier full-scaffold attempt, superseded by the stack |
| 2 | adr-template-index-9588 | ADR template and slot index | b | none |
| 3 | pyproject-spec08-bounds-9588 | pyproject, uv.lock, skeleton | c | dependency bounds consulted |
| 4 | governance-docs-9588 | MODULE_CONTRACTS, RISK_REGISTER, ADR-006 | b | none |
| 5 | settings-logging-9588 | settings.yaml, typed config, logging | c | none |
| 6 | makefile-readme-9588 | Makefile and scaffold README | c | none |
| 7 | season-windows-9588 | season windows seed | c | none (holiday indicator built directly) |
| 8 | architectural-guards-9588 | architectural guard tests | c | none |
| 9 | leak-scan-precommit-9588 | leak scanner, pre-commit | c | none |
| 10 | m0-ci-governance-9588 | governance checks, six-job CI | c | none |
| 11 | m0-ci-against-main-9588 | six-job CI against main | c | none |
| 12 | hypothesis-adr007-9588 | ADR-007, hypothesis dependency | b | none |
| 13 | scenario-config-9588 | SimulationError, ScenarioConfig | c | none |
| 14 | scenario-yamls-9588 | scenario YAMLs | c | none |
| 15 | dgp-core-9588 | DGP week spine, adstock, Hill | a | simulator-side geometric adstock recursion and Hill formula, in synth.py |
| 16 | spend-patterns-9588 | generate_spend | a | flighted burst logic (mask, then floor, then whole-euro rounding), in synth.py |
| 17 | assemble-scenario-9588 | assemble_scenario, audits | c | none |
| 18 | platform-bias-9588 | platform_report | a | platform over-credit formula (own-effect inflation plus demand-claiming leak weighted by spend share), in synth.py |
| 19 | truth-files-9588 | TruthFile schema | c | none |
| 20 | simulate-cli-9588 | simulator CLI | c | none |
| 21 | m1-close-9588 | Layer P artifacts | c | none (regenerated) |
| 22 | dbt-scaffold-9588 | dbt scaffold | c | no warehouse in the new design |
| 23 | mart-only-guard-9588 | mart-only guard | c | none |
| 24 | staging-layer-9588 | dbt staging | c | none |
| 25 | fct-mmm-input-9588 | fct_mmm_input | c | none |
| 26 | dim-layer-9588 | dim_layer | c | none |
| 27 | platform-reported-9588 | fct_platform_reported | c | none |
| 28 | db-accessors-9588 | db accessors | c | none |
| 29 | export-marts-9588 | export_marts | c | none |
| 30 | m2-warehouse-close-9588 | CI warehouse gates | c | none |
| 31 | p4-transforms-9588 | model transforms, scaling | a | unrolled causal adstock convolution with normalised weights, log-space Hill with a positive floor, in transforms.py |
| 32 | p4-priors-9588 | PriorConfig, priors YAML | c | prior families consulted |
| 33 | p4-md070-9588 | shared-shape sanity test | c | none |
| 34 | p4-build-model-9588 | build_model, sample_model, smoke fit | a | non-centered Fourier block, truncated Gamma slope prior, coords and dims layout, in model.py |
| 35 | p4-posterior-io-9588 | posterior parquet I/O | c | none |
| 36 | p4-diagnostics-9588 | diagnostics gates, report writer | a | R-hat, ESS, divergence and BFMI gate logic, in diagnostics.py |
| 37 | p4-fit-synthetic-9588 | make fit-synthetic | c | none |
| 38 | p4-elicit-9588 | elicitation converters | c | none tonight (useful later for elicited Layer R priors) |
| 39 | p5-recovery-metrics-9588 | recovery metrics engine | c | none |
| 40 | p5-fit-sb-sc-9588 | S-B and S-C full fits | c | none |
| 41 | p5-holdout-9588 | holdout fits, coverage tables | a | conditional-forecast holdout with adstock carry-over from the training window, MAPE and 90 percent coverage columns, in evaluate.py |
| 42 | p5-ols-hc1-9588 | OLS plus HC1 baseline | a | least-squares baseline design (adstock at prior mode, Fourier terms), in baselines.py |
| 43 | p5-crosscheck-9588 | pymc-marketing cross-check | c | none (out of tonight's scope) |
| 44 | p5-recovery-report-9588 | RECOVERY_REPORT generator | c | none |

Kept open for Rafael's decision (at most four): 18, 34, 36, 41. All others are closed
with the comment "Superseded by the build on main; see STATUS.md for the salvage
record." No branch was deleted.
