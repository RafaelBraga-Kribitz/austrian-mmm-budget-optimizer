# STATUS

Run date: 2026-09-15. Working branch: build/ambo. MERGE_TO_MAIN: true.

## Morning brief

Written 2026-09-15 at the end of the run. Six stages done; nothing is blocked.

**Where the code is.** main holds Stages 1 and 2: commit 3285620 (merge of cd235f2,
hygiene, package skeleton and CI) and commit 3768d7c (merge of 6218abd, Layer P with
parameter recovery). build/ambo holds, on top of that, bbf6b2a (Stage 3, Layer R),
7bbccf5 (Stage 4, Layer D), 90b0658 (Stage 5, rendered README and German summary),
081b14b (Stage 6, executed notebook), 6ef121e (this brief) and one fix commit for
the CI smoke profile. Draft pull request 46 (build/ambo into main) is the review
vehicle. Ten commits in total, one human identity, no history rewritten, no branch
deleted.

**Three charts to open first.**

1. reports/layer_p/parameter_recovery.png: true parameter values (orange crosses)
   against the model's 90 percent intervals, 26 of 28 inside.
2. reports/layer_p/attribution_gap.png: platform-reported share against true
   incremental share; Paid Search overstated by 24.8 points, TV understated by 28.3.
3. reports/layer_r/channel_contributions.png: the README headline chart, share of
   revenue per channel on the public demo data with intervals.

Then reports/layer_d/reallocation_gain.png, the gain distribution with its 10th
percentile marked.

**Headline numbers** (full table under Numbers, each with its artifact path):

- Layer P recovery: 26 of 28 true parameters inside their 90 percent interval;
  4 of 5 channel revenue shares covered (reports/layer_p/parameter_recovery.csv,
  contribution_recovery.csv).
- Layer P attribution gap: Paid Search +24.8 pp, Paid Social +17.5 pp, TV -28.3 pp
  (reports/layer_p/attribution_gap.csv).
- Layer P holdout, 26 weeks: MMM MAPE 3.0 percent, ridge 4.7, seasonal naive 9.6;
  coverage 85, 92, 92 percent (reports/layer_p/holdout_metrics.csv).
- Layer R: Media channel 1 drives 22.1 percent of revenue (18.1 to 28.1), channel 2
  7.1 percent (6.6 to 7.7); holdout MAPE 4.4 percent against 7.5 (ridge) and 19.3
  (naive) (reports/layer_r/channel_contributions.csv, holdout_metrics.csv).
- Layer D: same budget reallocated gains a median 2.5 percent of media contribution,
  10th percentile -0.8 percent, so the rule says hold; 25 percent more budget gains a
  median 23.3 percent, 92 percent of it to channel 1, and the rule says recommend
  (reports/layer_d/decision.json, next_200k.md).
- Sampler gates: every reported fit passes R-hat below 1.01, ESS above 400, zero
  divergences, after the recorded ladder (reports/layer_p/diagnostics.json,
  holdout_diagnostics.json, reports/layer_r/*.json).

**Blockers.** None that stopped a stage. Two things to know: the gh CLI was absent and
the GitHub API was used instead; and a parallel build appeared during the night (pull
request 45, branch layer-p-pipeline-9588, opened 17:59 by a second tooling session on
top of the Stage 1 skeleton). It is a competing Layer P implementation, reports its own
recovery gates as red, and now conflicts with main. It was left untouched.

**Decisions for Rafael today, ranked by impact.**

1. Merge build/ambo into main (pull request 46), or ask for changes first. Everything
   in it regenerates from three commands; the README numbers test guards the text.
2. Pull request 45, the parallel build: close it, or cherry-pick anything you prefer
   from it (its calendar dummies and normalised adstock are the main differences), and
   stop that session if it is still running. Two Layer P implementations on one repo
   will confuse a reader.
3. Layer R data source: the pymc-marketing example file has two unnamed, index-scaled
   channels, which keeps Layer D in shares and ratios. Robyn's dt_simulated_weekly
   (five named channels, money units) was reachable at
   github.com/facebookexperimental/Robyn/main/python/src/robyn/tutorials/resources/
   and would make the decision layer read in money; swapping it in is a config plus
   loader change. Your anonymised agency data would be the real answer.
4. Breakeven ROAS: the 40 percent contribution margin in src/ambo/configs/layer_r.yaml
   is a placeholder assumption. Set the real margin; the rule and the README rerender.
5. Kept pull requests 18 (platform over-credit) and 34 (model builder): their functions
   are salvaged into the package, so they can be closed; 36 and 41 were closed at the
   end of the run to keep four open once 45 and 46 existed.

**One paragraph to read aloud.** This project builds a marketing mix model that
estimates what each advertising channel really adds to revenue, then turns that into a
budget recommendation with honest uncertainty. Before trusting it on any advertiser's
data, I made it pass a test where the answer is known: on a synthetic advertiser with
five channels, it recovered 26 of 28 true parameters inside its stated intervals and
showed how a platform dashboard overstates paid search by about 25 points while giving
TV no credit at all. Run on public demo data, it beats a seasonal forecast and a ridge
regression on out-of-sample error, and its optimiser says the current budget split is
close to optimal, with a 15 percent chance a reallocation would lose money, so the
recommendation is to hold at the same budget and to put most of any extra budget into
the stronger channel. The next step is to run the same pipeline on real client data.

## Current stage

All six stages done. Awaiting Rafael's review of pull request 46.

## Done

| Stage | Commit | Produced |
|-------|--------|----------|
| 0 Inventory | cd235f2 (with Stage 1) | Counts, constraints and triage table below. |
| 1 Hygiene | cd235f2, merged to main in 3285620 | Root cleaned, docs moved, LICENSE, package skeleton with transforms and calendar, CI, uv lock; 40 pull requests closed, 4 kept open. |
| 2 Layer P | 6218abd, merged to main in 3768d7c | Synthetic advertiser with disclosed truth, PyMC model, parameter and contribution recovery, attribution gap, holdout against two baselines, all under reports/layer_p. |
| 3 Layer R | bbf6b2a (build/ambo) | Same model on the pymc-marketing example dataset: channel contributions, response curves, holdout, diagnostics, posterior draws under reports/layer_r. |
| 4 Layer D | 7bbccf5 (build/ambo) | Budget optimiser on the Layer R posterior: reallocation table, gain distribution, decision rule, next-budget note under reports/layer_d. |
| 5 README | 90b0658 (build/ambo) | README.md and docs/summary_de.md rendered from reports/ by scripts; numbers test in tests/test_readme_numbers.py. |
| 6 Notebook | 081b14b (build/ambo) | notebooks/01_walkthrough.ipynb executed on the tiny config with outputs saved; CI runs it. |

## Numbers

Every number below is read from the named artifact; none is typed from memory.

Layer P, synthetic advertiser with known truth (156 weeks, 5 channels):

| Metric | Value | Artifact |
|--------|-------|----------|
| True parameters inside their 90 percent interval | 26 of 28 | reports/layer_p/parameter_recovery.csv |
| Misses | Paid Search decay (true 0.15, interval 0.17 to 0.52); TV slope (true 1.40, interval 0.69 to 1.29) | same |
| Channels whose true revenue share is inside the interval | 4 of 5 (TV: true 9.5 percent, interval 9.7 to 11.4) | reports/layer_p/contribution_recovery.csv |
| Platform-reported share minus true incremental share | Paid Search +24.8 pp (60.8 vs 36.0); Paid Social +17.5 pp; TV -28.3 pp; Print -7.1 pp; Radio -6.8 pp | reports/layer_p/attribution_gap.csv |
| Full-fit diagnostics | max R-hat 1.009, min ESS 436, 0 divergences, BFMI 0.89; reached at target_accept 0.99 after 14 divergences at 0.9 and 1 at 0.95 | reports/layer_p/diagnostics.json |
| Holdout, weeks 131 to 156 | MMM MAPE 3.0 percent, coverage 85 percent; ridge 4.7 percent, 92 percent; seasonal naive 9.6 percent, 92 percent. Holdout fit gates passed at target_accept 0.99 with 2000 draws after 13 divergences at 0.9, an ESS shortfall at 0.95 and 13 divergences again at 0.95 with 2000 draws | reports/layer_p/holdout_metrics.csv |
| Wall time of the full run | 891.5 seconds (14.9 minutes) for both fits and all ladder attempts, nutpie, 2 chains | reports/layer_p/run_info.json |

Layer R, public demo data (pymc-marketing example, 179 weeks, 2 channels):

| Metric | Value | Artifact |
|--------|-------|----------|
| Share of revenue, Media channel 1 | 22.1 percent (18.1 to 28.1) | reports/layer_r/channel_contributions.csv |
| Share of revenue, Media channel 2 | 7.1 percent (6.6 to 7.7) | same |
| ROAS in the file's index units (revenue per unit of spend) | channel 1: 3783 (3089 to 4798); channel 2: 2322 (2160 to 2505) | same |
| Full-fit diagnostics | max R-hat 1.006, min ESS 441, 0 divergences, first attempt | reports/layer_r/diagnostics.json |
| Holdout, last 26 weeks | MMM MAPE 4.4 percent, coverage 85 percent; ridge 7.5 percent, 92 percent; seasonal naive 19.3 percent, 96 percent | reports/layer_r/holdout_metrics.csv |

Layer D, decision on the Layer R posterior (500 draws, 200 per-draw optimisations):

| Metric | Value | Artifact |
|--------|-------|----------|
| Same total budget: gain from reallocation | median +2.5 percent of current media contribution, 10th percentile -0.8 percent, probability of a loss 14.6 percent; verdict: hold (10th percentile negative) | reports/layer_d/decision.json |
| Same total budget: moves | Media channel 1 +23 percent, Media channel 2 -45 percent of current weekly spend | reports/layer_d/reallocation_table.csv |
| Budget plus 25 percent | median gain +23.3 percent, 10th percentile +18.9 percent, no draw loses; 92 percent of the extra goes to channel 1; probability channel 1 is not the best marginal channel 43.6 percent; verdict: recommend | reports/layer_d/next_200k.md |
| Breakeven ROAS | 2.50 at a contribution margin of 40 percent (assumption in src/ambo/configs/layer_r.yaml) | reports/layer_d/decision.json |

## Blockers

- None that stop a stage. The gh CLI is absent (Stage 0); the GitHub API was used
  instead with the same outcome.

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
- D-10 The first Layer P probe gave the always-on channels nearly flat spend, which left
  their curves unidentified (45 divergences, ESS 150). The generator now gives Paid
  Search and Paid Social seasonal swings and campaign pulses, as real accounts have.
- D-11 The model's adstock is the truncated recursion (13 lags, unnormalised weights),
  the same definition the generator uses, so half-saturation and effect size are
  comparable one to one in the recovery chart. SPEC-04's normalised-weight mismatch
  was dropped for that reason.
- D-12 The Hill slope prior is LogNormal(0, 0.5) instead of SPEC-04's truncated Gamma:
  smoother geometry for the sampler, no hard boundary, same weakly informative range.
- D-13 Sampler ladder, recorded in every diagnostics.json: divergences or a high R-hat
  raise target_accept to 0.95 and then 0.99; too few effective draws double the draws
  at the same rung; the best attempt is kept if none passes. The Layer P full fit
  needed the 0.99 rung (14 divergences at 0.9, 1 at 0.95, 0 at 0.99). MD-050's
  target_accept of 0.9 therefore does not hold on this data.
- D-14 Holdout is weeks 131 to 156 (26 weeks) as the build brief asks, not the 13-week
  protocol of SPEC-05.
- D-15 Layer R uses the pymc-marketing example file because it was reachable; Robyn's
  dt_simulated_weekly (five named channels, money units) is the alternative and was
  also reachable at
  github.com/facebookexperimental/Robyn/main/python/src/robyn/tutorials/resources/.
  The file's two event dummies are merged into one control; its channels have no
  names, so they are labelled Media channel 1 and 2; its spend is index scaled, so
  Layer D reports shares and ratios and the marginal ROAS numbers are in index units.
- D-16 Breakeven ROAS is 1 divided by a contribution margin of 40 percent, stated in
  src/ambo/configs/layer_r.yaml. This is an assumption for Rafael to confirm.
- D-17 The "next EUR 200k" question is answered through the plus-25-percent scenario,
  with the unit caveat written into reports/layer_d/next_200k.md. The extra budget
  bound lets each channel grow by the bound share plus the budget increase.
- D-18 Posterior draws (a few hundred kilobytes per layer) are committed under reports/
  so Layer D and the charts regenerate without sampling.
- D-19 CI runs ruff, the fast tests, the tiny-config pipeline and the executed
  notebook; the tiny outputs (reports/layer_p_tiny, data/synthetic_tiny) are ignored.
- D-20 Draft pull request 46 (build/ambo into main) was opened as the review vehicle
  for Stages 3 to 6. To stay at four open pull requests after pull request 45 appeared,
  36 and 41 were closed with the same comment as the others; their content is fully
  salvaged (diagnostics gates, holdout protocol).
- D-21 Pull request 45, opened by a parallel tooling session during the run, was not
  triaged, commented on or closed; it is Rafael's call.
- D-22 The first CI run of the Stage 2 commit on build/ambo failed on the smoke step's
  180-second limit: the tiny profile kept the reporting thresholds, which a 100-draw run
  cannot meet, so the ladder fitted each model three times. The tiny profile now
  switches the ladder off (sampling.ladder: false) and carries thresholds suited to
  its budget; its gates are still written to diagnostics.json and its numbers are
  never reported. Every later run, including main, had passed, but close to the
  limit.

## Next action

Rafael reviews pull request 46 and decides on the five items in the morning brief.

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

Kept open for Rafael's decision: 18 and 34. All others are closed with the comment
"Superseded by the build on main; see STATUS.md for the salvage record." (36 and 41 at
the end of the run, see D-20). Open at the end of the run: 18, 34, 45 (parallel build,
not part of this inventory) and 46 (build/ambo). No branch was deleted.
