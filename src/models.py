"""
Data structures for SCA Time Automation.
Using TypedDict for type hints while keeping dict flexibility.
"""

from typing import TypedDict


class CalendarEvent(TypedDict):
    """Event from Outlook calendar export."""

    title: str
    start: str
    end: str
    category: str
    minutes: int
    associate: str
    recipients: int
    all_day: bool


class ProjectCode(TypedDict):
    """Project code from Excel input."""

    company: str
    description: str
    code: str  # OP-XXXXXXX


class TimeEntry(TypedDict):
    """Entry for SharePoint submission."""

    week_beginning: str  # YYYY-MM-DD (sunday)
    category: str
    hours: float
    opportunity_id: str
    account_name: str
    comments: str
    status: str  # NEW, MODIFIED, APPROVED
