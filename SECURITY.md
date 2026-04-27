# Security Policy

Portable AI Assets separates public engine assets from private memory and runtime state.

## Supported versions

The current prototype branch receives security fixes on a best-effort basis until formal versioning begins.

## Reporting a vulnerability

Please open a private security advisory or contact the maintainers privately. Do not publish secrets, private memory, runtime databases, logs, or machine-local config in public issues.

## Sensitive data policy

- Replace secrets with `[REDACTED]`.
- Do not commit raw runtime DBs, logs, histories, session traces, or backups.
- Use `--public-safety-scan`, `--release-readiness`, and `--public-release-smoke-test` before publishing artifacts.
