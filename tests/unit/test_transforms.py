"""Tests for `ambo.model.transforms` (T-301).

Implements: MD-020, MD-021, MD-030

Numpy reference implementations live here, not in `src/` (T-301 notes). Impulse
causality is asserted before any "looks smooth" check (trap T-2).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytensor
import pytensor.tensor as pt
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ambo.common.errors import AmboError, FitError
from ambo.model.transforms import (
    ScaleFactors,
    adstock_convolve,
    compute_scale_factors,
    from_model_scale,
    geometric_adstock_weights,
    hill_saturation,
    to_model_scale,
)

# Unit tests must not depend on a C toolchain / Python.h (R-10 class of
# failure). Production sampling still uses PyTensor's default C linker when
# cxx is available.
pytensor.config.cxx = ""

_LENGTH = 8
_PT_ATOL = 1e-10
_SCALE_ATOL = 1e-12


def numpy_geometric_adstock_weights(lam: float, length: int) -> np.ndarray:
    """Independent numpy reference — not imported from src."""
    idx = np.arange(length, dtype=np.float64)
    weights = lam**idx
    return weights / weights.sum()


def numpy_adstock_convolve(x: np.ndarray, lam: float, length: int) -> np.ndarray:
    weights = numpy_geometric_adstock_weights(lam, length)
    return np.convolve(x, weights, mode="full")[: len(x)]


def numpy_hill(a: np.ndarray, k: float, s: float) -> np.ndarray:
    floor = 1e-8
    a_safe = np.maximum(a, floor)
    k_safe = max(k, floor)
    return 1.0 / (1.0 + np.exp(-s * (np.log(a_safe) - np.log(k_safe))))


def _eval_adstock(x: np.ndarray, lam: float, length: int) -> np.ndarray:
    x_sym = pt.vector("x")
    lam_sym = pt.scalar("lam")
    fn = pytensor.function([x_sym, lam_sym], adstock_convolve(x_sym, lam_sym, length))
    return np.asarray(fn(x.astype(np.float64), np.float64(lam)), dtype=np.float64)


def _eval_weights(lam: float, length: int) -> np.ndarray:
    lam_sym = pt.scalar("lam")
    fn = pytensor.function([lam_sym], geometric_adstock_weights(lam_sym, length))
    return np.asarray(fn(np.float64(lam)), dtype=np.float64)


def _eval_hill(a: np.ndarray, k: float, s: float) -> np.ndarray:
    a_sym = pt.vector("a")
    k_sym = pt.scalar("K")
    s_sym = pt.scalar("s")
    fn = pytensor.function([a_sym, k_sym, s_sym], hill_saturation(a_sym, k_sym, s_sym))
    return np.asarray(
        fn(a.astype(np.float64), np.float64(k), np.float64(s)),
        dtype=np.float64,
    )


def test_adstock_impulse_response_is_causal() -> None:
    x = np.zeros(50, dtype=np.float64)
    x[10] = 1000.0
    lam = 0.6
    got = _eval_adstock(x, lam, _LENGTH)
    weights = numpy_geometric_adstock_weights(lam, _LENGTH)
    assert (got[:10] == 0.0).all()
    for lag in range(_LENGTH):
        assert got[10 + lag] == pytest.approx(1000.0 * weights[lag], abs=_PT_ATOL)


def test_adstock_weights_sum_to_one() -> None:
    weights = _eval_weights(0.6, _LENGTH)
    assert weights.sum() == pytest.approx(1.0, abs=_PT_ATOL)
    assert weights.shape == (_LENGTH,)


def test_adstock_pytensor_matches_numpy_reference() -> None:
    rng = np.random.default_rng(20260903)
    x = rng.random(80)
    lam = 0.55
    got = _eval_adstock(x, lam, _LENGTH)
    expected = numpy_adstock_convolve(x, lam, _LENGTH)
    np.testing.assert_allclose(got, expected, atol=_PT_ATOL, rtol=0.0)


def test_adstock_length_less_than_one_raises_fit_error() -> None:
    with pytest.raises(FitError, match="L must be >= 1"):
        geometric_adstock_weights(pt.scalar("lam"), 0)


def test_src_transforms_does_not_import_simulator_or_settings(repo_root: Path) -> None:
    text = (repo_root / "src" / "ambo" / "model" / "transforms.py").read_text(encoding="utf-8")
    assert "np.convolve" not in text
    assert "lfilter" not in text
    assert "from ambo.simulate" not in text
    assert "import ambo.simulate" not in text
    assert "load_settings" not in text


def test_hill_at_k_is_exactly_half() -> None:
    k, s = 800.0, 1.2
    got = _eval_hill(np.array([k]), k, s)
    assert got[0] == pytest.approx(0.5, abs=1e-12)


def test_hill_at_zero_is_zero() -> None:
    got = _eval_hill(np.array([0.0]), 100.0, 1.1)
    assert got[0] == pytest.approx(0.0, abs=1e-8)


def test_hill_pytensor_matches_numpy_reference() -> None:
    a = np.linspace(0.0, 5000.0, 40)
    got = _eval_hill(a, k=2000.0, s=1.1)
    expected = numpy_hill(a, k=2000.0, s=1.1)
    np.testing.assert_allclose(got, expected, atol=_PT_ATOL, rtol=0.0)


def _spend_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "revenue": [100.0, 200.0, 300.0],
            "spend_meta": [10.0, 0.0, 20.0],
            "spend_radio": [5.0, 5.0, 5.0],
            "spend_other": [0.0, 0.0, 0.0],
        }
    )


def test_compute_scale_factors_uses_nonzero_week_mean() -> None:
    sf = compute_scale_factors(_spend_frame(), ["meta", "radio"])
    assert sf.revenue_mean == pytest.approx(200.0)
    assert sf.spend_means["meta"] == pytest.approx(15.0)
    assert sf.spend_means["radio"] == pytest.approx(5.0)


def test_all_zero_channel_raises_fit_error() -> None:
    with pytest.raises(FitError, match="other"):
        compute_scale_factors(_spend_frame(), ["meta", "other"])


def test_missing_spend_column_raises_fit_error() -> None:
    with pytest.raises(FitError, match="spend_print_regional"):
        compute_scale_factors(_spend_frame(), ["print_regional"])


def test_scale_factors_rejects_non_positive_revenue() -> None:
    with pytest.raises(FitError, match="revenue_mean"):
        ScaleFactors(revenue_mean=0.0, spend_means={"meta": 1.0})


def test_fit_error_is_ambo_error() -> None:
    assert issubclass(FitError, AmboError)


def test_scale_round_trip_is_exact_to_1e_12() -> None:
    frame = _spend_frame().drop(columns=["spend_other"])
    sf = compute_scale_factors(frame, ["meta", "radio"])
    restored = from_model_scale(to_model_scale(frame, sf), sf)
    np.testing.assert_allclose(
        restored["revenue"].to_numpy(dtype=float),
        frame["revenue"].to_numpy(dtype=float),
        atol=_SCALE_ATOL,
        rtol=0.0,
    )
    np.testing.assert_allclose(
        restored["spend_meta"].to_numpy(dtype=float),
        frame["spend_meta"].to_numpy(dtype=float),
        atol=_SCALE_ATOL,
        rtol=0.0,
    )
    np.testing.assert_allclose(
        restored["spend_radio"].to_numpy(dtype=float),
        frame["spend_radio"].to_numpy(dtype=float),
        atol=_SCALE_ATOL,
        rtol=0.0,
    )


def test_to_model_scale_does_not_mutate_input() -> None:
    frame = _spend_frame().drop(columns=["spend_other"])
    original = frame["revenue"].to_numpy(dtype=float).copy()
    sf = compute_scale_factors(frame, ["meta"])
    to_model_scale(frame, sf)
    np.testing.assert_array_equal(frame["revenue"].to_numpy(dtype=float), original)


@given(
    revenue=st.lists(
        st.floats(min_value=1.0, max_value=1e6, allow_nan=False), min_size=3, max_size=8
    ),
    spend=st.lists(
        st.floats(min_value=0.1, max_value=1e5, allow_nan=False), min_size=3, max_size=8
    ),
)
@settings(max_examples=25, deadline=None)
def test_scale_round_trip_property(revenue: list[float], spend: list[float]) -> None:
    n = min(len(revenue), len(spend))
    frame = pd.DataFrame({"revenue": revenue[:n], "spend_meta": spend[:n]})
    sf = compute_scale_factors(frame, ["meta"])
    restored = from_model_scale(to_model_scale(frame, sf), sf)
    np.testing.assert_allclose(
        restored.to_numpy(dtype=float),
        frame.to_numpy(dtype=float),
        atol=_SCALE_ATOL,
        rtol=_SCALE_ATOL,
    )
