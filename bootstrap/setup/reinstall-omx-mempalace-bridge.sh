#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${HOME:?HOME environment variable is required}"
PYTHON_BIN="${HOME_DIR}/.venvs/mempalace/bin/python"
INSTALLER="${HOME_DIR}/.codex/hooks/omx-mempalace/install.py"
HOOKS_JSON="${HOME_DIR}/.codex/hooks.json"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing MemPalace python: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -f "${INSTALLER}" ]]; then
  echo "Missing bridge installer: ${INSTALLER}" >&2
  exit 1
fi

echo "Reinstalling OMX ↔ MemPalace bridge..."
"${PYTHON_BIN}" "${INSTALLER}"

echo
echo "Bridge reinstall finished. Check hooks file: ${HOOKS_JSON}"
