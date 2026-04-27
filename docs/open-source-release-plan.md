# Open-Source Release Plan

## Goal

Release Portable AI Assets System as a public project **without exposing personal memory, sensitive machine state, or private runtime artifacts**.

---

## Release boundary

### Public repository should include
- bootstrap engine / CLI
- adapters framework
- example manifests
- example policies
- schema and validation rules
- documentation
- sample public-safe asset packs

### Public repository should exclude
- private memory/profile content
- real project summaries
- local session archives
- database files
- machine-local secrets
- personal runtime instruction history

### Recommended topology
- public repo = engine/framework
- private repo = canonical memory/assets
- local config = pointer from engine to active private asset root
- non-Git backup = runtime-heavy state and histories

---

## Recommended release steps

### Step 1 — Create a clean public repo skeleton
Include:
- `README.md`
- `CONTRIBUTING.md`
- `docs/architecture.md`
- `docs/non-goals.md`
- `docs/adapter-sdk.md`
- `docs/open-source-positioning.md`
- `docs/public-facing-thesis.md`
- `docs/public-roadmap.md`
- `docs/differentiators.md`
- `docs/security-model.md`
- `bootstrap/`
- `adapters/` templates
- `stack/` example manifests
- `tests/`

---

### Step 2 — Replace personal data with templates
Convert private content into:
- sample memory entries
- sample adapters
- sample manifests
- redacted reports

---

### Step 3 — Add explicit security model
Document:
- public/private/secret asset classes
- Git vs non-Git boundary
- redaction expectations
- review-before-apply rules

---

### Step 4 — Ship a minimal demo story
Example:
1. explain the public-facing thesis in one minute
2. validate schemas
3. inspect adapter inventory
4. preview connector actions without writes
5. generate redacted example outputs
6. run public-safety, release-readiness, and completed-work-review gates
7. package the public-safe demo story
8. build the public demo pack

A good demo matters more than breadth.

---

### Step 5 — Run release hardening gates
Before publishing, run:

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both
./bootstrap/setup/bootstrap-ai-assets.sh --release-readiness --both
./bootstrap/setup/bootstrap-ai-assets.sh --public-release-pack --both
./bootstrap/setup/bootstrap-ai-assets.sh --public-release-archive --both
./bootstrap/setup/bootstrap-ai-assets.sh --public-release-smoke-test --both
./bootstrap/setup/bootstrap-ai-assets.sh --github-publish-check --both
./bootstrap/setup/bootstrap-ai-assets.sh --public-repo-staging --both
./bootstrap/setup/bootstrap-ai-assets.sh --public-repo-staging-status --both
./bootstrap/setup/bootstrap-ai-assets.sh --github-publish-dry-run --both
./bootstrap/setup/bootstrap-ai-assets.sh --github-handoff-pack --both
./bootstrap/setup/bootstrap-ai-assets.sh --github-final-preflight --both
./bootstrap/setup/bootstrap-ai-assets.sh --release-provenance --both
./bootstrap/setup/bootstrap-ai-assets.sh --verify-release-provenance --both
./bootstrap/setup/bootstrap-ai-assets.sh --release-closure --both
./bootstrap/setup/bootstrap-ai-assets.sh --manual-release-reviewer-checklist --both
./bootstrap/setup/bootstrap-ai-assets.sh --public-docs-external-reader-review --both
./bootstrap/setup/bootstrap-ai-assets.sh --public-package-freshness-review --both
./bootstrap/setup/bootstrap-ai-assets.sh --release-candidate-closure-review --both
./bootstrap/setup/bootstrap-ai-assets.sh --release-reviewer-packet-index --both
./bootstrap/setup/bootstrap-ai-assets.sh --release-reviewer-decision-log --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-quickstart --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-plan --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-status --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-template --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-followup-index --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-followup-candidates --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-followup-candidate-status --both
./bootstrap/setup/bootstrap-ai-assets.sh --initial-completion-review --both
./bootstrap/setup/bootstrap-ai-assets.sh --human-action-closure-checklist --both
./bootstrap/setup/bootstrap-ai-assets.sh --manual-reviewer-execution-packet --both
./bootstrap/setup/bootstrap-ai-assets.sh --manual-reviewer-public-surface-freshness --both
./bootstrap/setup/bootstrap-ai-assets.sh --manual-reviewer-handoff-readiness --both
./bootstrap/setup/bootstrap-ai-assets.sh --manual-reviewer-handoff-packet-index --both
./bootstrap/setup/bootstrap-ai-assets.sh --manual-reviewer-handoff-freeze-check --both
./bootstrap/setup/bootstrap-ai-assets.sh --agent-owner-delegation-review --both
./bootstrap/setup/bootstrap-ai-assets.sh --agent-complete-external-actions-reserved --both
./bootstrap/setup/bootstrap-ai-assets.sh --agent-complete-failclosed-hardening-review --both
./bootstrap/setup/bootstrap-ai-assets.sh --agent-complete-regression-evidence-integrity --both
./bootstrap/setup/bootstrap-ai-assets.sh --agent-complete-syntax-invalid-evidence-failclosed-review --both
./bootstrap/setup/bootstrap-ai-assets.sh --agent-complete-phase102-rollup-evidence-failclosed-review --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reference-inventory --both
./bootstrap/setup/bootstrap-ai-assets.sh --external-reference-backlog --both
```

The public safety scan should have zero blockers and ideally zero warnings. The release readiness report aggregates required docs, schemas, adapter contracts, portable skills, public safety, and demo-pack availability.

`--public-release-pack` creates a redacted export under `dist/portable-ai-assets-public-<timestamp>/` with `MANIFEST.json`, `PACK-INDEX.md`, and `CHECKSUMS.sha256`. It intentionally excludes private memory, skills, raw reports/candidates/backups, runtime DB/logs, machine-local config, and non-Git backup state.

`--public-release-archive` creates a `.tar.gz` plus a `.sha256` checksum from the latest public release pack. `--public-release-smoke-test` extracts the archive and verifies required files, Python syntax, shell CLI public-safety mode, and forbidden-text scan results.

`--github-publish-check` creates/refreshes GitHub-facing materials (`LICENSE`, `SECURITY.md`, `CHANGELOG.md`, `RELEASE_NOTES-v0.1.md`, `docs/github-publishing.md`) and reports whether the repo is ready to publish. It does not create a GitHub repo, push commits, or publish a release.

`--public-repo-staging` creates `dist/github-staging/portable-ai-assets/`, a public-safe working tree intended to become the GitHub repo root after manual review. It initializes Git locally for convenience, writes `GITHUB-PUBLISH-CHECKLIST.md` and `STAGING-MANIFEST.json`, and still avoids commit, push, remote creation, or release publishing.

`--public-repo-staging-status` reports the staging tree's git status, branch, remote state, changed-file categories, and forbidden-text findings. `--github-publish-dry-run` emits suggested commit/repo/tag metadata and command drafts while executing none of them.

`--github-handoff-pack` creates `dist/github-handoff/portable-ai-assets-handoff-<timestamp>/` with `HANDOFF.md`, `HANDOFF.json`, the GitHub publish checklist, release notes, latest gate reports, archive/checksum pointers, and the non-executing manual command drafts. It is reviewer handoff material only; it does not commit, push, create a remote, create a repo, or publish a release.

`--github-final-preflight` aggregates the latest release/GitHub gates, rechecks the staging repo has no remote, confirms every command draft is non-executing, verifies the handoff bundle, checks archive/checksum files, and recomputes the archive SHA256. It is the final machine-generated check before human review and manual publication.

`--release-provenance` writes an unsigned public provenance manifest under `dist/provenance/` with the archive subject, recomputed SHA256, checksum file pointer, and tree digests for the release pack, staging tree, and handoff bundle. It is audit metadata for reviewers, not a cryptographic attestation yet.

`--verify-release-provenance` reloads the latest provenance, recomputes the archive SHA256 and current tree digests, compares them to the recorded values, and reports drift before anything is published. It remains report-only and does not prove external authenticity because the provenance is unsigned.

`--release-closure` aggregates the latest public safety, release readiness, demo pack, public release pack/archive/smoke, GitHub publish/staging/dry-run/handoff/final-preflight, unsigned provenance, provenance verification, and completed-work-review evidence into one report-only closure gate. Its ready state is `ready-for-manual-release-review`, not publish approval; it blocks on missing/failing evidence, configured remotes, command drafts that execute, or public-safety/provenance problems, and it still does not commit, push, create remotes, publish releases, call providers, or execute hooks/actions/code.

Phase 77 strengthens this closure evidence by classifying every GitHub dry-run command draft by manual publication risk and surfacing a publication command summary plus boundary notes. The command drafts remain copy/paste-only reviewer aids: no command is executed, no credential is validated, no provider/API is called, no repo/remote/tag/release is created, and no publication is approved automatically.

`--manual-release-reviewer-checklist` converts the latest release closure, GitHub final preflight, public safety, release readiness, publication boundary, command draft classification, and artifact checksum evidence into a human reviewer checklist. Its ready state is `ready-for-human-review`, not approval; it blocks on missing/failing evidence and remains report-only/local artifact generation only, with no publishing, no push, no remote/tag/repo/release creation, no credential validation, no provider/API call, and no command execution.

`--public-package-freshness-review` confirms the latest manual release reviewer checklist and Phase 77/78 release evidence are present in the local public release pack and GitHub staging tree, and that both surfaces document the reviewer checklist/freshness gates. Its ready state is `ready`; stale means rerun `--public-release-pack --both`, `--public-repo-staging --both`, and public safety before manual review. It remains report-only/local evidence only: no publication, no push, no remote/repo/tag/release creation, no credential validation, no provider/API call, and no command execution.

`--release-candidate-closure-review` aggregates the final local release-candidate evidence packet for human review after release closure, manual release reviewer checklist, public docs external-reader review, public package freshness review, public safety, release readiness, GitHub final preflight, and completed-work-review are ready/aligned. Its ready state is `ready-for-final-human-review`, not automatic publish approval; it blocks on stale/missing/failing evidence, configured remotes, executable command drafts, forbidden public findings, or boundary drift. It remains report-only/local evidence only: no publication, no commit, no push, no remote/repo/tag/release creation, no credential validation, no provider/API call, and no hook/action/command execution.

`--release-reviewer-packet-index` creates a local table of contents for the final human reviewer packet after the release-candidate closure evidence is ready. Its ready state is `ready`, meaning the packet is complete and navigable, not publication approval or an automated go/no-go decision. It remains report-only/local evidence only: no publication, no commit, no push, no remote/repo/tag/release creation, no credential validation, no provider/API call, no hook/action/command execution, no upload, and no runtime/admin/provider-state mutation.

`--release-reviewer-decision-log` creates a local report-only human reviewer decision-log template/status artifact after `--release-reviewer-packet-index`. Its status `needs-human-review` means the template and source evidence are ready for a human to record findings, open questions, public/private-boundary notes, publication-boundary notes, and a separate manual decision placeholder; it does not approve a release, make a go/no-go decision, publish, commit, push, create remotes/repos/tags/releases, validate credentials, call APIs, execute hooks/actions/commands, upload artifacts, or mutate runtime/admin/provider state.

`--external-reviewer-quickstart` creates a local report-only first-10-minutes path for an external human reviewer after `--release-reviewer-decision-log`. It checks that README, public thesis, redacted demo pack, reviewer packet index, and decision-log template are discoverable from one short path. Its ready state is navigability evidence only, not release approval or a go/no-go decision; it does not approve, publish, commit, push, create remotes/repos/tags/releases, validate credentials, call APIs, upload artifacts, execute hooks/actions/commands, or mutate runtime/admin/provider state.

`--external-reviewer-feedback-plan` creates a local report-only capture/import plan after `--external-reviewer-quickstart` and `--release-reviewer-decision-log`. Its ready state `ready-for-feedback-review` means the human reviewer notes can be converted into local follow-up/backlog drafts; it is not release approval, not a go/no-go decision, and it does not mutate issues or backlogs automatically. It does not approve, publish, commit, push, create remotes/repos/tags/releases, validate credentials, call APIs, upload artifacts, execute hooks/actions/commands, or mutate runtime/admin/provider state.

`--external-reviewer-feedback-status` creates a local report-only checker for a human-filled `bootstrap/reviewer-feedback/external-reviewer-feedback.md` file after `--external-reviewer-feedback-plan`. Its ready state `ready-for-follow-up-review` means required feedback fields are present and local follow-up items can be reviewed; it is not release approval, not a go/no-go decision, and it does not create or mutate issues/backlogs automatically. It does not approve, publish, commit, push, create remotes/repos/tags/releases, validate credentials, call APIs, upload artifacts, execute hooks/actions/commands, or mutate runtime/admin/provider state.

`--external-reviewer-feedback-template` writes only a human-fillable `bootstrap/reviewer-feedback/external-reviewer-feedback.md.template` file for the Phase 86 status gate. Its ready state `template-ready` means the template exists, not that human feedback has been supplied; it is template-only/report-only, does not create the final `external-reviewer-feedback.md`, does not satisfy the status gate, and does not approve, publish, commit, push, create remotes/repos/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues/backlogs, execute hooks/actions/commands, or mutate runtime/admin/provider state.

`--external-reviewer-feedback-followup-index` creates a local report-only index for human follow-up review after the feedback plan/status/template gates. It points to the human-fillable template, latest feedback status report, feedback plan report, template report, and the optional filled feedback file when present. Its ready state means the index is navigable, not that human feedback exists or a release is approved; it does not create issues, mutate backlogs, approve, publish, commit, push, create remotes/repos/tags/releases, validate credentials, call APIs, upload artifacts, execute hooks/actions/commands, or mutate runtime/admin/provider state.

`--external-reviewer-feedback-followup-candidates` creates only local candidate files under `bootstrap/candidates/` from a human-filled `external-reviewer-feedback.md` after the feedback status gate is `ready-for-follow-up-review`. It is local-only/template-only/report-only and does not create remote issues, mutate backlogs, record approval, publish, commit, push, create remotes/repos/tags/releases, validate credentials, call APIs, upload artifacts, execute hooks/actions/commands, or mutate runtime/admin/provider state. If feedback status is still `needs-human-feedback`, it remains blocked and writes no candidate files.

`--external-reviewer-feedback-followup-candidate-status` scans the local candidate bundle from `--external-reviewer-feedback-followup-candidates`, checks candidate file structure and safety invariants, and reports whether the bundle is ready for manual follow-up handling. It is local-only/report-only and does not create remote issues, mutate issues/backlogs, record approval, publish, commit, push, create remotes/repos/tags/releases, validate credentials, call APIs, upload artifacts, execute hooks/actions/commands, or mutate runtime/admin/provider state. If the candidate bundle is absent because human feedback is still missing, it remains blocked instead of creating or fabricating candidates.

`--initial-completion-review` summarizes machine readiness, human feedback, follow-up candidate status, and manual publication boundaries after the public release gates and external reviewer feedback gates. It is local-only/report-only: it can report machine-side readiness while human feedback is still pending, but it does not approve, publish, push, create repos/remotes/tags/releases, validate credential material, call APIs/providers, upload artifacts, mutate issues/backlogs, execute hooks/actions/commands, record go/no-go, or fabricate human feedback. Manual publication and any final release approval remain outside automation.

`--human-action-closure-checklist` turns the initial completion state into a local-only/report-only checklist for the remaining human feedback, follow-up, and manual publication actions. It tells a human to copy/fill `bootstrap/reviewer-feedback/external-reviewer-feedback.md`, rerun feedback/candidate gates, manually review candidates, and make any external sharing/publication decision outside automation; it does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs/providers, upload artifacts, mutate issues/backlogs, execute hooks/actions/commands, record go/no-go, or fabricate human feedback. The boundary explicitly excludes approving, publishing, pushing, credentials validation, APIs/provider calls, and executing commands.

`--manual-reviewer-execution-packet` turns the human-action closure checklist into a local-only/report-only one-page human runbook index. It links the latest reviewer packet, external reviewer quickstart, feedback template, follow-up index, staging status, and closure checklist, and lists the manual feedback/follow-up/manual publication sequence without executing it. Its ready state `ready-for-human-runbook` is not approval, not publication, and not a go/no-go decision; it does not create final feedback, create issues/backlogs, approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs/providers, upload artifacts, mutate remotes, or execute commands. The packet is only operator/reviewer guidance for a human to run outside automation.

`--manual-reviewer-public-surface-freshness` is Phase 94 is a local-only/report-only freshness and coverage check for the human runbook across public pack and GitHub staging surfaces; it does not approve, publish, push, execute, call APIs/providers, validate credentials, or mutate issues/backlogs. It verifies that the Phase 93 `latest-manual-reviewer-execution-packet` JSON/Markdown and the Phase 94 command wiring are visible in local public pack, GitHub staging, docs, and shell wrapper surfaces. A ready result means surfaces are fresh enough for a human reviewer to inspect; it is not release approval, not a go/no-go decision, and not completion of human feedback.

`--manual-reviewer-handoff-readiness` is Phase 95 is a local-only/report-only handoff readiness digest for a human operator; it does not approve, share, invite, publish, push, execute, call APIs/providers, validate credentials, or mutate issues/backlogs. It summarizes the ready public reviewer surfaces, manual reviewer execution packet, public surface freshness report, feedback template, public release pack, and GitHub staging tree so a human can decide whether and how to perform any real handoff outside automation. A ready-for-human-handoff result is not release approval, not a go/no-go decision, not an invitation, and not completion of human feedback.

`--manual-reviewer-handoff-packet-index` is Phase 96 is a local-only/report-only human handoff packet index/status that cross-links the handoff readiness digest, public pack, staging tree, reviewer runbook, feedback template, exact human-only next actions, and drift checks without sharing, inviting, approving, publishing, executing, calling APIs/providers, validating credentials, or mutating issues/backlogs. Its ready-for-human-handoff-packet result means the local packet index is navigable for a human operator/reviewer; it is not release approval, not a go/no-go decision, not an invitation, not publication, and not completion of human feedback.

`--manual-reviewer-handoff-freeze-check` is Phase 97 is a local-only/report-only handoff freeze check that verifies packet freshness, packet index readiness, indexed local artifact presence, and human-only next actions without sharing, inviting, approving, publishing, executing, calling APIs/providers, validating credentials, creating feedback, or mutating issues/backlogs. Its frozen-for-human-handoff result means the local packet is stable and navigable for a human handoff; it is not release approval, not a go/no-go decision, not an invitation, not publication, and not completion of human feedback.

`--agent-owner-delegation-review` is Phase 98 is a local-only/report-only agent-side owner delegation review that records engineering/code review, testing, safety checks, and product-material self-review are delegated to the agent without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs. It means the user need not review code for machine-side progress; real external sharing, reviewer invitations, publication, external feedback authorship, and final go/no-go remain explicit owner-side external decisions.

`--agent-complete-external-actions-reserved` is Phase 99 is a local-only/report-only agent-complete external-actions-reserved final rollup that records machine-side and agent-side work is complete while real sharing, reviewer invitation, publication, external feedback authorship, and final go/no-go remain explicit external owner decisions without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs. Its ready state means agent-side work can continue without user code review, but no external action has been authorized or performed.

`--agent-complete-failclosed-hardening-review` is Phase 100 is a local-only/report-only fail-closed hardening review for the agent-complete rollup, confirming malformed upstream numeric fields and blocked source evidence cannot claim completion without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs.

`--agent-complete-regression-evidence-integrity` is Phase 101 is a local-only/report-only regression evidence integrity audit confirming Phase 100 fail-closed regression coverage is backed by actual test function definitions rather than comments or string mentions without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs.

`--agent-complete-syntax-invalid-evidence-failclosed-review` is Phase 102 is a local-only/report-only syntax-invalid evidence fail-closed review confirming syntax-invalid regression evidence cannot satisfy definition-backed coverage or claim agent completion without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs.

`--agent-complete-phase102-rollup-evidence-failclosed-review` is Phase 103: a local-only/report-only Phase102 rollup evidence fail-closed review confirming downstream completed-work and agent-complete rollups require valid Phase102 report evidence before continuing without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs.

`--external-reference-inventory`

`--external-reference-backlog` tracks candidate external projects and idea families to review before building new memory/backend capabilities. It reports reviewed baselines, high-priority candidates, expected reference doc outputs, and missing review artifacts. Phase 73 marks the agent workflow/skill registry lane reviewed: CrewAI, AutoGen, Semantic Kernel, Microsoft Agent Framework Skills, Anthropic Agent Skills, and LangGraph inform manifest-first packaging, progressive disclosure, capability declarations, and registry discovery while preserving the no-runtime/no-execution boundary.

Phase 74 marks the reproducible environment portability lane reviewed: Nix flakes, Home Manager, Dev Containers, chezmoi, and yadm inform manifest/lock provenance, schema-first environment descriptors, typed validation, collision preview, context selectors, layering, and action-risk boundaries before any environment projection. The release scope remains non-executing: no package install/build, container start, dotfile apply, lifecycle command, bootstrap/hook execution, secret lookup, admin mutation, commit, push, or publication.

Phase 75 marks the supply-chain provenance and release evidence lane reviewed: Sigstore, SLSA, in-toto, CycloneDX, and SPDX inform subject/materials/builder/products vocabulary, attestation-shaped local evidence, SBOM-style inventory discipline, release maturity labeling, and manual reviewer handoff. The release scope remains unsigned and local unless a future explicit signing process is designed: no signing, certificate creation, transparency-log upload, external attestation generation, SBOM publication, provider/API call, credential validation, commit, push, or release publication.

Phase 76 marks the declarative desired-state lane reviewed: Kubernetes custom resources/operators, `kubectl diff`, Server-Side Apply, OpenGitOps, Argo CD, and Flux inform desired vs observed state, public-safe diffs, status/conditions, drift detection, reconcile preview, destructive-action gating, and narrow reviewed apply boundaries. The release scope remains an asset/report layer: no Kubernetes/Argo/Flux controller, no cluster/API access, no sync/prune/force/delete automation, no hook/action execution, no provider/API call, no credential validation, no commit, push, or publication.

`--team-pack-preview` checks public-safe team asset pack manifests, role profiles, playbooks, policies, shared adapter sources, and layering metadata. It is report-only and does not apply shared team content into private assets or live runtime files.

`--project-pack-preview` checks public-safe project pack manifests, project-scoped instructions, knowledge-source references, action metadata, adapter projection files, and declared capability risk classes. It is report-only and does not upload knowledge, call providers/actions, authenticate, execute hooks/code, or write runtime state.

`--capability-policy-preview` compares current project/team pack capabilities against a reviewed capability baseline and reports added, removed, changed, risk-upgraded, and risk-downgraded capabilities. It is report-only and does not execute actions, call providers, authenticate, update baselines, or mutate live runtime/admin state.

`--capability-policy-candidate-generation` refreshes `bootstrap/candidates/capability-policy/reviewed-baseline.yaml.template` from current declarative capability metadata and reports the same delta/risk/policy summary used by preview. It remains report-only: it does not create `reviewed-baseline.yaml`, does not call baseline apply, does not execute capabilities, does not call providers, does not authenticate, and does not mutate runtime/admin/provider state.

`--capability-policy-candidate-status` reports whether the generated template and optional human-created `reviewed-baseline.yaml` are valid, synchronized, and ready for reviewed apply. It is report-only: it does not write the template, does not create or modify `reviewed-baseline.yaml`, does not call baseline apply, does not execute capabilities, does not call providers, does not authenticate, and does not mutate runtime/admin/provider state.

`--capability-policy-baseline-apply` applies only a human-created reviewed capability baseline file, backing up the previous baseline first. It does not execute capabilities, call providers, authenticate, write runtime adapters, or mutate hosted/admin settings.

`--completed-work-review` is a report-only post-phase review that checks roadmap alignment, latest release readiness, public safety, external learning/backlog coverage, and capability governance boundaries before the next candidate is implemented. It reads docs and latest report JSON only, emits its own report, and does not execute hooks/actions/code, call providers, authenticate, or mutate runtime/admin/provider state.

---

## Suggested first public milestone

### v0.1 — Portable AI Assets Prototype
Must include:
- inspect
- plan
- diff
- merge-candidates
- review-apply
- adapter registry contracts
- connector inventory / preview
- sample adapters
- sample redacted asset pack

This is enough to prove the thesis without overcommitting to full ecosystem coverage.

---

## What not to promise publicly yet

Do not over-promise:
- universal lossless migration
- full compatibility with every agent/runtime
- stable standardization across all ecosystems
- automatic semantic merge for every target

Better public framing:
- canonical ownership first
- adapter-based portability
- conservative migration
- human-review-aware reconciliation
