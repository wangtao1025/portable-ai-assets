# Contributing

Thanks for your interest in Portable AI Assets System.

## Contribution priorities

High-value contributions include:
- new manifest/schema coverage
- safer inspect/plan/apply behavior
- adapter discovery improvements
- drift-aware diff and merge heuristics
- public-safe sample assets
- docs that clarify release boundaries and safety rules
- tests for new bootstrap/report behavior

---

## Ground rules

### 1. Safety before convenience
Do not submit changes that make high-risk runtime writes more aggressive without clear guardrails.

### 2. Discovery before overwrite
Changes should prefer inspect/report/diff flows over blind mutation.

### 3. Public-safe examples only
Do not commit:
- private memory
- secrets
- auth files
- personal machine paths unless clearly redacted/example-only
- real session archives from a private environment

### 4. Keep schemas lightweight and useful
Schema hardening is good; overcomplicated validation that blocks practical use is not.

---

## Recommended workflow

1. Make the smallest coherent change.
2. Add or update tests when behavior changes.
3. Run the relevant checks.
4. Describe safety implications in the PR.

Typical local checks:

```bash
python3 -m unittest tests/test_bootstrap_phase4.py
python3 -m py_compile bootstrap/setup/bootstrap_ai_assets.py
./bootstrap/setup/bootstrap-ai-assets.sh --validate-schemas --both
```

---

## PR checklist

Before opening a PR, verify:
- docs match behavior
- new manifests validate
- sample assets remain public-safe
- reports do not contain private user data
- new automation preserves backup-before-write and review-aware behavior

---

## Design bar

A good contribution should make at least one of these better:
- portability
- safety
- inspectability
- reviewability
- reproducibility

If a change makes the system more powerful but less legible or less safe, it probably needs a narrower scope.
