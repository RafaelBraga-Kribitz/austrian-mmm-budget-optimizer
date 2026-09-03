# Architecture Decision Records

## Naming convention

`docs/ADR/ADR-NNN_short-title.md`, per GB-201. Numbers are assigned in order and never
reused — a superseded ADR is marked **Superseded**, it is never deleted or renumbered.
Copy `docs/ADR/TEMPLATE.md` to start a new one; do not create `ADR-000_template.md` —
`ADR-000` is already the ratified precedence ADR (see below), and the template lives at
`TEMPLATE.md` for that reason (D-09).

## Standing rule (D-06)

**Every spec edit gets its own ADR, from here on.** An ADR is owed whenever spec text
changes or a gate moves. Filling a gap a spec left open without changing its text is an
*interpretation*, not an edit, and is recorded in `docs/BUILD_LOG.md` plus an in-script
source comment instead (D-07).

ADRs are append-only, exactly like `docs/BUILD_LOG.md`: a decision that no longer holds is
marked **Superseded** by a new ADR that references it, never edited or deleted in place.

## Existing ADRs

| ADR | Title | Status | Decisions |
|-----|-------|--------|-----------|
| [ADR-000](ADR-000_document-precedence-and-blueprint-defaults.md) | Document precedence, blueprint defaults, and the ingest cycle deviation | **Ratified** | D-1: precedence is scoped, not ranked — Charter governs goals/scope/acceptance, SPEC governs operative detail, ADR outranks both. D-2: the twenty DOC-tier BP-D-01…BP-D-20 blueprint defaults are accepted wholesale rather than re-litigated item by item. |
| [ADR-006](ADR-006_module-contracts-layout-and-citation-policy.md) | Module contracts, layout, and citation policy | **Ratified** | SPEC-08 §2's contract-first citation repoints at `docs/MODULE_CONTRACTS.md`; the canonical layout gains `.github/`, `.planning/`, `uv.lock`, `.gitattributes`; the standing no-unpublished-citation rule with its two deferred violations (Phase 4, Phase 9); commit-history conformance begins at the first `m0-bootstrap` commit. |
| [ADR-007](ADR-007_hypothesis-dev-dependency.md) | Adding `hypothesis` as a dev dependency for property-based tests | **Ratified** | `hypothesis` added to `[dependency-groups] dev` (dev-group only) for D-03's property-based tests of `adstock_recursive`/`hill`; the automated `SUS` legitimacy verdict was surfaced with counter-evidence and resolved by an explicit human approval gate. |
| [ADR-008](ADR-008_pyarrow-parquet-engine.md) | Adding `pyarrow` so MD-051 thinned posteriors can be parquet | **Ratified** | `pyarrow>=14,<23` added to runtime dependencies; pandas 2.3 has no parquet engine otherwise. |

## Reserved slots (GB-202)

Five ADR numbers are pre-planned for decisions the project already knows it will need to
make, before the work that exercises them starts. A reserved slot is filled by the ADR
with that number when the triggering decision is actually made — reservation is not
ratification.

| ADR | Topic | Trigger |
|-----|-------|---------|
| ADR-001 | Permission outcome and sector labeling (AG-001/AG-040) | The private agency data drop plus written permission lands (Phase 6, M4) and the sector label for the anonymized disclosure is fixed |
| ADR-002 | Channel-mapping decisions, including the `other` share (SPEC-02 §5.2, AG-062) | Real agency channel names are mapped onto the 7-channel taxonomy during intake |
| ADR-003 | Anonymization recipe version confirmation | Records that the anonymization factors were drawn and where they are kept — **never their values** |
| ADR-004 | Layer R window and any data reconstructions (AG §5.4) | The real-data fitting window is fixed and any reconstruction of missing/partial history is decided |
| ADR-005 | Reparameterization ladder rung, if greater than 1 (MD-073) | The sampler needs a reparameterization beyond the baseline rung to reach acceptable diagnostics |

## Standard (non-slot) triggers

Beyond the five reserved slots, any of the following also files an ADR per GB-202: a spec
deviation, a new dependency, a gate widening, a charter change, or a Charter §7 degradation
decision.
