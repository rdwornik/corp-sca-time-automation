"""Tests for the per-day `date` column threading (Tenrox migration Step 4a)."""

import pandas as pd

from src.aggregator import aggregate_entries, add_week_summaries
from src.gap_filler import _distribute_entry_dates


class TestDistributeEntryDates:
    """_distribute_entry_dates pours autofill hours onto real weekday dates."""

    def _entry(self, hours, cat="Admin"):
        return {
            "week_beginning": "2026-06-28",
            "category": cat,
            "client": "",
            "hours": hours,
            "opportunity_id": "",
            "comments": f"{cat} work",
            "is_autofilled": True,
            "status": "NEW",
        }

    def test_single_entry_fits_first_day(self):
        cap = [("2026-06-29", 8.0), ("2026-06-30", 8.0)]
        out = _distribute_entry_dates([self._entry(3.0)], cap)
        assert len(out) == 1
        assert out[0]["date"] == "2026-06-29"
        assert out[0]["hours"] == 3.0

    def test_entry_splits_across_days_when_day_full(self):
        cap = [("2026-06-29", 2.0), ("2026-06-30", 8.0)]
        out = _distribute_entry_dates([self._entry(5.0)], cap)
        # 2h on Mon (capacity), remaining 3h on Tue
        assert [(e["date"], e["hours"]) for e in out] == [
            ("2026-06-29", 2.0),
            ("2026-06-30", 3.0),
        ]

    def test_totals_preserved_across_multiple_entries(self):
        cap = [("2026-06-29", 4.0), ("2026-06-30", 4.0)]
        entries = [self._entry(3.0, "Admin"), self._entry(5.0, "Training")]
        out = _distribute_entry_dates(entries, cap)
        assert sum(e["hours"] for e in out) == 8.0
        # every produced row carries a real date
        assert all(e["date"] in {"2026-06-29", "2026-06-30"} for e in out)

    def test_hours_stay_on_half_hour_grid(self):
        cap = [("2026-06-29", 3.0), ("2026-06-30", 3.0)]
        out = _distribute_entry_dates([self._entry(2.5), self._entry(1.5)], cap)
        assert all(e["hours"] % 0.5 == 0.0 for e in out)

    def test_overflow_falls_back_to_last_day(self):
        # sum(entries) > sum(capacity): remainder attaches to the last day,
        # preserving the total rather than dropping hours.
        cap = [("2026-06-29", 1.0)]
        out = _distribute_entry_dates([self._entry(3.0)], cap)
        assert sum(e["hours"] for e in out) == 3.0
        assert out[-1]["date"] == "2026-06-29"

    def test_empty_capacity_falls_back_to_week(self):
        out = _distribute_entry_dates([self._entry(2.0)], [])
        assert out[0]["date"] == "2026-06-28"  # week_beginning fallback


class TestAggregatorDateColumn:
    """aggregate_entries / add_week_summaries carry the date column through."""

    def _df(self):
        return pd.DataFrame([
            {
                "week_beginning": "2026-06-28",
                "date": "2026-06-30",
                "category": "Discovery",
                "client": "Acme",
                "hours": 2.0,
                "opportunity_id": "OP-1",
                "title": "call",
                "external_domains": "",
                "needs_review": False,
                "is_autofilled": False,
                "status": "NEW",
            }
        ])

    def test_date_is_second_column(self):
        result = aggregate_entries(self._df())
        assert list(result.columns)[:2] == ["week_beginning", "date"]

    def test_week_total_row_has_blank_date(self):
        result = add_week_summaries(aggregate_entries(self._df()))
        total = result[result["category"] == ">>> WEEK TOTAL"].iloc[0]
        assert total["date"] == ""
        assert result[result["category"] == "Discovery"].iloc[0]["date"] == "2026-06-30"

    def test_dateless_frame_unaffected(self):
        # Backward compatibility: a frame without a date column must not gain one.
        df = self._df().drop(columns=["date"])
        result = add_week_summaries(aggregate_entries(df))
        assert "date" not in result.columns
