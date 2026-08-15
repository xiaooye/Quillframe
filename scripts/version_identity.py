#!/usr/bin/env python3
"""Enforce one current NovelForge Framework version identity.

NovelForge is still pre-1.0 and latest ``main`` is the development baseline, but
public machine/version surfaces must not drift independently. This checker is
stdlib-only, deterministic, and performs no release promotion or model work.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEMVER = r"([0-9]+\.[0-9]+\.[0-9]+)"

FRAMEWORK_MANIFEST = ROOT / "HARNESS_MANIFEST.yaml"
SKILL_ENTRY = ROOT / "SKILL.md"
CLI_ENTRY = ROOT / "novelforge.py"
PROJECT_SDK = ROOT / "project_sdk.py"
MCP_STDIO = ROOT / "harness" / "control_plane" / "mcp_stdio.py"
DOC_MANIFEST = ROOT / "docs" / "documentation_manifest.json"

VERSION_LINE_RE = re.compile(rf"(?m)^\s*version:\s*[\"']?{SEMVER}[\"']?\s*$")
CLI_VERSION_RE = re.compile(rf"(?m)^FRAMEWORK_VERSION\s*=\s*[\"']{SEMVER}[\"']\s*$")
SDK_VERSION_RE = re.compile(rf"(?m)^DEFAULT_FRAMEWORK_VERSION\s*=\s*[\"']{SEMVER}[\"']\s*$")
MCP_VERSION_RE = re.compile(
    rf"SERVER_INFO\s*=\s*\{{.*?[\"']version[\"']\s*:\s*[\"']{SEMVER}[\"']",
    re.S,
)


def parse_text_version(path: Path, pattern: re.Pattern[str], label: str) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, f"{path.relative_to(ROOT)}: missing {label} version surface"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{path.relative_to(ROOT)}: cannot read {label} version surface: {exc}"
    match = pattern.search(text)
    if not match:
        return None, f"{path.relative_to(ROOT)}: cannot parse {label} version"
    return match.group(1), None


def doc_manifest_version() -> tuple[str | None, str | None]:
    if not DOC_MANIFEST.exists():
        return None, "docs/documentation_manifest.json: missing documentation manifest"
    try:
        payload: Any = json.loads(DOC_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"docs/documentation_manifest.json: invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "docs/documentation_manifest.json: root must be an object"
    value = payload.get("framework_version")
    if not isinstance(value, str) or not re.fullmatch(SEMVER, value):
        return None, "docs/documentation_manifest.json: framework_version must be SemVer X.Y.Z"
    return value, None


def main() -> int:
    probes = {
        "HARNESS_MANIFEST.yaml": parse_text_version(FRAMEWORK_MANIFEST, VERSION_LINE_RE, "Framework manifest"),
        "SKILL.md": parse_text_version(SKILL_ENTRY, VERSION_LINE_RE, "Skill metadata"),
        "novelforge.py": parse_text_version(CLI_ENTRY, CLI_VERSION_RE, "CLI Framework"),
        "project_sdk.py": parse_text_version(PROJECT_SDK, SDK_VERSION_RE, "Project SDK default Framework"),
        "harness/control_plane/mcp_stdio.py": parse_text_version(MCP_STDIO, MCP_VERSION_RE, "MCP server"),
        "docs/documentation_manifest.json": doc_manifest_version(),
    }

    versions = {name: value for name, (value, _) in probes.items() if value is not None}
    errors = [problem for _, problem in probes.values() if problem is not None]
    authority = versions.get("HARNESS_MANIFEST.yaml")
    if authority is not None:
        for name, value in versions.items():
            if value != authority:
                errors.append(
                    f"{name}: framework version identity mismatch: {value!r} != HARNESS_MANIFEST.yaml {authority!r}"
                )

    result = {
        "schema": "novelforge_version_identity_check_v1",
        "version_identity_contract": "PASS" if not errors else "FAIL",
        "authority": "HARNESS_MANIFEST.yaml",
        "framework_version": authority,
        "surfaces": versions,
        "errors": errors,
        "latest_main_is_development_baseline": True,
        "release_promotion_performed": False,
        "model_execution": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
