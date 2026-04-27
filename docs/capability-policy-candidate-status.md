# Capability Policy Candidate Status

Capability policy candidate status is a report-only review gate between candidate template generation and reviewed baseline apply.

Run:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-candidate-status --both
```

## Input

The command reads only declarative files:

- `bootstrap/candidates/capability-policy/reviewed-baseline.yaml.template`
- `bootstrap/candidates/capability-policy/reviewed-baseline.yaml`
- `sample-assets/capability-policy/baseline.yaml` or `capability-policy/baseline.yaml`
- current public-safe project/team pack capability declarations

## Output

The command emits:

```text
bootstrap/reports/latest-capability-policy-candidate-status.json
bootstrap/reports/latest-capability-policy-candidate-status.md
```

It does **not** create or update either candidate file. In particular, it never creates:

```text
bootstrap/candidates/capability-policy/reviewed-baseline.yaml
```

## Report contents

The report includes:

- `executes_anything: false`;
- whether the template exists;
- whether a human-created reviewed baseline exists;
- whether the reviewed baseline validates;
- whether the reviewed baseline is synchronized with the current preview/template;
- `apply_readiness` and `ready_for_apply`;
- added, removed, changed, risk-upgraded, and risk-downgraded capability counts;
- capability risk class counts and policy outcome counts;
- `reviewer_guidance` with a human-review checklist, next action, template/reviewed-baseline paths, and non-executing command drafts;
- `review_handoff_audit` with read-only preflight evidence, file existence, SHA256 hashes for candidate/reviewed/current baseline inputs when present, and handoff steps proving no auto-copy or auto-apply occurred;
- write counters proving `templates_written == 0` and `reviewed_baselines_written == 0`.

## Reviewer guidance

The JSON and Markdown reports include a `reviewer_guidance` block. It is documentation only:

- `next_action` names the expected human step, such as `human-review-template`, `fix-reviewed-baseline`, `sync-reviewed-baseline-with-current-preview`, or `run-reviewed-apply-if-intended`;
- the checklist asks reviewers to compare added/removed/changed declarations, inspect risk upgrades and policy outcome changes, and confirm the files contain no credential values, tokens, webhook URLs, or provider connection strings;
- command drafts show common manual commands, but every draft has `executes: false` and the status command does not run them.

## Review handoff audit

The JSON and Markdown reports also include `review_handoff_audit`. It records only local declarative evidence:

- candidate template, reviewed baseline, current baseline, and review-instructions paths;
- `exists` flags and SHA256 hashes when files are present; missing reviewed baselines produce `null` hashes rather than creating files;
- a preflight checklist such as `human-reviewed-baseline-present` and `candidate-status-report-only`;
- `writes_anything: false`, `writes: 0`, and `executes_anything: false`;
- handoff steps reminding reviewers to inspect the candidate status report, copy the template only after human acceptance, rerun status, and avoid auto-apply.

This audit is meant to make human review reproducible without expanding the execution surface.

## Readiness states

- Missing reviewed baseline: `needs-human-review`, not ready for apply.
- Invalid reviewed baseline: blocked, not ready for apply.
- Valid but out-of-sync reviewed baseline: needs sync, not ready for apply.
- Valid and synchronized reviewed baseline: ready for `--capability-policy-baseline-apply`.

## Safety boundary

This mode must not:

- write the reviewed baseline template;
- create `reviewed-baseline.yaml`;
- run `--capability-policy-baseline-apply`;
- execute actions, hooks, scripts, MCP tools, workflow nodes, or custom agents;
- call providers, APIs, webhooks, hosted actions, or admin endpoints;
- authenticate or validate credentials;
- mutate live runtimes, hosted workspaces, provider settings, Git remotes, credential bindings, runtime adapter files, or provider admin data.

## Review workflow

1. Run `--capability-policy-preview --both` and inspect capability deltas.
2. Run `--capability-policy-candidate-generation --both` to refresh `reviewed-baseline.yaml.template`.
3. Run `--capability-policy-candidate-status --both` to confirm whether human review is still needed.
4. Review the template manually and create `reviewed-baseline.yaml` only after accepting the capability policy changes.
5. Run `--capability-policy-candidate-status --both` again to verify validation and sync status.
6. Run `--capability-policy-baseline-apply --both` only when the status report says the reviewed baseline is ready for apply.
7. Inspect the diff and commit baseline changes explicitly if desired.
