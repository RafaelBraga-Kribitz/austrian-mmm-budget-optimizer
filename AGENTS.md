# AGENTS.md — Build Playbook for AI Agents (AMBO)

You are an AI coding agent (Sonnet-class or better) building the Austrian MMM & Budget
Optimizer. This file tells you HOW to work. WHAT to build is in `PROJECT_CHARTER.md`
and `docs/SPEC-01…09`. Read them in Charter §8 order first.

---

## 1. Non-negotiable rules

- A-1 **Spec supremacy.** Code vs spec: spec wins. Spec vs spec: Charter wins.
  External reality forces a deviation ⇒ ADR + preserve the output contract + cite the
  ADR in the docstring. Never silently deviate.
- A-2 **Layer order is the argument.** No Layer R (real data) fit may exist in the repo
  before the M3 recovery gates are green, and no Layer R results before
  `config/priors_real.yaml` is frozen. Both facts are enforced by git-ancestry checks
  (SPEC-09 §5) — do not attempt to "fix" ordering after the fact; if you broke the
  order, tell the human; history rewriting is forbidden.
- A-3 **No scope creep.** Charter §2.2. No Robyn, no daily grain, no extra KPIs, no
  lift tests, no apps. One line in Future work each, maximum.
- A-4 **Anonymization is absolute.** The secret rescaling factors (k_spend, k_rev), the
  client's identity, campaign names, and any pre-anonymization file must NEVER appear
  in the repo, the git history, logs, test fixtures, notebook outputs, or error
  messages. The private drop lives outside the repo (SPEC-02 §3). If you ever see a
  raw value or name in a diff: stop, tell the human, do not commit.
- A-5 **No invented data.** You never fabricate spend, revenue, or platform metrics.
  Layer P data comes only from the SPEC-01 simulator (which is disclosed by design);
  Layer R only from the anonymization pipeline. Gates fail ⇒ investigate; widen only
  via ADR.
- A-6 **Priors are marketing judgments, not tuning knobs.** After the M4 freeze you may
  not adjust any prior in response to Layer R results. Prior-sensitivity analysis
  (SPEC-05 §5) is the sanctioned way to explore prior influence — it varies priors
  transparently, it does not replace the frozen ones.
- A-7 **Uncertainty is part of every answer.** No ROAS, contribution, gain, or gap is
  ever reported as a point estimate alone. If an artifact shows a number without its
  HDI, the artifact is wrong.
- A-8 **Numbers only from SSOT** in README/exec summary (CI-checked).
- A-9 **One milestone, one PR**, gate checklist ticked item-by-item.

## 2. When to STOP and ask the human

1. Anything touching the private data drop: obtaining it, permission wording,
   anonymization parameter choices (the human draws the secret factors), ambiguous
   channel mapping, suspected PII in exports.
2. M4 freeze: the human approves `docs/PRIOR_ELICITATION.md` — the rationales are
   THEIR agency experience; you draft structure, they own content.
3. Recovery gate failures you cannot root-cause in two focused attempts (check the
   SPEC-04 §7 reparameterization ladder first).
4. Sampler pathologies persisting after the full ladder.
5. Charter §7 degradation decision (if permission fails).
6. Power BI build + screenshots (M7, human task).
7. Golden tolerance-band regeneration (SPEC-05 §7) — propose, human approves.

## 3. Build order and gates (expands Charter §5)

### M0 — Bootstrap
SPEC-08 §2 layout, pinned deps, loud-failing Make stubs, ruff/mypy/pre-commit, ci.yml
(lint+test), smoke test. **Gate:** setup/lint/test green + CI.

### M1 — Simulator
`ambo/simulate/` per SPEC-01: DGP exactly as written, three scenarios, truth files,
plausibility gates, unit tests on every DGP component (adstock recursion vs closed
form, Hill values at K, seasonality peak week). **Gate:** SPEC-01 §7.

### M2 — Model on S-A
`ambo/model/` per SPEC-04: builder returns a PyMC model from (data, priors-yaml);
fit S-A full budget; diagnostics module (R-hat/ESS/divergences/energy); posterior
parquet writer. **Gate:** SPEC-04 §7 all-green on S-A.

### M3 — Recovery suite
`ambo/validate/` per SPEC-05: recovery metrics vs truth.json for S-A/S-B/S-C,
zero-effect test, holdout, OLS baseline, pymc-marketing cross-check,
RECOVERY_REPORT.md generator. **Gate:** SPEC-05 §3–§6; report committed. Layer R work
is now unlocked.

### M4 — Agency intake (human-heavy)
You build the pipeline (`ambo/intake/`) + validation; the human runs it on the private
drop and commits ONLY the anonymized outputs. Then: draft PRIOR_ELICITATION.md +
priors_real.yaml with the human; freeze (commit + hash in SSOT). **Gate:** SPEC-02 §6;
freeze recorded; leak-scan green.

### M5 — Layer R fit
Same model code, Layer R matrix, frozen priors; diagnostics; prior-sensitivity
(flat-prior refit) + no-promo sensitivity; short-data narrative artifacts.
**Gate:** SPEC-04 §7 on Layer R (with the §7.6 relaxations); SPEC-05 §5 artifacts.

### M6 — Decision layer
`ambo/decide/`: optimizer (SAA over posterior draws, constraints, extrapolation
guards, brand-search exclusion), what-if budget grid, attribution-gap module.
**Gate:** SPEC-06 §7 incl. optimizer-recovery test on S-A truth.

### M7 — Reporting
Exports, exec charts, EXEC_SUMMARY, README (correct framing variant), LIMITATIONS,
dashboard handoff, screenshots (human). **Gate:** Charter §4 DL-1…10.

## 4. Working style

- W-1: Test in the same commit as the requirement (`Implements: SIM-031, MD-021` in
  docstrings — greppable).
- W-2: Functions < ~60 lines; model math lives in ONE module (`ambo/model/mmm.py`) —
  simulator and model share NO code (independence is what makes recovery meaningful;
  there is a test asserting no imports between `simulate/` and `model/`).
- W-3: Conventional commits + REQ IDs; append-only `docs/BUILD_LOG.md` per milestone.
- W-4: Notebooks are optional narrative only, never load-bearing; every notebook cell
  reads artifacts produced by `make` targets.

## 5. Verification protocol (before claiming any milestone)

```
make lint && make test
make recover            # M3+: recovery suite on scenarios (uses cached posteriors if fresh)
make ssot && git diff reports/NUMERIC_SSOT.md
python scripts/check_ssot_consistency.py
python scripts/check_layer_order.py       # M3+
python scripts/leak_scan.py               # M4+
```

Tick the milestone's full gate list in the PR. Unticked = not done.

## 6. Known traps (pre-loaded lessons)

- T-1: **Scaling.** Sampler health requires scaled inputs: divide spend by its
  per-channel mean, revenue by its mean, as SPEC-04 §3.1 prescribes. Un-scaled fits
  diverge and waste days. All reported quantities are back-transformed — the
  transform pair lives in one tested module.
- T-2: **Adstock convolution direction.** Effect carries FORWARD (this week's spend
  affects future weeks). An off-by-one or reversed convolution passes visual
  inspection and destroys recovery. The SPEC-01 unit test (closed-form geometric
  series) and SPEC-04's shared-shape test exist for this.
- T-3: **Simulator-model incest.** If model code imports simulator transforms (or vice
  versa), recovery becomes circular. W-2's independence test is load-bearing.
- T-4: **Seasonality eats channels.** With spend flighted on the demand calendar
  (S-B, and reality), Fourier terms and media terms compete. Expect wide HDIs, not
  point-estimate agreement; gates are calibrated accordingly. Do not "fix" by removing
  seasonality — that manufactures fake ROAS.
- T-5: **Hill parameter identifiability.** K and s trade off against β. Recovery is
  gated on ROAS and response-curve SHAPE at observed spend ranges (SPEC-05 §3.3), not
  on individual K/s point recovery — do not tighten those gates, they are wide on
  purpose.
- T-6: **MCMC reproducibility.** Seeded PyMC is deterministic on one machine+version,
  NOT across platforms. Golden tests use tolerance bands (SPEC-05 §7). Never write a
  checksum test on posterior draws.
- T-7: **Brand search flatters every model.** It correlates near-perfectly with
  revenue because it IS demand. Model it (absorbs variance) but never let the
  optimizer shift budget into it (SPEC-06 §3.6), and say why in the report — this
  single paragraph signals more marketing seniority than any chart.
- T-8: **Platform conversions ≠ truth.** In the attribution-gap module, platform
  numbers are the OBJECT of study, never a calibration target.
- T-9: **log vs level.** The model is additive in revenue level (SPEC-04 §2) — do not
  log-transform revenue "to make it nicer"; contributions must decompose additively in
  a€ for the waterfall chart to be honest.
