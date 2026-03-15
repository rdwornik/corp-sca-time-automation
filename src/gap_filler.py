"""
Fill empty time slots (9:00-17:00) with generated entries.
"""

import pandas as pd
from datetime import datetime, timedelta

# Categories that can be autofilled
AUTOFILL_CATEGORIES = {
    "Prep - Demo/ Presentation",
    "Internal Meeting",
    "Admin",
    "Training",
    "Support",
}

# NEVER autofill these
NEVER_AUTOFILL = {
    "Customer - Demo/ Presentation",
    "Discovery",
    "POC",
    "RFI/RFP/RFQ",  # Requires specific client engagement
    "Travel",
    "Time Off",
}

WORK_START = 9  # 9:00
WORK_END = 17  # 17:00


def find_empty_slots(events: list, date: datetime) -> list[tuple[int, int]]:
    """
    Find empty time slots between 9:00-17:00 for a given date.
    Returns list of (start_hour, end_hour) tuples.
    """
    date_str = date.strftime("%Y-%m-%d")

    # Get events for this day
    day_events = []
    for e in events:
        if e["start"].startswith(date_str):
            start_hour = int(e["start"][11:13])
            end_hour = int(e["end"][11:13])
            end_min = int(e["end"][14:16])
            if end_min > 0:
                end_hour += 1
            day_events.append((max(start_hour, WORK_START), min(end_hour, WORK_END)))

    # Find empty slots
    occupied = [False] * 24
    for start, end in day_events:
        for h in range(start, end):
            if 0 <= h < 24:
                occupied[h] = True

    empty_slots = []
    slot_start = None

    for hour in range(WORK_START, WORK_END):
        if not occupied[hour]:
            if slot_start is None:
                slot_start = hour
        else:
            if slot_start is not None:
                empty_slots.append((slot_start, hour))
                slot_start = None

    if slot_start is not None:
        empty_slots.append((slot_start, WORK_END))

    return empty_slots


def calculate_category_distribution(df: pd.DataFrame, week: str) -> dict[str, float]:
    """
    Calculate percentage distribution of autofillable categories for a week.
    Works with individual calendar events (non-aggregated data).
    Returns dict of {(category, client, opp_id): proportion}.
    """
    week_data = df[
        (df["week_beginning"] == week)
        & (df["category"].isin(AUTOFILL_CATEGORIES))
        & (~df["is_autofilled"])
    ]

    if week_data.empty:
        return {("Prep - Demo/ Presentation", "", ""): 1.0}

    total = week_data["hours"].sum()
    if total == 0:
        return {("Prep - Demo/ Presentation", "", ""): 1.0}

    distribution = {}
    for _, row in week_data.iterrows():
        cat = row["category"]
        client = row.get("client", "")
        opp_id = row.get("opportunity_id", "")
        key = (cat, client, opp_id)
        distribution[key] = distribution.get(key, 0) + row["hours"] / total

    return distribution


def generate_autofill_entries(
    events: list,
    aggregated_df: pd.DataFrame,
    week: str,
    empty_hours: float,
    use_ai: bool = True,
) -> list[dict]:
    """
    Generate new entries to fill empty hours, distributed by category proportion.
    Ensures total hours equals exactly empty_hours (no rounding errors).

    Args:
        events: Calendar events list
        aggregated_df: Aggregated DataFrame
        week: Week beginning date (YYYY-MM-DD)
        empty_hours: Number of hours to fill
        use_ai: If True, use Gemini AI for comment generation
    """
    from src.gemini_client import generate_autofill_comment
    from src.config import get_settings

    # Categories that should NEVER have opportunity_id or client
    NO_OPPORTUNITY_ID_CATEGORIES = {
        "Training",
        "Admin",
        "Support",
        "Travel",
        "Time Off",
    }

    distribution = calculate_category_distribution(aggregated_df, week)

    # Build context for Gemini from week activities
    week_data = aggregated_df[
        (aggregated_df["week_beginning"] == week)
        & (aggregated_df["category"] != ">>> WEEK TOTAL")
    ]
    if "comments" in week_data.columns and not week_data["comments"].empty:
        week_context = "; ".join(week_data["comments"].head(3).tolist())
    else:
        week_context = "General work"

    # Calculate hours with rounding
    new_entries = []
    total_allocated = 0.0

    for (cat, client, opp_id), proportion in distribution.items():
        hours = round(empty_hours * proportion * 2) / 2  # Round to 0.5
        if hours > 0:
            # Clear client/opportunity_id for non-sales categories
            if cat in NO_OPPORTUNITY_ID_CATEGORIES:
                client = ""
                opp_id = ""

            # Generate comment for autofilled entry
            settings = get_settings()
            ai_enabled = settings["ai"]["enabled"] and use_ai

            comment = None
            if ai_enabled:
                comment = generate_autofill_comment(cat, client, week_context)

            if not comment:
                # Fallback to simple comment
                if client:
                    comment = f"{cat} work for {client}"
                else:
                    comment = f"{cat} work"

            new_entries.append(
                {
                    "week_beginning": week,
                    "category": cat,
                    "client": client,
                    "hours": hours,
                    "opportunity_id": opp_id,
                    "comments": comment,
                    "external_domains": "",
                    "needs_review": True,
                    "is_autofilled": True,
                    "status": "NEW",
                }
            )
            total_allocated += hours

    # Fix rounding errors - ensure total equals exactly empty_hours
    if new_entries and abs(total_allocated - empty_hours) > 0.01:
        difference = empty_hours - total_allocated
        # Add/subtract difference to the largest entry (most visible)
        largest_entry = max(new_entries, key=lambda x: x["hours"])
        largest_entry["hours"] = round((largest_entry["hours"] + difference) * 2) / 2
        # Ensure we don't create negative hours
        if largest_entry["hours"] < 0:
            largest_entry["hours"] = 0

    return new_entries


def fill_gaps_with_new_entries(
    aggregated_df: pd.DataFrame, use_ai: bool = True, target_hours: float = 40.0
) -> pd.DataFrame:
    """
    Find actual empty time slots and create new autofilled entries.
    Only fills if there are truly empty hours in the calendar.

    Args:
        aggregated_df: Aggregated DataFrame with events
        use_ai: If True, use Gemini AI for comment generation
        target_hours: Target hours per week (default 40.0)
    """
    from src.loader import load_and_filter

    events = load_and_filter()
    df = aggregated_df.copy()

    # Ensure is_autofilled column exists and is False for original entries
    if "is_autofilled" not in df.columns:
        df["is_autofilled"] = False
    df["is_autofilled"] = df["is_autofilled"].fillna(False)

    all_new_entries = []

    for week in df["week_beginning"].unique():
        # Skip Time Off weeks
        has_time_off = (
            (df["week_beginning"] == week) & (df["category"] == "Time Off")
        ).any()
        if has_time_off:
            continue

        # Skip WEEK TOTAL rows
        week_data = df[
            (df["week_beginning"] == week) & (df["category"] != ">>> WEEK TOTAL")
        ]

        current_hours = week_data["hours"].sum()

        if current_hours >= target_hours:
            continue

        # Find ACTUAL empty slots in the calendar for this week
        week_date = datetime.strptime(week, "%Y-%m-%d")
        total_empty_hours = 0

        for day_offset in range(7):
            day = week_date + timedelta(days=day_offset)
            if day.weekday() < 5:  # Weekdays only
                empty_slots = find_empty_slots(events, day)
                for start_h, end_h in empty_slots:
                    total_empty_hours += end_h - start_h

        # Only autofill if there are actual empty slots
        if total_empty_hours > 0:
            # Don't exceed available empty slots or target
            empty_hours = min(total_empty_hours, target_hours - current_hours)

            if empty_hours > 0:
                new_entries = generate_autofill_entries(
                    events, df, week, empty_hours, use_ai
                )
                all_new_entries.extend(new_entries)

    # Add new entries to dataframe
    if all_new_entries:
        from src.aggregator import add_week_summaries

        new_df = pd.DataFrame(all_new_entries)
        df = pd.concat(
            [df[df["category"] != ">>> WEEK TOTAL"], new_df], ignore_index=True
        )

        # Recalculate week totals
        df = df.sort_values(["week_beginning", "category", "client"])
        df = add_week_summaries(df)

    return df
