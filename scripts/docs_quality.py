#!/usr/bin/env python3
"""Deterministic documentation QA for NovelForge.

This checker intentionally performs no semantic/model judgment and is safe for
normal CI. It catches objective source and layout-risk regressions; rendered
visual inspection and native-language copy review remain mandatory per
``docs/DOCUMENTATION_QA.*``.
"""
from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ROOT_READMES = [ROOT / "README.md", ROOT / "README.en.md", ROOT / "README.zh-CN.md"]
UI_DIR = ROOT / "assets" / "ui"
TARGET_GITHUB_WIDTH = 820.0
MIN_RENDERED_TEXT_PX = 12.0
LONG_TEXT_CHARS = 24

ERRORS: list[str] = []
WARNINGS: list[str] = []

HEX_RE = re.compile(r"^(?:#[0-9A-Fa-f]{3}|#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{8})$")
CSS_HEX_RE = re.compile(r"#([0-9A-Za-z]+)")
ARROW_BLOCK_RE = re.compile(r"```text\s*\n(?:(?!```).)*(?:→|\s->\s)(?:(?!```).)*```", re.S)
MD_LINK_RE = re.compile(r"(?:!\[[^\]]*\]|\[[^\]]*\])\(([^)]+)\)")
HTML_LINK_RE = re.compile(r"\b(?:src|href)=[\"']([^\"']+)[\"']", re.I)
NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", re.I)
FONT_SHORTHAND_RE = re.compile(r"\bfont\s*:\s*[^;{}]*?\b(\d+(?:\.\d+)?)px\b", re.I)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def error(path: Path, message: str) -> None:
    ERRORS.append(f"{rel(path)}: {message}")


def warn(path: Path, message: str) -> None:
    WARNINGS.append(f"{rel(path)}: {message}")


def local_target(source: Path, raw: str) -> Path | None:
    raw = raw.strip()
    if not raw or raw.startswith(("http://", "https://", "mailto:", "#", "data:")):
        return None
    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1]
    raw = unquote(raw.split("#", 1)[0].split("?", 1)[0])
    if not raw:
        return None
    return (source.parent / raw).resolve()


def check_markdown(path: Path) -> None:
    if not path.exists():
        error(path, "missing required root README")
        return
    text = path.read_text(encoding="utf-8")
    if ARROW_BLOCK_RE.search(text):
        error(path, "Tier-A landing page contains a fenced arrow-process block; use a designed module or structured prose fallback")

    for match in list(MD_LINK_RE.finditer(text)) + list(HTML_LINK_RE.finditer(text)):
        target = local_target(path, match.group(1))
        if target is None:
            continue
        try:
            target.relative_to(ROOT)
        except ValueError:
            error(path, f"local link escapes repository: {match.group(1)}")
            continue
        if not target.exists():
            error(path, f"broken local link/asset: {match.group(1)}")

    if path.name == "README.zh-CN.md":
        # Advisory only. Product names and exact protocol identifiers can remain English.
        risky = {
            "reviewer shopping": "prefer a native Chinese explanation; preserve only an exact normative identifier when needed",
            "semantic reject": "prefer Chinese prose with `semantic_reject` only as the exact identifier",
            "consumer project": "prefer 下游项目",
            "Human-facing": "prefer 人类可读 / 面向用户",
            "Generic Framework": "prefer 通用框架 in explanatory prose",
        }
        for phrase, note in risky.items():
            if phrase in text:
                warn(path, f"Chinese copy contains '{phrase}': {note}")


def parse_viewbox(path: Path, root: ET.Element) -> tuple[float, float, float, float] | None:
    raw = root.attrib.get("viewBox")
    if not raw:
        error(path, "SVG is missing viewBox")
        return None
    parts = re.split(r"[\s,]+", raw.strip())
    if len(parts) != 4:
        error(path, f"invalid viewBox: {raw!r}")
        return None
    try:
        x, y, w, h = map(float, parts)
    except ValueError:
        error(path, f"non-numeric viewBox: {raw!r}")
        return None
    if w <= 0 or h <= 0:
        error(path, f"viewBox must have positive size: {raw!r}")
        return None
    return x, y, w, h


def element_text(el: ET.Element) -> str:
    return "".join(el.itertext()).strip()


def css_class_font_sizes(root: ET.Element) -> dict[str, float]:
    result: dict[str, float] = {}
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] != "style":
            continue
        css = el.text or ""
        for selector, body in re.findall(r"\.([A-Za-z0-9_-]+)\s*\{([^}]+)\}", css):
            match = FONT_SIZE_RE.search(body) or FONT_SHORTHAND_RE.search(body)
            if match:
                result[selector] = float(match.group(1))
    return result


def inherited_font_size(el: ET.Element, class_sizes: dict[str, float]) -> float | None:
    raw = el.attrib.get("font-size")
    if raw:
        raw = raw.removesuffix("px")
        try:
            return float(raw)
        except ValueError:
            return None
    for cls in el.attrib.get("class", "").split():
        if cls in class_sizes:
            return class_sizes[cls]
    style = el.attrib.get("style", "")
    match = FONT_SIZE_RE.search(style) or FONT_SHORTHAND_RE.search(style)
    return float(match.group(1)) if match else None


def char_em_width(ch: str) -> float:
    if ch.isspace():
        return 0.34
    if unicodedata.east_asian_width(ch) in {"W", "F"}:
        return 1.0
    category = unicodedata.category(ch)
    if category.startswith("P"):
        return 0.38
    if ch.isupper():
        return 0.66
    if ch.isdigit():
        return 0.56
    return 0.54


def estimated_width(text: str, font_size: float) -> float:
    return sum(char_em_width(ch) for ch in text) * font_size


def numeric_attr(el: ET.Element, name: str) -> float | None:
    raw = el.attrib.get(name)
    if raw is None:
        return None
    raw = raw.split()[0]
    return float(raw) if NUM_RE.fullmatch(raw) else None


def check_svg(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        error(path, f"malformed SVG/XML: {exc}")
        return

    vb = parse_viewbox(path, root)
    title = next((el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "title"), None)
    desc = next((el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "desc"), None)
    if title is None or not element_text(title):
        error(path, "product UI SVG requires non-empty <title>")
    if desc is None or not element_text(desc):
        error(path, "product UI SVG requires non-empty <desc>")

    for el in root.iter():
        for attr in ("fill", "stroke", "color", "stop-color", "flood-color"):
            value = el.attrib.get(attr)
            if value and value.startswith("#") and not HEX_RE.fullmatch(value):
                error(path, f"invalid {attr} color {value!r}")

    for style_el in (el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "style"):
        for token in CSS_HEX_RE.findall(style_el.text or ""):
            color = "#" + token
            if not HEX_RE.fullmatch(color):
                error(path, f"invalid CSS hex color {color!r}")

    if "@font-face" in raw or re.search(r"\.(?:woff2?|ttf|otf)\b", raw, re.I):
        error(path, "external/embedded font files are not allowed in documentation SVGs")

    if vb is None:
        return

    vx, vy, vw, vh = vb
    scale = min(1.0, TARGET_GITHUB_WIDTH / vw)
    class_sizes = css_class_font_sizes(root)
    strict = root.attrib.get("data-doc-tier") == "A"

    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] != "text":
            continue
        text = element_text(el)
        if not text:
            continue

        x = numeric_attr(el, "x")
        y = numeric_attr(el, "y")
        if x is not None and not (vx <= x <= vx + vw):
            error(path, f"text x={x:g} is outside viewBox")
        if y is not None and not (vy <= y <= vy + vh):
            error(path, f"text y={y:g} is outside viewBox")

        font_size = inherited_font_size(el, class_sizes)
        if strict:
            if font_size is None:
                error(path, f"strict Tier-A text must expose a measurable font-size: {text[:48]!r}")
                continue
            rendered = font_size * scale
            if rendered < MIN_RENDERED_TEXT_PX:
                error(path, f"text becomes ~{rendered:.1f}px at {TARGET_GITHUB_WIDTH:.0f}px GitHub width (< {MIN_RENDERED_TEXT_PX}px): {text[:48]!r}")

            if len(text) >= LONG_TEXT_CHARS:
                budget_raw = el.attrib.get("data-max-width")
                if not budget_raw:
                    error(path, f"long strict Tier-A text lacks data-max-width budget: {text[:60]!r}")
                else:
                    try:
                        budget = float(budget_raw)
                    except ValueError:
                        error(path, f"invalid data-max-width={budget_raw!r}: {text[:48]!r}")
                    else:
                        width = estimated_width(text, font_size)
                        if width > budget:
                            error(path, f"estimated text width {width:.0f}px exceeds budget {budget:.0f}px: {text[:60]!r}")
        elif font_size is not None and font_size * scale < 10.5:
            warn(path, f"legacy home asset may render tiny (~{font_size * scale:.1f}px at {TARGET_GITHUB_WIDTH:.0f}px): {text[:48]!r}")


def main() -> int:
    for path in ROOT_READMES:
        check_markdown(path)

    if not UI_DIR.exists():
        error(UI_DIR, "missing assets/ui directory")
    else:
        for path in sorted(UI_DIR.glob("home-*.svg")):
            check_svg(path)

    for item in WARNINGS:
        print(f"WARNING: {item}")
    for item in ERRORS:
        print(f"ERROR: {item}")

    print(f"docs-quality: {len(ERRORS)} error(s), {len(WARNINGS)} warning(s)")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    raise SystemExit(main())
