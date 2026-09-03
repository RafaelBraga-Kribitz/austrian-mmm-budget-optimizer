---
phase: 5
slug: recovery-suite
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-03
---

# Phase 5 — Validation Strategy

> Per-phase validation contract. Seeded from `05-RESEARCH.md`. Per-task rows use WBS
> IDs T-401…T-410.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x; ArviZ HDI; DuckDB for integration paths only |
| **Quick run command** | `uv run pytest tests/unit/test_recovery.py -q` |
| **Full suite command** | `make lint && make test` (smoke excluded unless `SMOKE=1`; fit marker always off) |
| **Full fits** | `make fit-synthetic` (never via `make test`) |
| **Recover** | `make recover` (no sampling, T-406+) |
| **Estimated runtime** | unit tests ~1–2 min; three full fits 15–35 min each; holdout three more |

## Sampling Rate

- **After every task commit:** the plan's `<verify>` automated command
- **After every plan wave:** `make lint && make test`
- **Before claiming M3:** SPEC-05 §3–§6 green in the generated report; SSOT rows present;
  `make recover` regenerates without NUTS
- **Max feedback latency (unit):** ~60 seconds for T-401 fixtures

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T-401 | 05-01 | 1 | REQ-q1-truth-recovery | P1/P2/P3 | Fixture ROAS/HDI/gates match known answers; YAML=§3 | unit | `uv run pytest tests/unit/test_recovery.py -q` | ✅ | ✅ |
| T-402 | 05-02 | 2 | REQ-q1-truth-recovery | P13 | P-SB/P-SC MD-071/072 green; parquets committed | make | inspect `diag_P-SB.md` `diag_P-SC.md` | ✅ | ✅ |
| T-403 | 05-03 | 3 | REQ-q1-truth-recovery | P8 | Beat naive MAPE on S-A/S-B; coverage column present | unit+make | holdout tests + CSVs | ✅ | ✅ |
| T-404 | 05-04 | 4 | REQ-q1-truth-recovery | P11 | OLS+HC1 vs textbook 1e-8; no statsmodels | unit | `uv run pytest tests/unit/test_baseline_ols.py -q` | ✅ | ✅ |
| T-405 | 05-05 | 5 | REQ-q1-truth-recovery | P12 | mapping doc + confinement guard; correlation reported | unit+art | crosscheck tests | ✅ | ✅ |
| T-406 | 05-06 | 6 | REQ-dl2-recovery-report | P9 | §8 order test; closing ≥500 chars; no sample() | unit | `uv run pytest tests/unit/test_recovery_report.py -q` | ⬜ | ⬜ |
| T-407 | 05-07 | 7 | REQ-dl1-reproducible-pipeline | P6 | bands schema; golden test; no draw checksum | unit | `uv run pytest tests/golden -q` | ⬜ | ⬜ |
| T-408 | 05-08 | 8 | REQ-e4-numeric-ssot | — | SSOT regenerates; planted mismatch caught | unit | governance + generate_ssot tests | ⬜ | ⬜ |
| T-409 | 05-09 | 9 | REQ-e2-layer-order | — | Green now; both GB-501 failure modes fire in tmp repos | unit | `uv run pytest tests/unit/test_governance_checks.py -q` | ⬜ | ⬜ |
| T-410 | 05-10 | 10 | REQ-q1-truth-recovery | VR-310 | Gate table all-green; SSOT recovery_pass_*; BUILD_LOG ledger | make | `make recover` + SSOT diff | ⬜ | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [x] P-SA posterior + diag (Phase 4)
- [x] `response_curve_at` caller-supplied grid (Phase 2)
- [x] `check_layer_order.py` / `check_ssot_consistency.py` + CI (Phase 1)
- [x] `src/ambo/validate/recovery.py` — 05-01
- [x] P-SB / P-SC posteriors — 05-02
- [x] holdout CSVs — 05-03
- [x] OLS table — 05-04
- [x] crosscheck mapping — 05-05
- [ ] `RECOVERY_REPORT.md` — 05-06
- [ ] golden bands — 05-07
- [ ] `NUMERIC_SSOT.md` — 05-08
- [ ] M3 close — 05-10

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Status |
| --- | --- | --- | --- | --- |
| P-SB/P-SC wall time ≤ 35 min/fit | D-18 | Timing is machine-bound | `make fit-synthetic`; BUILD_LOG | ✅ |
| Live CI vs main | REQ-dl8-quality | `ci.yml` only fires against `main` | Do not invent `"Approved"` (D-19) | ⬜ |
| Red VR-3xx after two debug attempts | VR-310 | Human stop (AGENTS §2) | Do not widen the YAML | ⬜ |

## Gate hygiene

A red VR-3xx is investigated in VR-310 order (transforms MD-070 → scaling round-trip →
data joins → sampler health). Widening requires an ADR naming the structural cause.
Two failed focused attempts ⇒ stop and ask the human.
