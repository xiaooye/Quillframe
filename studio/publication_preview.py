#!/usr/bin/env python3
"""Read-only publication preview projection for NovelForge product surfaces.

This adapter executes the deterministic publication compiler in a temporary
workspace and returns browser-safe preview material plus artifact fingerprints.
It never writes into a Project, never changes Canon/Settlement state, and never
claims that caller-supplied manuscript text is authoritative merely because its
accepted fingerprint is internally consistent.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COMPILER_PATH = ROOT / "publication" / "compiler.py"
SCHEMA = "novelforge_publication_preview_projection_v1"
PROFILE_ALIASES = {
    "text": "clean_text",
    "clean_text": "clean_text",
    "web": "web_reflow",
    "web_reflow": "web_reflow",
    "print": "print_book",
    "print_book": "print_book",
    "epub": "epub3",
    "epub3": "epub3",
}
MAX_PREVIEW_CHARS = 160_000


def _compiler() -> ModuleType:
    if not COMPILER_PATH.is_file():
        raise ValueError("publication/compiler.py is unavailable")
    spec = importlib.util.spec_from_file_location("novelforge_publication_compiler", COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("publication compiler cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _clip(value: str) -> tuple[str, bool]:
    if len(value) <= MAX_PREVIEW_CHARS:
        return value, False
    return value[:MAX_PREVIEW_CHARS], True


def _artifact_sha(report: dict[str, Any]) -> str | None:
    detail = report.get("detail")
    files = detail.get("files") if isinstance(detail, dict) else None
    if not isinstance(files, list) or not files or not isinstance(files[0], dict):
        return None
    value = files[0].get("sha256")
    return value if isinstance(value, str) else None


def _preview_from_build(profile: str, output: Path, ir: dict[str, Any]) -> dict[str, Any]:
    if profile == "clean_text":
        chunks: list[str] = []
        for chapter in ir["chapters"]:
            path = output / (str(chapter["chapter_id"]).replace("/", "-") + ".txt")
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8"))
            else:
                chunks.append(str(chapter["text"]))
        content, truncated = _clip("\n\n".join(chunks))
        return {"kind": "text", "content": content, "truncated": truncated}

    if profile in {"web_reflow", "print_book"}:
        name = "index.html" if profile == "web_reflow" else "book.html"
        content, truncated = _clip((output / name).read_text(encoding="utf-8"))
        return {"kind": "html", "content": content, "truncated": truncated}

    with zipfile.ZipFile(output) as zf:
        chapter_names = sorted(
            name for name in zf.namelist()
            if name.startswith("EPUB/chapter-") and name.endswith(".xhtml")
        )
        content = zf.read(chapter_names[0]).decode("utf-8") if chapter_names else ""
        content, truncated = _clip(content)
        return {
            "kind": "xhtml",
            "content": content,
            "truncated": truncated,
            "entry": chapter_names[0] if chapter_names else None,
        }


def build_preview(source: dict[str, Any], profile: str) -> dict[str, Any]:
    """Compile one deterministic derived preview without mutating Project state."""
    if not isinstance(source, dict):
        raise ValueError("publication source must be an object")
    compiler_profile = PROFILE_ALIASES.get(profile)
    if compiler_profile is None:
        raise ValueError("profile must be text, web, print, epub, clean_text, web_reflow, print_book, or epub3")

    compiler = _compiler()
    ir = compiler.compile_ir(source)
    with tempfile.TemporaryDirectory(prefix="novelforge-publication-preview-") as td:
        root = Path(td)
        output = root / ("book.epub" if compiler_profile == "epub3" else compiler_profile)
        report = compiler.build(ir, compiler_profile, output)
        preview = _preview_from_build(compiler_profile, output, ir)
        validation = None
        if compiler_profile == "epub3":
            validation = compiler.validate_epub(output, ir=ir)

    accepted = [
        {
            "chapter_id": chapter["chapter_id"],
            "title": chapter["title"],
            "accepted_fingerprint": chapter["accepted_fingerprint"],
        }
        for chapter in ir["chapters"]
    ]
    return {
        "schema": SCHEMA,
        "profile": profile,
        "compiler_profile": compiler_profile,
        "compiler": "publication/compiler.py",
        "source_fingerprint": ir["source_fingerprint"],
        "accepted_chapters": accepted,
        "accepted_fingerprint_guard": True,
        "source_authority_verified": False,
        "text_preservation": report.get("text_preservation"),
        "text_roundtrip": bool(report.get("detail", {}).get("text_roundtrip")),
        "artifact": {
            "sha256": _artifact_sha(report),
            "kind": "epub" if compiler_profile == "epub3" else ("html" if compiler_profile in {"web_reflow", "print_book"} else "text"),
            "derived": True,
        },
        "preview": preview,
        "validation": validation,
        "query_only": True,
        "mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "canon_authority": False,
        "settlement_authority": False,
    }


def self_test() -> dict[str, Any]:
    text = "第一段。\n\nSecond paragraph."
    accepted = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    source = {
        "book": {
            "identifier": "urn:novelforge:publication-preview-self-test",
            "title": "Preview Fixture",
            "language": "zh-CN",
            "modified": "2026-08-15T00:00:00Z",
        },
        "chapters": [{
            "chapter_id": "CH-001",
            "title": "第一章",
            "text": text,
            "accepted_fingerprint": accepted,
        }],
    }
    previews = {profile: build_preview(source, profile) for profile in ("text", "web", "print", "epub")}
    checks = {
        "all_profiles": all(value["schema"] == SCHEMA for value in previews.values()),
        "authority_false": all(value["authority"] is False for value in previews.values()),
        "no_mutation": all(value["mutation_performed"] is False for value in previews.values()),
        "no_model": all(value["model_execution"] is False for value in previews.values()),
        "exact_text_guard": all(value["accepted_fingerprint_guard"] is True and value["text_roundtrip"] is True for value in previews.values()),
        "artifact_fingerprints": all(isinstance(value["artifact"]["sha256"], str) and value["artifact"]["sha256"].startswith("sha256:") for value in previews.values()),
        "epub_internal_validation": previews["epub"]["validation"]["valid"] is True,
        "source_authority_not_invented": all(value["source_authority_verified"] is False for value in previews.values()),
    }
    return {
        "publication_preview_projection_contract": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "schema": SCHEMA,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build a read-only NovelForge publication preview projection")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--input", required=True)
    build.add_argument("--profile", required=True, choices=sorted(PROFILE_ALIASES))
    build.add_argument("--output")
    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        value = self_test()
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0 if value["publication_preview_projection_contract"] == "PASS" else 1

    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    value = build_preview(source, args.profile)
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
