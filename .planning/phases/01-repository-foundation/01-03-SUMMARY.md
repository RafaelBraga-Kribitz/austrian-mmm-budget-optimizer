---
phase: 01-repository-foundation
plan: 03
subsystem: governance
tags: [module-contracts, risk-register, adr, pull-request-template, governance]

# Dependency graph
requires:
  - phase: 01-01
    provides: "docs/ADR/TEMPLATE.md + docs/ADR/README.md with the ADR-006 slot reserved, m0-bootstrap branch checked out"
  - phase: 01-02
    provides: "src/ambo/common/ subpackage (config.py, errors.py, logging.py not yet written — contracts written ahead of code per grow-as-you-go, D-03)"
provides:
  - "docs/MODULE_CONTRACTS.md — tracked contract of record for src/ambo/, three entries (config.py, errors.py, logging.py), supersedes 03_MODULES.md"
  - "docs/RISK_REGISTER.md — tracked, reviewable risk register: Charter R-1..R-9 verbatim plus build findings R-10..R-13, complete triads"
  - "docs/ADR/ADR-006_module-contracts-layout-and-citation-policy.md — ratified, closes the D-04 unpublished-citation violation"
  - ".github/pull_request_template.md — the six D-24 judgment items, zero overlap with the future repo-layout test"
affects: [01-04, 01-05, 01-06, 01-07, 01-08, 01-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Contract-of-record document paired with a future machine guard (test_repo_layout.py, plan 01-07) rather than a checklist — D-02/D-23 applied"
    - "Frozen-blueprint signposting: a local-only superseded blockquote banner on the gitignored 03_MODULES.md/12_RISK_REGISTER.md working copies, confirmed to stay untracked via git status — repeats the pattern this plan's own predecessor set"
    - "Risk-ID reservation: Charter risks R-1..R-9 fixed forever; every later finding starts at R-10, so an appended finding can never shadow a Charter risk by ID collision"

key-files:
  created:
    - docs/MODULE_CONTRACTS.md
    - docs/RISK_REGISTER.md
    - docs/ADR/ADR-006_module-contracts-layout-and-citation-policy.md
    - .github/pull_request_template.md
  modified:
    - docs/ADR/README.md
    - docs/EXECUTION_BLUEPRINT/03_MODULES.md (local-only, untracked/gitignored)
    - docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md (local-only, untracked/gitignored)

key-decisions:
  - "R-4's and R-8's Fallback cells have no direct source in 12_RISK_REGISTER.md's per-milestone rows (RK-M6-2 and RK-M7-3 both list Mitigation and Detection but no Fallback) — authored fallback text from the surrounding SPEC/DC context (DC-704 audit re-check; ADR-gated scope additions) rather than leaving the cell blank, per D-08's 'no blank triad cell' rule."
  - "R-9 (promo calendar reconstruction) has no entry anywhere in 12_RISK_REGISTER.md's per-milestone tables at all — authored its full Fallback/Detection triad from Charter R-9's own mitigation text plus SPEC-05 section 5.4's VR-504 no-promo sensitivity fit, rather than treating the absence as a gap to leave open."
  - "Milestone-to-phase mapping for each risk's Owner phase column resolved via ROADMAP.md's explicit M0-M7 to Phase 1-9 table, not guessed: R-1/R-6 to Phase 6 (M4), R-2/R-9 to Phase 7 (M5), R-3/R-5 to Phase 5 (M3), R-4 to Phase 8 (M6), R-7 to Phase 4 (M2), R-8 and R-12 marked 'standing' since their enforcement (forbidden-deps test, uv.lock diff review) is continuous rather than owned by one milestone."
  - "docs/ADR/README.md updated beyond the plan's files_modified list to move ADR-006 from its 'in flight' placeholder into the ratified ADR table (Rule 2) — the README's own prior text explicitly promised this step ('It will move into the table above once ratified'), and leaving it stale after ratification would itself be a published-document inconsistency of the kind D-04 exists to prevent."

requirements-completed: [REQ-scope-in, REQ-risk-register, REQ-milestones]

coverage:
  - id: D1
    description: "docs/MODULE_CONTRACTS.md tracked, three level-3 headings for the three Phase-1-shipped modules, all five section labels present per entry, header names 03_MODULES.md superseded and states the contract-first same-PR rule"
    requirement: "REQ-scope-in"
    verification:
      - kind: other
        ref: "git ls-files docs/MODULE_CONTRACTS.md; grep -cE '^### src/ambo/' == 3; grep -c '**Public API**'/'**Invariants**'/'**Testing**' each == 3; grep -q superseded; git status --porcelain docs/EXECUTION_BLUEPRINT/ empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/RISK_REGISTER.md tracked, all nine Charter R-1..R-9 rows present exactly once plus four build findings at R-10+, no empty triad cells, Review log section present"
    requirement: "REQ-risk-register"
    verification:
      - kind: other
        ref: "git ls-files docs/RISK_REGISTER.md; 13 total R-rows; 9 unique Charter IDs R-1..R-9; 0 empty-cell rows; '## Review log' present; blueprint dir clean"
        status: pass
    human_judgment: false
  - id: D3
    description: "ADR-006 ratified with all four TEMPLATE.md sections, four numbered D-05 decisions, names MODULE_CONTRACTS.md/.gitattributes/uv.lock/.planning//.github//Phase 4/Phase 9, Spec deviations table with >=4 REQ-tagged rows"
    requirement: "REQ-milestones"
    verification:
      - kind: other
        ref: "4 section headings present; all seven named strings found; REQ- count = 6 (>=4)"
        status: pass
    human_judgment: false
  - id: D4
    description: ".github/pull_request_template.md carries exactly six judgment checkboxes with no layout/forbidden-deps/line-ending item duplicated from the future repo-layout test"
    requirement: "REQ-scope-in"
    verification:
      - kind: other
        ref: "grep -c '^- \\[ \\]' == 6; grep for layout|forbidden-deps|line-ending as checkbox items == 0; git ls-files returns the path"
        status: pass
    human_judgment: false

duration: ~13min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 3: Governance Documents (MODULE_CONTRACTS, RISK_REGISTER, ADR-006, PR template) Summary

**Four tracked governance documents close the D-04 unpublished-citation violation: MODULE_CONTRACTS.md and RISK_REGISTER.md promote the module-contract and risk-register content out of the gitignored blueprint, ADR-006 ratifies all four D-05 decisions in one document, and the PR template gets the six judgment items the future layout test cannot check.**

## Performance

- **Duration:** ~13 min (commit-to-commit; context-reading against the full canonical-reference
  set — SPEC-08, SPEC-09, PROJECT_CHARTER, ADR-000/TEMPLATE, both frozen blueprint files,
  01-CONTEXT.md, 01-RESEARCH.md, ROADMAP.md — preceded the edits)
- **Started:** 2026-08-04T20:36:12+02:00 (approx., prior plan's close)
- **Completed:** 2026-08-04T20:45:34+02:00
- **Tasks:** 3
- **Files modified:** 4 created, 1 modified (tracked); 2 local-only signpost edits (untracked/gitignored)

## Accomplishments
- `docs/MODULE_CONTRACTS.md` written as the tracked contract of record for `src/ambo/`: header
  states the supersession of `03_MODULES.md`, the same-PR contract-first rule, and the
  set-comparison (not order-sensitive) guard-test contract; three entries
  (`common/config.py`, `common/errors.py`, `common/logging.py`) each carry all five required
  section labels (`Purpose`, `Public API`, `Invariants`, `Failure modes`, `Testing`); a
  Dependency-directions section reproduces the four FORBIDDEN edges plan 01-07 tests against
- `docs/RISK_REGISTER.md` seeded with all nine Charter R-1..R-9 risks verbatim plus four Phase 1
  build findings at R-10..R-13 (no-`g++`, M0 leak-scan pattern-set scope, the load-bearing
  `pymc<6` bound, Chocolatey `make` provenance) — every row carries a complete
  Mitigation/Fallback/Detection triad with no blank cells, and a Review log section records the
  Phase 1 entry review
- `ADR-006` ratified: all four D-05 decisions in one document (SPEC-08 §2's contract-first
  repoint, the four layout additions, the standing no-unpublished-citation rule with its two
  named deferrals, and the pre-EB-080 commit-history note), following `TEMPLATE.md`'s exact
  four-section shape with a populated Spec deviations table
- `.github/pull_request_template.md` carries the six D-24 judgment items (BUILD_LOG entry,
  evidence attached, effort budget, per-edit ADRs, SSOT regeneration, quality-standards review)
  with a header explaining why the machine-checked half is deliberately absent

## Task Commits

Each task was committed atomically:

1. **Task 1: Write docs/MODULE_CONTRACTS.md and freeze 03_MODULES.md** - `3a2c895` (docs)
2. **Task 2: Seed docs/RISK_REGISTER.md with the Charter risks and the build findings** - `6140502` (docs)
3. **Task 3: Write ADR-006 and the pull-request template** - `e62371b` (docs)

**Plan metadata:** committed separately after this summary is written.

## Files Created/Modified
- `docs/MODULE_CONTRACTS.md` - Contract of record: header + three entries + dependency-direction table
- `docs/RISK_REGISTER.md` - Tracked register: header + 13-row table (R-1..R-13) + Review log
- `docs/ADR/ADR-006_module-contracts-layout-and-citation-policy.md` - Ratified ADR, four D-05 decisions, Spec deviations table
- `.github/pull_request_template.md` - Six judgment checkboxes, header explaining the machine-checked omissions
- `docs/ADR/README.md` - ADR-006 moved from "in flight" into the ratified ADR index table
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` - Local-only superseded banner (untracked/gitignored, confirmed by `git status`)
- `docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md` - Local-only superseded banner (untracked/gitignored, confirmed by `git status`)

## Decisions Made
- Where `12_RISK_REGISTER.md`'s per-milestone rows omitted a Fallback cell for a Charter risk
  (R-4, R-8) or had no entry at all (R-9), authored the missing triad content from the
  surrounding SPEC/Charter context rather than leaving a blank cell — D-08 forbids blank
  Mitigation/Fallback/Detection cells and gives no exception for content the source register
  happened not to state.
- Owner-phase values resolved via ROADMAP.md's explicit M0-M7 → Phase 1-9 mapping table (not
  guessed): full mapping recorded in `key-decisions` above.
- Updated `docs/ADR/README.md` beyond the plan's stated `files_modified` list, moving ADR-006
  into the ratified table — the README's own prior text promised this exact step once ratified,
  and Rule 2 (auto-add missing critical functionality) covers closing a self-declared TODO in a
  tracked governance document during the same plan that ratifies the ADR it refers to.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1's entry section labels initially used level-2 headings and periods inside the bold markers, breaking the automated verify pattern**
- **Found during:** Task 1 self-verification, before commit
- **Issue:** The first draft of `docs/MODULE_CONTRACTS.md` used `## src/ambo/...` (level-2) for
  the three module headings instead of the plan-specified level-3 (`### src/ambo/...`), and used
  `**Public API.**` / `**Invariants.**` / `**Testing.**` (period inside the bold markers) for
  the entry section labels. The plan's automated verify greps for `^### src/ambo/` and the exact
  literal `**Public API**` (no period), so both mismatches would have failed CI's future
  `test_repo_layout.py`-adjacent verification even though the content was substantively correct.
- **Fix:** Changed all three module headings to level-3, and removed the period from inside the
  bold markers on `Purpose`, `Public API`, `Invariants`, `Failure modes`, `Testing` across all
  three entries. Also reworded the entry-format description list (which used the same bold
  pattern to describe the format itself) to backticks, so the description text no longer
  double-counts against the per-entry label greps.
- **Files modified:** `docs/MODULE_CONTRACTS.md`
- **Verification:** Re-ran the plan's exact automated verify line; all five sub-checks pass
  (`### src/ambo/` count = 3, `**Public API**`/`**Invariants**`/`**Testing**` counts = 3 each,
  `superseded` found, blueprint dir clean)
- **Committed in:** `3a2c895` (Task 1 commit; fixed before commit, not a follow-up)

---

**Total deviations:** 1 auto-fixed (Rule 1 - verify-pattern-breaking formatting bug caught before commit)
**Impact on plan:** No scope creep. The fix was required for the plan's own stated acceptance
criteria to be satisfiable at all, and was caught and corrected before any commit landed.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `docs/MODULE_CONTRACTS.md` now has entries ready for `common/config.py`, `common/errors.py`,
  and `common/logging.py` — plan 01-04 writes the modules these entries already describe as
  contracts (grow-as-you-go, D-03); the same-PR contract-first rule is now a document a reader
  can open, not a dangling citation
- `docs/RISK_REGISTER.md` is the tracked register every subsequent phase's entry-review appends
  to; the Review log section is ready for the Phase 2 entry line
- ADR-006 closes SPEC-08 §2's citation gap and adds the four missing layout paths, which is a
  prerequisite for plan 01-07's no-allowlist `tests/unit/test_repo_layout.py` to be writable at
  all — that test now has a complete canonical listing to compare the tree against
- `.github/pull_request_template.md` is in place before the first real milestone PR opens; its
  six items have zero overlap with the guard tests plan 01-07/01-08 will add, so no future
  duplication needs to be caught and removed later

---
*Phase: 01-repository-foundation*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 4 created artifacts found on disk (docs/MODULE_CONTRACTS.md, docs/RISK_REGISTER.md,
docs/ADR/ADR-006_module-contracts-layout-and-citation-policy.md,
.github/pull_request_template.md); all 3 task commits verified present in git history
(3a2c895, 6140502, e62371b).
