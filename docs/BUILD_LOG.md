# Build Log

This file is **append-only** and is never edited in place (EB-082 applied at document
level). A correction to a prior entry is never a rewrite — it is a **new dated entry that
cites the entry it corrects**. Entries are ordered by insertion, so file position, not the
date string, is the tie-break when two entries share a date: the entry appearing later in
the file is the later one. A milestone whose measured effort is **strictly greater than**
2x its Charter §5 day budget stops work and files an ADR analyzing why; effort measured at
exactly 2x does not trip the rule (e.g. an M0 measured at 1.0 d against its 0.5 d budget
does not trip — 1.01 d does).

---

## M0 - Bootstrap

### 2026-08-04 — D-29 audit: pre-existing artifacts vs WBS acceptance criteria

Phase 1 (P0/M0) opens with an audit of the three WBS tasks that were partly done before
this plan started: T-001 (git baseline), T-003 (repository skeleton), T-012 (governance
scaffold). Each acceptance criterion below was checked by running the probe named in the
Observed column, not by copying the D-29 known-state table in
`01-CONTEXT.md`.

| WBS AC | Expected | Observed | Verdict | Closed by |
|---|---|---|---|---|
| T-001 AC-1 | Baseline commit contains only documentation, zero code | `git log --oneline 1851f39 -1 --stat` shows 25 files changed, 4943 insertions(+), 0 deletions; every path is `.md` (AGENTS.md, PROJECT_CHARTER.md, docs/EXECUTION_BLUEPRINT/*, docs/SPEC-01..09) | PASS | — |
| T-001 AC-2 | `.gitattributes` or config pins LF for `*.csv`, `*.py`, `*.yaml`, `*.md` | No `.gitattributes` file exists; `git config --get core.autocrlf` (local) and `git config --global --get core.autocrlf` both exit 1 (unset) | FAIL | 01-01 Task 2 |
| T-001 AC-3 | No file from outside the corpus committed | Same `--stat` output as AC-1: all 25 paths are charter, agent playbook, SPEC-01..09 or execution-blueprint documents; nothing else | PASS | — |
| T-003 AC-1 | Tree diff vs SPEC-08 §2 is empty (allowing not-yet-created source files) | `ls` at repo root shows only `.gitignore`, `.git/`, `.planning/`, `AGENTS.md`, `PROJECT_CHARTER.md`, `docs/`. None of `README.md`, `LICENSE`, `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`, `.env.example`, `config/`, `src/ambo/`, `dbt/`, `scripts/`, `data/`, `exports/`, `reports/`, `dashboards/`, `tests/` exists yet | PASS | 01-02 Task 3 |
| T-003 AC-2 | Ignore rules proven by validation probe | `touch data/warehouse/x.duckdb exports/foo.csv && git status --porcelain`: `data/warehouse/x.duckdb` does not appear (ignored, correct); `exports/foo.csv` appears as untracked (`?? exports/`) — correct per the W5 ingest resolution, which committed `exports/*.csv` by design rather than gitignoring it (SPEC-08 §2, EB-081). Probe files deleted immediately after the check; nothing was staged | PASS | — |
| T-003 AC-3 | LICENSE = MIT with author line matching Charter header | `ls LICENSE` — no such file | PASS | 01-02 Task 3 |
| T-012 AC-1 | ADR template has the four GB-201 sections | `ls docs/ADR/` shows only `ADR-000_document-precedence-and-blueprint-defaults.md`; no template file exists | FAIL | 01-01 Task 3 |
| T-012 AC-2 | Pre-planned ADR slots ADR-001..005 listed with their GB-202 topics | No `docs/ADR/README.md` exists; no index of reserved slots exists anywhere | FAIL | 01-01 Task 3 |
| T-012 AC-3 | BUILD_LOG has its append-only rule stated at top | Before this task ran, `docs/BUILD_LOG.md` did not exist | FAIL | 01-01 Task 1 (this entry) |

**Deviations not remediated by this audit (recorded, not fixed):**

1. The baseline commit message reads `chore: baseline commit — charter, agent playbook,
   SPEC-01..09, execution blueprint`, not the exact text T-001's implementation notes
   specify (`chore: baseline governance corpus (Charter v1.0, SPEC-01..09, blueprint)`).
   EB-082 forbids amending a landed commit to fix this. ADR-006 (plan 01-03) carries the
   note per D-18 of `01-CONTEXT.md`: commits `1851f39`…`151d32b` predate the EB-080 commit
   convention, and conformance begins with the first `m0-bootstrap` commit.
2. `core.autocrlf` is unset both locally and globally. T-001's implementation notes
   proposed a local-config fix (`core.autocrlf=input`); D-22 supersedes that approach with
   a committed `.gitattributes`, which does not depend on the reviewer's own git config.
   Task 2 of this plan closes T-001 AC-2 on that basis, not by setting `core.autocrlf`.
3. `.gitignore` carries one line beyond the EB-081 list: `docs/EXECUTION_BLUEPRINT/`. This
   is D-01 (`01-CONTEXT.md`) and is correct — the execution blueprint is internal build
   scaffolding, restored to disk for this phase but never committed.

**PASS-with-evidence, recorded for completeness:**

- Repository merge settings match D-12: `gh api repos/:owner/:repo --jq '{squash:
  .allow_squash_merge, rebase: .allow_rebase_merge, merge: .allow_merge_commit}'` returns
  `{"squash": false, "rebase": false, "merge": true}`. Squash and rebase merge are
  disabled at the repository level, so the merge button cannot destroy the task-level
  commit trail EB-082 and the layer-order argument depend on.

### 2026-08-04 — D-07: T-011 season-window spec interpretations (advent, schulbeginn)

`scripts/generate_season_windows.py` (plan 01-06) fills two gaps SPEC-01 section 2.1
leaves open. Per D-07 (`01-CONTEXT.md`), the spec text stands unchanged in both cases and
the work fills a gap, not a change — so this build-log entry plus the in-script source
comments on `advent_weeks()` and `schulbeginn_weeks()` are the record; no ADR is owed.

1. **Advent is read as exactly 4 flagged weeks total, ending at the Dec-24 week
   inclusive.** SPEC-01 section 2.1 says "advent = 1 in the 4 ISO weeks before and incl.
   the week of Dec 24", which is compatible with either 4 weeks total (3 before + the
   Dec-24 week) or 5 weeks total (4 before + the Dec-24 week). `docs/EXECUTION_BLUEPRINT/
   05_IMPLEMENTATION_GUIDES.md` section 1.2 resolves this in favour of 4 weeks total:
   "the ISO week containing Dec 24 and the 3 preceding ISO weeks (total 4 weeks)". The
   generator implements the Guide's reading. Evidence: SPEC-01 section 2.1 (line 32),
   Guide section 1.2 (lines 31-34).
2. **Styrian school start (schulbeginn) is read as the second Monday of September.**
   SPEC-01 section 2.1 says only "1 in the 2 weeks around Styrian school start, early
   Sep", naming no precise date. The `holidays` package's Austria calendar carries no
   AT-6 (Styria) school-holiday subdivision, so there is no data source encoding the
   actual first school day of any given year. The Guide (section 1.2, lines 35-37) fixes
   the reading as "second Monday of September (fixed rule)": flag that ISO week and the
   ISO week before it. The generator implements this fixed rule every year in range,
   2019-2027, with no calendar-package lookup.

Both readings are recorded twice, per T-011's own acceptance criteria (`02_WBS.md` lines
248-249): as the in-script source comments on `advent_weeks()` and
`schulbeginn_weeks()` in `scripts/generate_season_windows.py`, and as this entry.

### 2026-08-04 — T-010 AC-1: planted-violation proof for all four architectural guards

Per D-23 and T-010 AC-1 (`02_WBS.md` lines 218-221), each of the four standing guard
tests added in plan 01-07 was proven to actually fail on a planted violation, not just
proven to pass on a clean tree. The proof ran entirely on a scratch branch
(`scratch-01-07-planted-violations`, created from `m0-bootstrap` at commit `009f56f`),
with no commit ever made on it — every planted change was a working-tree edit, reverted
by hand before the next violation was planted. The branch was deleted with `git branch -d`
(a safe, non-force delete: since nothing was ever committed to it, it pointed at the same
commit as `m0-bootstrap` and diverged in zero commits) immediately after the fourth proof,
restoring `HEAD` to `m0-bootstrap` with a clean working tree. Nothing from the scratch
branch reached `m0-bootstrap`'s history, preserving EB-082.

1. **`tests/unit/test_import_independence.py` (SIM-003/W-2 firewall).** Planted
   `src/ambo/simulate/_scratch_violation.py` containing `from ambo.model import fit`.
   Failing node id: `tests/unit/test_import_independence.py::test_simulate_and_model_do_not_import_each_other`.
   Message: `AssertionError: simulate<->model cross-import found (SIM-003 / W-2
   firewall): src/ambo/simulate/_scratch_violation.py imports ambo.model`.
2. **`tests/unit/test_forbidden_deps.py` (Charter O-3 / EB-030).** Planted
   `src/ambo/_scratch_violation2.py` containing `import robyn`.
   Failing node id: `tests/unit/test_forbidden_deps.py::test_no_forbidden_framework_is_imported_anywhere`.
   Message: `AssertionError: Forbidden framework import(s) found (Charter O-3):
   src/ambo/_scratch_violation2.py: ['robyn']`.
3. **`tests/unit/test_repo_layout.py` (D-23 layout guard).** Added a new top-level
   directory `_scratch_top_level_violation/.gitkeep`, staged with `git add -f` so
   `git ls-files` would see it.
   Failing node id: `tests/unit/test_repo_layout.py::test_top_level_entries_are_all_in_the_canonical_layout`.
   Message: `AssertionError: Top-level entr(y/ies) not in the SPEC-08 section 2 (+
   D-14) canonical layout: ['_scratch_top_level_violation']. ... Scanned 23 top-level
   entries across 120 tracked files.`
4. **`tests/unit/test_line_endings.py` (D-22 LF pin).** Planted
   `docs/_scratch_crlf_violation.scratchdat` with CRLF bytes, staged with a temporary
   `.gitattributes` override line (`docs/_scratch_crlf_violation.scratchdat text`) so
   `git check-attr text` reported `set` rather than relying on the catch-all `auto`.
   Failing node id: `tests/unit/test_line_endings.py::test_no_tracked_text_file_contains_a_carriage_return`.
   Message: `AssertionError: Tracked text file(s) contain a carriage-return byte:
   ['docs/_scratch_crlf_violation.scratchdat']`.

After each proof, the planted file was deleted (and, for violations 3 and 4, unstaged
with `git restore --staged` and the `.gitattributes` override reverted with
`git checkout --`) before the next violation was planted, so each proof isolated exactly
one guard. `uv run pytest tests -q` was confirmed green on the scratch branch immediately
before switching back to `m0-bootstrap`.

**Related fix, discovered by `test_line_endings.py` itself during authoring (not part of
the planted-violation proof above):** several already-tracked files
(`.gitignore`, `PROJECT_CHARTER.md`, four `docs/SPEC-*.md` files, `docs/ADR/
ADR-000_document-precedence-and-blueprint-defaults.md`, and four `.planning/*.md` files)
carried CRLF bytes in their on-disk working-tree copies, despite their committed blobs
already being LF-only (confirmed via `git show HEAD:<path>` before the fix). Root cause:
this dev machine's `core.autocrlf` is `true`, and a plain `git checkout -- <path>` is a
no-op when git's clean-filtered comparison already matches the index, so the CRLF bytes
survived on disk from an earlier write until a *fresh* checkout (delete, then
`git checkout HEAD -- <path>`) forced the `eol=lf` smudge filter to re-apply. No commit
was needed — the object database was already correct, only the working-tree bytes
changed, and `git status --porcelain` was empty for all twelve paths both before and
after.
