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

### 2026-09-01 — T-012 AC-1 and AC-2 closed (01-01 Task 3)

Cites the 2026-08-04 D-29 audit entry above. `docs/ADR/TEMPLATE.md` now exists at
`TEMPLATE.md` (not `ADR-000_template.md`, per D-09) with exactly the four GB-201
level-2 sections: Context, Decision, Consequences, Spec deviations. `docs/ADR/README.md`
now exists as the ADR index: GB-201 naming convention, D-06 standing bar, ADR-000
recorded as Ratified, all five GB-202 reserved slots (ADR-001 permission, ADR-002
channel-mapping, ADR-003 anonymization, ADR-004 Layer R window, ADR-005
reparameterization) with their topics, plus the standard non-slot triggers. T-012
AC-3 was already discharged by the audit entry that created this file.

T-012 AC-1: PASS. T-012 AC-2: PASS. T-012 AC-3: PASS (unchanged).

### 2026-09-01 — Locked execution decisions (1A 2A 3A 4B)

Human answers to the four blocking questions, locked for the rest of this loop:

1. **Pin `uv.lock` (1A).** Direct deps match SPEC-08 §3. `scikit-learn` 1.9.0 is present
   transitively via `pymc-marketing` → `pymc-extras`. Charter O-3 is import-scoped, not
   tree-scoped; no ADR. The standing guard in plan 01-07 (`tests/unit/test_forbidden_deps.py`)
   remains the enforcement. EB-030 pin commit is `chore(01-02): pin dependency set per EB-030`.
2. **Reuse `m0-bootstrap` artifacts (2A).** Later plans copy already-verified files from
   `origin/m0-bootstrap` rather than rewriting them. Draft PR #1 is still not the merge vehicle.
3. **No private drop at M4 (3A).** Build all drop-independent work. At M4 write the Charter §7
   degradation ADR and ship Layers P+D on S-B. Do not invent Layer R data (A-5).
4. **One PR per GSD plan (4B).** One git commit per task inside the plan. Supersedes the
   2026-09-01 "one PR per task" topology note for the rest of this loop.

### 2026-09-01 — T-003 AC-1 and AC-3 closed (01-02 Task 3)

Cites the 2026-08-04 D-29 audit entry. The SPEC-08 §2 skeleton, `.env.example` (exactly
`AMBO_PRIVATE_DROP`, fictional path), and MIT LICENSE (`Copyright (c) 2026 Rafael Braga-Kribitz`)
are in the tree. Ignore probe re-run: `data/warehouse/x.duckdb` ignored; `exports/foo.csv`
untracked-not-ignored; probe files deleted, nothing residual staged. T-003 AC-1 and AC-3
verdict cells above flipped FAIL → PASS — the one sanctioned in-place edit for those rows.

### 2026-09-01 — T-004 and T-005 closed (01-04)

`config/settings.yaml` is the single configuration home: SPEC-02 §5.2 channel order,
adstock L=8, six paths (warehouse is the DuckDB file), MD-050 sampler block, parameter-free
scenario registry. `load_settings()` is cached, `extra='forbid'`, wraps validation failures
in `ConfigError` naming the key path. `get_logger` attaches `PrivatePathFilter`, which
reads the drop path only through `load_settings()` and redacts `msg`, `args`, and
exception text (CR-02). Copied from verified m0-bootstrap `5f12504` (2A).

Plant-and-revert: inserting `target_accept` into `src/ambo/common/errors.py` failed
`test_sampler_keys_appear_nowhere_else_in_src_ambo`; revert restored green. 19 unit tests
pass; mypy clean on `src/ambo`.

### 2026-09-01 — T-006 closed (01-05)

Canonical Makefile: 18 SPEC-08 §5 targets, `SHELL := /bin/sh` and `.SHELLFLAGS := -eu -c`,
twelve D-27 stubs, vacuous `transform` (D-17), `all` fails fast without fitting. Scaffold
README with `## Roadmap` nine-phase table (D-28). Copied from m0-bootstrap `0d46727` /
`64e8fe5` (2A). `make test` 19 passed.

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
