---
phase: 4
slug: mmm-on-s-a
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-03
---

# Phase 4 — Validation Strategy

> Per-phase validation contract. Seeded from `04-RESEARCH.md`. Per-task rows use WBS
> IDs T-301…T-308.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (`pyproject.toml`); PyMC/ArviZ for smoke; dbt warehouse must exist for MD-070 and smoke |
| **Quick run command** | `uv run pytest tests/unit/test_transforms.py tests/unit/test_priors.py tests/unit/test_mmm.py -q` |
| **Full suite command** | `make lint && make test` (smoke excluded unless `SMOKE=1`) |
| **Smoke command** | `make transform && make test SMOKE=1` |
| **Full fit command** | `make fit-synthetic` (never part of `make test`) |
| **Estimated runtime** | unit tests ~1 min; smoke a few minutes inside the 15 min CI job; full S-A 15–35 min |

## Sampling Rate

- **After every task commit:** the plan's `<verify>` automated command
- **After every plan wave:** `make lint && make test`
- **Before claiming M2:** MD-071/072 green on committed `diag_P-SA.md`; `P-SA.parquet` present
- **Max feedback latency (unit):** ~60 seconds after D-02 (PyMC import) lands

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T-301 | 04-01 | 1 | REQ-q1-truth-recovery | T-2 convolution | Causal impulse; pytensor=numpy 1e-10; L is an argument | unit | `uv run pytest tests/unit/test_transforms.py -q` | ✅ | ✅ |
| T-301 | 04-01 | 1 | REQ-q1-truth-recovery | T-1 scaling | `from(to(x))==x` to 1e-12; all-zero → FitError | property | same | ✅ | ✅ |
| T-301 | 04-01 | 1 | REQ-dl8-quality | Pitfall 1 | `import pymc` succeeds after numpy constraint | smoke-import | `uv run python -c "import pymc, arviz"` | ✅ | ✅ |
| T-303 | 04-02 | 2 | REQ-q1-truth-recovery | MD-040 | synthetic priors channel-agnostic; extra=forbid | unit | `uv run pytest tests/unit/test_priors.py -q` | ✅ | ✅ |
| T-303 | 04-02 | 2 | ADR-006 deferral | W6 | `max_fit_minutes==35` on Settings | unit | `uv run pytest tests/unit/test_config.py -q` | ✅ | ✅ |
| T-302 | 04-03 | 3 | REQ-q1-truth-recovery | T-2/T-3 | r>0.95 per S-A channel; test imports both packages | unit | `uv run pytest tests/unit/test_transform_sanity.py -q` | ✅ | ✅ |
| T-304 | 04-04 | 4 | REQ-q2-real-incremental-roas | MD-002 | free-RV name set; no S-A/layer literals in mmm.py | unit | `uv run pytest tests/unit/test_mmm.py -q` | ⬜ | ⬜ |
| T-304 | 04-04 | 4 | REQ-dl8-quality | EB-060 | smoke fit completes; R-hat finite | smoke | `make test SMOKE=1` | ⬜ | ⬜ |
| T-305 | 04-05 | 5 | REQ-dl1-reproducible-pipeline | T-1 | save/load round-trip; refuse missing scale factors; atomic | unit | `uv run pytest tests/unit/test_posterior_io.py -q` | ⬜ | ⬜ |
| T-306 | 04-06 | 6 | REQ-q1-truth-recovery | MD-071 | synthetic idata with injected divergences fails the gate | unit | `uv run pytest tests/unit/test_diagnostics.py -q` | ⬜ | ⬜ |
| T-307 | 04-07 | 7 | REQ-q1-truth-recovery | MD-071/072 | full S-A fit; diag report all-green; parquet committed | make | `make fit-synthetic` then inspect diag | ⬜ | ⬜ |
| T-308 | 04-08 | 8 | REQ-dl6-priors-as-deliverable | MD-060 | converter round-trips; no PRIOR_ELICITATION.md invented | unit | `uv run pytest tests/unit/test_elicit.py -q` | ⬜ | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [x] `src/ambo/model/transforms.py` — 04-01
- [x] `FitError` — 04-01
- [x] numpy lock constraint — 04-01
- [x] `priors.py` + `priors_synthetic.yaml` — 04-02
- [x] `test_transform_sanity.py` — 04-03
- [ ] `mmm.py` + `fit.sample_model` + smoke — 04-04
- [ ] `posterior_io.py` — 04-05
- [ ] `diagnostics.py` — 04-06
- [ ] `data/posteriors/P-SA.parquet` + `reports/model/diag_P-SA.md` — 04-07
- [ ] `elicit.py` — 04-08

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Status |
| --- | --- | --- | --- | --- |
| Full S-A NUTS wall time ≤ 35 min on 4 cores | D-01 / MD-050 | Timing depends on this machine | `make fit-synthetic`; record elapsed in BUILD_LOG | ⬜ |
| Live CI smoke on ubuntu+windows | REQ-dl8-quality | `ci.yml` only fires against `main` (D-19) | Same pattern as M0 #11 / M1 / warehouse: do not invent `"Approved"` | ⬜ |
| MD-073 ladder, if needed | MD-071 | Only if the full fit is unhealthy | Follow rungs in order; ADR-005 past rung 1 | ⬜ not triggered |

## Gate hygiene

A red MD-071 is investigated via MD-073, never by loosening thresholds in this phase.
Two failed focused attempts ⇒ stop and ask the human (AGENTS §2).
