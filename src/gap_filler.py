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


def build_historical_profile(
    all_weeks_data: pd.DataFrame,
    current_week: str,
    window_size: int = 4,
) -> dict[tuple[str, str, str], float]:
    """
    Build a category profile from the last window_size weeks of non-autofilled data.

    Excludes current_week from the history window. Only includes AUTOFILL_CATEGORIES;
    NEVER_AUTOFILL categories are excluded even if present in the data.

    Returns {(category, client, opp_id): proportion} summing to 1.0,
    or empty dict if no historical data is available (signals Gemini fallback).
    """
    prior_weeks = sorted(
        [w for w in all_weeks_data["week_beginning"].unique() if w < current_week],
        reverse=True,
    )
    history_weeks = prior_weeks[:window_size]

    if not history_weeks:
        return {}

    history_data = all_weeks_data[
        (all_weeks_data["week_beginning"].isin(history_weeks))
        & (all_weeks_data["category"].isin(AUTOFILL_CATEGORIES))
        & (~all_weeks_data["category"].isin(NEVER_AUTOFILL))
        & (~all_weeks_data["is_autofilled"])
    ]

    if history_data.empty:
        return {}

    total = history_data["hours"].sum()
    if total == 0:
        return {}

    profile: dict[tuple[str, str, str], float] = {}
    for _, row in history_data.iterrows():
        cat = row["category"]
        client = str(row.get("client", "") or "")
        opp_id = str(row.get("opportunity_id", "") or "")
        key = (cat, client, opp_id)
        profile[key] = profile.get(key, 0.0) + row["hours"] / total

    return profile


def allocate_gap_hours(
    gap_hours: float,
    current_week_profile: dict[tuple[str, str, str], float],
    historical_profile: dict[tuple[str, str, str], float],
    current_weight: float = 0.5,
) -> dict[tuple[str, str, str], float]:
    """
    Blend current week and historical profiles, then allocate gap_hours.

    Returns {(category, client, opp_id): hours} rounded to 0.5h.
    NEVER_AUTOFILL categories are excluded from the output.
    Returns empty dict if blended profile is empty (signals Gemini fallback).
    """
    history_weight = 1.0 - current_weight
    all_keys = set(current_week_profile) | set(historical_profile)
    # Safety: strip any NEVER_AUTOFILL that shouldn't be present
    all_keys = {k for k in all_keys if k[0] not in NEVER_AUTOFILL}

    if not all_keys:
        return {}

    blended: dict[tuple[str, str, str], float] = {}
    for key in all_keys:
        cur = current_week_profile.get(key, 0.0) * current_weight
        hist = historical_profile.get(key, 0.0) * history_weight
        blended[key] = cur + hist

    # Normalize after filtering
    total_blend = sum(blended.values())
    if total_blend == 0:
        return {}
    blended = {k: v / total_blend for k, v in blended.items()}

    # Round each allocation to nearest 0.5h; drop zero-hour entries
    allocation: dict[tuple[str, str, str], float] = {}
    for key, proportion in blended.items():
        hours = round(gap_hours * proportion * 2) / 2
        if hours > 0:
            allocation[key] = hours

    return allocation


def generate_autofill_entries(
    events: list,
    aggregated_df: pd.DataFrame,
    week: str,
    empty_hours: float,
    use_ai: bool = True,
) -> list[dict]:
    """
    Generate new entries to fill empty hours using weighted-blend algorithm.

    Blends current week's category distribution with a historical profile from the
    last N weeks. Falls back to Gemini allocation when no profile is available.

    Args:
        events: Calendar events list
        aggregated_df: Full aggregated DataFrame (all weeks, used for history)
        week: Week beginning date (YYYY-MM-DD)
        empty_hours: Number of hours to fill
        use_ai: If True, use Gemini AI for comment generation and fallback allocation
    """
    from src.gemini_client import generate_autofill_comment, ask_gemini_allocation
    from src.config import get_settings

    # Categories that should NEVER have opportunity_id or client
    NO_OPPORTUNITY_ID_CATEGORIES = {
        "Training",
        "Admin",
        "Support",
        "Travel",
        "Time Off",
    }

    settings = get_settings()
    gf_cfg = settings.get("gap_filler", {})
    current_weight = float(gf_cfg.get("current_weight", 0.5))
    history_window = int(gf_cfg.get("history_window", 4))

    # Build current week and historical profiles
    current_profile = calculate_category_distribution(aggregated_df, week)
    historical_profile = build_historical_profile(
        aggregated_df, week, window_size=history_window
    )

    # Build context for Gemini from week activities
    week_data = aggregated_df[
        (aggregated_df["week_beginning"] == week)
        & (aggregated_df["category"] != ">>> WEEK TOTAL")
    ]
    if "comments" in week_data.columns and not week_data["comments"].empty:
        valid_comments = week_data["comments"].dropna().head(3).tolist()
        week_context = "; ".join(valid_comments) if valid_comments else "General work"
    else:
        week_context = "General work"

    # Determine allocation path
    allocation_by_key: dict[tuple[str, str, str], float] = {}

    if historical_profile:
        # Weighted blend path
        allocation_by_key = allocate_gap_hours(
            empty_hours, current_profile, historical_profile, current_weight
        )

    if not allocation_by_key and use_ai and settings["ai"]["enabled"]:
        # Gemini fallback: no history or blend produced empty result
        gemini_alloc = ask_gemini_allocation(
            empty_hours, week, list(AUTOFILL_CATEGORIES), week_context
        )
        # Convert category-only dict to (cat, "", "") keyed dict
        for cat, hours in gemini_alloc.items():
            # Inherit client/opp_id from current week profile if a matching key exists
            matched_key = next(
                (k for k in current_profile if k[0] == cat), (cat, "", "")
            )
            allocation_by_key[matched_key] = hours

    if not allocation_by_key:
        # Hard fallback: current profile proportions (original behaviour)
        for (cat, client, opp_id), proportion in current_profile.items():
            hours = round(empty_hours * proportion * 2) / 2
            if hours > 0:
                allocation_by_key[(cat, client, opp_id)] = hours

    # Build entry dicts
    new_entries = []
    total_allocated = 0.0
    ai_enabled = settings["ai"]["enabled"] and use_ai

    for (cat, client, opp_id), hours in allocation_by_key.items():
        if hours <= 0:
            continue

        if cat in NO_OPPORTUNITY_ID_CATEGORIES:
            client = ""
            opp_id = ""

        comment = None
        if ai_enabled:
            comment = generate_autofill_comment(cat, client, week_context)
        if not comment:
            comment = f"{cat} work for {client}" if client else f"{cat} work"

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

    # Fix rounding: keep total equal to empty_hours
    if new_entries and abs(total_allocated - empty_hours) > 0.01:
        difference = empty_hours - total_allocated
        largest_entry = max(new_entries, key=lambda x: x["hours"])
        largest_entry["hours"] = round((largest_entry["hours"] + difference) * 2) / 2
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
