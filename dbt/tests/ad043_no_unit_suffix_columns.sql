-- ad043_no_unit_suffix_columns: strict AD-043 enforcement (D-16). This is a
-- singular test -- dbt's contract is zero rows returned = pass, any row returned =
-- fail -- so any `_eur`/`_aeur`-suffixed column surviving on a stg_/fct_/dim_
-- model fails `dbt build`. This is the ONE authored home for the AD-043 rule;
-- plan 03-05 extends this same file with mart hints, it is never restated
-- elsewhere.
--
-- The raw layer is deliberately excluded by the stg_/fct_/dim_ prefix filter: raw
-- views are typed passthroughs of the producing-side CSV columns and legitimately
-- carry `spend_eur`/`platform_revenue_eur` (see dbt/models/raw/*.sql) -- AD-043
-- governs staging and mart *output*, not the raw layer, and the prefix filter is
-- the mechanism that scopes it there.
--
-- This reading is stricter than SPEC-03 AD-001's literal wording ("a dbt test
-- fails if a mart mixes `_eur` and `_aeur` columns"): the weaker "mixes both
-- suffixes" form would pass a mart that forgot the rename entirely and shipped
-- only one suffix -- exactly the failure worth catching (D-16; also recorded in
-- docs/BUILD_LOG.md's departures entry from plan 03-01).
--
-- Because this test reads `information_schema` rather than `ref()`-ing a model,
-- dbt cannot infer its dependencies from the query text -- the hints below
-- schedule it after the four staging models are materialized.
-- depends_on: {{ ref('stg_media_weekly') }}
-- depends_on: {{ ref('stg_outcome_weekly') }}
-- depends_on: {{ ref('stg_promo') }}
-- depends_on: {{ ref('stg_calendar_weekly') }}

select table_name, column_name
from information_schema.columns
where table_schema = '{{ target.schema }}'
  and (
    starts_with(table_name, 'stg_')
    or starts_with(table_name, 'fct_')
    or starts_with(table_name, 'dim_')
  )
  and (
    ends_with(column_name, '_eur')
    or ends_with(column_name, '_aeur')
  )
