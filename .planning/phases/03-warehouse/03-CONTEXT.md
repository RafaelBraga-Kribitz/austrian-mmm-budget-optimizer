# Phase 3: Warehouse - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

One queryable source of modeling input, so the model provably reads a contract rather than a
pile of CSVs it could quietly reshape.

Scope is WBS tasks **T-201…T-205** (`docs/EXECUTION_BLUEPRINT/02_WBS.md`, Phase P2 section):
dbt scaffold with raw external views over the committed synthetic CSVs; four staging models
with BP-D-03 unit-neutral renames; three marts (`fct_mmm_input`, `dim_layer`,
`fct_platform_reported`) with the AD-040…044 test suite; `src/ambo/common/db.py` read-only
accessors; `scripts/export_marts.py` with `make export` wiring.

The dependency chain is strictly linear — T-201 → T-202 → T-203 → T-204 → T-205 — so there is
essentially no wave parallelism to find.

**Not in scope:** any model code (`ambo/model/`, Phase 4), the real Layer R *data* (Phase 6 —
though the guarded staging branch is written here, see D-10), the five other export CSVs
(their producing phases add them to this phase's registry), any dbt docs/lineage artifact
(deferred, see below).

### Corrections to upstream documents applied during this discussion

1. **ROADMAP's Phase 3 note on BP-D-05 is stale.** It says `layer_r_present: false` is "a
   blueprint default, not a ratified decision — accept or override it explicitly at task time."
   `docs/ADR/ADR-000` **D-2** ratified BP-D-01…BP-D-20 wholesale and states the DoR
   accept/override item "is satisfied for all twenty by this ADR." `layer_r_present: false` is
   binding. Do not re-litigate it.

2. **WBS T-205 AC-3 is stale.** It reads "Exports land gitignored; `.gitkeep` intact" — written
   before the W5 resolution. `docs/SPEC-08_engineering.md` §2 now reads
   `exports/ (*.csv COMMITTED — DL-1 compares against them; EB-081)` and `.gitignore` lists
   `exports/*.csv` under COMMITTED BY DESIGN. The WBS card was never updated. Settled by D-01
   below; fix the card as part of this phase.

3. **Phase 3 had no effort budget of its own.** The ROADMAP line reads "Shares M2's 2 d with
   Phase 4", so Charter §5's per-phase 2× tripwire had nothing to measure against. Settled by
   D-17.

</domain>

<decisions>
## Implementation Decisions

### Export commit policy

- **D-01:** `exports/mmm_input_weekly.csv` is **committed**, per SPEC-08 §2 and EB-081
  post-W5. Phase 9's DL-1 probe compares regenerated exports against committed versions and is
  the first row of the G-REL release gate — gitignoring the file reopens W5. WBS T-205 AC-3 is
  corrected, not followed.
- **D-02:** Drift is caught by a **CI job 3 diff-check on the D-20 pattern**: regenerate
  (`make transform && make export`), then `git diff --exit-code exports/`. A mart change that
  alters the export fails the build unless the committed CSV is regenerated in the same PR.
  Job 3 already builds dbt, so this adds no job — EB-060's six stay six.
- **D-03:** The export registry is **grow-as-you-go** — one entry now
  (`mmm_input_weekly.csv`); each producing phase adds its own, following D-03 of Phase 1
  (`MODULE_CONTRACTS.md`). The registry must be structured so later phases extend a dict rather
  than copy-paste a new script (T-205 AC-2).
- **D-04:** Float output is **explicit fixed precision — 6 decimals**, pinned in the registry,
  matching what the simulator already writes. pandas' default repr is a library implementation
  detail; a minor version bump could rewrite every line of a committed file and turn the
  job-3 diff-check red for a reason unrelated to the warehouse. Same reasoning as `truth.json`'s
  `sort_keys` + fixed float formatting in Phase 2, and as D-22's `.gitattributes` LF pin.
- **D-05:** The **a€-in-committed-exports interaction is recorded, not acted on here.** Once
  Phase 6 flips `layer_r_present`, this committed export carries Layer R a€ rows in the history
  of a repo that goes public at M3 — and Phase 1's D-26 explicitly scoped a€ figures in
  `exports/` *out* of the leak scan (correctly, when nothing was committed there). Phase 3 adds
  a header comment in `scripts/export_marts.py` and a `docs/RISK_REGISTER.md` entry so D-26's
  scope is revisited **before** the M4 flip. Widening the leak scan now was rejected: the
  patterns cannot be tuned against data that does not exist, and a gate that cries wolf now is
  one that gets ignored in Phase 6.

### Contract-freeze enforcement

- **D-06:** The mart contracts are enforced by **dbt model contracts** —
  `config(contract={enforced: true})` with the full `columns:` + `data_type:` block in the
  schema yml. dbt refuses to build a model whose output does not match the declaration:
  build-time refusal in the warehouse's own language, with a precise error. Replaces the
  ROADMAP's prose-only freeze rule.
  - **Research must confirm dbt-duckdb's constraint-enforcement level before the plan commits
    to this.** dbt-core ≥ 1.8 is pinned; adapter support for contracts/constraints varies. If
    dbt-duckdb cannot enforce, fall back to the pytest-against-the-built-mart form
    (settings.yaml-derived column set, D-23 `test_repo_layout.py` precedent) and say so
    explicitly in the plan.
- **D-07:** **All three marts** get enforced contracts — `fct_mmm_input`, `dim_layer`, and
  `fct_platform_reported`. All three are exposed by `db.py` accessors and therefore all three
  are contract surfaces; `fct_platform_reported` is Phase 8's DC-702 input and
  `dim_layer.monetary_unit` is what keeps the AD-043 unit story straight.
- **D-08:** **The dbt schema yml is the single normative home** for the mart column contracts
  (§A-2 magic numbers, E-4 numeric SSOT). `db.py` **derives** its expected column set from the
  yml (or a small generated constant) rather than restating it, so a contract change propagates
  instead of drifting. `docs/MODULE_CONTRACTS.md` cites the yml **by path** rather than copying
  the list — the same repoint D-02 of Phase 1 did for SPEC-08 §2.
- **D-09:** The AD-030 mart-only rule becomes a **fifth standing guard test**, joining the four
  from Phase 1's D-23. Scope, precisely:
  - `src/ambo/model/` and `src/ambo/decide/` may not read CSV or parquet at all, and may not
    open duckdb outside `src/ambo/common/db.py`;
  - `src/ambo/report/` may read `exports/` only (03_MODULES §10 gives it that access
    legitimately — a repo-wide ban would be wrong).

  This replaces T-204 AC-1's one-time `grep -rn "read_csv" src/ambo/model src/ambo/decide`.
  A grep verified once in Phase 3 decays the moment Phase 4 writes model code, and AD-030 is
  the constraint the entire "model reads a contract, not a pile of CSVs" claim rests on. Sits
  naturally in BP-G-01's existing guard family.
- **D-10:** `db.py` **collects all postcondition violations and raises once** with the full
  list — which assertion, which layer, which offending weeks or columns. 03_MODULES §1.3's
  plural "listing violated assertions" reads this way, and Phase 5's VR-310 debug ladder
  (transforms → scaling round-trip → **data joins** → sampler health) is what will actually
  read this error. A single join bug can trip four assertions at once; peeling them off one
  run at a time is the wrong ergonomics for that moment.

### Test rigor beyond the WBS minimum

- **D-11:** **A real negative dbt test proves duplicate grain keys FAIL.** A pytest points dbt
  at a poisoned fixture directory (duplicate week × layer × channel row in a tmp CSV, tmp
  warehouse file) and asserts `dbt build` exits non-zero on the `unique` test.
  - T-202's validation line defers this to "Python-side export tests", but export tests never
    invoke dbt — nothing would demonstrate that dbt fails. A `unique` test passing on clean
    inputs proves the test exists, not that it fires, and ROADMAP success criterion 4 says
    "FAIL **rather than being silently deduplicated**", which cannot be verified without making
    it happen.
  - **This requires source paths to be parameterized by a dbt var in T-201** — scaffold work
    that belongs at the start of the chain, not bolted on at T-202. The same parameterization
    serves D-14 and Phase 6's intake tests.
- **D-12:** **AD-042 reconciliation covers all three Layer P layers**, not P-SA alone.
  Parameterize the singular test over P-SA, P-SB, P-SC — each layer's mart revenue sum
  reconciles to its own simulator CSV within 1e-6. A P-SA-only check is blind to a dropped S-C,
  a mislabeled S-C-as-S-B, and cross-layer union bugs; Phase 5 runs recovery on all three. All
  three CSVs are already committed, so there is nothing to build. *Note this tightens rather
  than widens a gate, so standing rule 4's ADR requirement does not apply.*
- **D-13:** **`dim_layer.channels_present` derives from source-row presence** — a channel is
  present if it has rows in staging for that layer. Six for every Layer P layer;
  manifest-matched for Layer R, which is exactly what AD-044 asserts at M4. The mart's contract
  states that **model code iterates `channels_present`, never the seven `spend_*` columns.**

  *Why this matters, and why it was not on the original gray-area list:* all three Layer P
  scenarios carry the same six channels — `other` never appears, since BP-D-04 makes it
  Layer-R-only. But 03_MODULES §8 binds `fct_mmm_input` to seven `spend_<channel>` columns, so
  **`spend_other` is structurally 0.0 on every Layer P row.** Meanwhile S-C's `display_video`
  has real spend (92,193 total) and *zero true effect* — that is the VR-304 design. A
  structurally-absent channel and a present-but-ineffective channel must not look the same to
  the model, or MD-040's channel-agnostic priors end up fitting a β for a channel with no data
  at all. `channels_present` is the mart's mechanism for saying which columns are real.

  Nonzero-spend derivation was rejected: it silently reclassifies a real channel that has a
  zero-spend period, and on Layer R it could disagree with `INTAKE_MANIFEST.yaml`, putting
  AD-044 in the position of failing for a legitimate reason.
- **D-14:** **`channels_present` gets a both-directions singular test.** For every layer: each
  channel listed has at least one source row, **and** every `spend_<channel>` column *not*
  listed is 0.0 on every row. Makes the absent-vs-ineffective distinction a checked fact, so a
  pivot bug that leaks S-B spend into an absent column fails at build. Gives AD-044 a working
  shape to inherit at M4.
- **D-15:** **The gapless week spine comes from the seed**, not from SQL date arithmetic.
  Anti-join each layer's weeks against `stg_calendar_weekly`'s rows between that layer's min and
  max `week_start`. One calendar governs the spine as well as the flags (AD-020), and there is
  zero week arithmetic in SQL that could drift from the generator. The seed covers 2019–2027,
  comfortably spanning Layer P's 156 weeks and Layer R's 52–104. *This departs from Guide §8.3's
  `generate_series` instruction — deliberately, and consistent with Guide §8.2's "no
  recomputation of windows in SQL ever". Note it in the PR so a reviewer does not read it as an
  oversight.*
- **D-16:** **AD-043 is implemented strictly:** neither `_eur` nor `_aeur` may appear in **any**
  staging or mart output column; the monetary unit lives only in `dim_layer.monetary_unit`.
  This matches BP-D-03's actual design and T-202 AC-2's wording, and it cannot pass while the
  rename is missing. SPEC-03 AD-001's literal text says a test fails when a mart *mixes* the two
  suffixes — that weaker form passes a mart that forgot the rename entirely, which is the
  failure actually worth catching. **The strict reading is stricter than AD-001 as written —
  state this in the PR so a reviewer does not read it as a deviation.**

### Budget and sequencing

- **D-17:** **Phase 3 is named at 1 d of M2's 2 d; Phase 4 takes the other 1 d.** Each phase
  therefore has its own 2× trip point and an unambiguous ADR obligation. Phase 4 carries eight
  tasks against Phase 3's five, but Phase 3 took on notable extra test scope in this
  discussion, so an even split reflects where the work actually sits. **Record the split in the
  `docs/BUILD_LOG.md` M2 entry** so it is not re-derived later.
- **D-18:** **Tests ship in the plan that creates what they verify** — contracts and AD-043
  with the models, spine/reconciliation/`channels_present` with the marts, the guard test and
  the job-3 diff-check with `db.py`/export. Source paths are parameterized in T-201 so the
  poisoned fixture has somewhere to point from the start. Every commit stays self-verifying and
  no plan lands an unverified model, matching the contract-first rule.
- **D-19:** **Named shed order for the 1 d → 2 d zone.** Everything added in this discussion
  sits beyond the WBS minimum, so shedding one is not a spec deviation. Shed in this order, and
  **flag each shed in `docs/BUILD_LOG.md` before doing it** — never absorb quietly:
  1. the poisoned-fixture harness (D-11) — highest scaffold cost;
  2. the secondary mart contracts on `dim_layer` / `fct_platform_reported` (D-07);
  3. AD-042's S-B / S-C extension (D-12).

  **Never shed:** the `fct_mmm_input` enforced contract (D-06), the mart-only guard test (D-09),
  or `channels_present` and its derivation (D-13) — Phase 4 consumes all three directly.
  At 2 d, stop and write the standing-rule-5 ADR.

### Layer R staging branch

- **D-20:** **The `layer_r_present` branch ships written and fixture-exercised.** Write the
  jinja-guarded union per BP-D-05 (ratified — omitting it would need its own ADR), then build a
  minimal fake `data/real_anon/`-shaped fixture under `tests/fixtures/` and run one dbt
  invocation with `layer_r_present: true` against it. Reuses the source-path parameterization
  D-11 already requires. Phase 6 then flips a flag onto a path that has already executed,
  instead of running dead SQL for the first time in a phase that also has a permission gate, a
  prior freeze, and real client data in play.
  - The fixture is synthetic and obviously fake — it encodes *shape*, not values, and must not
    be mistaken for or shaped by real client data.

### Makefile and CI

- **D-21:** **The D-17 `make transform` conditional is removed.** `make transform` becomes
  `uv run dbt build --project-dir dbt --profiles-dir dbt`, full stop. The conditional existed so
  job 3 could pass by *running* rather than being skipped (Phase 1's D-16); once a dbt project
  exists that purpose is spent, and a "nothing to build" branch would turn a deleted
  `dbt_project.yml` into a green CI job. dbt itself fails loudly on a missing project, and
  `tests/unit/test_repo_layout.py` already asserts the tree against SPEC-08 §2 — which lists
  `dbt/ (dbt_project.yml, profiles.yml, models/, seeds/…)` — so the file's existence is guarded
  where guards live.
- **D-22:** **CI job 3 gains a `windows-latest` matrix leg**, with the same choco-install-make
  step job 2 uses. The job name stays `dbt`, so EB-060's six hold (D-21 of Phase 1 already
  established that a matrix leg is not a seventh job). Job 3 is cheap — small data, no PyTensor
  compile — and today it is ubuntu-only while the dev machine is Windows, so profile-path,
  path-separator and line-ending breakage would only ever appear locally, get fixed ad hoc, and
  never get encoded.
- **D-23:** **Warehouse path: keep Guide §8.1's relative form, pin the invocation, assert the
  result.** `profiles.yml` keeps `../data/warehouse/ambo.duckdb`; the Makefile always passes
  `--project-dir dbt --profiles-dir dbt` so resolution never depends on the caller's cwd; and a
  test asserts the built file sits at exactly `settings.paths.warehouse`. No new env var, which
  keeps EB-041's surface clean.
  - **Research must verify dbt-duckdb's actual path-resolution base.** Guide §8.1 asserts the
    `path:` resolves relative to the *profile directory*; if it in fact resolves relative to the
    invocation cwd, the warehouse lands somewhere other than `settings.paths.warehouse` and
    `db.py` reports "run make transform" against a file that was just built. **Treat §8.1's
    claim as unconfirmed.**

### `fct_platform_reported`

- **D-24:** **Build the full Layer P surface now and pre-declare the Layer R extension.**
  Week × layer × channel with `platform_conversions`, `platform_conv_value` (the BP-D-03 rename
  of `platform_revenue_eur`), and `impressions` — all three already committed by SIM-060/061.
  Enforce the contract on exactly those columns, and **state in the contract that Layer R adds
  `clicks` at M4 as an anticipated extension recorded in the intake ADR**, so it lands as a
  planned amendment rather than an ADR-worthy surprise break. Phase 8 gets a stable Layer P
  surface to build DC-702 against during the drop-blocked window.

### Claude's Discretion

- Internal structure of the export registry dict (D-03) and the exact float-format directive
  (D-04), as long as the output is byte-stable at 6 decimals.
- The concrete form of the poisoned-fixture harness (D-11) — how source paths are
  parameterized, where the tmp warehouse lives, how the non-zero exit is asserted.
- Wording of the `RISK_REGISTER.md` entry and the `export_marts.py` header comment (D-05).
- Exact column set and shape of the fake Layer R fixture (D-20), beyond matching the SPEC-02
  §5.2 taxonomy and the BP-D-03 column names.
- Whether the `channels_present` both-directions check (D-14) is one singular test or two, and
  its exact failure-message format.
- How `db.py` derives its column set from the dbt yml (D-08) — direct yml parse, a generated
  constant, or a dbt artifact read — provided there is exactly one authored home.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Governing spec (primary — read in full before writing any dbt or db.py code)

- `docs/SPEC-03_data_model.md` — the whole warehouse contract, 65 lines: §1 stack and unit
  suffixes (AD-001, AD-002), §2 the four staging models, §3 the three marts, §4 the AD-040…044
  test set, §5 the six BI exports and AD-050.

### Task breakdown and implementation guidance

- `docs/EXECUTION_BLUEPRINT/02_WBS.md` — **Phase P2 section, T-201…T-205 (lines 431–510).**
  Task-by-task objective, prerequisites, outputs, implementation notes, validation, and
  acceptance criteria. *Note T-205 AC-3 is stale — see the Corrections block above.*
- `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` §8.1–§8.3 (lines 225–244) — SQL-level
  dbt guidance: profile and vars, the staging union and BP-D-03 renames, the jinja pivot over
  `channel_taxonomy`, the gapless-spine anti-join, and the AD-042 singular test. *Two claims
  here are deliberately departed from or unconfirmed — see D-15 and D-23.*
  Also §9 (lines 245–256) for CI job mechanics.
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` §1.3 (`db.py` public API and postconditions), §8
  (`dbt/` — the binding `fct_mmm_input` column contract), §9 (`export_marts.py` contract and
  the all-scripts rules), §10 (the enforced cross-module dependency graph — the basis for D-09).
  *Frozen as of Phase 1's D-02: read as design input, never edit.*
- `docs/EXECUTION_BLUEPRINT/01_PHASES.md` P2 section — phase framing, entry/exit criteria, and
  the phase-independent standing rules (notably rule 5, the effort tripwire).

### Quality gates and checklists

- `docs/EXECUTION_BLUEPRINT/10_VALIDATION_GATES.md` §4 (G-DATA-W, lines 60–66) — the warehouse
  gate: AD-040 grain/spine, AD-041 ranges, AD-042 reconciliation, AD-043 unit-suffix, AD-044
  (M4), BP-G-03 taxonomy equality. §2 (lines 32–44) — the standing per-PR gates including the
  BP-G-01 guard-test family D-09 joins.
- `docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md` M2 section — the PR checklist this milestone must
  tick with evidence. *M2's PR covers Phases 3 and 4 together (D-11 of Phase 1).*
- `docs/EXECUTION_BLUEPRINT/09_ANTI_PATTERNS.md` §A-2 (magic numbers — the basis for D-08's
  single-home rule) and §A-17 (never fix a governance gate by editing history).
- `docs/MODULE_CONTRACTS.md` — the contract of record. **Phase 3 must add same-PR entries for
  `src/ambo/common/db.py` and `scripts/export_marts.py`**, or `tests/unit/test_repo_layout.py`
  fails (Phase 1 D-23 asserts every `src/ambo/` module has an entry).

### Ratified decisions and blueprint defaults

- `docs/ADR/ADR-000_document-precedence-and-blueprint-defaults.md` — **D-1** precedence is
  scoped, not ranked (Charter governs goals/scope/acceptance, SPEC governs operative detail,
  ADR outranks both). **D-2** ratifies BP-D-01…BP-D-20 wholesale — this is what makes
  `layer_r_present: false` binding and the ROADMAP's Phase 3 note stale.
- `docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md` §5 — **BP-D-03** (unit-neutral staging renames,
  line 107), **BP-D-05** (`layer_r_present` var and the `intake_channels.csv` seed for AD-044,
  line 109), **BP-D-19** (`channels_present` as a comma-joined string in taxonomy order,
  line 123), **BP-D-20** (`make all` fails fast, never auto-samples, line 124).
- `docs/SPEC-08_engineering.md` §2 canonical repository layout (including
  `exports/ (*.csv COMMITTED)` — the basis for D-01), §3 the pinned dependency table, §5 the
  Makefile target interface, §6 the six-job CI contract, §8 git conventions.

### Constants and inputs this phase reads

- `config/settings.yaml` — the seven-channel taxonomy in SPEC-02 §5.2 order (the dbt
  `channel_taxonomy` var must equal it; BP-G-03 tests this), and `paths.warehouse`
  (`data/warehouse/ambo.duckdb`, the assertion target in D-23).
- `dbt/seeds/season_windows.csv` — the committed Austrian-calendar seed (AD-020), source for
  `stg_calendar_weekly` **and** for the gapless spine (D-15). Diff-checked in CI job 1 by
  Phase 1's D-20.
- `data/synthetic/{s_a,s_b,s_c}/media_weekly.csv` — columns
  `week_start, channel, spend_eur, impressions, platform_conversions, platform_revenue_eur`;
  six channels, no `other`, no `clicks`.
- `data/synthetic/{s_a,s_b,s_c}/outcome_weekly.csv` — columns
  `week_start, revenue_eur, orders, promo_flag`.
- `docs/SPEC-02_agency_data_pipeline.md` §5.2 — the fixed seven-channel taxonomy and its order.
- `docs/SPEC-06_decision_layer.md` §5 — what DC-702 consumes from `fct_platform_reported`
  (relevant to D-24's freeze decision).

### Requirements traceability

- `.planning/REQUIREMENTS.md` — REQ-q1-truth-recovery (contributing), REQ-grain-and-windows
  (contributing — weekly spine), REQ-dl1-reproducible-pipeline (contributing — `make transform`
  opens the DL-1 probe).
- `.planning/intel/constraints.md` §AD-001…AD-050 — condensed constraint text when a quick
  reference beats the full SPEC.
- `.planning/phases/02-ground-truth-simulator/02-CONTEXT.md` — Phase 2's decisions; its
  `<code_context>` names this phase as the consumer of the SIM-004 CSV schemas.
- `.planning/phases/01-repository-foundation/01-CONTEXT.md` — D-02/D-03 (`MODULE_CONTRACTS.md`
  is the contract of record, grow-as-you-go), D-11 (milestone branches — M2 is one branch,
  `m2-warehouse-model`, spanning Phases 3 and 4), D-16/D-17 (phase-gated jobs pass by running;
  the vacuously-correct-check pattern D-21 now retires), D-20 (the seed diff-check D-02
  mirrors), D-21 (the CI matrix precedent D-22 follows), D-23 (the guard-test family D-09
  joins), D-25 (`settings.yaml` authored whole with `extra='forbid'`), D-26 (the leak-scan
  scope D-05 flags for revisit).

### Open research questions (not decisions — verify before planning commits)

1. **dbt-duckdb constraint/contract enforcement level** (blocks D-06). dbt-core ≥ 1.8 is
   pinned, but adapter support for `contract: {enforced: true}` and column `data_type`
   enforcement varies. If unsupported, fall back to the pytest-against-the-built-mart form.
2. **dbt-duckdb `path:` resolution base** (blocks D-23). Guide §8.1 claims profile-dir-relative;
   confirm against the invocation cwd before relying on it.
3. **Does dbt find a committed `profiles.yml` inside `--project-dir`** without an explicit
   `--profiles-dir`, and is the explicit flag portable across Git Bash, native Win32 make, and
   Ubuntu? (Same class as Phase 1's open Makefile `SHELL` question.)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `dbt/seeds/season_windows.csv` (Phase 1) — the committed calendar, 2019–2027, columns
  `iso_year, iso_week, week_start, advent_flag, schulbeginn_flag, jan_dip_flag, spring_flag,
  summer_lull_flag`. Feeds `stg_calendar_weekly` and the D-15 spine. Never recompute these
  windows in SQL.
- `data/synthetic/{s_a,s_b,s_c}/` (Phase 2) — nine committed artifacts, byte-reproducible, the
  raw layer's only inputs. All three scenarios carry the same six channels.
- `src/ambo/common/config.py`, `logging.py`, `errors.py` (Phase 1) — `Settings`,
  `load_settings()`, `repo_root()`, structured logging with `AMBO_PRIVATE_DROP` redaction, and
  the typed exception root. `DataContractError` belongs in the `errors.py` hierarchy.
- `tests/unit/test_repo_layout.py`, `test_forbidden_deps.py`, `test_import_independence.py`,
  `test_no_requests.py` (Phase 1) — the four existing guard tests. D-09's mart-only guard is
  the fifth and should match their structure and failure-message style.
- `Makefile` (Phase 1) — the 18-target interface. `transform` and `export` already exist as
  conditional/stub targets; `make all` already sequences
  `transform → recover → sensitivity → decide → ssot → export → report`.
- `.github/workflows/ci.yml` (Phase 1) — six jobs. Job 3 (`dbt`) is currently ubuntu-only and
  runs `make transform`; job 1 already carries the D-20 seed diff-check whose shape D-02
  reuses.

### Established Patterns

- **Machine enforcement over the written rule, every time the rule is checkable.** Phase 1's
  D-12, D-20 and D-23 each converted a rule into a mechanism. D-02, D-06, D-09, D-14, D-16 and
  D-23 continue it — this is the intended direction whenever the planner finds another such
  rule.
- **Single home for every fact** (EB-040, E-4, §A-2). D-08 applies it to the mart column
  contract; D-04's pinned float format and D-13's `channels_present` are the same instinct.
- **Config duplication across languages is tested, not eliminated** — BP-G-03's dbt-var vs
  `settings.yaml` taxonomy check is the accepted precedent when two languages must know one
  fact.
- **Byte-stable, LF-only output discipline** (`.gitattributes`, Phase 1 D-22; `truth.json`,
  Phase 2). D-04 extends it to the committed export.
- **`pydantic.BaseModel` with `extra='forbid'`** for all config/schema classes, project-wide.
- **Append-only history** (EB-082). No force-push, no rebase, no amend — including as a fix for
  a red gate.

### Integration Points

- **Phase 4 (MMM on S-A)** consumes `db.py`'s `read_mmm_input(layer)` as its only data doorway
  (AD-030), and depends on D-13's `channels_present` to know which of the seven `spend_*`
  columns are real for a given layer. T-203 blocks T-301 and beyond.
- **Phase 6 (Agency Intake)** flips `layer_r_present` to true, adds `data/real_anon/` and
  `dbt/seeds/intake_channels.csv`, and activates AD-044. D-20's fixture-exercised branch and
  D-14's presence test are what it inherits; D-05's risk entry is what it must act on.
- **Phase 8 (Decision Layer)** reads `fct_platform_reported` for DC-702's attribution gap, and
  extends the D-03 export registry with `allocation_scenarios.csv` and `attribution_gap.csv`.
- **Phase 9 (Reporting & Release)** runs the DL-1 probe against the committed exports D-01
  establishes, and extends the registry with the remaining files.
- **M2 branch topology:** Phases 3 and 4 commit into one branch `m2-warehouse-model`, with the
  PR opened as a draft at milestone start (Phase 1 D-19) so `pull_request` CI fires on every
  push. One PR at the M2 exit gate, not one per phase.

</code_context>

<specifics>
## Specific Ideas

- **The `spend_other` finding is the most load-bearing thing in this document.** `other` is
  Layer-R-only (BP-D-04), so every Layer P row will carry a structurally-zero `spend_other`
  column, while S-C's `display_video` carries real spend with zero true effect by design
  (VR-304). If the model cannot tell those two apart, MD-040's channel-agnostic priors fit a β
  for a channel with no data. D-13 and D-14 exist for this; the planner should treat
  `channels_present` as a Phase-4 interface, not an incidental `dim_layer` column.

- **The poisoned-fixture harness (D-11) is scaffold with three customers, not one.** It serves
  the duplicate-key negative test, the D-20 Layer R branch exercise, and Phase 6's intake tests.
  Parameterizing source paths in T-201 is what makes all three possible — build it there, once,
  rather than three times.

- **Two guide instructions are deliberately departed from, and both need a line in the PR** so
  a reviewer does not read them as oversights: D-15 (seed-derived spine, not Guide §8.3's
  `generate_series`) and D-16 (strict AD-043, stricter than SPEC-03 AD-001's "mixes" wording).
  Neither is a gate widening; both are tightenings, so neither owes an ADR under standing
  rule 4 — but silence would look like drift.

- **Three upstream document corrections belong in this phase's PR**, not just in this file:
  WBS T-205 AC-3 (exports gitignored → committed), the ROADMAP Phase 3 BP-D-05 note (stale
  post-ADR-000 D-2), and the ROADMAP Phase 3 effort line (no per-phase budget → 1 d, D-17).
  Per Phase 1's D-07, correcting a stale statement of already-ratified fact is an
  interpretation, not a spec edit — a `docs/BUILD_LOG.md` entry suffices; no ADR is owed. A
  change to SPEC-08, SPEC-03, or any gate would be different.

- **Effort awareness.** Phase 3 is 1 d with a 2 d tripwire (D-17), and this discussion added
  meaningful scope on top of T-201…T-205: three enforced contracts, a poisoned-fixture harness,
  a fifth guard test, a Windows CI leg, the job-3 diff-check, AD-042 × 3, the
  `channels_present` test, and a Layer R fixture. D-19's shed order exists precisely so the
  executor does not improvise under pressure — but the planner should size deliberately up
  front rather than relying on it.

</specifics>

<deferred>
## Deferred Ideas

- **Revisit D-26's leak-scan scope for committed `exports/*.csv`** — **Phase 6**, before the
  `layer_r_present` flip. Phase 1 already deferred "widen the leak-scan pattern set when real
  data lands" to Phase 6; D-05 adds the specific reason (the export is now a committed public
  artifact that will carry a€ rows) and the tracking mechanism (a `RISK_REGISTER.md` entry, so
  it does not depend on memory).

- **`dbt docs generate` lineage graph as a portfolio artifact** — **Phase 9**. A rendered
  lineage diagram from raw CSVs through staging to `fct_mmm_input` would make the "the model
  reads a contract" claim visible at a glance, which is squarely a DL-10/RB reporting concern.
  Raised during this discussion and deliberately not decided here: Phase 9 owns everything a
  reader touches, and Charter O-5 excludes hosted surfaces, so any such artifact must be a
  committed static image under `docs/assets/`, not a served docs site.

- **`clicks` joins `fct_platform_reported`** — **Phase 6**, as the pre-declared extension in
  D-24, recorded in the intake ADR rather than treated as a contract break.

- **Left to the researcher and planner, not deferred to a later phase:** where the BP-G-03
  taxonomy-equality pytest lives and how it reads the dbt var; whether `dim_layer` and
  `fct_platform_reported` are also exported (SPEC-03 §5 lists only `mmm_input_weekly.csv` for
  this phase); the exact row ordering of the committed export.

</deferred>

---

*Phase: 3-Warehouse*
*Context gathered: 2026-08-05*
