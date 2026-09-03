# Phase 4: MMM on S-A - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-03
**Phase:** 4-MMM-on-S-A
**Areas discussed:** W6 ceiling home, numpy/numba break, plan split vs WBS, RV naming,
fit-synthetic scenario count, priors_real presence, sampler-key test rewrite

---

## Runtime ceiling home (W6 / ADR-006 Phase-4 deferral)

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level `Settings.max_fit_minutes` (Recommended) | Sibling of `adstock_length`; sampler block stays MD-050-pure | ✓ |
| Field on `SamplerConfig` | Mixes an operational budget into NUTS kwargs; trips the identifier-greedy sampler-key test | |
| Leave it only in gitignored 07_QUALITY_STANDARDS | Leaves ADR-006's published-citation deferral open | |

**Notes:** → CONTEXT D-01.

---

## Numpy 2.5 / Numba `row_stack`

| Option | Description | Selected |
|--------|-------------|----------|
| uv `constraint-dependencies` numpy<2.5, SPEC range unchanged (Recommended) | Restores `import pymc` without an ADR or a spec edit | ✓ |
| Change `[project] dependencies` to `numpy>=1.26,<2.5` | Contradicts SPEC-08 §3's declared `<3` | |
| Add numba as a direct pin | New dependency → EB-030 ADR; Numba is ArviZ's transitive | |
| Monkeypatch `np.row_stack = np.vstack` in `ambo/__init__.py` | Hides a lockfile break; fails the "honest engineering" bar | |

**Notes:** → CONTEXT D-02.

---

## Plan granularity

| Option | Description | Selected |
|--------|-------------|----------|
| 1:1 with T-301…T-308 (Recommended) | Matches 4B and the WBS critical path | ✓ |
| Split T-301 into adstock vs scaling | Two PRs for one WBS card; scaling is the same trap module | |
| Combine T-305+T-306+T-307 | One giant fit PR; harder to review; smoke would land too late | |

**Notes:** → CONTEXT D-08. Smoke's `pm.sample` site is carved into 04-04 (D-11) so
confinement is non-vacuous before the 15–35 min run.

---

## Free RV names

| Option | Description | Selected |
|--------|-------------|----------|
| `lam`/`k`/`s`/`beta` with `channel` coord (Recommended) | PyMC idiom; WBS `_c` read as index notation | ✓ |
| Literal names `lam_c`, `k_c`, … | Fights ArviZ flattening (`lam_c` vs `lam[channel]`) | |
| One RV per channel (`lam_search_brand`, …) | Explodes the name set; MD-040 channel-agnostic priors become awkward | |

**Notes:** → CONTEXT D-06.

---

## `make fit-synthetic` scenario count

| Option | Description | Selected |
|--------|-------------|----------|
| P-SA only this phase (Recommended) | Matches T-307; T-402 owns S-B/S-C | ✓ |
| Fit all three now | ~3× compute; Phase 5 recovery still needs those posteriors but T-402 is the named task | |

**Notes:** → CONTEXT D-20.

---

## `priors_real.yaml` in Phase 4

| Option | Description | Selected |
|--------|-------------|----------|
| Do not create (Recommended) | A-5/A-6; human owns M4 content | ✓ |
| Empty schema file | A placeholder that looks like a freeze | |
| Copy synthetic → real | Encodes Layer P into the Layer R prior file | |

**Notes:** → CONTEXT D-03.
