# Capability Policy Baseline Apply

Capability policy baseline apply is a reviewed apply gate for capability governance metadata.

Run:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-baseline-apply --both
```

## Input

The command looks for a human-created reviewed file:

```text
bootstrap/candidates/capability-policy/reviewed-baseline.yaml
```

That file must contain a non-empty `capabilities:` list where each item has:

- `name`
- `risk_class`
- `policy_outcome`

## Output

If the reviewed file exists and validates, the command:

1. backs up the current baseline under `bootstrap/backups/capability-policy-baseline-apply-<timestamp>/baseline.yaml`;
2. writes the reviewed baseline into the active baseline path;
3. emits `latest-capability-policy-baseline-apply.json/md`.

If the reviewed file is missing, it skips safely. If it is invalid, it blocks safely.

## Safety boundary

This gate writes only the reviewed baseline file. It must not:

- execute actions, hooks, scripts, MCP tools, or custom agents;
- call providers, APIs, webhooks, or hosted admin endpoints;
- authenticate or validate credentials;
- mutate live runtimes, hosted workspaces, provider settings, Git remotes, or runtime adapter files.

## Review workflow

1. Run `--capability-policy-preview --both`.
2. Review added/removed/changed/risk-upgraded capabilities.
3. Create `bootstrap/candidates/capability-policy/reviewed-baseline.yaml` manually.
4. Run `--capability-policy-baseline-apply --both`.
5. Inspect the diff and commit baseline changes explicitly if desired.
