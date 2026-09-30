"""Write reports/memo_EN.md, the one-page English decision memo, from reports/.

Every number is read from the Layer D and Layer P artifacts; the values inserted are
recorded in reports/memo_values.json so tests/test_readme_numbers.py can check them
and compare the committed memo with a fresh render.

    uv run python scripts/render_memo.py [--pdf]

``--pdf`` also builds reports/memo_EN.pdf with pandoc (LaTeX engine, 1 inch margins)
and records the SHA-256 of the Markdown it was built from in
reports/memo_EN.pdf.sha256, so a memo that changed without a PDF rebuild fails the
test suite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
MEMO = REPORTS / "memo_EN.md"
PDF = REPORTS / "memo_EN.pdf"
PDF_SOURCE_HASH = REPORTS / "memo_EN.pdf.sha256"
VALUES: dict[str, str] = {}


def v(key: str, value) -> str:
    text = str(value)
    VALUES[key] = text
    return text


def pct(x: float, digits: int = 1) -> str:
    return f"{100 * float(x):.{digits}f}"


def num(x: float, digits: int = 1) -> str:
    return f"{float(x):.{digits}f}"


def exact(x: float) -> str:
    """Three decimals and an ellipsis, with a typographic minus, for the source list."""
    return f"{float(x):.3f}".replace("-", "−") + "…"


def _join(names: list[str]) -> str:
    return " and ".join(names) if len(names) <= 2 else ", ".join(names[:-1]) + " and " + names[-1]


def render() -> str:
    VALUES.clear()
    with open(REPORTS / "layer_d" / "decision.json", encoding="utf-8") as fh:
        dec = json.load(fh)
    table = pd.read_csv(REPORTS / "layer_d" / "reallocation_table.csv")
    gap = pd.read_csv(REPORTS / "layer_p" / "attribution_gap.csv")
    same = dec["same_total"]
    rows = table[table["scenario"] == "same_total"].reset_index(drop=True)
    search = gap[gap["channel"] == "Paid Search"].iloc[0]

    up = [r["channel"] for _, r in rows.iterrows() if r["delta_pct"] > 0.5]
    down = [r["channel"] for _, r in rows.iterrows() if r["delta_pct"] < -0.5]
    flat = [r["channel"] for _, r in rows.iterrows() if abs(r["delta_pct"]) <= 0.5]
    moves = []
    if up:
        moves.append(f"more {_join(up)}")
    if down:
        moves.append(f"less {_join(down)}")
    if flat:
        moves.append(f"no change to {' or '.join(flat)}")
    mix = ", ".join(moves[:-1]) + ", and " + moves[-1] if len(moves) > 1 else moves[0]

    gain_med = v("m_gain_median", num(same["gain_pct_of_current_contribution_median"]))
    gain_p10 = v("m_gain_p10", num(same["gain_pct_of_current_contribution_p10"]))
    p_neg = v("m_p_neg", pct(same["probability_gain_negative"]))
    search_over = v("m_search_over", num(search["platform_over_true_pct"], 0))
    total = v("m_weekly_total", f"{same['total_budget']:.0f}")
    extra_cost = v("m_extra_cost", f"{same['total_budget'] - rows['current_spend'].sum():.0f}")

    if same["recommend"]:
        recommendation = (
            f"Make the change. Media contribution is expected to rise by {gain_med} percent, and "
            f"at the 10th percentile the gain is still {gain_p10} percent."
        )
        next_step = "Apply this mix on the demonstration budget until a live euro file exists."
    else:
        recommendation = (
            f"Hold. The median gain is {gain_med} percent of media contribution, but the decision "
            f"rule is not met (10th percentile {gain_p10} percent)."
        )
        next_step = (
            "Keep the current mix on the demonstration budget until a live euro file exists."
        )
    mass = ("The mass of the chart sits above zero." if same["gain_p10"] > 0
            else "Part of the mass sits below zero.")

    evidence = []
    med_exact = exact(same["gain_pct_of_current_contribution_median"])
    p10_exact = exact(same["gain_pct_of_current_contribution_p10"])
    sources = [
        f"- {gain_med} percent — `reports/layer_d/decision.json` (same-budget gain as a "
        f"percent of current contribution, {med_exact}), also `reports/readme_values.json`",
        f"- {gain_p10} percent — `reports/layer_d/decision.json` (10th percentile, "
        f"{p10_exact}), also `reports/readme_values.json`",
    ]
    if down:
        cut = rows.loc[rows["delta_pct"].idxmin()]
        cut_pct = v("m_cut_pct", f"{abs(cut['delta_pct']):.0f}")
        evidence.append(
            f"- {cut['channel']} weekly spend falls {cut_pct} percent in the recommended mix "
            f"(`reports/layer_d/reallocation_table.csv`)."
        )
        sources.append(
            f"- {cut_pct} percent — `reports/layer_d/reallocation_table.csv` ({cut['channel']} "
            f"change {exact(cut['delta_pct'])}), rounded as in `reports/readme_values.json`"
        )
    evidence += [
        f"- The chance the change loses money is {p_neg} percent "
        f"(`reports/layer_d/decision.json`).",
        f"- On a synthetic advertiser with known truth, the platform report credited Paid Search "
        f"with {search_over} percent more revenue than it really added "
        f"(`reports/layer_p/attribution_gap.csv`).",
    ]
    sources += [
        f"- {p_neg} percent — `reports/layer_d/decision.json` (probability the gain is "
        f"negative)",
        f"- {search_over} percent — `reports/layer_p/attribution_gap.csv` (Paid Search "
        f"platform figure over truth, {exact(search['platform_over_true_pct'])})",
        f"- {extra_cost} extra and {total} weekly total — `reports/layer_d/decision.json` "
        f"(recommended total equals current total, {exact(same['total_budget'])})",
    ]

    lines = [
        "# Decision memo",
        "",
        "For the marketing lead. Austrian media mix and budget optimizer (AMBO), demonstration "
        "advertiser.",
        "",
        "## 1. The decision this memo supports",
        "",
        f"Approve a same-budget change to the weekly media mix: {mix}.",
        "",
        "## 2. Recommendation",
        "",
        recommendation,
        "",
        "## 3. Evidence",
        "",
        *evidence,
        "",
        "## 4. Chart",
        "",
        "![Gain from reallocating the same total budget, as a percent of current weekly media "
        "contribution](reports/layer_d/reallocation_gain.png){width=5.4in}",
        "",
        f"Main results chart: `reports/layer_d/reallocation_gain.png`. The dashed line is the "
        f"{gain_med} percent median; the solid line is the {gain_p10} percent tenth percentile. "
        f"{mass}",
        "",
        "## 5. What we do not know",
        "",
        "- The demonstration data is a public simulated dataset in unnamed money units. Shares "
        "and percent gains are usable; the cash amounts are not euros.",
        "- No live advertiser, and no Austrian client file, has been fitted. Competitors may "
        "change spend in response.",
        "- The recommended weeks assume the fitted curves still hold at the new spend levels; "
        "that has not been tested with a lift experiment.",
        "",
        "## 6. Next step and its cost",
        "",
        f"{next_step} Extra media cost is {extra_cost}; the weekly total stays {total} in the "
        f"dataset's units (`reports/layer_d/decision.json`).[^1]",
        "",
        "[^1]: Estimates come from a Bayesian media mix model.",
        "",
        "## Numbers in this memo",
        "",
        *sources,
        "",
    ]
    return "\n".join(lines)


def source_hash(path: Path = MEMO) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_pdf() -> None:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise SystemExit("pandoc not found; install pandoc and a LaTeX engine to build the PDF")
    subprocess.run(
        [pandoc, str(MEMO.relative_to(ROOT)), "-o", str(PDF.relative_to(ROOT)),
         "--resource-path=.", "-V", "geometry:margin=1in"],
        cwd=ROOT, check=True,
    )
    PDF_SOURCE_HASH.write_text(f"{source_hash()}  {MEMO.name}\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", action="store_true", help="also build memo_EN.pdf with pandoc")
    args = parser.parse_args()
    if not (REPORTS / "layer_d" / "decision.json").exists():
        print("Layer D has not run; reports/memo_EN.md is left as it is")
        return 0
    MEMO.write_text(render(), encoding="utf-8")
    with open(REPORTS / "memo_values.json", "w", encoding="utf-8") as fh:
        json.dump(VALUES, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print(f"reports/memo_EN.md written with {len(VALUES)} values")
    if args.pdf:
        build_pdf()
        print("reports/memo_EN.pdf built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
