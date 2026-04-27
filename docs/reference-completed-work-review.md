# Reference: Completed Work Review

## What this gate does well

It turns a post-phase product/engineering review into a repeatable report. The report connects roadmap alignment, release-readiness correctness, public-safety status, external learning, and capability-governance boundaries in one checkpoint.

## What Portable AI Assets should adopt

- Review completed work before advancing to the next candidate.
- Keep the review report-only and based on existing docs/latest reports.
- Preserve explicit evidence for `executes_anything: false` where capability policy is involved.
- Keep external-reference backlog/inventory visible so design decisions continue to borrow mature patterns rather than evolve in isolation.

## What to avoid

- Do not make the review gate execute hooks/actions/code.
- Do not start runtimes, MCP servers, hosted providers, or admin workflows.
- Do not authenticate, bind credentials, or validate real tokens.
- Do not write runtime state, provider settings, or capability baselines.

## Safe integration boundary

The command may read public docs and latest local report JSON. It may emit only its own `latest-completed-work-review` report files. Any apply behavior remains outside this gate and must stay behind a separate human-reviewed apply path.

## Raw/runtime data boundary

Raw memory, private paths, provider credentials, webhook URLs, tenant IDs, token values, execution traces, and runtime caches must stay outside public docs and sample reports.
