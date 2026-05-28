#!/usr/bin/env python3
"""
SCA Time Automation - Main CLI entry point

Commands:
  export              Reminder to run VBA export script
  preview             Generate Excel preview with time entries
  preview --no-ai     Generate preview without AI (YAML-based only, faster)
  preview --weeks N   Filter to last N weeks (default: from config)
  upload WEEK         Upload specific week (e.g., "2025-12-07")
  upload --latest     Upload most recent week from preview
  upload --all        Upload all weeks from preview
  upload --force      Upload even if week already exists in SharePoint
  status              Show weeks in preview and their upload status
  report              Generate manager report (Weekly Hours + Opportunities)
  report --weeks N    Report for last N weeks (default: from config)
  catchup             Auto-detect missing weeks, generate preview
  catchup --dry-run   Show missing weeks without generating Excel
  catchup --max-weeks N  Limit lookback range
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.excel_preview import generate_final_preview
from src.sharepoint import get_access_token, get_uploaded_weeks, post_week_entries, post_all_weeks

import pandas as pd


def _run_vbs_export(vbs_path: Path, weeks: int) -> bool:
    """Run VBS calendar export script with retry and fallback prompts.

    Returns True if the export succeeded, False if the user chose to continue
    with existing calendar_export.json.  Calls sys.exit(1) if the user declines
    to continue.
    """
    def _attempt() -> bool:
        try:
            result = subprocess.run(
                ["cscript", "//Nologo", str(vbs_path), str(weeks)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0
        except Exception:
            return False

    if _attempt():
        return True

    print("VBS export failed — is Outlook running?")
    if input("Retry? [y/N] ").strip().lower() == "y" and _attempt():
        return True

    if input("Continue with existing calendar_export.json? [y/N] ").strip().lower() != "y":
        sys.exit(1)
    return False


def _check_excel_writable(path: Path) -> None:
    """Fail fast if Excel output file is locked by another process (e.g., Excel is open).

    Call this before any expensive pipeline work so the user isn't waiting 20+ minutes
    only to hit a PermissionError at the write step.
    """
    p = Path(path)
    if not p.exists():
        return
    try:
        p.open("r+b").close()
    except PermissionError:
        print("Error: Cannot write Excel — close the file first and retry.")
        print(f"  File: {p}")
        sys.exit(1)


def cmd_export(run: bool = False, weeks: int = 4):
    """Export calendar from Outlook. With --run, executes VBS script directly."""
    if run:
        vbs_path = Path(__file__).parent / "calendar_export.vbs"
        if not vbs_path.exists():
            print(f"Error: VBS script not found: {vbs_path}")
            sys.exit(1)

        print(f"Running calendar export ({weeks} weeks back)...")
        print()
        _run_vbs_export(vbs_path, weeks)
        print()
        print("Next: python scripts/run.py preview")
    else:
        print("=" * 60)
        print("STEP 1: Export Calendar from Outlook")
        print("=" * 60)
        print()
        print("Option A (recommended):")
        print(f"  python scripts/run.py export --run --weeks {weeks}")
        print()
        print("Option B (manual):")
        print(f"  cscript //Nologo scripts/calendar_export.vbs {weeks}")
        print()
        print("Then run: python scripts/run.py preview")
        print()


def cmd_preview(use_ai: bool = True, weeks_back: int | None = None):
    """Generate Excel preview with time entries."""
    t0 = time.time()
    settings = get_settings()

    # Use default from config if not specified
    if weeks_back is None:
        weeks_back = settings.get("report", {}).get("weeks_back", 12)

    # Fail fast before running pipeline if Excel is open/locked
    output_path = settings["paths"]["excel_preview"]
    _check_excel_writable(Path(output_path))

    # Check AI configuration
    ai_enabled = settings["ai"]["enabled"] and use_ai
    mode = "AI-enabled" if ai_enabled else "YAML-only"

    print(f"Generating preview ({mode}, last {weeks_back} weeks)...")
    print()

    df = generate_final_preview(output_path, fill=True, weeks_back=weeks_back, verbose=True)

    # Count entries (excluding summary rows)
    entry_count = len(df[df["category"] != ">>> WEEK TOTAL"])
    week_count = df[df["category"] != ">>> WEEK TOTAL"]["week_beginning"].nunique()

    print()
    print(f"Generated {entry_count} entries across {week_count} weeks")
    print(f"Preview saved: {output_path}")
    print()

    print("Opening preview...")
    try:
        os.startfile(str(output_path))
    except (AttributeError, OSError):
        try:
            subprocess.Popen(["xdg-open", str(output_path)])
        except FileNotFoundError:
            pass

    print(f"Done in {int(time.time() - t0)}s")
    print()
    print("Next: python scripts/run.py upload --all")
    print()



def cmd_upload(week: str = None, latest: bool = False, all_weeks: bool = False, force: bool = False):
    """Upload time entries to SharePoint.

    Args:
        week: Specific week to upload (e.g., "2025-12-07")
        latest: Upload only the most recent week
        all_weeks: Upload all weeks from preview
        force: Upload even if week already exists in SharePoint
    """
    settings = get_settings()
    preview_path = settings["paths"]["excel_preview"]

    if not Path(preview_path).exists():
        print(f"Error: Preview file not found: {preview_path}")
        print("Run 'python scripts/run.py preview' first")
        sys.exit(1)

    # Load preview Excel
    df = pd.read_excel(preview_path)

    # Get unique weeks (excluding summary rows)
    weeks = df[df["category"] != ">>> WEEK TOTAL"]["week_beginning"].unique()
    weeks = sorted([w for w in weeks if pd.notna(w)])

    if len(weeks) == 0:
        print("No weeks found in preview")
        sys.exit(1)

    # Upload all weeks
    if all_weeks:
        print(f"Uploading all {len(weeks)} weeks from preview...")
        result = post_all_weeks(df, force=force)

        print()
        print(f"Upload complete: {result['totals']['success']} successful, {result['totals']['failed']} failed")

        if result['totals']['failed'] > 0:
            print("\nFailed entries by week:")
            for week_key, week_results in result['by_week'].items():
                failed_in_week = [r for r in week_results if not r['success']]
                if failed_in_week:
                    print(f"  [{week_key}]")
                    for r in failed_in_week:
                        print(f"    - {r['category']}: {r.get('error', 'Unknown error')}")
            sys.exit(1)
        return

    # Determine which single week to upload
    if latest:
        target_week = weeks[-1]
        print(f"Uploading latest week: {target_week}")
    elif week:
        if week not in weeks:
            print(f"Error: Week '{week}' not found in preview")
            print(f"Available weeks: {', '.join(weeks)}")
            sys.exit(1)
        target_week = week
        print(f"Uploading week: {target_week}")
    else:
        print("Error: Specify --all, --latest, or provide a week date")
        sys.exit(1)

    # Upload single week
    print()
    results = post_week_entries(df, target_week, force=force)

    # Summary
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful

    print()
    print(f"Upload complete: {successful} successful, {failed} failed")

    if failed > 0:
        print("\nFailed entries:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['category']}: {r.get('error', 'Unknown error')}")
        sys.exit(1)


def cmd_report(weeks_back: int | None = None):
    """Generate manager report (Weekly Hours + Opportunities)."""
    from scripts.manager_report import generate_manager_report
    generate_manager_report(weeks_back=weeks_back)


def cmd_status():
    """Show weeks in preview and their upload status."""
    settings = get_settings()
    preview_path = settings["paths"]["excel_preview"]

    if not Path(preview_path).exists():
        print(f"Preview file not found: {preview_path}")
        print("Run 'python scripts/run.py preview' first")
        return

    # Load preview Excel
    df = pd.read_excel(preview_path)

    # Get weeks and summaries
    weeks_data = []
    for week in df["week_beginning"].unique():
        if pd.isna(week):
            continue

        week_df = df[df["week_beginning"] == week]
        total_row = week_df[week_df["category"] == ">>> WEEK TOTAL"]

        if len(total_row) > 0:
            total_hours = total_row.iloc[0]["hours"]
        else:
            total_hours = week_df[week_df["category"] != ">>> WEEK TOTAL"]["hours"].sum()

        weeks_data.append({
            "week": week,
            "hours": total_hours,
            "entries": len(week_df[week_df["category"] != ">>> WEEK TOTAL"])
        })

    # Sort by week
    weeks_data = sorted(weeks_data, key=lambda x: x["week"])

    print()
    print("=" * 60)
    print("WEEKS IN PREVIEW")
    print("=" * 60)
    print()

    for w in weeks_data:
        status = "✓ Ready" if w["hours"] >= 40 else f"⚠ {w['hours']}h (target: 40h)"
        print(f"{w['week']:>12} | {w['entries']:>2} entries | {w['hours']:>5.1f}h | {status}")

    print()
    print(f"Total weeks: {len(weeks_data)}")
    print()


def cmd_catchup(use_ai: bool = True, dry_run: bool = False, max_weeks: int | None = None):
    """Auto-detect missing weeks and generate preview for them.

    Queries SharePoint for uploaded weeks, calculates which weeks are missing
    up to last Sunday, runs the full pipeline, and opens the Excel preview.
    """
    from src.date_utils import last_sunday, sundays_between, weeks_back_to_cover
    from src.excel_writer import write_excel_with_formatting

    t0 = time.time()
    settings = get_settings()
    if max_weeks is None:
        max_weeks = settings.get("report", {}).get("weeks_back", 12)

    # Step 1: authenticate early — fail fast before any heavy work
    print("Checking SharePoint connection...")
    token = get_access_token()

    # Step 2: query SharePoint for already-uploaded weeks
    uploaded = get_uploaded_weeks(token)
    end_sunday = last_sunday()

    if uploaded:
        last_uploaded = max(uploaded)
        print(f"Last uploaded week: {last_uploaded}")
    else:
        # No uploads found — fall back to max_weeks lookback
        print(
            f"No uploaded weeks found in SharePoint. "
            f"Using last {max_weeks} weeks as range."
        )
        last_uploaded = last_sunday(
            date.fromordinal(end_sunday.toordinal() - max_weeks * 7)
        )

    # Step 3: calculate missing weeks
    missing = sundays_between(last_uploaded, end_sunday)

    if not missing:
        print(f"All caught up! All weeks up to {end_sunday} are already uploaded.")
        return

    first_missing = missing[0]
    last_missing = missing[-1]
    print(f"Missing {len(missing)} week(s): {first_missing} -> {last_missing}")

    if dry_run:
        print()
        print("Weeks that would be generated:")
        for w in missing:
            status = "(already uploaded)" if w in uploaded else "(missing)"
            print(f"  {w}  {status}")
        return

    # Fail fast before pipeline if Excel is open/locked
    output_path = Path(settings["paths"]["excel_preview"])
    _check_excel_writable(output_path)

    # Step 4: run full pipeline with enough weeks to cover range
    weeks_back = weeks_back_to_cover(first_missing)

    # Auto-refresh calendar data before generating preview
    print(f"Exporting calendar ({weeks_back} weeks)...")
    vbs_path = Path(__file__).parent / "scripts" / "calendar_export.vbs"
    _run_vbs_export(vbs_path, weeks_back)

    ai_mode = "AI-enabled" if use_ai else "YAML-only"
    print(f"Running pipeline ({ai_mode}, {weeks_back} weeks back)...")
    print()

    output_path = Path(settings["paths"]["excel_preview"])
    df = generate_final_preview(
        output_path=None, fill=True, weeks_back=weeks_back, verbose=True
    )

    # Step 5: filter DataFrame to only missing weeks
    missing_strings = {w.isoformat() for w in missing}
    is_data_row = df["category"] != ">>> WEEK TOTAL"
    in_missing = df["week_beginning"].isin(missing_strings)
    filtered_df = df[in_missing | (~is_data_row & in_missing)].copy()

    # include WEEK TOTAL rows for missing weeks
    is_total = df["category"] == ">>> WEEK TOTAL"
    filtered_df = df[in_missing | (is_total & df["week_beginning"].isin(missing_strings))].copy()

    if filtered_df.empty:
        print(
            "No calendar events found for the missing weeks. "
            "Run 'python scripts/run.py export --run' to refresh calendar data."
        )
        return

    # Step 6: write filtered Excel
    print("Writing Excel...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_excel_with_formatting(filtered_df, output_path)
    except PermissionError:
        print("Error: Cannot write Excel — close the file first and retry.")
        print(f"  File: {output_path}")
        sys.exit(1)

    # Step 7: open file
    print("Opening preview...")
    try:
        os.startfile(str(output_path))
    except (AttributeError, OSError):
        try:
            subprocess.Popen(["xdg-open", str(output_path)])
        except FileNotFoundError:
            pass  # not on Linux either — user can open manually

    entry_count = len(filtered_df[filtered_df["category"] != ">>> WEEK TOTAL"])
    print()
    print(f"Generated {len(missing)} week(s): {first_missing} -> {last_missing}")
    print(f"{entry_count} entries written to: {output_path}")
    print(f"Done in {int(time.time() - t0)}s")
    print()
    print("Next: python scripts/run.py upload --all")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="SCA Time Automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # export command
    export_parser = subparsers.add_parser("export", help="Export calendar from Outlook")
    export_parser.add_argument("--run", action="store_true", help="Run VBS export script directly")
    export_parser.add_argument("--weeks", type=int, default=4, help="Number of weeks back to export (default: 4)")

    # preview command
    preview_parser = subparsers.add_parser("preview", help="Generate Excel preview")
    preview_parser.add_argument("--no-ai", action="store_true", help="Disable AI (faster, YAML-based only)")
    preview_parser.add_argument("--weeks", type=int, default=None, help="Number of weeks back to include (default: from config)")

    # upload command
    upload_parser = subparsers.add_parser("upload", help="Upload time entries to SharePoint")
    upload_parser.add_argument("week", nargs="?", help="Week to upload (YYYY-MM-DD)")
    upload_parser.add_argument("--latest", action="store_true", help="Upload most recent week")
    upload_parser.add_argument("--all", action="store_true", help="Upload all weeks from preview")
    upload_parser.add_argument("--force", action="store_true", help="Upload even if week already exists in SharePoint")

    # status command
    subparsers.add_parser("status", help="Show weeks in preview")

    # report command
    report_parser = subparsers.add_parser("report", help="Generate manager report (Weekly Hours + Opportunities)")
    report_parser.add_argument("--weeks", type=int, default=None, help="Number of weeks back to include (default: from config)")

    # catchup command
    catchup_parser = subparsers.add_parser("catchup", help="Auto-detect missing weeks and generate preview")
    catchup_parser.add_argument("--no-ai", action="store_true", help="Disable AI (faster, YAML-based only)")
    catchup_parser.add_argument("--dry-run", action="store_true", help="Show missing weeks without generating Excel")
    catchup_parser.add_argument("--max-weeks", type=int, default=None, help="Max weeks back to look when no uploads found (default: from config)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "export":
            cmd_export(run=args.run, weeks=args.weeks)
        elif args.command == "preview":
            cmd_preview(use_ai=not args.no_ai, weeks_back=args.weeks)
        elif args.command == "upload":
            cmd_upload(week=args.week, latest=args.latest, all_weeks=getattr(args, 'all', False), force=args.force)
        elif args.command == "status":
            cmd_status()
        elif args.command == "report":
            cmd_report(weeks_back=args.weeks)
        elif args.command == "catchup":
            cmd_catchup(
                use_ai=not args.no_ai,
                dry_run=args.dry_run,
                max_weeks=args.max_weeks,
            )
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
