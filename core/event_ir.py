#!/usr/bin/env python3
"""Causal Event IR for NovelForge scene simulation.

Event IR is a pre-prose candidate representation. It binds actors, causal beats,
reader-question movement and typed state deltas to evidence/fingerprints while
remaining explicitly non-authoritative.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_event_ir_v1"
DELTA_KEYS = ("state_delta", "knowledge_delta", "relationship_delta", "resource_delta")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} required")
    return value.strip()


def _sha(value: Any, name: str) -> str:
    value = _text(value, name)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} invalid hex") from exc
    return value


def _string_list(value: Any, name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{name} must be string list")
    out = [item.strip() for item in value]
    if not allow_empty and not out:
        raise ValueError(f"{name} must not be empty")
    if len(out) != len(set(out)):
        raise ValueError(f"{name} contains duplicates")
    return out


def _delta_list(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be list")
    out: list[dict[str, Any]] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise ValueError(f"{name}[{index}] must be object")
        subject_id = _text(row.get("subject_id"), f"{name}[{index}].subject_id")
        field = _text(row.get("field"), f"{name}[{index}].field")
        evidence_refs = _string_list(row.get("evidence_refs", []), f"{name}[{index}].evidence_refs", allow_empty=False)
        metadata = row.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError(f"{name}[{index}].metadata must be object")
        out.append({
            "subject_id": subject_id,
            "field": field,
            "before": row.get("before"),
            "after": row.get("after"),
            "evidence_refs": evidence_refs,
            "metadata": metadata,
        })
    return out


def normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("event must be object")
    if raw.get("schema") not in {None, SCHEMA}:
        raise ValueError("wrong event schema")
    if raw.get("authority") is True or raw.get("canon_write") is True or raw.get("settlement_authority") is True:
        raise ValueError("Event IR cannot grant authority")
    story_order = raw.get("story_order")
    if isinstance(story_order, bool) or not isinstance(story_order, int) or story_order < 0:
        raise ValueError("story_order must be non-negative integer")
    actors = _string_list(raw.get("actors"), "actors", allow_empty=False)
    event = {
        "schema": SCHEMA,
        "event_id": _text(raw.get("event_id"), "event_id"),
        "scene_id": _text(raw.get("scene_id"), "scene_id"),
        "story_order": story_order,
        "actors": actors,
        "preconditions": _string_list(raw.get("preconditions", []), "preconditions"),
        "intent": _text(raw.get("intent"), "intent"),
        "action": _text(raw.get("action"), "action"),
        "obstacle": _text(raw.get("obstacle"), "obstacle"),
        "response": _text(raw.get("response"), "response"),
        "consequence": _text(raw.get("consequence"), "consequence"),
        "reader_question_before": raw.get("reader_question_before") if raw.get("reader_question_before") is None or isinstance(raw.get("reader_question_before"), str) else None,
        "reader_question_after": raw.get("reader_question_after") if raw.get("reader_question_after") is None or isinstance(raw.get("reader_question_after"), str) else None,
        "reader_reward": _string_list(raw.get("reader_reward", []), "reader_reward"),
        "source_refs": _string_list(raw.get("source_refs", []), "source_refs", allow_empty=False),
        "evidence_refs": _string_list(raw.get("evidence_refs", []), "evidence_refs", allow_empty=False),
        "subject_fingerprint": _sha(raw.get("subject_fingerprint"), "subject_fingerprint"),
        "authority": False,
        "canon_write": False,
        "settlement_authority": False,
    }
    for key in DELTA_KEYS:
        event[key] = _delta_list(raw.get(key, []), key)
    event["event_fingerprint"] = fingerprint(event)
    return event


def self_test() -> int:
    raw = {
        "schema": SCHEMA,
        "event_id": "EVT-1",
        "scene_id": "SCN-1",
        "story_order": 3,
        "actors": ["CHAR-A", "CHAR-B"],
        "preconditions": ["CHAR-A needs the ledger", "CHAR-B controls access"],
        "intent": "CHAR-A tries to secure the ledger without exposing the real motive.",
        "action": "CHAR-A offers a face-saving exchange.",
        "obstacle": "CHAR-B suspects the offer hides another agenda.",
        "response": "CHAR-B agrees only after adding a costly condition.",
        "consequence": "CHAR-A gets access but loses freedom of action.",
        "state_delta": [{"subject_id": "SCN-1", "field": "ledger_access", "before": False, "after": True, "evidence_refs": ["event:exchange"]}],
        "knowledge_delta": [{"subject_id": "CHAR-B", "field": "suspicion", "before": "low", "after": "high", "evidence_refs": ["event:hidden-agenda-signal"]}],
        "relationship_delta": [{"subject_id": "REL-A-B", "field": "trust", "before": 2, "after": 1, "evidence_refs": ["event:conditional-agreement"]}],
        "resource_delta": [{"subject_id": "RES-A", "field": "freedom_of_action", "before": 3, "after": 2, "evidence_refs": ["event:costly-condition"]}],
        "reader_question_before": "Can CHAR-A get access?",
        "reader_question_after": "What will the added condition force CHAR-A to sacrifice?",
        "reader_reward": ["competence", "costly win"],
        "source_refs": ["plan:SCN-1"],
        "evidence_refs": ["sim:CHAR-A", "sim:CHAR-B", "resolve:SCN-1"],
        "subject_fingerprint": "sha256:" + "a" * 64,
        "authority": False,
        "canon_write": False,
    }
    event = normalize_event(raw)
    causal = bool(event["knowledge_delta"]) and bool(event["relationship_delta"]) and bool(event["resource_delta"]) and len(event["actors"]) == 2
    noncanon = event["authority"] is False and event["canon_write"] is False and event["settlement_authority"] is False
    guard = False
    bad = json.loads(json.dumps(raw))
    bad["authority"] = True
    try:
        normalize_event(bad)
    except ValueError:
        guard = True
    ok = causal and noncanon and guard and event["event_fingerprint"].startswith("sha256:")
    print(json.dumps({
        "event_ir_contract": "PASS" if ok else "FAIL",
        "multi_character_causal_event": causal,
        "non_authoritative": noncanon,
        "authority_guard": guard,
        "fingerprint_bound": True,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge Event IR validator")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--output")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    event = normalize_event(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(event, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
