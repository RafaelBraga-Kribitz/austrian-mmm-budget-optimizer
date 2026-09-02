# Deferred Items — Phase 3 (warehouse)

Out-of-scope discoveries logged per the executor's scope-boundary rule: not fixed,
not part of any Phase 3 plan's `files_modified`.

## 03-01 — `ruff format --check .` on Phase 3 planning docs (resolved on this lineage)

**Found during:** 03-01 Task 3 verification (`make lint` / `ruff format --check .`).

**Issue:** `uv run ruff format --check .` reported two files "would be reformatted":
- `.planning/phases/03-warehouse/03-PATTERNS.md`
- `.planning/phases/03-warehouse/03-RESEARCH.md`

Both are markdown files with embedded Python code fences that ruff's formatter normalizes.
On `origin/m0-bootstrap` this was deferred (those files were not in 03-01 `files_modified`).
On this lineage they landed in the same plan's 2A context copy (`dabdb6f`), so they *are*
this plan's files.

**Scope decision:** Formatted both files so `make lint` is green (same 02-01 precedent).
Not treated as a standing deferral.

**Status:** Resolved 2026-09-02 — `make lint` exits 0 after the format.
