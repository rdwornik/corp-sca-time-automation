# archive/ — Pending-Classification Zone

Per ADR-60 amendment 2026-05-27 (in `.dev-knowledge/docs/decisions/`).

Holding zone for artifacts whose destination isn't yet decided. Reviewed periodically; each item is either:

- deleted (git history retains it), or
- promoted to `decisions/`, `audits/`, `diagrams/`, or authored into an ADR.

Not a dumping ground — a triage queue. If something sits here across two reviews with no decision, default to deletion.

## Child-repo taxonomy reminder

This is a child code repo. Its `docs/` carries `decisions/` + `audits/` + `archive/` (+ `diagrams/` where applicable). It does **not** carry `handoffs/` (centralized in `.dev-knowledge/docs/handoffs/`), `research/`, or `council-questions/`.

## Current contents

- `2026-03-15_CODE_REVIEW_REPORT.md` — pre-ADR-34 UPPERCASE-TYPE naming pattern (BACKLOG P3 "retire opportunistically during Phase 2 visits" — left in place this session as cosmetic-only)

## Naming convention

`YYYY-MM-DD-{descriptive-slug}.md` (lowercase slug; the UPPERCASE-TYPE file above is legacy).

## How to review

1. Open the file. Skim for what's still actionable.
2. If actionable → `git mv` to the correct live folder (preserves history).
3. If superseded / one-shot value already extracted → `git rm`.
4. If still genuinely "don't know" after two passes → `git rm` (the periodic-review threshold).
