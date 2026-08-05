# Phase 3: Warehouse - Research

**Researched:** 2026-08-05
**Domain:** dbt + DuckDB warehouse layer; contract enforcement; grain/uniqueness testing; CI/Makefile path portability
**Confidence:** HIGH (dbt/dbt-duckdb mechanics were empirically verified against the exact locally-installed toolchain — dbt-core 1.12.0, dbt-duckdb 1.10.1 — not just read from docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Export commit policy**
- D-01: `exports/mmm_input_weekly.csv` is **committed**, per SPEC-08 §2 and EB-081 post-W5. WBS T-205 AC-3 is corrected, not followed.
- D-02: Drift is caught by a **CI job 3 diff-check on the D-20 pattern**: regenerate (`make transform && make export`), then `git diff --exit-code exports/`.
- D-03: The export registry is **grow-as-you-go** — one entry now (`mmm_input_weekly.csv`); structured so later phases extend a dict rather than copy-paste a new script.
- D-04: Float output is **explicit fixed precision — 6 decimals**, pinned in the registry, matching the simulator's own `%.6f` format.
- D-05: The a€-in-committed-exports interaction is **recorded, not acted on here** — a header comment in `scripts/export_marts.py` and a `docs/RISK_REGISTER.md` entry, revisited before the M4 `layer_r_present` flip.

**Contract-freeze enforcement**
- D-06: Mart contracts enforced by **dbt model contracts** (`config(contract={enforced: true})` with full `columns:`/`data_type:`). Research must confirm dbt-duckdb's constraint-enforcement level before committing; fall back to pytest-against-the-built-mart if unsupported.
- D-07: **All three marts** get enforced contracts — `fct_mmm_input`, `dim_layer`, `fct_platform_reported`.
- D-08: **The dbt schema yml is the single normative home** for mart column contracts; `db.py` derives its expected column set from the yml (or a generated constant) rather than restating it; `MODULE_CONTRACTS.md` cites the yml by path.
- D-09: The AD-030 mart-only rule becomes a **fifth standing guard test**: `src/ambo/model/` and `src/ambo/decide/` may not read CSV/parquet or open duckdb outside `src/ambo/common/db.py`; `src/ambo/report/` may read `exports/` only.
- D-10: `db.py` **collects all postcondition violations and raises once** with the full list (assertion, layer, offending weeks/columns).

**Test rigor beyond the WBS minimum**
- D-11: **A real negative dbt test proves duplicate grain keys FAIL** — a pytest points dbt at a poisoned fixture directory (duplicate week × layer × channel row) and asserts `dbt build` exits non-zero on the `unique` test. Requires source paths parameterized by a dbt var in T-201.
- D-12: **AD-042 reconciliation covers all three Layer P layers** (P-SA, P-SB, P-SC), not P-SA alone. Tightens, not widens — no ADR needed.
- D-13: **`dim_layer.channels_present` derives from source-row presence** — a channel is present if it has rows in staging for that layer. Model code iterates `channels_present`, never the seven `spend_*` columns directly.
- D-14: **`channels_present` gets a both-directions singular test**: listed channels have ≥1 source row, and every `spend_<channel>` column *not* listed is 0.0 on every row.
- D-15: **The gapless week spine comes from the seed** (`stg_calendar_weekly`), not SQL date arithmetic — anti-join each layer's weeks against the seed between that layer's min/max `week_start`. Deliberate departure from Guide §8.3's `generate_series` instruction; note in PR.
- D-16: **AD-043 is implemented strictly**: neither `_eur` nor `_aeur` may appear in **any** staging or mart output column. Stricter than SPEC-03 AD-001's literal "mixes" wording; note in PR.

**Budget and sequencing**
- D-17: Phase 3 is named at **1 d of M2's 2 d**; Phase 4 takes the other 1 d. Record the split in `docs/BUILD_LOG.md`.
- D-18: **Tests ship in the plan that creates what they verify.** Source paths parameterized in T-201.
- D-19: **Named shed order** for the 1 d → 2 d zone (flag each shed in `docs/BUILD_LOG.md` before doing it):
  1. the poisoned-fixture harness (D-11) — highest scaffold cost;
  2. the secondary mart contracts on `dim_layer`/`fct_platform_reported` (D-07);
  3. AD-042's S-B/S-C extension (D-12).
  **Never shed:** the `fct_mmm_input` enforced contract (D-06), the mart-only guard test (D-09), `channels_present` and its derivation (D-13).

**Layer R staging branch**
- D-20: **The `layer_r_present` branch ships written and fixture-exercised** — jinja-guarded union per BP-D-05, exercised with a minimal fake `data/real_anon/`-shaped fixture under `tests/fixtures/` and one dbt invocation with `layer_r_present: true`. Fixture is synthetic and obviously fake.

**Makefile and CI**
- D-21: **The D-17 `make transform` conditional is removed.** `make transform` becomes `uv run dbt build --project-dir dbt --profiles-dir dbt`, full stop.
- D-22: **CI job 3 gains a `windows-latest` matrix leg**, same choco-install-make step as job 2. Job name stays `dbt`.
- D-23: **Warehouse path: keep Guide §8.1's relative form, pin the invocation, assert the result.** `profiles.yml` keeps a relative path; the Makefile always passes `--project-dir dbt --profiles-dir dbt`; a test asserts the built file sits at exactly `settings.paths.warehouse`. **Research must verify dbt-duckdb's actual path-resolution base — Guide §8.1's "resolves relative to profile dir" claim is unconfirmed.** — **See Pitfall 1 below: this research empirically disproves that claim for this exact invocation pattern.**

**`fct_platform_reported`**
- D-24: **Build the full Layer P surface now and pre-declare the Layer R extension** — `platform_conversions`, `platform_conv_value`, `impressions` frozen now; Layer R's `clicks` pre-declared as a planned M4 amendment in the contract text and the intake ADR.

### Claude's Discretion
- Internal structure of the export registry dict (D-03) and the exact float-format directive (D-04), as long as output is byte-stable at 6 decimals.
- The concrete form of the poisoned-fixture harness (D-11) — how source paths are parameterized, where the tmp warehouse lives, how the non-zero exit is asserted.
- Wording of the `RISK_REGISTER.md` entry and the `export_marts.py` header comment (D-05).
- Exact column set/shape of the fake Layer R fixture (D-20), beyond the SPEC-02 §5.2 taxonomy and BP-D-03 column names.
- Whether the `channels_present` both-directions check (D-14) is one singular test or two, and its failure-message format.
- How `db.py` derives its column set from the dbt yml (D-08) — direct yml parse, a generated constant, or a dbt artifact read.

### Deferred Ideas (OUT OF SCOPE)
- Revisit D-26's leak-scan scope for committed `exports/*.csv` — **Phase 6**, before the `layer_r_present` flip.
- `dbt docs generate` lineage graph as a portfolio artifact — **Phase 9**.
- `clicks` joins `fct_platform_reported` — **Phase 6**, D-24's pre-declared extension.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-q1-truth-recovery (contributing) | The model must recover known truth; Phase 3 is a contributing precondition — the mart must carry revenue/spend that reconciles exactly to the simulator's disclosed truth. | AD-042 reconciliation mechanics (singular test, `ABS(diff) <= 1e-6`, not float `=`) in Pitfall/Code Examples sections; exact S-A/S-B/S-C revenue sums verified below give the planner concrete acceptance-criterion numbers. |
| REQ-grain-and-windows (contributing — weekly spine) | ISO weeks (Mon–Sun) everywhere; gapless spine per layer. | D-15's seed-anti-join mechanism detailed with exact SQL pattern; `dbt/seeds/season_windows.csv` confirmed as 2019–2027 (471 rows incl. header), covering all three scenarios' windows with margin. |
| REQ-dl1-reproducible-pipeline (contributing — `make transform` opens the DL-1 probe) | A fresh clone must reproduce Layer P artifacts without private inputs; `make transform` is the first stage of that probe. | Makefile/CI mechanics section: exact `make transform` recipe, the empirically-verified path-resolution fix, Windows/Linux portability notes, CI job 3 matrix change. |
</phase_requirements>

## Summary

This phase turns nine already-committed synthetic CSVs (Phase 2 output) into one dbt-built,
contract-enforced DuckDB mart (`fct_mmm_input`) that Phase 4's model code reads exclusively. The
toolchain (dbt-core 1.12.0, dbt-duckdb 1.10.1, duckdb 1.5.5 Python driver) is **already installed**
in this repo's `.venv` from Phase 1's `uv sync` — no new packages, no legitimacy audit needed. No
`dbt_project.yml`, `profiles.yml`, or dbt models exist yet; Phase 3 builds the dbt project from
scratch.

Three findings materially change how the plan should be written versus what CONTEXT.md's open
research questions assumed:

1. **Guide §8.1's path-resolution claim is empirically wrong for this invocation pattern.**
   Live-tested against the exact locally-installed dbt-core 1.12.0 / dbt-duckdb 1.10.1: a relative
   `path:` in `profiles.yml` resolves against the **current working directory at invocation time**,
   not against `profiles.yml`'s own directory, when `--project-dir` and `--profiles-dir` are both
   passed explicitly (the pattern D-21/D-23 mandate). Since `make transform` always runs with CWD =
   repo root, the correct `profiles.yml` `path:` is `data/warehouse/ambo.duckdb` (no `../`) — the
   Guide's `../data/warehouse/ambo.duckdb` form would resolve **one directory above the repository
   root** and fail or write outside the tree entirely. This is the single most load-bearing
   correction in this document (see Pitfall 1).

2. **dbt model contracts (`contract: {enforced: true}` + `columns:`/`data_type:`) are supported by
   dbt-duckdb for table-materialized models** — confirmed by the adapter's own documentation
   (constraint/contract translation to DuckDB DDL) and consistent with dbt-core's adapter-agnostic
   contract-checking mechanism (a typed `CREATE TABLE (...) AS SELECT` that fails at the database
   level on a mismatch). However, **DuckDB does not appear in dbt's official per-platform
   `constraints:` support table** (the `primary_key`/`unique`/`check` block inside a contract). The
   safe, well-supported subset is the **columns + data_type contract only** — D-06/D-07 should be
   satisfied with that subset, and grain uniqueness (AD-040, D-11) should be enforced through
   ordinary dbt generic tests, which are guaranteed to work on any adapter because they run as SQL
   queries, not adapter-specific DDL constraints.

3. **Multi-column grain uniqueness needs no new dbt package.** dbt's native `unique` generic test
   accepts a `column_name` that is an arbitrary SQL expression (an officially documented FAQ
   pattern), e.g. `column_name: "(week_start || '-' || layer || '-' || channel)"`. This avoids
   adding `dbt_utils` as a new dependency (which EB-030 would otherwise treat as an ADR event) and
   is exactly what D-11's poisoned-fixture negative test needs to prove fails.

**Primary recommendation:** Build the dbt project exactly per D-01…D-24, using the columns-only
contract form for D-06/D-07, expression-based native `unique` tests for AD-040/D-11, a
singular-test pattern with `ABS(a - b) <= 1e-6` for AD-042/D-12, and `path: data/warehouse/ambo.duckdb`
(not `../data/warehouse/ambo.duckdb`) in `profiles.yml` given the confirmed CWD-relative resolution.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Raw ingestion (CSV → typed view) | Database / Storage (dbt `raw` layer, DuckDB external views) | — | `read_csv_auto` external views are the only I/O boundary; no Python touches the CSVs after this phase |
| Unit harmonization / renames (BP-D-03) | Database / Storage (dbt `staging` layer) | — | SQL-only transform, no business logic; keeps `_eur`/`_aeur` segregation testable in one place (AD-043) |
| Grain enforcement, contract freeze, reconciliation | Database / Storage (dbt `marts` layer + dbt tests) | — | AD-040…044 are dbt-test-native; a Python-side re-check would be a second, driftable home |
| Read-only data access for model/decide/report | API / Backend equivalent (`ambo/common/db.py`) | — | AD-030's single doorway; the only place `duckdb.connect()` may appear outside dbt itself |
| Contract violation reporting | API / Backend (`db.py` postcondition checks) | — | Collect-all-raise-once (D-10) is application logic, not a database concern |
| Export/BI feed generation | API / Backend (`scripts/export_marts.py`) | Database / Storage (reads only from marts via `db.py`/direct duckdb read) | Export scripts are Python orchestration over the frozen mart contract, never a second SQL layer |
| Architectural boundary enforcement (mart-only rule) | API / Backend (pytest guard test, D-09) | — | AST/grep-based guard tests are how this project machine-enforces every other boundary (Phase 1 precedent) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dbt-core` | 1.12.0 (already resolved by `uv.lock` from the `>=1.8,<2` pin) [VERIFIED: local `uv run dbt --version`] | SQL transformation orchestration, testing, contracts | Pinned in `pyproject.toml` since Phase 1 (SPEC-08 §3); already installed |
| `dbt-duckdb` | 1.10.1 (resolved by the `>=1.8,<2` pin) [VERIFIED: local `uv run dbt --version`] | dbt adapter targeting an embedded DuckDB file | Pinned since Phase 1; the only adapter this project uses (AD-001) |
| `duckdb` (Python driver) | 1.5.5 [VERIFIED: local `uv run python -c "import duckdb; print(duckdb.__version__)"`] | `ambo/common/db.py`'s read-only connection to the built warehouse | Already a pinned runtime dependency (`duckdb>=1.0`); no new package |

No new Python or dbt packages are required for this phase. `dbt-core`/`dbt-duckdb`/`duckdb` were
already vetted and installed in Phase 1 (`01-02-PLAN.md`'s legitimacy checkpoint). **The Package
Legitimacy Audit section below is a formality confirming no new install, not a fresh vetting.**

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dbt's native generic tests (`unique`, `not_null`, `accepted_values`) | bundled with dbt-core | AD-040 grain uniqueness, AD-041 ranges | Always — no package install; use expression `column_name` for composite-key uniqueness (see Code Examples) |
| dbt singular tests (`tests/*.sql` or `dbt/tests/*.sql`) | bundled with dbt-core | AD-042 reconciliation, D-14 `channels_present` both-directions check | Whenever the assertion needs custom SQL beyond a generic test's parameters |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dbt-native `unique` test with a concatenated expression column | `dbt_utils.unique_combination_of_columns` | Requires adding the `dbt_utils` dbt package (a `dbt/packages.yml` + `dbt deps` step) — a new dependency surface EB-030 would treat as an ADR event for zero functional gain, since the native form is officially documented and equally reliable |
| dbt model contract's `columns:`/`data_type:` only | Also declaring the contract's inline `constraints:` block (`primary_key`, `unique`) | DuckDB is not listed in dbt's official per-platform constraint-support table; the columns-only form is unambiguously supported and sufficient once paired with generic/singular tests for grain and value rules |
| dbt enforced contracts (D-06's chosen path) | pytest-against-the-built-mart (settings.yaml-derived column set) | This was CONTEXT.md's named fallback if dbt-duckdb couldn't enforce contracts. Research confirms it CAN (columns-only form), so the fallback is not needed — but see Pitfall 2 for the narrow limitation that motivated naming it |

**Installation:** None — `uv sync` (already run in Phase 1) installs everything this phase needs.

**Version verification:** Confirmed live against this repo's `.venv`, not training data:
```
$ uv run dbt --version
Core: installed 1.12.0 (latest)
Plugins: duckdb 1.10.1 (latest)
$ uv run python -c "import duckdb; print(duckdb.__version__)"
1.5.5
```

## Package Legitimacy Audit

**Not applicable — no new packages are installed in this phase.** `dbt-core`, `dbt-duckdb`, and
`duckdb` were pinned in `pyproject.toml` and vetted at Phase 1's dependency-legitimacy checkpoint
(`01-02-PLAN.md`). This phase only writes SQL/YAML inside the already-installed `dbt/` project and
Python inside already-permitted `src/ambo/common/` and `scripts/`. If the plan introduces any dbt
package (e.g., `dbt_utils` — see Alternatives Considered, rejected above), the Package Legitimacy
Gate must be re-run against that package before it lands.

## Architecture Patterns

### System Architecture Diagram

```
data/synthetic/{s_a,s_b,s_c}/{media_weekly,outcome_weekly}.csv   (Phase 2, committed, immutable)
data/real_anon/*.csv  (fixture only in this phase — real content arrives Phase 6, jinja-guarded)
                │
                ▼
   ┌─────────────────────────── dbt "raw" layer ───────────────────────────┐
   │ read_csv_auto external views, one per scenario file + real_anon       │
   │ (behind {% if var('layer_r_present') %}), literal `layer` column      │
   └─────────────────────────────────┬───────────────────────────────────┘
                                      ▼
   ┌────────────────────────── dbt "staging" layer ────────────────────────┐
   │ stg_media_weekly   — union of raw views, BP-D-03 renames, no _eur/    │
   │                       _aeur leakage, duplicate keys FAIL (AD-040 half)│
   │ stg_outcome_weekly — same pattern, revenue/orders/promo_flag          │
   │ stg_promo          — Layer P from outcome.promo_flag; Layer R stub    │
   │ stg_calendar_weekly— season_windows.csv seed, read only, never        │
   │                       recomputed (AD-020, D-15)                       │
   └─────────────────────────────────┬───────────────────────────────────┘
                                      ▼
   ┌─────────────────────────── dbt "marts" layer ─────────────────────────┐
   │ fct_mmm_input (week × layer)         ── enforced contract (D-06/07)   │
   │   revenue, orders, promo_flag, 5 calendar flags, spend_<channel>×7    │
   │ dim_layer (layer)                    ── enforced contract            │
   │   channels_present (D-13), monetary_unit, source_tag, weeks          │
   │ fct_platform_reported (week × layer × channel) ── enforced contract  │
   │   platform_conversions, platform_conv_value, impressions             │
   │ dbt tests: AD-040 (gapless spine + unique grain), AD-041 (ranges),    │
   │            AD-042 (±1e-6 reconciliation ×3 layers), AD-043 (strict    │
   │            unit-suffix), AD-044 (dormant, gated on layer_r_present)   │
   └─────────────────────────────────┬───────────────────────────────────┘
                                      ▼
              ┌─────────────────────────────────────────┐
              │ src/ambo/common/db.py (AD-030 doorway)   │
              │  connect(read_only=True)                 │
              │  read_mmm_input(layer) -> DataFrame       │  ◄── the ONLY route
              │  read_platform_reported(layer)            │      model/decide/report
              │  read_dim_layer()                         │      code may take (D-09
              │  postcondition checks, collect-all-raise  │      guard test enforces)
              │  -once (D-10)                              │
              └───────────────┬───────────────────────────┘
                               ▼
              ┌─────────────────────────────────────────┐
              │ scripts/export_marts.py (make export)     │
              │  registry dict (D-03), 6-decimal fixed    │
              │  float format (D-04)                      │
              │  → exports/mmm_input_weekly.csv (COMMITTED│
              │     per D-01; contract-tested per AD-050)  │
              └─────────────────────────────────────────┘
                               ▲
              CI job 3 (`dbt` job): make transform, then a
              D-02 diff-check on `make export` output against
              the committed exports/ CSV — drift fails the build
```

### Recommended Project Structure
```
dbt/
├── dbt_project.yml          # profile: ambo; model-paths: ["models"]; vars block
├── profiles.yml             # committed; target dev; path: data/warehouse/ambo.duckdb (NOT ../..., see Pitfall 1)
├── packages.yml             # ABSENT — no dbt package needed (see Alternatives Considered)
├── seeds/
│   └── season_windows.csv   # already committed (Phase 1)
├── models/
│   ├── raw/
│   │   ├── _raw__sources.yml        # or read_csv_auto directly in each raw_*.sql model
│   │   ├── raw_media_p_sa.sql       # + p_sb, p_sc, and layer_r_present-guarded raw_media_r.sql
│   │   └── raw_outcome_p_sa.sql     # + p_sb, p_sc, raw_outcome_r.sql (guarded)
│   ├── staging/
│   │   ├── stg_media_weekly.sql
│   │   ├── stg_outcome_weekly.sql
│   │   ├── stg_promo.sql
│   │   ├── stg_calendar_weekly.sql
│   │   └── _staging__schema.yml     # AD-043 tests, staging-level not_null/unique
│   ├── marts/
│   │   ├── fct_mmm_input.sql
│   │   ├── dim_layer.sql
│   │   ├── fct_platform_reported.sql
│   │   └── _marts__schema.yml       # contract columns/data_type, AD-040..044 tests
│   └── tests/                       # dbt singular tests (AD-042 reconciliation, channels_present)
│       ├── ad042_revenue_reconciliation.sql
│       └── channels_present_both_directions.sql
tests/
├── fixtures/
│   └── warehouse_poisoned/          # D-11: duplicate-grain fixture CSVs (source-path-var-pointed)
│   └── real_anon_fake/              # D-20: fake Layer R shape fixture
└── unit/
    ├── test_db.py                  # T-204: round-trip + contract-violation fixtures
    ├── test_export_marts.py        # T-205: schema contract test on fixtures
    ├── test_mart_only_access.py    # D-09: 5th architectural guard
    └── test_warehouse_build.py     # D-11/D-20/D-23: dbt-invoking tests (subprocess)
src/ambo/common/
└── db.py                            # T-204
scripts/
└── export_marts.py                  # T-205
```

### Pattern 1: Raw layer as `read_csv_auto` external views, source-path parameterized (T-201, D-11, D-18, D-20)

**What:** Each raw model is a `SELECT` over `read_csv_auto('{{ var("data_synthetic_path") }}/s_a/media_weekly.csv')`
with a literal `layer` column, rather than a dbt `source()` pointing at a fixed path. The var
defaults to `data/synthetic` (repo-relative, matching `settings.paths.data_synthetic`) but can be
overridden per-invocation.

**Why this matters:** D-11's poisoned-fixture test, D-20's fake-Layer-R fixture exercise, and
Phase 6's real intake tests all need to point dbt at a *different* directory than the real one,
without touching the model SQL. Parameterizing the path once in T-201 is what makes all three
possible without three separate scaffolds (CONTEXT.md's "three customers" framing).

**Example:**
```sql
-- models/raw/raw_media_p_sa.sql
select
    week_start,
    channel,
    spend_eur,
    impressions,
    platform_conversions,
    platform_revenue_eur,
    'P-SA' as layer
from read_csv_auto('{{ var("data_synthetic_path", "data/synthetic") }}/s_a/media_weekly.csv')
```

```sql
-- models/raw/raw_media_r.sql
{% if var('layer_r_present', false) %}
select
    week_start,
    channel,
    spend_aeur,
    clicks,
    impressions,
    platform_conversions,
    platform_conv_value,
    'R' as layer
from read_csv_auto('{{ var("data_real_anon_path", "data/real_anon") }}/media_weekly.csv')
{% else %}
select
    cast(null as date) as week_start, cast(null as varchar) as channel,
    cast(null as double) as spend_aeur, cast(null as bigint) as clicks,
    cast(null as bigint) as impressions, cast(null as bigint) as platform_conversions,
    cast(null as double) as platform_conv_value, cast(null as varchar) as layer
where false
{% endif %}
```

Invocation for the poisoned-fixture negative test (D-11):
```bash
uv run dbt build --project-dir dbt --profiles-dir dbt \
  --vars '{"data_synthetic_path": "tests/fixtures/warehouse_poisoned"}'
# must exit non-zero on the AD-040 unique test
```

### Pattern 2: Columns-only enforced contract (D-06, D-07, D-08)

**What:** Declare `contract: {enforced: true}` plus a full `columns:` list with `name`+`data_type`
on every mart. Do **not** add an inline `constraints:` list (`primary_key`/`unique`) — that
sub-feature's DuckDB support is not confirmed (see Pitfall 2). Grain uniqueness is a separate,
ordinary dbt test (Pattern 3).

**Example (`models/marts/_marts__schema.yml`):**
```yaml
# Source: dbt Developer Hub, reference/resource-configs/contract (fetched 2026-08-05)
models:
  - name: fct_mmm_input
    config:
      contract: {enforced: true}
      materialized: table
    columns:
      - name: week_start
        data_type: date
        data_tests: [not_null]
      - name: layer
        data_type: varchar
        data_tests: [not_null]
      - name: revenue
        data_type: double
        data_tests: [not_null]
      - name: orders
        data_type: bigint
      - name: promo_flag
        data_type: integer
      - name: advent_flag
        data_type: integer
      - name: jan_dip_flag
        data_type: integer
      - name: spring_flag
        data_type: integer
      - name: schulbeginn_flag
        data_type: integer
      - name: summer_lull_flag
        data_type: integer
      - name: spend_search_brand
        data_type: double
      - name: spend_search_generic
        data_type: double
      - name: spend_meta
        data_type: double
      - name: spend_display_video
        data_type: double
      - name: spend_print_regional
        data_type: double
      - name: spend_radio
        data_type: double
      - name: spend_other
        data_type: double
    data_tests:
      - unique:
          column_name: "(week_start || '|' || layer)"
```
This matches `03_MODULES.md` §8's binding column list for `fct_mmm_input` exactly (`week_start
DATE, layer TEXT, revenue DOUBLE, orders BIGINT, promo_flag INT, 5 calendar flags INT, spend_<channel>
DOUBLE ×7`), so `db.py`'s postcondition check and this yml describe the same contract by
construction — the single-home rule D-08 requires.

If a model's `SELECT` produces a column not in this list, a column with the wrong type, or omits a
declared column, `dbt build` fails at the `CREATE TABLE (...) AS SELECT` step with a DuckDB-level
type/column error — a genuine build-time refusal, not a Python-side check running after the fact.

### Pattern 3: Grain uniqueness via native expression-based `unique` test (AD-040, D-11)

**What:** dbt's bundled `unique` generic test accepts any SQL expression as `column_name` — no
`dbt_utils` package needed.

**Example:**
```yaml
# Source: docs.getdbt.com/faqs/Tests/uniqueness-two-columns (fetched 2026-08-05)
models:
  - name: fct_platform_reported
    data_tests:
      - unique:
          column_name: "(week_start || '|' || layer || '|' || channel)"
      - not_null:
          column_name: week_start
```
Verified locally that this pattern (a concatenation expression as `column_name`) is DuckDB-syntax
compatible (`||` is DuckDB's string-concat operator, same as Postgres). A poisoned fixture with a
duplicate `(week_start, layer, channel)` triple produces a duplicate concatenated string, and the
`unique` test's underlying SQL (`SELECT <expr>, COUNT(*) ... HAVING COUNT(*) > 1`) returns a row —
`dbt build` reports the test as `FAIL` and the process exits non-zero. This is the mechanism D-11's
pytest asserts against, via `subprocess.run([...], check=False)` and checking `returncode != 0`.

### Pattern 4: AD-042 float-tolerance reconciliation as a singular test, not `=`

**What:** A singular test file whose `SELECT` returns rows **on failure** (dbt's singular-test
contract: zero rows = pass, any rows = fail). Never compare floats with `=`.

**Example (`models/tests/ad042_revenue_reconciliation.sql`):**
```sql
-- Source: dbt Developer Hub, "Singular tests" (fetched 2026-08-05); tolerance technique is
-- ABS(diff) <= tolerance, never float equality (SPEC-03 AD-042, D-12's all-three-layers scope).
with mart_totals as (
    select layer, sum(revenue) as mart_revenue
    from {{ ref('fct_mmm_input') }}
    where layer in ('P-SA', 'P-SB', 'P-SC')
    group by layer
),
csv_totals as (
    select 'P-SA' as layer, sum(revenue_eur) as csv_revenue
        from read_csv_auto('{{ var("data_synthetic_path", "data/synthetic") }}/s_a/outcome_weekly.csv')
    union all
    select 'P-SB', sum(revenue_eur)
        from read_csv_auto('{{ var("data_synthetic_path", "data/synthetic") }}/s_b/outcome_weekly.csv')
    union all
    select 'P-SC', sum(revenue_eur)
        from read_csv_auto('{{ var("data_synthetic_path", "data/synthetic") }}/s_c/outcome_weekly.csv')
)
select m.layer, m.mart_revenue, c.csv_revenue, abs(m.mart_revenue - c.csv_revenue) as delta
from mart_totals m
join csv_totals c using (layer)
where abs(m.mart_revenue - c.csv_revenue) > 1e-6
```
Verified reconciliation targets from the actual committed CSVs (see Phase Requirements table and
Common Pitfalls for provenance): P-SA `revenue_eur` sum = **14,893,565.459516**; P-SB =
**9,794,127.034897**; P-SC = **6,992,687.768258**. These are useful as literal expected-value
assertions in `tests/unit/test_warehouse_build.py` (querying the built mart directly), independent
of the dbt singular test.

### Pattern 5: `channels_present` both-directions test (D-13, D-14)

```sql
-- Source: derived from SPEC-03 §3 + CONTEXT.md D-13/D-14 (project-specific, not external docs)
-- Direction 1: every channel listed in channels_present has >=1 source row for that layer.
-- Direction 2: every spend_<channel> column NOT listed is exactly 0.0 on every row.
-- One singular test per direction is the simplest to debug independently (Claude's Discretion:
-- planner may combine into one file with a UNION ALL of both failure sets).
```

### Anti-Patterns to Avoid
- **`SELECT DISTINCT` or `GROUP BY` to "clean up" duplicate grain rows before the mart:** this
  silently deduplicates exactly the failure ROADMAP success criterion 4 requires to surface. The
  staging layer must UNION the raw sources with no dedup logic anywhere in the SQL; only the dbt
  `unique` test may detect and fail on a duplicate — never a query construct that resolves it.
- **`generate_series` for the week spine:** explicitly rejected by D-15; the seed is the single
  source of week definitions (AD-020) and SQL date arithmetic can drift from it.
- **Comparing floats with `=` or `ROUND(...) = ROUND(...)`:** AD-042's ±1e-6 tolerance is a
  `ABS(diff) <= tolerance` predicate, never equality after rounding (rounding can mask a real drift
  smaller than the rounding unit but larger than 1e-6).
- **A model-level `constraints:` block (`primary_key`, `unique`) relying on unconfirmed DuckDB
  constraint-DDL support:** use the columns-only contract plus ordinary generic/singular tests
  instead (Pattern 2/3).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Schema/type enforcement on marts | A custom Python schema-diff script run after `dbt build` | dbt's native `contract: {enforced: true}` + `columns:`/`data_type:` | Refuses to build at the database level; single YAML home; no second code path to keep in sync |
| Composite-key uniqueness | A hand-rolled `GROUP BY ... HAVING COUNT(*) > 1` wired into CI ad hoc | dbt's native `unique` generic test with an expression `column_name` | Already the project's testing idiom (AD-040 etc.); shows up in `dbt build` output with a named, greppable test |
| Multi-source config duplication (channel taxonomy) | Trusting the dbt var and `settings.yaml` never drift | A pytest asserting `channel_taxonomy` var == `Settings.channels` (BP-G-03 precedent, already established for other cross-language duplication in this project) | Two languages must each know the taxonomy; the project's own precedent is "tested, not eliminated" |
| Float precision in the committed export | pandas' default `to_csv` float repr | Explicit `float_format="%.6f"` (D-04) | A pandas minor-version bump can silently rewrite every line of a committed, diff-checked CSV |

**Key insight:** every mechanism in this phase that could be "a written rule reviewers check" is
instead machine-enforced — this is the established pattern from Phase 1 (D-12/D-20/D-23) and
Phase 2, and CONTEXT.md's own decisions (D-02, D-06, D-09, D-14, D-16, D-23) continue it
deliberately. The planner should treat any new rule surfaced during planning the same way.

## Common Pitfalls

### Pitfall 1: Guide §8.1's relative-path claim is wrong for the mandated invocation pattern [VERIFIED: empirical test against installed dbt-core 1.12.0 / dbt-duckdb 1.10.1]

**What goes wrong:** `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` §8.1 states
"`dbt-duckdb` resolves relative to the profile dir," and generic dbt/dbt-duckdb documentation says
the same thing ("resolved relative to your `profiles.yml` file"). **Both are wrong for the exact
invocation this project's D-21/D-23 mandate: `dbt build --project-dir dbt --profiles-dir dbt` run
from the repository root.** A live three-part test against this repo's own installed toolchain
(reproduced below) shows the `path:` value in `profiles.yml` resolves against the **process's
current working directory at invocation**, not against the directory containing `profiles.yml`,
whenever `--project-dir`/`--profiles-dir` are passed explicitly (empirically confirmed identical
for both `dbt debug` and `dbt build`).

**Why it happens:** dbt-duckdb's own path-resolution code resolves the `path:` string via Python's
standard relative-path semantics against `os.getcwd()`, not against the resolved location of
`profiles.yml`. The documentation describing "relative to profiles.yml" appears to describe the
*default* invocation (no `--project-dir`/`--profiles-dir` flags, `profiles.yml` found by dbt's own
search in `~/.dbt/` or cwd) rather than the explicit-flags case this project uses.

**How to avoid:** Set `profiles.yml`'s `path:` to **`data/warehouse/ambo.duckdb`** (no leading
`../`), because `make transform` always invokes `dbt build --project-dir dbt --profiles-dir dbt`
with CWD = repository root (Make does not `cd` into the recipe's directory). This lands the file at
exactly `<repo_root>/data/warehouse/ambo.duckdb`, matching `settings.paths.warehouse`. **This is a
deliberate, evidence-based departure from the Guide** — note it in the PR next to D-15/D-16's
similar departures so a reviewer does not read it as an oversight.

**Warning signs:** `dbt build` failing with `IO Error: Cannot open file "...\data\warehouse\..."`
where the printed path has one extra or one fewer directory level than expected — that error text
directly reveals which base directory dbt actually resolved against, and is the fastest way to
confirm this behavior if a plan chooses to re-verify it at implementation time.

**Reproduction (run to re-verify if the dbt-duckdb version ever changes):**
```bash
# From repo root equivalent, with dbt/profiles.yml containing path: 'data/warehouse/x.duckdb'
uv run dbt build --project-dir dbt --profiles-dir dbt
# Confirms: file lands at <cwd>/data/warehouse/x.duckdb, i.e., cwd-relative, not profiles.yml-relative.
```
The T-201 acceptance criteria already name the correct verification mechanism (D-23: "a test
asserts the built file sits at exactly `settings.paths.warehouse`") — that assertion test is what
will catch a regression here across dbt-duckdb version bumps; it should not be treated as optional.

### Pitfall 2: DuckDB is not on dbt's official constraint-support platform table

**What goes wrong:** A plan that adds a `constraints:` block (`type: primary_key`, `type: unique`)
inside the mart's `contract:` yml, expecting DuckDB to translate it into enforced DDL the same way
Postgres/Snowflake/BigQuery do.

**Why it happens:** dbt-duckdb's own docs mention "translating contract specifications into
enforceable DuckDB constraints" in general terms, which reads as a green light, but dbt's official
cross-platform constraint reference table (`docs.getdbt.com/reference/resource-properties/constraints`)
does not list DuckDB among the platforms with documented constraint-type support — meaning the
specific behavior (which constraint types actually compile to working DDL, and whether a violation
fails the build or is silently accepted) is unverified for this adapter.

**How to avoid:** Use only the `columns:` + `data_type:` form of the contract (Pattern 2) — this
part of contract enforcement is adapter-agnostic in dbt-core (it produces a typed `CREATE TABLE`
statement and lets the database itself reject a type mismatch) and does not depend on the
per-platform `constraints:` translation table at all. Enforce uniqueness and not-null through
ordinary dbt tests (Pattern 3), which are plain SQL queries dbt evaluates and are unaffected by
adapter-specific constraint-DDL support.

**Warning signs:** A `constraints:` block that appears to pass locally but was never actually
exercised with a violating fixture — the same "green on clean inputs proves the test exists, not
that it fires" trap CONTEXT.md's D-11 discussion already names for the `unique` test.

### Pitfall 3: `--profiles-dir` relative-path resolution has a documented dbt-core inconsistency between commands

**What goes wrong:** [dbt-core issue #3133](https://github.com/dbt-labs/dbt-core/issues/3133)
(open, labeled `type:bug`) reports that `--profiles-dir` is resolved relative to CWD for `dbt
debug` but relative to `--project-dir` for `dbt run` (and by extension `dbt build`), when both are
passed as relative paths.

**Why it happens:** Historical inconsistency in dbt-core's CLI argument handling across commands
that predates the current pinned version; not confirmed fixed in 1.12.0.

**How to avoid:** In this project's specific case, `--project-dir dbt` and `--profiles-dir dbt` are
the *same literal string*, so this ambiguity is defused by construction: whether `--profiles-dir`
resolves against CWD or against `--project-dir`, the result is the same directory
(`<repo_root>/dbt`) as long as CWD is `<repo_root>` — which the empirical test in Pitfall 1
confirms it does resolve to correctly. **This is not a live bug for this project's invocation
pattern**, but it is the reason the empirical test in Pitfall 1 was necessary rather than trusting
either the docs or the Guide's prose claim. If a future plan changes the Makefile to invoke dbt
from a different CWD, or changes `--project-dir`/`--profiles-dir` to different relative values,
this issue becomes live again and must be re-verified the same way.

### Pitfall 4: A negative dbt test that only proves the test exists, not that it fires

**What goes wrong:** T-202's WBS text as originally written defers the duplicate-key negative
proof to "Python-side export tests" — but export tests never invoke dbt, so nothing in that plan
would ever demonstrate `dbt build` actually failing on a duplicate. A green `unique` test on clean
synthetic data proves the test is *present*, not that it *fires* on a violation.

**Why it happens:** It is easy to write the positive case (grain is unique on real committed data,
test passes) and stop there, because the negative case requires standing up a second, poisoned
dbt invocation — genuinely more scaffolding.

**How to avoid:** D-11 already settles this — build the poisoned-fixture harness and assert
`dbt build --vars '{"data_synthetic_path": "<tmp poisoned dir>"}'` exits non-zero specifically on
the AD-040 `unique` test, using `subprocess.run(..., check=False)` and inspecting `returncode` (and
ideally grepping the captured stdout/stderr for the failing test's name, so a red exit code caused
by an unrelated failure is not mistaken for proof of the intended one).

**Warning signs:** A plan's acceptance criteria that only say "the `unique` test exists" rather
than "the `unique` test was proven to fail against a poisoned fixture."

### Pitfall 5: Windows/Linux `make transform` divergence going undetected

**What goes wrong:** Job 3 (`dbt`) in CI is currently `ubuntu-latest` only, while the primary dev
machine is Windows — meaning any path-separator, line-ending, or shell-quoting difference in the
dbt invocation would only ever surface locally, get "fixed" ad hoc, and never get encoded into CI.

**Why it happens:** No Windows leg existed on this job before Phase 3 (confirmed by reading
`ci.yml`, which currently has exactly one `runs-on: ubuntu-latest` step in the `dbt` job, unlike
the `test` job's existing `os: [ubuntu-latest, windows-latest]` matrix).

**How to avoid:** D-22 already mandates adding the same `windows-latest` leg (with the same
choco-install-make step job 2 already uses) to job 3. The Makefile's `SHELL := /bin/sh` /
`.SHELLFLAGS := -eu -c` pin (established in Phase 1) already makes `make transform`'s recipe
portable; the new CI leg is what proves it, not a new mechanism.

**Warning signs:** A `make transform` recipe that uses forward-slash paths hard-coded as string
literals inside SQL (rather than repo-relative dbt vars) would still work on Windows through
`read_csv_auto` (DuckDB accepts forward slashes on Windows), but should be reviewed if any shell
script (not SQL) constructs a path with `/` outside of Git Bash's translation layer.

## Code Examples

### `db.py` accessor skeleton with collect-all-raise-once postconditions (D-10)
```python
# Source: derived from 03_MODULES.md §1.3 + CONTEXT.md D-10 (project-specific design, not
# external library documentation).
def read_mmm_input(layer: str) -> pd.DataFrame:
    con = connect(read_only=True)
    frame = con.execute(
        "select * from fct_mmm_input where layer = ? order by week_start", [layer]
    ).df()
    violations: list[str] = []
    if frame.empty:
        violations.append(f"layer={layer!r}: no rows returned")
    else:
        if not frame["week_start"].is_monotonic_increasing:
            violations.append(f"layer={layer!r}: week_start is not ascending")
        gaps = frame["week_start"].diff().dropna()
        bad_gaps = gaps[gaps != pd.Timedelta(days=7)]
        if not bad_gaps.empty:
            violations.append(f"layer={layer!r}: non-7-day gap(s) at {bad_gaps.index.tolist()}")
        spend_cols = [c for c in frame.columns if c.startswith("spend_")]
        nan_spend_cols = [c for c in spend_cols if frame[c].isna().any()]
        if nan_spend_cols:
            violations.append(f"layer={layer!r}: NaN in spend column(s) {nan_spend_cols}")
        if (frame["revenue"] <= 0).any():
            bad_weeks = frame.loc[frame["revenue"] <= 0, "week_start"].tolist()
            violations.append(f"layer={layer!r}: revenue <= 0 at week(s) {bad_weeks}")
    if violations:
        raise DataContractError(
            "read_mmm_input() postcondition violation(s):\n" + "\n".join(violations)
        )
    return frame
```

### The mart-only guard test (D-09), mirroring the existing four guards' style
```python
# Source: pattern lifted directly from tests/unit/test_forbidden_deps.py and
# tests/unit/test_import_independence.py (this repo, Phase 1) — same AST-walk technique,
# extended to a literal-string scan for CSV/parquet/duckdb-open calls.
_FORBIDDEN_IO_CALLS = {"read_csv", "read_parquet", "read_csv_auto"}  # pandas/duckdb literal calls
_SCAN_PACKAGES = ("model", "decide")

def test_model_and_decide_never_touch_csv_parquet_or_duckdb_directly(repo_root: Path) -> None:
    # AST-walk src/ambo/model/ and src/ambo/decide/ for:
    #   1. any Call whose func attr is in _FORBIDDEN_IO_CALLS
    #   2. any Call to duckdb.connect (outside src/ambo/common/db.py, which is never scanned here)
    ...

def test_report_only_reads_exports_directory(repo_root: Path) -> None:
    # AST-walk src/ambo/report/ for any string literal referencing "data/synthetic",
    # "data/real_anon", or "data/warehouse" — report/ may reference "exports/" only.
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `dbt_utils.unique_combination_of_columns` for composite-key tests | Native `unique` test with an expression `column_name` | Documented as a dbt FAQ pattern well before dbt-core 1.12 — not a recent change, but underused relative to the `dbt_utils` habit | No new dbt package dependency for this project's grain tests |
| Model-level custom SQL for schema drift checks | `contract: {enforced: true}` | dbt-core 1.5 (2023) introduced model contracts; stable by 1.8+ (this project's pin) | Build-time refusal instead of a downstream Python assertion catching drift late |

**Deprecated/outdated:** None specific to this phase — the toolchain (dbt-core 1.8-1.12 range,
dbt-duckdb matching) is current and actively maintained; no superseded APIs are in play.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `--profiles-dir` vs. `--project-dir` relative-resolution inconsistency (dbt-core issue #3133) is not fixed in 1.12.0, but is defused for this project because both flags carry the identical literal string `dbt` | Pitfall 3 | Low — even if the underlying bug were fixed, the two possible resolutions coincide for this project's invocation, so behavior is unaffected either way. Verified empirically that the actual result (Pitfall 1) matches CWD-relative resolution regardless. |
| A2 | The empirically observed CWD-relative path resolution (Pitfall 1) holds identically on Linux (CI's ubuntu-latest runner) since it was only tested on this Windows dev machine | Pitfall 1, Standard Stack | Low-medium — the resolution logic is pure Python path-joining in the dbt-duckdb adapter (OS-independent by construction), but this claim is untested on Linux. D-22's new Windows CI leg plus the existing Ubuntu leg together will surface any divergence immediately once T-201 lands; recommend the plan's acceptance criteria explicitly require both CI legs green, not just local Windows confirmation. |
| A3 | DuckDB's lack of a listed row in dbt's official constraints-support table means constraint-type (`primary_key`/`unique`) translation is unconfirmed, not necessarily broken | Pitfall 2, Pattern 2 | Low — the recommended mitigation (columns-only contract + ordinary tests) sidesteps the question entirely, so this assumption does not gate any decision; it only justifies avoiding a feature this phase does not need. |

## Open Questions

1. **Does dbt-duckdb's `contract: {enforced: true}` (columns-only form) actually reject a
   type-mismatched `SELECT` at build time for this specific dbt-core 1.12.0/dbt-duckdb 1.10.1
   pairing, or only for a missing/extra column?**
   - What we know: dbt-core's contract mechanism is documented to check both column presence and
     `data_type` for every declared column, generically across adapters, by wrapping the model's
     `SELECT` in a typed `CREATE TABLE` statement.
   - What's unclear: This was not independently re-verified against a deliberately
     type-mismatched model in this research session (only the CWD-relative path behavior was
     live-tested, since that was the specifically flagged open question in CONTEXT.md).
   - Recommendation: T-203's plan should include one throwaway red-then-green proof (a model
     declaring `data_type: integer` for a column the `SELECT` actually returns as `double`,
     confirmed to fail `dbt build`, then reverted) — the same "prove it fires, not just exists"
     discipline D-11 already applies to the `unique` test, and Phase 1's D-23 established as
     precedent for all four existing guard tests.

2. **Exact list of `dim_layer` and `fct_platform_reported` columns beyond what SPEC-03 §3 names in
   prose** (SPEC-03 gives descriptions, not a literal column/type table, for these two marts —
   unlike `fct_mmm_input`, which `03_MODULES.md` §8 pins exactly).
   - What we know: `dim_layer`: `layer, weeks, channels_present (list/string), monetary_unit
     ('EUR'|'aEUR'), source_tag ('GROUND-TRUTH'|'REAL-ANON')`. `fct_platform_reported`: week ×
     layer × channel grain, `platform_conversions`, `platform_conv_value`
     (renamed from `platform_revenue_eur`), `impressions`.
   - What's unclear: exact SQL types for `channels_present` (BP-D-19 says "canonical comma-joined
     string in taxonomy order" — so `varchar`, not a DuckDB `LIST`) and whether `weeks` is a
     count (`bigint`) or a range.
   - Recommendation: settle as `varchar` for `channels_present` (matches BP-D-19's explicit
     wording, "comma-joined string") and `bigint` for `weeks` (a simple count) at plan time; this
     is a small enough gap that the planner can resolve it directly rather than needing another
     research pass.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `dbt-core` (via `uv run dbt`) | T-201…T-205, `make transform` | ✓ [VERIFIED: local] | 1.12.0 | — |
| `dbt-duckdb` adapter | same | ✓ [VERIFIED: local] | 1.10.1 | — |
| `duckdb` Python driver | `db.py` (T-204) | ✓ [VERIFIED: local] | 1.5.5 | — |
| GNU Make (native Win32) | `make transform` locally | ✓ [VERIFIED: local, `GNU Make 4.4.1 Built for Windows32`] | 4.4.1 | — |
| `windows-latest` GitHub Actions runner + choco `make` | CI job 3's new D-22 matrix leg | Not locally testable — same pattern as job 2's existing, already-proven Windows leg | — | None needed; job 2 is the working precedent |
| git | layer-order/leak CI jobs (unaffected by this phase) | ✓ [VERIFIED: local, git 2.55.0.windows.2] | 2.55.0 | — |

**Missing dependencies with no fallback:** none.

**Missing dependencies with fallback:** none — everything this phase needs is already installed.

## Validation Architecture

`workflow.nyquist_validation` is absent from `.planning/config.json`, so it is treated as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (already configured, `pyproject.toml` `[tool.pytest.ini_options]`), invoking `dbt build` as a subprocess for dbt-level assertions |
| Config file | `pyproject.toml` (pytest config); `dbt/dbt_project.yml` + `dbt/models/**/*.yml` (dbt test config) — no separate dbt test-runner config file |
| Quick run command | `uv run pytest tests/unit/test_db.py tests/unit/test_export_marts.py tests/unit/test_mart_only_access.py -q` |
| Full suite command | `make transform && make test` (dbt build + full pytest, matching what CI job 3 + job 2 together exercise) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|--------------|
| REQ-q1-truth-recovery (contributing) | AD-042 reconciliation: mart revenue sum matches simulator CSV sum within 1e-6, all three P-layers | dbt singular test + integration | `uv run dbt build --project-dir dbt --profiles-dir dbt` (test named `ad042_revenue_reconciliation`) | ❌ Wave 0 (T-203) |
| REQ-q1-truth-recovery (contributing) | `channels_present` correctly distinguishes structurally-absent from present-but-ineffective channels | dbt singular test (both directions) | same `dbt build` invocation | ❌ Wave 0 (T-203) |
| REQ-grain-and-windows (contributing) | Gapless ascending weekly spine per layer, derived from the seed | dbt singular test (anti-join against `stg_calendar_weekly`) | `dbt build` | ❌ Wave 0 (T-203) |
| REQ-grain-and-windows (contributing) | Duplicate grain keys FAIL, never silently deduplicated | dbt generic test (negative, poisoned fixture) + pytest wrapper | `uv run pytest tests/unit/test_warehouse_build.py::test_duplicate_grain_key_fails_dbt_build -q` | ❌ Wave 0 (T-201/T-202) |
| REQ-dl1-reproducible-pipeline (contributing) | `make transform` builds green locally and in CI job 3 on committed data, no private inputs | integration / smoke | `make transform` | ❌ Wave 0 (T-201) |
| REQ-dl1-reproducible-pipeline (contributing) | Warehouse file lands at exactly `settings.paths.warehouse` | pytest (path assertion) | `uv run pytest tests/unit/test_warehouse_build.py::test_warehouse_file_lands_at_settings_path -q` | ❌ Wave 0 (T-201) |
| REQ-dl1-reproducible-pipeline (contributing) | `fct_mmm_input`/`dim_layer`/`fct_platform_reported` contracts refuse build on drift | dbt build-time contract | `dbt build` | ❌ Wave 0 (T-203) |
| — (D-09 architectural, not a numbered REQ) | model/decide never touch CSV/parquet/duckdb directly; report/ reads only exports/ | pytest (AST guard) | `uv run pytest tests/unit/test_mart_only_access.py -q` | ❌ Wave 0 (T-204) |
| — (D-02 CI mechanic) | Committed export matches regenerated export byte-for-byte | CI-only diff-check (not a pytest) | `make transform && make export && git diff --exit-code exports/` | ❌ Wave 0 (T-205, CI workflow edit) |

### Sampling Rate
- **Per task commit:** the quick-run command above (three targeted pytest files), plus `dbt build`
  whenever a `.sql`/`.yml` file under `dbt/` changed in that commit.
- **Per wave merge:** `make transform && make test` (full dbt build + full pytest suite).
- **Phase gate:** CI job 3 (`dbt`, both `ubuntu-latest` and the new `windows-latest` leg) green,
  plus job 1's existing season-windows diff-check unaffected, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `dbt/dbt_project.yml`, `dbt/profiles.yml` — do not exist yet; T-201 creates them from scratch.
- [ ] `dbt/models/{raw,staging,marts}/` — empty; T-201/T-202/T-203 populate in sequence.
- [ ] `tests/unit/test_db.py` — does not exist; T-204.
- [ ] `tests/unit/test_export_marts.py` — does not exist; T-205.
- [ ] `tests/unit/test_mart_only_access.py` — does not exist (the 5th guard, D-09); T-204.
- [ ] `tests/unit/test_warehouse_build.py` — does not exist; needed for D-11's poisoned-fixture
      proof, D-20's fake-Layer-R exercise, and D-23's path-assertion test; T-201/T-203.
- [ ] `tests/fixtures/warehouse_poisoned/` and `tests/fixtures/real_anon_fake/` — do not exist;
      T-201 (parameterization) enables both, content authored where each is first used (D-11,
      D-20).
- [ ] `src/ambo/common/errors.py` needs a new `DataContractError(AmboError)` subclass — named in
      `03_MODULES.md` §1.3 but not yet added to `errors.py` (currently only `ConfigError` and
      `SimulationError` exist).

## Security Domain

`security_enforcement` is not present in `.planning/config.json`; treated as enabled by default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | This phase has no user-facing auth surface — DuckDB file is local, single-process |
| V3 Session Management | No | N/A — no sessions in a local warehouse build |
| V4 Access Control | Partial | `db.py`'s `connect(read_only=True)` default is the access-control mechanism — the only write path is `dbt build` itself; `db.py` must never expose a write-capable connection to `model`/`decide`/`report` code (proven by the D-09 guard test's "write attempt raises" acceptance criterion, already in T-204's WBS text) |
| V5 Input Validation | Yes | dbt's enforced contract (Pattern 2) and `db.py`'s postcondition checks (D-10) together are this phase's input-validation layer — every frame crossing the AD-030 boundary is schema- and range-checked before any caller sees it |
| V6 Cryptography | No | No secrets, no cryptographic operations in this phase — the private-drop redaction invariant (`AmboError`'s no-private-content rule) is inherited from Phase 1 and unaffected here |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| SQL injection via dbt var interpolation into `read_csv_auto(...)` path strings | Tampering | All path vars in this project are internal dbt vars set by the Makefile/CI/tests, never external user input — no untrusted string ever reaches a dbt Jinja `{{ var(...) }}` call in this phase. Still worth a one-line note in `dbt_project.yml`'s vars documentation that these vars are trusted-input-only, since a future phase (Phase 6 intake) is the first to introduce any externally-sourced path |
| Accidental write to the warehouse file from application code | Tampering | `db.py`'s `read_only=True` default connection (V4 above); the D-09 guard test's write-attempt-raises acceptance criterion |
| Leak of anonymization secrets or client identity via the D-20 fake Layer R fixture | Information Disclosure | D-20 explicitly requires the fixture be "synthetic and obviously fake — it encodes shape, not values"; the leak-scan CI job (unaffected by this phase) already scans the whole tree including `tests/fixtures/` |

## Sources

### Primary (HIGH confidence)
- Local, live-verified toolchain: `uv run dbt --version` (dbt-core 1.12.0, dbt-duckdb 1.10.1), `uv run python -c "import duckdb; print(duckdb.__version__)"` (1.5.5), `make --version` (GNU Make 4.4.1, Win32), `git --version` (2.55.0.windows.2) — run in this session against this repo's actual `.venv`.
- Empirical path-resolution test: three-part live reproduction (relative-path error-message inspection, absolute-flags cross-cwd confirmation, and a full `dbt build` producing a real DuckDB file at the CWD-relative location) against the installed dbt-core 1.12.0 / dbt-duckdb 1.10.1 pairing, run in a scratch directory this session.
- This repository's own files, read directly: `data/synthetic/{s_a,s_b,s_c}/{media_weekly,outcome_weekly}.csv` (row counts, column names, channel sets, date ranges, revenue sums computed via `awk`), `dbt/seeds/season_windows.csv`, `pyproject.toml`, `uv.lock`, `config/settings.yaml`, `src/ambo/common/{config,errors}.py`, `docs/MODULE_CONTRACTS.md`, `docs/SPEC-03_data_model.md`, `docs/EXECUTION_BLUEPRINT/{02_WBS,03_MODULES,05_IMPLEMENTATION_GUIDES,09_ANTI_PATTERNS,10_VALIDATION_GATES}.md`, `.github/workflows/ci.yml`, `Makefile`, `tests/unit/{test_repo_layout,test_forbidden_deps,test_import_independence}.py`.

### Secondary (MEDIUM confidence)
- [dbt Developer Hub — DuckDB setup](https://docs.getdbt.com/docs/local/connect-data-platform/duckdb-setup) — path resolution claim ("relative to profiles.yml"), **empirically contradicted for this project's explicit-flags invocation pattern; see Pitfall 1**.
- [dbt Developer Hub — contract config](https://docs.getdbt.com/reference/resource-configs/contract) — materialization requirements (table/view/incremental support; Python models/materialized views excluded).
- [dbt Developer Hub — constraints reference](https://docs.getdbt.com/reference/resource-properties/constraints) — per-platform constraint support table; DuckDB absent, motivating Pitfall 2's recommendation.
- [dbt Developer Hub — uniqueness of two columns FAQ](https://docs.getdbt.com/faqs/Tests/uniqueness-two-columns) — the expression-based `unique` test pattern used in Pattern 3.
- [dbt-core GitHub issue #3133](https://github.com/dbt-labs/dbt-core/issues/3133) — `--profiles-dir` relative-resolution inconsistency between `dbt debug` and `dbt run`; informs Pitfall 3.
- [DeepWiki — duckdb/dbt-duckdb Constraints and Data Validation](https://deepwiki.com/duckdb/dbt-duckdb/8.4-constraints-and-data-validation) — general confirmation that dbt-duckdb translates contract specs into DuckDB constraints, without version/materialization specifics.

### Tertiary (LOW confidence)
- None relied upon for a load-bearing claim in this document — all package-existence and mechanism claims above were either verified against this repo's own installed toolchain, empirically tested, or cited from official dbt documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed live against the installed `.venv`, not training data.
- Architecture (contract mechanism, path resolution): HIGH for the path-resolution finding (empirically tested three ways against the exact installed versions); MEDIUM for the contract-enforcement type-checking depth (cited from docs, not independently red-then-green tested this session — see Open Question 1).
- Pitfalls: HIGH for Pitfalls 1, 3, 4, 5 (empirically verified or directly derived from this repo's own committed files); MEDIUM for Pitfall 2 (documented absence of DuckDB from a support table, not a confirmed failure).

**Research date:** 2026-08-05
**Valid until:** 30 days, EXCEPT the dbt-core/dbt-duckdb version pins and the empirically-verified
path-resolution behavior — re-verify Pitfall 1's reproduction if `uv.lock`'s `dbt-core`/`dbt-duckdb`
versions ever change, since this is exactly the kind of adapter-internals behavior a minor version
bump could alter silently.
