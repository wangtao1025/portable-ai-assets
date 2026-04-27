# Open-Source Demo Story

This document describes the shortest public-safe walkthrough for showing what Portable AI Assets System already does.

## Goal

Demonstrate that the project is not just a schema collection, but a working **portable AI work-environment layer** with:
- a clear 60-second public thesis
- manifest validation
- adapter inventory
- connector action preview
- redacted public-safe example artifact generation
- public safety / release readiness / completed-work-review gates
- a compact public demo pack

---

## 60-second promise

> Own your AI work environment instead of rebuilding it every time you change tools, models, clients, or machines.

The demo should let a new reader understand this arc quickly:
1. durable AI work-environment assets can be represented explicitly;
2. runtime adapters can describe where those assets project without becoming a runtime;
3. connector previews can explain behavior before any live write;
4. redacted examples and public review gates make the story safe to share.

---

## Recommended sequence

### 1. Explain the public thesis

Read:
- `README.md`
- `docs/public-facing-thesis.md`

Expected takeaway: this project is the portability/ownership layer above agents, memory backends, workflow builders, and MCP hosts.

### 2. Validate manifests

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --validate-schemas --both
```

Review:
- `bootstrap/reports/latest-validate-schemas.md`

### 3. Inspect adapter inventory

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --connectors --both
```

Review:
- `bootstrap/reports/latest-connectors.md`

### 4. Preview connector behavior without writing files

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --connector-preview --both
```

Review:
- `bootstrap/reports/latest-connector-preview.md`

This is the safest way to explain what the built-in connector vocabulary means today.

### 5. Generate public-safe example outputs

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --redacted-examples --both
```

Review:
- `examples/redacted/connector-walkthrough.example.md`
- `examples/redacted/connector-summary.example.json`

### 6. Run public sharing gates

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both
./bootstrap/setup/bootstrap-ai-assets.sh --release-readiness --both
./bootstrap/setup/bootstrap-ai-assets.sh --completed-work-review --both
```

Review:
- `bootstrap/reports/latest-public-safety-scan.md`
- `bootstrap/reports/latest-release-readiness.md`
- `bootstrap/reports/latest-completed-work-review.md`

### 7. Generate the packaged demo story

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --demo-story --both
```

Review:
- `bootstrap/reports/latest-demo-story.md`
- `examples/redacted/demo-story.example.md`

### 8. Generate the public demo pack

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --public-demo-pack --both
```

Review:
- `bootstrap/reports/latest-public-demo-pack.md`
- `examples/redacted/public-demo-pack/`

---

## What to share publicly

A reasonable first public bundle is:
- `README.md`
- `docs/public-facing-thesis.md`
- `docs/architecture.md`
- `docs/adapter-sdk.md`
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

---

## Why this sequence works

It tells a clear story:
1. the project has a public thesis that is easy to understand;
2. it has machine-checkable structure;
3. it understands runtimes through adapter contracts;
4. it can preview how those contracts map canonical assets to runtime surfaces;
5. it can generate public-safe artifacts for open-source explanation;
6. it can run safety/release/review gates before sharing.

That is enough to demonstrate real product shape without exposing private memory or pretending full universal migration already exists.

---

## Safety boundary

The demo is intentionally narrow:
- no private memory
- no credentials
- no provider/API calls
- no agent execution
- no shell/browser/MCP invocation by adapters
- no Git remote mutation
- no runtime/admin/provider state writes

It is a public-safe story about the portable asset layer, not a claim that the project is already a universal agent runtime or live migration engine.
