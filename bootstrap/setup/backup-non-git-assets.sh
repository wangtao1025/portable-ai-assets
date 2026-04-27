#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${HOME:?HOME environment variable is required}"
BACKUP_ROOT="${HOME_DIR}/AI-Assets/non-git-backups"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${BACKUP_ROOT}/${STAMP}"
mkdir -p "${DEST}"

copy_path() {
  local src="$1"
  local rel="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "${DEST}/$(dirname "$rel")"
    cp -R "$src" "${DEST}/${rel}"
    echo "backed up: $src -> ${DEST}/${rel}"
  else
    echo "missing: $src"
  fi
}

copy_path "${HOME_DIR}/.hermes/state.db" "hermes/state.db"
copy_path "${HOME_DIR}/.hermes/sessions" "hermes/sessions"
copy_path "${HOME_DIR}/.claude/history.jsonl" "claude/history.jsonl"
copy_path "${HOME_DIR}/.claude/projects" "claude/projects"
copy_path "${HOME_DIR}/.codex/history.jsonl" "codex/history.jsonl"
copy_path "${HOME_DIR}/.codex/sessions" "codex/sessions"
copy_path "${HOME_DIR}/.mempalace-auto/bridge/corpus-live" "mempalace/corpus-live"

echo
echo "Backup directory created: ${DEST}"
echo "This is a plain local copy. Move or sync it to encrypted external/cloud storage if desired."
