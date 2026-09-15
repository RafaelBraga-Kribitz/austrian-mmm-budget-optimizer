"""Layer R is refused rather than fabricated (A-5, Charter §7)."""

import pytest

from ambo.data import LayerRUnavailable, load_layer_r
from ambo.run import main


def test_load_layer_r_raises():
    with pytest.raises(LayerRUnavailable, match="Charter"):
        load_layer_r()


def test_cli_layer_r_exits_2():
    assert main(["layer_r"]) == 2
