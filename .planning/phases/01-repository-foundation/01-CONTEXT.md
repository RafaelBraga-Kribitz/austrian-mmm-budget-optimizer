# Phase 1: Repository Foundation - Context

**Gathered:** 2026-08-04
**Status:** Ready for planning

<domain>
## Phase Boundary

A clone-and-run engineering shell where the quality bar, the scope walls, and the governance
mechanisms all exist and are enforced before a single line of science is written.

Scope is WBS tasks **T-001…T-012** (`docs/EXECUTION_BLUEPRINT/02_WBS.md`, Phase P0 section):
git baseline, Python/uv scaffold with pinned deps, repository skeleton, settings + logging,
Makefile, lint/type/pre-commit toolchain, leak scan, six-job CI, test scaffold with
architectural guard tests, season-windows seed, governance scaffold.

**Zero science code.** No simulator, no model, no dbt models, no scripts that compute anything.

### Corrections to upstream documents applied during this discussion

1. **`docs/EXECUTION_BLUEPRINT/` was missing from disk.** STATE.md claimed the files remained
   on disk after being gitignored on 2026-08-04; they did not. All 14 were restored from commit
   `1851f39` during this discussion (untracked, gitignored). See D-01.
2. **ROADMAP.md's Phase 1 "must resolve before execution" block is stale.** INGEST-CONFLICTS
   WARNING 3 was resolved at source in commit `ffce015` — SPEC-08 §2 now reads "canonical" not
   "exact", includes all four contract modules, and the `06_CHECKLISTS [STD]` item was reworded.
   Do not re-litigate it.
3. **The branch question in that same block is stale.** The repo is on `main` and the
   documentation-only baseline commit `1851f39` already exists, so Success Criterion 3 is
   already satisfied.

</domain>

<decisions>
## Implementation Decisions

### Blueprint access and document promotion

- **D-01:** `docs/EXECUTION_BLUEPRINT/` (14 files) is **restored to disk and stays gitignored**.
  Done during this discussion via `git checkout 1851f39 -- docs/EXECUTION_BLUEPRINT/` followed by
  unstaging; `git status` is clean. Commit `1851f39` remains the **canonical** version — the
  working copy is a read surface, not an edit surface. Do not commit these files.
- **D-02:** Module contracts are **promoted to a tracked `docs/MODULE_CONTRACTS.md`**.
  `03_MODULES.md` gets an unmissable superseded-as-of-Phase-1 header and is never edited again;
  it remains the design input for contracts not yet written. `MODULE_CONTRACTS.md` is the
  contract of record for what exists.
- **D-03:** `MODULE_CONTRACTS.md` is **grow-as-you-go**. Phase 1 writes the header (the
  contract-first rule and the entry format) plus entries only for what Phase 1 ships:
  `src/ambo/common/config.py` and `src/ambo/common/logging.py`. Every later PR adds its own
  entry, so SPEC-08 §2's same-PR rule is an observable addition rather than a flag flip.
- **D-04:** **Standing rule: no published document may cite an unpublished one.** Two known
  violations are deferred with named owners — the normative fit ceiling
  (`07_QUALITY_STANDARDS` Part A, cited by SPEC-08 §5) moves into `config/settings.yaml` in
  **Phase 4**; the DL-1 release probe (`11_ACCEPTANCE_CRITERIA` §4, cited by SPEC-08 §5,
  Charter DL-1 and ADR-000) gets a tracked home in **Phase 9**. ADR-006 carries this list.

### Governance and ADR policy

- **D-05:** Phase 1 writes **ADR-006**. It covers, in one document: the SPEC-08 §2 repoint at
  `docs/MODULE_CONTRACTS.md`; the SPEC-08 §2 layout additions (D-14); the D-04 standing rule
  with its two deferred items; and the D-18 commit-history note. Reserved slots ADR-001…005
  stay open for their GB-202 topics (permission outcome, channel mapping, anonymization recipe,
  Layer R window, sampler reparameterization).
- **D-06:** **Every spec edit gets its own ADR, from here on.** This is the standing bar.
- **D-07:** **Interpretations are not edits.** When a spec's text stands unchanged and the work
  fills a gap the spec left open — e.g. T-011 reading SPEC-01 §2.1's "around Styrian school
  start" as "second Monday of September" because the `holidays` package has no AT-6 school data
  — the record is a `docs/BUILD_LOG.md` entry plus an in-script source comment, exactly as
  T-011 already specifies. An ADR is owed when spec text changes or a gate moves.
- **D-08:** **`docs/RISK_REGISTER.md` is tracked and seeded in Phase 1**, satisfying
  REQ-risk-register with a reviewable artifact. `12_RISK_REGISTER.md` is frozen alongside
  `03_MODULES.md`. Seed with R-1…R-9 plus this finding, discovered during the discussion:
  *no C compiler (`g++`) on the Windows dev machine; PyTensor falls back to the NumPy backend;
  threatens the ≤35 min/fit ceiling and the ~14-fit compute ledger; owner Phase 4; detection =
  a compiler check in `make setup`.*
- **D-09:** T-012's ADR template moves to **`docs/ADR/TEMPLATE.md`** — the WBS specifies
  `docs/ADR/ADR-000_template.md`, but `ADR-000` is already taken by the precedence ADR. The
  `ADR-NNN_` prefix is reserved for real ADRs.

### Branch, PR and history mechanics

- **D-10:** **Full PR ceremony now; enforcement at M3.** GitHub returns HTTP 403 for both
  `branches/main/protection` and `rulesets` on this private free-tier repo ("Upgrade to GitHub
  Pro or make this repository public"), so EB-080's protection is not achievable until
  go-public. Add **"enable branch protection with all six required checks"** to the existing
  M3 go-public checklist in STATE.md.
- **D-11:** **Milestone branches, phase commits.** One branch per milestone — `m0-bootstrap`,
  `m1-simulator`, `m2-warehouse-model`, … — phases commit into it, and the PR opens when the
  milestone exit gate is green. M2 spans Phases 3 and 4 on a single branch.
- **D-12:** **Squash and rebase merge are disabled on the repo.** Applied during this discussion
  (`allow_squash_merge=false`, `allow_rebase_merge=false`, `allow_merge_commit=true`). Repo
  settings are not Pro-gated the way protection is. The merge button now physically cannot
  destroy the task-level commit trail EB-082 and the layer-order argument depend on.
- **D-13:** **Push `main` first, then cut `m0-bootstrap`.** `origin/main` is 2 commits behind
  local — `ffce015` (the seven-warning resolution + ADR-000) and `151d32b` (the M3 checkpoint)
  are local-only. They are already on `main` and relocating them would require history
  rewriting, which EB-082 forbids. After this push, `main` only ever advances by merge commit.
- **D-18:** ADR-006 notes that commits `1851f39`…`151d32b` predate the EB-080 commit convention,
  that EB-082 forbids fixing them, and that conformance begins with the first `m0-bootstrap`
  commit. The format itself is already specified and is **not** a decision to make:
  `07_QUALITY_STANDARDS` line 113 fixes it as
  `feat|fix|test|docs|chore|refactor(scope): message [REQ-IDs]`.

### CI design

- **D-15:** **Coverage blocks at M0 close.** `--cov-fail-under=80` lands non-failing in T-002
  and flips to blocking as part of the M0 exit. Only `common/config.py` and `common/logging.py`
  are in scope (`scripts/` is outside `--cov=src/ambo`) and both ship with test suites from
  T-004/T-005. EB-072 states ≥80% flatly.
- **D-16:** **Phase-gated jobs pass by running, not by being skipped.** No `if: hashFiles()`
  guards — a skipped job reports as skipped, Success Criterion 2 forbids passing by absence, and
  a skipped check cannot satisfy a required-status rule once protection turns on at M3.
- **D-17:** Those scripts are **vacuously-correct real checks, not stubs.**
  `scripts/check_layer_order.py` implements the actual predicate now (scan history for Layer R
  artifacts; none exist → green, and say so). `scripts/check_ssot_consistency.py` likewise (no
  `reports/NUMERIC_SSOT.md` → nothing to reconcile → green). Phase 5 **extends** them rather
  than replacing them, so placeholder rot is structurally impossible: the moment a Layer R
  artifact appears, the check has real work and does it. Job 3 (dbt) gets the same treatment via
  its make target.
- **D-19:** **CI triggers are `push: [main]` + `pull_request: [main]`**, with the milestone PR
  opened as a **draft at milestone start** so `pull_request` fires on every subsequent push to
  the branch — continuous CI with no duplicate runs. Add a `concurrency` group that cancels
  superseded runs. No cron, ever (Charter O-7). `fetch-depth: 0` on jobs 5 and 6 per BP-D-13.
- **D-20:** **The season-windows seed is diff-checked in job 1 (lint).** Regenerate
  `dbt/seeds/season_windows.csv` and fail on any `git diff`. Job 1 already has Python and no
  heavy dependencies, so this costs seconds and adds no job — EB-060's six stay six. The seed is
  AD-020's single calendar and the only sanctioned shared input across the W-2 simulator↔model
  firewall; silent divergence there would be the hardest bug in the project to attribute.

### Windows parity and correctness

- **D-21:** **Matrix the test job across `ubuntu-latest` and `windows-latest`.** The job *name*
  stays `test`, so EB-060's six-job contract holds — it simply produces two check runs.
  `windows-latest` bills at 2× on private repos; budget accordingly against the 2,000 free
  minutes/month.
- **D-22:** **LF is pinned by a committed `.gitattributes`** — `* text=auto eol=lf`, explicit
  rules for `*.csv`, `*.py`, `*.yaml`, `*.md`, and `-text` for `*.parquet`, `*.png`, `*.pbix`.
  Local git config does not travel and would make reproducibility depend on the reviewer's
  setup. Add a test asserting no CRLF in tracked text files. **T-001 AC-2 is currently entirely
  unmet:** no `.gitattributes` exists, and `core.autocrlf` and `core.eol` are unset both locally
  and globally. SIM-070's byte-identical CSV gate in Phase 2 depends on closing this.

### Repository layout enforcement

- **D-14:** **SPEC-08 §2 is amended to list `.github/`, `.planning/`, `uv.lock` and
  `.gitattributes`.** All four are permanent and load-bearing; their absence is an authoring gap,
  not a rule. Recorded in ADR-006 (no separate ADR).
- **D-23:** **T-010 grows from three guard tests to four.** `tests/unit/test_repo_layout.py`
  asserts the real tree against SPEC-08 §2 with **no allowlist** (D-14 makes this possible), and
  fails on any `src/ambo/` module lacking a `docs/MODULE_CONTRACTS.md` entry. This makes the
  `06_CHECKLISTS [STD]` item machine-enforced rather than a box someone ticks — matching GB §8's
  stance that the governance showpieces are scripts a reviewer runs. The other three guards are
  unchanged: forbidden-deps (EB-030), simulate↔model import independence (SIM-003/W-2), and
  no-`requests` (EB-070).
- **D-24:** **`.github/pull_request_template.md` carries only the judgment items** the layout
  test cannot check — BUILD_LOG entry written, evidence attached, effort budget respected, ADRs
  filed, SSOT regenerated if any number changed. No duplication with the test. This gives
  standing rule 1's "checklist ticked in the PR with evidence" a literal home.

### Configuration, tooling and scanning

- **D-25:** **`config/settings.yaml` is authored whole in Phase 1**, per T-004: the 7-channel
  taxonomy in SPEC-02 §5.2 order (`search_brand`, `search_generic`, `meta`, `display_video`,
  `print_regional`, `radio`, `other`), adstock `L=8`, all paths, the MD-050 sampler block
  (4 chains, tune=1000, draws=1000, `target_accept=0.9`, `random_seed=42`,
  `init='jitter+adapt_diag'`), and the scenario registry. These are fixed spec constants, not
  guesses. Authoring them now makes T-004's grep assertion (`target_accept` appears nowhere but
  config) true from the moment PyMC code first exists. pydantic `extra='forbid'` therefore
  declares every key up front.
- **D-26:** **`scripts/leak_scan.py`'s M0 pattern subset is high-precision and path-scoped.**
  Three checks: (a) the resolved `AMBO_PRIVATE_DROP` path anywhere; (b) email / URL / person-name
  shapes only under `data/real_anon/` and `reports/ingestion/`; (c) bare currency literals only
  in notebooks, where nbstripout already runs. Everything else — a€ figures in `exports/`, € in
  docs — is **explicitly out of scope**, stated in the script header. A gate with near-zero
  false positives is one that is still trusted in Phase 6.

### Makefile

- **D-27:** T-006's loud-failing stub message is
  **`"NOT IMPLEMENTED — arrives in Phase N (see README §Roadmap)"`**, replacing the WBS's
  pointer at the now-gitignored `docs/EXECUTION_BLUEPRINT/01_PHASES.md`.
- **D-28:** **Phase 1 creates a minimal `README.md`** so that pointer resolves: title, a
  one-paragraph what-this-is, a `§Roadmap` table of the nine phases with status, and an
  under-construction note. `README.md` is in SPEC-08 §2's layout regardless. Phase 9 replaces the
  body wholesale per RB §6 — this is a scaffold, not an attempt at DL-10.

### Plan structure

- **D-29:** **The plan opens with an audit task.** T-001, T-003 and T-012 are each partly done.
  The audit checks every pre-existing artifact against its WBS acceptance criteria, writes the
  result to `docs/BUILD_LOG.md` as M0 evidence, and turns only the failures into tasks. Known
  state going in:

  | Task | Done | Not done |
  |---|---|---|
  | T-001 | baseline commit `1851f39` (doc-only), branch `main` | `.gitattributes` (AC-2), `m0-bootstrap` branch, commit message differs from the specified text |
  | T-003 | `.gitignore` (EB-081-shaped, plus a `docs/EXECUTION_BLUEPRINT/` line) | directory skeleton with `.gitkeep`, `.env.example`, LICENSE |
  | T-012 | `docs/ADR/` exists, ADR-000 ratified | template (→ `docs/ADR/TEMPLATE.md`), `docs/BUILD_LOG.md`, ADR README listing the five GB-202 slots |

### Claude's Discretion

- Exact `.gitattributes` rule set beyond the LF pin and the binary exclusions in D-22.
- Wording and section structure of ADR-006, `MODULE_CONTRACTS.md`, `RISK_REGISTER.md` and the
  PR template.
- Concrete regex forms for the three leak-scan pattern classes in D-26.
- How the audit task in D-29 reports (table in BUILD_LOG vs. per-task lines).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Task definitions and acceptance criteria (primary — read first)

- `docs/EXECUTION_BLUEPRINT/02_WBS.md` — **Phase P0 section, lines 19–262.** The T-001…T-012
  definitions: objective, rationale, prerequisites, outputs, dependencies, implementation notes,
  validation, acceptance criteria, traceability. This is the authoritative task-level contract
  for Phase 1. *Restored from commit `1851f39` per D-01; gitignored, so it will not appear in
  `git ls-files`.*
- `docs/EXECUTION_BLUEPRINT/01_PHASES.md` — P0 phase framing and the phase-independent standing
  rules.
- `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` — Guide §7 (leak scan, cited by T-008),
  Guide §9 (CI, cited by T-009), Guide §1.2 (season windows, cited by T-011).

### Binding engineering and governance specs (published)

- `docs/SPEC-08_engineering.md` — the core Phase 1 spec. §1 toolchain (EB-001/002), §2 canonical
  repository layout, §3 pinned dependency table with exact bounds (EB-030), §4 configuration and
  secrets (EB-040/041), §5 the 19-target Makefile interface (EB-050), §6 CI six-job contract
  (EB-060/061), §7 testing policy (EB-070…073), §8 git conventions (EB-080/081/082).
  **Being amended in this phase — see D-02, D-14, ADR-006.**
- `docs/SPEC-09_governance_quality.md` — GB-201 (ADR path template and required sections),
  GB-202 (the five reserved ADR slots), GB §8 (governance showpieces are scripts, not registries).
- `docs/ADR/ADR-000_document-precedence-and-blueprint-defaults.md` — **ratified.** D-1: precedence
  is *scoped*, not ranked — Charter governs goals/scope/acceptance, SPEC governs operative detail,
  ADR outranks both. D-2: BP-D-01…20 accepted wholesale.
- `PROJECT_CHARTER.md` — §2.2 out-of-scope O-1…O-8, §5 milestone effort budgets, §6 risks R-1…R-9,
  §7 degradation path.

### Standards, checklists and gates (internal, restored)

- `docs/EXECUTION_BLUEPRINT/07_QUALITY_STANDARDS.md` — line 103 the `Implements: <REQ-IDs>`
  docstring convention; line 113 the commit-message format; Part A the normative ≤35 min/fit
  ceiling (**deferred to Phase 4 for promotion — D-04**).
- `docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md` — the `[STD]` standing checklist. Its layout item
  becomes a test (D-23); its judgment items become the PR template (D-24).
- `docs/EXECUTION_BLUEPRINT/09_ANTI_PATTERNS.md` — §A-2 magic numbers, the rationale behind
  T-004's one-config-home rule.
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` — **being frozen in this phase (D-02).** Read it as
  the seed for `docs/MODULE_CONTRACTS.md`, then add the superseded header.
- `docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md` — **being frozen in this phase (D-08).** Seed
  for `docs/RISK_REGISTER.md`.
- `docs/EXECUTION_BLUEPRINT/11_ACCEPTANCE_CRITERIA.md` — §4 the DL-1 release probe
  (**deferred to Phase 9 for promotion — D-04**); §2.4 the Definition of Ready.

### Constants referenced by Phase 1 artifacts

- `docs/SPEC-04_mmm_model.md` — MD-050 sampler settings, needed verbatim by `config/settings.yaml`
  under D-25.
- `docs/SPEC-02_agency_data_pipeline.md` §5.2 — the fixed 7-channel taxonomy and its order,
  needed verbatim by `config/settings.yaml` under D-25.
- `docs/SPEC-01_ground_truth_simulator.md` §2.1 — the Austrian calendar window rules T-011
  encodes into `dbt/seeds/season_windows.csv`.

### Project-level context

- `.planning/PROJECT.md` — the eight unratified Group A design commitments, the constraint set,
  and the resolution table for W1–W7.
- `.planning/REQUIREMENTS.md` — REQ-dl8-quality, REQ-scope-in, REQ-scope-out, REQ-milestones,
  REQ-risk-register are Phase 1's five.
- `.planning/INGEST-CONFLICTS.md` — the resolution log for all seven warnings. Confirms none is
  carried into any phase.
- `.planning/intel/constraints.md` — 76 entries across 20 SPEC sources; the full technical
  contract, not restated in PROJECT.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

**There is no code.** The repository contains documentation only — zero `.py` files, no
`pyproject.toml`, no `Makefile`, no `.github/`, no `src/`, no `tests/`. Phase 1 writes the first
line of code in this project.

Two Phase-1 artifacts already exist as partial output and are inputs rather than work:

- `.gitignore` — already EB-081-shaped, with the correct committed-by-design list and **no**
  `exports/*.csv` line (correct post-W5). Carries one addition beyond EB-081:
  `docs/EXECUTION_BLUEPRINT/`. Verify, do not re-author.
- `docs/ADR/ADR-000_document-precedence-and-blueprint-defaults.md` — ratified. ADR-006 must not
  contradict it.

### Established Patterns

- **Governance by runnable artifact, not by checklist.** GB §8 states the showpieces are four
  scripts a reviewer can run. D-17, D-20 and D-23 all follow this: prefer a test or a script over
  a written rule wherever the rule is machine-checkable.
- **Single home for every fact.** EB-040 (one config home), E-4 (numeric SSOT), 09 §A-2 (magic
  numbers), and W6's resolution all express the same principle. D-02, D-08 and D-14 apply it to
  documents.
- **Append-only history is a deliverable.** EB-082. No force-push, no rebase, no amend, ever —
  including as a fix for a red gate. This constrains every remediation option in this phase.

### Integration Points

- **Toolchain verified present on the dev machine:** GNU Make 4.4.1 (ezwinports, native Win32),
  `uv` 0.11.29, Python 3.12.10, git 2.55.0.windows.2.
- **Toolchain gap:** no `g++`. Recorded in `docs/RISK_REGISTER.md` per D-08; Phase 4 owns it.
- **Repo:** `origin` → `github.com/RafaelBraga-Kribitz/austrian-mmm-budget-optimizer`, **private**,
  default branch `main`, merge-commit-only as of D-12.

### Open questions for research (not decisions)

1. **Makefile `SHELL` pin.** ezwinports make is a native Win32 build; it selects `sh.exe` or
   `cmd.exe` depending on PATH. BP-D-14 requires POSIX sh recipes, so `SHELL` needs an explicit
   value that resolves under both Git Bash and Linux. Find the portable form.
2. **Does `windows-latest` ship a usable `make`?** D-21's matrix leg depends on it. If not,
   determine the setup step (chocolatey, MSYS2, or `ezwinports` via winget).
3. **`uv` cross-platform lock.** T-002 AC-1 requires all SPEC-08 §3 packages resolvable with the
   stated bounds on both Windows and Linux from one `uv.lock`. Confirm `dbt-core`/`dbt-duckdb`
   and `pymc` co-resolve within those bounds before pinning.

</code_context>

<specifics>
## Specific Ideas

- **The vacuously-correct-check pattern (D-17) is the shape to reach for elsewhere in this
  phase.** Rather than writing a stub and a tripwire, implement the real predicate and let it be
  trivially satisfied. It cannot rot, it needs no expiry mechanism, and Phase 5 extends rather
  than replaces. Apply the same reasoning to job 3 and to anything else that must be "green with
  notice" at M0.
- **Prefer machine enforcement over the written rule every time the rule is checkable.** Three
  decisions in this discussion converted a written rule into a mechanism: D-12 (disable the
  squash button rather than remember not to press it), D-20 (diff-check the seed rather than
  trust idempotency), D-23 (test the layout rather than tick a checklist). Where the planner
  finds another such rule, that is the intended direction.
- **Effort budget is 0.5 d and standing rule 5 trips at 2×.** This discussion added six artifacts
  beyond the WBS — `docs/MODULE_CONTRACTS.md`, `docs/RISK_REGISTER.md`, `ADR-006`, `README.md`,
  `.gitattributes`, `.github/pull_request_template.md` — plus a fourth guard test and a seed
  diff-check. All are small and mostly prose, but the planner should sequence deliberately and
  flag early if the budget is at risk rather than discovering it at 2×.

</specifics>

<deferred>
## Deferred Ideas

- **Promote the normative fit ceiling** (`07_QUALITY_STANDARDS` Part A, ≤35 min/fit at MD-050 on
  4 cores) into `config/settings.yaml` — **Phase 4**, per D-04 and D-25's one-config-home rule.
- **Promote the DL-1 release probe** (`11_ACCEPTANCE_CRITERIA` §4) into a tracked document —
  **Phase 9**, per D-04. It is the first row of the G-REL release gate and is currently cited by
  Charter DL-1, SPEC-08 §5 and ADR-000.
- **Widen the leak-scan pattern set** when real data lands — **Phase 6**, alongside T-501…T-506.
  Recorded as a risk-register entry so it does not depend on memory (D-26).
- **Enable branch protection with all six required checks** — **M3 / Phase 5**, appended to the
  existing go-public checklist in STATE.md (D-10).
- **Resolve the `g++` / PyTensor compiler gap** — **Phase 4**, per D-08. Detection is a compiler
  check in `make setup`; the mitigation (MSVC Build Tools or m2w64) is Phase 4's call.
- **Not discussed, still open for Phase 1's planner or a later pass:** whether `make setup`
  should run `pre-commit install` for a reviewer who only wants to read the repo; the LICENSE
  author line's exact form given the anonymization posture; how the 0.5 d effort tripwire is
  measured in practice.

</deferred>

---

*Phase: 1-repository-foundation*
*Context gathered: 2026-08-04*
