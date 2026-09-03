"""Tests for `ambo.model.diagnostics` (T-306 / MD-071 / MD-072 / MD-074).

Implements: MD-071, MD-072, MD-074
"""

from __future__ import annotations

from pathlib import Path

import arviz as az
import numpy as np

from ambo.common.config import repo_root
from ambo.model.diagnostics import DiagGates, run_diagnostics, write_diag_report

_RNG = np.random.default_rng(0)


def _idata(
    *,
    n_div: int = 0,
    chain1_shift: float = 0.0,
    n_draws: int = 500,
    n_weeks: int = 24,
    ppc_noise: float = 0.2,
    include_ppc: bool = True,
) -> az.InferenceData:
    n_chain = 2
    alpha = np.stack(
        [
            _RNG.normal(size=n_draws),
            _RNG.normal(loc=chain1_shift, size=n_draws),
        ]
    )
    diverging = np.zeros((n_chain, n_draws), dtype=bool)
    if n_div:
        diverging.flat[:n_div] = True
    energy = _RNG.normal(size=(n_chain, n_draws))
    groups: dict[str, object] = {
        "posterior": {"alpha": alpha},
        "sample_stats": {"diverging": diverging, "energy": energy},
    }
    if include_ppc:
        y_obs = _RNG.normal(size=n_weeks)
        y_ppc = y_obs + _RNG.normal(scale=ppc_noise, size=(n_chain, n_draws, n_weeks))
        groups["posterior_predictive"] = {"y": y_ppc}
        groups["observed_data"] = {"y": y_obs}
        return az.from_dict(
            **groups,
            dims={"y": ["week"]},
            coords={"week": np.arange(n_weeks)},
        )
    return az.from_dict(**groups)


def test_healthy_idata_passes_standard() -> None:
    result = run_diagnostics(_idata(), DiagGates.standard())
    assert result.profile == "standard"
    assert result.n_divergences == 0
    assert result.all_green
    assert result.ppc_coverage is not None
    assert result.ppc_coverage >= 0.85


def test_injected_divergences_fail_standard_but_not_layer_r() -> None:
    idata = _idata(n_div=3)
    standard = run_diagnostics(idata, DiagGates.standard())
    relaxed = run_diagnostics(idata, DiagGates.layer_r())
    assert standard.n_divergences == 3
    assert not standard.all_green
    div_row = next(c for c in standard.checks if c.name == "divergences")
    assert not div_row.passed
    assert relaxed.profile == "layer_r"
    assert relaxed.all_green
    assert next(c for c in relaxed.checks if c.name == "divergences").passed


def test_layer_r_is_constructor_not_n_obs_heuristic() -> None:
    short = _idata(n_weeks=8, n_div=3)
    # Same short series, two explicit profiles — the week count does not pick the gate.
    assert not run_diagnostics(short, DiagGates.standard()).all_green
    assert run_diagnostics(short, DiagGates.layer_r()).all_green
    source = (repo_root() / "src/ambo/model/diagnostics.py").read_text(encoding="utf-8")
    assert "n_obs" not in source
    assert "len(df)" not in source
    body = source.split("def run_diagnostics", 1)[1].split("\ndef write_diag_report", 1)[0]
    assert "DiagGates.standard" not in body
    assert "DiagGates.layer_r" not in body


def test_shifted_chains_fail_rhat() -> None:
    result = run_diagnostics(_idata(chain1_shift=10.0), DiagGates.standard())
    assert not result.all_green
    assert not next(c for c in result.checks if c.name == "R-hat").passed


def test_missing_ppc_fails_md072_not_dropped() -> None:
    result = run_diagnostics(_idata(include_ppc=False), DiagGates.standard())
    ppc = next(c for c in result.checks if c.name == "PPC_90")
    assert ppc.statistic is None
    assert not ppc.passed
    assert "not dropped" in ppc.detail
    assert not result.all_green


def test_write_diag_report_emits_table_and_plots(tmp_path: Path) -> None:
    idata = _idata(n_div=2)
    result = run_diagnostics(idata, DiagGates.layer_r())
    dest = write_diag_report(result, "P-SA", idata=idata, directory=tmp_path)
    text = dest.read_text(encoding="utf-8")
    assert dest.name == "diag_P-SA.md"
    assert "| Gate |" in text
    assert "divergences" in text
    assert (tmp_path / "ppc_P-SA.png").is_file()
    assert (tmp_path / "energy_P-SA.png").is_file()
    assert "pair plots" in text


def test_standard_energy_plot_only_when_divergences(tmp_path: Path) -> None:
    idata = _idata(n_div=0)
    result = run_diagnostics(idata, DiagGates.standard())
    write_diag_report(result, "P-SA", idata=idata, directory=tmp_path)
    assert (tmp_path / "ppc_P-SA.png").is_file()
    assert not (tmp_path / "energy_P-SA.png").exists()


def test_thresholds_match_spec() -> None:
    std = DiagGates.standard()
    rel = DiagGates.layer_r()
    assert std.rhat_max == 1.01
    assert std.ess_min == 400.0
    assert std.divergences_max == 0
    assert std.bfmi_min == 0.3
    assert std.ppc_coverage_min == 0.85
    assert rel.ess_min == 300.0
    assert rel.divergences_max == 5
    assert rel.rhat_max == std.rhat_max
    assert rel.ppc_coverage_min == std.ppc_coverage_min
