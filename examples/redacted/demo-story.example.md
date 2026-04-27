# Portable AI Assets Demo Story

This is a public-safe walkthrough for demonstrating the open-source prototype.

## 60-second promise

Own your AI work environment instead of rebuilding it every time you change tools, models, clients, or machines.

The demo arc shows a portable asset layer in miniature: machine-checkable structure, runtime adapter vocabulary, non-mutating connector previews, redacted public examples, and safety/release review gates.

## Step 1 — Validate schemas

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --validate-schemas --both`
Expected valid manifests: 16

## Step 2 — Inspect adapter inventory

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --connectors --both`
Expected runtimes: claude-code, codex, example-runtime, hermes, memos-local-plugin-hermes

## Step 3 — Preview built-in connector actions

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --connector-preview --both`
Expected previewable adapters: 5

## Step 4 — Generate public-safe example artifacts

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --redacted-examples --both`
Expected artifact: `examples/redacted/connector-walkthrough.example.md`

## Step 5 — Run public safety and release review gates

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both`
Expected report: `bootstrap/reports/latest-public-safety-scan.md`

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --release-readiness --both`
Expected report: `bootstrap/reports/latest-release-readiness.md`

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --completed-work-review --both`
Expected report: `bootstrap/reports/latest-completed-work-review.md`

## Step 6 — Package the demo story

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --demo-story --both`
Expected artifact: `examples/redacted/demo-story.example.md`

## Step 7 — Build the public demo pack

Run: `./bootstrap/setup/bootstrap-ai-assets.sh --public-demo-pack --both`
Expected artifact: `examples/redacted/public-demo-pack/`

## Suggested sharing bundle

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
