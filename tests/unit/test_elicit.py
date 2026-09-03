"""Tests for `ambo.model.elicit` (T-308 / MD-060). Does not invent Layer R content.

Implements: MD-060
"""

from __future__ import annotations

import doctest
import math

import pytest
from scipy.special import betainc, gammainc

from ambo.common.config import repo_root
from ambo.common.errors import FitError
from ambo.model import elicit
from ambo.model.elicit import (
    beta_params_from_halflife_range,
    gamma_params_from_k_range,
    halflife_from_lambda,
    lambda_from_halflife,
    sigma_beta_from_max_effect_share,
)


def test_lambda_halflife_round_trip() -> None:
    for weeks in (0.5, 1.0, 2.0, 8.0, 20.0):
        lam = lambda_from_halflife(weeks)
        assert 0.0 < lam < 1.0
        assert math.isclose(halflife_from_lambda(lam), weeks, rel_tol=1e-12)


def test_longer_halflife_implies_larger_lambda() -> None:
    assert lambda_from_halflife(8.0) > lambda_from_halflife(2.0) > lambda_from_halflife(1.0)


def test_beta_params_place_90_percent_mass_in_range() -> None:
    lo_wk, hi_wk = 1.0, 4.0
    params = beta_params_from_halflife_range(lo_wk, hi_wk)
    lam_lo = lambda_from_halflife(lo_wk)
    lam_hi = lambda_from_halflife(hi_wk)
    mass = float(betainc(params.a, params.b, lam_hi) - betainc(params.a, params.b, lam_lo))
    assert abs(mass - 0.9) <= 0.01
    mode = (params.a - 1.0) / (params.a + params.b - 2.0)
    assert lam_lo < mode < lam_hi


def test_gamma_params_place_90_percent_mass_in_range() -> None:
    lo, hi = 1.0, 3.0
    params = gamma_params_from_k_range(lo, hi)
    mass = float(
        gammainc(params.shape, hi * params.rate) - gammainc(params.shape, lo * params.rate)
    )
    assert abs(mass - 0.9) <= 0.01
    mode = (params.shape - 1.0) / params.rate
    assert math.isclose(mode, 0.5 * (lo + hi), rel_tol=1e-9)


def test_beta_mode_moves_with_halflife_range() -> None:
    short = beta_params_from_halflife_range(1.0, 3.0)
    long = beta_params_from_halflife_range(4.0, 8.0)
    mode_short = (short.a - 1.0) / (short.a + short.b - 2.0)
    mode_long = (long.a - 1.0) / (long.a + long.b - 2.0)
    assert mode_long > mode_short


def test_sigma_beta_increases_with_share() -> None:
    low = sigma_beta_from_max_effect_share(0.10)
    high = sigma_beta_from_max_effect_share(0.20)
    assert high == pytest.approx(2.0 * low)
    assert low > 0.0


def test_invalid_ranges_raise_fit_error() -> None:
    with pytest.raises(FitError, match="half-life"):
        beta_params_from_halflife_range(4.0, 1.0)
    with pytest.raises(FitError, match="K"):
        gamma_params_from_k_range(0.0, 2.0)
    with pytest.raises(FitError, match="share"):
        sigma_beta_from_max_effect_share(-0.1)


def test_prior_elicitation_doc_is_not_invented() -> None:
    assert not (repo_root() / "docs" / "PRIOR_ELICITATION.md").is_file()


def test_elicit_doctests() -> None:
    result = doctest.testmod(elicit)
    assert result.failed == 0
    assert result.attempted >= 3
