---
phase: 02-ground-truth-simulator
verified: 2026-08-05T15:10:00Z
status: passed
score: 5/5 roadmap truths verified (plus 10/10 plan-level artifact sets confirmed present, wired, and green)
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 2: Ground-Truth Simulator — Verification Report

**Phase Goal:** A fictional Austrian advertiser whose every parameter is disclosed in-repo, so
that "the model recovered ROAS" becomes a checkable claim rather than a plot.
**Verified:** 2026-08-05T15:10:00Z
**Status:** passed
**Re-verification:** No — initial verification.

## Method

This phase spans 10 plans (02-01…02-10) building `src/ambo/simulate/` end-to-end. Rather than
trusting each plan's SUMMARY.md narrative, every claim below was re-derived from the live
codebase: the full test suite was run, `make simulate && make validate-sim` was executed and
its gate table inspected directly, `truth.json`/CSV artifacts were opened and spot-checked
field-by-field, `mypy`/`ruff` were run fresh, git history and `REQUIREMENTS.md` were
cross-checked, and the independently-produced `02-REVIEW.md` code-review report (added after
the phase's own plans completed) was read for anything the plan authors might have missed.

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria — the binding contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `make simulate && make validate-sim` produces `data/synthetic/{s_a,s_b,s_c}/` and every SIM-070…075 gate reports green | ✓ VERIFIED | Ran both targets live. Gate table: `SIM-070 PASS`, `SIM-071 PASS`, `SIM-072 PASS`, `SIM-073 PASS`, `SIM-074 PASS`, `SIM-075 PASS`, `BP-G-02 DELEGATED` (its own selector `pytest -k "spec_parameter_table or rule_level"` run in the same invocation, 2 passed). Exit code 0. |
| 2 | Running the simulator twice produces byte-identical CSVs and truth files — determinism is proven, not assumed | ✓ VERIFIED | SIM-070 row prints two SHA-256 hashes (`016aad7d…` committed vs. regenerated) — identical. After `make simulate` regenerated the tree fresh, `git status --short data/synthetic/` showed **zero diff** against the committed bytes — a live re-generation matched the committed artifacts byte-for-byte. `.gitattributes` also pins `*.csv`/`*.json` to `eol=lf`, and the writer independently pins `newline="\n"`, so the round-trip claim in 02-10-SUMMARY.md is architecturally consistent with what was observed. |
| 3 | Each `truth.json` contains every SPEC-01 §4/§6 parameter plus the §8 derived quantities, schema-validated by a committed pydantic model | ✓ VERIFIED | `TruthFile`/`ChannelTruth` (pydantic, `extra="forbid"`, frozen) in `src/ambo/simulate/truth.py`. SIM-075 gate re-reads and re-validates all three files against the schema and against `ScenarioConfig` — PASS. Spot-checked `data/synthetic/s_c/truth.json` directly: `display_video.true_avg_roas == 0.0`, `total_contribution_eur == 0.0`, `contribution_share == 0.0`, `zero_effect_channel == "display_video"` — exact zeros, not near-zero. |
| 4 | Unit tests prove the closed forms independently: adstock converges to `x/(1−λ)`, `Hill(K)=0.5` exactly, max-revenue week falls in Advent, SIM-031 spend-pattern statistics hold | ✓ VERIFIED | `tests/unit/test_dgp.py`: impulse test (`test_adstock_impulse_response_is_causal`, line 264) is written and collected **before** the closed-form test (`test_adstock_closed_form_limit`, line 273) — the project's own trap-T-2 discipline. Live gate evidence: `SIM-074 PASS constant_spend_residual=9.09e-13, impulse_residual=2.78e-17, hill_at_K_residual=0.0`. `SIM-073 PASS` — every audited ISO year's peak week carries `advent_flag=True` (S-C's half-year with no Advent window is explicitly reported as skipped, not silently omitted). `tests/unit/test_spend_patterns.py` SIM-031 tests pass live (26 tests, full suite green). |
| 5 | Scenario YAMLs are the authoritative parameter source, and a test asserts they equal the SPEC-01 §4 table — divergence fails the test, never a silent fix | ✓ VERIFIED | `tests/unit/test_scenario_config.py::test_yaml_matches_spec_parameter_table` hard-codes the SPEC-01 §4 table independently and loads the YAML directly via `yaml.safe_load` (not through `load_scenario`). 02-03-SUMMARY.md documents red-then-green proof (a deliberate `s_a.yaml` edit made the test fail with a named diff, then passed clean after revert) — this is the exact BP-G-02 discipline the truth demands, and the test is present and passing in the live suite today. |

**Score:** 5/5 roadmap truths verified.

### Plan-Level Must-Haves (summarized — 10 plans, ~100 individual truths/artifacts/links)

Rather than re-listing every one of the ~100 plan-level `must_haves` entries individually
(each plan's PLAN.md/SUMMARY.md pair documents its own in detail), this section verifies the
artifacts and key links they collectively produce, confirmed to exist, be substantive, and be
wired — not merely claimed.

| Plan | Artifact(s) | Exists | Substantive | Wired | Status |
|------|-------------|--------|-------------|-------|--------|
| 02-01 | `docs/ADR/ADR-007_hypothesis-dev-dependency.md`, `hypothesis` in `[dependency-groups] dev`, `.hypothesis/` gitignored | ✓ | ✓ (Status: Ratified, indexed in README, verdict/counter-evidence recorded) | ✓ (imported only in `tests/`, never `src/`) | ✓ VERIFIED |
| 02-02 | `src/ambo/simulate/config.py` (`ScenarioConfig` tree), `SimulationError` | ✓ | ✓ (236 stmt, 6 validators, 91% branch coverage) | ✓ (imported by every downstream simulate module) | ✓ VERIFIED |
| 02-03 | `config/scenarios/{s_a,s_b,s_c}.yaml`, `scripts/author_scenario_schedules.py` | ✓ | ✓ (all three load via `load_scenario()` live) | ✓ (BP-G-02 test passing; aid unreachable from `src/`, confirmed by grep) | ✓ VERIFIED |
| 02-04 | `src/ambo/simulate/dgp.py` (week spine, seasonality, adstock, Hill) | ✓ | ✓ (94% coverage; impulse-before-closed-form ordering confirmed in file) | ✓ (`test_import_independence.py` SIM-003 firewall green) | ✓ VERIFIED |
| 02-05 | `src/ambo/simulate/spend_patterns.py` (`generate_spend`) | ✓ | ✓ (96% coverage; no `cfg.id ==` branch present) | ✓ (consumed by `dgp.assemble_scenario`) | ✓ VERIFIED |
| 02-06 | `dgp.py` extension (`SimulationResult`, `assemble_scenario`, 3 audits) | ✓ | ✓ (SIM-071 constructor precondition confirmed live: `decomposition_audit` = 0.0 for all 3 scenarios) | ✓ | ✓ VERIFIED |
| 02-07 | `src/ambo/simulate/platform_bias.py` (`platform_report`) | ✓ | ✓ (96% coverage; hand-computed SIM-060 identity documented) | ✓ (called from CLI, feeds `truth.py`) | ✓ VERIFIED |
| 02-08 | `src/ambo/simulate/truth.py` (`TruthFile`, `response_curve_at`, `write_truth`) | ✓ | ✓ (91% coverage; byte-stability + atomic write confirmed) | ✓ (registered in `MODULE_CONTRACTS.md`, consumed by CLI) | ✓ VERIFIED |
| 02-09 | `src/ambo/simulate/__main__.py`, `Makefile` targets | ✓ | ✓ (92% coverage; 7-row gate table runs live, confirmed above) | ✓ (`make simulate`/`make validate-sim` both exercised live) | ✓ VERIFIED |
| 02-10 | `data/synthetic/{s_a,s_b,s_c}/` (9 files), `docs/BUILD_LOG.md` M1 entry | ✓ | ✓ (all 9 files present, non-empty, spot-checked) | ✓ (`git ls-files data/synthetic` = 10, incl. `.gitkeep`) | ✓ VERIFIED |

### Requirements Coverage

| Requirement | Phase Role | Description | Status | Evidence |
|-------------|-----------|--------------|--------|----------|
| REQ-q1-truth-recovery | Contributing (owned by Phase 5) | Model recovers known truth incl. zero-effect channel | ✓ SATISFIED (as a contributing phase) | `REQUIREMENTS.md` traceability table correctly still shows this `Pending` with Phase 5 as owner and Phases 2/3/4 as "Also touches" — every plan in this phase (02-01…02-10) deliberately did **not** call `requirements.mark-complete`, each SUMMARY documenting why (02-01-SUMMARY.md even records reverting an accidental premature mark-complete). This is the correct behavior for a contributing phase, not a gap. |
| REQ-grain-and-windows | Contributing (owned by Phase 6) | ISO weeks, Layer P grain per SPEC-01 §5 | ✓ SATISFIED (as a contributing phase) | Same traceability discipline: `REQUIREMENTS.md` line 196 shows `Phase 6 | Phases 2, 3 | Pending` — correct, not falsely marked complete. The Layer P grain itself (156/104/78 weeks, ISO Monday spine) is enforced by `ScenarioConfig` validators and `week_index()`, live-tested. |

No orphaned requirements: `.planning/REQUIREMENTS.md`'s own "Coverage note" section explicitly documents that Phases 2/3/4 own no Charter requirement by design (SPEC-tier contract instead), matching the phase brief given to this verifier.

### Anti-Patterns Found

An independent code-review pass (`02-REVIEW.md`, added to the phase directory after plan
execution, `git log` commit `41c57f7`) found **0 critical, 5 warning, 1 info** findings — all
validation-gap / edge-case-correctness issues, none of which are reachable through the
currently-shipped scenario YAMLs or CLI surface:

| File | Finding | Severity | Impact |
|------|---------|----------|--------|
| `truth.py:104-114` | `marginal_roas_at`'s zero-spend branch returns `0.0` instead of the correct finite value when `s == 1.0` exactly (affects `search_generic`, used in all 3 scenarios) | ⚠️ Warning | Unreachable in the shipped pipeline (`compute_truth` always raises before a zero-mean-spend call), but a future direct caller could get a silently wrong value. |
| `config.py:182-205` | `PlatformBiasParams` (`phi`/`theta`/`cpm`) has no positivity validation, unlike sibling models | ⚠️ Warning | A misauthored future YAML with `cpm<=0` would divide-by-zero into `inf`/`nan` rather than raising `SimulationError`. Shipped YAMLs are all correctly authored. |
| `config.py:246-262` | `ScenarioConfig`'s top-level scalars (`b0`, `growth`, `noise_share`, `aov_base`, etc.) have no domain validators, unlike every other numeric field in the file | ⚠️ Warning | Same class of gap — inconsistent with the file's own otherwise-scrupulous discipline; not currently reachable. |
| `dgp.py:334-373` | `SimulationResult`'s docstring claims immutability ("cannot exist in a violating state") but the frozen dataclass does not prevent in-place `DataFrame` mutation | ⚠️ Warning | Documentation overstates the guarantee; no test in the shipped suite is affected (tests that need a violating state `.copy()` first). |
| `truth.py:337-363` | `write_truth`'s `json.dumps` call leaves `allow_nan` at its Python default (`True`), so a future `NaN`/`Infinity` would serialize as non-RFC-8259 tokens instead of raising | ⚠️ Warning | Not currently reachable (no NaN reaches this path with the shipped data); would be caught after-the-fact by SIM-075's reload-and-revalidate, but only after already being committed. |
| `dgp.py:50-63` | `round_half_up` documents but does not enforce a non-negative-input assumption | ℹ️ Info | Defense-in-depth suggestion; not a defect against current usage. |

**Disposition:** None of these findings falsify the phase goal. The three shipped scenarios
(S-A, S-B, S-C) are correctly parameterized, generate correctly, and every SIM-070…075 gate
is green with margin on the actual committed data — "the model recovered ROAS" is a checkable
claim today. The findings describe **defense-in-depth gaps** for hypothetical future misuse
(a badly-authored YAML, a direct call to an internal function with an out-of-domain argument)
rather than defects in what was actually shipped. They are legitimate backlog items and are
already written down in a dated, git-tracked report — recommend a small follow-up plan or an
explicit backlog entry before Phase 6 (Agency Intake) starts authoring new YAML-driven
config, since that is where a missing validator would first become reachable by a human
typo. No `TODO`/`FIXME`/`XXX` markers exist in any file this phase touched.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `uv run pytest tests/unit/` | 281 passed, 93% coverage of `src/ambo/` | ✓ PASS |
| Type checking | `uv run mypy` | Success: no issues found in 17 source files | ✓ PASS |
| Lint (code, not planning-doc markdown) | `uv run ruff check .` | All checks passed! | ✓ PASS |
| Simulator generation | `make simulate` | 3 scenarios written in ~0.05s each, exit 0 | ✓ PASS |
| Gate runner | `make validate-sim` | 7-row table, all PASS/DELEGATED, exit 0 | ✓ PASS |
| Impulse-before-closed-form ordering | `grep -n` line numbers in `test_dgp.py` | impulse test at line 264, closed-form at line 273 | ✓ PASS |
| Property-based invariants collected | `pytest -k "bounded or monotone or causal or unit_fraction" --collect-only` | 6 collected (≥5 required) | ✓ PASS |
| Zero-effect channel exact zero | Direct read of `data/synthetic/s_c/truth.json` | `0.0`/`0.0`/`0.0`, never near-zero | ✓ PASS |
| CSV NULL discipline | `head` of `media_weekly.csv` | Header exact SIM-004 match; no CR bytes (`grep -c $'\r'` = 0) | ✓ PASS |
| Debt markers | `grep -rn "TBD\|FIXME\|XXX"` across all Phase 2 touched files | No matches | ✓ PASS |
| No fictional-advertiser narrative leaked into Phase 2 | `grep -ni "alpentrek"` across scenario YAMLs and `src/` | No matches | ✓ PASS |

### Human Verification Required

None. Every must-have this phase declares is either a mechanically-checkable artifact/test
(verified above by direct execution) or an explicit human checkpoint the phase itself already
resolved and documented in git history:

- **02-01 Task 2** (package-legitimacy SUS verdict for `hypothesis`) — human approval string
  `"approved"` recorded verbatim in `02-01-SUMMARY.md` with the checker output and
  counter-evidence pasted, commit order verified (ADR commit precedes `uv.lock` commit).
- **02-10 Task 3** (M1 milestone sign-off) — human approval string `"Approved"` recorded
  verbatim in `docs/BUILD_LOG.md`'s finalization entry, with the evidence bundle (gate table,
  coverage, effort tally) pasted before the approval was requested.

Both are already-closed human gates, not open items for this verification pass.

### Gaps Summary

No gaps. All 5 ROADMAP.md Success Criteria are independently verified against live command
output, not SUMMARY.md narrative. All 10 plans' artifacts exist, are substantive, and are
wired into the CLI/gate runner that exercises them end-to-end. The full test suite (281
tests), `mypy --strict`, and `ruff check` are all green today. `make simulate && make
validate-sim` produces a 7-row gate table with every row PASS (or DELEGATED-and-passing).
The nine committed data artifacts are present, non-empty, byte-consistent with a fresh
regeneration, and spot-checked for the specific SIM-075/SIM-004 contract details. The
REQUIREMENTS.md traceability table correctly reflects this phase's "contributing, not
owning" status for both of its requirement IDs. An independent code review found only
non-blocking, defense-in-depth warnings — recorded as informational findings above, not as
gaps against this phase's declared must-haves.

---

_Verified: 2026-08-05T15:10:00Z_
_Verifier: Claude (gsd-verifier)_
