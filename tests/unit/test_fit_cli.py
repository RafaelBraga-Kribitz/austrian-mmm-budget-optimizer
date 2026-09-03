"""CLI and orchestration tests for `ambo.model.fit` (T-307). Does not run NUTS.

Implements: MD-050, MD-073, EB-050, D-18
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ambo.common.config import repo_root
from ambo.common.errors import FitError
from ambo.model.diagnostics import DiagGates, DiagResult, GateCheck
from ambo.model.fit import (
    _require_rung1_retry_eligible,
    _rung1_retry_eligible,
    channels_present_for_layer,
    main,
    run_fit,
    tighten_s_c_prior,
)
from ambo.model.priors import SYNTHETIC_PRIORS_RELATIVE, load_priors

_GATE_NAMES = ("R-hat", "ESS_bulk", "ESS_tail", "divergences", "BFMI", "PPC_90")


def _diag_result(*failed: str) -> DiagResult:
    failed_set = set(failed)
    checks = tuple(
        GateCheck(
            name=name,
            passed=name not in failed_set,
            statistic=None,
            threshold="",
            detail="",
        )
        for name in _GATE_NAMES
    )
    return DiagResult(
        profile="standard",
        gates=DiagGates.standard(),
        checks=checks,
        all_green=not failed_set,
        n_divergences=int("divergences" in failed_set),
        ppc_coverage=0.9,
    )


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


def test_make_n_fit_synthetic_runs_three_layers() -> None:
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
    assert "--layer P-SB" in combined
    assert "--layer P-SC" in combined


def test_cli_requires_layer() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_rung1_retry_allows_divergences_with_or_without_ess_tail() -> None:
    assert _rung1_retry_eligible(_diag_result("divergences"))
    assert _rung1_retry_eligible(_diag_result("divergences", "ESS_tail"))


def test_rung1_retry_refuses_ess_tail_alone_or_other_red_gates() -> None:
    assert not _rung1_retry_eligible(_diag_result())
    assert not _rung1_retry_eligible(_diag_result("ESS_tail"))
    assert not _rung1_retry_eligible(_diag_result("divergences", "R-hat"))
    assert not _rung1_retry_eligible(_diag_result("divergences", "ESS_bulk"))
    assert not _rung1_retry_eligible(_diag_result("divergences", "BFMI"))
    assert not _rung1_retry_eligible(_diag_result("divergences", "PPC_90"))


def test_require_rung1_retry_eligible_raises_when_rhat_is_red() -> None:
    with pytest.raises(FitError, match="MD-071/072 red"):
        _require_rung1_retry_eligible(
            _diag_result("divergences", "R-hat"),
            "P-SC",
            Path("reports/model/diag_P-SC.md"),
        )


def test_tighten_s_c_prior_is_md073_rung3_and_does_not_edit_yaml() -> None:
    path = repo_root() / SYNTHETIC_PRIORS_RELATIVE
    original = path.read_bytes()
    priors = load_priors(path)
    tightened = tighten_s_c_prior(priors)
    assert path.read_bytes() == original
    for channel in tightened.channels.values():
        assert (channel.s.shape, channel.s.rate, channel.s.lower, channel.s.upper) == (
            4.0,
            3.0,
            0.5,
            2.5,
        )
        assert channel.lam == priors.channels["meta"].lam
        assert channel.K == priors.channels["meta"].K
        assert channel.beta == priors.channels["meta"].beta
    for channel in priors.channels.values():
        assert (channel.s.shape, channel.s.rate, channel.s.lower, channel.s.upper) == (
            3.0,
            2.0,
            0.3,
            3.0,
        )
