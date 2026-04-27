# Capability Policy Candidate Generation

Capability policy candidate generation is a report-only helper for preparing reviewed baseline updates without bypassing human review.

Run:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-candidate-generation --both
```

## Input

The command reuses the capability policy preview inputs:

- reviewed baseline candidates from `sample-assets/capability-policy/baseline.yaml` or `capability-policy/baseline.yaml`;
- current capability declarations from public-safe project/team pack manifests.

## Output

The command writes or refreshes only:

```text
bootstrap/candidates/capability-policy/reviewed-baseline.yaml.template
```

It also emits:

```text
bootstrap/reports/latest-capability-policy-candidate-generation.json
bootstrap/reports/latest-capability-policy-candidate-generation.md
```

The report includes:

- `executes_anything: false`;
- template path and reviewed baseline path;
- added, removed, changed, risk-upgraded, and risk-downgraded capability counts;
- capability risk class counts;
- policy outcome counts;
- checks proving the reviewed baseline was not generated automatically.

## Safety boundary

This mode must not:

- create `bootstrap/candidates/capability-policy/reviewed-baseline.yaml`;
- run `--capability-policy-baseline-apply` automatically;
- execute actions, hooks, scripts, MCP tools, or custom agents;
- call providers, APIs, webhooks, or hosted admin endpoints;
- authenticate or validate credentials;
- mutate live runtimes, hosted workspaces, provider settings, Git remotes, credential bindings, or runtime adapter files.

## Review workflow

1. Run `--capability-policy-preview --both` and inspect capability deltas.
2. Run `--capability-policy-candidate-generation --both` to refresh the template.
3. Run `--capability-policy-candidate-status --both` to confirm that the template exists and whether human review is still required.
4. Review `reviewed-baseline.yaml.template` manually.
5. Copy the template to `reviewed-baseline.yaml` only after accepting the capability policy changes.
6. Run `--capability-policy-candidate-status --both` again to confirm the reviewed baseline validates and is synchronized.
7. Run `--capability-policy-baseline-apply --both` only when candidate status reports it is ready for apply.
8. Inspect the diff and commit baseline changes explicitly if desired.
