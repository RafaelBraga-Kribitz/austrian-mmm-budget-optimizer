-- raw_media_p: typed passthrough of the three committed Layer P media_weekly.csv
-- files, plus a `layer` literal. No renames, no dedup, no filtering -- BP-D-03's
-- unit-neutral renames belong in staging (plan 03-03), not here. `spend_eur` arrives
-- as an integer in the CSV and is left uncast; the cast to DOUBLE belongs in staging
-- where the BP-D-03 rename happens.
--
-- Every read_csv_auto path is built from the `data_synthetic_path` var (T-201) -- no
-- literal `data/synthetic` prefix is hard-coded anywhere in this file. This is the
-- single parameterization plans 03-03 (poisoned fixture), 03-06 (Layer R fixture) and
-- Phase 6 (agency intake tests) all depend on.
{% set scenario_layers = [
    ("s_a", "P-SA"),
    ("s_b", "P-SB"),
    ("s_c", "P-SC"),
] %}

{% for scenario_dir, layer in scenario_layers %}
select
    week_start,
    channel,
    spend_eur,
    impressions,
    platform_conversions,
    platform_revenue_eur,
    '{{ layer }}' as layer
from read_csv_auto('{{ var("data_synthetic_path") }}/{{ scenario_dir }}/media_weekly.csv')
{% if not loop.last %}
union all
{% endif %}
{% endfor %}
