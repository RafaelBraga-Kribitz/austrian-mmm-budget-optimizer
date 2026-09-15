"""Synthetic generator: shapes, seed determinism, truth file written and readable."""

import json
from importlib import resources

import pandas as pd
import pytest
import yaml

from ambo import synth


@pytest.fixture(scope="module")
def config():
    with resources.files("ambo.configs").joinpath("tiny.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_shapes_and_columns(config):
    result = synth.generate(config)
    weeks = config["synthetic"]["weeks"]
    channels = config["channels"]
    assert len(result.data) == weeks
    for ch in channels:
        assert f"spend_{ch}" in result.data.columns
        assert (result.data[f"spend_{ch}"] >= 0).all()
    assert "revenue" in result.data.columns and (result.data["revenue"] > 0).all()
    assert config["control"]["column"] in result.data.columns
    online = [ch for ch in channels if config["synthetic"]["channels"][ch].get("platform")]
    for ch in online:
        assert f"platform_{ch}" in result.data.columns
    assert list(result.contributions.columns) == ["week", *channels, "baseline", "noise"]


def test_seed_determinism(config):
    a = synth.generate(config)
    b = synth.generate(config)
    pd.testing.assert_frame_equal(a.data, b.data)
    assert a.truth == b.truth


def test_different_seed_changes_data(config):
    other = dict(config)
    other["synthetic"] = dict(config["synthetic"], seed=config["synthetic"]["seed"] + 1)
    a = synth.generate(config)
    b = synth.generate(other)
    assert not a.data["revenue"].equals(b.data["revenue"])


def test_truth_file_written_and_readable(config, tmp_path):
    result = synth.generate(config)
    synth.write(result, tmp_path)
    assert (tmp_path / "truth.json").exists()
    with open(tmp_path / "truth.json", encoding="utf-8") as fh:
        truth = json.load(fh)
    assert truth["channels"] == config["channels"]
    for ch in config["channels"]:
        block = truth["channel_truth"][ch]
        for key in ("decay", "half_saturation", "slope", "effect", "roas"):
            assert key in block
    data, truth2, contributions = synth.load(tmp_path)
    assert truth2 == truth
    assert len(data) == len(contributions) == config["synthetic"]["weeks"]


def test_decomposition_adds_up(config):
    result = synth.generate(config)
    parts = result.contributions
    total = parts[config["channels"]].sum(axis=1) + parts["baseline"] + parts["noise"]
    pd.testing.assert_series_equal(
        total.round(2), result.data["revenue"], check_names=False, atol=0.01
    )


def test_plausibility(config):
    truth = synth.generate(config).truth
    share = truth["totals"]["media_share_of_revenue"]
    assert 0.15 <= share <= 0.45
    search = truth["channel_truth"]["Paid Search"]
    tv = truth["channel_truth"]["TV"]
    assert search["platform_share_of_reported"] > search["contribution_share_of_media"]
    assert tv["platform_share_of_reported"] == 0.0


def test_independent_transforms_match_the_model_reference():
    import numpy as np

    from ambo.transforms import adstock, hill

    x = np.array([10.0, 0.0, 5.0, 0.0, 0.0, 3.0])
    np.testing.assert_allclose(synth.adstock_recursive(x, 0.5), adstock(x, 0.5, len(x)))
    a = np.array([0.0, 1.0, 2.0, 4.0, 8.0])
    np.testing.assert_allclose(synth.hill_curve(a, 2.0, 1.3), hill(a, 2.0, 1.3))
