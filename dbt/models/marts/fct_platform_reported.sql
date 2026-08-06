-- fct_platform_reported: the third contract-enforced mart (D-07, SPEC-03 section 3),
-- grain week x layer x channel. Materialized as a table (dbt_project.yml `marts:
-- +materialized: table`); contract enforced by
-- `_fct_platform_reported__schema.yml`.
--
-- A straight six-column projection of stg_media_weekly, already at this mart's
-- grain -- no aggregation, no filtering, no coalescing. NULL platform metrics on an
-- offline channel (e.g. print_regional) survive here as NULL: coercing them to 0
-- would make a channel that reports nothing indistinguishable from a channel that
-- reports zero, exactly the confusion AGENTS T-8 warns about in the attribution-gap
-- module (SPEC-06 section 5, DC-501/DC-502) that consumes this mart. Platform
-- numbers are the OBJECT of study there, never a calibration target.
--
-- `clicks` is deliberately not projected. It is NULL on every Layer P row today
-- (stg_media_weekly casts it so) and arrives with real content only at M4 when Layer
-- R's intake pipeline lands it -- see this model's own schema description for the
-- D-24 pre-declaration of that planned amendment.
select
    cast(week_start as date) as week_start,
    cast(layer as varchar) as layer,
    cast(channel as varchar) as channel,
    cast(platform_conversions as bigint) as platform_conversions,
    cast(platform_conv_value as double) as platform_conv_value,
    cast(impressions as bigint) as impressions
from {{ ref('stg_media_weekly') }}
