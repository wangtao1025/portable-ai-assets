#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATH_HELPER="${SCRIPT_DIR}/portable_ai_assets_paths.py"
CONFIG_PATH=""
ASSET_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG_PATH="$2"
      shift 2
      ;;
    --asset-root)
      ASSET_ROOT="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--config PATH] [--asset-root PATH]" >&2
      exit 1
      ;;
  esac
done

HELPER_ARGS=()
if [[ -n "${CONFIG_PATH}" ]]; then
  HELPER_ARGS+=(--config "${CONFIG_PATH}")
fi
if [[ -n "${ASSET_ROOT}" ]]; then
  HELPER_ARGS+=(--asset-root "${ASSET_ROOT}")
fi

if [[ -f "${PATH_HELPER}" ]]; then
  eval "$(python3 "${PATH_HELPER}" --shell-exports ${HELPER_ARGS+"${HELPER_ARGS[@]}"})"
fi

"${SCRIPT_DIR}/export-canonical-profile.sh"
echo
"${SCRIPT_DIR}/refresh-canonical-memory.sh"
echo

echo "Refresh complete. Review diffs under ${PAA_ASSET_ROOT:-${HOME}/AI-Assets}/memory/ and commit only durable canonical changes."
