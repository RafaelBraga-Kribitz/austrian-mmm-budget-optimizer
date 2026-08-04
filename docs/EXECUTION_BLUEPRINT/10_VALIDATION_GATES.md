# 10 — VALIDATION GATES (consolidated catalog)

Every gate in the project, grouped into nine named gate classes. A milestone exits
only when its mapped gate classes are green ([01_PHASES.md](01_PHASES.md) maps
phases → classes). For each gate: **trigger** (when it runs), **runner** (command),
**evidence** (artifact a reviewer inspects), **failure protocol**.

Gate IDs from the SPECs (SIM/AG/AD/MD/VR/DC) are authoritative; this catalog adds
the class grouping and the blueprint-level gates (BP-G-xx) that the SPECs imply but
do not number.

---

## 1. Gate classes and milestone mapping

| Class | Name | Green required for |
|-------|------|--------------------|
| G-ARCH | Architecture Gate | P2, and standing from P3 |
| G-DATA-P | Data Quality — Layer P | M1 |
| G-DATA-W | Data Quality — Warehouse | P2 (inside M2 PR) |
| G-DATA-R | Data Quality — Layer R | M4 |
| G-ENG | Engineering Gate | every milestone |
| G-SCI-1..5 | Scientific Gates (DGP, sampler, recovery, Layer-R honesty, decision) | M1, M2, M3, M5, M6 |
| G-VIZ | Visualization Gate | M7 |
| G-DOC | Documentation Gate | M4 (elicitation), M7 (all) |
| G-GOV | Governance Gate | M0 (scaffold), M3 (mechanisms), M4 (freeze/leak), standing |
| G-PORT | Portfolio Gate | M7 |
| G-REL | Release Gate | M7 final |

---

## 2. Standing gates (run on every PR — CI)

| Gate | Trigger/Runner | Evidence | Failure protocol |
|------|----------------|----------|------------------|
| G-ENG lint | CI job 1: `make lint` (ruff + ruff-format + mypy strict) | CI log | Fix; suppressions need inline justification |
| G-ENG tests+coverage | CI job 2: pytest, cov ≥ 80% `src/` | CI log + cov report | Fix; coverage drops block merge |
| G-ENG smoke-fit | CI job 2, `@smoke`: S-A 60 wk, 1×200/200 samples without error, finite R-hat, < 15 min | CI log timing | Investigate compile cache first (BP-D-17), then model graph |
| G-DATA-W dbt | CI job 3: `dbt build` on committed data | CI log | Schema/test failure = data contract break; fix before anything else |
| G-GOV SSOT | CI job 4: `check_ssot_consistency.py` | CI log | Regenerate SSOT in-PR or fix the stray literal; whitelisting requires justification comment |
| G-GOV layer-order | CI job 5: `check_layer_order.py` (full history) | CI log | NEVER "fix" by history edits (A-17); if red, the process was violated — stop, tell the human |
| G-GOV leak | CI job 6 + pre-commit: `leak_scan.py` | CI log | If a real value is found: STOP, human-led remediation (AGENTS A-4) |
| BP-G-01 guard tests | in job 2: simulate↔model independence, forbidden deps, no-requests, pymc-marketing confinement, sample()-only-in-fit | test names in CI log | An intentional new edge requires updating [03 §10](03_MODULES.md) + ADR |

## 3. G-DATA-P — Simulator gates (M1; `make validate-sim`)

| Gate | Check | Evidence |
|------|-------|----------|
| SIM-070 | Two runs byte-identical | hash pair in gate table output |
| SIM-071 | base + Σ contributions + noise = revenue, tol 1e-6 | max abs deviation printed |
| SIM-072 | No negative pre-clip revenue; media share ∈ [15,45]%/yr; noise var share ∈ [2,10]% | per-scenario stats |
| SIM-073 | Max revenue week of each simulated year ∈ Advent window | week list |
| SIM-074 | Adstock closed form (const-spend limit, impulse); Hill(K)=0.5 exact | test run |
| SIM-075 | truth.json schema-complete (pydantic), all §4/§6/§8 quantities | validation output |
| BP-G-02 | Scenario YAML == SPEC-01 §4 table; S-C↔S-B minimal diff | test run |

**Failure protocol:** implementation bug until proven otherwise (spec parameters are
designed to pass); a proven spec infeasibility ⇒ ADR + human spec fix. Never tune §4.

## 4. G-DATA-W — Warehouse gates (P2; `make transform`)

AD-040 grain/spine, AD-041 ranges, AD-042 reconciliation ≤ 1e-6, AD-043 unit-suffix
segregation, AD-044 manifest-channel match (active from M4), BP-G-03 taxonomy
equality (dbt var == settings.yaml, pytest). Evidence: dbt test output in CI job 3.
Failure: fix models/staging; mart schema changes after P3 ⇒ ADR (contract break).

## 5. G-SCI-2 — Sampler health (M2, then every reported fit)

MD-070 (pre-fit, once): transform-shape correlation > 0.95/channel. MD-071: R-hat
< 1.01, ESS bulk/tail > 400, divergences = 0, BFMI > 0.3. MD-072: PPC ≥ 85% weeks
in 90% band, plot committed. MD-074 (Layer R only, explicit constructor): ESS > 300,
divergences ≤ 5 with energy plot + funnel-free pair plots + human note.
Evidence: `reports/model/diag_<layer>.md`.
**Failure protocol:** MD-073 ladder IN ORDER — (1) target_accept 0.95, (2)
non-centered Fourier, (3) tighter s prior Gamma(4,3) [0.5,2.5], (4) fix s=1 (model
class change ⇒ rerun Layer P recovery). One rung per attempt; ADR-005 past rung 1;
human after full ladder (AGENTS §2.4).

## 6. G-SCI-3 — Recovery gates (M3; `make recover`)

The VR §3 table verbatim (thresholds are spec, reproduced here for the runner):

| Gate | S-A | S-B | S-C |
|------|-----|-----|-----|
| VR-301 ROAS coverage (true in 90% HDI) | ≥ 5/6 | ≥ 4/6 | ≥ 4/6 incl. zero channel |
| VR-302 Spearman (median vs true) | ≥ 0.83 | ≥ 0.7 | not gated |
| VR-303 curve MAE% (per-channel / median) | ≤ 15 / ≤ 10 | ≤ 25 / ≤ 15 | reported |
| VR-304 zero-effect (display_video) | — | — | P(ROAS<0.2) ≥ 0.7 AND share ≤ 3% |
| VR-305 half-life ranking print/radio > search | required | required | required |
| VR-306 media share within ±10 pp of truth | required | required | required |

Plus VR-401 (beat seasonal-naive MAPE on S-A/S-B; coverage reported), VR-601
(OLS side-by-side exists, HC1 verified), VR-602 (crosscheck corr ≥ 0.8 on S-B,
mapping doc complete), VR-701/702/703 (reproducibility trio).
Evidence: RECOVERY_REPORT.md + gate table + golden bands.
**Failure protocol:** VR-310 debug order — transforms (MD-070) → scaling round-trip
→ data joins → sampler health. Widening ⇒ ADR naming suspected structural cause.
Two failed focused attempts ⇒ human.

## 7. G-DATA-R — Intake gates (M4; `make validate-intake`)

AG-060 continuity/≥52wk, AG-061 media↔outcome consistency, AG-062 shares
(`other`<10%, no week >15% of window spend, flighted-zero rules, search >0 in ≥95%
weeks), AG-063 ratio sanity (rev/spend ∈ [1.5,50], CTR ∈ [0.1,15]%), AG-064
December seasonality, AG-065 PII scrub + leak scan, AG-066 manifest complete.
Evidence: `reports/ingestion/intake_validation.md` (scale-free stats only).
**Failure protocol:** every failure here is a STOP-and-ask (AGENTS §2.1) — mapping
and unit questions belong to the human; relaxations via the specific ADRs the spec
names (AG-062 taxonomy ADR; AG-060 short-window ADR + Charter §7 consult; AG-064
counter-seasonal ADR).

## 8. G-GOV — Governance gates (M4 freeze + standing)

| Gate | Check | Evidence |
|------|-------|----------|
| BP-G-04 permission | DATA_PERMISSION.md complete (exists/role/date/scope, no names) BEFORE any private file processed | doc + ADR-001 |
| GB-502 freeze | Freeze commit + `prior-freeze-v1` tag ancestor of every R artifact; no post-tag edits (amendment exception per Guide §10) | check_layer_order output |
| GB-501 order | RECOVERY_REPORT commit ancestor of every R fit artifact | same |
| MD-061/062 elicitation | Doc-lint: fields, ≥100-char first-person rationales, YAML↔doc match, freeze statement + hash | test run |
| AG-045 leak | Full scan green locally at M4; pattern scan green in CI forever | scan output in PR |

## 9. G-SCI-5 — Decision gates (M6; `make decide`)

DC-701 optimizer recovery (S-A cosine ≥ 0.90/regret ≤ 5%; S-B ≥ 0.80/≤ 10%),
DC-702 φ-ordering on S-B, DC-703 two-run byte determinism, DC-704 constraint audit
(Σ=B ±1e-6, bounds exact, fixed channels untouched), DC-705 full regeneration
without sampling. Evidence: gate table in PR + exports + SSOT keys.
**Failure protocol:** with green G-SCI-3, suspect optimizer numerics first
(BP-D-16 steady-state mismatch, gradient, restart seeding) — the model is already
validated.

## 10. G-VIZ / G-DOC / G-PORT / G-REL (M7)

| Gate | Check |
|------|-------|
| G-VIZ | Five RB-2xx charts: regenerate byte-stable, no sampling; style/format/caption compliance (title, unit axes, source note, epistemic tag, fixed colors); RB-301 recompute test green |
| G-DOC | README = RB §6 order (structure test) incl. GB-503 script link + ≤5-command reproduce; EXEC_SUMMARY = RB §5 ≤ 2 pages; LIMITATIONS ⊇ GB §6 nine items (mapping table); correct framing variant active |
| G-PORT | Charter §1.2 readability review: every executive artifact readable without knowing "adstock" by name; DC-504 + T-7 brand-search paragraphs present (the marketing-seniority signals); prior-elicitation doc reads as agency judgment, not stats |
| G-REL | DL-1..10 table green per [11 §4](11_ACCEPTANCE_CRITERIA.md); fresh-clone probe log; final SSOT; full leak scan; tag v1.0 |

**G-PORT failure protocol:** wording fixes only — numbers cannot change at this
gate (they are SSOT-locked); if a number must change, the producing phase reopens.
