"""Write notebooks/01_walkthrough.ipynb (unexecuted) and, with --execute, run it.

The notebook reruns Layer P on the tiny config (short window, small sampling
budget) and shows the four Layer P charts with a short interpretation each. Cell
outputs are saved by the execution step so the notebook reads without a kernel.

    uv run python scripts/build_notebook.py --execute
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "notebooks" / "01_walkthrough.ipynb"

CELLS = [
    new_markdown_cell(
        "# Walkthrough: does the model recover a truth it was handed?\n\n"
        "This notebook reruns Layer P, the synthetic advertiser with disclosed truth, on the "
        "tiny profile (a shorter window and a small sampling budget, so it finishes in a few "
        "minutes). The numbers here are for illustration; the reported figures come from "
        "`python -m ambo.run layer_p` on the full profile and live under `reports/layer_p`."
    ),
    new_code_cell(
        "import json\nfrom pathlib import Path\n\nfrom IPython.display import Image, display\n"
        "import pandas as pd\n\nfrom ambo.run import run_layer_p\n\n"
        "OUT = Path('../reports/layer_p_tiny')\nDATA = Path('../data/synthetic_tiny')\n"
        "CONFIG = Path('../src/ambo/configs/tiny.yaml')"
    ),
    new_markdown_cell(
        "## 1. Generate the data, fit, evaluate\n\nOne call regenerates the data, fits the "
        "model twice (full window, then the holdout window), and writes every table and chart."
    ),
    new_code_cell(
        "numbers = run_layer_p(CONFIG, OUT, DATA)\n"
        "print(json.dumps({k: numbers[k] for k in ('weeks', 'parameters_covered', "
        "'parameters_total', 'diagnostics_pass', 'elapsed_seconds')}, indent=2))"
    ),
    new_markdown_cell(
        "## 2. The truth the model never sees\n\nEvery parameter of the data-generating "
        "process is written to `truth.json`. The model gets the weekly spend and revenue only."
    ),
    new_code_cell(
        "truth = json.loads((DATA / 'truth.json').read_text())\n"
        "pd.DataFrame(truth['channel_truth']).T[['decay', 'half_saturation', 'slope', "
        "'effect', 'roas', 'contribution_share_of_revenue']]"
    ),
    new_markdown_cell(
        "## 3. Sampler health\n\nR-hat, effective sample size and divergences are checked "
        "against fixed thresholds on every fit. A failed gate is written down, never hidden."
    ),
    new_code_cell(
        "diag = json.loads((OUT / 'diagnostics.json').read_text())\n"
        "{k: diag[k] for k in ('max_rhat', 'min_ess_bulk', 'min_ess_tail', 'divergences', "
        "'pass_all', 'attempts')}"
    ),
    new_markdown_cell(
        "## 4. Parameter recovery\n\nEach line is a 90 percent posterior interval, the dot "
        "its median, the orange cross the true value. Offline channels with flighted spend "
        "recover tightly; always-on channels with steadier spend carry wider intervals, which "
        "is the honest answer when the data moves little."
    ),
    new_code_cell("display(Image(filename=str(OUT / 'parameter_recovery.png'), width=1000))"),
    new_code_cell(
        "rec = pd.read_csv(OUT / 'parameter_recovery.csv')\n"
        "rec[['family', 'parameter', 'true', 'median', 'lo', 'hi', 'covered']]"
    ),
    new_markdown_cell(
        "## 4b. Response curves against the truth\n\nThe orange line is the true response "
        "curve of the generator, the black line the posterior median and the band its 90 "
        "percent interval. This is the test a budget decision depends on: the curve at "
        "observed spend, not the individual parameters behind it."
    ),
    new_code_cell("display(Image(filename=str(OUT / 'response_curve_recovery.png'), width=1000))"),
    new_code_cell("pd.read_csv(OUT / 'response_curve_metrics.csv')"),
    new_markdown_cell(
        "## 5. Contribution recovery\n\nThe share of revenue each channel drives is what a "
        "marketer acts on. It is recovered more tightly than the individual curve parameters, "
        "because half-saturation, slope and effect size trade off against each other while "
        "their product at observed spend does not."
    ),
    new_code_cell("display(Image(filename=str(OUT / 'contribution_recovery.png'), width=1000))"),
    new_markdown_cell(
        "## 6. Platform claims against incremental truth\n\nThe simulated platform report "
        "credits the online channels with their own effect inflated plus a slice of baseline "
        "demand, and credits offline media with nothing. Search ends up overstated and the "
        "upper funnel understated, which is the pattern practitioners see in last-touch "
        "dashboards."
    ),
    new_code_cell("display(Image(filename=str(OUT / 'attribution_gap.png'), width=1000))"),
    new_code_cell(
        "pd.read_csv(OUT / 'attribution_gap.csv')[['channel', 'platform_share', 'true_share', "
        "'gap_pp', 'estimated_share_median']]"
    ),
    new_markdown_cell(
        "## 7. Holdout forecast\n\nThe model is refit on the first part of the window and "
        "forecasts the rest with the actual spend. Two baselines set the bar: last year's "
        "revenue for the same week, and a ridge regression on raw spend with month dummies. "
        "The MMM is not always the most accurate point forecaster; its value is calibrated "
        "uncertainty and a decomposition the baselines cannot give."
    ),
    new_code_cell("display(Image(filename=str(OUT / 'holdout.png'), width=1000))"),
    new_code_cell("pd.read_csv(OUT / 'holdout_metrics.csv')"),
    new_markdown_cell(
        "## What to take away\n\nA model that cannot recover parameters it was handed cannot "
        "be trusted on real data. This one recovers the observable quantities (contribution "
        "shares, ROAS, the direction of the attribution gap) on the default seed; the full "
        "profile results in `reports/layer_p` are the ones cited in the README."
    ),
]


def build() -> None:
    nb = new_notebook(cells=CELLS)
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata["language_info"] = {"name": "python"}
    PATH.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, PATH)
    print(f"wrote {PATH} with {len(CELLS)} cells")


def execute(timeout: int) -> None:
    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
        "--inplace", f"--ExecutePreprocessor.timeout={timeout}", str(PATH),
    ]
    subprocess.run(cmd, check=True, cwd=PATH.parent)
    nb = nbformat.read(PATH, as_version=4)
    outputs = sum(len(c.get("outputs", [])) for c in nb.cells if c.cell_type == "code")
    print(f"executed {PATH}: {outputs} outputs saved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    build()
    if args.execute:
        execute(args.timeout)
