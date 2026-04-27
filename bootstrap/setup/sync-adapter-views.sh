#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${HOME:?HOME environment variable is required}"
ASSETS_DIR="${HOME_DIR}/AI-Assets"
BACKUP_DIR="${HOME_DIR}/AI-Assets/bootstrap/backups/adapter-sync-$(date +%Y%m%d-%H%M%S)"

mkdir -p "${BACKUP_DIR}"

sync_if_present() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$src" ]]; then
    echo "missing source: $src"
    return
  fi
  if [[ -f "$dst" ]]; then
    mkdir -p "${BACKUP_DIR}/$(dirname "${dst#${HOME_DIR}/}")"
    cp "$dst" "${BACKUP_DIR}/${dst#${HOME_DIR}/}"
    echo "backed up: $dst"
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "synced: $src -> $dst"
}

sync_if_present "${ASSETS_DIR}/adapters/hermes/USER.md"   "${HOME_DIR}/.hermes/memories/USER.md"
sync_if_present "${ASSETS_DIR}/adapters/hermes/MEMORY.md" "${HOME_DIR}/.hermes/memories/MEMORY.md"

echo
sync_if_present "${ASSETS_DIR}/adapters/claude/CLAUDE.md" "${HOME_DIR}/.claude/CLAUDE.md"

echo
sync_if_present "${ASSETS_DIR}/adapters/codex/AGENTS.md"  "${HOME_DIR}/.codex/AGENTS.md"

echo
 echo "Backups stored under: ${BACKUP_DIR}"
 echo "Review runtime behavior after sync because Claude/Codex instruction files affect live agent behavior."
