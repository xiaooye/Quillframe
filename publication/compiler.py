#!/usr/bin/env python3
"""Deterministic NovelForge publication compiler.

Accepted manuscript text is immutable input. The compiler creates a renderer-
neutral IR and derived clean-text, web-reflow, print-HTML and EPUB 3.3 outputs.
It performs structural validation and exact text round-trip checks; full EPUB
release conformance requires an explicitly supplied external EPUBCheck command.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shlex
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

IR_SCHEMA = "novelforge_publication_ir_v1"
BUILD_SCHEMA = "novelforge_publication_build_v1"
PROFILES = {"clean_text", "web_reflow", "print_book", "epub3"}
EPUB_MIMETYPE = b"application/epub+zip"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
XHTML_NS = "http://www.w3.org/1999/xhtml"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def text_fingerprint(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _text(value: Any, name: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be {'string' if allow_empty else 'non-empty string'}")
    return value


def _fp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", value):
        raise ValueError(f"{name} must be sha256:<64 lowercase hex>")
    return value


def safe_id(value: str) -> str:
    out = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    if not out:
        raise ValueError(f"chapter_id cannot form safe filename: {value!r}")
    return out


def compile_ir(source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise ValueError("publication source must be object")
    book = source.get("book")
    if not isinstance(book, dict):
        raise ValueError("book object required")
    normalized_book = {
        "identifier": _text(book.get("identifier"), "book.identifier"),
        "title": _text(book.get("title"), "book.title"),
        "language": _text(book.get("language"), "book.language"),
        "modified": _text(book.get("modified"), "book.modified"),
    }
    raw_chapters = source.get("chapters")
    if not isinstance(raw_chapters, list) or not raw_chapters:
        raise ValueError("chapters must be non-empty list")
    chapters = []
    ids: set[str] = set(); safe_ids: set[str] = set()
    for raw in raw_chapters:
        if not isinstance(raw, dict):
            raise ValueError("chapter must be object")
        cid = _text(raw.get("chapter_id"), "chapter.chapter_id")
        if cid in ids:
            raise ValueError(f"duplicate chapter_id: {cid}")
        ids.add(cid)
        sid = safe_id(cid)
        if sid in safe_ids:
            raise ValueError(f"chapter filename collision: {cid}")
        safe_ids.add(sid)
        text = _text(raw.get("text"), f"{cid}.text", allow_empty=True)
        accepted = _fp(raw.get("accepted_fingerprint"), f"{cid}.accepted_fingerprint")
        actual = text_fingerprint(text)
        if actual != accepted:
            raise ValueError(f"accepted manuscript fingerprint mismatch: {cid}")
        chapters.append({
            "chapter_id": cid,
            "title": _text(raw.get("title"), f"{cid}.title"),
            "text": text,
            "accepted_fingerprint": accepted,
        })
    basis = {"book": normalized_book, "chapters": [{"chapter_id": c["chapter_id"], "title": c["title"], "accepted_fingerprint": c["accepted_fingerprint"]} for c in chapters]}
    return {
        "schema": IR_SCHEMA,
        "book": normalized_book,
        "chapters": chapters,
        "source_fingerprint": sha256_bytes(canonical(basis)),
        "text_preservation": "exact-unicode-text",
        "authority": False,
    }


def validate_ir(ir: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(ir, dict) or ir.get("schema") != IR_SCHEMA:
        return ["publication IR schema mismatch"]
    if ir.get("authority") is not False or ir.get("text_preservation") != "exact-unicode-text":
        errors.append("publication IR authority/text-preservation boundary invalid")
    book = ir.get("book")
    if not isinstance(book, dict):
        errors.append("book object required")
    chapters = ir.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        errors.append("chapters must be non-empty list")
    else:
        seen = set()
        for c in chapters:
            if not isinstance(c, dict):
                errors.append("chapter must be object"); continue
            cid = c.get("chapter_id")
            if not isinstance(cid, str) or not cid:
                errors.append("chapter_id required"); continue
            if cid in seen:
                errors.append(f"duplicate chapter_id: {cid}")
            seen.add(cid)
            text = c.get("text")
            fp = c.get("accepted_fingerprint")
            if not isinstance(text, str) or not isinstance(fp, str) or text_fingerprint(text) != fp:
                errors.append(f"accepted text fingerprint mismatch: {cid}")
    return errors


def _css(profile: str) -> str:
    common = "body{font-family:serif;line-height:1.7;max-width:46rem;margin:0 auto;padding:2rem}.chapter{break-after:page}.manuscript-text{white-space:pre-wrap}h1{line-height:1.25}"
    if profile == "print_book":
        return "@page{size:6in 9in;margin:0.7in 0.65in 0.8in}@media print{body{max-width:none;padding:0}.chapter{break-after:page}}" + common
    return common


def _html_document(ir: dict[str, Any], profile: str) -> str:
    book = ir["book"]
    sections = []
    for c in ir["chapters"]:
        sections.append(f'<section class="chapter" id="{html.escape(safe_id(c["chapter_id"]))}"><h1>{html.escape(c["title"])}</h1><div class="manuscript-text">{html.escape(c["text"])}</div></section>')
    return '<!doctype html><html lang="{}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{}</title><style>{}</style></head><body>{}</body></html>\n'.format(html.escape(book["language"]), html.escape(book["title"]), _css(profile), "".join(sections))


def _write_clean(ir: dict[str, Any], out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for c in ir["chapters"]:
        name = safe_id(c["chapter_id"]) + ".txt"
        data = c["text"].encode("utf-8")
        (out / name).write_bytes(data)
        files.append({"path": name, "sha256": sha256_bytes(data), "accepted_fingerprint": c["accepted_fingerprint"]})
    (out / "publication-ir.json").write_text(json.dumps(ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"profile": "clean_text", "files": files, "text_roundtrip": all(x["sha256"] == x["accepted_fingerprint"] for x in files)}


def _write_html(ir: dict[str, Any], out: Path, profile: str) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    name = "book.html" if profile == "print_book" else "index.html"
    data = _html_document(ir, profile).encode("utf-8")
    (out / name).write_bytes(data)
    (out / "publication-ir.json").write_text(json.dumps(ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"profile": profile, "files": [{"path": name, "sha256": sha256_bytes(data)}], "text_roundtrip": _validate_html_text(out / name, ir) == []}


def _validate_html_text(path: Path, ir: dict[str, Any]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors = []
    for c in ir["chapters"]:
        escaped = html.escape(c["text"])
        if f'<div class="manuscript-text">{escaped}</div>' not in text:
            errors.append(f"rendered chapter text mismatch: {c['chapter_id']}")
    return errors


def _zip_write(zf: zipfile.ZipFile, name: str, data: bytes, compress: bool = True) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIME)
    info.create_system = 0
    info.external_attr = 0o644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    zf.writestr(info, data)


def _chapter_xhtml(ir: dict[str, Any], c: dict[str, Any]) -> bytes:
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            f'<html xmlns="{XHTML_NS}" lang="{html.escape(ir["book"]["language"])}"><head><title>{html.escape(c["title"])}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>'
            f'<body><section class="chapter"><h1>{html.escape(c["title"])}</h1><div class="manuscript-text">{html.escape(c["text"])}</div></section></body></html>\n').encode("utf-8")


def _nav_xhtml(ir: dict[str, Any], names: list[tuple[str, str]]) -> bytes:
    links = "".join(f'<li><a href="{html.escape(name)}">{html.escape(title)}</a></li>' for name, title in names)
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            f'<html xmlns="{XHTML_NS}" xmlns:epub="http://www.idpf.org/2007/ops" lang="{html.escape(ir["book"]["language"])}"><head><title>Contents</title></head><body><nav epub:type="toc" id="toc"><h1>Contents</h1><ol>{links}</ol></nav></body></html>\n').encode("utf-8")


def _opf(ir: dict[str, Any], names: list[tuple[str, str]]) -> bytes:
    book = ir["book"]
    items = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>', '<item id="css" href="style.css" media-type="text/css"/>']
    spine = []
    for i, (name, _) in enumerate(names, 1):
        items.append(f'<item id="c{i}" href="{html.escape(name)}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="c{i}"/>')
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
           f'<package xmlns="{OPF_NS}" version="3.0" unique-identifier="pub-id" xml:lang="{html.escape(book["language"])}">'
           f'<metadata xmlns:dc="{DC_NS}"><dc:identifier id="pub-id">{html.escape(book["identifier"])}</dc:identifier><dc:title>{html.escape(book["title"])}</dc:title><dc:language>{html.escape(book["language"])}</dc:language><meta property="dcterms:modified">{html.escape(book["modified"])}</meta></metadata>'
           f'<manifest>{"".join(items)}</manifest><spine>{"".join(spine)}</spine></package>\n')
    return xml.encode("utf-8")


def _container_xml() -> bytes:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<container version="1.0" xmlns="{CONTAINER_NS}"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>\n').encode("utf-8")


def _write_epub(ir: dict[str, Any], out: Path) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    names = [(f'chapter-{i:04d}-{safe_id(c["chapter_id"])}.xhtml', c["title"]) for i, c in enumerate(ir["chapters"], 1)]
    with zipfile.ZipFile(out, "w") as zf:
        _zip_write(zf, "mimetype", EPUB_MIMETYPE, compress=False)
        _zip_write(zf, "META-INF/container.xml", _container_xml())
        _zip_write(zf, "EPUB/package.opf", _opf(ir, names))
        _zip_write(zf, "EPUB/nav.xhtml", _nav_xhtml(ir, names))
        _zip_write(zf, "EPUB/style.css", _css("web_reflow").encode("utf-8"))
        for (name, _), c in zip(names, ir["chapters"]):
            _zip_write(zf, "EPUB/" + name, _chapter_xhtml(ir, c))
        _zip_write(zf, "META-INF/novelforge-publication-ir.json", (json.dumps(ir, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
    report = validate_epub(out, ir=ir)
    return {"profile": "epub3", "files": [{"path": out.name, "sha256": sha256_bytes(out.read_bytes())}], "text_roundtrip": report["text_roundtrip"], "internal_validation": report["valid"]}


def validate_epub(path: Path, *, ir: dict[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist(); names = [x.filename for x in infos]
            if not infos or infos[0].filename != "mimetype": errors.append("mimetype must be first ZIP entry")
            elif infos[0].compress_type != zipfile.ZIP_STORED: errors.append("mimetype must be uncompressed")
            if "mimetype" not in names or zf.read("mimetype") != EPUB_MIMETYPE: errors.append("invalid EPUB mimetype")
            required = {"META-INF/container.xml", "EPUB/package.opf", "EPUB/nav.xhtml"}
            missing = sorted(required - set(names))
            if missing: errors.append("missing EPUB resources: " + ", ".join(missing))
            if not missing:
                container = ET.fromstring(zf.read("META-INF/container.xml")); rf = container.find(f".//{{{CONTAINER_NS}}}rootfile")
                if rf is None or rf.attrib.get("full-path") != "EPUB/package.opf": errors.append("container rootfile mismatch")
                opf = ET.fromstring(zf.read("EPUB/package.opf")); manifest = opf.find(f"{{{OPF_NS}}}manifest"); spine = opf.find(f"{{{OPF_NS}}}spine")
                if manifest is None or spine is None: errors.append("package manifest/spine missing")
                else:
                    items = {x.attrib.get("id"): x for x in manifest.findall(f"{{{OPF_NS}}}item")}
                    nav = items.get("nav")
                    if nav is None or "nav" not in nav.attrib.get("properties", "").split(): errors.append("navigation document not declared with nav property")
                    for item in items.values():
                        href = item.attrib.get("href")
                        if href and "EPUB/" + href not in names: errors.append(f"manifest resource missing: {href}")
                    for ref in spine.findall(f"{{{OPF_NS}}}itemref"):
                        if ref.attrib.get("idref") not in items: errors.append(f"spine idref missing from manifest: {ref.attrib.get('idref')}")
                nav_doc = ET.fromstring(zf.read("EPUB/nav.xhtml"))
                navs = [x for x in nav_doc.iter() if x.tag == f"{{{XHTML_NS}}}nav"]
                if not navs: errors.append("EPUB navigation toc missing")
            text_roundtrip = True
            if ir is not None:
                chapter_names = sorted(n for n in names if n.startswith("EPUB/chapter-") and n.endswith(".xhtml"))
                if len(chapter_names) != len(ir.get("chapters", [])):
                    errors.append("chapter resource count mismatch"); text_roundtrip = False
                else:
                    for name, c in zip(chapter_names, ir["chapters"]):
                        root = ET.fromstring(zf.read(name)); divs = [x for x in root.iter() if x.tag == f"{{{XHTML_NS}}}div" and x.attrib.get("class") == "manuscript-text"]
                        rendered = "" if not divs else "".join(divs[0].itertext())
                        if rendered != c["text"] or text_fingerprint(rendered) != c["accepted_fingerprint"]:
                            errors.append(f"EPUB text round-trip mismatch: {c['chapter_id']}"); text_roundtrip = False
            else:
                text_roundtrip = False
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        errors.append(f"EPUB validation error: {type(exc).__name__}: {exc}"); text_roundtrip = False
    return {"schema": "novelforge_epub_validation_v1", "valid": not errors, "errors": errors, "text_roundtrip": text_roundtrip, "spec_target": "W3C EPUB 3.3", "external_epubcheck": "not_run", "authority": False}


def run_epubcheck(epub: Path, command: str) -> dict[str, Any]:
    argv = shlex.split(command) + [str(epub)]
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    return {"command": argv, "returncode": proc.returncode, "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:], "passed": proc.returncode == 0}


def build(ir: dict[str, Any], profile: str, output: Path) -> dict[str, Any]:
    errors = validate_ir(ir)
    if errors: raise ValueError("invalid publication IR: " + "; ".join(errors))
    if profile not in PROFILES: raise ValueError(f"unknown publication profile: {profile}")
    if profile == "clean_text": detail = _write_clean(ir, output)
    elif profile in {"web_reflow", "print_book"}: detail = _write_html(ir, output, profile)
    else: detail = _write_epub(ir, output)
    return {"schema": BUILD_SCHEMA, "profile": profile, "source_fingerprint": ir["source_fingerprint"], "text_preservation": "exact-unicode-text", "detail": detail, "authority": False, "model_execution": False}


def self_test() -> int:
    c1 = "第一段。\n\n第二段 <&> 保持原样。"
    c2 = "A line.\nAnother line.\n\n最后一段。"
    source = {"book": {"identifier": "urn:novelforge:selftest", "title": "测试书", "language": "zh-CN", "modified": "2026-01-13T00:00:00Z"}, "chapters": [
        {"chapter_id": "CH-001", "title": "第一章", "text": c1, "accepted_fingerprint": text_fingerprint(c1)},
        {"chapter_id": "CH-002", "title": "第二章", "text": c2, "accepted_fingerprint": text_fingerprint(c2)},
    ]}
    ir = compile_ir(source)
    tamper = json.loads(json.dumps(source)); tamper["chapters"][0]["text"] += "x"; tamper_guard = False
    try: compile_ir(tamper)
    except ValueError: tamper_guard = True
    with tempfile.TemporaryDirectory(prefix="novelforge-publication-") as td:
        root = Path(td)
        clean = build(ir, "clean_text", root / "clean")
        web = build(ir, "web_reflow", root / "web")
        print_report = build(ir, "print_book", root / "print")
        a = root / "a.epub"; b = root / "b.epub"
        epub_a = build(ir, "epub3", a); epub_b = build(ir, "epub3", b)
        validation = validate_epub(a, ir=ir)
        deterministic = a.read_bytes() == b.read_bytes()
        clean_exact = all((root / "clean" / (safe_id(c["chapter_id"]) + ".txt")).read_text(encoding="utf-8") == c["text"] for c in ir["chapters"])
        ok = all((tamper_guard, clean["detail"]["text_roundtrip"], clean_exact, web["detail"]["text_roundtrip"], print_report["detail"]["text_roundtrip"], epub_a["detail"]["text_roundtrip"], epub_b["detail"]["internal_validation"], validation["valid"], validation["text_roundtrip"], deterministic))
    print(json.dumps({"publication_compiler_contract": "PASS" if ok else "FAIL", "ir_schema": IR_SCHEMA, "profiles": sorted(PROFILES), "accepted_text_fingerprint_guard": tamper_guard, "clean_text_exact": clean_exact, "web_text_roundtrip": web["detail"]["text_roundtrip"], "print_text_roundtrip": print_report["detail"]["text_roundtrip"], "epub_internal_valid": validation["valid"], "epub_text_roundtrip": validation["text_roundtrip"], "deterministic_epub": deterministic, "external_epubcheck_required_for_release": True, "authority": False, "model_execution": False}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge deterministic publication compiler")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    comp = sub.add_parser("compile"); comp.add_argument("--input", required=True); comp.add_argument("--output", required=True)
    bld = sub.add_parser("build"); bld.add_argument("--ir", required=True); bld.add_argument("--profile", required=True, choices=sorted(PROFILES)); bld.add_argument("--output", required=True); bld.add_argument("--report")
    val = sub.add_parser("validate-epub"); val.add_argument("--epub", required=True); val.add_argument("--ir"); val.add_argument("--epubcheck-command"); val.add_argument("--release", action="store_true"); val.add_argument("--output")
    args = p.parse_args()
    if args.command == "self-test": return self_test()
    if args.command == "compile":
        ir = compile_ir(json.loads(Path(args.input).read_text(encoding="utf-8"))); Path(args.output).write_text(json.dumps(ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); return 0
    if args.command == "build":
        report = build(json.loads(Path(args.ir).read_text(encoding="utf-8")), args.profile, Path(args.output)); text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"; Path(args.report).write_text(text, encoding="utf-8") if args.report else print(text, end=""); return 0
    ir = json.loads(Path(args.ir).read_text(encoding="utf-8")) if args.ir else None
    report = validate_epub(Path(args.epub), ir=ir)
    if args.epubcheck_command:
        report["external_epubcheck"] = run_epubcheck(Path(args.epub), args.epubcheck_command)
    if args.release and (not report["valid"] or not isinstance(report.get("external_epubcheck"), dict) or not report["external_epubcheck"].get("passed")):
        report["release_valid"] = False; code = 1
    else:
        report["release_valid"] = report["valid"] and (not args.release or bool(report.get("external_epubcheck", {}).get("passed"))); code = 0 if report["valid"] else 1
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"; Path(args.output).write_text(text, encoding="utf-8") if args.output else print(text, end=""); return code


if __name__ == "__main__":
    raise SystemExit(main())
