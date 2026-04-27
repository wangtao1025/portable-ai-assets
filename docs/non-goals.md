# Non-Goals

This project is intentionally **not** trying to do everything in the AI tooling stack.

## Not a new agent runtime

Portable AI Assets does not aim to replace:
- Hermes
- Claude Code
- Codex
- MemPalace
- MCP hosts
- local model runners

It sits above them as a portability layer.

---

## Not a universal memory backend

The goal is not to declare one database or one vector store as the only valid memory system.

Instead, the goal is to:
- preserve durable user value
- summarize and normalize key memory artifacts
- adapt those assets into multiple runtimes safely

---

## Not lossless migration for every tool

Some runtime state is inherently lossy, version-specific, or private.

This project does not promise:
- perfect round-trip conversion for every runtime
- one-click migration for every future agent
- automatic semantic merge for every drifted file

When ambiguity is high, human review is the feature, not a failure.

---

## Not a secret-sync system

This repo should not become the place where personal tokens, credentials, or auth files are spread across machines.

Secret handling must remain separate from public-safe canonical assets.

---

## Not a giant prompt dump

The canonical layer should stay structured and intentional.

This project is not trying to accumulate every raw session transcript or every runtime artifact in Git.

Git should mainly hold:
- summaries
- manifests
- schemas
- adapter sources
- docs
- scripts

---

## Not an excuse to overwrite local state

Bootstrap is discovery-first.

The system should not assume:
- the machine is fresh
- the local runtime is unmanaged
- the canonical file is always newer
- overwrite is safe just because hashes differ

Drift awareness and review-before-apply are core constraints.

---

## Not tied to a single vendor or model family

The project should remain useful even as:
- file locations change
- vendors rename products
- models are swapped out
- local and remote runtimes coexist

The durable value is the asset model and reconciliation workflow, not loyalty to one platform.
