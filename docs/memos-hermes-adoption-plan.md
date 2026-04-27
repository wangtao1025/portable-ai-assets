# MemOS Local Plugin for Hermes — Adoption Plan

This document evaluates whether Hermes should use MemOS `memos-local-plugin` and how Portable AI Assets should integrate with it safely.

## Recommendation

Yes, it is worth trying — but not by immediately replacing existing Hermes memory in the main profile.

Recommended path:

1. treat MemOS as an optional **runtime memory backend**
2. test it in a separate Hermes profile or sandbox first
3. keep Portable AI Assets as the canonical ownership/review layer
4. import MemOS outputs into canonical candidates only after inspection
5. never commit raw MemOS SQLite/log state into Git

## Why it is promising

MemOS has strengths that Hermes could benefit from:

- local-first memory backend
- L1 trace capture
- L2 policy induction
- L3 world-model abstraction
- skill crystallization with lifecycle
- explicit feedback loops
- retrieval tiers for prompt injection
- Hermes adapter via JSON-RPC bridge
- clear source/runtime separation

This is stronger than simple flat memory because it can preserve not only facts, but also repeated strategies and learned capabilities.

## Why not enable blindly

During local feasibility checks, these commands timed out on this machine:

- `node --version`
- `npm --version`
- `hermes --version`
- `npm view @memtensor/memos-local-plugin ...`

Also, the MemOS Hermes runtime paths are not currently present:

- `~/.hermes/memos-plugin/` — not present
- `~/.hermes/plugins/memos-local-plugin/` — not present

So the safe next step is not “install into the live Hermes profile immediately”; it is “model it, inspect prerequisites, and add a test-profile enablement plan.”

## Safe enablement sequence

### 1. Fix/verify local command health

Before installation, verify:

```bash
node --version
npm --version
hermes --version
hermes plugins list
hermes memory status
```

If these hang, fix shell/runtime environment first.

### 2. Back up Hermes state

Before plugin install:

```bash
cp -a ~/.hermes ~/.hermes.backup-before-memos-$(date +%Y%m%d-%H%M%S)
```

Or use the existing non-Git backup flow once this is formalized.

### 3. Use a test Hermes profile first

Prefer a dedicated profile such as:

```bash
hermes profile create memos-test --clone
hermes -p memos-test plugins list
```

Then install/enable MemOS only in that profile.

### 4. Install through official mechanism

Based on MemOS docs, expected package is:

```bash
npm install -g @memtensor/memos-local-plugin
memos-local-plugin install hermes
```

But this should only be run after command health is confirmed and preferably in a test profile.

### 5. Observe runtime outputs

Expected Hermes MemOS runtime paths:

```text
~/.hermes/memos-plugin/config.yaml
~/.hermes/memos-plugin/data/memos.db
~/.hermes/memos-plugin/skills/
~/.hermes/memos-plugin/logs/
```

### 6. Import into Portable AI Assets via review candidates

Future import should generate candidates such as:

```text
memory/projects/*.md
memory/policies/*.md
memory/world-models/*.md
skills/*.yaml
bootstrap/reports/latest-memos-import-preview.md
```

The import should be report-first and review-required.

## Integration model

```text
Hermes runtime
  ↓ uses
MemOS runtime backend
  ↓ produces rich local DB/log/skill state
Portable AI Assets adapter
  ↓ summarizes into candidate canonical assets
private assets repo
  ↓ human review / commit / push
```

## What to build next

### A. `--memos-health` report ✅

Implemented command:

```bash
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --memos-health --both
```

Checks:

- Node/npm availability
- Hermes CLI availability
- MemOS package availability
- presence of `~/.hermes/memos-plugin/`
- presence of SQLite DB/config/logs
- whether plugin appears in `hermes plugins list`

### B. `--memos-import-preview` report ✅

Implemented command:

```bash
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --memos-import-preview --both
```

If DB exists, it inspects it read-only and reports:

- tables present
- row counts for traces/policies/world_model/skills
- latest updated timestamps
- candidate canonical outputs

It does not write canonical memory. It only maps possible future outputs such as:

- `memory/projects/<reviewed-from-memos>.md`
- `memory/policies/<reviewed-policy>.md`
- `memory/world-models/<reviewed-world-model>.md`
- `skills/<portable-skill>.yaml`

### C. Portable skill manifest ✅

Implemented schema and inventory:

```bash
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --skills-inventory --both
```

Use MemOS skill lifecycle as inspiration for a portable skill schema:

```yaml
name:
status: draft | probationary | active | retired
confidence:
trigger:
procedure:
verification:
boundaries:
source_evidence:
adapter_projection:
```

### D. `--memos-skill-candidates` review bundle ✅

Implemented command:

```bash
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --memos-skill-candidates --both
```

If the MemOS SQLite DB has a `skills` table, this reads it in SQLite read-only mode and generates:

```text
bootstrap/candidates/memos-skills-<timestamp>/
  001-<skill>.candidate.yaml
  REVIEW-INSTRUCTIONS.md
  SUMMARY.md
```

Generated candidates are intentionally downgraded to `probationary` unless the runtime source says `retired`. They are not copied into canonical `skills/` until reviewed.

### E. skill candidate status / review apply ✅

Implemented commands:

```bash
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --skill-candidates-status --both
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --skill-review-apply --both
```

Review convention:

```text
001-example.candidate.yaml   # machine-generated, not canonical
001-example.reviewed.yaml    # human-reviewed final portable skill manifest
```

`--skill-candidates-status` validates reviewed files and reports which are ready. `--skill-review-apply` copies only valid `*.reviewed.yaml` files into canonical `skills/<name>.yaml`, backing up existing targets first. It never applies raw candidate files.

### F. skill projection preview ✅

Implemented command:

```bash
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --skill-projection-preview --both
```

This previews how `active` and `probationary` portable skills would project into adapter targets declared under `adapter_projection`, for example:

```text
skills/reviewed-sync.yaml
  -> adapters/hermes/USER.md
  -> adapters/claude/instructions.md
  -> adapters/codex/instructions.md
```

It is preview-only: no adapter files or runtime files are modified.

### G. skill projection candidates ✅

Implemented command:

```bash
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --skill-projection-candidates --both
```

This turns the projection preview into reviewable candidate files under:

```text
bootstrap/candidates/skill-projections-<timestamp>/
  <runtime>.<adapter>.skill-projection.md
  REVIEW-INSTRUCTIONS.md
  SUMMARY.md
```

These files are review bundles only. They are not written into adapters and should not be treated as already-applied runtime instructions.

### H. skill projection status / review apply ✅

Implemented commands:

```bash
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --skill-projection-status --both
/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --skill-projection-review-apply --both
```

Review convention:

```text
hermes.USER.skill-projection.md  # generated candidate
hermes.USER.reviewed.md          # human-reviewed projection with Target adapter metadata
```

`--skill-projection-status` reports candidate/reviewed projection files and validates whether reviewed files have target metadata and non-empty content. `--skill-projection-review-apply` appends only reviewed projection blocks into canonical adapter files and backs up existing adapter targets first. It never applies raw `*.skill-projection.md` candidate files.

## Bottom line

MemOS is a good plugin to try for Hermes, but Portable AI Assets should integrate it as a runtime backend with safe import/review/export boundaries.

The ideal outcome is:

- Hermes gets richer live memory from MemOS
- Portable AI Assets preserves durable distilled outputs
- Git stays clean, reviewable, and portable
