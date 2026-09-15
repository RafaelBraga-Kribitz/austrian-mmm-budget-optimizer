"""Parameter recovery on the default Layer P seed. Slow: runs the full sampler."""

from importlib import resources

import pytest
import yaml

from ambo import evaluate, model, synth


@pytest.mark.slow
def test_at_least_80_percent_of_true_parameters_inside_their_90_percent_interval():
    with resources.files("ambo.configs").joinpath("layer_p.yaml").open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    result = synth.generate(config)
    md = model.prepare(result.data, config)
    idata, _ = model.fit(model.build_model(md, config["priors"]), config["sampling"])
    post = model.extract(idata)
    table = evaluate.parameter_recovery(post, md, result.truth)
    assert table["covered"].mean() >= 0.80, table[~table["covered"]]
