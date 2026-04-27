# Reference: Declarative desired-state reconciliation

## Scope

Phase 76 reviews mature declarative desired-state systems as external references for Portable AI Assets governance:

- Kubernetes custom resources, CRDs, operators, `kubectl diff`, and Server-Side Apply
- OpenGitOps principles
- Argo CD declarative setup, diffing, health/sync vocabulary, and sync safety options
- Flux GitOps Toolkit sources, artifacts, Kustomizations, reconciliation, health/status, prune, deletion policy, and suspend/resume controls

This review is conceptual and public-safe. It does not run Kubernetes, Argo CD, Flux, `kubectl`, controllers, operators, hooks, sync, prune, or apply commands.

## Why this matters for Portable AI Assets

Portable AI Assets is not an agent runtime, memory backend, workflow builder, Kubernetes controller, or GitOps deployment engine. But the same problem appears at the AI work-environment layer:

- a user has a desired AI workspace state: memories, skills, instructions, adapters, project/team packs, policies, release evidence, and public-safe docs;
- actual local state can drift across machines, clients, agent runtimes, private asset roots, and generated projection files;
- safe portability requires explainable diffs and reviewable plans before anything writes to files or runtime surfaces.

Desired-state systems provide mature vocabulary for making this safer without turning Portable AI Assets into an executor.

## Reviewed systems and useful patterns

### Kubernetes custom resources and operators

Kubernetes custom resources make domain-specific desired state explicit through API objects, and operators/controllers watch that desired state, compare it to current cluster state, and reconcile toward it.

Patterns to absorb:

- manifest-first desired state rather than imperative one-off scripts;
- status/conditions vocabulary to explain observed state and health;
- reconciliation as a loop concept: desired, observed, diff, action plan, status;
- custom resources as typed extension points.

Boundary:

- Portable AI Assets should not become a Kubernetes operator or cluster controller;
- do not access clusters, create CRDs, start controllers, or mutate cluster resources;
- absorb the vocabulary for local reports and reviewed asset governance only.

### `kubectl diff` and Server-Side Apply

`kubectl diff` previews changes between manifests and live objects. Server-Side Apply tracks field ownership/managed fields and detects conflicts between managers.

Patterns to absorb:

- diff-first review before apply;
- field ownership / manager vocabulary for explaining who owns or last changed an asset projection;
- conflict detection before overwriting another owner’s fields;
- server-side apply’s conflict language as inspiration for future projection collision checks.

Boundary:

- no `kubectl apply`, no dry-run against a live API server, no cluster API calls;
- future local asset apply must remain narrow, reviewed, backup-aware, and file-scoped, not a general sync engine.

### OpenGitOps

OpenGitOps defines GitOps through declarative desired state, versioned and immutable state, automatic pull, and continuous reconciliation.

Patterns to absorb:

- desired state should be declarative and versionable;
- reconciliation should be transparent and repeatable;
- history and review matter as much as the final state.

Boundary:

- Portable AI Assets should not automatically pull, sync, or reconcile private assets from remotes;
- commit, push, remote setup, publication, and release remain explicit human actions.

### Argo CD

Argo CD is declarative GitOps continuous delivery for Kubernetes. Its concepts around applications, sync status, health status, diffing, ignore differences, selective sync, prune, and deletion confirmation provide useful governance language.

Patterns to absorb:

- separate sync status from health/status: “matches desired state” is not the same as “safe/healthy”;
- explain out-of-sync reasons and ignored differences;
- make destructive actions such as prune/delete require explicit controls;
- support selective, reviewed application of a subset rather than broad automatic apply.

Boundary:

- do not run Argo CD, create Applications, sync apps, prune resources, call Git webhooks, or manage cluster credentials;
- Portable AI Assets can use similar terms in reports without becoming CD tooling.

### Flux

Flux models sources, generated artifacts, Kustomizations, reconciliation intervals, dependencies, health checks, inventory, prune, deletion policy, suspend/resume, and status conditions.

Patterns to absorb:

- source artifact vs rendered/observed state separation;
- dependency and readiness vocabulary;
- suspend/resume as a safety switch for reconciliation;
- inventory/status/history as review evidence;
- prune/delete/force/decryption/remote-cluster controls as high-risk surfaces requiring explicit review.

Boundary:

- do not run Flux controllers, trigger reconcile, access clusters, decrypt secrets, or apply Kustomizations;
- retain only report-only ideas for local asset drift and candidate projection planning.

## What Portable AI Assets should adopt

1. **Desired-state manifest vocabulary**
   - Define what the user wants the AI work environment to contain.
   - Include asset classes, target scopes, expected projections, capability policy posture, review status, and provenance references.

2. **Observed-state reports**
   - Generate current state from local files/docs/reports without starting runtimes or calling providers.
   - Report missing files, extra files, stale projections, policy drift, release evidence drift, and public-safety drift.

3. **Diff-first governance**
   - Show added/removed/changed assets before writes.
   - Label destructive or high-risk operations: delete, prune, replace, force, credential binding, network/API, hook/action execution, admin/provider control, commit/push/publish.

4. **Reconcile preview, not automatic reconcile**
   - Produce a human-readable plan describing what would need to change.
   - The default output remains report-only.

5. **Reviewed apply gates**
   - If future apply behavior is needed, it must read from a reviewed candidate file, write only narrow local targets, create backup/evidence, and refuse runtime/provider/admin mutation.
   - Broad sync, prune, force, hook execution, and remote publication remain out of scope.

6. **Status and condition vocabulary**
   - Use clear states such as `ready`, `needs-review`, `blocked`, `empty`, `drift-detected`, `review-required`, and `ready-for-manual-release-review`.
   - Separate alignment/diff status from safety/release health.

7. **Drift detection**
   - Detect divergence between canonical private assets, public docs, generated examples, release evidence, and projected runtime instruction surfaces.
   - Drift reports should be public-safe and redact private paths, credentials, tenant IDs, workspace IDs, and provider details.

## What Portable AI Assets should avoid

- becoming a Kubernetes controller, operator, GitOps reconciler, CD system, package manager, workflow runtime, or deployment engine;
- automatic apply/sync/prune/force/delete behavior;
- starting controllers, MCP servers, hooks, actions, containers, or background reconciliation loops as part of reports;
- calling cluster APIs, provider APIs, webhooks, credential validators, registries, or remote Git services;
- storing raw runtime state, secrets, cluster credentials, provider credentials, conversations, traces, caches, embeddings, generated execution logs, or private admin exports in public docs;
- claiming external attestation, signing, SLSA level, or GitOps compliance from local unsigned reports.

## Implications for v0.1 governance

Phase 76 strengthens v0.1 by making future “sync” language precise:

- `preview` means compute and explain drift/diff only;
- `reconcile preview` means propose a plan, not execute it;
- `reviewed apply` means a narrow, file-scoped, human-reviewed write path with backups and evidence;
- `sync`, `prune`, `force`, `delete`, `publish`, and `remote reconcile` are not v0.1 capabilities unless separately designed and explicitly reviewed.

This keeps the project aligned with its core promise: preserve a portable AI work environment across tools, models, clients, and machines without turning the asset layer into the runtime.

## Safe integration boundary

For now, Portable AI Assets should only add:

- reference docs and public positioning language;
- report-only desired/current/diff vocabulary;
- future backlog items for local desired-state manifests, drift reports, and reconcile previews;
- reviewed apply constraints modeled after existing narrow baseline apply gates.

It should not add controllers, background loops, external network calls, provider authentication, cluster access, runtime mutation, automatic Git operations, or release publication.

## Source URLs reviewed

- https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
- https://kubernetes.io/docs/concepts/extend-kubernetes/operator/
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_diff/
- https://kubernetes.io/docs/reference/using-api/server-side-apply/
- https://opengitops.dev/
- https://argo-cd.readthedocs.io/en/stable/core_concepts/
- https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/
- https://argo-cd.readthedocs.io/en/stable/user-guide/diffing/
- https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/
- https://fluxcd.io/flux/concepts/
- https://fluxcd.io/flux/components/kustomize/kustomizations/
