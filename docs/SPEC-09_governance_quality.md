# SPEC-09 — Governance & Quality (AMBO, deliberately lightweight)

Requirement IDs: `GB-xxx`. Same cap as the sibling projects: the mechanisms below are
ALL the governance there is. This repo's signature mechanisms are the **layer-order
proof** and the **prior freeze** (§5) plus the **leak scan** (SPEC-02 AG-045).

---

## 1. Epistemic tags

- GB-101: GROUND-TRUTH / REAL-ANON / MODELED / CALIBRATED per Charter §3.
- GB-102: The a€ caption (Charter E-5) and the DC-302 counterfactual caption live in
  `ambo/report/captions.py` only; a grep-test enforces single-occurrence in `src/`.
- GB-103: SSOT rows carry a `tag` column; README/exec numbers carry tags inline.

## 2. ADRs

- GB-201: `docs/ADR/ADR-NNN_short-title.md`, append-only, template identical to the
  sibling repos (Context / Decision / Consequences / Spec deviations with REQ IDs).
- GB-202: Pre-planned ADR slots: ADR-001 permission outcome + sector labeling
  (AG-001/AG-040); ADR-002 channel-mapping decisions incl. `other` share (SPEC-02 §5.2, AG-062);
  ADR-003 anonymization recipe version confirmation (factors NOT included — the ADR
  records that they were drawn and where they are kept, never their values);
  ADR-004 Layer R window + any data reconstructions (AG §5.4); ADR-005
  reparameterization ladder rung if > 1 (MD-073). Plus the standard triggers:
  spec deviation, new dependency, gate widening, charter change, Charter §7
  degradation decision.

## 3. SSOT mechanism

- GB-301: `reports/NUMERIC_SSOT.md` generated only by `scripts/generate_ssot.py`;
  columns `key | value | unit | tag | produced_by | updated_at`.
- GB-302: Minimum keys: recovery gate results per scenario (`recovery_pass_sa/sb/sc`
  booleans + `roas_coverage_<scenario>`), `zero_channel_verdict`,
  `roas_<channel>_median` + `roas_<channel>_hdi90` (Layer R),
  `expected_gain_pct` + HDI bounds, `expected_gain_aeur_annual`,
  `next_euro_best_channel`, `next_euro_marginal_roas`,
  `overcredit_ratio_<channel>` (Layer R), `optimizer_regret_sb`,
  `holdout_mape_real`, `prior_freeze_commit`, `layer_r_weeks`,
  `media_share_of_revenue_real`, `divergences_real_fit`.
- GB-303: `scripts/check_ssot_consistency.py` (CI): README, EXEC_SUMMARY, and
  RECOVERY_REPORT numeric literals with SSOT-adjacent units (a€, %, ×, weeks) must
  match SSOT within documented rounding; whitelist file with per-entry justification
  comments.

## 4. CI gates summary

lint → tests+coverage (incl. smoke-fit) → dbt build → SSOT consistency → layer-order
check → leak scan. PRs touching results regenerate SSOT in the same PR (freshness
check as siblings).

## 5. Layer-order & prior-freeze enforcement (this repo's signature)

`scripts/check_layer_order.py` asserts in CI, via git history (which is append-only,
EB-082):

- GB-501: The commit adding `reports/recovery/RECOVERY_REPORT.md` with all M3 gates
  green is an ancestor of any commit adding files matching
  `data/posteriors/R*.parquet` or `reports/model/diag_R.md` (model proven on truth
  BEFORE real data was fit).
- GB-502: The commit freezing `config/priors_real.yaml` + `docs/PRIOR_ELICITATION.md`
  (hash recorded in SSOT `prior_freeze_commit`) is an ancestor of any Layer R fit
  artifact commit, and neither file is modified after the freeze commit (git log
  check). Legitimate impossibility (e.g., a channel absent from real data) ⇒ APPENDED
  amendment section in the elicitation doc created BEFORE the fit + ADR — the frozen
  ranges themselves never change.
- GB-503: The README's three-layer explainer (RB §6.5) links this script so reviewers
  can verify the mechanism, not just the claim.

## 6. LIMITATIONS.md (minimum contents)

1. Recovery is on a disclosed DGP family; passing it bounds implementation error, not
   model-misspecification error on reality (VR §8.8 wording; lift tests as the real
   next step).
2. Layer R window is short (state `layer_r_weeks`); which parameters are prior-
   dominated (from VR-501) and what that means for the recommendation.
3. Anonymization: what a€ masking preserves and destroys (AG-041 list verbatim);
   absolute ROAS not interpretable.
4. In-sample counterfactual caveat for the gain metric (DC-302); no competitive
   reaction, no creative quality, no cross-channel synergies modeled.
5. Brand-search endogeneity: why it is modeled but excluded from reallocation
   (AGENTS T-7 paragraph).
6. Promo calendar reconstructed from memory/records (CALIBRATED) + VR-504 outcome.
7. Weekly grain hides within-week dynamics; adstock length L=8 caps measurable
   carryover.
8. Platform-reported metrics are themselves modeled objects (Layer P φ/θ are
   assumptions about HOW platforms over-credit, informing ordering checks only).
9. MCMC reproducibility doctrine (VR §7): what "reproducible" means here.

## 7. Data quality gates index

| Domain | Gate IDs | Spec |
|--------|----------|------|
| Simulator | SIM-070…075 | SPEC-01 §7 |
| Agency intake | AG-060…066 | SPEC-02 §6 |
| dbt models | AD-040…044 | SPEC-03 §4 |
| Model diagnostics | MD-070…074 | SPEC-04 §7 |
| Recovery | VR-301…306, VR-401 | SPEC-05 §§3–4 |
| Sensitivity | VR-501…504 | SPEC-05 §5 |
| Baselines/cross-check | VR-601…602 | SPEC-05 §6 |
| Decision layer | DC-701…705 | SPEC-06 §7 |

## 8. What deliberately does NOT exist

No audit-finding registry, no session handouts, no re-verification matrix, no cron.
The README may link decision-analytics-reconstruction for reviewers who want that
machinery. This repo's governance showpieces are: the layer-order proof, the prior
freeze, the published anonymization protocol, and the leak scan — four mechanisms,
each enforced by a script a reviewer can run.
