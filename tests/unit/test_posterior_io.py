"""Tests for `ambo.model.posterior_io` (T-305 / MD-051).

Implements: MD-051, EB-050, BP-D-06
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pandas.testing import assert_frame_equal

from ambo.common.config import load_settings
from ambo.common.errors import FitError
from ambo.model.posterior_io import (
    _DEFAULT_THIN,
    _META_KEY,
    load_posterior,
    save_posterior,
)
from ambo.model.transforms import ScaleFactors

_CHANNELS = ("meta", "radio")
_DATA_HASH = "abc123"
_PRIOR_SHA = "def456"


def _scale_factors() -> ScaleFactors:
    return ScaleFactors(
        revenue_mean=100.0,
        spend_means={"meta": 10.0, "radio": 20.0},
    )


def _idata(n_chains: int = 4, n_draws: int = 1000) -> az.InferenceData:
    """Constructed idata: alpha[c, d] = c * n_draws + d so thinning is exact."""
    chain_idx = np.arange(n_chains, dtype=np.float64)[:, None]
    draw_idx = np.arange(n_draws, dtype=np.float64)[None, :]
    alpha = chain_idx * n_draws + draw_idx
    beta = np.stack([alpha, alpha + 0.5], axis=-1)
    return az.from_dict(
        posterior={"alpha": alpha, "beta": beta},
        coords={"channel": list(_CHANNELS)},
        dims={"beta": ["channel"]},
    )


def _save(tmp_path: Path, idata: az.InferenceData | None = None, **kwargs: Any) -> Path:
    params: dict[str, Any] = {
        "idata": idata if idata is not None else _idata(),
        "sf": _scale_factors(),
        "name": "P-SA",
        "data_hash": _DATA_HASH,
        "prior_sha256": _PRIOR_SHA,
        "directory": tmp_path,
    }
    params.update(kwargs)
    return save_posterior(**params)


def test_save_load_round_trip_draws_and_metadata(tmp_path: Path) -> None:
    dest = _save(tmp_path, thin=4)
    assert dest.name == "P-SA.parquet"
    bundle = load_posterior("P-SA", directory=tmp_path)

    expected = np.arange(0, 4 * 1000, 4, dtype=np.float64)
    assert len(bundle.draws) == 1000
    np.testing.assert_array_equal(bundle.draws["alpha"].to_numpy(), expected)
    assert "beta__meta" in bundle.draws.columns
    assert "beta__radio" in bundle.draws.columns

    assert bundle.metadata["data_hash"] == _DATA_HASH
    assert bundle.metadata["prior_sha256"] == _PRIOR_SHA
    assert bundle.metadata["thin"] == 4
    assert bundle.metadata["name"] == "P-SA"
    sampler = load_settings().sampler
    assert bundle.metadata["seed"] == sampler.random_seed
    assert bundle.metadata["sampler"]["init"] == sampler.init
    assert bundle.metadata["sampler"]["chains"] == sampler.chains
    assert bundle.scale_factors.revenue_mean == pytest.approx(100.0)
    assert bundle.scale_factors.spend_means["meta"] == pytest.approx(10.0)
    assert bundle.scale_factors.spend_means["radio"] == pytest.approx(20.0)
    assert dest.with_suffix(".nc").is_file()

    reloaded = load_posterior("P-SA", directory=tmp_path)
    assert_frame_equal(bundle.draws, reloaded.draws)


def test_thinning_4000_to_1000(tmp_path: Path) -> None:
    dest = _save(tmp_path, _idata(n_chains=4, n_draws=1000), thin=_DEFAULT_THIN)
    bundle = load_posterior("P-SA", directory=tmp_path)
    assert len(bundle.draws) == 1000
    assert bundle.draws["alpha"].iloc[0] == pytest.approx(0.0)
    assert bundle.draws["alpha"].iloc[1] == pytest.approx(4.0)
    assert bundle.draws["alpha"].iloc[-1] == pytest.approx(3996.0)
    assert dest.is_file()


def test_load_missing_scale_factors_raises(tmp_path: Path) -> None:
    dest = tmp_path / "P-SA.parquet"
    table = pa.Table.from_pandas(pd.DataFrame({"alpha": [1.0]}), preserve_index=False)
    payload = {"name": "P-SA", "thin": 4, "data_hash": "x", "prior_sha256": "y"}
    table = table.replace_schema_metadata({_META_KEY: json.dumps(payload).encode("utf-8")})
    pq.write_table(table, dest)

    with pytest.raises(FitError, match="scale factors missing"):
        load_posterior("P-SA", directory=tmp_path)


def test_load_missing_schema_metadata_raises(tmp_path: Path) -> None:
    dest = tmp_path / "P-SA.parquet"
    table = pa.Table.from_pandas(pd.DataFrame({"alpha": [1.0]}), preserve_index=False)
    pq.write_table(table, dest)

    with pytest.raises(FitError, match="ambo_posterior"):
        load_posterior("P-SA", directory=tmp_path)


def test_atomic_write_leaves_no_final_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "P-SA.parquet"

    def boom(src: str | Path, dst: str | Path) -> None:
        raise OSError("simulated crash before replace")

    monkeypatch.setattr("ambo.model.posterior_io.os.replace", boom)
    with pytest.raises(OSError, match="simulated crash"):
        _save(tmp_path)

    assert not dest.exists()
    assert list(tmp_path.iterdir()) == []


def test_atomic_write_cleans_temp_when_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "P-SA.parquet"

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr("ambo.model.posterior_io.pq.write_table", boom)
    with pytest.raises(OSError, match="simulated write failure"):
        _save(tmp_path)

    assert not dest.exists()
    assert list(tmp_path.iterdir()) == []


def test_bp_d_06_names_and_rejects_unknown(tmp_path: Path) -> None:
    path = _save(tmp_path, name="R__flat")
    assert path.name == "R__flat.parquet"
    load_posterior("R__flat", directory=tmp_path)

    with pytest.raises(FitError, match="BP-D-06"):
        save_posterior(
            _idata(n_chains=1, n_draws=8),
            _scale_factors(),
            "not-a-layer",
            data_hash=_DATA_HASH,
            prior_sha256=_PRIOR_SHA,
            thin=1,
            directory=tmp_path,
        )


def test_loco_variant_name_is_accepted(tmp_path: Path) -> None:
    path = _save(tmp_path, _idata(n_chains=1, n_draws=8), name="R__loco-search_brand", thin=1)
    assert path.name == "R__loco-search_brand.parquet"
    load_posterior("R__loco-search_brand", directory=tmp_path)


def test_path_separator_in_name_raises(tmp_path: Path) -> None:
    with pytest.raises(FitError, match="basename"):
        save_posterior(
            _idata(n_chains=1, n_draws=8),
            _scale_factors(),
            "../P-SA",
            data_hash=_DATA_HASH,
            prior_sha256=_PRIOR_SHA,
            thin=1,
            directory=tmp_path,
        )


def test_thin_less_than_one_raises(tmp_path: Path) -> None:
    with pytest.raises(FitError, match="thin must be"):
        _save(tmp_path, _idata(n_chains=1, n_draws=8), thin=0)


def test_missing_posterior_group_raises(tmp_path: Path) -> None:
    with pytest.raises(FitError, match="no posterior"):
        save_posterior(
            az.InferenceData(),
            _scale_factors(),
            "P-SA",
            data_hash=_DATA_HASH,
            prior_sha256=_PRIOR_SHA,
            thin=1,
            directory=tmp_path,
        )


def test_missing_parquet_raises(tmp_path: Path) -> None:
    with pytest.raises(FitError, match="not found"):
        load_posterior("P-SA", directory=tmp_path)
