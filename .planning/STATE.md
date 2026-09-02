---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 4
current_phase_name: MMM on S-A
status: executing
stopped_at: Completed 03-09-PLAN.md
last_updated: "2026-09-02T16:20:00Z"
last_activity: 2026-09-02
last_activity_desc: "Phase 3 warehouse closed; Task 3 CI deferred (D-19)"
progress:
  total_phases: 9
  completed_phases: 3
  total_plans: 28
  completed_plans: 28
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** A reviewer can verify from git history alone that the model recovered known truth before it touched real data, and that the priors preceded the results.
**Current focus:** Phase 4 — MMM on S-A (P3 / M2). Not present on `m0-bootstrap`.

## Current Position

Phase: 4 of 9 (MMM on S-A)
Plan: Phase 3 complete; Phase 4 not yet planned on this lineage
Status: executing
Last activity: 2026-09-02 — warehouse closed (9/9); Task 3 CI deferred D-19

Progress: Phase 1 [██████████] 100% (9/9). Phase 2 [██████████] 100% (10/10). Phase 3 [██████████] 100% (9/9).

## Performance Metrics

**Velocity:**

- Total plans completed: 28
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 9/9 | - | - |
| 02 | 10/10 | - | - |
| 03 | 9/9 | - | - |

**Recent Trend:** No data yet.

*Updated after each plan completion*

## Accumulated Context

### Decisions

Full log in PROJECT.md. `docs/ADR/` now exists and **ADR-000 is ratified**, covering document
precedence, the twenty BP-D blueprint defaults (accepted wholesale), and the ingest cycle
deviation. The eight Group A design commitments asserted by SPEC text remain formally
unratified and are candidates for ADR-001+ as they are exercised.

- [Ingest]: Roadmap mirrors blueprint P0–P8 1:1 as Phases 1–9 — re-deriving would orphan the T-001…T-806 WBS and the traceability matrix.
- [Ingest]: All 25 REQ IDs carried verbatim; no new IDs invented for Phases 2–4.
- [2026-08-04]: All 7 ingest warnings resolved at source rather than deferred into phases — the source SPECs were contradictory independently of the ingest, so fixing the documents (not annotating the plan) was the only resolution that survives into implementation. See ADR-000 and the INGEST-CONFLICTS resolution log.
- [2026-08-04, ADR-000 D-1]: Precedence is scoped, not ranked — Charter governs goals/scope/acceptance, SPEC governs operative detail, ADR outranks both. The Charter's own passages were corrected where they restated SPEC values wrongly.
- [2026-09-01]: Delivery topology for this execution loop is **one PR per GSD task** on
  `cursor/*-9588` branches off `main`. That supersedes D-11's milestone-branch PR for the
  duration of the loop. `origin/m0-bootstrap` / draft PR #1 already contain later work;
  they are not the merge vehicle.
- [2026-09-01, locked 1A 2A 3A 4B]: (1A) pin `uv.lock`; O-3 is import-scoped so transitive
  sklearn via pymc-marketing is accepted. (2A) copy verified artifacts from `m0-bootstrap`
  rather than rewriting. (3A) no private drop — build drop-independent work; Charter §7
  degradation ADR at M4; ship Layers P+D on S-B. (4B) one PR per GSD plan with one commit
  per task — supersedes the same-day one-PR-per-task topology for the rest of the loop.
- [2026-09-02, 03-01]: `profiles.yml` `dev.path` is the bare `data/warehouse/ambo.duckdb`
  string (no `../` prefix) per RESEARCH.md Pitfall 1.
- [2026-09-02, 03-01]: `make transform` is the unconditional single-line dbt build (D-21).
- [2026-09-02, 03-01]: `dbt/.user.yml` gitignored (per-machine usage-stats UUID).
- [2026-09-02, 03-01]: REQ-dl1-reproducible-pipeline not marked complete (Phase-9-owned).
- [2026-09-02, 03-02]: `DataContractError` is the third `AmboError` subclass; mart-only
  AST guard (D-09) converts AD-030 into a standing check.
- [2026-09-02, 03-03]: staging layer applies BP-D-03 renames; AD-043 is a singular
  information_schema test; poisoned fixture proves duplicate grain keys fail dbt build.
- [2026-09-02, 03-04]: `fct_mmm_input` is the enforced 17-column model-input contract;
  AD-040 seed-derived spine, AD-041 ranges, AD-042 three-layer reconciliation.
- [2026-09-02, 03-05]: `dim_layer.channels_present` is source-presence-derived;
  absent `other` vs present-but-ineffective S-C `display_video` is distinguishable.
- [2026-09-02, 03-06]: `fct_platform_reported` Layer P surface frozen at six columns;
  AD-044 dormant; `layer_r_present` branch executed once against a fake fixture (D-20).
- [2026-09-02, 03-07]: `ambo.common.db` is the only data doorway; contract columns
  derived from mart YAML; collect-all-raise-once `DataContractError`.
- [2026-09-02, 03-08]: `exports/mmm_input_weekly.csv` is registry-written, byte-stable,
  and byte-identical with m0 after local `make export`.
- [2026-09-02, 03-09]: CI job 3 is a two-leg matrix with export drift gate; job 2
  builds the warehouse before pytest; ruff format scoped to Python; R-14 added.
  Task 3 live CI confirmation deferred (D-19).

### Pending Todos

None yet.

### Blockers/Concerns

**Closed 2026-08-04 — all seven ingest warnings resolved at source.** W1–W7 were fixed by
editing the source documents (see `.planning/INGEST-CONFLICTS.md` resolution log and
`docs/ADR/ADR-000`). None is carried into any phase. The intel count discrepancy is also
corrected. What remains:

1. **[Phase 1] Branch name.** Repository is on **`master`**; the blueprint, EB-080 branch
   protection, `check_layer_order.py`, and CI config all assume **`main`**, and each gets
   written against it once. Renamed to `main` on 2026-08-04 — no remote exists, so the rename
   was local and lossless. Verify before the first push that any forge default branch matches.
   *(The rest of the original blocker is stale: the baseline commit already exists — `1851f39`,
   documentation-only, zero code — so the layer-order argument does start clean.)*

2. **[Phase 6] External dependency.** The private agency drop plus written permission is the
   only external blocker. Phases 1–5 are fully drop-independent; fill any wait window with the
   intake codebase (T-501…T-506), the decision layer against Layer P (T-701…T-704), and
   reporting infrastructure (T-801, T-802).

3. **[M3 exit — ACTION REQUIRED, no natural trigger] Repository is PRIVATE; make it public
   when the recovery report exists.** The repo was public from 2026-08-04 13:53 until 16:0x
   with 39k words of specs, zero code and no README. Set private on 2026-08-04 by decision:
   go public at **M3**, when `reports/recovery/RECOVERY_REPORT.md` proves the model recovers
   known truth. That is the moment the project's central claim stops being a promise. Git
   history is untouched, so the layer-order argument (Charter §5) still verifies on release.

   **Before flipping back to public, do all of:**

   - [ ] `RECOVERY_REPORT.md` exists with SPEC-05 §3 gates green
   - [ ] `README.md` exists per SPEC-07 §6 (DL-10: leads with the recovery result)
   - [ ] `LICENSE` (MIT, per SPEC-08 §2) present
   - [ ] `gh repo edit --visibility public`

   *Done 2026-08-04:* `docs/EXECUTION_BLUEPRINT/` untracked and gitignored as internal build
   scaffolding (files remain on disk, and remain in history from commit `1851f39` — EB-082
   forbids rewriting, which is accepted). Published tree is now `PROJECT_CHARTER.md`,
   `AGENTS.md`, `docs/ADR/`, `docs/SPEC-01..09`, `.planning/`. `.planning/` was kept tracked
   deliberately: it is version-controlled backup for ROADMAP/STATE, and INGEST-CONFLICTS.md
   with its resolution log is a defensible artifact rather than noise.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-09-02T16:20:00Z
Stopped at: Completed 03-09-PLAN.md (Phase 3 warehouse closed; Task 3 CI D-19)
Resume file: none on m0-bootstrap — Phase 4 plans do not exist there

Next: plan **Phase 4 (MMM on S-A)** from Charter/SPEC-04, or fill the drop wait
with intake T-501…T-506 / decide T-701…T-704 / report T-801/T-802. Never invent
Layer R (A-5). Do not copy m0 `uv.lock`.
