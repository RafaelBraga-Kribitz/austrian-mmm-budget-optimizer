"""Two reference forecasters for the holdout comparison.

* Seasonal naive: this week's revenue equals the revenue 52 weeks earlier.
* Ridge regression on raw spend, month-of-year dummies, a linear trend and the
  control, with the penalty chosen on the last quarter of the training window.

Both return a point forecast, a 90 percent interval built from the training
residuals (normal approximation), and the same two metrics as the model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

Z90 = 1.6448536269514722


@dataclass
class Forecast:
    name: str
    yhat: np.ndarray
    lo: np.ndarray
    hi: np.ndarray

    def metrics(self, actual: np.ndarray) -> dict:
        return {
            "model": self.name,
            "mape": mape(actual, self.yhat),
            "coverage_90": float(np.mean((actual >= self.lo) & (actual <= self.hi))),
            "interval_width_mean": float(np.mean(self.hi - self.lo)),
            "n_test": int(len(actual)),
        }


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    return float(np.mean(np.abs(actual - predicted) / np.abs(actual)))


def seasonal_naive(revenue: np.ndarray, train_weeks: int, season: int = 52) -> Forecast:
    y = np.asarray(revenue, dtype=float)
    n = len(y)
    if train_weeks <= season:
        raise ValueError("seasonal naive needs more than one season of training data")
    yhat = y[train_weeks - season : n - season]
    resid = y[season:train_weeks] - y[:train_weeks - season]
    sd = float(np.std(resid, ddof=1))
    return Forecast("Seasonal naive", yhat, yhat - Z90 * sd, yhat + Z90 * sd)


def _design(data: pd.DataFrame, channels: list[str], control: str, n_train: int) -> np.ndarray:
    spend = np.column_stack([data[f"spend_{c}"].to_numpy(dtype=float) for c in channels])
    months = pd.to_datetime(data["week_start"]).dt.month.to_numpy()
    dummies = np.column_stack([(months == m).astype(float) for m in range(1, 13)])
    trend = np.arange(1, len(data) + 1, dtype=float)[:, None] / n_train
    ctrl = data[control].to_numpy(dtype=float)[:, None]
    return np.hstack([spend, dummies, trend, ctrl])


def _ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    """Closed-form ridge with an unpenalised intercept on centred data."""
    x_mean = x.mean(axis=0)
    y_mean = y.mean()
    xc, yc = x - x_mean, y - y_mean
    k = xc.shape[1]
    coef = np.linalg.solve(xc.T @ xc + alpha * np.eye(k), xc.T @ yc)
    intercept = y_mean - x_mean @ coef
    return coef, float(intercept)


def ridge(
    data: pd.DataFrame,
    channels: list[str],
    control: str,
    train_weeks: int,
    alphas: list[float],
) -> Forecast:
    y = data["revenue"].to_numpy(dtype=float)
    x = _design(data, channels, control, train_weeks)
    x_train, y_train = x[:train_weeks], y[:train_weeks]
    scale = x_train.std(axis=0)
    scale[scale == 0] = 1.0
    xs = x / scale
    n_val = max(8, train_weeks // 4)
    fit_end = train_weeks - n_val
    best_alpha, best_err = alphas[0], np.inf
    for alpha in alphas:
        coef, b0 = _ridge_fit(xs[:fit_end], y[:fit_end], alpha)
        err = mape(y[fit_end:train_weeks], xs[fit_end:train_weeks] @ coef + b0)
        if err < best_err:
            best_alpha, best_err = alpha, err
    coef, b0 = _ridge_fit(xs[:train_weeks], y_train, best_alpha)
    fitted = xs[:train_weeks] @ coef + b0
    sd = float(np.std(y_train - fitted, ddof=1))
    yhat = xs[train_weeks:] @ coef + b0
    name = f"Ridge regression (alpha {best_alpha:g})"
    return Forecast(name, yhat, yhat - Z90 * sd, yhat + Z90 * sd)
