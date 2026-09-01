# MODULE CONTRACTS

**This document is the contract of record for every module that exists in `src/ambo/`.**
`docs/EXECUTION_BLUEPRINT/03_MODULES.md` is superseded as of Phase 1: it is frozen, never edited
again, and remains the design input for contracts not yet written here. Where a contract below
was promoted from `03_MODULES.md`, its content is authoritative here, not there.

**Contract-first rule (SPEC-08 §2).** A new module inside a listed `src/ambo/` package is
permitted and expected. It requires an entry in this document, merged in the *same pull request*
that adds the module. `tests/unit/test_repo_layout.py` enforces the one-entry-per-module
invariant mechanically (D-23) — a module lacking an entry here fails CI, so this document
cannot silently fall behind the tree.

**Entry format.** Each module gets a level-3 heading that is exactly its repository-relative
path, followed by five labeled sections in this order:

- `Purpose` — one or two sentences: what the module is for.
- `Public API` — one bullet per exported symbol, with its signature.
- `Invariants` — what must always hold, checked or by convention.
- `Failure modes` — what raises, and under what condition.
- `Testing` — where the module's tests live and what they prove.

Entries are ordered by import path (`src/ambo/common/` before `src/ambo/intake/`, alphabetically
within a package) purely for readability. The layout guard (`test_repo_layout.py`) compares the
*set* of modules against the *set* of entries, never the order, so two orderings of the same
entries are equally valid and reordering this file is never itself a contract change.

---

### src/ambo/common/config.py

**Purpose** Typed, validated, single-read configuration (EB-040). The only module that reads
`config/settings.yaml` and `AMBO_PRIVATE_DROP` directly; every other module reads settings via
`load_settings()`.

**Public API**
- `class PathsConfig(BaseModel)` — `data_synthetic: Path`, `data_real_anon: Path`,
  `posteriors: Path`, `warehouse: Path`, `exports: Path`, `reports: Path`.
- `class SamplerConfig(BaseModel)` — `chains: int` (=4), `tune: int` (=1000), `draws: int`
  (=1000), `target_accept: float` (=0.9), `random_seed: int` (=42), `init: str`
  (=`"jitter+adapt_diag"`).
- `class ScenarioConfig(BaseModel)` — `label: str`, `config: Path` (repository-relative path to
  the scenario YAML). Phase 1 declares the schema only; full simulate-layer parameters live in
  the scenario YAML itself once `src/ambo/simulate/` ships, never duplicated here.
- `class Settings(BaseModel)` — fields: `channels: tuple[str, ...]` (7, SPEC-02 §5.2 taxonomy
  order), `adstock_length: int` (=8), `paths: PathsConfig`, `sampler: SamplerConfig`,
  `scenarios: dict[str, ScenarioConfig]`, `private_drop: Path | None` (from
  `AMBO_PRIVATE_DROP`). `BaseModel`, not `BaseSettings`: `BaseSettings` moved to the separate
  `pydantic-settings` distribution in pydantic v2, which is not in the SPEC-08 §3 dependency
  table, and EB-030 makes adding it an ADR event; `BaseModel` plus `load_settings()`'s own
  `functools.lru_cache` already satisfies EB-040's pydantic-validated single-read requirement.
  Invariants: `extra='forbid'`; `channels` exactly SPEC-02 §5.2's seven entries in order; lists
  become tuples after validation (immutable).
- `load_settings() -> Settings` — cached; idempotent; raises `ConfigError` naming the failing
  key path on invalid YAML.
- `repo_root() -> Path` — resolves the repository root independent of the caller's working
  directory; every path in `Settings.paths` is anchored through it.

**Invariants** Config is read exactly once per process (caching); no module other than
`config.py` reads YAML or `os.environ` for settings (intake mapping-rule files are the one
documented exception, per D-01's module-contract preamble in `03_MODULES.md`).

**Failure modes** Missing or malformed `config/settings.yaml` → `ConfigError` naming the
expected path and, where the failure is a validation error, the failing field. Unset
`AMBO_PRIVATE_DROP` → `private_drop` is `None`; `config.py` itself never raises on this (only
`ambo.intake` raises when it needs the drop and finds none, per AG-020).

**Testing** `tests/unit/test_config.py` — round-trip load, `extra='forbid'` rejection of an
unknown key, both `AMBO_PRIVATE_DROP` set and unset, and `ConfigError` raised and asserted for
a malformed YAML fixture.

### src/ambo/common/errors.py

**Purpose** The typed exception root for the project and its Phase 1 subclass. Every module
that raises a domain error subclasses `AmboError`, never raises a bare `Exception` or a
built-in exception type for expected failure conditions (09 §A-7).

**Public API**
- `class AmboError(Exception)` — the project's root exception. All typed exceptions elsewhere in
  `src/ambo/` (`DataContractError`, `GateFailure`, `IntakeError`, `LeakDetected`, `FitError`, …)
  subclass this as those modules land; Phase 1 ships the root and its first subclass only.
- `class ConfigError(AmboError)` — raised by `ambo.common.config` on invalid or missing
  configuration.

**Invariants** Exception messages never contain private-drop content or file-system paths
under `AMBO_PRIVATE_DROP` (redaction is the logging filter's job for log records; exceptions
raised from `ambo.intake` carry counts, never values, by construction). Subclasses are added
per module as that module lands, each getting its own entry in this document.

**Failure modes** None — this module raises nothing itself; it only defines the exception
hierarchy other modules raise into.

**Testing** Raised and asserted from `tests/unit/test_config.py` (`ConfigError` path); no
standalone test file, since the module has no behavior beyond class definitions.

### src/ambo/common/logging.py

**Purpose** The sole logger factory for the project (EB-041). No module calls
`logging.getLogger` directly or uses `print` in `src/`.

**Public API**
- `get_logger(name: str) -> logging.Logger` — returns a configured logger with
  `PrivatePathFilter` installed; `name` is conventionally `__name__` of the caller.
- `class PrivatePathFilter(logging.Filter)` — redacts the resolved `AMBO_PRIVATE_DROP` path to
  the literal string `<PRIVATE_DROP>` in every emitted record.
- `LOG_FORMAT` — the fixed format string:
  `"%(asctime)s %(levelname)s %(name)s %(message)s"`.
- `AMBO_LOG_LEVEL` — the environment variable name whose value (default `INFO`) sets the root
  logger's level.

**Invariants** `PrivatePathFilter` is installed on every logger `get_logger()` returns, with no
opt-out; the format string is fixed project-wide (no per-module overrides); level defaults to
`INFO` when `AMBO_LOG_LEVEL` is unset.

**Failure modes** None — a missing or invalid `AMBO_LOG_LEVEL` value falls back to `INFO`
rather than raising.

**Testing** `tests/unit/test_logging.py` — redaction proven against a fake private-drop path
embedded in a log message, and a no-op case proving the filter is inert when
`AMBO_PRIVATE_DROP` is unset.

---

## Dependency directions

Reproduced from `03_MODULES.md` §10 (the full package-level table), since two of these edges
become guard tests in plan 01-07 and this is the tracked place a reviewer can read them without
opening the gitignored blueprint.

```
simulate  →  (nothing in ambo except common)
intake    →  common
model     →  common
validate  →  common, model (fit/posterior_io/transforms), truth.json files
decide    →  common, model.posterior_io/transforms (read-only)
report    →  common, exports/SSOT side-files, model.posterior_io (read-only)
common    →  (nothing in ambo)
```

**Forbidden edges** (guard-tested by `tests/unit/test_forbidden_deps.py` and
`tests/unit/test_import_independence.py`, plan 01-07):

1. `simulate` ↔ `model`, either direction (SIM-003, W-2 firewall) — neither package may import
   the other; they share no transform code, only the season-windows seed as config.
2. `pymc_marketing` imported anywhere outside `ambo/validate/crosscheck.py` (MD-003).
3. `requests` imported anywhere in `src/ambo/` (EB-070 — zero network).
4. `pm.sample()` (or equivalent PyMC sampling entry point) called anywhere outside
   `ambo/model/fit.py`.
