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

### src/ambo/common/db.py

**Purpose** The ONLY data doorway for `model`/`decide`/`report` code (AD-030). The
single module in `src/ambo/` that opens a duckdb connection or imports `duckdb`;
plan 03-02's mart-only guard test (`tests/unit/test_mart_only_access.py`) enforces
the surrounding half of that rule for `model/`, `decide/` and `report/`.

**Public API**
- `connect(read_only: bool = True) -> duckdb.DuckDBPyConnection` — opens the
  warehouse at `load_settings().paths.warehouse`. `read_only=True` by default; this
  is the access-control mechanism the phase depends on (the only write path to the
  warehouse is `dbt build` itself). `read_only=False` is reserved for tooling and
  must never be used by `model`, `decide` or `report` code.
- `read_mmm_input(layer: str) -> pd.DataFrame` — the single model input contract
  (AD-030), grain week x layer, columns and order cited from
  `dbt/models/marts/_fct_mmm_input__schema.yml` (never restated here, D-08),
  ordered by `week_start` ascending.
- `read_platform_reported(layer: str) -> pd.DataFrame` — grain week x layer x
  channel, columns cited from `dbt/models/marts/_fct_platform_reported__schema.yml`,
  ordered by `week_start` then `channel`. Platform-metric NULLs for offline
  channels are never coalesced to zero.
- `read_dim_layer() -> pd.DataFrame` — one row per layer, columns cited from
  `dbt/models/marts/_dim_layer__schema.yml`, ordered by `layer`.

**Invariants** `connect()` is read-only by default — the only write path to the
warehouse is `dbt build` itself (ASVS V4). This module is the only place in
`src/ambo/` that opens a duckdb connection or imports `duckdb`. Each mart's column
contract is cited **by path** — `dbt/models/marts/_fct_mmm_input__schema.yml`,
`_dim_layer__schema.yml`, `_fct_platform_reported__schema.yml` — and derived at
runtime by the private `_contract_columns()` helper; the column list is never
restated as a literal here or in this document (D-08). Every postcondition
violation on a call is collected and raised as a single `DataContractError`
(D-10), never one violation per run — Phase 5's VR-310 debug ladder is what
actually reads that message.

**Failure modes** `DataContractError`: a missing warehouse file (message names the
`make transform` command); an unknown `layer` argument (message lists the valid
layers read from `dim_layer`); a mart named in `_contract_columns()` that is not
declared in any schema yml under `dbt/models/marts/`; any violated frame
postcondition (empty result, column set/order mismatch, non-ascending or
non-gapless `week_start`, NaN in a spend column, non-positive `revenue`, NaN in a
grain column).

**Testing** `tests/unit/test_db.py` — the round trip against the committed
simulator CSVs (all three layers, within 1e-6), shape and column-order pinning,
the offline-null preservation on `fct_platform_reported`, `dim_layer`'s shape, the
read-only write-rejection proof (and that the warehouse is unmodified afterward),
the unknown-layer message, the missing-warehouse message, and the
collect-all-raise-once proof (a frame violating two postconditions simultaneously
raises one message naming both).

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
- `class DataContractError(AmboError)` — raised by `ambo.common.db` (the only data doorway for
  model/decide/report code, AD-030) for a missing warehouse file, an unknown layer argument, a
  mart-schema mismatch, or a violated frame postcondition.

**Invariants** Exception messages never contain private-drop content or file-system paths
under `AMBO_PRIVATE_DROP` (redaction is the logging filter's job for log records; exceptions
raised from `ambo.intake` carry counts, never values, by construction). Subclasses are added
per module as that module lands, each getting its own entry in this document.

**Failure modes** None — this module raises nothing itself; it only defines the exception
hierarchy other modules raise into. `DataContractError` is raised by `ambo.common.db` for: a
missing warehouse file (directing the caller to run `make transform`), an unknown layer
argument, a mart-schema mismatch against the declared column contract, and a violated frame
postcondition.

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
- `class SimulationResult` — frozen dataclass: `cfg`, `weeks`, `spend` (wide, week x channel,
  int €), `components` (every intermediate array kept for audit — `trend`, `season`,
  `promo_mult`, `promo_flag`, `base`, `adstock_<c>`/`m_<c>` per channel, `eps`,
  `revenue_pre_clip`, `revenue`), `media` (SIM-004 long frame, spend columns populated, the three
  platform columns all-null placeholders plan 02-07's `platform_report` fills in), `outcome`
  (SIM-004 frame). `__post_init__` runs the SIM-071 decomposition audit and raises
  `SimulationError` — naming the worst week and its deviation — if it fails, so a
  `SimulationResult` that violates the decomposition invariant cannot be constructed.
- `assemble_scenario(cfg: ScenarioConfig, rng: np.random.Generator) -> SimulationResult` — the
  only orchestrator in this module: `week_index` -> `baseline_demand` -> `generate_spend`
  (the generator's first six draw calls) -> per-channel adstock/Hill in `SPEC_CHANNEL_ORDER` (a
  plain loop, never vectorized across channels, A-14) -> one `rng.normal(0.0, sigma, size=T)`
  noise draw strictly after `generate_spend` on the same generator (SPEC-01 §2.3) -> the ≥0
  revenue clip -> `orders` via `round_half_up` -> the two SIM-004 frames. `generate_spend` is
  imported inside the function body, not at module level, because `spend_patterns.py` imports
  `round_half_up` from this module — a top-level cross-import would cycle (A-15).
- `decomposition_audit(result: SimulationResult) -> float` — SIM-071: the maximum absolute
  deviation of `base + Σ_c m_c + eps` from the stored `revenue_pre_clip`, re-summed from
  `result.components`'s own stored arrays. Passes when `<= 1e-6`.
- `plausibility_audit(result: SimulationResult) -> dict[str, float]` — SIM-072:
  `min_revenue_pre_clip`, `noise_variance_share` (`var(eps) / var(revenue_pre_clip)`), and one
  `media_share_<iso_year>` entry per covered ISO year (media contribution over that year's total
  revenue). Passes when `min_revenue_pre_clip >= 0`, `0.02 <= noise_variance_share <= 0.10`, and
  every `media_share_<iso_year>` is in `[0.15, 0.45]`.
- `peak_week_audit(result: SimulationResult) -> dict[int, tuple[int, bool]]` — SIM-073: per
  covered ISO year, `(peak_week_number, carries_advent_flag)` for that year's maximum-revenue
  week. A year is audited only if its Advent window lies inside the covered span (detected as "at
  least one `advent_flag == 1` row exists for that year"); an unaudited year is still present in
  the mapping under the documented sentinel `(-1, True)` so a caller can see it was skipped, not
  silently omitted. Passes when every *audited* year's boolean is `True`.

**Invariants** The week spine is gapless, strictly ascending, every `week_start` an ISO Monday,
every consecutive pair exactly 7 days apart, for all three scenarios. No advent, schulbeginn,
jan_dip, spring or summer-lull rule is reimplemented anywhere in this module — `week_index`
reads `SEED_PATH` and nothing else classifies a week. `season_index`'s five weights are read
signed from `SeasonWeights` and added with no sign flip in code (`jan_dip`/`summer_lull` are
negative in the YAML). `adstock_recursive` never depends on a future `x` value (causality);
`lam == 1.0` is rejected explicitly because `x / (1 - lam)` diverges there. `hill`'s output lies
in `[0, 1]` and is monotonically non-decreasing in `a` for every in-domain `(K, s)`. This module
is never imported by, and never imports, `ambo.model` (SIM-003).
`assemble_scenario`'s revenue-noise draw is one `rng.normal` call, strictly after
`generate_spend`'s six channel draws, on the same generator (SIM-070/SIM-001 determinism: two
runs from generators freshly seeded with `cfg.seed` produce elementwise-equal frames). A
`SimulationResult`'s `components` re-sum to `revenue_pre_clip` within 1e-6 as a **constructor
precondition** (SIM-071), not an after-the-fact report. `outcome` carries exactly `cfg.weeks`
rows and `media` exactly `6 * cfg.weeks` rows; `media` is sorted by `week_start` ascending then
`SPEC_CHANNEL_ORDER` position with `(week_start, channel)` unique; `outcome` is sorted by
`week_start` ascending with `week_start` unique. Both frames carry SIM-004's exact column names
and order.

**Failure modes** Every raise site is `SimulationError`: a window `(iso_year, iso_week)` key
absent from `SEED_PATH` (names the missing key); a duplicate `(iso_year, iso_week)` key in the
seed (names the duplicate); a non-Monday, non-strictly-increasing, or non-7-day-gap week
spine; `adstock_recursive` given a non-1-D, non-finite, or negative `x`, or `lam` outside `[0,
1)`; `hill` given a non-finite or negative `a`, or a non-positive `K`/`s`; `SimulationResult()`
given `components` that do not re-sum to `revenue_pre_clip` within 1e-6 (names the worst week
and its absolute deviation).

**Testing** `tests/unit/test_dgp.py` — SIM-073 seasonality point tests, SIM-074 adstock/Hill
point tests (impulse test written and run before the closed-form limit test, per the project's
own trap-T-2 discipline), D-03's five bounded `hypothesis` property tests, and (plan 02-06)
`assemble_scenario`/audit tests covering SIM-071/072/073, frame shape and column-order pinning,
the gapless week spine, media row ordering (the taxonomy-not-alphabetical assertion), the AOV
orders rule, the promo-flag/YAML match, the zero-effect channel, and same-seed determinism.

---

### src/ambo/simulate/platform_bias.py

**Purpose** SIM-060's simulated platform-reporting over-credit and BP-D-02's impressions/
conversions, completing `media_weekly.csv`'s three previously-null columns (T-106). SIM-061:
this makes "platform ROAS vs true ROAS" a known quantity in Layer P that Phase 8's DC-702
attribution-gap gate must later recover.

**Public API**
- `platform_report(result: SimulationResult) -> pd.DataFrame` — `03_MODULES.md` §2.4's
  contract exactly. Returns a frame with `6 * cfg.weeks` rows and SIM-004's six columns
  (`week_start, channel, spend_eur, impressions, platform_conversions, platform_revenue_eur`)
  in order, row order identical to the input `result.media`.

**Invariants** Pure — every value is derived from the handed `SimulationResult`; no I/O; never
imports `ambo.model` (SIM-003). `share_{c,t} = spend_{c,t} / total_spend_t` is computed with a
guarded expression so a zero-total-spend week yields exactly `0.0` for every channel's share,
never `NaN` or infinity. `print_regional` and `radio` (`platform.phi is None`) carry NULL in
all three platform columns for every row — offline channels have no platform reporting at all.
`impressions`/`platform_conversions` are nullable `Int64`, `platform_revenue_eur` is nullable
`Float64`, so NULL is a true missing value that survives to an empty CSV field rather than `0`
or `nan`. `phi`, `theta` and `cpm` are read from `result.cfg.channels[c].platform` — this
module contains no such literal, so SPEC-01 §6's table keeps exactly one home (the scenario
YAML), the same single-home rule BP-G-02 already guards at load time.

**Failure modes** `SimulationError` if `result.media`'s row count is not `6 * cfg.weeks`, or
its column set is not exactly SIM-004's six columns — this module is a completion step and
must not silently reshape its input.

**Testing** `tests/unit/test_platform_bias.py` — a hand-computed identity to 1e-9 (literal
arithmetic in the test, not a second call to the module), offline-NULL and online-non-null
coverage across all three scenarios, the CPM/AOV impressions/conversions rules, the
zero-total-spend-week no-NaN case, a config-not-code monkeypatch proof, SIM-061's over-credit
ordering (`display_video > meta > search_generic > search_brand`) on S-A/S-B, and row-order
preservation.

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

### src/ambo/simulate/truth.py

**Purpose** `truth.json`'s schema, the closed-form true-response-curve evaluator, and
byte-stable emission (SPEC-01 §4/§6/§8, SIM-060, SIM-070, SIM-075, Guide §1.5, BP-D-02/
BP-D-16, T-107). This is the single home of the closed-form `beta·Hill` curve formula (A-8)
and of the `truth.json` serialisation format. `response_curve_at` and `marginal_roas_at`
reuse `dgp.hill` so the truth curve and the generated per-week contributions cannot diverge.

**Public API**
- `response_curve_at(params: TrueParams, x_grid: np.ndarray) -> np.ndarray` — the true
  response curve at steady-state adstock (`a = x/(1-lam)`, contribution `beta * hill(a, K,
  s)`), evaluated at a **caller-supplied grid** (SPEC-01 §8's grid note, resolving
  INGEST-CONFLICTS WARNING 4): this phase calls it once with the 21-point diagnostic grid
  over 0…2× max weekly spend; Phase 3/8's `exports/response_curves.csv` calls the same
  function again with MD-082's 21-point 0…1.5× observed grid — no interpolation, no second
  home for the formula. `response_curve_at(params, [0.0]) == [0.0]` exactly; identically
  `0.0` when `beta == 0.0`. Raises `SimulationError` on a non-1-D, non-finite or negative
  grid.
- `marginal_roas_at(params: TrueParams, x_mean: float) -> float` — Guide §1.5's analytic
  derivative `beta·s·K^s·a^{s-1}/(a^s+K^s)^2 · 1/(1-lam)` at `a = x_mean/(1-lam)`.
  Truth-side only: uses SPEC-01's raw-recursion steady state, never the model's normalized
  one (BP-D-16). Returns exactly `0.0` when `beta == 0.0`; at `a == 0.0` returns `0.0` for
  `s >= 1.0` and raises `SimulationError` for `s < 1.0` (unbounded derivative at the origin).
- `class ChannelTruth(BaseModel)` — one channel's disclosed truth: the §4 parameters (`lam`,
  `K`, `s`, `beta`), `half_life_weeks`, spend/contribution aggregates, `true_avg_roas`,
  `true_marginal_roas_at_mean_spend`, the 21-point `response_curve_spend_eur`/
  `response_curve_contribution_eur` arrays, and the §6 platform quantities (`platform_phi`,
  `platform_theta`, `platform_cpm`, `platform_roas`), all `None` for offline channels.
- `class TruthFile(BaseModel)` — scenario metadata, the §2.1/§2.3 scalars (`b0`, `growth`,
  `noise_share`, `aov_base`, `aov_advent_bonus`, `promo_multiplier`, `season_weights`),
  window aggregates (`total_revenue_eur`, `total_media_contribution_eur`,
  `media_share_of_revenue`), `response_curve_grid_max_multiple` (always `2.0`), and
  `channels: tuple[ChannelTruth, ...]` in `SPEC_CHANNEL_ORDER`.
- `compute_truth(result: SimulationResult, media: pd.DataFrame) -> TruthFile` — pure;
  aggregates `result` and the platform-completed `media` frame (from
  `platform_bias.platform_report`) into a `TruthFile`. Raises `SimulationError` naming any
  channel whose total spend over the window is `0.0` — a `0/0` average ROAS never reaches a
  committed artifact.
- `write_truth(t: TruthFile, path: Path) -> None` — byte-stable (SIM-070): `sort_keys=True`,
  2-space indent, every float pre-normalised through a fixed `%.10g` format, one trailing
  newline, LF endings pinned in the writer (`newline="\n"`, not `.gitattributes`). Atomic
  (EB-050): writes `<path>.tmp-<pid>` then `os.replace`s onto `path`, removing the temp file
  on any exception.

**Invariants** Both pydantic models are `extra='forbid'` and frozen. `channels` is always in
`SPEC_CHANNEL_ORDER`. The diagnostic response-curve grid is 21 points over 0…2× max weekly
spend and is never the comparison grid (SPEC-01 §8: `1.3× optimizer bound < 1.5× reporting
horizon < 2.0× truth diagnostic`); the curve evaluator itself takes a caller-supplied grid,
so no reconciliation rule is needed between the 1.3×/1.5×/2.0× horizons. Offline channels
(`print_regional`, `radio`) carry `None` in all four platform fields, never a fabricated
zero. `compute_truth`'s `contribution_share` values sum to `media_share_of_revenue` exactly,
since both divide by the same `total_revenue_eur`. This module imports nothing from
`ambo.model` (SIM-003).

**Failure modes** `SimulationError`: `response_curve_at` given a non-1-D, non-finite or
negative grid; `marginal_roas_at` given a non-finite or negative `x_mean`, or an unbounded
derivative at `a == 0.0` with `s < 1.0`; `compute_truth` given a channel whose total spend
over the window is `0.0`.

**Testing** `tests/unit/test_truth.py` — SIM-075 schema completeness and parameter equality
against `load_scenario` for all three scenarios, frozen/`extra='forbid'` rejection,
`true_avg_roas` re-derivation, contribution-share-sums-to-media-share, marginal-ROAS-vs-
finite-difference agreement, response-curve monotonicity and the S-C zero-effect exact-zero
spot check, the caller-supplied-grid property Phase 3/8 depends on, offline-null platform
fields, the zero-total-spend `SimulationError`, `write_truth` byte-stability/sorted-keys/
float-precision/no-temp-file guarantees, and a single-home grep guard for the curve formula.

---

### src/ambo/simulate/__main__.py

**Purpose** The simulator CLI and the SIM-070…075 + BP-G-02 gate runner (T-108). The
only module in `simulate/` that performs I/O (Functional-Core / Imperative-Shell) — every
other module in this package stays pure and independently testable.

**Public API**
- `main(argv: list[str] | None = None) -> int` — CLI grammar `python -m ambo.simulate
  {all|s_a|s_b|s_c|validate} [--outdir PATH]`. Generates the requested scenario(s) (`all`
  in the fixed order `s_a, s_b, s_c`) into `<outdir>/<scenario>/`, or delegates to
  `validate_sim(outdir)` for `validate`. Returns 0 on success, 1 on a `SimulationError`;
  an unrecognised target is rejected by `argparse` itself (exit 2, usage message naming
  the five valid choices) before any output directory is created. `--outdir` defaults to
  `repo_root() / "data" / "synthetic"`.
- `validate_sim(outdir: Path) -> int` — the SIM-070…075 + BP-G-02 gate runner. Logs a
  fixed-width `GATE | STATUS | EVIDENCE` table (six PASS/FAIL rows plus a `DELEGATED`
  BP-G-02 row naming its real check, `tests/unit/test_scenario_config.py`'s
  `spec_parameter_table`/`rule_level`-selected tests) and returns 0 if and only if every
  SIM-0xx row is `PASS`. `make validate-sim` composes this function's exit code with the
  delegated selector's own, so the target as a whole cannot go green without both.

**Invariants** Sole I/O module in `simulate/`. One fresh
`np.random.default_rng(cfg.seed)` per scenario, never reused across scenarios
(SIM-001/SIM-070). Both CSV writers (`_write_media_csv`, `_write_outcome_csv`) pin SIM-004's
exact column names and order, UTF-8 encoding, an explicit LF line terminator
(`newline=""` plus `lineterminator="\n"`, not `.gitattributes`), a fixed `%.6f` float
format, `na_rep=""` so an offline channel's NULL renders as a genuinely empty field
distinguishable from `0`, and `index=False`; integer columns are cast to the nullable
`Int64` dtype so they render with no decimal point. Every write (both CSVs and
`truth.json`, the latter via `truth.write_truth`) is atomic: a `.tmp-<pid>` sibling then
`os.replace`, removed on any exception. `validate_sim`'s SIM-070 regeneration and every
non-vacuous existence check assert all nine expected files exist and are non-empty in
both trees **before** comparing, so an empty or partial regeneration cannot pass
vacuously. `validate_sim` performs no remediation on a red gate — it logs the realized
value against the expected bound and returns 1; widening a bound is never done here
(ROADMAP Phase 2 rollback rule). `validate_sim` imports nothing from the test framework
or `tests/` — SIM-074's closed-form checks call `dgp.adstock_recursive`/`dgp.hill`
directly, in-process.

**Failure modes** `main` returns 1 (message logged) on a `SimulationError` raised
anywhere in the per-scenario pipeline (`load_scenario`, `assemble_scenario`,
`compute_truth`). `validate_sim` never raises for an ordinary gate failure — a failing
row is reported as `FAIL` with its evidence, and the function returns 1; an
unreadable/invalid `truth.json` is caught and reported as a SIM-075 failure, not
propagated.

**Testing** `tests/unit/test_simulate_cli.py` — SIM-070 byte-determinism (a two-run,
non-vacuous nine-file comparison), all-nine-artifacts creation, the SIM-004 header
strings read from written bytes (not an in-memory frame), offline-channel empty-field
rendering, no-CR-bytes, the ISO-date/gapless-spine check, media row ordering
(taxonomy, not alphabetical), single-scenario/unknown-target CLI behavior, and
`validate_sim`'s pass/fail on a fresh generation, a corrupted `truth.json`, and a
missing artifact.

---

### scripts/export_marts.py

**Purpose** The registry-driven, byte-stable export writer (T-205, D-01..D-05).
Writes `exports/*.csv` from the marts, reading exclusively through
`ambo.common.db` (AD-030) — this script is Python orchestration over the frozen
mart contract, never a second SQL layer. `exports/mmm_input_weekly.csv` is the
first (and today, only) registry entry; Phase 8 and Phase 9 add the remaining
SPEC-03 §5 files by adding a registry entry, never a second script.

**Public API**
- `class ExportSpec` — one registry entry: `reader: Callable[[], pd.DataFrame]`,
  `columns: Callable[[pd.DataFrame], list[str]]` (the ordered column list,
  derived from the reader's own frame — never restated as a literal, D-08's
  discipline applied here), `dtype_casts: dict[str, str]` (`"date"` →
  `YYYY-MM-DD` string, `"Int64"` → nullable pandas integer), `sort_keys:
  list[str]` (the row-sort order and the frame's grain key).
- `EXPORT_REGISTRY: dict[str, ExportSpec]` — keyed by output filename (D-03); one
  entry today, `mmm_input_weekly.csv`, reading every layer `read_dim_layer()`
  reports via `read_mmm_input(layer)` (no hard-coded layer list), sorted by
  `layer` then `week_start`.
- `validate_no_duplicate_grain_keys(frame, sort_keys) -> None` — raises
  `DataContractError` naming the duplicated key(s) if `frame` has a duplicate on
  `sort_keys`; never silently deduplicates (AD-050).
- `build_export_frame(spec: ExportSpec) -> pd.DataFrame` — read, column-order,
  validate, sort — everything short of dtype casts and the write.
- `write_export(name: str, outdir: Path) -> Path` — the full pipeline for one
  registry entry, ending in the atomic write; returns the written path.
- `main(argv: list[str] | None = None) -> int` — CLI: `python
  scripts/export_marts.py [NAME ...]`. No arguments writes every registry entry;
  one or more names writes only those. Resolves the output directory through
  `load_settings().paths.exports`.

**Invariants** Every float value is written at explicit fixed six-decimal
precision (`%.6f`), never pandas' default repr (D-04). The write is atomic and
LF-only — a `.tmp-<pid>` sibling written with `newline=""` and an explicit
`lineterminator="\n"`, then `os.replace`d onto the destination, with the temp
file removed on any exception — mirroring
`ambo.simulate.__main__._atomic_write_csv` verbatim. Row order is explicit and
stable (sorted by `sort_keys`, currently `layer` then `week_start`), never left
to DuckDB's scan order, so two runs on an unchanged warehouse are byte-identical.
Importing this module performs no file writes and no other side effect. The
mart's column list and order are never restated as a literal here — cited by
path at `dbt/models/marts/_fct_mmm_input__schema.yml`, the same repoint D-08
requires of `db.py`.

**Failure modes** `DataContractError`: a duplicated grain key
(`(week_start, layer)`) in a frame about to be exported, or an unrecognized
`dtype_casts` cast keyword. `SystemExit(2)` (via `argparse`'s own error path) on
an unknown registry entry name passed on the command line.

**Testing** `tests/unit/test_export_marts.py` — the registry shape (a non-empty
dict, every value carrying a reader, column source, dtype casts and sort keys);
the committed `exports/mmm_input_weekly.csv` matches the mart contract exactly
(header, 338 data rows, `YYYY-MM-DD` dates, the three Layer P values, sorted by
layer then `week_start`); a duplicated grain key fails rather than
deduplicating; every float value is fixed six decimals; the file contains no
carriage-return byte; and two consecutive writes from the same warehouse, plus
the committed file, are byte-identical.

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
