# 09 — ANTI-PATTERNS (forbidden implementations)

Each entry: what it looks like in THIS repo, the concrete failure it causes, and the
enforcement that catches it. Reviewers check this list explicitly ([06 STD]).

## A-1 Simulator–model incest (trap T-3)
Sharing adstock/Hill/scaling code (or "just a small helper") between `simulate/` and
`model/`. **Failure:** recovery becomes circular — the model recovers its own code,
not truth; the entire Q1 argument collapses. **Enforcement:** AST guard test (T-010);
the sanctioned exception is shared *config data* (`season_windows.csv`, AD-020) —
never shared transforms.

## A-2 Magic numbers
Sampler settings, gate thresholds, L, grid sizes, budgets inline in code.
**Failure:** spec drift becomes invisible; MD-050 "fixed settings" stops being
checkable. **Enforcement:** settings/config objects (B4); grep review; the VR §3
gate table and MD-050 block live in exactly one place each.

## A-3 Hardcoded paths
Absolute paths, `C:\...`, home-relative paths, or the private-drop path in code.
**Failure:** breaks fresh-clone reproduction (DL-1); private path in code is a leak.
**Enforcement:** `paths` config + pathlib; leak scan pattern for drive-letter paths.

## A-4 Notebook-driven production
Any load-bearing logic in a notebook; committed notebook outputs. **Failure:** leak
surface (outputs can embed real values) + irreproducibility. **Enforcement:** W-4
(notebooks read make-produced artifacts only), nbstripout hook, leak scan.

## A-5 Hidden state & mutable globals
Module-level mutable caches, `np.random.seed()` global seeding, mutable default
args, state smuggled between pipeline stages in memory. **Failure:** determinism
gates (SIM-070, DC-703, VR-701) fail intermittently — the most expensive class of
bug to chase. **Enforcement:** explicit `Generator` injection (B7 tests re-run
functions twice); review.

## A-6 Data leakage (scientific)
Computing ScaleFactors on the full window for a holdout fit; using future weeks in
any feature; letting truth.json values steer model/prior choices for Layer P fits
(MD-040 exists to prevent exactly this); calibrating anything against platform
conversions (trap T-8). **Failure:** recovery/holdout results are fake-good; the
project's honesty claim dies. **Enforcement:** holdout leakage test (Guide §4.2);
MD-040 channel-agnostic test; review of every feature construction.

## A-7 Silent failures & swallowed exceptions
`except: pass`, defaulting on parse errors, warnings that only reach logs, gate
runners that print-but-exit-0. **Failure:** a red gate ships as green.
**Enforcement:** B6 error rules; gate runners' exit-code tests; poisoned-fixture
tests for every gate's failure direction.

## A-8 Copy-paste logic
Re-deriving ROAS/back-transform/caption text/format strings at a second site.
**Failure:** SSOT violations — README says 3.4×, chart says 3.6×. **Enforcement:**
single-home rules: back-transform only in `transforms.py`; captions only in
`captions.py` (grep-test GB-102); numbers only via SSOT (GB-303 checker); ROAS
computation only in `recovery.py`/model outputs.

## A-9 Spec drift
Implementing a "better" adstock, changing gate thresholds to pass, renaming export
columns, "improving" the DGP. **Failure:** the spec-supremacy contract (A-1 AGENTS)
breaks; downstream specs silently desync. **Enforcement:** spec-table equality
tests (T-101, T-401); ADR requirement for any deviation; review against REQ IDs.

## A-10 Prior tampering after freeze
Adjusting `priors_real.yaml` (or its interpretation) after seeing Layer R results;
re-running elicitation "because the fit looked wrong". **Failure:** destroys the
project's central epistemic claim (E-3); detectable forever in git history.
**Enforcement:** `check_layer_order.py` GB-502; A-6 AGENTS; the sanctioned
alternative is VR-501 sensitivity analysis.

## A-11 Point estimates without uncertainty
Reporting ROAS/gain/gap medians alone; charts without HDI whiskers/bands; SSOT keys
without their `_hdi90_*` companions. **Failure:** violates A-7 (AGENTS); the artifact
is wrong by definition. **Enforcement:** M7 A-7 sweep ([06 §M7](06_CHECKLISTS.md));
SSOT key-pair review.

## A-12 Unsanctioned caching / memoization of results
Caching fit results keyed on nothing, reusing stale posteriors after data/prior
changes, hand-copying numbers between artifacts. **Failure:** artifacts desync from
inputs; freshness check (GB §4) can't see it. **Enforcement:** posterior metadata
(data/prior hashes) + loader refusal; `make` dependency discipline; SSOT freshness
in PRs.

## A-13 Over-engineering
Abstract transform interfaces "for other saturation curves", plugin registries for
channels, async pipelines, config inheritance trees, premature vectorization of the
simulator loop. **Failure:** effort budget blown (Charter §5 tripwire), review
surface grows, no gate gets greener. **Enforcement:** [08 patterns-not-used](08_PATTERNS.md);
Charter O-1..O-8 scope walls; review question "which gate does this abstraction
serve?".

## A-14 Premature optimization
Optimizing sampler/pytensor internals before MD-071 fails; micro-tuning dbt;
rewriting the convolution for speed before profiling. **Failure:** wasted budget +
new bug surface in the highest-risk code. **Enforcement:** performance thresholds
(07 Part A) are generous; optimize only on measured breach, log the measurement.

## A-15 Circular imports
Any import cycle, incl. via `common` growing upward dependencies. **Failure:**
import-time crashes, untestable modules. **Enforcement:** [03 §10] edge list; ruff
`TID`/import-linter-style guard test if a cycle ever appears (add to T-010).

## A-16 Configuration duplication
The same constant in settings.yaml AND a module AND dbt vars without a
cross-check. **Failure:** silent divergence (taxonomy drift between Python and
dbt is the live risk). **Enforcement:** where duplication across languages is
unavoidable (dbt vars vs settings), a pytest equality-checks them (Guide §8.1);
everywhere else: one home only.

## A-17 History rewriting
Force-push, rebase of pushed branches, amending pushed commits, "cleaning up" the
M4 diff after the fact. **Failure:** the layer-order proof becomes unverifiable —
worse than any mess it would clean. **Enforcement:** EB-082; branch protection;
if something private landed: STOP, human performs documented remediation (A-4
AGENTS).

## A-18 Gate gaming
Widening thresholds, cherry-picking seeds, re-running until green, marking S-C
"expected fail". **Failure:** the gates stop meaning anything; reviewers can see
threshold history in git. **Enforcement:** VR-310 (widening ⇒ ADR naming suspected
structural cause); fixed seeds in config; golden bands regeneration requires PR
justification (EB-073).

## A-19 Unit-masking mistakes (a€ discipline)
Writing real € in Layer R artifacts; mixing `_eur`/`_aeur` columns in a mart;
omitting the a€ caption; printing absolute ROAS claims from masked data as if
absolute. **Failure:** anonymization breach or honesty breach. **Enforcement:**
AD-043 dbt test; E-5 caption single-source + grep; leak scan; LIMITATIONS §3
wording.

## A-20 Compute in CI
Running full fits in CI, letting `make all` trigger sampling implicitly, cron
workflows. **Failure:** EB-061/O-7 violations, 6-hour CI, flaky golden tests.
**Enforcement:** `fit` marker never in CI; BP-D-20 fail-fast make behavior; single
workflow file review.
