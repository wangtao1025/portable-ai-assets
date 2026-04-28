<!-- Public snapshot notice: this is a static sanitized snapshot copied into a public artifact; it is not live GitHub state. Regenerate local report-only gates for current status. -->

# AI-Assets Adapter Connector Report

Generated: 2026-04-25T18:40:43
Engine root: `/Users/example/AI-Assets`
Asset root: `/Users/example/AI-Assets`
Config path: `/Users/example/.config/portable-ai-assets/config.yaml`
Schema dir: `/Users/example/AI-Assets/schemas`

## Summary

- Total adapters: 5
- Valid adapters: 5
- Invalid adapters: 0
- Runtimes: claude-code, codex, example-runtime, hermes, memos-local-plugin-hermes
- Import connectors: copy-file, read-file, sqlite-summary
- Export connectors: copy-file, manual-only, write-file

## Adapters

### claude-instructions

- runtime: claude-code
- path: `/Users/example/AI-Assets/adapters/registry/claude-instructions.yaml`
- schema: adapter-contract-v1
- valid: True
- apply_policy: human-review-required
- asset_class: public
- shareability: public-safe
- canonical_sources: adapters/claude/instructions.md
- live_targets: ~/.claude/CLAUDE.md
- connector.import: read-file
- connector.export: write-file
- errors: none

### codex-instructions

- runtime: codex
- path: `/Users/example/AI-Assets/adapters/registry/codex-instructions.yaml`
- schema: adapter-contract-v1
- valid: True
- apply_policy: human-review-required
- asset_class: public
- shareability: public-safe
- canonical_sources: adapters/codex/instructions.md
- live_targets: ~/.codex/AGENTS.md
- connector.import: read-file
- connector.export: write-file
- errors: none

### example-runtime-instructions

- runtime: example-runtime
- path: `/Users/example/AI-Assets/sample-assets/adapters/example-runtime/adapter.yaml`
- schema: adapter-contract-v1
- valid: True
- apply_policy: safe-auto-apply
- asset_class: public
- shareability: public-safe
- canonical_sources: sample-assets/adapters/example-runtime/canonical/instructions.md
- live_targets: /Users/example/.example-runtime/INSTRUCTIONS.md
- connector.import: copy-file
- connector.export: copy-file
- errors: none

### hermes-user-memory

- runtime: hermes
- path: `/Users/example/AI-Assets/adapters/registry/hermes-user-memory.yaml`
- schema: adapter-contract-v1
- valid: True
- apply_policy: human-review-required
- asset_class: public
- shareability: public-safe
- canonical_sources: adapters/hermes/USER.md
- live_targets: ~/.hermes/memories/USER.md
- connector.import: read-file
- connector.export: write-file
- errors: none

### memos-local-plugin-hermes-runtime-backend

- runtime: memos-local-plugin-hermes
- path: `/Users/example/AI-Assets/adapters/registry/memos-local-plugin-hermes.yaml`
- schema: adapter-contract-v1
- valid: True
- apply_policy: manual-only
- asset_class: public
- shareability: public-safe
- canonical_sources: memory/runtime-backends/memos-local-plugin.md
- live_targets: ~/.hermes/memos-plugin/config.yaml, ~/.hermes/memos-plugin/data/memos.db, ~/.hermes/memos-plugin/skills, ~/.hermes/memos-plugin/logs
- connector.import: sqlite-summary
- connector.export: manual-only
- errors: none

