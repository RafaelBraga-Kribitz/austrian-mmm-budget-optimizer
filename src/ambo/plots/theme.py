"""Chart theme: wrap bk-viz when present, else the same tokens locally.

Implements: STATUS D-07. Fallback exists so the pipeline still runs if the
GitHub package is unavailable; colours match ``bk_theme.RAW`` / ``COLOR['light']``.
"""

from __future__ import annotations

from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt

# Verbatim from bk_theme.RAW / COLOR['light'] (D-07).
RAW = {
    "off-white": "#E6E6E6",
    "paper": "#DEDEDE",
    "light": "#D6D6D6",
    "mid": "#A0A0A0",
    "dark-grey": "#646464",
    "off-black": "#282828",
    "orange": "#FA6400",
    "blue": "#5B7FFF",
}

TOKENS = {
    "surface": RAW["off-white"],
    "surface-2": RAW["paper"],
    "ink": RAW["off-black"],
    "ink-2": RAW["dark-grey"],
    "mid": RAW["mid"],
    "accent-01": RAW["orange"],
    "accent-02": RAW["blue"],
}

CHANNEL_PALETTE = (
    RAW["off-black"],
    RAW["dark-grey"],
    RAW["blue"],
    RAW["orange"],
    "#4A4A4A",
)

_BK: Any = None
try:
    import bk_theme as _BK
except ImportError:
    _BK = None


def tokens() -> dict[str, str]:
    return dict(TOKENS)


def channel_colors(n: int) -> list[str]:
    if n < 1:
        return []
    if _BK is not None and hasattr(_BK, "palette"):
        try:
            return list(_BK.palette(n))
        except Exception:
            pass
    return [CHANNEL_PALETTE[i % len(CHANNEL_PALETTE)] for i in range(n)]


def apply_theme() -> None:
    """Apply the design-system rcParams. Safe to call more than once."""
    mpl.use("Agg", force=False)
    if _BK is not None:
        _BK.apply(mode="light")
        return
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["surface"],
            "axes.edgecolor": TOKENS["mid"],
            "axes.labelcolor": TOKENS["ink"],
            "text.color": TOKENS["ink"],
            "xtick.color": TOKENS["ink-2"],
            "ytick.color": TOKENS["ink-2"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "font.size": 11,
            "axes.titlesize": 13,
            "figure.dpi": 120,
        }
    )
