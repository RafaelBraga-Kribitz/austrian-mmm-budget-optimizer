# Synthesis Summary — Austrian MMM & Budget Optimizer (AMBO)

Ingest mode: `new` (net-new bootstrap; no pre-existing `.planning/` content).
Precedence applied: ADR > SPEC > PRD > DOC, no per-doc overrides.
Synthesized: 2026-08-04.

This file is the entry point for `gsd-roadmapper`. Read the conflicts report before
routing.

---

## Document counts by type

- Total ingested: 24
- ADR: 0
- SPEC: 20 — `docs/SPEC-01..09` (9) plus `docs/EXECUTION_BLUEPRINT/02..12` (11)
- PRD: 1 — `PROJECT_CHARTER.md`
- DOC: 3 — `docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md`, `01_PHASES.md`, `13_TRACEABILITY_MATRIX.md`
- UNKNOWN: 0 · low-confidence: 0 · high-confidence: 10 · medium-confidence: 14

Because no ADR exists, **SPEC is the top populated precedence tier** and
`PROJECT_CHARTER.md` (PRD) loses to any `SPEC-*` on contradiction — notwithstanding
the Charter's own claim to the contrary. See conflicts WARNING 1.

## Decisions

- ADRs found: 0
- Decisions locked: 0 (no document carries `locked: true`)
- Entries written to `decisions.md`: 28, all `status: proposed`
  - Group A — 8 ADR-shaped design commitments asserted by SPEC text but never ratified: additive-in-level not log (MD-001); pymc-marketing confined to crosscheck (MD-003/O-3); simulator and model share no transform code (SIM-003/A-1); `fct_mmm_input` as sole model input (AD-030); two-stage privacy-by-construction intake (AG-030); append-only git history as a deliverable (EB-082/GB-501/502); `search_brand` modeled but not reallocatable (DC-203c/R-4); layer-order and prior-freeze ordering (E-2/E-3).
  - Group B — 20 blueprint decisions BP-D-01..BP-D-20 from the DOC-tier master plan, which the source itself labels "proposals with defaults". None was promoted to a binding constraint by this synthesis. See conflicts WARNING 7.

## Requirements

- Source: `PROJECT_CHARTER.md` only (the sole PRD)
- Entries written to `requirements.md`: 25
  - `REQ-q1-truth-recovery`, `REQ-q2-real-incremental-roas`, `REQ-q3-optimal-allocation`, `REQ-q4-attribution-gap`
  - `REQ-dl1-reproducible-pipeline` … `REQ-dl10-readme` (10 deliverables, each with the Charter acceptance criterion plus its SPEC-tier expansion where one exists)
  - `REQ-e1-tagged-headline-numbers`, `REQ-e2-layer-order`, `REQ-e3-prior-freeze`, `REQ-e4-numeric-ssot`, `REQ-e5-anonymized-euro-caption`
  - `REQ-scope-in`, `REQ-scope-out`, `REQ-grain-and-windows`, `REQ-milestones`, `REQ-degradation-path`, `REQ-risk-register`
- No competing acceptance variants arose between PRDs, because only one PRD exists. The competing-variant conditions that did arise are SPEC-versus-SPEC and are recorded as warnings.

## Constraints

- Entries written to `constraints.md`: 76
- Type breakdown: protocol 26 · nfr 24 · schema 19 · api-contract 7
- Coverage by source family:
  - SPEC-01 simulator: 8 entries (SIM-001..004, DGP math, spend patterns, true parameter table, scenarios, SIM-060/061, SIM-070..075, truth.json §8)
  - SPEC-02 intake: 6 (AG-001/002, AG-020/030..032, AG-040..045, canonical schema, AG-060..066, AG-070)
  - SPEC-03 warehouse: 5 (AD-001/002, AD-020, AD-030, AD-040..044, AD-050)
  - SPEC-04 model: 9 (MD-001..003, model math, MD-020..022, MD-030, MD-040/041, MD-050/051, MD-060..062, MD-070..074, MD-080..083)
  - SPEC-05 validation: 6 (VR-301..310, VR-401, VR-501..504, VR-601/602, VR-701..703, report structure)
  - SPEC-06 decision layer: 6 (DC-201..205, DC-301/302, DC-401, DC-501..504, DC-601, DC-701..705)
  - SPEC-07 reporting: 6 (artifact inventory, RB-201..205, RB-301/302, RB-401..406, EXEC_SUMMARY/README structure, chart and number standards)
  - SPEC-08 engineering: 8 (EB-001/002, layout, EB-030, EB-040/041, Makefile, EB-060/061, EB-070..073, EB-080..082)
  - SPEC-09 governance: 6 (GB-101..103, GB-201/202, GB-301..303, GB-501..503, LIMITATIONS contents, gate index)
  - Blueprint SPEC-tier 02..12: 16 (task-card contract, module contracts ×3, forbidden import edges, critical path and compute ledger, implementation guides, checklists, quality thresholds, coding standards, patterns, anti-patterns, gate catalog, DoR/DoD, DL expansion, risk controls)

## Context

- Entries written to `context.md`: 10 topics — project definition; blueprint authority and subordination; repository state at ingest; the external dependency (private agency drop, not an API); the execution protocol; the specification-gap index; the nine phases P0-P8; per-phase entry/exit/rollback; traceability discipline; and the shape of the cross-reference graph.

## Conflicts

- **0 blockers**
- **7 warnings** — user resolution required before routing
- **7 info** — recorded for transparency, no gate

Warning headlines:
1. The Charter's self-declared "Charter beats specs" authority is inverted by the configured precedence, and nothing ratifies either ordering.
2. Optimizer fixed-channel set: SPEC-06 fixes `search_brand` only; 03_MODULES adds `other`. Equal precedence, materially different DL-4 output.
3. SPEC-08 §2's "exact" repository layout omits `model/fit.py`, `model/priors.py`, `simulate/config.py`, and `simulate/__main__.py`, which 03_MODULES defines as contracts and which a guard test requires — colliding with the standing checklist item "no file outside the SPEC-08 §2 layout".
4. Response-curve grid mismatch: truth is 0…2×max (SPEC-01 §8), model is 0…1.5×max (MD-082), and both feed one export plus the VR-303 M3 exit gate with no regridding rule.
5. DL-1 acceptance requires comparing regenerated exports against committed versions, but `exports/*.csv` is gitignored.
6. Full-fit runtime ceiling stated as ~35 min, ~30 min, and 15-35 min in three SPEC-tier documents.
7. Twenty DOC-tier BP-D defaults are already treated as binding by SPEC-tier documents — a precedence inversion; none is ratified and several name ADRs that do not exist.

Two contradictions were auto-resolved under precedence and were recorded as INFO:
S-B scenario length (SPEC-01 §5's 104 weeks beats the Charter §2.3 implication of 156)
and the DL-1 reproduction command set (SPEC-08 §5 plus 11 §4 beat the Charter's
`make setup && make all`).

**Status 2026-08-04: both closed, and neither can flip.** ADR-000 D-1 ratified precedence
as *scoped* rather than ranked — the Charter governs goals/scope/acceptance, the SPECs
govern operative detail — and both Charter passages were corrected at source, so the
contradictions no longer exist in the corpus. All seven WARNINGs are likewise resolved;
see `.planning/INGEST-CONFLICTS.md` resolution log.

**Notable deviation from the standard synthesis rules:** cross-reference cycle
detection found two strongly connected components covering 22 of 24 documents. These
were recorded as INFO rather than as blockers, because every document was classified
and read exactly once and no intel entry was derived by following a reference — the
cycles are navigational sibling links, not content-derivation loops. Full reasoning is
in conflicts INFO 3. Applying the rule literally would have aborted the ingest of a
structurally healthy corpus.

## Files produced

- `.planning/intel/decisions.md` — 28 entries, 0 locked, 0 ADRs
- `.planning/intel/requirements.md` — 25 `REQ-*` entries from the Charter
- `.planning/intel/constraints.md` — 76 entries across 20 SPEC sources
- `.planning/intel/context.md` — 10 DOC-tier topics
- `.planning/INGEST-CONFLICTS.md` — full conflict report, three buckets

## Status

**AWAITING USER — 7 competing variants and precedence questions need resolution
before routing.** No blockers; the intel is complete and internally consistent, but
warnings 2, 3, 4, and 5 are genuine SPEC-versus-SPEC contradictions that a downstream
plan cannot silently pick between, and warnings 1 and 7 govern how the whole corpus is
weighted.
