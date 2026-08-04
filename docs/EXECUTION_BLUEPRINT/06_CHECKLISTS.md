# 06 — CHECKLISTS (per milestone)

Paste the relevant milestone block into the milestone PR and tick item-by-item with
evidence links (CI run URL, file path, command output). **Unticked = not done**
(AGENTS §5). Seven checklist classes per milestone: Implementation, Code review,
QA, Scientific validation, Documentation, Repository hygiene, Release (M7 only has
the full Release class; earlier milestones have a mini "merge readiness" version).

Shared items appear once here and are referenced as **[STD]** in each milestone:

**[STD] Merge readiness (every milestone)**
- [ ] `make lint && make test` green locally (output pasted)
- [ ] All six CI jobs green on the PR head commit
- [ ] Coverage ≥ 80% of `src/ambo/` (report linked) — from first milestone with code
- [ ] No TODO/FIXME/XXX left in touched files (`grep -rn "TODO\|FIXME\|XXX" src/ tests/ scripts/`)
- [ ] No new warnings in pytest output; no ruff/mypy suppressions added without a comment justifying each
- [ ] Conventional commits with REQ IDs; PR title carries the milestone
- [ ] `docs/BUILD_LOG.md` entry appended (scope, decisions, wall-times)
- [ ] SSOT regenerated in this PR if any reported number changed (GB §4 freshness)
- [ ] No file added outside the SPEC-08 §2 layout; no gitignored-by-design artifact committed
- [ ] Review performed against [07_QUALITY_STANDARDS.md](07_QUALITY_STANDARDS.md) and [09_ANTI_PATTERNS.md](09_ANTI_PATTERNS.md) (reviewer states "checked" explicitly)

---

## M0 — Bootstrap

**Implementation**
- [ ] T-001…T-012 all closed per their WBS acceptance criteria
- [ ] `make setup` from a fresh clone succeeds on Windows Git Bash AND Linux (or CI proves Linux)
- [ ] Makefile stub targets exit non-zero with phase-pointer messages
- [ ] Guard tests exist and were proven to bite (scratch-violation evidence linked)

**Code review**
- [ ] Settings: `extra='forbid'`, all MD-050 numbers in config only
- [ ] Logging factory is the sole logger path; redaction test reviewed
- [ ] leak_scan never echoes matched content (code path reviewed)
- [ ] ci.yml: 6 jobs, fetch-depth 0 on jobs 5–6, no cron, caches keyed correctly

**QA**
- [ ] Pre-commit blocks: planted private key; planted email in `data/real_anon/`
- [ ] `.gitignore` probe (warehouse file + export csv) shows clean status
- [ ] season_windows regeneration idempotent (`git diff` empty)

**Scientific validation**
- [ ] Season-window unit tests enumerate all five window rules incl. advent count = 4/year and Dec-24 containment

**Documentation**
- [ ] ADR template + 5 pre-planned slots listed; BUILD_LOG header states append-only rule
- [ ] `.env.example` documents AMBO_PRIVATE_DROP with secrecy note
- [ ] Schulbeginn interpretation recorded in BUILD_LOG (Guide §1.2)

**Repository hygiene**
- [ ] Baseline commit = docs only; code starts at commit 2+
- [ ] LF endings pinned; `uv.lock` committed
- [ ] [STD]

---

## M1 — Simulator

**Implementation**
- [ ] T-101…T-109 closed; `make simulate && make validate-sim` green, table pasted
- [ ] Scenario YAMLs == SPEC-01 §4 table (test link); S-C differs from S-B only in weeks/seed/zero-β (test link)

**Code review**
- [ ] No import between `simulate/` and `model/` (guard test green)
- [ ] RNG: single generator per scenario, documented draw order
- [ ] Rounding/flooring order per Guide §1.3

**QA**
- [ ] SIM-070 byte-determinism proven twice (hashes pasted)
- [ ] SIM-031 spend statistics green ×3 scenarios
- [ ] CSV schemas exactly SIM-004 (column names/order test)

**Scientific validation**
- [ ] SIM-071 decomposition audit ≤ 1e-6 all weeks, all scenarios
- [ ] SIM-072 plausibility: media share ∈ [15,45]%, noise var share ∈ [2,10]% (numbers pasted)
- [ ] SIM-073 peak week in Advent each simulated year
- [ ] SIM-074 closed-form + impulse tests green; Hill(K)=0.5 exact
- [ ] SIM-075 truth.json schema-valid ×3; S-C display_video truth ROAS = 0

**Documentation**
- [ ] Docstrings carry `Implements: SIM-xxx`; promo/burst authoring rationale in BUILD_LOG

**Repository hygiene**
- [ ] Exactly 9 data files committed under `data/synthetic/`; nothing else
- [ ] [STD]

---

## P2 — Warehouse (reviewed inside the M2 PR)

**Implementation**
- [ ] T-201…T-205 closed; `make transform` green locally + CI job 3
- [ ] AD-040..043 green; AD-044 present + gated off; AD-042 delta pasted

**Code review**
- [ ] Pivot generated from taxonomy var (no hand-written channel SQL)
- [ ] BP-D-03 renames complete; no `_eur`/`_aeur` column survives staging
- [ ] db.py: read-only, contract assertions, mart-only rule grep pasted

**QA**
- [ ] Round-trip totals: simulator CSV vs mart vs accessor frame (equalities pasted)
- [ ] `layer_r_present=false` build has zero Layer R rows (query pasted)

**Documentation**
- [ ] fct_mmm_input column contract in [03_MODULES.md §8](03_MODULES.md) matches built schema (describe output pasted)
- [ ] [STD]

---

## M2 — Model on S-A

**Implementation**
- [ ] T-301…T-308 closed; full S-A fit executed at MD-050 settings

**Code review**
- [ ] Free-RV name set == Guide §2.2 table
- [ ] No scenario/layer branch in mmm.py (grep pasted)
- [ ] Scaling round-trip property test reviewed; back-transform lives only in transforms.py
- [ ] posterior_io refuses metadata-less files; atomic write reviewed

**QA**
- [ ] Smoke-fit green in CI < 15 min (run time pasted)
- [ ] Two same-machine runs: ArviZ summaries match to 3 decimals

**Scientific validation**
- [ ] MD-070 transform-shape correlation > 0.95 per channel (values pasted)
- [ ] MD-071: R-hat < 1.01, ESS bulk/tail > 400, divergences = 0, BFMI > 0.3 (diag report linked)
- [ ] MD-072: PPC ≥ 85% weeks in band; PPC plot committed
- [ ] MD-040: priors_synthetic channel-agnostic (test link)
- [ ] Prior-predictive sanity within [0.2, 5]× observed mean

**Documentation**
- [ ] `reports/model/diag_P-SA.md` committed; ladder not used (or ADR-005 if rung > 1)

**Repository hygiene**
- [ ] `P-SA.parquet` committed with full metadata; netCDF NOT committed
- [ ] [STD]

---

## M3 — Recovery suite

**Implementation**
- [ ] T-401…T-410 closed; `make recover` green end-to-end

**Code review**
- [ ] Gate table constant == VR §3 cell-for-cell (side-by-side reviewed)
- [ ] ROAS draws computed via model transforms only (no truth-side code in the path)
- [ ] pymc-marketing confined to crosscheck.py (guard test)
- [ ] check_layer_order tmp-repo tests cover all four cases (Guide §10)

**QA**
- [ ] VR-701 3-decimal regression green; VR-702 golden bands committed + green in CI
- [ ] VR-703: netCDF deleted → `make report` regenerates identically (hashes pasted)
- [ ] Holdout leakage guard test green (training-window ScaleFactors)

**Scientific validation**
- [ ] VR-301 coverage: S-A ≥ 5/6, S-B ≥ 4/6, S-C ≥ 4/6 (counts pasted)
- [ ] VR-302 Spearman: S-A ≥ 0.83, S-B ≥ 0.7 (values pasted)
- [ ] VR-303 curve MAE%: S-A ≤ 15/10, S-B ≤ 25/15 (table pasted); S-C reported
- [ ] VR-304 zero-effect: P(ROAS<0.2) ≥ 0.7 AND share ≤ 3% (values pasted)
- [ ] VR-305 half-life ranking holds ×3 scenarios
- [ ] VR-306 media share within ±10 pp ×3 scenarios
- [ ] VR-401 beats naive on S-A + S-B (MAPEs pasted)
- [ ] VR-601 OLS table present with HC1 verified against textbook case
- [ ] VR-602 correlation ≥ 0.8 on S-B; mapping doc complete

**Documentation**
- [ ] RECOVERY_REPORT.md section order machine-checked; closing ≥ 500 chars with MD-020 + lift-test content
- [ ] SSOT: recovery keys + zero_channel_verdict present with tags

**Repository hygiene**
- [ ] P-SB/P-SC parquets committed; goldens under `tests/golden/`; compute ledger in BUILD_LOG
- [ ] [STD]

---

## M4 — Agency intake (human-heavy)

**Implementation**
- [ ] T-501…T-506 closed pre-drop (fixture evidence); T-507…T-510 closed on the drop

**Code review**
- [ ] RescaleFactors: bounds + rejection rule enforced; repr redacted; never serialized (code reviewed line-by-line)
- [ ] Stage-1 cannot write inside repo; stage-2 writes only whitelisted outputs (guards reviewed)
- [ ] Exception paths carry counts, never values/names

**QA (leak-critical — reviewer must be the human)**
- [ ] AG-060..066 green on real outputs; ingestion report committed and contains only scale-free/masked stats
- [ ] Full local leak scan green (blocklist mode); CI pattern scan green
- [ ] The M4 commit's file list reviewed name-by-name: only `data/real_anon/*`, manifest, ingestion report, intake seed, dbt flip, ADRs, DATA_PERMISSION, elicitation files
- [ ] No absolute real € anywhere in the diff (human eyeball + scan)
- [ ] `git log -p` of the PR contains zero pre-anonymization values (spot-check protocol: 10 random hunks)

**Scientific validation**
- [ ] Window length ≥ 52 weeks (or descriptive-only ADR + Charter §7 consult)
- [ ] AG-063 ratio + CTR sanity values pasted; AG-064 December check result pasted
- [ ] Channel mapping reviewed; `other` < 10% (ADR-002 records share + BP-D-04 choice)

**Documentation**
- [ ] DATA_PERMISSION.md: permission/role/date/scope, zero names
- [ ] ADR-001..004 merged; BP-D-11 decision recorded in ADR-003
- [ ] PRIOR_ELICITATION.md: every Layer R channel, all 5 MD-060 fields, rationales ≥ 100 chars first-person (MD-061 lint green), freeze statement + hash (MD-062)

**Repository hygiene / freeze**
- [ ] Freeze commit contains exactly priors_real.yaml + elicitation doc; tag `prior-freeze-v1` on it
- [ ] `check_layer_order.py` green; no Layer R fit artifact exists yet (script output pasted)
- [ ] [STD]

---

## M5 — Layer R fit + sensitivity

**Implementation**
- [ ] T-601…T-605 closed; `make fit-real && make sensitivity` executed

**Code review**
- [ ] `DiagGates.layer_r()` used explicitly; no threshold edits to standard profile
- [ ] Variant plumbing produces BP-D-06 names exactly

**QA**
- [ ] Posterior metadata: priors hash == freeze-commit blob hash (values pasted)
- [ ] All artifacts regenerate from committed parquets without sampling

**Scientific validation**
- [ ] MD-074: ESS > 300; divergences ≤ 5 WITH energy plot + funnel-free pair plots + human note (report linked)
- [ ] VR-501 forest plot committed; movement/narrowing paragraph slots filled with SSOT numbers
- [ ] VR-502 re-attribution table with HDIs; VR-503 combined figure; VR-504 delta table
- [ ] VR-401 Layer R row reported with n=13 caveat text
- [ ] Wide HDIs discussed, not hidden (A-7)

**Documentation**
- [ ] SSOT: roas_<channel> keys + layer_r_weeks + divergences_real_fit + holdout_mape_real + media_share_of_revenue_real
- [ ] [STD] (CI layer-order + freeze checks green on THIS PR is mandatory evidence)

---

## M6 — Decision layer

**Implementation**
- [ ] T-701…T-705 closed; `make decide` green from committed posteriors only

**Code review**
- [ ] Constraint construction single-path (factory); search_brand + other fixed
- [ ] Gradient formula reviewed against Guide §5; draw subset = first 500 rows
- [ ] No sampling import path in `decide/` (reviewed)

**QA**
- [ ] DC-703 determinism: two full runs byte-identical (hashes pasted)
- [ ] DC-704 audit: Σ=B ± 1e-6, bounds exact, fixed channels unchanged (test link)
- [ ] Toy-problem optimum found to 1e-4 (unit test)

**Scientific validation**
- [ ] DC-401: S-A cosine ≥ 0.90 & regret ≤ 5%; S-B ≥ 0.80 & ≤ 10% (values pasted)
- [ ] DC-502 φ-ordering reproduced on S-B (ordering pasted)
- [ ] Restart spread ≤ 1% or warning visibly propagated to artifacts
- [ ] Extrapolation guards visible in outputs (1.3× bounds + binding flags)

**Documentation**
- [ ] DC-302 caption on every gain artifact (grep + visual)
- [ ] DC-504 paragraph ≥ 500 chars, ≥ 3 numbers, tone reviewed
- [ ] SSOT: expected_gain keys, overcredit ratios, next_euro keys, optimizer_regret_sb
- [ ] [STD]

---

## M7 — Reporting & release

**Implementation**
- [ ] T-801…T-806 closed; `make ssot export report` green

**Code review**
- [ ] Captions single-occurrence grep-test green (GB-102)
- [ ] Chart code reads only exports/SSOT-fed frames/committed posteriors (imports audit)
- [ ] RB-301 recompute test green

**QA / Visualization Gate**
- [ ] Five charts regenerate byte-stable twice; every chart: title, unit axes, source note, epistemic tag (visual review, all five screenshotted in PR)
- [ ] Channel colors identical across all charts (test link)
- [ ] `make report` requires no sampling (netCDF-deleted probe)

**Scientific validation**
- [ ] Every number in README/EXEC_SUMMARY has tag + HDI where MODELED (A-7 sweep)
- [ ] check_ssot_consistency green across all three docs; whitelist entries each justified

**Documentation Gate**
- [ ] README order == RB §6 (structure test); leads with recovery verdict + Layer R answer; RB-201 before RB-202; stack talk not before §8; check_layer_order linked (GB-503); reproduce section ≤ 5 commands
- [ ] LIMITATIONS: all nine GB §6 items mapped to sections (mapping table in PR)
- [ ] EXEC_SUMMARY: RB §5 structure; freeze hash in "Why trust this"; ≤ 2 pages
- [ ] Correct framing variant active (Layer R alive vs Charter §7) — decision referenced

**Dashboard (human)**
- [ ] 4 pages per RB-401..404; German subtitles; a€ footer verbatim; .pbix + 4 screenshots committed; rebuild instructions verified by second party

**Release Gate**
- [ ] DL-1: fresh-clone `make setup && make all` probe log attached (Layer P bit-for-bit within tolerance doctrine; zero private inputs)
- [ ] DL-2…DL-10 verified per [11 §4](11_ACCEPTANCE_CRITERIA.md) (table with evidence links)
- [ ] Final SSOT regenerated in the release PR; leak scan full mode green
- [ ] Effort vs Charter §5 budget recorded; tag `v1.0`
- [ ] [STD]
