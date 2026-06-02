---
last_reviewed: 2026-06-02
status: active
owner: Rob
---

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

## 5. Critical rules

1. **The Excel preview is a mandatory human-review gate** — never upload a week that has not been reviewed.
2. **`GRAPH_ACCESS_TOKEN` is per-session (~1h)** — refresh before an upload run; it falls back to `az account get-access-token` when `az login` is active.
3. **Never add API keys to a repo-local `.env`** beyond the per-session `GRAPH_ACCESS_TOKEN` — global secrets live in `Documents/.secrets/.env` (PowerShell profile). This repo uses `GEMINI_API_KEY`.
4. **Upload is idempotent per week** — do not add `--force` to bypass an apparent "missing" week without checking first.
5. **Config lives in YAML + `.env` (`${VAR}` expansion)** — never hardcode paths, IDs, or categories.
6. **Client detection degrades gracefully** (Gemini AI → keyword) — do not hard-fail when the AI tier is unavailable.

(First-time environment setup + the `.env` variable list live in `CONTRIBUTING.md` § Pre-commit setup.)

## 6. Session start protocol

1. `git status` — clean working tree?
2. `git log --oneline -5` — recent context
3. Read `VISION.md` + `ARCHITECTURE.md` if continuing structural work
4. `python -m pytest` — confirm green before changes
5. Wait for Rob's prompt — never improvise

(The `scripts/run.py` command reference lives in `ARCHITECTURE.md` § CLI Reference.)

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
- ADR-38: universal repo baseline — A6 (2026-06-02) makes the seven-file canonical set mandatory (VISION, ARCHITECTURE, CLAUDE, BACKLOG, CONTRIBUTING, JOURNAL, LESSONS); README optional
- ADR-49: record consolidation (CHANGELOG retired; git history as record)
- ADR-51: ARCHITECTURE.md convention (universal; text-only codemap override for flat repos)
- ADR-53: CLAUDE.md as single canonical agent-instruction file
- ADR-60: docs/ folder taxonomy (decisions/ + audits/ + archive/ baseline) + entry-scripts in `scripts/` (run.py relocated 2026-05-28)

## 12. Section history

- v1.0 (pre-ADR-53) — free-form reference (what-this-repo-does, quick-start, inline architecture + data flow + Known-issues + module table).
- v2.0 (2026-05-27) — re-homed into the ADR-53 12-section template; architecture + data flow moved to `ARCHITECTURE.md`; "Known issues" moved to `BACKLOG.md`; purpose/scope moved to `VISION.md`; `.env.example` retired (env vars documented in §5); dangling `../ECOSYSTEM.md` link removed.
- v2.1 (2026-06-02) — ecosystem-unify to the seven-file canonical standard (ADR-38 A6): added the required `last_reviewed` YAML frontmatter (the previously-deferred "contested representation" — resolved by the lock); restored the canonical §5 Critical rules + §6 Session start protocol spine (the old §5 Setup → CONTRIBUTING, §6 Key commands → ARCHITECTURE § CLI Reference); §11 ADR-38 line updated to A6. Added `CONTRIBUTING.md` + `LESSONS.md`; VISION +§Values; ARCHITECTURE +Key conventions/+Authority/+Validators/+Governing ADRs; BACKLOG migrated to the ADR-66 story-map.

---

**Last updated:** 2026-06-02
**Maintained by:** Rob
