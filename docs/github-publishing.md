# GitHub Publishing Draft

## Repository description

Portable AI Assets is a cross-agent continuity layer for owning AI memory, skills, adapters, schemas, and migration workflows outside any single runtime.

## Suggested topics

- ai-agents
- ai-memory
- mcp
- local-first
- agentic-workflows
- ai-portability
- developer-tools
- personal-knowledge-management
- schemas
- automation

## Suggested tagline

Own your AI assets — memory, skills, adapters, and workflows — across agents, machines, and runtimes.

## Publish checklist

1. Run `--public-safety-scan --both`.
2. Run `--release-readiness --both`.
3. Run `--public-release-pack --both`.
4. Run `--public-release-archive --both`.
5. Run `--public-release-smoke-test --both`.
6. Review `MANIFEST.json`, `CHECKSUMS.sha256`, `CHANGELOG.md`, and `RELEASE_NOTES-v0.1.md`.
7. If `wangtao1025/portable-ai-assets` already exists, treat this as an existing public repository update: review the sanitized tree, use a temporary remote only for an owner-approved public `main` sync, remove the remote immediately after push, and keep tag/release decisions separate.
8. Never auto-push private memory, runtime state, backups, candidates, machine-local config, or secrets.
