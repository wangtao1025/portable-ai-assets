# Reference: Dify / Flowise / Langflow Workflow Builders

This note captures lessons from visual AI workflow builders — Dify, Flowise, and Langflow — for Portable AI Assets. The goal is to learn how prompt/workflow/agent/RAG assets are packaged, exported, shared, deployed, and versioned, while keeping Portable AI Assets focused on canonical assets, adapter contracts, review gates, public-safe packs, and runtime-boundary discipline.

Sources reviewed for this initial reference:

- `langgenius/dify` public README and public documentation around workflow apps, self-hosting, model providers, RAG pipelines, agents, observability, and application import/export concepts.
- `FlowiseAI/Flowise` public README and `packages/server/src/database/entities/ChatFlow.ts` for visual agent/chatflow persistence fields such as `flowData`, `chatbotConfig`, `apiConfig`, `analytic`, `mcpServerConfig`, `workspaceId`, and chatflow/agentflow type.
- `langflow-ai/langflow` public README, public docs around flows/components/import-export/API/MCP, and `src/backend/base/langflow/services/database/models/flow/model.py` for flow metadata, serializable `data`, access type, endpoint, MCP enablement, custom Python components, and tags.

This is a reference review, not an integration. No Dify, Flowise, or Langflow server, Docker stack, database, workflow, model provider, vector database, plugin, API key, credential store, or MCP endpoint was installed, started, authenticated, or configured.

## What workflow builders do well

Dify, Flowise, and Langflow make AI applications tangible as visual, shareable, deployable workflow assets. They are important references because many durable AI assets are not only memory: prompts, graph nodes, routing rules, model/provider settings, tool bindings, RAG pipelines, variables, and deployment endpoints are all valuable continuity artifacts.

Useful architectural patterns:

- **Visual workflow as asset** — flows/apps are represented as serializable graphs with nodes/components, edges, inputs, outputs, prompts, tools, model settings, and metadata.
- **Import/export UX** — users expect to export a workflow/app, move it between environments, and import it elsewhere with provider credentials and environment-specific settings re-bound separately.
- **Runtime deployment boundary** — a flow can be deployed as an API, chat app, agent, webhook, embedded widget, or MCP tool, but that deployment state is different from the canonical workflow definition.
- **RAG pipeline separation** — datasets, documents, chunks, vector stores, and embeddings are runtime/data assets attached to a workflow, not the same as the workflow graph itself.
- **Credential indirection** — provider keys, tool credentials, API keys, database URLs, and deployment secrets should be referenced by name/config, not embedded in public workflow assets.
- **Workspace/project scoping** — workflow assets live under workspaces/projects/folders with access controls, public/private flags, sharing, duplication, and ownership metadata.
- **Custom component/plugin extension** — Langflow custom Python components, Flowise component integrations, and Dify tool/model/provider integrations show that arbitrary executable extension surfaces need strong boundaries.
- **Observability and analytics hooks** — workflow builders often store analytic/trace/feedback settings, but logs/traces and conversation runs should remain runtime state.
- **MCP/API exposure** — Langflow and Flowise-style MCP/API exposure validates treating flows as possible tools, but mutating publication/execution should stay outside preview modes.

## Concepts Portable AI Assets should adopt

Portable AI Assets should adapt the following ideas at the schema/report/adapter layer:

1. **Workflow manifest as canonical asset**
   A portable workflow asset should describe graph structure, prompts, variables, input/output schema, model/tool references, RAG dependencies, visibility, and runtime targets without embedding secrets or raw runtime data.

2. **Environment binding separation**
   Provider credentials, model endpoints, vector DB URLs, webhooks, API keys, and deployment URLs should be separate machine/team-local bindings, not hardcoded in canonical public workflow definitions.

3. **Graph diff and review**
   Workflow graphs need semantic review beyond raw JSON/YAML diffs: node additions/removals, prompt changes, model/provider changes, tool permission changes, RAG source changes, and deployment exposure changes.

4. **Asset dependency inventory**
   Workflow previews should list dependencies: model providers, tools, MCP servers, datasets, knowledge bases, vector stores, files, credentials, environment variables, and custom components.

5. **Visibility and deployment metadata**
   Candidate workflows should record whether they are private, workspace-shared, public, API-exposed, webhook-enabled, or MCP-enabled. Public reports must redact workspace/project/user IDs and endpoint names.

6. **Executable extension risk classification**
   Custom Python/JS components, plugins, tool nodes, webhooks, HTTP nodes, code execution, and MCP servers should be classified separately from declarative prompt/model nodes.

7. **Template/sample pack discipline**
   Public examples should include fake workflows with fake providers, fake credentials, fake datasets, and clear rebinding instructions, similar to existing team-pack and redacted-example strategy.

## Concepts Portable AI Assets should avoid

Portable AI Assets should not turn into Dify, Flowise, or Langflow.

Avoid:

- becoming a visual workflow builder, chat app server, model gateway, RAG runtime, agent orchestration platform, component marketplace, MCP server host, or deployment platform;
- committing raw workflow runtime databases, conversation logs, traces, feedback, analytics, vector indexes, uploaded documents, generated files, provider credentials, or API keys into Git;
- treating imported flow JSON/YAML as safe merely because it is text — tool nodes, code nodes, webhooks, HTTP calls, and custom components can be executable or exfiltration-capable;
- auto-importing or auto-publishing workflows into live Dify/Flowise/Langflow instances without a reviewed apply gate;
- assuming a workflow exported from one runtime is portable to another without an adapter/rebinding layer;
- exposing real workspace IDs, endpoint names, webhook URLs, dataset names, credential names, or internal tool names in public reports without redaction.

## Safe integration boundary

Recommended role split:

```text
Dify / Flowise / Langflow runtime
  -> owns visual editing, graph execution, model/provider calls, RAG execution, credential stores, custom components, deployment endpoints, analytics, traces, and runtime databases
  -> may expose workflow graph definitions, app metadata, dependency metadata, exported templates, and deployment/visibility flags

Portable AI Assets
  -> owns reviewed canonical workflow manifests, adapter contracts, dependency inventories, public-safe sample packs, team packs, and release gates
  -> imports workflow-builder data only through read-only previews and reviewable candidates
  -> exports workflow projections only after environment binding, credential, and executable-risk review
```

A future workflow-builder adapter should be read-only / preview-first:

1. detect Dify/Flowise/Langflow project exports, local config, Docker/database hints, or exported workflow files without starting servers;
2. parse graph metadata and dependencies without executing custom components or resolving live credentials;
3. classify nodes by risk: prompt/model/input/output, retrieval/dataset, tool/MCP/API, HTTP/webhook, code/custom component, deployment/analytics;
4. redact identifiers, endpoints, credential references, dataset names, and workspace/user metadata in public reports;
5. generate candidate bundles that include graph summaries, dependency manifests, prompt diffs, and rebinding instructions;
6. require reviewed canonical files before writing `workflows/`, `skills/`, team packs, or runtime adapter projections;
7. avoid write-back/import/publish into live workflow builders until a separate reviewed apply gate exists.

## Implications for Portable AI Assets

### Schema implications

Possible future schema additions:

- `workflow-manifest-v1` with fields for `name`, `workflow_version`, `asset_class`, `runtime_family`, `graph_summary`, `nodes`, `edges`, `inputs`, `outputs`, `prompts`, `model_refs`, `tool_refs`, `rag_refs`, `credential_refs`, `deployment_refs`, `visibility_scope`, and `apply_policy`.
- `workflow-node-risk`: `prompt`, `model`, `retrieval`, `tool`, `mcp`, `http`, `webhook`, `code`, `custom-component`, `deployment`, `analytics`.
- `environment-binding-v1` for machine/team-local provider credentials, endpoints, vector DBs, and secret references.
- `workflow-review-candidate-v1` for semantic graph diffs and rebinding checklists.

### Adapter implications

Future workflow-builder adapters should be declarative before executable:

- connector import: `dify-export-preview`, `flowise-chatflow-preview`, `langflow-flow-preview`, or `workflow-graph-summary`;
- connector export: `manual-only` until import/write-back semantics are designed;
- apply policy: `human-review-required` or `manual-only`;
- detection: exported DSL/YAML/JSON files, Docker compose/config hints, DB table metadata, workspace/project folders;
- reports: counts by workflow type, node risk, dependency kind, credential refs, deployment exposure, and public/private visibility, with raw secrets and private identifiers redacted.

### Report implications

Useful report modes to consider later:

- `--workflow-builder-inventory` — detect exported Dify/Flowise/Langflow workflow assets and runtime hints without executing anything.
- `--workflow-graph-preview` — summarize node/edge counts, prompt/model/tool/RAG dependencies, and risk classes.
- `--workflow-candidates` — generate review bundles for selected workflow exports.
- `--workflow-binding-status` — report missing provider/model/tool/vector credential bindings separately from canonical workflow graph validity.
- `--workflow-public-safety-scan` — detect secrets, endpoint URLs, credential names, private dataset names, and executable nodes in workflow exports.

## Public-safety and Git boundary

Keep out of Git and public reports:

- provider API keys, OAuth tokens, credential stores, webhook URLs, database URLs, model gateway secrets, and environment files;
- runtime DBs, vector indexes, uploaded documents, RAG chunks, traces, analytics, feedback, conversation logs, and generated files;
- real workspace IDs, project IDs, user IDs, organization IDs, endpoint names, dataset names, credential names, and internal tool names unless redacted;
- custom component source code if it contains proprietary logic, secrets, private endpoints, or unsafe execution behavior.

Safe public artifacts:

- redacted workflow manifests with fake providers and fake credentials;
- graph summaries and dependency counts;
- sample workflows using `/Users/example/...`, fake URLs, and explicit rebinding placeholders;
- docs explaining workflow graph vs runtime deployment/data boundaries.

## Follow-up verification questions

Before building a real adapter, verify against current upstream docs/code:

1. Which export/import formats are stable for Dify app DSL, Flowise chatflow/agentflow JSON, and Langflow flow JSON?
2. Which fields may contain credentials, endpoint URLs, webhook URLs, or private dataset/tool names?
3. Can workflow graph metadata be parsed without importing user code or executing custom components?
4. How should RAG datasets/files/chunks be represented: canonical workflow dependency, private asset, or backup-only runtime data?
5. How should public/private/workspace/API/MCP deployment exposure be preserved for private review but redacted publicly?
6. What semantic graph diff is most useful for reviewers: node changes, prompt changes, model/provider changes, tool risk changes, or deployment exposure changes?

## Summary judgment

Dify, Flowise, and Langflow are highly relevant references for prompt/workflow portability, graph-based AI app assets, environment rebinding, and visual-flow review. Portable AI Assets should adopt workflow manifest, dependency inventory, node-risk classification, and binding-status concepts, but should not become a visual builder, RAG runtime, model gateway, marketplace, or deployment server. The safe path is read-only, preview-first workflow import that converts selected flow definitions into reviewed canonical manifests while keeping credentials, runtime DBs, uploads, vectors, traces, and executable extension behavior outside Git.
