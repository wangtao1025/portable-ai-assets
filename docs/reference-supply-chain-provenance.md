# Reference: Supply-chain provenance and release evidence

## Scope

This note reviews mature supply-chain provenance, attestation, signing, and SBOM systems as external references for Portable AI Assets. The goal is to learn how public software projects communicate release trust and audit evidence without pretending that local report files are external cryptographic proof.

Reviewed references:

- Sigstore documentation
- SLSA specification
- in-toto documentation and specification entrypoints
- CycloneDX SBOM capabilities and specification overview
- SPDX specifications

Source URLs reviewed:

- https://docs.sigstore.dev/
- https://slsa.dev/spec/v1.2/
- https://slsa.dev/spec/v1.2/attestation-model
- https://slsa.dev/spec/v1.2/provenance
- https://in-toto.io/
- https://in-toto.io/docs/
- https://cyclonedx.org/specification/overview/
- https://cyclonedx.org/capabilities/sbom/
- https://spdx.dev/use/specifications/

## What these systems do well

### Sigstore

Sigstore makes software signing easier to verify at ecosystem scale. Its keyless model, certificate transparency, Rekor transparency log, Fulcio certificates, and bundle-oriented verification show how authenticity evidence should be tied to identities, signatures, timestamps, and public append-only records rather than hidden local assertions.

Useful lesson: Portable AI Assets can learn the language of signing subjects, identity, transparency, and verifier handoff, but local release evidence must remain explicitly unsigned until a real signing flow exists. A local Markdown or JSON report must not be described as a Sigstore-signed artifact.

### SLSA

SLSA provides an industry-consensus framework for describing and incrementally improving supply-chain security. It organizes build/source expectations into levels and tracks, and its provenance guidance focuses on verifiable information about where, when, and how an artifact was produced. Its attestation model separates explicit metadata from signatures: the signature authenticates who made the statement, while the predicate describes facts such as build command, materials, builder, and subject.

Useful lesson: Portable AI Assets should use level-like maturity language carefully. It can report local evidence completeness and threat-boundary coverage, but it should not claim a SLSA level unless the required build platform, provenance generation, distribution, and verification properties are actually implemented.

### in-toto

in-toto models a software supply chain as a sequence of steps with signed metadata about materials, products, commands, and expected relationships. It gives projects a vocabulary for linking evidence across build, test, package, and release steps and for checking that the delivered artifact followed the expected path.

Useful lesson: Portable AI Assets can adopt a lightweight evidence-chain vocabulary for release closure: subject, materials, steps, products, expected checks, and reviewer handoff. It should not become a supply-chain workflow executor or create misleading signed link metadata without real keys, identities, and verification.

### CycloneDX

CycloneDX provides a mature SBOM model for inventorying software components, services, dependency relationships, vulnerabilities, attestations, and adjacent BOM types. Its SBOM framing is useful because it makes release contents inspectable and machine-readable rather than relying on narrative release notes alone.

Useful lesson: Portable AI Assets public release packs should keep strong manifest and component inventory evidence: files, schemas, sample assets, adapter metadata, docs, reports, checksums, and relationships. The project should not become an SBOM registry, vulnerability scanner, dependency resolver, or SaaS compliance platform.

### SPDX

SPDX specifications provide a standard way to communicate software bill-of-materials data, licensing, copyright, package/file relationships, and provenance-like metadata across organizations and tooling. SPDX reinforces that license and component metadata are part of release trust, not an afterthought.

Useful lesson: Portable AI Assets should keep public release evidence license-aware and relationship-aware. It can document which public sample assets, schemas, docs, and scripts are included and under what terms, while keeping private memory, raw runtime state, and credential-bearing data out of public artifacts.

## Patterns Portable AI Assets should absorb

### 1. Subject, materials, builder, and products vocabulary

Release evidence should identify:

- the release subject, such as an archive path, staging tree, or demo pack;
- materials, such as source files, schemas, sample assets, docs, and prior gate reports;
- builder or generator identity, limited to local tool/version/script metadata that is public-safe;
- products, such as release archive, checksum file, staging tree, handoff pack, provenance JSON, and closure report;
- timestamps and hashes where they are already computed locally;
- verification status and drift status.

This is useful even before external signing because it gives reviewers a consistent evidence model.

### 2. Attestation-style structure without fake attestation claims

SLSA and in-toto show that an attestation needs an authenticated statement plus a predicate. Portable AI Assets can mirror the shape for local audit metadata:

- `subject`: what artifact or tree the report describes;
- `predicate_type`: local Portable AI Assets release-evidence vocabulary;
- `predicate`: checks, materials, commands declared by existing gates, boundaries, and result summaries;
- `verification`: recomputed hash/tree-digest checks;
- `limitations`: unsigned, local-only, not transparency-log-backed, not third-party-certified.

The naming must stay honest: local unsigned audit metadata is not external attestation, not a signature, and not a compliance certification.

### 3. SBOM and release inventory thinking

CycloneDX and SPDX reinforce that public release artifacts should be inspectable. Portable AI Assets should continue to expose:

- release pack manifest;
- package/archive index;
- checksums;
- docs/reference inventory;
- sample asset inventory;
- adapter/capability inventory;
- license/security/release notes;
- redaction and public-safety evidence.

For v0.1, this can remain a local manifest/checksum/report set instead of a full CycloneDX or SPDX document.

### 4. Transparency about maturity and non-goals

Mature supply-chain systems distinguish claim strength. Portable AI Assets should make release status names precise:

- `ready-for-manual-release-review` is a review state, not publish approval;
- unsigned provenance is useful reviewer metadata, not authenticity proof;
- local verification detects drift in local artifacts, not compromise across the whole ecosystem;
- release closure aggregates evidence, but does not sign, upload, publish, or certify anything.

### 5. Evidence chain before publication

Before public publication, reviewers should be able to trace:

1. public-safety scan status;
2. release-readiness status;
3. demo pack status;
4. public release pack/archive/smoke-test status;
5. GitHub publish/staging/dry-run/handoff/final-preflight status;
6. unsigned provenance and provenance verification status;
7. completed-work-review alignment;
8. release-closure aggregation.

This mirrors supply-chain thinking while staying within the project’s non-executing release boundary.

## What Portable AI Assets should not absorb

Portable AI Assets should not become:

- a signing authority;
- a certificate authority;
- a transparency log;
- a SLSA build platform;
- an in-toto layout/link metadata executor;
- an SBOM registry;
- a vulnerability scanner;
- a license compliance service;
- a package registry or artifact repository;
- a CI/CD release automation system;
- a hosted compliance or policy engine.

It should also avoid:

- claiming Sigstore signing without a real signature, certificate, and transparency log bundle;
- claiming a SLSA level without meeting the required controls;
- generating fake in-toto signed metadata;
- uploading provenance, attestations, SBOMs, or release assets automatically;
- calling GitHub, registries, identity providers, package indexes, or transparency logs from default gates;
- validating credentials or reading token values;
- embedding private paths, account IDs, emails, tenant IDs, repository remotes, API keys, OAuth tokens, webhook URLs, or connection strings in public reports.

## Safe integration boundary

The safe boundary is:

```text
Supply-chain systems → public docs/spec review → local release-evidence vocabulary → unsigned public-safe manifest/checksum/provenance reports → manual reviewer handoff → optional future external signing outside default gates.
```

Report-only modes may inspect local public-safe release artifacts, docs, checksums, manifests, and latest gate reports. They must not:

- sign artifacts;
- create certificates;
- upload to transparency logs;
- generate externally authenticated attestations;
- publish releases;
- create GitHub repos, remotes, tags, or releases;
- call provider, registry, GitHub, package, webhook, identity, or transparency-log APIs;
- authenticate or validate credentials;
- execute hooks, actions, build steps, package managers, or CI workflows;
- mutate runtime/admin/provider state;
- commit or push.

## Schema, adapter, and report implications

Near-term implications:

1. Keep `--release-provenance`, `--verify-release-provenance`, and `--release-closure` language explicit: unsigned local audit metadata, not external authenticity proof.
2. Consider future release evidence JSON fields that align with subject/materials/builder/products/predicate/limitations vocabulary.
3. Keep SBOM-style inventories as public-safe manifests/checksums before adopting a full CycloneDX or SPDX document format.
4. Add stronger docs around which evidence a manual reviewer should trust and which evidence remains out of scope.
5. Defer real signing, external attestations, transparency-log upload, and registry publication until the project intentionally designs a separate manual or opt-in release process.

## Raw/runtime data that must remain outside Git

Keep these out of Git and public release packs:

- private memory, private project summaries, private skills, and raw agent sessions;
- runtime databases, traces, caches, logs, embeddings, generated diffs, and local backups;
- private repository remotes, branch protection exports, CI secrets, signing keys, certificates, OIDC tokens, and registry credentials;
- local absolute paths, hostnames, usernames, account IDs, tenant IDs, emails, and organization identifiers;
- webhook URLs, API endpoints with secrets, connection strings, package registry tokens, and cloud/provider admin exports;
- vulnerability scanner outputs or license exports that contain private dependency or customer context unless redacted.

## Adoption decision

Adopt the subject/materials/products vocabulary, attestation-shaped local evidence structure, SBOM-style inventory discipline, explicit maturity labeling, and release evidence chain mindset. Do not adopt signing authority, transparency-log, SLSA certification, in-toto execution, SBOM registry, vulnerability scanning, automated publication, credential validation, commit, push, or provider/API behavior.

For Phase 75, this remains a reviewed reference document plus backlog/strategy/roadmap/release alignment update. It does not add signing, attestation generation, transparency-log upload, SBOM publication, provider/API calls, credential validation, hooks/actions/code execution, commit, push, or release publication behavior.
