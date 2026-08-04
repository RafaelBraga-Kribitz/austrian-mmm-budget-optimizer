---
phase: 01-repository-foundation
plan: 07
subsystem: testing
tags: [pytest, ast, architectural-guards, gitignore, line-endings, module-contracts]

# Dependency graph
requires:
  - phase: 01-02
    provides: "pyproject.toml (pytest --strict-markers, mypy strict), uv.lock (the O-3 import-scope binding decision), importable src/ambo/ subpackage tree"
  - phase: 01-03
    provides: "docs/MODULE_CONTRACTS.md with entries for config.py, errors.py, logging.py, and the Dependency directions / forbidden-edges table"
  - phase: 01-04
    provides: "src/ambo/common/{config,errors,logging}.py -- repo_root(), ConfigError, get_logger() -- the tests/conftest.py repo_root fixture wraps ambo.common.config.repo_root()"
  - phase: 01-05
    provides: "Makefile's `test` target (pytest -m \"not smoke and not fit\") that these guards now run under"
provides:
  - "tests/conftest.py -- repo_root, seeded_rng, tmp_repo fixtures plus a pytest_sessionfinish hook that turns NO_TESTS_COLLECTED into a hard failure"
  - "tests/unit/test_repo_layout.py -- the fourth guard (D-23): SPEC-08 section 2 + D-14 canonical layout with no allowlist, plus the two-directional MODULE_CONTRACTS.md contract-first cross-check"
  - "tests/unit/test_forbidden_deps.py -- Charter O-3 / EB-030 scope wall, import-scoped only (does not parse uv.lock, per the binding 01-02 checkpoint decision)"
  - "tests/unit/test_import_independence.py -- SIM-003/W-2 simulate<->model AST firewall, plus the pymc_marketing and pm.sample() confinement checks from MODULE_CONTRACTS.md's forbidden-edges table"
  - "tests/unit/test_no_requests.py -- EB-070 zero-network guarantee, plus a nested-pytest.main() proof that --strict-markers rejects an unregistered marker"
  - "tests/unit/test_line_endings.py -- D-22 proof that no tracked text file (via git check-attr text) contains a carriage-return byte"
  - "tests/unit/test_gitignore.py -- EB-081 ignore-rule guard, converting T-003's manual probe into a non-destructive test"
  - "docs/BUILD_LOG.md T-010 AC-1 entry recording all four guards proven red on a planted violation, plus the CRLF working-tree-drift fix this plan's own test surfaced"
affects: [01-08, 01-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AST-walk guards, never runtime import or text search: import names compared by whole first-dotted-segment equality (never substring), so a package whose name embeds a forbidden one as a fragment (sklearn_extra_fake_pkg) is not flagged, and an aliased import (import sklearn as np) still is, because the alias name is never what's compared"
    - "D-17 vacuous-pass visibility: every guard asserts its scanned-file-count is nonzero (or, for simulate/model today, explicitly documents why a near-zero count is a real scan, not a skip) and prints what it scanned"
    - "git ls-files as the tracked-file enumeration boundary: test_repo_layout.py and test_line_endings.py both enumerate via git ls-files rather than filesystem walk, so untracked scratch files and gitignored artifacts are out of scope by construction -- exactly what makes the planted-violation proof for the layout and line-ending guards require an explicit git add -f to be visible at all"
    - "Non-destructive real-working-tree probing: test_gitignore.py operates on the actual repository (not tmp_repo) via a create/assert/finally-cleanup/assert-status-unchanged pattern, since the rules under test are this repo's own .gitignore"
    - "Scratch-branch planted-violation proof with zero commits: the branch is created, violations are planted and reverted as pure working-tree edits (never committed), then the branch is deleted with a safe non-force `git branch -d` -- nothing can reach m0-bootstrap's history because nothing was ever committed to the scratch ref"
    - "core.autocrlf-driven working-tree CRLF drift is fixed via delete + fresh `git checkout HEAD -- <path>`, not a plain `git checkout -- <path>` (which no-ops when git's clean-filtered comparison already matches the index, even though raw on-disk bytes differ) -- no commit needed since the object database blob was already LF-clean"

key-files:
  created:
    - tests/conftest.py
    - tests/unit/test_repo_layout.py
    - tests/unit/test_forbidden_deps.py
    - tests/unit/test_import_independence.py
    - tests/unit/test_no_requests.py
    - tests/unit/test_line_endings.py
    - tests/unit/test_gitignore.py
  modified:
    - docs/BUILD_LOG.md
    - .gitignore
    - PROJECT_CHARTER.md
    - docs/ADR/ADR-000_document-precedence-and-blueprint-defaults.md
    - docs/SPEC-01_ground_truth_simulator.md
    - docs/SPEC-04_mmm_model.md
    - docs/SPEC-05_validation_recovery.md
    - docs/SPEC-06_decision_layer.md
    - docs/SPEC-08_engineering.md
    - .planning/INGEST-CONFLICTS.md
    - .planning/PROJECT.md
    - .planning/intel/SYNTHESIS.md
    - .planning/intel/requirements.md

key-decisions:
  - "test_forbidden_deps.py is import-scoped only and does NOT parse uv.lock, deviating from the plan's own key_links/WBS text (both of which describe a lockfile scan). This follows the binding human checkpoint ruling recorded in 01-02-SUMMARY.md and .planning/STATE.md: Charter O-3 governs ambo's own imports, not every transitive package name in the resolved dependency tree, because scikit-learn arrives transitively via the Charter-sanctioned pymc-marketing chain and a tree-scoped guard would fail on it."
  - "Fixed twelve already-tracked files' working-tree-only CRLF bytes (committed blobs were already LF-clean) discovered by test_line_endings.py during its own authoring -- not part of the planted-violation proof, a real pre-existing defect this guard's job is to catch. Root cause: core.autocrlf=true on this dev machine plus a plain `git checkout --` no-op when git's clean-filter comparison already matches the index. Fixed via delete + `git checkout HEAD --` per file; no commit needed since object database content was unchanged."
  - "The planted CRLF-violation file used an explicit .gitattributes override line (docs/_scratch_crlf_violation.scratchdat text) rather than relying on the .gitattributes catch-all's `auto` value, matching the plan's literal 'staged with the attribute overridden' instruction, even though the catch-all alone would have been sufficient for the guard's own text != 'unset' filter."

requirements-completed: [REQ-scope-out, REQ-scope-in, REQ-dl8-quality]

coverage:
  - id: D1
    description: "tests/conftest.py provides repo_root/seeded_rng/tmp_repo fixtures and a pytest_sessionfinish hook that fails a zero-collected-items session instead of letting it report success"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: unit
        ref: "uv run pytest tests/golden -q exits 1 with 'FATAL: pytest collected 0 test item(s)' printed (verified by hand -- tests/golden/ has only .gitkeep)"
        status: pass
      - kind: other
        ref: "uv run pytest tests --collect-only -q reports 39 collected items"
        status: pass
    human_judgment: false
  - id: D2
    description: "tests/unit/test_repo_layout.py enforces the SPEC-08 section 2 + D-14 canonical layout with no allowlist, and the MODULE_CONTRACTS.md contract-first cross-check in both directions (missing entry, orphan entry, duplicate heading)"
    requirement: "REQ-scope-in"
    verification:
      - kind: unit
        ref: "tests/unit/test_repo_layout.py (3 tests: top-level entries, src/ambo subpackages, module-contract cross-check)"
        status: pass
      - kind: other
        ref: "Planted a tracked top-level scratch dir, a module with no contract entry, and a duplicated MODULE_CONTRACTS heading by hand -- each turned its respective assertion red with the expected message, then green after reverting"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/unit/test_forbidden_deps.py, test_import_independence.py, test_no_requests.py -- the three original architectural guards, each reporting a nonzero scanned count, whole-name matching (no substring false positives), AST-based (not text search)"
    requirement: "REQ-scope-out"
    verification:
      - kind: unit
        ref: "tests/unit/test_forbidden_deps.py (1 test), test_import_independence.py (3 tests), test_no_requests.py (2 tests) -- all pass"
        status: pass
      - kind: other
        ref: "Planted `import robyn` under src/ambo/ and a simulate->model cross-import by hand -- each turned the relevant guard red; a substring-fragment import (sklearn_extra_fake_pkg) did not trip the whole-name match"
        status: pass
    human_judgment: false
  - id: D4
    description: "tests/unit/test_line_endings.py and test_gitignore.py convert the D-22 and T-003 manual probes into tests; the gitignore probe leaves git status --porcelain byte-identical before/after"
    requirement: "REQ-scope-out"
    verification:
      - kind: unit
        ref: "tests/unit/test_line_endings.py (1 test), test_gitignore.py (3 tests) -- all pass"
        status: pass
      - kind: other
        ref: "Verified by hand: BEFORE=$(git status --porcelain); run test_gitignore.py; AFTER=$(git status --porcelain); BEFORE == AFTER"
        status: pass
    human_judgment: false
  - id: D5
    description: "All four guards proven to fail on a planted violation (T-010 AC-1), on a scratch branch created/used/deleted with zero commits, evidence recorded in docs/BUILD_LOG.md"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "docs/BUILD_LOG.md's new T-010 AC-1 entry names all four guards, each with the planted change and the exact failing pytest node id + AssertionError message; git branch --list shows only m0-bootstrap and main after; git diff HEAD~1 --numstat -- docs/BUILD_LOG.md reports 0 deletions"
        status: pass
    human_judgment: false

duration: ~24min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 7: Test Scaffold and Four Architectural Guards Summary

**Seven test modules (`conftest.py` + 6 guard files, 13 new tests, 39 total) turning D-23's four standing architectural rules — repository layout, forbidden dependencies, simulate/model independence, no-network — plus the line-ending pin and gitignore rules into scripts a reviewer runs, each proven to fail on a planted violation.**

## Performance

- **Duration:** ~24 min (from prior plan's close at 19:25:45Z through final self-check)
- **Started:** 2026-08-04T19:25:45Z (approx., prior plan's close)
- **Completed:** 2026-08-04T19:49:00Z (approx.)
- **Tasks:** 3 (all `type="auto"`, no checkpoints)
- **Files modified:** 8 new + 1 (`docs/BUILD_LOG.md`) modified as plan deliverables; 12 additional pre-existing tracked files had their working-tree bytes re-checked-out (content-identical, LF-fix only, no commit)

## Accomplishments
- `tests/conftest.py`: `repo_root` (session-scoped, wraps `ambo.common.config.repo_root()`), `seeded_rng` (NumPy `Generator` off a fixed constant, never global RNG state), `tmp_repo` (throwaway git repo with a local commit identity) fixtures, plus a `pytest_sessionfinish` hook that converts a `NO_TESTS_COLLECTED` exit into a hard failure with an explicit collected-count message — verified by hand against `tests/golden/` (only a `.gitkeep`): exits 1 with `FATAL: pytest collected 0 test item(s)`
- `tests/unit/test_repo_layout.py`: the fourth guard (D-23) — two frozen sets (permitted top-level entries, permitted `src/ambo/` subpackages) expressing the SPEC-08 section 2 + D-14 canonical layout with **no allowlist**, enumerated via `git ls-files` so untracked/gitignored paths are out of scope by construction; plus the contract-first cross-check parsing `docs/MODULE_CONTRACTS.md`'s level-3 headings against every non-`__init__` module under `src/ambo/`, catching a missing entry, an orphan entry, and a duplicate heading as three distinct failure messages
- `tests/unit/test_forbidden_deps.py`, `test_import_independence.py`, `test_no_requests.py`: the three original guards, all AST-based (never runtime import or text search), whole-first-segment name matching, each asserting a nonzero scanned-file count. `test_import_independence.py` also encodes the two remaining `MODULE_CONTRACTS.md` forbidden edges (`pymc_marketing` confined to `validate/crosscheck.py`, `pm.sample()`/`pymc.sample()` confined to `model/fit.py`) and `test_no_requests.py` proves `--strict-markers` rejects an unregistered marker via a nested `pytest.main()` against a throwaway file
- `tests/unit/test_line_endings.py`, `test_gitignore.py`: the D-22 CRLF pin and the T-003/EB-081 ignore-rule probe, both converted from manual checks into tests. The line-ending guard consults `git check-attr text` rather than a hardcoded extension list; the gitignore guard operates on the real working tree through a create/assert/`finally`-cleanup pattern, proven to leave `git status --porcelain` byte-identical
- All four guards proven red-then-green: three via ad-hoc planting during authoring (repo-layout, forbidden-deps, import-independence, all reverted before commit) and, separately, the full T-010 AC-1 proof on a scratch branch (`scratch-01-07-planted-violations`, zero commits ever made on it, deleted with a safe `git branch -d`) — each of the four final guards planted, confirmed red with its exact node id + message, reverted, before the next was planted. Evidence recorded in `docs/BUILD_LOG.md`
- Full unit suite: 26 pre-existing tests + 13 new = **39 passed**, 95% coverage on the two modules in `--cov=src/ambo` scope

## Task Commits

Each task was committed atomically:

1. **Task 1: Build the test scaffold and the repository-layout guard** - `a853dbc` (test)
2. **Task 2: Write the three original architectural guards** - `009f56f` (test)
3. **Task 3: Convert the line-ending and ignore-rule probes into tests and record the planted-violation evidence** - `7f62340` (test)

**Plan metadata:** committed separately after this summary is written.

## Files Created/Modified
- `tests/conftest.py` - `repo_root`, `seeded_rng`, `tmp_repo` fixtures; `pytest_sessionfinish` empty-collection guard
- `tests/unit/test_repo_layout.py` - the fourth guard: canonical-layout + contract-first cross-check, no allowlist
- `tests/unit/test_forbidden_deps.py` - Charter O-3 / EB-030 import-scoped scope wall
- `tests/unit/test_import_independence.py` - SIM-003/W-2 firewall + `pymc_marketing`/`pm.sample()` confinement
- `tests/unit/test_no_requests.py` - EB-070 zero-network guard + `--strict-markers` proof
- `tests/unit/test_line_endings.py` - D-22 no-CRLF proof via `git check-attr text`
- `tests/unit/test_gitignore.py` - EB-081 ignore-rule guard, non-destructive real-tree probe
- `docs/BUILD_LOG.md` - T-010 AC-1 entry (four planted-violation proofs + the CRLF-drift fix note), append-only
- `.gitignore`, `PROJECT_CHARTER.md`, four `docs/SPEC-*.md`, `docs/ADR/ADR-000_...md`, four `.planning/*.md` — working-tree bytes only, re-checked-out to strip stray CRLF; content and committed blobs unchanged (no diff against HEAD, no new commit needed for these)

## Decisions Made
- **`test_forbidden_deps.py` does not scan `uv.lock`** — see key-decisions above. This is a deliberate deviation from the plan's own text (Task 2's action paragraph and the `key_links` entry both describe a lockfile scan), following the binding O-3 import-scope ruling from the 01-02 human checkpoint. Documented in the test module's own docstring as well as here.
- **CRLF working-tree drift fixed via delete + fresh `git checkout HEAD --`**, not a plain `git checkout --` (which is a no-op when git's clean-filtered comparison already matches the index despite differing raw bytes on disk) — see key-decisions above.
- **The planted CRLF-violation file used an explicit `.gitattributes` override** rather than relying on the catch-all's `auto` value, matching the plan's literal instruction even though not strictly required by the guard's own `!= "unset"` filter logic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 override, human-ratified] `test_forbidden_deps.py` does not parse `uv.lock`, despite the plan's own text instructing it to**
- **Found during:** Task 2, before writing `test_forbidden_deps.py`
- **Issue:** The plan's Task 2 action paragraph and `key_links` entry both instruct scanning `uv.lock` for forbidden distribution names ("a parse of `uv.lock` finds no package whose name is a forbidden distribution... so a transitive arrival is caught too"). This directly conflicts with the binding decision from plan 01-02's human checkpoint (recorded in `01-02-SUMMARY.md` and `.planning/STATE.md`'s Decisions log): Charter O-3 is import-scoped, not tree-scoped, specifically because `scikit-learn` arrives transitively via the Charter-sanctioned `pymc-marketing` chain and a tree-scoped guard would fail on this approved dependency.
- **Fix:** Implemented the guard as import-scoped only — an AST walk of `src/ambo/`, `scripts/`, and `tests/` for forbidden import names, with no `uv.lock` parsing. Documented the rationale in the test module's own docstring, citing the binding decision by source.
- **Files modified:** `tests/unit/test_forbidden_deps.py`
- **Verification:** `uv run pytest tests/unit/test_forbidden_deps.py -q` passes with `scikit-learn` present (transitively) in `uv.lock`; a planted `import robyn` still turns the guard red
- **Committed in:** `009f56f` (Task 2 commit)

**2. [Rule 1 - Bug] Twelve already-tracked files carried working-tree-only CRLF bytes**
- **Found during:** Task 3, while authoring and first running `test_line_endings.py`
- **Issue:** `test_line_endings.py`'s own first run failed against real, already-committed files: `.gitignore`, `PROJECT_CHARTER.md`, four `docs/SPEC-*.md` files, `docs/ADR/ADR-000_...md`, and four `.planning/*.md` files all had CRLF bytes on disk, even though `git show HEAD:<path>` confirmed each committed blob was already LF-only. Root cause: this dev machine's `core.autocrlf` is `true`; a plain `git checkout -- <path>` no-ops when git's clean-filtered comparison of the working file already equals the index blob, so the stray CRLF (introduced by an earlier direct write, before any git filter touched the file) survived indefinitely.
- **Fix:** For each affected path, deleted the file and ran `git checkout HEAD -- <path>` (a full re-materialization from the index, which does apply the `eol=lf` smudge filter). Verified 0 CR bytes remaining in all twelve files afterward, and `git status --porcelain` empty for all of them both before and after (content byte-identical apart from line-ending representation — no commit needed).
- **Files modified:** `.gitignore`, `PROJECT_CHARTER.md`, `docs/SPEC-01_ground_truth_simulator.md`, `docs/SPEC-04_mmm_model.md`, `docs/SPEC-05_validation_recovery.md`, `docs/SPEC-06_decision_layer.md`, `docs/SPEC-08_engineering.md`, `docs/ADR/ADR-000_document-precedence-and-blueprint-defaults.md`, `.planning/INGEST-CONFLICTS.md`, `.planning/PROJECT.md`, `.planning/intel/SYNTHESIS.md`, `.planning/intel/requirements.md`
- **Verification:** `uv run pytest tests/unit/test_line_endings.py -q` passes; `git status --porcelain` unchanged for all twelve files pre/post fix
- **Committed in:** No commit needed (working-tree-only fix, object database already correct); recorded as a related note in the `docs/BUILD_LOG.md` T-010 AC-1 entry (`7f62340`, Task 3 commit)

---

**Total deviations:** 2 (1 human-ratified architectural override carried forward from a prior plan's checkpoint decision; 1 Rule 1 bug this task's own guard test surfaced and fixed inline)
**Impact on plan:** No scope creep. Both were required for the plan's own stated acceptance criteria (the forbidden-deps guard must not false-positive on an approved dependency; the line-ending guard must actually pass against the real, already-committed tree) to be satisfiable at all.

## Issues Encountered
One minor lint-only correction during Task 2: `ruff check` flagged two `E501` line-too-long errors in `test_import_independence.py` (an f-string exceeding 100 columns inside the assertion-message builder); reflowed via a local `rel` variable before commit. No logic change, not tracked as a formal deviation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All four D-23 architectural guards are now real, running scripts (`make test` includes them) rather than checklist items — the `06_CHECKLISTS [STD]` layout item is machine-enforced with no allowlist, exactly as D-23 intended
- `tests/conftest.py`'s `tmp_repo` fixture is ready for plan 01-09's layer-order tests to reuse, per the plan's own note
- Plan 01-08 (leak scan, `.pre-commit-config.yaml`) can now register its own pre-commit hooks against a test suite that already fails loudly on zero-collection, giving CI a real backstop from the start
- The AST-walk pattern (whole-first-segment name matching, nonzero-scanned-count assertions) established across all three forbidden-import guards is a reusable template for any future architectural guard
- `docs/MODULE_CONTRACTS.md`'s contract-first rule (D-23) is now mechanically enforced — the next module added under `src/ambo/` without a same-PR contract entry will fail CI immediately, not just in review
- The `core.autocrlf`-driven CRLF working-tree drift is now understood and has a documented fix pattern (delete + fresh `git checkout HEAD --`); worth a note for any contributor cloning fresh on a machine with `core.autocrlf=true`, though `.gitattributes`' `eol=lf` pin means a **fresh** clone should never exhibit this (the drift here came from direct file writes predating any git filter application, not from checkout itself)

---
*Phase: 01-repository-foundation*
*Completed: 2026-08-04*
