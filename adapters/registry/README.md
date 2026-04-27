# Adapter Registry

This directory holds the real adapter contract manifests used by the bootstrap engine.

Current scope:
- Hermes user memory adapter
- Claude instruction adapter
- Codex instruction adapter

These manifests describe:
- canonical sources
- live runtime targets
- connector labels
- detection hints
- apply policy

They are metadata contracts for discovery, validation, and reporting.
They are not yet executable plugin modules.
