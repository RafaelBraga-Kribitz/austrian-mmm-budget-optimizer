-- raw_outcome_r: Layer R outcome, jinja-guarded on `layer_r_present`. True branch
-- reads data_real_anon_path/outcome_weekly.csv (week_start, revenue_aeur, orders).
-- False branch is a zero-row select with the identical column list, so a downstream
-- union never changes type whether the flag is on or off.
{% if var('layer_r_present') %}
select
    week_start,
    revenue_aeur,
    orders,
    'R' as layer
from read_csv_auto('{{ var("data_real_anon_path") }}/outcome_weekly.csv')
{% else %}
select
    cast(null as date) as week_start,
    cast(null as double) as revenue_aeur,
    cast(null as bigint) as orders,
    cast(null as varchar) as layer
where false
{% endif %}
