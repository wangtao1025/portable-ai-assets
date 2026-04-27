# Security Model

## Principle

Portable AI Assets System separates AI-related information into **public**, **private**, and **secret** asset classes.

The project should never assume all AI state is equally shareable.

---

## Asset classes

### 1. Public
Safe to publish in an open-source repository.

Examples:
- engine / CLI code
- adapters framework
- manifests without personal data
- docs
- tests
- example templates

### 2. Private
Not suitable for public publication, but may be versioned in a private repository or stored in local backup.

Examples:
- personal memory
- project summaries
- runtime-local instruction files with user-specific context
- merge candidate bundles
- review artifacts

### 3. Secret
Must not be committed to Git and should be excluded from public and private source releases unless separately encrypted and intentionally managed.

Examples:
- auth.json
- tokens
- credential-bearing local config
- secret bindings

---

## Recommended boundaries

### Public Git layer
Should contain:
- schemas
- manifests
- engine code
- docs
- templates
- public-safe examples

### Private Git layer (optional, but recommended for real usage)
May contain:
- redacted memory summaries
- private adapters
- non-secret project-level AI assets
- canonical user/team AI asset repo separate from the public engine repo

### Non-Git backup layer
Should contain:
- sessions
- histories
- state DBs
- runtime-heavy archives
- machine-local drift evidence

---

## Review-before-apply rule

Any drifted target with user-specific local state should pass through:

1. inspect
2. diff
3. merge-candidates
4. human review
5. review-apply

This rule exists to prevent accidental overwrite of locally evolved AI behavior.

---

## Release guidance

Before open-sourcing any repository snapshot:

- remove or redact private memory
- exclude non-Git backups
- exclude local auth/config secrets
- replace real summaries with templates/examples
- check merge candidate bundles for personal content

---

## Security thesis

The project is valuable only if portability does **not** collapse privacy boundaries.

Ownership and portability must be paired with:
- reviewability
- redaction
- explicit asset classification
- conservative apply behavior
