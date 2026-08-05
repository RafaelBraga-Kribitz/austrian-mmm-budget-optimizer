---
phase: 02-ground-truth-simulator
plan: 07
subsystem: simulate
tags: [numpy, pandas, nullable-dtypes, sim-060, sim-061, bp-d-02]

# Dependency graph
requires:
  - phase: 02-06
    provides: "SimulationResult (cfg, weeks, spend, components, media, outcome) and assemble_scenario(cfg, rng) -- the components frame's base/m_<channel> arrays and the media frame's three all-NaN placeholder columns this plan populates"
provides:
  - "platform_report(result) -- completes media_weekly.csv's three platform-reporting columns with SIM-060's known over-credit formula and BP-D-02's impressions/conversions rules"
affects: [02-08, 02-09, 02-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guarded division via np.where(total > 0, spend / np.where(total > 0, total, 1.0), 0.0) -- never evaluates a division by zero, so a zero-total-spend week yields share_c == 0.0 exactly, not NaN"
    - "Nullable pandas extension dtypes (Int64, Float64) for genuinely-absent values -- an offline channel's platform columns carry pd.NA, distinguishable from 0, and write as an empty CSV field"
    - "Left merge on (week_start, channel) with validate='one_to_one' to attach freshly-computed columns to an existing frame while preserving that frame's row order, rather than re-sorting"

key-files:
  created:
    - src/ambo/simulate/platform_bias.py
    - tests/unit/test_platform_bias.py
  modified:
    - docs/MODULE_CONTRACTS.md

key-decisions:
  - "share_{c,t} and platform_revenue_eur are computed from result.spend and result.components directly (not from result.media's own spend_eur column), matching the plan's read_first sources -- result.media's spend_eur is populated from the same underlying spend arrays, so the two are always numerically identical, but result.spend is the more direct source since it is already a wide per-channel frame aligned to weeks's row order."
  - "The zero-total-spend-week test (test_zero_total_spend_week_gives_zero_share_and_no_nan) zeroes only result.spend for one week and reuses result.components unchanged -- SIM-071's decomposition invariant re-sums components alone, so a SimulationResult can be reconstructed with a zeroed spend frame without needing any component adjustment to keep the constructor precondition satisfied."
  - "The config-not-code test (test_phi_theta_come_from_config_not_code) uses pydantic's model_copy(update=...) on the frozen ScenarioConfig/ChannelConfig/PlatformBiasParams chain rather than monkeypatching an attribute directly -- frozen=True blocks attribute assignment, and model_copy(update=...) does not re-run validators, so a patched phi value reaches platform_report exactly as given."

requirements-completed: []  # REQ-q1-truth-recovery is Phase-5/6-owned per REQUIREMENTS.md traceability table -- same decision as every prior 02-0x plan (02-02, 02-04, 02-05, 02-06); not marked complete here.

coverage:
  - id: D1
    description: "platform_report(result) computes platform_revenue_eur = m_c*phi + theta*base_t*share_c for the four online channels, matching a hand-computed identity to within 1e-9 (SIM-060)"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_hand_computed_example_matches_to_1e_9"
        status: pass
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_phi_theta_come_from_config_not_code"
        status: pass
    human_judgment: false
  - id: D2
    description: "print_regional and radio carry NULL (nullable-dtype, never 0) in all three platform columns for every week; online channels are never null or non-finite"
    verification:
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_offline_channels_are_null_everywhere"
        status: pass
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_online_channels_are_never_null_or_non_finite"
        status: pass
    human_judgment: false
  - id: D3
    description: "impressions = round_half_up(spend_eur/cpm*1000) and platform_conversions = round_half_up(platform_revenue_eur/AOV_t) for online channels (BP-D-02)"
    verification:
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_impressions_follow_the_cpm_rule"
        status: pass
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_platform_conversions_follow_the_aov_rule"
        status: pass
    human_judgment: false
  - id: D4
    description: "A zero-total-spend week yields share_c == 0.0 for every channel, never NaN or infinity"
    verification:
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_zero_total_spend_week_gives_zero_share_and_no_nan"
        status: pass
    human_judgment: false
  - id: D5
    description: "SIM-061: the known over-credit ordering (display_video > meta > search_generic > search_brand, matching the phi ordering) is present in the generated data on S-A and S-B"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_over_credit_ordering_matches_phi_ordering"
        status: pass
    human_judgment: false
  - id: D6
    description: "Row order of the returned frame is identical to the input result.media row order (no re-sort)"
    verification:
      - kind: unit
        ref: "tests/unit/test_platform_bias.py#test_row_order_is_preserved"
        status: pass
    human_judgment: false
  - id: D7
    description: "Contract-first docs/MODULE_CONTRACTS.md entry for platform_bias.py landed in the same commit as the code (D-23)"
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

# Phase 2 Plan 7: Simulated Platform Reporting Bias Summary

**`platform_report(result)` completes `media_weekly.csv`'s three still-null columns with SPEC-01 §6's disclosed over-credit formula (`m_c*phi + theta*base_t*share_c`) and BP-D-02's impressions/conversions rules, leaving offline channels genuinely NULL via nullable pandas dtypes.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-05
- **Tasks:** 2 completed
- **Files modified:** 3 (`src/ambo/simulate/platform_bias.py` new, `tests/unit/test_platform_bias.py` new, `docs/MODULE_CONTRACTS.md` extended)

## Accomplishments

- `platform_report(result: SimulationResult) -> pd.DataFrame` — the `03_MODULES.md` §2.4 contract exactly. Validates `result.media`'s row count (`6 * cfg.weeks`) and column set first, raising `SimulationError` (a completion step, never a silent reshape) if either is wrong.
- `share_{c,t}` computed via `np.where(total_spend > 0, spend / np.where(total_spend > 0, total_spend, 1.0), 0.0)` — never evaluates a division by zero, so a zero-total-spend week yields `share_c == 0.0` for every channel, exactly, never `NaN` or infinity.
- For the four online channels (`cfg.channels[c].platform.phi is not None`): `platform_revenue_eur = m_c*phi_c + theta_c*base_t*share_c`, `impressions = round_half_up(spend_eur/cpm_c*1000)`, `platform_conversions = round_half_up(platform_revenue_eur/AOV_t)` where `AOV_t` matches `assemble_scenario`'s own rule. `phi`, `theta`, `cpm` are read from `result.cfg.channels[c].platform` — the module contains no such literal.
- `print_regional` and `radio` carry `pd.NA` (nullable `Int64`/`Float64` dtypes) in all three platform columns for every row — a true missing value, distinguishable from `0`, that writes as an empty CSV field.
- The output is built by left-merging freshly-computed platform columns onto `result.media` (minus its three placeholder columns) on `(week_start, channel)` with `validate="one_to_one"` — this preserves `result.media`'s existing row order rather than re-sorting.
- 20 tests in `tests/unit/test_platform_bias.py` (9.1s), covering: the SIM-060 hand-computed identity, offline-NULL and online-non-null/finite coverage across all three scenarios, the CPM/AOV rules elementwise, the zero-total-spend-week guarantee, a config-not-code monkeypatch proof (via `model_copy(update=...)` on the frozen `ScenarioConfig`/`ChannelConfig`/`PlatformBiasParams` chain, since `frozen=True` blocks direct attribute assignment), SIM-061's over-credit ordering on S-A/S-B, and row-order preservation.
- The contract-first `docs/MODULE_CONTRACTS.md` entry for `platform_bias.py` landed in the same commit as the code (D-23), inserted alphabetically between `dgp.py` and `spend_patterns.py`.

## Hand-computed example (for the Charter §5 record)

Scenario **S-A** (seed 101), channel **`meta`**, week position 10 (`week_start = 2021-03-15`):

| Input | Value |
|---|---|
| `m_meta` (`components["m_meta"]`) | 6236.423359874582 |
| `base_t` (`components["base"]`) | 60663.30991982767 |
| `spend_search_brand` | 648.0 |
| `spend_search_generic` | 2330.0 |
| `spend_meta` | 1795.0 |
| `spend_display_video` | 1592.0 |
| `spend_print_regional` | 0.0 |
| `spend_radio` | 0.0 |
| `total_spend_t` | 6365.0 |
| `share_meta` (`1795.0 / 6365.0`) | 0.2820109976433621 |
| `phi_meta` / `theta_meta` (from `s_a.yaml`, SPEC-01 §6) | 1.5 / 0.01 |

`platform_revenue_eur = 6236.423359874582 * 1.5 + 0.01 * 60663.30991982767 * 0.2820109976433621 = 9525.712245320265`

`platform_report`'s output for that exact row: `9525.712245320265` — matches to floating-point equality (well inside 1e-9).

## Realized SIM-061 over-credit ordering (S-A, S-B)

`platform_roas / true_roas` per online channel, aggregated as `Σ platform_revenue_eur / Σ platform_revenue_eur`... i.e. `(Σ platform_revenue_eur / Σ spend_eur) / (Σ m_c / Σ spend_eur)`:

| Channel | S-A ratio | S-B ratio | φ (design) |
|---|---|---|---|
| `display_video` | 2.0148932323440096 | 2.0142599110192285 | 2.0 |
| `meta` | 1.5270209874780205 | 1.526179622232659 | 1.5 |
| `search_generic` | 1.327289532054731 | 1.326826924519861 | 1.3 |
| `search_brand` | 1.1964441333391898 | 1.1929042097039122 | 1.1 |

Both scenarios order `display_video > meta > search_generic > search_brand`, matching φ = 2.0 > 1.5 > 1.3 > 1.1 exactly, and each realized ratio sits close to its channel's designed φ (the `theta` demand-claiming term adds a small additional lift above φ, as expected). S-C is excluded per SPEC-01 §4's footnote: `display_video.true_params.beta == 0.0` there, making `true_roas` (and therefore the ratio) undefined by construction.

## Task Commits

Each task was committed atomically:

1. **Task 1: platform_report and its module contract** - `4b8e2cc` (feat)
2. **Task 2: SIM-060/061 formula, NULL-handling and over-credit ordering tests** - `a42f8a6` (test)

**Plan metadata:** committed as part of this summary's own commit.

## Files Modified

- `src/ambo/simulate/platform_bias.py` — new module: `platform_report(result)`, `_validate_media_shape`, `_MEDIA_COLUMNS`/`_PLATFORM_COLUMNS` constants.
- `tests/unit/test_platform_bias.py` — new: 20 tests covering SIM-060, SIM-061, BP-D-02, offline-NULL and row-order/config-source guarantees.
- `docs/MODULE_CONTRACTS.md` — new `### src/ambo/simulate/platform_bias.py` entry (Purpose, Public API, Invariants, Failure modes, Testing), inserted between the existing `dgp.py` and `spend_patterns.py` entries.

## Decisions Made

- `share_{c,t}` and `platform_revenue_eur` are computed from `result.spend`/`result.components` directly rather than from `result.media`'s own (placeholder) `spend_eur` column — both sources are numerically identical since `assemble_scenario` populates `media["spend_eur"]` from the same `spend` frame, but `result.spend` is the more direct, already-wide-per-channel source the plan's `read_first` list points to.
- The zero-total-spend-week test zeroes only `result.spend` for one week and leaves `result.components` untouched — SIM-071's decomposition invariant re-sums `components` alone, so no component adjustment is needed to keep the `SimulationResult` constructor precondition satisfied when reconstructing a modified result for the test.
- The config-not-code test uses pydantic `model_copy(update=...)` up the frozen `ScenarioConfig` → `ChannelConfig` → `PlatformBiasParams` chain instead of a direct attribute monkeypatch — `frozen=True` on all three models blocks `__setattr__`, and `model_copy(update=...)` does not re-run validators, so the patched `phi` value reaches `platform_report` exactly as given without disturbing `SPEC_CHANNEL_ORDER` field-order validation.

## Deviations from Plan

None — plan executed exactly as written; every acceptance criterion (mypy strict, repo-layout, both smoke-test one-liners, no φ/θ/CPM literal in the module, `make lint`/`make test`) passed on first implementation.

## Issues Encountered

`make lint` (`ruff format --check .` over the whole repo) still fails on the pre-existing, already-deferred `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`/`02-RESEARCH.md` markdown formatting issue first logged by 02-01 and re-confirmed by every plan since (02-04, 02-05, 02-06) — re-confirmed here as still out of scope (neither file is in this plan's `files_modified`, neither was touched by either task). `uv run ruff check .` (lint proper), `uv run mypy` (strict, whole `src/ambo`), and `uv run ruff format --check` scoped to this plan's own three files all pass cleanly. `make test` passes fully (235 passed, up from 215 before this plan).

## Next Phase Readiness

- `media_weekly.csv`'s three platform columns are now fully computable for all three scenarios; `platform_report` is available for plan 02-09's CLI/export wiring and plan 02-10's committed `data/synthetic/` artifacts.
- Plan 02-08 (`truth.py`'s `compute_truth`) can now aggregate `platform_report`'s output into `truth.json`'s platform-vs-true ROAS diagnostics alongside `SimulationResult.components`.
- No blockers for 02-08.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: src/ambo/simulate/platform_bias.py
- FOUND: tests/unit/test_platform_bias.py
- FOUND: docs/MODULE_CONTRACTS.md
- FOUND: 4b8e2cc (Task 1 commit)
- FOUND: a42f8a6 (Task 2 commit)
