# Code Review Report — SCA Time Automation

**Date:** 2026-03-15
**Branch:** `code-review-2026-03-15`
**Reviewer:** Claude Opus 4.6

## Final State

```
REPO: corp-sca-time-automation
TESTS: 2 passed, 0 failed
RUFF: clean (0 issues)
COMMITS: 3
FILES CHANGED: 23
```

## Commits Made

1. `e8afec9` — **style: ruff lint + format pass** (21 files)
2. `627546a` — **docs: update CLAUDE.md to current state** (2 files)
3. `ab47374` — **docs: professional README** (1 file)

## Issues Found and Fixed

### Bugs Fixed

| File | Issue | Fix |
|------|-------|-----|
| `src/gap_filler.py:161-164` | `comment` variable used before assignment when `ai_enabled=False` — would cause `NameError` | Initialize `comment = None` before conditional block |
| `src/gap_filler.py:142` | `week_data.get("comments", ...)` uses dict `.get()` on DataFrame — incorrect API | Use `"comments" in week_data.columns` check |
| `src/gap_filler.py:83` | `== False` comparison on pandas Series (E712) | Use `~df["is_autofilled"]` |

### Lint Issues Fixed

| File | Issue |
|------|-------|
| `src/excel_preview.py:13` | Unused imports: `resolve_overlaps_by_hour`, `get_priority` (redefined locally) |
| `src/excel_preview.py:75` | Unused variable `settings` in `generate_preview()` |
| `src/excel_preview.py:78` | Unused variable `sales_categories` |
| `src/excel_preview.py:98` | Unused variable `needs_opp_id` |
| `src/excel_preview.py:9` | Unused import `get_category_mapping` (after removing `sales_categories`) |
| `src/excel_writer.py:71` | Bare `except:` — changed to `except (TypeError, AttributeError):` |

### Formatting

All 22 Python files in `src/` and `tests/` reformatted with `ruff format`.

## Issues Found but NOT Fixed

These are quality issues documented in CLAUDE.md "Known issues" — fixing them would change functionality:

### Dead Code
- `src/gemini_client.py` — `detect_client_from_comment()` marked deprecated, never called
- `src/excel_preview.py` — `split_multiday_events()` defined but only used within `generate_preview()`

### Naming
- `src/aggregator.py` — `aggregate_entries()` doesn't aggregate, it sorts and reorders columns

### Duplication
- `NO_OPPORTUNITY_ID_CATEGORIES` defined in both `excel_preview.py` and `gap_filler.py`
- `CATEGORY_MAP` for SharePoint exists in `sharepoint.py` separately from category config in `mapper.py`/`overlap.py`
- `CalendarEvent` TypedDict defined in both `models.py` and `loader.py`

### Test Coverage Gaps
- Only 2 proper pytest tests exist (in `test_no_opportunity_categories.py`)
- 6 other test files are standalone scripts, not pytest-compatible
- Zero pytest coverage for: config, loader, mapper, overlap, aggregator, excel_writer, sharepoint, gemini_client, project_codes, text_utils

### Architecture Notes
- No `pyproject.toml` — project uses `requirements.txt` only
- Uses `argparse` (not click), `print` (not rich/logging)
- Broad exception handling in `gemini_client.py` and `mapper.py` silently swallows errors

## Documentation Changes

### CLAUDE.md
- Condensed from 650 lines to ~130 lines
- Fixed inaccurate module descriptions
- Added module responsibility table
- Added known issues and test coverage gaps
- Removed speculative future enhancements
- Unignored from `.gitignore` (was incorrectly excluded from version control)

### README.md
- Condensed from 400 lines to ~90 lines
- Professional single-page format
- Clear install/configure/usage flow
- Architecture data flow diagram
- Accurate test count

## Recommendations for Follow-up

1. **Convert standalone test scripts to pytest** — most test logic exists but needs `def test_*()` wrappers
2. **Centralize constants** — move `NO_OPPORTUNITY_ID_CATEGORIES`, `CATEGORY_MAP`, priority order to config
3. **Add `pyproject.toml`** — modern Python packaging, consolidate requirements
4. **Add logging** — replace silent exception swallowing with proper logging
5. **Remove dead code** — `detect_client_from_comment()` in gemini_client.py
