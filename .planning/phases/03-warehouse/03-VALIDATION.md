---
phase: 3
slug: warehouse
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `03-RESEARCH.md` § Validation Architecture. Per-task rows are filled in once
> `03-*-PLAN.md` files exist; task IDs below are the ROADMAP WBS IDs (T-201…T-205).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (already configured via `pyproject.toml` `[tool.pytest.ini_options]`), invoking `dbt build` as a subprocess for dbt-level assertions |
| **Config file** | `pyproject.toml` (pytest); `dbt/dbt_project.yml` + `dbt/models/**/*.yml` (dbt tests) — no separate dbt test-runner config |
| **Quick run command** | `uv run pytest tests/unit/test_db.py tests/unit/test_export_marts.py tests/unit/test_mart_only_access.py -q` |
| **Full suite command** | `make transform && make test` (dbt build + full pytest — what CI jobs 2 + 3 together exercise) |
| **Estimated runtime** | ~30 seconds (dbt build on committed synthetic data + targeted pytest) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command above, **plus** `uv run dbt build --project-dir dbt --profiles-dir dbt` whenever that commit touched any `.sql` / `.yml` file under `dbt/`
- **After every plan wave:** Run `make transform && make test`
- **Before `/gsd-verify-work`:** Full suite green, **and** CI job 3 (`dbt`) green on both `ubuntu-latest` and the new `windows-latest` leg; job 1's season-windows diff-check must remain unaffected
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T-201 | 03-01 | 1 | REQ-dl1-reproducible-pipeline | — | Warehouse file lands at exactly `settings.paths.warehouse`; no private inputs read | integration | `uv run pytest tests/unit/test_warehouse_build.py::test_warehouse_file_lands_at_settings_path -q` | ✅ | ✅ green |
| T-201 | 03-01 | 1 | REQ-dl1-reproducible-pipeline | — | `make transform` green locally and in CI on committed data only | smoke | `make transform` | ✅ | ✅ green |
| T-202 | 03-03 | 2 | REQ-grain-and-windows | — | Duplicate grain keys FAIL the build; never silently deduplicated | negative (poisoned fixture) | `uv run pytest tests/unit/test_warehouse_build.py::test_duplicate_grain_key_fails_dbt_build -q` | ✅ | ✅ green |
| T-203 | 03-04 | 3 | REQ-q1-truth-recovery | — | AD-042: mart revenue sum == simulator CSV sum within 1e-6, all three P-layers | dbt singular test | `uv run dbt build --project-dir dbt --profiles-dir dbt` (`ad042_revenue_reconciliation`) | ✅ | ✅ green |
| T-203 | 03-05 | 4 | REQ-q1-truth-recovery | — | `channels_present` distinguishes structurally-absent from present-but-ineffective (both directions) | dbt singular test | `uv run dbt build --project-dir dbt --profiles-dir dbt` | ✅ | ✅ green |
| T-203 | 03-04 | 3 | REQ-grain-and-windows | — | Gapless ascending weekly spine per layer (anti-join vs `stg_calendar_weekly`) | dbt singular test | `uv run dbt build --project-dir dbt --profiles-dir dbt` | ✅ | ✅ green |
| T-203 | 03-04 / 03-05 / 03-06 | 3 / 4 / 5 | REQ-dl1-reproducible-pipeline | V5 Input Validation | `fct_mmm_input` / `dim_layer` / `fct_platform_reported` contracts refuse build on schema drift | dbt build-time contract | `uv run dbt build --project-dir dbt --profiles-dir dbt` | ✅ | ✅ green |
| T-204 | 03-02 / 03-07 | 1 / 6 | D-09 (architectural; G-ARCH) | V4 Access Control | `model`/`decide` never touch CSV/parquet/duckdb directly; `report/` reads only `exports/`; write attempt raises | pytest AST guard | `uv run pytest tests/unit/test_mart_only_access.py -q` | ✅ | ✅ green |
| T-205 | 03-08 | 7 | REQ-grain-and-windows | — | `exports/mmm_input_weekly.csv` contract-tested; duplicate grain keys FAIL | pytest | `uv run pytest tests/unit/test_export_marts.py -q` | ✅ | ✅ green |
| T-205 | 03-09 | 8 | D-02 (CI mechanic) | — | Committed export matches regenerated export byte-for-byte | CI-only diff-check | `make transform && make export && git diff --exit-code exports/` | ✅ | ✅ green locally; ⬜ pending human CI confirmation (Task 3 checkpoint) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `dbt/dbt_project.yml`, `dbt/profiles.yml` — created by plan 03-01 (T-201)
- [x] `dbt/models/{raw,staging,marts}/` — populated by plans 03-01/03-03/03-04/03-05/03-06 in sequence (T-201/T-202/T-203)
- [x] `tests/unit/test_warehouse_build.py` — created by plan 03-01, extended by 03-03/03-04/03-05/03-06; carries the D-11 poisoned-fixture proof, the D-20 fake-Layer-R exercise, and the D-23 path assertion
- [x] `tests/unit/test_db.py` — created by plan 03-07 (T-204)
- [x] `tests/unit/test_mart_only_access.py` — created by plan 03-02 (the 5th D-09 guard, T-204)
- [x] `tests/unit/test_export_marts.py` — created by plan 03-08 (T-205)
- [x] `tests/fixtures/real_anon_fake/` — created by plan 03-06 (D-20 fixture run). `tests/fixtures/warehouse_poisoned/` was **not** created as a static directory — plans 03-03/03-05 implemented the D-11 poisoned-fixture harness as a `synthetic_tree_copy` pytest fixture that copies `data/synthetic/` into `tmp_path` and poisons it programmatically at test time, reused unmodified by 03-05/03-06. This satisfies D-11's intent (a real negative dbt test proving duplicate grain keys FAIL) without a committed poisoned-data directory; no plan SUMMARY records this as a shed or a gap.
- [x] `src/ambo/common/errors.py` — `DataContractError(AmboError)` added by plan 03-02 (T-204)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Status |
| --- | --- | --- | --- | --- |
| CI job 3 green on the `windows-latest` leg | REQ-dl1-reproducible-pipeline | Cannot be asserted from a local run — requires an actual GitHub Actions execution on a Windows runner | Push the branch, open the Actions run, confirm job 3 passes on both `ubuntu-latest` and `windows-latest` matrix legs | ⬜ pending — this plan's Task 3 checkpoint (`blocking`, human-verify) discharges this row; not yet confirmed |
| Contract-drift refusal is genuinely enforced for a **type** mismatch (RESEARCH Open Question 1) | REQ-dl1-reproducible-pipeline | Documented but not red-then-green proven for dbt-core 1.12.0 / dbt-duckdb 1.10.1 | In T-203, temporarily change a contracted column's `data_type` to a mismatched type, confirm `dbt build` fails, then revert and confirm green | ✅ closed — plan 03-04 Task 2 proved all three contract-drift shapes (type mismatch, missing column, extra column) red-then-green on `fct_mmm_input`, see `03-04-SUMMARY.md` coverage id D2 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** The validation *document* (per-task map, Wave 0, sign-off criteria) is complete and
every automated row is green as of plan 03-09 Task 2. This does **not** assert the phase's one
remaining manual item (CI job 3's `windows-latest` leg) is green — that is exactly what this
plan's Task 3 blocking checkpoint exists to confirm with a human, and it has not run yet. See the
Manual-Only Verifications table above for its live status.
