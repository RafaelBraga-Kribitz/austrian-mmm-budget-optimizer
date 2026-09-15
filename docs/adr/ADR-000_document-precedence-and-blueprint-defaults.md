# ADR-000 — Document precedence, blueprint defaults, and the ingest cycle deviation

- **Status:** Accepted
- **Date:** 2026-08-04
- **Deciders:** Rafael Braga-Kribitz
- **Supersedes:** —
- **Related:** `PROJECT_CHARTER.md` §7 (authority), `docs/SPEC-09_governance_quality.md`
  GB-201/GB-202, the execution blueprint's master plan §5 (BP-D block — internal, not
  published), `.planning/INGEST-CONFLICTS.md` (WARNING 1, WARNING 7, INFO 3)

---

## Context

The repository carries 24 planning documents (1 charter, 20 SPEC-tier, 3 DOC-tier) and,
until this ADR, zero ratified decisions. Three governance questions were left open by that
state, and all three block clean execution rather than any single milestone:

1. **Precedence is unratified and self-contradictory.** `PROJECT_CHARTER.md` declared
   "Charter beats specs; specs beat code". The document-ingest pipeline was configured with
   the opposite ordering for operative detail (ADR > SPEC > PRD > DOC), and resolved two
   real contradictions on that basis. Nothing ratified either ordering.
2. **Twenty DOC-tier defaults are already load-bearing.** `00_MASTER_PLAN.md` §5 labels the
   BP-D-01…BP-D-20 items "proposals with defaults", yet SPEC-tier documents hard-code
   several of them as binding module contracts. A consumer reading the SPEC tier would treat
   them as authoritative when their basis is explicitly override-able.
3. **The ingest declined a default blocker rule** and needs that on the record.

## Decision

### D-1 — Precedence is scoped, not ranked

The Charter and the SPECs govern **different questions**, and the apparent inversion
dissolves once that is stated explicitly:

| Question | Authority |
|----------|-----------|
| What is in scope, what is out, what counts as done, which risks are accepted | **`PROJECT_CHARTER.md`** — and a SPEC may not silently widen or narrow it |
| Operative detail: numeric thresholds, grids, schemas, file layout, command sequences | **The relevant SPEC** — the Charter's restatements are summaries, not the source |
| Anything ratified here or in a later ADR | **The ADR** — top of the order |

The configured ingest ordering (ADR > SPEC > PRD > DOC) is **ratified as-is** for operative
detail. Where the Charter paraphrases a SPEC value and the two differ, the SPEC governs and
the Charter is corrected to match — not the reverse. Where a SPEC contradicts the Charter on
*scope or acceptance*, that is a Charter-level change and requires an ADR.

Consequently the two auto-resolutions stand, and both source documents have been corrected
so the contradictions no longer exist:

- Scenario S-B is **104 weeks** (SPEC-01 §5), corroborated by SPEC-05 VR-503, 03_MODULES
  §2.1 and 01_PHASES. The Charter §2.3 parenthetical was imprecise drafting and is fixed.
- DL-1's reproduction probe is the explicit target sequence in 11_ACCEPTANCE_CRITERIA §4,
  not `make all` — which by SPEC-08 §5's own definition contains no `simulate` or fit target
  and therefore cannot reproduce `data/synthetic/`. The Charter DL-1 row is fixed.

### D-2 — The BP-D block is ratified wholesale

BP-D-01 through BP-D-20 in `00_MASTER_PLAN.md` §5 are **accepted as binding defaults**,
effective immediately, without item-by-item re-litigation at task time. The DoR item in
11_ACCEPTANCE_CRITERIA §2.4 ("accept or override the applicable BP-D") is satisfied for all
twenty by this ADR; it continues to apply to any BP-D item added later.

Ratifying the block in one act rather than twenty is deliberate: the defaults were authored
as a coherent set, several are mutually dependent (BP-D-02/03 share the staging-column
scheme; BP-D-05/10 share the seed-generation path), and twenty separate ratification events
would cost more effort than the decisions themselves are worth on a solo project with a
13.5-day build budget.

The four items that name a future ADR keep their pre-planned GB-202 slots, but for a
narrower purpose — recording **what was actually observed**, not re-deciding the default:

| Item | Default ratified here | Slot retained for |
|------|----------------------|-------------------|
| BP-D-04 | `other` is modeled if ≥1% spend, and excluded from reallocation | ADR-002 at intake: whether `other` appeared, and at what share |
| BP-D-02 | CPM-based impressions; `platform_conversions` from revenue ÷ AOV | Recorded in `truth.json`; no further ADR needed unless the rule changes |
| BP-D-03 | Unit-neutral staging names; unit in `dim_layer.monetary_unit` | ADR slot released |
| BP-D-11 | (per 00 §5) | ADR at the point it is exercised |

### D-3 — Cross-reference cycles are not ingest blockers

The ingest found two strongly connected components in the `cross_refs` graph covering 22 of
24 documents and declined to treat them as blockers. **That call is ratified.**

The default rule guards against *transitive content resolution* — where document A's meaning
is only definable through document B and vice versa, so synthesis loops. That precondition
does not hold here: all 24 documents were classified up front, each was read exactly once,
each carries self-contained content, and no entry in `.planning/intel/` was derived by
following a reference. The cycles are navigational "see also" links between siblings in a
single batch. Applying the rule literally would have blocked 22 of 24 documents in a
structurally healthy corpus.

## Consequences

**Positive.** Precedence is answerable in one sentence per question type. The twenty defaults
become citable constraints instead of proposals that every downstream reader must re-check.
Four INGEST-CONFLICTS items (WARNING 1, WARNING 7, INFO 1, INFO 2) are closed rather than
carried into execution.

**Negative.** Wholesale ratification means a BP-D item could turn out wrong under real data
and will then need a superseding ADR rather than a quiet override at task time. This is
accepted: the failure is visible and cheap to correct, whereas twenty ratification events are
expensive and certain.

**Neutral.** `docs/ADR/` now exists ahead of T-012, which had scheduled its creation. T-012
reduces to adding the ADR index and the GB-201 lint.
