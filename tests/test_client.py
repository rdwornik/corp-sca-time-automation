import json

with open("data/input/calendar_export.json", "r", encoding="utf-8-sig") as f:
    data = json.load(f)

    print("=== INTERNAL MEETING events ===")
    for e in data["events"]:
        if e["category"] == "INTERNAL MEETING":
            print(f"{e['start']} - {e['end']}: {e['title'][:50]}")
