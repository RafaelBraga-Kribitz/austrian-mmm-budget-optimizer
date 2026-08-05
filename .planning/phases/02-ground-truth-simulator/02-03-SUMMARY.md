---
phase: 02-ground-truth-simulator
plan: 03
subsystem: simulate
tags: [scenario-yaml, spec-01, bp-g-02, authoring-aid, spend-patterns]

# Dependency graph
requires:
  - phase: 02-ground-truth-simulator (plan 02)
    provides: "ScenarioConfig model tree (extra='forbid'), load_scenario(), SimulationError -- the schema every value in this plan's YAMLs is validated against"
provides:
  - "config/scenarios/{s_a,s_b,s_c}.yaml -- the authoritative SPEC-01 section 2.1/3/4/5/6 parameter source for all three scenarios (SIM-002)"
  - "scripts/author_scenario_schedules.py -- the dev-only, deterministic promo/burst placement authoring aid (D-02): read_windows, prorate, black_friday_week, anchored_promo_weeks, anchored_burst_starts, spread_placements, main(--scenario)"
  - "tests/unit/test_scenario_config.py extended with 10 BP-G-02 tests: YAML==SPEC-01 table equality, per-covered-year counting rules, S-C/S-B rule-level diff, collinearity-switch-in-data, authoring-aid-unreachable-from-src"
affects: [02-04-spend-patterns, 02-05-dgp, 02-06-dgp-gates, 02-08-truth, 02-09-cli-gates]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dev-only authoring aid lives under scripts/, writes no files, prints a YAML fragment to stdout; its output is hand-copied into config/scenarios/*.yaml and frozen -- never executed at simulate time (A-13, D-02)"
    - "BP-G-02 spec-table-equality tests hard-code the SPEC-01 section 4/6 tables and the section 2.1 scalars as module-level test constants, loading the scenario YAML directly via yaml.safe_load (never through load_scenario()) so the test trusts nothing about the loader's own transformation"
    - "Round-half-up pro-rating (BP-D-09): math.floor(full_count * covered_weeks / weeks_in_year + 0.5), re-derived independently in both the authoring aid and the test file rather than imported from one into the other"

key-files:
  created:
    - scripts/author_scenario_schedules.py
    - config/scenarios/s_a.yaml
    - config/scenarios/s_b.yaml
    - config/scenarios/s_c.yaml
  modified:
    - tests/unit/test_scenario_config.py

key-decisions:
  - "Spring promo-week anchors are the spring window's own 1/3 and 2/3 index points (not literal week-number constants), so the anchor choice adapts if the spring window's length ever changes -- CONTEXT.md D-01 fully delegates this choice"
  - "Radio's 2 Advent-anchored bursts are authored as a lead-in burst (A-3, ending the week before Advent starts) plus an in-Advent burst (A) -- two 3-week bursts cannot both fit inside the 4-week Advent window without overlapping; recorded for docs/BUILD_LOG.md at M1 close"
  - "meta.spend.advent_factor: SPEC-01 section 3's meta row states no seasonal multiplier by itself, but SIM-030 presupposes a 0.5 baseline for meta in S-A ('0.5->0.9 for search_generic/meta') -- read as 0.5 (S-A) / 0.9 (S-B/S-C), same switch as search_generic; recorded for docs/BUILD_LOG.md at M1 close"
  - "The four online-channel cpm values (search_brand 12.0, search_generic 20.0, meta 6.0, display_video 4.0) are authored, not spec-given (BP-D-02 names no values); impressions are descriptive-only and never modeled; recorded for docs/BUILD_LOG.md at M1 close"
  - "test_promo_week_counting_rules asserts >= 2 (not == 2) promo weeks fall inside a fully-covered spring window, after separately asserting the 2 specific spring-anchor weeks are present -- an unconstrained spread pick can coincidentally also land inside the spring range (observed: s_b 2022 has 3), which is correct authoring-aid behavior, not a bug"

patterns-established:
  - "Pattern: promo/burst schedule provenance is regenerate-and-re-paste, never hand-edit -- both scenario YAML comments and this SUMMARY state that a wrong-looking week number is fixed in scripts/author_scenario_schedules.py and re-run, not edited in place"

requirements-completed: [REQ-q1-truth-recovery, REQ-grain-and-windows]

# Metrics
duration: 55min
completed: 2026-08-05
status: complete
---

# Phase 02 Plan 03: Scenario YAML Authoring Summary

**The three SPEC-01 scenario YAMLs (config/scenarios/{s_a,s_b,s_c}.yaml) authored as the single authoritative ground-truth parameter source, with a deterministic dev-only placement aid for the unanchored promo/burst weeks and a BP-G-02 test suite that forces the YAML and SPEC-01's own tables to agree.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-08-05T09:52:00Z
- **Completed:** 2026-08-05T10:02:33Z
- **Tasks:** 3 completed
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- `scripts/author_scenario_schedules.py`: `read_windows`, `prorate`, `black_friday_week`, `anchored_promo_weeks`, `anchored_burst_starts`, `spread_placements`, `main(--scenario {s_a,s_b,s_c,all})` -- reads `dbt/seeds/season_windows.csv`, writes no files, prints a byte-identical-across-runs YAML fragment; not reachable from `src/ambo/` (verified by `grep` and by `test_authoring_aid_is_not_reachable_from_src`).
- `config/scenarios/{s_a,s_b,s_c}.yaml`: every SPEC-01 section 2.1/3/4/5/6 value authored literally (156/104/78 weeks, seeds 101/202/303, S-C's `display_video.beta=0.0`, S-A/B/C `advent_factor` 0.5/0.9/0.9), plus the two authored value sets (four `cpm` constants, `meta.advent_factor` interpretation) and the frozen promo/burst schedules from the authoring aid's own stdout.
- All three scenarios load cleanly through `load_scenario()`; `tests/unit/test_line_endings.py` confirms LF endings on the new YAMLs.
- `tests/unit/test_scenario_config.py` extended with 10 new tests (26 -> 36 collected): SPEC-01 table equality (parameters, season weights, scalar constants, platform bias), the SPEC-01 section 5 grain cross-checked against `dbt/seeds/season_windows.csv` row counts, per-covered-year promo/burst counting rules (including S-C's pro-rated 2023 half-year), the S-C/S-B rule-level diff (not a literal YAML diff, per 02-RESEARCH.md Pitfall 7), the collinearity-switch-is-data assertion, and the authoring-aid-unreachable-from-`src/` guard.
- BP-G-02's spec-equality test proven to bite: a deliberate `s_a.yaml` `search_generic.K` edit (`3000.0` -> `3001.0`) made `pytest -k spec_parameter_table` fail with `AssertionError: s_a.search_generic.K: expected 3000.0, got 3001.0`; reverted, and the same command passed green with a clean `git diff`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Deterministic promo/burst placement authoring aid** - `9c268f1` (feat)
2. **Task 2: Author the three scenario YAMLs** - `320e8e2` (feat)
3. **Task 3: BP-G-02 spec-table equality, counting rules, and the rule-level S-C↔S-B diff** - `b15b51e` (test)

**Plan metadata:** (this commit, following)

## Files Created/Modified

- `scripts/author_scenario_schedules.py` - dev-only, one-off authoring aid (D-02); prints deterministic promo/burst placements per scenario
- `config/scenarios/s_a.yaml` - S-A: 156 weeks, seed 101, collinearity OFF
- `config/scenarios/s_b.yaml` - S-B: 104 weeks, seed 202, collinearity ON
- `config/scenarios/s_c.yaml` - S-C: 78 weeks, seed 303, collinearity ON, `display_video.beta=0.0`
- `tests/unit/test_scenario_config.py` - 10 new BP-G-02 tests appended (structural tests from 02-02 untouched)

## Decisions Made

- Spring promo-week anchors computed as the spring window's 1/3 and 2/3 index points (weeks 17 and 20 for the 9-week W14-22 window used in 2021/2022/2023), not hard-coded week numbers -- CONTEXT.md D-01 fully delegates the exact choice.
- Radio's 2 Advent-anchored bursts authored as a lead-in burst (`A-3`) plus an in-Advent burst (`A`), since two 3-week bursts cannot both fit inside the 4-week Advent window without overlapping. Recorded for `docs/BUILD_LOG.md` at M1 close.
- `meta.spend.advent_factor` read as 0.5 (S-A) / 0.9 (S-B/S-C), mirroring `search_generic`'s switch, resolving SIM-030's "0.5->0.9 for search_generic/meta" phrasing against SPEC-01 section 3's meta row (which states no seasonal multiplier by itself). Recorded for `docs/BUILD_LOG.md` at M1 close.
- Four online-channel `cpm` constants authored (not spec-given, per BP-D-02): `search_brand`=12.0, `search_generic`=20.0, `meta`=6.0, `display_video`=4.0; identical across all three scenarios; impressions remain descriptive-only. Recorded for `docs/BUILD_LOG.md` at M1 close.
- `requirements.mark-complete` not invoked, following 02-01/02-02's precedent: both `REQ-q1-truth-recovery` and `REQ-grain-and-windows` are Phase-5/6-owned per `.planning/REQUIREMENTS.md`'s traceability table; this plan is a contributing phase only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_promo_week_counting_rules`'s spring-window assertion changed from exact-count to anchor-presence + minimum-count**
- **Found during:** Task 3 verification (`pytest tests/unit/test_scenario_config.py`)
- **Issue:** The plan's spec ("two promo weeks lie inside the spring window for every covered year whose spring window is covered") was implemented as `len(in_spring) == 2`. This failed on real data: `s_b` 2022's unconstrained spread placement happened to also draw week 15, which falls inside the spring window (14-22) in addition to the 2 intentional spring anchors (17, 20) -- `len(in_spring) == 3`, not a bug in the YAML or the authoring aid (the Guide's spread rule says nothing about avoiding the spring window; only the 2 anchored spring weeks are a hard requirement).
- **Fix:** Re-derived the exact 2 spring-anchor weeks independently (same 1/3 and 2/3 index rule the authoring aid uses) and asserted their *presence* directly, the same pattern already used for the Black-Friday/Advent anchors above. Kept a weaker `>= 2` sanity check for "inside the fully covered spring window" rather than removing the count check entirely.
- **Files modified:** `tests/unit/test_scenario_config.py`
- **Verification:** `uv run pytest tests/unit/test_scenario_config.py -v` -> 36 passed
- **Committed in:** `b15b51e` (Task 3 commit, discovered and fixed before that commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test assertion design, discovered against real authored data -- no change to `scripts/author_scenario_schedules.py` or any scenario YAML)
**Impact on plan:** The fix corrected the test's own precision, not the aid's or the YAMLs' behavior. No scope creep -- the anchor-presence check is strictly more precise than the count check it replaced (it also still enforces "at least 2 in a fully covered spring window").

## Issues Encountered

None beyond the one auto-fixed item above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 02-04 (`spend_patterns.py`) can now read every SIM-030/031 spend-pattern parameter -- including the collinearity switch (`advent_factor`/`spring_factor`), the pulse convention (`pulse_every`/`pulse_multiplier`), and the frozen burst schedules -- through `load_scenario()`, with `tests/unit/test_scenario_config.py`'s BP-G-02 suite guaranteeing those values can never silently drift from SPEC-01. `docs/MODULE_CONTRACTS.md` and all four Phase 1 architectural guards (`test_repo_layout.py`, `test_import_independence.py`, `test_forbidden_deps.py`, `uv run mypy` strict) remain green.

**Items to record in `docs/BUILD_LOG.md` at M1 close** (per this plan's `<output>` instruction):
1. The four authored `cpm` values and their descriptive-only status (search_brand 12.0, search_generic 20.0, meta 6.0, display_video 4.0 -- BP-D-02, no spec value given).
2. The `meta.advent_factor` interpretation (0.5/0.9, mirroring `search_generic`'s SIM-030 switch).
3. The radio Advent-anchoring reading (lead-in burst `A-3` + in-Advent burst `A`, since two 3-week bursts cannot both fit inside the 4-week Advent window).
4. The promo/burst authoring rationale (spring anchors at the window's 1/3 and 2/3 index points; 5/5/3 spread counts for promo/print/radio in a full year; D-02's frozen-at-authoring-time discipline).
5. The BP-G-02 red-then-green evidence: deliberate `s_a.yaml` `search_generic.K` edit `3000.0 -> 3001.0` made `pytest -k spec_parameter_table` fail (`AssertionError: s_a.search_generic.K: expected 3000.0, got 3001.0`); reverted, and the test passed green with a clean `git diff`.

**Known pre-existing, out-of-scope item (unchanged from 02-01/02-02):** `make lint`'s `ruff format --check .` step still fails on two markdown files (`02-PATTERNS.md`, `02-RESEARCH.md`) authored during Phase 2 planning, unrelated to this plan's `files_modified`. Logged in `.planning/phases/02-ground-truth-simulator/deferred-items.md`; `ruff check .` (lint proper), `uv run mypy` (strict) and `make test` (109 passed) all pass cleanly.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: scripts/author_scenario_schedules.py
- FOUND: config/scenarios/s_a.yaml
- FOUND: config/scenarios/s_b.yaml
- FOUND: config/scenarios/s_c.yaml
- FOUND: tests/unit/test_scenario_config.py (modified)
- FOUND commit: 9c268f1
- FOUND commit: 320e8e2
- FOUND commit: b15b51e
