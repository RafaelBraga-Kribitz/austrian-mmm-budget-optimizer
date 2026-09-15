# ADR-012 — Five-channel Layer P and Charter §7 degradation

- **Status:** Accepted
- **Date:** 2026-09-15
- **Deciders:** Rafael Braga-Kribitz (via STATUS.md D-05 on `main`); recorded here so
  the deviation is an ADR, not a silent fork of SPEC-01.
- **Supersedes:** —
- **Related:** STATUS.md D-05, D-06, D-08; `PROJECT_CHARTER.md` §2.1, §7; SPEC-01 §4–§5;
  SPEC-04 §2; SPEC-05 §3; AGENTS A-5

---

## Context

The 2026-09-15 rebuild on `main` discarded the stacked GSD package (dbt warehouse,
six-channel SPEC-01 taxonomy, pydantic settings) and started a flat `src/ambo`
package. STATUS.md D-05 names five Layer P channels (TV, Radio, Print, Paid Search,
Paid Social). There is no private agency drop in the repository, and A-5 forbids
inventing Layer R spend or revenue. Charter §7 already describes the shippable
degradation: Layers P + D on disclosed synthetic truth.

SPEC-01 still describes six channels and three scenarios (S-A/S-B/S-C). Shipping
the five-channel advertiser without an ADR would be a silent spec deviation.

## Decision

1. **Layer P taxonomy is the five STATUS D-05 channels.** Mechanics stay those of
   SPEC-01 (geometric adstock, Hill saturation, flighted offline media, platform
   over-credit on online channels). Parameter values are mapped from SPEC-01 §4:
   Paid Search ← search_generic, Paid Social ← meta, TV ← display_video, Print ←
   print_regional, Radio ← radio. There is no brand-search line, so the optimiser
   may reallocate every channel (STATUS constraint 12).
2. **One 156-week clean series is the reported Layer P fit** (S-A analogue, seed
   101). S-B collinearity and S-C zero-effect remain callable in `ambo.synth.generate`
   (`collinear=True`, `zero_channel=...`) and are unit-tested; they are not the
   reported fit in this build.
3. **Charter §7 degradation is in force.** `ambo.data.load_layer_r` raises rather
   than fabricating a public demo series. The optimiser and attribution-gap module
   run on Layer P. README uses the alternate framing (validated MMM + optimiser on
   disclosed ground truth).
4. **Python 3.11 and nutpie** are accepted (STATUS D-06, D-08). Spec asked for 3.12
   and `pm.sample` NUTS; nutpie is the primary sampler with PyMC NUTS as fallback.
5. **Recovery gates** are the SPEC-05 observables (ROAS HDI coverage, Spearman,
   curve MAE%, half-life direction, media-share) evaluated on five channels, not
   six. Thresholds are those of the S-A/S-B band adapted to n=5 (coverage ≥ 4/5,
   Spearman ≥ 0.70, median curve MAE% ≤ 15). They live in `ambo.evaluate`, not as a
   silent widening of `config/recovery_gates.yaml` (that file is not in this
   package). Widening further still requires a new ADR.

The output contract preserved: every reported ROAS, contribution, gain, and gap
carries a 90% HDI (A-7); simulator and model share no transform code (SIM-003);
platform numbers are never a calibration target (T-8).

## Consequences

- Reviewers comparing this repo to SPEC-01 will see five names, not six. The
  mapping is in this ADR and in `CHANNEL_SPECS` in `src/ambo/synth.py`.
- M3 “all three scenarios green” is not claimed. The reported recovery table is
  one Layer P series.
- Layer R results cannot appear until a real drop is ingested (A-2, A-5).
- CI does not run the full NUTS fit (`pytest -m "not slow"`). Full regeneration is
  `python -m ambo.run layer_p`.

## Spec deviations

| REQ / clause | Spec said | This ADR | Output contract preserved |
|---|---|---|---|
| SPEC-01 §4 taxonomy | six channels including `search_brand` | five channels, no brand search | Same DGP maths; truth.json still has per-channel ROAS, φ, curves |
| SPEC-01 §5 | S-A/S-B/S-C all reported | S-A analogue reported; S-B/S-C helpers tested | generate() still encodes collinearity and zero-effect |
| SPEC-04 §2 controls | promo + advent + January | one holiday flag + Fourier | Additive level model, scaled inputs |
| SPEC-04 MD-050 | PyMC NUTS, 4×1000, target_accept 0.9 | nutpie primary, same draw budget | Diagnostics still MD-071 |
| SPEC-05 §3 | six-channel cell counts | five-channel analogue in evaluate.py | Observables (ROAS, shape, share), not K/s point recovery |
| SPEC-08 Python | 3.12 | 3.11 (D-06) | None in the maths |
| Charter §7 | optional degradation ADR at M4 | taken now; no Layer R | README alternate framing |

## Amendment 2026-09-15 — calendar, MD-073 rung 1, MD-020

The original spec-deviations table recorded a holiday-only control. That was the
Stage 1 skeleton, not the intended end state.

1. **SPEC-04 §2 calendar.** Promo, Advent, and January-dip dummies now sit on top
   of the Fourier block, plus the D-07 holiday indicator. Leaving Advent out of
   the linear predictor dumped the DGP's +55% Advent baseline onto flighted
   print/radio (VR-310 attempt 1). The "one holiday flag" row above is
   superseded. Output contract unchanged: additive-in-level, scaled inputs.
2. **MD-073 rung 1.** `target_accept=0.95` after 53 divergences at 0.9. MD-071
   went green on the calendar-controlled Layer P fit (0 divergences, R-hat <
   1.01, ESS > 400). No further ladder rungs in this amendment.
3. **MD-020 normalised adstock.** Stage 1 shipped unnormalised truncated weights.
   The model, evaluate, OLS, and optimiser now use
   `w_i = λ^i / Σ_{i=0..L−1} λ^i` together. At constant weekly spend the
   steady-state adstock equals the spend itself (DC-201). Recovery gates are
   **not** widened.

Implements: MD-020, MD-022, MD-073.
