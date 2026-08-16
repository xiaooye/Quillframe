#!/usr/bin/env python3
"""Deterministic required-context assembly receipts for NovelForge.

The semantic selector owns relevance. This runtime only proves that the IDs a
manager/model selected are legal for the requested stage and satisfy explicitly
declared context obligations. Missing required obligations fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import context_inspector

SCHEMA = "novelforge_context_assembly_v1"
RECEIPT_SCHEMA = "novelforge_context_assembly_receipt_v1"
STATUSES = {"satisfied", "missing_required", "invalid_selection"}


def _fp(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _normalize_obligation(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("context obligation must be object")
    required = raw.get("required", True)
    if not isinstance(required, bool):
        raise ValueError("obligation.required must be boolean")
    authorities = raw.get("allowed_authorities", [])
    if not isinstance(authorities, list) or any(x not in context_inspector.AUTHORITIES for x in authorities):
        raise ValueError("obligation.allowed_authorities invalid")
    return {
        "obligation_id": _nonempty(raw.get("obligation_id"), "obligation_id"),
        "class": _nonempty(raw.get("class"), "class"),
        "purpose": _nonempty(raw.get("purpose"), "purpose"),
        "required": required,
        "allowed_authorities": sorted(set(authorities)),
        "require_source_fingerprint": bool(raw.get("require_source_fingerprint", False)),
    }


def _item_purposes(item: dict[str, Any]) -> set[str]:
    metadata = item.get("metadata", {})
    values = metadata.get("purposes", [])
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return set()
    return {x for x in values if isinstance(x, str) and x}


def assemble(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("assembly payload must be object")
    if payload.get("schema") not in {None, SCHEMA}:
        raise ValueError("invalid assembly schema")
    run_id = _nonempty(payload.get("run_id"), "run_id")
    stage = payload.get("stage")
    if stage not in context_inspector.STAGES:
        raise ValueError("invalid assembly stage")
    manifest = payload.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("manifest required")
    selected_ids = payload.get("selected_item_ids", [])
    if not isinstance(selected_ids, list) or any(not isinstance(x, str) or not x for x in selected_ids):
        raise ValueError("selected_item_ids must be string array")
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selected_item_ids must be unique")
    obligations = [_normalize_obligation(x) for x in payload.get("obligations", [])]
    if len({x["obligation_id"] for x in obligations}) != len(obligations):
        raise ValueError("duplicate obligation_id")

    view = context_inspector.inspect(manifest, payload.get("overlay"), stage=stage)
    by_id = {x["id"]: x for x in view["items"]}
    unknown = [x for x in selected_ids if x not in by_id]
    ineligible = [x for x in selected_ids if x in by_id and not by_id[x]["eligible"]]
    selected = [by_id[x] for x in selected_ids if x in by_id and by_id[x]["eligible"]]

    results = []
    missing_required = []
    for obligation in obligations:
        matches = []
        for item in selected:
            if item["class"] != obligation["class"]:
                continue
            if obligation["purpose"] not in _item_purposes(item):
                continue
            if obligation["allowed_authorities"] and item["authority"] not in obligation["allowed_authorities"]:
                continue
            if obligation["require_source_fingerprint"] and not item.get("source_fingerprint"):
                continue
            matches.append(item["id"])
        satisfied = bool(matches)
        if obligation["required"] and not satisfied:
            missing_required.append(obligation["obligation_id"])
        results.append({**obligation, "satisfied": satisfied, "satisfied_by": sorted(matches)})

    status = "satisfied"
    if unknown or ineligible:
        status = "invalid_selection"
    elif missing_required:
        status = "missing_required"

    body = {
        "schema": RECEIPT_SCHEMA,
        "run_id": run_id,
        "manifest_id": view.get("manifest_id"),
        "stage": stage,
        "selected_item_ids": sorted(selected_ids),
        "obligations": results,
        "unknown_selected_ids": sorted(unknown),
        "ineligible_selected_ids": sorted(ineligible),
        "missing_required_obligations": sorted(missing_required),
        "status": status,
        "proceed": status == "satisfied",
        "semantic_relevance_judged_by_runtime": False,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False},
        "model_execution": False,
    }
    body["receipt_fingerprint"] = _fp(body)
    return body


def self_test() -> dict[str, Any]:
    fp = "sha256:" + "a" * 64
    manifest = {"manifest_id": "CTX-A", "items": [
        {"id": "PROFILE", "class": "project_profile", "authority": "locked", "source_fingerprint": fp,
         "stages": ["writer_pre_draft"], "metadata": {"purposes": ["prose_realization"]}},
        {"id": "PREF", "class": "author_model", "authority": "learning", "source_fingerprint": fp,
         "stages": ["writer_pre_draft"], "metadata": {"purposes": ["author_intent"]}},
        {"id": "PRIVATE", "class": "private_character_state", "authority": "derived",
         "stages": ["character_simulation"], "metadata": {"purposes": ["character_reasoning"]}},
        {"id": "REAL", "class": "realization_projection", "authority": "derived", "source_fingerprint": fp,
         "stages": ["realization_projection", "writer_pre_draft"], "metadata": {"purposes": ["scene_realization"]}},
    ]}
    obligations = [
        {"obligation_id": "O-PROFILE", "class": "project_profile", "purpose": "prose_realization", "required": True,
         "allowed_authorities": ["locked", "accepted"], "require_source_fingerprint": True},
        {"obligation_id": "O-REAL", "class": "realization_projection", "purpose": "scene_realization", "required": True,
         "allowed_authorities": ["derived"], "require_source_fingerprint": True},
    ]
    ok = assemble({"schema": SCHEMA, "run_id": "RUN-1", "stage": "writer_pre_draft", "manifest": manifest,
                   "selected_item_ids": ["PROFILE", "REAL"], "obligations": obligations})
    missing = assemble({"schema": SCHEMA, "run_id": "RUN-2", "stage": "writer_pre_draft", "manifest": manifest,
                        "selected_item_ids": ["PROFILE"], "obligations": obligations})
    private = assemble({"schema": SCHEMA, "run_id": "RUN-3", "stage": "writer_pre_draft", "manifest": manifest,
                        "selected_item_ids": ["PROFILE", "PRIVATE", "REAL"], "obligations": obligations})
    optional = assemble({"schema": SCHEMA, "run_id": "RUN-4", "stage": "writer_pre_draft", "manifest": manifest,
                         "selected_item_ids": ["PROFILE", "REAL"], "obligations": [*obligations,
                         {"obligation_id": "O-CORPUS", "class": "corpus_benchmark", "purpose": "paragraph_rhythm", "required": False}]})
    passed = all([
        ok["proceed"], ok["status"] == "satisfied",
        not missing["proceed"] and missing["status"] == "missing_required" and "O-REAL" in missing["missing_required_obligations"],
        not private["proceed"] and private["status"] == "invalid_selection" and "PRIVATE" in private["ineligible_selected_ids"],
        optional["proceed"] and optional["obligations"][-1]["satisfied"] is False,
        ok["semantic_relevance_judged_by_runtime"] is False,
    ])
    return {
        "schema": SCHEMA,
        "context_assembly_contract": "PASS" if passed else "FAIL",
        "required_present_proceeds": ok["proceed"],
        "required_missing_blocks": not missing["proceed"],
        "private_writer_selection_blocks": not private["proceed"],
        "optional_missing_proceeds": optional["proceed"],
        "semantic_relevance_judged_by_runtime": False,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge required-context assembly")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("assemble"); a.add_argument("--input", required=True); a.add_argument("--output")
    sub.add_parser("self-test")
    ns = p.parse_args()
    if ns.cmd == "self-test":
        out = self_test()
    else:
        out = assemble(json.loads(Path(ns.input).read_text(encoding="utf-8")))
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if ns.cmd == "assemble" and ns.output:
        Path(ns.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if out.get("context_assembly_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
