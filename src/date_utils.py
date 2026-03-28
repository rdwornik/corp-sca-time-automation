"""
Pure date utilities for Sunday-based week calculations.

All week boundaries in this project are Sundays (weekday() == 6).
"""

from datetime import date, timedelta


def last_sunday(ref: date | None = None) -> date:
    """Return the most recent Sunday on or before ref (default: today)."""
    if ref is None:
        ref = date.today()
    days_since_sunday = (ref.weekday() + 1) % 7
    return ref - timedelta(days=days_since_sunday)


def sundays_between(start: date, end: date) -> list[date]:
    """Return all Sundays from start (exclusive) to end (inclusive).

    Both start and end must be Sundays.
    Returns empty list if start >= end.

    Example:
        sundays_between(date(2025, 2, 2), date(2025, 3, 23))
        -> [date(2025, 2, 9), ..., date(2025, 3, 23)]
    """
    if start.weekday() != 6:
        raise ValueError(f"start must be a Sunday, got {start} (weekday {start.weekday()})")
    if end.weekday() != 6:
        raise ValueError(f"end must be a Sunday, got {end} (weekday {end.weekday()})")

    result = []
    current = start + timedelta(weeks=1)
    while current <= end:
        result.append(current)
        current += timedelta(weeks=1)
    return result


def weeks_back_to_cover(target_sunday: date, ref: date | None = None) -> int:
    """Calculate weeks_back needed for filter_by_weeks to include target_sunday.

    filter_by_weeks uses: cutoff = datetime.now() - timedelta(weeks=weeks_back)
    This returns ceil((ref - target_sunday).days / 7) + 1 as a safety margin.
    """
    if ref is None:
        ref = date.today()
    delta_days = (ref - target_sunday).days
    if delta_days <= 0:
        return 1
    return (delta_days // 7) + 2  # +2: ceil + safety margin
