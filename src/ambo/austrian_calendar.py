"""Austrian public holidays as a weekly indicator.

The thirteen nationwide public holidays (gesetzliche Feiertage) are computed
directly: nine fixed dates and four that move with Easter. No external calendar
package is needed, and the result is deterministic.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

FIXED_HOLIDAYS = (
    (1, 1),  # Neujahr
    (1, 6),  # Heilige Drei Koenige
    (5, 1),  # Staatsfeiertag
    (8, 15),  # Mariae Himmelfahrt
    (10, 26),  # Nationalfeiertag
    (11, 1),  # Allerheiligen
    (12, 8),  # Mariae Empfaengnis
    (12, 25),  # Christtag
    (12, 26),  # Stefanitag
)

EASTER_OFFSETS = (1, 39, 50, 60)  # Ostermontag, Christi Himmelfahrt, Pfingstmontag, Fronleichnam


def easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (anonymous algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def austrian_public_holidays(year: int) -> list[date]:
    """All nationwide Austrian public holidays of ``year``, sorted."""
    days = [date(year, month, day) for month, day in FIXED_HOLIDAYS]
    easter = easter_sunday(year)
    days.extend(easter + timedelta(days=offset) for offset in EASTER_OFFSETS)
    return sorted(days)


def holiday_flag(week_starts: pd.Series | list[date]) -> np.ndarray:
    """1 when the Monday-to-Sunday week starting on each date contains a public holiday."""
    starts = pd.to_datetime(pd.Series(list(week_starts))).dt.date.tolist()
    years = sorted({d.year for d in starts} | {d.year + 1 for d in starts})
    holidays = set()
    for year in years:
        holidays.update(austrian_public_holidays(year))
    flags = np.zeros(len(starts), dtype=float)
    for idx, start in enumerate(starts):
        week = {start + timedelta(days=offset) for offset in range(7)}
        flags[idx] = 1.0 if week & holidays else 0.0
    return flags
