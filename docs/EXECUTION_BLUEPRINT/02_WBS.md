# 02 — WORK BREAKDOWN STRUCTURE

46 tasks, T-001…T-806, each sized to roughly one focused coding session (0.5–4 h).
Execute in ID order unless [04_DEPENDENCIES.md](04_DEPENDENCIES.md) marks a parallel
track. Task-card conventions:

- **DoR/DoD**: every task inherits the global Definition of Ready and Definition of
  Done from [11_ACCEPTANCE_CRITERIA.md §2–3](11_ACCEPTANCE_CRITERIA.md); cards list
  only *deltas*. Acceptance criteria are objective — a reviewer can verify each with
  a command or a file inspection.
- **Traceability** line: REQ IDs (SIM/AG/AD/MD/VR/DC/RB/EB/GB), Charter refs,
  deliverables (DL-x). Full matrix: [13_TRACEABILITY_MATRIX.md](13_TRACEABILITY_MATRIX.md).
- **[HUMAN]** marks tasks the agent must not perform alone (AGENTS §2).
- Module contracts for all APIs named here: [03_MODULES.md](03_MODULES.md).
  Deep dives: [05_IMPLEMENTATION_GUIDES.md](05_IMPLEMENTATION_GUIDES.md) ("Guide §n").

---

# Phase P0 — Repository foundation (M0)

### T-001 — Initialize git repository and baseline commit
**Objective.** Create the git repo; commit the pre-existing governance corpus
(charter, AGENTS, SPECs, this blueprint) as the first commit; establish branch
discipline.
**Rationale.** The layer-order proof (GB-501/502) and the "recovery before reality"
argument (Charter §5) are *git-history claims*; history must exist before any code
and must never be rewritten (EB-082).
**Prerequisites.** None. **Inputs.** Existing `.md` files.
**Outputs.** `.git/`, commit 1 = docs only; `main` branch; local git config
(`core.autocrlf=input` to keep LF endings deterministic across Windows/Linux —
byte-identical CSV gates SIM-070 depend on stable EOLs).
**Depends on:** — **Blocks:** every other task.
**Implementation notes.** Commit message `chore: baseline governance corpus (Charter v1.0, SPEC-01..09, blueprint)`.
Then create working branch `m0-bootstrap` for the milestone PR. If the repo gets a
GitHub remote, enable branch protection on `main` requiring the six CI jobs (EB-080)
as soon as T-009 lands.
**Validation.** `git log --oneline` shows exactly the baseline commit; `git status` clean.
**Acceptance criteria.** (1) Baseline commit contains only documentation, zero code.
(2) `.gitattributes` or config pins LF for `*.csv`, `*.py`, `*.yaml`, `*.md`.
(3) No file from outside the corpus committed.
**Traceability:** EB-080, EB-082, GB-501/502 enabler; Charter §5.

### T-002 — Python project scaffold: pyproject, uv, pinned dependencies
**Objective.** `pyproject.toml` (package `ambo`, `src/` layout, Python 3.12), all
SPEC-08 §3 runtime+dev dependencies with the exact bounds, `uv.lock` committed.
**Rationale.** Everything downstream imports this environment; pinning is an ADR-level
matter afterwards (EB-030).
**Prerequisites.** T-001. **Inputs.** SPEC-08 §3 dependency table.
**Outputs.** `pyproject.toml`, `uv.lock`, empty `src/ambo/__init__.py` (version string
`0.1.0`).
**Depends on:** T-001. **Blocks:** T-004…T-012, everything.
**Implementation notes.** `uv venv && uv sync`. Configure ruff (line 100) and mypy
(`--strict` scoped to `src/ambo/`, `ignore_missing_imports` for
pymc/arviz/pytensor/pymc_marketing/duckdb/holidays) inside `pyproject.toml` — one
config home, no scattered ini files. Register pytest options (`-q`,
`--cov=src/ambo --cov-fail-under=80` activated once ≥1 real module exists — until
then keep coverage config present but non-failing via an explicit marker, noted in
the Makefile comment). Do NOT add robyn/lightweight_mmm/prophet/sklearn (EB-030).
**Validation.** `uv sync` from clean checkout; `uv run python -c "import ambo"`.
**Acceptance criteria.** (1) All SPEC-08 §3 packages resolvable with stated bounds on
Windows and Linux (uv cross-platform lock). (2) `uv.lock` committed. (3) mypy runs
clean on the empty package. (4) No forbidden dependency in the lock file.
**Traceability:** EB-001, EB-030; DL-8.

### T-003 — Repository skeleton, .gitignore, .env.example, LICENSE
**Objective.** Create the exact SPEC-08 §2 tree (empty dirs with `.gitkeep`),
`.gitignore` per EB-081, `.env.example` documenting `AMBO_PRIVATE_DROP` only, MIT
LICENSE.
**Rationale.** Fixed layout is load-bearing: tests assert module boundaries by path;
the leak scan and layer-order scripts glob these paths.
**Prerequisites.** T-002. **Inputs.** SPEC-08 §2 tree, EB-081 list.
**Outputs.** Full directory skeleton; `data/synthetic/`, `data/real_anon/`,
`data/posteriors/` present (committed-by-design dirs); `data/warehouse/`,
`data/cache/`, `exports/` gitignored with `.gitkeep`.
**Depends on:** T-002. **Blocks:** all module tasks.
**Implementation notes.** `.env.example` contains the variable name, an example
Windows path, and a comment that contents are secret (EB-041). Verify `.gitignore`
covers: `.venv/`, `data/warehouse/`, `data/cache/`, `*.nc`, `exports/*.csv`, `.env`,
`__pycache__/`, `.pytest_cache/`, `dbt/target/`, `dbt/logs/`, `.ipynb_checkpoints/`.
**Validation.** `git status` after `touch data/warehouse/x.duckdb exports/foo.csv`
shows nothing to add.
**Acceptance criteria.** (1) Tree diff vs SPEC-08 §2 is empty (allowing not-yet-created
source files). (2) Ignore rules proven by the validation probe. (3) LICENSE = MIT with
author line matching Charter header.
**Traceability:** EB-081, AG-020, EB-041; DL-1.

### T-004 — Settings: `config/settings.yaml` + `ambo/common/config.py`
**Objective.** Central non-secret configuration: channel taxonomy (7 channels incl.
`other`), adstock length L=8, paths (data dirs, warehouse file, exports, reports),
sampler settings block (MD-050 values), scenario registry; loaded once via a pydantic
Settings object.
**Rationale.** EB-040 — one config home; magic numbers are an anti-pattern
([09 §A-2](09_ANTI_PATTERNS.md)).
**Prerequisites.** T-003. **Inputs.** SPEC-04 §5, SPEC-08 §4, SPEC-02 §5.2 taxonomy.
**Outputs.** `config/settings.yaml`; `src/ambo/common/config.py` per
[03_MODULES.md §common](03_MODULES.md); unit tests.
**Depends on:** T-003. **Blocks:** T-005 onward (everything imports settings).
**Implementation notes.** `load_settings()` is cached (single read per process);
`AMBO_PRIVATE_DROP` read from env via python-dotenv, typed `Path | None`, *never*
required unless an intake target runs (fail-fast with the AG-020 message there, not
at import). Paths resolved relative to repo root discovered from the package location.
**Validation.** Unit tests: YAML round-trip; missing env var behavior; unknown-key
rejection (pydantic `extra='forbid'`).
**Acceptance criteria.** (1) All MD-050 sampler numbers live here and nowhere else.
(2) `grep -rn "target_accept" src/ | grep -v config` → empty. (3) Channel list
identical to SPEC-02 §5.2 order. (4) `extra='forbid'` proven by test.
**Traceability:** EB-040, EB-041, AG-020, MD-050.

### T-005 — Logging: `ambo/common/logging.py` with private-path filter
**Objective.** Project logger factory: stdlib logging, structured format
(`ts level module msg`), and a filter that hard-drops any record whose message
contains the resolved `AMBO_PRIVATE_DROP` path (EB-041).
**Rationale.** Leak surface control — log lines are the easiest way to leak the
private path into CI logs or committed reports.
**Prerequisites.** T-004. **Outputs.** `src/ambo/common/logging.py` + tests.
**Depends on:** T-004. **Blocks:** all modules that log (all).
**Implementation notes.** Filter behavior when the env var is unset: no-op. Test with
a fake path set: a log call containing that path raises in strict mode (tests) /
redacts to `<PRIVATE_DROP>` at runtime — choose redact-at-runtime + assert-in-tests
(the test asserts the redaction happened). No print() anywhere in `src/`
([07 §logging](07_QUALITY_STANDARDS.md)).
**Validation.** Unit tests for both env states.
**Acceptance criteria.** (1) Redaction proven by test. (2) `get_logger(__name__)` is
the only logger construction pattern in the codebase (grep-testable). (3) Log format
fixed and documented.
**Traceability:** EB-041, AG-045 adjacency.

### T-006 — Makefile (canonical interface, loud-failing stubs)
**Objective.** The full SPEC-08 §5 target list from day one. Targets whose phase
hasn't arrived exit non-zero with `"NOT IMPLEMENTED (arrives in phase Pn — see docs/EXECUTION_BLUEPRINT/01_PHASES.md)"`.
**Rationale.** The Makefile is the contract between phases, agents, CI, and README §8;
loud stubs prevent silent no-ops (AGENTS/M0 "loud-failing Make stubs").
**Prerequisites.** T-002. **Outputs.** `Makefile`.
**Depends on:** T-002. **Blocks:** T-009 (CI calls make).
**Implementation notes.** POSIX sh recipes only (BP-D-14); every sampling target
prints expected runtime before starting (EB-050) — encode the runtime strings now as
variables. `make all` = transform→recover→sensitivity→decide→ssot→export→report and
must **fail fast** with instructions if required posteriors are missing (BP-D-20),
never trigger fits.
**Validation.** `make -n <target>` for each target; `make lint test` runs the real
tools; stub targets exit ≠ 0.
**Acceptance criteria.** (1) Target list exactly matches SPEC-08 §5 (names and
semantics). (2) Stub exit codes ≠ 0 with the phase pointer message. (3) Works under
Git Bash on Windows and bash on Linux.
**Traceability:** EB-050, SPEC-08 §5; DL-1.

### T-007 — Lint/type/pre-commit toolchain
**Objective.** ruff (lint+format, line 100), mypy strict scoped per EB-001,
`.pre-commit-config.yaml` with: ruff, ruff-format, end-of-file-fixer, check-yaml,
detect-private-key, `leak_scan.py --staged`, nbstripout.
**Prerequisites.** T-002 (configs live in pyproject), T-008 ordering note: the
pre-commit hook references `scripts/leak_scan.py`; land T-008 in the same PR before
enabling the hook.
**Outputs.** `.pre-commit-config.yaml`; `make lint` wired.
**Depends on:** T-002. **Blocks:** T-009.
**Implementation notes.** nbstripout matters even though notebooks are optional
(W-4) — it's leak-surface control (EB-002). Pre-commit pinned revs.
**Validation.** `pre-commit run --all-files` green; deliberately stage a fake private
key → hook blocks.
**Acceptance criteria.** (1) All seven hooks present and pinned. (2) `make lint` =
ruff check + ruff format --check + mypy, exit ≠ 0 on any violation. (3) Hook blocks
the fake-key probe.
**Traceability:** EB-001, EB-002; DL-8.

### T-008 — `scripts/leak_scan.py` (pattern subset + staged mode)
**Objective.** The leak scanner per AG-045: (a) pattern subset (always available):
private-drop path regex, email/URL patterns in `data/real_anon/`, currency-formatted
literals in notebooks; (b) full mode: additionally reads
`$AMBO_PRIVATE_DROP/blocklist.txt` when present, skips gracefully otherwise;
(c) `--staged` mode for pre-commit.
**Rationale.** One of the four governance showpieces (GB §8); must exist before any
real data can possibly appear.
**Prerequisites.** T-004, T-005. **Outputs.** `scripts/leak_scan.py` + tests using
synthetic fixture trees (never real values — AG-032 discipline applies to these
fixtures too).
**Depends on:** T-004. **Blocks:** T-007 hook, T-009 CI job 6.
**Implementation notes.** Guide §7. Exit codes: 0 clean, 1 findings (list file:line:
pattern-class, never echo the matched secret content itself — echo a hash prefix),
2 usage error. CI runs pattern subset only (blocklist unavailable there by design).
**Validation.** Tests: seeded fixture repo with a planted email in `data/real_anon/`
→ exit 1; clean tree → exit 0; blocklist present → planted blocklisted value found.
**Acceptance criteria.** (1) Three modes behave per above with tests. (2) Findings
output never contains the matched secret text. (3) Runtime < 10 s on the repo.
**Traceability:** AG-045, EB-002, GB §8; DL-9.

### T-009 — CI workflow `ci.yml`
**Objective.** Single workflow, six required jobs (EB-060): (1) lint; (2) test incl.
smoke-fit marker; (3) dbt build on committed data; (4) SSOT consistency; (5) layer
order; (6) leak scan pattern subset. Phase-gated jobs run their script, which exits
green-with-notice while its subject doesn't exist yet (BP-D-13 note; scripts arrive
T-408/T-409 — until then the jobs invoke placeholder-free `make` targets that exist
from T-006 and fail loudly if miswired, plus `if: hashFiles(...)` guards only where a
script genuinely cannot exist yet — prefer the script-exits-green pattern once
scripts land).
**Prerequisites.** T-006, T-007, T-008. **Outputs.** `.github/workflows/ci.yml`.
**Depends on:** T-006–T-008. **Blocks:** M0 exit.
**Implementation notes.** Guide §9. ubuntu-latest; `fetch-depth: 0` on jobs 5 and 6
(BP-D-13); uv cache + pytensor compiledir cache (BP-D-17); smoke job budget guard
15 min (EB-060); no cron triggers ever (Charter O-7).
**Validation.** Push branch, observe all six jobs green.
**Acceptance criteria.** (1) Six jobs, all marked required once branch protection is
possible. (2) Smoke job wall time < 15 min. (3) No workflow besides ci.yml. (4) Jobs
5–6 have full history.
**Traceability:** EB-060, EB-061, Charter O-7; DL-8.

### T-010 — Test scaffold + architectural guard tests
**Objective.** `tests/{unit,fixtures,golden}/` layout; `conftest.py` with seeded RNG
fixture and tmp-path helpers; the two standing architectural tests: forbidden-deps
(EB-030: importing robyn/lightweight_mmm/prophet/sklearn anywhere fails; also
lockfile scan) and simulate↔model import independence (W-2/SIM-003: AST-walk both
packages, assert no cross-import in either direction); plus the no-`requests` test
(EB-070).
**Prerequisites.** T-002. **Outputs.** test scaffold + 3 guard tests.
**Depends on:** T-002. **Blocks:** M0 exit; guards all later phases.
**Implementation notes.** Import-independence via AST over files (not runtime
imports), so it catches lazy imports too. Mark expensive tests: `@pytest.mark.smoke`
(CI-only unless `SMOKE=1`, EB-060), `@pytest.mark.fit` (never CI).
**Validation.** Introduce a deliberate cross-import in a scratch branch → test fails.
**Acceptance criteria.** (1) Guard tests fail on planted violations (proven once in a
scratch commit, then reverted). (2) Marker policy in `pyproject.toml` with
`--strict-markers`. (3) `make test` green.
**Traceability:** EB-030, EB-070, SIM-003, W-2; T-3 trap.

### T-011 — Season windows: generator script + committed seed + tests
**Objective.** `scripts/generate_season_windows.py` producing
`dbt/seeds/season_windows.csv` (one row per ISO week × year 2019–2027; columns
`iso_year, iso_week, week_start, advent_flag, schulbeginn_flag, jan_dip_flag,
spring_flag, summer_lull_flag`) from the `holidays` package + SPEC-01 §2.1 fixed
ISO-week rules; committed seed; unit tests.
**Rationale.** AD-020 — the single source of Austrian-calendar definitions consumed
by BOTH simulator and dbt (the sanctioned shared-CONFIG exception to W-2).
**Prerequisites.** T-002. **Outputs.** script + seed + tests.
**Depends on:** T-002. **Blocks:** T-103 (simulator seasonality), T-202 (staging).
**Implementation notes.** Guide §1.2 (window rules made exact: advent = the ISO week
containing Dec 24 plus the 4 preceding ISO weeks? — no: SPEC-01 says "the 4 ISO weeks
before and incl. the week of Dec 24", i.e. exactly 4 flagged weeks ending at the
Dec-24 week inclusive; encode as: weeks W where `W ∈ {w(Dec24)−3 … w(Dec24)}`.
Schulbeginn: the ISO week containing Styria's first school day (from `holidays`
subdivision AT-6 school calendar is NOT in the package — use the fixed rule "second
Monday of September" documented in the script header with source comment, flag that
week and the one before). Fixed-week flags: jan_dip W02–05, spring W14–22,
summer_lull W29–33.) Regeneration must be byte-idempotent; CI can diff-check.
**Validation.** Tests: exactly 4 advent weeks per year; Dec-24 week flagged; 2022
specific spot values; flag columns ∈ {0,1}; every ISO week of every year present
exactly once.
**Acceptance criteria.** (1) Seed committed, 2019–2027 coverage. (2) Regeneration
idempotent (`git diff` empty after rerun). (3) Tests enumerate all five window rules.
(4) Schulbeginn rule + source documented in-script (it interprets SPEC-01's "around
Styrian school start"; this interpretation is recorded in BUILD_LOG).
**Traceability:** AD-020, SIM §2.1, MD-022.

### T-012 — Governance scaffold: ADR template, BUILD_LOG, docs hygiene
**Objective.** `docs/ADR/ADR-000_template.md` (Context / Decision / Consequences /
Spec deviations with REQ IDs — GB-201), empty append-only `docs/BUILD_LOG.md` with
usage header, `docs/ADR/` README listing the five pre-planned slots (GB-202).
**Prerequisites.** T-001. **Outputs.** as above.
**Depends on:** T-001. **Blocks:** any ADR-triggering event.
**Validation.** Files exist; template fields match GB-201.
**Acceptance criteria.** (1) Template has the four sections. (2) Pre-planned ADR
slots ADR-001..005 listed with their GB-202 topics. (3) BUILD_LOG has its
append-only rule stated at top.
**Traceability:** GB-201, GB-202, W-3.

---

# Phase P1 — Ground-truth simulator (M1)

### T-101 — Scenario configuration schema + authored scenario YAMLs
**Objective.** Pydantic `ScenarioConfig` (channels, weeks, seed, §4 parameter table,
spend-pattern params, §6 φ/θ platform-bias params, promo-week list, burst schedules,
collinearity flag, CPM constants per BP-D-02) + authored `config/scenarios/
{s_a,s_b,s_c}.yaml` implementing SPEC-01 §3–§5 with BP-D-09's explicit week lists.
**Rationale.** SIM-002: YAML is authoritative; the schema makes drift from SPEC-01 §4
mechanically checkable (a test compares YAML values to the spec table hard-coded in
the test).
**Prerequisites.** T-004, T-011. **Inputs.** SPEC-01 §3–§6 tables; BP-D-02/09.
**Outputs.** `src/ambo/simulate/config.py` (or schemas module per
[03_MODULES.md](03_MODULES.md)), three YAMLs, tests.
**Depends on:** T-011. **Blocks:** T-102…T-108.
**Implementation notes.** Guide §1.1. Promo weeks: 10/year aligned per §2.1 (Black
Friday week, 2 Advent, 2 spring, 5 spread) — author the concrete ISO weeks per
simulated year; S-C (78 wk = 2022-W01…2023-W26): pro-rate. Burst schedules for
print/radio: author explicit burst-start weeks satisfying §3 counts and the S-B/S-C
anchoring rule (SIM-030). S-C YAML: identical to S-B except weeks=78, seed=303,
`display_video.beta=0`.
**Validation.** Schema tests incl. spec-table equality test; S-C↔S-B diff test
(only the three permitted differences).
**Acceptance criteria.** (1) `extra='forbid'`; all §4 values match spec table by
test. (2) Promo/burst lists satisfy their counting rules by test (10/yr pro-rated;
8 print bursts/yr with 3 anchored; 5 radio bursts/yr with 2 anchored). (3) The S-C
zero-beta and the SIM-030 collinearity flags present exactly as specified.
**Traceability:** SIM-002, SIM-030, §4/§5/§6 tables; DL-2 enabler.

### T-102 — Spend patterns: `simulate/spend_patterns.py`
**Objective.** Per-channel weekly spend series per SPEC-01 §3 exactly: always-on
Normals with floors, seasonal planning multipliers, meta 6-week ×1.8 pulse, flighted
print/radio bursts from the authored schedules; whole-€ rounding; one RNG stream from
the scenario seed.
**Prerequisites.** T-101. **Outputs.** module + SIM-031 tests.
**Depends on:** T-101. **Blocks:** T-105.
**Implementation notes.** Guide §1.3. Single `numpy.random.Generator` seeded once per
scenario, consumed in a *documented fixed order* (channel order = taxonomy order) so
adding channels later doesn't scramble streams. Collinearity switch (SIM-030) applies
the stronger multipliers for S-B/S-C. Floors applied after draw (`max(draw, floor)`).
**Validation.** SIM-031: annual totals within ±10% of design mean × weeks; zero-week
share within ±10 pp of design per flighted channel; determinism (same seed → same
frame).
**Acceptance criteria.** (1) SIM-031 tests green for all three scenarios. (2) All
spends integer ≥ 0. (3) meta pulse exactly every 6th week (t mod 6 == 0 convention
documented). (4) Burst weeks match YAML schedules exactly.
**Traceability:** SIM-030, SIM-031.

### T-103 — Baseline demand + seasonality in `simulate/dgp.py`
**Objective.** `base_t = B0 × (1+g)^t × season_t × promo_mult_t` with season_t
assembled from the committed season-windows seed exactly per §2.1 weights.
**Prerequisites.** T-011, T-101. **Outputs.** functions + tests.
**Depends on:** T-011, T-101. **Blocks:** T-105.
**Implementation notes.** Reads `season_windows.csv` (AD-020) — never recomputes
windows. promo_mult from the YAML promo list. Keep season_t as a returned component
for the SIM-071 audit.
**Validation.** Tests: max season_t in advent weeks; season_t=1.0 in unflagged weeks;
promo weeks get ×1.15; peak-week test drives SIM-073.
**Acceptance criteria.** (1) Weights exactly (+0.55, +0.25, +0.15, −0.20, −0.10).
(2) Component arrays exposed for audit. (3) SIM-073 pre-check green on all scenarios.
**Traceability:** SIM §2.1, SIM-073, AD-020.

### T-104 — Simulator-side adstock + Hill + closed-form tests
**Objective.** Raw recursive geometric adstock (`a_t = x_t + λ a_{t−1}`, a_0=0) and
Hill (`h = a^s/(a^s + K^s)`) implemented **inside `simulate/`** with independent
tests (SIM-003 — no imports from `model/`).
**Prerequisites.** T-101. **Outputs.** functions + SIM-074 tests.
**Depends on:** T-101. **Blocks:** T-105, T-106.
**Implementation notes.** Guide §1.4; convolution direction trap T-2: `a_t` must
depend on x_{≤t} only — the closed-form test (constant spend x ⇒ a_t → x/(1−λ))
catches reversal; add an impulse test: single spend spike at t=k ⇒ a decays
geometrically for t ≥ k and is 0 before k.
**Validation.** SIM-074: geometric-series limit within 1e-9 at t=200; `Hill(K)=0.5`
exact; impulse-response direction test.
**Acceptance criteria.** (1) All three tests green. (2) No import from `ambo.model`
(guard test T-010 stays green). (3) Vectorized over weeks (no Python loop over
channels × weeks × draws — plain loop over t is fine).
**Traceability:** SIM §2.2, SIM-003, SIM-074; traps T-2/T-3.

### T-105 — Revenue assembly, noise, orders, decomposition audit
**Objective.** `revenue_t = base_t + Σ_c β_c·Hill(adstock(x_c)) + ε_t`,
ε ~ N(0, 0.04·mean(base)); clip ≥ 0; `orders_t = round(revenue_t / AOV_t)`,
AOV = 95 + 10·advent; internal component store for the audit; outputs
`media_weekly.csv` (spend part) + `outcome_weekly.csv`.
**Prerequisites.** T-102, T-103, T-104. **Outputs.** assembled scenario frames +
SIM-071/072 audit functions.
**Depends on:** T-102–T-104. **Blocks:** T-106, T-107, T-108.
**Implementation notes.** Noise drawn from the same scenario RNG stream *after* spend
draws (documented order). Keep `components` frame (base, season factor, promo factor,
per-channel m_c, ε) — this is what SIM-071 re-sums and what T-107 aggregates into
truth.
**Validation.** SIM-071: base + Σm + ε = revenue to 1e-6 per week. SIM-072: no
negative pre-clip revenue; media share of annual revenue ∈ [15%,45%]; noise variance
share ∈ [2%,10%].
**Acceptance criteria.** (1) SIM-071/072 green all scenarios. (2) CSV schemas exactly
SIM-004 (column names/order). (3) `week_start` ISO Mondays covering exactly the
scenario window.
**Traceability:** SIM §2.3, SIM-071, SIM-072, SIM-004.

### T-106 — Platform reporting bias: `simulate/platform_bias.py`
**Objective.** SIM-060: per online channel,
`platform_revenue_{c,t} = m_{c,t}·φ_c + θ_c·base_t·share_{c,t}` with the §6 φ/θ
table; print/radio NULL; plus BP-D-02: impressions from CPM constants,
`platform_conversions = round(platform_revenue / AOV_t)`.
**Prerequisites.** T-105. **Outputs.** module + tests; completes `media_weekly.csv`
columns.
**Depends on:** T-105. **Blocks:** T-107 (truth includes platform ROAS), T-704.
**Implementation notes.** `share_c` = channel share of total spend that week
(zero-total weeks ⇒ share 0). Record φ, θ, CPM in truth.json (SIM-060 end + BP-D-02).
**Validation.** Tests: offline channels NULL; identity re-derivation on a small
hand-computed example; platform ROAS ordering by construction (φ ordering) present in
generated data.
**Acceptance criteria.** (1) φ/θ exactly the §6 values by test. (2) NULL handling per
SIM-004. (3) Hand-example equality to 1e-9.
**Traceability:** SIM-060, SIM-061, BP-D-02; DL-5 enabler.

### T-107 — Truth files: `simulate/truth.py` + pydantic schema
**Objective.** `truth.json` per scenario with every §4/§6 parameter + §8 derived
quantities: true total contribution per channel (level + share), true average ROAS
(Σm/Σx), true marginal ROAS at mean weekly spend (analytic derivative at steady-state
mean adstock), 21-point response-curve samples (0…2× max weekly spend, steady-state
adstock), platform ROAS; scenario metadata (seed, weeks, flags); pydantic
`TruthFile` schema committed (SIM-075).
**Prerequisites.** T-105, T-106. **Outputs.** `truth.py`, `TruthFile` schema,
three committed `truth.json`.
**Depends on:** T-105, T-106. **Blocks:** T-401, T-702.
**Implementation notes.** Guide §1.5 (exact formulas incl. the analytic Hill
derivative `dm/dx = β·s·K^s·a^{s−1}/(a^s+K^s)^2 · da/dx` with steady-state
`a = x/(1−λ)`, `da/dx = 1/(1−λ)`). Marginal ROAS is *truth-side* — uses SPEC-01
parameterization (BP-D-16). JSON serialization: sorted keys, 2-space indent, fixed
float format → byte-stable.
**Validation.** SIM-075 schema validation; spot-check: S-C `display_video` true ROAS
= 0, contribution share = 0; response-curve monotone nondecreasing.
**Acceptance criteria.** (1) Schema-validated on all three files. (2) Every §4/§6
parameter present + all §8 derived quantities. (3) Byte-stable across two runs.
**Traceability:** SIM-075, SIM §8; DL-2.

### T-108 — Simulator CLI, `make simulate`/`validate-sim`, determinism gate
**Objective.** `python -m ambo.simulate all|s_a|s_b|s_c` orchestrating T-102…T-107;
`make simulate` writes `data/synthetic/<scenario>/`; `make validate-sim` runs
SIM-070..075 as a gate suite printing a pass/fail table and exiting non-zero on any
failure.
**Prerequisites.** T-105–T-107. **Outputs.** CLI, wired make targets, gate runner.
**Depends on:** T-105–T-107. **Blocks:** T-109.
**Implementation notes.** SIM-070 determinism: the gate runner regenerates to a temp
dir and byte-compares against `data/synthetic/` (also catches accidental manual
edits). Write CSVs with fixed float formatting and LF endings (T-001).
**Validation.** Run twice; byte-identical. Gate suite green.
**Acceptance criteria.** (1) `make validate-sim` exit 0 iff all SIM gates pass and
prints one row per gate. (2) Byte-identity proven. (3) CLI has `--outdir` for tests
(tmp path), default `data/synthetic/`.
**Traceability:** SIM-001, SIM-070..075.

### T-109 — M1 close: commit data, BUILD_LOG, milestone PR
**Objective.** Commit `data/synthetic/**` (9 files), run AGENTS §5 protocol, tick M1
checklist ([06 §M1](06_CHECKLISTS.md)) in the PR, BUILD_LOG entry, merge.
**Depends on:** T-108 + all P1 tasks. **Blocks:** P2.
**Acceptance criteria.** (1) PR shows the ticked SPEC-01 §7 gate list with evidence
links (CI run + gate-runner output pasted). (2) All CI jobs green. (3) BUILD_LOG line
appended.
**Traceability:** A-9, W-3; M1 exit.

---

# Phase P2 — Warehouse (SPEC-03)

### T-201 — dbt scaffold + raw external views
**Objective.** `dbt/` project (dbt-duckdb, profile targeting
`data/warehouse/ambo.duckdb`), `raw` layer as external views over the committed
synthetic CSVs (+ Layer R behind `layer_r_present` var, default false — BP-D-05);
seeds directory already holds `season_windows.csv`.
**Prerequisites.** T-109. **Outputs.** `dbt_project.yml`, `profiles.yml`, raw models,
`make transform` wired.
**Depends on:** T-109. **Blocks:** T-202.
**Implementation notes.** Guide §8.1. `profiles.yml` committed (path relative to
project — no user-specific paths). Vars: `layer_r_present: false`,
`channel_taxonomy` list (must equal settings.yaml list — a test compares them).
**Validation.** `dbt build` green locally + CI job 3.
**Acceptance criteria.** (1) Warehouse file gitignored, created on build. (2) CI job
3 green with no private inputs. (3) Taxonomy-equality test green.
**Traceability:** AD-001, EB-060 job 3, BP-D-05.

### T-202 — Staging models + unit harmonization
**Objective.** `stg_media_weekly`, `stg_outcome_weekly`, `stg_promo`,
`stg_calendar_weekly` per SPEC-03 §2 with BP-D-03 unit-neutral renames; duplicate
keys FAIL (never dedup); `layer` column values 'P-SA'|'P-SB'|'P-SC'|'R'.
**Prerequisites.** T-201. **Outputs.** 4 staging models + schema tests.
**Depends on:** T-201. **Blocks:** T-203.
**Implementation notes.** Guide §8.2. Layer P media lacks `clicks` → NULL column in
the union; Layer P `platform_revenue_eur` → `platform_conv_value`; Layer R
`spend_aeur` → `spend`. `stg_calendar_weekly` reads the seed. Duplicate-key failure
via dbt `unique` tests on composite keys, plus a not-null spine.
**Validation.** dbt tests; a poisoned-fixture test (duplicate row in a tmp CSV) is
covered in Python-side export tests instead (dbt tests prove the constraint on real
inputs).
**Acceptance criteria.** (1) All staging schema tests green. (2) No `_eur`/`_aeur`
suffix survives into staging output columns (AD-043 test half). (3) Calendar staging
matches seed row-for-row.
**Traceability:** AD-001, AD-002, AD-020, BP-D-03.

### T-203 — Marts + dbt test suite
**Objective.** `fct_mmm_input` (week × layer, calendar flags, promo, revenue, orders,
pivoted `spend_<channel>` over the fixed taxonomy, NULL→0), `dim_layer` (weeks,
channels_present as canonical comma-string BP-D-19, monetary_unit, source_tag),
`fct_platform_reported`; tests AD-040 (grain unique+not_null, gapless spine per
layer), AD-041 (ranges), AD-042 (P-SA revenue reconciliation ±1e-6), AD-043
(unit-suffix segregation), AD-044 (intake-channel seed comparison — inert until
BP-D-05 flip).
**Prerequisites.** T-202. **Outputs.** 3 marts + tests.
**Depends on:** T-202. **Blocks:** T-204, T-205, T-301+.
**Implementation notes.** Guide §8.3. Pivot via jinja over the taxonomy var (never
hand-written per-channel SQL ×7). Gapless spine: generate week spine per layer from
dim_layer min/max, left-join, assert no null joins.
**Validation.** `dbt build` + all tests green in CI.
**Acceptance criteria.** (1) AD-040..043 green (AD-044 present, gated). (2)
`fct_mmm_input` column set exactly as [03 §dbt](03_MODULES.md) documents. (3)
Reconciliation delta printed in test output ≤ 1e-6.
**Traceability:** AD-030, AD-040..044, BP-D-19.

### T-204 — `ambo/common/db.py` mart accessors
**Objective.** Read-only typed accessors: `read_mmm_input(layer)`,
`read_platform_reported(layer)`, `read_dim_layer()` returning validated DataFrames
(pandera-style validation implemented as plain pydantic/assert checks — no new deps);
the ONLY route by which model code touches data (AD-030).
**Prerequisites.** T-203. **Outputs.** module + tests against the built warehouse.
**Depends on:** T-203. **Blocks:** T-304+, T-701+.
**Implementation notes.** Connection read-only; helpful error if warehouse missing
("run make transform"). Returned frame contract documented in
[03 §common](03_MODULES.md) and asserted (columns, dtypes, no NaN in spends).
**Validation.** Round-trip test: simulator CSV → dbt → accessor frame → totals match.
**Acceptance criteria.** (1) `grep -rn "read_csv" src/ambo/model src/ambo/decide` →
empty (mart-only rule). (2) Contract assertions tested. (3) Read-only mode proven
(write attempt raises).
**Traceability:** AD-030; G-ARCH.

### T-205 — `scripts/export_marts.py` + contract tests (initial slice)
**Objective.** `make export` writing `exports/mmm_input_weekly.csv` now; the other
five exports (SPEC-03 §5) added by their producing phases into this same script —
the script owns export schemas centrally with per-file contract tests on fixtures
(AD-050).
**Prerequisites.** T-204. **Outputs.** script + contract tests + `make export` wiring.
**Depends on:** T-204. **Blocks:** T-705, T-802, T-805 (BI feed).
**Acceptance criteria.** (1) Export schema contract test exists and passes for the
implemented file(s). (2) Script is additive — later phases extend a registry dict,
not copy-paste new scripts. (3) Exports land gitignored; `.gitkeep` intact.
**Traceability:** AD-050, SPEC-03 §5.

---

# Phase P3 — MMM on S-A (M2)

### T-301 — `model/transforms.py`: adstock convolution, Hill, scaling pair
**Objective.** Model-side transforms per MD-020/021/030: normalized-weight
fixed-length (L=8, from settings) geometric adstock as a vectorized pytensor op with
a mirrored numpy reference; Hill; `compute_scale_factors` / `to_model_scale` /
`from_model_scale` (revenue ÷ mean; spend ÷ per-channel nonzero mean).
**Prerequisites.** T-203 (schema knowledge), T-004. **Outputs.** module + tests.
**Depends on:** T-204. **Blocks:** T-302, T-304.
**Implementation notes.** Guide §2.1 — the single most bug-prone module (traps
T-1/T-2). Numpy reference implementation lives in the test file, not in `src`
(prevents accidental production use). Round-trip property test:
`from(to(x)) == x` to 1e-12. Zero-spend channels: nonzero mean uses only x>0 weeks;
all-zero channel ⇒ explicit error (cannot scale).
**Validation.** pytensor-vs-numpy equality to 1e-10 on random series; weight
normalization Σw=1; causality (impulse test — output zero before impulse).
**Acceptance criteria.** (1) All property tests green. (2) L read from settings only.
(3) Scaling round-trip test green. (4) No import from `ambo.simulate` (guard test).
**Traceability:** MD-020, MD-021, MD-030; traps T-1/T-2.

### T-302 — MD-070 shared-shape transform sanity test
**Objective.** Pre-fit gate: model transforms vs simulator transforms on the S-A
spend series correlate > 0.95 per channel — computed WITHOUT code sharing (each side
applies its own implementation; the test file orchestrates both).
**Prerequisites.** T-301, T-104. **Outputs.** `tests/unit/test_transform_sanity.py`.
**Depends on:** T-301. **Blocks:** T-307 (must be green before first fit).
**Implementation notes.** Uses truth λ per channel on both sides; correlation over
the adstock outputs (before Hill). Document in the test docstring why equality is
NOT expected (raw recursion vs normalized L=8 — MD-020's deliberate mismatch).
**Acceptance criteria.** (1) r > 0.95 all six channels on S-A. (2) Test imports both
packages but neither imports the other (guard test still green).
**Traceability:** MD-070; traps T-2/T-3.

### T-303 — `PriorConfig` + `config/priors_synthetic.yaml` + MD-040 guard
**Objective.** Pydantic `PriorConfig` mirroring SPEC-04 §4 structure (per-channel
λ Beta, K Gamma in scaled units, s truncated Gamma, β HalfNormal; the global block);
`priors_synthetic.yaml` with the MD-040 channel-agnostic values; a test asserting NO
channel-differentiated values in the synthetic file.
**Prerequisites.** T-004. **Outputs.** schema + YAML + tests.
**Depends on:** T-004. **Blocks:** T-304.
**Implementation notes.** Schema stores per-channel entries even when identical
(explicit > implicit) but the MD-040 test asserts value-equality across channels for
the synthetic file. K prior Gamma(2, 1.3) (≈ mode 0.77, mean 1.54 in scaled units ~
1.5× mean spend as specced).
**Acceptance criteria.** (1) YAML loads through schema with `extra='forbid'`. (2)
MD-040 equality test green. (3) All §4 distribution families and the global values
exactly as specced.
**Traceability:** MD-040, SPEC-04 §4.

### T-304 — `model/mmm.py`: `build_model` + prior-predictive sanity + smoke fit
**Objective.** MD-002 exactly:
`build_model(df, channels, priors) -> pm.Model` implementing SPEC-04 §2 math on
scaled variables — intercept, linear trend, order-4 yearly Fourier (period 52.18),
promo + advent + jan dummies, per-channel β·Hill(adstock); Normal likelihood. No
scenario branches. Plus the CI smoke-fit test (EB-060: S-A first 60 weeks, 1 chain,
200/200, asserts sampling completes and R-hat finite).
**Prerequisites.** T-301, T-303, T-204. **Outputs.** module + smoke test.
**Depends on:** T-301, T-303. **Blocks:** T-305–T-307.
**Implementation notes.** Guide §2.2 (variable naming table — names are API for
posterior_io and everything downstream; fix them here: `alpha, tau, gamma_sin_j,
gamma_cos_j, delta_promo, delta_advent, delta_jan, lam_c, k_c, s_c, beta_c, sigma`,
coords `channel`, `week`). Fourier features precomputed as data; dummies from mart
columns. Prior-predictive sanity check (not a gate): sampled prior predictive mean
within [0.2, 5]× observed mean — catches unit mistakes cheaply before MCMC.
**Validation.** Smoke test in CI; prior-predictive check test; model graph has
exactly the §2 terms (assert set of free RVs).
**Acceptance criteria.** (1) Free-RV name set matches the documented table. (2)
Smoke fit completes < 15 min in CI. (3) No branch on scenario/layer identifiers
inside the builder (grep test for 'S-A'/'layer' literals in mmm.py). (4)
`Implements: MD-002` in the docstring.
**Traceability:** MD-001, MD-002, MD-020..022, EB-060; DL-3 enabler.

### T-305 — `model/posterior_io.py`: netCDF + thinned parquet + scale factors
**Objective.** Save/load per MD-051 + BP-D-06: full ArviZ netCDF to gitignored local
path; thinned parquet (every 4th draw ⇒ 1000 rows, flat columns
`<var>[__<channel>]`) committed under `data/posteriors/<name>.parquet` with an
embedded metadata block (scale factors, data hash, prior file hash, sampler settings,
git commit, seed) written atomically (EB-050 temp+rename).
**Prerequisites.** T-304. **Outputs.** module + tests.
**Depends on:** T-304. **Blocks:** T-306, T-307, T-401+, T-701+.
**Implementation notes.** Guide §2.3. Metadata as parquet key-value file metadata +
sidecar-free (single file). Loader validates metadata presence and refuses files
without scale factors (they'd silently break back-transforms — trap T-1).
**Acceptance criteria.** (1) Round-trip test: save→load→identical draws + metadata.
(2) Thinning arithmetic proven (4000→1000). (3) Atomicity test (interrupt via
temp-file inspection: no partial file at final path). (4) Naming per BP-D-06.
**Traceability:** MD-051, EB-050, BP-D-06.

### T-306 — `model/diagnostics.py` + diag report writer
**Objective.** MD-071/072/074 machinery: R-hat, ESS bulk/tail, divergences, BFMI,
PPC coverage; writes `reports/model/diag_<layer>.md` with the gate table, PPC plot
PNG, energy plot when divergences > 0; Layer R relaxation profile switchable by
argument, never by autodetect.
**Prerequisites.** T-305. **Outputs.** module + tests (on smoke-fit idata fixture).
**Depends on:** T-305. **Blocks:** T-307, T-601.
**Implementation notes.** Gate thresholds from a `DiagGates` config object with two
constructors: `standard()` (MD-071) and `layer_r()` (MD-074) — explicit at call
site. PPC band = 90% central posterior predictive interval; coverage = share of
weeks inside.
**Acceptance criteria.** (1) Gate evaluation unit-tested against synthetic idata
with known properties (constructed pathological cases: injected divergence count,
low-ESS chain). (2) Report contains the mandatory table + plots. (3) Relaxed profile
only via explicit constructor.
**Traceability:** MD-071, MD-072, MD-074.

### T-307 — Fit runner + `make fit-synthetic` (S-A) + M2 gate
**Objective.** `python -m ambo.model.fit --layer P-SA [--variant …]` orchestrating:
mart read → scale → build → sample (MD-050 fixed settings from config) → posterior_io
save → diagnostics report; `make fit-synthetic` initially fits S-A; run the full S-A
fit; pass MD-071/072; commit `P-SA.parquet` + diag report.
**Prerequisites.** T-302 green, T-304–T-306. **Outputs.** runner, committed
posterior + report.
**Depends on:** T-302, T-304–T-306. **Blocks:** T-401, T-402; M2 exit.
**Implementation notes.** Runtime print up-front (EB-050). Variant flag reserved now
(`flat|nopromo|loco-<ch>|holdout`) — wired in P6 but parsed/validated here so the
interface is stable. If MD-071 fails: MD-073 ladder, one rung per attempt, ADR past
rung 1.
**Validation.** MD-071 all green on S-A full fit; MD-072 PPC ≥ 85%.
**Acceptance criteria.** (1) `data/posteriors/P-SA.parquet` committed with complete
metadata. (2) `reports/model/diag_P-SA.md` shows all gates green. (3) Two runs same
machine ⇒ ArviZ summaries match to 3 decimals (VR-701 pre-check). (4) M2 checklist
ticked in PR.
**Traceability:** MD-050, MD-051, MD-071..073; M2 exit; DL-8.

### T-308 — `model/elicit.py`: elicitation conversion helpers
**Objective.** MD-060's converters, built ahead of M4 (no data dependency):
`beta_params_from_halflife_range(lo_wk, hi_wk) -> (a, b)` (mode at implied λ, ~90%
mass in range), `gamma_params_from_k_range(lo_scaled, hi_scaled)`,
`sigma_beta_from_max_effect_share(share, mean_revenue_scaled)`.
**Prerequisites.** T-301 (λ↔half-life convention lives with transforms).
**Outputs.** module + tests.
**Depends on:** T-301. **Blocks:** T-509, T-510.
**Implementation notes.** Guide §3 (the small optimization: solve Beta(a,b) with
mode m and CDF(hi)−CDF(lo)=0.9 via scipy brentq over concentration; document the
λ = 2^(−1/halflife) mapping and its inverse; all conversions pure + deterministic).
**Acceptance criteria.** (1) Round-trip tests: given (a,b) → derived range covers
the implied λ with stated mass ±1%. (2) Monotonicity property tests. (3) Doctest
example per function (these get referenced from PRIOR_ELICITATION.md).
**Traceability:** MD-060, MD-061 enabler.

---

# Phase P4 — Recovery suite (M3)

### T-401 — `validate/recovery.py`: metrics engine VR-301..306
**Objective.** Compute, per scenario: ROAS coverage vs truth (per channel, 90% HDI
containment), Spearman rank of median ROAS vs true ROAS, response-curve MAE% over
the observed-spend grid vs truth curves, S-C zero-effect posterior P(ROAS<0.2) and
contribution share, half-life ranking check, total-media-share delta; evaluate
against the VR §3 gate table (per-scenario thresholds).
**Prerequisites.** T-107, T-307. **Outputs.** module + `RecoveryMetrics`/`GateResults`
types + tests on fixture posteriors.
**Depends on:** T-107, T-307. **Blocks:** T-406, T-410.
**Implementation notes.** Guide §4.1. ROAS draws = Σm_c/Σx_c computed from posterior
draws through model-side transforms + back-transform (from_model_scale) — never via
simulator code. Curve comparison restricted to observed-spend grid points (VR-303,
trap T-5). Gate table lives in a config dict mirroring VR §3 exactly; thresholds are
DATA, not code.
**Acceptance criteria.** (1) Metrics unit-tested on constructed posteriors with known
answers. (2) Gate table matches VR §3 cell-for-cell (reviewed against spec). (3)
Output serializes to the report + SSOT without recomputation.
**Traceability:** VR-301..306, VR-310.

### T-402 — Full fits S-B and S-C; commit posteriors
**Objective.** Run the T-307 runner for P-SB and P-SC (full MD-050 budget); pass
MD-071/072 per scenario; commit `P-SB.parquet`, `P-SC.parquet` + diag reports.
**Depends on:** T-307. **Blocks:** T-401's full evaluation, T-403…T-406.
**Implementation notes.** Expect S-C to be the stress case; MD-073 ladder applies;
wide HDIs acceptable, unhealthy sampling not.
**Acceptance criteria.** (1) Both posteriors committed with metadata. (2) Diag
reports green (standard profile). (3) Combined wall time logged in BUILD_LOG
(feeds the BP-D-18 compute ledger).
**Traceability:** MD-050/051/071; M3 enabler.

### T-403 — `validate/holdout.py` (VR-401)
**Objective.** Refit on first T−13 weeks per scenario (runner `--variant holdout`),
conditional forecast of the last 13 with actual spend, MAPE + 90%-interval coverage
vs seasonal-naive (`revenue_{t−52}`); committed summary CSVs
`reports/model/holdout_<layer>.csv` (BP-D-06 — no extra posteriors committed).
**Depends on:** T-307, T-402. **Blocks:** T-406, T-410.
**Implementation notes.** Guide §4.2: naive baseline needs ≥ 65 weeks (52+13) — true
for all scenarios; assert it. Forecast = posterior predictive with observed spend
matrices, seasonality/trend extended.
**Acceptance criteria.** (1) Model beats naive MAPE on S-A and S-B (gate). (2) CSV
schema contract-tested. (3) Coverage number reported alongside MAPE (A-7: never MAPE
alone).
**Traceability:** VR-401.

### T-404 — `validate/baseline_ols.py` (VR-601)
**Objective.** OLS with adstock fixed at prior-mode λ, no saturation, same other
regressors, HC1 errors (via statsmodels? — NO: statsmodels is not in SPEC-08 §3 and
adding a dep needs ADR; implement OLS + HC1 with numpy/scipy directly — small,
closed-form, unit-testable); side-by-side S-B table for the report.
**Depends on:** T-402. **Blocks:** T-406.
**Implementation notes.** Guide §4.3 (HC1 sandwich formula). Whatever the result, it
ships (spec's stated purpose: show why Bayesian machinery earns its complexity).
**Acceptance criteria.** (1) OLS + HC1 verified against a textbook example in tests
to 1e-8. (2) Output table columns: coef, HC1 se, sign-stability note vs Bayesian
median. (3) No new dependency added.
**Traceability:** VR-601, EB-030.

### T-405 — `validate/crosscheck.py` (VR-602, S-B)
**Objective.** pymc-marketing `MMM` fit on S-B with transforms/priors matched as
closely as its API allows; gate: channel-ROAS posterior-median correlation ≥ 0.8 vs
raw-PyMC; produce `reports/recovery/crosscheck_mapping.md` documenting every matched
and unmatchable element (gap-index item).
**Depends on:** T-402. **Blocks:** T-406.
**Implementation notes.** Guide §4.4. pymc-marketing imports confined to this module
(MD-003 — an import-location guard test). Version-pin sensitivity: record the
installed version in the mapping doc; API drift is RK-M3-2.
**Acceptance criteria.** (1) Correlation gate evaluated and reported. (2) Mapping doc
lists: adstock form, saturation form, prior-by-prior mapping table, anything
unmatched + why. (3) Guard test: `pymc_marketing` imported nowhere else in `src/`.
**Traceability:** VR-602, MD-003.

### T-406 — `validate/report.py`: RECOVERY_REPORT.md generator + plots
**Objective.** Generate `reports/recovery/RECOVERY_REPORT.md` in the exact VR §8
section order (verdict template with slots → gate table → recovery dot plots +
curve overlays per scenario → zero-effect headline → holdout table → OLS comparison →
crosscheck summary → ≥500-char honest-closing template), embedding PNGs produced
here from committed posteriors only (VR-703).
**Depends on:** T-401, T-403, T-404, T-405. **Blocks:** T-410; unlocks Layer R.
**Implementation notes.** Verdict/closing paragraphs are *templates with slots*
filled from gate results — no free-form generation (VR §8.1/8.8). Plot style via
`report/style.py` if T-801 already landed (parallel track) else minimal local style
to be swapped in P8 — prefer pulling T-801 forward (04_DEPENDENCIES §6 recommends it).
**Acceptance criteria.** (1) Section order machine-checked by a doc-structure test.
(2) Regeneration from committed posteriors only — delete local netCDF, run
`make recover`, report identical. (3) Closing section ≥ 500 chars, references
MD-020 mismatch + lift-test next step (VR §8.8 content requirements).
**Traceability:** VR §8, VR-703; DL-2.

### T-407 — Golden metrics: bands + regression tests (VR-701/702)
**Objective.** `scripts/generate_golden_metrics.py` → `tests/golden/
recovery_bands.json` (per scenario × channel: posterior-median ROAS ± 0.15·posterior
SD); golden test comparing committed posteriors' summaries against bands; VR-701
same-machine 3-decimal regression test using cached fits.
**Depends on:** T-402. **Blocks:** T-410.
**Implementation notes.** NEVER checksum draws (trap T-6). Regeneration path
documented in the script header: rerun + PR justification (EB-073).
**Acceptance criteria.** (1) Bands file committed, schema-tested. (2) Golden test
green in CI against committed parquets. (3) Band regeneration produces stable file
(sorted keys).
**Traceability:** VR-701, VR-702, EB-073; trap T-6.

### T-408 — SSOT: `scripts/generate_ssot.py` + `scripts/check_ssot_consistency.py`
**Objective.** SSOT generator producing `reports/NUMERIC_SSOT.md`
(`key|value|unit|tag|produced_by|updated_at`, GB-301) covering all GB-302 keys that
exist at this phase (recovery booleans, coverage stats, zero-channel verdict,
optimizer/Layer R keys appear later — generator reads a registry of producers and
emits what exists, BP-D-08 key splitting); consistency checker: numeric literals with
SSOT-adjacent units in README/EXEC_SUMMARY/RECOVERY_REPORT must match SSOT within
documented rounding, whitelist file with justification comments (GB-303).
**Depends on:** T-401, T-406. **Blocks:** T-410, CI job 4 goes strict.
**Implementation notes.** Guide §6. Producers register `(key, value, unit, tag,
source_artifact)`; the generator never computes analytics itself — it collects from
artifacts (report-side JSON side-files emitted by T-401/403/703/704).
**Acceptance criteria.** (1) SSOT regenerates deterministically (stable ordering,
timestamps from artifact mtimes not runtime clock — or a fixed `--as-of` arg; choose
artifact-derived to keep diffs meaningful). (2) Checker catches a planted mismatched
literal in a fixture doc (test). (3) Whitelist requires a justification comment per
entry (parse-enforced).
**Traceability:** GB-301..303, E-4; DL-8/DL-10 enabler.

### T-409 — `scripts/check_layer_order.py` + CI wiring
**Objective.** Git-ancestry enforcement (GB-501/502): recovery-report-before-Layer-R
and freeze-before-fit; green trivially while no Layer R artifact exists; wired as CI
job 5 with full history (BP-D-13).
**Depends on:** T-408 (reads `prior_freeze_commit` from SSOT), T-001.
**Blocks:** T-410; hard-guards P5/P6 forever.
**Implementation notes.** Guide §5: exact git plumbing (first-commit-adding-path via
`git log --diff-filter=A --follow`, ancestry via `git merge-base --is-ancestor`,
post-freeze modification via `git log <tag>.. -- <files>`), the GB-502 amendment
exception (appended amendment section committed before the fit + ADR — the script
allows appends that match the amendment header pattern, never edits to frozen
ranges; implement as: any post-tag change to `config/priors_real.yaml` fails; a
post-tag change to the elicitation doc passes only if the diff is append-only and
the added lines start under an `## Amendment` heading).
**Acceptance criteria.** (1) Green on current repo. (2) Simulated-violation tests
(construct throwaway repos in tmp via git init in tests) prove both failure modes
fire. (3) README (later, T-804) links this script (GB-503) — noted in traceability.
**Traceability:** GB-501..503, E-2, E-3, A-2.

### T-410 — M3 close: full gate run, report committed, Layer R unlocked
**Objective.** Run everything (`make recover`), verify VR §3–§6 all green, commit
RECOVERY_REPORT.md + posteriors + SSOT, tick M3 checklist, merge — this PR is the
commit GB-501 will reference forever.
**Depends on:** T-401…T-409.
**Acceptance criteria.** (1) All VR gates green in the pasted gate table. (2) SSOT
contains `recovery_pass_sa/sb/sc = true` + `zero_channel_verdict`. (3)
`make report` (no sampling) regenerates the report byte-stable. (4) BUILD_LOG entry
records the wall-clock compute ledger.
**Traceability:** M3 exit; Charter E-2; DL-2.

---

# Phase P5 — Agency intake (M4)

*T-501…T-506 are drop-independent — build them while waiting for the drop.*

### T-501 — Intake fixture generator (synthetic lookalikes)
**Objective.** `tests/fixtures/intake/make_fixtures.py` generating realistic private-
drop lookalikes (daily Google/Meta-style exports with campaign names, a billing
spend sheet, a shop revenue export, a promo list — all fake, clearly labeled) used
by all intake tests (AG-032: never real excerpts).
**Depends on:** T-010. **Blocks:** T-502…T-505 tests.
**Implementation notes.** Include deliberate dirt: partial edge weeks, a duplicate
day, a missing week range, a campaign that maps ambiguously, an umlaut encoding
quirk — each keyed to an AG gate it must trigger.
**Acceptance criteria.** (1) Fixtures deterministic (seeded). (2) Each planted defect
documented in the generator with the gate it exercises. (3) No string resembling a
real client (reviewed).
**Traceability:** AG-032, EB-071.

### T-502 — `intake/standardize.py` (stage 1)
**Objective.** Read private-drop inputs (any subset per SPEC-02 §2), map to canonical
schema + channel taxonomy via mapping rules declared in a config the human edits at
intake, aggregate daily→ISO weeks (partial edge weeks DROPPED, AG-050), write
STILL-PRIVATE intermediates to `$AMBO_PRIVATE_DROP/staged/`.
**Depends on:** T-501, T-004, T-005. **Blocks:** T-503.
**Implementation notes.** Guide §7.2. Fail fast if env var unset (AG-020 message).
Campaign→channel mapping rules as ordered regex list in a YAML the human writes
during intake (stored in the private drop, summarized into the manifest — rules
summaries are public, raw campaign names are not). Nothing from this module ever
writes inside the repo (path assertion in code + test).
**Acceptance criteria.** (1) Fixture run produces staged files with canonical
columns. (2) Partial-week dropping proven by test. (3) Repo-write-guard test green.
(4) Unmapped campaign ⇒ hard error listing the offending count (not names) in the
exception.
**Traceability:** AG-020, AG-030, AG-050, §5.2.

### T-503 — `intake/anonymize.py` (stage 2)
**Objective.** Apply AG-040..044: identity removal (drop campaign strings after
mapping), dual-factor rescaling (k_spend, k_rev read interactively or via private
env — never persisted), count scaling (per AG-042 or ADR'd k_cnt per BP-D-11),
whole-a€ rounding, column whitelist enforcement (only §5.3 columns), write
`data/real_anon/` + `INTAKE_MANIFEST.yaml`.
**Depends on:** T-502. **Blocks:** T-504, T-508.
**Implementation notes.** Guide §7.3. Factors: prompt at runtime (never CLI args —
shell history is a leak surface; never logged; never in manifest). Rejection rule
|k_spend−k_rev| < 0.15 enforced at entry. PII scrub: schema whitelist makes
free-text structurally impossible; additional regex pass (emails, URLs, phone
numbers) hard-fails (AG-044).
**Acceptance criteria.** (1) Fixture run end-to-end produces schema-exact public
files. (2) Planted PII in fixtures ⇒ hard fail (test). (3) Factor values absent from
all outputs, logs, and exceptions (test captures logging + output and greps). (4)
Manifest schema-validated (pydantic `IntakeManifest`, AG-066).
**Traceability:** AG-040..044, AG-031, AG-066; DL-9.

### T-504 — `intake/validate.py` + `make validate-intake` (AG-060..066)
**Objective.** Gate suite over `data/real_anon/`: continuity (gapless weeks, ≥ 52),
media↔outcome week consistency, `other` < 10%, spike rule (no week > 15% of window
spend), flighted-zero rules, revenue/spend ratio ∈ [1.5, 50], CTR ∈ [0.1%, 15%],
December-mean seasonality check, PII/leak scan invocation, manifest completeness;
writes `reports/ingestion/intake_validation.md`.
**Depends on:** T-503. **Blocks:** T-508 acceptance.
**Implementation notes.** Runs identically on fixtures (tests) and the real outputs
(human). Each gate: id, description, threshold, result, evidence stat — table
mirrors [10_VALIDATION_GATES.md](10_VALIDATION_GATES.md) format.
**Acceptance criteria.** (1) Every AG-060..066 gate implemented + fixture-tested both
passing and failing directions. (2) Report contains only scale-free/masked stats
(leak-scan clean on it, by test). (3) Exit codes: 0 all green else 1.
**Traceability:** AG-060..066; DL-9.

### T-505 — Leak scan full mode + pre-commit + intake-channel seed
**Objective.** Extend T-008: blocklist mode against `$AMBO_PRIVATE_DROP/
blocklist.txt`; pre-commit hook now runs full scan locally when env var set
(AG-045); stage 2 additionally emits `dbt/seeds/intake_channels.csv` (public:
channel, present, weeks) enabling AD-044 (BP-D-05).
**Depends on:** T-503, T-008. **Blocks:** T-506, T-508.
**Acceptance criteria.** (1) Blocklist hit in fixture ⇒ block (test). (2) Seed
schema-tested. (3) CI still runs pattern subset only (no env var in CI — asserted in
workflow review).
**Traceability:** AG-045, AD-044, BP-D-05.

### T-506 — dbt Layer R integration readiness
**Objective.** Make the `layer_r_present` flip a one-line change: staging unions
tested against fixture real_anon files in a tmp warehouse; AD-044 test wired to the
intake-channel seed; `fct_mmm_input` pivot verified with a channel subset (absent
channels → 0 columns present but zero-filled, presence recorded in dim_layer).
**Depends on:** T-203, T-505. **Blocks:** T-508.
**Acceptance criteria.** (1) With fixtures + var=true, `dbt build` green incl.
AD-044. (2) With var=false (CI state pre-M4), build green and no Layer R rows
anywhere. (3) dim_layer Layer R row correct on fixtures.
**Traceability:** AD-044, BP-D-05, §5.2 subset handling.

### T-507 — [HUMAN] Permission confirmation + `docs/DATA_PERMISSION.md` + ADR-001
**Objective.** Human secures written permission (stored privately); repo gets
`docs/DATA_PERMISSION.md`: permission exists, from whom in role terms, date, scope —
no names (AG-001). ADR-001 records the outcome + sector labeling choice (AG-040).
**Depends on:** external. **Blocks:** T-508. **Hard deadline:** end of M4 else
Charter §7 ADR (AG-002 — no gray-zone processing).
**Acceptance criteria.** (1) Doc contains the four required elements, zero names.
(2) ADR-001 merged. (3) Leak scan green on both.
**Traceability:** AG-001, AG-002, GB-202.

### T-508 — [HUMAN+agent] Execute intake on the private drop; commit outputs
**Objective.** Human runs `make intake` then `make anonymize` (drawing factors per
AG-041), agent supports; `make validate-intake` green; commit ONLY `data/real_anon/*`
+ manifest + ingestion report + intake-channel seed + dbt var flip; ADR-002 (channel
mapping + `other` share + BP-D-04 decision), ADR-003 (anonymization recipe version;
factors' existence and storage location, never values; BP-D-11 decision), ADR-004
(window + reconstructions).
**Depends on:** T-502…T-507. **Blocks:** T-509 finalization, T-510, P6.
**Acceptance criteria.** (1) AG-060..066 green on real outputs (report committed).
(2) Full local leak scan green; CI leak scan green. (3) The commit contains
exclusively the enumerated public artifacts (reviewed file-by-file — checklist
[06 §M4](06_CHECKLISTS.md)). (4) ADR-002/003/004 merged. (5) dbt build green with
Layer R live (AD-044 green against the real manifest seed).
**Traceability:** AG-030..066, GB-202; DL-9; M4 core.

### T-509 — Elicitation doc structure + MD-061 doc-lint test
**Objective.** Agent drafts `docs/PRIOR_ELICITATION.md` skeleton: one section per
Layer R channel (from the real manifest) with the exact MD-060 field structure
(half-life range → Beta via elicit.py; K range in relative terms → Gamma; max weekly
effect share → σβ; ≥100-char first-person rationale placeholder markers that FAIL
the lint until replaced; source field); implement `tests/test_elicitation_doc.py`
(parses doc, presence, rationale length + boilerplate rejection, YAML↔doc value
match via converters).
**Depends on:** T-308, T-508 (channel list). **Blocks:** T-510.
**Implementation notes.** Boilerplate rejection: reject rationales matching template
markers, duplicated across channels (pairwise similarity), or lacking first-person
tokens. The lint is the enforcement of "this field is the portfolio signal".
**Acceptance criteria.** (1) Lint fails on the skeleton (by design — proves it
bites). (2) Lint's YAML-match check runs converters exactly (tolerance stated). (3)
Doc includes the MD-062 freeze-statement slot (commit hash filled at T-510).
**Traceability:** MD-060..062.

### T-510 — [HUMAN+agent] Elicitation content + `priors_real.yaml` + FREEZE
**Objective.** Human authors rationales/ranges (their agency experience — agent
drafts structure only, AGENTS §2.2); agent converts ranges → YAML via elicit.py;
single freeze commit adds both files; tag `prior-freeze-v1`; SSOT records
`prior_freeze_commit`; MD-061 lint green; layer-order check green.
**Depends on:** T-509, T-508. **Blocks:** P6 entirely (E-3).
**Acceptance criteria.** (1) One commit contains both files finalized; tag on it
(BP-D-07). (2) MD-061 green. (3) `check_layer_order.py` green with freeze recognized.
(4) No Layer R fit artifact exists anywhere yet (script-verified). (5) M4 checklist
ticked; BUILD_LOG entry.
**Traceability:** MD-041, MD-060..062, E-3, GB-502; DL-6.

---

# Phase P6 — Layer R fit + sensitivity (M5)

### T-601 — Layer R fit + diagnostics (relaxed profile) + committed posterior
**Objective.** `python -m ambo.model.fit --layer R` under frozen priors; diagnostics
with `DiagGates.layer_r()` (MD-074: ESS > 300; ≤5 divergences only with energy plot +
funnel-free pair plots + human review note in the report); commit `R.parquet` +
`reports/model/diag_R.md`.
**Depends on:** T-510. **Blocks:** T-602…T-605, T-705.
**Implementation notes.** Wide HDIs are content, not failure. If the ladder is
needed: MD-073 order, ADR-005 past rung 1; rung 4 forces re-running P4 recovery.
**Acceptance criteria.** (1) Diag report green under the relaxed profile with all
required evidence plots. (2) Posterior metadata records frozen prior file hash =
freeze-commit blob hash (mechanical freeze check). (3) CI layer-order + freeze
checks green on the PR.
**Traceability:** MD-050/051/074, GB-501/502; DL-3.

### T-602 — VR-501 prior-influence + VR-503 S-B contrast
**Objective.** Refit R with `priors_synthetic.yaml` (`--variant flat` ⇒
`R__flat.parquet`); refit S-B likewise (`P-SB__flat.parquet`); forest plot per
channel (elicited vs flat, R) `reports/recovery/vr_prior_influence.png` + the
combined R-vs-S-B figure; one analysis paragraph (template slots: where elicitation
moved/narrowed).
**Depends on:** T-601. **Blocks:** T-605, T-802 (RB-205 restyles this).
**Acceptance criteria.** (1) Both variant posteriors committed (BP-D-06 names). (2)
Figure regenerates from committed parquets only. (3) Paragraph references ≥ 2
channels by name with numeric deltas (SSOT-fed).
**Traceability:** VR-501, VR-503; DL-3; the portfolio centerpiece.

### T-603 — VR-502 LOCO + VR-504 no-promo sensitivity
**Objective.** Leave-one-channel-out refit (largest-spend channel ⇒
`R__loco-<ch>.parquet`): report contribution re-attribution; no-promo refit
(`R__nopromo.parquet`): ROAS shifts table → feeds LIMITATIONS §6.
**Depends on:** T-601.
**Acceptance criteria.** (1) Re-attribution table: dropped channel's contribution
share redistribution with HDIs. (2) No-promo ROAS delta table with HDIs. (3) Both
regenerate without sampling from committed variants.
**Traceability:** VR-502, VR-504, R-9.

### T-604 — Layer R holdout + cross-check
**Objective.** VR-401 on R (reported either way, n=13 caveat mandatory) → SSOT
`holdout_mape_real`; VR-602 crosscheck on R (no gate — comparison paragraph +
mapping-doc addendum).
**Depends on:** T-601.
**Acceptance criteria.** (1) Holdout CSV + SSOT row with caveat text slot. (2)
Crosscheck paragraph with correlation number. (3) No new posterior committed beyond
the defined variants (holdout summarized as CSV per BP-D-06).
**Traceability:** VR-401, VR-602.

### T-605 — M5 close: short-data narrative + SSOT + gates
**Objective.** Assemble the M5 evidence: diag summary, sensitivity artifacts,
holdout, SSOT keys (`roas_<channel>_median/_hdi90_lo/_hi`, `layer_r_weeks`,
`divergences_real_fit`, `media_share_of_revenue_real`, `holdout_mape_real`); tick M5
checklist; merge.
**Depends on:** T-601…T-604.
**Acceptance criteria.** (1) All listed SSOT keys present with tags (MODELED /
REAL-ANON as appropriate). (2) M5 checklist ticked with artifact links. (3)
`make sensitivity` green end-to-end without refitting.
**Traceability:** M5 exit; GB-302; DL-3.

---

# Phase P7 — Decision layer (M6)

*T-701…T-704 need only P4 (Layer P posteriors + truth) — schedule inside the drop
wait if it is still open.*

### T-701 — `decide/optimizer.py`: SAA objective, constraints, solver
**Objective.** DC-201..204 exactly: steady-state expected contribution objective
averaged over first 500 thinned draws; constraints Σx=B, 0 ≤ x_c ≤ 1.3×max observed
weekly spend, `search_brand` fixed at historical mean (+ `other` fixed, BP-D-04);
SLSQP with 20 seeded-Dirichlet restarts; restart-spread convergence report;
uncertainty by evaluating x* under all 1000 draws.
**Depends on:** T-305, T-410. **Blocks:** T-702, T-703, T-705.
**Implementation notes.** Guide §5 (numerics: optimize in share-space with B
factored out; analytic gradient of Hill worth supplying; seeded restarts via
`numpy.random.Generator(PCG64(seed))`; determinism DC-703 requires fixed draw subset
+ fixed restart seeds).
**Acceptance criteria.** (1) Constraint audit test: Σ=B to 1e-6, bounds exact,
fixed channels unchanged (DC-704). (2) Two runs byte-identical outputs (DC-703).
(3) Convergence report emitted; spread > 1% ⇒ warning flag in output (DC-204). (4)
On a hand-constructed 2-channel toy with known optimum: solver finds it to 1e-4
(unit test).
**Traceability:** DC-201..204, DC-703, DC-704.

### T-702 — Optimizer recovery test (DC-401) on S-A/S-B
**Objective.** Optimize under (i) true parameters (SPEC-01 parameterization,
BP-D-16) and (ii) posterior; gates: S-A cosine ≥ 0.90 & regret ≤ 5% (regret
evaluated under TRUE params); S-B cosine ≥ 0.80 & regret ≤ 10%; RECOVERY_REPORT
addendum + SSOT `optimizer_regret_sb`.
**Depends on:** T-701, T-107.
**Acceptance criteria.** (1) Both gates green. (2) Addendum section appended via the
report generator (not hand-edited). (3) SSOT key written with tag MODELED.
**Traceability:** DC-401, DC-701; BP-D-16.

### T-703 — `decide/scenarios.py`: budget scenarios + next-euro ladder
**Objective.** DC-205: B ∈ {0.8, 1.0, 1.2}×mean → `exports/allocation_scenarios.csv`
(historical share, optimal share, spend, expected contribution mean + HDI, binding-
constraint flags); DC-301 gain metric (+HDI, +annualized) → SSOT; DC-601 ladder:
±a€500/week marginal contribution per reallocatable channel → SSOT
`next_euro_best_channel`, `next_euro_marginal_roas`.
**Depends on:** T-701. **Blocks:** T-705, T-802 (RB-201 feed).
**Acceptance criteria.** (1) Export schema contract-tested (AD-050 registry). (2)
Gain metric formula exactly DC-301 (test on constructed posterior). (3) Ladder
excludes `search_brand` + `other`; caption from `captions.py` (DC-302) attached in
all rendered artifacts.
**Traceability:** DC-205, DC-301/302, DC-601; DL-4.

### T-704 — `decide/attribution_gap.py` + DC-502 ordering gate
**Objective.** Per channel with platform data: platform ROAS, MMM ROAS (mean+HDI),
overcredit ratio, P(platform > MMM); Layer P S-B gate: recovered overcredit ordering
= φ ordering (display_video > meta > search_generic > search_brand); Layer R output
`exports/attribution_gap.csv` + dumbbell chart; DC-504 interpretation paragraph
(≥500 chars, template with number slots).
**Depends on:** T-701 (shared posterior plumbing), T-106, T-410; Layer R part needs
T-601.
**Acceptance criteria.** (1) DC-502 ordering gate green on S-B. (2) Masked-unit
cancellation documented in module docstring (platform ROAS is ratio-valid under
AG-041/042). (3) Chart + CSV regenerate via `make decide` with no sampling. (4)
Paragraph ≥ 500 chars, references ≥ 3 numeric results, tone constraint (no vendor-
bashing) noted for review.
**Traceability:** DC-501..504, SIM-061; DL-5.

### T-705 — M6 close: Layer R decision run + gates + SSOT
**Objective.** Full `make decide` on Layer R; DC-701..705 all green; exports +
charts committed where specced; SSOT gain/gap/next-euro keys written; M6 checklist;
merge.
**Depends on:** T-702…T-704, T-601.
**Acceptance criteria.** (1) DC-701..705 table pasted in PR, all green. (2)
`expected_gain_pct` + bounds + `expected_gain_aeur_annual` +
`overcredit_ratio_<channel>` in SSOT, tagged MODELED. (3) Determinism re-proven on
final artifacts.
**Traceability:** DC-701..705; M6 exit; DL-4, DL-5.

---

# Phase P8 — Reporting & release (M7)

### T-801 — `report/style.py`, `format.py`, `captions.py`
**Objective.** Chart standards (RB §7): matplotlib Agg, 12×6 in, dpi 150, Okabe-Ito
with FIXED per-channel colors; formatter functions (`a€1.2 M`, `3.4×`, 1-decimal
percentages — all tested); captions module = single home of the a€ caption
(Charter E-5), DC-302 counterfactual caption, AG-070 anonymization paragraph —
grep-test enforces single occurrence in `src/` (GB-102).
**Depends on:** T-004. *(Parallel-track: pull forward to P4 so T-406 uses it.)*
**Acceptance criteria.** (1) Channel→color map is total over the taxonomy and
test-asserted stable. (2) Formatter unit tests cover the three formats incl. edge
cases (0, negatives, >10M). (3) Grep-test green: each caption string occurs exactly
once in `src/`.
**Traceability:** RB §7, GB-102, E-5.

### T-802 — `report/charts.py`: five executive charts + RB-301 test
**Objective.** RB-201..205 exactly (titles, content, captions as specced), reading
only exports/SSOT-backed frames + committed posteriors; `make report` target; RB-301
test recomputing RB-201's bars from `allocation_scenarios.csv` and asserting match;
RB-302: regeneration without sampling.
**Depends on:** T-801, T-703, T-704, T-602. Layer P variants buildable earlier —
degradation-proof (RB §6.1) by parameterizing the data layer.
**Acceptance criteria.** (1) Five PNGs regenerate deterministically (`make report`
twice → identical files). (2) RB-301 test green. (3) Every chart: business-English
title, unit axes, source note bottom-left, epistemic tag bottom-right (assert via a
chart-metadata helper, reviewed visually once). (4) No chart code reads warehouse or
refits (imports audit).
**Traceability:** RB-201..205, RB-301/302; DL-7 support, DL-10.

### T-803 — Exports completion + `reports/EXEC_SUMMARY.md`
**Objective.** Complete the AD-050 export registry (all six CSVs); write
EXEC_SUMMARY per RB §5 mandatory structure (≤2 pages, every number from SSOT with
tags, DC-302 caption verbatim, freeze commit hash in "Why trust this").
**Depends on:** T-705, T-605, T-802.
**Acceptance criteria.** (1) All six exports contract-tested. (2)
`check_ssot_consistency.py` green over EXEC_SUMMARY. (3) Structure sections 1–6 in
order (doc-structure test). (4) Every claim carries a number + HDI + tag (review
checklist item).
**Traceability:** AD-050, RB §5, A-7/A-8; DL-3/4/5 surfacing.

### T-804 — README.md + LIMITATIONS.md
**Objective.** README per RB §6 exact order (both framing variants drafted in the
repo per RB §6.1 — active one at root, alternate as a clearly-marked section of the
spec-designated location); LIMITATIONS ≥ the nine GB §6 items with live numbers
(`layer_r_weeks`, VR-501 prior-domination findings, AG-041 preserved/destroyed list
verbatim, DC-302, T-7 brand-search paragraph, VR-504 outcome, L=8 cap, φ/θ
epistemics, VR §7 reproducibility doctrine).
**Depends on:** T-803; degradation variant depends only on P4.
**Acceptance criteria.** (1) README section order machine-checked; leads with
recovery + Layer R answer (DL-10); RB-201 then RB-202 embedded; stack talk first in
§8; `check_layer_order.py` linked (GB-503). (2) LIMITATIONS covers all nine items —
checklist mapping each item to its section. (3) SSOT consistency green over README.
(4) a€ caption appears wherever a€ values shown (E-5).
**Traceability:** RB §6, GB §6, GB-503; DL-9, DL-10.

### T-805 — [HUMAN] Power BI dashboard + screenshots
**Objective.** Human builds `dashboards/ambo.pbix` per RB-401..405 on the six
exports; agent prepares `dashboards/README.md` (rebuild instructions, data-source
rewiring steps) and the export refresh; screenshots to
`docs/assets/dashboard_p1..p4.png`.
**Depends on:** T-803.
**Acceptance criteria.** (1) Four pages match RB-401..404 content lists. (2) German
subtitles + a€ footer verbatim from captions.py (RB-405). (3) `.pbix` + 4 PNGs
committed; README rebuild path tested by a second person/agent following it.
**Traceability:** RB-401..406; DL-7.

### T-806 — Release audit: DL-1..10, final SSOT, tag v1.0
**Objective.** Execute the Release checklist ([06 §M7](06_CHECKLISTS.md)): fresh-
clone reproduction probe (DL-1: `make setup && make all` on committed artifacts —
Layer P bit-for-bit within tolerance doctrine, no private inputs), every DL verified
against its expanded criteria ([11 §4](11_ACCEPTANCE_CRITERIA.md)), final SSOT
regeneration, LIMITATIONS cross-check, leak scan full, tag `v1.0`.
**Depends on:** T-801…T-805.
**Acceptance criteria.** (1) DL-1..10 table with evidence links, all green, in the
release PR. (2) Fresh-clone probe log attached. (3) Tag `v1.0` on the merge commit.
(4) BUILD_LOG final entry with total effort vs Charter §5 budget.
**Traceability:** Charter §4 (all DLs), M7 exit; G-REL.
