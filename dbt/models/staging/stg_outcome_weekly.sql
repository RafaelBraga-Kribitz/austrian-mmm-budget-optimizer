-- stg_outcome_weekly: grain week x layer. `promo_flag` is deliberately not
-- projected here -- it is stg_promo's grain (SPEC-03 section 2). No `distinct`,
-- `group by`, or `row_number()`: a duplicate grain key must reach the `unique`
-- test intact so it can fail.
select
    week_start,
    layer,
    cast(revenue_eur as double) as revenue,
    orders
from {{ ref('raw_outcome_p') }}

union all

select
    week_start,
    layer,
    cast(revenue_aeur as double) as revenue,
    orders
from {{ ref('raw_outcome_r') }}
