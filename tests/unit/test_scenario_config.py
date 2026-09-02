"""Structural validation tests for `ambo.simulate.config` (T-101).

Implements: SIM-002, BP-G-02, REQ-grain-and-windows

Every negative test builds from `_valid_scenario_dict()` (or its s_b/s_c-shaped
siblings) and deviates in exactly one field, so a failure isolates exactly one
validator. This file asserts on shape only -- no SPEC-01 section 4 parameter
value is pinned here; that spec-table-equality test lands in plan 02-03 once the
scenario YAMLs exist.
"""

from __future__ import annotations

import csv
import math
import re
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ambo.common.config import load_settings, repo_root
from ambo.common.errors import SimulationError
from ambo.simulate.config import SPEC_CHANNEL_ORDER, ScenarioConfig, load_scenario


@pytest.fixture(autouse=True)
def _clear_scenario_cache() -> Iterator[None]:
    """Every test starts and ends with a cold `load_scenario` cache, mirroring
    `test_config.py`'s `_clear_settings_cache`."""
    load_scenario.cache_clear()
    yield
    load_scenario.cache_clear()


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge `patch` onto a shallow-per-level copy of `base`. Only
    dict values recurse; everything else (including tuples) is replaced
    outright. This is what lets every negative test override exactly one nested
    field (e.g. `channels.display_video.true_params.beta`) without repeating the
    whole payload."""
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _true_params(lam: float, k: float, s: float, beta: float) -> dict[str, float]:
    return {"lam": lam, "K": k, "s": s, "beta": beta}


def _always_on_spend(
    mean: float,
    sd: float,
    *,
    floor_eur: int | None = None,
    advent_factor: float = 0.0,
    spring_factor: float = 0.0,
    pulse_every: int | None = None,
    pulse_multiplier: float | None = None,
) -> dict[str, object]:
    return {
        "mean": mean,
        "sd": sd,
        "floor_eur": floor_eur,
        "advent_factor": advent_factor,
        "spring_factor": spring_factor,
        "pulse_every": pulse_every,
        "pulse_multiplier": pulse_multiplier,
        "burst_length": None,
        "burst_starts": None,
    }


def _flighted_spend(
    mean: float, sd: float, *, burst_length: int, burst_starts: dict[int, tuple[int, ...]]
) -> dict[str, object]:
    return {
        "mean": mean,
        "sd": sd,
        "floor_eur": None,
        "advent_factor": 0.0,
        "spring_factor": 0.0,
        "pulse_every": None,
        "pulse_multiplier": None,
        "burst_length": burst_length,
        "burst_starts": burst_starts,
    }


def _online_platform(phi: float, theta: float, cpm: float) -> dict[str, float]:
    return {"phi": phi, "theta": theta, "cpm": cpm}


def _offline_platform() -> dict[str, None]:
    return {"phi": None, "theta": None, "cpm": None}


def _base_channels(
    *, burst_year: int = 2021, display_video_beta: float = 6000.0
) -> dict[str, dict[str, object]]:
    """A fresh (never shared, never mutated-in-place) SPEC-01 section 4-shaped
    channel dict, in `SPEC_CHANNEL_ORDER`. `burst_year` anchors print/radio
    bursts to whichever ISO year the caller's window covers, and
    `display_video_beta` switches the zero-effect channel on/off, so the three
    scenario builders below never need to deep-merge a *replacement* year key
    onto a *different* base year key (which `_deep_merge` cannot express, since
    it only adds/overrides dict keys and never deletes one)."""
    return {
        "search_brand": {
            "true_params": _true_params(0.10, 800.0, 1.2, 6000.0),
            "spend": _always_on_spend(700.0, 60.0, floor_eur=400),
            "platform": _online_platform(1.1, 0.05, 50.0),
        },
        "search_generic": {
            "true_params": _true_params(0.20, 3000.0, 1.0, 15000.0),
            "spend": _always_on_spend(2500.0, 200.0, advent_factor=0.5, spring_factor=0.2),
            "platform": _online_platform(1.3, 0.01, 30.0),
        },
        "meta": {
            "true_params": _true_params(0.35, 2500.0, 0.9, 12000.0),
            "spend": _always_on_spend(2000.0, 300.0, pulse_every=6, pulse_multiplier=1.8),
            "platform": _online_platform(1.5, 0.01, 20.0),
        },
        "display_video": {
            "true_params": _true_params(0.50, 2000.0, 1.1, display_video_beta),
            "spend": _always_on_spend(1200.0, 150.0),
            "platform": _online_platform(2.0, 0.005, 15.0),
        },
        "print_regional": {
            "true_params": _true_params(0.60, 4000.0, 1.3, 8000.0),
            "spend": _flighted_spend(
                5000.0, 500.0, burst_length=2, burst_starts={burst_year: (10, 30)}
            ),
            "platform": _offline_platform(),
        },
        "radio": {
            "true_params": _true_params(0.55, 3500.0, 1.2, 5000.0),
            "spend": _flighted_spend(
                3500.0, 300.0, burst_length=3, burst_starts={burst_year: (5, 20)}
            ),
            "platform": _offline_platform(),
        },
    }


def _base_season_weights() -> dict[str, float]:
    return {
        "advent": 0.55,
        "schulbeginn": 0.25,
        "spring": 0.15,
        "jan_dip": -0.20,
        "summer_lull": -0.10,
    }


def _base_scenario_dict(
    *,
    scenario_id: str,
    weeks: int,
    seed: int,
    start_iso_year: int,
    start_iso_week: int,
    end_iso_year: int,
    end_iso_week: int,
    collinearity: bool,
    promo_weeks: dict[int, tuple[int, ...]],
    burst_year: int,
    display_video_beta: float,
) -> dict[str, object]:
    """A fresh, minimal but fully valid payload for one (id, weeks, seed) row."""
    return {
        "id": scenario_id,
        "weeks": weeks,
        "seed": seed,
        "start_iso_year": start_iso_year,
        "start_iso_week": start_iso_week,
        "end_iso_year": end_iso_year,
        "end_iso_week": end_iso_week,
        "collinearity": collinearity,
        "b0": 60000.0,
        "growth": 0.001,
        "noise_share": 0.04,
        "aov_base": 95.0,
        "aov_advent_bonus": 10.0,
        "promo_multiplier": 1.15,
        "season_weights": _base_season_weights(),
        "promo_weeks": promo_weeks,
        "channels": _base_channels(burst_year=burst_year, display_video_beta=display_video_beta),
    }


def _valid_scenario_dict(**overrides: object) -> dict[str, object]:
    """A minimal but fully valid s_a-shaped payload, with shallow-merge overrides.
    Every negative test in this file builds from this helper so a failure
    isolates exactly one deviation. This helper hard-codes no SPEC-01 section 4
    value that plan 02-03's spec-equality test also asserts -- it is a shape
    fixture, not a second home for the parameter table."""
    base = _base_scenario_dict(
        scenario_id="s_a",
        weeks=156,
        seed=101,
        start_iso_year=2021,
        start_iso_week=1,
        end_iso_year=2023,
        end_iso_week=52,
        collinearity=False,
        promo_weeks={2021: (47,), 2022: (47,), 2023: (47,)},
        burst_year=2021,
        display_video_beta=6000.0,
    )
    return _deep_merge(base, overrides)


def _valid_s_b_dict(**overrides: object) -> dict[str, object]:
    """An s_b-shaped payload: SPEC-01 section 5's second (id, weeks, seed) row,
    re-anchored to a 2021-2022 window so every promo/burst week stays inside it."""
    base = _base_scenario_dict(
        scenario_id="s_b",
        weeks=104,
        seed=202,
        start_iso_year=2021,
        start_iso_week=1,
        end_iso_year=2022,
        end_iso_week=52,
        collinearity=True,
        promo_weeks={2021: (47,), 2022: (47,)},
        burst_year=2021,
        display_video_beta=6000.0,
    )
    return _deep_merge(base, overrides)


def _valid_s_c_dict(**overrides: object) -> dict[str, object]:
    """An s_c-shaped payload: SPEC-01 section 5's third (id, weeks, seed) row,
    zero-effect `display_video`, re-anchored to the 02_WBS.md S-C reading
    (2022-W01..2023-W26) with every promo/burst week re-anchored inside it."""
    base = _base_scenario_dict(
        scenario_id="s_c",
        weeks=78,
        seed=303,
        start_iso_year=2022,
        start_iso_week=1,
        end_iso_year=2023,
        end_iso_week=26,
        collinearity=True,
        promo_weeks={2022: (47,), 2023: (21,)},
        burst_year=2022,
        display_video_beta=0.0,
    )
    return _deep_merge(base, overrides)


def _to_yaml_native(value: object) -> object:
    """Recursively convert tuples to lists so `yaml.safe_dump` (which has no
    representer for `tuple`) can serialize a payload built with this file's dict
    helpers -- a real authored scenario YAML would have lists at these positions
    too; pydantic coerces them to tuples on load."""
    if isinstance(value, dict):
        return {key: _to_yaml_native(val) for key, val in value.items()}
    if isinstance(value, tuple):
        return [_to_yaml_native(val) for val in value]
    return value


class _FakeScenarioEntry:
    """Stand-in for `ambo.common.config.ScenarioConfig` (the settings-registry
    entry, not this module's `ScenarioConfig`) -- only the `config` attribute
    `load_scenario()` reads."""

    def __init__(self, config: Path) -> None:
        self.config = config


class _FakeSettings:
    """Stand-in for `ambo.common.config.Settings` -- only the `scenarios`
    attribute `load_scenario()` reads."""

    def __init__(self, scenarios: dict[str, _FakeScenarioEntry]) -> None:
        self.scenarios = scenarios


# ---------------------------------------------------------------------------
# Construction and extra='forbid'
# ---------------------------------------------------------------------------


def test_scenario_config_constructs_from_valid_payload() -> None:
    cfg = ScenarioConfig(**_valid_scenario_dict())
    assert cfg.id == "s_a"
    assert cfg.weeks == 156
    assert tuple(cfg.channels) == SPEC_CHANNEL_ORDER


def test_extra_key_raises_naming_the_key() -> None:
    with pytest.raises(ValidationError, match="unexpected_key"):
        ScenarioConfig(**_valid_scenario_dict(unexpected_key=1))


def test_models_are_frozen() -> None:
    cfg = ScenarioConfig(**_valid_scenario_dict())
    with pytest.raises(ValidationError, match="frozen"):
        cfg.weeks = 104  # type: ignore[misc]


# ---------------------------------------------------------------------------
# weeks grain + (id, weeks, seed) identity (SPEC-01 section 5)
# ---------------------------------------------------------------------------


def test_invalid_weeks_grain_raises() -> None:
    with pytest.raises(ValidationError, match="157"):
        ScenarioConfig(**_valid_scenario_dict(weeks=157))


@pytest.mark.parametrize(
    "builder",
    [_valid_scenario_dict, _valid_s_b_dict, _valid_s_c_dict],
    ids=["s_a", "s_b", "s_c"],
)
def test_valid_scenario_identity_constructs(builder: Any) -> None:
    cfg = ScenarioConfig(**builder())
    assert cfg.weeks in {156, 104, 78}


def test_scenario_identity_seed_mismatch_raises() -> None:
    with pytest.raises(ValidationError, match="999"):
        ScenarioConfig(**_valid_scenario_dict(seed=999))


# ---------------------------------------------------------------------------
# channels: membership + order (SPEC-01 section 4)
# ---------------------------------------------------------------------------


def test_spec_channel_order_matches_settings_taxonomy() -> None:
    """A-8 single-home guard: the six Layer P channels here must equal the first
    six entries of the shared `Settings.channels` taxonomy, and `other` (the
    Layer R seventh slot) must never appear in a Layer P scenario."""
    assert SPEC_CHANNEL_ORDER == tuple(load_settings().channels[:6])
    assert "other" not in SPEC_CHANNEL_ORDER


def test_channels_missing_radio_raises() -> None:
    payload = _valid_scenario_dict()
    channels = dict(payload["channels"])  # type: ignore[arg-type]
    del channels["radio"]
    payload["channels"] = channels
    with pytest.raises(ValidationError, match="radio"):
        ScenarioConfig(**payload)


def test_channels_containing_other_channel_raises() -> None:
    payload = _valid_scenario_dict()
    channels = dict(payload["channels"])  # type: ignore[arg-type]
    channels["other"] = channels.pop("radio")
    payload["channels"] = channels
    with pytest.raises(ValidationError, match="other"):
        ScenarioConfig(**payload)


def test_channels_out_of_order_raises() -> None:
    payload = _valid_scenario_dict()
    channels = payload["channels"]  # type: ignore[assignment]
    keys = list(channels)  # type: ignore[arg-type]
    keys[0], keys[1] = keys[1], keys[0]
    payload["channels"] = {key: channels[key] for key in keys}  # type: ignore[index]
    with pytest.raises(ValidationError, match="search_generic"):
        ScenarioConfig(**payload)


# ---------------------------------------------------------------------------
# S-C zero-effect display_video (SPEC-01 section 4 footnote)
# ---------------------------------------------------------------------------


def test_s_c_nonzero_display_video_beta_raises() -> None:
    payload = _valid_s_c_dict(channels={"display_video": {"true_params": {"beta": 6000.0}}})
    with pytest.raises(ValidationError, match="s_c"):
        ScenarioConfig(**payload)


def test_s_c_zero_display_video_beta_constructs() -> None:
    cfg = ScenarioConfig(**_valid_s_c_dict())
    assert cfg.channels["display_video"].true_params.beta == 0.0


def test_s_a_zero_display_video_beta_raises() -> None:
    payload = _valid_scenario_dict(channels={"display_video": {"true_params": {"beta": 0.0}}})
    with pytest.raises(ValidationError, match="s_a"):
        ScenarioConfig(**payload)


# ---------------------------------------------------------------------------
# promo/burst schedules inside the declared window
# ---------------------------------------------------------------------------


def test_promo_week_outside_window_raises() -> None:
    payload = _valid_scenario_dict(promo_weeks={2021: (47,), 2024: (1,)})
    with pytest.raises(ValidationError, match="2024"):
        ScenarioConfig(**payload)


def test_burst_start_outside_window_raises() -> None:
    """`radio`'s burst_length is 3; a start of 51 in the window's last ISO year
    (2023, end_iso_week=52) spans into week 53, which is outside the window."""
    payload = _valid_scenario_dict(channels={"radio": {"spend": {"burst_starts": {2023: (51,)}}}})
    with pytest.raises(ValidationError, match="53"):
        ScenarioConfig(**payload)


def test_overlapping_bursts_raise() -> None:
    """`print_regional`'s burst_length is 2; starts (10, 11) overlap because
    11 < 10 + 2."""
    payload = _valid_scenario_dict(
        channels={"print_regional": {"spend": {"burst_starts": {2021: (10, 11)}}}}
    )
    with pytest.raises(ValidationError, match="overlap"):
        ScenarioConfig(**payload)


def test_burst_adjacency_is_accepted_as_two_distinct_bursts() -> None:
    """Starts (10, 12) are exactly adjacent (10 + burst_length(2) == 12) and are
    accepted as two distinct bursts, never merged."""
    payload = _valid_scenario_dict(
        channels={"print_regional": {"spend": {"burst_starts": {2021: (10, 12)}}}}
    )
    cfg = ScenarioConfig(**payload)
    assert len(cfg.channels["print_regional"].spend.burst_starts[2021]) == 2  # type: ignore[index]


# ---------------------------------------------------------------------------
# platform-bias all-or-none (SPEC-01 section 6)
# ---------------------------------------------------------------------------


def test_platform_half_populated_raises() -> None:
    payload = _valid_scenario_dict(channels={"search_brand": {"platform": {"cpm": None}}})
    with pytest.raises(ValidationError, match="cpm=None"):
        ScenarioConfig(**payload)


def test_platform_all_set_constructs() -> None:
    cfg = ScenarioConfig(**_valid_scenario_dict())
    assert cfg.channels["search_brand"].platform.cpm is not None


def test_platform_all_none_constructs() -> None:
    cfg = ScenarioConfig(**_valid_scenario_dict())
    assert cfg.channels["print_regional"].platform.phi is None


# ---------------------------------------------------------------------------
# covered_iso_years / covered_week_count helpers
# ---------------------------------------------------------------------------


def test_covered_iso_years() -> None:
    s_a = ScenarioConfig(**_valid_scenario_dict())
    assert s_a.covered_iso_years() == (2021, 2022, 2023)

    s_c = ScenarioConfig(**_valid_s_c_dict())
    assert s_c.covered_iso_years() == (2022, 2023)


# ---------------------------------------------------------------------------
# load_scenario() boundary conversion (SimulationError, never a bare built-in)
# ---------------------------------------------------------------------------


def test_load_scenario_unknown_name() -> None:
    with pytest.raises(SimulationError, match="s_z"):
        load_scenario("s_z")


def test_load_scenario_missing_file_names_the_path(monkeypatch: pytest.MonkeyPatch) -> None:
    missing_relative = Path("config") / "scenarios" / "does_not_exist_s_q.yaml"
    fake_settings = _FakeSettings({"s_q": _FakeScenarioEntry(missing_relative)})
    monkeypatch.setattr("ambo.simulate.config.load_settings", lambda: fake_settings)

    expected_path = repo_root() / missing_relative
    with pytest.raises(SimulationError, match=re.escape(str(expected_path))):
        load_scenario("s_q")


def test_load_scenario_invalid_yaml_raises_naming_failing_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    scenario_dir = tmp_path / "config" / "scenarios"
    scenario_dir.mkdir(parents=True)

    invalid_payload = _valid_scenario_dict(weeks=157)
    (scenario_dir / "s_a.yaml").write_text(
        yaml.safe_dump(_to_yaml_native(invalid_payload)), encoding="utf-8"
    )

    fake_settings = _FakeSettings(
        {"s_a": _FakeScenarioEntry(Path("config") / "scenarios" / "s_a.yaml")}
    )
    monkeypatch.setattr("ambo.simulate.config.load_settings", lambda: fake_settings)
    monkeypatch.setattr("ambo.simulate.config.repo_root", lambda: tmp_path)

    with pytest.raises(SimulationError, match="weeks"):
        load_scenario("s_a")


# ---------------------------------------------------------------------------
# BP-G-02: scenario YAML == SPEC-01 spec tables (plan 02-03)
#
# Every constant below is hard-coded from SPEC-01 directly, deliberately
# duplicating the scenario YAMLs -- that duplication is exactly what BP-G-02
# asks for: two independent homes a test forces to agree, so drift in either
# one fails loudly instead of silently.
# ---------------------------------------------------------------------------

ALL_SCENARIO_IDS: tuple[str, ...] = ("s_a", "s_b", "s_c")

# SPEC-01 section 4, verbatim. display_video.beta is 6000.0 in s_a/s_b and 0.0
# in s_c (the section 4 footnote's zero-effect channel), handled as a per-test
# override below rather than baked into this table.
SPEC_01_SECTION_4: dict[str, dict[str, float]] = {
    "search_brand": {"lam": 0.10, "K": 800.0, "s": 1.2, "beta": 6000.0},
    "search_generic": {"lam": 0.20, "K": 3000.0, "s": 1.0, "beta": 15000.0},
    "meta": {"lam": 0.35, "K": 2500.0, "s": 0.9, "beta": 12000.0},
    "display_video": {"lam": 0.50, "K": 2000.0, "s": 1.1, "beta": 6000.0},
    "print_regional": {"lam": 0.60, "K": 4000.0, "s": 1.3, "beta": 8000.0},
    "radio": {"lam": 0.55, "K": 3500.0, "s": 1.2, "beta": 5000.0},
}

# SPEC-01 section 6, verbatim. print_regional/radio carry no platform reporting
# at all (phi/theta/cpm all None -- offline channels); the four online
# channels' `cpm` values are BP-D-02-authored, not spec-given, so only
# phi/theta are pinned to a spec value here.
SPEC_01_SECTION_6: dict[str, dict[str, float | None]] = {
    "search_brand": {"phi": 1.1, "theta": 0.05},
    "search_generic": {"phi": 1.3, "theta": 0.01},
    "meta": {"phi": 1.5, "theta": 0.01},
    "display_video": {"phi": 2.0, "theta": 0.005},
    "print_regional": {"phi": None, "theta": None},
    "radio": {"phi": None, "theta": None},
}

# SPEC-01 section 2.1, verbatim.
SPEC_01_SEASON_WEIGHTS: dict[str, float] = {
    "advent": 0.55,
    "schulbeginn": 0.25,
    "spring": 0.15,
    "jan_dip": -0.20,
    "summer_lull": -0.10,
}

SPEC_01_SCALAR_CONSTANTS: dict[str, float] = {
    "b0": 60000.0,
    "growth": 0.001,
    "noise_share": 0.04,
    "aov_base": 95.0,
    "aov_advent_bonus": 10.0,
    "promo_multiplier": 1.15,
}

# SPEC-01 section 5, verbatim: (weeks, seed, start, end) per scenario.
SPEC_01_SECTION_5_WINDOWS: dict[str, dict[str, object]] = {
    "s_a": {"weeks": 156, "seed": 101, "start": (2021, 1), "end": (2023, 52)},
    "s_b": {"weeks": 104, "seed": 202, "start": (2022, 1), "end": (2023, 52)},
    "s_c": {"weeks": 78, "seed": 303, "start": (2022, 1), "end": (2023, 26)},
}


def _raw_scenario_yaml(scenario_id: str) -> dict[str, Any]:
    """Load one scenario's raw YAML with `yaml.safe_load` directly -- never
    through `load_scenario()` -- so this test suite trusts nothing about the
    loader's own transformation and re-derives everything independently
    (mirrors `test_config.py`'s round-trip pattern)."""
    path = repo_root() / "config" / "scenarios" / f"{scenario_id}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def _all_raw_scenarios() -> dict[str, dict[str, Any]]:
    return {scenario_id: _raw_scenario_yaml(scenario_id) for scenario_id in ALL_SCENARIO_IDS}


def _season_windows_rows() -> list[dict[str, str]]:
    path = repo_root() / "dbt" / "seeds" / "season_windows.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _year_windows() -> dict[int, dict[str, Any]]:
    """Per ISO year: the flagged `advent`/`schulbeginn`/`spring` week numbers
    plus the year's total ISO week count -- read directly from the committed
    calendar seed, never recomputed from calendar rules (AD-020)."""
    windows: dict[int, dict[str, Any]] = {}
    for row in _season_windows_rows():
        year = int(row["iso_year"])
        week = int(row["iso_week"])
        entry = windows.setdefault(
            year, {"advent": [], "schulbeginn": [], "spring": [], "weeks_in_year": 0}
        )
        entry["weeks_in_year"] = max(entry["weeks_in_year"], week)
        if row["advent_flag"] == "1":
            entry["advent"].append(week)
        if row["schulbeginn_flag"] == "1":
            entry["schulbeginn"].append(week)
        if row["spring_flag"] == "1":
            entry["spring"].append(week)
    return windows


def _black_friday_week(iso_year: int) -> int:
    """The ISO week containing the 4th Friday of November of `iso_year`,
    re-derived independently of `scripts/author_scenario_schedules.py`."""
    fridays_seen = 0
    day = date(iso_year, 11, 1)
    while True:
        if day.weekday() == 4:
            fridays_seen += 1
            if fridays_seen == 4:
                return day.isocalendar()[1]
        day += timedelta(days=1)


def _prorate(full_count: int, covered_weeks: int, weeks_in_year: int) -> int:
    """floor(full_count * covered_weeks / weeks_in_year + 0.5) -- round half UP
    (BP-D-09), re-derived independently of the authoring aid's own `prorate()`."""
    return math.floor(full_count * covered_weeks / weeks_in_year + 0.5)


def _covered_span(
    iso_year: int, start: tuple[int, int], end: tuple[int, int], weeks_in_year: int
) -> tuple[int, int]:
    start_year, start_week = start
    end_year, end_week = end
    covered_start = start_week if iso_year == start_year else 1
    covered_end = end_week if iso_year == end_year else weeks_in_year
    return covered_start, covered_end


def test_yaml_matches_spec_parameter_table() -> None:
    raw_by_scenario = _all_raw_scenarios()
    assert len(raw_by_scenario) == 3, (
        "expected exactly 3 scenario YAML files -- the scan is broken, not vacuously passing."
    )
    for scenario_id, raw in raw_by_scenario.items():
        for channel_id, expected in SPEC_01_SECTION_4.items():
            actual = raw["channels"][channel_id]["true_params"]
            for field in ("lam", "K", "s"):
                assert actual[field] == expected[field], (
                    f"{scenario_id}.{channel_id}.{field}: expected {expected[field]!r}, "
                    f"got {actual[field]!r}"
                )
            expected_beta = (
                0.0
                if (channel_id == "display_video" and scenario_id == "s_c")
                else expected["beta"]
            )
            assert actual["beta"] == expected_beta, (
                f"{scenario_id}.{channel_id}.beta: expected {expected_beta!r}, "
                f"got {actual['beta']!r}"
            )


def test_yaml_matches_spec_season_weights() -> None:
    raw_by_scenario = _all_raw_scenarios()
    assert len(raw_by_scenario) == 3, (
        "expected exactly 3 scenario YAML files -- the scan is broken, not vacuously passing."
    )
    for scenario_id, raw in raw_by_scenario.items():
        actual = raw["season_weights"]
        for key, expected_value in SPEC_01_SEASON_WEIGHTS.items():
            assert actual[key] == expected_value, f"{scenario_id}.season_weights.{key}"


def test_yaml_matches_spec_scalar_constants() -> None:
    raw_by_scenario = _all_raw_scenarios()
    assert len(raw_by_scenario) == 3, (
        "expected exactly 3 scenario YAML files -- the scan is broken, not vacuously passing."
    )
    for scenario_id, raw in raw_by_scenario.items():
        for key, expected_value in SPEC_01_SCALAR_CONSTANTS.items():
            assert raw[key] == expected_value, f"{scenario_id}.{key}"


def test_yaml_matches_spec_platform_bias_table() -> None:
    raw_by_scenario = _all_raw_scenarios()
    assert len(raw_by_scenario) == 3, (
        "expected exactly 3 scenario YAML files -- the scan is broken, not vacuously passing."
    )
    for scenario_id, raw in raw_by_scenario.items():
        for channel_id, expected in SPEC_01_SECTION_6.items():
            actual = raw["channels"][channel_id]["platform"]
            if expected["phi"] is None:
                assert actual["phi"] is None, f"{scenario_id}.{channel_id}.phi"
                assert actual["theta"] is None, f"{scenario_id}.{channel_id}.theta"
                assert actual["cpm"] is None, f"{scenario_id}.{channel_id}.cpm"
            else:
                assert actual["phi"] == expected["phi"], f"{scenario_id}.{channel_id}.phi"
                assert actual["theta"] == expected["theta"], f"{scenario_id}.{channel_id}.theta"
                assert actual["cpm"] is not None, f"{scenario_id}.{channel_id}.cpm is None"
                assert actual["cpm"] > 0, f"{scenario_id}.{channel_id}.cpm must be positive"


def test_week_counts_and_window_endpoints() -> None:
    rows = _season_windows_rows()
    assert rows, "dbt/seeds/season_windows.csv scan is broken, not vacuously passing."
    row_index = {(int(r["iso_year"]), int(r["iso_week"])): r for r in rows}

    scanned = 0
    for scenario_id, expected in SPEC_01_SECTION_5_WINDOWS.items():
        scanned += 1
        raw = _raw_scenario_yaml(scenario_id)
        assert raw["weeks"] == expected["weeks"], f"{scenario_id}.weeks"

        start = (raw["start_iso_year"], raw["start_iso_week"])
        end = (raw["end_iso_year"], raw["end_iso_week"])
        assert start == expected["start"], f"{scenario_id} start window"
        assert end == expected["end"], f"{scenario_id} end window"

        count = sum(1 for point in row_index if start <= point <= end)
        assert count == expected["weeks"], (
            f"{scenario_id}: seed row count between {start} and {end} inclusive is "
            f"{count}, expected {expected['weeks']}"
        )
    assert scanned == 3, "expected exactly 3 scenarios scanned -- the scan is broken."

    assert row_index[(2021, 1)]["week_start"] == "2021-01-04"
    assert row_index[(2022, 1)]["week_start"] == "2022-01-03"
    assert row_index[(2023, 26)]["week_start"] == "2023-06-26"


def test_promo_week_counting_rules() -> None:
    year_windows = _year_windows()
    scanned = 0
    for scenario_id, expected in SPEC_01_SECTION_5_WINDOWS.items():
        raw = _raw_scenario_yaml(scenario_id)
        start = expected["start"]
        end = expected["end"]
        assert isinstance(start, tuple) and isinstance(end, tuple)
        start_year, _start_week = start
        end_year, _end_week = end

        for year in range(start_year, end_year + 1):
            scanned += 1
            weeks_in_year = year_windows[year]["weeks_in_year"]
            covered_start, covered_end = _covered_span(year, start, end, weeks_in_year)
            covered_weeks = covered_end - covered_start + 1
            expected_count = _prorate(10, covered_weeks, weeks_in_year)

            promo_weeks_year = raw["promo_weeks"][year]
            assert len(promo_weeks_year) == expected_count, (
                f"{scenario_id} {year}: expected {expected_count} promo weeks, got "
                f"{len(promo_weeks_year)}"
            )

            bf_week = _black_friday_week(year)
            if covered_start <= bf_week <= covered_end:
                assert bf_week in promo_weeks_year, (
                    f"{scenario_id} {year}: missing Black Friday promo week {bf_week}"
                )

            advent_weeks = year_windows[year]["advent"]
            nearest_to_dec24 = [w for w in sorted(advent_weeks, reverse=True) if w != bf_week][:2]
            for week in nearest_to_dec24:
                if covered_start <= week <= covered_end:
                    assert week in promo_weeks_year, (
                        f"{scenario_id} {year}: missing Advent-anchored promo week {week}"
                    )

            # The 2 spring anchors are re-derived at the same 1/3 and 2/3 index
            # points the authoring aid itself uses (not a literal week-number
            # constant, since the spring window's own boundaries are read from
            # the seed, not hard-coded) -- checking for their *presence* is
            # more precise than counting "weeks inside spring window", since an
            # unconstrained spread pick can coincidentally also land inside the
            # spring window without being wrong.
            spring_weeks = year_windows[year]["spring"]
            n = len(spring_weeks)
            spring_anchors = {spring_weeks[n // 3], spring_weeks[(2 * n) // 3]}
            for week in spring_anchors:
                if covered_start <= week <= covered_end:
                    assert week in promo_weeks_year, (
                        f"{scenario_id} {year}: missing spring-anchored promo week {week}"
                    )
            in_spring = [w for w in promo_weeks_year if w in spring_weeks]
            if all(covered_start <= w <= covered_end for w in spring_weeks):
                assert len(in_spring) >= 2, (
                    f"{scenario_id} {year}: expected at least 2 promo weeks inside the "
                    f"fully covered spring window, got {len(in_spring)}: {in_spring}"
                )

    assert scanned > 0, (
        "no (scenario, year) pairs scanned -- the scan is broken, not vacuously passing."
    )


def test_burst_counting_rules() -> None:
    year_windows = _year_windows()
    scanned = 0
    for scenario_id, expected in SPEC_01_SECTION_5_WINDOWS.items():
        raw = _raw_scenario_yaml(scenario_id)
        start = expected["start"]
        end = expected["end"]
        assert isinstance(start, tuple) and isinstance(end, tuple)
        start_year, _start_week = start
        end_year, _end_week = end

        for year in range(start_year, end_year + 1):
            weeks_in_year = year_windows[year]["weeks_in_year"]
            covered_start, covered_end = _covered_span(year, start, end, weeks_in_year)
            covered_weeks = covered_end - covered_start + 1
            advent_start = min(year_windows[year]["advent"])
            schulbeginn_start = min(year_windows[year]["schulbeginn"])

            channel_rules = (
                ("print_regional", 8, 2, (advent_start, advent_start + 2, schulbeginn_start)),
                ("radio", 5, 3, (advent_start - 3, advent_start)),
            )
            for channel_id, per_year_count, length, anchor_starts in channel_rules:
                scanned += 1
                expected_count = _prorate(per_year_count, covered_weeks, weeks_in_year)
                starts = raw["channels"][channel_id]["spend"]["burst_starts"].get(year, [])
                assert len(starts) == expected_count, (
                    f"{scenario_id} {channel_id} {year}: expected {expected_count} burst "
                    f"starts, got {len(starts)}: {starts}"
                )

                for anchor in anchor_starts:
                    if covered_start <= anchor and anchor + length - 1 <= covered_end:
                        assert anchor in starts, (
                            f"{scenario_id} {channel_id} {year}: missing anchored burst "
                            f"start {anchor}"
                        )

                for burst_start in starts:
                    assert covered_start <= burst_start, (
                        f"{scenario_id} {channel_id} {year}: burst start {burst_start} "
                        f"falls before the covered span"
                    )
                    assert burst_start + length - 1 <= covered_end, (
                        f"{scenario_id} {channel_id} {year}: burst starting "
                        f"{burst_start} (length {length}) extends past covered span "
                        f"end {covered_end}"
                    )

                ordered = sorted(starts)
                for prev_start, next_start in zip(ordered, ordered[1:], strict=False):
                    assert next_start >= prev_start + length, (
                        f"{scenario_id} {channel_id} {year}: overlapping bursts "
                        f"{prev_start}/{next_start}"
                    )

    assert scanned > 0, (
        "no (scenario, channel, year) triples scanned -- the scan is broken, not vacuously passing."
    )


def test_s_c_differs_from_s_b_at_rule_level() -> None:
    """S-C is 'identical to S-B except ...' (SPEC-01 section 4 footnote) is a
    statement about the *generating rule*, not the literal YAML diff: S-C's
    shortened 78-week window (vs S-B's 104) legitimately changes the *count*
    and *placement* of promo/burst weeks compared to S-B, even though both
    files satisfy the same section-3 counting rules (asserted separately by
    `test_promo_week_counting_rules`/`test_burst_counting_rules` above). A
    literal 3-key (`weeks`, `seed`, `display_video.beta`) YAML diff would
    spuriously fail on the schedule lists -- see 02-RESEARCH.md Pitfall 7.
    Schedule lists are therefore deliberately NOT asserted equal or unequal
    here; only their un-scheduled sibling fields are."""
    s_b = load_scenario("s_b")
    s_c = load_scenario("s_c")

    assert s_b.collinearity is True
    assert s_c.collinearity is True

    for channel_id in SPEC_CHANNEL_ORDER:
        b_channel = s_b.channels[channel_id]
        c_channel = s_c.channels[channel_id]

        assert b_channel.true_params.lam == c_channel.true_params.lam
        assert b_channel.true_params.K == c_channel.true_params.K
        assert b_channel.true_params.s == c_channel.true_params.s
        if channel_id == "display_video":
            assert b_channel.true_params.beta == 6000.0
            assert c_channel.true_params.beta == 0.0
        else:
            assert b_channel.true_params.beta == c_channel.true_params.beta

        assert b_channel.spend.mean == c_channel.spend.mean
        assert b_channel.spend.sd == c_channel.spend.sd
        assert b_channel.spend.floor_eur == c_channel.spend.floor_eur
        assert b_channel.spend.advent_factor == c_channel.spend.advent_factor
        assert b_channel.spend.spring_factor == c_channel.spend.spring_factor
        assert b_channel.spend.pulse_every == c_channel.spend.pulse_every
        assert b_channel.spend.pulse_multiplier == c_channel.spend.pulse_multiplier
        assert b_channel.spend.burst_length == c_channel.spend.burst_length
        # burst_starts (the schedule list) is deliberately not compared here.

        assert b_channel.platform.phi == c_channel.platform.phi
        assert b_channel.platform.theta == c_channel.platform.theta
        assert b_channel.platform.cpm == c_channel.platform.cpm

    assert s_b.weeks == 104
    assert s_c.weeks == 78
    assert s_b.seed == 202
    assert s_c.seed == 303
    assert (s_b.start_iso_year, s_b.start_iso_week) == (s_c.start_iso_year, s_c.start_iso_week)
    assert (s_b.end_iso_year, s_b.end_iso_week) != (s_c.end_iso_year, s_c.end_iso_week)
    # promo_weeks (the other schedule list) is deliberately not compared here.


def test_collinearity_switch_is_expressed_in_data() -> None:
    raw_by_scenario = _all_raw_scenarios()
    assert len(raw_by_scenario) == 3, (
        "expected exactly 3 scenario YAML files -- the scan is broken, not vacuously passing."
    )
    expected_advent_factor = {"s_a": 0.5, "s_b": 0.9, "s_c": 0.9}

    for scenario_id, raw in raw_by_scenario.items():
        for channel_id in ("search_generic", "meta"):
            actual = raw["channels"][channel_id]["spend"]["advent_factor"]
            assert actual == expected_advent_factor[scenario_id], (
                f"{scenario_id}.{channel_id}.advent_factor: expected "
                f"{expected_advent_factor[scenario_id]!r}, got {actual!r}"
            )
        assert raw["channels"]["search_generic"]["spend"]["spring_factor"] == 0.2, (
            f"{scenario_id}.search_generic.spring_factor"
        )

        for channel_id, channel in raw["channels"].items():
            if channel_id in ("search_generic", "meta"):
                continue
            actual = channel["spend"]["advent_factor"]
            assert actual == 0.0, (
                f"{scenario_id}.{channel_id}.advent_factor: expected 0.0, got {actual!r}"
            )


def test_authoring_aid_is_not_reachable_from_src() -> None:
    """A-13/CONTEXT.md D-02 guard: the throwaway placement aid
    (`scripts/author_scenario_schedules.py`) must never become importable or
    even referenced production code."""
    src_root = repo_root() / "src" / "ambo"
    py_files = list(src_root.rglob("*.py"))
    assert py_files, "No files found under src/ambo/ -- the scan is broken, not vacuously passing."

    offenders = [
        py_file
        for py_file in py_files
        if "author_scenario_schedules" in py_file.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        "authoring aid referenced from src/ambo/ (A-13/D-02 violation): "
        + ", ".join(str(p) for p in offenders)
    )
