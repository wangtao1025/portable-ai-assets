# Capability Policy Preview

Capability policy preview compares a reviewed baseline of capability metadata against the current capabilities declared by project and team packs.

Run:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-preview --both
```

## What it reports

- added capabilities;
- removed capabilities;
- changed risk classes or policy outcomes;
- risk upgrades and downgrades;
- current risk-class counts;
- current policy-outcome counts;
- whether anything executes (`false`).

## Safety boundary

This mode is report-only. It must not:

- execute actions, hooks, MCP tools, scripts, or custom agents;
- call providers, APIs, webhooks, or hosted admin endpoints;
- authenticate or validate credentials;
- mutate project packs, team packs, adapters, live runtimes, Git remotes, or hosted workspaces.

## Review model

A human should review added, removed, changed, or risk-upgraded capabilities before any future project/team/shared apply behavior. Only after approval should the reviewed baseline be updated.
