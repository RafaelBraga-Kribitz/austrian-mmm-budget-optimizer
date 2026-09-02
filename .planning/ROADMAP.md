# Roadmap: Austrian MMM & Budget Optimizer (AMBO)

## Overview

Nine phases that build a credibility argument in order, not a feature list. Phase 1 starts git
history and the engineering shell. Phases 2–4 build the Layer P proving ground: a simulator
with disclosed ground truth, a warehouse that becomes the model's only input, and a Bayesian
MMM fitted on the clean scenario. Phase 5 is the hinge — the recovery suite proves the model
finds truth it was never shown, and its passing commit becomes the git ancestor that unlocks
every Layer R artifact that follows. Phase 6 takes in the real agency data under a permission
gate and freezes the priors before anything is fitted. Phase 7 produces the real answer with
honest uncertainty. Phase 8 turns that posterior into a budget recommendation and an
attribution-gap analysis. Phase 9 makes it all readable and releasable.

The ordering is the product. Phases 5 and 6 are enforced by `scripts/check_layer_order.py` over
git ancestry, so the sequence is a checkable fact rather than a claim in a README.

**Phase structure mirrors `docs/EXECUTION_BLUEPRINT/01_PHASES.md` P0–P8 exactly** (Phase N =
P(N−1)). Do not re-derive it: the 46-task WBS numbering (T-001…T-806) and
`13_TRACEABILITY_MATRIX.md` are keyed to this decomposition.

**Blocked on the private agency drop:** Phases 1–5 are entirely drop-independent. Phase 6 is
partially blocked (T-507/508/510), Phase 7 fully, Phase 8 for Layer R runs only, Phase 9 for
Layer R content only. Exploit the split — the intake codebase, the whole decision layer against
Layer P, and all reporting infrastructure can be built during the wait.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Repository Foundation** - Git history, pinned toolchain, six-job CI, and governance scaffolding on an empty-but-honest codebase (P0 / M0)
- [x] **Phase 2: Ground-Truth Simulator** - Three scenario datasets with disclosed truth files, deterministic to the byte (P1 / M1)
- [ ] **Phase 3: Warehouse** - DuckDB + dbt marts; `fct_mmm_input` becomes the model's only input contract (P2 / M1→M2 seam)
- [ ] **Phase 4: MMM on S-A** - Raw-PyMC model fitted on the clean scenario with clean diagnostics (P3 / M2)
- [ ] **Phase 5: Recovery Suite** - The credibility engine; passing it unlocks all Layer R work by git ancestry (P4 / M3)
- [ ] **Phase 6: Agency Intake** - Permission gate, anonymized real data in the repo, priors frozen before any fit (P5 / M4)
- [ ] **Phase 7: Layer R Fit & Sensitivity** - The real answer with honest uncertainty and the prior-influence artifact (P6 / M5)
- [ ] **Phase 8: Decision Layer** - Constrained optimizer and attribution gap, gated on Layer P recovery (P7 / M6)
- [ ] **Phase 9: Reporting & Release** - Executive charts, README, LIMITATIONS, dashboard, DL-1…DL-10 audit, tag v1.0 (P8 / M7)

## Phase Details

### Phase 1: Repository Foundation

**Goal**: A clone-and-run engineering shell where the quality bar, the scope walls, and the
governance mechanisms all exist and are enforced before a single line of science is written.
**Blueprint phase**: P0
**Milestone**: M0
**Effort budget**: 0.5 d (>2× ⇒ stop + ADR)
**Drop-blocked**: No
**UI hint**: no — this phase ships no frontend surface. The word "layout" below refers to the
SPEC-08 §2 *repository* layout (a file tree), not a UI layout.
**Depends on**: Nothing (first phase)
**Requirements**: REQ-dl8-quality, REQ-scope-in, REQ-scope-out, REQ-milestones, REQ-risk-register
**Success Criteria** (what must be TRUE):

  1. `make setup && make lint && make test` runs green on a fresh clone, on both Windows Git Bash and Linux.
  2. CI `ci.yml` runs all six required jobs and all six pass — phase-gated jobs pass with an explicit "nothing to check yet" exit, never by being absent (EB-060).
  3. Git history begins with a documentation-only baseline commit (charter + specs + blueprint, zero code) that every later commit descends from.
  4. `dbt/seeds/season_windows.csv` is committed with passing unit tests, so the simulator and dbt read one calendar (AD-020).
  5. The two architectural guard tests exist and fail loudly when violated: forbidden dependencies (robyn, lightweight_mmm, prophet, sklearn) and simulate↔model import independence.

**Plans**: 9 plans across 5 waves
Plans:
**Wave 1**

- [x] 01-01-PLAN.md — D-29 audit, `.gitattributes` LF pin, `m0-bootstrap` branch, ADR template + index (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — pyproject + pinned `uv.lock` behind a legitimacy checkpoint, SPEC-08 §2 skeleton, `.env.example`, LICENSE (wave 2)
- [x] 01-03-PLAN.md — `MODULE_CONTRACTS.md`, `RISK_REGISTER.md`, ADR-006, PR template (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-04-PLAN.md — `config/settings.yaml` whole, `common/config.py`, `common/logging.py` + tests (wave 3)
- [x] 01-05-PLAN.md — the 18-target Makefile with loud stubs, scaffold README (wave 3)
- [x] 01-06-PLAN.md — season-windows generator, committed seed, rule tests (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-07-PLAN.md — test scaffold + the four architectural guards, line-ending and ignore tests (wave 4)
- [x] 01-08-PLAN.md — `leak_scan.py` three modes + tests, seven pinned pre-commit hooks (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 01-09-PLAN.md — the two vacuously-correct governance checks, six-job `ci.yml`, M0 close (wave 5)

**WBS tasks**: T-001…T-012
**Quality gates**: G-ENG, G-GOV (subset)
**Rollback**: None meaningful — no downstream consumers. If toolchain choices fail on Windows, fix inside this phase; do not defer.

**Must resolve before execution — INGEST-CONFLICTS WARNING 3 (repository layout):**
SPEC-08 §2 declares an "exact" repository layout that omits `model/fit.py`, `model/priors.py`,
`simulate/config.py`, and `simulate/__main__.py` — all four of which
`docs/EXECUTION_BLUEPRINT/03_MODULES.md` defines as binding public contracts, and one of which
(`model/fit.py`) is load-bearing for the guard test T-010 builds here, since "`pm.sample`
outside `model/fit.py`" is a forbidden import edge.

This is the sharpest of the four carried contradictions and it must be settled in this phase,
because `06_CHECKLISTS.md [STD]` requires "no file added outside the SPEC-08 §2 layout" on
**every** milestone PR. As written, the PR that adds `model/fit.py` in Phase 4 fails the
standing checklist on the same PR that introduces it — and the same trap applies to the
simulator files in Phase 2. Resolve by either extending SPEC-08 §2's listing to include the
four files, or softening the "exact" wording and the [STD] checklist item to allow
contract-listed additions. Do not let an implementer silently pick.
See `.planning/INGEST-CONFLICTS.md` WARNING 3.

**Also settle here:** the repository is on branch `master` with **zero commits** and
`AGENTS.md`, `PROJECT_CHARTER.md`, `docs/`, `.planning/` untracked. T-001 assumes
git-init-and-baseline-commit is the first action on branch `main`. Decide whether to rename to
`main` (the blueprint, EB-080's branch protection, and standing rule 2 all say `main`) before
the baseline commit — after it, renaming is cheap but the ancestry scripts and CI config should
be written against the final name once.

---

### Phase 2: Ground-Truth Simulator

**Goal**: A fictional Austrian advertiser whose every parameter is disclosed in-repo, so that
"the model recovered ROAS" becomes a checkable claim rather than a plot.
**Blueprint phase**: P1
**Milestone**: M1
**Effort budget**: 1.5 d (>2× ⇒ stop + ADR)
**Drop-blocked**: No
**Depends on**: Phase 1 (season-windows seed must exist — the simulator consumes it)
**Requirements**: REQ-q1-truth-recovery (contributing), REQ-grain-and-windows (contributing — Layer P grain)
**Success Criteria** (what must be TRUE):

  1. `make simulate && make validate-sim` produces `data/synthetic/{s_a,s_b,s_c}/` and every SIM-070…075 gate reports green.
  2. Running the simulator twice produces byte-identical CSVs and truth files — determinism is proven, not assumed.
  3. Each `truth.json` contains every SPEC-01 §4/§6 parameter plus the §8 derived quantities, schema-validated by a committed pydantic model.
  4. Unit tests prove the closed forms independently: adstock converges to `x/(1−λ)` for constant spend, `Hill(K) = 0.5` exactly, the max revenue week of each simulated year falls in Advent, and SIM-031 spend-pattern statistics hold.
  5. Scenario YAMLs are the authoritative parameter source, and a test asserts they equal the SPEC-01 §4 table — divergence fails the test and a human reconciles, never a silent fix toward either side.

**Plans**: 10/10 plans executed
Plans:
**Wave 1**

- [x] 02-01-PLAN.md — ADR-007 for the `hypothesis` dev dependency, its blocking legitimacy checkpoint, and the install (wave 1)
- [x] 02-02-PLAN.md — `SimulationError`, the `ScenarioConfig` model tree, module contract, structural tests (T-101a) (wave 1)

**Wave 2** *(blocked on Wave 1)*

- [x] 02-03-PLAN.md — promo/burst placement aid, the three scenario YAMLs, BP-G-02 spec-table equality (T-101b) (wave 2)

**Wave 3** *(blocked on Wave 2)*

- [x] 02-04-PLAN.md — `dgp.py` week spine, seasonality, baseline demand, adstock + Hill, property tests (T-103, T-104) (wave 3)

**Wave 4** *(blocked on Wave 3)*

- [x] 02-05-PLAN.md — `spend_patterns.py` and the SIM-030/031 statistics (T-102) (wave 4)

**Wave 5** *(blocked on Wave 4)*

- [x] 02-06-PLAN.md — `SimulationResult`, `assemble_scenario`, SIM-071/072/073 audits (T-105) (wave 5)

**Wave 6** *(blocked on Wave 5)*

- [x] 02-07-PLAN.md — `platform_bias.py`, SIM-060/061 and BP-D-02 impressions/conversions (T-106) (wave 6)

**Wave 7** *(blocked on Wave 6)*

- [x] 02-08-PLAN.md — `truth.py`, `TruthFile`, `response_curve_at`, byte-stable JSON (T-107) (wave 7)

**Wave 8** *(blocked on Wave 7)*

- [x] 02-09-PLAN.md — CLI, gate runner, real `make simulate`/`validate-sim`, SIM-070 (T-108) (wave 8)

**Wave 9** *(blocked on Wave 8)*

- [x] 02-10-PLAN.md — commit the nine artifacts, BUILD_LOG M1 entry, milestone sign-off (T-109) (wave 9)

**WBS tasks**: T-101…T-109
**Quality gates**: G-DATA-P, G-SCI-1, G-ENG
**Rollback**: If SIM-072 plausibility fails structurally (media share of revenue outside [15%, 45%] with spec parameters), do **not** tune the SPEC-01 §4 values. Re-check the implementation first — the spec's parameter set is designed to pass. Only a proven spec-level infeasibility justifies an ADR plus a human spec fix.

**RESOLVED at source — INGEST-CONFLICTS WARNING 4 (response-curve grid), part 1 of 2.**
This is **no longer an open decision for Phase 2**. `docs/SPEC-01_ground_truth_simulator.md` §8
now carries a "Grid note (resolves INGEST-CONFLICTS WARNING 4)" paragraph settling it (verified
by direct read during Phase 2 research — see `02-RESEARCH.md` Pitfall 1). The resolution:

- The 21-point 0…2× max weekly spend array in `truth.json` is a **diagnostic** sample kept in
  that file only. It shows where the model would be extrapolating and is never the comparison grid.

- `exports/response_curves.csv` (AD-050) carries **one grid only** — MD-082's 21 points over
  0…1.5× max *observed* weekly spend — and the Layer P truth column on that export is the
  closed-form curve evaluated at those same 21 points. VR-303 differences on that grid.

- The true curve is closed-form (β·Hill at steady-state adstock), so it evaluates exactly at any
  spend with no interpolation error. The simulator therefore exposes it as a function of a
  **caller-supplied grid**: plan 02-08 ships `truth.response_curve_at(params, x_grid)` and
  registers it in `docs/MODULE_CONTRACTS.md`, so Phase 3/8's export reuses the formula instead of
  re-deriving it.

---

### Phase 3: Warehouse

**Goal**: One queryable source of modeling input, so that the model provably reads a contract
rather than a pile of CSVs it could quietly reshape.
**Blueprint phase**: P2
**Milestone**: M1→M2 seam (counts against M2's 2 d)
**Effort budget**: Shares M2's 2 d with Phase 4
**Drop-blocked**: No
**Depends on**: Phase 2 (synthetic CSVs must be committed — dbt builds on them in CI)
**Requirements**: REQ-q1-truth-recovery (contributing), REQ-grain-and-windows (contributing — weekly spine), REQ-dl1-reproducible-pipeline (contributing — `make transform` opens the DL-1 probe)
**Success Criteria** (what must be TRUE):

  1. `make transform` builds the dbt project green locally and in CI job 3, on committed synthetic data with no private inputs.
  2. `fct_mmm_input` exists as the sole model input contract, and `ambo/common/db.py` accessors return frames matching the documented mart schemas — gapless ascending weekly spine, documented columns, no NaN in spends, revenue > 0.
  3. AD-040…043 dbt tests pass, including the AD-042 reconciliation: Layer P-SA total revenue in `fct_mmm_input` equals the simulator CSV sum within 1e-6.
  4. `exports/mmm_input_weekly.csv` is contract-tested, and duplicate grain keys FAIL rather than being silently deduplicated.

**Plans**: TBD
**WBS tasks**: T-201…T-205
**Quality gates**: G-DATA-W, G-ARCH (model code demonstrably reads only the mart)
**Rollback**: The `fct_mmm_input` contract freezes at T-203. Any mart schema change after Phase 4 starts is an ADR-worthy contract break, because it forces a change to the model contract.

**Note:** `layer_r_present` starts `false` and AD-044 stays dormant until Phase 6 flips it. That
is BP-D-05 — a blueprint default, not a ratified decision. Accept or override it explicitly at
task time per the Definition of Ready; do not silently re-decide it.

---

### Phase 4: MMM on S-A

**Goal**: A Bayesian MMM that fits the clean scenario with a healthy sampler, so that any later
recovery failure can be attributed to the science rather than to the machinery.
**Blueprint phase**: P3
**Milestone**: M2
**Effort budget**: 2 d including Phase 3 (>2× ⇒ stop + ADR)
**Drop-blocked**: No
**Depends on**: Phase 3
**Requirements**: REQ-q1-truth-recovery (contributing), REQ-q2-real-incremental-roas (contributing — one model definition serves all layers), REQ-dl6-priors-as-deliverable (contributing — `elicit.py` built here at T-308, ahead of its M4 use)
**Success Criteria** (what must be TRUE):

  1. MD-070 transform sanity passes **before** the first fit is attempted: model and simulator transform outputs correlate > 0.95 per channel on the S-A spend series. (This catches convolution bugs cheaply, and the parameterization mismatch is deliberate — MD-070 checks correlation, never equality.)
  2. A full-budget S-A fit passes SPEC-04 §7: R-hat < 1.01 on all parameters, ESS bulk and tail > 400, zero divergences, BFMI > 0.3 on all chains.
  3. The posterior predictive check puts observed revenue inside the 90% band for ≥ 85% of weeks, with the plot committed.
  4. `data/posteriors/P-SA.parquet` (thinned, carrying scale factors and provenance metadata) and `reports/model/diag_P-SA.md` are committed, and the CI smoke-fit is green inside its 15-minute budget.
  5. MD-040's test proves the Layer P priors are channel-agnostic — identical Beta on every λ, identical HalfNormal on every β — so recovery cannot come from priors that encode the truth table.

**Plans**: TBD
**WBS tasks**: T-301…T-308
**Quality gates**: G-SCI-2 (sampler health), G-ENG
**Rollback**: An MD-071 failure triggers the MD-073 reparameterization ladder **in order**, one rung per attempt; leaving rung 1 requires ADR-005. Rung 4 (fixing s = 1) is a model-class change and forces all of Phase 5 to be re-run. Two failed root-cause attempts ⇒ stop and ask the human.

**Open item — INGEST-CONFLICTS WARNING 6 (runtime ceiling):** three SPEC-tier documents give
three different full-fit ceilings — ~35 min (07_QUALITY_STANDARDS Part A), ~30 min (03_MODULES
§4), and 15–35 min (04_DEPENDENCIES §7). A 32-minute fit is simultaneously compliant and
non-compliant depending on which page a reviewer opens, and the value feeds the Charter §5
effort tripwire through the compute ledger. Pick one number, put it in the single home that
09 A-2 (magic numbers) demands, and have the other documents cite it rather than restate it.

---

### Phase 5: Recovery Suite

**Goal**: Proof that the model finds truth it was never shown — and a commit whose ancestry
makes that proof unfalsifiable for every result that follows.
**Blueprint phase**: P4
**Milestone**: M3
**Effort budget**: 2.5 d (>2× ⇒ stop + ADR)
**Drop-blocked**: No
**Depends on**: Phase 4
**Requirements**: REQ-q1-truth-recovery (owning), REQ-dl2-recovery-report, REQ-e2-layer-order, REQ-e4-numeric-ssot, REQ-dl1-reproducible-pipeline (contributing)
**Success Criteria** (what must be TRUE):

  1. Every VR-3xx gate is green per scenario at its scenario-specific threshold — including VR-304, where the model must say the zero-effect channel does nothing: P(average ROAS < 0.2) ≥ 0.7 and median contribution share ≤ 3% on S-C's `display_video`.
  2. `reports/recovery/RECOVERY_REPORT.md` is generated (not hand-edited), carries the mandatory SPEC-05 §8 section order, an all-green gate table, and the ≥ 500-character "what this does and does not prove" closing.
  3. VR-401 holdout beats the seasonal-naive MAPE baseline on S-A and S-B, and the VR-602 pymc-marketing cross-check correlates ≥ 0.8 with the raw-PyMC model on S-B.
  4. `make report` regenerates every recovery artifact from the committed thinned posteriors with **zero sampling** (VR-703), and golden tolerance bands live in `tests/golden/` with their generator script.
  5. `scripts/check_layer_order.py` and `scripts/check_ssot_consistency.py` are wired into CI and green — from this point, Layer R work is unlocked, and the unlock is a checked fact rather than a promise (Charter E-2).

**Plans**: TBD
**WBS tasks**: T-401…T-410
**Quality gates**: G-SCI-3 (recovery), G-DATA, G-ENG, G-GOV (SSOT + layer-order mechanisms live)
**Rollback**: A red VR-3xx gate is a **stop condition**, not a tune-the-gate condition. Debug in VR-310 order: transforms (MD-070) → scaling round-trip → data joins → sampler health. Widening any gate requires an ADR that names the suspected structural cause. Two failed focused attempts ⇒ human.

**Must resolve before execution — INGEST-CONFLICTS WARNING 4 (response-curve grid), part 2 of 2:**
VR-303 gates the "mean absolute error between posterior-mean curve and true curve over the
observed-spend grid" without specifying which grid, and the truth (0…2×max) and model
(0…1.5×max) grids are not identical. VR-303's numeric result depends entirely on the
unspecified reconciliation, and it is a hard M3 exit gate — meaning this ambiguity can decide
whether the project's central credibility claim passes or fails. The reconciliation chosen in
Phase 2 must be implemented consistently here, and `exports/response_curves.csv` must be
explicit about whether it carries one grid or two.
See `.planning/INGEST-CONFLICTS.md` WARNING 4 and Phase 2.

---

### Phase 6: Agency Intake

**Goal**: Real client data inside the repo without a single identifying or absolute value —
and the priors written down, with rationales, before anyone has seen a result.
**Blueprint phase**: P5
**Milestone**: M4
**Effort budget**: 1.5 d, human-heavy (>2× ⇒ stop + ADR)
**Drop-blocked**: **Partially** — T-507, T-508, T-510 need the drop; the intake codebase T-501…T-506 needs only Phase 1 and belongs in the wait window
**Depends on**: Phase 5 (for the freeze and any Layer R artifact — Charter E-2). The intake *code* may be built any time after Phase 1.
**Requirements**: REQ-dl6-priors-as-deliverable, REQ-e3-prior-freeze, REQ-grain-and-windows (owning), REQ-degradation-path, REQ-dl9-honesty (contributing), REQ-q2-real-incremental-roas (contributing — the data)
**Success Criteria** (what must be TRUE):

  1. `docs/DATA_PERMISSION.md` is committed — stating that written permission exists, from whom in role terms only, the date, and the scope — and it was committed **before** any private file was processed. No gray-zone processing happened while waiting.
  2. `make validate-intake` reports AG-060…066 green on the real drop's outputs, and `data/real_anon/` plus `INTAKE_MANIFEST.yaml` are committed carrying no secret factors, no client identity, and no absolute totals.
  3. The leak scan is green in full local mode and in the CI subset, with the log retained.
  4. `config/priors_real.yaml` and the final `docs/PRIOR_ELICITATION.md` land in **one** freeze commit tagged `prior-freeze-v1`, MD-061 doc-lint is green (every channel present, every rationale ≥ 100 characters and not boilerplate, YAML matching the stated ranges), and no Layer R fit artifact exists anywhere in history yet.
  5. dbt `layer_r_present` is flipped to true and AD-044 is active and green — the mart's channel list matches the manifest.

**Plans**: TBD
**WBS tasks**: T-501…T-510
**Quality gates**: G-DATA-R, G-GOV (permission, freeze, leak scan), G-DOC (elicitation doc)
**Rollback**: If permission is not confirmed by the end of M4, write the Charter §7 degradation ADR **now, not later** — AG-002 forbids gray-zone processing while waiting. The project then ships as Layers P+D on S-B, with the attribution-gap module running on SIM-060's known over-credit and the README taking its RB §6.1 alternate framing. A window shorter than 52 weeks triggers AG-060's descriptive-only consequence plus an ADR and a Charter §7 consult.

**Note:** the freeze deadline may slip; a fit before the freeze may not. That asymmetry is the
whole of E-3.

---

### Phase 7: Layer R Fit & Sensitivity

**Goal**: The real client's answer, with uncertainty reported as content rather than hidden as
weakness.
**Blueprint phase**: P6
**Milestone**: M5
**Effort budget**: 2 d (>2× ⇒ stop + ADR)
**Drop-blocked**: **Yes** — fully
**Depends on**: Phase 6 including the freeze tag. `check_layer_order.py` must be green *before* the first Layer R fit lands; it verifies that ancestry forever after.
**Requirements**: REQ-q2-real-incremental-roas (owning), REQ-dl3-layer-r-posterior-report, REQ-e2-layer-order (contributing — first exercise), REQ-e3-prior-freeze (contributing — enforced here), REQ-e4-numeric-ssot (contributing)
**Success Criteria** (what must be TRUE):

  1. A Layer R fit under the frozen priors passes SPEC-04 §7 with the MD-074 relaxations (ESS > 300); any tolerated divergences (≤ 5) ship with a committed energy plot, funnel-free pair plots, and a human review note.
  2. `data/posteriors/R.parquet` plus the variant posteriors are committed, and both the layer-order and prior-freeze checks are green in CI **on the very PR that adds them**.
  3. A ROAS table with 90% HDIs, response curves, and an additive contribution decomposition exists for the real client, with the MD-080 additivity test proving components sum to fitted μ within tolerance.
  4. The VR-501 prior-influence forest plot (`reports/recovery/vr_prior_influence.png` — the portfolio artifact of this project), VR-502 leave-one-channel-out, VR-503 S-B contrast, and VR-504 no-promo artifacts are all committed.
  5. SSOT carries `roas_*`, `layer_r_weeks`, `divergences_real_fit`, and `holdout_mape_real`, with the n=13 holdout caveat stated whichever way the holdout lands.

**Plans**: TBD
**WBS tasks**: T-601…T-605
**Quality gates**: G-SCI-4 (Layer R honesty), G-GOV
**Rollback**: Sampler pathologies surviving the full MD-073 ladder ⇒ stop and ask the human. **Wide HDIs are not a failure — they are the finding** (MD-074, risk R-2). The informative-priors-vs-flat comparison is the centerpiece precisely when identification is weak on 52–104 weeks.

---

### Phase 8: Decision Layer

**Goal**: A budget recommendation a marketing lead can act on, with the extrapolation guard
rails visible in the output rather than buried in a caveat.
**Blueprint phase**: P7
**Milestone**: M6
**Effort budget**: 2 d (>2× ⇒ stop + ADR)
**Drop-blocked**: Code no, Layer R runs yes — build T-701…T-704 during the drop-blocked window
**Depends on**: Phase 5 for the code and the Layer P gates (needs committed P posteriors and truth files); Phase 7 for the Layer R runs (T-705)
**Requirements**: REQ-q3-optimal-allocation, REQ-q4-attribution-gap, REQ-dl4-optimizer-output, REQ-dl5-attribution-gap-artifact, REQ-e5-anonymized-euro-caption (contributing — DC-302 caption)
**Success Criteria** (what must be TRUE):

  1. DC-701 optimizer recovery is green on Layer P: on S-A, allocation cosine similarity ≥ 0.90 versus the true-parameter optimum and regret ≤ 5% of true-optimal; on S-B, ≥ 0.80 and ≤ 10%.
  2. DC-702 reproduces the simulated over-credit **ordering** on S-B: display_video > meta > search_generic > search_brand.
  3. `exports/allocation_scenarios.csv` shows 3 budget rows × channels with historical and optimal shares, expected contribution with HDI, binding-constraint flags, and the 1.3× extrapolation-guard bounds visible per channel.
  4. DC-704's constraint audit is exact — Σ x = B to 1e-6, bounds respected, `search_brand` unchanged — and two runs produce byte-identical CSVs (DC-703).
  5. `exports/attribution_gap.csv` and `reports/decide/dc_attribution_gap.png` regenerate via `make decide` from committed posteriors with no sampling, carrying per-channel P(platform > MMM) and the ≥ 500-character interpretation paragraph written from the marketing chair.

**Plans**: TBD
**WBS tasks**: T-701…T-705
**Quality gates**: G-SCI-5 (decision validity), G-ENG
**Rollback**: A DC-401 regret failure with a green Phase 5 means **suspect the optimizer first** — steady-state formula mismatch, constraint handling, restart seeding — not the model. The model already passed recovery.

**Must resolve before execution — INGEST-CONFLICTS WARNING 2 (optimizer fixed-channel set):**
SPEC-06 DC-203(c) fixes exactly one channel at its historical mean — `search_brand` — and
DC-704's constraint audit correspondingly checks only that `search_brand` is unchanged.
`03_MODULES.md` §6.1 states the `optimize_allocation` post-condition as "fixed channels
(search_brand, **other**) at historical mean", adding a second channel. Both documents are
SPEC-tier at equal precedence, so this cannot be auto-resolved.

The two variants produce materially different DL-4 output — a different optimal allocation and
a different headline expected gain — whenever `other` is present in the Layer R channel mix,
and the DC-704 audit test is written differently under each. The basis for the addition is
BP-D-04, which is DOC-tier and self-labels the item "(ADR-002 at intake)", requiring an ADR
that does not exist. Choose one variant explicitly: amend SPEC-06 to include `other` in the
fixed set, or strike the reference from 03_MODULES §6.1 and defer to ADR-002.
See `.planning/INGEST-CONFLICTS.md` WARNING 2.

---

### Phase 9: Reporting & Release

**Goal**: Everything a reader touches — and a release a stranger can reproduce from a clean
clone without any private input.
**Blueprint phase**: P8
**Milestone**: M7
**Effort budget**: 2 d (>2× ⇒ stop + ADR)
**Drop-blocked**: Layer R content yes; the T-801/T-802 infrastructure subset needs only Phase 5 and belongs in the wait window
**Depends on**: Phase 8 for full content
**Requirements**: REQ-dl1-reproducible-pipeline (owning), REQ-dl7-dashboard, REQ-dl9-honesty, REQ-dl10-readme, REQ-e1-tagged-headline-numbers, REQ-e5-anonymized-euro-caption (owning), REQ-dl8-quality (contributing — release-commit audit), REQ-e4-numeric-ssot (contributing — RB-601 final), REQ-degradation-path (contributing — alternate framing if exercised)
**Success Criteria** (what must be TRUE):

  1. A clean clone runs the DL-1 probe sequence with zero errors and **no fits**, and regenerated artifacts match the committed ones — text byte-equal, MCMC-derived numbers inside VR-702 bands — with the log attached to the release PR. Separately, `make simulate && make validate-sim` byte-reproduces `data/synthetic/`.
  2. README follows the RB §6 order exactly, leads with the recovery verdict and the gain number, embeds RB-201 before RB-202 (money first, credibility second), and every headline number carries its epistemic tag inline.
  3. All five RB-2xx executive charts regenerate via `make report` in under 2 minutes with zero sampling, each carrying a business-English title, unit-labeled axes, a source note, and an epistemic tag.
  4. `LIMITATIONS.md` covers all nine GB §6 items with a 9/9 mapping table, and `check_ssot_consistency.py` is green — proving no number lives outside SSOT.
  5. `dashboards/ambo.pbix` and the four `docs/assets/dashboard_p1..p4.png` screenshots are committed with verified rebuild instructions, the final SSOT is regenerated in the release PR, and the repo is tagged `v1.0`.

**Plans**: TBD
**WBS tasks**: T-801…T-806
**Quality gates**: G-VIZ, G-DOC, G-PORT, G-REL
**Rollback**: If Layer R died in Phase 6 under the degradation ADR, this phase executes the RB §6.1 alternate framing. **The phase itself never blocks on Layer R.**

**Must resolve before execution — INGEST-CONFLICTS WARNING 5 (DL-1 vs gitignored exports):**
`11_ACCEPTANCE_CRITERIA.md` §4 requires the DL-1 probe to "compare regenerated reports/exports
to committed versions", but SPEC-08 §2 lists `exports/` as gitignored and EB-081 puts
`exports/*.csv` in `.gitignore`, with the committed-by-design list naming only
`data/synthetic/`, `data/real_anon/`, and `data/posteriors/*.parquet`. There is no committed
version of any export CSV to compare against, so the exports half of the probe cannot be
executed as specified — and DL-1 is the **first row of the G-REL release gate**.

Resolve by either restricting the DL-1 comparison to `reports/` artifacts, or committing the
six export CSVs by design and amending EB-081. Note the same tension touches RB-301, whose
pytest recomputes RB-201's bars from `allocation_scenarios.csv`.
See `.planning/INGEST-CONFLICTS.md` WARNING 5.

**Note on UI:** this phase produces a Power BI dashboard and executive charts, but the project
has no web frontend (Charter O-5 excludes hosted apps) and SPEC-07 §4 already fixes every
dashboard page's content list (RB-401…406) plus the German subtitle and a€ footer standard
(RB-405). No separate UI design contract is needed — SPEC-07 **is** the design contract.

## Progress

**Execution Order:** Phases execute in numeric order 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9.

**Standing rules** (`01_PHASES.md` §Phase-independent):

1. Every phase closes with the AGENTS §5 verification protocol run, the milestone checklist ticked in the PR with evidence, a `docs/BUILD_LOG.md` entry, and SSOT regenerated if any number changed.
2. A phase is **not** entered until the previous phase's PR is merged with all CI jobs green (one milestone, one PR).
3. Cross-phase parallelism is allowed only along the explicitly parallel tracks in `04_DEPENDENCIES.md` §5–6; everything else is sequential.
4. Any gate widened, dependency added, or spec deviated ⇒ ADR before merge (GB-202).
5. Any phase exceeding 2× its effort budget ⇒ stop and write an ADR analyzing why, before continuing.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Repository Foundation | M0 | 9/9 | Complete | 2026-09-02 |
| 2. Ground-Truth Simulator | M1 | 10/10 | Complete | 2026-09-02 |
| 3. Warehouse | M1→M2 | 0/TBD | Not started | - |
| 4. MMM on S-A | M2 | 0/TBD | Not started | - |
| 5. Recovery Suite | M3 | 0/TBD | Not started | - |
| 6. Agency Intake | M4 | 0/TBD | Not started | - |
| 7. Layer R Fit & Sensitivity | M5 | 0/TBD | Not started | - |
| 8. Decision Layer | M6 | 0/TBD | Not started | - |
| 9. Reporting & Release | M7 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-08-04 from doc ingest. Phase structure mirrors `docs/EXECUTION_BLUEPRINT/01_PHASES.md` P0–P8 1:1.*
