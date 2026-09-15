# Austrian MMM and Budget Optimizer

For one advertiser, which channels contributed incrementally, how far off were
platform-reported numbers, and what does a reallocation gain?

![Incremental contribution per channel on public demo data, with 90 percent intervals](reports/layer_r/channel_contributions.png)

On synthetic data with known truth, 26 of 28 true parameters fall inside their 90 percent posterior intervals, and the platform-reported share of Paid Search is 24.8 percentage points above its true incremental share.

On the public demo data, incremental contribution is Media channel 1 22.1 percent of revenue (18.1 to 28.1); Media channel 2 7.1 percent of revenue (6.6 to 7.7).

Reallocating the same budget gains 2.5 percent of current media contribution (10th percentile -0.8 percent); the shift is not recommended under the decision rule.

Contribution profit is the north star, not revenue: a channel that returns less
than the breakeven return on ad spend destroys margin however large its revenue
looks. Customer acquisition cost is fully loaded or it is fiction. Attribution is a
hypothesis until it has been tested against something outside the platform's own
reporting. Platform-reported numbers are claims, not measurements, because every
platform counts the conversions it can see and credits itself for demand that would
have arrived anyway. The model below is built to test those claims.

## Method

- Data: weekly spend per channel and revenue. Layer P is a synthetic advertiser with 156 weeks and five channels (TV, Radio, Print, Paid Search, Paid Social) whose true parameters are written to data/synthetic/truth.json; Layer R is the public example dataset shipped with pymc-marketing (see data/README.md). Public demo data; a real-data swap-in is planned.
- Adstock: geometric carry-over per channel, so this week's spend keeps working in the following weeks with a decay rate the model estimates.
- Saturation: a Hill curve per channel on the adstocked spend, with a half-saturation point and a slope, so returns diminish as spend grows.
- Seasonality and controls: a linear trend, two yearly Fourier pairs, and one control (a public-holiday week indicator on Layer P, an event week on Layer R).
- Priors: weakly informative and identical across channels, on scaled data, so that the estimates come from the data and not from a prior that knows the answer. Each prior and its reasoning is in the model docstring.
- Sampler: NUTS (nutpie), 2 chains, 1000 tuning and 1000 draws per chain, target acceptance 0.9, raised to 0.99 by the recorded ladder after divergences.
- Diagnostics: R-hat below 1.01, effective sample size above 400, zero divergences; written to diagnostics.json next to every fit.
- Holdout protocol: fit on the first 130 weeks, forecast the rest with the actual spend, and report MAPE and 90 percent interval coverage against a seasonal-naive and a ridge-regression baseline.

## Results: holdout forecast against two baselines

Layer P, synthetic data, 26 holdout weeks:

| Model | MAPE | 90 percent interval coverage |
|---|---|---|
| Seasonal naive | 9.6 percent | 92 percent |
| Ridge regression | 4.7 percent | 92 percent |
| Bayesian MMM | 3.0 percent | 85 percent |

The MMM has the lowest point error here. Its case does not rest on that: the baselines say nothing about which channel earned the revenue, and the MMM's interval coverage is what makes its uncertainty usable.

Layer R, public demo data, 26 holdout weeks:

| Model | MAPE | 90 percent interval coverage |
|---|---|---|
| Seasonal naive | 19.3 percent | 96 percent |
| Ridge regression | 7.5 percent | 92 percent |
| Bayesian MMM | 4.4 percent | 85 percent |

The MMM has the lowest point error here. Its case does not rest on that: the baselines say nothing about which channel earned the revenue, and the MMM's interval coverage is what makes its uncertainty usable.

## Decision

Same total weekly budget, reallocated (spend in the data's index-scaled units, contribution in revenue units per week):

| Channel | Current weekly spend | Recommended | Change | Marginal ROAS at current (90 percent interval) | Marginal ROAS at recommended (90 percent interval) | Contribution at recommended (90 percent interval) |
|---|---|---|---|---|---|---|
| Media channel 1 | 0.309 | 0.381 | +23 percent | 4410.01 (3917.70 to 4999.54) | 3556.96 (3176.76 to 3976.50) | 1581 (1372 to 1893) |
| Media channel 2 | 0.162 | 0.090 | -45 percent | 3090.80 (2583.99 to 4191.74) | 3551.57 (2333.15 to 4847.97) | 317 (120 to 652) |

Gain from the reallocation: median 2.5 percent of current media contribution, 10th percentile -0.8 percent, probability of a loss 14.6 percent. Hold: the rule is not met.

Decision rule: Shift budget toward a channel only while the lower bound of its marginal ROAS 90 percent interval stays above the breakeven ROAS, and only if the 10th percentile of the reallocation gain is positive. Breakeven ROAS is 2.50 at a contribution margin of 40 percent (an assumption stated in the config).

With 25 percent more budget the gain is a median 23.3 percent of current contribution; where the extra budget goes, and how likely that call is wrong, is in reports/layer_d/next_200k.md.

![Distribution of the gain from reallocation](reports/layer_d/reallocation_gain.png)

## Reproduce

```
uv sync
uv run python -m ambo.run layer_p
uv run python -m ambo.run layer_r && uv run python -m ambo.run layer_d
```

## Limitations

- Layer R runs on public demo data with two unnamed, index-scaled media channels, so its shares and ratios are meaningful and its money amounts are not. No Austrian client data was used; a real-data swap-in is planned.
- One model form (geometric adstock, Hill saturation, additive baseline) is assumed; recovery on Layer P shows the sampler recovers that form, not that reality has it.
- Weekly national data cannot separate channels whose spend moves together; the intervals widen accordingly and the optimiser stays inside the bounds set in the config.
- The optimiser assumes response curves hold at new spend levels, competitors do not react, and a constant weekly spend reaches its steady state.

## What I would do differently with production data

- Geo-level weekly data, so that regional variation in spend identifies the response
  curves instead of time alone.
- Calibration against lift tests: geo experiments or holdouts on at least one channel,
  used as priors or as a check on the incremental estimates.
- Media cost inflation, so that spend is converted to reach before modelling and a
  price rise is not mistaken for saturation.
- Competitor spend as a control, since a rival's campaign moves the baseline.
- Longer history for seasonality: three full years at minimum, with the calendar of
  promotions written down rather than reconstructed.
- Data-quality gates before modelling: gapless weeks, spend reconciled to invoices,
  platform exports reconciled to the ad accounts, and outliers explained before they
  enter the fit.

## Status

Built layers: Layer P (synthetic truth and parameter recovery), Layer R (public demo data), Layer D (budget optimiser and decision rule). The package and Layer P are on main; Layers R and D are on the build/ambo branch pending review. Date: 2026-09-15.
