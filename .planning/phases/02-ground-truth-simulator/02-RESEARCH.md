# Phase 2: Ground-Truth Simulator - Research

**Researched:** 2026-08-05
**Domain:** Deterministic synthetic data-generating process (DGP) — geometric adstock,
Hill saturation, seasonal baseline demand, spend-pattern simulation, platform-bias
simulation, byte-stable JSON provenance artifacts. Python 3.12 / numpy / pydantic.
**Confidence:** HIGH (this phase is spec-driven, not exploratory — nearly every claim
traces to SPEC-01, the WBS, or the Implementation Guide; the residual LOW-confidence
items are the two genuinely-open implementer choices D-01/D-02 already delegate, plus
one new dependency-governance question this research surfaces)

## Summary

Phase 2 has almost no free design parameters. SPEC-01 fully specifies the baseline
demand formula, the geometric-adstock/Hill media-effect chain, the six channel spend
patterns, the true parameter table, the three scenarios, the platform-bias formulas,
the six SIM-070…075 gates, and the truth.json derived-quantity set — including the
response-curve grid question that `ROADMAP.md`'s stale INGEST-CONFLICTS WARNING 4 note
still flags as unresolved. It is not: SPEC-01 §8 resolves it explicitly (verified by
reading the file directly, see Common Pitfalls #1). The 02_WBS.md T-101…T-109 task
cards and 05_IMPLEMENTATION_GUIDES.md §1 then operationalize every one of those specs
into module-level contracts (03_MODULES.md §2 / docs/MODULE_CONTRACTS.md), so the
planner's job is sequencing and verification-loop design, not invention.

The one place this research adds material information beyond re-stating the spec: the
project's own EB-030 rule ("any new dependency requires an ADR, including small ones")
applies to CONTEXT.md's D-03 decision to add `hypothesis` for property-based testing.
`hypothesis` is not in the SPEC-08 §3 dependency table nor in Phase 1's `pyproject.toml`
dev group. The plan MUST include an ADR task for this addition — it is a real, unbudgeted
governance step, not optional discretion. Additionally, this project's own automated
package-legitimacy checker flags `hypothesis` as `SUS` (see Package Legitimacy Audit) on
signals that read as a checker/metadata artifact rather than a real risk (`hypothesis` is
a 12+-year-old, extremely widely used PyPI package — `pip index versions` shows an
unbroken release history from `0.0.1` in 2013 to `6.165.1`, and it is literally the
name-brand Python property-testing library the project's own decision D-03 asks for by
name). Per the package-legitimacy protocol this SUS verdict must still be surfaced and
gated behind a `checkpoint:human-verify` task regardless of how confident the research
is that it is a false positive.

**Primary recommendation:** Implement `simulate/` exactly as SPEC-01 + 03_MODULES.md §2
specify, in the WBS's T-101→T-104(parallel)→T-105→T-106→T-107→T-108→T-109 order; add one
extra task early in the phase to (a) get an ADR merged for the new `hypothesis` dev
dependency and (b) run `checkpoint:human-verify` on it per the SUS verdict, before any
property-based test that imports it lands.

## Architectural Responsibility Map

This project is a batch data-generation pipeline, not a client/server application, so
the standard browser/SSR/API/CDN/DB tiers do not apply. The project's own tier system is
the `ambo/*` package boundary declared in `docs/MODULE_CONTRACTS.md` / `03_MODULES.md`
§10 — each capability below is mapped to the package (and, for cross-phase capabilities,
the *later* package) that owns it, since that is what determines correct task
assignment for this phase.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Scenario parameter schema + authored YAMLs | `simulate/config.py` (this phase) | `common/config.py` (reads via settings registry only) | SIM-002: YAML is authoritative; `Settings.scenarios` only points at file paths, never duplicates §4 values (established in Phase 1) |
| Spend-pattern generation (§3) | `simulate/spend_patterns.py` | — | Pure function of `(ScenarioConfig, Generator)` — no I/O, no shared code with `model/` |
| Baseline demand + seasonality (§2.1) | `simulate/dgp.py` | `dbt/seeds/season_windows.csv` (Phase 1, read-only) | Season windows are the one sanctioned shared-CONFIG exception (AD-020); simulator never recomputes calendar logic |
| Adstock/Hill media effect (§2.2) | `simulate/dgp.py` | — | Must be an **independent** implementation from `model/transforms.py` (SIM-003/A-1) — this is the single most important architectural boundary in the phase |
| Revenue assembly + decomposition audit (§2.3) | `simulate/dgp.py` | — | `SimulationResult` is the internal contract SIM-071 checks against |
| Platform-bias simulation (§6) | `simulate/platform_bias.py` | `decide/attribution_gap.py` (Phase 8, consumer) | Truth-side φ/θ generation now; the attribution-gap *model* that must recover it is Phase 8's job |
| truth.json schema + derivation (§8) | `simulate/truth.py` | `validate/recovery.py` (Phase 5, consumer), `decide/optimizer.py` (Phase 7, consumer via DC-401) | This phase's most downstream-load-bearing artifact — three later phases read it directly |
| CLI + gate runner (`make simulate`/`validate-sim`) | `simulate/__main__.py` | `Makefile` (already stubbed, Phase 1) | Wires the above into the two make targets that are this phase's exit criterion |
| Committed scenario CSVs/JSON as the warehouse's Layer P input | `data/synthetic/<scenario>/` (this phase, output) | `dbt/models/raw` (Phase 3, consumer) | Contract boundary: column names/order (SIM-004) are binding on Phase 3's staging layer sight-unseen |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-q1-truth-recovery (contributing) | Model recovers known truth (ROAS, half-lives, saturation, allocation) incl. not hallucinating a zero-effect channel | This phase produces the truth (`truth.json`, SIM-075) that Phase 5's VR-3xx gates check the model against; SIM-003/A-1 independence is what makes that check meaningful rather than circular |
| REQ-grain-and-windows (contributing — Layer P grain) | ISO weeks (Mon–Sun, Europe/Vienna) everywhere; Layer P per SPEC-01 §5 (S-A 156 / S-B 104 / S-C 78 weeks) | T-101/T-103 implement the exact per-scenario week counts and ISO-Monday `week_start` column American SIM-004 requires; `season_windows.csv` (Phase 1, AD-020) is the single calendar source this phase must read, never recompute |

## Standard Stack

### Core

| Library | Version (pinned) | Purpose | Why Standard |
|---------|-------|---------|--------------|
| `numpy` | `>=1.26,<3` (already pinned, Phase 1) | Geometric-adstock recursion, Hill saturation, spend-series generation, seeded `Generator` | Project-wide numeric core; `np.random.Generator` (not the legacy global `numpy.random.seed()`) is NumPy's own documented best practice for reproducible, non-global RNG state — exactly what SIM-001/A-5 require [CITED: blog.scientific-python.org/numpy/numpy-rng, numpy.org/neps/nep-0019-rng-policy.html] |
| `pandas` | `>=2.2,<3` (already pinned) | Weekly time-index frames, ISO-week/date handling, CSV I/O | Already the project's frame library (Phase 1); `pd.Timestamp`/`isocalendar()` gives correct ISO-Monday semantics without hand-rolled week math |
| `pydantic` | `>=2.7` (already pinned) | `ScenarioConfig`, `TruthFile` schemas, `extra='forbid'` | Established project-wide convention (Phase 1: `BaseModel`, not `BaseSettings` — EB-030 makes the separate `pydantic-settings` package an ADR event, and plain `BaseModel` + `functools.lru_cache` already satisfies EB-040) |
| `PyYAML` | `>=6` (already pinned) | Scenario YAML authoring/parsing | Already the project's YAML library (Phase 1's `config.py` uses `yaml.safe_load`) |
| stdlib `json` | 3.12 stdlib | `truth.json` serialization | `json.dump(..., sort_keys=True)` with a fixed float formatter is sufficient for SIM-070 byte-stability — no third-party JSON library needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `hypothesis` | latest `6.x` (verified `6.165.1` on PyPI at research time) | D-03's property-based tests for `adstock_recursive`/`hill` invariants | **New dev dependency — requires an ADR before use (EB-030); see Package Legitimacy Audit and Common Pitfalls #2 below. Not yet in `pyproject.toml`.** |
| `holidays` | `>=0.50` (already pinned, unused by this phase) | N/A for Phase 2 | Phase 1's `generate_season_windows.py` already consumed this; Phase 2 reads the *committed CSV*, never imports `holidays` itself (AD-020 — shared config, not shared code/deps) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `hypothesis` for property tests | Hand-rolled randomized-input loops in plain `pytest` | Rejected: reinvents shrinking/example-minimization for no benefit; D-03 explicitly names `hypothesis` and the user accepted its cost |
| stdlib `json` for truth.json | `orjson`/`ujson` for speed | Rejected: full 3-scenario build budget is <30s (07 Part A) with three small JSON files — no measured performance problem exists to justify a new dependency (A-14 premature optimization) |
| `numpy.random.Generator` per scenario | `numpy.random.seed()` global state | Rejected: SPEC-01/A-5 explicitly forbid global RNG state — it breaks determinism gates intermittently, the most expensive class of bug in this codebase per the project's own anti-pattern catalog |

**Installation (once the ADR for `hypothesis` is merged):**
```bash
uv add --group dev hypothesis
```

**Version verification performed this session:**
- `pip index versions hypothesis` → latest `6.165.1`, unbroken history back to `0.0.1` (2013) — [VERIFIED: PyPI registry]
- `gsd-tools query package-legitimacy check --ecosystem pypi hypothesis` → verdict `SUS`, reasons `too-new` / `unknown-downloads` / `no-repository` — these three signals are inconsistent with the package's actual 12-year history and appear to reflect a checker data-source anomaly (likely reading a re-index timestamp as "publish date"), but per protocol the SUS verdict is surfaced verbatim below and must still be gated, not waved off. [ASSUMED: package identity/reputation — not independently confirmed via Context7 or official docs this session]

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `hypothesis` | PyPI | Checker reports "too-new" (contradicted by `pip index versions` showing releases since 2013) | Checker reports "unknown" (contradicted by general knowledge: one of the most-downloaded Python testing libraries, part of the standard scientific-Python testing toolchain) | Checker reports "none found" (actual repo: `github.com/HypothesisWorks/hypothesis`) | **SUS** (automated) | **Flagged — planner must add `checkpoint:human-verify` before the install task, per protocol, despite the research team's assessment that this is a false positive** |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `hypothesis` — gate its `uv add` behind human confirmation. This is on top of, not instead of, the EB-030 ADR requirement below.

*`hypothesis` was discovered via training knowledge and CONTEXT.md's own D-03 decision text, not via Context7/official docs this session — tag `[ASSUMED]` on its identity per the package-name-provenance rule, notwithstanding registry existence.*

## Architecture Patterns

### System Architecture Diagram

```
config/scenarios/{s_a,s_b,s_c}.yaml  (authored, SIM-002 authoritative)
        │
        ▼
ScenarioConfig (pydantic, extra='forbid')  ── load_scenario(name) ──┐
        │                                                            │
        ▼                                                            │
┌───────────────────────┐   dbt/seeds/season_windows.csv (Phase 1)   │
│ np.random.Generator    │◄──────────────┐                           │
│ seeded from cfg.seed   │               │                           │
└──────────┬─────────────┘               │                           │
           │ draw order: channels        ▼                           │
           │ (taxonomy order), then   season_index()                 │
           │ noise vector             (dgp.py, pure)                 │
           ▼                             │                           │
  generate_spend()                       │                           │
  (spend_patterns.py)                    │                           │
           │                             │                           │
           └──────────────┬──────────────┘                           │
                           ▼                                         │
                 assemble_scenario()  ◄── adstock_recursive() + hill()│
                 (dgp.py orchestrator)     (dgp.py, independent of    │
                           │               model/transforms.py)      │
                           ▼                                        │
                  SimulationResult (frozen; components               │
                  re-sum to revenue within 1e-6 — SIM-071)            │
                           │                                          │
              ┌────────────┼─────────────────┐                       │
              ▼            ▼                 ▼                       │
     media_weekly.csv  outcome_weekly.csv  platform_report()          │
     (spend columns)   (revenue/orders/     (platform_bias.py, §6)    │
                        promo_flag)                │                 │
              └────────────┬─────────────────┘     │                 │
                           ▼                                          │
                   compute_truth()  (truth.py) ──── reads §4/§6 params
                           │                          from cfg + result
                           ▼
                  truth.json (byte-stable: sort_keys, fixed float fmt)
                           │
                           ▼
         validate_sim() gate runner (SIM-070..075, __main__.py)
                           │
                 make simulate && make validate-sim
                           │
                           ▼
        data/synthetic/<scenario>/{media_weekly.csv,
                                    outcome_weekly.csv, truth.json}
                (committed; consumed by Phase 3's dbt raw layer)
```

### Recommended Project Structure

Fixed by `docs/MODULE_CONTRACTS.md` / `03_MODULES.md` §2 — not a design choice for this
phase, reproduced here for planning convenience:

```
src/ambo/simulate/
├── __init__.py        # package docstring only (exists, empty, from Phase 0)
├── config.py           # ScenarioConfig, load_scenario()            (T-101)
├── spend_patterns.py    # generate_spend()                          (T-102)
├── dgp.py               # season_index, adstock_recursive, hill,
│                        # assemble_scenario, SimulationResult        (T-103/T-104/T-105)
├── platform_bias.py     # platform_report()                         (T-106)
├── truth.py             # TruthFile, compute_truth, write_truth      (T-107)
└── __main__.py          # CLI: all|s_a|s_b|s_c, validate_sim()       (T-108)

config/scenarios/
├── s_a.yaml
├── s_b.yaml
└── s_c.yaml

tests/unit/
├── test_scenario_config.py     # spec-table equality, S-C/S-B diff, extra='forbid'
├── test_spend_patterns.py      # SIM-031 stats, determinism, floor/round order
├── test_dgp.py                 # season_index weights, adstock closed-form + impulse
│                                # (SIM-074), Hill(K)=0.5, hypothesis property tests (D-03)
├── test_platform_bias.py       # φ/θ table, NULL offline handling, hand-example check
├── test_truth.py               # SIM-075 schema, byte-stability, S-C zero-ROAS spot check
└── test_simulate_cli.py        # SIM-070 determinism (regen-to-temp-dir byte compare),
                                 # SIM-071/072/073 audits, gate-table exit codes
```

### Pattern 1: Functional Core / Imperative Shell (project-wide, load-bearing here)

**What:** All math (`season_index`, `adstock_recursive`, `hill`, `generate_spend`,
`platform_report`, the marginal-ROAS derivative in `truth.py`) is a pure function of its
explicit arguments (`ScenarioConfig`, an `np.random.Generator`, or plain arrays). Only
`__main__.py` performs I/O (reading YAML, writing CSV/JSON).
**When to use:** Every module in `simulate/` — this is what makes SIM-070's byte-identity
gate and SIM-071's decomposition audit tractable to test in isolation.
**Example (illustrative — signatures, not implementation, per the module contract's
"signatures are contracts" convention):**
```python
# Source: docs/MODULE_CONTRACTS.md §2 (schematic, not literal source)
def adstock_recursive(x: np.ndarray, lam: float) -> np.ndarray:
    """Pure, O(T), causal. a_0 = 0. a_t depends only on x_{<=t}."""
    ...


def assemble_scenario(cfg: ScenarioConfig, rng: np.random.Generator) -> "SimulationResult":
    """Orchestrator — the only function that sequences the pure pieces above."""
    ...
```

### Pattern 2: Single Seeded Generator, Documented Draw Order

**What:** One `np.random.Generator` instantiated once per scenario from `cfg.seed`
(never reused across scenarios, never the legacy global seed). Consumption order is
fixed and must be documented in the module docstring: channels in taxonomy order, then
the noise vector (T-105's revenue assembly draws noise *after* all six channels'
spend draws).
**When to use:** `spend_patterns.py` and the noise draw inside `dgp.py`'s revenue
assembly — anywhere SPEC-01 calls for a stochastic draw.
**Why it matters here specifically:** this is the mechanism SIM-001/SIM-070's
byte-determinism gate depends on; NumPy's own `Generator` bit-stream carries **no
cross-version compatibility guarantee** [CITED: numpy.org/doc/stable/reference/random/bit_generators/generated/numpy.random.SeedSequence.html]. This is not a live risk for
AMBO specifically because `uv.lock` pins the exact numpy build across dev machines and
CI, but the planner should not assume "seeded Generator ⇒ portable forever" as a general
fact — only "seeded Generator + pinned numpy version ⇒ reproducible here."

### Pattern 3: Byte-Stable JSON Serialization

**What:** `truth.json` written with `json.dump(data, f, sort_keys=True, indent=2)` plus a
fixed float formatter (Guide §1.5 specifies `%.10g`) and LF line endings (already
enforced repo-wide by `.gitattributes`, Phase 1/D-22).
**When to use:** `truth.py`'s `write_truth()` — the sole place this formatting logic
should exist (single-home rule, A-8).
**Example:**
```python
# Source: docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md §1.5 (formula only)
def _fixed_float(x: float) -> str:
    return f"{x:.10g}"


# json.dump's default float repr is NOT what SIM-070 needs -- Python's repr(float)
# is round-trip-exact but not necessarily identical in string form across float
# values that differ in the 17th significant digit only; %.10g gives a fixed,
# shorter, deterministic representation. Confirm the exact json.dump hook mechanism
# (default= for floats requires a custom encoder subclass, since json.dump's float
# formatting is NOT independently hookable via a simple kwarg) during T-107 --
# this is a real implementation detail to verify against Python 3.12's json module,
# not assumed correct by analogy.
```

### Anti-Patterns to Avoid

- **Vectorizing the adstock recursion "for speed":** A-14/Guide §1.4 — a plain forward
  loop over `t` is correct and clear; premature vectorization risks the causality
  invariant (`a_t` depending on future `x`) for no measured benefit (full build budget
  is <30s already).
- **Any import between `simulate/` and `model/`, in either direction:** A-1/SIM-003 —
  even a "just this one small helper" adstock/Hill share collapses the entire recovery
  argument. `tests/unit/test_import_independence.py` already exists (from Phase 1,
  T-010) and is currently vacuously green because both packages are empty; it becomes
  load-bearing the moment `simulate/dgp.py` lands.
- **Baking the promo/burst placement script (D-02) into `src/ambo/simulate/` as an
  importable module:** A-13 — it is explicitly a throwaway authoring aid per CONTEXT.md;
  its output gets frozen into YAML and it should live outside `src/` (e.g. a one-off
  script under `scripts/` marked clearly as dev-only, or discarded after use) or it risks
  becoming unintentional "shipped" speculative-generality code with no WBS task and no
  module-contract entry to keep it honest.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Randomized invariant testing with shrinking | A custom loop of `random.random()` calls + manual bisection on failure | `hypothesis` (D-03, pending ADR) | Hypothesis's example-shrinking is exactly what makes a counterexample to "adstock output ≤ x/(1−λ)" actionable instead of an opaque failure |
| ISO week / Monday-of-week computation | Hand-rolled `datetime` arithmetic for "the Monday of ISO week N" | `pandas`/stdlib `datetime.date.fromisocalendar()` (already used in Phase 1's `generate_season_windows.py`) | ISO week/year boundary edge cases (week 53, year-crossing weeks) are a classic off-by-one source; the project already has a working, tested reference in the season-windows generator |
| Property-based numeric bounds (`min_value`/`max_value` clamping in tests) | Manual `assume()`-heavy filtering of broadly-generated floats | `st.floats(min_value=..., max_value=..., allow_nan=False, allow_infinity=False)` / `st.integers(min_value=...)` directly [CITED: semaphore.io/blog/property-based-testing-python-hypothesis-pytest] | Generating in-bounds data directly is faster and avoids Hypothesis's "too much filtering" health-check failures |
| Round-trip / closed-form derivative checks | Numerically differentiating `β·Hill(a)` for the marginal-ROAS test | The analytic formula already given in Guide §1.5 (`dm/dx = β·s·K^s·a^{s−1}/(a^s+K^s)^2 · 1/(1−λ)`) | The spec already hands you the exact closed form; a numerical-differentiation test would introduce its own tolerance/step-size tuning problem for no reason |

**Key insight:** almost nothing in this phase is a "pick a library and integrate it"
problem — the math is fully specified. The hand-rolling risk here is procedural, not
algorithmic: re-deriving calendar arithmetic that Phase 1 already solved, or writing a
bespoke fuzzer where `hypothesis` is explicitly asked for.

## Common Pitfalls

### Pitfall 1: Treating the response-curve grid as still unresolved
**What goes wrong:** `ROADMAP.md`'s Phase 2 section still carries INGEST-CONFLICTS
WARNING 4 text ("Must resolve before execution... Decide before writing `truth.py`:
interpolate truth onto the model grid, truncate the truth grid at 1.5×, or emit two
grids...") as if it were an open decision for this phase.
**Why it happens:** `ROADMAP.md` was written before `SPEC-01_ground_truth_simulator.md`
§8 was amended with its "Grid note (resolves INGEST-CONFLICTS WARNING 4)" paragraph —
the roadmap text is now stale, not authoritative.
**How to avoid:** Read SPEC-01 §8 directly (verified in full this session). It is
already resolved: truth.json's 21-point 0…2×max grid is a **diagnostic-only** sample,
never used for comparison; `exports/response_curves.csv` (Phase 3/8, AD-050) carries
one grid only — the MD-082 grid (21 points, 0…1.5×max **observed** weekly spend) — with
the truth column on that export being the closed-form curve evaluated **at those same
21 points**, not the diagnostic array. The concrete implication for **this phase**:
`truth.py`'s response-curve logic should be structured as a reusable pure function of a
caller-supplied grid (SPEC-01 §8: "The simulator exposes the curve as a function of a
caller-supplied grid"), not just a value baked once into `TruthFile` at the fixed 0…2×
points — Phase 3/8's export script will need to call the same closed-form evaluator at
the 1.5× grid later, and 03_MODULES.md §2.5's current contract for `truth.py` doesn't
yet name that function explicitly. **Recommend the plan add this exposed function
(e.g. `response_curve_at(true_params, x_grid) -> np.ndarray`) to `docs/MODULE_CONTRACTS.md`
in the same PR as `truth.py`, per the contract-first rule**, even though it is not
literally required to pass any SIM-07x gate in *this* phase — it is required so Phase
3/8 doesn't have to reverse-engineer or re-derive the formula from `truth.json`'s
diagnostic array.
**Warning signs:** A `truth.py` implementation that only ever computes the 0…2× array
inline inside `compute_truth()` with no separately callable/importable closed-form
curve function is under-built for what §8 actually asks for.

### Pitfall 2: `hypothesis` is a new dependency requiring an ADR, not just a pip install
**What goes wrong:** D-03 reads as "add property-based tests" without flagging that
this project's own EB-030 rule ("Any upgrade or new dependency requires an ADR, including
small ones") applies to a *dev*-only test dependency exactly as much as a runtime one.
`hypothesis` is absent from both SPEC-08 §3's dependency table and Phase 1's
`pyproject.toml` `[dependency-groups] dev` list.
**Why it happens:** EB-030's "including small ones" clause is easy to read past when
the addition is "just a test tool"; the project has, however, treated even a *type-stub*
addition as ADR-relevant territory before (Phase 1 explicitly chose a `mypy` override
over adding `types-PyYAML` specifically to avoid triggering this rule).
**How to avoid:** Plan an explicit task, sequenced before the first property-based test
task, to (a) write and merge an ADR for adding `hypothesis` as a dev dependency
(GB-201/202 — standard trigger "new dependency"), and (b) run `checkpoint:human-verify`
on the package per its `SUS` legitimacy verdict (see Package Legitimacy Audit) before
`uv add`. This is genuine, unbudgeted-in-the-charter-sense scope inside the already-thin
1.5-day / 2× tripwire budget CONTEXT.md's D-03 note explicitly calls out — track it.
**Warning signs:** A plan that adds `hypothesis` to `pyproject.toml` in the same task
that first uses it, with no ADR file in the diff.

### Pitfall 3: `.hypothesis/` cache directory is not yet in `.gitignore`
**What goes wrong:** Hypothesis writes a local example database (`.hypothesis/` by
default, containing pickled/serialized failing examples) the first time any property
test runs or fails. The current `.gitignore` (verified this session) has no entry for it.
**Why it happens:** It's a new-to-this-phase tool; nothing before this phase needed
the entry.
**How to avoid:** Add `.hypothesis/` to `.gitignore` in the same task/PR that introduces
the dependency (a `.gitignore` update, not a `.gitattributes` one — this is a
non-deterministic local cache, not a tracked artifact).
**Warning signs:** `git status` showing an untracked `.hypothesis/` directory after
running the new tests locally.

### Pitfall 4: Convolution-direction reversal in the simulator's own adstock (trap T-2)
**What goes wrong:** `a_t = x_t + λ·a_{t−1}` implemented in a way that lets `a_t` depend
on `x_{t+1}` or later (e.g. an off-by-one in a vectorized cumulative-sum formulation,
or applying the recursion in reverse index order).
**Why it happens:** Geometric-series closed forms are easy to write correctly on paper
and subtly wrong in a vectorized implementation; this is explicitly called out as the
project's own named "trap T-2" and is why SIM-074 mandates *two* tests, not one.
**How to avoid:** Implement as the plain forward `for t in range(...)` loop the Guide
explicitly sanctions (§1.4) rather than a clever vectorization; write the impulse test
(`x = e_k ⇒ a_t = λ^{t−k}` for `t ≥ k`, `0` before) *before* the closed-form test, since
the impulse test is the one that actually catches a direction reversal — the closed-form
limit test alone can pass even with certain reversed implementations if the reversal is
symmetric in effect (WBS/Guide's own emphasis: "this is the test that kills the
reversed-convolution bug").
**Warning signs:** Closed-form test green but impulse test showing nonzero adstock
*before* the impulse week.

### Pitfall 5: `hypothesis` property-strategy choice interacting with SIM-domain constraints
**What goes wrong:** Using unconstrained `st.floats()` for spend/adstock inputs, which
by default includes NaN, ±infinity, and subnormals — all of which are meaningless in
this domain and will produce spurious Hypothesis-discovered "failures" that are really
test-strategy bugs, not `adstock_recursive`/`hill` bugs.
**Why it happens:** `st.floats()`'s permissive defaults are a common first-use gotcha
generally, not specific to this project [CITED: semaphore.io/blog/property-based-testing-python-hypothesis-pytest].
**How to avoid:** Always pass `allow_nan=False, allow_infinity=False`, and a sensible
`min_value=0` for spend/adstock domains (both `adstock_recursive` and `hill` are
undefined or raise `ValueError` for negative input per the module contract). Combine
property tests with the fixed example tests (`Hill(K)=0.5` exact, the impulse test)
rather than relying on generated examples alone to hit that precise boundary case.
**Warning signs:** A property test failing on `float('nan')` or a subnormal float with
no domain meaning.

### Pitfall 6: Floor/round/multiply order in spend-pattern generation
**What goes wrong:** Applying the seasonal multiplier, drawing from the Normal, flooring,
and rounding in the wrong order (e.g. rounding before flooring, or flooring the mean
before drawing) silently shifts SIM-031's annual-total and zero-week-share statistics
outside their ±10%/±10pp tolerance without any single step looking "wrong" in isolation.
**Why it happens:** The Guide is explicit about the order (§1.3: "apply to the *mean* of
the Normal, then draw, then floor, then round") precisely because it is easy to get
subtly wrong and only surfaces as a failed statistical test, not a crash.
**How to avoid:** Implement the four steps as an explicit, commented sequence matching
Guide §1.3's order verbatim; write the SIM-031 statistical tests *before* believing the
implementation is done, not as an afterthought.
**Warning signs:** SIM-031 annual-total test failing by a suspiciously small, systematic
margin (a rounding/ordering bug tends to bias in one consistent direction, unlike a
genuinely wrong distribution parameter which tends to miss by more).

### Pitfall 7: S-C↔S-B "minimal diff" test asserting the wrong thing
**What goes wrong:** Writing the BP-G-02 S-C/S-B YAML-diff test as a literal 3-key diff
(`weeks`, `seed`, `display_video.beta`) when S-C's shortened 78-week window
(2022-W01…2023-W26, pro-rated per BP-D-09) also legitimately changes the *count* and
*placement* of promo/burst weeks compared to S-B's full 104 weeks — a naive 3-field diff
assertion will spuriously fail (or worse, silently pass by only checking those three
keys and missing an actual unrelated divergence elsewhere in the schedule).
**Why it happens:** "S-C is identical to S-B except..." (SPEC-01 §4 footnote, T-101's
acceptance criteria) is a statement about the *generating rule*, not about the literal
YAML diff, once time-window truncation cascades into different promo/burst counts.
**How to avoid:** Design the equality test to assert the *rule*-level invariants
(collinearity flags equal; `display_video.beta` differs exactly as `0` vs S-B's nonzero
value; per-covered-year promo/burst *counts* satisfy the same §3 counting rules in both
files) rather than raw YAML-diff equality on the schedule lists themselves.
**Warning signs:** The diff test failing every time the burst schedule is regenerated
for the shorter window, or conversely, a diff test so loose it wouldn't catch a real
`display_video.beta` typo.

### Pitfall 8: Effort-budget tracking discipline (Charter §5 tripwire)
**What goes wrong:** Not tracking Phase 2's cumulative measured time against the 1.5-day
(720-minute, per Phase 1's own established "8-hour working day" convention for the `d`
unit) budget as D-03's property-based tests add real, accepted-but-real scope.
**Why it happens:** Without a running total, the 2× tripwire (1440 minutes) is easy to
cross silently — Phase 1's BUILD_LOG entry shows the project does track this
per-plan-duration and sum it explicitly at phase close; Phase 2 should do the same from
the start given CONTEXT.md's own explicit flag on this risk.
**How to avoid:** Follow Phase 1's BUILD_LOG pattern — log each plan's measured duration
in `.planning/STATE.md`'s Performance Metrics table as it completes, and sum against the
720/1440-minute thresholds at phase close, escalating (stop + ADR) if the 2× line is
crossed rather than absorbing it silently.
**Warning signs:** Reaching T-108/T-109 without a running effort total anywhere.

## Code Examples

Formulas and illustrative patterns only (per this project's own convention that
implementation guides carry math/pseudocode, not literal source — `03_MODULES.md`'s
"signatures are contracts, not implementations"):

### Adstock closed-form and impulse tests (SIM-074)
```python
# Source: docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md §1.4 (formulas)
# Closed form: constant spend x for T weeks -> a_T -> x / (1 - lam) as T grows.
# a_t = x * (1 - lam**t) / (1 - lam)   # exact finite-T formula
# Impulse: x = e_k (single spike at week k) -> a_t = lam**(t-k) for t >= k, else 0.


def test_adstock_closed_form_limit() -> None:
    x = np.full(200, 1000.0)
    a = adstock_recursive(x, lam=0.6)
    assert abs(a[-1] - 1000.0 / (1 - 0.6)) < 1e-9


def test_adstock_impulse_response() -> None:
    x = np.zeros(50)
    x[10] = 1000.0
    a = adstock_recursive(x, lam=0.6)
    assert (a[:10] == 0).all()
    for t in range(10, 50):
        assert abs(a[t] - 1000.0 * 0.6 ** (t - 10)) < 1e-9
```

### Hypothesis property test skeleton (D-03, pending the ADR/checkpoint from Pitfall 2)
```python
# Source: pattern per semaphore.io/blog/property-based-testing-python-hypothesis-pytest
# (bounds-direct strategy) + this project's own SIM-074 domain (a >= 0, K > 0, s > 0).
from hypothesis import given, settings
from hypothesis import strategies as st


@given(
    x=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    lam=st.floats(min_value=0, max_value=0.99, allow_nan=False, allow_infinity=False),
)
def test_adstock_bounded(x: float, lam: float) -> None:
    a = adstock_recursive(np.full(52, x), lam)
    assert (a >= 0).all()
    assert (a <= x / (1 - lam) + 1e-6).all()


@given(
    a=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    K=st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False),
    s=st.floats(min_value=0.1, max_value=5, allow_nan=False, allow_infinity=False),
)
def test_hill_bounded_and_domain(a: float, K: float, s: float) -> None:
    h = hill(np.array([a]), K, s)
    assert 0 <= h[0] <= 1


def test_hill_at_k_is_half() -> None:
    assert abs(hill(np.array([3000.0]), K=3000.0, s=1.0)[0] - 0.5) < 1e-12
```

### Byte-stable truth.json write (SIM-070/SIM-075)
```python
# Source: docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md §1.5 (formula: sort_keys,
# fixed float format, LF endings). The float-formatting mechanism (json.JSONEncoder
# subclass vs. pre-formatting floats to strings before dump) is an implementation
# decision to verify at T-107 -- Python's json module does not expose a simple
# per-float-format hook via a kwarg, only via a custom encoder or a float_repr override
# on a subclass; confirm which approach the codebase already uses elsewhere (none yet).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `numpy.random.seed()` global RNG | `numpy.random.Generator`/`default_rng()` instance passed explicitly | NumPy 1.17 (2019), now the documented best practice | Already the project's Phase 1 convention; Phase 2 must continue it per-scenario, never globally [CITED: numpy.org/neps/nep-0019-rng-policy.html] |
| `pydantic.BaseSettings` for schema+env-var binding | `pydantic.BaseModel` + explicit env read, since `BaseSettings` moved to the separate `pydantic-settings` package in pydantic v2 | Established in this repo at Phase 1 (T-004) | Directly reused for `ScenarioConfig`/`TruthFile` — no new pattern to introduce |

**Deprecated/outdated:** none specific to this phase beyond the two above, both already
resolved by Phase 1 precedent.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `hypothesis`'s identity/reputation as a legitimate, long-established package (contra the automated `SUS` verdict) | Standard Stack, Package Legitimacy Audit | Low technical risk (it is genuinely a well-known package), but process risk: skipping the mandated `checkpoint:human-verify` because the research team is "confident" would violate this project's own governance discipline (the same discipline SIM-070/GB-501 depend on elsewhere) |
| A2 | Exact ISO week numbers for the 5 "spread" promo weeks/year and unanchored print/radio burst starts (S-A/S-B/S-C) | Not covered in this doc — explicitly delegated to the implementer by D-01/D-02 | Low — CONTEXT.md already accepts this as implementer discretion, gated only by SIM-030/031 passing |
| A3 | The exact mechanism for hooking a fixed float format into Python's stdlib `json.dump` (custom encoder vs. pre-formatting) | Code Examples, Pitfall (embedded) | Low-medium — a wrong choice would surface immediately as a SIM-070 byte-comparison failure in T-108's own gate, not silently |
| A4 | `hypothesis`'s default `max_examples` (100) is sufficient without a project-specific `settings` profile override | Code Examples | Low — CI test-suite runtime budget has slack (no `@pytest.mark.smoke`-style budget applies to plain unit tests); a slow property test would surface as a measured test-suite duration increase, not a correctness issue |

**If this table is empty:** N/A — see rows above. All four are low-risk, non-blocking,
and either already explicitly delegated by CONTEXT.md (A2) or self-revealing on first
test run (A3, A4). A1 is the one item genuinely worth a human glance given the project's
own governance-first culture.

## Open Questions

1. **Should `truth.py` expose a caller-supplied-grid response-curve function now, or is
   returning only the fixed 0…2× array in `TruthFile` sufficient for this phase's own
   gates?**
   - What we know: SIM-075/SIM-070/071/072/073/074 (this phase's own gates) only require
     the 21-point 0…2× diagnostic array to exist inside `truth.json`, schema-validated.
     Nothing in *this phase's* gate list requires the caller-supplied-grid capability.
   - What's unclear: whether deferring that capability to Phase 3/8 (when the export
     script is actually written) risks a Phase 8 rediscovery of the exact closed-form
     formula from scratch, duplicating logic instead of reusing it (a mild A-8 risk
     three phases downstream).
   - Recommendation: build the small reusable function now (cheap, pure, already fully
     specified by Guide §1.5's formula) and register it in `docs/MODULE_CONTRACTS.md`
     in the same PR, even though no *this-phase* gate strictly requires it — the marginal
     cost is near zero and it directly serves SPEC-01 §8's explicit "exposes... as a
     function of a caller-supplied grid" sentence.

2. **Does the `hypothesis` ADR get one of the five pre-planned slots (ADR-001…005) or a
   new ADR-006+?**
   - What we know: GB-202 pre-plans exactly five ADR slots (permission/sector,
     channel-mapping, anonymization-recipe, Layer-R-window, reparameterization-ladder) —
     none is "new test dependency."
   - What's unclear: whether the project wants a lightweight ADR-006-style entry (Phase 1
     already used ADR-006 for the module-contracts document promotion, per STATE.md) or
     prefers to fold this into Phase 2's own milestone PR without a dedicated ADR number.
   - Recommendation: treat it as a new, ordinary ADR (next available number) — EB-030's
     "including small ones" phrasing reads as intentionally not carving out an exception
     for dev-only or small dependencies.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all of `simulate/` | ✓ | 3.12.10 | — |
| `uv` | dependency install (`uv add --group dev hypothesis`) | ✓ | 0.11.29 | — |
| `git` | ADR commit, BUILD_LOG discipline | ✓ | 2.55.0 | — |
| `hypothesis` (PyPI) | D-03 property-based tests | ✗ (not yet installed — pending ADR per Pitfall 2) | latest `6.165.1` confirmed resolvable | Point-value + closed-form tests alone (already WBS-mandated) cover SIM-074 without it; `hypothesis` is additive rigor, not a blocking dependency for the phase's own exit gate |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `hypothesis` — the phase's own exit criteria
(SIM-070…075) do not require it; D-03's property tests are additional rigor the user
explicitly accepted, gated by an ADR + checkpoint that should land before it's installed.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest>=8` + `pytest-cov` (already configured, Phase 1) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (coverage gate currently non-blocking per D-15 until M0 exit criteria — verify whether it has flipped blocking by Phase 2's start) |
| Quick run command | `uv run pytest tests/unit/test_dgp.py tests/unit/test_scenario_config.py -q` (per-module, fast) |
| Full suite command | `make test` (wired from Phase 1) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIM-002/BP-G-02 | Scenario YAML == SPEC-01 §4 table; S-C/S-B minimal-diff (rule-level, per Pitfall 7) | unit | `pytest tests/unit/test_scenario_config.py -x` | ❌ Wave 0 |
| SIM-030/031 | Spend-pattern statistics (annual totals ±10%, zero-week share ±10pp), determinism | unit | `pytest tests/unit/test_spend_patterns.py -x` | ❌ Wave 0 |
| SIM-073 | Season weights exact; peak-revenue week in Advent | unit | `pytest tests/unit/test_dgp.py -k season -x` | ❌ Wave 0 |
| SIM-074 | Adstock closed-form + impulse; Hill(K)=0.5 exact; D-03 hypothesis properties | unit + property | `pytest tests/unit/test_dgp.py -k "adstock or hill" -x` | ❌ Wave 0 |
| SIM-060/061 | φ/θ platform-bias formulas; NULL offline handling; hand-computed example | unit | `pytest tests/unit/test_platform_bias.py -x` | ❌ Wave 0 |
| SIM-071/072 | Decomposition audit ≤1e-6; media-share/noise-variance plausibility bounds | unit | `pytest tests/unit/test_dgp.py -k assemble -x` | ❌ Wave 0 |
| SIM-075 | truth.json schema-complete; S-C zero-ROAS spot check; byte-stable | unit | `pytest tests/unit/test_truth.py -x` | ❌ Wave 0 |
| SIM-070 | Two `make simulate` runs byte-identical | integration | `pytest tests/unit/test_simulate_cli.py -k determinism -x` | ❌ Wave 0 |
| REQ-grain-and-windows (P grain) | Exact per-scenario week counts (156/104/78), ISO-Monday `week_start` | unit | `pytest tests/unit/test_scenario_config.py -k weeks -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the relevant module's quick-run command above.
- **Per wave merge:** `make test` (full suite, includes all guard tests from Phase 1).
- **Phase gate:** `make simulate && make validate-sim` green (SIM-070…075 gate table)
  before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/unit/test_scenario_config.py` — covers SIM-002, BP-G-02, REQ-grain-and-windows
- [ ] `tests/unit/test_spend_patterns.py` — covers SIM-030, SIM-031
- [ ] `tests/unit/test_dgp.py` — covers SIM-073, SIM-074, SIM-071, SIM-072 (+ D-03 hypothesis properties once the ADR lands)
- [ ] `tests/unit/test_platform_bias.py` — covers SIM-060, SIM-061
- [ ] `tests/unit/test_truth.py` — covers SIM-075
- [ ] `tests/unit/test_simulate_cli.py` — covers SIM-070, the gate-runner's own exit-code behavior
- [ ] Framework install: no new pytest infra needed — `hypothesis` is the only new install, and only for `test_dgp.py`'s property-based subset (pending ADR)
- [ ] `conftest.py` already has a `repo_root` fixture (used by Phase 1's guard tests) — reusable as-is for the new test files, no new shared fixture needed unless a scenario-config-loading fixture proves useful across multiple test files

## Security Domain

`security_enforcement` is absent from `.planning/config.json` (only
`workflow._auto_chain_active: false` is set), so per the default it is treated as
enabled. This phase, however, has no user-facing surface, no authentication, no network
I/O (EB-070 forbids `requests` anywhere in `src/`), and processes no real/private data
(SIM-004's outputs are entirely synthetic and disclosed by design) — most ASVS
categories genuinely do not apply, and forcing a fit would misdirect planning effort.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user-facing surface in this phase |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes | `pydantic.BaseModel` with `extra='forbid'` on `ScenarioConfig`/`TruthFile` (already the project convention); `ValueError` on out-of-domain `hill()`/`adstock_recursive()` inputs per the module contract |
| V6 Cryptography | No | No secrets, no crypto operations in this phase (the private-drop / anonymization crypto-adjacent concerns belong to Phase 6) |

### Known Threat Patterns for this stack

This phase's real "threat model" is scientific/process integrity, not a conventional
attacker surface — the project's own anti-pattern catalog (`09_ANTI_PATTERNS.md`) already
enumerates the equivalent STRIDE-style concerns specific to this codebase; reproduced
here as the closest analog:

| Pattern | STRIDE-analog | Standard Mitigation |
|---------|--------|---------------------|
| Simulator–model code sharing (A-1) | Tampering (with the recovery argument's integrity) | AST guard test (`test_import_independence.py`, already exists from Phase 1, currently vacuous) |
| Spec drift / gate widening to force green (A-9/A-18) | Repudiation / Tampering | Spec-table equality tests (T-101); ADR requirement for any deviation |
| Hidden state / global RNG seeding (A-5) | Non-determinism as a denial-of-reproducibility | Explicit `Generator` injection, never `numpy.random.seed()` |

## Sources

### Primary (HIGH confidence)
- `docs/SPEC-01_ground_truth_simulator.md` (full file read this session) — the DGP,
  gates, truth.json derivations, and the §8 response-curve grid resolution
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` T-101…T-109 (full task cards read this session)
- `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` §1 (full section read this session)
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` §2, §10 and `docs/MODULE_CONTRACTS.md` (module
  contracts and dependency-direction rules, both read in full)
- `docs/EXECUTION_BLUEPRINT/09_ANTI_PATTERNS.md`, `10_VALIDATION_GATES.md`,
  `04_DEPENDENCIES.md`, `01_PHASES.md` (P1 section), `06_CHECKLISTS.md` (M1 section)
- `.planning/phases/02-ground-truth-simulator/02-CONTEXT.md`, `.planning/REQUIREMENTS.md`,
  `.planning/STATE.md`, `.planning/intel/constraints.md`, `.planning/intel/decisions.md`
- `src/ambo/common/config.py`, `config/settings.yaml`, `pyproject.toml`,
  `tests/unit/test_import_independence.py`, `.gitattributes`, `.gitignore` — all read
  directly from the current repository state this session
- `pip index versions hypothesis` (executed this session) — PyPI registry version history
- `gsd-tools query package-legitimacy check --ecosystem pypi hypothesis` (executed this
  session) — verdict SUS

### Secondary (MEDIUM confidence)
- WebSearch: NumPy `Generator`/`SeedSequence` best practices and cross-version
  compatibility caveat (numpy.org NEP-19, numpy.org SeedSequence docs, blog.scientific-python.org)
- WebSearch: Hypothesis property-based testing best practices for numeric invariants
  (semaphore.io/blog/property-based-testing-python-hypothesis-pytest)

### Tertiary (LOW confidence)
- `hypothesis` package reputation/identity as assessed from training knowledge, not
  independently confirmed via Context7 or official docs this session (see Assumptions
  Log A1) — tagged `[ASSUMED]` per the package-name-provenance rule despite PyPI
  registry confirmation of existence.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every core library is already pinned by Phase 1; `hypothesis`
  is the sole addition and its version/existence is registry-verified (identity/reputation
  is the one `[ASSUMED]` item)
- Architecture: HIGH — module contracts, dependency directions, and data flow are fully
  specified in `docs/MODULE_CONTRACTS.md`/`03_MODULES.md`, not left to this phase's
  design discretion
- Pitfalls: HIGH — six of eight pitfalls are direct restatements of named project traps
  (T-2, A-1, A-5, A-8, A-9, A-13/A-14) with explicit enforcement mechanisms already in
  the repo; the two novel findings (hypothesis-as-new-dependency, response-curve grid
  staleness in ROADMAP.md) were independently verified by reading source files this
  session, not inferred

**Research date:** 2026-08-05
**Valid until:** 30 days (spec-driven phase on a stable internal spec; re-verify sooner
only if SPEC-01, the WBS, or MODULE_CONTRACTS.md change before planning starts)
