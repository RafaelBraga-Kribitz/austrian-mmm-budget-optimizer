---
phase: 01-repository-foundation
plan: 01
subsystem: infra
tags: [git, gitattributes, adr, governance, branch-topology]

# Dependency graph
requires: []
provides:
  - "docs/BUILD_LOG.md — append-only build evidence log, seeded with the M0 D-29 audit"
  - "Committed .gitattributes pinning LF for all tracked text types (D-22)"
  - "origin/main pushed current; m0-bootstrap branch cut, pushed, and checked out (D-11, D-13)"
  - "docs/ADR/TEMPLATE.md and docs/ADR/README.md — usable ADR mechanism with the five GB-202 reserved slots"
affects: [01-02, 01-03, 01-04, 01-05, 01-06, 01-07, 01-08, 01-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Append-only document discipline (EB-082 applied at document level) — BUILD_LOG.md and ADR/README.md both state a correction is a new dated entry, never an in-place edit"
    - "Committed .gitattributes over local core.autocrlf for line-ending reproducibility (D-22)"
    - "Milestone branch, phase-commits topology (D-11) — m0-bootstrap now the working branch for the rest of Phase 1"

key-files:
  created:
    - docs/BUILD_LOG.md
    - .gitattributes
    - docs/ADR/TEMPLATE.md
    - docs/ADR/README.md
  modified: []

key-decisions:
  - "Audited T-001/T-003/T-012 against running probes rather than copying the D-29 known-state table — confirmed exact same verdicts, with one clarification: T-003 AC-2's exports/foo.csv untracked-not-ignored result is correct per the W5 ingest resolution (exports committed by design), not a gitignore gap"
  - "git add --renormalize . implies -u (tracked files only); .planning/STATE.md's pre-existing out-of-scope content edit was left uncommitted in the .gitattributes commit and deferred to this plan's final state-tracking commit"

requirements-completed: [REQ-milestones, REQ-dl8-quality]

coverage:
  - id: D1
    description: "docs/BUILD_LOG.md exists with the append-only header (correction rule, insertion-order tie-break, strictly-greater-than 2x tripwire) and an M0 audit table covering all 9 T-001/T-003/T-012 acceptance criteria, every FAIL routed to a named closing task"
    requirement: "REQ-milestones"
    verification:
      - kind: other
        ref: "grep -q 'append-only' docs/BUILD_LOG.md && grep -qE '^## M0' docs/BUILD_LOG.md && [ \"$(grep -cE '^\\| *T-0(01|03|12) AC-' docs/BUILD_LOG.md)\" -ge 9 ]"
        status: pass
    human_judgment: false
  - id: D2
    description: ".gitattributes committed at repo root, pinning LF for text types and binary treatment for parquet/png/pbix/nc/duckdb/etc; already-tracked files renormalized by a new commit (not history rewriting)"
    requirement: "REQ-milestones"
    verification:
      - kind: other
        ref: "git check-attr text eol -- docs/BUILD_LOG.md (text: set, eol: lf); git check-attr -a -- data/posteriors/example.parquet (text: unset)"
        status: pass
    human_judgment: false
  - id: D3
    description: "origin/main is current (0 commits behind local main) and m0-bootstrap branch exists, is pushed, and is checked out; root commit 1851f39 unchanged"
    requirement: "REQ-milestones"
    verification:
      - kind: other
        ref: "git rev-list --count origin/main..main == 0; git rev-parse --verify m0-bootstrap; git rev-list --max-parents=0 HEAD == 1851f39"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/ADR/TEMPLATE.md has exactly the four GB-201 sections at TEMPLATE.md (not ADR-000_template.md); docs/ADR/README.md lists ADR-000 as Ratified and all five GB-202 reserved slots with their topics"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "grep -cE '^## (Context|Decision|Consequences|Spec deviations)' docs/ADR/TEMPLATE.md == 4; grep -o -E 'ADR-00[1-5]' docs/ADR/README.md | sort -u | wc -l == 5; grep -qi ratified docs/ADR/README.md"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 1: Repository Foundation Bootstrap Summary

**D-29 audit opens the append-only BUILD_LOG, a committed .gitattributes pins LF repo-wide, origin/main is pushed and m0-bootstrap is cut, and the ADR mechanism (TEMPLATE.md + README.md with all five GB-202 slots) is usable.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-04T18:12:00Z (approx.)
- **Completed:** 2026-08-04T18:19:58Z
- **Tasks:** 3
- **Files modified:** 4 created (docs/BUILD_LOG.md, .gitattributes, docs/ADR/TEMPLATE.md, docs/ADR/README.md)

## Accomplishments
- Audited every pre-existing Phase 1 artifact (T-001, T-003, T-012) against its WBS acceptance criteria by running the actual probes (git log --stat, git check-attr, git config, ls, the .gitignore touch-probe, gh api) rather than copying the D-29 known-state table; wrote the result as a 9-row markdown table in the new `docs/BUILD_LOG.md`, with every FAIL routed to the plan and task that closes it
- Pinned LF for all tracked text types with a committed `.gitattributes` (D-22), renormalized already-tracked files with `git add --renormalize .`, and confirmed both a text path (`docs/BUILD_LOG.md` → `eol: lf`) and a binary path (`data/posteriors/example.parquet` → `text: unset`) resolve as intended
- Established the branch topology in D-13's order: pushed `origin/main` (bringing it from 4 commits behind to current), then cut and pushed `m0-bootstrap` — every subsequent Phase 1 commit lands there per D-11
- Wrote `docs/ADR/TEMPLATE.md` with exactly the four GB-201 sections at the `TEMPLATE.md` path (not `ADR-000_template.md`, since ADR-000 is already the ratified precedence ADR) and `docs/ADR/README.md` as the index, listing ADR-000 as Ratified and all five GB-202 reserved slots (ADR-001…005) with their topics and triggers

## Task Commits

Each task was committed atomically:

1. **Task 1: Audit pre-existing artifacts and create the append-only build log** - `984cdf3` (docs)
2. **Task 2: Pin line endings with .gitattributes and establish the branch topology** - `9318dd1` (chore)
3. **Task 3: Write the ADR template and the ADR index with the five reserved slots** - `37ad68b` (docs)

**Plan metadata:** committed separately after this summary is written.

_All three commits land on `main` (Tasks 1–2, before the branch cut) and `m0-bootstrap` (Task 3, after the branch cut) per D-11/D-13; `git merge-base --is-ancestor 1851f39 HEAD` confirms `m0-bootstrap` still descends from the doc-only baseline._

## Files Created/Modified
- `docs/BUILD_LOG.md` - Append-only build log; header states the four required rules, M0 heading with the 9-row D-29 audit table
- `.gitattributes` - Repo-root LF pin (catch-all + explicit text-type rules) and binary/`-diff` rules for parquet/png/jpg/pbix/nc/duckdb/xlsx/pdf
- `docs/ADR/TEMPLATE.md` - Four-section GB-201 ADR template with a header comment explaining the TEMPLATE.md filename decision (D-09)
- `docs/ADR/README.md` - ADR index: naming convention, D-06 standing bar, existing-ADR table (ADR-000 Ratified), five GB-202 reserved slots, standard non-slot triggers

## Decisions Made
- Confirmed the D-29 known-state table's verdicts by re-running every probe rather than trusting the prior discussion's memory; all matched except one clarification worth recording: the `.gitignore` ignore-probe shows `exports/foo.csv` as untracked-not-ignored, which is *correct* under the W5 ingest resolution (exports committed by design) even though it looks like a gap against the original T-003 WBS wording
- `git add --renormalize .` implies `-u` and only re-adds already-tracked files; it did not touch the two pre-existing untracked/modified out-of-scope artifacts (`.planning/config.json`, `.planning/research/`, `.planning/STATE.md`'s content edit), which were left alone and are deferred to this plan's final state-tracking commit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 2's binary-attribute verify sub-check has an unmatchable grep pattern**
- **Found during:** Task 2 verification
- **Issue:** The plan's automated verify line greps `git check-attr -a -- data/posteriors/example.parquet` for the literal substring `-text`. `check-attr -a` output format is `<path>: <attr>: <value>` (e.g. `text: unset`), which never contains the hyphenated `-text` gitattributes-file syntax. The grep therefore always returns no-match regardless of whether the binary attribute is correctly applied.
- **Fix:** Verified the underlying acceptance criterion directly — `git check-attr -a -- data/posteriors/example.parquet` reports `binary: set`, `diff: unset`, `merge: unset`, `text: unset`, which is the correct binary treatment (the `binary` macro in `.gitattributes` is `-diff -merge -text`). No file change was needed; this is a verify-script wording issue, not a functional gap.
- **Files modified:** none (verification-only)
- **Verification:** Manual `git check-attr -a` inspection confirms `text: unset` for the parquet path
- **Committed in:** n/a (no code change; documented here for traceability)

**2. [Rule 3 - Blocking] Task 1's full-tree `git status --porcelain` clean-check cannot pass due to pre-existing out-of-scope artifacts**
- **Found during:** Task 1 verification
- **Issue:** The plan's automated verify requires `[ -z "$(git status --porcelain)" ]` after Task 1. At the start of this plan the working tree already carried `.planning/STATE.md` (modified, from an earlier orchestration step) and two untracked paths (`.planning/config.json`, `.planning/research/`) — none of which are in this plan's `files_modified` list and none of which were touched by the T-003 AC-2 ignore probe.
- **Fix:** Ran the ignore probe (`touch data/warehouse/x.duckdb exports/foo.csv && git status --porcelain`) and confirmed the probe itself left no residue (both files deleted, neither staged) — satisfying the actual intent of the acceptance criterion ("the probe files were deleted and never staged"). Per the scope-boundary rule, the pre-existing out-of-scope items were left untouched rather than force-committed or deleted to satisfy the literal full-tree-clean check.
- **Files modified:** none
- **Verification:** `git status --porcelain` shows only the three pre-existing, out-of-scope items after Task 1's commit — no new residue from the probe
- **Committed in:** n/a (verification-only; the pre-existing items are out of this plan's scope)

---

**Total deviations:** 2 auto-fixed/documented (1 verify-script wording bug, 1 scope-boundary judgment call). Neither required a code or content change.
**Impact on plan:** No scope creep. Both deviations are verification-interpretation issues, not defects in the delivered artifacts.

## Issues Encountered
None beyond the two deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `m0-bootstrap` is the active branch; plans 01-02 through 01-09 commit onto it per D-11
- `.gitattributes` is in place before any further text file is committed, so Phase 2's SIM-070 byte-identical CSV gate inherits a deterministic line-ending history
- The ADR mechanism is ready for ADR-006 (plan 01-03) and for the five reserved GB-202 slots as their triggering decisions arrive
- `docs/BUILD_LOG.md` is open for every subsequent plan's evidence entries in this milestone

---
*Phase: 01-repository-foundation*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 4 created artifacts found on disk; all 3 task commits verified present in git history (984cdf3, 9318dd1, 37ad68b).
