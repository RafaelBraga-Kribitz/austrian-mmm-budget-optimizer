# Economic evaluation: Austrian MMM and Budget Optimizer

Pre-build scenario exercise · evaluation date 2026-08-03 · method v2.0 · cost basis v1.2 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision

The head of marketing at an Austrian mid-market advertiser splits the same media budget across channels each year. The question is whether it is buying sales that would happen anyway while underfunding channels that add profit. Value = budget moved × change in incremental revenue per euro × margin.

## Scale, baseline and horizon

- Target: an Austrian advertiser above about €200k a year of media [sourced: `PROJECT_CHARTER.md` §1 at `1851f39`].
- Design advertiser, a Graz outdoor-gear e-tailer: six channels, base revenue €60k a week; media about €0.49M a year [sourced: `docs/SPEC-01_ground_truth_simulator.md` §2–3 at `1851f39`; estimate].
- Movable budget: €0.1M a year, 20 % [assumption]; the optimiser keeps the total and caps each channel [sourced: `docs/SPEC-06_decision_layer.md` §2–3 at `1851f39`].
- Contribution margin: 30 % [assumption: e-retail].
- Baseline: today's allocation, split by what platform dashboards credit; they "over-credit their own channels" (charter §1). The unchanged media budget is not a cost.
- Horizon: 3 yearly splits, discounted at 5 % (factor 2.72).
- Committed forecasts: effort budget 14 days (charter §5); client data falling through, Medium (R-1); weak identification, High (R-2).

## Scenarios

Outcomes after following the recommendation, including imperfect estimation and whether the advertiser acts. Δr = change in incremental revenue per euro moved; value = €0.1M × Δr × 30 %.

| Outcome | Δr | Value per year | Probability |
|---|---|---|---|
| Finds strong platform over-credit | +1.2 | +€36k | 0.20 [assumption: charter §1] |
| Finds a partial improvement | +0.5 | +€15k | 0.30 [assumption] |
| No reliable or actionable move | 0 | €0 | 0.20 [assumption] |
| Adverse: misidentified effects move euros into saturated channels | −0.8 | −€24k | 0.30 [assumption: R-2 High; short, collinear spend history] |

## Expected value and cost

Expected gain = 0.20 × €36k + 0.30 × €15k − 0.30 × €24k = €4.5k a year; over 3 years **€12.3k**. The adverse row cancels most of the strong one: identification risk, not model fit, sets the value.

Rate: €54 per active hour, the market cost of the role this work needs (data science · senior, advertised minimum, ADJMI snapshot 2026-10-18; ADJMI = Austria Data-Job Market Intelligence), €51 loaded plus €3 AI and equipment. Hours: owner scope estimate, 220 h, including data intake and first-year maintenance [estimate]. Maintenance for years 2 and 3: 10 % of build hours a year. Hosting €0.

| Case | Hours (build + years 2–3) | Total cost | Multiple |
|---|---|---|---|
| Central | 220 + 44 | €14,256 | 0.86× |
| 0.5× hours | 110 + 22 | €7,128 | 1.7× |
| 1.5× hours | 330 + 66 | €21,384 | 0.57× |

## Verdict

**Fails financial hurdle**: 0.86× central against 4×; 0.67× at a rate 30 % higher (the inputs are floors). Maximum affordable cost: €12.3k ÷ 4 = **€3.1k**, about 47 h in all.

Break-even driver, budget actually moved each year: €116k for 1× (about €0.58M of media at a 20 % share); €465k for 4× (about €2.3M of media).

Reversing assumptions:

1. An advertiser with about €2.3M of media a year or more, at the same share and margin.
2. Spend history that identifies channel effects well enough to cut the adverse probability to 0.10; 4× then needs about €1.1M of media.

## Recommendation

**Defer** until an advertiser of about €2.3M of media, with 52 or more weeks of spend by channel and written data permission, is in hand. For a smaller client, a geo-split or holdout experiment on one channel answers the main question for far less. Measure: hours; whether data arrive and budget moves; the amount moved; the change in incremental revenue per euro moved, checked by a lift test; the margin.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
