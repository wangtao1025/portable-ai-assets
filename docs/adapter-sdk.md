# Adapter SDK

## Goal

Phase 13 introduces a minimal **adapter contract** so new runtimes can be added without hardcoding every integration into the bootstrap engine.

The SDK is intentionally small:
- declare canonical sources
- declare live runtime targets
- declare import/export connector types
- declare detection hints
- declare apply policy

This keeps the portability layer extensible without pretending every runtime can be migrated losslessly.

---

## Minimal contract

Adapter manifests use `adapter-contract-v1`.

Required fields:
- `name`
- `adapter_version`
- `runtime`
- `description`
- `canonical_sources`
- `live_targets`
- `connector`
- `detection`
- `apply_policy`

### `connector`
Current minimal shape:
- `import` — how live runtime state is read into a candidate view
- `export` — how canonical content is projected into a runtime view
- optional `notes`

Current connector names are descriptive labels, not executable plugins yet.
Examples:
- `read-file`
- `write-file`
- `copy-file`

### `detection`
Current minimal shape:
- `default_paths`
- optional `signature_markers`

### `apply_policy`
Allowed values:
- `safe-auto-apply`
- `human-review-required`
- `manual-only`

---

## Registry locations

Phase 13 currently recognizes adapter contracts in:
- `adapters/registry/*.yaml`
- `sample-assets/adapters/**/adapter.yaml`

This gives the project two layers:
1. real runtime adapter registry
2. public-safe sample adapters for open-source communication

---

## Current runtime adapters

Initial registry entries:
- `adapters/registry/hermes-user-memory.yaml`
- `adapters/registry/claude-instructions.yaml`
- `adapters/registry/codex-instructions.yaml`

Public-safe example:
- `sample-assets/adapters/example-runtime/adapter.yaml`

---

## Bootstrap support

New report modes:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --connectors --both
./bootstrap/setup/bootstrap-ai-assets.sh --connector-preview --both
./bootstrap/setup/bootstrap-ai-assets.sh --redacted-examples --both
```

These generate:
- `bootstrap/reports/latest-connectors.json`
- `bootstrap/reports/latest-connectors.md`
- `bootstrap/reports/latest-connector-preview.json`
- `bootstrap/reports/latest-connector-preview.md`
- `bootstrap/reports/latest-redacted-examples.json`
- `bootstrap/reports/latest-redacted-examples.md`

The connector report shows:
- total adapters
- valid vs invalid adapters
- runtimes represented
- import/export connector inventory
- per-adapter apply policy and shareability

The connector preview report adds:
- built-in action previews for `read-file`, `write-file`, and `copy-file`
- source/target resolution
- bytes available from the source side
- zero-write execution previews for safer inspection

The redacted-examples mode writes public-safe walkthrough artifacts into:
- `examples/redacted/connector-walkthrough.example.md`
- `examples/redacted/connector-summary.example.json`

---

## Design constraints

This is a **metadata-first SDK**, not a full plugin execution runtime.

That means Phase 13 currently provides:
- a standard contract
- registry discovery
- schema validation
- inventory/reporting
- public-safe examples

It does **not yet** provide:
- executable connector plugins
- arbitrary code loading from adapter manifests
- semantic import/export transforms for every runtime
- universal migration guarantees

That restraint is intentional.

---

## How to add a new runtime adapter

1. Copy `sample-assets/adapters/example-runtime/adapter.yaml`
2. Create a real manifest under `adapters/registry/`
3. Point `canonical_sources` at canonical repo assets
4. Point `live_targets` at the runtime surface
5. Pick conservative connector labels
6. Mark high-risk targets as `human-review-required`
7. Run:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --validate-schemas --both
./bootstrap/setup/bootstrap-ai-assets.sh --connectors --both
```

If the adapter appears in the connector report and validates cleanly, it is registered at the metadata layer.
