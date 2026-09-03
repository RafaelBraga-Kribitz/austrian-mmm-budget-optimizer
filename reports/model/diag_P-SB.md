# Diagnostics — P-SB

Profile: `standard` (all-green).

- MD-073 rung 2 (ADR-005): non-centered Fourier; reported names gamma_sin/gamma_cos.
- MD-073 rung 1 applied: target_accept raised to 0.95 (Settings.sampler unchanged; not an MD-050 edit).
- MD-073 rung 1 extended (ADR-011): target_accept raised to 0.99 after 0.95 still left divergences (Settings.sampler unchanged; ADR-010 superseded).

| Gate | Threshold | Statistic | Result |
|------|-----------|-----------|--------|
| R-hat | < 1.01 | 1.004 | PASS |
| ESS_bulk | > 400 | 1385 | PASS |
| ESS_tail | > 400 | 1407 | PASS |
| divergences | <= 0 | 0 | PASS |
| BFMI | > 0.3 | 0.7484 | PASS |
| PPC_90 | >= 85% | 0.9519 | PASS |

PPC plot: `ppc_P-SB.png`.
