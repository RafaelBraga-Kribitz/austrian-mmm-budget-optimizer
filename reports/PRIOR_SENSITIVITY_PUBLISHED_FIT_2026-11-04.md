# Prior sensitivity, rerun on the published-fit setup (2026-11-04)

Question: does Facebook still clear the breakeven return of 2.50 under vague priors,
when the vague fit is made the same way as the published fit?

Short answer: **No.** Under vague priors the lower bound of Facebook's marginal ROAS at
current spend is 0.11 on the 500-draw subset that the optimiser reads (0.21 on all 4,000
draws). The rule holds Facebook at current spend. The recommendation changes from
"move out of Out-of-home into TV and Facebook" to "move out of Out-of-home into TV".
Data are the public Robyn demo file. Units are not euros.

## Why the two sets of figures differ

The two sets of numbers come from the same fit. They differ in how many posterior draws
they read.

| Figure set | Source | Posterior draws used | TV lower bound | Facebook lower bound |
|---|---|---|---|---|
| Portfolio page, README | `reports/layer_d/reallocation_table.csv` | 500 (random subset, seed 42) | 4.38 | 4.76 |
| `PRIOR_SENSITIVITY.md`, bd547f4 | `placebo.decision_ranking` on `reports/layer_r/posterior_draws.csv` | all 4,000 | 4.52 | 4.06 |

Evidence: on the committed reported-prior draws (`reports/layer_r/posterior_draws.csv`),
the two computations give TV 4.52 and Facebook 4.06 on all 4,000 draws, and TV 4.38 and
Facebook 4.76 on `rs.subset(500, seed=42)`. Both match the two documents to two decimals.
`ambo.optimize.run_layer_d` takes `rs_full.subset(decision.posterior_draws)`; the
sensitivity script reads the full set. Layer D on the committed draws reproduces the
published table to 2e-11.

Other things checked, and not the cause:

- The reported-prior fit in bd547f4 is the committed fit. `reports/layer_r/` has no
  changed fit file on `feat/data-quality-gate` against `origin/main`; only added files
  (`data_quality.*`, `marginal_roas.csv`).
- `layer_r.yaml` differs only by a source checksum line. Sampler settings, seed 42 and
  the diagnostic gates are the same.
- Code changes between the two branches are a data-quality gate, type annotations and an
  optimiser fix for the unspent-budget case. None changes the fit. The same-total
  allocation is unchanged. The `reports/layer_d/` files on that branch were re-rendered
  with the optimiser fix, so its +25 percent and +200,000 rows may differ from
  `origin/main`. This page uses the `origin/main` code throughout.

Why it matters: a 5th percentile on 500 draws is noisy. For Facebook, with a long upper
tail and small spend, the lower bound moved by 0.7 between the two readings of one fit.
The earlier page compares like with like (4,000 draws against 4,000 draws), but it does
not reproduce the figures a reader sees on the portfolio page. This page gives the
optimiser's 500-draw reading as the main figure, with the 4,000-draw reading beside it.

## What was run

Worktree `austrian-mmm-budget-optimizer-prior-sensitivity`, branch
`analysis/prior-sensitivity-published-fit`, from `origin/main` at 99ac5f7 (the lockfile
and code of the published fit; `uv sync`). `layer_r_vague.yaml` is added to that tree
from `feat/data-quality-gate`. The checksum line is removed, because `origin/main` code
does not read it. Against `layer_r.yaml` the file differs only in `layer`, `title`,
`output_dir` and the nine priors. Not changed: priors, rule, sampler settings, seed.

```sh
uv run python -m ambo.run layer_r --out reports/rerun/layer_r_reported
uv run python -m ambo.run layer_d --data reports/rerun/layer_r_reported --out reports/rerun/layer_d_reported
uv run python -m ambo.run layer_r --config src/ambo/configs/layer_r_vague.yaml
uv run python -m ambo.run layer_d --config src/ambo/configs/layer_r_vague.yaml --data reports/layer_r_vague --out reports/layer_d_vague
uv run python scripts/prior_sensitivity_table.py
```

Sampler: nutpie, 2 chains, tune 1000, draws 1000, target_accept 0.9, seed 42, with the
repo's gate ladder (raises target_accept, then doubles draws, when a gate fails).

## Does the reported-prior rerun reproduce the published numbers?

**No, not exactly.** The optimiser reproduces (Layer D on the committed draws matches to
2e-11). The sampler does not: the same code, data, seed and settings gave a different
draw set and a different ladder path.

| | Committed fit | Rerun |
|---|---|---|
| Ladder | 0.9/1000 fail, 0.95/1000 fail, 0.95/2000 pass | 0.9/1000 fail, 0.95/1000 fail, 0.99/1000 fail, 0.99/2000 pass |
| Final R-hat / min ESS (bulk) / divergences | 1.0033 / 764 / 0 | 1.0047 / 601 / 0 |
| Same-total gain, median (10th percentile) | 15.1 % (8.8 %) | 14.7 % (9.0 %) |
| Facebook marginal ROAS lower bound, 500 draws | 4.76 | 3.41 |
| TV marginal ROAS lower bound, 500 draws | 4.38 | 4.72 |
| Funded channels, same total | TV, Facebook | TV, Facebook |

The rule's decision and the headline gain hold. The channel intervals do not match to
two decimals. Nothing was adjusted to close that gap. The likely cause is run-to-run
Monte Carlo variation in nutpie that `random_seed=42` does not remove (not isolated
here). The Facebook lower bound under reported priors ranges from 3.06 to 4.76 across the
readings in the table below. That range shows how much of the earlier 4.06 versus 4.76
gap is Monte Carlo noise.

## Marginal ROAS at current spend, by channel and prior set

Median (90 % interval). "Funded" means the lower bound is above 2.50 and the rule lets
the channel grow. "500 d" is the optimiser's subset; "4000 d" is all draws.

| Channel | Published fit, reported priors | Rerun, reported priors | Rerun, vague priors |
|---|---|---|---|
| TV, 500 d | 7.26 (4.38 to 10.72), funded | 7.23 (4.72 to 10.41), funded | 6.88 (4.27 to 9.78), funded |
| TV, 4000 d | 7.26 (4.52 to 10.68) | 7.29 (4.73 to 10.50) | 6.74 (4.07 to 9.78) |
| Facebook, 500 d | 20.53 (4.76 to 45.52), funded | 19.14 (3.41 to 43.21), funded | 16.75 (0.11 to 46.24), **not funded** |
| Facebook, 4000 d | 19.61 (4.06 to 44.38) | 19.32 (3.06 to 43.61) | 15.54 (0.21 to 48.11) |
| Print, 500 d | 7.81 (1.22 to 16.01), held | 7.38 (1.29 to 17.01), held | 5.64 (0.37 to 15.68), held |
| Print, 4000 d | 7.63 (1.30 to 16.80) | 7.67 (1.14 to 16.77) | 5.95 (0.24 to 16.30) |
| Search, 500 d | 7.68 (0.89 to 25.55), held | 7.93 (0.32 to 24.52), held | 5.36 (0.03 to 29.63), held |
| Search, 4000 d | 7.54 (0.59 to 24.78) | 7.42 (0.47 to 24.94) | 5.37 (0.03 to 28.68) |
| Out-of-home, 500 d | 0.75 (0.10 to 1.68), cut | 0.71 (0.15 to 1.78), cut | 0.59 (0.00 to 1.68), cut |
| Out-of-home, 4000 d | 0.71 (0.10 to 1.70) | 0.72 (0.11 to 1.74) | 0.57 (0.01 to 1.70) |

Breakeven ROAS is 2.50 (contribution margin 40 %). Out-of-home is cut because its
marginal ROAS is below breakeven. It is not a funded channel under any prior set.

Share of posterior draws in which Facebook's marginal ROAS is above 2.50 (all draws):
0.97 (published fit), 0.96 (rerun), 0.88 (vague). Under vague priors, 12 % of draws put
Facebook below breakeven. The rule needs at most 5 % below, so Facebook fails.

## Reallocation gain under each prior set

Same total budget. Percent of current media contribution. The probability of a loss was
0 of 500 draws in every case.

| Prior set | Median | 10th percentile | Held by the rule | Recommended shift |
|---|---|---|---|---|
| Published fit, reported priors | 15.1 % | 8.8 % | Print, Search | Out-of-home -20 %, TV +50 %, Facebook +50 % |
| Rerun, reported priors | 14.7 % | 9.0 % | Print, Search | Out-of-home -20 %, TV +50 %, Facebook +50 % |
| Rerun, vague priors | 8.7 % | 4.0 % | Print, Facebook, Search | Out-of-home -17 %, TV +50 %, others at current spend |

Other scenarios (median / 10th percentile gain):

| Scenario | Published fit | Rerun, reported | Rerun, vague |
|---|---|---|---|
| +25 percent budget | 24.0 % / 15.2 % | 17.4 % / 10.0 % | 14.3 % / 7.0 % |
| +200,000 a year | 17.4 % / 10.6 % | 16.9 % / 10.6 % | 10.2 % / 5.0 % |

In the +25 percent scenario the reported-prior rerun also holds Facebook (the published
fit does not). Facebook is therefore close to the line under reported priors too. Its
funding there depends on the draw set.

## Sampler diagnostics

Repo gates: R-hat below 1.01, effective sample size above 400 (bulk and tail), zero
divergences. Values are for the final accepted attempt.

| Fit | R-hat max | ESS bulk min | ESS tail min | Divergences | Gates |
|---|---|---|---|---|---|
| Published fit (committed) | 1.0033 | 764 | 577 | 0 | pass |
| Rerun, reported priors | 1.0047 | 601 | 688 | 0 | pass |
| Rerun, vague priors | 1.0025 | 666 | 489 | 0 | pass |

The vague-prior holdout fit also passed (R-hat 1.0019, ESS bulk 633, 0 divergences).

Failed attempts before the final one (all recorded in each `diagnostics.json`):

- Vague: 0.90/1000 failed (5 divergences, R-hat 1.0107, min ESS 427); 0.95/1000 failed
  (7 divergences, ESS 252); 0.99/1000 failed (0 divergences, ESS 242); 0.99/2000 passed.
- Reported rerun: 0.90/1000 (R-hat 1.0151, ESS 208), 0.95/1000 (R-hat 1.0102, ESS 310)
  and 0.99/1000 (ESS 283) failed; 0.99/2000 passed.

The final vague fit used target_accept 0.99 and 2,000 draws per chain. The published fit
used 0.95 and 2,000. This is the repo's ladder at work. It is not a change to the priors
or to the sampler policy.

## Does the recommendation change?

Yes. Under vague priors, same total budget, the rule gives a smaller and different move.
Out-of-home loses 17 % (not 20 %), TV gains 50 %, and Facebook is held at current spend,
because the lower bound of its marginal ROAS is 0.11, not above 2.50. The expected gain
is a median 8.7 % (10th percentile 4.0 %), in place of 15.1 % (8.8 %). The direction of
the move (out of Out-of-home, into TV) survives. The Facebook leg does not. About 6.4 of
the 15.1 percentage points of median gain are not supported under vague priors in this
fit. This is a fit-to-fit comparison, with the Monte Carlo spread noted above.

## Limits

- One vague-prior fit and one reported-prior rerun. The reported-prior rerun already
  moves Facebook's lower bound from 4.76 to 3.41, so a single fit does not fix its
  value. The vague-prior bound (0.11 or 0.21) is far below that spread, so the
  conclusion about Facebook does not turn on it.
- The vague priors are deliberately worse (see `layer_r_vague.yaml`). They show how much
  the priors carry. They do not show which fit is better.
- The cause of the non-reproducible sampling was not isolated.
- Public demo data. Units are not euros.
- `reports/PRIOR_SENSITIVITY.md` (bd547f4) lives on `feat/data-quality-gate`, not on
  `origin/main`. This page is therefore a new dated file. The older page is unedited.

## Files

- `reports/layer_r_vague/`, `reports/layer_d_vague/`: vague-prior fit and optimiser run.
- `reports/rerun/layer_r_reported/`, `reports/rerun/layer_d_reported/`: reported-prior rerun.
- `reports/rerun/layer_d_committed_fit/`: Layer D on the committed draws (reproduction check).
- `src/ambo/configs/layer_r_vague.yaml`, `scripts/prior_sensitivity_table.py`.

## Run times

Reported-prior rerun 542 s (fit and holdout, all ladder attempts). Vague-prior run
904 s. The two ran in parallel on 16 cores. Layer D took 4 s each.
