"""Chart theme: the Braga design system v2.1 through bk-viz.

Rules the charts follow (DECISIONS.md D-053, D-036): flat ``surface`` ground, one
highlight (``hl``, the ultramarine accent) per chart, structure in ink and greys,
1px ``mid`` hairlines for axes, BKribitz for headings and BKribitz Mono for every
number, label and tick. Colour lives in marks, never in type: every label is ``ink``
or ``ink-2``, and ``mid`` is never text. No text below 12px. Every figure carries a
provenance strip. Colours come only from bk-viz roles; this module holds no hex value.
Every PNG is 1600 px wide and well under 1 MB.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import bk_theme as bk  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

HAIRLINE_PT = bk.HAIRLINE_PT
WIDTH_PX = 1600
DPI = 100

# The one epistemic tag every figure in this repository carries: Layer P is synthetic
# with a disclosed truth, Layer R is Robyn's simulated dataset, Layer D is derived from it.
TAG = "SIMULATED"

# Roles the charts ask for. "accent" is the one highlight per chart.
_ROLE = {"accent": "hl"}

_applied = False


def apply() -> None:
    """Install the theme once per process."""
    global _applied
    if _applied:
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bk.apply("light", grid="none")
    plt.rcParams.update({"figure.dpi": DPI, "savefig.dpi": DPI})
    _applied = True


def color(role: str) -> str:
    """Design-system colour by role: surface, surface-3, ink, ink-2, mid, accent (= hl)."""
    apply()
    return bk.c(_ROLE.get(role, role))


def font(role: str = "mono", weight: int | str = "regular", size: str = "mono"):
    """BKribitz (``display``) or BKribitz Mono (``mono``) at a design-system size."""
    apply()
    return bk.font(role, weight, size)


def new_figure(height_px: int = 900, nrows: int = 1, ncols: int = 1, **kwargs):
    apply()
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(WIDTH_PX / DPI, height_px / DPI), dpi=DPI, **kwargs
    )
    return fig, axes


def hairlines(ax, keep=("left", "bottom")) -> None:
    """Axes as 1px ``mid`` hairlines, no tick marks, mono tick labels in ``ink-2``."""
    bk.strip_chrome(ax, keep=keep)
    ax.tick_params(length=0, colors=color("mid"), labelcolor=color("ink-2"))


def heading(ax, text: str, pad: float = 10) -> None:
    """Panel heading in BKribitz 700, ink."""
    ax.set_title(text, loc="left", color=color("ink"), pad=pad,
                 fontproperties=font("display", "bold", "body"))


def axis_label(ax, x: str | None = None, y: str | None = None) -> None:
    """Axis titles in ``ink-2`` mono."""
    if x is not None:
        ax.set_xlabel(x, color=color("ink-2"), fontproperties=font())
    if y is not None:
        ax.set_ylabel(y, color=color("ink-2"), fontproperties=font())


def guide(ax, value: float, orient: str = "v", label: str | None = None) -> None:
    """A dashed hairline reference (zero line, breakeven, current spend); label in ink-2."""
    kw = dict(color=color("mid"), lw=HAIRLINE_PT, ls=(0, (3, 3)), zorder=1)
    fp = font("mono", "regular", "mono-sm")
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
                color=color("ink-2"),
                fontproperties=fp,
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
                color=color("ink-2"),
                fontproperties=fp,
            )


def footer(fig: Figure, source: str, note: str | None = None) -> None:
    """Provenance strip at the bottom: opening ink rule, source line, epistemic tag, note."""
    bk.footer(fig, source=source, tag=TAG, note=note, left=0.04, right=0.03, y=0.075)


def save(fig: Figure, path: Path) -> Path:
    """Write a PNG at 1600 px width and check it stays under 1 MB."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bk.check_glyphs(fig)
    fig.savefig(path, dpi=DPI, facecolor=color("surface"))
    plt.close(fig)
    size = path.stat().st_size
    if size > 1_000_000:
        raise RuntimeError(f"{path} is {size / 1e6:.2f} MB, above the 1 MB limit")
    return path
