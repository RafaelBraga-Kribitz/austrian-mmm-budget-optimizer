"""ScenarioConfig model tree for SPEC-01's disclosed data-generating process.

The pydantic schema that makes SPEC-01 sections 3-6 mechanically checkable
(SIM-002: the scenario YAML is the authoritative parameter source; SIM-030: the
spend-season collinearity switch is expressed in data via this schema's fields,
never in code). EB-040's single-read rule applies here too.

Implements: REQ-q1-truth-recovery, REQ-grain-and-windows

This is the only module that reads `config/scenarios/*.yaml`; every later module in
`src/ambo/simulate/` reads simulate-layer parameters exclusively through
`load_scenario()`, never by re-parsing YAML itself. This module never imports
anything from `ambo.model` -- the simulator and the model share no code (SIM-003),
only the season-windows seed as config.
"""

from __future__ import annotations

import functools

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from ambo.common.config import load_settings, repo_root
from ambo.common.errors import SimulationError

# SPEC-01 section 4, verbatim and in order. These are `Settings.channels[:6]` --
# the six Layer P channels. `other` is a Layer R taxonomy slot (config/settings.yaml's
# seventh `channels` entry) with no SPEC-01 section 4 row, so it is rejected by a
# Layer P ScenarioConfig.
SPEC_CHANNEL_ORDER: tuple[str, ...] = (
    "search_brand",
    "search_generic",
    "meta",
    "display_video",
    "print_regional",
    "radio",
)

# SPEC-01 section 5, verbatim: the only three (id, weeks, seed) triples any scenario
# YAML may declare. Pinning this here (not just weeks-in-a-set) is what makes the
# grain and the seed both load-time-checkable, not just the grain alone.
_VALID_SCENARIO_IDENTITIES: frozenset[tuple[str, int, int]] = frozenset(
    {
        ("s_a", 156, 101),
        ("s_b", 104, 202),
        ("s_c", 78, 303),
    }
)


class TrueParams(BaseModel):
    """The four true media-effect parameters the model must recover (SPEC-01 section 4).

    Field names match `03_MODULES.md` section 2.1 verbatim -- `K` uppercase is
    intentional (the project's selected ruff rule set is E, F, I, UP, B; no
    pep8-naming), matching the closed-form notation `K_c` used throughout SPEC-01.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    lam: float
    K: float
    s: float
    beta: float

    @field_validator("lam")
    @classmethod
    def _lam_in_unit_interval(cls, value: float) -> float:
        # The closed form x/(1-lam) diverges at lam=1, so the interval is
        # half-open: 0.0 is a legitimate (no-decay) value, 1.0 never is.
        if not (0.0 <= value < 1.0):
            raise ValueError(f"lam must satisfy 0.0 <= lam < 1.0, got {value!r}")
        return value

    @field_validator("K")
    @classmethod
    def _K_is_positive(cls, value: float) -> float:
        if not value > 0.0:
            raise ValueError(f"K must be > 0, got {value!r}")
        return value

    @field_validator("s")
    @classmethod
    def _s_is_positive(cls, value: float) -> float:
        if not value > 0.0:
            raise ValueError(f"s must be > 0, got {value!r}")
        return value

    @field_validator("beta")
    @classmethod
    def _beta_is_non_negative(cls, value: float) -> float:
        if not value >= 0.0:
            raise ValueError(f"beta must be >= 0, got {value!r}")
        return value


class SpendPattern(BaseModel):
    """One channel's weekly spend-draw parameters (SPEC-01 section 3).

    `burst_length`/`burst_starts` and `pulse_every`/`pulse_multiplier` are each an
    all-or-nothing pair: an always-on channel (e.g. `search_brand`) declares both
    of a pair as `None`; a flighted channel (e.g. `print_regional`) declares both.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    mean: float
    sd: float
    floor_eur: int | None
    advent_factor: float
    spring_factor: float
    pulse_every: int | None
    pulse_multiplier: float | None
    burst_length: int | None
    burst_starts: dict[int, tuple[int, ...]] | None

    @field_validator("mean")
    @classmethod
    def _mean_is_positive(cls, value: float) -> float:
        if not value > 0.0:
            raise ValueError(f"mean must be > 0, got {value!r}")
        return value

    @field_validator("sd")
    @classmethod
    def _sd_is_non_negative(cls, value: float) -> float:
        if not value >= 0.0:
            raise ValueError(f"sd must be >= 0, got {value!r}")
        return value

    @field_validator("advent_factor")
    @classmethod
    def _advent_factor_is_non_negative(cls, value: float) -> float:
        if not value >= 0.0:
            raise ValueError(f"advent_factor must be >= 0, got {value!r}")
        return value

    @field_validator("spring_factor")
    @classmethod
    def _spring_factor_is_non_negative(cls, value: float) -> float:
        if not value >= 0.0:
            raise ValueError(f"spring_factor must be >= 0, got {value!r}")
        return value

    @field_validator("pulse_every")
    @classmethod
    def _pulse_every_is_positive_when_set(cls, value: int | None) -> int | None:
        if value is not None and not value > 0:
            raise ValueError(f"pulse_every must be > 0 when set, got {value!r}")
        return value

    @field_validator("pulse_multiplier")
    @classmethod
    def _pulse_multiplier_is_positive_when_set(cls, value: float | None) -> float | None:
        if value is not None and not value > 0.0:
            raise ValueError(f"pulse_multiplier must be > 0 when set, got {value!r}")
        return value

    @field_validator("burst_length")
    @classmethod
    def _burst_length_is_positive_when_set(cls, value: int | None) -> int | None:
        if value is not None and not value > 0:
            raise ValueError(f"burst_length must be > 0 when set, got {value!r}")
        return value

    @model_validator(mode="after")
    def _validate_paired_fields(self) -> SpendPattern:
        if (self.burst_length is None) != (self.burst_starts is None):
            raise ValueError(
                "burst_length and burst_starts must both be set or both be None, "
                f"got burst_length={self.burst_length!r}, burst_starts={self.burst_starts!r}"
            )
        if (self.pulse_every is None) != (self.pulse_multiplier is None):
            raise ValueError(
                "pulse_every and pulse_multiplier must both be set or both be None, "
                f"got pulse_every={self.pulse_every!r}, pulse_multiplier={self.pulse_multiplier!r}"
            )
        return self


class PlatformBiasParams(BaseModel):
    """A channel's known platform over-credit parameters (SPEC-01 section 6).

    An offline channel (`print_regional`, `radio`) has no platform reporting at
    all: `phi`, `theta`, `cpm` are all `None`. An online channel has all three.
    A half-populated block (e.g. `phi` set, `cpm` `None`) is never valid.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    phi: float | None
    theta: float | None
    cpm: float | None

    @model_validator(mode="after")
    def _validate_all_or_none(self) -> PlatformBiasParams:
        values = (self.phi, self.theta, self.cpm)
        populated = [value is not None for value in values]
        if any(populated) and not all(populated):
            raise ValueError(
                "phi, theta and cpm must be either all set or all None, got "
                f"phi={self.phi!r}, theta={self.theta!r}, cpm={self.cpm!r}"
            )
        return self


class ChannelConfig(BaseModel):
    """One channel's full parameter set: true effect, spend draw, platform bias."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    true_params: TrueParams
    spend: SpendPattern
    platform: PlatformBiasParams


class SeasonWeights(BaseModel):
    """The five multiplicative season-index weights (SPEC-01 section 2.1).

    No defaults: the YAML must state all five explicitly. 02-03's spec-equality
    test pins the SPEC-01 values (+0.55, +0.25, +0.15, -0.20, -0.10) against this
    schema; this module only authors the shape, never the values.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    advent: float
    schulbeginn: float
    spring: float
    jan_dip: float
    summer_lull: float


class ScenarioConfig(BaseModel):
    """The full parameter set for one SPEC-01 scenario (S-A, S-B or S-C).

    Constructed only via `load_scenario()` in normal use; direct construction is
    exercised by tests. Frozen and `extra='forbid'`, like every model in this
    module, so a typo in a scenario YAML is a load-time failure, never a silently
    ignored parameter.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    weeks: int
    seed: int
    start_iso_year: int
    start_iso_week: int
    end_iso_year: int
    end_iso_week: int
    collinearity: bool
    b0: float
    growth: float
    noise_share: float
    aov_base: float
    aov_advent_bonus: float
    promo_multiplier: float
    season_weights: SeasonWeights
    promo_weeks: dict[int, tuple[int, ...]]
    channels: dict[str, ChannelConfig]

    @field_validator("channels")
    @classmethod
    def _channels_match_spec_order(
        cls, value: dict[str, ChannelConfig]
    ) -> dict[str, ChannelConfig]:
        got = tuple(value)
        if got != SPEC_CHANNEL_ORDER:
            raise ValueError(
                f"channels must be exactly {SPEC_CHANNEL_ORDER!r} in that order, got {got!r}"
            )
        return value

    @field_validator("weeks")
    @classmethod
    def _weeks_is_a_valid_grain(cls, value: int) -> int:
        if value not in {156, 104, 78}:
            raise ValueError(f"weeks must be one of (156, 104, 78), got {value!r}")
        return value

    @model_validator(mode="after")
    def _validate_scenario_identity(self) -> ScenarioConfig:
        identity = (self.id, self.weeks, self.seed)
        if identity not in _VALID_SCENARIO_IDENTITIES:
            raise ValueError(
                "(id, weeks, seed) must be one of "
                f"{sorted(_VALID_SCENARIO_IDENTITIES)!r} (SPEC-01 section 5), got {identity!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_zero_effect_channel(self) -> ScenarioConfig:
        beta = self.channels["display_video"].true_params.beta
        is_s_c = self.id == "s_c"
        if is_s_c and beta != 0.0:
            raise ValueError(
                f"scenario s_c must have display_video.true_params.beta == 0.0, got {beta!r}"
            )
        if not is_s_c and beta == 0.0:
            raise ValueError(
                f"scenario {self.id!r} must have display_video.true_params.beta > 0, got 0.0"
            )
        return self

    @model_validator(mode="after")
    def _validate_schedules_inside_window(self) -> ScenarioConfig:
        """Every promo week and every burst span must fall inside
        `[start_iso_year/start_iso_week .. end_iso_year/end_iso_week]`. Window
        membership is checked on (iso_year, iso_week) tuples only -- this module
        performs no calendar arithmetic and never reads
        `dbt/seeds/season_windows.csv`; that read belongs to `dgp.py` (AD-020,
        single home)."""
        window_start = (self.start_iso_year, self.start_iso_week)
        window_end = (self.end_iso_year, self.end_iso_week)
        valid_years = set(range(self.start_iso_year, self.end_iso_year + 1))

        for year, weeks in self.promo_weeks.items():
            if year not in valid_years:
                raise ValueError(
                    f"promo_weeks year {year!r} is outside the declared window "
                    f"[{self.start_iso_year}..{self.end_iso_year}]"
                )
            for week in weeks:
                point = (year, week)
                if not (window_start <= point <= window_end):
                    raise ValueError(
                        f"promo_weeks entry {point!r} falls outside the declared window "
                        f"[{window_start}..{window_end}]"
                    )

        for channel_id, channel in self.channels.items():
            spend = channel.spend
            burst_length = spend.burst_length
            burst_starts = spend.burst_starts
            if burst_length is None or burst_starts is None:
                continue
            for year, starts in burst_starts.items():
                if year not in valid_years:
                    raise ValueError(
                        f"channel {channel_id!r} burst_starts year {year!r} is outside the "
                        f"declared window [{self.start_iso_year}..{self.end_iso_year}]"
                    )
                for start in starts:
                    for week in range(start, start + burst_length):
                        point = (year, week)
                        if not (window_start <= point <= window_end):
                            raise ValueError(
                                f"channel {channel_id!r} burst starting {point!r} (length "
                                f"{burst_length}) falls outside the declared window "
                                f"[{window_start}..{window_end}]"
                            )
        return self

    @model_validator(mode="after")
    def _validate_bursts_do_not_overlap(self) -> ScenarioConfig:
        """Two bursts in the same channel/year overlap when
        `next_start < prev_start + burst_length`. Exact adjacency
        (`next_start == prev_start + burst_length`) is **accepted** as two
        distinct bursts and is never merged into one longer burst -- SPEC-01
        section 3 and Guide section 1.1 forbid overlap and are silent on
        touching; this accept-on-adjacency reading is an interpretation recorded
        for `docs/BUILD_LOG.md` at M1 close."""
        for channel_id, channel in self.channels.items():
            spend = channel.spend
            burst_length = spend.burst_length
            burst_starts = spend.burst_starts
            if burst_length is None or burst_starts is None:
                continue
            for year, starts in burst_starts.items():
                ordered = sorted(starts)
                for prev_start, next_start in zip(ordered, ordered[1:], strict=False):
                    if next_start < prev_start + burst_length:
                        raise ValueError(
                            f"channel {channel_id!r} year {year!r} has overlapping bursts: "
                            f"start {prev_start!r} (length {burst_length}) overlaps start "
                            f"{next_start!r}"
                        )
        return self

    def covered_iso_years(self) -> tuple[int, ...]:
        """Every ISO year this scenario's window touches, start to end inclusive."""
        return tuple(range(self.start_iso_year, self.end_iso_year + 1))

    def covered_week_count(self, iso_year: int, weeks_in_iso_year: int) -> int:
        """The number of ISO weeks of `iso_year` this scenario's window covers.

        `weeks_in_iso_year` (52 or 53) is supplied by the caller so this method
        stays calendar-free (AD-020, single home: only `dgp.py` computes ISO week
        counts). A fully covered year returns `weeks_in_iso_year`; the first
        and/or last year of the window returns its covered span instead.
        """
        if iso_year < self.start_iso_year or iso_year > self.end_iso_year:
            raise SimulationError(
                f"covered_week_count(): iso_year {iso_year!r} is outside the declared "
                f"window [{self.start_iso_year}..{self.end_iso_year}]"
            )
        start_week = self.start_iso_week if iso_year == self.start_iso_year else 1
        end_week = self.end_iso_week if iso_year == self.end_iso_year else weeks_in_iso_year
        return end_week - start_week + 1


@functools.cache
def load_scenario(name: str) -> ScenarioConfig:
    """Load, validate and cache one scenario's `ScenarioConfig` (SIM-002).

    Resolves `name` against `load_settings().scenarios`, anchors the registered
    path through `repo_root()`, and raises `SimulationError` -- naming the known
    scenario ids on an unknown `name`, the expected absolute path on a missing
    file, and the failing key path(s) on a schema violation -- so a bare
    `KeyError`, `FileNotFoundError` or pydantic `ValidationError` never escapes
    this module boundary (09_ANTI_PATTERNS A-7).
    """
    settings = load_settings()
    if name not in settings.scenarios:
        known = ", ".join(sorted(settings.scenarios))
        raise SimulationError(
            f"load_scenario(): unknown scenario id {name!r}, known scenario id(s): {known}"
        )

    scenario_path = repo_root() / settings.scenarios[name].config
    if not scenario_path.is_file():
        raise SimulationError(
            f"load_scenario(): expected scenario file at {scenario_path}, not found"
        )

    with scenario_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise SimulationError(f"load_scenario(): {scenario_path} did not parse to a mapping")

    try:
        return ScenarioConfig(**raw)
    except ValidationError as exc:
        failing_keys = ", ".join(
            ".".join(str(part) for part in error["loc"]) for error in exc.errors()
        )
        raise SimulationError(
            f"load_scenario(): invalid scenario configuration in {scenario_path} -- "
            f"failing key path(s): {failing_keys}"
        ) from exc
