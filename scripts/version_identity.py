#!/usr/bin/env python3
"""Enforce one current Quillframe Framework version identity.

Quillframe is still pre-1.0 and latest ``main`` is the development baseline, but
public machine/version surfaces must not drift independently. This checker is
stdlib-only, deterministic, and performs no release promotion or model work.
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEMVER = r"([0-9]+\.[0-9]+\.[0-9]+)"

VERSION_FILE = ROOT / "VERSION"
FRAMEWORK_MANIFEST = ROOT / "HARNESS_MANIFEST.yaml"
SKILL_ENTRY = ROOT / "SKILL.md"
CLI_ENTRY = ROOT / "quillframe.py"
PROJECT_SDK = ROOT / "project_sdk.py"
MCP_STDIO = ROOT / "harness" / "control_plane" / "mcp_stdio.py"
DOC_MANIFEST = ROOT / "docs" / "documentation_manifest.json"
DOC_MANIFEST_FULL = ROOT / "docs" / "quillframe_documentation_manifest.json"
PYPROJECT = ROOT / "pyproject.toml"
SITE_PACKAGE = ROOT / "site" / "package.json"
STUDIO_PACKAGE = ROOT / "studio" / "app" / "package.json"
TAURI_CARGO = ROOT / "studio" / "app" / "src-tauri" / "Cargo.toml"
TAURI_CONFIG = ROOT / "studio" / "app" / "src-tauri" / "tauri.conf.json"
HOST_BRIDGE = ROOT / "studio" / "host_bridge.py"
HOST_BRIDGE_CONTRACT = ROOT / "studio" / "host_bridge_contract.json"
SITE_PRODUCT = ROOT / "site" / "src" / "ProductApp.tsx"
DOCS_TITLE = ROOT / "site" / "docs-site" / "src" / "components" / "QuillframeSiteTitle.astro"
AI_CATALOG = ROOT / "site" / "public" / ".well-known" / "ai-catalog.json"

VERSION_LINE_RE = re.compile(rf"(?m)^\s*version:\s*[\"']?{SEMVER}[\"']?\s*$")
CLI_VERSION_RE = re.compile(rf"(?m)^FRAMEWORK_VERSION\s*=\s*[\"']{SEMVER}[\"']\s*$")
SDK_VERSION_RE = re.compile(rf"(?m)^DEFAULT_FRAMEWORK_VERSION\s*=\s*[\"']{SEMVER}[\"']\s*$")
MCP_VERSION_RE = re.compile(
    rf"SERVER_INFO\s*=\s*\{{.*?[\"']version[\"']\s*:\s*[\"']{SEMVER}[\"']",
    re.S,
)
HOST_BRIDGE_VERSION_RE = re.compile(rf"[\"']framework_version[\"']\s*:\s*[\"']{SEMVER}[\"']")
SITE_PRODUCT_VERSION_RE = re.compile(rf"const\s+productVersion\s*=\s*[\"']{SEMVER}[\"']")
DOCS_TITLE_VERSION_RE = re.compile(rf"aria-label=[\"']Quillframe\s+{SEMVER}[\"']")
README_SUBLINE_RE = re.compile(rf"<sub>{SEMVER}\s+·")


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


def json_field_version(path: Path, field: str, label: str) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, f"{path.relative_to(ROOT)}: missing {label} version surface"
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{path.relative_to(ROOT)}: invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, f"{path.relative_to(ROOT)}: root must be an object"
    value = payload.get(field)
    if not isinstance(value, str) or not re.fullmatch(SEMVER, value):
        return None, f"{path.relative_to(ROOT)}: {field} must be SemVer X.Y.Z"
    return value, None


def toml_field_version(path: Path, table: str, field: str, label: str) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, f"{path.relative_to(ROOT)}: missing {label} version surface"
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return None, f"{path.relative_to(ROOT)}: invalid TOML: {exc}"
    value = (payload.get(table) or {}).get(field)
    if not isinstance(value, str) or not re.fullmatch(SEMVER, value):
        return None, f"{path.relative_to(ROOT)}: {table}.{field} must be SemVer X.Y.Z"
    return value, None


def version_file() -> tuple[str | None, str | None]:
    try:
        value = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return None, f"VERSION: cannot read version authority: {exc}"
    if not re.fullmatch(SEMVER, value):
        return None, "VERSION: must be SemVer X.Y.Z"
    return value, None


def main() -> int:
    probes = {
        "VERSION": version_file(),
        "HARNESS_MANIFEST.yaml": parse_text_version(FRAMEWORK_MANIFEST, VERSION_LINE_RE, "Framework manifest"),
        "SKILL.md": parse_text_version(SKILL_ENTRY, VERSION_LINE_RE, "Skill metadata"),
        "quillframe.py": parse_text_version(CLI_ENTRY, CLI_VERSION_RE, "CLI Framework"),
        "project_sdk.py": parse_text_version(PROJECT_SDK, SDK_VERSION_RE, "Project SDK default Framework"),
        "harness/control_plane/mcp_stdio.py": parse_text_version(MCP_STDIO, MCP_VERSION_RE, "MCP server"),
        "pyproject.toml": toml_field_version(PYPROJECT, "project", "version", "Python package"),
        "site/package.json": json_field_version(SITE_PACKAGE, "version", "site package"),
        "studio/app/package.json": json_field_version(STUDIO_PACKAGE, "version", "Studio package"),
        "studio/app/src-tauri/Cargo.toml": toml_field_version(TAURI_CARGO, "package", "version", "Tauri package"),
        "studio/app/src-tauri/tauri.conf.json": json_field_version(TAURI_CONFIG, "version", "Tauri config"),
        "studio/host_bridge.py": parse_text_version(HOST_BRIDGE, HOST_BRIDGE_VERSION_RE, "Host Bridge"),
        "studio/host_bridge_contract.json": json_field_version(HOST_BRIDGE_CONTRACT, "framework_version", "Host Bridge contract"),
        "docs/documentation_manifest.json": json_field_version(DOC_MANIFEST, "framework_version", "documentation manifest"),
        "docs/quillframe_documentation_manifest.json": json_field_version(DOC_MANIFEST_FULL, "framework_version", "full documentation manifest"),
        "README.md": parse_text_version(ROOT / "README.md", README_SUBLINE_RE, "README release"),
        "README.en.md": parse_text_version(ROOT / "README.en.md", README_SUBLINE_RE, "English README release"),
        "README.zh-CN.md": parse_text_version(ROOT / "README.zh-CN.md", README_SUBLINE_RE, "Chinese README release"),
        "site/src/ProductApp.tsx": parse_text_version(SITE_PRODUCT, SITE_PRODUCT_VERSION_RE, "product shell"),
        "site/docs-site/src/components/QuillframeSiteTitle.astro": parse_text_version(DOCS_TITLE, DOCS_TITLE_VERSION_RE, "docs shell"),
        "site/public/.well-known/ai-catalog.json": json_field_version(AI_CATALOG, "version_line", "AI catalog"),
    }

    versions = {name: value for name, (value, _) in probes.items() if value is not None}
    errors = [problem for _, problem in probes.values() if problem is not None]
    authority = versions.get("VERSION")
    if authority is not None:
        for name, value in versions.items():
            if value != authority:
                errors.append(
                    f"{name}: framework version identity mismatch: {value!r} != VERSION {authority!r}"
                )

    result = {
        "schema": "quillframe_version_identity_check_v1",
        "version_identity_contract": "PASS" if not errors else "FAIL",
        "authority": "VERSION",
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
