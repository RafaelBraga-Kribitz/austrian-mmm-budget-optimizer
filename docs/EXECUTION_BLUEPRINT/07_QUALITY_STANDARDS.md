# 07 — QUALITY STANDARDS & CODING STANDARDS

Part A: measurable thresholds per deliverable class. Part B: full coding standards
beyond linting. Everything here is review-enforceable; where a threshold can be
automated it names its enforcement point.

---

## Part A — Measurable quality thresholds

| Dimension | Threshold | Enforced by |
|---|---|---|
| Test coverage | ≥ 80% of `src/ambo/` lines; no module below 60% | pytest-cov in CI job 2 (EB-072) |
| Function length | ≤ ~60 lines (AGENTS W-2); hard review flag above 80 | review + ruff `PLR0915` proxy |
| Cyclomatic complexity | ≤ 10 per function | ruff `C901` (enable mccabe, max 10) |
| Module size | ≤ ~500 lines; split above | review |
| Typing | mypy `--strict` clean on `src/ambo/` | CI job 1 (EB-001) |
| Lint/format | ruff clean, line 100 | CI job 1 |
| Runtime — simulator | 3 scenarios < 30 s | T-108 validation |
| Runtime — full fit | ≤ ~35 min/fit at MD-050 on 4 cores; measure + BUILD_LOG | fit runner logs |
| Runtime — CI smoke | < 15 min wall | pytest-timeout 900 s (EB-060) |
| Runtime — `make report` | < 2 min, zero sampling | VR-703 probe |
| Memory | full fit < 8 GB RSS; thinned parquet < 5 MB each | spot-check at T-307 |
| Determinism — simulator | byte-identical (SIM-070) | gate runner |
| Determinism — optimizer/exports | byte-identical two-run (DC-703) | gate test |
| Determinism — MCMC | same machine+seed: summaries to 3 decimals (VR-701); cross-platform: bands ±0.15·SD (VR-702); NEVER draw checksums | golden tests |
| Sampler health (reported fits) | R-hat < 1.01; ESS bulk/tail > 400 (R: > 300); divergences 0 (R: ≤ 5 w/ evidence); BFMI > 0.3 | MD-071/074 gates |
| PPC | ≥ 85% weeks in 90% band | MD-072 |
| Recovery | VR §3 table per scenario (see [10 §G-SCI-3](10_VALIDATION_GATES.md)) | recovery gates |
| Scientific honesty | no point estimate without HDI (A-7); every headline number tagged (E-1) | review + SSOT tags |
| Docs completeness | README = RB §6 order; LIMITATIONS ⊇ GB §6 nine items; EXEC_SUMMARY = RB §5; elicitation = MD-060 fields, rationales ≥ 100 chars | structure tests + MD-061 lint |
| Numbers in docs | 100% of unit-bearing literals traceable to SSOT or whitelisted-with-justification | check_ssot_consistency (GB-303) |
| Visualization | 12×6 in, dpi 150, Okabe-Ito fixed channel colors, title/axes/source/tag on every chart | style module + M7 visual review |
| Pipeline determinism | `make report`/`make decide` reproducible from committed artifacts, no sampling | VR-703/DC-705 probes |
| Leak safety | leak scan green (pattern subset in CI, full local); zero real values/names/factors in repo forever | CI job 6 + pre-commit |

## Part B — Coding standards

### B1. Naming
- Modules/functions/variables: `snake_case`; classes: `PascalCase`; constants:
  `UPPER_SNAKE`. Channel identifiers appear ONLY as the canonical taxonomy strings
  (SPEC-02 §5.2) — never abbreviated, never re-cased.
- Units in names at boundaries: `_eur`, `_aeur`, `_scaled`, `_wk` where ambiguity is
  possible (interior math on scaled values may drop suffixes once the boundary is
  explicit).
- Posterior variable names are API — the Guide §2.2 table is binding.
- Test names: `test_<unit>__<behavior>` (double underscore separates subject from
  behavior).

### B2. Folder ownership
Each `src/ambo/<pkg>/` belongs to exactly one SPEC (simulate→01, intake→02,
model→04, validate→05, decide→06, report→07, common→08). A change spanning two
packages cites both REQ IDs. `scripts/` belongs to SPEC-08/09. dbt/ to SPEC-03.
No file exists without an owning SPEC.

### B3. Dependency & import rules
- Allowed import edges: exactly [03 §10](03_MODULES.md). Guard tests enforce the
  forbidden ones; everything else is review.
- Absolute imports only (`from ambo.model import transforms`); no relative imports
  beyond one dot; no wildcard imports; no imports inside functions except optional
  heavy deps guarded for CLI startup (documented case-by-case).
- New third-party dependency ⇒ ADR (EB-030), no exceptions — including "small"
  ones like statsmodels/tqdm.

### B4. Configuration pattern
- All non-secret config: `config/*.yaml` → pydantic schema → `load_settings()`.
  `extra='forbid'` everywhere. No module-level tunables, no argv-driven science
  parameters (CLI selects *what* to run, config defines *how*).
- The single env var is `AMBO_PRIVATE_DROP` (EB-041). Adding another env var is a
  spec deviation ⇒ ADR.

### B5. Logging pattern
- `get_logger(__name__)` only; INFO for phase progress, DEBUG for internals,
  WARNING for tolerated anomalies (must also surface in artifacts — a warning that
  only lands in a log is a silent failure), ERROR before raising.
- Never log: private-drop contents/paths (filter enforces), factor values,
  campaign names, absolute real €.
- Sampling targets log expected runtime up front (EB-050).

### B6. Error handling
- Typed exceptions from [03 §preamble](03_MODULES.md); constructors carry
  machine-usable fields (gate id, counts) not prose only.
- Never `except Exception: pass`; never return sentinel values for failure paths;
  fail fast at the boundary where context is richest.
- Gate failures raise `GateFailure` listing every failed gate, not just the first.
- User-facing CLI wrappers translate exceptions to exit codes + one-line messages;
  stack traces stay in logs.

### B7. Testing philosophy
- Test the *requirement*, in the same commit, named by it (W-1): every REQ ID in a
  docstring has a test that would fail if the requirement regressed.
- Prefer property/round-trip/closed-form tests over example tests for math
  (adstock, Hill, scaling, elicitation, HC1).
- Fixtures: synthetic only (EB-071/AG-032); deterministic; poisoned fixtures for
  every gate's failure direction (a gate that never failed in a test is untested).
- Markers: `smoke` (CI-only unless SMOke=1), `fit` (never CI); `--strict-markers`.
- Post-M2, every bug fix lands with a regression test in the same PR (EB-072).
- No network in any test (EB-070). No sleeps, no wall-clock dependence (freeze time
  where needed).

### B8. Documentation standards
- Every public function: docstring with one-line purpose, args/returns semantics
  (types live in signatures), raised exceptions, `Implements: <REQ-IDs>` where
  applicable.
- Module docstrings state the owning SPEC + the module's one-sentence purpose.
- Comments explain constraints/why-not-obvious ("normalized weights so β stays
  interpretable, MD-020"), never narrate the next line.
- Generated docs (RECOVERY_REPORT, SSOT, diag reports) are never hand-edited —
  regeneration is the only write path; hand-written docs (README, EXEC_SUMMARY,
  LIMITATIONS) take numbers only from SSOT.

### B9. Commit & PR standards
- Conventional commits: `feat|fix|test|docs|chore|refactor(scope): message [REQ-IDs]`.
- One milestone = one PR (A-9); within it, one task ≈ 1–3 commits, each green.
- PR body: milestone checklist from [06_CHECKLISTS.md](06_CHECKLISTS.md) ticked
  with evidence; deviations impossible without ADR link.
- No force-push, no rebase of pushed history, no amend of pushed commits (EB-082).
- Merge strategy: merge commits (not squash) — task-level commits are part of the
  layer-order evidence trail.

### B10. ADR requirements
- Triggers (GB-202): spec deviation, new dependency, gate widening, charter
  change, degradation decision, reparameterization past rung 1, anonymization
  recipe changes. Template: Context/Decision/Consequences/Spec deviations w/ REQ IDs.
- ADRs are append-only; superseding ADR references the superseded.

### B11. Refactoring policy
- Refactors ride behind green tests only; no behavior change + refactor in one
  commit. Public API changes (anything in [03_MODULES.md](03_MODULES.md)) update
  the contract doc in the same PR.
- Post-freeze (M4+), refactors must not touch `config/priors_real.yaml`,
  elicitation doc, or committed posteriors — the layer-order checker will fail the
  PR if they do (that is the mechanism working, not a bug).

### B12. Technical debt policy
- Debt is recorded, never silent: a `## Debt` line in BUILD_LOG with owner + planned
  phase. TODO comments in code are forbidden ([06 STD]) — debt lives in BUILD_LOG,
  not in source.
- Debt that would violate an invariant (privacy, determinism, layer order) is not
  debt — it is a defect and blocks merge.
