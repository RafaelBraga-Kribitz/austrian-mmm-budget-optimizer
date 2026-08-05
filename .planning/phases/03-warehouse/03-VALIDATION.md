---
phase: 3
slug: warehouse
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| T-201 | TBD | TBD | REQ-dl1-reproducible-pipeline | — | Warehouse file lands at exactly `settings.paths.warehouse`; no private inputs read | integration | `uv run pytest tests/unit/test_warehouse_build.py::test_warehouse_file_lands_at_settings_path -q` | ❌ W0 | ⬜ pending |
| T-201 | TBD | TBD | REQ-dl1-reproducible-pipeline | — | `make transform` green locally and in CI on committed data only | smoke | `make transform` | ❌ W0 | ⬜ pending |
| T-202 | TBD | TBD | REQ-grain-and-windows | — | Duplicate grain keys FAIL the build; never silently deduplicated | negative (poisoned fixture) | `uv run pytest tests/unit/test_warehouse_build.py::test_duplicate_grain_key_fails_dbt_build -q` | ❌ W0 | ⬜ pending |
| T-203 | TBD | TBD | REQ-q1-truth-recovery | — | AD-042: mart revenue sum == simulator CSV sum within 1e-6, all three P-layers | dbt singular test | `uv run dbt build --project-dir dbt --profiles-dir dbt` (`ad042_revenue_reconciliation`) | ❌ W0 | ⬜ pending |
| T-203 | TBD | TBD | REQ-q1-truth-recovery | — | `channels_present` distinguishes structurally-absent from present-but-ineffective (both directions) | dbt singular test | `uv run dbt build --project-dir dbt --profiles-dir dbt` | ❌ W0 | ⬜ pending |
| T-203 | TBD | TBD | REQ-grain-and-windows | — | Gapless ascending weekly spine per layer (anti-join vs `stg_calendar_weekly`) | dbt singular test | `uv run dbt build --project-dir dbt --profiles-dir dbt` | ❌ W0 | ⬜ pending |
| T-203 | TBD | TBD | REQ-dl1-reproducible-pipeline | V5 Input Validation | `fct_mmm_input` / `dim_layer` / `fct_platform_reported` contracts refuse build on schema drift | dbt build-time contract | `uv run dbt build --project-dir dbt --profiles-dir dbt` | ❌ W0 | ⬜ pending |
| T-204 | TBD | TBD | D-09 (architectural; G-ARCH) | V4 Access Control | `model`/`decide` never touch CSV/parquet/duckdb directly; `report/` reads only `exports/`; write attempt raises | pytest AST guard | `uv run pytest tests/unit/test_mart_only_access.py -q` | ❌ W0 | ⬜ pending |
| T-205 | TBD | TBD | REQ-grain-and-windows | — | `exports/mmm_input_weekly.csv` contract-tested; duplicate grain keys FAIL | pytest | `uv run pytest tests/unit/test_export_marts.py -q` | ❌ W0 | ⬜ pending |
| T-205 | TBD | TBD | D-02 (CI mechanic) | — | Committed export matches regenerated export byte-for-byte | CI-only diff-check | `make transform && make export && git diff --exit-code exports/` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `dbt/dbt_project.yml`, `dbt/profiles.yml` — do not exist; T-201 creates from scratch
- [ ] `dbt/models/{raw,staging,marts}/` — empty; T-201/T-202/T-203 populate in sequence
- [ ] `tests/unit/test_warehouse_build.py` — does not exist; needed for the D-11 poisoned-fixture proof, the D-20 fake-Layer-R exercise, and the D-23 path assertion (T-201/T-203)
- [ ] `tests/unit/test_db.py` — does not exist; T-204
- [ ] `tests/unit/test_mart_only_access.py` — does not exist (the 5th D-09 guard); T-204
- [ ] `tests/unit/test_export_marts.py` — does not exist; T-205
- [ ] `tests/fixtures/warehouse_poisoned/` and `tests/fixtures/real_anon_fake/` — do not exist; T-201 adds the parameterization that enables both, content authored where each is first used (D-11, D-20)
- [ ] `src/ambo/common/errors.py` — add `DataContractError(AmboError)`; named in `03_MODULES.md` §1.3 but absent (only `ConfigError`, `SimulationError` exist today)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI job 3 green on the `windows-latest` leg | REQ-dl1-reproducible-pipeline | Cannot be asserted from a local run — requires an actual GitHub Actions execution on a Windows runner | Push the branch, open the Actions run, confirm job 3 passes on both `ubuntu-latest` and `windows-latest` matrix legs |
| Contract-drift refusal is genuinely enforced for a **type** mismatch (RESEARCH Open Question 1) | REQ-dl1-reproducible-pipeline | Documented but not red-then-green proven for dbt-core 1.12.0 / dbt-duckdb 1.10.1 | In T-203, temporarily change a contracted column's `data_type` to a mismatched type, confirm `dbt build` fails, then revert and confirm green |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
