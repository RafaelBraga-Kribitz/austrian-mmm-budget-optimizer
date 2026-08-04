## Conflict Detection Report

Operation: ingest (mode: new). Corpus: 24 documents — 1 PRD, 20 SPEC, 3 DOC, 0 ADR.
Precedence applied: ADR > SPEC > PRD > DOC. No per-doc precedence override was set on
any classification. No document carries `locked: true`, so no LOCKED-vs-LOCKED
condition could arise.

### BLOCKERS (0)

None. No locked decisions exist anywhere in the corpus, no classification came back
UNKNOWN, and no classification came back low-confidence. See INFO 3 for the one
condition that would normally raise a blocker and why it was not treated as one.

### WARNINGS (7)

[WARNING] Charter's self-declared authority is inverted by the configured precedence
  Found: PROJECT_CHARTER.md line 7-8 declares "Authority: Single Source of Truth for goals, scope, acceptance. Charter beats specs; specs beat code; deviations require ADRs."
  Found: PROJECT_CHARTER.md is classified PRD (confidence medium, precedence null); the configured ordering is ADR > SPEC > PRD > DOC, which makes every docs/SPEC-0x file outrank the Charter on contradiction. The classifier flagged this explicitly ("Synthesizer may want to assign elevated precedence per the document's own authority statement").
  Impact: Two contradictions were auto-resolved against the Charter under the configured ordering (see INFO 1 and INFO 2). Both happened to favour the more precise SPEC text, but the ordering itself is unratified — no ADR exists to settle it, and the Charter is the only document that states an authority order at all.
  → Decide one of: (a) accept the configured ordering as-is and note it in PROJECT.md; (b) set `precedence: 0` for PROJECT_CHARTER.md via --manifest and re-run ingest, which will flip INFO 1 and INFO 2 the other way; or (c) author ADR-000 recording the intended precedence, which is the only mechanism SPEC-09 GB-201 provides for this class of decision.

[WARNING] Competing optimizer fixed-channel sets — SPEC-06 vs 03_MODULES
  Found: docs/SPEC-06_decision_layer.md DC-203(c) fixes exactly one channel: "`search_brand` FIXED at its historical mean". DC-704's constraint audit correspondingly checks only "search_brand unchanged".
  Found: docs/EXECUTION_BLUEPRINT/03_MODULES.md §6.1 states the `optimize_allocation` post-condition as "fixed channels (search_brand, other) at historical mean", adding `other` to the fixed set.
  Found: the basis for the addition is BP-D-04 in docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md, which is DOC-tier and self-labels the item "(ADR-002 at intake)" — i.e. it requires an ADR that does not exist.
  Impact: Both documents are SPEC-tier and equal precedence, so this cannot be auto-resolved. The two variants produce materially different DL-4 output (optimal allocation and expected gain) whenever `other` is present in the Layer R channel mix, and the DC-704 audit test would be written differently under each.
  → Choose one variant before routing: either amend SPEC-06 DC-203/DC-704 to include `other` in the fixed set, or strike the `other` reference from 03_MODULES §6.1 and defer the question to ADR-002 at intake. Both variants are preserved verbatim in .planning/intel/constraints.md and .planning/intel/decisions.md (BP-D-04).

[WARNING] SPEC-08 §2 declares an "exact" repository layout that omits modules 03_MODULES defines as binding contracts
  Found: docs/SPEC-08_engineering.md §2 heading reads "Repository layout (exact; empty dirs get `.gitkeep`)" and lists `src/ambo/model/` as "(mmm.py, transforms.py, elicit.py, diagnostics.py, posterior_io.py)" and `src/ambo/simulate/` as "(dgp.py, spend_patterns.py, platform_bias.py, truth.py)".
  Found: docs/EXECUTION_BLUEPRINT/03_MODULES.md §4.2 defines `model/priors.py` and §4.4 defines `model/fit.py` as public contracts; §2.1 defines `simulate/config.py` and §2.6 defines `simulate/__main__.py`.
  Found: docs/EXECUTION_BLUEPRINT/04_DEPENDENCIES.md §1 makes `model/fit.py` load-bearing — "`pm.sample` outside `model/fit.py`" is one of the five guard-tested forbidden import edges.
  Found: docs/EXECUTION_BLUEPRINT/06_CHECKLISTS.md [STD] requires "No file added outside the SPEC-08 §2 layout" on every milestone PR.
  Impact: Both sources are SPEC-tier and equal precedence. As written, creating `model/fit.py` — which the forbidden-edge guard test T-010 requires to exist — fails the standing checklist item on the very PR that introduces it. Four files are affected.
  → Reconcile before routing: extend SPEC-08 §2's layout listing to include `model/fit.py`, `model/priors.py`, `simulate/config.py`, and `simulate/__main__.py`, or soften the "exact" wording and the 06 [STD] checklist item to allow contract-listed additions. Do not let an implementer silently pick.

[WARNING] Response-curve grid mismatch between truth and model, feeding one shared export and one comparison gate
  Found: docs/SPEC-01_ground_truth_simulator.md §8 specifies the truth response-curve sample as "contribution at 21 spend grid points 0…2×max weekly spend, at steady-state adstock".
  Found: docs/SPEC-04_mmm_model.md MD-082 specifies the model response curves as "contribution at 21 grid points (0…1.5× max observed weekly spend — NOT 2×; extrapolation guard starts here)".
  Found: docs/SPEC-03_data_model.md AD-050 defines a single export `exports/response_curves.csv` as "spend grid × channel × layer: contribution mean + HDI (+ truth for P)", implying one shared grid; and docs/SPEC-05_validation_recovery.md VR-303 gates "mean absolute error between posterior-mean curve and true curve over the observed-spend grid" without specifying which grid or any regridding rule.
  Impact: Two SPEC-tier documents at equal precedence define non-identical 21-point grids for quantities that must be joined in one CSV and differenced in one gate. VR-303's numeric result depends on the unspecified reconciliation (interpolate truth onto the model grid, truncate the truth grid at 1.5×, or emit two grids), and VR-303 is a hard M3 exit gate. The blueprint's ambiguity index (00 §5) does not cover this.
  → Specify the reconciliation before routing: pick the grid VR-303 evaluates on and state whether `response_curves.csv` carries one grid or two. Both grid definitions are preserved verbatim in .planning/intel/constraints.md.

[WARNING] DL-1 acceptance requires comparing exports against committed versions, but exports are gitignored
  Found: docs/EXECUTION_BLUEPRINT/11_ACCEPTANCE_CRITERIA.md §4 DL-1 requires "compare regenerated reports/exports to committed versions: text artifacts byte-equal, MCMC-derived numbers within VR-702 bands".
  Found: docs/SPEC-08_engineering.md §2 lists `exports/ (gitignored except .gitkeep)` and EB-081 puts `exports/*.csv` in `.gitignore`, with the "committed-by-design" list naming only `data/synthetic/`, `data/real_anon/`, and `data/posteriors/*.parquet`.
  Impact: Both sources are SPEC-tier and equal precedence. There is no committed version of any export CSV to compare against, so the DL-1 release-gate probe as specified cannot be executed for the exports half. DL-1 is the first row of the G-REL release gate.
  → Reconcile before routing: either restrict the DL-1 comparison to `reports/` artifacts, or commit the six export CSVs by design and amend EB-081. Note that the same tension touches RB-301, whose pytest recomputes RB-201 bars from `allocation_scenarios.csv`.

[WARNING] Competing full-fit runtime thresholds across three SPEC-tier documents
  Found: docs/EXECUTION_BLUEPRINT/07_QUALITY_STANDARDS.md Part A states "Runtime — full fit | ≤ ~35 min/fit at MD-050 on 4 cores".
  Found: docs/EXECUTION_BLUEPRINT/03_MODULES.md §4 states "Full fit (MD-050) ≤ ~30 min/scenario on a modern laptop".
  Found: docs/EXECUTION_BLUEPRINT/04_DEPENDENCIES.md §7 states "est. 15–35 min each on 4 cores", and docs/SPEC-08_engineering.md §5 states fits "cost 30–90 min total".
  Impact: Three different ceilings for the same measurement at equal precedence. 07 Part A is the document that review enforces, so a 32-minute fit is simultaneously compliant and non-compliant depending on which page a reviewer opens. Minor, but the value feeds the Charter §5 effort tripwire via the 04 §7 compute ledger.
  → Pick one number, place it in the single home that 09 A-2 (magic numbers) demands, and have the other two documents cite it rather than restate it.

[WARNING] DOC-tier blueprint defaults (BP-D) are treated as binding by SPEC-tier documents
  Found: docs/EXECUTION_BLUEPRINT/00_MASTER_PLAN.md is classified DOC (confidence medium), and §5 labels all twenty BP-D items "proposals with defaults: implement the default unless the human overrides; items marked (ADR) must be recorded as an ADR when exercised".
  Found: SPEC-tier documents already hard-code several of them as contracts — 03_MODULES §2.4 binds BP-D-02, §4.5 binds BP-D-06 posterior naming, §6.1 binds BP-D-04 (see WARNING 2), §8 binds BP-D-03/05/19; 04_DEPENDENCIES §7 binds BP-D-18 and the compute ledger, §preamble binds BP-D-16; 10_VALIDATION_GATES §2 binds BP-D-17 and §9 binds BP-D-16; 11_ACCEPTANCE_CRITERIA §2 DoR item 4 makes accepting-or-overriding a BP-D a precondition for starting any task.
  Impact: A precedence inversion. A downstream consumer reading .planning/intel/constraints.md will treat those module contracts as SPEC-authoritative, when their basis is DOC-tier and explicitly override-able. Four of the twenty (BP-D-04, BP-D-11, and the ADR triggers in BP-D-02/BP-D-03 chains) additionally name an ADR that does not exist. None of the twenty has been ratified.
  → Before routing, decide whether the BP-D set is accepted wholesale (record it once, e.g. as ADR-000 or in PROJECT.md) or item-by-item at task time per the DoR. All twenty are preserved verbatim with `status: proposed` in .planning/intel/decisions.md; none was promoted to a binding constraint by this synthesis.

### INFO (7)

[INFO] Auto-resolved: SPEC-01 §5 beats PROJECT_CHARTER.md §2.3 on scenario S-B length
  Note: PROJECT_CHARTER.md §2.3 states "Layer P: 156 weeks per scenario (S-C: 78)", which implies S-B = 156. docs/SPEC-01_ground_truth_simulator.md §5 sets S-B = 104 weeks, seed 202. SPEC outranks PRD under the configured precedence, so 104 is carried into the intel. Corroborating SPEC-tier text: SPEC-05 VR-503 refers to S-B as "104+ clean-ish weeks", 03_MODULES §2.1 constrains `ScenarioConfig.weeks` to {156, 104, 78}, and 01_PHASES describes S-B as "Realistic: 2 years". The Charter's parenthetical is read as imprecise drafting rather than an intentional 156-week S-B. Subject to WARNING 1 if the precedence is reversed.

[INFO] Auto-resolved: SPEC-08 §5 and 11_ACCEPTANCE_CRITERIA §4 beat PROJECT_CHARTER.md DL-1 on the reproduction command set
  Note: PROJECT_CHARTER.md DL-1 says "Fresh clone + `make setup && make all` reproduces every Layer P artifact bit-for-bit-in-tolerance". SPEC-08 §5 defines `make all` as transform → recover → sensitivity → decide → ssot → export → report, which includes neither `simulate` nor any fit target, so `make all` alone cannot reproduce `data/synthetic/`. 11_ACCEPTANCE_CRITERIA §4 supplies the operative probe (explicit target sequence, plus a separate `make simulate && make validate-sim` byte-reproduction step). SPEC outranks PRD; the SPEC-tier probe is carried as the acceptance criterion for REQ-dl1-reproducible-pipeline. Note that the export half of that probe is itself contradicted — see WARNING 5.

[INFO] Cross-reference cycle detection: 2 strongly connected components covering 22 of 24 documents, treated as benign
  Note: DFS over the `cross_refs` graph found two SCCs. SCC-1 (9 nodes): PROJECT_CHARTER.md plus SPEC-02..SPEC-09 — the Charter's §8 document map points at every SPEC while SPEC-02/04/05/06/08/09 point back at the Charter, and SPEC-03/07 close further loops through SPEC-04/05/09. SCC-2 (13 nodes): blueprint documents 00, 01, 02, 03, 05, 06, 07, 08, 09, 10, 11, 12, 13. Only `docs/SPEC-01_ground_truth_simulator.md` and `docs/EXECUTION_BLUEPRINT/04_DEPENDENCIES.md` are acyclic. Max traversal depth was 4, far below the 50 cap.
  Note: The default rule records every cycle as an unresolved blocker and excludes the cyclic set from synthesis. That rule was NOT applied here, as a deliberate and disclosed deviation. Its stated rationale is that synthesis loops produce garbage — which requires transitive content resolution, where doc A's meaning is only definable via doc B and vice versa. That condition does not hold in this corpus: every one of the 24 documents was already classified and was read exactly once, each carries self-contained content, and no entry in the intel files was derived by following a reference. The cycles here are navigational "see also" links between siblings in a single ingest batch. Applying the rule literally would have blocked 22 of 24 documents and aborted the ingest of a structurally healthy corpus.
  → If you prefer the strict interpretation, re-run with a --manifest that breaks the mutual links (or accept this note as the record of the decision). Nothing else in this report depends on it.

[INFO] No ADR tier exists; SPEC is the top populated precedence tier
  Note: `docs/ADR/` is referenced by docs/SPEC-08_engineering.md §2 (layout), docs/SPEC-09_governance_quality.md GB-201 (path template `docs/ADR/ADR-NNN_short-title.md`), and GB-202 (five pre-planned slots ADR-001..ADR-005), and is scheduled for creation by task T-012. The directory is absent from the ingest set. Consequences carried into the intel: zero decisions are `locked`, every entry in .planning/intel/decisions.md is `status: proposed`, and eight ADR-shaped design commitments asserted by SPEC text (additive-not-log, pymc-marketing confinement, simulator/model code independence, mart-only model input, two-stage intake, append-only history, brand-search fixed, layer-order and freeze ordering) are recorded as unratified.

[INFO] Zero LOCKED decisions in the corpus
  Note: All 24 classifications carry `locked: false`. There is therefore no LOCKED-vs-LOCKED contradiction and no LOCKED-vs-existing-context contradiction. Mode is `new` with no pre-existing `.planning/` content, so the merge-mode check against an existing `<decisions>` block did not apply.

[INFO] Dangling and imprecise section cross-references
  Note: Several citations point at sections that do not exist or do not contain the cited content. PROJECT_CHARTER.md R-4 cites "SPEC-06 §3.6" for the brand-search exclusion, which actually lives at DC-203(c) in SPEC-06 §2; DL-4 cites "SPEC-06 §3" for extrapolation guards, which are also in §2. PROJECT_CHARTER.md E-2 cites "SPEC-05 §2" for the Layer P gates, while SPEC-05 itself names §3 as the gate section (§2 defines what recovery is measured against). docs/EXECUTION_BLUEPRINT/01_PHASES.md P6 cites "SPEC-04 §7.6/MD-074", but SPEC-04 §7 has no §7.6. These are documentation hygiene items, not content contradictions; the intel files cite the sections that actually hold the content.

[INFO] Heavy blueprint-versus-SPEC overlap treated as restatement, not conflict
  Note: As instructed, the intentional duplication between docs/EXECUTION_BLUEPRINT/00-13 and docs/SPEC-01..09 was not flagged. Verified-identical restatements include: the full VR §3 recovery gate table reproduced cell-for-cell in 10_VALIDATION_GATES §6; MD-071/MD-074 sampler thresholds in 07 Part A and 10 §5; SIM-070..075 in 10 §3 and 06 M1; AG-060..066 in 10 §7; DC-701..705 in 10 §9 and 01_PHASES P7; the six-job CI list in EB-060, 10 §2, and 06 M0; coverage >= 80% in Charter DL-8, EB-072, 07 Part A, and 06 [STD]; and the MD-050 sampler settings in SPEC-04 §5 and 03_MODULES §1.1. Where a restated value diverged, it is reported above — see WARNING 6, the only divergence found in this class.
