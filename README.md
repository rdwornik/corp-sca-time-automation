# SCA Time Automation

Automates weekly time entry submission to the SharePoint SCA Time Tracker from Outlook calendar exports. Built for Blue Yonder Pre-Sales Engineers to streamline the repetitive process of categorizing meetings, detecting clients, filling time gaps, and uploading entries — reducing a manual 30+ minute task to a quick review-and-submit workflow.

## Features

- **Calendar Export** — Standalone VBS script exports Outlook events with categories and external attendee domains
- **AI-Powered Client Detection** — Gemini AI matches meetings to clients from project codes (with keyword fallback)
- **Smart Category Mapping** — Outlook categories (.PREFIX) map to SharePoint categories automatically
- **Overlap Resolution** — Priority-based: customer-facing activities always win overlapping slots
- **Intelligent Gap Filling** — Weighted blend of your actual work patterns + Gemini comment generation for autofilled slots
- **Catchup Mode** — Auto-detects missing weeks and generates preview without manual date entry
- **Excel Preview** — Color-coded review file (green=original, yellow=autofilled, red=totals) before upload
- **SharePoint Upload** — Graph API integration to post entries directly to the Time Tracker list; `--force` re-uploads existing weeks
- **Manager Report** — Weekly hours pivot table and opportunity tracking summary

## Installation

```bash
git clone <repository-url>
cd sca-time-automation

python -m venv .venv
.venv\Scripts\activate          # Windows

pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env` and fill in:
   - `ONEDRIVE_PATH` — path to your OneDrive (for project_codes.xlsx)
   - `GRAPH_ACCESS_TOKEN` — from [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) (expires hourly)
   - `GEMINI_API_KEY` — from [AI Studio](https://aistudio.google.com/apikey) (optional)

2. Export calendar events by running `cscript scripts/calendar_export.vbs` from a terminal (no Outlook macro setup needed)

3. **Access token** — `GRAPH_ACCESS_TOKEN` is optional if `az login` is active; the tool falls back to `az account get-access-token` automatically. Set it in `.env` only when Azure CLI is unavailable.

4. Symlink project codes: `mklink data\input\project_codes.xlsx "path\to\Project_Codes.xlsx"`

## Usage

```bash
# 1. Export calendar (shows VBA instructions)
python run.py export

# 2. Generate preview
python run.py preview              # With AI client detection
python run.py preview --no-ai     # Keyword matching only (faster)
python run.py preview --weeks 12  # Limit to last 12 weeks

# 3. Review data/output/time_entries_preview.xlsx

# 4. Check status
python run.py status

# 5. Upload to SharePoint
python run.py upload --all           # All weeks
python run.py upload --latest        # Most recent week
python run.py upload 2025-12-07      # Specific week
python run.py upload --all --force   # Re-upload even if weeks already exist

# Or: auto-detect and preview missing weeks in one step
python run.py catchup                # Preview only missing weeks
python run.py catchup --dry-run      # Show which weeks are missing, no Excel generated
python run.py catchup --max-weeks 8  # Limit lookback

# 6. Manager report (optional)
python run.py report
python run.py report --weeks 8
```

## Architecture

```
VBS Script (cscript scripts/calendar_export.vbs) -> calendar_export.json
  -> loader.py      (load + filter events)
  -> mapper.py      (category mapping + client detection)
  -> overlap.py     (priority-based overlap resolution)
  -> aggregator.py  (sort + week totals)
  -> gap_filler.py  (autofill empty slots to 40h)
  -> excel_writer.py (formatted Excel output)
  -> User reviews
  -> sharepoint.py  (Graph API upload)
```

Key config files: `config/settings.yaml`, `config/category_mapping.yaml`, `config/excluded.yaml`

## Testing

```bash
python -m pytest
python -m ruff check src/
```

60 automated tests across date utils, gap filler, SharePoint queries, catchup logic, upload idempotency, and Excel writer.

## Development

See [CLAUDE.md](CLAUDE.md) for module details, coding standards, and known issues.

## License

Internal use only — Blue Yonder Pre-Sales Engineering.
