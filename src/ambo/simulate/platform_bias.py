"""Simulated platform reporting with the known over-credit of SPEC-01 section 6
(SIM-060, SIM-061), plus BP-D-02's impressions/conversions completion of
`media_weekly.csv`'s three still-null columns (T-106).

Implements: REQ-q1-truth-recovery

This module is pure: every value it returns is derived from the `SimulationResult`
it is handed, and it performs no I/O of its own (the media placeholder frame and
the calendar/config data it completes were already read by `assemble_scenario` and
`load_scenario`). It imports nothing from `ambo.model` (SIM-003) -- the over-credit
injected here is exactly the known quantity Phase 8's DC-702 attribution-gap gate
must later recover, so keeping this module's own math independent of anything the
model touches is what makes that later recovery evidence rather than a tautology.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ambo.common.errors import SimulationError
from ambo.simulate.config import SPEC_CHANNEL_ORDER
from ambo.simulate.dgp import SimulationResult, round_half_up

# SIM-004's six `media_weekly.csv` columns, in order -- what `platform_report`
# both expects on its input `result.media` and guarantees on its return value.
_MEDIA_COLUMNS: tuple[str, ...] = (
    "week_start",
    "channel",
    "spend_eur",
    "impressions",
    "platform_conversions",
    "platform_revenue_eur",
)

_PLATFORM_COLUMNS: tuple[str, ...] = (
    "impressions",
    "platform_conversions",
    "platform_revenue_eur",
)


def _validate_media_shape(result: SimulationResult) -> None:
    """`platform_report` is a completion step, not a reshaping one: it raises
    `SimulationError` rather than silently accepting a `media` frame whose row
    count or column set does not already match SIM-004."""
    media = result.media
    expected_rows = 6 * result.cfg.weeks
    if len(media) != expected_rows:
        raise SimulationError(
            f"platform_report(): expected {expected_rows} row(s) in result.media "
            f"(6 * cfg.weeks), got {len(media)}"
        )
    if set(media.columns) != set(_MEDIA_COLUMNS):
        raise SimulationError(
            f"platform_report(): result.media columns must be exactly "
            f"{_MEDIA_COLUMNS!r}, got {tuple(media.columns)!r}"
        )


def platform_report(result: SimulationResult) -> pd.DataFrame:
    """Complete `result.media`'s three platform-reporting columns (SPEC-01 section
    6, T-106) -- the `03_MODULES.md` section 2.4 `platform_report(result) ->
    pd.DataFrame` contract.

    `share_{c,t}` is channel `c`'s share of total spend across all six channels in
    week `t`: `spend_{c,t} / total_spend_t`, computed via a guarded expression
    (`np.where(total > 0, spend / np.where(total > 0, total, 1.0), 0.0)`) so a
    zero-total-spend week never evaluates a division by zero -- `share_c` is
    exactly `0.0` for every channel that week, never NaN or infinity.

    For each online channel (`cfg.channels[c].platform.phi is not None`):
    `platform_revenue_{c,t} = m_{c,t} * phi_c + theta_c * base_t * share_{c,t}`,
    `impressions_{c,t} = round_half_up(spend_{c,t} / cpm_c * 1000)`, and
    `platform_conversions_{c,t} = round_half_up(platform_revenue_{c,t} / AOV_t)`
    where `AOV_t = cfg.aov_base + cfg.aov_advent_bonus * advent_flag_t` -- the
    same AOV rule `assemble_scenario` uses for `orders`. `phi`, `theta` and `cpm`
    are read from `result.cfg` -- this module contains no such literal, so
    SPEC-01 section 6's table keeps exactly one home (the scenario YAML).

    `print_regional` and `radio` (`platform.phi is None`) carry NULL in all three
    platform columns for every week: offline channels have no platform reporting
    at all. The three columns are pandas nullable dtypes (`Int64` for
    `impressions`/`platform_conversions`, `Float64` for `platform_revenue_eur`) so
    that NULL is a true missing value, distinguishable from `0`, and survives to
    an empty field when the frame is later written to CSV.

    Returns a frame with exactly `6 * cfg.weeks` rows and SIM-004's six columns in
    order, with row order identical to the input `result.media`'s row order (this
    function never re-sorts).
    """
    _validate_media_shape(result)

    cfg = result.cfg
    weeks = result.weeks
    spend = result.spend
    components = result.components

    total_spend = spend[list(SPEC_CHANNEL_ORDER)].sum(axis=1).to_numpy(dtype=np.float64)
    safe_total = np.where(total_spend > 0.0, total_spend, 1.0)

    base = components["base"].to_numpy(dtype=np.float64)
    aov = cfg.aov_base + cfg.aov_advent_bonus * weeks["advent_flag"].to_numpy(dtype=np.float64)
    week_start = weeks["week_start"].to_numpy()

    per_channel_frames: list[pd.DataFrame] = []
    for channel_id in SPEC_CHANNEL_ORDER:
        platform = cfg.channels[channel_id].platform
        channel_spend = spend[channel_id].to_numpy(dtype=np.float64)
        share = np.where(total_spend > 0.0, channel_spend / safe_total, 0.0)

        if platform.phi is None:
            # Offline channel: no platform reporting at all (SPEC-01 section 6).
            impressions = pd.array([pd.NA] * len(weeks), dtype="Int64")
            conversions = pd.array([pd.NA] * len(weeks), dtype="Int64")
            revenue = pd.array([pd.NA] * len(weeks), dtype="Float64")
        else:
            m_c = components[f"m_{channel_id}"].to_numpy(dtype=np.float64)
            platform_revenue = m_c * platform.phi + platform.theta * base * share
            impressions_raw = round_half_up(channel_spend / platform.cpm * 1000.0)
            conversions_raw = round_half_up(platform_revenue / aov)
            impressions = pd.array(impressions_raw, dtype="Int64")
            conversions = pd.array(conversions_raw, dtype="Int64")
            revenue = pd.array(platform_revenue, dtype="Float64")

        per_channel_frames.append(
            pd.DataFrame(
                {
                    "week_start": week_start,
                    "channel": channel_id,
                    "impressions": impressions,
                    "platform_conversions": conversions,
                    "platform_revenue_eur": revenue,
                }
            )
        )

    platform_values = pd.concat(per_channel_frames, ignore_index=True)

    out = result.media.drop(columns=list(_PLATFORM_COLUMNS)).merge(
        platform_values, on=["week_start", "channel"], how="left", validate="one_to_one"
    )
    return out.reindex(columns=list(_MEDIA_COLUMNS))
