# External Reference Strategy

Portable AI Assets should not evolve in isolation. It should continuously study adjacent memory systems, runtime plugins, bridge layers, and agent frameworks, then absorb only the parts that strengthen the portability layer.

## Principle

```text
Learn from external systems, but do not copy their product scope.
```

Portable AI Assets is a canonical asset / adapter / review layer. External memory backends such as MemOS plugins or MemPalace are runtime systems that can feed it, but they should not replace its source-of-truth model.

## Review workflow for external systems

1. Identify the external system and its scope.
2. Classify it as one or more of:
   - runtime memory backend
   - bridge / adapter layer
   - workflow orchestrator
   - prompt / skill system
   - storage / retrieval engine
   - public release / packaging inspiration
3. Extract:
   - ideas to adopt
   - ideas not to adopt
   - integration boundary
   - canonical asset implications
4. Write a `docs/reference-<system>.md` note.
5. Update schemas/adapters/docs only after review.
6. Keep raw runtime data and secrets out of Git and public release packs.
7. Use the `reference_intake_radar` in `--external-reference-backlog` to keep a public-safe queue of next review lanes before inventing new asset classes.

## Reference intake radar

The radar is a report-only discovery surface. It is generated from local docs/backlog state and recommends candidate review lanes; it does **not** research, clone, download, authenticate, call providers/APIs, execute tools, or write runtime/admin/provider/credential state.

Current lanes to evaluate next:

- coding-agent workspace portability: Continue.dev, Cline, Roo Code, Aider, OpenHands (reviewed in Phase 70)
- agent workflow and skill registries: CrewAI, AutoGen, Semantic Kernel, Anthropic Agent Skills, LangGraph (reviewed in Phase 73)
- reproducible environment portability: Nix flakes, Dev Containers, Home Manager, chezmoi, yadm (reviewed in Phase 74)
- supply-chain provenance and release evidence: Sigstore, SLSA, in-toto, CycloneDX, SPDX (reviewed in Phase 75)
- declarative desired-state reconciliation: Kubernetes CRD, GitOps, Argo CD, Flux (reviewed in Phase 76)

Promote one lane at a time from `candidate` to `queued`, write a `docs/reference-*.md` review, then decide what to adopt or avoid. When all current high-priority lanes are reviewed, treat an empty radar as healthy coverage rather than a request to invent runtime scope.

## Current references

- `docs/reference-memos-local-plugin.md`
- `docs/reference-mempalace.md`
- `docs/reference-letta-memgpt.md`
- `docs/reference-openmemory.md`
- `docs/reference-mcp-memory-servers.md`
- `docs/reference-supermemory.md`
- `docs/reference-langgraph-memory.md`
- `docs/reference-open-webui-memory.md`
- `docs/reference-workflow-builders.md`
- `docs/reference-ide-project-memory.md`
- `docs/reference-assistant-projects.md`
- `docs/reference-hosted-agent-workspace-governance.md`
- `docs/reference-coding-agent-workspace-portability.md`
- `docs/reference-agent-workflow-skill-registries.md`
- `docs/reference-reproducible-environment-portability.md`
- `docs/reference-supply-chain-provenance.md`
- `docs/reference-declarative-desired-state.md`
- `docs/reference-capability-risk-policy-gates.md`

## What to absorb from current references

### From MemOS local plugin

- lifecycle-aware skills
- runtime memory taxonomy
- adapter contracts
- observability mindset
- source/runtime separation

### From MemPalace / OMX bridge

- memory backend as an independent long-term system
- bridge-based integration
- raw corpus vs curated canonical summaries
- runtime cache vs durable memory separation
- external memory imports should pass through preview/review gates

### From Letta / MemGPT

- explicit memory tiers such as core, recall, archival, procedural, and runtime cache
- labeled memory blocks and budget-aware adapter projections
- runtime-owned messages/passages/embeddings should be summarized through preview/review gates, not mirrored into Git

### From OpenMemory-style shared memory services

- app/client-scoped memory and visibility boundaries
- memory lifecycle vocabulary such as active, paused, archived, deleted, probationary, and retired
- MCP-first memory service surfaces as integration boundaries
- explainable reports with categories, access summaries, and backup/health posture without raw runtime dumps

### From MCP memory servers

- MCP is a useful protocol boundary for memory tools, but tool risk must be classified before any automated use
- read/search/context tools should be separated from write/update/delete/admin tools
- server detection and tool inventory should be possible without starting arbitrary commands by default
- runtime storage diversity (JSONL, file banks, SQLite/FTS, vector stores, managed services) should collapse into reviewed canonical candidates, not raw Git mirrors

### From Supermemory-style managed memory platforms

- source-scope metadata should distinguish user, project, team, client, plugin, and container-tag boundaries
- profile projection should separate stable facts, recent activity, relevant memory, and project knowledge with explicit budgets
- memory relations such as updates, extends, and derives are useful for review of contradictions and superseded facts
- MCP/plugin tools need risk classification: read/search/context/list differs from save/forget/config mutation
- benchmark-minded evaluation should eventually test update handling, recall quality, redaction, and projection safety

### From LangGraph / LangChain memory patterns

- short-term thread/workflow state and long-term cross-thread memory should be separated explicitly
- graph checkpoints, pending writes, replay histories, traces, and state snapshots are runtime artifacts, not canonical Git memory
- semantic, episodic, and procedural memory taxonomy can help route facts, examples, and procedures into different candidate/review flows
- namespaces are useful for user/project/team/workflow scoping, but identifiers must be redacted in public reports
- hot-path agent writes and background memory extraction need provenance labels and should default to review before canonical projection

### From Open WebUI / local assistant memory

- local-first assistant runtimes make data-root, DB, upload, vector-index, and storage-provider boundaries concrete and inspectable
- personal memory, knowledge bases, uploaded documents, RAG chunks, embeddings, and runtime config should be separate asset classes
- vector collections and embeddings are rebuildable runtime caches; relational/source rows or reviewed summaries are the candidate source
- permission and visibility metadata such as personal, group, admin, or instance-shared should be preserved for private review but redacted in public reports
- future adapters should inventory Open WebUI DB/storage/vector metadata read-only and generate candidates only after human visibility review

### From Dify / Flowise / Langflow workflow builders

- visual workflow graphs are durable AI assets, but runtime deployments, traces, conversations, credentials, datasets, and vector indexes are separate runtime/binding layers
- workflow manifests should capture graph structure, prompts, variables, inputs/outputs, model/tool/RAG references, visibility, and deployment exposure without embedding secrets
- workflow review needs semantic graph diffs: node changes, prompt changes, provider/model changes, tool risk changes, RAG source changes, and deployment exposure changes
- environment bindings for provider keys, endpoints, vector DBs, webhooks, and credential refs should be separate local/team-private assets
- custom components, code nodes, HTTP/webhook nodes, tool nodes, and MCP servers should be classified separately from declarative prompt/model nodes

### From IDE assistant project memory

- repo-local instruction files and rule directories are durable AI assets and should project from canonical project-rule manifests
- rule metadata such as globs, always-apply/manual invocation, description, priority, language/toolchain, and target runtime is important for safe adapter projection
- generated or imported IDE memories/rules should carry provenance and default to review-required before becoming canonical project facts
- IDE code indexes, embeddings, chats, telemetry, terminal logs, and workspace caches are runtime/cache/backup state, not Git canonical memory
- projection previews should detect conflicts across `.cursor/rules`, `.rules`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and Copilot instruction surfaces before writing

### From coding-agent workspace portability

- coding-agent workspaces need reviewed workspace packs that separate project instructions, role profiles, task handoffs, test/build commands, tool permissions, and environment expectations
- Continue.dev/Cline/Roo/Aider/OpenHands-style surfaces validate role-specific projections and task handoff candidates, but live planning, edits, terminals, browsers, MCP calls, sandboxes, and model calls remain runtime responsibilities
- projection previews should report capability deltas before any write: file writes, shell/code execution, network/browser access, MCP/tool bindings, credentials, scheduled/background behavior, and auto-commit/push posture
- raw chats, terminal/browser traces, code indexes, repo maps, embeddings, generated diffs, credentials, provider endpoints, and sandbox state are runtime/cache/backup artifacts, not public Git canonical assets
- future adapters should be read-only inventory first, generate reviewed workspace-pack candidates, run instruction conflict/capability checks, and only then allow narrow reviewed writes to agent-specific instruction surfaces

### From agent workflow and skill registries

- agent/skill/task packages need manifest-first metadata: name, description, trigger, role/goal, inputs, expected outputs, linked resources, lifecycle status, review status, provenance, and target runtime projections
- progressive disclosure is useful for large skill bundles: keep the manifest small and load linked references/templates/examples only when review or projection needs them
- capability declarations must precede projection: text-only, read-only data, file writes, network/API/webhook, code/shell execution, credential binding, admin/provider control, scheduled/background behavior, and delegation should be visible before any apply
- runtime artifacts such as conversations, team messages, traces, checkpoints, thread state, execution logs, provider bindings, and tool outputs are not canonical Git assets
- future registries should inventory and preview skills/roles/tasks/workflows without starting runtimes, executing tools, calling providers, authenticating, or syncing packages automatically

### From reproducible environment portability

- portable environment descriptors should be manifest-first and may record lock/provenance evidence, but lock data is audit metadata rather than permission to fetch, build, install, or activate anything
- Dev Containers-style schema and namespaced customization patterns are useful for cross-tool interoperability, while container build/run, lifecycle commands, mounts, ports, and privileged flags remain runtime boundaries
- Home Manager-style validation, typed options, compatibility/state versions, collision detection, generations, and rollback vocabulary are useful for preview/report gates before any environment projection
- chezmoi/yadm-style context selectors and Git-friendly review can inform machine/project/runtime targeting, but dotfile application, `$HOME` mutation, bootstrap/hooks, encrypted secret archives, and auto-sync stay out of scope
- future environment reports should preview compatibility, collisions, capability deltas, lock drift, and action surfaces without installing packages, starting containers, reading secrets, mutating runtime/admin state, or committing/pushing

### From supply-chain provenance and release evidence

- release evidence should use subject/materials/builder/products vocabulary so archives, staging trees, handoff packs, checksums, gate reports, and provenance files form a reviewable local evidence chain
- SLSA and in-toto attestation patterns are useful for explicit predicates and supply-chain step evidence, but Portable AI Assets must not claim SLSA levels, Sigstore signatures, or in-toto signed metadata without real external controls
- CycloneDX/SPDX-style SBOM thinking reinforces public-safe inventories for files, schemas, sample assets, docs, licenses, checksums, adapter metadata, and report relationships before publication
- release status names must stay precise: `ready-for-manual-release-review` is not publish approval, and unsigned local provenance is not external authenticity proof
- future release gates should strengthen evidence completeness, drift detection, redaction, and reviewer handoff without signing artifacts, uploading attestations, calling registries/providers/APIs, validating credentials, committing, pushing, or publishing

### From declarative desired-state reconciliation

- desired-state manifests should describe target AI work-environment assets and expected projections without implying immediate execution
- observed-state reports should compare local files/docs/reports/projections against desired state and explain drift through public-safe diffs
- reconcile should default to `reconcile preview`: a plan with status/conditions, not a controller loop, sync engine, or automatic apply
- destructive or broad operations such as delete, prune, force, replace, remote sync, credential binding, provider/API calls, hook execution, commit, push, and publish require explicit review and are out of v0.1 default scope
- future reviewed apply gates should stay narrow, file-scoped, backup-aware, and sourced from human-reviewed candidate files, preserving Portable AI Assets as the asset layer rather than a runtime/controller

### From hosted assistant project containers

- hosted project containers are useful for project-pack vocabulary: instructions, knowledge-source membership, visibility, can-use/can-edit permissions, and action/tool metadata
- hosted chat histories, memories, uploaded storage, RAG chunks, embeddings, action logs, workspace identifiers, and credentials are runtime/private/cache state, not public canonical assets
- action/tool manifests should record purpose, schema pointers, risk class, credential-reference names, and environment binding names without embedding credential values

### From hosted agent / team workspace governance

- team/project packs need governance metadata: scope, visibility, permissions, retention, audit requirements, data controls, and capability policy
- shared apply previews should report permission deltas, capability-risk deltas, data-control flags, redaction status, and required human approvals
- identity systems, SSO/SCIM/RBAC servers, compliance tooling, DLP/eDiscovery, billing analytics, provider admin consoles, and retention enforcement remain external boundaries
- governance reports must redact users, emails, org IDs, tenant IDs, workspace IDs, audit logs, usage exports, credentials, webhooks, and provider-specific admin data

### From capability risk policy gates

- capabilities need a stable risk ladder: text-only, read-only-data, write-memory, write-files, external-network, code-execution, credential-binding, and admin-control
- risk reports should include invocation mode, execution location, mutation target, network posture, credential posture, visibility scope, rollback posture, and provenance
- future shared apply previews should show capability deltas and policy outcomes before any MCP/action/hook/custom-agent/cloud-execution surface is enabled
- `credential-binding` and `admin-control` must stay local/private/manual-first; public reports may show reference labels but never values or provider admin exports
- inventory modes should read declarative metadata only and must not start MCP servers, execute hooks, call webhooks/APIs, authenticate providers, or run imported code

## What not to absorb

- raw DB/corpus mirroring into Git
- arbitrary executable plugin scope before metadata contracts are mature
- agent/team/workflow execution scope; Portable AI Assets owns reviewed definitions and projections, not live orchestration, traces, or checkpoints
- automatic publishing/syncing of private memory
- one runtime becoming the only truth

## Operating rule

Every future memory/backend/tool reference should answer:

1. What is this system excellent at?
2. Which idea should Portable AI Assets adopt?
3. Which idea should Portable AI Assets explicitly avoid?
4. What is the safe integration boundary?
5. What report-only check should exist before any apply/write behavior?
