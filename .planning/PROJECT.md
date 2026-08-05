# Austrian MMM & Budget Optimizer (AMBO)

## What This Is

A Bayesian Marketing Mix Model in raw PyMC for a real, anonymized Austrian advertiser, built
in three layers: prove the model recovers **known** truth on a disclosed synthetic
data-generating process (Layer P), only then fit real agency data under priors frozen before
fitting (Layer R), then answer "where does the next euro go?" with a constrained budget
optimizer and a platform-vs-MMM attribution-gap analysis (Layer D). Written for Austrian
marketing leaders and analytics hiring managers who know adstock and saturation by effect,
not by name — and for technical reviewers who will read the priors and the diagnostics.

This is a solo portfolio project with a single implementer. Everything runs locally on ~4
cores with **zero network access anywhere** (EB-070); there is no live API of any kind.

## Core Value

A reviewer can verify **from git history alone** that the model recovered known truth before
it ever touched real data, and that the priors were written before the results existed — and
then read an HDI-tagged answer to where the next advertising euro works hardest.

If the numbers are right but that ordering cannot be checked by running a script, the project
has failed at the only thing that distinguishes it from every other MMM demo.

## Requirements

Full requirement text with acceptance criteria: `.planning/REQUIREMENTS.md`.
Source intel (verbatim, with Charter refs preserved): `.planning/intel/requirements.md`.

### Validated

Validated in Phase 1: Repository Foundation — five delivery-discipline requirements, each
proven by an executable mechanism rather than by review:

- [x] **REQ-dl8-quality** — the six-job CI workflow, the `ruff`/`mypy` lint chain, and the
      pre-commit toolchain, all green on Ubuntu and Windows.
- [x] **REQ-scope-in** — `docs/MODULE_CONTRACTS.md` is the contract of record; the repo-layout
      and import-independence guards enforce it.
- [x] **REQ-scope-out** — the forbidden-deps and no-requests guards, plus `scripts/leak_scan.py`.
- [x] **REQ-milestones** — the milestone-branch topology (D-11) and the PR template's six
      judgment checkboxes.
- [x] **REQ-risk-register** — `docs/RISK_REGISTER.md`, seeded with R-1…R-9 verbatim from the
      Charter plus R-10…R-13 from build findings.

### Active

Twenty of the 25 v1 requirements remain active. Grouped by Charter origin:

- [ ] **Q1–Q4** — the four analytical questions (truth recovery, real incremental ROAS,
      optimal allocation, attribution gap)
- [ ] **DL-1…DL-10** — the ten deliverables, each with an objective acceptance criterion
- [ ] **E-1…E-5** — the five epistemic rules (tagged numbers, layer order, prior freeze,
      numeric SSOT, a€ caption)
- [x] **Scope / grain / milestones / degradation / risk** — validated above by Phase 1, except
      the grain and degradation-path requirements, which Phases 2–6 exercise.

### Out of Scope

Charter §2.2, O-1…O-8. Two of these are enforced mechanically rather than by review:

- **Geo-experiments, lift tests, experiment calibration** (O-1) — the correct next step for a
  real engagement, not for a portfolio build with no client budget.
- **Daily grain, intra-week effects, auction/bid modeling** (O-2) — the grain is ISO weeks
  everywhere; daily grain would change every spec.
- **Additional MMM frameworks or model averaging** (O-3) — exactly two implementations exist,
  raw PyMC (primary) and pymc-marketing (cross-check only). *Enforced by the forbidden-deps
  test, which is **import-scoped, not tree-scoped**: it blocks what `ambo`'s own code imports
  (robyn, lightweight_mmm, prophet, sklearn), not every package name in the resolved
  dependency tree. Ratified in Phase 1 — `scikit-learn` is legitimately present transitively
  via `pymc-marketing` → `pymc-extras`, and a tree-scoped guard would false-positive on the
  Charter-sanctioned cross-check implementation.*
- **Customer-level modeling, funnel analytics, creative analysis** (O-4) — different data,
  different project.
- **Hosted apps** (O-5) — the what-if deliverable is Power BI plus exported scenario tables.
  There is no web frontend in this project.
- **Multi-KPI modeling** (O-6) — revenue only; orders are reported descriptively.
- **Automated data refresh crons** (O-7) — there is no live feed. *Enforced by a single CI
  workflow with no cron.*
- **Competitor spend estimation, share-of-voice purchases** (O-8) — unavailable and
  unnecessary.

## Context

**Provenance.** This project was bootstrapped by `/gsd-ingest-docs` from an existing
24-document corpus, not from a blank slate. The corpus is: `PROJECT_CHARTER.md` (1 PRD),
`docs/SPEC-01..09` plus `docs/EXECUTION_BLUEPRINT/02..12` (20 SPEC-tier), and
`docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md`, `01_PHASES.md`, `13_TRACEABILITY_MATRIX.md`
(3 DOC-tier). The roadmap's nine phases mirror the blueprint's P0–P8 exactly; re-deriving a
parallel decomposition would orphan the 46-task WBS numbering (T-001…T-806) and the
traceability matrix.

**Repository state.** Git repo on branch `master` with **zero commits**. `AGENTS.md`,
`PROJECT_CHARTER.md`, `docs/`, and `.planning/` are untracked. The blueprint's T-001 assumes
git-init-and-baseline-commit is the very first action and assumes branch `main`. Both
discrepancies are recorded in STATE.md and must be settled in Phase 1.

**The external blocker is a data drop, not an API.** The tasking that commissioned the
blueprint mentioned an ENTSO-E API token; that is a template artifact from a sibling energy
project. AMBO has no ENTSO-E dependency and no network access at all. The structurally
equivalent blocker is the **private agency data drop plus written permission**, needed at M4
(Phase 6). "Drop-blocked vs drop-independent" replaces "API-blocked vs non-API": Phases 1–5
are entirely drop-independent, as are the intake codebase, the whole decision layer developed
against Layer P, and all reporting infrastructure.

**Audience calibration.** Every artifact must be readable by a marketing leader. The
prior-elicitation document is as much a deliverable as the model.

## Constraints

Full technical contract: `.planning/intel/constraints.md` (76 entries across 20 SPEC
sources). Do not restate it — read it. Only the constraints that shape **phase sequencing**
are listed here.

- **Dependency**: `fct_mmm_input` is the sole model input (AD-030) — `ambo/model/` reads only
  the mart via `ambo/common/db.py`, never CSVs. This makes the warehouse a hard prerequisite
  of the model, which is why Phase 3 exists as its own phase even though the Charter's
  milestone table folds it into M2.
- **Build order**: Layer P gates precede all Layer R publication (E-2, GB-501) — the commit
  adding `RECOVERY_REPORT.md` with green M3 gates must be a git **ancestor** of any Layer R
  posterior. Phase 5 is therefore an unlock gate for Phases 6–9, enforced by
  `scripts/check_layer_order.py` in CI, not by promise.
- **Build order**: Priors freeze before fitting (E-3, GB-502) — `config/priors_real.yaml` plus
  `docs/PRIOR_ELICITATION.md` commit before any Layer R fit artifact exists, verified by git
  ancestry plus a no-post-freeze-modification check.
- **Git policy**: History is append-only (EB-082). No force-push, no rebase of pushed history,
  no amends, ever — both ancestry proofs depend on trustworthy history. A red layer-order gate
  is never fixed by editing history; it means the process was violated. Merge commits, not
  squash, because task-level commits are part of the evidence trail.
- **Tech stack**: Python 3.12 + `uv`; DuckDB + `dbt-duckdb`; `pymc>=5.15,<6` raw PyMC as the
  primary model. `pymc_marketing` may be imported **only** in `src/ambo/validate/crosscheck.py`.
  Any new dependency requires an ADR, without exception.
- **Environment**: Zero network in any test or runtime (EB-070). The only env var is
  `AMBO_PRIVATE_DROP`, a path whose contents are secret and which only
  `intake/standardize.py` may read.
- **Compute**: ~14 full-budget fits at 15–35 min each on 4 cores. Fits are explicit `make`
  targets, never run in CI, never implicit in `make all`. Cumulative compute exceeding 2× the
  ledger estimate is an effort-budget event.
- **Effort tripwire**: Any phase exceeding 2× its Charter §5 day budget triggers a stop and an
  ADR analyzing why, before continuing.
- **Privacy**: Only stage-2 anonymization outputs may enter the repo. A leak-scan hit is a
  STOP with human-led remediation — and remediation is never a history rewrite.

## Key Decisions

**There are zero ratified decisions in this project.** `docs/ADR/` does not exist. It is
referenced by SPEC-09 GB-201 (path template `docs/ADR/ADR-NNN_short-title.md`) and GB-202
(five pre-planned slots ADR-001…ADR-005), and is scheduled for creation by task **T-012** in
Phase 1. Until then, nothing below is locked.

<decisions>
status: ALL UNRATIFIED — no ADR exists in this repository as of 2026-08-04

The eight items below are the project's operative design stance. They are asserted directly
by SPEC-tier documents and should be implemented as written, but none has been ratified by an
ADR and each remains formally `status: proposed`. Full text: `.planning/intel/decisions.md`
Group A.

- UNRATIFIED — **Additive-in-level, not log** (MD-001). The MMM is additive in revenue level
  because contributions must decompose additively for the waterfall and the optimizer.
- UNRATIFIED — **Raw PyMC primary, pymc-marketing cross-check only** (MD-003, VR-602, O-3).
  Import-guarded to `validate/crosscheck.py`.
- UNRATIFIED — **Simulator and model share no transform code** (SIM-003, A-1). Neither may
  import the other in either direction; each implements its own adstock/Hill with independent
  tests. The single sanctioned exception is shared CONFIG (`season_windows.csv`), never shared
  transform code. Sharing code collapses the entire recovery argument.
- UNRATIFIED — **Deliberate parameterization mismatch is a feature** (MD-020). Simulator uses
  raw geometric recursion, model uses fixed-length normalized-weight convolution (L=8). MD-070
  checks correlation > 0.95, not equality. Do not "fix" it.
- UNRATIFIED — **`fct_mmm_input` is the sole model input contract** (AD-030).
- UNRATIFIED — **Two-stage privacy-by-construction intake** (AG-030, AG-020). Stage 1 writes
  private intermediates under `$AMBO_PRIVATE_DROP`; stage 2 writes public outputs to
  `data/real_anon/`. Only stage-2 outputs may enter the repo.
- UNRATIFIED — **Git history is append-only and is itself a deliverable** (EB-082, GB-501,
  GB-502).
- UNRATIFIED — **`search_brand` is modeled but not reallocatable** (DC-203c, DC-704, R-4).
  Brand search is partly an outcome of other media; the optimizer fixes it at its historical
  mean. *Note: whether `other` joins it in the fixed set is an open contradiction — see below.*
</decisions>

### Blueprint defaults (BP-D-01…BP-D-20) — NOT promoted to constraints

The DOC-tier `00_MASTER_PLAN.md` §5 defines twenty decisions and labels them itself as
"proposals with defaults: implement the default unless the human overrides; items marked (ADR)
must be recorded as an ADR when exercised." None is ratified, and several SPEC-tier documents
already hard-code them as contracts — a precedence inversion (INGEST-CONFLICTS WARNING 7).

**None of the twenty is binding.** Per the blueprint's own Definition of Ready, each task must
accept-or-override the BP-D items it exercises, explicitly and on the record — never silently
re-decide them. Full text: `.planning/intel/decisions.md` Group B.

### Ingest contradictions — all seven RESOLVED at source (2026-08-04)

Seven warnings were surfaced at ingest. All seven have since been resolved by editing the
source documents, so none is carried into execution. Full report and resolution log:
`.planning/INGEST-CONFLICTS.md`. Governance decisions: `docs/ADR/ADR-000`.

| # | Contradiction | Resolution |
|---|---------------|------------|
| W1 | Charter declared "Charter beats specs"; configured precedence inverts it. Nothing ratified either. | **ADR-000 D-1** — precedence is *scoped*, not ranked: Charter governs goals/scope/acceptance, SPEC governs operative detail, ADR outranks both. Charter §7 rewritten; §2.3 and DL-1 corrected at source, closing INFO 1 and INFO 2 permanently. |
| W2 | Optimizer fixed set: `search_brand` only (DC-203c) vs `search_brand` + `other` (03_MODULES §6.1). | **BP-D-04 adopted.** DC-203(c) now defines a fixed *set* resolved against channels present; `other` is Layer-R-only, so Layer P and DC-401 are untouched. DC-704 asserts over the resolved set, not a hard-coded name. |
| W3 | SPEC-08 §2's "exact" layout omitted four contract modules a guard test requires. | **Both halves fixed.** The four modules added; "exact" → "canonical" with new packages needing an ADR but new modules allowed given a same-PR 03_MODULES contract entry; the 06 [STD] checklist item reworded to match. |
| W4 | Truth grid 0…2×max vs model grid 0…1.5×max feeding one export and the VR-303 gate. | **One grid: MD-082's.** The true curve is closed-form, so it is evaluated exactly at the model's 21 points — no interpolation. The 0…2× array stays in `truth.json` as a diagnostic. Guard ladder stated explicitly: 1.3× optimizer < 1.5× reporting < 2.0× diagnostic. |
| W5 | DL-1 compares exports against committed versions; `exports/*.csv` was gitignored. | **Exports committed by design** (EB-081). Makes the DL-1 probe and RB-301 executable, and lets a reader inspect headline numbers on the forge without cloning. |
| W6 | Three different full-fit ceilings across three documents. | **Single normative home**: 07_QUALITY_STANDARDS Part A, ≤ 35 min/fit at MD-050 on 4 cores. 03_MODULES §4, 04 §7 and SPEC-08 §5 now cite it. |
| W7 | Twenty DOC-tier BP-D defaults treated as binding by SPEC-tier documents. | **ADR-000 D-2** ratifies BP-D-01…20 wholesale. The DoR's per-item accept/override is satisfied for all twenty; ADR slots retained only to record what intake actually observes. |

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Mirror the blueprint's P0–P8 as Phases 1–9 rather than re-deriving | Re-deriving would orphan the T-001…T-806 WBS numbering and the 13_TRACEABILITY_MATRIX | — Pending |
| Carry all 25 REQ IDs verbatim from the ingest | The `Implements: <REQ-IDs>` docstring convention and the traceability matrix depend on stable IDs | — Pending |
| Preserve W2–W5 as must-resolve items inside their phases rather than picking a side | All four are SPEC-vs-SPEC at equal precedence; an implementer silently choosing is exactly the failure mode | — Pending |

---
*Last updated: 2026-08-05 after Phase 2 (Ground-Truth Simulator) completed — the fictional
Austrian advertiser exists in git history with every SIM-070…075 gate green, closing M1.
REQ-q1-truth-recovery and REQ-grain-and-windows remain Pending (contributing only, not fully
validated by this phase) — both are owned by later phases per ROADMAP.md.*
