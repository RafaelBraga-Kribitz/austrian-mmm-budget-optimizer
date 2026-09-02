-- dim_layer: the layer-grain dimension (D-07, SPEC-03 section 3). Materialized as a
-- table (dbt_project.yml `marts: +materialized: table`); contract enforced by
-- `_dim_layer__schema.yml`.
--
-- present: distinct (layer, channel) pairs that have at least one source row in
-- stg_media_weekly. This is D-13's derivation -- a channel is present if and only if
-- it has rows in staging for that layer. Never derived from nonzero spend: a
-- nonzero-spend derivation would silently reclassify a real channel with a
-- legitimate zero-spend period, and on Layer R it could disagree with the intake
-- manifest, putting AD-044 (plan 03-06) in the position of failing for a reason that
-- has nothing to do with the actual defect it exists to catch.
with present as (
    select distinct layer, channel
    from {{ ref('stg_media_weekly') }}
),

-- ordinal: the channel_taxonomy var's own order, materialized as (channel, position)
-- pairs via a jinja loop -- the mechanism that makes BP-D-19's "canonical taxonomy
-- order" a checked fact rather than an assumption about SQL's default row order.
ordinal as (
    select *
    from (
        values
        {% for channel in var('channel_taxonomy') %}
        ('{{ channel }}', {{ loop.index }}){{ "," if not loop.last }}
        {% endfor %}
    ) as t(channel, position)
),

-- joined: per-layer comma-joined channels_present string, ordered by taxonomy
-- position. The inner join to `ordinal` is deliberate -- a source channel outside
-- the taxonomy is dropped here rather than silently appended; catching that case is
-- AD-044's job (plan 03-06), and listing an unknown channel here would defeat it.
joined as (
    select
        present.layer,
        string_agg(present.channel, ',' order by ordinal.position) as channels_present
    from present
    inner join ordinal
        on present.channel = ordinal.channel
    group by present.layer
),

-- weeks: distinct week count per layer, from stg_outcome_weekly. This CTE also
-- drives the final grain -- a layer with outcome rows but no media rows still
-- produces a dim_layer row (channels_present coalesced to '') rather than vanishing.
-- With layer_r_present false, the staging unions contribute zero Layer R rows, so
-- this CTE (and therefore the whole model) naturally contains exactly the three
-- Layer P rows -- no placeholder Layer R row is ever fabricated.
weeks as (
    select
        layer,
        count(distinct week_start) as weeks
    from {{ ref('stg_outcome_weekly') }}
    group by layer
)

select
    cast(weeks.layer as varchar) as layer,
    cast(weeks.weeks as bigint) as weeks,
    cast(coalesce(joined.channels_present, '') as varchar) as channels_present,
    cast(
        case when starts_with(weeks.layer, 'P-') then 'EUR' else 'aEUR' end as varchar
    ) as monetary_unit,
    cast(
        case
            when starts_with(weeks.layer, 'P-') then 'GROUND-TRUTH'
            else 'REAL-ANON'
        end as varchar
    ) as source_tag
from weeks
left join joined
    on weeks.layer = joined.layer
