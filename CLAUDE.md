# CLAUDE.md — SCA Time Automation
> **Session contract for Claude Code in this repo.** Read on every session start (auto). Single canonical agent-instruction file per ADR-53.
>
> **For universal rules:** read `../.dev-knowledge/protocols/ESSENTIALS.md` and `../.dev-knowledge/protocols/PLAYBOOK.md`.

## 1. First read (session start)

In order, read:
1. This file (you're here)
2. `VISION.md` — purpose, scope, relationships
3. `ARCHITECTURE.md` — pipeline, module map, invariants
4. `../.dev-knowledge/protocols/ESSENTIALS.md` — Rob's universal working style
5. Recent commits (`git log --oneline -5`) for current context

## 2. Repo identity

- **Name:** `corp-sca-time-automation`
- **Status:** `active`
- **Purpose:** Automates weekly time-entry submission to the SharePoint SCA Time Tracker from Outlook calendar exports (map → detect client → resolve overlap → fill to 40h → Excel preview → upload).
- **Owner:** Rob
- **Critical paths:** `scripts/run.py`, `src/`, `config/`, `tests/`
- **Relationships:** fully standalone at runtime. Reads `Project_Codes.xlsm` from `90_System/` (shared input with `corp-opportunity-manager`). Uploads to SharePoint via Graph API.
- **License:** internal use only — Blue Yonder Pre-Sales Engineering.

## 3. Architecture

See `ARCHITECTURE.md` for the pipeline, module map, layer/invariants, and data flow (required per ADR-51 — mandatory for every repo). The pipeline is a flat-module sequence: `loader → mapper → overlap → aggregator → gap_filler → excel_writer → (human review) → sharepoint`.

## 4. Conventions

- **Naming:** snake_case Python; `ADR-NN-topic.md` if local ADRs are ever added (hyphen per ADR-34).
- **Commits:** Conventional Commits — `type(scope): summary`.
- **Branches:** `feat/<topic>`, `fix/<topic>`, `chore/<scope>` off `main`.
- **Dev standards:** Python 3.12+, functional style (no classes unless necessary); TypedDict for type hints; explicit imports (`from src.module import function`); YAML/`.env` for all config, no hardcoded values; graceful degradation (AI → keyword fallback); all comments/docs in English.
- **Linting/testing:** `python -m ruff check src/`; `python -m pytest`.

## 5. Setup

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` at the repo root with (no `.env.example` template is kept — root hygiene, ADR-49/PLAYBOOK):
- `ONEDRIVE_PATH` — path to your OneDrive (for `project_codes.xlsx`)
- `GRAPH_ACCESS_TOKEN` — Graph API bearer token from [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) (expires hourly). **Optional if `az login` is active** — the tool falls back to `az account get-access-token` automatically; set it in `.env` only when Azure CLI is unavailable.
- `GEMINI_API_KEY` — Gemini AI key (optional; enables AI client detection)
- Azure IDs — tenant / client IDs per `config/settings.yaml`

Then:
1. Export calendar events: `cscript scripts/calendar_export.vbs` (no Outlook macro setup needed) — `python scripts/run.py export` prints these instructions.
2. Symlink project codes: `mklink data\input\project_codes.xlsx "path\to\Project_Codes.xlsx"`.

API keys are otherwise loaded globally from `Documents/.secrets/.env` via the PowerShell profile — do **not** add keys to a repo-local `.env` beyond the per-session `GRAPH_ACCESS_TOKEN`. This repo uses `GEMINI_API_KEY`.

## 6. Key commands

```bash
python scripts/run.py export                 # Show VBA export instructions
python scripts/run.py preview                # Generate Excel preview (AI mode)
python scripts/run.py preview --no-ai        # Without AI (faster)
python scripts/run.py preview --weeks 12     # Limit to last 12 weeks
python scripts/run.py status                 # Show weeks and totals
python scripts/run.py upload --all           # Upload all weeks
python scripts/run.py upload --latest        # Upload most recent week
python scripts/run.py upload 2025-12-07      # Upload specific week
python scripts/run.py upload --all --force   # Re-upload even if weeks exist
python scripts/run.py report [--weeks N]     # Manager report
python scripts/run.py catchup [--dry-run]    # Auto-detect + preview missing weeks
```

## 7. Slash commands available

User-level (`~/.claude/commands/`): `/boot`, `/save`, `/session-summary`. No repo-level commands directory.

## 8. Skills active

- User-level (`~/.claude/skills/`): `gotchas` (consult before modifying code), `verify` (after pytest passes).
- Repo-level (`.claude/rules/`): `code-standards.md`, `python-env.md`, `testing.md` — read before code changes.

## 9. Hooks active

No `.pre-commit-config.yaml`. Lint/test run manually (`python -m ruff check src/`, `python -m pytest`) per §4.

## 10. Anti-patterns specific to Claude Code in this repo

- **`aggregator.py` naming:** `aggregate_entries()` sorts + adds total rows; it does NOT aggregate. Do not assume summation (tracked in BACKLOG).
- **Duplicated constants:** `NO_OPPORTUNITY_ID_CATEGORIES` and `CATEGORY_MAP` are duplicated across modules — change all copies or consolidate (see BACKLOG).
- **Standalone "tests":** several `tests/test_*.py` are scripts run via `python tests/test_*.py`, not pytest — do not assume `pytest` covers them.
- **GRAPH_ACCESS_TOKEN:** is per-session (~short-lived) — refresh before upload runs.
- **Upload idempotency:** re-running upload does not duplicate a week unless `--force`; do not add `--force` to bypass an apparent "missing" week without checking.

## 11. Recent ADRs binding here

Governance ADRs live in `../.dev-knowledge/docs/decisions/`:
- ADR-33: VISION.md universalization (frontmatter schema; tier/scale removed 2026-05-23)
- ADR-34: file naming conventions (hyphen ADR names)
- ADR-38: universal repo baseline (VISION + ARCHITECTURE + BACKLOG mandatory; README optional, A5)
- ADR-49: record consolidation (CHANGELOG retired; git history as record)
- ADR-51: ARCHITECTURE.md convention (universal; text-only codemap override for flat repos)
- ADR-53: CLAUDE.md as single canonical agent-instruction file

## 12. Section history

- v1.0 (pre-ADR-53) — free-form reference (what-this-repo-does, quick-start, inline architecture + data flow + Known-issues + module table).
- v2.0 (2026-05-27) — re-homed into the ADR-53 12-section template; architecture + data flow moved to `ARCHITECTURE.md`; "Known issues" moved to `BACKLOG.md`; purpose/scope moved to `VISION.md`; `.env.example` retired (env vars documented in §5); dangling `../ECOSYSTEM.md` link removed.

---

**Last updated:** 2026-05-27
**Maintained by:** Rob
