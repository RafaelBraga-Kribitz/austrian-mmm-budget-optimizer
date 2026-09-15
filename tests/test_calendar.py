"""Austrian public holiday calendar."""

from datetime import date

import numpy as np

from ambo.austrian_calendar import austrian_public_holidays, easter_sunday, holiday_flag


def test_easter_known_dates():
    assert easter_sunday(2023) == date(2023, 4, 9)
    assert easter_sunday(2024) == date(2024, 3, 31)
    assert easter_sunday(2025) == date(2025, 4, 20)


def test_thirteen_holidays_per_year_and_moving_feasts():
    days = austrian_public_holidays(2024)
    assert len(days) == 13
    assert date(2024, 4, 1) in days  # Ostermontag
    assert date(2024, 5, 9) in days  # Christi Himmelfahrt
    assert date(2024, 5, 20) in days  # Pfingstmontag
    assert date(2024, 5, 30) in days  # Fronleichnam
    assert date(2024, 10, 26) in days  # Nationalfeiertag


def test_weekly_flag_marks_weeks_containing_a_holiday():
    # Mondays: 2024-04-29 (week with 1 May), 2024-05-06 (Christi Himmelfahrt on 9 May),
    # 2024-06-10 (no holiday).
    flags = holiday_flag([date(2024, 4, 29), date(2024, 5, 6), date(2024, 6, 10)])
    np.testing.assert_array_equal(flags, np.array([1.0, 1.0, 0.0]))
