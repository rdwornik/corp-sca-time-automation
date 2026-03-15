"""
Keep each calendar event as separate row. No aggregation by category.
"""

import pandas as pd


def aggregate_entries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep each event as a separate row (no aggregation).
    Just sort by week and category.
    """
    df = df.copy()

    # Rename title to comments for Excel output
    if "title" in df.columns:
        df["comments"] = df["title"]
        df = df.drop(columns=["title"])

    # Ensure required columns exist
    if "status" not in df.columns:
        df["status"] = "NEW"
    if "is_autofilled" not in df.columns:
        df["is_autofilled"] = False

    # Sort by week, category, client for organized output
    df = df.sort_values(["week_beginning", "category", "client"])

    # Reorder columns
    column_order = [
        "week_beginning",
        "category",
        "client",
        "hours",
        "opportunity_id",
        "comments",
        "external_domains",
        "needs_review",
        "is_autofilled",
        "status",
    ]

    # Only include columns that exist in the dataframe
    final_columns = [col for col in column_order if col in df.columns]
    df = df[final_columns]

    return df


def add_week_summaries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add WEEK TOTAL summary row after each week with total hours.
    """
    rows = []

    # Sort weeks to ensure consistent ordering
    for week in sorted(df["week_beginning"].unique()):
        week_data = df[df["week_beginning"] == week]

        # Add all events for this week
        for _, row in week_data.iterrows():
            rows.append(row.to_dict())

        # Add WEEK TOTAL summary row
        total_hours = week_data["hours"].sum()
        summary_row = {
            "week_beginning": week,
            "category": ">>> WEEK TOTAL",
            "client": "",
            "hours": total_hours,
            "opportunity_id": "",
            "comments": f"Total: {total_hours}h / 40h = {total_hours / 40 * 100:.0f}%",
            "external_domains": "",
            "needs_review": False,
            "is_autofilled": False,
            "status": "---",
        }
        rows.append(summary_row)

    result_df = pd.DataFrame(rows)

    # Reorder columns to match standard order
    column_order = [
        "week_beginning",
        "category",
        "client",
        "hours",
        "opportunity_id",
        "comments",
        "external_domains",
        "needs_review",
        "is_autofilled",
        "status",
    ]

    # Only include columns that exist in the dataframe
    final_columns = [col for col in column_order if col in result_df.columns]
    result_df = result_df[final_columns]

    return result_df
