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
| T-003 AC-1 | Tree diff vs SPEC-08 §2 is empty (allowing not-yet-created source files) | `ls` at repo root shows only `.gitignore`, `.git/`, `.planning/`, `AGENTS.md`, `PROJECT_CHARTER.md`, `docs/`. None of `README.md`, `LICENSE`, `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`, `.env.example`, `config/`, `src/ambo/`, `dbt/`, `scripts/`, `data/`, `exports/`, `reports/`, `dashboards/`, `tests/` exists yet | FAIL | 01-02 Task 3 |
| T-003 AC-2 | Ignore rules proven by validation probe | `touch data/warehouse/x.duckdb exports/foo.csv && git status --porcelain`: `data/warehouse/x.duckdb` does not appear (ignored, correct); `exports/foo.csv` appears as untracked (`?? exports/`) — correct per the W5 ingest resolution, which committed `exports/*.csv` by design rather than gitignoring it (SPEC-08 §2, EB-081). Probe files deleted immediately after the check; nothing was staged | PASS | — |
| T-003 AC-3 | LICENSE = MIT with author line matching Charter header | `ls LICENSE` — no such file | FAIL | 01-02 Task 3 |
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

---

## 2026-09-15 — Stage 2+ pipeline on the rebuilt package (ADR-012)

After Stage 1 landed on `main`, the stacked GSD PRs were closed as superseded
(STATUS.md salvage record). This entry records the flat-package continuation:

- `ambo.synth` — independent geometric recursion + Hill; five-channel Layer P
  (D-05); platform over-credit (SIM-060); committed `data/synthetic/` via
  `python -m ambo.run simulate`.
- `ambo.model` — scaled additive-in-level MMM, non-centred Fourier, one holiday
  control, nutpie primary (D-08).
- `ambo.evaluate` / `baselines` / `optimize` / `report` — recovery observables,
  OLS+HC1, SLSQP with 1.3× cap, HDI-bearing artifacts.
- `ambo.data.load_layer_r` raises (A-5, Charter §7). Deviation ADR: `docs/adr/ADR-012_five-channel-layer-p-and-charter-7.md`.

---

## 2026-09-15 — VR-310 calendar + MD-020 normalised adstock

Layer P identification, two focused attempts, gates not widened:

1. **Calendar (VR-310 #1 / SPEC-04 §2).** Promo, Advent, and January-dip
   dummies added to the linear predictor (plus D-07 holiday). MD-073 rung 1:
   `target_accept=0.95` after 53 divergences at 0.9. Local 4×1000 nutpie fit
   went MD-071 all-green (0 divergences). Recovery stayed RED on VR-302/303/305
   (search half-life outranked TV; print curve MAE 50%).
2. **MD-020 (VR-310 #2).** Model / evaluate / OLS / optimiser now share
   unit-sum truncated weights (`ADSTOCK_NORMALIZE=True`). Simulator recursion
   is unchanged (SIM-003). `bk_theme.apply("light")` positional call (D-07).
   ADR-012 amendment records the closed calendar deviation.

Full `python -m ambo.run layer_p` after this entry regenerates reports from a
posterior that matches the normalised graph. Recovery all-green is not claimed
until that report says so.

---

## 2026-09-15 — MD-073 rung 4 (ADR-013)

The MD-020 4×1000 nutpie fit was RED on MD-071: **1 divergence** (chain 3,
draw 423) at low search `K` with `s ≈ 1.53`. Rungs 1–3 of the ladder were
already applied (target_accept 0.95, non-centred Fourier, tight s prior).
Rung 4 fixes `s_c = 1` (logistic saturation). Recovery gates are not widened.
See `docs/adr/ADR-013_hill-slope-fixed.md`.

---

## 2026-09-15 — ADR-014: rung 4 rolled back

The `s_c = 1` 4×1000 fit produced 3 divergences (worse than the 1-divergence
MD-020 sampled-`s` graph) and the same RED recovery (Spearman 0.600).
Rung 4 is reverted. Identification attempts stop here (AGENTS §2). The
reported model is MD-020 + calendar + sampled s + target_accept 0.95.
MD-071 and recovery gates are not widened.

---

## 2026-09-15 — Layer P reports committed (honest RED)

`python -m ambo.run layer_p` on the ADR-014 graph wrote `reports/` from a
4×1000 nutpie posterior (seed 42). `posterior.nc` is gitignored;
`data/synthetic/scale_factors.json` is committed so reports can be
regenerated with a local netCDF. Attribution-gap export omits offline
channels (no platform dashboard). `layer_p` exits 1 unless both MD-071 and
recovery are all-green.

Measured: MD-071 1 divergence; recovery VR-301/306 PASS, VR-302/303/305
FAIL; holdout MAPE 0.0418 vs naive 0.0784; gain HDI crosses zero.
