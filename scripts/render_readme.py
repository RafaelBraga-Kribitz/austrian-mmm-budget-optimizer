"""Render README.md from scripts/readme_template.md and the artifacts under reports/.

Every number that reaches the README is read from a file under reports/ and written
here; nothing is typed by hand. The values inserted are recorded in
reports/readme_values.json so tests/test_readme_numbers.py can check that the README
contains no number the reports do not.

    uv run python scripts/render_readme.py [--date 2026-09-15]
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

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


def layer_p_values() -> dict:
    d = REPORTS / "layer_p"
    if not (d / "run_info.json").exists():
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
    if not (d / "run_info.json").exists():
        return {}
    return {
        "info": read_json(d / "run_info.json"),
        "diag": read_json(d / "diagnostics.json"),
        "channels": pd.read_csv(d / "channel_contributions.csv"),
        "metrics": pd.read_csv(d / "holdout_metrics.csv"),
    }


def layer_d_values() -> dict:
    d = REPORTS / "layer_d"
    if not (d / "decision.json").exists():
        return {}
    return {
        "decision": read_json(d / "decision.json"),
        "table": pd.read_csv(d / "reallocation_table.csv"),
    }


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def headline(p: dict, r: dict, dd: dict) -> tuple[str, str, str]:
    lines = []
    if p:
        info = p["info"]
        cov = v("p_curve_cov", pct(info["curve_coverage_mean"], 0))
        covered = v("p_covered", info["parameters_covered"])
        total = v("p_total", info["parameters_total"])
        over = v("p_search_over", num(p["search"]["platform_over_true_pct"], 0))
        lines.append(
            f"On synthetic data with known truth, the estimated response curves cover the true "
            f"curves on {cov} percent of the observed spend range and {covered} of {total} true "
            f"parameters fall inside their 90 percent intervals; the platform report credits "
            f"Paid Search with {over} percent more revenue than it really adds, and gives the "
            f"offline channels nothing."
        )
    if r:
        parts = []
        for _, row in r["channels"].iterrows():
            ch = row["channel"]
            med = v("r_share_" + ch, pct(row["share_median"]))
            lo = v("r_lo_" + ch, pct(row["share_lo"]))
            hi = v("r_hi_" + ch, pct(row["share_hi"]))
            parts.append(f"{ch} {med} percent ({lo} to {hi})")
        lines.append(
            "On the public demo data (five named channels), the share of revenue each channel "
            "drives is " + "; ".join(parts) + "."
        )
    if dd:
        same = dd["decision"]["same_total"]
        verdict = "recommended" if same["recommend"] else "not recommended under the decision rule"
        med = v("d_gain_median", num(same["gain_pct_of_current_contribution_median"], 1))
        p10 = v("d_gain_p10", num(same["gain_pct_of_current_contribution_p10"], 1))
        lines.append(
            f"Reallocating the same budget gains {med} percent of current media contribution "
            f"(10th percentile {p10} percent); the shift is {verdict}."
        )
    if r:
        chart = "reports/layer_r/channel_contributions.png"
        alt = "Incremental contribution per channel on public demo data, with 90 percent intervals"
    else:
        chart = "reports/layer_p/response_curve_recovery.png"
        alt = "Response curve recovery on synthetic data: true curves against posterior bands"
    return chart, alt, "\n\n".join(lines)


def method_bullets(p: dict) -> str:
    diag = p["diag"] if p else {}
    fit = diag.get("fit", {})
    thresholds = diag.get("thresholds", {})
    weeks = v("m_weeks", p["info"]["weeks"]) if p else ""
    train = v("m_train", int(p["metrics"]["train_weeks"].iloc[0])) if p else ""
    sampler = v("m_sampler", fit.get("sampler", ""))
    chains = v("m_chains", fit.get("chains", ""))
    tune = v("m_tune", fit.get("tune", ""))
    draws = v("m_draws", fit.get("draws", ""))
    attempts = diag.get("attempts", [])
    first_ta = v("m_ta_start", attempts[0]["target_accept"]) if attempts else ""
    ta = v("m_ta", fit.get("target_accept", ""))
    ladder = (
        f"target acceptance {first_ta}, raised to {ta} by the recorded ladder after divergences"
        if attempts and len(attempts) > 1 else f"target acceptance {ta}"
    )
    rhat = v("m_rhat", thresholds.get("rhat_max", ""))
    ess = v("m_ess", int(thresholds.get("ess_min", 0)))
    return "\n".join(
        [
            f"- Data: weekly spend per channel and revenue. Layer P is a synthetic advertiser "
            f"with {weeks} weeks and five channels (TV, Radio, Print, Paid Search, Paid Social) "
            f"whose true parameters are written to data/synthetic/truth.json; Layer R is Robyn's "
            f"simulated weekly dataset with five named channels in money units (see "
            f"data/README.md). Public demo data; a real-data swap-in is planned.",
            "- Adstock: geometric carry-over per channel, so this week's spend keeps working in "
            "the following weeks with a decay rate the model estimates.",
            "- Saturation: a Hill curve per channel on the adstocked spend, with a half-saturation "
            "point and a slope, so returns diminish as spend grows.",
            "- Seasonality and controls: a linear trend, two yearly Fourier pairs, and one "
            "control (a public-holiday week indicator on Layer P, competitor sales on Layer R).",
            "- Priors: weakly informative and identical across channels, on scaled data, so that "
            "the estimates come from the data and not from a prior that knows the answer. Each "
            "prior and its reasoning is in the model docstring.",
            f"- Sampler: NUTS ({sampler}), {chains} chains, {tune} tuning and {draws} draws per "
            f"chain, {ladder}.",
            f"- Diagnostics: R-hat below {rhat}, effective sample size above {ess}, zero "
            f"divergences; written to diagnostics.json next to every fit.",
            f"- Holdout protocol: fit on the first {train} weeks, forecast the rest with the "
            f"actual spend, and report MAPE and 90 percent interval coverage against a "
            f"seasonal-naive and a ridge-regression baseline.",
        ]
    )


def proof_section(p: dict) -> str:
    if not p:
        return "Layer P has not run yet."
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
            largest = " (the largest channel by spend)" if row["spend_total"] == top_spend else ""
            true_share = v("pr_miss_true_" + ch, pct(row["true_share_of_revenue"]))
            lo = v("pr_miss_lo_" + ch, pct(row["share_lo"]))
            hi = v("pr_miss_hi_" + ch, pct(row["share_hi"]))
            bits.append(
                f"{ch}{largest}: true share {true_share} percent against an interval of "
                f"{lo} to {hi}"
            )
        share_sentence = (
            f"Revenue shares are covered for {shares_ok} of {n_ch} channels; the exception sits "
            f"just outside its interval: " + "; ".join(bits) + "."
        )
    worst = cur.loc[cur["curve_coverage_observed_range"].idxmin(), "channel"]
    return "\n\n".join(
        [
            "![Response curve recovery on synthetic data: true curves against posterior bands]"
            "(reports/layer_p/response_curve_recovery.png)",
            f"Before trusting the model on any advertiser's data, it had to recover a truth it "
            f"was handed. On the synthetic advertiser the estimated response curves cover the "
            f"true curves on {cov_mean} percent of the grid points inside the observed spend "
            f"range (worst channel, {worst}: {cov_min} percent), with a mean error of at most "
            f"{mae_max} percent of the true curve's height. {covered} of {total} individual "
            f"parameters fall inside their 90 percent intervals.",
            f"The misses follow a known trade-off, not a bug: {n_eff_over} of {n_eff} effect "
            f"sizes and {n_k_over} of {n_eff} half-saturation points have medians above the "
            f"truth, because a curve that rises higher but saturates later fits the same "
            f"observed weeks. Recovery is therefore judged on curves and shares, which are what "
            f"a budget decision uses, not on point parameters. {share_sentence}",
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


def holdout_section(p: dict, r: dict) -> str:
    out = []
    if p:
        m = p["metrics"]
        n_test = v("h_p_ntest", int(m["n_test"].iloc[0]))
        out.append(
            f"Layer P, synthetic data, {n_test} holdout weeks:\n\n"
            + holdout_table(m, "p") + "\n\n" + verdict_sentence(m, "p")
        )
    if r:
        m = r["metrics"]
        n_test = v("h_r_ntest", int(m["n_test"].iloc[0]))
        out.append(
            f"Layer R, public demo data, {n_test} holdout weeks:\n\n"
            + holdout_table(m, "r") + "\n\n" + verdict_sentence(m, "r")
        )
    return "\n\n".join(out) if out else "No holdout results yet."


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
            f"below nominal, so the intervals are slightly too narrow and the model is a little "
            f"overconfident; the baselines' wider intervals covered more."
        )
    elif short < -5.0:
        calibration = (
            f"Its 90 percent intervals covered {cov} percent of holdout weeks, more than the "
            f"nominal 90, so on this data the intervals are wider than they need to be."
        )
    else:
        calibration = (
            f"Its 90 percent intervals covered {cov} percent of holdout weeks, on target."
        )
    if mmm["mape"] <= best_other["mape"]:
        head = (
            "The MMM has the lowest point error here. Its case does not rest on that: the "
            "baselines say nothing about which channel earned the revenue."
        )
    else:
        name = best_other["model"].split(" (")[0].lower()
        head = (
            f"The MMM loses on point error to the {name} baseline on this data. That is "
            "reported as it comes out: the case for the MMM is interpretability (which "
            "channel earned the revenue, with intervals), not always accuracy."
        )
    return head + " " + calibration


def decision_section(dd: dict, run_date: date) -> str:
    if not dd:
        due = v("d_due", (run_date + timedelta(days=7)).isoformat())
        return f"Layer D (budget optimiser and decision rule): first results by {due}."
    dec = dd["decision"]
    table = dd["table"]
    same = table[table["scenario"] == "same_total"]
    rows = [
        "| Channel | Current weekly spend | Recommended | Change | Marginal ROAS at current "
        "(90 percent interval) | Marginal ROAS at recommended (90 percent interval) | "
        "Contribution at recommended (90 percent interval) |",
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
    s = dec["same_total"]
    verdict = "Recommend the shift." if s["recommend"] else "Hold: the rule is not met."
    gain_med = v("d_gain_med2", num(s["gain_pct_of_current_contribution_median"], 1))
    gain_p10 = v("d_gain_p10_2", num(s["gain_pct_of_current_contribution_p10"], 1))
    p_neg = v("d_p_neg", pct(s["probability_gain_negative"]))
    breakeven = v("d_breakeven", num(dec["breakeven_roas"]))
    margin = v("d_margin", pct(dec["contribution_margin"], 0))
    held_channels = [str(c) for c in s["held_channels"]]
    gate = (
        "The breakeven gate held " + " and ".join(held_channels) + " at current spend: the "
        "lower bound of their marginal ROAS interval falls below breakeven, so no budget moves "
        "toward them however high their median."
        if held_channels else
        "The breakeven gate did not bind: every channel's marginal ROAS lower bound stays "
        "above breakeven at the recommended spend."
    )
    text = [
        "Same total weekly budget, reallocated. Spend and contribution are weekly, in the "
        "dataset's money units; marginal ROAS is revenue per unit of spend:",
        "",
        "\n".join(rows),
        "",
        f"Gain from the reallocation: median {gain_med} percent of current media contribution, "
        f"10th percentile {gain_p10} percent, probability of a loss {p_neg} percent. {verdict}",
        "",
        f"Decision rule: {dec['decision_rule']} Breakeven ROAS is {breakeven} at a contribution "
        f"margin of {margin} percent (an assumption stated in the config). {gate}",
    ]
    if "plus_extra_budget" in dec:
        e = dec["plus_extra_budget"]
        extra = v("d_extra_year", money(dec["extra_budget_per_year"]))
        e_gain = v("d_extra_gain", num(e["gain_pct_of_current_contribution_median"], 1))
        e_p10 = v("d_extra_p10", num(e["gain_pct_of_current_contribution_p10"], 1))
        e_verdict = "recommend" if e["recommend"] else "hold"
        text += [
            "",
            f"With {extra} more per year, spread over 52 weeks, media contribution rises by a "
            f"median {e_gain} percent (10th percentile {e_p10} percent); the rule says "
            f"{e_verdict}. Where the extra budget goes, channel by channel, and how likely that "
            f"call is wrong, is in reports/layer_d/next_200k.md.",
        ]
    text += [
        "",
        "![Distribution of the gain from reallocation](reports/layer_d/reallocation_gain.png)",
    ]
    return "\n".join(text)


def limitations(p: dict, r: dict) -> str:
    items = [
        "- Layer R runs on Robyn's simulated weekly dataset: five named channels and revenue "
        "in the dataset's money units, whose currency its authors do not name. Shares, ROAS "
        "ratios and the breakeven test are meaningful; the amounts are not euros. No Austrian "
        "client data was used; a real-data swap-in is planned.",
        "- One model form (geometric adstock, Hill saturation, additive baseline) is assumed; "
        "recovery on Layer P shows the sampler recovers that form, not that reality has it.",
        "- Effect size and half-saturation trade off against each other, so individual point "
        "parameters are recovered less well than curves and shares; the proof section states "
        "the direction of that bias.",
        "- Weekly national data cannot separate channels whose spend moves together; the "
        "intervals widen accordingly and the optimiser stays inside the bounds set in the config.",
        "- The optimiser assumes response curves hold at new spend levels, competitors do not "
        "react, and a constant weekly spend reaches its steady state.",
    ]
    if p and not p["diag"].get("pass_all", False):
        items.append(
            "- The Layer P sampler did not meet every diagnostic threshold; see "
            "reports/layer_p/diagnostics.json for the numbers and the attempts made."
        )
    if r and not r["diag"].get("pass_all", False):
        items.append(
            "- The Layer R sampler did not meet every diagnostic threshold; see "
            "reports/layer_r/diagnostics.json."
        )
    return "\n".join(items)


def status_line(p: dict, r: dict, dd: dict, run_date: date) -> str:
    layers = []
    if p:
        layers.append("Layer P (synthetic truth and parameter recovery)")
    if r:
        layers.append("Layer R (public demo data)")
    if dd:
        layers.append("Layer D (budget optimiser and decision rule)")
    when = v("status_date", run_date.isoformat())
    return (
        f"Built layers: {', '.join(layers) if layers else 'none yet'}. Everything in this README "
        f"regenerates from the three commands above. Date: {when}."
    )


def render(run_date: date) -> str:
    p, r, dd = layer_p_values(), layer_r_values(), layer_d_values()
    chart, alt, lines = headline(p, r, dd)
    template = (ROOT / "scripts" / "readme_template.md").read_text(encoding="utf-8")
    fills = {
        "headline_chart": chart,
        "headline_alt": alt,
        "headline_lines": lines,
        "method_bullets": method_bullets(p),
        "proof_section": proof_section(p),
        "holdout_section": holdout_section(p, r),
        "decision_section": decision_section(dd, run_date),
        "limitations": limitations(p, r),
        "status_line": status_line(p, r, dd, run_date),
    }
    text = template
    for key, value in fills.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    run_date = date.fromisoformat(args.date)
    text = render(run_date)
    (ROOT / "README.md").write_text(text, encoding="utf-8")
    REPORTS.mkdir(exist_ok=True)
    with open(REPORTS / "readme_values.json", "w", encoding="utf-8") as fh:
        json.dump(VALUES, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"README.md rendered with {len(VALUES)} values from reports/")


if __name__ == "__main__":
    main()
