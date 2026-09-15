"""Model builder tests: scaling, Fourier, compile. Sampling is marked slow."""

from __future__ import annotations

import numpy as np
import pytest

from ambo.config import CHANNEL_IDS
from ambo.model import build_model, fourier_features, scale_frame
from ambo.synth import adstock_recursive, generate, modeling_frame
from ambo.transforms import adstock


def test_scale_frame_round_trip_means():
    frame = modeling_frame(generate(seed=101, n_weeks=30))
    scaled, factors = scale_frame(frame)
    assert scaled["revenue"].mean() == pytest.approx(1.0)
    assert factors.revenue_mean == pytest.approx(frame["revenue"].mean())
    for channel in CHANNEL_IDS:
        x = frame[f"spend_{channel}"].to_numpy(dtype=float)
        nonzero = x[x > 0]
        if nonzero.size:
            assert factors.spend_means[channel] == pytest.approx(float(nonzero.mean()))


def test_fourier_features_shape():
    sin_feat, cos_feat = fourier_features(52)
    assert sin_feat.shape == (52, 4)
    assert cos_feat.shape == (52, 4)


def test_build_model_compiles():
    frame = modeling_frame(generate(seed=101, n_weeks=24))
    scaled, _ = scale_frame(frame)
    model = build_model(scaled)
    names = {rv.name for rv in model.unobserved_RVs}
    assert "lam" in names
    assert "delta_holiday" in names
    assert "gamma_sin_offset" in names
    assert any(rv.name == "y" for rv in model.observed_RVs)


def test_shared_shape_adstock_correlates():
    """MD-070 analogue: recursive DGP vs truncated model weights, same λ."""
    sim = generate(seed=101)
    x = sim.spend["paid_search"].to_numpy(dtype=float)
    decay = 0.35
    rec = adstock_recursive(x, decay)
    trunc = adstock(x, decay, 8)
    rho = np.corrcoef(rec, trunc)[0, 1]
    assert rho > 0.95


@pytest.mark.slow
def test_smoke_sample_recovers_positive_media():
    from ambo.evaluate import compute_recovery
    from ambo.model import sample_model

    sim = generate(seed=101, n_weeks=40)
    frame = modeling_frame(sim)
    scaled, factors = scale_frame(frame)
    model = build_model(scaled)
    idata = sample_model(model, draws=50, tune=50, chains=2, seed=1, progressbar=False)
    result = compute_recovery(frame, idata, factors, sim.truth)
    assert result.n_draws == 100
    assert any(row.roas_median > 0 for row in result.channels)
