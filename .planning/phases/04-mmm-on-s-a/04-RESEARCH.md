# Phase 4: MMM on S-A - Research

**Researched:** 2026-09-03
**Domain:** raw PyMC MMM; pytensor adstock/Hill; scaling; NUTS diagnostics; prior YAML
**Confidence:** HIGH on transforms/convolution/numpy-break (empirically verified on this
machine and lockfile); HIGH on contracts (03_MODULES §4 + SPEC-04 + WBS T-301…T-308 read
in full); MEDIUM on full-fit wall time until 04-07 actually runs MD-050 here.

<user_constraints>
## User Constraints (from CONTEXT.md)

Locked 1A 2A 3A 4B still apply. Phase 4 is **not** on `m0-bootstrap` — implement from
specs. Do not copy m0 `uv.lock`. Do not invent Layer R. Simulator and model share no
production code.

**D-01…D-20** from CONTEXT.md are in force. Do not re-litigate W6, MD-020's deliberate
parameterization mismatch, or the T-307 "S-A only this phase" reading of `fit-synthetic`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-q1-truth-recovery (contributing) | Model must be able to recover known truth later; this phase ships a healthy S-A fit and MD-070 | Convolution direction empirically pinned; MD-070 preview r ≥ 0.999 on all six S-A channels |
| REQ-q2-real-incremental-roas (contributing) | One model definition serves all layers | `build_model(df, channels, priors)` has no scenario branches; channel list drives media terms |
| REQ-dl6-priors-as-deliverable (contributing) | `elicit.py` built here ahead of M4 | Converters specified in 03_MODULES §4.7; MD-061 lint deferred with the human doc |
| REQ-dl8-quality (contributing) | lint/test/CI including smoke-fit | Smoke profile already wired in `ci.yml` job 2 (`SMOKE=1`); 04-04 adds the marked test |
</phase_requirements>

## Summary

Phase 4 turns the frozen `fct_mmm_input` contract into a raw-PyMC model, a full-budget
S-A posterior, and the diagnostics a reviewer reads before believing recovery. The math
is SPEC-04 §2 exactly; the transforms are a **deliberate** mismatch with SPEC-01
(normalized finite convolution vs raw recursion). Three findings change how the plans
must be written:

1. **`import pymc` currently fails on this lockfile.** NumPy 2.5.2 removed
   `numpy.row_stack`; transitive `numba==0.63.0b1` still overloads it at import, and
   ArviZ imports Numba on the way in. PyTensor itself imports fine and sees `/usr/bin/g++`.
   D-02's uv constraint (`numpy<2.5`) is a prerequisite of every later plan that touches
   PyMC, so it belongs in 04-01 — not next to `mmm.py`.

2. **Causal convolution is `np.convolve(x, w, mode="full")[:T]` with
   `w_i = λ^i / Σ_{j=0}^{L-1} λ^j`.** An explicit double loop and that convolve agree to
   ~1e-16. The **reversed** kernel disagrees at 0.54 on a random series (T-2). Production
   code still uses an unrolled length-L sum, not `np.convolve`, matching the simulator's
   "no clever vectorization in src" discipline. Tests may use the verified convolve as
   the numpy reference.

3. **MD-070 will not be the hard part on S-A.** Truth-λ adstock outputs of the recursive
   DGP vs L=8 normalized convolution correlate at r ∈ [0.99986, 1.0] across all six
   channels. The gate is r > 0.95. A fail would mean a reversed kernel or an off-by-one,
   not a borderline correlation. The test still belongs **before** the first fit (T-302
   blocks T-307) because that is the cheap T-2 catch.

**Primary recommendation:** Execute D-08's eight stacked plans. Pin numpy in 04-01.
Keep `transforms.py` pytensor-pure with L as an argument. Put the only `pm.sample` in
`fit.sample_model` in 04-04. Run the real S-A NUTS fit in 04-07. Do not author
`priors_real.yaml`.

## Standard Stack

| Piece | Version / pin | Role this phase |
|-------|---------------|-----------------|
| Python | 3.12 (already) | runtime |
| numpy | declared `>=1.26,<3`; lock constrained `<2.5` (D-02) | arrays; currently 2.5.2 **broken** with locked Numba |
| pytensor | 2.38.3 (via pymc) | transform graphs; `cxx=/usr/bin/g++` |
| pymc | 5.28.5 (`>=5.15,<6`) | `pm.Model` / `pm.sample` |
| arviz | 0.23.4 | InferenceData, R-hat, ESS, BFMI, PPC |
| scipy | already pinned | `elicit.py` brentq (04-08) |
| pandas / pydantic / PyYAML | already | ScaleFactors, PriorConfig, YAML |

No new direct dependency. Hypothesis is already a dev dependency (ADR-007) and is the
right tool for the scaling round-trip property test.

## Architecture Patterns (external + this repo)

1. **Causal finite geometric adstock.** Weights `w_i = λ^i / Σ λ^j` for `i = 0…L-1`.
   Output at t uses x[t], x[t-1], … only (postcondition in 03_MODULES §4.1). Unroll L
   in Python when building the pytensor graph:

   ```python
   delayed = x if i == 0 else pt.concatenate([pt.zeros((i,)), x[:-i]])
   acc = acc + w[i] * delayed
   ```

2. **Hill.** Identical formula to SPEC-01 §2.2: `a^s / (a^s + K^s)`. Independent
   implementation. `Hill(K, K, s) = 0.5` is the point test.

3. **Scaling (T-1).** `y / mean(y)`; per-channel `x / mean(x[x>0])`. Inverse is
   multiplication by the stored means. K priors are in **scaled** spend units
   (Gamma(2, 1.3) ⇒ mean 2/1.3 ≈ 1.538 ≈ 1.5× mean scaled spend).

4. **PyMC model construction.** `with pm.Model(coords=...)` ; `pm.Data` for observed
   spend/dummies; `pm.sample` **only** in `fit.py`. Truncated slope:
   `pm.Truncated("s", pm.Gamma.dist(alpha=3, beta=2), lower=0.3, upper=3.0, dims="channel")`.
   PyMC 5 Gamma uses `alpha` (shape) and `beta` (rate).

5. **This repo's own analogs.** `dgp.adstock_recursive` impulse-first tests;
   `common/config.py` pydantic `extra='forbid'` + frozen; `common/errors.py` subclass
   pattern; simulate CLI atomic writes (`os.replace` after `.tmp-<pid>`).

## Don't Do This (anti-patterns)

- Import `ambo.simulate` from `ambo.model` (or vice versa) — T-3, SIM-003, guard test.
- `np.convolve` / `lfilter` / strided tricks **in `src/ambo/model/`** — T-2.
- Log-transform revenue — MD-001 / T-9.
- Hardcode `L = 8` inside `transforms.py` — L is config, passed in.
- Restate MD-050 literals (`chains=4`, `tune=1000`, …) in `fit.py`.
- `pm.sample` in `mmm.py`, tests (via a local import of pymc.sample), or notebooks.
- Checksum tests on posterior draws — T-6.
- Channel-differentiated values in `priors_synthetic.yaml` — MD-040.
- A β for structurally absent `other` on Layer P — D-13 of Phase 3 / D-10 here.
- `priors_real.yaml` placeholder — A-5/A-6.
- Fitting inside `make all` or default `make test`.
- Leaving rung 1 of MD-073 without ADR-005.

## Common Pitfalls

### Pitfall 1 — NumPy 2.5 removes `row_stack`; locked Numba still overloads it

**What goes wrong:** `uv run python -c "import pymc"` raises
`AttributeError: module 'numpy' has no attribute 'row_stack'` at ArviZ→Numba import.
Observed here: numpy 2.5.2, numba 0.63.0b1, arviz 0.23.4, pymc 5.28.5. PyTensor
imports cleanly.

**Why:** NumPy 2.5.0 (2026-06-21) removed the `row_stack` alias (deprecated since 2.0).
Numba 0.63.0b1 still does `overload(np.row_stack)` at import.

**Fix:** D-02. `[tool.uv] constraint-dependencies = ["numpy>=1.26,<2.5"]` then
`uv lock`. Prove with `uv run python -c "import pymc, arviz"`. Do not add Numba as a
direct dependency. Do not change SPEC-08's declared `numpy>=1.26,<3`.

**Detection:** 04-01 Task acceptance includes a successful `import pymc`.

### Pitfall 2 — `test_sampler_keys_appear_nowhere_else_in_src_ambo` is identifier-greedy

**What goes wrong:** The first module that writes `settings.sampler.draws` fails CI
because the test regexes every SamplerConfig field name anywhere under `src/ambo/`
except `config.py`.

**Fix:** D-05 in 04-04. Keep the single-home rule; forbid restated literals
(`4`, `1000`, `0.9`, `42`, `jitter+adapt_diag` assigned as sampling args) rather than
forbidding the words `draws` / `tune`.

### Pitfall 3 — Reversed convolution looks plausible and destroys recovery (T-2)

**What goes wrong:** `np.convolve(x, w[::-1], …)` still produces a smooth decaying
series. Empirically, vs the causal loop, max abs error was **0.54** on a random length-80
series with λ=0.6, L=8; the forward kernel agreed to 1e-16.

**Fix:** Impulse test first: zeros before the impulse week; at the impulse week the
output equals `w_0`; the next week equals `w_1`, etc. Unrolled pytensor sum in src.
Numpy reference in the test file may use the verified forward `np.convolve`.

**Detection:** `test_adstock_impulse_response_is_causal` plus pytensor-vs-numpy 1e-10.

### Pitfall 4 — MD-070 equality vs correlation

**What goes wrong:** An implementer "fixes" normalized vs recursive to match, collapsing
the recovery argument (MD-020, T-3).

**Fix:** Test docstring states equality is not expected. Assert `r > 0.95` only.
Preview on this machine (S-A spend, truth λ, L=8):

| channel | λ | r |
|---------|-----|------|
| search_brand | 0.10 | 1.000000 |
| search_generic | 0.20 | 1.000000 |
| meta | 0.35 | 1.000000 |
| display_video | 0.50 | 0.999950 |
| print_regional | 0.60 | 0.999865 |
| radio | 0.55 | 0.999969 |

### Pitfall 5 — `pm.sample` confinement vs smoke tests

**What goes wrong:** A smoke test that calls `pm.sample` in `tests/` is fine (the AST
guard scans `src/ambo/` only), but putting `pm.sample` in `mmm.py` to "try the model"
fails `test_pymc_sample_called_only_in_model_fit`. Until `fit.py` exists, there is
**no legal production call site**.

**Fix:** D-11. 04-04 creates `fit.sample_model` as that site; smoke imports it.

### Pitfall 6 — Scaling with `mean(spend)` including zeros

**What goes wrong:** Flighted channels (print, radio) have many zero weeks. Including
them shrinks the spend mean, inflates scaled x, and shifts K relative to the 1.5×
interpretation.

**Fix:** `spend_means[c] = x[x > 0].mean()`. All-zero channel → `FitError` naming the
channel, never a silent 1.0.

### Pitfall 7 — `channels_present` is a comma-string, not a list

**What goes wrong:** Treating the DuckDB varchar as already-split, or splitting and
then iterating seven `spend_*` columns anyway.

**Fix:** Parse on `,`, strip, keep taxonomy order. Only those names become the
`channel` coord. `spend_other` stays 0.0 on Layer P and gets no RV.

### Pitfall 8 — Hill numerical issues at a=0

**What goes wrong:** `0**s` is fine for s>0 in numpy; pytensor may still need a clip
for graph stability. Do not rewrite the formula.

**Fix:** Point tests: `hill(0)=0`, `hill(K)=0.5`. If pytensor needs
`pt.maximum(a, 0.0)` that is a domain assertion, not a formula change.

## Code Examples (verified locally)

### Numpy reference adstock (test file only)

```python
def numpy_geometric_adstock_weights(lam: float, length: int) -> np.ndarray:
    idx = np.arange(length, dtype=np.float64)
    weights = lam**idx
    return weights / weights.sum()


def numpy_adstock_convolve(x: np.ndarray, lam: float, length: int) -> np.ndarray:
    weights = numpy_geometric_adstock_weights(lam, length)
    return np.convolve(x, weights, mode="full")[: len(x)]
```

Verified: agrees with the double loop to ~1e-16; impulse at t=5 with λ=0.6, L=8 gives
`a[:5]==0`, `a[5]==w[0]≈0.4068`, `a[6]==w[1]≈0.2441`.

### Gamma(2, 1.3) in scaled units

Mean = shape/rate = 2/1.3 ≈ 1.538. Mode = (shape-1)/rate ≈ 0.769. Matches MD-040's
"around 1.5× mean spend" for the **mean**, not the mode. T-303's "≈ mode 0.77, mean
1.54" note is correct — do not "fix" the prior to make the mode 1.5.

## State of the Art

Standard geometric adstock + Hill MMM in raw PyMC; pymc-marketing stays confined to
`validate/crosscheck.py` (does not exist yet). No new framework. Fourier order 4 with
period 52.18 (ISO-week year) plus Austrian calendar dummies on top is the SPEC-04
design — do not replace it with a Prophet seasonality or a Gaussian process.

## Open Questions (resolved in CONTEXT; recorded here as closed)

| # | Question | Resolution |
|---|----------|------------|
| 1 | Where does the 35 min ceiling live? | D-01: `Settings.max_fit_minutes`, plan 04-02 |
| 2 | How to make `import pymc` work? | D-02: uv constraint numpy<2.5, plan 04-01 |
| 3 | Literal `lam_c` vs dims? | D-06: `lam` with `channel` coord |
| 4 | Does `fit-synthetic` run three scenarios now? | D-20: P-SA only; T-402 later |
| 5 | Numpy reference in src or tests? | D-18 / T-301: tests only |

No remaining open research questions that block planning.
