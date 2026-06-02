# Installing the `tier1-lifecycle` plugin

ADR-70 Tier-1 lifecycle for a host repo: session-end **propose-closures** (Stop
hook), proposal **surfacing** (SessionStart hook), the **`/review-closures`**
human-gated close command, and a portable **ruff lint gate**.

The plugin operates on the host repo's `BACKLOG.md` and `logs/` via
`$CLAUDE_PROJECT_DIR`; the scripts themselves live under `${CLAUDE_PLUGIN_ROOT}`.

## Prerequisites

- The host repo has a `BACKLOG.md` whose tasks use the `- [#id] ... · Done when: ...`
  form (ADR-66). The proposer degrades gracefully on a smaller/simpler backlog —
  it proposes only what matches and writes "no closures detected" otherwise.
- A `logs/` directory will be created on first run (gitignore `logs/PROPOSALS-*.md`).

## 1. Install the CC plugin (commands + hooks)

The `.dev-knowledge` hub is a plugin **marketplace** (`.claude-plugin/marketplace.json`).
Add it and install at **project scope** (config committed into the host repo so the
install is reproducible):

```bash
# from the host repo root
claude plugin marketplace add /path/to/.dev-knowledge --scope project
claude plugin install tier1-lifecycle@dev-knowledge-methodology --scope project
/reload-plugins        # in an interactive session, to activate
```

This writes to the host repo's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "dev-knowledge-methodology": {
      "source": { "source": "directory", "path": "/path/to/.dev-knowledge" }
    }
  },
  "enabledPlugins": { "tier1-lifecycle@dev-knowledge-methodology": true }
}
```

> If the host repo gitignores `.claude/` (e.g. `ai-council` does), this config is
> not committed by default. Either force-add it (`git add -f .claude/settings.json`)
> or keep the install local — decide per repo; do not silently override the repo's
> ignore intent.

## 2. Install the ruff lint gate (separate — pre-commit framework)

A CC plugin **cannot** ship a `.pre-commit-config.yaml`. Merge the pinned-rev stanza
in `assets/ruff-pre-commit.yaml` into the host repo's `.pre-commit-config.yaml`
(create the file with a `repos:` list if absent), then:

```bash
pre-commit install
```

## Verify

- `python "$CLAUDE_PLUGIN_ROOT/scripts/review_closures.py" surface` (with
  `CLAUDE_PROJECT_DIR` = host root) prints a summary when proposals exist, else silent.
- Stage a lint error and attempt a commit → the ruff gate blocks it.
- Make a `closes [#N]` commit for an open host item → the Stop hook proposes it next stop.
- `/review-closures` → human-gated close on the host backlog.
