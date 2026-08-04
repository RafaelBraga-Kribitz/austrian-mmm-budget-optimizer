---
phase: 01-repository-foundation
plan: 04
subsystem: infra
tags: [pydantic, yaml, logging, config, pytest, mypy]

# Dependency graph
requires:
  - phase: 01-02
    provides: "pyproject.toml (pymc/mypy-strict/pytest config), uv.lock, importable src/ambo/ subpackage tree"
  - phase: 01-03
    provides: "docs/MODULE_CONTRACTS.md with pre-written entries for config.py, errors.py, logging.py (contract-first, D-03)"
provides:
  - "config/settings.yaml — the single configuration home (EB-040): SPEC-02 5.2 channel taxonomy in order, adstock_length=8, six repo-relative paths, MD-050 sampler block verbatim, parameter-free s_a/s_b/s_c scenario registry"
  - "src/ambo/common/errors.py — AmboError root exception, ConfigError subclass"
  - "src/ambo/common/config.py — repo_root(), PathsConfig, SamplerConfig, ScenarioConfig, Settings (pydantic BaseModel, extra=forbid, frozen), load_settings() cached via functools.lru_cache"
  - "src/ambo/common/logging.py — LOG_FORMAT, PrivatePathFilter, get_logger() — the sole logger-construction pattern, redacts AMBO_PRIVATE_DROP from every emitted record"
  - "tests/unit/test_config.py + tests/unit/test_logging.py — first real tests in the repo; uv run python -m pytest -q now exits 0 (16 tests) instead of exit 5 (zero collected)"
affects: [01-05, 01-06, 01-07, 01-08, 01-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-config-home enforced as a test, not a manual grep: tests/unit/test_config.py reads SamplerConfig.model_fields.keys() and asserts none of those names appears (word-boundary match) in any src/ambo/*.py file except config.py itself — proven red-then-green by planting a key into simulate/__init__.py and reverting"
    - "get_logger(name) attaches PrivatePathFilter + a LOG_FORMAT StreamHandler exactly once per logger name (idempotency guard via 'is there already a PrivatePathFilter on this logger'), sets propagate=False so a logger never double-emits via an ancestor logger's own handler"
    - "PrivatePathFilter resolves AMBO_PRIVATE_DROP exclusively through load_settings().private_drop, never os.environ directly — one resolution path project-wide (EB-041)"
    - "load_settings() anchors every config/settings.yaml paths.* entry against repo_root() before pydantic validation, so Settings.paths is always absolute regardless of caller cwd"
    - "mypy override added for yaml.* (PyYAML ships no py.typed marker) rather than adding the types-PyYAML dev dependency — avoids triggering the project's no-new-dependency-without-ADR rule for a pinned, already-approved runtime dependency"

key-files:
  created:
    - config/settings.yaml
    - src/ambo/common/errors.py
    - src/ambo/common/config.py
    - src/ambo/common/logging.py
    - tests/unit/test_config.py
    - tests/unit/test_logging.py
  modified:
    - docs/MODULE_CONTRACTS.md
    - pyproject.toml
    - .gitignore

key-decisions:
  - "Settings is pydantic.BaseModel, not BaseSettings, as MODULE_CONTRACTS.md originally specified — BaseSettings lives in the separate pydantic-settings distribution, absent from SPEC-08 3's dependency table, and EB-030 makes adding a distribution an ADR event. BaseModel plus load_settings()'s own functools.lru_cache already satisfies EB-040's pydantic-validated single-read requirement. Corrected the MODULE_CONTRACTS.md entry to match (Rule 1 — the contract's stated base class did not match what the plan's own Task 2 instructed)."
  - "MODULE_CONTRACTS.md's SamplerConfig field was named 'seed'; corrected to 'random_seed' to match MD-050 (SPEC-04 5) and D-25 verbatim, both of which name the key random_seed. Field name now matches the YAML key exactly, no aliasing needed."
  - "Added a mypy override for yaml.* rather than the types-PyYAML dev dependency: PyYAML is already a pinned SPEC-08 3 runtime dependency, so extending the existing ignore_missing_imports pattern (already used for pymc/arviz/pytensor/etc.) needs no new package and triggers no ADR."

requirements-completed: [REQ-dl8-quality, REQ-scope-out]

coverage:
  - id: D1
    description: "config/settings.yaml authored whole: five top-level blocks (channels, adstock_length, paths, sampler, scenarios), SPEC-02 5.2 channel order, adstock_length=8, MD-050 sampler block verbatim, parameter-free scenario registry"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: unit
        ref: "task-1 automated verify: uv run python -c \"import yaml; d=yaml.safe_load(open('config/settings.yaml')); assert sorted(d)==['adstock_length','channels','paths','sampler','scenarios']; assert d['channels']==[...]; assert d['adstock_length']==8; assert len(d['sampler'])==6; assert sorted(d['scenarios'])==['s_a','s_b','s_c']\""
        status: pass
    human_judgment: false
  - id: D2
    description: "Typed settings (repo_root, PathsConfig, SamplerConfig, ScenarioConfig, Settings, load_settings) with unknown-key rejection, channel-order validation, single-read caching, and the single-config-home invariant as a test"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: unit
        ref: "tests/unit/test_config.py (9 tests: round-trip, channel order, adstock length, cache identity, private_drop set/unset, unknown-key ConfigError, missing-file ConfigError, sampler-key sweep)"
        status: pass
      - kind: other
        ref: "uv run mypy — Success: no issues found in 11 source files"
        status: pass
    human_judgment: false
  - id: D3
    description: "Logger factory with private-path redaction: PrivatePathFilter attached by get_logger() to every logger it returns, redacts in both record.msg and record.args, no-op when AMBO_PRIVATE_DROP unset, fixed LOG_FORMAT, idempotent handler attachment"
    requirement: "REQ-scope-out"
    verification:
      - kind: unit
        ref: "tests/unit/test_logging.py (7 tests: redaction in message, redaction in args, no-op when unset, fixed format applied, single-handler idempotency, getLogger() confined to common/logging.py, no print() in src/ambo/)"
        status: pass
    human_judgment: false
  - id: D4
    description: "src/ambo/common satisfies mypy --strict and docs/MODULE_CONTRACTS.md's config.py entry names the base class the implementation actually uses"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "uv run mypy (Success, 11 source files); uv run pytest tests/unit -q (16 passed); uv run python -m pytest -q exits 0"
        status: pass
    human_judgment: false

duration: ~12min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 4: Settings, Errors and Logging (config/settings.yaml, common/config.py, common/logging.py) Summary

**The single configuration home (config/settings.yaml) plus the two src/ambo/common modules every later module imports: pydantic-validated cached settings with unknown-key rejection, and a logger factory whose PrivatePathFilter is the project's first leak-surface control — proven by the repository's first 16 real tests.**

## Performance

- **Duration:** ~12 min (context reading through final commit, 20:53–21:05 UTC+2)
- **Started:** 2026-08-04T18:53:12Z (approx., prior plan's close)
- **Completed:** 2026-08-04T19:05:05Z
- **Tasks:** 3 (all `type="auto"`, no checkpoints)
- **Files modified:** 9 (1 in Task 1, 5 in Task 2 including two deviation-driven edits, 2 in Task 3, plus 3 lint-format touch-ups in a follow-up commit)

## Accomplishments
- `config/settings.yaml` authored whole per D-25: the seven-channel SPEC-02 5.2 taxonomy in exact order, `adstock_length: 8`, six repository-relative paths (warehouse as the DuckDB *file* path, not the directory), the complete six-key MD-050 sampler block verbatim, and a parameter-free `s_a`/`s_b`/`s_c` scenario registry pointing at Phase 2's future scenario YAMLs
- `src/ambo/common/errors.py` and `config.py`: `AmboError`/`ConfigError` exception hierarchy; `Settings` (pydantic `BaseModel`, `extra="forbid"`, `frozen=True`) with `PathsConfig`/`SamplerConfig`/`ScenarioConfig`; `load_settings()` cached via `functools.lru_cache`, anchors every path against `repo_root()`, raises `ConfigError` naming the failing key path on invalid YAML or a missing file
- `src/ambo/common/logging.py`: `get_logger(name)` — the sole sanctioned logger-construction pattern — attaches `PrivatePathFilter` and a fixed-format `StreamHandler` exactly once per logger name; the filter redacts the resolved `AMBO_PRIVATE_DROP` path to `<PRIVATE_DROP>` in both `record.msg` and `record.args`, case-insensitively, with both path-separator forms normalized, and is a pass-through no-op when the variable is unset
- `tests/unit/test_config.py` (9 tests) and `tests/unit/test_logging.py` (7 tests): the repository's first real tests. `uv run python -m pytest -q` now exits 0 (16 passed) instead of exit 5 (zero collected). The single-config-home test was proven red-then-green by planting a sampler key into `simulate/__init__.py`, observing failure, then reverting
- `docs/MODULE_CONTRACTS.md`'s `config.py` entry corrected to match the implementation: `BaseModel` (not `BaseSettings`) and `random_seed` (not `seed`)

## Task Commits

Each task was committed atomically:

1. **Task 1: Author config/settings.yaml whole** - `8948414` (feat)
2. **Task 2: Implement typed settings with unknown-key rejection and its test suite** - `c21e6c6` (feat)
3. **Task 3: Implement the logger factory with private-path redaction and its test suite** - `ab3d4b7` (feat)
4. **Follow-up: ruff format** - `37c1ca1` (style) — line-wrapping only, caught by `ruff check`/`ruff format --check` after Task 3, before overall verification; no logic change

**Plan metadata:** committed separately after this summary is written.

## Files Created/Modified
- `config/settings.yaml` - The five-block single configuration home (EB-040)
- `src/ambo/common/errors.py` - `AmboError`, `ConfigError`
- `src/ambo/common/config.py` - `repo_root()`, `PathsConfig`, `SamplerConfig`, `ScenarioConfig`, `Settings`, `load_settings()`
- `src/ambo/common/logging.py` - `LOG_FORMAT`, `PrivatePathFilter`, `get_logger()`
- `tests/unit/test_config.py` - 9 tests covering round-trip, ordering, caching, both private-drop env states, both ConfigError paths, single-config-home sweep
- `tests/unit/test_logging.py` - 7 tests covering redaction (message + args), no-op-when-unset, fixed format, handler idempotency, and the two grep-shaped invariants as tests
- `docs/MODULE_CONTRACTS.md` - `config.py` entry: `BaseModel` (not `BaseSettings`), `random_seed` (not `seed`), `ScenarioConfig` and `Settings` field lists brought in line with the implementation
- `pyproject.toml` - mypy override added for `yaml.*`
- `.gitignore` - `.coverage` added (pytest-cov artifact generated by this plan's own test runs)

## Decisions Made
- **`Settings` is `BaseModel`, not `BaseSettings`** — see key-decisions above; this was the plan's own Task 2 instruction, and the MODULE_CONTRACTS.md entry (written ahead of code in 01-03 per D-03) had to be corrected to match rather than the implementation bending to an outdated contract.
- **`SamplerConfig`'s `seed` field renamed to `random_seed`** in both the implementation and the MODULE_CONTRACTS.md entry, to match MD-050 and D-25 verbatim (both name the sampler key `random_seed`, never `seed`).
- **mypy `yaml.*` override instead of the `types-PyYAML` dependency** — see key-decisions above; avoids an ADR event for a stub-only package covering an already-pinned runtime dependency.
- **`.coverage` added to `.gitignore`** — a pytest-cov artifact this plan's own test runs generate; harmless but was previously untracked-and-uncovered by any ignore rule.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `MODULE_CONTRACTS.md`'s `config.py` entry named the wrong pydantic base class and sampler field name**
- **Found during:** Task 2, before writing `config.py`
- **Issue:** The pre-written contract (from 01-03, D-03 grow-as-you-go) said `class Settings(BaseSettings)` and `seed: int (=42)`. Task 2's own instructions require `BaseModel` (with the documented rationale about `pydantic-settings` not being a SPEC-08 3 dependency) and the plan's `sampler` verbatim block names the key `random_seed`, matching MD-050.
- **Fix:** Implemented `Settings(BaseModel)` and `SamplerConfig.random_seed` as specified by the plan's own text; updated the `MODULE_CONTRACTS.md` entry to match (base class, field name, and `ScenarioConfig`/`Settings` field lists brought current), per the plan's explicit "update the entry so the base class matches the implementation" instruction.
- **Files modified:** `src/ambo/common/config.py`, `docs/MODULE_CONTRACTS.md`
- **Verification:** `uv run mypy` clean; `tests/unit/test_config.py::test_yaml_round_trip_reproduces_every_value` asserts `settings.sampler.random_seed == raw["sampler"]["random_seed"]`
- **Committed in:** `c21e6c6` (Task 2 commit)

**2. [Rule 3 - Blocking] `mypy --strict` failed on the `yaml` import — no stubs installed**
- **Found during:** Task 2, running the plan's own `uv run mypy` verify step
- **Issue:** PyYAML ships no `py.typed` marker and the project has no stub package for it; `mypy --strict` reported `Library stubs not installed for "yaml" [import-untyped]`, blocking the task's acceptance criteria.
- **Fix:** Added a `[[tool.mypy.overrides]]` block for `yaml.*` with `ignore_missing_imports = true`, following the exact pattern already established for `pymc`/`arviz`/`pytensor`/`pymc_marketing`/`duckdb`/`holidays`. Did not add the `types-PyYAML` package, since PROJECT.md's constraint set requires an ADR for any new dependency — extending an existing config mechanism for an already-pinned dependency avoids that entirely.
- **Files modified:** `pyproject.toml`
- **Verification:** `uv run mypy` — Success: no issues found in 10 (then 11) source files
- **Committed in:** `c21e6c6` (Task 2 commit)

**3. [Rule 1 - Bug] `.coverage` was an untracked, ungitignored pytest-cov artifact**
- **Found during:** Task 2, first `git status --short` after running the test suite
- **Issue:** The project's coverage config (`--cov=src/ambo` in `pyproject.toml`) writes a `.coverage` file on every test run; `.gitignore`'s environment/tooling block covers `.pytest_cache/` but not `.coverage`, so every future test run would leave an untracked file.
- **Fix:** Added `.coverage` to `.gitignore`'s environment/tooling section.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` no longer lists `.coverage` after a test run
- **Committed in:** `c21e6c6` (Task 2 commit)

**4. [Rule 1 - Bug] `ruff format --check` flagged three files after Task 3**
- **Found during:** Post-Task-3 quality sweep (`uv run ruff check` / `uv run ruff format --check`, not explicitly required by the plan's `<verify>` blocks but consistent with EB-001's toolchain and the project's own CI job 1)
- **Issue:** `typing.Iterator` used instead of `collections.abc.Iterator` (ruff `UP035`) in both test files, and four multi-line strings in `config.py`/`test_config.py`/`test_logging.py` exceeded the 100-column reflow ruff prefers as single lines.
- **Fix:** Switched both `Iterator` imports to `collections.abc`; ran `uv run ruff format` on the five plan-04 files.
- **Files modified:** `src/ambo/common/config.py`, `tests/unit/test_config.py`, `tests/unit/test_logging.py`
- **Verification:** `uv run ruff check .` — All checks passed; `uv run ruff format --check .` — 58 files already formatted; `uv run pytest tests/unit -q` — 16 passed; `uv run mypy` — Success
- **Committed in:** `37c1ca1` (separate follow-up commit, after Task 3's own commit)

---

**Total deviations:** 4 auto-fixed (2 Rule 1 — contract-drift bug and gitignore gap; 1 Rule 1 — lint/format bug; 1 Rule 3 — blocking mypy stub gap)
**Impact on plan:** No scope creep. All four were required for the plan's own stated acceptance criteria (mypy clean, MODULE_CONTRACTS.md matching the implementation, a clean `git status`) to be satisfiable at all.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `src/ambo/common/{config,errors,logging}.py` are the first three real modules in the project and the dependency root every later `src/ambo/` module imports (per `docs/MODULE_CONTRACTS.md`'s dependency-directions table: `common → (nothing in ambo)`)
- `config/settings.yaml` is the single configuration home Phase 2 onward reads via `load_settings()`; the scenario registry's `config:` paths (`config/scenarios/s_a.yaml` etc.) are ready for Phase 2 to author against
- `uv run python -m pytest -q` exits 0 for the first time in this project's history — the coverage gate (currently non-blocking per D-15) has real modules in its `--cov=src/ambo` scope to measure (95% on the two shipped modules)
- The single-config-home test pattern (`SamplerConfig.model_fields.keys()` swept against `src/ambo/*.py`) and the get_logger()-is-the-only-construction-pattern / no-`print()` tests are reusable templates for plan 01-07's broader guard-test suite (`test_repo_layout.py`, `test_forbidden_deps.py`, `test_import_independence.py`, `test_no_requests.py`)
- `docs/MODULE_CONTRACTS.md` now has three complete, implementation-accurate entries (`config.py`, `errors.py`, `logging.py`) — the contract-first same-PR rule (D-03) is now demonstrated in both directions: contract written ahead of code (01-03), then corrected to match what the code actually needed (this plan)

---
*Phase: 01-repository-foundation*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 6 created artifacts found on disk (config/settings.yaml, src/ambo/common/errors.py,
src/ambo/common/config.py, src/ambo/common/logging.py, tests/unit/test_config.py,
tests/unit/test_logging.py); all 4 commits verified present in git history
(8948414, c21e6c6, ab3d4b7, 37c1ca1).
