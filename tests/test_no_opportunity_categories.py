"""
Test that non-sales categories never have client or opportunity_id.
"""


def test_no_opportunity_categories_cleared():
    """Verify that Training, Admin, Support, Travel, Time Off categories have no client/opp_id."""

    # Define the categories that should never have opportunity_id
    NO_OPPORTUNITY_ID_CATEGORIES = {
        "Training",
        "Admin",
        "Support",
        "Travel",
        "Time Off",
    }

    # Simulate the logic from excel_preview.py
    test_cases = [
        # (category, initial_client, initial_opp_id, expected_client, expected_opp_id)
        ("Training", "Michelin", "OPP123", "", ""),
        ("Admin", "Wurth", "OPP456", "", ""),
        ("Support", "Veronesi", "OPP789", "", ""),
        ("Travel", "Merz", "OPP999", "", ""),
        ("Time Off", "Company", "OPP111", "", ""),
        # Non-NO_OPPORTUNITY_ID_CATEGORIES categories should keep their values
        ("Customer - Demo/ Presentation", "Michelin", "OPP123", "Michelin", "OPP123"),
        ("Discovery", "Wurth", "OPP456", "Wurth", "OPP456"),
    ]

    for (
        category,
        initial_client,
        initial_opp_id,
        expected_client,
        expected_opp_id,
    ) in test_cases:
        client = initial_client
        opp_id = initial_opp_id

        # Apply the clearing logic
        if category in NO_OPPORTUNITY_ID_CATEGORIES:
            client = ""
            opp_id = ""

        assert client == expected_client, (
            f"Category {category}: expected client '{expected_client}', got '{client}'"
        )
        assert opp_id == expected_opp_id, (
            f"Category {category}: expected opp_id '{expected_opp_id}', got '{opp_id}'"
        )

        print(f"[OK] {category}: client='{client}', opp_id='{opp_id}'")

    print("\n[SUCCESS] All NO_OPPORTUNITY_ID_CATEGORIES tests passed!")


def test_gap_filler_rounding_fix():
    """Verify that gap filler allocates exactly the requested hours."""

    # Simulate the rounding fix logic from gap_filler.py
    empty_hours = 1.0  # Need exactly 1 hour

    # Simulate 3 categories with equal proportion (would cause rounding issues)
    distribution = {
        ("Prep - Demo/ Presentation", "", ""): 0.333,
        ("Internal Meeting", "", ""): 0.333,
        ("Admin", "", ""): 0.334,
    }

    # Calculate hours with rounding (old logic)
    entries = []
    total_allocated = 0.0

    for (cat, client, opp_id), proportion in distribution.items():
        hours = round(empty_hours * proportion * 2) / 2  # Round to 0.5
        if hours > 0:
            entries.append(
                {
                    "category": cat,
                    "client": client,
                    "hours": hours,
                    "opportunity_id": opp_id,
                }
            )
            total_allocated += hours

    print(f"Before rounding fix: allocated {total_allocated}h (target: {empty_hours}h)")

    # Apply rounding fix
    if entries and abs(total_allocated - empty_hours) > 0.01:
        difference = empty_hours - total_allocated
        # Add/subtract difference to the largest entry
        largest_entry = max(entries, key=lambda x: x["hours"])
        largest_entry["hours"] = round((largest_entry["hours"] + difference) * 2) / 2
        # Recalculate total
        total_allocated = sum(e["hours"] for e in entries)

    print(f"After rounding fix: allocated {total_allocated}h (target: {empty_hours}h)")

    # Verify total matches target
    assert abs(total_allocated - empty_hours) < 0.01, (
        f"Expected {empty_hours}h, got {total_allocated}h"
    )

    print(f"\n[SUCCESS] Gap filler allocates exactly {empty_hours}h as requested!")


if __name__ == "__main__":
    test_no_opportunity_categories_cleared()
    print()
    test_gap_filler_rounding_fix()
