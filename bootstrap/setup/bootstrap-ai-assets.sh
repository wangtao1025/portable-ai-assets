#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/bootstrap_ai_assets.py"
PATH_HELPER="${SCRIPT_DIR}/portable_ai_assets_paths.py"

MODE="inspect"
OUTPUT_FORMAT="both"
CONFIG_PATH=""
ASSET_ROOT=""
ASSET_REPO_REMOTE=""
SHOW_CONFIG="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --inspect)
      MODE="inspect"
      shift
      ;;
    --plan)
      MODE="plan"
      shift
      ;;
    --apply)
      MODE="apply"
      shift
      ;;
    --diff)
      MODE="diff"
      shift
      ;;
    --merge-apply)
      MODE="merge-apply"
      shift
      ;;
    --merge-candidates)
      MODE="merge-candidates"
      shift
      ;;
    --review-apply)
      MODE="review-apply"
      shift
      ;;
    --validate-schemas)
      MODE="validate-schemas"
      shift
      ;;
    --connectors)
      MODE="connectors"
      shift
      ;;
    --skills-inventory)
      MODE="skills-inventory"
      shift
      ;;
    --skill-projection-preview)
      MODE="skill-projection-preview"
      shift
      ;;
    --skill-projection-candidates)
      MODE="skill-projection-candidates"
      shift
      ;;
    --skill-projection-status)
      MODE="skill-projection-status"
      shift
      ;;
    --skill-projection-review-apply)
      MODE="skill-projection-review-apply"
      shift
      ;;
    --public-safety-scan)
      MODE="public-safety-scan"
      shift
      ;;
    --release-readiness)
      MODE="release-readiness"
      shift
      ;;
    --public-release-pack)
      MODE="public-release-pack"
      shift
      ;;
    --public-release-archive)
      MODE="public-release-archive"
      shift
      ;;
    --public-release-smoke-test)
      MODE="public-release-smoke-test"
      shift
      ;;
    --github-publish-check)
      MODE="github-publish-check"
      shift
      ;;
    --public-repo-staging)
      MODE="public-repo-staging"
      shift
      ;;
    --public-repo-staging-status)
      MODE="public-repo-staging-status"
      shift
      ;;
    --public-repo-staging-history-preflight)
      MODE="public-repo-staging-history-preflight"
      shift
      ;;
    --manual-publication-decision-packet)
      MODE="manual-publication-decision-packet"
      shift
      ;;
    --github-publish-dry-run)
      MODE="github-publish-dry-run"
      shift
      ;;
    --github-handoff-pack)
      MODE="github-handoff-pack"
      shift
      ;;
    --github-final-preflight)
      MODE="github-final-preflight"
      shift
      ;;
    --release-provenance)
      MODE="release-provenance"
      shift
      ;;
    --verify-release-provenance)
      MODE="verify-release-provenance"
      shift
      ;;
    --release-closure)
      MODE="release-closure"
      shift
      ;;
    --public-package-freshness-review)
      MODE="public-package-freshness-review"
      shift
      ;;
    --public-docs-external-reader-review)
      MODE="public-docs-external-reader-review"
      shift
      ;;
    --release-candidate-closure-review)
      MODE="release-candidate-closure-review"
      shift
      ;;
    --release-reviewer-packet-index)
      MODE="release-reviewer-packet-index"
      shift
      ;;
    --release-reviewer-decision-log)
      MODE="release-reviewer-decision-log"
      shift
      ;;
    --external-reviewer-quickstart)
      MODE="external-reviewer-quickstart"
      shift
      ;;
    --external-reviewer-feedback-plan)
      MODE="external-reviewer-feedback-plan"
      shift
      ;;
    --external-reviewer-feedback-status)
      MODE="external-reviewer-feedback-status"
      shift
      ;;
    --external-reviewer-feedback-template)
      MODE="external-reviewer-feedback-template"
      shift
      ;;
    --external-reviewer-feedback-followup-index)
      MODE="external-reviewer-feedback-followup-index"
      shift
      ;;
    --external-reviewer-feedback-followup-candidates)
      MODE="external-reviewer-feedback-followup-candidates"
      shift
      ;;
    --external-reviewer-feedback-followup-candidate-status)
      MODE="external-reviewer-feedback-followup-candidate-status"
      shift
      ;;
    --initial-completion-review)
      MODE="initial-completion-review"
      shift
      ;;
    --human-action-closure-checklist)
      MODE="human-action-closure-checklist"
      shift
      ;;
    --manual-reviewer-execution-packet)
      MODE="manual-reviewer-execution-packet"
      shift
      ;;
    --manual-reviewer-public-surface-freshness)
      MODE="manual-reviewer-public-surface-freshness"
      shift
      ;;
    --manual-reviewer-handoff-readiness)
      MODE="manual-reviewer-handoff-readiness"
      shift
      ;;
    --manual-reviewer-handoff-packet-index)
      MODE="manual-reviewer-handoff-packet-index"
      shift
      ;;
    --manual-reviewer-handoff-freeze-check)
      MODE="manual-reviewer-handoff-freeze-check"
      shift
      ;;
    --agent-owner-delegation-review)
      MODE="agent-owner-delegation-review"
      shift
      ;;
    --agent-complete-external-actions-reserved)
      MODE="agent-complete-external-actions-reserved"
      shift
      ;;
    --agent-complete-failclosed-hardening-review)
      MODE="agent-complete-failclosed-hardening-review"
      shift
      ;;
    --agent-complete-regression-evidence-integrity)
      MODE="agent-complete-regression-evidence-integrity"
      shift
      ;;
    --agent-complete-syntax-invalid-evidence-failclosed-review)
      MODE="agent-complete-syntax-invalid-evidence-failclosed-review"
      shift
      ;;
    --agent-complete-phase102-rollup-evidence-failclosed-review)
      MODE="agent-complete-phase102-rollup-evidence-failclosed-review"
      shift
      ;;
    --manual-release-reviewer-checklist)
      MODE="manual-release-reviewer-checklist"
      shift
      ;;
    --external-reference-inventory)
      MODE="external-reference-inventory"
      shift
      ;;
    --external-reference-backlog)
      MODE="external-reference-backlog"
      shift
      ;;
    --team-pack-preview)
      MODE="team-pack-preview"
      shift
      ;;
    --project-pack-preview)
      MODE="project-pack-preview"
      shift
      ;;
    --capability-risk-inventory)
      MODE="capability-risk-inventory"
      shift
      ;;
    --capability-policy-preview)
      MODE="capability-policy-preview"
      shift
      ;;
    --capability-policy-candidate-generation)
      MODE="capability-policy-candidate-generation"
      shift
      ;;
    --capability-policy-candidate-status)
      MODE="capability-policy-candidate-status"
      shift
      ;;
    --capability-policy-baseline-apply)
      MODE="capability-policy-baseline-apply"
      shift
      ;;
    --completed-work-review)
      MODE="completed-work-review"
      shift
      ;;
    --connector-preview)
      MODE="connector-preview"
      shift
      ;;
    --redacted-examples)
      MODE="redacted-examples"
      shift
      ;;
    --demo-story)
      MODE="demo-story"
      shift
      ;;
    --public-demo-pack)
      MODE="public-demo-pack"
      shift
      ;;
    --refresh-canonical-assets)
      MODE="refresh-canonical-assets"
      shift
      ;;
    --private-assets-status)
      MODE="private-assets-status"
      shift
      ;;
    --memos-health)
      MODE="memos-health"
      shift
      ;;
    --memos-import-preview)
      MODE="memos-import-preview"
      shift
      ;;
    --memos-skill-candidates)
      MODE="memos-skill-candidates"
      shift
      ;;
    --skill-candidates-status)
      MODE="skill-candidates-status"
      shift
      ;;
    --skill-review-apply)
      MODE="skill-review-apply"
      shift
      ;;
    --init-private-assets)
      MODE="init-private-assets"
      ASSET_ROOT="$2"
      shift 2
      ;;
    --json)
      OUTPUT_FORMAT="json"
      shift
      ;;
    --markdown)
      OUTPUT_FORMAT="markdown"
      shift
      ;;
    --both)
      OUTPUT_FORMAT="both"
      shift
      ;;
    --config)
      CONFIG_PATH="$2"
      shift 2
      ;;
    --asset-root)
      ASSET_ROOT="$2"
      shift 2
      ;;
    --asset-repo-remote)
      ASSET_REPO_REMOTE="$2"
      shift 2
      ;;
    --show-config)
      SHOW_CONFIG="true"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--inspect|--plan|--apply|--diff|--merge-apply|--merge-candidates|--review-apply|--validate-schemas|--connectors|--skills-inventory|--skill-projection-preview|--skill-projection-candidates|--skill-projection-status|--skill-projection-review-apply|--public-safety-scan|--release-readiness|--public-release-pack|--public-release-archive|--public-release-smoke-test|--github-publish-check|--public-repo-staging|--public-repo-staging-status|--public-repo-staging-history-preflight|--manual-publication-decision-packet|--github-publish-dry-run|--github-handoff-pack|--github-final-preflight|--release-provenance|--verify-release-provenance|--release-closure|--public-package-freshness-review|--public-docs-external-reader-review|--release-candidate-closure-review|--release-reviewer-packet-index|--release-reviewer-decision-log|--external-reviewer-quickstart|--external-reviewer-feedback-plan|--external-reviewer-feedback-status|--external-reviewer-feedback-template|--external-reviewer-feedback-followup-index|--external-reviewer-feedback-followup-candidates|--external-reviewer-feedback-followup-candidate-status|--initial-completion-review|--human-action-closure-checklist|--manual-reviewer-execution-packet|--manual-reviewer-public-surface-freshness|--manual-reviewer-handoff-readiness|--manual-reviewer-handoff-packet-index|--manual-reviewer-handoff-freeze-check|--agent-owner-delegation-review|--agent-complete-external-actions-reserved|--agent-complete-failclosed-hardening-review|--agent-complete-regression-evidence-integrity|--agent-complete-syntax-invalid-evidence-failclosed-review|--agent-complete-phase102-rollup-evidence-failclosed-review|--manual-release-reviewer-checklist|--external-reference-inventory|--external-reference-backlog|--team-pack-preview|--project-pack-preview|--capability-risk-inventory|--capability-policy-preview|--capability-policy-candidate-generation|--capability-policy-candidate-status|--capability-policy-baseline-apply|--connector-preview|--redacted-examples|--demo-story|--public-demo-pack|--refresh-canonical-assets|--private-assets-status|--memos-health|--memos-import-preview|--memos-skill-candidates|--skill-candidates-status|--skill-review-apply|--init-private-assets PATH] [--json|--markdown|--both] [--config PATH] [--asset-root PATH] [--asset-repo-remote URL] [--show-config]" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${PYTHON_SCRIPT}" ]]; then
  echo "Missing bootstrap inspector: ${PYTHON_SCRIPT}" >&2
  exit 1
fi

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

if [[ "${SHOW_CONFIG}" == "true" ]]; then
  if [[ -f "${PATH_HELPER}" ]]; then
    python3 "${PATH_HELPER}" ${HELPER_ARGS+"${HELPER_ARGS[@]}"}
  else
    printf '{"engine_root": %q, "asset_root": %q}
' "${SCRIPT_DIR}/../.." "${HOME}/AI-Assets"
  fi
  exit 0
fi

PY_ARGS=(--mode "${MODE}" --output-format "${OUTPUT_FORMAT}")
if [[ -n "${CONFIG_PATH}" ]]; then
  PY_ARGS+=(--config "${CONFIG_PATH}")
fi
if [[ -n "${ASSET_ROOT}" ]]; then
  PY_ARGS+=(--asset-root "${ASSET_ROOT}")
fi
if [[ -n "${ASSET_REPO_REMOTE}" ]]; then
  PY_ARGS+=(--asset-repo-remote "${ASSET_REPO_REMOTE}")
fi

python3 "${PYTHON_SCRIPT}" "${PY_ARGS[@]}"
