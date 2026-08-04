# Requirements (synthesized intel)

Source tier: PRD. Exactly one PRD in the ingest set: `PROJECT_CHARTER.md`
(Charter v1.0, 2026-07-18). All requirement IDs below are derived (`REQ-{slug}`);
the Charter's own identifiers (Q1-Q4, DL-1..10, E-1..5, O-1..8, M0-M7, R-1..9) are
preserved verbatim inside each entry.

Note on precedence: per the configured ordering (ADR > SPEC > PRD > DOC) and the
absence of any ADR, SPEC-tier documents outrank this PRD on contradiction. The
Charter itself claims the opposite ("Charter beats specs") — see
`.planning/INGEST-CONFLICTS.md` WARNING 1.

---

## REQ-q1-truth-recovery
- source: PROJECT_CHARTER.md §1.1 (Q1)
- description: The model must recover known truth — ROAS, adstock half-lives, saturation, optimal allocation — within stated tolerances, including a zero-effect channel it must NOT hallucinate.
- acceptance: SPEC-05 recovery suite run on SPEC-01 scenarios; all SPEC-05 §3 gates green per scenario at their scenario-specific thresholds.
- scope: Layer P validation, credibility argument, deliverable DL-2

## REQ-q2-real-incremental-roas
- source: PROJECT_CHARTER.md §1.1 (Q2)
- description: Determine what drives the real client's revenue — incremental ROAS and response curves per channel, with credible intervals.
- acceptance: SPEC-04 model fitted on SPEC-02 data; Layer R posterior report with ROAS table (90% HDIs), response curves, contribution decomposition.
- scope: Layer R answer, deliverable DL-3

## REQ-q3-optimal-allocation
- source: PROJECT_CHARTER.md §1.1 (Q3)
- description: At the same total budget, determine the optimal allocation and the expected contribution gain versus the historical allocation.
- acceptance: SPEC-06 optimizer output showing optimal vs historical allocation, expected gain in a€ and %, with extrapolation guards visibly active.
- scope: decision layer, deliverable DL-4

## REQ-q4-attribution-gap
- source: PROJECT_CHARTER.md §1.1 (Q4)
- description: Quantify the gap between platform-reported ROAS and MMM incremental ROAS, per channel.
- acceptance: SPEC-06 attribution-gap module output — table plus chart, platform ROAS vs MMM ROAS per channel.
- scope: decision layer, deliverable DL-5

## REQ-dl1-reproducible-pipeline
- source: PROJECT_CHARTER.md §4 (DL-1)
- description: A reproducible pipeline: fresh clone plus `make setup && make all` reproduces every Layer P artifact bit-for-bit-in-tolerance without any private inputs; Layer R artifacts reproduce given the private data drop.
- acceptance: MCMC tolerance doctrine per SPEC-05 §7 applies; private drop per SPEC-02 §3. (Expanded and partially superseded by SPEC-tier 11_ACCEPTANCE_CRITERIA §4 DL-1 probe protocol — see conflicts INFO 2 and WARNING 5.)
- scope: reproducibility, release gate

## REQ-dl2-recovery-report
- source: PROJECT_CHARTER.md §4 (DL-2)
- description: Answer to Q1 delivered as `reports/recovery/RECOVERY_REPORT.md`.
- acceptance: All SPEC-05 §3 gates green, including the zero-effect channel test; report generated (not hand-edited), gate table all-green, VR-304 verdict section present, SSOT `recovery_pass_*` true.
- scope: Layer P credibility artifact

## REQ-dl3-layer-r-posterior-report
- source: PROJECT_CHARTER.md §4 (DL-3)
- description: Answer to Q2 delivered as a Layer R posterior report.
- acceptance: ROAS table with 90% HDIs, response curves, contribution decomposition per SPEC-04 §8; additivity test MD-080 green; every ROAS row has HDI columns populated.
- scope: Layer R reporting

## REQ-dl4-optimizer-output
- source: PROJECT_CHARTER.md §4 (DL-4)
- description: Answer to Q3 delivered as optimizer output.
- acceptance: `allocation_scenarios.csv` with 3 budget rows × channels and a binding-flags column; SSOT `expected_gain_pct(_lo/_hi)` plus `expected_gain_aeur_annual`; DC-302 caption on every gain artifact; bounds column shows 1.3× guard values.
- scope: decision layer output, extrapolation guards

## REQ-dl5-attribution-gap-artifact
- source: PROJECT_CHARTER.md §4 (DL-5)
- description: Answer to Q4 delivered as attribution-gap table plus chart.
- acceptance: `attribution_gap.csv` plus `dc_attribution_gap.png` plus RB-203; DC-502 ordering gate green on S-B; per-channel P(platform>MMM) column present.
- scope: decision layer output

## REQ-dl6-priors-as-deliverable
- source: PROJECT_CHARTER.md §4 (DL-6)
- description: `docs/PRIOR_ELICITATION.md` treated as a first-class deliverable — every prior with a marketing rationale, frozen pre-fit.
- acceptance: Rationale >= 100 characters per prior (SPEC-04 §6); MD-061 doc-lint green (fields present, no boilerplate, YAML matches stated ranges); MD-062 freeze statement with commit hash; GB-502 ancestry check green.
- scope: marketing-domain portfolio signal, epistemic rule E-3

## REQ-dl7-dashboard
- source: PROJECT_CHARTER.md §4 (DL-7)
- description: Power BI dashboard `dashboards/ambo.pbix` per SPEC-07 §4, plus screenshots.
- acceptance: `.pbix` committed; `docs/assets/dashboard_p1..p4.png` exist; pages match RB-401..404 content lists; rebuild instructions verified.
- scope: reporting, human-executed task

## REQ-dl8-quality
- source: PROJECT_CHARTER.md §4 (DL-8)
- description: Engineering quality bar for release.
- acceptance: `make test` green; ruff plus mypy clean; CI green including smoke-fit; coverage >= 80% of `src/`. Release-commit CI run shows all six jobs green with coverage report linked.
- scope: engineering gate, CI

## REQ-dl9-honesty
- source: PROJECT_CHARTER.md §4 (DL-9)
- description: `LIMITATIONS.md` covering at least the SPEC-09 §6 list; anonymization protocol published without secrets; no absolute real € anywhere.
- acceptance: LIMITATIONS mapping table 9/9 items; SPEC-02 plus DATA_PERMISSION plus AG-070 paragraph in README; leak scan full-mode green log.
- scope: governance, privacy, portfolio credibility

## REQ-dl10-readme
- source: PROJECT_CHARTER.md §4 (DL-10)
- description: README leads with the recovery result and the Layer R answer, per SPEC-07 §6.
- acceptance: README structure test green; first content section contains recovery verdict plus gain number with epistemic tags; RB-201 and RB-202 embedded in that order.
- scope: reader-facing entry point

## REQ-e1-tagged-headline-numbers
- source: PROJECT_CHARTER.md §3 (E-1)
- description: Every headline number carries its epistemic tag (GROUND-TRUTH / REAL-ANON / MODELED / CALIBRATED) in README and exec summary.
- acceptance: SSOT rows carry a `tag` column (GB-103); README/exec numbers carry tags inline; reviewed at the M7 sweep.
- scope: epistemic framework

## REQ-e2-layer-order
- source: PROJECT_CHARTER.md §3 (E-2)
- description: Layer R results are published ONLY if Layer P gates passed — a CI-checked fact, not a promise.
- acceptance: GB-501 — the commit adding `RECOVERY_REPORT.md` with all M3 gates green is a git ancestor of any commit adding `data/posteriors/R*.parquet` or `reports/model/diag_R.md`; `scripts/check_layer_order.py` green in CI job 5.
- scope: build order, credibility architecture

## REQ-e3-prior-freeze
- source: PROJECT_CHARTER.md §3 (E-3)
- description: `config/priors_real.yaml` (Layer R priors plus rationales) is committed BEFORE any Layer R fit artifact exists — priors are marketing judgments and must demonstrably precede results.
- acceptance: GB-502 git-ancestry check plus no post-freeze modification of the frozen files; freeze commit hash in SSOT `prior_freeze_commit`.
- scope: epistemic integrity, M4 exit

## REQ-e4-numeric-ssot
- source: PROJECT_CHARTER.md §3 (E-4)
- description: `reports/NUMERIC_SSOT.md` is generated only by `scripts/generate_ssot.py` and is the sole source for numbers in README and exec summary.
- acceptance: CI-gated by `scripts/check_ssot_consistency.py` (GB-303); whitelist entries carry per-entry justification comments; RB-601 — no number outside SSOT.
- scope: number integrity, anti-drift

## REQ-e5-anonymized-euro-caption
- source: PROJECT_CHARTER.md §3 (E-5)
- description: Anonymized euros are always written a€ and every Layer R artifact carries the fixed caption stating that values are rescaled by undisclosed factors, ratios and shapes preserved, absolute levels masked.
- acceptance: Single caption source in `ambo/report/captions.py`; grep-test enforces single occurrence in `src/` (GB-102).
- scope: anonymization disclosure, reporting

## REQ-scope-in
- source: PROJECT_CHARTER.md §2.1
- description: Eight in-scope workstreams — ground-truth simulator (3 scenarios), agency-data pipeline with permission gate and dual-factor rescaling, DuckDB+dbt warehouse at weekly grain, Bayesian MMM in raw PyMC with elicited priors, validation with recovery gates and false-positive control, decision layer with constrained optimizer and attribution gap, reporting with exec summary/charts/Power BI/SSOT, and engineering with uv/Python 3.12/Makefile/pytest/ruff/CI plus light governance.
- acceptance: Each workstream traces to its owning SPEC (SPEC-01..09) and to at least one WBS task in the traceability matrix.
- scope: project boundary

## REQ-scope-out
- source: PROJECT_CHARTER.md §2.2 (O-1..O-8)
- description: Explicitly out of scope — geo-experiments/lift tests/experiment calibration (O-1); daily-grain MMM, intra-week effects, auction/bid modeling (O-2); additional MMM frameworks or model averaging (O-3); customer-level modeling, funnel analytics, creative analysis (O-4); hosted apps (O-5); multi-KPI modeling, revenue only (O-6); automated data refresh crons (O-7); competitor spend estimation and share-of-voice purchases (O-8).
- acceptance: Forbidden-deps test enforces O-3 at dependency level (EB-030); single CI workflow with no cron enforces O-7; review plus scope walls otherwise.
- scope: anti-scope-creep guard rails

## REQ-grain-and-windows
- source: PROJECT_CHARTER.md §2.3
- description: Grain is ISO weeks (Mon-Sun, Europe/Vienna civil dates); everything weekly. Layer P is 156 weeks per scenario with S-C at 78, synthetic dates 2022-W01 to 2024-W52. Layer R is whatever the agency data covers, expected 52-104 weeks, with the exact window documented at intake and reported with every Layer R result.
- acceptance: AG-050 weekly aggregation with partial edge weeks dropped; AG-060 window length >= 52 weeks; `layer_r_weeks` in SSOT. NOTE: the Layer P sentence conflicts with SPEC-01 §5, which sets S-B to 104 weeks — SPEC wins (see conflicts INFO 1).
- scope: temporal grain, dataset sizing

## REQ-milestones
- source: PROJECT_CHARTER.md §5
- description: Eight milestones M0-M7 — bootstrap, simulator plus 3 scenarios plus truth files, raw-PyMC model fitted on S-A, full recovery suite plus OLS baseline plus cross-check, agency data intake plus prior freeze, Layer R fit plus sensitivity, decision layer, reporting and release. Effort budget M0 0.5d, M1 1.5d, M2 2d, M3 2.5d, M4 1.5d (human-heavy), M5 2d, M6 2d, M7 2d.
- acceptance: Each milestone exits only on its named gate (SPEC-01 §7, SPEC-04 §7, SPEC-05 §3-§6, SPEC-02 §6, SPEC-06 §7, DL-1..DL-10). Any milestone exceeding 2× its effort budget triggers a stop plus ADR.
- scope: delivery sequencing, effort tripwire

## REQ-degradation-path
- source: PROJECT_CHARTER.md §7, docs/SPEC-02_agency_data_pipeline.md (AG-002)
- description: If Layer R becomes impossible (permission falls through), the repo remains shippable as Layers P+D on scenario S-B, the attribution-gap module runs on simulated platform-reporting bias (SIM-060 known over-credit), and the README uses its alternate framing.
- acceptance: Decision made via ADR by end of M4, not later; no gray-zone processing while waiting; RB §6.1 alternate framing pre-drafted so the outcome cannot tempt improvisation.
- scope: risk R-1 mitigation, release contingency

## REQ-risk-register
- source: PROJECT_CHARTER.md §6 (R-1..R-9)
- description: Nine charter-level risks remain authoritative — permission failure, weak identification on 52-104 real weeks, spend/demand collinearity, brand-search endogeneity, MCMC non-reproducibility across platforms, anonymization leak, sampler divergences, scope creep, and imperfect promo-calendar reconstruction.
- acceptance: Each risk has a named mitigation binding to a SPEC mechanism; expanded per milestone in 12_RISK_REGISTER.md with mitigation/fallback/detection triads.
- scope: risk management baseline
