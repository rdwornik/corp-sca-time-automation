"""Tests for the Tenrox payload builder (src/tenrox.build_week_payload)."""

from datetime import date

import pandas as pd

from src.tenrox import build_week_payload, _note


def _df(rows: list[dict]) -> pd.DataFrame:
    base = {
        "week_beginning": "2026-06-28",
        "date": "2026-06-29",
        "category": "Admin",
        "client": "",
        "hours": 1.0,
        "opportunity_id": "",
        "comments": "work",
        "external_domains": "",
        "needs_review": False,
        "is_autofilled": False,
        "status": "NEW",
    }
    return pd.DataFrame([{**base, **r} for r in rows])


RUN = date(2026, 7, 5)  # mission run date; keeps the future-date guard deterministic


class TestOverhead:
    def test_admin_is_postable_hours_only(self):
        p = build_week_payload(_df([{"category": "Admin", "hours": 2.0, "date": "2026-06-29"}]), "2026-06-28", RUN)
        e = p["entries"][0]
        assert e["postable"] is True
        assert e["seconds"] == 7200
        assert e["assignment"] == "administration"
        assert e["assignment_attribute_uid"] == 4823451
        assert e["note"] == '"Admin","work"'  # overhead: no OPID field

    def test_hours_to_seconds_quarter_hour(self):
        p = build_week_payload(_df([{"category": "Admin", "hours": 0.25}]), "2026-06-28", RUN)
        assert p["entries"][0]["seconds"] == 900

    def test_travel_maps_to_travel_admin(self):
        p = build_week_payload(_df([{"category": "Travel", "hours": 1.0}]), "2026-06-28", RUN)
        assert p["entries"][0]["assignment"] == "travel_administration"
        assert p["entries"][0]["assignment_attribute_uid"] == 4823454


class TestSalesHold:
    def test_sales_held_pending_note_mechanism(self):
        p = build_week_payload(_df([{"category": "Discovery", "hours": 3.0, "opportunity_id": "OP-1"}]), "2026-06-28", RUN)
        e = p["entries"][0]
        assert e["postable"] is False
        assert "note mechanism" in e["hold_reason"]
        assert e["assignment"] == "sales_activities"

    def test_sales_missing_opid_reported(self):
        p = build_week_payload(_df([{"category": "POC", "hours": 2.0, "opportunity_id": ""}]), "2026-06-28", RUN)
        assert p["entries"][0]["hold_reason"] == "sales entry missing opportunity_id"

    def test_sales_note_format_when_built(self):
        # The note string is assembled even while the entry is held.
        p = build_week_payload(_df([{"category": "Discovery", "hours": 1.0, "opportunity_id": "OP-001008", "comments": "call"}]), "2026-06-28", RUN)
        assert p["entries"][0]["note"] == '"Discovery","OP-001008","call"'


class TestGroupingAndDates:
    def test_same_day_same_category_grouped(self):
        rows = [
            {"category": "Admin", "hours": 1.0, "date": "2026-06-29", "comments": "a"},
            {"category": "Admin", "hours": 2.0, "date": "2026-06-29", "comments": "b"},
        ]
        p = build_week_payload(_df(rows), "2026-06-28", RUN)
        assert len(p["entries"]) == 1
        assert p["entries"][0]["hours"] == 3.0
        assert p["entries"][0]["note"] == '"Admin","a; b"'

    def test_different_days_not_grouped(self):
        rows = [
            {"category": "Admin", "hours": 1.0, "date": "2026-06-29"},
            {"category": "Admin", "hours": 1.0, "date": "2026-06-30"},
        ]
        p = build_week_payload(_df(rows), "2026-06-28", RUN)
        assert len(p["entries"]) == 2

    def test_entry_date_is_mmddyyyy(self):
        p = build_week_payload(_df([{"category": "Admin", "date": "2026-06-30"}]), "2026-06-28", RUN)
        assert p["entries"][0]["entry_date"] == "06-30-2026"

    def test_week_bounds(self):
        p = build_week_payload(_df([{"category": "Admin"}]), "2026-06-28", RUN)
        assert p["start_date"] == "06-28-2026"
        assert p["end_date"] == "07-04-2026"


class TestGuards:
    def test_time_off_skipped(self):
        p = build_week_payload(_df([{"category": "Time Off", "hours": 8.0}]), "2026-06-28", RUN)
        assert p["entries"] == []
        assert p["skipped"][0]["category"] == "Time Off"
        assert "non_working_time" in p["skipped"][0]["reason"]

    def test_future_date_held(self):
        # date after the run date must not be postable
        p = build_week_payload(_df([{"category": "Admin", "date": "2026-07-04"}]), "2026-06-28", date(2026, 6, 30))
        assert p["entries"][0]["postable"] is False
        assert "future-dated" in p["entries"][0]["hold_reason"]

    def test_unmapped_category_skipped(self):
        p = build_week_payload(_df([{"category": "Nonexistent Category", "hours": 1.0}]), "2026-06-28", RUN)
        assert p["entries"] == []
        assert "no Tenrox mapping" in p["skipped"][0]["reason"]

    def test_week_total_rows_ignored(self):
        rows = [{"category": "Admin", "hours": 1.0}, {"category": ">>> WEEK TOTAL", "hours": 1.0}]
        p = build_week_payload(_df(rows), "2026-06-28", RUN)
        assert len(p["entries"]) == 1

    def test_missing_date_column_raises(self):
        df = _df([{"category": "Admin"}]).drop(columns=["date"])
        try:
            build_week_payload(df, "2026-06-28", RUN)
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "date" in str(exc)


class TestNoteHelper:
    def test_endash_category_name_quoted(self):
        # Categories with special characters (en-dash / slashes) stay intact.
        assert _note("Customer - Demo/ Presentation", "OP-9", "x", True) == '"Customer - Demo/ Presentation","OP-9","x"'

    def test_embedded_quotes_neutralized(self):
        assert _note("Admin", "", 'say "hi"', False) == '"Admin","say \'hi\'"'
