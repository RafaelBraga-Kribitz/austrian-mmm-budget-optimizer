# Dashboard

Four pages on the CSV feed in `reports/exports/`, in two renderings of the same page set:

| Rendering | Path | Needs |
|---|---|---|
| Power BI Project (PBIP: TMDL model, PBIR report) | `dashboards/MMM.pbip` | Power BI Desktop on Windows |
| Static HTML twin | `dashboards/html/index.html` | any browser, offline |

The page set, German subtitles, visuals, column notes and captions are specified in
[docs/dashboard_handoff.md](../docs/dashboard_handoff.md); that document stays the
specification for both renderings. Why a text project and a twin instead of a `.pbix`:
[ADR-010](../docs/adr/ADR-010_dashboard-pbip-and-html-twin.md).

Every number on every page is read from `reports/exports/*.csv`, which
`scripts/export_dashboard.py` writes from the committed Layer P, R and D artifacts.
Nothing is typed by hand. Amounts are in the money units of the public demo dataset
(Robyn), not euros; no page formats them with a currency sign.

| Page | German subtitle | Files |
|---|---|---|
| 1 Recommendation | Wohin der naechste Euro geht | `recommendation_allocation.csv`, `recommendation_gain.csv` |
| 2 Contributions | Was jeder Kanal beitraegt | `contributions_weekly.csv`, `roas_summary.csv` |
| 3 Response curves | Wo die Saettigung beginnt | `response_curves.csv` |
| 4 Proof | Der Beweis auf bekannter Wahrheit | `proof_*.csv`, `holdout_metrics.csv` |

## Open in Power BI Desktop

The project was written and tested as text; it has not yet been opened in Power BI
Desktop. This is the human step.

1. Use a Power BI Desktop release from November 2025 or later (the report uses PBIR
   schemas report 3.0.0, page 2.0.0, visual container 2.4.0). If your release does not
   save PBIP with PBIR by default, enable under *File > Options and settings > Options >
   Preview features*: *Power BI Project (.pbip) save option*, *Store semantic model using
   TMDL format* and *Store reports using enhanced metadata format (PBIR)*; restart.
2. Clone the repository and open `dashboards/MMM.pbip`.
3. Set the path: *Transform data > Edit parameters > ExportsPath* to the absolute path of
   `reports\exports\` in your clone (for example
   `C:\repos\austrian-mmm-budget-optimizer\reports\exports\`). It is the only path in the
   model.
4. *Refresh*. Ten tables load from CSV, `Calendar` is calculated from
   `ContributionsWeekly`. Numbers are parsed with the en-US culture, so a German Windows
   locale does not turn decimal points into thousands separators.
5. Check page 1 with the scenario slicer on *Same total budget*: the median gain,
   10th percentile gain, probability of a loss and breakeven ROAS cards must equal the
   README Decision section (`a_gain_median`, `a_gain_p10`, `a_p_neg`, `a_breakeven` in
   `reports/readme_values.json`). Page 4: *True parameters inside 90% interval* must equal
   `p_covered` of `p_total`; the Paid Search *Platform over true* cell must equal the
   README's over-credit (`p_search_over`). Page 2: TV's revenue share must equal
   `r_share_TV`.
6. Look at every page for what text cannot guarantee: series colours (current spend
   grey, recommendation blue, Baseline grey at the bottom of the stack), slicer defaults,
   axis titles, the offline rows of the attribution-gap table showing "no platform
   report", and the tab order in *View > Selection > Tab order*.
7. Save. Desktop then owns the PBIR and TMDL files; commit its changes as an ordinary
   diff and run the tests below.
8. Screenshot each page at 1280 by 720 to `docs/assets/dashboard_p1.png` to
   `dashboard_p4.png` (SPEC-07 RB-406) and add them to the README template next to the
   HTML-twin screenshots.

`.pbi/localSettings.json` and `.pbi/cache.abf` are ignored by `.gitignore`; never commit
them.

## The semantic model

| Table | Source | Role |
|---|---|---|
| `Gain` | `recommendation_gain.csv` | One row per scenario; the scenario dimension (`scenario_label`, sorted by `scenario_order`) |
| `Allocation` | `recommendation_allocation.csv` | Current and recommended spend, marginal ROAS with intervals, `held_label` |
| `Channel` | `contributions_weekly.csv` (distinct channels) | Layer R channel dimension, Baseline first |
| `ContributionsWeekly` | `contributions_weekly.csv` | Weekly decomposition, long format |
| `Calendar` | calculated from `ContributionsWeekly[week_start]` | Marked date table (`dataCategory: Time`, key `Date`) |
| `RoasSummary` | `roas_summary.csv` | ROAS and revenue share with intervals |
| `ResponseCurves` | `response_curves.csv` | Layer R curves with bands |
| `ParameterRecovery`, `ProofResponseCurves`, `AttributionGap`, `SamplerGates`, `Holdout` | `proof_*.csv`, `holdout_metrics.csv` | Page 4, standalone tables |

Relationships are single-direction, many-to-one: `Allocation` to `Gain` (scenario) and to
`Channel`; `ContributionsWeekly`, `RoasSummary` and `ResponseCurves` to `Channel`;
`ContributionsWeekly[week_start]` to `Calendar[Date]`. Implicit measures are off; every
measure has a format string (text measures excepted), a display folder and a `///`
description that says what it means and, where it should equal a README figure, which
one. Per-channel measures such as marginal ROAS return blank on totals rather than a sum
that means nothing; scenario measures return blank unless exactly one scenario is
selected. Offline channels' undefined platform-over-true ratio is shown as "no platform
report", never as zero, and their rows are kept.

Theme: `MMM.Report/StaticResources/RegisteredResources/BragaMMM.json`, chrome from the
Braga design system tokens (light), data colours its five categorical colours.
Accessibility: every data visual has a title and alt text; tab order runs left to
right, top to bottom; decorative rules are out of the tab order.

## The HTML twin

```bash
uv run python scripts/build_dashboard_html.py          # writes dashboards/html/index.html
uv run python scripts/build_dashboard_html.py --check  # exits 1 if the committed page is stale
```

Open `dashboards/html/index.html` in a browser; it makes no network request. Sources:
`dashboards/html/src/` (`template.html`, `dashboard.css`, `dashboard.js`); the script
inlines them with the ten CSV files as JSON. Tabs follow the URL hash
(`#recommendation`, `#contributions`, `#response-curves`, `#proof`) and the arrow keys;
each chart is one keyboard stop whose arrow keys step through the data points, and each
has a data table. Light and dark follow the system setting.

Screenshots of the twin are in `docs/assets/dashboard_html_p1.png` to
`dashboard_html_p4.png` (1440 pixel wide window, light mode, one per page).

## Checks

```bash
uv run pytest tests/test_dashboard_pbip.py tests/test_dashboard_html.py
uv run python scripts/validate_pbip.py --schemas /path/to/json-schemas
```

The first test file checks the report against the model (every visual field exists in
the TMDL, every relationship joins existing columns, every export file is loaded through
`ExportsPath`, pages and German subtitles match the handoff, alt text and tab order, the
theme). The second checks the twin (deterministic, equal to the committed file, headline
figures equal to the CSV files, no network resources, captions verbatim).
`validate_pbip.py` validates every PBIR and PBIP JSON file against the schema it
declares, from a local clone of github.com/microsoft/json-schemas (the path is the
folder that contains `fabric/`); without `--schemas` it prints that it skipped and exits
0.

## Refresh after a pipeline run

1. `uv run python -m ambo.run layer_p`, `layer_r`, `layer_d` (or keep the committed
   artifacts).
2. `uv run python scripts/export_dashboard.py`.
3. `uv run python scripts/build_dashboard_html.py`.
4. In Power BI Desktop: *Refresh*.
