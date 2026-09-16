# Limitations

What this package does and does not prove, in the order a reviewer would ask.
Numbers are deliberately absent here; every figure lives in the artifacts named,
and README.md carries the ones that matter.

## 1. Recovery on a disclosed data-generating process

Layer P proves that the sampler recovers a truth of the same family the model
assumes: geometric adstock, Hill saturation, an additive baseline. Passing it bounds
implementation error (a reversed convolution, a scaling bug, a leaking holdout). It
says nothing about model-misspecification error on a real advertiser, whose response
may not be Hill-shaped and whose carry-over may not be geometric. The real next step
is calibration against lift tests (geo experiments or channel holdouts), which the
charter keeps out of scope for this version.

Artifacts: `reports/layer_p/response_curve_recovery.png`, `response_curve_metrics.csv`,
`parameter_recovery.csv`, `contribution_recovery.csv`.

## 2. The effect-times-saturation trade-off

Effect size and half-saturation point trade off against each other: a curve that rises
higher but saturates later fits the same observed weeks. On Layer P the medians of both
sit above the truth for every channel, and one channel's revenue share falls just
outside its interval. Recovery is therefore judged on curves at observed spend and on
shares, which are what a budget decision uses, not on point parameters. README.md,
section "Proof on known truth", states the direction and size of this bias from the
artifacts.

## 3. No real client data yet, and what anonymisation will change

Layer R runs on Robyn's simulated weekly dataset (`data/README.md`): five named
channels in money units whose currency the authors do not name. Shares, ROAS ratios,
the breakeven test and the reallocation shares are meaningful; the amounts are not
euros. No Austrian client data was used. When a client drop arrives it is processed
only with written permission and through the anonymisation protocol in
`docs/specs/SPEC-02_agency_data_pipeline.md`: independent rescaling factors preserve
all ratios among spends, all ratios among revenues, response-curve shapes, adstock
timing, allocation shares and the relative ranking of channels, and destroy absolute
euro amounts and absolute ROAS. Absolute ROAS will then not be interpretable and the
README will say so.

## 4. Short windows and prior-dominated parameters

The public file has 208 weeks; a real client window is expected to be shorter. On both,
channels with few active weeks carry wide intervals on decay, half-saturation and
slope, and those parameters lean on the priors. `reports/layer_r/posterior_summary.csv`
shows which. A prior-sensitivity refit (weak versus elicited priors, SPEC-05 VR-501)
is not implemented in this version; until it is, the honest reading is that for thinly
flighted channels the response curve beyond observed spend is largely the prior.

## 5. The gain is an in-sample counterfactual

The reallocation gain assumes the fitted response curves hold at the new spend levels,
that competitors do not react, that creative quality and cross-channel synergies stay
as they were, and that a constant weekly spend reaches its adstock steady state. Every
channel is bounded to plus or minus fifty percent of its current spend, and the extra
budget scenarios add the increase on top of that bound. The decision rule in
`reports/layer_d/decision.json` refuses shifts whose marginal return is not above
breakeven at the lower bound of the interval, and the breakeven itself rests on a
contribution-margin assumption stated in `src/ambo/configs/layer_r.yaml` (STATUS
D-28: forty percent until a real client figure exists).

## 6. Brand search

Brand search correlates with revenue because it is demand, not a cause of it. The
charter therefore models it but never lets the optimiser move budget into it. None of
the five channels in this version is a brand-search line, so the exclusion has nothing
to attach to yet; at client intake it becomes binding wherever a brand-search channel
exists (ADR-008).

## 7. Promotions and other omitted drivers

The demo data carries no promotion calendar; the model uses one control (public
holiday weeks on Layer P, competitor sales on Layer R). On real data the promotion
calendar is reconstructed from records and memory, tagged as a judgment input, and its
influence checked by refitting without it. Price changes, distribution, weather and
competitor advertising are not modelled and land in the baseline or in whichever
channel happens to move with them.

## 8. Weekly grain and truncated carry-over

Weekly national data hides within-week dynamics and cannot separate channels whose
spend moves together; the intervals widen accordingly. The adstock is truncated at
thirteen lags, which caps measurable carry-over at roughly a quarter and makes decay
rates near one unidentifiable by construction.

## 9. Platform-reported numbers are modelled objects

On Layer P the platform report is generated by two assumptions about how dashboards
over-credit: an inflation of the channel's own effect and a claim on baseline demand in
proportion to spend share, with offline media receiving nothing. The attribution gap
therefore tests the direction and ordering of the distortion, not its magnitude on any
real platform. On real data the platform numbers are the object of study, never a
calibration target.

## 10. Holdout honesty

The holdout is a conditional forecast with actual spend, judged by MAPE and by
90 percent interval coverage against a seasonal-naive and a ridge baseline. On the
public data the model loses on point error to ridge and its intervals are wider than
nominal; on the synthetic data it wins on point error and its intervals are slightly
too narrow. Both are reported as they come out in README.md.

## 11. Reproducibility

Every artifact regenerates from three commands. With the same machine, package versions
and seed the runs are identical; across machines the sampler's draws differ and only
summary statistics agree, within sampling error. When a diagnostic gate fails, the
sampler settings are raised in a fixed, recorded order and every attempt is written to
`diagnostics.json`; nothing is retuned silently. Draws are never compared by checksum.
