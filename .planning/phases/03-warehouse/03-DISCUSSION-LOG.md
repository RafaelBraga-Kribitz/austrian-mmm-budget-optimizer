# Phase 3: Warehouse - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-05
**Phase:** 3-Warehouse
**Areas discussed:** Export commit policy, Contract-freeze enforcement, Test rigor beyond WBS,
M2 budget & sequencing, Layer R staging branch timing, `make transform` guard retirement,
`fct_platform_reported` scope, Warehouse path portability

**Areas offered and selected:** all four of the initial gray areas were selected, then all four
of the second round.

---

## Export commit policy

### Q1 — `exports/mmm_input_weekly.csv`: committed or gitignored?

| Option | Description | Selected |
|--------|-------------|----------|
| Committed (Recommended) | Follow SPEC-08 §2 + EB-081 post-W5; DL-1 needs a committed version to diff against; treat WBS T-205 AC-3 as stale | ✓ |
| Gitignored | Follow WBS T-205 AC-3 literally; reopens W5 and leaves DL-1 and RB-301 without inputs | |
| Committed, but only from Phase 9 | Build now, gitignore through M2–M6, commit in the release PR | |

**User's choice:** Committed
**Notes:** The two documents were not equally authoritative — SPEC-08 §2 and `.gitignore` were
both *edited* by the W5 resolution; the WBS card was simply never revisited. → CONTEXT D-01.

### Q2 — How is the committed export kept honest against drift?

| Option | Description | Selected |
|--------|-------------|----------|
| CI diff-check, D-20 pattern (Recommended) | Job 3 regenerates then `git diff --exit-code exports/`; mirrors the seed diff-check; no new job | ✓ |
| Schema contract test only | AD-050 minimum on fixtures; catches schema breaks but not value drift | |
| Both | Contract test in job 2 plus diff-check in job 3 | |

**User's choice:** CI diff-check, D-20 pattern
**Notes:** → CONTEXT D-02.

### Q3 — The a€-in-committed-exports interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Record it, act in Phase 6 (Recommended) | Header comment + RISK_REGISTER entry so D-26's leak-scan scope is revisited before the M4 flip | ✓ |
| Widen the leak scan now | Extend `leak_scan.py` to `exports/*.csv` in Phase 3 | |
| Nothing — Phase 6 owns it | Rely on the existing Phase 1 deferred item | |

**User's choice:** Record it, act in Phase 6
**Notes:** Raised by Claude as a consequence of Q1 — committing the export means Layer R a€ rows
enter the history of a repo that goes public at M3, and Phase 1's D-26 deliberately scoped a€
in `exports/` out of the leak scan. Widening now was rejected because the patterns cannot be
tuned against data that does not exist. → CONTEXT D-05.

### Q4 — Export registry: declared whole or grown per phase?

| Option | Description | Selected |
|--------|-------------|----------|
| Grow-as-you-go (Recommended) | One entry now; each producing phase adds its own (D-03 precedent) | ✓ |
| Declared whole, five inert | All six registered with `producing_phase` and a NOT-YET status (D-17/D-25 precedent) | |
| Declared whole, schemas too | All six with authored column contracts | |

**User's choice:** Grow-as-you-go
**Notes:** → CONTEXT D-03.

### Q5 — Float discipline for the committed export

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit fixed precision (Recommended) | Pin `float_format` at 6 decimals, matching the simulator CSVs | ✓ |
| pandas default repr | Lossless but a library detail; a version bump can rewrite every line | |
| Round to 2 decimals | Currency-shaped but discards the 1e-6 AD-042 headroom | |

**User's choice:** Explicit fixed precision
**Notes:** → CONTEXT D-04.

---

## Contract-freeze enforcement

### Q1 — How is the `fct_mmm_input` column contract enforced?

| Option | Description | Selected |
|--------|-------------|----------|
| dbt enforced contract (Recommended) | `config(contract={enforced: true})` with full columns/data_type; build-time refusal | ✓ |
| pytest against the built mart | Python test on column set/order/dtypes, settings.yaml-derived | |
| Both | dbt contract plus the BP-G-03 pytest extended to the full column set | |
| Written rule only | Keep the ROADMAP rollback text; reviewers catch drift | |

**User's choice:** dbt enforced contract
**Notes:** Flagged at ask time that dbt-duckdb's constraint-support level must be verified by
research before the plan commits; the pytest form is the named fallback. → CONTEXT D-06.

### Q2 — Does the mart-only rule become a standing guard test?

| Option | Description | Selected |
|--------|-------------|----------|
| Guard test, scoped (Recommended) | Fifth guard: no CSV/parquet in model/decide, no duckdb outside db.py, report limited to exports/ | ✓ |
| Guard test, model + decide only | T-204's literal scope, no `report/` clause | |
| Keep the grep | Verify once at T-204, record as PR evidence | |

**User's choice:** Guard test, scoped
**Notes:** The `report/` carve-out matters — 03_MODULES §10 gives `report/` legitimate access to
`exports/`, so a repo-wide ban would be wrong. → CONTEXT D-09.

### Q3 — Which artifact is normative for the mart column contract?

| Option | Description | Selected |
|--------|-------------|----------|
| dbt yml normative; db.py derives (Recommended) | Single home in the yml; db.py reads from it; MODULE_CONTRACTS cites by path | ✓ |
| dbt yml normative; db.py restates + tested | BP-G-03's tested-duplication pattern | |
| settings.yaml normative | Promote the column contract into settings.yaml | |

**User's choice:** dbt yml normative; db.py derives
**Notes:** settings.yaml was rejected in part because D-25 authored it whole with five declared
blocks under `extra='forbid'`. → CONTEXT D-08.

### Q4 — Do the other two marts get enforced contracts?

| Option | Description | Selected |
|--------|-------------|----------|
| All three (Recommended) | All three are db.py-exposed contract surfaces | ✓ |
| `fct_mmm_input` only | Freeze exactly what AD-030 names | |
| `fct_mmm_input` + `dim_layer` | Leave `fct_platform_reported` open until Phase 8 | |

**User's choice:** All three
**Notes:** → CONTEXT D-07.

### Q5 — How does `db.py` report contract violations?

| Option | Description | Selected |
|--------|-------------|----------|
| Collect all, one raise (Recommended) | Full list: assertion, layer, offending weeks/columns | ✓ |
| Fail fast on first violation | Simpler; worse when one join bug trips four assertions | |
| You decide | Leave the shape to planner/executor | |

**User's choice:** Collect all, one raise
**Notes:** Framed against Phase 5's VR-310 debug ladder, which is what will actually read this
error text. → CONTEXT D-10.

---

## Test rigor beyond WBS

### Q1 — How do we prove duplicate grain keys actually fail?

| Option | Description | Selected |
|--------|-------------|----------|
| Real negative dbt test (Recommended) | Poisoned fixture; assert `dbt build` exits non-zero on the `unique` test | ✓ |
| Python-side assertion only | T-202's literal deferral; leaves SC-4's claim untested | |
| Both | Negative dbt test plus accessor-boundary assertion | |

**User's choice:** Real negative dbt test
**Notes:** The gap Claude surfaced: T-202 defers the poisoned-fixture test to "Python-side
export tests", but export tests never invoke dbt, so nothing would demonstrate the failure.
Requires source paths parameterized by a dbt var in T-201. → CONTEXT D-11.

### Q2 — How broad is the AD-042 reconciliation?

| Option | Description | Selected |
|--------|-------------|----------|
| All three Layer P scenarios (Recommended) | Parameterize over P-SA/P-SB/P-SC; catches dropped and mislabeled layers | ✓ |
| P-SA only, per spec | Literal SPEC-03 §4 compliance | |
| All three, plus spine and spend totals | Adds the pivot-integrity check | |

**User's choice:** All three Layer P scenarios
**Notes:** Noted at ask time that this tightens rather than widens a gate, so standing rule 4's
ADR requirement does not apply. → CONTEXT D-12.

### Q3 — How is `dim_layer.channels_present` derived?

| Option | Description | Selected |
|--------|-------------|----------|
| Source-row presence; model must read it (Recommended) | Present = has rows in staging; model iterates `channels_present`, not the 7 columns | ✓ |
| Nonzero-spend derivation | Present = total spend > 0; risks disagreeing with the Layer R manifest | |
| Declared per layer in config | Explicit declaration in settings.yaml / manifest | |

**User's choice:** Source-row presence; model must read it
**Notes:** Grounded in a data check run during the discussion: all three Layer P scenarios carry
the same six channels and no `other`, so `spend_other` is structurally 0.0 on every Layer P row
— while S-C's `display_video` has 92,193 in spend and zero true effect by VR-304 design. The two
must stay distinguishable or MD-040's channel-agnostic priors fit a β for a channel with no
data. → CONTEXT D-13.

### Q4 — Does the `channels_present` contract get a test?

| Option | Description | Selected |
|--------|-------------|----------|
| Singular test both directions (Recommended) | Listed channels have rows; unlisted `spend_*` columns are 0.0 everywhere | ✓ |
| One direction only | Just the absent-channels-are-zero half | |
| Documented only | Rely on the enforced column contract and AD-041 | |

**User's choice:** Singular test both directions
**Notes:** → CONTEXT D-14.

### Q5 — Where does the gapless-spine week spine come from?

| Option | Description | Selected |
|--------|-------------|----------|
| From the seed via `stg_calendar_weekly` (Recommended) | Anti-join against the seed's weeks; no SQL date arithmetic | ✓ |
| `generate_series` per Guide §8.3 | Literal guide instruction; independent of the seed | |
| Both, cross-checked | Seed anti-join plus a seed-self-gaplessness assertion | |

**User's choice:** From the seed via `stg_calendar_weekly`
**Notes:** A deliberate departure from Guide §8.3, consistent with Guide §8.2's "no
recomputation of windows in SQL ever" and with AD-020's one-calendar rule. Needs a line in the
PR so it does not read as an oversight. → CONTEXT D-15.

### Q6 — Which reading does the AD-043 test implement?

| Option | Description | Selected |
|--------|-------------|----------|
| Strict — no suffix anywhere (Recommended) | Neither `_eur` nor `_aeur` in any staging or mart output column | ✓ |
| Mixing only, per AD-001 literal | Fail only when one model carries both | |
| Strict on staging, mixing on marts | Split the two documents' readings | |

**User's choice:** Strict — no suffix anywhere
**Notes:** T-202 AC-2 and SPEC-03 AD-001 state AD-043 differently; the mixing form passes a mart
that forgot the rename entirely. Stricter than AD-001 as written, so it needs a PR note.
→ CONTEXT D-16.

---

## M2 budget & sequencing

### Q1 — What does the effort tripwire measure for Phase 3?

| Option | Description | Selected |
|--------|-------------|----------|
| Named split, 1 d / 1 d (Recommended) | Each phase gets its own 2× trip point; recorded in BUILD_LOG | ✓ |
| Pooled — M2 trips at 4 d combined | Faithful to the Charter table; no signal until both phases end | |
| Phase 3 named at 0.75 d | Weighted toward Phase 4's larger task count and the open g++ risk | |

**User's choice:** Named split, 1 d / 1 d
**Notes:** Claude surfaced that Phase 3 had no budget of its own — the ROADMAP line reads
"Shares M2's 2 d with Phase 4", leaving the per-phase tripwire with nothing to measure.
→ CONTEXT D-17.

### Q2 — How does the added test scope distribute across the plans?

| Option | Description | Selected |
|--------|-------------|----------|
| With the thing it tests (Recommended) | Each test ships in the plan that creates its target; T-201 parameterizes source paths | ✓ |
| Trailing hardening plan | WBS minimum first, all extra tests in one final plan | |
| Split by language | dbt tests with models; Python scaffold batched at the end | |

**User's choice:** With the thing it tests
**Notes:** → CONTEXT D-18.

### Q3 — What happens between 1 d (budget) and 2 d (tripwire)?

| Option | Description | Selected |
|--------|-------------|----------|
| Named shed order, flag each shed (Recommended) | Pre-ranked discretionary items; BUILD_LOG flag before each shed; never-shed list | ✓ |
| No shedding — flag and continue | Phase 2's D-03 stance; stop and ADR at 2 d | |
| Flag at 1 d and ask | Executor checkpoints to the human at the budget line | |

**User's choice:** Named shed order, flag each shed
**Notes:** All items added in this discussion sit beyond the WBS minimum, so shedding one is not
a spec deviation. → CONTEXT D-19.

---

## Layer R staging branch timing

| Option | Description | Selected |
|--------|-------------|----------|
| Inert + fixture-exercised (Recommended) | Write the guarded union per BP-D-05, then exercise it with a fake `data/real_anon/`-shaped fixture | ✓ |
| Inert, unexercised | The literal blueprint default; first execution happens in M4 | |
| Defer the branch to Phase 6 | No dead code, but overrides BP-D-05 and needs an ADR | |

**User's choice:** Inert + fixture-exercised
**Notes:** Reuses the source-path parameterization D-11 already requires. Deferring would have
needed an ADR, since ADR-000 D-2 ratified BP-D-05. → CONTEXT D-20.

---

## `make transform` guard retirement

| Option | Description | Selected |
|--------|-------------|----------|
| Remove it (Recommended) | `make transform` = `uv run dbt build`; dbt fails loudly; repo-layout test guards the file's existence | ✓ |
| Invert it to a hard failure | Keep the conditional, exit non-zero on missing project | |
| Keep as-is | Zero churn; leaves a path where job 3 passes without building | |

**User's choice:** Remove it
**Notes:** The D-17 conditional existed so job 3 could pass by running rather than being skipped
(D-16); once a dbt project exists that purpose is spent. → CONTEXT D-21.

---

## `fct_platform_reported` scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full Layer P, extension pre-declared (Recommended) | conversions + conv_value + impressions frozen; Layer R `clicks` pre-declared as a planned M4 amendment | ✓ |
| Full Layer P, no pre-declaration | Freeze flat; `clicks` goes through the normal contract-break path | |
| Minimal — conversions and value only | Smallest frozen surface; drops `impressions` | |

**User's choice:** Full Layer P, extension pre-declared
**Notes:** Its Layer P content is fully determined by SIM-060/061's committed columns; only the
Layer R side involves guesswork. → CONTEXT D-24.

---

## Warehouse path portability

### Q1 — Does CI job 3 gain a Windows leg?

| Option | Description | Selected |
|--------|-------------|----------|
| Matrix it, D-21 pattern (Recommended) | Add `windows-latest` with the choco make step; job name stays `dbt`, so EB-060's six hold | ✓ |
| Ubuntu only, verify locally | Saves Windows minutes; nothing records that it works there | |
| Ubuntu only, plus a path-location test | Cross-platform coverage via job 2's matrix without a second dbt build | |

**User's choice:** Matrix it, D-21 pattern
**Notes:** Confirmed by reading `ci.yml` during the discussion that job 3 is currently
ubuntu-only while the dev machine is Windows. → CONTEXT D-22.

### Q2 — How is the warehouse path specified and verified?

| Option | Description | Selected |
|--------|-------------|----------|
| Guide's relative form, pinned invocation, asserted (Recommended) | Keep §8.1's relative path, always pass `--project-dir`/`--profiles-dir`, assert the built file matches `settings.paths.warehouse` | ✓ |
| Absolute path via env var | Immune to cwd questions; adds a third env var and breaks bare `dbt build` | |
| Relative form, no assertion | Trust §8.1 as written | |

**User's choice:** Guide's relative form, pinned invocation, asserted
**Notes:** Guide §8.1's claim that `path:` resolves relative to the profile dir is flagged as
**unconfirmed** and handed to research. → CONTEXT D-23.

---

## Claude's Discretion

- Internal structure of the export registry dict and the exact float-format directive.
- Concrete form of the poisoned-fixture harness — source-path parameterization, tmp warehouse
  location, non-zero-exit assertion.
- Wording of the `RISK_REGISTER.md` entry and the `export_marts.py` header comment.
- Exact column set and shape of the fake Layer R fixture, beyond the SPEC-02 §5.2 taxonomy and
  BP-D-03 column names.
- Whether the `channels_present` both-directions check is one singular test or two, and its
  failure-message format.
- How `db.py` derives its column set from the dbt yml — yml parse, generated constant, or dbt
  artifact read.
- Where the BP-G-03 taxonomy-equality pytest lives; whether `dim_layer` and
  `fct_platform_reported` are also exported; the committed export's row ordering.

## Deferred Ideas

- **Revisit D-26's leak-scan scope for committed `exports/*.csv`** — Phase 6, before the
  `layer_r_present` flip. Tracked via a `RISK_REGISTER.md` entry rather than memory.
- **`dbt docs generate` lineage graph as a portfolio artifact** — Phase 9. Raised during the
  discussion and deliberately not decided here; Charter O-5 means it would have to be a
  committed static image under `docs/assets/`, not a served docs site.
- **`clicks` joins `fct_platform_reported`** — Phase 6, as D-24's pre-declared extension.
