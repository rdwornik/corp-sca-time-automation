---
last_reviewed: 2026-06-02
status: active
owner: Rob
---

# Contributing

<!-- scope: meta -->

Sole contributor: Rob Dwornik. Audience: future Rob + AI agents (Claude Code, Codex)
working on the time-automation pipeline. Universal working style lives in
`../.dev-knowledge/protocols/ESSENTIALS.md` + `PLAYBOOK.md`; this file is the
repo-specific contribution contract.

## Branch naming

Off `main` (ADR-30): `feat/<topic>`, `fix/<topic>`, `chore/<scope>`. One branch per unit
of work; merge `--no-ff` after the manual checks pass.

## Commit style

Conventional Commits — `type(scope): summary` (imperative). Types: `feat / fix / docs /
chore / refactor / test`. All comments/docs in English.

### Backlog-id references (forward-only index)

`BACKLOG.md` follows the ADR-66 story-map; tasks carry a `[#id]`. When a commit closes a
task, reference it (`closes [#id]`) so the work is locatable via
`git log --grep "closes \[#"`. Git history is the implementation record (ADR-65); done
tasks leave the file.

## Pre-commit setup

No `.pre-commit-config.yaml` — checks are run manually (see Validators).

### First-time environment setup

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` at the repo root (no `.env.example` is kept — root hygiene):

- `ONEDRIVE_PATH` — path to your OneDrive (for `project_codes.xlsx`)
- `GRAPH_ACCESS_TOKEN` — Graph API bearer token from Graph Explorer (expires hourly).
  **Optional if `az login` is active** — the tool falls back to `az account get-access-token`.
- `GEMINI_API_KEY` — Gemini AI key (optional; enables AI client detection)
- Azure tenant / client IDs per `config/settings.yaml`

Then symlink project codes: `mklink data\input\project_codes.xlsx "path\to\Project_Codes.xlsx"`.
API keys are otherwise loaded globally from `Documents/.secrets/.env` via the PowerShell
profile — do **not** add keys to a repo-local `.env` beyond the per-session `GRAPH_ACCESS_TOKEN`.

## Validators

- **Lint:** `python -m ruff check src/`.
- **Tests:** `python -m pytest` (note: several `tests/test_*.py` are standalone scripts run via
  `python tests/test_*.py`, not pytest — see CLAUDE §10 / BACKLOG).
- **External conformance (read-only):** `../.dev-knowledge/scripts/audit.py` audits this repo
  against the seven-file canonical standard (ADR-38 A6); it never writes here (ADR-28).

## ADR process

corp-sca carries **no local ADRs** — governance decisions live in
`../.dev-knowledge/docs/decisions/`. If a repo-specific decision ever warrants a record, add
`docs/decisions/ADR-NN-topic.md` (hyphen-named, ADR-34) and note it here.

## Handoff process

Handoffs centralize in `../.dev-knowledge/docs/handoffs/` (ADR-42/60) — this repo carries no
`docs/handoffs/`. Continuing a prior session: read the most recent bundle there, then recent
commits + the last `JOURNAL.md` entries here.
