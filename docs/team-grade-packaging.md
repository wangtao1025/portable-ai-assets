# Team-Grade Packaging

Phase 50 extends Portable AI Assets from an individual continuity layer toward team-safe asset packs. The goal is not to centralize everyone into one giant memory store. The goal is to package reviewed, role-scoped, public/private-aware AI assets so a team can bootstrap shared behavior without leaking personal memory or overwriting local customization.

## Goals

Team-grade packaging should support:

- shared team policies and playbooks;
- role-specific profiles for engineering, product, research, support, or ops;
- layered overrides where a team baseline can be extended by project, role, and individual assets;
- public-safe sample packs that demonstrate structure without real private memory;
- report-only preview before any team pack is applied to a private asset root or runtime adapter.

## Non-goals

This phase does not provide:

- real-time team memory sync;
- multi-user permissions or hosted access control;
- automatic publication of private team data;
- automatic overwrite of individual runtime memory or instruction files;
- secret distribution or credential management.

## Layer model

Recommended layer order:

```text
base public engine
  -> sample/public team pack
  -> private organization pack
  -> project pack
  -> role profile
  -> individual private asset root
  -> runtime adapters generated through review/apply gates
```

Each layer should declare whether it is:

- `public-safe` — safe to publish as an example;
- `team-private` — safe only inside a team/private repo;
- `individual-private` — user-specific and not part of shared team baselines;
- `secret-external` — referenced only by secret manager or local config, never committed.

## Recommended team pack structure

```text
team-pack/
├── team-pack.yaml
├── README.md
├── policies/
│   └── engineering-review.md
├── roles/
│   ├── engineer.md
│   ├── product.md
│   └── research.md
├── playbooks/
│   └── release-readiness.md
└── adapters/
    └── shared-instructions.md
```

## Manifest fields

A minimal team pack manifest should describe:

```yaml
name: example-team-pack
pack_version: v1
asset_class: public
shareability: public-safe
description: Public-safe example team asset pack.
layers:
  - team-baseline
  - role-profile
roles:
  - engineer
  - product
policies:
  - policies/engineering-review.md
playbooks:
  - playbooks/release-readiness.md
adapters:
  - adapters/shared-instructions.md
apply_policy: human-review-required
```

## Safety rules

1. Team packs are canonical assets, not runtime dumps.
2. Team packs should not include real private user memory by default.
3. Role profiles should be additive and reviewable.
4. Individual private asset roots remain the final local source before runtime projection.
5. Applying team pack content into adapters should require a preview or candidate stage before writes.
6. Secrets and credentials remain external references only.
7. Public example packs must use fake names, fake paths, and redacted examples.

## Report implications

The `--team-pack-preview` report should remain report-only and should show:

- discovered team pack manifests;
- public-safe vs private classification;
- layer names;
- roles;
- referenced policies/playbooks/adapters and whether they exist;
- apply policy;
- warnings for missing docs, secret-like content, or private absolute paths in public packs.

## Future apply model

A future apply flow should be staged:

1. inventory team packs;
2. preview resolved layer order;
3. generate candidate adapter/profile bundles;
4. require review for team-private content;
5. apply only reviewed blocks into private canonical adapters;
6. never write directly into live runtime files from a team pack.

## Summary judgment

Team-grade packaging should make Portable AI Assets useful for small teams without compromising the core safety model. The right v1 is manifest-first and preview-first: define public-safe example packs, report their structure, and keep all real team/private rollout behind explicit review gates.
