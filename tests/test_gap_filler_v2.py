"""Tests for gap filler v2: weighted-blend algorithm with historical profile."""

import pandas as pd
from unittest.mock import patch

from src.gap_filler import (
    AUTOFILL_CATEGORIES,
    NEVER_AUTOFILL,
    allocate_gap_hours,
    build_historical_profile,
)
from src.gemini_client import ask_gemini_allocation


def _make_df(weeks: list[dict]) -> pd.DataFrame:
    """Build a minimal DataFrame for gap filler tests.

    Each dict in weeks: {week: str, category: str, hours: float, is_autofilled: bool}
    """
    rows = []
    for w in weeks:
        rows.append({
            "week_beginning": w["week"],
            "category": w["category"],
            "hours": float(w["hours"]),
            "is_autofilled": w.get("is_autofilled", False),
            "client": w.get("client", ""),
            "opportunity_id": w.get("opp_id", ""),
        })
    return pd.DataFrame(rows)


class TestWeeklyProfile:
    """Tests for build_historical_profile()."""

    def test_empty_history_returns_empty_profile(self):
        """No prior weeks → empty historical profile (triggers Gemini fallback)."""
        df = _make_df([
            {"week": "2025-03-23", "category": "Admin", "hours": 8},
        ])
        result = build_historical_profile(df, current_week="2025-03-23", window_size=4)
        assert result == {}

    def test_builds_profile_from_last_n_weeks(self):
        """Profile uses exactly history_window weeks, not all available data."""
        # 5 prior weeks; window=2 → only the 2 most recent should count
        df = _make_df([
            {"week": "2025-02-09", "category": "Admin", "hours": 8},
            {"week": "2025-02-16", "category": "Admin", "hours": 8},
            {"week": "2025-02-23", "category": "Admin", "hours": 8},
            {"week": "2025-03-02", "category": "Internal Meeting", "hours": 4},
            {"week": "2025-03-09", "category": "Training", "hours": 4},
            # current week (excluded)
            {"week": "2025-03-16", "category": "Admin", "hours": 8},
        ])
        # window=2 → only 2025-03-09 and 2025-03-02 should contribute
        result = build_historical_profile(df, current_week="2025-03-16", window_size=2)
        keys = {k[0] for k in result}
        assert "Internal Meeting" in keys or "Training" in keys
        assert "Admin" not in keys  # Admin only in older weeks outside the window

    def test_never_autofill_categories_excluded_from_profile(self):
        """NEVER_AUTOFILL categories must not appear in historical profile."""
        never_cat = next(iter(NEVER_AUTOFILL))
        df = _make_df([
            {"week": "2025-03-09", "category": never_cat, "hours": 8},
            {"week": "2025-03-09", "category": "Admin", "hours": 4},
        ])
        result = build_historical_profile(df, current_week="2025-03-16", window_size=4)
        profile_cats = {k[0] for k in result}
        assert never_cat not in profile_cats
        assert "Admin" in profile_cats

    def test_profile_proportions_sum_to_one(self):
        """Returned proportions must sum to 1.0 (within float tolerance)."""
        df = _make_df([
            {"week": "2025-03-09", "category": "Admin", "hours": 6},
            {"week": "2025-03-09", "category": "Internal Meeting", "hours": 2},
            {"week": "2025-03-09", "category": "Training", "hours": 4},
        ])
        result = build_historical_profile(df, current_week="2025-03-16", window_size=4)
        assert result, "Expected non-empty profile"
        assert abs(sum(result.values()) - 1.0) < 1e-9

    def test_skips_current_week_in_history(self):
        """The current week being filled must not be included in historical window."""
        df = _make_df([
            # Only the current week is present — no prior history
            {"week": "2025-03-16", "category": "Admin", "hours": 8},
        ])
        result = build_historical_profile(df, current_week="2025-03-16", window_size=4)
        assert result == {}


class TestWeightedBlend:
    """Tests for allocate_gap_hours()."""

    def test_equal_weight_blends_evenly(self):
        """50/50 blend of equal-proportion profiles gives the same proportions."""
        cat_a = ("Admin", "", "")
        cat_b = ("Internal Meeting", "", "")
        # Both profiles: 50% Admin, 50% Internal Meeting → blend unchanged
        cur = {cat_a: 0.5, cat_b: 0.5}
        hist = {cat_a: 0.5, cat_b: 0.5}
        result = allocate_gap_hours(8.0, cur, hist, current_weight=0.5)
        assert result[cat_a] == result[cat_b]

    def test_hours_rounded_to_half_hour(self):
        """All allocated hours must be multiples of 0.5."""
        cur = {("Admin", "", ""): 1.0}
        hist = {("Admin", "", ""): 1.0}
        result = allocate_gap_hours(7.0, cur, hist, current_weight=0.5)
        for hours in result.values():
            assert hours % 0.5 == 0.0, f"{hours} is not a multiple of 0.5"

    def test_total_allocated_equals_gap_hours(self):
        """Sum of allocations must equal gap_hours (within 0.5h rounding tolerance)."""
        cur = {
            ("Admin", "", ""): 0.6,
            ("Internal Meeting", "", ""): 0.4,
        }
        hist = {
            ("Admin", "", ""): 0.5,
            ("Training", "", ""): 0.5,
        }
        result = allocate_gap_hours(9.0, cur, hist, current_weight=0.5)
        total = sum(result.values())
        assert abs(total - 9.0) <= 0.5

    def test_never_autofill_not_in_output(self):
        """NEVER_AUTOFILL categories must not appear in allocation output."""
        never_cat = next(iter(NEVER_AUTOFILL))
        cur = {(never_cat, "", ""): 1.0}
        hist = {(never_cat, "", ""): 1.0}
        result = allocate_gap_hours(8.0, cur, hist, current_weight=0.5)
        output_cats = {k[0] for k in result}
        assert never_cat not in output_cats


class TestGeminiFallback:
    """Tests for Gemini fallback path in generate_autofill_entries()."""

    def test_gemini_fallback_called_when_no_history(self):
        """Empty historical profile triggers ask_gemini_allocation, not weighted blend."""
        from src.gap_filler import generate_autofill_entries

        df = _make_df([
            # Only a current week row — no prior history
            {"week": "2025-03-23", "category": "Admin", "hours": 8},
        ])

        gemini_called = []

        def fake_ask_gemini(gap_hours, week_date, available_categories, week_context):
            gemini_called.append(True)
            return {"Admin": gap_hours}

        with patch("src.gemini_client.ask_gemini_allocation", side_effect=fake_ask_gemini), \
             patch("src.gemini_client.generate_autofill_comment", return_value="test comment"):
            generate_autofill_entries([], df, "2025-03-23", empty_hours=4.0, use_ai=True)

        assert gemini_called, "ask_gemini_allocation was not called despite empty history"

    def test_gemini_allocation_respects_never_autofill(self):
        """Even when Gemini suggests a NEVER_AUTOFILL category, it must be filtered out."""
        never_cat = next(iter(NEVER_AUTOFILL))
        result = ask_gemini_allocation(
            gap_hours=4.0,
            week_date="2025-03-23",
            available_categories=list(AUTOFILL_CATEGORIES),
            week_context="some work",
        )
        # Direct call with mocked Gemini returning a NEVER_AUTOFILL category
        with patch("src.gemini_client.call_gemini", return_value=f'{{"{never_cat}": 4.0, "Admin": 0.0}}'):
            result = ask_gemini_allocation(
                gap_hours=4.0,
                week_date="2025-03-23",
                available_categories=list(AUTOFILL_CATEGORIES),
                week_context="some work",
            )
        assert never_cat not in result, f"{never_cat} should be filtered (not in available_categories)"
