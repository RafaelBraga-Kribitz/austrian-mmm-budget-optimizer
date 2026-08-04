# SPEC-08 — Engineering, Tooling, CI (AMBO)

Requirement IDs: `EB-xxx`. Same engineering culture as the sibling repos; the
MMM-specific additions are the sampling-compute strategy (§6) and the leak scan.

---

## 1. Toolchain

- EB-001: Python 3.12 + `uv`; `ruff` (lint+format, line 100); `mypy --strict` on
  `src/ambo/` (ignore_missing_imports for pymc/arviz/pytensor).
- EB-002: `pre-commit`: ruff, ruff-format, end-of-file-fixer, check-yaml,
  detect-private-key, `scripts/leak_scan.py --staged` (AG-045), nbstripout (notebook
  outputs never committed — leak surface).

## 2. Repository layout (canonical; empty dirs get `.gitkeep`)

This is the canonical set of packages and directories. **No new top-level directory or
`src/ambo/` subpackage may be added without an ADR.** New *modules inside* a listed
package are permitted and expected, on one condition: the module has a public contract
entry in the module-contract document (`03_MODULES`, internal execution blueprint)
merged in the same PR (contract-first). The per-package file lists below are the
contracts known at authoring time, not a closed set.

```
austrian-mmm-budget-optimizer/
├── PROJECT_CHARTER.md          ├── AGENTS.md
├── README.md                   ├── LIMITATIONS.md
├── LICENSE (MIT)               ├── Makefile
├── pyproject.toml              ├── .pre-commit-config.yaml
├── .gitignore                  ├── .env.example        # AMBO_PRIVATE_DROP only
├── config/
│   ├── settings.yaml           # channel lists, windows, L (adstock length), paths
│   ├── scenarios/              # s_a.yaml, s_b.yaml, s_c.yaml  (SPEC-01)
│   ├── priors_synthetic.yaml   # MD-040
│   └── priors_real.yaml        # MD-041, frozen M4
├── src/ambo/
│   ├── simulate/    (config.py, dgp.py, spend_patterns.py, platform_bias.py,
│   │                 truth.py, __main__.py)
│   ├── intake/      (standardize.py, anonymize.py, validate.py)
│   ├── model/       (mmm.py, priors.py, fit.py, transforms.py, elicit.py,
│   │                 diagnostics.py, posterior_io.py)
│   ├── validate/    (recovery.py, holdout.py, sensitivity.py, baseline_ols.py,
│   │                 crosscheck.py, report.py)
│   ├── decide/      (optimizer.py, attribution_gap.py, scenarios.py)
│   ├── report/      (charts.py, format.py, style.py, captions.py)
│   └── common/      (config.py, db.py, logging.py)
├── dbt/             (dbt_project.yml, profiles.yml, models/, seeds/season_windows.csv)
├── scripts/         (generate_ssot.py, export_marts.py, generate_golden_metrics.py,
│                     check_ssot_consistency.py, check_layer_order.py, leak_scan.py)
├── data/            (synthetic/ COMMITTED, real_anon/ COMMITTED,
│                     posteriors/ COMMITTED (thinned parquet only),
│                     warehouse/ + cache/ + local netCDF gitignored)
├── exports/         (*.csv COMMITTED — DL-1 compares against them; EB-081)
├── reports/         (committed: NUMERIC_SSOT.md, EXEC_SUMMARY.md, recovery/, model/,
│                     decide/, executive_charts/, ingestion/)
├── dashboards/      (ambo.pbix, README.md)
├── docs/            (SPEC-01..09, PRIOR_ELICITATION.md, DATA_PERMISSION.md, ADR/,
│                     assets/, BUILD_LOG.md)
└── tests/           (unit/, fixtures/, golden/)
```

## 3. Dependencies (pin; upgrades need ADR)

Runtime: `pandas>=2.2,<3`, `numpy>=1.26,<3`, `pymc>=5.15,<6`, `arviz>=0.18`,
`pytensor` (as pinned by pymc), `pymc-marketing>=0.8` (crosscheck only),
`scipy>=1.13`, `duckdb>=1.0`, `dbt-core>=1.8,<2`, `dbt-duckdb>=1.8,<2`,
`holidays>=0.50`, `matplotlib>=3.8`, `pydantic>=2.7`, `PyYAML>=6`, `python-dotenv>=1`.
Dev: `pytest>=8`, `pytest-cov`, `ruff`, `mypy`, `pre-commit`, `nbstripout`.
- EB-030: `uv.lock` committed. Forbidden-deps test (no robyn/lightweight_mmm/
  prophet/sklearn — Charter O-3 at dependency level).

## 4. Configuration & secrets

- EB-040: All non-secret settings in `config/`, loaded once via pydantic Settings.
- EB-041: The ONLY env var is `AMBO_PRIVATE_DROP` (path). It is not a secret per se,
  but its CONTENTS are — no code may copy from it except `intake/standardize.py`,
  and nothing under it is ever logged (logger filter asserts path not in messages).

## 5. Makefile (canonical interface)

```
setup            uv venv + install + pre-commit install
simulate         build all 3 scenarios + truth files
validate-sim     SIM gates
intake           stage-1 standardize (requires AMBO_PRIVATE_DROP)   [human runs]
anonymize        stage-2 → data/real_anon/                          [human runs]
validate-intake  AG gates
transform        dbt build
fit-synthetic    fit S-A, S-B, S-C (full sampling budget)
fit-real         fit Layer R (frozen priors)
recover          recovery suite + RECOVERY_REPORT.md
sensitivity      VR-5xx suite
decide           optimizer + attribution gap
ssot             generate SSOT
export           exports/
report           executive charts (from committed posteriors — no sampling)
test             pytest -q (coverage ≥ 80% src/)
lint             ruff + mypy
all              transform→recover→sensitivity→decide→ssot→export→report
                 (assumes fits exist; fits are explicit targets because of their cost
                  — see 07_QUALITY_STANDARDS Part A for the normative per-fit ceiling.
                  `make all` therefore does NOT reproduce data/synthetic/ or any
                  posterior; the DL-1 probe is 11_ACCEPTANCE_CRITERIA §4, not this)
```

- EB-050: Sampling targets print expected runtime up front and write posteriors
  atomically (temp + rename) so an interrupted fit never leaves partial files.

## 6. CI (`ci.yml` — the only workflow; Charter O-7: no cron)

- EB-060: Jobs, all required: (1) lint; (2) test — includes the SMOKE-FIT: build S-A
  60-week subset, 1 chain × 200/200 draws, assert it samples without error and
  R-hat is finite (< 15 min budget; marked `@pytest.mark.smoke`, runs in CI, skipped
  in `make test` locally unless `SMOKE=1`); (3) dbt build on committed data (synthetic
  + real_anon are in-repo, so CI needs no private inputs); (4)
  `check_ssot_consistency.py`; (5) `check_layer_order.py` (SPEC-09 §5); (6)
  `leak_scan.py` pattern subset.
- EB-061: Full fits NEVER run in CI (cost); golden comparisons in CI run against the
  committed thinned posteriors with VR-702 tolerance bands.

## 7. Testing policy

- EB-070: No network in any test (this project needs none anywhere — a selling point:
  assert no `requests` import outside intake, which itself only reads local files).
- EB-071: Synthetic test fixtures live under `tests/fixtures/` only; intake fixtures
  are generated lookalikes (AG-032), never real excerpts.
- EB-072: Coverage ≥ 80%; every post-M2 bug gets a regression test in its fix PR.
- EB-073: Golden: VR-702 bands + DC determinism. Regeneration via
  `scripts/generate_golden_metrics.py` + PR justification.

## 8. Git conventions

- EB-080: Conventional commits + REQ IDs; one milestone = one PR; `main` protected by
  all six CI jobs.
- EB-081: `.gitignore`: `.venv/`, `data/warehouse/`, `data/cache/`, `*.nc`, `.env`,
  `__pycache__/`, `.pytest_cache/`, `dbt/target/`, `dbt/logs/`, `.ipynb_checkpoints/`.
  NOTE committed-by-design: `data/synthetic/`, `data/real_anon/`,
  `data/posteriors/*.parquet`, **`exports/*.csv`**. The exports are committed for two
  reasons: DL-1's release probe compares regenerated exports against committed versions
  and has nothing to compare against otherwise (and RB-301 recomputes RB-201 bars from
  `allocation_scenarios.csv`), and a reader can inspect the project's headline numbers
  on the forge without cloning or installing anything. They are small, text, and
  diffable — a changed export shows up in review, which is the point.
- EB-082: History is append-only: no force-push, no history rewriting, ever — the
  layer-order argument (Charter §5) depends on trustworthy history. If something
  private lands in a commit: the remedy is credential/data rotation + repo surgery
  performed BY THE HUMAN with the leak documented; agents never rewrite history
  themselves (AGENTS A-4).
