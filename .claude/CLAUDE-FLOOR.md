# CLAUDE-FLOOR.md — methodology floor

> Auto-loaded methodology baseline for any Claude Code / Codex session in this repo. Generated from the methodology hub; do not hand-edit (a `.sha256` sidecar guards it). Re-read this file before any structural change.

## Session contract
- Claude Code is the **executor**: it reads, edits, tests, commits, branches. It does **not** make architectural decisions without an explicit prompt, and **never improvises** — no clear prompt, no action.
- Every formal prompt opens with a 3-line header: **Model** (Sonnet = "do it the usual way" / Opus = "figure out the approach") · **Mode** (auto-accept / plan-then-auto / plan) · **Effort** (low / medium / high / xhigh).
- Pick **max 1–2 objectives** per session. Everything else is backlog. Scope is sacred.

## Valve discipline (UNDERSTAND first)
- Before planning, state: what is the problem, what could break, which files are involved.
- For any non-trivial change, **STOP after UNDERSTAND** and get approval before creating or editing files.
- Plan Mode first catches a bad approach at 200 tokens instead of 5,000.

## Verify cadence
- Run the repo's checks **after each numbered step, not at the end** — default trio: `pytest -x --tb=short && ruff check && git status` (substitute the repo's actual test/lint commands).
- "Verify, don't trust" — if a long session says "done", check the filesystem / re-run the tests.
- A step with no verify action is incomplete.

## Ship rule (branch → merge --no-ff)
- **Every** change — even a one-line doc edit — goes branch → merge `--no-ff`; never commit direct to `main`. Branches: `feat/ fix/ docs/ chore/`.
- Commit after each file edit (Conventional Commits: `type(scope): summary` + body for non-trivial). Git history IS the changelog.
- Finish via the `/ship` git-finish flow (merge `--no-ff`, never fast-forward). **Working tree must be clean at session end.**

## Context budget
- `/clear` between unrelated tasks (different feature/repo, or after a high-effort prompt).
- After **2 failed attempts**, `/clear` and rewrite the prompt from scratch — polluted context makes it worse, not better.
- Read line ranges (`@file:15-80`), not whole files. Use `!cmd` for quick zero-token checks.

## Safety + gotchas
- **Check the gotchas skill before modifying any file.**
- **Never delete files, functions, code blocks, or branches without asking.**
- **`OneDrive - Blue Yonder` is an absolute exclusion zone** — never write or delete into any path containing it.
- Date every artifact (filename or frontmatter).

## Re-anchor rule
Before any **structural** change (architecture, governance, a multi-file refactor, a new abstraction), **re-read this floor first**. For ordinary within-session work, trust the context already loaded — no per-action re-read needed.

## Depth escape-hatches (optional — not required for a normal session)
- This repo's own `CLAUDE.md`, `VISION.md`, `ARCHITECTURE.md` — repo-specific authority.
- The methodology hub (`.dev-knowledge`) — full protocols (PLAYBOOK / ESSENTIALS). Depth only; this floor is self-sufficient for a normal session.
