"""
Load and match project codes (Opportunity IDs).
"""

import pandas as pd
from pathlib import Path
from src.config import get_settings


def load_project_codes(path: str | Path | None = None) -> pd.DataFrame:
    """Load project codes from Excel - supports old and new format."""
    if path is None:
        settings = get_settings()
        path = Path(settings["paths"]["project_codes"])

    df = pd.read_excel(path)

    # Detect format and normalize column names
    if "JDA OpptyID" in df.columns:
        # New format
        df = df.rename(
            columns={
                "JDA OpptyID": "code",
                "Account Name": "company",
                "Opportunity Name": "description",
            }
        )
    elif "Project Code" in df.columns:
        # Old format with headers
        df = df.rename(
            columns={
                "Project Code": "code",
                "Company": "company",
                "Project Description": "description",
            }
        )
    else:
        # Legacy format without headers (positional)
        df.columns = ["company", "description", "code"]

    df["company_lower"] = df["company"].str.lower().str.strip()
    df["description_lower"] = df["description"].str.lower().str.strip()

    return df


def match_opportunity_id(
    client: str, event_title: str, project_codes: pd.DataFrame
) -> tuple[str, bool]:
    """
    Find Opportunity ID for client + event context.
    Returns: (code, needs_review)
    """
    if not client:
        return "", False

    client_lower = client.lower().strip()

    # Find projects for this client - exact or contains
    matches = project_codes[
        project_codes["company_lower"].str.contains(client_lower, case=False, na=False)
    ]

    if matches.empty:
        return "", False

    if len(matches) == 1:
        return matches.iloc[0]["code"], False

    # Multiple - try match description in title
    if event_title:
        title_lower = event_title.lower()
        for _, row in matches.iterrows():
            desc_words = [w for w in row["description_lower"].split() if len(w) > 3]
            for word in desc_words:
                if word in title_lower:
                    return row["code"], False

    # Return first, flag for review
    return matches.iloc[0]["code"], True
