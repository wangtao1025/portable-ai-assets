#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import pathlib
import re
import sys
from typing import Dict, List

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from portable_ai_assets_paths import resolve_runtime_paths

HOME = pathlib.Path.home()
RUNTIME_PATHS = resolve_runtime_paths(script_path=pathlib.Path(__file__).resolve())
ASSETS = pathlib.Path(RUNTIME_PATHS["asset_root"])
SRC_ROOT = HOME / ".mempalace-auto" / "bridge" / "corpus-live" / "projects"
DST_ROOT = ASSETS / "memory" / "projects"
RAW_ROOT = ASSETS / "memory" / "summaries" / "mempalace-latest"
INDEX_PATH = ASSETS / "memory" / "summaries" / "INDEX.md"

DST_ROOT.mkdir(parents=True, exist_ok=True)
RAW_ROOT.mkdir(parents=True, exist_ok=True)


def slug_to_name(slug: str) -> str:
    slug = re.sub(r"-[0-9a-f]{8}$", "", slug)
    return slug.replace("-", " ").strip()


def title_case(name: str) -> str:
    return " ".join(part.capitalize() if part.islower() else part for part in name.split())


def extract_field(text: str, field: str) -> str:
    m = re.search(rf"^- {re.escape(field)}: (.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def extract_bullets(text: str) -> List[str]:
    lines = text.splitlines()
    bullets = []
    in_section = False
    for line in lines:
        if line.startswith("## Stable Project Memory"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("- "):
            bullets.append(line[2:].strip())
    return bullets


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def summarise(slug: str, text: str) -> str:
    cwd = extract_field(text, "cwd")
    updated = extract_field(text, "updated_at")
    bullets = [clean(b) for b in extract_bullets(text)]
    title = title_case(slug_to_name(slug))
    lines = [
        f"# Project Summary — {title}",
        "",
        f"Updated: {dt.date.today().isoformat()}",
        f"Source basis: MemPalace latest-session snapshot `{slug}`",
    ]
    if cwd:
        lines.append(f"Original cwd: `{cwd}`")
    if updated:
        lines.append(f"Snapshot updated_at: `{updated}`")
    lines.extend(["", "## Stable memory extracted", ""])
    if bullets:
        for b in bullets[:8]:
            lines.append(f"- {b}")
    else:
        lines.append("- No stable project bullets were found in the snapshot.")
    lines.extend([
        "",
        "## Portability note",
        "",
        "This file is a canonical, human-readable export intended to survive machine changes even if runtime bridge state or local caches are rebuilt later.",
        "",
    ])
    return "\n".join(lines)


index_rows: List[str] = [
    "# MemPalace Latest Snapshot Index",
    "",
    f"Generated: {dt.datetime.now().isoformat(timespec='seconds')}",
    "",
    "| Slug | Export | Raw Copy |",
    "|---|---|---|",
]

count = 0
for latest in sorted(SRC_ROOT.glob("*/latest-session.md")):
    slug = latest.parent.name
    text = latest.read_text(encoding="utf-8", errors="replace")
    summary = summarise(slug, text)
    out = DST_ROOT / f"{slug}.md"
    out.write_text(summary, encoding="utf-8")
    raw = RAW_ROOT / f"{slug}.md"
    raw.write_text(text, encoding="utf-8")
    index_rows.append(f"| `{slug}` | `memory/projects/{out.name}` | `memory/summaries/mempalace-latest/{raw.name}` |")
    count += 1

INDEX_PATH.write_text("\n".join(index_rows) + "\n", encoding="utf-8")
print(f"Exported {count} project snapshots into {DST_ROOT}")
print(f"Wrote raw copies into {RAW_ROOT}")
print(f"Wrote index: {INDEX_PATH}")
