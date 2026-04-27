# Project Pack Preview

Project packs are project-scoped Portable AI Assets. They describe reusable project instructions, curated knowledge-source membership, adapter projection targets, and declarative action/capability metadata without mirroring hosted assistant runtime state.

## Purpose

A project pack preview answers:

- Which project-scoped instructions and knowledge files are referenced?
- Which adapter projection files would be involved in a future review/apply path?
- Which action or capability metadata is declared?
- Which risk classes and policy outcomes must be reviewed before any shared/project apply behavior?

## Safety boundary

`--project-pack-preview` is report-only. It must not:

- upload knowledge files to hosted providers;
- create or mutate hosted projects / Custom GPTs / Claude Projects;
- call action schemas or webhook/API endpoints;
- authenticate to providers;
- write adapter/runtime files;
- execute project hooks, MCP servers, custom agents, or workflow code.

## Recommended manifest fields

- `name`
- `pack_version`
- `asset_class`
- `shareability`
- `project_scope`
- `visibility`
- `instructions`
- `knowledge_sources`
- `actions`
- `adapters`
- `capabilities`
- `apply_policy`

Capability entries should include at least:

- `name`
- `risk_class`
- `policy_outcome`

## Future follow-up

A future capability delta report can compare current project-pack declarations against a reviewed target state before allowing any candidate/review/apply workflow.
