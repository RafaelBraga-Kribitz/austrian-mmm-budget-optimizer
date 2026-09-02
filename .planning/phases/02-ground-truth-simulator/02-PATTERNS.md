# Phase 2: Ground-Truth Simulator - Pattern Map

**Mapped:** 2026-08-05
**Files analyzed:** 15 (6 `src/ambo/simulate/` modules, 3 scenario YAMLs, 6 test files)
**Analogs found:** 15 / 15 (all role-match or exact; no "no analog" files — Phase 1
established every convention this phase needs to extend)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/ambo/simulate/config.py` | config/model | file-I/O (YAML read) + validation | `src/ambo/common/config.py` | exact |
| `src/ambo/simulate/spend_patterns.py` | service (pure function) | transform (RNG draw → array) | `scripts/generate_season_windows.py` (calendar-derivation style) + `common/config.py` (RNG/channel-order convention referenced in `conftest.py`) | role-match |
| `src/ambo/simulate/dgp.py` | service (pure function + orchestrator) | transform / batch | `scripts/generate_season_windows.py` (pure deterministic derivation, docstring style) | role-match |
| `src/ambo/simulate/platform_bias.py` | service (pure function) | transform | `scripts/generate_season_windows.py` | role-match |
| `src/ambo/simulate/truth.py` | model + service | transform + file-I/O (byte-stable JSON write) | `scripts/generate_season_windows.py` (byte-stable CSV write, `main()`/`SEED_PATH` pattern) + `common/config.py` (pydantic `BaseModel`, `extra='forbid'`) | exact (write pattern) / role-match (schema) |
| `src/ambo/simulate/__main__.py` | CLI / imperative shell | request-response (argv → exit code) | `scripts/generate_season_windows.py`'s `main() -> int` + `if __name__ == "__main__": raise SystemExit(main())` | exact |
| `config/scenarios/{s_a,s_b,s_c}.yaml` | config (authored data) | file-I/O (static) | `config/settings.yaml` | exact |
| `tests/unit/test_scenario_config.py` | test | request-response (load → assert) | `tests/unit/test_config.py` | exact |
| `tests/unit/test_spend_patterns.py` | test | transform / property | `tests/unit/test_config.py` (fixture style) + `conftest.py`'s `seeded_rng` fixture | role-match |
| `tests/unit/test_dgp.py` | test | transform / property (`hypothesis`) | `tests/unit/test_config.py` (assertion style); no in-repo `hypothesis` analog yet — pattern taken from RESEARCH.md Code Examples | partial (new: property-based) |
| `tests/unit/test_platform_bias.py` | test | transform | `tests/unit/test_config.py` | exact |
| `tests/unit/test_truth.py` | test | file-I/O + schema | `tests/unit/test_config.py` (`ConfigError` match-style assertions) + `scripts/generate_season_windows.py`'s determinism-by-construction (for byte-stability test design) | role-match |
| `tests/unit/test_simulate_cli.py` | test | integration (subprocess/CLI, determinism) | `tests/unit/test_import_independence.py` (repo-wide AST/file-scan style) + `conftest.py`'s `tmp_repo`/`repo_root` fixtures | role-match |

## Pattern Assignments

### `src/ambo/simulate/config.py` (config/model, file-I/O + validation)

**Analog:** `src/ambo/common/config.py` (full file read, 172 lines)

**Module docstring pattern** (lines 1-15): every module opens with a docstring naming
the SPEC/EB/AD/MD-nnn IDs it implements, an explicit "Implements: ..." line, and a
statement of *which module owns which read* (single-home rule). Copy this shape for
`simulate/config.py`'s docstring, naming SIM-002/EB-040 and stating that
`simulate/config.py` is the only module that reads `config/scenarios/*.yaml` directly.

**Pydantic schema pattern** (lines 58-115):
```python
class PathsConfig(BaseModel):
    """One-line purpose statement."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    data_synthetic: Path
    ...


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    channels: tuple[str, ...]
    ...

    @field_validator("channels")
    @classmethod
    def _validate_channel_order(cls, value: tuple[str, ...]) -> tuple[str, ...]: ...
```
`ScenarioConfig` in `simulate/config.py` must follow the exact same shape: nested
`BaseModel`s with `model_config = ConfigDict(extra="forbid", frozen=True)`, a
`field_validator` for any ordering/domain invariant (e.g. channel spend-pattern keys
must match `SPEC_CHANNEL_ORDER`).

**`repo_root()`-anchored, cached loader pattern** (lines 45-55, 129-171):
```python
def repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ConfigError(...)


@functools.lru_cache(maxsize=1)
def load_settings() -> Settings:
    ...
    with settings_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    ...
    try:
        return Settings(**data)
    except ValidationError as exc:
        failing_keys = ", ".join(...)
        raise ConfigError(f"...: failing key path(s): {failing_keys}") from exc
```
`load_scenario(name)` should reuse `ambo.common.config.repo_root()` (imported, not
reimplemented — `simulate` may import `ambo.common`), use `yaml.safe_load`, and wrap
`ValidationError` in a typed error the same way. Decide whether to cache per-scenario
(likely yes, via `functools.lru_cache` keyed on scenario name) mirroring
`load_settings()`'s single-cached-object discipline.

**Error handling pattern:** every raised error is a subclass of `AmboError`
(`src/ambo/common/errors.py` lines 15-27), never a bare `ValueError`/`Exception`. Add a
new `SimulateError(AmboError)` (or similarly named) in a scenario/DGP error subclass
alongside `ConfigError`'s existing pattern, or reuse `ConfigError` for pure config-load
failures per its "raised by any module that loads scenario config" framing — planner
should decide which per `MODULE_CONTRACTS.md`'s existing error taxonomy, but the shape
(subclass `AmboError`, message never contains a private-drop path) is fixed.

---

### `src/ambo/simulate/spend_patterns.py`, `dgp.py`, `platform_bias.py` (service, pure function / transform)

**Analog:** `scripts/generate_season_windows.py` (full file read, 180 lines) for
docstring/determinism conventions; `tests/conftest.py`'s `seeded_rng` fixture (lines
29-32) for the RNG-injection convention these modules must honor at call sites.

**Module docstring pattern** (generate_season_windows.py lines 1-31): states the owning
SPEC section, cites `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` section
numbers for any disambiguated reading, states "Implements: REQ-...", and explicitly
calls out any deliberately-not-imported dependency and why (mirrors this phase's own
"simulate never imports model" boundary — restate that boundary in `dgp.py`'s
docstring explicitly, per A-1).

**Pure-function-with-explicit-seed pattern** (generate_season_windows.py has no RNG,
but the "no hidden state, explicit inputs only" discipline is identical): every
function in `spend_patterns.py`/`dgp.py`/`platform_bias.py` takes an explicit
`np.random.Generator` (never reads a module-level RNG) — this is the "Single Seeded
Generator, Documented Draw Order" pattern from RESEARCH.md Pattern 2, and the
`seeded_rng` conftest fixture:
```python
@pytest.fixture
def seeded_rng() -> np.random.Generator:
    return np.random.default_rng(_SEEDED_RNG_SEED)
```
Test files for these modules should take `seeded_rng` as a fixture argument rather than
constructing their own `default_rng()` inline, for consistency with the rest of the
suite.

**Deterministic-build-then-write pattern** (generate_season_windows.py lines 128-155,
`build_rows()`): separate the *pure computation* (`build_rows`) from *I/O*
(`main()`/file write) — this is exactly the Functional-Core/Imperative-Shell pattern
RESEARCH.md Pattern 1 mandates for `simulate/`. `spend_patterns.py::generate_spend()`,
`dgp.py::season_index()/adstock_recursive()/hill()/assemble_scenario()`, and
`platform_bias.py::platform_report()` are all "build_rows-shaped": pure, no I/O, called
by `__main__.py`.

**Season-window read pattern (AD-020 shared-config exception):** `dgp.py`'s
`season_index()` reads `dbt/seeds/season_windows.csv` (the file
`generate_season_windows.py` produces) via plain `csv`/`pandas` read — never recomputes
the advent/schulbeginn/jan-dip/spring/summer-lull logic in `generate_season_windows.py`
lines 66-125. Treat that file as a frozen, read-only input; do not re-import or call
anything from `scripts/generate_season_windows.py` (it is a one-off script, not a
package module, so there is nothing importable there anyway — confirms the "shared
config, not shared code" boundary literally).

---

### `src/ambo/simulate/truth.py` (model + service, transform + byte-stable file-I/O)

**Analog A (byte-stable write):** `scripts/generate_season_windows.py::main()` (lines
157-175):
```python
def main() -> int:
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows(YEAR_RANGE)
    with SEED_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return 0
```
The determinism discipline to copy: open with explicit `newline=""` and pin the line
terminator (`"\n"`) explicitly rather than relying solely on `.gitattributes` — the
project's own comment on this pattern (lines 160-167) states the writer itself must be
byte-stable because CI's diff-check runs before git's checkout filters. `truth.py`'s
`write_truth()` should apply the equivalent discipline for JSON: explicit `encoding="utf-8"`,
explicit newline handling, `json.dump(data, f, sort_keys=True, indent=2)` plus the
`%.10g` fixed-float formatter RESEARCH.md's Pattern 3 specifies (verify the exact
`json.dump` float-formatting hook mechanism during implementation, per RESEARCH.md
Assumption A3 — no existing in-repo JSON writer to copy verbatim, this is genuinely new).

**Analog B (pydantic schema + `extra='forbid'`):** `src/ambo/common/config.py`'s
`Settings`/`PathsConfig` pattern (see config.py section above) — `TruthFile` follows
the identical `BaseModel` + `ConfigDict(extra="forbid", frozen=True)` shape.

---

### `src/ambo/simulate/__main__.py` (CLI, request-response)

**Analog:** `scripts/generate_season_windows.py`'s `main() -> int` +
`if __name__ == "__main__": raise SystemExit(main())` (lines 157-179). Copy this exact
shape: a `main(argv: list[str] | None = None) -> int` function (extended to parse
`all|s_a|s_b|s_c` and dispatch), returning an int exit code, with the module-level
guard calling `raise SystemExit(main())`. Gate-runner (`validate_sim()`) should be a
separate function in the same module, also returning an int exit code, so
`make simulate && make validate-sim` maps directly onto two `SystemExit`-raising
entry points.

---

### `config/scenarios/{s_a,s_b,s_c}.yaml` (config, authored data)

**Analog:** `config/settings.yaml` (full file, 71 lines). Copy conventions:
- A top-of-file comment block explaining the file's authority ("this file is the
  authoritative source, not duplicated elsewhere" — mirrors `config/settings.yaml`
  lines 1-14's EB-040 framing, restated for SIM-002).
- Inline comments citing the exact SPEC-01 section for each block of values (mirrors
  `channels:` block's `# SPEC-02 section 5.2` comment, line 16).
- No secrets, no environment-specific values — everything here is spec-derived
  constants, read via `yaml.safe_load` only.

---

### `tests/unit/test_scenario_config.py`, `test_platform_bias.py`, `test_truth.py` (test, assertion-heavy)

**Analog:** `tests/unit/test_config.py` (full file, 162 lines).

**Fixture + cache-clearing pattern** (lines 48-53):
```python
@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    load_settings.cache_clear()
    yield
    load_settings.cache_clear()
```
If `simulate/config.py::load_scenario()` uses `functools.lru_cache`, `test_scenario_config.py`
needs the equivalent autouse fixture.

**Round-trip / spec-equality assertion pattern** (lines 61-77): load the raw YAML with
`yaml.safe_load` directly in the test and assert every parsed field matches, rather
than trusting the loader's own transformation — copy this "trust nothing, re-derive
independently in the test" style for `test_scenario_config.py`'s SPEC-01 §4
table-equality tests.

**Typed-error assertion pattern** (lines 110-139):
```python
with pytest.raises(ConfigError, match="totally_unexpected_key"):
    load_settings()
```
Use for `extra='forbid'` violation tests and for missing-scenario-file tests in
`test_scenario_config.py`/`test_truth.py`.

**Single-config-home guard pattern** (lines 142-162,
`test_sampler_keys_appear_nowhere_else_in_src_ambo`): an A-8 single-home test that
`grep`s the whole `src/ambo` tree for a config's field names outside its owning module.
Consider an analogous guard in `test_truth.py` for any `truth.json` schema fields that
must not be duplicated/recomputed elsewhere (e.g. asserting the response-curve formula
constants exist only in `truth.py`).

---

### `tests/unit/test_spend_patterns.py`, `test_dgp.py` (test, transform + property-based)

**Analog:** `tests/conftest.py`'s `seeded_rng` fixture (lines 29-32) + RESEARCH.md's
Code Examples section for the `hypothesis` skeleton (no in-repo `hypothesis` analog
exists yet — this is genuinely new to the project, gated behind the ADR/checkpoint
Pitfall 2 describes).

**Point-test pattern to copy verbatim** (RESEARCH.md Code Examples,
"Adstock closed-form and impulse tests"):
```python
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
Write the impulse test **before** trusting the closed-form test green (Pitfall 4 — the
impulse test is what catches a reversed-convolution bug the closed-form test can miss).

**Hypothesis property-test skeleton** (RESEARCH.md Code Examples,
"Hypothesis property test skeleton") — use only after the ADR + `checkpoint:human-verify`
task lands (see Shared Patterns below); strategies must pass
`allow_nan=False, allow_infinity=False` and domain-appropriate `min_value`/`max_value`
per Pitfall 5.

---

### `tests/unit/test_simulate_cli.py` (test, integration/CLI determinism)

**Analog:** `tests/unit/test_import_independence.py` (full file, 143 lines) for the
"repo-wide scan with a clear non-vacuous assertion" style, plus `conftest.py`'s
`repo_root`/`tmp_repo` fixtures (lines 22-27, 35-47) for regen-to-temp-dir comparisons.

**Non-vacuous-scan-guard pattern** (lines 55-64):
```python
assert scanned > 0, "No files found under ... -- the scan is broken, not vacuously passing."
```
Apply the same discipline to the SIM-070 byte-identity test: assert the two generated
directories actually contain the expected files before asserting byte-equality, so a
silently-empty regen can't pass by vacuous comparison.

**`tmp_repo`/`repo_root` fixture reuse** (conftest.py lines 22-27, 35-47): use
`repo_root` to locate `make simulate`'s real output location, and a `tmp_path`-based
temp directory (following the `tmp_repo` pattern's style, though a bare git repo is
likely unnecessary here — a plain `tmp_path` fixture suffices) to regenerate a second
copy for the byte-compare.

## Shared Patterns

### Pydantic `BaseModel` + `extra='forbid'` + `ConfigDict(frozen=True)`
**Source:** `src/ambo/common/config.py` lines 58-115
**Apply to:** `simulate/config.py::ScenarioConfig` (and its nested per-channel blocks),
`simulate/truth.py::TruthFile`. Every schema class in the phase must set
`model_config = ConfigDict(extra="forbid", frozen=True)` — no exceptions, this is a
project-wide EB-040 invariant, not a per-file choice.

### `yaml.safe_load` for all YAML reads
**Source:** `src/ambo/common/config.py` line 24, 153 (`import yaml`, `yaml.safe_load(handle)`)
**Apply to:** `simulate/config.py::load_scenario()`. Never `yaml.load()` unsafe, never
a third-party YAML alternative (PyYAML is the pinned, established library).

### Typed exception hierarchy (`AmboError` subclasses only)
**Source:** `src/ambo/common/errors.py` lines 15-27
**Apply to:** every raise site across all six `simulate/` modules. No bare
`ValueError`/`Exception` for expected failure conditions (A-7); `hill()`/
`adstock_recursive()` domain violations (negative input) should raise a typed error
per the module contract, following the same "subclass `AmboError`, redaction invariant
in the docstring" convention.

### `get_logger(__name__)` — the sole logger factory
**Source:** `src/ambo/common/logging.py` lines 109-137
**Apply to:** any `simulate/` module that logs (likely `__main__.py`'s CLI progress/
gate-result output). No module calls `logging.getLogger` directly, no `print` in
`src/` (per `logging.py`'s docstring, line 8, and RESEARCH.md's EB-070/A-anti-pattern
notes).

### Functional Core / Imperative Shell — pure math, I/O only in `__main__.py`
**Source:** `scripts/generate_season_windows.py`'s `build_rows()` (pure) vs. `main()`
(I/O) split, lines 128-175; RESEARCH.md Pattern 1.
**Apply to:** all of `spend_patterns.py`, `dgp.py`, `platform_bias.py`, and the pure
parts of `truth.py` (`compute_truth()`, the response-curve evaluator) — none of these
touch the filesystem; only `__main__.py` reads YAML/CSV and writes CSV/JSON.

### Single Seeded Generator, injected not global
**Source:** `tests/conftest.py`'s `seeded_rng` fixture (lines 29-32); RESEARCH.md
Pattern 2.
**Apply to:** every stochastic draw in `spend_patterns.py` and `dgp.py`'s noise-vector
step — always an explicit `np.random.Generator` parameter, seeded once per scenario
from `cfg.seed`, never `numpy.random.seed()`.

### Byte-stable, LF-only, `newline=""`-pinned file writes
**Source:** `scripts/generate_season_windows.py::main()` lines 157-175 (comment at
160-167 explaining *why* the writer itself must be byte-stable, not just
`.gitattributes`).
**Apply to:** `truth.py::write_truth()`'s JSON write and `dgp.py`/`__main__.py`'s CSV
writes for `media_weekly.csv`/`outcome_weekly.csv` — same discipline, JSON/CSV specific
formatting details differ but the "don't rely solely on `.gitattributes`, pin it in the
writer" principle is identical.

### AST-based cross-package import guards already exist and become load-bearing
**Source:** `tests/unit/test_import_independence.py` (full file) — currently
vacuously passing (both `simulate/` and `model/` are empty stubs).
**Apply to:** no new test file needed for this guard, but every new `simulate/*.py`
module must be written knowing this test will start actually scanning real content the
moment it lands — a stray `from ambo.model import ...` (even inside a function body,
which the AST walk still catches) will fail CI immediately.

## No Analog Found

None. Every file in this phase's scope has at least a role-match analog already
committed from Phase 1. The one partially-novel element is `hypothesis`-based property
tests in `test_dgp.py` (D-03) — no in-repo `hypothesis` usage exists yet, so its pattern
is taken from RESEARCH.md's Code Examples section (itself sourced from the well-known
`semaphore.io` property-testing tutorial pattern) rather than from a codebase analog.
This is expected and tracked, not a gap in this pattern search — RESEARCH.md's Pitfall 2
already requires an ADR + `checkpoint:human-verify` task before this code lands, which
the planner must sequence ahead of any task that imports `hypothesis`.

## Metadata

**Analog search scope:** `src/ambo/common/`, `scripts/`, `tests/unit/`, `tests/conftest.py`,
`config/settings.yaml` — the entirety of Phase 0/1's committed surface relevant to
`simulate/`'s import allowance (`ambo.common` only, per SIM-003).
**Files scanned:** 7 read in full (`common/config.py`, `common/errors.py`,
`common/logging.py`, `scripts/generate_season_windows.py`, `tests/conftest.py`,
`tests/unit/test_config.py`, `tests/unit/test_import_independence.py`) + 1 config file
(`config/settings.yaml`) + 2 directory listings (`tests/unit/*.py` glob,
`generate_season_windows.py` glob).
**Pattern extraction date:** 2026-08-05
