# SPEC-07 — Reporting, Dashboard, README (AMBO)

Requirement IDs: `RB-xxx`.

---

## 1. Artifact inventory

| Artifact | Path | Produced by |
|----------|------|-------------|
| Executive summary | `reports/EXEC_SUMMARY.md` | hand-written, SSOT numbers only |
| Recovery report | `reports/recovery/RECOVERY_REPORT.md` | generated (SPEC-05 §8) |
| Prior elicitation | `docs/PRIOR_ELICITATION.md` | human + agent, frozen M4 |
| Executive charts | `reports/executive_charts/*.png` | `make report` |
| Numeric SSOT | `reports/NUMERIC_SSOT.md` | `scripts/generate_ssot.py` |
| BI exports | `exports/*.csv` | `scripts/export_marts.py` |
| Power BI | `dashboards/ambo.pbix` + `docs/assets/dashboard_p*.png` | manual (human) |
| README / LIMITATIONS | repo root | hand-written per §6 / SPEC-09 §6 |

## 2. Executive charts (exactly five)

- RB-201 `01_where_next_euro.png` — THE money chart: marginal-ROAS ladder (DC-601)
  as horizontal bars with HDI whiskers, best channel highlighted, extrapolation-guard
  note. Title: "Where the next advertising euro works hardest (Client A)".
- RB-202 `02_truth_recovery.png` — S-B true-vs-posterior ROAS dot plot (the
  credibility chart; caption: "Before trusting the model on real data, we made it
  pass a test where the truth is known").
- RB-203 `03_attribution_gap.png` — Layer R dumbbell (DC-503 restyled executive).
- RB-204 `04_contribution_waterfall.png` — Layer R average-week decomposition: base,
  seasonality, promo, each channel (posterior means; additive; a€).
- RB-205 `05_prior_value.png` — VR-501 forest plot restyled: "what 8 years of agency
  experience does to the estimates" (elicited vs flat priors, Layer R).

## 3. Chart data flow

- RB-301: Exec charts read only exports/SSOT-backed frames; a pytest recomputes
  RB-201's bars from `allocation_scenarios.csv`/posterior parquet and asserts match.
- RB-302: All charts regenerate WITHOUT sampling (VR-703).

## 4. Power BI dashboard (manual, specified)

Source: the six `exports/` CSVs (AD-050). Pages:

- RB-401 Page 1 "Empfehlung" (Recommendation): optimal vs historical allocation
  (clustered bars), expected-gain card with HDI, next-euro table, guard-rail note.
- RB-402 Page 2 "Beiträge" (Contributions): stacked area weekly decomposition,
  channel slicer, ROAS matrix with HDI columns.
- RB-403 Page 3 "Kurven" (Response curves): line charts per channel from
  `response_curves.csv` with HDI bands, current-spend marker, 1.3× guard line.
- RB-404 Page 4 "Beweis" (Proof): recovery dot plot from `roas_summary.csv`
  (truth column where present), gate-status table, attribution-gap dumbbell.
- RB-405: German one-sentence subtitle per page; a€ explained in a footer text box
  (caption wording from `captions.py`, copied verbatim).
- RB-406: Screenshots → `docs/assets/dashboard_p1..p4.png`; `.pbix` committed;
  rebuild instructions in `dashboards/README.md`.

## 5. `reports/EXEC_SUMMARY.md` (≤ 2 pages, structure mandatory)

1. **The answer** (≤ 4 sentences): expected gain at same budget (a€ + %, HDI); the
   next-euro channel; the largest attribution gap; the recovery verdict in one clause.
2. **Why trust this** (1 paragraph): the three-layer architecture; recovery gates
   passed; priors frozen before fitting (with commit hash).
3. **What each channel does** (table: spend share, contribution share, ROAS + HDI,
   marginal ROAS; one sentence per notable channel).
4. **Platform numbers vs reality** (1 paragraph + RB-203 reference).
5. **Recommendation** (1 paragraph): reallocation summary + the two caveat sentences
   (DC-302 caption + short-data note). A number attached to every claim.
6. **What would change this** (≤ 3 bullets, from LIMITATIONS).

## 6. README.md structure (order mandatory)

1. H1 + one-sentence definition naming Bayesian MMM, a real anonymized Austrian
   advertiser, and PyMC.
2. Headline question blockquote → answer paragraph: recovery verdict (tag MODELED,
   on GROUND-TRUTH data), expected gain + HDI, biggest attribution gap, each with
   epistemic tag.
3. RB-201 embedded, then RB-202 (money first, credibility second).
4. "What is real vs. synthetic vs. modeled" table (GROUND-TRUTH / REAL-ANON /
   MODELED / CALIBRATED, one row each with one-line meaning).
5. The three-layer architecture explainer (5 sentences + the git-history claim: model
   proven on disclosed truth BEFORE seeing real data; priors frozen before fitting —
   both verifiable via `scripts/check_layer_order.py`, linked).
6. Results: ROAS table, allocation table, attribution-gap table.
7. Dashboard screenshots.
8. Reproduce: ≤ 5 commands; note Layer P + all reports reproduce with zero private
   inputs; Layer R refit requires the private drop (by design).
9. Anonymization protocol summary (AG-070 wording) + link to SPEC-02.
10. Architecture sketch; data statement; LIMITATIONS link; license; author block
    (same format as sibling repos).

### 6.1 Alternate framing (Charter §7 degradation)

If Layer R dies: §2's answer paragraph swaps to the pre-written variant: "a fully
validated MMM + optimizer demonstrated end-to-end on disclosed ground truth — built
to be pointed at any advertiser's data" and §4/§6 drop REAL-ANON rows. Both variants
live in this spec so the outcome can't tempt improvisation.

- RB-601: No number outside SSOT (CI-checked); stack talk first appears in README §8.

## 7. Chart standards

Identical to sibling repos: matplotlib ≥ 3.8 Agg, 12×6 in, dpi 150, Okabe-Ito palette
via `ambo/report/style.py` (fixed channel colors across ALL charts), formatter module
`ambo/report/format.py` ("a€1.2 M", ROAS "3.4×", percentages 1 decimal — tested).
Every chart: business-English title, unit-labeled axes, source note bottom-left
("Source: anonymized client data / disclosed simulation / own model"), epistemic tag
bottom-right. `captions.py` is the single home of: the a€ caption (Charter E-5), the
DC-302 counterfactual caption, the AG-070 anonymization paragraph — grep-enforced
single occurrence in `src/`.
