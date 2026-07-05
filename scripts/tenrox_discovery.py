#!/usr/bin/env python3
"""Tenrox auth/read probe harness (STOP-GATE 2 evidence; retained tool).

NOTE (2026-07-05): standalone-Python replay of this handler was proven
NON-VIABLE - the ASPX pageKey is single-use (consumed by the browser's own
AJAX call) and cannot be minted from Python. See
docs/audits/2026-07-05-tenrox-aspx-pivot.md. The live read + write now run in
an in-page console snippet (scripts/tenrox_console_uploader.js). This script
is kept as (a) the reproducible probe that established the evidence table and
(b) the REST/read client to revive if a non-federated API credential lands
(BACKLOG #8). It is not part of the normal run path.

The REST/OAuth API is unusable on this SSO-federated tenant (proven at
STOP-GATE 2, 2026-07-05). The working surface is the UI's async postback:

  POST /TEnterprise/Entry/TimeEntry/MyTimesheet.aspx?r=<rand>&pageKey=<key>
  body: pageMethod=GetTimesheetDetails&IsTenroxAsyncCallback=true
        &usercontrolid=&requestData=<url-encoded JSON>

Auth is the browser cookie (TENROX_COOKIE) + OrgName header. The embedded
tenant.token JWT expires ~1h after issue; a 401 / login-HTML response means
the cookie is stale - STOP and ask for a fresh paste (no retry loop).

Replaying this read for a given week IS discovery: it yields that week's
TimesheetUid, the assignment rows (task UIDs), existing entries (for
idempotency) and the Open/Submitted status. Output JSON lands in the
gitignored data/discovery/ directory. Secrets are never printed.

Usage:
  python scripts/tenrox_discovery.py                     # current + target week
  python scripts/tenrox_discovery.py 2026-06-28          # one specific week
"""

import json
import random
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_env, get_project_root, load_yaml

TIMEOUT = 30
HOST_DEFAULT = "jda.tenrox.net"
TARGET_WEEK = "2026-06-28"  # mission-pinned; never derived from "today"

# Work types that must have an assignment row for the loader to function
# (Leave Time is reported but excluded - the loader skips Time Off).
REQUIRED_WORK_TYPES = [
    "Sales Activities",
    "Administration",
    "Internal Project Support",
    "Learning and Development",
    "Travel Administration",
]


def base_url() -> str:
    host = get_env("TENROX_HOST", HOST_DEFAULT)
    return f"https://{host}/TEnterprise"


def timesheet_headers() -> dict:
    cookie = get_env("TENROX_COOKIE", "")
    if not cookie:
        print("ERROR: TENROX_COOKIE is not set. Run: keys set TENROX_COOKIE \"<cookie>\"")
        sys.exit(2)
    return {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "csrftoken": "0",
        "origin": f"https://{get_env('TENROX_HOST', HOST_DEFAULT)}",
        "referer": f"https://{get_env('TENROX_HOST', HOST_DEFAULT)}/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
        ),
        "Cookie": cookie,
        "OrgName": get_env("TENROX_ORG", "JDASoftware"),
    }


def user_unique_id() -> int:
    mapping = load_yaml("tenrox_mapping.yaml")
    return int(mapping["timesheet"]["user_unique_id"])


def discovery_dir() -> Path:
    d = get_project_root() / "data" / "discovery"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _looks_like_auth_failure(resp: requests.Response) -> str | None:
    if resp.status_code in (301, 302, 303, 307, 308):
        return f"redirect to {resp.headers.get('Location', '?')} (login redirect = cookie expired)"
    if resp.status_code in (401, 403):
        return f"HTTP {resp.status_code} (cookie invalid/expired)"
    ctype = resp.headers.get("Content-Type", "")
    if "text/html" in ctype and ("login" in resp.text[:2000].lower() or "signin" in resp.text[:2000].lower()):
        return "HTML login page (cookie expired)"
    return None


def get_timesheet_details(week_sunday: str) -> dict | None:
    """Replay GetTimesheetDetails for the week containing week_sunday (YYYY-MM-DD)."""
    request_data = {
        "date": week_sunday,
        "userUniqueId": user_unique_id(),
        "roleObjectType": 26,
        "roleObjectUniqueId": -1,
        "comingFrom": "MYTIMESHEET",
        "hasPrevious": False,
        "hasNext": False,
        "pinnedAssignmentAttributeIds": [],
    }
    params = {
        "r": str(random.random()),  # noqa: S311 - cache-buster, not security
        "pageKey": get_env("TENROX_PAGEKEY", "688c34fa97cee8ed96090d212b1bd730"),
    }
    body = {
        "pageMethod": "GetTimesheetDetails",
        "IsTenroxAsyncCallback": "true",
        "usercontrolid": "",
        "requestData": json.dumps(request_data),
    }
    try:
        resp = requests.post(
            f"{base_url()}/Entry/TimeEntry/MyTimesheet.aspx",
            headers=timesheet_headers(),
            params=params,
            data=body,
            timeout=TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        print(f"ERROR: request failed for {week_sunday}: {exc}")
        return None

    reason = _looks_like_auth_failure(resp)
    if reason:
        print(f"STOP: cookie auth failed on GetTimesheetDetails ({week_sunday})")
        print(f"  status: {resp.status_code}  reason: {reason}")
        print("Ask the operator for a fresh TENROX_COOKIE paste (JWT expires ~1h).")
        sys.exit(2)

    try:
        data = resp.json()
    except ValueError:
        print(f"ERROR: non-JSON response for {week_sunday} (status {resp.status_code})")
        print(f"  first 300 chars: {resp.text[:300]}")
        return None

    if not isinstance(data, dict) or "main" not in data:
        print(f"ERROR: unexpected response shape for {week_sunday}: keys={list(data)[:10] if isinstance(data, dict) else type(data).__name__}")
        return None
    return data


def analyze(data: dict, week_sunday: str) -> None:
    main = data.get("main", {})
    print(f"  timesheetId: {main.get('timesheetId')}  template: {main.get('templateName')}")
    print(f"  period: {main.get('periodSD', '?')[:10]} -> {main.get('periodED', '?')[:10]}")
    state = data.get("currentState", {})
    props = state.get("Properties", {})
    print(f"  status: {state.get('ActivityName')}  isSubmitted={main.get('isSubmitted')}  isClosed={main.get('isClosed')}  readonly={props.get('ISREADONLY')}")

    assignments = data.get("assignments", [])
    present = {a.get("WORKTYPE_NAME") for a in assignments}
    print(f"  assignment rows: {len(assignments)}")
    for a in assignments:
        print(
            f"    - {a.get('WORKTYPE_NAME'):<28} assignAttrUid={a.get('ASSNATRIBUID')}"
            f" taskUid={a.get('TASK_UID')} project={a.get('PROJECT_NAME')!r}"
        )
    missing = [wt for wt in REQUIRED_WORK_TYPES if wt not in present]
    if missing:
        print(f"  STOP-GATE 3: missing assignment rows for: {missing}")
        print("  -> ask operator to add one manual UI entry per missing work type, then re-run.")
    else:
        print("  STOP-GATE 3: clear - all required work types have assignment rows.")

    entries = data.get("timeEntries")
    print(f"  existing timeEntries: {0 if entries in (None, []) else len(entries)}")


def main() -> int:
    weeks = sys.argv[1:] or [
        # current week is resolved server-side from the pinned target's neighbours;
        # we always want the mission target plus whatever week the operator is on.
        TARGET_WEEK,
    ]
    out_dir = discovery_dir()
    print(f"Tenrox discovery against {base_url()} (org: {get_env('TENROX_ORG', 'JDASoftware')})")
    print()

    rc = 0
    for week in weeks:
        print(f"[week {week}]")
        data = get_timesheet_details(week)
        if data is None:
            rc = 1
            print()
            continue
        out_path = out_dir / f"tenrox_timesheet_{week}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        analyze(data, week)
        print(f"  saved -> {out_path.relative_to(get_project_root())}")
        print()

    print("Discovery complete. Files in data/discovery/ (gitignored).")
    return rc


if __name__ == "__main__":
    sys.exit(main())
