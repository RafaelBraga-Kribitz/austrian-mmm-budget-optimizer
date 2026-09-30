"""Model bookkeeping that does not need a real sampler run."""

from ambo import model


def test_sampler_fallback_is_recorded_as_a_deviation(monkeypatch):
    monkeypatch.setattr(model, "_sample", lambda *a, **k: (object(), "pymc"))
    sampling = {"sampler": "nutpie", "chains": 2, "tune": 10, "draws": 10,
                "target_accept": 0.9, "seed": 1}
    _, info = model.fit(None, sampling)
    assert info["sampler"] == "pymc"
    assert info["deviations"] == ["nutpie unavailable, used pymc"]


def test_no_deviation_when_the_requested_sampler_ran(monkeypatch):
    monkeypatch.setattr(model, "_sample", lambda *a, **k: (object(), "nutpie"))
    sampling = {"sampler": "nutpie", "chains": 2, "tune": 10, "draws": 10,
                "target_accept": 0.9, "seed": 1}
    _, info = model.fit(None, sampling)
    assert info["deviations"] == []
