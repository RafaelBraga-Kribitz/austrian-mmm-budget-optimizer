"""Every report chart renders from the committed report tables at 1600 px and under 1 MB."""

import json
from pathlib import Path

import matplotlib.image as mpimg
import numpy as np
import pandas as pd

from ambo.plots import charts, theme

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "reports" / "layer_p"
R = ROOT / "reports" / "layer_r"
D = ROOT / "reports" / "layer_d"


def _check(path: Path) -> None:
    assert path.exists() and path.stat().st_size < 1_000_000
    assert mpimg.imread(path).shape[1] == theme.WIDTH_PX


def test_theme_tokens_resolve():
    for role in ("surface", "surface-3", "ink", "ink-2", "mid", "accent"):
        assert theme.color(role).startswith("#")


def test_layer_p_charts(tmp_path):
    _check(charts.parameter_recovery(pd.read_csv(P / "parameter_recovery.csv"),
                                     tmp_path / "a.png", "test"))
    _check(charts.contribution_recovery(pd.read_csv(P / "contribution_recovery.csv"),
                                        tmp_path / "b.png", "test"))
    _check(charts.attribution_gap(pd.read_csv(P / "attribution_gap.csv"),
                                  tmp_path / "c.png", "test"))
    _check(charts.response_curve_recovery(pd.read_csv(P / "response_curves.csv"),
                                          tmp_path / "d.png", "test"))
    _check(charts.holdout(pd.read_csv(P / "holdout_predictions.csv"),
                          pd.read_csv(P / "holdout_metrics.csv"), tmp_path / "e.png", "test"))


def test_layer_r_charts(tmp_path):
    table = pd.read_csv(R / "channel_contributions.csv")
    weekly = pd.read_csv(R / "weekly_contributions.csv")
    channels = json.loads((R / "model_data.json").read_text())["channels"]
    _check(charts.channel_contributions(table, weekly, channels, tmp_path / "a.png", "test"))
    _check(charts.response_curves(pd.read_csv(R / "response_curves.csv"), tmp_path / "b.png",
                                  "test", max_multiple_of_observed=2.0))


def test_reallocation_gain_chart(tmp_path):
    gains = pd.read_csv(D / "reallocation_gain_draws.csv")["same_total"].to_numpy()
    current = np.full_like(gains, 400000.0)
    _check(charts.reallocation_gain(gains, current, tmp_path / "g.png", "test", bound_share=0.3))

