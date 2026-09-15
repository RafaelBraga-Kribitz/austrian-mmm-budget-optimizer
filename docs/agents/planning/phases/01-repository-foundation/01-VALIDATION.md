---
phase: 1
slug: repository-foundation
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-04
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `01-RESEARCH.md` § Validation Architecture.

**Phase 1 is the phase that builds the test infrastructure itself.** Every "gap" below is
the shape of a T-00x task, not a deficiency to remediate separately. Wave 0 is therefore
unusually large by design.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 — **not yet installed**; T-002 installs it, T-010 builds the scaffold |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — created by T-002 |
| **Quick run command** | `make test` (skips `@pytest.mark.smoke` locally unless `SMOKE=1`, per SPEC-08 §6) |
| **Full suite command** | `SMOKE=1 make test` locally; CI job 2 (`test`) always runs the smoke marker |
| **Estimated runtime** | ~10–30 seconds (no science code in this phase; all tests are guards, config and seed checks) |

Coverage: `--cov=src/ambo --cov-fail-under=80` lands **non-blocking** in T-002 and flips to
blocking at M0 exit (D-15). Only `common/config.py` and `common/logging.py` are in `--cov`
scope; `scripts/` is deliberately outside it.

---

## Sampling Rate

- **After every task commit:** `make lint` (seconds) + targeted `pytest tests/unit/test_<module>.py -x`
  for whatever T-00x just landed.
- **After every plan wave:** `make lint && make test` (full non-smoke suite).
- **Before `/gsd-verify-work`:** full suite green, and CI `ci.yml` all six jobs green on
  `m0-bootstrap` before the milestone PR is marked ready-for-review (D-11).
- **Max feedback latency:** 30 seconds locally; CI smoke job budget <15 min (T-009 AC-2).

**Sequencing constraint:** T-004 and T-005 are the only modules inside `--cov` scope, so they
must land before coverage is treated as a phase-gate criterion (D-15).

---

## Per-Task Verification Map

Plan and wave columns are filled by the planner; task IDs below are WBS tasks (T-00x) plus the
discussion-added deliverables. `File Exists` is ❌ W0 for everything — this phase creates the
test tree.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T-002 AC-1 | TBD | TBD | REQ-dl8-quality | — | N/A | CI | `uv sync` green on **both** matrix legs (ubuntu + windows) | ❌ W0 | ⬜ pending |
| T-003 | TBD | TBD | REQ-dl8-quality | — | Ignored paths never staged | unit | `pytest tests/unit/test_gitignore.py -x` (convert WBS manual probe to a test) | ❌ W0 | ⬜ pending |
| T-004 AC-2 | TBD | TBD | REQ-dl8-quality | T-1-01 | Config is the single home for constants | unit | `pytest tests/unit/test_config.py -x` (assert `target_accept` appears nowhere but config) | ❌ W0 | ⬜ pending |
| T-005 AC-1 | TBD | TBD | REQ-scope-out | T-1-02 | Private paths redacted from logs | unit | `pytest tests/unit/test_logging.py -x` | ❌ W0 | ⬜ pending |
| T-006 AC-2/3 | TBD | TBD | REQ-dl8-quality | — | Stub targets exit non-zero | CI | both `test` matrix legs green + `make -n <target>` | ❌ W0 | ⬜ pending |
| T-007 | TBD | TBD | REQ-dl8-quality | T-1-03 | Fake-key probe is blocked pre-commit | manual + CI | `pre-commit run --all-files`; fake-key probe on a scratch branch, **not** committed | ❌ W0 | ⬜ pending |
| T-008 | TBD | TBD | REQ-scope-out | T-1-04 | Leak scan catches all 3 pattern classes | unit | `pytest tests/unit/test_leak_scan.py -x` | ❌ W0 | ⬜ pending |
| T-009 AC-1/2 | TBD | TBD | REQ-dl8-quality | — | Six jobs required; smoke <15 min | CI | observe `ci.yml` run — all six green, none skipped (D-16) | ❌ W0 | ⬜ pending |
| T-010 (guard 1) | TBD | TBD | REQ-scope-out | — | Forbidden deps rejected (EB-030) | unit | `pytest tests/unit/test_forbidden_deps.py -x` | ❌ W0 | ⬜ pending |
| T-010 (guard 2) | TBD | TBD | REQ-scope-out | — | simulate↔model import independence (W-2) | unit | `pytest tests/unit/test_import_independence.py -x` | ❌ W0 | ⬜ pending |
| T-010 (guard 3) | TBD | TBD | REQ-scope-out | — | No `requests` (EB-070) | unit | `pytest tests/unit/test_no_requests.py -x` | ❌ W0 | ⬜ pending |
| T-010 (guard 4 / D-23) | TBD | TBD | REQ-scope-in | — | Repo tree matches SPEC-08 §2, **no allowlist**; every `src/ambo/` module has a MODULE_CONTRACTS entry | unit | `pytest tests/unit/test_repo_layout.py -x` | ❌ W0 | ⬜ pending |
| T-011 | TBD | TBD | REQ-dl8-quality | — | Season windows encode SPEC-01 §2.1 | unit | `pytest tests/unit/test_season_windows.py -x` + job 1 seed diff-check (D-20) | ❌ W0 | ⬜ pending |
| T-012 / D-08 | TBD | TBD | REQ-risk-register | — | R-1…R-9 + g++ finding tracked with mitigation/fallback/detection | doc | `docs/RISK_REGISTER.md` exists and is reviewable | ❌ W0 | ⬜ pending |
| D-22 | TBD | TBD | REQ-dl8-quality | — | No CRLF in tracked text files | unit | `pytest tests/unit/test_line_endings.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Requirements with no programmatic test this phase** (recorded so the gap is explicit, not silent):

| Req ID | Why not automated here |
|--------|------------------------|
| REQ-milestones | Process rule (effort budgets, 2× stop-plus-ADR). Phase 1 seeds the mechanism via `docs/BUILD_LOG.md` entries; it does not test it programmatically. |
| REQ-scope-in | Partly doc-shaped — the `docs/MODULE_CONTRACTS.md` header (D-03) is the artifact. The machine-checkable half **is** covered, by guard 4 (D-23). |

---

## Wave 0 Requirements

- [ ] `uv add --dev pytest pytest-cov ruff mypy pre-commit nbstripout` — framework install (T-002)
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` block — T-002
- [ ] `tests/{unit,fixtures,golden}/` directory tree — T-010
- [ ] `tests/conftest.py` — seeded RNG fixture, tmp-path helpers — T-010
- [ ] `tests/unit/test_repo_layout.py`, `test_forbidden_deps.py`, `test_import_independence.py`, `test_no_requests.py` — the four guards (T-010 + D-23)
- [ ] `tests/unit/test_config.py`, `tests/unit/test_logging.py` — T-004 / T-005 acceptance criteria require them
- [ ] `tests/unit/test_leak_scan.py` — T-008
- [ ] `tests/unit/test_season_windows.py` — T-011

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fake-key pre-commit probe | REQ-dl8-quality (T-007) | Committing a real-shaped secret to prove the hook fires would poison append-only history (EB-082). Must stay off `main`. | Create a scratch branch, stage a fake key, confirm `pre-commit` blocks the commit, delete the branch. Never merge. |
| Guard tests fail on planted violations | REQ-scope-out (T-010) | Proving a guard *fails correctly* requires temporarily planting a violation. | On a scratch commit: add `import robyn`, confirm `test_forbidden_deps.py` goes red, revert. Record in `docs/BUILD_LOG.md`. |
| CI six-job contract | REQ-dl8-quality (T-009) | Only observable by running the real workflow on GitHub. | Push to `m0-bootstrap` with the draft PR open (D-19); confirm six checks report, **none skipped** (D-16). |
| Milestone effort-budget discipline | REQ-milestones | Human judgment against a 0.5 d budget with a 2× tripwire. | Record actual elapsed effort in `docs/BUILD_LOG.md` at phase close; stop and file an ADR if >1.0 d. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
