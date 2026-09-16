# ADR-008 — Slim-build spec deviations (keep, do not revert)

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** Rafael Braga-Kribitz
- **Supersedes:** —
- **Related:** STATUS.md D-05, D-06, D-11, D-12, D-14, D-33; `docs/specs/SPEC-01_ground_truth_simulator.md`; `docs/specs/SPEC-04_mmm_model.md`; `docs/specs/SPEC-05_validation_recovery.md`

---

## Context

The 15 Sep 2026 package on `main` is a slim PyMC pipeline (Layers P, R, D) that
salvaged functions from the earlier GSD/dbt stack rather than merging that stack.
Several SPEC-tier contracts were deliberately not implemented. On 16 Sep they
were ratified as keep-and-document, not revert (STATUS D-33).

## Decision

The following shipped behaviour is the contract of the v1 public-demo package.
Reverting any item is a new ADR, not a silent fix.

1. **Five named channels, not the SPEC-01 six.** Layer P uses TV, Radio, Print,
   Paid Search, Paid Social. Layer R (Robyn public file) uses TV, Out-of-home,
   Print, Facebook, Search. The SPEC-01 taxonomy (`search_brand`,
   `search_generic`, `meta`, `display_video`, `print_regional`, `radio`, plus
   `other`) applies when real agency data is mapped at intake.
2. **Matched adstock, not SPEC-04 mismatch.** Generator and model both use a
   13-lag truncated geometric recursion with unnormalised weights so recovery
   compares half-saturation and effect size one-to-one. SPEC-04's
   normalised-weight convolution (L=8) is not used.
3. **Hill slope prior is LogNormal(0, 0.5),** not SPEC-04's truncated Gamma.
   Same weakly informative range; smoother sampler geometry; no hard boundary.
4. **Holdout is 26 weeks** (Layer P: weeks 131–156; Layer R: last 26 of 208),
   not SPEC-05's last 13. Coverage and MAPE in the README are on that window.
5. **Python 3.11** is the pinned interpreter. Nothing in the code depends on
   3.12.

The GSD warehouse (DuckDB, dbt, `fct_mmm_input`) is not part of this package.
STATUS D-29 forbids resurrecting it during polish.

## Consequences

- Recovery numbers already published are comparable across generator and model
  because adstock matches. Reintroducing the SPEC-04 mismatch would invalidate
  the current recovery charts.
- Brand-search exclusion (SPEC-06) has no line to attach to on the current five
  channels. It becomes binding at client intake if a brand-search channel exists.
- Intake of real data is a mapping exercise onto whatever channels the drop
  contains, recorded in a later ADR (reserved GB-202 slot ADR-002), not a
  silent rename back to SPEC-01 names.
