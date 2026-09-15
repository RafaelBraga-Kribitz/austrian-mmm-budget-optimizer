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
  truncated version of that recursion, a causal convolution with weights
  ``decay ** i`` for ``i = 0 .. length-1``. With ``length`` 13 and a decay of 0.7 the
  dropped tail is below one percent of the steady-state value.
* Hill saturation: ``a ** slope / (a ** slope + k ** slope)``, equal to one half at
  ``a == k``. The pytensor version is evaluated in log space with a small positive
  floor so gradients stay finite at zero spend.
"""

from __future__ import annotations

import numpy as np
import pytensor.tensor as pt

HILL_FLOOR = 1e-8


def adstock_weights(decay: float, length: int) -> np.ndarray:
    """Weights ``decay ** i`` for lags ``0 .. length-1`` (unnormalised)."""
    if length < 1:
        raise ValueError("adstock length must be at least 1")
    return np.asarray(decay, dtype=float) ** np.arange(length)


def adstock(x: np.ndarray, decay: float, length: int) -> np.ndarray:
    """Truncated geometric adstock of a 1-d series (numpy reference).

    ``out[t] = sum_{i=0}^{length-1} decay**i * x[t-i]`` with ``x[t-i] = 0`` for
    ``t - i < 0``. Equals the recursion ``a[t] = x[t] + decay * a[t-1]`` when
    ``length`` is at least the series length.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError("adstock expects a 1-d series")
    weights = adstock_weights(decay, length)
    out = np.zeros_like(x)
    for lag, weight in enumerate(weights):
        if lag == 0:
            out += weight * x
        else:
            out[lag:] += weight * x[:-lag]
    return out


def hill(a: np.ndarray, k, slope) -> np.ndarray:
    """Hill saturation (numpy reference): ``a^s / (a^s + k^s)``.

    ``k`` and ``slope`` may be scalars or arrays that broadcast against ``a``.
    """
    a = np.maximum(np.asarray(a, dtype=float), 0.0)
    k = np.asarray(k, dtype=float)
    slope = np.asarray(slope, dtype=float)
    num = a**slope
    return num / (num + k**slope)


def adstock_pt(x, decay, length: int):
    """Truncated geometric adstock as a pytensor graph (same maths as ``adstock``).

    Unrolled over ``length`` lags so the graph contains no scan. ``x`` is a 1-d
    tensor, ``decay`` a scalar tensor.
    """
    if length < 1:
        raise ValueError("adstock length must be at least 1")
    total = x
    for lag in range(1, length):
        delayed = pt.concatenate([pt.zeros((lag,)), x[:-lag]])
        total = total + (decay**lag) * delayed
    return total


def hill_pt(a, k, slope):
    """Hill saturation as a pytensor graph, evaluated as ``sigmoid(s (log a - log k))``."""
    a_safe = pt.maximum(a, HILL_FLOOR)
    k_safe = pt.maximum(k, HILL_FLOOR)
    return pt.sigmoid(slope * (pt.log(a_safe) - pt.log(k_safe)))


def hill_marginal(a: np.ndarray, k, slope) -> np.ndarray:
    """Derivative of the Hill curve with respect to its input, numpy reference."""
    a = np.maximum(np.asarray(a, dtype=float), HILL_FLOOR)
    k = np.asarray(k, dtype=float)
    slope = np.asarray(slope, dtype=float)
    ks = k**slope
    num = slope * ks * a ** (slope - 1.0)
    den = (a**slope + ks) ** 2
    return num / den
