# 01 — PHASES (Execution Roadmap)

Nine phases, P0–P8. Phases map onto Charter milestones M0–M7; the warehouse (SPEC-03)
gets its own phase P2 because AD-030 makes it a hard prerequisite of the model
(`ambo/model/` reads only `fct_mmm_input`), which the Charter's milestone table leaves
implicit. Mapping:

| Phase | Charter milestone | Name | Effort (Charter §5) | Blocked on private drop? |
|-------|------------------|------|---------------------|--------------------------|
| P0 | M0 | Repository foundation | 0.5 d | No |
| P1 | M1 | Ground-truth simulator | 1.5 d | No |
| P2 | (M1→M2 seam) | Warehouse (DuckDB + dbt) | counts against M2's 2 d | No |
| P3 | M2 | MMM on S-A | 2 d (incl. P2) | No |
| P4 | M3 | Recovery suite | 2.5 d | No |
| P5 | M4 | Agency intake | 1.5 d (human-heavy) | **Partially** (T-507/508/510) |
| P6 | M5 | Layer R fit + sensitivity | 2 d | **Yes** |
| P7 | M6 | Decision layer | 2 d | Code no; Layer R runs yes |
| P8 | M7 | Reporting & release | 2 d | Layer R content yes |

> **Effort tripwire (Charter §5):** any phase exceeding 2× its budget ⇒ stop, write an
> ADR analyzing why, before continuing.

Tasks referenced below are defined in [02_WBS.md](02_WBS.md). Gates in
[10_VALIDATION_GATES.md](10_VALIDATION_GATES.md). Checklists in
[06_CHECKLISTS.md](06_CHECKLISTS.md).

---

## P0 — Repository foundation (M0)

**Goals.** A clone-and-run engineering shell: git history started, toolchain pinned,
layout per SPEC-08 §2, CI green on an empty-but-honest codebase, governance scaffolding
(ADR template, BUILD_LOG, leak scan pattern subset, season-windows seed).

**Entry criteria.** None (first phase). The only pre-existing files are
`PROJECT_CHARTER.md`, `AGENTS.md`, `docs/SPEC-01..09`, this blueprint.

**Exit criteria (M0 gate).**
- `make setup && make lint && make test` green on a fresh clone (Windows Git Bash and
  Linux).
- CI `ci.yml` runs and passes all six jobs (phase-gated jobs pass trivially with an
  explicit "nothing to check yet" exit, never by being absent — the job list is fixed
  from day one, EB-060).
- Baseline commit contains charter+specs+blueprint before any code commit (history
  argument starts clean).
- `dbt/seeds/season_windows.csv` committed with unit tests (T-011).

**Deliverables.** T-001…T-012 artifacts: git repo, `pyproject.toml` + `uv.lock`,
skeleton dirs, `config/settings.yaml`, `common/{config,logging}.py`, Makefile,
ruff/mypy/pre-commit, `scripts/leak_scan.py`, `ci.yml`, test scaffold with the two
architectural guard tests (forbidden-deps, simulate↔model import independence),
season-windows seed + generator, ADR template + `docs/BUILD_LOG.md`.

**Quality gates.** Engineering Gate (G-ENG) + Governance Gate (G-GOV) subset — see
[10_VALIDATION_GATES.md §2](10_VALIDATION_GATES.md).

**Rollback condition.** None meaningful (no downstream consumers). If toolchain
choices fail on Windows (BP-D-14), fix within P0; do not defer.

---

## P1 — Ground-truth simulator (M1)

**Goals.** SPEC-01 implemented exactly: three scenario datasets + `truth.json` files
committed; every DGP component unit-tested; SIM-070..075 gates green.

**Entry criteria.** P0 exit. Season-windows seed exists (T-011) — the simulator
consumes it (AD-020).

**Exit criteria (M1 gate).** All SIM-070..075 pass via `make simulate &&
make validate-sim`; `data/synthetic/{s_a,s_b,s_c}/` committed; determinism proven
byte-identical on two runs; unit tests for adstock closed form, Hill(K)=0.5,
seasonality peak week, spend-pattern statistics (SIM-031) green; scenario YAMLs are
the authoritative parameter source (SIM-002) and match SPEC-01 §4 tables.

**Deliverables.** T-101…T-109.

**Quality gates.** Data Quality Gate (G-DATA-P), Scientific Gate subset (G-SCI-1:
DGP correctness), Engineering Gate.

**Rollback condition.** If SIM-072 plausibility fails structurally (media share of
revenue outside [15%, 45%] with spec parameters): do **not** tune SPEC-01 §4 values;
re-check implementation first (the spec's parameter set is designed to pass); if a
genuine spec-level infeasibility is proven, ADR + spec fix by the human.

---

## P2 — Warehouse (SPEC-03)

**Goals.** DuckDB + dbt project; raw→staging→marts on committed synthetic data;
`fct_mmm_input` becomes the sole model input contract; exports script skeleton.

**Entry criteria.** P1 exit (synthetic CSVs committed — dbt builds on them in CI).

**Exit criteria.** `make transform` (dbt build) green locally and in CI job 3;
AD-040..043 tests pass (AD-044 activates at M4 per BP-D-05); reconciliation test
AD-042 (P-SA revenue sum = CSV sum ± 1e-6) green; `ambo/common/db.py` accessors
return frames matching the documented mart schemas; `exports/mmm_input_weekly.csv`
contract-tested.

**Deliverables.** T-201…T-205.

**Quality gates.** Data Quality Gate (G-DATA-W), Architecture Gate (G-ARCH: model
code demonstrably reads only the mart).

**Rollback condition.** Schema changes to marts after P3 starts require touching the
model contract — treat any post-P3 mart schema change as an ADR-worthy event.

---

## P3 — MMM on S-A (M2)

**Goals.** SPEC-04 model builder, transforms, priors config, sampling runner,
posterior IO, diagnostics; full-budget fit on S-A passing MD-071/072.

**Entry criteria.** P2 exit; T-302's transform sanity test (MD-070) must pass
**before** the first fit is attempted (it catches T-2 convolution bugs cheaply).

**Exit criteria (M2 gate).** SPEC-04 §7 all green on S-A: R-hat < 1.01, ESS bulk/tail
> 400, 0 divergences, BFMI > 0.3, PPC ≥ 85% weeks in 90% band, PPC plot committed;
`data/posteriors/P-SA.parquet` committed with scale factors; `reports/model/diag_P-SA.md`
generated; smoke-fit test green in CI; MD-040's no-channel-differentiation test green.

**Deliverables.** T-301…T-308 (T-308 `elicit.py` is built here, ahead of its M4 use —
it has no data dependency and de-risks the drop-blocked window).

**Quality gates.** Scientific Gate (G-SCI-2: sampler health), Engineering Gate.

**Rollback condition.** MD-071 failure ⇒ MD-073 reparameterization ladder IN ORDER,
one rung per attempt; leaving rung 1 ⇒ ADR-005; rung 4 (fix s=1) ⇒ model-class change,
re-run all of P4 afterwards. Two failed root-cause attempts ⇒ stop, ask human
(AGENTS §2.3/§2.4).

---

## P4 — Recovery suite (M3)

**Goals.** The credibility engine: recovery metrics vs truth for S-A/S-B/S-C
(VR-301..306), holdout (VR-401), OLS baseline (VR-601), pymc-marketing cross-check
(VR-602), golden tolerance bands (VR-701/702), RECOVERY_REPORT.md generator, SSOT v1,
layer-order CI check. **Passing this phase unlocks all Layer R work (Charter E-2).**

**Entry criteria.** P3 exit.

**Exit criteria (M3 gate).** Every VR-3xx gate green per scenario at its
scenario-specific threshold (incl. VR-304 zero-effect verdict on S-C); VR-401 beats
seasonal-naive MAPE on S-A/S-B; VR-602 correlation ≥ 0.8 on S-B;
`reports/recovery/RECOVERY_REPORT.md` committed with the §8 mandatory structure;
`P-SB.parquet`, `P-SC.parquet` committed; golden bands in `tests/golden/` with
generator script; `make report` regenerates everything without sampling (VR-703);
`scripts/check_layer_order.py` + `check_ssot_consistency.py` wired into CI and green.

**Deliverables.** T-401…T-410.

**Quality gates.** Scientific Gate (G-SCI-3: recovery), Data Quality, Engineering,
Governance (SSOT + layer-order mechanisms live).

**Rollback condition.** A red VR-3xx gate is a **stop condition**, not a
tune-the-gate condition: debug order VR-310 (transforms → scaling round-trip → data
joins → sampler health). Widening any gate requires an ADR naming the suspected
structural cause. Two failed focused attempts ⇒ human (AGENTS §2.3).

---

## P5 — Agency intake (M4)

**Goals.** The complete intake codebase (built and tested on synthetic lookalike
fixtures — drop-independent), then the human-executed run on the private drop,
committed anonymized outputs, and the prior freeze.

**Entry criteria.** P4 exit **for the freeze and any Layer R artifact** (Charter E-2).
The intake *code* (T-501…T-506) only needs P0 and may be built any time after it —
schedule it inside the drop wait window (see [04 §6](04_DEPENDENCIES.md)).

**Exit criteria (M4 gate).** AG-060..066 green on the real drop's outputs
(`make validate-intake`, report under `reports/ingestion/`); `data/real_anon/` +
`INTAKE_MANIFEST.yaml` committed; `docs/DATA_PERMISSION.md` committed; ADR-001..004
written; leak scan (full local + CI subset) green; `docs/PRIOR_ELICITATION.md` +
`config/priors_real.yaml` committed in the freeze commit, tagged `prior-freeze-v1`
(BP-D-07); MD-061 doc-lint test green; dbt `layer_r_present` flipped and AD-044
active and green.

**Deliverables.** T-501…T-510.

**Quality gates.** Data Quality Gate (G-DATA-R), Governance Gate (G-GOV: permission,
freeze, leak scan), Documentation Gate (elicitation doc).

**Rollback condition.** Permission unconfirmed by end of M4 ⇒ Charter §7 degradation
ADR **now, not later** (AG-002 forbids gray-zone processing). Window < 52 weeks ⇒
AG-060's descriptive-only consequence, ADR + Charter §7 consult.

---

## P6 — Layer R fit + sensitivity (M5)

**Goals.** The real-data answer with honest uncertainty: Layer R fit under frozen
priors, MD-074-relaxed diagnostics, the full VR-5xx sensitivity suite, Layer R
holdout + cross-check, short-data narrative.

**Entry criteria.** P5 exit, including freeze tag. `check_layer_order.py` must be
green *before* the first Layer R fit lands (it will verify ancestry forever after).

**Exit criteria (M5 gate).** SPEC-04 §7 on Layer R with §7.6/MD-074 relaxations
(ESS > 300; ≤ 5 divergences only with committed energy plot + funnel-free pair plots +
human review note); `R.parquet` + variant posteriors committed (BP-D-06 naming);
VR-501 prior-influence chart (`vr_prior_influence.png`) + VR-502 LOCO + VR-503 S-B
contrast + VR-504 no-promo artifacts committed; holdout row for Layer R in SSOT
(reported either way, n=13 caveat); crosscheck paragraph written; SSOT updated
(`roas_*`, `layer_r_weeks`, `divergences_real_fit`, `holdout_mape_real`).

**Deliverables.** T-601…T-605.

**Quality gates.** Scientific Gate (G-SCI-4: Layer R honesty), Governance
(layer-order + freeze checks green in CI on the PR that adds Layer R artifacts).

**Rollback condition.** Sampler pathologies after the full MD-073 ladder ⇒ human
(AGENTS §2.4). Wide HDIs are **not** failure — they are content (MD-074).

---

## P7 — Decision layer (M6)

**Goals.** Optimizer (SAA over posterior draws, constraints, extrapolation guards,
brand-search + `other` exclusion), budget scenarios, next-euro ladder,
attribution-gap module; gated by the Layer P optimizer-recovery and φ-ordering tests.

**Entry criteria.** For code + Layer P gates (T-701…T-704): P4 exit (needs committed
P posteriors + truth files). For Layer R runs (T-705): P6 exit. **Exploit this split:
build T-701…T-704 during the drop-blocked window.**

**Exit criteria (M6 gate).** DC-701 (S-A cosine ≥ 0.90, regret ≤ 5%; S-B ≥ 0.80 /
≤ 10%); DC-702 φ-ordering reproduced on S-B; DC-703 two-run determinism byte-identical;
DC-704 constraint audit exact (Σ=B to 1e-6, bounds respected, `search_brand`
unchanged); DC-705 every artifact regenerates via `make decide` without sampling;
`exports/allocation_scenarios.csv`, `exports/attribution_gap.csv`,
`reports/decide/dc_attribution_gap.png` exist; SSOT gains + regret + next-euro keys
written.

**Deliverables.** T-701…T-705.

**Quality gates.** Scientific Gate (G-SCI-5: decision validity), Engineering Gate.

**Rollback condition.** DC-401 regret gate failure with green P4 ⇒ suspect the
optimizer (steady-state formula mismatch BP-D-16, constraint handling, restart
seeding) before suspecting the model; the model already passed recovery.

---

## P8 — Reporting & release (M7)

**Goals.** Everything a reader touches: five executive charts, EXEC_SUMMARY, README
(correct framing variant), LIMITATIONS, exports finalized, Power BI (human),
screenshots, final DL-1..10 audit.

**Entry criteria.** P7 exit for full content. Infrastructure subset (T-801 style/
format/captions; T-802 chart code against synthetic/Layer P inputs) requires only P4
and belongs in the drop-wait window.

**Exit criteria (M7 gate = release).** All of Charter §4 DL-1…DL-10 pass their
expanded acceptance criteria in [11_ACCEPTANCE_CRITERIA.md §4](11_ACCEPTANCE_CRITERIA.md);
`check_ssot_consistency.py` green (no number outside SSOT, RB-601); all five RB-2xx
charts regenerate via `make report` with no sampling; README structure exactly RB §6
order; LIMITATIONS covers all nine GB §6 items; dashboard `.pbix` + 4 screenshots
committed; final SSOT regenerated in the release PR; repo tagged `v1.0`.

**Deliverables.** T-801…T-806.

**Quality gates.** Visualization Gate (G-VIZ), Documentation Gate (G-DOC),
Portfolio Gate (G-PORT), Release Gate (G-REL) — all defined in
[10_VALIDATION_GATES.md](10_VALIDATION_GATES.md).

**Rollback condition.** If Layer R died in P5 (degradation ADR), P8 executes the
RB §6.1 alternate framing; the phase itself never blocks on Layer R.

---

## Phase-independent standing rules

1. Every phase closes with: AGENTS §5 verification protocol run + milestone checklist
   ticked in the PR + BUILD_LOG entry + SSOT regenerated if any number changed.
2. A phase is **not** entered until the previous phase's PR is merged to `main` with
   all CI jobs green (A-9: one milestone, one PR).
3. Cross-phase parallelism is allowed only along the explicitly parallel tracks in
   [04_DEPENDENCIES.md §5–6](04_DEPENDENCIES.md); everything else is sequential.
4. Any gate widened, dependency added, or spec deviated ⇒ ADR before merge (GB-202).
