# Capability Policy Candidate Status Reference

Phase: 65
Status: reviewed
Reference family: report-only candidate review status, human-reviewed baseline readiness, and non-executing capability governance.

This phase adds a read-only status gate for capability policy baseline candidates. It answers whether the generated template, optional human-created reviewed baseline, validation results, and current preview are ready for the narrow reviewed apply gate.

## What this phase implements

Portable AI Assets now has:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-candidate-status --both
```

The command reads candidate and baseline files, then reports:

- template existence;
- reviewed baseline existence;
- reviewed baseline validation status;
- reviewed-vs-current synchronization deltas;
- `apply_readiness` and `ready_for_apply`;
- policy outcome counts and risk class counts;
- `reviewer_guidance` containing the next human action, review checklist, safe file paths, and non-executing command drafts;
- `review_handoff_audit` containing read-only preflight evidence, candidate/reviewed/current baseline hashes where files exist, handoff steps, `writes_anything: false`, and `executes_anything: false`;
- `executes_anything: false`;
- zero write counters for templates and reviewed baselines.

## Safety boundary

Candidate status is strictly report-only. It must not:

- write or refresh `reviewed-baseline.yaml.template`;
- create or modify `reviewed-baseline.yaml`;
- call `--capability-policy-baseline-apply`;
- start or call MCP servers;
- execute actions, hooks, scripts, workflow nodes, or custom agents;
- call providers, APIs, webhooks, hosted assistant actions, or admin endpoints;
- authenticate or validate credentials;
- mutate runtime adapter files, hosted workspaces, provider settings, Git remotes, credential bindings, or provider admin data.

## What Portable AI Assets should adopt

1. Place an explicit report-only readiness check between generated templates and reviewed apply.
2. Distinguish “template exists” from “human-reviewed baseline exists”.
3. Treat missing reviewed baselines as `needs-human-review`, not as an error that should be auto-fixed.
4. Treat invalid or out-of-sync reviewed baselines as not ready for apply.
5. Keep delta/risk/policy summaries visible in every governance stage so reviewers do not approve blind file writes.
6. Surface reviewer guidance in status output as non-executing instructions, not automation.
7. Add review handoff audit evidence (file presence, hashes, and preflight checklist) so humans can reproduce what was reviewed without expanding the apply surface.

## What Portable AI Assets should avoid

- Do not auto-copy `reviewed-baseline.yaml.template` to `reviewed-baseline.yaml`.
- Do not let command drafts in reviewer guidance execute automatically.
- Do not treat a valid YAML file as enough; it must also match the current preview when appropriate.
- Do not hide risk upgrades, policy changes, or added/removed capability declarations behind a generic “ready” status.
- Do not omit audit evidence needed to reproduce human handoff decisions.
- Do not put credential values, tenant identifiers, provider endpoints, action payloads, raw execution traces, or admin exports in candidate status reports.

## Integration boundary

The safe integration boundary remains declarative and non-executing:

```text
capability policy preview/current declarations
  -> reviewed-baseline.yaml.template
  -> candidate status report
  -> human-created reviewed-baseline.yaml
  -> candidate status report
  -> reviewed baseline apply
```

Runtime execution, provider calls, hosted admin state, credentials, and raw logs remain outside this flow.
