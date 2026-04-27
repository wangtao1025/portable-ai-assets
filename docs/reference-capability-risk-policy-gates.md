# Capability Risk Policy Gates Reference Review

Phase: 58
Status: reviewed
Reference family: MCP tools, hosted assistant actions, IDE hooks, custom coding agents, cloud execution agents, workflow-builder executable nodes, and enterprise capability controls.

This review turns the capability-governance lessons from prior references into a sharper risk-gate model. The goal is not to build a policy engine or execute external tools. The goal is to define which capability metadata Portable AI Assets should inventory and report before any future shared/team/project-pack apply behavior can enable MCP servers, actions, hooks, custom agents, cloud execution, or credential-bound connectors.

## Why this matters

Portable AI Assets can safely move text instructions, canonical memory summaries, manifests, and adapter projections only if executable capabilities are treated differently from ordinary text. A team pack that changes a prompt is lower risk than one that enables:

- an MCP server with write/delete/admin tools;
- a hosted assistant action with an external HTTP endpoint;
- an IDE hook that can run shell commands;
- a custom coding agent that can modify repositories;
- a cloud agent with network and secret access;
- a workflow node that can call APIs or execute arbitrary code.

Prior phases already say “preview first” and “review before apply.” Phase 58 adds a reusable vocabulary for *why* a capability is risky and what evidence a report should show before a human approves it.

## Reference signals observed

### MCP and plugin memory surfaces

MCP memory/server references show that tool names alone are not enough. `search`, `list`, and `context` tools are different from `save`, `update`, `delete`, `merge`, `admin`, or arbitrary command tools. The transport and storage backend also matter: local JSONL/file-bank storage is a different boundary from a managed API or database with credentials.

Useful signal: classify individual tools by operation risk, not just by the fact that they come from an MCP server.

### Hosted assistant actions and project containers

Claude Projects, Custom GPT-style actions, and hosted project assistants expose action/tool metadata alongside instructions and knowledge sources. Actions may reference schemas, remote endpoints, OAuth credentials, webhook URLs, and provider-managed permissions.

Useful signal: action metadata can be canonical, but credential values, endpoint secrets, logs, uploaded files, provider-hosted chat histories, and runtime execution traces are not canonical public assets.

### IDE hooks and coding-agent rules

IDE/project-memory references show that repo-local instruction files are durable assets, while hooks, custom commands, code indexes, terminal logs, and workspace caches are runtime/execution state. Hooks can be triggered automatically and may run with the developer’s local permissions.

Useful signal: automatic invocation and shell/code execution are independent risk multipliers even when the hook is stored as a simple text file.

### Workflow builders and executable nodes

Dify/Flowise/Langflow-style builders make prompts and graph structure portable, but code nodes, HTTP nodes, tool nodes, webhooks, MCP nodes, credentials, datasets, traces, and vector indexes require separate binding and risk classification.

Useful signal: graph diffs should include node-risk deltas and environment-binding deltas, not just prompt or topology changes.

### Hosted coding agents and workspace governance

Hosted agent governance references show that cloud agents, custom agents, hooks, MCP access, code referencing, organization access, and policy toggles are treated as administrative controls. Once an agent can run in a cloud workspace, inspect repos, or open pull requests, risk moves from “local prompt projection” to “shared execution governance.”

Useful signal: shared apply previews must surface capability expansion, permission expansion, and required approvals before a runtime is changed.

## Capability risk vocabulary to adopt

Use these labels in future manifests and reports. They are intentionally coarse, stable, and easy to review.

| Risk class | Meaning | Examples | Default gate |
|---|---|---|---|
| `text-only` | Human/agent-readable instructions with no direct runtime capability. | prompts, docs, playbooks, static instructions | preview + diff |
| `read-only-data` | Reads/searches/lists context without intended mutation. | MCP `search`, local file inventory, status/list APIs | preview + redaction check |
| `write-memory` | Mutates memory, skills, canonical assets, or runtime stores. | save/update/delete/merge memory, skill import apply | candidate + reviewed apply |
| `write-files` | Mutates files or repo-local rules/adapters. | write adapter, update rule file, create project instruction | reviewed apply + backup |
| `external-network` | Calls external HTTP/webhook/API endpoints. | hosted actions, HTTP workflow nodes, remote connectors | binding review + credential separation |
| `code-execution` | Runs local/cloud code, shell, notebooks, hooks, agents, or workflow code nodes. | pre/post hooks, shell tools, coding agents, cloud runners | explicit approval + sandbox/rollback notes |
| `credential-binding` | References credentials or secret-bearing environment bindings. | API keys, OAuth, tokens, connection strings, secret names | never public; local/private binding review |
| `admin-control` | Changes membership, permissions, retention, billing, audit, org/workspace policy, or provider settings. | workspace admin APIs, policy toggles, user access | manual-only / out-of-scope by default |

Risk is cumulative. A connector that both executes code and uses credentials should be reported as both `code-execution` and `credential-binding`, then gated by the stricter class.

## Additional risk dimensions

Future reports should include these dimensions because they change review severity:

- **Invocation mode**: manual, on-demand, scheduled, event-triggered, always-on, automatic.
- **Execution location**: local machine, dev container, CI, remote SaaS, cloud agent, unknown.
- **Mutation target**: canonical assets, adapter files, runtime memory, repository code, hosted workspace settings, external service.
- **Network posture**: offline, local-only, internal network, public internet, unknown.
- **Credential posture**: no credential, environment reference, credential reference name, embedded secret value, unknown.
- **Visibility scope**: individual, project, team, org, public-safe example.
- **Rollback posture**: no mutation, backup available, provider rollback available, unknown/no rollback.
- **Provenance**: source manifest, imported runtime config, generated candidate, human-reviewed file, unknown.

## What Portable AI Assets should adopt

### 1. Capability inventory before shared apply

Add a future report-only gate such as:

```text
bootstrap/setup/bootstrap-ai-assets.sh --capability-risk-inventory --both
```

The report should inventory capability-bearing assets from team packs, project packs, adapter contracts, workflow manifests, MCP registry entries, action manifests, and hook/custom-agent descriptors. It should not start servers, execute hooks, call external APIs, or validate credentials.

### 2. Capability deltas in previews

Any future `--team-pack-preview`, `--project-pack-preview`, or shared apply readiness report should show:

- new capabilities introduced;
- capabilities removed;
- risk classes before vs after;
- invocation changes, especially manual -> automatic/event-triggered;
- network/credential binding changes;
- whether public-safe examples contain only fake paths/data;
- required review/approval tier.

### 3. Conservative default gates

Recommended defaults:

- `text-only`: preview and diff are enough for individual/private surfaces.
- `read-only-data`: preview plus public-safety/redaction scan.
- `write-memory` and `write-files`: candidate/review/apply with backup.
- `external-network`: require binding review and redacted endpoint/secret handling.
- `code-execution`: require explicit human approval and sandbox/rollback notes.
- `credential-binding`: values must stay local/private; public reports may show reference names only.
- `admin-control`: manual-only in v1; do not automate provider admin mutations.

### 4. Policy outcome vocabulary

Reports should classify each capability with a simple outcome:

- `allow-preview` — safe to describe without mutation.
- `review-required` — cannot apply without a reviewed candidate or approval evidence.
- `manual-only` — Portable AI Assets may document/inventory but should not apply automatically.
- `blocked-public` — cannot enter public release/demo output.
- `out-of-scope` — belongs to identity/admin/compliance/runtime systems, not this project.

### 5. Evidence requirements

For any capability above `read-only-data`, a reviewed apply candidate should include:

- source manifest path and source runtime;
- target runtime/scope;
- risk classes and dimensions;
- human-readable purpose;
- proposed diff or binding change;
- credential-reference names, never values;
- rollback/backup plan where applicable;
- reviewer/approval note, redacted in public outputs.

## What Portable AI Assets should explicitly avoid

Do not turn Portable AI Assets into:

- an MCP host or MCP tool execution broker;
- an action execution runtime;
- a workflow engine;
- a cloud-agent scheduler or sandbox;
- a hooks runner;
- a credential manager or secrets sync system;
- an enterprise policy engine;
- a provider admin console;
- a system that silently enables tool/network/code/admin capabilities because a manifest exists.

Also avoid:

- executing imported code to inspect it;
- starting unknown MCP servers during inventory;
- validating live credentials in public/release gates;
- copying webhook URLs, API keys, OAuth tokens, session cookies, or connection strings into Git;
- treating a benign connector label as proof that a capability is safe;
- collapsing all capabilities into a single “tool enabled” boolean.

## Safe integration boundary

### Inventory only

A capability-risk gate may read declarative metadata such as:

- adapter contract connector names;
- MCP server names, transport labels, declared tool names, and storage hints;
- action names, purpose summaries, schema pointers, and credential-reference labels;
- hook/custom-agent descriptor paths and trigger labels;
- workflow node types and environment-binding names;
- team/project-pack capability policy sections.

It must not execute tools, run shell commands from imported manifests, call remote endpoints, start services, authenticate to providers, or mutate runtime state.

### Preview before candidate

If risk is elevated, generate a candidate bundle rather than applying directly. The bundle should explain the capability, the risk class, the expected mutation, and the missing review evidence.

### Reviewed apply only

A future apply gate may consider reviewed files only when risk permits it. `admin-control`, embedded secrets, unknown executable code, or unreviewed automatic hooks should remain manual-only or blocked.

## Canonical mapping

| External capability concept | Portable AI Assets mapping |
|---|---|
| MCP server | adapter/runtime capability inventory item; read-only preview by default |
| MCP tool | per-tool risk class such as read-only-data, write-memory, code-execution, or admin-control |
| Hosted action | action manifest / environment binding candidate; network + credential review required |
| Webhook/API endpoint | environment binding name only; real URL stays private/local |
| IDE hook | executable capability requiring trigger, sandbox, and rollback review |
| Custom coding agent | code-execution capability; repo/workspace scope must be explicit |
| Cloud execution agent | code-execution + external-network + credential-binding risk unless proven otherwise |
| Workflow code/HTTP/tool node | workflow capability delta in graph preview |
| Provider admin setting | admin-control; manual-only / out-of-scope by default |
| Credential reference | private binding label; never public value |

## Raw/runtime data that must remain outside Git

Keep these out of public canonical assets and release/demo packs:

- API keys, OAuth tokens, session cookies, private keys, connection strings;
- webhook URLs and provider endpoints containing tenant/project identifiers;
- raw MCP server configs if they embed local private paths or env values;
- hook scripts from private repositories unless explicitly public-safe examples;
- cloud-agent logs, terminal logs, execution traces, build outputs, and PR/repo IDs;
- provider admin exports, audit logs, permission dumps, user lists, or billing data;
- workflow run histories, HTTP payloads, datasets, vector indexes, and credentials;
- real approval identities, ticket URLs, org/workspace/project IDs, or emails.

Use fake examples or `[REDACTED]` placeholders in public reports.

## Report/check implications

Near-term reusable gates to add later:

1. `--capability-risk-inventory --both`
   - inventory declared MCP/actions/hooks/custom agents/cloud execution/workflow capabilities;
   - classify risk classes, invocation mode, execution location, credential/network posture, and target scope;
   - report blockers without executing anything.

2. `--capability-policy-preview --both`
   - compare a team/project pack capability policy against declared capabilities;
   - show allowed, review-required, manual-only, blocked-public, and out-of-scope items.

3. `--shared-apply-readiness --both`
   - refuse shared apply when elevated capability risk lacks reviewed evidence, redaction, backup/rollback, or approval metadata.

4. `--capability-redaction-check --both`
   - scan capability manifests/reports for secret-like values, private endpoints, real identities, local private paths, and provider IDs before public packaging.

These remain report-only until project-pack/team-pack apply behavior is mature.

## Decision for Portable AI Assets

Adopt the risk vocabulary, dimensions, and report-only gate requirements now. Defer executable enforcement, credential validation, MCP/action execution, cloud-agent operation, and provider admin mutation.

Phase 58 makes `docs/reference-capability-risk-policy-gates.md` a reviewed reference so future shared/project/team apply behavior has a precise capability-risk contract before it can mutate tool, action, hook, agent, or cloud-execution surfaces.

## Sources checked

This review synthesizes the earlier local reference docs and public documentation families already reviewed in this project:

- MCP memory server reference patterns: protocol-level memory tools, storage diversity, read/search vs save/update/delete/admin separation.
- Hosted assistant project references: Claude Projects / Custom GPT-style instructions, knowledge, action/tool metadata, sharing, and provider-hosted runtime boundaries.
- IDE assistant project-memory references: repo-local rules, instruction projection matrices, hooks/custom commands, IDE caches, and prompt-injection boundaries.
- Workflow-builder references: Dify / Flowise / Langflow graph assets, HTTP/tool/code nodes, environment bindings, credentials, and runtime traces.
- Hosted agent/workspace governance references: GitHub Copilot organization controls, custom agents, hooks, MCP/cloud-agent access, admin policy scope, audit, retention, and capability policy.

The review intentionally avoids relying on private implementation details or access-controlled pages. It adopts conservative, source/runtime-separated capability boundaries that are useful even when provider-specific APIs change.
