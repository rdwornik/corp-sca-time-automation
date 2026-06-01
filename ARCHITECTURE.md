---
last_reviewed: 2026-05-27
status: active
owner: Rob
---

# Architecture — `corp-sca-time-automation`

> Living document. Updated after structural changes.
> Last updated: `2026-05-27` (`initial ADR-51 conformance authoring; content moved from CLAUDE.md`)

## Purpose [CORE]

`corp-sca-time-automation` is a flat-module Python pipeline that converts an
Outlook calendar export into an approved weekly SharePoint time-entry upload. It
maps events to SharePoint categories, detects clients, resolves overlapping
events by priority, fills gaps to 40 hours, writes a colour-coded Excel preview
for human review, and uploads the approved week via the Graph API.

---

## Codemap [CORE]

> **Text-only codemap (override per ADR-51).** corp-sca has a **flat `src/`
> layout** — no package subgraph worth a Mermaid diagram — so this codemap is a
> prose module overview rather than a generated graph (no CODEMAP markers, no
> generator dependency). The semantic detail is in the Module Map below.

The pipeline is a linear sequence of single-purpose modules under `src/`, driven
by the `scripts/run.py` CLI. Configuration modules (`config.py`, `project_codes.py`) and
utility modules (`date_utils.py`, `text_utils.py`, `models.py`) support the
pipeline stages. AI client detection (`gemini_client.py`) is optional and
degrades to keyword matching. `sharepoint.py` is the only outbound network
surface (Graph API). There are no subpackages; every module is a direct child of
`src/`.

---

## Layer Boundaries & Invariants [CORE]

### Layer model

corp-sca is a **flat-module pipeline**, not a layered package. The natural
ordering is the data-flow pipeline (see Data Flow below):

```
loader → mapper → overlap → aggregator → gap_filler → excel_writer → (review) → sharepoint
```

Supporting modules (`config`, `date_utils`, `text_utils`, `models`,
`project_codes`, `gemini_client`) are imported by pipeline stages as needed.

**Enforcement tool:** convention + code review (no Tach; flat layout).
**Config file:** N/A.
**Where enforced:** code review; `python -m ruff check src/`.

### Invariants

1. **Highest-priority category wins per hour slot** during overlap resolution
   (priority table below; `overlap.py`).
2. **`gap_filler.py` fills empty 9–17 slots proportionally to reach a 40-hour
   week** — autofilled entries are marked distinctly (yellow) in the Excel.
3. **SharePoint upload is idempotent per week** — re-running does not duplicate
   an already-uploaded week unless `--force` is passed (`sharepoint.py`).
4. **`aggregator.py` sorts and adds `>>> WEEK TOTAL` summary rows; it does NOT
   sum/aggregate** (the name is misleading — tracked in BACKLOG).
5. **The Excel preview is a mandatory human-review gate** before any upload.
6. **All configuration lives in YAML + `.env` with `${VAR}` expansion** — no
   hardcoded paths, IDs, or categories.
7. **Client detection degrades gracefully**: Gemini AI → keyword fallback.

### Priority order (overlap resolution)

| Priority | Category |
|----------|----------|
| 100 | Customer - Demo/ Presentation |
| 90 | Discovery |
| 85 | RFI/RFP/RFQ |
| 80 | POC |
| 70 | Prep - Demo/ Presentation |
| 50 | Internal Meeting |
| 40 | Training |
| 30 | Support |
| 20 | Admin |
| 10 | Travel |
| 5 | Time Off |

→ Related decisions: governance ADRs in `.dev-knowledge/docs/decisions/` (ADR-38 baseline, ADR-51 architecture convention).

---

## Module Map

### `src/` (flat) + entry point

| Module | Responsibility |
|--------|----------------|
| `scripts/run.py` | CLI entry point (argparse): preview / status / upload / report / export / catchup |
| `src/config.py` | Load YAML configs + `.env` with `${VAR}` expansion |
| `src/loader.py` | Load calendar JSON; filter excluded categories; filter by weeks |
| `src/mapper.py` | Outlook→SharePoint category mapping; client detection (AI/keyword) |
| `src/overlap.py` | Resolve overlapping events (highest priority wins per hour slot) |
| `src/aggregator.py` | Sort entries + add `>>> WEEK TOTAL` rows (sorts, does not aggregate) |
| `src/gap_filler.py` | Find empty 9–17 slots; generate proportional autofill to 40h |
| `src/excel_preview.py` | Orchestrates the pipeline: load → map → overlap → aggregate → fill → write |
| `src/excel_writer.py` | Write formatted Excel (green=original, yellow=autofilled, red=totals) |
| `src/date_utils.py` | Sunday-based week math (last_sunday, sundays_between, weeks_back_to_cover) |
| `src/sharepoint.py` | Graph API client; query uploaded weeks; post entries to the SharePoint list |
| `src/gemini_client.py` | Gemini AI for client detection + comment generation (optional) |
| `src/project_codes.py` | Load project codes from Excel; match client → opportunity_id |
| `src/text_utils.py` | Text normalization (accents, case, whitespace) |
| `src/models.py` | TypedDict definitions |
| `scripts/manager_report.py` | Generate manager summary report |

---

## Data Flow

```
VBA Export (Outlook) -> calendar_export.json
  -> loader.py        (load + filter by category/weeks)
  -> mapper.py        (category mapping + client detection)
  -> overlap.py       (priority-based hour slot resolution)
  -> aggregator.py    (sort + add week totals)
  -> gap_filler.py    (autofill empty slots to 40h)
  -> excel_writer.py  (formatted Excel with colours)
  -> User reviews Excel
  -> sharepoint.py    (upload via Graph API)
```

---

## Configuration Architecture

| Source | Format | Purpose |
|--------|--------|---------|
| `config/settings.yaml` | YAML | paths, processing params, SharePoint IDs, AI config |
| `config/category_mapping.yaml` | YAML | Outlook category prefix → SharePoint category name |
| `config/excluded.yaml` | YAML | categories to skip entirely |
| `.env` | dotenv | `ONEDRIVE_PATH`, `GRAPH_ACCESS_TOKEN` (per-session), `GEMINI_API_KEY`, Azure IDs |

**Resolution order:** `.env` `${VAR}` expansion into YAML > YAML literal value.

> **Dependency model:** corp-sca runs on `requirements.txt` (pandas, openpyxl,
> pyyaml, python-dotenv, google-genai, requests). It intentionally does **not**
> use `pyproject.toml` — see VISION § Scope.

---

**Maintained by:** Rob
