"""
Handle overlapping calendar events - select highest priority per time slot.
"""

from datetime import datetime, timedelta
from collections import defaultdict

CATEGORY_PRIORITY = {
    "Customer - Demo/ Presentation": 100,
    "Discovery": 90,
    "RFI/RFP/RFQ": 85,
    "POC": 80,
    "Prep - Demo/ Presentation": 70,
    "Internal Meeting": 50,
    "Training": 40,
    "Support": 30,
    "Admin": 20,
    "Travel": 10,
    "Time Off": 5,
}


def parse_datetime(dt_str: str) -> datetime:
    return datetime.strptime(dt_str[:16], "%Y-%m-%d %H:%M")


def get_priority(category: str) -> int:
    return CATEGORY_PRIORITY.get(category, 0)


def resolve_overlaps_by_hour(events: list, get_category_func) -> list:
    """
    For each hour slot, keep only the highest priority event.
    Adjusts event minutes based on hours won.
    """
    hour_map = defaultdict(list)

    for idx, event in enumerate(events):
        sp_category = get_category_func(event)
        if not sp_category:
            continue

        priority = get_priority(sp_category)
        start = parse_datetime(event["start"])
        end = parse_datetime(event["end"])

        current = start.replace(minute=0, second=0)
        while current < end:
            hour_key = (current.date(), current.hour)
            hour_map[hour_key].append((idx, priority, sp_category))
            current += timedelta(hours=1)

    selected_hours = defaultdict(int)

    for hour_key, candidates in hour_map.items():
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            winner_idx = candidates[0][0]
            selected_hours[winner_idx] += 1

    result = []
    for idx, event in enumerate(events):
        won_hours = selected_hours.get(idx, 0)
        if won_hours > 0:
            new_event = event.copy()
            new_event["minutes"] = won_hours * 60
            result.append(new_event)

    return result
