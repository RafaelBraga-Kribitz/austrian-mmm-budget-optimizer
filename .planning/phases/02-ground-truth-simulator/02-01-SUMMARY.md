---
phase: 02-ground-truth-simulator
plan: 01
subsystem: testing
tags: [hypothesis, property-based-testing, uv, dependency-governance, adr]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "pyproject.toml [dependency-groups] dev list, docs/ADR/ governance process (EB-030), .gitignore EB-081 structure"
provides:
  - "ADR-007 ratifying hypothesis as a dev-only test dependency"
  - "hypothesis==6.165.1 installed in [dependency-groups] dev, uv.lock regenerated"
  - ".hypothesis/ gitignored"
  - "human-approved package-legitimacy precedent for future SUS-flagged dependencies"
affects: [02-05-property-based-tests]

# Tech tracking
tech-stack:
  added: ["hypothesis>=6.165.1 (dev-only)"]
  patterns:
    - "SUS package-legitimacy verdicts require a blocking checkpoint:human-verify gate before uv add, regardless of researcher confidence in the counter-evidence"
    - "ADR back-fill: a placeholder value ('pending install') in a Ratified ADR is completed within the same plan that authored it, not treated as an amendment"

key-files:
  created:
    - docs/ADR/ADR-007_hypothesis-dev-dependency.md
    - .planning/phases/02-ground-truth-simulator/deferred-items.md
  modified:
    - docs/ADR/README.md
    - pyproject.toml
    - uv.lock
    - .gitignore

key-decisions:
  - "hypothesis added to [dependency-groups] dev only, never [project] dependencies — keeps it out of the O-3 forbidden-deps runtime surface"
  - "Human explicitly approved the SUS legitimacy verdict as a checker data artifact after independently confirming maintainer identity, source repo, and release history on pypi.org"

patterns-established:
  - "Pattern: package-legitimacy SUS verdicts are surfaced verbatim (verdict + reasons) in both the ADR and the plan SUMMARY, with counter-evidence recorded alongside — never silently overridden"

requirements-completed: [REQ-q1-truth-recovery]

coverage:
  - id: D1
    description: "ADR-007 ratified and indexed in docs/ADR/README.md, no GB-202 reserved slot consumed"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "tests/unit/test_repo_layout.py, tests/unit/test_line_endings.py -x"
        status: pass
    human_judgment: false
  - id: D2
    description: "Human approved the hypothesis SUS package-legitimacy verdict before install"
    requirement: "REQ-q1-truth-recovery"
    verification: []
    human_judgment: true
    rationale: "Approval is an inherently human judgment call (package trust) — the checkpoint's own protocol forbids auto-approval regardless of researcher confidence."
  - id: D3
    description: "hypothesis installed as a dev-only dependency, uv.lock regenerated, .hypothesis/ gitignored"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "uv run python -c 'import hypothesis; print(hypothesis.__version__)'"
        status: pass
      - kind: unit
        ref: "tests/unit/test_gitignore.py, tests/unit/test_forbidden_deps.py, tests/unit/test_no_requests.py -x"
        status: pass
      - kind: other
        ref: "make test (full suite, 73 passed)"
        status: pass
    human_judgment: false

duration: 33min
completed: 2026-08-05
status: complete
---

# Phase 02 Plan 01: Hypothesis Dev Dependency Governance Summary

**Ratified ADR-007, human-approved the SUS package-legitimacy verdict for `hypothesis`, and installed `hypothesis==6.165.1` as a dev-only dependency with `.hypothesis/` gitignored — unblocking plan 02-05's property-based tests.**

## Performance

- **Duration:** ~33 min across two sessions (session 1: Task 1 + checkpoint reached; session 2/this session: Task 2 approval recorded + Task 3 execution + SUMMARY)
- **Completed:** 2026-08-05T09:23:41Z
- **Tasks:** 3/3 completed
- **Files modified:** 6 (docs/ADR/ADR-007_hypothesis-dev-dependency.md, docs/ADR/README.md, pyproject.toml, uv.lock, .gitignore, plus deferred-items.md created)

## Accomplishments

- Wrote and ratified ADR-007, indexed in `docs/ADR/README.md`'s Existing ADRs table, consuming no GB-202 reserved slot (ADR-001…005 untouched)
- Surfaced the automated package-legitimacy checker's `SUS` verdict for `hypothesis` (reasons: `too-new`, `unknown-downloads`, `no-repository`) to a human alongside counter-evidence, and received explicit approval
- Installed `hypothesis==6.165.1` into `[dependency-groups] dev` only via `uv add --group dev hypothesis`; `uv.lock` regenerated; `[project] dependencies` byte-unchanged
- Gitignored `.hypothesis/` (Hypothesis's local example database) with a comment citing ADR-007
- Back-filled the resolved version `6.165.1` into ADR-007's Decision section, replacing the "pending install" placeholder

## Task Commits

1. **Task 1: Write ADR-007 for the hypothesis dev dependency and index it** - `0e9c634` (docs)
2. **Task 2: Human approval of the `hypothesis` package-legitimacy SUS verdict** - no dedicated commit (approval-only checkpoint gate; see "Checkpoint Resolution" below)
3. **Task 3: Install hypothesis into the dev group and gitignore its example database** - `a0330a5` (feat)

**Plan metadata:** (this commit, see below)

## Checkpoint Resolution — Task 2

**Checker output (`gsd-tools query package-legitimacy check --ecosystem pypi hypothesis`), re-run verbatim at this checkpoint:**

```json
[
  {
    "name": "hypothesis",
    "verdict": "SUS",
    "signals": {
      "exists": true,
      "publishedAt": "2026-08-04T21:00:47.014918Z",
      "weeklyDownloads": null,
      "repoUrl": null,
      "deprecated": false,
      "postinstall": null,
      "ecosystem": "pypi"
    },
    "reasons": ["too-new", "unknown-downloads", "no-repository"]
  }
]
```

**`pip index versions hypothesis`, re-run verbatim at this checkpoint:**

```
hypothesis (6.165.1)
Available versions: 6.165.1, 6.165.0, 6.164.0, ... [unbroken descending series] ... 0.0.3, 0.0.2, 0.0.1
```
(Full list spans 0.0.1 through 6.165.1 with no gaps in the major-version progression; earliest entries — 0.x series — correspond to the package's 2013 origin per the pypi.org release history the human independently confirmed.)

**Human approval string:** `"approved"` — the user visited `https://pypi.org/project/hypothesis/` and confirmed all four facts required by the checkpoint's `<how-to-verify>`: maintainer is HypothesisWorks/David R. MacIver; source links to `github.com/HypothesisWorks/hypothesis`; release history starts in 2013 (not the 90-day window the checker flagged); latest version `6.165.1` matches the `pip index versions` output above.

**Commit-order verification:** confirmed via `git log --oneline -5` at the start of this session that no `uv add`/`uv sync` had run and `uv.lock` was unmodified prior to this approval being recorded — Task 3's `uv.lock`-touching commit (`a0330a5`) is strictly after Task 1's ADR commit (`0e9c634`) and after this approval.

## Files Created/Modified

- `docs/ADR/ADR-007_hypothesis-dev-dependency.md` - New ADR: Context/Decision/Consequences/Spec deviations for the hypothesis dev dependency, verdict + counter-evidence recorded verbatim, resolved version back-filled to `6.165.1`
- `docs/ADR/README.md` - New row in the `## Existing ADRs` table linking ADR-007
- `pyproject.toml` - `hypothesis>=6.165.1` appended to `[dependency-groups] dev`; `[project] dependencies` untouched
- `uv.lock` - Regenerated by `uv add --group dev hypothesis` (adds hypothesis + sortedcontainers)
- `.gitignore` - `.hypothesis/` added to the `# --- Environment / tooling ---` section, immediately after `.pytest_cache/`, citing ADR-007
- `.planning/phases/02-ground-truth-simulator/deferred-items.md` - New file logging an out-of-scope, pre-existing `ruff format --check .` failure (see Deviations below)

## Decisions Made

- `hypothesis` added to `[dependency-groups] dev` only, per EB-030 and O-3 — never `[project] dependencies`, so the runtime forbidden-deps surface (`tests/unit/test_forbidden_deps.py`) is unaffected.
- The SUS verdict was treated as a checker data artifact only after the blocking human checkpoint explicitly confirmed it — the researcher's confidence alone was never sufficient per this project's own protocol.

## Deviations from Plan

### Auto-fixed Issues

None — Tasks 1 and 3 executed as written; Task 2 resolved via the recorded human approval, matching the plan's own resume-signal contract.

### Auto-fixed Issues (state-update correction)

**1. [Rule 1 - Bug] `requirements.mark-complete` prematurely marked REQ-q1-truth-recovery fully complete**
- **Found during:** State updates step (after Task 3)
- **Issue:** `gsd_run query requirements.mark-complete REQ-q1-truth-recovery` checked the requirement's box and set its traceability-table status to "Complete" in `.planning/REQUIREMENTS.md`. REQ-q1-truth-recovery is explicitly Phase-5-owned ("accepted when all SPEC-05 §3 gates are green per scenario"), with Phases 2/3/4 listed only as "Also touches." This plan (02-01) is dependency governance only — it does not satisfy the requirement's acceptance criterion.
- **Fix:** Reverted both edits in `.planning/REQUIREMENTS.md` (checkbox back to `[ ]`, traceability status back to `Pending`) so the requirement remains open until Phase 5 actually satisfies it. `requirements-completed: [REQ-q1-truth-recovery]` remains in this SUMMARY's frontmatter per the template's instruction to copy the plan's own `requirements:` field verbatim — that field records which requirement this plan *contributes to*, not that this plan alone completes it.
- **Files modified:** `.planning/REQUIREMENTS.md` (reverted to pre-mark-complete state — no net diff)
- **Verification:** `git diff .planning/REQUIREMENTS.md` is empty after the revert.

### Deferred (out of scope, not fixed)

**1. [Scope boundary] `make lint` fails via `ruff format --check .` on two pre-existing, unrelated markdown files**
- **Found during:** Task 3 verification (`make lint`)
- **Issue:** `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md` and `02-RESEARCH.md` (both authored during Phase 2 planning, before this plan ran, and not in this plan's `files_modified`) are reported as "would be reformatted" by `ruff format --check .` — reformatting affects blank-line spacing around embedded Python code fences.
- **Confirmed pre-existing:** `git stash` (removing all uncommitted changes from this plan) reproduces the identical two-file failure, proving it predates this plan's execution and is unrelated to the hypothesis install.
- **Scope decision:** Not fixed, per the executor's SCOPE BOUNDARY rule (only auto-fix issues directly caused by the current task's changes in files the task touches). Logged to `.planning/phases/02-ground-truth-simulator/deferred-items.md` instead.
- **Isolated verification:** `uv run ruff check .` → "All checks passed!"; `uv run mypy` → "Success: no issues found in 11 source files"; `make test` → 73 passed. Only the markdown-formatting check on those two unrelated files fails; Task 3's own `<verify>` command (`import hypothesis` + the three targeted pytest files) is unaffected and green.

---

**Total deviations:** 1 deferred (out of scope, not auto-fixed).
**Impact on plan:** None — the deferred item is unrelated to this plan's deliverables and does not block plan 02-05.

## Issues Encountered

None beyond the deferred `ruff format` item above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Plan 02-05 (property-based tests for `adstock_recursive` and `hill`) is unblocked: `hypothesis==6.165.1` is importable, dev-group-scoped, and its example database is gitignored. `make test` and the targeted `tests/unit/test_gitignore.py`, `tests/unit/test_forbidden_deps.py`, and `tests/unit/test_no_requests.py` are all green. The one deferred item (pre-existing markdown formatting drift in two Phase 2 planning docs) does not block any downstream plan; a future plan touching those files, or a dedicated formatting pass, should run `uv run ruff format .` on them.

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-08-05*

## Self-Check: PASSED

All claimed files found on disk (`docs/ADR/ADR-007_hypothesis-dev-dependency.md`, `.gitignore`,
`pyproject.toml`, `uv.lock`, `02-01-SUMMARY.md`, `deferred-items.md`). Both claimed commit
hashes (`0e9c634`, `a0330a5`) found in `git log --oneline --all`.
