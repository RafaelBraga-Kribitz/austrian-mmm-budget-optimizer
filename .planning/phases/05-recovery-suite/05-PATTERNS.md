# Phase 5: Recovery Suite - Pattern Map

**Mapped:** 2026-09-03
**Files analyzed:** validate package (empty except `__init__.py`), posterior_io,
transforms, fit, truth.py, governance scripts, Phase 4 analogs
**Analogs found:** 12 direct/role-match; remainder first recovery-science files

## File Classification

| New/Modified File | Role | Closest Analog | Match Quality |
|---|---|---|---|
| `src/ambo/validate/recovery.py` | metrics (pure + I/O) | `ambo.simulate.__main__` gate runner | role-match |
| `config/recovery_gates.yaml` | DATA thresholds | `config/priors_synthetic.yaml` (values as data) | role-match |
| `src/ambo/common/errors.py` (`ValidationError`) | utility | `FitError` / `DataContractError` | exact |
| `tests/unit/test_recovery.py` | test | `tests/unit/test_diagnostics.py` (constructed idata) | role-match |
| `src/ambo/model/fit.py` (T-402 Makefile; T-403 variant) | CLI | itself | exact |
| `Makefile` `fit-synthetic` / `recover` / `ssot` | config | Phase 3 `export` becoming real | exact |
| `src/ambo/validate/holdout.py` | orchestration | `fit.run_fit` | role-match |
| `src/ambo/validate/baseline_ols.py` | closed-form math | `elicit.py` (scipy, no new dep) | role-match |
| `src/ambo/validate/crosscheck.py` | confined import | MD-003 guard already in `test_import_independence.py` | exact (guard) |
| `src/ambo/validate/report.py` | generated markdown | `diagnostics.write_diag_report` | role-match |
| `scripts/generate_ssot.py` | collect-don't-compute | `scripts/export_marts.py` registry | exact idiom |
| `scripts/generate_golden_metrics.py` | generator | season-windows generator (idempotent, sorted) | role-match |
| `scripts/check_layer_order.py` | extend | itself (D-17 Phase 1) | exact — do not replace |
| `scripts/check_ssot_consistency.py` | extend | itself | exact — do not replace |
| `docs/MODULE_CONTRACTS.md` | contract | every prior module PR (D-23) | exact |

## Pattern Assignments

### `recovery.py` (metrics)

**Analog:** diagnostics constructed-idata tests; simulate validate-sim gate table.

**Do copy:** frozen pydantic result types; JSON side-files with atomic replace;
thresholds loaded from YAML; `Implements:` REQ line; functions < ~60 lines.

**Do not copy:** simulator adstock/Hill; restated SPEC-05 numbers in Python; DuckDB
handles (use `read_mmm_input` or injected frames).

Compile model transforms **once** (`pytensor.function` of `adstock_convolve` +
`hill_saturation`) and reuse across draws. Do not set `pytensor.config.cxx = ""` in
this module (that pin lives in transform *unit* tests only).

### `generate_ssot.py` (registry)

**Analog:** `scripts/export_marts.py` D-03 registry.

A tuple of `(key, path, extractor)` or a glob of `reports/recovery/*.json` producers.
Deterministic key order. `updated_at` from artifact mtime (UTC ISO). Never opens a
posterior to compute a ROAS.

### Holdout CSV

**Analog:** `diag_P-SA.md` — committed text next to gitignored `.nc`.

Schema tested; coverage column mandatory (A-7).

### Cross-check confinement

**Analog:** `test_pymc_marketing_imported_only_in_validate_crosscheck` already allows
exactly `src/ambo/validate/crosscheck.py`. Creating that file turns the guard from
vacuous to load-bearing — same pattern as `pm.sample` in 04-04.
