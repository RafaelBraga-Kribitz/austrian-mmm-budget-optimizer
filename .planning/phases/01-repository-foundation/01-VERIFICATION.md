---
phase: 01-repository-foundation
verified: 2026-08-04T22:15:00Z
status: gaps_found
score: 4/5 roadmap success criteria verified (1 currently failing on HEAD); 5/5 phase requirements satisfied
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "make setup && make lint && make test runs green on a fresh clone, on both Windows Git Bash and Linux (ROADMAP Success Criterion 1)"
    status: failed
    reason: >
      `make lint` currently fails on the checked-out HEAD (commit 8125640) because
      `uv run ruff format --check .` flags one file needing reformatting:
      `.planning/phases/01-repository-foundation/01-REVIEW.md`, which contains an
      embedded Python code fence (ruff 0.16.1 formats Python code blocks inside
      Markdown by default, and this repo's `[tool.ruff]` config has no
      `exclude`/`extend-exclude` for `.planning/`). This file was added by the
      code-review sub-agent's own output (commit 8125640, "docs(01): add code
      review report") — it is not a deliverable of any of the 9 execution plans
      and is not part of `files_modified` in any plan or summary. `ruff check .`
      and `uv run mypy` are both clean; only `ruff format --check .` fails, on
      this single file. CI proved the actual phase-work commit (3989259, the tip
      of plan 01-09's work, before the review report was added) fully green with
      "79 files already formatted" on both the ubuntu-latest and windows-latest
      legs (runs 30951615385 / 30951952211 / 30952418680). The regression was
      introduced by a later, out-of-plan commit, not by the phase's own
      engineering work.
    artifacts:
      - path: ".planning/phases/01-repository-foundation/01-REVIEW.md"
        issue: "Embedded Python code fence is not ruff-format-clean; breaks `make lint`/CI job 1 on the current tree"
    missing:
      - "Run `uv run ruff format .planning/phases/01-repository-foundation/01-REVIEW.md` to bring it into formatting compliance, OR add `.planning/` to `[tool.ruff] extend-exclude` in `pyproject.toml` (consistent with `.planning/` being GSD tooling state rather than project source, per ADR-006's D-14 layout addition) so future planning artifacts with embedded code cannot silently break the quality gate again."
---

# Phase 1: Repository Foundation Verification Report

**Phase Goal:** A clone-and-run engineering shell where the quality bar, the scope walls, and the
governance mechanisms all exist and are enforced before a single line of science is written.
**Verified:** 2026-08-04
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the roadmap contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `make setup && make lint && make test` runs green on a fresh clone, on both Windows Git Bash and Linux | ✗ FAILED (on current HEAD) | `make test` passes locally (75 tests, 95% coverage on scoped modules). `make lint` fails on HEAD: `ruff check .` passes, `mypy` passes, but `ruff format --check .` flags `.planning/phases/01-repository-foundation/01-REVIEW.md` (1 file would be reformatted, 79 already formatted). Root cause is a post-phase artifact (the code-review report), not phase code — see Gaps below. CI proved this criterion true, on both `ubuntu-latest` and `windows-latest`, at the actual final phase-work commit `3989259` (runs 30951615385, 30951952211, 30952418680 all green, `gh run view 30952418680` confirms all 7 check runs SUCCESS). |
| 2 | CI `ci.yml` runs all six required jobs and all six pass — phase-gated jobs pass with an explicit "nothing to check yet" exit, never by being absent | ✓ VERIFIED | `.github/workflows/ci.yml` parses to exactly `{lint, test, dbt, ssot, layer-order, leak}` (verified via `yaml.safe_load`); no job carries `if:`; no `schedule:`/`cron:` anywhere. `gh run view 30952418680 --json jobs` shows all 7 check runs (5 singleton + 2 `test` matrix legs) `conclusion: success`. `scripts/check_layer_order.py` and `scripts/check_ssot_consistency.py` both print explicit "nothing to check"/"nothing to reconcile" notices and exit 0 when run locally, matching CI's log output for those jobs. |
| 3 | Git history begins with a documentation-only baseline commit (charter + specs + blueprint, zero code) that every later commit descends from | ✓ VERIFIED | `git rev-list --max-parents=0 HEAD` = `1851f39`, message "chore: baseline commit — charter, agent playbook, SPEC-01..09, execution blueprint"; `git show --stat` on it lists only `.md` documentation files, zero `.py`/`.ipynb`. `git rev-list --count 1851f39..HEAD` = 53 (every subsequent commit descends from it). |
| 4 | `dbt/seeds/season_windows.csv` is committed with passing unit tests, so the simulator and dbt read one calendar (AD-020) | ✓ VERIFIED | File tracked, 471 lines (470 data rows + header), header matches the 8-column spec exactly. `uv run pytest tests/unit/test_season_windows.py -q` passes (part of the full green suite). |
| 5 | The two architectural guard tests exist and fail loudly when violated: forbidden dependencies (robyn, lightweight_mmm, prophet, sklearn) and simulate↔model import independence | ✓ VERIFIED | `tests/unit/test_forbidden_deps.py` and `tests/unit/test_import_independence.py` exist, pass (4 tests), and `docs/BUILD_LOG.md`'s T-010 AC-1 entry plus `01-07-SUMMARY.md` document planted-violation proofs (red-then-green) on a scratch branch that was deleted, never merged. Phase 1 actually shipped four guards (D-23 extended the WBS's two to four — repo-layout and no-network added) — a superset of this criterion, not a shortfall. `test_forbidden_deps.py` is deliberately import-scoped rather than `uv.lock`-scoped per the binding 01-02 human-checkpoint ruling (O-3 is import-scoped, not tree-scoped) — confirmed correct and documented in the module's own docstring. |

**Score:** 4/5 roadmap success criteria verified; 1 failing on the current tracked tree for a reason outside the phase's own plan-authored deliverables (see Gaps).

### Requirements Coverage (Phase 1's five REQ IDs)

| Requirement | Owning Plan(s) | Status | Evidence |
|---|---|---|---|
| REQ-dl8-quality | 01-01, 01-02, 01-04, 01-05, 01-06, 01-07, 01-08, 01-09 | ✓ SATISFIED (with the make-lint caveat above) | `make test` green (75 tests); `ruff check .` and `mypy` clean; CI green on the phase's actual final commit including the smoke-adjacent `test` job; coverage measured at 95% on the two modules in scope, gate present but intentionally non-blocking per D-15 (confirmed: `--cov-fail-under` commented out in both `addopts` and `[tool.coverage.report]`, the latter fixed mid-phase in `727de22`). |
| REQ-scope-in | 01-03, 01-07 | ✓ SATISFIED | Eight in-scope workstreams traced via `docs/MODULE_CONTRACTS.md`'s contract-first cross-check, mechanically enforced by `tests/unit/test_repo_layout.py` (3 module-contract entries match the 3 non-`__init__` modules shipped; guard proven to fail on a missing/duplicate/orphan entry per `01-07-SUMMARY.md`). |
| REQ-scope-out | 01-02, 01-04, 01-07, 01-08 | ✓ SATISFIED | O-1…O-8 excluded; `tests/unit/test_forbidden_deps.py` enforces O-3 at the import level (verified: `uv tree` shows `scikit-learn` present only transitively via `pymc-marketing`→`pymc-extras`, and the test correctly does not fail on it, per the ratified import-scope-not-tree-scope decision); single CI workflow with `grep -c cron` = 0 enforces O-7. |
| REQ-milestones | 01-01, 01-03, 01-05, 01-09 | ✓ SATISFIED | Eight milestones M0–M7 tracked in ROADMAP.md; `docs/BUILD_LOG.md` M0 section carries the D-29 audit, the strictly-greater-than-2x tripwire language, and the M0 close entry with real CI-run evidence and elapsed-effort accounting (~194 min / ~0.4 d against the 0.5 d budget — tripwire not tripped, consistent with the plan's own recorded arithmetic). |
| REQ-risk-register | 01-03, 01-09 | ✓ SATISFIED | `docs/RISK_REGISTER.md` tracked; all nine Charter risks R-1…R-9 present exactly once (`grep` count confirms 9 unique Charter IDs), 12 total rows (R-1…R-13, minus R-13 counted separately as struck through), zero empty mitigation/fallback/detection cells, R-13 closed with a build-log evidence reference and struck-through row rather than deleted. |

No orphaned requirements: all five phase requirement IDs declared in ROADMAP.md appear in at least one plan's `requirements:` frontmatter field, confirmed by grepping across all 9 `*-PLAN.md` files.

### Required Artifacts (spot-checked at all four levels: exists, substantive, wired, behaves)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/BUILD_LOG.md` | Append-only M0 audit + close log | ✓ VERIFIED | Tracked, header states append-only/correction/tie-break/tripwire rules, M0 section present with consolidated close entry incl. real CI run URLs |
| `.gitattributes` | LF pin, binary rules | ✓ VERIFIED | Tracked; `git check-attr` behavior consistent with claims (spot-checked via file content) |
| `docs/ADR/TEMPLATE.md` + `README.md` | GB-201/202 ADR mechanism | ✓ VERIFIED | Both tracked; TEMPLATE has 4 required section headings; README lists ADR-000 Ratified + 5 reserved slots |
| `pyproject.toml` / `uv.lock` | SPEC-08 §3 bounds, universal lockfile | ✓ VERIFIED | `pymc>=5.15,<6` present; `resolution-markers` count = 0 (universal); 134 packages resolved; no forbidden framework found via `uv tree` sweep |
| `src/ambo/common/{config,errors,logging}.py` | Typed settings, redaction filter | ✓ VERIFIED | Import clean, `mypy` success on 11 source files, `load_settings()` cached, unit tests pass |
| `config/settings.yaml` | Single config home | ✓ VERIFIED | 5 top-level blocks, channel order matches SPEC-02 §5.2 exactly, sampler block has 6 keys |
| `Makefile` | 18-target build interface | ✓ VERIFIED | `make transform` vacuously-correct (exit 0, notice); `make simulate` loud stub (exit 2, "NOT IMPLEMENTED — arrives in Phase 2"); `make all` fails fast without fitting (exit 2, names `fit-synthetic`) — all three behaviors reproduced live |
| `dbt/seeds/season_windows.csv` | Committed calendar | ✓ VERIFIED | 470 data rows, correct header, tracked |
| `scripts/leak_scan.py` | 3-mode leak scanner | ✓ VERIFIED (with 2 code-review findings, see below) | Exits 0 on clean tree; `--bogus-flag` behavior and `--full` blocklist-unavailable notice previously verified by 01-08/01-09; two real bugs found by CI were fixed in `2bb8b7c`/`60c3f04` (confirmed present in git history) |
| `.pre-commit-config.yaml` | 7 pinned EB-002 hooks | ✓ VERIFIED | `grep -c 'id:'` = 7, `grep -c 'rev:'` = 3 (non-local repos pinned) |
| `scripts/check_layer_order.py` / `check_ssot_consistency.py` | Real GB-501/502/301 predicates | ✓ VERIFIED | Both run live, print the exact "nothing to check"/"nothing to reconcile" notices and exit 0 |
| `.github/workflows/ci.yml` | Single 6-job workflow | ✓ VERIFIED | Only file under `.github/workflows/`; 6 job IDs confirmed via YAML parse; matrix + timeout-minutes: 15 present on `test` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full unit suite green | `uv run python -m pytest -q` | 75 passed, 95% coverage on scoped modules | ✓ PASS |
| `make test` | `make test` | 61 passed (smoke/fit deselected) | ✓ PASS |
| `make lint` | `make lint` | **FAILS** on `ruff format --check .` against `01-REVIEW.md` | ✗ FAIL (see Gaps) |
| Leak scanner clean-tree exit | `uv run python scripts/leak_scan.py` | exit 0, no findings | ✓ PASS |
| Governance checks vacuous-pass notices | `uv run python scripts/check_layer_order.py` / `check_ssot_consistency.py` | both exit 0 with explicit notices | ✓ PASS |
| Makefile stub/vacuous/guard behaviors | `make transform`, `make simulate`, `make all` | exit 0/2/2 respectively, exact expected messages | ✓ PASS |
| Forbidden-deps / import-independence guards | `uv run pytest tests/unit/test_forbidden_deps.py tests/unit/test_import_independence.py -q` | 4 passed | ✓ PASS |
| Real CI run, six job identities, none skipped | `gh run view 30952418680 --json jobs` | all 7 check runs `success` (5 singleton + 2 matrix legs) | ✓ PASS |
| mypy strict clean | `uv run mypy` | Success: no issues found in 11 source files | ✓ PASS |
| Coverage gate non-blocking (D-15) | `grep cov-fail-under pyproject.toml` (excluding comments) | 0 active occurrences, both flip points documented inline | ✓ PASS |
| uv.lock universal, no forbidden framework | `grep -c resolution-markers uv.lock`; `uv tree \| grep -Ei 'robyn\|lightweight\|meridian\|prophet'` | 0; no matches | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention exists in this project; the phase's own equivalent
"governance showpiece" scripts (`leak_scan.py`, `check_layer_order.py`, `check_ssot_consistency.py`)
were exercised directly above rather than through a probe harness. No conventional probes found via
`find scripts -path '*/tests/probe-*.sh'` (empty result).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/phases/01-repository-foundation/01-REVIEW.md` | 133, 177, 203, 253 | Unformatted embedded Python code fences (ruff-format) | Warning | Breaks `make lint` / CI job 1 on the current tree — see Gaps |
| `scripts/leak_scan.py` (per code review CR-01) | 117-139 | `.env.example` generic-shape carve-out + CI never sets `AMBO_PRIVATE_DROP` → a real path pasted into `.env.example` is never caught by CI's `leak` job | Warning | Documented, pre-existing design gap flagged by `01-REVIEW.md`; not a violation of any stated must-have (the plan only required the CI-safe subset + full-mode-absent notice, both of which work); recommend human decide whether to widen per the CR-01 fix suggestion |
| `src/ambo/common/logging.py` (per code review CR-02) | 66-88 | `PrivatePathFilter._redact` only redacts `str` `msg`/`args`; never touches `record.exc_info`/traceback text | Warning | `logger.exception(...)` or a non-`str` arg bypasses redaction; documented, pre-existing gap; not exercised at M0 (no code calls `logger.exception` yet) |
| `scripts/check_ssot_consistency.py` (per code review WR-01/WR-02) | 119-143 | Unit-symbol asymmetry (`×` vs `x`); Austrian comma-decimal parsing not supported | Info | Inert at M0 (no reconciled SSOT data exists yet); Phase 5 will need to fix before it becomes load-bearing |
| `scripts/check_layer_order.py` (per code review WR-03) | 59-61, 120-132 | Uncaught `CalledProcessError` on a root-commit edge case instead of the documented exit-code contract | Info | Untested edge case, not reachable at M0 |
| `tests/unit/test_config.py` (per code review WR-04) | 87-94 | One test's Windows-literal fixture doesn't exercise absolute-path resolution on POSIX (unlike its sibling test files, which were fixed) | Info | Test-quality gap, not a functional defect |

No `TBD`/`FIXME`/`XXX` debt markers found in any phase-modified file (`grep -rnE 'TBD|FIXME|XXX' src/ scripts/ tests/ Makefile pyproject.toml config/` returns nothing). No `TODO`/`HACK`/`PLACEHOLDER` markers either.

### Human Verification Required

None. All items above were resolved programmatically — either verified true by direct command
execution, or resolved to a concrete, evidenced gap.

### Gaps Summary

Phase 1's actual engineering work — every one of the nine plans' artifacts, the CI workflow, the
four architectural guards, the leak scanner, the two governance checks, and the governance
documents — is genuinely built, wired, and was proven green in real CI runs (30951615385 /
30951952211 / 30952418680, on both `ubuntu-latest` and `windows-latest`) at the actual tip of the
phase's work (commit `3989259`). Every plan-level `must_haves` claim spot-checked against live
command output in this verification matched the SUMMARY claims, with the exception of the two
already-known, already-fixed defects the orchestrator flagged in advance (the leak-scan
self-matching doc comment and the platform-asymmetry test bugs, both fixed in `2bb8b7c`/`a05d4ee`/
`60c3f04`, all three confirmed present in `git log`), and the D-15 duplicate-coverage-gate fix
(`727de22`, confirmed present).

The one real, currently-reproducible gap is that **`make lint` fails on the checked-out HEAD right
now** (commit `8125640`), because `.planning/phases/01-repository-foundation/01-REVIEW.md` — a
code-review report added by this verification pipeline's own sibling agent, not a deliverable of
any of the 9 execution plans — contains an embedded Python code fence that `ruff format --check .`
does not consider formatted. `ruff check .` and `mypy` are both clean; this is purely a
`ruff format` finding on one file. Because ROADMAP Success Criterion 1 says literally "runs green
on a fresh clone," and a fresh clone of the current tree reproduces this failure, the criterion is
false as of this exact commit, even though it was true — and CI-proven true on both platforms — at
the commit the phase's own plans actually produced.

This is a one-line, mechanical fix (reformat the one file, or exclude `.planning/` from ruff's
scan scope) and does not reflect any structural defect in Phase 1's delivered engineering shell.
Recommend closing it before shipping the milestone PR, but it does not call into question whether
the quality bar, scope walls, and governance mechanisms this phase built actually exist and work —
they do, and they were the ones that caught this.

---

_Verified: 2026-08-04_
_Verifier: Claude (gsd-verifier)_
