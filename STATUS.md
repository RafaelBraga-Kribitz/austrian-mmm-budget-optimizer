# STATUS

Updated 2026-09-30. Working branch: main. This file holds the current state and the
decisions only. The session logs up to 2026-09-16 (overnight build, morning brief,
audit fixes, polish, inventory and pull request triage) are in `docs/BUILD_LOG.md`,
section "Session logs moved from STATUS.md on 2026-09-30".

## Current state

- **Package.** All six build stages are on `main`: Layer P (synthetic advertiser with
  disclosed truth), Layer R (Robyn's simulated weekly dataset, five named channels,
  ADR-007), Layer D (budget optimiser on the Layer R posterior), the rendered README
  and German summary, the executed notebook, tests and CI. Merge commits `0be8cbc`
  (pull request 46) and `8e77086` (pull request 47).
- **Governance.** Live records are ADR-000, ADR-007, ADR-008 and ADR-009 in
  `docs/adr/`. ADR-009 lists the spec sections that were never built. The planning
  stack (charter, agent playbook, GSD plans) is archived under `docs/archive/`.
- **Branches.** The D-30 cleanup was done on 2026-09-16. Checked with
  `git ls-remote origin` on 2026-09-30: `main` plus the heads of merged pull requests
  48 to 52 (`feat/memo-en`, `cursor/readme-standard-109f`, `readme-v1.2`,
  `readme-diagram-direction`, `claude/dreamy-rubin-k4envu`). All five are merged into
  `main` and can be deleted.
- **Tag and version.** Annotated tag `v1.0.0` exists on origin at `113c601` (portfolio
  polish, 2026-09-16). A clone that has not fetched tags does not show it; audit item 19
  was checked on such a clone. `pyproject.toml` carried version 0.1.0 at that commit.
  The 2026-09-30 audit fixes set the package version to 1.1.0 in `pyproject.toml` and
  `ambo.__version__`; the matching tag `v1.1.0` goes on `main` after they merge. Open,
  see below.
- **Contribution margin.** 40 percent, breakeven ROAS 2.50. A placeholder assumption
  in `src/ambo/configs/layer_r.yaml` until a real client margin exists (D-16, D-28).

## Current results

Every value is read from the named artifact. Layer R is the Robyn dataset (208 weeks);
Layer P is the synthetic advertiser (156 weeks).

| Metric | Value | Artifact |
|--------|-------|----------|
| Layer P true parameters inside their 90 percent interval | 26 of 28; misses: Paid Search decay, TV slope | reports/layer_p/parameter_recovery.csv |
| Layer P channels whose true revenue share is inside the interval | 4 of 5 (TV just outside) | reports/layer_p/contribution_recovery.csv |
| Layer P response-curve coverage, mean over channels / worst (TV) | 91 / 56 percent of grid points in the observed spend range | reports/layer_p/response_curve_metrics.csv |
| Layer P response-curve error, worst channel | 13.6 percent of the true curve height | same |
| Layer P effect and half-saturation medians above truth | 5 of 5 and 5 of 5 | reports/layer_p/parameter_recovery.csv |
| Paid Search platform-reported over true incremental revenue | +45.1 percent (3489025 vs 2404051); Paid Social +54.9 percent | reports/layer_p/attribution_gap.csv |
| Layer P holdout, weeks 131 to 156 (trained on 130) | MMM MAPE 3.0 percent, coverage 85; ridge 4.7, 92; seasonal naive 9.6, 92 | reports/layer_p/holdout_metrics.csv |
| Layer R (Robyn) revenue share, median (90 percent interval) | TV 6.0 (3.5 to 10.0); Out-of-home 2.7 (0.3 to 7.9); Print 1.8 (0.4 to 5.5); Facebook 2.5 (0.6 to 5.5); Search 3.2 (0.3 to 10.5) | reports/layer_r/channel_contributions.csv |
| Layer R ROAS, median | TV 7.3; Out-of-home 1.1; Print 8.7; Facebook 21.4; Search 9.8 | same |
| Layer R holdout, last 26 of 208 weeks (trained on 182) | MMM MAPE 7.9 percent, ridge 5.1, seasonal naive 22.3; coverage 100, 100, 96 percent. The MMM loses on point error; the README says so | reports/layer_r/holdout_metrics.csv |
| Layer D same budget | median gain +15.1 percent of media contribution, 10th percentile +8.8, no losing draw; Print and Search held by the rule; verdict recommend | reports/layer_d/decision.json, reallocation_table.csv |
| Layer D plus 25 percent | median gain +24.0 percent, 10th percentile +15.2; Out-of-home, Print and Search held | same |
| Layer D plus 200000 per year | median gain +17.4 percent, 10th percentile +10.6; verdict recommend | reports/layer_d/next_200k.md |
| Breakeven ROAS | 2.50 at a contribution margin of 40 percent (placeholder assumption) | reports/layer_d/decision.json |

Sampler gates (R-hat below 1.01, ESS above 400, zero divergences) pass on every
reported fit after the recorded ladder (D-13). The target acceptance each fit passed
at, from the `attempts` list of its diagnostics file:

| Fit | Passed at | Attempts before it | Artifact |
|-----|-----------|--------------------|----------|
| Layer P full, 156 weeks | target_accept 0.99, 1000 draws | 14 divergences at 0.9, 1 at 0.95 | reports/layer_p/diagnostics.json |
| Layer P holdout, 130 weeks | target_accept 0.99, 2000 draws | divergences at 0.9, ESS shortfall at 0.95, divergences at 0.95 with 2000 draws | reports/layer_p/holdout_diagnostics.json |
| Layer R full, 208 weeks | target_accept 0.95, 2000 draws | R-hat 1.012 and ESS 290 at 0.9, ESS 301 at 0.95, both with 1000 draws | reports/layer_r/diagnostics.json |
| Layer R holdout, 182 weeks | target_accept 0.99, 2000 draws | divergences at 0.9, ESS shortfall at 0.95, divergences at 0.95 with 2000 draws | reports/layer_r/holdout_diagnostics.json |

## Open now

- **Release tag.** Create annotated tag `v1.1.0` on `main` after the 2026-09-30 audit
  fixes merge (`v1.0.0` is taken by `113c601`; the package version is already 1.1.0).
- **Merged branches.** Delete the five merged heads listed under Current state.
- **Audit 2026-09-30.** All items are closed except item 13: pin the README contract
  repository in `.github/workflows/readme-quality.yml` to a commit SHA (resolution
  table in `docs/AUDIT_2026-09-30.md`).
- **Human work.** The Power BI build and its screenshots (`docs/dashboard_handoff.md`).
- **Blocker for real data.** The private agency drop plus written permission is the
  only external blocker for Layer R on real Austrian client data. D-29 says do not wait
  idle: polish the public-demo package. AG-002 still forbids gray-zone processing.

## Decisions

A decision that no longer holds is marked, not deleted. Markers added on 2026-09-30
are in bold.

### Recorded 2026-09-16

Rafael chose all six remaining items in session. Defaults were the recommendations;
none was overridden.

| ID | Choice | What it means |
|----|--------|----------------|
| D-28 | Keep contribution margin at 40 percent | Breakeven ROAS stays 2.50. Labeled assumption in `src/ambo/configs/layer_r.yaml`. A real client margin replaces it at intake; until then do not retune the rule. Closes the open question in D-16. |
| D-29 | Next work is portfolio polish while waiting for the private drop | LIMITATIONS, dashboard handoff, v1 tag, ADRs, branch cleanup. Do not resurrect the GSD warehouse/dbt stack. Do not gray-zone process client files. |
| D-30 | Delete stale remote branches | Done 2026-09-16: 46 heads removed (`m0-bootstrap`, `build/ambo`, the `-9588` stack, `cursor/layer-p-pipeline-9588`). Remote then had `main` only. GitHub can restore any of them from its closed pull request. **Heads of pull requests 48 to 52 were added and merged later; see Current state.** |
| D-31 | This workspace tracks `origin/main` | Local `m0-bootstrap` is abandoned. Untracked leftovers (`.planning/`, `dbt/`, `docs/EXECUTION_BLUEPRINT/`) stay off main. |
| D-32 | Restore `.gitattributes` | Reverses D-03. Windows checkouts pin LF so CSV and Python stay byte-stable. Source: commit `9318dd1`. |
| D-33 | File ADRs for the slim-build spec deviations; do not revert | D-05 (five channels), D-11 (matched adstock), D-12 (LogNormal slope), D-14 (26-week holdout), D-06 (Python 3.11). Recorded in `docs/adr/ADR-008_slim-build-spec-deviations.md`. Spec sections never built: ADR-009. |

**Not on the table.** D-05, D-11, D-12, D-14, D-24, D-27 remain as shipped. Repo stays public.

### Taken 2026-09-15 evening (audit fixes, ADR-007)

- D-24 Layer R uses competitor sales (divided by its mean) as the one control; the two
  one-off events and the newsletter column are not used. Reversible in
  src/ambo/configs/layer_r.yaml.
- D-25 The 200000-per-year question is answered as a third optimiser scenario, the
  yearly amount spread over 52 weeks on top of the current weekly total, in the
  dataset's money units.
- D-26 The smoke profile of Layer P is unchanged; the overlay chart is produced there
  too and shown in the notebook.
- D-27 Pull request 45 was closed on Rafael's decision (ADR-007) with a comment; its
  branch is untouched and retrievable from the pull request.

### Taken 2026-09-15 (overnight build)

- D-01 Stage 0 inventory runs inside this build instead of waiting for a separate
  review of the pull request export. Reversible: nothing in Stage 0 changes the repo.
- D-02 The .planning directory (GSD workflow artifacts) moved to docs/agents/planning
  because its files reference the workflow tooling that produced them and the root
  allow list has no place for it. Nothing was deleted. **Moved again on 2026-09-30 to
  docs/archive/agents/planning (docs/archive/README.md).**
- D-03 .gitattributes was removed from the root because it is not on the root allow
  list. It only pinned LF line endings; every file in the repo is LF already and the
  CI runner is Linux. Restore from commit 9318dd1 if Windows checkouts need it.
  **Reversed by D-32.**
- D-04 The pull request stack was salvaged by copying functions, not by cherry-picking
  commits, because every branch depends on a settings, pydantic and dbt layer that the
  new package does not have. The salvage record is in the Inventory section. **The
  Inventory section is now in docs/BUILD_LOG.md.**
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
  words. Tracked files outside docs/agents are clean. **The planning files are now
  under docs/archive/agents/planning; --exclude-dir=agents still matches that base
  name.**
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
  target_accept of 0.9 therefore does not hold on this data. **Per-fit rungs on the
  current artifacts are in Current results: the Layer R full fit passed at 0.95, the
  other three fits at 0.99.**
- D-14 Holdout is weeks 131 to 156 (26 weeks) as the build brief asks, not the 13-week
  protocol of SPEC-05. **On Layer R the holdout is the last 26 of 208 weeks.**
- D-15 Layer R uses the pymc-marketing example file because it was reachable; Robyn's
  dt_simulated_weekly (five named channels, money units) is the alternative and was
  also reachable at
  github.com/facebookexperimental/Robyn/main/python/src/robyn/tutorials/resources/.
  The file's two event dummies are merged into one control; its channels have no
  names, so they are labelled Media channel 1 and 2; its spend is index scaled, so
  Layer D reports shares and ratios and the marginal ROAS numbers are in index units.
  **Superseded by ADR-007 (Robyn dataset) and D-24.**
- D-16 Breakeven ROAS is 1 divided by a contribution margin of 40 percent, stated in
  src/ambo/configs/layer_r.yaml. This is an assumption for Rafael to confirm.
  **Confirmed as a placeholder assumption by D-28.**
- D-17 The "next EUR 200k" question is answered through the plus-25-percent scenario,
  with the unit caveat written into reports/layer_d/next_200k.md. The extra budget
  bound lets each channel grow by the bound share plus the budget increase.
  **Superseded by D-25 (a separate plus-200000-per-year scenario).**
- D-18 Posterior draws (a few hundred kilobytes per layer) are committed under reports/
  so Layer D and the charts regenerate without sampling. **The committed files are now
  about 0.9 MB (Layer P) and 1.8 MB (Layer R); audit item 16.**
- D-19 CI runs ruff, the fast tests, the tiny-config pipeline and the executed
  notebook; the tiny outputs (reports/layer_p_tiny, data/synthetic_tiny) are ignored.
- D-20 Draft pull request 46 (build/ambo into main) was opened as the review vehicle
  for Stages 3 to 6. To stay at four open pull requests after pull request 45 appeared,
  36 and 41 were closed with the same comment as the others; their content is fully
  salvaged (diagnostics gates, holdout protocol). **Pull request 46 was merged.**
- D-21 Pull request 45, opened by a parallel tooling session during the run, was not
  triaged, commented on or closed; it is Rafael's call. **Superseded by D-27.**
- D-22 The first CI run of the Stage 2 commit on build/ambo failed on the smoke step's
  180-second limit: the tiny profile kept the reporting thresholds, which a 100-draw run
  cannot meet, so the ladder fitted each model three times. The tiny profile now
  switches the ladder off (sampling.ladder: false) and carries thresholds suited to
  its budget; its gates are still written to diagnostics.json and its numbers are
  never reported. Every later run, including main, had passed, but close to the
  limit.
- D-23 Commit 3328693 went out with one line over the ruff length limit because the
  shell command that ran the gates did not stop on the lint failure before committing.
  The eleventh commit fixes the line. Amending and force-pushing would have kept the
  count at ten but breaks the no-rewrite rule, which weighs more; the cap of ten
  commits is therefore exceeded by one, and the cause is recorded here.
