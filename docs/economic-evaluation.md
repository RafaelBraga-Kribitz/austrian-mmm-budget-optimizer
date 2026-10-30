# Economic evaluation: Austrian MMM and Budget Optimizer

Pre-build scenario exercise · evaluation date 2026-08-03 · method v2.0 · cost basis v1.1 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision

The head of marketing at an Austrian mid-market advertiser splits the same media budget across channels each year; the study is valued by the contribution profit a better-informed split adds: budget moved × change in incremental revenue per euro × margin.

## Scale, baseline and horizon

- Target: an Austrian advertiser above about €200k a year of media spend [sourced: `PROJECT_CHARTER.md` §1 at `1851f39`].
- Design advertiser, a Graz outdoor-gear e-tailer: six channels, base revenue €60k a week [sourced: `docs/SPEC-01_ground_truth_simulator.md` §2 at `1851f39`]; spend about €0.49M a year [estimate, SPEC-01 §3].
- Movable budget: €0.1M a year, 20 % [assumption]; the optimiser keeps the total, caps channels at 1.3× their largest weekly spend and excludes brand search [sourced: `docs/SPEC-06_decision_layer.md` §2–3 at `1851f39`; charter risk R-4].
- Contribution margin: 30 % [assumption: e-retail].
- Baseline: the split platform dashboards credit; they "over-credit their own channels" (charter §1).
- Horizon: 3 yearly splits, discounted at 5 %.
- Committed forecasts: effort budget 14 days (charter §5); client data falling through Medium (R-1); weak identification High (R-2).

## Scenarios

Action: move €0.1M a year from the channels platforms credit most to those they under-credit. Δr = change in incremental revenue per euro moved; value = €0.1M × Δr × 30 %.

| State | Δr | Value per year | Probability |
|---|---|---|---|
| Strong platform over-credit | +1.2 | +€36k | 0.20 [assumption: charter §1] |
| Partial over-credit | +0.5 | +€15k | 0.30 [assumption] |
| Split near the best; no usable benefit | 0 | €0 | 0.20 [assumption] |
| Adverse: moved euros land in saturated or zero-effect channels | −0.8 | −€24k | 0.30 [assumption: R-2 High, R-4] |

## Expected value and cost

- EV(move without the study) = 0.20 × 36 + 0.30 × 15 + 0 − 0.30 × 24 = +€4.5k a year: moving is the uninformed choice.
- Perfect information moves except in the adverse state: €7.2k + €4.5k = €11.7k a year. Expected value of perfect information (EVPI) = €11.7k − €4.5k = **€7.2k a year**; over 3 years at 5 % (factor 2.72), **€19.6k**.
- Realistic fraction f = 0.35 [assumption, sensitivity parameter: the known-truth test raises trust; short, collinear data (R-2) and data that may not arrive (R-1) pull it down]. Expected gross value = 0.35 × €19.6k = **€6.9k**.

Rate: €54 per active hour, the market cost of the role this work needs (data science · senior, advertised minimum, ADJMI snapshot 2026-10-18; ADJMI = Austria Data-Job Market Intelligence), €51 loaded plus €3 AI and equipment. Maintenance: 10 % of build hours a year, 3 years. Implementation: 12 h client data intake (charter M4: 1.5 days) [estimate]. Hosting €0.

| Case | Build | Maintenance | Implementation | Total cost | Multiple |
|---|---|---|---|---|---|
| Central, 36 h | €1,944 | €583 | €648 | €3,175 | 2.2× |
| 0.5×, 18 h | €972 | €292 | €648 | €1,912 | 3.6× |
| 1.5×, 54 h | €2,916 | €875 | €648 | €4,439 | 1.5× |

## Verdict

**Fails financial hurdle**: 2.2× central against 4×; 1.7× at a rate 30 % higher (€69.3 all-in; the inputs are floors). Maximum affordable cost: €6.9k ÷ 4 = **€1.7k**.

Break-even driver: budget actually moved. 1× at €46k a year; 4× at €185k, about €0.93M of media at a 20 % share.

Reversing assumptions:

1. Media spend of €0.93M or more, same movable share.
2. Client data identify channels well enough for f ≥ 0.65.

## Recommendation

**Defer** until an advertiser with about €0.9M of media, 52 or more weeks of spend by channel and written data permission is in hand. Measure: hours; whether data arrive and budget moves; the amount moved; the change in incremental revenue per euro moved, checked by a lift test; the margin.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
