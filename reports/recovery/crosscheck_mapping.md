# pymc-marketing cross-check mapping (VR-602)

Installed `pymc_marketing.__version__`: **0.19.4**
(pin `0.19.4`).

Layer: `P-SB`. Channels: 6. Weeks: 104.

## Correlation gate

- Pearson of channel posterior-median ROAS: 0.9648
- Spearman of channel posterior-median ROAS: 0.8857
- Gate: both ≥ 0.8. **PASS**.
- Their NUTS divergences (not MD-071): 3050.

## Per-channel median ROAS

| Channel | ambo (raw PyMC) | pymc-marketing |
|---|---:|---:|
| `search_brand` | 3.2326 | 3.7619 |
| `search_generic` | 1.3822 | 1.3532 |
| `meta` | 1.5068 | 1.4118 |
| `display_video` | 3.2454 | 2.9361 |
| `print_regional` | 1.5187 | 1.4955 |
| `radio` | 1.5950 | 1.4615 |

## Transform and prior mapping

| Element | ambo | pymc-marketing 0.19.4 | Status | Note |
|---|---|---|---|---|
| adstock form | normalized geometric, L=8, causal (MD-020) | GeometricAdstock(l_max=8, normalize=True, mode=After) | matched | alpha is λ; Beta(2, 4) on both. |
| saturation form | Hill a^s/(a^s+K^s) then ×β (MD-021) | HillSaturation: β × hill_function(x, slope, kappa) | matched | slope=s, kappa=K, saturation_beta=β. Same closed form. |
| adstock then Hill | adstock_convolve then hill_saturation | adstock_first=True | matched |  |
| λ / alpha prior | Beta(2, 4) | Prior('Beta', alpha=2, beta=4, dims=channel) | matched |  |
| K / kappa prior | Gamma(shape=2, rate=1.3) | Prior('Gamma', alpha=2, beta=1.3, dims=channel) | matched | PyMC Gamma beta is the rate. |
| s / slope prior | Truncated Gamma(3, 2) on [0.3, 3.0] | untruncated Gamma(3, 2) on saturation_slope | unmatched | Prior('Truncated', dist=Prior('Gamma', ...)) names the inner RV; API refuses it. |
| β prior | HalfNormal(0.15) | Prior('HalfNormal', sigma=0.15, dims=channel) | matched |  |
| intercept | Normal(1.0, 0.3) on mean-scaled revenue | Prior('Normal', mu=1.0, sigma=0.3) after FixedScaling | matched |  |
| observation noise | HalfNormal(0.1) on scaled revenue | likelihood Normal with HalfNormal(0.1) sigma | matched |  |
| scaling | MD-030: revenue mean; per-channel mean of positive spend weeks | FixedScaling with those exact ScaleFactors | matched | Default MMM max-abs is not used. |
| linear trend t/T | τ ~ Normal(0, 0.1) times t/T | t_over_t as a control; gamma_control μ=0 σ=0.1 at that slot | matched | MMM has no dedicated τ; HSGP time-varying intercept is a different model. |
| yearly Fourier | order 4, period 52.18 weeks, non-centered (ADR-005) | sin/cos injected as controls with Normal(0, 0.15) | unmatched | yearly_seasonality is day-of-year/365.25 + Laplace; no 52.18 knob. |
| promo / advent / jan | separate Normal priors with distinct μ, σ | same three flags as controls; per-slot μ, σ arrays on gamma_control | matched | Controls are unscaled in MMM; flags are already 0/1. |
| NUTS init | jitter+adapt_diag (MD-050) | adapt_diag | unmatched | jitter+adapt_diag trips 0<alpha<=1. Raising accept did not help. |
| MMM class | raw PyMC in ambo.model.mmm | pymc_marketing.mmm.MMM (legacy in 0.19.4) | matched | VR-602 names MMM. Multidimensional MMM is the 0.20 replacement; not used. |

## What this does and does not prove

A high correlation says two independently implemented Hill-adstock MMMs
rank channels similarly on S-B. It is not a claim that pymc-marketing is
calibrated to truth (that is SPEC-05 §3 against `truth.json`), and it is
not a reason to replace the raw-PyMC model. Unmatched rows above are API
limits, not silent deviations (A-1).
