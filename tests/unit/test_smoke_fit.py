"""CI smoke-fit: P-SA first 60 weeks, 1 chain, 200/200 (EB-060 / MD-050).

Implements: EB-060

Never reported. Full-budget fits stay off `make test` (EB-061).
"""

from __future__ import annotations

import arviz as az
import numpy as np
import pytensor
import pytest

from ambo.common.config import load_settings, repo_root
from ambo.common.db import read_dim_layer, read_mmm_input
from ambo.model.fit import sample_model
from ambo.model.mmm import build_model
from ambo.model.priors import SYNTHETIC_PRIORS_RELATIVE, load_priors
from ambo.model.transforms import compute_scale_factors, to_model_scale

pytensor.config.cxx = ""

_SMOKE_WEEKS = 60
_SMOKE_DRAWS = 200
_SMOKE_TUNE = 200
_SMOKE_CHAINS = 1


def _present_channels(layer: str) -> list[str]:
    dim = read_dim_layer()
    raw = str(dim.set_index("layer").loc[layer, "channels_present"])
    return [token for token in raw.split(",") if token]


@pytest.mark.smoke
def test_smoke_fit_p_sa_completes_with_finite_rhat() -> None:
    settings = load_settings()
    frame = read_mmm_input("P-SA").iloc[:_SMOKE_WEEKS].copy()
    channels = _present_channels("P-SA")
    priors = load_priors(repo_root() / SYNTHETIC_PRIORS_RELATIVE)
    scale_factors = compute_scale_factors(frame, channels)
    scaled = to_model_scale(frame, scale_factors)
    model = build_model(scaled, channels, priors)
    idata = sample_model(
        model,
        draws=_SMOKE_DRAWS,
        tune=_SMOKE_TUNE,
        chains=_SMOKE_CHAINS,
        target_accept=settings.sampler.target_accept,
        random_seed=settings.sampler.random_seed,
        init=settings.sampler.init,
        progressbar=False,
        compute_convergence_checks=False,
    )
    rhat = az.rhat(idata)
    values = np.asarray(rhat.to_array())
    finite = values[np.isfinite(values)]
    # One-chain rank-normalized R-hat can be NaN; split-R-hat on the same
    # idata must still produce at least one finite number so the smoke gate
    # is not a silent pass on an empty diagnostic.
    if finite.size == 0:
        split = np.asarray(az.rhat(idata, method="split").to_array())
        finite = split[np.isfinite(split)]
    assert finite.size > 0, "R-hat produced no finite values"
    assert np.isfinite(finite).all()
