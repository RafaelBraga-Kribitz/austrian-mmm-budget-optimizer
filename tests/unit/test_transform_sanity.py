"""MD-070 shared-shape transform sanity (T-302).

Implements: MD-070

The simulator uses raw geometric recursion (`adstock_recursive`); the model uses
a finite-length *normalized* convolution (`adstock_convolve`). That mismatch is
deliberate (MD-020). Equality is NOT expected. This test only asserts that, on
S-A spend at each channel's truth λ, the two adstock outputs (before Hill)
correlate above 0.95 — cheap detection of a reversed or off-by-one kernel (T-2).

Production packages still must not import each other; this test file may.
"""

from __future__ import annotations

import json

import numpy as np
import pytensor
import pytensor.tensor as pt

from ambo.common.config import load_settings
from ambo.common.db import read_dim_layer, read_mmm_input
from ambo.model.transforms import adstock_convolve
from ambo.simulate.dgp import adstock_recursive

# Same portable linker as test_transforms.py — unit tests must not need Python.h.
pytensor.config.cxx = ""

_MD070_MIN_CORR = 0.95
_LAYER = "P-SA"


def _truth_lambdas() -> dict[str, float]:
    path = load_settings().paths.data_synthetic / "s_a" / "truth.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["channel"]: float(row["lam"]) for row in payload["channels"]}


def _present_channels() -> list[str]:
    dim = read_dim_layer()
    raw = str(dim.set_index("layer").loc[_LAYER, "channels_present"])
    return [token for token in raw.split(",") if token]


def _model_adstock(spend: np.ndarray, lam: float, length: int) -> np.ndarray:
    x_sym = pt.vector("x")
    lam_sym = pt.scalar("lam")
    fn = pytensor.function([x_sym, lam_sym], adstock_convolve(x_sym, lam_sym, length))
    return np.asarray(fn(spend.astype(np.float64), np.float64(lam)), dtype=np.float64)


def test_md070_model_and_simulator_adstock_correlate_on_s_a() -> None:
    """Per-channel Pearson r > 0.95 on S-A spend. Equality is not expected."""
    frame = read_mmm_input(_LAYER)
    length = load_settings().adstock_length
    lambdas = _truth_lambdas()
    channels = _present_channels()
    assert len(channels) == 6, f"expected six S-A channels, got {channels!r}"

    scores: dict[str, float] = {}
    for channel in channels:
        spend = frame[f"spend_{channel}"].to_numpy(dtype=np.float64)
        lam = lambdas[channel]
        simulated = adstock_recursive(spend, lam)
        modeled = _model_adstock(spend, lam, length)
        corr = float(np.corrcoef(simulated, modeled)[0, 1])
        scores[channel] = corr
        assert corr > _MD070_MIN_CORR, (
            f"{channel}: r={corr:.6f} is not > {_MD070_MIN_CORR} (MD-070). "
            "A reversed or off-by-one kernel is the usual cause; do not force "
            "equality with the recursive DGP (MD-020)."
        )
    print("MD-070 correlations:", scores)
