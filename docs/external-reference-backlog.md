# External Reference Backlog

This backlog prevents Portable AI Assets from evolving in isolation. Each candidate is a system or idea family worth studying before we invent or implement a similar capability.

## Review states

- `candidate` — known system / idea worth reviewing
- `queued` — selected for near-term review
- `reviewed` — has a `docs/reference-<system>.md` note
- `adopted` — lessons have been incorporated into schemas/adapters/docs
- `rejected` — reviewed and intentionally not adopted

## Priority rubric

Prioritize systems that can improve one of these areas:

1. runtime memory backend integration
2. cross-agent portability
3. skill / procedure lifecycle
4. adapter contract design
5. safe import/export / review gates
6. local-first storage and privacy boundaries
7. release / packaging maturity

## Backlog

| id | system | category | state | priority | why review | expected output |
|---|---|---|---|---|---|---|
| memos-local-plugin | MemOS local plugin | runtime memory backend / skill lifecycle | reviewed | high | Strong local memory plugin reference: taxonomy, skill lifecycle, runtime/source separation. | `docs/reference-memos-local-plugin.md` |
| mempalace | MemPalace + OMX bridge | long-term memory core / bridge | reviewed | high | Current local memory-core candidate and bridge pattern. | `docs/reference-mempalace.md` |
| letta-memgpt | Letta / MemGPT | agent memory runtime | reviewed | high | Mature agent memory architecture and memory tiers may inform canonical asset classes. | `docs/reference-letta-memgpt.md` |
| openmemory | OpenMemory-style memory layer | shared memory service | reviewed | high | Useful reference for cross-application memory service boundaries, app/client scoping, lifecycle states, MCP surfaces, and explainable memory operations. | `docs/reference-openmemory.md` |
| supermemory | Supermemory-style universal memory | managed memory platform | reviewed | high | Useful product/API reference for ingestion, recall, profile projection, container/project scoping, MCP/plugin tools, and managed-memory portability boundaries. | `docs/reference-supermemory.md` |
| langgraph-memory | LangGraph / LangChain memory patterns | agent graph memory | reviewed | high | Useful for workflow state vs durable memory separation, namespace scopes, semantic/episodic/procedural taxonomy, and hot-path vs background memory provenance. | `docs/reference-langgraph-memory.md` |
| mcp-memory-servers | MCP memory servers | protocol memory integration | reviewed | high | Relevant for protocol-level memory tool boundaries, transport/storage diversity, runtime discovery, and read-only preview-first adapter design. | `docs/reference-mcp-memory-servers.md` |
| dify-flowise-langflow | Dify / Flowise / Langflow | workflow builders | reviewed | high | Useful for prompt/workflow portability, visual-flow asset boundaries, graph dependency inventory, node-risk classification, and environment rebinding. | `docs/reference-workflow-builders.md` |
| open-webui-memory | Open WebUI / local assistant memory | local assistant runtime | reviewed | high | Useful for local-first memory UX, personal-memory vs knowledge/RAG boundaries, permissions, storage, vector-index rebuildability, and import/export safety. | `docs/reference-open-webui-memory.md` |
| zed-cursor-project-memory | IDE assistant project memory | IDE/project memory | reviewed | high | Useful for project-local instructions, IDE rule files, workspace portability, projection matrices, and instruction conflict checks. | `docs/reference-ide-project-memory.md` |
| assistant-projects-gpts | Claude Projects / Custom GPTs / project assistants | assistant project containers | reviewed | high | Useful for hosted/project-scoped instruction, file, memory, action, and sharing boundaries beyond IDE-local assistants. | `docs/reference-assistant-projects.md` |
| hosted-agent-workspace-governance | Hosted agent/team workspace governance | hosted agent governance | reviewed | high | Useful for org/workspace policy, audit, sharing, data-retention, and admin-control boundaries before team/project-pack apply behavior. | `docs/reference-hosted-agent-workspace-governance.md` |
| capability-risk-policy-gates | Capability risk policy gates | capability governance | reviewed | high | Useful for turning MCP/actions/hooks/custom agents/cloud execution risk classes into report-only preview gates before shared apply. | `docs/reference-capability-risk-policy-gates.md` |
| capability-policy-report-implementation | Capability policy report implementation patterns | capability governance / report gates | reviewed | high | Converts Phase 58 risk vocabulary into report-only inventory, policy preview, and shared-apply readiness gates without creating an execution runtime. | `docs/reference-capability-policy-report-implementation.md` |
| project-pack-preview | Project pack preview and capability deltas | project/team packaging | reviewed | high | Adds report-only project-pack preview for project instructions, knowledge-source references, action metadata, adapter projections, and capability risk declarations. | `docs/reference-project-pack-preview.md` |
| capability-policy-preview | Capability policy preview and delta reporting | capability governance / project-pack deltas | reviewed | high | Adds report-only capability policy delta preview for added, removed, changed, and risk-upgraded capabilities before any project/team/shared apply behavior. | `docs/reference-capability-policy-preview.md` |
| capability-policy-baseline-apply | Reviewed capability policy baseline apply | capability governance / reviewed baselines | reviewed | high | Adds a narrow reviewed apply gate that writes only human-reviewed capability baseline files with backup, without mutating runtimes or providers. | `docs/reference-capability-policy-baseline-apply.md` |
| completed-work-review | Completed work review gate | roadmap / release governance / external learning | reviewed | high | Adds a report-only post-phase review for roadmap alignment, release readiness, public safety, capability boundaries, and external-learning checks before continuing. | `docs/reference-completed-work-review.md` |
| capability-policy-candidate-generation | Capability policy baseline candidate generation | capability governance / reviewed baselines | reviewed | high | Adds report-only reviewed-baseline template generation from preview/current capability metadata while still requiring human review before apply. | `docs/reference-capability-policy-candidate-generation.md` |
| capability-policy-candidate-status | Capability policy candidate status gate | capability governance / reviewed baselines | reviewed | high | Adds a report-only readiness and review handoff audit gate that checks template/reviewed-baseline existence, validation, synchronization, hashes/preflight evidence, and apply readiness without writing candidates or applying baselines. | `docs/reference-capability-policy-candidate-status.md` |
| coding-agent-workspace-portability | Continue.dev / Cline / Roo Code / Aider / OpenHands | coding-agent workspace / project memory | reviewed | high | Useful for workspace packs, role profiles, repo instructions, task handoffs, capability deltas, and runtime/cache/credential boundaries so project-pack projection is not IDE-specific. | `docs/reference-coding-agent-workspace-portability.md` |
| agent-workflow-skill-registries | CrewAI / AutoGen / Semantic Kernel / Anthropic Agent Skills / LangGraph | agent workflow / skill registry | reviewed | high | Compared task graphs, agent roles, skills/tools, filesystem skill packaging, registry metadata, and trust boundaries before extending procedure and workflow asset schemas. | `docs/reference-agent-workflow-skill-registries.md` |
| reproducible-environment-portability | Nix flakes / Dev Containers / Home Manager / chezmoi / yadm | environment portability / dotfiles | reviewed | high | Compared manifest/lock provenance, schema-first dev environments, declarative user environment validation, context selectors, dotfile preview/apply boundaries, and action-risk surfaces before adding portable environment descriptors. | `docs/reference-reproducible-environment-portability.md` |
| supply-chain-provenance | Sigstore / SLSA / in-toto / CycloneDX / SPDX | release provenance / supply chain | reviewed | high | Compared signing, SLSA provenance, in-toto evidence chains, CycloneDX/SPDX SBOM inventory, and release-trust boundaries before strengthening public release evidence language. | `docs/reference-supply-chain-provenance.md` |
| declarative-desired-state | Kubernetes CRD / GitOps / Argo CD / Flux | desired-state reconciliation | reviewed | high | Compared declarative desired state, diff, status/conditions, reconciliation, drift detection, destructive action controls, and reviewed apply boundaries for future asset sync governance. | `docs/reference-declarative-desired-state.md` |

## Required review template

Every reviewed candidate should answer:

1. What does this system do well?
2. What should Portable AI Assets adopt?
3. What should Portable AI Assets explicitly avoid?
4. What is the safe integration boundary?
5. What schema/adapter/report should change, if any?
6. What raw/runtime data must remain outside Git?

## Reference intake radar

The `--external-reference-backlog` report now includes a report-only `reference_intake_radar` section. It converts the current reviewed coverage and candidate queue into next review lanes without contacting external services or cloning projects.

Safety contract:

- `executes_anything: false`
- `calls_external_services: false`
- `writes_runtime_state: false`
- no network search, clone, download, provider/API call, authentication, runtime execution, or credential/admin/provider mutation
- record only public conceptual notes, review questions, expected `docs/reference-*.md` outputs, and adoption boundaries

Current radar lanes:

1. coding-agent workspace portability — Continue.dev, Cline, Roo Code, Aider, OpenHands (reviewed in Phase 70)
2. agent workflow and skill registries — CrewAI, AutoGen, Semantic Kernel, Anthropic Agent Skills, LangGraph (reviewed in Phase 73)
3. reproducible environment portability — Nix flakes, Dev Containers, Home Manager, chezmoi, yadm (reviewed in Phase 74)
4. supply-chain provenance and release evidence — Sigstore, SLSA, in-toto, CycloneDX, SPDX (reviewed in Phase 75)
5. declarative desired-state reconciliation — Kubernetes CRD, GitOps, Argo CD, Flux (reviewed in Phase 76)

## Near-term queue

Recommended next reviews after Phase 76:

- Current high-priority reference radar lanes are reviewed. Keep the radar report-only and add any new lane only after it clearly strengthens memory portability, adapter governance, public release safety, or reviewed apply boundaries without expanding into runtime/controller scope.
