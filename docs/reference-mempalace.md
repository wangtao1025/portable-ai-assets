# Reference: MemPalace and the OMX Bridge

This note captures lessons from the local MemPalace / OMX bridge setup so Portable AI Assets can absorb the useful architecture without becoming a runtime memory engine itself.

## What MemPalace contributes

MemPalace is best treated as a long-term memory core candidate: a runtime system that stores, retrieves, and organizes memory outside any single chat client.

Useful ideas to absorb:

- **Long-term memory as its own subsystem** — memory should survive model, client, and agent changes.
- **Bridge-based integration** — runtime tools can push/pull context through bridges instead of making one tool the only source of truth.
- **Corpus separation** — raw or indexed memory corpus belongs in runtime/backup layers, while curated summaries belong in the canonical asset layer.
- **Project/session summarization** — rolling session material can be summarized into stable project memory before it becomes canonical.
- **Runtime cache vs durable memory** — fast local cache and long-lived corpus are different layers and should not be collapsed.

## What Portable AI Assets should not copy

Portable AI Assets should not become MemPalace itself.

Avoid copying:

- runtime retrieval engine scope
- vector/index storage as Git-tracked data
- raw corpus mirroring into public or private Git
- automatic overwrite of agent instruction files based on memory retrieval
- tight coupling to one memory backend

## Integration stance

Recommended role split:

```text
MemPalace / memory backend
  -> stores and retrieves rich runtime memory
  -> owns raw corpus/index/runtime state

Portable AI Assets
  -> owns curated canonical summaries, schemas, adapters, review gates
  -> previews imports from memory backends
  -> exports reviewed portable assets into private Git
```

## Concrete design lessons for this repo

1. Keep `memory/summaries/mempalace-latest/` and raw bridge corpus outside public release artifacts.
2. Treat `stack/mcp/omx-mempalace-bridge.yaml` as a first-class portability asset.
3. Prefer bridge adapters over direct coupling to one memory runtime.
4. Preserve source/runtime separation: Git tracks durable summaries, not raw retrieval state.
5. Add external-reference inventory so new memory systems are reviewed explicitly instead of copied blindly.

## Current local anchors

Public-safe anchors only:

- `stack/tools/mempalace.yaml`
- `stack/mcp/omx-mempalace-bridge.yaml`
- `bootstrap/setup/refresh-mempalace-project-summaries.py`
- `bootstrap/setup/reinstall-omx-mempalace-bridge.sh`

Machine-local runtime paths such as `~/.mempalace-auto/bridge/corpus-live/` are backup/runtime state, not public source.
