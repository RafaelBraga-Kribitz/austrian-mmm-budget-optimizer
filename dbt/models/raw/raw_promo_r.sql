-- raw_promo_r: Layer R promo calendar, jinja-guarded on `layer_r_present`. True
-- branch reads data_real_anon_path/promo_calendar.csv (week_start, promo_flag).
-- False branch is a zero-row select with the identical column list, so a downstream
-- union never changes type whether the flag is on or off.
{% if var('layer_r_present') %}
select
    week_start,
    promo_flag,
    'R' as layer
from read_csv_auto('{{ var("data_real_anon_path") }}/promo_calendar.csv')
{% else %}
select
    cast(null as date) as week_start,
    cast(null as bigint) as promo_flag,
    cast(null as varchar) as layer
where false
{% endif %}
