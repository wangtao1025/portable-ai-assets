# Restore Readiness Smoke Plan

This document records the minimal restore path for the Portable AI Assets split-repo setup after the private root was backed up to GitHub.

## Repository roles

- **private canonical assets repo**: `wangtao1025/ai-assets-private`
  - Visibility must remain PRIVATE.
  - Contains canonical memories, adapter manifests, local restore workflows, private stack metadata, and private/local paths.
  - Do not copy this repo directly to public surfaces.
- **public engine repo**: `wangtao1025/portable-ai-assets`
  - Public sanitized engine/docs/tests/sample surface.
  - Public `v0.1.0` already exists and must remain immutable: do not move v0.1.0.
  - Public `v0.1.1` already exists and must remain immutable: do not move v0.1.1.
  - Public `v0.1.2` already exists and must remain immutable: do not move v0.1.2.
  - Public `v0.1.3` already exists and must remain immutable: do not move v0.1.3.
  - Future public release planning must use a new tag such as `v0.1.4`.

## Minimal new-machine restore path

1. Clone the private canonical assets repo into the intended local asset root:

   ```bash
   git clone https://github.com/wangtao1025/ai-assets-private.git ~/AI-Assets
   cd ~/AI-Assets
   ```

2. Confirm the private checkout is private-root content and not the public engine repo:

   ```bash
   git remote -v
   git status --short --branch
   git rev-parse HEAD
   ```

   Expected remote shape:

   ```text
   origin  https://github.com/wangtao1025/ai-assets-private.git
   ```

3. Set or verify the local configuration pointer. The important invariant is that `asset_root` points to the private canonical assets checkout, not to a public staging directory:

   ```yaml
   engine_root: ~/portable-ai-assets-engine
   asset_root: ~/AI-Assets
   asset_repo_remote: https://github.com/wangtao1025/ai-assets-private.git
   default_sync_mode: review-before-commit
   allow_auto_commit: false
   ```

4. If a separate public engine checkout is needed, clone the public engine repo separately:

   ```bash
   git clone https://github.com/wangtao1025/portable-ai-assets.git ~/portable-ai-assets-engine
   ```

5. Run a restore smoke test from the private root checkout. On a fresh clone or temporary clone, pass both `--engine-root "$PWD"` and `--asset-root "$PWD"` explicitly so local machine config does not redirect engine or asset reports back to an older checkout:

   ```bash
   ./bootstrap/setup/bootstrap-ai-assets.sh --show-config --engine-root "$PWD" --asset-root "$PWD"
   python3 -m py_compile bootstrap/setup/bootstrap_ai_assets.py bootstrap/setup/portable_ai_assets_paths.py
   python3 -m unittest discover -s tests -p test_bootstrap_phase4.py -k restore_readiness_smoke_plan_documents_private_public_recovery_path
   ./bootstrap/setup/bootstrap-ai-assets.sh --engine-root "$PWD" --asset-root "$PWD" --restore-smoke-check --both
   ./bootstrap/setup/bootstrap-ai-assets.sh --engine-root "$PWD" --asset-root "$PWD" --completed-work-review --both
   ```

   A fresh clone may report blocked for `completed-work-review` until you regenerate prerequisite reports such as public safety, release readiness, capability governance, and late-stage completion evidence. The `--restore-smoke-check --both` diagnostic should remain non-mutating and may report `ready-with-prerequisite-regeneration-needed` until those ignored runtime reports exist. That is expected because `bootstrap/reports/latest-*` runtime reports are intentionally ignored and are not part of the private Git history. Treat this as a signal to regenerate prerequisite reports, not as a failed clone.

6. Regenerate prerequisite reports when you need a fully aligned completed-work review:

   ```bash
   ./bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both --engine-root "$PWD" --asset-root "$PWD"
   ./bootstrap/setup/bootstrap-ai-assets.sh --release-readiness --both --engine-root "$PWD" --asset-root "$PWD"
   ./bootstrap/setup/bootstrap-ai-assets.sh --completed-work-review --both --engine-root "$PWD" --asset-root "$PWD"
   ```

7. Confirm public/private boundaries before any publication work. Restore is not release work; do not create, move, or delete public release tags while running restore smoke diagnostics:

   ```bash
   git ls-remote --heads --tags https://github.com/wangtao1025/portable-ai-assets.git main 'refs/tags/v0.1.0' 'refs/tags/v0.1.1' 'refs/tags/v0.1.2' 'refs/tags/v0.1.3'
   ```

   Expected immutable tag boundary and live-main check:

   ```text
   main    <live SHA from git ls-remote; public main can advance after this document is committed>
   v0.1.0  724e3c1dd1b5bca9bc90f196bde5837c5e6f2bbc
   v0.1.1  6f06d98b85e18d629175705c19436a4df199c876 (peeled commit; GitHub ref may be an annotated tag object)
   v0.1.2  dd7993c5c074a012fedd34f7957672e172041a65
   v0.1.3  9d67382cdefeddcbbefa3eacc943aabda12a36f1
   ```

   Rerun this command for live public `main`; do not treat this committed document as live GitHub state. The existing release tag SHAs above are immutable boundary checks, while public `main` may legitimately move forward with later guidance-only syncs.

## Restore smoke test checklist

- [ ] `engine_root` and `asset_root` both point to the private canonical assets repo when running fresh-clone smoke diagnostics.
- [ ] The private remote is `wangtao1025/ai-assets-private` and remains private.
- [ ] The public engine repo remains a separate checkout or remote reference.
- [ ] `bootstrap/setup/bootstrap-ai-assets.sh --engine-root "$PWD" --asset-root "$PWD" --restore-smoke-check --both` exits 0 without mutating repositories; a fresh clone may report `ready-with-prerequisite-regeneration-needed` until prerequisite reports are regenerated.
- [ ] `bootstrap/setup/bootstrap-ai-assets.sh --engine-root "$PWD" --asset-root "$PWD" --completed-work-review --both` exits 0 after prerequisite reports are regenerated; a fresh clone may report blocked until you regenerate prerequisite reports.
- [ ] `python3 -m unittest discover -s tests -p test_bootstrap_phase4.py` exits 0.
- [ ] Public `v0.1.0` is not moved.
- [ ] Public `v0.1.1` is not moved.
- [ ] Public `v0.1.2` is not moved.
- [ ] Public `v0.1.3` is not moved.
- [ ] Public release planning, if needed, uses `v0.1.4` or another new tag; restore is not release work.

## Non-goals

- Do not publish private root contents to the public engine repo.
- Do not create public releases during restore; restore is not release work.
- Do not move public `v0.1.0`, `v0.1.1`, `v0.1.2`, or `v0.1.3`, and do not create `v0.1.4` from a restore smoke run.
- Do not upload artifacts or invite reviewers/collaborators during restore smoke testing.
- Do not treat committed public `bootstrap/reports/latest-*` snapshots as live GitHub state; rerun local report-only gates for current status.
