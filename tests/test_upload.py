import subprocess

import pandas as pd
import pytest

from src.sharepoint import post_week_entries


def _az_logged_in() -> bool:
    """Check if az CLI has an active session."""
    try:
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(
    not _az_logged_in(),
    reason="az login session not active (required for Graph API token)",
)
def test_upload_week():
    df = pd.read_excel("data/output/time_entries_preview.xlsx")
    results = post_week_entries(df, "2025-12-07")

    success = sum(1 for r in results if r["success"])
    failed = [r for r in results if not r["success"]]

    print(f"\nSuccess: {success}/{len(results)}")
    if failed:
        print(f"First error: {failed[0]}")

    assert success == len(results), f"{len(failed)} entries failed"
