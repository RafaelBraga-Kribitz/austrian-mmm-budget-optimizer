"""Layer R shaping and tables on the committed dataset and on a small fixture."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ambo import layer_r, model
from ambo.run import load_config

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def config():
    return load_config(None, "layer_r.yaml")


def test_load_source_shapes_the_robyn_file(config):
    data = layer_r.load_source(config, ROOT / config["data_dir"])
    assert len(data) == 208
    assert list(data["week"][:3]) == [1, 2, 3]
    for ch in config["channels"]:
        assert f"spend_{ch}" in data.columns
    control = data[config["control"]["column"]]
    assert control.mean() == pytest.approx(1.0)  # control_scale: mean
    assert data["week_start"].iloc[0] == "2015-11-23"


def test_load_source_takes_event_columns_when_there_is_no_control(tmp_path):
    raw = pd.DataFrame(
        {"d": ["2024-01-01", "2024-01-08", "2024-01-15"], "rev": [10.0, 11.0, 12.0],
         "x_S": [1.0, 2.0, 3.0], "promo": [0, 1, 0], "sale": [0, 0, 1]}
    )
    raw.to_csv(tmp_path / "f.csv", index=False)
    cfg = {
        "source": {"file": "f.csv", "date_column": "d", "revenue_column": "rev",
                   "spend_columns": {"x_S": "X"}, "event_columns": ["promo", "sale"]},
        "control": {"column": "event"},
    }
    data = layer_r.load_source(cfg, tmp_path)
    assert list(data.columns) == ["week", "week_start", "revenue", "spend_X", "event"]
    assert list(data["event"]) == [0.0, 1.0, 1.0]


def _model_data() -> model.ModelData:
    return model.ModelData(
        channels=["A", "B"],
        weeks=np.arange(1, 5),
        spend=np.array([[10.0, 0.0], [10.0, 5.0], [10.0, 5.0], [10.0, 10.0]]),
        revenue=np.array([100.0, 100.0, 100.0, 100.0]),
        control=np.zeros(4),
        spend_means=np.array([10.0, 7.5]),
        revenue_mean=100.0,
        n_train=4,
        adstock_length=2,
        fourier_order=1,
        fourier_period=52.18,
        week_start=["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22"],
    )


def test_channel_table_shares_and_roas():
    md = _model_data()
    contribs = np.zeros((3, 4, 2))
    contribs[:, :, 0] = 5.0  # A: 20 per draw over 4 weeks, spend 40
    contribs[:, :, 1] = np.array([1.0, 2.0, 3.0])[:, None]  # B varies by draw, spend 20
    table = layer_r.channel_table(contribs, md)
    a, b = table.iloc[0], table.iloc[1]
    assert a["channel"] == "A" and a["share_median"] == pytest.approx(0.05)
    assert a["roas_median"] == pytest.approx(0.5) and a["roas_lo"] == pytest.approx(0.5)
    assert b["contribution_median"] == pytest.approx(8.0)
    assert b["roas_lo"] < b["roas_median"] < b["roas_hi"]
    assert b["spend_mean_week"] == pytest.approx(5.0)


def test_weekly_contribution_table_columns_match_the_chart():
    md = _model_data()
    contribs = np.ones((3, 4, 2))
    base = np.full((3, 4), 90.0)
    weekly = layer_r.weekly_contribution_table(contribs, base, md)
    assert list(weekly.columns) == [
        "week", "week_start", "revenue", "baseline_median",
        "A median", "A lo", "A hi", "B median", "B lo", "B hi",
    ]
    assert (weekly["baseline_median"] == 90.0).all()
    assert (weekly["A median"] == 1.0).all()
