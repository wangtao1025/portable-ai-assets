# Portable Bootstrap Design

Updated: 2026-04-23

## Goal

Make `AI-Assets` self-bootstrapping on a new or partially used machine.

Desired UX:

```bash
git clone <private-repo> ~/AI-Assets
cd ~/AI-Assets
./bootstrap/setup/bootstrap-ai-assets.sh
```

The command should inspect the local machine, detect what is installed, compare local runtime state with canonical assets, and then propose or apply safe updates.

---

## Core design principle

Do **not** assume a clean machine.

The bootstrap must support three states:

1. **Fresh machine** — tool not installed yet
2. **Existing machine** — tool installed, but no prior AI-Assets wiring
3. **Diverged machine** — tool installed and already used, possibly on a newer major version or with changed file conventions

That means this system must be **discovery-first**, not path-hardcoded-only.

---

## Why this is better than only static backup

A static backup helps recovery.
A bootstrap command helps **migration and reattachment**.

It should answer:

- Is Claude installed here?
- Is Codex installed here?
- Is Hermes installed here?
- Is MemPalace present here?
- Is oh-my-codex present?
- Are hooks already wired?
- Are local adapter files newer or user-modified?
- Did upstream rename `AGENTS.md` or move config locations?

---

## Required behavior

### 1. Environment discovery

Bootstrap should detect:

- presence of `~/.hermes`
- presence of `~/.claude`
- presence of `~/.codex`
- presence of `~/.mempalace-auto`
- presence of MemPalace venv / executable
- presence of oh-my-codex via AGENTS/hook signatures or npm package
- presence of Claude-specific plugin/skill directories

### 2. Version-aware adapters

Do not assume exact filenames forever.

Instead use a layered resolver:

1. explicit paths from `AI-Assets/stack/*.yaml`
2. known default paths for current versions
3. signature-based discovery
4. user confirmation only if discovery fails materially

Example:

- if future Codex no longer uses `AGENTS.md`, search for:
  - known replacement files from manifest
  - recognizable OMX markers / runtime signatures
  - installed package metadata
  - hook registration patterns

### 3. Drift handling

Never blindly overwrite a live machine.

For each sync target, classify into one of these states:

- `missing`
- `managed-and-matches`
- `managed-but-drifted`
- `present-but-unmanaged`
- `unknown-version-layout`

Recommended action then depends on state.

### 4. Safe update model

The bootstrap should default to:

- inspect
- diff
- backup
- then write

Never first-write live runtime files without:

- creating a timestamped local backup
- logging what changed
- knowing whether the target is managed or user-diverged

---

## Proposed command surfaces

### A. Inspect only

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --inspect
```

Outputs:
- discovered tools
- discovered paths
- detected versions or signatures
- managed/drifted/missing state per adapter and bridge

### B. Plan mode

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --plan
```

Outputs:
- what would be installed
- what would be linked
- what would be synced
- what is unsafe to auto-update

### C. Apply safe changes

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --apply
```

Does only reversible, local, low-risk operations.

### D. Force or expert mode

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --apply --force-managed-overwrite
```

Only for explicit operator intent.

---

## Discovery strategies by tool

### Hermes

Primary signals:
- `~/.hermes/config.yaml`
- `~/.hermes/memories/`
- `~/.hermes/skills/`

### Claude

Primary signals:
- `~/.claude/CLAUDE.md`
- `~/.claude/settings.json`
- `~/.claude/plugins/`
- `~/.claude/skills/`

### Codex

Primary signals:
- `~/.codex/AGENTS.md`
- `~/.codex/hooks.json`
- `~/.codex/skills/`
- `~/.codex/agents/`

Secondary signals:
- oh-my-codex markers inside files
- npm global install or package resolution

### MemPalace

Primary signals:
- `~/.venvs/mempalace/bin/mempalace`
- `~/.mempalace-auto/bridge/`

Secondary signals:
- bridge hook references
- MemPalace config/runtime directories

---

## Handling upstream breaking changes

This is the key concern.

### Rule: never bind the system to one filename alone

Use a manifest schema like:

```yaml
adapter_resolution:
  codex:
    primary_candidates:
      - ~/.codex/AGENTS.md
    signature_markers:
      - "oh-my-codex"
      - "OMX"
      - "codex-native-hook"
    fallback_search_roots:
      - ~/.codex
    future_aliases: []
```

Then update the manifest when upstream moves things.

### Rule: preserve local unknown layouts

If bootstrap sees a plausible installed Codex layout but cannot map it confidently:

- classify as `unknown-version-layout`
- export findings to a report
- do not overwrite anything automatically

### Rule: manage by signature, not just by path

Examples of signatures:
- specific comment markers
- hook command fragments
- known JSON keys
- known directory shape
- package metadata

---

## Merge strategy for partially used new machines

This is the hardest case and must be first-class.

### Three-way model

For each target file compare:

- **canonical**: AI-Assets adapter version
- **local live**: file on current machine
- **base**: previous managed version if available

Actions:

- if local missing -> install canonical
- if local equals canonical -> no-op
- if local differs but still managed -> show diff, allow safe update
- if local has user changes -> back up and require explicit approval to replace

This is why future bootstrap should maintain a small machine-local state file recording last applied managed version hashes.

---

## Additional files to add later

Planned future files:

- `stack/resolvers.yaml` — path/signature discovery rules
- `bootstrap/state/` — last-applied hashes and machine-local apply records
- `bootstrap/reports/` — human-readable inspection reports
- `bootstrap/setup/bootstrap-ai-assets.sh` — main entrypoint
- `bootstrap/setup/bootstrap_ai_assets.py` — resolver / planner engine

---

## Recommended implementation phases

### Phase 1
- build inspect-only bootstrap
- detect installed tools and paths
- classify state
- write report

### Phase 2
- safe backup-before-write sync for adapters and bridges
- no package installs yet

### Phase 3
- optional installer integration for runtimes / plugins / bridge wiring
- support apply mode

### Phase 4
- drift-aware merge and version-layout resolver improvements

---

## Decision

Yes — your idea is the right direction.

The right end state is **not** just backup files.
It is:

- a Git-tracked canonical layer
- a non-Git backup layer
- a discovery-first bootstrap command
- version/layout drift handling
- safe merge/update logic for already-used machines

This should become the next major layer of `AI-Assets`.
