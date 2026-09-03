"""Tests for `ambo.validate.recovery` (T-401).

Implements: VR-301, VR-302, VR-303, VR-304, VR-305, VR-306

Numpy references live here, not in `src/` — they are the independent expected
values for constructed-posterior ROAS (D-06).
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from ambo.common.errors import AmboError, ValidationError
from ambo.model.posterior_io import PosteriorBundle
from ambo.model.transforms import ScaleFactors
from ambo.simulate.config import SeasonWeights
from ambo.simulate.truth import ChannelTruth, TruthFile
from ambo.validate.recovery import (
    compute_recovery,
    evaluate_gates,
    load_gate_table,
)

_LENGTH = 8
_N_DRAWS = 40
_CHANNEL = "meta"


def _numpy_adstock(x: np.ndarray, lam: float, length: int) -> np.ndarray:
    idx = np.arange(length, dtype=np.float64)
    weights = lam**idx
    weights = weights / weights.sum()
    return np.convolve(x, weights, mode="full")[: len(x)]


def _numpy_hill(a: np.ndarray, k: float, s: float) -> np.ndarray:
    floor = 1e-8
    a_safe = np.maximum(a, floor)
    k_safe = max(k, floor)
    return 1.0 / (1.0 + np.exp(-s * (np.log(a_safe) - np.log(k_safe))))


def _channel_truth(
    channel: str,
    *,
    lam: float,
    k: float,
    s: float,
    beta: float,
    true_avg_roas: float,
    contribution_share: float = 0.1,
) -> ChannelTruth:
    return ChannelTruth(
        channel=channel,
        lam=lam,
        K=k,
        s=s,
        beta=beta,
        half_life_weeks=1.0,
        total_spend_eur=1.0,
        mean_weekly_spend_eur=1.0,
        max_weekly_spend_eur=1.0,
        total_contribution_eur=1.0,
        contribution_share=contribution_share,
        true_avg_roas=true_avg_roas,
        true_marginal_roas_at_mean_spend=0.0,
        response_curve_spend_eur=(0.0,),
        response_curve_contribution_eur=(0.0,),
        platform_phi=None,
        platform_theta=None,
        platform_cpm=None,
        platform_roas=None,
    )


def _truth(channels: list[ChannelTruth], media_share: float = 0.2) -> TruthFile:
    return TruthFile(
        schema_version="1.0",
        scenario_id="s_a",
        weeks=16,
        seed=1,
        collinearity=False,
        start_iso_year=2022,
        start_iso_week=1,
        end_iso_year=2022,
        end_iso_week=16,
        zero_effect_channel=None,
        b0=1.0,
        growth=0.0,
        noise_share=0.1,
        aov_base=50.0,
        aov_advent_bonus=0.0,
        promo_multiplier=1.0,
        season_weights=SeasonWeights(
            advent=0.55, schulbeginn=0.25, spring=0.15, jan_dip=-0.2, summer_lull=-0.1
        ),
        total_revenue_eur=1000.0,
        total_media_contribution_eur=media_share * 1000.0,
        media_share_of_revenue=media_share,
        response_curve_grid_max_multiple=2.0,
        channels=tuple(channels),
    )


def _bundle_and_frame(
    channels: list[str],
    params: dict[str, dict[str, float]],
    *,
    n_weeks: int = 16,
    spend_value: float = 100.0,
    revenue_value: float = 1000.0,
) -> tuple[PosteriorBundle, pd.DataFrame]:
    data: dict[str, np.ndarray] = {}
    spend_means: dict[str, float] = {}
    frame_cols: dict[str, np.ndarray] = {
        "revenue": np.full(n_weeks, revenue_value, dtype=np.float64),
    }
    for name in channels:
        row = params[name]
        for key in ("lam", "k", "s", "beta"):
            data[f"{key}__{name}"] = np.full(_N_DRAWS, row[key], dtype=np.float64)
        frame_cols[f"spend_{name}"] = np.full(n_weeks, spend_value, dtype=np.float64)
        spend_means[name] = spend_value
    bundle = PosteriorBundle(
        draws=pd.DataFrame(data),
        metadata={},
        scale_factors=ScaleFactors(revenue_mean=revenue_value, spend_means=spend_means),
        path=Path("constructed.parquet"),
    )
    return bundle, pd.DataFrame(frame_cols)


def _expected_roas(
    *,
    lam: float,
    k: float,
    s: float,
    beta: float,
    spend: float,
    revenue_mean: float,
    n_weeks: int,
    length: int,
) -> float:
    x_scaled = np.full(n_weeks, spend / spend, dtype=np.float64)
    adstocked = _numpy_adstock(x_scaled, lam, length)
    m_eur = beta * _numpy_hill(adstocked, k, s) * revenue_mean
    return float(m_eur.sum() / (spend * n_weeks))


def test_constructed_posterior_roas_matches_numpy(tmp_path: Path) -> None:
    lam, k, s, beta = 0.5, 1.0, 1.0, 0.4
    expected = _expected_roas(
        lam=lam, k=k, s=s, beta=beta, spend=100.0, revenue_mean=1000.0, n_weeks=16, length=_LENGTH
    )
    bundle, frame = _bundle_and_frame(
        [_CHANNEL], {_CHANNEL: {"lam": lam, "k": k, "s": s, "beta": beta}}
    )
    truth = _truth([_channel_truth(_CHANNEL, lam=lam, k=k, s=s, beta=beta, true_avg_roas=expected)])
    metrics = compute_recovery(
        "P-SA",
        bundle=bundle,
        frame=frame,
        truth=truth,
        output_dir=tmp_path,
        adstock_length=_LENGTH,
    )
    got = metrics.channels[0].roas_median
    assert abs(got - expected) < 1e-8
    assert metrics.channels[0].in_hdi


def test_true_roas_outside_hdi_fails_vr301(tmp_path: Path) -> None:
    lam, k, s, beta = 0.5, 1.0, 1.0, 0.4
    expected = _expected_roas(
        lam=lam, k=k, s=s, beta=beta, spend=100.0, revenue_mean=1000.0, n_weeks=16, length=_LENGTH
    )
    bundle, frame = _bundle_and_frame(
        [_CHANNEL], {_CHANNEL: {"lam": lam, "k": k, "s": s, "beta": beta}}
    )
    truth = _truth(
        [_channel_truth(_CHANNEL, lam=lam, k=k, s=s, beta=beta, true_avg_roas=expected + 50.0)]
    )
    metrics = compute_recovery(
        "P-SA",
        bundle=bundle,
        frame=frame,
        truth=truth,
        output_dir=tmp_path,
        adstock_length=_LENGTH,
    )
    assert metrics.channels[0].in_hdi is False
    gates_path = tmp_path / "gates.yaml"
    gates_path.write_text(_one_channel_gates(min_in_hdi=1), encoding="utf-8")
    result = evaluate_gates(metrics, output_dir=tmp_path, gates_path=gates_path)
    vr301 = next(item for item in result.checks if item.gate == "VR-301")
    assert vr301.passed is False
    assert result.all_green is False


def test_zero_effect_curve_mae_is_none(tmp_path: Path) -> None:
    params = {"lam": 0.4, "k": 1.0, "s": 1.0, "beta": 0.0}
    bundle, frame = _bundle_and_frame(["display_video"], {"display_video": params})
    truth = _truth(
        [
            _channel_truth(
                "display_video",
                lam=0.4,
                k=1.0,
                s=1.0,
                beta=0.0,
                true_avg_roas=0.0,
                contribution_share=0.0,
            )
        ],
        media_share=0.0,
    )
    metrics = compute_recovery(
        "P-SC",
        bundle=bundle,
        frame=frame,
        truth=truth,
        output_dir=tmp_path,
        adstock_length=_LENGTH,
    )
    assert metrics.channels[0].mae_pct is None
    assert metrics.vr303_median_mae_pct is None
    assert metrics.vr304_p_roas_lt == pytest.approx(1.0)
    assert metrics.vr304_median_share == pytest.approx(0.0)


def test_half_life_ranking_print_radio_above_search(tmp_path: Path) -> None:
    names = ["print_regional", "radio", "search_brand", "search_generic"]
    params = {
        "print_regional": {"lam": 0.80, "k": 1.0, "s": 1.0, "beta": 0.2},
        "radio": {"lam": 0.75, "k": 1.0, "s": 1.0, "beta": 0.2},
        "search_brand": {"lam": 0.30, "k": 1.0, "s": 1.0, "beta": 0.2},
        "search_generic": {"lam": 0.20, "k": 1.0, "s": 1.0, "beta": 0.2},
    }
    bundle, frame = _bundle_and_frame(names, params)
    truths = [
        _channel_truth(
            name,
            lam=params[name]["lam"],
            k=1.0,
            s=1.0,
            beta=0.2,
            true_avg_roas=float(i + 1),
        )
        for i, name in enumerate(names)
    ]
    truth = _truth(truths)
    metrics = compute_recovery(
        "P-SA",
        bundle=bundle,
        frame=frame,
        truth=truth,
        output_dir=tmp_path,
        adstock_length=_LENGTH,
    )
    assert metrics.half_life_rank_ok is True
    swapped = {
        "print_regional": {"lam": 0.20, "k": 1.0, "s": 1.0, "beta": 0.2},
        "radio": {"lam": 0.20, "k": 1.0, "s": 1.0, "beta": 0.2},
        "search_brand": {"lam": 0.80, "k": 1.0, "s": 1.0, "beta": 0.2},
        "search_generic": {"lam": 0.75, "k": 1.0, "s": 1.0, "beta": 0.2},
    }
    bundle_bad, frame_bad = _bundle_and_frame(names, swapped)
    bad = compute_recovery(
        "P-SA",
        bundle=bundle_bad,
        frame=frame_bad,
        truth=truth,
        output_dir=tmp_path,
        adstock_length=_LENGTH,
    )
    assert bad.half_life_rank_ok is False


def test_gate_yaml_matches_spec05_section_3() -> None:
    """Independent copy of SPEC-05 §3 — the YAML is data, this test is the audit."""
    table = load_gate_table()
    assert table["P-SA"]["vr_301_min_in_hdi"] == 5
    assert table["P-SB"]["vr_301_min_in_hdi"] == 4
    assert table["P-SC"]["vr_301_min_in_hdi"] == 4
    assert table["P-SA"]["vr_302_min_spearman"] == pytest.approx(0.83)
    assert table["P-SB"]["vr_302_min_spearman"] == pytest.approx(0.7)
    assert table["P-SA"]["vr_302_gated"] is True
    assert table["P-SC"]["vr_302_gated"] is False
    assert table["P-SA"]["vr_303_max_mae_pct_per_channel"] == pytest.approx(15.0)
    assert table["P-SA"]["vr_303_max_mae_pct_median"] == pytest.approx(10.0)
    assert table["P-SB"]["vr_303_max_mae_pct_per_channel"] == pytest.approx(25.0)
    assert table["P-SB"]["vr_303_max_mae_pct_median"] == pytest.approx(15.0)
    assert table["P-SA"]["vr_303_gated"] is True
    assert table["P-SC"]["vr_303_gated"] is False
    assert table["P-SA"]["vr_304_gated"] is False
    assert table["P-SC"]["vr_304_gated"] is True
    assert table["P-SC"]["vr_304_channel"] == "display_video"
    assert table["P-SC"]["vr_304_roas_threshold"] == pytest.approx(0.2)
    assert table["P-SC"]["vr_304_min_prob"] == pytest.approx(0.7)
    assert table["P-SC"]["vr_304_max_median_share"] == pytest.approx(0.03)
    for layer in ("P-SA", "P-SB", "P-SC"):
        assert table[layer]["vr_305_required"] is True
        assert table[layer]["vr_306_max_share_delta"] == pytest.approx(0.10)
        assert table[layer]["n_channels"] == 6


def test_metrics_json_round_trip(tmp_path: Path) -> None:
    lam, k, s, beta = 0.5, 1.0, 1.0, 0.4
    expected = _expected_roas(
        lam=lam, k=k, s=s, beta=beta, spend=100.0, revenue_mean=1000.0, n_weeks=16, length=_LENGTH
    )
    bundle, frame = _bundle_and_frame(
        [_CHANNEL], {_CHANNEL: {"lam": lam, "k": k, "s": s, "beta": beta}}
    )
    truth = _truth([_channel_truth(_CHANNEL, lam=lam, k=k, s=s, beta=beta, true_avg_roas=expected)])
    metrics = compute_recovery(
        "P-SA",
        bundle=bundle,
        frame=frame,
        truth=truth,
        output_dir=tmp_path,
        adstock_length=_LENGTH,
    )
    path = tmp_path / "metrics_P-SA.json"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "\r" not in text
    reloaded = type(metrics).model_validate_json(path.read_text(encoding="utf-8"))
    assert reloaded.channels[0].roas_median == pytest.approx(metrics.channels[0].roas_median)


def test_unknown_layer_raises() -> None:
    with pytest.raises(ValidationError, match="unknown layer"):
        compute_recovery("R")
    assert issubclass(ValidationError, AmboError)


def test_validate_does_not_import_simulate_dgp(repo_root: Path) -> None:
    offenders: list[str] = []
    for py_file in (repo_root / "src" / "ambo" / "validate").rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            if any(
                name == "ambo.simulate.dgp" or name.startswith("ambo.simulate.dgp.")
                for name in names
            ):
                offenders.append(py_file.as_posix())
    assert not offenders


def _one_channel_gates(*, min_in_hdi: int) -> str:
    payload = {
        "P-SA": {
            "n_channels": 1,
            "vr_301_min_in_hdi": min_in_hdi,
            "vr_302_min_spearman": 0.83,
            "vr_302_gated": False,
            "vr_303_max_mae_pct_per_channel": 15.0,
            "vr_303_max_mae_pct_median": 10.0,
            "vr_303_gated": False,
            "vr_304_gated": False,
            "vr_305_required": False,
            "vr_306_max_share_delta": 0.10,
        }
    }
    return yaml.safe_dump(payload)
