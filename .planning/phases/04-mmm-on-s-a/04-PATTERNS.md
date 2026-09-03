# Phase 4: MMM on S-A - Pattern Map

**Mapped:** 2026-09-03
**Files analyzed:** contracts + Phase 1–3 analogs (model package is empty except `__init__.py`)
**Analogs found:** 14 direct/role-match; remainder are first model-science files (conceptual
precedent named)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/ambo/model/transforms.py` | math (pure) | transform | `src/ambo/simulate/dgp.py` `adstock_recursive` / `hill` | role-match — **independent copy of the idea, zero shared code** |
| `src/ambo/common/errors.py` (`FitError`) | utility | — | `SimulationError` / `DataContractError` in the same file | exact |
| `tests/unit/test_transforms.py` | test | — | `tests/unit/test_dgp.py` impulse-first adstock tests | exact idiom |
| `pyproject.toml` `[tool.uv] constraint-dependencies` | config | — | none in repo | no analog — uv lock constraint, not a new package |
| `uv.lock` | config | — | existing lock (Phase 1 1A) | exact (re-resolve under constraint) |
| `src/ambo/model/priors.py` | schema | config I/O | `ambo.simulate.config.ScenarioConfig` | role-match |
| `config/priors_synthetic.yaml` | config | — | `config/scenarios/s_a.yaml` | role-match (explicit per-channel block, values equal) |
| `config/settings.yaml` + `common/config.py` (`max_fit_minutes`) | config | — | `adstock_length` sibling field | exact |
| `tests/unit/test_priors.py` | test | — | `tests/unit/test_scenario_config.py` extra=forbid + BP-G-02 equality | role-match |
| `src/ambo/model/mmm.py` | model builder | graph | none | no analog — first PyMC model; contract is SPEC-04 §2 + D-06 names |
| `src/ambo/model/fit.py` | CLI / sampler shell | IO + sample | `src/ambo/simulate/__main__.py` | role-match (thin shell, runtime print, no math) |
| `tests/unit/test_mmm.py` / `test_smoke_fit.py` | test | — | `test_simulate_cli.py` + pytest `smoke` marker already in pyproject | role-match |
| `src/ambo/model/posterior_io.py` | IO | file-I/O atomic | `_atomic_write_csv` in simulate `__main__` | exact (temp+rename, provenance) |
| `src/ambo/model/diagnostics.py` | report writer | file-I/O | `ambo.simulate.__main__.validate_sim` gate table | role-match |
| `src/ambo/model/elicit.py` | pure converters | — | none | no analog — scipy.optimize.brentq; doctests required |
| `Makefile` `fit-synthetic` | config | — | `simulate:` real-target shape | exact |
| `docs/MODULE_CONTRACTS.md` | contract | — | every prior module PR | exact (D-23, same PR as the module) |
| `tests/unit/test_config.py` (sampler-key rewrite) | test | — | itself | exact (narrow the assertion, do not delete) |
| `tests/unit/test_import_independence.py` (print strings) | test | — | itself | exact (stop saying "vacuously empty") |

## Pattern Assignments

### `src/ambo/model/transforms.py` (math — T-301, traps T-1/T-2)

**Analog:** `src/ambo/simulate/dgp.py` lines 243–309 (`adstock_recursive`, `hill`)

**Do copy:** module docstring stating independence from the other package; domain
validation that raises a typed error naming the offending value; functions under ~60
lines; `Implements:` REQ line.

**Do not copy:** the recursive formula; `SimulationError` (use `FitError`); any import
of `ambo.simulate`.

**L as argument, not settings read** — D-15. Callers pass `load_settings().adstock_length`.

**Unrolled convolution** (D-18), not the simulator's Python for-loop over T and not
`np.convolve` in src.

### `tests/unit/test_transforms.py` (impulse first)

**Analog:** `tests/unit/test_dgp.py` lines 258–270

```python
def test_adstock_impulse_response_is_causal() -> None:
    x = np.zeros(50)
    x[10] = 1000.0
    a = adstock_recursive(x, lam=0.6)
    assert (a[:10] == 0).all()
```

Same ordering: impulse / causality **before** any closed-form or "looks smooth" check.
Then pytensor-vs-numpy 1e-10, weights sum to 1, Hill(K)=0.5, scaling round-trip 1e-12,
all-zero channel raises `FitError`.

Numpy reference functions live in this test module (T-301 notes). Hypothesis
`roundtrip` like `test_dgp.py`'s property block is welcome (ADR-007 already paid for).

### `FitError` in `errors.py`

**Analog:** `DataContractError` addition in plan 03-02.

Add the class, update the `docs/MODULE_CONTRACTS.md` `errors.py` Public API bullet,
inherit the redaction invariant by not restating it at length.

### `priors.py` / YAML

**Analog:** `ambo.simulate.config` — pydantic tree, `extra='forbid'`, frozen, load from
path. MD-040 equality test is the cousin of BP-G-02 (YAML equals a spec table): here
YAML channel blocks equal **each other**.

### `fit.py` as imperative shell

**Analog:** `ambo.simulate.__main__.main` — argparse, runtime print first (EB-050),
delegate math, atomic artifact write via another module, `get_logger(__name__)`, no
`print()`.

`pm.sample` lives only here. Sampler kwargs come from `load_settings().sampler`
attribute access (D-05).

### `posterior_io` atomic write

**Analog:** `ambo.simulate.__main__` temp sibling + `os.replace`, delete temp on
exception. Parquet + netCDF. Metadata must include scale factors or `load_posterior`
refuses the file (T-1).

### Makefile `fit-synthetic`

**Analog:** `simulate:` — drop `$(call STUB,4)`, keep the runtime `echo` as the first
recipe line, then `uv run python -m ambo.model.fit --layer P-SA`. D-20: P-SA only.

## Sources

- `.planning/phases/04-mmm-on-s-a/04-CONTEXT.md` (D-01…D-20)
- `.planning/phases/04-mmm-on-s-a/04-RESEARCH.md` (Pitfalls 1–8)
- `docs/SPEC-04_mmm_model.md`
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` §4
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` T-301…T-308
- `src/ambo/simulate/dgp.py`, `tests/unit/test_dgp.py`
- `src/ambo/common/config.py`, `tests/unit/test_config.py`
- `src/ambo/common/errors.py`
