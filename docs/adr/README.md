# Architecture decision records

Decisions that shape the package, newest last. A decision that no longer holds is
superseded by a new record, never edited away.

These five records are the live governance of the repository.

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-000](ADR-000_document-precedence-and-blueprint-defaults.md) | Document precedence, blueprint defaults, and the ingest cycle deviation | Accepted (2026-08-04) |
| [ADR-007](ADR-007_audit-verdict-and-layer-r-dataset-swap.md) | AMBO audit verdict and Layer R dataset swap | Accepted (2026-09-15) |
| [ADR-008](ADR-008_slim-build-spec-deviations.md) | Slim-build spec deviations (keep, do not revert) | Accepted (2026-09-16) |
| [ADR-009](ADR-009_spec-sections-not-built.md) | Spec sections not built and not planned | Accepted (2026-09-30); dashboard row superseded by ADR-010 |
| [ADR-010](ADR-010_dashboard-pbip-and-html-twin.md) | Power BI as a PBIP text project, plus a static HTML twin | Accepted (2026-10-27) |

Numbers 001 to 006 were never used and will not be filled. They were reserved by the
planning stack (SPEC-09 GB-202) for decisions on permission, channel mapping at intake,
anonymisation, the Layer R window, sampler reparameterisation and module contracts.
That stack was stopped (STATUS D-29, D-31) and its files are archived under
`docs/archive/`. A future decision on one of those topics takes the next free number,
starting at ADR-011 (ADR-010 is taken by the dashboard).

The build-time decisions D-01 to D-33 with their reasons are in `STATUS.md`.
