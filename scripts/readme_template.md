# Austrian MMM and Budget Optimizer

For one advertiser, which channels contributed incrementally, how far off were
platform-reported numbers, and what does a reallocation gain?

![{{headline_alt}}]({{headline_chart}})

{{headline_lines}}

Contribution profit is the north star, not revenue: a channel that returns less
than the breakeven return on ad spend destroys margin however large its revenue
looks. Customer acquisition cost is fully loaded or it is fiction. Attribution is a
hypothesis until it has been tested against something outside the platform's own
reporting. Platform-reported numbers are claims, not measurements, because every
platform counts the conversions it can see and credits itself for demand that would
have arrived anyway. The model below is built to test those claims.

## Method

{{method_bullets}}

## Results: holdout forecast against two baselines

{{holdout_section}}

## Decision

{{decision_section}}

## Reproduce

```
uv sync
uv run python -m ambo.run layer_p
uv run python -m ambo.run layer_r && uv run python -m ambo.run layer_d
```

## Limitations

{{limitations}}

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

{{status_line}}
