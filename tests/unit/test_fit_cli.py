"""CLI and orchestration tests for `ambo.model.fit` (T-307). Does not run NUTS.

Implements: MD-050, EB-050, D-20
"""

from __future__ import annotations

import subprocess

import pytest

from ambo.common.config import repo_root
from ambo.common.errors import FitError
from ambo.model.fit import channels_present_for_layer, main, run_fit


def test_channels_present_for_p_sa_are_taxonomy_ordered() -> None:
    channels = channels_present_for_layer("P-SA")
    assert channels, "P-SA channels_present was empty — warehouse scan is broken"
    assert "other" not in channels
    assert channels == [
        "search_brand",
        "search_generic",
        "meta",
        "display_video",
        "print_regional",
        "radio",
    ]


def test_unknown_layer_raises() -> None:
    with pytest.raises(FitError, match="unknown layer"):
        channels_present_for_layer("not-a-layer")


def test_unwired_variant_is_refused_before_sampling() -> None:
    with pytest.raises(FitError, match="not wired"):
        run_fit("P-SA", variant="flat")
    with pytest.raises(FitError, match="unknown fit variant"):
        run_fit("P-SA", variant="not-a-variant")


def test_make_n_fit_synthetic_is_the_p_sa_cli() -> None:
    result = subprocess.run(
        ["make", "-n", "fit-synthetic"],
        cwd=repo_root(),
        check=True,
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    assert "NOT IMPLEMENTED" not in combined
    assert "ambo.model.fit" in combined
    assert "--layer P-SA" in combined


def test_cli_requires_layer() -> None:
    with pytest.raises(SystemExit):
        main([])
