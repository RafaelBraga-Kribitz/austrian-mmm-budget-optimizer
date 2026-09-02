"""Tests for `ambo.simulate.truth` (T-107).

Implements: REQ-q1-truth-recovery

Covers SIM-075's schema completeness across all three scenarios, SIM-070's
byte-stability of `write_truth`, the S-C zero-effect-channel exact-zero spot
check, the analytic-marginal-ROAS-vs-finite-difference agreement, and the
caller-supplied-grid property (SPEC-01 section 8) Phase 3/8's export depends on.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from ambo.common.errors import SimulationError
from ambo.simulate.config import SPEC_CHANNEL_ORDER, load_scenario
from ambo.simulate.dgp import SimulationResult, assemble_scenario
from ambo.simulate.platform_bias import platform_report
from ambo.simulate.truth import (
    TruthFile,
    compute_truth,
    response_curve_at,
    write_truth,
)

_ALL_SCENARIOS = ["s_a", "s_b", "s_c"]
_OFFLINE_CHANNELS = ("print_regional", "radio")
_ONLINE_CHANNELS = tuple(c for c in SPEC_CHANNEL_ORDER if c not in _OFFLINE_CHANNELS)


def _build_truth(scenario_id: str) -> tuple[SimulationResult, TruthFile]:
    """Shared fixture-like helper: assemble one scenario and compute its truth."""
    cfg = load_scenario(scenario_id)
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = platform_report(result)
    return result, compute_truth(result, media)


# ---------------------------------------------------------------------------
# SIM-075 schema completeness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_truth_file_validates_and_is_complete(scenario_id: str) -> None:
    result, truth = _build_truth(scenario_id)
    cfg = result.cfg

    assert isinstance(truth, TruthFile)
    assert [c.channel for c in truth.channels] == list(SPEC_CHANNEL_ORDER)
    assert len(truth.channels) == 6, "must not pass vacuously on zero channels"

    for channel_truth in truth.channels:
        params = cfg.channels[channel_truth.channel].true_params
        assert channel_truth.lam == params.lam
        assert channel_truth.K == params.K
        assert channel_truth.s == params.s
        assert channel_truth.beta == params.beta

        if channel_truth.channel in _ONLINE_CHANNELS:
            assert channel_truth.platform_phi is not None
            assert channel_truth.platform_theta is not None
            assert channel_truth.platform_cpm is not None
            assert channel_truth.platform_roas is not None
        else:
            assert channel_truth.platform_phi is None
            assert channel_truth.platform_theta is None
            assert channel_truth.platform_cpm is None
            assert channel_truth.platform_roas is None


def test_truth_file_rejects_unknown_key_and_is_frozen() -> None:
    _, truth = _build_truth("s_a")
    dump = truth.model_dump(mode="json")

    with pytest.raises(ValidationError, match="extra_field"):
        TruthFile(**{**dump, "extra_field": 1})

    with pytest.raises(ValidationError, match="frozen"):
        truth.schema_version = "2.0"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Derived-quantity correctness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_true_avg_roas_equals_sum_m_over_sum_x(scenario_id: str) -> None:
    result, truth = _build_truth(scenario_id)
    checked_any = False
    for channel_truth in truth.channels:
        channel_id = channel_truth.channel
        expected_roas = float(
            result.components[f"m_{channel_id}"].sum() / result.spend[channel_id].sum()
        )
        assert abs(channel_truth.true_avg_roas - expected_roas) < 1e-9
        checked_any = True
    assert checked_any


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_contribution_shares_sum_to_media_share_of_revenue(scenario_id: str) -> None:
    _, truth = _build_truth(scenario_id)
    total_share = sum(c.contribution_share for c in truth.channels)
    assert abs(total_share - truth.media_share_of_revenue) < 1e-9


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_marginal_roas_matches_finite_difference(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    _, truth = _build_truth(scenario_id)

    checked_any = False
    for channel_truth in truth.channels:
        params = cfg.channels[channel_truth.channel].true_params
        if params.beta == 0.0:
            continue
        x_mean = channel_truth.mean_weekly_spend_eur
        h = x_mean * 1e-5
        forward = response_curve_at(params, np.array([x_mean + h]))[0]
        backward = response_curve_at(params, np.array([x_mean - h]))[0]
        finite_diff = (forward - backward) / (2 * h)
        relative_error = abs(channel_truth.true_marginal_roas_at_mean_spend - finite_diff) / abs(
            finite_diff
        )
        assert relative_error < 1e-6, f"{scenario_id}/{channel_truth.channel}: {relative_error!r}"
        checked_any = True
    assert checked_any, "no beta > 0 channel was checked -- must not pass vacuously"


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_response_curve_is_monotone_non_decreasing(scenario_id: str) -> None:
    _, truth = _build_truth(scenario_id)
    checked_any = False
    for channel_truth in truth.channels:
        curve = np.array(channel_truth.response_curve_contribution_eur)
        assert np.all(np.diff(curve) >= -1e-12), (
            f"{scenario_id}/{channel_truth.channel}: not monotone"
        )
        checked_any = True
    assert checked_any

    if scenario_id == "s_c":
        display_video = next(c for c in truth.channels if c.channel == "display_video")
        assert all(v == 0.0 for v in display_video.response_curve_contribution_eur)
        assert len(display_video.response_curve_contribution_eur) == 21


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_response_curve_grid_spans_zero_to_two_times_max_spend(scenario_id: str) -> None:
    _, truth = _build_truth(scenario_id)
    assert truth.response_curve_grid_max_multiple == 2.0
    checked_any = False
    for channel_truth in truth.channels:
        grid = channel_truth.response_curve_spend_eur
        assert len(grid) == 21
        assert grid[0] == 0.0
        assert grid[-1] == pytest.approx(2.0 * channel_truth.max_weekly_spend_eur, abs=1e-9)
        checked_any = True
    assert checked_any


def test_response_curve_at_accepts_a_caller_supplied_grid() -> None:
    """SPEC-01 section 8: `response_curve_at` is generic in its grid argument --
    calling it with MD-082's future 1.5x-max horizon (a *different* grid than the
    stored 2x diagnostic array) must agree with an independent closed-form
    recomputation, and must agree with the stored 2x-grid array at the one spend
    level the two grids are guaranteed to share: `x == 0.0`."""
    cfg = load_scenario("s_a")
    _, truth = _build_truth("s_a")

    checked_any = False
    for channel_truth in truth.channels:
        params = cfg.channels[channel_truth.channel].true_params
        max_spend = channel_truth.max_weekly_spend_eur

        md082_grid = np.linspace(0.0, 1.5 * max_spend, 21)
        actual = response_curve_at(params, md082_grid)

        a = md082_grid / (1.0 - params.lam)
        expected = params.beta * (a**params.s / (a**params.s + params.K**params.s))
        assert np.allclose(actual, expected, atol=1e-9)

        # The shared spend level both grids anchor at.
        assert md082_grid[0] == 0.0 == channel_truth.response_curve_spend_eur[0]
        assert abs(actual[0] - channel_truth.response_curve_contribution_eur[0]) < 1e-9
        checked_any = True
    assert checked_any


# ---------------------------------------------------------------------------
# S-C zero-effect channel and offline-null coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_s_c_zero_effect_channel_truth_is_exactly_zero(scenario_id: str) -> None:
    _, truth = _build_truth(scenario_id)

    if scenario_id == "s_c":
        display_video = next(c for c in truth.channels if c.channel == "display_video")
        assert display_video.true_avg_roas == 0.0
        assert display_video.total_contribution_eur == 0.0
        assert display_video.contribution_share == 0.0
        assert truth.zero_effect_channel == "display_video"
    else:
        assert truth.zero_effect_channel is None


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_offline_channels_have_null_platform_fields(scenario_id: str) -> None:
    _, truth = _build_truth(scenario_id)
    checked_any = False
    for channel_truth in truth.channels:
        if channel_truth.channel in _OFFLINE_CHANNELS:
            assert channel_truth.platform_phi is None
            assert channel_truth.platform_theta is None
            assert channel_truth.platform_cpm is None
            assert channel_truth.platform_roas is None
            checked_any = True
    assert checked_any, "no offline channel was checked -- must not pass vacuously"


def test_zero_total_spend_channel_raises() -> None:
    """Zeroing only `result.spend` (never `components`) is sufficient -- SIM-071's
    decomposition invariant re-sums `components` alone, so no adjustment is
    needed to keep the `SimulationResult` constructor precondition satisfied
    (the same pattern 02-07's zero-total-spend test uses)."""
    cfg = load_scenario("s_a")
    result = assemble_scenario(cfg, np.random.default_rng(cfg.seed))
    media = platform_report(result)
    channel_id = "search_brand"

    zeroed_spend = result.spend.copy()
    zeroed_spend[channel_id] = 0

    zeroed_result = SimulationResult(
        cfg=result.cfg,
        weeks=result.weeks,
        spend=zeroed_spend,
        components=result.components,
        media=result.media,
        outcome=result.outcome,
    )

    with pytest.raises(SimulationError, match=channel_id):
        compute_truth(zeroed_result, media)


# ---------------------------------------------------------------------------
# write_truth byte-stability (SIM-070)
# ---------------------------------------------------------------------------


def test_write_truth_is_byte_stable(tmp_path: Path) -> None:
    _, truth = _build_truth("s_b")
    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"

    write_truth(truth, path_a)
    write_truth(truth, path_b)

    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()
    assert bytes_a == bytes_b
    assert b"\r" not in bytes_a
    text = bytes_a.decode("utf-8")
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_written_json_keys_are_sorted(tmp_path: Path) -> None:
    _, truth = _build_truth("s_a")
    path = tmp_path / "truth.json"
    write_truth(truth, path)

    def _assert_sorted(obj: object) -> None:
        if isinstance(obj, dict):
            keys = list(obj.keys())
            assert keys == sorted(keys), f"unsorted keys: {keys!r}"
            for value in obj.values():
                _assert_sorted(value)
        elif isinstance(obj, list):
            for item in obj:
                _assert_sorted(item)

    parsed = json.loads(path.read_text(encoding="utf-8"))
    _assert_sorted(parsed)


_NUMBER_RE = re.compile(r"-?\d+\.\d+(?:[eE][+-]?\d+)?|-?\d+(?:[eE][+-]?\d+)?")


def _significant_digit_count(literal: str) -> int:
    """Count of significant digits in a JSON numeric literal, ignoring sign,
    decimal point, exponent, and leading/trailing zeros -- what `%.10g`
    guarantees stays `<= 10`."""
    mantissa = literal.lower().split("e")[0].lstrip("-+")
    integer_part, _, frac_part = mantissa.partition(".")
    integer_part = integer_part.lstrip("0")
    digits = integer_part + frac_part if integer_part else frac_part.lstrip("0")
    digits = digits.rstrip("0") or "0"
    return len(digits)


def test_written_floats_have_at_most_ten_significant_digits(tmp_path: Path) -> None:
    _, truth = _build_truth("s_b")
    path = tmp_path / "truth.json"
    write_truth(truth, path)
    text = path.read_text(encoding="utf-8")

    offenders = [
        match.group(0)
        for match in _NUMBER_RE.finditer(text)
        if _significant_digit_count(match.group(0)) > 10
    ]
    assert not offenders, f"literal(s) with more than 10 significant digits: {offenders}"


def test_write_truth_leaves_no_temp_file(tmp_path: Path) -> None:
    _, truth = _build_truth("s_a")
    path = tmp_path / "truth.json"
    write_truth(truth, path)

    entries = sorted(p.name for p in tmp_path.iterdir())
    assert entries == ["truth.json"], f"unexpected directory contents: {entries!r}"


# ---------------------------------------------------------------------------
# Single-home guard (A-8)
# ---------------------------------------------------------------------------

_TRIPLE_QUOTED_RE = re.compile(
    r'"""(?:[^"\\]|\\.|"(?!""))*"""|\'\'\'(?:[^\'\\]|\\.|\'(?!\'\'))*\'\'\'', re.DOTALL
)
_CURVE_EXPRESSION_RE = re.compile(r"\(1\.0\s*-\s*params\.lam\)")


def _strip_comments_and_docstrings(text: str) -> str:
    """Remove triple-quoted string literals and `#`-comment lines, so a prose
    mention of the closed-form formula in an explanatory docstring or comment
    elsewhere (e.g. `dgp.py`'s note on why `lam == 1.0` is rejected) cannot trip
    the single-home guard below."""
    text = _TRIPLE_QUOTED_RE.sub("", text)
    kept_lines = [line for line in text.splitlines() if not line.strip().startswith("#")]
    return "\n".join(kept_lines)


def test_curve_formula_has_a_single_home(repo_root: Path) -> None:
    """Adapts `test_config.py`'s single-config-home grep guard: the steady-state
    adstock closed form (`x / (1 - lam)`, spelled `(1.0 - params.lam)` in code)
    must appear only in `truth.py` (A-8)."""
    src_root = repo_root / "src" / "ambo"
    truth_module = src_root / "simulate" / "truth.py"

    py_files = sorted(src_root.rglob("*.py"))
    assert py_files, "No files found under src/ambo/ -- the scan is broken, not vacuously passing."

    offenders: list[str] = []
    for py_file in py_files:
        if py_file == truth_module:
            continue
        text = _strip_comments_and_docstrings(py_file.read_text(encoding="utf-8"))
        if _CURVE_EXPRESSION_RE.search(text):
            offenders.append(py_file.relative_to(repo_root).as_posix())

    assert not offenders, (
        "steady-state-adstock curve expression found outside truth.py (A-8): "
        + ", ".join(offenders)
    )

    truth_text = _strip_comments_and_docstrings(truth_module.read_text(encoding="utf-8"))
    assert _CURVE_EXPRESSION_RE.search(truth_text), (
        "sanity check failed: the curve expression pattern no longer matches truth.py itself "
        "-- the scan would otherwise pass vacuously"
    )
