---
version: "1.0"
owner: Rob
last_reviewed: "2026-05-27"
status: active
---

# VISION — corp-sca-time-automation

## Vision

`corp-sca-time-automation` automates weekly time-entry submission to the
SharePoint SCA Time Tracker from Outlook calendar exports. It loads VBA-exported
calendar events, maps them to SharePoint categories, detects the client (via
Gemini AI with a keyword fallback), resolves overlapping events by priority,
fills gaps to a 40-hour week, writes a colour-coded Excel preview for human
review, and uploads the approved week to SharePoint via the Graph API. It turns a
manual, error-prone weekly chore into a review-and-approve workflow.

## Scope

**In scope:**
- Calendar-export ingestion and category/week filtering.
- Outlook→SharePoint category mapping and client detection (AI or keyword).
- Priority-based overlap resolution and gap-fill to 40h.
- Excel preview generation (colour-coded) for human review.
- Idempotent per-week upload to the SharePoint SCA Time Tracker (Graph API).
- Manager report generation; missing-week catch-up detection.

**Out of scope (non-goals):**
- Acting without human review — the Excel preview is an approval gate.
- Business logic or data belonging to other repos.
- Obsidian vault interaction.
- Migrating off `requirements.txt` to `pyproject.toml` (intentional — see ARCHITECTURE).

## Relationships

corp-sca-time-automation operates under the `.dev-knowledge` methodology and is
**fully standalone** at runtime. Its one shared-state dependency is read-only:
it reads `Project_Codes.xlsm` from `90_System/`, which is **also read by
`corp-opportunity-manager`** (shared input, not a code dependency). It uploads
time entries to SharePoint via the Graph API.

## Lifecycle

VISION is a living document, reviewed at session boundaries.

**Review triggers:**
- New pipeline stage or output target added.
- The SharePoint SCA Time Tracker schema or category set changes.
- The shared `Project_Codes.xlsm` contract changes (coordinate with
  corp-opportunity-manager — a drift signal if it diverges).

**Ownership:** Rob (sole authority).
**Edit process:** conversational edit (standalone repo; no Council gate).

## References

- `ARCHITECTURE.md` — pipeline, module map, invariants
- `CLAUDE.md` — session contract and how to work in this repo
- `BACKLOG.md` — cross-session pending items (tech-debt tracked here)
- `.dev-knowledge/` — ecosystem methodology and governance
