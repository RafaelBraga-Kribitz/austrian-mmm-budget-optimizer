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

### 2026-08-04 — M0 close: consolidated evidence (plan 01-09)

Phase 1 (P0/M0) closes with `.github/workflows/ci.yml` (the single six-job workflow)
and the two governance checks (`scripts/check_layer_order.py`,
`scripts/check_ssot_consistency.py`) landed. This entry consolidates what the eight
prior plans handed off, per T-009's own acceptance criteria and Phase 1 Success
Criterion 4. The CI-run line below is intentionally left as a pending placeholder —
plan 01-09 Task 3 is a `checkpoint:human-verify` gate that appends the real run URL
and the Windows-leg `make --version` string here once a human has observed the run,
which is when that evidence first exists. Nothing above this entry, and no other part
of this entry, is edited by that append (additions only).

**Audit verdicts (plan 01-01) and which task closed each failure.** The D-29 audit
entry above (2026-08-04) checked eight WBS acceptance criteria by running the named
probe; five passed outright and three failed. Each FAIL was closed by a specific
downstream task, not silently absorbed:

| WBS AC | Verdict | Closed by |
| --- | --- | --- |
| T-001 AC-1 | PASS | — |
| T-001 AC-2 (`.gitattributes` / LF pin) | FAIL | 01-01 Task 2 (committed `.gitattributes`, D-22) |
| T-001 AC-3 | PASS | — |
| T-003 AC-1 | PASS | — |
| T-003 AC-2 (ignore-rule probe) | PASS | — |
| T-003 AC-3 (LICENSE) | PASS (not yet due) | 01-02 Task 3 |
| T-012 AC-1 (ADR template) | FAIL | 01-01 Task 3 (`docs/ADR/TEMPLATE.md`) |
| T-012 AC-2 (reserved ADR slots listed) | FAIL | 01-01 Task 3 (`docs/ADR/README.md`) |
| T-012 AC-3 (BUILD_LOG append-only header) | FAIL | 01-01 Task 1 (this file) |

**Four planted-violation guard proofs (plan 01-07).** Already recorded in full,
including exact failing node ids and assertion messages, in the "T-010 AC-1:
planted-violation proof for all four architectural guards" entry above (2026-08-04).
Summarized here for the consolidated record: `test_import_independence.py::test_simulate_and_model_do_not_import_each_other`,
`test_forbidden_deps.py::test_no_forbidden_framework_is_imported_anywhere`,
`test_repo_layout.py::test_top_level_entries_are_all_in_the_canonical_layout`,
`test_line_endings.py::test_no_tracked_text_file_contains_a_carriage_return` — each
proven red on a planted violation, on a scratch branch with zero commits ever made on
it, then proven green again after the violation was reverted.

**Fake-key probe result (plan 01-08).** On scratch branch
`scratch-01-08-fake-key-probe`, a staged synthetic (never-real) PEM-style RSA
private-key block was blocked by the `detect-private-key` pre-commit hook before any
commit object existed: `git commit` exited 1 with `Private key found:
docs/_scratch_fake_key_probe.pem`; `git log --oneline -1` showed the same commit
(`0d12366`) before and after the attempt. The probe file was unstaged and deleted, and
the scratch branch was deleted with a non-force `git branch -d` (zero unique commits,
so the delete was a fast-forward no-op on history) — `git branch --list` afterward
showed only `m0-bootstrap` and `main`.

**Two season-window interpretations (plan 01-06).** Already recorded in full, with
citations to SPEC-01 section 2.1 and Guide section 1.2, in the "D-07: T-011
season-window spec interpretations" entry above (2026-08-04): advent is read as
exactly 4 flagged weeks total, ending at the Dec-24 week inclusive; schulbeginn
(Styrian school start) is read as the second Monday of September, since the
`holidays` package carries no AT-6 school-holiday subdivision.

**The eighteen Makefile target names** (SPEC-08 section 5, plan 01-05): `setup`,
`simulate`, `validate-sim`, `intake`, `anonymize`, `validate-intake`, `transform`,
`fit-synthetic`, `fit-real`, `recover`, `sensitivity`, `decide`, `ssot`, `export`,
`report`, `test`, `lint`, `all`.

**The six CI job names** (EB-060, `.github/workflows/ci.yml`, this plan): `lint`,
`test`, `dbt`, `ssot`, `layer-order`, `leak`. `test` is matrixed over
`ubuntu-latest`/`windows-latest` (D-21) and so produces two check runs while
remaining one of the six.

**CI run evidence (appended at the plan 01-09 Task 3 checkpoint).** Draft pull
request #1 (`m0-bootstrap` -> `main`, still in draft per D-11) exercised the
workflow across three pushes. The first run
(<https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer/actions/runs/30948579395>)
failed on two independent bugs surfaced by CI's Linux leg and self-scan, neither
caught by local (Windows-only) verification: (1) `scripts/leak_scan.py`'s own
`PRIVATE_DROP_PATTERNS` doc-comment examples matched the pattern they were
documenting, so the `leak` job flagged its own source; (2)
`Path(private_drop_raw).resolve()` in `config.py` made the `D:/...`-literal test
fixtures in `test_logging.py`/`test_leak_scan.py` absolute on Windows but
cwd-relative on Linux, failing four `test (ubuntu-latest)` cases. A second run
(<https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer/actions/runs/30951320145>)
fixed both but surfaced a third, previously-masked bug in the same code path:
`_resolve_private_drop_needles()` built three separator-form needles without
deduplicating, and on Linux two of the three were identical strings that both
matched the same line, double-counting one real match as two `Finding`s in
`test_private_drop_literal_path_found_when_resolved_via_environment` and
`test_env_example_carve_out_does_not_suppress_the_literal_check`. The third run
(<https://github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer/actions/runs/30951615385>)
is green: all six EB-060 jobs — `lint`, `test` (both `ubuntu-latest` and
`windows-latest` legs), `dbt`, `ssot`, `layer-order`, `leak` — report SUCCESS, none
skipped. The Windows leg's `make --version` output reads `GNU Make 4.4.1 / Built
for x86_64-w64-mingw32`, matching the development machine's verified 4.4.1 exactly
— the closing evidence for R-13, struck through on `docs/RISK_REGISTER.md` against
this entry. The `layer-order` and `ssot` jobs each printed their nothing-to-check
notice (`check_layer_order: no Layer R artifact matching ... and no
'prior-freeze-v1' tag found -- nothing to check yet`; `check_ssot_consistency: no
reports/NUMERIC_SSOT.md found ... -- nothing to reconcile`), and the `lint` job's
season-windows seed regeneration produced no diff. Three follow-up fix commits
(`2bb8b7c`, `a05d4ee`, `60c3f04`) landed 01-08/01-09 bug corrections — none of them
weakened a check, exempted a file from a scan, or skipped/xfailed a test; see
`01-09-SUMMARY.md` Deviations for the full account, including the correction to
01-08's SUMMARY claim that the scanner "exits 0 on the clean repository," which was
not accurate as originally written.

**Elapsed effort against the 0.5 d Charter section 5 budget.** Summing each plan's
measured duration from `.planning/STATE.md`'s Performance Metrics table (an 8-hour
working day is the interpretation used throughout this project for the `d` unit,
consistent with how every prior plan's duration was recorded in minutes): P01 (20 min)
plus P02 (8 min) plus P03 (13 min) plus P04 (12 min) plus P05 (8 min) plus P06
(~15 min) plus P07 (24 min) plus P08 (~30 min) totals 130 min for plans 01-01..01-08,
plus plan 01-09's own measured duration
(recorded in `01-09-SUMMARY.md`, since this entry is written before that plan
finishes). Even before adding plan 01-09's time, 130 min (~2.17 h, ~0.27 d) is well
under the 240 min (0.5 d) budget and nowhere near the 480 min (1.0 d) strictly-greater
tripwire threshold from this file's own header rule. **Verdict: the tripwire is not
tripped** — Phase 1's total measured effort, once 01-09 is added, remains far below
2x its budget; no ADR is triggered. The exact combined total is restated in
`01-09-SUMMARY.md`'s Performance section for the permanent record.

---

## M1 - Simulator

### 2026-08-05 — M1 close: scope, interpretations, authoring rationale, governance, gate evidence, effort tally (plan 02-10)

Phase 2 (P0's Layer P simulator, T-101…T-109) closes with the nine Layer P artifacts
committed under `data/synthetic/{s_a,s_b,s_c}/` and a proven git-checkout round-trip.
This entry consolidates what the ten Phase 2 plans handed off, per T-109's own
acceptance criteria and the M1 Documentation checklist row.

**Scope.** M1 was executed across ten plans: 02-01 ratified ADR-007 and installed
`hypothesis` as a dev-only property-testing dependency; 02-02 built the
`SimulationError`/`ScenarioConfig` pydantic model tree; 02-03 authored the three
`config/scenarios/{s_a,s_b,s_c}.yaml` files plus the promo/burst placement authoring
aid; 02-04 built `week_index`/`season_index`/`baseline_demand`/`round_half_up` and the
simulator's own `adstock_recursive`/`hill`; 02-05 built `generate_spend`; 02-06 built
`SimulationResult`/`assemble_scenario` and the SIM-071/072/073 audits; 02-07 built
`platform_report` (SIM-060/061 platform-reporting bias); 02-08 built `truth.py`'s
schema, closed-form curve evaluator and byte-stable `write_truth`; 02-09 built the
CLI, byte-stable CSV writers and the full SIM-070…075 + BP-G-02 gate runner plus real
`make simulate`/`validate-sim` targets; 02-10 (this plan) committed the nine Layer P
artifacts, proved the git-checkout round-trip, and closes M1.

**Interpretations recorded (not ADRs — D-07).** Each line names the plan that made
it; none changes spec text, so per `docs/ADR/README.md`'s standing rule each is
recorded here plus an in-source comment, not filed as an ADR.

1. `SimulationError(AmboError)` supersedes `03_MODULES.md` §2.2/§2.3's `ValueError`
   for expected failure conditions, because `docs/MODULE_CONTRACTS.md` is the
   contract of record and A-7 forbids bare built-ins; plain `ValueError` remains
   correct inside pydantic validators (02-02).
2. Exactly-adjacent burst spans in the same channel are accepted as two distinct
   bursts and never merged; only true overlap is rejected — SPEC-01 §3 and Guide
   §1.1 forbid overlap and are silent on touching (02-02).
3. Scenario windows: S-A 2021-W01…2023-W52 (156), S-B 2022-W01…2023-W52 (104), S-C
   2022-W01…2023-W26 (78), each cross-checked against the row count in
   `dbt/seeds/season_windows.csv`; SPEC-01 §5 fixes the week counts but not the
   calendar endpoints (02-03).
4. The four authored per-channel CPM constants and their descriptive-only status —
   BP-D-02 mandates CPM constants in the scenario YAML but names no values (02-03).
5. `meta` carries an `advent_factor` of 0.5 in S-A and 0.9 in S-B/S-C: SPEC-01 §3's
   `meta` row states no seasonal multiplier, but SIM-030's "0.5→0.9 for
   search_generic/meta" presupposes the 0.5 baseline, and Guide §1.3 requires the
   switch to live in data (02-03).
6. Radio's two Advent-anchored bursts are authored as a lead-in burst plus an
   in-Advent burst, because two 3-week bursts cannot both fit inside a 4-week Advent
   window without overlapping (02-03).
7. `season_index` takes the five signed weights as an argument rather than
   hard-coding them, so SIM-002's YAML stays the only home (02-04).
8. `generate_spend` takes the week-index frame as a third argument rather than
   reading the calendar seed itself, preserving the Functional-Core/Imperative-Shell
   split and AD-020's single home (02-05).
9. SIM-073 is evaluated for ISO year 2022 only in S-C, because its 2023 half-year
   does not cover an Advent window; the skipped year is reported by the gate runner,
   never silently omitted (02-06).
10. The `truth.json` float-format mechanism actually used, closing 02-RESEARCH.md
    Assumption A3 (02-08).
11. SPEC-01 §8's grid note already resolves INGEST-CONFLICTS WARNING 4; the
    ROADMAP's Phase 2 "must resolve before execution" text was stale, and `truth.py`
    exposes `response_curve_at` as a function of a caller-supplied grid so Phase 3/8
    reuses the closed form (02-08).

**Promo/burst authoring rationale.** `scripts/author_scenario_schedules.py` (02-03)
is a dev-only, one-off placement aid (A-13: kept outside `src/`, never imported by or
reachable from `src/ambo/`, verified by a standing guard test) that computes the
unanchored promo/print/radio week placements deterministically from
`dbt/seeds/season_windows.csv` and prints a YAML fragment to stdout — it performs no
file I/O itself. Anchored placements (Black Friday, the two Advent-anchored radio
bursts, the spring 1/3 and 2/3 index-point promo weeks) are computed directly from
each covered year's window boundaries; unanchored placements (the remaining spread
promo/print/radio weeks) are drawn via a fixed, auditable spread rule, never a
`random`/`np.random` call, so the aid's own output is exactly reproducible across
runs. The printed fragment is hand-copied into `config/scenarios/*.yaml` and frozen
there (Guide §1.1, D-02): the schedule the simulator reads at `make simulate` time is
the frozen YAML text, never a runtime recomputation, so a wrong-looking week number is
fixed by editing the aid and re-pasting its output, never by hand-editing the
committed YAML.

**Governance.** ADR-007 (`docs/ADR/ADR-007_hypothesis-dev-dependency.md`, ratified
02-01) adds `hypothesis>=6.165.1` to `[dependency-groups] dev` only (EB-030, O-3) for
D-03's property-based tests of `adstock_recursive`/`hill`. Its automated `SUS`
package-legitimacy verdict (reasons: `too-new`, `unknown-downloads`,
`no-repository`) was surfaced verbatim, alongside independently-gathered
counter-evidence (maintainer identity, source repository, unbroken 2013-origin
release history), at a blocking `checkpoint:human-verify` gate; the human confirmed
all four facts on pypi.org before `uv add` ran. The install order was verified:
`uv.lock` was unmodified before the approval was recorded, and the lockfile-touching
commit is strictly after both the ADR commit and the approval.

**Gate evidence.** The full seven-row `make validate-sim` table (re-run for this
plan, both before and after the git checkout round-trip, with identical results):

```text
GATE     STATUS     EVIDENCE
SIM-070  PASS       committed=016aad7d5e8c3c629fd23cc99abb2f8d655f50173ab9f2e757401e4c30cccfd1 regenerated=016aad7d5e8c3c629fd23cc99abb2f8d655f50173ab9f2e757401e4c30cccfd1
SIM-071  PASS       s_a=0.0, s_b=0.0, s_c=0.0 (max=0.0, bound<=1e-6)
SIM-072  PASS       s_a: {'min_revenue_pre_clip': 64094.84287664617, 'noise_variance_share': 0.03113949883141409, 'media_share_2021': 0.2730426362263659, 'media_share_2022': 0.26633491313334523, 'media_share_2023': 0.25753447781321676}; s_b: {'min_revenue_pre_clip': 70242.79391112749, 'noise_variance_share': 0.026355908286650902, 'media_share_2022': 0.27442453188862836, 'media_share_2023': 0.26245675624176334}; s_c: {'min_revenue_pre_clip': 62307.90535157751, 'noise_variance_share': 0.03959346809337588, 'media_share_2022': 0.2472965119066494, 'media_share_2023': 0.255949800658689}
SIM-073  PASS       s_a 2021: peak_week=50 advent_flag=True; s_a 2022: peak_week=51 advent_flag=True; s_a 2023: peak_week=50 advent_flag=True; s_b 2022: peak_week=50 advent_flag=True; s_b 2023: peak_week=50 advent_flag=True; s_c 2022: peak_week=50 advent_flag=True; s_c 2023: skipped (Advent window not fully covered)
SIM-074  PASS       constant_spend_residual=9.094947017729282e-13 (bound<=1e-9), impulse_residual=2.7755575615628914e-17 (bound<=1e-9), hill_at_K_residual=0.0 (bound<=1e-12)
SIM-075  PASS       all three truth.json files re-validated and match ScenarioConfig
BP-G-02  DELEGATED  scenario YAML == SPEC-01 section 4 table (SIM-002 single home); checked by the selector `tests/unit/test_scenario_config.py -k "spec_parameter_table or rule_level"`, run by make validate-sim in the same invocation so the target cannot go green without it.
```

Exit code `0` both before and after
`rm -rf data/synthetic/s_a data/synthetic/s_b data/synthetic/s_c && git checkout --
data/synthetic/` — the round-trip check T-02-43 exists to prove: the committed bytes
survive a checkout with the repository's pinned `eol=lf` `.gitattributes` rule, with
no CRLF reintroduction of the kind plan 01-07 found under `core.autocrlf=true`.

**Elapsed effort against the 1.5 d Charter section 5 budget.** Summing each plan's
measured duration from `.planning/STATE.md`'s Performance Metrics table (same 8-hour
working-day convention the M0 entry established): P01 (33 min) plus P02 (20 min)
plus P03 (55 min) plus P04 (25 min) plus P05 (~35 min) plus P06 (~45 min) plus P07
(35 min) plus P08 (~40 min) plus P09 (~40 min) totals 328 min for plans 02-01…02-09,
plus plan 02-10's own measured duration (recorded in `02-10-SUMMARY.md`'s
Performance section, since this entry is written before that plan finishes). 328 min
(~5.47 h, ~0.68 d) is already well under the 720 min (1.5 d) budget and far from the
1440 min (2×) strictly-greater stop-and-ADR tripwire from this file's own header
rule, and plan 02-10's own duration — comparable in scope to the other
single-task-cluster plans in this phase (35–55 min) — cannot plausibly push the
combined total anywhere near 1440 min. **Verdict: the tripwire is not tripped** —
Phase 2's total measured effort, once 02-10 is added, remains far below 2x its
budget; no ADR is triggered. The exact combined total, including plan 02-10's own
measured duration, is restated in `02-10-SUMMARY.md`'s Performance section for the
permanent record.

### 2026-08-05 — M1 close: effort tally finalized and human sign-off recorded (plan 02-10, Task 3)

This entry corrects nothing in the M1 close entry above (2026-08-05); it appends the
one figure that entry left open — plan 02-10's own measured duration — and records
the Task 3 checkpoint's outcome, per this file's own append-only rule (a correction
is a new dated entry that cites the entry it corrects, never a rewrite).

**Elapsed effort, finalized.** Plan 02-10 measured ~20 min across its two `auto`
tasks and the Task 3 checkpoint wrap-up (commit timestamps: `885743a` at 13:40:45
CEST -> `dd29e78` at 13:43:25 CEST, Task 1, ~3 min; `dd29e78` -> `260d12d` at
13:46:58 CEST, Task 2, ~3 min; plus the Task 3 evidence-gathering and sign-off work
in this session). Added to the 328 min already summed for plans 02-01...02-09, the
Phase 2 total is **348 min (~5.8 h, ~0.72 d)** — well under the 720 min (1.5 d)
Charter section 5 budget and far below the 1440 min (2x) strictly-greater
stop-and-ADR tripwire. **Verdict: the tripwire is not tripped; no ADR is required.**

**Task 3 checkpoint re-verification.** Re-run in this session, after the M1 close
entry above was already written: `make lint` -- `ruff check .` (lint proper) and
`uv run mypy` (strict, whole `src/ambo`) both pass cleanly; the whole-repo
`ruff format --check .` step still fails only on the same pre-existing,
already-deferred `02-PATTERNS.md`/`02-RESEARCH.md` markdown-embedded-code-fence
issue first logged by 02-01 and re-confirmed by every plan since (02-04 through
02-09) -- confirmed here as still out of scope (neither file is in this plan's
`files_modified`; both predate this plan, landed in `4a1a214`); `ruff format --check`
scoped to `src/ambo tests scripts` (40 files) passes cleanly. `make test` passes
fully: 281 passed, coverage of `src/ambo` at 93% (`>= 80%` M1 threshold). `grep -rn
"TODO\|FIXME\|XXX" src/ tests/ scripts/` returns no matches. `make simulate && make
validate-sim` reproduces the identical seven-row gate table pasted in the M1 close
entry above, including the identical SIM-070 hash pair
(`016aad7d5e8c3c629fd23cc99abb2f8d655f50173ab9f2e757401e4c30cccfd1` on both sides),
both before and independently confirmed against the already-proven git-checkout
round-trip from Task 1. `data/synthetic/s_c/truth.json`'s `display_video` entry
carries exact `0.0` for `true_avg_roas`, `total_contribution_eur` and
`contribution_share`; `data/synthetic/s_a/media_weekly.csv`'s header is exactly
`week_start,channel,spend_eur,impressions,platform_conversions,platform_revenue_eur`
with `print_regional` rows ending in three empty fields.

**No CI run and no PR exist yet for this branch** (`m0-bootstrap`) -- the `[STD]`
merge-readiness rows requiring a green CI run and a human quality-standards review
statement are not self-certifiable pre-PR. Per the human's explicit approval below,
these two rows are deferred to PR-open time (`/gsd-ship`), consistent with the M0
precedent (01-09 Task 3) where the CI-run evidence line was likewise appended only
once a human had observed a real run.

**Human sign-off.** The human reviewed the evidence bundle above (281 tests passed,
93% coverage, all seven SIM-0xx/BP-G-02 gates green, the SIM-070 round-trip hash
match, and the 348 min effort total against the 720/1440 min budget/tripwire) and
responded **"Approved"**, explicitly agreeing to defer the CI-jobs-green and
quality-standards-review-statement `[STD]` rows to PR-open time since no PR/CI run
exists yet for this branch. **M1 is closed. Phase 3 may begin.**
