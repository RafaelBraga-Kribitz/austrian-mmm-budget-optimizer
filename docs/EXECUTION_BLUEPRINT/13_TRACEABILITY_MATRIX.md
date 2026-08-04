# 13 — TRACEABILITY MATRIX

Two directions: **forward** (task → requirements → deliverables → artifacts) and
**reverse** (every SPEC requirement family → covering tasks). Rule: nothing exists
without traceability — a PR whose changes map to no REQ ID is either a blueprint
bug or scope creep ([09 §A-9](09_ANTI_PATTERNS.md)).

Charter column: E = epistemic rules §3, DL = deliverables §4, R = risks §6,
O = out-of-scope walls §2.2. A/T/W = AGENTS rules/traps/working style.

## 1. Forward matrix (task → REQ → Charter → artifacts)

| Task | REQ IDs | Charter / AGENTS | Key artifacts |
|------|---------|------------------|---------------|
| T-001 | EB-080, EB-082 | §5 build-order argument; A-2 | `.git/`, baseline commit |
| T-002 | EB-001, EB-030 | DL-8 | `pyproject.toml`, `uv.lock` |
| T-003 | EB-081, AG-020, EB-041 | DL-1 | skeleton, `.gitignore`, `.env.example`, LICENSE |
| T-004 | EB-040, EB-041, MD-050 | E-4 adjacency | `config/settings.yaml`, `common/config.py` |
| T-005 | EB-041 | A-4 | `common/logging.py` |
| T-006 | EB-050, SPEC-08 §5 | DL-1 | `Makefile` |
| T-007 | EB-001, EB-002 | DL-8 | `.pre-commit-config.yaml` |
| T-008 | AG-045, EB-002 | R-6, A-4, DL-9 | `scripts/leak_scan.py` |
| T-009 | EB-060, EB-061 | O-7, DL-8 | `.github/workflows/ci.yml` |
| T-010 | EB-030, EB-070, SIM-003 | W-2, T-3 | guard tests |
| T-011 | AD-020, MD-022, SIM §2.1 | — | `scripts/generate_season_windows.py`, seed CSV |
| T-012 | GB-201, GB-202 | W-3 | ADR template, `docs/BUILD_LOG.md` |
| T-101 | SIM-002, SIM-030, §4/§5/§6 | O-scope, DL-2 | scenario schema + 3 YAMLs |
| T-102 | SIM-030, SIM-031 | — | `simulate/spend_patterns.py` |
| T-103 | SIM §2.1, SIM-073 | — | baseline/seasonality fns |
| T-104 | SIM §2.2, SIM-003, SIM-074 | T-2, T-3 | simulator adstock/Hill |
| T-105 | SIM §2.3, SIM-071, SIM-072, SIM-004 | — | revenue assembly, CSVs |
| T-106 | SIM-060, SIM-061 | DL-5 enabler; T-8 | `simulate/platform_bias.py` |
| T-107 | SIM-075, SIM §8 | DL-2 | `simulate/truth.py`, truth.json ×3 |
| T-108 | SIM-001, SIM-070..075 | DL-1 | CLI, `make simulate/validate-sim` |
| T-109 | A-9, W-3 | M1 exit | committed `data/synthetic/`, PR |
| T-201 | AD-001, EB-060(3) | — | dbt scaffold |
| T-202 | AD-001/002/020 | BP-D-03 | staging models |
| T-203 | AD-030, AD-040..044 | BP-D-19 | marts + dbt tests |
| T-204 | AD-030 | G-ARCH | `common/db.py` |
| T-205 | AD-050 | DL-7 feed | `scripts/export_marts.py` |
| T-301 | MD-020/021/030 | T-1, T-2 | `model/transforms.py` |
| T-302 | MD-070 | T-2/T-3 | transform sanity test |
| T-303 | MD-040, SPEC-04 §4 | A-6 | `PriorConfig`, `priors_synthetic.yaml` |
| T-304 | MD-001/002/020..022, EB-060(2) | T-9 | `model/mmm.py`, smoke test |
| T-305 | MD-051, EB-050 | BP-D-06 | `model/posterior_io.py` |
| T-306 | MD-071/072/074 | R-7 | `model/diagnostics.py` |
| T-307 | MD-050/051/071..073 | M2 exit, DL-8 | fit runner, `P-SA.parquet`, diag report |
| T-308 | MD-060 | DL-6 enabler | `model/elicit.py` |
| T-401 | VR-301..306, VR-310 | Q1, DL-2 | `validate/recovery.py` |
| T-402 | MD-050/051/071 | — | `P-SB/P-SC.parquet` + diag |
| T-403 | VR-401 | — | `validate/holdout.py`, holdout CSVs |
| T-404 | VR-601, EB-030 | — | `validate/baseline_ols.py` |
| T-405 | VR-602, MD-003 | O-3 boundary | `validate/crosscheck.py`, mapping doc |
| T-406 | VR §8, VR-703 | DL-2 | `validate/report.py`, RECOVERY_REPORT.md |
| T-407 | VR-701/702, EB-073 | R-5, T-6 | golden bands + tests |
| T-408 | GB-301..303 | E-4, A-8, DL-10 | SSOT generator + checker |
| T-409 | GB-501..503 | E-2, E-3, A-2 | `scripts/check_layer_order.py` |
| T-410 | M3 gates | E-2 unlock, DL-2 | M3 PR (the GB-501 anchor commit) |
| T-501 | AG-032, EB-071 | A-5 | intake fixtures |
| T-502 | AG-020/030/050, §5.2 | A-4 | `intake/standardize.py` |
| T-503 | AG-040..044/031/066 | R-6, A-4, DL-9 | `intake/anonymize.py`, manifest schema |
| T-504 | AG-060..066 | DL-9 | `intake/validate.py`, ingestion report |
| T-505 | AG-045, AD-044 | BP-D-05/11 | leak full mode, intake seed |
| T-506 | AD-044, §5.2 subset | BP-D-05 | dbt Layer R readiness |
| T-507 | AG-001/002 | R-1, ADR-001 | `docs/DATA_PERMISSION.md` |
| T-508 | AG-030..066, GB-202 | M4 core, ADR-002/003/004, DL-9 | `data/real_anon/`, manifest, flip |
| T-509 | MD-060/061 | §2.2 human split | elicitation skeleton + lint |
| T-510 | MD-041/060..062, GB-502 | E-3, DL-6 | freeze commit + tag `prior-freeze-v1` |
| T-601 | MD-050/051/074, GB-501/502 | Q2, DL-3 | `R.parquet`, `diag_R.md` |
| T-602 | VR-501/503 | R-2 centerpiece, DL-3 | `vr_prior_influence.png`, variant parquets |
| T-603 | VR-502/504 | R-9 | LOCO/no-promo artifacts |
| T-604 | VR-401, VR-602 | — | R holdout CSV, crosscheck addendum |
| T-605 | GB-302 | M5 exit, DL-3 | SSOT Layer R keys |
| T-701 | DC-201..204, DC-703/704 | Q3, R-4, T-7 | `decide/optimizer.py` |
| T-702 | DC-401, DC-701 | — | recovery addendum, `optimizer_regret_sb` |
| T-703 | DC-205/301/302/601 | Q3, DL-4 | `allocation_scenarios.csv`, ladder |
| T-704 | DC-501..504, DC-702 | Q4, T-8, DL-5 | `attribution_gap.csv`, dumbbell chart |
| T-705 | DC-701..705 | M6 exit, DL-4/5 | M6 PR + SSOT keys |
| T-801 | RB §7, GB-102 | E-5 | `report/style.py`, `format.py`, `captions.py` |
| T-802 | RB-201..205, RB-301/302 | DL-10 | 5 exec charts + tests |
| T-803 | AD-050, RB §5 | A-7/A-8, DL-3/4/5 | six exports, EXEC_SUMMARY.md |
| T-804 | RB §6/§6.1, GB §6, GB-503 | DL-9/10 | README.md, LIMITATIONS.md |
| T-805 | RB-401..406 | DL-7 | `ambo.pbix`, screenshots |
| T-806 | DL-1..10, VR-702 | Charter §4, M7 exit | release PR, tag v1.0 |

## 2. Reverse coverage (requirement family → tasks)

| Requirement family | Covered by | Gaps |
|---|---|---|
| SIM-001..004 | T-101, T-105, T-107, T-108 | none |
| SIM-030/031 | T-101, T-102 | none |
| SIM-060/061 | T-106 (+T-704 consumer) | none |
| SIM-070..075 | T-104, T-105, T-107, T-108 | none |
| AG-001/002 | T-507 | human-dependent |
| AG-020, AG-030..032 | T-502, T-503, T-501 | none |
| AG-040..045 | T-503, T-505, T-008 | BP-D-11 decision at ADR-003 |
| AG-050, §5.2..§5.4 | T-502, T-503 | none |
| AG-060..066 | T-504, T-508 | none |
| AG-070 | T-801 (captions), T-804 (README) | none |
| AD-001/002/020 | T-201, T-202, T-011 | none |
| AD-030 | T-203, T-204 | none |
| AD-040..044 | T-203, T-505, T-506 | none |
| AD-050 | T-205, T-703, T-704, T-803 | none |
| MD-001..003 | T-304, T-405 (confinement) | none |
| MD-020..022 | T-301, T-304, T-011 | none |
| MD-030 | T-301 | none |
| MD-040/041 | T-303, T-510 | none |
| MD-050/051 | T-004 (settings), T-305, T-307 | none |
| MD-060..062 | T-308, T-509, T-510 | human content |
| MD-070..074 | T-302, T-306, T-307, T-601 | none |
| MD-080..083 | T-304 (deterministics), T-401 (ROAS), T-703 (marginal) — response-curve export lands via T-406/T-803 | none |
| VR-301..310 | T-401, T-410 | none |
| VR-401 | T-403, T-604 | none |
| VR-501..504 | T-602, T-603 | none |
| VR-601/602 | T-404, T-405, T-604 | none |
| VR-701..703 | T-407, T-406, T-802 | none |
| VR §8 | T-406 | none |
| DC-201..205 | T-701, T-703 | none |
| DC-301/302 | T-703, T-801 (caption home) | none |
| DC-401 | T-702 | none |
| DC-501..504 | T-704 | none |
| DC-601 | T-703 | none |
| DC-701..705 | T-702, T-703, T-704, T-705 | none |
| RB-201..205, 301/302 | T-802 | none |
| RB-401..406 | T-805 | human-dependent |
| RB §5/§6/§6.1 | T-803, T-804 | none |
| RB §7 | T-801 | none |
| EB-001/002 | T-002, T-007 | none |
| EB-030 | T-002, T-010, T-404 (no-new-dep discipline) | none |
| EB-040/041 | T-004, T-005 | none |
| EB-050 | T-006, T-305 | none |
| EB-060/061 | T-009, T-304 (smoke), T-407 (goldens-in-CI) | none |
| EB-070..073 | T-010, T-501, T-407 | none |
| EB-080..082 | T-001, T-009, process rules | none |
| GB-101..103 | T-408 (tags in SSOT), T-801, T-804 | none |
| GB-201/202 | T-012 + event-driven ADRs | none |
| GB-301..303 | T-408 | none |
| GB-501..503 | T-409, T-410 (anchor), T-510 (freeze), T-804 (link) | none |
| GB §6 (LIMITATIONS) | T-804 (content), fed by T-602/603 (VR-501/504), T-011/settings (L=8) | none |
| Charter DL-1..10 | see [11 §4](11_ACCEPTANCE_CRITERIA.md) mapping | none |
| Charter Q1..Q4 | Q1: T-401..T-410 · Q2: T-601..T-605 · Q3: T-701..T-703/705 · Q4: T-704/705 | none |

**Coverage verdict:** every requirement family in SPEC-01..09 maps to at least one
WBS task; every WBS task cites at least one requirement. The only intentionally
uncovered spec content is out-of-scope by charter (O-1..O-8) and the "deliberately
does not exist" list (GB §8).

## 3. Maintenance rule

When a task is re-scoped or an ADR deviates from a spec: update this matrix row,
the task card, and (if the public API changed) [03_MODULES.md](03_MODULES.md) in
the same PR. A stale traceability matrix is treated as a failed Documentation Gate
at the next milestone.
