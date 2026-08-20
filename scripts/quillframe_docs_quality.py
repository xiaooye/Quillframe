#!/usr/bin/env python3
"""Deterministic Quillframe public-documentation checks.

The zh-CN check detects untranslated prose while allowing exact technical names and
identifiers to remain embedded in otherwise native Chinese documentation.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_MANIFEST = ROOT / "docs/quillframe_documentation_manifest.json"
DOC_ASSETS = ROOT / "docs/assets"
ERRORS: list[str] = []

FOREIGN_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9+._-]*)(?![A-Za-z0-9_])")
FENCED_CODE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MARKDOWN_TARGET_RE = re.compile(r"\]\((?:[^()]|\([^)]*\))*\)")
URL_RE = re.compile(r"https?://\S+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
ALT_RE = re.compile(r"\balt=[\"']([^\"']*)[\"']", re.I)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
ENGLISH_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z'-]*\b")

# Proper names and standards that are normal to retain in Chinese technical prose.
ALLOWED_FOREIGN = {
    "quillframe", "github", "python", "json", "svg", "utf-8", "utf",
    "mcp", "godot", "solidjs", "react", "vue", "sha256", "html", "css",
}


def err(message: str) -> None:
    ERRORS.append(message)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        err(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return {}


def prose_only(text: str) -> str:
    text = FENCED_CODE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = MARKDOWN_TARGET_RE.sub("]", text)
    text = HTML_TAG_RE.sub(" ", text)
    return text


def foreign_tokens(text: str) -> list[str]:
    found: list[str] = []
    for token in FOREIGN_TOKEN_RE.findall(text):
        low = token.lower()
        if low in ALLOWED_FOREIGN:
            continue
        if len(token) == 1 or re.fullmatch(r"[A-Z]\d*", token):
            continue
        found.append(token)
    return found


def check_native_chinese(path: Path, text: str) -> None:
    prose = prose_only(text)
    cjk_count = len(CJK_RE.findall(prose))
    latin_count = sum(len(word) for word in ENGLISH_WORD_RE.findall(prose))
    if cjk_count == 0:
        err(f"{path.relative_to(ROOT)}: zh-CN document contains no Chinese prose")
    elif cjk_count / max(1, cjk_count + latin_count) < 0.08:
        err(f"{path.relative_to(ROOT)}: zh-CN document is dominated by untranslated English prose")

    for paragraph in re.split(r"\n\s*\n", prose):
        normalized = " ".join(paragraph.split())
        if len(normalized) < 80 or CJK_RE.search(normalized):
            continue
        if normalized.startswith(("-", "*", "|")) or "&nbsp;" in normalized:
            continue
        if len(ENGLISH_WORD_RE.findall(normalized)) >= 10:
            err(f"{path.relative_to(ROOT)}: untranslated English paragraph: {normalized[:100]!r}")
    for alt in ALT_RE.findall(text):
        if not CJK_RE.search(alt) and len(ENGLISH_WORD_RE.findall(alt)) >= 8:
            err(f"{path.relative_to(ROOT)}: untranslated English alt text: {alt!r}")


def check_public(manifest: dict) -> None:
    retired_public_brand = "Novel" + "Forge"
    if manifest.get("schema") != "quillframe_public_documentation_manifest_v2":
        err("public manifest schema must be quillframe_public_documentation_manifest_v2")
    expected_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if manifest.get("framework_version") != expected_version:
        err("public manifest framework_version must match VERSION")
    if manifest.get("public_brand") != "Quillframe":
        err("public manifest brand must be Quillframe")
    if manifest.get("technical_namespace") != "quillframe":
        err("technical namespace must remain quillframe")
    if manifest.get("governance_registry") != "docs/documentation_manifest.json":
        err("public manifest must identify the documentation governance registry")
    if "legacy_technical_namespace" in manifest or "compatibility_registry" in manifest:
        err("pre-1.0 documentation manifest fields are forbidden")
    if manifest.get("chinese_style") != "native_zh_CN_prose_exact_identifiers_only":
        err("public manifest must declare native zh-CN prose policy")

    for pair in manifest.get("current_pairs", []):
        if not isinstance(pair, list) or len(pair) != 2:
            err("current_pairs entry must be [en, zh-CN]")
            continue
        for raw in pair:
            path = ROOT / raw
            if not path.exists():
                err(f"{raw}: missing public-current document")
                continue
            text = path.read_text(encoding="utf-8")
            if "Quillframe" not in text:
                err(f"{raw}: current public surface does not name Quillframe")
            for line_no, line in enumerate(text.splitlines(), 1):
                if retired_public_brand in line:
                    low = line.lower()
                    if not ("histor" in low or "former" in low or "旧" in line or "曾用" in line):
                        err(f"{raw}:{line_no}: retired public brand outside historical context")
        zh = ROOT / pair[1]
        if zh.exists():
            check_native_chinese(zh, zh.read_text(encoding="utf-8"))


def check_svg(path: Path) -> None:
    retired_public_brand = "Novel" + "Forge"
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except Exception as exc:
        err(f"{path.relative_to(ROOT)}: malformed SVG: {exc}")
        return
    if not root.attrib.get("viewBox"):
        err(f"{path.relative_to(ROOT)}: missing viewBox")
    for tag in ("title", "desc"):
        elements = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == tag]
        if not elements or not "".join(elements[0].itertext()).strip():
            err(f"{path.relative_to(ROOT)}: missing <{tag}>")
    raw = path.read_text(encoding="utf-8")
    if "@font-face" in raw or re.search(r"\.(?:woff2?|ttf|otf)\b", raw, re.I):
        err(f"{path.relative_to(ROOT)}: embedded font forbidden")
    if retired_public_brand in raw:
        err(f"{path.relative_to(ROOT)}: retired public brand in current SVG")

    if path.name.endswith(".zh-CN.svg"):
        visible_parts: list[str] = []
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            if tag in {"title", "desc", "text"}:
                visible_parts.append("".join(element.itertext()))
        tokens = foreign_tokens("\n".join(visible_parts))
        if tokens:
            unique = ", ".join(sorted(set(tokens), key=str.lower))
            err(f"{path.relative_to(ROOT)}: ordinary English token(s) in zh-CN SVG: {unique}")


def check_assets(manifest: dict) -> None:
    svgs = sorted(DOC_ASSETS.rglob("*.svg")) if DOC_ASSETS.exists() else []
    if len(svgs) < 25:
        err(f"docs/assets: expected >=25 SVGs, found {len(svgs)}")
    for path in svgs:
        check_svg(path)
    names = {path.name for path in svgs}
    for stem in manifest.get("canonical_diagrams", []):
        for lang in ("en", "zh-CN"):
            if f"{stem}.{lang}.svg" not in names:
                err(f"missing {stem}.{lang}.svg")


def main() -> int:
    manifest = load_json(PUBLIC_MANIFEST)
    check_public(manifest)
    check_assets(manifest)
    for raw in manifest.get("audit_files", []):
        path = ROOT / raw
        if not path.exists():
            err(f"{raw}: missing")
        else:
            load_json(path)
    if ERRORS:
        for item in ERRORS:
            print("ERROR:", item)
        print(f"quillframe-docs-quality: {len(ERRORS)} error(s)")
        return 1
    print("quillframe-docs-quality: 0 error(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
