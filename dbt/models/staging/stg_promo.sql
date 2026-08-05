-- stg_promo: grain week x layer. Layer P's promo signal comes from the outcome
-- CSV's `promo_flag` column; Layer R's from a separate promo calendar CSV
-- (SPEC-03 section 2 split). No `distinct`, `group by`, or `row_number()`.
select
    week_start,
    layer,
    cast(promo_flag as integer) as promo_flag
from {{ ref('raw_outcome_p') }}

union all

select
    week_start,
    layer,
    cast(promo_flag as integer) as promo_flag
from {{ ref('raw_promo_r') }}
