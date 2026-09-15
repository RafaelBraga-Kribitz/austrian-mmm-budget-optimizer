# Austrian MMM and Budget Optimizer

For one advertiser: which channels contributed incrementally, how far off were
the platform dashboards, and what does a reallocation of the *same* budget
return — with a 90% interval on every claim.

This repository ships **Layers P + D** on a disclosed synthetic Austrian
e-tailer (Charter §7 / ADR-012). There is no real agency drop here; Layer R is
refused rather than invented.

## What you get

- A five-channel weekly MMM in raw PyMC (geometric adstock with MD-020
  normalised weights, Hill saturation, trend, yearly Fourier, promo / Advent /
  January dummies plus an Austrian holiday indicator).
- A simulator that does **not** share transform code with the model, so recovery
  is evidence.
- Recovery, holdout vs a seasonal-naive baseline, OLS+HC1, a budget optimiser
  with a 1.3× historical-max guard, and an attribution-gap table that treats
  platform ROAS as the object of study.

Channel names (STATUS D-05): TV, Radio, Print, Paid Search, Paid Social.

## Reproduce

```bash
uv sync --python 3.11
uv run pytest -m "not slow"
uv run python -m ambo.run simulate   # data/synthetic/
uv run python -m ambo.run layer_p    # fit + reports (slow; NUTS)
```

Numbers in `reports/NUMERIC_SSOT.md` are generated, not typed. If a chart shows
a ROAS, contribution, or gain without its 90% HDI, the chart is wrong.

Read `docs/LIMITATIONS.md` before the recovery table. Layer P recovery on the
reported posterior is **RED** (see `reports/recovery/RECOVERY_REPORT.md` and
`reports/NUMERIC_SSOT.md`); MD-071 fails by one divergence
(`reports/model/diag_P.md`). Those files are generated, not typed.
