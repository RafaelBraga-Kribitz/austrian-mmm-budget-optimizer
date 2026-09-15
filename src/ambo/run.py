"""Pipeline CLI: ``python -m ambo.run layer_p`` regenerates every Layer P artifact."""

from __future__ import annotations

import argparse
import json
import sys

from ambo.config import (
    DATA_DIR,
    HOLDOUT_START_WEEK,
    POSTERIOR_NC,
    REPORTS_DIR,
    SAMPLER_CHAINS,
    SAMPLER_DRAWS,
    SAMPLER_SEED,
    SAMPLER_TUNE,
)
from ambo.data import LayerRUnavailable, load_layer_r


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ambo.run")
    parser.add_argument(
        "command",
        choices=("layer_p", "simulate", "fit", "report", "layer_r"),
        help="layer_p runs simulate → fit → evaluate → optimise → report",
    )
    parser.add_argument("--draws", type=int, default=SAMPLER_DRAWS)
    parser.add_argument("--tune", type=int, default=SAMPLER_TUNE)
    parser.add_argument("--chains", type=int, default=SAMPLER_CHAINS)
    parser.add_argument("--seed", type=int, default=SAMPLER_SEED)
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "layer_r":
        try:
            load_layer_r()
        except LayerRUnavailable as exc:
            print(exc, file=sys.stderr)
            return 2
        return 0
    if args.command == "simulate":
        return _simulate()
    if args.command == "fit":
        return _fit(args.draws, args.tune, args.chains, args.seed, args.progress)
    if args.command == "report":
        return _report()
    _simulate()
    fit_rc = _fit(args.draws, args.tune, args.chains, args.seed, args.progress)
    report_rc = _report()
    return 0 if fit_rc == 0 and report_rc == 0 else 1


def _simulate() -> int:
    from ambo.synth import generate, write_artifacts

    sim = generate()
    path = write_artifacts(sim)
    print(f"Wrote Layer P artifacts under {path}")
    return 0


def _fit(draws: int, tune: int, chains: int, seed: int, progress: bool) -> int:
    from ambo.diagnostics import run_diagnostics, write_diag_report
    from ambo.model import build_model, sample_model, scale_frame
    from ambo.synth import generate, modeling_frame

    sim = generate()
    frame = modeling_frame(sim)
    scaled, factors = scale_frame(frame)
    model = build_model(scaled)
    idata = sample_model(
        model, draws=draws, tune=tune, chains=chains, seed=seed, progressbar=progress
    )
    POSTERIOR_NC.parent.mkdir(parents=True, exist_ok=True)
    idata.to_netcdf(POSTERIOR_NC)
    (DATA_DIR / "scale_factors.json").write_text(
        json.dumps(
            {
                "revenue_mean": factors.revenue_mean,
                "spend_means": factors.spend_means,
                "channels": list(factors.channels),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    diag = run_diagnostics(idata)
    write_diag_report(diag, idata, layer="P")
    print(f"Wrote posterior {POSTERIOR_NC} (all_green={diag.all_green})")
    return 0 if diag.all_green else 1


def _report() -> int:
    import arviz as az

    from ambo.baselines import fit_ols_baseline
    from ambo.evaluate import compute_recovery, holdout_table, stacked_posterior
    from ambo.optimize import historical_max, historical_means, optimize_budget
    from ambo.report import write_attribution_gap, write_recovery_report, write_ssot
    from ambo.synth import generate, modeling_frame

    if not POSTERIOR_NC.exists():
        print(f"missing posterior {POSTERIOR_NC}; run fit first", file=sys.stderr)
        return 1
    sim = generate()
    frame = modeling_frame(sim)
    idata = az.from_netcdf(POSTERIOR_NC)
    scales = _load_scales()
    recovery = compute_recovery(frame, idata, scales, sim.truth)
    holdout = holdout_table(frame, idata, scales, start_week=HOLDOUT_START_WEEK)
    holdout_dir = REPORTS_DIR / "model"
    holdout_dir.mkdir(parents=True, exist_ok=True)
    holdout.to_csv(holdout_dir / "holdout_P.csv", index=False, lineterminator="\n")
    roas = {row.channel: row.roas_median for row in recovery.channels}
    ols = fit_ols_baseline(frame, bayesian_roas=roas)
    draws = stacked_posterior(idata)
    allocation = optimize_budget(historical_means(frame), historical_max(frame), draws, scales)
    write_recovery_report(recovery, holdout, ols, allocation, revenue_mean=scales.revenue_mean)
    write_ssot(recovery, holdout, allocation, scales.revenue_mean)
    write_attribution_gap(sim.media, recovery)
    print(f"Wrote reports under {REPORTS_DIR} (all_green={all(recovery.gates.values())})")
    return 0 if all(recovery.gates.values()) else 1


def _load_scales():
    from ambo.model import ScaleFactors

    payload = json.loads((DATA_DIR / "scale_factors.json").read_text(encoding="utf-8"))
    return ScaleFactors(
        revenue_mean=float(payload["revenue_mean"]),
        spend_means={k: float(v) for k, v in payload["spend_means"].items()},
        channels=tuple(payload["channels"]),
    )


if __name__ == "__main__":
    sys.exit(main())
