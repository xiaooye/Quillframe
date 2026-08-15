#!/usr/bin/env python3
"""NovelForge Studio Project Hub projection.

Consumes novelforge_project_adapter_resolution_v1 and emits a browser/remote-safe,
read-only Studio projection. This module is a presentation/query adapter only;
it carries no Canon, Framework-write, settlement, or semantic authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "novelforge_project_adapter_resolution_v1"
OUTPUT_SCHEMA = "novelforge_studio_project_hub_projection_v1"
SURFACES = {"cli", "local_app", "cloud_ui", "agent_package"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _safe_framework(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed = ("name", "version", "commit", "bundle_fingerprint")
    return {key: value[key] for key in allowed if value.get(key) is not None}


def _safe_paths(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for domain, entry in sorted(value.items()):
        if not isinstance(domain, str) or not isinstance(entry, dict):
            continue
        result[domain] = {
            "relative": entry.get("relative"),
            "exists": bool(entry.get("exists", False)),
            "kind": entry.get("kind", "unknown"),
        }
    return result


def build_projection(source: dict[str, Any], surface: str = "cloud_ui") -> dict[str, Any]:
    if source.get("schema") != SOURCE_SCHEMA:
        raise ValueError(f"expected source schema {SOURCE_SCHEMA}")
    if surface not in SURFACES:
        raise ValueError("surface must be one of: " + ", ".join(sorted(SURFACES)))

    source_fp = fingerprint(source)
    projection: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "source_schema": SOURCE_SCHEMA,
        "source_fingerprint": source_fp,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "surface": surface,
        "surface_semantics": {
            "delivery_surface_only": True,
            "capability_does_not_imply_authority": True,
            "direct_core_store_access": False,
            "absolute_paths_exposed": False,
        },
        "project": {
            "id": source.get("project_id"),
            "title": source.get("project_title"),
            "version": source.get("project_version"),
            "language": source.get("language"),
            "layout": source.get("layout"),
            "project_schema_version": source.get("project_schema_version"),
        },
        "framework_lock": _safe_framework(source.get("framework_lock")),
        "authority_policy": source.get("authority") if isinstance(source.get("authority"), dict) else {},
        "logical_paths": _safe_paths(source.get("paths")),
        "quality_policy": source.get("quality") if isinstance(source.get("quality"), dict) else {},
        "build_policy": source.get("build") if isinstance(source.get("build"), dict) else {},
        "unavailable": [
            "current_chapter",
            "current_scene",
            "manuscript_lifecycle",
            "latest_run",
            "publication_status",
            "quality_status",
        ],
    }
    projection["projection_fingerprint"] = fingerprint(projection)
    return projection


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input JSON must be an object")
    return value


def self_test() -> dict[str, Any]:
    source = {
        "schema": SOURCE_SCHEMA,
        "project_id": "PROJECT-SYNTHETIC",
        "project_title": "Synthetic Story Loom",
        "project_version": "0.0.0",
        "language": "en",
        "project_root": "/private/host/path/never-expose",
        "layout": "mapped",
        "framework_lock": {
            "name": "NovelForge",
            "version": "8.0.0-dev",
            "commit": "fixture",
            "bundle_fingerprint": "sha256:" + "a" * 64,
        },
        "project_schema_version": "1",
        "authority": {"precedence": "locked > accepted > active_plan > review > proposal"},
        "paths": {
            "manuscripts": {
                "relative": "manuscripts",
                "absolute": "/private/host/path/never-expose/manuscripts",
                "exists": True,
                "kind": "dir",
            }
        },
        "quality": {"reader_grip": "very_high"},
        "build": {},
    }
    first = build_projection(source, "cloud_ui")
    second = build_projection(source, "cloud_ui")
    serialized = canonical(first)

    wrong_schema_rejected = False
    try:
        build_projection({"schema": "wrong"})
    except ValueError:
        wrong_schema_rejected = True

    checks = {
        "source_schema_rejected": wrong_schema_rejected,
        "authority_false": first["authority"] is False,
        "no_project_root": "project_root" not in serialized,
        "no_absolute_paths": "/private/host/path/never-expose" not in serialized,
        "deterministic": first == second,
        "source_fingerprint_bound": first["source_fingerprint"] == fingerprint(source),
        "projection_fingerprint_present": first["projection_fingerprint"].startswith("sha256:"),
    }
    return {
        "studio_project_hub_projection_contract": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "projection": first,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a safe NovelForge Studio Project Hub projection")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("input")
    build.add_argument("--surface", choices=sorted(SURFACES), default="cloud_ui")
    build.add_argument("--output")

    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["studio_project_hub_projection_contract"] == "PASS" else 1

    projection = build_projection(load_json(Path(args.input)), args.surface)
    rendered = json.dumps(projection, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
