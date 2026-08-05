"""Tests for `ambo.simulate.spend_patterns` (T-102, SIM-030, SIM-031).

Implements: REQ-q1-truth-recovery

Every statistical design value (annual totals, flighting zero-week shares) is
re-derived here directly from SPEC-01 section 3 and the scenario's own
`ScenarioConfig`/`weeks` frame -- never by calling anything in
`spend_patterns.py` -- so the ±10%/±10pp assertions are real checks, not
tautologies (02-RESEARCH.md Pitfall 6's diagnostic point: a floor/round/multiply
ordering bug biases these statistics by a small, systematic margin rather than
crashing).

`np.random.default_rng(cfg.seed)` is constructed directly (rather than via
`conftest.py`'s `seeded_rng` fixture) whenever a test's own point is SIM-001
reproducibility keyed to the *scenario's own* seed -- `seeded_rng` deliberately
carries a fixed, scenario-independent constant and cannot stand in for that.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ambo.simulate.config import ScenarioConfig, SpendPattern, load_scenario
from ambo.simulate.dgp import week_index
from ambo.simulate.spend_patterns import generate_spend

SCENARIOS: tuple[str, ...] = ("s_a", "s_b", "s_c")

# SPEC-01 section 3's nominal flighted zero-week shares.
_NOMINAL_ZERO_SHARE: dict[str, float] = {"print_regional": 0.70, "radio": 0.75}


def _design_annual_totals(
    cfg: ScenarioConfig, weeks: pd.DataFrame, iso_year: int
) -> dict[str, float]:
    """Each channel's expected annual spend total, re-derived directly from
    SPEC-01 section 3 -- never by calling `generate_spend` or any other
    `spend_patterns.py` symbol. An always-on channel is `mean * sum over the
    year of (1 + advent_factor*advent + spring_factor*spring)`, times the pulse
    multiplier on pulse weeks. A flighted channel is `mean * burst_length *
    number_of_bursts_authored_in_that_year` (correctly pro-rating a partial
    covered year, since `weeks`/`burst_starts` only ever carry weeks inside the
    scenario's declared window)."""
    year_weeks = weeks[weeks["iso_year"] == iso_year]
    totals: dict[str, float] = {}
    for channel_id, channel in cfg.channels.items():
        pattern = channel.spend
        if pattern.burst_length is not None and pattern.burst_starts is not None:
            bursts_this_year = len(pattern.burst_starts.get(iso_year, ()))
            totals[channel_id] = pattern.mean * pattern.burst_length * bursts_this_year
            continue

        t = year_weeks["t"].to_numpy()
        advent = year_weeks["advent_flag"].to_numpy()
        spring = year_weeks["spring_flag"].to_numpy()
        term = 1.0 + pattern.advent_factor * advent + pattern.spring_factor * spring
        if pattern.pulse_every is not None:
            assert pattern.pulse_multiplier is not None
            pulse_mask = (t % pattern.pulse_every) == 0
            term = np.where(pulse_mask, term * pattern.pulse_multiplier, term)
        totals[channel_id] = pattern.mean * float(term.sum())
    return totals


def _scheduled_burst_t_values(pattern: SpendPattern, weeks: pd.DataFrame) -> set[int]:
    """The `t` values covered by `pattern`'s authored burst spans, derived
    directly from `pattern.burst_starts`/`pattern.burst_length` and `weeks`'s own
    `(iso_year, iso_week) -> t` mapping -- never by calling `generate_spend`."""
    assert pattern.burst_length is not None
    assert pattern.burst_starts is not None
    key_to_t = {
        (year, week): t
        for year, week, t in zip(weeks["iso_year"], weeks["iso_week"], weeks["t"], strict=True)
    }
    covered: set[int] = set()
    for year, starts in pattern.burst_starts.items():
        for start in starts:
            for week in range(start, start + pattern.burst_length):
                covered.add(key_to_t[(year, week)])
    return covered


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_determinism_same_seed_same_frame(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    weeks = week_index(cfg)

    frame_a = generate_spend(cfg, np.random.default_rng(cfg.seed), weeks)
    frame_b = generate_spend(cfg, np.random.default_rng(cfg.seed), weeks)

    assert not frame_a.empty, f"{scenario_id}: generate_spend returned an empty frame"
    assert frame_a.equals(frame_b), f"{scenario_id}: two fresh cfg.seed-seeded runs diverged"


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_all_spends_are_non_negative_integers(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    weeks = week_index(cfg)
    frame = generate_spend(cfg, np.random.default_rng(cfg.seed), weeks)

    for column in frame.columns:
        assert frame[column].to_numpy().dtype == np.int64, (
            f"{scenario_id}/{column}: expected dtype int64, got {frame[column].dtype!r}"
        )
    assert (frame.to_numpy() >= 0).all(), f"{scenario_id}: found a negative spend value"
    assert frame["search_brand"].min() >= 400, (
        f"{scenario_id}: search_brand floor violated, min={frame['search_brand'].min()!r}"
    )


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_annual_totals_within_ten_percent_of_design(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    weeks = week_index(cfg)
    frame = generate_spend(cfg, np.random.default_rng(cfg.seed), weeks)

    years_checked = 0
    for iso_year in cfg.covered_iso_years():
        year_rows = weeks[weeks["iso_year"] == iso_year]
        if year_rows.empty:
            continue
        design = _design_annual_totals(cfg, weeks, iso_year)
        t_values = year_rows["t"].to_numpy()
        for channel_id in cfg.channels:
            realized = float(frame.loc[t_values, channel_id].sum())
            design_total = design[channel_id]
            rel_err = abs(realized - design_total) / design_total
            assert rel_err <= 0.10, (
                f"{scenario_id}/{channel_id}/{iso_year}: realized={realized!r} "
                f"design={design_total!r} rel_err={rel_err!r} exceeds SIM-031's 10% tolerance"
            )
        years_checked += 1

    assert years_checked > 0, f"{scenario_id}: no covered ISO year was checked"


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_flighted_zero_week_share_matches_schedule_exactly(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    weeks = week_index(cfg)
    frame = generate_spend(cfg, np.random.default_rng(cfg.seed), weeks)

    for channel_id in ("print_regional", "radio"):
        pattern = cfg.channels[channel_id].spend
        covered_t = _scheduled_burst_t_values(pattern, weeks)
        all_t = set(weeks["t"].to_numpy().tolist())
        non_covered_t = all_t - covered_t

        zero_on_non_covered = (frame.loc[sorted(non_covered_t), channel_id] == 0).all()
        positive_on_covered = (frame.loc[sorted(covered_t), channel_id] > 0).all()
        assert zero_on_non_covered, f"{scenario_id}/{channel_id}: a non-burst week is non-zero"
        assert positive_on_covered, f"{scenario_id}/{channel_id}: a burst week is zero"

        realized_zero_share = float((frame[channel_id] == 0).mean())
        schedule_zero_share = len(non_covered_t) / len(all_t)
        assert realized_zero_share == schedule_zero_share, (
            f"{scenario_id}/{channel_id}: realized zero-week share "
            f"{realized_zero_share!r} != schedule-implied {schedule_zero_share!r}"
        )


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_flighted_zero_week_share_within_ten_points_of_spec_nominal(scenario_id: str) -> None:
    """The schedule-implied zero share, over the *whole* scenario window (not a
    single partial year) -- S-C's pro-rated 2023 half-year sits near the lower
    edge of the radio tolerance in isolation by construction, so narrowing this
    check to one partial year would mask a real regression instead of catching
    one."""
    cfg = load_scenario(scenario_id)
    weeks = week_index(cfg)
    total_weeks = len(weeks)

    for channel_id, nominal in _NOMINAL_ZERO_SHARE.items():
        pattern = cfg.channels[channel_id].spend
        covered_t = _scheduled_burst_t_values(pattern, weeks)
        schedule_zero_share = 1.0 - len(covered_t) / total_weeks
        diff = abs(schedule_zero_share - nominal)
        assert diff <= 0.10, (
            f"{scenario_id}/{channel_id}: schedule zero share={schedule_zero_share!r} "
            f"nominal={nominal!r} diff={diff!r} exceeds SIM-031's 10pp tolerance"
        )


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_meta_pulse_fires_every_sixth_week(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    weeks = week_index(cfg)
    frame = generate_spend(cfg, np.random.default_rng(cfg.seed), weeks)

    t = weeks["t"].to_numpy()
    pulse_t = t[(t % 6) == 0]
    non_pulse_t = t[(t % 6) != 0]
    assert len(pulse_t) > 0, f"{scenario_id}: no pulse week found"
    assert len(non_pulse_t) > 0, f"{scenario_id}: no non-pulse week found"

    pulse_mean = float(frame.loc[pulse_t, "meta"].mean())
    non_pulse_mean = float(frame.loc[non_pulse_t, "meta"].mean())
    ratio = pulse_mean / non_pulse_mean
    rel_err = abs(ratio - 1.8) / 1.8
    assert rel_err <= 0.05, (
        f"{scenario_id}: pulse/non-pulse meta mean ratio={ratio!r} "
        f"(pulse_mean={pulse_mean!r}, non_pulse_mean={non_pulse_mean!r}) not within 5% of 1.8"
    )


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_burst_weeks_match_the_yaml_schedules_exactly(scenario_id: str) -> None:
    cfg = load_scenario(scenario_id)
    weeks = week_index(cfg)
    frame = generate_spend(cfg, np.random.default_rng(cfg.seed), weeks)

    for channel_id in ("print_regional", "radio"):
        pattern = cfg.channels[channel_id].spend
        expected_t = _scheduled_burst_t_values(pattern, weeks)
        realized_t = set(frame.index[frame[channel_id] > 0].tolist())
        assert realized_t == expected_t, (
            f"{scenario_id}/{channel_id}: non-zero weeks {sorted(realized_t)} != "
            f"YAML-schedule weeks {sorted(expected_t)}"
        )


def test_collinearity_stronger_advent_spend_in_s_b_than_s_a() -> None:
    cfg_a = load_scenario("s_a")
    cfg_b = load_scenario("s_b")
    weeks_a = week_index(cfg_a)
    weeks_b = week_index(cfg_b)
    frame_a = generate_spend(cfg_a, np.random.default_rng(cfg_a.seed), weeks_a)
    frame_b = generate_spend(cfg_b, np.random.default_rng(cfg_b.seed), weeks_b)

    for channel_id in ("search_generic", "meta"):
        advent_a = weeks_a["advent_flag"].to_numpy().astype(bool)
        t_a = weeks_a["t"].to_numpy()
        ratio_a = (
            frame_a.loc[t_a[advent_a], channel_id].mean()
            / frame_a.loc[t_a[~advent_a], channel_id].mean()
        )

        advent_b = weeks_b["advent_flag"].to_numpy().astype(bool)
        t_b = weeks_b["t"].to_numpy()
        ratio_b = (
            frame_b.loc[t_b[advent_b], channel_id].mean()
            / frame_b.loc[t_b[~advent_b], channel_id].mean()
        )

        assert ratio_b > ratio_a, (
            f"{channel_id}: SIM-030 expects a stronger S-B advent/non-advent spend ratio "
            f"than S-A, got ratio_a={ratio_a!r} ratio_b={ratio_b!r}"
        )


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_draw_order_is_channel_taxonomy_then_noise(scenario_id: str) -> None:
    """Pins the documented six-call, taxonomy-order draw sequence (module
    docstring's **Draw order** section): a follow-on draw taken from the same
    generator right after `generate_spend` returns is bit-for-bit reproducible
    across two fresh cfg.seed-seeded runs -- the property `assemble_scenario`
    (plan 02-06) needs for its own noise draw to be deterministic."""
    cfg = load_scenario(scenario_id)
    weeks = week_index(cfg)

    rng_1 = np.random.default_rng(cfg.seed)
    frame_1 = generate_spend(cfg, rng_1, weeks)
    follow_on_1 = rng_1.normal(size=cfg.weeks)

    rng_2 = np.random.default_rng(cfg.seed)
    frame_2 = generate_spend(cfg, rng_2, weeks)
    follow_on_2 = rng_2.normal(size=cfg.weeks)

    assert frame_1.equals(frame_2), f"{scenario_id}: generate_spend itself is not deterministic"
    assert np.array_equal(follow_on_1, follow_on_2), (
        f"{scenario_id}: the draw immediately following generate_spend() is not bit-for-bit "
        "reproducible -- the documented draw order may have been scrambled"
    )


def test_no_global_rng_seeding_in_simulate_package(repo_root: Path) -> None:
    """Anti-pattern A-5: the global NumPy RNG is never seeded or read anywhere in
    `src/ambo/simulate/`. Comment lines are stripped before scanning so a
    docstring line that merely *names* the forbidden entry point (to explain why
    it's forbidden) cannot make the scan self-invalidating."""
    simulate_dir = repo_root / "src" / "ambo" / "simulate"
    py_files = sorted(simulate_dir.rglob("*.py"))
    assert py_files, "No files found under src/ambo/simulate/ -- the scan is broken."

    forbidden = ("np.random.seed(", "numpy.random.seed(")
    offenders: list[str] = []
    for py_file in py_files:
        lines = py_file.read_text(encoding="utf-8").splitlines()
        code_lines = [line for line in lines if not line.strip().startswith("#")]
        code_text = "\n".join(code_lines)
        if any(pattern in code_text for pattern in forbidden):
            offenders.append(py_file.relative_to(repo_root).as_posix())

    assert not offenders, (
        "global NumPy RNG seeding found in src/ambo/simulate/ (anti-pattern A-5): "
        + ", ".join(offenders)
    )
