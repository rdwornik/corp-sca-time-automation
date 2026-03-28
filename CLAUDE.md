# CLAUDE.md — SCA Time Automation

## What this repo does

Automates weekly time entry submission to SharePoint SCA Time Tracker from Outlook calendar exports. Exports calendar events via VBA, maps them to SharePoint categories, detects clients (AI or keyword), fills gaps to 40h, and uploads via Graph API.

## Quick start

```bash
# Install
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env  # then fill in ONEDRIVE_PATH, GRAPH_ACCESS_TOKEN, GEMINI_API_KEY

# Run
python run.py preview          # Generate Excel preview
python run.py preview --no-ai  # Without AI (faster)
python run.py status           # Show weeks and totals
python run.py upload --all     # Upload all weeks to SharePoint
python run.py upload --latest  # Upload most recent week
python run.py upload 2025-12-07  # Upload specific week
python run.py report           # Generate manager report
python run.py export           # Show VBA export instructions
python run.py catchup          # Auto-detect missing weeks, generate preview
```

## Architecture

### Data flow

```
VBA Export (Outlook) -> calendar_export.json
  -> loader.py (load + filter by category/weeks)
  -> mapper.py (category mapping + client detection)
  -> overlap.py (priority-based hour slot resolution)
  -> aggregator.py (sort + add week totals)
  -> gap_filler.py (autofill empty slots to 40h)
  -> excel_writer.py (formatted Excel with colors)
  -> User reviews Excel
  -> sharepoint.py (upload via Graph API)
```

### Key modules

| Module | Purpose |
|--------|---------|
| `run.py` | CLI entry point (argparse) |
| `src/config.py` | Load YAML configs + `.env` with `${VAR}` expansion |
| `src/loader.py` | Load calendar JSON, filter excluded categories, filter by weeks |
| `src/mapper.py` | Outlook->SharePoint category mapping, client detection (AI/keyword) |
| `src/overlap.py` | Resolve overlapping events (highest priority wins per hour slot) |
| `src/aggregator.py` | Sort entries + add ">>> WEEK TOTAL" summary rows (no aggregation) |
| `src/gap_filler.py` | Find empty 9-17 slots, generate proportional autofill entries |
| `src/excel_preview.py` | Orchestrates full pipeline: load -> map -> overlap -> aggregate -> fill -> write |
| `src/excel_writer.py` | Write formatted Excel (green=original, yellow=autofilled, red=totals) |
| `src/date_utils.py` | Sunday-based week math: last_sunday, sundays_between, weeks_back_to_cover |
| `src/sharepoint.py` | Graph API client, query uploaded weeks, post entries to SharePoint list |
| `src/gemini_client.py` | Gemini AI for client detection + comment generation |
| `src/project_codes.py` | Load project codes from Excel, match client->opportunity_id |
| `src/text_utils.py` | Text normalization (accents, case, whitespace) |
| `src/models.py` | TypedDict definitions |
| `scripts/manager_report.py` | Generate manager summary report |

### Config files

- `config/settings.yaml` — paths, processing params, SharePoint IDs, AI config
- `config/category_mapping.yaml` — Outlook category prefix -> SharePoint category name
- `config/excluded.yaml` — categories to skip entirely
- `.env` — `ONEDRIVE_PATH`, `GRAPH_ACCESS_TOKEN` (per-session), Azure IDs

## API Keys

Keys loaded globally from `Documents/.secrets/.env` via PowerShell profile.
Do NOT add API keys to local `.env`.
Check: `keys list` | Update: `keys set KEY value` | Reload: `keys reload`

This repo uses: `GEMINI_API_KEY`

## Dev standards

- Python 3.12+, functional style (no classes unless necessary)
- TypedDict for type hints
- Explicit imports: `from src.module import function`
- YAML/`.env` for all configuration, no hardcoded values
- `ruff` for linting and formatting
- `pytest` for tests
- All comments and docs in English
- Graceful degradation (AI -> keyword fallback)

## Key commands

```bash
python run.py export                  # Show VBA export instructions
python run.py preview                 # Generate preview (AI mode)
python run.py preview --no-ai        # Generate preview (keyword only)
python run.py preview --weeks 12     # Limit to last 12 weeks
python run.py status                  # Show weeks in preview
python run.py upload --all           # Upload all weeks
python run.py upload --latest        # Upload most recent week
python run.py upload 2025-12-07      # Upload specific week
python run.py upload --all --force   # Re-upload even if weeks already exist
python run.py report                  # Manager report
python run.py report --weeks 8       # Manager report, last 8 weeks
python run.py catchup                 # Auto-detect + preview missing weeks
python run.py catchup --dry-run      # Show missing weeks without generating Excel
python run.py catchup --max-weeks 8  # Limit lookback when no uploads found
```

## Test suite

```bash
python -m pytest                     # Run all tests
python -m pytest tests/test_no_opportunity_categories.py  # Specific file
python -m ruff check src/            # Lint check
```

Current: 56 pytest tests across `test_no_opportunity_categories.py`, `test_date_utils.py`, `test_sharepoint_queries.py`, `test_catchup.py`, `test_upload_idempotency.py`, `test_excel_writer.py`, `test_gap_filler_v2.py`. Other test files (`test_overlap_fix.py`, `test_client.py`, `test_column_order.py`, `test_no_aggregation.py`, `test_gemini_client_detection.py`, `test_upload.py`) are standalone verification scripts (run with `python tests/test_*.py`), not pytest tests.

## Dependencies

- `pandas` — DataFrame operations, Excel I/O
- `openpyxl` — Excel formatting and tables
- `pyyaml` — YAML config parsing
- `python-dotenv` — `.env` file loading
- `google-genai` — Gemini AI client (optional)
- `requests` — SharePoint Graph API calls

## Integration points

corp-sca-time-automation is fully standalone.

- **Shared state**: reads Project_Codes.xlsm from 90_System/ (shared with corp-opportunity-manager)
- Uploads time entries to SharePoint via Graph API
- No Obsidian vault interaction

## Related repos

- [ECOSYSTEM.md](../ECOSYSTEM.md) — full ecosystem overview
- [corp-opportunity-manager](../corp-opportunity-manager/) — also reads Project_Codes.xlsm
- [corp-ops](../corp-ops/) — SharePoint/Graph API tooling

## Known issues

- `models.py` defines TypedDicts that are not imported elsewhere (duplicate CalendarEvent in loader.py)
- `aggregator.py` function `aggregate_entries()` is misleadingly named — it sorts, not aggregates
- `NO_OPPORTUNITY_ID_CATEGORIES` is duplicated in `excel_preview.py` and `gap_filler.py`
- `CATEGORY_MAP` for SharePoint is duplicated in `sharepoint.py` vs mapper/overlap modules
- Most test files are standalone scripts, not proper pytest tests — low automated test coverage
- Modules with zero pytest coverage: config, loader, mapper, overlap, aggregator, gap_filler, excel_preview, excel_writer, sharepoint, gemini_client, project_codes, text_utils
- `split_multiday_events()` in excel_preview.py is defined but only used internally — verify it's needed
- `detect_client_from_comment()` in gemini_client.py is deprecated dead code

## Priority order (overlap resolution)

1. Customer - Demo/Presentation (100)
2. Discovery (90)
3. RFI/RFP/RFQ (85)
4. POC (80)
5. Prep - Demo/Presentation (70)
6. Internal Meeting (50)
7. Training (40)
8. Support (30)
9. Admin (20)
10. Travel (10)
11. Time Off (5)

## License

Internal use only — Blue Yonder Pre-Sales Engineering.
