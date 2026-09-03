"""Model-side adstock, Hill, and scaling (SPEC-04 MD-020 / MD-021 / MD-030).

Implements: MD-020, MD-021, MD-030

Independent of `ambo.simulate`: the simulator uses raw geometric recursion; this
module uses a finite-length *normalized* convolution (MD-020). Recovery is
meaningful only if the two implementations do not share code. `L` is an argument
(callers pass `Settings.adstock_length`); this file does not read settings.

Pytensor graphs in production; numpy references live in
`tests/unit/test_transforms.py` (T-301).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import pandas as pd
import pytensor.tensor as pt

from ambo.common.errors import FitError

# pytensor is untyped; graphs are tested numerically (T-301).
# mypy: disable-error-code="no-untyped-call"


def geometric_adstock_weights(lam: Any, length: int) -> Any:
    """Normalized geometric weights `w_i = lam**i / sum_{j=0..L-1} lam**j`.

    Implements: MD-020

    `length` is a Python int (baked into the graph). `lam` is a scalar tensor
    or a pytensor-compatible scalar. Raises `FitError` if `length < 1`.
    """
    if length < 1:
        raise FitError(f"geometric_adstock_weights(): L must be >= 1, got {length!r}")
    idx = pt.arange(length)
    weights = lam**idx
    return weights / pt.sum(weights)


def adstock_convolve(x: Any, lam: Any, length: int) -> Any:
    """Causal length-L convolution of `x` with normalized geometric weights.

    Implements: MD-020

    `output[t]` depends only on `x[max(0, t-L+1) .. t]`. Unrolled over `length`
    (a Python int) so the graph has no `scan` and no `convolve` — trap T-2 hides
    in reversed kernels and clever vectorization.
    """
    weights = geometric_adstock_weights(lam, length)
    delayed = x
    total = weights[0] * delayed
    for lag in range(1, length):
        delayed = pt.concatenate([pt.zeros((lag,)), x[:-lag]])
        total = total + weights[lag] * delayed
    return total


_HILL_FLOOR = 1e-8


def hill_saturation(a: Any, K: Any, s: Any) -> Any:
    """Hill saturation `a^s / (a^s + K^s)` (SPEC-01 §2.2 math, independent copy).

    Implements: MD-021

    Evaluated as `sigmoid(s * (log(a) - log(K)))` with a positive floor so
    gradients stay finite when adstocked spend is zero and `s < 1` (Pitfall 8).
    The floor is a numerical domain assertion, not a change to the formula.
    """
    a_safe = pt.maximum(a, _HILL_FLOOR)
    k_safe = pt.maximum(K, _HILL_FLOOR)
    return pt.sigmoid(s * (pt.log(a_safe) - pt.log(k_safe)))


@dataclass(frozen=True)
class ScaleFactors:
    """Positive revenue mean and per-channel nonzero-week spend means (MD-030).

    Implements: MD-030
    """

    revenue_mean: float
    spend_means: Mapping[str, float]

    def __post_init__(self) -> None:
        frozen_means = MappingProxyType(dict(self.spend_means))
        object.__setattr__(self, "spend_means", frozen_means)
        if not _is_positive_finite(self.revenue_mean):
            raise FitError(
                f"ScaleFactors: revenue_mean must be finite and > 0, got {self.revenue_mean!r}"
            )
        if not frozen_means:
            raise FitError("ScaleFactors: spend_means must contain at least one channel")
        for channel, mean in frozen_means.items():
            if not _is_positive_finite(mean):
                raise FitError(
                    f"ScaleFactors: spend mean for channel {channel!r} must be finite "
                    f"and > 0, got {mean!r}"
                )


def _is_positive_finite(value: float) -> bool:
    return math.isfinite(value) and value > 0.0


def compute_scale_factors(df: pd.DataFrame, channels: list[str]) -> ScaleFactors:
    """Revenue mean and per-channel mean of strictly positive spend weeks.

    Implements: MD-030

    An all-zero (or non-positive) channel raises `FitError` naming the channel —
    it cannot be scaled. Missing `spend_<channel>` columns also raise `FitError`.
    """
    if not channels:
        raise FitError("compute_scale_factors(): channels must be non-empty")
    if "revenue" not in df.columns:
        raise FitError("compute_scale_factors(): missing revenue column")
    if df.empty:
        raise FitError("compute_scale_factors(): frame is empty")

    revenue_mean = float(df["revenue"].to_numpy(dtype=float).mean())
    spend_means: dict[str, float] = {}
    for channel in channels:
        column = f"spend_{channel}"
        if column not in df.columns:
            raise FitError(f"compute_scale_factors(): missing column {column}")
        spend = df[column].to_numpy(dtype=float)
        positive = spend[spend > 0.0]
        if positive.size == 0:
            raise FitError(
                f"compute_scale_factors(): channel {channel!r} has no positive-spend "
                "weeks and cannot be scaled"
            )
        spend_means[channel] = float(positive.mean())
    return ScaleFactors(revenue_mean=revenue_mean, spend_means=spend_means)


def to_model_scale(df: pd.DataFrame, scale_factors: ScaleFactors) -> pd.DataFrame:
    """Divide revenue and listed-channel spend by the stored means (MD-030).

    Implements: MD-030

    Returns a copy. Spend columns not in `scale_factors.spend_means` are unchanged.
    """
    out = df.copy()
    out["revenue"] = out["revenue"] / scale_factors.revenue_mean
    for channel, mean in scale_factors.spend_means.items():
        column = f"spend_{channel}"
        if column not in out.columns:
            raise FitError(f"to_model_scale(): missing column {column}")
        out[column] = out[column] / mean
    return out


def from_model_scale(df: pd.DataFrame, scale_factors: ScaleFactors) -> pd.DataFrame:
    """Multiply scaled revenue and listed-channel spend back to level units.

    Implements: MD-030

    Exact inverse of `to_model_scale` for those columns (property-tested to 1e-12).
    The only back-transformation site (trap T-1).
    """
    out = df.copy()
    out["revenue"] = out["revenue"] * scale_factors.revenue_mean
    for channel, mean in scale_factors.spend_means.items():
        column = f"spend_{channel}"
        if column not in out.columns:
            raise FitError(f"from_model_scale(): missing column {column}")
        out[column] = out[column] * mean
    return out
