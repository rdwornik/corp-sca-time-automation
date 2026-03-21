"""
SharePoint Graph API connector for SCA Time Tracker.
"""

import requests
from azure.identity import AzureCliCredential
from src.config import get_settings


def get_graph_url() -> str:
    """Build Graph API URL from config."""
    settings = get_settings()
    site_id = settings["sharepoint"]["site_id"]
    list_id = settings["sharepoint"]["list_id"]
    base_url = settings["sharepoint"]["graph_base_url"]
    return f"{base_url}/sites/{site_id}/lists/{list_id}/items"


# Map our categories to SharePoint valid values
CATEGORY_MAP = {
    "Prep - Demo/ Presentation": "Prep – Demo/ Presentation",
    "Customer - Demo/ Presentation": "Customer – Demo/ Presentation",
    "Time Off": "Time Off",
    "Admin": "Admin",
    "Support": "Support",
    "Internal Meeting": "Internal Meeting",
    "Training": "Training",
    "Discovery": "Discovery",
    "RFI/RFP/RFQ": "RFI/RFP/RFQ",
    "POC": "POC",
    "Travel": "Travel",
}


def get_access_token() -> str:
    """Get Graph API token via az login session. Auto-refreshes."""
    try:
        credential = AzureCliCredential()
        token = credential.get_token("https://graph.microsoft.com/.default")
        return token.token
    except Exception as e:
        raise ValueError(
            f"Cannot get Graph token: {e}\n"
            f"Run 'az login' first, then retry."
        ) from e


def post_time_entry(entry: dict, access_token: str = None) -> dict:
    """Post single time entry to SharePoint."""
    import math

    if access_token is None:
        access_token = get_access_token()

    # Map category to SharePoint format
    sp_category = CATEGORY_MAP.get(entry.get("category"), entry.get("category"))

    # Clean NaN values
    def clean_value(val):
        if val is None:
            return None
        if isinstance(val, float) and math.isnan(val):
            return None
        return val

    fields = {
        "WeekBeginning": entry["week_beginning"],
        "Category": sp_category,
        "Hours": float(entry["hours"]),
    }

    # Add optional fields only if not NaN/None
    comments = clean_value(entry.get("comments"))
    if comments:
        fields["Comments"] = str(comments)

    opp_id = clean_value(entry.get("opportunity_id"))
    if opp_id:
        fields["OpportunityID"] = str(opp_id)

    client = clean_value(entry.get("client"))
    if client:
        fields["AccountName"] = str(client)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(get_graph_url(), headers=headers, json={"fields": fields})

    if response.status_code == 201:
        return {"success": True, "data": response.json()}
    else:
        return {
            "success": False,
            "error": response.text,
            "status": response.status_code,
        }


def post_week_entries(df, week: str, access_token: str = None) -> list:
    """Post all entries for a specific week."""
    if access_token is None:
        access_token = get_access_token()

    week_data = df[
        (df["week_beginning"] == week) & (df["category"] != ">>> WEEK TOTAL")
    ]

    results = []
    for _, row in week_data.iterrows():
        result = post_time_entry(row.to_dict(), access_token)
        results.append(
            {
                "category": row["category"],
                "hours": row["hours"],
                "success": result["success"],
                "error": result.get("error"),
            }
        )
        print(
            f"  {'OK' if result['success'] else 'FAIL'} {row['category']}: {row['hours']}h"
        )

    return results


def post_all_weeks(df, access_token: str = None) -> dict:
    """Post all weeks from DataFrame to SharePoint.

    Returns:
        dict with 'by_week' (results per week) and 'totals' (success/fail counts)
    """
    import pandas as pd

    if access_token is None:
        access_token = get_access_token()

    # Get unique weeks (excluding summary rows)
    weeks = df[df["category"] != ">>> WEEK TOTAL"]["week_beginning"].unique()
    weeks = sorted([w for w in weeks if pd.notna(w)])

    all_results = {}
    total_success = 0
    total_failed = 0

    for week in weeks:
        print(f"\n[{week}]")
        results = post_week_entries(df, week, access_token)
        all_results[week] = results

        week_success = sum(1 for r in results if r["success"])
        week_failed = len(results) - week_success
        total_success += week_success
        total_failed += week_failed

    return {
        "by_week": all_results,
        "totals": {"success": total_success, "failed": total_failed},
        "weeks": weeks,
    }
