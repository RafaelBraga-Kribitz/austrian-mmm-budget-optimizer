# Lessons learned: Austrian MMM and Budget Optimizer

Evaluation: [economic-evaluation.md](economic-evaluation.md).

## Expectations against actuals (as of 2026-10-30)

| Item | Expected (evaluation) | Actual | Evidence |
|---|---|---|---|
| Effort | 36 h central (18 to 54 h); charter budget 14 days | 36 h by the commit-day convention; session-span check 17 h; no time log | cost basis v1.1, hours table; `PROJECT_CHARTER.md` §5 |
| Total cost | €3,175 central, with 3 years of maintenance and 12 h data intake | €1,944 build to date; maintenance and intake not incurred | same |
| Technical performance | A posterior that tells a profitable move from an adverse one | Known-truth test and public demo fit done. On demo data the same-budget shift gains a median 15.1 % of media contribution (10th percentile 8.8 %); no draw of 500 loses. Demo units are not euros | `reports/layer_d/decision.json` |
| Adoption | Inside f = 0.35 | None: no client data has been processed | `docs/adr/ADR-009_spec-sections-not-built.md` |
| Operational outcome | Budget moved by an advertiser | Unmeasured | none |
| Attributable value | €6.9k gross expected over 3 years | Unmeasured | none |

## Lessons

**L-AMBO-1. Secure written data permission before the build when value depends on one client's data.** Scope: client-data analytics. Charter risk R-1 (client data falls through, Medium) happened: the intake was never built and no client data arrived. The evaluation's adoption term, not the model, was the binding risk. Evidence: `docs/adr/ADR-009_spec-sections-not-built.md`; `LIMITATIONS.md` §3. Date: 2026-10-30.

**L-AMBO-2. Value the decision, not the forecast error.** Scope: models that support budget moves. On the demo holdout, ridge regression had lower error than the MMM (MAPE 5.1 % against 7.9 %; MAPE = mean absolute percentage error), yet only the MMM answers which channel should get the next euro. Evidence: `reports/layer_r/holdout_metrics.csv`; `README.md`, "Validation". Date: 2026-10-30.
