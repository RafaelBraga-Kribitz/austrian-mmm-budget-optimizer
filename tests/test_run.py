"""Command-line parsing: every layer dispatches with the arguments it was given."""

import pytest

from ambo import layer_r, optimize, run


def test_unknown_layer_is_rejected():
    with pytest.raises(SystemExit):
        run.main(["layer_x"])


def test_packaged_configs_load():
    for name in ("layer_p.yaml", "layer_r.yaml", "tiny.yaml", "tiny_layer_r.yaml"):
        cfg = run.load_config(None, name)
        assert {"layer", "channels", "model", "priors", "sampling"} <= set(cfg)


@pytest.mark.parametrize(
    ("layer", "module", "func"),
    [("layer_p", run, "run_layer_p"), ("layer_r", layer_r, "run_layer_r"),
     ("layer_d", optimize, "run_layer_d")],
)
def test_each_layer_receives_config_out_and_data(monkeypatch, capsys, layer, module, func):
    seen = {}

    def fake(config_path=None, out_dir=None, data_dir=None):
        seen.update(config=config_path, out=out_dir, data=data_dir)
        return {"ok": True}

    monkeypatch.setattr(module, func, fake)
    assert run.main([layer, "--config", "c.yaml", "--out", "o", "--data", "d"]) == 0
    assert seen == {"config": "c.yaml", "out": "o", "data": "d"}
    assert '"ok": true' in capsys.readouterr().out
