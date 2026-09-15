"""The report charts. Each function takes a table produced by ``ambo.evaluate`` or
``ambo.optimize`` and writes one PNG. No chart carries a title that repeats the
caption; the panel headings say what the axis shows."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ambo.plots import theme

DOT = 6.0


def _dot_interval(ax, y, med, lo, hi, true=None, label_fmt="{:.2f}"):
    ink, mid, accent = theme.color("ink"), theme.color("mid"), theme.color("accent")
    ax.hlines(y, lo, hi, color=ink, lw=theme.HAIRLINE_PT * 1.5, zorder=2)
    ax.plot(med, y, "o", color=ink, ms=DOT, zorder=3)
    if true is not None:
        ax.plot(true, y, "x", color=accent, ms=9, mew=2.0, zorder=4)
    for yi, hi_i, m_i in zip(y, hi, med, strict=True):
        ax.annotate(label_fmt.format(m_i), xy=(hi_i, yi), xytext=(6, 0),
                    textcoords="offset points", va="center", ha="left",
                    color=mid, fontsize=8, family="monospace")


def _panel_setup(ax, heading: str, labels, xlabel: str):
    theme.hairlines(ax)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, color=theme.color("mid"))
    ax.set_title(heading, loc="left", color=theme.color("ink"), fontsize=11, pad=10)
    ax.margins(x=0.25)


def parameter_recovery(table: pd.DataFrame, path: Path, source: str) -> Path:
    """Three panels: adstock decay, saturation, coefficients. True value as orange cross."""
    fig, axes = theme.new_figure(
        height_px=900, ncols=3, gridspec_kw={"width_ratios": [1, 1.25, 1.4]}
    )
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.16, wspace=0.95)
    families = [
        ("Adstock decay", "Adstock decay\nshare of the effect carried\ninto next week",
         "decay", 1.0, "{:.2f}"),
        ("Saturation",
         "Saturation\nhalf-saturation as a multiple of\naverage weekly spend, and slope",
         "value", 1.0, "{:.2f}"),
        ("Coefficients", "Effect at saturation and baseline\nEUR thousand per week",
         "eur_k", 1000.0, "{:.1f}"),
    ]
    for ax, (family, heading, _kind, scale, fmt) in zip(axes, families, strict=True):
        sub = table[table["family"] == family].reset_index(drop=True)
        y = np.arange(len(sub))
        _dot_interval(ax, y, sub["median"] / scale, sub["lo"] / scale, sub["hi"] / scale,
                      sub["true"] / scale, fmt)
        _panel_setup(ax, heading, sub["parameter"].tolist(), "")
        if family == "Coefficients":
            theme.guide(ax, 0.0, "v")
    covered = int(table["covered"].sum())
    theme.footer(
        fig, source,
        note=f"Line: 90% posterior interval. Dot: posterior median. Orange cross: true value. "
             f"{covered} of {len(table)} true values fall inside their interval.",
    )
    return theme.save(fig, path)


def contribution_recovery(table: pd.DataFrame, path: Path, source: str) -> Path:
    fig, ax = theme.new_figure(height_px=700)
    fig.subplots_adjust(left=0.16, right=0.92, top=0.88, bottom=0.20)
    y = np.arange(len(table))
    _dot_interval(ax, y, 100 * table["share_median"], 100 * table["share_lo"],
                  100 * table["share_hi"], 100 * table["true_share_of_revenue"], "{:.1f}%")
    _panel_setup(ax, "Share of total revenue driven by each channel, percent",
                 table["channel"].tolist(), "")
    theme.guide(ax, 0.0, "v")
    covered = int(table["covered"].sum())
    theme.footer(
        fig, source,
        note=f"Line: 90% posterior interval. Dot: posterior median. Orange cross: true share. "
             f"{covered} of {len(table)} channels covered.",
    )
    return theme.save(fig, path)


def attribution_gap(table: pd.DataFrame, path: Path, source: str) -> Path:
    """Dumbbell: platform-reported share versus true incremental share per channel."""
    fig, ax = theme.new_figure(height_px=700)
    fig.subplots_adjust(left=0.16, right=0.92, top=0.88, bottom=0.22)
    ink, mid, accent = theme.color("ink"), theme.color("mid"), theme.color("accent")
    worst = int(table["abs_gap_pp"].idxmax())
    for i, row in table.iterrows():
        col = accent if i == worst else mid
        ax.plot([100 * row["true_share"], 100 * row["platform_share"]], [i, i],
                color=col, lw=2.5 if i == worst else 1.5, zorder=2, solid_capstyle="butt")
        ax.plot(100 * row["true_share"], i, "o", color=ink, ms=DOT + 1, zorder=3)
        ax.plot(100 * row["platform_share"], i, "o", mfc=theme.color("surface"), mec=ink,
                mew=1.5, ms=DOT + 1, zorder=3)
        right = max(row["true_share"], row["platform_share"]) * 100
        ax.annotate(f"{row['gap_pp']:+.1f} pp", xy=(right, i), xytext=(8, 0),
                    textcoords="offset points", va="center", ha="left",
                    color=accent if i == worst else mid, fontsize=9, family="monospace")
    _panel_setup(ax, "Share of attributed revenue, percent: filled dot = true incremental, "
                     "hollow dot = platform-reported", table["channel"].tolist(), "")
    theme.footer(
        fig, source,
        note="Gap in percentage points, platform minus truth. Offline channels receive no "
             "platform credit at all. Orange marks the largest gap.",
    )
    return theme.save(fig, path)


def holdout(preds: pd.DataFrame, metrics: pd.DataFrame, path: Path, source: str,
            money_unit: str = "EUR thousand") -> Path:
    """Test window: actual revenue, the MMM forecast with its 90% band, and both baselines."""
    fig, ax = theme.new_figure(height_px=800)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.20)
    ink, mid, accent = theme.color("ink"), theme.color("mid"), theme.color("accent")
    x = preds["week"].to_numpy()
    scale = 1000.0 if money_unit == "EUR thousand" else 1.0
    ax.fill_between(x, preds["bayesian_mmm_lo"] / scale, preds["bayesian_mmm_hi"] / scale,
                    color=theme.color("surface-3"), lw=0, zorder=1)
    ax.plot(x, preds["seasonal_naive_yhat"] / scale, color=mid, ls=(0, (3, 3)), lw=1.5, zorder=2)
    ax.plot(x, preds["ridge_regression_yhat"] / scale, color=mid, ls=(0, (1, 2)), lw=1.5, zorder=2)
    ax.plot(x, preds["bayesian_mmm_yhat"] / scale, color=accent, lw=2.0, zorder=3)
    ax.plot(x, preds["actual"] / scale, color=ink, lw=1.75, zorder=4)
    theme.hairlines(ax)
    ax.set_title("Holdout weeks: actual revenue (black), MMM forecast (orange) with 90% band, "
                 f"seasonal naive (dashed), ridge (dotted). {money_unit} per week",
                 loc="left", color=ink, fontsize=11, pad=10)
    ax.set_xlabel("Week", color=mid)
    lines = []
    for _, r in metrics.iterrows():
        lines.append(
            f"{r['model']}: MAPE {100 * r['mape']:.1f}%, coverage {100 * r['coverage_90']:.0f}%"
        )
    theme.footer(fig, source, note="   |   ".join(lines))
    return theme.save(fig, path)


def channel_contributions(
    table: pd.DataFrame, weekly: pd.DataFrame, channels: list[str], path: Path, source: str
) -> Path:
    """Left: share of revenue per channel with 90% intervals. Right: weekly contributions."""
    fig, (ax_left, ax_right) = theme.new_figure(
        height_px=800, ncols=2, gridspec_kw={"width_ratios": [1, 1.6]}
    )
    fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.20, wspace=0.45)
    ink, mid, accent = theme.color("ink"), theme.color("mid"), theme.color("accent")
    y = np.arange(len(table))
    _dot_interval(ax_left, y, 100 * table["share_median"], 100 * table["share_lo"],
                  100 * table["share_hi"], None, "{:.1f}%")
    best = int(table["share_median"].idxmax())
    ax_left.plot(100 * table.loc[best, "share_median"], best, "o", color=accent, ms=DOT + 1,
                 zorder=5)
    _panel_setup(ax_left, "Share of revenue driven by each channel, percent",
                 table["channel"].tolist(), "")
    theme.guide(ax_left, 0.0, "v")
    x = weekly["week"].to_numpy()
    styles = [(ink, "-"), (mid, (0, (3, 3))), (ink, (0, (1, 2))), (mid, "-"), (ink, (0, (5, 2)))]
    for i, ch in enumerate(channels):
        col, ls = styles[i % len(styles)]
        ax_right.fill_between(x, weekly[f"{ch} lo"], weekly[f"{ch} hi"],
                              color=theme.color("surface-3"), lw=0, zorder=1)
        ax_right.plot(x, weekly[f"{ch} median"], color=col, ls=ls, lw=1.6, zorder=3, label=ch)
    ax_right.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=ink)
    theme.hairlines(ax_right)
    ax_right.set_title("Weekly incremental contribution per channel, median line and 90% band",
                       loc="left", color=ink, fontsize=11, pad=10)
    ax_right.set_xlabel("Week", color=mid)
    ax_right.margins(x=0.03)
    theme.footer(
        fig, source,
        note="Left: line = 90% posterior interval, dot = median; orange marks the largest share. "
             "Right: contribution in the data's revenue units.",
    )
    return theme.save(fig, path)


def response_curves(curves: pd.DataFrame, path: Path, source: str) -> Path:
    """Spend versus incremental weekly revenue per channel, with 90% band and current spend."""
    channels = list(dict.fromkeys(curves["channel"]))
    fig, axes = theme.new_figure(height_px=700, ncols=len(channels), sharey=False)
    if len(channels) == 1:
        axes = [axes]
    fig.subplots_adjust(left=0.08, right=0.97, top=0.86, bottom=0.22, wspace=0.35)
    ink, mid, accent = theme.color("ink"), theme.color("mid"), theme.color("accent")
    for ax, ch in zip(axes, channels, strict=True):
        sub = curves[curves["channel"] == ch]
        ax.fill_between(sub["spend"], sub["lo"], sub["hi"], color=theme.color("surface-3"),
                        lw=0, zorder=1)
        ax.plot(sub["spend"], sub["median"], color=ink, lw=1.8, zorder=3)
        current = float(sub["current_spend"].iloc[0])
        ax.axvline(current, color=accent, lw=1.5, zorder=2)
        ax.annotate("current average\nweekly spend", xy=(current, 1.0),
                    xycoords=("data", "axes fraction"), xytext=(5, -4),
                    textcoords="offset points", ha="left", va="top", color=accent, fontsize=8)
        theme.hairlines(ax)
        ax.set_title(ch, loc="left", color=ink, fontsize=11, pad=10)
        ax.set_xlabel("Weekly spend held constant", color=mid)
        ax.set_ylabel("Incremental revenue per week", color=mid)
        ax.margins(x=0.02)
    theme.footer(
        fig, source,
        note="Line: posterior median response at a constant weekly spend. Band: 90% interval. "
             "Curves stop at 1.5 times the largest observed weekly spend.",
    )
    return theme.save(fig, path)


def reallocation_gain(gain: np.ndarray, contribution_current: np.ndarray, path: Path,
                      source: str) -> Path:
    """Distribution of the weekly gain from reallocation, 10th percentile marked."""
    fig, ax = theme.new_figure(height_px=700)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.86, bottom=0.22)
    ink, mid, accent = theme.color("ink"), theme.color("mid"), theme.color("accent")
    rel = 100.0 * gain / contribution_current
    p10, p50 = np.percentile(rel, 10), np.median(rel)
    ax.hist(rel, bins=40, color=theme.color("surface-3"), edgecolor=ink, linewidth=0.4, zorder=2)
    theme.guide(ax, 0.0, "v")
    ax.axvline(p10, color=accent, lw=2.0, zorder=3)
    ax.annotate(f"10th percentile {p10:+.1f}%", xy=(p10, 1.0), xycoords=("data", "axes fraction"),
                xytext=(6, -4), textcoords="offset points", ha="left", va="top", color=accent,
                fontsize=9, family="monospace")
    ax.axvline(p50, color=ink, lw=1.2, ls=(0, (3, 3)), zorder=3)
    ax.annotate(f"median {p50:+.1f}%", xy=(p50, 0.88), xycoords=("data", "axes fraction"),
                xytext=(6, 0), textcoords="offset points", ha="left", va="top", color=ink,
                fontsize=9, family="monospace")
    theme.hairlines(ax)
    ax.set_title("Gain from reallocating the same total budget, percent of current weekly "
                 "media contribution, one bar per posterior draw",
                 loc="left", color=ink, fontsize=11, pad=10)
    ax.set_xlabel("Gain, percent", color=mid)
    ax.set_ylabel("Posterior draws", color=mid)
    theme.footer(
        fig, source,
        note=f"Probability the reallocation loses money: {100 * np.mean(gain < 0):.1f}%. "
             "Constant-spend steady state; channels bounded to plus or minus 50% of current spend.",
    )
    return theme.save(fig, path)
