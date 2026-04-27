# Redacted Connector Walkthrough

This is a public-safe example generated from the latest connector inventory.

## Summary

- total_adapters: 5
- runtimes: claude-code, codex, example-runtime, hermes, memos-local-plugin-hermes
- export_connectors: copy-file, manual-only, write-file

## Adapters

### claude-instructions

- runtime: claude-code
- apply_policy: human-review-required
- shareability: public-safe
- connector.import: read-file
- connector.export: write-file
- canonical_sources: adapters/claude/instructions.md
- live_targets: ~/.claude/CLAUDE.md

### codex-instructions

- runtime: codex
- apply_policy: human-review-required
- shareability: public-safe
- connector.import: read-file
- connector.export: write-file
- canonical_sources: adapters/codex/instructions.md
- live_targets: ~/.codex/AGENTS.md

### example-runtime-instructions

- runtime: example-runtime
- apply_policy: safe-auto-apply
- shareability: public-safe
- connector.import: copy-file
- connector.export: copy-file
- canonical_sources: sample-assets/adapters/example-runtime/canonical/instructions.md
- live_targets: /Users/example/.example-runtime/INSTRUCTIONS.md

### hermes-user-memory

- runtime: hermes
- apply_policy: human-review-required
- shareability: public-safe
- connector.import: read-file
- connector.export: write-file
- canonical_sources: adapters/hermes/USER.md
- live_targets: ~/.hermes/memories/USER.md

### memos-local-plugin-hermes-runtime-backend

- runtime: memos-local-plugin-hermes
- apply_policy: manual-only
- shareability: public-safe
- connector.import: sqlite-summary
- connector.export: manual-only
- canonical_sources: memory/runtime-backends/memos-local-plugin.md
- live_targets: ~/.hermes/memos-plugin/config.yaml, ~/.hermes/memos-plugin/data/memos.db, ~/.hermes/memos-plugin/skills, ~/.hermes/memos-plugin/logs

