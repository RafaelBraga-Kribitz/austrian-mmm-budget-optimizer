"""Media response transforms used by the model: geometric adstock and Hill saturation.

Two implementations live here on purpose. The numpy functions are the reference
used by tests and by every reporting routine (holdout prediction, contribution
decomposition, response curves, optimiser). The pytensor functions build the same
maths into the PyMC graph. The synthetic data generator in ``ambo.synth`` has its
own, independently written adstock and Hill so that parameter recovery is evidence
rather than a tautology.

Conventions
-----------
* Adstock carries effect forward: ``a[t] = x[t] + decay * a[t-1]``. The model uses a
  truncated convolution with weights ``w_i = λ^i / Σ_{i=0..L-1} λ^i`` (MD-020).
  Unit-sum weights keep β interpretable as saturated contribution; at constant
  spend the steady-state adstock equals the spend itself. Pass ``normalize=False``
  to recover the unnormalised recursion used by the DGP-shape unit tests.
* Hill saturation: ``a ** slope / (a ** slope + k ** slope)``, equal to one half at
  ``a == k``. The pytensor version is evaluated in log space with a small positive
  floor so gradients stay finite at zero spend.

Implements: MD-020, MD-021.
"""

from __future__ import annotations

import numpy as np
import pytensor.tensor as pt

from ambo.config import ADSTOCK_NORMALIZE

HILL_FLOOR = 1e-8


def _normalize_flag(normalize: bool | None) -> bool:
    return ADSTOCK_NORMALIZE if normalize is None else bool(normalize)


def adstock_weights(decay: float, length: int, *, normalize: bool | None = None) -> np.ndarray:
    """Weights ``decay ** i`` for lags ``0 .. length-1``.

    With ``normalize=True`` (MD-020 default via config) the weights sum to one.
    """
    if length < 1:
        raise ValueError("adstock length must be at least 1")
    weights = np.asarray(decay, dtype=float) ** np.arange(length)
    if _normalize_flag(normalize):
        total = float(weights.sum())
        if total <= 0.0:
            raise ValueError("adstock weight sum must be positive")
        weights = weights / total
    return weights


def adstock_steady_state_gain(
    decay: float, length: int, *, normalize: bool | None = None
) -> float:
    """Multiplier from constant spend ``x`` to constant adstocked spend.

    MD-020 normalised weights: gain is 1 (steady state equals ``x``). Unnormalised
    truncated geometric: ``sum_{i=0}^{L-1} decay**i``.
    """
    if _normalize_flag(normalize):
        return 1.0
    return float(np.sum(np.asarray(decay, dtype=float) ** np.arange(length)))


def adstock(
    x: np.ndarray, decay: float, length: int, *, normalize: bool | None = None
) -> np.ndarray:
    """Truncated geometric adstock of a 1-d series (numpy reference).

    ``out[t] = sum_{i=0}^{length-1} w_i * x[t-i]`` with ``x[t-i] = 0`` for
    ``t - i < 0``. Unnormalised (``normalize=False``) equals the recursion
    ``a[t] = x[t] + decay * a[t-1]`` when ``length`` is at least the series length.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError("adstock expects a 1-d series")
    weights = adstock_weights(decay, length, normalize=normalize)
    out = np.zeros_like(x)
    for lag, weight in enumerate(weights):
        if lag == 0:
            out += weight * x
        else:
            out[lag:] += weight * x[:-lag]
    return out


def hill(a: np.ndarray, k: float, slope: float) -> np.ndarray:
    """Hill saturation (numpy reference): ``a^s / (a^s + k^s)``."""
    a = np.maximum(np.asarray(a, dtype=float), 0.0)
    num = a**slope
    return num / (num + float(k) ** slope)


def adstock_pt(x, decay, length: int, *, normalize: bool | None = None):
    """Truncated geometric adstock as a pytensor graph (same maths as ``adstock``).

    Unrolled over ``length`` lags so the graph contains no scan. ``x`` is a 1-d
    tensor, ``decay`` a scalar tensor.
    """
    if length < 1:
        raise ValueError("adstock length must be at least 1")
    total = x
    weight_sum = decay * 0.0 + 1.0
    for lag in range(1, length):
        delayed = pt.concatenate([pt.zeros((lag,)), x[:-lag]])
        weight = decay**lag
        total = total + weight * delayed
        weight_sum = weight_sum + weight
    if _normalize_flag(normalize):
        return total / weight_sum
    return total


def hill_pt(a, k, slope):
    """Hill saturation as a pytensor graph, evaluated as ``sigmoid(s (log a - log k))``."""
    a_safe = pt.maximum(a, HILL_FLOOR)
    k_safe = pt.maximum(k, HILL_FLOOR)
    return pt.sigmoid(slope * (pt.log(a_safe) - pt.log(k_safe)))


def hill_marginal(a: np.ndarray, k: float, slope: float) -> np.ndarray:
    """Derivative of the Hill curve with respect to its input, numpy reference."""
    a = np.maximum(np.asarray(a, dtype=float), HILL_FLOOR)
    ks = float(k) ** slope
    num = slope * ks * a ** (slope - 1.0)
    den = (a**slope + ks) ** 2
    return num / den
