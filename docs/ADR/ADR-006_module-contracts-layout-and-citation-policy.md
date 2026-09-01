# ADR-006 — Module contracts, layout, and citation policy

- **Status:** Ratified
- **Date:** 2026-08-04
- **Deciders:** Rafael Braga-Kribitz
- **Supersedes:** —
- **Related:** `docs/SPEC-08_engineering.md` §2 (repository layout), `docs/SPEC-09_governance_quality.md`
  GB-201/GB-202, `docs/ADR/ADR-000_document-precedence-and-blueprint-defaults.md`,
  `.planning/phases/01-repository-foundation/01-CONTEXT.md` D-01…D-05, D-14, D-18, D-24

---

## Context

Four Phase 1 governance questions share one root cause — `docs/EXECUTION_BLUEPRINT/` (14 files)
is gitignored per D-01, and several published, tracked documents were written as if a reader
could open it. That is a standing-rule violation the moment it is stated, and this ADR is where
Phase 1 closes it.

1. **SPEC-08 §2's contract-first citation is unresolvable.** The canonical-layout section names
   `03_MODULES` (internal execution blueprint) as the place a new module's public contract must
   be entered in the same PR. A reader following that citation from the published SPEC hits a
   file that does not exist in their clone.
2. **SPEC-08 §2's canonical layout omits four permanent, load-bearing paths.** `.github/`,
   `.planning/`, `uv.lock`, and `.gitattributes` all exist in this repository by design (Phase 1
   creates or requires all four), yet none appears in the layout tree SPEC-08 §2 declares
   canonical. Plan 01-07's `tests/unit/test_repo_layout.py` is specified to compare the real tree
   against this listing with **no allowlist** — which is only possible once the listing is
   complete.
3. **The standing rule itself needs to exist and be stated once, in one place**, rather than
   being re-derived ad hoc every time a published document's citation is checked: no published
   document may cite an unpublished one. Two such violations were found during Phase 1 planning
   and need named owners, not silent deferral.
4. **Commits `1851f39`…`151d32b` predate the EB-080 conventional-commit convention** (`01-01`'s
   D-13 branch-topology work landed before this convention was written down), and EB-082 forbids
   fixing them by rewriting history. Absent a record, a later reviewer has no way to know this
   was a deliberate acceptance rather than an oversight.

## Decision

Four decisions, one per D-05 topic:

### 1. SPEC-08 §2's contract-first citation repoints at `docs/MODULE_CONTRACTS.md`

The contract-first rule in SPEC-08 §2 — "a new module inside a listed package is permitted... on
one condition: the module has a public contract entry in the module-contract document... merged
in the same PR" — now cites `docs/MODULE_CONTRACTS.md`, not `03_MODULES`.
`docs/EXECUTION_BLUEPRINT/03_MODULES.md` is frozen as of this phase: it is never edited again and
remains the design input for contracts not yet written, but it is no longer the citation target
for any published document.

### 2. SPEC-08 §2's canonical layout gains four entries

`.github/`, `.planning/`, `uv.lock`, and `.gitattributes` are added to SPEC-08 §2's canonical
repository layout. All four are permanent and load-bearing — `.github/` carries `ci.yml` and the
pull-request template this ADR also creates; `.planning/` is the version-controlled GSD state
this project runs on; `uv.lock` is the EB-030 point-of-no-return lockfile; `.gitattributes` is the
D-22 line-ending pin. Their earlier absence from the listing was an authoring gap, not a rule —
none of the four is optional or newly introduced by this decision. This is what makes the
no-allowlist repository layout test in plan 01-07 possible: with all permanent paths listed, a
tree-vs-listing comparison can be exact rather than approximate.

### 3. Standing rule: no published document may cite an unpublished one

Stated once, here, for reuse: a document a reader can open (published, tracked) may never cite a
document the reader cannot open (unpublished, gitignored) as if it were readable. Two known
violations existed at this ADR's ratification, and both are recorded with a named owning phase
rather than left as open questions:

- The normative per-fit ceiling, currently stated only in `07_QUALITY_STANDARDS` Part A and cited
  by SPEC-08 §5, moves into `config/settings.yaml` in **Phase 4** — the single-config-home rule
  (EB-040, D-25) gives it a published home at the same time the fit-runner code that needs it is
  written.
- The DL-1 release probe, currently stated only in `11_ACCEPTANCE_CRITERIA` §4 and cited by
  SPEC-08 §5, Charter DL-1, and ADR-000, gets a tracked home in **Phase 9** — the release phase
  that actually executes the probe is the natural place to publish its exact sequence.

Both are deferrals with an owning phase, not open questions left for a future reader to resolve.

### 4. Commit-history conformance begins with the first `m0-bootstrap` commit

Commits `1851f39` through `151d32b` predate the EB-080 conventional-commit-plus-REQ-IDs
convention; the baseline commit's message text differs from what T-001 specifies. EB-082 forbids
amending them, so this ADR is the permanent record instead of a history rewrite. Conformance is
in effect from the first commit on `m0-bootstrap` onward. The message format itself was already
fixed before this ADR — `07_QUALITY_STANDARDS` line 113 specifies
`feat|fix|test|docs|chore|refactor(scope): message [REQ-IDs]` — so this decision is only the
starting-point record, not a new format choice.

## Consequences

**Positive.** Every published document's citations now resolve for a reader who has only the
tracked tree. The repository-layout guard test in plan 01-07 can compare the real tree against a
complete canonical listing with no allowlist, which is strictly stronger than an allowlist-based
check. The standing citation rule is stated once and is reusable the next time a similar gap is
found, rather than re-litigated. The commit-history gap has a permanent, referenceable record
instead of living only in tribal memory.

**Negative.** `docs/MODULE_CONTRACTS.md` and `docs/RISK_REGISTER.md` are now the documents of
record their SPEC-tier and Charter-tier counterparts depend on staying current — a future PR that
adds a module without its contract entry, or that closes a risk without updating its row, breaks
a real citation chain rather than a cosmetic one. This is accepted: `tests/unit/test_repo_layout.py`
(plan 01-07) makes the module-contract half of that dependency mechanically enforced, matching the
project's stated preference for machine enforcement over a written rule wherever the rule is
checkable.

**Neutral.** Every specification edit from this ADR onward gets its own ADR (D-06, already the
standing bar recorded in `docs/ADR/README.md`); this ADR is simply the first to exercise SPEC-08
§2 under that rule.

## Spec deviations

| Document | Section | Change | REQ IDs |
|----------|---------|--------|---------|
| `docs/SPEC-08_engineering.md` | §2 | Contract-first citation repointed from `03_MODULES` (gitignored) to `docs/MODULE_CONTRACTS.md` (tracked) | REQ-scope-in |
| `docs/SPEC-08_engineering.md` | §2 | Canonical layout tree gains `.github/`, `.planning/`, `uv.lock`, `.gitattributes` | REQ-scope-in, REQ-dl8-quality |
| *(standing rule, no single document)* | — | No published document may cite an unpublished one; two known violations recorded with owning phases (Phase 4, Phase 9) | REQ-scope-in |
| *(commit history, no document edit)* | — | Commit-history conformance begins at the first `m0-bootstrap` commit; `1851f39`…`151d32b` are recorded as pre-convention and un-amendable per EB-082 | REQ-milestones |
