# Architecture

## Thesis

Portable AI Assets System is a **canonical asset layer above AI runtimes**.

It does not try to replace Hermes, Claude Code, Codex, MemPalace, or future runtimes.
It provides a durable place to store and reconcile the assets that would otherwise be trapped inside those runtimes.

---

## Layer model

### 1. Canonical layer
Git-tracked, human-reviewable assets:
- memory summaries
- preferences and project summaries
- adapter source files
- manifests
- schemas
- policies
- bootstrap scripts
- docs and examples

### 2. Adapter layer
Runtime-specific projections derived from canonical assets:
- Hermes memory views
- `CLAUDE.md`
- `AGENTS.md`
- hook or bridge descriptors
- tool-specific instruction adapters
- adapter contract manifests in `adapters/registry/`

These are portability surfaces, not the only truth.

### 3. Runtime layer
Machine-local state owned by specific tools:
- session logs
- JSONL histories
- sqlite databases
- caches
- lock files
- generated corpora
- local plugin state

This layer is important to preserve, but should not be the primary canonical source.

### 4. Backup layer
Non-Git, cold-storage copies of high-value runtime state:
- runtime DBs
- session archives
- bridge corpora
- local instruction snapshots
- redacted review artifacts when needed

---

## Control plane vs data plane

### Control plane
The repo decides:
- what assets exist
- how they are classified
- which schema applies
- which targets are safe to auto-apply
- which targets require human review

### Data plane
The bootstrap pipeline reads and writes:
- local adapter files
- local backup directories
- machine-local reports
- managed-state hashes

This separation keeps the policy legible even when runtime layouts drift.

---

## Bootstrap pipeline

The intended lifecycle is:

1. `--inspect`
2. `--plan`
3. `--apply` for low-risk actions
4. `--diff`
5. `--merge-apply` for low-ambiguity drift
6. `--merge-candidates` for review bundles
7. `--review-apply` after explicit human approval
8. `--validate-schemas` to keep manifests machine-checkable

The system should remain useful even when only the early read-only phases are run.

---

## Safety model

### Low-risk targets
Examples:
- missing canonical-only files
- regenerated summaries
- validated manifests
- no-op matches

These may be auto-applied conservatively.

### High-risk targets
Examples:
- drifted instruction adapters
- files with local customization
- unknown version layouts
- targets where canonical and live both contain meaningful unique content

These should flow through:
- diff
- candidate bundle generation
- human review
- explicit reviewed merge apply

---

## Schema model

Schemas are intentionally lightweight at first.

They exist to answer:
- what class of manifest is this?
- are required keys present?
- can tooling reason about this file safely?

Current useful classes:
- stack manifest
- tool manifest
- bridge manifest
- architecture note

This is enough to make the repo inspectable and packageable without premature over-standardization.

---

## Public-open-source boundary

The public project should expose:
- engine
- schemas
- sample manifests
- sample assets
- docs
- tests

The private repo may additionally hold:
- real memory
- private project summaries
- non-redacted reports
- machine-local backups
- runtime-specific secrets

Portable AI Assets is designed so the public engine can be open-sourced without requiring publication of the private asset corpus.
