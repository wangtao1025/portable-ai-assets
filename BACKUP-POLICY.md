# Non-Git Backup Policy

Updated: 2026-04-23

This document covers large, runtime-derived, or database-backed assets that should **not** live in the Git-tracked canonical layer but still need to survive machine changes.

## Why a separate backup layer exists

Git is the right home for:

- canonical text summaries
- adapter views
- manifests
- scripts
- architecture notes

Git is **not** the ideal home for:

- raw session archives
- local SQLite databases
- high-volume JSONL histories
- bridge corpus dumps
- runtime caches and database sidecars

## Current high-value backup targets on this machine

- `~/.hermes/state.db`
- `~/.hermes/sessions/`
- `~/.claude/history.jsonl`
- `~/.claude/projects/`
- `~/.codex/history.jsonl`
- `~/.codex/sessions/`
- `~/.mempalace-auto/bridge/corpus-live/`

See `stack/backup-manifest.yaml` for the normalized inventory.

## Backup tiers

### Tier 1 — must preserve

These are the most valuable non-Git assets:

- `~/.hermes/state.db`
- `~/.hermes/sessions/`
- `~/.codex/sessions/`
- `~/.mempalace-auto/bridge/corpus-live/`

### Tier 2 — good to preserve

- `~/.claude/history.jsonl`
- `~/.claude/projects/`
- `~/.codex/history.jsonl`

## Recommended storage destinations

Use one of these outside Git:

- encrypted external drive
- private cloud drive with local encryption
- NAS / private synced folder

## Restore order

1. Restore `AI-Assets` Git repo.
2. Restore non-Git backup archives from this policy.
3. Reinstall runtimes if needed.
4. Restore bridges/hooks.
5. Run refresh/export scripts to regenerate canonical summaries.
