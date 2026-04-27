#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
from pathlib import Path
from typing import Any, Dict, Optional


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
    if value in ('', 'null', 'Null', 'NULL', '~'):
        return None if value != '' else ''
    if value in ('true', 'True', 'TRUE'):
        return True
    if value in ('false', 'False', 'FALSE'):
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def simple_yaml_load(text: str) -> Any:
    result: Dict[str, Any] = {}
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith('#') or ':' not in stripped or raw.startswith(' '):
            continue
        key, value = stripped.split(':', 1)
        result[key.strip()] = _parse_yaml_scalar(value)
    return result


def discover_engine_root(script_path: Optional[Path] = None) -> Path:
    anchor = (script_path or Path(__file__)).resolve()
    return anchor.parents[2]


def _resolve_path(value: Optional[str], *, base: Path) -> Optional[Path]:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    else:
        path = path.resolve()
    return path


def _load_yaml_mapping(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    data = simple_yaml_load(path.read_text(encoding='utf-8'))
    return data if isinstance(data, dict) else {}


def resolve_runtime_paths(
    *,
    config_path: Optional[str] = None,
    asset_root_override: Optional[str] = None,
    engine_root_override: Optional[str] = None,
    script_path: Optional[Path] = None,
) -> Dict[str, Any]:
    home = Path.home()
    default_config_path = home / '.config' / 'portable-ai-assets' / 'config.yaml'
    selected_config = Path(
        config_path
        or os.environ.get('PAA_CONFIG_PATH')
        or default_config_path
    ).expanduser()
    config_data = _load_yaml_mapping(selected_config)
    config_base = selected_config.parent if selected_config.parent else home

    env_engine_root = os.environ.get('PAA_ENGINE_ROOT')
    env_asset_root = os.environ.get('PAA_ASSET_ROOT')
    discovered_engine_root = discover_engine_root(script_path)

    engine_root = (
        _resolve_path(engine_root_override, base=config_base)
        or _resolve_path(env_engine_root, base=config_base)
        or _resolve_path(config_data.get('engine_root'), base=config_base)
        or discovered_engine_root
    )
    asset_root = (
        _resolve_path(asset_root_override, base=config_base)
        or _resolve_path(env_asset_root, base=config_base)
        or _resolve_path(config_data.get('asset_root'), base=config_base)
        or engine_root
    )

    return {
        'engine_root': str(engine_root),
        'asset_root': str(asset_root),
        'asset_repo_remote': config_data.get('asset_repo_remote'),
        'default_sync_mode': config_data.get('default_sync_mode', 'review-before-commit'),
        'allow_auto_commit': bool(config_data.get('allow_auto_commit', False)),
        'config_path': str(selected_config),
        'config_exists': selected_config.is_file(),
    }


def shell_exports(runtime_paths: Dict[str, Any]) -> str:
    exports = {
        'PAA_ENGINE_ROOT': runtime_paths['engine_root'],
        'PAA_ASSET_ROOT': runtime_paths['asset_root'],
        'PAA_CONFIG_PATH': runtime_paths['config_path'],
        'PAA_ASSET_REPO_REMOTE': runtime_paths.get('asset_repo_remote') or '',
        'PAA_DEFAULT_SYNC_MODE': runtime_paths.get('default_sync_mode') or 'review-before-commit',
        'PAA_ALLOW_AUTO_COMMIT': 'true' if runtime_paths.get('allow_auto_commit') else 'false',
    }
    return "\n".join(f"export {key}={shlex.quote(str(value))}" for key, value in exports.items())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--asset-root')
    parser.add_argument('--engine-root')
    parser.add_argument('--shell-exports', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    runtime_paths = resolve_runtime_paths(
        config_path=args.config,
        asset_root_override=args.asset_root,
        engine_root_override=args.engine_root,
        script_path=Path(__file__).resolve(),
    )

    if args.shell_exports:
        print(shell_exports(runtime_paths))
    else:
        print(json.dumps(runtime_paths, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
