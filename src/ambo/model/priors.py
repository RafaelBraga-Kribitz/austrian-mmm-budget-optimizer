"""Prior YAML schema (SPEC-04 §4, MD-040).

Implements: MD-040

`PriorConfig` is the only object `build_model` reads for prior hyperparameters.
Layer P values live in `config/priors_synthetic.yaml` and are channel-agnostic
on purpose: recovery must come from data plus structure, not from priors that
encode the truth table. Layer R YAML is authored at M4 — this module never
invents it.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from ambo.common.config import SPEC_CHANNEL_ORDER
from ambo.common.errors import FitError

SYNTHETIC_PRIORS_RELATIVE = "config/priors_synthetic.yaml"


def _gt_zero(name: str, value: float) -> float:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and > 0, got {value!r}")
    return value


class BetaParams(BaseModel):
    """Beta(a, b) hyperparameters for λ (SPEC-04 §4)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    a: float
    b: float

    @field_validator("a", "b")
    @classmethod
    def _positive(cls, value: float) -> float:
        return _gt_zero("Beta parameter", value)


class GammaParams(BaseModel):
    """Gamma(shape, rate) hyperparameters for K in scaled spend units."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    shape: float
    rate: float

    @field_validator("shape", "rate")
    @classmethod
    def _positive(cls, value: float) -> float:
        return _gt_zero("Gamma parameter", value)


class TruncGammaParams(BaseModel):
    """Truncated Gamma(shape, rate) on [lower, upper] for the Hill slope s."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    shape: float
    rate: float
    lower: float
    upper: float

    @field_validator("shape", "rate")
    @classmethod
    def _positive(cls, value: float) -> float:
        return _gt_zero("Truncated-Gamma parameter", value)

    @model_validator(mode="after")
    def _ordered_finite_bounds(self) -> Self:
        if not math.isfinite(self.lower) or not math.isfinite(self.upper):
            raise ValueError("Truncated-Gamma bounds must be finite")
        if not (self.lower < self.upper):
            raise ValueError(
                f"Truncated-Gamma lower must be < upper, got [{self.lower}, {self.upper}]"
            )
        return self


class HalfNormalParams(BaseModel):
    """HalfNormal(sigma) hyperparameters for β and residual σ."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sigma: float

    @field_validator("sigma")
    @classmethod
    def _positive(cls, value: float) -> float:
        return _gt_zero("HalfNormal sigma", value)


class NormalParams(BaseModel):
    """Normal(mu, sigma) hyperparameters for intercept, trend, Fourier, dummies."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mu: float
    sigma: float

    @field_validator("mu")
    @classmethod
    def _finite_mu(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError(f"Normal mu must be finite, got {value!r}")
        return value

    @field_validator("sigma")
    @classmethod
    def _positive_sigma(cls, value: float) -> float:
        return _gt_zero("Normal sigma", value)


class ChannelPrior(BaseModel):
    """Per-channel media priors: λ, K, s, β."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lam: BetaParams
    K: GammaParams
    s: TruncGammaParams
    beta: HalfNormalParams


class GlobalPriors(BaseModel):
    """Non-media priors (SPEC-04 §4), shared across channels."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    alpha: NormalParams
    tau: NormalParams
    gamma: NormalParams
    delta_promo: NormalParams
    delta_advent: NormalParams
    delta_jan: NormalParams
    sigma: HalfNormalParams


class PriorConfig(BaseModel):
    """The prior tree `build_model` consumes. extra=forbid, frozen.

    `channels` lists every SPEC-02 §5.2 name explicitly (D-19), even when values
    are identical. MD-040 equality is asserted in tests, not by schema identity.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    channels: dict[str, ChannelPrior]
    globals: GlobalPriors

    @model_validator(mode="after")
    def _channels_match_taxonomy(self) -> Self:
        keys = tuple(self.channels)
        if keys != SPEC_CHANNEL_ORDER:
            raise ValueError(
                f"channels keys must equal {SPEC_CHANNEL_ORDER!r} in that exact order, got {keys!r}"
            )
        return self


def load_priors(path: Path) -> PriorConfig:
    """Parse and validate a prior YAML. Raises `FitError` on missing/invalid files."""
    if not path.is_file():
        raise FitError(f"load_priors(): expected prior file at {path}, not found")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise FitError(f"load_priors(): {path} did not parse to a mapping")

    try:
        return PriorConfig(**raw)
    except ValidationError as exc:
        failing_keys = ", ".join(
            ".".join(str(part) for part in error["loc"]) for error in exc.errors()
        )
        raise FitError(
            f"load_priors(): invalid prior configuration in {path} — failing "
            f"key path(s): {failing_keys}"
        ) from exc
