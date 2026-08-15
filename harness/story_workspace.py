#!/usr/bin/env python3
"""Non-authoritative Story Workspace projection for NovelForge.

The projector groups already-normalized, source-bound Project objects into one
read-only workspace view while preserving each object's lifecycle/authority
class. It never parses private consumer schemas into a parallel Canon store and
never grants Canon/Settlement authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_story_workspace_v1"
INPUT_SCHEMA = "novelforge_story_workspace_input_v1"
SECTIONS = {
    "structure", "timeline", "characters", "relationships", "world_state",
    "plans", "reader_expectations", "context", "branches", "other",
}
LIFECYCLES = {"locked", "accepted", "active_plan", "review", "proposal", "derived", "scenario"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} invalid hex") from exc
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} required")
    return value.strip()


def normalize_object(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("workspace object must be object")
    object_id = _text(raw.get("id"), "object.id")
    section = raw.get("section")
    if section not in SECTIONS:
        raise ValueError(f"invalid workspace section for {object_id}: {section!r}")
    lifecycle = raw.get("lifecycle")
    authority_class = raw.get("authority_class")
    if lifecycle not in LIFECYCLES:
        raise ValueError(f"invalid lifecycle for {object_id}: {lifecycle!r}")
    if authority_class not in LIFECYCLES:
        raise ValueError(f"invalid authority_class for {object_id}: {authority_class!r}")
    if raw.get("authority") is True or raw.get("canon_write") is True or raw.get("settlement_authority") is True:
        raise ValueError(f"workspace projection cannot grant authority: {object_id}")
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata must be object: {object_id}")
    story_order = raw.get("story_order")
    if isinstance(story_order, bool) or (story_order is not None and not isinstance(story_order, int)):
        raise ValueError(f"story_order must be integer|null: {object_id}")
    return {
        "id": object_id,
        "section": section,
        "kind": _text(raw.get("kind"), f"{object_id}.kind"),
        "label": raw.get("label") if isinstance(raw.get("label"), str) else None,
        "source_ref": _text(raw.get("source_ref"), f"{object_id}.source_ref"),
        "source_fingerprint": _sha(raw.get("source_fingerprint"), f"{object_id}.source_fingerprint"),
        "authority_class": authority_class,
        "lifecycle": lifecycle,
        "story_order": story_order,
        "metadata": metadata,
        "authority": False,
    }


def build_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema") != INPUT_SCHEMA:
        raise ValueError(f"input schema must be {INPUT_SCHEMA}")
    project = payload.get("project")
    if not isinstance(project, dict):
        raise ValueError("project object required")
    layout = project.get("layout")
    if layout not in {"standard", "mapped"}:
        raise ValueError("project.layout must be standard|mapped")
    framework_lock = project.get("framework_lock")
    if not isinstance(framework_lock, dict):
        raise ValueError("project.framework_lock required")
    objects_raw = payload.get("objects", [])
    if not isinstance(objects_raw, list):
        raise ValueError("objects must be list")
    objects = [normalize_object(item) for item in objects_raw]
    ids = [item["id"] for item in objects]
    if len(ids) != len(set(ids)):
        raise ValueError("workspace object ids must be unique")
    objects.sort(key=lambda item: (
        item["section"],
        item["story_order"] if item["story_order"] is not None else 10**18,
        item["id"],
    ))
    sections = {section: [item for item in objects if item["section"] == section] for section in sorted(SECTIONS)}
    lifecycle_counts = {
        lifecycle: sum(1 for item in objects if item["lifecycle"] == lifecycle)
        for lifecycle in sorted(LIFECYCLES)
    }
    project_projection = {
        "project_id": _text(project.get("project_id"), "project.project_id"),
        "project_title": _text(project.get("project_title"), "project.project_title"),
        "project_version": project.get("project_version") if isinstance(project.get("project_version"), str) else None,
        "layout": layout,
        "framework_lock": framework_lock,
    }
    fingerprint_payload = {"project": project_projection, "objects": objects}
    return {
        "schema": SCHEMA,
        "workspace_fingerprint": fingerprint(fingerprint_payload),
        "project": project_projection,
        "sections": sections,
        "object_count": len(objects),
        "lifecycle_counts": lifecycle_counts,
        "authority_classes_preserved": True,
        "parallel_canon_store": False,
        "authority": False,
        "canon_write": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    objects = [
        {"id": "CHAR-A", "section": "characters", "kind": "character", "source_ref": "bible/characters/CHAR-A.md", "source_fingerprint": "sha256:" + "a" * 64, "authority_class": "locked", "lifecycle": "locked", "story_order": 0},
        {"id": "CH-1", "section": "structure", "kind": "chapter", "source_ref": "plans/chapters/CH-1.md", "source_fingerprint": "sha256:" + "b" * 64, "authority_class": "active_plan", "lifecycle": "active_plan", "story_order": 1},
        {"id": "BR-1", "section": "branches", "kind": "scenario_branch", "source_ref": "scenario:BR-1", "source_fingerprint": "sha256:" + "c" * 64, "authority_class": "scenario", "lifecycle": "scenario", "story_order": 1},
    ]
    base = {
        "schema": INPUT_SCHEMA,
        "project": {
            "project_id": "P", "project_title": "Fixture", "project_version": "0.1", "layout": "standard",
            "framework_lock": {"name": "NovelForge", "version": "0.9.0-candidate", "commit": "fixture", "bundle_fingerprint": "sha256:" + "d" * 64},
        },
        "objects": objects,
    }
    standard = build_workspace(base)
    mapped_input = json.loads(json.dumps(base))
    mapped_input["project"]["layout"] = "mapped"
    mapped_input["objects"] = list(reversed(objects))
    mapped = build_workspace(mapped_input)
    stable_order = [item["id"] for item in standard["sections"]["characters"]] == ["CHAR-A"] and mapped["object_count"] == 3
    noncanon = not standard["authority"] and not standard["canon_write"] and standard["sections"]["branches"][0]["authority"] is False
    lifecycle = standard["lifecycle_counts"]["locked"] == 1 and standard["lifecycle_counts"]["active_plan"] == 1 and standard["lifecycle_counts"]["scenario"] == 1
    guard = False
    bad = json.loads(json.dumps(base))
    bad["objects"][0]["lifecycle"] = "accepted"
    bad["objects"][0]["authority_class"] = "accepted"
    bad["objects"][0]["authority"] = True
    try:
        build_workspace(bad)
    except ValueError:
        guard = True
    ok = stable_order and noncanon and lifecycle and guard and standard["project"]["layout"] == "standard" and mapped["project"]["layout"] == "mapped"
    print(json.dumps({
        "story_workspace_contract": "PASS" if ok else "FAIL",
        "standard_and_mapped": True,
        "authority_preserved": lifecycle,
        "projection_non_authoritative": noncanon,
        "authority_escalation_guard": guard,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge Story Workspace projector")
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--input", required=True)
    build_parser.add_argument("--output")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = build_workspace(payload)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
