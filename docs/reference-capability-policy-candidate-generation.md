# Capability Policy Candidate Generation Reference

Phase: 64
Status: reviewed
Reference family: report-only baseline candidate generation, policy delta review, and human-reviewed capability governance.

This phase adds a candidate-generation step for reviewed capability baselines. It turns current project/team capability declarations into a baseline template, while preserving the rule that only a human-created `reviewed-baseline.yaml` can be applied.

## What this phase implements

Portable AI Assets now has:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-candidate-generation --both
```

The command writes:

```text
bootstrap/candidates/capability-policy/reviewed-baseline.yaml.template
```

It never writes:

```text
bootstrap/candidates/capability-policy/reviewed-baseline.yaml
```

The generated report includes current policy deltas, capability risk class counts, policy outcome counts, template path, reviewed baseline path, and `executes_anything: false`.

## Safety boundary

Candidate generation may write only the template and its latest report files. It must not:

- start or call MCP servers;
- execute actions, hooks, scripts, workflow nodes, or custom agents;
- call providers, APIs, webhooks, hosted assistant actions, or admin endpoints;
- authenticate or validate credentials;
- create the reviewed baseline file automatically;
- call the baseline apply gate automatically;
- mutate live runtime files, hosted workspaces, provider settings, Git remotes, credential bindings, or provider admin data.

## What Portable AI Assets should adopt

1. Generate templates from declarative capability metadata, not from runtime execution traces or provider state.
2. Preserve an explicit human review gap between template generation and baseline apply.
3. Report added, removed, changed, risk-upgraded, and risk-downgraded capabilities alongside risk classes and policy outcomes.
4. Keep candidate generation useful for reviewers while preventing template output from becoming an automatic approval path.

## What Portable AI Assets should avoid

- Do not auto-create `reviewed-baseline.yaml` from current declarations.
- Do not auto-run `--capability-policy-baseline-apply` after template generation.
- Do not treat low-risk current deltas as implicit approval.
- Do not include credential values, secret endpoints, tenant identifiers, provider admin exports, action payloads, or execution logs in baseline templates.

## Integration boundary

The safe integration boundary is report-only metadata transformation:

```text
capability policy preview/current declarations -> reviewed-baseline.yaml.template -> human review -> reviewed-baseline.yaml -> reviewed apply gate
```

The runtime and provider boundary remains outside this flow.
