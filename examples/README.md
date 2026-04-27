# Examples

This directory contains public-safe example flows and redacted outputs.

Suggested starting points:
- `../sample-assets/` for redacted manifest examples
- `../sample-assets/adapters/` for public-safe adapter contract examples
- `./redacted/` for public-safe walkthrough outputs
- schema validation via `bootstrap/setup/bootstrap-ai-assets.sh --validate-schemas --both`
- connector inventory via `bootstrap/setup/bootstrap-ai-assets.sh --connectors --both`
- connector execution preview via `bootstrap/setup/bootstrap-ai-assets.sh --connector-preview --both`
- generate redacted examples via `bootstrap/setup/bootstrap-ai-assets.sh --redacted-examples --both`
- generate a packaged demo walkthrough via `bootstrap/setup/bootstrap-ai-assets.sh --demo-story --both`
- generate a shareable public demo pack via `bootstrap/setup/bootstrap-ai-assets.sh --public-demo-pack --both`
- inspect pack metadata in `examples/redacted/public-demo-pack/MANIFEST.json`
- redacted reports copied here only after personal content is removed

The purpose is to show how the system works without publishing real memory, runtime instructions, or local machine state.
