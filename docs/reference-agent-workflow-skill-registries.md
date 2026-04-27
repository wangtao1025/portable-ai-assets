# Reference: Agent workflow and skill registries

## Scope

This note reviews mature agent/workflow/skill systems as external references for Portable AI Assets. The goal is to learn metadata, packaging, discovery, and trust-boundary patterns without turning Portable AI Assets into an agent runtime, workflow orchestrator, or skill executor.

Reviewed references:

- CrewAI agents/tasks/skills documentation
- Microsoft AutoGen AgentChat agents and teams documentation
- Microsoft Semantic Kernel agents documentation
- Microsoft Agent Framework skills documentation
- Anthropic Agent Skills documentation
- LangGraph Platform documentation as an adjacent workflow-runtime reference

## What these systems do well

### CrewAI

CrewAI makes the agent/work unit split explicit:

- agents have roles, goals, backstories, tools, memory/delegation controls, reasoning and iteration limits, rate limits, and execution constraints;
- tasks describe expected outputs, assigned agents, context dependencies, tools, guardrails, output files, and optional human input;
- skills are composable custom components that can be packaged, discovered, and reused across crews.

Useful lesson: durable procedure assets need both human-readable instructions and machine-readable execution/risk metadata. Roles, goals, task inputs/outputs, guardrails, and delegation permissions should be reviewable before any runtime uses them.

### AutoGen

AutoGen AgentChat emphasizes a runtime contract:

- agents expose names, descriptions, `run`, and `run_stream` methods;
- agents are stateful and should receive new messages rather than full-history replays;
- teams such as `RoundRobinGroupChat`, selector teams, swarms, and graph-style workflows coordinate multiple agents;
- documentation explicitly recommends starting with a single agent and moving to teams only when collaboration is necessary;
- observing team behavior, termination, state management, serialization, tracing, and human-in-the-loop controls are first-class runtime concerns.

Useful lesson: multi-agent workflow state, traces, termination, and message history are runtime artifacts. Portable AI Assets can own the reviewed team/role/task definitions and handoff metadata, but should not own or replay live conversations, traces, or team execution state.

### Semantic Kernel and Microsoft Agent Framework

Microsoft agent documentation separates agent abstractions from concrete execution surfaces:

- agents are abstractions over model, instructions, plugins/tools, and channels;
- different agent implementations support different hosting, orchestration, and tool surfaces;
- Agent Framework skills package reusable functionality behind explicit definitions and invocation contracts;
- agent and skill composition lives near runtime orchestration, tool authorization, and provider bindings.

Useful lesson: skill/agent metadata should carry clear capability declarations and environment-binding names, while concrete provider credentials, tool authorization, invocation logs, and runtime state remain outside canonical public assets.

### Anthropic Agent Skills

Anthropic Agent Skills provide a particularly relevant packaging reference:

- each skill is filesystem-based and requires `SKILL.md` with YAML frontmatter;
- required metadata includes `name` and `description`, with naming and length constraints;
- descriptions tell the agent what the skill does and when to use it;
- optional resources such as scripts, templates, examples, and reference files support progressive disclosure;
- skills can be composed, loaded on demand, and kept out of context until needed;
- security guidance treats skills like installed software: audit every bundled file, external dependency, and tool/code invocation path before trusting it;
- custom skills do not automatically sync across all surfaces, which validates the need for a cross-surface portability layer.

Useful lesson: a portable skill/procedure asset should use manifest-first packaging, progressive disclosure, linked files, and strong trust metadata. Public examples should never imply that importing a skill is safe without review.

### LangGraph Platform

LangGraph is a workflow runtime and deployment platform, not an asset portability layer. It is still useful as an adjacent reference because it makes the following runtime responsibilities explicit:

- graph execution and orchestration;
- persisted thread/checkpoint state;
- deployment/runtime configuration;
- observability, traces, and control-plane operations.

Useful lesson: Portable AI Assets should preserve reviewed graph/task/skill definitions and portability metadata, but graph checkpoints, thread state, deployment configuration, traces, and runtime control-plane state remain out of scope.

## Patterns Portable AI Assets should absorb

### 1. Manifest-first skill and agent packaging

Future portable skill/procedure and agent-role manifests should capture:

- stable name, description, version, owner/source, lifecycle status, and review status;
- trigger/when-to-use text for agent selection;
- role/goal/backstory or domain context where relevant;
- required inputs, expected outputs, examples, and verification steps;
- linked resource files such as templates, references, or scripts, with public-safe paths;
- provenance and source evidence;
- target runtime projections such as Hermes, Claude Code, Codex, Claude Skills, CrewAI, or AutoGen;
- public/private classification and redaction posture.

### 2. Capability and risk declarations before projection

Agent/skill manifests should classify capability posture before any adapter projection:

- text-only guidance;
- read-only data access;
- file writes;
- external network/API/webhook access;
- code/shell execution;
- credential binding;
- admin/provider control;
- scheduled/background behavior;
- multi-agent delegation or human-in-the-loop requirement.

This aligns with existing capability-risk policy gates and prevents apparently simple skills from smuggling executable or network behavior into runtime instructions.

### 3. Registry and discovery metadata without execution

A future registry can inventory portable skills, roles, tasks, project packs, and workflow definitions without invoking them. Useful registry fields:

- package id and version;
- category and supported runtimes;
- trigger/selection metadata;
- linked files and checksums;
- lifecycle status: draft, probationary, active, retired;
- review evidence and reviewer notes;
- compatibility notes and known limitations;
- risk class and policy outcome;
- projection targets and adapter status.

Discovery should answer “what could be projected after review?” rather than “what should be run now?”.

### 4. Progressive disclosure for large procedures

Anthropic-style filesystem skills validate the current Portable AI Assets approach: keep the manifest small, link detailed references/templates/examples, and load only the needed resource during projection or review.

For public release, this means samples can show package structure and metadata while keeping private procedure details, runtime logs, and secrets outside public artifacts.

### 5. Human review and trust boundary as product features

External systems make skills and workflows powerful by combining instructions, tools, code, and external resources. Portable AI Assets should treat this as a trust boundary:

- imported skills default to review-required or probationary;
- bundled scripts/templates/resources are audited before activation;
- external URLs and dependencies are recorded as risky until reviewed;
- projection previews show capability deltas before writing target runtime files;
- reviewed apply gates remain narrow and explicit.

## What Portable AI Assets should not absorb

Portable AI Assets should not become:

- an agent runtime;
- a workflow orchestrator;
- a multi-agent team executor;
- a graph/checkpoint runtime;
- a tool/plugin runner;
- a hosted skill marketplace;
- a provider credential broker;
- an MCP/action/hook/cloud execution platform;
- an observability/tracing backend;
- a chat-history or execution-trace warehouse.

It should also avoid:

- importing raw conversations, traces, thread state, checkpoint state, execution logs, or provider transcripts into Git;
- auto-running imported skills or scripts;
- auto-syncing runtime-installed skills across surfaces without review;
- treating runtime-specific skill directories as the canonical source of truth;
- embedding API keys, OAuth tokens, webhook URLs, endpoints, account IDs, workspace IDs, or provider-specific admin data in public docs/reports.

## Safe integration boundary

The safe boundary is:

```text
External agent/workflow/skill runtimes → read-only metadata inventory → reviewed portable skill/role/task candidates → capability/risk preview → narrow human-reviewed projection into target runtime files.
```

Report-only modes may inspect declarative metadata and generate public-safe summaries. They must not:

- start agent/workflow runtimes;
- execute skills, scripts, hooks, tools, tasks, or workflows;
- call providers, APIs, webhooks, or MCP tools;
- authenticate or validate credentials;
- mutate runtime/admin/provider state;
- publish or sync packages;
- commit or push.

## Schema, adapter, and report implications

Near-term implications:

1. Keep `portable-skill-manifest-v1` as the canonical skill/procedure layer and extend only after more implementation evidence.
2. Consider future `agent-role-manifest-v1` or `workflow-definition-manifest-v1` only when a concrete adapter needs it.
3. Add registry reports before apply behavior: inventory skills/roles/tasks, summarize risk classes, and list projection targets.
4. Reuse existing capability-risk gates for any agent/skill/workflow projection.
5. Keep external reference reviews as docs first; do not implement runtime execution because these references are intentionally runtime products.

## Raw/runtime data that must remain outside Git

Keep these out of Git and public release packs:

- runtime-installed skill directories from private machines unless rewritten as reviewed public-safe samples;
- raw conversations, team messages, traces, checkpoints, observations, and run histories;
- tool call payloads and outputs;
- shell/code execution logs;
- provider/model bindings and API credentials;
- MCP server configs with private paths or env values;
- generated diffs, task scratchpads, and live workspace state;
- deployment/control-plane config;
- tenant/workspace/user identifiers;
- marketplace/package credentials or publication state.

## Adoption decision

Adopt the packaging, metadata, lifecycle, registry, progressive-disclosure, and trust-boundary lessons. Do not adopt the runtime/executor scope.

For Phase 73, this remains a reviewed reference document and roadmap/release alignment update only. It does not add execution, adapter writes, provider calls, or publication behavior.
