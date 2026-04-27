# Project Pack Preview Reference Review

Phase: 60
Status: reviewed
Reference family: hosted project assistants, project-scoped instructions, knowledge-source membership, actions/tool metadata, adapter projections, and capability deltas.

Project packs extend team-pack packaging into a project-scoped asset bundle. The goal is not to mirror provider-hosted assistant state. The goal is to make project instructions, curated knowledge membership, adapter projections, and action/capability metadata reviewable before they are projected into any runtime.

## What this phase implements

Portable AI Assets now has a report-only project pack preview gate:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --project-pack-preview --both
```

It discovers project-pack manifests from:

- `sample-assets/project-pack/project-pack.yaml`
- future private/project roots such as `project-packs/*/project-pack.yaml`

It reports:

- project pack name, version, scope, visibility, shareability, and apply policy;
- referenced instruction, knowledge, action, and adapter files;
- missing references;
- declared capabilities;
- capability risk-class counts and policy-outcome counts;
- whether anything executes (`false`).

## Safety boundary

The preview is non-executing and non-mutating. It must not:

- create, update, or publish hosted assistant projects;
- upload knowledge files to providers;
- call action schemas, APIs, webhooks, MCP tools, or connectors;
- authenticate or validate credentials;
- execute project hooks, workflow code, custom agents, or scripts;
- write live runtime adapter files.

## What Portable AI Assets should adopt

1. Treat project pack manifests as durable private/canonical assets.
2. Keep instructions and curated knowledge-source membership separate from provider-hosted uploads, retrieval chunks, embeddings, chat histories, and action logs.
3. Make capability metadata explicit before shared apply behavior: risk class, policy outcome, visibility, and project scope.
4. Require candidate/review/apply gates before projecting project packs into hosted assistants, IDE assistants, MCP clients, or team-shared runtimes.

## What Portable AI Assets should avoid

- Do not become a hosted project assistant SaaS or GPT marketplace.
- Do not mirror provider-hosted chat history, uploaded storage, retrieval chunks, embeddings, action logs, workspace identifiers, OAuth tokens, webhook URLs, or credentials into Git.
- Do not treat public-safe samples as real project configuration.
- Do not auto-apply project pack capability changes from preview output.

## Future follow-up

A future capability delta gate can compare project-pack declarations against an existing reviewed target state and report additions/removals/upgrades before candidate/review/apply behavior exists.
