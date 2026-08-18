#!/usr/bin/env python3
"""Deterministic execution-boundary receipt for selected Quillframe context.

The model/manager owns the semantic questions: what information is missing,
what to search, which result is relevant, and when context is sufficient.  This
module verifies only execution truth after that semantic choice: selected ids
exist, are legal for the receiving stage, do not cross private/hidden
boundaries, and satisfy any *exact artifact identities/fingerprints* explicitly
required by higher authority.

Generic class/purpose obligations are intentionally not interpreted here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import context_inspector

SCHEMA = "quillframe_context_assembly_v2"
LEGACY_SCHEMA = "quillframe_context_assembly_v1"
RECEIPT_SCHEMA = "quillframe_context_assembly_receipt_v2"
STATUSES = {"satisfied", "missing_required_ref", "invalid_selection"}


def _fp(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _sha(value: Any, name: str) -> str:
    value = _nonempty(value, name)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _required_refs(payload: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    """Normalize exact authority/runtime-required artifacts.

    `required_item_ids` means an upstream authority has already named the exact
    artifact identity.  It does not mean this runtime has inferred that a class
    of literary context is necessary.
    """
    required = payload.get("required_item_ids", [])
    if not isinstance(required, list) or any(not isinstance(x, str) or not x.strip() for x in required):
        raise ValueError("required_item_ids must be string array")
    required = [x.strip() for x in required]
    if len(required) != len(set(required)):
        raise ValueError("required_item_ids must be unique")

    expected = payload.get("required_source_fingerprints", {})
    if not isinstance(expected, dict):
        raise ValueError("required_source_fingerprints must be object")
    normalized: dict[str, str] = {}
    for item_id, fingerprint in expected.items():
        item_id = _nonempty(item_id, "required_source_fingerprints key")
        if item_id not in required:
            raise ValueError("fingerprint requirement must name an exact required_item_id")
        normalized[item_id] = _sha(fingerprint, f"required_source_fingerprints.{item_id}")
    return required, normalized


def assemble(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("assembly payload must be object")
    schema = payload.get("schema")
    if schema not in {None, SCHEMA, LEGACY_SCHEMA}:
        raise ValueError("invalid assembly schema")
    if payload.get("obligations"):
        raise ValueError(
            "semantic class/purpose obligations are not a deterministic context gate in v2; "
            "use agent context selection/search, or name an exact required_item_id when higher authority requires one"
        )

    run_id = _nonempty(payload.get("run_id"), "run_id")
    stage = payload.get("stage")
    if stage not in context_inspector.STAGES:
        raise ValueError("invalid assembly stage")
    manifest = payload.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("manifest required")

    selected_ids = payload.get("selected_item_ids", [])
    if not isinstance(selected_ids, list) or any(not isinstance(x, str) or not x.strip() for x in selected_ids):
        raise ValueError("selected_item_ids must be string array")
    selected_ids = [x.strip() for x in selected_ids]
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selected_item_ids must be unique")

    required_ids, expected_fingerprints = _required_refs(payload)
    view = context_inspector.inspect(manifest, payload.get("overlay"), stage=stage)
    by_id = {x["id"]: x for x in view["items"]}

    unknown = sorted(x for x in selected_ids if x not in by_id)
    ineligible = sorted(x for x in selected_ids if x in by_id and not by_id[x]["eligible"])
    selected_eligible = {x for x in selected_ids if x in by_id and by_id[x]["eligible"]}

    missing_required = sorted(x for x in required_ids if x not in selected_eligible)
    fingerprint_mismatches: list[str] = []
    for item_id, expected in expected_fingerprints.items():
        item = by_id.get(item_id)
        if item is None or not item.get("eligible"):
            continue
        if item.get("source_fingerprint") != expected:
            fingerprint_mismatches.append(item_id)
    fingerprint_mismatches.sort()

    status = "satisfied"
    if unknown or ineligible or fingerprint_mismatches:
        status = "invalid_selection"
    elif missing_required:
        status = "missing_required_ref"

    body = {
        "schema": RECEIPT_SCHEMA,
        "run_id": run_id,
        "manifest_id": view.get("manifest_id"),
        "stage": stage,
        "selected_item_ids": sorted(selected_ids),
        "required_item_ids": sorted(required_ids),
        "unknown_selected_ids": unknown,
        "ineligible_selected_ids": ineligible,
        "missing_required_item_ids": missing_required,
        "source_fingerprint_mismatches": fingerprint_mismatches,
        "status": status,
        "proceed": status == "satisfied",
        "semantic_relevance_judged_by_runtime": False,
        "context_sufficiency_judged_by_runtime": False,
        "semantic_obligation_matching_supported": False,
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
        {"id": "REMOTE", "class": "canon", "authority": "accepted", "source_fingerprint": fp,
         "stages": ["writer_pre_draft"], "metadata": {"purposes": ["whatever-the-agent-needs"]}},
        {"id": "PRIVATE", "class": "private_character_state", "authority": "derived", "source_fingerprint": fp,
         "stages": ["character_simulation"], "metadata": {"purposes": ["character_reasoning"]}},
    ]}

    ok = assemble({
        "schema": SCHEMA, "run_id": "RUN-1", "stage": "writer_pre_draft", "manifest": manifest,
        "selected_item_ids": ["REMOTE"], "required_item_ids": ["REMOTE"],
        "required_source_fingerprints": {"REMOTE": fp},
    })
    missing = assemble({
        "schema": SCHEMA, "run_id": "RUN-2", "stage": "writer_pre_draft", "manifest": manifest,
        "selected_item_ids": [], "required_item_ids": ["REMOTE"],
    })
    private = assemble({
        "schema": SCHEMA, "run_id": "RUN-3", "stage": "writer_pre_draft", "manifest": manifest,
        "selected_item_ids": ["PRIVATE"], "required_item_ids": [],
    })
    mismatch = assemble({
        "schema": SCHEMA, "run_id": "RUN-4", "stage": "writer_pre_draft", "manifest": manifest,
        "selected_item_ids": ["REMOTE"], "required_item_ids": ["REMOTE"],
        "required_source_fingerprints": {"REMOTE": "sha256:" + "b" * 64},
    })
    legacy_semantic_obligation_rejected = False
    try:
        assemble({
            "schema": LEGACY_SCHEMA, "run_id": "RUN-5", "stage": "writer_pre_draft", "manifest": manifest,
            "selected_item_ids": ["PROFILE"],
            "obligations": [{"obligation_id": "O", "class": "project_profile", "purpose": "prose_realization"}],
        })
    except ValueError:
        legacy_semantic_obligation_rejected = True

    passed = all([
        ok["proceed"] and ok["status"] == "satisfied",
        not missing["proceed"] and missing["status"] == "missing_required_ref",
        not private["proceed"] and "PRIVATE" in private["ineligible_selected_ids"],
        not mismatch["proceed"] and "REMOTE" in mismatch["source_fingerprint_mismatches"],
        legacy_semantic_obligation_rejected,
        ok["semantic_relevance_judged_by_runtime"] is False,
        ok["context_sufficiency_judged_by_runtime"] is False,
    ])
    return {
        "schema": SCHEMA,
        "context_assembly_contract": "PASS" if passed else "FAIL",
        "exact_required_ref_missing_blocks": not missing["proceed"],
        "required_missing_blocks": not missing["proceed"],
        "private_writer_selection_blocks": not private["proceed"],
        "source_fingerprint_mismatch_blocks": not mismatch["proceed"],
        "legacy_semantic_obligation_rejected": legacy_semantic_obligation_rejected,
        "semantic_relevance_judged_by_runtime": False,
        "context_sufficiency_judged_by_runtime": False,
        "semantic_obligation_matching_supported": False,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe context execution-boundary receipt")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("assemble")
    a.add_argument("--input", required=True)
    a.add_argument("--output")
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