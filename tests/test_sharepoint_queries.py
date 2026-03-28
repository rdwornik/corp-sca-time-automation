"""Tests for SharePoint query functions — mocked Graph API."""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from src.sharepoint import (
    get_uploaded_weeks,
    get_last_uploaded_week,
    is_week_uploaded,
)


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.text = str(json_data)
    return mock


class TestGetUploadedWeeks:
    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_parses_dates_correctly(self, mock_get, _mock_token):
        mock_get.return_value = _mock_response({
            "value": [
                {"fields": {"WeekBeginning": "2025-12-07T00:00:00Z"}},
                {"fields": {"WeekBeginning": "2025-12-14T00:00:00Z"}},
            ]
        })
        result = get_uploaded_weeks()
        assert result == {date(2025, 12, 7), date(2025, 12, 14)}

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_empty_list_returns_empty_set(self, mock_get, _mock_token):
        mock_get.return_value = _mock_response({"value": []})
        result = get_uploaded_weeks()
        assert result == set()

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_handles_pagination(self, mock_get, _mock_token):
        page1 = _mock_response({
            "value": [{"fields": {"WeekBeginning": "2025-12-07T00:00:00Z"}}],
            "@odata.nextLink": "https://graph.microsoft.com/page2",
        })
        page2 = _mock_response({
            "value": [{"fields": {"WeekBeginning": "2025-12-14T00:00:00Z"}}],
        })
        mock_get.side_effect = [page1, page2]

        result = get_uploaded_weeks()
        assert result == {date(2025, 12, 7), date(2025, 12, 14)}
        assert mock_get.call_count == 2

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_401_raises_systemexit(self, mock_get, _mock_token):
        mock_get.return_value = _mock_response({}, status_code=401)
        with pytest.raises(SystemExit, match="az login"):
            get_uploaded_weeks()

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_403_raises_systemexit(self, mock_get, _mock_token):
        mock_get.return_value = _mock_response({}, status_code=403)
        with pytest.raises(SystemExit, match="Access denied"):
            get_uploaded_weeks()

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_skips_items_without_weekbeginning(self, mock_get, _mock_token):
        mock_get.return_value = _mock_response({
            "value": [
                {"fields": {}},
                {"fields": {"WeekBeginning": "2025-12-07T00:00:00Z"}},
            ]
        })
        result = get_uploaded_weeks()
        assert result == {date(2025, 12, 7)}


class TestGetLastUploadedWeek:
    @patch("src.sharepoint.get_uploaded_weeks")
    def test_returns_max_date(self, mock_uploaded):
        mock_uploaded.return_value = {
            date(2025, 12, 7),
            date(2025, 12, 14),
            date(2025, 11, 30),
        }
        result = get_last_uploaded_week()
        assert result == date(2025, 12, 14)

    @patch("src.sharepoint.get_uploaded_weeks")
    def test_returns_none_for_empty(self, mock_uploaded):
        mock_uploaded.return_value = set()
        result = get_last_uploaded_week()
        assert result is None


class TestIsWeekUploaded:
    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_returns_true_when_items_exist(self, mock_get, _mock_token):
        mock_get.return_value = _mock_response({
            "value": [{"fields": {"WeekBeginning": "2025-12-07T00:00:00Z"}}]
        })
        assert is_week_uploaded(date(2025, 12, 7)) is True

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_returns_false_when_no_items(self, mock_get, _mock_token):
        mock_get.return_value = _mock_response({"value": []})
        assert is_week_uploaded(date(2025, 12, 7)) is False

    @patch("src.sharepoint.get_access_token", return_value="fake-token")
    @patch("src.sharepoint.requests.get")
    def test_401_raises_systemexit(self, mock_get, _mock_token):
        mock_get.return_value = _mock_response({}, status_code=401)
        with pytest.raises(SystemExit, match="az login"):
            is_week_uploaded(date(2025, 12, 7))
