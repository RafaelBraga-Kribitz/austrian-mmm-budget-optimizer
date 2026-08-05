---
phase: 02-ground-truth-simulator
reviewed: 2026-08-05T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - config/scenarios/s_a.yaml
  - config/scenarios/s_b.yaml
  - config/scenarios/s_c.yaml
  - data/synthetic/s_a/media_weekly.csv
  - data/synthetic/s_a/outcome_weekly.csv
  - data/synthetic/s_a/truth.json
  - data/synthetic/s_b/media_weekly.csv
  - data/synthetic/s_b/outcome_weekly.csv
  - data/synthetic/s_b/truth.json
  - data/synthetic/s_c/media_weekly.csv
  - data/synthetic/s_c/outcome_weekly.csv
  - data/synthetic/s_c/truth.json
  - docs/ADR/ADR-007_hypothesis-dev-dependency.md
  - docs/ADR/README.md
  - docs/BUILD_LOG.md
  - docs/MODULE_CONTRACTS.md
  - scripts/author_scenario_schedules.py
  - src/ambo/common/errors.py
  - src/ambo/simulate/__main__.py
  - src/ambo/simulate/config.py
  - src/ambo/simulate/dgp.py
  - src/ambo/simulate/platform_bias.py
  - src/ambo/simulate/spend_patterns.py
  - src/ambo/simulate/truth.py
  - tests/unit/test_dgp.py
  - tests/unit/test_platform_bias.py
  - tests/unit/test_scenario_config.py
  - tests/unit/test_simulate_cli.py
  - tests/unit/test_spend_patterns.py
  - tests/unit/test_truth.py
findings:
  critical: 0
  warning: 5
  info: 1
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-08-05
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

This phase implements the ground-truth simulator (`src/ambo/simulate/`): scenario config
schema, the disclosed data-generating process, spend-pattern generation, platform-bias
over-credit injection, the `truth.json` closed-form curve emitter, and the CLI/gate runner,
plus the three committed scenario YAMLs and their generated artifacts. The module-level
discipline is unusually strong: every documented invariant (SIM-001, SIM-070...075, A-5,
A-8, A-14, A-15) is backed by a targeted point test, a property-based test, or a grep-based
single-home guard, and the code I traced matches its own docstrings almost everywhere.

No critical/blocking defects were found — no injection, no secrets, no crashes reachable
from the currently-shipped scenario YAMLs or CLI surface. The issues below are all
**validation-gap** and **edge-case-correctness** findings: places where this codebase's own
very high documented bar (every domain assumption stated and, in the sibling `TrueParams`/
`SpendPattern` models, *enforced*) is not actually met, so a future change to a scenario
YAML or a new caller of an exported function could silently produce NaN/Infinity, a raw
(non-`SimulationError`) exception, or a subtly wrong number instead of the clean, named
failure this codebase otherwise guarantees everywhere else.

## Warnings

### WR-01: `marginal_roas_at`'s zero-spend branch is mathematically wrong at `s == 1.0`

**File:** `src/ambo/simulate/truth.py:104-114`
**Issue:** At `a == 0.0`, the function returns exactly `0.0` for every `s >= 1.0`:

```python
a = x_mean / (1.0 - params.lam)
if a == 0.0:
    if params.s >= 1.0:
        return 0.0
    raise SimulationError(...)
```

The true derivative of Hill saturation at the origin is `dh/da = s*K^s*a^(s-1) / (a^s+K^s)^2`.
For `s > 1`, `a^(s-1) -> 0` as `a -> 0`, so the limit genuinely is `0`. But for `s == 1.0`
exactly, `a^(s-1) = a^0 = 1` (the limit from the positive side), giving
`dh/da -> K / K^2 = 1/K`, i.e. `marginal_roas_at` should return
`beta * K / K^2 * (1/(1-lam)) = beta / (K * (1-lam))`, **not** `0.0`, whenever `beta > 0`.
`search_generic` — one of the six SPEC-01 channels, used in all three shipped scenarios —
has `true_params.s == 1.0` exactly, so this is not a hypothetical parameter combination.

This branch is currently unreachable in the shipped pipeline only because
`compute_truth` already raises `SimulationError` before calling `marginal_roas_at` if a
channel's total window spend is `0.0` (so `mean_weekly_spend_eur` can never be exactly
`0.0` in practice). But `marginal_roas_at` is public, exported, and documented as safe to
call standalone (its own docstring: "Returns... `0.0` for `s >= 1.0`" — stated as a general
contract, not as "unreachable in this phase"). A future caller (e.g. Phase 3/8's export
code, which the module docstring explicitly anticipates reusing this function) that calls
it directly with `x_mean=0.0` for an `s==1.0` channel will get a silently wrong marginal
ROAS of `0.0` instead of a `SimulationError` or the correct finite value.

**Fix:** Special-case `s == 1.0` to return the closed-form value instead of `0.0`:
```python
if a == 0.0:
    if params.s > 1.0:
        return 0.0
    if params.s == 1.0:
        return float(params.beta * params.K / params.K**2 * (1.0 / (1.0 - params.lam)))
    raise SimulationError(...)
```
and add a regression test at `x_mean=0.0, s=1.0` (currently no test in `test_truth.py`
exercises this branch at all).

### WR-02: `PlatformBiasParams` has no positivity validation on `phi`/`theta`/`cpm`

**File:** `src/ambo/simulate/config.py:182-205`
**Issue:** `TrueParams` and `SpendPattern` both validate every numeric field's domain
explicitly (`K > 0`, `s > 0`, `mean > 0`, `sd >= 0`, etc.). `PlatformBiasParams` only
validates the all-or-none pairing of `phi`/`theta`/`cpm` (`_validate_all_or_none`) — it
never checks that `cpm > 0` or that `phi`/`theta` are non-negative. A scenario YAML with
`cpm: 0.0` (or a negative value) for an online channel loads without error, then in
`platform_bias.platform_report`:
```python
impressions_raw = round_half_up(channel_spend / platform.cpm * 1000.0)
```
divides by zero, producing `inf`/`nan`, which `round_half_up` (`np.floor(x + 0.5).astype(np.int64)`)
then silently casts to an undefined/overflowed `int64` value rather than raising — exactly
the kind of un-named failure this codebase's `SimulationError` convention exists to prevent
everywhere else it applies this discipline.
**Fix:** Add field validators mirroring `TrueParams`/`SpendPattern`'s pattern:
```python
@field_validator("cpm")
@classmethod
def _cpm_is_positive_when_set(cls, value: float | None) -> float | None:
    if value is not None and not value > 0.0:
        raise ValueError(f"cpm must be > 0 when set, got {value!r}")
    return value
```
(and analogous non-negativity checks for `phi`/`theta` if SPEC-01 section 6 constrains
their sign, which the current shipped YAMLs' all-positive values suggest it does).

### WR-03: `ScenarioConfig`'s top-level scalars have no domain validation

**File:** `src/ambo/simulate/config.py:246-262`
**Issue:** `b0`, `growth`, `noise_share`, `aov_base`, `aov_advent_bonus`, and
`promo_multiplier` are declared as plain `float` fields with no `field_validator`, unlike
every other numeric model in this file. Concretely reachable failure modes if any of these
were ever misauthored in a scenario YAML:
- `aov_base <= 0` (with `aov_advent_bonus` not compensating on non-Advent weeks) makes
  `orders = round_half_up(revenue / aov)` in `dgp.assemble_scenario` divide by zero on every
  non-Advent week — a raw `ZeroDivisionError`/`inf`/`nan`, never a `SimulationError`.
- `noise_share < 0` makes `sigma = cfg.noise_share * mean(base)` negative, and
  `rng.normal(0.0, sigma, size=T)` raises a bare `ValueError` from NumPy (`scale < 0`) —
  again, not the project's own `SimulationError` boundary-conversion convention that
  `errors.py`'s `SimulationError` docstring and `09_ANTI_PATTERNS` A-7 both call for.

This is inconsistent with the rest of the file, which is otherwise scrupulous about
converting every domain violation into a named `SimulationError`/`ValidationError` at
load time rather than letting it surface as a raw exception deep inside `assemble_scenario`.
**Fix:** Add field validators for the fields whose sign matters for correctness
(`b0 > 0`, `noise_share >= 0`, `aov_base > 0`, `promo_multiplier > 0`); `growth` and
`aov_advent_bonus` can legitimately be zero or (for `growth`) mildly negative, so those
may warrant a looser bound rather than strict positivity.

### WR-04: `SimulationResult`'s "cannot exist in a violating state" guarantee only holds at construction time

**File:** `src/ambo/simulate/dgp.py:334-373`
**Issue:** The class docstring states: "A `SimulationResult` that violates the
decomposition cannot exist." This is only true immediately after `__init__` runs. The
dataclass is `frozen=True`, which prevents *reassigning* `result.components = ...`, but
does nothing to prevent in-place mutation of the `pandas.DataFrame` object each field
already holds — e.g. `result.components.iloc[0, result.components.columns.get_loc("base")] = 999.0`
succeeds silently and immediately violates the SIM-071 invariant the constructor just
proved, with no error raised anywhere. Several of this phase's own tests exploit exactly
this fact deliberately and safely (they call `.copy()` first, e.g.
`test_assemble_decomposition_violation_raises_at_construction`), which shows the mutability
is understood by the test author — but the *production* docstring's absolute claim
("cannot exist") is not actually enforced against callers outside the test suite who might
mutate a `SimulationResult`'s frame in place instead of copying it first (nothing in the
public API prevents this).
**Fix:** Either soften the docstring claim to "cannot be *constructed* in a violating
state" (accurate) and note the mutability caveat explicitly, or defensively `.copy()` every
DataFrame field in `__post_init__` before storing it, so the constructed object is actually
immutable from the caller's perspective, matching the stronger claim the docstring makes.

### WR-05: `write_truth` does not guard against non-finite floats reaching the JSON writer

**File:** `src/ambo/simulate/truth.py:337-363`
**Issue:** `json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)` is called
with `allow_nan` at its default (`True`). If a `TruthFile` ever carried a `NaN`/`Infinity`
value (e.g., via WR-01's edge case, or any future division-by-zero reachable through WR-02/
WR-03), `write_truth` would silently emit the non-standard JSON tokens `NaN`/`Infinity`/
`-Infinity` into a committed artifact instead of raising — these tokens are not valid per
RFC 8259 and would break any strict (non-Python) JSON consumer reading `truth.json`
downstream, quietly defeating this module's own stated "byte-stable, spec-conformant"
goal. (Note: `_gate_sim_075`'s reload-and-revalidate step would likely catch this
*after* the fact via `TruthFile.model_validate_json`, since pydantic-core's JSON parser is
strict — but the corrupt artifact would already be committed to disk by that point.)
**Fix:** Pass `allow_nan=False` to `json.dumps` so a non-finite float raises immediately at
write time with a clear `ValueError`, rather than producing a quietly-invalid artifact:
```python
text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
```

## Info

### IN-01: `round_half_up` documents but does not enforce its non-negative-input assumption

**File:** `src/ambo/simulate/dgp.py:50-63`
**Issue:** The docstring states "Assumes non-negative input, as every caller in this
phase's domain guarantees" but the function performs no validation, unlike
`adstock_recursive`/`hill` in the same module, which both explicitly validate their inputs
and raise `SimulationError` on violation. Given WR-02/WR-03 above describe concrete paths
by which a non-finite or negative value could reach this function from an unvalidated
config field, a defensive check here would provide a second line of defense and a much
clearer failure message than a silent `int64` overflow.
**Fix:** Add the same style of guard used elsewhere in this module:
```python
if values.size > 0 and (not np.all(np.isfinite(values)) or np.any(values < 0.0)):
    raise SimulationError(f"round_half_up(): values must be all-finite and non-negative")
```

---

_Reviewed: 2026-08-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
