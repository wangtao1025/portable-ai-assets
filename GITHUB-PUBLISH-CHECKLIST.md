# GitHub Publish Checklist

This staging tree is generated for manual review before creating or pushing a public GitHub repository.

## Required before publishing

- [ ] Review README, docs, examples, schemas, and adapter registry.
- [ ] Confirm `LICENSE`, `SECURITY.md`, `CHANGELOG.md`, and `RELEASE_NOTES-v0.1.md` are acceptable.
- [ ] Run `python3 -m unittest tests/test_bootstrap_phase4.py` if tests are included and local Python supports it.
- [ ] Run `./bin/paa install` and `paa doctor` if validating global CLI installation locally.
- [ ] Run `./bin/paa safety --both` (or `/bin/bash bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both`) inside this staging repo.
- [ ] Treat committed `bootstrap/reports/latest-*` files as static sanitized snapshots, not live GitHub state; rerun local report-only gates for current status.
- [ ] Confirm no private memory, runtime DBs/logs, backups, candidates, machine-local config, or secrets are present.
- [ ] Create the GitHub repo manually and push only after review.

## Suggested GitHub metadata

- Description: Portable AI Assets is a cross-agent continuity layer for owning AI memory, skills, adapters, schemas, and migration workflows outside any single runtime.
- Topics: ai-agents, ai-memory, mcp, local-first, agentic-workflows, ai-portability, developer-tools, schemas
- Existing release tag: v0.1.0; do not move it. v0.1.1 already exists and v0.1.2 already exists; do not move them. Use a new tag (for example v0.1.3) for follow-up releases.
