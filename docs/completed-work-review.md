# Completed Work Review Gate

`--completed-work-review` is a report-only post-phase review gate. It checks whether the just-completed work still looks reasonable, correct, roadmap-aligned, faithful to the Portable AI Assets vision, and informed by external references instead of closed-door invention.

```bash
./bootstrap/setup/bootstrap-ai-assets.sh --completed-work-review --both
```

The report reads existing docs and latest reports only. It does not execute hooks/actions/code, start MCP servers, call providers, authenticate, validate credentials, update baselines, or mutate runtime/admin/provider state.

## Review axes

1. **Safety / correctness** — release readiness, public safety, and non-execution evidence remain green.
2. **Vision / roadmap alignment** — work remains anchored in portability, canonical ownership, safe migration, and reviewable reconciliation.
3. **External learning** — external-reference backlog/inventory are present so new capabilities keep learning from mature adjacent systems.
4. **Capability governance boundary** — policy preview/apply gates remain report-only or reviewed-only.

The expected output is `bootstrap/reports/latest-completed-work-review.json/md`. A warning or failure should be resolved before the next implementation phase.
