---
phase: 01-repository-foundation
plan: 05
subsystem: infra
tags: [make, build-interface, readme, ci-contract, posix-sh]

# Dependency graph
requires:
  - phase: 01-02
    provides: "pyproject.toml (uv-run tool invocations lint/test target against), uv.lock, src/ambo/ package tree"
provides:
  - "Makefile — the canonical 18-target SPEC-08 section 5 build interface (EB-050), portable across Linux and Windows Git Bash via a pinned SHELL/.SHELLFLAGS"
  - "README.md — scaffold with a ## Roadmap section every Makefile stub message's pointer resolves against (D-27/D-28)"
affects: [01-06, 01-08, 01-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SHELL := /bin/sh + .SHELLFLAGS := -eu -c pinned at the top of the Makefile — resolves natively on Linux and, via native-Win32 GNU Make's basename PATH fallback, inside Git Bash on Windows (RESEARCH.md Pattern 1)"
    - "D-27 loud-failing stub via a parameterized `define STUB` make macro (`$(call STUB,N)`) — every unimplemented target echoes the exact phase-numbered message and exits non-zero, so a missing target can never report success by doing nothing"
    - "D-17 vacuously-correct check pattern applied to `transform`: it runs the real dbt-project-exists predicate now (true branch dormant until Phase 3) rather than shipping a stub, so CI job 3 has a real green check from day one"
    - "BP-D-20 fail-fast guard on `all`: a shell predicate over `data/posteriors/*.parquet` runs before the composite `$(MAKE) transform recover sensitivity decide ssot export report` invocation, so `all` can never trigger a fit and never silently no-ops when required posteriors are absent"

key-files:
  created:
    - Makefile
    - README.md

key-decisions:
  - "Sampling-target EB-050 runtime-string scope resolved as fit-synthetic, fit-real, sensitivity (the three targets that write or would write posteriors), not recover/decide/ssot/export/report which only read already-fit output — the plan's action text left this open ('one per sampling target') and this is the reading consistent with EB-050's own wording ('write posteriors atomically')."
  - "Plan prose said 'twelve' stub targets but its own explicit phase-mapping list names thirteen (simulate, validate-sim, intake, anonymize, validate-intake, fit-synthetic, fit-real, recover, sensitivity, decide, ssot, export, report) — implemented all thirteen named in the list, since 18 total minus the five real targets (setup, transform, test, lint, all) arithmetically requires thirteen, not twelve. Auto-fixed per Rule 1 (the plan's own list is unambiguous; only the summary count in the prose was wrong)."

requirements-completed: [REQ-dl8-quality, REQ-milestones]

coverage:
  - id: D1
    description: "Makefile declares exactly the 18 SPEC-08 section 5 targets, .PHONY-listed in spec order, with no target outside that list"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "for t in <all 18 names>; do make -n \"$t\"; done — all resolve with no 'No rule to make target' error; grep -cE '^[a-z-]+:' Makefile == 18"
        status: pass
    human_judgment: false
  - id: D2
    description: "Thirteen unimplemented targets exit non-zero with the exact D-27 message naming their owning phase; the mapping matches the README Roadmap table"
    requirement: "REQ-milestones"
    verification:
      - kind: other
        ref: "make simulate exits 2, output contains 'NOT IMPLEMENTED — arrives in Phase 2 (see README §Roadmap)'; same pattern verified for fit-synthetic (Phase 4, with runtime line printed first)"
        status: pass
    human_judgment: false
  - id: D3
    description: "make lint runs ruff check, ruff format --check, mypy in that fixed order and stops at first failure; make test deselects smoke+fit by default and includes smoke under SMOKE=1"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "make -n lint shows the three lines in order; make -n test shows -m \"not smoke and not fit\"; SMOKE=1 make -n test shows -m \"not fit\"; uv run pytest -m \"not smoke and not fit\" -q passes 16/16"
        status: pass
    human_judgment: false
  - id: D4
    description: "make transform is vacuously-correct (real dbt-project-exists check, exits 0 with a nothing-to-build notice today); make all fails fast with a fit-synthetic instruction and never triggers a fit"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "make transform exits 0, output states no dbt project found; make all exits 2 (non-zero), output names 'fit-synthetic'; make -n all shows the transform/recover/sensitivity/decide/ssot/export/report chain with no fit-synthetic or fit-real line anywhere in it"
        status: pass
    human_judgment: false
  - id: D5
    description: "README.md exists with a ## Roadmap section listing all nine phases and status, satisfying every Makefile stub's pointer"
    requirement: "REQ-milestones"
    verification:
      - kind: other
        ref: "grep -q '^## Roadmap' README.md; grep -cE '^\\| *[1-9] *\\|' README.md == 9; grep -ci 'future work' == 0; grep -c '!\\[' == 0; grep -q 'make setup'; every Phase N appearing in a Makefile stub message (2,4,5,6,7,8,9) has a matching README row"
        status: pass
    human_judgment: false

duration: ~8min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 5: Makefile and Scaffold README (build interface, loud stubs) Summary

**The full SPEC-08 section 5 eighteen-target build interface with a Linux/Windows-portable shell pin, thirteen phase-numbered loud-failing stubs, two vacuously-correct real checks (`transform`, `all`), and the minimal nine-phase `README.md` every stub message's pointer resolves against.**

## Performance

- **Duration:** ~8 min (from prior session's close at 19:07:45Z through final metadata commit)
- **Started:** 2026-08-04T19:07:45Z (approx., prior plan's close)
- **Completed:** 2026-08-04T19:15:55Z (approx.)
- **Tasks:** 2 (both `type="auto"`, no checkpoints)
- **Files modified:** 2 (1 per task: `Makefile`, `README.md`)

## Accomplishments
- `Makefile` declares exactly the 18 SPEC-08 section 5 targets (`.PHONY`, spec order), opened with `SHELL := /bin/sh` / `.SHELLFLAGS := -eu -c` (RESEARCH.md Pattern 1) so recipes are POSIX sh on both Linux and Windows Git Bash without relying on a developer's personal shell — verified against the actual dev-machine toolchain (GNU Make 4.4.1, ezwinports)
- Five real targets: `setup` (uv venv + uv sync + pre-commit install, with the read-only-reviewer no-op rationale recorded inline), `lint` (ruff check → ruff format --check → mypy, first-failure-wins), `test` (SMOKE=1-conditional marker expression via a make `ifeq`, fit marker always deselected per EB-061), `transform` (D-17 vacuously-correct real dbt-project-exists check, not a stub), and `all` (BP-D-20 fail-fast guard on `data/posteriors/*.parquet` before invoking the composite `transform recover sensitivity decide ssot export report` chain — never triggers a fit)
- Thirteen loud-failing stub targets, each firing a single parameterized `define STUB` macro that echoes the exact D-27 message (`NOT IMPLEMENTED — arrives in Phase N (see README §Roadmap)`) and exits non-zero — phase mapping: `simulate`/`validate-sim` → 2, `intake`/`anonymize`/`validate-intake` → 6, `fit-synthetic` → 4, `fit-real`/`sensitivity` → 7, `recover`/`ssot`/`export` → 5, `decide` → 8, `report` → 9
- EB-050 expected-runtime strings (`FIT_SYNTHETIC_RUNTIME`, `FIT_REAL_RUNTIME`, `SENSITIVITY_RUNTIME`) print ahead of the stub message for the three sampling targets
- `README.md` scaffold: title, one-paragraph what-this-is (Charter-derived), `## Roadmap` table with all nine phases and milestone mapping (Phase 1 `in progress`, Phases 2–9 `not started`), and a `## Status` note pointing at `make setup`/`make lint`/`make test`, `PROJECT_CHARTER.md`, and `docs/` — no numeric results, badges, or Future Work section, per D-28's scaffold-not-DL-10 scope

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the canonical Makefile with the portable shell pin and loud stubs** - `0d46727` (feat)
2. **Task 2: Write the scaffold README with the nine-phase roadmap section** - `64e8fe5` (docs)

**Plan metadata:** committed separately after this summary is written.

## Files Created/Modified
- `Makefile` - 18-target SPEC-08 section 5 build interface, portable shell pin, D-27 stubs, D-17 `transform` check, BP-D-20 `all` guard
- `README.md` - Scaffold with title, what-this-is paragraph, `## Roadmap` (9 phases), `## Status` note

## Decisions Made
- **Sampling-target runtime-string scope** (see key-decisions above): `fit-synthetic`, `fit-real`, `sensitivity` — the targets that write or would write posteriors — get an `EB-050` runtime line; `recover`/`decide`/`ssot`/`export`/`report` only consume already-fit output and do not.
- **Implemented thirteen stub targets, not twelve** as the plan's summary prose stated — the plan's own explicit phase-mapping list names thirteen targets by name, and 18 total minus the five real targets (`setup`, `transform`, `test`, `lint`, `all`) is arithmetically thirteen. Followed the unambiguous explicit list rather than the miscounted prose (Rule 1 — the discrepancy was internal to the plan text, not a design choice).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan prose says "twelve" stub targets; the plan's own explicit list names thirteen**
- **Found during:** Task 1, while enumerating stub targets against the plan's phase-mapping sentence
- **Issue:** The plan's action text and acceptance criteria both say "The remaining twelve targets are loud-failing stubs" / "Each of the twelve stub targets...", but the same paragraph's explicit mapping (`simulate` and `validate-sim` are Phase 2; `fit-synthetic` is Phase 4; `recover`, `ssot` and `export` are Phase 5; `intake`, `anonymize` and `validate-intake` are Phase 6; `fit-real` and `sensitivity` are Phase 7; `decide` is Phase 8; `report` is Phase 9) names 13 distinct targets. Arithmetically, 18 total targets minus the 5 explicitly real ones (`setup`, `transform`, `test`, `lint`, `all`) is also 13, confirming the list is correct and the "twelve" count in the prose is the error.
- **Fix:** Implemented all 13 targets named in the explicit list as stubs, matching SPEC-08 section 5's full 18-target closed set with no target omitted or left without a rule.
- **Files modified:** `Makefile`
- **Verification:** `grep -cE '^[a-z-]+:' Makefile` returns 18 (exactly SPEC-08's target count); every target resolves under `make -n <target>` with no "No rule to make target" error
- **Committed in:** `0d46727` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — internal prose/list count mismatch in the plan itself, resolved by following the plan's own unambiguous explicit list)
**Impact on plan:** No scope creep. The fix was required for the plan's own acceptance criteria ("all 18 targets exist and no others") to be satisfiable at all — a 12-stub implementation would leave one of the 18 SPEC-08 targets without a rule.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The `Makefile` is now the single, portable build-interface contract every later plan (CI in 01-09, `scripts/generate_season_windows.py`'s eventual `transform`-adjacent wiring in 01-06, `scripts/leak_scan.py` in 01-08) invokes through `uv run`-wrapped targets rather than ad-hoc shell commands
- `README.md`'s `## Roadmap` heading is now a real, stable anchor — every future Makefile stub or CI failure message that says "see README §Roadmap" resolves to an actual section with real phase rows
- The `define STUB`/`$(call STUB,N)` pattern and the `data/posteriors/*.parquet` guard shape in `all` are reusable templates: Phase 4 replaces the `fit-synthetic` stub body in place, Phase 5 replaces `recover`/`ssot`/`export`, and so on — no target needs to be re-declared, only its recipe body swapped
- `make setup`, `make lint`, and `make test` are real today and exercised by this plan's own verification; a fresh clone can now bootstrap and validate itself per the README's own instructions

---
*Phase: 01-repository-foundation*
*Completed: 2026-08-04*

## Self-Check: PASSED

Both created artifacts found on disk (`Makefile`, `README.md`); both task commits verified
present in git history (`0d46727`, `64e8fe5`).
