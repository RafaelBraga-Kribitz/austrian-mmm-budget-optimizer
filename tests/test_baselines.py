"""Textbook HC1 and OLS design (VR-601)."""

from __future__ import annotations

import numpy as np
import pytest

from ambo.baselines import beta_mode, fit_ols_baseline, ols_hc1
from ambo.synth import generate, modeling_frame


def test_beta_mode_of_2_4():
    assert beta_mode(2.0, 4.0) == pytest.approx(1.0 / 4.0)


def test_ols_hc1_matches_lstsq_and_positive_se():
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = 1.0 + 2.0 * x + np.array([0.1, -0.1, 0.2, -0.2])
    design = np.column_stack([np.ones(4), x])
    coef, se = ols_hc1(design, y)
    np.testing.assert_allclose(coef, np.linalg.lstsq(design, y, rcond=None)[0])
    assert np.all(se > 0)


def test_ols_runs_on_layer_p():
    frame = modeling_frame(generate(seed=101, n_weeks=80))
    roas = {name: 1.0 for name in ("tv", "radio", "print", "paid_search", "paid_social")}
    result = fit_ols_baseline(frame, bayesian_roas=roas)
    assert result.n_obs == 80
    assert "adstock_tv" in result.coef
    assert result.se_hc1["intercept"] >= 0
