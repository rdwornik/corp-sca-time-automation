# Tenrox migration — Step 0 reconciliation note

**Date:** 2026-07-05 · **Branch:** `feature/tenrox-loader` · **Baseline:** `python -m pytest` → 69 passed, 1 skipped (clean tree on `main` @ 2fb2627)

Reality check performed before any Tenrox work, per mission Step 0. Disk state is the authority.

## Findings

| Claim | Reality on disk | Verdict |
|---|---|---|
| Handoff: repo at `Documents\Scripts\sca-time-automation` | Path does not exist; repo is `Documents\Dev\corp-sca-time-automation` | Handoff stale |
| Handoff: `src/sca_time_automation/loaders/`, root `run.py` | Flat `src/` (15 modules, no subpackages); CLI is `scripts/run.py` with subcommands `export / preview / status / upload / report / catchup` | Handoff stale; **ARCHITECTURE.md is current** |
| Handoff §4 business rules | Handoff file intentionally off-repo; §4 rules delivered by operator in-session. Durable in-repo form will be `config/tenrox_mapping.yaml` (mission Step 3) — that config is the source of truth going forward | No repo action |
| `last_sunday()` "known Sunday edge-case open item" | `last_sunday()` on a Sunday returns the same day; regression test `test_sunday_returns_same_day` already exists (`tests/test_date_utils.py:10`). Not in BACKLOG | Claim stale; coverage exists |
| Calendar export freshness | `data/input/calendar_export.json` covers 2026-01-26 → 2026-03-27 (222 events); zero events on/after 2026-06-21 — week 2026-06-28 NOT covered | Fresh export required at Step 6 |
| Upload target | `src/sharepoint.py` (Graph API) is the only outbound surface; upload driven from `scripts/run.py cmd_upload` reading the preview Excel; idempotency via `is_week_uploaded()` | As documented |

## Verified CLI syntax (actual)

`python scripts/run.py export [--run] [--weeks N]` · `preview [--no-ai] [--weeks N]` · `upload [week YYYY-MM-DD | --latest | --all] [--force]` · `status` · `report [--weeks N]` · `catchup [--no-ai] [--dry-run] [--max-weeks N]`

## Consequences for this mission

- TenroxLoader lands as flat `src/tenrox.py` (mirroring `sharepoint.py`'s public surface), dispatched from `cmd_upload` behind a `loader.target` config switch. `src/loader.py` name is taken (calendar loader).
- Preview rows are per-event (aggregator sorts, does not sum), so per-day dates thread through additively (operator decision: actual event days).
- Docs-fix queue item: none needed for ARCHITECTURE.md (current); BACKLOG gets a handoff-trail note instead (mission Final step).
