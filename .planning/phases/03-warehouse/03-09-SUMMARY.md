---
phase: 03-warehouse
plan: 09
subsystem: ci
tags: [ci, dbt, export-drift, m2-close]

duration: 25min
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 9: CI close and M2 warehouse BUILD_LOG Summary

**Job 3 is a two-leg Ubuntu/Windows matrix with an export drift gate. Job 2 builds the warehouse before pytest. `make lint`'s ruff format is scoped to Python. R-14 and the M2 BUILD_LOG close are recorded. Task 3 (live GitHub Actions on both OS legs) is deferred under D-19 — stacked PRs do not fire `ci.yml`.**

## Task Commits

1. **Task 1: CI job 3 Windows matrix + export drift** — `b68a514` (feat)
2. **Task 1b: job 2 warehouse-before-pytest** — `608ea2f` (fix; m0 `f58e4f1`)
3. **Task 1c: ruff format scoped to `src tests scripts`** — `a7945ba` (fix; m0 `61ae810`)
4. **Task 2: R-14, ROADMAP corrections, BUILD_LOG close** — `25ed91d` (docs)

**Plan metadata:** (this commit)

m0 had **no 03-09-SUMMARY.md**; this file is written here.

## Accomplishments

- `dbt` job: `strategy.matrix.os: [ubuntu-latest, windows-latest]`, fail-fast false, Chocolatey make-install, `make transform` → `make export` → `git diff --exit-code exports/`.
- `test` job: `make transform` after `uv sync` so `db.py` / export tests find `data/warehouse/ambo.duckdb` on a fresh checkout.
- `make lint`: `ruff format --check src tests scripts`.
- R-14: leak-scan scope for committed `exports/*.csv` must be revisited in Phase 6 before `layer_r_present` flip.
- Local: `make transform && make export && git diff --exit-code exports/` exits 0. `make lint && make test` — **316 passed**, 93% coverage.

## Deviations from Plan

**1. [Process] 2A copy** of CI/Makefile/docs from m0 `58e76ee` / `f58e4f1` / `61ae810` / `f8302fe`.

**2. [Process] Task 3 blocking-human CI confirmation not discharged.** `ci.yml` only runs on push/PR against `main` (D-19). Same pattern as M0 (#11) and M1. This chat did **not** invent an `"Approved"` token. A main-based vehicle after the stack merges is what confirms both `dbt` legs.

**3. [Process] 4B** one PR per plan. m0's missing 03-09 SUMMARY is written on this lineage.

**4. [Disk] EXECUTION_BLUEPRINT/02_WBS.md** is gitignored and absent here; the T-205 AC-3 correction is recorded in BUILD_LOG only (same as m0).

## Next Phase Readiness

Phase 3 warehouse science is complete on this lineage. **Phase 4 (MMM on S-A) is not on `m0-bootstrap`.** Next work is drop-independent: plan Phase 4 from specs, or fill wait windows with intake T-501…T-506 / decide T-701…T-704 / report T-801/T-802. No Layer R fits (3A, A-5).

---
*Phase: 03-warehouse*
*Completed: 2026-09-02*

## Self-Check: PASSED
