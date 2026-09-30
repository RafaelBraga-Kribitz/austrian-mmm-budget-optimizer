# ADR-009: Spec sections not built and not planned

- **Status:** Accepted
- **Date:** 2026-09-30
- **Deciders:** Rafael Braga-Kribitz
- **Supersedes:** none. Replaces the pointer to reserved slot ADR-002 in ADR-008 (see Consequences).
- **Related:** STATUS.md D-04, D-29, D-31, D-33; ADR-000; ADR-008; `docs/specs/SPEC-01` to `SPEC-09`; `docs/archive/README.md`; `docs/AUDIT_2026-09-30.md` items 3 and 20

---

## Context

The nine specs in `docs/specs/` were written for the planning stack: a GSD workflow
with a DuckDB and dbt warehouse, a subpackage per stage, a Makefile and a set of
governance scripts. That stack was stopped (STATUS D-29, D-31). The package on `main`
is the slim PyMC pipeline (Layers P, R, D) that salvaged functions from it (D-04).

ADR-008 records the shipped behaviour that differs from the specs (five channels,
matched adstock, LogNormal slope, 26-week holdout, Python 3.11). It does not say which
spec sections describe code, files and checks that do not exist. A reader who follows
a spec looks for them and finds nothing. The 2026-09-30 audit (items 3 and 20) asked
for one record that closes this gap.

## Decision

The sections below were never built and will not be built for this package. Each spec
file carries a banner that points here. The specs stay in the repository as the design
record; where a section below and the code disagree, the code and ADR-008 describe what
exists.

This ADR covers only what is missing. Numeric deviations of shipped behaviour are in
ADR-008 and STATUS.

### 1. Mechanisms not built

| Spec section | What it describes | Status |
|--------------|-------------------|--------|
| SPEC-02, whole spec | Agency intake in `src/ambo/intake/` (`standardize.py`, `anonymize.py`, `validate.py`), the `AMBO_PRIVATE_DROP` variable, `.env.example`, `data/real_anon/`, `INTAKE_MANIFEST.yaml`, `docs/DATA_PERMISSION.md`, `reports/ingestion/`, the AG-06x gates, `scripts/leak_scan.py` | Not built. No client data has been processed. The permission rule (AG-001, AG-002) and the anonymisation recipe (AG-040 to AG-044) remain the stated protocol for a client drop and are what LIMITATIONS.md section 3 cites. Intake, if it happens, is a mapping step recorded in a new ADR (ADR-008, Consequences). |
| SPEC-03, whole spec | DuckDB file `data/warehouse/ambo.duckdb`, dbt project `dbt/`, marts `fct_mmm_input`, `dim_layer`, `fct_platform_reported`, `ambo/common/db.py`, the AD-04x dbt tests, `exports/` | Not built. duckdb was removed from the dependencies. The model reads CSV directly: Layer P from `data/synthetic/`, Layer R from `data/layer_r/dt_simulated_weekly.csv` through `ambo.layer_r`. |
| SPEC-04 section 6 | Prior elicitation: `docs/PRIOR_ELICITATION.md`, `ambo/model/elicit.py`, `tests/test_elicitation_doc.py`, frozen `config/priors_real.yaml` | Not built. Layer R priors are the weakly informative `priors` block of `src/ambo/configs/layer_r.yaml`, not elicited and not frozen. |
| SPEC-04 section 2 | Promo, Advent and January-dip dummies on top of the Fourier terms | Not built. Each layer has one control: public-holiday weeks on Layer P, competitor sales on Layer R (D-24). |
| SPEC-05 sections 5 and 6 | Sensitivity suite VR-501 to VR-504 (prior swap, leave-one-channel-out, no-promo refit), OLS HC1 baseline VR-601, pymc-marketing cross-check VR-602 | Not built. The holdout compares against a ridge regression and a seasonal-naive forecast (`src/ambo/baselines.py`). LIMITATIONS.md section 4 names the missing prior-sensitivity refit. |
| SPEC-05 section 7 | Golden bands `tests/golden/recovery_bands.json` from `scripts/generate_golden_metrics.py` | Not built. |
| SPEC-01 section 5, SPEC-05 section 3 | Three scenarios S-A, S-B, S-C with per-scenario gates and a zero-effect channel | Not built. Layer P is one 156-week scenario. |
| SPEC-06 section 4, DC-502, DC-503 | Optimizer recovery test on true parameters, overcredit ordering gate, Layer R attribution gap | Not built. The attribution gap runs on Layer P only; the Robyn file has no platform-reported revenue. |
| SPEC-07 sections 2 and 4 | Five executive charts in `reports/executive_charts/`, `reports/EXEC_SUMMARY.md`, `dashboards/ambo.pbix`, `docs/assets/dashboard_p1..p4.png` | Not built as specified. Charts are per layer under `reports/layer_p/`, `reports/layer_r/`, `reports/layer_d/`; the summary is `reports/memo_EN.md` and `docs/summary_de.md`; the dashboard is specified in `docs/dashboard_handoff.md` and not yet built. |
| SPEC-09 section 3 | `reports/NUMERIC_SSOT.md` from `scripts/generate_ssot.py`, checked by `scripts/check_ssot_consistency.py` | Not built. Rendered numbers are recorded in `reports/readme_values.json` and `reports/summary_de_values.json` by the render scripts and checked by `tests/test_readme_numbers.py`. |
| SPEC-09 section 5 | `scripts/check_layer_order.py`: git-ancestry checks GB-501 and GB-502, and the prior freeze | Not built and will not be. Layer P was merged to `main` before the first Layer R commit (STATUS, Done table), but no script checks it, and there is no prior freeze to check. |
| SPEC-08 sections 1, 5 and 6 | `mypy --strict`, `.pre-commit-config.yaml`, nbstripout, the Makefile and every `make` target, the six-job CI | Not built. There is no Makefile. The commands are `uv run python -m ambo.run layer_p`, `layer_r`, `layer_d` and the scripts below. CI is `.github/workflows/ci.yml`. |
| SPEC-02 AG-070, SPEC-07 section 7, SPEC-09 GB-102 | Single caption module `ambo/report/captions.py` | Not built. Captions are written where they are used: the README template, the render scripts, the chart code and `docs/dashboard_handoff.md`. |

### 2. Paths the specs name and what exists instead

| Spec path | What exists |
|-----------|-------------|
| `src/ambo/simulate/` | `src/ambo/synth.py` |
| `src/ambo/intake/` | nothing (section 1) |
| `src/ambo/model/` (`mmm.py`, `priors.py`, `fit.py`, `transforms.py`, `diagnostics.py`, `posterior_io.py`) | `src/ambo/model.py`, `src/ambo/transforms.py`, `src/ambo/diagnostics.py` |
| `src/ambo/validate/` (`recovery.py`, `holdout.py`, `baseline_ols.py`, `report.py`) | `src/ambo/evaluate.py`, `src/ambo/baselines.py` |
| `src/ambo/decide/` (`optimizer.py`, `scenarios.py`, `attribution_gap.py`) | `src/ambo/optimize.py`; the attribution gap is in `src/ambo/evaluate.py` |
| `src/ambo/report/` (`charts.py`, `style.py`, `format.py`) | `src/ambo/plots/charts.py`, `src/ambo/plots/theme.py` |
| `src/ambo/common/` | nothing; configs are plain YAML read in `src/ambo/run.py` |
| Layer R loader (inside intake and dbt in the specs) | `src/ambo/layer_r.py` |
| Calendar seed `dbt/seeds/season_windows.csv` | `src/ambo/austrian_calendar.py` |
| Entry points (`__main__.py`, `make` targets) | `src/ambo/run.py` |
| `config/settings.yaml`, `config/scenarios/` | `src/ambo/configs/layer_p.yaml`, `layer_r.yaml`, `tiny.yaml` |
| `config/priors_synthetic.yaml` | `priors` block of `src/ambo/configs/layer_p.yaml` (and `tiny.yaml`) |
| `config/priors_real.yaml` | `priors` block of `src/ambo/configs/layer_r.yaml`; not elicited, not frozen |
| `docs/PRIOR_ELICITATION.md` | nothing |
| `data/synthetic/<scenario>/` (`media_weekly.csv`, `outcome_weekly.csv`, `truth.json`) | `data/synthetic/` (`weekly.csv`, `truth.json`, `true_contributions.csv`), see `data/README.md` |
| `data/real_anon/` | nothing; public demo data in `data/layer_r/` |
| `data/posteriors/<layer>.parquet` | `reports/layer_p/posterior_draws.csv`, `reports/layer_r/posterior_draws.csv` |
| `data/warehouse/`, `data/cache/` | nothing (both paths are only gitignored) |
| `reports/model/diag_<layer>.md` | `reports/<layer>/diagnostics.json`, `holdout_diagnostics.json` |
| `reports/recovery/RECOVERY_REPORT.md` | README.md section on Layer P and the tables under `reports/layer_p/` |
| `reports/decide/` | `reports/layer_d/` |
| `reports/NUMERIC_SSOT.md` | `reports/readme_values.json`, `reports/summary_de_values.json` |
| `reports/EXEC_SUMMARY.md` | `reports/memo_EN.md`, `docs/summary_de.md` |
| `exports/*.csv` | `reports/exports/*.csv` |
| `dashboards/` | nothing; `docs/dashboard_handoff.md` |
| `docs/ADR/` | `docs/adr/` |
| `docs/SPEC-0x` | `docs/specs/SPEC-0x` |
| `scripts/export_marts.py` | `scripts/export_dashboard.py` |
| `scripts/generate_ssot.py` | `scripts/render_readme.py`, `scripts/render_summary_de.py` |
| `scripts/leak_scan.py`, `generate_golden_metrics.py`, `check_ssot_consistency.py`, `check_layer_order.py` | nothing |
| (no spec path) | `scripts/build_notebook.py` writes and executes `notebooks/01_walkthrough.ipynb` |
| `tests/unit/`, `tests/fixtures/`, `tests/golden/` | flat `tests/` |
| `tests/test_elicitation_doc.py` | nothing |
| `Makefile`, `.pre-commit-config.yaml`, `.env.example` | nothing |
| `PROJECT_CHARTER.md`, `AGENTS.md` at the root | `docs/archive/PROJECT_CHARTER.md`, `docs/archive/agents/AGENTS.md` (archived) |

## Alternatives rejected

- Delete the unbuilt sections from the specs: loses the design record that ADR-000 and
  ADR-008 cite by requirement ID.
- Build the missing mechanisms: STATUS D-29 forbids resurrecting the warehouse stack
  during polish, and the intake waits on a client drop with written permission.
- One ADR per spec: nine records for one fact.

## Consequences

- A reader who meets a spec path first checks the tables above.
- Specs are no longer the source for file layout. The code, the README section
  "Repository structure" and this ADR are.
- ADR-008 points to "reserved GB-202 slot ADR-002" for the intake channel mapping. The
  reserved slots 001 to 006 will not be used (`docs/adr/README.md`); that decision
  takes the next free number instead.
- Building any item in section 1 later is a new ADR that supersedes the matching row
  here.
