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


def headline(p: dict, r: dict, dd: dict) -> tuple[str, str, str]:
    lines = []
    if p:
        info = p["info"]
        covered = v("p_covered", info["parameters_covered"])
        total = v("p_total", info["parameters_total"])
        gap = v("p_search_gap", num(p["search"]["gap_pp"], 1))
        lines.append(
            f"On synthetic data with known truth, {covered} of {total} true parameters fall "
            f"inside their 90 percent posterior intervals, and the platform-reported share of "
            f"Paid Search is {gap} percentage points above its true incremental share."
        )
    if r:
        parts = []
        for _, row in r["channels"].iterrows():
            ch = row["channel"]
            med = v("r_share_" + ch, pct(row["share_median"]))
            lo = v("r_lo_" + ch, pct(row["share_lo"]))
            hi = v("r_hi_" + ch, pct(row["share_hi"]))
            parts.append(f"{ch} {med} percent of revenue ({lo} to {hi})")
        lines.append(
            "On the public demo data, incremental contribution is " + "; ".join(parts) + "."
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
        chart = "reports/layer_p/parameter_recovery.png"
        alt = "Parameter recovery on synthetic data: true values against posterior intervals"
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
            f"whose true parameters are written to data/synthetic/truth.json; Layer R is the "
            f"public example dataset shipped with pymc-marketing (see data/README.md). Public "
            f"demo data; a real-data swap-in is planned.",
            "- Adstock: geometric carry-over per channel, so this week's spend keeps working in "
            "the following weeks with a decay rate the model estimates.",
            "- Saturation: a Hill curve per channel on the adstocked spend, with a half-saturation "
            "point and a slope, so returns diminish as spend grows.",
            "- Seasonality and controls: a linear trend, two yearly Fourier pairs, and one "
            "control (a public-holiday week indicator on Layer P, an event week on Layer R).",
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
            + holdout_table(m, "p") + "\n\n" + winner_sentence(m)
        )
    if r:
        m = r["metrics"]
        n_test = v("h_r_ntest", int(m["n_test"].iloc[0]))
        out.append(
            f"Layer R, public demo data, {n_test} holdout weeks:\n\n"
            + holdout_table(m, "r") + "\n\n" + winner_sentence(m)
        )
    return "\n\n".join(out) if out else "No holdout results yet."


def winner_sentence(m: pd.DataFrame) -> str:
    mmm = m[m["model"] == "Bayesian MMM"].iloc[0]
    others = m[m["model"] != "Bayesian MMM"]
    best_other = others.loc[others["mape"].idxmin()]
    if mmm["mape"] <= best_other["mape"]:
        return (
            "The MMM has the lowest point error here. Its case does not rest on that: the "
            "baselines say nothing about which channel earned the revenue, and the MMM's "
            "interval coverage is what makes its uncertainty usable."
        )
    name = best_other["model"].split(" (")[0].lower()
    return (
        f"The MMM loses on point error to the {name} baseline on this data. That is reported "
        "as it comes out: the case for the MMM is calibration and interpretability (which "
        "channel earned the revenue, with intervals), not always accuracy."
    )


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
        cur = v(f"d_cur_{ch}", num(r["current_spend"], 3))
        rec = v(f"d_rec_{ch}", num(r["recommended_spend"], 3))
        delta = v(f"d_delta_{ch}", signed(r["delta_pct"]))
        mr_cur = v(f"d_mr_cur_{ch}", num(r["marginal_roas_current_median"]))
        mr_cur_lo = v(f"d_mr_cur_lo_{ch}", num(r["marginal_roas_current_lo"]))
        mr_cur_hi = v(f"d_mr_cur_hi_{ch}", num(r["marginal_roas_current_hi"]))
        mr_rec = v(f"d_mr_rec_{ch}", num(r["marginal_roas_recommended_median"]))
        mr_rec_lo = v(f"d_mr_rec_lo_{ch}", num(r["marginal_roas_recommended_lo"]))
        mr_rec_hi = v(f"d_mr_rec_hi_{ch}", num(r["marginal_roas_recommended_hi"]))
        c_rec = v(f"d_c_rec_{ch}", num(r["contribution_recommended_median"], 0))
        c_lo = v(f"d_c_rec_lo_{ch}", num(r["contribution_recommended_lo"], 0))
        c_hi = v(f"d_c_rec_hi_{ch}", num(r["contribution_recommended_hi"], 0))
        rows.append(
            f"| {ch} | {cur} | {rec} | {delta} percent | {mr_cur} ({mr_cur_lo} to {mr_cur_hi}) | "
            f"{mr_rec} ({mr_rec_lo} to {mr_rec_hi}) | {c_rec} ({c_lo} to {c_hi}) |"
        )
    s = dec["same_total"]
    p25 = dec["plus_25_percent"]
    verdict = "Recommend the shift." if s["recommend"] else "Hold: the rule is not met."
    gain_med = v("d_gain_med2", num(s["gain_pct_of_current_contribution_median"], 1))
    gain_p10 = v("d_gain_p10_2", num(s["gain_pct_of_current_contribution_p10"], 1))
    p_neg = v("d_p_neg", pct(s["probability_gain_negative"]))
    breakeven = v("d_breakeven", num(dec["breakeven_roas"]))
    margin = v("d_margin", pct(dec["contribution_margin"], 0))
    p25_gain = v("d_p25_gain", num(p25["gain_pct_of_current_contribution_median"], 1))
    text = [
        "Same total weekly budget, reallocated (spend in the data's index-scaled units, "
        "contribution in revenue units per week):",
        "",
        "\n".join(rows),
        "",
        f"Gain from the reallocation: median {gain_med} percent of current media contribution, "
        f"10th percentile {gain_p10} percent, probability of a loss {p_neg} percent. {verdict}",
        "",
        f"Decision rule: {dec['decision_rule']} Breakeven ROAS is {breakeven} at a contribution "
        f"margin of {margin} percent (an assumption stated in the config).",
        "",
        f"With 25 percent more budget the gain is a median {p25_gain} percent of current "
        f"contribution; where the extra budget goes, and how likely that call is wrong, is in "
        f"reports/layer_d/next_200k.md.",
        "",
        "![Distribution of the gain from reallocation](reports/layer_d/reallocation_gain.png)",
    ]
    return "\n".join(text)


def limitations(p: dict, r: dict) -> str:
    items = [
        "- Layer R runs on public demo data with two unnamed, index-scaled media channels, so "
        "its shares and ratios are meaningful and its money amounts are not. No Austrian client "
        "data was used; a real-data swap-in is planned.",
        "- One model form (geometric adstock, Hill saturation, additive baseline) is assumed; "
        "recovery on Layer P shows the sampler recovers that form, not that reality has it.",
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
        f"Built layers: {', '.join(layers) if layers else 'none yet'}. The package and Layer P "
        f"are on main; Layers R and D are on the build/ambo branch pending review. Date: {when}."
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
