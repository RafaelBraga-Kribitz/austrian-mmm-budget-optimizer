"""Recovery helpers on a tiny constructed posterior."""

from __future__ import annotations

import arviz as az
import numpy as np
import xarray as xr

from ambo.config import CHANNEL_IDS
from ambo.evaluate import compute_recovery, hdi_interval
from ambo.model import ScaleFactors
from ambo.synth import generate, modeling_frame


def test_hdi_covers_mean_of_normal():
    rng = np.random.default_rng(0)
    samples = rng.normal(2.0, 0.1, size=2000)
    lo, hi = hdi_interval(samples, 0.9)
    assert lo < 2.0 < hi


def _idata_from_truth(truth: dict, n_draws: int = 20) -> az.InferenceData:
    n_ch = len(CHANNEL_IDS)
    lam = np.array([truth["channels"][c]["decay"] for c in CHANNEL_IDS])
    posterior = {
        "alpha": (("chain", "draw"), np.full((1, n_draws), 1.0)),
        "tau": (("chain", "draw"), np.zeros((1, n_draws))),
        "delta_holiday": (("chain", "draw"), np.zeros((1, n_draws))),
        "sigma": (("chain", "draw"), np.full((1, n_draws), 0.05)),
        "lam": (("chain", "draw", "channel"), np.broadcast_to(lam, (1, n_draws, n_ch))),
        "k": (("chain", "draw", "channel"), np.broadcast_to(np.ones(n_ch), (1, n_draws, n_ch))),
        "s": (("chain", "draw", "channel"), np.broadcast_to(np.ones(n_ch), (1, n_draws, n_ch))),
        "beta": (
            ("chain", "draw", "channel"),
            np.broadcast_to(np.full(n_ch, 0.1), (1, n_draws, n_ch)),
        ),
        "gamma_sin": (("chain", "draw", "fourier"), np.zeros((1, n_draws, 4))),
        "gamma_cos": (("chain", "draw", "fourier"), np.zeros((1, n_draws, 4))),
    }
    ds = xr.Dataset({name: (dims, values) for name, (dims, values) in posterior.items()})
    return az.InferenceData(posterior=ds)


def test_compute_recovery_returns_five_channels():
    sim = generate(seed=101, n_weeks=30)
    frame = modeling_frame(sim)
    spend_means = {}
    for channel in CHANNEL_IDS:
        x = frame[f"spend_{channel}"].to_numpy(dtype=float)
        positive = x[x > 0]
        spend_means[channel] = float(positive.mean()) if positive.size else 1.0
    scales = ScaleFactors(
        revenue_mean=float(frame["revenue"].mean()),
        spend_means=spend_means,
        channels=CHANNEL_IDS,
    )
    idata = _idata_from_truth(sim.truth)
    result = compute_recovery(frame, idata, scales, sim.truth)
    assert len(result.channels) == 5
    assert set(result.gates) == {"VR-301", "VR-302", "VR-303", "VR-305", "VR-306"}
