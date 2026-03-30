"""
Test script to verify column order is correct.
Expected order: week_beginning, category, client, hours, opportunity_id,
                comments, external_domains, needs_review, is_autofilled, status
"""

import pandas as pd
from src.aggregator import aggregate_entries, add_week_summaries

# Create test data
test_data = [
    {
        "week_beginning": "2025-12-15",
        "category": "Internal Meeting",
        "hours": 1.0,
        "client": "",
        "opportunity_id": "",
        "title": "Test Meeting",
        "external_domains": "",
        "needs_review": False,
        "status": "NEW",
        "is_autofilled": False,
    }
]

expected_order = [
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

print("=== Testing Column Order ===\n")

df = pd.DataFrame(test_data)
result = aggregate_entries(df)

print("After aggregate_entries():")
print(f"Actual columns: {list(result.columns)}")
print(f"Expected order: {expected_order}")
print()

if list(result.columns) == expected_order:
    print("[SUCCESS] Column order matches in aggregate_entries()")
else:
    print("[FAILURE] Column order does not match in aggregate_entries()")
    print(f"Difference: {set(result.columns) ^ set(expected_order)}")
print()

# Test with week summaries
result_with_summary = add_week_summaries(result)

print("After add_week_summaries():")
print(f"Actual columns: {list(result_with_summary.columns)}")
print(f"Expected order: {expected_order}")
print()

if list(result_with_summary.columns) == expected_order:
    print("[SUCCESS] Column order matches in add_week_summaries()")
else:
    print("[FAILURE] Column order does not match in add_week_summaries()")
    print(f"Difference: {set(result_with_summary.columns) ^ set(expected_order)}")
print()

# Display first few rows
print("Sample output:")
print(result_with_summary.to_string(index=False))
