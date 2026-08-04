# SPEC-02 — Agency Data Pipeline (Layer R): Permission, Anonymization, Intake

Turns private agency exports into publishable REAL-ANON weekly series. Requirement
IDs: `AG-xxx`. Code in `src/ambo/intake/`. This spec is also a published document —
the anonymization protocol being public (minus secrets) is part of the portfolio's
governance story.

---

## 1. Legal/ethical gate (blocks everything else in this spec)

- AG-001: Before any private file is processed: written permission from the data
  owner (former agency and/or client, as contracts require) covering "publication of
  anonymized, rescaled aggregates for portfolio purposes". Stored PRIVATELY (never in
  repo). The repo gets `docs/DATA_PERMISSION.md` stating: permission exists, from whom
  in role terms ("the advertiser's managing director"), date, and scope — no names.
- AG-002: If permission cannot be confirmed by end of M4 ⇒ Charter §7 degradation
  path, decided by ADR. No gray-zone processing "while we wait".

## 2. What the human collects from the archive (the "private drop")

Target inputs (any subset; the pipeline adapts, see §5.3):

| Input | Typical source | Minimum columns |
|-------|---------------|-----------------|
| Media spend by channel over time | agency billing / platform exports | date or week, channel, spend |
| Platform performance exports | Google Ads, Meta Ads Manager | date, campaign, impressions, clicks, conversions, conv. value |
| Outcome series | client shop backend / GA e-commerce | date, revenue (and/or orders, leads) |
| Promo/price calendar | media plans, emails, memory | start, end, description |
| Offline media plans | insertion orders (print/radio/OOH) | period, medium, gross cost |

- AG-020: The private drop lives at a path OUTSIDE the repo, referenced only via env
  var `AMBO_PRIVATE_DROP` (e.g. `D:/private/ambo_drop/`). The repo's `.env.example`
  documents the variable; code fails fast with a clear message if unset when intake
  targets run.

## 3. Pipeline architecture (privacy by construction)

- AG-030: Two-stage design:
  1. `python -m ambo.intake.standardize` — reads the private drop, maps to the §5
     canonical schema, writes STILL-PRIVATE intermediates into `$AMBO_PRIVATE_DROP/staged/`.
  2. `python -m ambo.intake.anonymize` — applies §4, writes the PUBLIC outputs into
     `data/real_anon/` (committed).
  Only stage-2 outputs may ever enter the repo.
- AG-031: `data/real_anon/` files: `media_weekly.csv`, `outcome_weekly.csv`,
  `promo_calendar.csv`, `INTAKE_MANIFEST.yaml` (schema §5.4).
- AG-032: The repo's test fixtures for intake code are SYNTHETIC lookalikes generated
  by a fixture script (clearly labeled), never excerpts of the private drop.

## 4. Anonymization recipe (exact)

- AG-040: **Identity:** client becomes "Client A, an Austrian <sector> advertiser"
  (sector chosen at intake, as coarse as needed). No brand, product, city, or URL
  strings anywhere. Campaign names are dropped after channel mapping (§5.2).
- AG-041: **Dual-factor rescaling:** the human draws two secret factors ONCE:
  `k_spend ~ Uniform(0.4, 2.5)` and `k_rev ~ Uniform(0.4, 2.5)` independently
  (rejection rule: redraw if |k_spend − k_rev| < 0.15, so ROAS is not ≈ preserved).
  ALL monetary spend values × k_spend; ALL revenue/conversion-value values × k_rev;
  round to whole a€. Factors recorded only in the human's private notes.
  Consequences (state in LIMITATIONS): absolute a€ and absolute ROAS are masked;
  preserved and therefore publishable: all ratios among spends, all ratios among
  revenues, response-curve SHAPES, adstock timing, allocation SHARES, relative ROAS
  ranking across channels, and the platform-vs-MMM gap RATIO per channel.
- AG-042: **Counts** (impressions, clicks, platform conversions) × k_spend as well
  (keeps platform CPA/ROAS internally consistent in masked units), rounded.
- AG-043: **Dates:** kept (seasonality is analytically essential). Weekly aggregation
  (§5.1) already coarsens.
- AG-044: **PII scrub checklist** (stage 2 hard-fails if violated): no person names,
  emails, phone numbers; no search-term/keyword strings; no URLs; no geo finer than
  Bundesland; no free-text fields at all in public outputs — enforced by schema
  (public CSVs have ONLY the whitelisted columns of §5).
- AG-045: **Leak scan:** `scripts/leak_scan.py` runs in CI over the whole repo + git
  staged changes: regex for the private-drop path, currency-formatted numbers in
  committed notebooks against a blocklist file (privately maintained list of the ~20
  most distinctive real values, itself NOT in the repo — the script reads it from
  `$AMBO_PRIVATE_DROP/blocklist.txt` when available and skips gracefully in CI),
  email/URL patterns in `data/real_anon/`. Local pre-commit hook runs the full scan;
  CI runs the pattern subset.

## 5. Canonical schema (public outputs)

### 5.1 Weekly aggregation

- AG-050: Daily inputs aggregate to ISO weeks (Mon–Sun, Europe/Vienna). Weeks at the
  window edges that are partial are DROPPED (not padded). Spend: sum. Revenue: sum.
  Counts: sum.

### 5.2 Channel taxonomy (fixed; map every campaign to exactly one)

`search_brand`, `search_generic`, `meta`, `display_video`, `print_regional`, `radio`,
`other` — mapping rules written per source during intake into the manifest (e.g.,
"campaigns matching brand-term lists → search_brand"). `other` must stay < 10% of
total spend (AG-062) or the taxonomy is revisited via ADR. Channels absent from the
client's mix simply don't appear (the model handles any subset — SPEC-04 is
channel-list-driven).

### 5.3 Public files

| File | Columns (exact; nothing else permitted) |
|------|------------------------------------------|
| `media_weekly.csv` | `week_start, channel, spend_aeur, impressions, clicks, platform_conversions, platform_conv_value_aeur` (NULLs allowed for offline channels) |
| `outcome_weekly.csv` | `week_start, revenue_aeur, orders` |
| `promo_calendar.csv` | `week_start, promo_flag (0/1), promo_type ('price'\|'content'\|'unknown')` — reconstructed; tag CALIBRATED |

### 5.4 `INTAKE_MANIFEST.yaml`

Records (public, no secrets): window covered, channels present, weeks count, mapping
rule summaries, aggregation decisions, known data issues (e.g., "Meta export missing
2023-W07..W09 — spend reconstructed from invoices, flagged `reconstructed=true`" —
such flags get their own column if used), permission doc reference, anonymization
recipe version. NOT recorded: factors, client identity, absolute totals.

## 6. Validation gates (`make validate-intake`, report to `reports/ingestion/`)

- AG-060: Continuity: gapless ISO weeks within the covered window per file; window
  length ≥ 52 weeks (else Layer R is descriptive-only — ADR + Charter §7 consult).
- AG-061: Consistency: every media week exists in outcome weeks and vice versa.
- AG-062: Shares: `other` channel < 10% of spend; no single week > 15% of total-window
  spend (spike = likely unit or dedup error); zero-spend weeks allowed only for
  flighted channels (print_regional, radio) and `search_*` must be > 0 in ≥ 95% of
  weeks (always-on sanity — relax via ADR if the client truly paused).
- AG-063: Ratio sanity (scale-free, so computable despite masking): weekly
  revenue/spend ratio within [1.5, 50] for all weeks (outside ⇒ mapping or unit bug);
  platform CTR (clicks/impressions) within [0.1%, 15%] where present.
- AG-064: Seasonality visibility: if the window includes a December, the Dec revenue
  mean must exceed the annual weekly mean (Austrian retail expectation for this
  client type; if the client is genuinely counter-seasonal, ADR with sector note).
- AG-065: PII scrub (AG-044) automated checks pass; leak scan clean.
- AG-066: Manifest complete (schema-validated, pydantic).

## 7. What gets published about this pipeline

- AG-070: This spec file, the manifest, `docs/DATA_PERMISSION.md`, and a README
  paragraph: "Real client data is used with permission, anonymized by a published
  protocol (SPEC-02): identity removed, channels generalized, all monetary values
  rescaled by undisclosed independent factors. Analyses use only masking-invariant
  quantities." — wording lives in `ambo/report/captions.py` (single caption source).
