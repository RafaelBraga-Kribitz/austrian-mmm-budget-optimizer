-- ad040_gapless_week_spine: AD-040's spine half. Singular test -- zero rows
-- returned = pass, any row returned = fail.
--
-- Deliberate departure from 05_IMPLEMENTATION_GUIDES.md section 8.3, which
-- instructs a `generate_series` week spine: this test derives the expected spine
-- from the committed `stg_calendar_weekly` seed instead (D-15). One calendar
-- governs the spine as well as the five calendar flags (AD-020), and there is zero
-- week arithmetic in SQL that could drift from the generator. The seed covers
-- 2019-2027, comfortably spanning Layer P's 156 weeks and Layer R's eventual
-- 52-104. This departure is recorded in docs/BUILD_LOG.md (plan 03-01) and must be
-- mentioned in the M2 PR description.
--
-- Empty-layer behaviour: a layer with no rows in fct_mmm_input contributes no row
-- to `bounds`, therefore no rows to `expected`, therefore no false spine
-- violation. This is why bounds come from the mart rather than from the
-- calendar's full range -- with layer_r_present false, Layer R is exactly that
-- empty case, and a calendar-driven spine would report every week of 2019-2027 as
-- a Layer R gap.
with bounds as (
    select layer, min(week_start) as min_week, max(week_start) as max_week
    from {{ ref('fct_mmm_input') }}
    group by layer
),

expected as (
    select bounds.layer, calendar.week_start
    from bounds
    inner join {{ ref('stg_calendar_weekly') }} as calendar
        on calendar.week_start between bounds.min_week and bounds.max_week
)

select expected.layer, expected.week_start
from expected
left join {{ ref('fct_mmm_input') }} as mart
    on expected.layer = mart.layer and expected.week_start = mart.week_start
where mart.week_start is null
