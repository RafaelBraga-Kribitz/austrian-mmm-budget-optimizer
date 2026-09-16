# Architecture decision records

Decisions that shape the package, newest last. A decision that no longer holds is
superseded by a new record, never edited away.

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-000](ADR-000_document-precedence-and-blueprint-defaults.md) | Document precedence, blueprint defaults, and the ingest cycle deviation | Accepted (2026-08-04) |
| [ADR-007](ADR-007_audit-verdict-and-layer-r-dataset-swap.md) | AMBO audit verdict and Layer R dataset swap | Accepted (2026-09-15) |
| [ADR-008](ADR-008_slim-build-spec-deviations.md) | Slim-build spec deviations (keep, do not revert) | Accepted (2026-09-16) |

Numbers 001 to 006 are reserved for decisions the specs already name (permission
outcome, channel mapping at intake, anonymisation recipe, Layer R window, sampler
reparameterisation, module contracts); they are filled when those decisions are made.
The build-time decisions D-01 to D-33 with their reasons are in `STATUS.md`.
