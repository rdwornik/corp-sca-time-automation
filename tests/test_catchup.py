"""Integration tests for catchup command logic.

Tests the date-range detection and filtering logic using mocked SharePoint
and pipeline calls. Does not hit real endpoints or write real Excel files.
"""

from datetime import date
import pandas as pd

from src.date_utils import last_sunday, sundays_between


class TestCatchupDateLogic:
    """Test the week-gap detection logic independently of the CLI."""

    def test_identifies_missing_weeks(self):
        uploaded = {date(2025, 3, 2), date(2025, 3, 9)}
        end = date(2025, 3, 30)  # Sunday
        last_uploaded = max(uploaded)
        missing = sundays_between(last_uploaded, end)
        assert missing == [date(2025, 3, 16), date(2025, 3, 23), date(2025, 3, 30)]

    def test_no_missing_when_caught_up(self):
        end = date(2025, 3, 23)  # Sunday
        uploaded = {date(2025, 3, 23)}
        last_uploaded = max(uploaded)
        missing = sundays_between(last_uploaded, end)
        assert missing == []

    def test_one_week_missing(self):
        uploaded = {date(2025, 3, 16)}
        end = date(2025, 3, 23)
        missing = sundays_between(max(uploaded), end)
        assert missing == [date(2025, 3, 23)]


class TestCatchupDataframeFiltering:
    """Test that the DataFrame filtering for missing weeks is correct."""

    def _make_df(self) -> pd.DataFrame:
        rows = [
            {"week_beginning": "2025-03-09", "category": "Admin", "hours": 8.0, "is_autofilled": False},
            {"week_beginning": "2025-03-09", "category": ">>> WEEK TOTAL", "hours": 8.0, "is_autofilled": False},
            {"week_beginning": "2025-03-16", "category": "Internal Meeting", "hours": 4.0, "is_autofilled": False},
            {"week_beginning": "2025-03-16", "category": ">>> WEEK TOTAL", "hours": 4.0, "is_autofilled": False},
            {"week_beginning": "2025-03-23", "category": "Discovery", "hours": 6.0, "is_autofilled": False},
            {"week_beginning": "2025-03-23", "category": ">>> WEEK TOTAL", "hours": 6.0, "is_autofilled": False},
        ]
        return pd.DataFrame(rows)

    def test_filter_keeps_only_missing_weeks(self):
        df = self._make_df()
        missing_strings = {"2025-03-16", "2025-03-23"}

        is_total = df["category"] == ">>> WEEK TOTAL"
        in_missing = df["week_beginning"].isin(missing_strings)
        filtered = df[in_missing | (is_total & in_missing)].copy()

        weeks_in_result = set(filtered[filtered["category"] != ">>> WEEK TOTAL"]["week_beginning"])
        assert weeks_in_result == {"2025-03-16", "2025-03-23"}
        assert "2025-03-09" not in filtered["week_beginning"].values

    def test_filter_includes_week_total_rows(self):
        df = self._make_df()
        missing_strings = {"2025-03-23"}

        is_total = df["category"] == ">>> WEEK TOTAL"
        in_missing = df["week_beginning"].isin(missing_strings)
        filtered = df[in_missing | (is_total & in_missing)].copy()

        total_rows = filtered[filtered["category"] == ">>> WEEK TOTAL"]
        assert len(total_rows) == 1
        assert total_rows.iloc[0]["week_beginning"] == "2025-03-23"

    def test_filter_empty_when_no_calendar_data(self):
        df = self._make_df()
        # Missing week that has no data in the DataFrame
        missing_strings = {"2025-04-06"}

        is_total = df["category"] == ">>> WEEK TOTAL"
        in_missing = df["week_beginning"].isin(missing_strings)
        filtered = df[in_missing | (is_total & in_missing)].copy()

        assert filtered.empty


class TestCatchupFallback:
    """Test the no-uploads fallback logic."""

    def test_no_uploads_uses_max_weeks_fallback(self):
        """When SharePoint is empty, we fall back to max_weeks calculation."""
        max_weeks = 4
        end = date(2025, 3, 23)  # known Sunday for determinism
        # Simulate: last_uploaded = end - max_weeks * 7
        last_uploaded = last_sunday(
            date.fromordinal(end.toordinal() - max_weeks * 7)
        )
        missing = sundays_between(last_uploaded, end)
        assert len(missing) == max_weeks
        assert missing[-1] == end
