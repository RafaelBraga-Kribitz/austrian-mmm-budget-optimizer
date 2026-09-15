"""Sampler health gates: R-hat, effective sample size, divergences, energy.

One function turns an ArviZ InferenceData into a plain dictionary that is written
to ``diagnostics.json`` next to the fit. Thresholds come from the YAML config so the
same gates apply to every layer.
"""

from __future__ import annotations

import json
from pathlib import Path

import arviz as az
import numpy as np


def summarise(idata: az.InferenceData, thresholds: dict, extra: dict | None = None) -> dict:
    """Max R-hat, min ESS (bulk and tail), divergences and min BFMI, with pass flags."""
    # unrounded statistics: az.summary rounds to two decimals, which would turn an
    # R-hat of 1.006 into a failing 1.01
    rhat_ds = az.rhat(idata)
    ess_bulk_ds = az.ess(idata, method="bulk")
    ess_tail_ds = az.ess(idata, method="tail")
    rhat_by_param = {str(k): float(np.nanmax(v.to_numpy())) for k, v in rhat_ds.items()}
    ess_by_param = {str(k): float(np.nanmin(v.to_numpy())) for k, v in ess_bulk_ds.items()}
    rhat = np.array(list(rhat_by_param.values()))
    ess_bulk = np.array(list(ess_by_param.values()))
    ess_tail = np.array([float(np.nanmin(v.to_numpy())) for v in ess_tail_ds.values()])
    stats = idata.sample_stats
    divergences = int(stats["diverging"].sum()) if "diverging" in stats else 0
    bfmi = None
    if "energy" in stats:
        bfmi = float(np.min(az.bfmi(idata)))
    n_chains = int(idata.posterior.sizes["chain"])
    n_draws = int(idata.posterior.sizes["draw"])
    result = {
        "max_rhat": float(np.nanmax(rhat)),
        "min_ess_bulk": float(np.nanmin(ess_bulk)),
        "min_ess_tail": float(np.nanmin(ess_tail)),
        "divergences": divergences,
        "min_bfmi": bfmi,
        "chains": n_chains,
        "draws_per_chain": n_draws,
        "worst_rhat_parameter": max(rhat_by_param, key=rhat_by_param.get),
        "worst_ess_parameter": min(ess_by_param, key=ess_by_param.get),
        "thresholds": {
            "rhat_max": float(thresholds["rhat_max"]),
            "ess_min": float(thresholds["ess_min"]),
            "divergences_max": int(thresholds["divergences_max"]),
        },
    }
    result["pass_rhat"] = bool(result["max_rhat"] < thresholds["rhat_max"])
    result["pass_ess"] = bool(
        min(result["min_ess_bulk"], result["min_ess_tail"]) > thresholds["ess_min"]
    )
    result["pass_divergences"] = bool(divergences <= thresholds["divergences_max"])
    result["pass_all"] = bool(
        result["pass_rhat"] and result["pass_ess"] and result["pass_divergences"]
    )
    if extra:
        result.update(extra)
    return result


def write(result: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")
