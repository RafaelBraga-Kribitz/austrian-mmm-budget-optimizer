# Deferred Items — Phase 02 (Ground-Truth Simulator)

Out-of-scope discoveries logged during plan execution, per the executor's SCOPE BOUNDARY
rule (only auto-fix issues directly caused by the current task's changes).

## 02-01 — `make lint` fails on pre-existing planning docs, unrelated to Task 3's scope

**Found during:** 02-01 Task 3 verification (`make lint` / `ruff format --check .`).

**Issue:** `uv run ruff format --check .` reports two files "would be reformatted":
- `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`
- `.planning/phases/02-ground-truth-simulator/02-RESEARCH.md`

Both are markdown files authored during Phase 2 planning (ratified before this plan's
Task 1 ran) containing embedded Python code fences that ruff's formatter reformats
(blank-line normalization around `def`/`@given`). Neither file is in this plan's
`files_modified` list, and neither was touched by Task 1 or Task 3.

**Confirmed pre-existing:** `git stash` (removing all of this plan's uncommitted changes)
reproduces the identical two-file failure, proving it predates this plan's execution.

**Scope decision:** Not fixed — out of scope per SCOPE BOUNDARY (issues in files this plan
did not modify). `ruff check .` (lint proper) and `uv run mypy` both pass cleanly in
isolation; only `ruff format --check .` on these two markdown files fails. `make test`
passes fully (73 passed). Task 3's own verify command
(`uv run python -c "import hypothesis"; uv run pytest tests/unit/test_gitignore.py
tests/unit/test_forbidden_deps.py tests/unit/test_no_requests.py -x`) is unaffected and
green.

**Status:** Deferred — a future plan touching `02-PATTERNS.md`/`02-RESEARCH.md` (or a
dedicated formatting pass) should run `uv run ruff format .` on these two files.

## 02-04 — same pre-existing `ruff format --check .` failure re-confirmed, still out of scope

**Found during:** 02-04 Task 1/2/3 verification (`make lint`).

**Issue:** Identical to the 02-01 entry above — `02-PATTERNS.md` and `02-RESEARCH.md` still
fail `ruff format --check .`. Neither file is in this plan's `files_modified` list and
neither was touched by any of this plan's three tasks.

**Confirmed pre-existing (again):** `git stash` of every uncommitted 02-04 change reproduces
the identical two-file failure with the plan's own files removed from the diff.

**Scope decision:** Not fixed, same reasoning as 02-01. `ruff check .` and `uv run mypy` both
pass cleanly across the whole repository including the three files this plan adds/modifies
(`src/ambo/simulate/dgp.py`, `tests/unit/test_dgp.py`, `docs/MODULE_CONTRACTS.md`). `uv run
ruff format --check src/ambo/simulate/dgp.py tests/unit/test_dgp.py` passes in isolation.
