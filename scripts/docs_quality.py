#!/usr/bin/env python3
"""Deterministic documentation QA for Quillframe.

Normal CI must never spend model/API usage. This checker validates the machine-
checkable half of the documentation contract without pretending deterministic
code can replace semantic or rendered visual review.

The public documentation manifest is authoritative for registered product/docs
pages. Engineering specifications under ``specs/`` are opt-in records: selected
specs may be registered, but the checker does not force every historical or
single-language engineering record into the public documentation inventory.
"""
from __future__ import annotations

import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOC_MANIFEST = ROOT / "docs" / "documentation_manifest.json"
FRAMEWORK_MANIFEST = ROOT / "HARNESS_MANIFEST.yaml"
CLI_ENTRY = ROOT / "quillframe.py"
UI_DIR = ROOT / "assets" / "ui"
TARGET_GITHUB_WIDTH = 820.0
MIN_RENDERED_TEXT_PX = 12.0
LONG_TEXT_CHARS = 24

ERRORS: list[str] = []
WARNINGS: list[str] = []

HEX_RE = re.compile(r"^(?:#[0-9A-Fa-f]{3}|#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{8})$")
CSS_HEX_RE = re.compile(r"#([0-9A-Za-z]+)")
ARROW_BLOCK_RE = re.compile(r"```(?:text)?\s*\n(?:(?!```).)*(?:→|\s->\s)(?:(?!```).)*```", re.S)
MD_LINK_RE = re.compile(r"(?:!\[[^\]]*\]|\[[^\]]*\])\(([^)]+)\)")
HTML_LINK_RE = re.compile(r"\b(?:src|href)=[\"']([^\"']+)[\"']", re.I)
NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", re.I)
FONT_SHORTHAND_RE = re.compile(r"\bfont\s*:\s*[^;{}]*?\b(\d+(?:\.\d+)?)px\b", re.I)
H1_RE = re.compile(r"(?m)^# (?!#)")
TABLE_SEPARATOR_RE = re.compile(r"(?m)^\s*\|?(?:\s*:?-{3,}:?\s*\|){2,}.*$")
VERSION_RE = re.compile(r"(?m)^\s*version:\s*[\"']?([0-9]+\.[0-9]+\.[0-9]+)")
CLI_VERSION_RE = re.compile(r'^FRAMEWORK_VERSION\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', re.M)
STALE_EXAMPLE_RE = re.compile(
    r'(?:minimum_framework_version\s*=\s*"7\.[01]\.0"|'
    r'"version"\s*:\s*"7\.[01]\.0"|'
    r'\bQuillframe\s+7\.[01](?:\.0)?\b)',
    re.I,
)

# Public documentation roots are automatically inventoried. ``specs/`` is
# intentionally absent: engineering specs are historical/implementation records
# and enter the public docs manifest only when explicitly selected.
CONTROLLED_DOC_ROOTS = (
    ROOT,
    ROOT / "assets",
    ROOT / "core",
    ROOT / "corpus",
    ROOT / "docs",
    ROOT / "evals",
    ROOT / "harness",
    ROOT / "knowledge",
    ROOT / "release",
    ROOT / "studio",
    ROOT / "surface",
)
EXCLUDED_DISCOVERY_DIRS = {".git", ".quillframe", "node_modules", "dist", "__pycache__"}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def error(path: Path, message: str) -> None:
    ERRORS.append(f"{rel(path)}: {message}")


def warn(path: Path, message: str) -> None:
    WARNINGS.append(f"{rel(path)}: {message}")


def migration_issue(path: Path, message: str, *, strict_current: bool) -> None:
    """Block reviewed-current docs; candidate migration debt remains visible."""
    (error if strict_current else warn)(path, message)


def load_doc_manifest() -> dict:
    if not DOC_MANIFEST.exists():
        error(DOC_MANIFEST, "missing documentation manifest")
        return {}
    try:
        data = json.loads(DOC_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        error(DOC_MANIFEST, f"invalid JSON: {exc}")
        return {}
    if data.get("schema") != "quillframe_documentation_manifest_v1":
        error(DOC_MANIFEST, f"unexpected schema: {data.get('schema')!r}")
    return data


def framework_version() -> str | None:
    if not FRAMEWORK_MANIFEST.exists():
        error(FRAMEWORK_MANIFEST, "missing framework manifest")
        return None
    match = VERSION_RE.search(FRAMEWORK_MANIFEST.read_text(encoding="utf-8"))
    if not match:
        error(FRAMEWORK_MANIFEST, "cannot parse framework version")
        return None
    return match.group(1)


def cli_framework_version() -> str | None:
    if not CLI_ENTRY.exists():
        warn(CLI_ENTRY, "missing CLI entrypoint; implementation/release version drift cannot be checked")
        return None
    match = CLI_VERSION_RE.search(CLI_ENTRY.read_text(encoding="utf-8"))
    if not match:
        warn(CLI_ENTRY, "cannot parse FRAMEWORK_VERSION; implementation/release version drift cannot be checked")
        return None
    return match.group(1)


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


def check_links(path: Path, text: str) -> None:
    for match in [*MD_LINK_RE.finditer(text), *HTML_LINK_RE.finditer(text)]:
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


def check_chinese_copy(path: Path, text: str) -> None:
    risky = {
        "reviewer shopping": "prefer native Chinese prose; keep the English term only for the exact anti-pattern",
        "semantic reject": "prefer Chinese prose with `semantic_reject` only as an exact identifier",
        "consumer project": "prefer 下游项目",
        "Human-facing": "prefer 面向用户 / 人类可读",
        "Generic Framework": "prefer 通用框架 in explanatory prose",
        "exactly one": "prefer 恰好一个 / 只能有一个 outside normative identifiers",
        "must not": "prefer natural Chinese prohibition outside code/quoted identifiers",
    }
    for phrase, note in risky.items():
        if phrase in text:
            warn(path, f"Chinese copy contains {phrase!r}: {note}")


def check_markdown(path: Path, *, tier: str, status: str, rewrite_policy: str) -> None:
    if not path.exists():
        error(path, "manifest-listed document is missing")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        error(path, f"not valid UTF-8: {exc}")
        return

    strict_current = status in {"reviewed_7_2", "reviewed_current"} and rewrite_policy != "preserve_history"
    h1_count = len(H1_RE.findall(text))
    if h1_count != 1:
        migration_issue(path, f"expected exactly one Markdown H1, found {h1_count}", strict_current=strict_current)

    check_links(path, text)

    if tier == "A":
        if ARROW_BLOCK_RE.search(text):
            migration_issue(
                path,
                "Tier-A page contains a fenced arrow-process block; use a designed module or structured prose",
                strict_current=strict_current,
            )
        tables = len(TABLE_SEPARATOR_RE.findall(text))
        if tables:
            migration_issue(
                path,
                f"Tier-A page contains {tables} native Markdown table(s); use designed modules or compact prose",
                strict_current=strict_current,
            )

    if rewrite_policy != "preserve_history" and STALE_EXAMPLE_RE.search(text):
        warn(path, "contains a 7.0/7.1 framework-version example/reference; verify whether it is stale")

    if path.name.endswith(".zh-CN.md") and rewrite_policy != "preserve_history":
        check_chinese_copy(path, text)


def discover_bilingual_docs() -> set[str]:
    found: set[str] = set()
    for path in ROOT.glob("*.md"):
        if path.name.endswith((".en.md", ".zh-CN.md")):
            found.add(rel(path))
    for base in CONTROLLED_DOC_ROOTS[1:]:
        if not base.exists():
            continue
        for path in base.rglob("*.md"):
            if any(part in EXCLUDED_DISCOVERY_DIRS for part in path.parts):
                continue
            if path.name.endswith((".en.md", ".zh-CN.md")):
                found.add(rel(path))
    return found


def check_inventory(manifest: dict) -> list[tuple[Path, str, str, str]]:
    docs = manifest.get("documents")
    if not isinstance(docs, list):
        error(DOC_MANIFEST, "documents must be a list")
        return []

    ids: set[str] = set()
    tracked: dict[str, tuple[str, str, str]] = {}
    checks: list[tuple[Path, str, str, str]] = []
    allowed_tiers = {"A", "B", "C"}
    allowed_status = {"needs_rebuild", "candidate_review", "reviewed_current", "reviewed_7_2", "preserve"}

    for entry in docs:
        if not isinstance(entry, dict):
            error(DOC_MANIFEST, "document entry must be an object")
            continue
        doc_id = entry.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            error(DOC_MANIFEST, "document entry is missing id")
            continue
        if doc_id in ids:
            error(DOC_MANIFEST, f"duplicate document id: {doc_id}")
        ids.add(doc_id)

        tier = entry.get("tier")
        status = entry.get("status")
        rewrite_policy = entry.get("rewrite_policy", "rebuild")
        if tier not in allowed_tiers:
            error(DOC_MANIFEST, f"{doc_id}: invalid tier {tier!r}")
        if status not in allowed_status:
            error(DOC_MANIFEST, f"{doc_id}: invalid status {status!r}")

        en = entry.get("english")
        zh = entry.get("chinese")
        if not isinstance(en, str) or not en.endswith(".en.md"):
            error(DOC_MANIFEST, f"{doc_id}: english path must end in .en.md")
            continue
        if not isinstance(zh, str) or not zh.endswith(".zh-CN.md"):
            error(DOC_MANIFEST, f"{doc_id}: chinese path must end in .zh-CN.md")
            continue

        expected_zh = en[:-6] + ".zh-CN.md"
        if zh != expected_zh:
            error(DOC_MANIFEST, f"{doc_id}: bilingual pair path mismatch: expected {expected_zh}")

        for raw in (en, zh):
            previous = tracked.get(raw)
            if previous is not None:
                previous_id, previous_status, previous_rewrite = previous
                historical_alias = (
                    status == "preserve"
                    and rewrite_policy == "preserve_history"
                    and previous_status == "preserve"
                    and previous_rewrite == "preserve_history"
                )
                if historical_alias:
                    warn(DOC_MANIFEST, f"historical document path has multiple navigation aliases: {previous_id}, {doc_id} -> {raw}")
                else:
                    error(DOC_MANIFEST, f"path tracked by more than one active document entry: {raw}")
            else:
                tracked[raw] = (doc_id, str(status), str(rewrite_policy))
                checks.append((ROOT / raw, str(tier), str(status), str(rewrite_policy)))

    discovered = discover_bilingual_docs()
    for raw in sorted(discovered - set(tracked)):
        error(ROOT / raw, "bilingual public-facing doc is not registered in documentation_manifest.json")

    routers = manifest.get("routers", [])
    if not isinstance(routers, list):
        error(DOC_MANIFEST, "routers must be a list")
    else:
        for item in routers:
            raw = item.get("path") if isinstance(item, dict) else None
            if not isinstance(raw, str):
                error(DOC_MANIFEST, "router entry missing path")
                continue
            path = ROOT / raw
            if not path.exists():
                error(path, "manifest-listed router is missing")

    return checks


def element_text(el: ET.Element) -> str:
    return "".join(el.itertext()).strip()


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


def css_class_font_sizes(root: ET.Element) -> dict[str, float]:
    result: dict[str, float] = {}
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] != "style":
            continue
        for selector, body in re.findall(r"\.([A-Za-z0-9_-]+)\s*\{([^}]+)\}", el.text or ""):
            match = FONT_SIZE_RE.search(body) or FONT_SHORTHAND_RE.search(body)
            if match:
                result[selector] = float(match.group(1))
    return result


def inherited_font_size(el: ET.Element, class_sizes: dict[str, float]) -> float | None:
    raw = el.attrib.get("font-size")
    if raw:
        try:
            return float(raw.removesuffix("px"))
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
    if unicodedata.category(ch).startswith("P"):
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
                error(path, f"text becomes ~{rendered:.1f}px at {TARGET_GITHUB_WIDTH:.0f}px (< {MIN_RENDERED_TEXT_PX}px): {text[:48]!r}")
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
    manifest = load_doc_manifest()
    release_version = framework_version()
    implementation_version = cli_framework_version()

    if manifest and release_version and manifest.get("framework_version") != release_version:
        error(
            DOC_MANIFEST,
            f"framework_version={manifest.get('framework_version')!r} does not match HARNESS_MANIFEST.yaml {release_version!r}",
        )
    if release_version and implementation_version and release_version != implementation_version:
        warn(
            FRAMEWORK_MANIFEST,
            f"release metadata drift: HARNESS_MANIFEST.yaml={release_version} while quillframe.py reports {implementation_version}",
        )

    checks = check_inventory(manifest) if manifest else []
    for path, tier, status, rewrite_policy in checks:
        check_markdown(path, tier=tier, status=status, rewrite_policy=rewrite_policy)

    root_readme = ROOT / "README.md"
    if not root_readme.exists():
        error(root_readme, "missing root product entrypoint")
    else:
        check_links(root_readme, root_readme.read_text(encoding="utf-8"))

    if not UI_DIR.exists():
        error(UI_DIR, "missing assets/ui directory")
    else:
        for path in sorted(UI_DIR.glob("home-*.svg")):
            check_svg(path)

    if manifest:
        states: dict[str, int] = {}
        for entry in manifest.get("documents", []):
            state = entry.get("status", "unknown")
            states[state] = states.get(state, 0) + 1
        print("documentation-inventory:", ", ".join(f"{key}={value}" for key, value in sorted(states.items())))

    for item in WARNINGS:
        print(f"WARNING: {item}")
    for item in ERRORS:
        print(f"ERROR: {item}")

    print(f"docs-quality: {len(ERRORS)} error(s), {len(WARNINGS)} warning(s)")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    raise SystemExit(main())
