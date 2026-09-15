"""Layer R: the same model on public demo data.

Loads the dataset named in the config, shapes it into the columns the model
expects (``week``, ``week_start``, ``spend_<channel>``, ``revenue``, control), fits,
writes diagnostics, contribution and response-curve artifacts, the holdout
comparison, and the posterior draws that Layer D consumes.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ambo import diagnostics, evaluate, model
from ambo.plots import charts
from ambo.transforms import adstock_weights, hill


def load_source(config: dict, data_dir: Path) -> pd.DataFrame:
    src = config["source"]
    raw = pd.read_csv(Path(data_dir) / src["file"])
    out = pd.DataFrame(
        {
            "week": np.arange(1, len(raw) + 1),
            "week_start": pd.to_datetime(raw[src["date_column"]]).dt.date.astype(str),
            "revenue": raw[src["revenue_column"]].to_numpy(dtype=float),
        }
    )
    for col, label in src["spend_columns"].items():
        out[f"spend_{label}"] = raw[col].to_numpy(dtype=float)
    event = np.zeros(len(raw))
    for col in src.get("event_columns", []):
        event = np.maximum(event, raw[col].to_numpy(dtype=float))
    out[config["control"]["column"]] = event
    return out


def channel_table(contribs: np.ndarray, md: model.ModelData) -> pd.DataFrame:
    """Share of revenue, total contribution and ROAS per channel with 90 percent intervals."""
    total_revenue = float(md.revenue.sum())
    totals = contribs.sum(axis=1)
    rows = []
    for i, ch in enumerate(md.channels):
        spend_total = float(md.spend[:, i].sum())
        share = totals[:, i] / total_revenue
        roas = totals[:, i] / spend_total
        rows.append(
            {
                "channel": ch,
                "spend_total": spend_total,
                "spend_mean_week": float(md.spend[:, i].mean()),
                "contribution_median": float(np.median(totals[:, i])),
                "contribution_lo": float(np.percentile(totals[:, i], 5)),
                "contribution_hi": float(np.percentile(totals[:, i], 95)),
                "share_median": float(np.median(share)),
                "share_lo": float(np.percentile(share, 5)),
                "share_hi": float(np.percentile(share, 95)),
                "roas_median": float(np.median(roas)),
                "roas_lo": float(np.percentile(roas, 5)),
                "roas_hi": float(np.percentile(roas, 95)),
            }
        )
    return pd.DataFrame(rows)


def steady_state_contribution(
    spend: np.ndarray, decay: np.ndarray, half_sat: np.ndarray, slope: np.ndarray,
    effect: np.ndarray, spend_mean: float, revenue_mean: float, length: int,
) -> np.ndarray:
    """Weekly contribution of a constant weekly spend, per draw. Shape (S, len(spend)).

    Constant spend ``x`` carried with the truncated adstock settles at
    ``x * sum(decay**i)``; the Hill curve then gives the response.
    """
    x = np.asarray(spend, dtype=float)[None, :] / spend_mean
    carry = np.array([adstock_weights(d, length).sum() for d in decay])[:, None]
    a = x * carry
    out = np.empty_like(a)
    for s in range(a.shape[0]):
        out[s] = effect[s] * hill(a[s], half_sat[s], slope[s])
    return out * revenue_mean


def response_curves(post: model.Posterior, md: model.ModelData, config: dict) -> pd.DataFrame:
    rc = config["response_curves"]
    rows = []
    for i, ch in enumerate(md.channels):
        top = float(md.spend[:, i].max()) * float(rc["max_multiple_of_observed"])
        grid = np.linspace(0.0, top, int(rc["grid_points"]))
        curve = steady_state_contribution(
            grid,
            post.draws["decay"][:, i],
            post.draws["half_saturation"][:, i],
            post.draws["slope"][:, i],
            post.draws["effect"][:, i],
            md.spend_means[i],
            md.revenue_mean,
            md.adstock_length,
        )
        for g, med, lo, hi in zip(
            grid,
            np.median(curve, axis=0),
            np.percentile(curve, 5, axis=0),
            np.percentile(curve, 95, axis=0),
            strict=True,
        ):
            rows.append({"channel": ch, "spend": g, "median": med, "lo": lo, "hi": hi,
                         "current_spend": float(md.spend[:, i].mean())})
    return pd.DataFrame(rows)


def run_layer_r(config_path=None, out_dir=None, data_dir=None) -> dict:
    from ambo.model import fit_with_ladder
    from ambo.run import load_config

    t_start = time.time()
    config = load_config(config_path, "layer_r.yaml")
    out = Path(out_dir or config["output_dir"])
    data_path = Path(data_dir or config["data_dir"])
    out.mkdir(parents=True, exist_ok=True)
    source = f"{config['title']}; python -m ambo.run layer_r"

    data = load_source(config, data_path)
    data.to_csv(out / "model_input.csv", index=False, lineterminator="\n")
    md = model.prepare(data, config)
    idata, info, diag = fit_with_ladder(md, config)
    diag.update({"layer": config["layer"], "weeks": md.n_weeks, "fit": info})
    diagnostics.write(diag, out / "diagnostics.json")
    model.summary_table(idata).to_csv(
        out / "posterior_summary.csv", index=False, lineterminator="\n"
    )
    post = model.extract(idata)
    contribs = model.media_contributions(post, md)
    base = model.baseline_mean(post, md)

    table = channel_table(contribs, md)
    table.to_csv(out / "channel_contributions.csv", index=False, lineterminator="\n")
    weekly = weekly_contribution_table(contribs, base, md)
    weekly.to_csv(out / "weekly_contributions.csv", index=False, lineterminator="\n")
    charts.channel_contributions(table, weekly, md.channels, out / "channel_contributions.png",
                                 source)
    curves = response_curves(post, md, config)
    curves.to_csv(out / "response_curves.csv", index=False, lineterminator="\n")
    charts.response_curves(curves, out / "response_curves.png", source)
    model.write_posterior(post, md, out)

    metrics, preds, hold_info, hold_idata = evaluate.holdout(data, config)
    metrics.to_csv(out / "holdout_metrics.csv", index=False, lineterminator="\n")
    preds.to_csv(out / "holdout_predictions.csv", index=False, lineterminator="\n")
    charts.holdout(preds, metrics, out / "holdout.png", source, money_unit="revenue units")
    hold_diag = hold_info.pop("diagnostics")
    hold_diag.update({"layer": config["layer"], "weeks": int(config["holdout"]["train_weeks"]),
                      "fit": hold_info})
    diagnostics.write(hold_diag, out / "holdout_diagnostics.json")

    numbers = {
        "layer": config["layer"],
        "weeks": md.n_weeks,
        "channels": table.to_dict(orient="records"),
        "holdout": metrics.to_dict(orient="records"),
        "diagnostics_pass": bool(diag["pass_all"]),
        "holdout_diagnostics_pass": bool(hold_diag["pass_all"]),
        "elapsed_seconds": round(time.time() - t_start, 1),
        "sampler": info["sampler"],
    }
    with open(out / "run_info.json", "w", encoding="utf-8") as fh:
        json.dump(numbers, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return numbers


def weekly_contribution_table(
    contribs: np.ndarray, base: np.ndarray, md: model.ModelData
) -> pd.DataFrame:
    out = pd.DataFrame({"week": md.weeks, "week_start": md.week_start, "revenue": md.revenue})
    out["baseline_median"] = np.median(base, axis=0)
    for i, ch in enumerate(md.channels):
        out[f"{ch} median"] = np.median(contribs[:, :, i], axis=0)
        out[f"{ch} lo"] = np.percentile(contribs[:, :, i], 5, axis=0)
        out[f"{ch} hi"] = np.percentile(contribs[:, :, i], 95, axis=0)
    return out
