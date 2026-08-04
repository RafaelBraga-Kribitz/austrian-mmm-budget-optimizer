# Austrian MMM & Budget Optimizer (AMBO)

An Austrian mid-market marketing mix model that estimates each channel's incremental
contribution from weekly spend and revenue, and turns that posterior into a budget
recommendation — built so that the recovery of known truth on simulated data is
checkable from git history before any real data is touched.

## Roadmap

| Phase | Name | Milestone | Status |
|-------|------|-----------|--------|
| 1 | Repository Foundation | M0 | in progress |
| 2 | Ground-Truth Simulator | M1 | not started |
| 3 | Warehouse | M1→M2 | not started |
| 4 | MMM on S-A | M2 | not started |
| 5 | Recovery Suite | M3 | not started |
| 6 | Agency Intake | M4 | not started |
| 7 | Layer R Fit & Sensitivity | M5 | not started |
| 8 | Decision Layer | M6 | not started |
| 9 | Reporting & Release | M7 | not started |

## Status

This repository is under construction; the current milestone is **M0**. Phase 9
replaces this README with the release version once the numeric SSOT exists.

To verify a fresh clone: `make setup`, then `make lint` and `make test`.

For scope and acceptance criteria see `PROJECT_CHARTER.md`; for the full engineering
and modeling specifications see `docs/`.
