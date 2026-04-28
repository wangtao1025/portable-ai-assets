#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple



def _strip_yaml_comment(value: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == '#' and not in_single and not in_double:
            return value[:index].rstrip()
    return value.rstrip()


def _parse_yaml_scalar(value: str) -> Any:
    value = _strip_yaml_comment(value).strip()
    if value == "":
        return ""
    if value in ("null", "Null", "NULL", "~"):
        return None
    if value in ("true", "True", "TRUE"):
        return True
    if value in ("false", "False", "FALSE"):
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_yaml_scalar(part.strip()) for part in inner.split(",")]
    try:
        if re.match(r"^-?\d+$", value):
            return int(value)
        if re.match(r"^-?\d+\.\d+$", value):
            return float(value)
    except Exception:
        pass
    return value


def simple_yaml_load(text: str) -> Any:
    raw_lines = text.splitlines()
    lines = []
    for raw in raw_lines:
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        indent = len(raw) - len(raw.lstrip(' '))
        lines.append((indent, raw.strip()))
    if not lines:
        return None
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(-1, root)]
    for idx, (indent, content) in enumerate(lines):
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if content.startswith('- '):
            value_text = content[2:].strip()
            if not isinstance(parent, list):
                continue
            if ':' in value_text and not value_text.startswith(('"', "'")):
                key, value = value_text.split(':', 1)
                item: Dict[str, Any] = {key.strip(): _parse_yaml_scalar(value)}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(_parse_yaml_scalar(value_text))
            continue
        if ':' not in content:
            continue
        key, value = content.split(':', 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            next_is_list = False
            for next_indent, next_content in lines[idx + 1:]:
                if next_indent <= indent:
                    break
                next_is_list = next_content.startswith('- ')
                break
            container: Any = [] if next_is_list else {}
            if isinstance(parent, dict):
                parent[key] = container
            stack.append((indent, container))
        else:
            if isinstance(parent, dict):
                parent[key] = _parse_yaml_scalar(value)
    return root

HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from portable_ai_assets_paths import resolve_runtime_paths

ENGINE_ROOT = Path(__file__).resolve().parents[2]
CURRENT_RUNTIME_PATHS: Dict[str, Any] = {}
ASSETS = ENGINE_ROOT
REPORTS = ASSETS / "bootstrap" / "reports"
STATE = ASSETS / "bootstrap" / "state"
BACKUPS = ASSETS / "bootstrap" / "backups"
CANDIDATES = ASSETS / "bootstrap" / "candidates"
SCHEMAS = ENGINE_ROOT / "schemas"


def build_asset_class_rules(engine_root: Path, asset_root: Path) -> Dict[str, List[str]]:
    return {
        "public": [
            str(engine_root / "README.md"),
            str(engine_root / "stack"),
            str(engine_root / "adapters"),
            str(engine_root / "bootstrap" / "setup"),
            str(engine_root / "bootstrap" / "checks"),
            str(engine_root / "docs"),
            str(engine_root / "tests"),
            str(engine_root / "sample-assets"),
            str(engine_root / "examples"),
            "/AI-Assets/README.md",
            "/AI-Assets/stack/",
            "/AI-Assets/adapters/",
            "/AI-Assets/bootstrap/setup/",
            "/AI-Assets/bootstrap/checks/",
            "/AI-Assets/docs/",
            "/AI-Assets/tests/",
            "/AI-Assets/sample-assets/",
            "/AI-Assets/examples/",
        ],
        "private": [
            str(asset_root / "memory"),
            str(asset_root / "skills"),
            str(asset_root / "bootstrap" / "candidates"),
            str(asset_root / "bootstrap" / "reports"),
            str(asset_root / "non-git-backups"),
            "/AI-Assets/memory/",
            "/AI-Assets/skills/",
            "/AI-Assets/bootstrap/candidates/",
            "/AI-Assets/bootstrap/reports/",
            "/AI-Assets/non-git-backups/",
            "/.hermes/memories/",
            "/.claude/CLAUDE.md",
            "/.codex/AGENTS.md",
        ],
        "secret": [
            "/.codex/auth.json",
            "/.claude/settings.local.json",
            "/.claude/config.json",
            "/.hermes/config.yaml",
        ],
    }


def configure_runtime_paths(config_path: Optional[str] = None, asset_root_override: Optional[str] = None) -> Dict[str, Any]:
    global ENGINE_ROOT, ASSETS, REPORTS, STATE, BACKUPS, CANDIDATES, SCHEMAS, MANAGED_STATE_PATH, CURRENT_RUNTIME_PATHS, ASSET_CLASS_RULES
    CURRENT_RUNTIME_PATHS = resolve_runtime_paths(
        config_path=config_path,
        asset_root_override=asset_root_override,
        script_path=Path(__file__).resolve(),
    )
    ENGINE_ROOT = Path(CURRENT_RUNTIME_PATHS["engine_root"])
    ASSETS = Path(CURRENT_RUNTIME_PATHS["asset_root"])
    REPORTS = ASSETS / "bootstrap" / "reports"
    STATE = ASSETS / "bootstrap" / "state"
    BACKUPS = ASSETS / "bootstrap" / "backups"
    CANDIDATES = ASSETS / "bootstrap" / "candidates"
    SCHEMAS = ENGINE_ROOT / "schemas"
    REPORTS.mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    SCHEMAS.mkdir(parents=True, exist_ok=True)
    MANAGED_STATE_PATH = STATE / "managed-state.json"
    ASSET_CLASS_RULES = build_asset_class_rules(ENGINE_ROOT, ASSETS)
    return CURRENT_RUNTIME_PATHS


configure_runtime_paths()


SAFE_ACTIONS = {"safe-install-canonical", "refresh-canonical-memory", "preserve-and-validate", "no-op"}
REVIEW_ACTIONS = {"review-diff-before-sync", "backup-and-manual-review", "inspect-layout-manually"}
MANAGED_STATE_PATH = STATE / "managed-state.json"
SCHEMA_FILE_MAP = {
    "stack-manifest-v1": "stack-manifest-v1.json",
    "tool-manifest-v1": "tool-manifest-v1.json",
    "bridge-manifest-v1": "bridge-manifest-v1.json",
    "architecture-note-v1": "architecture-note-v1.json",
    "adapter-contract-v1": "adapter-contract-v1.json",
    "portable-skill-manifest-v1": "portable-skill-manifest-v1.json",
}
DEFAULT_SCHEMA_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "stack-manifest-v1": {
        "type": "object",
        "required": ["version", "updated_at", "owner", "root"],
        "enum": {
            "asset_class": ["public", "private", "secret", "unknown"],
        },
    },
    "tool-manifest-v1": {
        "type": "object",
        "required": ["name", "kind", "status", "home", "paths", "preserve_in_git", "backup_but_not_git", "rebuildable", "restore_notes"],
    },
    "bridge-manifest-v1": {
        "type": "object",
        "required": ["name", "kind", "status", "canonical_role", "source_paths", "runtime_paths", "preserve_in_git", "backup_but_not_git", "restore_notes"],
    },
    "architecture-note-v1": {
        "type": "object",
        "required": ["name", "kind", "status", "canonical_role", "recommended_model", "rules"],
    },
    "adapter-contract-v1": {
        "type": "object",
        "required": [
            "name",
            "adapter_version",
            "runtime",
            "description",
            "canonical_sources",
            "live_targets",
            "connector",
            "detection",
            "apply_policy",
        ],
        "properties": {
            "apply_policy": {"enum": ["safe-auto-apply", "human-review-required", "manual-only"]},
        },
    },
    "portable-skill-manifest-v1": {
        "type": "object",
        "required": [
            "name",
            "skill_version",
            "status",
            "description",
            "trigger",
            "procedure",
            "verification",
            "boundaries",
            "source_evidence",
            "adapter_projection",
        ],
        "properties": {
            "status": {"enum": ["draft", "probationary", "active", "retired"]},
            "confidence": {"enum": ["low", "medium", "high"]},
        },
    },
}



def sha256_text(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path, limit: int = 5000) -> str:
    if not path.is_file():
        return ""
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return data[:limit]



def read_full_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""



def load_managed_state(path: Path = MANAGED_STATE_PATH) -> Dict[str, object]:
    if not path.is_file():
        return {"targets": {}, "last_updated": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"targets": {}, "last_updated": None}
    if not isinstance(data, dict):
        return {"targets": {}, "last_updated": None}
    data.setdefault("targets", {})
    data.setdefault("last_updated", None)
    return data



def save_managed_state(data: Dict[str, object], path: Path = MANAGED_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = dt.datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")



def record_managed_target(
    target: str,
    live_path: Path,
    canonical_path: Path,
    live_hash: Optional[str],
    canonical_hash: Optional[str],
    path: Path = MANAGED_STATE_PATH,
) -> None:
    state = load_managed_state(path)
    state.setdefault("targets", {})[target] = {
        "recorded_at": dt.datetime.now().isoformat(timespec="seconds"),
        "live_path": str(live_path),
        "canonical_path": str(canonical_path),
        "live_hash": live_hash,
        "canonical_hash": canonical_hash,
    }
    save_managed_state(state, path)



def _normalize_text_block(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()



def _section_label(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return fallback



def safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip()).strip("-._")
    return slug or "candidate"



def classify_asset_path(path_str: str) -> Dict[str, str]:
    normalized = str(path_str)
    for asset_class in ("secret", "private", "public"):
        for needle in ASSET_CLASS_RULES[asset_class]:
            if needle in normalized:
                return {
                    "asset_class": asset_class,
                    "shareability": "do-not-publish" if asset_class in {"private", "secret"} else "public-safe",
                }
    return {"asset_class": "unknown", "shareability": "review-required"}



def build_target_schema_metadata(target: str, state: str, recommended_action: str) -> Dict[str, str]:
    portability = "lossy-adapter" if recommended_action in REVIEW_ACTIONS or state == "managed-but-drifted" else "canonical-or-safe"
    apply_policy = "human-review-required" if recommended_action in REVIEW_ACTIONS else "safe-auto-apply"
    return {
        "target": target,
        "portability": portability,
        "apply_policy": apply_policy,
        "adapter_state": state,
        "recommended_action": recommended_action,
    }



def detect_manifest_schema(path: Path) -> Optional[str]:
    normalized = str(path)
    if normalized.endswith("/stack/manifest.yaml"):
        return "stack-manifest-v1"
    if normalized.endswith("/stack/mcp/shared-memory-pattern.yaml"):
        return "architecture-note-v1"
    if "/stack/tools/" in normalized and normalized.endswith(".yaml"):
        return "tool-manifest-v1"
    if "/stack/mcp/" in normalized and normalized.endswith(".yaml"):
        return "bridge-manifest-v1"
    if normalized.endswith("/adapter.yaml") and "/sample-assets/adapters/" in normalized:
        return "adapter-contract-v1"
    if "/adapters/registry/" in normalized and normalized.endswith(".yaml"):
        return "adapter-contract-v1"
    if "/sample-assets/skills/" in normalized and normalized.endswith(".yaml"):
        return "portable-skill-manifest-v1"
    if "/skills/" in normalized and normalized.endswith(".yaml"):
        return "portable-skill-manifest-v1"
    return None



def _discover_manifest_paths(root: Path) -> List[Path]:
    manifest_paths: List[Path] = []
    for rel in ("stack", "adapters/registry", "sample-assets/adapters", "skills", "sample-assets/skills"):
        base = root / rel
        if base.is_dir():
            manifest_paths.extend(sorted(base.glob("**/*.yaml")))
    return manifest_paths



def load_adapter_contracts(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> List[Dict[str, Any]]:
    contracts: List[Dict[str, Any]] = []
    for manifest_path in _discover_manifest_paths(root):
        schema_name = detect_manifest_schema(manifest_path)
        if schema_name != "adapter-contract-v1":
            continue
        payload = load_yaml_data(manifest_path)
        validation = validate_manifest_payload(schema_name, payload, schema_dir=schema_dir)
        entry = {
            "path": str(manifest_path),
            "schema": schema_name,
            "valid": validation["valid"],
            "errors": validation["errors"],
            "payload": payload,
        }
        entry.update(classify_asset_path(str(manifest_path)))
        contracts.append(entry)
    contracts.sort(key=lambda item: (str(item["payload"].get("runtime", "")), str(item["payload"].get("name", "")), item["path"]))
    return contracts



def build_connector_report(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    adapters = load_adapter_contracts(root, schema_dir=schema_dir)
    valid_adapters = [entry for entry in adapters if entry["valid"]]
    runtimes = sorted({str(entry["payload"].get("runtime", "unknown")) for entry in valid_adapters})
    import_connectors = sorted({str(entry["payload"].get("connector", {}).get("import", "unknown")) for entry in valid_adapters})
    export_connectors = sorted({str(entry["payload"].get("connector", {}).get("export", "unknown")) for entry in valid_adapters})
    return {
        "mode": "connectors",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "schema_dir": str(schema_dir),
        "summary": {
            "total_adapters": len(adapters),
            "valid_adapters": len(valid_adapters),
            "invalid_adapters": sum(1 for entry in adapters if not entry["valid"]),
            "runtimes": runtimes,
            "import_connectors": import_connectors,
            "export_connectors": export_connectors,
        },
        "adapters": [
            {
                "name": entry["payload"].get("name"),
                "runtime": entry["payload"].get("runtime"),
                "path": entry["path"],
                "schema": entry["schema"],
                "valid": entry["valid"],
                "errors": entry["errors"],
                "apply_policy": entry["payload"].get("apply_policy"),
                "canonical_sources": entry["payload"].get("canonical_sources", []),
                "live_targets": entry["payload"].get("live_targets", []),
                "connector": entry["payload"].get("connector", {}),
                "asset_class": entry.get("asset_class"),
                "shareability": entry.get("shareability"),
            }
            for entry in adapters
        ],
    }



def load_portable_skill_manifests(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> List[Dict[str, Any]]:
    skills: List[Dict[str, Any]] = []
    for manifest_path in _discover_manifest_paths(root):
        schema_name = detect_manifest_schema(manifest_path)
        if schema_name != "portable-skill-manifest-v1":
            continue
        payload = load_yaml_data(manifest_path)
        validation = validate_manifest_payload(schema_name, payload, schema_dir=schema_dir)
        entry = {
            "path": str(manifest_path),
            "schema": schema_name,
            "valid": validation["valid"],
            "errors": validation["errors"],
            "payload": payload,
        }
        entry.update(classify_asset_path(str(manifest_path)))
        skills.append(entry)
    skills.sort(key=lambda item: (str(item["payload"].get("status", "")), str(item["payload"].get("name", "")), item["path"]))
    return skills



def build_skills_inventory_report(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    skills = load_portable_skill_manifests(root, schema_dir=schema_dir)
    valid_skills = [entry for entry in skills if entry["valid"]]
    statuses: Dict[str, int] = {}
    projection_targets = set()
    for entry in valid_skills:
        payload = entry["payload"]
        status = str(payload.get("status", "unknown"))
        statuses[status] = statuses.get(status, 0) + 1
        projection = payload.get("adapter_projection", {})
        if isinstance(projection, dict):
            projection_targets.update(str(key) for key in projection.keys())
    return {
        "mode": "skills-inventory",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "schema_dir": str(schema_dir),
        "summary": {
            "total_skills": len(skills),
            "valid_skills": len(valid_skills),
            "invalid_skills": sum(1 for entry in skills if not entry["valid"]),
            "statuses": statuses,
            "projection_targets": sorted(projection_targets),
        },
        "skills": [
            {
                "name": entry["payload"].get("name"),
                "status": entry["payload"].get("status"),
                "confidence": entry["payload"].get("confidence"),
                "path": entry["path"],
                "schema": entry["schema"],
                "valid": entry["valid"],
                "errors": entry["errors"],
                "description": entry["payload"].get("description"),
                "trigger": entry["payload"].get("trigger"),
                "adapter_projection": entry["payload"].get("adapter_projection", {}),
                "asset_class": entry.get("asset_class"),
                "shareability": entry.get("shareability"),
            }
            for entry in skills
        ],
        "recommendations": [
            "Treat draft/probationary runtime-imported skills as candidates until reviewed",
            "Promote to active only with source evidence, verification, and boundaries",
            "Keep adapter projection declarative; do not execute arbitrary plugin code from skill manifests",
        ],
    }



def _format_skill_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, dict):
                items.append("; ".join(f"{k}: {v}" for k, v in item.items()))
            else:
                items.append(str(item))
        return [item for item in items if item.strip()]
    if value is None:
        return []
    return [line.strip().lstrip("-*").strip() for line in str(value).splitlines() if line.strip()]



def render_skill_projection_preview(payload: Dict[str, Any]) -> str:
    name = payload.get("name", "unknown-skill")
    lines = [
        f"### {name}",
        "",
        f"- status: {payload.get('status', 'unknown')}",
        f"- confidence: {payload.get('confidence', 'unknown')}",
        f"- trigger: {payload.get('trigger', 'unspecified')}",
        f"- description: {payload.get('description', 'unspecified')}",
    ]
    procedure = _format_skill_list(payload.get("procedure"))
    verification = _format_skill_list(payload.get("verification"))
    boundaries = _format_skill_list(payload.get("boundaries"))
    if procedure:
        lines.append("- procedure:")
        lines.extend(f"  - {item}" for item in procedure)
    if verification:
        lines.append("- verification:")
        lines.extend(f"  - {item}" for item in verification)
    if boundaries:
        lines.append("- boundaries:")
        lines.extend(f"  - {item}" for item in boundaries)
    lines.append("")
    return "\n".join(lines)



def build_skill_projection_preview_report(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    skills = load_portable_skill_manifests(root, schema_dir=schema_dir)
    projectable = [entry for entry in skills if entry["valid"] and entry["payload"].get("status") in {"active", "probationary"}]
    actions: List[Dict[str, Any]] = []
    projection_targets = set()
    for entry in projectable:
        payload = entry["payload"]
        projection = payload.get("adapter_projection", {})
        if not isinstance(projection, dict):
            continue
        preview_text = render_skill_projection_preview(payload)
        for runtime, target_value in projection.items():
            target_path = _resolve_contract_path(root, str(target_value))
            projection_targets.add(str(runtime))
            actions.append({
                "skill": payload.get("name"),
                "skill_path": entry["path"],
                "runtime": str(runtime),
                "target": str(target_path),
                "target_exists": target_path.exists(),
                "mode": "preview-only",
                "would_write": False,
                "preview_text": preview_text,
                "description": "Would append or merge a reviewed portable skill projection into this adapter after explicit review/apply",
            })
    return {
        "mode": "skill-projection-preview",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "schema_dir": str(schema_dir),
        "summary": {
            "total_skills": len(skills),
            "projectable_skills": len(projectable),
            "actions": len(actions),
            "projection_targets": sorted(projection_targets),
        },
        "actions": actions,
        "recommendations": [
            "This mode is preview-only and does not modify adapters or runtimes",
            "Project only active/probationary skills with reviewed evidence and boundaries",
            "Use a future explicit projection apply gate after reviewing this report",
        ],
    }



def _projection_candidate_filename(action: Dict[str, Any]) -> str:
    target_name = Path(str(action.get("target", "adapter"))).name.replace(".md", "")
    return f"{safe_slug(str(action.get('runtime', 'runtime')))}.{safe_slug(target_name)}.skill-projection.md"



def render_skill_projection_candidate(action: Dict[str, Any]) -> str:
    return "\n".join([
        f"# Skill Projection Candidate — {action.get('runtime')} / {action.get('skill')}",
        "",
        "This is a review candidate. Do not apply blindly.",
        "",
        "## Target adapter",
        "",
        f"- Runtime: {action.get('runtime')}",
        f"- Target adapter: `{action.get('target')}`",
        f"- Target exists: {action.get('target_exists')}",
        f"- Source skill: `{action.get('skill_path')}`",
        "",
        "## Proposed projection block",
        "",
        "```markdown",
        str(action.get("preview_text", "")).rstrip(),
        "```",
        "",
        "## Review checklist",
        "",
        "- Confirm this skill belongs in the target adapter.",
        "- Remove environment-specific or private details if needed.",
        "- Preserve existing adapter instructions when merging.",
        "- Create a reviewed projection file only after human review.",
        "",
    ])



def generate_skill_projection_candidates(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    preview_report = build_skill_projection_preview_report(root, schema_dir=schema_dir)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_dir = root / "bootstrap" / "candidates" / f"skill-projections-{stamp}"
    candidates: List[Dict[str, Any]] = []
    actions = preview_report.get("actions", [])
    if actions:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        for action in actions:
            filename = _projection_candidate_filename(action)
            candidate_path = bundle_dir / filename
            candidate_path.write_text(render_skill_projection_candidate(action), encoding="utf-8")
            candidates.append({
                "skill": action.get("skill"),
                "runtime": action.get("runtime"),
                "target": action.get("target"),
                "candidate_path": str(candidate_path),
                "review_required": True,
            })
        (bundle_dir / "REVIEW-INSTRUCTIONS.md").write_text(
            "# Skill Projection Candidate Review\n\n"
            "These files are generated from portable skill manifests and adapter projection metadata.\n\n"
            "Review checklist:\n\n"
            "- Do not copy projections into adapters without reading them.\n"
            "- Preserve existing adapter-specific instruction contracts.\n"
            "- Keep private or environment-specific details out of public-safe adapters.\n"
            "- Future apply steps should use reviewed projection files, not these raw candidates.\n",
            encoding="utf-8",
        )
        summary_lines = [
            "# Skill Projection Candidates Summary",
            "",
            f"Generated candidates: {len(candidates)}",
            "",
        ]
        for item in candidates:
            summary_lines.append(f"- {item['skill']} -> {item['runtime']}: `{item['candidate_path']}`")
        (bundle_dir / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return {
        "mode": "skill-projection-candidates",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "schema_dir": str(schema_dir),
        "bundle_dir": str(bundle_dir) if actions else None,
        "summary": {
            "preview_actions": len(actions),
            "candidate_files": len(candidates),
        },
        "candidates": candidates,
        "recommendations": [
            "Review generated projection candidates before copying into adapter files",
            "Do not apply projections directly to live runtimes",
            "Use a future reviewed projection apply gate for adapter writes",
        ],
    }



def _discover_skill_projection_bundles(root: Path) -> List[Path]:
    candidates_root = root / "bootstrap" / "candidates"
    if not candidates_root.is_dir():
        return []
    return sorted([path for path in candidates_root.glob("skill-projections-*") if path.is_dir()], key=lambda path: path.name)



def _extract_markdown_backtick_field(text: str, field_name: str) -> Optional[str]:
    pattern = rf"{re.escape(field_name)}:\s*`([^`]+)`"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None



def _extract_reviewed_projection_block(text: str) -> str:
    marker = "## Reviewed projection block"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text.strip()



def build_skill_projection_status_report(root: Path = ASSETS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    bundles = _discover_skill_projection_bundles(root)
    bundle_entries: List[Dict[str, Any]] = []
    candidate_total = 0
    reviewed_total = 0
    ready_total = 0
    for bundle in bundles:
        candidate_files = sorted(bundle.glob("*.skill-projection.md"))
        reviewed_files = sorted(bundle.glob("*.reviewed.md"))
        reviewed_entries: List[Dict[str, Any]] = []
        for reviewed in reviewed_files:
            text = reviewed.read_text(encoding="utf-8", errors="replace")
            target = _extract_markdown_backtick_field(text, "Target adapter")
            block = _extract_reviewed_projection_block(text)
            errors: List[str] = []
            if not target:
                errors.append("missing Target adapter metadata")
            if not block.strip():
                errors.append("reviewed projection block is empty")
            ready = not errors
            reviewed_entries.append({
                "path": str(reviewed),
                "target": target,
                "valid": ready,
                "errors": errors,
                "ready_to_apply": ready,
                "bytes": len(text.encode("utf-8")),
            })
            if ready:
                ready_total += 1
        candidate_total += len(candidate_files)
        reviewed_total += len(reviewed_files)
        bundle_entries.append({
            "bundle_dir": str(bundle),
            "candidate_files": [str(path) for path in candidate_files],
            "reviewed_files": reviewed_entries,
            "ready_to_apply": sum(1 for item in reviewed_entries if item["ready_to_apply"]),
        })
    return {
        "mode": "skill-projection-status",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "bundles": len(bundles),
            "candidate_files": candidate_total,
            "reviewed_files": reviewed_total,
            "ready_to_apply": ready_total,
        },
        "bundles": bundle_entries,
        "recommendations": [
            "Create *.reviewed.md files only after reviewing projection candidates",
            "Run --skill-projection-review-apply only after reviewed projections are ready",
            "Review adapter diffs before projecting changes to live runtimes",
        ],
    }



def execute_skill_projection_review_apply(root: Path = ASSETS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    status_report = build_skill_projection_status_report(root)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = root / "bootstrap" / "backups" / f"skill-projection-review-apply-{stamp}"
    results: List[Dict[str, Any]] = []
    applied = 0
    skipped = 0
    failed = 0
    for bundle in status_report["bundles"]:
        for reviewed in bundle.get("reviewed_files", []):
            source = Path(reviewed["path"])
            result = {"source": str(source), "target": reviewed.get("target"), "status": "skipped", "details": "", "backup_path": None}
            if not reviewed.get("valid"):
                result["details"] = f"Reviewed projection is not ready: {', '.join(reviewed.get('errors', []))}"
                skipped += 1
                results.append(result)
                continue
            try:
                text = source.read_text(encoding="utf-8", errors="replace")
                projection_block = _extract_reviewed_projection_block(text)
                target = Path(str(reviewed["target"])).expanduser()
                if not target.is_absolute():
                    target = root / target
                target.parent.mkdir(parents=True, exist_ok=True)
                backup_path = backup_target(target, backup_root)
                existing = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
                addition = "\n\n<!-- portable-ai-assets: skill-projection:start -->\n" + projection_block.strip() + "\n<!-- portable-ai-assets: skill-projection:end -->\n"
                target.write_text(existing.rstrip() + addition, encoding="utf-8")
                result.update({"status": "applied", "details": "Appended reviewed skill projection to adapter", "backup_path": str(backup_path) if backup_path else None})
                applied += 1
            except Exception as exc:
                result.update({"status": "failed", "details": str(exc)})
                failed += 1
            results.append(result)
    return {
        "mode": "skill-projection-review-apply",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "backup_root": str(backup_root),
        "based_on_status_generated_at": status_report["generated_at"],
        "summary": {"applied": applied, "skipped": skipped, "failed": failed},
        "results": results,
        "recommendations": [
            "Review adapter diffs before projecting to live runtimes",
            "Run connector/diff reports before applying adapter changes into runtime files",
            "Do not auto-commit or auto-push projection changes",
        ],
    }



def _resolve_contract_path(root: Path, value: str) -> Path:
    expanded = value.replace("~", str(HOME), 1) if value.startswith("~") else value
    candidate = Path(expanded)
    if candidate.is_absolute():
        return candidate
    return root / candidate



def _preview_connector_action(root: Path, adapter: Dict[str, Any], direction: str) -> Dict[str, Any]:
    connector = adapter.get("connector", {})
    connector_name = str(connector.get(direction, "unknown"))
    if direction == "export":
        source_value = next(iter(adapter.get("canonical_sources", []) or []), "")
        target_value = next(iter(adapter.get("live_targets", []) or []), "")
    else:
        source_value = next(iter(adapter.get("live_targets", []) or []), "")
        target_value = next(iter(adapter.get("canonical_sources", []) or []), "")
    source = _resolve_contract_path(root, source_value) if source_value else root
    target = _resolve_contract_path(root, target_value) if target_value else root
    source_exists = source.is_file()
    content_bytes = source.stat().st_size if source_exists else 0
    if connector_name == "write-file":
        description = "Would project canonical content into the live runtime target without executing writes in preview mode."
    elif connector_name == "read-file":
        description = "Would read the live runtime target into a candidate view without modifying files."
    elif connector_name == "copy-file":
        description = "Would copy bytes from source to target, but preview mode only reports the action."
    else:
        description = "Unknown connector type; preview mode reports metadata only."
    return {
        "direction": direction,
        "connector": connector_name,
        "mode": "preview",
        "source": str(source),
        "target": str(target),
        "source_exists": source_exists,
        "bytes_available": content_bytes,
        "description": description,
    }



def build_connector_preview_report(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    connector_report = build_connector_report(root, schema_dir=schema_dir)
    preview_adapters: List[Dict[str, Any]] = []
    for adapter in connector_report["adapters"]:
        if not adapter.get("valid"):
            continue
        preview_adapters.append(
            {
                **adapter,
                "actions": [
                    _preview_connector_action(root, adapter, "export"),
                    _preview_connector_action(root, adapter, "import"),
                ],
            }
        )
    return {
        "mode": "connector-preview",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "schema_dir": str(schema_dir),
        "summary": {
            "previewable_adapters": len(preview_adapters),
            "runtimes": connector_report["summary"]["runtimes"],
            "import_connectors": connector_report["summary"]["import_connectors"],
            "export_connectors": connector_report["summary"]["export_connectors"],
        },
        "adapters": preview_adapters,
    }



def _redact_public_text(text: str) -> str:
    text = re.sub(r"/Users/(?!example\b|yourname\b|you\b)[A-Za-z0-9._-]+", "/Users/example", text)
    text = re.sub(r"/home/(?!example\b|yourname\b|you\b)[A-Za-z0-9._-]+", "/home/example", text)
    text = re.sub(r"(?i)(\b(api[_-]?key|secret|token|password|credential)\b\s*[:=]\s*)['\"]?[^\s'\"]{8,}", r"\1[REDACTED]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{20,}\b", "[REDACTED]", text)
    text = re.sub(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b", "[REDACTED]", text)
    return text


def _redact_public_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_public_text(value)
    if isinstance(value, list):
        return [_redact_public_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_public_value(item) for key, item in value.items()}
    return value



def generate_redacted_example_bundle(root: Path = ASSETS) -> Dict[str, str]:
    reports_dir = root / "bootstrap" / "reports"
    connectors_path = reports_dir / "latest-connectors.json"
    if not connectors_path.is_file():
        raise FileNotFoundError(connectors_path)
    connector_report = json.loads(connectors_path.read_text(encoding="utf-8"))
    examples_root = root / "examples" / "redacted"
    examples_root.mkdir(parents=True, exist_ok=True)
    walkthrough_path = examples_root / "connector-walkthrough.example.md"
    summary_path = examples_root / "connector-summary.example.json"
    lines: List[str] = []
    lines.append("# Redacted Connector Walkthrough")
    lines.append("")
    lines.append("This is a public-safe example generated from the latest connector inventory.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- total_adapters: {connector_report['summary']['total_adapters']}")
    lines.append(f"- runtimes: {', '.join(connector_report['summary']['runtimes']) or 'none'}")
    lines.append(f"- export_connectors: {', '.join(connector_report['summary']['export_connectors']) or 'none'}")
    lines.append("")
    lines.append("## Adapters")
    lines.append("")
    for adapter in connector_report.get("adapters", []):
        if adapter.get("shareability") != "public-safe":
            continue
        lines.append(f"### {adapter['name']}")
        lines.append("")
        lines.append(f"- runtime: {adapter['runtime']}")
        lines.append(f"- apply_policy: {adapter['apply_policy']}")
        lines.append(f"- shareability: {adapter['shareability']}")
        lines.append(f"- connector.import: {adapter.get('connector', {}).get('import', 'unknown')}")
        lines.append(f"- connector.export: {adapter.get('connector', {}).get('export', 'unknown')}")
        lines.append(f"- canonical_sources: {_redact_public_text(', '.join(adapter.get('canonical_sources', [])) or 'none')}")
        lines.append(f"- live_targets: {_redact_public_text(', '.join(adapter.get('live_targets', [])) or 'none')}")
        lines.append("")
    walkthrough_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    public_summary = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source_report": str(connectors_path.relative_to(root)) if connectors_path.is_relative_to(root) else connectors_path.name,
        "total_public_safe_adapters": sum(1 for adapter in connector_report.get("adapters", []) if adapter.get("shareability") == "public-safe"),
        "runtimes": connector_report["summary"]["runtimes"],
    }
    summary_path.write_text(json.dumps(_redact_public_value(public_summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "walkthrough_path": str(walkthrough_path),
        "summary_path": str(summary_path),
    }



def build_redacted_examples_report(root: Path = ASSETS) -> Dict[str, Any]:
    bundle = generate_redacted_example_bundle(root)
    return {
        "mode": "redacted-examples",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "outputs": bundle,
    }



def _load_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}



def build_demo_story_report(root: Path = ASSETS) -> Dict[str, Any]:
    reports_dir = root / "bootstrap" / "reports"
    examples_dir = root / "examples" / "redacted"
    examples_dir.mkdir(parents=True, exist_ok=True)
    validate_report = _load_json_if_exists(reports_dir / "latest-validate-schemas.json")
    connectors_report = _load_json_if_exists(reports_dir / "latest-connectors.json")
    preview_report = _load_json_if_exists(reports_dir / "latest-connector-preview.json")
    story_path = examples_dir / "demo-story.example.md"
    lines: List[str] = []
    lines.append("# Portable AI Assets Demo Story")
    lines.append("")
    lines.append("This is a public-safe walkthrough for demonstrating the open-source prototype.")
    lines.append("")
    lines.append("## 60-second promise")
    lines.append("")
    lines.append("Own your AI work environment instead of rebuilding it every time you change tools, models, clients, or machines.")
    lines.append("")
    lines.append("The demo arc shows a portable asset layer in miniature: machine-checkable structure, runtime adapter vocabulary, non-mutating connector previews, redacted public examples, and safety/release review gates.")
    lines.append("")
    lines.append("## Step 1 — Validate schemas")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --validate-schemas --both`")
    lines.append(f"Expected valid manifests: {validate_report.get('summary', {}).get('valid', 'unknown')}")
    lines.append("")
    lines.append("## Step 2 — Inspect adapter inventory")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --connectors --both`")
    lines.append(f"Expected runtimes: {', '.join(connectors_report.get('summary', {}).get('runtimes', [])) or 'unknown'}")
    lines.append("")
    lines.append("## Step 3 — Preview built-in connector actions")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --connector-preview --both`")
    lines.append(f"Expected previewable adapters: {preview_report.get('summary', {}).get('previewable_adapters', 'unknown')}")
    lines.append("")
    lines.append("## Step 4 — Generate public-safe example artifacts")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --redacted-examples --both`")
    lines.append("Expected artifact: `examples/redacted/connector-walkthrough.example.md`")
    lines.append("")
    lines.append("## Step 5 — Run public safety and release review gates")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both`")
    lines.append("Expected report: `bootstrap/reports/latest-public-safety-scan.md`")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --release-readiness --both`")
    lines.append("Expected report: `bootstrap/reports/latest-release-readiness.md`")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --completed-work-review --both`")
    lines.append("Expected report: `bootstrap/reports/latest-completed-work-review.md`")
    lines.append("")
    lines.append("## Step 6 — Package the demo story")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --demo-story --both`")
    lines.append("Expected artifact: `examples/redacted/demo-story.example.md`")
    lines.append("")
    lines.append("## Step 7 — Build the public demo pack")
    lines.append("")
    lines.append("Run: `./bootstrap/setup/bootstrap-ai-assets.sh --public-demo-pack --both`")
    lines.append("Expected artifact: `examples/redacted/public-demo-pack/`")
    lines.append("")
    lines.append("## Suggested sharing bundle")
    lines.append("")
    lines.append("- `docs/public-facing-thesis.md`")
    lines.append("- `docs/open-source-demo-story.md`")
    lines.append("- `docs/open-source-demo-pack.md`")
    lines.append("- `docs/reference-coding-agent-workspace-portability.md`")
    lines.append("- `bootstrap/reports/latest-validate-schemas.md`")
    lines.append("- `bootstrap/reports/latest-connectors.md`")
    lines.append("- `bootstrap/reports/latest-connector-preview.md`")
    lines.append("- `bootstrap/reports/latest-public-safety-scan.md`")
    lines.append("- `bootstrap/reports/latest-release-readiness.md`")
    lines.append("- `bootstrap/reports/latest-completed-work-review.md`")
    lines.append("- `examples/redacted/connector-walkthrough.example.md`")
    story_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "mode": "demo-story",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "story_path": str(story_path),
        "summary": {
            "validated_manifests": validate_report.get("summary", {}).get("valid"),
            "adapter_runtimes": connectors_report.get("summary", {}).get("runtimes", []),
            "previewable_adapters": preview_report.get("summary", {}).get("previewable_adapters"),
        },
    }



def build_public_demo_pack_report(root: Path = ASSETS) -> Dict[str, Any]:
    pack_root = root / "examples" / "redacted" / "public-demo-pack"
    pack_root.mkdir(parents=True, exist_ok=True)
    artifacts = [
        root / "README.md",
        root / "docs" / "architecture.md",
        root / "docs" / "adapter-sdk.md",
        root / "docs" / "public-facing-thesis.md",
        root / "docs" / "open-source-demo-story.md",
        root / "docs" / "open-source-demo-pack.md",
        root / "docs" / "reference-coding-agent-workspace-portability.md",
        root / "bootstrap" / "reports" / "latest-validate-schemas.md",
        root / "bootstrap" / "reports" / "latest-connectors.md",
        root / "bootstrap" / "reports" / "latest-connector-preview.md",
        root / "bootstrap" / "reports" / "latest-public-safety-scan.md",
        root / "bootstrap" / "reports" / "latest-release-readiness.md",
        root / "bootstrap" / "reports" / "latest-completed-work-review.md",
        root / "examples" / "redacted" / "connector-walkthrough.example.md",
        root / "examples" / "redacted" / "demo-story.example.md",
    ]
    copied: List[str] = []
    for artifact in artifacts:
        if not artifact.is_file():
            continue
        destination = pack_root / artifact.name
        destination.write_text(_redact_public_text(artifact.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
        copied.append(artifact.name)
    manifest = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "asset_class": "public",
        "pack_kind": "public-demo-pack",
        "file_count": len(copied),
        "files": copied,
    }
    manifest_path = pack_root / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index_path = pack_root / "PACK-INDEX.md"
    lines = [
        "# Public Demo Pack",
        "",
        "This directory bundles the core public-safe artifacts for a lightweight open-source demo.",
        "",
        "## Portable AI Assets demo arc",
        "",
        "1. explain the 60-second promise: own the AI work environment instead of rebuilding it when tools, models, clients, or machines change",
        "2. show schemas and adapter reports as the machine-checkable portability layer",
        "3. show connector previews and redacted examples without mutating live runtimes",
        "4. show public safety, release readiness, and completed-work review evidence before sharing",
        "",
        f"Generated: {manifest['generated_at']}",
        f"Asset class: {manifest['asset_class']}",
        f"File count: {manifest['file_count']}",
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- {name}" for name in copied)
    lines.extend(["", "## Metadata", "", f"- MANIFEST.json: `{manifest_path.name}`"])
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "mode": "public-demo-pack",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "pack_dir": str(pack_root),
        "index_path": str(index_path),
        "manifest_path": str(manifest_path),
        "summary": {
            "files_in_pack": len(copied),
        },
    }



PUBLIC_SAFETY_SCAN_DIRS = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
    "CHANGELOG.md",
    "RELEASE_NOTES-v0.1.md",
    "GIT-POLICY.md",
    "BACKUP-POLICY.md",
    "docs",
    "schemas",
    "adapters/registry",
    "bootstrap/setup",
    "bin",
    "sample-assets",
    "examples/redacted",
]

PUBLIC_SAFETY_EXCLUDE_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "bootstrap/reports",
    "bootstrap/backups",
    "bootstrap/candidates",
    "non-git-backups",
}

SECRET_LIKE_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----", re.IGNORECASE)),
    ("api-key-assignment", re.compile(r"(?i)\b(api[_-]?key|secret|token|password|credential)\b\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
]

PRIVATE_PATH_PATTERNS = [
    ("private-macos-home", re.compile(r"/Users/(?!example\b|yourname\b|you\b)[A-Za-z0-9._-]+")),
    ("private-linux-home", re.compile(r"/home/(?!example\b|yourname\b|you\b)[A-Za-z0-9._-]+")),
]

TEXT_FILE_SUFFIXES = {
    "",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".toml",
    ".cfg",
    ".ini",
}


def _is_public_scan_excluded(path: Path) -> bool:
    parts = set(path.parts)
    if parts.intersection(PUBLIC_SAFETY_EXCLUDE_PARTS):
        return True
    normalized = str(path)
    return any(excluded in normalized for excluded in PUBLIC_SAFETY_EXCLUDE_PARTS)


def _iter_public_surface_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for rel in PUBLIC_SAFETY_SCAN_DIRS:
        base = root / rel
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if _is_public_scan_excluded(candidate.relative_to(root) if candidate.is_relative_to(root) else candidate):
                continue
            if candidate.suffix not in TEXT_FILE_SUFFIXES:
                continue
            files.append(candidate)
    return sorted(set(files))


def _scan_text_for_public_safety_findings(path: Path, text: str, root: Path) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    relative = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "[REDACTED]" in line:
            continue
        for finding_type, pattern in SECRET_LIKE_PATTERNS:
            if pattern.search(line):
                findings.append({
                    "severity": "blocker",
                    "type": finding_type,
                    "path": relative,
                    "line": line_no,
                    "excerpt": line.strip()[:180],
                    "recommendation": "Replace secret-like content with [REDACTED] or move it to private asset/runtime state.",
                })
        for finding_type, pattern in PRIVATE_PATH_PATTERNS:
            for match in pattern.finditer(line):
                findings.append({
                    "severity": "warning",
                    "type": finding_type,
                    "path": relative,
                    "line": line_no,
                    "excerpt": match.group(0),
                    "recommendation": "Use /Users/example/... or document this only in private/local reports before publishing.",
                })
    return findings


PUBLIC_RELEASE_INCLUDE_PATHS = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
    "CHANGELOG.md",
    "RELEASE_NOTES-v0.1.md",
    "GIT-POLICY.md",
    "BACKUP-POLICY.md",
    "docs",
    "schemas",
    "adapters/README.md",
    "adapters/registry",
    "bootstrap/setup",
    "tests",
    "sample-assets",
    "examples/README.md",
    "examples/redacted",
]

PUBLIC_RELEASE_REPORTS = [
    "latest-validate-schemas.md",
    "latest-validate-schemas.json",
    "latest-connectors.md",
    "latest-connectors.json",
    "latest-connector-preview.md",
    "latest-connector-preview.json",
    "latest-public-safety-scan.md",
    "latest-public-safety-scan.json",
    "latest-release-readiness.md",
    "latest-release-readiness.json",
    "latest-team-pack-preview.md",
    "latest-team-pack-preview.json",
    "latest-public-demo-pack.md",
    "latest-public-demo-pack.json",
    "latest-release-closure.md",
    "latest-release-closure.json",
    "latest-github-final-preflight.md",
    "latest-github-final-preflight.json",
    "latest-manual-release-reviewer-checklist.md",
    "latest-manual-release-reviewer-checklist.json",
    "latest-public-docs-external-reader-review.md",
    "latest-public-docs-external-reader-review.json",
    "latest-release-candidate-closure-review.md",
    "latest-release-candidate-closure-review.json",
    "latest-release-reviewer-packet-index.md",
    "latest-release-reviewer-packet-index.json",
    "latest-release-reviewer-decision-log.md",
    "latest-release-reviewer-decision-log.json",
    "latest-external-reviewer-quickstart.md",
    "latest-external-reviewer-quickstart.json",
    "latest-external-reviewer-feedback-plan.md",
    "latest-external-reviewer-feedback-plan.json",
    "latest-external-reviewer-feedback-status.md",
    "latest-external-reviewer-feedback-status.json",
    "latest-external-reviewer-feedback-template.md",
    "latest-external-reviewer-feedback-template.json",
    "latest-external-reviewer-feedback-followup-index.md",
    "latest-external-reviewer-feedback-followup-index.json",
    "latest-external-reviewer-feedback-followup-candidates.md",
    "latest-external-reviewer-feedback-followup-candidates.json",
    "latest-external-reviewer-feedback-followup-candidate-status.md",
    "latest-external-reviewer-feedback-followup-candidate-status.json",
    "latest-initial-completion-review.md",
    "latest-initial-completion-review.json",
    "latest-human-action-closure-checklist.md",
    "latest-human-action-closure-checklist.json",
    "latest-manual-reviewer-execution-packet.md",
    "latest-manual-reviewer-execution-packet.json",
    "latest-manual-reviewer-public-surface-freshness.md",
    "latest-manual-reviewer-public-surface-freshness.json",
    "latest-manual-reviewer-handoff-readiness.md",
    "latest-manual-reviewer-handoff-readiness.json",
    "latest-manual-reviewer-handoff-packet-index.md",
    "latest-manual-reviewer-handoff-packet-index.json",
    "latest-manual-reviewer-handoff-freeze-check.md",
    "latest-manual-reviewer-handoff-freeze-check.json",
    "latest-agent-owner-delegation-review.md",
    "latest-agent-owner-delegation-review.json",
    "latest-agent-complete-external-actions-reserved.md",
    "latest-agent-complete-external-actions-reserved.json",
    "latest-agent-complete-failclosed-hardening-review.md",
    "latest-agent-complete-failclosed-hardening-review.json",
    "latest-agent-complete-regression-evidence-integrity.md",
    "latest-agent-complete-regression-evidence-integrity.json",
    "latest-agent-complete-syntax-invalid-evidence-failclosed-review.md",
    "latest-agent-complete-syntax-invalid-evidence-failclosed-review.json",
    "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md",
    "latest-agent-complete-phase102-rollup-evidence-failclosed-review.json",
    "latest-completed-work-review.md",
    "latest-completed-work-review.json",
    "latest-public-repo-staging-history-preflight.md",
    "latest-public-repo-staging-history-preflight.json",
    "latest-manual-publication-decision-packet.md",
    "latest-manual-publication-decision-packet.json",
]

PUBLIC_RELEASE_EXCLUDE_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "bootstrap/backups",
    "bootstrap/candidates",
    "bootstrap/state",
    "non-git-backups",
    "memory",
    "skills",
    "dist",
}


def _is_public_release_excluded(path: Path) -> bool:
    normalized = str(path)
    parts = set(path.parts)
    if parts.intersection(PUBLIC_RELEASE_EXCLUDE_PARTS):
        return True
    return any(excluded in normalized for excluded in PUBLIC_RELEASE_EXCLUDE_PARTS)


def _iter_public_release_source_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for rel in PUBLIC_RELEASE_INCLUDE_PATHS:
        base = root / rel
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(root) if candidate.is_relative_to(root) else candidate
            if _is_public_release_excluded(relative):
                continue
            if candidate.suffix not in TEXT_FILE_SUFFIXES:
                continue
            files.append(candidate)
    reports_dir = root / "bootstrap" / "reports"
    for report_name in PUBLIC_RELEASE_REPORTS:
        report_path = reports_dir / report_name
        if report_path.is_file():
            files.append(report_path)
    return sorted(set(files))


def _public_snapshot_notice(report_name: str) -> Dict[str, Any]:
    return {
        "static_sanitized_snapshot": True,
        "message": (
            f"{report_name} is a static sanitized snapshot copied into a public artifact; "
            "it is not live GitHub state and may describe the staging context at generation time. "
            "Regenerate local report-only gates for current status."
        ),
    }


def _label_public_report_snapshot_text(report_name: str, text: str) -> str:
    notice = _public_snapshot_notice(report_name)
    if report_name.endswith(".json"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data.setdefault("public_snapshot_notice", notice)
                return json.dumps(_redact_public_value(data), ensure_ascii=False, indent=2) + "\n"
        except Exception:
            pass
    if report_name.endswith(".md"):
        prefix = (
            "<!-- Public snapshot notice: this is a static sanitized snapshot copied into a public artifact; "
            "it is not live GitHub state. Regenerate local report-only gates for current status. -->\n\n"
        )
        if "Public snapshot notice" not in text:
            return prefix + _redact_public_text(text)
    return _redact_public_text(text)


def _write_public_reports_readme(reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    readme = reports_dir / "README.md"
    readme.write_text(
        "# Public report snapshots\n\n"
        "Files in this directory are static sanitized snapshots copied into the public artifact. "
        "They are not live GitHub state and may describe the source or staging context at the time the artifact was generated.\n\n"
        "For current status, rerun the local report-only gates such as public safety, staging history preflight, GitHub dry-run, and manual publication decision packet.\n",
        encoding="utf-8",
    )


def _write_public_release_index(pack_dir: Path, manifest: Dict[str, Any]) -> None:
    lines = [
        "# Portable AI Assets Public Release Pack",
        "",
        "This export contains only the public-safe engine/demo surface selected by the release pack generator.",
        "",
        f"Generated: {manifest['generated_at']}",
        f"Pack kind: {manifest['pack_kind']}",
        f"File count: {manifest['file_count']}",
        "",
        "## Safety metadata",
        "",
        f"- Public safety status: {manifest.get('public_safety_status', 'unknown')}",
        f"- Release readiness: {manifest.get('release_readiness', 'unknown')}",
        "- Private memory, raw runtime state, backups, candidates, machine-local config, DBs, and logs are intentionally excluded.",
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- `{path}`" for path in manifest.get("files", []))
    lines.extend(["", "## Integrity", "", "- `MANIFEST.json`", "- `CHECKSUMS.sha256`"])
    (pack_dir / "PACK-INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_public_release_pack_report(root: Path = ASSETS) -> Dict[str, Any]:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dist_root = root / "dist"
    pack_dir = dist_root / f"portable-ai-assets-public-{stamp}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    source_files = _iter_public_release_source_files(root)
    copied: List[str] = []
    skipped: List[Dict[str, str]] = []
    for source in source_files:
        try:
            relative = source.relative_to(root)
        except ValueError:
            skipped.append({"path": str(source), "reason": "outside-root"})
            continue
        target = pack_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
            relative_text = str(relative)
            if relative_text.startswith("bootstrap/reports/latest-"):
                target.write_text(_label_public_report_snapshot_text(source.name, text), encoding="utf-8")
            else:
                target.write_text(_redact_public_text(text), encoding="utf-8")
            copied.append(str(relative))
        except Exception as exc:
            skipped.append({"path": str(relative), "reason": str(exc)})

    pack_reports_dir = pack_dir / "bootstrap" / "reports"
    if pack_reports_dir.exists():
        _write_public_reports_readme(pack_reports_dir)
        copied.append(str((pack_reports_dir / "README.md").relative_to(pack_dir)))

    release_readiness = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-release-readiness.json")
    public_safety = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-public-safety-scan.json")
    files_for_manifest = sorted(copied)
    manifest = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "asset_class": "public",
        "pack_kind": "public-release-pack",
        "source_root": str(root),
        "file_count": len(files_for_manifest),
        "files": files_for_manifest,
        "excluded_private_surfaces": ["memory", "skills", "bootstrap/candidates", "bootstrap/backups", "bootstrap/state", "non-git-backups", "runtime DBs/logs", "machine-local config"],
        "public_safety_status": public_safety.get("summary", {}).get("status", "unknown"),
        "release_readiness": release_readiness.get("summary", {}).get("readiness", "unknown"),
    }
    _write_public_release_index(pack_dir, manifest)
    manifest_path = pack_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(_redact_public_value(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checksum_lines: List[str] = []
    checksum_files = sorted([path for path in pack_dir.rglob("*") if path.is_file()])
    for path in checksum_files:
        relative = path.relative_to(pack_dir)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checksum_lines.append(f"{digest}  {relative}")
    checksums_path = pack_dir / "CHECKSUMS.sha256"
    checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    return {
        "mode": "public-release-pack",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "dist_root": str(dist_root),
        "pack_dir": str(pack_dir),
        "manifest_path": str(manifest_path),
        "checksums_path": str(checksums_path),
        "summary": {
            "files_in_pack": len(files_for_manifest),
            "skipped": len(skipped),
            "public_safety_status": manifest["public_safety_status"],
            "release_readiness": manifest["release_readiness"],
        },
        "files": files_for_manifest,
        "skipped": skipped,
        "recommendations": [
            "Run --public-safety-scan and --release-readiness immediately before sharing this pack.",
            "Review MANIFEST.json and CHECKSUMS.sha256 before publishing.",
            "Publish the generated dist directory or archive it externally; the command does not commit or push.",
        ],
    }


def _latest_public_release_pack_dir(root: Path) -> Optional[Path]:
    latest_report = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-public-release-pack.json")
    pack_dir_value = latest_report.get("pack_dir")
    if isinstance(pack_dir_value, str) and Path(pack_dir_value).is_dir():
        return Path(pack_dir_value)
    dist_root = root / "dist"
    if not dist_root.is_dir():
        return None
    candidates = sorted((path for path in dist_root.glob("portable-ai-assets-public-*") if path.is_dir()), key=lambda path: path.name)
    return candidates[-1] if candidates else None


def build_public_package_freshness_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only check that Phase 78 release-review evidence reached pack/staging.

    This gate reads local latest-* reports and generated public artifacts only. It does
    not publish, push, create repositories/tags/releases, validate credentials, call
    providers, or mutate remote state.
    """
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    required_reports = [
        "public-release-pack",
        "public-repo-staging-status",
        "manual-release-reviewer-checklist",
        "public-safety-scan",
        "release-readiness",
        "release-closure",
        "github-final-preflight",
    ]
    latest_reports = {prefix: _load_json_if_exists(reports_dir / f"latest-{prefix}.json") for prefix in required_reports}

    pack_dir = _latest_public_release_pack_dir(root)
    staging_report = latest_reports.get("public-repo-staging-status") or {}
    staging_dir_value = staging_report.get("staging_dir") if isinstance(staging_report, dict) else None
    staging_dir = Path(staging_dir_value) if isinstance(staging_dir_value, str) else root / "dist" / "github-staging" / "portable-ai-assets"

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def tree_contains_text(base: Optional[Path], needle: str, relative_paths: List[str]) -> bool:
        if base is None or not base.is_dir():
            return False
        for relative in relative_paths:
            if needle in read_optional(base / relative):
                return True
        return False

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    def report_summary(prefix: str) -> Dict[str, Any]:
        report = latest_reports.get(prefix) or {}
        summary = report.get("summary") if isinstance(report, dict) else None
        return summary if isinstance(summary, dict) else {}

    add_check("public-release-pack:latest-report", latest_reports.get("public-release-pack") is not None, str(reports_dir / "latest-public-release-pack.json"))
    add_check("public-release-pack:dir", pack_dir is not None and pack_dir.is_dir(), str(pack_dir) if pack_dir else "missing")
    add_check("public-release-pack:manual-reviewer-json", pack_dir is not None and (pack_dir / "bootstrap" / "reports" / "latest-manual-release-reviewer-checklist.json").is_file(), "bootstrap/reports/latest-manual-release-reviewer-checklist.json")
    add_check("public-release-pack:manual-reviewer-md", pack_dir is not None and (pack_dir / "bootstrap" / "reports" / "latest-manual-release-reviewer-checklist.md").is_file(), "bootstrap/reports/latest-manual-release-reviewer-checklist.md")
    add_check("public-release-pack:manual-reviewer-command-doc", tree_contains_text(pack_dir, "--manual-release-reviewer-checklist", ["docs/open-source-release-plan.md", "docs/public-roadmap.md", "bootstrap/setup/bootstrap-ai-assets.sh"]), "public pack documents manual release reviewer checklist command")
    add_check("public-release-pack:freshness-review-command-shell", tree_contains_text(pack_dir, "--public-package-freshness-review", ["bootstrap/setup/bootstrap-ai-assets.sh", "docs/open-source-release-plan.md", "docs/public-roadmap.md"]), "public pack includes freshness review command wiring")

    add_check("github-staging:latest-status-report", latest_reports.get("public-repo-staging-status") is not None, str(reports_dir / "latest-public-repo-staging-status.json"))
    add_check("github-staging:dir", staging_dir.is_dir(), str(staging_dir))
    add_check("github-staging:manual-reviewer-command-doc", tree_contains_text(staging_dir, "--manual-release-reviewer-checklist", ["docs/open-source-release-plan.md", "docs/public-roadmap.md", "bootstrap/setup/bootstrap-ai-assets.sh"]), "GitHub staging documents manual release reviewer checklist command")
    add_check("github-staging:freshness-review-command-shell", tree_contains_text(staging_dir, "--public-package-freshness-review", ["bootstrap/setup/bootstrap-ai-assets.sh", "docs/open-source-release-plan.md", "docs/public-roadmap.md"]), "GitHub staging includes freshness review command wiring")

    manual_summary = report_summary("manual-release-reviewer-checklist")
    safety_summary = report_summary("public-safety-scan")
    readiness_summary = report_summary("release-readiness")
    closure_summary = report_summary("release-closure")
    preflight_summary = report_summary("github-final-preflight")
    staging_summary = report_summary("public-repo-staging-status")
    add_check("manual-release-reviewer-checklist:ready", manual_summary.get("status") == "ready-for-human-review" and manual_summary.get("executes_anything") is False, str(manual_summary or "missing"))
    add_check("public-safety-scan:pass", safety_summary.get("status") == "pass" and int(safety_summary.get("forbidden_findings", 0) or 0) == 0, str(safety_summary or "missing"))
    add_check("release-readiness:ready", readiness_summary.get("readiness") == "ready" and int(readiness_summary.get("fail", 0) or 0) == 0, str(readiness_summary or "missing"))
    add_check("release-closure:manual-review-ready", closure_summary.get("status") == "ready-for-manual-release-review" and closure_summary.get("executes_anything") is False, str(closure_summary or "missing"))
    add_check("github-final-preflight:ready", preflight_summary.get("status") == "ready" and preflight_summary.get("executes_anything") is False, str(preflight_summary or "missing"))
    add_check("public-repo-staging-status:ready", staging_summary.get("status") == "ready" and int(staging_summary.get("forbidden_findings", 0) or 0) == 0, str(staging_summary or "missing"))

    forbidden_findings = sum(int(report_summary(prefix).get("forbidden_findings", 0) or 0) for prefix in ["public-safety-scan", "release-closure", "github-final-preflight", "manual-release-reviewer-checklist", "public-repo-staging-status"])
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    blocked_sources = [prefix for prefix in ["manual-release-reviewer-checklist", "release-closure", "github-final-preflight"] if str(report_summary(prefix).get("status", "")).startswith("blocked")]
    status = "blocked" if blocked_sources or forbidden_findings > 0 else ("stale" if fail_count else "ready")

    source_summaries = {prefix: report_summary(prefix) for prefix in required_reports}
    return {
        "mode": "public-package-freshness-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "pack_dir": str(pack_dir) if pack_dir else None,
        "staging_dir": str(staging_dir),
        "required_reports": required_reports,
        "source_summaries": source_summaries,
        "checks": checks,
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "forbidden_findings": forbidden_findings,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": bool(staging_summary.get("remote_configured") or closure_summary.get("remote_configured") or preflight_summary.get("remote_configured")),
        },
        "review_boundary": [
            "Report-only freshness review of local public release package and GitHub staging artifacts.",
            "Does not publish, push, create remotes, create repositories, create tags, create releases, call providers, or validate credentials.",
            "If stale, regenerate local public pack/staging artifacts and rerun this review before human publication review.",
        ],
        "recommendations": [
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --public-release-pack --both after changing public docs, reports, or release gates.",
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --public-repo-staging --both after refreshing the public release pack.",
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both after refreshing pack/staging artifacts.",
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --public-package-freshness-review --both immediately before manual release review.",
        ],
    }


def build_manual_reviewer_public_surface_freshness_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only check that the Phase 93 human runbook reached public surfaces.

    This gate reads local latest-* reports, generated public release pack files, GitHub
    staging files, docs, and shell wrapper text only. It does not publish, push, create
    repositories/tags/releases, validate credentials, call providers/APIs, execute
    commands, approve release, fabricate human feedback, or mutate issues/backlogs.
    """
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    required_reports = [
        "manual-reviewer-execution-packet",
        "public-release-pack",
        "public-repo-staging-status",
    ]
    latest_reports = {prefix: _load_json_if_exists(reports_dir / f"latest-{prefix}.json") for prefix in required_reports}

    pack_dir = _latest_public_release_pack_dir(root)
    pack_report = latest_reports.get("public-release-pack") or {}
    pack_dir_value = pack_report.get("pack_dir") if isinstance(pack_report, dict) else None
    if pack_dir is None and isinstance(pack_dir_value, str) and Path(pack_dir_value).is_dir():
        pack_dir = Path(pack_dir_value)

    staging_report = latest_reports.get("public-repo-staging-status") or {}
    staging_dir_value = staging_report.get("staging_dir") if isinstance(staging_report, dict) else None
    staging_dir = Path(staging_dir_value) if isinstance(staging_dir_value, str) else root / "dist" / "github-staging" / "portable-ai-assets"

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def tree_contains_text(base: Optional[Path], needle: str, relative_paths: List[str]) -> bool:
        if base is None or not base.is_dir():
            return False
        return any(needle in read_optional(base / relative) for relative in relative_paths)

    def report_summary(prefix: str) -> Dict[str, Any]:
        report = latest_reports.get(prefix) or {}
        summary = report.get("summary") if isinstance(report, dict) else None
        return summary if isinstance(summary, dict) else {}

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    manual_summary = report_summary("manual-reviewer-execution-packet")
    staging_summary = report_summary("public-repo-staging-status")
    source_ready = (
        manual_summary.get("status") == "ready-for-human-runbook"
        and manual_summary.get("manual_review_required") is True
        and manual_summary.get("human_feedback_pending") is True
        and manual_summary.get("one_page_runbook_ready") is True
        and manual_summary.get("executes_anything") is False
        and manual_summary.get("remote_mutation_allowed") is False
        and manual_summary.get("credential_validation_allowed") is False
        and manual_summary.get("auto_approves_release") is False
        and int(manual_summary.get("remote_issues_created", 0) or 0) == 0
        and manual_summary.get("issue_backlog_mutation_allowed") is False
    )
    add_check("source:manual-reviewer-execution-packet:ready", source_ready, str(manual_summary or "missing"))

    add_check("public-pack:latest-report", latest_reports.get("public-release-pack") is not None, str(reports_dir / "latest-public-release-pack.json"))
    add_check("public-pack:dir", pack_dir is not None and pack_dir.is_dir(), str(pack_dir) if pack_dir else "missing")
    add_check("public-pack:manual-reviewer-execution-packet-json", pack_dir is not None and (pack_dir / "bootstrap" / "reports" / "latest-manual-reviewer-execution-packet.json").is_file(), "bootstrap/reports/latest-manual-reviewer-execution-packet.json")
    add_check("public-pack:manual-reviewer-execution-packet-md", pack_dir is not None and (pack_dir / "bootstrap" / "reports" / "latest-manual-reviewer-execution-packet.md").is_file(), "bootstrap/reports/latest-manual-reviewer-execution-packet.md")
    add_check("public-pack:manual-reviewer-public-surface-freshness-command", tree_contains_text(pack_dir, "--manual-reviewer-public-surface-freshness", ["docs/open-source-release-plan.md", "docs/public-roadmap.md", "bootstrap/setup/bootstrap-ai-assets.sh"]), "public pack documents Phase 94 freshness command")

    add_check("github-staging:latest-status-report", latest_reports.get("public-repo-staging-status") is not None, str(reports_dir / "latest-public-repo-staging-status.json"))
    add_check("github-staging:dir", staging_dir.is_dir(), str(staging_dir))
    add_check("github-staging:manual-reviewer-execution-packet-json", (staging_dir / "bootstrap" / "reports" / "latest-manual-reviewer-execution-packet.json").is_file(), "bootstrap/reports/latest-manual-reviewer-execution-packet.json")
    add_check("github-staging:manual-reviewer-execution-packet-md", (staging_dir / "bootstrap" / "reports" / "latest-manual-reviewer-execution-packet.md").is_file(), "bootstrap/reports/latest-manual-reviewer-execution-packet.md")
    add_check("github-staging:manual-reviewer-public-surface-freshness-command", tree_contains_text(staging_dir, "--manual-reviewer-public-surface-freshness", ["docs/open-source-release-plan.md", "docs/public-roadmap.md", "bootstrap/setup/bootstrap-ai-assets.sh"]), "GitHub staging documents Phase 94 freshness command")

    release_plan = read_optional(root / "docs" / "open-source-release-plan.md")
    roadmap = read_optional(root / "docs" / "public-roadmap.md")
    shell_wrapper = read_optional(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase94_release_plan_ok = (
        "--manual-reviewer-public-surface-freshness --both" in release_plan
        and "local-only/report-only freshness and coverage check" in release_plan
        and "public pack and GitHub staging" in release_plan
        and "does not approve, publish, push, execute, call APIs/providers, validate credentials, or mutate issues/backlogs" in release_plan
    )
    add_check("docs:release-plan-documents-phase94", phase94_release_plan_ok, "docs/open-source-release-plan.md documents Phase 94 public surface freshness boundary")
    add_check("roadmap:phase94-documented", "### Phase 94 — Manual reviewer public surface freshness ✅" in roadmap and "Checks Phase 93 runbook coverage in public pack and staging without executing or publishing." in roadmap, "docs/public-roadmap.md documents Phase 94")
    add_check("shell:manual-reviewer-public-surface-freshness-command", "--manual-reviewer-public-surface-freshness" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 94 flag")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    forbidden_findings = int(staging_summary.get("forbidden_findings", 0) or 0)
    status = "blocked" if forbidden_findings else ("stale" if fail_count else "ready")

    return {
        "mode": "manual-reviewer-public-surface-freshness",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "pack_dir": str(pack_dir) if pack_dir else None,
        "staging_dir": str(staging_dir),
        "required_reports": required_reports,
        "source_summaries": {prefix: report_summary(prefix) for prefix in required_reports},
        "checks": checks,
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "forbidden_findings": forbidden_findings,
            "manual_review_required": True,
            "human_feedback_pending": bool(manual_summary.get("human_feedback_pending", True)),
            "followup_candidates_ready": bool(manual_summary.get("followup_candidates_ready", False)),
            "one_page_runbook_ready": bool(manual_summary.get("one_page_runbook_ready", False)),
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": bool(staging_summary.get("remote_configured", False)),
        },
        "review_boundary": [
            "Report-only freshness/coverage check for Phase 93 manual reviewer execution packet across local public pack, GitHub staging, docs, and shell surfaces.",
            "Does not create final human feedback, execute the human runbook, send invitations, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
            "A ready result means public surfaces include the runbook evidence and Phase 94 command wiring; it is not release approval, not a go/no-go decision, and not completion of human feedback.",
        ],
        "recommendations": [
            "Rerun --manual-reviewer-execution-packet --both after changing human-action closure or reviewer guidance.",
            "Rerun --public-release-pack --both and --public-repo-staging --both after changing docs, shell wrapper, or latest reviewer packet reports.",
            "Rerun --manual-reviewer-public-surface-freshness --both immediately before giving the local public pack/staging tree to a human reviewer.",
        ],
    }



def build_manual_reviewer_handoff_readiness_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only final human handoff digest for ready reviewer surfaces.

    This gate summarizes local public pack/staging/reviewer artifacts for a human
    operator. It does not share anything, send invitations, publish, push, execute
    commands, call providers/APIs, validate credentials, approve release, create
    feedback, or mutate issues/backlogs.
    """
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    required_reports = [
        "manual-reviewer-public-surface-freshness",
        "manual-reviewer-execution-packet",
        "human-action-closure-checklist",
    ]
    latest_reports = {prefix: _load_json_if_exists(reports_dir / f"latest-{prefix}.json") for prefix in required_reports}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def report_summary(prefix: str) -> Dict[str, Any]:
        report = latest_reports.get(prefix) or {}
        summary = report.get("summary") if isinstance(report, dict) else None
        return summary if isinstance(summary, dict) else {}

    freshness_report = latest_reports.get("manual-reviewer-public-surface-freshness") or {}
    freshness_summary = report_summary("manual-reviewer-public-surface-freshness")
    manual_summary = report_summary("manual-reviewer-execution-packet")
    checklist_summary = report_summary("human-action-closure-checklist")

    pack_dir_value = freshness_report.get("pack_dir") if isinstance(freshness_report, dict) else None
    staging_dir_value = freshness_report.get("staging_dir") if isinstance(freshness_report, dict) else None
    pack_dir = Path(pack_dir_value) if isinstance(pack_dir_value, str) else _latest_public_release_pack_dir(root)
    staging_dir = Path(staging_dir_value) if isinstance(staging_dir_value, str) else root / "dist" / "github-staging" / "portable-ai-assets"

    feedback_template = root / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md.template"
    execution_packet_md = reports_dir / "latest-manual-reviewer-execution-packet.md"
    freshness_md = reports_dir / "latest-manual-reviewer-public-surface-freshness.md"

    handoff_artifacts = [
        {"name": "public-release-pack", "path": str(pack_dir) if pack_dir else None, "ready": bool(pack_dir and pack_dir.is_dir())},
        {"name": "github-staging", "path": str(staging_dir), "ready": staging_dir.is_dir()},
        {"name": "manual-reviewer-execution-packet", "path": str(execution_packet_md), "ready": execution_packet_md.is_file()},
        {"name": "public-surface-freshness-report", "path": str(freshness_md), "ready": freshness_md.is_file()},
        {"name": "feedback-template", "path": str(feedback_template), "ready": feedback_template.is_file()},
    ]

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    freshness_ready = (
        freshness_summary.get("status") == "ready"
        and int(freshness_summary.get("fail", 0) or 0) == 0
        and freshness_summary.get("human_feedback_pending") is True
        and freshness_summary.get("executes_anything") is False
        and freshness_summary.get("remote_mutation_allowed") is False
        and freshness_summary.get("credential_validation_allowed") is False
        and freshness_summary.get("auto_approves_release") is False
        and int(freshness_summary.get("remote_issues_created", 0) or 0) == 0
        and freshness_summary.get("issue_backlog_mutation_allowed") is False
    )
    manual_ready = (
        manual_summary.get("status") == "ready-for-human-runbook"
        and manual_summary.get("human_feedback_pending") is True
        and manual_summary.get("one_page_runbook_ready") is True
        and manual_summary.get("executes_anything") is False
        and manual_summary.get("remote_mutation_allowed") is False
        and manual_summary.get("credential_validation_allowed") is False
        and manual_summary.get("auto_approves_release") is False
        and int(manual_summary.get("remote_issues_created", 0) or 0) == 0
        and manual_summary.get("issue_backlog_mutation_allowed") is False
    )
    checklist_ready = (
        checklist_summary.get("status") == "ready-for-human-action"
        and checklist_summary.get("human_feedback_pending") is True
        and checklist_summary.get("executes_anything") is False
        and checklist_summary.get("remote_mutation_allowed") is False
        and checklist_summary.get("credential_validation_allowed") is False
        and checklist_summary.get("auto_approves_release") is False
        and int(checklist_summary.get("remote_issues_created", 0) or 0) == 0
        and checklist_summary.get("issue_backlog_mutation_allowed") is False
    )

    add_check("source:manual-reviewer-public-surface-freshness:ready", freshness_ready, str(freshness_summary or "missing"))
    add_check("source:manual-reviewer-execution-packet:ready", manual_ready, str(manual_summary or "missing"))
    add_check("source:human-action-closure-checklist:ready", checklist_ready, str(checklist_summary or "missing"))
    for artifact in handoff_artifacts:
        add_check(f"artifact:{artifact['name']}", bool(artifact.get("ready")), str(artifact.get("path")))

    release_plan = read_optional(root / "docs" / "open-source-release-plan.md")
    roadmap = read_optional(root / "docs" / "public-roadmap.md")
    shell_wrapper = read_optional(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase95_release_plan_ok = (
        "--manual-reviewer-handoff-readiness --both" in release_plan
        and "local-only/report-only handoff readiness digest" in release_plan
        and "does not approve, share, invite, publish, push, execute, call APIs/providers, validate credentials, or mutate issues/backlogs" in release_plan
    )
    add_check("docs:release-plan-documents-phase95", phase95_release_plan_ok, "docs/open-source-release-plan.md documents Phase 95 handoff readiness boundary")
    add_check("roadmap:phase95-documented", "### Phase 95 — Manual reviewer handoff readiness ✅" in roadmap and "Summarizes the ready public reviewer surfaces for a human handoff without sharing, inviting, publishing, or approving." in roadmap, "docs/public-roadmap.md documents Phase 95")
    add_check("shell:manual-reviewer-handoff-readiness-command", "--manual-reviewer-handoff-readiness" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 95 flag")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready-for-human-handoff"

    return {
        "mode": "manual-reviewer-handoff-readiness",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "pack_dir": str(pack_dir) if pack_dir else None,
        "staging_dir": str(staging_dir),
        "required_reports": required_reports,
        "source_summaries": {prefix: report_summary(prefix) for prefix in required_reports},
        "handoff_artifacts": handoff_artifacts,
        "checks": checks,
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": bool(freshness_summary.get("remote_configured", False)),
        },
        "manual_handoff_sequence": [
            "Open the public release pack and GitHub staging tree locally.",
            "Read the manual reviewer execution packet and public surface freshness report.",
            "Copy/fill external-reviewer-feedback.md from the template only if a human reviewer is ready to provide feedback.",
            "Any sharing, invitation, publication, approval, go/no-go, or follow-up issue/backlog action remains manual and outside this gate.",
        ],
        "review_boundary": [
            "Report-only digest of local handoff readiness for human reviewer/operator use.",
            "Does not share artifacts, send invitations, create final feedback, execute the runbook, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
            "A ready-for-human-handoff result means the local surfaces are organized for a human; it is not release approval, not a go/no-go decision, and not completion of human feedback.",
        ],
        "recommendations": [
            "Rerun --manual-reviewer-public-surface-freshness --both immediately before this handoff readiness digest.",
            "Have a human operator decide if/when to share or invite external reviewers outside automation.",
            "After real human feedback is supplied, rerun feedback status and follow-up candidate gates locally.",
        ],
    }


def build_manual_reviewer_handoff_packet_index_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only human handoff packet index/status for manual reviewer operations.

    This gate cross-links the Phase 95 handoff readiness digest with exact
    human-only next actions and drift checks. It does not share artifacts, send
    invitations, publish, approve, execute commands, call APIs/providers,
    validate credentials, create feedback, or mutate issues/backlogs.
    """
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    handoff_report_path = reports_dir / "latest-manual-reviewer-handoff-readiness.json"
    handoff_report = _load_json_if_exists(handoff_report_path)
    handoff_summary = handoff_report.get("summary") if isinstance(handoff_report.get("summary"), dict) else {}
    handoff_artifacts = handoff_report.get("handoff_artifacts") if isinstance(handoff_report.get("handoff_artifacts"), list) else []

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def artifact_path(name: str, fallback: Path) -> Path:
        for artifact in handoff_artifacts:
            if isinstance(artifact, dict) and artifact.get("name") == name and isinstance(artifact.get("path"), str):
                return Path(str(artifact.get("path")))
        return fallback

    pack_dir = artifact_path("public-release-pack", _latest_public_release_pack_dir(root) or root / "dist" / "portable-ai-assets-public-missing")
    staging_dir = artifact_path("github-staging", root / "dist" / "github-staging" / "portable-ai-assets")
    execution_packet_md = artifact_path("manual-reviewer-execution-packet", reports_dir / "latest-manual-reviewer-execution-packet.md")
    freshness_md = artifact_path("public-surface-freshness-report", reports_dir / "latest-manual-reviewer-public-surface-freshness.md")
    phase102_rollup_diagnostics_md = artifact_path("phase102-rollup-diagnostics", staging_dir / "bootstrap" / "reports" / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md")
    completed_work_diagnostics_md = artifact_path("completed-work-diagnostics", staging_dir / "bootstrap" / "reports" / "latest-completed-work-review.md")
    feedback_template = artifact_path("feedback-template", root / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md.template")
    handoff_readiness_md = reports_dir / "latest-manual-reviewer-handoff-readiness.md"

    packet_index = [
        {"name": "handoff-readiness-digest", "path": str(handoff_readiness_md), "ready": handoff_readiness_md.is_file(), "review_role": "operator"},
        {"name": "public-release-pack", "path": str(pack_dir), "ready": pack_dir.is_dir(), "review_role": "operator/reviewer"},
        {"name": "github-staging", "path": str(staging_dir), "ready": staging_dir.is_dir(), "review_role": "operator/reviewer"},
        {"name": "phase102-rollup-diagnostics", "path": str(phase102_rollup_diagnostics_md), "ready": phase102_rollup_diagnostics_md.is_file(), "review_role": "operator/reviewer"},
        {"name": "completed-work-diagnostics", "path": str(completed_work_diagnostics_md), "ready": completed_work_diagnostics_md.is_file(), "review_role": "operator/reviewer"},
        {"name": "manual-reviewer-execution-packet", "path": str(execution_packet_md), "ready": execution_packet_md.is_file(), "review_role": "operator"},
        {"name": "public-surface-freshness-report", "path": str(freshness_md), "ready": freshness_md.is_file(), "review_role": "operator"},
        {"name": "feedback-template", "path": str(feedback_template), "ready": feedback_template.is_file(), "review_role": "reviewer"},
    ]

    human_only_next_actions = [
        {"id": "human-share-decision", "title": "Decide whether/when/how to share local public pack or staging tree", "automation_allowed": False, "requires_human": True},
        {"id": "human-reviewer-invitation", "title": "Decide whether/when/how to invite external reviewers", "automation_allowed": False, "requires_human": True},
        {"id": "human-feedback-capture", "title": "Copy/fill external-reviewer-feedback.md from the template only after real human review", "automation_allowed": False, "requires_human": True},
        {"id": "human-followup-review", "title": "Review any feedback-derived follow-up candidates before issue/backlog mutation", "automation_allowed": False, "requires_human": True},
        {"id": "human-release-go-no-go", "title": "Make any release approval, go/no-go, publication, push, tag, or release decision manually", "automation_allowed": False, "requires_human": True},
    ]

    drift_checks: List[Dict[str, str]] = []
    def add_drift_check(name: str, ok: bool, detail: str) -> None:
        drift_checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    handoff_ready = (
        handoff_summary.get("status") == "ready-for-human-handoff"
        and int(handoff_summary.get("fail", 0) or 0) == 0
        and handoff_summary.get("human_feedback_pending") is True
        and handoff_summary.get("shares_anything") is False
        and handoff_summary.get("sends_invitations") is False
        and handoff_summary.get("executes_anything") is False
        and handoff_summary.get("remote_mutation_allowed") is False
        and handoff_summary.get("credential_validation_allowed") is False
        and handoff_summary.get("auto_approves_release") is False
        and int(handoff_summary.get("remote_issues_created", 0) or 0) == 0
        and handoff_summary.get("issue_backlog_mutation_allowed") is False
    )
    add_drift_check("source:manual-reviewer-handoff-readiness:ready", handoff_ready, str(handoff_summary or "missing"))
    for item in packet_index:
        add_drift_check(f"packet:{item['name']}", bool(item.get("ready")), str(item.get("path")))
    add_drift_check("actions:human-only", all(action.get("automation_allowed") is False and action.get("requires_human") is True for action in human_only_next_actions), "all next actions require humans and forbid automation")

    release_plan = read_optional(root / "docs" / "open-source-release-plan.md")
    roadmap = read_optional(root / "docs" / "public-roadmap.md")
    shell_wrapper = read_optional(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase96_release_plan_ok = (
        "--manual-reviewer-handoff-packet-index --both" in release_plan
        and "local-only/report-only human handoff packet index/status" in release_plan
        and "without sharing, inviting, approving, publishing, executing, calling APIs/providers, validating credentials, or mutating issues/backlogs" in release_plan
    )
    add_drift_check("docs:release-plan-documents-phase96", phase96_release_plan_ok, "docs/open-source-release-plan.md documents Phase 96 packet index/status boundary")
    add_drift_check("roadmap:phase96-documented", "### Phase 96 — Manual reviewer handoff packet index ✅" in roadmap and "Cross-links the handoff readiness digest, public pack, staging tree, reviewer runbook, feedback template, and exact human-only next actions without sharing, inviting, publishing, or approving." in roadmap, "docs/public-roadmap.md documents Phase 96")
    add_drift_check("shell:manual-reviewer-handoff-packet-index-command", "--manual-reviewer-handoff-packet-index" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 96 flag")

    fail_count = sum(1 for check in drift_checks if check["status"] == "fail")
    pass_count = sum(1 for check in drift_checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready-for-human-handoff-packet"
    return {
        "mode": "manual-reviewer-handoff-packet-index",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "required_reports": ["manual-reviewer-handoff-readiness"],
        "source_summaries": {"manual-reviewer-handoff-readiness": handoff_summary},
        "packet_index": packet_index,
        "human_only_next_actions": human_only_next_actions,
        "drift_checks": drift_checks,
        "summary": {
            "status": status,
            "checks": len(drift_checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": bool(handoff_summary.get("remote_configured", False)),
        },
        "review_boundary": [
            "Report-only packet index/status for a human handoff; it only cross-links local artifacts and human-only actions.",
            "Does not share artifacts, send invitations, create final feedback, execute commands, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
            "A ready-for-human-handoff-packet result means the local packet index is navigable; it is not release approval, not a go/no-go decision, not an invitation, and not completion of human feedback.",
        ],
        "recommendations": [
            "Rerun --manual-reviewer-handoff-readiness --both immediately before this packet index/status gate.",
            "Have a human operator decide if/when to share local artifacts or invite reviewers outside automation.",
            "After real human feedback exists, rerun feedback status and follow-up candidate gates locally.",
        ],
    }


def build_manual_reviewer_handoff_freeze_check_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only freeze check for the manual reviewer handoff packet.

    This gate verifies that the packet index is still ready and all indexed local
    artifacts are present for a human handoff. It does not share, invite,
    approve, publish, execute commands, call APIs/providers, validate
    credentials, create feedback, or mutate issues/backlogs.
    """
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    packet_path = reports_dir / "latest-manual-reviewer-handoff-packet-index.json"
    packet_report = _load_json_if_exists(packet_path)
    packet_summary = packet_report.get("summary") if isinstance(packet_report.get("summary"), dict) else {}
    packet_index = packet_report.get("packet_index") if isinstance(packet_report.get("packet_index"), list) else []
    human_actions = packet_report.get("human_only_next_actions") if isinstance(packet_report.get("human_only_next_actions"), list) else []

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    freeze_checks: List[Dict[str, str]] = []
    def add_freeze_check(name: str, ok: bool, detail: str) -> None:
        freeze_checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    packet_ready = (
        packet_summary.get("status") == "ready-for-human-handoff-packet"
        and int(packet_summary.get("fail", 0) or 0) == 0
        and packet_summary.get("human_feedback_pending") is True
        and packet_summary.get("shares_anything") is False
        and packet_summary.get("sends_invitations") is False
        and packet_summary.get("writes_anything") is False
        and int(packet_summary.get("writes", 0) or 0) == 0
        and packet_summary.get("executes_anything") is False
        and packet_summary.get("remote_mutation_allowed") is False
        and packet_summary.get("credential_validation_allowed") is False
        and packet_summary.get("auto_approves_release") is False
        and int(packet_summary.get("remote_issues_created", 0) or 0) == 0
        and packet_summary.get("issue_backlog_mutation_allowed") is False
    )
    add_freeze_check("source:manual-reviewer-handoff-packet-index:frozen", packet_ready, str(packet_summary or "missing"))

    frozen_packet_entries: List[Dict[str, Any]] = []
    for item in packet_index:
        if not isinstance(item, dict):
            continue
        raw_path = item.get("path")
        path = Path(str(raw_path)) if isinstance(raw_path, str) and raw_path else root / ".missing-packet-entry"
        present = path.is_file() if path.suffix else path.is_dir()
        frozen_packet_entries.append({
            "name": item.get("name"),
            "path": str(path),
            "present": present,
            "ready_in_packet_index": item.get("ready") is True,
            "review_role": item.get("review_role"),
        })
    all_entries_present = bool(frozen_packet_entries) and all(entry["present"] and entry["ready_in_packet_index"] for entry in frozen_packet_entries)
    add_freeze_check("packet:all-indexed-artifacts-present", all_entries_present, f"entries={len(frozen_packet_entries)}")

    entries_by_name = {str(entry.get("name")): entry for entry in frozen_packet_entries}
    expected_diagnostics = {
        "phase102-rollup-diagnostics": root / "dist" / "github-staging" / "portable-ai-assets" / "bootstrap" / "reports" / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md",
        "completed-work-diagnostics": root / "dist" / "github-staging" / "portable-ai-assets" / "bootstrap" / "reports" / "latest-completed-work-review.md",
    }
    diagnostic_entry_counts: Dict[str, int] = {name: 0 for name in expected_diagnostics}
    for entry in frozen_packet_entries:
        name = str(entry.get("name"))
        if name in diagnostic_entry_counts:
            diagnostic_entry_counts[name] += 1
    duplicate_diagnostic_entries = sorted(name for name, count in diagnostic_entry_counts.items() if count > 1)
    add_freeze_check(
        "diagnostics:no-duplicate-diagnostic-entries",
        not duplicate_diagnostic_entries,
        "duplicates=" + (",".join(duplicate_diagnostic_entries) if duplicate_diagnostic_entries else "none"),
    )
    diagnostic_tokens_by_name = {
        "phase102-rollup-diagnostics": ["phase102_report_invalid_fields", "invalid_fields="],
        "completed-work-diagnostics": ["invalid_fields="],
    }
    diagnostic_freeze_entries: List[Dict[str, Any]] = []
    diagnostic_freeze_failures: List[Dict[str, Any]] = []
    for name, expected_path in expected_diagnostics.items():
        entry = entries_by_name.get(name, {})
        path = Path(str(entry.get("path"))) if entry.get("path") else root / ".missing-diagnostic-entry"
        text = read_optional(path)
        path_matches = path.resolve() == expected_path.resolve()
        required_tokens = diagnostic_tokens_by_name[name]
        missing_tokens = [token for token in required_tokens if token not in text]
        present = path.is_file()
        ready_in_packet_index = entry.get("ready_in_packet_index") is True
        content_tokens_present = present and not missing_tokens
        if not path_matches:
            diagnostic_freeze_failures.append({"name": name, "reason": "path_mismatch", "path": str(path), "expected_path": str(expected_path)})
        if not present:
            diagnostic_freeze_failures.append({"name": name, "reason": "missing_file", "path": str(path)})
        if not ready_in_packet_index:
            diagnostic_freeze_failures.append({"name": name, "reason": "not_ready", "path": str(path)})
        if missing_tokens:
            diagnostic_freeze_failures.append({"name": name, "reason": "missing_tokens", "path": str(path), "missing_tokens": missing_tokens})
        diagnostic_freeze_entries.append({
            "name": name,
            "path": str(path),
            "expected_path": str(expected_path),
            "path_matches_expected": path_matches,
            "present": present,
            "ready_in_packet_index": ready_in_packet_index,
            "content_tokens_present": content_tokens_present,
            "required_tokens": required_tokens,
            "missing_tokens": missing_tokens,
        })
        add_freeze_check(
            f"diagnostics:{name.replace('-diagnostics', '')}-content-frozen",
            path_matches and path.is_file() and entry.get("ready_in_packet_index") is True and content_tokens_present,
            str(path),
        )
    diagnostics_frozen = bool(diagnostic_freeze_entries) and all(
        entry["path_matches_expected"] and entry["present"] and entry["ready_in_packet_index"] and entry["content_tokens_present"]
        for entry in diagnostic_freeze_entries
    )
    add_freeze_check("diagnostics:all-required-diagnostics-frozen", diagnostics_frozen, f"entries={len(diagnostic_freeze_entries)}")

    actions_human_only = bool(human_actions) and all(isinstance(action, dict) and action.get("automation_allowed") is False and action.get("requires_human") is True for action in human_actions)
    action_ids = {str(action.get("id")) for action in human_actions if isinstance(action, dict)}
    required_action_ids = {"human-share-decision", "human-reviewer-invitation", "human-feedback-capture", "human-followup-review", "human-release-go-no-go"}
    add_freeze_check("actions:human-only-freeze", actions_human_only and required_action_ids.issubset(action_ids), "all required human-only actions remain manual")

    release_plan = read_optional(root / "docs" / "open-source-release-plan.md")
    roadmap = read_optional(root / "docs" / "public-roadmap.md")
    shell_wrapper = read_optional(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase97_release_plan_ok = (
        "--manual-reviewer-handoff-freeze-check --both" in release_plan
        and "local-only/report-only handoff freeze check" in release_plan
        and "without sharing, inviting, approving, publishing, executing, calling APIs/providers, validating credentials, creating feedback, or mutating issues/backlogs" in release_plan
    )
    add_freeze_check("docs:release-plan-documents-phase97", phase97_release_plan_ok, "docs/open-source-release-plan.md documents Phase 97 freeze boundary")
    add_freeze_check("roadmap:phase97-documented", "### Phase 97 — Manual reviewer handoff freeze check ✅" in roadmap and "Verifies the handoff packet index, local artifact pointers, and human-only next actions are frozen and navigable without sharing, inviting, publishing, approving, or creating feedback." in roadmap, "docs/public-roadmap.md documents Phase 97")
    add_freeze_check("shell:manual-reviewer-handoff-freeze-check-command", "--manual-reviewer-handoff-freeze-check" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 97 flag")

    fail_count = sum(1 for check in freeze_checks if check["status"] == "fail")
    pass_count = sum(1 for check in freeze_checks if check["status"] == "pass")
    status = "blocked" if fail_count else "frozen-for-human-handoff"
    return {
        "mode": "manual-reviewer-handoff-freeze-check",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "required_reports": ["manual-reviewer-handoff-packet-index"],
        "source_summaries": {"manual-reviewer-handoff-packet-index": packet_summary},
        "frozen_packet_entries": frozen_packet_entries,
        "diagnostic_freeze_entries": diagnostic_freeze_entries,
        "diagnostic_freeze_failures": diagnostic_freeze_failures,
        "duplicate_diagnostic_entries": duplicate_diagnostic_entries,
        "human_only_next_actions": human_actions,
        "freeze_checks": freeze_checks,
        "summary": {
            "status": status,
            "checks": len(freeze_checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": bool(packet_summary.get("remote_configured", False)),
        },
        "review_boundary": [
            "Report-only freeze check for the local manual reviewer handoff packet.",
            "Verifies packet index readiness, indexed artifact presence, docs/roadmap/shell wiring, and human-only action boundaries.",
            "Does not share artifacts, send invitations, create final feedback, execute commands, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
            "A frozen-for-human-handoff result means the local packet is stable enough for a human to inspect; it is not release approval, not a go/no-go decision, not an invitation, not publication, and not completion of human feedback.",
        ],
        "recommendations": [
            "Rerun --manual-reviewer-handoff-packet-index --both immediately before this freeze check.",
            "If any indexed artifact changes, rerun the public pack/staging/freshness/readiness/index chain before human sharing.",
            "Have a human decide whether and how to share or invite reviewers outside automation.",
        ],
    }


def build_agent_owner_delegation_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only agent-side owner delegation review.

    The user delegated engineering/code review, verification, and implementation
    decisions to the agent by default. This gate records the internal review
    responsibilities the agent owns while preserving the external side-effect
    boundary: no sharing, invitations, publication, feedback fabrication,
    credential validation, provider/API calls, command execution, or issue/backlog
    mutation.
    """
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    freeze_path = reports_dir / "latest-manual-reviewer-handoff-freeze-check.json"
    freeze_report = _load_json_if_exists(freeze_path)
    freeze_summary = freeze_report.get("summary") if isinstance(freeze_report.get("summary"), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    delegated_agent_responsibilities = [
        {"area": "engineering-review", "owner": "agent", "requires_user_code_review": False, "description": "Agent owns implementation review, safety invariants, and regression checks before asking for external owner decisions."},
        {"area": "code-review", "owner": "agent", "requires_user_code_review": False, "description": "Agent may use independent subagents/fresh contexts for code review instead of requiring user code review."},
        {"area": "verification", "owner": "agent", "requires_user_code_review": False, "description": "Agent owns TDD, target tests, module tests, full suite, public gate chain, and local report inspection."},
        {"area": "product-material-review", "owner": "agent", "requires_user_code_review": False, "description": "Agent owns docs/roadmap/release material self-review and consistency checks within local non-mutating boundaries."},
    ]
    reserved_owner_external_decisions = [
        {"area": "real-sharing", "reserved_for": "owner", "automation_allowed": False, "description": "Whether/where/how to share artifacts with real people or services."},
        {"area": "reviewer-invitation", "reserved_for": "owner", "automation_allowed": False, "description": "Inviting named external reviewers or sending messages outside the local repo."},
        {"area": "publication", "reserved_for": "owner", "automation_allowed": False, "description": "Creating remotes/repos/tags/releases, pushing, publishing, or uploading artifacts."},
        {"area": "external-feedback-authorship", "reserved_for": "real-human-reviewer", "automation_allowed": False, "description": "Final external reviewer feedback must come from a real human and cannot be fabricated by automation."},
        {"area": "final-go-no-go", "reserved_for": "owner", "automation_allowed": False, "description": "Final release approval/go-no-go remains an explicit owner decision."},
    ]

    delegation_checks: List[Dict[str, str]] = []
    def add_check(name: str, ok: bool, detail: str) -> None:
        delegation_checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    freeze_ready = (
        freeze_summary.get("status") == "frozen-for-human-handoff"
        and int(freeze_summary.get("fail", 0) or 0) == 0
        and freeze_summary.get("human_feedback_pending") is True
        and freeze_summary.get("shares_anything") is False
        and freeze_summary.get("sends_invitations") is False
        and freeze_summary.get("writes_anything") is False
        and int(freeze_summary.get("writes", 0) or 0) == 0
        and freeze_summary.get("executes_anything") is False
        and freeze_summary.get("remote_mutation_allowed") is False
        and freeze_summary.get("credential_validation_allowed") is False
        and freeze_summary.get("auto_approves_release") is False
        and int(freeze_summary.get("remote_issues_created", 0) or 0) == 0
        and freeze_summary.get("issue_backlog_mutation_allowed") is False
    )
    add_check("source:manual-reviewer-handoff-freeze-check:frozen", freeze_ready, str(freeze_summary or "missing"))
    add_check("delegation:agent-internal-review-owned", all(item.get("owner") == "agent" and item.get("requires_user_code_review") is False for item in delegated_agent_responsibilities), "engineering/code/verification/material review delegated to agent")
    add_check("boundary:external-owner-decisions-reserved", all(item.get("automation_allowed") is False for item in reserved_owner_external_decisions), "real sharing/invitation/publication/feedback/go-no-go remain external decisions")

    release_plan = read_optional(root / "docs" / "open-source-release-plan.md")
    roadmap = read_optional(root / "docs" / "public-roadmap.md")
    shell_wrapper = read_optional(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase98_release_plan_ok = (
        "--agent-owner-delegation-review --both" in release_plan
        and "local-only/report-only agent-side owner delegation review" in release_plan
        and "without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs" in release_plan
    )
    add_check("docs:release-plan-documents-phase98", phase98_release_plan_ok, "docs/open-source-release-plan.md documents Phase 98 delegation boundary")
    add_check("roadmap:phase98-documented", "### Phase 98 — Agent owner delegation review ✅" in roadmap and "Records that engineering/code review and verification are delegated to the agent while real external sharing, reviewer invitation, publication, feedback authorship, and final go/no-go remain explicit owner-side external decisions." in roadmap, "docs/public-roadmap.md documents Phase 98")
    add_check("shell:agent-owner-delegation-review-command", "--agent-owner-delegation-review" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 98 flag")

    fail_count = sum(1 for check in delegation_checks if check["status"] == "fail")
    pass_count = sum(1 for check in delegation_checks if check["status"] == "pass")
    status = "blocked" if fail_count else "agent-review-delegated"
    return {
        "mode": "agent-owner-delegation-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "required_reports": ["manual-reviewer-handoff-freeze-check"],
        "source_summaries": {"manual-reviewer-handoff-freeze-check": freeze_summary},
        "delegated_agent_responsibilities": delegated_agent_responsibilities,
        "reserved_owner_external_decisions": reserved_owner_external_decisions,
        "delegation_checks": delegation_checks,
        "summary": {
            "status": status,
            "checks": len(delegation_checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "agent_engineering_review_delegated": True,
            "agent_code_review_delegated": True,
            "agent_verification_delegated": True,
            "agent_product_material_review_delegated": True,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": bool(freeze_summary.get("remote_configured", False)),
        },
        "review_boundary": [
            "Agent owns internal engineering review, code review, verification, and product-material consistency checks by default.",
            "User code review is not required for machine-side progress; use independent agent review/fresh contexts when needed.",
            "External side effects remain reserved: real sharing, reviewer invitations, publication, uploads, remote/repo/tag/release creation, final external feedback authorship, and final go/no-go.",
            "Does not share artifacts, send invitations, create final feedback, execute commands, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
        ],
        "recommendations": [
            "Continue agent-side review/verification without asking the user to inspect code unless a true owner/external decision is needed.",
            "Use independent subagent review for code-quality/security verification before any commit/publish request.",
            "Ask the user only before real external sharing, invitations, publication, credential/API use, or final go/no-go.",
        ],
    }


def build_agent_complete_external_actions_reserved_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Final local rollup: agent-side complete, external actions reserved.

    This report-only gate consumes the Phase 98 delegation review and summarizes
    that machine-side/agent-side work is complete while real sharing,
    invitations, publication, external feedback authorship, and final go/no-go
    remain explicit external owner decisions.
    """
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    delegation_path = reports_dir / "latest-agent-owner-delegation-review.json"
    delegation_report = _load_json_if_exists(delegation_path)
    delegation_summary = delegation_report.get("summary") if isinstance(delegation_report.get("summary"), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    reserved_external_actions = [
        {"area": "real-sharing", "automation_allowed": False, "requires_explicit_owner_decision": True},
        {"area": "reviewer-invitation", "automation_allowed": False, "requires_explicit_owner_decision": True},
        {"area": "publication", "automation_allowed": False, "requires_explicit_owner_decision": True},
        {"area": "external-feedback-authorship", "automation_allowed": False, "requires_explicit_owner_decision": True},
        {"area": "final-go-no-go", "automation_allowed": False, "requires_explicit_owner_decision": True},
    ]
    completed_agent_surfaces = [
        {"area": "engineering-review", "status": "delegated-to-agent"},
        {"area": "code-review", "status": "delegated-to-agent"},
        {"area": "verification", "status": "delegated-to-agent"},
        {"area": "product-material-review", "status": "delegated-to-agent"},
        {"area": "handoff-packet", "status": "frozen"},
    ]

    rollup_checks: List[Dict[str, str]] = []
    def add_check(name: str, ok: bool, detail: str) -> None:
        rollup_checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    def int_or_none(value: object) -> Optional[int]:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        return None

    delegation_fail_count = int_or_none(delegation_summary.get("fail", 0))
    delegation_writes = int_or_none(delegation_summary.get("writes", 0))
    delegation_remote_issues_created = int_or_none(delegation_summary.get("remote_issues_created", 0))
    delegation_ready = (
        delegation_summary.get("status") == "agent-review-delegated"
        and delegation_fail_count == 0
        and delegation_summary.get("agent_engineering_review_delegated") is True
        and delegation_summary.get("agent_code_review_delegated") is True
        and delegation_summary.get("agent_verification_delegated") is True
        and delegation_summary.get("agent_product_material_review_delegated") is True
        and delegation_summary.get("requires_user_code_review") is False
        and delegation_summary.get("external_owner_decision_required") is True
        and delegation_summary.get("human_feedback_pending") is True
        and delegation_summary.get("shares_anything") is False
        and delegation_summary.get("sends_invitations") is False
        and delegation_summary.get("writes_anything") is False
        and delegation_writes == 0
        and delegation_summary.get("executes_anything") is False
        and delegation_summary.get("remote_mutation_allowed") is False
        and delegation_summary.get("credential_validation_allowed") is False
        and delegation_summary.get("auto_approves_release") is False
        and delegation_remote_issues_created == 0
        and delegation_summary.get("issue_backlog_mutation_allowed") is False
    )
    add_check("source:agent-owner-delegation-review:delegated", delegation_ready, str(delegation_summary or "missing"))
    add_check("completion:agent-side-complete", all(item.get("status") in {"delegated-to-agent", "frozen"} for item in completed_agent_surfaces), "agent-owned engineering/code/verification/material review surfaces complete")
    add_check("boundary:external-actions-reserved", all(item.get("automation_allowed") is False and item.get("requires_explicit_owner_decision") is True for item in reserved_external_actions), "all real external actions remain owner-reserved")

    release_plan = read_optional(root / "docs" / "open-source-release-plan.md")
    roadmap = read_optional(root / "docs" / "public-roadmap.md")
    shell_wrapper = read_optional(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase99_release_plan_ok = (
        "--agent-complete-external-actions-reserved --both" in release_plan
        and "local-only/report-only agent-complete external-actions-reserved final rollup" in release_plan
        and "without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs" in release_plan
    )
    add_check("docs:release-plan-documents-phase99", phase99_release_plan_ok, "docs/open-source-release-plan.md documents Phase 99 final rollup boundary")
    add_check("roadmap:phase99-documented", "### Phase 99 — Agent-complete external-actions-reserved rollup ✅" in roadmap and "Summarizes the final machine-side state as agent-complete while reserving real sharing, reviewer invitation, publication, external feedback authorship, and final go/no-go for explicit external owner decisions." in roadmap, "docs/public-roadmap.md documents Phase 99")
    add_check("shell:agent-complete-external-actions-reserved-command", "--agent-complete-external-actions-reserved" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 99 flag")

    fail_count = sum(1 for check in rollup_checks if check["status"] == "fail")
    pass_count = sum(1 for check in rollup_checks if check["status"] == "pass")
    agent_side_complete = fail_count == 0 and delegation_ready
    machine_side_complete = agent_side_complete
    status = "agent-complete-external-actions-reserved" if agent_side_complete else "blocked"
    return {
        "mode": "agent-complete-external-actions-reserved",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "required_reports": ["agent-owner-delegation-review"],
        "source_summaries": {"agent-owner-delegation-review": delegation_summary},
        "completed_agent_surfaces": completed_agent_surfaces,
        "reserved_external_actions": reserved_external_actions,
        "rollup_checks": rollup_checks,
        "summary": {
            "status": status,
            "checks": len(rollup_checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "agent_side_complete": agent_side_complete,
            "machine_side_complete": machine_side_complete,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": delegation_summary.get("remote_configured") is True,
        },
        "review_boundary": [
            "Machine-side and agent-side review/verification work is complete for the current local handoff path.",
            "External actions remain owner-reserved: real sharing, reviewer invitations, publication/upload/push/tag/release/remote creation, external feedback authorship, and final go/no-go.",
            "Does not share artifacts, send invitations, create final feedback, execute commands, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
        ],
        "recommendations": [
            "Continue internal agent verification as needed without requiring user code review.",
            "Ask the user only when a real external target/action is needed.",
            "If the owner authorizes an external action later, create a narrow action-specific plan/template rather than executing implicitly.",
        ],
    }


def _read_text_if_exists(path: Path) -> str:
    try:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _agent_complete_failclosed_regression_requirements() -> List[Tuple[str, str, str]]:
    return [
        ("missing-delegation-source-blocks-completion", "test_agent_complete_rollup_blocks_completion_booleans_when_delegation_missing", "blocked status and completion booleans false"),
        ("malformed-fail-blocks-without-crash", "test_agent_complete_rollup_blocks_malformed_delegation_summary_without_crashing", "blocked status without ValueError"),
        ("malformed-writes-blocks-without-crash", "test_agent_complete_rollup_blocks_malformed_writes_without_crashing", "blocked status without ValueError"),
        ("malformed-remote-issues-blocks-without-crash", "test_agent_complete_rollup_blocks_malformed_remote_issues_without_crashing", "blocked status without ValueError"),
    ]


def _definition_backed_regression_coverage(test_text: str) -> List[Dict[str, Any]]:
    try:
        tree = ast.parse(test_text or "")
        function_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    except SyntaxError:
        function_names = set()
    coverage: List[Dict[str, Any]] = []
    for scenario, test_name, expected in _agent_complete_failclosed_regression_requirements():
        covered = test_name in function_names
        coverage.append({
            "scenario": scenario,
            "test_name": test_name,
            "covered": covered,
            "expected": expected,
            "evidence_kind": "test-function-definition",
        })
    return coverage


def build_agent_complete_failclosed_hardening_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only fail-closed hardening review for the agent-complete rollup."""
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    rollup_report = _load_json_if_exists(reports_dir / "latest-agent-complete-external-actions-reserved.json")
    rollup_summary = rollup_report.get("summary") if isinstance(rollup_report.get("summary"), dict) else {}

    test_file = root / "tests" / "test_bootstrap_phase4.py"
    test_text = _read_text_if_exists(test_file)
    failclosed_regression_coverage = _definition_backed_regression_coverage(test_text)
    hardening_checks: List[Dict[str, str]] = []
    def add_check(name: str, ok: bool, detail: str) -> None:
        hardening_checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    rollup_ready = (
        rollup_summary.get("status") == "agent-complete-external-actions-reserved"
        and rollup_summary.get("agent_side_complete") is True
        and rollup_summary.get("machine_side_complete") is True
        and rollup_summary.get("requires_user_code_review") is False
        and rollup_summary.get("external_owner_decision_required") is True
        and rollup_summary.get("human_feedback_pending") is True
        and rollup_summary.get("shares_anything") is False
        and rollup_summary.get("sends_invitations") is False
        and rollup_summary.get("writes_anything") is False
        and rollup_summary.get("writes") == 0
        and rollup_summary.get("executes_anything") is False
        and rollup_summary.get("remote_mutation_allowed") is False
        and rollup_summary.get("credential_validation_allowed") is False
        and rollup_summary.get("auto_approves_release") is False
        and rollup_summary.get("remote_issues_created") == 0
        and rollup_summary.get("issue_backlog_mutation_allowed") is False
    )
    add_check("source:agent-complete-external-actions-reserved:complete", rollup_ready, str(rollup_summary or "missing"))
    coverage_ready = all(item.get("covered") is True for item in failclosed_regression_coverage)
    add_check("coverage:failclosed-regressions-present", coverage_ready, "missing source, malformed fail, malformed writes, malformed remote issues")

    release_plan = _read_text_if_exists(root / "docs" / "open-source-release-plan.md")
    roadmap = _read_text_if_exists(root / "docs" / "public-roadmap.md")
    shell_wrapper = _read_text_if_exists(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase100_release_plan_ok = (
        "--agent-complete-failclosed-hardening-review --both" in release_plan
        and "local-only/report-only fail-closed hardening review" in release_plan
        and "without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs" in release_plan
    )
    add_check("docs:release-plan-documents-phase100", phase100_release_plan_ok, "docs/open-source-release-plan.md documents Phase 100 fail-closed boundary")
    add_check("roadmap:phase100-documented", "### Phase 100 — Agent-complete fail-closed hardening review ✅" in roadmap and "Tracks fail-closed regression coverage for the agent-complete rollup, including missing source evidence and malformed numeric upstream fields, while preserving the external-actions-reserved boundary." in roadmap, "docs/public-roadmap.md documents Phase 100")
    add_check("shell:agent-complete-failclosed-hardening-review-command", "--agent-complete-failclosed-hardening-review" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 100 flag")

    fail_count = sum(1 for check in hardening_checks if check["status"] == "fail")
    pass_count = sum(1 for check in hardening_checks if check["status"] == "pass")
    failclosed_regressions_covered = fail_count == 0 and coverage_ready and rollup_ready
    status = "failclosed-hardened" if failclosed_regressions_covered else "blocked"
    return {
        "mode": "agent-complete-failclosed-hardening-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "required_reports": ["agent-complete-external-actions-reserved"],
        "source_summaries": {"agent-complete-external-actions-reserved": rollup_summary},
        "failclosed_regression_coverage": failclosed_regression_coverage,
        "hardening_checks": hardening_checks,
        "summary": {
            "status": status,
            "checks": len(hardening_checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "agent_side_complete": failclosed_regressions_covered,
            "machine_side_complete": failclosed_regressions_covered,
            "failclosed_regressions_covered": failclosed_regressions_covered,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": rollup_summary.get("remote_configured") is True,
        },
        "review_boundary": [
            "Report-only hardening review for the agent-complete rollup's fail-closed behavior.",
            "Confirms blocked/malformed source evidence cannot claim completion or crash the rollup path.",
            "Does not share artifacts, send invitations, create final feedback, execute commands, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
        ],
        "recommendations": [
            "Keep adding fail-closed regression tests whenever independent review finds a malformed-source or blocked-state gap.",
            "Ask the user only for real external target/action authorization.",
        ],
    }

def build_agent_complete_regression_evidence_integrity_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only integrity audit requiring Phase 100 regression evidence to be real test definitions."""
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    phase100_report = _load_json_if_exists(reports_dir / "latest-agent-complete-failclosed-hardening-review.json")
    phase100_summary = phase100_report.get("summary") if isinstance(phase100_report.get("summary"), dict) else {}
    test_text = _read_text_if_exists(root / "tests" / "test_bootstrap_phase4.py")
    regression_evidence = _definition_backed_regression_coverage(test_text)

    integrity_checks: List[Dict[str, str]] = []
    def add_check(name: str, ok: bool, detail: str) -> None:
        integrity_checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    phase100_ready = (
        phase100_summary.get("status") == "failclosed-hardened"
        and phase100_summary.get("agent_side_complete") is True
        and phase100_summary.get("machine_side_complete") is True
        and phase100_summary.get("failclosed_regressions_covered") is True
        and phase100_summary.get("requires_user_code_review") is False
        and phase100_summary.get("external_owner_decision_required") is True
        and phase100_summary.get("human_feedback_pending") is True
        and phase100_summary.get("shares_anything") is False
        and phase100_summary.get("sends_invitations") is False
        and phase100_summary.get("writes_anything") is False
        and phase100_summary.get("writes") == 0
        and phase100_summary.get("executes_anything") is False
        and phase100_summary.get("remote_mutation_allowed") is False
        and phase100_summary.get("credential_validation_allowed") is False
        and phase100_summary.get("auto_approves_release") is False
        and phase100_summary.get("remote_issues_created") == 0
        and phase100_summary.get("issue_backlog_mutation_allowed") is False
    )
    add_check("source:agent-complete-failclosed-hardening-review:complete", phase100_ready, str(phase100_summary or "missing"))
    coverage_ready = all(item.get("covered") is True and item.get("evidence_kind") == "test-function-definition" for item in regression_evidence)
    add_check("coverage:test-function-definitions-present", coverage_ready, "requires def-backed tests, not comments or string mentions")

    release_plan = _read_text_if_exists(root / "docs" / "open-source-release-plan.md")
    roadmap = _read_text_if_exists(root / "docs" / "public-roadmap.md")
    shell_wrapper = _read_text_if_exists(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase101_release_plan_ok = (
        "--agent-complete-regression-evidence-integrity --both" in release_plan
        and "local-only/report-only regression evidence integrity audit" in release_plan
        and "without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs" in release_plan
    )
    add_check("docs:release-plan-documents-phase101", phase101_release_plan_ok, "docs/open-source-release-plan.md documents Phase 101 definition-backed evidence boundary")
    add_check("roadmap:phase101-documented", "### Phase 101 — Agent-complete regression evidence integrity ✅" in roadmap and "Confirms Phase 100 regression coverage is backed by actual test function definitions rather than comments or string mentions while preserving the external-actions-reserved boundary." in roadmap, "docs/public-roadmap.md documents Phase 101")
    add_check("shell:agent-complete-regression-evidence-integrity-command", "--agent-complete-regression-evidence-integrity" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 101 flag")

    fail_count = sum(1 for check in integrity_checks if check["status"] == "fail")
    pass_count = sum(1 for check in integrity_checks if check["status"] == "pass")
    definition_backed_regressions_covered = fail_count == 0 and phase100_ready and coverage_ready
    status = "definition-backed" if definition_backed_regressions_covered else "blocked"
    return {
        "mode": "agent-complete-regression-evidence-integrity",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "required_reports": ["agent-complete-failclosed-hardening-review"],
        "source_summaries": {"agent-complete-failclosed-hardening-review": phase100_summary},
        "regression_evidence": regression_evidence,
        "integrity_checks": integrity_checks,
        "summary": {
            "status": status,
            "checks": len(integrity_checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "agent_side_complete": definition_backed_regressions_covered,
            "machine_side_complete": definition_backed_regressions_covered,
            "definition_backed_regressions_covered": definition_backed_regressions_covered,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": phase100_summary.get("remote_configured") is True,
        },
        "review_boundary": [
            "Report-only integrity audit for Phase 100 fail-closed regression evidence.",
            "Confirms required regression coverage is backed by test function definitions, not comments or string mentions.",
            "Does not share artifacts, send invitations, create final feedback, execute commands, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
        ],
        "recommendations": [
            "Keep regression evidence definition-backed whenever future hardening coverage is added.",
            "Ask the user only for real external target/action authorization.",
        ],
    }


def build_agent_complete_syntax_invalid_evidence_failclosed_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only fail-closed review proving syntax-invalid evidence cannot claim completion."""
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    phase101_report = _load_json_if_exists(reports_dir / "latest-agent-complete-regression-evidence-integrity.json")
    phase101_summary = phase101_report.get("summary") if isinstance(phase101_report.get("summary"), dict) else {}
    syntax_invalid_fixture = (
        "def test_agent_complete_rollup_blocks_completion_booleans_when_delegation_missing(self):\n"
        "    pass\n"
        "def test_agent_complete_rollup_blocks_malformed_delegation_summary_without_crashing(self)\n"
        "    pass\n"
    )
    try:
        ast.parse(syntax_invalid_fixture)
        syntax_invalid = False
    except SyntaxError:
        syntax_invalid = True
    syntax_invalid_regression_evidence = _definition_backed_regression_coverage(syntax_invalid_fixture)

    syntax_invalid_checks: List[Dict[str, str]] = []
    def add_check(name: str, ok: bool, detail: str) -> None:
        syntax_invalid_checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    phase101_ready = (
        phase101_summary.get("status") == "definition-backed"
        and phase101_summary.get("agent_side_complete") is True
        and phase101_summary.get("machine_side_complete") is True
        and phase101_summary.get("definition_backed_regressions_covered") is True
        and phase101_summary.get("requires_user_code_review") is False
        and phase101_summary.get("external_owner_decision_required") is True
        and phase101_summary.get("human_feedback_pending") is True
        and phase101_summary.get("shares_anything") is False
        and phase101_summary.get("sends_invitations") is False
        and phase101_summary.get("writes_anything") is False
        and phase101_summary.get("writes") == 0
        and phase101_summary.get("executes_anything") is False
        and phase101_summary.get("remote_mutation_allowed") is False
        and phase101_summary.get("credential_validation_allowed") is False
        and phase101_summary.get("auto_approves_release") is False
        and phase101_summary.get("remote_issues_created") == 0
        and phase101_summary.get("issue_backlog_mutation_allowed") is False
    )
    add_check("source:agent-complete-regression-evidence-integrity:complete", phase101_ready, str(phase101_summary or "missing"))
    coverage_failclosed = syntax_invalid and all(item.get("covered") is False for item in syntax_invalid_regression_evidence)
    add_check("syntax-invalid:coverage-failclosed", coverage_failclosed, "syntax-invalid test evidence must yield no definition-backed coverage")

    release_plan = _read_text_if_exists(root / "docs" / "open-source-release-plan.md")
    roadmap = _read_text_if_exists(root / "docs" / "public-roadmap.md")
    shell_wrapper = _read_text_if_exists(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase102_release_plan_ok = (
        "--agent-complete-syntax-invalid-evidence-failclosed-review --both" in release_plan
        and "local-only/report-only syntax-invalid evidence fail-closed review" in release_plan
        and "without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs" in release_plan
    )
    add_check("docs:release-plan-documents-phase102", phase102_release_plan_ok, "docs/open-source-release-plan.md documents Phase 102 syntax-invalid evidence boundary")
    add_check("roadmap:phase102-documented", "### Phase 102 — Agent-complete syntax-invalid evidence fail-closed review ✅" in roadmap and "Confirms syntax-invalid regression evidence cannot satisfy definition-backed coverage or claim agent completion while preserving the external-actions-reserved boundary." in roadmap, "docs/public-roadmap.md documents Phase 102")
    add_check("shell:agent-complete-syntax-invalid-evidence-failclosed-review-command", "--agent-complete-syntax-invalid-evidence-failclosed-review" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 102 flag")

    fail_count = sum(1 for check in syntax_invalid_checks if check["status"] == "fail")
    pass_count = sum(1 for check in syntax_invalid_checks if check["status"] == "pass")
    syntax_invalid_evidence_blocks_completion = fail_count == 0 and phase101_ready and coverage_failclosed
    status = "syntax-invalid-failclosed" if syntax_invalid_evidence_blocks_completion else "blocked"
    return {
        "mode": "agent-complete-syntax-invalid-evidence-failclosed-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "required_reports": ["agent-complete-regression-evidence-integrity"],
        "source_summaries": {"agent-complete-regression-evidence-integrity": phase101_summary},
        "syntax_invalid": syntax_invalid,
        "syntax_invalid_regression_evidence": syntax_invalid_regression_evidence,
        "syntax_invalid_checks": syntax_invalid_checks,
        "summary": {
            "status": status,
            "checks": len(syntax_invalid_checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "agent_side_complete": False,
            "machine_side_complete": False,
            "syntax_invalid_evidence_blocks_completion": syntax_invalid_evidence_blocks_completion,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": phase101_summary.get("remote_configured") is True,
        },
        "review_boundary": [
            "Report-only fail-closed review for syntax-invalid regression evidence.",
            "Confirms syntax-invalid test evidence cannot satisfy definition-backed coverage or claim agent/machine completion.",
            "Does not share artifacts, send invitations, create final feedback, execute commands, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
        ],
        "recommendations": [
            "Keep syntax-invalid source evidence fail-closed when future evidence parsers are added.",
            "Ask the user only for real external target/action authorization.",
        ],
    }


def _validate_phase102_syntax_invalid_evidence_report(phase102_report: Any) -> Dict[str, Any]:
    """Strictly validate latest Phase102 syntax-invalid fail-closed report evidence."""
    report_type = type(phase102_report).__name__ if phase102_report is not None else "missing"
    report = phase102_report if isinstance(phase102_report, dict) else {}
    raw_summary = report.get("summary")
    if isinstance(raw_summary, dict):
        summary_type = "dict"
        phase102_summary = raw_summary
    else:
        summary_type = "missing" if raw_summary is None else type(raw_summary).__name__
        phase102_summary = {}

    def exact_int(key: str, expected: int) -> bool:
        value = phase102_summary.get(key)
        return type(value) is int and value == expected

    expected_summary_values = {
        "status": "syntax-invalid-failclosed",
        "syntax_invalid_evidence_blocks_completion": True,
        "agent_side_complete": False,
        "machine_side_complete": False,
        "requires_user_code_review": False,
        "external_owner_decision_required": True,
        "human_feedback_pending": True,
        "shares_anything": False,
        "sends_invitations": False,
        "writes_anything": False,
        "executes_anything": False,
        "remote_mutation_allowed": False,
        "credential_validation_allowed": False,
        "auto_approves_release": False,
        "issue_backlog_mutation_allowed": False,
    }
    expected_int_values = {
        "writes": 0,
        "remote_issues_created": 0,
        "checks": 5,
        "pass": 5,
        "fail": 0,
        "warn": 0,
    }
    def exact_value(key: str, expected: Any) -> bool:
        value = phase102_summary.get(key)
        if type(expected) is bool:
            return value is expected
        return value == expected

    invalid_fields = sorted(
        [key for key, expected in expected_summary_values.items() if not exact_value(key, expected)]
        + [key for key, expected in expected_int_values.items() if not exact_int(key, expected)]
    )
    invalid_field_types = ",".join(
        f"{key}_type={type(phase102_summary.get(key)).__name__ if key in phase102_summary else 'missing'}"
        for key in invalid_fields
    )
    invalid_fields_text = ",".join(invalid_fields) if invalid_fields else "none"

    valid = (
        report.get("mode") == "agent-complete-syntax-invalid-evidence-failclosed-review"
        and not invalid_fields
    )
    evidence = (
        f"phase102_report_evidence_valid={valid}; "
        f"report_type={report_type}; "
        f"summary_type={summary_type}; "
        f"invalid_fields={invalid_fields_text}; "
        f"{invalid_field_types + '; ' if invalid_field_types else ''}"
        f"mode={report.get('mode')}; "
        f"status={phase102_summary.get('status')}; "
        f"checks={phase102_summary.get('checks')}; "
        f"pass={phase102_summary.get('pass')}; "
        f"fail={phase102_summary.get('fail')}; "
        f"warn={phase102_summary.get('warn')}"
    )
    return {
        "valid": valid,
        "mode": report.get("mode"),
        "report_type": report_type,
        "summary_type": summary_type,
        "invalid_fields": invalid_fields,
        "summary": phase102_summary,
        "evidence": evidence,
        "shares_anything": False,
        "executes_anything": False,
        "remote_mutation_allowed": False,
        "credential_validation_allowed": False,
        "auto_approves_release": False,
        "issue_backlog_mutation_allowed": False,
    }


def build_agent_complete_phase102_rollup_evidence_failclosed_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only review that downstream rollups fail closed without valid Phase102 evidence."""
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    phase102_report = _load_json_if_exists(reports_dir / "latest-agent-complete-syntax-invalid-evidence-failclosed-review.json")
    phase102_validation = _validate_phase102_syntax_invalid_evidence_report(phase102_report)
    phase102_summary = phase102_validation["summary"]
    phase102_report_evidence_valid = phase102_validation["valid"]

    release_plan = _read_text_if_exists(root / "docs" / "open-source-release-plan.md")
    roadmap = _read_text_if_exists(root / "docs" / "public-roadmap.md")
    shell_wrapper = _read_text_if_exists(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    phase103_release_plan_ok = (
        "--agent-complete-phase102-rollup-evidence-failclosed-review --both" in release_plan
        and "local-only/report-only Phase102 rollup evidence fail-closed review" in release_plan
    )
    phase103_roadmap_ok = (
        "### Phase 103 — Agent-complete Phase102 rollup evidence fail-closed review ✅" in roadmap
        and "Confirms downstream completed-work and agent-complete rollups require valid Phase102 report evidence before continuing." in roadmap
    )

    phase102_rollup_checks: List[Dict[str, Any]] = []
    def add_check(name: str, ok: bool, detail: str, extra: Optional[Dict[str, Any]] = None) -> None:
        check: Dict[str, Any] = {"name": name, "status": "pass" if ok else "fail", "detail": detail}
        if extra:
            check.update(extra)
        phase102_rollup_checks.append(check)

    completed_work_report = build_completed_work_review_report(root)
    completed_work_axes = completed_work_report.get("review_axes") if isinstance(completed_work_report.get("review_axes"), dict) else {}
    phase102_rollup_axis = completed_work_axes.get("agent_completion_evidence") if isinstance(completed_work_axes.get("agent_completion_evidence"), dict) else {}

    add_check(
        "source:agent-complete-syntax-invalid-evidence-failclosed-review:valid",
        phase102_report_evidence_valid,
        phase102_validation["evidence"],
        {"invalid_fields": phase102_validation.get("invalid_fields", [])},
    )
    add_check("rollup:completed-work-requires-phase102-report-evidence", phase102_rollup_axis.get("status") == "pass", str(phase102_rollup_axis.get("evidence") or phase102_rollup_axis or "missing"))
    add_check("docs:release-plan-documents-phase103", phase103_release_plan_ok, "docs/open-source-release-plan.md documents Phase 103 Phase102 rollup evidence boundary")
    add_check("roadmap:phase103-documented", phase103_roadmap_ok, "docs/public-roadmap.md documents Phase 103")
    add_check("shell:agent-complete-phase102-rollup-evidence-failclosed-review-command", "--agent-complete-phase102-rollup-evidence-failclosed-review" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes Phase 103 flag")

    fail_count = sum(1 for check in phase102_rollup_checks if check["status"] == "fail")
    pass_count = sum(1 for check in phase102_rollup_checks if check["status"] == "pass")
    rollup_requires_phase102_report_evidence = fail_count == 0 and phase102_report_evidence_valid
    status = "phase102-evidence-failclosed" if rollup_requires_phase102_report_evidence else "blocked"
    return {
        "mode": "agent-complete-phase102-rollup-evidence-failclosed-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "required_reports": ["agent-complete-syntax-invalid-evidence-failclosed-review"],
        "source_summaries": {"agent-complete-syntax-invalid-evidence-failclosed-review": phase102_summary},
        "phase102_rollup_checks": phase102_rollup_checks,
        "summary": {
            "status": status,
            "checks": len(phase102_rollup_checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "agent_side_complete": False,
            "machine_side_complete": False,
            "phase102_report_evidence_valid": phase102_report_evidence_valid,
            "phase102_report_invalid_fields": phase102_validation.get("invalid_fields", []),
            "rollup_requires_phase102_report_evidence": rollup_requires_phase102_report_evidence,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "manual_review_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "remote_configured": False,
        },
        "review_boundary": [
            "Report-only fail-closed review for downstream Phase102 evidence rollup.",
            "Confirms missing or malformed Phase102 report evidence blocks completed-work/agent-complete rollup continuation.",
            "Does not share artifacts, send invitations, create final feedback, execute commands, approve releases, publish, push, create remotes/repos/tags/releases, validate credentials, call providers/APIs, upload artifacts, or mutate issues/backlogs.",
        ],
        "recommendations": [
            "Keep completed-work and agent-complete rollups dependent on strict latest Phase102 report evidence.",
            "Ask the user only for real external target/action authorization.",
        ],
    }


def build_public_release_archive_report(root: Path = ASSETS) -> Dict[str, Any]:
    pack_dir = _latest_public_release_pack_dir(root)
    if pack_dir is None:
        pack_report = build_public_release_pack_report(root)
        pack_dir = Path(pack_report["pack_dir"])
    archive_path = pack_dir.with_suffix(".tar.gz")
    if archive_path.exists():
        archive_path.unlink()
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(pack_dir, arcname=pack_dir.name)
    archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_path.write_text(f"{archive_sha256}  {archive_path.name}\n", encoding="utf-8")
    file_count = sum(1 for path in pack_dir.rglob("*") if path.is_file())
    archive_size_bytes = archive_path.stat().st_size
    return {
        "mode": "public-release-archive",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "pack_dir": str(pack_dir),
        "archive_path": str(archive_path),
        "checksum_path": str(checksum_path),
        "summary": {
            "file_count": file_count,
            "archive_size_bytes": archive_size_bytes,
            "archive_sha256": archive_sha256,
        },
        "recommendations": [
            "Run --public-release-smoke-test before sharing the archive.",
            "Publish the .tar.gz together with its .sha256 checksum when distributing outside Git.",
        ],
    }


def _latest_public_release_archive_path(root: Path) -> Optional[Path]:
    latest_report = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-public-release-archive.json")
    archive_value = latest_report.get("archive_path")
    if isinstance(archive_value, str) and Path(archive_value).is_file():
        return Path(archive_value)
    dist_root = root / "dist"
    if not dist_root.is_dir():
        return None
    candidates = sorted(dist_root.glob("portable-ai-assets-public-*.tar.gz"), key=lambda path: path.name)
    return candidates[-1] if candidates else None


def _run_smoke_command(args: List[str], cwd: Path, timeout: int = 20) -> Dict[str, Any]:
    import subprocess

    try:
        clean_env = os.environ.copy()
        for key in list(clean_env):
            if key.startswith("PAA_"):
                clean_env.pop(key, None)
        completed = subprocess.run(args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, env=clean_env)
        return {"ok": completed.returncode == 0, "returncode": completed.returncode, "output": completed.stdout[-2000:]}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "returncode": None, "output": f"timeout after {timeout}s: {exc}"}
    except Exception as exc:
        return {"ok": False, "returncode": None, "output": str(exc)}


def _scan_pack_tree_for_forbidden_text(pack_dir: Path) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for path in sorted(pack_dir.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_FILE_SUFFIXES:
            continue
        relative = path.relative_to(pack_dir)
        if "bootstrap" in relative.parts and "reports" in relative.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(_scan_text_for_public_safety_findings(path, text, pack_dir))
    return findings


def build_public_release_smoke_test_report(root: Path = ASSETS) -> Dict[str, Any]:
    import tempfile

    archive_path = _latest_public_release_archive_path(root)
    pack_dir = _latest_public_release_pack_dir(root)
    checks: List[Dict[str, Any]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    with tempfile.TemporaryDirectory(prefix="paa-release-smoke-") as tmpdir:
        tmp = Path(tmpdir)
        extracted_root: Optional[Path] = None
        if archive_path and archive_path.is_file():
            try:
                with tarfile.open(archive_path, "r:gz") as archive:
                    archive.extractall(tmp)
                extracted_candidates = [path for path in tmp.iterdir() if path.is_dir()]
                extracted_root = extracted_candidates[0] if extracted_candidates else None
                add_check("archive-extract", extracted_root is not None, str(archive_path))
            except Exception as exc:
                add_check("archive-extract", False, str(exc))
        elif pack_dir and pack_dir.is_dir():
            extracted_root = pack_dir
            add_check("pack-dir-present", True, str(pack_dir))
        else:
            add_check("release-artifact-present", False, "No public release archive or pack directory found")

        if extracted_root is not None:
            required_files = [
                "README.md",
                "MANIFEST.json",
                "PACK-INDEX.md",
                "CHECKSUMS.sha256",
                "bootstrap/setup/bootstrap_ai_assets.py",
                "bootstrap/setup/bootstrap-ai-assets.sh",
                "schemas/README.md",
            ]
            for rel in required_files:
                add_check(f"required:{rel}", (extracted_root / rel).is_file(), rel)

            compile_result = _run_smoke_command([sys.executable, "-m", "py_compile", "bootstrap/setup/bootstrap_ai_assets.py"], cwd=extracted_root)
            add_check("python-py-compile", compile_result["ok"], compile_result["output"] or "py_compile ok")

            cli_result = _run_smoke_command([
                "/bin/bash",
                "bootstrap/setup/bootstrap-ai-assets.sh",
                "--public-safety-scan",
                "--json",
                "--config",
                str(extracted_root / ".no-local-config.yaml"),
            ], cwd=extracted_root)
            add_check("shell-cli-public-safety-scan", cli_result["ok"], cli_result["output"] or "cli ok")

            forbidden_findings = _scan_pack_tree_for_forbidden_text(extracted_root)
            add_check("forbidden-text-scan", len(forbidden_findings) == 0, f"findings={len(forbidden_findings)}")
        else:
            forbidden_findings = []

    failed = [check for check in checks if not check["ok"]]
    return {
        "mode": "public-release-smoke-test",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "archive_path": str(archive_path) if archive_path else None,
        "pack_dir": str(pack_dir) if pack_dir else None,
        "summary": {
            "status": "pass" if not failed else "fail",
            "checks": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "forbidden_findings": len(forbidden_findings),
        },
        "checks": checks,
        "recommendations": [
            "Only publish archives whose smoke-test status is pass.",
            "If py_compile or CLI smoke tests fail, regenerate the public release pack after fixing bootstrap files.",
        ],
    }


def _github_publish_file_templates(root: Path) -> Dict[str, str]:
    archive_report = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-public-release-archive.json")
    smoke_report = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-public-release-smoke-test.json")
    archive_path = _redact_public_text(str(archive_report.get("archive_path", "dist/portable-ai-assets-public-<timestamp>.tar.gz")))
    archive_sha = archive_report.get("summary", {}).get("archive_sha256", "<sha256>")
    smoke_status = smoke_report.get("summary", {}).get("status", "unknown")
    current_year = dt.datetime.now().year
    return {
        "LICENSE": f"MIT License\n\nCopyright (c) {current_year} Portable AI Assets contributors\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software and associated documentation files (the \"Software\"), to deal\nin the Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons to whom the Software is\nfurnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all\ncopies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\nSOFTWARE.\n",
        "SECURITY.md": "# Security Policy\n\nPortable AI Assets separates public engine assets from private memory and runtime state.\n\n## Supported versions\n\nThe current prototype branch receives security fixes on a best-effort basis until formal versioning begins.\n\n## Reporting a vulnerability\n\nPlease open a private security advisory or contact the maintainers privately. Do not publish secrets, private memory, runtime databases, logs, or machine-local config in public issues.\n\n## Sensitive data policy\n\n- Replace secrets with `[REDACTED]`.\n- Do not commit raw runtime DBs, logs, histories, session traces, or backups.\n- Use `--public-safety-scan`, `--release-readiness`, and `--public-release-smoke-test` before publishing artifacts.\n",
        "CHANGELOG.md": "# Changelog\n\n## v0.1.0 — Prototype release candidate\n\n### Added\n\n- Portable AI Assets bootstrap engine with inspect, plan, diff, review/apply, and release-pack workflows.\n- JSON schemas for stack, tool, bridge, architecture-note, adapter-contract, and portable-skill manifests.\n- Adapter registry and connector inventory / preview reports.\n- Public-safe sample assets, redacted examples, demo pack, release pack, archive, and smoke test gates.\n- MemOS/Hermes adoption planning with read-only health/import preview and reviewed skill candidate flows.\n\n### Security\n\n- Public/private/secret asset boundary documented.\n- Release safety scans check for secret-like strings and private absolute paths.\n- Runtime DBs/logs/candidates/backups stay outside public release packs.\n",
        "RELEASE_NOTES-v0.1.md": f"# Release Notes — v0.1.0\n\nPortable AI Assets v0.1.0 is a prototype release for a cross-agent continuity layer: canonical assets, schemas, adapters, review gates, and public-safe release tooling.\n\n## Highlights\n\n- Metadata-first schema validation for portable AI assets.\n- Adapter contract registry and connector preview workflow.\n- Review-first candidate/apply gates for memory, skills, and adapter projections.\n- Public release pack, archive, checksum, and smoke-test pipeline.\n\n## Verification snapshot\n\n- Latest archive: `{archive_path}`\n- Archive SHA256: `{archive_sha}`\n- Smoke test status: `{smoke_status}`\n\n## Not included\n\nThis release intentionally excludes private memory, raw runtime state, candidates, backups, DBs, logs, tokens, and machine-local config.\n",
        "docs/github-publishing.md": "# GitHub Publishing Draft\n\n## Repository description\n\nPortable AI Assets is a cross-agent continuity layer for owning AI memory, skills, adapters, schemas, and migration workflows outside any single runtime.\n\n## Suggested topics\n\n- ai-agents\n- ai-memory\n- mcp\n- local-first\n- agentic-workflows\n- ai-portability\n- developer-tools\n- personal-knowledge-management\n- schemas\n- automation\n\n## Suggested tagline\n\nOwn your AI assets — memory, skills, adapters, and workflows — across agents, machines, and runtimes.\n\n## Publish checklist\n\n1. Run `--public-safety-scan --both`.\n2. Run `--release-readiness --both`.\n3. Run `--public-release-pack --both`.\n4. Run `--public-release-archive --both`.\n5. Run `--public-release-smoke-test --both`.\n6. Review `MANIFEST.json`, `CHECKSUMS.sha256`, `CHANGELOG.md`, and `RELEASE_NOTES-v0.1.md`.\n7. Create the GitHub repo manually; do not auto-push private memory.\n",
    }


def ensure_github_publishing_materials(root: Path = ASSETS) -> Dict[str, Any]:
    templates = _github_publish_file_templates(root)
    written: List[str] = []
    unchanged: List[str] = []
    for rel, content in templates.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and path.read_text(encoding="utf-8", errors="replace") == content:
            unchanged.append(rel)
            continue
        path.write_text(content, encoding="utf-8")
        written.append(rel)
    return {"written": written, "unchanged": unchanged, "expected": sorted(templates.keys())}


def build_github_publish_check_report(root: Path = ASSETS) -> Dict[str, Any]:
    material_results = ensure_github_publishing_materials(root)
    checks: List[Dict[str, Any]] = []

    def add_check(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    required_files = [
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "SECURITY.md",
        "CHANGELOG.md",
        "RELEASE_NOTES-v0.1.md",
        "docs/github-publishing.md",
        "docs/security-model.md",
        "docs/open-source-release-plan.md",
    ]
    for rel in required_files:
        add_check(f"file:{rel}", "pass" if (root / rel).is_file() else "fail", rel)

    latest_reports = [
        "latest-public-safety-scan.json",
        "latest-release-readiness.json",
        "latest-public-release-pack.json",
        "latest-public-release-archive.json",
        "latest-public-release-smoke-test.json",
    ]
    for rel in latest_reports:
        path = root / "bootstrap" / "reports" / rel
        add_check(f"report:{rel}", "pass" if path.is_file() else "warn", str(path.relative_to(root)) if path.exists() else "run release gates")

    safety = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-public-safety-scan.json")
    readiness = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-release-readiness.json")
    smoke = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-public-release-smoke-test.json")
    archive = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-public-release-archive.json")
    add_check("safety:public-safety-scan", "pass" if safety.get("summary", {}).get("status") == "pass" else "fail", str(safety.get("summary", {})))
    add_check("release:readiness", "pass" if readiness.get("summary", {}).get("readiness") == "ready" else "fail", str(readiness.get("summary", {})))
    add_check("release:smoke-test", "pass" if smoke.get("summary", {}).get("status") == "pass" else "fail", str(smoke.get("summary", {})))
    archive_path = Path(str(archive.get("archive_path", "")))
    add_check("release:archive-file", "pass" if archive_path.is_file() else "fail", str(archive_path) if str(archive_path) != "." else "missing archive")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else ("needs-review" if warn_count else "ready")
    return {
        "mode": "github-publish-check",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {"status": status, "checks": len(checks), "pass": pass_count, "warn": warn_count, "fail": fail_count},
        "materials": material_results,
        "github": {
            "description": "Portable AI Assets is a cross-agent continuity layer for owning AI memory, skills, adapters, schemas, and migration workflows outside any single runtime.",
            "topics": ["ai-agents", "ai-memory", "mcp", "local-first", "agentic-workflows", "ai-portability", "developer-tools", "schemas"],
            "release_tag": "v0.1.0",
            "release_notes": "RELEASE_NOTES-v0.1.md",
        },
        "checks": checks,
        "recommendations": [
            "Review generated GitHub materials before publishing.",
            "Create/push the GitHub repository manually; this command never pushes or creates remotes.",
            "Attach the public release archive and .sha256 only after smoke-test status is pass.",
        ],
    }


PUBLIC_REPO_STAGING_INCLUDE_PATHS = [
    ".gitignore",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
    "CHANGELOG.md",
    "RELEASE_NOTES-v0.1.md",
    "GIT-POLICY.md",
    "BACKUP-POLICY.md",
    "docs",
    "schemas",
    "adapters/README.md",
    "adapters/registry",
    "bootstrap/setup",
    "bin",
    "tests",
    "sample-assets",
    "examples/README.md",
    "examples/redacted",
]

PUBLIC_REPO_STAGING_EXCLUDE_PARTS = PUBLIC_RELEASE_EXCLUDE_PARTS.union({
    "bootstrap/reports",
    "examples/redacted/public-demo-pack",
})


def _is_public_repo_staging_excluded(path: Path) -> bool:
    normalized = str(path)
    parts = set(path.parts)
    if parts.intersection(PUBLIC_REPO_STAGING_EXCLUDE_PARTS):
        return True
    return any(excluded in normalized for excluded in PUBLIC_REPO_STAGING_EXCLUDE_PARTS)


def _iter_public_repo_staging_source_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for rel in PUBLIC_REPO_STAGING_INCLUDE_PATHS:
        base = root / rel
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(root) if candidate.is_relative_to(root) else candidate
            if _is_public_repo_staging_excluded(relative):
                continue
            if candidate.suffix not in TEXT_FILE_SUFFIXES and candidate.name != "paa":
                continue
            files.append(candidate)
    return sorted(set(files))


def _write_github_publish_checklist(staging_dir: Path) -> Path:
    checklist = staging_dir / "GITHUB-PUBLISH-CHECKLIST.md"
    lines = [
        "# GitHub Publish Checklist",
        "",
        "This staging tree is generated for manual review before creating or pushing a public GitHub repository.",
        "",
        "## Required before publishing",
        "",
        "- [ ] Review README, docs, examples, schemas, and adapter registry.",
        "- [ ] Confirm `LICENSE`, `SECURITY.md`, `CHANGELOG.md`, and `RELEASE_NOTES-v0.1.md` are acceptable.",
        "- [ ] Run `python3 -m unittest tests/test_bootstrap_phase4.py` if tests are included and local Python supports it.",
        "- [ ] Run `./bin/paa install` and `paa doctor` if validating global CLI installation locally.",
        "- [ ] Run `./bin/paa safety --both` (or `/bin/bash bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both`) inside this staging repo.",
        "- [ ] Treat committed `bootstrap/reports/latest-*` files as static sanitized snapshots, not live GitHub state; rerun local report-only gates for current status.",
        "- [ ] Confirm no private memory, runtime DBs/logs, backups, candidates, machine-local config, or secrets are present.",
        "- [ ] Create the GitHub repo manually and push only after review.",
        "",
        "## Suggested GitHub metadata",
        "",
        "- Description: Portable AI Assets is a cross-agent continuity layer for owning AI memory, skills, adapters, schemas, and migration workflows outside any single runtime.",
        "- Topics: ai-agents, ai-memory, mcp, local-first, agentic-workflows, ai-portability, developer-tools, schemas",
        "- Existing release tag: v0.1.0; do not move it. Use a new tag (for example v0.1.1) for follow-up releases.",
    ]
    checklist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checklist


def build_public_repo_staging_report(root: Path = ASSETS) -> Dict[str, Any]:
    staging_dir = root / "dist" / "github-staging" / "portable-ai-assets"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Ensure GitHub-facing materials exist in the source root before copying.
    ensure_github_publishing_materials(root)

    copied: List[str] = []
    skipped: List[Dict[str, str]] = []
    for source in _iter_public_repo_staging_source_files(root):
        try:
            relative = source.relative_to(root)
        except ValueError:
            skipped.append({"path": str(source), "reason": "outside-root"})
            continue
        target = staging_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(_redact_public_text(source.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
            target.chmod(source.stat().st_mode & 0o777)
            copied.append(str(relative))
        except Exception as exc:
            skipped.append({"path": str(relative), "reason": str(exc)})

    checklist_path = _write_github_publish_checklist(staging_dir)
    copied.append(str(checklist_path.relative_to(staging_dir)))

    git_init = _run_smoke_command(["git", "init"], cwd=staging_dir, timeout=20)
    py_compile = _run_smoke_command([sys.executable, "-m", "py_compile", "bootstrap/setup/bootstrap_ai_assets.py"], cwd=staging_dir, timeout=20)
    reports_excluded_before_smoke = not (staging_dir / "bootstrap" / "reports").exists()
    safety_cli = _run_smoke_command([
        "/bin/bash",
        "bootstrap/setup/bootstrap-ai-assets.sh",
        "--public-safety-scan",
        "--json",
        "--config",
        str(staging_dir / ".no-local-config.yaml"),
    ], cwd=staging_dir, timeout=30)
    # Remove smoke-generated transient files so the staging tree remains source-only.
    reports_dir = staging_dir / "bootstrap" / "reports"
    if reports_dir.exists():
        shutil.rmtree(reports_dir)
    for cache_dir in staging_dir.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)

    source_reports_dir = root / "bootstrap" / "reports"
    staging_reports_dir = staging_dir / "bootstrap" / "reports"
    for report_name in PUBLIC_RELEASE_REPORTS:
        source_report = source_reports_dir / report_name
        if not source_report.is_file():
            continue
        target_report = staging_reports_dir / report_name
        target_report.parent.mkdir(parents=True, exist_ok=True)
        target_report.write_text(_label_public_report_snapshot_text(report_name, source_report.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
        copied.append(str(target_report.relative_to(staging_dir)))
    if staging_reports_dir.exists():
        _write_public_reports_readme(staging_reports_dir)
        copied.append(str((staging_reports_dir / "README.md").relative_to(staging_dir)))

    forbidden_findings = _scan_pack_tree_for_forbidden_text(staging_dir)

    checks = [
        {"name": "git-init", "ok": git_init["ok"], "detail": git_init["output"] or "git init ok"},
        {"name": "python-py-compile", "ok": py_compile["ok"], "detail": py_compile["output"] or "py_compile ok"},
        {"name": "shell-cli-public-safety-scan", "ok": safety_cli["ok"], "detail": safety_cli["output"] or "public safety cli ok"},
        {"name": "forbidden-text-scan", "ok": len(forbidden_findings) == 0, "detail": f"findings={len(forbidden_findings)}"},
        {"name": "private-memory-excluded", "ok": not (staging_dir / "memory").exists(), "detail": "memory/ absent"},
        {"name": "reports-excluded-from-source", "ok": reports_excluded_before_smoke, "detail": "bootstrap/reports absent before staging smoke test"},
    ]
    # The smoke CLI may create bootstrap/reports; keep it but make sure .gitignore excludes it.
    gitignore_path = staging_dir / ".gitignore"
    if gitignore_path.is_file() and "bootstrap/reports/" not in gitignore_path.read_text(encoding="utf-8", errors="replace"):
        with gitignore_path.open("a", encoding="utf-8") as handle:
            handle.write("\n# Generated staging smoke-test reports\nbootstrap/reports/\n")

    failed = [check for check in checks if not check["ok"]]
    manifest = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "asset_class": "public",
        "pack_kind": "github-staging-repo",
        "file_count": len(copied),
        "files": sorted(copied),
        "checks": checks,
    }
    manifest_path = staging_dir / "STAGING-MANIFEST.json"
    manifest_path.write_text(json.dumps(_redact_public_value(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "mode": "public-repo-staging",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "staging_dir": str(staging_dir),
        "manifest_path": str(manifest_path),
        "checklist_path": str(checklist_path),
        "summary": {
            "status": "ready" if not failed else "blocked",
            "files_in_staging": len(copied),
            "skipped": len(skipped),
            "checks": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "forbidden_findings": len(forbidden_findings),
            "git_initialized": git_init["ok"],
        },
        "checks": checks,
        "files": sorted(copied),
        "skipped": skipped,
        "recommendations": [
            "Review dist/github-staging/portable-ai-assets before pushing anywhere.",
            "Run git status inside the staging repo and commit manually only after review.",
            "Do not add private memory, runtime state, candidates, backups, or local config to the public staging repo.",
        ],
    }


def _public_repo_staging_dir(root: Path) -> Path:
    return root / "dist" / "github-staging" / "portable-ai-assets"


def _category_counts(entries: List[Dict[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in entries:
        category = entry.get("category", "other")
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def build_public_repo_staging_status_report(root: Path = ASSETS) -> Dict[str, Any]:
    staging_dir = _public_repo_staging_dir(root)
    git_dir = staging_dir / ".git"
    status_result = run_git_command(staging_dir, ["status", "--short"]) if git_dir.is_dir() else {"ok": False, "output": "staging git repo not initialized"}
    status_entries = parse_git_status_short(status_result.get("output", "")) if status_result.get("ok") else []
    branch_result = run_git_command(staging_dir, ["branch", "--show-current"]) if git_dir.is_dir() else {"ok": False, "output": ""}
    remote_result = run_git_command(staging_dir, ["remote", "-v"]) if git_dir.is_dir() else {"ok": False, "output": ""}
    diff_stat_result = run_git_command(staging_dir, ["diff", "--stat"]) if git_dir.is_dir() else {"ok": False, "output": ""}
    forbidden_findings = _scan_pack_tree_for_forbidden_text(staging_dir) if staging_dir.is_dir() else []
    status = "missing" if not staging_dir.is_dir() else ("blocked" if forbidden_findings else "ready")
    return {
        "mode": "public-repo-staging-status",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "staging_dir": str(staging_dir),
        "summary": {
            "status": status,
            "staging_exists": staging_dir.is_dir(),
            "git_initialized": git_dir.is_dir(),
            "branch": branch_result.get("output") or None,
            "remote_configured": bool(remote_result.get("output")),
            "changed_files": len(status_entries),
            "category_counts": _category_counts(status_entries),
            "forbidden_findings": len(forbidden_findings),
        },
        "git": {
            "status_short": status_result.get("output", ""),
            "status_entries": status_entries,
            "branch": branch_result.get("output", ""),
            "remotes": remote_result.get("output", ""),
            "diff_stat": diff_stat_result.get("output", ""),
        },
        "forbidden_findings": forbidden_findings,
        "recommendations": [
            "Run --public-repo-staging first if the staging repo is missing.",
            "Review all staged public source files before committing.",
            "Keep remotes empty until the target GitHub repository is chosen intentionally.",
        ],
    }


def _git_rev_parse_if_available(repo_dir: Path, rev: str) -> Optional[str]:
    result = run_git_command(repo_dir, ["rev-parse", "--verify", rev])
    return result.get("output") if result.get("ok") and result.get("output") else None


def build_public_repo_staging_history_preflight_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only check for whether generated GitHub staging has publication history context.

    This command never fetches, adds remotes, commits, tags, pushes, creates releases,
    validates credentials, or calls providers. It only inspects the local staging git
    metadata and checklist text so humans can distinguish a freshly generated staging
    tree from a staging tree whose public `main` / `v0.1.0` history has been
    intentionally reattached.
    """
    status_report = build_public_repo_staging_status_report(root)
    staging_dir = Path(status_report["staging_dir"])
    git_initialized = bool(status_report.get("summary", {}).get("git_initialized"))
    remote_configured = bool(status_report.get("summary", {}).get("remote_configured"))
    forbidden_findings = int(status_report.get("summary", {}).get("forbidden_findings") or 0)
    head_rev = _git_rev_parse_if_available(staging_dir, "HEAD") if git_initialized else None
    v010_rev = _git_rev_parse_if_available(staging_dir, "v0.1.0^{commit}") if git_initialized else None
    checklist_path = staging_dir / "GITHUB-PUBLISH-CHECKLIST.md"
    checklist_text = checklist_path.read_text(encoding="utf-8", errors="replace") if checklist_path.is_file() else ""
    checklist_declares_existing_v010 = "Existing release tag: v0.1.0" in checklist_text
    v010_behind_head = bool(head_rev and v010_rev and head_rev != v010_rev)
    generated_without_history = checklist_declares_existing_v010 and (not head_rev or not v010_rev)

    checks: List[Dict[str, str]] = []
    def add(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": _redact_public_text(detail)})

    add("staging-dir-exists", "pass" if staging_dir.is_dir() else "fail", str(staging_dir))
    add("staging-git-initialized", "pass" if git_initialized else "fail", str(git_initialized))
    add("staging-remote-empty", "pass" if not remote_configured else "fail", str(remote_configured))
    add("staging-forbidden-clean", "pass" if forbidden_findings == 0 else "fail", f"forbidden_findings={forbidden_findings}")
    add("checklist-declares-existing-v010", "pass" if checklist_declares_existing_v010 else "warn", "Existing release tag: v0.1.0" if checklist_declares_existing_v010 else "missing existing-tag checklist wording")
    add("staging-head-exists", "pass" if head_rev else "fail", head_rev or "missing HEAD")
    add("v010-tag-exists", "pass" if v010_rev else "fail", v010_rev or "missing v0.1.0^{commit}")
    if head_rev and v010_rev:
        add("v010-behind-head", "pass" if v010_behind_head else "warn", f"v0.1.0={v010_rev}; HEAD={head_rev}")
    if generated_without_history:
        add("existing-tag-context-without-history", "warn", "checklist says v0.1.0 exists, but generated staging lacks HEAD and/or v0.1.0 tag history")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    if remote_configured or forbidden_findings:
        status = "blocked"
    elif generated_without_history:
        status = "needs-history-reattach"
    elif fail_count:
        status = "blocked"
    elif warn_count:
        status = "needs-review"
    else:
        status = "ready"

    manual_steps = [
        {"step": "review-staging-status", "command": "git status --short", "cwd": str(staging_dir), "executes": False, "owner_approval_required": True},
        {"step": "review-current-history", "command": "git log --oneline --decorate -5", "cwd": str(staging_dir), "executes": False, "owner_approval_required": True},
        {"step": "review-v010-tag", "command": "git rev-parse --verify v0.1.0^{commit}", "cwd": str(staging_dir), "executes": False, "owner_approval_required": True},
        {"step": "reattach-public-history-if-approved", "command": "Reattach public main/v0.1.0 history only after explicit owner approval; do not move v0.1.0.", "cwd": str(staging_dir), "executes": False, "owner_approval_required": True},
    ]
    return {
        "mode": "public-repo-staging-history-preflight",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "staging_dir": str(staging_dir),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "head_rev": head_rev,
            "v010_rev": v010_rev,
            "v010_behind_head": v010_behind_head,
            "checklist_declares_existing_v010": checklist_declares_existing_v010,
        },
        "checks": checks,
        "based_on_status": status_report,
        "manual_history_context_steps": manual_steps,
        "recommendations": [
            "Treat needs-history-reattach as expected for freshly generated staging; reattach public history before any manual publication.",
            "Do not move v0.1.0; if a follow-up release is approved later, use a new tag such as v0.1.1.",
            "This report is local/read-only: it never fetches, creates remotes, commits, tags, pushes, uploads, or releases anything.",
        ],
    }


def build_manual_publication_decision_packet_report(root: Path = ASSETS) -> Dict[str, Any]:
    reports_dir = root / "bootstrap" / "reports"
    history = _load_json_if_exists(reports_dir / "latest-public-repo-staging-history-preflight.json")
    if not history:
        history = build_public_repo_staging_history_preflight_report(root)
    dry_run = _load_json_if_exists(reports_dir / "latest-github-publish-dry-run.json")
    if not dry_run:
        dry_run = build_github_publish_dry_run_report(root)
    safety = _load_json_if_exists(reports_dir / "latest-public-safety-scan.json")
    completed = _load_json_if_exists(reports_dir / "latest-completed-work-review.json")

    history_summary = history.get("summary", {}) if isinstance(history.get("summary"), dict) else {}
    dry_summary = dry_run.get("summary", {}) if isinstance(dry_run.get("summary"), dict) else {}
    safety_summary = safety.get("summary", {}) if isinstance(safety.get("summary"), dict) else {}
    completed_summary = completed.get("summary", {}) if isinstance(completed.get("summary"), dict) else {}
    completed_axes = completed.get("review_axes", {}) if isinstance(completed.get("review_axes"), dict) else {}
    external_learning = completed_axes.get("external_learning", {}) if isinstance(completed_axes.get("external_learning"), dict) else {}
    suggested_release_tag = dry_run.get("suggested_release_tag") or "v0.1.1"

    options = [
        {
            "id": "keep-local-only",
            "title": "Keep Phase127+ changes local/staged only",
            "recommended_when": "Owner wants more local review before any external mutation.",
            "requires_owner_approval": False,
            "blocked_until": None,
            "steps": [
                {"step": "continue-local-hardening", "command": "Run local/report-only gates and update handoffs only.", "executes": False},
            ],
            "risks": ["Public GitHub main remains behind local hardening until a later approved push."],
        },
        {
            "id": "prepare-history-reattachment-main-push",
            "title": "Prepare owner-approved public-history reattachment and main push plan",
            "recommended_when": "Owner wants Phase127+ public on GitHub main but no new release yet.",
            "requires_owner_approval": True,
            "blocked_until": "explicit-owner-approval",
            "steps": [
                {"step": "reattach-history", "command": "Reattach public main/v0.1.0 history in staging after owner approval; do not move v0.1.0.", "executes": False},
                {"step": "review-and-commit", "command": "Review staged diff, then create a local staging commit only after approval.", "executes": False},
                {"step": "push-main", "command": "Push public main only after final owner confirmation.", "executes": False},
            ],
            "risks": ["Requires exact public history context; a fresh generated repo is not enough."],
        },
        {
            "id": "prepare-v011-tag-release",
            "title": f"Prepare later {suggested_release_tag} tag/release plan",
            "recommended_when": "Owner wants a formal follow-up release after main is updated and reviewed.",
            "requires_owner_approval": True,
            "blocked_until": "history-reattached-and-main-reviewed",
            "steps": [
                {"step": "confirm-main", "command": "Confirm public main contains intended follow-up commit after owner-approved push.", "executes": False},
                {"step": "create-new-tag", "command": f"Draft new tag {suggested_release_tag}; never move v0.1.0.", "executes": False},
                {"step": "release-review", "command": "Draft release notes/upload checklist only after explicit owner approval.", "executes": False},
            ],
            "risks": ["Tag/release before main review could publish stale or unintended content."],
        },
    ]

    checks: List[Dict[str, str]] = []
    def add(name: str, ok: bool, detail: str, warn: bool = False) -> None:
        checks.append({"name": name, "status": "pass" if ok else ("warn" if warn else "fail"), "detail": _redact_public_text(detail)})

    add("history-preflight-present", bool(history), str(history_summary or "missing"))
    add("history-preflight-non-executing", history_summary.get("executes_anything") is False, str(history_summary.get("executes_anything")))
    add("dry-run-non-executing", dry_summary.get("executes_anything") is False, str(dry_summary.get("executes_anything")))
    add("public-safety-pass", safety_summary.get("status") == "pass" and int(safety_summary.get("findings") or 0) == 0, str(safety_summary or "missing"))
    add("completed-work-aligned", completed_summary.get("status") == "aligned", str(completed_summary.get("status") or "missing"), warn=True)
    add("external-learning-pass", external_learning.get("status") == "pass", str(external_learning.get("status") or "missing"), warn=True)
    add("owner-options-non-executing", all(step.get("executes") is False for option in options for step in option.get("steps", [])), "all option steps are non-executing drafts")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    return {
        "mode": "manual-publication-decision-packet",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": "blocked" if fail_count else "owner-decision-required",
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
            "suggested_release_tag": suggested_release_tag,
            "history_status": history_summary.get("status"),
            "dry_run_status": dry_summary.get("status"),
        },
        "checks": checks,
        "source_summaries": {
            "public_repo_staging_history_preflight": history_summary,
            "github_publish_dry_run": dry_summary,
            "public_safety_scan": safety_summary,
            "completed_work_review": completed_summary,
            "external_learning": external_learning,
        },
        "decision_options": options,
        "recommendations": [
            "Use this packet for owner choice only; it does not approve or perform publication.",
            "If publishing later, reattach public history first, review main, and never move v0.1.0.",
            f"Treat {suggested_release_tag} as a future follow-up tag candidate only after main is reviewed and owner-approved.",
        ],
    }


def build_github_publish_dry_run_report(root: Path = ASSETS) -> Dict[str, Any]:
    status_report = build_public_repo_staging_status_report(root)
    staging_dir = Path(status_report["staging_dir"])
    repo_name = "portable-ai-assets"
    head_rev = _git_rev_parse_if_available(staging_dir, "HEAD")
    v010_rev = _git_rev_parse_if_available(staging_dir, "v0.1.0^{commit}")
    checklist_text = ""
    checklist_path = staging_dir / "GITHUB-PUBLISH-CHECKLIST.md"
    if checklist_path.is_file():
        checklist_text = checklist_path.read_text(encoding="utf-8", errors="replace")
    existing_v010_tag_behind_head = bool(head_rev and v010_rev and head_rev != v010_rev)
    existing_v010_context_without_git_history = (
        "Existing release tag: v0.1.0" in checklist_text
        and not head_rev
        and not v010_rev
    )
    should_use_followup_tag = existing_v010_tag_behind_head or existing_v010_context_without_git_history
    release_tag = "v0.1.1" if should_use_followup_tag else "v0.1.0"
    commit_message = "Update Portable AI Assets after v0.1.0" if should_use_followup_tag else "Initial public release: Portable AI Assets v0.1.0"
    branch = status_report["summary"].get("branch") or "main"
    remote_configured = status_report["summary"].get("remote_configured")
    commands = [
        {"step": "review", "command": "git status --short", "cwd": str(staging_dir), "executes": False},
        {"step": "review-diff", "command": "git diff --stat", "cwd": str(staging_dir), "executes": False},
        {"step": "stage", "command": "git add .", "cwd": str(staging_dir), "executes": False},
        {"step": "commit", "command": f"git commit -m {json.dumps(commit_message)}", "cwd": str(staging_dir), "executes": False},
        {"step": "create-repo", "command": f"gh repo create {repo_name} --public --source=. --remote=origin --description {json.dumps('Portable AI Assets is a cross-agent continuity layer for owning AI memory, skills, adapters, schemas, and migration workflows outside any single runtime.')} --disable-wiki", "cwd": str(staging_dir), "executes": False},
        {"step": "push", "command": f"git push -u origin {branch}", "cwd": str(staging_dir), "executes": False},
        {"step": "tag", "command": f"git tag {release_tag}", "cwd": str(staging_dir), "executes": False},
        {"step": "push-tag", "command": f"git push origin {release_tag}", "cwd": str(staging_dir), "executes": False},
    ]
    checks = [
        {"name": "staging-ready", "status": "pass" if status_report["summary"]["status"] == "ready" else "fail", "detail": status_report["summary"]["status"]},
        {"name": "changed-files-present", "status": "pass" if status_report["summary"]["changed_files"] > 0 else "warn", "detail": str(status_report["summary"]["changed_files"])},
        {"name": "remote-empty", "status": "pass" if not remote_configured else "warn", "detail": status_report["git"].get("remotes") or "no remotes"},
        {"name": "forbidden-findings", "status": "pass" if status_report["summary"]["forbidden_findings"] == 0 else "fail", "detail": str(status_report["summary"]["forbidden_findings"])},
    ]
    if existing_v010_tag_behind_head:
        checks.append({
            "name": "existing-v010-tag-behind-head",
            "status": "warn",
            "detail": f"v0.1.0={v010_rev}; HEAD={head_rev}; suggested_release_tag={release_tag}; do not move v0.1.0",
        })
    if existing_v010_context_without_git_history:
        checks.append({
            "name": "release-tag-context-without-git-history",
            "status": "warn",
            "detail": f"GITHUB-PUBLISH-CHECKLIST.md says v0.1.0 already exists, but staging has no HEAD or v0.1.0 tag; suggested_release_tag={release_tag}; reattach public history before manual publication",
        })
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    return {
        "mode": "github-publish-dry-run",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "staging_dir": str(staging_dir),
        "summary": {
            "status": "blocked" if fail_count else ("needs-review" if warn_count else "ready"),
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warn_count,
            "fail": fail_count,
            "commands": len(commands),
            "executes_anything": False,
        },
        "checks": checks,
        "suggested_commit_message": commit_message,
        "suggested_repo_name": repo_name,
        "suggested_release_tag": release_tag,
        "commands": commands,
        "based_on_status": status_report,
        "recommendations": [
            "This is a dry run only; no commit, push, tag, release, repo, or remote is created.",
            "Review the staging tree and command drafts before executing anything manually.",
            "Do not move v0.1.0; if it already points behind HEAD, use the suggested follow-up tag instead.",
            "If the generated staging repo has no commit history but the checklist says v0.1.0 already exists, reattach public history before any manual publication.",
            "Prefer creating or updating the GitHub repo only after public safety and staging status are clean.",
        ],
    }



def _write_github_handoff_markdown(path: Path, handoff: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# GitHub Publication Handoff")
    lines.append("")
    lines.append("This handoff bundle is public-safe review material for a human maintainer. It does not commit, push, create a remote, or publish a release.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- generated_at: {handoff['generated_at']}")
    lines.append(f"- status: {handoff['summary']['status']}")
    lines.append(f"- staging_dir: `{handoff['staging_dir']}`")
    lines.append(f"- handoff_dir: `{handoff['handoff_dir']}`")
    lines.append(f"- public_archive: `{handoff.get('public_archive') or 'missing'}`")
    lines.append(f"- archive_sha256: `{handoff.get('archive_sha256') or 'unknown'}`")
    lines.append(f"- executes_anything: {handoff['summary']['executes_anything']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in handoff.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Manual publish steps — draft only")
    lines.append("")
    for command in handoff.get("manual_steps", []):
        lines.append(f"### {command['step']}")
        lines.append("")
        lines.append("```bash")
        lines.append(command["command"])
        lines.append("```")
        lines.append("")
    lines.append("## Safety reminders")
    lines.append("")
    for reminder in handoff.get("safety_reminders", []):
        lines.append(f"- {reminder}")
    lines.append("")
    lines.append("## Included support files")
    lines.append("")
    for rel in handoff.get("included_files", []):
        lines.append(f"- `{rel}`")
    lines.append("")
    path.write_text(_redact_public_text("\n".join(lines) + "\n"), encoding="utf-8")


def build_github_handoff_pack_report(root: Path = ASSETS) -> Dict[str, Any]:
    reports_dir = root / "bootstrap" / "reports"
    dry_run_report = build_github_publish_dry_run_report(root)
    status_report = dry_run_report.get("based_on_status", build_public_repo_staging_status_report(root))
    safety_report = _load_json_if_exists(reports_dir / "latest-public-safety-scan.json")
    readiness_report = _load_json_if_exists(reports_dir / "latest-release-readiness.json")
    smoke_report = _load_json_if_exists(reports_dir / "latest-public-release-smoke-test.json")
    github_report = _load_json_if_exists(reports_dir / "latest-github-publish-check.json")
    archive_report = _load_json_if_exists(reports_dir / "latest-public-release-archive.json")

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    handoff_dir = root / "dist" / "github-handoff" / f"portable-ai-assets-handoff-{timestamp}"
    if handoff_dir.exists():
        shutil.rmtree(handoff_dir)
    handoff_dir.mkdir(parents=True, exist_ok=True)

    def _status(report: Dict[str, Any], *path: str, default: str = "missing") -> str:
        value: Any = report
        for key in path:
            if not isinstance(value, dict):
                return default
            value = value.get(key)
        return str(value) if value is not None else default

    archive_path = archive_report.get("archive_path") if isinstance(archive_report.get("archive_path"), str) else None
    archive_exists = bool(archive_path and Path(archive_path).is_file())
    archive_sha = archive_report.get("summary", {}).get("archive_sha256")
    checks = [
        {"name": "staging-status", "status": "pass" if status_report.get("summary", {}).get("status") == "ready" else "fail", "detail": _status(status_report, "summary", "status")},
        {"name": "dry-run-ready", "status": "pass" if dry_run_report.get("summary", {}).get("status") == "ready" else "fail", "detail": _status(dry_run_report, "summary", "status")},
        {"name": "dry-run-non-executing", "status": "pass" if dry_run_report.get("summary", {}).get("executes_anything") is False else "fail", "detail": str(dry_run_report.get("summary", {}).get("executes_anything"))},
        {"name": "public-safety", "status": "pass" if safety_report.get("summary", {}).get("status") == "pass" else "fail", "detail": _status(safety_report, "summary", "status")},
        {"name": "release-readiness", "status": "pass" if readiness_report.get("summary", {}).get("readiness") == "ready" else "fail", "detail": _status(readiness_report, "summary", "readiness")},
        {"name": "release-smoke-test", "status": "pass" if smoke_report.get("summary", {}).get("status") == "pass" else "fail", "detail": _status(smoke_report, "summary", "status")},
        {"name": "github-publish-check", "status": "pass" if github_report.get("summary", {}).get("status") == "ready" else "warn", "detail": _status(github_report, "summary", "status")},
        {"name": "public-archive-file", "status": "pass" if archive_exists else "fail", "detail": _redact_public_text(str(archive_path or "missing"))},
    ]

    support_candidates = [
        (root / "RELEASE_NOTES-v0.1.md", "RELEASE_NOTES-v0.1.md"),
        (root / "CHANGELOG.md", "CHANGELOG.md"),
        (root / "SECURITY.md", "SECURITY.md"),
        (root / "docs" / "github-publishing.md", "docs/github-publishing.md"),
        (root / "dist" / "github-staging" / "portable-ai-assets" / "GITHUB-PUBLISH-CHECKLIST.md", "GITHUB-PUBLISH-CHECKLIST.md"),
        (reports_dir / "latest-public-safety-scan.md", "reports/latest-public-safety-scan.md"),
        (reports_dir / "latest-release-readiness.md", "reports/latest-release-readiness.md"),
        (reports_dir / "latest-public-release-smoke-test.md", "reports/latest-public-release-smoke-test.md"),
        (reports_dir / "latest-github-publish-check.md", "reports/latest-github-publish-check.md"),
        (reports_dir / "latest-public-repo-staging-status.md", "reports/latest-public-repo-staging-status.md"),
        (reports_dir / "latest-github-publish-dry-run.md", "reports/latest-github-publish-dry-run.md"),
        (reports_dir / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md", "reports/latest-agent-complete-phase102-rollup-evidence-failclosed-review.md"),
        (reports_dir / "latest-completed-work-review.md", "reports/latest-completed-work-review.md"),
        (reports_dir / "latest-manual-reviewer-handoff-freeze-check.md", "reports/latest-manual-reviewer-handoff-freeze-check.md"),
    ]
    included_files: List[str] = []
    skipped_files: List[Dict[str, str]] = []
    for source, rel in support_candidates:
        if not source.is_file():
            skipped_files.append({"path": rel, "reason": "missing"})
            continue
        target = handoff_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_redact_public_text(source.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
        included_files.append(rel)

    freeze_source = reports_dir / "latest-manual-reviewer-handoff-freeze-check.md"
    freeze_copy = handoff_dir / "reports" / "latest-manual-reviewer-handoff-freeze-check.md"
    freeze_included = "reports/latest-manual-reviewer-handoff-freeze-check.md" in included_files and freeze_copy.is_file()
    checks.append({"name": "handoff-freeze-report-included", "status": "pass" if freeze_included else "fail", "detail": str(freeze_copy)})
    freeze_content_match = freeze_included and _redact_public_text(freeze_source.read_text(encoding="utf-8", errors="replace")) == freeze_copy.read_text(encoding="utf-8", errors="replace")
    checks.append({"name": "handoff-freeze-report-content-match", "status": "pass" if freeze_content_match else "fail", "detail": "copied freeze report matches redacted source" if freeze_content_match else "copied freeze report differs or is missing"})
    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    freeze_report = _load_json_if_exists(reports_dir / "latest-manual-reviewer-handoff-freeze-check.json")
    freeze_generated_at = str(freeze_report.get("generated_at", "")) if isinstance(freeze_report, dict) else ""
    try:
        freeze_dt = dt.datetime.fromisoformat(freeze_generated_at)
        handoff_dt = dt.datetime.fromisoformat(generated_at)
        freshness_ok = freeze_dt <= handoff_dt
    except Exception:
        freshness_ok = False
    checks.append({"name": "handoff-generated-after-freeze-report", "status": "pass" if freshness_ok else "fail", "detail": f"freeze_generated_at={freeze_generated_at}; handoff_generated_at={generated_at}"})

    handoff_payload = {
        "generated_at": generated_at,
        "asset_class": "public",
        "pack_kind": "github-publication-handoff",
        "staging_dir": _redact_public_text(str(dry_run_report.get("staging_dir", ""))),
        "handoff_dir": _redact_public_text(str(handoff_dir)),
        "public_archive": _redact_public_text(str(archive_path or "")),
        "archive_sha256": archive_sha,
        "summary": {
            "status": "pending",
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": sum(1 for check in checks if check["status"] == "warn"),
            "fail": sum(1 for check in checks if check["status"] == "fail"),
            "included_files": len(included_files),
            "executes_anything": False,
            "forbidden_findings": 0,
        },
        "checks": checks,
        "manual_steps": dry_run_report.get("commands", []),
        "safety_reminders": [
            "Review the staging tree before running any git or gh command manually.",
            "Do not publish private memory, private skills, raw runtime state, DBs, logs, candidates, backups, or machine-local config.",
            "Run public safety, release readiness, smoke test, staging status, and dry-run checks again immediately before publishing.",
            "Keep this handoff as review material; it is not proof that a human has reviewed every file.",
        ],
        "included_files": sorted(included_files),
        "skipped_files": skipped_files,
        "source_reports": {
            "public_safety": safety_report.get("summary", {}),
            "release_readiness": readiness_report.get("summary", {}),
            "release_smoke_test": smoke_report.get("summary", {}),
            "github_publish_check": github_report.get("summary", {}),
            "staging_status": status_report.get("summary", {}),
            "publish_dry_run": dry_run_report.get("summary", {}),
        },
    }
    _write_github_handoff_markdown(handoff_dir / "HANDOFF.md", handoff_payload)
    handoff_payload["included_files"] = sorted(included_files + ["HANDOFF.md", "HANDOFF.json"])
    (handoff_dir / "HANDOFF.json").write_text(json.dumps(_redact_public_value(handoff_payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    forbidden_findings = _scan_pack_tree_for_forbidden_text(handoff_dir)
    checks.append({"name": "handoff-forbidden-text", "status": "pass" if not forbidden_findings else "fail", "detail": f"findings={len(forbidden_findings)}"})
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else ("needs-review" if warn_count else "ready")
    handoff_payload["summary"].update({"status": status, "checks": len(checks), "pass": pass_count, "warn": warn_count, "fail": fail_count, "forbidden_findings": len(forbidden_findings)})
    handoff_payload["checks"] = checks
    handoff_payload["forbidden_findings"] = forbidden_findings
    (handoff_dir / "HANDOFF.json").write_text(json.dumps(_redact_public_value(handoff_payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_github_handoff_markdown(handoff_dir / "HANDOFF.md", handoff_payload)

    return {
        "mode": "github-handoff-pack",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "handoff_dir": str(handoff_dir),
        "handoff_markdown": str(handoff_dir / "HANDOFF.md"),
        "handoff_json": str(handoff_dir / "HANDOFF.json"),
        "staging_dir": str(dry_run_report.get("staging_dir", "")),
        "public_archive": str(archive_path or ""),
        "archive_sha256": archive_sha,
        "summary": handoff_payload["summary"],
        "checks": checks,
        "included_files": handoff_payload["included_files"],
        "skipped_files": skipped_files,
        "manual_steps": dry_run_report.get("commands", []),
        "forbidden_findings": forbidden_findings,
        "recommendations": handoff_payload["safety_reminders"],
    }



def build_github_final_preflight_report(root: Path = ASSETS) -> Dict[str, Any]:
    reports_dir = root / "bootstrap" / "reports"
    safety = _load_json_if_exists(reports_dir / "latest-public-safety-scan.json")
    readiness = _load_json_if_exists(reports_dir / "latest-release-readiness.json")
    archive = _load_json_if_exists(reports_dir / "latest-public-release-archive.json")
    smoke = _load_json_if_exists(reports_dir / "latest-public-release-smoke-test.json")
    github = _load_json_if_exists(reports_dir / "latest-github-publish-check.json")
    staging = _load_json_if_exists(reports_dir / "latest-public-repo-staging.json")
    staging_status = build_public_repo_staging_status_report(root)
    dry_run = build_github_publish_dry_run_report(root)
    handoff = _load_json_if_exists(reports_dir / "latest-github-handoff-pack.json")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": _redact_public_text(detail)})

    def summary_value(report: Dict[str, Any], key: str, nested: str = "summary") -> Any:
        value = report.get(nested, {})
        return value.get(key) if isinstance(value, dict) else None

    add_check("public-safety-pass", "pass" if summary_value(safety, "status") == "pass" else "fail", str(summary_value(safety, "status") or "missing"))
    add_check("release-readiness-ready", "pass" if summary_value(readiness, "readiness") == "ready" else "fail", str(summary_value(readiness, "readiness") or "missing"))
    add_check("release-smoke-pass", "pass" if summary_value(smoke, "status") == "pass" else "fail", str(summary_value(smoke, "status") or "missing"))
    add_check("github-publish-check-ready", "pass" if summary_value(github, "status") == "ready" else "fail", str(summary_value(github, "status") or "missing"))
    add_check("public-repo-staging-ready", "pass" if summary_value(staging, "status") == "ready" else "fail", str(summary_value(staging, "status") or "missing"))
    add_check("staging-status-ready", "pass" if summary_value(staging_status, "status") == "ready" else "fail", str(summary_value(staging_status, "status") or "missing"))
    add_check("staging-remote-empty", "pass" if summary_value(staging_status, "remote_configured") is False else "fail", str(summary_value(staging_status, "remote_configured")))
    add_check("dry-run-ready", "pass" if summary_value(dry_run, "status") == "ready" else "fail", str(summary_value(dry_run, "status") or "missing"))
    dry_executes = summary_value(dry_run, "executes_anything") is False and all(command.get("executes") is False for command in dry_run.get("commands", []))
    add_check("dry-run-non-executing", "pass" if dry_executes else "fail", str(summary_value(dry_run, "executes_anything")))
    add_check("handoff-pack-ready", "pass" if summary_value(handoff, "status") == "ready" else "fail", str(summary_value(handoff, "status") or "missing"))
    add_check("handoff-non-executing", "pass" if summary_value(handoff, "executes_anything") is False else "fail", str(summary_value(handoff, "executes_anything")))
    add_check("handoff-forbidden-clean", "pass" if summary_value(handoff, "forbidden_findings") == 0 else "fail", str(summary_value(handoff, "forbidden_findings")))

    archive_path_value = archive.get("archive_path")
    archive_path = Path(archive_path_value) if isinstance(archive_path_value, str) else None
    archive_exists = bool(archive_path and archive_path.is_file())
    checksum_path = Path(str(archive.get("checksum_path", ""))) if archive.get("checksum_path") else (archive_path.with_suffix(archive_path.suffix + ".sha256") if archive_path else None)
    checksum_exists = bool(checksum_path and checksum_path.is_file())
    recorded_sha = summary_value(archive, "archive_sha256")
    computed_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest() if archive_exists and archive_path else None
    add_check("archive-file-exists", "pass" if archive_exists else "fail", str(archive_path or "missing"))
    add_check("archive-checksum-file-exists", "pass" if checksum_exists else "fail", str(checksum_path or "missing"))
    add_check("archive-sha256-matches", "pass" if archive_exists and recorded_sha and computed_sha == recorded_sha else "fail", f"recorded={recorded_sha or 'missing'} computed={computed_sha or 'missing'}")

    handoff_dir_value = handoff.get("handoff_dir")
    handoff_dir = Path(handoff_dir_value) if isinstance(handoff_dir_value, str) else None
    handoff_files_ok = bool(handoff_dir and (handoff_dir / "HANDOFF.md").is_file() and (handoff_dir / "HANDOFF.json").is_file())
    add_check("handoff-files-exist", "pass" if handoff_files_ok else "fail", str(handoff_dir or "missing"))

    command_drafts = dry_run.get("commands", []) if isinstance(dry_run.get("commands"), list) else []
    forbidden_findings = _scan_pack_tree_for_forbidden_text(handoff_dir) if handoff_dir and handoff_dir.is_dir() else []
    if forbidden_findings:
        add_check("handoff-tree-forbidden-clean", "fail", f"findings={len(forbidden_findings)}")
    else:
        add_check("handoff-tree-forbidden-clean", "pass", "findings=0")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else ("needs-review" if warn_count else "ready")
    return {
        "mode": "github-final-preflight",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
            "command_drafts": len(command_drafts),
            "remote_configured": summary_value(staging_status, "remote_configured"),
            "forbidden_findings": len(forbidden_findings),
        },
        "checks": checks,
        "paths": {
            "staging_dir": staging_status.get("staging_dir"),
            "handoff_dir": str(handoff_dir) if handoff_dir else "",
            "archive_path": str(archive_path) if archive_path else "",
            "checksum_path": str(checksum_path) if checksum_path else "",
        },
        "artifact_sha256": {"recorded": recorded_sha, "computed": computed_sha},
        "command_drafts": command_drafts,
        "source_summaries": {
            "public_safety": safety.get("summary", {}),
            "release_readiness": readiness.get("summary", {}),
            "public_release_archive": archive.get("summary", {}),
            "public_release_smoke_test": smoke.get("summary", {}),
            "github_publish_check": github.get("summary", {}),
            "public_repo_staging": staging.get("summary", {}),
            "public_repo_staging_status": staging_status.get("summary", {}),
            "github_publish_dry_run": dry_run.get("summary", {}),
            "github_handoff_pack": handoff.get("summary", {}),
        },
        "forbidden_findings": forbidden_findings,
        "recommendations": [
            "Treat this as the last machine-generated preflight before human review and manual publication.",
            "If status is not ready, rerun the failed gate command and regenerate handoff/preflight reports.",
            "Do not execute command drafts until a human has reviewed the staging tree and handoff bundle.",
        ],
    }



def _tree_digest(root: Path) -> Dict[str, Any]:
    if not root.is_dir():
        return {"exists": False, "file_count": 0, "sha256": None, "files": []}
    rows: List[Dict[str, Any]] = []
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if ".git" in path.relative_to(root).parts:
            continue
        relative = str(path.relative_to(root))
        file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        size = path.stat().st_size
        rows.append({"path": relative, "sha256": file_sha, "size_bytes": size})
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha.encode("ascii"))
        digest.update(b"\0")
    return {"exists": True, "file_count": len(rows), "sha256": digest.hexdigest(), "files": rows}


def _write_release_provenance_markdown(path: Path, provenance: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# Portable AI Assets Release Provenance")
    lines.append("")
    lines.append("This is a public-safe, unsigned provenance manifest for human review. It records artifact checksums and gate summaries; it does not publish or mutate any Git remote.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    summary = provenance.get("summary", {})
    for key in ["status", "checks", "pass", "warn", "fail", "executes_anything", "forbidden_findings"]:
        lines.append(f"- {key}: {summary.get(key)}")
    lines.append("")
    lines.append("## Subject")
    lines.append("")
    subject = provenance.get("subject", {})
    lines.append(f"- archive: `{subject.get('archive_path') or 'missing'}`")
    lines.append(f"- archive_sha256: `{subject.get('archive_sha256') or 'missing'}`")
    lines.append(f"- checksum_file: `{subject.get('checksum_path') or 'missing'}`")
    lines.append("")
    lines.append("## Tree digests")
    lines.append("")
    for name, tree in provenance.get("tree_digests", {}).items():
        lines.append(f"- {name}: exists={tree.get('exists')} files={tree.get('file_count')} sha256=`{tree.get('sha256') or 'missing'}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in provenance.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Source report summaries")
    lines.append("")
    for name, summary_value in provenance.get("source_summaries", {}).items():
        lines.append(f"- `{name}`: `{summary_value}`")
    lines.append("")
    path.write_text(_redact_public_text("\n".join(lines) + "\n"), encoding="utf-8")


def build_release_provenance_report(root: Path = ASSETS) -> Dict[str, Any]:
    reports_dir = root / "bootstrap" / "reports"
    final_preflight = _load_json_if_exists(reports_dir / "latest-github-final-preflight.json")
    if not final_preflight:
        final_preflight = build_github_final_preflight_report(root)
    archive_report = _load_json_if_exists(reports_dir / "latest-public-release-archive.json")
    staging_status = _load_json_if_exists(reports_dir / "latest-public-repo-staging-status.json")
    dry_run = _load_json_if_exists(reports_dir / "latest-github-publish-dry-run.json")
    handoff = _load_json_if_exists(reports_dir / "latest-github-handoff-pack.json")
    safety = _load_json_if_exists(reports_dir / "latest-public-safety-scan.json")
    readiness = _load_json_if_exists(reports_dir / "latest-release-readiness.json")
    smoke = _load_json_if_exists(reports_dir / "latest-public-release-smoke-test.json")

    archive_path_value = archive_report.get("archive_path")
    archive_path = Path(archive_path_value) if isinstance(archive_path_value, str) else None
    checksum_path_value = archive_report.get("checksum_path")
    checksum_path = Path(checksum_path_value) if isinstance(checksum_path_value, str) else (archive_path.with_suffix(archive_path.suffix + ".sha256") if archive_path else None)
    archive_exists = bool(archive_path and archive_path.is_file())
    checksum_exists = bool(checksum_path and checksum_path.is_file())
    archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest() if archive_exists and archive_path else None
    recorded_sha = archive_report.get("summary", {}).get("archive_sha256")

    staging_dir = Path(str(staging_status.get("staging_dir", root / "dist" / "github-staging" / "portable-ai-assets")))
    handoff_dir = Path(str(handoff.get("handoff_dir", ""))) if handoff.get("handoff_dir") else None
    pack_dir_value = archive_report.get("pack_dir")
    pack_dir = Path(pack_dir_value) if isinstance(pack_dir_value, str) else _latest_public_release_pack_dir(root)
    tree_digests = {
        "public_release_pack": _tree_digest(pack_dir) if pack_dir else {"exists": False, "file_count": 0, "sha256": None, "files": []},
        "github_staging": _tree_digest(staging_dir),
        "github_handoff": _tree_digest(handoff_dir) if handoff_dir else {"exists": False, "file_count": 0, "sha256": None, "files": []},
    }

    checks: List[Dict[str, str]] = []
    def add(name: str, ok: bool, detail: str, warn: bool = False) -> None:
        checks.append({"name": name, "status": "pass" if ok else ("warn" if warn else "fail"), "detail": _redact_public_text(detail)})

    add("final-preflight-ready", final_preflight.get("summary", {}).get("status") == "ready", str(final_preflight.get("summary", {}).get("status") or "missing"))
    add("archive-exists", archive_exists, str(archive_path or "missing"))
    add("checksum-exists", checksum_exists, str(checksum_path or "missing"))
    add("archive-sha256-matches", bool(archive_sha and recorded_sha and archive_sha == recorded_sha), f"recorded={recorded_sha or 'missing'} computed={archive_sha or 'missing'}")
    add("staging-tree-digest", bool(tree_digests["github_staging"].get("sha256")), str(tree_digests["github_staging"].get("file_count")))
    add("handoff-tree-digest", bool(tree_digests["github_handoff"].get("sha256")), str(tree_digests["github_handoff"].get("file_count")))
    add("pack-tree-digest", bool(tree_digests["public_release_pack"].get("sha256")), str(tree_digests["public_release_pack"].get("file_count")))
    add("dry-run-non-executing", dry_run.get("summary", {}).get("executes_anything") is False, str(dry_run.get("summary", {}).get("executes_anything")))
    add("staging-remote-empty", staging_status.get("summary", {}).get("remote_configured") is False, str(staging_status.get("summary", {}).get("remote_configured")))

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    provenance_dir = root / "dist" / "provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    provenance_json = provenance_dir / f"portable-ai-assets-provenance-{timestamp}.json"
    provenance_md = provenance_dir / f"portable-ai-assets-provenance-{timestamp}.md"

    source_summaries = {
        "public_safety": safety.get("summary", {}),
        "release_readiness": readiness.get("summary", {}),
        "public_release_archive": archive_report.get("summary", {}),
        "public_release_smoke_test": smoke.get("summary", {}),
        "public_repo_staging_status": staging_status.get("summary", {}),
        "github_publish_dry_run": dry_run.get("summary", {}),
        "github_handoff_pack": handoff.get("summary", {}),
        "github_final_preflight": final_preflight.get("summary", {}),
    }
    provenance_payload: Dict[str, Any] = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "asset_class": "public",
        "provenance_kind": "unsigned-release-provenance-v1",
        "executes_anything": False,
        "subject": {
            "name": archive_path.name if archive_path else "missing",
            "archive_path": _redact_public_text(str(archive_path or "")),
            "checksum_path": _redact_public_text(str(checksum_path or "")),
            "archive_sha256": archive_sha,
            "recorded_archive_sha256": recorded_sha,
        },
        "tree_digests": _redact_public_value(tree_digests),
        "source_summaries": _redact_public_value(source_summaries),
        "checks": checks,
        "recommendations": [
            "Publish this provenance file next to the release archive/checksum if useful for reviewers.",
            "Treat this as unsigned provenance; add cryptographic signing in a future phase before claiming tamper-proof attestation.",
            "Regenerate provenance after any release artifact, staging tree, or handoff bundle changes.",
        ],
    }
    provenance_json.write_text(json.dumps(_redact_public_value(provenance_payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_release_provenance_markdown(provenance_md, provenance_payload)
    forbidden = _scan_pack_tree_for_forbidden_text(provenance_dir)
    add("provenance-forbidden-clean", len(forbidden) == 0, f"findings={len(forbidden)}")
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else ("needs-review" if warn_count else "ready")
    summary = {"status": status, "checks": len(checks), "pass": pass_count, "warn": warn_count, "fail": fail_count, "executes_anything": False, "forbidden_findings": len(forbidden)}
    provenance_payload["summary"] = summary
    provenance_payload["checks"] = checks
    provenance_payload["forbidden_findings"] = forbidden
    provenance_json.write_text(json.dumps(_redact_public_value(provenance_payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_release_provenance_markdown(provenance_md, provenance_payload)
    latest_json = provenance_dir / "latest-provenance.json"
    latest_md = provenance_dir / "latest-provenance.md"
    latest_json.write_text(provenance_json.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(provenance_md.read_text(encoding="utf-8"), encoding="utf-8")
    return {
        "mode": "release-provenance",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "provenance_dir": str(provenance_dir),
        "provenance_json": str(provenance_json),
        "provenance_markdown": str(provenance_md),
        "latest_json": str(latest_json),
        "latest_markdown": str(latest_md),
        "summary": summary,
        "subject": provenance_payload["subject"],
        "tree_digests": tree_digests,
        "checks": checks,
        "source_summaries": source_summaries,
        "forbidden_findings": forbidden,
        "recommendations": provenance_payload["recommendations"],
    }



def _latest_provenance_path(root: Path) -> Optional[Path]:
    provenance_report = _load_json_if_exists(root / "bootstrap" / "reports" / "latest-release-provenance.json")
    value = provenance_report.get("provenance_json")
    if isinstance(value, str) and Path(value).is_file():
        return Path(value)
    candidate = root / "dist" / "provenance" / "latest-provenance.json"
    if candidate.is_file():
        return candidate
    provenance_dir = root / "dist" / "provenance"
    if not provenance_dir.is_dir():
        return None
    candidates = sorted(provenance_dir.glob("portable-ai-assets-provenance-*.json"), key=lambda path: path.name)
    return candidates[-1] if candidates else None


def build_verify_release_provenance_report(root: Path = ASSETS) -> Dict[str, Any]:
    reports_dir = root / "bootstrap" / "reports"
    provenance_path = _latest_provenance_path(root)
    provenance = _load_json_if_exists(provenance_path) if provenance_path else {}
    archive_report = _load_json_if_exists(reports_dir / "latest-public-release-archive.json")
    staging_status = _load_json_if_exists(reports_dir / "latest-public-repo-staging-status.json")
    handoff = _load_json_if_exists(reports_dir / "latest-github-handoff-pack.json")

    archive_path_value = archive_report.get("archive_path")
    archive_path = Path(archive_path_value) if isinstance(archive_path_value, str) else None
    checksum_path_value = archive_report.get("checksum_path")
    checksum_path = Path(checksum_path_value) if isinstance(checksum_path_value, str) else (archive_path.with_suffix(archive_path.suffix + ".sha256") if archive_path else None)
    archive_exists = bool(archive_path and archive_path.is_file())
    checksum_exists = bool(checksum_path and checksum_path.is_file())
    computed_archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest() if archive_exists and archive_path else None
    provenance_archive_sha = provenance.get("subject", {}).get("archive_sha256")
    report_archive_sha = archive_report.get("summary", {}).get("archive_sha256")

    staging_dir = Path(str(staging_status.get("staging_dir", root / "dist" / "github-staging" / "portable-ai-assets")))
    handoff_dir = Path(str(handoff.get("handoff_dir", ""))) if handoff.get("handoff_dir") else None
    pack_dir_value = archive_report.get("pack_dir")
    pack_dir = Path(pack_dir_value) if isinstance(pack_dir_value, str) else _latest_public_release_pack_dir(root)
    current_tree_digests = {
        "public_release_pack": _tree_digest(pack_dir) if pack_dir else {"exists": False, "file_count": 0, "sha256": None, "files": []},
        "github_staging": _tree_digest(staging_dir),
        "github_handoff": _tree_digest(handoff_dir) if handoff_dir else {"exists": False, "file_count": 0, "sha256": None, "files": []},
    }
    recorded_tree_digests = provenance.get("tree_digests", {}) if isinstance(provenance.get("tree_digests"), dict) else {}
    checks: List[Dict[str, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": _redact_public_text(detail)})

    add("provenance-file-exists", bool(provenance_path and provenance_path.is_file()), str(provenance_path or "missing"))
    add("provenance-kind", provenance.get("provenance_kind") == "unsigned-release-provenance-v1", str(provenance.get("provenance_kind") or "missing"))
    add("provenance-non-executing", provenance.get("executes_anything") is False or provenance.get("summary", {}).get("executes_anything") is False, str(provenance.get("executes_anything", provenance.get("summary", {}).get("executes_anything"))))
    add("archive-file-exists", archive_exists, str(archive_path or "missing"))
    add("checksum-file-exists", checksum_exists, str(checksum_path or "missing"))
    add("archive-sha256-matches-provenance", bool(computed_archive_sha and provenance_archive_sha and computed_archive_sha == provenance_archive_sha), f"computed={computed_archive_sha or 'missing'} provenance={provenance_archive_sha or 'missing'}")
    add("archive-sha256-matches-report", bool(computed_archive_sha and report_archive_sha and computed_archive_sha == report_archive_sha), f"computed={computed_archive_sha or 'missing'} report={report_archive_sha or 'missing'}")

    tree_results: Dict[str, Dict[str, Any]] = {}
    for name, current in current_tree_digests.items():
        recorded = recorded_tree_digests.get(name, {}) if isinstance(recorded_tree_digests.get(name), dict) else {}
        sha_ok = bool(current.get("sha256") and recorded.get("sha256") and current.get("sha256") == recorded.get("sha256"))
        count_ok = current.get("file_count") == recorded.get("file_count")
        tree_results[name] = {"current": current, "recorded": recorded, "sha256_match": sha_ok, "file_count_match": count_ok}
        add(f"tree:{name}:sha256", sha_ok, f"current={current.get('sha256') or 'missing'} recorded={recorded.get('sha256') or 'missing'}")
        add(f"tree:{name}:file-count", count_ok, f"current={current.get('file_count')} recorded={recorded.get('file_count')}")

    provenance_dir = provenance_path.parent if provenance_path else root / "dist" / "provenance"
    forbidden = _scan_pack_tree_for_forbidden_text(provenance_dir) if provenance_dir.is_dir() else []
    add("provenance-forbidden-clean", len(forbidden) == 0, f"findings={len(forbidden)}")
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    summary = {"status": "ready" if fail_count == 0 else "blocked", "checks": len(checks), "pass": pass_count, "fail": fail_count, "executes_anything": False, "forbidden_findings": len(forbidden)}
    return {
        "mode": "verify-release-provenance",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "provenance_path": str(provenance_path or ""),
        "summary": summary,
        "subject": {
            "archive_path": str(archive_path or ""),
            "checksum_path": str(checksum_path or ""),
            "computed_archive_sha256": computed_archive_sha,
            "provenance_archive_sha256": provenance_archive_sha,
            "report_archive_sha256": report_archive_sha,
        },
        "checks": checks,
        "tree_results": tree_results,
        "forbidden_findings": forbidden,
        "recommendations": [
            "If verification is blocked, regenerate release artifacts, final preflight, provenance, and then rerun this verifier.",
            "This verifies unsigned provenance against local artifacts; it does not prove external artifact authenticity.",
            "Use a future signing phase for tamper-resistant release attestations.",
        ],
    }



def build_release_closure_report(root: Path = ASSETS) -> Dict[str, Any]:
    required_evidence = [
        "public-safety-scan",
        "release-readiness",
        "public-demo-pack",
        "public-release-pack",
        "public-release-archive",
        "public-release-smoke-test",
        "github-publish-check",
        "public-repo-staging",
        "public-repo-staging-status",
        "github-publish-dry-run",
        "github-handoff-pack",
        "manual-reviewer-handoff-freeze-check",
        "github-final-preflight",
        "release-provenance",
        "verify-release-provenance",
        "completed-work-review",
    ]
    reports: Dict[str, Dict[str, Any]] = {
        prefix: _load_latest_report_json_for_root(root, prefix) or {} for prefix in required_evidence
    }

    checks: List[Dict[str, str]] = []

    def summary(prefix: str) -> Dict[str, Any]:
        value = reports.get(prefix, {}).get("summary", {})
        return value if isinstance(value, dict) else {}

    def add_check(name: str, ok: bool, detail: str, warn: bool = False) -> None:
        checks.append({
            "name": name,
            "status": "pass" if ok else ("warn" if warn else "fail"),
            "detail": _redact_public_text(detail),
        })

    def evidence_present(prefix: str) -> bool:
        return bool(reports.get(prefix))

    def status_in(prefix: str, allowed: set) -> bool:
        value = summary(prefix).get("status")
        return isinstance(value, str) and value in allowed

    def readiness_ready(prefix: str) -> bool:
        values = summary(prefix)
        return values.get("readiness") == "ready" or values.get("status") == "ready"

    for prefix in required_evidence:
        add_check(f"evidence:{prefix}:present", evidence_present(prefix), "present" if evidence_present(prefix) else "missing latest report")

    add_check("public-safety-pass", status_in("public-safety-scan", {"pass"}), str(summary("public-safety-scan").get("status") or "missing"))
    add_check("public-safety-no-blockers", int(summary("public-safety-scan").get("blockers") or 0) == 0, str(summary("public-safety-scan").get("blockers", "missing")))
    add_check("release-readiness-ready", readiness_ready("release-readiness"), str(summary("release-readiness").get("readiness") or summary("release-readiness").get("status") or "missing"))
    add_check("public-demo-pack-ready", status_in("public-demo-pack", {"ready"}) or (evidence_present("public-demo-pack") and int(summary("public-demo-pack").get("files_in_pack") or 0) > 0), str(summary("public-demo-pack").get("status") or summary("public-demo-pack").get("files_in_pack") or "missing"))
    add_check("public-release-pack-ready", status_in("public-release-pack", {"ready"}) or (evidence_present("public-release-pack") and summary("public-release-pack").get("public_safety_status") == "pass" and summary("public-release-pack").get("release_readiness") == "ready"), str(summary("public-release-pack").get("status") or summary("public-release-pack") or "missing"))
    add_check("public-release-archive-ready", status_in("public-release-archive", {"ready"}) or (evidence_present("public-release-archive") and int(summary("public-release-archive").get("file_count") or 0) > 0 and bool(summary("public-release-archive").get("archive_sha256"))), str(summary("public-release-archive").get("status") or summary("public-release-archive").get("archive_sha256") or "missing"))
    add_check("public-release-smoke-pass", status_in("public-release-smoke-test", {"pass", "ready"}), str(summary("public-release-smoke-test").get("status") or "missing"))
    add_check("github-publish-check-ready", status_in("github-publish-check", {"ready"}), str(summary("github-publish-check").get("status") or "missing"))
    add_check("public-repo-staging-ready", status_in("public-repo-staging", {"ready"}), str(summary("public-repo-staging").get("status") or "missing"))
    add_check("public-repo-staging-status-ready", status_in("public-repo-staging-status", {"ready"}), str(summary("public-repo-staging-status").get("status") or "missing"))
    add_check("github-publish-dry-run-ready", status_in("github-publish-dry-run", {"ready"}), str(summary("github-publish-dry-run").get("status") or "missing"))
    add_check("github-handoff-pack-ready", status_in("github-handoff-pack", {"ready"}), str(summary("github-handoff-pack").get("status") or "missing"))
    add_check("manual-reviewer-handoff-freeze-check-frozen", status_in("manual-reviewer-handoff-freeze-check", {"frozen-for-human-handoff"}), str(summary("manual-reviewer-handoff-freeze-check").get("status") or "missing"))
    github_handoff_checks = reports.get("github-handoff-pack", {}).get("checks", [])
    github_handoff_fresh_after_freeze = any(
        isinstance(check, dict)
        and check.get("name") == "handoff-generated-after-freeze-report"
        and check.get("status") == "pass"
        for check in github_handoff_checks
    )
    add_check("github-handoff-fresh-after-freeze", github_handoff_fresh_after_freeze, "handoff-generated-after-freeze-report=pass" if github_handoff_fresh_after_freeze else "missing or failing freshness check")
    add_check("github-final-preflight-ready", status_in("github-final-preflight", {"ready"}), str(summary("github-final-preflight").get("status") or "missing"))
    add_check("release-provenance-ready", status_in("release-provenance", {"ready"}), str(summary("release-provenance").get("status") or "missing"))
    provenance_report = reports.get("release-provenance", {})
    provenance_is_unsigned_local = provenance_report.get("mode") == "release-provenance" and summary("release-provenance").get("executes_anything") is False
    explicit_provenance_kind = provenance_report.get("provenance_kind") or summary("release-provenance").get("provenance_kind")
    add_check("release-provenance-unsigned-kind", provenance_is_unsigned_local or explicit_provenance_kind == "unsigned-release-provenance-v1", str(explicit_provenance_kind or provenance_report.get("mode") or "missing"))
    add_check("verify-release-provenance-ready", status_in("verify-release-provenance", {"ready"}), str(summary("verify-release-provenance").get("status") or "missing"))
    add_check("completed-work-review-aligned", status_in("completed-work-review", {"aligned", "ready", "pass"}), str(summary("completed-work-review").get("status") or "missing"))
    completed_axes = reports.get("completed-work-review", {}).get("review_axes", {})
    external_learning_axis = completed_axes.get("external_learning", {}) if isinstance(completed_axes, dict) else {}
    external_learning_status = external_learning_axis.get("status") if isinstance(external_learning_axis, dict) else None
    add_check("completed-work-external-learning-pass", external_learning_status == "pass", str(external_learning_status or "missing"))

    command_drafts: List[Dict[str, Any]] = []
    for key in ["commands", "command_drafts", "manual_steps"]:
        value = reports.get("github-publish-dry-run", {}).get(key)
        if isinstance(value, list):
            command_drafts.extend(item for item in value if isinstance(item, dict))
    value = reports.get("github-final-preflight", {}).get("command_drafts")
    if isinstance(value, list):
        command_drafts.extend(item for item in value if isinstance(item, dict))
    command_drafts = [_redact_public_value(command) for command in command_drafts]

    def classify_publication_command(command: Dict[str, Any]) -> str:
        text = f"{command.get('step') or ''} {command.get('name') or ''} {command.get('command') or ''}".lower()
        if "gh repo create" in text or "repo create" in text or "create repo" in text:
            return "repo-create"
        if "git push" in text or " push" in text:
            return "push"
        if "git tag" in text or " tag" in text:
            return "tag"
        if "git commit" in text or " commit" in text:
            return "commit"
        if "git add" in text or " add" in text:
            return "stage"
        if "gh release" in text or " release" in text or "publish" in text:
            return "release-publish"
        return "manual-review"

    for command in command_drafts:
        command["publication_risk"] = classify_publication_command(command)
        command["manual_review_required"] = True
    commands_non_executing = all(command.get("executes") is False for command in command_drafts)
    publication_command_summary: Dict[str, Any] = {
        "total": len(command_drafts),
        "non_executing": sum(1 for command in command_drafts if command.get("executes") is False),
        "manual_review_required": sum(1 for command in command_drafts if command.get("manual_review_required") is True),
        "by_publication_risk": {},
    }
    for command in command_drafts:
        risk = str(command.get("publication_risk") or "manual-review")
        publication_command_summary["by_publication_risk"][risk] = publication_command_summary["by_publication_risk"].get(risk, 0) + 1
    add_check("command-drafts-non-executing", commands_non_executing, f"command_drafts={len(command_drafts)}")
    add_check("publication-command-drafts-manual-review", publication_command_summary["manual_review_required"] == len(command_drafts), f"manual_review_required={publication_command_summary['manual_review_required']}/{len(command_drafts)}")

    non_executing_sources = [
        "public-demo-pack",
        "github-publish-dry-run",
        "github-handoff-pack",
        "manual-reviewer-handoff-freeze-check",
        "github-final-preflight",
        "release-provenance",
        "verify-release-provenance",
        "completed-work-review",
    ]
    def source_is_non_executing(prefix: str) -> bool:
        value = summary(prefix).get("executes_anything")
        if value is False:
            return True
        if value is None and prefix in {"public-demo-pack"} and evidence_present(prefix):
            return True
        return False

    for prefix in non_executing_sources:
        add_check(f"{prefix}-non-executing", source_is_non_executing(prefix), str(summary(prefix).get("executes_anything")))

    remote_values = [
        summary("public-repo-staging-status").get("remote_configured"),
        summary("github-final-preflight").get("remote_configured"),
    ]
    remote_configured = any(value is True for value in remote_values)
    add_check("no-git-remote-configured", not remote_configured and any(value is False for value in remote_values), str(remote_values))

    forbidden_total = 0
    for prefix in ["public-demo-pack", "public-release-pack", "public-repo-staging", "github-handoff-pack", "manual-reviewer-handoff-freeze-check", "github-final-preflight", "release-provenance", "verify-release-provenance"]:
        value = summary(prefix).get("forbidden_findings", 0)
        if isinstance(value, int):
            forbidden_total += value
    add_check("public-forbidden-findings-clean", forbidden_total == 0, f"forbidden_findings={forbidden_total}")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    missing_count = sum(1 for prefix in required_evidence if not evidence_present(prefix))
    status = "blocked" if fail_count else ("needs-review" if warn_count else "ready-for-manual-release-review")
    source_summaries = {prefix: summary(prefix) for prefix in required_evidence}
    return {
        "mode": "release-closure",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "missing": missing_count,
            "required_evidence": len(required_evidence),
            "executes_anything": False,
            "remote_configured": remote_configured,
            "command_drafts": len(command_drafts),
            "forbidden_findings": forbidden_total,
        },
        "required_evidence": required_evidence,
        "checks": checks,
        "source_summaries": _redact_public_value(source_summaries),
        "command_drafts": command_drafts,
        "publication_command_summary": publication_command_summary,
        "publication_boundary": [
            "Command drafts are classified by publication risk for human review only; they are never executed by this gate.",
            "A reviewer must copy/paste commands intentionally after inspecting safety, readiness, staging, handoff, provenance, and current git state.",
            "Credential checks and provider authentication remain outside this report-only gate; do not validate credentials or call GitHub/provider APIs here.",
            "Commit, repo-create, push, tag, and release-publish commands are manual publication actions, not automatic approval or automation.",
        ],
        "manual_review_boundary": [
            "This is a report-only release closure gate for manual release review.",
            "It does not commit, push, create remotes, publish GitHub repositories, upload archives, or execute command drafts.",
            "A human reviewer must inspect the release pack, staging tree, handoff bundle, provenance, and generated command drafts before any publication step.",
        ],
        "provenance_boundary": [
            "Release provenance remains unsigned local audit metadata.",
            "It verifies local artifact and tree consistency only; it is not an external authenticity proof or tamper-resistant attestation.",
        ],
        "recommendations": [
            "If status is blocked, regenerate the failing latest-* report(s) and rerun --release-closure --both.",
            "If status is ready-for-manual-release-review, proceed only to human review; do not treat this as automatic publish approval.",
            "Add signed provenance or external attestations in a future phase before making stronger supply-chain claims.",
        ],
    }



def build_public_docs_external_reader_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only review of whether public docs answer a first external reader's questions.

    This gate reads public docs and local latest-* evidence only. It does not execute
    hooks, publish, push, create remotes/repositories/tags/releases, call providers,
    validate credentials, or mutate runtime/admin/provider state.
    """
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    reports_dir = root / "bootstrap" / "reports"

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    readme = read_optional(root / "README.md")
    thesis = read_optional(docs_dir / "public-facing-thesis.md")
    release_plan = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh")
    combined = "\n".join([readme, thesis, release_plan, roadmap]).lower()

    def has_all(text: str, needles: List[str]) -> bool:
        lowered = text.lower()
        return all(needle.lower() in lowered for needle in needles)

    def has_any(text: str, needles: List[str]) -> bool:
        lowered = text.lower()
        return any(needle.lower() in lowered for needle in needles)

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    add_check(
        "reader:one-minute-promise",
        has_any(combined, ["one-minute", "60-second", "within one minute"]) and has_all(combined, ["portable ai assets", "without starting", "tools"]),
        "Public docs should make the core promise understandable in about one minute.",
    )
    add_check(
        "reader:non-goals-clear",
        has_any(combined, ["not another agent runtime", "not an agent runtime", "non-goals", "what this is not"])
        and has_any(combined, ["workflow builder", "memory saas", "memory backend"]),
        "Public docs should clearly say this is not a runtime, memory product, or workflow builder.",
    )
    add_check(
        "reader:public-private-boundary",
        has_any(combined, ["public/private boundary", "public repo includes", "private by default"])
        and has_any(combined, ["credentials", "tokens", "secrets"])
        and has_any(combined, ["private memory", "personal memory", "private project summaries"]),
        "Public docs should separate public engine/samples from private memory, identifiers, and secrets.",
    )
    add_check(
        "reader:quickstart-or-review-command",
        has_any(readme, ["fast public demo", "quickstart", "60-second overview"])
        or "--public-docs-external-reader-review" in combined,
        "README or release docs should give an obvious starting point or review command.",
    )
    add_check(
        "reader:portable-layer-scope",
        has_any(combined, ["portable ai assets layer", "portability layer"])
        and has_any(combined, ["cross-agent", "across agents"])
        and has_any(combined, ["cross-model", "models"])
        and has_any(combined, ["cross-client", "clients"])
        and has_any(combined, ["cross-machine", "machines"]),
        "Public docs should frame the product as a portable asset layer across agents/models/clients/machines.",
    )
    add_check(
        "reader:safety-review-boundary",
        has_any(combined, ["manual release review", "manual-review", "human review"])
        and has_any(combined, ["public-safety-scan", "safety gates", "report-only gates"]),
        "Public docs should show safety/manual review boundaries, not auto-publication.",
    )
    add_check(
        "release-plan:documents-external-reader-review",
        "--public-docs-external-reader-review" in release_plan,
        "docs/open-source-release-plan.md documents the external-reader review gate.",
    )
    add_check(
        "roadmap:phase80-documented",
        "phase 80" in roadmap.lower() and "external-reader" in roadmap.lower(),
        "docs/public-roadmap.md records Phase 80 external-reader review scope.",
    )
    add_check(
        "shell:external-reader-review-command",
        "--public-docs-external-reader-review" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --public-docs-external-reader-review.",
    )

    safety_summary = (_load_json_if_exists(reports_dir / "latest-public-safety-scan.json").get("summary") or {})
    readiness_summary = (_load_json_if_exists(reports_dir / "latest-release-readiness.json").get("summary") or {})
    freshness_summary = (_load_json_if_exists(reports_dir / "latest-public-package-freshness-review.json").get("summary") or {})
    add_check(
        "evidence:public-safety-scan",
        not safety_summary or (safety_summary.get("status") == "pass" and int(safety_summary.get("forbidden_findings", 0) or 0) == 0),
        str(safety_summary or "not generated yet; run --public-safety-scan --both before release review"),
    )
    add_check(
        "evidence:release-readiness",
        not readiness_summary or (readiness_summary.get("readiness") == "ready" and int(readiness_summary.get("fail", 0) or 0) == 0),
        str(readiness_summary or "not generated yet; run --release-readiness --both before release review"),
    )
    add_check(
        "evidence:package-freshness",
        not freshness_summary or (freshness_summary.get("status") in {"ready", "stale"} and freshness_summary.get("executes_anything") is False),
        str(freshness_summary or "not generated yet; run --public-package-freshness-review --both after regenerating pack/staging"),
    )

    forbidden_findings = int(safety_summary.get("forbidden_findings", 0) or 0) if isinstance(safety_summary, dict) else 0
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if forbidden_findings > 0 else ("needs-docs-review" if fail_count else "ready")

    return {
        "mode": "public-docs-external-reader-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "documents": {
            "readme": str(root / "README.md"),
            "public_facing_thesis": str(docs_dir / "public-facing-thesis.md"),
            "open_source_release_plan": str(docs_dir / "open-source-release-plan.md"),
            "public_roadmap": str(docs_dir / "public-roadmap.md"),
            "shell_wrapper": str(root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh"),
        },
        "reader_questions": [
            "Can a new reader explain in one minute that this is a portable AI assets layer?",
            "Can they tell it is not an agent runtime, memory SaaS/backend, chat UI, or workflow builder?",
            "Can they identify the public/private boundary for memory, project summaries, credentials, tokens, logs, and runtime state?",
            "Can they find a quickstart/demo or the --public-docs-external-reader-review --both command?",
            "Can they see that release review is report-only/manual and does not publish or validate credentials?",
        ],
        "checks": checks,
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": 0,
            "fail": fail_count,
            "forbidden_findings": forbidden_findings,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": False,
        },
        "review_boundary": [
            "Report-only external-reader comprehension review of public docs and local latest reports.",
            "Does not execute hooks/code/actions, publish, push, create remotes/repositories/tags/releases, call providers, validate credentials, or mutate runtime/admin/provider state.",
            "If status is needs-docs-review, update source docs and regenerate public pack/staging through existing local gates.",
        ],
        "recommendations": [
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --public-docs-external-reader-review --both after changing README or public docs.",
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --public-safety-scan --both before sharing public artifacts.",
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --public-release-pack --both and --public-repo-staging --both after this report changes.",
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --public-package-freshness-review --both immediately before manual release review.",
        ],
    }



def build_release_candidate_closure_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Aggregate the final local release-candidate evidence packet for human review.

    This gate is intentionally report-only. It reads latest-* reports and public docs,
    but does not publish, push, create remotes/repositories/tags/releases, call APIs,
    validate credentials, execute hooks/actions, or mutate runtime/admin/provider state.
    """
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    required_evidence = [
        "release-closure",
        "manual-release-reviewer-checklist",
        "public-docs-external-reader-review",
        "public-package-freshness-review",
        "public-safety-scan",
        "release-readiness",
        "github-final-preflight",
        "completed-work-review",
    ]
    reports: Dict[str, Dict[str, Any]] = {
        prefix: _load_latest_report_json_for_root(root, prefix) or {} for prefix in required_evidence
    }

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def source_summary(prefix: str) -> Dict[str, Any]:
        value = reports.get(prefix, {}).get("summary", {})
        return value if isinstance(value, dict) else {}

    def status_of(prefix: str) -> str:
        summary = source_summary(prefix)
        value = summary.get("status") or summary.get("readiness") or "missing"
        return str(value)

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({
            "name": name,
            "status": "pass" if ok else "fail",
            "detail": _redact_public_text(detail),
        })

    for prefix in required_evidence:
        add_check(f"evidence:{prefix}:present", bool(reports.get(prefix)), "present" if reports.get(prefix) else "missing latest report")

    add_check(
        "evidence:release-closure:ready",
        source_summary("release-closure").get("status") == "ready-for-manual-release-review",
        status_of("release-closure"),
    )
    add_check(
        "evidence:manual-release-reviewer-checklist:ready",
        source_summary("manual-release-reviewer-checklist").get("status") == "ready-for-human-review"
        and source_summary("manual-release-reviewer-checklist").get("manual_review_required") is True,
        str(source_summary("manual-release-reviewer-checklist")),
    )
    add_check(
        "evidence:public-docs-external-reader-review:ready",
        source_summary("public-docs-external-reader-review").get("status") == "ready",
        status_of("public-docs-external-reader-review"),
    )
    add_check(
        "evidence:public-package-freshness-review:ready",
        source_summary("public-package-freshness-review").get("status") == "ready",
        status_of("public-package-freshness-review"),
    )
    add_check(
        "evidence:public-safety-scan:pass",
        source_summary("public-safety-scan").get("status") == "pass"
        and int(source_summary("public-safety-scan").get("forbidden_findings", 0) or 0) == 0,
        str(source_summary("public-safety-scan")),
    )
    add_check(
        "evidence:release-readiness:ready",
        source_summary("release-readiness").get("readiness") == "ready" or source_summary("release-readiness").get("status") == "ready",
        status_of("release-readiness"),
    )
    add_check(
        "evidence:github-final-preflight:ready",
        source_summary("github-final-preflight").get("status") == "ready",
        status_of("github-final-preflight"),
    )
    add_check(
        "evidence:completed-work-review:aligned",
        source_summary("completed-work-review").get("status") in {"aligned", "ready"},
        status_of("completed-work-review"),
    )

    release_plan = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan.lower()
    add_check(
        "docs:release-plan-documents-final-closure",
        "--release-candidate-closure-review" in release_plan
        and "manual-release-reviewer-checklist" in release_plan
        and "public-docs-external-reader-review" in release_plan
        and "public-package-freshness-review" in release_plan
        and all(term in release_plan_lower for term in ["report-only", "credential", "push"]),
        "docs/open-source-release-plan.md should document the final report-only release-candidate closure review and boundary.",
    )
    add_check(
        "roadmap:phase81-documented",
        "phase 81" in roadmap.lower() and "release candidate" in roadmap.lower(),
        "docs/public-roadmap.md records Phase 81 release candidate closure review scope.",
    )
    add_check(
        "shell:release-candidate-closure-command",
        "--release-candidate-closure-review" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --release-candidate-closure-review.",
    )

    executes_anything = any(source_summary(prefix).get("executes_anything") is True for prefix in required_evidence)
    remote_configured = any(source_summary(prefix).get("remote_configured") is True for prefix in required_evidence)
    remote_mutation_allowed = any(source_summary(prefix).get("remote_mutation_allowed") is True for prefix in required_evidence)
    credential_validation_allowed = any(source_summary(prefix).get("credential_validation_allowed") is True for prefix in required_evidence)
    forbidden_findings = 0
    for prefix in required_evidence:
        value = source_summary(prefix).get("forbidden_findings")
        if isinstance(value, int):
            forbidden_findings += value
    add_check("report-only-sources", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")

    final_review_packet = [
        {
            "id": "human-final-review",
            "title": "Human reviewer makes the final go/no-go decision outside this tool.",
            "evidence": "latest-release-candidate-closure-review plus latest manual reviewer checklist",
            "status": "ready",
        },
        {
            "id": "manual-publication-boundary",
            "title": "Confirm no automatic publication, remote mutation, credential validation, or command execution is performed.",
            "evidence": "review_boundary and source summaries",
            "status": "ready" if not (executes_anything or remote_mutation_allowed or credential_validation_allowed) else "blocked",
        },
        {
            "id": "freshness-before-release",
            "title": "Confirm public docs, public package, staging, and manual reviewer evidence are fresh immediately before any manual release action.",
            "evidence": "latest-public-docs-external-reader-review and latest-public-package-freshness-review",
            "status": "ready" if source_summary("public-package-freshness-review").get("status") == "ready" else "blocked",
        },
    ]
    for item in final_review_packet:
        item["review_type"] = "manual"
        item["executes_anything"] = False
        item["auto_approves_release"] = False
        add_check(f"packet:{item['id']}", item.get("status") == "ready", str(item.get("status")))

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready-for-final-human-review"
    review_boundary = [
        "This is a final local release-candidate closure packet for human review; it is not automatic publish approval.",
        "It does not publish, push, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions, or mutate runtime/admin/provider state.",
        "Any real release action remains a separate explicit human operation after reviewing latest reports, checksums, public safety, command drafts, and public/private boundaries.",
    ]
    return {
        "mode": "release-candidate-closure-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "final_review_packet_items": len(final_review_packet),
        },
        "required_evidence": required_evidence,
        "source_summaries": _redact_public_value({prefix: source_summary(prefix) for prefix in required_evidence}),
        "checks": checks,
        "final_review_packet": _redact_public_value(final_review_packet),
        "review_boundary": review_boundary,
        "recommendations": [
            "Run /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --release-candidate-closure-review --both after manual-release-reviewer-checklist, public-docs-external-reader-review, and public-package-freshness-review.",
            "If status is blocked, regenerate the failing latest-* evidence report(s) and rerun --release-candidate-closure-review --both.",
            "Treat ready-for-final-human-review as a human handoff packet only, not automatic publish approval.",
            "Keep publication, credential validation, remote creation, tag creation, release creation, and push actions outside this report-only gate.",
        ],
    }



def build_release_reviewer_packet_index_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Build a report-only table of contents for human release reviewers.

    The index points reviewers at the latest local release evidence artifacts. It
    reads docs and latest-* reports only; it does not publish, push, create
    remotes/repositories/tags/releases, call APIs, validate credentials, execute
    hooks/actions, or mutate runtime/admin/provider state.
    """
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    reports_dir = root / "bootstrap" / "reports"
    packet_specs = [
        ("final-release-candidate-review", "Release candidate closure review", "release-candidate-closure-review", "Final local release-candidate evidence packet for human go/no-go review."),
        ("manual-reviewer-checklist", "Manual release reviewer checklist", "manual-release-reviewer-checklist", "Checklist for human review of release closure, command drafts, and boundaries."),
        ("release-closure", "Release closure", "release-closure", "Aggregated report-only closure gate before manual review."),
        ("public-docs-external-reader", "Public docs external-reader review", "public-docs-external-reader-review", "First-reader comprehension review for README, thesis, roadmap, and release plan."),
        ("public-package-freshness", "Public package freshness review", "public-package-freshness-review", "Checks local public package/staging freshness against reviewer evidence."),
        ("public-safety", "Public safety scan", "public-safety-scan", "Forbidden-text and public safety evidence."),
        ("release-readiness", "Release readiness", "release-readiness", "Readiness aggregation for required public docs and artifacts."),
        ("github-final-preflight", "GitHub final preflight", "github-final-preflight", "Final report-only GitHub publication preflight evidence."),
        ("public-release-pack", "Public release pack", "public-release-pack", "Redacted public release package report."),
        ("public-release-archive", "Public release archive", "public-release-archive", "Archive/checksum report for the latest public pack."),
        ("public-release-smoke-test", "Public release smoke test", "public-release-smoke-test", "Extracted archive smoke-test evidence."),
        ("completed-work-review", "Completed work review", "completed-work-review", "Post-phase alignment and boundary review."),
    ]
    source_prefixes = [spec[2] for spec in packet_specs]
    reports: Dict[str, Dict[str, Any]] = {
        prefix: _load_latest_report_json_for_root(root, prefix) or {} for prefix in source_prefixes
    }

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def source_summary(prefix: str) -> Dict[str, Any]:
        value = reports.get(prefix, {}).get("summary", {})
        return value if isinstance(value, dict) else {}

    def status_of(prefix: str) -> str:
        summary = source_summary(prefix)
        value = summary.get("status") or summary.get("readiness") or "missing"
        return str(value)

    def summary_bool(prefix: str, key: str) -> bool:
        return source_summary(prefix).get(key) is True

    packet_index: List[Dict[str, Any]] = []
    for item_id, title, prefix, reviewer_note in packet_specs:
        json_path = reports_dir / f"latest-{prefix}.json"
        md_path = reports_dir / f"latest-{prefix}.md"
        summary = source_summary(prefix)
        packet_index.append({
            "id": item_id,
            "title": title,
            "report_prefix": prefix,
            "json_path": str(json_path),
            "markdown_path": str(md_path),
            "exists": json_path.is_file() and md_path.is_file() and bool(reports.get(prefix)),
            "status": status_of(prefix),
            "reviewer_note": reviewer_note,
            "executes_anything": bool(summary.get("executes_anything")) if summary.get("executes_anything") is True else False,
            "remote_mutation_allowed": bool(summary.get("remote_mutation_allowed")) if summary.get("remote_mutation_allowed") is True else False,
            "credential_validation_allowed": bool(summary.get("credential_validation_allowed")) if summary.get("credential_validation_allowed") is True else False,
            "remote_configured": bool(summary.get("remote_configured")) if summary.get("remote_configured") is True else False,
            "forbidden_findings": int(summary.get("forbidden_findings", 0) or 0) if isinstance(summary.get("forbidden_findings", 0), int) else 0,
        })

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({
            "name": name,
            "status": "pass" if ok else "fail",
            "detail": _redact_public_text(detail),
        })

    for item in packet_index:
        add_check(f"packet:{item['report_prefix']}:present", bool(item["exists"]), f"{item['json_path']} and {item['markdown_path']}")

    ready_expectations = {
        "release-candidate-closure-review": {"ready-for-final-human-review"},
        "manual-release-reviewer-checklist": {"ready-for-human-review"},
        "release-closure": {"ready-for-manual-release-review"},
        "public-docs-external-reader-review": {"ready"},
        "public-package-freshness-review": {"ready"},
        "public-safety-scan": {"pass"},
        "release-readiness": {"ready"},
        "github-final-preflight": {"ready"},
        "completed-work-review": {"aligned", "ready"},
    }
    for prefix, expected in ready_expectations.items():
        add_check(f"evidence:{prefix}:ready", status_of(prefix) in expected, status_of(prefix))

    docs_release_plan = read_optional(docs_dir / "open-source-release-plan.md")
    docs_roadmap = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = docs_release_plan.lower()
    add_check(
        "docs:release-plan-documents-reviewer-packet-index",
        "--release-reviewer-packet-index" in docs_release_plan
        and "release-candidate-closure-review" in docs_release_plan
        and all(term in release_plan_lower for term in ["report-only", "credential", "push", "publish"]),
        "docs/open-source-release-plan.md documents reviewer packet index and report-only boundary.",
    )
    add_check(
        "roadmap:phase82-documented",
        "phase 82" in docs_roadmap.lower() and "reviewer packet" in docs_roadmap.lower(),
        "docs/public-roadmap.md records Phase 82 release reviewer packet index scope.",
    )
    add_check(
        "shell:release-reviewer-packet-index-command",
        "--release-reviewer-packet-index" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --release-reviewer-packet-index.",
    )

    executes_anything = any(item["executes_anything"] for item in packet_index)
    remote_mutation_allowed = any(item["remote_mutation_allowed"] for item in packet_index)
    credential_validation_allowed = any(item["credential_validation_allowed"] for item in packet_index)
    remote_configured = any(item["remote_configured"] for item in packet_index)
    forbidden_findings = sum(int(item.get("forbidden_findings", 0) or 0) for item in packet_index)
    add_check("report-only-sources", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")

    public_docs = [
        {"id": "readme", "path": "README.md", "exists": (root / "README.md").is_file(), "reviewer_note": "Project thesis, quickstart, and public positioning."},
        {"id": "public-facing-thesis", "path": "docs/public-facing-thesis.md", "exists": (docs_dir / "public-facing-thesis.md").is_file(), "reviewer_note": "External-reader value proposition and non-goals."},
        {"id": "open-source-release-plan", "path": "docs/open-source-release-plan.md", "exists": (docs_dir / "open-source-release-plan.md").is_file(), "reviewer_note": "Manual release gates and boundaries."},
        {"id": "public-roadmap", "path": "docs/public-roadmap.md", "exists": (docs_dir / "public-roadmap.md").is_file(), "reviewer_note": "Roadmap, phase history, and non-goals."},
    ]

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready"
    review_boundary = [
        "This release reviewer packet index is a report-only table of contents for human reviewers; it is not publication approval.",
        "It does not publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "Any real release action remains a separate explicit human operation after reviewing the indexed local evidence, checksums, public safety, and public/private boundaries.",
    ]
    return {
        "mode": "release-reviewer-packet-index",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "packet_items": len(packet_index),
            "public_doc_items": len(public_docs),
            "auto_approves_release": False,
        },
        "packet_index": _redact_public_value(packet_index),
        "public_docs": _redact_public_value(public_docs),
        "source_summaries": _redact_public_value({prefix: source_summary(prefix) for prefix in source_prefixes}),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Run /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --release-reviewer-packet-index --both after --release-candidate-closure-review --both and public-package-freshness-review --both.",
            "Use this report as a reviewer table of contents only; ready means the index is complete, not publication approval.",
            "If status is blocked, regenerate the missing/failing latest-* evidence report(s) and rerun --release-reviewer-packet-index --both.",
            "Keep publication, credential validation, remote creation, tag creation, release creation, push, and provider/API actions outside this report-only gate.",
        ],
    }


def build_release_reviewer_decision_log_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Build a local, report-only template for recording human release review decisions.

    This report intentionally does not decide, approve, publish, push, create
    remotes/repositories/tags/releases, call APIs, validate credentials, execute
    hooks/actions/commands, or mutate runtime/admin/provider state. It only
    checks that the reviewer packet index is ready and emits pending fields a
    human can fill outside automation.
    """
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    reports_dir = root / "bootstrap" / "reports"
    packet_report = _load_latest_report_json_for_root(root, "release-reviewer-packet-index") or {}
    packet_summary = packet_report.get("summary", {}) if isinstance(packet_report.get("summary", {}), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({
            "name": name,
            "status": "pass" if ok else "fail",
            "detail": _redact_public_text(detail),
        })

    packet_json = reports_dir / "latest-release-reviewer-packet-index.json"
    packet_md = reports_dir / "latest-release-reviewer-packet-index.md"
    add_check("packet-index:json-present", packet_json.is_file() and bool(packet_report), str(packet_json))
    add_check("packet-index:markdown-present", packet_md.is_file(), str(packet_md))
    add_check("evidence:release-reviewer-packet-index:ready", packet_summary.get("status") == "ready", str(packet_summary.get("status", "missing")))
    add_check("packet-index:manual-review-required", packet_summary.get("manual_review_required") is True, str(packet_summary))
    add_check("packet-index:not-auto-approval", packet_summary.get("auto_approves_release") is False, str(packet_summary.get("auto_approves_release")))

    executes_anything = packet_summary.get("executes_anything") is True
    remote_mutation_allowed = packet_summary.get("remote_mutation_allowed") is True
    credential_validation_allowed = packet_summary.get("credential_validation_allowed") is True
    remote_configured = packet_summary.get("remote_configured") is True
    forbidden_findings = int(packet_summary.get("forbidden_findings", 0) or 0) if isinstance(packet_summary.get("forbidden_findings", 0), int) else 0
    add_check("report-only-source", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")

    docs_release_plan = read_optional(docs_dir / "open-source-release-plan.md")
    docs_roadmap = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = docs_release_plan.lower()
    add_check(
        "docs:release-plan-documents-reviewer-decision-log",
        "--release-reviewer-decision-log" in docs_release_plan
        and "release-reviewer-packet-index" in docs_release_plan
        and all(term in release_plan_lower for term in ["report-only", "credential", "push", "publish", "approve"]),
        "docs/open-source-release-plan.md documents reviewer decision log and report-only/non-approval boundary.",
    )
    add_check(
        "roadmap:phase83-documented",
        "phase 83" in docs_roadmap.lower() and "decision log" in docs_roadmap.lower(),
        "docs/public-roadmap.md records Phase 83 release reviewer decision log scope.",
    )
    add_check(
        "shell:release-reviewer-decision-log-command",
        "--release-reviewer-decision-log" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --release-reviewer-decision-log.",
    )

    decision_log_template = [
        {"id": "reviewer-identity", "title": "Reviewer identity and timestamp", "prompt": "Record the human reviewer name/handle and review timestamp.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "evidence-reviewed", "title": "Evidence reviewed", "prompt": "List the packet index artifacts reviewed and any missing/stale evidence.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "public-private-boundary", "title": "Public/private boundary findings", "prompt": "Record whether public samples/docs/reports remain redacted and safe for publication.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "publication-boundary", "title": "Publication boundary findings", "prompt": "Record that no automated publish/push/tag/release/credential/API action is triggered by this gate.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "manual-decision", "title": "Manual reviewer decision", "prompt": "Record the human decision separately from this report; this template is not release approval.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "follow-up-notes", "title": "Follow-up notes", "prompt": "Record any required follow-up before a separate explicit human release action.", "status": "pending-human-entry", "executes_anything": False},
    ]

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "needs-human-review"
    review_boundary = [
        "This release reviewer decision log is a report-only local template/status artifact for human review notes; it is not release approval.",
        "It records pending human-review fields only and does not publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "Any go/no-go decision and any real release action remain separate explicit human operations outside this gate.",
    ]
    return {
        "mode": "release-reviewer-decision-log",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "decision_recorded": False,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "decision_log_items": len(decision_log_template),
            "auto_approves_release": False,
        },
        "decision_log_template": _redact_public_value(decision_log_template),
        "source_summaries": _redact_public_value({"release-reviewer-packet-index": packet_summary}),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Run /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --release-reviewer-decision-log --both after --release-reviewer-packet-index --both.",
            "Use this report as a local decision-log template only; needs-human-review means a human still must fill/review notes, not release approval.",
            "If status is blocked, regenerate the missing/failing reviewer packet index evidence and rerun --release-reviewer-decision-log --both.",
            "Keep publication, credential validation, remote creation, tag creation, release creation, push, provider/API actions, and final go/no-go decisions outside this report-only gate.",
        ],
    }



def build_external_reviewer_quickstart_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Build a report-only first-10-minutes path for external release reviewers."""
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    reports_dir = root / "bootstrap" / "reports"
    packet_report = _load_latest_report_json_for_root(root, "release-reviewer-packet-index") or {}
    decision_report = _load_latest_report_json_for_root(root, "release-reviewer-decision-log") or {}
    packet_summary = packet_report.get("summary", {}) if isinstance(packet_report.get("summary", {}), dict) else {}
    decision_summary = decision_report.get("summary", {}) if isinstance(decision_report.get("summary", {}), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": _redact_public_text(detail)})

    quickstart_path = [
        {"id": "readme-start-here", "title": "Repository README start-here", "path": "README.md", "why": "Explains the Portable AI Assets positioning and first external-reader entry point.", "executes_anything": False},
        {"id": "public-facing-thesis", "title": "Public-facing thesis", "path": "docs/public-facing-thesis.md", "why": "States why a portable AI work-environment asset layer matters and what it is not.", "executes_anything": False},
        {"id": "public-demo-pack", "title": "Redacted public demo pack", "path": "examples/redacted/public-demo-pack", "why": "Shows safe public examples without private paths, credentials, or customer data.", "executes_anything": False},
        {"id": "reviewer-packet-index", "title": "Release reviewer packet index", "path": "bootstrap/reports/latest-release-reviewer-packet-index.md", "why": "Single local index of final release-review artifacts for human review.", "executes_anything": False},
        {"id": "decision-log-template", "title": "Reviewer decision-log template", "path": "bootstrap/reports/latest-release-reviewer-decision-log.md", "why": "Human-review notes and manual decision placeholder; not release approval.", "executes_anything": False},
    ]
    for item in quickstart_path:
        path = root / str(item["path"])
        item["exists"] = path.exists()
        item["is_file"] = path.is_file()
        item["is_dir"] = path.is_dir()
        add_check(f"quickstart:{item['id']}:present", bool(item["exists"]), str(path))
        add_check(f"quickstart:{item['id']}:non-executing", item.get("executes_anything") is False, str(item.get("executes_anything")))

    readme_text = read_optional(root / "README.md")
    thesis_text = read_optional(docs_dir / "public-facing-thesis.md")
    release_plan_text = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap_text = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan_text.lower()
    add_check("entry:readme-explains-portability-layer", "portable ai assets" in readme_text.lower() and ("portability" in readme_text.lower() or "portable" in readme_text.lower()), "README.md explains the public entry point.")
    add_check("entry:public-thesis-explains-boundary", "public" in thesis_text.lower() and ("boundary" in thesis_text.lower() or "not" in thesis_text.lower()), "docs/public-facing-thesis.md explains public positioning/boundary.")
    add_check("evidence:release-reviewer-packet-index:ready", packet_summary.get("status") == "ready", str(packet_summary.get("status", "missing")))
    add_check("evidence:release-reviewer-decision-log:needs-human-review", decision_summary.get("status") == "needs-human-review", str(decision_summary.get("status", "missing")))
    add_check("packet-index:not-auto-approval", packet_summary.get("auto_approves_release") is False, str(packet_summary.get("auto_approves_release")))
    add_check("decision-log:not-auto-approval", decision_summary.get("auto_approves_release") is False, str(decision_summary.get("auto_approves_release")))

    source_summaries = {"release-reviewer-packet-index": packet_summary, "release-reviewer-decision-log": decision_summary}
    executes_anything = any(summary.get("executes_anything") is True for summary in source_summaries.values())
    remote_mutation_allowed = any(summary.get("remote_mutation_allowed") is True for summary in source_summaries.values())
    credential_validation_allowed = any(summary.get("credential_validation_allowed") is True for summary in source_summaries.values())
    remote_configured = any(summary.get("remote_configured") is True for summary in source_summaries.values())
    forbidden_findings = sum(int(summary.get("forbidden_findings", 0) or 0) for summary in source_summaries.values() if isinstance(summary.get("forbidden_findings", 0), int))
    add_check("report-only-source", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")
    add_check("docs:release-plan-documents-external-reviewer-quickstart", "--external-reviewer-quickstart" in release_plan_text and "release-reviewer-decision-log" in release_plan_text and all(term in release_plan_lower for term in ["report-only", "credential", "push", "publish", "approve", "execute"]), "docs/open-source-release-plan.md documents external reviewer quickstart and report-only/non-approval boundary.")
    add_check("roadmap:phase84-documented", "phase 84" in roadmap_text.lower() and "external reviewer quickstart" in roadmap_text.lower(), "docs/public-roadmap.md records Phase 84 external reviewer quickstart scope.")
    add_check("shell:external-reviewer-quickstart-command", "--external-reviewer-quickstart" in shell_wrapper, "bootstrap/setup/bootstrap-ai-assets.sh exposes --external-reviewer-quickstart.")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready"
    review_boundary = [
        "This external reviewer quickstart is a report-only local first-10-minutes path for human reviewers; it is not release approval.",
        "It checks discoverability of public docs and local release-review evidence only and does not publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "The release reviewer decision log remains needs-human-review; any go/no-go decision and real release action stay separate explicit human operations outside this gate.",
    ]
    return {
        "mode": "external-reviewer-quickstart",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "quickstart_items": len(quickstart_path),
            "auto_approves_release": False,
        },
        "quickstart_path": _redact_public_value(quickstart_path),
        "source_summaries": _redact_public_value(source_summaries),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Run /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-quickstart --both after --release-reviewer-decision-log --both.",
            "Use this as the external reviewer first-10-minutes path: README → public thesis → redacted demo pack → reviewer packet index → decision log template.",
            "If status is blocked, regenerate or document the missing public entry/evidence artifact and rerun --external-reviewer-quickstart --both.",
            "Keep publication, credential validation, remote creation, tag creation, release creation, push, provider/API actions, command execution, and final go/no-go decisions outside this report-only gate.",
        ],
    }


def build_external_reviewer_feedback_plan_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Build a report-only feedback capture/import plan for external reviewer notes.

    This gate turns the reviewer quickstart + decision-log evidence into a local
    follow-up planning surface only. It does not record a decision, approve a
    release, mutate issue trackers/backlogs, publish, push, create remotes/repos,
    call APIs, validate credentials, execute commands, or mutate runtime state.
    """
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    reports_dir = root / "bootstrap" / "reports"
    quickstart_report = _load_latest_report_json_for_root(root, "external-reviewer-quickstart") or {}
    decision_report = _load_latest_report_json_for_root(root, "release-reviewer-decision-log") or {}
    quickstart_summary = quickstart_report.get("summary", {}) if isinstance(quickstart_report.get("summary", {}), dict) else {}
    decision_summary = decision_report.get("summary", {}) if isinstance(decision_report.get("summary", {}), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": _redact_public_text(detail)})

    quickstart_json = reports_dir / "latest-external-reviewer-quickstart.json"
    quickstart_md = reports_dir / "latest-external-reviewer-quickstart.md"
    decision_json = reports_dir / "latest-release-reviewer-decision-log.json"
    decision_md = reports_dir / "latest-release-reviewer-decision-log.md"
    add_check("quickstart:json-present", quickstart_json.is_file() and bool(quickstart_report), str(quickstart_json))
    add_check("quickstart:markdown-present", quickstart_md.is_file(), str(quickstart_md))
    add_check("decision-log:json-present", decision_json.is_file() and bool(decision_report), str(decision_json))
    add_check("decision-log:markdown-present", decision_md.is_file(), str(decision_md))
    add_check("evidence:external-reviewer-quickstart:ready", quickstart_summary.get("status") == "ready", str(quickstart_summary.get("status", "missing")))
    add_check("evidence:release-reviewer-decision-log:needs-human-review", decision_summary.get("status") == "needs-human-review", str(decision_summary.get("status", "missing")))
    add_check("quickstart:not-auto-approval", quickstart_summary.get("auto_approves_release") is False, str(quickstart_summary.get("auto_approves_release")))
    add_check("decision-log:not-auto-approval", decision_summary.get("auto_approves_release") is False, str(decision_summary.get("auto_approves_release")))

    source_summaries = {"external-reviewer-quickstart": quickstart_summary, "release-reviewer-decision-log": decision_summary}
    executes_anything = any(summary.get("executes_anything") is True for summary in source_summaries.values())
    remote_mutation_allowed = any(summary.get("remote_mutation_allowed") is True for summary in source_summaries.values())
    credential_validation_allowed = any(summary.get("credential_validation_allowed") is True for summary in source_summaries.values())
    remote_configured = any(summary.get("remote_configured") is True for summary in source_summaries.values())
    forbidden_findings = sum(int(summary.get("forbidden_findings", 0) or 0) for summary in source_summaries.values() if isinstance(summary.get("forbidden_findings", 0), int))
    add_check("report-only-source", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")

    release_plan_text = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap_text = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-external-reviewer-feedback-plan",
        "--external-reviewer-feedback-plan" in release_plan_text
        and "external-reviewer-quickstart" in release_plan_text
        and "release-reviewer-decision-log" in release_plan_text
        and all(term in release_plan_lower for term in ["report-only", "credential", "push", "publish", "approve", "execute"]),
        "docs/open-source-release-plan.md documents external reviewer feedback plan and report-only/non-approval boundary.",
    )
    add_check(
        "roadmap:phase85-documented",
        "phase 85" in roadmap_text.lower() and "external reviewer feedback" in roadmap_text.lower(),
        "docs/public-roadmap.md records Phase 85 external reviewer feedback plan scope.",
    )
    add_check(
        "shell:external-reviewer-feedback-plan-command",
        "--external-reviewer-feedback-plan" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --external-reviewer-feedback-plan.",
    )

    feedback_capture_template = [
        {"id": "reviewer-notes-source", "title": "Reviewer notes source", "prompt": "Identify the human-filled decision log or reviewer note document that follow-ups come from.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "public-private-boundary-finding", "title": "Public/private boundary finding", "prompt": "Capture any public/private-boundary issue, redaction concern, or missing evidence noted by the reviewer.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "publication-boundary-finding", "title": "Publication boundary finding", "prompt": "Capture any concern about publication commands, credential checks, remote mutation, or release approval wording.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "usability-follow-up", "title": "External-reader usability follow-up", "prompt": "Capture confusing first-10-minutes navigation, docs, demo-pack, or packet-index feedback.", "status": "pending-human-entry", "executes_anything": False},
        {"id": "follow-up-backlog-entry", "title": "Follow-up backlog entry", "prompt": "Draft a local backlog/issue entry for each reviewed follow-up; do not create remote issues automatically.", "status": "pending-human-entry", "executes_anything": False},
    ]
    follow_up_backlog_drafts = [
        {"id": "public-private-boundary-follow-up", "title": "Public/private boundary follow-up draft", "category": "public-safety", "suggested_local_backlog_text": "Review and address any external reviewer public/private-boundary or redaction findings before publication.", "executes": False, "mutates_issues": False},
        {"id": "publication-boundary-follow-up", "title": "Publication boundary follow-up draft", "category": "release-boundary", "suggested_local_backlog_text": "Review and address any external reviewer concerns about commands, credentials, remote mutation, upload, or release approval wording.", "executes": False, "mutates_issues": False},
        {"id": "first-ten-minutes-usability-follow-up", "title": "First-10-minutes usability follow-up draft", "category": "reviewer-ergonomics", "suggested_local_backlog_text": "Improve README/thesis/demo-pack/packet-index navigation based on external reviewer first-10-minutes notes.", "executes": False, "mutates_issues": False},
    ]
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready-for-feedback-review"
    review_boundary = [
        "This external reviewer feedback plan is a report-only local capture/import plan for human notes; it is not release approval.",
        "It can guide local follow-up/backlog drafts, but it does not mutate issues, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "Any actual issue creation, backlog mutation, go/no-go decision, or real release action remains a separate explicit human operation outside this gate.",
    ]
    return {
        "mode": "external-reviewer-feedback-plan",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "decision_recorded": False,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "feedback_capture_items": len(feedback_capture_template),
            "follow_up_drafts": len(follow_up_backlog_drafts),
            "auto_approves_release": False,
        },
        "feedback_capture_template": _redact_public_value(feedback_capture_template),
        "follow_up_backlog_drafts": _redact_public_value(follow_up_backlog_drafts),
        "source_summaries": _redact_public_value(source_summaries),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Run /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-plan --both after --external-reviewer-quickstart --both and --release-reviewer-decision-log --both.",
            "Use this report to convert human reviewer notes into local follow-up drafts only; it does not create remote issues or mutate a backlog automatically.",
            "If status is blocked, regenerate the quickstart/decision-log evidence and rerun --external-reviewer-feedback-plan --both.",
            "Keep publication, credential validation, issue mutation, remote creation, tag creation, release creation, push, provider/API actions, command execution, and final go/no-go decisions outside this report-only gate.",
        ],
    }



def build_external_reviewer_feedback_status_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Build a report-only status check for a human-filled reviewer feedback file."""
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    reports_dir = root / "bootstrap" / "reports"
    feedback_file = root / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md"
    plan_report = _load_latest_report_json_for_root(root, "external-reviewer-feedback-plan") or {}
    plan_summary = plan_report.get("summary", {}) if isinstance(plan_report.get("summary", {}), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def field_value(text: str, field: str) -> str:
        prefix = f"{field}:"
        for line in text.splitlines():
            if line.strip().lower().startswith(prefix.lower()):
                return line.split(":", 1)[1].strip()
        return ""

    def bool_field(text: str, field: str) -> bool:
        return field_value(text, field).strip().lower() in {"true", "yes", "1", "approved", "recorded"}

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": _redact_public_text(detail)})

    plan_json = reports_dir / "latest-external-reviewer-feedback-plan.json"
    plan_md = reports_dir / "latest-external-reviewer-feedback-plan.md"
    add_check("feedback-plan:json-present", plan_json.is_file() and bool(plan_report), str(plan_json))
    add_check("feedback-plan:markdown-present", plan_md.is_file(), str(plan_md))
    add_check("evidence:external-reviewer-feedback-plan:ready", plan_summary.get("status") == "ready-for-feedback-review", str(plan_summary.get("status", "missing")))
    add_check("feedback-plan:not-auto-approval", plan_summary.get("auto_approves_release") is False, str(plan_summary.get("auto_approves_release")))

    feedback_text = read_optional(feedback_file)
    feedback_present = feedback_file.is_file()
    add_check("feedback-file:present", feedback_present, str(feedback_file))

    required_specs = [
        ("reviewer", "Human reviewer identity or handle"),
        ("reviewed_at", "Human review timestamp"),
        ("source_decision_log", "Decision log or notes source reviewed"),
        ("public_private_boundary", "Public/private-boundary reviewer finding"),
        ("publication_boundary", "Publication-boundary reviewer finding"),
        ("first_ten_minutes_usability", "External reviewer first-10-minutes usability notes"),
        ("follow_up_items", "Local follow-up items or explicit none"),
        ("approval_recorded", "Must be false; this gate does not record approval"),
        ("go_no_go_decision_recorded", "Must be false; this gate does not record go/no-go decisions"),
    ]
    required_feedback_fields: List[Dict[str, Any]] = []
    for field, description in required_specs:
        value = field_value(feedback_text, field)
        if field == "follow_up_items" and not value:
            value = "present" if "follow_up_items:" in feedback_text.lower() else ""
        present = bool(value)
        required_feedback_fields.append({
            "id": field,
            "description": description,
            "status": "present" if present else "missing",
            "executes_anything": False,
        })
        add_check(f"feedback-field:{field}:present", present, f"{field}={'present' if present else 'missing'}")

    approval_recorded = bool_field(feedback_text, "approval_recorded")
    go_no_go_recorded = bool_field(feedback_text, "go_no_go_decision_recorded")
    add_check("feedback-file:no-approval-recorded", not approval_recorded, f"approval_recorded={approval_recorded}")
    add_check("feedback-file:no-go-no-go-recorded", not go_no_go_recorded, f"go_no_go_decision_recorded={go_no_go_recorded}")

    follow_up_lines = [line.strip()[2:].strip() for line in feedback_text.splitlines() if line.strip().startswith("- ")]
    follow_up_review_items = [
        {"id": f"follow-up-{idx}", "text": _redact_public_text(text), "status": "pending-human-follow-up", "executes": False, "mutates_issues": False}
        for idx, text in enumerate(follow_up_lines, start=1)
        if text
    ]

    source_summaries = {"external-reviewer-feedback-plan": plan_summary}
    executes_anything = plan_summary.get("executes_anything") is True
    remote_mutation_allowed = plan_summary.get("remote_mutation_allowed") is True
    credential_validation_allowed = plan_summary.get("credential_validation_allowed") is True
    remote_configured = plan_summary.get("remote_configured") is True
    forbidden_findings = int(plan_summary.get("forbidden_findings", 0) or 0) if isinstance(plan_summary.get("forbidden_findings", 0), int) else 0
    add_check("report-only-source", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")

    release_plan_text = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap_text = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-external-reviewer-feedback-status",
        "--external-reviewer-feedback-status" in release_plan_text
        and "external-reviewer-feedback-plan" in release_plan_text
        and all(term in release_plan_lower for term in ["report-only", "credential", "push", "publish", "approve", "execute"]),
        "docs/open-source-release-plan.md documents feedback status and report-only/non-approval boundary.",
    )
    add_check(
        "roadmap:phase86-documented",
        "phase 86" in roadmap_text.lower() and "external reviewer feedback status" in roadmap_text.lower(),
        "docs/public-roadmap.md records Phase 86 external reviewer feedback status scope.",
    )
    add_check(
        "shell:external-reviewer-feedback-status-command",
        "--external-reviewer-feedback-status" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --external-reviewer-feedback-status.",
    )

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "needs-human-feedback" if fail_count else "ready-for-follow-up-review"
    present_required_fields = sum(1 for item in required_feedback_fields if item["status"] == "present")
    review_boundary = [
        "This external reviewer feedback status is a report-only local checker for a human-filled feedback file; it is not release approval.",
        "It summarizes local follow-up readiness only and does not mutate issues or backlogs, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "Any issue creation, backlog mutation, go/no-go decision, approval record, or real release action remains a separate explicit human operation outside this gate.",
    ]
    return {
        "mode": "external-reviewer-feedback-status",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "feedback_file_present": feedback_present,
            "decision_recorded": go_no_go_recorded,
            "approval_recorded": approval_recorded,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "required_fields": len(required_feedback_fields),
            "present_required_fields": present_required_fields,
            "follow_up_items": len(follow_up_review_items),
            "auto_approves_release": False,
        },
        "feedback_file": _redact_public_value({"path": str(feedback_file), "exists": feedback_present}),
        "required_feedback_fields": _redact_public_value(required_feedback_fields),
        "follow_up_review_items": _redact_public_value(follow_up_review_items),
        "source_summaries": _redact_public_value(source_summaries),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Run /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-status --both after a human creates bootstrap/reviewer-feedback/external-reviewer-feedback.md.",
            "Use this report to validate the local feedback file and summarize follow-up readiness only; it does not create remote issues or mutate a backlog automatically.",
            "If status is needs-human-feedback, complete missing fields or remove any approval/go-no-go markers before rerunning --external-reviewer-feedback-status --both.",
            "Keep publication, credential validation, issue mutation, remote creation, tag creation, release creation, push, provider/API actions, command execution, approval, and final go/no-go decisions outside this report-only gate.",
        ],
    }



def execute_external_reviewer_feedback_template(root: Path = ASSETS) -> Dict[str, Any]:
    """Write a human-fillable reviewer feedback template without creating the final feedback file."""
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    feedback_dir = root / "bootstrap" / "reviewer-feedback"
    template_path = feedback_dir / "external-reviewer-feedback.md.template"
    final_feedback_path = feedback_dir / "external-reviewer-feedback.md"
    status_report = _load_latest_report_json_for_root(root, "external-reviewer-feedback-status") or {}
    status_summary = status_report.get("summary", {}) if isinstance(status_report.get("summary", {}), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": _redact_public_text(detail)})

    template_fields = [
        {"id": "reviewer", "description": "Human reviewer identity or handle", "placeholder": "<human reviewer name/handle>", "executes_anything": False},
        {"id": "reviewed_at", "description": "Human review timestamp", "placeholder": "<YYYY-MM-DDTHH:MM:SS>", "executes_anything": False},
        {"id": "source_decision_log", "description": "Decision log or notes source reviewed", "placeholder": "bootstrap/reports/latest-release-reviewer-decision-log.md", "executes_anything": False},
        {"id": "public_private_boundary", "description": "Public/private-boundary reviewer finding", "placeholder": "<human finding or none>", "executes_anything": False},
        {"id": "publication_boundary", "description": "Publication-boundary reviewer finding", "placeholder": "<human finding or none>", "executes_anything": False},
        {"id": "first_ten_minutes_usability", "description": "External reviewer first-10-minutes usability notes", "placeholder": "<human usability notes>", "executes_anything": False},
        {"id": "follow_up_items", "description": "Local follow-up items or explicit none", "placeholder": "- <follow-up item or none>", "executes_anything": False},
        {"id": "approval_recorded", "description": "Must remain false; this template is not approval", "placeholder": "false", "executes_anything": False},
        {"id": "go_no_go_decision_recorded", "description": "Must remain false; this template is not a go/no-go decision", "placeholder": "false", "executes_anything": False},
    ]
    template_text = """# External Reviewer Feedback Template

This is a human-fillable draft. Copy this template to `external-reviewer-feedback.md` only after a human reviewer fills the fields below.

This template is not release approval, not a go/no-go decision, and not an instruction to publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues/backlogs, or execute hooks/actions/commands.

reviewer: <human reviewer name/handle>
reviewed_at: <YYYY-MM-DDTHH:MM:SS>
source_decision_log: bootstrap/reports/latest-release-reviewer-decision-log.md
public_private_boundary: <human finding or none>
publication_boundary: <human finding or none>
first_ten_minutes_usability: <human usability notes>
follow_up_items:
- <follow-up item or none>
approval_recorded: false
go_no_go_decision_recorded: false

## Human instructions

1. Fill every placeholder above.
2. Keep `approval_recorded: false` and `go_no_go_decision_recorded: false` unless a separate explicit human release process outside automation records a decision elsewhere.
3. Save the filled copy as `bootstrap/reviewer-feedback/external-reviewer-feedback.md`.
4. Rerun `/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-status --both`.
5. Do not use this template to create remote issues, publish releases, validate credentials, call APIs, or execute commands automatically.
"""
    feedback_dir.mkdir(parents=True, exist_ok=True)
    template_path.write_text(template_text, encoding="utf-8")

    add_check("feedback-status:needs-human-feedback", status_summary.get("status") in {"needs-human-feedback", "ready-for-follow-up-review"}, str(status_summary.get("status", "missing")))
    add_check("template:file-written", template_path.is_file(), str(template_path))
    add_check("template:final-feedback-not-created", not final_feedback_path.exists(), str(final_feedback_path))

    release_plan_text = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap_text = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-external-reviewer-feedback-template",
        "--external-reviewer-feedback-template" in release_plan_text
        and "external-reviewer-feedback" in release_plan_text
        and all(term in release_plan_lower for term in ["template-only", "report-only", "credential", "push", "publish", "approve", "execute"]),
        "docs/open-source-release-plan.md documents feedback template and template-only/report-only boundary.",
    )
    add_check(
        "roadmap:phase87-documented",
        "phase 87" in roadmap_text.lower() and "external reviewer feedback template" in roadmap_text.lower(),
        "docs/public-roadmap.md records Phase 87 external reviewer feedback template scope.",
    )
    add_check(
        "shell:external-reviewer-feedback-template-command",
        "--external-reviewer-feedback-template" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --external-reviewer-feedback-template.",
    )

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    review_boundary = [
        "This external reviewer feedback template generator is template-only/report-only; it is not release approval.",
        "It writes only `external-reviewer-feedback.md.template` and does not create the final human feedback file, does not mutate issues or backlogs, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "The Phase 86 status gate should remain needs-human-feedback until a human copies, fills, and saves the final `external-reviewer-feedback.md` file.",
    ]
    return {
        "mode": "external-reviewer-feedback-template",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": "blocked" if fail_count else "template-ready",
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "template_written": template_path.is_file(),
            "feedback_file_created": final_feedback_path.exists(),
            "writes_anything": True,
            "writes": 1,
            "template_fields": len(template_fields),
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": status_summary.get("remote_configured") is True,
            "forbidden_findings": int(status_summary.get("forbidden_findings", 0) or 0) if isinstance(status_summary.get("forbidden_findings", 0), int) else 0,
            "auto_approves_release": False,
        },
        "template_file": _redact_public_value({"path": str(template_path), "exists": template_path.is_file()}),
        "final_feedback_file": _redact_public_value({"path": str(final_feedback_path), "exists": final_feedback_path.exists()}),
        "template_fields": _redact_public_value(template_fields),
        "source_summaries": _redact_public_value({"external-reviewer-feedback-status": status_summary}),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Have a human copy bootstrap/reviewer-feedback/external-reviewer-feedback.md.template to external-reviewer-feedback.md only after filling the required fields.",
            "Rerun /bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-status --both after the human-filled file exists.",
            "Do not treat template-ready as release approval, go/no-go decision, issue creation, publication approval, or remote mutation permission.",
        ],
    }



def build_external_reviewer_feedback_followup_index_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Build a report-only index of external reviewer feedback follow-up artifacts."""
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    reports_dir = root / "bootstrap" / "reports"
    feedback_dir = root / "bootstrap" / "reviewer-feedback"
    template_report = _load_latest_report_json_for_root(root, "external-reviewer-feedback-template") or {}
    status_report = _load_latest_report_json_for_root(root, "external-reviewer-feedback-status") or {}
    plan_report = _load_latest_report_json_for_root(root, "external-reviewer-feedback-plan") or {}
    template_summary = template_report.get("summary", {}) if isinstance(template_report.get("summary", {}), dict) else {}
    status_summary = status_report.get("summary", {}) if isinstance(status_report.get("summary", {}), dict) else {}
    plan_summary = plan_report.get("summary", {}) if isinstance(plan_report.get("summary", {}), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": _redact_public_text(detail)})

    packet_items = [
        {"id": "feedback-template", "title": "Human-fillable feedback template", "path": "bootstrap/reviewer-feedback/external-reviewer-feedback.md.template", "required": True, "why": "Starting point a human copies/fills before the status gate can become ready.", "executes_anything": False},
        {"id": "feedback-status-report", "title": "External reviewer feedback status report", "path": "bootstrap/reports/latest-external-reviewer-feedback-status.md", "required": True, "why": "Shows whether a human-filled feedback file exists and is well-formed.", "executes_anything": False},
        {"id": "feedback-plan-report", "title": "External reviewer feedback plan report", "path": "bootstrap/reports/latest-external-reviewer-feedback-plan.md", "required": True, "why": "Explains how human notes map to local follow-up categories.", "executes_anything": False},
        {"id": "feedback-template-report", "title": "External reviewer feedback template report", "path": "bootstrap/reports/latest-external-reviewer-feedback-template.md", "required": True, "why": "Confirms template generation boundaries and non-approval status.", "executes_anything": False},
        {"id": "optional-filled-feedback-file", "title": "Optional human-filled feedback file", "path": "bootstrap/reviewer-feedback/external-reviewer-feedback.md", "required": False, "why": "Present only after a human copies/fills the template; absence is acceptable before human review.", "executes_anything": False},
    ]
    for item in packet_items:
        item_path = root / str(item["path"])
        item["exists"] = item_path.exists()
        item["is_file"] = item_path.is_file()
        if item["required"]:
            add_check(f"packet:{item['id']}:present", bool(item["exists"]), str(item_path))
        add_check(f"packet:{item['id']}:non-executing", item.get("executes_anything") is False, str(item.get("executes_anything")))

    add_check("evidence:external-reviewer-feedback-template:template-ready", template_summary.get("status") == "template-ready", str(template_summary.get("status", "missing")))
    add_check("evidence:external-reviewer-feedback-status:available", status_summary.get("status") in {"needs-human-feedback", "ready-for-follow-up-review"}, str(status_summary.get("status", "missing")))
    add_check("evidence:external-reviewer-feedback-plan:ready", plan_summary.get("status") == "ready-for-feedback-review", str(plan_summary.get("status", "missing")))
    add_check("template:not-auto-approval", template_summary.get("auto_approves_release") is False, str(template_summary.get("auto_approves_release")))
    add_check("status:not-auto-approval", status_summary.get("auto_approves_release") is False, str(status_summary.get("auto_approves_release")))
    add_check("plan:not-auto-approval", plan_summary.get("auto_approves_release") is False, str(plan_summary.get("auto_approves_release")))

    source_summaries = {
        "external-reviewer-feedback-template": template_summary,
        "external-reviewer-feedback-status": status_summary,
        "external-reviewer-feedback-plan": plan_summary,
    }
    executes_anything = any(summary.get("executes_anything") is True for summary in source_summaries.values())
    remote_mutation_allowed = any(summary.get("remote_mutation_allowed") is True for summary in source_summaries.values())
    credential_validation_allowed = any(summary.get("credential_validation_allowed") is True for summary in source_summaries.values())
    remote_configured = any(summary.get("remote_configured") is True for summary in source_summaries.values())
    forbidden_findings = sum(int(summary.get("forbidden_findings", 0) or 0) for summary in source_summaries.values() if isinstance(summary.get("forbidden_findings", 0), int))
    feedback_file_present = (feedback_dir / "external-reviewer-feedback.md").is_file()
    approval_recorded = status_summary.get("approval_recorded") is True
    decision_recorded = status_summary.get("decision_recorded") is True
    add_check("report-only-source", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")
    add_check("no-approval-recorded", not approval_recorded, f"approval_recorded={approval_recorded}")
    add_check("no-go-no-go-recorded", not decision_recorded, f"decision_recorded={decision_recorded}")

    release_plan_text = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap_text = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-external-reviewer-feedback-followup-index",
        "--external-reviewer-feedback-followup-index" in release_plan_text
        and "external-reviewer-feedback-template" in release_plan_text
        and "external-reviewer-feedback-status" in release_plan_text
        and "external-reviewer-feedback-plan" in release_plan_text
        and all(term in release_plan_lower for term in ["report-only", "credential", "push", "publish", "approve", "execute"]),
        "docs/open-source-release-plan.md documents feedback follow-up index and report-only/non-approval boundary.",
    )
    add_check(
        "roadmap:phase88-documented",
        "phase 88" in roadmap_text.lower() and "external reviewer feedback follow-up index" in roadmap_text.lower(),
        "docs/public-roadmap.md records Phase 88 external reviewer feedback follow-up index scope.",
    )
    add_check(
        "shell:external-reviewer-feedback-followup-index-command",
        "--external-reviewer-feedback-followup-index" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --external-reviewer-feedback-followup-index.",
    )

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    review_boundary = [
        "This external reviewer feedback follow-up index is report-only local navigation evidence; it is not release approval.",
        "It links humans to the template, status report, feedback plan, template report, and optional filled feedback file, but does not mutate issues or backlogs, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "The optional filled feedback file remains human-created; absence of that file is acceptable and should not be auto-filled by this index.",
    ]
    return {
        "mode": "external-reviewer-feedback-followup-index",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": "blocked" if fail_count else "ready",
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "packet_items": len(packet_items),
            "feedback_file_present": feedback_file_present,
            "decision_recorded": decision_recorded,
            "approval_recorded": approval_recorded,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "auto_approves_release": False,
        },
        "packet_items": _redact_public_value(packet_items),
        "source_summaries": _redact_public_value(source_summaries),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Use this index as local navigation for human follow-up review only; it does not create issues or mutate backlogs.",
            "If a filled feedback file is absent, have a human copy/fill the template and rerun --external-reviewer-feedback-status --both.",
            "Keep publication, credential validation, issue mutation, remote creation, tag creation, release creation, push, provider/API actions, command execution, approval, and final go/no-go decisions outside this report-only index.",
        ],
    }



def execute_external_reviewer_feedback_followup_candidates(root: Path = ASSETS) -> Dict[str, Any]:
    """Generate local follow-up candidate files from human-filled external reviewer feedback."""
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    reports_dir = root / "bootstrap" / "reports"
    feedback_file = root / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md"
    candidates_root = root / "bootstrap" / "candidates"
    status_report = _load_latest_report_json_for_root(root, "external-reviewer-feedback-status") or {}
    index_report = _load_latest_report_json_for_root(root, "external-reviewer-feedback-followup-index") or {}
    status_summary = status_report.get("summary", {}) if isinstance(status_report.get("summary", {}), dict) else {}
    index_summary = index_report.get("summary", {}) if isinstance(index_report.get("summary", {}), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": _redact_public_text(detail)})

    feedback_text = read_optional(feedback_file)
    feedback_file_present = feedback_file.is_file()
    add_check("feedback-file:present", feedback_file_present, str(feedback_file))
    add_check("evidence:external-reviewer-feedback-status:ready", status_summary.get("status") == "ready-for-follow-up-review", str(status_summary.get("status", "missing")))
    add_check("evidence:external-reviewer-feedback-followup-index:ready", index_summary.get("status") == "ready", str(index_summary.get("status", "missing")))
    approval_recorded = status_summary.get("approval_recorded") is True or "approval_recorded: true" in feedback_text.lower()
    decision_recorded = status_summary.get("decision_recorded") is True or "go_no_go_decision_recorded: true" in feedback_text.lower()
    add_check("feedback-file:no-approval-recorded", not approval_recorded, f"approval_recorded={approval_recorded}")
    add_check("feedback-file:no-go-no-go-recorded", not decision_recorded, f"decision_recorded={decision_recorded}")

    follow_up_items = [line.strip()[2:].strip() for line in feedback_text.splitlines() if line.strip().startswith("- ") and line.strip()[2:].strip()]
    add_check("feedback-file:follow-up-items-present", bool(follow_up_items), f"follow_up_items={len(follow_up_items)}")

    source_summaries = {
        "external-reviewer-feedback-status": status_summary,
        "external-reviewer-feedback-followup-index": index_summary,
    }
    executes_anything = any(summary.get("executes_anything") is True for summary in source_summaries.values())
    remote_mutation_allowed = any(summary.get("remote_mutation_allowed") is True for summary in source_summaries.values())
    credential_validation_allowed = any(summary.get("credential_validation_allowed") is True for summary in source_summaries.values())
    remote_configured = any(summary.get("remote_configured") is True for summary in source_summaries.values())
    forbidden_findings = sum(int(summary.get("forbidden_findings", 0) or 0) for summary in source_summaries.values() if isinstance(summary.get("forbidden_findings", 0), int))
    add_check("report-only-source", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")

    release_plan_text = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap_text = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-external-reviewer-feedback-followup-candidates",
        "--external-reviewer-feedback-followup-candidates" in release_plan_text
        and "external-reviewer-feedback-followup-index" in release_plan_text
        and all(term in release_plan_lower for term in ["local-only", "template-only", "report-only", "credential", "push", "publish", "approve", "execute"]),
        "docs/open-source-release-plan.md documents feedback follow-up candidates and local-only/template-only/report-only boundary.",
    )
    add_check(
        "roadmap:phase89-documented",
        "phase 89" in roadmap_text.lower() and "external reviewer feedback follow-up candidates" in roadmap_text.lower(),
        "docs/public-roadmap.md records Phase 89 external reviewer feedback follow-up candidates scope.",
    )
    add_check(
        "shell:external-reviewer-feedback-followup-candidates-command",
        "--external-reviewer-feedback-followup-candidates" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --external-reviewer-feedback-followup-candidates.",
    )

    pre_write_fail_count = sum(1 for check in checks if check["status"] == "fail")
    candidate_files: List[Dict[str, Any]] = []
    bundle_dir = candidates_root / f"external-reviewer-feedback-followups-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if pre_write_fail_count == 0:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / "REVIEW-INSTRUCTIONS.md").write_text(
            "# External reviewer feedback follow-up candidates\n\nThese are local candidate files for human review only. Do not treat them as remote issues, approvals, publication decisions, or executable commands.\n",
            encoding="utf-8",
        )
        for idx, item in enumerate(follow_up_items, start=1):
            filename = f"follow-up-{idx:02d}.candidate.md"
            rel_path = (bundle_dir / filename).relative_to(root)
            candidate_text = (
                f"# Follow-up candidate {idx}\n\n"
                "Status: candidate-needs-human-review\n"
                "Executes: false\n"
                "Mutates issues: false\n"
                "Auto-approves release: false\n\n"
                f"Source feedback item: {item}\n\n"
                "## Human review notes\n\n- Decide whether to create a real issue/backlog item outside automation.\n- Do not publish, push, call APIs, validate credentials, or execute commands from this candidate.\n"
            )
            (bundle_dir / filename).write_text(candidate_text, encoding="utf-8")
            candidate_files.append({"id": f"follow-up-{idx:02d}", "path": str(rel_path), "source_text": _redact_public_text(item), "executes": False, "mutates_issues": False, "status": "candidate-needs-human-review"})
    add_check("candidates:local-files-written", pre_write_fail_count != 0 or len(candidate_files) == len(follow_up_items), f"candidate_files={len(candidate_files)}")
    add_check("candidates:no-remote-issues-created", True, "remote_issues_created=0")

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    review_boundary = [
        "This external reviewer feedback follow-up candidate generator is local-only/template-only/report-only; it is not release approval.",
        "It writes only local candidate files for human review and does not create remote issues, mutate issues or backlogs, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "It only generates candidates when the feedback status gate is ready-for-follow-up-review; otherwise it remains blocked and writes no candidate files.",
    ]
    return {
        "mode": "external-reviewer-feedback-followup-candidates",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": "blocked" if fail_count else "candidates-generated",
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "feedback_file_present": feedback_file_present,
            "follow_up_items": len(follow_up_items),
            "candidate_files_written": len(candidate_files),
            "remote_issues_created": 0,
            "decision_recorded": decision_recorded,
            "approval_recorded": approval_recorded,
            "writes_anything": bool(candidate_files),
            "writes": len(candidate_files) + (1 if candidate_files else 0),
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "auto_approves_release": False,
        },
        "candidate_bundle": _redact_public_value({"path": str(bundle_dir.relative_to(root)), "exists": bundle_dir.is_dir()}),
        "candidate_files": _redact_public_value(candidate_files),
        "source_summaries": _redact_public_value(source_summaries),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Review generated candidate files locally; create real issues/backlog entries manually outside this gate if appropriate.",
            "If status is blocked, complete the human feedback file and rerun --external-reviewer-feedback-status --both before generating candidates.",
            "Keep publication, credential validation, issue mutation, remote creation, tag creation, release creation, push, provider/API actions, command execution, approval, and final go/no-go decisions outside this local candidate generator.",
        ],
    }



def build_external_reviewer_feedback_followup_candidate_status_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Scan local external reviewer feedback follow-up candidate bundles without mutation."""
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    reports_dir = root / "bootstrap" / "reports"
    candidates_root = root / "bootstrap" / "candidates"
    candidates_report = _load_latest_report_json_for_root(root, "external-reviewer-feedback-followup-candidates") or {}
    candidates_summary = candidates_report.get("summary", {}) if isinstance(candidates_report.get("summary", {}), dict) else {}
    candidate_bundle = candidates_report.get("candidate_bundle", {}) if isinstance(candidates_report.get("candidate_bundle", {}), dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": _redact_public_text(detail)})

    generated = candidates_summary.get("status") == "candidates-generated"
    add_check("evidence:external-reviewer-feedback-followup-candidates:generated", generated, str(candidates_summary.get("status", "missing")))

    bundle_rel = str(candidate_bundle.get("path", "") or "")
    bundle_path = (root / bundle_rel).resolve() if bundle_rel else candidates_root
    if root not in [bundle_path, *bundle_path.parents]:
        bundle_path = candidates_root
    bundle_exists = bundle_path.is_dir()
    add_check("candidate-bundle:exists", bundle_exists, str(bundle_path))

    candidate_paths = sorted(bundle_path.glob("*.candidate.md")) if bundle_exists else []
    add_check("candidate-bundle:has-candidate-files", bool(candidate_paths), f"candidate_files={len(candidate_paths)}")

    candidate_files: List[Dict[str, Any]] = []
    unsafe_candidates = 0
    human_reviewed_candidates = 0
    for path in candidate_paths:
        text = read_optional(path)
        lower = text.lower()
        executes = "executes: true" in lower
        mutates_issues = "mutates issues: true" in lower or "mutates_issues: true" in lower
        auto_approves = "auto-approves release: true" in lower or "auto_approves_release: true" in lower
        human_decision = "human decision:" in lower
        if executes or mutates_issues or auto_approves:
            unsafe_candidates += 1
        if human_decision:
            human_reviewed_candidates += 1
        status = "unknown"
        for line in text.splitlines():
            if line.lower().startswith("status:"):
                status = line.split(":", 1)[1].strip() or "unknown"
                break
        candidate_files.append({
            "path": str(path.relative_to(root)),
            "status": _redact_public_text(status),
            "human_reviewed": human_decision,
            "executes": executes,
            "mutates_issues": mutates_issues,
            "auto_approves_release": auto_approves,
        })
    add_check("candidates:all-local-non-executing", unsafe_candidates == 0, f"unsafe_candidates={unsafe_candidates}")
    add_check("candidates:no-remote-issues-created", candidates_summary.get("remote_issues_created", 0) == 0, f"remote_issues_created={candidates_summary.get('remote_issues_created', 0)}")

    executes_anything = candidates_summary.get("executes_anything") is True
    remote_mutation_allowed = candidates_summary.get("remote_mutation_allowed") is True
    credential_validation_allowed = candidates_summary.get("credential_validation_allowed") is True
    remote_configured = candidates_summary.get("remote_configured") is True
    forbidden_findings = int(candidates_summary.get("forbidden_findings", 0) or 0) if isinstance(candidates_summary.get("forbidden_findings", 0), int) else 0
    add_check("report-only-source", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_mutation_allowed and not remote_configured, f"remote_mutation_allowed={remote_mutation_allowed}; remote_configured={remote_configured}")
    add_check("no-credential-validation-enabled", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")

    release_plan_text = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap_text = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-external-reviewer-feedback-followup-candidate-status",
        "--external-reviewer-feedback-followup-candidate-status" in release_plan_text
        and "external-reviewer-feedback-followup-candidates" in release_plan_text
        and all(term in release_plan_lower for term in ["local-only", "report-only", "credential", "push", "publish", "approve", "execute", "mutate issues"]),
        "docs/open-source-release-plan.md documents feedback follow-up candidate status and local-only/report-only boundary.",
    )
    add_check(
        "roadmap:phase90-documented",
        "phase 90" in roadmap_text.lower() and "external reviewer feedback follow-up candidate status" in roadmap_text.lower(),
        "docs/public-roadmap.md records Phase 90 external reviewer feedback follow-up candidate status scope.",
    )
    add_check(
        "shell:external-reviewer-feedback-followup-candidate-status-command",
        "--external-reviewer-feedback-followup-candidate-status" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --external-reviewer-feedback-followup-candidate-status.",
    )

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready-for-manual-follow-up"
    review_boundary = [
        "This external reviewer feedback follow-up candidate status scanner is local-only/report-only; it is not release approval.",
        "It reads local candidate files only and does not create remote issues, mutate issues or backlogs, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.",
        "Human-reviewed candidate decisions are informational counters only; any real issue/backlog creation remains manual and outside this gate.",
    ]
    return {
        "mode": "external-reviewer-feedback-followup-candidate-status",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "manual_review_required": True,
            "candidate_bundle_present": bundle_exists,
            "candidate_files_scanned": len(candidate_files),
            "human_reviewed_candidates": human_reviewed_candidates,
            "unsafe_candidates": unsafe_candidates,
            "remote_issues_created": 0,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "auto_approves_release": False,
        },
        "candidate_bundle": _redact_public_value({"path": str(bundle_path.relative_to(root)) if root in [bundle_path, *bundle_path.parents] else "bootstrap/candidates", "exists": bundle_exists}),
        "candidate_files": _redact_public_value(candidate_files),
        "source_summaries": _redact_public_value({"external-reviewer-feedback-followup-candidates": candidates_summary}),
        "checks": checks,
        "review_boundary": review_boundary,
        "recommendations": [
            "Use this report as a local checklist only; create or defer real issues/backlog entries manually outside automation.",
            "If status is blocked, regenerate candidates only after human feedback is ready, then inspect unsafe or incomplete candidate files locally.",
            "Keep publication, credential validation, issue mutation, remote creation, tag creation, release creation, push, provider/API actions, command execution, approval, and final go/no-go decisions outside this status scanner.",
        ],
    }



def build_initial_completion_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only MVP closure review separating machine readiness from human actions."""
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    setup_dir = root / "bootstrap" / "setup"
    latest_prefixes = [
        "public-safety-scan",
        "release-readiness",
        "public-release-archive",
        "public-release-smoke-test",
        "public-release-pack",
        "public-repo-staging",
        "public-repo-staging-status",
        "public-package-freshness-review",
        "completed-work-review",
        "external-reviewer-feedback-template",
        "external-reviewer-feedback-status",
        "external-reviewer-feedback-followup-index",
        "external-reviewer-feedback-followup-candidates",
        "external-reviewer-feedback-followup-candidate-status",
    ]
    reports = {prefix: _load_latest_report_json_for_root(root, prefix) or {} for prefix in latest_prefixes}

    def summary(prefix: str) -> Dict[str, Any]:
        value = reports.get(prefix, {}).get("summary", {}) if isinstance(reports.get(prefix, {}), dict) else {}
        return value if isinstance(value, dict) else {}

    def read_optional(path: Path) -> str:
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str, warn: bool = False) -> None:
        checks.append({
            "name": name,
            "status": "pass" if ok else ("warn" if warn else "fail"),
            "detail": _redact_public_text(detail),
        })

    source_summaries = {prefix: summary(prefix) for prefix in latest_prefixes}
    optional_release_evidence = {"public-release-archive", "public-release-smoke-test", "public-repo-staging"}
    for prefix in latest_prefixes:
        add_check(
            f"evidence:{prefix}:present",
            bool(reports.get(prefix)),
            "present" if reports.get(prefix) else "missing latest report",
            warn=prefix in optional_release_evidence,
        )

    safety = summary("public-safety-scan")
    readiness = summary("release-readiness")
    archive = summary("public-release-archive")
    smoke = summary("public-release-smoke-test")
    pack = summary("public-release-pack")
    staging = summary("public-repo-staging")
    staging_status = summary("public-repo-staging-status")
    freshness = summary("public-package-freshness-review")
    completed = summary("completed-work-review")
    feedback_template = summary("external-reviewer-feedback-template")
    feedback_status = summary("external-reviewer-feedback-status")
    followup_index = summary("external-reviewer-feedback-followup-index")
    followup_candidates = summary("external-reviewer-feedback-followup-candidates")
    candidate_status = summary("external-reviewer-feedback-followup-candidate-status")

    archive_ok = (not archive) or str(archive.get("status", "")).lower() in {"ready", "pass", "archive-ready"} or bool(archive.get("archive_sha256"))
    smoke_ok = (not smoke) or str(smoke.get("status", "")).lower() in {"ready", "pass", "smoke-ready"}
    pack_ok = str(pack.get("status", "")).lower() in {"ready", "pass", "package-ready"} or (
        pack.get("public_safety_status") == "pass" and pack.get("release_readiness") == "ready"
    )
    staging_ok = (not staging) or str(staging.get("status", "")).lower() in {"ready", "pass", "staged", "staging-ready"}
    machine_release_ok = (
        safety.get("status") == "pass"
        and int(safety.get("blockers", 0) or 0) == 0
        and (readiness.get("readiness") == "ready" or readiness.get("status") == "ready")
        and int(readiness.get("fail", 0) or 0) == 0
        and archive_ok
        and smoke_ok
        and pack_ok
        and staging_ok
        and str(staging_status.get("status", "")).lower() in {"ready", "pass", "staging-ready"}
        and freshness.get("status") == "ready"
        and completed.get("status") == "aligned"
    )
    add_check("machine-readiness:public-release-gates-ready", machine_release_ok, "public safety/readiness/archive/smoke/pack/staging/freshness/completed-work reports are ready/aligned")

    external_review_navigation_ok = (
        feedback_template.get("status") == "template-ready"
        and feedback_template.get("feedback_file_created") is not True
        and followup_index.get("status") == "ready"
    )
    add_check("external-reviewer:navigation-and-template-ready", external_review_navigation_ok, "template and follow-up index exist without creating final human feedback")

    human_feedback_complete = feedback_status.get("status") == "ready" and feedback_status.get("feedback_file_present") is True
    add_check("human-feedback:final-feedback-file-status", human_feedback_complete, str(feedback_status.get("status", "missing")), warn=True)

    candidates_ready = (
        followup_candidates.get("status") in {"candidates-generated", "ready"}
        and int(followup_candidates.get("candidate_files_written", 0) or 0) > 0
        and candidate_status.get("status") == "ready-for-manual-follow-up"
        and candidate_status.get("candidate_bundle_present") is True
    )
    candidates_pending_due_to_human_feedback = (
        not candidates_ready
        and not human_feedback_complete
        and followup_candidates.get("status") == "blocked"
        and candidate_status.get("status") == "blocked"
    )
    add_check("human-feedback:followup-candidates-status", candidates_ready, "ready" if candidates_ready else "pending until human final feedback is supplied", warn=candidates_pending_due_to_human_feedback)

    safety_booleans = {
        "writes_anything": False,
        "executes_anything": False,
        "remote_mutation_allowed": False,
        "credential_validation_allowed": False,
        "auto_approves_release": False,
    }
    unsafe_details: List[str] = []
    for prefix, source in source_summaries.items():
        for key in safety_booleans:
            if source.get(key) is True:
                if prefix == "external-reviewer-feedback-template" and key == "writes_anything" and source.get("template_written") is True and source.get("feedback_file_created") is not True:
                    continue
                unsafe_details.append(f"{prefix}.{key}=true")
        if source.get("remote_configured") is True or source.get("remote_push_enabled") is True:
            unsafe_details.append(f"{prefix}.remote_configured_or_push_enabled=true")
        if int(source.get("remote_issues_created", 0) or 0) > 0:
            unsafe_details.append(f"{prefix}.remote_issues_created={source.get('remote_issues_created')}")
    add_check("boundary:no-execution-remote-mutation-credential-approval", not unsafe_details, "; ".join(unsafe_details) if unsafe_details else "all source summaries remain local/report-only")

    release_plan_text = read_optional(docs_dir / "open-source-release-plan.md")
    roadmap_text = read_optional(docs_dir / "public-roadmap.md")
    shell_wrapper = read_optional(setup_dir / "bootstrap-ai-assets.sh")
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-initial-completion-review",
        "--initial-completion-review" in release_plan_text and all(term in release_plan_lower for term in ["machine readiness", "human feedback", "manual publication", "report-only", "local-only", "credential", "publish", "push", "approve", "execute", "mutate"]),
        "docs/open-source-release-plan.md documents initial completion review and its non-mutating boundary.",
    )
    add_check(
        "roadmap:phase91-documented",
        "phase 91" in roadmap_text.lower() and "initial completion" in roadmap_text.lower(),
        "docs/public-roadmap.md records Phase 91 initial completion / MVP closure review.",
    )
    add_check(
        "shell:initial-completion-review-command",
        "--initial-completion-review" in shell_wrapper,
        "bootstrap/setup/bootstrap-ai-assets.sh exposes --initial-completion-review.",
    )

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    machine_readiness_ready = machine_release_ok and external_review_navigation_ok and not unsafe_details
    if fail_count:
        status = "blocked"
    elif human_feedback_complete and candidates_ready:
        status = "initial-completion-ready"
    else:
        status = "machine-ready-human-feedback-pending" if machine_readiness_ready else "blocked"

    human_handoff_required = [
        "Manual: a human reviewer must create/fill bootstrap/reviewer-feedback/external-reviewer-feedback.md from the template before feedback follow-up candidates can become ready.",
        "Manual: publication, repository creation, push/tag/release, credential checks, uploads, issue/backlog mutation, and go/no-go approval stay outside automation.",
    ]
    return {
        "mode": "initial-completion-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "machine_readiness_ready": machine_readiness_ready,
            "human_feedback_complete": human_feedback_complete,
            "human_action_required": not (human_feedback_complete and candidates_ready),
            "followup_candidates_ready": candidates_ready,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": False,
            "auto_approves_release": False,
        },
        "source_summaries": _redact_public_value(source_summaries),
        "checks": checks,
        "human_handoff_required": human_handoff_required,
        "review_boundary": [
            "This initial completion review is local-only/report-only and does not approve a release.",
            "It reads latest local reports/docs only; it does not publish, push, commit, tag, create releases/repos/remotes, call APIs/providers, validate credentials, upload artifacts, execute hooks/actions/commands, or mutate issues/backlogs.",
            "Machine readiness can be true while human feedback remains pending; this is expected and must not be auto-filled.",
        ],
        "recommendations": [
            "If status is machine-ready-human-feedback-pending, treat engineering MVP closure as locally ready for human handoff, not as publication approval.",
            "Have a human copy and fill bootstrap/reviewer-feedback/external-reviewer-feedback.md from the template before rerunning follow-up candidate gates.",
            "Keep final publication and go/no-go decisions manual and explicit.",
        ],
    }


def build_human_action_closure_checklist_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only checklist telling a human what remains after initial completion review."""
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    reviewer_dir = root / "bootstrap" / "reviewer-feedback"
    feedback_template = reviewer_dir / "external-reviewer-feedback.md.template"
    feedback_file = reviewer_dir / "external-reviewer-feedback.md"
    required_evidence = [
        "initial-completion-review",
        "external-reviewer-feedback-template",
        "external-reviewer-feedback-status",
        "external-reviewer-feedback-followup-candidates",
        "external-reviewer-feedback-followup-candidate-status",
    ]
    reports: Dict[str, Dict[str, Any]] = {
        prefix: _load_latest_report_json_for_root(root, prefix) or {} for prefix in required_evidence
    }

    def source_summary(prefix: str) -> Dict[str, Any]:
        value = reports.get(prefix, {}).get("summary", {})
        return value if isinstance(value, dict) else {}

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str, severity: str = "fail") -> None:
        status = "pass" if ok else ("warn" if severity == "warn" else "fail")
        checks.append({
            "name": name,
            "status": status,
            "detail": _redact_public_text(detail),
        })

    initial_summary = source_summary("initial-completion-review")
    feedback_template_summary = source_summary("external-reviewer-feedback-template")
    feedback_status_summary = source_summary("external-reviewer-feedback-status")
    candidates_summary = source_summary("external-reviewer-feedback-followup-candidates")
    candidate_status_summary = source_summary("external-reviewer-feedback-followup-candidate-status")

    initial_status = str(initial_summary.get("status") or "")
    machine_readiness_ready = initial_summary.get("machine_readiness_ready") is True or initial_status == "initial-completion-ready"
    human_feedback_complete = initial_summary.get("human_feedback_complete") is True or feedback_status_summary.get("status") in {"ready", "ready-for-follow-up-review"}
    human_feedback_pending = not human_feedback_complete
    followup_candidates_ready = candidate_status_summary.get("status") in {"ready-for-manual-follow-up", "ready"} or candidate_status_summary.get("candidate_bundle_present") is True

    for prefix in required_evidence:
        add_check(f"evidence:{prefix}:present", bool(reports.get(prefix)), "present" if reports.get(prefix) else "missing latest report")
    add_check(
        "initial-completion:machine-ready-human-feedback-pending",
        initial_status in {"machine-ready-human-feedback-pending", "initial-completion-ready"} and machine_readiness_ready,
        initial_status or "missing",
    )
    add_check("feedback-template:present", feedback_template.is_file() or feedback_template_summary.get("status") == "template-ready", str(feedback_template.relative_to(root)) if feedback_template.exists() else str(feedback_template_summary.get("status") or "missing"))
    add_check("feedback-file:human-owned", True, "final external-reviewer-feedback.md is never created or filled by this gate")
    add_check("feedback-status:human-feedback-pending-visible", feedback_status_summary.get("status") in {"needs-human-feedback", "ready", "ready-for-follow-up-review"}, str(feedback_status_summary.get("status") or "missing"))
    add_check("followup-candidates:blocked-until-human-feedback", candidates_summary.get("status") in {"blocked", "candidates-generated", "ready"}, str(candidates_summary.get("status") or "missing"))
    add_check("candidate-status:manual-review-state-visible", candidate_status_summary.get("status") in {"blocked", "ready-for-manual-follow-up", "ready"}, str(candidate_status_summary.get("status") or "missing"))

    release_plan_path = root / "docs" / "open-source-release-plan.md"
    roadmap_path = root / "docs" / "public-roadmap.md"
    shell_path = root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh"
    release_plan_text = release_plan_path.read_text(encoding="utf-8", errors="replace") if release_plan_path.is_file() else ""
    roadmap_text = roadmap_path.read_text(encoding="utf-8", errors="replace") if roadmap_path.is_file() else ""
    shell_text = shell_path.read_text(encoding="utf-8", errors="replace") if shell_path.is_file() else ""
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-human-action-closure-checklist",
        "--human-action-closure-checklist" in release_plan_text and all(term in release_plan_lower for term in ["local-only", "report-only", "human feedback", "follow-up", "manual publication", "approving", "publishing", "pushing", "credentials", "apis", "executing"]),
        "docs/open-source-release-plan.md documents Phase 92 human action checklist and boundaries.",
    )
    add_check("roadmap:phase92-documented", "Phase 92" in roadmap_text and "Human action closure checklist" in roadmap_text, "docs/public-roadmap.md records Phase 92 human action closure checklist.")
    add_check("shell:human-action-closure-checklist-command", "--human-action-closure-checklist" in shell_text, "bootstrap/setup/bootstrap-ai-assets.sh exposes --human-action-closure-checklist.")

    unsafe_sources = [initial_summary, feedback_status_summary, candidates_summary, candidate_status_summary]
    executes_anything = any(summary.get("executes_anything") is True for summary in unsafe_sources)
    remote_mutation_allowed = any(summary.get("remote_mutation_allowed") is True for summary in unsafe_sources)
    credential_validation_allowed = any(summary.get("credential_validation_allowed") is True for summary in unsafe_sources)
    auto_approves_release = any(summary.get("auto_approves_release") is True for summary in unsafe_sources)
    remote_issues_created = sum(int(summary.get("remote_issues_created") or 0) for summary in unsafe_sources if isinstance(summary.get("remote_issues_created") or 0, int))
    add_check("safety:no-execution", not executes_anything, f"executes_anything={executes_anything}")
    add_check("safety:no-remote-mutation", not remote_mutation_allowed and remote_issues_created == 0, f"remote_mutation_allowed={remote_mutation_allowed}; remote_issues_created={remote_issues_created}")
    add_check("safety:no-credential-validation", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("safety:no-auto-release-approval", not auto_approves_release, f"auto_approves_release={auto_approves_release}")

    human_action_checklist = [
        {
            "id": "copy-fill-external-reviewer-feedback",
            "title": "Human copies the feedback template and fills bootstrap/reviewer-feedback/external-reviewer-feedback.md.",
            "evidence": "bootstrap/reviewer-feedback/external-reviewer-feedback.md.template",
            "status": "pending" if human_feedback_pending else "done",
        },
        {
            "id": "rerun-external-reviewer-feedback-status",
            "title": "Rerun --external-reviewer-feedback-status --both after the human-filled feedback file exists.",
            "evidence": "latest-external-reviewer-feedback-status",
            "status": "pending" if human_feedback_pending else "ready",
        },
        {
            "id": "generate-local-followup-candidates",
            "title": "Only after ready feedback, run --external-reviewer-feedback-followup-candidates --both to create local candidate drafts.",
            "evidence": "latest-external-reviewer-feedback-followup-candidates",
            "status": "pending" if not followup_candidates_ready else "ready",
        },
        {
            "id": "review-followup-candidates-manually",
            "title": "Human reviews local follow-up candidates before any issue/backlog handling outside automation.",
            "evidence": "latest-external-reviewer-feedback-followup-candidate-status",
            "status": "pending" if not followup_candidates_ready else "ready",
        },
        {
            "id": "manual-publication-decision",
            "title": "Human makes any external sharing/publication decision manually; this checklist does not approve or publish.",
            "evidence": "latest-initial-completion-review plus manual reviewer packet",
            "status": "pending",
        },
    ]
    for item in human_action_checklist:
        item["review_type"] = "manual"
        item["executes_anything"] = False
        item["auto_approves_release"] = False

    for item in human_action_checklist:
        add_check(f"human-action:{item['id']}", True, str(item.get("status")))

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready-for-human-action"
    human_action_required = [
        "Human copy/fill bootstrap/reviewer-feedback/external-reviewer-feedback.md from bootstrap/reviewer-feedback/external-reviewer-feedback.md.template.",
        "Human rerun feedback status and local follow-up candidate gates after final feedback exists.",
        "Human manually review any local follow-up candidates before creating issues or backlog entries outside this automation.",
        "Human make any publication/share/go-no-go decision outside this report-only gate.",
    ]
    review_boundary = [
        "This checklist is local-only/report-only guidance for a human; it does not create or fill final feedback.",
        "It does not approve release, record go/no-go, publish, upload, commit, push, tag, create remotes/repos/releases, validate credentials, call APIs/providers, mutate issues/backlogs, or execute hooks/actions/commands.",
        "Machine readiness can be true while human feedback remains pending; the pending human actions are explicit checklist items, not automated tasks.",
    ]
    return {
        "mode": "human-action-closure-checklist",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "machine_readiness_ready": machine_readiness_ready,
            "human_feedback_complete": human_feedback_complete,
            "human_feedback_pending": human_feedback_pending,
            "manual_review_required": True,
            "followup_candidates_ready": followup_candidates_ready,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
        },
        "required_evidence": required_evidence,
        "source_summaries": _redact_public_value({prefix: source_summary(prefix) for prefix in required_evidence}),
        "checks": checks,
        "human_action_checklist": _redact_public_value(human_action_checklist),
        "human_action_required": human_action_required,
        "review_boundary": review_boundary,
        "feedback_paths": {
            "template": str(feedback_template.relative_to(root)) if feedback_template.is_relative_to(root) else str(feedback_template),
            "final_feedback_file": str(feedback_file.relative_to(root)) if feedback_file.is_relative_to(root) else str(feedback_file),
            "final_feedback_file_present": feedback_file.is_file(),
        },
        "recommendations": [
            "If status is blocked, regenerate the missing latest-* evidence reports and rerun --human-action-closure-checklist --both.",
            "If status is ready-for-human-action, hand this checklist to a human; do not treat it as release approval.",
            "Do not create the final external reviewer feedback file, issues, backlog entries, remotes, tags, releases, uploads, or credential checks from this gate.",
        ],
    }


def build_manual_reviewer_execution_packet_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only one-page runbook index for the human reviewer execution sequence."""
    root = root.expanduser().resolve()
    reports_dir = root / "bootstrap" / "reports"
    reviewer_dir = root / "bootstrap" / "reviewer-feedback"
    feedback_template = reviewer_dir / "external-reviewer-feedback.md.template"
    feedback_file = reviewer_dir / "external-reviewer-feedback.md"
    required_evidence = [
        "human-action-closure-checklist",
        "external-reviewer-feedback-template",
        "external-reviewer-feedback-followup-index",
        "external-reviewer-quickstart",
        "release-reviewer-packet-index",
        "public-repo-staging-status",
    ]
    reports: Dict[str, Dict[str, Any]] = {
        prefix: _load_latest_report_json_for_root(root, prefix) or {} for prefix in required_evidence
    }

    def source_summary(prefix: str) -> Dict[str, Any]:
        value = reports.get(prefix, {}).get("summary", {})
        return value if isinstance(value, dict) else {}

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str, severity: str = "fail") -> None:
        status = "pass" if ok else ("warn" if severity == "warn" else "fail")
        checks.append({"name": name, "status": status, "detail": _redact_public_text(detail)})

    closure_summary = source_summary("human-action-closure-checklist")
    template_summary = source_summary("external-reviewer-feedback-template")
    followup_index_summary = source_summary("external-reviewer-feedback-followup-index")
    quickstart_summary = source_summary("external-reviewer-quickstart")
    packet_index_summary = source_summary("release-reviewer-packet-index")
    staging_status_summary = source_summary("public-repo-staging-status")

    for prefix in required_evidence:
        add_check(f"evidence:{prefix}:present", bool(reports.get(prefix)), "present" if reports.get(prefix) else "missing latest report")
    add_check(
        "evidence:human-action-closure-checklist:ready",
        closure_summary.get("status") == "ready-for-human-action",
        str(closure_summary.get("status") or "missing"),
    )
    add_check("evidence:feedback-template:ready", feedback_template.is_file() or template_summary.get("status") == "template-ready", str(template_summary.get("status") or "missing"))
    add_check("evidence:followup-index:navigable", followup_index_summary.get("status") in {"ready", "blocked"}, str(followup_index_summary.get("status") or "missing"))
    add_check("evidence:external-reviewer-quickstart:ready", quickstart_summary.get("status") in {"ready", "needs-human-review"}, str(quickstart_summary.get("status") or "missing"))
    add_check("evidence:release-reviewer-packet-index:ready", packet_index_summary.get("status") == "ready", str(packet_index_summary.get("status") or "missing"))
    add_check("evidence:staging-status:no-remote-required", staging_status_summary.get("remote_configured") is not True, f"remote_configured={staging_status_summary.get('remote_configured')}")

    release_plan_path = root / "docs" / "open-source-release-plan.md"
    roadmap_path = root / "docs" / "public-roadmap.md"
    shell_path = root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh"
    release_plan_text = release_plan_path.read_text(encoding="utf-8", errors="replace") if release_plan_path.is_file() else ""
    roadmap_text = roadmap_path.read_text(encoding="utf-8", errors="replace") if roadmap_path.is_file() else ""
    shell_text = shell_path.read_text(encoding="utf-8", errors="replace") if shell_path.is_file() else ""
    release_plan_lower = release_plan_text.lower()
    add_check(
        "docs:release-plan-documents-manual-reviewer-execution-packet",
        "--manual-reviewer-execution-packet" in release_plan_text and all(term in release_plan_lower for term in ["local-only", "report-only", "one-page", "human runbook", "feedback", "follow-up", "manual publication", "approving", "publishing", "pushing", "credentials", "apis", "executing"]),
        "docs/open-source-release-plan.md documents Phase 93 manual reviewer execution packet and boundaries.",
    )
    add_check("roadmap:phase93-documented", "Phase 93" in roadmap_text and "Manual reviewer execution packet" in roadmap_text, "docs/public-roadmap.md records Phase 93 manual reviewer execution packet.")
    add_check("shell:manual-reviewer-execution-packet-command", "--manual-reviewer-execution-packet" in shell_text, "bootstrap/setup/bootstrap-ai-assets.sh exposes --manual-reviewer-execution-packet.")

    unsafe_sources = [closure_summary, template_summary, followup_index_summary, quickstart_summary, packet_index_summary, staging_status_summary]
    executes_anything = any(summary.get("executes_anything") is True for summary in unsafe_sources)
    remote_mutation_allowed = any(summary.get("remote_mutation_allowed") is True for summary in unsafe_sources)
    credential_validation_allowed = any(summary.get("credential_validation_allowed") is True for summary in unsafe_sources)
    auto_approves_release = any(summary.get("auto_approves_release") is True for summary in unsafe_sources)
    remote_issues_created = sum(int(summary.get("remote_issues_created") or 0) for summary in unsafe_sources if isinstance(summary.get("remote_issues_created") or 0, int))
    add_check("safety:no-execution", not executes_anything, f"executes_anything={executes_anything}")
    add_check("safety:no-remote-mutation", not remote_mutation_allowed and remote_issues_created == 0, f"remote_mutation_allowed={remote_mutation_allowed}; remote_issues_created={remote_issues_created}")
    add_check("safety:no-credential-validation", not credential_validation_allowed, f"credential_validation_allowed={credential_validation_allowed}")
    add_check("safety:no-auto-release-approval", not auto_approves_release, f"auto_approves_release={auto_approves_release}")

    human_feedback_pending = closure_summary.get("human_feedback_pending") is not False
    followup_candidates_ready = closure_summary.get("followup_candidates_ready") is True
    human_runbook_steps = [
        {
            "id": "read-one-page-packet",
            "title": "Human reads this packet, latest human-action closure checklist, external reviewer quickstart, and release reviewer packet index.",
            "evidence": "latest-manual-reviewer-execution-packet plus latest-human-action-closure-checklist",
            "status": "ready",
        },
        {
            "id": "copy-fill-feedback-file",
            "title": "Human copies the template and fills bootstrap/reviewer-feedback/external-reviewer-feedback.md; automation must not fabricate it.",
            "evidence": "bootstrap/reviewer-feedback/external-reviewer-feedback.md.template",
            "status": "pending" if human_feedback_pending else "done",
        },
        {
            "id": "rerun-feedback-status",
            "title": "Human reruns feedback status after the filled feedback file exists.",
            "evidence": "latest-external-reviewer-feedback-status",
            "status": "pending" if human_feedback_pending else "ready",
        },
        {
            "id": "generate-and-review-local-followups",
            "title": "After ready feedback, generate local follow-up candidates and manually review them before any issue/backlog action outside automation.",
            "evidence": "latest-external-reviewer-feedback-followup-candidates and latest-external-reviewer-feedback-followup-candidate-status",
            "status": "pending" if not followup_candidates_ready else "ready",
        },
        {
            "id": "manual-publication-or-sharing-decision",
            "title": "Human makes any publication/share/go-no-go decision outside this report-only runbook.",
            "evidence": "manual release/reviewer decision records outside automation",
            "status": "pending",
        },
    ]
    for step in human_runbook_steps:
        step["review_type"] = "manual"
        step["executes_anything"] = False
        step["auto_approves_release"] = False
    for step in human_runbook_steps:
        add_check(f"human-runbook:{step['id']}", True, str(step.get("status")))

    manual_command_sequence = [
        "cp bootstrap/reviewer-feedback/external-reviewer-feedback.md.template bootstrap/reviewer-feedback/external-reviewer-feedback.md  # human-run outside gate, then edit manually",
        "./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-status --both",
        "./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-followup-candidates --both",
        "./bootstrap/setup/bootstrap-ai-assets.sh --external-reviewer-feedback-followup-candidate-status --both",
        "./bootstrap/setup/bootstrap-ai-assets.sh --initial-completion-review --both",
        "./bootstrap/setup/bootstrap-ai-assets.sh --human-action-closure-checklist --both",
        "./bootstrap/setup/bootstrap-ai-assets.sh --manual-reviewer-execution-packet --both",
    ]
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready-for-human-runbook"
    return {
        "mode": "manual-reviewer-execution-packet",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "manual_review_required": True,
            "human_feedback_pending": human_feedback_pending,
            "followup_candidates_ready": followup_candidates_ready,
            "one_page_runbook_ready": status == "ready-for-human-runbook",
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
        },
        "required_evidence": required_evidence,
        "source_summaries": _redact_public_value({prefix: source_summary(prefix) for prefix in required_evidence}),
        "checks": checks,
        "human_runbook_steps": _redact_public_value(human_runbook_steps),
        "manual_command_sequence": manual_command_sequence,
        "human_owned_inputs": [
            str(feedback_template.relative_to(root)) if feedback_template.is_relative_to(root) else str(feedback_template),
            str(feedback_file.relative_to(root)) if feedback_file.is_relative_to(root) else str(feedback_file),
            "Manual external sharing/publication/go-no-go decision outside automation.",
        ],
        "review_boundary": [
            "This packet is a local-only/report-only one-page human runbook index; it does not execute the manual command sequence.",
            "It does not create/fill final feedback, approve release, record go/no-go, publish, upload, commit, push, tag, create remotes/repos/releases, validate credentials, call APIs/providers, mutate issues/backlogs, or execute hooks/actions/commands.",
            "Human feedback can remain pending while the runbook is ready; pending items are human-owned, not automated tasks.",
        ],
        "recommendations": [
            "If blocked, regenerate the missing latest-* evidence reports and rerun --manual-reviewer-execution-packet --both.",
            "If ready-for-human-runbook, give this packet to the human reviewer/operator; do not treat it as release approval.",
            "Perform any copy/edit, issue/backlog, publication, credential, or API work manually outside this gate and outside report automation.",
        ],
    }


def build_manual_release_reviewer_checklist_report(root: Path = ASSETS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    required_evidence = [
        "release-closure",
        "github-final-preflight",
        "public-safety-scan",
        "release-readiness",
    ]
    reports: Dict[str, Dict[str, Any]] = {
        prefix: _load_latest_report_json_for_root(root, prefix) or {} for prefix in required_evidence
    }

    def source_summary(prefix: str) -> Dict[str, Any]:
        value = reports.get(prefix, {}).get("summary", {})
        return value if isinstance(value, dict) else {}

    checks: List[Dict[str, str]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({
            "name": name,
            "status": "pass" if ok else "fail",
            "detail": _redact_public_text(detail),
        })

    def evidence_present(prefix: str) -> bool:
        return bool(reports.get(prefix))

    release_closure = reports.get("release-closure", {})
    final_preflight = reports.get("github-final-preflight", {})
    closure_summary = source_summary("release-closure")
    preflight_summary = source_summary("github-final-preflight")
    safety_summary = source_summary("public-safety-scan")
    readiness_summary = source_summary("release-readiness")

    for prefix in required_evidence:
        add_check(f"evidence:{prefix}:present", evidence_present(prefix), "present" if evidence_present(prefix) else "missing latest report")
    add_check("release-closure-ready-for-manual-review", closure_summary.get("status") == "ready-for-manual-release-review", str(closure_summary.get("status") or "missing"))
    add_check("github-final-preflight-ready", preflight_summary.get("status") == "ready", str(preflight_summary.get("status") or "missing"))
    add_check("public-safety-pass", safety_summary.get("status") == "pass", str(safety_summary.get("status") or "missing"))
    add_check("release-readiness-ready", readiness_summary.get("readiness") == "ready" or readiness_summary.get("status") == "ready", str(readiness_summary.get("readiness") or readiness_summary.get("status") or "missing"))

    closure_commands = release_closure.get("command_drafts", [])
    if not isinstance(closure_commands, list):
        closure_commands = []
    preflight_commands = final_preflight.get("command_drafts", [])
    if not isinstance(preflight_commands, list):
        preflight_commands = []
    command_drafts = [item for item in closure_commands + preflight_commands if isinstance(item, dict)]
    command_drafts = [_redact_public_value(item) for item in command_drafts]
    commands_non_executing = all(command.get("executes") is False for command in command_drafts)
    closure_publication_summary = release_closure.get("publication_command_summary", {})
    if not isinstance(closure_publication_summary, dict):
        closure_publication_summary = {}
    publication_command_summary = {
        "total": int(closure_publication_summary.get("total") or len(closure_commands)),
        "non_executing": int(closure_publication_summary.get("non_executing") or sum(1 for command in closure_commands if isinstance(command, dict) and command.get("executes") is False)),
        "manual_review_required": int(closure_publication_summary.get("manual_review_required") or sum(1 for command in closure_commands if isinstance(command, dict) and command.get("manual_review_required") is True)),
        "by_publication_risk": closure_publication_summary.get("by_publication_risk", {}) if isinstance(closure_publication_summary.get("by_publication_risk", {}), dict) else {},
    }
    add_check("command-drafts-non-executing", commands_non_executing, f"command_drafts={len(command_drafts)}")
    add_check("publication-command-summary-present", publication_command_summary["total"] > 0, str(publication_command_summary))

    artifact_checksum = final_preflight.get("artifact_checksum", {})
    if not isinstance(artifact_checksum, dict):
        artifact_checksum = {}
    artifact_sha256 = final_preflight.get("artifact_sha256", {})
    if not isinstance(artifact_sha256, dict):
        artifact_sha256 = {}
    if not artifact_checksum and artifact_sha256:
        artifact_checksum = {
            "recorded_sha256": artifact_sha256.get("recorded") or artifact_sha256.get("recorded_sha256"),
            "computed_sha256": artifact_sha256.get("computed") or artifact_sha256.get("computed_sha256"),
        }
    artifact_checksum_matches = artifact_checksum.get("matches") is True or bool(artifact_checksum.get("recorded_sha256") and artifact_checksum.get("recorded_sha256") == artifact_checksum.get("computed_sha256"))
    if artifact_checksum and "matches" not in artifact_checksum:
        artifact_checksum["matches"] = artifact_checksum_matches
    add_check("artifact-checksum-matches", artifact_checksum_matches, str(artifact_checksum or "missing"))

    executes_anything = any(source_summary(prefix).get("executes_anything") is True for prefix in required_evidence)
    remote_configured = any(source_summary(prefix).get("remote_configured") is True for prefix in ["release-closure", "github-final-preflight"])
    forbidden_findings = 0
    for prefix in ["release-closure", "github-final-preflight", "public-safety-scan"]:
        value = source_summary(prefix).get("forbidden_findings")
        if isinstance(value, int):
            forbidden_findings += value
    add_check("report-only-sources", not executes_anything, f"executes_anything={executes_anything}")
    add_check("no-remote-mutation-enabled", not remote_configured, f"remote_configured={remote_configured}")
    add_check("public-forbidden-findings-clean", forbidden_findings == 0, f"forbidden_findings={forbidden_findings}")

    checklist = [
        {
            "id": "release-closure-review",
            "title": "Confirm release closure is ready for manual release review.",
            "evidence": "latest-release-closure",
            "status": "ready" if closure_summary.get("status") == "ready-for-manual-release-review" else "blocked",
        },
        {
            "id": "github-final-preflight-review",
            "title": "Confirm GitHub final preflight is ready and non-executing.",
            "evidence": "latest-github-final-preflight",
            "status": "ready" if preflight_summary.get("status") == "ready" else "blocked",
        },
        {
            "id": "public-safety-review",
            "title": "Review public safety scan results and confirm no blockers or forbidden findings.",
            "evidence": "latest-public-safety-scan",
            "status": "ready" if safety_summary.get("status") == "pass" else "blocked",
        },
        {
            "id": "release-readiness-review",
            "title": "Review release readiness and confirm v0.1 readiness remains ready.",
            "evidence": "latest-release-readiness",
            "status": "ready" if readiness_summary.get("readiness") == "ready" or readiness_summary.get("status") == "ready" else "blocked",
        },
        {
            "id": "publication-boundary-review",
            "title": "Confirm publication boundary: report-only, no publish, no push, no remote creation, no credential validation.",
            "evidence": "release closure publication_boundary/manual_review_boundary",
            "status": "ready" if release_closure.get("publication_boundary") else "blocked",
        },
        {
            "id": "command-drafts-review",
            "title": "Manually inspect command drafts; they are reference-only and are not executed by this gate.",
            "evidence": "release closure and final preflight command_drafts",
            "status": "ready" if command_drafts and commands_non_executing else "blocked",
        },
        {
            "id": "artifact-checksum-review",
            "title": "Confirm final artifact checksum evidence matches before any manual publication.",
            "evidence": "github final preflight artifact_checksum",
            "status": "ready" if artifact_checksum_matches else "blocked",
        },
    ]
    for item in checklist:
        item["review_type"] = "manual"
        item["executes_anything"] = False
        item["auto_approves_release"] = False

    for item in checklist:
        add_check(f"checklist:{item['id']}", item.get("status") == "ready", str(item.get("status")))

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else "ready-for-human-review"
    review_boundary = [
        "This checklist is for human reviewer evidence only; it does not publish, push, create remotes, create tags, or execute command drafts.",
        "It does not validate credentials, authenticate to GitHub/providers, call APIs, or mutate provider/admin/runtime state.",
        "A human reviewer must inspect the release closure, final preflight, safety scan, readiness report, checksums, and command drafts before any manual release action.",
    ]
    return {
        "mode": "manual-release-reviewer-checklist",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "checks": len(checks),
            "pass": pass_count,
            "fail": fail_count,
            "checklist_items": len(checklist),
            "manual_review_required": True,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "remote_configured": remote_configured,
            "forbidden_findings": forbidden_findings,
            "command_drafts": len(command_drafts),
        },
        "required_evidence": required_evidence,
        "source_summaries": _redact_public_value({prefix: source_summary(prefix) for prefix in required_evidence}),
        "checks": checks,
        "checklist": _redact_public_value(checklist),
        "review_boundary": review_boundary,
        "publication_command_summary": _redact_public_value(publication_command_summary),
        "artifact_checksum": _redact_public_value(artifact_checksum),
        "command_drafts": command_drafts,
        "recommendations": [
            "If status is blocked, regenerate the failing latest-* evidence report(s) and rerun --manual-release-reviewer-checklist --both.",
            "If status is ready-for-human-review, hand the checklist to a human reviewer; do not treat it as automatic release approval.",
            "Keep publication, credential validation, remote creation, tag creation, and push actions outside this report-only gate.",
        ],
    }



def build_external_reference_inventory_report(root: Path = ASSETS) -> Dict[str, Any]:
    docs_dir = root / "docs"
    reference_docs = sorted(docs_dir.glob("reference-*.md")) if docs_dir.is_dir() else []
    strategy_doc = docs_dir / "external-reference-strategy.md"
    references: List[Dict[str, Any]] = []
    adopted_keywords = ["source/runtime separation", "bridge", "adapter", "skill", "taxonomy", "corpus", "review", "preview", "runtime cache", "canonical"]
    avoid_keywords = ["not copy", "avoid", "should not", "not become", "raw", "secret", "auto"]
    for path in reference_docs:
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        system_name = path.stem.removeprefix("reference-")
        references.append({
            "system": system_name,
            "path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "title": next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), system_name),
            "bytes": path.stat().st_size,
            "mentions_memory": "memory" in lower,
            "mentions_bridge": "bridge" in lower,
            "mentions_runtime_boundary": "runtime" in lower and ("canonical" in lower or "source" in lower),
            "adopted_keyword_hits": sorted({keyword for keyword in adopted_keywords if keyword in lower}),
            "avoid_keyword_hits": sorted({keyword for keyword in avoid_keywords if keyword in lower}),
        })
    systems = sorted(item["system"] for item in references)
    checks = [
        {"name": "strategy-doc", "status": "pass" if strategy_doc.is_file() else "fail", "detail": str(strategy_doc.relative_to(root)) if strategy_doc.exists() else "missing docs/external-reference-strategy.md"},
        {"name": "memos-reference", "status": "pass" if any("memos" in item["system"] for item in references) else "warn", "detail": "present" if any("memos" in item["system"] for item in references) else "missing"},
        {"name": "mempalace-reference", "status": "pass" if any("mempalace" in item["system"] for item in references) else "warn", "detail": "present" if any("mempalace" in item["system"] for item in references) else "missing"},
        {"name": "letta-memgpt-reference", "status": "pass" if any("letta" in item["system"] or "memgpt" in item["system"] for item in references) else "warn", "detail": "present" if any("letta" in item["system"] or "memgpt" in item["system"] for item in references) else "missing"},
        {"name": "openmemory-reference", "status": "pass" if any("openmemory" in item["system"] for item in references) else "warn", "detail": "present" if any("openmemory" in item["system"] for item in references) else "missing"},
        {"name": "mcp-memory-servers-reference", "status": "pass" if any("mcp-memory" in item["system"] or ("mcp" in item["system"] and "memory" in item["system"]) for item in references) else "warn", "detail": "present" if any("mcp-memory" in item["system"] or ("mcp" in item["system"] and "memory" in item["system"]) for item in references) else "missing"},
        {"name": "supermemory-reference", "status": "pass" if any("supermemory" in item["system"] for item in references) else "warn", "detail": "present" if any("supermemory" in item["system"] for item in references) else "missing"},
        {"name": "langgraph-memory-reference", "status": "pass" if any("langgraph" in item["system"] or "langchain" in item["system"] for item in references) else "warn", "detail": "present" if any("langgraph" in item["system"] or "langchain" in item["system"] for item in references) else "missing"},
        {"name": "open-webui-memory-reference", "status": "pass" if any("open-webui" in item["system"] or "webui" in item["system"] for item in references) else "warn", "detail": "present" if any("open-webui" in item["system"] or "webui" in item["system"] for item in references) else "missing"},
        {"name": "workflow-builders-reference", "status": "pass" if any("workflow-builder" in item["system"] or "workflow-builders" in item["system"] for item in references) else "warn", "detail": "present" if any("workflow-builder" in item["system"] or "workflow-builders" in item["system"] for item in references) else "missing"},
        {"name": "ide-project-memory-reference", "status": "pass" if any("ide-project" in item["system"] or "project-memory" in item["system"] for item in references) else "warn", "detail": "present" if any("ide-project" in item["system"] or "project-memory" in item["system"] for item in references) else "missing"},
        {"name": "assistant-projects-reference", "status": "pass" if any("assistant-project" in item["system"] or "assistant-projects" in item["system"] for item in references) else "warn", "detail": "present" if any("assistant-project" in item["system"] or "assistant-projects" in item["system"] for item in references) else "missing"},
        {"name": "hosted-agent-workspace-governance-reference", "status": "pass" if any("hosted-agent-workspace-governance" in item["system"] or "workspace-governance" in item["system"] for item in references) else "warn", "detail": "present" if any("hosted-agent-workspace-governance" in item["system"] or "workspace-governance" in item["system"] for item in references) else "missing"},
        {"name": "capability-risk-policy-gates-reference", "status": "pass" if any("capability-risk-policy" in item["system"] or "capability-risk" in item["system"] for item in references) else "warn", "detail": "present" if any("capability-risk-policy" in item["system"] or "capability-risk" in item["system"] for item in references) else "missing"},
        {"name": "project-pack-preview-reference", "status": "pass" if any("project-pack" in item["system"] for item in references) else "warn", "detail": "present" if any("project-pack" in item["system"] for item in references) else "missing"},
        {"name": "capability-policy-preview-reference", "status": "pass" if any("capability-policy-preview" in item["system"] for item in references) else "warn", "detail": "present" if any("capability-policy-preview" in item["system"] for item in references) else "missing"},
        {"name": "capability-policy-baseline-apply-reference", "status": "pass" if any("capability-policy-baseline-apply" in item["system"] for item in references) else "warn", "detail": "present" if any("capability-policy-baseline-apply" in item["system"] for item in references) else "missing"},
        {"name": "capability-policy-candidate-status-reference", "status": "pass" if any("capability-policy-candidate-status" in item["system"] for item in references) else "warn", "detail": "present" if any("capability-policy-candidate-status" in item["system"] for item in references) else "missing"},
        {"name": "completed-work-review-reference", "status": "pass" if any("completed-work-review" in item["system"] for item in references) else "warn", "detail": "present" if any("completed-work-review" in item["system"] for item in references) else "missing"},
        {"name": "at-least-thirteen-references", "status": "pass" if len(references) >= 13 else "warn", "detail": str(len(references))},
        {"name": "runtime-boundaries-covered", "status": "pass" if any(item["mentions_runtime_boundary"] for item in references) else "warn", "detail": str(sum(1 for item in references if item["mentions_runtime_boundary"]))},
    ]
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else ("needs-review" if warn_count else "ready")
    return {
        "mode": "external-reference-inventory",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "reference_docs": len(references),
            "systems": systems,
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
        },
        "strategy_doc": str(strategy_doc),
        "references": references,
        "checks": checks,
        "recommendations": [
            "Use this inventory to keep Portable AI Assets learning from external memory systems instead of evolving in isolation.",
            "For every new backend or plugin, add a docs/reference-<system>.md note with adopt / avoid / integration-boundary sections.",
            "Keep runtime backends as sources for reviewed canonical assets, not as the public Git source of truth.",
        ],
    }



def _parse_external_reference_backlog(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    rows: List[Dict[str, str]] = []
    headers: List[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "|" not in stripped[1:]:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not headers:
            headers = [cell.lower().replace(" ", "_") for cell in cells]
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if len(cells) != len(headers):
            continue
        rows.append({headers[index]: cells[index] for index in range(len(headers))})
    return rows


def build_external_reference_intake_radar(rows: List[Dict[str, str]], high_priority_candidates: List[Dict[str, str]]) -> Dict[str, Any]:
    reviewed_ids = {row.get("id", "") for row in rows if row.get("state") in {"reviewed", "adopted"}}
    queued_ids = {row.get("id", "") for row in rows if row.get("state") in {"candidate", "queued"}}
    lane_catalog = [
        {
            "id": "coding-agent-workspace-portability",
            "lane": "coding-agent workspace portability",
            "candidate_systems": ["Continue.dev", "Cline", "Roo Code", "Aider", "OpenHands"],
            "why_review": "Compare project memory, instruction files, workspace context, and coding-agent handoff patterns.",
            "expected_output": "docs/reference-coding-agent-workspace-portability.md",
            "adoption_boundary": "Adopt portable project-memory conventions; avoid importing private workspaces or live tool credentials.",
        },
        {
            "id": "agent-workflow-skill-registries",
            "lane": "agent workflow and skill registries",
            "candidate_systems": ["CrewAI", "AutoGen", "Semantic Kernel", "Anthropic Agent Skills", "LangGraph"],
            "why_review": "Study agent/task/skill lifecycle patterns that can inform public-safe procedure packaging.",
            "expected_output": "docs/reference-agent-workflow-skill-registries.md",
            "adoption_boundary": "Adopt schema and registry lessons only; do not execute agents, providers, tools, or workflows.",
        },
        {
            "id": "reproducible-environment-portability",
            "lane": "reproducible environment portability",
            "candidate_systems": ["Nix flakes", "Dev Containers", "Home Manager", "chezmoi", "yadm"],
            "why_review": "Learn how mature projects separate portable declarative state from local machine state.",
            "expected_output": "docs/reference-reproducible-environment-portability.md",
            "adoption_boundary": "Adopt reproducibility and dotfile boundary lessons; keep raw local runtime data outside git.",
        },
        {
            "id": "supply-chain-provenance",
            "lane": "supply-chain provenance and release evidence",
            "candidate_systems": ["Sigstore", "SLSA", "in-toto", "CycloneDX", "SPDX"],
            "why_review": "Strengthen release provenance, attestations, SBOM thinking, and audit receipts for public release.",
            "expected_output": "docs/reference-supply-chain-provenance.md",
            "adoption_boundary": "Adopt evidence and metadata patterns; do not sign, publish, or call external services in this report.",
        },
        {
            "id": "declarative-desired-state",
            "lane": "declarative desired-state reconciliation",
            "candidate_systems": ["Kubernetes CRD", "GitOps", "Argo CD", "Flux"],
            "why_review": "Study desired-state, diff, reconciliation, and reviewed apply patterns for asset sync governance.",
            "expected_output": "docs/reference-declarative-desired-state.md",
            "adoption_boundary": "Adopt conceptual review-gate lessons; do not connect to clusters or controllers.",
        },
    ]
    lanes = [lane for lane in lane_catalog if lane.get("id", "") not in reviewed_ids]
    return {
        "status": "actionable" if lanes else "empty",
        "source": "local backlog and reviewed reference coverage only",
        "executes_anything": False,
        "calls_external_services": False,
        "writes_runtime_state": False,
        "writes_files": False,
        "network_access": False,
        "reviewed_reference_count": len(reviewed_ids),
        "queued_or_candidate_count": len(queued_ids),
        "high_priority_candidate_count": len(high_priority_candidates),
        "adoption_workflow": ["candidate", "queued", "reviewed", "adopted", "rejected"],
        "public_safe_boundary": "Record public conceptual notes, review questions, expected docs, and adoption boundaries only; never store private runtime data, credentials, tokens, or connection strings.",
        "non_execution_boundary": "Report-only radar: no network search, no clone, no downloads, no provider/API calls, no authentication, no runtime execution, no admin/provider/credential writes.",
        "recommended_lanes": lanes,
        "next_step": "Promote one lane to candidate or queued in docs/external-reference-backlog.md, then write the matching docs/reference-*.md review before adopting lessons.",
    }


def build_external_reference_backlog_report(root: Path = ASSETS) -> Dict[str, Any]:
    backlog_path = root / "docs" / "external-reference-backlog.md"
    strategy_path = root / "docs" / "external-reference-strategy.md"
    rows = _parse_external_reference_backlog(backlog_path)
    state_counts: Dict[str, int] = {}
    priority_counts: Dict[str, int] = {}
    categories: Dict[str, int] = {}
    reviewed_with_docs = 0
    missing_expected_docs: List[Dict[str, str]] = []
    high_priority_candidates: List[Dict[str, str]] = []
    for row in rows:
        state = row.get("state", "unknown")
        priority = row.get("priority", "unknown")
        state_counts[state] = state_counts.get(state, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        category = row.get("category", "unknown")
        categories[category] = categories.get(category, 0) + 1
        expected = row.get("expected_output", "")
        expected_clean = expected.strip("`")
        expected_path = root / expected_clean if expected_clean.startswith("docs/") else None
        if state in {"reviewed", "adopted"}:
            if expected_path and expected_path.is_file():
                reviewed_with_docs += 1
            else:
                missing_expected_docs.append({"id": row.get("id", "unknown"), "expected_output": expected})
        if priority == "high" and state in {"candidate", "queued"}:
            high_priority_candidates.append(row)
    reference_intake_radar = build_external_reference_intake_radar(rows, high_priority_candidates)
    has_open_high_priority_queue = len(high_priority_candidates) >= 1 or reference_intake_radar.get("status") == "empty"
    checks = [
        {"name": "backlog-doc", "status": "pass" if backlog_path.is_file() else "fail", "detail": str(backlog_path.relative_to(root)) if backlog_path.exists() else "missing docs/external-reference-backlog.md"},
        {"name": "strategy-doc", "status": "pass" if strategy_path.is_file() else "warn", "detail": str(strategy_path.relative_to(root)) if strategy_path.exists() else "missing docs/external-reference-strategy.md"},
        {"name": "has-candidates", "status": "pass" if len(rows) >= 5 else "warn", "detail": str(len(rows))},
        {"name": "has-reviewed-baseline", "status": "pass" if state_counts.get("reviewed", 0) >= 2 else "warn", "detail": str(state_counts.get("reviewed", 0))},
        {"name": "reviewed-docs-exist", "status": "pass" if not missing_expected_docs else "fail", "detail": str(len(missing_expected_docs))},
        {"name": "has-high-priority-queue", "status": "pass" if has_open_high_priority_queue else "warn", "detail": str(len(high_priority_candidates))},
    ]
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else ("needs-review" if warn_count else "ready")
    reference_intake_radar = build_external_reference_intake_radar(rows, high_priority_candidates)
    return {
        "mode": "external-reference-backlog",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "backlog_path": str(backlog_path),
        "summary": {
            "status": status,
            "items": len(rows),
            "state_counts": dict(sorted(state_counts.items())),
            "priority_counts": dict(sorted(priority_counts.items())),
            "high_priority_candidates": len(high_priority_candidates),
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
        },
        "items": rows,
        "categories": dict(sorted(categories.items())),
        "high_priority_candidates": high_priority_candidates,
        "missing_expected_docs": missing_expected_docs,
        "checks": checks,
        "reference_intake_radar": reference_intake_radar,
        "recommendations": [
            "Promote one high-priority candidate at a time from candidate to queued, then write a docs/reference-<system>.md review before implementing lessons.",
            "Prefer studying existing memory/backend systems before designing new asset classes or adapter behavior.",
            "Keep this backlog public-safe: record ideas and boundaries, not private runtime data or credentials.",
        ],
    }


def _team_pack_manifest_paths(root: Path) -> List[Path]:
    candidates = [root / "sample-assets" / "team-pack" / "team-pack.yaml"]
    candidates.extend(sorted((root / "team-packs").glob("*/team-pack.yaml")) if (root / "team-packs").is_dir() else [])
    return [path for path in candidates if path.is_file()]


def build_team_pack_preview_report(root: Path = ASSETS) -> Dict[str, Any]:
    docs = root / "docs"
    required_docs = [
        docs / "team-grade-packaging.md",
        root / "sample-assets" / "team-pack" / "README.md",
        root / "examples" / "redacted" / "team-pack.example.md",
    ]
    manifests: List[Dict[str, Any]] = []
    checks: List[Dict[str, str]] = []
    for doc in required_docs:
        checks.append({"name": f"required:{doc.relative_to(root)}", "status": "pass" if doc.is_file() else "fail", "detail": str(doc.relative_to(root))})
    for path in _team_pack_manifest_paths(root):
        payload = load_yaml_data(path)
        if not isinstance(payload, dict):
            payload = {}
        referenced: List[Dict[str, Any]] = []
        for key in ["policies", "playbooks", "adapters"]:
            for rel in payload.get(key, []) if isinstance(payload.get(key), list) else []:
                ref_path = path.parent / str(rel)
                referenced.append({"kind": key, "path": str(Path(str(path.parent.relative_to(root))) / str(rel)) if path.is_relative_to(root) else str(ref_path), "exists": ref_path.is_file()})
        for role in payload.get("roles", []) if isinstance(payload.get("roles"), list) else []:
            role_path = path.parent / "roles" / f"{role}.md"
            referenced.append({"kind": "roles", "path": str(Path(str(path.parent.relative_to(root))) / "roles" / f"{role}.md") if path.is_relative_to(root) else str(role_path), "exists": role_path.is_file()})
        missing_refs = [item for item in referenced if not item["exists"]]
        shareability = str(payload.get("shareability", "unknown"))
        asset_class = str(payload.get("asset_class", "unknown"))
        manifests.append({
            "name": payload.get("name", path.stem),
            "path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "pack_version": payload.get("pack_version"),
            "asset_class": asset_class,
            "shareability": shareability,
            "apply_policy": payload.get("apply_policy", "unknown"),
            "layers": payload.get("layers", []) if isinstance(payload.get("layers"), list) else [],
            "roles": payload.get("roles", []) if isinstance(payload.get("roles"), list) else [],
            "referenced": referenced,
            "missing_references": len(missing_refs),
            "public_safe": shareability == "public-safe" and asset_class == "public",
        })
    checks.append({"name": "has-team-pack-manifest", "status": "pass" if manifests else "warn", "detail": str(len(manifests))})
    checks.append({"name": "all-references-exist", "status": "pass" if all(item["missing_references"] == 0 for item in manifests) else "warn", "detail": str(sum(item["missing_references"] for item in manifests))})
    checks.append({"name": "public-safe-sample", "status": "pass" if any(item["public_safe"] for item in manifests) else "warn", "detail": str(sum(1 for item in manifests if item["public_safe"]))})
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    return {
        "mode": "team-pack-preview",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": "blocked" if fail_count else ("needs-review" if warn_count else "ready"),
            "manifests": len(manifests),
            "public_safe_manifests": sum(1 for item in manifests if item["public_safe"]),
            "roles": sum(len(item["roles"]) for item in manifests),
            "layers": sum(len(item["layers"]) for item in manifests),
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warn_count,
            "fail": fail_count,
        },
        "manifests": manifests,
        "checks": checks,
        "recommendations": [
            "Treat team packs as canonical layer inputs, not live runtime overwrites.",
            "Use preview/candidate/review/apply stages before projecting shared team guidance into adapters.",
            "Keep individual private memory and secrets outside shared team packs.",
        ],
    }


def _capability_risk_for_connector(label: str, direction: str) -> List[str]:
    normalized = str(label or "").strip().lower()
    risks: List[str] = []
    if normalized in {"", "none", "manual-only"}:
        return ["text-only"] if normalized == "manual-only" else []
    if normalized in {"read-file", "copy-file", "sqlite-summary", "json-summary", "list", "search", "context", "status"}:
        risks.append("read-only-data")
    if normalized in {"write-file", "copy-to-live", "append-file", "apply", "sync"} or direction == "export":
        if normalized not in {"manual-only", "read-file"}:
            risks.append("write-files")
    if any(token in normalized for token in ["http", "webhook", "api", "remote", "network"]):
        risks.append("external-network")
    if any(token in normalized for token in ["shell", "exec", "code", "hook", "agent", "script"]):
        risks.append("code-execution")
    if any(token in normalized for token in ["credential", "oauth", "token", "secret", "auth"]):
        risks.append("credential-binding")
    return sorted(set(risks or ["text-only"]))


def _policy_outcome_for_risks(risks: List[str], apply_policy: str = "") -> str:
    risk_set = set(risks)
    policy = str(apply_policy or "").lower()
    if "admin-control" in risk_set or policy == "manual-only":
        return "manual-only"
    if "credential-binding" in risk_set:
        return "blocked-public"
    if risk_set & {"write-memory", "write-files", "external-network", "code-execution"}:
        return "review-required"
    if "read-only-data" in risk_set:
        return "allow-preview"
    return "allow-preview"


def _add_count(counts: Dict[str, int], values: List[str]) -> None:
    for value in values:
        counts[value] = counts.get(value, 0) + 1


def _project_pack_manifest_paths(root: Path) -> List[Path]:
    candidates = [root / "sample-assets" / "project-pack" / "project-pack.yaml"]
    candidates.extend(sorted((root / "project-packs").glob("*/project-pack.yaml")) if (root / "project-packs").is_dir() else [])
    return [path for path in candidates if path.is_file()]


def _capability_entries_from_payload(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    for item in payload.get("capabilities", []) if isinstance(payload.get("capabilities"), list) else []:
        if isinstance(item, dict):
            name = str(item.get("name") or "unnamed-capability")
            risk = str(item.get("risk_class") or item.get("risk_classes") or "text-only")
            outcome = str(item.get("policy_outcome") or _policy_outcome_for_risks([risk], payload.get("apply_policy", "")))
        else:
            name = str(item)
            risk = "text-only"
            outcome = "allow-preview"
        entries.append({"name": name, "risk_class": risk, "policy_outcome": outcome})
    return entries


def build_project_pack_preview_report(root: Path = ASSETS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    docs = root / "docs"
    required_docs = [
        docs / "project-pack-preview.md",
        root / "sample-assets" / "project-pack" / "README.md",
        root / "examples" / "redacted" / "project-pack.example.md",
    ]
    manifests: List[Dict[str, Any]] = []
    checks: List[Dict[str, str]] = []
    risk_counts: Dict[str, int] = {}
    outcome_counts: Dict[str, int] = {}
    for doc in required_docs:
        checks.append({"name": f"required:{doc.relative_to(root)}", "status": "pass" if doc.is_file() else "fail", "detail": str(doc.relative_to(root))})
    for path in _project_pack_manifest_paths(root):
        payload = load_yaml_data(path)
        if not isinstance(payload, dict):
            payload = {}
        referenced: List[Dict[str, Any]] = []
        reference_keys = ["instructions", "knowledge_sources", "actions", "adapters"]
        for key in reference_keys:
            for rel in payload.get(key, []) if isinstance(payload.get(key), list) else []:
                ref_path = path.parent / str(rel)
                referenced.append({"kind": key, "path": str(Path(str(path.parent.relative_to(root))) / str(rel)) if path.is_relative_to(root) else str(ref_path), "exists": ref_path.is_file()})
        missing_refs = [item for item in referenced if not item["exists"]]
        capability_entries = _capability_entries_from_payload(payload)
        for entry in capability_entries:
            risk = entry["risk_class"]
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
            outcome_counts[entry["policy_outcome"]] = outcome_counts.get(entry["policy_outcome"], 0) + 1
        shareability = str(payload.get("shareability", "unknown"))
        asset_class = str(payload.get("asset_class", "unknown"))
        manifests.append({
            "name": payload.get("name", path.stem),
            "path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "pack_version": payload.get("pack_version"),
            "asset_class": asset_class,
            "shareability": shareability,
            "project_scope": payload.get("project_scope", "unknown"),
            "visibility": payload.get("visibility", "unknown"),
            "apply_policy": payload.get("apply_policy", "unknown"),
            "referenced": referenced,
            "missing_references": len(missing_refs),
            "capabilities": capability_entries,
            "public_safe": shareability == "public-safe" and asset_class == "public",
            "executes_anything": False,
        })
    checks.append({"name": "has-project-pack-manifest", "status": "pass" if manifests else "warn", "detail": str(len(manifests))})
    checks.append({"name": "all-references-exist", "status": "pass" if all(item["missing_references"] == 0 for item in manifests) else "warn", "detail": str(sum(item["missing_references"] for item in manifests))})
    checks.append({"name": "public-safe-sample", "status": "pass" if any(item["public_safe"] for item in manifests) else "warn", "detail": str(sum(1 for item in manifests if item["public_safe"]))})
    checks.append({"name": "no-execution", "status": "pass", "detail": "preview-only; no actions, connectors, credentials, or runtime files are executed or mutated"})
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    return {
        "mode": "project-pack-preview",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": "blocked" if fail_count else ("needs-review" if warn_count else "ready"),
            "manifests": len(manifests),
            "public_safe_manifests": sum(1 for item in manifests if item["public_safe"]),
            "capabilities": sum(len(item["capabilities"]) for item in manifests),
            "risk_class_counts": dict(sorted(risk_counts.items())),
            "policy_outcome_counts": dict(sorted(outcome_counts.items())),
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
        },
        "manifests": manifests,
        "checks": checks,
        "recommendations": [
            "Treat project packs as canonical project-scoped assets, not hosted assistant/runtime mirrors.",
            "Keep knowledge sources, action metadata, and adapter projections reviewable before any write/apply behavior.",
            "Compare capability deltas before projecting project packs into team or shared runtime surfaces.",
        ],
    }


def build_capability_risk_inventory_report(root: Path = ASSETS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    capabilities: List[Dict[str, Any]] = []
    risk_counts: Dict[str, int] = {}
    outcome_counts: Dict[str, int] = {}

    for path in sorted((root / "adapters" / "registry").glob("*.yaml")) if (root / "adapters" / "registry").is_dir() else []:
        payload = load_yaml_data(path)
        if not isinstance(payload, dict):
            continue
        name = str(payload.get("name") or path.stem)
        apply_policy = str(payload.get("apply_policy") or "unknown")
        connector = payload.get("connector") if isinstance(payload.get("connector"), dict) else {}
        for direction in ["import", "export"]:
            label = connector.get(direction)
            if not label:
                continue
            risks = _capability_risk_for_connector(str(label), direction)
            outcome = _policy_outcome_for_risks(risks, apply_policy)
            _add_count(risk_counts, risks)
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
            capabilities.append({
                "kind": "adapter-connector",
                "name": f"{name}:{direction}:{label}",
                "source": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
                "runtime": payload.get("runtime", "unknown"),
                "direction": direction,
                "connector": label,
                "risk_classes": risks,
                "policy_outcome": outcome,
                "apply_policy": apply_policy,
                "executes_anything": False,
            })

    for manifest in _team_pack_manifest_paths(root):
        payload = load_yaml_data(manifest)
        if not isinstance(payload, dict):
            payload = {}
        name = str(payload.get("name") or manifest.stem)
        apply_policy = str(payload.get("apply_policy") or "human-review-required")
        risks = ["text-only"]
        outcome = "review-required" if "review" in apply_policy or "human" in apply_policy else _policy_outcome_for_risks(risks, apply_policy)
        _add_count(risk_counts, risks)
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        capabilities.append({
            "kind": "team-pack",
            "name": name,
            "source": str(manifest.relative_to(root)) if manifest.is_relative_to(root) else str(manifest),
            "risk_classes": risks,
            "policy_outcome": outcome,
            "apply_policy": apply_policy,
            "layers": payload.get("layers", []) if isinstance(payload.get("layers"), list) else [],
            "roles": payload.get("roles", []) if isinstance(payload.get("roles"), list) else [],
            "executes_anything": False,
        })

    for manifest in _project_pack_manifest_paths(root):
        payload = load_yaml_data(manifest)
        if not isinstance(payload, dict):
            payload = {}
        apply_policy = str(payload.get("apply_policy") or "human-review-required")
        for entry in _capability_entries_from_payload(payload) or [{"name": str(payload.get("name") or manifest.stem), "risk_class": "text-only", "policy_outcome": "review-required"}]:
            risks = [str(entry.get("risk_class") or "text-only")]
            outcome = str(entry.get("policy_outcome") or _policy_outcome_for_risks(risks, apply_policy))
            _add_count(risk_counts, risks)
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
            capabilities.append({
                "kind": "project-pack",
                "name": f"{payload.get('name', manifest.stem)}:{entry.get('name')}",
                "source": str(manifest.relative_to(root)) if manifest.is_relative_to(root) else str(manifest),
                "risk_classes": risks,
                "policy_outcome": outcome,
                "apply_policy": apply_policy,
                "project_scope": payload.get("project_scope", "unknown"),
                "visibility": payload.get("visibility", "unknown"),
                "executes_anything": False,
            })

    checks = [
        {"name": "inventory-report-only", "status": "pass", "detail": "does not start servers, execute hooks, call APIs, authenticate, or mutate runtime state"},
        {"name": "has-capabilities", "status": "pass" if capabilities else "warn", "detail": str(len(capabilities))},
        {"name": "no-execution", "status": "pass" if all(not item.get("executes_anything") for item in capabilities) else "fail", "detail": "executes_anything=false"},
        {"name": "review-gates-present", "status": "pass" if any(item.get("policy_outcome") in {"review-required", "manual-only", "blocked-public"} for item in capabilities) else "warn", "detail": str(outcome_counts)},
    ]
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    return {
        "mode": "capability-risk-inventory",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": "blocked" if fail_count else ("needs-review" if warn_count else "ready"),
            "capabilities": len(capabilities),
            "risk_class_counts": dict(sorted(risk_counts.items())),
            "policy_outcome_counts": dict(sorted(outcome_counts.items())),
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
        },
        "capabilities": capabilities,
        "checks": checks,
        "recommendations": [
            "Keep capability gates report-only before any shared/team/project-pack apply behavior.",
            "Route write, network, code-execution, credential, and admin-control capabilities through candidate/review/apply or manual-only gates.",
            "Inventory credential reference names only; never copy credential values, webhook URLs, tokens, or execution traces into public assets.",
        ],
    }


CAPABILITY_RISK_RANK = {
    "text-only": 0,
    "read-only-data": 1,
    "write-memory": 2,
    "write-files": 3,
    "external-network": 4,
    "code-execution": 5,
    "credential-binding": 6,
    "admin-control": 7,
}


def _capability_policy_baseline_paths(root: Path) -> List[Path]:
    candidates = [
        root / "sample-assets" / "capability-policy" / "baseline.yaml",
        root / "capability-policy" / "baseline.yaml",
    ]
    return [path for path in candidates if path.is_file()]


def _capability_record_map(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    mapped: Dict[str, Dict[str, Any]] = {}
    for item in records:
        name = str(item.get("name") or "")
        if not name:
            continue
        risks = item.get("risk_classes") if isinstance(item.get("risk_classes"), list) else [item.get("risk_class", "text-only")]
        risk = str(risks[0] if risks else "text-only")
        mapped[name] = {
            "name": name,
            "risk_class": risk,
            "risk_rank": CAPABILITY_RISK_RANK.get(risk, 0),
            "policy_outcome": str(item.get("policy_outcome") or "allow-preview"),
            "source": item.get("source", ""),
            "kind": item.get("kind", "capability"),
        }
    return mapped


def _load_capability_policy_baseline(root: Path) -> Dict[str, Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for path in _capability_policy_baseline_paths(root):
        payload = load_yaml_data(path)
        if not isinstance(payload, dict):
            continue
        for item in payload.get("capabilities", []) if isinstance(payload.get("capabilities"), list) else []:
            if isinstance(item, dict):
                enriched = dict(item)
                enriched.setdefault("source", str(path.relative_to(root)) if path.is_relative_to(root) else str(path))
                records.append(enriched)
    return _capability_record_map(records)


def _current_policy_capability_records(root: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    project_report = build_project_pack_preview_report(root)
    for manifest in project_report.get("manifests", []):
        pack_name = str(manifest.get("name") or "project-pack")
        for item in manifest.get("capabilities", []):
            records.append({
                "name": f"{pack_name}:{item.get('name')}",
                "risk_class": item.get("risk_class", "text-only"),
                "policy_outcome": item.get("policy_outcome", "allow-preview"),
                "source": manifest.get("path", ""),
                "kind": "project-pack",
            })
    team_report = build_team_pack_preview_report(root)
    for manifest in team_report.get("manifests", []):
        pack_name = str(manifest.get("name") or "team-pack")
        records.append({
            "name": f"{pack_name}:team-pack",
            "risk_class": "text-only",
            "policy_outcome": "review-required",
            "source": manifest.get("path", ""),
            "kind": "team-pack",
        })
    return records


def build_capability_policy_preview_report(root: Path = ASSETS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    baseline = _load_capability_policy_baseline(root)
    current = _capability_record_map(_current_policy_capability_records(root))
    added = [current[name] for name in sorted(set(current) - set(baseline))]
    removed = [baseline[name] for name in sorted(set(baseline) - set(current))]
    changed: List[Dict[str, Any]] = []
    risk_upgrades: List[Dict[str, Any]] = []
    risk_downgrades: List[Dict[str, Any]] = []
    for name in sorted(set(current) & set(baseline)):
        before = baseline[name]
        after = current[name]
        if before["risk_class"] != after["risk_class"] or before["policy_outcome"] != after["policy_outcome"]:
            delta = {"name": name, "before": before, "after": after}
            changed.append(delta)
            if after["risk_rank"] > before["risk_rank"]:
                risk_upgrades.append(delta)
            elif after["risk_rank"] < before["risk_rank"]:
                risk_downgrades.append(delta)
    outcome_counts: Dict[str, int] = {}
    risk_counts: Dict[str, int] = {}
    for item in current.values():
        outcome_counts[item["policy_outcome"]] = outcome_counts.get(item["policy_outcome"], 0) + 1
        risk_counts[item["risk_class"]] = risk_counts.get(item["risk_class"], 0) + 1
    checks = [
        {"name": "preview-report-only", "status": "pass", "detail": "no actions, connectors, credentials, providers, or runtime files are executed or mutated"},
        {"name": "baseline-present", "status": "pass" if baseline else "warn", "detail": str(len(baseline))},
        {"name": "current-capabilities-present", "status": "pass" if current else "warn", "detail": str(len(current))},
        {"name": "risk-upgrades-reviewed", "status": "warn" if risk_upgrades else "pass", "detail": str(len(risk_upgrades))},
    ]
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    status = "blocked" if fail_count else ("needs-review" if warn_count or added or removed or changed else "ready")
    return {
        "mode": "capability-policy-preview",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "status": status,
            "baseline_capabilities": len(baseline),
            "current_capabilities": len(current),
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "risk_upgrades": len(risk_upgrades),
            "risk_downgrades": len(risk_downgrades),
            "risk_class_counts": dict(sorted(risk_counts.items())),
            "policy_outcome_counts": dict(sorted(outcome_counts.items())),
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
        },
        "baseline_paths": [str(path.relative_to(root)) if path.is_relative_to(root) else str(path) for path in _capability_policy_baseline_paths(root)],
        "deltas": {
            "added": added,
            "removed": removed,
            "changed": changed,
            "risk_upgrades": risk_upgrades,
            "risk_downgrades": risk_downgrades,
        },
        "checks": checks,
        "recommendations": [
            "Review added, removed, and risk-upgraded capabilities before any project/team/shared apply behavior.",
            "Treat this as policy preview only; do not execute actions, call providers, authenticate, or mutate runtime/admin state.",
            "Update the reviewed baseline only after human approval of the capability delta.",
        ],
    }


def _capability_policy_reviewed_baseline_path(root: Path) -> Path:
    return root / "bootstrap" / "candidates" / "capability-policy" / "reviewed-baseline.yaml"


def _capability_policy_template_path(root: Path) -> Path:
    return root / "bootstrap" / "candidates" / "capability-policy" / "reviewed-baseline.yaml.template"


def _yaml_scalar(value: Any) -> str:
    text = str(value)
    if not text:
        return '""'
    if re.match(r"^[A-Za-z0-9_./:@+-]+$", text):
        return text
    return json.dumps(text, ensure_ascii=False)


def render_capability_policy_baseline_template(capabilities: List[Dict[str, Any]]) -> str:
    lines = [
        "# Copy this file to reviewed-baseline.yaml only after human review.",
        "# Generated from capability-policy-preview current declarations.",
        "# Keep entries declarative and public/private safe; never include credential values or endpoint secrets.",
        "# This template is not applied automatically.",
        "capabilities:",
    ]
    if not capabilities:
        lines.append("  []")
    else:
        for item in sorted(capabilities, key=lambda entry: str(entry.get("name") or "")):
            lines.extend([
                f"  - name: {_yaml_scalar(item.get('name', ''))}",
                f"    risk_class: {_yaml_scalar(item.get('risk_class', 'text-only'))}",
                f"    policy_outcome: {_yaml_scalar(item.get('policy_outcome', 'allow-preview'))}",
            ])
    return "\n".join(lines) + "\n"


def build_capability_policy_candidate_generation_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Generate a reviewed-baseline template from current capability declarations.

    This is a narrow candidate-generation step. It writes only
    reviewed-baseline.yaml.template and never creates reviewed-baseline.yaml,
    applies baselines, executes capabilities, calls providers, authenticates, or
    mutates runtime/admin/credential state.
    """
    root = root.expanduser().resolve()
    preview = build_capability_policy_preview_report(root)
    current = list(_capability_record_map(_current_policy_capability_records(root)).values())
    template_path = _capability_policy_template_path(root)
    reviewed_path = _capability_policy_reviewed_baseline_path(root)
    template_text = render_capability_policy_baseline_template(current)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(template_text, encoding="utf-8")
    deltas = preview.get("deltas", {}) if isinstance(preview.get("deltas"), dict) else {}
    checks = [
        {"name": "template-written", "status": "pass" if template_path.is_file() else "fail", "detail": str(template_path.relative_to(root)) if template_path.exists() else "missing template"},
        {"name": "reviewed-baseline-not-written", "status": "pass" if not reviewed_path.exists() else "fail", "detail": "requires human copy/review before apply" if not reviewed_path.exists() else str(reviewed_path.relative_to(root))},
        {"name": "candidate-generation-non-execution", "status": "pass", "detail": "does not execute capabilities, start runtimes, call providers, authenticate, or mutate runtime/admin/credential state"},
    ]
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    return {
        "mode": "capability-policy-candidate-generation",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "template_path": str(template_path),
        "reviewed_path": str(reviewed_path),
        "summary": {
            "status": "blocked" if fail_count else "generated",
            "templates_written": 1 if template_path.is_file() else 0,
            "reviewed_baselines_written": 1 if reviewed_path.exists() else 0,
            "baseline_capabilities": preview.get("summary", {}).get("baseline_capabilities", 0),
            "current_capabilities": len(current),
            "added": len(deltas.get("added", [])),
            "removed": len(deltas.get("removed", [])),
            "changed": len(deltas.get("changed", [])),
            "risk_upgrades": len(deltas.get("risk_upgrades", [])),
            "risk_downgrades": len(deltas.get("risk_downgrades", [])),
            "risk_class_counts": preview.get("summary", {}).get("risk_class_counts", {}),
            "policy_outcome_counts": preview.get("summary", {}).get("policy_outcome_counts", {}),
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
        },
        "deltas": deltas,
        "checks": checks,
        "recommendations": [
            "Review the generated reviewed-baseline.yaml.template before copying it to reviewed-baseline.yaml.",
            "Run capability-policy-baseline-apply only after human review creates reviewed-baseline.yaml.",
            "Do not treat template generation as permission to execute capabilities or mutate provider/runtime/admin state.",
        ],
    }


def _capability_policy_reviewed_sync_delta(reviewed: Dict[str, Dict[str, Any]], current: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    added = [current[name] for name in sorted(set(current) - set(reviewed))]
    removed = [reviewed[name] for name in sorted(set(reviewed) - set(current))]
    changed: List[Dict[str, Any]] = []
    for name in sorted(set(current) & set(reviewed)):
        before = reviewed[name]
        after = current[name]
        if before["risk_class"] != after["risk_class"] or before["policy_outcome"] != after["policy_outcome"]:
            changed.append({"name": name, "before": before, "after": after})
    return {"added": added, "removed": removed, "changed": changed}


def build_capability_policy_reviewer_guidance(root: Path, apply_readiness: str, template_path: Path, reviewed_path: Path, ready_for_apply: bool) -> Dict[str, Any]:
    template_rel = str(template_path.relative_to(root)) if template_path.is_relative_to(root) else str(template_path)
    reviewed_rel = str(reviewed_path.relative_to(root)) if reviewed_path.is_relative_to(root) else str(reviewed_path)
    if ready_for_apply:
        next_action = "run-reviewed-apply-if-intended"
    elif apply_readiness == "missing-template":
        next_action = "regenerate-template"
    elif apply_readiness == "blocked-invalid-reviewed-baseline":
        next_action = "fix-reviewed-baseline"
    elif apply_readiness == "blocked-out-of-sync":
        next_action = "sync-reviewed-baseline-with-current-preview"
    else:
        next_action = "human-review-template"
    return {
        "status": apply_readiness,
        "next_action": next_action,
        "template_path": template_rel,
        "reviewed_path": reviewed_rel,
        "checklist": [
            "Compare added/removed/changed capability declarations against the latest capability policy preview.",
            "Review risk upgrades and policy outcome changes before accepting the candidate baseline.",
            "Confirm every capability remains declarative and contains no credential values, tokens, webhook URLs, or provider connection strings.",
            "Confirm reviewers do not execute capabilities, start runtimes, call providers, authenticate, or mutate runtime/admin/provider/credential state.",
            "Create reviewed-baseline.yaml only after human acceptance, then rerun candidate status before apply.",
        ],
        "commands": {
            "regenerate_template": {"executes": False, "command": "/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-candidate-generation --both"},
            "copy_template_to_reviewed": {"executes": False, "command": f"cp {template_rel} {reviewed_rel}"},
            "status_after_review": {"executes": False, "command": "/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-candidate-status --both"},
            "apply_when_ready": {"executes": False, "command": "/bin/bash ./bootstrap/setup/bootstrap-ai-assets.sh --capability-policy-baseline-apply --both"},
        },
        "safety_boundary": "Command drafts are non-executing guidance only; this report does not run them.",
    }


def _relative_path_or_absolute(path: Path, root: Path) -> str:
    return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)


def _review_handoff_file_evidence(path: Path, root: Path) -> Dict[str, Any]:
    return {
        "path": _relative_path_or_absolute(path, root),
        "exists": path.is_file(),
        "sha256": sha256_text(path) if path.is_file() else None,
    }


def build_capability_policy_review_handoff_audit(
    root: Path,
    status: str,
    apply_readiness: str,
    ready_for_apply: bool,
    template_path: Path,
    reviewed_path: Path,
    baseline_path: Path,
    review_instructions_path: Path,
) -> Dict[str, Any]:
    """Build read-only handoff evidence for human-reviewed baseline preflight.

    The audit intentionally hashes only local declarative files and never writes,
    applies, executes, calls providers, authenticates, or mutates runtime/admin/
    credential state.
    """
    template_evidence = _review_handoff_file_evidence(template_path, root)
    reviewed_evidence = _review_handoff_file_evidence(reviewed_path, root)
    baseline_evidence = _review_handoff_file_evidence(baseline_path, root)
    instructions_evidence = _review_handoff_file_evidence(review_instructions_path, root)
    checklist = [
        {"name": "candidate-template-present", "status": "pass" if template_evidence["exists"] else "warn", "detail": template_evidence["path"] if template_evidence["exists"] else "missing reviewed-baseline.yaml.template"},
        {"name": "human-reviewed-baseline-present", "status": "pass" if reviewed_evidence["exists"] else "warn", "detail": reviewed_evidence["path"] if reviewed_evidence["exists"] else "missing reviewed-baseline.yaml; needs human review"},
        {"name": "current-baseline-evidence", "status": "pass" if baseline_evidence["exists"] else "warn", "detail": baseline_evidence["path"] if baseline_evidence["exists"] else "missing current baseline evidence"},
        {"name": "review-instructions-present", "status": "pass" if instructions_evidence["exists"] else "warn", "detail": instructions_evidence["path"] if instructions_evidence["exists"] else "missing review instructions"},
        {"name": "candidate-status-report-only", "status": "pass", "detail": "writes=0; executes=false; does not auto-copy or auto-apply"},
    ]
    return {
        "status": status,
        "apply_readiness": apply_readiness,
        "executes_anything": False,
        "writes_anything": False,
        "writes": 0,
        "preflight": {
            "ready_for_apply": ready_for_apply,
            "checklist": checklist,
        },
        "evidence": {
            "template": template_evidence,
            "reviewed_baseline": reviewed_evidence,
            "current_baseline": baseline_evidence,
            "review_instructions": instructions_evidence,
            "template_sha256": template_evidence["sha256"],
            "reviewed_baseline_sha256": reviewed_evidence["sha256"],
            "current_baseline_sha256": baseline_evidence["sha256"],
            "review_instructions_sha256": instructions_evidence["sha256"],
        },
        "handoff_steps": [
            "Inspect the candidate status report and capability policy preview before editing reviewed-baseline.yaml.",
            "Copy reviewed-baseline.yaml.template to reviewed-baseline.yaml only after human review accepts the declarative policy delta.",
            "Rerun the candidate status report to confirm reviewed-baseline.yaml validates and is synchronized before any reviewed apply.",
            "Do not auto-copy, auto-apply, execute capabilities, call providers, authenticate, or mutate runtime/admin/provider/credential state from this audit.",
        ],
    }


def build_capability_policy_candidate_status_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report whether the human-reviewed capability policy candidate is ready to apply.

    This status gate is read-only: it never writes templates, creates reviewed
    baselines, applies baselines, executes capabilities, calls providers,
    authenticates, or mutates runtime/admin/credential state.
    """
    root = root.expanduser().resolve()
    preview = build_capability_policy_preview_report(root)
    current = _capability_record_map(_current_policy_capability_records(root))
    template_path = _capability_policy_template_path(root)
    reviewed_path = _capability_policy_reviewed_baseline_path(root)
    template_exists = template_path.is_file()
    reviewed_exists = reviewed_path.is_file()
    reviewed_valid = False
    reviewed_in_sync = False
    ready_for_apply = False
    validation_errors: List[str] = []
    sync_delta: Dict[str, List[Dict[str, Any]]] = {"added": [], "removed": [], "changed": []}
    apply_readiness = "needs-human-review"

    if reviewed_exists:
        reviewed_payload = load_yaml_data(reviewed_path)
        validation_errors = _validate_capability_baseline_payload(reviewed_payload)
        reviewed_valid = not validation_errors
        if reviewed_valid:
            reviewed_capabilities = _capability_record_map(reviewed_payload.get("capabilities", [])) if isinstance(reviewed_payload, dict) else {}
            sync_delta = _capability_policy_reviewed_sync_delta(reviewed_capabilities, current)
            reviewed_in_sync = not sync_delta["added"] and not sync_delta["removed"] and not sync_delta["changed"]
            ready_for_apply = reviewed_in_sync
            apply_readiness = "ready-for-apply" if ready_for_apply else "blocked-out-of-sync"
        else:
            apply_readiness = "blocked-invalid-reviewed-baseline"
    elif not template_exists:
        apply_readiness = "missing-template"

    deltas = preview.get("deltas", {}) if isinstance(preview.get("deltas"), dict) else {}
    checks = [
        {"name": "candidate-status-read-only", "status": "pass", "detail": "does not write template/reviewed baseline, apply baseline, execute capabilities, call providers, authenticate, or mutate runtime/admin/credential state"},
        {"name": "template-exists", "status": "pass" if template_exists else "warn", "detail": str(template_path.relative_to(root)) if template_exists else "missing reviewed-baseline.yaml.template"},
        {"name": "reviewed-baseline-exists", "status": "pass" if reviewed_exists else "warn", "detail": str(reviewed_path.relative_to(root)) if reviewed_exists else "missing reviewed-baseline.yaml; needs human review"},
    ]
    if reviewed_exists:
        checks.append({"name": "reviewed-baseline-valid", "status": "pass" if reviewed_valid else "fail", "detail": "valid" if reviewed_valid else "; ".join(validation_errors)})
        if reviewed_valid:
            checks.append({"name": "reviewed-baseline-in-sync", "status": "pass" if reviewed_in_sync else "fail", "detail": "matches current capability declarations" if reviewed_in_sync else f"added={len(sync_delta['added'])}; removed={len(sync_delta['removed'])}; changed={len(sync_delta['changed'])}"})
    checks.append({"name": "apply-readiness", "status": "pass" if ready_for_apply else ("fail" if apply_readiness.startswith("blocked") else "warn"), "detail": apply_readiness})
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    status = "ready-for-apply" if ready_for_apply else ("blocked" if fail_count else "needs-human-review")
    reviewer_guidance = build_capability_policy_reviewer_guidance(root, apply_readiness, template_path, reviewed_path, ready_for_apply)
    review_handoff_audit = build_capability_policy_review_handoff_audit(
        root,
        status,
        apply_readiness,
        ready_for_apply,
        template_path,
        reviewed_path,
        _capability_policy_default_baseline_path(root),
        template_path.parent / "REVIEW-INSTRUCTIONS.md",
    )
    return {
        "mode": "capability-policy-candidate-status",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "template_path": str(template_path),
        "reviewed_path": str(reviewed_path),
        "summary": {
            "status": status,
            "apply_readiness": apply_readiness,
            "ready_for_apply": ready_for_apply,
            "template_exists": template_exists,
            "reviewed_baseline_exists": reviewed_exists,
            "reviewed_baseline_valid": reviewed_valid,
            "reviewed_baseline_in_sync": reviewed_in_sync,
            "templates_written": 0,
            "reviewed_baselines_written": 0,
            "baseline_capabilities": preview.get("summary", {}).get("baseline_capabilities", 0),
            "current_capabilities": len(current),
            "added": len(deltas.get("added", [])),
            "removed": len(deltas.get("removed", [])),
            "changed": len(deltas.get("changed", [])),
            "risk_upgrades": len(deltas.get("risk_upgrades", [])),
            "risk_downgrades": len(deltas.get("risk_downgrades", [])),
            "risk_class_counts": preview.get("summary", {}).get("risk_class_counts", {}),
            "policy_outcome_counts": preview.get("summary", {}).get("policy_outcome_counts", {}),
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
        },
        "deltas": deltas,
        "reviewed_sync_delta": sync_delta,
        "validation_errors": validation_errors,
        "reviewer_guidance": reviewer_guidance,
        "review_handoff_audit": review_handoff_audit,
        "checks": checks,
        "recommendations": [
            "If reviewed-baseline.yaml is missing, copy reviewed-baseline.yaml.template only after human review.",
            "Run capability-policy-baseline-apply only when this status report says ready-for-apply.",
            "This status gate does not apply baselines, execute capabilities, call providers, authenticate, or mutate runtime/admin/credential state.",
        ],
    }


def _capability_policy_default_baseline_path(root: Path) -> Path:
    sample = root / "sample-assets" / "capability-policy" / "baseline.yaml"
    private = root / "capability-policy" / "baseline.yaml"
    return private if private.exists() else sample


def _validate_capability_baseline_payload(payload: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["baseline payload must be a mapping"]
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("capabilities must be a non-empty list")
        return errors
    for index, item in enumerate(capabilities):
        if not isinstance(item, dict):
            errors.append(f"capabilities[{index}] must be a mapping")
            continue
        if not item.get("name"):
            errors.append(f"capabilities[{index}].name is required")
        if not item.get("risk_class"):
            errors.append(f"capabilities[{index}].risk_class is required")
        if not item.get("policy_outcome"):
            errors.append(f"capabilities[{index}].policy_outcome is required")
    return errors


def execute_capability_policy_baseline_apply(root: Path = ASSETS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    reviewed_path = _capability_policy_reviewed_baseline_path(root)
    baseline_path = _capability_policy_default_baseline_path(root)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = root / "bootstrap" / "backups" / f"capability-policy-baseline-apply-{stamp}"
    backup_path = backup_dir / "baseline.yaml"
    checks: List[Dict[str, str]] = []
    results: List[Dict[str, Any]] = []
    applied = 0
    skipped = 0
    checks.append({"name": "reviewed-baseline-exists", "status": "pass" if reviewed_path.is_file() else "warn", "detail": str(reviewed_path.relative_to(root)) if reviewed_path.exists() else "missing reviewed-baseline.yaml"})
    if not reviewed_path.is_file():
        skipped = 1
        status = "skipped"
        results.append({"action": "skip", "reason": "missing-reviewed-baseline", "path": str(reviewed_path)})
    else:
        reviewed_text = reviewed_path.read_text(encoding="utf-8")
        reviewed_payload = load_yaml_data(reviewed_path)
        errors = _validate_capability_baseline_payload(reviewed_payload)
        checks.append({"name": "reviewed-baseline-valid", "status": "pass" if not errors else "fail", "detail": "; ".join(errors) if errors else "valid"})
        if errors:
            skipped = 1
            status = "blocked"
            results.append({"action": "skip", "reason": "invalid-reviewed-baseline", "errors": errors})
        else:
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            backup_dir.mkdir(parents=True, exist_ok=True)
            if baseline_path.exists():
                shutil.copy2(baseline_path, backup_path)
            else:
                backup_path.write_text("", encoding="utf-8")
            baseline_path.write_text(reviewed_text if reviewed_text.endswith("\n") else reviewed_text + "\n", encoding="utf-8")
            applied = 1
            status = "applied"
            results.append({"action": "applied", "reviewed_path": str(reviewed_path), "baseline_path": str(baseline_path), "backup_path": str(backup_path)})
    checks.append({"name": "no-runtime-mutation", "status": "pass", "detail": "only reviewed baseline file may be written; no live runtimes/providers/admin settings are touched"})
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    if fail_count:
        status = "blocked"
    elif applied:
        status = "applied"
    elif warn_count:
        status = "skipped"
    return {
        "mode": "capability-policy-baseline-apply",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "reviewed_path": str(reviewed_path),
        "baseline_path": str(baseline_path),
        "backup_path": str(backup_path) if backup_path.exists() else "",
        "summary": {
            "status": status,
            "applied": applied,
            "skipped": skipped,
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warn_count,
            "fail": fail_count,
            "executes_anything": False,
        },
        "results": results,
        "checks": checks,
        "recommendations": [
            "Use this only after a human creates reviewed-baseline.yaml from a capability policy preview.",
            "Commit reviewed baseline changes explicitly after inspecting the diff.",
            "This apply gate must never mutate live runtimes, hosted providers, admin settings, or credential bindings.",
        ],
    }


def _load_latest_report_json_for_root(root: Path, prefix: str) -> Optional[Dict[str, object]]:
    path = root / "bootstrap" / "reports" / f"latest-{prefix}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _review_axis(name: str, status: str, evidence: List[str], recommendation: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    axis = {"name": name, "status": status, "evidence": evidence, "recommendation": recommendation}
    if extra:
        axis.update(extra)
    return axis


def build_completed_work_review_report(root: Path = ASSETS) -> Dict[str, Any]:
    """Report-only checkpoint for reviewing completed phases before continuing.

    This gate intentionally reads docs/latest reports only. It does not execute project
    capabilities, start runtimes, call providers, authenticate, mutate baselines, or write
    runtime/admin state.
    """
    root = root.expanduser().resolve()
    docs_dir = root / "docs"
    roadmap_path = docs_dir / "public-roadmap.md"
    backlog_path = docs_dir / "external-reference-backlog.md"
    roadmap_text = roadmap_path.read_text(encoding="utf-8", errors="replace") if roadmap_path.is_file() else ""
    backlog_report = build_external_reference_backlog_report(root)
    latest_reports = {
        prefix: _load_latest_report_json_for_root(root, prefix)
        for prefix in [
            "release-readiness",
            "public-safety-scan",
            "external-reference-inventory",
            "external-reference-backlog",
            "capability-risk-inventory",
            "project-pack-preview",
            "capability-policy-preview",
            "capability-policy-candidate-generation",
            "capability-policy-candidate-status",
            "capability-policy-baseline-apply",
            "agent-complete-syntax-invalid-evidence-failclosed-review",
        ]
    }

    def latest_summary(prefix: str) -> Dict[str, Any]:
        report = latest_reports.get(prefix) or {}
        summary = report.get("summary") if isinstance(report, dict) else None
        return summary if isinstance(summary, dict) else {}

    checks: List[Dict[str, str]] = []
    axes: Dict[str, Dict[str, Any]] = {}

    readiness = latest_summary("release-readiness")
    readiness_ok = readiness.get("readiness") == "ready" and int(readiness.get("fail", 0) or 0) == 0
    safety = latest_summary("public-safety-scan")
    safety_ok = safety.get("status") == "pass" and int(safety.get("blockers", 0) or 0) == 0
    non_exec_reports = ["capability-risk-inventory", "project-pack-preview", "capability-policy-preview", "capability-policy-candidate-generation", "capability-policy-candidate-status", "capability-policy-baseline-apply"]
    non_exec_ok = True
    non_exec_evidence: List[str] = []
    for prefix in non_exec_reports:
        summary = latest_summary(prefix)
        if summary:
            non_exec_evidence.append(f"{prefix}: executes_anything={summary.get('executes_anything')}")
            if summary.get("executes_anything") is not False:
                non_exec_ok = False
    axes["safety"] = _review_axis(
        "Safety / correctness gate",
        "pass" if readiness_ok and safety_ok and non_exec_ok else "fail",
        [f"release-readiness={readiness.get('readiness')}", f"public-safety={safety.get('status')}"] + non_exec_evidence,
        "Keep public safety, readiness, and non-execution reports green before adding another apply surface.",
    )

    vision_keywords = ["portable", "agents", "models", "clients", "machines", "not another agent runtime", "canonical", "reviewable reconciliation"]
    present_vision = [word for word in vision_keywords if word.lower() in roadmap_text.lower()]
    completed_phases = [int(match) for match in re.findall(r"Phase\s+(\d+)\s+[^\n]*✅", roadmap_text)]
    latest_completed_phase = f"Phase {max(completed_phases)}" if completed_phases else "none"
    axes["vision_alignment"] = _review_axis(
        "Vision and roadmap alignment",
        "pass" if len(present_vision) >= 5 and completed_phases else "warn",
        [f"roadmap={roadmap_path.relative_to(root) if roadmap_path.exists() else 'missing'}", f"vision_terms={len(present_vision)}/{len(vision_keywords)}", f"latest_completed_phase={latest_completed_phase}"],
        "Continue to anchor new work in portability, canonical ownership, safe migration, and reviewable reconciliation rather than runtime replacement.",
    )

    phase103_documented = "### Phase 103 — Agent-complete Phase102 rollup evidence fail-closed review ✅" in roadmap_text
    if phase103_documented:
        phase102_report = latest_reports.get("agent-complete-syntax-invalid-evidence-failclosed-review") or {}
        phase102_validation = _validate_phase102_syntax_invalid_evidence_report(phase102_report)
        phase102_report_evidence_valid = phase102_validation["valid"]
        phase102_invalid_fields = phase102_validation.get("invalid_fields", [])
        phase102_invalid_fields_text = ",".join(str(field) for field in phase102_invalid_fields) if phase102_invalid_fields else "none"
        axes["agent_completion_evidence"] = _review_axis(
            "Agent completion evidence rollup",
            "pass" if phase102_report_evidence_valid else "fail",
            [
                f"phase103_documented={phase103_documented}",
                f"phase102_report_evidence_valid={phase102_report_evidence_valid}",
                f"invalid_fields={phase102_invalid_fields_text}",
                phase102_validation["evidence"],
            ],
            "Keep completed-work rollups blocked unless latest Phase102 report evidence is present, well-typed, and fail-closed.",
            {"invalid_fields": phase102_invalid_fields},
        )

    inventory = latest_summary("external-reference-inventory")
    reviewed_count = int((backlog_report.get("summary", {}).get("state_counts", {}) or {}).get("reviewed", 0) or 0)
    candidate_rows = backlog_report.get("high_priority_candidates", []) or []
    candidate_ids = [str(row.get("id")) for row in candidate_rows if isinstance(row, dict)]
    external_ok = reviewed_count >= 1 and (inventory.get("status") in {"ready", "needs-review"} or bool(candidate_ids))
    axes["external_learning"] = _review_axis(
        "External learning / anti-closed-door check",
        "pass" if external_ok else "warn",
        [f"reviewed_references={reviewed_count}", f"inventory_status={inventory.get('status')}", f"high_priority_candidates={', '.join(candidate_ids) if candidate_ids else 'none'}"],
        "Promote a high-priority reference/candidate through a written review before implementing comparable behavior.",
    )

    policy_preview = latest_summary("capability-policy-preview")
    candidate_generation = latest_summary("capability-policy-candidate-generation")
    candidate_status = latest_summary("capability-policy-candidate-status")
    baseline_apply = latest_summary("capability-policy-baseline-apply")
    capability_ok = (
        policy_preview.get("executes_anything") is False
        and candidate_generation.get("executes_anything") is False
        and candidate_status.get("executes_anything") is False
        and int(candidate_status.get("templates_written", 0) or 0) == 0
        and int(candidate_status.get("reviewed_baselines_written", 0) or 0) == 0
        and int(candidate_generation.get("reviewed_baselines_written", 0) or 0) == 0
        and baseline_apply.get("executes_anything") is False
        and int(baseline_apply.get("fail", 0) or 0) == 0
    )
    axes["capability_governance"] = _review_axis(
        "Capability governance boundary",
        "pass" if capability_ok else "warn",
        [
            f"policy-preview-status={policy_preview.get('status')}",
            f"candidate-generation-status={candidate_generation.get('status')}",
            f"candidate-reviewed-baselines-written={candidate_generation.get('reviewed_baselines_written')}",
            f"candidate-status={candidate_status.get('status')}",
            f"candidate-status-apply-readiness={candidate_status.get('apply_readiness')}",
            f"candidate-status-reviewed-baselines-written={candidate_status.get('reviewed_baselines_written')}",
            f"baseline-apply-status={baseline_apply.get('status')}",
            f"baseline-apply-fail={baseline_apply.get('fail')}",
        ],
        "Keep candidate generation template-only and candidate status report-only; never auto-create reviewed-baseline.yaml or update baseline without the reviewed apply gate.",
    )

    for key, axis in axes.items():
        checks.append({"name": key, "status": axis["status"], "detail": "; ".join(axis["evidence"])})
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "blocked" if fail_count else ("needs-review" if warn_count else "aligned")
    return {
        "mode": "completed-work-review",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {"status": status, "checks": len(checks), "pass": pass_count, "warn": warn_count, "fail": fail_count, "executes_anything": False},
        "review_axes": axes,
        "latest_report_summaries": {prefix: latest_summary(prefix) for prefix in latest_reports},
        "next_recommended_candidates": candidate_ids,
        "checks": checks,
        "recommendations": [
            "Review this report after each completed phase before starting the next implementation loop.",
            "If any axis warns or fails, resolve docs/reports/backlog alignment before adding new capabilities.",
            "For the next capability-policy phase, keep status/report gates read-only and require human copy/review before apply.",
        ],
    }


def build_public_safety_scan_report(root: Path = ASSETS) -> Dict[str, Any]:
    scanned_files = _iter_public_surface_files(root)
    findings: List[Dict[str, Any]] = []
    unreadable: List[Dict[str, str]] = []
    for path in scanned_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            unreadable.append({"path": str(path), "error": str(exc)})
            continue
        findings.extend(_scan_text_for_public_safety_findings(path, text, root))
    blocker_count = sum(1 for item in findings if item["severity"] == "blocker")
    warning_count = sum(1 for item in findings if item["severity"] == "warning")
    status = "blocked" if blocker_count else ("needs-review" if warning_count or unreadable else "pass")
    return {
        "mode": "public-safety-scan",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "scan_scope": PUBLIC_SAFETY_SCAN_DIRS,
        "summary": {
            "status": status,
            "scanned_files": len(scanned_files),
            "findings": len(findings),
            "blockers": blocker_count,
            "warnings": warning_count,
            "unreadable_files": len(unreadable),
        },
        "findings": findings,
        "unreadable": unreadable,
        "recommendations": [
            "Fix all blocker findings before publishing a public repository or demo pack.",
            "Review warning findings manually; example paths are preferred for public docs and sample assets.",
            "Keep raw memory, reports, candidates, backups, DBs, logs, and runtime state out of public release surfaces.",
        ],
    }


def build_release_readiness_report(root: Path = ASSETS) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add_check(name: str, status: str, detail: str, severity: str = "required") -> None:
        checks.append({"name": name, "status": status, "severity": severity, "detail": detail})

    required_paths = [
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "SECURITY.md",
        "CHANGELOG.md",
        "RELEASE_NOTES-v0.1.md",
        "docs/architecture.md",
        "docs/non-goals.md",
        "docs/adapter-sdk.md",
        "docs/open-source-release-plan.md",
        "docs/capability-policy-candidate-generation.md",
        "docs/reference-capability-policy-candidate-generation.md",
        "docs/capability-policy-candidate-status.md",
        "docs/reference-capability-policy-candidate-status.md",
        "schemas/README.md",
        "sample-assets/README.md",
        "examples/README.md",
        "examples/redacted/README.md",
        "bootstrap/setup/bootstrap-ai-assets.sh",
        "bootstrap/setup/bootstrap_ai_assets.py",
    ]
    for rel in required_paths:
        add_check(f"required:{rel}", "pass" if (root / rel).exists() else "fail", rel)

    schema_report = validate_schema_directory(root, schema_dir=ENGINE_ROOT / "schemas")
    add_check(
        "schema-validation",
        "pass" if schema_report["summary"]["invalid"] == 0 else "fail",
        f"valid={schema_report['summary']['valid']} invalid={schema_report['summary']['invalid']}",
    )

    connector_report = build_connector_report(root, schema_dir=ENGINE_ROOT / "schemas")
    add_check(
        "adapter-contracts",
        "pass" if connector_report["summary"]["invalid_adapters"] == 0 and connector_report["summary"]["total_adapters"] > 0 else "fail",
        f"total={connector_report['summary']['total_adapters']} invalid={connector_report['summary']['invalid_adapters']}",
    )

    skills_report = build_skills_inventory_report(root, schema_dir=ENGINE_ROOT / "schemas")
    add_check(
        "portable-skills",
        "pass" if skills_report["summary"]["invalid_skills"] == 0 else "fail",
        f"total={skills_report['summary']['total_skills']} invalid={skills_report['summary']['invalid_skills']}",
        severity="recommended",
    )

    team_pack_report = build_team_pack_preview_report(root)
    add_check(
        "team-pack-preview",
        "pass" if team_pack_report["summary"]["status"] == "ready" else ("fail" if team_pack_report["summary"]["status"] == "blocked" else "warn"),
        f"manifests={team_pack_report['summary']['manifests']} public_safe={team_pack_report['summary']['public_safe_manifests']}",
        severity="recommended",
    )

    capability_report = build_capability_risk_inventory_report(root)
    add_check(
        "capability-risk-inventory",
        "pass" if capability_report["summary"]["status"] == "ready" else ("fail" if capability_report["summary"]["status"] == "blocked" else "warn"),
        f"capabilities={capability_report['summary']['capabilities']} risks={capability_report['summary']['risk_class_counts']}",
        severity="recommended",
    )

    project_pack_report = build_project_pack_preview_report(root)
    add_check(
        "project-pack-preview",
        "pass" if project_pack_report["summary"]["status"] == "ready" else ("fail" if project_pack_report["summary"]["status"] == "blocked" else "warn"),
        f"manifests={project_pack_report['summary']['manifests']} capabilities={project_pack_report['summary']['capabilities']}",
        severity="recommended",
    )

    capability_policy_report = build_capability_policy_preview_report(root)
    add_check(
        "capability-policy-preview",
        "pass" if capability_policy_report["summary"]["status"] == "ready" else ("fail" if capability_policy_report["summary"]["status"] == "blocked" else "warn"),
        f"added={capability_policy_report['summary']['added']} removed={capability_policy_report['summary']['removed']} risk_upgrades={capability_policy_report['summary']['risk_upgrades']}",
        severity="recommended",
    )

    candidate_template = root / "bootstrap" / "candidates" / "capability-policy" / "reviewed-baseline.yaml.template"
    reviewed_baseline = root / "bootstrap" / "candidates" / "capability-policy" / "reviewed-baseline.yaml"
    add_check(
        "capability-policy-candidate-generation-template",
        "pass" if candidate_template.is_file() and not reviewed_baseline.exists() else ("fail" if reviewed_baseline.exists() else "warn"),
        "template present and reviewed-baseline.yaml absent" if candidate_template.is_file() and not reviewed_baseline.exists() else ("reviewed-baseline.yaml must be human-created only" if reviewed_baseline.exists() else "Run --capability-policy-candidate-generation --both before release."),
        severity="recommended",
    )

    candidate_status_report = build_capability_policy_candidate_status_report(root)
    candidate_status_summary = candidate_status_report["summary"]
    candidate_status_ok = (
        candidate_status_summary.get("executes_anything") is False
        and int(candidate_status_summary.get("templates_written", 0) or 0) == 0
        and int(candidate_status_summary.get("reviewed_baselines_written", 0) or 0) == 0
        and candidate_status_summary.get("status") in {"ready", "needs-human-review", "needs-sync"}
    )
    add_check(
        "capability-policy-candidate-status",
        "pass" if candidate_status_ok else "warn",
        f"status={candidate_status_summary.get('status')} apply_readiness={candidate_status_summary.get('apply_readiness')} writes={candidate_status_summary.get('templates_written')}/{candidate_status_summary.get('reviewed_baselines_written')}",
        severity="recommended",
    )

    safety_report = build_public_safety_scan_report(root)
    safety_status = "fail" if safety_report["summary"]["blockers"] else ("warn" if safety_report["summary"]["warnings"] else "pass")
    add_check(
        "public-safety-scan",
        safety_status,
        f"blockers={safety_report['summary']['blockers']} warnings={safety_report['summary']['warnings']}",
    )

    demo_pack_dir = root / "examples" / "redacted" / "public-demo-pack"
    demo_pack_manifest = demo_pack_dir / "MANIFEST.json"
    add_check(
        "public-demo-pack",
        "pass" if demo_pack_manifest.is_file() else "warn",
        str(demo_pack_manifest.relative_to(root)) if demo_pack_manifest.exists() else "Run --public-demo-pack --both before release.",
        severity="recommended",
    )

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    readiness = "blocked" if fail_count else ("needs-review" if warn_count else "ready")
    return {
        "mode": "release-readiness",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "readiness": readiness,
            "checks": len(checks),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "schema_invalid": schema_report["summary"]["invalid"],
            "safety_blockers": safety_report["summary"]["blockers"],
            "safety_warnings": safety_report["summary"]["warnings"],
        },
        "checks": checks,
        "recommendations": [
            "Resolve fail checks before cutting a public release.",
            "Review warn checks and regenerate the public demo pack immediately before publication.",
            "Keep the private asset repo separate from this public engine/demo surface.",
        ],
    }



def build_refresh_canonical_assets_report(root: Path = ASSETS) -> Dict[str, Any]:
    candidate_setup_dir = root / "bootstrap" / "setup"
    setup_dir = candidate_setup_dir if candidate_setup_dir.is_dir() else ENGINE_ROOT / "bootstrap" / "setup"
    steps: List[Dict[str, Any]] = []
    for name, filename in [
        ("export-canonical-profile", "export-canonical-profile.sh"),
        ("refresh-canonical-memory", "refresh-canonical-memory.sh"),
    ]:
        script = setup_dir / filename
        if not script.is_file():
            steps.append({"name": name, "script": str(script), "status": "missing", "output": "script not found"})
            continue
        ok, output = run_script(script, extra_env={
            "PAA_ENGINE_ROOT": str(ENGINE_ROOT),
            "PAA_ASSET_ROOT": str(root),
            "PAA_CONFIG_PATH": CURRENT_RUNTIME_PATHS.get("config_path", ""),
        })
        steps.append({"name": name, "script": str(script), "status": "ok" if ok else "failed", "output": output})
    return {
        "mode": "refresh-canonical-assets",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "total_steps": len(steps),
            "successful_steps": sum(1 for step in steps if step["status"] == "ok"),
            "failed_steps": sum(1 for step in steps if step["status"] == "failed"),
            "missing_steps": sum(1 for step in steps if step["status"] == "missing"),
        },
        "steps": steps,
    }



def _write_text_if_missing(path: Path, text: str) -> str:
    if path.exists():
        return "exists"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return "created"


def _write_config_with_backup(config_path: Path, text: str) -> Dict[str, Any]:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {"path": str(config_path), "status": "created", "backup_path": None}
    if config_path.exists():
        current = config_path.read_text(encoding="utf-8", errors="replace")
        if current == text:
            result["status"] = "unchanged"
            return result
        backup_path = config_path.with_suffix(config_path.suffix + f".{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.bak")
        shutil.copy2(config_path, backup_path)
        result["status"] = "updated-with-backup"
        result["backup_path"] = str(backup_path)
    config_path.write_text(text, encoding="utf-8")
    return result


def build_private_assets_readme(asset_root: Path, engine_root: Path) -> str:
    return f"""# Private AI Assets

This repository stores private, canonical AI memory/assets for Portable AI Assets.

It is intended to be paired with a separate public engine checkout:

- engine_root: `{engine_root}`
- asset_root: `{asset_root}`

## What belongs here

- cleaned long-term memory summaries
- project summaries
- private adapter sources
- private stack/manifests
- review reports and merge candidates

## What should not be committed

- raw runtime databases
- session logs
- caches
- secrets
- credentials

Default workflow:

1. keep using AI runtimes normally
2. run refresh/export from the engine
3. review diffs in this private assets repo
4. commit/push intentionally
"""


def build_private_assets_gitignore() -> str:
    return """# Runtime-heavy / non-canonical state
non-git-backups/
memory/summaries/mempalace-latest/
bootstrap/backups/
bootstrap/state/
*.db
*.sqlite
*.sqlite3
*.db-wal
*.db-shm
*.log
*.tmp
.DS_Store

# Secrets / credentials
.env
.env.*
*secret*
*credential*
*token*
"""


def build_private_assets_git_policy() -> str:
    return """# Private AI Assets Git Policy

## Commit to this repo

- `memory/profile/` cleaned user/profile summaries
- `memory/projects/` durable project summaries
- `adapters/` private canonical adapter sources
- `stack/` private manifests and restore metadata
- `bootstrap/reports/` review reports when useful

## Do not commit by default

- raw runtime DBs
- histories / session traces
- caches
- credentials / tokens / local settings
- large raw export archives

Treat this repo as a long-term asset ledger, not as a mirror of every runtime file.
"""


def build_local_config_text(asset_root: Path, engine_root: Path, asset_repo_remote: Optional[str] = None) -> str:
    remote_line = f"asset_repo_remote: {asset_repo_remote}\n" if asset_repo_remote else "asset_repo_remote: null\n"
    return (
        f"engine_root: {engine_root}\n"
        f"asset_root: {asset_root}\n"
        f"{remote_line}"
        "default_sync_mode: review-before-commit\n"
        "allow_auto_commit: false\n"
    )


def initialize_private_assets_repo(
    asset_root: Path = ASSETS,
    *,
    config_path: Optional[Path] = None,
    asset_repo_remote: Optional[str] = None,
    initialize_git: bool = True,
) -> Dict[str, Any]:
    asset_root = asset_root.expanduser().resolve()
    engine_root = ENGINE_ROOT.expanduser().resolve()
    config_target = (config_path or Path(CURRENT_RUNTIME_PATHS.get("config_path") or (HOME / ".config" / "portable-ai-assets" / "config.yaml"))).expanduser().resolve()

    directories = [
        "memory/profile",
        "memory/projects",
        "memory/summaries",
        "skills",
        "adapters/hermes",
        "adapters/claude",
        "adapters/codex",
        "stack/tools",
        "stack/mcp",
        "bootstrap/reports",
        "bootstrap/candidates",
        "non-git-backups",
    ]
    dir_results: List[Dict[str, str]] = []
    for rel in directories:
        path = asset_root / rel
        existed = path.is_dir()
        path.mkdir(parents=True, exist_ok=True)
        dir_results.append({"path": str(path), "status": "exists" if existed else "created"})

    file_results: List[Dict[str, str]] = []
    for rel, text in [
        ("README.md", build_private_assets_readme(asset_root, engine_root)),
        ("GIT-POLICY.md", build_private_assets_git_policy()),
        (".gitignore", build_private_assets_gitignore()),
        ("memory/README.md", "# Memory\n\nCanonical memory summaries for this private asset repo.\n"),
        ("skills/README.md", "# Skills\n\nPortable skill manifests promoted through review from runtime learning, manual procedures, or external references.\n"),
        ("adapters/README.md", "# Adapters\n\nPrivate canonical adapter sources for runtime-specific projections.\n"),
        ("stack/README.md", "# Stack\n\nPrivate tool, MCP, bridge, and restore manifests.\n"),
        ("bootstrap/README.md", "# Bootstrap Artifacts\n\nReports, candidates, and local review artifacts generated by the public engine.\n"),
    ]:
        path = asset_root / rel
        status = _write_text_if_missing(path, text)
        file_results.append({"path": str(path), "status": status})

    git_result: Dict[str, Any] = {"attempted": initialize_git, "status": "skipped", "output": ""}
    if initialize_git:
        import subprocess

        if (asset_root / ".git").exists():
            git_result.update({"status": "exists", "output": "Git repository already initialized"})
        else:
            try:
                completed = subprocess.run(
                    ["git", "init"],
                    cwd=str(asset_root),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=30,
                    check=False,
                )
                git_result.update({"status": "ok" if completed.returncode == 0 else "failed", "output": completed.stdout.strip()})
            except Exception as exc:
                git_result.update({"status": "failed", "output": str(exc)})

    config_text = build_local_config_text(asset_root, engine_root, asset_repo_remote)
    config_result = _write_config_with_backup(config_target, config_text)

    return {
        "mode": "init-private-assets",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(engine_root),
        "root": str(asset_root),
        "config_path": str(config_target),
        "asset_repo_remote": asset_repo_remote,
        "summary": {
            "directories": len(dir_results),
            "created_directories": sum(1 for item in dir_results if item["status"] == "created"),
            "files": len(file_results),
            "created_files": sum(1 for item in file_results if item["status"] == "created"),
            "config_status": config_result["status"],
            "git_status": git_result["status"],
        },
        "directories": dir_results,
        "files": file_results,
        "git": git_result,
        "config": config_result,
        "next_steps": [
            "Review generated private asset scaffold",
            "Run ./bootstrap/setup/bootstrap-ai-assets.sh --show-config",
            "Run ./bootstrap/setup/bootstrap-ai-assets.sh --refresh-canonical-assets --both",
            "Review git diff in the private assets repo before commit/push",
        ],
    }



def run_git_command(root: Path, args: List[str], timeout: int = 30) -> Dict[str, Any]:
    import subprocess

    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return {"ok": completed.returncode == 0, "returncode": completed.returncode, "output": (completed.stdout or "").strip()}
    except Exception as exc:
        return {"ok": False, "returncode": None, "output": str(exc)}


def parse_git_status_short(output: str) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    for line in output.splitlines():
        if not line:
            continue
        if len(line) > 3 and line[2] == " ":
            status = line[:2]
            path_text = line[3:]
        else:
            parts = line.split(maxsplit=1)
            status = (parts[0] if parts else "").ljust(2)
            path_text = parts[1] if len(parts) > 1 else ""
        # Rename/copy lines look like "R  old -> new"; the final path is usually what reviewers need.
        display_path = path_text.split(" -> ")[-1]
        category = "other"
        if display_path.startswith("memory/profile/"):
            category = "memory_profile"
        elif display_path.startswith("memory/projects/"):
            category = "memory_projects"
        elif display_path.startswith("memory/"):
            category = "memory_other"
        elif display_path.startswith("skills/"):
            category = "skills"
        elif display_path.startswith("adapters/"):
            category = "adapters"
        elif display_path.startswith("stack/"):
            category = "stack"
        elif display_path.startswith("bootstrap/reports/"):
            category = "reports"
        elif display_path.startswith("bootstrap/candidates/"):
            category = "candidates"
        elif display_path.startswith("docs/") or display_path == "README.md" or display_path.endswith("POLICY.md"):
            category = "docs_policy"
        entries.append({"status": status, "path": display_path, "raw": line, "category": category})
    return entries


def run_probe_command(args: List[str], timeout: int = 8) -> Dict[str, Any]:
    import subprocess

    exe = shutil.which(args[0])
    if not exe:
        return {"available": False, "path": None, "ok": False, "timed_out": False, "returncode": None, "output": "command not found"}
    try:
        completed = subprocess.run(
            [exe, *args[1:]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {"available": True, "path": exe, "ok": completed.returncode == 0, "timed_out": False, "returncode": completed.returncode, "output": (completed.stdout or "").strip()[:2000]}
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or "")).strip() if isinstance(exc.stdout, str) else ""
        return {"available": True, "path": exe, "ok": False, "timed_out": True, "returncode": None, "output": output or f"timed out after {timeout}s"}
    except Exception as exc:
        return {"available": True, "path": exe, "ok": False, "timed_out": False, "returncode": None, "output": str(exc)}


def build_memos_health_report(root: Path = ASSETS) -> Dict[str, Any]:
    hermes_runtime = HOME / ".hermes" / "memos-plugin"
    hermes_plugin = HOME / ".hermes" / "plugins" / "memos-local-plugin"
    paths = {
        "hermes_runtime_root": hermes_runtime,
        "hermes_plugin_code": hermes_plugin,
        "config": hermes_runtime / "config.yaml",
        "sqlite_db": hermes_runtime / "data" / "memos.db",
        "skills": hermes_runtime / "skills",
        "logs": hermes_runtime / "logs",
    }
    path_results = {name: {"path": str(path), "exists": path.exists(), "is_dir": path.is_dir(), "is_file": path.is_file()} for name, path in paths.items()}
    commands = {
        "node_version": run_probe_command(["node", "--version"]),
        "npm_version": run_probe_command(["npm", "--version"]),
        "hermes_version": run_probe_command(["hermes", "--version"]),
        "hermes_plugins_list": run_probe_command(["hermes", "plugins", "list"], timeout=12),
        "hermes_memory_status": run_probe_command(["hermes", "memory", "status"], timeout=12),
        "memos_npm_view": run_probe_command(["npm", "view", "@memtensor/memos-local-plugin", "version", "--json"], timeout=20),
    }
    blockers: List[str] = []
    for key in ["node_version", "npm_version", "hermes_version"]:
        if not commands[key]["ok"]:
            blockers.append(f"{key} is not healthy: {commands[key]['output']}")
    if not path_results["hermes_runtime_root"]["exists"]:
        blockers.append("MemOS Hermes runtime root is not present yet")
    if not path_results["hermes_plugin_code"]["exists"]:
        blockers.append("MemOS Hermes plugin code is not installed yet")
    recommendations = [
        "Do not enable MemOS in the main Hermes profile until node/npm/hermes probes are healthy",
        "Use a Hermes test profile before installing into the main profile",
        "Back up ~/.hermes before any plugin install",
        "After runtime DB exists, run a read-only import preview before writing canonical assets",
    ]
    return {
        "mode": "memos-health",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "summary": {
            "commands_checked": len(commands),
            "healthy_commands": sum(1 for item in commands.values() if item["ok"]),
            "runtime_paths_present": sum(1 for item in path_results.values() if item["exists"]),
            "blockers": len(blockers),
            "ready_for_test_profile_install": len(blockers) == 0,
        },
        "commands": commands,
        "paths": path_results,
        "blockers": blockers,
        "recommendations": recommendations,
    }



MEMOS_KNOWN_TABLES = [
    "sessions",
    "episodes",
    "traces",
    "policies",
    "l2_candidate_pool",
    "world_model",
    "skills",
    "feedback",
    "decision_repairs",
    "audit_events",
    "kv",
]


def _sqlite_table_names(db_path: Path) -> List[str]:
    import sqlite3

    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=3)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return [str(row[0]) for row in rows]
    finally:
        conn.close()


def _sqlite_count_rows(db_path: Path, table: str) -> Optional[int]:
    import sqlite3

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
        return None
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=3)
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception:
        return None
    finally:
        conn.close()


def _sqlite_max_column(db_path: Path, table: str, column: str) -> Optional[Any]:
    import sqlite3

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table) or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", column):
        return None
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=3)
    try:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in columns:
            return None
        value = conn.execute(f"SELECT MAX({column}) FROM {table}").fetchone()[0]
        return value
    except Exception:
        return None
    finally:
        conn.close()


def _memos_candidate_outputs(table_counts: Dict[str, Optional[int]]) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    if (table_counts.get("traces") or 0) > 0 or (table_counts.get("episodes") or 0) > 0:
        candidates.append({"source": "traces/episodes", "candidate_path": "memory/projects/<reviewed-from-memos>.md", "review": "summarize durable project facts; exclude raw dialogue and secrets"})
    if (table_counts.get("policies") or 0) > 0:
        candidates.append({"source": "policies", "candidate_path": "memory/policies/<reviewed-policy>.md", "review": "preserve recurring strategy only if broadly useful"})
    if (table_counts.get("world_model") or 0) > 0:
        candidates.append({"source": "world_model", "candidate_path": "memory/world-models/<reviewed-world-model>.md", "review": "preserve stable environment abstractions; avoid stale topology"})
    if (table_counts.get("skills") or 0) > 0:
        candidates.append({"source": "skills", "candidate_path": "skills/<portable-skill>.yaml", "review": "convert only reviewed active/probationary skills with evidence"})
    if (table_counts.get("decision_repairs") or 0) > 0:
        candidates.append({"source": "decision_repairs", "candidate_path": "memory/profile/preferences.md", "review": "promote only stable preferences/anti-patterns"})
    return candidates


def build_memos_import_preview_report(root: Path = ASSETS) -> Dict[str, Any]:
    memos_root = HOME / ".hermes" / "memos-plugin"
    db_path = memos_root / "data" / "memos.db"
    config_path = memos_root / "config.yaml"
    skills_dir = memos_root / "skills"
    logs_dir = memos_root / "logs"
    db_exists = db_path.is_file()
    tables: List[str] = []
    table_counts: Dict[str, Optional[int]] = {}
    latest_values: Dict[str, Optional[Any]] = {}
    errors: List[str] = []
    if db_exists:
        try:
            tables = _sqlite_table_names(db_path)
            for table in MEMOS_KNOWN_TABLES:
                if table in tables:
                    table_counts[table] = _sqlite_count_rows(db_path, table)
                    latest_values[table] = _sqlite_max_column(db_path, table, "updated_at") or _sqlite_max_column(db_path, table, "ts") or _sqlite_max_column(db_path, table, "last_seen_at")
                else:
                    table_counts[table] = None
                    latest_values[table] = None
        except Exception as exc:
            errors.append(str(exc))
    else:
        errors.append("MemOS SQLite DB not found; install/enable MemOS for Hermes before import preview")
        for table in MEMOS_KNOWN_TABLES:
            table_counts[table] = None
            latest_values[table] = None
    candidates = _memos_candidate_outputs(table_counts)
    recommendations = [
        "This mode is read-only and does not write canonical assets",
        "Do not commit MemOS SQLite/log files directly to Git",
        "Use generated candidate paths only after human review",
    ]
    if not db_exists:
        recommendations.insert(0, "Run --memos-health and enable MemOS in a Hermes test profile before expecting import candidates")
    elif not candidates:
        recommendations.insert(0, "MemOS DB exists but no importable rows were detected yet; use Hermes with MemOS for a while and retry")
    else:
        recommendations.insert(0, "Review candidate mappings before generating canonical summaries")
    return {
        "mode": "memos-import-preview",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "memos": {
            "runtime_root": str(memos_root),
            "config_path": str(config_path),
            "config_exists": config_path.is_file(),
            "db_path": str(db_path),
            "db_exists": db_exists,
            "skills_dir": str(skills_dir),
            "skills_dir_exists": skills_dir.is_dir(),
            "logs_dir": str(logs_dir),
            "logs_dir_exists": logs_dir.is_dir(),
        },
        "summary": {
            "tables_detected": len(tables),
            "known_tables_present": sum(1 for table in MEMOS_KNOWN_TABLES if table in tables),
            "candidate_outputs": len(candidates),
            "errors": len(errors),
        },
        "tables": tables,
        "table_counts": table_counts,
        "latest_values": latest_values,
        "candidate_outputs": candidates,
        "errors": errors,
        "recommendations": recommendations,
    }



def _sqlite_table_columns(db_path: Path, table: str) -> List[str]:
    import sqlite3

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
        return []
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=3)
    try:
        return [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    finally:
        conn.close()



def _sqlite_select_dict_rows(db_path: Path, table: str, limit: int = 100) -> List[Dict[str, Any]]:
    import sqlite3

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
        return []
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=3)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"SELECT * FROM {table} LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()



def _first_nonempty(row: Dict[str, Any], keys: List[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default



def _yaml_scalar(value: str) -> str:
    value = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not value:
        return ""
    if "\n" in value or value.startswith(("-", "#", "{", "[", "!", "@")) or ":" in value:
        return json.dumps(value, ensure_ascii=False)
    return value



def _yaml_list_block(items: List[str], indent: str = "  ") -> str:
    clean = [item.strip() for item in items if str(item).strip()]
    if not clean:
        clean = ["Review imported runtime evidence before use."]
    return "\n".join(f"{indent}- {_yaml_scalar(item)}" for item in clean)



def _split_steps(text: str) -> List[str]:
    if not text:
        return []
    parts: List[str] = []
    for line in str(text).replace("\r\n", "\n").split("\n"):
        stripped = line.strip().lstrip("-*").strip()
        if stripped:
            parts.append(stripped)
    return parts or [str(text).strip()]



def _runtime_skill_to_candidate_yaml(row: Dict[str, Any], db_path: Path) -> Tuple[str, str]:
    raw_name = _first_nonempty(row, ["name", "title", "skill_name", "key", "id"], "memos-runtime-skill")
    name = safe_slug(raw_name.lower())
    row_id = _first_nonempty(row, ["id", "skill_id", "uuid", "key"], name)
    description = _first_nonempty(row, ["description", "summary", "content", "body"], "Imported MemOS runtime skill candidate; review before promotion.")
    trigger = _first_nonempty(row, ["trigger", "when_to_use", "activation", "context"], "Review imported MemOS evidence before using this skill.")
    procedure_text = _first_nonempty(row, ["procedure", "steps", "instructions", "content", "body"], "Review the source row and rewrite into a portable procedure.")
    verification_text = _first_nonempty(row, ["verification", "tests", "success_criteria"], "Validate against reports/tests before promotion.")
    boundaries_text = _first_nonempty(row, ["boundaries", "constraints", "risks"], "Do not auto-apply runtime-imported behavior without human review.")
    confidence = _first_nonempty(row, ["confidence", "reliability", "score"], "medium").lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    # Runtime-imported skills are intentionally downgraded to probationary unless retired.
    runtime_status = _first_nonempty(row, ["status", "state", "lifecycle"], "probationary").lower()
    status = "retired" if runtime_status == "retired" else "probationary"
    updated_at = _first_nonempty(row, ["updated_at", "last_seen_at", "ts", "created_at"], "unknown")
    yaml_text = "\n".join([
        f"name: {name}",
        "skill_version: v1",
        f"status: {status}",
        f"confidence: {confidence}",
        f"description: {_yaml_scalar(description)}",
        f"trigger: {_yaml_scalar(trigger)}",
        "procedure:",
        _yaml_list_block(_split_steps(procedure_text)),
        "verification:",
        _yaml_list_block(_split_steps(verification_text)),
        "boundaries:",
        _yaml_list_block(_split_steps(boundaries_text)),
        "source_evidence:",
        "  - type: runtime-import",
        f"    reference: MemOS skills table row {row_id}",
        f"    note: Imported read-only from {db_path}; runtime_status={runtime_status}; updated_at={updated_at}",
        "adapter_projection:",
        "  hermes: adapters/hermes/USER.md",
        "  claude-code: adapters/claude/instructions.md",
        "  codex: adapters/codex/instructions.md",
        "",
    ])
    return name, yaml_text



def build_memos_skill_candidates_report(root: Path = ASSETS, memos_root: Optional[Path] = None) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    memos_root = memos_root or (HOME / ".hermes" / "memos-plugin")
    db_path = memos_root / "data" / "memos.db"
    errors: List[str] = []
    candidates: List[Dict[str, Any]] = []
    source_rows = 0
    bundle_dir: Optional[Path] = None
    table_columns: List[str] = []
    if not db_path.is_file():
        errors.append("MemOS SQLite DB not found; run --memos-health and --memos-import-preview first")
    else:
        try:
            tables = _sqlite_table_names(db_path)
            if "skills" not in tables:
                errors.append("MemOS SQLite DB has no skills table")
            else:
                table_columns = _sqlite_table_columns(db_path, "skills")
                rows = _sqlite_select_dict_rows(db_path, "skills", limit=100)
                source_rows = len(rows)
                if rows:
                    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
                    bundle_dir = root / "bootstrap" / "candidates" / f"memos-skills-{stamp}"
                    bundle_dir.mkdir(parents=True, exist_ok=True)
                    for index, row in enumerate(rows, start=1):
                        name, yaml_text = _runtime_skill_to_candidate_yaml(row, db_path)
                        candidate_path = bundle_dir / f"{index:03d}-{name}.candidate.yaml"
                        candidate_path.write_text(yaml_text, encoding="utf-8")
                        candidates.append({
                            "name": name,
                            "candidate_path": str(candidate_path),
                            "source_row_id": _first_nonempty(row, ["id", "skill_id", "uuid", "key"], str(index)),
                            "status": "candidate",
                            "review_required": True,
                        })
                    (bundle_dir / "REVIEW-INSTRUCTIONS.md").write_text(
                        "# MemOS Skill Candidate Review\n\n"
                        "These files were generated from the MemOS runtime `skills` table in read-only mode.\n\n"
                        "Review checklist:\n\n"
                        "- Keep candidates as `probationary` until evidence is verified.\n"
                        "- Remove runtime noise, secrets, and environment-specific assumptions.\n"
                        "- Strengthen `procedure`, `verification`, and `boundaries` before promoting to `active`.\n"
                        "- Copy reviewed files into `skills/<name>.yaml`; do not commit raw MemOS DB/logs.\n",
                        encoding="utf-8",
                    )
                    summary_lines = [
                        "# MemOS Skill Candidates Summary",
                        "",
                        f"Source DB: `{db_path}`",
                        f"Source rows: {source_rows}",
                        f"Generated candidates: {len(candidates)}",
                        "",
                    ]
                    for item in candidates:
                        summary_lines.append(f"- {item['name']}: `{item['candidate_path']}`")
                    (bundle_dir / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
                else:
                    errors.append("MemOS skills table exists but contains no rows")
        except Exception as exc:
            errors.append(str(exc))
    recommendations = [
        "This mode reads MemOS SQLite and writes candidate YAML files only; it does not modify canonical skills or runtime config",
        "Review candidates before copying them into skills/<name>.yaml",
        "Keep imported skills probationary until source evidence, verification, and boundaries are strong",
    ]
    return {
        "mode": "memos-skill-candidates",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "memos": {
            "runtime_root": str(memos_root),
            "db_path": str(db_path),
            "db_exists": db_path.is_file(),
            "skills_table_columns": table_columns,
        },
        "bundle_dir": str(bundle_dir) if bundle_dir else None,
        "summary": {
            "source_rows": source_rows,
            "generated_candidates": len(candidates),
            "errors": len(errors),
        },
        "candidates": candidates,
        "errors": errors,
        "recommendations": recommendations,
    }



def _discover_skill_candidate_bundles(root: Path) -> List[Path]:
    candidates_root = root / "bootstrap" / "candidates"
    if not candidates_root.is_dir():
        return []
    bundles = [path for path in candidates_root.glob("memos-skills-*") if path.is_dir()]
    return sorted(bundles, key=lambda path: path.name)



def _validate_portable_skill_file(path: Path, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    try:
        payload = load_yaml_data(path)
        validation = validate_manifest_payload("portable-skill-manifest-v1", payload, schema_dir=schema_dir)
        name = payload.get("name") if isinstance(payload, dict) else None
    except Exception as exc:
        payload = {}
        validation = {"valid": False, "errors": [str(exc)], "schema": "portable-skill-manifest-v1"}
        name = None
    return {"payload": payload, "name": name, "valid": validation["valid"], "errors": validation["errors"]}



def build_skill_candidates_status_report(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    bundles = _discover_skill_candidate_bundles(root)
    bundle_entries: List[Dict[str, Any]] = []
    candidate_total = 0
    reviewed_total = 0
    ready_total = 0
    for bundle in bundles:
        candidate_files = sorted(bundle.glob("*.candidate.yaml"))
        reviewed_files = sorted(bundle.glob("*.reviewed.yaml"))
        reviewed_entries: List[Dict[str, Any]] = []
        for reviewed in reviewed_files:
            validation = _validate_portable_skill_file(reviewed, schema_dir=schema_dir)
            reviewed_entries.append({
                "path": str(reviewed),
                "name": validation["name"],
                "valid": validation["valid"],
                "errors": validation["errors"],
                "ready_to_apply": validation["valid"],
            })
            if validation["valid"]:
                ready_total += 1
        candidate_total += len(candidate_files)
        reviewed_total += len(reviewed_files)
        bundle_entries.append({
            "bundle_dir": str(bundle),
            "candidate_files": [str(path) for path in candidate_files],
            "reviewed_files": reviewed_entries,
            "ready_to_apply": sum(1 for item in reviewed_entries if item["ready_to_apply"]),
        })
    return {
        "mode": "skill-candidates-status",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "schema_dir": str(schema_dir),
        "summary": {
            "bundles": len(bundles),
            "candidate_files": candidate_total,
            "reviewed_files": reviewed_total,
            "ready_to_apply": ready_total,
        },
        "bundles": bundle_entries,
        "recommendations": [
            "Create reviewed files as *.reviewed.yaml next to candidate files after human review",
            "Run --skill-review-apply only after reviewed files validate as portable skill manifests",
            "Review git diff after applying reviewed skills; do not auto-push",
        ],
    }



def execute_skill_review_apply(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    status_report = build_skill_candidates_status_report(root, schema_dir=schema_dir)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = root / "bootstrap" / "backups" / f"skill-review-apply-{stamp}"
    skills_root = root / "skills"
    results: List[Dict[str, Any]] = []
    applied = 0
    skipped = 0
    failed = 0
    for bundle in status_report["bundles"]:
        for reviewed in bundle.get("reviewed_files", []):
            source = Path(reviewed["path"])
            result = {
                "source": str(source),
                "target": None,
                "name": reviewed.get("name"),
                "status": "skipped",
                "details": "",
                "backup_path": None,
            }
            if not reviewed.get("valid"):
                result["details"] = f"Reviewed file is not a valid portable skill manifest: {', '.join(reviewed.get('errors', []))}"
                skipped += 1
                results.append(result)
                continue
            name = safe_slug(str(reviewed.get("name") or source.stem.replace(".reviewed", "")))
            target = skills_root / f"{name}.yaml"
            result["target"] = str(target)
            try:
                text = source.read_text(encoding="utf-8")
                if not text.strip():
                    raise ValueError("reviewed skill file is empty")
                target.parent.mkdir(parents=True, exist_ok=True)
                backup_path = backup_target(target, backup_root)
                target.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
                result.update({
                    "status": "applied",
                    "details": "Copied reviewed portable skill into canonical skills directory",
                    "backup_path": str(backup_path) if backup_path else None,
                })
                applied += 1
            except Exception as exc:
                result.update({"status": "failed", "details": str(exc)})
                failed += 1
            results.append(result)
    if not results:
        skipped = 0
    return {
        "mode": "skill-review-apply",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "backup_root": str(backup_root),
        "based_on_status_generated_at": status_report["generated_at"],
        "summary": {"applied": applied, "skipped": skipped, "failed": failed},
        "results": results,
        "recommendations": [
            "Run --skills-inventory after applying reviewed skills",
            "Review the private asset repo diff before commit/push",
            "Project applied skills into adapters only through explicit review/apply flows",
        ],
    }



def build_private_assets_status_report(root: Path = ASSETS) -> Dict[str, Any]:
    root = root.expanduser().resolve()
    root_exists = root.is_dir()
    git_probe = run_git_command(root, ["rev-parse", "--is-inside-work-tree"]) if root_exists else {"ok": False, "output": "asset root does not exist"}
    is_git_repo = bool(git_probe.get("ok") and git_probe.get("output") == "true")

    branch = "unknown"
    remotes: List[Dict[str, str]] = []
    status_entries: List[Dict[str, str]] = []
    diff_stat = ""
    upstream_status = "unknown"

    if is_git_repo:
        branch_result = run_git_command(root, ["branch", "--show-current"])
        branch = branch_result["output"] or "detached-or-unknown"
        remote_result = run_git_command(root, ["remote", "-v"])
        seen_remotes = set()
        if remote_result["ok"]:
            for line in remote_result["output"].splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    key = (parts[0], parts[1])
                    if key not in seen_remotes:
                        remotes.append({"name": parts[0], "url": parts[1]})
                        seen_remotes.add(key)
        status_result = run_git_command(root, ["status", "--short"])
        if status_result["ok"]:
            status_entries = parse_git_status_short(status_result["output"])
        diff_result = run_git_command(root, ["diff", "--stat"])
        if diff_result["ok"]:
            diff_stat = diff_result["output"]
        upstream_result = run_git_command(root, ["status", "-sb"])
        if upstream_result["ok"]:
            first_line = upstream_result["output"].splitlines()[0] if upstream_result["output"].splitlines() else ""
            upstream_status = first_line

    dirty = bool(status_entries)
    has_remote = bool(remotes) or bool(CURRENT_RUNTIME_PATHS.get("asset_repo_remote"))
    categories: Dict[str, int] = {}
    for entry in status_entries:
        categories[entry["category"]] = categories.get(entry["category"], 0) + 1

    recommendations: List[str] = []
    if not root_exists:
        recommendations.append("Run --init-private-assets to create and bind a private asset repo")
    elif not is_git_repo:
        recommendations.append("Initialize Git in the private asset root before relying on status/review reports")
    elif not dirty:
        recommendations.append("No local private asset changes detected; nothing to commit")
    else:
        recommendations.append("Review changed canonical assets before committing")
        if categories.get("memory_profile") or categories.get("memory_projects"):
            recommendations.append("Memory summaries changed; inspect them for durable facts vs runtime noise")
        if categories.get("skills"):
            recommendations.append("Portable skills changed; verify lifecycle status, evidence, boundaries, and projection safety")
        if categories.get("adapters"):
            recommendations.append("Adapter files changed; run diff/review before projecting to runtimes")
        recommendations.append("Commit locally only after review; push only when intentionally syncing the private repo")
    if root_exists and is_git_repo and not has_remote:
        recommendations.append("No Git remote detected; add one manually if this private repo should sync across machines")

    return {
        "mode": "private-assets-status",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "configured_asset_repo_remote": CURRENT_RUNTIME_PATHS.get("asset_repo_remote"),
        "git": {
            "root_exists": root_exists,
            "is_git_repo": is_git_repo,
            "branch": branch,
            "has_remote": has_remote,
            "remotes": remotes,
            "upstream_status": upstream_status,
            "dirty": dirty,
        },
        "summary": {
            "changed_files": len(status_entries),
            "categories": categories,
            "recommendation_count": len(recommendations),
        },
        "changes": status_entries,
        "diff_stat": diff_stat,
        "recommendations": recommendations,
    }



def load_yaml_data(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return simple_yaml_load(handle.read())



def load_schema_definition(schema_name: str, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    if schema_name not in SCHEMA_FILE_MAP:
        raise KeyError(f"Unknown schema: {schema_name}")
    schema_path = schema_dir / SCHEMA_FILE_MAP[schema_name]
    if schema_path.is_file():
        return json.loads(schema_path.read_text(encoding="utf-8"))
    return DEFAULT_SCHEMA_DEFINITIONS[schema_name]



def validate_manifest_payload(schema_name: str, payload: Any, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    schema = load_schema_definition(schema_name, schema_dir=schema_dir)
    errors: List[str] = []
    if schema.get("type") == "object" and not isinstance(payload, dict):
        return {"valid": False, "errors": ["payload must be a mapping/object"], "schema": schema_name}

    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in payload:
            errors.append(f"missing required field: {field}")

    enum_rules = dict(schema.get("enum", {}))
    for field, field_spec in schema.get("properties", {}).items():
        if isinstance(field_spec, dict) and "enum" in field_spec:
            enum_rules.setdefault(field, field_spec["enum"])
    for field, allowed_values in enum_rules.items():
        if field in payload and payload[field] not in allowed_values:
            errors.append(f"field {field} must be one of: {', '.join(allowed_values)}")

    return {"valid": not errors, "errors": errors, "schema": schema_name}



def validate_schema_directory(root: Path = ASSETS, schema_dir: Path = SCHEMAS) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    manifest_paths = _discover_manifest_paths(root)
    for manifest_path in manifest_paths:
        schema_name = detect_manifest_schema(manifest_path)
        if not schema_name:
            continue
        try:
            payload = load_yaml_data(manifest_path)
            validation = validate_manifest_payload(schema_name, payload, schema_dir=schema_dir)
        except Exception as exc:
            validation = {"valid": False, "errors": [str(exc)], "schema": schema_name}
        results.append(
            {
                "path": str(manifest_path),
                "schema": schema_name,
                "valid": validation["valid"],
                "errors": validation["errors"],
            }
        )

    return {
        "mode": "validate-schemas",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "host_home": str(HOME),
        "engine_root": str(ENGINE_ROOT),
        "root": str(root),
        "config_path": CURRENT_RUNTIME_PATHS.get("config_path"),
        "schema_dir": str(schema_dir),
        "summary": {
            "total": len(results),
            "valid": sum(1 for item in results if item["valid"]),
            "invalid": sum(1 for item in results if not item["valid"]),
        },
        "results": results,
    }



def split_document_sections(text: str) -> List[Dict[str, str]]:
    normalized_text = text.replace("\r\n", "\n")
    lines = normalized_text.split("\n")
    sections: List[Dict[str, str]] = []

    if any(line.strip() == "§" for line in lines):
        blocks = []
        current: List[str] = []
        for line in lines:
            if line.strip() == "§":
                block = "\n".join(current).strip()
                if block:
                    blocks.append(block)
                current = []
            else:
                current.append(line)
        tail = "\n".join(current).strip()
        if tail:
            blocks.append(tail)
        for idx, block in enumerate(blocks, start=1):
            sections.append({
                "label": _section_label(block, f"section-{idx}"),
                "content": block,
                "normalized": _normalize_text_block(block),
            })
        return sections

    heading_indexes = [idx for idx, line in enumerate(lines) if line.lstrip().startswith("#")]
    if heading_indexes:
        for pos, start in enumerate(heading_indexes):
            end = heading_indexes[pos + 1] if pos + 1 < len(heading_indexes) else len(lines)
            chunk = "\n".join(lines[start:end]).strip()
            if chunk:
                heading = lines[start].strip()
                sections.append({
                    "label": heading,
                    "content": chunk,
                    "normalized": _normalize_text_block(chunk),
                })
        if sections:
            return sections

    blocks = [block.strip() for block in normalized_text.split("\n\n") if block.strip()]
    for idx, block in enumerate(blocks, start=1):
        sections.append({
            "label": _section_label(block, f"block-{idx}"),
            "content": block,
            "normalized": _normalize_text_block(block),
        })
    return sections



def compare_document_sections(canonical_text: str, live_text: str) -> Dict[str, object]:
    canonical_sections = split_document_sections(canonical_text)
    live_sections = split_document_sections(live_text)

    canonical_map = {section["normalized"]: section for section in canonical_sections}
    live_map = {section["normalized"]: section for section in live_sections}

    canonical_only = [section for key, section in canonical_map.items() if key not in live_map]
    live_only = [section for key, section in live_map.items() if key not in canonical_map]

    canonical_by_label = {section["label"]: section for section in canonical_sections}
    live_by_label = {section["label"]: section for section in live_sections}
    changed_shared_labels = [
        label
        for label in sorted(set(canonical_by_label) & set(live_by_label))
        if canonical_by_label[label]["normalized"] != live_by_label[label]["normalized"]
    ]

    return {
        "canonical_sections": canonical_sections,
        "live_sections": live_sections,
        "canonical_only": canonical_only,
        "live_only": live_only,
        "canonical_only_labels": [section["label"] for section in canonical_only],
        "live_only_labels": [section["label"] for section in live_only],
        "changed_shared_labels": changed_shared_labels,
        "shared_labels": sorted(set(canonical_by_label) & set(live_by_label)),
    }



def build_merge_guidance(section_comparison: Dict[str, object], has_base: bool) -> Dict[str, object]:
    canonical_missing_sections = section_comparison["canonical_only_labels"]
    live_only_sections = section_comparison["live_only_labels"]
    changed_shared_sections = section_comparison["changed_shared_labels"]

    if changed_shared_sections or (canonical_missing_sections and live_only_sections):
        strategy = "manual-merge-preserve-both"
        summary = "Both canonical and live sides contain unique or changed sections; preserve both and merge manually."
    elif canonical_missing_sections:
        strategy = "apply-canonical-missing-sections"
        summary = "Live file mostly matches but is missing canonical sections; rehydrate those sections in canonical order after backup."
    elif live_only_sections:
        strategy = "preserve-live-extra-sections"
        summary = "Live file contains extra local sections; keep the live file unchanged and only record managed state when safe."
    else:
        strategy = "manual-line-review"
        summary = "Line-level drift exists without clean section boundaries; inspect unified diff manually."

    if has_base:
        summary += " A managed-state hash record is available for historical reference."
    else:
        summary += " No prior managed-state hash record was recorded yet."

    return {
        "strategy": strategy,
        "summary": summary,
        "canonical_missing_sections": canonical_missing_sections,
        "live_only_sections": live_only_sections,
        "changed_shared_sections": changed_shared_sections,
        "base_available": has_base,
    }



def analyze_text_diff(canonical_text: str, live_text: str, base_text: Optional[str] = None) -> Dict[str, object]:
    section_comparison = compare_document_sections(canonical_text, live_text)
    import difflib
    diff_lines = list(
        difflib.unified_diff(
            canonical_text.splitlines(),
            live_text.splitlines(),
            fromfile="canonical",
            tofile="live",
            lineterm="",
            n=3,
        )
    )
    diff_excerpt = "\n".join(diff_lines[:160]) if diff_lines else ""
    similarity_ratio = round(difflib.SequenceMatcher(None, canonical_text, live_text).ratio(), 4)

    base_summary: Optional[Dict[str, object]] = None
    if base_text is not None:
        base_summary = {
            "canonical_changed_since_base": _normalize_text_block(base_text) != _normalize_text_block(canonical_text),
            "live_changed_since_base": _normalize_text_block(base_text) != _normalize_text_block(live_text),
        }

    return {
        "line_counts": {
            "canonical": len(canonical_text.splitlines()),
            "live": len(live_text.splitlines()),
            "base": len(base_text.splitlines()) if base_text is not None else None,
        },
        "similarity_ratio": similarity_ratio,
        "section_comparison": section_comparison,
        "merge_guidance": build_merge_guidance(section_comparison, has_base=base_text is not None),
        "unified_diff_excerpt": diff_excerpt,
        "base_summary": base_summary,
    }



def render_merge_candidate_text(canonical_text: str, live_text: str, strategy: str) -> str:
    if strategy == "apply-canonical-missing-sections":
        canonical_sections = split_document_sections(canonical_text)
        live_sections = split_document_sections(live_text)
        live_by_normalized = {section["normalized"]: section for section in live_sections}
        merged_sections = []
        for section in canonical_sections:
            merged_sections.append(live_by_normalized.get(section["normalized"], section)["content"])
        separator = "\n§\n" if "§" in canonical_text or "§" in live_text else "\n\n"
        merged_text = separator.join(part.strip() for part in merged_sections if part.strip())
        return merged_text + ("\n" if merged_text else "")

    if strategy == "preserve-live-extra-sections":
        return live_text if live_text.endswith("\n") or not live_text else live_text + "\n"

    raise ValueError(f"Unsupported merge strategy for automatic candidate rendering: {strategy}")



def execute_merge_apply_entry(entry: Dict[str, object], backup_root: Path, state_path: Path = MANAGED_STATE_PATH) -> Dict[str, object]:
    target = entry["target"]
    strategy = entry["analysis"]["merge_guidance"]["strategy"]
    live_path = Path(entry["live_path"])
    canonical_path = Path(entry["canonical_path"])

    result = {
        "target": target,
        "merge_strategy": strategy,
        "executed": False,
        "status": "skipped",
        "details": "",
    }

    if entry.get("state") != "managed-but-drifted":
        result["details"] = "Phase 5 only considers managed-but-drifted targets for semi-automatic merge/apply."
        return result

    if strategy not in {"apply-canonical-missing-sections", "preserve-live-extra-sections"}:
        result["details"] = "Strategy still requires manual merge review."
        return result

    canonical_text = read_full_text(canonical_path)
    live_text = read_full_text(live_path)
    merged_text = render_merge_candidate_text(canonical_text, live_text, strategy)

    if _normalize_text_block(merged_text) == _normalize_text_block(live_text):
        record_managed_target(target, live_path, canonical_path, sha256_text(live_path), sha256_text(canonical_path), path=state_path)
        result.update({
            "executed": True,
            "status": "noop",
            "details": "Live file already satisfies the low-ambiguity merge rule; recorded managed state only.",
        })
        return result

    live_path.parent.mkdir(parents=True, exist_ok=True)
    backed_up = backup_target(live_path, backup_root)
    live_path.write_text(merged_text, encoding="utf-8")
    record_managed_target(target, live_path, canonical_path, sha256_text(live_path), sha256_text(canonical_path), path=state_path)
    result.update({
        "executed": True,
        "status": "applied",
        "details": f"Applied low-ambiguity merge to {live_path}. Backup: {backed_up or 'none'}",
    })
    return result



def classify_adapter(canonical: Path, live: Path, signatures: List[str]) -> Dict[str, object]:
    canonical_exists = canonical.is_file()
    live_exists = live.is_file()
    live_text = read_text(live)
    canonical_hash = sha256_text(canonical)
    live_hash = sha256_text(live)
    found_signatures = [s for s in signatures if s and s in live_text]

    if not live_exists:
        state = "missing"
    elif canonical_exists and canonical_hash == live_hash:
        state = "managed-and-matches"
    elif canonical_exists and found_signatures:
        state = "managed-but-drifted"
    elif live_exists and found_signatures:
        state = "present-but-unmanaged"
    elif live_exists:
        state = "unknown-version-layout"
    else:
        state = "missing"

    return {
        "canonical_path": str(canonical),
        "live_path": str(live),
        "canonical_exists": canonical_exists,
        "live_exists": live_exists,
        "canonical_hash": canonical_hash,
        "live_hash": live_hash,
        "state": state,
        "found_signatures": found_signatures,
    }


def detect_hermes() -> Dict[str, object]:
    home = HOME / ".hermes"
    return {
        "name": "hermes",
        "present": home.exists(),
        "home": str(home),
        "signals": {
            "config_yaml": (home / "config.yaml").is_file(),
            "memories_dir": (home / "memories").is_dir(),
            "skills_dir": (home / "skills").is_dir(),
        },
        "adapter": classify_adapter(
            ASSETS / "adapters" / "hermes" / "USER.md",
            home / "memories" / "USER.md",
            ["portable, cross-agent long-term memory", "AI asset system"],
        ),
        "adapter_memory": classify_adapter(
            ASSETS / "adapters" / "hermes" / "MEMORY.md",
            home / "memories" / "MEMORY.md",
            ["AI-Assets", "MemPalace"],
        ),
    }


def detect_claude() -> Dict[str, object]:
    home = HOME / ".claude"
    plugin_cache = home / "plugins" / "cache"
    cache_entries = []
    if plugin_cache.is_dir():
        for owner in sorted(plugin_cache.iterdir()):
            if owner.is_dir():
                for plugin in sorted(owner.iterdir()):
                    if plugin.is_dir():
                        versions = [p.name for p in sorted(plugin.iterdir()) if p.is_dir()]
                        cache_entries.append({"plugin": f"{owner.name}/{plugin.name}", "versions": versions[:5]})
    return {
        "name": "claude-code",
        "present": home.exists(),
        "home": str(home),
        "signals": {
            "claude_md": (home / "CLAUDE.md").is_file(),
            "settings_json": (home / "settings.json").is_file(),
            "skills_dir": (home / "skills").is_dir(),
            "plugins_dir": (home / "plugins").is_dir(),
        },
        "adapter": classify_adapter(
            ASSETS / "adapters" / "claude" / "CLAUDE.md",
            home / "CLAUDE.md",
            ["Always reply in Chinese", "AI-Assets/memory", "portable source"],
        ),
        "plugin_cache": cache_entries[:10],
    }


def detect_codex() -> Dict[str, object]:
    home = HOME / ".codex"
    hooks_path = home / "hooks.json"
    hooks_text = read_text(hooks_path, limit=20000)
    return {
        "name": "codex",
        "present": home.exists(),
        "home": str(home),
        "signals": {
            "agents_md": (home / "AGENTS.md").is_file(),
            "hooks_json": hooks_path.is_file(),
            "skills_dir": (home / "skills").is_dir(),
            "agents_dir": (home / "agents").is_dir(),
            "omx_signature_in_hooks": "codex-native-hook" in hooks_text,
            "mempalace_bridge_in_hooks": "omx-mempalace" in hooks_text or "mempalace" in hooks_text,
        },
        "adapter": classify_adapter(
            ASSETS / "adapters" / "codex" / "AGENTS.md",
            home / "AGENTS.md",
            ["oh-my-codex", "OMX", "codex-native-hook", "Portable AI Asset Contract"],
        ),
    }


def detect_mempalace() -> Dict[str, object]:
    exe = HOME / ".venvs" / "mempalace" / "bin" / "mempalace"
    bridge = HOME / ".mempalace-auto" / "bridge"
    corpus = bridge / "corpus-live"
    latest_count = len(list(corpus.glob("projects/*/latest-session.md"))) if corpus.is_dir() else 0
    return {
        "name": "mempalace",
        "present": exe.exists() or bridge.exists(),
        "signals": {
            "executable": exe.exists(),
            "bridge_dir": bridge.is_dir(),
            "corpus_live": corpus.is_dir(),
            "project_latest_snapshots": latest_count,
        },
        "paths": {
            "executable": str(exe),
            "bridge": str(bridge),
            "corpus_live": str(corpus),
        },
    }


def detect_bridge() -> Dict[str, object]:
    root = HOME / ".codex" / "hooks" / "omx-mempalace"
    config = root / "config.json"
    install = root / "install.py"
    bridge = root / "bridge.py"
    return {
        "name": "omx-mempalace-bridge",
        "present": root.exists(),
        "signals": {
            "bridge_py": bridge.is_file(),
            "install_py": install.is_file(),
            "config_json": config.is_file(),
        },
        "paths": {
            "root": str(root),
            "bridge_py": str(bridge),
            "install_py": str(install),
            "config_json": str(config),
        },
    }


def build_inspect_report() -> Dict[str, object]:
    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    tools = {
        "hermes": detect_hermes(),
        "claude-code": detect_claude(),
        "codex": detect_codex(),
        "mempalace": detect_mempalace(),
        "omx-mempalace-bridge": detect_bridge(),
    }
    return {
        "generated_at": generated_at,
        "mode": "inspect",
        "assets_root": str(ASSETS),
        "host_home": str(HOME),
        "tools": tools,
        "summary": {
            "present_tools": [name for name, data in tools.items() if data.get("present")],
            "missing_tools": [name for name, data in tools.items() if not data.get("present")],
        },
    }


def plan_action_for_adapter(adapter: Dict[str, object], label: str) -> Dict[str, object]:
    state = adapter["state"]
    live_path = adapter["live_path"]
    canonical_path = adapter["canonical_path"]
    if state == "missing":
        return {
            "target": label,
            "state": state,
            "recommended_action": "safe-install-canonical",
            "risk": "low",
            "reason": f"Live target is missing; canonical adapter exists at {canonical_path}.",
            "next_step": f"Back up parent directory if needed, then create {live_path} from canonical source.",
        }
    if state == "managed-and-matches":
        return {
            "target": label,
            "state": state,
            "recommended_action": "no-op",
            "risk": "low",
            "reason": "Live target already matches canonical adapter.",
            "next_step": "Leave unchanged.",
        }
    if state == "managed-but-drifted":
        return {
            "target": label,
            "state": state,
            "recommended_action": "review-diff-before-sync",
            "risk": "medium",
            "reason": "Live target appears related to canonical adapter but content differs.",
            "next_step": f"Generate a diff between {canonical_path} and {live_path}, create a local backup, then decide whether to merge or replace.",
        }
    if state == "present-but-unmanaged":
        return {
            "target": label,
            "state": state,
            "recommended_action": "backup-and-manual-review",
            "risk": "medium",
            "reason": "Live target has recognizable signatures but is not a clean canonical match.",
            "next_step": f"Back up {live_path}, inspect local customizations, then decide whether to adopt AI-Assets management.",
        }
    return {
        "target": label,
        "state": state,
        "recommended_action": "inspect-layout-manually",
        "risk": "high",
        "reason": "The layout or file content is not confidently recognizable.",
        "next_step": f"Inspect {live_path} manually and extend resolver rules before any overwrite.",
    }


def build_plan_report(inspect_report: Dict[str, object]) -> Dict[str, object]:
    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    tools = inspect_report["tools"]
    actions: List[Dict[str, object]] = []

    hermes = tools["hermes"]
    actions.append(plan_action_for_adapter(hermes["adapter"], "hermes-user-memory"))
    actions.append(plan_action_for_adapter(hermes["adapter_memory"], "hermes-agent-memory"))

    claude = tools["claude-code"]
    actions.append(plan_action_for_adapter(claude["adapter"], "claude-instructions"))

    codex = tools["codex"]
    actions.append(plan_action_for_adapter(codex["adapter"], "codex-instructions"))

    bridge = tools["omx-mempalace-bridge"]
    if bridge["present"]:
        actions.append({
            "target": "omx-mempalace-bridge",
            "state": "present",
            "recommended_action": "preserve-and-validate",
            "risk": "low",
            "reason": "Bridge runtime is present and inspect discovered expected files.",
            "next_step": "Keep current bridge wiring, and in later apply phases verify hooks.json before reinstalling.",
        })
    else:
        actions.append({
            "target": "omx-mempalace-bridge",
            "state": "missing",
            "recommended_action": "install-bridge-after-runtime-setup",
            "risk": "medium",
            "reason": "Bridge is absent; memory continuity between Codex/OMX and MemPalace would be incomplete.",
            "next_step": "Install runtimes first, then run the bridge installer from AI-Assets-managed source.",
        })

    mempalace = tools["mempalace"]
    if mempalace["present"]:
        actions.append({
            "target": "mempalace-project-summaries",
            "state": "present",
            "recommended_action": "refresh-canonical-memory",
            "risk": "low",
            "reason": "MemPalace corpus is available and can continue feeding canonical exports.",
            "next_step": "Run refresh-canonical-memory.sh periodically or after major work sessions.",
        })

    return {
        "generated_at": generated_at,
        "mode": "plan",
        "assets_root": inspect_report["assets_root"],
        "host_home": inspect_report["host_home"],
        "based_on_inspect_generated_at": inspect_report["generated_at"],
        "actions": actions,
        "summary": {
            "safe_now": [a["target"] for a in actions if a["recommended_action"] in SAFE_ACTIONS],
            "needs_review": [a["target"] for a in actions if a["recommended_action"] in {"review-diff-before-sync", "backup-and-manual-review"}],
            "high_risk": [a["target"] for a in actions if a["risk"] == "high"],
        },
    }



def adapter_target_map(inspect_report: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    tools = inspect_report["tools"]
    return {
        "hermes-user-memory": tools["hermes"]["adapter"],
        "hermes-agent-memory": tools["hermes"]["adapter_memory"],
        "claude-instructions": tools["claude-code"]["adapter"],
        "codex-instructions": tools["codex"]["adapter"],
    }



def build_diff_entry(target: str, adapter: Dict[str, object], plan_action: Dict[str, object], managed_state: Dict[str, object]) -> Dict[str, object]:
    canonical_path = Path(adapter["canonical_path"])
    live_path = Path(adapter["live_path"])
    canonical_text = read_text(canonical_path, limit=200000)
    live_text = read_text(live_path, limit=200000)

    recorded_base = managed_state.get("targets", {}).get(target)
    base_text: Optional[str] = None
    base_hash = None
    if recorded_base and recorded_base.get("live_hash") == adapter.get("canonical_hash"):
        base_text = canonical_text
        base_hash = recorded_base.get("live_hash")

    analysis = analyze_text_diff(canonical_text, live_text, base_text=base_text)

    return {
        "target": target,
        "state": plan_action["state"],
        "recommended_action": plan_action["recommended_action"],
        "risk": plan_action["risk"],
        "schema_metadata": build_target_schema_metadata(target, plan_action["state"], plan_action["recommended_action"]),
        "asset_classification": {
            "canonical": classify_asset_path(str(canonical_path)),
            "live": classify_asset_path(str(live_path)),
        },
        "canonical_path": str(canonical_path),
        "live_path": str(live_path),
        "canonical_hash": adapter.get("canonical_hash"),
        "live_hash": adapter.get("live_hash"),
        "found_signatures": adapter.get("found_signatures", []),
        "base": {
            "available": base_text is not None,
            "hash": base_hash,
            "record": recorded_base,
        },
        "analysis": analysis,
        "next_step": plan_action["next_step"],
    }



def build_diff_report(inspect_report: Dict[str, object], plan_report: Dict[str, object]) -> Dict[str, object]:
    managed_state = load_managed_state()
    adapters = adapter_target_map(inspect_report)
    entries: List[Dict[str, object]] = []

    for action in plan_report["actions"]:
        target = action["target"]
        if action["recommended_action"] not in REVIEW_ACTIONS:
            continue
        adapter = adapters.get(target)
        if not adapter:
            continue
        entries.append(build_diff_entry(target, adapter, action, managed_state))

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "diff",
        "assets_root": inspect_report["assets_root"],
        "host_home": inspect_report["host_home"],
        "based_on_inspect_generated_at": inspect_report["generated_at"],
        "based_on_plan_generated_at": plan_report["generated_at"],
        "managed_state_path": str(MANAGED_STATE_PATH),
        "entries": entries,
        "summary": {
            "review_targets": [entry["target"] for entry in entries],
            "manual_merge_required": [
                entry["target"]
                for entry in entries
                if entry["analysis"]["merge_guidance"]["strategy"] == "manual-merge-preserve-both"
            ],
            "canonical_patch_candidates": [
                entry["target"]
                for entry in entries
                if entry["analysis"]["merge_guidance"]["strategy"] == "apply-canonical-missing-sections"
            ],
            "preserve_local_candidates": [
                entry["target"]
                for entry in entries
                if entry["analysis"]["merge_guidance"]["strategy"] == "preserve-live-extra-sections"
            ],
        },
    }



def backup_target(path: Path, backup_root: Path) -> Optional[Path]:
    if not path.exists():
        return None
    relative = path.as_posix().lstrip("/")
    dest = backup_root / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return dest


def run_script(script: Path, extra_env: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    import subprocess

    env = os.environ.copy()
    if extra_env:
        env.update({key: value for key, value in extra_env.items() if value is not None})
    command = ["/bin/bash", str(script)] if script.suffix == ".sh" else [str(script)]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=True, env=env, timeout=120)
        output = (completed.stdout or "") + (completed.stderr or "")
        return True, output.strip()
    except subprocess.TimeoutExpired as e:
        output = ((e.stdout or "") + (e.stderr or "")).strip()
        return False, output or "script timed out"
    except subprocess.CalledProcessError as e:
        output = ((e.stdout or "") + (e.stderr or "")).strip()
        return False, output



def load_report_json(prefix: str) -> Optional[Dict[str, object]]:
    path = REPORTS / f"latest-{prefix}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None



def execute_apply(plan_report: Dict[str, object]) -> Dict[str, object]:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUPS / f"apply-{stamp}"
    backup_root.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, object]] = []

    for action in plan_report["actions"]:
        target = action["target"]
        rec = action["recommended_action"]
        result = {
            "target": target,
            "recommended_action": rec,
            "executed": False,
            "status": "skipped",
            "details": "",
        }

        if rec == "safe-install-canonical":
            if target == "hermes-agent-memory":
                src = ASSETS / "adapters" / "hermes" / "MEMORY.md"
                dst = HOME / ".hermes" / "memories" / "MEMORY.md"
                dst.parent.mkdir(parents=True, exist_ok=True)
                backed_up = backup_target(dst, backup_root)
                shutil.copy2(src, dst)
                record_managed_target(target, dst, src, sha256_text(dst), sha256_text(src))
                result.update({
                    "executed": True,
                    "status": "applied",
                    "details": f"Copied canonical file to {dst}. Backup: {backed_up or 'none (target missing)'}",
                })
            else:
                result["details"] = "No executor implemented for this safe-install target yet."
        elif rec == "refresh-canonical-memory":
            script = ENGINE_ROOT / "bootstrap" / "setup" / "refresh-canonical-memory.sh"
            ok, output = run_script(script, extra_env={
                "PAA_ENGINE_ROOT": str(ENGINE_ROOT),
                "PAA_ASSET_ROOT": str(ASSETS),
                "PAA_CONFIG_PATH": CURRENT_RUNTIME_PATHS.get("config_path", ""),
            })
            result.update({
                "executed": True,
                "status": "applied" if ok else "failed",
                "details": output,
            })
        elif rec == "preserve-and-validate":
            if target == "omx-mempalace-bridge":
                hooks = HOME / ".codex" / "hooks.json"
                bridge_root = HOME / ".codex" / "hooks" / "omx-mempalace"
                ok = hooks.is_file() and bridge_root.is_dir()
                result.update({
                    "executed": True,
                    "status": "validated" if ok else "failed",
                    "details": f"hooks.json present={hooks.is_file()}, bridge_root present={bridge_root.is_dir()}",
                })
            else:
                result["details"] = "No validator implemented for this target yet."
        elif rec == "no-op":
            adapter = adapter_target_map(build_inspect_report()).get(target)
            if adapter:
                record_managed_target(
                    target,
                    Path(adapter["live_path"]),
                    Path(adapter["canonical_path"]),
                    adapter.get("live_hash"),
                    adapter.get("canonical_hash"),
                )
            result.update({
                "executed": True,
                "status": "noop",
                "details": "Target already matches canonical state.",
            })
        else:
            result["details"] = "Conservative apply mode skips review-required or unknown actions."

        results.append(result)

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "apply",
        "assets_root": str(ASSETS),
        "host_home": str(HOME),
        "based_on_plan_generated_at": plan_report["generated_at"],
        "backup_root": str(backup_root),
        "results": results,
        "summary": {
            "applied": [r["target"] for r in results if r["status"] in {"applied", "validated", "noop"}],
            "skipped": [r["target"] for r in results if r["status"] == "skipped"],
            "failed": [r["target"] for r in results if r["status"] == "failed"],
        },
    }



def execute_merge_apply(diff_report: Dict[str, object]) -> Dict[str, object]:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUPS / f"merge-apply-{stamp}"
    backup_root.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, object]] = []

    for entry in diff_report["entries"]:
        results.append(execute_merge_apply_entry(entry, backup_root))

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "merge-apply",
        "assets_root": diff_report["assets_root"],
        "host_home": diff_report["host_home"],
        "based_on_diff_generated_at": diff_report["generated_at"],
        "backup_root": str(backup_root),
        "results": results,
        "summary": {
            "applied": [r["target"] for r in results if r["status"] == "applied"],
            "noop": [r["target"] for r in results if r["status"] == "noop"],
            "skipped": [r["target"] for r in results if r["status"] == "skipped"],
            "failed": [r["target"] for r in results if r["status"] == "failed"],
        },
    }



def render_manual_merge_candidate_text(entry: Dict[str, object], canonical_text: str, live_text: str) -> str:
    analysis = entry["analysis"]
    guidance = analysis["merge_guidance"]
    comparison = analysis["section_comparison"]
    lines: List[str] = []
    lines.append(f"# Manual merge worksheet: {entry['target']}")
    lines.append("")
    lines.append(f"- state: {entry['state']}")
    lines.append(f"- recommended_action: {entry['recommended_action']}")
    lines.append(f"- merge_strategy: {guidance['strategy']}")
    lines.append(f"- canonical_path: `{entry['canonical_path']}`")
    lines.append(f"- live_path: `{entry['live_path']}`")
    lines.append("")
    lines.append("## Review guidance")
    lines.append("")
    lines.append(guidance["summary"])
    lines.append("")
    lines.append("## Manual merge worksheet")
    lines.append("")
    lines.append("Use this file as a review surface; do not overwrite live runtime files blindly.")
    lines.append("")
    if guidance["canonical_missing_sections"]:
        lines.append("### Canonical-only sections to consider re-introducing")
        lines.append("")
        for section in comparison["canonical_only"]:
            lines.append(f"#### {section['label']}")
            lines.append("")
            lines.append("```markdown")
            lines.append(section["content"])
            lines.append("```")
            lines.append("")
    if guidance["live_only_sections"]:
        lines.append("### Live-only sections to preserve or consciously replace")
        lines.append("")
        for section in comparison["live_only"]:
            lines.append(f"#### {section['label']}")
            lines.append("")
            lines.append("```markdown")
            lines.append(section["content"])
            lines.append("```")
            lines.append("")
    if guidance["changed_shared_sections"]:
        lines.append("### Shared sections with conflicting content")
        lines.append("")
        canonical_by_label = {section["label"]: section for section in comparison["canonical_sections"]}
        live_by_label = {section["label"]: section for section in comparison["live_sections"]}
        for label in guidance["changed_shared_sections"]:
            lines.append(f"#### {label}")
            lines.append("")
            lines.append("##### Canonical")
            lines.append("")
            lines.append("```markdown")
            lines.append(canonical_by_label[label]["content"])
            lines.append("```")
            lines.append("")
            lines.append("##### Live")
            lines.append("")
            lines.append("```markdown")
            lines.append(live_by_label[label]["content"])
            lines.append("```")
            lines.append("")
    lines.append("## Unified diff excerpt")
    lines.append("")
    lines.append("```diff")
    lines.append(analysis["unified_diff_excerpt"] or "(no textual diff excerpt generated)")
    lines.append("```")
    lines.append("")
    lines.append("## Source snapshots")
    lines.append("")
    lines.append("### Canonical snapshot")
    lines.append("")
    lines.append("```markdown")
    lines.append(canonical_text)
    lines.append("```")
    lines.append("")
    lines.append("### Live snapshot")
    lines.append("")
    lines.append("```markdown")
    lines.append(live_text)
    lines.append("```")
    lines.append("")
    return "\n".join(lines) + "\n"



def _fact_key(text: str) -> str:
    lowered = text.lower()
    if "grey's anatomy" in lowered or "grey’s anatomy" in lowered:
        return "greys-anatomy"
    if "harry potter" in lowered:
        return "harry-potter"
    if "canonical memory" in lowered or "sole source of truth" in lowered:
        return "canonical-memory-direction"
    if "portable" in lowered and "asset system" in lowered:
        return "portable-ai-assets"
    return _normalize_text_block(text)[:120]



def _prefer_live_over_canonical(live_text: str, canonical_text: str) -> str:
    if len(live_text) >= len(canonical_text):
        return live_text
    return canonical_text



def render_target_aware_hermes_draft(entry: Dict[str, object], canonical_text: str, live_text: str) -> str:
    canonical_sections = split_document_sections(canonical_text)
    live_sections = split_document_sections(live_text)
    merged_by_key: Dict[str, str] = {}
    order: List[str] = []

    for section in canonical_sections + live_sections:
        key = _fact_key(section["content"])
        chosen = merged_by_key.get(key)
        if chosen is None:
            merged_by_key[key] = section["content"]
            order.append(key)
        else:
            merged_by_key[key] = _prefer_live_over_canonical(section["content"], chosen)

    lines: List[str] = []
    lines.append(f"# Suggested merged draft: {entry['target']}")
    lines.append("")
    lines.append("<!-- Review carefully before using. This draft deduplicates overlapping memory facts and prefers the richer phrasing. -->")
    lines.append("")
    for idx, key in enumerate(order):
        content = merged_by_key[key]
        marker = "PRESERVED FROM LIVE" if content in {section['content'] for section in live_sections} else "INSERTED FROM CANONICAL"
        lines.append(f"<!-- {marker}: {key} -->")
        lines.append(content)
        if idx != len(order) - 1:
            lines.append("§")
    lines.append("")
    return "\n".join(lines)



def render_target_aware_instruction_draft(entry: Dict[str, object], canonical_text: str, live_text: str) -> str:
    comparison = entry["analysis"]["section_comparison"]
    canonical_by_label = {section["label"]: section for section in comparison["canonical_sections"]}
    live_by_label = {section["label"]: section for section in comparison["live_sections"]}
    lines: List[str] = []
    lines.append(f"# Suggested merged draft: {entry['target']}")
    lines.append("")
    lines.append("<!-- Review carefully before using. This draft preserves the current live instruction contract and appends portable AI-Assets guidance as an addendum. -->")
    lines.append("")
    lines.append(live_text.strip())
    lines.append("")
    lines.append("## Portable AI Assets Addendum")
    lines.append("")

    for section in comparison["canonical_sections"]:
        label = section["label"]
        if label in comparison["changed_shared_labels"]:
            lines.append(f"### Reconcile: {label}")
            lines.append("")
            lines.append("```markdown")
            lines.append(canonical_by_label[label]["content"])
            lines.append("```")
            lines.append("")
            if label in live_by_label:
                lines.append("```markdown")
                lines.append(live_by_label[label]["content"])
                lines.append("```")
                lines.append("")
        elif label in comparison["canonical_only_labels"]:
            lines.append(f"<!-- INSERTED FROM CANONICAL: {label} -->")
            lines.append(section["content"])
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"



def render_suggested_merge_draft_text(entry: Dict[str, object], canonical_text: str, live_text: str) -> str:
    target = entry.get("target", "")
    if target == "hermes-user-memory":
        return render_target_aware_hermes_draft(entry, canonical_text, live_text)
    if target in {"claude-instructions", "codex-instructions"}:
        return render_target_aware_instruction_draft(entry, canonical_text, live_text)

    comparison = entry["analysis"]["section_comparison"]
    canonical_by_label = {section["label"]: section for section in comparison["canonical_sections"]}
    live_by_label = {section["label"]: section for section in comparison["live_sections"]}
    used_live_labels = set()
    lines: List[str] = []
    lines.append(f"# Suggested merged draft: {entry['target']}")
    lines.append("")
    lines.append("<!-- Review carefully before using. This is a heuristic draft, not an applied result. -->")
    lines.append("")

    shared_labels = set(comparison["shared_labels"])
    changed_labels = set(comparison["changed_shared_labels"])
    canonical_only_labels = set(comparison["canonical_only_labels"])

    for section in comparison["canonical_sections"]:
        label = section["label"]
        if label in shared_labels and label not in changed_labels:
            live_section = live_by_label.get(label, section)
            lines.append(f"<!-- PRESERVED FROM LIVE: {label} -->")
            lines.append(live_section["content"])
            lines.append("")
            used_live_labels.add(label)
        elif label in changed_labels:
            lines.append(f"<!-- CONFLICT: {label} | prefer live below, canonical retained in comment -->")
            lines.append("<!-- CANONICAL VERSION")
            lines.append(canonical_by_label[label]["content"])
            lines.append("-->")
            if label in live_by_label:
                lines.append(f"<!-- PRESERVED FROM LIVE: {label} -->")
                lines.append(live_by_label[label]["content"])
                used_live_labels.add(label)
            else:
                lines.append(canonical_by_label[label]["content"])
            lines.append("")
        elif label in canonical_only_labels:
            lines.append(f"<!-- INSERTED FROM CANONICAL: {label} -->")
            lines.append(section["content"])
            lines.append("")
        else:
            lines.append(section["content"])
            lines.append("")

    for section in comparison["live_sections"]:
        label = section["label"]
        if label not in used_live_labels and label not in shared_labels:
            lines.append(f"<!-- PRESERVED FROM LIVE: {label} -->")
            lines.append(section["content"])
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"



def render_normalized_final_draft_text(target: str, suggested_text: str) -> str:
    text = re.sub(r"(?ms)^# Suggested merged draft: .*?\n\n", "", suggested_text)
    text = re.sub(r"(?m)^<!--.*?-->\s*\n?", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    if target == "hermes-user-memory":
        parts = [part.strip() for part in text.split("§") if part.strip()]
        text = "\n§\n".join(dict.fromkeys(parts)) + "\n"
    elif target in {"claude-instructions", "codex-instructions"}:
        text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    return text



def render_reviewed_merge_seed_text(target: str, normalized_text: str) -> str:
    text = normalized_text
    if target in {"claude-instructions", "codex-instructions"}:
        pattern = re.compile(r"### Reconcile: (?P<label>.+?)\n\n```markdown\n(?P<canonical>.*?)\n```\n\n```markdown\n(?P<live>.*?)\n```", re.S)

        def repl(match: re.Match[str]) -> str:
            live_block = match.group("live").strip()
            return live_block

        text = pattern.sub(repl, text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text



def write_manual_merge_candidate_bundle(entry: Dict[str, object], output_root: Path) -> Dict[str, str]:
    canonical_path = Path(entry["canonical_path"])
    live_path = Path(entry["live_path"])
    canonical_text = read_full_text(canonical_path)
    live_text = read_full_text(live_path)

    bundle_dir = output_root / safe_slug(entry["target"])
    bundle_dir.mkdir(parents=True, exist_ok=True)

    canonical_copy = bundle_dir / "canonical-source.md"
    live_copy = bundle_dir / "live-source.md"
    candidate_path = bundle_dir / "merge-candidate.md"
    review_instructions_path = bundle_dir / "REVIEW-INSTRUCTIONS.md"
    reviewed_merge_template_path = bundle_dir / "reviewed-merge.md.template"
    suggested_merge_draft_path = bundle_dir / "suggested-merge-draft.md"
    normalized_final_draft_path = bundle_dir / "normalized-final-draft.md"
    reviewed_merge_seed_path = bundle_dir / "reviewed-merge.seed.md"

    canonical_copy.write_text(canonical_text, encoding="utf-8")
    live_copy.write_text(live_text, encoding="utf-8")
    candidate_path.write_text(render_manual_merge_candidate_text(entry, canonical_text, live_text), encoding="utf-8")
    suggested_merge_draft = render_suggested_merge_draft_text(entry, canonical_text, live_text)
    suggested_merge_draft_path.write_text(suggested_merge_draft, encoding="utf-8")
    normalized_final_draft = render_normalized_final_draft_text(entry["target"], suggested_merge_draft)
    normalized_final_draft_path.write_text(normalized_final_draft, encoding="utf-8")
    reviewed_merge_seed_path.write_text(
        render_reviewed_merge_seed_text(entry["target"], normalized_final_draft),
        encoding="utf-8",
    )
    review_instructions_path.write_text(
        "# Review instructions\n\n"
        "1. Read merge-candidate.md and both source snapshot files.\n"
        "2. Create a new file named reviewed-merge.md in this directory.\n"
        "3. Put ONLY the final merged adapter content in reviewed-merge.md (no extra commentary).\n"
        "4. Then run bootstrap-ai-assets.sh --review-apply to back up and apply it.\n",
        encoding="utf-8",
    )
    reviewed_merge_template_path.write_text(
        "# Copy this file to reviewed-merge.md and replace the entire contents with the final merged adapter text.\n",
        encoding="utf-8",
    )

    return {
        "target": entry["target"],
        "bundle_dir": str(bundle_dir),
        "candidate_path": str(candidate_path),
        "canonical_copy_path": str(canonical_copy),
        "live_copy_path": str(live_copy),
        "review_instructions_path": str(review_instructions_path),
        "reviewed_merge_template_path": str(reviewed_merge_template_path),
        "suggested_merge_draft_path": str(suggested_merge_draft_path),
        "normalized_final_draft_path": str(normalized_final_draft_path),
        "reviewed_merge_seed_path": str(reviewed_merge_seed_path),
    }



def execute_review_apply_entry(
    entry: Dict[str, object],
    bundle_dir: Path,
    backup_root: Path,
    state_path: Path = MANAGED_STATE_PATH,
) -> Dict[str, object]:
    result = {
        "target": entry["target"],
        "executed": False,
        "status": "skipped",
        "details": "",
    }
    if entry.get("state") != "managed-but-drifted":
        result["details"] = "Review-apply only supports managed-but-drifted targets."
        return result

    reviewed_merge = bundle_dir / "reviewed-merge.md"
    if not reviewed_merge.is_file():
        result["details"] = "No reviewed-merge.md found in candidate bundle."
        return result

    live_path = Path(entry["live_path"])
    canonical_path = Path(entry["canonical_path"])
    merged_text = read_full_text(reviewed_merge)
    if not merged_text:
        result["details"] = "reviewed-merge.md is empty; refusing to apply."
        return result

    live_path.parent.mkdir(parents=True, exist_ok=True)
    backed_up = backup_target(live_path, backup_root)
    live_path.write_text(merged_text, encoding="utf-8")
    record_managed_target(
        entry["target"],
        live_path,
        canonical_path,
        sha256_text(live_path),
        entry.get("canonical_hash") or sha256_text(canonical_path),
        path=state_path,
    )
    result.update({
        "executed": True,
        "status": "applied",
        "details": f"Applied reviewed merge from {reviewed_merge}. Backup: {backed_up or 'none'}",
    })
    return result



def execute_review_apply(candidate_report: Dict[str, object]) -> Dict[str, object]:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUPS / f"review-apply-{stamp}"
    backup_root.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, object]] = []

    entry_by_target = {}
    diff_report = load_report_json("diff")
    if diff_report:
        entry_by_target = {entry["target"]: entry for entry in diff_report.get("entries", [])}

    for bundle in candidate_report.get("results", []):
        target = bundle["target"]
        entry = entry_by_target.get(target)
        if not entry:
            results.append({
                "target": target,
                "executed": False,
                "status": "skipped",
                "details": "No matching diff entry found in latest-diff.json.",
            })
            continue
        results.append(execute_review_apply_entry(entry, Path(bundle["bundle_dir"]), backup_root))

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "review-apply",
        "assets_root": candidate_report["assets_root"],
        "host_home": candidate_report["host_home"],
        "based_on_merge_candidates_generated_at": candidate_report["generated_at"],
        "backup_root": str(backup_root),
        "results": results,
        "summary": {
            "applied": [r["target"] for r in results if r["status"] == "applied"],
            "skipped": [r["target"] for r in results if r["status"] == "skipped"],
            "failed": [r["target"] for r in results if r["status"] == "failed"],
        },
    }



def generate_merge_candidates(diff_report: Dict[str, object]) -> Dict[str, object]:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    candidates_root = CANDIDATES / f"merge-candidates-{stamp}"
    candidates_root.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, str]] = []
    skipped: List[Dict[str, str]] = []

    for entry in diff_report["entries"]:
        strategy = entry["analysis"]["merge_guidance"]["strategy"]
        if strategy in {"manual-merge-preserve-both", "manual-line-review"}:
            results.append(write_manual_merge_candidate_bundle(entry, candidates_root))
        else:
            skipped.append({
                "target": entry["target"],
                "reason": f"Strategy {strategy} is low-ambiguity and does not need a manual merge worksheet.",
            })

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "merge-candidates",
        "assets_root": diff_report["assets_root"],
        "host_home": diff_report["host_home"],
        "based_on_diff_generated_at": diff_report["generated_at"],
        "candidates_root": str(candidates_root),
        "results": results,
        "skipped": skipped,
        "summary": {
            "generated_targets": [r["target"] for r in results],
            "skipped_targets": [r["target"] for r in skipped],
        },
    }



def markdown_for_inspect(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Bootstrap Inspect Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Present tools: {', '.join(report['summary']['present_tools']) or 'none'}")
    lines.append(f"- Missing tools: {', '.join(report['summary']['missing_tools']) or 'none'}")
    lines.append("")
    for name, data in report["tools"].items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- present: {data.get('present')}")
        if "home" in data:
            lines.append(f"- home: `{data['home']}`")
        if "paths" in data:
            for k, v in data["paths"].items():
                lines.append(f"- {k}: `{v}`")
        signals = data.get("signals", {})
        if signals:
            lines.append("- signals:")
            for k, v in signals.items():
                lines.append(f"  - {k}: {v}")
        for key in ("adapter", "adapter_memory"):
            adapter = data.get(key)
            if adapter:
                lines.append(f"- {key} state: {adapter['state']}")
                lines.append(f"  - live_path: `{adapter['live_path']}`")
                lines.append(f"  - canonical_path: `{adapter['canonical_path']}`")
                if adapter.get("found_signatures"):
                    lines.append(f"  - found_signatures: {', '.join(adapter['found_signatures'])}")
        plugin_cache = data.get("plugin_cache")
        if plugin_cache:
            lines.append("- plugin_cache sample:")
            for item in plugin_cache:
                lines.append(f"  - {item['plugin']}: {', '.join(item['versions'])}")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Phase 1 is inspect-only. No runtime files were modified.")
    lines.append("- Later phases should use this report to drive plan/apply logic.")
    return "\n".join(lines) + "\n"


def markdown_for_plan(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Bootstrap Plan Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Based on inspect report: {report['based_on_inspect_generated_at']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Safe now: {', '.join(report['summary']['safe_now']) or 'none'}")
    lines.append(f"- Needs review: {', '.join(report['summary']['needs_review']) or 'none'}")
    lines.append(f"- High risk: {', '.join(report['summary']['high_risk']) or 'none'}")
    lines.append("")
    lines.append("## Planned actions")
    lines.append("")
    for action in report["actions"]:
        lines.append(f"### {action['target']}")
        lines.append("")
        lines.append(f"- state: {action['state']}")
        lines.append(f"- recommended_action: {action['recommended_action']}")
        lines.append(f"- risk: {action['risk']}")
        lines.append(f"- reason: {action['reason']}")
        lines.append(f"- next_step: {action['next_step']}")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Phase 2 is plan-only. No runtime files were modified.")
    lines.append("- A future apply phase should always back up live targets before writing.")
    return "\n".join(lines) + "\n"


def markdown_for_apply(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Bootstrap Apply Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Based on plan report: {report['based_on_plan_generated_at']}")
    lines.append(f"Backup root: `{report['backup_root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Applied/validated: {', '.join(report['summary']['applied']) or 'none'}")
    lines.append(f"- Skipped: {', '.join(report['summary']['skipped']) or 'none'}")
    lines.append(f"- Failed: {', '.join(report['summary']['failed']) or 'none'}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    for result in report["results"]:
        lines.append(f"### {result['target']}")
        lines.append("")
        lines.append(f"- recommended_action: {result['recommended_action']}")
        lines.append(f"- status: {result['status']}")
        lines.append(f"- executed: {result['executed']}")
        lines.append(f"- details: {result['details']}")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Phase 3 is conservative apply. Only low-risk actions were executed.")
    lines.append("- Review-required targets remain untouched until a later diff/merge phase.")
    return "\n".join(lines) + "\n"



def markdown_for_diff(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Bootstrap Diff / Merge Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Based on inspect report: {report['based_on_inspect_generated_at']}")
    lines.append(f"Based on plan report: {report['based_on_plan_generated_at']}")
    lines.append(f"Managed state: `{report['managed_state_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Review targets: {', '.join(report['summary']['review_targets']) or 'none'}")
    lines.append(f"- Manual merge required: {', '.join(report['summary']['manual_merge_required']) or 'none'}")
    lines.append(f"- Canonical patch candidates: {', '.join(report['summary']['canonical_patch_candidates']) or 'none'}")
    lines.append(f"- Preserve-local candidates: {', '.join(report['summary']['preserve_local_candidates']) or 'none'}")
    lines.append("")
    lines.append("## Entries")
    lines.append("")
    for entry in report["entries"]:
        guidance = entry["analysis"]["merge_guidance"]
        comparison = entry["analysis"]["section_comparison"]
        lines.append(f"### {entry['target']}")
        lines.append("")
        lines.append(f"- state: {entry['state']}")
        lines.append(f"- recommended_action: {entry['recommended_action']}")
        lines.append(f"- risk: {entry['risk']}")
        lines.append(f"- portability: {entry['schema_metadata']['portability']}")
        lines.append(f"- apply_policy: {entry['schema_metadata']['apply_policy']}")
        lines.append(f"- canonical_asset_class: {entry['asset_classification']['canonical']['asset_class']}")
        lines.append(f"- live_asset_class: {entry['asset_classification']['live']['asset_class']}")
        lines.append(f"- similarity_ratio: {entry['analysis']['similarity_ratio']}")
        lines.append(f"- merge_strategy: {guidance['strategy']}")
        lines.append(f"- base_available: {guidance['base_available']}")
        lines.append(f"- canonical_path: `{entry['canonical_path']}`")
        lines.append(f"- live_path: `{entry['live_path']}`")
        if entry.get("found_signatures"):
            lines.append(f"- found_signatures: {', '.join(entry['found_signatures'])}")
        lines.append(f"- canonical_missing_sections: {', '.join(guidance['canonical_missing_sections']) or 'none'}")
        lines.append(f"- live_only_sections: {', '.join(guidance['live_only_sections']) or 'none'}")
        lines.append(f"- changed_shared_sections: {', '.join(guidance['changed_shared_sections']) or 'none'}")
        lines.append(f"- merge_summary: {guidance['summary']}")
        lines.append(f"- next_step: {entry['next_step']}")
        lines.append("")
        lines.append("#### Unified diff excerpt")
        lines.append("")
        lines.append("```diff")
        lines.append(entry["analysis"]["unified_diff_excerpt"] or "(no textual diff excerpt generated)")
        lines.append("```")
        lines.append("")
        lines.append("#### Section review")
        lines.append("")
        lines.append(f"- Shared labels: {', '.join(comparison['shared_labels']) or 'none'}")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Phase 4 does not overwrite drifted runtime files.")
    lines.append("- It generates merge guidance and diff context so later apply phases can stay conservative.")
    return "\n".join(lines) + "\n"



def markdown_for_merge_apply(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Bootstrap Merge-Apply Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Based on diff report: {report['based_on_diff_generated_at']}")
    lines.append(f"Backup root: `{report['backup_root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Applied: {', '.join(report['summary']['applied']) or 'none'}")
    lines.append(f"- No-op: {', '.join(report['summary']['noop']) or 'none'}")
    lines.append(f"- Skipped: {', '.join(report['summary']['skipped']) or 'none'}")
    lines.append(f"- Failed: {', '.join(report['summary']['failed']) or 'none'}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    for result in report["results"]:
        lines.append(f"### {result['target']}")
        lines.append("")
        lines.append(f"- merge_strategy: {result['merge_strategy']}")
        lines.append(f"- status: {result['status']}")
        lines.append(f"- executed: {result['executed']}")
        lines.append(f"- details: {result['details']}")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Phase 5 only auto-applies low-ambiguity merge strategies.")
    lines.append("- Manual-merge targets remain untouched.")
    return "\n".join(lines) + "\n"



def markdown_for_merge_candidates(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Bootstrap Merge Candidate Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Based on diff report: {report['based_on_diff_generated_at']}")
    lines.append(f"Candidates root: `{report['candidates_root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Generated targets: {', '.join(report['summary']['generated_targets']) or 'none'}")
    lines.append(f"- Skipped targets: {', '.join(report['summary']['skipped_targets']) or 'none'}")
    lines.append("")
    lines.append("## Generated bundles")
    lines.append("")
    for result in report["results"]:
        lines.append(f"### {result['target']}")
        lines.append("")
        lines.append(f"- bundle_dir: `{result['bundle_dir']}`")
        lines.append(f"- candidate_path: `{result['candidate_path']}`")
        lines.append(f"- canonical_copy_path: `{result['canonical_copy_path']}`")
        lines.append(f"- live_copy_path: `{result['live_copy_path']}`")
        lines.append(f"- review_instructions_path: `{result['review_instructions_path']}`")
        lines.append(f"- reviewed_merge_template_path: `{result['reviewed_merge_template_path']}`")
        lines.append(f"- suggested_merge_draft_path: `{result['suggested_merge_draft_path']}`")
        lines.append(f"- normalized_final_draft_path: `{result['normalized_final_draft_path']}`")
        lines.append(f"- reviewed_merge_seed_path: `{result['reviewed_merge_seed_path']}`")
        lines.append("")
    if report["skipped"]:
        lines.append("## Skipped")
        lines.append("")
        for skipped in report["skipped"]:
            lines.append(f"- {skipped['target']}: {skipped['reason']}")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Phase 6 generates reviewable merge worksheets for manual-merge targets.")
    lines.append("- These candidate files are for human review; they do not overwrite runtime files.")
    return "\n".join(lines) + "\n"



def markdown_for_review_apply(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Bootstrap Review-Apply Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Based on merge-candidates report: {report['based_on_merge_candidates_generated_at']}")
    lines.append(f"Backup root: `{report['backup_root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Applied: {', '.join(report['summary']['applied']) or 'none'}")
    lines.append(f"- Skipped: {', '.join(report['summary']['skipped']) or 'none'}")
    lines.append(f"- Failed: {', '.join(report['summary']['failed']) or 'none'}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    for result in report["results"]:
        lines.append(f"### {result['target']}")
        lines.append("")
        lines.append(f"- status: {result['status']}")
        lines.append(f"- executed: {result['executed']}")
        lines.append(f"- details: {result['details']}")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Phase 7 only applies reviewed-merge.md files created by human review.")
    lines.append("- Runtime files remain untouched when no reviewed merge exists.")
    return "\n".join(lines) + "\n"



def markdown_for_validate_schemas(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Schema Validation Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Schema dir: `{report['schema_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total manifests: {report['summary']['total']}")
    lines.append(f"- Valid: {report['summary']['valid']}")
    lines.append(f"- Invalid: {report['summary']['invalid']}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    for result in report["results"]:
        lines.append(f"### {result['path']}")
        lines.append("")
        lines.append(f"- schema: {result['schema']}")
        lines.append(f"- valid: {result['valid']}")
        lines.append(f"- errors: {', '.join(result['errors']) or 'none'}")
        lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_connectors(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Adapter Connector Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Schema dir: `{report['schema_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total adapters: {report['summary']['total_adapters']}")
    lines.append(f"- Valid adapters: {report['summary']['valid_adapters']}")
    lines.append(f"- Invalid adapters: {report['summary']['invalid_adapters']}")
    lines.append(f"- Runtimes: {', '.join(report['summary']['runtimes']) or 'none'}")
    lines.append(f"- Import connectors: {', '.join(report['summary']['import_connectors']) or 'none'}")
    lines.append(f"- Export connectors: {', '.join(report['summary']['export_connectors']) or 'none'}")
    lines.append("")
    lines.append("## Adapters")
    lines.append("")
    for adapter in report["adapters"]:
        lines.append(f"### {adapter['name']}")
        lines.append("")
        lines.append(f"- runtime: {adapter['runtime']}")
        lines.append(f"- path: `{adapter['path']}`")
        lines.append(f"- schema: {adapter['schema']}")
        lines.append(f"- valid: {adapter['valid']}")
        lines.append(f"- apply_policy: {adapter['apply_policy']}")
        lines.append(f"- asset_class: {adapter['asset_class']}")
        lines.append(f"- shareability: {adapter['shareability']}")
        lines.append(f"- canonical_sources: {', '.join(adapter['canonical_sources']) or 'none'}")
        lines.append(f"- live_targets: {', '.join(adapter['live_targets']) or 'none'}")
        connector = adapter.get("connector", {})
        lines.append(f"- connector.import: {connector.get('import', 'unknown')}")
        lines.append(f"- connector.export: {connector.get('export', 'unknown')}")
        lines.append(f"- errors: {', '.join(adapter['errors']) or 'none'}")
        lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_skills_inventory(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Portable Skills Inventory Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Schema dir: `{report['schema_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total skills: {report['summary']['total_skills']}")
    lines.append(f"- Valid skills: {report['summary']['valid_skills']}")
    lines.append(f"- Invalid skills: {report['summary']['invalid_skills']}")
    statuses = report['summary'].get('statuses', {})
    lines.append(f"- Statuses: {', '.join(f'{k}={v}' for k, v in statuses.items()) or 'none'}")
    lines.append(f"- Projection targets: {', '.join(report['summary'].get('projection_targets', [])) or 'none'}")
    lines.append("")
    lines.append("## Skills")
    lines.append("")
    for skill in report.get("skills", []):
        lines.append(f"### {skill['name']}")
        lines.append("")
        lines.append(f"- status: {skill['status']}")
        lines.append(f"- confidence: {skill['confidence']}")
        lines.append(f"- path: `{skill['path']}`")
        lines.append(f"- schema: {skill['schema']}")
        lines.append(f"- valid: {skill['valid']}")
        lines.append(f"- asset_class: {skill['asset_class']}")
        lines.append(f"- shareability: {skill['shareability']}")
        lines.append(f"- description: {skill.get('description') or 'none'}")
        lines.append(f"- trigger: {skill.get('trigger') or 'none'}")
        projection = skill.get("adapter_projection", {})
        if isinstance(projection, dict):
            lines.append(f"- adapter_projection: {', '.join(f'{k}->{v}' for k, v in projection.items()) or 'none'}")
        else:
            lines.append(f"- adapter_projection: {projection or 'none'}")
        lines.append(f"- errors: {', '.join(skill['errors']) or 'none'}")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_connector_preview(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Connector Preview Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Previewable adapters: {report['summary']['previewable_adapters']}")
    lines.append(f"- Runtimes: {', '.join(report['summary']['runtimes']) or 'none'}")
    lines.append("")
    lines.append("## Actions")
    lines.append("")
    for adapter in report["adapters"]:
        lines.append(f"### {adapter['name']}")
        lines.append("")
        for action in adapter.get("actions", []):
            lines.append(f"- {action['direction']}: {action['connector']} ({action['mode']})")
            lines.append(f"  - source: `{action['source']}`")
            lines.append(f"  - target: `{action['target']}`")
            lines.append(f"  - source_exists: {action['source_exists']}")
            lines.append(f"  - bytes_available: {action['bytes_available']}")
            lines.append(f"  - description: {action['description']}")
        lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_redacted_examples(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Redacted Examples Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- walkthrough_path: `{report['outputs']['walkthrough_path']}`")
    lines.append(f"- summary_path: `{report['outputs']['summary_path']}`")
    lines.append("")
    lines.append("These files are intended to be public-safe example artifacts.")
    return "\n".join(lines) + "\n"



def markdown_for_demo_story(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Demo Story Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- validated_manifests: {report['summary']['validated_manifests']}")
    lines.append(f"- adapter_runtimes: {', '.join(report['summary']['adapter_runtimes']) or 'none'}")
    lines.append(f"- previewable_adapters: {report['summary']['previewable_adapters']}")
    lines.append("")
    lines.append("## Output")
    lines.append("")
    lines.append(f"- story_path: `{report['story_path']}`")
    return "\n".join(lines) + "\n"



def markdown_for_public_demo_pack(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Demo Pack Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- files_in_pack: {report['summary']['files_in_pack']}")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- pack_dir: `{report['pack_dir']}`")
    lines.append(f"- index_path: `{report['index_path']}`")
    lines.append(f"- manifest_path: `{report['manifest_path']}`")
    return "\n".join(lines) + "\n"



def markdown_for_refresh_canonical_assets(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Canonical Refresh Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- total_steps: {report['summary']['total_steps']}")
    lines.append(f"- successful_steps: {report['summary']['successful_steps']}")
    lines.append(f"- failed_steps: {report['summary']['failed_steps']}")
    lines.append(f"- missing_steps: {report['summary']['missing_steps']}")
    lines.append("")
    lines.append("## Steps")
    lines.append("")
    for step in report["steps"]:
        lines.append(f"### {step['name']}")
        lines.append("")
        lines.append(f"- script: `{step['script']}`")
        lines.append(f"- status: {step['status']}")
        lines.append(f"- output: {step['output'] or 'none'}")
        lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_skill_projection_review_apply(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Skill Projection Review-Apply Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Backup root: `{report['backup_root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- applied: {report['summary']['applied']}")
    lines.append(f"- skipped: {report['summary']['skipped']}")
    lines.append(f"- failed: {report['summary']['failed']}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    if report.get("results"):
        for result in report["results"]:
            lines.append(f"- {result.get('status')}: `{result.get('source')}` -> `{result.get('target')}`")
            lines.append(f"  - details: {result.get('details')}")
            if result.get("backup_path"):
                lines.append(f"  - backup: `{result.get('backup_path')}`")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_skill_projection_status(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Skill Projection Status Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- bundles: {report['summary']['bundles']}")
    lines.append(f"- candidate_files: {report['summary']['candidate_files']}")
    lines.append(f"- reviewed_files: {report['summary']['reviewed_files']}")
    lines.append(f"- ready_to_apply: {report['summary']['ready_to_apply']}")
    lines.append("")
    lines.append("## Bundles")
    lines.append("")
    if report.get("bundles"):
        for bundle in report["bundles"]:
            lines.append(f"### {bundle['bundle_dir']}")
            lines.append("")
            lines.append(f"- candidate_files: {len(bundle.get('candidate_files', []))}")
            lines.append(f"- reviewed_files: {len(bundle.get('reviewed_files', []))}")
            lines.append(f"- ready_to_apply: {bundle.get('ready_to_apply', 0)}")
            for reviewed in bundle.get("reviewed_files", []):
                lines.append(f"  - reviewed: `{reviewed['path']}` target=`{reviewed.get('target')}` valid={reviewed['valid']}")
                if reviewed.get("errors"):
                    lines.append(f"    - errors: {', '.join(reviewed['errors'])}")
            lines.append("")
    else:
        lines.append("- none")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_skill_projection_candidates(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Skill Projection Candidates Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Schema dir: `{report['schema_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- preview_actions: {report['summary']['preview_actions']}")
    lines.append(f"- candidate_files: {report['summary']['candidate_files']}")
    lines.append(f"- bundle_dir: `{report.get('bundle_dir')}`")
    lines.append("")
    lines.append("## Candidates")
    lines.append("")
    if report.get("candidates"):
        for item in report["candidates"]:
            lines.append(f"- {item['skill']} -> {item['runtime']}: `{item['candidate_path']}`")
            lines.append(f"  - target: `{item['target']}`")
            lines.append(f"  - review_required: {item['review_required']}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_skill_projection_preview(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Skill Projection Preview Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Schema dir: `{report['schema_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- total_skills: {report['summary']['total_skills']}")
    lines.append(f"- projectable_skills: {report['summary']['projectable_skills']}")
    lines.append(f"- actions: {report['summary']['actions']}")
    lines.append(f"- projection_targets: {', '.join(report['summary']['projection_targets']) or 'none'}")
    lines.append("")
    lines.append("## Projection actions")
    lines.append("")
    if report.get("actions"):
        for action in report["actions"]:
            lines.append(f"### {action['skill']} -> {action['runtime']}")
            lines.append("")
            lines.append(f"- skill_path: `{action['skill_path']}`")
            lines.append(f"- target: `{action['target']}`")
            lines.append(f"- target_exists: {action['target_exists']}")
            lines.append(f"- mode: {action['mode']}")
            lines.append(f"- would_write: {action['would_write']}")
            lines.append(f"- description: {action['description']}")
            lines.append("- preview_text:")
            lines.append("")
            lines.append("```markdown")
            lines.append(action.get("preview_text", ""))
            lines.append("```")
            lines.append("")
    else:
        lines.append("- none")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_skill_candidates_status(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Skill Candidates Status Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Schema dir: `{report['schema_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- bundles: {report['summary']['bundles']}")
    lines.append(f"- candidate_files: {report['summary']['candidate_files']}")
    lines.append(f"- reviewed_files: {report['summary']['reviewed_files']}")
    lines.append(f"- ready_to_apply: {report['summary']['ready_to_apply']}")
    lines.append("")
    lines.append("## Bundles")
    lines.append("")
    if report.get("bundles"):
        for bundle in report["bundles"]:
            lines.append(f"### {bundle['bundle_dir']}")
            lines.append("")
            lines.append(f"- candidate_files: {len(bundle.get('candidate_files', []))}")
            lines.append(f"- reviewed_files: {len(bundle.get('reviewed_files', []))}")
            lines.append(f"- ready_to_apply: {bundle.get('ready_to_apply', 0)}")
            for reviewed in bundle.get("reviewed_files", []):
                lines.append(f"  - reviewed: `{reviewed['path']}` valid={reviewed['valid']} name={reviewed.get('name')}")
                if reviewed.get("errors"):
                    lines.append(f"    - errors: {', '.join(reviewed['errors'])}")
            lines.append("")
    else:
        lines.append("- none")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_skill_review_apply(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Skill Review-Apply Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Backup root: `{report['backup_root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- applied: {report['summary']['applied']}")
    lines.append(f"- skipped: {report['summary']['skipped']}")
    lines.append(f"- failed: {report['summary']['failed']}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    if report.get("results"):
        for result in report["results"]:
            lines.append(f"- {result.get('status')}: {result.get('name')} `{result.get('source')}` -> `{result.get('target')}`")
            lines.append(f"  - details: {result.get('details')}")
            if result.get("backup_path"):
                lines.append(f"  - backup: `{result.get('backup_path')}`")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_memos_skill_candidates(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets MemOS Skill Candidates Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    memos = report.get("memos", {})
    lines.append("## MemOS runtime")
    lines.append("")
    lines.append(f"- runtime_root: `{memos.get('runtime_root')}`")
    lines.append(f"- db: `{memos.get('db_path')}` exists={memos.get('db_exists')}")
    lines.append(f"- skills_table_columns: {', '.join(memos.get('skills_table_columns', [])) or 'none'}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- source_rows: {report['summary']['source_rows']}")
    lines.append(f"- generated_candidates: {report['summary']['generated_candidates']}")
    lines.append(f"- errors: {report['summary']['errors']}")
    lines.append(f"- bundle_dir: `{report.get('bundle_dir')}`")
    lines.append("")
    lines.append("## Candidates")
    lines.append("")
    if report.get("candidates"):
        for item in report["candidates"]:
            lines.append(f"- {item['name']}: `{item['candidate_path']}`")
            lines.append(f"  - source_row_id: {item['source_row_id']}")
            lines.append(f"  - review_required: {item['review_required']}")
    else:
        lines.append("- none")
    lines.append("")
    if report.get("errors"):
        lines.append("## Errors / blockers")
        lines.append("")
        for error in report["errors"]:
            lines.append(f"- {error}")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_memos_import_preview(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets MemOS Import Preview Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    memos = report["memos"]
    lines.append("## MemOS runtime")
    lines.append("")
    lines.append(f"- runtime_root: `{memos['runtime_root']}`")
    lines.append(f"- config: `{memos['config_path']}` exists={memos['config_exists']}")
    lines.append(f"- db: `{memos['db_path']}` exists={memos['db_exists']}")
    lines.append(f"- skills_dir: `{memos['skills_dir']}` exists={memos['skills_dir_exists']}")
    lines.append(f"- logs_dir: `{memos['logs_dir']}` exists={memos['logs_dir_exists']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- tables_detected: {report['summary']['tables_detected']}")
    lines.append(f"- known_tables_present: {report['summary']['known_tables_present']}")
    lines.append(f"- candidate_outputs: {report['summary']['candidate_outputs']}")
    lines.append(f"- errors: {report['summary']['errors']}")
    lines.append("")
    lines.append("## Known table counts")
    lines.append("")
    for table, count in report.get("table_counts", {}).items():
        latest = report.get("latest_values", {}).get(table)
        lines.append(f"- {table}: {count if count is not None else 'missing'}; latest={latest if latest is not None else 'unknown'}")
    lines.append("")
    lines.append("## Candidate canonical outputs")
    lines.append("")
    if report.get("candidate_outputs"):
        for item in report["candidate_outputs"]:
            lines.append(f"- {item['source']} -> `{item['candidate_path']}`")
            lines.append(f"  - review: {item['review']}")
    else:
        lines.append("- none")
    lines.append("")
    if report.get("errors"):
        lines.append("## Errors / blockers")
        lines.append("")
        for error in report["errors"]:
            lines.append(f"- {error}")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_memos_health(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets MemOS/Hermes Health Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- commands_checked: {report['summary']['commands_checked']}")
    lines.append(f"- healthy_commands: {report['summary']['healthy_commands']}")
    lines.append(f"- runtime_paths_present: {report['summary']['runtime_paths_present']}")
    lines.append(f"- blockers: {report['summary']['blockers']}")
    lines.append(f"- ready_for_test_profile_install: {report['summary']['ready_for_test_profile_install']}")
    lines.append("")
    lines.append("## Commands")
    lines.append("")
    for name, item in report.get("commands", {}).items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- path: `{item.get('path')}`")
        lines.append(f"- available: {item.get('available')}")
        lines.append(f"- ok: {item.get('ok')}")
        lines.append(f"- timed_out: {item.get('timed_out')}")
        lines.append(f"- output: {item.get('output') or 'none'}")
        lines.append("")
    lines.append("## Runtime paths")
    lines.append("")
    for name, item in report.get("paths", {}).items():
        lines.append(f"- {name}: `{item['path']}` exists={item['exists']} is_file={item['is_file']} is_dir={item['is_dir']}")
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if report.get("blockers"):
        for blocker in report["blockers"]:
            lines.append(f"- {blocker}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_private_assets_status(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Private Asset Status Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Configured asset repo remote: `{report.get('configured_asset_repo_remote') or 'none'}`")
    lines.append("")
    lines.append("## Git")
    lines.append("")
    git = report["git"]
    lines.append(f"- root_exists: {git['root_exists']}")
    lines.append(f"- is_git_repo: {git['is_git_repo']}")
    lines.append(f"- branch: {git['branch']}")
    lines.append(f"- has_remote: {git['has_remote']}")
    lines.append(f"- upstream_status: {git['upstream_status']}")
    lines.append(f"- dirty: {git['dirty']}")
    lines.append("")
    if git.get("remotes"):
        lines.append("### Remotes")
        lines.append("")
        for remote in git["remotes"]:
            lines.append(f"- {remote['name']}: `{remote['url']}`")
        lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- changed_files: {report['summary']['changed_files']}")
    categories = report['summary'].get('categories', {})
    if categories:
        for category, count in sorted(categories.items()):
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- categories: none")
    lines.append("")
    lines.append("## Changes")
    lines.append("")
    if report.get("changes"):
        for change in report["changes"]:
            lines.append(f"- `{change['status']}` `{change['path']}` ({change['category']})")
    else:
        lines.append("- none")
    lines.append("")
    if report.get("diff_stat"):
        lines.append("## Diff stat")
        lines.append("")
        lines.append("```text")
        lines.append(str(report["diff_stat"]))
        lines.append("```")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_init_private_assets(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Private Asset Repo Initialization Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append(f"Config path: `{report['config_path']}`")
    lines.append(f"Asset repo remote: `{report.get('asset_repo_remote') or 'none'}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- directories: {report['summary']['directories']}")
    lines.append(f"- created_directories: {report['summary']['created_directories']}")
    lines.append(f"- files: {report['summary']['files']}")
    lines.append(f"- created_files: {report['summary']['created_files']}")
    lines.append(f"- config_status: {report['summary']['config_status']}")
    lines.append(f"- git_status: {report['summary']['git_status']}")
    lines.append("")
    lines.append("## Config")
    lines.append("")
    lines.append(f"- status: {report['config']['status']}")
    if report['config'].get('backup_path'):
        lines.append(f"- backup_path: `{report['config']['backup_path']}`")
    lines.append("")
    lines.append("## Git")
    lines.append("")
    lines.append(f"- status: {report['git']['status']}")
    if report['git'].get('output'):
        lines.append(f"- output: {report['git']['output']}")
    lines.append("")
    lines.append("## Next steps")
    lines.append("")
    for step in report.get("next_steps", []):
        lines.append(f"- {step}")
    lines.append("")
    return "\n".join(lines) + "\n"



def markdown_for_public_repo_staging_status(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Repo Staging Status")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Staging dir: `{report['staging_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Staging exists: {report['summary']['staging_exists']}")
    lines.append(f"- Git initialized: {report['summary']['git_initialized']}")
    lines.append(f"- Branch: {report['summary']['branch']}")
    lines.append(f"- Remote configured: {report['summary']['remote_configured']}")
    lines.append(f"- Changed files: {report['summary']['changed_files']}")
    lines.append(f"- Forbidden findings: {report['summary']['forbidden_findings']}")
    lines.append(f"- Category counts: {report['summary']['category_counts']}")
    lines.append("")
    lines.append("## Git status --short")
    lines.append("")
    lines.append("```text")
    lines.append(report.get("git", {}).get("status_short") or "")
    lines.append("```")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_report_checks(report: Dict[str, object], title: str) -> str:
    lines: List[str] = []
    lines.append(f"# AI-Assets {title}")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    if report.get("staging_dir"):
        lines.append(f"Staging dir: `{report['staging_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in report.get("summary", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    if report.get("manual_history_context_steps"):
        lines.append("")
        lines.append("## Manual history context steps — not executed")
        lines.append("")
        for step in report.get("manual_history_context_steps", []):
            lines.append(f"### {step['step']}")
            lines.append("")
            lines.append("```bash")
            lines.append(step["command"])
            lines.append("```")
            lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_github_publish_dry_run(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets GitHub Publish Dry Run")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Staging dir: `{report['staging_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Warn: {report['summary']['warn']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append(f"- Commands: {report['summary']['commands']}")
    lines.append(f"- Executes anything: {report['summary']['executes_anything']}")
    lines.append("")
    lines.append("## Suggested commit")
    lines.append("")
    lines.append(f"`{report['suggested_commit_message']}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Command drafts — not executed")
    lines.append("")
    for command in report.get("commands", []):
        lines.append(f"### {command['step']}")
        lines.append("")
        lines.append("```bash")
        lines.append(command["command"])
        lines.append("```")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"






def markdown_for_github_handoff_pack(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets GitHub Handoff Pack")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Handoff dir: `{report['handoff_dir']}`")
    lines.append(f"Staging dir: `{report['staging_dir']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Warn: {report['summary']['warn']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append(f"- Included files: {report['summary']['included_files']}")
    lines.append(f"- Executes anything: {report['summary']['executes_anything']}")
    lines.append(f"- Forbidden findings: {report['summary']['forbidden_findings']}")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- HANDOFF.md: `{report['handoff_markdown']}`")
    lines.append(f"- HANDOFF.json: `{report['handoff_json']}`")
    lines.append(f"- Public archive: `{report.get('public_archive') or 'missing'}`")
    lines.append(f"- Archive SHA256: `{report.get('archive_sha256') or 'unknown'}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Included files")
    lines.append("")
    for rel in report.get("included_files", []):
        lines.append(f"- `{rel}`")
    lines.append("")
    lines.append("## Manual command drafts — not executed")
    lines.append("")
    for command in report.get("manual_steps", []):
        lines.append(f"### {command['step']}")
        lines.append("")
        lines.append("```bash")
        lines.append(command["command"])
        lines.append("```")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_github_final_preflight(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets GitHub Final Preflight")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Warn: {report['summary']['warn']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append(f"- Executes anything: {report['summary']['executes_anything']}")
    lines.append(f"- Command drafts: {report['summary']['command_drafts']}")
    lines.append(f"- Remote configured: {report['summary']['remote_configured']}")
    lines.append(f"- Forbidden findings: {report['summary']['forbidden_findings']}")
    lines.append("")
    lines.append("## Paths")
    lines.append("")
    for key, value in report.get("paths", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Artifact checksum")
    lines.append("")
    artifact = report.get("artifact_sha256", {})
    lines.append(f"- recorded: `{artifact.get('recorded') or 'missing'}`")
    lines.append(f"- computed: `{artifact.get('computed') or 'missing'}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Command drafts — not executed")
    lines.append("")
    for command in report.get("command_drafts", []):
        lines.append(f"### {command['step']}")
        lines.append("")
        lines.append("```bash")
        lines.append(command["command"])
        lines.append("```")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"




def markdown_for_release_provenance(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Release Provenance Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Provenance JSON: `{report['provenance_json']}`")
    lines.append(f"Provenance Markdown: `{report['provenance_markdown']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Warn: {report['summary']['warn']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append(f"- Executes anything: {report['summary']['executes_anything']}")
    lines.append(f"- Forbidden findings: {report['summary']['forbidden_findings']}")
    lines.append("")
    lines.append("## Subject")
    lines.append("")
    subject = report.get("subject", {})
    lines.append(f"- Archive: `{subject.get('archive_path') or 'missing'}`")
    lines.append(f"- Archive SHA256: `{subject.get('archive_sha256') or 'missing'}`")
    lines.append(f"- Recorded SHA256: `{subject.get('recorded_archive_sha256') or 'missing'}`")
    lines.append("")
    lines.append("## Tree digests")
    lines.append("")
    for name, tree in report.get("tree_digests", {}).items():
        lines.append(f"- {name}: exists={tree.get('exists')} files={tree.get('file_count')} sha256=`{tree.get('sha256') or 'missing'}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"




def markdown_for_verify_release_provenance(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Verify Release Provenance")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Provenance path: `{report.get('provenance_path') or 'missing'}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append(f"- Executes anything: {report['summary']['executes_anything']}")
    lines.append(f"- Forbidden findings: {report['summary']['forbidden_findings']}")
    lines.append("")
    lines.append("## Subject")
    lines.append("")
    subject = report.get("subject", {})
    for key in ["archive_path", "checksum_path", "computed_archive_sha256", "provenance_archive_sha256", "report_archive_sha256"]:
        lines.append(f"- {key}: `{subject.get(key) or 'missing'}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Tree verification")
    lines.append("")
    for name, result in report.get("tree_results", {}).items():
        current = result.get("current", {})
        recorded = result.get("recorded", {})
        lines.append(f"### {name}")
        lines.append(f"- sha256_match: {result.get('sha256_match')}")
        lines.append(f"- file_count_match: {result.get('file_count_match')}")
        lines.append(f"- current: files={current.get('file_count')} sha256=`{current.get('sha256') or 'missing'}`")
        lines.append(f"- recorded: files={recorded.get('file_count')} sha256=`{recorded.get('sha256') or 'missing'}`")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"




def markdown_for_release_closure(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Release Closure")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only closure gate for manual release review. It does not publish, push, create remotes, or execute command drafts.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "missing", "required_evidence", "executes_anything", "remote_configured", "command_drafts", "forbidden_findings"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Required evidence")
    lines.append("")
    for prefix in report.get("required_evidence", []):
        source = report.get("source_summaries", {}).get(prefix, {})
        lines.append(f"- `{prefix}`: `{source}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Manual review boundary")
    lines.append("")
    for item in report.get("manual_review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Provenance boundary")
    lines.append("")
    for item in report.get("provenance_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Publication command summary")
    lines.append("")
    publication_summary = report.get("publication_command_summary", {})
    lines.append(f"- total: {publication_summary.get('total', 0)}")
    lines.append(f"- non_executing: {publication_summary.get('non_executing', 0)}")
    lines.append(f"- manual_review_required: {publication_summary.get('manual_review_required', 0)}")
    lines.append("- by_publication_risk:")
    for risk, count in sorted((publication_summary.get("by_publication_risk") or {}).items()):
        lines.append(f"  - {risk}: {count}")
    lines.append("")
    lines.append("## Publication boundary")
    lines.append("")
    for item in report.get("publication_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Command drafts — not executed")
    lines.append("")
    for command in report.get("command_drafts", []):
        lines.append(f"### {command.get('step') or command.get('name') or 'command'}")
        lines.append("")
        lines.append(f"- executes: {command.get('executes')}")
        lines.append("")
        if command.get("command"):
            lines.append("```bash")
            lines.append(str(command.get("command")))
            lines.append("```")
            lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_public_package_freshness_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Package Freshness Review")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only freshness review for local public release package and GitHub staging artifacts. It does not publish, push, create remotes, create repositories, create tags, create releases, call provider APIs, or validate credentials.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "forbidden_findings", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append(f"- pack_dir: `{report.get('pack_dir')}`")
    lines.append(f"- staging_dir: `{report.get('staging_dir')}`")
    lines.append("")
    lines.append("## Required latest reports")
    lines.append("")
    for prefix in report.get("required_reports", []):
        source = report.get("source_summaries", {}).get(prefix, {})
        lines.append(f"- `{prefix}`: `{source}`")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_public_docs_external_reader_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Docs External-Reader Review")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only comprehension review for first-time external readers. It does not execute hooks/code/actions, publish, push, create remotes/repositories/tags/releases, call provider APIs, validate credentials, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "forbidden_findings", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Reader questions")
    lines.append("")
    for question in report.get("reader_questions", []):
        lines.append(f"- {question}")
    lines.append("")
    lines.append("## Documents")
    lines.append("")
    for name, path in (report.get("documents") or {}).items():
        lines.append(f"- `{name}`: `{path}`")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_release_candidate_closure_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Release Candidate Closure Review")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only final release-candidate handoff packet for human review. It does not publish, push, create remotes/repositories/tags/releases, call provider APIs, validate credentials, execute hooks/actions, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "final_review_packet_items"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Required evidence")
    lines.append("")
    for prefix in report.get("required_evidence", []):
        source = report.get("source_summaries", {}).get(prefix, {})
        lines.append(f"- `{prefix}`: `{source}`")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Final review packet")
    lines.append("")
    for item in report.get("final_review_packet", []):
        lines.append(f"- **{item.get('status')}** `{item.get('id')}` — {item.get('title')}")
        lines.append(f"  - evidence: `{item.get('evidence')}`")
        lines.append(f"  - review_type: {item.get('review_type')}; executes_anything: {item.get('executes_anything')}; auto_approves_release: {item.get('auto_approves_release')}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_release_reviewer_packet_index(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Release Reviewer Packet Index")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only table of contents for human release reviewers. It does not publish, push, commit, create remotes/repositories/tags/releases, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "packet_items", "public_doc_items", "auto_approves_release"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Packet index")
    lines.append("")
    for item in report.get("packet_index", []):
        exists = "present" if item.get("exists") else "missing"
        lines.append(f"- **{exists}** `{item.get('id')}` — {item.get('title')}")
        lines.append(f"  - report_prefix: `{item.get('report_prefix')}`; status: `{item.get('status')}`")
        lines.append(f"  - markdown: `{item.get('markdown_path')}`")
        lines.append(f"  - json: `{item.get('json_path')}`")
        lines.append(f"  - reviewer_note: {item.get('reviewer_note')}")
        lines.append(f"  - executes_anything: {item.get('executes_anything')}; remote_mutation_allowed: {item.get('remote_mutation_allowed')}; credential_validation_allowed: {item.get('credential_validation_allowed')}")
    lines.append("")
    lines.append("## Public docs")
    lines.append("")
    for item in report.get("public_docs", []):
        exists = "present" if item.get("exists") else "missing"
        lines.append(f"- **{exists}** `{item.get('path')}` — {item.get('reviewer_note')}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_release_reviewer_decision_log(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Release Reviewer Decision Log")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only local template/status artifact for human release review notes. It does not approve releases, publish, push, commit, create remotes/repositories/tags/releases, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "decision_recorded", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "decision_log_items", "auto_approves_release"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Decision log template")
    lines.append("")
    for item in report.get("decision_log_template", []):
        lines.append(f"- **{item.get('status')}** `{item.get('id')}` — {item.get('title')}")
        lines.append(f"  - prompt: {item.get('prompt')}")
        lines.append(f"  - executes_anything: {item.get('executes_anything')}")
    lines.append("")
    lines.append("## Source summaries")
    lines.append("")
    for prefix, summary in (report.get("source_summaries") or {}).items():
        lines.append(f"- `{prefix}`: `{summary}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_external_reviewer_quickstart(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reviewer Quickstart")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only local first-10-minutes path for external human reviewers. It does not approve releases, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "quickstart_items", "auto_approves_release"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## First 10 minutes path")
    lines.append("")
    for item in report.get("quickstart_path", []):
        lines.append(f"- **{'present' if item.get('exists') else 'missing'}** `{item.get('id')}` — {item.get('title')}")
        lines.append(f"  - path: `{item.get('path')}`")
        lines.append(f"  - why: {item.get('why')}")
        lines.append(f"  - executes_anything: {item.get('executes_anything')}")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Source summaries")
    lines.append("")
    for prefix, summary in (report.get("source_summaries") or {}).items():
        lines.append(f"- `{prefix}`: `{summary}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_external_reviewer_feedback_plan(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reviewer Feedback Plan")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only local capture/import plan for human reviewer notes. It does not approve releases, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, mutate issues/backlogs, execute hooks/actions/commands, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "decision_recorded", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "feedback_capture_items", "follow_up_drafts", "auto_approves_release"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Feedback capture template")
    lines.append("")
    for item in report.get("feedback_capture_template", []):
        lines.append(f"- `{item.get('id')}` — {item.get('title')}")
        lines.append(f"  - status: {item.get('status')}")
        lines.append(f"  - prompt: {item.get('prompt')}")
        lines.append(f"  - executes_anything: {item.get('executes_anything')}")
    lines.append("")
    lines.append("## Follow-up backlog drafts")
    lines.append("")
    for item in report.get("follow_up_backlog_drafts", []):
        lines.append(f"- `{item.get('id')}` — {item.get('title')}")
        lines.append(f"  - category: {item.get('category')}")
        lines.append(f"  - draft: {item.get('suggested_local_backlog_text')}")
        lines.append(f"  - executes: {item.get('executes')}")
        lines.append(f"  - mutates_issues: {item.get('mutates_issues')}")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Source summaries")
    lines.append("")
    for prefix, summary in (report.get("source_summaries") or {}).items():
        lines.append(f"- `{prefix}`: `{summary}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_external_reviewer_feedback_status(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reviewer Feedback Status")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only local checker for a human-filled external reviewer feedback file. It does not approve releases, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, mutate issues/backlogs, execute hooks/actions/commands, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "feedback_file_present", "decision_recorded", "approval_recorded", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "required_fields", "present_required_fields", "follow_up_items", "auto_approves_release"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    feedback_file = report.get("feedback_file") or {}
    lines.append("## Feedback file")
    lines.append("")
    lines.append(f"- path: `{feedback_file.get('path')}`")
    lines.append(f"- exists: {feedback_file.get('exists')}")
    lines.append("")
    lines.append("## Required feedback fields")
    lines.append("")
    for item in report.get("required_feedback_fields", []):
        lines.append(f"- **{item.get('status')}** `{item.get('id')}` — {item.get('description')}; executes_anything: {item.get('executes_anything')}")
    lines.append("")
    lines.append("## Follow-up review items")
    lines.append("")
    for item in report.get("follow_up_review_items", []):
        lines.append(f"- `{item.get('id')}` — {item.get('text')}")
        lines.append(f"  - status: {item.get('status')}; executes: {item.get('executes')}; mutates_issues: {item.get('mutates_issues')}")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Source summaries")
    lines.append("")
    for prefix, summary in (report.get("source_summaries") or {}).items():
        lines.append(f"- `{prefix}`: `{summary}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_external_reviewer_feedback_template(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reviewer Feedback Template")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a template-only/report-only generator for a human-fillable external reviewer feedback template. It does not approve releases, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, mutate issues/backlogs, execute hooks/actions/commands, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "template_written", "feedback_file_created", "writes_anything", "writes", "template_fields", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "auto_approves_release"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append(f"- template_file: `{(report.get('template_file') or {}).get('path')}` exists={(report.get('template_file') or {}).get('exists')}")
    lines.append(f"- final_feedback_file: `{(report.get('final_feedback_file') or {}).get('path')}` exists={(report.get('final_feedback_file') or {}).get('exists')}")
    lines.append("")
    lines.append("## Template fields")
    lines.append("")
    for item in report.get("template_fields", []):
        lines.append(f"- `{item.get('id')}` — {item.get('description')}; executes_anything: {item.get('executes_anything')}")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Source summaries")
    lines.append("")
    for prefix, summary in (report.get("source_summaries") or {}).items():
        lines.append(f"- `{prefix}`: `{summary}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_external_reviewer_feedback_followup_index(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reviewer Feedback Follow-up Index")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only local index for external reviewer feedback follow-up artifacts. It does not approve releases, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, mutate issues/backlogs, execute hooks/actions/commands, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "packet_items", "feedback_file_present", "decision_recorded", "approval_recorded", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "auto_approves_release"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Packet items")
    lines.append("")
    for item in report.get("packet_items", []):
        lines.append(f"- **{'present' if item.get('exists') else 'missing'}** `{item.get('id')}` — {item.get('title')}")
        lines.append(f"  - path: `{item.get('path')}`")
        lines.append(f"  - required: {item.get('required')}; executes_anything: {item.get('executes_anything')}")
        lines.append(f"  - why: {item.get('why')}")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Source summaries")
    lines.append("")
    for prefix, summary in (report.get("source_summaries") or {}).items():
        lines.append(f"- `{prefix}`: `{summary}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_external_reviewer_feedback_followup_candidates(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reviewer Feedback Follow-up Candidates")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a local-only/template-only/report-only candidate generator for human reviewer follow-up. It does not create remote issues, approve releases, publish, push, commit, create remotes/repositories/tags/releases, upload artifacts, call provider APIs, validate credentials, execute hooks/actions/commands, or mutate runtime/admin/provider state.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "manual_review_required", "feedback_file_present", "follow_up_items", "candidate_files_written", "remote_issues_created", "decision_recorded", "approval_recorded", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "auto_approves_release"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Candidate bundle")
    lines.append("")
    bundle = report.get("candidate_bundle") or {}
    lines.append(f"- path: `{bundle.get('path')}`")
    lines.append(f"- exists: {bundle.get('exists')}")
    lines.append("")
    lines.append("## Candidate files")
    lines.append("")
    for item in report.get("candidate_files", []):
        lines.append(f"- `{item.get('id')}` — `{item.get('path')}`")
        lines.append(f"  - status: {item.get('status')}; executes: {item.get('executes')}; mutates_issues: {item.get('mutates_issues')}")
        lines.append(f"  - source: {item.get('source_text')}")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Source summaries")
    lines.append("")
    for prefix, summary in (report.get("source_summaries") or {}).items():
        lines.append(f"- `{prefix}`: `{summary}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_external_reviewer_feedback_followup_candidate_status(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reviewer Feedback Follow-up Candidate Status")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in [
        "status",
        "checks",
        "pass",
        "fail",
        "manual_review_required",
        "candidate_bundle_present",
        "candidate_files_scanned",
        "human_reviewed_candidates",
        "unsafe_candidates",
        "remote_issues_created",
        "writes_anything",
        "executes_anything",
        "remote_mutation_allowed",
        "credential_validation_allowed",
        "remote_configured",
        "forbidden_findings",
        "auto_approves_release",
    ]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Candidate bundle")
    lines.append("")
    bundle = report.get("candidate_bundle", {}) if isinstance(report.get("candidate_bundle", {}), dict) else {}
    lines.append(f"- path: `{bundle.get('path', '')}`")
    lines.append(f"- exists: `{bundle.get('exists', False)}`")
    lines.append("")
    lines.append("## Candidate files")
    lines.append("")
    for candidate in report.get("candidate_files", []) or []:
        if not isinstance(candidate, dict):
            continue
        lines.append(f"- `{candidate.get('path')}` — status `{candidate.get('status')}`, human_reviewed `{candidate.get('human_reviewed')}`, executes `{candidate.get('executes')}`, mutates_issues `{candidate.get('mutates_issues')}`, auto_approves_release `{candidate.get('auto_approves_release')}`")
    if not report.get("candidate_files"):
        lines.append("- none")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []) or []:
        if not isinstance(check, dict):
            continue
        lines.append(f"- {check.get('status', 'unknown').upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)



def markdown_for_initial_completion_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Initial Completion / MVP Closure Review")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in [
        "status",
        "checks",
        "pass",
        "warn",
        "fail",
        "machine_readiness_ready",
        "human_feedback_complete",
        "human_action_required",
        "followup_candidates_ready",
        "writes_anything",
        "executes_anything",
        "remote_mutation_allowed",
        "credential_validation_allowed",
        "remote_configured",
        "auto_approves_release",
    ]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Human handoff required")
    lines.append("")
    for item in report.get("human_handoff_required", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_human_action_closure_checklist(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Human Action Closure Checklist")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "machine_readiness_ready", "human_feedback_complete", "human_feedback_pending", "manual_review_required", "followup_candidates_ready", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Human action checklist")
    lines.append("")
    for item in report.get("human_action_checklist", []) or []:
        if isinstance(item, dict):
            lines.append(f"- **{item.get('status')}** `{item.get('id')}` — {item.get('title')}")
            lines.append(f"  - evidence: `{item.get('evidence')}`")
            lines.append(f"  - review_type: {item.get('review_type')}; executes_anything: {item.get('executes_anything')}; auto_approves_release: {item.get('auto_approves_release')}")
    lines.append("")
    lines.append("## Human action required")
    lines.append("")
    for item in report.get("human_action_required", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_manual_reviewer_execution_packet(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Manual Reviewer Execution Packet")
    lines.append("")
    lines.append("This is a local-only/report-only one-page human runbook index. It does not execute commands, approve release, publish, upload, create remotes/repos/tags/releases, validate credentials, call APIs/providers, or mutate issues/backlogs.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "manual_review_required", "human_feedback_pending", "followup_candidates_ready", "one_page_runbook_ready", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Human runbook steps")
    lines.append("")
    for step in report.get("human_runbook_steps", []) or []:
        if isinstance(step, dict):
            lines.append(f"- **{step.get('status')}** `{step.get('id')}` — {step.get('title')}")
            lines.append(f"  - evidence: `{step.get('evidence')}`")
            lines.append(f"  - review_type: {step.get('review_type')}; executes_anything: {step.get('executes_anything')}; auto_approves_release: {step.get('auto_approves_release')}")
    lines.append("")
    lines.append("## Manual command sequence (not executed by this gate)")
    lines.append("")
    for command in report.get("manual_command_sequence", []) or []:
        lines.append(f"- `{command}`")
    lines.append("")
    lines.append("## Human-owned inputs")
    lines.append("")
    for item in report.get("human_owned_inputs", []) or []:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_manual_reviewer_public_surface_freshness(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Manual Reviewer Public Surface Freshness")
    lines.append("")
    lines.append("This is a local-only/report-only freshness and coverage check for the Phase 93 human runbook across public pack, GitHub staging, docs, and shell surfaces. It does not approve, publish, push, execute commands, call APIs/providers, validate credentials, create final human feedback, or mutate issues/backlogs.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "forbidden_findings", "manual_review_required", "human_feedback_pending", "followup_candidates_ready", "one_page_runbook_ready", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Required reports")
    lines.append("")
    for prefix in report.get("required_reports", []) or []:
        lines.append(f"- `{prefix}`")
    lines.append("")
    lines.append("## Public surfaces")
    lines.append("")
    lines.append(f"- public pack: `{report.get('pack_dir')}`")
    lines.append(f"- GitHub staging: `{report.get('staging_dir')}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)




def markdown_for_manual_reviewer_handoff_readiness(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Manual Reviewer Handoff Readiness")
    lines.append("")
    lines.append("This is a local-only/report-only handoff readiness digest for a human operator. It does not approve, share, invite, publish, push, execute commands, call APIs/providers, validate credentials, create final human feedback, or mutate issues/backlogs.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Handoff artifacts")
    lines.append("")
    for artifact in report.get("handoff_artifacts", []) or []:
        if isinstance(artifact, dict):
            lines.append(f"- `{artifact.get('name')}`: ready=`{artifact.get('ready')}` path=`{artifact.get('path')}`")
    lines.append("")
    lines.append("## Manual handoff sequence")
    lines.append("")
    for item in report.get("manual_handoff_sequence", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_manual_reviewer_handoff_packet_index(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Manual Reviewer Handoff Packet Index")
    lines.append("")
    lines.append("This is a local-only/report-only human handoff packet index/status. It cross-links local artifacts and human-only next actions; it does not share, invite, approve, publish, push, execute commands, call APIs/providers, validate credentials, create final human feedback, or mutate issues/backlogs.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Packet index")
    lines.append("")
    for item in report.get("packet_index", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('name')}`: ready=`{item.get('ready')}` role=`{item.get('review_role')}` path=`{item.get('path')}`")
    lines.append("")
    lines.append("## Human-only next actions")
    lines.append("")
    for item in report.get("human_only_next_actions", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('id')}`: automation_allowed=`{item.get('automation_allowed')}` requires_human=`{item.get('requires_human')}` — {item.get('title')}")
    lines.append("")
    lines.append("## Drift checks")
    lines.append("")
    for check in report.get("drift_checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_manual_reviewer_handoff_freeze_check(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Manual Reviewer Handoff Freeze Check")
    lines.append("")
    lines.append("This is a local-only/report-only freeze check for the human handoff packet. It verifies packet readiness and artifact presence; it does not share, invite, approve, publish, push, execute commands, call APIs/providers, validate credentials, create feedback, or mutate issues/backlogs.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Frozen packet entries")
    lines.append("")
    for item in report.get("frozen_packet_entries", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('name')}`: present=`{item.get('present')}` ready_in_packet_index=`{item.get('ready_in_packet_index')}` role=`{item.get('review_role')}` path=`{item.get('path')}`")
    lines.append("")
    lines.append("## Diagnostic freeze entries")
    lines.append("")
    for item in report.get("diagnostic_freeze_entries", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('name')}`: present=`{item.get('present')}` ready_in_packet_index=`{item.get('ready_in_packet_index')}` path_matches_expected=`{item.get('path_matches_expected')}` content_tokens_present=`{item.get('content_tokens_present')}` expected_path=`{item.get('expected_path')}`")
    lines.append("")
    lines.append("## Diagnostic freeze failures")
    lines.append("")
    failures = report.get("diagnostic_freeze_failures", []) or []
    if failures:
        for item in failures:
            if isinstance(item, dict):
                lines.append(f"- `{item.get('name')}`: reason=`{item.get('reason')}` path=`{item.get('path')}`")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Duplicate diagnostic entries")
    lines.append("")
    duplicates = report.get("duplicate_diagnostic_entries", []) or []
    lines.append("- " + (", ".join(str(item) for item in duplicates) if duplicates else "none"))
    lines.append("")
    lines.append("## Freeze checks")
    lines.append("")
    for check in report.get("freeze_checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Human-only next actions")
    lines.append("")
    for item in report.get("human_only_next_actions", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('id')}`: automation_allowed=`{item.get('automation_allowed')}` requires_human=`{item.get('requires_human')}`")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_agent_owner_delegation_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Agent Owner Delegation Review")
    lines.append("")
    lines.append("This is a local-only/report-only delegation review. It records that internal engineering/code review, verification, and product-material review are delegated to the agent, while real external sharing, invitations, publication, feedback authorship, and final go/no-go remain explicit external owner decisions.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "agent_engineering_review_delegated", "agent_code_review_delegated", "agent_verification_delegated", "agent_product_material_review_delegated", "requires_user_code_review", "external_owner_decision_required", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Delegated agent responsibilities")
    lines.append("")
    for item in report.get("delegated_agent_responsibilities", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('area')}`: owner=`{item.get('owner')}` requires_user_code_review=`{item.get('requires_user_code_review')}` — {item.get('description')}")
    lines.append("")
    lines.append("## Reserved external owner decisions")
    lines.append("")
    for item in report.get("reserved_owner_external_decisions", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('area')}`: reserved_for=`{item.get('reserved_for')}` automation_allowed=`{item.get('automation_allowed')}` — {item.get('description')}")
    lines.append("")
    lines.append("## Delegation checks")
    lines.append("")
    for check in report.get("delegation_checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_agent_complete_external_actions_reserved(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Agent-Complete / External-Actions-Reserved Rollup")
    lines.append("")
    lines.append("This is a local-only/report-only final rollup for the current handoff path. It records that machine-side and agent-side work is complete while real external actions remain explicit owner decisions.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "agent_side_complete", "machine_side_complete", "requires_user_code_review", "external_owner_decision_required", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Completed agent surfaces")
    lines.append("")
    for item in report.get("completed_agent_surfaces", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('area')}`: `{item.get('status')}`")
    lines.append("")
    lines.append("## Reserved external actions")
    lines.append("")
    for item in report.get("reserved_external_actions", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('area')}`: automation_allowed=`{item.get('automation_allowed')}` requires_explicit_owner_decision=`{item.get('requires_explicit_owner_decision')}`")
    lines.append("")
    lines.append("## Rollup checks")
    lines.append("")
    for check in report.get("rollup_checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_agent_complete_failclosed_hardening_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Agent-Complete Fail-Closed Hardening Review")
    lines.append("")
    lines.append("This is a local-only/report-only hardening review for the agent-complete rollup. It tracks fail-closed regression coverage and preserves the external-actions-reserved boundary.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "agent_side_complete", "machine_side_complete", "failclosed_regressions_covered", "requires_user_code_review", "external_owner_decision_required", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Fail-closed regression coverage")
    lines.append("")
    for item in report.get("failclosed_regression_coverage", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('scenario')}`: covered=`{item.get('covered')}` expected=`{item.get('expected')}`")
    lines.append("")
    lines.append("## Hardening checks")
    lines.append("")
    for check in report.get("hardening_checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_agent_complete_regression_evidence_integrity(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Agent-Complete Regression Evidence Integrity")
    lines.append("")
    lines.append("This is a local-only/report-only integrity audit for Phase 100 fail-closed regression evidence. It requires definition-backed test evidence and preserves the external-actions-reserved boundary.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "agent_side_complete", "machine_side_complete", "definition_backed_regressions_covered", "requires_user_code_review", "external_owner_decision_required", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Regression evidence")
    lines.append("")
    for item in report.get("regression_evidence", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('scenario')}`: covered=`{item.get('covered')}` evidence_kind=`{item.get('evidence_kind')}` test=`{item.get('test_name')}`")
    lines.append("")
    lines.append("## Integrity checks")
    lines.append("")
    for check in report.get("integrity_checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_agent_complete_syntax_invalid_evidence_failclosed_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Agent-Complete Syntax-Invalid Evidence Fail-Closed Review")
    lines.append("")
    lines.append("This is a local-only/report-only fail-closed review proving syntax-invalid regression evidence cannot satisfy definition-backed coverage or claim agent completion.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "agent_side_complete", "machine_side_complete", "syntax_invalid_evidence_blocks_completion", "requires_user_code_review", "external_owner_decision_required", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append(f"- syntax_invalid: `{report.get('syntax_invalid')}`")
    lines.append("")
    lines.append("## Syntax-invalid regression evidence")
    lines.append("")
    for item in report.get("syntax_invalid_regression_evidence", []) or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('scenario')}`: covered=`{item.get('covered')}` evidence_kind=`{item.get('evidence_kind')}` test=`{item.get('test_name')}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("syntax_invalid_checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_agent_complete_phase102_rollup_evidence_failclosed_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Agent-Complete Phase102 Rollup Evidence Fail-Closed Review")
    lines.append("")
    lines.append("This is a local-only/report-only fail-closed review proving downstream completed-work and agent-complete rollups require valid Phase102 report evidence before continuing.")
    lines.append("")
    summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "warn", "fail", "agent_side_complete", "machine_side_complete", "phase102_report_evidence_valid", "phase102_report_invalid_fields", "rollup_requires_phase102_report_evidence", "requires_user_code_review", "external_owner_decision_required", "manual_review_required", "human_feedback_pending", "shares_anything", "sends_invitations", "writes_anything", "writes", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "auto_approves_release", "remote_issues_created", "issue_backlog_mutation_allowed", "remote_configured"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Required evidence")
    lines.append("")
    for prefix in report.get("required_reports", []) or []:
        source = report.get("source_summaries", {}).get(prefix, {}) if isinstance(report.get("source_summaries", {}), dict) else {}
        lines.append(f"- `{prefix}`: `{source}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("phase102_rollup_checks", []) or []:
        if isinstance(check, dict):
            lines.append(f"- {str(check.get('status', 'unknown')).upper()}: {check.get('name')} — {check.get('detail', '')}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for item in report.get("review_boundary", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for item in report.get("recommendations", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def markdown_for_manual_release_reviewer_checklist(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Manual Release Reviewer Checklist")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")
    lines.append("This is a report-only checklist for a human release reviewer. It does not publish, push, create remotes, validate credentials, call provider APIs, or execute command drafts.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in ["status", "checks", "pass", "fail", "checklist_items", "manual_review_required", "executes_anything", "remote_mutation_allowed", "credential_validation_allowed", "remote_configured", "forbidden_findings", "command_drafts"]:
        lines.append(f"- {key}: {report['summary'].get(key)}")
    lines.append("")
    lines.append("## Required evidence")
    lines.append("")
    for prefix in report.get("required_evidence", []):
        source = report.get("source_summaries", {}).get(prefix, {})
        lines.append(f"- `{prefix}`: `{source}`")
    lines.append("")
    lines.append("## Review boundary")
    lines.append("")
    for item in report.get("review_boundary", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Checklist")
    lines.append("")
    for item in report.get("checklist", []):
        lines.append(f"- **{item.get('status')}** `{item.get('id')}` — {item.get('title')}")
        lines.append(f"  - evidence: `{item.get('evidence')}`")
        lines.append(f"  - review_type: {item.get('review_type')}; executes_anything: {item.get('executes_anything')}; auto_approves_release: {item.get('auto_approves_release')}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    publication_summary = report.get("publication_command_summary", {})
    lines.append("## Publication command summary")
    lines.append("")
    lines.append(f"- total: {publication_summary.get('total', 0)}")
    lines.append(f"- non_executing: {publication_summary.get('non_executing', 0)}")
    lines.append(f"- manual_review_required: {publication_summary.get('manual_review_required', 0)}")
    lines.append("- by_publication_risk:")
    for risk, count in sorted((publication_summary.get("by_publication_risk") or {}).items()):
        lines.append(f"  - {risk}: {count}")
    lines.append("")
    lines.append("## Artifact checksum")
    lines.append("")
    checksum = report.get("artifact_checksum", {})
    for key in ["recorded_sha256", "computed_sha256", "matches"]:
        lines.append(f"- {key}: {checksum.get(key)}")
    lines.append("")
    lines.append("## Command drafts — not executed")
    lines.append("")
    for command in report.get("command_drafts", []):
        lines.append(f"### {command.get('step') or command.get('name') or 'command'}")
        lines.append("")
        lines.append(f"- executes: {command.get('executes')}")
        lines.append(f"- manual_review_required: {command.get('manual_review_required')}")
        lines.append("")
        if command.get("command"):
            lines.append("```bash")
            lines.append(str(command.get("command")))
            lines.append("```")
            lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_external_reference_inventory(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reference Inventory")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Strategy doc: `{report.get('strategy_doc')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Reference docs: {report['summary']['reference_docs']}")
    lines.append(f"- Systems: {', '.join(report['summary'].get('systems', [])) or 'none'}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Warn: {report['summary']['warn']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## References")
    lines.append("")
    for ref in report.get("references", []):
        lines.append(f"### {ref['title']}")
        lines.append(f"- system: `{ref['system']}`")
        lines.append(f"- path: `{ref['path']}`")
        lines.append(f"- mentions_memory: {ref['mentions_memory']}")
        lines.append(f"- mentions_bridge: {ref['mentions_bridge']}")
        lines.append(f"- mentions_runtime_boundary: {ref['mentions_runtime_boundary']}")
        lines.append(f"- adopted_keyword_hits: {', '.join(ref.get('adopted_keyword_hits', [])) or 'none'}")
        lines.append(f"- avoid_keyword_hits: {', '.join(ref.get('avoid_keyword_hits', [])) or 'none'}")
        lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"




def markdown_for_external_reference_backlog(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets External Reference Backlog")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Backlog path: `{report.get('backlog_path')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Items: {report['summary']['items']}")
    lines.append(f"- State counts: {report['summary']['state_counts']}")
    lines.append(f"- Priority counts: {report['summary']['priority_counts']}")
    lines.append(f"- High priority candidates: {report['summary']['high_priority_candidates']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Warn: {report['summary']['warn']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## High-priority candidates")
    lines.append("")
    for item in report.get("high_priority_candidates", []):
        lines.append(f"- `{item.get('id')}` — {item.get('system')} ({item.get('category')}): {item.get('why_review')}")
    lines.append("")
    radar = report.get("reference_intake_radar", {}) if isinstance(report.get("reference_intake_radar"), dict) else {}
    lines.append("## Reference intake radar")
    lines.append("")
    lines.append(f"- Status: {radar.get('status')}")
    lines.append(f"- Source: {radar.get('source')}")
    lines.append(f"- executes_anything: {radar.get('executes_anything')}")
    lines.append(f"- calls_external_services: {radar.get('calls_external_services')}")
    lines.append(f"- writes_runtime_state: {radar.get('writes_runtime_state')}")
    lines.append(f"- Public-safe boundary: {radar.get('public_safe_boundary')}")
    lines.append(f"- Non-execution boundary: {radar.get('non_execution_boundary')}")
    lines.append(f"- Adoption workflow: {radar.get('adoption_workflow')}")
    lines.append(f"- Next step: {radar.get('next_step')}")
    lines.append("")
    lines.append("### Recommended lanes")
    lines.append("")
    for lane in radar.get("recommended_lanes", []):
        lines.append(f"- **{lane.get('lane')}** — candidates: {', '.join(lane.get('candidate_systems', []))}; output: `{lane.get('expected_output')}`; boundary: {lane.get('adoption_boundary')}")
    lines.append("")
    lines.append("## Backlog items")
    lines.append("")
    for item in report.get("items", []):
        lines.append(f"- `{item.get('id')}` | {item.get('system')} | state={item.get('state')} | priority={item.get('priority')} | output={item.get('expected_output')}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_public_repo_staging(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Repo Staging Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Staging dir: `{report['staging_dir']}`")
    lines.append(f"Manifest: `{report['manifest_path']}`")
    lines.append(f"Checklist: `{report['checklist_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Files in staging: {report['summary']['files_in_staging']}")
    lines.append(f"- Skipped: {report['summary']['skipped']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Passed: {report['summary']['passed']}")
    lines.append(f"- Failed: {report['summary']['failed']}")
    lines.append(f"- Forbidden findings: {report['summary']['forbidden_findings']}")
    lines.append(f"- Git initialized: {report['summary']['git_initialized']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        status = "pass" if check.get("ok") else "fail"
        detail = str(check.get("detail", "")).strip().replace("\n", " ")[:300]
        lines.append(f"- **{status}** `{check['name']}`: {detail}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_github_publish_check(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets GitHub Publish Check")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Warn: {report['summary']['warn']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append("")
    lines.append("## Generated / verified materials")
    lines.append("")
    lines.append(f"- Written: {', '.join(report['materials'].get('written', [])) or 'none'}")
    lines.append(f"- Unchanged: {', '.join(report['materials'].get('unchanged', [])) or 'none'}")
    lines.append("")
    lines.append("## GitHub metadata draft")
    lines.append("")
    lines.append(f"- Description: {report['github']['description']}")
    lines.append(f"- Topics: {', '.join(report['github']['topics'])}")
    lines.append(f"- Release tag: {report['github']['release_tag']}")
    lines.append(f"- Release notes: `{report['github']['release_notes']}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_public_release_archive(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Release Archive Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Pack dir: `{report['pack_dir']}`")
    lines.append(f"Archive: `{report['archive_path']}`")
    lines.append(f"Checksum file: `{report['checksum_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- File count: {report['summary']['file_count']}")
    lines.append(f"- Archive size bytes: {report['summary']['archive_size_bytes']}")
    lines.append(f"- Archive sha256: `{report['summary']['archive_sha256']}`")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_public_release_smoke_test(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Release Smoke Test Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Archive: `{report.get('archive_path')}`")
    lines.append(f"Pack dir: `{report.get('pack_dir')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Passed: {report['summary']['passed']}")
    lines.append(f"- Failed: {report['summary']['failed']}")
    lines.append(f"- Forbidden findings: {report['summary']['forbidden_findings']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        status = "pass" if check.get("ok") else "fail"
        detail = str(check.get("detail", "")).strip().replace("\n", " ")[:300]
        lines.append(f"- **{status}** `{check['name']}`: {detail}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_public_release_pack(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Release Pack Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Pack dir: `{report['pack_dir']}`")
    lines.append(f"Manifest: `{report['manifest_path']}`")
    lines.append(f"Checksums: `{report['checksums_path']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Files in pack: {report['summary']['files_in_pack']}")
    lines.append(f"- Skipped: {report['summary']['skipped']}")
    lines.append(f"- Public safety status: {report['summary']['public_safety_status']}")
    lines.append(f"- Release readiness: {report['summary']['release_readiness']}")
    lines.append("")
    lines.append("## Included files")
    lines.append("")
    for path in report.get("files", []):
        lines.append(f"- `{path}`")
    if report.get("skipped"):
        lines.append("")
        lines.append("## Skipped")
        lines.append("")
        for item in report["skipped"]:
            lines.append(f"- `{item['path']}`: {item['reason']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_team_pack_preview(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Team Pack Preview")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    summary = report["summary"]
    lines.append(f"- Status: {summary['status']}")
    lines.append(f"- Manifests: {summary['manifests']}")
    lines.append(f"- Public-safe manifests: {summary['public_safe_manifests']}")
    lines.append(f"- Roles: {summary['roles']}")
    lines.append(f"- Layers: {summary['layers']}")
    lines.append(f"- Checks: {summary['checks']}")
    lines.append(f"- Pass: {summary['pass']}")
    lines.append(f"- Warn: {summary['warn']}")
    lines.append(f"- Fail: {summary['fail']}")
    lines.append("")
    lines.append("## Manifests")
    lines.append("")
    for item in report.get("manifests", []):
        lines.append(f"### {item['name']}")
        lines.append(f"- path: `{item['path']}`")
        lines.append(f"- version: {item.get('pack_version')}")
        lines.append(f"- asset_class: {item.get('asset_class')}")
        lines.append(f"- shareability: {item.get('shareability')}")
        lines.append(f"- apply_policy: {item.get('apply_policy')}")
        lines.append(f"- layers: {', '.join(item.get('layers', [])) or 'none'}")
        lines.append(f"- roles: {', '.join(item.get('roles', [])) or 'none'}")
        lines.append(f"- missing_references: {item.get('missing_references')}")
        lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_project_pack_preview(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Project Pack Preview")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append("")
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {summary['status']}")
    lines.append(f"- Manifests: {summary['manifests']}")
    lines.append(f"- Public-safe manifests: {summary['public_safe_manifests']}")
    lines.append(f"- Capabilities: {summary['capabilities']}")
    lines.append(f"- Risk class counts: {summary['risk_class_counts']}")
    lines.append(f"- Policy outcome counts: {summary['policy_outcome_counts']}")
    lines.append(f"- Executes anything: {summary['executes_anything']}")
    lines.append(f"- Checks: {summary['checks']}")
    lines.append(f"- Pass: {summary['pass']}")
    lines.append(f"- Warn: {summary['warn']}")
    lines.append(f"- Fail: {summary['fail']}")
    lines.append("")
    lines.append("## Manifests")
    lines.append("")
    for item in report.get("manifests", []):
        lines.append(f"### {item['name']}")
        lines.append(f"- path: `{item['path']}`")
        lines.append(f"- version: {item.get('pack_version')}")
        lines.append(f"- asset_class: {item.get('asset_class')}")
        lines.append(f"- shareability: {item.get('shareability')}")
        lines.append(f"- project_scope: {item.get('project_scope')}")
        lines.append(f"- visibility: {item.get('visibility')}")
        lines.append(f"- apply_policy: {item.get('apply_policy')}")
        lines.append(f"- capabilities: {len(item.get('capabilities', []))}")
        lines.append(f"- missing_references: {item.get('missing_references')}")
        lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_capability_risk_inventory(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Capability Risk Inventory")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append("")
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {summary['status']}")
    lines.append(f"- Capabilities: {summary['capabilities']}")
    lines.append(f"- Risk class counts: {summary['risk_class_counts']}")
    lines.append(f"- Policy outcome counts: {summary['policy_outcome_counts']}")
    lines.append(f"- Executes anything: {summary['executes_anything']}")
    lines.append(f"- Checks: {summary['checks']}")
    lines.append(f"- Pass: {summary['pass']}")
    lines.append(f"- Warn: {summary['warn']}")
    lines.append(f"- Fail: {summary['fail']}")
    lines.append("")
    lines.append("## Capabilities")
    lines.append("")
    for item in report.get("capabilities", []):
        lines.append(f"### {item.get('name')}")
        lines.append(f"- kind: {item.get('kind')}")
        lines.append(f"- source: `{item.get('source')}`")
        lines.append(f"- risk_classes: {', '.join(item.get('risk_classes', [])) or 'none'}")
        lines.append(f"- policy_outcome: {item.get('policy_outcome')}")
        lines.append(f"- apply_policy: {item.get('apply_policy')}")
        lines.append(f"- executes_anything: {item.get('executes_anything')}")
        lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_capability_policy_preview(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Capability Policy Preview")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append("")
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {summary['status']}")
    lines.append(f"- Baseline capabilities: {summary['baseline_capabilities']}")
    lines.append(f"- Current capabilities: {summary['current_capabilities']}")
    lines.append(f"- Added: {summary['added']}")
    lines.append(f"- Removed: {summary['removed']}")
    lines.append(f"- Changed: {summary['changed']}")
    lines.append(f"- Risk upgrades: {summary['risk_upgrades']}")
    lines.append(f"- Risk downgrades: {summary['risk_downgrades']}")
    lines.append(f"- Risk class counts: {summary['risk_class_counts']}")
    lines.append(f"- Policy outcome counts: {summary['policy_outcome_counts']}")
    lines.append(f"- Executes anything: {summary['executes_anything']}")
    lines.append("")
    lines.append("## Baseline paths")
    lines.append("")
    for path in report.get("baseline_paths", []):
        lines.append(f"- `{path}`")
    lines.append("")
    lines.append("## Delta summary")
    lines.append("")
    for key in ["added", "removed", "risk_upgrades", "risk_downgrades"]:
        lines.append(f"### {key}")
        values = report.get("deltas", {}).get(key, [])
        if values:
            for item in values:
                lines.append(f"- `{item.get('name')}`")
        else:
            lines.append("- none")
        lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_capability_policy_candidate_generation(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Capability Policy Candidate Generation")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Template path: `{report.get('template_path')}`")
    lines.append(f"Reviewed path: `{report.get('reviewed_path')}`")
    lines.append("")
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {summary['status']}")
    lines.append(f"- Templates written: {summary['templates_written']}")
    lines.append(f"- Reviewed baselines written: {summary['reviewed_baselines_written']}")
    lines.append(f"- Baseline capabilities: {summary['baseline_capabilities']}")
    lines.append(f"- Current capabilities: {summary['current_capabilities']}")
    lines.append(f"- Added: {summary['added']}")
    lines.append(f"- Removed: {summary['removed']}")
    lines.append(f"- Changed: {summary['changed']}")
    lines.append(f"- Risk upgrades: {summary['risk_upgrades']}")
    lines.append(f"- Risk downgrades: {summary['risk_downgrades']}")
    lines.append(f"- Risk class counts: {summary['risk_class_counts']}")
    lines.append(f"- Policy outcome counts: {summary['policy_outcome_counts']}")
    lines.append(f"- Executes anything: {summary['executes_anything']}")
    lines.append("")
    lines.append("## Delta summary")
    lines.append("")
    for key in ["added", "removed", "changed", "risk_upgrades", "risk_downgrades"]:
        lines.append(f"### {key}")
        values = report.get("deltas", {}).get(key, [])
        if values:
            for item in values:
                lines.append(f"- `{item.get('name')}`")
        else:
            lines.append("- none")
        lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Human review required")
    lines.append("")
    lines.append("Copy reviewed-baseline.yaml.template to reviewed-baseline.yaml only after human review; this command never creates the reviewed file or applies the baseline.")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_capability_policy_candidate_status(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Capability Policy Candidate Status")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Template path: `{report.get('template_path')}`")
    lines.append(f"Reviewed path: `{report.get('reviewed_path')}`")
    lines.append("")
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {summary['status']}")
    lines.append(f"- Apply readiness: {summary['apply_readiness']}")
    lines.append(f"- Ready for apply: {summary['ready_for_apply']}")
    lines.append(f"- Template exists: {summary['template_exists']}")
    lines.append(f"- Reviewed baseline exists: {summary['reviewed_baseline_exists']}")
    lines.append(f"- Reviewed baseline valid: {summary['reviewed_baseline_valid']}")
    lines.append(f"- Reviewed baseline in sync: {summary['reviewed_baseline_in_sync']}")
    lines.append(f"- Templates written: {summary['templates_written']}")
    lines.append(f"- Reviewed baselines written: {summary['reviewed_baselines_written']}")
    lines.append(f"- Added: {summary['added']}")
    lines.append(f"- Removed: {summary['removed']}")
    lines.append(f"- Changed: {summary['changed']}")
    lines.append(f"- Risk upgrades: {summary['risk_upgrades']}")
    lines.append(f"- Risk downgrades: {summary['risk_downgrades']}")
    lines.append(f"- Risk class counts: {summary['risk_class_counts']}")
    lines.append(f"- Policy outcome counts: {summary['policy_outcome_counts']}")
    lines.append(f"- Executes anything: {summary['executes_anything']}")
    lines.append("")
    lines.append("## Read-only review gate")
    lines.append("")
    lines.append("This status command does not apply baselines, does not create reviewed-baseline.yaml, and does not rewrite reviewed-baseline.yaml.template.")
    if summary.get("apply_readiness") == "needs-human-review":
        lines.append("The candidate needs human review before apply: copy reviewed-baseline.yaml.template to reviewed-baseline.yaml only after checking the capability policy delta.")
    lines.append("")
    lines.append("## Delta summary")
    lines.append("")
    for key in ["added", "removed", "changed", "risk_upgrades", "risk_downgrades"]:
        lines.append(f"### {key}")
        values = report.get("deltas", {}).get(key, [])
        if values:
            for item in values:
                lines.append(f"- `{item.get('name')}`")
        else:
            lines.append("- none")
        lines.append("")
    lines.append("## Reviewed sync delta")
    lines.append("")
    for key in ["added", "removed", "changed"]:
        values = report.get("reviewed_sync_delta", {}).get(key, [])
        lines.append(f"- {key}: {len(values)}")
    lines.append("")
    guidance = report.get("reviewer_guidance", {})
    if guidance:
        lines.append("## Reviewer guidance")
        lines.append("")
        lines.append(f"- Next action: {guidance.get('next_action')}")
        lines.append(f"- Guidance status: {guidance.get('status')}")
        lines.append(f"- Template: `{guidance.get('template_path')}`")
        lines.append(f"- Reviewed baseline: `{guidance.get('reviewed_path')}`")
        lines.append(f"- {guidance.get('safety_boundary')}")
        lines.append("")
        lines.append("### Checklist")
        lines.append("")
        for item in guidance.get("checklist", []):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("### Command drafts")
        lines.append("")
        lines.append("Command drafts are non-executing; copy/run manually only after human review.")
        for name, command in guidance.get("commands", {}).items():
            lines.append(f"- `{name}` executes={command.get('executes')}: `{command.get('command')}`")
        lines.append("")
    audit = report.get("review_handoff_audit", {})
    if audit:
        lines.append("## Review handoff audit")
        lines.append("")
        lines.append(f"- Status: {audit.get('status')}")
        lines.append(f"- Apply readiness: {audit.get('apply_readiness')}")
        lines.append(f"- Ready for apply: {audit.get('preflight', {}).get('ready_for_apply')}")
        lines.append(f"- Writes anything: {audit.get('writes_anything')}")
        lines.append(f"- Executes anything: {audit.get('executes_anything')}")
        evidence = audit.get("evidence", {})
        lines.append(f"- Template SHA256: `{evidence.get('template_sha256')}`")
        lines.append(f"- Reviewed baseline SHA256: `{evidence.get('reviewed_baseline_sha256')}`")
        lines.append(f"- Current baseline SHA256: `{evidence.get('current_baseline_sha256')}`")
        lines.append(f"- Review instructions SHA256: `{evidence.get('review_instructions_sha256')}`")
        lines.append("")
        lines.append("### Preflight checklist")
        lines.append("")
        for item in audit.get("preflight", {}).get("checklist", []):
            lines.append(f"- **{item.get('status')}** `{item.get('name')}`: {item.get('detail')}")
        lines.append("")
        lines.append("### Handoff steps")
        lines.append("")
        for item in audit.get("handoff_steps", []):
            lines.append(f"- {item}")
        lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_capability_policy_baseline_apply(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Capability Policy Baseline Apply")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Reviewed path: `{report.get('reviewed_path')}`")
    lines.append(f"Baseline path: `{report.get('baseline_path')}`")
    lines.append(f"Backup path: `{report.get('backup_path') or 'none'}`")
    lines.append("")
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {summary['status']}")
    lines.append(f"- Applied: {summary['applied']}")
    lines.append(f"- Skipped: {summary['skipped']}")
    lines.append(f"- Executes anything: {summary['executes_anything']}")
    lines.append(f"- Checks: {summary['checks']}")
    lines.append(f"- Pass: {summary['pass']}")
    lines.append(f"- Warn: {summary['warn']}")
    lines.append(f"- Fail: {summary['fail']}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    for item in report.get("results", []):
        lines.append(f"- {item.get('action')}: {item.get('reason') or item.get('baseline_path') or ''}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"


def markdown_for_completed_work_review(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Completed Work Review")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append("")
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {summary['status']}")
    lines.append(f"- Executes anything: {summary['executes_anything']}")
    lines.append(f"- Checks: {summary['checks']}")
    lines.append(f"- Pass: {summary['pass']}")
    lines.append(f"- Warn: {summary['warn']}")
    lines.append(f"- Fail: {summary['fail']}")
    lines.append("")
    lines.append("## Review axes")
    lines.append("")
    for key, axis in report.get("review_axes", {}).items():
        lines.append(f"### {axis.get('name', key)}")
        lines.append(f"- status: {axis.get('status')}")
        lines.append(f"- evidence: {'; '.join(axis.get('evidence', []))}")
        for extra_key in sorted(set(axis.keys()) - {"name", "status", "evidence", "recommendation"}):
            lines.append(f"- {extra_key}: `{axis.get(extra_key)}`")
        lines.append(f"- recommendation: {axis.get('recommendation')}")
        lines.append("")
    lines.append("## Next recommended candidates")
    lines.append("")
    candidates = report.get("next_recommended_candidates", [])
    if candidates:
        for candidate in candidates:
            lines.append(f"- {candidate}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report.get("checks", []):
        lines.append(f"- **{check['status']}** `{check['name']}`: {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    lines.append("")
    lines.append("This report is a post-phase review to confirm completed work remains reasonable, correct, roadmap-aligned, faithful to the Portable AI Assets original vision, and informed by external learning rather than closed-door building.")
    return "\n".join(lines) + "\n"


def markdown_for_public_safety_scan(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Public Safety Scan")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Status: {report['summary']['status']}")
    lines.append(f"- Scanned files: {report['summary']['scanned_files']}")
    lines.append(f"- Findings: {report['summary']['findings']}")
    lines.append(f"- Blockers: {report['summary']['blockers']}")
    lines.append(f"- Warnings: {report['summary']['warnings']}")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if report["findings"]:
        for item in report["findings"]:
            lines.append(f"- **{item['severity']}** `{item['path']}:{item['line']}` {item['type']}: `{item['excerpt']}`")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def markdown_for_release_readiness(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AI-Assets Release Readiness Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Engine root: `{report['engine_root']}`")
    lines.append(f"Asset root: `{report['root']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Readiness: {report['summary']['readiness']}")
    lines.append(f"- Checks: {report['summary']['checks']}")
    lines.append(f"- Pass: {report['summary']['pass']}")
    lines.append(f"- Warn: {report['summary']['warn']}")
    lines.append(f"- Fail: {report['summary']['fail']}")
    lines.append(f"- Schema invalid: {report['summary']['schema_invalid']}")
    lines.append(f"- Safety blockers: {report['summary']['safety_blockers']}")
    lines.append(f"- Safety warnings: {report['summary']['safety_warnings']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for check in report["checks"]:
        lines.append(f"- **{check['status']}** `{check['name']}` ({check['severity']}): {check['detail']}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines) + "\n"



def write_outputs(report: Dict[str, object], output_format: str) -> None:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = report["mode"]
    json_path = REPORTS / f"{prefix}-{stamp}.json"
    md_path = REPORTS / f"{prefix}-{stamp}.md"
    latest_json = REPORTS / f"latest-{prefix}.json"
    latest_md = REPORTS / f"latest-{prefix}.md"

    json_text = json.dumps(report, ensure_ascii=False, indent=2)
    if report["mode"] == "inspect":
        md_text = markdown_for_inspect(report)
    elif report["mode"] == "plan":
        md_text = markdown_for_plan(report)
    elif report["mode"] == "diff":
        md_text = markdown_for_diff(report)
    elif report["mode"] == "merge-apply":
        md_text = markdown_for_merge_apply(report)
    elif report["mode"] == "merge-candidates":
        md_text = markdown_for_merge_candidates(report)
    elif report["mode"] == "review-apply":
        md_text = markdown_for_review_apply(report)
    elif report["mode"] == "validate-schemas":
        md_text = markdown_for_validate_schemas(report)
    elif report["mode"] == "connectors":
        md_text = markdown_for_connectors(report)
    elif report["mode"] == "skills-inventory":
        md_text = markdown_for_skills_inventory(report)
    elif report["mode"] == "connector-preview":
        md_text = markdown_for_connector_preview(report)
    elif report["mode"] == "redacted-examples":
        md_text = markdown_for_redacted_examples(report)
    elif report["mode"] == "demo-story":
        md_text = markdown_for_demo_story(report)
    elif report["mode"] == "public-demo-pack":
        md_text = markdown_for_public_demo_pack(report)
    elif report["mode"] == "refresh-canonical-assets":
        md_text = markdown_for_refresh_canonical_assets(report)
    elif report["mode"] == "init-private-assets":
        md_text = markdown_for_init_private_assets(report)
    elif report["mode"] == "private-assets-status":
        md_text = markdown_for_private_assets_status(report)
    elif report["mode"] == "memos-health":
        md_text = markdown_for_memos_health(report)
    elif report["mode"] == "memos-import-preview":
        md_text = markdown_for_memos_import_preview(report)
    elif report["mode"] == "memos-skill-candidates":
        md_text = markdown_for_memos_skill_candidates(report)
    elif report["mode"] == "skill-candidates-status":
        md_text = markdown_for_skill_candidates_status(report)
    elif report["mode"] == "skill-review-apply":
        md_text = markdown_for_skill_review_apply(report)
    elif report["mode"] == "skill-projection-preview":
        md_text = markdown_for_skill_projection_preview(report)
    elif report["mode"] == "skill-projection-candidates":
        md_text = markdown_for_skill_projection_candidates(report)
    elif report["mode"] == "skill-projection-status":
        md_text = markdown_for_skill_projection_status(report)
    elif report["mode"] == "skill-projection-review-apply":
        md_text = markdown_for_skill_projection_review_apply(report)
    elif report["mode"] == "public-safety-scan":
        md_text = markdown_for_public_safety_scan(report)
    elif report["mode"] == "release-readiness":
        md_text = markdown_for_release_readiness(report)
    elif report["mode"] == "public-release-pack":
        md_text = markdown_for_public_release_pack(report)
    elif report["mode"] == "public-release-archive":
        md_text = markdown_for_public_release_archive(report)
    elif report["mode"] == "public-release-smoke-test":
        md_text = markdown_for_public_release_smoke_test(report)
    elif report["mode"] == "github-publish-check":
        md_text = markdown_for_github_publish_check(report)
    elif report["mode"] == "public-repo-staging":
        md_text = markdown_for_public_repo_staging(report)
    elif report["mode"] == "public-repo-staging-status":
        md_text = markdown_for_public_repo_staging_status(report)
    elif report["mode"] == "public-repo-staging-history-preflight":
        md_text = markdown_for_report_checks(report, "Public Repo Staging History Preflight")
    elif report["mode"] == "manual-publication-decision-packet":
        md_text = markdown_for_report_checks(report, "Manual Publication Decision Packet")
    elif report["mode"] == "github-publish-dry-run":
        md_text = markdown_for_github_publish_dry_run(report)
    elif report["mode"] == "github-handoff-pack":
        md_text = markdown_for_github_handoff_pack(report)
    elif report["mode"] == "github-final-preflight":
        md_text = markdown_for_github_final_preflight(report)
    elif report["mode"] == "release-provenance":
        md_text = markdown_for_release_provenance(report)
    elif report["mode"] == "verify-release-provenance":
        md_text = markdown_for_verify_release_provenance(report)
    elif report["mode"] == "release-closure":
        md_text = markdown_for_release_closure(report)
    elif report["mode"] == "public-package-freshness-review":
        md_text = markdown_for_public_package_freshness_review(report)
    elif report["mode"] == "public-docs-external-reader-review":
        md_text = markdown_for_public_docs_external_reader_review(report)
    elif report["mode"] == "release-candidate-closure-review":
        md_text = markdown_for_release_candidate_closure_review(report)
    elif report["mode"] == "release-reviewer-packet-index":
        md_text = markdown_for_release_reviewer_packet_index(report)
    elif report["mode"] == "release-reviewer-decision-log":
        md_text = markdown_for_release_reviewer_decision_log(report)
    elif report["mode"] == "external-reviewer-quickstart":
        md_text = markdown_for_external_reviewer_quickstart(report)
    elif report["mode"] == "external-reviewer-feedback-plan":
        md_text = markdown_for_external_reviewer_feedback_plan(report)
    elif report["mode"] == "external-reviewer-feedback-status":
        md_text = markdown_for_external_reviewer_feedback_status(report)
    elif report["mode"] == "external-reviewer-feedback-template":
        md_text = markdown_for_external_reviewer_feedback_template(report)
    elif report["mode"] == "external-reviewer-feedback-followup-index":
        md_text = markdown_for_external_reviewer_feedback_followup_index(report)
    elif report["mode"] == "external-reviewer-feedback-followup-candidates":
        md_text = markdown_for_external_reviewer_feedback_followup_candidates(report)
    elif report["mode"] == "external-reviewer-feedback-followup-candidate-status":
        md_text = markdown_for_external_reviewer_feedback_followup_candidate_status(report)
    elif report["mode"] == "initial-completion-review":
        md_text = markdown_for_initial_completion_review(report)
    elif report["mode"] == "human-action-closure-checklist":
        md_text = markdown_for_human_action_closure_checklist(report)
    elif report["mode"] == "manual-reviewer-execution-packet":
        md_text = markdown_for_manual_reviewer_execution_packet(report)
    elif report["mode"] == "manual-reviewer-public-surface-freshness":
        md_text = markdown_for_manual_reviewer_public_surface_freshness(report)
    elif report["mode"] == "manual-reviewer-handoff-readiness":
        md_text = markdown_for_manual_reviewer_handoff_readiness(report)
    elif report["mode"] == "manual-reviewer-handoff-packet-index":
        md_text = markdown_for_manual_reviewer_handoff_packet_index(report)
    elif report["mode"] == "manual-reviewer-handoff-freeze-check":
        md_text = markdown_for_manual_reviewer_handoff_freeze_check(report)
    elif report["mode"] == "agent-owner-delegation-review":
        md_text = markdown_for_agent_owner_delegation_review(report)
    elif report["mode"] == "agent-complete-external-actions-reserved":
        md_text = markdown_for_agent_complete_external_actions_reserved(report)
    elif report["mode"] == "agent-complete-failclosed-hardening-review":
        md_text = markdown_for_agent_complete_failclosed_hardening_review(report)
    elif report["mode"] == "agent-complete-regression-evidence-integrity":
        md_text = markdown_for_agent_complete_regression_evidence_integrity(report)
    elif report["mode"] == "agent-complete-syntax-invalid-evidence-failclosed-review":
        md_text = markdown_for_agent_complete_syntax_invalid_evidence_failclosed_review(report)
    elif report["mode"] == "agent-complete-phase102-rollup-evidence-failclosed-review":
        md_text = markdown_for_agent_complete_phase102_rollup_evidence_failclosed_review(report)
    elif report["mode"] == "manual-release-reviewer-checklist":
        md_text = markdown_for_manual_release_reviewer_checklist(report)
    elif report["mode"] == "external-reference-inventory":
        md_text = markdown_for_external_reference_inventory(report)
    elif report["mode"] == "external-reference-backlog":
        md_text = markdown_for_external_reference_backlog(report)
    elif report["mode"] == "team-pack-preview":
        md_text = markdown_for_team_pack_preview(report)
    elif report["mode"] == "project-pack-preview":
        md_text = markdown_for_project_pack_preview(report)
    elif report["mode"] == "capability-risk-inventory":
        md_text = markdown_for_capability_risk_inventory(report)
    elif report["mode"] == "capability-policy-preview":
        md_text = markdown_for_capability_policy_preview(report)
    elif report["mode"] == "capability-policy-candidate-generation":
        md_text = markdown_for_capability_policy_candidate_generation(report)
    elif report["mode"] == "capability-policy-candidate-status":
        md_text = markdown_for_capability_policy_candidate_status(report)
    elif report["mode"] == "capability-policy-baseline-apply":
        md_text = markdown_for_capability_policy_baseline_apply(report)
    elif report["mode"] == "completed-work-review":
        md_text = markdown_for_completed_work_review(report)
    else:
        md_text = markdown_for_apply(report)

    if output_format in ("json", "both"):
        json_path.write_text(json_text + "\n", encoding="utf-8")
        latest_json.write_text(json_text + "\n", encoding="utf-8")
    if output_format in ("markdown", "both"):
        md_path.write_text(md_text, encoding="utf-8")
        latest_md.write_text(md_text, encoding="utf-8")

    print(f"{report['mode'].capitalize()} report generated for {report['host_home']}")
    if output_format in ("json", "both"):
        print(f"JSON: {json_path}")
        print(f"JSON latest: {latest_json}")
    if output_format in ("markdown", "both"):
        print(f"Markdown: {md_path}")
        print(f"Markdown latest: {latest_md}")



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="inspect", choices=["inspect", "plan", "apply", "diff", "merge-apply", "merge-candidates", "review-apply", "validate-schemas", "connectors", "skills-inventory", "skill-projection-preview", "skill-projection-candidates", "skill-projection-status", "skill-projection-review-apply", "public-safety-scan", "release-readiness", "public-release-pack", "public-release-archive", "public-release-smoke-test", "github-publish-check", "public-repo-staging", "public-repo-staging-status", "public-repo-staging-history-preflight", "manual-publication-decision-packet", "github-publish-dry-run", "github-handoff-pack", "github-final-preflight", "release-provenance", "verify-release-provenance", "release-closure", "public-package-freshness-review", "public-docs-external-reader-review", "release-candidate-closure-review", "release-reviewer-packet-index", "release-reviewer-decision-log", "external-reviewer-quickstart", "external-reviewer-feedback-plan", "external-reviewer-feedback-status", "external-reviewer-feedback-template", "external-reviewer-feedback-followup-index", "external-reviewer-feedback-followup-candidates", "external-reviewer-feedback-followup-candidate-status", "initial-completion-review", "human-action-closure-checklist", "manual-reviewer-execution-packet", "manual-reviewer-public-surface-freshness", "manual-reviewer-handoff-readiness", "manual-reviewer-handoff-packet-index", "manual-reviewer-handoff-freeze-check", "agent-owner-delegation-review", "agent-complete-external-actions-reserved", "agent-complete-failclosed-hardening-review", "agent-complete-regression-evidence-integrity", "agent-complete-syntax-invalid-evidence-failclosed-review", "agent-complete-phase102-rollup-evidence-failclosed-review", "manual-release-reviewer-checklist", "external-reference-inventory", "external-reference-backlog", "team-pack-preview", "project-pack-preview", "capability-risk-inventory", "capability-policy-preview", "capability-policy-candidate-generation", "capability-policy-candidate-status", "capability-policy-baseline-apply", "completed-work-review", "connector-preview", "redacted-examples", "demo-story", "public-demo-pack", "refresh-canonical-assets", "init-private-assets", "private-assets-status", "memos-health", "memos-import-preview", "memos-skill-candidates", "skill-candidates-status", "skill-review-apply"])
    parser.add_argument("--output-format", default="both", choices=["json", "markdown", "both"])
    parser.add_argument("--config")
    parser.add_argument("--asset-root")
    parser.add_argument("--asset-repo-remote")
    args = parser.parse_args()

    configure_runtime_paths(config_path=args.config, asset_root_override=args.asset_root)
    inspect_report = build_inspect_report()
    if args.mode == "inspect":
        write_outputs(inspect_report, args.output_format)
    elif args.mode == "plan":
        plan_report = build_plan_report(inspect_report)
        write_outputs(plan_report, args.output_format)
    elif args.mode == "diff":
        plan_report = build_plan_report(inspect_report)
        diff_report = build_diff_report(inspect_report, plan_report)
        write_outputs(diff_report, args.output_format)
    elif args.mode == "merge-apply":
        plan_report = build_plan_report(inspect_report)
        diff_report = build_diff_report(inspect_report, plan_report)
        merge_apply_report = execute_merge_apply(diff_report)
        write_outputs(merge_apply_report, args.output_format)
    elif args.mode == "merge-candidates":
        plan_report = build_plan_report(inspect_report)
        diff_report = build_diff_report(inspect_report, plan_report)
        merge_candidate_report = generate_merge_candidates(diff_report)
        write_outputs(merge_candidate_report, args.output_format)
    elif args.mode == "review-apply":
        candidate_report = load_report_json("merge-candidates")
        if candidate_report is None:
            raise SystemExit("No latest merge-candidates report found. Run --merge-candidates first.")
        review_apply_report = execute_review_apply(candidate_report)
        write_outputs(review_apply_report, args.output_format)
    elif args.mode == "validate-schemas":
        schema_report = validate_schema_directory()
        write_outputs(schema_report, args.output_format)
    elif args.mode == "connectors":
        connector_report = build_connector_report()
        write_outputs(connector_report, args.output_format)
    elif args.mode == "skills-inventory":
        skills_report = build_skills_inventory_report()
        write_outputs(skills_report, args.output_format)
    elif args.mode == "skill-projection-preview":
        projection_report = build_skill_projection_preview_report()
        write_outputs(projection_report, args.output_format)
    elif args.mode == "skill-projection-candidates":
        projection_candidates_report = generate_skill_projection_candidates()
        write_outputs(projection_candidates_report, args.output_format)
    elif args.mode == "skill-projection-status":
        projection_status_report = build_skill_projection_status_report()
        write_outputs(projection_status_report, args.output_format)
    elif args.mode == "skill-projection-review-apply":
        projection_apply_report = execute_skill_projection_review_apply()
        write_outputs(projection_apply_report, args.output_format)
    elif args.mode == "public-safety-scan":
        safety_report = build_public_safety_scan_report()
        write_outputs(safety_report, args.output_format)
    elif args.mode == "release-readiness":
        readiness_report = build_release_readiness_report()
        write_outputs(readiness_report, args.output_format)
    elif args.mode == "public-release-pack":
        release_pack_report = build_public_release_pack_report()
        write_outputs(release_pack_report, args.output_format)
    elif args.mode == "public-release-archive":
        archive_report = build_public_release_archive_report()
        write_outputs(archive_report, args.output_format)
    elif args.mode == "public-release-smoke-test":
        smoke_report = build_public_release_smoke_test_report()
        write_outputs(smoke_report, args.output_format)
    elif args.mode == "github-publish-check":
        github_report = build_github_publish_check_report()
        write_outputs(github_report, args.output_format)
    elif args.mode == "public-repo-staging":
        staging_report = build_public_repo_staging_report()
        write_outputs(staging_report, args.output_format)
    elif args.mode == "public-repo-staging-status":
        staging_status_report = build_public_repo_staging_status_report()
        write_outputs(staging_status_report, args.output_format)
    elif args.mode == "public-repo-staging-history-preflight":
        staging_history_preflight_report = build_public_repo_staging_history_preflight_report()
        write_outputs(staging_history_preflight_report, args.output_format)
    elif args.mode == "manual-publication-decision-packet":
        decision_packet_report = build_manual_publication_decision_packet_report()
        write_outputs(decision_packet_report, args.output_format)
    elif args.mode == "github-publish-dry-run":
        dry_run_report = build_github_publish_dry_run_report()
        write_outputs(dry_run_report, args.output_format)
    elif args.mode == "github-handoff-pack":
        handoff_report = build_github_handoff_pack_report()
        write_outputs(handoff_report, args.output_format)
    elif args.mode == "github-final-preflight":
        final_preflight_report = build_github_final_preflight_report()
        write_outputs(final_preflight_report, args.output_format)
    elif args.mode == "release-provenance":
        provenance_report = build_release_provenance_report()
        write_outputs(provenance_report, args.output_format)
    elif args.mode == "verify-release-provenance":
        verify_provenance_report = build_verify_release_provenance_report()
        write_outputs(verify_provenance_report, args.output_format)
    elif args.mode == "release-closure":
        closure_report = build_release_closure_report()
        write_outputs(closure_report, args.output_format)
    elif args.mode == "public-package-freshness-review":
        freshness_review_report = build_public_package_freshness_review_report()
        write_outputs(freshness_review_report, args.output_format)
    elif args.mode == "public-docs-external-reader-review":
        external_reader_report = build_public_docs_external_reader_review_report()
        write_outputs(external_reader_report, args.output_format)
    elif args.mode == "release-candidate-closure-review":
        release_candidate_closure_report = build_release_candidate_closure_review_report()
        write_outputs(release_candidate_closure_report, args.output_format)
    elif args.mode == "release-reviewer-packet-index":
        reviewer_packet_index_report = build_release_reviewer_packet_index_report()
        write_outputs(reviewer_packet_index_report, args.output_format)
    elif args.mode == "release-reviewer-decision-log":
        reviewer_decision_log_report = build_release_reviewer_decision_log_report()
        write_outputs(reviewer_decision_log_report, args.output_format)
    elif args.mode == "external-reviewer-quickstart":
        external_reviewer_quickstart_report = build_external_reviewer_quickstart_report()
        write_outputs(external_reviewer_quickstart_report, args.output_format)
    elif args.mode == "external-reviewer-feedback-plan":
        external_reviewer_feedback_plan_report = build_external_reviewer_feedback_plan_report()
        write_outputs(external_reviewer_feedback_plan_report, args.output_format)
    elif args.mode == "external-reviewer-feedback-status":
        external_reviewer_feedback_status_report = build_external_reviewer_feedback_status_report()
        write_outputs(external_reviewer_feedback_status_report, args.output_format)
    elif args.mode == "external-reviewer-feedback-template":
        external_reviewer_feedback_template_report = execute_external_reviewer_feedback_template()
        write_outputs(external_reviewer_feedback_template_report, args.output_format)
    elif args.mode == "external-reviewer-feedback-followup-index":
        external_reviewer_feedback_followup_index_report = build_external_reviewer_feedback_followup_index_report()
        write_outputs(external_reviewer_feedback_followup_index_report, args.output_format)
    elif args.mode == "external-reviewer-feedback-followup-candidates":
        external_reviewer_feedback_followup_candidates_report = execute_external_reviewer_feedback_followup_candidates()
        write_outputs(external_reviewer_feedback_followup_candidates_report, args.output_format)
    elif args.mode == "external-reviewer-feedback-followup-candidate-status":
        external_reviewer_feedback_followup_candidate_status_report = build_external_reviewer_feedback_followup_candidate_status_report()
        write_outputs(external_reviewer_feedback_followup_candidate_status_report, args.output_format)
    elif args.mode == "initial-completion-review":
        initial_completion_review_report = build_initial_completion_review_report()
        write_outputs(initial_completion_review_report, args.output_format)
    elif args.mode == "human-action-closure-checklist":
        human_action_closure_checklist_report = build_human_action_closure_checklist_report()
        write_outputs(human_action_closure_checklist_report, args.output_format)
    elif args.mode == "manual-reviewer-execution-packet":
        manual_reviewer_execution_packet_report = build_manual_reviewer_execution_packet_report()
        write_outputs(manual_reviewer_execution_packet_report, args.output_format)
    elif args.mode == "manual-reviewer-public-surface-freshness":
        manual_reviewer_public_surface_freshness_report = build_manual_reviewer_public_surface_freshness_report()
        write_outputs(manual_reviewer_public_surface_freshness_report, args.output_format)
    elif args.mode == "manual-reviewer-handoff-readiness":
        manual_reviewer_handoff_readiness_report = build_manual_reviewer_handoff_readiness_report()
        write_outputs(manual_reviewer_handoff_readiness_report, args.output_format)
    elif args.mode == "manual-reviewer-handoff-packet-index":
        manual_reviewer_handoff_packet_index_report = build_manual_reviewer_handoff_packet_index_report()
        write_outputs(manual_reviewer_handoff_packet_index_report, args.output_format)
    elif args.mode == "manual-reviewer-handoff-freeze-check":
        manual_reviewer_handoff_freeze_check_report = build_manual_reviewer_handoff_freeze_check_report()
        write_outputs(manual_reviewer_handoff_freeze_check_report, args.output_format)
    elif args.mode == "agent-owner-delegation-review":
        agent_owner_delegation_review_report = build_agent_owner_delegation_review_report()
        write_outputs(agent_owner_delegation_review_report, args.output_format)
    elif args.mode == "agent-complete-external-actions-reserved":
        agent_complete_external_actions_reserved_report = build_agent_complete_external_actions_reserved_report()
        write_outputs(agent_complete_external_actions_reserved_report, args.output_format)
    elif args.mode == "agent-complete-failclosed-hardening-review":
        agent_complete_failclosed_hardening_review_report = build_agent_complete_failclosed_hardening_review_report()
        write_outputs(agent_complete_failclosed_hardening_review_report, args.output_format)
    elif args.mode == "agent-complete-regression-evidence-integrity":
        agent_complete_regression_evidence_integrity_report = build_agent_complete_regression_evidence_integrity_report()
        write_outputs(agent_complete_regression_evidence_integrity_report, args.output_format)
    elif args.mode == "agent-complete-syntax-invalid-evidence-failclosed-review":
        agent_complete_syntax_invalid_evidence_failclosed_review_report = build_agent_complete_syntax_invalid_evidence_failclosed_review_report()
        write_outputs(agent_complete_syntax_invalid_evidence_failclosed_review_report, args.output_format)
    elif args.mode == "agent-complete-phase102-rollup-evidence-failclosed-review":
        agent_complete_phase102_rollup_evidence_failclosed_review_report = build_agent_complete_phase102_rollup_evidence_failclosed_review_report()
        write_outputs(agent_complete_phase102_rollup_evidence_failclosed_review_report, args.output_format)
    elif args.mode == "manual-release-reviewer-checklist":
        reviewer_checklist_report = build_manual_release_reviewer_checklist_report()
        write_outputs(reviewer_checklist_report, args.output_format)
    elif args.mode == "external-reference-inventory":
        external_reference_report = build_external_reference_inventory_report()
        write_outputs(external_reference_report, args.output_format)
    elif args.mode == "external-reference-backlog":
        external_reference_backlog_report = build_external_reference_backlog_report()
        write_outputs(external_reference_backlog_report, args.output_format)
    elif args.mode == "team-pack-preview":
        team_pack_report = build_team_pack_preview_report()
        write_outputs(team_pack_report, args.output_format)
    elif args.mode == "project-pack-preview":
        project_pack_report = build_project_pack_preview_report()
        write_outputs(project_pack_report, args.output_format)
    elif args.mode == "capability-risk-inventory":
        capability_report = build_capability_risk_inventory_report()
        write_outputs(capability_report, args.output_format)
    elif args.mode == "capability-policy-preview":
        policy_report = build_capability_policy_preview_report()
        write_outputs(policy_report, args.output_format)
    elif args.mode == "capability-policy-candidate-generation":
        candidate_generation_report = build_capability_policy_candidate_generation_report()
        write_outputs(candidate_generation_report, args.output_format)
    elif args.mode == "capability-policy-candidate-status":
        candidate_status_report = build_capability_policy_candidate_status_report()
        write_outputs(candidate_status_report, args.output_format)
    elif args.mode == "capability-policy-baseline-apply":
        baseline_apply_report = execute_capability_policy_baseline_apply()
        write_outputs(baseline_apply_report, args.output_format)
    elif args.mode == "completed-work-review":
        completed_review_report = build_completed_work_review_report()
        write_outputs(completed_review_report, args.output_format)
    elif args.mode == "connector-preview":
        preview_report = build_connector_preview_report()
        write_outputs(preview_report, args.output_format)
    elif args.mode == "redacted-examples":
        redacted_examples_report = build_redacted_examples_report()
        write_outputs(redacted_examples_report, args.output_format)
    elif args.mode == "demo-story":
        demo_story_report = build_demo_story_report()
        write_outputs(demo_story_report, args.output_format)
    elif args.mode == "public-demo-pack":
        demo_pack_report = build_public_demo_pack_report()
        write_outputs(demo_pack_report, args.output_format)
    elif args.mode == "refresh-canonical-assets":
        refresh_report = build_refresh_canonical_assets_report()
        write_outputs(refresh_report, args.output_format)
    elif args.mode == "init-private-assets":
        init_report = initialize_private_assets_repo(ASSETS, asset_repo_remote=args.asset_repo_remote)
        write_outputs(init_report, args.output_format)
    elif args.mode == "private-assets-status":
        status_report = build_private_assets_status_report()
        write_outputs(status_report, args.output_format)
    elif args.mode == "memos-health":
        memos_report = build_memos_health_report()
        write_outputs(memos_report, args.output_format)
    elif args.mode == "memos-import-preview":
        memos_import_report = build_memos_import_preview_report()
        write_outputs(memos_import_report, args.output_format)
    elif args.mode == "memos-skill-candidates":
        memos_skill_report = build_memos_skill_candidates_report()
        write_outputs(memos_skill_report, args.output_format)
    elif args.mode == "skill-candidates-status":
        skill_status_report = build_skill_candidates_status_report()
        write_outputs(skill_status_report, args.output_format)
    elif args.mode == "skill-review-apply":
        skill_apply_report = execute_skill_review_apply()
        write_outputs(skill_apply_report, args.output_format)
    else:
        plan_report = build_plan_report(inspect_report)
        apply_report = execute_apply(plan_report)
        write_outputs(apply_report, args.output_format)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
