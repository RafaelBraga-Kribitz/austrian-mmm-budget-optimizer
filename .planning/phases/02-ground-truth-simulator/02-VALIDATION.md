---
phase: 2
slug: ground-truth-simulator
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-05
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest>=8 + pytest-cov (already configured, Phase 1) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (coverage gate currently non-blocking per D-15 until M0 exit criteria — verify whether it has flipped blocking by Phase 2's start) |
| **Quick run command** | `uv run pytest tests/unit/test_dgp.py tests/unit/test_scenario_config.py -q` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~30 seconds (full 3-scenario build) |

---

## Sampling Rate

- **After every task commit:** Run the relevant module's quick-run command (see Per-Task Verification Map)
- **After every plan wave:** Run `make test` (full suite, includes all guard tests from Phase 1)
- **Before `/gsd-verify-work`:** `make simulate && make validate-sim` green (SIM-070…075 gate table)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (planner-assigned) | TBD | TBD | SIM-002/BP-G-02, REQ-grain-and-windows | — | Scenario YAML == SPEC-01 §4 table; S-C/S-B minimal-diff is rule-level, not literal (Pitfall 7); exact per-scenario week counts (156/104/78), ISO-Monday `week_start` | unit | `pytest tests/unit/test_scenario_config.py -x` | ❌ W0 | ⬜ pending |
| TBD (planner-assigned) | TBD | TBD | SIM-030/031 | — | Spend-pattern statistics (annual totals ±10%, zero-week share ±10pp), determinism; floor/round/multiply order per Guide §1.3 (Pitfall 6) | unit | `pytest tests/unit/test_spend_patterns.py -x` | ❌ W0 | ⬜ pending |
| TBD (planner-assigned) | TBD | TBD | SIM-073 | — | Season weights exact; peak-revenue week in Advent | unit | `pytest tests/unit/test_dgp.py -k season -x` | ❌ W0 | ⬜ pending |
| TBD (planner-assigned) | TBD | TBD | SIM-074 | — | Adstock closed-form + impulse test (impulse first — catches direction reversal, Pitfall 4); Hill(K)=0.5 exact; D-03 hypothesis properties (pending ADR, Pitfall 2) | unit + property | `pytest tests/unit/test_dgp.py -k "adstock or hill" -x` | ❌ W0 | ⬜ pending |
| TBD (planner-assigned) | TBD | TBD | SIM-060/061 | — | φ/θ platform-bias formulas; NULL offline handling; hand-computed example | unit | `pytest tests/unit/test_platform_bias.py -x` | ❌ W0 | ⬜ pending |
| TBD (planner-assigned) | TBD | TBD | SIM-071/072 | — | Decomposition audit ≤1e-6; media-share/noise-variance plausibility bounds | unit | `pytest tests/unit/test_dgp.py -k assemble -x` | ❌ W0 | ⬜ pending |
| TBD (planner-assigned) | TBD | TBD | SIM-075 | — | truth.json schema-complete; S-C zero-ROAS spot check; byte-stable (sort_keys, fixed float fmt) | unit | `pytest tests/unit/test_truth.py -x` | ❌ W0 | ⬜ pending |
| TBD (planner-assigned) | TBD | TBD | SIM-070 | — | Two `make simulate` runs byte-identical | integration | `pytest tests/unit/test_simulate_cli.py -k determinism -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_scenario_config.py` — stubs for SIM-002, BP-G-02, REQ-grain-and-windows
- [ ] `tests/unit/test_spend_patterns.py` — stubs for SIM-030, SIM-031
- [ ] `tests/unit/test_dgp.py` — stubs for SIM-073, SIM-074, SIM-071, SIM-072 (+ D-03 hypothesis properties once the ADR lands)
- [ ] `tests/unit/test_platform_bias.py` — stubs for SIM-060, SIM-061
- [ ] `tests/unit/test_truth.py` — stubs for SIM-075
- [ ] `tests/unit/test_simulate_cli.py` — stubs for SIM-070, the gate-runner's own exit-code behavior
- [ ] Framework install: no new pytest infra needed. `hypothesis` is the only new install (dev dependency), gated behind an ADR + `checkpoint:human-verify` on its automated `SUS` legitimacy verdict (see 02-RESEARCH.md Pitfall 2 and Package Legitimacy Audit) before `uv add`
- [ ] `conftest.py` already has a `repo_root` fixture (Phase 1) — reusable as-is; no new shared fixture needed unless a scenario-config-loading fixture proves useful across multiple test files

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification. The one human touchpoint is process, not test coverage: `checkpoint:human-verify` on the `hypothesis` package's automated SUS legitimacy verdict before it is added as a dev dependency (research assesses this as very likely a false positive given hypothesis's 12+-year PyPI history, but the project's own governance protocol requires the human gate regardless).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
