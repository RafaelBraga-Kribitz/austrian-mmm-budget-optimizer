"""Write the dashboard feed under reports/exports/ from the layer artifacts.

Tidy CSV files, one per dashboard page or table, so a BI tool can be pointed at a
folder instead of at the model. Nothing is computed here; every column is copied or
reshaped from a file under reports/. Re-run after any pipeline run:

    uv run python scripts/export_dashboard.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
OUT = REPORTS / "exports"


def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, lineterminator="\n")
    print(f"{name}: {len(df)} rows")


def recommendation() -> None:
    """Page 1, Recommendation: allocation per scenario and the gain per scenario."""
    table = pd.read_csv(REPORTS / "layer_d" / "reallocation_table.csv")
    write(table, "recommendation_allocation.csv")
    dec = read_json(REPORTS / "layer_d" / "decision.json")
    rows = []
    for name, block in dec.items():
        if isinstance(block, dict) and "gain_median" in block:
            rows.append(
                {
                    "scenario": name,
                    "total_weekly_budget": block["total_budget"],
                    "gain_median": block["gain_median"],
                    "gain_p10": block["gain_p10"],
                    "gain_p90": block["gain_p90"],
                    "gain_pct_of_contribution_median": block[
                        "gain_pct_of_current_contribution_median"
                    ],
                    "gain_pct_of_contribution_p10": block["gain_pct_of_current_contribution_p10"],
                    "probability_gain_negative": block["probability_gain_negative"],
                    "recommend": block["recommend"],
                    "held_channels": "; ".join(block["held_channels"]),
                    "breakeven_roas": block["breakeven_roas"],
                }
            )
    write(pd.DataFrame(rows), "recommendation_gain.csv")


def contributions() -> None:
    """Page 2, Contributions: weekly decomposition (long format) and the ROAS matrix."""
    weekly = pd.read_csv(REPORTS / "layer_r" / "weekly_contributions.csv")
    channels = [
        c[: -len(" median")]
        for c in weekly.columns
        if c.endswith(" median") and c != "baseline_median"
    ]
    rows = []
    for _, r in weekly.iterrows():
        rows.append(
            {"week": r["week"], "week_start": r["week_start"], "channel": "Baseline",
             "median": r["baseline_median"], "lo": None, "hi": None, "revenue": r["revenue"]}
        )
        for ch in channels:
            rows.append(
                {"week": r["week"], "week_start": r["week_start"], "channel": ch,
                 "median": r[f"{ch} median"], "lo": r[f"{ch} lo"], "hi": r[f"{ch} hi"],
                 "revenue": r["revenue"]}
            )
    write(pd.DataFrame(rows), "contributions_weekly.csv")
    write(pd.read_csv(REPORTS / "layer_r" / "channel_contributions.csv"), "roas_summary.csv")


def curves() -> None:
    """Page 3, Response curves: curves with current spend and the observed range."""
    write(pd.read_csv(REPORTS / "layer_r" / "response_curves.csv"), "response_curves.csv")


def proof() -> None:
    """Page 4, Proof: recovery tables, sampler gates, attribution gap, holdout."""
    recovery = pd.read_csv(REPORTS / "layer_p" / "parameter_recovery.csv")
    write(recovery, "proof_parameter_recovery.csv")
    write(pd.read_csv(REPORTS / "layer_p" / "response_curves.csv"), "proof_response_curves.csv")
    write(pd.read_csv(REPORTS / "layer_p" / "attribution_gap.csv"), "proof_attribution_gap.csv")
    gates = []
    for layer in ("layer_p", "layer_r"):
        for fit in ("diagnostics", "holdout_diagnostics"):
            d = read_json(REPORTS / layer / f"{fit}.json")
            gates.append(
                {
                    "layer": layer,
                    "fit": "full" if fit == "diagnostics" else "holdout",
                    "max_rhat": d["max_rhat"],
                    "min_ess_bulk": d["min_ess_bulk"],
                    "min_ess_tail": d["min_ess_tail"],
                    "divergences": d["divergences"],
                    "attempts": len(d.get("attempts", [])),
                    "final_target_accept": d["fit"]["target_accept"],
                    "final_draws": d["fit"]["draws"],
                    "pass_all": d["pass_all"],
                }
            )
    write(pd.DataFrame(gates), "proof_sampler_gates.csv")
    holdout = []
    for layer in ("layer_p", "layer_r"):
        h = pd.read_csv(REPORTS / layer / "holdout_metrics.csv")
        h.insert(0, "layer", layer)
        holdout.append(h)
    write(pd.concat(holdout, ignore_index=True), "holdout_metrics.csv")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    recommendation()
    contributions()
    curves()
    proof()


if __name__ == "__main__":
    main()
