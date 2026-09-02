# ADR-007 — Adding `hypothesis` as a dev dependency for property-based tests

- **Status:** Ratified
- **Date:** 2026-08-05
- **Deciders:** —
- **Supersedes:** —
- **Related:** EB-030, GB-202, SPEC-08 §3, SIM-074, WBS T-104, CONTEXT.md D-03

---

## Context

EB-030 requires an ADR for any new dependency, "including small ones." Phase 1 already
applied this rule in practice: plan 01-04 chose a `mypy` `ignore_missing_imports` override
for `yaml.*` over adding the separate `types-PyYAML` package specifically to avoid
triggering an ADR event for a type-stub-only addition (see `pyproject.toml`'s inline
comment on that override and STATE.md's 01-04 decision log entry).

Phase 2's CONTEXT.md decision D-03 adds property-based tests for `simulate/dgp.py`'s
`adstock_recursive` and `hill` functions, on top of the WBS-mandated point tests
(closed-form limit, impulse test, `Hill(K)=0.5` exact, SIM-031 spend stats). SIM-074 covers
those implementations only at fixed points; it does not exercise the bounded/monotonic
invariants D-03 asks for (adstock output bounded by `[0, x/(1-λ)]`, adstock monotonically
non-decreasing in any single spend value, Hill output in `[0, 1]` and monotonically
non-decreasing in adstocked spend for `s_c > 0`).

`hypothesis` is absent from both SPEC-08 §3's dependency table and `pyproject.toml`'s
`[dependency-groups] dev` list. The question this ADR answers: may a dev-only test
dependency be added to satisfy D-03's property-based-testing requirement, and on what
evidence, given that this project's own automated package-legitimacy checker returns a
`SUS` verdict for `hypothesis`.

## Decision

Add `hypothesis` to `[dependency-groups] dev` in `pyproject.toml` — dev group only, never
`[project] dependencies` — so it never ships in the runtime dependency closure and never
affects the O-3 forbidden-deps surface (`tests/unit/test_forbidden_deps.py` is
import-scoped to `src/ambo`, and `hypothesis` is never imported there).

Resolved version (from `uv.lock`, back-filled by Task 3 of this plan after the human
approval gate in Task 2): `hypothesis==6.167.1` (specifier `hypothesis>=6.165.1` in
`[dependency-groups] dev`; transitive `sortedcontainers==2.4.0`).

A hand-rolled randomized loop (`random.random()` calls plus manual bisection on a failing
case) was rejected as the alternative: `hypothesis`'s example-shrinking behaviour is exactly
what turns a counterexample to "adstock output ≤ x/(1−λ)" into a minimal, actionable failing
case instead of an opaque one (02-RESEARCH.md "Don't Hand-Roll").

## Consequences

Property-based invariants for `adstock_recursive` and `hill` become expressible, and their
counterexamples become minimal and actionable via Hypothesis's shrinking, rather than
requiring hand-rolled bisection.

The dev install surface grows by one package and its transitive closure. `.hypothesis/`
(Hypothesis's local per-machine example database) must be gitignored — done in Task 3 of
this plan.

The phase's 1.5-day (720-minute) Charter §5 budget absorbs this governance step plus the
property tests themselves; the 2× stop-and-ADR tripwire at 1440 minutes is tracked in
`docs/BUILD_LOG.md` at this milestone's close, per CONTEXT.md D-03's explicit
effort-budget-awareness note.

**Package-legitimacy verdict, recorded verbatim:** this project's automated checker
(`gsd-tools query package-legitimacy check --ecosystem pypi hypothesis`) returned verdict
`SUS`, with reasons `too-new`, `unknown-downloads`, `no-repository`. Counter-evidence
gathered during Phase 2 research and re-confirmed at this checkpoint: `pip index versions
hypothesis` shows an unbroken release history from `0.0.1` in 2013 through `6.165.1`,
directly contradicting "too-new"; the real source repository is
`github.com/HypothesisWorks/hypothesis`, contradicting "no-repository"; `hypothesis` is one
of the most-downloaded Python testing libraries and part of the standard scientific-Python
testing toolchain, contradicting "unknown-downloads". This verdict was resolved by the
blocking `checkpoint:human-verify` gate in Task 2 of plan 02-01 — an explicit human
approval, not by the researcher's own confidence that the SUS signals were a checker data
artifact. The protocol requires the human gate regardless of how strong the counter-evidence
looks; that gate is what makes this decision defensible rather than merely convenient.

## Spec deviations

| Document | Section | Change | REQ IDs |
|----------|---------|--------|---------|
| `docs/SPEC-08_engineering.md` | §3 | Adds `hypothesis` to the dev dependency group; the SPEC-08 §3 table is extended by this ADR rather than edited in place | REQ-dl8-quality, REQ-q1-truth-recovery |
