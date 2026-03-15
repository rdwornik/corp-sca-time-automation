"""
Test script to verify no aggregation by category.
Each event should be a separate row.
"""

import pandas as pd
from src.aggregator import aggregate_entries, add_week_summaries

# Create test data: 3 separate events with same category+client
test_data = [
    {
        "week_beginning": "2025-12-15",
        "category": "Internal Meeting",
        "hours": 1.0,
        "client": "",
        "opportunity_id": "",
        "title": "Supply Chain Advisory All-Hands Meeting",
        "external_domains": "",
        "needs_opp_id": False,
        "needs_review": False,
        "status": "NEW",
        "is_autofilled": False,
    },
    {
        "week_beginning": "2025-12-15",
        "category": "Internal Meeting",
        "hours": 1.0,
        "client": "",
        "opportunity_id": "",
        "title": "Tel Robert",
        "external_domains": "",
        "needs_opp_id": False,
        "needs_review": False,
        "status": "NEW",
        "is_autofilled": False,
    },
    {
        "week_beginning": "2025-12-15",
        "category": "Internal Meeting",
        "hours": 0.5,
        "client": "",
        "opportunity_id": "",
        "title": "Alignment on DSP Service Description",
        "external_domains": "",
        "needs_opp_id": False,
        "needs_review": False,
        "status": "NEW",
        "is_autofilled": False,
    },
]

print("=== Testing No Aggregation by Category ===\n")
print(f"Input: {len(test_data)} Internal Meeting events")
print(f"Total hours: {sum(e['hours'] for e in test_data)}")
for event in test_data:
    print(f"  - {event['title']}: {event['hours']}h")
print()

df = pd.DataFrame(test_data)

# Call aggregate_entries (should NOT aggregate anymore)
result = aggregate_entries(df)

print(f"After aggregate_entries(): {len(result)} rows (excluding WEEK TOTAL)")
print()

# Add week summaries
result_with_summary = add_week_summaries(result)

# Filter out WEEK TOTAL rows for counting
data_rows = result_with_summary[result_with_summary["category"] != ">>> WEEK TOTAL"]
summary_rows = result_with_summary[result_with_summary["category"] == ">>> WEEK TOTAL"]

print(f"After add_week_summaries():")
print(f"  - Data rows: {len(data_rows)}")
print(f"  - WEEK TOTAL rows: {len(summary_rows)}")
print()

print("Data rows:")
for _, row in data_rows.iterrows():
    print(f"  - {row.get('comments', row.get('title', 'N/A'))}: {row['hours']}h")
print()

print("WEEK TOTAL:")
for _, row in summary_rows.iterrows():
    print(f"  - {row['comments']}")
print()

# Verify expectations
if len(data_rows) == 3 and len(summary_rows) == 1:
    total_hours = summary_rows.iloc[0]["hours"]
    if total_hours == 2.5:
        print("[SUCCESS] No aggregation - 3 separate events + 1 WEEK TOTAL (2.5h)")
    else:
        print(f"[FAILURE] WEEK TOTAL should be 2.5h, got {total_hours}h")
else:
    print(
        f"[FAILURE] Expected 3 data rows + 1 WEEK TOTAL, got {len(data_rows)} + {len(summary_rows)}"
    )
