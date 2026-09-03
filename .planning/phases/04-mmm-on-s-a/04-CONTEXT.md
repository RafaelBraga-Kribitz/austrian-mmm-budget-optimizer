# Phase 4: MMM on S-A - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning

<domain>
## Phase Boundary

A Bayesian MMM that fits the clean scenario (S-A) with a healthy sampler, so any later
recovery failure can be attributed to the science rather than to the machinery.

Scope is WBS tasks **T-301…T-308** (`docs/EXECUTION_BLUEPRINT/02_WBS.md`, Phase P3):
`transforms.py` (normalized geometric adstock, Hill, scaling pair); MD-070 shared-shape
test; `PriorConfig` + `config/priors_synthetic.yaml`; `build_model`; `posterior_io`;
`diagnostics`; the fit runner + full-budget S-A fit; `elicit.py` converters (ahead of M4).

Critical path (intel `04_DEPENDENCIES`): T-301 → T-302/304 → T-305 → T-306 → T-307 (S-A
fit). T-303 is parallel with T-301 on paper; stacked PRs still sequence it. T-308 does not
block the S-A fit.

**Not in scope:** `config/priors_real.yaml` or `docs/PRIOR_ELICITATION.md` rationales
(human-owned at M4; A-6); Layer R fits or posteriors (A-2, A-5, locked 3A); S-B/S-C full
fits (T-402, Phase 5); recovery suite (Phase 5); copying `m0-bootstrap` science (Phase 4
is not on m0); copying m0 `uv.lock`; inventing Layer R data.

### Corrections to upstream documents applied during this discussion

1. **ROADMAP's Phase 4 "Open item — INGEST-CONFLICTS WARNING 6" is stale.** W6 was closed
   at ingest: the single normative home is `07_QUALITY_STANDARDS` Part A, **≤ 35 min/fit**
   at MD-050 on 4 cores. ADR-006 already scheduled that number into `config/settings.yaml`
   in Phase 4 so a published document stops citing a gitignored one. Settled by D-01.

2. **ROADMAP's Phase 4 effort line still says "2 d including Phase 3".** Plan 03-01 / D-17
   already split M2: Phase 3 = 1 d, Phase 4 = 1 d, each with its own 2× tripwire. Correct
   the ROADMAP line in the close plan (04-08), same interpretation-not-spec-edit pattern
   as 03-09.

3. **SPEC-08 §5 `fit-synthetic` lists three scenario fits.** WBS T-307 fits S-A only;
   T-402 (Phase 5) adds S-B/S-C. This phase implements the T-307 reading. The make-target
   comment is updated to say so; the 35 min/fit ceiling still applies per fit.

4. **`test_sampler_keys_appear_nowhere_else_in_src_ambo` will go red the moment `fit.py`
   reads `settings.sampler.draws`.** The test's intent (no restated MD-050 literals) is
   load-bearing; its current "identifier must not appear" implementation is Phase-1-vacuous
   and must be corrected when the first consumer lands (D-05), not worked around.
</domain>

<decisions>
## Implementation Decisions

### Runtime ceiling and settings (closes ADR-006 Phase-4 deferral, W6)

- **D-01:** `max_fit_minutes: 35` is a **top-level** `Settings` field, sibling of
  `adstock_length`, not a `SamplerConfig` field. Sampler keys stay exactly MD-050
  (`chains`, `tune`, `draws`, `target_accept`, `random_seed`, `init`). The ceiling is an
  operational budget, not a NUTS hyperparameter. `config/settings.yaml` header comments
  that currently say the ceiling "moves here in Phase 4" are replaced with the live key.
  Makefile `FIT_*_RUNTIME` strings cite this value rather than restating a competing
  number. Lands in plan 04-02 with the other `config/` work.

### Numpy / Numba import break (blocks every PyMC import today)

- **D-02:** Keep SPEC-08 §3's declared range `numpy>=1.26,<3` in `[project] dependencies`.
  Add a lock-only pin via `[tool.uv] constraint-dependencies = ["numpy>=1.26,<2.5"]` so
  the resolver cannot pick NumPy 2.5+, which removed `numpy.row_stack`. The currently
  locked `numba==0.63.0b1` (transitive via ArviZ) still overloads `np.row_stack` at import
  time, so `import pymc` / `import arviz` currently raise `AttributeError`. This is not a
  new dependency and not a bound widening — no ADR. Lands in 04-01 because nothing that
  imports PyMC can be tested until the lock resolves to an importable set. Prefer a
  non-beta Numba if the resolver offers one under that numpy cap; do not add Numba as a
  direct dependency.

### Priors files and elicitation doc

- **D-03:** Ship `config/priors_synthetic.yaml` (MD-040) only. **Do not create**
  `config/priors_real.yaml` or draft `PRIOR_ELICITATION.md` rationales. `elicit.py`
  converters + unit tests land in 04-08. MD-061 doc-lint is not written against a
  placeholder document — it waits for the human-owned M4 file. Never fabricate Layer R
  priors (A-5, A-6).

### MD-070 independence

- **D-04:** Model transforms are an independent pytensor implementation in
  `transforms.py`. The numpy reference lives **in the test file**, not in `src/` (T-301
  implementation notes). `tests/unit/test_transform_sanity.py` (04-03) may import both
  `ambo.model.transforms` and `ambo.simulate.dgp`; production packages may not. MD-070
  correlates adstock outputs (before Hill) on S-A spend using each channel's truth λ.
  Equality is not expected and must not be asserted.

### Sampler-key guard, first consumer

- **D-05:** When `fit.py` first reads `Settings.sampler`, rewrite
  `test_sampler_keys_appear_nowhere_else_in_src_ambo` so it still forbids **restated
  MD-050 numeric/string literals** outside `config.py` / `settings.yaml`, but **permits
  attribute access** on a loaded `SamplerConfig`. Do not delete the test. Lands in 04-04.

### Free RV names (Guide §2.2 / T-304 AC)

- **D-06:** Documented name set, used as PyMC RV names with coords — the WBS `_c` suffix
  is index notation, not a literal suffix:

  | RV | coords |
  |----|--------|
  | `alpha` | — |
  | `tau` | — |
  | `gamma_sin` | `fourier` = (1, 2, 3, 4) |
  | `gamma_cos` | `fourier` |
  | `delta_promo` | — |
  | `delta_advent` | — |
  | `delta_jan` | — |
  | `lam` | `channel` |
  | `k` | `channel` |
  | `s` | `channel` |
  | `beta` | `channel` |
  | `sigma` | — |

  Observed: `y` (not a free RV). Data coords also include `week`. Fourier period `52.18`
  and order `4` are named constants in `mmm.py` citing SPEC-04 §2 (D-12) — not settings,
  not tunable.

### FitError

- **D-07:** `FitError(AmboError)` is added in `src/ambo/common/errors.py` in 04-01.
  `ScaleFactors` construction raises it on an all-zero channel. `build_model` raises it
  when a requested channel has no `spend_<channel>` column. Same redaction invariant as
  every `AmboError`.

### Plan split equals WBS (4B)

- **D-08:** One GSD plan per WBS task, stacked PRs off `cursor/m2-warehouse-close-9588`:

  | Plan | WBS | Wave |
  |------|-----|------|
  | 04-01 | T-301 transforms (adstock + Hill + scaling) + D-02 numpy pin + FitError | 1 |
  | 04-02 | T-303 PriorConfig + priors_synthetic.yaml + D-01 max_fit_minutes | 2 |
  | 04-03 | T-302 MD-070 shared-shape test | 3 |
  | 04-04 | T-304 `build_model` + thin `sample_model` + smoke test | 4 |
  | 04-05 | T-305 posterior_io | 5 |
  | 04-06 | T-306 diagnostics | 6 |
  | 04-07 | T-307 `run_fit` + `make fit-synthetic` + full S-A fit artifacts | 7 |
  | 04-08 | T-308 elicit.py + M2 close (ROADMAP/STATE/BUILD_LOG) | 8 |

  Scaling is **not** a separate plan — T-301 owns the pair. Smoke sampling is a thin
  `pm.sample` wrapper in `fit.py` in 04-04 so the confinement guard has a legal home
  before the full CLI exists (D-11).

### Full S-A fit is a real NUTS run

- **D-09:** Plan 04-07 actually runs MD-050 on P-SA (4 chains, tune=1000, draws=1000,
  target_accept=0.9, seed=42, init=jitter+adapt_diag). Wall time is logged to
  `docs/BUILD_LOG.md`. Thinned parquet every 4th draw → 1000 rows. NetCDF local /
  gitignored (`*.nc` already ignored). No checksum tests on draws (T-6). Fits are make
  targets, never implicit in `make all`, never the default `make test` path. If MD-071
  fails: MD-073 ladder in order, one rung per attempt, ADR-005 if leaving rung 1; two
  failed root-cause attempts ⇒ stop and ask the human.

### `channels_present`

- **D-10:** `fit.py` (not `mmm.py`) reads `dim_layer` via `db.read_dim_layer()`, parses
  the comma-joined `channels_present` string (taxonomy order), and passes that list into
  `build_model`. `mmm.py` has no scenario/layer branches and does not import `db`.
  Structurally absent `other` on Layer P gets no β. Present-but-ineffective S-C
  `display_video` is modeled (recovery owns the zero-effect gate).

### Smoke vs full runner

- **D-11:** 04-04 adds `sample_model(model, *, draws, tune, chains, target_accept,
  random_seed, init, **kwargs) -> az.InferenceData` as the **only** `pm.sample` call site.
  The CI smoke test (S-A first 60 weeks, 1 chain, 200/200, `@pytest.mark.smoke`) calls
  this helper. 04-07 adds `run_fit` / CLI / `make fit-synthetic` on top of it.

### Fourier constants

- **D-12:** `FOURIER_PERIOD_WEEKS = 52.18` and `FOURIER_ORDER = 4` live in `mmm.py` as
  named constants with a SPEC-04 §2 citation. They are spec math, not configuration.

### `from_model_scale` growth

- **D-13:** 04-01 ships the DataFrame inverse pair (`to_model_scale` /
  `from_model_scale`) property-tested to 1e-12. Contribution / ROAS back-transforms are
  added in the same module when posterior_io or diagnostics need them (04-05/04-06) —
  still the only back-transformation site (T-1). Do not scatter `* revenue_mean` in
  report code.

### R-10 compiler

- **D-14:** This environment has `/usr/bin/g++`; PyTensor reports it as `cxx`. R-10
  remains a Windows-dev risk. No new `make setup` compiler probe this phase (scope).

### `transforms.py` purity

- **D-15:** `transforms.py` does not call `load_settings()`. `L` is an argument.
  Callers pass `load_settings().adstock_length`. Keeps the math pure and the "L from
  settings, not code" rule mechanically obvious.

### Coverage fail-under

- **D-16:** Leave `--cov-fail-under=80` commented (Phase 1 D-15). Flipping it is not
  this phase's gate. Do not silently uncomment.

### `reports/model/`

- **D-17:** Add `reports/model/.gitkeep` in 04-06 (or 04-07 if the first committed file
  is the diag report itself). SPEC-08 §2 lists `reports/model/`.

### Pytensor in src, numpy in tests

- **D-18:** Production adstock/Hill are pytensor graphs, evaluated in tests via
  `pytensor.function`. Independent numpy references in `tests/unit/test_transforms.py`
  must agree to 1e-10. Convolution is an unrolled length-L causal sum (L is a Python
  int, typically 8) — not `scan`, not `np.convolve` in `src/` (T-2 hides in clever
  vectorization; the simulator already rejected that for the same reason). Tests MAY
  use `np.convolve(x, w, mode="full")[:T]` as the numpy reference: research verified it
  matches the causal loop to ~1e-16, and the reversed kernel does not.

### Prior YAML shape

- **D-19:** `PriorConfig.channels` is an explicit `dict[str, ChannelPrior]` listing
  every SPEC-02 §5.2 channel, even when values are identical (T-303: explicit >
  implicit). MD-040's test asserts value-equality across those entries for
  `priors_synthetic.yaml`, not schema-level identity. Globals match SPEC-04 §4
  exactly. `s` is truncated Gamma(3, 2) on [0.3, 3.0]. K is Gamma(shape=2, rate=1.3)
  in scaled spend units.

### `make fit-synthetic` this phase

- **D-20:** The target fits **P-SA only**. Runtime banner still prints the 35 min
  ceiling from `max_fit_minutes`. Comment names T-402 as the S-B/S-C extension.
</decisions>

<specifics>
## Specific Ideas

- Impulse-response test before closed-form / correlation tests, same ordering as
  `tests/unit/test_dgp.py` (02-RESEARCH Pitfall 4 / T-2).
- `ScaleFactors` is a frozen pydantic `BaseModel` or frozen dataclass; all values > 0.
  Nonzero-week mean: `x[x > 0].mean()`, never `x.mean()` (zeros are real weeks, not
  missingness).
- Thin parquet columns `<var>` or `<var>__<channel>` (03_MODULES §4.5). Metadata in
  parquet schema metadata (single file, no sidecar).
- `DiagGates.standard()` / `DiagGates.layer_r()` — explicit at the call site.
- Variant flag parsed in 04-07 (`flat|nopromo|loco-<ch>|holdout`) even if only the
  default path is wired; interface stable for Phase 5/7.
- CI smoke already has `SMOKE=1` on job 2 and warehouse-before-pytest; 04-04 only
  needs to add the marked test. Do not add a seventh CI job.
</specifics>

<deferred>
## Deferred Ideas (OUT OF SCOPE)

- `config/priors_real.yaml` and `PRIOR_ELICITATION.md` content — **Phase 6 / M4, human**.
- S-B / S-C full-budget fits — **Phase 5, T-402**.
- MD-080…083 contribution / ROAS / response-curve **exports** — machinery may start in
  transforms/posterior_io; the committed export files are Phase 8/9.
- MD-061 doc-lint against PRIOR_ELICITATION.md — **Phase 6**.
- Coverage-gate flip — not this phase.
- R-10 Windows compiler check in `make setup`.
- Revisit leak-scan scope for `exports/*.csv` — **Phase 6** (R-14).
- Golden tolerance bands — **Phase 5**.
- Charter §7 degradation ADR — **Phase 6** if permission fails (locked 3A).
</deferred>
