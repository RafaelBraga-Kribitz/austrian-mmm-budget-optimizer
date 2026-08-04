# Phase 1: Repository Foundation - Research

**Researched:** 2026-08-04
**Domain:** Cross-platform Python/uv engineering scaffold, Make-based build interface, GitHub Actions CI, lightweight governance-by-script
**Confidence:** MEDIUM (three priority questions answered with HIGH/empirical evidence; several supporting claims are WebSearch-only and marked LOW)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

D-01…D-29 in `.planning/phases/01-repository-foundation/01-CONTEXT.md` are all locked for this phase. The load-bearing ones for this research (full text lives in CONTEXT.md, not restated here):

- **D-14, D-16, D-17, D-19, D-20, D-21, D-22, D-25** — CI/repo-layout/config mechanics this research directly informs.
- **D-27, D-28, D-29** — Makefile stub message text, minimal README, and the audit-first plan opening.
- All other D-NN items (D-01…D-13, D-15, D-18, D-23, D-24, D-26) govern blueprint access, governance/ADR policy, branch/PR mechanics, and layout enforcement — the planner should read CONTEXT.md directly rather than rely on a research summary for these, since they are process/documentation decisions this research does not add technical evidence to.

**Binding constraints this research was scoped inside (verbatim from the task brief):**
- D-16: phase-gated CI jobs pass by RUNNING, not by being skipped. No `if: hashFiles()` guards.
- D-17: `scripts/check_layer_order.py` and `scripts/check_ssot_consistency.py` are vacuously-correct real checks, not stubs — implement the real predicate, which is trivially green today.
- D-19: CI triggers are `push: [main]` + `pull_request: [main]`; draft PR opened at milestone start; no cron ever; `fetch-depth: 0` on jobs 5 and 6.
- D-20: season-windows seed is diff-checked inside job 1 (lint) — no seventh job. EB-060's six stay six.
- D-21: `test` job matrixed over ubuntu-latest + windows-latest; job NAME stays `test`.
- D-22: LF pinned by committed `.gitattributes` (`* text=auto eol=lf`).
- D-25: `config/settings.yaml` authored whole now, pydantic `extra='forbid'`.
- EB-082: append-only history. No force-push, no rebase, no amend — ever, including as a fix for a red gate.

### Claude's Discretion

- Exact `.gitattributes` rule set beyond the LF pin and the binary exclusions in D-22.
- Wording and section structure of ADR-006, `MODULE_CONTRACTS.md`, `RISK_REGISTER.md` and the PR template.
- Concrete regex forms for the three leak-scan pattern classes in D-26.
- How the audit task in D-29 reports (table in BUILD_LOG vs. per-task lines).

### Deferred Ideas (OUT OF SCOPE)

- Promote the normative fit ceiling (`07_QUALITY_STANDARDS` Part A) into `config/settings.yaml` — Phase 4.
- Promote the DL-1 release probe (`11_ACCEPTANCE_CRITERIA` §4) into a tracked document — Phase 9.
- Widen the leak-scan pattern set when real data lands — Phase 6.
- Enable branch protection with all six required checks — M3 / Phase 5.
- Resolve the `g++`/PyTensor compiler gap — Phase 4.
- Not discussed, still open: whether `make setup` should run `pre-commit install` for a read-only reviewer (this research's secondary question 4 addresses it — see Common Pitfalls context and Assumptions A4); the LICENSE author line's exact form; how the 0.5 d effort tripwire is measured in practice.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-dl8-quality | `make test` green; ruff + mypy clean; CI green including smoke-fit; coverage ≥80% of `src/`. Release-commit CI run shows all six jobs green. | Validation Architecture section maps every T-00x deliverable to its test/CI proof; Pattern 2/3 resolve the two platform-parity risks (Windows make, cross-platform lock) that would otherwise silently fail this requirement's CI leg; Package Legitimacy Audit clears the dependency set feeding `make test`/`make lint`. |
| REQ-scope-in | Eight in-scope workstreams, each tracing to its owning SPEC and to at least one WBS task. | Architectural Responsibility Map + Recommended Project Structure show where Phase 1's slice of this traceability lives (`docs/MODULE_CONTRACTS.md`, D-02/D-03); no new research needed beyond confirming SPEC-08 §2 layout, which this research reproduces. |
| REQ-scope-out | O-1…O-8 excluded; forbidden-deps test enforces O-3 at dependency level; single CI workflow with no cron enforces O-7. | Don't Hand-Roll table + Standard Stack "Alternatives Considered" row confirm Robyn/Meridian/lightweight_mmm/model-averaging are correctly excluded from the resolved dependency set (verified — none appear in the empirical `uv.lock`); Code Examples' CI workflow has no `schedule:`/cron trigger, matching D-19. |
| REQ-milestones | Eight milestones M0–M7, each exiting only on its named gate; 2× budget trip triggers a stop plus an ADR. | Validation Architecture "Phase gate" row states the exact M0-exit criterion (all six CI jobs green, coverage gate flips per D-15); this research does not change the 0.5 d budget, it reduces the risk of the budget being consumed by the three priority unknowns now resolved. |
| REQ-risk-register | Nine charter-level risks R-1…R-9 remain authoritative, each with a named mitigation, reviewed at each phase entry. | Standard Stack "Note for RISK_REGISTER" (PyMC 6.0 proximity) and Pattern 3 "known risk" (pytensor/g++ NumPy-backend fallback, already D-08's seed) give the D-08 seeding task concrete, current evidence rather than assumption. |

</phase_requirements>

## Summary

Phase 1 has zero science-code risk — it is pure engineering scaffold — but carries real Windows/Linux parity risk because the sole developer machine is Windows and CI must matrix `ubuntu-latest` + `windows-latest` (D-21) against one committed `Makefile` and one `uv.lock`. The three priority questions in scope for this research are now resolved with concrete, plannable answers:

1. **Makefile `SHELL` pin** — `SHELL := /bin/sh` + `.SHELLFLAGS := -ec` is the correct single-Makefile-line answer. It works on Linux because `/bin/sh` is a literal path, and it works under Windows Git Bash because ezwinports/native-Win32 GNU Make falls back to a `PATH` search for the shell's basename when the literal path doesn't resolve as a Windows path — and Git's `sh.exe` is on `PATH` inside a Git Bash session.
2. **`windows-latest` does not ship GNU Make.** Confirmed absent from the runner-images toolset manifest. The `test` job's Windows leg needs an explicit `choco install make` step (Chocolatey is preinstalled on `windows-latest`), which should install the same ezwinports-lineage `make` already verified on the dev machine.
3. **`uv` cross-platform lock: no collision found.** An empirical `uv lock` run against the exact SPEC-08 §3 bounds resolved 112 packages in 1.4s into a single **universal** lockfile (wheels for win32/win_amd64/manylinux/musllinux/macosx all present, zero fork-markers). `dbt-core` and `pymc`/`pytensor` co-resolve cleanly; the previously-worried protobuf/urllib3 vs. numpy/scipy corridor is not a real conflict at these bounds.

**Primary recommendation:** Trust the WBS task order (T-001→T-012) with the D-29 audit-first opening; pin `SHELL`/`.SHELLFLAGS` exactly as researched; add one explicit `choco install make` step to the Windows leg of the `test` job; and treat the `uv.lock` resolution as settled — do not spend planning cycles hunting for a dependency conflict that empirically does not exist at these bounds.

## Architectural Responsibility Map

AMBO is an offline batch/CLI pipeline (simulate → transform → fit → validate → decide → report), not a web application — the standard Browser/SSR/API/CDN tiers from the output-format template don't apply. The table below substitutes AMBO's real tiers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Git history / provenance | Version control (git) | CI/CD (layer-order check, Phase 5+) | GB-501/502 and Charter §5 are git-history claims; nothing else can prove ordering |
| Python/uv dependency scaffold | Local dev toolchain (`pyproject.toml`, `uv.lock`) | CI/CD (`uv sync` in every job) | One lockfile is the cross-platform contract (T-002 AC-1) |
| Repository skeleton & ignore rules | Filesystem convention (SPEC-08 §2) | CI/CD (`test_repo_layout.py`, D-23) | Fixed layout is load-bearing for path-globbing scripts |
| Central config (`config/settings.yaml` + `common/config.py`) | Application code (`src/ambo/common`) | — | EB-040 one-config-home; D-25 authors it whole now |
| Logging + private-path filter | Application code (`src/ambo/common`) | CI/CD (leak scan job 6) | Leak surface control lives in code, enforced in CI |
| Makefile interface | Local dev toolchain | CI/CD (every job calls `make <target>`) | The Makefile *is* the contract between phases/agents/CI/README §8 |
| Lint/type/pre-commit | Local dev toolchain (git hook) | CI/CD (job 1, `make lint`) | Dual-owner by design: hook catches locally, CI job is the actual gate |
| Leak scan (`scripts/leak_scan.py`) | Application code (`scripts/`) | CI/CD (job 6) + local pre-commit hook | One of the four governance showpieces (GB §8) |
| CI workflow (six required jobs) | CI/CD (GitHub Actions) | — | EB-060/061; D-16/D-19/D-21 all constrain this tier directly |
| Test scaffold + guard tests | Application code (`tests/`) | CI/CD (job 2 enforces) | Architectural guards (forbidden-deps, import-independence, no-requests, layout) |
| Season-windows seed | Data/config (`dbt/seeds/season_windows.csv`) | CI/CD (job 1 diff-check, D-20) | AD-020 single calendar shared across the W-2 firewall |
| Governance scaffold (ADR, BUILD_LOG, RISK_REGISTER) | Governance docs (`docs/ADR/`, `docs/*.md`) | — | GB-201/202; reviewed at every phase entry |

## Standard Stack

### Core

| Library | Verified resolvable version (uv lock, 2026-08-04) | Purpose | Why Standard |
|---------|------|---------|--------------|
| `pandas` | latest satisfying `>=2.2,<3` | Dataframe layer, agency data & marts | Universal in this ecosystem; SPEC-08 §3 pin |
| `numpy` | 2.4.6 (satisfies `>=1.26,<3`) | Numerics | pymc/pytensor/scipy base dependency |
| `pymc` | 5.28.5 (satisfies `>=5.15,<6`) | Bayesian MMM (Phase 4+) | Primary model implementation per Charter O-3 |
| `arviz` | latest satisfying `>=0.18` | Posterior diagnostics | Standard PyMC companion |
| `pytensor` | 2.38.3 (as pinned transitively by pymc) | pymc backend | No pin needed — pymc controls it |
| `pymc-marketing` | 0.19.4 (satisfies `>=0.8`) | Cross-check model only (Charter O-3) | Explicitly the *second* of exactly two sanctioned implementations |
| `scipy` | 1.18.0 (satisfies `>=1.13`) | Numerics | pymc/pytensor dependency |
| `duckdb` | latest satisfying `>=1.0` | Local warehouse | SPEC-08 canonical warehouse engine |
| `dbt-core` | 1.12.0 (satisfies `>=1.8,<2`) | Transform layer | SPEC-08 §2 `dbt/` |
| `dbt-duckdb` | 1.10.1 (satisfies `>=1.8,<2`) | dbt adapter | Pairs with duckdb |
| `holidays` | latest satisfying `>=0.50` | AT calendar source for season windows | T-011 |
| `matplotlib` | latest satisfying `>=3.8` | Charts (Phase 8+) | SPEC-08 §3 pin |
| `pydantic` | latest satisfying `>=2.7` | Settings validation, `extra='forbid'` | EB-040 |
| `PyYAML` | latest satisfying `>=6` | Config parsing | Standard |
| `python-dotenv` | latest satisfying `>=1` | `.env` → `AMBO_PRIVATE_DROP` | EB-041 |

### Supporting (dev)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| `pytest>=8` | Test runner | `make test` |
| `pytest-cov` | Coverage | `--cov=src/ambo --cov-fail-under=80` (non-blocking until M0 close, D-15) |
| `ruff` | Lint + format, line 100 | `make lint` |
| `mypy` | Strict type check on `src/ambo/` | `make lint` |
| `pre-commit` | Git hook runner | `make setup` |
| `nbstripout` | Notebook output stripping | leak-surface control (EB-002) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| raw PyMC | Robyn / Meridian / lightweight_mmm | Explicitly forbidden — Charter O-3, enforced by T-010's forbidden-deps guard test |
| GNU Make | `just`, `nox`, `invoke` | Spec fixes Make (SPEC-08 §5); not a Phase 1 decision to revisit |
| pytensor NumPy backend | pytensor C/JAX backend | No `g++` on dev machine (RISK_REGISTER R-owner-Phase-4); NumPy fallback works but is slower — out of Phase 1 scope |

**Installation:**
```bash
uv venv
uv sync
```

**Version verification (empirical, this session):**
```bash
uv lock   # from a throwaway pyproject.toml containing exactly the SPEC-08 §3 bounds
# Resolved 112 packages in 1.43s — single universal lock, no fork-markers, no errors.
```
This is the actual evidence for T-002 AC-1 ("all SPEC-08 §3 packages resolvable with stated bounds on Windows and Linux"). The planner should have T-002 run the real `uv lock` inside the project (not a throwaway) and commit the resulting `uv.lock` — do not hand-author it.

**Note for RISK_REGISTER (D-08 seed):** `pymc>=5.15,<6` resolved to 5.28.5, close to but safely under the `<6` ceiling. PyMC 6.0 / PyTensor 3.0 / ArviZ 1.0 are flagged in current PyMC-ecosystem discussion as upcoming breaking releases — the existing `<6` upper bound already guards against this; no action needed in Phase 1 beyond noting the bound is load-bearing (an ADR is required if it's ever widened, per EB-030).

## Package Legitimacy Audit

All 20 SPEC-08 §3 runtime + dev packages were checked via the legitimacy seam. Every package returned **SUS**, but inspection of the `reasons` shows this is a heuristic artifact of this environment, not a real risk signal: the two triggering reasons are `unknown-downloads` (the checker has no download-stats source configured here — it is not that downloads are actually low) and `too-new` (it appears to key off the *latest published version's* release date, which is recent for every actively-maintained package in this list — pandas, numpy, pymc, ruff, mypy, pre-commit all ship frequently). This is expected behavior for a list of some of the most widely-used packages in the Python data-science ecosystem, not a hallucination signal.

Corroborating evidence beyond the checker: (a) `repoUrl` for the packages that returned one matches the canonical org — `pymc-devs/pymc`, `dbt-labs/dbt-core`, `pydantic/pydantic`, `pytest-dev/pytest`, `pre-commit/pre-commit`, `duckdb/duckdb-python`, `jwills/dbt-duckdb`, `theskumar/python-dotenv`; (b) the empirical `uv lock` resolution above pulled every one of these (plus ~90 transitive deps) directly from `https://pypi.org/simple` with real `files.pythonhosted.org` artifact URLs — that resolution is itself a registry-existence check for the whole dependency tree.

| Package | Registry | Reasons flagged | Corroboration | Verdict | Disposition |
|---------|----------|------------------|----------------|---------|-------------|
| pandas | pypi | too-new, unknown-downloads, no-repository | Resolved via uv lock from pypi.org/simple; universally known | SUS (heuristic) | Approved |
| numpy | pypi | unknown-downloads, no-repository | Same | SUS (heuristic) | Approved |
| pymc | pypi | too-new, unknown-downloads | repoUrl=github.com/pymc-devs/pymc | SUS (heuristic) | Approved |
| arviz | pypi | unknown-downloads, no-repository | Standard PyMC companion; resolved via uv lock | SUS (heuristic) | Approved |
| pytensor | pypi | too-new, unknown-downloads, no-repository | Transitively pinned by pymc | SUS (heuristic) | Approved |
| pymc-marketing | pypi | unknown-downloads, no-repository | Resolved via uv lock | SUS (heuristic) | Approved |
| scipy | pypi | unknown-downloads, no-repository | Resolved via uv lock | SUS (heuristic) | Approved |
| duckdb | pypi | too-new, unknown-downloads | repoUrl=github.com/duckdb/duckdb-python | SUS (heuristic) | Approved |
| dbt-core | pypi | too-new, unknown-downloads | repoUrl=github.com/dbt-labs/dbt-core | SUS (heuristic) | Approved |
| dbt-duckdb | pypi | unknown-downloads | repoUrl=github.com/jwills/dbt-duckdb | SUS (heuristic) | Approved |
| holidays | pypi | too-new, unknown-downloads, no-repository | Resolved via uv lock | SUS (heuristic) | Approved |
| matplotlib | pypi | too-new, unknown-downloads | repoUrl=matplotlib.org | SUS (heuristic) | Approved |
| pydantic | pypi | unknown-downloads | repoUrl=github.com/pydantic/pydantic | SUS (heuristic) | Approved |
| PyYAML | pypi | unknown-downloads | repoUrl=pyyaml.org | SUS (heuristic) | Approved |
| python-dotenv | pypi | unknown-downloads | repoUrl=github.com/theskumar/python-dotenv | SUS (heuristic) | Approved |
| pytest | pypi | unknown-downloads | repoUrl=github.com/pytest-dev/pytest | SUS (heuristic) | Approved |
| pytest-cov | pypi | unknown-downloads, no-repository | Resolved via uv lock | SUS (heuristic) | Approved |
| ruff | pypi | too-new, unknown-downloads | repoUrl=docs.astral.sh/ruff | SUS (heuristic) | Approved |
| mypy | pypi | too-new, unknown-downloads | repoUrl=mypy-lang.org | SUS (heuristic) | Approved |
| pre-commit | pypi | too-new, unknown-downloads | repoUrl=github.com/pre-commit/pre-commit | SUS (heuristic) | Approved |
| nbstripout | pypi | unknown-downloads | repoUrl=pypi.org/project/nbstripout | SUS (heuristic) | Approved |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** all 20 — but disposition is "Approved" per the heuristic-artifact analysis above, not a genuine risk. Per protocol, the planner should still add **one combined** `checkpoint:human-verify` task in T-002 (not 20 individual ones — disproportionate to the 0.5 d budget) that has the human glance at the generated `uv.lock` top-level package list against SPEC-08 §3 before the first commit of that lockfile. This satisfies the spirit of the gate without multiplying tasks for a single locked, authoritative dependency table.

## Architecture Patterns

### System Architecture Diagram (Phase 1 slice only)

```
Developer / CI runner
       │
       ▼
 [git clone] ──► working tree (docs already present, code absent)
       │
       ▼
 make setup ──► uv venv + uv sync (reads pyproject.toml + uv.lock)
       │             │
       │             ▼
       │        .venv/ (gitignored) ── pre-commit install (git hook, local only)
       ▼
 make lint / make test ──► ruff, mypy, pytest
       │                        │
       │                        ▼
       │                  tests/unit/*  (guard tests: forbidden-deps,
       │                                 import-independence, no-requests,
       │                                 repo-layout — D-23)
       ▼
 git push / PR (draft, opened at milestone start — D-19)
       │
       ▼
 .github/workflows/ci.yml  (single workflow, six required jobs, D-16 no skip-guards)
   ├─ job 1 lint         (ruff + mypy + season-windows seed diff-check, D-20)
   ├─ job 2 test         (pytest incl. smoke marker; matrixed ubuntu+windows, D-21)
   ├─ job 3 dbt          (make transform — vacuously green, D-17)
   ├─ job 4 ssot         (check_ssot_consistency.py — vacuously green, D-17)
   ├─ job 5 layer-order  (check_layer_order.py — vacuously green, D-17; fetch-depth 0)
   └─ job 6 leak-scan    (leak_scan.py pattern subset; fetch-depth 0)
       │
       ▼
 all six green ──► merge-commit into milestone branch (m0-bootstrap) ──► main
```

### Recommended Project Structure (Phase 1 deliverables only)
```
config/
├── settings.yaml            # D-25: channels, L=8, paths, MD-050 sampler block, scenarios
src/ambo/
└── common/
    ├── config.py             # T-004: pydantic Settings, load_settings() cached
    └── logging.py             # T-005: get_logger(), private-path redaction filter
scripts/
├── leak_scan.py               # T-008
└── generate_season_windows.py # T-011
dbt/seeds/season_windows.csv   # T-011 committed seed
tests/{unit,fixtures,golden}/  # T-010 scaffold + guard tests
docs/
├── ADR/{TEMPLATE.md,ADR-006_...md,README.md}  # T-012, D-05, D-09
├── BUILD_LOG.md                                # T-012
├── MODULE_CONTRACTS.md                         # D-02/D-03
└── RISK_REGISTER.md                            # D-08
.github/workflows/ci.yml       # T-009
.github/pull_request_template.md  # D-24
Makefile                       # T-006
.pre-commit-config.yaml        # T-007
.gitattributes                 # D-22
README.md                      # D-28
```

### Pattern 1: Portable Makefile SHELL pin (priority question 1 — answer)

**What:** A two-line, platform-agnostic shell pin that works identically under Linux CI, `windows-latest` CI (once `make` is installed), and the Windows dev machine's Git Bash terminal.

**Why it works — the mechanism:**
- GNU Make's documented behavior: `SHELL` is normally *never* taken from the environment (to avoid a user's personal shell preference leaking into recipes) — **except** on MS-DOS/MS-Windows, where the environment's `SHELL` value *is* honored, specifically because Windows users rarely set it themselves. [CITED: gnu.org/software/make/manual/html_node/Choosing-the-Shell.html]
- If the Makefile instead sets `SHELL` explicitly to a literal path (`/bin/sh`), that assignment wins on all platforms. On Linux this is trivially correct (`/bin/sh` exists). On native-Win32 GNU Make (ezwinports, the build already verified on the dev machine), when the literal path doesn't resolve as a real Windows path, Make falls back to a `PATH` search for the shell's **basename** with known Windows executable extensions (`.exe`, `.com`, `.bat`, `.sh`) — this is documented native-Win32-Make behavior, not a hack. [CITED: gnu.org/software/make/manual/html_node/Choosing-the-Shell.html; corroborated by community reports of the same fallback in help-make / Cygwin / MinGW mailing-list threads — MEDIUM confidence, cross-checked across independent threads]
- Inside a Git Bash terminal, Git's own `usr/bin` (containing `sh.exe`) is on `PATH`, so the fallback search succeeds and resolves to Git's POSIX `sh`.

**When to use:** Every recipe in the Makefile (BP-D-14 requires POSIX sh recipes uniformly).

**Exact lines for the planner to drop into T-006's Makefile (top of file, before any target):**
```make
SHELL := /bin/sh
.SHELLFLAGS := -eu -c
```
`-eu` (errexit + nounset) is a POSIX-sh-safe strictness upgrade over the bare `-c` default; drop the `-eu` if any historical recipe deliberately relies on non-strict behavior (none currently do — T-006 is greenfield).

**Verification the planner should add to T-006's validation:** a one-line CI-visible probe such as `@$(SHELL) --version | head -1` inside `make -n <target>` output, or simply rely on `make lint test` executing real POSIX-sh recipes and going green on both matrix legs (D-21) as the proof.

**Caveat (WebSearch-only, LOW confidence, worth a one-line note in T-006 but not a blocker):** one thread warns that if `sh.exe` is *also* separately picked up by a **different, non-ezwinports** Windows Make variant (e.g. MinGW/MSYS "mingw32-make"), having `sh.exe` on `PATH` can conflict with that variant's *own* internal shell assumptions. This does not apply here — the dev machine and (once installed) the CI runner both use the same ezwinports-lineage native-Win32 `make`, not MSYS2's `mingw32-make`. The planner should NOT install `make` via MSYS2/pacman in CI for this reason — use `choco install make` (see Pattern 2) to keep the same Make lineage on both the dev machine and CI.

### Pattern 2: `windows-latest` make availability (priority question 2 — answer)

**What:** `windows-latest` (Windows Server 2022/2025 runner image) does **not** ship GNU Make. [VERIFIED: fetched `actions/runner-images` toolset-2022.json and the Windows2022-Readme.md installed-software list directly this session — `make`/`mingw32-make` is absent from both; only MinGW 14.x (compiler toolchain, no `make` binary bundled) and empty MSYS2/mingw package arrays are present]

**Concrete setup step for T-009's `test` job, Windows leg:**
```yaml
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Install make (Windows only)
        if: runner.os == 'Windows'
        run: choco install make -y
      - name: Set up uv
        uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: make test
```
`choco` (Chocolatey) is preinstalled on `windows-latest` [CITED: WebSearch — GitHub `actions/runner-images` issue discussion confirms `choco` ships on Windows runners; MEDIUM confidence]. `choco install make` pulls the community "make" package which is the same ezwinports lineage as the dev-machine binary — install cost is small (single binary, seconds) and does not change per-job billing meaningfully relative to the 2× Windows-runner rate already budgeted under D-21.

**Important — this is NOT an `if: hashFiles()` skip-guard (which D-16 forbids).** The `if: runner.os == 'Windows'` conditional selects *which setup step* runs, not whether the job itself passes or is skipped; the job still runs to completion and reports a real pass/fail on both OSes. This distinction should be explicit in T-009's plan so a reviewer doesn't mistake it for a D-16 violation.

**Residual risk (flag for RISK_REGISTER, not a blocker):** the exact chocolatey "make" package provenance (ezwinports vs. another GnuWin32 mirror) could not be confirmed via an authoritative source this session (community.chocolatey.org returned HTTP 403 to the fetch tool). [ASSUMED — verify by reading `choco install make -y` output in the first actual CI run; if it turns out to be a different/older GNU Make than 4.4.1, that's still almost certainly fine since Make's `SHELL` fallback behavior (Pattern 1) is a documented feature of the ezwinports/native-Win32 Make family broadly, not version-specific — but confirm the version string in CI logs as cheap due diligence.]

### Pattern 3: `uv` cross-platform lock (priority question 3 — answer)

**What:** One `uv.lock`, generated by a plain `uv lock` (or `uv sync`) against `pyproject.toml` containing exactly the SPEC-08 §3 bounds, resolves for all platforms by default — this is `uv`'s **universal resolution** behavior, not something that needs opt-in flags.

**Empirical evidence [VERIFIED: uv lock resolution, empirical test — this session, `uv 0.11.29`, `Python 3.12.10`, Windows host]:**
```bash
uv lock
# Resolved 112 packages in 1.43s
```
Inspecting the resulting `uv.lock`:
- **No `resolution-markers` / fork-markers** anywhere in the file — meaning `uv` found a *single* dependency-version assignment (not a per-platform split) that satisfies every constraint.
- The `numpy` package entry alone lists wheels for `macosx_10_13_x86_64`, `macosx_11_0_arm64`, `macosx_14_0_arm64`, `macosx_14_0_x86_64`, `manylinux_2_27_aarch64`, `manylinux_2_27_x86_64`, `musllinux_1_2_aarch64`, `musllinux_1_2_x86_64`, `win32`, `win_amd64`, `win_arm64` — i.e. the one lockfile already carries Windows AND Linux (AND macOS) wheel references for every platform-specific package.
- Some packages correctly carry platform markers where genuinely platform-conditional (e.g. `tzdata` is only pulled in `when sys_platform == 'win32'`) — this is expected and correct, not evidence of conflict.

**Resolved versions for the specific pair the user flagged as highest-risk:**

| Package | Resolved version | Bound | Resolved without conflict against |
|---|---|---|---|
| `dbt-core` | 1.12.0 | `>=1.8,<2` | protobuf 6.33.6, urllib3 2.7.0 |
| `dbt-duckdb` | 1.10.1 | `>=1.8,<2` | duckdb, dbt-core |
| `pymc` | 5.28.5 | `>=5.15,<6` | pytensor 2.38.3, numpy 2.4.6, scipy 1.18.0 |
| `pymc-marketing` | 0.19.4 | `>=0.8` | pymc, arviz |

**Conclusion: no constraint collision exists at the SPEC-08 §3 bounds.** `dbt-core`'s `protobuf`/`urllib3`/`requests` dependency chain and `pymc`/`pytensor`'s `numpy`/`scipy` dependency chain resolved to a single mutually-compatible version set with zero forking. **No bound change is needed.** The planner should treat T-002 AC-1 as low-risk and simply have the task run the real `uv lock` inside the actual `pyproject.toml` (not hand-transcribe versions) and commit it — do not spend a task slot investigating a conflict that does not exist.

**One real, separate, and already-known risk (not a resolution conflict) to keep on the RISK_REGISTER:** `pytensor` needs a C compiler for its fast (C/JAX) backends; the dev machine has no `g++`, so `pytensor` silently falls back to the NumPy backend at runtime. This is unrelated to lockfile resolution (the package installs fine either way) and is already captured by D-08's seeded risk-register entry, owned by Phase 4.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-platform shell recipes | A custom shebang-detection script or per-OS Makefile | `SHELL := /bin/sh` + `.SHELLFLAGS` (Pattern 1) | GNU Make already documents and implements the fallback; a custom detection script is one more thing to test and maintain |
| Cross-platform dependency lock | Two separate lockfiles (Windows/Linux) or manual version pinning per OS | `uv lock`'s default universal resolution (Pattern 3) | uv already resolves multi-platform wheels into one file; hand-splitting reintroduces the exact drift risk D-21/T-002 exist to prevent |
| Vacuous-but-real CI checks (job 3/4/5) | A `TODO`/stub script or an `if: hashFiles()` skip | The real predicate, trivially green today (D-17) | Explicitly locked by D-16/D-17 — this is not a Phase 1 design choice, it's already decided; listed here only so the planner doesn't second-guess it |
| Private-path leak prevention | Manual code review discipline | `common/logging.py` redaction filter + `scripts/leak_scan.py` (T-005/T-008) | Governance-by-runnable-artifact is the established project pattern (GB §8) |

**Key insight:** every "don't hand-roll" item in this phase already has its answer fixed by a locked CONTEXT.md decision or by a documented, verifiable platform behavior — Phase 1's job is to encode the right two-line fix once (SHELL pin, lockfile), not to build tooling around the problem.

## Common Pitfalls

### Pitfall 1: Treating the `windows-latest` make setup step as a D-16 skip-guard
**What goes wrong:** A reviewer sees `if: runner.os == 'Windows'` in the `test` job and flags it as violating D-16 ("no `if: hashFiles()` guards... jobs pass by running, not by being skipped").
**Why it happens:** Surface-level pattern match on `if:` inside a CI job.
**How to avoid:** D-16 is about *job-level* skip-guards that let a job report `skipped` instead of `pass`/`fail`. A *step-level* OS conditional inside a job that still runs to completion and reports a real result is a different, unrelated mechanism. State this explicitly in the T-009 plan/PLAN.md so it survives review.
**Warning signs:** Any CI review checklist item phrased as "no `if:` anywhere in ci.yml" (too strict — should be "no job reports skipped").

### Pitfall 2: Installing `make` via MSYS2/pacman instead of Chocolatey in CI
**What goes wrong:** MSYS2's `mingw32-make` (or MSYS's own `make`) has different path-translation and shell-detection semantics than the ezwinports native-Win32 `make` used on the dev machine — recipes that work locally can behave differently in CI (e.g. path separator handling, or the `SHELL` fallback in Pattern 1 not triggering the same way).
**Why it happens:** MSYS2 is a common recommendation for "get Unix tools on Windows CI" searches, and it's a plausible-looking option since MSYS2 is available on `windows-latest`.
**How to avoid:** Use `choco install make`, which installs the same Make lineage already verified on the dev machine (GNU Make 4.4.1, ezwinports, native Win32), keeping local and CI behavior identical.
**Warning signs:** A CI-only Makefile bug that can't be reproduced locally.

### Pitfall 3: Hand-editing `uv.lock` or transcribing versions from this research
**What goes wrong:** The exact resolved versions in this document (e.g. `pymc 5.28.5`) are a snapshot from 2026-08-04 and will drift as new releases land within the same SPEC-08 bounds.
**Why it happens:** Copy-pasting "known good" versions feels safer than trusting the resolver.
**How to avoid:** T-002 should run `uv lock` for real inside the project's actual `pyproject.toml` and commit whatever it produces — the *bounds* are the spec-locked contract (EB-030: upgrades need an ADR), not the exact resolved versions.
**Warning signs:** A PR that edits `uv.lock` by hand instead of via `uv lock`/`uv sync`.

### Pitfall 4: Season-windows advent-week off-by-one
**What goes wrong:** SPEC-01 §2.1 reads "4 ISO weeks before and incl. the week of Dec 24," which is ambiguous between 4 total flagged weeks and 5 (4 *before* + 1 *of*).
**Why it happens:** Natural-language ambiguity in the spec text itself.
**How to avoid:** The WBS (T-011 implementation notes) and Guide §1.2 already resolve this explicitly as **4 total weeks**: `W ∈ {w(Dec24)−3 … w(Dec24)}`. This is a D-07 "interpretation, not an edit" — record it in `docs/BUILD_LOG.md` plus an in-script source comment, per T-011's own acceptance criteria; no ADR needed.
**Warning signs:** A test asserting 5 advent weeks per year instead of 4.

## Code Examples

### Makefile SHELL pin + loud-failing stub pattern (T-006)
```make
# Portable POSIX-sh recipes on both Linux and Windows (Git Bash / ezwinports make).
# See RESEARCH.md Pattern 1 for why this specific form resolves on both platforms.
SHELL := /bin/sh
.SHELLFLAGS := -eu -c

.PHONY: fit-real
fit-real:
	@echo "NOT IMPLEMENTED — arrives in Phase N (see README §Roadmap)"; exit 1
```
*(D-27 fixes the exact stub message text; substitute the correct phase number per target.)*

### GitHub Actions concurrency group for continuous draft-PR CI (D-19, secondary question 5)
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```
[CITED: WebSearch, standard GitHub Actions documented pattern — LOW confidence, single-source; cross-check against `docs.github.com/actions/using-jobs/using-concurrency` before finalizing T-009]. This groups runs by `workflow+ref`: pushes to `main` get a stable group that is never cancelled (protecting the `push:[main]` run required for D-19's "no duplicate runs, but main always completes"), while `pull_request` runs on the draft-PR branch share a group per PR ref and get cancelled when superseded by a newer push to that branch.

### Windows leg of the `test` job (T-009, priority question 2)
```yaml
jobs:
  test:
    name: test
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Install make (Windows only)
        if: runner.os == 'Windows'
        run: choco install make -y
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: make test
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `pip` + `pip-tools`/`Pipenv` for locking | `uv` (Rust-based resolver) | uv reached broad ecosystem adoption well before this project's start; already the project's chosen tool (SPEC-08 §1) | Universal cross-platform resolution by default (Pattern 3) is a `uv`-specific capability not present in `pip-tools` — reinforces that SPEC-08's tool choice was correct for T-002's cross-platform requirement |
| GnuWin32 `make` port (2006-era, GNU Make 3.81, unmaintained) | ezwinports `make` (actively maintained, GNU Make 4.x) | Ongoing | The dev machine already has the newer, maintained port (4.4.1) — matching this in CI via `choco install make` (not `gnuwin32-make`) matters |

**Deprecated/outdated:**
- `gnuwin32-make` chocolatey package: GNU Make 3.81, unmaintained since ~2010 — do not use even though it appears in search results; prefer the plain `make` chocolatey package (ezwinports lineage, matches dev machine).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Chocolatey "make" package (as opposed to "gnuwin32-make") is ezwinports-lineage GNU Make, matching the dev machine's verified 4.4.1 | Pattern 2 | Low — even if it's a different Make variant, the `SHELL` fallback in Pattern 1 is documented as general native-Win32-Make behavior, not version-specific; worst case is a CI-only Makefile quirk discoverable on first CI run |
| A2 | The community-thread claim about `sh.exe`-on-PATH conflicting with *MSYS2's* `mingw32-make` (not relevant here since we avoid MSYS2) | Pattern 1 caveat | Low — informs an avoidance recommendation (don't use MSYS2/pacman for make in CI) rather than a load-bearing claim |
| A3 | GitHub's documented concurrency-group pattern (`github.workflow`-`github.ref` + ref-conditional cancel-in-progress) is the correct form for D-19's requirement | Code Examples | Medium — if wrong, worst case is either duplicate CI runs (cost) or a cancelled `main` push run (governance/audit-trail gap); verify against `docs.github.com` before landing T-009 |
| A4 | `pre-commit install` in `make setup` is a safe no-op for a read-only reviewer | Common Pitfalls context / D-27 deferred item | Low — confirmed mechanism (git hooks only fire on `git commit`), but not independently verified against an authoritative pre-commit doc this session |

## Open Questions

1. **Exact provenance of the Chocolatey "make" package** (A1 above).
   - What we know: it exists, is community-maintained, distinct from "gnuwin32-make."
   - What's unclear: exact upstream source (ezwinports vs. another GnuWin32-family build) — the community.chocolatey.org package page returned HTTP 403 to the fetch tool this session.
   - Recommendation: cheap to resolve at execution time — read the `choco install make -y` output in the first real T-009 CI run (it prints the installed version) and compare to the dev machine's `make --version` (4.4.1). No blocking action needed in planning.

2. **Exact GitHub Actions concurrency-group syntax cross-check** (A3 above).
   - What we know: the pattern above is a standard, widely-documented GitHub Actions idiom.
   - What's unclear: this session's evidence is WebSearch-only (LOW confidence per the source hierarchy), not fetched from `docs.github.com` directly.
   - Recommendation: T-009's implementation step should do a 30-second confirm against `docs.github.com/en/actions/using-jobs/using-concurrency` before committing `ci.yml` — cheap, and this is exactly the kind of syntax detail worth a final doc check rather than research-time verification.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | T-002 (pyproject `requires-python`) | ✓ | 3.12.10 | — |
| `uv` | T-002 (venv + lock + sync) | ✓ | 0.11.29 | — |
| GNU Make | T-006 (Makefile interface) | ✓ (dev machine) | 4.4.1 (ezwinports, native Win32) | On `windows-latest` CI: `choco install make` (Pattern 2) |
| git | T-001 (baseline commit, branch discipline) | ✓ | 2.55.0.windows.2 | — |
| C compiler (`g++`) | pytensor fast backend (not exercised until Phase 4) | ✗ | — | pytensor NumPy backend (already the documented fallback; RISK_REGISTER entry per D-08, owned Phase 4) |
| GitHub `windows-latest` runner Make | T-009 CI `test` job, Windows leg | ✗ (not preinstalled) | — | `choco install make -y` step (Pattern 2) |
| Chocolatey on `windows-latest` | T-009 CI Windows-leg make install | ✓ (preinstalled per GitHub runner-images) | — | — |

**Missing dependencies with no fallback:** none — every gap identified has a documented, low-cost fallback.

**Missing dependencies with fallback:**
- `g++` — pytensor falls back to NumPy backend (Phase 4 territory, not Phase 1-blocking).
- `windows-latest` GNU Make — `choco install make -y` step in T-009.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (not yet installed — T-002 installs it; T-010 builds the scaffold) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (T-002: `-q`, `--cov=src/ambo --cov-fail-under=80` non-blocking until M0 close per D-15; `--strict-markers`, T-010) |
| Quick run command | `make test` (locally skips `@pytest.mark.smoke` unless `SMOKE=1`, per SPEC-08 §6) |
| Full suite command | `SMOKE=1 make test` locally, or CI job 2 (`test`) which always runs the smoke marker |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-dl8-quality | `make test` green; ruff+mypy clean; CI green incl. smoke-fit; coverage ≥80% of `src/` | unit + CI job 1/2 | `make lint && make test` | ❌ Wave 0 — created by T-002/T-006/T-007/T-010 |
| REQ-scope-in | Eight in-scope workstreams trace to owning SPEC + WBS task | doc/manual | N/A this phase — traceability matrix is D-02/03 scaffold work | ❌ Wave 0 — `docs/MODULE_CONTRACTS.md` header (D-03) |
| REQ-scope-out | O-1…O-8 excluded; forbidden-deps test enforces O-3; no-cron enforces O-7 | unit (guard test) + CI | `pytest tests/unit/test_forbidden_deps.py -x` | ❌ Wave 0 — created by T-010 |
| REQ-milestones | Eight milestones, effort budgets, 2× stop-plus-ADR rule | doc/process | N/A this phase — Phase 1 seeds the mechanism (BUILD_LOG entries), doesn't test it programmatically | N/A — process rule, not code |
| REQ-risk-register | R-1…R-9 tracked with mitigation/fallback/detection triads, reviewed each phase entry | doc | `docs/RISK_REGISTER.md` exists and is reviewable | ❌ Wave 0 — created by T-012/D-08 |

Additional Phase 1 acceptance criteria that need their own test/CI mapping (from the WBS, not a Charter REQ but load-bearing for DL-8/DL-1):

| WBS AC | Behavior | Test Type | Automated Command |
|--------|----------|-----------|--------------------|
| T-002 AC-1 | uv.lock cross-platform resolvable | CI (both matrix legs of `test` job resolve `uv sync` without error) | `uv sync` on ubuntu-latest AND windows-latest |
| T-003 validation | `.gitignore` correctness | manual probe (WBS-specified) | `touch data/warehouse/x.duckdb exports/foo.csv && git status` shows nothing to add — worth converting to a pytest per the "test over ticked box" pattern, planner's discretion |
| T-004 AC-2 | `target_accept` appears nowhere but config | grep guard | `grep -rn "target_accept" src/ \| grep -v config` → empty; should be a pytest, not a manual grep, per D-23's own reasoning |
| T-005 AC-1 | Private-path redaction proven | unit | `pytest tests/unit/test_logging.py -x` |
| T-006 AC-2/3 | Stub exit codes ≠0; works under Git Bash + Linux bash | CI (both matrix legs) + `make -n <target>` | both `test` job matrix legs green is the actual proof |
| T-007 | pre-commit hooks + fake-key probe blocks | manual/CI | `pre-commit run --all-files` + a scratch-branch fake-key probe (not committed) |
| T-008 | leak scan 3 modes | unit | `pytest tests/unit/test_leak_scan.py -x` |
| T-009 AC-1/2 | six jobs required, smoke <15min | CI itself | observe `ci.yml` run |
| T-010 | guard tests fail on planted violations | unit (proven once on a scratch commit, reverted) | `pytest tests/unit/test_*.py -x` |
| T-011 | season-windows rules | unit | `pytest tests/unit/test_season_windows.py -x`; regeneration idempotence via CI job 1 diff-check (D-20) |
| D-23 (4th guard) | repo layout matches SPEC-08 §2, no allowlist | unit | `pytest tests/unit/test_repo_layout.py -x` |

### Sampling Rate
- **Per task commit:** `make lint` (fast, seconds) + targeted `pytest tests/unit/test_<module>.py -x` for whatever T-00x just landed.
- **Per wave merge:** `make lint && make test` (full non-smoke suite; smoke marker only runs in CI per SPEC-08 §6).
- **Phase gate:** CI `ci.yml` all six jobs green on the `m0-bootstrap` branch before the milestone PR is marked ready-for-review (D-11); coverage gate (`--cov-fail-under=80`) flips from non-blocking to blocking exactly at M0 exit (D-15) — the planner should sequence T-004/T-005 (which are the only modules in `--cov` scope) before treating coverage as a phase-gate criterion.

### Wave 0 Gaps
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` block — created by T-002.
- [ ] `tests/{unit,fixtures,golden}/` directory + `conftest.py` (seeded RNG fixture, tmp-path helpers) — created by T-010.
- [ ] `tests/unit/test_repo_layout.py`, `test_forbidden_deps.py`, `test_import_independence.py`, `test_no_requests.py` — created by T-010 (four guard tests per D-23).
- [ ] `tests/unit/test_config.py`, `test_logging.py` — created alongside T-004/T-005 (their own acceptance criteria require unit tests).
- [ ] `tests/unit/test_leak_scan.py` — created alongside T-008.
- [ ] `tests/unit/test_season_windows.py` — created alongside T-011.
- [ ] Framework install: `uv add --dev pytest pytest-cov ruff mypy pre-commit nbstripout` — part of T-002.

*(This is expected — Phase 1 is the phase that builds the test infrastructure itself; the "gaps" above are simply the shape of T-002/T-004/T-005/T-008/T-010/T-011, not a deficiency to remediate separately.)*

## Security Domain

`security_enforcement` is not set in `.planning/config.json` (file does not exist), so the default (enabled) applies. AMBO is an offline batch/CLI pipeline with no network-facing service, no authentication, and a single local user — most ASVS web-application categories do not apply; the relevant categories are input validation (config/data) and secrets handling.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No login surface anywhere in this project |
| V3 Session Management | No | No sessions — CLI/batch only |
| V4 Access Control | No | Single local user, filesystem-level access only |
| V5 Input Validation | Yes | pydantic `Settings` model with `extra='forbid'` (T-004, D-25) validates `config/settings.yaml`; dbt seed schema tests (T-011) validate `season_windows.csv` shape |
| V6 Cryptography | No (narrow) | No secrets are encrypted at rest by design — `AMBO_PRIVATE_DROP` contents are never copied into the repo (EB-041); this is an avoidance control, not a crypto control. No hand-rolled crypto anywhere in scope. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Private local-drop path (or its contents) leaking into logs/CI output | Information Disclosure | `common/logging.py` redaction filter (T-005) — hard-drops/redacts any log record containing the resolved `AMBO_PRIVATE_DROP` path |
| Private/anonymized data leaking into committed files | Information Disclosure | `scripts/leak_scan.py` (T-008) pattern-subset scan in CI job 6 + `--staged` pre-commit hook (T-007) |
| Supply-chain risk from a malicious/typosquatted dependency | Tampering | `uv.lock` pinned + committed (EB-030); forbidden-deps guard test (T-010) blocks the named-forbidden libraries; this session's Package Legitimacy Audit corroborates the full SPEC-08 §3 list against canonical repos |
| Silent config drift (a hardcoded number bypassing the single config home) | Tampering / Repudiation | `extra='forbid'` pydantic Settings (T-004) + the `target_accept`-outside-config grep guard (T-004 AC-2) |
| History rewriting hiding a leaked secret or altering the layer-order proof | Repudiation / Tampering | EB-082 append-only history is a process control, not code — no force-push/rebase/amend ever, enforced by discipline + branch settings (D-12 disables squash/rebase merge at the repo-settings level) |

## Sources

### Primary (HIGH confidence)
- Empirical `uv lock` resolution against SPEC-08 §3 bounds, executed this session (uv 0.11.29, Python 3.12.10) — 112 packages, single universal lockfile, zero fork-markers. Directly answers priority question 3.
- Empirical fetch of `actions/runner-images` `toolset-2022.json` and `Windows2022-Readme.md` (main branch, this session) confirming GNU Make absent from `windows-latest`. Directly answers priority question 2.
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` lines 19–262 (T-001…T-012, read in full this session).
- `docs/SPEC-08_engineering.md` (read in full this session).
- `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` §1.2, §7, §9 (read in full this session).
- `docs/SPEC-09_governance_quality.md` (read in full this session).
- `.planning/phases/01-repository-foundation/01-CONTEXT.md` (D-01…D-29, read in full this session).

### Secondary (MEDIUM confidence)
- GNU Make manual, "Choosing the Shell" node (gnu.org) — SHELL environment-variable Windows exception and `.SHELLFLAGS` default, via WebSearch with an authoritative source cited inline.
- GitHub `actions/runner-images` issue discussion confirming Chocolatey preinstalled on Windows runners, via WebSearch.

### Tertiary (LOW confidence — flagged for validation at execution time)
- WebSearch-only claim about ezwinports native-Win32 Make's `PATH`-search fallback for an unresolvable `SHELL` literal path (cross-checked across multiple independent mailing-list/forum threads, but not fetched from an authoritative GNU document specific to ezwinports).
- WebSearch-only claim about the community "make" Chocolatey package's ezwinports provenance (community.chocolatey.org page returned HTTP 403 to the fetch tool this session — could not verify directly).
- WebSearch-only GitHub Actions `concurrency` group syntax recommendation (standard, well-known pattern, but not fetched from `docs.github.com` directly this session).
- WebSearch-only claim about `pre-commit install` being a safe no-op for a read-only reviewer.

## Metadata

**Confidence breakdown:**
- Priority Q1 (SHELL pin): MEDIUM — mechanism is well-documented (HIGH for the base GNU Make behavior), but the specific ezwinports fallback claim is WebSearch-cross-checked, not authoritative-doc-fetched
- Priority Q2 (windows-latest make): HIGH — directly fetched and inspected the authoritative runner-images manifest this session
- Priority Q3 (uv cross-platform lock): HIGH — empirical, reproducible tool execution this session, zero conflicts found
- Standard stack / package legitimacy: MEDIUM — versions empirically resolved (HIGH), but the legitimacy-checker's SUS verdicts required manual override reasoning (documented above) since its downloads-signal is unavailable in this environment
- Architecture / governance sections: HIGH — sourced entirely from the project's own locked CONTEXT.md, WBS, and SPEC documents, not external research

**Research date:** 2026-08-04
**Valid until:** 2026-09-03 (30 days) for the CONTEXT/WBS/SPEC-derived sections (stable, project-locked); the `uv.lock` empirical versions table should be treated as a point-in-time snapshot only — re-run `uv lock` at T-002 execution time rather than trusting these exact version numbers.
