# SPEC-01 — Ground-Truth Simulator (Layer P)

Defines the EXACT data-generating process (DGP) for "AlpenTrek GmbH", a fictional
Graz-based outdoor-gear e-tailer. Everything here is DISCLOSED by design — the point
is that truth is known. Requirement IDs: `SIM-xxx`. Code in `src/ambo/simulate/`.
Epistemic tag of outputs: **GROUND-TRUTH**.

---

## 1. Principles

- SIM-001: Fully deterministic given (scenario config, seed). Seeds fixed per scenario
  (§5). Two runs ⇒ byte-identical CSVs.
- SIM-002: All parameters live in `config/scenarios/<scenario>.yaml`; §4 tables are the
  authoritative values (YAML wins if they ever diverge — but keep them identical).
- SIM-003: Simulator and model share NO code (AGENTS T-3; enforced by an import test).
  The simulator implements its own adstock/Hill functions with independent unit tests.
- SIM-004: Outputs per scenario, under `data/synthetic/<scenario>/`:
  - `media_weekly.csv` — `week_start (ISO Monday), channel, spend_eur, impressions, platform_conversions, platform_revenue_eur` (§6)
  - `outcome_weekly.csv` — `week_start, revenue_eur, orders, promo_flag`
  - `truth.json` — every DGP parameter + derived per-channel truths (§8)
  All three are COMMITTED (small).

## 2. The DGP (implement exactly; weekly index t = 1…T)

### 2.1 Baseline demand

`base_t = B0 × (1 + g)^t × season_t × promo_mult_t`

- B0 = 60,000 € expected weekly base revenue; g = 0.001 (≈ +0.1%/week trend).
- `season_t`: multiplicative index built as: 1
  + 0.55 × advent(t)   (advent = 1 in the 4 ISO weeks before and incl. the week of Dec 24)
  + 0.25 × schulbeginn(t) (1 in the 2 weeks around Styrian school start, early Sep)
  + 0.15 × spring(t)   (1 in ISO weeks 14–22, hiking-season ramp)
  − 0.20 × jan_dip(t)  (1 in ISO weeks 2–5)
  − 0.10 × summer_lull(t) (1 in ISO weeks 29–33)
  Window definitions computed from the real Austrian calendar for the simulated years
  (the `holidays` package + fixed ISO-week rules above; unit-tested).
- `promo_flag_t`: 1 in 10 pre-scheduled promo weeks/year (list in scenario YAML —
  aligned to Black Friday week, 2 Advent weeks, 2 spring weeks, 5 others spread);
  `promo_mult_t = 1.15` when flagged, else 1.0.

### 2.2 Media effect per channel c

- Geometric adstock: `a_{c,t} = x_{c,t} + λ_c × a_{c,t−1}`, a_{c,0}=0, where x = spend €.
- Hill saturation on the ADSTOCKED spend: `h_{c,t} = a_{c,t}^{s_c} / (a_{c,t}^{s_c} + K_c^{s_c})`.
- Contribution: `m_{c,t} = β_c × h_{c,t}` (a€/week at full saturation = β_c).

### 2.3 Revenue

`revenue_t = base_t + Σ_c m_{c,t} + ε_t`, `ε_t ~ Normal(0, σ)`, σ = 0.04 × mean(base).
Clip at ≥ 0 (must never bind in practice — gate SIM-072).
`orders_t = round(revenue_t / AOV_t)`, AOV_t = 95 € + 10 € × advent(t) (descriptive only).

## 3. Spend patterns (per channel; all spends in whole €, drawn once per scenario seed)

| Channel | Pattern |
|---------|---------|
| `search_brand` | Always-on: Normal(700, 60) per week, floor 400 |
| `search_generic` | Always-on with seasonal planning: Normal(2500, 200) × (1 + 0.5×advent + 0.2×spring) |
| `meta` | Always-on pulsed: Normal(2000, 300); every 6th week ×1.8 (campaign pushes) |
| `display_video` | Always-on: Normal(1200, 150) |
| `print_regional` | Flighted: 0 in ~70% of weeks; bursts of 2 consecutive weeks at Normal(5000, 500), 8 bursts/year, 3 fixed in Advent/Schulbeginn windows, rest seeded-random |
| `radio` | Flighted: 0 in ~75% of weeks; 3-week bursts at Normal(3500, 300), 5 bursts/year, 2 fixed in Advent |

- SIM-030: In scenario S-B and S-C the seasonal multipliers on spend are STRONGER
  (advent factor 0.5→0.9 for search_generic/meta; all print/radio bursts anchored to
  demand peaks) — this creates the deliberate spend↔season collinearity.
- SIM-031: Spend series unit tests: annual totals within ±10% of the design means ×
  weeks; flighting share of zero-weeks within ±10 pp of design.

## 4. True media parameters (the numbers the model must recover)

| Channel | λ_c (decay) | half-life (wk, derived) | K_c (€, half-sat adstock) | s_c (shape) | β_c (€/wk max) |
|---------|------------|------------------------|---------------------------|-------------|----------------|
| search_brand | 0.10 | 0.30 | 800 | 1.2 | 6,000 |
| search_generic | 0.20 | 0.43 | 3,000 | 1.0 | 15,000 |
| meta | 0.35 | 0.66 | 2,500 | 0.9 | 12,000 |
| display_video | 0.50 | 1.00 | 2,000 | 1.1 | 6,000 † |
| print_regional | 0.60 | 1.36 | 4,000 | 1.3 | 8,000 |
| radio | 0.55 | 1.16 | 3,500 | 1.2 | 5,000 |

† In scenario **S-C**, `display_video` β = **0** (the zero-effect channel; spend
pattern unchanged). Everything else identical to S-B.

## 5. Scenarios

| ID | Weeks | Collinearity (SIM-030) | Zero-effect channel | Seed | Purpose |
|----|-------|------------------------|--------------------|------|---------|
| S-A | 156 | OFF | none | 101 | Clean identification — the model's best case |
| S-B | 104 | ON | none | 202 | Realistic: 2 years, spend follows demand calendar |
| S-C | 78 | ON | display_video | 303 | Hostile: short + collinear + a channel that does nothing |

## 6. Simulated platform reporting (for the attribution-gap module, Charter §7)

- SIM-060: `platform_conversions/revenue` per channel are generated with KNOWN
  over-credit: `platform_revenue_{c,t} = m_{c,t} × φ_c + θ_c × base_t × share_c` where
  φ_c (own-effect inflation) and θ_c (demand-claiming leak) are:
  search_brand φ=1.1, θ=0.05; search_generic φ=1.3, θ=0.01; meta φ=1.5, θ=0.01;
  display_video φ=2.0, θ=0.005; print/radio: no platform reporting (NULL — offline).
  `share_c` = channel's share of total spend that week. Parameters go into truth.json.
- SIM-061: This makes "platform ROAS vs true ROAS" a KNOWN quantity in Layer P — the
  attribution-gap module must recover the direction and rough magnitude of φ
  distortions (gate in SPEC-06 §7).

## 7. Simulator gates (`make simulate` then `make validate-sim`)

- SIM-070: Determinism: two runs byte-identical.
- SIM-071: Decomposition audit: base + Σ contributions + noise = revenue exactly
  (re-summed from internal components, tolerance 1e-6).
- SIM-072: Plausibility: no negative revenue pre-clip; media share of total revenue
  ∈ [15%, 45%] annually (else the advertiser caricature is off); noise share of
  variance ∈ [2%, 10%].
- SIM-073: Seasonality: the max revenue week of each simulated year falls in the
  Advent window.
- SIM-074: Adstock closed-form test: for constant spend x, a_t → x/(1−λ) (geometric
  series); Hill(K) = 0.5 exactly.
- SIM-075: truth.json completeness: every §4/§6 parameter + derived quantities (§8)
  present; schema-validated (pydantic model committed).

## 8. `truth.json` derived quantities (computed by the simulator, used by SPEC-05)

Per channel: true total contribution (a€ and share), **true average ROAS** =
Σm_c / Σx_c over the full window, true marginal ROAS at mean historical weekly spend
(analytic derivative of β·Hill at mean adstock), response-curve sample (contribution
at 21 spend grid points 0…2×max weekly spend, at steady-state adstock), platform
ROAS (from §6). Plus scenario metadata (seed, weeks, flags).
