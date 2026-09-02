-- raw_media_r: Layer R media, jinja-guarded on `layer_r_present` (BP-D-05, ratified
-- ADR-000 D-2). The true branch reads data_real_anon_path/media_weekly.csv per
-- SPEC-02's anonymized-output shape (spend_aeur, clicks, impressions,
-- platform_conversions, platform_conv_value). The false branch (the committed
-- default) is a zero-row select with the identical column list and explicit casts,
-- so a downstream union never changes type whether the flag is on or off.
{% if var('layer_r_present') %}
select
    week_start,
    channel,
    spend_aeur,
    clicks,
    impressions,
    platform_conversions,
    platform_conv_value,
    'R' as layer
from read_csv_auto('{{ var("data_real_anon_path") }}/media_weekly.csv')
{% else %}
select
    cast(null as date) as week_start,
    cast(null as varchar) as channel,
    cast(null as double) as spend_aeur,
    cast(null as bigint) as clicks,
    cast(null as bigint) as impressions,
    cast(null as bigint) as platform_conversions,
    cast(null as double) as platform_conv_value,
    cast(null as varchar) as layer
where false
{% endif %}
