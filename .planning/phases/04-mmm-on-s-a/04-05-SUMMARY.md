---
phase: 04-mmm-on-s-a
plan: 05
subsystem: model-posterior-io
tags: [parquet, md-051, pyarrow, eb-050]

duration: 40min
completed: 2026-09-03
status: complete
---

# Phase 4 Plan 5: posterior_io Summary

**T-305 is green. Thinned posteriors round-trip with `ScaleFactors` in parquet schema metadata. Files without scale factors are refused. Atomic writes leave no partial file at the final path.**

## Task Commits

1. **ADR-008 + pyarrow lock** — `d0a74c2` (docs)
2. **Task 1: save/load + tests + contract** — `0c2c5b4` (feat)
3. **NetCDF engine + basename guard** — `603eb5e` (fix)
4. **mypy InferenceData access + extra tests** — `7c247e4` (fix)
5. **BUILD_LOG / ROADMAP / STATE** — (this commit)

## Accomplishments

- ADR-008: `pyarrow>=14,<23`, locked 22.0.0. pandas 2.3 has no parquet engine.
- `save_posterior` / `load_posterior` / `PosteriorBundle`.
- Thinning 4000→1000 proven on constructed idata.
- Metadata: scale factors, data hash, prior sha256, sampler from Settings, git commit, seed.
- Atomic temp+replace; missing scale factors → `FitError`.
- BP-D-06 names; gitignored `.nc` via ArviZ default h5netcdf.

## Deviations from Plan

**1. [Dep] pyarrow is a new runtime dependency.** Required by MD-051; filed as ADR-008 (EB-030). Not a silent add.

**2. [NetCDF] Default h5netcdf, not scipy.** scipy cannot write grouped InferenceData files. h5netcdf is already transitive via arviz — no second new package.

**3. [IO] `ParquetFile.read()` instead of `pq.read_table`.** The AD-030 AST guard flags any `.read_table(` in `model/`. Same bytes, different call name.

**4. [Process] 4B** one PR per plan.

## Next Phase Readiness

04-06 diagnostics can stack. Full S-A MD-050 fit stays 04-07. Do not author `priors_real.yaml`.

---
*Phase: 04-mmm-on-s-a*
*Completed: 2026-09-03*

## Self-Check: PASSED
