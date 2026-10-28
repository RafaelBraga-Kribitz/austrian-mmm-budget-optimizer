"""Render README.md from scripts/readme_template.md and the artifacts under reports/.

Every number that reaches the README is read from a file under reports/ and written
here; nothing is typed by hand. The values inserted are recorded in
reports/readme_values.json so tests/test_readme_numbers.py can check that the README
contains no number the reports do not.

    uv run python scripts/render_readme.py [--date 2026-09-16]

The template holds every hand-written section; only the {{placeholders}} are filled
from reports/. Pass --date when the pipeline has been rerun; without it the date of
the committed render is kept.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from ambo.optimize import next_budget_filename

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
VALUES: dict[str, str] = {}


def v(key: str, value) -> str:
    """Record a rendered value and return it as text."""
    text = str(value)
    VALUES[key] = text
    return text


def pct(x: float, digits: int = 1) -> str:
    return f"{100 * float(x):.{digits}f}"


def num(x: float, digits: int = 2) -> str:
    return f"{float(x):.{digits}f}"


def money(x: float) -> str:
    return f"{float(x):.0f}"


def signed(x: float, digits: int = 0) -> str:
    return f"{float(x):+.{digits}f}"


def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _has(folder: Path, *names: str) -> bool:
    """A test counts as run only when every artifact the README reads from it exists."""
    return all((folder / name).exists() for name in names)


def layer_p_values() -> dict:
    d = REPORTS / "layer_p"
    if not _has(d, "run_info.json", "diagnostics.json", "attribution_gap.csv", "holdout_metrics.csv",
                "parameter_recovery.csv", "contribution_recovery.csv", "response_curve_metrics.csv"):
        return {}
    gap = pd.read_csv(d / "attribution_gap.csv")
    return {
        "info": read_json(d / "run_info.json"),
        "diag": read_json(d / "diagnostics.json"),
        "gap": gap,
        "search": gap[gap["channel"] == "Paid Search"].iloc[0],
        "metrics": pd.read_csv(d / "holdout_metrics.csv"),
        "recovery": pd.read_csv(d / "parameter_recovery.csv"),
        "contribution": pd.read_csv(d / "contribution_recovery.csv"),
        "curves": pd.read_csv(d / "response_curve_metrics.csv"),
    }


def layer_r_values() -> dict:
    d = REPORTS / "layer_r"
    if not _has(d, "run_info.json", "diagnostics.json", "channel_contributions.csv",
                "holdout_metrics.csv"):
        return {}
    return {
        "info": read_json(d / "run_info.json"),
        "diag": read_json(d / "diagnostics.json"),
        "channels": pd.read_csv(d / "channel_contributions.csv"),
        "metrics": pd.read_csv(d / "holdout_metrics.csv"),
    }


def layer_d_values() -> dict:
    d = REPORTS / "layer_d"
    if not _has(d, "decision.json", "reallocation_table.csv"):
        return {}
    return {
        "decision": read_json(d / "decision.json"),
        "table": pd.read_csv(d / "reallocation_table.csv"),
    }


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

# Channel names that read better in lower case in the middle of a sentence.
SENTENCE_NAMES = {"Out-of-home": "out-of-home"}


def nm(channel: str) -> str:
    return SENTENCE_NAMES.get(channel, channel)


def and_join(items: list[str], oxford: bool = False) -> str:
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    sep = ", and " if oxford else " and "
    return ", ".join(items[:-1]) + sep + items[-1]


def _unsigned(text: str) -> str:
    return text.lstrip("+-")


def decision_facts(dd: dict) -> dict:
    """What the budget recommendation says, read from the budget shift recommendation files."""
    dec = dd["decision"]
    same = dec["same_total"]
    rows = dd["table"][dd["table"]["scenario"] == "same_total"]
    breakeven = v("a_breakeven", num(dec["breakeven_roas"]))
    # the move cap is a config setting, not an artifact
    with open(ROOT / "src" / "ambo" / "configs" / "layer_r.yaml", encoding="utf-8") as fh:
        cap_value = 100 * float(yaml.safe_load(fh)["decision"]["bound_share"])
    ups, downs, holds, capped = [], [], [], []
    for _, row in rows.iterrows():
        ch = row["channel"]
        if bool(row["held_by_rule"]):
            holds.append(ch)
        elif row["delta_pct"] > 0.5:
            ups.append((ch, v("a_delta_" + ch, signed(row["delta_pct"]))))
            if abs(row["delta_pct"] - cap_value) < 0.5:
                capped.append(ch)
        elif row["delta_pct"] < -0.5:
            downs.append((
                ch,
                v("a_delta_" + ch, signed(row["delta_pct"])),
                v("a_mr_" + ch, num(row["marginal_roas_current_median"])),
            ))
    return {
        "recommend": bool(same["recommend"]),
        "breakeven": breakeven,
        "cap": v("a_cap", f"{cap_value:.0f}"),
        "ups": ups,
        "downs": downs,
        "holds": holds,
        "capped": capped,
        "gain_median": v("a_gain_median", num(same["gain_pct_of_current_contribution_median"], 1)),
        "gain_p10": v("a_gain_p10", num(same["gain_pct_of_current_contribution_p10"], 1)),
        "gain_p10_raw": float(same["gain_pct_of_current_contribution_p10"]),
        "p_neg": v("a_p_neg", pct(same["probability_gain_negative"])),
        "draws": v("a_draws", dec["posterior_draws_used"]),
    }


def _up_phrase(ups: list[tuple[str, str]]) -> str:
    deltas = {d for _, d in ups}
    if len(ups) > 1 and len(deltas) == 1:
        return f"{and_join([nm(c) for c, _ in ups])} ({ups[0][1]} percent each)"
    return and_join([f"{nm(c)} ({d} percent)" for c, d in ups])


def answer_text(f: dict) -> str:
    """The answer in the top box: one short paragraph, read from the recommendation."""
    if not f["recommend"]:
        return "hold the current allocation. No budget shift passes the decision rule. Units are not euros."
    move = []
    if f["downs"]:
        move.append(
            "out of " + and_join([f"{nm(c)} ({d} percent)" for c, d, _ in f["downs"]])
        )
    if f["ups"]:
        move.append("into " + _up_phrase(f["ups"]))
    return (
        "move weekly budget " + " ".join(move) + f". Media contribution gains a median "
        f"{f['gain_median']} percent. Units are not euros."
    )


def decision_lead(f: dict) -> str:
    """The recommendation, or the rejection of a candidate, in short paragraphs."""
    if not f["recommend"]:
        return _rejected_lead(f)
    head = "**Recommendation (public demo data, same total budget):**"
    sentences = []
    if f["downs"] or f["ups"]:
        move = "move weekly budget"
        if f["downs"]:
            move += " out of " + and_join([nm(c) for c, _, _ in f["downs"]])
        if f["ups"]:
            move += (" and" if f["downs"] else "") + " into " + and_join(
                [nm(c) for c, _ in f["ups"]]
            )
        sentences.append(move + ".")
    for c, d, mr in f["downs"]:
        sentences.append(
            f"{c} returns {mr} per extra unit of spend, below the breakeven return of "
            f"{f['breakeven']}, so it loses {_unsigned(d)} percent of its spend."
        )
    ups = f["ups"]
    if ups:
        deltas = {d for _, d in ups}
        if len(deltas) == 1:
            each = " each" if len(ups) > 1 else ""
            verb_up = "gain" if len(ups) > 1 else "gains"
            sentences.append(
                f"{and_join([nm(c) for c, _ in ups])}{each} {verb_up} {_unsigned(ups[0][1])} percent."
            )
        else:
            sentences.extend(f"{nm(c)} gains {_unsigned(d)} percent." for c, d in ups)
    paragraphs = [head + " " + " ".join(sentences)]
    if f["holds"]:
        hold = (
            f"Hold {and_join(f['holds'])}. The lower end of their return interval falls below "
            "the breakeven return on ad spend (ROAS)."
        )
        if f["capped"]:
            stop = "stop" if len(f["capped"]) > 1 else "stops"
            hold += (
                f" {and_join(f['capped'])} {stop} at the cap that the config puts on any "
                f"channel's move: {f['cap']} percent of its current spend."
            )
        paragraphs.append(hold)
    return "\n\n".join(paragraphs)


def _rejected_lead(f: dict) -> str:
    """The decision rule rejected the candidate: hold the current allocation, show the candidate."""
    head = (
        "**No shift recommended (public demo data, same total budget):** hold the current "
        "allocation. The decision rule rejects the best candidate that the optimiser found."
    )
    paragraphs = [head]
    if f["downs"] or f["ups"]:
        cand = ["Rejected candidate, not advice: the candidate shifted weekly budget"]
        if f["downs"]:
            cand.append("out of " + and_join([nm(c) for c, _, _ in f["downs"]]))
        if f["ups"]:
            cand.append(("and " if f["downs"] else "") + "into " + and_join(
                [nm(c) for c, _ in f["ups"]]
            ))
        sentences = [" ".join(cand) + "."]
        for c, d, mr in f["downs"]:
            sentences.append(
                f"{c} would return {mr} per extra unit of spend, below the breakeven return "
                f"of {f['breakeven']}, and would lose {_unsigned(d)} percent of its spend."
            )
        ups = f["ups"]
        if ups:
            deltas = {d for _, d in ups}
            if len(deltas) == 1:
                each = " each" if len(ups) > 1 else ""
                sentences.append(
                    f"{and_join([nm(c) for c, _ in ups])} would{each} gain "
                    f"{_unsigned(ups[0][1])} percent."
                )
            else:
                sentences.extend(f"{nm(c)} would gain {_unsigned(d)} percent." for c, d in ups)
        if f["gain_p10_raw"] <= 0:
            sentences.append(
                f"The 10th percentile of the candidate's gain is {f['gain_p10']} percent, which "
                "is not above zero. The rule rejects the candidate."
            )
        else:
            sentences.append("The rule rejects the candidate.")
        paragraphs.append(" ".join(sentences))
    if f["holds"]:
        paragraphs.append(
            f"The rule would hold {and_join(f['holds'])} at current spend. The lower end of "
            "their return interval falls below the breakeven return on ad spend (ROAS)."
        )
    return "\n\n".join(paragraphs)


def headline_values(p: dict, r: dict) -> tuple[str, str]:
    """Record the headline numbers of the made-up-data test; return the chart and its alt text."""
    if p:
        info = p["info"]
        v("p_curve_cov", pct(info["curve_coverage_mean"], 0))
        v("p_covered", info["parameters_covered"])
        v("p_total", info["parameters_total"])
        v("p_search_over", num(p["search"]["platform_over_true_pct"], 0))
    if r:
        for _, row in r["channels"].iterrows():
            ch = row["channel"]
            v("r_share_" + ch, pct(row["share_median"]))
            v("r_lo_" + ch, pct(row["share_lo"]))
            v("r_hi_" + ch, pct(row["share_hi"]))
        return (
            "reports/layer_r/channel_contributions.png",
            "Incremental contribution per channel on public demo data, with 90 percent intervals",
        )
    return (
        "reports/layer_p/response_curve_recovery.png",
        "Response curve recovery on synthetic data: true curves against posterior bands",
    )


def share_table(r: dict) -> str:
    rows = ["| Channel | Share of revenue (percent) | 90 percent interval |", "|---|---|---|"]
    for _, row in r["channels"].iterrows():
        ch = row["channel"]
        rows.append(
            f"| {ch} | {v('r_share_' + ch, pct(row['share_median']))} | "
            f"{v('r_lo_' + ch, pct(row['share_lo']))} to {v('r_hi_' + ch, pct(row['share_hi']))} |"
        )
    return "\n".join(rows)


def headline_caption(r: dict) -> str:
    """Caption under the primary chart: what it shows and what to take from it."""
    if not r:
        return (
            "*Blue: true response curve; black: posterior median; band: 90 percent interval. "
            "The model is judged on whether the band covers the blue line.*"
        )
    ch = r["channels"]
    top = ch.loc[ch["share_median"].idxmax()]
    widest = ch.loc[(ch["share_hi"] - ch["share_lo"]).idxmax()]
    name = top["channel"]
    med = v("c_top_share", pct(top["share_median"]))
    lo = v("c_top_lo", pct(top["share_lo"]))
    hi = v("c_top_hi", pct(top["share_hi"]))
    weeks = v("c_weeks", r["info"]["weeks"])
    wname = widest["channel"]
    wlo = v("c_wide_lo", pct(widest["share_lo"]))
    whi = v("c_wide_hi", pct(widest["share_hi"]))
    return (
        f"*Left: share of revenue each channel drives, median and 90 percent interval. "
        f"{name} drives the largest share, {med} percent ({lo} to {hi}). {wname} has the widest "
        f"interval ({wlo} to {whi} percent), so its median alone is no basis for moving "
        f"budget. Right: weekly contribution per channel over the {weeks} weeks, in the demo "
        f"file's money units. Units are not euros.*"
    )


def _fit_phrase(diag: dict, key: str) -> tuple[str, str, str]:
    """Target acceptance, draws and attempt of the reported fit."""
    fit = diag.get("fit", {})
    ta = v(f"m_ta_{key}", fit.get("target_accept", ""))
    draws = v(f"m_draws_{key}", fit.get("draws", ""))
    attempts = diag.get("attempts", [])
    if len(attempts) > 1:
        return ta, draws, "on attempt " + v(f"m_attempts_{key}", len(attempts))
    return ta, draws, "on the first attempt"


def method_bullets(p: dict, r: dict) -> str:
    """Definitions of the modelling terms; sampler lines appear only when a fit has run."""
    bullets = [
        "- **Adstock:** geometric carry-over per channel. This week's spend keeps working in "
        "the following weeks, with a decay rate that the model estimates.",
        "- **Saturation:** a Hill curve per channel on the carried-over spend. It has a "
        "half-saturation point and a slope, so returns diminish as spend grows.",
        "- **Seasonality and controls:** a linear trend, two yearly Fourier pairs (sine and "
        "cosine terms for the yearly pattern) and one control. The control is a "
        "public-holiday week indicator on the made-up data and competitor sales on the "
        "public demo data.",
        "- **Priors:** a prior is the assumption that the model holds before it sees the "
        "data. The priors here are weakly informative and identical across channels, on "
        "scaled data. So the estimates come from the data, not from a prior that knows the "
        "answer. The model docstring gives each prior and its reasoning.",
    ]
    rhat_bullet = (
        "- **R-hat:** a check that compares the sampler chains with each other. A value "
        "near 1 means the chains agree."
    )
    if not (p or r):
        return "\n".join(bullets + [rhat_bullet])
    diag = p["diag"] if p else r["diag"]
    fit = diag.get("fit", {})
    thresholds = diag.get("thresholds", {})
    sampler = v("m_sampler", fit.get("sampler", ""))
    chains = v("m_chains", fit.get("chains", ""))
    tune = v("m_tune", fit.get("tune", ""))
    attempts = diag.get("attempts", [])
    first_ta = v("m_ta_start", attempts[0]["target_accept"] if attempts else
                 fit.get("target_accept", ""))
    first_draws = v("m_draws_start", attempts[0]["draws"] if attempts else fit.get("draws", ""))
    fits = []
    if p:
        fits.append(("made-up data", *_fit_phrase(p["diag"], "p")))
    if r:
        fits.append(("public demo data", *_fit_phrase(r["diag"], "r")))
    if len({f[1:] for f in fits}) == 1:
        _, ta, draws, when = fits[0]
        ran = (f"{'Both reported fits' if len(fits) > 1 else 'The reported fit'} ran at target "
               f"acceptance {ta} with {draws} draws per chain, {when}.")
    else:
        ran = "The reported fits ran: " + "; ".join(
            f"{label} at target acceptance {ta} with {draws} draws per chain, {when}"
            for label, ta, draws, when in fits
        ) + "."
    rhat = v("m_rhat", thresholds.get("rhat_max", ""))
    ess = v("m_ess", int(thresholds.get("ess_min", 0)))
    splits = []
    if p:
        train = v("m_train_p", int(p["metrics"]["train_weeks"].iloc[0]))
        weeks = v("m_weeks_p", p["info"]["weeks"])
        splits.append(f"the first {train} of {weeks} weeks on the made-up data")
    if r:
        train = v("m_train_r", int(r["metrics"]["train_weeks"].iloc[0]))
        weeks = v("m_weeks_r", r["info"]["weeks"])
        splits.append(f"the first {train} of {weeks} weeks on the public demo data")
    return "\n".join(
        bullets
        + [
            f"- **Sampler:** the No-U-Turn Sampler (NUTS, run through {sampler}) with {chains} "
            f"chains and {tune} tuning draws. It starts at target acceptance {first_ta} with "
            f"{first_draws} draws per chain. When a gate fails, a recorded ladder raises the "
            f"target acceptance and then the draws. {ran}",
            rhat_bullet,
            f"- **Diagnostics:** R-hat below {rhat}, effective sample size above {ess} and zero "
            f"divergences. The code writes them to `diagnostics.json` next to every fit.",
            f"- **Holdout protocol:** fit on {' and on '.join(splits)}. Forecast the rest with "
            f"the actual spend. Report MAPE and 90 percent interval coverage against a "
            f"seasonal-naive and a ridge-regression baseline.",
        ]
    )


def data_table(p: dict, r: dict, dd: dict) -> str:
    rows = ["| Test | Source | Grain and window | Tag |", "|---|---|---|---|"]
    if p:
        weeks = v("data_weeks_p", p["info"]["weeks"])
        rows.append(
            "| Made-up data with a known answer | Generated advertiser; true parameters in "
            f"`data/synthetic/truth.json` | Weekly, {weeks} weeks, five channels (TV, Radio, "
            "Print, Paid Search, Paid Social) | `SIMULATED` |"
        )
    if r:
        weeks = v("data_weeks_r", r["info"]["weeks"])
        rows.append(
            "| Public demo data | Robyn simulated weekly dataset (MIT, Meta Platforms); columns "
            f"and licence in `data/README.md` | Weekly, {weeks} weeks, five named channels in "
            "the file's money units | `SIMULATED` |"
        )
    rows.append(
        "| Control, made-up data | Austrian public-holiday week indicator | Weekly | `VERIFIED` |"
    )
    if dd:
        dec = dd["decision"]
        margin = v("data_margin", pct(dec["contribution_margin"], 0))
        breakeven = v("data_breakeven", num(dec["breakeven_roas"]))
        rows.append(
            f"| Assumption | Contribution margin {margin} percent, breakeven ROAS {breakeven}, a "
            "placeholder in the public-demo config until a client margin is supplied | Decision "
            "rule | `ASSUMPTION` |"
        )
    return "\n".join(rows)


def proof_section(p: dict) -> str:
    if not p:
        return "The test on made-up data has not run yet."
    info, rec, con, cur = p["info"], p["recovery"], p["contribution"], p["curves"]
    n_channels = len(con)
    cov_mean = v("pr_curve_cov_mean", pct(info["curve_coverage_mean"], 0))
    cov_min = v("pr_curve_cov_min", pct(info["curve_coverage_min"], 0))
    mae_max = v("pr_curve_mae_max", num(info["curve_mae_pct_max"], 1))
    covered = v("pr_covered", info["parameters_covered"])
    total = v("pr_total", info["parameters_total"])
    effects = rec[rec["parameter"].str.endswith(" effect")]
    ksat = rec[rec["parameter"].str.endswith(" half-saturation")]
    n_eff_over = v("pr_eff_over", int((effects["median"] > effects["true"]).sum()))
    n_k_over = v("pr_k_over", int((ksat["median"] > ksat["true"]).sum()))
    n_eff = v("pr_n_eff", len(effects))
    shares_ok = v("pr_shares_ok", int(con["covered"].sum()))
    n_ch = v("pr_n_ch", n_channels)
    misses = con[~con["covered"]]
    if len(misses) == 0:
        share_sentence = "The revenue share of every channel is inside its interval."
    else:
        bits = []
        top_spend = con["spend_total"].max()
        for _, row in misses.iterrows():
            ch = row["channel"]
            largest = ", the largest channel by spend" if row["spend_total"] == top_spend else ""
            true_share = v("pr_miss_true_" + ch, pct(row["true_share_of_revenue"]))
            lo = v("pr_miss_lo_" + ch, pct(row["share_lo"]))
            hi = v("pr_miss_hi_" + ch, pct(row["share_hi"]))
            bits.append(
                f"{ch}{largest}. Its true share is {true_share} percent, against an interval "
                f"of {lo} to {hi}."
            )
        lead = "The exception sits" if len(misses) == 1 else "The exceptions sit"
        share_sentence = (
            f"Revenue shares are covered for {shares_ok} of {n_ch} channels. {lead} just "
            f"outside its interval: " + " ".join(bits)
        )
    worst = cur.loc[cur["curve_coverage_observed_range"].idxmin(), "channel"]
    gap = p["gap"]
    over = gap[gap["gap_pp"] > 0].sort_values("gap_pp", ascending=False)
    under = gap[gap["platform_share"] == 0].sort_values("gap_pp")
    over_bits = and_join([
        f"{row['channel']} by " + _unsigned(v("pg_over_" + row["channel"], signed(row["gap_pp"], 1)))
        for _, row in over.iterrows()
    ])
    under_bits = and_join(
        [
            f"{row['channel']} {v('pg_true_' + row['channel'], pct(row['true_share']))}"
            for _, row in under.iterrows()
        ],
        oxford=False,
    )
    gap_caption = (
        "*Hollow dot: the share of revenue that the platform report credits to a channel. "
        "Filled dot: its true share of incremental media contribution. Both are for the "
        "made-up advertiser. The two shares use different denominators, and neither is total "
        f"revenue. The report over-credits {over_bits} percentage points. It gives the offline "
        f"channels nothing, although their true shares are {under_bits} percent.*"
    )
    return "\n\n".join(
        [
            "![Response curve recovery on synthetic data: true curves against posterior bands]"
            "(reports/layer_p/response_curve_recovery.png)",
            "*Blue: the true response curve. Black: the posterior median. Band: the 90 percent "
            "interval. Dashed line: the largest observed weekly spend. Beyond it, the model "
            "extrapolates.*",
            f"Before anyone trusts the model on an advertiser's data, it had to recover a truth "
            f"it was handed. On the made-up advertiser, the estimated response curves cover the "
            f"true curves on {cov_mean} percent of the grid points inside the observed spend "
            f"range. The worst channel is {worst}, at {cov_min} percent. The mean error is at "
            f"most {mae_max} percent of the true curve's height. {covered} of {total} "
            f"individual parameters fall inside their 90 percent intervals.",
            "The misses follow a known trade-off, not a bug. Each curve has two settings that "
            "trade off: how high it rises (the effect size) and how much spend it takes to "
            "level off (the half-saturation point; [How it works](#how-it-works) defines "
            "saturation). A curve that rises higher but levels off later fits the same "
            "observed weeks.",
            f"For that reason, {n_eff_over} of {n_eff} effect sizes and {n_k_over} of {n_eff} "
            f"half-saturation points have medians above the truth. We judge recovery on curves "
            f"and shares, which a budget decision uses, not on point parameters.",
            share_sentence,
            "![Per channel on synthetic data: share of platform-attributed revenue in the "
            "platform report against true share of incremental media contribution]"
            "(reports/layer_p/attribution_gap.png)",
            gap_caption,
        ]
    )


def holdout_table(metrics: pd.DataFrame, key: str) -> str:
    rows = ["| Model | MAPE | 90 percent interval coverage |", "|---|---|---|"]
    for _, r in metrics.iterrows():
        name = r["model"].split(" (")[0]
        mape = v(f"{key}_mape_{name}", pct(r["mape"]))
        cov = v(f"{key}_cov_{name}", pct(r["coverage_90"], 0))
        rows.append(f"| {name} | {mape} percent | {cov} percent |")
    return "\n".join(rows)


def holdout_heading(m: pd.DataFrame, key: str, label: str) -> str:
    """A finding-first H3: who wins on holdout error, with both numbers."""
    mmm = m[m["model"] == "Bayesian MMM"].iloc[0]
    others = m[m["model"] != "Bayesian MMM"]
    best = others.loc[others["mape"].idxmin()]
    best_name = best["model"].split(" (")[0].lower()
    mmm_mape = v(f"hh_{key}_mmm", pct(mmm["mape"]))
    best_mape = v(f"hh_{key}_best", pct(best["mape"]))
    if mmm["mape"] <= best["mape"]:
        return (f"### {label}: the MMM has the lowest holdout error, {mmm_mape} percent "
                f"against {best_mape} percent for {best_name}")
    return (f"### {label}: {best_name} beats the MMM on holdout error, {best_mape} percent "
            f"against {mmm_mape} percent")


def holdout_section(p: dict, r: dict) -> str:
    out = [
        "Each model learns from the earlier weeks and forecasts the last weeks it has not "
        "seen. Error is the mean absolute percentage error (MAPE). Coverage is how often the "
        "actual week fell inside the model's 90 percent interval.\n\n"
        "Two simple baselines set the bar. Seasonal naive repeats the revenue of 52 weeks "
        "earlier. Ridge regression is a plain regression with a penalty on large coefficients."
    ]
    if p:
        m = p["metrics"]
        n_test = v("h_p_ntest", int(m["n_test"].iloc[0]))
        out.append(
            holdout_heading(m, "p", "Test on made-up data with a known answer") + "\n\n"
            f"Holdout of {n_test} weeks on made-up data:\n\n"
            + holdout_table(m, "p") + "\n\n" + verdict_sentence(m, "p")
        )
    if r:
        m = r["metrics"]
        n_test = v("h_r_ntest", int(m["n_test"].iloc[0]))
        out.append(
            holdout_heading(m, "r", "Test on public demo data") + "\n\n"
            f"Holdout of {n_test} weeks on public demo data:\n\n"
            + holdout_table(m, "r") + "\n\n" + verdict_sentence(m, "r")
        )
    return "\n\n".join(out) if len(out) > 1 else "No holdout results yet."


def verdict_sentence(m: pd.DataFrame, key: str) -> str:
    mmm = m[m["model"] == "Bayesian MMM"].iloc[0]
    others = m[m["model"] != "Bayesian MMM"]
    best_other = others.loc[others["mape"].idxmin()]
    cov = v(f"{key}_mmm_cov", pct(mmm["coverage_90"], 0))
    short = 90.0 - 100.0 * mmm["coverage_90"]
    if short > 0.5:
        gap = v(f"{key}_cov_gap", f"{short:.0f}")
        calibration = (
            f"Its 90 percent intervals covered {cov} percent of holdout weeks, {gap} points "
            f"below nominal. So the intervals are slightly too narrow and the model is a "
            f"little overconfident. The wider intervals of the baselines covered more."
        )
    elif short < -5.0:
        calibration = (
            f"Its 90 percent intervals covered {cov} percent of holdout weeks, more than the "
            f"nominal 90. So on this data the intervals are wider than they need to be."
        )
    else:
        calibration = (
            f"Its 90 percent intervals covered {cov} percent of holdout weeks, on target."
        )
    if mmm["mape"] <= best_other["mape"]:
        head = (
            "The MMM has the lowest point error here. Its case does not rest on that, because "
            "the baselines say nothing about which channel earned the revenue."
        )
    else:
        name = best_other["model"].split(" (")[0].lower()
        head = (
            f"The MMM loses on point error to the {name} baseline on this data. We report "
            "that as it comes out. The case for the MMM is interpretability, not always "
            "accuracy: it shows which channel earned the revenue, with intervals."
        )
    return head + " " + calibration


def decision_table(dd: dict) -> str:
    same = dd["table"][dd["table"]["scenario"] == "same_total"]
    recommended = bool(dd["decision"]["same_total"]["recommend"])
    spend = "Recommended weekly spend" if recommended else "Rejected candidate weekly spend"
    after = "after the shift" if recommended else "at the rejected candidate spend"
    rows = [
        f"| Channel | Current weekly spend | {spend} | Change | Return on the "
        "next unit of spend, today (90 percent interval) | Return on the next unit of spend, "
        f"{after} (90 percent interval) | Media contribution {after} "
        "(90 percent interval) |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in same.iterrows():
        ch = r["channel"]
        cur = v(f"d_cur_{ch}", money(r["current_spend"]))
        rec = v(f"d_rec_{ch}", money(r["recommended_spend"]))
        delta = v(f"d_delta_{ch}", signed(r["delta_pct"]))
        mr_cur = v(f"d_mr_cur_{ch}", num(r["marginal_roas_current_median"]))
        mr_cur_lo = v(f"d_mr_cur_lo_{ch}", num(r["marginal_roas_current_lo"]))
        mr_cur_hi = v(f"d_mr_cur_hi_{ch}", num(r["marginal_roas_current_hi"]))
        mr_rec = v(f"d_mr_rec_{ch}", num(r["marginal_roas_recommended_median"]))
        mr_rec_lo = v(f"d_mr_rec_lo_{ch}", num(r["marginal_roas_recommended_lo"]))
        mr_rec_hi = v(f"d_mr_rec_hi_{ch}", num(r["marginal_roas_recommended_hi"]))
        c_rec = v(f"d_c_rec_{ch}", money(r["contribution_recommended_median"]))
        c_lo = v(f"d_c_rec_lo_{ch}", money(r["contribution_recommended_lo"]))
        c_hi = v(f"d_c_rec_hi_{ch}", money(r["contribution_recommended_hi"]))
        held = " (held by the rule)" if bool(r["held_by_rule"]) else ""
        rows.append(
            f"| {ch}{held} | {cur} | {rec} | {delta} percent | {mr_cur} ({mr_cur_lo} to "
            f"{mr_cur_hi}) | {mr_rec} ({mr_rec_lo} to {mr_rec_hi}) | {c_rec} ({c_lo} to {c_hi}) |"
        )
    return "\n".join(rows)


def decision_blocks(dd: dict, run_date: date) -> dict:
    """Generated pieces of the Decision section; the template holds the fixed sentences."""
    dec = dd["decision"]
    s = dec["same_total"]
    f = decision_facts(dd)
    v("d_gain_med2", num(s["gain_pct_of_current_contribution_median"], 1))
    v("d_gain_p10_2", num(s["gain_pct_of_current_contribution_p10"], 1))
    v("d_p_neg", pct(s["probability_gain_negative"]))
    v("d_draws", dec["posterior_draws_used"])
    breakeven = v("d_breakeven", num(dec["breakeven_roas"]))
    margin = v("d_margin", pct(dec["contribution_margin"], 0))
    held_channels = [str(c) for c in s["held_channels"]]
    if held_channels:
        gate = (
            f"The breakeven gate held {and_join(held_channels)} at current spend. The lower "
            "bound of their marginal ROAS interval falls below breakeven, so no budget moves "
            "toward them, however high their median."
        )
    else:
        gate = (
            "The breakeven gate did not bind. Every channel's marginal ROAS lower bound stays "
            "above breakeven at the recommended spend."
        )
    gate_paragraph = (
        f"Breakeven ROAS is {breakeven} at a contribution margin of {margin} percent. The "
        f"config states that margin as an assumption. {gate}"
    )
    extra_paragraph = ""
    if "plus_extra_budget" in dec:
        e = dec["plus_extra_budget"]
        extra = v("d_extra_year", money(dec["extra_budget_per_year"]))
        e_gain = v("d_extra_gain", num(e["gain_pct_of_current_contribution_median"], 1))
        e_p10 = v("d_extra_p10", num(e["gain_pct_of_current_contribution_p10"], 1))
        e_verdict = "recommend" if e["recommend"] else "hold"
        extra_paragraph = (
            f"With {extra} more per year, spread over 52 weeks, media contribution rises by a "
            f"median {e_gain} percent (10th percentile {e_p10} percent). The amounts are in "
            f"dataset money units, and units are not euros. The rule says {e_verdict}. The "
            f"file `reports/layer_d/{next_budget_filename(dec['extra_budget_per_year'])}` "
            f"shows where the extra budget goes, channel by channel, and how likely that call "
            f"is wrong.\n\n"
        )
    if s["probability_gain_negative"] == 0:
        spread = f"None of the {f['draws']} posterior draws shows a loss."
    else:
        spread = f"{f['p_neg']} percent of the {f['draws']} posterior draws show a loss."
    caption_head = (
        "Gain from moving the same budget" if s["recommend"]
        else "Gain from the rejected candidate allocation, not advice"
    )
    gain_caption = (
        f"*{caption_head}, one bar per posterior draw. {spread} The blue "
        f"line marks the 10th percentile ({f['gain_p10']} percent). The dashed line marks the "
        f"median ({f['gain_median']} percent). Units are not euros.*"
    )
    return {
        "decision_lead": decision_lead(f),
        "decision_table": decision_table(dd),
        "decision_verdict": (
            "Recommend the shift." if s["recommend"]
            else "Hold the current allocation: the rule is not met."
        ),
        "gain_label": (
            "Gain from the reallocation" if s["recommend"] else "Gain from the rejected candidate"
        ),
        "gate_paragraph": gate_paragraph,
        "extra_budget_paragraph": extra_paragraph,
        "gain_caption": gain_caption,
        "answer_text": answer_text(f),
    }


def validation_sentence(p: dict, r: dict) -> str:
    """What the README may say about validation and demonstration, given the evidence that exists."""
    if p and r:
        return ("The model is validated on made-up data with a known truth and demonstrated on "
                "public data, pending a client swap-in.")
    if p:
        return ("The model is validated on made-up data with a known truth, pending a client "
                "swap-in.")
    if r:
        return ("The plan is to validate the model on made-up data with a known truth. It is "
                "demonstrated on public data, pending a client swap-in.")
    return ("The plan is to validate the model on made-up data with a known truth and to "
            "demonstrate it on public data, pending a client swap-in.")


def limitations(p: dict, r: dict) -> str:
    if r:
        data = (
            "- The public demo data is Robyn's simulated weekly dataset. It has five named "
            "channels and revenue in money units whose currency its authors do not name. Shares, "
            "ROAS ratios and the breakeven test are meaningful. The amounts are not euros. No "
            "Austrian client data was used. A real-data swap-in is planned."
        )
    else:
        data = (
            "- The plan is to use Robyn's simulated weekly dataset as public demo data. Its "
            "currency is not named, so its amounts would not be euros. No Austrian client data "
            "was used. A real-data swap-in is planned."
        )
    if p:
        form = (
            "- The model assumes one form: carry-over that decays geometrically (adstock), a "
            "Hill saturation curve and an additive baseline. [How it works](#how-it-works) "
            "defines these terms. The test on made-up data shows that the sampler recovers this "
            "form. It does not show that reality has this form."
        )
        tradeoff = (
            "- Effect size and half-saturation point trade off against each other. So the model "
            "recovers individual point parameters less well than curves and shares. The "
            "Validation section states the direction of that bias."
        )
    else:
        form = (
            "- The model assumes one form: carry-over that decays geometrically (adstock), a "
            "Hill saturation curve and an additive baseline. [How it works](#how-it-works) "
            "defines these terms. The planned test on made-up data would check whether the "
            "sampler finds this form. It would not show that reality has this form."
        )
        tradeoff = (
            "- Effect size and half-saturation point trade off against each other. So the model "
            "would find individual point parameters less well than curves and shares."
        )
    items = [
        data,
        form,
        tradeoff,
        "- Weekly national data cannot separate channels whose spend moves together. The "
        "intervals widen accordingly. The optimiser stays inside the bounds that the config "
        "sets.",
        "- The optimiser assumes that response curves hold at new spend levels. It assumes "
        "that competitors do not react. It assumes that a constant weekly spend reaches its "
        "steady state.",
    ]
    if p and not p["diag"].get("pass_all", False):
        items.append(
            "- The sampler for the test on made-up data did not meet every diagnostic "
            "threshold. See `reports/layer_p/diagnostics.json` for the numbers and the "
            "attempts made."
        )
    if r and not r["diag"].get("pass_all", False):
        items.append(
            "- The sampler for the test on public demo data did not meet every diagnostic "
            "threshold. See `reports/layer_r/diagnostics.json`."
        )
    return "\n".join(items)


def status_line(p: dict, r: dict, dd: dict, run_date: date) -> str:
    steps = []
    if p:
        steps.append("the test on made-up data with a known answer (synthetic truth and "
                     "parameter recovery)")
    if r:
        steps.append("the test on public demo data")
    if dd:
        steps.append("the budget shift recommendation (budget optimiser and decision rule)")
    when = v("status_date", run_date.isoformat())
    stamp = "Last validated" if p else "Last rendered"
    return (
        f"Built steps: {and_join(steps, oxford=True) if steps else 'none yet'}. Everything in "
        f"this README regenerates from the three run commands above. {stamp}: {when}."
    )


_IF_RE = re.compile(r"^\{\{#(if|elif|else|endif)(?: ([a-z_]+))?\}\}$")


def apply_conditions(template: str, flags: dict[str, bool]) -> str:
    """Keep or drop template passages by test state.

    A marker sits alone on its line: {{#if name}}, {{#elif name}}, {{#else}}, {{#endif}}.
    Passages may nest. The marker lines never reach the README.
    """
    out: list[str] = []
    stack: list[dict] = []
    for line in template.split("\n"):
        m = _IF_RE.match(line.strip())
        if not m:
            if all(level["active"] for level in stack):
                out.append(line)
            continue
        kind, name = m.groups()
        if name is not None and name not in flags:
            raise ValueError(f"readme_template.md uses an unknown condition: {name}")
        if kind == "if":
            stack.append({"taken": flags[name], "active": flags[name]})
        elif not stack:
            raise ValueError(f"readme_template.md has {{{{#{kind}}}}} without {{{{#if}}}}")
        elif kind == "elif":
            top = stack[-1]
            top["active"] = not top["taken"] and flags[name]
            top["taken"] = top["taken"] or flags[name]
        elif kind == "else":
            top = stack[-1]
            top["active"], top["taken"] = not top["taken"], True
        else:
            stack.pop()
    if stack:
        raise ValueError("readme_template.md has an {{#if}} without {{#endif}}")
    return "\n".join(out)


def render(run_date: date) -> str:
    VALUES.clear()
    p, r = layer_p_values(), layer_r_values()
    # the budget shift recommendation reads the posterior of the public-demo fit
    dd = layer_d_values() if r else {}
    chart, alt = headline_values(p, r)
    template = (ROOT / "scripts" / "readme_template.md").read_text(encoding="utf-8")
    # A passage that reports a result appears only when the artifacts for that result exist.
    template = apply_conditions(
        template,
        {
            "p": bool(p),
            "r": bool(r),
            "dd": bool(dd),
            "rec": bool(dd) and bool(dd["decision"]["same_total"]["recommend"]),
            "p_or_r": bool(p or r),
            "p_and_r": bool(p and r),
            "all": bool(p and r and dd),
        },
    )
    fills = {
        "headline_chart": chart,
        "headline_alt": alt,
        "headline_caption": headline_caption(r),
        "share_table": share_table(r) if r else "",
        "method_bullets": method_bullets(p, r),
        "data_table": data_table(p, r, dd),
        "proof_section": proof_section(p),
        "holdout_section": holdout_section(p, r),
        "limitations": limitations(p, r),
        "validation_sentence": validation_sentence(p, r),
        "status_line": status_line(p, r, dd, run_date),
    }
    if dd:
        fills.update(decision_blocks(dd, run_date))
    text = template
    for key, value in fills.items():
        text = text.replace("{{" + key + "}}", value)
    # numbers: every other placeholder is a value recorded in reports/readme_values.json
    missing = sorted(set(re.findall(r"\{\{([^{}]+)\}\}", text)) - VALUES.keys())
    if missing:
        raise ValueError(f"readme_template.md has placeholders the renderer does not fill: {missing}")
    return re.sub(r"\{\{([^{}]+)\}\}", lambda m: VALUES[m.group(1)], text)


def last_date() -> date:
    """The date of the committed render, so a rerun without --date reproduces it."""
    values = REPORTS / "readme_values.json"
    if values.exists():
        stamp = read_json(values).get("status_date")
        if stamp:
            return date.fromisoformat(stamp)
    return date.today()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None,
                        help="last-validated date (default: the date of the committed render)")
    args = parser.parse_args()
    run_date = date.fromisoformat(args.date) if args.date else last_date()
    text = render(run_date)
    (ROOT / "README.md").write_text(text, encoding="utf-8")
    REPORTS.mkdir(exist_ok=True)
    with open(REPORTS / "readme_values.json", "w", encoding="utf-8") as fh:
        json.dump(VALUES, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"README.md rendered with {len(VALUES)} values from reports/")


if __name__ == "__main__":
    main()
