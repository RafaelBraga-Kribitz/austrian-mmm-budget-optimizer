# If the advertiser gets 200,000 more per year, where does it go?

Numbers come from the Layer R posterior (reports/layer_r/posterior_draws.csv) through python -m ambo.run layer_d.

The extra budget is spread evenly over 52 weeks (3,846 per week on top of the current 69,851 per week, a 5.5 percent increase). Money is in the dataset's units; the same rule applies to euros once euro-denominated data is used.

## Where the extra budget goes

- TV: 87 percent of the increase (from 14,844 to 23,083 per week); marginal ROAS at the new spend 5.79 (90 percent interval 3.28 to 8.87).
- Out-of-home: 0 percent of the increase (from 43,218 to 37,634 per week); marginal ROAS at the new spend 0.84 (90 percent interval 0.11 to 1.89).
- Print: 0 percent of the increase (from 3,729 to 3,729 per week); marginal ROAS at the new spend 7.81 (90 percent interval 1.22 to 16.01).
- Facebook: 13 percent of the increase (from 2,146 to 3,337 per week); marginal ROAS at the new spend 15.97 (90 percent interval 3.27 to 39.18).
- Search: 0 percent of the increase (from 5,916 to 5,916 per week); marginal ROAS at the new spend 7.68 (90 percent interval 0.89 to 25.55).

## How likely is this call wrong?

- Probability that the extra budget adds less than nothing: 0.0 percent.
- Probability that Facebook is not the channel with the highest marginal return at the new allocation: 35.2 percent.
- Breakeven ROAS at a contribution margin of 40 percent: 2.50. Channels held at current spend by the rule: Print, Search.
- Verdict under the decision rule: recommend.

## Decision rule

Shift budget toward a channel only while the lower bound of its marginal ROAS 90 percent interval stays above the breakeven ROAS, and only if the 10th percentile of the reallocation gain is positive.
