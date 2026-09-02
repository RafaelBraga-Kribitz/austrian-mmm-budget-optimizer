# Deferred Items — Phase 02 (Ground-Truth Simulator)

Out-of-scope discoveries logged during plan execution, per the executor's SCOPE BOUNDARY
rule (only auto-fix issues directly caused by the current task's changes).

## 02-01 — `ruff format --check .` on Phase 2 planning docs (resolved on this lineage)

**Found during:** 02-01 Task 3 verification (`make lint` / `ruff format --check .`).

**Issue:** `uv run ruff format --check .` reported two files "would be reformatted":
- `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`
- `.planning/phases/02-ground-truth-simulator/02-RESEARCH.md`

Both are markdown files with embedded Python code fences that ruff's formatter normalizes
(blank-line spacing around `def`/`@given`). On `origin/m0-bootstrap` this was deferred
(those files predated 02-01 execution there). On this lineage they landed in the same
plan's 2A context copy (`9cebc29`), so they *are* this plan's files.

**Scope decision:** Formatted both files in Task 3 so `make lint` is green (plan
acceptance criterion). Not treated as a standing deferral.

**Status:** Resolved 2026-09-02 — `make lint` exits 0 after the format.
