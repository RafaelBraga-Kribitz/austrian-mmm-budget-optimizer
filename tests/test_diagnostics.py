"""Sampler gates on hand-made traces: a healthy one passes, a split one fails R-hat."""

import json

import arviz as az
import numpy as np

from ambo import diagnostics

THRESHOLDS = {"rhat_max": 1.01, "ess_min": 400, "divergences_max": 0}


def _idata(offset: float = 0.0, divergences: int = 0) -> az.InferenceData:
    rng = np.random.default_rng(1)
    a = rng.normal(size=(2, 1000))
    a[1] += offset  # chains that disagree
    b = rng.normal(size=(2, 1000, 3))
    diverging = np.zeros((2, 1000), dtype=bool)
    diverging[0, :divergences] = True
    return az.from_dict(
        posterior={"a": a, "b": b},
        sample_stats={"diverging": diverging, "energy": rng.normal(size=(2, 1000))},
    )


def test_healthy_trace_passes_every_gate():
    d = diagnostics.summarise(_idata(), THRESHOLDS, extra={"fit": {"sampler": "test"}})
    assert d["pass_all"] and d["pass_rhat"] and d["pass_ess"] and d["pass_divergences"]
    assert d["chains"] == 2 and d["draws_per_chain"] == 1000
    assert d["divergences"] == 0 and d["min_bfmi"] is not None
    assert d["fit"] == {"sampler": "test"}
    assert d["thresholds"]["ess_min"] == 400.0


def test_disagreeing_chains_fail_rhat_and_name_the_parameter():
    d = diagnostics.summarise(_idata(offset=3.0), THRESHOLDS)
    assert not d["pass_rhat"] and not d["pass_all"]
    assert d["worst_rhat_parameter"] == "a"


def test_divergences_fail_their_gate():
    d = diagnostics.summarise(_idata(divergences=3), THRESHOLDS)
    assert d["divergences"] == 3 and not d["pass_divergences"] and not d["pass_all"]


def test_write_creates_parent_and_round_trips(tmp_path):
    path = tmp_path / "nested" / "diagnostics.json"
    diagnostics.write({"pass_all": True, "max_rhat": 1.0}, path)
    assert json.loads(path.read_text()) == {"max_rhat": 1.0, "pass_all": True}
    assert path.read_text().endswith("\n")
