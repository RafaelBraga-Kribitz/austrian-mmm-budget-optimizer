-- stg_media_weekly: grain week x layer x channel. BP-D-03's unit-neutral renames
-- happen here -- this raw-to-staging boundary is the only place a `_eur`/`_aeur`
-- suffix may legitimately be dropped (AD-043). There is no `distinct`, `group by`,
-- or `row_number()` in this file: the inputs are canonical, and a duplicate grain
-- key must reach the `unique` test intact so it can fail (SPEC-03 section 2).
select
    week_start,
    layer,
    channel,
    cast(spend_eur as double) as spend,
    cast(null as bigint) as clicks,
    impressions,
    platform_conversions,
    platform_revenue_eur as platform_conv_value
from {{ ref('raw_media_p') }}

union all

select
    week_start,
    layer,
    channel,
    cast(spend_aeur as double) as spend,
    clicks,
    impressions,
    platform_conversions,
    platform_conv_value
from {{ ref('raw_media_r') }}
