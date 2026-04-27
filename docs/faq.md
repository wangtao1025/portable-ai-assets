# FAQ

## Is this another agent framework?
No.

Portable AI Assets System is a portability and ownership layer for long-lived AI assets. It sits above runtimes rather than replacing them.

## Is this a memory backend?
No.

Memory is one asset class inside the system, but the project also manages adapters, workflows, tool bindings, bootstrap logic, and migration/review flows.

## Why not just use one platform's built-in memory?
Because built-in memory is usually incomplete, platform-bound, and hard to migrate safely across clients and machines.

## Does it promise lossless migration across all runtimes?
No.

The system explicitly supports lossy adapters and review-aware reconciliation where exact cross-runtime portability is impossible.

## Why is there both Git and non-Git storage?
Because canonical text assets are well-suited to Git, while session archives, caches, histories, and DB files are not.

## Why is review/apply separated?
Because already-used machines drift over time. Safe portability requires inspect → diff → review → apply rather than blind overwrite.

## Can I open-source my setup directly?
Usually not safely.

Open-source the engine/framework layer first. Keep private memory, summaries, runtime-local artifacts, and secrets out of the public repository unless explicitly redacted.

## Who is this for?
Primarily:
- AI-native power users
- indie hackers
- local-first developers
- small AI teams
- multi-agent experimenters
