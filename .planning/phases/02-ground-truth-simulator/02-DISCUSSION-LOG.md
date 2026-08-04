# Phase 2: Ground-Truth Simulator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-05
**Phase:** 2-Ground-Truth Simulator
**Areas discussed:** Promo/burst week authoring, Test rigor beyond WBS minimum, AlpenTrek narrative flavor

---

## Promo/burst week authoring

**Question 1:** How much involvement do you want in choosing the exact ISO promo/burst weeks?

| Option | Description | Selected |
|--------|-------------|----------|
| Delegate fully | I pick weeks satisfying SIM-030/031 stats + Guide §1.1 rules; you're only pulled in if a gate fails | ✓ |
| Draft then approve | I propose the full week tables for S-A/S-B/S-C, you review before I freeze them into YAML | |
| You specify weeks | You give exact ISO weeks/dates | |

**User's choice:** Delegate fully

**Question 2:** For unanchored burst placements and the 5 spread promo weeks, how should placement be decided?

| Option | Description | Selected |
|--------|-------------|----------|
| Reasoned by hand, once | Matches WBS/Guide wording; I pick sensible spread-out weeks directly in YAML, no extra script | |
| Small one-off placement script | Throwaway script deterministically proposes non-overlapping placements from the seed, then copied into YAML as frozen constants | ✓ |

**User's choice:** Small one-off placement script
**Notes:** The script itself is not a deliverable — no WBS task, no module contract entry. Its output gets frozen into YAML; the script is discardable.

---

## Test rigor beyond WBS minimum

**Question:** Beyond the WBS-prescribed point tests, do you want additional property-based coverage (e.g. hypothesis) on adstock/Hill?

| Option | Description | Selected |
|--------|-------------|----------|
| WBS minimum only | The prescribed test set is exactly what SIM-074/SIM-071 gate on; little budget slack, extra tests don't move a gate | |
| Add property-based tests | hypothesis-based tests for adstock/Hill (monotonicity, bounds) for extra confidence, accepting some effort-budget risk | ✓ |
| Decide after point tests run | Ship WBS-mandated set first; add property tests only if a point test reveals a real edge case | |

**User's choice:** Add property-based tests
**Notes:** User explicitly accepted the added effort-budget risk against the 1.5-day (2× ⇒ stop+ADR) budget. Suggested properties (bounded adstock, monotonicity, Hill in [0,1]) are Claude's discretion to finalize.

---

## AlpenTrek narrative flavor

**Question:** Should Phase 2 artifacts carry narrative texture about "AlpenTrek GmbH", or stay purely mechanical?

| Option | Description | Selected |
|--------|-------------|----------|
| Purely mechanical now | Brand voice/story belongs to Phase 9 (README, dashboard, exec summary) | ✓ |
| Short blurb now | 2-3 sentence AlpenTrek description in truth.json metadata or a module docstring | |

**User's choice:** Purely mechanical now
**Notes:** Explicitly deferred to Phase 9, not left open — see Deferred Ideas.

---

## Claude's Discretion

- Exact ISO week numbers for all promo/burst schedules (within D-01/D-02 constraints).
- Internal structure/implementation of the one-off placement script.
- Which specific `hypothesis` properties to encode for the added adstock/Hill tests, beyond
  the three suggested in CONTEXT.md (bounded adstock, monotonicity, Hill range).

## Deferred Ideas

- AlpenTrek brand-voice/narrative texture — belongs to Phase 9 (Reporting & Release), not this
  phase. Not a scope-creep redirect (nothing was proposed outside the roadmap); this was a
  direct question about this phase's own artifact style, answered by scoping it out to where
  it belongs.
