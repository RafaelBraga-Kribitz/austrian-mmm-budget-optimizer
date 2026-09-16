# ADR-007 — AMBO audit verdict and Layer R dataset swap

- **Status:** Accepted
- **Date:** 2026-09-15
- **Deciders:** Rafael Braga-Kribitz
- **Supersedes:** —
- **Related:** STATUS.md (morning brief and audit-fixes section), D-15, D-16, D-24, D-25; ADR-008

---

## Context

The overnight build (branch build/ambo) delivered Layers P, R, D, the rendered README,
the German summary, the notebook, tests and CI. Layer R ran on the pymc-marketing
example dataset (two unnamed, index-scaled channels), which left the breakeven ROAS
gate unable to bind and the headline chart without channel names.

## Decision

1. Merge pull request 46 to main.
2. Replace the Layer R data with Robyn's simulated weekly dataset (five named
   channels, money units) before AMBO is pinned or cited in the portfolio narrative.
3. Add a true-versus-estimated response-curve chart to Layer P and name the
   effect-times-saturation trade-off in the README.
4. Correct the interval-coverage wording (coverage against its nominal) and lead the
   attribution gap with online over-credit in absolute terms.

## Alternatives rejected

- Keep the pymc-marketing data and caveat it: the decision rule stays vacuous.
- Wait for real Austrian client data: no client yet, blocks the pin indefinitely.

## Consequences

One extra day on AMBO before the next project starts. Overnight build decisions D-01
to D-19 stand except where superseded above; D-16 (forty percent contribution margin)
remains an assumption, confirmed as the working value on 2026-09-16 (STATUS D-28).
Executed the same day in pull request 47.
