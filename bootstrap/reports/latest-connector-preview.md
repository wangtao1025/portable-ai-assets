<!-- Public snapshot notice: this is a static sanitized snapshot copied into a public artifact; it is not live GitHub state. Regenerate local report-only gates for current status. -->

# AI-Assets Connector Preview Report

Generated: 2026-04-25T18:40:44
Engine root: `/Users/example/AI-Assets`
Asset root: `/Users/example/AI-Assets`
Config path: `/Users/example/.config/portable-ai-assets/config.yaml`

## Summary

- Previewable adapters: 5
- Runtimes: claude-code, codex, example-runtime, hermes, memos-local-plugin-hermes

## Actions

### claude-instructions

- export: write-file (preview)
  - source: `/Users/example/AI-Assets/adapters/claude/instructions.md`
  - target: `/Users/example/.claude/CLAUDE.md`
  - source_exists: True
  - bytes_available: 1243
  - description: Would project canonical content into the live runtime target without executing writes in preview mode.
- import: read-file (preview)
  - source: `/Users/example/.claude/CLAUDE.md`
  - target: `/Users/example/AI-Assets/adapters/claude/instructions.md`
  - source_exists: True
  - bytes_available: 3462
  - description: Would read the live runtime target into a candidate view without modifying files.

### codex-instructions

- export: write-file (preview)
  - source: `/Users/example/AI-Assets/adapters/codex/instructions.md`
  - target: `/Users/example/.codex/AGENTS.md`
  - source_exists: True
  - bytes_available: 1330
  - description: Would project canonical content into the live runtime target without executing writes in preview mode.
- import: read-file (preview)
  - source: `/Users/example/.codex/AGENTS.md`
  - target: `/Users/example/AI-Assets/adapters/codex/instructions.md`
  - source_exists: True
  - bytes_available: 29557
  - description: Would read the live runtime target into a candidate view without modifying files.

### example-runtime-instructions

- export: copy-file (preview)
  - source: `/Users/example/AI-Assets/sample-assets/adapters/example-runtime/canonical/instructions.md`
  - target: `/Users/example/.example-runtime/INSTRUCTIONS.md`
  - source_exists: True
  - bytes_available: 252
  - description: Would copy bytes from source to target, but preview mode only reports the action.
- import: copy-file (preview)
  - source: `/Users/example/.example-runtime/INSTRUCTIONS.md`
  - target: `/Users/example/AI-Assets/sample-assets/adapters/example-runtime/canonical/instructions.md`
  - source_exists: False
  - bytes_available: 0
  - description: Would copy bytes from source to target, but preview mode only reports the action.

### hermes-user-memory

- export: write-file (preview)
  - source: `/Users/example/AI-Assets/adapters/hermes/USER.md`
  - target: `/Users/example/.hermes/memories/USER.md`
  - source_exists: True
  - bytes_available: 603
  - description: Would project canonical content into the live runtime target without executing writes in preview mode.
- import: read-file (preview)
  - source: `/Users/example/.hermes/memories/USER.md`
  - target: `/Users/example/AI-Assets/adapters/hermes/USER.md`
  - source_exists: True
  - bytes_available: 1376
  - description: Would read the live runtime target into a candidate view without modifying files.

### memos-local-plugin-hermes-runtime-backend

- export: manual-only (preview)
  - source: `/Users/example/AI-Assets/memory/runtime-backends/memos-local-plugin.md`
  - target: `/Users/example/.hermes/memos-plugin/config.yaml`
  - source_exists: True
  - bytes_available: 1817
  - description: Unknown connector type; preview mode reports metadata only.
- import: sqlite-summary (preview)
  - source: `/Users/example/.hermes/memos-plugin/config.yaml`
  - target: `/Users/example/AI-Assets/memory/runtime-backends/memos-local-plugin.md`
  - source_exists: False
  - bytes_available: 0
  - description: Unknown connector type; preview mode reports metadata only.

