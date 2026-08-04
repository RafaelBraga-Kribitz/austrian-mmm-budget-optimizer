# 12 — RISK REGISTER (expanded per milestone)

Extends Charter §6 (R-1..R-9 remain authoritative; referenced where expanded).
Per risk: likelihood/impact, **mitigation** (reduce likelihood), **fallback**
(what we do if it fires), **detection** (how we notice early). Review the relevant
block at each phase entry ([01_PHASES.md](01_PHASES.md)).

## M0 — Foundation

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-M0-1 | Windows/Linux toolchain divergence (Make, EOLs, paths) breaks byte-determinism gates later | M/H | M: BP-D-14 (Git Bash + GNU Make, LF pinned at T-001, pathlib only). F: dev containers/WSL as documented alternative. D: CI (Linux) vs local (Windows) hash comparison at T-108 |
| RK-M0-2 | uv cross-platform lock fails for pymc/pytensor pins | L/M | M: lock early (T-002), test both platforms. F: platform markers in pyproject; ADR if a pin must move. D: `uv sync` failure in CI |
| RK-M0-3 | mypy --strict vs PyMC idioms generates suppression sprawl | M/M | M: scoped ignore_missing_imports (EB-001); type only our surfaces. F: per-module overrides documented in pyproject. D: suppression count in review |

## M1 — Simulator

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-M1-1 | Adstock direction/off-by-one (trap T-2) survives visual inspection | M/H | M: SIM-074 closed-form + impulse tests written BEFORE dgp assembly. F: VR-310 debug order points back here. D: MD-070 correlation < 0.95 at P3 |
| RK-M1-2 | SIM-072 plausibility fails with spec parameters | L/M | M: implement §4 exactly; audit media share early (T-105). F: proven infeasibility ⇒ ADR + human spec fix (never silent tuning). D: gate runner |
| RK-M1-3 | Float formatting/EOL nondeterminism breaks SIM-070 | M/M | M: fixed float format, LF, sorted JSON keys (Guide §1.5). D: two-run hash in gate |

## P2 — Warehouse

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-P2-1 | Mart schema churn after model starts (contract break) | M/H | M: freeze `fct_mmm_input` contract at T-203 ([03 §8]); ADR for any later change. D: db.py contract assertions fail |
| RK-P2-2 | dbt-duckdb version quirks (external views, seeds) | M/L | M: pinned versions; CI job 3 from P2 on. F: pin adjustment via ADR. D: CI |
| RK-P2-3 | Python↔dbt taxonomy drift | M/M | M: BP-G-03 equality pytest (A-16). D: that test |

## M2 — Model

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-M2-1 (R-7) | Divergences/pathologies on S-A | M/H | M: scaling (T-1) enforced by design; prior-predictive sanity pre-MCMC. F: MD-073 ladder in order; ADR-005 past rung 1; human after ladder. D: MD-071 |
| RK-M2-2 | Smoke-fit exceeds CI budget | M/M | M: BP-D-17 caches; 60-week subset; FAST sampling profile. F: reduce smoke draws via ADR (test-only change). D: CI timing |
| RK-M2-3 | Truncated-Gamma/Hill numerics (overflow at s→3, x→0) | M/M | M: log-space Hill where needed; unit tests at domain edges. D: NaN guards in transforms tests |
| RK-M2-4 | Scale-factor leakage into holdout later | M/H | M: factors computed per fitting slice by construction (T-301); leakage test at T-403. D: that test |

## M3 — Recovery

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-M3-1 (R-3/T-4) | S-B/S-C collinearity → wide HDIs → gates near-miss | H/M | M: gates already calibrated for this (VR §3 looser columns); do NOT remove seasonality (T-4). F: VR-310 debug order; widening only via ADR naming cause. D: recovery runner |
| RK-M3-2 | pymc-marketing API drift breaks crosscheck | M/M | M: pin ≥0.8; confine to one module (MD-003). F: document unmatchable elements (VR-602 sanctions this); ADR if gate impossible. D: T-405 CI |
| RK-M3-3 (R-5/T-6) | Cross-platform MCMC drift breaks goldens | C/M | M: tolerance bands ±0.15·SD (VR-702), never checksums. F: band regeneration with PR justification (EB-073). D: golden test |
| RK-M3-4 | False-positive control fails (model hallucinates display_video in S-C) | M/H | M: weakly-informative priors (MD-040) + HalfNormal β shrinkage. F: this is a STOP — structural bug or prior misdesign; VR-310 then human. D: VR-304 |
| RK-M3-5 | Layer-order script git edge cases (merge commits, follows) | M/M | M: tmp-repo test matrix (Guide §10). D: those tests |

## M4 — Intake (the external-dependency milestone)

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-M4-1 (R-1) | Permission falls through / drop never arrives | M/H | M: T-507 started immediately; drop-independent backlog fills the wait ([04 §6]). F: Charter §7 degradation ADR by end of M4 — Layers P+D on S-B become the showcase; RB §6.1 framing pre-drafted (T-804). D: calendar checkpoint at phase entry |
| RK-M4-2 (R-6) | Anonymization leak (factors, names, absolute €) | L/C | M: privacy-by-construction (two-stage AG-030, whitelist schema, RescaleFactors never serialized, leak scan, M4 human-review checklist). F: STOP + human-led remediation incl. rotation; documented (EB-082). D: leak scan + M4 file-by-file review |
| RK-M4-3 | Real data too short (< 52 wk) or too dirty (AG gates red) | M/H | M: pipeline adapts to input subsets (§5.3); reconstruction flags. F: descriptive-only ADR + Charter §7 consult (AG-060). D: `make validate-intake` |
| RK-M4-4 | Channel taxonomy misfit (`other` ≥ 10%) | M/M | M: mapping rules iterated with human at intake. F: taxonomy revisit via ADR-002. D: AG-062 |
| RK-M4-5 | CPC/CPM fingerprinting via AG-042 factor sharing | L/M | M: BP-D-11 recommendation (third factor k_cnt) put to human at M4; else documented in LIMITATIONS. D: ADR-003 review |
| RK-M4-6 | Elicitation stalls (human time is the bottleneck) | M/M | M: T-509 skeleton + converters (T-308) ready beforehand; structured interview format. F: freeze deadline slips — but NEVER fit before freeze (E-3 is inviolable). D: phase effort tracking |

## M5 — Layer R fit

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-M5-1 (R-2) | Weak identification on 52–104 weeks → very wide posteriors | H/M | M: none needed — this IS the finding; VR-501 becomes the centerpiece. F: narrative emphasis shift (already specced). D: HDI widths in diag report |
| RK-M5-2 | Pressure to "fix" priors after seeing fit (A-10) | M/C | M: freeze enforcement (GB-502) + AGENTS A-6; sanctioned outlet = VR-501. D: layer-order CI |
| RK-M5-3 | Divergences beyond MD-074 tolerance | M/H | M: ladder; relaxations are pre-specced, not improvised. F: human after ladder; possibly rung 4 + P4 rerun. D: MD-074 |
| RK-M5-4 | Sensitivity-fit compute stacks up (5+ full fits) | M/L | M: BP-D-18 ledger; serialize track H; overnight runs. D: BUILD_LOG times |

## M6 — Decision layer

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-M6-1 | Optimizer recovery gate fails though model passed M3 | M/M | M: BP-D-16 parameterization discipline; toy-problem unit test; analytic gradient. F: suspect optimizer numerics first ([01 §P7] rollback). D: DC-401 |
| RK-M6-2 (R-4/T-7) | Brand-search sneaks into reallocation via indirect paths | L/H | M: fixed-set constraint by construction + DC-704 audit test. D: that test |
| RK-M6-3 | SLSQP convergence flakiness → determinism breaks | M/M | M: seeded restarts, fixed draw subset, share-space conditioning (Guide §5). F: increase restarts via config + ADR if spread > 1% persists. D: DC-703 two-run test |
| RK-M6-4 | Extrapolation beyond data support hidden in outputs | L/H | M: 1.3× hard bounds + binding flags + DC-302 caption single-source. D: DC-704 + artifact review |

## M7 — Reporting & release

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-M7-1 | Number drift between README/EXEC/charts (A-8) | M/H | M: SSOT pipeline + GB-303 checker + RB-301 recompute test. D: CI job 4 |
| RK-M7-2 | Power BI stalls (human task, tooling) | M/M | M: exports frozen early (T-803); dashboard spec is precise (RB-401..405). F: ship README/exec-charts first, dashboard follows in a patch release — Charter DL-7 blocks v1.0 though: schedule human time explicitly. D: T-805 checkpoint |
| RK-M7-3 (R-8) | Scope creep at the end ("just add Robyn/daily grain") | H/M | M: Charter §2.2 walls + forbidden-deps test + A-3 (AGENTS). D: review + guard test |
| RK-M7-4 | Portfolio tone failure (jargon, vendor-bashing, overclaiming) | M/M | M: G-PORT gate with explicit review criteria; templates with slots for the sensitive paragraphs (DC-504, VR §8.8). D: G-PORT review |

## Cross-cutting

| ID | Risk | L/I | Mitigation / Fallback / Detection |
|----|------|-----|-----------------------------------|
| RK-X-1 | Agent violates layer order / freeze by accident | L/C | M: CI enforcement from M3 (not honor system); AGENTS A-2 instructs stop-and-tell. F: NO history rewrite — human decides remediation with the violation documented. D: CI job 5 |
| RK-X-2 | Effort budget blowout (Charter §5: >2× ⇒ stop) | M/M | M: per-phase tracking in BUILD_LOG; drop-wait window absorbs slack. F: stop + ADR analyzing cause. D: BUILD_LOG vs budget table |
| RK-X-3 | Blueprint drift from specs as work proceeds | M/M | M: blueprint subordination clause ([00 §preamble]); conflicts filed in BUILD_LOG and fixed blueprint-side. D: review habit |
| RK-X-4 | Multi-agent handoff loses context between phases | M/M | M: this blueprint + BUILD_LOG as the handoff artifacts; PR checklists as state; contract-first rule for API changes. D: DoR item 2/3 compliance |
