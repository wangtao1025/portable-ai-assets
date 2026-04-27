# AI-Assets Release Readiness Report

Generated: 2026-04-27T15:07:12
Engine root: `/Users/example/AI-Assets`
Asset root: `/Users/example/AI-Assets`

## Summary

- Readiness: ready
- Checks: 31
- Pass: 31
- Warn: 0
- Fail: 0
- Schema invalid: 0
- Safety blockers: 0
- Safety warnings: 0

## Checks

- **pass** `required:README.md` (required): README.md
- **pass** `required:CONTRIBUTING.md` (required): CONTRIBUTING.md
- **pass** `required:LICENSE` (required): LICENSE
- **pass** `required:SECURITY.md` (required): SECURITY.md
- **pass** `required:CHANGELOG.md` (required): CHANGELOG.md
- **pass** `required:RELEASE_NOTES-v0.1.md` (required): RELEASE_NOTES-v0.1.md
- **pass** `required:docs/architecture.md` (required): docs/architecture.md
- **pass** `required:docs/non-goals.md` (required): docs/non-goals.md
- **pass** `required:docs/adapter-sdk.md` (required): docs/adapter-sdk.md
- **pass** `required:docs/open-source-release-plan.md` (required): docs/open-source-release-plan.md
- **pass** `required:docs/capability-policy-candidate-generation.md` (required): docs/capability-policy-candidate-generation.md
- **pass** `required:docs/reference-capability-policy-candidate-generation.md` (required): docs/reference-capability-policy-candidate-generation.md
- **pass** `required:docs/capability-policy-candidate-status.md` (required): docs/capability-policy-candidate-status.md
- **pass** `required:docs/reference-capability-policy-candidate-status.md` (required): docs/reference-capability-policy-candidate-status.md
- **pass** `required:schemas/README.md` (required): schemas/README.md
- **pass** `required:sample-assets/README.md` (required): sample-assets/README.md
- **pass** `required:examples/README.md` (required): examples/README.md
- **pass** `required:examples/redacted/README.md` (required): examples/redacted/README.md
- **pass** `required:bootstrap/setup/bootstrap-ai-assets.sh` (required): bootstrap/setup/bootstrap-ai-assets.sh
- **pass** `required:bootstrap/setup/bootstrap_ai_assets.py` (required): bootstrap/setup/bootstrap_ai_assets.py
- **pass** `schema-validation` (required): valid=16 invalid=0
- **pass** `adapter-contracts` (required): total=5 invalid=0
- **pass** `portable-skills` (recommended): total=1 invalid=0
- **pass** `team-pack-preview` (recommended): manifests=1 public_safe=1
- **pass** `capability-risk-inventory` (recommended): capabilities=11 risks={'read-only-data': 5, 'text-only': 3, 'write-files': 3}
- **pass** `project-pack-preview` (recommended): manifests=1 capabilities=2
- **pass** `capability-policy-preview` (recommended): added=0 removed=0 risk_upgrades=0
- **pass** `capability-policy-candidate-generation-template` (recommended): template present and reviewed-baseline.yaml absent
- **pass** `capability-policy-candidate-status` (recommended): status=needs-human-review apply_readiness=needs-human-review writes=0/0
- **pass** `public-safety-scan` (required): blockers=0 warnings=0
- **pass** `public-demo-pack` (recommended): examples/redacted/public-demo-pack/MANIFEST.json

## Recommendations

- Resolve fail checks before cutting a public release.
- Review warn checks and regenerate the public demo pack immediately before publication.
- Keep the private asset repo separate from this public engine/demo surface.
