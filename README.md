# SCA Time Automation

Automates weekly time entry submission to the SharePoint SCA Time Tracker from Outlook calendar exports. Built for Blue Yonder Pre-Sales Engineers to streamline the repetitive process of categorizing meetings, detecting clients, filling time gaps, and uploading entries — reducing a manual 30+ minute task to a quick review-and-submit workflow.

## Features

- **VBA Calendar Export** — Outlook macro exports events with categories and external attendee domains
- **AI-Powered Client Detection** — Gemini AI matches meetings to clients from project codes (with keyword fallback)
- **Smart Category Mapping** — Outlook categories (.PREFIX) map to SharePoint categories automatically
- **Overlap Resolution** — Priority-based: customer-facing activities always win overlapping slots
- **Intelligent Gap Filling** — Distributes missing hours proportionally based on your actual work patterns
- **Excel Preview** — Color-coded review file (green=original, yellow=autofilled, red=totals) before upload
- **SharePoint Upload** — Graph API integration to post entries directly to the Time Tracker list
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

2. Install the VBA macro from `scripts/calendar_export.vbs` in Outlook (Alt+F11 > Insert Module)

3. Symlink project codes: `mklink data\input\project_codes.xlsx "path\to\Project_Codes.xlsx"`

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
python run.py upload --all        # All weeks
python run.py upload --latest     # Most recent week
python run.py upload 2025-12-07   # Specific week

# 6. Manager report (optional)
python run.py report
python run.py report --weeks 8
```

## Architecture

```
Outlook VBA Export -> calendar_export.json
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

2 automated tests covering opportunity ID clearing and gap filler rounding.

## Development

See [CLAUDE.md](CLAUDE.md) for module details, coding standards, and known issues.

## License

Internal use only — Blue Yonder Pre-Sales Engineering.
