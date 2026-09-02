# Phase 2: Ground-Truth Simulator - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the disclosed data-generating process (DGP) for the fictional Austrian advertiser
"AlpenTrek GmbH" (Graz-based outdoor-gear e-tailer), exactly as SPEC-01 defines it, so that
"the model recovered ROAS" becomes a checkable claim rather than a plot.

Deliverable: `src/ambo/simulate/` producing, per scenario (S-A, S-B, S-C),
`data/synthetic/<scenario>/{media_weekly.csv, outcome_weekly.csv, truth.json}` — deterministic,
byte-identical across runs, with every SIM-070…075 gate green via `make simulate && make
validate-sim`.

This phase owns no Charter `REQ-*` requirement outright (contributes to
REQ-q1-truth-recovery and REQ-grain-and-windows) — it is instrumental to Phase 5's recovery
argument, not a standalone deliverable to a marketing leader.

**Not in scope:** the model (`ambo/model/`, Phase 4), the warehouse (Phase 3), anything that
reads `season_windows.csv` besides the simulator itself (dbt reads it independently in Phase
3 — no shared code, only shared config per SIM-003/AD-020).

</domain>

<decisions>
## Implementation Decisions

### Promo/burst week authoring (T-101)
- **D-01:** User delegates the exact ISO promo/burst week choices fully to the implementer.
  No draft-then-approve step — only escalate if a SIM-030/031 gate fails.
- **D-02:** For the *unanchored* placements (the 5 "spread" promo weeks/year and the
  non-Advent/non-Schulbeginn burst starts for print/radio), write a small one-off placement
  script (not shipped code — a throwaway authoring aid) that deterministically proposes
  non-overlapping placements from the scenario seed. Copy its output into the scenario YAML
  as frozen constants. This is more auditable than freehand picks while staying consistent
  with the Guide §1.1 requirement that runtime randomness stay limited to spend-level noise
  (the script's output is authored-once, not computed at simulate-time).
  - Anchored weeks (Black Friday, 2 Advent promo weeks, Schulbeginn-adjacent bursts,
    Advent-anchored bursts) are still placed directly per their fixed rule — no script needed
    for those.

### Test rigor beyond WBS minimum
- **D-03:** Add property-based tests (e.g. `hypothesis`) for the simulator's own adstock and
  Hill implementations (`simulate/dgp.py`), on top of the WBS-mandated point tests
  (closed-form limit, impulse test, `Hill(K)=0.5` exact, SIM-031 spend stats). User accepted
  the added effort-budget risk explicitly — this is real scope beyond T-104's minimum, not
  "Claude's discretion."
  - Suggested properties (planner/executor to finalize): adstock output bounded by
    `[0, x/(1-λ)]` for any nonnegative spend series; adstock monotonically non-decreasing in
    any single spend value holding others fixed; Hill output in `[0, 1]` and monotonically
    non-decreasing in adstocked spend for `s_c > 0`.
  - Effort-budget awareness: Phase 2's budget is 1.5 d (>2× ⇒ stop + ADR per Charter §5). If
    property-based tests push total effort near 2×, flag it — don't silently absorb the
    overage.

### AlpenTrek narrative flavor
- **D-04:** Keep all Phase 2 artifacts (BUILD_LOG entry, docstrings, `truth.json`) purely
  mechanical — formulas, gates, determinism evidence. No brand-voice/story text. Narrative
  framing of "AlpenTrek GmbH" is explicitly Phase 9's job (README, exec summary, dashboard).

### Claude's Discretion
- Exact ISO week numbers for all promo/burst schedules across S-A/S-B/S-C (per D-01/D-02),
  as long as SIM-030 (collinearity anchoring for S-B/S-C) and SIM-031 (spend-pattern
  statistics) hold.
- Internal structure of the one-off placement script (D-02) — it is not a module contract
  deliverable and has no WBS task of its own; it only needs to produce placements that satisfy
  §3's counts and the S-B/S-C anchoring rule, then get discarded or kept as a dev-only
  utility outside `src/`.
- Which specific `hypothesis` properties to encode for D-03, beyond the three suggested above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Governing spec (primary — read in full before writing any simulate/ code)
- `docs/SPEC-01_ground_truth_simulator.md` — the exact DGP: baseline demand (§2.1), media
  effect / adstock / Hill (§2.2), revenue assembly (§2.3), spend patterns (§3), true media
  parameters table (§4), scenarios S-A/S-B/S-C (§5), platform-bias formulas (§6), SIM-070…075
  gates (§7), `truth.json` derived quantities incl. the already-resolved response-curve grid
  question (§8). This is the authoritative source; the WBS/Guide below operationalize it.

### Task breakdown and implementation guidance
- `docs/EXECUTION_BLUEPRINT/02_WBS.md` T-101…T-109 — task-by-task objectives, prerequisites,
  dependencies, implementation notes, validation, and acceptance criteria for every simulator
  module.
- `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` §1 (§1.1–§1.5) — deep-dive math and
  authoring guidance: scenario YAML authoring rules (incl. promo/burst counts), season-window
  rules (already resolved, see Prior Decisions below), spend-pattern draw order and RNG
  discipline, adstock/Hill closed-form + impulse tests, and the exact truth-derivation
  formulas (analytic marginal ROAS, response-curve sampling, byte-stable JSON serialization).
- `docs/EXECUTION_BLUEPRINT/03_MODULES.md` §2 (`ambo/simulate/`) — module-by-module function
  signatures and contracts: `config.py`, `spend_patterns.py`, `dgp.py`, `platform_bias.py`,
  `truth.py`, CLI. Also the forbidden-edges list (§ import graph) — `simulate` imports nothing
  from `ambo` except `common`.
- `docs/EXECUTION_BLUEPRINT/01_PHASES.md` P1 section — phase-level goals, entry/exit criteria,
  rollback condition (do not tune SPEC-01 §4 values on a plausibility failure — check the
  implementation first).

### Quality gates and checklists
- `docs/EXECUTION_BLUEPRINT/10_VALIDATION_GATES.md` §3 (G-DATA-P) — the SIM-070…075 +
  BP-G-02 gate table with exact pass/evidence criteria.
- `docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md` M1 section — the PR checklist (implementation,
  code review, QA, scientific validation rows) this phase's PR must tick with evidence.
- `docs/EXECUTION_BLUEPRINT/09_ANTI_PATTERNS.md` A-1 (simulator–model incest — the single most
  important guard for this phase), A-13 (speculative generality — relevant to the D-02
  placement script: keep it a throwaway aid, not a shipped abstraction), A-14 (premature
  optimization — do not vectorize the adstock loop cleverly at the cost of the causality
  property, per Guide §1.4).
- `docs/MODULE_CONTRACTS.md` (forbidden edges section) — `simulate ↔ model` import guard
  (SIM-003), enforced by `tests/unit/test_import_independence.py` from Phase 1.

### Shared config (not shared code)
- `dbt/seeds/season_windows.csv` — the committed calendar seed (AD-020) the simulator must
  read, never recompute. Generated in Phase 1 (`01-06-PLAN.md`); advent read as exactly 4
  flagged weeks ending at the Dec-24 week inclusive, schulbeginn as the second Monday of
  September — both already-settled readings (see Prior Decisions).

### Requirements traceability
- `.planning/REQUIREMENTS.md` — REQ-q1-truth-recovery and REQ-grain-and-windows entries
  (contributing, not owning, for this phase).
- `.planning/intel/constraints.md` §SIM-001…004, §SIM-060/061, §SIM-070…075 — condensed
  constraint text if a quick reference is faster than the full SPEC.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dbt/seeds/season_windows.csv` (Phase 1) — the season-window calendar. The simulator reads
  this file directly; it must not reimplement or recompute advent/schulbeginn/spring/jan-dip/
  summer-lull window logic.
- `src/ambo/common/config.py`, `src/ambo/common/logging.py`, `src/ambo/common/errors.py`
  (Phase 1) — `Settings`, `load_settings()`, `repo_root()`, structured logging, and the typed
  exception root are already built and are the only `ambo.*` package `simulate/` may import
  from (per the import graph).

### Established Patterns
- `pydantic.BaseModel` (not `BaseSettings`) for all config/schema classes — set in Phase 1 for
  `Settings` and reaffirmed for `ScenarioConfig`/`TruthFile` in 03_MODULES.md §2.1/§2.5.
  `extra='forbid'` invariant applies project-wide.
- Byte-stable, LF-only output discipline (`.gitattributes` from 01-01) — `truth.json` must
  serialize with `sort_keys=True` and fixed float formatting (Guide §1.5) to satisfy SIM-070.
- Single seeded `numpy.random.Generator` per scenario, consumed in a documented, fixed order
  (channel order = taxonomy order, then noise) — this is the project's established RNG
  discipline for reproducibility (mirrors the "one Generator, documented order" pattern that
  will recur in Phase 6's intake anonymization).

### Integration Points
- Phase 3 (Warehouse) builds dbt models directly on this phase's committed
  `data/synthetic/<scenario>/*.csv` — CSV schemas (SIM-004 column names/order) are a contract
  boundary the dbt staging layer depends on.
- Phase 5 (Recovery Suite) reads `truth.json` directly for the VR-3xx recovery gates — the
  `truth.py` schema and derived-quantity formulas are load-bearing for a phase three steps
  downstream.

</code_context>

<specifics>
## Specific Ideas

- The one-off placement script for unanchored promo/burst weeks (D-02) is explicitly a
  throwaway authoring aid, not a deliverable — no WBS task, no module contract entry, and it
  should not end up in `src/ambo/simulate/` as importable production code (that would risk
  tripping A-13 speculative-generality and blur the "frozen into YAML, not computed at
  runtime" boundary the Guide is explicit about).
- Property-based tests (D-03) are additional scope explicitly accepted by the user despite the
  tight 1.5-day effort budget — the planner should size this deliberately rather than let it
  balloon, and the executor should flag early if it's pushing toward the 2× stop-and-ADR
  tripwire.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. AlpenTrek narrative/brand-voice work was
identified as belonging to Phase 9 (Reporting & Release) and explicitly deferred there by
decision D-04, not as an unresolved idea.

</deferred>

---

*Phase: 2-Ground-Truth Simulator*
*Context gathered: 2026-08-05*
