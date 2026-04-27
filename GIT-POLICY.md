# Git Policy for AI-Assets

Updated: 2026-04-23

## Commit to Git

These are the durable, portable assets that should normally be versioned:

- `README.md`
- `memory/profile/` canonical summaries
- `memory/projects/` canonical summaries
- `memory/EXPORTS.md`
- `adapters/`
- `capabilities/`
- `stack/`
- `bootstrap/checks/`
- `bootstrap/setup/` scripts
- `bootstrap/install/` scripts

## Do not commit by default

These should be backed up elsewhere or regenerated locally:

- `memory/summaries/mempalace-latest/` raw snapshot copies
- `bootstrap/backups/`
- runtime logs
- caches
- indexes
- database files
- copied secrets / tokens / credential files

## Why raw MemPalace latest snapshots are ignored

They are useful for local forensics and refresh workflows, but they are closer to runtime dump material than to a clean portable source of truth. The canonical cleaned summaries under `memory/projects/` should be the Git-tracked layer.

## Backup strategy

Use Git for the text-first canonical layer, and use separate backup/storage for:

- `~/.hermes/state.db`
- `~/.claude/history.jsonl`
- `~/.codex/history.jsonl`
- `~/.mempalace-auto/bridge/corpus-live`
- any future local databases or vector indexes

## Recovery strategy

1. Restore this Git repo.
2. Restore large non-Git backups if available.
3. Reinstall runtimes and workflow layers.
4. Reinstall bridges and sync adapters.
5. Rebuild local caches and indexes.
