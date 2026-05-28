# BACKLOG — corp-sca-time-automation

<!-- schema: ADR-41 as relaxed by ADR-47 | grooming: per-handoff + quarterly deep -->

Cross-session pending items. Single source of truth for actionable work. Entry
form: `### [P{N}] [open|closed] <title>` with **What / Why / Added / Status**.
See `.dev-knowledge` ADR-41 (as relaxed by ADR-47) for schema and grooming
cadence. Items below were migrated from the CLAUDE.md "Known issues" list on
2026-05-27 (tech-debt belongs in the tracked backlog, not in prose).

---

### [P2] [open] Thin automated test coverage
- **What:** Most `tests/test_*.py` files are standalone verification scripts (run via `python tests/test_*.py`), not pytest tests. Modules with zero pytest coverage: `config`, `loader`, `mapper`, `overlap`, `aggregator`, `gap_filler`, `excel_preview`, `excel_writer`, `sharepoint`, `gemini_client`, `project_codes`, `text_utils`.
- **Why:** Low automated coverage on the core pipeline; regressions can slip through. Converting standalone scripts to pytest tests would raise the safety net.
- **Added:** 2026-05-27 (migrated from CLAUDE.md Known issues)
- **Status:** open

### [P3] [open] `aggregator.py` `aggregate_entries()` is misnamed
- **What:** `aggregate_entries()` sorts entries and adds week-total rows; it does not aggregate/sum. Rename to reflect actual behavior (e.g. `sort_and_total_entries()`).
- **Why:** Misleading name invites incorrect assumptions about behavior.
- **Added:** 2026-05-27 (migrated from CLAUDE.md Known issues)
- **Status:** open

### [P3] [open] Duplicated `NO_OPPORTUNITY_ID_CATEGORIES` constant
- **What:** `NO_OPPORTUNITY_ID_CATEGORIES` is defined in both `excel_preview.py` and `gap_filler.py`. Consolidate to a single source.
- **Why:** Duplicated constants drift independently → subtle bugs.
- **Added:** 2026-05-27 (migrated from CLAUDE.md Known issues)
- **Status:** open

### [P3] [open] Duplicated `CATEGORY_MAP` constant
- **What:** SharePoint `CATEGORY_MAP` is duplicated in `sharepoint.py` versus the mapper/overlap modules. Consolidate to a single source.
- **Why:** Same drift risk as the duplicated constant above.
- **Added:** 2026-05-27 (migrated from CLAUDE.md Known issues)
- **Status:** open

### [P3] [open] Dead `models.py` TypedDicts
- **What:** `models.py` defines TypedDicts that are not imported elsewhere; `CalendarEvent` is duplicated in `loader.py`. Either adopt `models.py` as the shared type source or remove the dead definitions.
- **Why:** Dead/duplicated type definitions confuse the source of truth for data shapes.
- **Added:** 2026-05-27 (migrated from CLAUDE.md Known issues)
- **Status:** open

### [P3] [open] Deprecated dead code: `detect_client_from_comment()`
- **What:** `detect_client_from_comment()` in `gemini_client.py` is deprecated dead code. Remove it.
- **Why:** Dead code increases maintenance surface and misleads readers.
- **Added:** 2026-05-27 (migrated from CLAUDE.md Known issues)
- **Status:** open

### [P3] [open] Verify `split_multiday_events()` is needed
- **What:** `split_multiday_events()` in `excel_preview.py` is defined but only used internally — confirm it is needed or remove it.
- **Why:** Possible dead/unreachable code path.
- **Added:** 2026-05-27 (migrated from CLAUDE.md Known issues)
- **Status:** open
