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
| Task 2 (structural half) | 02-02 | 1 | SIM-002, REQ-grain-and-windows | T-02-04, T-02-05 | `extra='forbid'`; weeks ∈ {156,104,78}; (id, weeks, seed) triple pinned to SPEC-01 §5; S-C ⇔ zero β; schedules inside the window; adjacent bursts accepted, overlap rejected | unit | `pytest tests/unit/test_scenario_config.py -x` | ❌ W0 | ⬜ pending |
| Task 3 (value half) | 02-03 | 2 | SIM-002/BP-G-02, REQ-grain-and-windows | T-02-08, T-02-10 | Scenario YAML == SPEC-01 §4 table (proven to bite); S-C/S-B diff is rule-level, not literal (Pitfall 7); exact week counts 156/104/78 cross-checked against the seed; ISO-Monday endpoints | unit | `pytest tests/unit/test_scenario_config.py -k "spec_parameter_table or rule_level or weeks" -x` | ❌ W0 | ⬜ pending |
| Task 1 | 02-04 | 3 | SIM-073 (season half), REQ-grain-and-windows | T-02-16 | Gapless ISO-Monday spine from the committed seed; missing/duplicate seed row raises; season weights exact; unflagged week is exactly 1.0 | unit | `pytest tests/unit/test_dgp.py -k season -x` | ❌ W0 | ⬜ pending |
| Tasks 2 and 3 | 02-04 | 3 | SIM-074 | T-02-13, T-02-14, T-02-15 | Impulse test written and run **before** the closed-form test (catches direction reversal, Pitfall 4); Hill(K)=0.5 exact to 1e-12; domain violations raise `SimulationError`; D-03 hypothesis properties incl. a generative causality twin | unit + property | `pytest tests/unit/test_dgp.py -k "adstock or hill" -x` | ❌ W0 | ⬜ pending |
| Task 2 | 02-05 | 4 | SIM-030/031 | T-02-18, T-02-19, T-02-20 | Annual totals ±10% against independently re-derived design values; flighted zero-week share exact vs schedule and ±10 pp vs §3 nominal; floor/round/multiply order per Guide §1.3 proven to bite (Pitfall 6); documented draw order pinned | unit | `pytest tests/unit/test_spend_patterns.py -x` | ❌ W0 | ⬜ pending |
| Task 2 | 02-06 | 5 | SIM-071/072, SIM-073 (peak-week half) | T-02-23, T-02-24, T-02-25 | Decomposition audit ≤ 1e-6 enforced at construction; media-share and noise-variance plausibility bounds; peak revenue week in Advent per audited year; SIM-004 column order and media row ordering | unit | `pytest tests/unit/test_dgp.py -k assemble -x` | ❌ W0 | ⬜ pending |
| Task 2 | 02-07 | 6 | SIM-060/061 | T-02-28, T-02-29, T-02-30 | φ/θ read from config, hand-computed example to 1e-9; offline channels NULL in all three columns; zero-total-spend week yields share 0 with no NaN; over-credit ordering present (S-A/S-B) | unit | `pytest tests/unit/test_platform_bias.py -x` | ❌ W0 | ⬜ pending |
| Task 3 | 02-08 | 7 | SIM-075, SIM-070 (truth-file half) | T-02-32, T-02-34, T-02-35 | truth.json schema-complete; S-C zero-ROAS spot check exact; byte-stable across two writes (sort_keys, `%.10g`, LF, atomic); `response_curve_at` accepts a caller-supplied grid | unit | `pytest tests/unit/test_truth.py -x` | ❌ W0 | ⬜ pending |
| Task 3 | 02-09 | 8 | SIM-070, REQ-grain-and-windows | T-02-37, T-02-38, T-02-40 | Two runs byte-identical across all nine artifacts, with non-empty preconditions asserted first; gate runner fails on a corrupted and on a missing artifact; CSV contract asserted against written bytes | integration | `pytest tests/unit/test_simulate_cli.py -k determinism -x` | ❌ W0 | ⬜ pending |
| Task 1 | 02-10 | 9 | SIM-070…075 (phase gate) | T-02-43, T-02-45 | Committed artifacts survive a `git checkout` round-trip with `make validate-sim` still green (the `core.autocrlf` failure mode plan 01-07 hit) | integration | `make validate-sim` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Every gap below is closed inside the plan that creates the code it covers — no test file is
back-filled after the fact, and no plan ships a module whose gate has no runnable command.

- [ ] `tests/unit/test_scenario_config.py` — created in **02-02 Task 2** (structural half: SIM-002, REQ-grain-and-windows), extended in **02-03 Task 3** (value half: BP-G-02 spec-table equality, counting rules, rule-level S-C↔S-B diff)
- [ ] `tests/unit/test_dgp.py` — created in **02-04 Task 1** (SIM-073 season half), extended in **02-04 Tasks 2–3** (SIM-074 point tests + D-03 hypothesis properties) and **02-06 Task 2** (SIM-071, SIM-072, SIM-073 peak-week half)
- [ ] `tests/unit/test_spend_patterns.py` — created in **02-05 Task 2** (SIM-030, SIM-031)
- [ ] `tests/unit/test_platform_bias.py` — created in **02-07 Task 2** (SIM-060, SIM-061)
- [ ] `tests/unit/test_truth.py` — created in **02-08 Task 3** (SIM-075 + byte-stability)
- [ ] `tests/unit/test_simulate_cli.py` — created in **02-09 Task 3** (SIM-070 + gate-runner exit codes + the written-bytes CSV contract)
- [ ] Framework install: no new pytest infra needed. `hypothesis` is the only new install (dev dependency), delivered by **02-01** — ADR-007 (EB-030) plus a blocking `checkpoint:human-verify` on its automated `SUS` legitimacy verdict before `uv add`, and `.hypothesis/` added to `.gitignore` in the same plan. 02-01 is wave 1 and 02-04 (the first plan importing `hypothesis`) is wave 3, so the ordering constraint holds structurally, not only by convention.
- [ ] `conftest.py` already has `repo_root`, `seeded_rng` and `tmp_repo` fixtures (Phase 1) — reused as-is; the only new autouse fixture is `load_scenario.cache_clear()` in `test_scenario_config.py`, mirroring `test_config.py`'s `_clear_settings_cache`

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification. The two human touchpoints are process, not test coverage:*

1. **02-01 Task 2** — blocking `checkpoint:human-verify` on the `hypothesis` package's automated SUS legitimacy verdict before it is added as a dev dependency (research assesses this as very likely a false positive given hypothesis's 12+-year PyPI history, but the project's own governance protocol requires the human gate regardless, and `workflow.auto_advance` does not apply to it).
2. **02-10 Task 3** — blocking `checkpoint:human-verify` for the M1 milestone sign-off: the `06_CHECKLISTS.md` `[STD]` and M1 blocks ticked with evidence, the seven-row gate table, the SIM-070 hash pair, the coverage figure, and the Charter §5 effort total checked against 720 / 1440 minutes.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — every task in all ten plans carries a `<verify><automated>` command
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — no plan has a task without one
- [x] Wave 0 covers all MISSING references — each of the six test modules is created inside the plan that ships the code it covers
- [x] No watch-mode flags — every command is a single-shot `pytest`/`make`/`uv run` invocation
- [ ] Feedback latency < 30s — holds for `test_scenario_config.py`, `test_spend_patterns.py`, `test_platform_bias.py`; `test_dgp.py` targets < 90s once the property tests and the assemble tests land, and `test_simulate_cli.py` targets < 120s because it regenerates all nine artifacts twice. Per-task quick-run selectors (`-k season`, `-k "adstock or hill"`, `-k assemble`, `-k determinism`) stay inside the 30s target; the > 30s figures apply only to whole-file runs. Measured runtimes are recorded in each plan's SUMMARY.
- [ ] `nyquist_compliant: true` set in frontmatter — set by `/gsd-validate-phase` after the measured runtimes confirm the latency row

**Approval:** pending
