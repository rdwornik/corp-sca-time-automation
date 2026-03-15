"""
Calendar JSON loader.
"""

import json
from pathlib import Path
from typing import TypedDict

from src.config import get_settings, get_excluded


class CalendarEvent(TypedDict):
    start: str
    end: str
    category: str
    title: str
    minutes: int
    all_day: bool
    external_domains: str
    location: str
    recipients: int
    busy_status: int


def load_calendar(path: str | Path | None = None) -> list[CalendarEvent]:
    """Load calendar events from JSON export."""
    if path is None:
        settings = get_settings()
        path = Path(settings["paths"]["calendar_input"])

    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    return data["events"]


def filter_excluded(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """Remove events with excluded categories."""
    excluded = get_excluded()
    excluded_cats = {c.upper() for c in excluded["categories"]}

    return [e for e in events if e["category"].upper() not in excluded_cats]


def filter_by_weeks(
    events: list[CalendarEvent], weeks_back: int
) -> list[CalendarEvent]:
    """Filter events to last N weeks."""
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(weeks=weeks_back)
    return [
        e for e in events if datetime.strptime(e["start"][:10], "%Y-%m-%d") >= cutoff
    ]


def load_and_filter(
    path: str | Path | None = None, weeks_back: int | None = None
) -> list[CalendarEvent]:
    """Load calendar and filter excluded categories.

    Args:
        path: Path to calendar JSON file
        weeks_back: If specified, filter to last N weeks
    """
    events = load_calendar(path)
    events = filter_excluded(events)

    if weeks_back is not None:
        events = filter_by_weeks(events, weeks_back)

    return events
