#!/usr/bin/env python3
"""Build and verify deterministic NovelForge framework bundles.

The runtime bundle is an uncompressed deterministic POSIX tar. It contains a
per-file content manifest but excludes repository history, specs, generated
runtime state, caches, release attestations and bundle outputs. The overall
bundle fingerprint is SHA-256 of the exact tar bytes and is suitable for a
consumer lockfile.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SCHEMA = "novelforge_framework_bundle_v1"
CONTENT_MANIFEST = "BUNDLE_CONTENT_MANIFEST.json"
DEFAULT_INCLUDE = {
    ".claude", ".github", "assets", "core", "corpus", "docs", "evals", "harness",
    "knowledge_base", "learning", "quality", "publication", "release", "scripts", "surface",
}
ROOT_FILES = {
    ".gitignore", "AGENTS.md", "AGENTS.en.md", "AGENTS.zh-CN.md",
    "CLAUDE.md", "CLAUDE.en.md", "CLAUDE.zh-CN.md",
    "HARNESS_MANIFEST.yaml", "README.md", "README.en.md", "README.zh-CN.md",
    "SKILL.md", "SKILL.en.md", "SKILL.zh-CN.md",
    "CHANGELOG.en.md", "CHANGELOG.zh-CN.md",
    "novelforge.py", "project_sdk.py", "project_adapter.py",
}
EXCLUDE_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".novelforge", "specs"}
EXCLUDE_NAMES = {
    "framework_bundle.attestation.json", "framework-bundle.tar", "framework-bundle.manifest.json",
}
EXCLUDE_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3", ".wal", ".shm"}


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_mode(path: Path) -> int:
    # Preserve only the executable bit; all other runtime files are normalized.
    return 0o755 if os.access(path, os.X_OK) and path.suffix in {".py", ".sh"} else 0o644


def eligible(rel: Path) -> bool:
    if not rel.parts:
        return False
    if any(part in EXCLUDE_PARTS for part in rel.parts):
        return False
    if rel.name in EXCLUDE_NAMES or rel.name == CONTENT_MANIFEST:
        return False
    if rel.suffix.lower() in EXCLUDE_SUFFIXES:
        return False
    if rel.parts[0] in DEFAULT_INCLUDE:
        return True
    return rel.as_posix() in ROOT_FILES


def iter_files(root: Path) -> Iterable[tuple[Path, Path]]:
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if eligible(rel):
            yield path, rel


def content_manifest(root: Path) -> dict[str, Any]:
    files = []
    for path, rel in iter_files(root):
        data = path.read_bytes()
        files.append({
            "path": rel.as_posix(),
            "size": len(data),
            "sha256": sha256_bytes(data),
            "mode": oct(file_mode(path)),
        })
    payload = {
        "schema": BUNDLE_SCHEMA,
        "format": "deterministic-posix-tar",
        "normalization": {"mtime": 0, "uid": 0, "gid": 0, "uname": "", "gname": ""},
        "files": files,
    }
    payload["content_index_fingerprint"] = sha256_bytes(
        json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return payload


def add_bytes(tf: tarfile.TarFile, name: str, data: bytes, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data); info.mtime = 0; info.uid = 0; info.gid = 0
    info.uname = ""; info.gname = ""; info.mode = mode
    tf.addfile(info, io.BytesIO(data))


def build(root: Path, output: Path) -> dict[str, Any]:
    root = root.resolve(); output = output.resolve()
    manifest = content_manifest(root)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w", format=tarfile.PAX_FORMAT) as tf:
        for path, rel in iter_files(root):
            add_bytes(tf, rel.as_posix(), path.read_bytes(), file_mode(path))
        add_bytes(tf, CONTENT_MANIFEST, manifest_bytes)
    bundle_bytes = output.read_bytes()
    return {
        "schema": "novelforge_framework_bundle_build_v1",
        "bundle_path": str(output),
        "bundle_fingerprint": sha256_bytes(bundle_bytes),
        "bundle_size": len(bundle_bytes),
        "content_index_fingerprint": manifest["content_index_fingerprint"],
        "files": len(manifest["files"]),
        "model_execution": False,
    }


def verify(bundle: Path, expected: str | None = None) -> dict[str, Any]:
    bundle = bundle.resolve(); errors: list[str] = []
    if not bundle.is_file():
        return {"schema": "novelforge_framework_bundle_verify_v1", "valid": False, "errors": ["bundle missing"]}
    data = bundle.read_bytes(); actual = sha256_bytes(data)
    if expected and actual != expected:
        errors.append("bundle fingerprint mismatch")
    try:
        with tarfile.open(bundle, "r") as tf:
            members = tf.getmembers()
            names = [m.name for m in members]
            if len(names) != len(set(names)):
                errors.append("duplicate tar paths")
            if CONTENT_MANIFEST not in names:
                errors.append("content manifest missing")
                manifest = None
            else:
                f = tf.extractfile(CONTENT_MANIFEST)
                manifest = json.loads((f.read() if f else b"").decode("utf-8"))
            for m in members:
                if m.mtime != 0 or m.uid != 0 or m.gid != 0 or m.uname or m.gname:
                    errors.append(f"non-deterministic tar metadata: {m.name}")
            if manifest:
                if manifest.get("schema") != BUNDLE_SCHEMA:
                    errors.append("invalid content manifest schema")
                declared = {x["path"]: x for x in manifest.get("files", [])}
                payload_names = set(names) - {CONTENT_MANIFEST}
                if payload_names != set(declared):
                    errors.append("tar/content-manifest file set mismatch")
                for name, item in declared.items():
                    f = tf.extractfile(name)
                    if f is None:
                        errors.append(f"missing payload: {name}"); continue
                    b = f.read()
                    if len(b) != item.get("size") or sha256_bytes(b) != item.get("sha256"):
                        errors.append(f"payload hash/size mismatch: {name}")
    except (tarfile.TarError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"bundle parse failure: {type(exc).__name__}: {exc}")
    return {
        "schema": "novelforge_framework_bundle_verify_v1",
        "valid": not errors,
        "bundle_fingerprint": actual,
        "expected_fingerprint": expected,
        "errors": errors,
        "model_execution": False,
    }


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="novelforge-bundle-test-") as td:
        root = Path(td) / "repo"; (root / "core").mkdir(parents=True); (root / "harness").mkdir(); (root / "quality").mkdir(); (root / "publication").mkdir()
        (root / "core" / "a.txt").write_text("alpha\n", encoding="utf-8")
        (root / "harness" / "b.py").write_text("print('beta')\n", encoding="utf-8")
        (root / "quality" / "c.py").write_text("print('quality')\n", encoding="utf-8")
        (root / "publication" / "compiler.py").write_text("print('publication')\n", encoding="utf-8")
        (root / "specs").mkdir(); (root / "specs" / "ignore.md").write_text("ignore", encoding="utf-8")
        a = Path(td) / "a.tar"; b = Path(td) / "b.tar"
        ba = build(root, a); bb = build(root, b)
        same = ba["bundle_fingerprint"] == bb["bundle_fingerprint"] and a.read_bytes() == b.read_bytes()
        good = verify(a, ba["bundle_fingerprint"])
        # Tamper one payload while preserving a valid tar structure.
        with tarfile.open(a, "r") as tf:
            manifest = json.loads(tf.extractfile(CONTENT_MANIFEST).read().decode("utf-8"))
            payloads = {m.name: tf.extractfile(m).read() for m in tf.getmembers() if m.isfile() and m.name != CONTENT_MANIFEST}
        tampered = Path(td) / "tampered.tar"
        with tarfile.open(tampered, "w", format=tarfile.PAX_FORMAT) as tf:
            for name in sorted(payloads):
                content = payloads[name] + (b"tamper" if name == "core/a.txt" else b"")
                add_bytes(tf, name, content)
            add_bytes(tf, CONTENT_MANIFEST, (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        bad = verify(tampered)
        excluded = all(x["path"] != "specs/ignore.md" for x in manifest["files"])
        quality_included = any(x["path"] == "quality/c.py" for x in manifest["files"])
        publication_included = any(x["path"] == "publication/compiler.py" for x in manifest["files"])
        ok = same and good["valid"] and not bad["valid"] and excluded and quality_included and publication_included
    return {
        "framework_bundle_contract": "PASS" if ok else "FAIL",
        "deterministic_bytes": same,
        "verification_passes": good["valid"],
        "tamper_detected": not bad["valid"],
        "specs_excluded": excluded,
        "quality_runtime_included": quality_included,
        "publication_runtime_included": publication_included,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge deterministic framework bundle")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--root", default=str(ROOT)); b.add_argument("--output", required=True); b.add_argument("--report")
    v = sub.add_parser("verify"); v.add_argument("--bundle", required=True); v.add_argument("--expected"); v.add_argument("--report")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test": result = self_test()
    elif args.cmd == "build": result = build(Path(args.root), Path(args.output))
    else: result = verify(Path(args.bundle), args.expected)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    report = getattr(args, "report", None)
    if report: Path(report).write_text(text, encoding="utf-8")
    print(text, end="")
    if args.cmd == "self-test": return 0 if result["framework_bundle_contract"] == "PASS" else 1
    if args.cmd == "verify": return 0 if result["valid"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
