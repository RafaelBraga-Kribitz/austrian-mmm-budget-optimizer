# Requirements: Austrian MMM & Budget Optimizer (AMBO)

**Defined:** 2026-08-04 (from doc ingest of `PROJECT_CHARTER.md`)
**Core Value:** A reviewer can verify from git history alone that the model recovered known truth before it touched real data, and that the priors preceded the results.

## About these IDs

All 25 IDs below are carried **verbatim** from `.planning/intel/requirements.md`, which derived
them from `PROJECT_CHARTER.md` (the sole PRD in the ingest corpus). The Charter's own
identifiers (Q1–Q4, DL-1…DL-10, E-1…E-5, O-1…O-8, M0–M7, R-1…R-9) are preserved inside each
entry.

**These IDs are load-bearing and must not be renamed.** Two mechanisms depend on them:
`docs/EXECUTION_BLUEPRINT/13_TRACEABILITY_MATRIX.md`, and the coding standard requiring every
public function's docstring to carry `Implements: <REQ-IDs>`.

> **Count discrepancy.** `.planning/intel/SYNTHESIS.md` reports 24 `REQ-*` entries;
> `.planning/intel/requirements.md` actually contains **25**. The synthesis header is off by
> one — its own enumeration lists 4 + 10 + 5 + 6 = 25. All 25 are carried here and all 25 are
> mapped. No requirement was dropped.

Full acceptance criteria (with SPEC-tier expansions) live in `.planning/intel/requirements.md`.
The summaries below are abridged; the intel file wins on any difference.

## v1 Requirements

### Analytical questions (Charter §1.1)

- [ ] **REQ-q1-truth-recovery**: The model recovers known truth — ROAS, adstock half-lives,
      saturation, optimal allocation — within stated tolerances, including a zero-effect
      channel it must NOT hallucinate. *(Q1; accepted when all SPEC-05 §3 gates are green per
      scenario at their scenario-specific thresholds.)*

- [ ] **REQ-q2-real-incremental-roas**: Determine what drives the real client's revenue —
      incremental ROAS and response curves per channel, with credible intervals. *(Q2)*

- [ ] **REQ-q3-optimal-allocation**: At the same total budget, determine the optimal allocation
      and the expected contribution gain versus the historical allocation. *(Q3; extrapolation
      guards visibly active.)*

- [ ] **REQ-q4-attribution-gap**: Quantify the gap between platform-reported ROAS and MMM
      incremental ROAS, per channel. *(Q4)*

### Deliverables (Charter §4)

- [ ] **REQ-dl1-reproducible-pipeline**: A fresh clone reproduces every Layer P artifact
      bit-for-bit-in-tolerance without any private inputs; Layer R artifacts reproduce given
      the private drop. *(DL-1; operative probe is 11_ACCEPTANCE_CRITERIA §4. RESOLVED
      2026-08-04 — Charter DL-1 corrected to point at that probe, and `exports/*.csv` is now
      committed-by-design per EB-081, so the export comparison is executable. INFO 2 and
      WARNING 5 closed.)*

- [ ] **REQ-dl2-recovery-report**: `reports/recovery/RECOVERY_REPORT.md` — generated, not
      hand-edited, gate table all-green, VR-304 verdict section present, SSOT `recovery_pass_*`
      true. *(DL-2, answers Q1)*

- [ ] **REQ-dl3-layer-r-posterior-report**: Layer R posterior report — ROAS table with 90%
      HDIs, response curves, contribution decomposition; MD-080 additivity test green; every
      ROAS row has HDI columns populated. *(DL-3, answers Q2)*

- [ ] **REQ-dl4-optimizer-output**: `allocation_scenarios.csv` with 3 budget rows × channels
      and a binding-flags column; SSOT `expected_gain_pct(_lo/_hi)` and
      `expected_gain_aeur_annual`; DC-302 caption on every gain artifact; bounds column shows
      1.3× guard values. *(DL-4, answers Q3)*

- [ ] **REQ-dl5-attribution-gap-artifact**: `attribution_gap.csv` + `dc_attribution_gap.png` +
      RB-203; DC-502 ordering gate green on S-B; per-channel P(platform > MMM) column present.
      *(DL-5, answers Q4)*

- [ ] **REQ-dl6-priors-as-deliverable**: `docs/PRIOR_ELICITATION.md` as a first-class
      deliverable — every prior with a ≥100-character marketing rationale, frozen pre-fit;
      MD-061 doc-lint green; MD-062 freeze statement with commit hash; GB-502 ancestry check
      green. *(DL-6)*

- [ ] **REQ-dl7-dashboard**: Power BI `dashboards/ambo.pbix` per SPEC-07 §4 plus
      `docs/assets/dashboard_p1..p4.png`; pages match RB-401…404 content lists; rebuild
      instructions verified. *(DL-7, human-executed)*

- [x] **REQ-dl8-quality**: `make test` green; ruff + mypy clean; CI green including smoke-fit;
      coverage ≥ 80% of `src/`. Release-commit CI run shows all six jobs green with coverage
      report linked. *(DL-8)*

- [ ] **REQ-dl9-honesty**: `LIMITATIONS.md` covering at least the SPEC-09 §6 nine-item list
      (9/9 mapping table); anonymization protocol published without secrets; no absolute real €
      anywhere; leak scan full-mode green log. *(DL-9)*

- [ ] **REQ-dl10-readme**: README leads with the recovery result and the Layer R answer;
      structure test green; RB-201 then RB-202 embedded in that order. *(DL-10)*

### Epistemic rules (Charter §3)

- [ ] **REQ-e1-tagged-headline-numbers**: Every headline number carries its epistemic tag
      (GROUND-TRUTH / REAL-ANON / MODELED / CALIBRATED) in README and exec summary; SSOT rows
      carry a `tag` column. *(E-1)*

- [ ] **REQ-e2-layer-order**: Layer R results are published ONLY if Layer P gates passed — a
      CI-checked fact. The commit adding `RECOVERY_REPORT.md` with all M3 gates green is a git
      ancestor of any commit adding `data/posteriors/R*.parquet` or `reports/model/diag_R.md`.
      *(E-2, GB-501)*

- [ ] **REQ-e3-prior-freeze**: `config/priors_real.yaml` is committed BEFORE any Layer R fit
      artifact exists, with no post-freeze modification; freeze commit hash in SSOT
      `prior_freeze_commit`. *(E-3, GB-502)*

- [ ] **REQ-e4-numeric-ssot**: `reports/NUMERIC_SSOT.md` is generated only by
      `scripts/generate_ssot.py` and is the sole source for numbers in README and exec summary;
      CI-gated by `scripts/check_ssot_consistency.py`; whitelist entries carry per-entry
      justification comments. *(E-4, GB-303, RB-601)*

- [ ] **REQ-e5-anonymized-euro-caption**: Anonymized euros are always written a€ and every
      Layer R artifact carries the fixed caption; single caption source in
      `ambo/report/captions.py`, grep-test enforces single occurrence in `src/`. *(E-5, GB-102)*

### Scope and delivery discipline (Charter §2, §5, §6, §7)

- [ ] **REQ-scope-in**: Eight in-scope workstreams (simulator, agency pipeline, warehouse,
      Bayesian MMM, validation, decision layer, reporting, engineering + light governance),
      each tracing to its owning SPEC and to at least one WBS task. *(§2.1)*

- [x] **REQ-scope-out**: O-1…O-8 excluded. Forbidden-deps test enforces O-3 at dependency
      level; single CI workflow with no cron enforces O-7; scope walls otherwise. *(§2.2)*

- [ ] **REQ-grain-and-windows**: ISO weeks (Mon–Sun, Europe/Vienna) everywhere. Layer P per
      SPEC-01 §5 (S-A 156, S-B 104, S-C 78 weeks). Layer R is whatever the agency data covers,
      expected 52–104 weeks, exact window documented at intake and reported with every Layer R
      result; AG-050 drops partial edge weeks; AG-060 requires ≥ 52 weeks; `layer_r_weeks` in
      SSOT. *(§2.3; note the Charter's "156 per scenario" is superseded by SPEC-01 §5 — see
      INGEST-CONFLICTS INFO 1.)*

- [x] **REQ-milestones**: Eight milestones M0–M7, each exiting only on its named gate. Effort
      budget M0 0.5d, M1 1.5d, M2 2d, M3 2.5d, M4 1.5d, M5 2d, M6 2d, M7 2d. Any milestone
      exceeding 2× its budget triggers a stop plus an ADR. *(§5)*

- [ ] **REQ-degradation-path**: If permission falls through, the repo remains shippable as
      Layers P+D on scenario S-B, the attribution-gap module runs on simulated platform bias
      (SIM-060), and the README uses its alternate framing. Decided by ADR **by end of M4, not
      later**; no gray-zone processing while waiting; RB §6.1 alternate framing pre-drafted.
      *(§7, AG-002, risk R-1)*

- [ ] **REQ-risk-register**: Nine charter-level risks R-1…R-9 remain authoritative, each with a
      named mitigation binding to a SPEC mechanism, expanded per milestone in
      12_RISK_REGISTER.md with mitigation/fallback/detection triads, reviewed at each phase
      entry. *(§6)*

## v2 Requirements

None. The Charter defines a single v1.0 release and an explicit out-of-scope list rather than
a deferred backlog. Charter O-1 ("geo-experiments / lift tests / MMM calibration against
experiments") is the one item the Charter itself names as future work — "the correct next step
for a real engagement" — to be mentioned in one line of the README's Future Work, not built.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Geo-experiments, lift tests, experiment calibration (O-1) | Correct next step for a real engagement; no client budget in a portfolio build |
| Daily-grain MMM, intra-week effects, auction/bid modeling (O-2) | Grain is ISO weeks everywhere; daily grain would change every spec |
| Robyn / Meridian / lightweight_mmm / model averaging (O-3) | Exactly two implementations exist: raw PyMC primary, pymc-marketing cross-check. Enforced by forbidden-deps test |
| Customer-level modeling, funnel analytics, creative analysis (O-4) | Different data, different project |
| Hosted apps (O-5) | What-if deliverable is Power BI + exported scenario tables. No web frontend exists |
| Multi-KPI modeling (O-6) | Revenue only; orders reported descriptively |
| Automated data refresh crons (O-7) | No live feed and no network access. CI is the only automation; enforced by single workflow, no cron |
| Competitor spend estimation, share-of-voice purchases (O-8) | Unavailable and unnecessary |
| Audit-finding registry, session handouts, re-verification matrix (GB §8) | Deliberately non-existent per SPEC-09; the governance showpieces are four scripts a reviewer can run |

## Traceability

Each requirement has exactly one **owning** phase — the phase that delivers it and whose exit
gate proves it. Several also have **contributing** phases that build a necessary precondition.
This mapping is the roadmap-level view; the task-level view lives in
`docs/EXECUTION_BLUEPRINT/13_TRACEABILITY_MATRIX.md`.

| Requirement | Owning Phase | Also touches | Status |
|-------------|--------------|--------------|--------|
| REQ-q1-truth-recovery | Phase 5 | Phases 2, 3, 4 | Pending |
| REQ-q2-real-incremental-roas | Phase 7 | Phases 4, 6 | Pending |
| REQ-q3-optimal-allocation | Phase 8 | — | Pending |
| REQ-q4-attribution-gap | Phase 8 | — | Pending |
| REQ-dl1-reproducible-pipeline | Phase 9 | Phases 3, 5 | Pending |
| REQ-dl2-recovery-report | Phase 5 | — | Pending |
| REQ-dl3-layer-r-posterior-report | Phase 7 | — | Pending |
| REQ-dl4-optimizer-output | Phase 8 | — | Pending |
| REQ-dl5-attribution-gap-artifact | Phase 8 | — | Pending |
| REQ-dl6-priors-as-deliverable | Phase 6 | Phase 4 (elicit.py, T-308) | Pending |
| REQ-dl7-dashboard | Phase 9 | — | Pending |
| REQ-dl8-quality | Phase 1 | Phase 9 (release-commit audit) | Complete |
| REQ-dl9-honesty | Phase 9 | Phase 6 (permission, leak scan) | Pending |
| REQ-dl10-readme | Phase 9 | — | Pending |
| REQ-e1-tagged-headline-numbers | Phase 9 | Phase 5 (SSOT `tag` column) | Pending |
| REQ-e2-layer-order | Phase 5 | Phase 7 (first exercise) | Pending |
| REQ-e3-prior-freeze | Phase 6 | Phase 7 (enforced) | Pending |
| REQ-e4-numeric-ssot | Phase 5 | Phases 7, 9 | Pending |
| REQ-e5-anonymized-euro-caption | Phase 9 | Phase 8 (DC-302 caption) | Pending |
| REQ-scope-in | Phase 1 | standing | Pending |
| REQ-scope-out | Phase 1 | standing | Complete |
| REQ-grain-and-windows | Phase 6 | Phases 2, 3 (Layer P grain) | Pending |
| REQ-milestones | Phase 1 | standing (all phases) | Complete |
| REQ-degradation-path | Phase 6 | Phase 9 (alternate framing) | Pending |
| REQ-risk-register | Phase 1 | standing (reviewed at each phase entry) | Pending |

**Coverage:**

- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

### Coverage note — Phases 2, 3, 4 own no Charter requirement

Phases 2 (simulator), 3 (warehouse), and 4 (MMM on S-A) have **contributing** requirements but
no **owning** one. This is a real property of the corpus, not an oversight:

The Charter's requirement set is deliverable-level. The Layer P build chain is instrumental to
REQ-q1 / REQ-dl2 rather than being a Charter deliverable in its own right — you cannot ship
"a simulator" to a marketing leader, you ship the recovery result it makes possible.

Those three phases are contracted at the **SPEC-tier requirement families**, which are the
binding technical contract and live in `.planning/intel/constraints.md`:

| Phase | Governing SPEC families | Exit gates |
|-------|------------------------|-----------|
| Phase 2 | SIM-001…004, SIM-030/031, SIM-060/061, SPEC-01 §2/§4/§5/§8 | SIM-070…075 |
| Phase 3 | AD-001/002, AD-020, AD-030, AD-050 | AD-040…043 |
| Phase 4 | MD-001…003, MD-020…022, MD-030, MD-040/041, MD-050/051, MD-080…083 | MD-070…072 |

No new `REQ-*` IDs were invented to paper over this. Inventing them would break the stable-ID
contract that `13_TRACEABILITY_MATRIX.md` and the `Implements:` docstring convention depend on.

---
*Requirements defined: 2026-08-04*
*Last updated: 2026-08-04 after roadmap creation (traceability populated)*
