"""Tenrox payload builder for the in-page console uploader.

The Tenrox timesheet handler cannot be driven from standalone Python (the
ASPX pageKey is single-use; REST is dead under SSO federation - see
docs/audits/2026-07-05-tenrox-aspx-pivot.md). So this module does NOT post.
It transforms an approved preview DataFrame into a pure-JSON payload that the
static, reviewed-once console snippet (scripts/tenrox_console_uploader.js)
posts from inside the operator's live, authenticated timesheet tab.

Strict code/data split: this builder emits DATA only. Business rules come
from config/tenrox_mapping.yaml (SCA category -> assignment UIDs, note rules).

Binding facts (from the 2026-07-05 captures):
- RegularTime is in SECONDS (hours * 3600).
- EntryDate is MM-DD-YYYY; week StartDate/EndDate bound the Sun..Sat period.
- TimesheetUid is per-week and read LIVE by the uploader - never in the payload.

Guards:
- Time Off / non_working_time assignments are skipped (entered manually).
- Future-dated entries (date > run date) are held, never posted.
- Sales entries are held until the note-save mechanism is wired: posting a
  sales entry without its OPID note would violate compliance (section 4.1).
  Overhead hours-only posting is allowed now.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TypedDict

import pandas as pd

from src.config import load_yaml

WEEK_TOTAL_MARKER = ">>> WEEK TOTAL"


class TenroxEntry(TypedDict):
    date: str                    # YYYY-MM-DD
    entry_date: str              # MM-DD-YYYY (ASPX payload form)
    category: str                # SCA category (note label)
    assignment: str              # mapping key
    assignment_attribute_uid: int
    attribute_data: dict
    hours: float
    seconds: int
    opportunity_id: str
    note: str
    requires_opid: bool
    postable: bool
    hold_reason: str             # "" when postable


def _load_mapping() -> dict:
    return load_yaml("tenrox_mapping.yaml")


def _mmddyyyy(iso_date: str) -> str:
    return datetime.strptime(iso_date[:10], "%Y-%m-%d").strftime("%m-%d-%Y")


def _note(category: str, opportunity_id: str, comments: str, requires_opid: bool) -> str:
    """Assemble the timesheet note per section 4.1.

    Sales:    "Category","OPID","Comments"
    Overhead: "Category","Comments"
    Fields are quoted; embedded quotes are stripped to keep the CSV-ish form.
    """
    def q(value: str) -> str:
        return '"' + str(value).replace('"', "'").strip() + '"'

    if requires_opid:
        return ",".join([q(category), q(opportunity_id), q(comments)])
    return ",".join([q(category), q(comments)])


def build_week_payload(
    df: pd.DataFrame, week: str, run_date: date | None = None
) -> dict:
    """Build the console-uploader payload for a single week.

    df is the approved preview DataFrame (must carry a `date` column). week is
    the literal Sunday string (e.g. "2026-06-28"). run_date defaults to today
    and is used only for the future-date guard.
    """
    if run_date is None:
        run_date = date.today()
    mapping = _load_mapping()
    cat_map = mapping["category_map"]
    assignments = mapping["assignments"]
    ts = mapping["timesheet"]

    if "date" not in df.columns:
        raise ValueError("preview DataFrame is missing the 'date' column (run Step 4a pipeline)")

    week_start = datetime.strptime(week, "%Y-%m-%d").date()
    week_end = week_start + timedelta(days=6)

    rows = df[(df["week_beginning"] == week) & (df["category"] != WEEK_TOTAL_MARKER)].copy()

    # Group per section 4.1: one note per (date, category, opportunity_id) per day.
    grouped: dict[tuple[str, str, str], dict] = {}
    skipped: list[dict] = []

    for _, row in rows.iterrows():
        category = str(row["category"])
        cfg = cat_map.get(category)
        opid = str(row.get("opportunity_id", "") or "")
        row_date = str(row.get("date", "") or "")
        hours = float(row.get("hours", 0) or 0)
        comment = str(row.get("comments", "") or "")

        if cfg is None:
            skipped.append({"category": category, "date": row_date, "hours": hours,
                            "reason": "no Tenrox mapping for this category"})
            continue
        if cfg.get("skip"):
            skipped.append({"category": category, "date": row_date, "hours": hours,
                            "reason": "non_working_time - enter manually in the UI"})
            continue
        if hours <= 0:
            continue

        key = (row_date, category, opid)
        if key not in grouped:
            grouped[key] = {"hours": 0.0, "comments": [], "cfg": cfg}
        grouped[key]["hours"] += hours
        if comment:
            grouped[key]["comments"].append(comment)

    entries: list[TenroxEntry] = []
    for (row_date, category, opid), g in sorted(grouped.items()):
        cfg = g["cfg"]
        assignment_key = cfg["assignment"]
        assn = assignments[assignment_key]
        requires_opid = bool(cfg.get("requires_opid"))
        # Preserve the pipeline's precision. Real entries are already on the
        # 0.5h grid; Tenrox itself supports 15-min (0.25h) increments, so do
        # NOT re-round here (it would zero a legitimate 0.25h entry).
        hours = round(g["hours"], 2)
        comments = "; ".join(dict.fromkeys(g["comments"])) or category

        postable, hold = True, ""
        # Future-date guard (never enter time dated after the run date).
        if row_date and datetime.strptime(row_date, "%Y-%m-%d").date() > run_date:
            postable, hold = False, "future-dated relative to run date"
        elif requires_opid and not opid:
            postable, hold = False, "sales entry missing opportunity_id"
        elif requires_opid:
            # Sales entries need a working OPID note; the note-save mechanism is
            # not yet wired, so hold them (overhead hours-only posting is fine).
            # When notes land, this branch flips to postable.
            postable, hold = False, "sales entry requires the note mechanism (not yet wired)"

        entries.append(TenroxEntry(
            date=row_date,
            entry_date=_mmddyyyy(row_date) if row_date else "",
            category=category,
            assignment=assignment_key,
            assignment_attribute_uid=int(assn["assignment_attribute_uid"]),
            attribute_data=dict(assn["attribute_data"]),
            hours=hours,
            seconds=int(round(hours * 3600)),
            opportunity_id=opid,
            note=_note(category, opid, comments, requires_opid),
            requires_opid=requires_opid,
            postable=postable,
            hold_reason=hold,
        ))

    postable_entries = [e for e in entries if e["postable"]]
    held_entries = [e for e in entries if not e["postable"]]

    return {
        "week_beginning": week,
        "start_date": week_start.strftime("%m-%d-%Y"),
        "end_date": week_end.strftime("%m-%d-%Y"),
        "timesheet": {
            "user_unique_id": int(ts["user_unique_id"]),
            "template_uid": int(ts["template_uid"]),
        },
        "entries": entries,
        "summary": {
            "postable_count": len(postable_entries),
            "held_count": len(held_entries),
            "skipped_count": len(skipped),
            "postable_hours": round(sum(e["hours"] for e in postable_entries), 2),
            "held_hours": round(sum(e["hours"] for e in held_entries), 2),
        },
        "skipped": skipped,
    }
