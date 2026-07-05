# BACKLOG — corp-sca-time-automation

## Big picture

corp-sca-time-automation turns a manual weekly chore — submitting time entries to the
SharePoint SCA Time Tracker — into a review-and-approve pipeline from Outlook calendar
exports. The backlog raises the safety net (test coverage) and pays down code-hygiene
debt so the pipeline stays trustworthy and readable.

**Themes (backbone):** Test coverage & safety net · Code hygiene & dead-code cleanup

---

## Test coverage & safety net
> As a maintainer, I want the silent-regression-prone modules under test, so a bad change is caught before it ships a wrong week.

### Cover the four genuinely-untested pipeline modules
So that config loading, calendar load/filter, project-code matching, and text normalization cannot regress silently.
- [#1] [P2][M] Add pytest coverage for the 4 uncovered `src/` modules — `config`, `loader`, `project_codes`, `text_utils` (the other 8 are covered: 69 passed / 1 skipped) · Done when: each of the 4 has a `tests/test_*.py` exercising it under `python -m pytest` · refs migrated from CLAUDE Known-issues; re-scoped 2026-06-02

---

## Code hygiene & dead-code cleanup
> As a reader, I want names that match behavior and one source of truth per constant/type, so the pipeline does not mislead the next change.

### Fix the misleading name and the duplicated constants
So that no call site reasons wrongly from a lying name or a constant that drifted between copies.
- [#2] [P3][S] Rename `aggregator.py::aggregate_entries()` (it sorts + adds `>>> WEEK TOTAL` rows; it does not aggregate) to e.g. `sort_and_total_entries()` · Done when: the rename lands + call sites updated · refs ARCHITECTURE Invariant #4
- [#3] [P3][S] Consolidate the duplicated `NO_OPPORTUNITY_ID_CATEGORIES` constant (defined in both `excel_preview.py` and `gap_filler.py`) to a single source · Done when: one definition remains · refs CLAUDE §10
- [#4] [P3][S] Consolidate the duplicated SharePoint `CATEGORY_MAP` (`sharepoint.py` vs the mapper/overlap modules) to a single source · Done when: one definition remains · refs CLAUDE §10

### Remove the dead code and resolve the dead types
So that the source of truth for data shapes is unambiguous and unreachable code stops accruing maintenance surface.
- [#5] [P3][S] Resolve the dead `models.py` TypedDicts (not imported elsewhere; `CalendarEvent` is duplicated in `loader.py`) — adopt `models.py` as the shared type source or remove the dead definitions · Done when: types have a single source · refs CLAUDE Known-issues
- [#6] [P3][S] Remove the deprecated dead `detect_client_from_comment()` in `gemini_client.py` · Done when: the function is gone + no references remain · refs CLAUDE Known-issues
- [#7] [P3][S] Verify `split_multiday_events()` in `excel_preview.py` is needed (used only internally) or remove it · Done when: kept-with-justification or removed · refs CLAUDE Known-issues

---

## Tenrox migration follow-ups
> As the timesheet owner, I want the Tenrox loader on a durable auth surface, so the ~1h cookie paste is not a permanent operating constraint.

### Escalate for a non-federated API credential
So that the loader can drop REST auth back in behind the same surface and stop depending on a per-run browser-cookie paste.
- [#8] [P2][M] Escalate to Upland/IT (ServiceNow / Marcin Izydorczyk) for a non-federated Tenrox API credential (service account or app token) — **preferred long-term path**. Context: REST `/api/token` password grant returns `400 Invalid credentials` for the SSO-federated account, the UI cookie does not authorize `/api/*`, AND the ASPX `MyTimesheet.aspx` handler is not drivable from standalone Python (pageKey single-use; STOP-GATE 2 + EXP-1/2, 2026-07-05; see `docs/audits/2026-07-05-tenrox-aspx-pivot.md`). Interim write path is an in-page console snippet run in the operator's live tab · Done when: an API credential is provisioned and `src/tenrox.py` revives its REST client behind the payload-builder surface, or IT confirms none is available · refs ASPX-pivot audit
- [#9] [P3][L] Full browser automation for Tenrox upload (Playwright with a persistent SSO/MFA profile) so the in-page-snippet manual paste step is eliminated. Depends on a decided SSO login strategy; only worthwhile if #8 does not land · Done when: an automated driver posts an approved week end-to-end without a manual console paste, or the slice is closed in favour of #8 · refs ASPX-pivot audit, console-uploader

---

**About this file** — ADR-66 story-map (Big Picture → Theme → User Story → Task), migrated
2026-06-02 from the ADR-41/47 stream schema per ADR-38 A6 (canonical backlog form, all
repos). Stories are human (goal + `So that`); tasks carry `[#id] [P][size] · Done when · refs`.
Done tasks **leave** (ADR-65); git is the implementation record.

**Grooming log:** 2026-05-27 (migrated from CLAUDE Known-issues) · 2026-06-02 (story-map migration; 7 open items preserved). Next quarterly: 2026-07-01.
