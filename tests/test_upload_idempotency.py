"""Tests for upload idempotency guard in post_week_entries."""

import pandas as pd
from unittest.mock import patch
from datetime import date

from src.sharepoint import post_week_entries, post_all_weeks


def _make_df() -> pd.DataFrame:
    rows = [
        {"week_beginning": "2025-03-23", "category": "Admin", "hours": 8.0},
        {"week_beginning": "2025-03-23", "category": "Internal Meeting", "hours": 4.0},
        {"week_beginning": "2025-03-23", "category": ">>> WEEK TOTAL", "hours": 12.0},
        {"week_beginning": "2025-03-30", "category": "Discovery", "hours": 6.0},
        {"week_beginning": "2025-03-30", "category": ">>> WEEK TOTAL", "hours": 6.0},
    ]
    return pd.DataFrame(rows)


class TestPostWeekEntriesIdempotency:
    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.is_week_uploaded", return_value=True)
    def test_skips_already_uploaded_week(self, mock_is_uploaded, mock_token):
        df = _make_df()
        results = post_week_entries(df, "2025-03-23")
        assert results == []
        mock_is_uploaded.assert_called_once_with(date(2025, 3, 23), "fake-token")

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.post_time_entry", return_value={"success": True})
    @patch("src.sharepoint.is_week_uploaded", return_value=True)
    def test_force_uploads_even_if_already_exists(self, mock_is_uploaded, mock_post, mock_token):
        df = _make_df()
        results = post_week_entries(df, "2025-03-23", force=True)
        # Should have uploaded 2 entries (excluding WEEK TOTAL)
        assert len(results) == 2
        assert all(r["success"] for r in results)
        mock_is_uploaded.assert_not_called()

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.post_time_entry", return_value={"success": True})
    @patch("src.sharepoint.is_week_uploaded", return_value=False)
    def test_uploads_when_not_yet_uploaded(self, mock_is_uploaded, mock_post, mock_token):
        df = _make_df()
        results = post_week_entries(df, "2025-03-23")
        assert len(results) == 2
        assert all(r["success"] for r in results)


class TestPostAllWeeksIdempotency:
    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.is_week_uploaded", return_value=True)
    def test_skips_all_weeks_when_all_uploaded(self, mock_is_uploaded, mock_token):
        df = _make_df()
        result = post_all_weeks(df)
        assert result["totals"]["success"] == 0
        assert result["totals"]["failed"] == 0

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.post_time_entry", return_value={"success": True})
    @patch("src.sharepoint.is_week_uploaded", return_value=True)
    def test_force_uploads_all_weeks(self, mock_is_uploaded, mock_post, mock_token):
        df = _make_df()
        result = post_all_weeks(df, force=True)
        # 3 data entries total (2 in week 1, 1 in week 2, excluding WEEK TOTAL rows)
        assert result["totals"]["success"] == 3
        assert result["totals"]["failed"] == 0
