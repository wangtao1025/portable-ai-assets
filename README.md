# Portable AI Assets System

> **Own your AI work environment instead of rebuilding it every time you change tools, models, clients, or machines.**

Portable AI Assets System is a **portable AI assets layer** for cross-agent, cross-model, cross-client, and cross-machine continuity.

It is not another agent runtime, chat UI, memory SaaS, workflow builder, or MCP host. It is the layer above those systems: a canonical, reviewable, public/private-aware asset layer for the durable pieces of an AI work environment.

It turns fragmented AI state — memory, skills, prompts, project rules, workflows, adapters, tool bindings, capability policies, and bootstrap logic — into assets that are:

- versioned
- reviewable
- auditable
- backup-aware
- restorable
- portable across runtimes

**Core promise:** change tools or machines without starting your AI environment from scratch.

## 60-second overview

AI users increasingly accumulate valuable working context in many places: chat memories, IDE rules, `AGENTS.md`, `CLAUDE.md`, prompt folders, skills, MCP configs, workflow exports, runtime histories, and machine-local setup scripts.

The problem is that those pieces are usually trapped in one app, one agent, one filesystem layout, or one machine.

Portable AI Assets System makes the durable parts explicit:

1. **Canonical assets** — the reviewed source of truth for memory, skills, project rules, workflows, policies, and adapters.
2. **Runtime projections** — generated or reviewed views for tools such as coding agents, IDE assistants, memory systems, and workflow builders.
3. **Non-Git backups** — raw sessions, DBs, logs, caches, histories, and runtime-heavy state that should be preserved but not treated as canonical public assets.
4. **Safety/report gates** — inspect, diff, candidate, review, public-safety, release-readiness, and capability-governance reports before risky apply behavior.

Typical use cases:

- **Switch agents or clients:** keep long-lived memory, skills, project rules, and tool metadata portable instead of locked into one runtime.
- **Move to a new machine:** restore the AI work environment from public engine code + private asset repo + local config pointer.
- **Share a project/team AI pack safely:** preview project rules, playbooks, knowledge references, and capability risks before applying anything.

For the longer public thesis, see `docs/public-facing-thesis.md`.

## Fast public demo

To see the smallest public-safe story, run:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --demo-story --both
./bootstrap/setup/bootstrap-ai-assets.sh --public-demo-pack --both
```

Then review:

- `examples/redacted/demo-story.example.md`
- `examples/redacted/public-demo-pack/PACK-INDEX.md`
- `bootstrap/reports/latest-public-demo-pack.md`

The demo intentionally stays report-only/public-safe: it validates structure, previews adapter behavior, packages redacted evidence, and points to safety/release review reports without executing agents, providers, hooks, or live runtime actions.

---

## What problem this solves

AI power users and teams increasingly accumulate value in many different places:

- chat-local memory
- runtime-specific instruction files
- prompt/skill folders
- tool bindings and MCP configs
- workflow definitions
- local sessions and history
- machine-specific bootstrap scripts

That creates fragmentation:

- switching clients breaks continuity
- switching machines loses setup
- switching runtimes loses accumulated behavior
- drifted local files make migration risky

Portable AI Assets System provides a canonical layer above those runtimes.

---

## What this project is

This project is **not another agent runtime**.

It is a portability and ownership layer for long-lived AI assets:

- canonical memory and summaries
- skills / prompts / playbooks
- runtime adapters (`CLAUDE.md`, `AGENTS.md`, Hermes memory views, etc.)
- bootstrap / restore logic
- drift-aware inspection, diff, review, and apply flows

---

## Core ideas

1. **Canonical source first**
   - Runtime-local files are projections, not the only truth.

2. **Discovery before overwrite**
   - Existing machines may already have drift, history, and local customization.
   - Inspect and classify first; do not blindly replace.

3. **Git layer + non-Git layer**
   - Canonical text assets belong in Git.
   - Runtime-heavy sessions, caches, DBs, and histories belong in non-Git backups.

4. **Review-aware reconciliation**
   - Low-risk targets can be applied automatically.
   - Drifted targets should move through diff, candidate generation, human review, and only then apply.

---

## Current prototype capabilities

### Bootstrap pipeline

- `--inspect`
- `--plan`
- `--apply`
- `--diff`
- `--merge-apply`
- `--merge-candidates`
- `--review-apply`

### Review pipeline

- generate manual merge worksheets
- generate suggested merge drafts
- generate normalized final drafts
- apply reviewed merges with backup-before-write

### Asset model already represented in repo

- memory summaries
- adapters
- adapter registry contracts
- tool manifests
- MCP / bridge manifests
- rebuild / restore scripts
- backup policies
- sample adapter contracts
- portable skill manifests

---

## Why this matters

Existing open-source tooling usually solves one adjacent piece:

- memory systems
- workflow builders
- local runtimes
- tool protocols
- bootstrap scripts

This project focuses on the missing layer:

## **portable AI asset ownership and continuity**

The goal is simple:

> Change tools, models, or machines without starting your AI environment from scratch.

---

## Configuring a private asset root

The recommended real-world setup is:

- **public engine repo** for bootstrap code, schemas, docs, and sample assets
- **private asset repo** for canonical memory and user-specific adapters
- **local config pointer** at `~/.config/portable-ai-assets/config.yaml`

Example config:

```yaml
engine_root: ~/portable-ai-assets-engine
asset_root: ~/AI-Assets-private
asset_repo_remote: git@github.com:example/private-ai-assets.git
default_sync_mode: review-before-commit
allow_auto_commit: false
```

Commands:

```bash
# inspect current binding
./bootstrap/setup/bootstrap-ai-assets.sh --show-config

# initialize a new private asset repo and write local config
./bootstrap/setup/bootstrap-ai-assets.sh --init-private-assets ~/AI-Assets-private \
  --asset-repo-remote git@github.com:example/private-ai-assets.git \
  --both

# refresh runtime-derived memory into the configured private asset root
./bootstrap/setup/bootstrap-ai-assets.sh --refresh-canonical-assets --both

# inspect private asset repo Git/diff readiness before commit/push
./bootstrap/setup/bootstrap-ai-assets.sh --private-assets-status --both

# inspect whether MemOS local plugin is safe to try with Hermes
./bootstrap/setup/bootstrap-ai-assets.sh --memos-health --both

# read-only preview of what MemOS DB could contribute to canonical assets
./bootstrap/setup/bootstrap-ai-assets.sh --memos-import-preview --both

# generate review-only portable skill candidates from MemOS skills table
./bootstrap/setup/bootstrap-ai-assets.sh --memos-skill-candidates --both

# inspect candidate bundles and reviewed skill files before apply
./bootstrap/setup/bootstrap-ai-assets.sh --skill-candidates-status --both

# copy only human-reviewed *.reviewed.yaml files into canonical skills/
./bootstrap/setup/bootstrap-ai-assets.sh --skill-review-apply --both

# preview how active/probationary skills would project into runtime adapters
./bootstrap/setup/bootstrap-ai-assets.sh --skill-projection-preview --both

# generate review bundles for skill projections without writing adapters
./bootstrap/setup/bootstrap-ai-assets.sh --skill-projection-candidates --both

# inspect reviewed skill projection files before applying to adapters
./bootstrap/setup/bootstrap-ai-assets.sh --skill-projection-status --both

# append only reviewed skill projections into canonical adapter files
./bootstrap/setup/bootstrap-ai-assets.sh --skill-projection-review-apply --both

# scan the public/demo surface for secret-like strings and private absolute paths
./bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both

# aggregate release readiness gates before publishing
./bootstrap/setup/bootstrap-ai-assets.sh --release-readiness --both

# export a redacted public release directory with manifest and checksums
./bootstrap/setup/bootstrap-ai-assets.sh --public-release-pack --both

# archive the latest public release pack and write archive checksum
./bootstrap/setup/bootstrap-ai-assets.sh --public-release-archive --both

# extract and smoke-test the latest public archive/pack
./bootstrap/setup/bootstrap-ai-assets.sh --public-release-smoke-test --both

# generate/check GitHub publishing materials without pushing
./bootstrap/setup/bootstrap-ai-assets.sh --github-publish-check --both

# generate a GitHub-ready public staging working tree without committing/pushing
./bootstrap/setup/bootstrap-ai-assets.sh --public-repo-staging --both

# inspect staging repo git status / branch / remote without committing
./bootstrap/setup/bootstrap-ai-assets.sh --public-repo-staging-status --both

# generate GitHub publish command drafts without executing them
./bootstrap/setup/bootstrap-ai-assets.sh --github-publish-dry-run --both

# generate a reviewer handoff pack for manual GitHub publication
./bootstrap/setup/bootstrap-ai-assets.sh --github-handoff-pack --both

# run final publication preflight across all GitHub/release gates
./bootstrap/setup/bootstrap-ai-assets.sh --github-final-preflight --both

# write unsigned public release provenance with archive/tree digests
./bootstrap/setup/bootstrap-ai-assets.sh --release-provenance --both

# verify the latest provenance against current local artifacts
./bootstrap/setup/bootstrap-ai-assets.sh --verify-release-provenance --both

# inventory portable skill manifests and lifecycle status
./bootstrap/setup/bootstrap-ai-assets.sh --skills-inventory --both

# inventory external reference systems and adopted lessons
./bootstrap/setup/bootstrap-ai-assets.sh --external-reference-inventory --both

# track candidate external projects to review before reinventing
./bootstrap/setup/bootstrap-ai-assets.sh --external-reference-backlog --both

# preview public-safe team asset packs and role/profile layering
./bootstrap/setup/bootstrap-ai-assets.sh --team-pack-preview --both

# preview public-safe project packs, knowledge references, actions, and capability risks
./bootstrap/setup/bootstrap-ai-assets.sh --project-pack-preview --both

# inventory capability-bearing adapter/team/project-pack metadata without executing anything
./bootstrap/setup/bootstrap-ai-assets.sh --capability-risk-inventory --both

# compare current project/team capabilities against a reviewed capability baseline
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-preview --both

# generate a reviewed baseline template without creating the reviewed baseline
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-candidate-generation --both

# report whether the human-reviewed candidate baseline is ready to apply
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-candidate-status --both

# apply a human-created reviewed capability baseline only, with backup
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-baseline-apply --both

# review completed work for roadmap alignment, safety, and external learning before advancing
./bootstrap/setup/bootstrap-ai-assets.sh --completed-work-review --both
```

`--init-private-assets` creates the private repo scaffold (`memory/`, `adapters/`, `stack/`, reports/candidates folders, `.gitignore`, `GIT-POLICY.md`) and initializes Git locally. It does **not** auto-push memory.

`--private-assets-status` is a report-only review gate. It checks whether the active private asset root is a Git repo, whether it has a remote, what files changed, which asset categories changed, and what the next safe sync step should be.

You can also override the active private asset root for one run:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --refresh-canonical-assets --both --asset-root ~/AI-Assets-private
```

A public-safe example config is available at:

- `sample-assets/config/portable-ai-assets.config.example.yaml`

---

## Repository structure

- `memory/` — canonical memory and summaries
- `adapters/` — runtime-specific projections
- `stack/` — manifests for tools, bridges, and topology
- `skills/` — private portable skill manifests promoted through review
- `sample-assets/skills/` — public-safe portable skill examples
- `bootstrap/` — inspection, planning, diff, apply, and candidate generation flows
- `docs/` — design, positioning, and roadmap documents
- `non-git-backups/` — runtime-heavy cold backups (not for public open-source release)

---

## Recommended open-source release shape

### Public

- engine / CLI
- schemas / manifests
- adapter framework
- policies / templates
- example asset packs
- docs and roadmap

### Private by default

- real personal memory
- private project summaries
- sensitive local runtime state
- secrets / tokens / credentials

---

## Audience

Best suited for:

- AI-native power users
- indie hackers
- local-first developers
- multi-agent experimenters
- small teams that want portable AI workflows

---

## Status

This is already a working prototype, not just a concept.

Implemented phases include:

- inspect-only discovery
- safe planning
- conservative apply
- diff / merge guidance
- manual review bundles
- review-assisted apply
- target-aware smarter draft synthesis
- normalized final draft cleanup
- schema validation and sample assets
- adapter SDK metadata and connector inventory

See also:

- `docs/architecture.md`
- `docs/non-goals.md`
- `docs/adapter-sdk.md`
- `docs/open-source-demo-story.md`
- `docs/open-source-demo-pack.md`
- `docs/public-facing-thesis.md`
- `docs/private-memory-repo-pattern.md`
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
- `docs/reference-capability-risk-policy-gates.md`
- `docs/reference-capability-policy-report-implementation.md`
- `docs/reference-project-pack-preview.md`
- `docs/reference-capability-policy-preview.md`
- `docs/capability-policy-candidate-generation.md`
- `docs/reference-capability-policy-candidate-generation.md`
- `docs/capability-policy-candidate-status.md`
- `docs/reference-capability-policy-candidate-status.md`
- `docs/reference-capability-policy-baseline-apply.md`
- `docs/completed-work-review.md`
- `docs/reference-completed-work-review.md`
- `docs/external-reference-strategy.md`
- `docs/external-reference-backlog.md`
- `docs/memos-hermes-adoption-plan.md`
- `docs/team-grade-packaging.md`
- `docs/open-source-positioning.md`
- `docs/public-roadmap.md`
- `docs/security-model.md`
- `docs/open-source-release-plan.md`
- `examples/redacted/README.md`

---

## Project thesis

Users should own their AI assets.
Not any single runtime.
Not any single platform.
Not any single machine.
