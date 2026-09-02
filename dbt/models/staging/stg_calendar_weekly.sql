-- stg_calendar_weekly: grain week. Typed passthrough of the season_windows seed --
-- no date arithmetic, no window recomputation, no `generate_series` here. The seed
-- is the single source of Austrian-calendar window definitions (AD-020), shared
-- with the simulator; this model reproduces it row-for-row.
select
    iso_year,
    iso_week,
    week_start,
    cast(advent_flag as integer) as advent_flag,
    cast(schulbeginn_flag as integer) as schulbeginn_flag,
    cast(jan_dip_flag as integer) as jan_dip_flag,
    cast(spring_flag as integer) as spring_flag,
    cast(summer_lull_flag as integer) as summer_lull_flag
from {{ ref('season_windows') }}
