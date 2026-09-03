---
phase: 04-mmm-on-s-a
plan: 03
subsystem: md070
tags: [adstock, recovery, t-2]

duration: 15min
completed: 2026-09-03
status: complete
---

# Phase 4 Plan 3: MD-070 Shared-Shape Sanity Summary

**T-302 is green. Model vs simulator adstock outputs correlate > 0.95 on all six S-A channels at truth λ. Equality is not expected and is not asserted.**

## Task Commits

1. **Task 1: MD-070 test** — (this commit)

## Accomplishments

- `tests/unit/test_transform_sanity.py` reads P-SA through `ambo.common.db`, truth λ from committed `truth.json`, evaluates model adstock via pytensor at `Settings.adstock_length`.
- Docstring names MD-070 and the MD-020 parameterization mismatch.
- Import-independence guard still green.

## Deviations from Plan

None.

## Next Phase Readiness

04-04 (`build_model` + smoke) is unblocked on priors + transforms + this cheap T-2 catch.

---
*Phase: 04-mmm-on-s-a*
*Completed: 2026-09-03*

## Self-Check: PASSED
