"""Command-line entry point.

    python -m ambo.run layer_p [--config path] [--out dir] [--data dir]

Layer P regenerates the synthetic data, fits the model, writes diagnostics, the
recovery tables and charts, and the holdout comparison, all deterministically.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import warnings
from importlib import resources
from pathlib import Path

import pandas as pd
import yaml

from ambo import __version__, diagnostics, evaluate, model, synth
from ambo.model import fit_with_ladder  # noqa: F401  (re-exported for callers)
from ambo.plots import charts

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def load_config(path: str | Path | None, default: str) -> dict:
    if path is None:
        with resources.files("ambo.configs").joinpath(default).open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def run_layer_p(config_path=None, out_dir=None, data_dir=None) -> dict:
    t_start = time.time()
    config = load_config(config_path, "layer_p.yaml")
    out = Path(out_dir or config["output_dir"])
    data_path = Path(data_dir or config["data_dir"])
    out.mkdir(parents=True, exist_ok=True)
    source = f"{config['title']}; {config['synthetic']['weeks']} weeks; python -m ambo.run layer_p"

    # 1. data with disclosed truth
    result = synth.generate(config)
    synth.write(result, data_path)
    data, truth = result.data, result.truth

    # 2. full fit and diagnostics
    md = model.prepare(data, config)
    idata, info, diag = fit_with_ladder(md, config)
    diag.update({"layer": config["layer"], "weeks": md.n_weeks, "fit": info})
    diagnostics.write(diag, out / "diagnostics.json")
    model.summary_table(idata).to_csv(
        out / "posterior_summary.csv", index=False, lineterminator="\n"
    )
    post = model.extract(idata)
    model.write_posterior(post, md, out)
    contribs = model.media_contributions(post, md)

    # 3. recovery and attribution gap
    recovery = evaluate.parameter_recovery(post, md, truth)
    recovery.to_csv(out / "parameter_recovery.csv", index=False, lineterminator="\n")
    charts.parameter_recovery(recovery, out / "parameter_recovery.png", source)
    contribution = evaluate.contribution_recovery(contribs, md, truth)
    contribution.to_csv(out / "contribution_recovery.csv", index=False, lineterminator="\n")
    charts.contribution_recovery(contribution, out / "contribution_recovery.png", source)
    gap = evaluate.attribution_gap(data, contribs, md, truth)
    gap.to_csv(out / "attribution_gap.csv", index=False, lineterminator="\n")
    charts.attribution_gap(gap, out / "attribution_gap.png", source)

    # 4. holdout against the two baselines
    metrics, preds, hold_info, hold_idata = evaluate.holdout(data, config)
    metrics.to_csv(out / "holdout_metrics.csv", index=False, lineterminator="\n")
    preds.to_csv(out / "holdout_predictions.csv", index=False, lineterminator="\n")
    charts.holdout(preds, metrics, out / "holdout.png", source)
    hold_diag = hold_info.pop("diagnostics")
    hold_diag.update({"layer": config["layer"], "weeks": int(config["holdout"]["train_weeks"]),
                      "fit": hold_info})
    diagnostics.write(hold_diag, out / "holdout_diagnostics.json")

    numbers = {
        "layer": config["layer"],
        "weeks": md.n_weeks,
        "parameters_total": int(len(recovery)),
        "parameters_covered": int(recovery["covered"].sum()),
        "coverage_share": float(recovery["covered"].mean()),
        "channels_share_covered": int(contribution["covered"].sum()),
        "largest_gap_channel": str(gap.loc[gap["abs_gap_pp"].idxmax(), "channel"]),
        "largest_gap_pp": float(gap["abs_gap_pp"].max()),
        "holdout": metrics.to_dict(orient="records"),
        "diagnostics_pass": bool(diag["pass_all"]),
        "holdout_diagnostics_pass": bool(hold_diag["pass_all"]),
        "elapsed_seconds": round(time.time() - t_start, 1),
        "sampler": info["sampler"],
        "versions": _versions(),
    }
    with open(out / "run_info.json", "w", encoding="utf-8") as fh:
        json.dump(numbers, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return numbers


def _versions() -> dict:
    import arviz
    import numpy
    import pymc

    out = {
        "ambo": __version__,
        "python": platform.python_version(),
        "pymc": pymc.__version__,
        "arviz": arviz.__version__,
        "numpy": numpy.__version__,
        "pandas": pd.__version__,
    }
    try:
        import nutpie

        out["nutpie"] = nutpie.__version__
    except ImportError:
        pass
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ambo.run")
    parser.add_argument("layer", choices=["layer_p", "layer_r", "layer_d"])
    parser.add_argument("--config", default=None, help="YAML config path (default: packaged)")
    parser.add_argument("--out", default=None, help="output directory (default: from config)")
    parser.add_argument("--data", default=None, help="data directory (default: from config)")
    args = parser.parse_args(argv)
    if args.layer == "layer_p":
        numbers = run_layer_p(args.config, args.out, args.data)
    elif args.layer == "layer_r":
        from ambo.layer_r import run_layer_r

        numbers = run_layer_r(args.config, args.out, args.data)
    else:
        from ambo.optimize import run_layer_d

        numbers = run_layer_d(args.config, args.out)
    print(json.dumps(numbers, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
