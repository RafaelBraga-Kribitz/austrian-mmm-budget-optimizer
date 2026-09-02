"""The disclosed data-generating process's mathematical core (SPEC-01 section 2.1,
2.2, 2.3; SIM-003; SIM-071...074; AD-020).

Implements: REQ-q1-truth-recovery, REQ-grain-and-windows

This module reads the committed calendar seed `dbt/seeds/season_windows.csv` and
never recomputes any window rule -- the five window rules (advent, schulbeginn,
jan_dip, spring, summer_lull) live in `scripts/generate_season_windows.py` and are
frozen there (AD-020, the single sanctioned shared-CONFIG exception to the
simulator-versus-model firewall).

Nothing in this module is imported from or shared with `ambo.model`: the simulator
implements its own adstock and Hill saturation, independently derived and
independently tested, so the Phase 5 recovery result -- "the model recovered the
true parameters" -- is evidence rather than a tautology (SIM-003, 09_ANTI_PATTERNS
A-1). `tests/unit/test_import_independence.py` enforces this mechanically.

This is the first half of `dgp.py` (T-103, T-104): the calendar spine, the
seasonal index, baseline demand, the rounding convention, and the simulator's own
adstock/Hill. `assemble_scenario`, `SimulationResult` and the SIM-071/072 audits
are plan 02-06's second half of this same file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from ambo.common.config import repo_root
from ambo.common.errors import SimulationError
from ambo.simulate.config import SPEC_CHANNEL_ORDER, ScenarioConfig, SeasonWeights

# The committed calendar seed (AD-020): the sole calendar authority for this
# module. Never recomputed here -- see the module docstring.
SEED_PATH = repo_root() / "dbt" / "seeds" / "season_windows.csv"

# The five window-flag columns, copied through `week_index()` untouched.
_FLAG_COLUMNS: tuple[str, ...] = (
    "advent_flag",
    "schulbeginn_flag",
    "jan_dip_flag",
    "spring_flag",
    "summer_lull_flag",
)


def round_half_up(values: np.ndarray) -> np.ndarray:
    """Round `values` to the nearest whole unit, half away from zero.

    This is the single project-wide rounding convention for whole-euro and
    whole-order quantities in this phase (A-8): every other `simulate/` module
    that needs whole-unit rounding (`spend_patterns.py`'s spend floor/round step,
    the orders computation) imports `round_half_up` from here rather than
    reimplementing it. Deliberately not `np.rint`, whose half-to-even
    ("banker's rounding") behaviour would round `0.5 -> 0` and `2.5 -> 2`; this
    function rounds `0.5 -> 1` and `2.5 -> 3`, matching BP-D-09's pro-rating
    convention. Assumes non-negative input, as every caller in this phase's
    domain guarantees (spend and revenue are never negative here).
    """
    return np.floor(values + 0.5).astype(np.int64)


def week_index(cfg: ScenarioConfig) -> pd.DataFrame:
    """Return the gapless, ISO-Monday-aligned weekly spine for `cfg`'s window.

    Reads `SEED_PATH` and filters to rows whose `(iso_year, iso_week)` tuple lies
    inclusively between `cfg`'s start and end endpoints, under plain tuple
    comparison. Raises `SimulationError` -- naming the offending key -- if any of
    the following does not hold: the filtered row count equals `cfg.weeks`; no
    duplicate `(iso_year, iso_week)` key; `week_start` strictly increasing; every
    consecutive `week_start` difference is exactly 7 days; every `week_start` is a
    Monday. A missing or duplicated calendar row is never silently defaulted to an
    unflagged week (AD-020).

    Returns a frame with `iso_year`, `iso_week`, `week_start` (datetime64), a new
    1-indexed `t` column (`1..T`, SPEC-01 section 2's weekly index), and the five
    window-flag columns as `int64` -- copied through untouched, since this
    function classifies nothing. Index is reset.
    """
    seed = pd.read_csv(SEED_PATH, parse_dates=["week_start"])

    window_start = (cfg.start_iso_year, cfg.start_iso_week)
    window_end = (cfg.end_iso_year, cfg.end_iso_week)
    keys = list(zip(seed["iso_year"], seed["iso_week"], strict=True))
    in_window = [window_start <= key <= window_end for key in keys]
    weeks = seed.loc[in_window].reset_index(drop=True)

    if weeks.empty:
        raise SimulationError(
            f"week_index(): no season_windows.csv rows found for window "
            f"[{window_start}..{window_end}]"
        )

    duplicate_mask = weeks.duplicated(subset=["iso_year", "iso_week"], keep=False)
    if duplicate_mask.any():
        duplicate_keys = sorted(
            set(
                zip(
                    weeks.loc[duplicate_mask, "iso_year"],
                    weeks.loc[duplicate_mask, "iso_week"],
                    strict=True,
                )
            )
        )
        raise SimulationError(
            f"week_index(): duplicate (iso_year, iso_week) key(s) in {SEED_PATH}: {duplicate_keys}"
        )

    weeks = weeks.sort_values(["iso_year", "iso_week"]).reset_index(drop=True)

    if len(weeks) != cfg.weeks:
        found_keys = sorted(set(zip(weeks["iso_year"], weeks["iso_week"], strict=True)))
        expected_keys = _expected_keys(cfg.start_iso_year, cfg.start_iso_week, cfg.weeks)
        missing = sorted(set(expected_keys) - set(found_keys))
        raise SimulationError(
            f"week_index(): expected {cfg.weeks} week(s) for window "
            f"[{window_start}..{window_end}], found {len(weeks)} in {SEED_PATH}"
            + (f"; missing key(s): {missing}" if missing else "")
        )

    if not weeks["week_start"].is_monotonic_increasing:
        raise SimulationError(
            f"week_index(): week_start is not strictly increasing for window "
            f"[{window_start}..{window_end}]"
        )

    diffs = weeks["week_start"].diff().dropna()
    bad_gap_mask = diffs != pd.Timedelta(days=7)
    if bad_gap_mask.any():
        bad_index = diffs.index[bad_gap_mask][0]
        prev_key = (
            weeks.loc[bad_index - 1, "iso_year"],
            weeks.loc[bad_index - 1, "iso_week"],
        )
        bad_key = (weeks.loc[bad_index, "iso_year"], weeks.loc[bad_index, "iso_week"])
        raise SimulationError(
            f"week_index(): non-7-day gap between {prev_key} and {bad_key} in {SEED_PATH}"
        )

    non_monday_mask = weeks["week_start"].dt.dayofweek != 0
    if non_monday_mask.any():
        bad_index = non_monday_mask.idxmax()
        bad_key = (weeks.loc[bad_index, "iso_year"], weeks.loc[bad_index, "iso_week"])
        raise SimulationError(
            f"week_index(): week_start for key {bad_key} in {SEED_PATH} is not a Monday"
        )

    weeks["t"] = np.arange(1, len(weeks) + 1, dtype=np.int64)
    for column in _FLAG_COLUMNS:
        weeks[column] = weeks[column].astype(np.int64)

    return weeks[["iso_year", "iso_week", "week_start", "t", *_FLAG_COLUMNS]].reset_index(drop=True)


def _expected_keys(start_iso_year: int, start_iso_week: int, count: int) -> list[tuple[int, int]]:
    """The `count` consecutive `(iso_year, iso_week)` keys starting at
    `(start_iso_year, start_iso_week)`, one per week, used only to name a missing
    key in a `SimulationError` message when the seed itself is short a row.

    Computed via `date.fromisocalendar`/`isocalendar()` -- plain ISO-calendar
    arithmetic to reconstruct the gapless spine `cfg` declares, independent of
    whatever the (possibly short) seed file actually contains. This is not a
    window-rule reimplementation (AD-020 forbids recomputing advent/schulbeginn/
    jan_dip/spring/summer_lull, not the plain weekly count); it is the only way
    to name a key that is, by definition, absent from the seed being diagnosed.
    """
    monday = date.fromisocalendar(start_iso_year, start_iso_week, 1)
    keys: list[tuple[int, int]] = []
    for _ in range(count):
        iso_year, iso_week, _ = monday.isocalendar()
        keys.append((iso_year, iso_week))
        monday += timedelta(days=7)
    return keys


def season_index(weeks: pd.DataFrame, season_weights: SeasonWeights) -> np.ndarray:
    """Return the multiplicative season index for each row of `weeks` (SPEC-01
    section 2.1).

    `1.0 + advent*advent_flag + schulbeginn*schulbeginn_flag + spring*spring_flag
    + jan_dip*jan_dip_flag + summer_lull*summer_lull_flag`. The YAML stores
    `jan_dip` and `summer_lull` **signed negative** (matching SPEC-01 section
    2.1's `- 0.20 x` / `- 0.10 x` notation), so all five terms are added here with
    no sign flip in code -- negating a value that is already negative in
    configuration would double-apply the sign, which is the obvious silent bug
    this function's tests guard against. A week with all five flags 0 returns
    exactly `1.0`; an adjacent flagged window never bleeds across its boundary
    because each term is gated by its own flag column, not by proximity.
    """
    w = season_weights
    result = (
        1.0
        + w.advent * weeks["advent_flag"].to_numpy()
        + w.schulbeginn * weeks["schulbeginn_flag"].to_numpy()
        + w.spring * weeks["spring_flag"].to_numpy()
        + w.jan_dip * weeks["jan_dip_flag"].to_numpy()
        + w.summer_lull * weeks["summer_lull_flag"].to_numpy()
    )
    return np.asarray(result, dtype=np.float64)


def baseline_demand(cfg: ScenarioConfig, weeks: pd.DataFrame) -> pd.DataFrame:
    """Return `cfg`'s baseline-demand components for each row of `weeks` (SPEC-01
    section 2.1): `base_t = b0 * (1 + g)^t * season_t * promo_mult_t`.

    Every component is returned as its own column, not just `base` -- T-103's
    second acceptance criterion, and what plan 02-06's SIM-071 decomposition
    audit re-sums: `trend` (`(1 + cfg.growth) ** t`), `season` (from
    `season_index`), `promo_mult` (`cfg.promo_multiplier` where `(iso_year,
    iso_week)` is listed in `cfg.promo_weeks`, else `1.0`), `promo_flag` (the
    same condition as an int 0/1), and `base` (`cfg.b0 * trend * season *
    promo_mult`).
    """
    t = weeks["t"].to_numpy()
    trend = (1.0 + cfg.growth) ** t
    season = season_index(weeks, cfg.season_weights)

    promo_flag = np.array(
        [
            1 if iso_week in cfg.promo_weeks.get(iso_year, ()) else 0
            for iso_year, iso_week in zip(weeks["iso_year"], weeks["iso_week"], strict=True)
        ],
        dtype=np.int64,
    )
    promo_mult = np.where(promo_flag == 1, cfg.promo_multiplier, 1.0)

    base = cfg.b0 * trend * season * promo_mult

    return pd.DataFrame(
        {
            "trend": trend,
            "season": season,
            "promo_mult": promo_mult,
            "promo_flag": promo_flag,
            "base": base,
        }
    )


def adstock_recursive(x: np.ndarray, lam: float) -> np.ndarray:
    """Geometric adstock (SPEC-01 section 2.2): `a_t = x_t + lam * a_{t-1}`, with
    `a_0 = 0` (equivalently, `a[0] = x[0]` in this 0-indexed array form).

    Pure, O(T), causal: `a_t` depends only on `x_{<=t}`. Computed with a plain
    forward loop over `t` -- deliberately not vectorized with `np.cumsum`,
    `np.convolve`, `scipy.signal.lfilter` or a strided trick, per
    `05_IMPLEMENTATION_GUIDES.md` section 1.4 and 09_ANTI_PATTERNS A-14: those
    forms are exactly where the project's named trap T-2 (convolution-direction
    reversal) hides, and a clever vectorization must never be traded for the
    causality property this function exists to guarantee.

    Validates first, raising `SimulationError` naming the offending value and the
    expected domain on any violation: `x` must be a 1-D array, every element
    finite and non-negative; `lam` must satisfy `0.0 <= lam < 1.0` (`lam == 1.0`
    is rejected explicitly because the closed form `x / (1 - lam)` diverges
    there).

    An empty `x` returns an empty array without raising -- a documented
    total-function property, not a reachable case in this phase's normal flow,
    since a valid `ScenarioConfig.weeks` is always one of `{156, 104, 78}`.
    """
    if x.ndim != 1:
        raise SimulationError(f"adstock_recursive(): x must be 1-D, got ndim={x.ndim!r}")
    if not np.all(np.isfinite(x)):
        raise SimulationError("adstock_recursive(): x must be all-finite, found NaN or infinity")
    if x.size > 0 and np.any(x < 0.0):
        raise SimulationError(
            f"adstock_recursive(): x must be all non-negative, found min={x.min()!r}"
        )
    if not (0.0 <= lam < 1.0):
        raise SimulationError(
            f"adstock_recursive(): lam must satisfy 0.0 <= lam < 1.0, got {lam!r}"
        )

    a = np.empty_like(x, dtype=np.float64)
    for t in range(x.shape[0]):
        a[t] = x[t] if t == 0 else x[t] + lam * a[t - 1]
    return a


def hill(a: np.ndarray, K: float, s: float) -> np.ndarray:
    """Hill saturation on adstocked spend (SPEC-01 section 2.2): `h = a^s / (a^s
    + K^s)`.

    `hill(K, K, s)` is exactly 0.5 for every `s > 0`, because numerator and
    denominator differ by exactly a factor of two in floating point when `a ==
    K`. `hill(0, K, s)` is exactly 0.0. Output lies in `[0, 1]` and is
    monotonically non-decreasing in `a` for every in-domain `(K, s)`.

    Validates first, raising `SimulationError` naming the offending value and the
    expected domain on any violation: `a` must be all finite and non-negative;
    `K` and `s` must both be strictly positive. A negative `a`, a non-finite `a`,
    or a non-positive `K`/`s` never silently produces a NaN.
    """
    if not np.all(np.isfinite(a)):
        raise SimulationError("hill(): a must be all-finite, found NaN or infinity")
    if a.size > 0 and np.any(a < 0.0):
        raise SimulationError(f"hill(): a must be all non-negative, found min={a.min()!r}")
    if not K > 0.0:
        raise SimulationError(f"hill(): K must be > 0, got {K!r}")
    if not s > 0.0:
        raise SimulationError(f"hill(): s must be > 0, got {s!r}")

    a_s = a**s
    result: np.ndarray = a_s / (a_s + K**s)
    return result


# The per-channel media-contribution component columns (`m_<c>`) stored in
# `SimulationResult.components`, in `SPEC_CHANNEL_ORDER` -- what SIM-071 re-sums.
_CONTRIBUTION_COLUMNS: tuple[str, ...] = tuple(f"m_{c}" for c in SPEC_CHANNEL_ORDER)


def _max_decomposition_deviation(components: pd.DataFrame) -> tuple[float, int]:
    """The SIM-071 re-sum: `base + Σ_c m_c + eps`, re-summed from `components`'s own
    stored arrays (never from any expression that produced `revenue_pre_clip` at
    construction time), compared against the stored `revenue_pre_clip` column.

    Returns `(max_abs_deviation, worst_row_position)`. Shared by
    `SimulationResult.__post_init__` (which raises `SimulationError` when the
    deviation exceeds 1e-6) and the public `decomposition_audit` function (plan
    02-06 Task 2), so the two never drift out of sync with each other.
    """
    channel_sum = components[list(_CONTRIBUTION_COLUMNS)].sum(axis=1).to_numpy()
    recomputed = components["base"].to_numpy() + channel_sum + components["eps"].to_numpy()
    deviation = np.abs(recomputed - components["revenue_pre_clip"].to_numpy())
    worst_position = int(np.argmax(deviation))
    return float(deviation[worst_position]), worst_position


@dataclass(frozen=True)
class SimulationResult:
    """The full assembled output of one `assemble_scenario` run (SPEC-01 §2.3, T-105).

    `cfg` — the scenario this result was built from. `weeks` — `week_index(cfg)`'s
    output, the gapless ISO-Monday spine. `spend` — `generate_spend`'s wide
    week x channel frame (int €). `components` — every intermediate array kept for
    audit: `trend`, `season`, `promo_mult`, `promo_flag`, `base` (from
    `baseline_demand`); `adstock_<c>`/`m_<c>` per channel in `SPEC_CHANNEL_ORDER`;
    `eps`; `revenue_pre_clip`; `revenue` (post-clip). `media` — the SIM-004 long
    frame with `week_start`, `channel`, `spend_eur` plus three all-null placeholder
    columns (`impressions`, `platform_conversions`, `platform_revenue_eur`) that
    plan 02-07's `platform_bias.platform_report` populates; sorted by `week_start`
    ascending then `SPEC_CHANNEL_ORDER` position. `outcome` — the SIM-004
    `week_start`, `revenue_eur`, `orders`, `promo_flag` frame, sorted by
    `week_start` ascending.

    Invariant (SIM-071): constructing a `SimulationResult` whose `components` do
    not re-sum to `revenue_pre_clip` within 1e-6 raises `SimulationError` in
    `__post_init__` — this makes the decomposition invariant a constructor
    precondition, not an after-the-fact report. A `SimulationResult` that
    violates the decomposition cannot exist.
    """

    cfg: ScenarioConfig
    weeks: pd.DataFrame
    spend: pd.DataFrame
    components: pd.DataFrame
    media: pd.DataFrame
    outcome: pd.DataFrame

    def __post_init__(self) -> None:
        max_deviation, worst_position = _max_decomposition_deviation(self.components)
        if max_deviation > 1e-6:
            worst_week = self.weeks["week_start"].iloc[worst_position]
            raise SimulationError(
                f"SimulationResult(): SIM-071 decomposition invariant violated at week "
                f"{worst_week.date()} (row {worst_position}): base + sum(m_c) + eps deviates "
                f"from the stored revenue_pre_clip by {max_deviation!r}, exceeding tolerance 1e-6"
            )


def assemble_scenario(cfg: ScenarioConfig, rng: np.random.Generator) -> SimulationResult:
    """Assemble one scenario run into a `SimulationResult` (SPEC-01 §2.2/§2.3, T-105).

    The only orchestrator in this module. Sequence, in exactly this order:
    `week_index` -> `baseline_demand` -> `generate_spend` (the generator's first
    six draw calls, `spend_patterns.py`'s documented order) -> per-channel
    adstock/Hill in `SPEC_CHANNEL_ORDER` (a plain loop, never vectorized across
    channels, per A-14) -> one `rng.normal` noise draw, strictly after
    `generate_spend` on the same generator (SPEC-01 §2.3, Guide §1.3's documented
    draw-order contract) -> revenue assembly and the ≥0 clip -> orders via
    `round_half_up` -> the two SIM-004 frames.

    `generate_spend` is imported locally (function-scoped, not at module level):
    `spend_patterns.py` imports `round_half_up` from this module, so a top-level
    import here would create an import cycle (A-15) between `dgp.py` and
    `spend_patterns.py`.

    Returns a `SimulationResult`, letting `__post_init__` run the SIM-071 audit.
    """
    from ambo.simulate.spend_patterns import generate_spend

    weeks = week_index(cfg)
    baseline = baseline_demand(cfg, weeks)
    spend = generate_spend(cfg, rng, weeks)

    component_columns: dict[str, np.ndarray] = {
        "trend": baseline["trend"].to_numpy(),
        "season": baseline["season"].to_numpy(),
        "promo_mult": baseline["promo_mult"].to_numpy(),
        "promo_flag": baseline["promo_flag"].to_numpy(),
        "base": baseline["base"].to_numpy(),
    }

    channel_sum = np.zeros(len(weeks), dtype=np.float64)
    for channel_id in SPEC_CHANNEL_ORDER:
        params = cfg.channels[channel_id].true_params
        x = spend[channel_id].to_numpy(dtype=np.float64)
        a_c = adstock_recursive(x, params.lam)
        m_c = params.beta * hill(a_c, params.K, params.s)
        component_columns[f"adstock_{channel_id}"] = a_c
        component_columns[f"m_{channel_id}"] = m_c
        channel_sum = channel_sum + m_c

    sigma = cfg.noise_share * float(baseline["base"].mean())
    eps = rng.normal(0.0, sigma, size=len(weeks))
    component_columns["eps"] = eps

    revenue_pre_clip = component_columns["base"] + channel_sum + eps
    revenue = np.maximum(revenue_pre_clip, 0.0)
    component_columns["revenue_pre_clip"] = revenue_pre_clip
    component_columns["revenue"] = revenue

    components = pd.DataFrame(component_columns)

    aov = cfg.aov_base + cfg.aov_advent_bonus * weeks["advent_flag"].to_numpy()
    orders = round_half_up(revenue / aov)

    media = pd.concat(
        [
            pd.DataFrame(
                {
                    "week_start": weeks["week_start"].to_numpy(),
                    "channel": channel_id,
                    "spend_eur": spend[channel_id].to_numpy(),
                }
            )
            for channel_id in SPEC_CHANNEL_ORDER
        ],
        ignore_index=True,
    )
    media["impressions"] = np.nan
    media["platform_conversions"] = np.nan
    media["platform_revenue_eur"] = np.nan
    media["channel"] = pd.Categorical(media["channel"], categories=SPEC_CHANNEL_ORDER, ordered=True)
    media = media.sort_values(["week_start", "channel"]).reset_index(drop=True)
    media["channel"] = media["channel"].astype(str)

    outcome = (
        pd.DataFrame(
            {
                "week_start": weeks["week_start"].to_numpy(),
                "revenue_eur": revenue,
                "orders": orders,
                "promo_flag": component_columns["promo_flag"],
            }
        )
        .sort_values("week_start")
        .reset_index(drop=True)
    )

    return SimulationResult(
        cfg=cfg, weeks=weeks, spend=spend, components=components, media=media, outcome=outcome
    )


def decomposition_audit(result: SimulationResult) -> float:
    """SIM-071: the maximum absolute deviation of `base + Σ_c m_c + eps` from the
    stored `revenue_pre_clip`, re-summed from `result.components`'s own stored
    arrays -- never from any expression that produced revenue at construction
    time (evidence, not a report about a report). Passes when the returned value
    is `<= 1e-6`. `SimulationResult.__post_init__` already makes this a
    construction-time invariant; this function exists so 02-09's gate runner can
    print the realized number `10_VALIDATION_GATES.md` §3 requires.
    """
    max_deviation, _ = _max_decomposition_deviation(result.components)
    return max_deviation


def plausibility_audit(result: SimulationResult) -> dict[str, float]:
    """SIM-072: plausibility statistics for `result`, returned as evidence (not a
    bare boolean) so 02-09's gate runner can print the numbers
    `10_VALIDATION_GATES.md` §3 asks for.

    Returns `min_revenue_pre_clip` (the minimum of the pre-clip revenue series --
    SIM-072 passes when this is `>= 0`, proving the `>= 0` clip in
    `assemble_scenario` never actually binds), `noise_variance_share`
    (`var(eps) / var(revenue_pre_clip)`, passes when in `[0.02, 0.10]`), and one
    `media_share_<iso_year>` entry per ISO year `result.weeks` covers
    (`Σ_c Σ_t m_{c,t} / Σ_t revenue_t`, restricted to that year's weeks; passes
    when in `[0.15, 0.45]`).
    """
    components = result.components
    revenue_pre_clip = components["revenue_pre_clip"].to_numpy()
    revenue = components["revenue"].to_numpy()
    eps = components["eps"].to_numpy()

    stats: dict[str, float] = {
        "min_revenue_pre_clip": float(revenue_pre_clip.min()),
        "noise_variance_share": float(np.var(eps) / np.var(revenue_pre_clip)),
    }

    total_media = components[list(_CONTRIBUTION_COLUMNS)].sum(axis=1).to_numpy()
    iso_years = result.weeks["iso_year"].to_numpy()
    for iso_year in sorted(set(iso_years)):
        mask = iso_years == iso_year
        stats[f"media_share_{iso_year}"] = float(total_media[mask].sum() / revenue[mask].sum())

    return stats


def peak_week_audit(result: SimulationResult) -> dict[int, tuple[int, bool]]:
    """SIM-073: per covered ISO year, `(peak_week_number, carries_advent_flag)`
    for that year's maximum-revenue week. Passes when every *audited* year's
    boolean is `True`.

    A year is audited only if its Advent window lies inside `result`'s covered
    span. This is detected as "does at least one row of that year carry
    `advent_flag == 1`" -- the Advent window sits at the end of the calendar
    year, so a window whose coverage ends before Advent (e.g. S-C's 2023
    half-year, ISO weeks 01-26) never has an `advent_flag == 1` row for that
    year and is therefore known not to be fully covered, without recomputing
    any calendar rule (AD-020).

    **Skipped-year convention (docstring-declared, not an inline comment, so a
    caller can rely on it):** a year that is not audited is still present in the
    returned mapping, recorded as the sentinel `(-1, True)` -- peak week `-1`
    (never a valid ISO week) paired with boolean `True` (so a skipped year can
    never itself fail the "every value's boolean is True" SIM-073 pass
    condition). This makes a skipped year visible to a caller (e.g. 02-09's gate
    runner, which can filter on `peak_week == -1` to report it) rather than
    silently absent from the mapping.
    """
    weeks = result.weeks
    revenue = result.components["revenue"].to_numpy()
    iso_years = weeks["iso_year"].to_numpy()
    iso_weeks = weeks["iso_week"].to_numpy()
    advent_flags = weeks["advent_flag"].to_numpy()

    audit: dict[int, tuple[int, bool]] = {}
    for iso_year in sorted(set(iso_years)):
        mask = iso_years == iso_year
        year_advent = advent_flags[mask]
        if not year_advent.any():
            audit[int(iso_year)] = (-1, True)
            continue
        year_revenue = revenue[mask]
        year_weeks = iso_weeks[mask]
        peak_position = int(np.argmax(year_revenue))
        audit[int(iso_year)] = (
            int(year_weeks[peak_position]),
            bool(year_advent[peak_position] == 1),
        )

    return audit
