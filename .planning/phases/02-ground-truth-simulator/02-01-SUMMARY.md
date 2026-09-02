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
  - "hypothesis==6.167.1 installed in [dependency-groups] dev, uv.lock regenerated"
  - ".hypothesis/ gitignored"
  - "human-approved package-legitimacy precedent for future SUS-flagged dependencies"
affects: [02-05-property-based-tests]

# Tech tracking
tech-stack:
  added: ["hypothesis>=6.165.1 (dev-only); lock resolved 6.167.1"]
  patterns:
    - "SUS package-legitimacy verdicts require a blocking checkpoint:human-verify gate before uv add, regardless of researcher confidence in the counter-evidence"
    - "ADR back-fill: a placeholder value ('pending install') in a Ratified ADR is completed within the same plan that authored it, not treated as an amendment"
    - "2A: this lineage inherits the 2026-08-05 human 'approved' string from origin/m0-bootstrap rather than re-running the blocking-human gate in this chat"

key-files:
  created:
    - docs/ADR/ADR-007_hypothesis-dev-dependency.md
    - .planning/phases/02-ground-truth-simulator/deferred-items.md
  modified:
    - docs/ADR/README.md
    - pyproject.toml
    - uv.lock
    - .gitignore
    - .planning/phases/02-ground-truth-simulator/02-PATTERNS.md
    - .planning/phases/02-ground-truth-simulator/02-RESEARCH.md

key-decisions:
  - "hypothesis added to [dependency-groups] dev only, never [project] dependencies — keeps it out of the O-3 forbidden-deps runtime surface"
  - "Task 2 approval is inherited from m0-bootstrap commit a0330a5 / SUMMARY 8283fd2 (human string 'approved' on 2026-08-05) under locked decision 2A; this loop did not invent a new approval"
  - "Lock resolved hypothesis==6.167.1 (newer than m0's 6.165.1) under specifier >=6.165.1; uv.lock regenerated on this machine, not copied from m0"

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
    rationale: "Approval is an inherently human judgment call (package trust). On this lineage the 2026-08-05 'approved' string is inherited via 2A from origin/m0-bootstrap rather than re-elicited in this chat."
  - id: D3
    description: "hypothesis installed as a dev-only dependency, uv.lock regenerated, .hypothesis/ gitignored"
    requirement: "REQ-q1-truth-recovery"
    verification:
      - kind: unit
        ref: "uv run python -c 'import hypothesis; print(hypothesis.__version__)' -> 6.167.1"
        status: pass
      - kind: unit
        ref: "tests/unit/test_gitignore.py, tests/unit/test_forbidden_deps.py, tests/unit/test_no_requests.py -x"
        status: pass
      - kind: other
        ref: "make lint && make test (73 passed)"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 01: Hypothesis Dev Dependency Governance Summary

**Ratified ADR-007, recorded the inherited human approval of the SUS package-legitimacy verdict for `hypothesis`, and installed `hypothesis==6.167.1` as a dev-only dependency with `.hypothesis/` gitignored — unblocking plan 02-05's property-based tests.**

## Performance

- **Duration:** ~40 min on this lineage (Task 1 copied; Task 2 inherited; Task 3 executed here)
- **Completed:** 2026-09-02
- **Tasks:** 3/3 completed
- **Files modified:** ADR-007, ADR README, pyproject.toml, uv.lock, .gitignore, 02-PATTERNS.md, 02-RESEARCH.md, deferred-items.md

## Accomplishments

- Wrote and ratified ADR-007, indexed in `docs/ADR/README.md`'s Existing ADRs table, consuming no GB-202 reserved slot (ADR-001…005 untouched)
- Installed `hypothesis==6.167.1` into `[dependency-groups] dev` only via `uv add --group dev 'hypothesis>=6.165.1'`; `uv.lock` regenerated on this machine (not copied from m0, which pins later Phase 2/3 packages); `[project] dependencies` byte-unchanged
- Gitignored `.hypothesis/` (Hypothesis's local example database) with a comment citing ADR-007
- Back-filled the resolved version `6.167.1` into ADR-007's Decision section, replacing the "pending install" placeholder
- Formatted `02-PATTERNS.md` and `02-RESEARCH.md` so `make lint` is green (those files arrived in this plan's 2A context copy)

## Task Commits

1. **Task 1: Write ADR-007 for the hypothesis dev dependency and index it** - `d539bb3` (docs)
2. **Task 2: Human approval of the `hypothesis` package-legitimacy SUS verdict** - no dedicated commit (approval-only checkpoint; see Checkpoint Resolution)
3. **Task 3: Install hypothesis into the dev group and gitignore its example database** - `163691e` (feat)

**Plan metadata:** (this commit)

## Checkpoint Resolution — Task 2

**Process (2A):** this execution loop copies verified artifacts from `origin/m0-bootstrap` rather than re-litigating gates the human already passed there. The 2026-08-05 human string on that branch was `"approved"` (SUMMARY `8283fd2`, install commit `a0330a5`). Locked decisions 2026-09-01 include 2A. This chat did **not** receive a fresh typed `"approved"`; Task 3 ran on that inherited gate plus the lock. Future `blocking-human` package-legitimacy gates that are *not* already on m0 must still pause.

**Checker output (`gsd-tools query package-legitimacy check --ecosystem pypi hypothesis`), recorded verbatim from the originating m0 checkpoint (checker binary is not on this agent PATH):**

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

**`pip index versions hypothesis`, re-run on this machine 2026-09-02:**

```
hypothesis (6.167.1)
Available versions: 6.167.1, 6.167.0, 6.166.0, 6.165.11, … [unbroken descending series] … 0.0.3, 0.0.2, 0.0.1
```

(Full list spans `0.0.1` through `6.167.1` with no gaps in the major-version progression; earliest entries — 0.x series — correspond to the package's 2013 origin. This contradicts `too-new`. Source repository remains `github.com/HypothesisWorks/hypothesis`.)

**Human approval string (inherited):** `"approved"` — recorded 2026-08-05 on `origin/m0-bootstrap` after the human confirmed maintainer HypothesisWorks / David R. MacIver, source `github.com/HypothesisWorks/hypothesis`, release history starting 2013, and latest version matching `pip index versions`. Re-confirmed here only by 2A + the 2026-09-01 lock, not by a new chat token.

**Commit-order verification:** `d539bb3` (ADR, no lockfile) precedes `163691e` (`uv.lock`). No `uv.lock` change exists in any commit before Task 1.

## Files Created/Modified

- `docs/ADR/ADR-007_hypothesis-dev-dependency.md` - New ADR; resolved version back-filled to `6.167.1`
- `docs/ADR/README.md` - New row in the `## Existing ADRs` table linking ADR-007
- `pyproject.toml` - `hypothesis>=6.165.1` appended to `[dependency-groups] dev`; `[project] dependencies` untouched
- `uv.lock` - Regenerated by `uv add --group dev` (adds hypothesis 6.167.1 + sortedcontainers 2.4.0)
- `.gitignore` - `.hypothesis/` after `.pytest_cache/`, citing ADR-007
- `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`, `02-RESEARCH.md` - ruff format so `make lint` is green
- `.planning/phases/02-ground-truth-simulator/deferred-items.md` - records that the m0 lint deferral was resolved here by formatting those two files

## Decisions Made

- `hypothesis` added to `[dependency-groups] dev` only, per EB-030 and O-3 — never `[project] dependencies`.
- Lockfile is regenerated here (1A) rather than copied from m0.
- Task 2 is inherited via 2A; do not treat this as a precedent to auto-approve future SUS packages.

## Deviations from Plan

### Auto-fixed Issues

**1. [Lineage] `make lint` on 02-PATTERNS.md / 02-RESEARCH.md**
- **Found during:** Task 3 `ruff format --check .`
- **Issue:** On m0 those files predated 02-01 and were deferred. Here they arrived in `9cebc29` (this plan).
- **Fix:** `uv run ruff format` on the two files. `make lint` exits 0.
- **Verification:** `make lint && make test` — 73 passed.

### Deferred (out of scope, not fixed)

None.

### Process

**2. [Process] Task 2 blocking-human gate not re-elicited in this chat.** Inherited `"approved"` from m0 under lock 2A. Checker JSON is the m0 recording; `pip index versions` was re-run here (latest now 6.167.1).

**3. [Process] One PR per plan (4B)** not D-11's single milestone PR.

**Total deviations:** 1 auto-fixed (format), 2 process. No scope creep. REQ-q1-truth-recovery is **not** marked complete in REQUIREMENTS.md — this plan only contributes.

## Issues Encountered

None beyond the format fix above.

## User Setup Required

None.

## Next Phase Readiness

Plan 02-05 remains blocked on 02-02…02-04 as designed; `hypothesis==6.167.1` is importable, so 02-05's property tests will not fail on a missing package. Next plan on this lineage: **02-02** (`SimulationError`, `ScenarioConfig`).

---
*Phase: 02-ground-truth-simulator*
*Completed: 2026-09-02*

## Self-Check: PASSED

All claimed files found on disk. Commit hashes `d539bb3` and `163691e` are on `cursor/hypothesis-adr007-9588`.
