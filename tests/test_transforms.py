"""Adstock and Hill saturation against hand-computed values on a 5-element vector."""

import numpy as np
import pytensor
import pytensor.tensor as pt
import pytest

from ambo.transforms import adstock, adstock_pt, hill, hill_marginal, hill_pt

X = np.array([10.0, 0.0, 5.0, 0.0, 0.0])


def test_adstock_matches_hand_computation():
    # decay 0.5, full length: a = [10, 5, 7.5, 3.75, 1.875]
    expected = np.array([10.0, 5.0, 7.5, 3.75, 1.875])
    np.testing.assert_allclose(adstock(X, 0.5, 5), expected)


def test_adstock_truncation_drops_old_lags():
    # length 2 keeps only lag 0 and lag 1: [10, 5, 5, 2.5, 0]
    np.testing.assert_allclose(adstock(X, 0.5, 2), np.array([10.0, 5.0, 5.0, 2.5, 0.0]))


def test_adstock_equals_recursion_when_length_covers_series():
    rng = np.random.default_rng(1)
    x = rng.gamma(2.0, 3.0, size=40)
    decay = 0.63
    rec = np.zeros_like(x)
    carry = 0.0
    for t, value in enumerate(x):
        carry = value + decay * carry
        rec[t] = carry
    np.testing.assert_allclose(adstock(x, decay, 40), rec, rtol=1e-12)


def test_hill_hand_values():
    a = np.array([0.0, 1.0, 2.0, 4.0, 8.0])
    # k = 2, slope = 1: a / (a + 2)
    np.testing.assert_allclose(hill(a, 2.0, 1.0), np.array([0.0, 1 / 3, 0.5, 2 / 3, 0.8]))
    # k = 2, slope = 2: a^2 / (a^2 + 4)
    np.testing.assert_allclose(hill(a, 2.0, 2.0), np.array([0.0, 0.2, 0.5, 0.8, 16 / 17]))


def test_hill_is_one_half_at_k():
    for k in (0.5, 3.0, 40.0):
        for s in (0.7, 1.0, 1.8):
            assert hill(np.array([k]), k, s)[0] == pytest.approx(0.5)


def test_pytensor_graphs_match_numpy_reference():
    x = pt.dvector("x")
    decay = pt.dscalar("decay")
    k = pt.dscalar("k")
    s = pt.dscalar("s")
    f_adstock = pytensor.function([x, decay], adstock_pt(x, decay, 5))
    f_hill = pytensor.function([x, k, s], hill_pt(x, k, s))
    np.testing.assert_allclose(f_adstock(X, 0.5), adstock(X, 0.5, 5), rtol=1e-12)
    a = np.array([0.0, 1.0, 2.0, 4.0, 8.0])
    np.testing.assert_allclose(f_hill(a, 2.0, 2.0), hill(a, 2.0, 2.0), atol=1e-7)


def test_hill_marginal_matches_finite_difference():
    a = np.array([0.5, 1.0, 2.0, 4.0, 8.0])
    k, s = 2.0, 1.3
    eps = 1e-6
    fd = (hill(a + eps, k, s) - hill(a - eps, k, s)) / (2 * eps)
    np.testing.assert_allclose(hill_marginal(a, k, s), fd, rtol=1e-5)
