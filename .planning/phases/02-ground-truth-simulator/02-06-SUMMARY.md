---
phase: 02-ground-truth-simulator
plan: 06
subsystem: simulate
tags: [numpy, pandas, dataclass, decomposition-audit, sim-071, sim-072, sim-073]

# Dependency graph
requires:
  - phase: 02-04
    provides: "week_index(cfg), baseline_demand(cfg, weeks), adstock_recursive(x, lam), hill(a, K, s), round_half_up(values) -- the calendar spine and the simulator's own transform chain"
  - phase: 02-05
    provides: "generate_spend(cfg, rng, weeks) -- the six SPEC-01 section 3 per-channel weekly spend series, consumed as the generator's first six draw calls"
provides:
  - "SimulationResult (frozen dataclass, SIM-071 constructor precondition), assemble_scenario(cfg, rng) -- the module's orchestrator -- and decomposition_audit/plausibility_audit/peak_week_audit (SIM-071/072/073 evidence functions)"
affects: [02-07, 02-08, 02-09, 02-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Constructor precondition via __post_init__ raising SimulationError -- the decomposition invariant is a type property, not a skippable test"
    - "Function-scoped (deferred) import of generate_spend inside assemble_scenario to break an A-15 import cycle with spend_patterns.py, which imports round_half_up from this same module"
    - "Audit functions return evidence dicts/floats, never bare booleans, so the gate runner (02-09) can print the numbers 10_VALIDATION_GATES.md section 3 requires"
    - "Documented sentinel convention ((-1, True)) for a skipped audit year, so a caller can distinguish 'skipped' from 'silently absent' without inspecting source"

key-files:
  created: []
  modified:
    - src/ambo/simulate/dgp.py
    - docs/MODULE_CONTRACTS.md
    - tests/unit/test_dgp.py

key-decisions:
  - "generate_spend is imported inside assemble_scenario's function body, not at module level -- spend_patterns.py imports round_half_up from dgp.py, so a top-level cross-import in dgp.py would create an A-15 import cycle (dgp -> spend_patterns -> dgp) that fails at first import regardless of which module a caller imports first. A function-scoped import defers the cross-reference until both modules are already fully initialized."
  - "components stores base/season/promo_mult/promo_flag/trend (from baseline_demand) plus adstock_<c>/m_<c> per channel plus eps/revenue_pre_clip/revenue -- a superset of what SIM-071 strictly needs, matching 03_MODULES.md section 2.3's description of the components frame and giving plan 02-08's truth.json aggregation everything it needs without re-deriving it."
  - "media's placeholder impressions/platform_conversions/platform_revenue_eur columns are float64 NaN, populated later by plan 02-07's platform_report -- not typed as nullable Int64, since no consumer of this plan reads them yet and the simplest placeholder avoids an extension-dtype decision that belongs to the module that actually computes real values."
  - "test_assemble_zero_beta_channel_contributes_exactly_zero falls back to the plan's own sanctioned alternative (exact-zero plus exact five-channel-sum equality) instead of a bit-identical S-B-windowed control run: ScenarioConfig._validate_scenario_identity pins (id, weeks, seed) to one of exactly the three frozen SPEC-01 section 5 triples, so no hybrid S-C-window/S-B-beta config can be constructed without bypassing validation -- recorded as the case the plan's own 'where a bit-identical comparison is not achievable' clause anticipates."
  - "peak_week_audit's skipped-year sentinel is (-1, True): -1 is never a valid ISO week (so it can never be confused with a real audited week), and True means 'never fails the every-value-is-True check' -- a caller identifies a skipped year by filtering on peak_week == -1, not by the boolean."

requirements-completed: []  # REQ-q1-truth-recovery and REQ-grain-and-windows remain Phase-5/6-owned per REQUIREMENTS.md traceability table (same decision as 02-02/02-04/02-05) -- not marked complete here.

coverage:
  - id: D1
    description: "assemble_scenario combines baseline demand, the six adstock/Hill media contributions and one noise draw (strictly after generate_spend, on the same generator) into revenue and orders, producing the two SIM-004 frames"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_frame_shapes_and_column_order"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_orders_follow_the_aov_rule"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_promo_flag_matches_the_yaml"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_determinism_same_seed"
        status: pass
    human_judgment: false
  - id: D2
    description: "SIM-071: the decomposition invariant is a SimulationResult constructor precondition (raises SimulationError naming the worst week and its deviation), proven both by all-scenario green audits and by a perturbation test that asserts the constructor raises"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_decomposition_audit_within_tolerance"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_decomposition_violation_raises_at_construction"
        status: pass
    human_judgment: false
  - id: D3
    description: "SIM-072: no negative pre-clip revenue, media share of annual revenue in [15%, 45%], noise variance share in [2%, 10%] -- all three scenarios, each bound asserted separately"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_plausibility_bounds"
        status: pass
    human_judgment: false
  - id: D4
    description: "SIM-073: the maximum-revenue week of every audited ISO year falls inside that year's Advent window; a year whose Advent window is not fully covered is recorded, not silently omitted"
    requirement: "REQ-grain-and-windows"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_peak_revenue_week_is_in_advent"
        status: pass
    human_judgment: false
  - id: D5
    description: "media rows are ordered by week_start then SPEC_CHANNEL_ORDER position with (week_start, channel) unique; outcome rows are ordered by week_start ascending with week_start unique; a zero-beta channel contributes exactly 0.0 and perturbs nothing"
    requirement: "REQ-grain-and-windows"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_media_row_order_is_week_then_taxonomy"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_week_spine_is_iso_monday_and_gapless"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_assemble_zero_beta_channel_contributes_exactly_zero"
        status: pass
    human_judgment: false
  - id: D6
    description: "Contract-first docs/MODULE_CONTRACTS.md dgp.py entry extended with SimulationResult/assemble_scenario/the three audits in the same commit as the code (D-23)"
    verification:
      - kind: unit
        ref: "tests/unit/test_repo_layout.py#test_module_contracts_match_src_ambo_modules_exactly"
        status: pass
    human_judgment: false

# Metrics
duration: ~45min
completed: 2026-08-05
status: complete
---

# Phase 2 Plan 6: Revenue Assembly, Decomposition Audit and SIM-07x Gates Summary

**`assemble_scenario` combines baseline demand, six adstock/Hill media contributions and one post-spend noise draw into revenue and orders, storing every component in a `SimulationResult` whose SIM-071 decomposition invariant is enforced as a constructor precondition rather than a skippable report.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-08-05
- **Tasks:** 2 completed
- **Files modified:** 3 (`src/ambo/simulate/dgp.py`, `docs/MODULE_CONTRACTS.md`, `tests/unit/test_dgp.py` -- no new files; this plan is the second half of an existing `dgp.py`)

## Accomplishments

- `SimulationResult` (frozen dataclass: `cfg`, `weeks`, `spend`, `components`, `media`, `outcome`) runs the SIM-071 re-sum in `__post_init__` and raises `SimulationError` -- naming the worst week and its absolute deviation -- when `components` do not re-sum to `revenue_pre_clip` within 1e-6, so a `SimulationResult` that violates the decomposition invariant cannot be constructed.
- `assemble_scenario(cfg, rng)` is the module's sole orchestrator: `week_index` -> `baseline_demand` -> `generate_spend` (the generator's first six draw calls) -> a plain per-channel adstock/Hill loop in `SPEC_CHANNEL_ORDER` (never vectorized across channels, A-14) -> one `rng.normal(0.0, sigma, size=T)` noise draw strictly after `generate_spend` on the same generator (SPEC-01 section 2.3) -> the `>= 0` revenue clip -> `orders` via `round_half_up` -> the two SIM-004 frames.
- `generate_spend` is imported inside `assemble_scenario`'s function body rather than at module level: `spend_patterns.py` imports `round_half_up` from `dgp.py`, so a top-level cross-import in `dgp.py` would create an A-15 import cycle. The deferred import breaks the cycle regardless of which module a caller imports first.
- `decomposition_audit`, `plausibility_audit`, `peak_week_audit` return evidence (a float, a stats dict, a per-year mapping) rather than a bare boolean, so plan 02-09's gate runner can print the numbers `10_VALIDATION_GATES.md` section 3 requires. `peak_week_audit` records a year whose Advent window is not fully covered under a documented sentinel `(-1, True)` instead of omitting it silently.
- SIM-071, SIM-072 and SIM-073 are green for all three scenarios, with the realized numbers pasted below.
- 29 tests appended to `tests/unit/test_dgp.py` (`-k assemble` selects the group), covering the audits, frame shape/column-order pinning, the gapless week spine, media row ordering (the taxonomy-not-alphabetical assertion), the AOV orders rule, promo-flag/YAML matching, the zero-effect channel, and same-seed determinism. Full file: 80 tests, 6.9s.
- The contract-first `docs/MODULE_CONTRACTS.md` `dgp.py` entry was extended with the five new symbols' signatures, the constructor-precondition invariant, the noise-after-spend draw order, and the two frame schemas, in the same commits as the code (D-23).

## Realized SIM-072 numbers (all three scenarios, M1 checklist)

Computed with `np.random.default_rng(cfg.seed)` per scenario -- `decomposition_audit` max abs deviation, `plausibility_audit` stats, `peak_week_audit` per-year peak:

| Scenario | SIM-071 max abs deviation | min_revenue_pre_clip | noise_variance_share | media_share by year |
|---|---|---|---|---|
| S-A (seed 101) | 0.0 | 64,094.84 | 0.03114 | 2021: 0.2730, 2022: 0.2663, 2023: 0.2575 |
| S-B (seed 202) | 0.0 | 70,242.79 | 0.02636 | 2022: 0.2744, 2023: 0.2625 |
| S-C (seed 303) | 0.0 | 62,307.91 | 0.03959 | 2022: 0.2473, 2023: 0.2559 |

All bounds hold with margin: `min_revenue_pre_clip >= 0` for all three (the clip never binds), `noise_variance_share` in `[0.02636, 0.03959]` well inside `[0.02, 0.10]`, every `media_share_<year>` in `[0.2473, 0.2744]` well inside `[0.15, 0.45]`.

**SIM-073 peak weeks:** S-A: `{2021: (50, True), 2022: (51, True), 2023: (50, True)}`. S-B: `{2022: (50, True), 2023: (50, True)}`. S-C: `{2022: (50, True), 2023: (-1, True)}` -- S-C's 2023 entry is the documented skipped-year sentinel: its half-year window (ISO weeks 01-26) contains no Advent window, so SIM-073 audits 2022 only for that scenario. Every audited year's peak-revenue week carries `advent_flag == 1`.

**For `docs/BUILD_LOG.md` at M1 close:** S-C's 2023 half-year (ISO weeks W01-W26) contains no Advent window; this is a covered-window consequence of the scenario's declared start/end (SPEC-01 section 5: S-C is 78 weeks starting 2022-W01), not a SIM-073 gate relaxation. `peak_week_audit` detects this without recomputing any calendar rule -- a year is audited only if at least one of its rows carries `advent_flag == 1`.

## Task Commits

Each task was committed atomically:

1. **Task 1: SimulationResult and assemble_scenario** - `acaf4bd` (feat)
2. **Task 2: SIM-071/072/073 audits and their tests** - `b5f51ce` (test)

**Plan metadata:** committed as part of this summary's own commit.

## Files Modified

- `src/ambo/simulate/dgp.py` -- appended `SimulationResult`, `_max_decomposition_deviation` (shared helper), `assemble_scenario`, `decomposition_audit`, `plausibility_audit`, `peak_week_audit`, and the `_CONTRIBUTION_COLUMNS` module constant
- `docs/MODULE_CONTRACTS.md` -- extended the `### src/ambo/simulate/dgp.py` entry's Public API, Invariants, Failure modes and Testing sections
- `tests/unit/test_dgp.py` -- 29 tests appended covering `assemble_scenario` and the three SIM-07x audits (parameterized over all three scenarios where applicable)

## Decisions Made

- `generate_spend` is imported inside `assemble_scenario`'s function body, not at module level -- recorded above and in the module docstring, since `spend_patterns.py`'s existing `from ambo.simulate.dgp import round_half_up` makes a top-level cross-import in `dgp.py` an A-15 import cycle.
- `components` stores the full `baseline_demand` output (`trend`, `season`, `promo_mult`, `promo_flag`, `base`) plus per-channel `adstock_<c>`/`m_<c>` plus `eps`/`revenue_pre_clip`/`revenue` -- a superset of what SIM-071 strictly needs, matching `03_MODULES.md` section 2.3's description and pre-supplying everything plan 02-08's `truth.json` aggregation needs.
- `media`'s three platform placeholder columns are float64 NaN rather than a nullable `Int64` extension dtype -- the simplest placeholder, since the module that actually computes real values (`platform_bias.py`, plan 02-07) owns that dtype decision.
- `test_assemble_zero_beta_channel_contributes_exactly_zero` uses the plan's own sanctioned fallback (exact-zero plus exact five-channel-sum equality) instead of a bit-identical S-B-windowed control run, because `ScenarioConfig._validate_scenario_identity` pins `(id, weeks, seed)` to one of exactly the three frozen SPEC-01 section 5 triples -- no hybrid config is constructible without bypassing validation.
- `peak_week_audit`'s skipped-year sentinel is `(-1, True)`: `-1` is never a valid ISO week, and `True` means the sentinel can never itself fail the "every audited year's boolean is True" check -- a caller filters on `peak_week == -1` to detect a skip.

## Deviations from Plan

None -- plan executed exactly as written, including its own explicitly-sanctioned fallback for the zero-beta-channel test (recorded as a Decision above, not a Rule 1-4 deviation, since the plan text itself names this fallback as the expected outcome when a bit-identical comparison is not achievable).

## Issues Encountered

- `make lint` (`ruff format --check .` over the whole repo) still fails on the pre-existing, already-deferred `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`/`02-RESEARCH.md` markdown formatting issue first logged by 02-01 and re-confirmed by 02-04 and 02-05 -- re-confirmed here as still out of scope (neither file is in this plan's `files_modified`, neither was touched by either task). `uv run ruff check .` (lint proper), `uv run mypy` (strict, whole `src/ambo`), and `uv run ruff format --check` scoped to this plan's own three files all pass cleanly. `make test` passes fully (215 passed, up from 186 before this plan).

## Next Phase Readiness

- `SimulationResult`, `assemble_scenario`, `decomposition_audit`, `plausibility_audit` and `peak_week_audit` are available for plan 02-07 (`platform_bias.platform_report`, which populates `media`'s three placeholder columns) and plan 02-08 (`truth.py`'s `compute_truth`, which aggregates `SimulationResult.components` into `truth.json`).
- Measured `test_dgp.py` runtime (6.9s for 80 tests, far under the 90s ceiling) recorded here for the Charter section 5 effort tally, per this plan's own `<output>` instruction.
- No blockers for 02-07.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: src/ambo/simulate/dgp.py
- FOUND: tests/unit/test_dgp.py
- FOUND: docs/MODULE_CONTRACTS.md
- FOUND: acaf4bd (Task 1 commit)
- FOUND: b5f51ce (Task 2 commit)
