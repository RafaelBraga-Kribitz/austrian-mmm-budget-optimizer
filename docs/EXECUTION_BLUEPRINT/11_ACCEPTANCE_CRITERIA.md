# 11 — ACCEPTANCE CRITERIA, DEFINITION OF READY, DEFINITION OF DONE

## 1. Principles

Acceptance criteria are **objective**: each is verifiable by a command, a test name,
a file inspection, or a numeric threshold. Words like "clean", "good", "reasonable"
are banned from criteria. Task-specific criteria live on the task cards
([02_WBS.md](02_WBS.md)); this document defines the global templates every task
inherits and the expansion of the Charter's DL-1..10 into checkable form.

## 2. Global Definition of Ready (DoR)

A task may start only when ALL of:

1. **Dependencies merged.** Every task listed under "Depends on" is closed and its
   PR merged to `main` (or explicitly co-scheduled in the same milestone PR).
2. **Spec basis identified.** The implementer has read the REQ IDs on the task's
   traceability line in the actual SPEC (not only this blueprint's paraphrase).
3. **Contract known.** The module contract in [03_MODULES.md](03_MODULES.md) for
   every file to be touched has been read; if the task requires a new public API,
   the contract addition is drafted first (contract-first rule).
4. **Decisions resolved.** Any BP-D decision the task exercises is either accepted
   as default or overridden by the human (recorded in BUILD_LOG/ADR) — never
   silently re-decided.
5. **Inputs exist.** All input artifacts (data files, posteriors, seeds, configs)
   exist at their canonical paths on `main`.
6. **Approvals present** (only where the card says [HUMAN]): the human is available
   for the parts AGENTS §2 assigns to them.
7. **Environment sane.** `make lint && make test` green on `main` before branching
   — never start a task on a red base.

## 3. Global Definition of Done (DoD)

A task is done only when ALL of:

1. **Code complete** per the task's objective and the module contract; no partial
   feature behind a comment.
2. **Tests passing:** new tests for the task's REQ IDs in the same commit (W-1);
   full `make test` green; coverage not reduced.
3. **Gates green:** every gate the task's validation section names, plus all
   standing CI gates ([10 §2](10_VALIDATION_GATES.md)).
4. **Documentation updated:** docstrings with `Implements:` tags; module contract
   doc updated if the public API changed; BUILD_LOG line if the task closed a
   decision or measured a runtime.
5. **Artifacts regenerated:** any committed artifact affected by the change
   (SSOT, reports, exports, posteriors metadata) regenerated in the same PR
   (freshness rule GB §4).
6. **No TODOs, no warnings:** zero TODO/FIXME in touched files; pytest output
   warning-free (or the warning suppressed with an inline justification).
7. **No duplicated logic:** the [09 §A-8](09_ANTI_PATTERNS.md) single-home rules
   hold (captions, back-transform, thresholds, formats).
8. **No violated invariants:** guard tests green (import independence, forbidden
   deps, leak scan, layer order).
9. **Reviewed:** at least one review pass against
   [07_QUALITY_STANDARDS.md](07_QUALITY_STANDARDS.md) +
   [09_ANTI_PATTERNS.md](09_ANTI_PATTERNS.md), stated explicitly in the PR.
10. **Acceptance criteria ticked** on the task card, each with evidence.

## 4. Deliverable acceptance — Charter DL-1..10 expanded

| DL | Charter wording (condensed) | Objective verification |
|----|------------------------------|------------------------|
| DL-1 | Fresh clone reproduces Layer P bit-for-bit-in-tolerance without private inputs; Layer R given the drop | Probe protocol: clean clone → `make setup && make transform && make recover && make decide && make ssot && make export && make report` using ONLY committed artifacts (no fits) → zero errors; then compare regenerated reports/exports to committed versions: text artifacts byte-equal, MCMC-derived numbers within VR-702 bands. Log attached to release PR. Separately: `make simulate && make validate-sim` byte-reproduces `data/synthetic/` |
| DL-2 | RECOVERY_REPORT with all SPEC-05 §3 gates green incl. zero-effect | `reports/recovery/RECOVERY_REPORT.md` exists, generated (not hand-edited — regeneration diff empty), gate table all-green, VR-304 verdict section present; SSOT `recovery_pass_*` true |
| DL-3 | Layer R posterior report: ROAS + 90% HDIs, response curves, decomposition | `diag_R.md` + ROAS table (mean/5/50/95/P(<1) per MD-081) + `response_curves.csv` rows for R + contributions export; additivity test MD-080 green; every ROAS row has HDI columns populated |
| DL-4 | Optimizer output with gain + guards visibly active | `allocation_scenarios.csv` (3 budget rows × channels, binding flags column present); SSOT `expected_gain_pct(_lo/_hi)` + `expected_gain_aeur_annual`; DC-302 caption present on every gain artifact; bounds column shows 1.3× guard values |
| DL-5 | Attribution-gap table + chart | `attribution_gap.csv` + `dc_attribution_gap.png` + RB-203; DC-502 gate green (S-B); per-channel P(platform>MMM) column present |
| DL-6 | Priors as deliverable, frozen pre-fit | PRIOR_ELICITATION.md passes MD-061 lint (fields, ≥100-char rationales, YAML match); MD-062 freeze statement with hash; GB-502 check green |
| DL-7 | Power BI + screenshots | `dashboards/ambo.pbix` committed; `docs/assets/dashboard_p1..p4.png` exist; pages match RB-401..404 content lists (human review vs checklist); rebuild instructions verified |
| DL-8 | Quality: tests, lint, CI, coverage ≥ 80% | CI run on release commit: all six jobs green; coverage report ≥ 80% linked |
| DL-9 | Honesty: LIMITATIONS ⊇ GB §6; protocol published; no absolute real € | LIMITATIONS mapping table (9/9 items); SPEC-02 + DATA_PERMISSION + AG-070 paragraph in README; leak scan full-mode green log |
| DL-10 | README leads with recovery + Layer R answer per RB §6 | README structure test green; first content section contains recovery verdict + gain number with tags; RB-201/202 embedded in order |

## 5. Milestone acceptance

A milestone is accepted when: its phase exit criteria ([01_PHASES.md](01_PHASES.md))
hold, its checklist ([06_CHECKLISTS.md](06_CHECKLISTS.md)) is fully ticked with
evidence in the PR, its gate classes ([10_VALIDATION_GATES.md](10_VALIDATION_GATES.md))
are green, and the PR is merged to `main` without history rewriting. There is no
"accepted with exceptions" state — an exception is an ADR, merged first.
