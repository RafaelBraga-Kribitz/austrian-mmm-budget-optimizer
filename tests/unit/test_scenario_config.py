"""Structural validation tests for `ambo.simulate.config` (T-101).

Implements: SIM-002, BP-G-02, REQ-grain-and-windows

Every negative test builds from `_valid_scenario_dict()` (or its s_b/s_c-shaped
siblings) and deviates in exactly one field, so a failure isolates exactly one
validator. This file asserts on shape only -- no SPEC-01 section 4 parameter
value is pinned here; that spec-table-equality test lands in plan 02-03 once the
scenario YAMLs exist.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
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
