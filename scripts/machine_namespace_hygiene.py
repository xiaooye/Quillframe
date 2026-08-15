#!/usr/bin/env python3
"""Fail when live NovelForge machine surfaces reintroduce pre-release Novel OS identifiers."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {".py", ".json", ".yml", ".yaml", ".toml"}
EXCLUDED_TOP = {".git", "docs", "knowledge", "assets", "specs"}
PATTERNS = {
    "legacy_env_prefix": "NOVEL" + "_OS_",
    "legacy_schema_prefix": "novel" + "_os_",
    "legacy_runtime_dir": ".novel" + "-os/",
    "legacy_server_slug": "novel" + "-os-control-plane",
    "legacy_machine_slug": "novel" + "-os-",
    "legacy_behavior_permission": "os" + "_behavior_write",
}


def live_files() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in EXTENSIONS and path != ROOT / ".gitignore":
            continue
        rel = path.relative_to(ROOT)
        if rel.parts and rel.parts[0] in EXCLUDED_TOP:
            continue
        if path.name.startswith("CHANGELOG"):
            continue
        out.append(path)
    return sorted(out)


def main() -> int:
    files = live_files()
    findings: list[dict[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for label, pattern in PATTERNS.items():
            if pattern in text:
                findings.append({"file": path.relative_to(ROOT).as_posix(), "kind": label})
    result = {
        "machine_namespace_contract": "PASS" if not findings else "FAIL",
        "namespace": "NovelForge-only",
        "files_scanned": len(files),
        "findings": findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
