"""Holdout baselines: seasonal naive and ridge on data whose answer is known."""

import numpy as np
import pandas as pd
import pytest

from ambo import baselines


def test_mape_is_mean_absolute_percentage_error():
    assert baselines.mape(np.array([100.0, 200.0]), np.array([110.0, 180.0])) == pytest.approx(0.1)


def test_seasonal_naive_repeats_last_year_exactly_on_a_periodic_series():
    t = np.arange(156)
    y = 100.0 + 10.0 * np.sin(2 * np.pi * t / 52) + 0.01 * (t % 3)  # tiny residual spread
    fc = baselines.seasonal_naive(y, train_weeks=130)
    assert len(fc.yhat) == 26
    np.testing.assert_allclose(fc.yhat, y[130 - 52 : 156 - 52])
    assert np.all(fc.lo < fc.yhat) and np.all(fc.hi > fc.yhat)
    metrics = fc.metrics(y[130:])
    assert metrics["n_test"] == 26 and metrics["mape"] < 0.001


def test_seasonal_naive_needs_more_than_one_season():
    with pytest.raises(ValueError):
        baselines.seasonal_naive(np.ones(80), train_weeks=52)


def test_ridge_recovers_a_linear_spend_response():
    rng = np.random.default_rng(0)
    n = 120
    starts = pd.date_range("2023-01-02", periods=n, freq="7D")
    spend = rng.uniform(50, 150, size=n)
    revenue = 1000.0 + 3.0 * spend + rng.normal(0, 1.0, size=n)
    data = pd.DataFrame(
        {"week_start": starts.strftime("%Y-%m-%d"), "spend_A": spend, "revenue": revenue,
         "holiday": np.zeros(n)}
    )
    fc = baselines.ridge(data, ["A"], "holiday", train_weeks=100, alphas=[0.01, 1.0])
    assert fc.name.startswith("Ridge regression (alpha ")
    assert len(fc.yhat) == 20
    assert baselines.mape(revenue[100:], fc.yhat) < 0.01
    assert fc.metrics(revenue[100:])["coverage_90"] >= 0.6  # 20 weeks, 12 month dummies


def test_forecast_metrics_count_coverage():
    fc = baselines.Forecast("x", np.array([1.0, 2.0]), np.array([0.0, 2.5]), np.array([2.0, 3.0]))
    m = fc.metrics(np.array([1.0, 2.0]))
    assert m["coverage_90"] == 0.5 and m["interval_width_mean"] == pytest.approx(1.25)
