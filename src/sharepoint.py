"""
SharePoint Graph API connector for SCA Time Tracker.
"""

import subprocess
import requests
from datetime import date
from typing import Optional
from src.config import get_env, get_settings


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
    """Get Graph API access token.

    Fallback chain:
    1. GRAPH_ACCESS_TOKEN env var (manual override)
    2. `az account get-access-token` CLI (auto-refreshes from az login session)
    3. Raise SystemExit prompting the user to run `az login`
    """
    # 1. Manual env var override
    token = get_env("GRAPH_ACCESS_TOKEN")
    if token:
        return token

    # 2. az CLI session
    try:
        result = subprocess.run(
            [
                "az", "account", "get-access-token",
                "--resource", "https://graph.microsoft.com",
                "--query", "accessToken",
                "-o", "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            token = result.stdout.strip()
            if token:
                return token
    except FileNotFoundError:
        pass  # az CLI not installed
    except Exception:
        pass

    raise SystemExit(
        "Cannot obtain a Graph API token.\n"
        "Run 'az login' to authenticate, then retry."
    )


def _parse_sharepoint_date(value: str) -> date:
    """Parse SharePoint date string like '2025-12-07T00:00:00Z' to datetime.date."""
    return date.fromisoformat(value[:10])


def _handle_response_errors(response: requests.Response, context: str) -> None:
    """Raise SystemExit on auth/permission errors."""
    if response.status_code == 401:
        raise SystemExit(
            f"Token expired or invalid during {context}. Run 'az login' first."
        )
    if response.status_code == 403:
        raise SystemExit(
            f"Access denied to SharePoint list during {context}. Check permissions."
        )


def get_uploaded_weeks(access_token: str = None) -> set[date]:
    """Return all WeekBeginning dates already uploaded to SharePoint.

    Handles pagination via @odata.nextLink.
    Returns empty set if list has no entries.
    """
    if access_token is None:
        access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    url = get_graph_url() + "?$expand=fields($select=WeekBeginning)&$top=5000"
    uploaded = set()

    while url:
        response = requests.get(url, headers=headers)
        _handle_response_errors(response, "get_uploaded_weeks")

        if response.status_code != 200:
            raise RuntimeError(
                f"Unexpected response from SharePoint: {response.status_code} {response.text}"
            )

        data = response.json()
        for item in data.get("value", []):
            raw = item.get("fields", {}).get("WeekBeginning")
            if raw:
                uploaded.add(_parse_sharepoint_date(raw))

        url = data.get("@odata.nextLink")

    return uploaded


def get_last_uploaded_week(access_token: str = None) -> Optional[date]:
    """Return the most recent WeekBeginning date uploaded to SharePoint.

    Returns None if no entries exist.
    """
    uploaded = get_uploaded_weeks(access_token)
    return max(uploaded) if uploaded else None


def is_week_uploaded(week_date: date, access_token: str = None) -> bool:
    """Check whether any entries exist for the given week date.

    Uses a server-side $filter for efficiency instead of fetching all weeks.
    """
    if access_token is None:
        access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    iso = week_date.isoformat()
    url = (
        get_graph_url()
        + "?$expand=fields($select=WeekBeginning)"
        + f"&$filter=fields/WeekBeginning eq '{iso}T00:00:00Z'&$top=1"
    )

    response = requests.get(url, headers=headers)
    _handle_response_errors(response, "is_week_uploaded")

    if response.status_code != 200:
        raise RuntimeError(
            f"Unexpected response from SharePoint: {response.status_code} {response.text}"
        )

    return len(response.json().get("value", [])) > 0


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


def post_week_entries(df, week: str, access_token: str = None, force: bool = False) -> list:
    """Post all entries for a specific week.

    Args:
        force: If True, upload even if week is already in SharePoint.
    """
    if access_token is None:
        access_token = get_access_token()

    # Idempotency check — skip unless forced
    week_date = date.fromisoformat(week) if isinstance(week, str) else week
    if not force and is_week_uploaded(week_date, access_token):
        print(f"  WARNING: week {week} already uploaded. Use --force to re-upload.")
        return []

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


def post_all_weeks(df, access_token: str = None, force: bool = False) -> dict:
    """Post all weeks from DataFrame to SharePoint.

    Args:
        force: If True, upload even if weeks are already in SharePoint.

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
        results = post_week_entries(df, week, access_token, force=force)
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
