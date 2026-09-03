# ADR-008 — Adding `pyarrow` so MD-051 thinned posteriors can be parquet

- **Status:** Ratified
- **Date:** 2026-09-03
- **Deciders:** —
- **Supersedes:** —
- **Related:** EB-030, MD-051, SPEC-04 §5, SPEC-08 §3, WBS T-305

---

## Context

MD-051 requires a committed thinned posterior under `data/posteriors/<layer>.parquet`
so `make report` can regenerate numbers without resampling. pandas 2.3 in this lockfile
has no parquet engine: neither `pyarrow` nor `fastparquet` is installed, and neither
is in SPEC-08 §3. `DataFrame.to_parquet` therefore cannot implement the spec. EB-030
requires an ADR for any new third-party dependency.

## Decision

Add `pyarrow>=14,<23` to `[project] dependencies`. It is the pandas-default parquet
engine, Apache-2.0 licensed, and is used only for posterior I/O (and pandas' own
parquet path). It is not a modelling framework and is not on the O-3 forbidden list.

Schema-level parquet metadata carries `ScaleFactors` and provenance; a file without
scale-factor metadata is refused at load time (T-1).

## Consequences

`ambo.model.posterior_io` can write and read MD-051 parquet atomically. The runtime
closure grows by pyarrow and its transitive pins in `uv.lock` (resolved **pyarrow
22.0.0**). NetCDF remains gitignored (`*.nc`) as the local full-idata companion;
the writer uses ArviZ's scipy engine so this ADR does not also add netcdf4/h5netcdf.

## Spec deviations

| Document | Section | Change | REQ IDs |
|----------|---------|--------|---------|
| `docs/SPEC-08_engineering.md` | §3 | Adds `pyarrow>=14,<23` to the runtime table; the SPEC-08 §3 list is extended by this ADR rather than edited in place | REQ-dl1-reproducible-pipeline |
