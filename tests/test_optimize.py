"""Optimizer constraint audit (DC-704)."""

from __future__ import annotations

import numpy as np
import pytest

from ambo.config import CHANNEL_IDS, EXTRAPOLATION_MULT
from ambo.model import ScaleFactors
from ambo.optimize import optimize_budget


def _fake_draws(n_draws: int = 8, n_ch: int = 5) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(0)
    return {
        "lam": rng.uniform(0.2, 0.6, size=(n_draws, n_ch)),
        "k": rng.uniform(0.8, 1.6, size=(n_draws, n_ch)),
        "s": rng.uniform(0.8, 1.4, size=(n_draws, n_ch)),
        "beta": rng.uniform(0.05, 0.2, size=(n_draws, n_ch)),
    }


def test_optimal_allocation_respects_budget_and_caps():
    hist = np.array([100.0, 80.0, 60.0, 200.0, 150.0])
    maxima = np.array([400.0, 300.0, 250.0, 500.0, 400.0])
    scales = ScaleFactors(
        revenue_mean=80_000.0,
        spend_means={name: float(hist[i]) for i, name in enumerate(CHANNEL_IDS)},
        channels=CHANNEL_IDS,
    )
    result = optimize_budget(hist, maxima, _fake_draws(), scales, n_draws=8, n_restarts=4, seed=0)
    spent = np.array([result.spends[c] for c in CHANNEL_IDS])
    assert spent.sum() == pytest.approx(hist.sum(), rel=1e-5)
    assert np.all(spent >= -1e-6)
    assert np.all(spent <= EXTRAPOLATION_MULT * maxima + 1e-6)
