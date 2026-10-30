# Economic evaluation: Austrian MMM and Budget Optimizer

Pre-build scenario exercise · evaluation date 2026-08-03 · method v2.0 · cost basis v1.2 ([COST_BASIS.md](https://github.com/RafaelBraga-Kribitz/braga-portfolio-docs/blob/main/docs/value-evaluation/COST_BASIS.md))

## Decision

The head of marketing at a large Austrian advertiser splits the same media budget across channels each year, with the model built in-house. Is it buying sales that would happen anyway while underfunding channels that add profit? Value = budget moved × change in incremental revenue per euro × margin.

## Scale, baseline and horizon

- The charter targets advertisers above about €200k of media a year [sourced: `PROJECT_CHARTER.md` §1 at `1851f39`]. An employer pays a senior data scientist 220 h for an MMM only at large scale, so the case is a large advertiser.
- Scale exists: FOCUS 2025 gross advertising values, rate-card based: REWE Group €226.4M, SPAR €194.3M, XXXLutz €168.4M [sourced: FOCUS 2025 ranking, supplied by the owner]. Net spend after discounts is unknown.
- Case advertiser: €20M net media, 10 % movable (€2M a year), contribution margin 25 % [assumptions: well below the gross values; retail margin].
- Baseline: today's split. k = share of the gain over platform-dashboard planning still available: 1 without an existing model, lower if an agency already runs one; central 0.5 [assumption: large advertisers often buy MMM through their agency].
- u = chance the result is used in the split: 0.8 [assumption, owner's judgement: non-use (committed contracts, channel-owner resistance, late results, wide intervals) happens but is the exception].
- Horizon: 3 yearly splits at 5 % (factor 2.72). Committed forecasts: client data falling through, Medium (R-1); weak identification, High (R-2).

## Scenarios

Outcomes of following the recommendation, against dashboard planning (k = 1). Δr = change in incremental revenue per euro moved; value = €2M × Δr × 25 %.

| Outcome | Δr | Value per year | Probability |
|---|---|---|---|
| Finds strong platform over-credit | +1.2 | +€600k | 0.20 [assumption: charter §1] |
| Finds a partial improvement | +0.5 | +€250k | 0.30 [assumption] |
| No reliable or actionable move | 0 | €0 | 0.20 [assumption] |
| Adverse: misidentified effects, e.g. promotions read as media | −0.8 | −€400k | 0.30 [assumption: R-2 High] |

## Expected value and cost

- Expected gain if used, k = 1: €75k a year, **€204k** over 3 years.
- Expected gross value = u × k × €204k = 0.8 × 0.5 × €204k = **€82k**.

Rate: €54 per active hour, the market cost of the role this work needs (data science · senior, advertised minimum, ADJMI snapshot 2026-10-18; ADJMI = Austria Data-Job Market Intelligence), €51 loaded plus €3 AI and equipment. Hours: owner scope estimate, 220 h, including data intake and first-year maintenance [estimate]; maintenance in years 2 and 3 at 10 % a year. Hosting €0.

| Case | Hours (build + years 2–3) | Total cost | Multiple |
|---|---|---|---|
| Central | 220 + 44 | €14,256 | 5.7× |
| 0.5× hours | 110 + 22 | €7,128 | 11.5× |
| 1.5× hours | 330 + 66 | €21,384 | 3.8× |

## Verdict

**Passes financial hurdle**: 5.7× central, conditional on the labelled assumptions; 4.5× at a rate 30 % higher (the inputs are floors); fails at 1.5× hours (3.8×). Maximum affordable cost: €82k ÷ 4 = **€20k**, a build of about 315 h.

Break-even driver, u × k: 0.07 for 1×, 0.28 for 4× (at u = 0.8, k ≥ 0.35).

For the mid-market design advertiser (€0.49M of media, €0.1M movable, 30 % margin, `docs/SPEC-01_ground_truth_simulator.md`), the same scenarios give €12.3k: 0.86×, fails.

Reversing assumptions:

1. An existing model already captures more than about two thirds of the gain (k < 0.35).
2. Less than about €1.4M a year actually moves (about €14M of net media at a 10 % share).

## Recommendation

**Build** for a large advertiser; first confirm the spend history varies enough by channel and reconciles with promotions and prices. Measure: hours; whether an incumbent model exists; budget moved; the change in incremental revenue per euro moved, checked by a lift test; the margin.

Actuals and lessons: [lessons-learned.md](lessons-learned.md).
