# Adapter layer

This directory describes the per-agent projection files that sit on top of the canonical memory and capability layers.

## Discovered adapter surfaces

### Hermes
- `~/.hermes/memories/USER.md`
- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/config.yaml`

### Claude Code
- `~/.claude/CLAUDE.md`
- `~/.claude/settings.json`
- `~/.claude/config.json`
- `~/.claude/settings.local.json`

### Codex / OMX
- `~/.codex/AGENTS.md`
- `~/.codex/hooks.json`
- `~/.codex/rules/default.rules`
- `~/.codex/skills/`
- `~/.codex/agents/`

## Design rule

These files are not the only truth.
They are the agent-specific views and runtime contracts.

Long term, generate or at least reconcile them from canonical data in:

- `../memory/`
- `../capabilities/`
- `../stack/manifest.yaml`
- `./registry/` adapter contract manifests

## Immediate practical goal

When moving to a new machine, restoring these adapter files should be an explicit bootstrap step rather than an implicit hope.
