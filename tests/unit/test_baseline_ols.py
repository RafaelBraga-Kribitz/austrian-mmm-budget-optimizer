"""OLS+HC1 baseline tests (VR-601). No statsmodels. Does not run NUTS.

Implements: VR-601
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ambo.common.config import repo_root
from ambo.validate.baseline_ols import OLSResult, beta_mode, ols_hc1, run_ols


def test_textbook_two_regressor_hc1_to_1e8() -> None:
    design = np.array(
        [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0], [1.0, 3.0], [1.0, 4.0]],
        dtype=np.float64,
    )
    y = np.array([1.0, 1.5, 3.5, 3.0, 5.0], dtype=np.float64)
    coef, se = ols_hc1(design, y)
    expected_coef = np.array([0.9, 0.95], dtype=np.float64)
    expected_se = np.array([0.27808871486152276, 0.13447428502629527], dtype=np.float64)
    np.testing.assert_allclose(coef, expected_coef, atol=1e-8, rtol=0.0)
    np.testing.assert_allclose(se, expected_se, atol=1e-8, rtol=0.0)


def test_beta_mode_of_synthetic_lambda_prior() -> None:
    assert beta_mode(2.0, 4.0) == pytest.approx(0.25)


def test_no_statsmodels_import_in_src() -> None:
    src = repo_root() / "src"
    offenders: list[str] = []
    for path in src.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name.split(".")[0] == "statsmodels" for alias in node.names):
                    offenders.append(str(path.relative_to(repo_root())))
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] == "statsmodels":
                    offenders.append(str(path.relative_to(repo_root())))
    assert offenders == []


def test_ols_on_injected_frame_writes_json(tmp_path: Path) -> None:
    n_weeks = 40
    frame = pd.DataFrame(
        {
            "week_start": pd.date_range("2022-01-03", periods=n_weeks, freq="W-MON"),
            "revenue": np.linspace(80.0, 120.0, n_weeks),
            "promo_flag": np.resize([0.0, 1.0], n_weeks),
            "advent_flag": np.resize([0.0, 0.0, 1.0], n_weeks),
            "jan_dip_flag": np.resize([1.0, 0.0, 0.0, 0.0], n_weeks),
            "spend_meta": np.linspace(1.0, 5.0, n_weeks),
        }
    )
    dest = run_ols(
        "P-SB",
        frame=frame,
        bayesian_roas={"meta": 1.0},
        output_dir=tmp_path,
    )
    result = OLSResult.model_validate_json(dest.read_text(encoding="utf-8"))
    assert result.layer == "P-SB"
    assert "adstock_meta" in result.coef
    assert "adstock_meta" in result.se_hc1
    assert result.lambda_mode["meta"] == pytest.approx(0.25)
    assert result.n_obs == n_weeks
    assert result.n_params == 14
