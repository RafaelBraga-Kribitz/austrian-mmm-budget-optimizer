"""Typed, validated, single-read configuration (EB-040).

Implements: EB-040, EB-041, AG-020, MD-050, ADR-006

The only module that reads `config/settings.yaml` and `AMBO_PRIVATE_DROP` directly;
every other module reads settings via `load_settings()`.

`Settings` is a `pydantic.BaseModel`, not a `pydantic.BaseSettings`. `BaseSettings`
moved to the separate `pydantic-settings` distribution in pydantic v2, that
distribution is not in the SPEC-08 section 3 dependency table, and EB-030 makes
adding a new dependency an ADR event. EB-040's actual requirement — a
pydantic-validated, single-read settings object — is fully satisfied by `BaseModel`
plus the `functools.lru_cache` on `load_settings()` below, so no new dependency is
needed.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from ambo.common.errors import ConfigError

SETTINGS_RELATIVE_PATH = "config/settings.yaml"

# SPEC-02 section 5.2, verbatim and in order. dbt pivots over this list, so the order
# is part of the contract, not just the membership.
SPEC_CHANNEL_ORDER: tuple[str, ...] = (
    "search_brand",
    "search_generic",
    "meta",
    "display_video",
    "print_regional",
    "radio",
    "other",
)


def repo_root() -> Path:
    """Resolve the repository root independent of the caller's working directory.

    Walks parents of this file until it finds the directory containing
    `pyproject.toml`. Raises `ConfigError` if none is found.
    """
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ConfigError(f"repo_root(): no pyproject.toml found in any parent directory of {current}")


class PathsConfig(BaseModel):
    """The six repository-relative paths every later module resolves through."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    data_synthetic: Path
    data_real_anon: Path
    posteriors: Path
    warehouse: Path
    exports: Path
    reports: Path


class SamplerConfig(BaseModel):
    """MD-050's fixed sampling settings, and nowhere else in `src/`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chains: int
    tune: int
    draws: int
    target_accept: float
    random_seed: int
    init: str


class ScenarioConfig(BaseModel):
    """One scenario registry entry. Phase 1 declares the schema only; full
    simulate-layer parameters are read from the scenario YAML itself, never
    duplicated here (EB-040)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    config: Path


class Settings(BaseModel):
    """The single, validated, single-read settings object (EB-040)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    channels: tuple[str, ...]
    adstock_length: int
    max_fit_minutes: int
    paths: PathsConfig
    sampler: SamplerConfig
    scenarios: dict[str, ScenarioConfig]
    private_drop: Path | None = None

    @field_validator("channels")
    @classmethod
    def _validate_channel_order(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        value = tuple(value)
        if value != SPEC_CHANNEL_ORDER:
            raise ValueError(
                f"channels must equal {SPEC_CHANNEL_ORDER!r} in that exact order, got {value!r}"
            )
        return value

    @field_validator("max_fit_minutes")
    @classmethod
    def _validate_max_fit_minutes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError(f"max_fit_minutes must be > 0, got {value!r}")
        return value


def _resolve_paths_block(raw_paths: Any, root: Path) -> Any:
    """Anchor every declared path against repo_root() before validation.

    Returns the input unchanged if it is not a mapping, so pydantic's own
    validation reports the type error rather than this helper.
    """
    if not isinstance(raw_paths, dict):
        return raw_paths
    return {key: str(root / value) for key, value in raw_paths.items()}


@functools.lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load, validate and cache the project's settings (EB-040).

    Reads `.env` via `python-dotenv` without overriding an already-set environment,
    reads `AMBO_PRIVATE_DROP` into `private_drop` as a resolved `Path` or `None`,
    parses `config/settings.yaml` with `yaml.safe_load`, and wraps any
    `ValidationError` in `ConfigError` naming the failing key path. An unset
    `AMBO_PRIVATE_DROP` is never an error here — only an intake target may raise on
    it (AG-020); `config.py` itself never raises on a missing drop.
    """
    root = repo_root()
    load_dotenv(root / ".env", override=False)

    private_drop_raw = os.environ.get("AMBO_PRIVATE_DROP")
    private_drop = Path(private_drop_raw).resolve() if private_drop_raw else None

    settings_path = root / SETTINGS_RELATIVE_PATH
    if not settings_path.is_file():
        raise ConfigError(
            f"load_settings(): expected configuration file at {settings_path}, not found"
        )

    with settings_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ConfigError(f"load_settings(): {settings_path} did not parse to a mapping")

    data: dict[str, Any] = dict(raw)
    data["paths"] = _resolve_paths_block(data.get("paths"), root)
    data["private_drop"] = private_drop

    try:
        return Settings(**data)
    except ValidationError as exc:
        failing_keys = ", ".join(
            ".".join(str(part) for part in error["loc"]) for error in exc.errors()
        )
        raise ConfigError(
            f"load_settings(): invalid configuration in {settings_path} — failing "
            f"key path(s): {failing_keys}"
        ) from exc
