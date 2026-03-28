"""Tests for src/date_utils.py — pure Sunday-based week math."""

import pytest
from datetime import date

from src.date_utils import last_sunday, sundays_between, weeks_back_to_cover


class TestLastSunday:
    def test_sunday_returns_same_day(self):
        d = date(2025, 3, 23)  # Sunday
        assert d.weekday() == 6
        assert last_sunday(d) == d

    def test_monday_returns_previous_sunday(self):
        d = date(2025, 3, 24)  # Monday
        assert last_sunday(d) == date(2025, 3, 23)

    def test_saturday_returns_six_days_back(self):
        d = date(2025, 3, 29)  # Saturday
        assert last_sunday(d) == date(2025, 3, 23)

    def test_wednesday_midweek(self):
        d = date(2025, 3, 26)  # Wednesday
        assert last_sunday(d) == date(2025, 3, 23)

    def test_default_returns_a_sunday(self):
        result = last_sunday()
        assert result.weekday() == 6


class TestSundaysBetween:
    def test_adjacent_sundays_returns_end(self):
        start = date(2025, 3, 16)
        end = date(2025, 3, 23)
        assert sundays_between(start, end) == [date(2025, 3, 23)]

    def test_same_date_returns_empty(self):
        d = date(2025, 3, 23)
        assert sundays_between(d, d) == []

    def test_start_after_end_returns_empty(self):
        assert sundays_between(date(2025, 3, 23), date(2025, 3, 16)) == []

    def test_seven_week_range(self):
        start = date(2025, 2, 2)   # Sunday
        end = date(2025, 3, 23)    # Sunday
        result = sundays_between(start, end)
        assert len(result) == 7
        assert result[0] == date(2025, 2, 9)
        assert result[-1] == date(2025, 3, 23)
        for d in result:
            assert d.weekday() == 6

    def test_raises_on_non_sunday_start(self):
        with pytest.raises(ValueError, match="start must be a Sunday"):
            sundays_between(date(2025, 3, 24), date(2025, 3, 30))  # Monday start

    def test_raises_on_non_sunday_end(self):
        with pytest.raises(ValueError, match="end must be a Sunday"):
            sundays_between(date(2025, 3, 23), date(2025, 3, 28))  # Friday end


class TestWeeksBackToCover:
    def test_same_week_returns_positive(self):
        ref = date(2025, 3, 28)  # Friday
        target = last_sunday(ref)  # Sunday March 23
        result = weeks_back_to_cover(target, ref=ref)
        assert result >= 1

    def test_four_weeks_back(self):
        ref = date(2025, 3, 28)
        target = date(2025, 3, 2)   # ~4 weeks back Sunday
        result = weeks_back_to_cover(target, ref=ref)
        assert result >= 4

    def test_twelve_weeks_back(self):
        ref = date(2025, 3, 28)
        target = date(2025, 1, 5)  # ~12 weeks back Sunday
        result = weeks_back_to_cover(target, ref=ref)
        assert result >= 12

    def test_future_target_returns_one(self):
        ref = date(2025, 3, 28)
        target = date(2025, 4, 6)  # future Sunday
        result = weeks_back_to_cover(target, ref=ref)
        assert result >= 1
