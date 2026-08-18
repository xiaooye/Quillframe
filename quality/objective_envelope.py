#!/usr/bin/env python3
"""Fingerprint-bound creative objective envelope for repair-safe Quillframe runs.

The manager/model selects a compact set of current objectives from authorized
Project/request evidence. This deterministic module validates provenance,
lineage and tamper resistance only; it does not decide which literary objectives
matter. Rejected realization text and critique history are not valid objective
sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_objective_envelope_v1"
CATEGORIES = {
    "story", "reader", "character_relationship", "pressure", "reward",
    "payoff_forward_pull", "profile", "user_direction", "continuity",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{name} must be non-empty string array")
    return [x.strip() for x in value]


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _payload(envelope: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in envelope.items() if k != "fingerprint"}


def build(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("objective envelope input must be object")
    subject_id = _nonempty(payload.get("subject_id"), "subject_id")
    run_id = _nonempty(payload.get("run_id"), "run_id")
    authority_cutoff = _nonempty(payload.get("authority_cutoff"), "authority_cutoff")
    if payload.get("derived_from_rejected_realization") is not False:
        raise ValueError("objective envelope must declare derived_from_rejected_realization=false")

    raw_items = payload.get("objective_items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("objective_items must be non-empty array")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError(f"objective_items[{index}] must be object")
        item_id = _nonempty(raw.get("id"), f"objective_items[{index}].id")
        if item_id in seen:
            raise ValueError(f"duplicate objective item id: {item_id}")
        seen.add(item_id)
        category = raw.get("category")
        if category not in CATEGORIES:
            raise ValueError(f"objective_items[{index}].category invalid")
        items.append({
            "id": item_id,
            "category": category,
            "statement": _nonempty(raw.get("statement"), f"objective_items[{index}].statement"),
            "source_refs": _refs(raw.get("source_refs"), f"objective_items[{index}].source_refs"),
        })

    must_preserve = payload.get("must_preserve")
    if not isinstance(must_preserve, list) or not must_preserve or any(not isinstance(x, str) or not x.strip() for x in must_preserve):
        raise ValueError("must_preserve must be non-empty string array")

    supersedes = payload.get("supersedes_fingerprint")
    change_authority_ref = payload.get("change_authority_ref")
    if supersedes is not None:
        supersedes = _sha(supersedes, "supersedes_fingerprint")
        change_authority_ref = _nonempty(change_authority_ref, "change_authority_ref")
    elif change_authority_ref is not None:
        raise ValueError("change_authority_ref requires supersedes_fingerprint")

    envelope: dict[str, Any] = {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "run_id": run_id,
        "authority_cutoff": authority_cutoff,
        "objective_items": items,
        "must_preserve": [x.strip() for x in must_preserve],
        "derived_from_rejected_realization": False,
        "supersedes_fingerprint": supersedes,
        "change_authority_ref": change_authority_ref,
        "semantic_completeness_judged_by_runtime": False,
        "authority": False,
        "permissions": {
            "canon_write": False,
            "framework_write": False,
            "durable_user_taste_write": False,
        },
        "model_execution": False,
    }
    envelope["fingerprint"] = _fingerprint(_payload(envelope))
    return envelope


def validate(envelope: Any, *, subject_id: str | None = None, run_id: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(envelope, dict):
        return ["objective envelope must be object"]
    if envelope.get("schema") != SCHEMA:
        errors.append("objective envelope schema mismatch")
    try:
        rebuilt = build({
            "subject_id": envelope.get("subject_id"),
            "run_id": envelope.get("run_id"),
            "authority_cutoff": envelope.get("authority_cutoff"),
            "objective_items": envelope.get("objective_items"),
            "must_preserve": envelope.get("must_preserve"),
            "derived_from_rejected_realization": envelope.get("derived_from_rejected_realization"),
            "supersedes_fingerprint": envelope.get("supersedes_fingerprint"),
            "change_authority_ref": envelope.get("change_authority_ref"),
        })
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    if subject_id is not None and envelope.get("subject_id") != subject_id:
        errors.append("objective envelope subject_id mismatch")
    if run_id is not None and envelope.get("run_id") != run_id:
        errors.append("objective envelope run_id mismatch")
    if envelope.get("fingerprint") != rebuilt["fingerprint"]:
        errors.append("objective envelope fingerprint mismatch")
    if envelope.get("semantic_completeness_judged_by_runtime") is not False:
        errors.append("runtime must not claim objective semantic completeness")
    if envelope.get("authority") is not False:
        errors.append("objective envelope must be non-authoritative")
    return errors


def self_test() -> dict[str, Any]:
    base = {
        "subject_id": "CH-SYN",
        "run_id": "RUN-SYN",
        "authority_cutoff": "active_plan+project_profile+current_user_direction",
        "objective_items": [
            {"id": "OBJ-1", "category": "reader", "statement": "Keep a live unresolved reader question.", "source_refs": ["plan:synthetic"]},
            {"id": "OBJ-2", "category": "character_relationship", "statement": "Keep interpersonal resistance and relationship energy.", "source_refs": ["profile:synthetic"]},
        ],
        "must_preserve": ["reader question", "causal pressure", "character energy"],
        "derived_from_rejected_realization": False,
    }
    envelope = build(base)
    valid = not validate(envelope, subject_id="CH-SYN", run_id="RUN-SYN")
    tampered = json.loads(json.dumps(envelope)); tampered["must_preserve"].append("invented")
    tamper_guard = any("fingerprint" in x for x in validate(tampered))
    rejected_guard = False
    try:
        build({**base, "derived_from_rejected_realization": True})
    except ValueError:
        rejected_guard = True
    steering_guard = False
    try:
        build({**base, "supersedes_fingerprint": envelope["fingerprint"]})
    except ValueError:
        steering_guard = True
    updated = build({**base, "supersedes_fingerprint": envelope["fingerprint"], "change_authority_ref": "user:explicit-steering"})
    checks = {
        "valid_compact_envelope": valid,
        "tamper_detected": tamper_guard,
        "rejected_realization_cannot_source_objective": rejected_guard,
        "objective_change_requires_authority_ref": steering_guard,
        "explicit_user_steering_can_supersede": updated["supersedes_fingerprint"] == envelope["fingerprint"],
        "runtime_does_not_judge_semantic_completeness": envelope["semantic_completeness_judged_by_runtime"] is False,
        "model_execution": envelope["model_execution"] is False,
    }
    return {
        "schema": SCHEMA,
        "objective_envelope_contract": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    build_cmd = sub.add_parser("build"); build_cmd.add_argument("--input", required=True); build_cmd.add_argument("--output")
    args = parser.parse_args()
    if args.command == "self-test":
        out = self_test(); print(json.dumps(out, ensure_ascii=False, indent=2)); return 0 if out["objective_envelope_contract"] == "PASS" else 1
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = build(payload)
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if args.output: Path(args.output).write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
