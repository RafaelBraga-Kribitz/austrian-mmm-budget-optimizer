"""CLI simulate path writes committed-size artifacts."""

from __future__ import annotations

from ambo.run import main


def test_simulate_cli(tmp_path, monkeypatch):
    monkeypatch.setattr("ambo.synth.DATA_DIR", tmp_path)
    monkeypatch.setattr("ambo.config.DATA_DIR", tmp_path)
    assert main(["simulate"]) == 0
    assert (tmp_path / "truth.json").exists()
