---
last_reviewed: 2026-06-02
status: active
owner: Rob
---

# Architecture — `corp-sca-time-automation`

> Living document. Updated after structural changes.
> Last updated: `2026-06-02` (`coherence re-review (universalization G1): priority-table strings aligned to config/code; module map + invariants verified against code`)

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

## CLI Reference

`scripts/run.py` (argparse) drives the pipeline:

| Command | What it does |
|---------|--------------|
| `export` | Show the VBA calendar-export instructions |
| `preview` | Generate the Excel preview (AI mode); `--no-ai` faster, `--weeks N` to limit |
| `status` | Show weeks and totals |
| `upload --all` / `--latest` / `<YYYY-MM-DD>` | Upload all / most-recent / a specific week; `--force` re-uploads existing weeks |
| `report [--weeks N]` | Manager report |
| `catchup [--dry-run]` | Auto-detect + preview missing weeks |

---

## Key conventions

- **Flat module layout.** Every module is a direct child of `src/`; no subpackages (text-only codemap per ADR-51).
- **Functional style.** No classes unless necessary; TypedDict for type hints; explicit imports (`from src.module import function`).
- **Config over hardcoding.** All paths/IDs/categories in YAML + `.env` (`${VAR}` expansion); `requirements.txt` (not `pyproject.toml`, intentional).
- **Append-only files.** `LESSONS.md` — never edit old entries (ADR-29). `JOURNAL.md` — newest-first prepend.
- **Naming.** snake_case Python; kebab-case markdown; `ADR-NN-topic.md` if local ADRs are ever added (ADR-34).

---

## Authority and governance

corp-sca-time-automation is a **standalone pipeline repo** governed by `.dev-knowledge` (Layer-2 binding authority, ADR-31). It carries **no local ADRs** — governance lives in `.dev-knowledge/docs/decisions/`.

- **Conformance:** verified out-of-band, read-only, by `.dev-knowledge/scripts/audit.py`. `.dev-knowledge` never writes here (Layer-2 invariant, ADR-28).
- **One shared input, read-only:** reads `Project_Codes.xlsm` (also read by `corp-opportunity-manager`) — a shared input, not a code dependency.

---

## Validators and enforcement

- **`python -m ruff check src/`** — lint.
- **`python -m pytest`** — unit tests (caveat: some `tests/test_*.py` are standalone scripts, not pytest-collected; see BACKLOG).
- **No pre-commit hooks** — checks run manually (CLAUDE §9).
- **External conformance (read-only):** `.dev-knowledge/scripts/audit.py` — seven-file canonical baseline + structural spine (ADR-38 A6).

---

## Governing ADRs

No local ADRs; binding decisions are ecosystem-level in `.dev-knowledge/docs/decisions/`:
ADR-29 (append-only LESSONS) · ADR-33 (VISION universalization) · ADR-34 (naming) · ADR-38 (universal baseline + A6 seven-file canonical set) · ADR-42 (handoffs centralized) · ADR-49 (record consolidation) · ADR-51 (ARCHITECTURE convention, text-only codemap override) · ADR-53 (CLAUDE.md) · ADR-60 (docs taxonomy).

---

**Maintained by:** Rob
