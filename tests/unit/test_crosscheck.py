"""pymc-marketing cross-check tests (VR-602). Does not run NUTS.

Implements: VR-602, MD-003
"""

from __future__ import annotations

import ast
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from ambo.common.config import repo_root
from ambo.model.transforms import ScaleFactors
from ambo.validate.crosscheck import (
    CONTROL_COLUMNS,
    CONTROL_MU,
    CONTROL_SIGMA,
    CORRELATION_GATE,
    EXPECTED_PYMC_MARKETING_VERSION,
    CrosscheckResult,
    build_crosscheck_mmm,
    channel_roas_medians,
    design_frame,
    installed_version,
    mapping_table,
    median_correlations,
    require_pinned_version,
    run_crosscheck,
)


def test_installed_version_matches_pin() -> None:
    assert installed_version() == EXPECTED_PYMC_MARKETING_VERSION
    assert require_pinned_version() == EXPECTED_PYMC_MARKETING_VERSION


def test_mapping_table_covers_required_rows() -> None:
    rows = {item.element: item for item in mapping_table()}
    assert "adstock form" in rows
    assert "saturation form" in rows
    assert rows["adstock form"].status == "matched"
    assert rows["saturation form"].status == "matched"
    unmatched = {item.element for item in mapping_table() if item.status == "unmatched"}
    assert "s / slope prior" in unmatched
    assert "yearly Fourier" in unmatched
    assert all(item.status in {"matched", "unmatched"} for item in mapping_table())


def test_control_prior_vectors_align() -> None:
    assert len(CONTROL_COLUMNS) == len(CONTROL_MU) == len(CONTROL_SIGMA) == 12


def test_identical_roas_vectors_correlate_at_one() -> None:
    values = {"search_brand": 3.0, "meta": 1.5, "radio": 0.4}
    pearson, spearman = median_correlations(values, values)
    assert pearson == pytest.approx(1.0)
    assert spearman == pytest.approx(1.0)


def test_design_frame_column_order() -> None:
    n_weeks = 8
    frame = pd.DataFrame(
        {
            "week_start": pd.date_range("2022-01-03", periods=n_weeks, freq="W-MON"),
            "revenue": np.linspace(80.0, 120.0, n_weeks),
            "promo_flag": 0.0,
            "advent_flag": 0.0,
            "jan_dip_flag": 0.0,
            "spend_meta": np.linspace(1.0, 4.0, n_weeks),
        }
    )
    designed = design_frame(frame, ["meta"])
    assert list(designed.columns) == ["week_start", "meta", *CONTROL_COLUMNS]
    assert designed["t_over_t"].iloc[-1] == pytest.approx(1.0)
    assert designed["meta"].iloc[0] == pytest.approx(1.0)


def test_channel_roas_from_constructed_idata() -> None:
    n_date = 10
    contrib = np.zeros((1, 4, n_date, 2), dtype=np.float64)
    contrib[..., 0] = 20.0
    contrib[..., 1] = 10.0
    posterior = xr.Dataset(
        {
            "channel_contribution_original_scale": xr.DataArray(
                contrib,
                dims=("chain", "draw", "date", "channel"),
                coords={
                    "chain": [0],
                    "draw": [0, 1, 2, 3],
                    "date": np.arange(n_date),
                    "channel": ["meta", "radio"],
                },
            )
        }
    )
    idata = az.InferenceData(posterior=posterior)
    spend = {"meta": 100.0, "radio": 200.0}
    roas = channel_roas_medians(idata, spend)
    assert roas["meta"] == pytest.approx(2.0)
    assert roas["radio"] == pytest.approx(0.5)


def test_injected_idata_writes_json_and_mapping(tmp_path: Path) -> None:
    n_weeks = 10
    frame = pd.DataFrame(
        {
            "week_start": pd.date_range("2022-01-03", periods=n_weeks, freq="W-MON"),
            "revenue": np.linspace(80.0, 120.0, n_weeks),
            "promo_flag": 0.0,
            "advent_flag": 0.0,
            "jan_dip_flag": 0.0,
            "spend_meta": np.full(n_weeks, 10.0),
            "spend_radio": np.full(n_weeks, 20.0),
        }
    )
    contrib = np.zeros((1, 2, n_weeks, 2), dtype=np.float64)
    contrib[..., 0] = 20.0
    contrib[..., 1] = 10.0
    posterior = xr.Dataset(
        {
            "channel_contribution_original_scale": xr.DataArray(
                contrib,
                dims=("chain", "draw", "date", "channel"),
                coords={
                    "chain": [0],
                    "draw": [0, 1],
                    "date": np.arange(n_weeks),
                    "channel": ["meta", "radio"],
                },
            )
        }
    )
    dest = run_crosscheck(
        "P-SB",
        frame=frame,
        bayesian_roas={"meta": 2.0, "radio": 0.5},
        idata=az.InferenceData(posterior=posterior),
        output_dir=tmp_path,
    )
    result = CrosscheckResult.model_validate_json(dest.read_text(encoding="utf-8"))
    assert result.gate_passed
    assert result.pearson == pytest.approx(1.0)
    assert result.spearman == pytest.approx(1.0)
    assert result.pymc_marketing_version == EXPECTED_PYMC_MARKETING_VERSION
    mapping = tmp_path / "crosscheck_mapping.md"
    text = mapping.read_text(encoding="utf-8")
    assert EXPECTED_PYMC_MARKETING_VERSION in text
    assert "adstock form" in text
    assert "PASS" in text


def test_build_mmm_is_geometric_hill() -> None:
    factors = ScaleFactors(revenue_mean=100.0, spend_means={"meta": 3.0, "radio": 4.0})
    mmm = build_crosscheck_mmm(["meta", "radio"], factors, length=8)
    assert mmm.__class__.__name__ == "MMM"
    assert mmm.adstock.__class__.__name__ == "GeometricAdstock"
    assert mmm.saturation.__class__.__name__ == "HillSaturation"
    assert mmm.adstock.l_max == 8
    assert mmm.adstock.normalize is True
    assert mmm.adstock_first is True
    assert mmm.yearly_seasonality is None


def test_crosscheck_source_does_not_call_pm_sample() -> None:
    source = (repo_root() / "src/ambo/validate/crosscheck.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "sample":
            continue
        callee = node.func.value
        if isinstance(callee, ast.Name) and callee.id in {"pm", "pymc"}:
            raise AssertionError("pm.sample in crosscheck.py; sampling must use MMM.fit")


def test_committed_psb_json_meets_gate_when_present() -> None:
    path = repo_root() / "reports" / "recovery" / "crosscheck_P-SB.json"
    if not path.is_file():
        pytest.skip("crosscheck_P-SB.json not committed yet")
    result = CrosscheckResult.model_validate_json(path.read_text(encoding="utf-8"))
    assert result.pymc_marketing_version == EXPECTED_PYMC_MARKETING_VERSION
    assert result.pearson >= CORRELATION_GATE
    assert result.spearman >= CORRELATION_GATE
    assert result.gate_passed
