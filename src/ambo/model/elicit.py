"""Prior elicitation converters (MD-060). No Layer R content.

Implements: MD-060

Geometric-adstock half-life mapping: ``λ = 2 ** (-1 / weeks)``. Longer half-life
implies larger λ. Beta and Gamma concentrations are solved with ``brentq`` so
~90% of the prior mass sits in the elicited range, with the mode at the range
midpoint (mapped through the same transform). ``docs/PRIOR_ELICITATION.md`` is
not authored here.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from scipy.optimize import brentq
from scipy.special import betainc, erfinv, gammainc

from ambo.common.errors import FitError
from ambo.model.priors import BetaParams, GammaParams

# mypy: disable-error-code="no-untyped-call"

_TARGET_MASS = 0.90
_KAPPA_LO = 2.01
_KAPPA_HI = 500.0
_SHAPE_LO = 1.01
_SHAPE_HI = 200.0
# HalfNormal(1) 95th percentile: √2 · erfinv(0.95).
_HALF_NORMAL_P95 = math.sqrt(2.0) * float(erfinv(0.95))


def lambda_from_halflife(weeks: float) -> float:
    """Geometric-adstock λ for a half-life in weeks.

    Implements: MD-060

    >>> round(lambda_from_halflife(1.0), 6)
    0.5
    >>> lambda_from_halflife(2.0) > lambda_from_halflife(1.0)
    True
    """
    if not math.isfinite(weeks) or weeks <= 0.0:
        raise FitError(f"half-life must be finite and > 0, got {weeks!r}")
    return float(2.0 ** (-1.0 / weeks))


def halflife_from_lambda(lam: float) -> float:
    """Inverse of `lambda_from_halflife`.

    Implements: MD-060

    >>> round(halflife_from_lambda(0.5), 6)
    1.0
    """
    if not math.isfinite(lam) or not (0.0 < lam < 1.0):
        raise FitError(f"λ must be in (0, 1), got {lam!r}")
    return float(-1.0 / math.log2(lam))


def beta_params_from_halflife_range(lo_wk: float, hi_wk: float) -> BetaParams:
    """Beta(a, b) for λ with mode at λ(mid) and ~90% mass in [λ(lo), λ(hi)].

    Implements: MD-060

    Longer half-life ⇒ larger λ, so the mass interval is
    ``[lambda_from_halflife(lo_wk), lambda_from_halflife(hi_wk)]``.

    >>> params = beta_params_from_halflife_range(1.0, 4.0)
    >>> params.a > 1.0 and params.b > 1.0
    True
    """
    _require_ordered_positive_range(lo_wk, hi_wk, "half-life")
    lam_lo = lambda_from_halflife(lo_wk)
    lam_hi = lambda_from_halflife(hi_wk)
    mode = lambda_from_halflife(0.5 * (lo_wk + hi_wk))
    kappa = _solve_mass(
        lambda k: _beta_interval_mass(k, mode, lam_lo, lam_hi),
        lo=_KAPPA_LO,
        hi=_KAPPA_HI,
        label="Beta concentration",
    )
    return BetaParams(a=1.0 + mode * (kappa - 2.0), b=1.0 + (1.0 - mode) * (kappa - 2.0))


def gamma_params_from_k_range(lo: float, hi: float) -> GammaParams:
    """Gamma(shape, rate) for scaled K with mode at mid and ~90% mass in [lo, hi].

    Implements: MD-060

    >>> params = gamma_params_from_k_range(1.0, 3.0)
    >>> params.shape > 1.0 and params.rate > 0.0
    True
    """
    _require_ordered_positive_range(lo, hi, "K")
    mode = 0.5 * (lo + hi)

    def mass(shape: float) -> float:
        rate = (shape - 1.0) / mode
        return float(gammainc(shape, hi * rate) - gammainc(shape, lo * rate))

    shape = _solve_mass(mass, lo=_SHAPE_LO, hi=_SHAPE_HI, label="Gamma shape")
    return GammaParams(shape=shape, rate=(shape - 1.0) / mode)


def sigma_beta_from_max_effect_share(share: float) -> float:
    """HalfNormal σ whose 95th percentile equals `share` of mean scaled revenue.

    Implements: MD-060

    Mean scaled revenue is 1 by construction (T-1), so `share` is already in
    outcome units. Example: a 15% ceiling ⇒ σ ≈ 0.0765.

    >>> round(sigma_beta_from_max_effect_share(0.15), 4)
    0.0765
    """
    if not math.isfinite(share) or share <= 0.0:
        raise FitError(f"max-effect share must be finite and > 0, got {share!r}")
    return float(share / _HALF_NORMAL_P95)


def _require_ordered_positive_range(lo: float, hi: float, name: str) -> None:
    if not math.isfinite(lo) or not math.isfinite(hi) or lo <= 0.0 or hi <= 0.0:
        raise FitError(f"{name} range bounds must be finite and > 0, got [{lo}, {hi}]")
    if not (lo < hi):
        raise FitError(f"{name} range lower must be < upper, got [{lo}, {hi}]")


def _beta_interval_mass(kappa: float, mode: float, lam_lo: float, lam_hi: float) -> float:
    a = 1.0 + mode * (kappa - 2.0)
    b = 1.0 + (1.0 - mode) * (kappa - 2.0)
    return float(betainc(a, b, lam_hi) - betainc(a, b, lam_lo))


def _solve_mass(
    mass_at: Callable[[float], float],
    *,
    lo: float,
    hi: float,
    label: str,
) -> float:
    """brentq so mass_at(x) = 0.9. If even the most diffuse x already exceeds 0.9, use it."""
    f_lo = float(mass_at(lo)) - _TARGET_MASS
    f_hi = float(mass_at(hi)) - _TARGET_MASS
    if f_lo > 0.0:
        return lo
    if f_lo * f_hi > 0.0:
        raise FitError(
            f"{label}: cannot place ~90% mass in the elicited range "
            f"(mass at {lo:g}={f_lo + _TARGET_MASS:.3f}, at {hi:g}={f_hi + _TARGET_MASS:.3f})"
        )
    return float(brentq(lambda x: float(mass_at(x)) - _TARGET_MASS, lo, hi))
