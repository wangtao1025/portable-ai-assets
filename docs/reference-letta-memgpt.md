# Reference: Letta / MemGPT

This note captures lessons from Letta, formerly MemGPT, for Portable AI Assets. The goal is to absorb mature agent-memory architecture patterns without turning Portable AI Assets into another stateful agent runtime.

Sources reviewed for this initial reference:

- Letta public repository README and package metadata.
- Public Letta schema/code surfaces around agent state, memory blocks, archival passages, archives, and git-backed memory repositories.
- Previously known MemGPT design concepts: core memory, recall memory, archival memory, self-editing memory tools, and context-window management.

This is a reference review, not an integration. No Letta server, CLI, cloud API, or local runtime was installed or enabled.

## What Letta / MemGPT does well

Letta is a stateful agent runtime with explicit long-term memory primitives. It treats the agent as something with persisted state, model/tool configuration, attached data, and memory that can be read and changed over time.

Useful architectural patterns:

- **Core memory blocks** — small, in-context labeled blocks such as `human` and `persona` give the agent durable high-salience context while staying within a character/token budget.
- **Archival memory** — larger facts and documents are stored outside the active context window as searchable passages associated with archives, embeddings, files, tags, and metadata.
- **Recall / conversation memory** — message history and summaries help the agent remember interaction history without keeping every raw turn in active context.
- **Context-window accounting** — the runtime tracks how much context is used by system prompt, core memory, summaries, external memory metadata, files, tools, and conversation messages.
- **Memory as structured state** — blocks, archives, passages, tools, sources, identities, groups, files, secrets, and agent settings are separate entities rather than one undifferentiated prompt blob.
- **Agent-editable memory with boundaries** — memory can be updated through tools/APIs, but blocks may be read-only, limited, labeled, or hidden.
- **Shared archives** — archival collections can be shared across agents, which separates reusable knowledge from one agent's local short-term state.
- **Git-backed memory direction** — Letta has code paths for git-enabled memory repositories where writes can go to a versioned source of truth and database state can act as a cache.

## Concepts Portable AI Assets should adopt

Portable AI Assets should adapt the following concepts at the metadata/canonical layer:

1. **Memory tier vocabulary**
   - `core` / high-salience profile facts
   - `recall` / conversation or session summaries
   - `archival` / larger reference corpus summaries
   - `procedural` / skills and playbooks
   - `runtime-cache` / vector indexes, DB rows, and fast retrieval surfaces that are not canonical Git assets

2. **Labeled blocks, not one giant memory file**
   Canonical memory and adapter projections should preserve labels such as `human`, `persona`, `project`, `preference`, `policy`, `skill`, and `source` so runtimes can project only the right pieces into active context.

3. **Character/token budgets as metadata**
   Adapter contracts should eventually record budget hints for projected memory blocks. A Hermes/Claude/Codex adapter may need a short profile block, while a retrieval backend may accept larger archival summaries.

4. **External memory summary reports**
   Reports should show what was included from runtime memory, what stayed external, and how many blocks/passages/summaries were available. This mirrors Letta's context overview without copying its runtime.

5. **Shared archive boundary**
   The Portable AI Assets equivalent of an archive should be a curated, reviewed corpus summary or source manifest, not raw embedded passages. The raw archive/index remains in runtime/backup storage.

6. **Versioned memory is valuable, but review gates matter**
   Letta's git-backed memory direction validates this repo's public-engine/private-assets split. Portable AI Assets should keep using Git for reviewed canonical assets, while runtime DBs stay cache/state.

## Concepts Portable AI Assets should avoid

Portable AI Assets should not copy Letta's product/runtime scope.

Avoid:

- becoming a live agent server or stateful conversation API;
- replacing Letta/MemGPT-style runtime memory tools;
- storing raw message history, embeddings, vector indexes, or database passages directly in Git;
- letting an agent autonomously rewrite canonical memory without preview/review/apply gates;
- treating cloud API state, secrets, tool credentials, or sandbox credentials as portable public assets;
- making one runtime's memory schema the only canonical format;
- assuming all memory should be in active context instead of separated by tier and budget.

## Safe integration boundary

Recommended role split:

```text
Letta / MemGPT runtime
  -> owns stateful agent execution, tools, message buffers, runtime DB/cache, embeddings, archives, and recall/search behavior
  -> may export blocks, archive summaries, message summaries, or agent-state metadata

Portable AI Assets
  -> owns reviewed canonical memory, portable skill manifests, adapter contracts, public-safe examples, provenance, and release gates
  -> imports Letta-derived data only through preview/candidate/review/apply flows
  -> exports adapter projections only after human review where runtime overwrite risk exists
```

A future Letta adapter should be read-only first:

1. discover Letta config/database/export paths;
2. summarize agent memory blocks and archive metadata without extracting secrets;
3. generate import preview reports and candidate canonical summaries;
4. require reviewed files before writing `memory/`, `skills/`, or adapter projections;
5. never write back into a Letta runtime unless a separate reviewed apply mode is explicitly designed.

## Implications for Portable AI Assets

### Schema implications

Possible future schema additions, after more upstream verification:

- Add optional `memory_tier` to canonical memory note metadata: `core`, `recall`, `archival`, `procedural`, `runtime-cache`.
- Add optional `block_label`, `budget_hint`, and `projection_priority` to adapter/source metadata.
- Add an `external_archive` source type for curated summaries of large runtime corpora.
- Extend portable skill manifests with evidence/trial metadata rather than copying agent-generated procedures directly.

No schema change is required in this phase; this review is advisory and backlog-driven.

### Adapter implications

A future `letta-runtime` adapter should be metadata-first and preview-only initially:

- `connector.import`: `letta-export-summary` or `sqlite-summary` if a local DB layout is stable and public.
- `connector.export`: `manual-only` until write-back semantics are safe.
- `apply_policy`: `manual-only` or `human-review-required`.
- `shareability`: public-safe only for sample adapters, never for real user memory blocks.

### Report implications

Reference and import reports should include:

- number of core memory blocks discovered;
- labels and character sizes, with values redacted or summarized where sensitive;
- archival collection/passages counts, not raw embeddings;
- recall/message summary counts, not raw conversation logs by default;
- explicit list of raw/runtime data excluded from Git.

## Raw/runtime data that must remain outside Git

Keep these outside both public release artifacts and private canonical Git unless explicitly summarized and reviewed:

- Letta databases, caches, embeddings, and vector indexes;
- raw passages and raw archive exports;
- raw message history and conversation logs;
- tool execution traces, sandbox outputs, telemetry, and credentials;
- API keys, cloud identifiers, secrets, tokens, and connection strings.

Git may contain public-safe sample adapter contracts and private reviewed summaries, but not raw runtime stores.

## Concrete design lessons for this repo

1. Keep `memory/profile/` close to Letta-style core memory: small, labeled, high-salience, and budget-aware.
2. Keep `memory/projects/` and curated source summaries close to archival memory: durable but not always projected into every prompt.
3. Treat `bootstrap/reports/*` as the equivalent of context/memory overview reports: they explain what exists and what was excluded.
4. Keep `skills/` as procedural memory with lifecycle metadata, not arbitrary executable plugins.
5. Prefer future read-only Letta import previews over immediate bidirectional sync.
6. Consider adding memory tier metadata after at least one more external reference review confirms the same taxonomy pressure.

## Current decision

Letta / MemGPT is marked as reviewed for architecture reference purposes.

Adopt now:

- memory tier vocabulary in docs;
- labeled block thinking for adapter projections;
- report language around core/recall/archival/runtime-cache boundaries;
- validation of Git-backed canonical memory as a separate reviewed layer.

Defer:

- any Letta runtime adapter implementation;
- schema changes until another reference review or concrete import/export need confirms the fields;
- any write-back or live sync into Letta-managed state.
