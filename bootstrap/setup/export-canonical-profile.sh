#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATH_HELPER="${SCRIPT_DIR}/portable_ai_assets_paths.py"

if [[ -f "${PATH_HELPER}" ]]; then
  eval "$(python3 "${PATH_HELPER}" --shell-exports)"
fi

HOME_DIR="${HOME:-$(python3 -c 'from pathlib import Path; print(Path.home())')}"
MEM_SRC_DIR="${HOME_DIR}/.mempalace-auto/bridge/global"
MEM_DST_DIR="${PAA_ASSET_ROOT:-${HOME_DIR}/AI-Assets}/memory/profile"

mkdir -p "${MEM_DST_DIR}"

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [[ -f "$src" ]]; then
    cp "$src" "$dst"
    echo "copied: $src -> $dst"
  else
    echo "missing: $src"
  fi
}

copy_if_exists "${MEM_SRC_DIR}/user-profile.md" "${MEM_DST_DIR}/mempalace-user-profile.md"
copy_if_exists "${MEM_SRC_DIR}/preferences.md" "${MEM_DST_DIR}/mempalace-preferences.md"

if [[ -f "${HOME_DIR}/.hermes/memories/USER.md" ]]; then
  cp "${HOME_DIR}/.hermes/memories/USER.md" "${MEM_DST_DIR}/hermes-user-memory.md"
  echo "copied: Hermes USER.md"
fi

echo "Done. Review canonical profile files under ${MEM_DST_DIR}"
