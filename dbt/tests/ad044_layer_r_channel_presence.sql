-- ad044_layer_r_channel_presence: SPEC-03 section 4 AD-044, shipped in its dormant
-- form (D-20, T-203 AC-1, BP-D-05). A singular test wrapped in a jinja conditional
-- on `var('intake_manifest_present')` (default false, dbt_project.yml). The false
-- branch -- the only branch that renders in Phase 3 -- is a zero-row select, so the
-- test compiles, appears in `dbt build` output, and passes inert.
--
-- Design point 1: why this test is gated on `intake_manifest_present` and NOT on
-- `layer_r_present`. BP-D-05 names both the `layer_r_present` var and an
-- `intake_channels.csv` seed for AD-044, and Phase 6 owns that seed. If this test
-- were gated on `layer_r_present` alone, plan 03-06's own D-20 fixture run -- which
-- sets `layer_r_present: true` to actually exercise the Layer R data path -- would
-- also render this test's true branch, which `ref()`s a seed
-- (`dbt/seeds/intake_channels.csv`) that does not exist yet, and the run would fail
-- at PARSE TIME for a reason unrelated to what this test is testing. A second,
-- independent var lets the Layer R *data path* be exercised now (plan 03-06's
-- fixture build) while the *manifest comparison* stays dormant until Phase 6's seed
-- lands. Phase 6 flips both vars together. This does not weaken AD-044: the test is
-- absent from the M4 gate today either way, and G-DATA-W
-- (docs/EXECUTION_BLUEPRINT/10_VALIDATION_GATES.md section 4) already marks AD-044
-- "active from M4", not Phase 3.
--
-- Design point 2: the true branch below is WRITTEN but has NEVER EXECUTED in this
-- phase -- plan 03-06's D-20 fixture run exercises the Layer R data path
-- (raw/staging/marts) but never sets `intake_manifest_present: true`, since doing
-- so would require the Phase-6-owned seed this plan deliberately does not create.
-- Unlike the Layer R data path (proven green end-to-end against a fixture this
-- plan), this comparison logic is unproven text. Phase 6 must treat its first run
-- as new code needing its own verification, not as something this plan already
-- validated.
--
-- Parse-time gate proof (recorded in the plan SUMMARY): dbt-core's default
-- behavior for a `ref()` naming a node that does not exist is a WARNING plus
-- silent exclusion of the depending node from the DAG -- `dbt build` itself still
-- exits 0. Setting `intake_manifest_present: true` with no `intake_channels` seed
-- present and no `--warn-error` flag therefore does NOT fail `dbt build`; it is
-- only with `--warn-error` (a standard dbt CLI flag, not a project setting, not
-- touched here) that the same missing-node condition becomes a hard Compilation
-- Error naming `intake_channels` and a non-zero exit. This is the proof Phase 6
-- must reproduce (or a stronger `flags: warn_error: true` project default must
-- exist) before trusting a red AD-044 run to actually be red.
--
-- Because this test reads a jinja-conditional relation rather than a `ref()` dbt can
-- always infer at parse time, the hint below schedules it after `dim_layer`
-- materializes in both branches.
-- depends_on: {{ ref('dim_layer') }}
{% if var('intake_manifest_present') %}
-- True branch (Phase 6 activates): symmetric difference between the comma-split
-- `channels_present` list on dim_layer's Layer R row and the intake-channel seed --
-- a full outer join on channel name, keeping only the non-matching side. Zero rows
-- returned means the two sources agree exactly; any row names a channel present on
-- exactly one side.
with listed as (
    select unnest(string_split(channels_present, ',')) as channel
    from {{ ref('dim_layer') }}
    where layer = 'R' and channels_present <> ''
),

manifest as (
    select channel
    from {{ ref('intake_channels') }}
)

select
    coalesce(listed.channel, manifest.channel) as channel,
    case
        when manifest.channel is null then 'listed_not_in_manifest'
        else 'manifest_not_listed'
    end as direction
from listed
full outer join manifest
    on listed.channel = manifest.channel
where listed.channel is null or manifest.channel is null
{% else %}
-- False branch (the committed Phase 3 default): zero rows, unconditionally. Same
-- two-column shape as the true branch so a reader sees at a glance what the true
-- branch's output would mean.
select
    cast(null as varchar) as channel,
    cast(null as varchar) as direction
where false
{% endif %}
