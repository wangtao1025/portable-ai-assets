# Reviewed Capability Policy Baseline Apply Reference

Phase: 62
Status: reviewed
Reference family: human-reviewed capability governance baselines, baseline update gates, and non-runtime apply workflows.

This phase adds a narrow reviewed apply gate for capability policy baselines. It does not apply capabilities to runtimes. It only updates the reviewed baseline that future previews compare against.

## What this phase implements

Portable AI Assets now has:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-baseline-apply --both
```

The command reads:

```text
bootstrap/candidates/capability-policy/reviewed-baseline.yaml
```

If the file exists and validates, it backs up the current baseline and writes the reviewed baseline into the active baseline path. If the file is missing, it skips. If invalid, it blocks.

## Safety boundary

This apply gate may write only the reviewed capability baseline file. It must not:

- start or call MCP servers;
- execute actions, hooks, scripts, workflow nodes, or custom agents;
- call providers, APIs, webhooks, hosted assistant actions, or admin endpoints;
- authenticate or validate credentials;
- mutate live runtime files, hosted workspaces, provider settings, Git remotes, or credential bindings.

## What Portable AI Assets should adopt

1. Keep a clear separation between previewing capability deltas and accepting a reviewed baseline.
2. Require a human-created `reviewed-baseline.yaml`; never auto-generate and immediately apply the baseline from current runtime declarations.
3. Back up the previous baseline before writing.
4. Keep Git commit/push explicit after reviewing the diff.

## What Portable AI Assets should avoid

- Do not treat baseline acceptance as permission to enable capabilities in runtime systems.
- Do not update baselines automatically just because a preview is clean.
- Do not place credential values, endpoints, action payloads, tenant IDs, or execution logs in baseline files.
- Do not mutate provider policy/admin settings from this gate.

## Related reviewed gate

`--capability-policy-candidate-generation` may write a `reviewed-baseline.yaml.template` from the current preview/current declarations. `--capability-policy-candidate-status` should be run before apply to report whether the template exists, whether a human-created `reviewed-baseline.yaml` exists, whether it validates, whether it is synchronized with current capability declarations, and whether it is ready for `--capability-policy-baseline-apply`. Applying still requires a human-created `reviewed-baseline.yaml` file.
