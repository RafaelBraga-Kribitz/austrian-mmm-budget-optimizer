---
phase: 02-ground-truth-simulator
plan: 04
subsystem: simulate
tags: [pandas, numpy, hypothesis, adstock, hill-saturation, seasonality, dgp]

# Dependency graph
requires:
  - phase: 02-01
    provides: hypothesis dev dependency (ADR-007), .hypothesis/ gitignored
  - phase: 02-02
    provides: SimulationError, ScenarioConfig/SeasonWeights schema
  - phase: 02-03
    provides: config/scenarios/{s_a,s_b,s_c}.yaml with promo_weeks/burst schedules
provides:
  - "week_index(cfg) -- gapless ISO-Monday weekly spine read from dbt/seeds/season_windows.csv"
  - "season_index(weeks, season_weights) -- SPEC-01 section 2.1's five signed weights, summed"
  - "baseline_demand(cfg, weeks) -- trend/season/promo_mult/promo_flag/base components"
  - "round_half_up(values) -- the project-wide whole-unit rounding convention (A-8)"
  - "adstock_recursive(x, lam) -- the simulator's own causal geometric adstock"
  - "hill(a, K, s) -- the simulator's own Hill saturation"
affects: [02-05, 02-06, 02-07, 02-08, 02-09, 02-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Functional-core pure math in dgp.py, no I/O (mirrors generate_season_windows.py's build_rows()/main() split)"
    - "hypothesis property tests: allow_nan=False/allow_infinity=False plus explicit min/max bounds, never assume() filtering"
    - "SimulationError naming the offending value/key at every raise site, never a bare ValueError escaping the module boundary"

key-files:
  created:
    - src/ambo/simulate/dgp.py
    - tests/unit/test_dgp.py
  modified:
    - docs/MODULE_CONTRACTS.md
    - pyproject.toml

key-decisions:
  - "season_index(weeks, season_weights) promotes 03_MODULES.md section 2.3's season_index(weeks: pd.DatetimeIndex, windows: pd.DataFrame) to a (week-index frame, SeasonWeights) signature -- the five weights are SIM-002 YAML values and must not be hard-coded in code"
  - "SimulationError replaces 03_MODULES.md's implicit ValueError on every domain violation in this module (week-spine invariants, adstock/hill domain guards), consistent with 02-02's same promotion"
  - "_expected_keys() (missing-calendar-row diagnostic) uses date.fromisocalendar()/isocalendar() to reconstruct the declared spine independently of the (possibly short) seed file -- this is plain ISO-calendar arithmetic, not a reimplementation of the five AD-020 window-classification rules, and it is the only way to name a key that is by definition absent from the file being diagnosed"
  - "Added a pyproject.toml mypy override for pandas.* (ignore_missing_imports), same precedent as the existing yaml.* override -- pandas is a pinned SPEC-08 section 3 runtime dependency, not a new one, so this avoids an EB-030 ADR event for the separate pandas-stubs package"

patterns-established:
  - "dgp.py is the first ambo.simulate module carrying real transform code -- test_import_independence.py's SIM-003 firewall is now non-vacuous and green"

requirements-completed: []  # Both REQ-q1-truth-recovery and REQ-grain-and-windows remain Phase-5/6-owned per REQUIREMENTS.md traceability (see 02-02-SUMMARY.md's identical decision) -- not marked complete here.

coverage:
  - id: D1
    description: "Gapless, ISO-Monday-aligned weekly spine (week_index) sourced from the committed season_windows.csv seed for all three scenarios, raising SimulationError naming a missing or duplicated calendar key"
    requirement: "REQ-grain-and-windows"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_week_index_row_count_matches_scenario_weeks"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_week_index_is_a_gapless_iso_monday_spine"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_week_index_raises_on_missing_calendar_row"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_week_index_raises_on_duplicate_calendar_row"
        status: pass
    human_judgment: false
  - id: D2
    description: "Seasonal index reproducing SPEC-01 section 2.1's five signed weights exactly, 1.0 on an unflagged week, no sign flip on jan_dip/summer_lull"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_season_index_all_flags_zero_returns_exactly_one"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_season_index_single_flag_matches_spec01_weight"
        status: pass
    human_judgment: false
  - id: D3
    description: "Baseline demand (trend/season/promo_mult/promo_flag/base) matching SPEC-01's base_t formula elementwise"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_baseline_demand_base_matches_spec01_formula"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_baseline_demand_promo_week_carries_the_promo_multiplier"
        status: pass
    human_judgment: false
  - id: D4
    description: "The simulator's own causal geometric adstock, proven by an impulse test written and run before the closed-form limit test (trap T-2 guard), plus domain validation"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_adstock_impulse_response_is_causal"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_adstock_closed_form_limit"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_adstock_raises_on_lam_equal_to_one"
        status: pass
    human_judgment: false
  - id: D5
    description: "The simulator's own exact Hill saturation (0.5 at a=K across the SPEC-01 section 4 table, 0.0 at a=0) plus domain validation"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_hill_at_k_is_exactly_half_across_spec01_table"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_hill_at_zero_spend_is_exactly_zero"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-03's five bounded hypothesis property invariants for adstock/Hill, including the causality generative twin of the impulse test, measured under 60s"
    verification:
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_adstock_is_causal_under_a_future_perturbation"
        status: pass
      - kind: unit
        ref: "tests/unit/test_dgp.py#test_hill_is_monotone_non_decreasing_in_adstocked_spend"
        status: pass
    human_judgment: false

# Metrics
duration: ~25min
completed: 2026-08-05
status: complete
---

# Phase 2 Plan 4: DGP Core -- Calendar Spine, Seasonality, Baseline Demand, Adstock/Hill Summary

**`src/ambo/simulate/dgp.py` first half: `week_index`/`season_index`/`baseline_demand`/`round_half_up`, plus the simulator's own causal `adstock_recursive` and exact `hill`, all independently tested with an impulse-before-closed-form ordering and five bounded `hypothesis` property invariants.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-08-05
- **Tasks:** 3 completed
- **Files modified:** 4 (`src/ambo/simulate/dgp.py` created, `tests/unit/test_dgp.py` created, `docs/MODULE_CONTRACTS.md` modified, `pyproject.toml` modified)

## Accomplishments

- The weekly spine (`week_index`) reads `dbt/seeds/season_windows.csv` for all three scenarios (156/104/78 weeks), is gapless, ISO-Monday-aligned, and raises `SimulationError` naming the offending key on a missing or duplicated calendar row -- never silently defaulting a week.
- `season_index` reproduces SPEC-01 section 2.1's five signed weights (`+0.55, +0.25, +0.15, -0.20, -0.10`) with no sign flip in code, and `baseline_demand` reproduces the full `base_t = b0 * (1+g)^t * season_t * promo_mult_t` formula with every component exposed as its own column (for plan 02-06's SIM-071 re-sum).
- The simulator's own `adstock_recursive` and `hill` are independently implemented (a plain forward loop, never `cumsum`/`convolve`/`lfilter`), proven by an impulse test written and run *before* the closed-form limit test per this project's own trap-T-2 discipline (02-RESEARCH.md Pitfall 4), and both are domain-guarded with typed `SimulationError`s rather than silent NaNs.
- D-03's five bounded `hypothesis` property tests land, including a causality property that is the generative twin of the impulse test -- the SIM-003 import-independence firewall (`test_import_independence.py`) is now non-vacuous and green, since `dgp.py` is the first `ambo.simulate` module carrying real transform code.

## Task Commits

Each task was committed atomically:

1. **Task 1: Week spine, seasonal index, baseline demand, and the rounding convention** - `3aa18c9` (feat)
2. **Task 2: Simulator-side adstock and Hill -- impulse test first, then closed form** - `9817b3a` (feat)
3. **Task 3: Property-based invariants for adstock and Hill (D-03)** - `5780c3f` (test)

**Plan metadata:** committed as part of this summary's own commit.

## Files Created/Modified

- `src/ambo/simulate/dgp.py` - `SEED_PATH`, `round_half_up`, `week_index`, `season_index`, `baseline_demand`, `adstock_recursive`, `hill`
- `tests/unit/test_dgp.py` - SIM-073 seasonality point tests, SIM-074 adstock/Hill point tests, D-03 property tests (51 tests total, ~5s runtime)
- `docs/MODULE_CONTRACTS.md` - contract-first `### src/ambo/simulate/dgp.py` entry (D-23), landed in the Task 1 commit covering the full public API including Task 2's `adstock_recursive`/`hill` (both functions' signatures were already fixed by SPEC-01 section 2.2 at plan-authoring time, so documenting them one task early does not misstate anything Task 2 later changed)
- `pyproject.toml` - `[[tool.mypy.overrides]]` for `pandas.*` (`ignore_missing_imports`), same precedent as the existing `yaml.*` override

## Decisions Made

- `season_index(weeks, season_weights)` promotes `03_MODULES.md` section 2.3's `season_index(weeks: pd.DatetimeIndex, windows: pd.DataFrame)` to a `(week-index frame, SeasonWeights)` signature -- recorded here for `docs/BUILD_LOG.md` per the plan's own instruction.
- `SimulationError` (not `ValueError`) is the raise type at every domain-violation site in this module, consistent with 02-02's identical promotion over `03_MODULES.md`.
- `_expected_keys()` (used only to name a missing calendar key in a `SimulationError` message) reconstructs the declared spine via `date.fromisocalendar()`/`isocalendar()` rather than re-reading the same seed file being diagnosed -- a genuinely missing row cannot be named by re-reading the file it's missing from. This is plain ISO-calendar arithmetic, not a reimplementation of the five AD-020 window-classification rules (advent/schulbeginn/jan_dip/spring/summer_lull), which this module still never touches.
- Added a `pandas.*` mypy override, mirroring the existing `yaml.*` override precedent from Phase 1 -- `pandas` is a pinned runtime dependency already, so this is a stub-completeness fix, not a new-dependency/ADR event.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] mypy `pandas` stub gap and `no-any-return` on `season_index`**
- **Found during:** Task 1 verification (`uv run mypy`)
- **Issue:** `mypy --strict` reported "Library stubs not installed for pandas" on the `import pandas as pd` line, and a `no-any-return` error on `season_index`'s return expression (pandas' `.to_numpy()` returns `Any` under strict mode without stubs).
- **Fix:** Added a `pandas.*` `ignore_missing_imports` override to `pyproject.toml` (same precedent as the existing `yaml.*` override) and wrapped `season_index`'s return value in `np.asarray(result, dtype=np.float64)` to pin the return type explicitly.
- **Files modified:** `pyproject.toml`, `src/ambo/simulate/dgp.py`
- **Verification:** `uv run mypy` exits 0 with "Success: no issues found in 13 source files".
- **Committed in:** `3aa18c9` (Task 1 commit)

**2. [Rule 3 - Blocking] `_expected_keys()` initial design re-read the corrupted seed file**
- **Found during:** Task 1 authoring, before tests were run — self-caught while writing the missing-calendar-row test.
- **Issue:** The first draft of `_expected_keys()` re-read `SEED_PATH` (the same, possibly-short seed) to compute "expected" keys, which cannot name a key genuinely absent from that same file.
- **Fix:** Rewrote `_expected_keys()` to reconstruct the declared spine from `cfg.start_iso_year`/`cfg.start_iso_week`/`cfg.weeks` via `date.fromisocalendar()`/`isocalendar()`, independent of the (possibly corrupted) seed file.
- **Files modified:** `src/ambo/simulate/dgp.py`
- **Verification:** `test_week_index_raises_on_missing_calendar_row` passes, correctly naming the deliberately-removed key.
- **Committed in:** `3aa18c9` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking correctness issues caught during implementation/verification).
**Impact on plan:** Both fixes were necessary for the module to satisfy its own acceptance criteria (`mypy` exit 0; a missing calendar row correctly named). No scope creep -- neither touched any file outside this plan's `files_modified` list.

## Issues Encountered

- `make lint`'s `ruff format --check .` fails on two pre-existing markdown files (`.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`, `02-RESEARCH.md`) containing embedded Python code fences ruff's formatter wants to reformat. Confirmed via `git stash` that this predates this plan's execution (already logged as a deferred item by 02-01). `ruff check .` and `uv run mypy` both pass cleanly across the whole repository including this plan's own files; `uv run ruff format --check` passes in isolation on `src/ambo/simulate/dgp.py` and `tests/unit/test_dgp.py`. Re-logged (not re-fixed) in `.planning/phases/02-ground-truth-simulator/deferred-items.md`.

## Next Phase Readiness

- `week_index`, `season_index`, `baseline_demand`, `round_half_up`, `adstock_recursive` and `hill` are all available for plan 02-05 (`spend_patterns.py`, which imports `round_half_up`) and plan 02-06 (`assemble_scenario`/`SimulationResult`/SIM-071/072 audits, the second half of this same file).
- Measured `test_dgp.py` runtime (~5s for 51 tests, well under the 60s ceiling and the 30s feedback-latency target) recorded here for the Charter section 5 effort tally, per this plan's own `<output>` instruction.
- No blockers for 02-05/02-06.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: src/ambo/simulate/dgp.py
- FOUND: tests/unit/test_dgp.py
- FOUND: docs/MODULE_CONTRACTS.md
- FOUND: 3aa18c9 (Task 1 commit)
- FOUND: 9817b3a (Task 2 commit)
- FOUND: 5780c3f (Task 3 commit)
