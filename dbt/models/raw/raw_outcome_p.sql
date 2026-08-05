-- raw_outcome_p: typed passthrough of the three committed Layer P outcome_weekly.csv
-- files, plus a `layer` literal. Same loop shape and same no-renames/no-dedup/
-- no-filtering discipline as raw_media_p.sql.
{% set scenario_layers = [
    ("s_a", "P-SA"),
    ("s_b", "P-SB"),
    ("s_c", "P-SC"),
] %}

{% for scenario_dir, layer in scenario_layers %}
select
    week_start,
    revenue_eur,
    orders,
    promo_flag,
    '{{ layer }}' as layer
from read_csv_auto('{{ var("data_synthetic_path") }}/{{ scenario_dir }}/outcome_weekly.csv')
{% if not loop.last %}
union all
{% endif %}
{% endfor %}
