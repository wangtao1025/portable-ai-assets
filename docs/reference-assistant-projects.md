# Assistant Projects / Custom GPTs Reference Review

Phase: 56  
Scope: Claude Projects, Custom GPTs, ChatGPT Projects, and similar hosted project-scoped assistant containers.  
Status: reviewed reference; not an implementation spec for a hosted assistant runtime.

## Why this reference matters

Hosted assistant project containers have converged around a useful product shape:

- a named project or assistant container
- project-scoped instructions
- project files / knowledge
- optional memory or personalization
- tools / actions / connectors
- sharing and visibility controls
- provider-hosted chat histories, retrieval indexes, and upload storage

This is close enough to Portable AI Assets that it is worth reviewing, but the boundary is important. Portable AI Assets should learn from the packaging and governance model without becoming another hosted assistant SaaS, RAG runtime, tool execution layer, or chat-history store.

## Systems reviewed

### Claude Projects

Public Claude Projects material describes projects as self-contained workspaces with their own chat histories and knowledge bases. A project can include uploaded documents, text, code, or other files as project knowledge, and can define project instructions that tailor Claude's responses. Paid plans can use enhanced project knowledge with retrieval augmented generation when content approaches context limits. Team and Enterprise sharing includes permission levels such as `Can use` and `Can edit`: users with use permission can see project contents, knowledge, and instructions and chat within the project; users with edit permission can modify project instructions/knowledge and manage members.

Portable AI Assets lesson: project instructions and curated knowledge-file manifests are portable asset concepts; provider-hosted chat histories, retrieval indexes, uploaded storage, and collaboration state are runtime/private state unless exported through a reviewed flow.

### Custom GPTs and GPT-style assistants

Custom GPT-style products commonly bundle instructions, knowledge files, capabilities/tools, and optional actions into a reusable assistant. They also create a sharp boundary between declarative assistant configuration and provider-hosted execution: custom actions require schemas/endpoints/credentials; knowledge retrieval is provider-managed; chats and memories are provider runtime data; sharing can be private, link/team/workspace scoped, or marketplace-like.

Portable AI Assets lesson: the declarative configuration is a useful adapter projection target, but credentials, connection strings, webhook URLs, uploaded file stores, retrieval chunks, embeddings, action execution logs, and conversation transcripts must not become public canonical assets.

### ChatGPT Projects and hosted project folders

ChatGPT Project-style containers group chats, files, and instructions around a task or workstream. They reinforce the same useful split: project-scoped context is durable enough to export or reconstruct, while the live conversation history and retrieval/cache implementation stay provider-hosted.

Portable AI Assets lesson: project scope, visibility, and asset membership should be recorded in manifests, but live chat history should not be treated as the canonical source of truth.

## What they do well

1. **Project-scoped packaging** — instructions, files, and chats are grouped by a named workstream rather than globally mixed.
2. **Instruction locality** — project instructions make intent explicit and lower the need for repeated prompting.
3. **Knowledge membership** — users can attach files or curated reference material to a project/assistant container.
4. **Permission vocabulary** — sharing models distinguish use/read from edit/manage permissions.
5. **Tool/action boundaries** — hosted products separate assistant configuration from external tool/action credentials and execution.
6. **Provider-managed retrieval** — large knowledge sets can be retrieved without forcing every user to manage a local vector stack.

## What Portable AI Assets should adopt

### Project pack vocabulary

Add or reuse manifest concepts for project-scoped asset packs:

- `project_id` or stable slug
- `display_name`
- `purpose`
- `instructions`
- `knowledge_sources`
- `visibility_scope`
- `permission_model`
- `target_runtimes`
- `adapter_projection`
- `source_provenance`
- `review_status`

The canonical asset should be the reviewed package definition, not the provider's live project object.

### Instruction / knowledge separation

Keep instructions separate from knowledge membership:

- instructions are prompt/policy assets
- knowledge files are source/reference assets
- retrieval indexes and chunks are rebuildable runtime cache
- uploaded provider storage is runtime/private state

This maps cleanly to existing Portable AI Assets layers: canonical Git assets, private asset root, non-Git backup, and runtime cache.

### Sharing and permission metadata

Hosted projects make permission intent visible. Portable AI Assets should preserve safe metadata such as:

- private / personal / team / organization visibility
- can-use vs can-edit style roles
- owner/reviewer identifiers redacted in public reports
- reviewed sharing state before projection into a hosted runtime

### Action/tool manifest boundaries

For Custom GPT-style actions and hosted tools, keep only declarative, redacted metadata in canonical assets:

- action name
- purpose
- OpenAPI/schema pointer if public-safe
- required capability class
- risk level
- credential reference name, not the credential value
- environment binding name, not the endpoint secret or token
- mutating/read-only classification

Execution remains outside Portable AI Assets unless a future connector has a separate reviewed apply gate.

### Import/export previews

A future hosted-project adapter should start with report-only behavior:

1. detect configured hosted project metadata export files or manually exported config
2. parse instructions, file lists, visibility, and action metadata without executing actions
3. redact identifiers and secrets
4. generate candidate project-pack manifests
5. require human review before canonical projection or runtime apply

## What Portable AI Assets should avoid

Portable AI Assets should not become:

- a hosted assistant SaaS
- a chat-history database
- a RAG/vector retrieval runtime
- a provider file-upload mirror
- a Custom GPT marketplace
- an action execution platform
- a generic webhook/API gateway
- a credential synchronization system
- a replacement for Claude Projects, ChatGPT Projects, or GPT builders

It should also avoid automatically importing:

- raw chat histories
- provider-hosted memories
- uploaded files without review
- generated retrieval chunks
- embeddings/vector indexes
- action execution logs
- OAuth tokens/API keys/secrets
- private webhook URLs or connection strings
- workspace/user/team identifiers in public reports

## Safe integration boundary

### Canonical / private asset candidates

These can be represented in canonical or private Portable AI Assets after review:

- project instructions
- project purpose/description
- curated knowledge source manifests
- public-safe file references
- project-pack membership metadata
- target-runtime projection metadata
- permission and visibility intent
- action/tool metadata with credential values removed
- migration notes and source provenance

### Runtime/private/backup-only state

These remain runtime/private or non-Git backup artifacts:

- chat histories and conversation transcripts
- uploaded provider storage
- hosted memories and personalization state
- RAG chunks, embeddings, indexes, and retrieval traces
- action/tool execution logs
- provider workspace IDs, user IDs, project IDs, and team IDs unless redacted
- credentials, tokens, API keys, OAuth refresh tokens, webhooks, and connection strings

### Rebuildable cache

These should be rebuildable from reviewed canonical/private assets and local/runtime configuration:

- retrieval indexes
- file chunks
- embedding stores
- search caches
- generated assistant/project runtime caches

## Suggested future schema/report implications

Do not implement a hosted assistant adapter yet. When needed, prefer these incremental steps:

1. `project-pack-manifest-v1` — project instructions, knowledge-source list, visibility, roles, and target projections.
2. `hosted-assistant-export-preview` — report-only parser for exported/declared assistant project configs.
3. `hosted-action-risk-inventory` — classify read-only vs mutating tools/actions and detect missing credential separation.
4. `project-pack-projection-preview` — show how a canonical project pack would project into Claude Projects, Custom GPTs, ChatGPT Projects, IDE rules, or local assistant runtimes.
5. Reviewed apply gates only after preview and redaction are reliable.

## Practical mapping to existing Portable AI Assets

| Hosted assistant concept | Portable AI Assets mapping | Git/public policy |
|---|---|---|
| Project instructions | canonical prompt/policy asset or project pack field | public-safe only if generic; private otherwise |
| Knowledge files | curated source manifest / private asset reference | file contents private unless deliberately public-safe |
| Project chat history | runtime history / non-Git backup | not canonical; not public |
| Provider RAG index | rebuildable runtime cache | never Git canonical |
| Custom actions/tools | declarative adapter/action metadata | no credentials; execution gated |
| Sharing settings | visibility/permission metadata | redact identities in public reports |
| Hosted memory | runtime/private candidate source | summarize only through reviewed import flow |

## Decision for Phase 56

Adopt the project-container vocabulary and permission/action boundaries, but keep Portable AI Assets above the hosted runtime layer. The next safe design move is not to build a hosted-project sync engine; it is to define project-pack manifests and preview-only imports/projections when a real need appears.
