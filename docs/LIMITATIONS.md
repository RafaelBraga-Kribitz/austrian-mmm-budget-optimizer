# LIMITATIONS

This file is the honesty layer (Charter DL-9, SPEC-09 §6). Read it before the
recovery table.

## What the model is

A weekly, additive-in-level Bayesian MMM: geometric adstock with MD-020
normalised weights, Hill saturation, linear trend, yearly Fourier seasonality,
and Austrian calendar dummies (promo, Advent, January dip) plus a public-holiday
indicator. It is identified on a **disclosed** synthetic advertiser (Layer P). It
is not a causal experiment, not a lift test, and not a claim about a live
client.

## What it is not

- **Not Layer R.** There is no real agency drop in this repository. Inventing one
  would violate A-5. Charter §7 applies: the showcase is Layers P + D on
  synthetic truth (ADR-012). Absolute euros here are simulator euros, not a
  client's.
- **Not a six-channel SPEC-01 replica.** STATUS D-05 / ADR-012 use five channels
  (TV, Radio, Print, Paid Search, Paid Social). There is no brand-search line, so
  the optimiser may move every channel. That is a documented deviation, not a
  hidden one.
- **Not S-B / S-C recovery.** Collinear spend and a zero-effect channel are
  implemented and unit-tested in the simulator. The reported fit is the 156-week
  clean series.
- **Not a guarantee that K and s are recovered as points.** Hill slope is
  fixed at 1 (MD-073 rung 4 / ADR-013). Half-sat K and β still trade off.
  Gates are on ROAS, curve *shape* at observed spend, half-life *direction*,
  and media share (T-5).
- **Not platform-calibrated.** Simulated dashboards over-credit by construction
  (φ, θ in `truth.json`). The attribution-gap chart treats those numbers as the
  object of study (T-8).
- **Not an out-of-sample budget experiment.** The optimiser is an in-sample
  counterfactual at constant-spend steady state, with a hard 1.3× historical max
  cap. Competitors do not react. Offline channels are moved in weekly-equivalent
  euros; real TV/print/radio buying is flighted.
- **Not cross-platform MCMC identical.** Seeded PyMC/nutpie is deterministic on
  one machine and version, not across platforms (T-6). Reports regenerate from a
  saved posterior; they are not checksummed draw-for-draw.
- **Not pymc-marketing, Robyn, or Meridian.** Charter O-3. A pymc-marketing
  cross-check was out of this build's scope (STATUS PR 43 triage).
- **Not a hosted app or a Power BI file.** Dashboard screenshots remain a human
  task (Charter M7).

## Known structural tensions

- Spend that follows the demand calendar confounds seasonality and media (T-4).
  The clean Layer P series turns that confound *off* so identification is
  possible; reality will look more like S-B.
- Simulator adstock is an infinite recursion; the model is a truncated
  convolution of length 8 with unit-sum weights. Agreement is evidence, not a
  tautology (MD-020, T-3). At constant spend the model’s steady-state adstock
  equals weekly spend (DC-201).
- Inputs are scaled (T-1). Every reported euro is back-transformed through
  `ScaleFactors`. If a chart ever shows a number without its 90% HDI, the chart
  is wrong (A-7).
