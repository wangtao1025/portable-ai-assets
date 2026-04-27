# Hosted Agent / Team Workspace Governance Reference Review

Phase: 57
Status: reviewed
Reference family: ChatGPT Enterprise / OpenAI Trust, Claude Enterprise/Admin API, Microsoft 365 Copilot governance, GitHub Copilot organization controls, and similar hosted AI workspace administration surfaces.

This review studies hosted AI workspaces as governance products: org/workspace membership, identity, permissions, audit, retention, data controls, policy toggles, and admin APIs. The goal is not to copy a hosted SaaS control plane. The goal is to define which governance metadata belongs in Portable AI Assets before future team-pack or project-pack apply behavior writes into shared assistant environments.

## Why this matters

Portable AI Assets already has personal, project, adapter, connector, team-pack, and hosted-project reference layers. The next risk is shared deployment: a team/project pack may eventually project instructions, skills, tools, workflows, or memory candidates into multiple runtime surfaces. Hosted AI products show that once assets become shared, the important questions are no longer only “what file should be written?” but also:

- who can read, edit, export, or apply it?
- which workspace / tenant / org owns it?
- what audit trail exists for changes?
- what retention or deletion policy applies?
- what identity provider / SSO / SCIM / role model controls membership?
- which tool, connector, MCP, plugin, or action capabilities are allowed?
- which data may be used for training, analytics, logging, search, or retrieval?
- what must remain private, redacted, or runtime-only?

## Reference signals observed

### Claude / Anthropic administration surfaces

Anthropic’s current public documentation exposes an Administration area for Admin API, Workspaces, Data residency and API data retention, Monitoring, Claude Code Analytics API, and Usage and Cost APIs. Its API reference copy describes management of organization settings, workspaces, and federation resources, with workspace-admin style concepts.

Useful signal: workspace governance is not just project instructions. It includes org/workspace topology, billing/usage, data-retention posture, monitoring/analytics, and federated identity resources.

### OpenAI enterprise / trust surfaces

OpenAI’s public Trust Portal emphasizes audited controls and compliance posture such as SOC 2 Type 2 and ISO certifications. OpenAI business/enterprise materials generally separate enterprise privacy/security posture from consumer use, with controls around organizational data, retention, and admin-managed deployment.

Useful signal: public release materials should not merely say “secure”; they should prove that governance artifacts are explicit, inspectable, and separated from private data. Portable AI Assets should produce local reports that answer what would be shared/applied, not rely on provider trust pages.

### Microsoft 365 Copilot governance

Microsoft 365 Copilot documentation frames governance around tenant isolation, Entra authorization and role-based access control, Purview retention policies, Content Search/eDiscovery, sensitivity labels, usage rights, data residency, and administrative controls over feedback and connected experiences. It also states that Copilot can access content the current user is authorized to access, and that stored interactions can be covered by compliance tooling.

Useful signal: AI assistant governance inherits enterprise information governance. Permissions, sensitivity labels, retention, eDiscovery, and user authorization are not optional metadata once assets are team-shared.

### GitHub Copilot organization / enterprise controls

GitHub Copilot organization docs expose an administration surface around plan/feature management, organization access, enterprise features, code referencing, chat/agents, cloud agent management, custom agents, hooks, MCP/cloud-agent access, and risk mitigations.

Useful signal: coding-agent governance must track not only instruction files but also agent modes, cloud execution, hooks, custom agents, MCP access, code-reference controls, and organization/enterprise policy scope.

## What these systems do well

1. **Tenant and workspace boundaries**
   - distinguish organization, workspace, project, team, and user scopes
   - centralize membership and permission assignment
   - support enterprise identity/federation patterns such as SSO/SCIM/RBAC

2. **Permission vocabulary**
   - separate read/use, edit/manage, admin, billing, audit, and owner capabilities
   - constrain which users can modify shared instructions, knowledge, tools, and memberships

3. **Policy controls**
   - expose toggles or rules for data retention, data residency, training use, sharing, external connectors, feedback, analytics, and tool access
   - map governance controls to org/workspace scope rather than burying them in per-user preferences

4. **Audit and monitoring**
   - track admin events, usage, cost, analytics, and sometimes agent/code execution telemetry
   - make shared environment changes accountable

5. **Data governance integration**
   - connect AI interactions to retention, eDiscovery, sensitivity labels, DLP, access controls, and compliance reports

6. **Capability governance**
   - treat custom agents, actions, MCP servers, hooks, connectors, cloud agents, and code execution as policy-controlled capabilities rather than ordinary text prompts

## What Portable AI Assets should adopt

### 1. Governance manifest vocabulary

Future team/project packs should include a declarative governance section, for example:

```yaml
governance:
  scope: team | project | org | role | individual
  visibility: private | team | org | public-safe-example
  permissions:
    readers: [role:engineer]
    editors: [role:maintainer]
    appliers: [role:asset-admin]
    auditors: [role:security]
  retention:
    canonical_assets: review-before-delete
    runtime_exports: local-policy
    reports: local-policy
  audit:
    required_for_apply: true
    include_diff_summary: true
  data_controls:
    allow_training_use: false
    allow_public_release: false
    redact_identifiers: true
  capability_policy:
    mcp_servers: review-required
    actions: review-required
    custom_code: manual-only
    cloud_agents: review-required
```

This should remain metadata-first. It should not become a hosted policy engine in v1.

### 2. Apply actor and approval metadata

Any future reviewed apply gate for shared assets should record:

- actor identity label or local operator label, redacted in public reports
- approval source: manual, reviewed bundle, ticket reference, policy exception
- target scope: individual, role, project, team, org
- target runtime and adapter
- diff summary
- risk class
- timestamp
- rollback/backup pointer

Public reports must redact real users, emails, org names, workspace IDs, tenant IDs, and ticket URLs unless they are fake examples.

### 3. Permission-aware preview gates

Preview reports should answer:

- which roles can read the proposed asset?
- which roles can edit it?
- who may apply it to runtime targets?
- what capability risks are included?
- whether the target is individual-private, team-private, org-shared, or public-safe
- whether the asset references secrets, private paths, webhook URLs, provider keys, or runtime identifiers

This is more useful than a simple “files changed” preview when multiple people share a workspace.

### 4. Capability policy classes

Adopt a stable risk vocabulary for governed capabilities:

- `text-only` — instructions, docs, prompts, playbooks
- `read-only-data` — search/list/context reads
- `write-memory` — save/update/delete/merge memory
- `external-network` — HTTP/webhook/action/API calls
- `code-execution` — local/cloud code, hooks, shell, notebook, agent tasks
- `credential-binding` — provider keys, OAuth, tokens, connection strings
- `admin-control` — membership, policy, retention, billing, audit, org settings

A future apply gate should require stronger review for each step up this ladder.

### 5. Retention and deletion semantics

Portable AI Assets should distinguish:

- canonical asset history
- generated reports
- candidate bundles
- backups
- runtime exports
- provider-hosted chat/history/memory
- public release packs

Retention policy should say which artifacts are durable source, which are local evidence, which are rebuildable, and which should be deleted/redacted before public release.

### 6. Data residency / tenant labels as metadata

For enterprise teams, location and tenant boundaries matter. Portable AI Assets should not enforce data residency, but manifests and reports can carry labels such as:

- `tenant_scope: local | personal | team | org | external-provider`
- `residency_policy: local-only | provider-managed | org-managed | unknown`
- `data_classification: public | internal | confidential | restricted | secret-redacted`

These labels help prevent accidental mixing of personal, team, and public release surfaces.

## What Portable AI Assets should explicitly avoid

Do not turn Portable AI Assets into:

- an identity provider, SSO, SCIM, or RBAC server
- an enterprise admin console
- a compliance product
- a DLP/eDiscovery platform
- a billing/usage analytics system
- a hosted AI workspace SaaS
- an audit-log database for all runtime activity
- a retention enforcement engine
- a policy engine that silently mutates provider settings
- a connector/action marketplace
- a cloud-agent execution controller
- a system that stores credentials, OAuth tokens, provider keys, webhook URLs, or connection strings in canonical Git assets

## Safe integration boundary

### Inventory first

A future hosted-workspace adapter may inventory:

- configured org/workspace/project labels
- role names and permission classes
- policy names and enabled/disabled state
- retention labels
- capability categories
- adapter/connector/action names
- audit event counts and redacted summaries

It must not collect raw chat histories, prompt logs, private documents, provider analytics exports, user emails, tenant IDs, access tokens, secret values, or webhook URLs into public canonical assets.

### Preview before apply

Before applying a team/project pack to a shared runtime, generate a preview that includes:

- target runtime and scope
- affected files/manifests/adapters
- permission deltas
- capability risk deltas
- data-control flags
- retention/report implications
- redaction status
- required human approvals

### Reviewed apply only

Shared apply should require explicit reviewed input, not automatic sync. Mutating operations that affect team/org workspaces should be treated as high-risk even when the underlying file write is technically simple.

## Canonical mapping

| Hosted governance concept | Portable AI Assets mapping |
|---|---|
| Organization / tenant | private metadata label, redacted in public reports |
| Workspace / project | project-pack or team-pack scope |
| User / group / role | role labels, not raw identities in public assets |
| Can use / can edit / admin | permission vocabulary for preview/apply reports |
| SSO / SCIM / federation | external identity boundary, not implemented in Portable AI Assets |
| Audit logs | local apply provenance and redacted report summaries |
| Retention policy | manifest/report retention labels and deletion guidance |
| Data residency | metadata label only; provider/org enforcement remains external |
| DLP / sensitivity labels | optional data-classification metadata |
| Usage/cost analytics | runtime/private report source; not canonical memory |
| Cloud agents / hooks / custom agents | governed capability class requiring review |
| MCP/actions/connectors | capability policy entries plus credential-binding separation |

## Raw/runtime data that must remain outside Git

Keep the following out of public canonical assets and Git-tracked examples:

- user emails and personal identifiers
- org IDs, tenant IDs, workspace IDs, project IDs
- SSO/SCIM/federation configuration values
- API keys, OAuth tokens, provider keys, session cookies
- webhook URLs, connection strings, secret names with values
- raw audit logs
- raw usage/cost exports
- raw chat histories or prompt logs
- uploaded files and document contents unless explicitly public-safe examples
- retrieval chunks, embeddings, vector indexes
- security incidents, DLP findings, or compliance exports
- provider admin screenshots or exports containing real identities

Use `[REDACTED]` or fake example values in public docs.

## Report/check implications

Near-term reusable gates to add later:

1. `--governance-pack-preview --both`
   - inventory governance sections in team/project packs
   - report scope, visibility, permission roles, retention, data controls, capability policy, and missing review metadata

2. `--shared-apply-readiness --both`
   - block shared apply when governance metadata is absent, redaction fails, capability risk is too high, or approval evidence is missing

3. `--apply-provenance-inventory --both`
   - summarize previous reviewed apply events with redacted actor/scope/risk/diff metadata

4. `--capability-risk-inventory --both`
   - list MCP/actions/hooks/custom agents/cloud agents/code execution bindings and classify them by risk

These should remain report-only until the preview/review/apply design is mature.

## Decision for Portable AI Assets

Adopt governance vocabulary and preview requirements now; defer implementation of a full policy engine.

Phase 57 makes `docs/reference-hosted-agent-workspace-governance.md` a reviewed reference so future shared/team/project-pack apply behavior has explicit governance constraints before it can mutate shared surfaces.

## Sources checked

The review used publicly reachable documentation surfaces and conservative interpretation:

- Anthropic Claude API Docs Administration area: Admin API overview, Workspaces, Data residency and API data retention, Monitoring, Claude Code Analytics API, Usage and Cost API.
- Anthropic API reference snippets describing management of organization settings, workspaces, federation resources, and workspace-admin concepts.
- OpenAI Trust Portal public compliance summary mentioning SOC 2 Type 2 and ISO certifications.
- Microsoft Learn: Data, Privacy, and Security for Microsoft 365 Copilot, including tenant isolation, Entra authorization/RBAC, Purview retention, Content Search/eDiscovery, sensitivity labels, feedback controls, and permission-scoped data access.
- GitHub Docs: managing GitHub Copilot in an organization, including organization administration, enterprise features, code referencing, chat/agents, cloud agent management, custom agents, hooks, access management, MCP/cloud-agent access, and risk mitigations.

Some provider help-center pages are access-controlled or dynamic. When a source was not directly readable, this review avoids relying on unverifiable implementation details and only adopts broadly visible governance patterns.
