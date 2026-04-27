# Changelog

## v0.1.0 — Prototype release candidate

### Added

- Portable AI Assets bootstrap engine with inspect, plan, diff, review/apply, and release-pack workflows.
- JSON schemas for stack, tool, bridge, architecture-note, adapter-contract, and portable-skill manifests.
- Adapter registry and connector inventory / preview reports.
- Public-safe sample assets, redacted examples, demo pack, release pack, archive, and smoke test gates.
- MemOS/Hermes adoption planning with read-only health/import preview and reviewed skill candidate flows.

### Security

- Public/private/secret asset boundary documented.
- Release safety scans check for secret-like strings and private absolute paths.
- Runtime DBs/logs/candidates/backups stay outside public release packs.
