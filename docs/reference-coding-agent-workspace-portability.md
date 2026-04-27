# Reference: Coding-Agent Workspace Portability

Phase: 70  
Scope: Continue.dev, Cline, Roo Code, Aider, OpenHands, and adjacent coding-agent workspace conventions.  
Status: reviewed reference; not an implementation spec for a coding-agent runtime.

## Why this reference matters

Coding agents are one of the highest-value portability targets for Portable AI Assets because they accumulate durable work-environment knowledge in many repo-local and machine-local places:

- project instructions and agent rules;
- workspace settings and tool permission profiles;
- command/test/build conventions;
- coding style and review preferences;
- task plans, handoffs, and checkpoint notes;
- model/provider configuration and API bindings;
- conversation histories, diffs, terminals, browser sessions, and execution traces.

The risk is that a user can switch from one coding agent to another and lose the most valuable parts of their working environment, or accidentally copy unsafe runtime state into a public repo. Portable AI Assets should own the reviewed, portable asset layer above these coding agents, while leaving live agent execution, code editing, terminal control, and provider credentials to the tools themselves.

This review intentionally remains report/documentation-only. No coding agent was launched, no repository was cloned, no network/API/provider was called, no tool permissions were changed, and no live workspace state was read or applied.

## Systems reviewed at the conceptual boundary

### Continue.dev

Continue-style assistants emphasize IDE-integrated coding support, model/provider configurability, context providers, slash commands or prompt shortcuts, and workspace/repo context. The useful portability lesson is that coding assistance is composed from declarative configuration, context sources, reusable prompts/rules, and provider bindings. Those classes should not be mixed together.

Portable AI Assets lesson: model/provider settings and context-provider bindings are environment-specific; durable prompts, rules, and project conventions can become canonical assets after review.

### Cline

Cline-style agents emphasize autonomous coding tasks, tool use, file edits, terminal commands, browser interaction, MCP/tool integration, and explicit user approval for risky actions. They make the tool-permission surface visible and therefore useful for capability policy design.

Portable AI Assets lesson: workspace instructions and task handoffs are portable candidates; approvals, terminal traces, browser state, MCP runtime state, and command outputs are runtime/evidence artifacts, not canonical Git memory.

### Roo Code

Roo Code-style systems build on the coding-agent pattern with mode/persona concepts, task workflows, custom instructions, and tool permissions. The important lesson is that a single workspace may need multiple role-specific projections: architect, coder, reviewer, tester, debugger, or documenter.

Portable AI Assets lesson: project packs should be able to project different reviewed instruction blocks by role/mode while keeping the canonical source deduplicated.

### Aider

Aider-style terminal agents highlight repo-native operation, Git diff/commit workflow, map/context construction, conventions files, and command-line configuration. They treat the Git working tree and commit boundaries as central parts of the agent workflow.

Portable AI Assets lesson: Git-aware coding agents benefit from portable instructions that distinguish coding conventions, test commands, commit style, and review expectations. Chat transcripts, repo maps, temporary context windows, and generated diffs should stay runtime/cache/evidence unless explicitly reviewed into a durable note.

### OpenHands

OpenHands-style agent environments emphasize full development sandboxes, tasks, browsing/terminal/file operations, runtime images, and evaluation or benchmark workflows. They make the environment boundary explicit: the agent's workspace can include containers, dependencies, secrets, task sandboxes, and execution logs.

Portable AI Assets lesson: reproducible workspace environment metadata matters, but Portable AI Assets should not become the sandbox or execution platform. It should record reviewed environment expectations and project-pack metadata, not raw container state or execution traces.

## What coding-agent workspaces do well

1. **Repo-local instruction surfaces** — coding agents converge around project rules, custom instructions, and agent-readable files. This validates canonical project-rule assets and adapter projections.
2. **Task handoff artifacts** — plans, TODOs, checkpoints, and summaries are valuable continuity assets when moving between agents or sessions.
3. **Tool permission visibility** — many coding agents expose approvals for file writes, shell commands, browser use, MCP tools, or network calls. This maps directly to capability-risk policy gates.
4. **Role/mode separation** — coder/reviewer/architect/debugger modes prevent one giant prompt from mixing all behaviors.
5. **Environment awareness** — agents need test commands, package managers, dependency managers, runtime versions, and workspace setup notes.
6. **Git-centered workflow** — diffs, branches, commits, and review boundaries are natural checkpoints for migration and handoff.
7. **Context source composition** — agents combine repo files, rules, issue text, terminal output, logs, web pages, and memory. Only some of that should become canonical.

## Concepts Portable AI Assets should adopt

### Workspace pack vocabulary

Add or reuse project/team-pack concepts for coding-agent workspaces:

- `workspace_slug`
- `repo_scope`
- `project_instructions`
- `agent_rules`
- `role_profiles`
- `task_handoff_policy`
- `test_commands`
- `build_commands`
- `package_manager`
- `tool_permissions`
- `mcp_or_tool_bindings`
- `environment_expectations`
- `target_coding_agents`
- `projection_targets`
- `source_provenance`
- `review_status`

The canonical asset should be a reviewed workspace pack, not a copy of any one agent's live workspace state.

### Role-specific instruction projections

A canonical project rule may need different projections:

- concise rule blocks for always-on coding context;
- detailed reviewer checklists for review mode;
- debugger playbooks for failure analysis;
- release/checklist instructions for publication mode;
- safety constraints for shell/network/MCP usage.

This supports Cline/Roo-style modes without turning Portable AI Assets into a mode executor.

### Task handoff as a portable artifact

Coding-agent sessions often end with valuable state:

- current task goal;
- completed steps;
- failing tests or blockers;
- changed files and rationale;
- next recommended command;
- open safety questions;
- whether commit/push has happened.

Portable AI Assets should treat reviewed handoff notes as durable project memory candidates, while leaving raw conversations and terminal logs outside Git/public release.

### Capability and permission deltas

Coding-agent portability is unsafe without a permission model. A projection preview should report whether a target agent would gain or lose:

- file-write permissions;
- shell/code execution;
- network/browser access;
- MCP/tool access;
- credential/environment binding;
- scheduled/background behavior;
- auto-commit/push behavior.

This extends existing capability-policy gates from project/team packs into coding-agent workspace packs.

### Context budget and source classes

Coding-agent context should be classified before projection:

- always-on instructions;
- repo conventions;
- role-specific playbooks;
- task handoff notes;
- recent changed-file summaries;
- retrieved docs;
- runtime logs/traces;
- raw chat transcripts.

Only reviewed, compact, durable material should become canonical assets. Runtime-heavy context remains backup/cache/evidence.

## Concepts Portable AI Assets should avoid

Portable AI Assets should not become:

- a coding agent;
- an IDE extension;
- a terminal automation runtime;
- a browser automation runtime;
- a sandbox/container execution platform;
- an MCP host or tool executor;
- a Git auto-commit/auto-push bot;
- a model/provider configuration broker;
- a universal coding-agent compatibility layer that promises lossless migration.

It should also avoid automatically importing or publishing:

- raw coding-agent chats;
- terminal logs and command outputs;
- browser sessions/screenshots;
- code indexes, embeddings, repo maps, and cached file snapshots;
- generated patches/diffs without review;
- local absolute paths, private repo names, issue/customer IDs, internal service names;
- API keys, tokens, model-provider credentials, MCP secrets, environment files, or webhook URLs;
- unreviewed repo-local rules from unknown worktrees.

## Safe integration boundary

```text
Coding-agent runtime
  -> owns live planning, code editing, terminal/browser/MCP execution, model calls, sandbox state, approvals, conversations, and traces
  -> may expose configuration files, instruction surfaces, rules, task summaries, and exported handoff notes

Portable AI Assets
  -> owns reviewed canonical workspace packs, project rules, role profiles, task handoff summaries, permission metadata, adapter projection previews, and public-safe examples
  -> imports coding-agent rules and handoffs only through read-only previews and reviewable candidates
  -> exports agent-specific instructions only after conflict, capability, and public-safety review
```

A future coding-agent adapter should be preview-first:

1. detect known instruction/rule/handoff files without launching the agent;
2. inventory project rules, modes, commands, and declared tool permissions;
3. classify artifacts as canonical candidate, runtime trace, cache, credential binding, or backup-only state;
4. generate review bundles for workspace packs and handoff notes;
5. report capability deltas before any projection;
6. require reviewed canonical files before writing to `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.clinerules`, `.roo/rules`, `.aider*`, Continue config, or similar targets;
7. never execute shell commands, start MCP servers, open browsers, authenticate providers, or mutate Git remotes in inventory/preview modes.

## Suggested schema/report implications

Do not implement a coding-agent sync engine yet. The safe next increments are metadata/report surfaces:

1. `workspace-pack-manifest-v1` — repo scope, instructions, role profiles, commands, permissions, and target agents.
2. `coding-agent-rules-inventory` — report-only inventory of known rule/instruction/handoff files.
3. `workspace-pack-preview` — show how canonical workspace assets would project into agent-specific surfaces.
4. `coding-agent-capability-delta` — compare current vs projected tool permissions and risk classes.
5. `task-handoff-candidates` — turn reviewed task summaries into durable project memory candidates.
6. `instruction-conflict-check` — detect contradictory rules across Continue/Cline/Roo/Aider/OpenHands/Cursor/Zed/Claude/Codex surfaces.

## Practical mapping to existing Portable AI Assets

| Coding-agent concept | Portable AI Assets mapping | Git/public policy |
|---|---|---|
| Project custom instructions | canonical project rule / workspace pack field | public-safe only if generic; private otherwise |
| Role/mode prompt | role profile projection | public-safe examples use fake projects |
| Test/build commands | environment expectation / project pack metadata | safe if generic; redact private services |
| Tool permissions | capability policy metadata | values public-safe only when not tied to secrets/admin systems |
| MCP/tool binding | declarative capability reference | no server start, no secret values |
| Task handoff summary | reviewed project memory candidate | private by default; public only if redacted |
| Terminal/browser trace | runtime evidence / backup-only | not canonical; not public |
| Code index/repo map/embedding cache | rebuildable runtime cache | never Git canonical |
| Provider/model credential | local environment binding | never public; never Git value |

## Public-safety and Git boundary

Keep out of Git and public reports:

- raw conversations, terminal output, browser traces, screenshots, execution logs, and telemetry;
- repository indexes, embeddings, cached source snapshots, and generated context windows;
- `.env` values, API keys, OAuth tokens, MCP secrets, webhooks, provider endpoints, and private connection strings;
- private repo names, customer/project identifiers, local absolute paths, issue URLs, or internal deployment commands unless redacted;
- unreviewed instructions that could contain prompt injection or unsafe tool-use guidance.

Safe public artifacts:

- fake workspace-pack examples;
- redacted rule inventory reports;
- role-profile examples for generic architect/coder/reviewer/tester modes;
- capability-delta examples with dummy tools and fake paths;
- docs explaining what is canonical, private, backup-only, and runtime/cache.

## Follow-up verification questions

Before building a real adapter, verify against current upstream docs/code:

1. Which instruction and rule filenames are currently supported by Continue.dev, Cline, Roo Code, Aider, and OpenHands?
2. Which config files are user-global vs repo-local vs workspace-local?
3. How do these agents represent tool approvals, MCP bindings, auto-approval rules, and dangerous actions?
4. Which handoff/checkpoint artifacts are user-exportable without scraping raw chats?
5. Which settings contain model/provider credentials or endpoints and therefore must remain local/private?
6. How should rule precedence be handled when the same repo has `AGENTS.md`, `CLAUDE.md`, `.clinerules`, `.aider*`, and IDE-specific rule files?
7. What public-safe examples best demonstrate migration from one coding agent to another without implying lossless runtime-state migration?

## Summary judgment

Coding-agent workspace portability is directly aligned with Portable AI Assets' core thesis: users should own the durable parts of their AI work environment when changing tools, models, clients, or machines. Portable AI Assets should adopt workspace packs, role profiles, task handoff candidates, instruction conflict checks, and capability-delta previews. It should explicitly avoid becoming a coding-agent runtime or copying raw chats, terminal traces, caches, credentials, or sandbox state into Git. The safe implementation path is read-only inventory, candidate generation, reviewed workspace packs, projection preview, capability review, and only then narrow human-reviewed adapter writes.
