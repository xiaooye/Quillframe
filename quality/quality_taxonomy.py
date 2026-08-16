#!/usr/bin/env python3
"""Machine contract and compatibility scanner for NovelForge prose quality IDs.

The registry is the machine-facing source of truth for HF/RG identifiers. Human
Surface/Reader documentation remains the explanatory contract, and self-test
requires the documented identifiers/names to agree with the registry.

Consuming projects may cite Framework identifiers in profiles and regression
suites. A Framework migration must scan those files: an identifier that still
exists but now names a different mechanism is a compatibility error, not a
successful migration.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = Path(__file__).with_name("taxonomy.json")
SCHEMA = "novelforge_quality_taxonomy_v1"
CODE_RE = re.compile(r"\b(?:HF|RG)-\d{2}\b")
LEGACY_RUNTIME_RE = re.compile(r"\bGeneric\s+Surface\s+v\d+(?:\.\d+)*\b", re.IGNORECASE)


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError(f"taxonomy registry must use {SCHEMA}")
    return value


def _norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")


def entries(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    families = registry.get("families")
    if not isinstance(families, dict) or not families:
        raise ValueError("taxonomy families are required")
    for family_id, family in families.items():
        if not isinstance(family, dict):
            raise ValueError(f"invalid taxonomy family: {family_id}")
        prefix = family.get("prefix")
        rows = family.get("entries")
        if not isinstance(prefix, str) or not prefix or not isinstance(rows, list) or not rows:
            raise ValueError(f"invalid taxonomy family metadata: {family_id}")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"invalid taxonomy row in {family_id}")
            code = row.get("id")
            name = row.get("name")
            aliases = row.get("aliases", [])
            if not isinstance(code, str) or not re.fullmatch(rf"{re.escape(prefix)}-\d{{2}}", code):
                raise ValueError(f"invalid taxonomy id in {family_id}: {code}")
            if code in result:
                raise ValueError(f"duplicate taxonomy id: {code}")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"taxonomy name required: {code}")
            if not isinstance(aliases, list) or not all(isinstance(x, str) and x.strip() for x in aliases):
                raise ValueError(f"invalid taxonomy aliases: {code}")
            result[code] = {**row, "family": family_id, "prefix": prefix}
    return result


def id_for_name(name: str, registry: dict[str, Any] | None = None) -> str:
    wanted = _norm(name)
    matches = []
    for code, row in entries(registry or load_registry()).items():
        labels = [row["name"], *row.get("aliases", [])]
        if wanted in {_norm(label) for label in labels}:
            matches.append(code)
    if len(matches) != 1:
        raise ValueError(f"taxonomy name must resolve exactly once: {name}: {matches}")
    return matches[0]


def validate_docs(registry: dict[str, Any] | None = None) -> list[str]:
    registry = registry or load_registry()
    by_id = entries(registry)
    errors: list[str] = []
    for family_id, family in registry["families"].items():
        docs = family.get("source_docs", [])
        if not isinstance(docs, list) or not docs:
            errors.append(f"{family_id}: source_docs required")
            continue
        family_rows = [row for row in by_id.values() if row["family"] == family_id]
        for rel in docs:
            path = ROOT / rel
            if not path.is_file():
                errors.append(f"{family_id}: source doc missing: {rel}")
                continue
            text = path.read_text(encoding="utf-8")
            for row in family_rows:
                if row["id"] not in text or row["name"] not in text:
                    errors.append(f"{rel}: missing canonical taxonomy heading/name for {row['id']} {row['name']}")
    return errors


def _alias_map(registry: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for code, row in entries(registry).items():
        for label in [row["name"], *row.get("aliases", [])]:
            token = _norm(label)
            if len(token) < 8:
                continue
            prior = result.get(token)
            if prior and prior != code:
                raise ValueError(f"taxonomy alias collision: {token}: {prior}, {code}")
            result[token] = code
    return result


def scan_text(text: str, *, source: str = "<memory>", registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or load_registry()
    by_id = entries(registry)
    aliases = _alias_map(registry)
    findings: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        cited = set(CODE_RE.findall(line))
        for code in sorted(cited):
            if code not in by_id:
                findings.append({"source": source, "line": lineno, "code": "unknown_identifier", "identifier": code, "text": line.strip()})
        if cited:
            normalized_line = _norm(line)
            for alias, expected_id in aliases.items():
                if alias in normalized_line and expected_id not in cited:
                    findings.append({
                        "source": source,
                        "line": lineno,
                        "code": "identifier_label_mismatch",
                        "label": alias,
                        "expected_identifier": expected_id,
                        "cited_identifiers": sorted(cited),
                        "text": line.strip(),
                    })
        for prefix in ("HF", "RG"):
            range_re = re.compile(rf"\b{prefix}-(\d{{2}})\s*\.\.\s*(?:{prefix}-)?(\d{{2}})\b")
            family_ids = sorted(int(code.split("-")[1]) for code in by_id if code.startswith(prefix + "-"))
            if not family_ids:
                continue
            expected = (min(family_ids), max(family_ids))
            for match in range_re.finditer(line):
                actual = (int(match.group(1)), int(match.group(2)))
                if actual != expected:
                    findings.append({
                        "source": source,
                        "line": lineno,
                        "code": "identifier_range_drift",
                        "family": prefix,
                        "expected": f"{prefix}-{expected[0]:02d}..{prefix}-{expected[1]:02d}",
                        "actual": match.group(0),
                        "text": line.strip(),
                    })
        if LEGACY_RUNTIME_RE.search(line):
            findings.append({
                "source": source,
                "line": lineno,
                "code": "legacy_runtime_taxonomy_marker",
                "text": line.strip(),
                "message": "Framework taxonomy identity must come from novelforge.lock.json plus the pinned taxonomy registry, not a hand-maintained Generic Surface version label.",
            })
    # De-duplicate findings that can be triggered by canonical name plus an alias on the same line.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for finding in findings:
        key = json.dumps(finding, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique


def scan_files(paths: list[Path], registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or load_registry()
    findings: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            findings.append({"source": str(path), "line": None, "code": "file_missing", "text": ""})
            continue
        findings.extend(scan_text(path.read_text(encoding="utf-8"), source=str(path), registry=registry))
    return {
        "schema": "novelforge_quality_taxonomy_scan_v1",
        "registry_schema": registry["schema"],
        "registry_version": registry.get("version"),
        "valid": not findings,
        "files": [str(path) for path in paths],
        "findings": findings,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> dict[str, Any]:
    registry = load_registry()
    by_id = entries(registry)
    docs = validate_docs(registry)
    good = scan_text("Expected: `RG-10 FORWARD-PULL-END / RG-15 SAFE-BUT-FLAT`", registry=registry)
    wrong_reader = scan_text("Expected: `RG-10 SAFE-BUT-FLAT`", registry=registry)
    wrong_surface = scan_text("Expected: `HF-23 SIGNIFICANCE-INFLATION`", registry=registry)
    wrong_range = scan_text("runtime: HF-01..HF-29 + RG-01..RG-10", registry=registry)
    old_runtime = scan_text("runtime: Generic Surface v6.3", registry=registry)
    checks = {
        "registry_entries": len(by_id) == 45,
        "safe_but_flat_is_rg15": id_for_name("SAFE-BUT-FLAT", registry) == "RG-15",
        "forward_pull_is_rg10": id_for_name("FORWARD-PULL-END", registry) == "RG-10",
        "significance_is_hf15": id_for_name("SIGNIFICANCE-INFLATION", registry) == "HF-15",
        "human_docs_match_registry": not docs,
        "current_pair_passes": not good,
        "reader_semantic_drift_detected": any(x["code"] == "identifier_label_mismatch" for x in wrong_reader),
        "surface_semantic_drift_detected": any(x["code"] == "identifier_label_mismatch" for x in wrong_surface),
        "range_drift_detected": any(x["code"] == "identifier_range_drift" for x in wrong_range),
        "legacy_runtime_marker_detected": any(x["code"] == "legacy_runtime_taxonomy_marker" for x in old_runtime),
    }
    return {
        "quality_taxonomy_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": registry["schema"],
        "version": registry.get("version"),
        "checks": checks,
        "doc_errors": docs,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge quality taxonomy compatibility contract")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    scan = sub.add_parser("scan")
    scan.add_argument("files", nargs="+")
    args = parser.parse_args()
    if args.command == "self-test":
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["quality_taxonomy_contract"] == "PASS" else 1
    result = scan_files([Path(value) for value in args.files])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
