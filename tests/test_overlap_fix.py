"""
Test script to verify overlap resolution is working correctly.
"""

from src.overlap import resolve_overlaps_by_hour, get_priority
from src.mapper import map_category

# Test events: 3 overlapping meetings at 15:00-16:00
test_events = [
    {
        "title": "Supply Chain Advisory All-Hands Meeting",
        "category": "INTERNAL MEETING",
        "start": "2025-12-16 15:00",
        "end": "2025-12-16 16:00",
        "minutes": 60,
    },
    {
        "title": "Tel Robert",
        "category": "INTERNAL MEETING",
        "start": "2025-12-16 15:00",
        "end": "2025-12-16 16:00",
        "minutes": 60,
    },
    {
        "title": "Alignment on DSP Service Description",
        "category": "INTERNAL MEETING",
        "start": "2025-12-16 15:00",
        "end": "2025-12-16 16:00",
        "minutes": 60,
    },
]

print("=== Testing Overlap Resolution ===\n")
print("Input: 3 overlapping Internal Meetings at 15:00-16:00")
print(f"Total minutes BEFORE resolution: {sum(e['minutes'] for e in test_events)}")
print()

# Test category mapping
for event in test_events:
    sp_cat = map_category(event["category"])
    priority = get_priority(sp_cat)
    print(f"  - {event['title'][:40]}...")
    print(f"    Category: {sp_cat}, Priority: {priority}")
print()

# Resolve overlaps
resolved = resolve_overlaps_by_hour(test_events, lambda e: map_category(e["category"]))

print(f"Output: {len(resolved)} event(s) after overlap resolution")
print(f"Total minutes AFTER resolution: {sum(e['minutes'] for e in resolved)}")
print()

for event in resolved:
    print(f"  [OK] {event['title']}")
    print(f"       Minutes: {event['minutes']}")
print()

if len(resolved) == 1 and resolved[0]["minutes"] == 60:
    print("[SUCCESS] Only 1 event with 60 minutes (overlap resolved correctly)")
else:
    print(f"[FAILURE] Expected 1 event with 60 minutes, got {len(resolved)} events")
    print(f"          Total: {sum(e['minutes'] for e in resolved)} minutes")
