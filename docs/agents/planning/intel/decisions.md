# Decisions (synthesized intel)

Source tier: ADR. **No ADRs exist in this repository.** `docs/ADR/` is referenced by
SPEC-09 GB-201/GB-202 and by five pre-planned slots (ADR-001..005), but the directory
is absent from the ingest set. Therefore:

- Zero decisions carry `locked: true`.
- The top populated precedence tier is SPEC, not ADR.
- Every entry below is `status: proposed` — nothing in this corpus is ratified by an
  ADR, including the items that SPEC-tier documents treat as binding.

Two groups follow: (A) design commitments asserted directly by SPEC-tier documents,
(B) blueprint decisions (BP-D-01..20) which the source itself labels
"proposals with defaults, implement unless the human overrides".

---

## Group A — SPEC-asserted design commitments

## Additive-in-level model, not log
- source: docs/SPEC-04_mmm_model.md (MD-001)
- status: proposed
- decision: The MMM is additive in revenue LEVEL (a€/€), not log, because contributions must decompose additively for the waterfall and the optimizer.
- scope: MMM functional form, contribution decomposition, optimizer objective

## Raw PyMC is primary; pymc-marketing is cross-check only
- source: docs/SPEC-04_mmm_model.md (MD-003), docs/SPEC-05_validation_recovery.md (VR-602), PROJECT_CHARTER.md (O-3)
- status: proposed
- decision: Exactly two implementations exist — raw PyMC (primary) and pymc-marketing (cross-check). `pymc_marketing` may be imported ONLY in `src/ambo/validate/crosscheck.py`, never in the primary model path. No Robyn, Meridian, lightweight_mmm, or model averaging.
- scope: modeling framework selection, dependency allow-list, import guard tests

## Simulator and model share no transform code
- source: docs/SPEC-01_ground_truth_simulator.md (SIM-003), docs/EXECUTION_BLUEPRINT/09_ANTI_PATTERNS.md (A-1)
- status: proposed
- decision: `src/ambo/simulate/` and `src/ambo/model/` must not import each other in either direction; each implements its own adstock/Hill with independent unit tests. The single sanctioned exception is shared CONFIG data (`dbt/seeds/season_windows.csv`, AD-020) — never shared transform code.
- scope: recovery-argument integrity, module boundaries, AST guard test T-010

## Deliberate simulator/model parameterization mismatch is a feature
- source: docs/SPEC-04_mmm_model.md (MD-020)
- status: proposed
- decision: The simulator uses raw geometric recursion; the model uses fixed-length normalized-weight convolution (L=8). The mismatch is intentional realism — the model never sees the true DGP form exactly. MD-070 checks correlation of transform outputs (>0.95), not equality. Do not "fix" it.
- scope: adstock parameterization, MD-070 sanity gate, recovery interpretation

## `fct_mmm_input` is the sole model input contract
- source: docs/SPEC-03_data_model.md (AD-030)
- status: proposed
- decision: `ambo/model/` reads only the `fct_mmm_input` mart via `ambo/common/db.py`, never CSVs. CSV reads inside `model/` and `decide/` are guard-tested forbidden edges.
- scope: warehouse boundary, data access layer, architecture gate G-ARCH

## Two-stage privacy-by-construction intake
- source: docs/SPEC-02_agency_data_pipeline.md (AG-030, AG-020)
- status: proposed
- decision: Stage 1 (`ambo.intake.standardize`) reads `$AMBO_PRIVATE_DROP` and writes still-private intermediates under the drop; stage 2 (`ambo.intake.anonymize`) writes public outputs to `data/real_anon/`. Only stage-2 outputs may enter the repo. `AMBO_PRIVATE_DROP` is the single env var.
- scope: anonymization architecture, repo privacy boundary, secrets handling

## Git history is append-only and is itself a deliverable
- source: docs/SPEC-08_engineering.md (EB-082), docs/SPEC-09_governance_quality.md (GB-501/GB-502)
- status: proposed
- decision: No force-push, no rebase of pushed history, no amends, ever. The layer-order proof (recovery report commit precedes any Layer R fit artifact) and the prior freeze (freeze commit precedes any Layer R fit artifact, files unmodified after) are verified by `scripts/check_layer_order.py` over git ancestry in CI. Agents never rewrite history; remediation of a leak is human-performed and documented.
- scope: git policy, governance enforcement, epistemic claim E-2/E-3

## `search_brand` is modeled but not reallocatable
- source: docs/SPEC-06_decision_layer.md (DC-203c, DC-704), PROJECT_CHARTER.md (R-4)
- status: proposed
- decision: Brand search is included in the model but FIXED at its historical mean in the optimizer, because brand search is partly an outcome of other media (endogeneity trap). DC-704 audits that it is unchanged.
- scope: optimizer constraint set, attribution honesty, LIMITATIONS content

## Layer P gates precede all Layer R publication
- source: PROJECT_CHARTER.md (E-2), docs/SPEC-05_validation_recovery.md (§preamble), docs/SPEC-09_governance_quality.md (GB-501)
- status: proposed
- decision: Layer R results are published ONLY if Layer P recovery gates passed. This ordering is CI-checked via git ancestry, not asserted by promise.
- scope: build order, publication gating, credibility architecture

## Prior freeze precedes any Layer R fit
- source: PROJECT_CHARTER.md (E-3), docs/SPEC-04_mmm_model.md (MD-041/MD-062), docs/SPEC-09_governance_quality.md (GB-502)
- status: proposed
- decision: `config/priors_real.yaml` plus `docs/PRIOR_ELICITATION.md` are committed BEFORE any Layer R fit artifact exists, enforced by git-ancestry check. Frozen ranges never change; the only sanctioned outlet after seeing results is the VR-501 sensitivity analysis.
- scope: epistemic integrity, prior elicitation deliverable DL-6, governance CI

---

## Group B — Blueprint decisions (BP-D), self-labelled proposals-with-defaults

## BP-D-01: ENTSO-E mention in tasking is inapplicable
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §3, §5
- status: proposed
- decision: AMBO has no ENTSO-E dependency and no live API at all (EB-070 asserts zero network; O-7 forbids automated refresh). The structurally equivalent external blocker is the private agency data drop + written permission, needed at M4. "API-blocked vs non-API work" maps to "drop-blocked vs drop-independent work".
- scope: external dependency identification, planning terminology

## BP-D-02: Layer P impressions and platform_conversions generating rule
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Per-channel CPM constants in scenario YAML; `impressions = round(spend/cpm x 1000)`; offline channels NULL. `platform_conversions = round(platform_revenue/AOV_t)`; offline NULL. Parameters recorded in `truth.json`.
- scope: SIM-004 gap closure, simulator output columns, truth.json schema

## BP-D-03: Unit-suffix union tension between Layer P and Layer R columns
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Staging renames to unit-neutral names (`spend`, `revenue`, `platform_conv_value`, `clicks` with NULL for P); monetary unit lives in `dim_layer.monetary_unit`; the AD-043 test asserts no model exposes both `_eur` and `_aeur` suffixed columns.
- scope: dbt staging design, AD-001/AD-043 reconciliation

## BP-D-04: `other` channel modeling and reallocation status
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Modeled if present with >=1% spend (weak prior); EXCLUDED from optimizer reallocation (fixed at historical mean, like `search_brand`) — an undefined bucket cannot be a recommendation. Marked (ADR-002 at intake).
- scope: optimizer constraint set, channel taxonomy handling

## BP-D-05: dbt must build in CI from M0 but `data/real_anon/` does not exist until M4
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: dbt var `layer_r_present: false`; staging conditionally unions Layer R sources; flipped to `true` in the M4 PR. AD-044 implemented via a public seed `dbt/seeds/intake_channels.csv` generated by intake stage-2 from the manifest.
- scope: dbt configuration, CI job 3, M4 activation

## BP-D-06: Posterior artifact naming and which variants get committed
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: `data/posteriors/P-SA.parquet`, `P-SB.parquet`, `P-SC.parquet`, `R.parquet`; variants `R__flat.parquet`, `R__nopromo.parquet`, `R__loco-<channel>.parquet`, `P-SB__flat.parquet` (glob `R*` in GB-501 catches all R variants). Holdout outputs committed as summary CSVs under `reports/model/holdout_<layer>.csv`, not posteriors.
- scope: posterior_io naming contract, layer-order glob, compute ledger

## BP-D-07: Operational definition of "the commit freezing priors"
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Freeze = the single commit adding both `config/priors_real.yaml` and the final `docs/PRIOR_ELICITATION.md`, annotated git tag `prior-freeze-v1`; `generate_ssot.py` reads the tag's commit hash into `prior_freeze_commit`; `check_layer_order.py` verifies ancestry plus no post-tag modification of either file.
- scope: GB-502 enforcement mechanics, SSOT key, M4 exit

## BP-D-08: SSOT interval keys
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: `roas_<channel>_hdi90` splits into two keys `roas_<channel>_hdi90_lo` and `roas_<channel>_hdi90_hi`; same split for `expected_gain_pct` bounds.
- scope: GB-302 SSOT key schema

## BP-D-09: Burst and promo-week counts on partial-year scenarios
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5, docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md §1.1
- status: proposed
- decision: Schedule per ISO calendar year covered; partial years get counts pro-rated by covered weeks, rounded half-up; the resulting explicit week lists are authored in scenario YAML, which is authoritative (SIM-002). S-C's half year 2023 pro-rates to 5 promo weeks.
- scope: scenario YAML authoring, SIM-030/031

## BP-D-10: Producer of `dbt/seeds/season_windows.csv`
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: `scripts/generate_season_windows.py` (uses `holidays` + SPEC-01 §2.1 ISO-week rules) generates it once for ISO years 2019-2027; committed; simulator and dbt both read the committed CSV; regeneration idempotent and diff-checked in CI.
- scope: AD-020 single-source-of-calendar, T-011

## BP-D-11: AG-042 count rescaling preserves real CPC/CPM
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Default is to follow the spec and document the preservation explicitly in LIMITATIONS §3. Recommendation to the human at M4: introduce a third secret factor `k_cnt` for counts (keeps CTR and internal consistency, masks CPC/CPM). Marked (ADR-003 if adopted — spec deviation).
- scope: anonymization residual fingerprinting surface, LIMITATIONS content

## BP-D-12: DC-601 "±€500/week" in masked Layer R units
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: ±a€500 as written; caption states masked units; ratio-invariance noted in LIMITATIONS.
- scope: marginal-ROAS ladder units, captions

## BP-D-13: Git-ancestry CI checks need full history
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: The `layer-order` and `leak-scan` CI jobs check out with `fetch-depth: 0`; `check_layer_order.py` exits green trivially while no Layer R artifacts exist.
- scope: ci.yml configuration, GB-501/502 runtime

## BP-D-14: Windows dev vs Makefile-canonical interface
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: GNU Make via Git Bash required for local dev (documented in README §8 dev note); CI runs `ubuntu-latest`; all Python paths via `pathlib`; Makefile recipes POSIX-sh only.
- scope: cross-platform toolchain, determinism gates

## BP-D-15: Optimizer total budget B per layer
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: B = mean total weekly spend over that layer's full window; DC-401 uses S-A's/S-B's own mean; DC-205 multipliers apply to Layer R's mean.
- scope: DC-205/DC-401 budget definition

## BP-D-16: DC-401 mixes two adstock parameterizations
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Truth-side evaluation uses SPEC-01 raw recursion steady state `x/(1-λ)`; posterior-side uses the model's normalized steady state `x` (DC-201). Comparison is on allocations and contributions only, never parameters.
- scope: optimizer recovery test correctness

## BP-D-17: CI smoke-fit 15-minute budget is tight for PyMC compile
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Cache `uv` env and pytensor compiledir in Actions cache; smoke test carries `@pytest.mark.timeout(900)`.
- scope: EB-060 CI budget, G-ENG smoke gate

## BP-D-18: Sampling budget for holdout and sensitivity refits
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5, docs/EXECUTION_BLUEPRINT/04_DEPENDENCIES.md §7
- status: proposed
- decision: Full MD-050 budget for every reported fit. Compute inventory ~14 full fits, estimated 3-8 h total wall time, planned in the 04 §7 ledger.
- scope: compute planning, effort budget tripwire

## BP-D-19: `dim_layer.channels_present` type
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Comma-joined string in canonical taxonomy order (BI-friendly, dbt-testable).
- scope: dim_layer schema

## BP-D-20: `make all` behavior when fits are missing
- source: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md §5
- status: proposed
- decision: Each non-fit target fails fast with the exact `make fit-*` command to run; never auto-triggers sampling (EB-050 cost control).
- scope: Makefile semantics, CI compute prevention
