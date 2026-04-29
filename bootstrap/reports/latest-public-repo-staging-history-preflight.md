<!-- Public snapshot notice: this is a static sanitized snapshot copied into a public artifact; it is not live GitHub state. Regenerate local report-only gates for current status. -->

# AI-Assets Public Repo Staging History Preflight

Generated: 2026-04-29T14:18:18
Staging dir: `/Users/example/AI-Assets/dist/github-staging/portable-ai-assets`

## Summary

- status: `ready`
- checks: `10`
- pass: `10`
- warn: `0`
- fail: `0`
- executes_anything: `False`
- remote_configured: `False`
- forbidden_findings: `0`
- head_rev: `217e714931c9b467a66ed19804aeea8f95c53e67`
- v010_rev: `724e3c1dd1b5bca9bc90f196bde5837c5e6f2bbc`
- v011_rev: `6f06d98b85e18d629175705c19436a4df199c876`
- v012_rev: `dd7993c5c074a012fedd34f7957672e172041a65`
- v010_behind_head: `True`
- checklist_declares_existing_v010: `True`

## Checks

- **pass** `staging-dir-exists`: /Users/example/AI-Assets/dist/github-staging/portable-ai-assets
- **pass** `staging-git-initialized`: True
- **pass** `staging-remote-empty`: False
- **pass** `staging-forbidden-clean`: forbidden_findings=0
- **pass** `checklist-declares-existing-v010`: Existing release tag: v0.1.0
- **pass** `staging-head-exists`: 217e714931c9b467a66ed19804aeea8f95c53e67
- **pass** `v010-tag-exists`: 724e3c1dd1b5bca9bc90f196bde5837c5e6f2bbc
- **pass** `v011-tag-exists`: 6f06d98b85e18d629175705c19436a4df199c876
- **pass** `v012-tag-exists`: dd7993c5c074a012fedd34f7957672e172041a65
- **pass** `v010-behind-head`: v0.1.0=724e3c1dd1b5bca9bc90f196bde5837c5e6f2bbc; HEAD=217e714931c9b467a66ed19804aeea8f95c53e67

## Manual history context steps — not executed

### review-staging-status

```bash
git status --short
```

### review-current-history

```bash
git log --oneline --decorate -5
```

### review-v010-tag

```bash
git rev-parse --verify v0.1.0^{commit}
```

### reattach-public-history-if-approved

```bash
Reattach public main/v0.1.0 history only after explicit owner approval; do not move v0.1.0.
```

## Recommendations

- Treat needs-history-reattach as expected for freshly generated staging; reattach public history before any manual publication.
- Do not move v0.1.0. Do not move v0.1.1. Do not move v0.1.2; if a follow-up release is approved later, use a new tag such as v0.1.3.
- This report is local/read-only: it never fetches, creates remotes, commits, tags, pushes, uploads, or releases anything.
