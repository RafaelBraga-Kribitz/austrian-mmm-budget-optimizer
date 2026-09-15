"""Chart theme: the Braga-Kribitz design system through bk-viz, with a fallback.

Rules the charts follow: ink on a light grey surface, one orange accent used for
exactly one element per chart, 1px mid-grey hairlines instead of gridlines,
monospace tick and data labels in mid grey, no chart title that repeats the caption,
business labels only. Every PNG is 1600 px wide and well under 1 MB.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

try:
    import bk_theme as _bk

    HAVE_BK = True
except ImportError:  # pragma: no cover - exercised only without the package
    _bk = None
    HAVE_BK = False

TOKENS = {
    "surface": "#E6E6E6",
    "surface-2": "#DEDEDE",
    "surface-3": "#D6D6D6",
    "ink": "#282828",
    "ink-2": "#646464",
    "mid": "#A0A0A0",
    "accent": "#FA6400",
}
HAIRLINE_PT = 72.0 / 96.0
WIDTH_PX = 1600
DPI = 100

_applied = False


def apply() -> None:
    """Install the theme once per process."""
    global _applied
    if _applied:
        return
    if HAVE_BK:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _bk.apply("light", grid="none")
    else:
        plt.rcParams.update(
            {
                "font.family": "monospace",
                "font.size": 10,
                "figure.facecolor": TOKENS["surface"],
                "axes.facecolor": TOKENS["surface"],
                "savefig.facecolor": TOKENS["surface"],
                "text.color": TOKENS["ink"],
                "axes.labelcolor": TOKENS["mid"],
                "xtick.color": TOKENS["mid"],
                "ytick.color": TOKENS["mid"],
                "xtick.labelcolor": TOKENS["ink-2"],
                "ytick.labelcolor": TOKENS["ink-2"],
                "axes.edgecolor": TOKENS["mid"],
                "axes.linewidth": HAIRLINE_PT,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.grid": False,
                "xtick.major.size": 0,
                "ytick.major.size": 0,
                "legend.frameon": False,
                "lines.linewidth": 1.75,
            }
        )
    plt.rcParams.update({"figure.dpi": DPI, "savefig.dpi": DPI})
    _applied = True


def color(role: str) -> str:
    """Design token by role: surface, ink, ink-2, mid, accent."""
    if HAVE_BK and role != "accent":
        return _bk.c(role)
    if HAVE_BK and role == "accent":
        return _bk.c("accent-01")
    return TOKENS[role]


def new_figure(height_px: int = 900, nrows: int = 1, ncols: int = 1, **kwargs):
    apply()
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(WIDTH_PX / DPI, height_px / DPI), dpi=DPI, **kwargs
    )
    return fig, axes


def hairlines(ax, keep=("left", "bottom")) -> None:
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(side in keep)
        ax.spines[side].set_color(color("mid"))
        ax.spines[side].set_linewidth(HAIRLINE_PT)
    ax.tick_params(length=0, colors=color("mid"), labelcolor=color("ink-2"))


def guide(ax, value: float, orient: str = "v", label: str | None = None) -> None:
    """A dashed hairline reference (zero line, breakeven, current spend)."""
    kw = dict(color=color("mid"), lw=HAIRLINE_PT, ls=(0, (3, 3)), zorder=1)
    if orient == "v":
        ax.axvline(value, **kw)
        if label:
            ax.annotate(
                label,
                xy=(value, 1.0),
                xycoords=("data", "axes fraction"),
                xytext=(4, -2),
                textcoords="offset points",
                ha="left",
                va="top",
                color=color("mid"),
                fontsize=8,
            )
    else:
        ax.axhline(value, **kw)
        if label:
            ax.annotate(
                label,
                xy=(1.0, value),
                xycoords=("axes fraction", "data"),
                xytext=(-4, 3),
                textcoords="offset points",
                ha="right",
                va="bottom",
                color=color("mid"),
                fontsize=8,
            )


def footer(fig: Figure, source: str, note: str | None = None) -> None:
    """Provenance strip at the bottom: source line in mid grey, optional note."""
    fig.text(0.04, 0.02, f"SOURCE  {source}".upper(), ha="left", va="bottom",
             color=color("mid"), fontsize=8, family="monospace")
    if note:
        fig.text(0.04, 0.05, note, ha="left", va="bottom", color=color("ink-2"), fontsize=9)


def save(fig: Figure, path: Path) -> Path:
    """Write a PNG at 1600 px width and check it stays under 1 MB."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor=color("surface"))
    plt.close(fig)
    size = path.stat().st_size
    if size > 1_000_000:
        raise RuntimeError(f"{path} is {size / 1e6:.2f} MB, above the 1 MB limit")
    return path
