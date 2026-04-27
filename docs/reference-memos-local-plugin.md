# Reference Review — MemOS `memos-local-plugin`

Source inspected: <https://github.com/MemTensor/MemOS/tree/main/apps/memos-local-plugin>

Inspection snapshot:

- repository path inspected: `apps/memos-local-plugin/`
- commit inspected: `8c6cec6250ec398bcef508b7c2c4dab7afbbfe1c`
- package: `@memtensor/memos-local-plugin`
- version observed: `2.0.0-beta.1`

## What it is

`memos-local-plugin` is a local-first memory plugin for AI agents. It has one shared algorithm core and multiple agent adapters.

Its core model is Reflect2Evolve:

- **L1 trace** — grounded step/turn records
- **L2 policy** — cross-task strategies induced from traces
- **L3 world model** — compressed environment/world cognition
- **Skill** — crystallized callable capability derived from repeated high-value patterns

It also includes:

- TypeScript agent-agnostic core
- OpenClaw TypeScript adapter
- Hermes Python adapter via JSON-RPC bridge
- SQLite runtime store
- structured logging
- local viewer UI
- release/docs/test discipline

## Strong ideas worth absorbing

### 1. Explicit source/runtime separation

Their `AGENTS.md` and `ARCHITECTURE.md` are very strict:

- source code lives in the package
- user data/config live under `~/.<agent>/memos-plugin/`
- all user-home paths are resolved through a single config/path layer
- install/upgrade/uninstall never touches runtime data blindly

This strongly reinforces our current public-engine/private-assets split:

- public engine repo should not contain real user memory
- private asset root should be configured explicitly
- runtime DB/log/session state should remain non-Git or exported through review gates

Potential adoption:

- keep `portable_ai_assets_paths.py` as the only path resolver
- document “no direct user-home writes outside path resolver” as a project rule
- add a future lint/check that searches for hardcoded `~/.hermes`, `~/.claude`, etc. outside allowed modules

### 2. Agent-agnostic core plus adapter contract

MemOS uses:

- `core/` for agent-agnostic logic
- `agent-contract/` as the shared boundary
- `adapters/<agent>/` for host-specific behavior

This maps cleanly to our `schemas/adapter-contract-v1.json` and registry direction.

Potential adoption:

- formalize an `agent-contract/` or `contracts/` layer in Portable AI Assets
- keep adapter registry metadata separate from execution logic
- add contract docs for import/export/apply semantics, not just manifest schema

### 3. Runtime memory is richer than canonical memory

MemOS uses SQLite for rich runtime memory:

- traces
- episodes
- feedback
- policies
- world model
- skills
- audit events
- vectors

This validates our distinction:

- runtime memory may be high-dimensional, noisy, evolving, and database-backed
- Git should store curated canonical summaries / manifests / adapter views
- raw runtime DBs belong in non-Git backups or import pipelines, not directly in canonical Git

Potential adoption:

- add explicit “runtime memory backend adapter” class separate from “canonical asset adapter”
- support import summaries from DB-backed memory systems without pretending their DB is the canonical source

### 4. Multi-layer memory taxonomy

MemOS’s L1/L2/L3/Skill taxonomy is useful as a vocabulary:

- L1: raw traces / episodes
- L2: recurring strategies / policies
- L3: world model / environment abstraction
- Skill: callable crystallized procedure

Portable AI Assets does not need to become a memory backend, but it can use this taxonomy for canonical asset classes.

Potential adoption:

- add optional canonical directories or schema classes for:
  - `memory/traces/` or raw imports — non-Git by default
  - `memory/policies/` — curated strategy summaries
  - `memory/world-models/` — durable environment abstractions
  - `skills/` — portable callable procedures
- keep these optional so the project remains a portability layer, not a competing runtime

### 5. Retrieval/injection discipline

MemOS has a three-tier retrieval pipeline:

1. skills
2. traces/episodes
3. world model

It also emphasizes prompt-size control and summary-vs-full skill injection.

Potential adoption:

- when generating adapter views for Claude/Codex/Hermes, distinguish:
  - compact summary injection
  - full detail available by reference
- avoid dumping entire memory files into runtime instruction surfaces
- add adapter metadata for “summary projection” vs “full export”

### 6. Skill lifecycle and reliability score

MemOS skills have:

- `probationary | active | retired`
- reliability `η`
- trials attempted/passed
- source policy/world-model lineage

This is directly useful for our portable skills/workflows story.

Potential adoption:

- define a portable skill manifest with:
  - status
  - reliability/confidence
  - source evidence
  - applicability boundaries
  - verification steps
- do not treat every generated skill as immediately canonical; require review / probation / evidence

### 7. Observability as product surface

MemOS treats logs/events/viewer as first-class:

- structured log channels
- audit log
- LLM/perf/event logs
- SSE viewer
- deterministic frontend validation docs

Potential adoption:

- keep our report artifacts as the first observability layer
- add event/audit naming conventions for future apply/sync operations
- add “say/run X, expect Y report” demos for public release

### 8. Strong documentation and module completion checklist

Their `AGENTS.md` requires:

- every module has README
- every module has tests
- events documented
- migrations documented
- release notes required

Potential adoption:

- add a lightweight `docs/module-completion-checklist.md`
- require new bootstrap modes to include:
  - docs
  - tests
  - report shape
  - public/private safety notes

## What not to absorb directly

### 1. Do not become the same product

MemOS is a runtime memory backend / plugin with algorithmic learning. Portable AI Assets should remain the portability, ownership, schema, adapter, refresh, and review layer above such systems.

### 2. Do not commit raw SQLite memory into Git

MemOS’s DB schema is valuable, but its DB is runtime state. Our Git layer should import curated summaries, policies, skills, and adapter views only after review.

### 3. Do not jump to executable plugin runtime too early

MemOS has real plugin execution surfaces. Our adapter layer should stay metadata-first for now, then add built-in safe connectors before arbitrary plugin execution.

### 4. Do not require Node/SQLite for the core Portable AI Assets workflow

MemOS is Node/TypeScript-heavy. Portable AI Assets should keep a lightweight bootstrap path that works with shell/Python and can integrate with many backends.

## Concrete roadmap recommendations

### Phase 26 — External memory backend reference notes

Status: this document.

Capture lessons from MemOS and similar systems without merging their runtime model into our canonical layer.

### Phase 27 — Contract layer hardening

Add a formal `contracts/` or `agent-contract/` concept for:

- adapter metadata
- import/export action semantics
- event names
- report shape stability
- compatibility rules

### Phase 28 — Canonical memory taxonomy v1

Add optional schema/classes for:

- profile facts
- project summaries
- policies / playbooks
- world models
- skills
- raw runtime import snapshots — non-Git by default

### Phase 29 — Portable skill manifest

Create a portable skill manifest inspired by MemOS’s skill lifecycle:

- name
- status: `draft | probationary | active | retired`
- confidence/reliability
- trigger
- procedure
- verification
- boundaries
- source evidence links
- adapter projection hints

### Phase 30 — Runtime backend import adapters

Add `runtime_backend` adapter type for systems like MemOS:

- inspect DB/config paths
- summarize available memory layers
- export candidate canonical summaries
- never overwrite canonical memory without review

## Positioning takeaway

MemOS answers: “How can an agent learn locally from its own interaction traces?”

Portable AI Assets answers: “How can a user own, review, version, migrate, and project long-lived AI assets across agents, memory backends, and machines?”

They are complementary. MemOS-like systems can become one class of runtime backend that Portable AI Assets can inspect, summarize, and preserve.
