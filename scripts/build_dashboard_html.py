"""Build the static HTML twin of the Power BI dashboard: dashboards/html/index.html.

Reads the same ten CSV files under reports/exports/ that the Power BI project loads,
embeds them as inline JSON, and writes one self-contained page: no network, no CDN, no
external font or script. Text figures (cards, tables, captions) are rendered here so
they read without JavaScript; the charts are inline SVG drawn by the embedded script
from the same JSON. The output is deterministic: the same CSV files give a
byte-identical page. The only date on the page is the README's last-validated date,
read from reports/readme_values.json.

    uv run python scripts/build_dashboard_html.py [--check]

--check exits 1 when the committed page differs from a fresh build.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "reports" / "exports"
SRC = ROOT / "dashboards" / "html" / "src"
OUT = ROOT / "dashboards" / "html" / "index.html"

FILES = (
    "recommendation_allocation.csv",
    "recommendation_gain.csv",
    "contributions_weekly.csv",
    "roas_summary.csv",
    "response_curves.csv",
    "proof_parameter_recovery.csv",
    "proof_response_curves.csv",
    "proof_attribution_gap.csv",
    "proof_sampler_gates.csv",
    "holdout_metrics.csv",
)

# Page set, names and German subtitles as specified in docs/dashboard_handoff.md.
PAGES = (
    ("recommendation", "Recommendation", "Wohin der naechste Euro geht"),
    ("contributions", "Contributions", "Was jeder Kanal beitraegt"),
    ("response-curves", "Response curves", "Wo die Saettigung beginnt"),
    ("proof", "Proof", "Der Beweis auf bekannter Wahrheit"),
)

# Captions copied verbatim from docs/dashboard_handoff.md, "Captions to copy verbatim".
MONEY_CAPTION = (
    "Amounts are in the money units of the public demo dataset (Robyn), whose currency is "
    "not named; shares, ratios and the breakeven test are meaningful, the amounts are not "
    "euros."
)
GAIN_CAPTION = (
    "In-sample counterfactual under the fitted model; assumes response curves hold and "
    "competitors do not react. No channel moves more than fifty percent from its current "
    "spend."
)

SCENARIO_LABELS = {
    "same_total": "Same total budget",
    "plus_25_percent": "Budget plus 25 percent",
    "plus_extra_budget": "Plus the yearly extra budget",
}
LAYER_LABELS = {"layer_p": "Layer P (synthetic)", "layer_r": "Layer R (public demo)"}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def parse(value: str):
    """CSV cell to a Python value: empty to None, True/False to bool, numbers to numbers."""
    if value == "":
        return None
    if value in ("True", "False"):
        return value == "True"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def read(name: str) -> list[dict]:
    with open(EXPORTS / name, encoding="utf-8", newline="") as fh:
        return [{k: parse(v) for k, v in row.items()} for row in csv.DictReader(fh)]


def load() -> dict[str, list[dict]]:
    return {name.removesuffix(".csv"): read(name) for name in FILES}


def last_validated() -> str:
    path = ROOT / "reports" / "readme_values.json"
    if not path.exists():
        return ""
    return json.loads(path.read_text(encoding="utf-8")).get("status_date", "")


# ---------------------------------------------------------------------------
# Formatting: dot decimal, comma thousands, never a currency sign
# ---------------------------------------------------------------------------


def money(x: float) -> str:
    return f"{x:,.0f}"


def pct(fraction: float, digits: int = 1) -> str:
    return f"{100 * fraction:.{digits}f}%"


def pct_value(value: float, digits: int = 1, signed: bool = False) -> str:
    return f"{value:+.{digits}f}%" if signed else f"{value:.{digits}f}%"


def ratio(x: float) -> str:
    return f"{x:.2f}"


def interval(lo: float, hi: float, fn) -> str:
    return f"{fn(lo)} to {fn(hi)}"


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


# ---------------------------------------------------------------------------
# HTML pieces
# ---------------------------------------------------------------------------


def kpi(label: str, value: str, note: str = "", key: str = "") -> str:
    data = f' data-kpi="{esc(key)}"' if key else ""
    note_html = f'<p class="kpi-note">{esc(note)}</p>' if note else ""
    return (
        f'<div class="kpi"{data}><p class="kpi-label">{esc(label)}</p>'
        f'<p class="kpi-value">{esc(value)}</p>{note_html}</div>'
    )


def table(caption: str, head: list[str], rows: list[list[str]], numeric: set[int],
          cls: str = "", foot: str = "") -> str:
    th = "".join(
        f'<th scope="col"{" class=num" if i in numeric else ""}>{esc(h)}</th>'
        for i, h in enumerate(head)
    )
    body = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            tag = "th scope=row" if i == 0 else "td"
            klass = ' class="num"' if i in numeric else ""
            cells.append(f"<{tag}{klass}>{cell}</{tag.split()[0]}>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    extra = f" {cls}" if cls else ""
    return (
        f'<div class="table-wrap{extra}"><table><caption>{esc(caption)}</caption>'
        f"<thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody>{foot}</table></div>"
    )


def data_table(caption: str, head: list[str], rows: list[list[str]], numeric: set[int]) -> str:
    """Screen-reader and keyboard fallback under a chart, collapsed by default."""
    return (
        '<details class="data-table"><summary>Data table</summary>'
        + table(caption, head, rows, numeric)
        + "</details>"
    )


def chart(chart_id: str, title: str, desc: str, height_class: str = "") -> str:
    klass = f"chart {height_class}".strip()
    return (
        f'<figure class="card"><figcaption><h3 class="chart-title" id="{chart_id}-t">'
        f"{esc(title)}</h3></figcaption>"
        f'<div class="{klass}" id="{chart_id}" role="group" aria-labelledby="{chart_id}-t" '
        f'aria-describedby="{chart_id}-d"></div>'
        f'<p class="chart-desc" id="{chart_id}-d">{esc(desc)}</p>'
    )


def page_head(idx: int) -> str:
    slug, name, subtitle = PAGES[idx]
    return (
        f'<section class="page" id="panel-{slug}" role="tabpanel" aria-labelledby="tab-{slug}" '
        f'tabindex="0"{"" if idx == 0 else " hidden"}>'
        f'<header class="page-head"><h2>{esc(name)}</h2>'
        f'<p class="subtitle" lang="de">{esc(subtitle)}</p></header>'
    )


def provenance(sources: str, extra: list[str] | None = None) -> str:
    lines = [
        f"<p><span class=\"tag\">SIMULATED</span> Source: {sources}. Intervals are 90 percent "
        "(5th to 95th percentile of the posterior draws).</p>"
    ]
    for e in extra or []:
        lines.append(f"<p>{esc(e)}</p>")
    return '<footer class="provenance">' + "".join(lines) + "</footer>"


def code(path: str) -> str:
    return f"<code>{esc(path)}</code>"


# --- Page 1 ------------------------------------------------------------------


def page_recommendation(d: dict) -> str:
    gain = {row["scenario"]: row for row in d["recommendation_gain"]}
    order = [s for s in SCENARIO_LABELS if s in gain] + [
        s for s in gain if s not in SCENARIO_LABELS
    ]
    alloc = d["recommendation_allocation"]
    out = [page_head(0)]
    out.append('<div class="controls" role="radiogroup" aria-label="Scenario">')
    for i, s in enumerate(order):
        checked = "true" if i == 0 else "false"
        out.append(
            f'<button type="button" role="radio" class="seg" data-scenario="{esc(s)}" '
            f'aria-checked="{checked}" tabindex="{0 if i == 0 else -1}">'
            f"{esc(SCENARIO_LABELS.get(s, s))}</button>"
        )
    out.append("</div>")
    for i, s in enumerate(order):
        g = gain[s]
        verdict = "Recommend" if g["recommend"] else "Hold"
        hidden = "" if i == 0 else " hidden"
        out.append(f'<div class="kpis" data-scenario-block="{esc(s)}"{hidden}>')
        out.append(kpi("Median gain", pct_value(g["gain_pct_of_contribution_median"]),
                       "of current media contribution", key=f"{s}-gain-median"))
        out.append(kpi("10th percentile gain", pct_value(g["gain_pct_of_contribution_p10"]),
                       "nine in ten draws gain at least this", key=f"{s}-gain-p10"))
        out.append(kpi("Probability of a loss", pct(g["probability_gain_negative"]),
                       "share of posterior draws", key=f"{s}-loss"))
        out.append(kpi("Verdict of the rule", verdict,
                       f"breakeven ROAS {ratio(g['breakeven_roas'])}", key=f"{s}-verdict"))
        out.append(kpi("Total weekly budget", money(g["total_weekly_budget"]),
                       "dataset money units, not euros", key=f"{s}-budget"))
        out.append("</div>")
    out.append(f'<p class="caption">{esc(GAIN_CAPTION)} In the two extra-budget scenarios '
               "the budget increase is added on top of that bound (LIMITATIONS.md, section "
               "5).</p>")
    out.append('<div class="grid two">')
    out.append(chart("c-spend", "Current against recommended weekly spend",
                     "Horizontal bars per channel: current weekly spend in grey, the selected "
                     "scenario's recommendation in blue, in the dataset's money units."))
    out.append(data_table(
        "Weekly spend per channel and scenario, dataset money units",
        ["Channel", "Scenario", "Current", "Recommended", "Change"],
        [[esc(r["channel"]), esc(SCENARIO_LABELS.get(r["scenario"], r["scenario"])),
          money(r["current_spend"]), money(r["recommended_spend"]),
          pct_value(r["delta_pct"], 1, signed=True)] for r in alloc],
        {2, 3, 4}))
    out.append("</figure>")
    out.append(chart("c-mroas", "Marginal ROAS at current spend, against breakeven",
                     "Dot and 90 percent interval per channel on a log scale; the dashed line "
                     "is breakeven ROAS. Blue: the channel receives budget in the selected "
                     "scenario."))
    out.append("</figure></div>")
    for i, s in enumerate(order):
        rows = []
        for r in (r for r in alloc if r["scenario"] == s):
            rule = '<span class="flag">Held by rule</span>' if r["held_by_rule"] else ""
            rows.append([
                esc(r["channel"]),
                money(r["current_spend"]),
                money(r["recommended_spend"]),
                pct_value(r["delta_pct"], 1, signed=True),
                f'{ratio(r["marginal_roas_current_median"])} '
                f'<span class="iv">({interval(r["marginal_roas_current_lo"], r["marginal_roas_current_hi"], ratio)})</span>',  # noqa: E501
                f'{ratio(r["marginal_roas_recommended_median"])} '
                f'<span class="iv">({interval(r["marginal_roas_recommended_lo"], r["marginal_roas_recommended_hi"], ratio)})</span>',  # noqa: E501
                f'{money(r["contribution_recommended_median"])} '
                f'<span class="iv">({interval(r["contribution_recommended_lo"], r["contribution_recommended_hi"], money)})</span>',  # noqa: E501
                rule,
            ])
        hidden = "" if i == 0 else " hidden"
        out.append(f'<div data-scenario-block="{esc(s)}"{hidden}>')
        out.append(table(
            f"Per channel, {SCENARIO_LABELS.get(s, s).lower()}: weekly spend in dataset money "
            "units, marginal ROAS and contribution with 90 percent intervals",
            ["Channel", "Current weekly spend", "Recommended", "Change",
             "Marginal ROAS at current", "Marginal ROAS at recommended",
             "Contribution at recommended", "Rule"],
            rows, {1, 2, 3, 4, 5, 6}, cls="wide"))
        held = gain[s]["held_channels"] or "none"
        out.append(f'<p class="note">Held by the rule in this scenario: {esc(held)}.</p></div>')
    out.append(
        '<p class="note">Channels marked <span class="flag">Held by rule</span> '
        "(<code>held_by_rule</code>) were held at current spend by the breakeven gate: the "
        "lower bound of their marginal ROAS interval falls below breakeven ROAS, so no budget "
        "moves toward them however high their median.</p>"
    )
    out.append(provenance(
        f"{code('reports/exports/recommendation_allocation.csv')} and "
        f"{code('recommendation_gain.csv')} (Layer D on the Layer R posterior)",
        [MONEY_CAPTION]))
    out.append("</section>")
    return "\n".join(out)


# --- Page 2 ------------------------------------------------------------------


def page_contributions(d: dict) -> str:
    roas = d["roas_summary"]
    weekly = d["contributions_weekly"]
    weeks = sorted({r["week"] for r in weekly})
    top = max(roas, key=lambda r: r["share_median"])
    wide = max(roas, key=lambda r: r["share_hi"] - r["share_lo"])
    out = [page_head(1), '<div class="kpis">']
    out.append(kpi("Largest revenue share", f"{top['channel']} {pct(top['share_median'])}",
                   f"90 percent interval {interval(top['share_lo'], top['share_hi'], pct)}",
                   key="top-share"))
    out.append(kpi("Widest share interval", wide["channel"],
                   f"{interval(wide['share_lo'], wide['share_hi'], pct)}; its median alone "
                   "is no basis for moving budget", key="wide-share"))
    out.append(kpi("Weeks decomposed", str(len(weeks)),
                   f"from {weekly[0]['week_start']} to {weekly[-1]['week_start']}",
                   key="weeks"))
    out.append("</div>")
    channels = list(dict.fromkeys(r["channel"] for r in weekly))
    out.append('<div class="controls chips" role="group" aria-label="Channels in the chart">')
    for i, ch in enumerate(channels):
        out.append(
            f'<button type="button" class="chip" data-channel="{esc(ch)}" aria-pressed="true">'
            f'<span class="sw sw-{i}" aria-hidden="true"></span>{esc(ch)}</button>'
        )
    out.append("</div>")
    out.append(chart("c-area", "Weekly revenue decomposition by channel, posterior median",
                     "Stacked areas per week: Baseline (revenue the model attributes to no "
                     "channel) at the bottom, each channel's median contribution above; the "
                     "line is observed revenue, and its distance from the top of the stack is "
                     "the weekly residual; weeks where the line rises far above the stack are "
                     "revenue the model does not explain. Media "
                     "is a thin layer on top of Baseline: hide Baseline with the buttons above "
                     "to rescale the axis to media only.", "tall"))
    by_week: dict[int, dict] = {}
    for r in weekly:
        by_week.setdefault(r["week"], {"week_start": r["week_start"],
                                       "revenue": r["revenue"]})[r["channel"]] = r["median"]
    out.append(data_table(
        "Weekly contribution per channel, posterior median, dataset money units",
        ["Week start"] + channels + ["Revenue"],
        [[esc(v["week_start"])] + [money(v[c]) for c in channels] + [money(v["revenue"])]
         for _, v in sorted(by_week.items())],
        set(range(1, len(channels) + 2))))
    out.append("</figure>")
    rows = []
    for r in roas:
        rows.append([
            esc(r["channel"]),
            f'{ratio(r["roas_median"])} <span class="iv">'
            f'({interval(r["roas_lo"], r["roas_hi"], ratio)})</span>',
            f'<span class="glyph" data-lo="{r["roas_lo"]}" data-mid="{r["roas_median"]}" '
            f'data-hi="{r["roas_hi"]}" aria-hidden="true"></span>',
            f'{pct(r["share_median"])} <span class="iv">'
            f'({interval(r["share_lo"], r["share_hi"], pct)})</span>',
            money(r["spend_total"]),
            money(r["spend_mean_week"]),
        ])
    out.append('<section class="card" aria-labelledby="roas-t">'
               '<h3 class="chart-title" id="roas-t">ROAS and revenue share per channel</h3>')
    out.append(table(
        "ROAS (revenue per unit of spend) and share of revenue, median with 90 percent "
        "interval; spend in dataset money units",
        ["Channel", "ROAS (90% interval)", "ROAS interval, log scale", "Revenue share",
         "Total spend", "Mean weekly spend"],
        rows, {1, 3, 4, 5}, cls="wide roas",
        foot='<tfoot aria-hidden="true"><tr><td></td><td></td><td><span class="glyph" '
             'data-axis="1"></span></td><td></td><td></td><td></td></tr></tfoot>'))
    out.append('<p class="chart-desc">Interval column: each bar spans the 90 percent ROAS '
               "interval on one shared log scale, the dot marks the median and the thin rule "
               "a ROAS of 1.</p>"
               "</section>")
    out.append(provenance(
        f"{code('reports/exports/contributions_weekly.csv')} and "
        f"{code('roas_summary.csv')} (Layer R, Robyn public demo data)", [MONEY_CAPTION]))
    out.append("</section>")
    return "\n".join(out)


# --- Page 3 ------------------------------------------------------------------


def page_curves(d: dict) -> str:
    curves = d["response_curves"]
    channels = list(dict.fromkeys(r["channel"] for r in curves))
    out = [page_head(2)]
    out.append('<p class="lead">One curve per channel: weekly contribution against weekly '
               "spend at the steady state of a constant weekly spend. The blue rule marks the "
               "channel's current weekly spend; the shaded zone lies beyond the largest "
               "observed week, where the curve is an extrapolation. Each curve ends at 1.5 "
               "times the largest observed weekly spend. Each panel has its own axes: compare "
               "shapes across channels, read levels from the axis.</p>")
    out.append('<div class="grid three">')
    for i, ch in enumerate(channels):
        cid = f"c-curve-{i}"
        out.append(f'<figure class="card"><figcaption><h3 class="chart-title" id="{cid}-t">'
                   f"{esc(ch)}</h3></figcaption>"
                   f'<div class="chart small" id="{cid}" data-curve="{esc(ch)}" role="group" '
                   f'aria-labelledby="{cid}-t" aria-describedby="{cid}-d"></div>'
                   f'<p class="chart-desc" id="{cid}-d">{esc(ch)} response curve: posterior '
                   "median with its 90 percent band, current weekly spend marked.</p>")
        rows = [r for r in curves if r["channel"] == ch]
        out.append(data_table(
            f"{ch}: weekly contribution by weekly spend, dataset money units",
            ["Weekly spend", "Median", "lo (5th pct)", "hi (95th pct)"],
            [[money(r["spend"]), money(r["median"]), money(r["lo"]), money(r["hi"])]
             for r in rows], {0, 1, 2, 3}))
        out.append("</figure>")
    out.append("</div>")
    rows = []
    for ch in channels:
        r = next(r for r in curves if r["channel"] == ch)
        rows.append([esc(ch), money(r["current_spend"]), money(r["observed_max_spend"])])
    out.append(table("Where each channel stands, weekly spend in dataset money units",
                     ["Channel", "Current weekly spend", "Largest observed week"], rows,
                     {1, 2}))
    out.append(provenance(
        f"{code('reports/exports/response_curves.csv')} (Layer R, Robyn public demo data)",
        [MONEY_CAPTION]))
    out.append("</section>")
    return "\n".join(out)


# --- Page 4 ------------------------------------------------------------------


def page_proof(d: dict) -> str:
    params = d["proof_parameter_recovery"]
    gates = d["proof_sampler_gates"]
    gap = d["proof_attribution_gap"]
    hold = d["holdout_metrics"]
    covered = sum(1 for r in params if r["covered"])
    passing = sum(1 for r in gates if r["pass_all"])
    p_mmm = next(r for r in hold if r["layer"] == "layer_p" and r["model"] == "Bayesian MMM")
    reported = [r for r in gap if r["platform_over_true_pct"] is not None]
    over = max(reported, key=lambda r: r["platform_over_true_pct"]) if reported else None
    search = next((r for r in gap if r["channel"] == "Paid Search"), over)
    out = [page_head(3), '<div class="kpis">']
    out.append(kpi("True parameters inside their interval", f"{covered} of {len(params)}",
                   "90 percent posterior intervals, synthetic advertiser", key="params"))
    out.append(kpi("Fits passing every sampler gate", f"{passing} of {len(gates)}",
                   "R-hat, effective sample size, divergences", key="gates"))
    out.append(kpi("MMM holdout error, Layer P", pct(p_mmm["mape"]),
                   f"MAPE over {p_mmm['n_test']} unseen weeks; coverage "
                   f"{pct(p_mmm['coverage_90'], 0)}", key="mape-p"))
    if search is not None and search["platform_over_true_pct"] is not None:
        out.append(kpi("Platform over-credit, " + search["channel"],
                       f"{search['platform_over_true_pct']:+.1f}%",
                       f"platform-reported over true incremental revenue; share gap "
                       f"{search['gap_pp']:+.1f} pp", key="overcredit"))
    out.append("</div>")
    out.append('<div class="grid two">')
    out.append(chart("c-params", "Posterior against the true value, per parameter",
                     "Each row is one parameter of the synthetic advertiser, scaled by its "
                     "true value: the vertical line at 1 is the truth, the dot the posterior "
                     "median, the bar the 90 percent interval (log scale). Red rows miss the "
                     "truth.", "params"))
    out.append(data_table(
        "True value against posterior median and 90 percent interval, per parameter",
        ["Parameter", "Unit", "True", "Median", "lo (5th pct)", "hi (95th pct)", "Covered"],
        [[esc(r["parameter"]), esc(r["unit"]), f"{r['true']:,.3g}", f"{r['median']:,.3g}",
          f"{r['lo']:,.3g}", f"{r['hi']:,.3g}", "yes" if r["covered"] else "no"]
         for r in params], {2, 3, 4, 5}))
    out.append("</figure>")
    out.append(chart("c-gap", "Platform-reported share against true share",
                     "Hollow dot: the channel's share of platform-attributed revenue in the "
                     "simulated platform report. Blue dot: its true share of incremental media "
                     "contribution. The two shares use different denominators; neither is "
                     "total revenue."))
    gap_rows = []
    for r in gap:
        ratio_txt = ("no platform report" if r["platform_over_true_pct"] is None
                     else f"{r['platform_over_true_pct']:+.1f}%")
        gap_rows.append([esc(r["channel"]), pct(r["platform_share"]), pct(r["true_share"]),
                         f"{r['gap_pp']:+.1f}", ratio_txt])
    out.append(table(
        "Attribution gap per channel, synthetic advertiser",
        ["Channel", "Platform share", "True share", "Gap, pp", "Platform over true"],
        gap_rows, {1, 2, 3, 4}))
    out.append('<p class="note">Offline channels receive no platform credit, so their '
               "platform-over-true ratio is undefined: shown as \"no platform report\", not "
               "as zero. Their gap is the under-credit.</p></figure></div>")
    out.append('<h3 class="section-title">True response curves over the recovered bands</h3>'
               '<p class="chart-desc"><span class="key key-hl" aria-hidden="true"></span> true '
               'curve (disclosed data-generating process) <span class="key key-ink" '
               'aria-hidden="true"></span> recovered posterior median, grey band 90 percent '
               "interval, shaded zone beyond the largest observed week.</p>")
    out.append('<div class="grid three">')
    pcurves = d["proof_response_curves"]
    for i, ch in enumerate(dict.fromkeys(r["channel"] for r in pcurves)):
        cid = f"c-pcurve-{i}"
        out.append(f'<figure class="card"><figcaption><h3 class="chart-title" id="{cid}-t">'
                   f"{esc(ch)}</h3></figcaption>"
                   f'<div class="chart small" id="{cid}" data-pcurve="{esc(ch)}" role="group" '
                   f'aria-labelledby="{cid}-t" aria-describedby="{cid}-d"></div>'
                   f'<p class="chart-desc" id="{cid}-d">{esc(ch)}: true curve in blue over '
                   "the recovered median and 90 percent band.</p>")
        rows = [r for r in pcurves if r["channel"] == ch]
        out.append(data_table(
            f"{ch}: true and recovered weekly contribution by weekly spend",
            ["Weekly spend", "True", "Median", "lo (5th pct)", "hi (95th pct)"],
            [[money(r["spend"]), money(r["true"]), money(r["median"]), money(r["lo"]),
              money(r["hi"])] for r in rows], {0, 1, 2, 3, 4}))
        out.append("</figure>")
    out.append("</div>")
    out.append('<section class="card" aria-labelledby="gates-t"><h3 class="chart-title" '
               'id="gates-t">Sampler gates, last recorded attempt per fit</h3>')
    out.append(table(
        "Sampler diagnostics per fit",
        ["Fit", "Max R-hat", "Min ESS bulk", "Min ESS tail", "Divergences", "Attempts",
         "Target accept", "Pass"],
        [[esc(f"{LAYER_LABELS.get(r['layer'], r['layer'])}, {r['fit']}"),
          f"{r['max_rhat']:.3f}", money(r["min_ess_bulk"]), money(r["min_ess_tail"]),
          str(r["divergences"]), str(r["attempts"]), f"{r['final_target_accept']:.2f}",
          "pass" if r["pass_all"] else "fail"] for r in gates],
        {1, 2, 3, 4, 5, 6}))
    out.append("</section>")
    out.append('<section class="card" aria-labelledby="hold-t"><h3 class="chart-title" '
               'id="hold-t">Holdout error and interval coverage</h3>')
    out.append(table(
        "Holdout MAPE and 90 percent interval coverage, both layers",
        ["Model", "Layer", "MAPE", "90% coverage", "Holdout weeks"],
        [[esc(r["model"]), esc(LAYER_LABELS.get(r["layer"], r["layer"])), pct(r["mape"]),
          pct(r["coverage_90"], 0), str(r["n_test"])] for r in hold],
        {2, 3, 4}))
    out.append('<p class="note">On the public demo data ridge regression beats the MMM on '
               "point error; the case for the MMM is which channel earned the revenue, with "
               "intervals.</p></section>")
    out.append(provenance(
        f"{code('reports/exports/proof_parameter_recovery.csv')}, "
        f"{code('proof_response_curves.csv')}, {code('proof_attribution_gap.csv')}, "
        f"{code('proof_sampler_gates.csv')}, {code('holdout_metrics.csv')} (Layer P synthetic "
        "advertiser with disclosed truth; holdout on both layers)",
        ["The platform report on Layer P is generated by two stated assumptions about "
         "over-crediting; the gap tests direction and ordering, not the magnitude on any real "
         "platform (LIMITATIONS.md, section 9)."]))
    out.append("</section>")
    return "\n".join(out)


def tabs() -> str:
    out = ['<nav class="tabs" role="tablist" aria-label="Dashboard pages">']
    for i, (slug, name, subtitle) in enumerate(PAGES):
        sel = "true" if i == 0 else "false"
        out.append(
            f'<button type="button" role="tab" id="tab-{slug}" aria-controls="panel-{slug}" '
            f'aria-selected="{sel}" tabindex="{0 if i == 0 else -1}" data-slug="{slug}">'
            f'<span class="tab-n">{i + 1}</span> {esc(name)}'
            f'<span class="tab-de" lang="de">{esc(subtitle)}</span></button>'
        )
    out.append("</nav>")
    return "\n".join(out)


def render(data: dict[str, list[dict]] | None = None) -> str:
    data = data or load()
    template = (SRC / "template.html").read_text(encoding="utf-8")
    css = (SRC / "dashboard.css").read_text(encoding="utf-8")
    js = (SRC / "dashboard.js").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    payload = payload.replace("</", "<\\/")
    validated = last_validated()
    body = "\n".join([tabs(), page_recommendation(data), page_contributions(data),
                      page_curves(data), page_proof(data)])
    fills = {
        "{{css}}": css,
        "{{js}}": js,
        "{{data}}": payload,
        "{{body}}": body,
        "{{validated}}": esc(validated or "not recorded"),
        "{{money_caption}}": esc(MONEY_CAPTION),
    }
    out = template
    for key, value in fills.items():
        out = out.replace(key, value)
    if "{{" in out.replace(payload, "").replace(js, ""):
        raise ValueError("template placeholder left unfilled")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the committed page differs from a fresh build")
    args = parser.parse_args()
    page = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != page:
            print(f"{OUT.relative_to(ROOT)} is stale; run scripts/build_dashboard_html.py")
            return 1
        print(f"{OUT.relative_to(ROOT)} matches a fresh build")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(ROOT)}: {len(page.encode('utf-8')):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
