"""Tests for `ambo.model.mmm` (T-304).

Implements: MD-001, MD-002
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pymc as pm
import pytensor
import pytest

from ambo.common.config import repo_root
from ambo.common.errors import FitError
from ambo.model.mmm import FOURIER_ORDER, FOURIER_PERIOD_WEEKS, build_model
from ambo.model.priors import SYNTHETIC_PRIORS_RELATIVE, PriorConfig, load_priors

pytensor.config.cxx = ""

_FREE_RV_NAMES = frozenset(
    {
        "alpha",
        "tau",
        "gamma_sin",
        "gamma_cos",
        "delta_promo",
        "delta_advent",
        "delta_jan",
        "lam",
        "k",
        "s",
        "beta",
        "sigma",
    }
)

_FORBIDDEN_LITERALS = ("P-SA", "P-SB", "P-SC", "S-A", "S-B", "S-C")


def _priors() -> PriorConfig:
    return load_priors(repo_root() / SYNTHETIC_PRIORS_RELATIVE)


def _tiny_scaled_frame(n_weeks: int = 24) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "revenue": rng.normal(1.0, 0.08, n_weeks).clip(0.3, None),
            "spend_meta": rng.gamma(2.0, 0.4, n_weeks),
            "spend_radio": rng.gamma(2.0, 0.4, n_weeks),
            "promo_flag": rng.integers(0, 2, n_weeks),
            "advent_flag": np.zeros(n_weeks, dtype=int),
            "jan_dip_flag": np.zeros(n_weeks, dtype=int),
        }
    )


def test_fourier_constants_match_spec_04() -> None:
    assert FOURIER_PERIOD_WEEKS == 52.18
    assert FOURIER_ORDER == 4


def test_free_rv_names_match_d06() -> None:
    model = build_model(_tiny_scaled_frame(), ["meta", "radio"], _priors())
    names = {rv.name for rv in model.free_RVs}
    assert names == _FREE_RV_NAMES


def test_mmm_source_has_no_scenario_or_layer_literals() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "ambo" / "model" / "mmm.py"
    text = source.read_text(encoding="utf-8")
    for token in _FORBIDDEN_LITERALS:
        assert token not in text, f"{token!r} found in mmm.py"
    assert re.search(r"\blayer\b", text) is None, "word 'layer' found in mmm.py"


def test_missing_spend_column_raises_fit_error() -> None:
    frame = _tiny_scaled_frame().drop(columns=["spend_radio"])
    with pytest.raises(FitError, match="spend_radio"):
        build_model(frame, ["meta", "radio"], _priors())


def test_prior_predictive_mean_is_within_order_of_observed() -> None:
    frame = _tiny_scaled_frame()
    model = build_model(frame, ["meta", "radio"], _priors())
    with model:
        idata = pm.sample_prior_predictive(draws=40, random_seed=1)
    prior_mean = float(idata.prior_predictive["y"].mean())
    observed_mean = float(frame["revenue"].mean())
    ratio = prior_mean / observed_mean
    assert 0.2 <= ratio <= 5.0, f"prior mean / observed mean = {ratio:.3f}"
