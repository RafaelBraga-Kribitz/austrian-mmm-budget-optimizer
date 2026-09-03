"""VR-401 holdout tests. Does not run NUTS.

Implements: VR-401
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ambo.common.config import repo_root
from ambo.common.errors import ValidationError
from ambo.model.fit import HOLDOUT_HORIZON as FIT_HORIZON
from ambo.model.fit import HOLDOUT_MIN_WEEKS as FIT_MIN
from ambo.model.posterior_io import PosteriorBundle
from ambo.model.transforms import ScaleFactors
from ambo.validate.holdout import (
    CSV_COLUMNS,
    HOLDOUT_HORIZON,
    HOLDOUT_MIN_WEEKS,
    run_holdout,
)

_CHANNEL = "meta"
_N_DRAWS = 40
_N_WEEKS = 65


def _frame() -> pd.DataFrame:
    revenue = np.full(_N_WEEKS, 50.0)
    revenue[-HOLDOUT_HORIZON:] = 100.0
    return pd.DataFrame(
        {
            "week_start": pd.date_range("2022-01-03", periods=_N_WEEKS, freq="W-MON"),
            "revenue": revenue,
            "promo_flag": 0.0,
            "advent_flag": 0.0,
            "jan_dip_flag": 0.0,
            f"spend_{_CHANNEL}": 1.0,
        }
    )


def _draws() -> pd.DataFrame:
    ones = np.ones(_N_DRAWS)
    data: dict[str, np.ndarray] = {
        "alpha": 2.0 * ones,
        "tau": 0.0 * ones,
        "delta_promo": 0.0 * ones,
        "delta_advent": 0.0 * ones,
        "delta_jan": 0.0 * ones,
        "sigma": 0.01 * ones,
        f"lam__{_CHANNEL}": 0.4 * ones,
        f"k__{_CHANNEL}": 1.0 * ones,
        f"s__{_CHANNEL}": 1.0 * ones,
        f"beta__{_CHANNEL}": 0.0 * ones,
    }
    for order in range(1, 5):
        data[f"gamma_sin__{order}"] = 0.0 * ones
        data[f"gamma_cos__{order}"] = 0.0 * ones
    return pd.DataFrame(data)


def _bundle(tmp_path: Path) -> PosteriorBundle:
    return PosteriorBundle(
        draws=_draws(),
        metadata={},
        scale_factors=ScaleFactors(revenue_mean=50.0, spend_means={_CHANNEL: 1.0}),
        path=tmp_path / "P-SA__holdout.parquet",
    )


def test_holdout_horizon_matches_fit() -> None:
    assert HOLDOUT_HORIZON == FIT_HORIZON == 13
    assert HOLDOUT_MIN_WEEKS == FIT_MIN == 65


def test_holdout_short_series_raises() -> None:
    short = _frame().iloc[:64]
    with pytest.raises(ValidationError, match="T >= 65"):
        run_holdout("P-SA", bundle=_bundle(Path(".")), frame=short, output_dir=Path("."))


def test_holdout_csv_schema_mape_coverage_and_beats_naive(tmp_path: Path) -> None:
    dest = run_holdout("P-SA", bundle=_bundle(tmp_path), frame=_frame(), output_dir=tmp_path)
    table = pd.read_csv(dest)
    assert list(table.columns) == list(CSV_COLUMNS)
    assert len(table) == HOLDOUT_HORIZON
    assert table["coverage_90"].notna().all()
    assert table["hdi_low"].notna().all() and table["hdi_high"].notna().all()
    model_mape = float(table["model_mape"].iloc[0])
    naive_mape = float(table["naive_mape"].iloc[0])
    assert model_mape < naive_mape
    assert 0.0 <= float(table["coverage_90"].iloc[0]) <= 1.0
    assert table["yhat_median"].median() == pytest.approx(100.0, abs=1.0)


def test_holdout_module_does_not_sample_or_import_dgp() -> None:
    source = (repo_root() / "src" / "ambo" / "validate" / "holdout.py").read_text(encoding="utf-8")
    assert "pm.sample(" not in source
    assert "simulate.dgp" not in source
    assert "from ambo.model.fit import run_fit" in source


@pytest.mark.parametrize("layer", ["P-SA", "P-SB"])
def test_committed_holdout_beats_naive_when_present(layer: str) -> None:
    path = repo_root() / "reports" / "model" / f"holdout_{layer}.csv"
    if not path.is_file():
        pytest.skip(f"{path.name} not generated yet")
    table = pd.read_csv(path)
    assert list(table.columns) == list(CSV_COLUMNS)
    assert table["coverage_90"].notna().all()
    assert float(table["model_mape"].iloc[0]) < float(table["naive_mape"].iloc[0])
