<!-- Public snapshot notice: this is a static sanitized snapshot copied into a public artifact; it is not live GitHub state. Regenerate local report-only gates for current status. -->

# AI-Assets Public Repo Staging History Preflight

Generated: 2026-04-28T09:52:22
Staging dir: `/Users/example/AI-Assets/dist/github-staging/portable-ai-assets`

## Summary

- status: `needs-history-reattach`
- checks: `8`
- pass: `5`
- warn: `1`
- fail: `2`
- executes_anything: `False`
- remote_configured: `False`
- forbidden_findings: `0`
- head_rev: `None`
- v010_rev: `None`
- v010_behind_head: `False`
- checklist_declares_existing_v010: `True`

## Checks

- **pass** `staging-dir-exists`: /Users/example/AI-Assets/dist/github-staging/portable-ai-assets
- **pass** `staging-git-initialized`: True
- **pass** `staging-remote-empty`: False
- **pass** `staging-forbidden-clean`: forbidden_findings=0
- **pass** `checklist-declares-existing-v010`: Existing release tag: v0.1.0
- **fail** `staging-head-exists`: missing HEAD
- **fail** `v010-tag-exists`: missing v0.1.0^{commit}
- **warn** `existing-tag-context-without-history`: checklist says v0.1.0 exists, but generated staging lacks HEAD and/or v0.1.0 tag history

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
- Do not move v0.1.0; if a follow-up release is approved later, use a new tag such as v0.1.1.
- This report is local/read-only: it never fetches, creates remotes, commits, tags, pushes, uploads, or releases anything.
