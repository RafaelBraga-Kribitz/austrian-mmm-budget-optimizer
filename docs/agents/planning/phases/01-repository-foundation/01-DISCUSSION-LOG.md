# Phase 1: Repository Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-04
**Phase:** 1-repository-foundation
**Areas discussed:** Blueprint access, Branch & PR mechanics, CI gate strictness, Windows parity, Layout guard scope, Milestone checklist home, Partially-done tasks, Commit history reconciliation, settings.yaml scope, Spec interpretation vs spec edit, Season-windows seed enforcement, Leak scan aggressiveness

**Findings surfaced before questioning:**
- `docs/EXECUTION_BLUEPRINT/` was absent from disk, contradicting STATE.md. Recoverable from `1851f39`.
- ROADMAP.md's Phase 1 "must resolve" block is stale — WARNING 3 and the branch question were both resolved in `ffce015`.
- `origin/main` is 2 commits behind local.
- GitHub returns 403 for branch protection and rulesets on this private free-tier repo.
- No `.gitattributes`; `core.autocrlf` and `core.eol` unset locally and globally.
- No `g++` on the dev machine (PyTensor backend risk, Phase 4).
- Three blueprint documents are cited by published docs: `03_MODULES`, `07_QUALITY_STANDARDS` Part A, `11_ACCEPTANCE_CRITERIA` §4.

---

## Blueprint access

### Where the 14 blueprint files should live

| Option | Description | Selected |
|--------|-------------|----------|
| Restore to disk, stay gitignored | Agents read by path; published tree unchanged; drift risk from history | ✓ |
| Re-track them in the repo | Visible to all clones, but 39k words of internal process docs go public at M3 | |
| Leave in history only | Nothing drifts, but Read/Grep can't reach it so it gets skipped | |
| Restore to disk + track a slim subset | Bundles the next question's answer | |

**User's choice:** Restore to disk, stay gitignored.
**Notes:** `1851f39` remains canonical; the working copy is a read surface, not an edit surface.

### How SPEC-08 §2's contract-first rule should work

| Option | Description | Selected |
|--------|-------------|----------|
| Promote to tracked `docs/MODULE_CONTRACTS.md` | Rule becomes checkable; W3's resolution rests on this clause | ✓ |
| Keep pointing at the internal blueprint | Zero work; published spec cites an unopenable document | |
| Drop the same-PR requirement | Re-opens W3; would need an ADR | |

**User's choice:** Promote to tracked `docs/MODULE_CONTRACTS.md`.

### How to record the SPEC-08 §2 amendment

| Option | Description | Selected |
|--------|-------------|----------|
| ADR-006, and that's the standing bar | Matches standing rule 4 and the ADR-000 precedent | ✓ |
| BUILD_LOG entry only | Lighter; leaves a changed spec clause with no decision record | |
| Split by materiality | Pragmatic; needs a written materiality test | |

**User's choice:** ADR-006, and that's the standing bar for every future spec edit.
**Notes:** GB-202's reserved slots ADR-001…005 stay open for their named topics.

### T-006's stub message text

| Option | Description | Selected |
|--------|-------------|----------|
| Point at README's phase table | Resolves in a clone; dangles until a README exists | ✓ |
| Name the phase, no pointer | Never dangles; no route to what Phase N delivers | |
| Keep the blueprint path | Zero deviation; dead on arrival for every other reader | |

**User's choice:** Point at README §Roadmap.

### Whether Phase 1 creates a README

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal README with phase table | SPEC-08 §2 lists README.md anyway; Phase 9 replaces the body | ✓ |
| Defer to Phase 9, stub points at Makefile | Self-contained; no README for eight phases | |
| Defer, accept the dangling pointer | Zero work; a loud-but-wrong error message | |

**User's choice:** Minimal README with phase table.

### When the fit ceiling and DL-1 probe get promoted

| Option | Description | Selected |
|--------|-------------|----------|
| Promote at point of need, record rule now | ADR-006 carries the rule and the two owners; protects the 0.5 d budget | ✓ |
| Promote all three in Phase 1 | Closes it permanently; adds scope to a 0.5 d phase | |
| Only 03_MODULES, leave the rest | Charter DL-1 keeps citing an unshipped file | |

**User's choice:** Promote at point of need — fit ceiling → Phase 4, DL-1 probe → Phase 9.

### Which module-contract document is authoritative

| Option | Description | Selected |
|--------|-------------|----------|
| MODULE_CONTRACTS.md is the source; 03_MODULES frozen | Single home; matches E-4 / 09 A-2 | ✓ |
| 03_MODULES stays the source, MODULE_CONTRACTS.md generated | Never drifts; needs a generator and CI check | |
| Both editable, reconcile by review | The two-documents-one-fact pattern that produced W1–W7 | |

**User's choice:** MODULE_CONTRACTS.md authoritative; 03_MODULES frozen with a superseded header.

### Whether the restore is a plan task or housekeeping

| Option | Description | Selected |
|--------|-------------|----------|
| Restore now, before planning | Planner can read T-001…T-012 by path | ✓ |
| Make it a Phase-1 plan task | Planner would have to write the task without reading the WBS | |
| Don't restore; agents read from history | Read/Grep can't reach it | |

**User's choice:** Restore now. **Executed during the discussion** — 14 files on disk, `git status` clean.

### What goes into MODULE_CONTRACTS.md in Phase 1

| Option | Description | Selected |
|--------|-------------|----------|
| Grow-as-you-go — rules + Phase 1's modules only | Same-PR rule becomes an observable addition | ✓ |
| Full port with status markers | Whole architecture visible; rule degrades to a flag flip | |
| Full port, no status markers | Doc misrepresents the repo for eight phases | |

**User's choice:** Grow-as-you-go.

### How the `[STD]` layout item is enforced

| Option | Description | Selected |
|--------|-------------|----------|
| A test in T-010's guard suite | Matches GB §8 — showpieces are scripts, not checklists | ✓ |
| Tracked PR template | Still a human ticking a box | |
| Both — test for layout, template for the rest | Most complete; two artifacts, partial overlap | |
| Leave it internal | The rule W3's resolution rewrote goes unenforced | |

**User's choice:** A test in T-010's guard suite. T-010 grows from three guards to four.

---

## Branch & PR mechanics

### How Phase 1's work lands on main

| Option | Description | Selected |
|--------|-------------|----------|
| Full PR ceremony now, enforcement at M3 | Self-imposed discipline; PR carries standing rule 1's evidence | ✓ |
| Commit to main until M3, then adopt PRs | No theatre; no home for the milestone checklist | |
| Branch + PR, merge without waiting for CI | Drops standing rule 2's guarantee | |

**User's choice:** Full PR ceremony now.
**Notes:** Protection is 403-blocked until go-public, so it joins the existing M3 checklist.

### Branch granularity given the phase↔milestone mismatch

| Option | Description | Selected |
|--------|-------------|----------|
| Milestone branches, phase commits | Follows EB-080 literally; M2 spans Phases 3–4 on one branch | ✓ |
| Phase branches, milestone PR from the last one | Cleaner sessions; two branch levels | |
| Phase branches, one PR each | Contradicts EB-080; splits M2's exit gate | |

**User's choice:** Milestone branches, phase commits.

### Whether to enforce merge commits mechanically

| Option | Description | Selected |
|--------|-------------|----------|
| Disable squash and rebase merge now | Repo settings aren't Pro-gated; the button can't destroy the trail | ✓ |
| Disable at M3 with branch protection | Five milestones with the squash button live | |
| Leave it, rely on discipline | The one irreversible mistake in the project | |

**User's choice:** Disable now. **Executed during the discussion** — `allow_squash_merge=false`, `allow_rebase_merge=false`.

### How commits reach origin

| Option | Description | Selected |
|--------|-------------|----------|
| Push main first, then branch m0-bootstrap | Relocating the doc commits would need history rewriting (EB-082) | ✓ |
| Push main, then push m0-bootstrap per task | Tightest CI loop; burns Actions minutes | |
| Push only at PR time | Fewest runs; twelve tasks' worth of signal arrives at once | |

**User's choice:** Push main first, then cut the branch.

---

## CI gate strictness

### When the coverage gate starts blocking

| Option | Description | Selected |
|--------|-------------|----------|
| Live at M0 close | Only config.py and logging.py in scope; EB-072 states ≥80% flatly | ✓ |
| Advisory until M2 | First blocking run lands on MMM code | |
| Live at M0 but at a lower bar | A threshold that isn't EB-072's — a spec deviation | |

**User's choice:** Live at M0 close.

### How jobs 3, 4 and 5 pass at M0

| Option | Description | Selected |
|--------|-------------|----------|
| Real scripts that exit 0 with a notice | Exactly what SC-2 asks; BP-D-13's script-exits-green pattern | ✓ |
| `if: hashFiles()` guards | Skipped ≠ passed; can't satisfy a required check at M3 | |
| Placeholders now, hashFiles for job 3 | Two patterns for one problem | |

**User's choice:** Real scripts that exit 0 with a notice.

### Stubs or vacuously-correct checks

| Option | Description | Selected |
|--------|-------------|----------|
| Vacuously-correct real checks | Rot structurally impossible; Phase 5 extends rather than replaces | ✓ |
| Dumb stubs + a replacement test | Five phases of a check that only looks like a check | |
| Dumb stubs + a hard expiry | Same detection logic, then thrown away | |

**User's choice:** Vacuously-correct real checks.

### CI trigger events

| Option | Description | Selected |
|--------|-------------|----------|
| `push:[main]` + `pull_request:[main]`, draft PR early | Continuous CI, no duplicate runs, concurrency cancel | ✓ |
| push (all branches) + pull_request | Double minutes on PR branches | |
| pull_request only | main's own state never verified | |

**User's choice:** `push:[main]` + `pull_request:[main]` with an early draft PR.

---

## Windows parity

### How the Windows half of SC-1 is proven

| Option | Description | Selected |
|--------|-------------|----------|
| Matrix the test job across ubuntu + windows | Job name unchanged so EB-060 holds; windows bills 2× on private | ✓ |
| Manual check, recorded in BUILD_LOG | Zero CI cost; SC-1 becomes a human promise | |
| Matrix lint + test both | Triples Windows minutes for a rare failure class | |
| Seventh Windows job | Breaks EB-060's six literally; needs an ADR | |

**User's choice:** Matrix the test job.

### How LF is pinned

| Option | Description | Selected |
|--------|-------------|----------|
| Committed `.gitattributes` | Travels with the repo; local config does not | ✓ |
| Both — .gitattributes plus core.autocrlf=input | Two homes for one rule | |
| Local config only | Nothing travels; CRLF returns silently on a new machine | |

**User's choice:** Committed `.gitattributes`, plus a no-CRLF test.
**Notes:** T-001 AC-2 is currently entirely unmet — neither file nor config exists.

### Where the risk register lives and where g++ is recorded

| Option | Description | Selected |
|--------|-------------|----------|
| Tracked `docs/RISK_REGISTER.md`, seeded now | Satisfies REQ-risk-register reviewably; closes the citation gap | ✓ |
| Keep the register internal, note g++ in BUILD_LOG | Evidence lives in an unshipped file | |
| Tracked register, defer the risk content to Phase 4 | Relies on remembering, three phases out | |

**User's choice:** Tracked `docs/RISK_REGISTER.md`, seeded with R-1…R-9 plus the g++ finding.

---

## Layout guard scope

| Option | Description | Selected |
|--------|-------------|----------|
| Amend SPEC-08 §2 to list them; test asserts the full tree | One place says what belongs; rolls into ADR-006 | ✓ |
| Allowlist inside the test | Two documents define the layout and disagree | |
| Narrow the test to `src/ambo/` subpackages | §2's most emphatic clause goes unenforced | |

**User's choice:** Amend SPEC-08 §2 to add `.github/`, `.planning/`, `uv.lock`, `.gitattributes`.
**Notes:** Surfaced because the guard test agreed earlier would have red-lined the repo it guards.

---

## Milestone checklist home

| Option | Description | Selected |
|--------|-------------|----------|
| Tracked PR template with the judgment items only | No duplication with the test; travels with the repo | ✓ |
| Promote 06_CHECKLISTS to `docs/CHECKLISTS.md` | Consistent with the other promotions; still needs manual linking | |
| BUILD_LOG entry per milestone, no template | Checklist not in front of you when writing the PR | |

**User's choice:** `.github/pull_request_template.md` carrying only the non-machine-checkable items.

---

## Partially-done tasks

| Option | Description | Selected |
|--------|-------------|----------|
| Audit task first, gaps become work | Honest about history; produces M0 evidence | ✓ |
| Re-derive everything from acceptance criteria | Churns correct files; diff noise | |
| Mark them done, plan only the remainder | Unmet criteria caught only by memory | |

**User's choice:** Audit task first.
**Notes:** Resolved the T-012 template name collision — `docs/ADR/TEMPLATE.md`, since ADR-000 is taken.

---

## Commit history reconciliation

| Option | Description | Selected |
|--------|-------------|----------|
| ADR-006 records it; convention starts at the next commit | Answer sits with the rule it qualifies | ✓ |
| BUILD_LOG entry, no ADR clause | Buried in chronological order | |
| Say nothing | Four non-conforming commits at the root of a history-is-evidence argument | |

**User's choice:** ADR-006 records it.

---

## settings.yaml scope

| Option | Description | Selected |
|--------|-------------|----------|
| Author whole, per T-004 | Fixed spec constants, not guesses; grep assertion true from day one | ✓ |
| Grow per phase | Anti-magic-number grep has no teeth until Phase 4 | |
| Author whole, sampler block behind a nested optional | Optionality that exists purely for phasing | |

**User's choice:** Author whole.

---

## Spec interpretation vs spec edit

| Option | Description | Selected |
|--------|-------------|----------|
| BUILD_LOG when the spec text stands, ADR when it changes | Keeps the ADR series meaningful | ✓ |
| ADR for any interpretation that fixes a free parameter | Strongest trail; thirty ADRs stop being read | |
| Escalate the spec instead — amend, then ADR | Heaviest; every ambiguity becomes an edit plus an ADR | |

**User's choice:** BUILD_LOG for interpretations, ADR for edits.
**Notes:** Policy applies across all nine phases, not just T-011.

---

## Season-windows seed enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Enforce in job 1 (lint) | Seconds, no new job, EB-060's six stay six | ✓ |
| Enforce in job 2 (test) as a unit test | Surfaces locally too; sits oddly among pure unit tests | |
| Leave it to the generator's own tests | Tests verify the generator, not the file dbt reads | |

**User's choice:** Diff-check in job 1.

---

## Leak scan aggressiveness

| Option | Description | Selected |
|--------|-------------|----------|
| High-precision patterns only, scoped by path | Near-zero false positives; still trusted in Phase 6 | ✓ |
| Broad patterns with an allowlist | Highest recall; allowlist grows under pressure to get CI green | |
| High-precision now, widen at Phase 6 | Depends on remembering unless it becomes a register entry | |

**User's choice:** High-precision, path-scoped. Widening at Phase 6 recorded in the risk register.

---

## Claude's Discretion

- Exact `.gitattributes` rule set beyond the LF pin and binary exclusions.
- Wording and structure of ADR-006, MODULE_CONTRACTS.md, RISK_REGISTER.md, the PR template.
- Concrete regex forms for the three leak-scan pattern classes.
- Reporting format of the audit task.

## Deferred Ideas

- Fit ceiling → `config/settings.yaml` in Phase 4.
- DL-1 release probe → tracked document in Phase 9.
- Leak-scan pattern widening → Phase 6, alongside T-501…T-506.
- Branch protection with six required checks → M3 go-public checklist.
- `g++` / PyTensor compiler gap → Phase 4.
- Raised but not discussed: whether `make setup` should run `pre-commit install` for a
  read-only reviewer; the LICENSE author line given the anonymization posture; how the 0.5 d
  effort tripwire is measured in practice.
