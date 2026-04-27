# AI-Assets Team Pack Preview

Generated: 2026-04-24T21:50:43
Engine root: `/Users/example/AI-Assets`
Asset root: `/Users/example/AI-Assets`

## Summary

- Status: ready
- Manifests: 1
- Public-safe manifests: 1
- Roles: 3
- Layers: 2
- Checks: 6
- Pass: 6
- Warn: 0
- Fail: 0

## Manifests

### example-team-pack
- path: `sample-assets/team-pack/team-pack.yaml`
- version: v1
- asset_class: public
- shareability: public-safe
- apply_policy: human-review-required
- layers: team-baseline, role-profile
- roles: engineer, product, research
- missing_references: 0

## Checks

- **pass** `required:docs/team-grade-packaging.md`: docs/team-grade-packaging.md
- **pass** `required:sample-assets/team-pack/README.md`: sample-assets/team-pack/README.md
- **pass** `required:examples/redacted/team-pack.example.md`: examples/redacted/team-pack.example.md
- **pass** `has-team-pack-manifest`: 1
- **pass** `all-references-exist`: 0
- **pass** `public-safe-sample`: 1

## Recommendations

- Treat team packs as canonical layer inputs, not live runtime overwrites.
- Use preview/candidate/review/apply stages before projecting shared team guidance into adapters.
- Keep individual private memory and secrets outside shared team packs.
