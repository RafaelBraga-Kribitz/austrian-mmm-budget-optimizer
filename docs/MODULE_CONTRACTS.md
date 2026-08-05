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
- `class SimulationError(AmboError)` — the `src/ambo/simulate/` package's error root; raised
  by every module in that package for a missing/invalid scenario YAML, an out-of-domain math
  input, a missing season-window row, and a failed decomposition audit.

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

### src/ambo/simulate/config.py

**Purpose** The pydantic `ScenarioConfig` model tree that makes SPEC-01 sections 3–6
mechanically checkable (SIM-002: the scenario YAML is the authoritative parameter source).
The only module that reads `config/scenarios/*.yaml`; every later `src/ambo/simulate/` module
reads simulate-layer parameters exclusively through `load_scenario()`.

**Public API**
- `SPEC_CHANNEL_ORDER: tuple[str, ...]` — the six SPEC-01 §4 channels, `Settings.channels[:6]`.
- `class TrueParams(BaseModel)` — `lam: float`, `K: float`, `s: float`, `beta: float`.
- `class SpendPattern(BaseModel)` — `mean`, `sd`, `floor_eur`, `advent_factor`,
  `spring_factor`, `pulse_every`, `pulse_multiplier`, `burst_length`, `burst_starts`.
- `class PlatformBiasParams(BaseModel)` — `phi: float | None`, `theta: float | None`,
  `cpm: float | None`.
- `class ChannelConfig(BaseModel)` — `true_params: TrueParams`, `spend: SpendPattern`,
  `platform: PlatformBiasParams`.
- `class SeasonWeights(BaseModel)` — `advent`, `schulbeginn`, `spring`, `jan_dip`,
  `summer_lull`, all `float`, no defaults.
- `class ScenarioConfig(BaseModel)` — `id: str`, `weeks: int`, `seed: int`,
  `start_iso_year/start_iso_week/end_iso_year/end_iso_week: int`, `collinearity: bool`,
  `b0/growth/noise_share/aov_base/aov_advent_bonus/promo_multiplier: float`,
  `season_weights: SeasonWeights`, `promo_weeks: dict[int, tuple[int, ...]]`,
  `channels: dict[str, ChannelConfig]`; plus `covered_iso_years() -> tuple[int, ...]` and
  `covered_week_count(iso_year: int, weeks_in_iso_year: int) -> int`.
- `load_scenario(name: str) -> ScenarioConfig` — cached (`functools.lru_cache`); the module's
  sole entry point for every caller outside this file.

**Invariants** `extra='forbid'` and `frozen=True` on every model above. `channels` is exactly
`SPEC_CHANNEL_ORDER` in that order. The `(id, weeks, seed)` triple is pinned to one of the
three SPEC-01 §5 rows. `channels["display_video"].true_params.beta == 0.0` if and only if
`id == "s_c"`. Every `promo_weeks` and `burst_starts` entry falls inside
`[start_iso_year/start_iso_week .. end_iso_year/end_iso_week]`. Bursts in the same channel/year
never overlap; exact adjacency (`next_start == prev_start + burst_length`) is accepted as two
distinct bursts. This module performs no calendar arithmetic and never reads
`dbt/seeds/season_windows.csv` — that read belongs to `dgp.py` (AD-020, single home).

**Failure modes** Every raise site in this module is `SimulationError`: unknown scenario id,
missing scenario YAML (names the expected absolute path), and any schema violation (names the
failing key path(s), converted at the module boundary from pydantic's `ValidationError`).
`ValueError` remains correct *inside* a `field_validator`/`model_validator` — that is the
pydantic idiom pydantic itself collects into a `ValidationError` — and is not a violation of
this rule.

**Testing** `tests/unit/test_scenario_config.py` — one positive/negative pair per validator
listed above, a single-home guard for `SPEC_CHANNEL_ORDER` against `Settings.channels`, a
frozen-model assertion, and `load_scenario()` boundary-conversion tests for both an unknown
scenario id and a missing file.

### src/ambo/simulate/dgp.py

**Purpose** The disclosed data-generating process's mathematical core (SPEC-01 §2.1/§2.2/§2.3):
the calendar spine, the seasonal index, baseline demand, the project-wide whole-unit rounding
convention, and the simulator's own geometric adstock and Hill saturation. Nothing in this
module is imported from or shared with `ambo.model` — the simulator implements its own
adstock/Hill so the Phase 5 recovery result is evidence rather than a tautology (SIM-003, A-1).

**Public API**
- `SEED_PATH: Path` — `repo_root() / "dbt" / "seeds" / "season_windows.csv"`, the committed
  calendar seed this module reads (AD-020).
- `round_half_up(values: np.ndarray) -> np.ndarray` — half-away-from-zero rounding to `int64`;
  the single project-wide home for this convention (A-8).
- `week_index(cfg: ScenarioConfig) -> pd.DataFrame` — the gapless, ISO-Monday weekly spine for
  `cfg`'s window: `iso_year`, `iso_week`, `week_start`, `t` (1-indexed), and the five window-flag
  columns, read from `SEED_PATH` and never recomputed.
- `season_index(weeks: pd.DataFrame, season_weights: SeasonWeights) -> np.ndarray` — the
  multiplicative season index (SPEC-01 §2.1's five signed weights, summed with no sign flip).
  Promotes `03_MODULES.md` §2.3's `season_index(weeks: pd.DatetimeIndex, windows: pd.DataFrame)`
  signature to a `(week-index frame, SeasonWeights)` pair — the five weights are SIM-002 YAML
  values and must not be hard-coded in code (recorded for `docs/BUILD_LOG.md`).
- `baseline_demand(cfg: ScenarioConfig, weeks: pd.DataFrame) -> pd.DataFrame` — `trend`,
  `season`, `promo_mult`, `promo_flag`, and `base` (`b0 * trend * season * promo_mult`), every
  component returned as its own column (re-summed by plan 02-06's SIM-071 decomposition audit).
- `adstock_recursive(x: np.ndarray, lam: float) -> np.ndarray` — geometric adstock, `a_t = x_t +
  lam * a_{t-1}`, `a_0 = 0`; pure, O(T), causal (`a_t` depends only on `x_{<=t}`); a plain
  forward loop, never `cumsum`/`convolve`/`lfilter` (A-14; the shapes trap T-2 hides in).
- `hill(a: np.ndarray, K: float, s: float) -> np.ndarray` — Hill saturation, `a^s / (a^s +
  K^s)`; `hill(K, K, s) == 0.5` exactly for every `s > 0`; `hill(0, K, s) == 0.0` exactly.

**Invariants** The week spine is gapless, strictly ascending, every `week_start` an ISO Monday,
every consecutive pair exactly 7 days apart, for all three scenarios. No advent, schulbeginn,
jan_dip, spring or summer-lull rule is reimplemented anywhere in this module — `week_index`
reads `SEED_PATH` and nothing else classifies a week. `season_index`'s five weights are read
signed from `SeasonWeights` and added with no sign flip in code (`jan_dip`/`summer_lull` are
negative in the YAML). `adstock_recursive` never depends on a future `x` value (causality);
`lam == 1.0` is rejected explicitly because `x / (1 - lam)` diverges there. `hill`'s output lies
in `[0, 1]` and is monotonically non-decreasing in `a` for every in-domain `(K, s)`. This module
is never imported by, and never imports, `ambo.model` (SIM-003).

**Failure modes** Every raise site is `SimulationError`: a window `(iso_year, iso_week)` key
absent from `SEED_PATH` (names the missing key); a duplicate `(iso_year, iso_week)` key in the
seed (names the duplicate); a non-Monday, non-strictly-increasing, or non-7-day-gap week
spine; `adstock_recursive` given a non-1-D, non-finite, or negative `x`, or `lam` outside `[0,
1)`; `hill` given a non-finite or negative `a`, or a non-positive `K`/`s`.

**Testing** `tests/unit/test_dgp.py` — SIM-073 seasonality point tests, SIM-074 adstock/Hill
point tests (impulse test written and run before the closed-form limit test, per the project's
own trap-T-2 discipline), and D-03's five bounded `hypothesis` property tests.

---

### src/ambo/simulate/spend_patterns.py

**Purpose** The six per-channel weekly spend series of SPEC-01 §3: always-on Normals with
seasonal planning multipliers and floors, the `meta` six-week ×1.8 pulse, and flighted
`print_regional`/`radio` bursts driven by the schedules `config/scenarios/*.yaml` freezes.
Promotes `03_MODULES.md` §2.2's two-argument `generate_spend(cfg, rng)` signature to three
arguments, `generate_spend(cfg, rng, weeks)` — SPEC-01 §3's seasonal multipliers need the
Advent/spring flags, AD-020 forbids recomputing those windows here, and this module performs no
I/O, so the week-index frame is injected by the caller instead of read here.

**Public API**
- `generate_spend(cfg: ScenarioConfig, rng: np.random.Generator, weeks: pd.DataFrame) ->
  pd.DataFrame` — the six spend series, indexed by `weeks`'s `t` column, columns exactly
  `SPEC_CHANNEL_ORDER` in that order, dtype `int64`, every value `>= 0` (`search_brand`
  additionally never below its declared floor).

**Invariants** `rng` is an explicit parameter, never a module-level or global RNG (A-5); it is
consumed as exactly six `rng.normal` calls, one per channel, in `SPEC_CHANNEL_ORDER` — a fixed,
documented draw order (SIM-001/SIM-070) that `assemble_scenario` (plan 02-06) continues
immediately afterward with the revenue noise draw. Per channel, the four SPEC-01 §3 steps run in
exactly this order (Guide §1.3): seasonal/pulse multipliers apply to the *mean*, then the draw,
then the flighting mask (flighted channels only), then the floor clamp (applied only to
mask-kept weeks, so a masked-zero week is never lifted to the floor), then whole-euro rounding
via `dgp.round_half_up` (A-8, single home). A flighted channel is non-zero exactly on its
authored burst weeks and exactly zero elsewhere, with no stochastic slack. This module contains
no scenario-name branch — SIM-030's collinearity switch enters only as the `advent_factor`/
`spring_factor` values a scenario's YAML carries.

**Failure modes** `SimulationError` if `weeks`'s row count does not equal `cfg.weeks`, or if any
channel's burst span in `cfg` falls outside the `(iso_year, iso_week)` set `weeks` carries — a
defence-in-depth restatement of `ScenarioConfig`'s own load-time schedule-in-window validator
(`03_MODULES.md` §2.2).

**Testing** `tests/unit/test_spend_patterns.py` — SIM-030/SIM-031 statistics against
independently re-derived design values, determinism, draw-order pinning, and Guide §1.3's
step-order proven to bite via a deliberate swap-and-revert.

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
