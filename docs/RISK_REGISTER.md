# RISK REGISTER

`PROJECT_CHARTER.md` §6 risks `R-1`..`R-9` remain authoritative and are copied here **verbatim**
rather than restated — this document expands them with a Fallback and Detection cell, it does
not re-decide them. IDs `R-1`..`R-9` are reserved for the Charter's own risks; every finding
discovered during the build takes an ID at `R-10` or above, so an appended finding can never
shadow a Charter risk.

This register is reviewed at every phase entry (per `docs/EXECUTION_BLUEPRINT/01_PHASES.md`
Phase-independent standing rule 1). A review appends exactly one dated line to the
[Review log](#review-log) below — it never restates, renumbers, or duplicates an existing risk
row.

A risk closes on evidence: a dated `docs/BUILD_LOG.md` reference or an ADR. Its row is then
struck through with that closing reference, never deleted (REQ-risk-register: a risk is never
removed, downgraded, softened, or reworded to make a gate read better).

No cell in the Mitigation, Fallback, or Detection columns may be blank. An unknown fallback is
written as `none identified` plus an owning phase, never left empty.

This document has no concurrent-writer contract and needs none: it is a single-author markdown
file in a single-developer offline repository. The only interruption case is a half-written
edit, and git's working-tree-versus-commit boundary already makes the published state atomic.

`docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md` is frozen alongside `03_MODULES.md` as of Phase 1
(D-08); its per-milestone mitigation/fallback/detection triads are the promotion source for the
rows below.

---

## Register

| ID | Risk | Likelihood | Impact | Mitigation | Fallback | Detection | Owner phase | Status |
|----|------|-----------|--------|------------|----------|-----------|--------------|--------|
| R-1 | Client permission falls through | Medium | Layer R dies | Charter §7 degradation path: project ships as Layers P+D on synthetic with full recovery story; README framing pre-written for both cases (SPEC-07 §6.1) | T-507 (permission chase) started immediately at Phase 6 entry; drop-independent backlog (intake codebase, decision layer against Layer P, reporting infrastructure) fills the wait window so no phase stalls on the answer | Calendar checkpoint at Phase 6 entry: if permission is not confirmed, the Charter §7 degradation ADR is written then, not later (AG-002 forbids gray-zone processing while waiting) | 6 | Open |
| R-2 | Adstock/saturation weakly identified on 52–104 real weeks | High | Wide posteriors | That IS the finding: informative-priors-vs-flat comparison (SPEC-05 §5) becomes the centerpiece; never hidden | None needed — wide HDIs are reported as content, not treated as a defect; narrative emphasis shifts to the prior-influence forest plot (VR-501), already specced | HDI widths in the Layer R diagnostic report (`reports/model/diag_R.md`) | 7 | Open |
| R-3 | Collinearity: spend planned on the demand calendar | Certain | Confounded estimates | S-B scenario tests exactly this; seasonality controls; honesty in `LIMITATIONS.md` | VR-310 debug order on a near-miss gate (transforms → scaling round-trip → data joins → sampler health); any gate widening requires an ADR naming the suspected structural cause, never a silent loosening | The recovery-suite gate runner (VR-301..306) | 5 | Open |
| R-4 | Brand-search endogeneity (brand search is partly an outcome of other media) | High | Over-credited brand search | `search_brand` is modeled but EXCLUDED from optimizer reallocation advice (SPEC-06 §2, DC-203(c)); the same exclusion applies to `other` when present (ADR-000 D-2 / BP-D-04); trap documented | If the DC-704 audit test ever shows a leak path around the fixed-set constraint, the constraint construction is re-audited by hand and, on a confirmed gap, DC-704 is widened only via an ADR before any release — the exclusion itself is never silently loosened | The DC-704 constraint-audit test (`ambo/decide/optimizer.py`'s fixed-channel-set check) | 8 | Open |
| R-5 | MCMC non-reproducibility across platforms | Certain | Golden tests break | Tolerance-band doctrine (SPEC-05 §7), committed thinned posteriors for report regeneration | Band regeneration with PR justification (EB-073) — tolerance bands (±0.15·SD, VR-702) are widened only with a documented reason attached to the regenerating PR, never silently | The golden comparison test in CI (job 2, against `tests/golden/`) | 5 | Open |
| R-6 | Anonymization leak (secret factors, client identity, absolute €) | Low | Serious | SPEC-02 §4 secrets protocol + CI leak-scan (SPEC-09 §5); factors never touch the repo or git history | STOP + human-led remediation including credential/data rotation; the leak is documented (EB-082 — agents never rewrite history themselves, AGENTS A-4) | `scripts/leak_scan.py` (CI pattern subset + full local mode) and the Phase 6 M4 file-by-file human review checklist | 6 | Open |
| R-7 | Divergences / sampler pathologies | Medium | Blocked fits | SPEC-04 §7 reparameterization ladder, prescribed in order; scaling (T-1) enforced by design; prior-predictive sanity checked pre-MCMC | MD-073 ladder followed in order, one rung per attempt; leaving rung 1 requires ADR-005; two failed root-cause attempts on the ladder escalate to the human | MD-071 diagnostic gate (R-hat, ESS, divergences, BFMI) | 4 | Open |
| R-8 | Scope creep (more frameworks, daily grain, lift tests) | High | Never ships | §2.2 + AGENTS A-3 | Any proposed scope addition is routed through an ADR before any code lands; if code already landed outside the wall, it is reverted or gated behind a documented post-v1.0 backlog item — never quietly merged | The forbidden-deps guard test (`tests/unit/test_forbidden_deps.py`) plus standing PR review against Charter §2.2 | standing | Open |
| R-9 | Promo calendar reconstruction is imperfect memory | Certain | Omitted-variable bias | Tagged CALIBRATED; sensitivity fit without promo regressor (SPEC-05 §5.4) | If the no-promo sensitivity fit (VR-504) shows a material shift versus the promo-included fit, the promo-attributed contribution is flagged as omitted-variable-biased in `LIMITATIONS.md` and the Layer R report, rather than silently trusted at face value | The VR-504 no-promo sensitivity artifact — a reviewer running `make sensitivity` sees the delta table directly | 7 | Open |
| R-10 | No C compiler on the development machine | Low | Medium | `g++` is absent on the Windows dev machine, so PyTensor falls back to its NumPy backend. Install MSVC Build Tools or an m2w64 toolchain — decided in Phase 4 | Accept the NumPy backend for all fits and re-budget the compute ledger accordingly (NumPy backend is slower but already the documented, working fallback per `01-RESEARCH.md`) | A compiler check added to `make setup` | 4 | Open |
| R-11 | Leak-scan pattern set is deliberately narrow at M0 | Low | Medium | D-26 scopes the M0 subset to three high-precision, path-scoped checks (private-drop path anywhere; email/URL/person-name shapes only under `data/real_anon/` and `reports/ingestion/`; bare currency literals only in notebooks) so the gate is still trusted in Phase 6 | Full mode plus the private-drop blocklist covers the specific values a narrow pattern set would miss, until the pattern set is widened | The Phase 6 intake tasks T-501..T-506 revisit the pattern set explicitly before real data lands | 6 | Open |
| R-12 | The `pymc<6` upper bound is load-bearing | Low | High | The SPEC-08 §3 `pymc>=5.15,<6` bound already guards against the PyMC 6.0 / PyTensor 3.0 / ArviZ 1.0 breaking releases discussed upstream; `uv.lock` resolved 5.28.5, safely under the ceiling | Pin to the last known-good resolved version if a transitive update ever forces the ceiling; widening the bound without an ADR is never done — EB-030 requires an ADR for any bound change | `uv lock` diff review in any pull request touching `pyproject.toml` | standing | Open |
| ~~R-13~~ | ~~The Chocolatey `make` package provenance is unconfirmed~~ | ~~Low~~ | ~~Low~~ | ~~`01-RESEARCH.md` could not fetch the Chocolatey package page directly (HTTP 403); the dev machine's GNU Make is confirmed ezwinports-lineage 4.4.1~~ | ~~Pin the Chocolatey package version once its provenance is confirmed, or install the ezwinports build directly on the CI runner instead of relying on Chocolatey's community package~~ | ~~The Windows leg of the CI `test` job prints `make --version`, giving a first real comparison point against the development machine's 4.4.1~~ | 1 | Closed — `docs/BUILD_LOG.md` M0 close entry, CI run `30951615385`: Windows leg printed `GNU Make 4.4.1 / Built for x86_64-w64-mingw32`, matching the development machine's verified 4.4.1 exactly |
| R-14 | `exports/mmm_input_weekly.csv` is committed, and once Phase 6 flips `layer_r_present`, that same committed file will carry Layer R a€ rows into a repository that goes public at M3 | Low (a scheduled Phase 6 flip, not a surprise) | Medium (a€ figures reaching the public repo unscanned) | Phase 1's D-26 scoped `exports/` a€ figures *out* of the leak scan — correctly, at a time when nothing was committed there (the scan cannot be tuned against data that does not exist, and a gate that cries wolf now against synthetic Layer P rows is one that gets ignored once real rows land). The mitigation is a scheduled revisit, not a widened scan today: Phase 6 must re-scope `scripts/leak_scan.py`'s pattern set for `exports/*.csv` before the `layer_r_present` flip lands any Layer R row in a committed export | If Phase 6 flips the flag without first revisiting the scope, treat it as a leak-scan-scope gap discovered late: STOP, widen the scan under an ADR, and re-run `scripts/leak_scan.py` against full history before any further Layer R commit | `scripts/export_marts.py`'s module header comment (in-code pointer, plan 03-08/03-09) plus this register row — two independent homes neither dependent on memory; Phase 6's own task list must tick the revisit explicitly | 6 | Open |

---

## Review log

- **2026-08-04 — Phase 1 entry review.** Register seeded from `PROJECT_CHARTER.md` §6 (R-1..R-9,
  copied verbatim) and `docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md`'s per-milestone triad
  expansion, plus four build findings discovered during Phase 1 planning and research (R-10..R-13).
  13 risks recorded; 13 open, 0 closed.
- **2026-08-04 — Plan 01-09 Task 3 checkpoint.** R-13 closed on evidence: CI run
  `30951615385` (see `docs/BUILD_LOG.md` M0 close entry) shows the Windows `test`
  leg's `make --version` output as `GNU Make 4.4.1 / Built for x86_64-w64-mingw32`,
  matching the development machine's independently-verified 4.4.1 build exactly.
  13 risks recorded; 12 open, 1 closed.
- **2026-08-06 — Plan 03-09 Task 2.** R-14 added: `exports/mmm_input_weekly.csv`
  (committed since plan 03-08, D-01) will carry Layer R a€ rows once Phase 6 flips
  `layer_r_present`, into a repository already public at M3, while Phase 1's D-26
  correctly scoped the leak scan's `exports/` a€ coverage out at a time when nothing
  was committed there. Tracked here plus `scripts/export_marts.py`'s header comment
  (D-05) so the Phase 6 revisit does not depend on memory. 14 risks recorded; 13
  open, 1 closed.
