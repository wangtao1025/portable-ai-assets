# Capability Policy Preview Reference Review

Phase: 61
Status: reviewed
Reference family: capability delta reporting, project/team pack governance, shared apply readiness, and non-executing policy previews.

Capability policy preview turns the capability-risk vocabulary and project-pack preview data into a practical before/after review gate. The goal is not to enforce policy or execute capabilities. The goal is to show humans how current project/team pack capability declarations differ from a reviewed baseline before any future shared apply behavior exists.

## What this phase implements

Portable AI Assets now has a report-only gate:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-preview --both
```

It compares:

- reviewed baseline capabilities from `sample-assets/capability-policy/baseline.yaml` or future private `capability-policy/baseline.yaml`;
- current capabilities discovered from project pack and team pack previews.

It reports:

- added capabilities;
- removed capabilities;
- changed capabilities;
- risk upgrades;
- risk downgrades;
- current risk-class counts;
- current policy-outcome counts;
- explicit `executes_anything: false`.

## Safety boundary

The preview is non-executing and non-mutating. It must not:

- run hooks, code, scripts, MCP tools, workflow nodes, or custom agents;
- call providers, APIs, webhooks, hosted assistant actions, or admin endpoints;
- authenticate, validate, or reveal credentials;
- mutate team packs, project packs, adapters, runtime state, Git remotes, or hosted workspaces.

## What Portable AI Assets should adopt

1. Require human review for added, removed, changed, or risk-upgraded capabilities before any shared/project/team apply behavior.
2. Treat reviewed capability baselines as private/canonical governance assets.
3. Keep public examples fake and public-safe.
4. Route higher-risk outcomes (`review-required`, `manual-only`, `blocked-public`) into candidate/review/apply or manual-only flows.

## What Portable AI Assets should avoid

- Do not become a policy enforcement engine.
- Do not infer real runtime permission state from declarative YAML alone.
- Do not auto-update baselines from current declarations without review.
- Do not publish credential values, endpoint secrets, OAuth tokens, webhook URLs, tenant IDs, workspace IDs, action payloads, or execution traces.

## Future follow-up

A future reviewed apply gate may let humans explicitly accept capability policy baseline changes, but it should write only reviewed baseline files and still avoid mutating live runtimes or provider settings.
