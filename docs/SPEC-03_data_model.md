# SPEC-03 — Data Model (DuckDB + dbt) (AMBO)

Between `data/synthetic|real_anon/` and modeling. Requirement IDs: `AD-xxx`.
Deliberately the smallest warehouse of the three portfolio projects — weekly grain,
two layers, one modeling matrix each.

---

## 1. Stack

- AD-001: DuckDB file `data/warehouse/ambo.duckdb` (gitignored); dbt + `dbt-duckdb`,
  project at `dbt/`. Layers: `raw` (external views over the committed CSVs) →
  `staging` (views) → `marts` (tables). Units in suffixes: `_eur` (Layer P),
  `_aeur` (Layer R) — the suffix difference is intentional and enforced (a dbt test
  fails if a mart mixes `_eur` and `_aeur` columns).
- AD-002: Universal keys: `week_start` (DATE, ISO Monday) + `layer`
  ('P-SA'|'P-SB'|'P-SC'|'R') + `channel` where applicable.

## 2. Staging

| Model | Grain | Logic |
|-------|-------|-------|
| `stg_media_weekly` | week × layer × channel | union of the three scenario CSVs + real_anon CSV, `layer` column added; dedup forbidden (inputs are canonical — duplicate keys FAIL, never silently resolved) |
| `stg_outcome_weekly` | week × layer | same pattern |
| `stg_promo` | week × layer | Layer P: from outcome CSV `promo_flag`; Layer R: from `promo_calendar.csv` |
| `stg_calendar_weekly` | week | ISO week attrs, `advent_flag`, `schulbeginn_flag`, `jan_dip_flag`, `spring_flag`, `summer_lull_flag` — SAME window definitions as SPEC-01 §2.1 (one seed CSV `dbt/seeds/season_windows.csv` drives BOTH the simulator and this model, so definitions cannot drift) |

- AD-020: `season_windows.csv` is the single source of Austrian-calendar window
  definitions; the simulator reads it too (exception to the no-shared-code rule
  AGENTS W-2: shared CONFIG is allowed, shared TRANSFORM code is not — stated here
  explicitly).

## 3. Marts

| Model | Grain | Columns |
|-------|-------|---------|
| `fct_mmm_input` | week × layer | `week_start, layer, revenue (eur or aeur per layer), orders, promo_flag`, calendar flags, plus one spend column per channel (`spend_search_brand`, … pivoted; NULL→0 for absent channels; channel presence per layer recorded in `dim_layer`) |
| `dim_layer` | layer | `layer, weeks, channels_present (list), monetary_unit ('EUR'\|'aEUR'), source_tag ('GROUND-TRUTH'\|'REAL-ANON')` |
| `fct_platform_reported` | week × layer × channel | platform conversions/value where present (Layer P §SIM-060 + Layer R exports) — feeds SPEC-06 §5 |

- AD-030: `fct_mmm_input` is THE model input contract. `ambo/model/` reads only this
  mart (via `ambo/common/db.py`), never CSVs.

## 4. dbt tests

- AD-040: unique+not_null on all grain keys; gapless week spine per layer.
- AD-041: Ranges: spend ≥ 0; revenue > 0; promo_flag ∈ (0,1).
- AD-042: Reconciliation: Layer P-SA total revenue in `fct_mmm_input` equals the
  simulator CSV sum within 1e-6 (aggregation integrity).
- AD-043: Unit-suffix segregation test (AD-001).
- AD-044: Layer R channel presence matches `INTAKE_MANIFEST.yaml` (parsed by a
  singular test).

## 5. Exports for BI (`make export` → `exports/`; Power BI reads only these)

| File | Content |
|------|---------|
| `exports/mmm_input_weekly.csv` | `fct_mmm_input` all layers |
| `exports/contributions_weekly.csv` | posterior-mean decomposition per week × channel × layer (SPEC-04 output) |
| `exports/roas_summary.csv` | ROAS mean + HDI per channel × layer + truth where layer P (SPEC-05 output) |
| `exports/response_curves.csv` | spend grid × channel × layer: contribution mean + HDI (+ truth for P) |
| `exports/allocation_scenarios.csv` | optimizer outputs (SPEC-06) |
| `exports/attribution_gap.csv` | platform vs MMM ROAS per channel × layer (SPEC-06) |

- AD-050: Export schemas contract-tested on fixtures (same pattern as sibling repos).
