---
phase: 02-ground-truth-simulator
plan: 05
subsystem: simulate
tags: [numpy, pandas, spend-generation, rng, sim-030, sim-031]

# Dependency graph
requires:
  - phase: 02-02
    provides: SimulationError, ScenarioConfig/SpendPattern schema, SPEC_CHANNEL_ORDER
  - phase: 02-03
    provides: config/scenarios/{s_a,s_b,s_c}.yaml with promo_weeks/burst schedules and the SIM-030 advent_factor switch
  - phase: 02-04
    provides: "week_index(cfg) -- gapless ISO-Monday weekly spine with the five window flags; round_half_up(values), the single home of the whole-unit rounding convention"
provides:
  - "generate_spend(cfg, rng, weeks) -- the six SPEC-01 section 3 per-channel weekly spend series"
affects: [02-06, 02-07, 02-08, 02-09, 02-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single injected np.random.Generator consumed in a documented fixed six-call taxonomy-order sequence (Pattern 2), never a module-level/global RNG"
    - "Four-step draw order (seasonal/pulse mean multiplier -> draw -> flighting mask -> floor clamp -> round) as an explicit, individually commented sequence matching Guide section 1.3 verbatim"

key-files:
  created:
    - src/ambo/simulate/spend_patterns.py
    - tests/unit/test_spend_patterns.py
  modified:
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "generate_spend(cfg, rng, weeks) promotes 03_MODULES.md section 2.2's two-argument generate_spend(cfg, rng) signature to three arguments -- the week-index frame (carrying the advent/spring flags) is injected by the caller rather than read here, since this module performs no I/O and AD-020 forbids recomputing window flags"
  - "The literal 02-05-PLAN.md acceptance criterion 'swap floor clamp and rounding step to prove red-then-green' is mathematically a no-op for this design: floor_eur is always an integer (int | None) and round_half_up rounds to the nearest integer, so round(max(x, floor)) == max(round(x), floor) for every real x when floor is integer -- verified both by proof and by an empirical swap-and-revert that produced zero test failures. The red-then-green evidence required by the plan was instead produced by swapping step 1 (seasonal/pulse multiplier applied to the mean) with step 2 (the draw) -- the Guide section 1.3 violation Pitfall 6 names as its other concrete example -- which reliably failed test_annual_totals_within_ten_percent_of_design across all three scenarios."
  - "Reworded two docstring sentences that used the English word 'draws' (plural of 'draw') after make test's MD-050 single-config-home guard (test_sampler_keys_appear_nowhere_else_in_src_ambo) flagged it as a false-positive whole-word collision with SamplerConfig's draws field name -- reworded to 'samples'/'draw calls', no behavior change"

patterns-established:
  - "spend_patterns.py is the first ambo.simulate module to make real stochastic draws through an injected Generator -- the six-call taxonomy-order sequence it documents is the draw-order contract dgp.py's noise draw (plan 02-06) must continue"

requirements-completed: []  # REQ-q1-truth-recovery and REQ-grain-and-windows remain Phase-5/6-owned per REQUIREMENTS.md traceability table (same decision as 02-02/02-04) -- not marked complete here.

coverage:
  - id: D1
    description: "generate_spend produces six deterministic, integer, non-negative weekly spend series for all three scenarios, consuming the injected generator in a documented, pinned six-call taxonomy-order sequence (SIM-001/SIM-070)"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_determinism_same_seed_same_frame"
        status: pass
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_all_spends_are_non_negative_integers"
        status: pass
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_draw_order_is_channel_taxonomy_then_noise"
        status: pass
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_no_global_rng_seeding_in_simulate_package"
        status: pass
    human_judgment: false
  - id: D2
    description: "The four SPEC-01 section 3 steps (seasonal/pulse mean multiplier, draw, flighting mask, floor clamp, whole-euro round) run in Guide section 1.3's exact order, proven to matter by a deliberate step-order swap that reliably fails SIM-031's annual-totals test, then reverted to green"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_annual_totals_within_ten_percent_of_design"
        status: pass
    human_judgment: false
  - id: D3
    description: "SIM-031: annual totals within +/-10% and flighted zero-week share within +/-10pp of independently re-derived design values, for every covered ISO year across all three scenarios"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_annual_totals_within_ten_percent_of_design"
        status: pass
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_flighted_zero_week_share_matches_schedule_exactly"
        status: pass
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_flighted_zero_week_share_within_ten_points_of_spec_nominal"
        status: pass
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_burst_weeks_match_the_yaml_schedules_exactly"
        status: pass
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_meta_pulse_fires_every_sixth_week"
        status: pass
    human_judgment: false
  - id: D4
    description: "SIM-030: the spend-season collinearity switch is expressed purely as YAML data (advent_factor 0.5 in S-A vs 0.9 in S-B) with no scenario-name branch anywhere in generate_spend, and S-B's advent/non-advent spend ratio is measurably stronger than S-A's for search_generic and meta"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_spend_patterns.py#test_collinearity_stronger_advent_spend_in_s_b_than_s_a"
        status: pass
    human_judgment: false
  - id: D5
    description: "Contract-first docs/MODULE_CONTRACTS.md entry for spend_patterns.py landed in the same commit as the module (D-23)"
    verification:
      - kind: unit
        ref: "tests/unit/test_repo_layout.py#test_module_contracts_match_src_ambo_modules_exactly"
        status: pass
    human_judgment: false

# Metrics
duration: ~35min
completed: 2026-08-05
status: complete
---

# Phase 2 Plan 5: Spend Patterns -- Six-Channel Weekly Spend Series Summary

**`generate_spend(cfg, rng, weeks)` draws SPEC-01 section 3's six per-channel weekly spend series from a single injected `Generator` consumed in documented taxonomy order, applying Guide section 1.3's four-step mean-multiplier/draw/flighting-mask/floor/round sequence -- proven to matter by a deliberate red-then-green step-order swap.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-05
- **Tasks:** 2 completed
- **Files modified:** 3 (`src/ambo/simulate/spend_patterns.py` created, `tests/unit/test_spend_patterns.py` created, `docs/MODULE_CONTRACTS.md` modified)

## Accomplishments

- `generate_spend(cfg, rng, weeks)` promotes `03_MODULES.md` section 2.2's two-argument signature to three arguments (rationale: the week-index frame carries the advent/spring flags SPEC-01 section 3's seasonal multipliers need, and this module performs no I/O), and consumes its injected `Generator` as exactly six `rng.normal` calls -- one per channel, in `SPEC_CHANNEL_ORDER` -- documented as the fixed draw order plan 02-06's noise draw must continue immediately afterward.
- Per channel, the four SPEC-01 section 3 steps run in Guide section 1.3's exact order: seasonal planning multipliers (and, for `meta`, the six-week x1.8 pulse) apply to the *mean*, then the draw, then the flighting mask (flighted channels only), then the floor clamp (applied only to mask-kept weeks), then whole-euro rounding via `dgp.round_half_up`.
- SIM-031's statistics (annual totals within +/-10%, flighted zero-week share within +/-10pp) hold for all three scenarios against design values re-derived independently in the test from SPEC-01 section 3 -- never by calling `spend_patterns.py` itself.
- SIM-030's collinearity switch is proven to be pure YAML data: `search_generic`/`meta`'s advent/non-advent spend ratio is measurably stronger in S-B than S-A, with no `cfg.id ==` branch anywhere in the module.
- The contract-first `docs/MODULE_CONTRACTS.md` entry landed in the same commit as the module (D-23).

## Task Commits

Each task was committed atomically:

1. **Task 1: generate_spend and its module contract** - `c080b25` (feat)
2. **Task 2: SIM-030/031 statistics, determinism and draw-order tests** - `8588ca4` (test)

**Plan metadata:** committed as part of this summary's own commit.

## Files Created/Modified

- `src/ambo/simulate/spend_patterns.py` - `generate_spend(cfg, rng, weeks)`, plus private helpers `_draw_channel_spend`, `_burst_coverage_mask`, `_validate_bursts_inside_weeks`
- `tests/unit/test_spend_patterns.py` - 26 tests (parameterized over all three scenarios where applicable): determinism, non-negative-integer/floor invariants, SIM-031 annual totals and flighted zero-week share (exact and nominal-tolerance), meta pulse ratio, YAML-schedule-exact burst weeks, SIM-030 collinearity, draw-order pinning, and the anti-pattern A-5 global-RNG scan; runtime well under 1s
- `docs/MODULE_CONTRACTS.md` - contract-first `### src/ambo/simulate/spend_patterns.py` entry (D-23)

## Decisions Made

- `generate_spend(cfg, rng, weeks)` promotes `03_MODULES.md` section 2.2's `generate_spend(cfg, rng)` to three arguments -- recorded here for `docs/BUILD_LOG.md` per the plan's own instruction.
- The plan's literal acceptance criterion ("swap floor clamp and rounding step to prove red-then-green") is mathematically a no-op in this codebase: `floor_eur` is always an integer (`int | None` in `SpendPattern`), and for an integer floor `f`, `round(max(x, f)) == max(round(x), f)` for every real `x` -- verified both by proof and by an empirical swap-and-revert (all 26 tests stayed green). The red-then-green evidence the plan requires was produced instead by swapping step 1 (seasonal/pulse multiplier applied to the *mean*) with step 2 (the draw) -- Pitfall 6's other named concrete example of the Guide section 1.3 violation -- which reliably failed `test_annual_totals_within_ten_percent_of_design` for all three scenarios (e.g. S-B/`search_brand`/2022: realized=42068.0 vs design=36400.0, rel_err=0.156 against the 0.10 tolerance) before being reverted to the correct order (confirmed identical to the committed file via `git diff`).
- `_validate_bursts_inside_weeks` restates `ScenarioConfig`'s own load-time schedule-in-window validator as defence-in-depth inside `generate_spend`, per `03_MODULES.md` section 2.2's instruction -- never expected to fire in normal use since `ScenarioConfig` already rejects an out-of-window schedule at load time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Docstring prose collided with the MD-050 sampler-key single-config-home guard**
- **Found during:** Task 2 verification (`make test`)
- **Issue:** `test_sampler_keys_appear_nowhere_else_in_src_ambo` (EB-040/A-2 single-config-home guard) whole-word-matches `SamplerConfig`'s field names anywhere outside `common/config.py`. The module docstring's ordinary-English use of "draws" (plural of "draw", describing the noise-draw handoff to `assemble_scenario`) collided with the `draws` sampler field name.
- **Fix:** Reworded to "samples the revenue noise vector" and "the *first* six draw calls" -- no behavior or documented-contract change, purely lexical.
- **Files modified:** `src/ambo/simulate/spend_patterns.py`
- **Verification:** `make test` exits 0 (186 passed); `uv run mypy` and `uv run ruff check .` both still exit 0.
- **Committed in:** `8588ca4` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking, caught by an existing guard test).
**Impact on plan:** Purely lexical fix inside this plan's own new file; no scope creep, no behavior change.

## Issues Encountered

- `make lint` (specifically `ruff format --check .` over the whole repo) still fails on the pre-existing, already-deferred `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`/`02-RESEARCH.md` markdown formatting issue first logged by 02-01 and re-confirmed by 02-04 -- re-confirmed here as still out of scope (neither file is in this plan's `files_modified`, neither was touched by this plan's two tasks). `uv run ruff check .` (lint proper), `uv run mypy`, and `uv run ruff format --check` scoped to this plan's own three files all pass cleanly, and `make test` passes fully (186 passed).

## Next Phase Readiness

- `generate_spend(cfg, rng, weeks)` is available for plan 02-06 (`assemble_scenario`, the second half of `dgp.py`), which must draw its revenue-noise vector from the *same* generator immediately after `generate_spend` returns, continuing this plan's documented six-call taxonomy-order sequence as its seventh draw.
- Measured `test_spend_patterns.py` runtime (well under 1s for 26 tests, far under the 30s ceiling) recorded here for the Charter section 5 effort tally, per this plan's own `<output>` instruction.
- No blockers for 02-06.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: src/ambo/simulate/spend_patterns.py
- FOUND: tests/unit/test_spend_patterns.py
- FOUND: docs/MODULE_CONTRACTS.md
- FOUND: c080b25 (Task 1 commit)
- FOUND: 8588ca4 (Task 2 commit)
