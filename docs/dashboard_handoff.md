# Dashboard handoff

This is the specification of the dashboard: pages, subtitles, visuals, column notes and
captions. The build is in [dashboards/](../dashboards/README.md): a Power BI Project
(`dashboards/MMM.pbip`, TMDL model and PBIR report) and a static HTML twin
(`dashboards/html/index.html`), both on the CSV feed under `reports/exports/`
(ADR-010). The feed is written by `uv run python scripts/export_dashboard.py`
after every pipeline run. No page reads the model; every page reads a file. Money is in
the dataset's units until real client data replaces the public demo file.

## Pages

| Page | German subtitle | Files | Visuals |
|------|-----------------|-------|---------|
| 1 Recommendation | Wohin der naechste Euro geht | `recommendation_allocation.csv`, `recommendation_gain.csv` | Clustered bars, current versus recommended spend per channel and scenario; a gain card with median and 10th percentile; a marginal ROAS table with the interval columns; a note that channels marked `held_by_rule` were held by the breakeven gate |
| 2 Contributions | Was jeder Kanal beitraegt | `contributions_weekly.csv`, `roas_summary.csv` | Stacked area of the weekly decomposition by channel (`median`), with the baseline row at the bottom; a channel slicer; a ROAS matrix with `roas_lo` and `roas_hi` as interval columns |
| 3 Response curves | Wo die Saettigung beginnt | `response_curves.csv` | One line chart per channel: `median` against `spend`, `lo` and `hi` as a band, a vertical marker at `current_spend`; the curve ends at 1.5 times the largest observed weekly spend |
| 4 Proof | Der Beweis auf bekannter Wahrheit | `proof_parameter_recovery.csv`, `proof_response_curves.csv`, `proof_attribution_gap.csv`, `proof_sampler_gates.csv`, `holdout_metrics.csv` | Dot-and-interval plot of `true` against `median`, `lo`, `hi`; the true curve (`true`) over the band per channel; a dumbbell of `platform_share` against `true_share`; the sampler gate table; the holdout table for both layers |

## Column notes

- Intervals are the 5th to 95th percentile of the posterior draws (`lo`, `hi`), a
  90 percent interval, everywhere.
- `recommendation_allocation.csv` has one block per scenario: `same_total`,
  `plus_25_percent`, and `plus_extra_budget` (the yearly extra budget from the config
  spread over 52 weeks). `share_current` and `share_recommended` are shares of the
  scenario's total.
- `contributions_weekly.csv` is long: one row per week and channel, plus a `Baseline`
  row per week without an interval.
- `proof_attribution_gap.csv` (a copy of `reports/layer_p/attribution_gap.csv`) leaves
  `platform_over_true_ratio` and `platform_over_true_pct` empty for TV, Radio and Print
  by design. Offline channels receive no platform credit (`platform_reported_total` is
  0), so the ratio is undefined. Show these cells as blank or "no platform report",
  not as zero, and do not filter the rows out: their `gap_pp` is the under-credit.
- `proof_sampler_gates.csv` records the last attempt of the recorded ladder per fit;
  `attempts` says how many fits it took to pass.

## Captions to copy verbatim

- Money: "Amounts are in the money units of the public demo dataset (Robyn), whose
  currency is not named; shares, ratios and the breakeven test are meaningful, the
  amounts are not euros." Replace with the anonymisation caption from
  `docs/specs/SPEC-02_agency_data_pipeline.md` once client data is in.
- Gain: "In-sample counterfactual under the fitted model; assumes response curves hold
  and competitors do not react. No channel moves more than fifty percent from its
  current spend."

## Rebuild

1. `uv run python -m ambo.run layer_p`, `layer_r`, `layer_d` (or reuse the committed
   artifacts under `reports/`).
2. `uv run python scripts/export_dashboard.py`.
3. `uv run python scripts/build_dashboard_html.py` rebuilds the HTML twin.
4. In Power BI Desktop, open `dashboards/MMM.pbip`, point the `ExportsPath` parameter at
   `reports/exports/` and refresh; the full checklist is in
   [dashboards/README.md](../dashboards/README.md).
5. Power BI screenshots are not committed yet: the project has not been opened in
   Desktop (STATUS, open items). The HTML twin's screenshots are
   `docs/assets/dashboard_html_p1.png` to `dashboard_html_p4.png`.
