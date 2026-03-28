"""Tests for gap filler v2: weighted-blend algorithm with historical profile."""

import pytest


class TestWeeklyProfile:
    """Tests for build_historical_profile()."""

    def test_empty_history_returns_empty_profile(self):
        """No prior weeks → empty historical profile (triggers Gemini fallback)."""
        pytest.skip("stub — implement after build_historical_profile exists")

    def test_builds_profile_from_last_n_weeks(self):
        """Profile uses exactly history_window weeks, not all available data."""
        pytest.skip("stub — implement after build_historical_profile exists")

    def test_never_autofill_categories_excluded_from_profile(self):
        """NEVER_AUTOFILL categories must not appear in historical profile."""
        pytest.skip("stub — implement after build_historical_profile exists")

    def test_profile_proportions_sum_to_one(self):
        """Returned proportions must sum to 1.0 (within float tolerance)."""
        pytest.skip("stub — implement after build_historical_profile exists")

    def test_skips_current_week_in_history(self):
        """The current week being filled must not be included in historical window."""
        pytest.skip("stub — implement after build_historical_profile exists")


class TestWeightedBlend:
    """Tests for allocate_gap_hours()."""

    def test_equal_weight_blends_evenly(self):
        """50/50 blend of two profiles gives equal-weight result."""
        pytest.skip("stub — implement after allocate_gap_hours exists")

    def test_hours_rounded_to_half_hour(self):
        """All allocated hours must be multiples of 0.5."""
        pytest.skip("stub — implement after allocate_gap_hours exists")

    def test_total_allocated_equals_gap_hours(self):
        """Sum of all allocations must equal gap_hours (within 0.5h rounding tolerance)."""
        pytest.skip("stub — implement after allocate_gap_hours exists")

    def test_never_autofill_not_in_output(self):
        """NEVER_AUTOFILL categories must not appear in allocation output."""
        pytest.skip("stub — implement after allocate_gap_hours exists")


class TestGeminiFallback:
    """Tests for Gemini fallback path in generate_autofill_entries()."""

    def test_gemini_fallback_called_when_no_history(self):
        """Empty historical profile triggers ask_gemini_allocation, not weighted blend."""
        pytest.skip("stub — implement after ask_gemini_allocation exists")

    def test_gemini_allocation_respects_never_autofill(self):
        """Even when Gemini suggests a NEVER_AUTOFILL category, it must be filtered out."""
        pytest.skip("stub — implement after ask_gemini_allocation exists")
