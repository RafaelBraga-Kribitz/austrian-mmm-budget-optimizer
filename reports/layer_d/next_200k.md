# If the advertiser gets 25 percent more budget, where does it go?

Numbers come from the Layer R posterior (reports/layer_r/posterior_draws.csv) through python -m ambo.run layer_d. The EUR 200k question maps onto the 25 percent scenario once euro-denominated data replaces the public demo data; the demo data's spend is index scaled, so this note gives shares and probabilities, not euro amounts.

Current weekly budget: 0.471 spend units. Scenario budget: 0.589 (extra 0.118).

## Where the extra budget goes

- Media channel 1: 92 percent of the increase (from 0.309 to 0.418 per week); marginal ROAS at the new spend 3170.69 (90 percent interval 2827.24 to 3535.27).
- Media channel 2: 8 percent of the increase (from 0.162 to 0.171 per week); marginal ROAS at the new spend 3049.36 (90 percent interval 2457.35 to 4166.59).

## How likely is this call wrong?

- Probability that the extra budget adds less than nothing: 0.0 percent.
- Probability that Media channel 1 is not the channel with the highest marginal return at the new allocation: 43.6 percent.
- Breakeven ROAS at a contribution margin of 40%: 2.50. Channels held at current spend by the rule: none.
- Verdict under the decision rule: recommend.

## Decision rule

Shift budget toward a channel only while the lower bound of its marginal ROAS 90 percent interval stays above the breakeven ROAS, and only if the 10th percentile of the reallocation gain is positive.
