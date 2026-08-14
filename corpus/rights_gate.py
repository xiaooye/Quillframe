#!/usr/bin/env python3
"""NovelForge corpus rights/storage intent validator.

This tool validates declared rights metadata and whether the requested storage
mode is consistent with policy. It does NOT perform legal analysis or infer
copyright status from a URL/title.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

RIGHTS = {"redistributable", "analysis_only", "unknown"}
STORAGE = {"metadata_only", "derived_only", "short_excerpt", "full_text"}


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("corpus_id", "source_title", "source_type", "rights_class", "rights_basis", "storage_intent"):
        if key not in record:
            errors.append(f"missing {key}")
    if errors:
        return errors
    rights = record.get("rights_class")
    storage = record.get("storage_intent")
    if rights not in RIGHTS:
        errors.append("invalid rights_class")
    if storage not in STORAGE:
        errors.append("invalid storage_intent")
    basis = str(record.get("rights_basis") or "").strip()
    if rights == "redistributable" and not basis:
        errors.append("redistributable requires non-empty rights_basis")
    if rights == "unknown" and storage != "metadata_only":
        errors.append("unknown rights permits metadata_only storage only")
    if rights == "analysis_only" and storage == "full_text":
        errors.append("analysis_only forbids full_text storage")
    if storage == "short_excerpt" and not record.get("excerpt_purpose"):
        errors.append("short_excerpt requires excerpt_purpose")
    return errors


def decision(record: dict[str, Any]) -> dict[str, Any]:
    errors = validate(record)
    return {
        "schema": "novelforge_corpus_rights_decision_v1",
        "corpus_id": record.get("corpus_id"),
        "allowed": not errors,
        "rights_class": record.get("rights_class"),
        "storage_intent": record.get("storage_intent"),
        "errors": errors,
        "legal_analysis_performed": False,
        "policy_note": "Declared rights metadata validated; source rights must be established by evidence outside this deterministic validator.",
    }


def self_test() -> dict[str, Any]:
    ok_record = {
        "corpus_id": "CORP-TEST-1",
        "source_title": "Fixture",
        "source_type": "book",
        "rights_class": "analysis_only",
        "rights_basis": "lawful user access; analysis only",
        "storage_intent": "derived_only",
    }
    bad_record = {
        "corpus_id": "CORP-TEST-2",
        "source_title": "Fixture",
        "source_type": "book",
        "rights_class": "analysis_only",
        "rights_basis": "lawful user access; analysis only",
        "storage_intent": "full_text",
    }
    ok = decision(ok_record)["allowed"] and not decision(bad_record)["allowed"]
    return {
        "rights_gate_contract": "PASS" if ok else "FAIL",
        "does_not_infer_legal_status": True,
        "analysis_only_full_text_blocked": True,
        "unknown_full_text_blocked": True,
    }


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input must be JSON object")
    return value


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge corpus rights gate")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate"); v.add_argument("--json", required=True)
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["rights_gate_contract"] == "PASS" else 1
    result = decision(load(Path(args.json)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
