# Open-Source Demo Pack

This document describes the smallest public-safe bundle that can be zipped or copied as a lightweight release/demo artifact.

## Goal

Package the most persuasive existing prototype outputs into one directory so someone can review the project quickly without running every command themselves.

The pack should communicate the full **Portable AI Assets demo arc**:
1. the public thesis: own the AI work environment instead of rebuilding it when tools, models, clients, or machines change;
2. the technical shape: schemas, adapters, previews, and redacted examples;
3. the safety shape: public-safety, release-readiness, and completed-work-review reports;
4. the boundary: report-only/public-safe evidence, not runtime execution.

---

## Generate the pack

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --public-demo-pack --both
```

Outputs:
- `bootstrap/reports/latest-public-demo-pack.md`
- `bootstrap/reports/latest-public-demo-pack.json`
- `examples/redacted/public-demo-pack/`

---

## Current pack contents

The pack pulls from public-safe artifacts that already exist in the repo:
- `README.md`
- `docs/architecture.md`
- `docs/adapter-sdk.md`
- `docs/public-facing-thesis.md`
- `docs/open-source-demo-story.md`
- `docs/open-source-demo-pack.md`
- `docs/reference-coding-agent-workspace-portability.md`
- `bootstrap/reports/latest-validate-schemas.md`
- `bootstrap/reports/latest-connectors.md`
- `bootstrap/reports/latest-connector-preview.md`
- `bootstrap/reports/latest-public-safety-scan.md`
- `bootstrap/reports/latest-release-readiness.md`
- `bootstrap/reports/latest-completed-work-review.md`
- `examples/redacted/connector-walkthrough.example.md`
- `examples/redacted/demo-story.example.md`

It also generates:
- `examples/redacted/public-demo-pack/PACK-INDEX.md`
- `examples/redacted/public-demo-pack/MANIFEST.json`

The manifest currently records:
- `generated_at`
- `asset_class`
- `pack_kind`
- `file_count`
- `files`

---

## Why this matters

The pack turns the prototype into something much easier to:
- attach to a release
- hand to an open-source reviewer
- share in a thread or issue
- compare across iterations
- export or zip later without re-deciding what belongs in the bundle

It is intentionally simple:
- no secrets
- no private memory
- no runtime DBs
- no live machine mutation
- manifest-first metadata so future export tooling has a stable anchor
- safety/release/review reports included as evidence before sharing

---

## Recommended use

A good public demo cadence is:
1. read the README/public thesis for the 60-second positioning
2. `--validate-schemas`
3. `--connectors`
4. `--connector-preview`
5. `--redacted-examples`
6. `--public-safety-scan`
7. `--release-readiness`
8. `--completed-work-review`
9. `--demo-story`
10. `--public-demo-pack`

That sequence yields both deep artifacts and a compact shareable bundle.

---

## Non-goals

The pack does not:
- execute agents or workflows;
- call providers, APIs, webhooks, MCP servers, or remote services;
- authenticate against user accounts;
- publish to GitHub;
- prove full universal migration.

It demonstrates the current public-safe project shape: a portable asset layer with reviewable reports and redacted examples.
