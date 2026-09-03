---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 5
current_phase_name: Recovery Suite
status: executing
stopped_at: Completed 05-05-PLAN.md
last_updated: "2026-09-03T13:15:00Z"
last_activity: 2026-09-03
last_activity_desc: "05-05 complete; T-405 pymc-marketing VR-602"
progress:
  total_phases: 9
  completed_phases: 4
  total_plans: 46
  completed_plans: 41
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** A reviewer can verify from git history alone that the model recovered known truth before it touched real data, and that the priors preceded the results.
**Current focus:** Phase 5 — Recovery Suite (P4 / M3). Drop-independent. No Layer R fits.

## Current Position

Phase: 5 of 9 (Recovery Suite)
Plan: 05-06 (T-406 RECOVERY_REPORT + make recover) next
Status: executing
Last activity: 2026-09-03 — 05-05 complete (T-405)

Progress: Phase 1 [██████████] 100% (9/9). Phase 2 [██████████] 100% (10/10). Phase 3 [██████████] 100% (9/9). Phase 4 [██████████] 100% (8/8). Phase 5 [█████·····] 50% (5/10).

## Performance Metrics

**Velocity:**

- Total plans completed: 41
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 9/9 | - | - |
| 02 | 10/10 | - | - |
| 03 | 9/9 | - | - |
| 04 | 8/8 | - | - |
| 05 | 5/10 | - | - |

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
- [2026-09-03, 04-01]: D-02 lock-only numpy `<2.4` (numpy 2.3.5, numba 0.65.1
  transitive, pymc 5.28.5). T-301 transforms are pytensor graphs; L is an
  argument; `FitError` is the model-package `AmboError`.
- [2026-09-03, 04-02]: D-01 `max_fit_minutes: 35` on Settings (not SamplerConfig).
  MD-040 synthetic priors are an explicit seven-channel YAML with identical
  values. `priors_real.yaml` was not created.
- [2026-09-03, 04-03]: MD-070 green on P-SA spend vs recursive DGP at truth λ;
  equality is not asserted.
- [2026-09-03, 04-04]: `build_model` + `sample_model` (only `pm.sample` site).
  Hill is log-space with floor 1e-8 (Pitfall 8). Smoke 1×200/200 green locally;
  1-chain R-hat uses a split-chain construction.
- [2026-09-03, 04-05]: ADR-008 pyarrow 22.0.0. posterior_io thins 4000→1000,
  embeds ScaleFactors in parquet schema metadata, refuses files without them.
  NetCDF uses ArviZ default h5netcdf (already transitive).

- [2026-09-03, 04-06]: DiagGates.standard vs layer_r are explicit constructors.
  Injected divergences fail standard and pass layer_r. Missing PPC fails MD-072.
- [2026-09-03, 04-07]: P-SA MD-050 fit is MD-071/072 green after ADR-011
  (`target_accept` 0.99). ADR-005 non-centered Fourier; ADR-010 (s=1) superseded.
  `P-SA.parquet` + `diag_P-SA.md` + `ppc_P-SA.png` committed. Wall time of the
  green attempt 443 s (7.4 min), well under 35 min.
- [2026-09-03, 04-08]: `elicit.py` converters (MD-060) without inventing
  `PRIOR_ELICITATION.md` or `priors_real.yaml`. Phase 4 closed. Live CI vs
  main still D-19 — do not invent `"Approved"`.

- [2026-09-03, 05-01]: Recovery metrics engine (T-401). Gate table is YAML
  mirroring SPEC-05 §3. validate may import `simulate.truth` (`response_curve_at`)
  but not `simulate.dgp` (D-03). HDI via ArviZ. No Layer R.
- [2026-09-03, 05-02]: P-SB and P-SC MD-050 fits all-green at `target_accept` 0.99
  (ADR-011). Rung-1 retries when ESS_tail fails alongside divergences (D-07,
  not a gate widening). Combined three-layer ladder wall ~38.9 min; each fit
  ≤ 35 min. No Layer R.

- [2026-09-03, 05-03]: Holdout VR-401. Train T−13, scale on slice, predict last
  13 with actual spend. P-SA/P-SB beat naive MAPE. Holdout parquets gitignored.

- [2026-09-03, 05-04]: OLS+HC1 (VR-601) without statsmodels. P-SB search_brand
  OLS sign disagrees with Bayesian ROAS; pinv for collinear X'X.

- [2026-09-03, 05-05]: pymc-marketing 0.19.4 VR-602 on P-SB. Pearson 0.9648 /
  Spearman 0.8857. adapt_diag (jitter trips alpha check). 3050 divergences
  reported, not MD-071. No Layer R.

### Pending Todos

- Execute 05-06…05-10 (T-406…T-410). Drop-independent. Never invent Layer R.

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

Last session: 2026-09-03T13:15:00Z
Stopped at: Completed 05-05-PLAN.md
Resume file: .planning/phases/05-recovery-suite/05-06-PLAN.md

Next: execute 05-06 (RECOVERY_REPORT.md + make recover). Never invent Layer R.
