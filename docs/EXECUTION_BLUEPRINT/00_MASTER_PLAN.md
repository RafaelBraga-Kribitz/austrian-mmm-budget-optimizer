# 00 — MASTER PLAN (Execution Blueprint, AMBO)

**Status:** Blueprint v1.0 — 2026-07-19
**Authority:** This blueprint is subordinate to `PROJECT_CHARTER.md` and `docs/SPEC-01..09`.
It adds no new requirements; it decomposes existing ones into executable work and
records proposed resolutions for every ambiguity found (§5). Where this blueprint and a
SPEC conflict, the SPEC wins and the conflict is a blueprint bug — file it in
`docs/BUILD_LOG.md` and fix the blueprint.

**Audience:** any competent coding agent (Claude Opus/Sonnet, GPT-5, Codex, Gemini) or
human engineer. After reading this document and the file it points you to, you should
never need to ask "what do I build next", "how should it behave", or "when is it done".

---

## 1. What this project is (one paragraph)

AMBO builds a Bayesian Marketing Mix Model in raw PyMC for a real anonymized Austrian
advertiser, **proves the model first on synthetic data with disclosed ground truth**
(Layer P), only then fits real data (Layer R) under priors frozen before fitting, and
finishes with a constrained budget optimizer and platform-vs-MMM attribution-gap
analysis (Layer D). The git history itself is a deliverable: recovery-before-reality
and freeze-before-fit are enforced by CI scripts over git ancestry
(SPEC-09 §5). Read `PROJECT_CHARTER.md` §1–§3 before anything else.

## 2. Repository inventory — what exists vs. what this blueprint creates work for

| Artifact class | Status on 2026-07-19 | Consequence |
|---|---|---|
| Project Charter | ✅ `PROJECT_CHARTER.md` v1.0 | Authoritative; unchanged by blueprint |
| Agent playbook | ✅ `AGENTS.md` | Authoritative working rules (A-1…A-9, T-1…T-9) |
| Specifications | ✅ `docs/SPEC-01..09` | Complete; gaps and ambiguities enumerated in §5 below |
| Governance | ✅ SPEC-09 (mechanisms specified) | Scripts do not exist yet — tasks T-008, T-408, T-409 |
| Engineering conventions | ✅ SPEC-08 | Toolchain not instantiated — Phase 0 |
| **Git repository** | ❌ **not initialized** | T-001 is the very first action; layer-order proof depends on history existing from day one |
| Repository skeleton | ❌ absent (no `src/`, `config/`, `tests/`, `Makefile`, `pyproject.toml`) | Phase 0 (T-001…T-012) creates it exactly per SPEC-08 §2 |
| Module stubs | ❌ absent | Created per module contracts in [03_MODULES.md](03_MODULES.md) |
| Data / models / reports | ❌ absent (by design — nothing is implemented) | Phases 1–8 |

## 3. External-dependency clarification (read before planning)

The tasking that commissioned this blueprint mentions an **ENTSO-E API token**. AMBO
has **no ENTSO-E dependency and no live API at all** — SPEC-08 EB-070 asserts zero
network access anywhere; Charter O-7 forbids automated refresh. The statement is a
template artifact from a sibling (energy) project. The structurally equivalent
external blocker in AMBO is:

> **The private agency data drop + written permission (SPEC-02 §1–§2), needed at M4.**

Everything the tasking says about "API-blocked vs. non-API work" maps onto
**drop-blocked vs. drop-independent work**:

- **Drop-blocked (cannot finish without the human + private data):** T-507, T-508,
  T-510 (permission, intake execution, elicitation content + freeze), all Layer R
  fits (Phase 6), Layer R decision runs (T-705), Layer R reporting content.
- **Drop-independent (do these while waiting):** all of Phases 0–4 (foundation,
  simulator, warehouse, model, recovery suite), the entire intake *codebase* against
  synthetic lookalike fixtures (T-501…T-506), the entire decision layer developed and
  gated on Layer P (T-701…T-704), and all reporting infrastructure (T-801, T-802
  chart code on synthetic inputs). See [04_DEPENDENCIES.md §6](04_DEPENDENCIES.md).

If permission fails: Charter §7 degradation path, decided by ADR at end of M4 —
pre-planned in [12_RISK_REGISTER.md](12_RISK_REGISTER.md) RK-M4-1.

## 4. How to use this blueprint (execution protocol)

1. **Find your task.** Open [02_WBS.md](02_WBS.md). Tasks are ordered; the first task
   whose status is open and whose dependencies (listed per task, graphed in
   [04_DEPENDENCIES.md](04_DEPENDENCIES.md)) are complete is your task. Parallel
   tracks are marked.
2. **Check Definition of Ready** — global template in
   [11_ACCEPTANCE_CRITERIA.md §2](11_ACCEPTANCE_CRITERIA.md) plus the task's own
   prerequisites. If not ready, do the blocking task instead.
3. **Read the module contract** for every file you touch:
   [03_MODULES.md](03_MODULES.md). Read the matching deep-dive in
   [05_IMPLEMENTATION_GUIDES.md](05_IMPLEMENTATION_GUIDES.md) if the task links one.
4. **Implement** under [07_QUALITY_STANDARDS.md](07_QUALITY_STANDARDS.md),
   [08_PATTERNS.md](08_PATTERNS.md), and [09_ANTI_PATTERNS.md](09_ANTI_PATTERNS.md).
   Tests land in the same commit as the requirement (AGENTS W-1); docstrings carry
   `Implements: <REQ-IDs>`.
5. **Validate** using the task's validation method and the relevant gates in
   [10_VALIDATION_GATES.md](10_VALIDATION_GATES.md); run the AGENTS §5 verification
   protocol before claiming any milestone.
6. **Close** against the task's acceptance criteria + global Definition of Done
   ([11_ACCEPTANCE_CRITERIA.md §3](11_ACCEPTANCE_CRITERIA.md)). Tick the milestone
   checklist ([06_CHECKLISTS.md](06_CHECKLISTS.md)) in the PR. One milestone = one PR
   (AGENTS A-9); within a milestone, commit per task with conventional commits + REQ IDs.
7. **Log** a line in `docs/BUILD_LOG.md` (append-only) when a task or milestone closes.

**Stop-and-ask triggers** are exactly AGENTS §2 (permission/private-data matters,
elicitation content, unexplainable gate failures after two attempts, sampler
pathologies after the full MD-073 ladder, degradation decision, Power BI, golden-band
regeneration). Everything else: decide per this blueprint and proceed.

## 5. Blueprint decisions (BP-D) — resolved ambiguities

Every place a SPEC left interpretation room, the blueprint proposes exactly one
resolution. These are **proposals with defaults**: implement the default unless the
human overrides; items marked *(ADR)* must be recorded as an ADR when exercised
because they touch spec wording. Full rationale per decision inline where used
(WBS/guides); index here.

| ID | Ambiguity | Resolved default |
|----|-----------|------------------|
| BP-D-01 | ENTSO-E mention in tasking | Inapplicable; external blocker = agency drop (§3) |
| BP-D-02 | SIM-004 lists `impressions`/`platform_conversions` for Layer P but SPEC-01 defines no generating rule for them | Per-channel CPM constants in scenario YAML; `impressions = round(spend/cpm×1000)`; offline channels NULL. `platform_conversions = round(platform_revenue/AOV_t)`; offline NULL. Parameters recorded in `truth.json` |
| BP-D-03 | Layer P columns (`spend_eur`, `platform_revenue_eur`, no `clicks`) vs Layer R columns (`spend_aeur`, `platform_conv_value_aeur`, `clicks`) must union in one staging model, while AD-001 demands unit-suffix segregation | Staging renames to unit-neutral names (`spend`, `revenue`, `platform_conv_value`, `clicks` with NULL for P); monetary unit lives in `dim_layer.monetary_unit`; AD-043 test asserts no model exposes both `_eur` and `_aeur` suffixed columns |
| BP-D-04 | Is the `other` channel modeled? Reallocatable? | Modeled if present with ≥1% spend (weak prior); **excluded from optimizer reallocation** (fixed at historical mean, like `search_brand`) — an undefined bucket cannot be a recommendation. *(ADR-002 at intake)* |
| BP-D-05 | dbt must build in CI from M0 but `data/real_anon/` doesn't exist until M4 | dbt var `layer_r_present: false`; staging conditionally unions Layer R sources; flipped to `true` in the M4 PR. AD-044 implemented via a public seed `dbt/seeds/intake_channels.csv` generated by intake stage-2 from the manifest |
| BP-D-06 | Posterior artifact naming; do sensitivity/holdout posteriors get committed? | `data/posteriors/P-SA.parquet`, `P-SB.parquet`, `P-SC.parquet`, `R.parquet`; variants `R__flat.parquet`, `R__nopromo.parquet`, `R__loco-<channel>.parquet`, `P-SB__flat.parquet` (glob `R*` in GB-501 catches all R variants). Holdout outputs are committed as summary CSVs under `reports/model/holdout_<layer>.csv`, not posteriors |
| BP-D-07 | "The commit freezing priors" is not operationally defined | Freeze = the single commit adding both `config/priors_real.yaml` and the final `docs/PRIOR_ELICITATION.md`, annotated git tag `prior-freeze-v1`; `generate_ssot.py` reads the tag's commit hash into `prior_freeze_commit`; `check_layer_order.py` verifies ancestry + no post-tag modification of either file |
| BP-D-08 | SSOT key `roas_<channel>_hdi90` is one key for an interval | Two keys: `roas_<channel>_hdi90_lo`, `roas_<channel>_hdi90_hi`; same split for `expected_gain_pct` bounds |
| BP-D-09 | "8 bursts/year", "10 promo weeks/year" on a 78-week scenario (S-C) | Schedule per ISO calendar year covered; partial years get counts pro-rated by covered weeks, rounded half-up; the resulting explicit week lists are authored in scenario YAML, which is authoritative (SIM-002) |
| BP-D-10 | Who produces `dbt/seeds/season_windows.csv` (AD-020)? | `scripts/generate_season_windows.py` (uses `holidays` + SPEC-01 §2.1 ISO-week rules) generates it once for ISO years 2019–2027 (covers any plausible Layer R window); committed; simulator and dbt both read the committed CSV; regeneration is idempotent and diff-checked in CI |
| BP-D-11 | AG-042 (counts × k_spend) preserves **real** CPC/CPM exactly (spend and clicks share the factor) — a residual fingerprinting surface | Default: follow spec, and document the preservation explicitly in LIMITATIONS §3. Recommendation to the human at M4: introduce a third secret factor `k_cnt` for counts (keeps CTR and internal consistency, masks CPC/CPM). *(ADR-003 if adopted — spec deviation)* |
| BP-D-12 | DC-601 "±€500/week" in masked Layer R units | ±a€500 as written; caption states masked units; note ratio-invariance in LIMITATIONS |
| BP-D-13 | Git-ancestry CI checks need history | The `layer-order` and `leak-scan` CI jobs check out with `fetch-depth: 0`; `check_layer_order.py` exits green trivially while no Layer R artifacts exist |
| BP-D-14 | Windows dev vs Makefile-canonical interface | GNU Make via Git Bash required for local dev (documented in README §8 dev note); CI runs `ubuntu-latest`; all Python paths via `pathlib`; Makefile recipes POSIX-sh only |
| BP-D-15 | Optimizer total budget B not defined per layer | B = mean total weekly spend over that layer's full window; DC-401 uses S-A's/S-B's own mean; DC-205 multipliers apply to Layer R's mean |
| BP-D-16 | DC-401 mixes two adstock parameterizations | Truth-side evaluation uses SPEC-01 raw recursion steady state `x/(1−λ)`; posterior-side uses the model's normalized steady state `x` (DC-201). Comparison is on allocations and contributions only, never parameters |
| BP-D-17 | CI smoke-fit 15-min budget is tight for PyMC compile | Cache `uv` env and pytensor compiledir in Actions cache; smoke test carries `@pytest.mark.timeout(900)`; see guide [05 §9](05_IMPLEMENTATION_GUIDES.md) |
| BP-D-18 | Sampling budget for holdout/sensitivity refits unstated | Full MD-050 budget for every reported fit (spec: "full budget for all reported fits"); compute inventory ~14 full fits, est. 3–8 h total wall time — planned in [04 §7](04_DEPENDENCIES.md) |
| BP-D-19 | `dim_layer.channels_present` type | Comma-joined string in canonical taxonomy order (BI-friendly, dbt-testable) |
| BP-D-20 | `make all` assumes fits exist — behavior when missing | Each non-fit target fails fast with the exact `make fit-*` command to run; never auto-triggers sampling (EB-050 cost control) |

## 6. Specification-gap index

Gaps needing *content authoring* (not just interpretation), all scheduled as WBS tasks:

| Gap | Where resolved |
|-----|----------------|
| Explicit promo-week lists and burst schedules per scenario (SPEC-01 §2.1/§3 gives rules, not weeks) | T-101 authors them in `config/scenarios/*.yaml` per BP-D-09 |
| Impressions/conversions DGP for Layer P | T-106 per BP-D-02 |
| `season_windows.csv` content | T-011 per BP-D-10 |
| ADR template file | T-012 (copy sibling-repo template per GB-201) |
| `docs/DATA_PERMISSION.md` content | T-507 (human; structure specified in WBS) |
| `docs/PRIOR_ELICITATION.md` skeleton with MD-060 field structure | T-509 (agent drafts structure; human owns content, AGENTS §2.2) |
| README both framing variants (RB §6/§6.1) | T-804 (both drafted; one activated) |
| SSOT whitelist file with per-entry justifications (GB-303) | T-408 creates the mechanism; entries added as reports are written |
| pymc-marketing prior/transform mapping documentation (VR-602 "as closely as API allows") | T-405 produces `reports/recovery/crosscheck_mapping.md` |

Contradictions found: **none hard.** Two soft tensions, both resolved by blueprint
decisions: the unit-suffix union tension (BP-D-03) and the dbt-before-M4 tension
(BP-D-05). The deliberate simulator/model parameterization mismatch (MD-020) is a
design feature, not a contradiction — do not "fix" it.

## 7. Document map of this blueprint

| Doc | Contents | Read when |
|-----|----------|-----------|
| [01_PHASES.md](01_PHASES.md) | 9 phases, entry/exit criteria, deliverables, rollback | Planning any phase |
| [02_WBS.md](02_WBS.md) | 46 tasks, one coding session each, full task cards | Always — the work queue |
| [03_MODULES.md](03_MODULES.md) | Contracts per module/class/function | Before touching any file |
| [04_DEPENDENCIES.md](04_DEPENDENCIES.md) | Graphs, critical path, parallel/blocked/risky work, compute plan | Sequencing decisions |
| [05_IMPLEMENTATION_GUIDES.md](05_IMPLEMENTATION_GUIDES.md) | Deep dives: transforms, elicitation math, optimizer, leak scan, git checks, dbt harmonization, CI smoke | When a task links it |
| [06_CHECKLISTS.md](06_CHECKLISTS.md) | Per-milestone implementation/review/QA/science/docs/hygiene/release checklists | PR time |
| [07_QUALITY_STANDARDS.md](07_QUALITY_STANDARDS.md) | Measurable thresholds + full coding standards | Always |
| [08_PATTERNS.md](08_PATTERNS.md) | Which design pattern goes where | Design time |
| [09_ANTI_PATTERNS.md](09_ANTI_PATTERNS.md) | Forbidden implementations, with the failure each causes | Design + review time |
| [10_VALIDATION_GATES.md](10_VALIDATION_GATES.md) | Every gate: trigger, runner, evidence, failure protocol | Milestone exits |
| [11_ACCEPTANCE_CRITERIA.md](11_ACCEPTANCE_CRITERIA.md) | Global DoR/DoD, DL-1..10 expanded to measurable criteria | Task close |
| [12_RISK_REGISTER.md](12_RISK_REGISTER.md) | Charter risks expanded per milestone + blueprint-found risks | Phase entry |
| [13_TRACEABILITY_MATRIX.md](13_TRACEABILITY_MATRIX.md) | Task ↔ REQ ↔ Charter ↔ deliverable ↔ artifact | Review + audit |

## 8. Ground rules restated (the ones agents break most)

- **Never** implement before T-001 (git init) is done — history is the argument.
- **Never** let `src/ambo/simulate/` and `src/ambo/model/` import each other (T-3).
- **Never** commit anything derived from the private drop except `data/real_anon/`
  outputs of stage 2 (A-4). When in doubt: stop, ask.
- **Never** report a number without its HDI (A-7) or outside SSOT (A-8).
- **Never** widen a gate without an ADR naming the suspected structural cause (VR-310).
- **Never** rewrite git history (EB-082) — not even to fix a mistake; escalate.
