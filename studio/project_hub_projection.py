#!/usr/bin/env python3
"""Read-only Studio projection for the native Quillframe Project context.

The resolver owns the Project contract. Studio receives only the context
identity and safe relative data-boundary evidence; host/action provenance is
not consumer Project identity and is intentionally not projected here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import re
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "quillframe_project_context_v1_0"
OUTPUT_SCHEMA = "quillframe_studio_project_hub_projection_v1"
PROJECT_SCHEMA = "quillframe_project_v1_0"
PROJECT_SCOPE = "novel"
SURFACES = {"cli", "local_app", "cloud_ui", "agent_package"}
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _require_context(source: dict[str, Any]) -> dict[str, Any]:
    if source.get("context_schema") != SOURCE_SCHEMA:
        raise ValueError(f"expected context schema {SOURCE_SCHEMA}")
    manifest = source.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("Project context manifest must be an object")
    if set(manifest) != {"schema", "id", "title", "language"}:
        raise ValueError("Project context manifest must contain exactly four keys")
    if manifest.get("schema") != PROJECT_SCHEMA:
        raise ValueError(f"manifest schema must be exactly {PROJECT_SCHEMA}")
    project_id = manifest.get("id")
    title = manifest.get("title")
    language = manifest.get("language")
    if not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("Project context id is not a native project id")
    if not isinstance(title, str) or not title.strip() or not isinstance(language, str) or not language.strip():
        raise ValueError("Project context title/language must be non-empty text")
    normalized_manifest = {"schema": PROJECT_SCHEMA, "id": project_id, "title": title.strip(), "language": language.strip()}
    if source.get("project_id") != normalized_manifest["id"]:
        raise ValueError("Project context id does not match manifest")
    if source.get("project_title") != normalized_manifest["title"]:
        raise ValueError("Project context title does not match manifest")
    if source.get("language") != normalized_manifest["language"]:
        raise ValueError("Project context language does not match manifest")
    if source.get("scope") != PROJECT_SCOPE:
        raise ValueError("Project context must declare novel scope")
    manifest_fp = source.get("manifest_fingerprint")
    if not isinstance(manifest_fp, str) or manifest_fp != fingerprint(normalized_manifest):
        raise ValueError("Project context manifest fingerprint does not match manifest")
    return {**source, "manifest": normalized_manifest, "project_title": normalized_manifest["title"], "language": normalized_manifest["language"], "manifest_fingerprint": manifest_fp}


def build_projection(source: dict[str, Any], surface: str = "cloud_ui") -> dict[str, Any]:
    context = _require_context(source)
    if surface not in SURFACES:
        raise ValueError("surface must be one of: " + ", ".join(sorted(SURFACES)))

    projection: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "source_schema": SOURCE_SCHEMA,
        "source_fingerprint": fingerprint(context),
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
            "arbitrary_policy_passthrough": False,
        },
        "project": {
            "id": context["project_id"],
            "title": context["project_title"],
            "language": context["language"],
            "scope": context["scope"],
            "manifest_fingerprint": context["manifest_fingerprint"],
            "schema": context["manifest"]["schema"],
        },
        "data_boundary": {
            "relative": ".quillframe/data",
            "fixed": True,
            "absolute_path_exposed": False,
        },
        "unavailable": [
            "authority_policy_details",
            "quality_policy_details",
            "current_chapter",
            "current_scene",
            "manuscript_lifecycle",
            "latest_run",
            "publication_status",
            "quality_status",
            "host_action_provenance",
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
    private_marker = "/private/host/path/never-expose"
    source = {
        "context_schema": SOURCE_SCHEMA,
        "manifest": {
            "schema": PROJECT_SCHEMA,
            "id": "PROJECT-SYNTHETIC",
            "title": "Synthetic Story Loom",
            "language": "en",
        },
        "manifest_fingerprint": fingerprint({
            "schema": PROJECT_SCHEMA,
            "id": "PROJECT-SYNTHETIC",
            "title": "Synthetic Story Loom",
            "language": "en",
        }),
        "project_id": "PROJECT-SYNTHETIC",
        "project_title": "Synthetic Story Loom",
        "language": "en",
        "scope": PROJECT_SCOPE,
        "project_root": private_marker,
        "data_root": private_marker + "/.quillframe/data",
    }
    first = build_projection(source, "cloud_ui")
    second = build_projection(source, "cloud_ui")
    serialized = canonical(first)

    wrong_schema_rejected = False
    try:
        build_projection({"context_schema": "wrong"})
    except ValueError:
        wrong_schema_rejected = True

    legacy_markers = ("framework" + "_lock", "framework" + "_attestation", "project" + "_version", "lay" + "out")
    checks = {
        "source_schema_rejected": wrong_schema_rejected,
        "authority_false": first["authority"] is False,
        "native_project_schema": first["project"]["schema"] == PROJECT_SCHEMA,
        "novel_scope": first["project"]["scope"] == PROJECT_SCOPE,
        "no_project_root": "project_root" not in serialized,
        "no_data_root_absolute": "data_root" not in serialized,
        "no_absolute_or_private_paths": private_marker not in serialized,
        "no_legacy_authority": all(key not in serialized for key in legacy_markers),
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
    parser = argparse.ArgumentParser(description="Build a safe Quillframe Studio Project Hub projection")
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
