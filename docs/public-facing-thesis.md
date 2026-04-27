# Public-facing thesis

## One-minute explanation

Portable AI Assets System is a **portability layer for AI work environments**.

It is for people and teams who use multiple AI assistants, coding agents, memory systems, workflow builders, and local machines — and do not want their accumulated AI memory, skills, prompts, project rules, tool bindings, and recovery procedures to be trapped inside any single runtime.

The project turns those scattered pieces into reviewed, versionable, public/private-aware assets that can be inspected, diffed, packaged, restored, and projected into different AI runtimes.

## The core promise

> Change tools, models, clients, or machines without starting your AI environment from scratch.

## Why this exists

AI users are accumulating durable work value in places that were not designed to be the long-term source of truth:

- chat memory inside one app
- IDE or coding-agent instruction files
- project rules such as `AGENTS.md`, `CLAUDE.md`, or editor rule folders
- prompt and skill directories
- MCP/tool bindings and capability metadata
- workflow builder exports
- local bootstrap scripts and restore notes
- runtime histories, databases, caches, and session traces

When any one of those systems changes, disappears, drifts, or stays on an old machine, continuity breaks.

Portable AI Assets System exists so the durable parts can live in a canonical asset layer, while runtime-specific state remains either a projection, a reviewed candidate, or a non-Git backup.

## Three concrete scenarios

### 1. Switching agents or clients

A user has useful memory, instructions, and project rules spread across Hermes, Claude Code, Codex, IDE assistants, MCP configs, and other tools.

Portable AI Assets keeps a canonical representation of the durable assets, then projects reviewed views into runtime-specific surfaces instead of making any one runtime the only truth.

### 2. Moving to a new machine

A new laptop should not mean rebuilding the AI work environment from memory.

The project separates:

- public engine code and schemas
- private canonical memory/assets
- local runtime state and backups
- machine-local config pointers

That makes restore and rebootstrap explicit instead of relying on ad-hoc dotfile copying.

### 3. Sharing a team/project AI pack safely

A team may want shared project instructions, playbooks, role profiles, capability policies, and workflow metadata.

Portable AI Assets treats those as reviewable project/team packs with public/private boundaries, capability-risk classification, and report-only previews before any apply behavior.

## What this is not

Portable AI Assets System is not:

- an agent runtime
- a chat UI
- a model server
- a memory SaaS
- a workflow builder
- an MCP host
- a credential broker
- a universal lossless migration guarantee

It is the layer above those systems: the ownership, portability, review, and recovery layer for long-lived AI assets.

## How it differs from adjacent tools

Adjacent tools usually optimize one layer:

- memory systems remember and retrieve context
- workflow builders orchestrate apps and agents
- MCP standardizes tool/resource access
- IDE assistants store project-local rules and chats
- dotfiles/devcontainers bootstrap developer environments

Portable AI Assets connects those concerns through a conservative asset model:

1. canonical source first
2. runtime projections second
3. raw runtime data outside Git
4. report-only inventory before apply
5. human-reviewed candidates for risky changes
6. public engine separated from private assets

## Public/private boundary

The open-source project should publish:

- bootstrap engine
- schemas
- sample assets
- adapter contracts
- report-only gates
- public-safe examples
- release and safety tooling

A real user's private repo should keep:

- personal memory
- private project summaries
- private adapters
- team/project-specific asset packs
- reviewed skill manifests
- local config and backup references

Raw runtime databases, session histories, embeddings, logs, caches, credentials, tokens, provider state, and private identifiers stay out of public docs and out of Git canonical assets unless explicitly redacted and reviewed.

## A good first public demo

A public v0.1 demo should prove a narrow thesis:

1. load public-safe sample assets
2. validate schemas
3. inventory adapters and capabilities
4. preview projections without writing runtime files
5. show public/private boundaries
6. generate release/public-safety reports

The demo should optimize for trust and legibility, not breadth.

## Success criterion

A new reader should understand within one minute:

- this project is not another AI app
- it protects the user's long-lived AI assets from runtime lock-in
- it favors explicit review, safety gates, and public/private separation
- it is useful because AI work increasingly spans many agents, models, tools, and machines
