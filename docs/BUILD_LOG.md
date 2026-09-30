# Build Log

This file is **append-only** and is never edited in place (EB-082 applied at document
level). A correction to a prior entry is never a rewrite — it is a **new dated entry that
cites the entry it corrects**. Entries are ordered by insertion, so file position, not the
date string, is the tie-break when two entries share a date: the entry appearing later in
the file is the later one. A milestone whose measured effort is **strictly greater than**
2x its Charter §5 day budget stops work and files an ADR analyzing why; effort measured at
exactly 2x does not trip the rule (e.g. an M0 measured at 1.0 d against its 0.5 d budget
does not trip — 1.01 d does).

---

## M0 - Bootstrap

### 2026-08-04 — D-29 audit: pre-existing artifacts vs WBS acceptance criteria

Phase 1 (P0/M0) opens with an audit of the three WBS tasks that were partly done before
this plan started: T-001 (git baseline), T-003 (repository skeleton), T-012 (governance
scaffold). Each acceptance criterion below was checked by running the probe named in the
Observed column, not by copying the D-29 known-state table in
`01-CONTEXT.md`.

| WBS AC | Expected | Observed | Verdict | Closed by |
|---|---|---|---|---|
| T-001 AC-1 | Baseline commit contains only documentation, zero code | `git log --oneline 1851f39 -1 --stat` shows 25 files changed, 4943 insertions(+), 0 deletions; every path is `.md` (AGENTS.md, PROJECT_CHARTER.md, docs/EXECUTION_BLUEPRINT/*, docs/SPEC-01..09) | PASS | — |
| T-001 AC-2 | `.gitattributes` or config pins LF for `*.csv`, `*.py`, `*.yaml`, `*.md` | No `.gitattributes` file exists; `git config --get core.autocrlf` (local) and `git config --global --get core.autocrlf` both exit 1 (unset) | FAIL | 01-01 Task 2 |
| T-001 AC-3 | No file from outside the corpus committed | Same `--stat` output as AC-1: all 25 paths are charter, agent playbook, SPEC-01..09 or execution-blueprint documents; nothing else | PASS | — |
| T-003 AC-1 | Tree diff vs SPEC-08 §2 is empty (allowing not-yet-created source files) | `ls` at repo root shows only `.gitignore`, `.git/`, `.planning/`, `AGENTS.md`, `PROJECT_CHARTER.md`, `docs/`. None of `README.md`, `LICENSE`, `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`, `.env.example`, `config/`, `src/ambo/`, `dbt/`, `scripts/`, `data/`, `exports/`, `reports/`, `dashboards/`, `tests/` exists yet | FAIL | 01-02 Task 3 |
| T-003 AC-2 | Ignore rules proven by validation probe | `touch data/warehouse/x.duckdb exports/foo.csv && git status --porcelain`: `data/warehouse/x.duckdb` does not appear (ignored, correct); `exports/foo.csv` appears as untracked (`?? exports/`) — correct per the W5 ingest resolution, which committed `exports/*.csv` by design rather than gitignoring it (SPEC-08 §2, EB-081). Probe files deleted immediately after the check; nothing was staged | PASS | — |
| T-003 AC-3 | LICENSE = MIT with author line matching Charter header | `ls LICENSE` — no such file | FAIL | 01-02 Task 3 |
| T-012 AC-1 | ADR template has the four GB-201 sections | `ls docs/ADR/` shows only `ADR-000_document-precedence-and-blueprint-defaults.md`; no template file exists | FAIL | 01-01 Task 3 |
| T-012 AC-2 | Pre-planned ADR slots ADR-001..005 listed with their GB-202 topics | No `docs/ADR/README.md` exists; no index of reserved slots exists anywhere | FAIL | 01-01 Task 3 |
| T-012 AC-3 | BUILD_LOG has its append-only rule stated at top | Before this task ran, `docs/BUILD_LOG.md` did not exist | FAIL | 01-01 Task 1 (this entry) |

**Deviations not remediated by this audit (recorded, not fixed):**

1. The baseline commit message reads `chore: baseline commit — charter, agent playbook,
   SPEC-01..09, execution blueprint`, not the exact text T-001's implementation notes
   specify (`chore: baseline governance corpus (Charter v1.0, SPEC-01..09, blueprint)`).
   EB-082 forbids amending a landed commit to fix this. ADR-006 (plan 01-03) carries the
   note per D-18 of `01-CONTEXT.md`: commits `1851f39`…`151d32b` predate the EB-080 commit
   convention, and conformance begins with the first `m0-bootstrap` commit.
2. `core.autocrlf` is unset both locally and globally. T-001's implementation notes
   proposed a local-config fix (`core.autocrlf=input`); D-22 supersedes that approach with
   a committed `.gitattributes`, which does not depend on the reviewer's own git config.
   Task 2 of this plan closes T-001 AC-2 on that basis, not by setting `core.autocrlf`.
3. `.gitignore` carries one line beyond the EB-081 list: `docs/EXECUTION_BLUEPRINT/`. This
   is D-01 (`01-CONTEXT.md`) and is correct — the execution blueprint is internal build
   scaffolding, restored to disk for this phase but never committed.

**PASS-with-evidence, recorded for completeness:**

- Repository merge settings match D-12: `gh api repos/:owner/:repo --jq '{squash:
  .allow_squash_merge, rebase: .allow_rebase_merge, merge: .allow_merge_commit}'` returns
  `{"squash": false, "rebase": false, "merge": true}`. Squash and rebase merge are
  disabled at the repository level, so the merge button cannot destroy the task-level
  commit trail EB-082 and the layer-order argument depend on.

---

### 2026-09-30: Correction to the 2026-08-04 entry (T-012 AC-2)

Corrects the T-012 AC-2 row of the 2026-08-04 audit above, which observed that no ADR
README existed. That was true on 2026-08-04. The index now exists at
`docs/adr/README.md` (lower-case `adr`, not `docs/ADR/`). It lists ADR-000, ADR-007,
ADR-008 and ADR-009 as the live set; slots 001 to 006 were never used and will not be
filled (ADR-009).

The planning files that entry cites (`01-CONTEXT.md`, plans 01-01 to 01-09) moved to
`docs/archive/agents/planning/phases/01-repository-foundation/`, and the Charter moved
to `docs/archive/PROJECT_CHARTER.md` (`docs/archive/README.md`). The milestone budget
rule in the header of this file cites the Charter and applied to the planning stack
only.

---

## Session logs moved from STATUS.md on 2026-09-30

The sections below were moved verbatim from STATUS.md, in their original order, so
that STATUS.md holds only the current state and the decisions. Headings are one level
deeper than in STATUS.md. Lines marked **[Stale 2026-09-30]**, **[Superseded by
ADR-007 (Robyn dataset)]** or **[Note 2026-09-30]** were added on the move; the
original text is unchanged.
The decision list D-01 to D-33 stays in STATUS.md.

### Audit fixes, second session (2026-09-15 evening)

Ranked audit items (ADR-007) and what was done:

1. Pull request 46 merged to main (merge commit 0be8cbc). Pull requests 45, 18 and 34
   closed with a comment; 36 and 41 had been closed earlier. Open pull requests: none
   besides the follow-up draft for this session.
2. Layer R swapped to Robyn's simulated weekly dataset (five named channels, money
   units, competitor sales as the control). Source, licence and checksum in
   data/README.md. The breakeven gate now binds: on the same budget it holds Print and
   Search (marginal ROAS lower bounds below 2.5) and Out-of-home loses budget because
   its ROAS sits below breakeven.
3. Layer P gained a response-curve overlay (reports/layer_p/response_curve_recovery.png,
   response_curves.csv, response_curve_metrics.csv) and the README states the
   effect-times-saturation trade-off and the TV share miss in plain words.
4. README wording: interval coverage against nominal is stated per layer (85 versus 90
   on Layer P: slightly overconfident; 100 on Layer R: wider than needed); the
   attribution gap now leads with online over-credit in absolute terms (Paid Search
   platform-reported revenue 45 percent above its true incremental revenue).
5. A sentence under the title says what "Austrian" means here.
6. duckdb removed from the dependencies and the lockfile. Branch deletion is blocked in
   this environment (see Blockers); the command for Rafael is there.

> **[Stale 2026-09-30]** Branch deletion was done on 2026-09-16 (STATUS D-30).

Numbers produced in this session (each from the named artifact):

| Metric | Value | Artifact |
|--------|-------|----------|
| Layer P response-curve coverage, mean over channels / worst (TV) | 91 / 56 percent of grid points in the observed spend range | reports/layer_p/response_curve_metrics.csv |
| Layer P response-curve error, worst channel | 13.6 percent of the true curve height | same |
| Layer P effect and half-saturation medians above truth | 5 of 5 and 5 of 5 | reports/layer_p/parameter_recovery.csv |
| Paid Search platform-reported over true incremental revenue | +45.1 percent (3489025 vs 2404051); Paid Social +54.9 percent | reports/layer_p/attribution_gap.csv |
| Layer R (Robyn) revenue share, median (90 percent interval) | TV 6.0 (3.5 to 10.0); Out-of-home 2.7 (0.3 to 7.9); Print 1.8 (0.4 to 5.5); Facebook 2.5 (0.6 to 5.5); Search 3.2 (0.3 to 10.5) | reports/layer_r/channel_contributions.csv |
| Layer R ROAS, median | TV 7.3; Out-of-home 1.1; Print 8.7; Facebook 21.4; Search 9.8 | same |
| Layer R diagnostics | full fit passed at 0.95 with 2000 draws after ESS shortfalls (290, 301); holdout passed at 0.99 with 2000 draws | reports/layer_r/diagnostics.json, holdout_diagnostics.json |
| Layer R holdout, 26 weeks | MMM MAPE 7.9 percent, ridge 5.1, seasonal naive 22.3; coverage 100, 100, 96 percent. The MMM loses on point error; the README says so | reports/layer_r/holdout_metrics.csv |
| Layer D same budget | median gain +15.1 percent of media contribution, 10th percentile +8.8, no losing draw; TV +50 percent, Facebook +50 percent, Out-of-home -20 percent, Print and Search held by the rule; verdict recommend | reports/layer_d/decision.json, reallocation_table.csv |
| Layer D plus 25 percent | median gain +24.0 percent, 10th percentile +15.2; Out-of-home, Print and Search held | same |
| Layer D plus 200000 per year | median gain +17.4 percent, 10th percentile +10.6; verdict recommend | reports/layer_d/next_200k.md |

Decisions taken in this session:

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

### Morning brief

Written 2026-09-15 at the end of the overnight run, kept as the record of that run.
Its Layer R and Layer D numbers come from the pymc-marketing example data and are
superseded by the audit-fixes section above. Six stages done; nothing is blocked.

> **[Stale 2026-09-30]** Every item under "Decisions for Rafael today" below is closed: 1 pull request 46 merged; 2 pull request 45 closed (D-27); 3 Layer R swapped to the Robyn dataset (ADR-007, pull request 47); 4 contribution margin kept at 40 percent as a placeholder assumption (D-28); 5 pull requests 18 and 34 closed. The read-aloud paragraph describes the pymc-marketing run; on the Robyn data the same-budget verdict is recommend, not hold. build/ambo was deleted under D-30.

**Where the code is.** main holds Stages 1 and 2: commit 3285620 (merge of cd235f2,
hygiene, package skeleton and CI) and commit 3768d7c (merge of 6218abd, Layer P with
parameter recovery). build/ambo holds, on top of that, bbf6b2a (Stage 3, Layer R),
7bbccf5 (Stage 4, Layer D), 90b0658 (Stage 5, rendered README and German summary),
081b14b (Stage 6, executed notebook), 6ef121e (this brief), 3328693 (smoke profile
fix) and one lint fix on top of it. Draft pull request 46 (build/ambo into main) is
the review vehicle. Eleven commits in total, one over the cap of ten (see D-23), one
human identity, no history rewritten, no branch deleted.

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

> **[Stale 2026-09-30]** Pull request 45 was closed on 2026-09-15 (D-27, ADR-007).

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

### Current stage

All six stages done and on `main` (merge commits `0be8cbc` and `8e77086`). Open
pull requests: none. Next stretch is portfolio polish (D-29), not a new model.

### Done

| Stage | Commit | Produced |
|-------|--------|----------|
| 0 Inventory | cd235f2 (with Stage 1) | Counts, constraints and triage table below. |
| 1 Hygiene | cd235f2, merged to main in 3285620 | Root cleaned, docs moved, LICENSE, package skeleton with transforms and calendar, CI, uv lock; 40 pull requests closed, 4 kept open. |
| 2 Layer P | 6218abd, merged to main in 3768d7c | Synthetic advertiser with disclosed truth, PyMC model, parameter and contribution recovery, attribution gap, holdout against two baselines, all under reports/layer_p. |
| 3 Layer R | bbf6b2a (build/ambo) | Same model on the pymc-marketing example dataset: channel contributions, response curves, holdout, diagnostics, posterior draws under reports/layer_r. |
| 4 Layer D | 7bbccf5 (build/ambo) | Budget optimiser on the Layer R posterior: reallocation table, gain distribution, decision rule, next-budget note under reports/layer_d. |
| 5 README | 90b0658 (build/ambo) | README.md and docs/summary_de.md rendered from reports/ by scripts; numbers test in tests/test_readme_numbers.py. |
| 6 Notebook | 081b14b (build/ambo) | notebooks/01_walkthrough.ipynb executed on the tiny config with outputs saved; CI runs it. |

> **[Stale 2026-09-30]** Stages 3 and 4 describe the pymc-marketing dataset. Superseded by ADR-007 (Robyn dataset): commit 41ac4d5, merged in 8e77086 (pull request 47). build/ambo no longer exists (D-30).

### Numbers

Every number below is read from the named artifact; none is typed from memory. The
Layer R and Layer D tables are from the overnight run on the pymc-marketing example data;
the current Robyn-data numbers are in the audit-fixes section at the top.

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

> **[Stale 2026-09-30]** Layer P was rerun in the second session for the response-curve overlay. The counts above still match the artifacts; reports/layer_p/run_info.json now records 907.3 seconds.

Layer R, public demo data (pymc-marketing example, 179 weeks, 2 channels):

> **[Superseded by ADR-007 (Robyn dataset)]** This table and the Layer D table below are the pymc-marketing run: 2 channels, same-budget gain +2.5 percent, verdict hold. Current numbers are in STATUS.md, "Current results".

| Metric | Value | Artifact |
|--------|-------|----------|
| Share of revenue, Media channel 1 | 22.1 percent (18.1 to 28.1) | reports/layer_r/channel_contributions.csv |
| Share of revenue, Media channel 2 | 7.1 percent (6.6 to 7.7) | same |
| ROAS in the file's index units (revenue per unit of spend) | channel 1: 3783 (3089 to 4798); channel 2: 2322 (2160 to 2505) | same |
| Full-fit diagnostics | max R-hat 1.006, min ESS 441, 0 divergences, first attempt | reports/layer_r/diagnostics.json |
| Holdout, last 26 weeks | MMM MAPE 4.4 percent, coverage 85 percent; ridge 7.5 percent, 92 percent; seasonal naive 19.3 percent, 96 percent | reports/layer_r/holdout_metrics.csv |

Layer D, decision on the Layer R posterior (500 draws, 200 per-draw optimisations):

> **[Superseded by ADR-007 (Robyn dataset)]** See the note above the Layer R table.

| Metric | Value | Artifact |
|--------|-------|----------|
| Same total budget: gain from reallocation | median +2.5 percent of current media contribution, 10th percentile -0.8 percent, probability of a loss 14.6 percent; verdict: hold (10th percentile negative) | reports/layer_d/decision.json |
| Same total budget: moves | Media channel 1 +23 percent, Media channel 2 -45 percent of current weekly spend | reports/layer_d/reallocation_table.csv |
| Budget plus 25 percent | median gain +23.3 percent, 10th percentile +18.9 percent, no draw loses; 92 percent of the extra goes to channel 1; probability channel 1 is not the best marginal channel 43.6 percent; verdict: recommend | reports/layer_d/next_200k.md |
| Breakeven ROAS | 2.50 at a contribution margin of 40 percent (assumption in src/ambo/configs/layer_r.yaml) | reports/layer_d/decision.json |

### Next action

Polish done 2026-09-16 on `main`: decision record committed; `LIMITATIONS.md` at the
root (eleven items mapped to SPEC-09 section 6, no hand-typed numbers); dashboard feed
under `reports/exports/` from `scripts/export_dashboard.py` with `docs/dashboard_handoff.md`;
ADR-007 (audit verdict) added from the audit log and `docs/adr/README.md` indexes the
records; README links all three; annotated tag `v1.0.0`. What remains is human work:
the Power BI build and screenshots, and the client drop with written permission.
Contribution margin stays 40 percent until a real client figure exists (D-28).

> **[Note 2026-09-30]** The tag sentence is correct: annotated tag v1.0.0 exists on origin at 113c601. Audit item 19 checked a local clone without fetched tags. The Power BI build, screenshots and the client drop are still open.

### Inventory

#### Counts (live, 2026-09-15)

| Item | Count |
|------|-------|
| Open pull requests | 44 (numbers 1 to 44, all against the previous branch in one stacked chain, except 1, 2 and 11 which target main) |
| Open issues | 0 |
| Remote branches | 45 (43 stack branches sharing the 9588 suffix, m0-bootstrap, main) |
| Local branches at start | 2 (main and the session branch) |

Reconciliation of the critiques: 44 is the number of open pull requests, 45 is the number
of remote branches (44 pull request heads plus main), and there are no issues at all.

#### Constraints extracted from the charter, specs and ADR

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

> **[Note 2026-09-30]** ADR-005, ADR-010 and ADR-011 in item 9 are records on the closed stack branches, not files in docs/adr/. Slots 001 to 006 in docs/adr/ are unused (ADR-009).

#### Pull request triage

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

All 44 stack pull requests are closed with the comment "Superseded by the build on
main; see STATUS.md for the salvage record." (18, 34, 36 and 41 last, per the audit).
Pull request 45 (parallel build) was closed per ADR-007; pull request 46 (build/ambo)
was merged to main. Branch deletion is pending on Rafael's side (see Blockers).

> **[Stale 2026-09-30]** Branch deletion was done on 2026-09-16 (D-30).
