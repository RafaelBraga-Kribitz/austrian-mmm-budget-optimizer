# Decision memo

For the marketing lead. Austrian media mix and budget optimizer (AMBO), demonstration advertiser.

## 1. The decision this memo supports

Approve a same-budget change to the weekly media mix: more TV and Facebook, less Out-of-home, and no change to Print or Search.

## 2. Recommendation

Make the change. Media contribution is expected to rise by 15.1 percent, and at the 10th percentile the gain is still 8.8 percent.

## 3. Evidence

- Out-of-home weekly spend falls 20 percent in the recommended mix (`reports/layer_d/reallocation_table.csv`).
- The chance the change loses money is 0.0 percent (`reports/layer_d/decision.json`).
- On a synthetic advertiser with known truth, the platform report credited Paid Search with 45 percent more revenue than it really added (`reports/layer_p/attribution_gap.csv`).

## 4. Chart

![Gain from reallocating the same total budget, as a percent of current weekly media contribution](reports/layer_d/reallocation_gain.png){width=5.4in}

Main results chart: `reports/layer_d/reallocation_gain.png`. The dashed line is the 15.1 percent median; the solid line is the 8.8 percent tenth percentile. The mass of the chart sits above zero.

## 5. What we do not know

- The demonstration data is a public simulated dataset in unnamed money units. Shares and percent gains are usable; the cash amounts are not euros.
- No live advertiser, and no Austrian client file, has been fitted. Competitors may change spend in response.
- The recommended weeks assume the fitted curves still hold at the new spend levels; that has not been tested with a lift experiment.

## 6. Next step and its cost

Apply this mix on the demonstration budget until a live euro file exists. Extra media cost is 0; the weekly total stays 69851 in the dataset's units (`reports/layer_d/decision.json`).[^1]

[^1]: Estimates come from a Bayesian media mix model.

## Numbers in this memo

- 15.1 percent — `reports/layer_d/decision.json` (same-budget gain as a percent of current contribution, 15.105…), also `reports/readme_values.json`
- 8.8 percent — `reports/layer_d/decision.json` (10th percentile, 8.800…), also `reports/readme_values.json`
- 20 percent — `reports/layer_d/reallocation_table.csv` (Out-of-home change −19.655…), rounded as in `reports/readme_values.json`
- 0.0 percent — `reports/layer_d/decision.json` (probability the gain is negative)
- 45 percent — `reports/layer_p/attribution_gap.csv` (Paid Search platform figure over truth, 45.131…)
- 0 extra and 69851 weekly total — `reports/layer_d/decision.json` (recommended total equals current total, 69851.435…)
