"""
Generate Excel preview for approval before SharePoint submission.
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from src.config import get_settings
from src.loader import load_and_filter
from src.mapper import map_category, detect_client
from src.project_codes import load_project_codes, match_opportunity_id
from src.overlap import resolve_overlaps_by_hour
from src.gap_filler import fill_gaps_with_new_entries


def get_week_beginning(date_str: str) -> str:
    """Get Sunday of the week for given date."""
    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
    days_since_sunday = (dt.weekday() + 1) % 7
    sunday = dt - timedelta(days=days_since_sunday)
    return sunday.strftime("%Y-%m-%d")


def round_hours(hours: float, precision: float = 0.5) -> float:
    """Round hours to nearest precision."""
    return round(hours / precision) * precision


def split_multiday_events(events: list) -> list:
    """Split multi-day all_day events into daily entries (8h per workday)."""
    result = []

    for event in events:
        if not event.get("all_day") or event["minutes"] <= 480:
            result.append(event)
            continue

        start = datetime.strptime(event["start"][:10], "%Y-%m-%d")
        end = datetime.strptime(event["end"][:10], "%Y-%m-%d")

        current = start
        while current < end:
            if current.weekday() < 5:  # Skip weekends
                daily_event = event.copy()
                daily_event["start"] = current.strftime("%Y-%m-%d 09:00")
                daily_event["end"] = current.strftime("%Y-%m-%d 17:00")
                daily_event["minutes"] = 480
                daily_event["all_day"] = False
                result.append(daily_event)
            current += timedelta(days=1)

    return result


def generate_preview(
    output_path: str | Path | None = None, weeks_back: int | None = None
) -> pd.DataFrame:
    """Generate Excel preview from calendar events.

    Uses project_codes.xlsx as single source of truth for client detection.

    Args:
        output_path: Path to output Excel file
        weeks_back: If specified, filter to last N weeks
    """

    # Categories that should NEVER have opportunity_id or client
    NO_OPPORTUNITY_ID_CATEGORIES = {
        "Training",
        "Admin",
        "Support",
        "Travel",
        "Time Off",
    }

    events = load_and_filter(weeks_back=weeks_back)
    events = split_multiday_events(events)

    # Resolve overlaps - only highest priority per hour
    events = resolve_overlaps_by_hour(events, lambda e: map_category(e["category"]))

    project_codes = load_project_codes()
    rows = []

    for event in events:
        sp_category = map_category(event["category"])
        if not sp_category:
            continue

        # detect_client now uses project_codes.xlsx directly
        client = detect_client(event)

        week = get_week_beginning(event["start"])
        hours = round_hours(event["minutes"] / 60)

        # Match opportunity ID for ANY row with client
        opp_id, needs_review = "", False
        if client:
            opp_id, needs_review = match_opportunity_id(
                client, event["title"], project_codes
            )

        # Clear client and opportunity_id for non-sales categories
        if sp_category in NO_OPPORTUNITY_ID_CATEGORIES:
            client = ""
            opp_id = ""
            needs_review = False

        rows.append(
            {
                "week_beginning": week,
                "category": sp_category,
                "client": client or "",
                "hours": hours,
                "opportunity_id": opp_id,
                "title": event["title"],
                "external_domains": event.get("external_domains", ""),
                "needs_review": needs_review,
                "is_autofilled": False,
                "status": "NEW",
            }
        )

    df = pd.DataFrame(rows)
    return df


def generate_aggregated_preview(
    output_path: str | Path | None = None, weeks_back: int | None = None
) -> pd.DataFrame:
    """
    Generate Excel preview with WEEK TOTAL summaries.
    Each calendar event is a separate row (no aggregation by category).

    Args:
        output_path: Path to output Excel file
        weeks_back: If specified, filter to last N weeks
    """
    from src.aggregator import aggregate_entries, add_week_summaries

    settings = get_settings()
    if output_path is None:
        output_path = Path(settings["paths"]["excel_preview"])

    df = generate_preview(output_path=None, weeks_back=weeks_back)
    # aggregate_entries now just sorts and prepares data (no aggregation)
    sorted_df = aggregate_entries(df)
    # Add WEEK TOTAL summary rows
    df_with_summary = add_week_summaries(sorted_df)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_with_summary.to_excel(output_path, index=False)

    return df_with_summary


def generate_final_preview(
    output_path: str | Path | None = None,
    fill: bool = True,
    weeks_back: int | None = None,
) -> pd.DataFrame:
    """Generate final Excel preview with gap filling and colors.

    Args:
        output_path: Path to output Excel file
        fill: If True, fill gaps to reach 40h target
        weeks_back: If specified, filter to last N weeks
    """
    from src.excel_writer import write_excel_with_formatting

    settings = get_settings()
    if output_path is None:
        output_path = Path(settings["paths"]["excel_preview"])

    df = generate_aggregated_preview(output_path=None, weeks_back=weeks_back)

    if fill:
        df = fill_gaps_with_new_entries(df)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    write_excel_with_formatting(df, output_path)

    return df
