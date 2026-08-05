---
phase: 02-ground-truth-simulator
plan: 08
subsystem: simulate
tags: [pydantic, numpy, json, sim-070, sim-075, byte-stable-serialization]

# Dependency graph
requires:
  - phase: 02-06
    provides: "SimulationResult (cfg, weeks, spend, components, media, outcome) and assemble_scenario(cfg, rng) -- the components frame's base/m_<channel> arrays this plan aggregates into per-channel truth"
  - phase: 02-07
    provides: "platform_report(result) -- the platform-completed media frame this plan aggregates into platform_roas"
provides:
  - "TruthFile/ChannelTruth pydantic schema covering every SPEC-01 section 4/6/8 quantity (SIM-075)"
  - "response_curve_at(params, x_grid) -- the closed-form true-response-curve evaluator, generic over any caller-supplied grid, registered in MODULE_CONTRACTS.md for Phase 3/8 to reuse without re-deriving the formula"
  - "marginal_roas_at(params, x_mean) -- Guide section 1.5's analytic marginal-ROAS derivative, truth-side only (BP-D-16)"
  - "compute_truth(result, media) -> TruthFile and write_truth(t, path) -- byte-stable (SIM-070), atomic JSON emission"
affects: [02-09, 02-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Float pre-normalisation through a fixed %.10g format before json.dumps -- json.dump/dumps exposes no per-float format hook (default= never fires for a native float), so pre-normalising the payload's values is the only mechanism, confirmed against Python 3.12's json module"
    - "EB-050 atomic write: <path>.tmp-<pid> then os.replace, with the temp file removed on any exception, matching posterior_io's documented T-305 pattern"
    - "A closed-form curve evaluator taking a caller-supplied grid (not a fixed array) so a diagnostic call (0...2x) and a downstream export call (MD-082's 0...1.5x) share one formula with zero interpolation error"

key-files:
  created:
    - src/ambo/simulate/truth.py
    - tests/unit/test_truth.py
  modified:
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "Assumption A3 (02-RESEARCH.md) resolved: float precision is pinned by recursively pre-normalising every float in the model_dump payload through float(f'{value:.10g}') before json.dumps, not via a custom JSONEncoder subclass -- json's encoder never routes a native float through default(), so a subclass would hit the identical limitation."
  - "SPEC-01 section 8's grid question required no new decision in this phase -- it was already resolved at the spec level (the ROADMAP's INGEST-CONFLICTS WARNING 4 text is stale, per 02-RESEARCH.md Pitfall 1). The only implementation consequence is that response_curve_at takes a caller-supplied grid rather than being hard-coded to the 0...2x diagnostic array."
  - "marginal_roas_at's a==0 branch returns 0.0 for s >= 1.0 and raises SimulationError for s < 1.0 (unbounded derivative at the origin), per the plan's explicit instruction -- this branch is defensive only: compute_truth always raises before reaching a zero-mean-spend channel, since a channel with zero total spend is itself rejected first."
  - "Tasks 1 and 2 landed in a single commit (e3e6ffc) -- truth.py was authored as one coherent module in a single pass (the schema and the functions that populate it are inseparable to write correctly in isolation), so there was no meaningful intermediate diff to split into two commits. Task 3's tests are their own commit (af085e1)."

requirements-completed: []  # REQ-q1-truth-recovery is Phase-5-owned per REQUIREMENTS.md traceability table -- same decision as every prior 02-0x plan.

coverage:
  - id: D1
    description: "TruthFile/ChannelTruth schema covers every SPEC-01 section 4/6/8 quantity (SIM-075), schema-validated (extra='forbid', frozen) for all three scenarios"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_truth.py#test_truth_file_validates_and_is_complete"
        status: pass
      - kind: unit
        ref: "tests/unit/test_truth.py#test_truth_file_rejects_unknown_key_and_is_frozen"
        status: pass
    human_judgment: false
  - id: D2
    description: "response_curve_at(params, x_grid) is a pure function of a caller-supplied grid, agrees with an independent recomputation on MD-082's future 1.5x horizon, and is registered in docs/MODULE_CONTRACTS.md"
    verification:
      - kind: unit
        ref: "tests/unit/test_truth.py#test_response_curve_at_accepts_a_caller_supplied_grid"
        status: pass
      - kind: unit
        ref: "tests/unit/test_repo_layout.py#test_module_contracts_match_src_ambo_modules_exactly"
        status: pass
    human_judgment: false
  - id: D3
    description: "marginal_roas_at agrees with a central finite difference of response_curve_at to 1e-6 relative tolerance for every beta > 0 channel across all three scenarios"
    verification:
      - kind: unit
        ref: "tests/unit/test_truth.py#test_marginal_roas_matches_finite_difference"
        status: pass
    human_judgment: false
  - id: D4
    description: "S-C's display_video truth (avg ROAS, total contribution, share, 21-point curve) is an exact zero, never a small nonzero number and never NaN"
    verification:
      - kind: unit
        ref: "tests/unit/test_truth.py#test_s_c_zero_effect_channel_truth_is_exactly_zero"
        status: pass
      - kind: unit
        ref: "tests/unit/test_truth.py#test_response_curve_is_monotone_non_decreasing"
        status: pass
    human_judgment: false
  - id: D5
    description: "A channel with zero total spend over the window raises SimulationError naming the channel, rather than emitting a 0/0 NaN into a committed truth file"
    verification:
      - kind: unit
        ref: "tests/unit/test_truth.py#test_zero_total_spend_channel_raises"
        status: pass
    human_judgment: false
  - id: D6
    description: "write_truth is byte-identical across two writes (sorted keys, 2-space indent, %.10g float precision, LF-only, single trailing newline) and atomic (no temp-file debris survives)"
    verification:
      - kind: unit
        ref: "tests/unit/test_truth.py#test_write_truth_is_byte_stable"
        status: pass
      - kind: unit
        ref: "tests/unit/test_truth.py#test_written_json_keys_are_sorted"
        status: pass
      - kind: unit
        ref: "tests/unit/test_truth.py#test_written_floats_have_at_most_ten_significant_digits"
        status: pass
      - kind: unit
        ref: "tests/unit/test_truth.py#test_write_truth_leaves_no_temp_file"
        status: pass
    human_judgment: false
  - id: D7
    description: "Platform ROAS is present for the four online channels and null (never a fabricated zero) for print_regional and radio, matching media_weekly.csv's NULL discipline"
    verification:
      - kind: unit
        ref: "tests/unit/test_truth.py#test_offline_channels_have_null_platform_fields"
        status: pass
    human_judgment: false
  - id: D8
    description: "The steady-state-adstock closed-form curve expression has a single home (truth.py) -- not re-derived anywhere else in src/ambo/ (A-8)"
    verification:
      - kind: unit
        ref: "tests/unit/test_truth.py#test_curve_formula_has_a_single_home"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min
completed: 2026-08-05
status: complete
---

# Phase 2 Plan 8: Truth-File Schema, Curve Evaluator and Byte-Stable Emission Summary

**`truth.py`'s `TruthFile`/`ChannelTruth` pydantic schema covers every SPEC-01 section 4/6/8 quantity (SIM-075); `response_curve_at`/`marginal_roas_at` expose the closed-form curve as reusable pure functions of a caller-supplied grid (registered in `docs/MODULE_CONTRACTS.md` for Phase 3/8), and `write_truth` emits byte-stable, atomically-replaced JSON (SIM-070) via pre-normalised `%.10g` floats.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-08-05
- **Tasks:** 3 completed
- **Files modified:** 3 (`src/ambo/simulate/truth.py` new, `tests/unit/test_truth.py` new, `docs/MODULE_CONTRACTS.md` extended)

## Accomplishments

- `response_curve_at(params: TrueParams, x_grid: np.ndarray) -> np.ndarray` -- the true response curve at steady-state adstock (`a = x/(1-lam)`, contribution `beta * hill(a, K, s)`), reusing `dgp.hill` so the truth curve and the per-week generated contributions can never diverge. Generic over any caller-supplied grid (SPEC-01 section 8's grid note, resolving INGEST-CONFLICTS WARNING 4): this phase calls it once with the 21-point 0...2x diagnostic grid; Phase 3/8's `exports/response_curves.csv` will call it again with MD-082's 21-point 0...1.5x observed grid, with zero interpolation error and no second home for the formula.
- `marginal_roas_at(params: TrueParams, x_mean: float) -> float` -- Guide section 1.5's analytic derivative `beta*s*K^s*a^(s-1)/(a^s+K^s)^2 * 1/(1-lam)`, truth-side only (BP-D-16, never the model's normalized steady state). Returns exactly `0.0` when `beta == 0.0`; defensively branches at `a == 0.0` (`0.0` for `s >= 1.0`, `SimulationError` for `s < 1.0`, where the derivative is unbounded).
- `class ChannelTruth`/`class TruthFile` (pydantic, `extra='forbid'`, frozen) -- every SPEC-01 section 4 parameter (`lam`, `K`, `s`, `beta`), section 6 parameter (`platform_phi`/`theta`/`cpm`/`roas`, `None` for offline channels), and section 8 derived quantity (`half_life_weeks`, spend/contribution aggregates, `true_avg_roas`, `true_marginal_roas_at_mean_spend`, the 21-point response-curve arrays), plus scenario metadata and the section 2.1/2.3 window scalars.
- `compute_truth(result: SimulationResult, media: pd.DataFrame) -> TruthFile` -- pure aggregation over `SPEC_CHANNEL_ORDER`. Raises `SimulationError` naming any channel whose total spend over the window is `0.0`, before a `0/0` ROAS can reach the artifact. `contribution_share` values sum to `media_share_of_revenue` exactly (both divide by the same `total_revenue_eur`).
- `write_truth(t: TruthFile, path: Path) -> None` -- `sort_keys=True`, 2-space indent, every float pre-normalised through `%.10g`, one trailing newline, LF pinned in the writer (`newline="\n"`, not `.gitattributes`). Atomic: `<path>.tmp-<pid>` then `os.replace`, with the temp file removed on any exception.
- The contract-first `docs/MODULE_CONTRACTS.md` entry for `truth.py` landed in the same commit as the code (D-23), registering all six exported symbols -- `response_curve_at` explicitly, per 02-RESEARCH.md's recommendation -- so Phase 3/8 finds the curve evaluator by contract rather than by reading `truth.json`'s diagnostic array.
- 32 tests in `tests/unit/test_truth.py` (4.1s, well under the 45s ceiling), parameterized across all three scenarios where applicable: SIM-075 schema completeness and parameter equality against `load_scenario`, frozen/`extra='forbid'` rejection, `true_avg_roas` re-derivation, contribution-share summation, marginal-ROAS-vs-finite-difference agreement (1e-6 relative tolerance), response-curve monotonicity and the S-C zero-effect exact-zero spot check, the caller-supplied-grid property against an independent MD-082-style 1.5x recomputation, offline-null platform fields, the zero-total-spend `SimulationError`, `write_truth`'s byte-stability/sorted-keys/`%.10g`-precision/no-temp-file guarantees, and a single-home grep guard (comments and docstrings stripped) for the curve formula.

## Task Commits

Each task was committed atomically:

1. **Task 1+2: TruthFile schema, curve evaluator, analytic marginal ROAS, compute_truth and byte-stable write_truth** - `e3e6ffc` (feat)
2. **Task 3: SIM-075 schema, byte-stability and truth-derivation tests** - `af085e1` (test)

**Plan metadata:** committed as part of this summary's own commit.

## Files Modified

- `src/ambo/simulate/truth.py` -- new module: `response_curve_at`, `marginal_roas_at`, `ChannelTruth`, `TruthFile`, `compute_truth`, `_normalize_floats`, `write_truth`.
- `tests/unit/test_truth.py` -- new: 32 tests covering SIM-075, SIM-070, the S-C zero-effect spot check, the caller-supplied-grid property, and the single-home guard.
- `docs/MODULE_CONTRACTS.md` -- new `### src/ambo/simulate/truth.py` entry (Purpose, Public API, Invariants, Failure modes, Testing), inserted alphabetically after `spend_patterns.py`.

## Decisions Made

- **Assumption A3 resolved** (02-RESEARCH.md Pattern 3): float precision is pinned by recursively pre-normalising every `float` in the `model_dump(mode="json")` payload through `float(f"{value:.10g}")` before `json.dumps`, not via a custom `JSONEncoder` subclass -- confirmed against Python 3.12's `json` module that `default=` never fires for a native `float` (it only fires for objects the encoder cannot natively serialise), so a subclass hits the identical "floats never reach a hookable method" limitation. Pre-normalisation is therefore the only mechanism.
- **SPEC-01 section 8's grid question required no new decision in this phase.** It was already resolved at the spec level before this plan started (02-RESEARCH.md Pitfall 1 confirms the ROADMAP's INGEST-CONFLICTS WARNING 4 text is stale). The only implementation consequence for `truth.py` is that `response_curve_at` is generic over a caller-supplied grid rather than hard-coded to the 0...2x diagnostic array -- proven by `test_response_curve_at_accepts_a_caller_supplied_grid`, which calls the function with an independent MD-082-style 0...1.5x grid and verifies agreement with a direct closed-form recomputation.
- `marginal_roas_at`'s `a == 0.0` branch returns `0.0` for `s >= 1.0` and raises `SimulationError` for `s < 1.0`, per the plan's explicit instruction. This branch is defensive only and is never exercised by real scenario data: `compute_truth` always raises `SimulationError` for a channel with zero total spend before reaching a zero-mean-spend call into `marginal_roas_at`.
- Tasks 1 and 2 landed in a single commit (`e3e6ffc`) rather than two -- `truth.py`'s schema and the functions that populate it (`compute_truth`, `write_truth`) were authored as one coherent module in a single pass, since writing the schema correctly required already knowing what `compute_truth` would populate it with. There was no meaningful intermediate diff to split. Task 3's tests remain their own commit (`af085e1`).

## Deviations from Plan

None beyond the commit-granularity note above (not a Rule 1-4 deviation -- no code behavior differs from the plan; only the task-to-commit mapping does). Every acceptance criterion (mypy strict, repo-layout, all four smoke-test one-liners from Tasks 1 and 2, `grep -c response_curve_at`, `make test`) passed on first implementation.

## Issues Encountered

`make lint` (`ruff format --check .` over the whole repo) still fails on the pre-existing, already-deferred `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`/`02-RESEARCH.md` markdown formatting issue first logged by 02-01 and re-confirmed by every plan since (02-04 through 02-07) -- re-confirmed here as still out of scope (neither file is in this plan's `files_modified`, neither was touched by any task). `uv run ruff check .` (lint proper), `uv run ruff format --check` scoped to this plan's own three files, and `uv run mypy` (strict, whole `src/ambo`) all pass cleanly. `make test` passes fully (267 passed, up from 235 before this plan).

## Next Phase Readiness

- `truth.json` is now fully computable for all three scenarios via `compute_truth(assemble_scenario(cfg, rng), platform_report(result))` followed by `write_truth`.
- Plan 02-09 (`__main__.py` CLI/`make simulate`/`make validate-sim`) can now wire `truth.py` into the end-to-end simulator entry point and its SIM-075 gate.
- Plan 02-10 (committed `data/synthetic/{s_a,s_b,s_c}/truth.json`) has everything it needs from this plan.
- No blockers for 02-09.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: src/ambo/simulate/truth.py
- FOUND: tests/unit/test_truth.py
- FOUND: docs/MODULE_CONTRACTS.md
- FOUND: e3e6ffc (Task 1+2 commit)
- FOUND: af085e1 (Task 3 commit)
