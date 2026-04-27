# Schemas

This directory contains the first public-safe schema artifacts for Portable AI Assets System.

Current scope:
- `stack-manifest-v1.json`
- `tool-manifest-v1.json`
- `bridge-manifest-v1.json`
- `architecture-note-v1.json`
- `adapter-contract-v1.json`
- `portable-skill-manifest-v1.json`

Purpose:
- make manifest classes explicit
- support validation in bootstrap
- separate canonical/public-safe metadata from private runtime state

These schemas are intentionally shallow in v1. They currently enforce top-level required fields and a few controlled enums. Deeper semantic validation can evolve later without blocking early open-source packaging.
