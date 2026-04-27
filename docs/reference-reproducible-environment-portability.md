# Reference: Reproducible environment portability

## Scope

This note reviews mature reproducible-environment and dotfile systems as external references for Portable AI Assets. The goal is to learn how mature projects separate declarative portable state from local machine state, runtime activation, package installation, secrets, and administrator control.

Reviewed references:

- Nix flakes documentation
- Home Manager manual
- Dev Containers specification and metadata reference
- chezmoi documentation
- yadm documentation

Source URLs reviewed:

- https://nix.dev/concepts/flakes
- https://nix.dev/manual/nix/latest/command-ref/new-cli/nix3-flake
- https://nix-community.github.io/home-manager/
- https://containers.dev/
- https://containers.dev/implementors/spec/
- https://containers.dev/implementors/json_reference/
- https://containers.dev/implementors/features/
- https://containers.dev/implementors/templates/
- https://www.chezmoi.io/
- https://www.chezmoi.io/user-guide/daily-operations/
- https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/
- https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/
- https://yadm.io/
- https://yadm.io/docs/overview
- https://yadm.io/docs/alternates
- https://yadm.io/docs/bootstrap
- https://yadm.io/docs/encryption
- https://yadm.io/docs/hooks

## What these systems do well

### Nix flakes

Nix flakes provide a standard project entrypoint with declared `inputs`, declared `outputs`, and a lock file that pins dependency versions. They make project interfaces discoverable through predictable output schemas while keeping implementation details behind a stable manifest. They also make provenance concrete: a lock file can explain which sources and revisions a reproducible environment expected.

Useful lesson: portable AI environment descriptors need a manifest plus provenance/lock evidence, but the lock evidence should be treated as review metadata rather than an instruction to fetch, build, or execute dependencies.

### Home Manager

Home Manager makes user-environment configuration declarative while separating validation/build from activation. It performs option type checks and assertions, tracks generations, supports rollback, and detects file collisions before overwriting user files. Its module/options model is useful because it gives configuration a typed, documented surface rather than an unstructured script bundle.

Useful lesson: Portable AI Assets should keep a strong distinction between validation/preview and activation. Collision detection, compatibility versions, generation metadata, and typed options are all useful for future reviewed projections.

### Dev Containers

Dev Containers use a small declarative entrypoint such as `devcontainer.json`, predictable discovery paths, schema-driven metadata, namespaced tool customizations, host-resource declarations, features, templates, and lifecycle hooks. The specification is a strong interoperability reference because multiple tools can interpret the same manifest while the runtime/container implementation remains outside the manifest itself.

Useful lesson: Portable AI Assets can adopt schema-first environment metadata, predictable discovery conventions, explicit merge rules, namespaced runtime-specific customizations, advisory host requirements, and template-like starter bundles. It should not adopt container build/run behavior or lifecycle command execution.

### chezmoi

chezmoi separates source state from target home-directory state, supports machine-specific templates and data, and emphasizes preview-first workflows such as diff before apply. It also documents script behavior, external archives, encryption, password-manager integration, and auto-sync hazards clearly.

Useful lesson: machine/context-aware projection is valuable, but executable scripts, secret providers, and auto-push behavior are trust boundaries that should remain outside public Portable AI Assets by default.

### yadm

yadm provides a lightweight Git-native model for dotfiles. It keeps files in their normal target paths, supports alternates by OS/distro/hostname/user/architecture/class, and exposes bootstrap, hook, and encryption mechanisms. It is intentionally close to Git, which makes review and history understandable.

Useful lesson: context selectors and Git-friendly review are useful, but `$HOME`-rooted worktrees, bootstrap/hook execution, symlink-like projection, and encrypted secret archives should not become core Portable AI Assets behavior.

## Patterns Portable AI Assets should absorb

### 1. Manifest plus provenance/lock evidence

Portable environment descriptors should record:

- stable environment id, version, owner/source, lifecycle status, and review status;
- required runtime families such as shell, language toolchain, package manager, container, editor, or agent runtime;
- pinned references, checksums, lock-file paths, or provenance notes where available;
- compatibility and state-version fields to avoid silent semantic drift;
- target machine selectors such as OS, architecture, host class, project class, and optional accelerator/resource class;
- public/private classification and redaction posture.

This should support review and reproducibility reasoning without fetching, installing, building, or activating anything.

### 2. Preview-first projection and collision detection

Home Manager, chezmoi, and yadm all reinforce that environment portability can damage user state if apply behavior is careless. Future Portable AI Assets projections should therefore preview:

- target files that would be created or changed;
- likely collisions with existing runtime files;
- machine selector matches and mismatches;
- version or lock drift;
- capability changes such as package installation, script execution, network fetches, mounts, ports, services, credentials, or admin permissions.

The default answer should be “review the diff,” not “apply now.”

### 3. Layering and namespaced customization

Dev Containers and Home Manager show that layered configuration needs explicit merge semantics. Portable AI Assets should prefer layered metadata such as:

- project baseline;
- personal local overlay;
- team/shared overlay;
- runtime adapter projection;
- reviewer-approved exception.

Runtime-specific settings should live under namespaced sections so the canonical layer does not become coupled to one tool, editor, model, package manager, or OS.

### 4. Context selectors without hidden host mutation

chezmoi and yadm make machine-specific differences explicit through templates, data, and alternates. Portable AI Assets should adopt context selectors for review and projection decisions, for example:

- OS and architecture;
- repo/project class;
- agent/runtime target;
- private vs public release context;
- resource class such as CPU-only, GPU-optional, or high-memory;
- local-only environment binding labels.

Selectors should decide which metadata is relevant. They should not secretly mutate `$HOME`, shell profiles, service definitions, package stores, or credential providers.

### 5. Action surfaces must be visible as risk

Dev Container lifecycle commands, Features install scripts, Home Manager activation, chezmoi scripts, yadm bootstrap/hooks, package installs, secret providers, mounts, ports, and privileged container flags all represent action surfaces. Portable AI Assets should model them as capability declarations before any projection:

- text-only environment notes;
- read-only inventory;
- file writes;
- package install/build/fetch;
- shell/code execution;
- container/runtime start;
- network/API access;
- credential binding or secret provider use;
- admin/root/service control;
- background/scheduled behavior.

This aligns with the existing capability-risk gates and keeps environment portability from smuggling execution into a documentation-looking manifest.

## What Portable AI Assets should not absorb

Portable AI Assets should not become:

- a package manager;
- a Nix/Home Manager wrapper;
- a container runtime or Dev Containers implementation;
- a dotfile manager;
- a `$HOME` worktree manager;
- an activation engine;
- a bootstrap or hook runner;
- a service manager;
- a secret manager;
- a root/admin provisioning tool;
- a network dependency fetcher;
- a machine fleet reconciliation engine.

It should also avoid:

- `curl | sh` style install/apply flows;
- automatic `apply`, `update`, `autoCommit`, or `autoPush` behavior;
- executing Dev Container lifecycle commands or Feature install scripts;
- building or starting containers;
- installing packages or mutating package stores;
- reading secret values from environment variables, password managers, encrypted archives, or provider CLIs;
- embedding absolute private paths, hostnames, user names, repository remotes, account IDs, ports, API keys, OAuth tokens, webhook URLs, or connection strings in public docs/reports.

## Safe integration boundary

The safe boundary is:

```text
External environment/dotfile systems → read-only manifest and docs review → portable environment descriptor candidates → compatibility/collision/capability preview → optional narrow human-reviewed projection by an external runtime/tool.
```

Report-only modes may inspect public-safe manifests, docs, lock/provenance metadata, and local sample files. They must not:

- install packages;
- fetch dependencies;
- build derivations or images;
- start containers;
- run activation scripts, lifecycle commands, bootstrap scripts, hooks, or setup code;
- mount local paths or open ports;
- read or validate credentials;
- mutate `$HOME`, shell profiles, package stores, service definitions, runtime caches, provider state, admin settings, or repositories;
- commit, push, auto-sync, or publish.

## Schema, adapter, and report implications

Near-term implications:

1. Consider a future `portable-environment-descriptor-v1` only as a non-executing metadata/review artifact.
2. Add environment compatibility and collision preview before any adapter writes environment-related files.
3. Represent lock/provenance evidence as audit data, not as permission to fetch/build.
4. Extend capability-risk reporting to make environment action surfaces visible: package install, lifecycle command, container start, mount/port exposure, secret provider, and admin/root control.
5. Keep docs/reference reviews first; defer implementation until a concrete adapter or public demo needs environment descriptor projection.

## Raw/runtime data that must remain outside Git

Keep these out of Git and public release packs:

- private dotfiles and shell profiles unless rewritten as public-safe examples;
- machine hostnames, usernames, local absolute paths, local network names, and device identifiers;
- package store caches, build artifacts, container images, volumes, mounts, and logs;
- Home Manager generations, activation logs, and local profile state;
- Dev Container runtime state, Docker/Podman metadata, forwarded ports, bind mounts, and feature install output;
- chezmoi/yadm private source trees, encrypted secret archives, password-manager references, bootstrap logs, hook outputs, and auto-sync settings;
- environment variables and secret values;
- provider credentials, tokens, webhook URLs, endpoints, account IDs, and connection strings.

## Adoption decision

Adopt the manifest, lock/provenance, schema, preview, collision-detection, layering, namespaced customization, context-selector, and action-risk lessons. Do not adopt package management, container execution, dotfile application, bootstrap/hook execution, secret management, admin provisioning, auto-sync, or machine-fleet reconciliation scope.

For Phase 74, this remains a reviewed reference document plus backlog/strategy/roadmap/release alignment update. It does not add install, build, container, activation, provider/API, credential, hook, commit, push, or publication behavior.
