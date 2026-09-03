"""The only legal `pm.sample` home (D-11 / MD-050).

Implements: MD-050

Sampler kwargs come from the caller (who reads `Settings.sampler`). This module
does not restate MD-050 literals.
"""

from __future__ import annotations

from typing import Any

import arviz as az
import pymc as pm

from ambo.common.logging import get_logger

LOGGER = get_logger(__name__)


def sample_model(
    model: pm.Model,
    *,
    draws: int,
    tune: int,
    chains: int,
    target_accept: float,
    random_seed: int,
    init: str,
    **kwargs: Any,
) -> az.InferenceData:
    """Run NUTS via the single `pm.sample` call site."""
    LOGGER.info(
        "sample_model: starting NUTS (chains=%s tune=%s draws=%s)",
        chains,
        tune,
        draws,
    )
    with model:
        idata: az.InferenceData = pm.sample(
            draws=draws,
            tune=tune,
            chains=chains,
            target_accept=target_accept,
            random_seed=random_seed,
            init=init,
            **kwargs,
        )
    LOGGER.info("sample_model: NUTS finished")
    return idata
