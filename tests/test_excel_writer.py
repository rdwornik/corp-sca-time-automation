"""Tests for Excel SUM formula generation in write_excel_with_formatting."""

import pytest
import pandas as pd


def _make_df_single_week() -> pd.DataFrame:
    """Single week with 2 data rows + 1 WEEK TOTAL row."""
    return pd.DataFrame([
        {"week_beginning": "2025-03-23", "category": "Admin", "hours": 8.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
        {"week_beginning": "2025-03-23", "category": "Internal Meeting", "hours": 4.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
        {"week_beginning": "2025-03-23", "category": ">>> WEEK TOTAL", "hours": 12.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
    ])


def _make_df_single_entry_week() -> pd.DataFrame:
    """Single week with only 1 data row + WEEK TOTAL."""
    return pd.DataFrame([
        {"week_beginning": "2025-03-23", "category": "Admin", "hours": 8.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
        {"week_beginning": "2025-03-23", "category": ">>> WEEK TOTAL", "hours": 8.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
    ])


def _make_df_two_weeks() -> pd.DataFrame:
    """Two weeks with different sizes to verify independent formula ranges."""
    return pd.DataFrame([
        {"week_beginning": "2025-03-23", "category": "Admin", "hours": 8.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
        {"week_beginning": "2025-03-23", "category": "Internal Meeting", "hours": 4.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
        {"week_beginning": "2025-03-23", "category": ">>> WEEK TOTAL", "hours": 12.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
        {"week_beginning": "2025-03-30", "category": "Discovery", "hours": 6.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
        {"week_beginning": "2025-03-30", "category": ">>> WEEK TOTAL", "hours": 6.0, "is_autofilled": False, "comments": None, "opportunity_id": None, "client": None},
    ])


def _get_hours_col_letter(ws) -> str:
    """Return the column letter for the 'hours' column."""
    from openpyxl.utils import get_column_letter
    for cell in ws[1]:
        if cell.value == "hours":
            return get_column_letter(cell.column)
    raise ValueError("hours column not found")


class TestWeekTotalSumFormula:
    def test_week_total_hours_is_formula(self, tmp_path):
        """WEEK TOTAL Hours cell must contain a =SUM formula, not a static float."""
        pytest.skip("not implemented yet")

    def test_week_total_formula_references_correct_rows(self, tmp_path):
        """SUM range must span exactly the data rows for that week (not TOTAL row itself)."""
        pytest.skip("not implemented yet")

    def test_single_row_week_total_formula(self, tmp_path):
        """Single data row week: formula should be =SUM(Dn:Dn) (same start and end row)."""
        pytest.skip("not implemented yet")

    def test_multiple_weeks_have_independent_formulas(self, tmp_path):
        """Each week's TOTAL formula must reference only its own data rows, not other weeks."""
        pytest.skip("not implemented yet")
