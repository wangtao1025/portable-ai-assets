# Capability Policy Report Implementation Reference

Phase: 59
Status: reviewed
Reference family: report-only implementation patterns for capability risk inventory and policy-preview gates.

This note records how Portable AI Assets should implement the Phase 58 capability-risk vocabulary without becoming an execution runtime or policy enforcement system.

## What this phase implements

Portable AI Assets now has a report-only capability inventory gate:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-risk-inventory --both
```

The gate inventories declarative capability metadata from:

- adapter registry connector contracts under `adapters/registry/*.yaml`;
- team pack manifests discovered by the existing team-pack preview path.

It classifies capabilities by coarse risk classes such as:

- `text-only`
- `read-only-data`
- `write-files`
- `external-network`
- `code-execution`
- `credential-binding`
- `admin-control`

and maps them into policy outcomes:

- `allow-preview`
- `review-required`
- `manual-only`
- `blocked-public`
- `out-of-scope`

## Safety boundary

The implementation is intentionally inventory-first and non-executing. It does not:

- start MCP servers;
- execute hooks, shell commands, scripts, or custom agents;
- call external APIs or webhooks;
- authenticate to providers;
- validate live credentials;
- mutate runtime files, Git remotes, hosted workspaces, or admin settings.

Every capability item records `executes_anything: false`, and the report includes a `no-execution` check.

## What Portable AI Assets should adopt

1. Treat capability metadata as a first-class release/readiness signal, not a hidden detail inside adapters or team packs.
2. Keep report-only inventory separate from future candidate/review/apply gates.
3. Classify risk cumulatively: a connector can be both `write-files` and `external-network`, and future manifests may add `credential-binding` or `code-execution` dimensions.
4. Include capability inventory in release readiness as a recommended gate so public/demo surfaces show that shared capability expansion is being reviewed.

## What Portable AI Assets should avoid

- Do not infer that a connector is safe just because it is declared in YAML.
- Do not execute unknown connector code to classify it.
- Do not publish credential values, webhook URLs, tokens, endpoint secrets, raw action payloads, execution traces, tenant IDs, or admin exports.
- Do not auto-apply shared/team/project-pack capability changes from this report.
- Do not turn this into an enterprise policy engine, MCP host, workflow runtime, hooks runner, cloud-agent scheduler, or credential manager.

## Future follow-up

A future `--capability-policy-preview` can compare before/after capability deltas for project packs or reviewed team-pack projection candidates. That preview should remain report-only until a separate human-reviewed apply gate exists.
