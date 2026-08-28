#!/usr/bin/env python3
"""Canonical parser and context owner for a Quillframe Project.

The Project contract is deliberately small and hard-cut: the root manifest is
exactly four scalar keys and durable Project state lives below
``<project>/.quillframe/data``. This module is the only runtime parser for
that contract. It never opens or creates the data boundary while resolving.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
import tomllib

PROJECT_SCHEMA = "quillframe_project_v1_0"
PROJECT_SCOPE = "novel"
MANIFEST_NAME = "quillframe.toml"
DATA_RELATIVE = Path(".quillframe") / "data"
MANIFEST_KEYS = {"schema", "id", "title", "language"}
CONTEXT_SCHEMA = "quillframe_project_context_v1_0"
PROJECT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def fingerprint_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _load_toml(root: Path) -> dict[str, Any]:
    path = root / MANIFEST_NAME
    if not path.is_file():
        raise ValueError(f"missing {MANIFEST_NAME}")
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid {MANIFEST_NAME}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{MANIFEST_NAME} must parse to object")
    return value


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def validate_project_id(value: Any) -> str:
    """Validate the one bounded Project identity grammar used by all callers."""
    if not isinstance(value, str) or not PROJECT_ID_PATTERN.fullmatch(value):
        raise ValueError("id must start with ASCII letter/digit and contain only ASCII letters, digits, '.', '_' or '-', with length 1..64")
    return value


def _validate_manifest(value: dict[str, Any]) -> dict[str, str]:
    keys = set(value)
    missing = sorted(MANIFEST_KEYS - keys)
    extra = sorted(keys - MANIFEST_KEYS)
    if missing or extra:
        raise ValueError(f"quillframe.toml must contain exactly four root keys; missing={missing}, extra={extra}")

    manifest = {key: _require_text(value[key], key) for key in MANIFEST_KEYS if key != "id"}
    manifest["id"] = validate_project_id(value["id"])
    if manifest["schema"] != PROJECT_SCHEMA:
        raise ValueError(f"schema must be exactly {PROJECT_SCHEMA}")
    return {key: manifest[key] for key in ("schema", "id", "title", "language")}


def _reject_legacy_metadata(root: Path) -> None:
    for name in ("quillframe.lock.json", "framework.attestation.json"):
        if (root / name).exists():
            raise ValueError(f"legacy metadata is rejected: {name}")


def resolve_contract(root: Path) -> dict[str, Any]:
    """Parse and normalize one Project without touching its data boundary."""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project root is not a directory: {root}")
    manifest_path = root / MANIFEST_NAME
    manifest = _validate_manifest(_load_toml(root))
    try:
        raw_manifest = manifest_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read {MANIFEST_NAME}: {exc}") from exc
    # Check legacy files before returning a usable context. Callers must do
    # this before opening or creating any Project database.
    _reject_legacy_metadata(root)
    data_root = (root / DATA_RELATIVE).resolve()
    if root not in data_root.parents:
        raise ValueError("Project data boundary escapes project root")
    return {
        "context_schema": CONTEXT_SCHEMA,
        "manifest": manifest,
        "manifest_fingerprint": fingerprint(manifest),
        "manifest_raw_fingerprint": fingerprint_bytes(raw_manifest),
        "project_id": manifest["id"],
        "project_title": manifest["title"],
        "language": manifest["language"],
        "scope": PROJECT_SCOPE,
        "project_root": str(root),
        "data_root": str(data_root),
    }


def validate(root: Path) -> dict[str, Any]:
    try:
        return {"valid": True, "errors": [], "resolution": resolve_contract(root)}
    except Exception as exc:
        return {"valid": False, "errors": [f"{type(exc).__name__}: {exc}"], "resolution": None}


def self_test(tmp: Path) -> dict[str, Any]:
    import shutil

    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    manifest_text = (
        'schema = "quillframe_project_v1_0"\n'
        'id = "PROJECT-TEST"\n'
        'title = "Fixture"\n'
        'language = "en"\n'
    )
    (tmp / MANIFEST_NAME).write_text(manifest_text, encoding="utf-8")
    resolution = resolve_contract(tmp)
    extra = tmp / "extra"
    extra.mkdir()
    (extra / MANIFEST_NAME).write_text(manifest_text + 'extra = "no"\n', encoding="utf-8")
    extra_rejected = not validate(extra)["valid"]
    stale = tmp / "stale"
    stale.mkdir()
    (stale / MANIFEST_NAME).write_text(manifest_text, encoding="utf-8")
    (stale / "quillframe.lock.json").write_text("{}\n", encoding="utf-8")
    stale_rejected = not validate(stale)["valid"]
    passed = resolution["manifest"]["schema"] == PROJECT_SCHEMA and resolution["scope"] == PROJECT_SCOPE and extra_rejected and stale_rejected
    return {
        "project_resolution_contract": "PASS" if passed else "FAIL",
        "exact_four_key_manifest": True,
        "scope": PROJECT_SCOPE,
        "legacy_metadata_rejected": stale_rejected,
        "data_boundary": resolution["data_root"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe exact flat Project resolver")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for command in ("resolve", "validate"):
        child = sub.add_parser(command)
        child.add_argument("path")
    test = sub.add_parser("self-test")
    test.add_argument("--tmp", default="/tmp/quillframe-project-resolution-self-test")
    args = parser.parse_args()
    if args.cmd == "self-test":
        result = self_test(Path(args.tmp))
        dump(result)
        return 0 if result["project_resolution_contract"] == "PASS" else 1
    root = Path(args.path)
    if args.cmd == "resolve":
        dump(resolve_contract(root))
        return 0
    if args.cmd == "validate":
        result = validate(root)
        dump(result)
        return 0 if result["valid"] else 1
    result = validate(root)
    dump(result)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
