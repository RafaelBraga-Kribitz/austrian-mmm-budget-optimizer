"""Tests for `ambo.common.config` (T-004).

Implements: EB-040, EB-041, AG-020, MD-050
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from ambo.common.config import (
    SPEC_CHANNEL_ORDER,
    SamplerConfig,
    load_settings,
    repo_root,
)
from ambo.common.errors import ConfigError

SPEC_02_CHANNELS = [
    "search_brand",
    "search_generic",
    "meta",
    "display_video",
    "print_regional",
    "radio",
    "other",
]

# Fictional path — never a real developer value, per EB-041's own rule, honored
# even inside a test (as `test_leak_scan.py`/`test_logging.py` do). `config.py`'s
# `load_settings()` calls `Path(...).resolve()` on the raw env value, which is a
# no-op on an already-absolute path but prefixes the cwd onto a relative one. A
# drive-letter path (`D:/...`) is absolute on Windows but merely relative-looking
# on POSIX, so a fixed `D:/...` literal would resolve against `cwd` (not as the
# absolute path this test's name claims to exercise) on the Linux CI leg only
# (01-09/WR-04 fix-forward, 01-10). Branching on `sys.platform` keeps the fixture
# genuinely absolute on both.
FAKE_PRIVATE_DROP = (
    "D:/private/ambo_drop_fake" if sys.platform == "win32" else "/private/ambo_drop_fake"
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Every test starts and ends with a cold cache, so env/file changes are seen."""
    load_settings.cache_clear()
    yield
    load_settings.cache_clear()


@pytest.fixture
def _unset_private_drop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AMBO_PRIVATE_DROP", raising=False)


def test_yaml_round_trip_reproduces_every_value() -> None:
    settings_path = repo_root() / "config" / "settings.yaml"
    raw = yaml.safe_load(settings_path.read_text(encoding="utf-8"))

    settings = load_settings()

    assert list(settings.channels) == raw["channels"]
    assert settings.adstock_length == raw["adstock_length"]
    assert settings.max_fit_minutes == raw["max_fit_minutes"]
    assert settings.sampler.chains == raw["sampler"]["chains"]
    assert settings.sampler.tune == raw["sampler"]["tune"]
    assert settings.sampler.draws == raw["sampler"]["draws"]
    assert settings.sampler.target_accept == raw["sampler"]["target_accept"]
    assert settings.sampler.random_seed == raw["sampler"]["random_seed"]
    assert settings.sampler.init == raw["sampler"]["init"]
    assert set(settings.scenarios) == set(raw["scenarios"])
    for scenario_id, scenario_raw in raw["scenarios"].items():
        assert settings.scenarios[scenario_id].label == scenario_raw["label"]


def test_channel_list_matches_spec_02_order() -> None:
    settings = load_settings()
    assert list(settings.channels) == SPEC_02_CHANNELS
    assert SPEC_CHANNEL_ORDER == tuple(SPEC_02_CHANNELS)


def test_adstock_length_is_eight() -> None:
    assert load_settings().adstock_length == 8


def test_max_fit_minutes_is_thirty_five() -> None:
    """D-01 / ADR-006: the 35 min ceiling lives on Settings, not SamplerConfig."""
    settings = load_settings()
    assert settings.max_fit_minutes == 35
    assert "max_fit_minutes" not in SamplerConfig.model_fields
    assert list(SamplerConfig.model_fields) == [
        "chains",
        "tune",
        "draws",
        "target_accept",
        "random_seed",
        "init",
    ]


def test_load_settings_is_cached_and_idempotent() -> None:
    first = load_settings()
    second = load_settings()
    assert first is second


def test_unset_private_drop_is_none(_unset_private_drop: None) -> None:
    settings = load_settings()
    assert settings.private_drop is None


def test_set_private_drop_resolves_to_a_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AMBO_PRIVATE_DROP", FAKE_PRIVATE_DROP)
    settings = load_settings()
    assert settings.private_drop == Path(FAKE_PRIVATE_DROP).resolve()
    assert settings.private_drop.is_absolute()


def test_non_positive_max_fit_minutes_raises_config_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_settings_path = repo_root() / "config" / "settings.yaml"
    data = yaml.safe_load(real_settings_path.read_text(encoding="utf-8"))
    data["max_fit_minutes"] = 0

    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    fake_config_dir = tmp_path / "config"
    fake_config_dir.mkdir()
    (fake_config_dir / "settings.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")

    monkeypatch.setattr("ambo.common.config.repo_root", lambda: tmp_path)
    monkeypatch.delenv("AMBO_PRIVATE_DROP", raising=False)

    with pytest.raises(ConfigError, match="max_fit_minutes"):
        load_settings()


def test_unknown_key_raises_config_error_naming_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_settings_path = repo_root() / "config" / "settings.yaml"
    data = yaml.safe_load(real_settings_path.read_text(encoding="utf-8"))
    data["totally_unexpected_key"] = "should never validate"

    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    fake_config_dir = tmp_path / "config"
    fake_config_dir.mkdir()
    (fake_config_dir / "settings.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")

    monkeypatch.setattr("ambo.common.config.repo_root", lambda: tmp_path)
    monkeypatch.delenv("AMBO_PRIVATE_DROP", raising=False)

    with pytest.raises(ConfigError, match="totally_unexpected_key"):
        load_settings()


def test_missing_settings_file_raises_config_error_naming_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    expected_path = tmp_path / "config" / "settings.yaml"

    monkeypatch.setattr("ambo.common.config.repo_root", lambda: tmp_path)
    monkeypatch.delenv("AMBO_PRIVATE_DROP", raising=False)

    with pytest.raises(ConfigError, match=re.escape(str(expected_path))):
        load_settings()


def test_sampler_keys_appear_nowhere_else_in_src_ambo() -> None:
    """The single-config-home rule (EB-040 / 09_ANTI_PATTERNS A-2), as a test rather
    than a manual grep. Key names come from `SamplerConfig` itself so this test
    cannot drift from the config it is protecting."""
    sampler_keys = list(SamplerConfig.model_fields.keys())
    src_root = repo_root() / "src" / "ambo"
    config_module = src_root / "common" / "config.py"

    offenders: list[str] = []
    for py_file in src_root.rglob("*.py"):
        if py_file == config_module:
            continue
        text = py_file.read_text(encoding="utf-8")
        for key in sampler_keys:
            if re.search(rf"\b{re.escape(key)}\b", text):
                offenders.append(f"{py_file}: {key}")

    assert not offenders, "MD-050 sampler key(s) found outside common/config.py: " + ", ".join(
        offenders
    )
