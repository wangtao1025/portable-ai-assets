# Portable Skill Manifest v1

Portable Skill Manifest v1 defines how reusable AI procedures become canonical assets instead of being trapped inside one runtime's plugin database or instruction file.

## Goal

A portable skill is a reviewed, durable procedure with lifecycle metadata, evidence, boundaries, and runtime projection hints. It can be learned from systems such as MemOS, Hermes, Claude Code, Codex, or manual project practice, but it is not automatically trusted just because it appears in runtime memory.

## Required fields

```yaml
name: review-before-sync
skill_version: v1
status: draft | probationary | active | retired
confidence: low | medium | high
description: One-sentence purpose.
trigger: When to consider using the skill.
procedure:
  - Step one.
verification:
  - How to check the outcome.
boundaries:
  - What this skill must not do.
source_evidence:
  - type: project-pattern | runtime-import | human-authored | external-reference
    reference: docs/example.md
    note: Why this evidence matters.
adapter_projection:
  hermes: adapters/hermes/USER.md
  claude-code: adapters/claude/instructions.md
  codex: adapters/codex/instructions.md
```

## Lifecycle

- `draft`: captured idea, not trusted for repeated use.
- `probationary`: used successfully but still gathering evidence.
- `active`: reusable and verified enough to project into adapters.
- `retired`: kept for audit/history but should not be projected by default.

## Importing from runtime systems such as MemOS

Runtime skill stores can be much richer than the canonical Git layer. Portable AI Assets should import them as candidates first:

```text
MemOS skills table / runtime traces
  -> --memos-import-preview
  -> --memos-skill-candidates
  -> bootstrap/candidates/memos-skills-<timestamp>/*.candidate.yaml
  -> human review creates *.reviewed.yaml
  -> --skill-candidates-status
  -> --skill-review-apply
  -> skills/<name>.yaml in private asset repo
  -> --skill-projection-preview
  -> --skill-projection-candidates
  -> human review creates *.reviewed.md
  -> --skill-projection-status
  -> --skill-projection-review-apply
  -> adapter projection only if active/probationary and safe
```

Do not commit raw SQLite rows, logs, or traces as portable skills.

## Safety rules

- Prefer `draft` or `probationary` for imported runtime candidates.
- Require source evidence before `active`.
- Put destructive, credential-touching, or environment-specific behavior in `boundaries`.
- Keep adapter projection declarative; do not execute arbitrary plugin code from a skill manifest.
