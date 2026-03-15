"""
Test script to verify Gemini AI client detection with project_codes.xlsx as source of truth.
"""

from src.mapper import detect_client

# Test cases for Gemini AI client detection
test_events = [
    {
        "title": "Dry run sessione IT",
        "external_domains": "",
        "expected_behavior": "Should use Gemini AI to detect Italian client (e.g., Veronesi)",
    },
    {
        "title": "Wurth meeting",
        "external_domains": "wurthindustry.com",
        "expected_behavior": "Should detect Wurth from domain hint or title",
    },
    {
        "title": "Meeting in Frankfurt office",
        "external_domains": "",
        "expected_behavior": "Should use Gemini AI to detect German client (e.g., Merz)",
    },
    {
        "title": "Internal alignment call",
        "external_domains": "",
        "expected_behavior": "Should return None (no client match)",
    },
]

print("=== Testing Gemini AI Client Detection ===\n")
print("NOTE: This test requires GEMINI_API_KEY in .env and project_codes.xlsx\n")
print("Client detection now uses project_codes.xlsx as single source of truth.\n")

for i, event in enumerate(test_events, 1):
    print(f"Test {i}: {event['title']}")
    if event["external_domains"]:
        print(f"        Domains: {event['external_domains']}")
    print(f"Expected: {event['expected_behavior']}")

    try:
        # detect_client now uses project_codes.xlsx directly
        client = detect_client(event)
        print(f"Result: {client or 'None'}")

        if client:
            print("[SUCCESS] Client detected")
        else:
            print("[OK] No client detected")

    except Exception as e:
        print(f"[ERROR] {e}")

    print()

print("\n=== Test autofill categories ===\n")

from src.gap_filler import AUTOFILL_CATEGORIES, NEVER_AUTOFILL

print(f"AUTOFILL_CATEGORIES: {AUTOFILL_CATEGORIES}")
print(f"NEVER_AUTOFILL: {NEVER_AUTOFILL}")
print()

if "RFI/RFP/RFQ" not in AUTOFILL_CATEGORIES:
    print("[SUCCESS] RFI/RFP/RFQ removed from AUTOFILL_CATEGORIES")
else:
    print("[FAILURE] RFI/RFP/RFQ still in AUTOFILL_CATEGORIES")

if "RFI/RFP/RFQ" in NEVER_AUTOFILL:
    print("[SUCCESS] RFI/RFP/RFQ added to NEVER_AUTOFILL")
else:
    print("[INFO] RFI/RFP/RFQ not in NEVER_AUTOFILL (optional)")
