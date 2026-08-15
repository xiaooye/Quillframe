#!/usr/bin/env python3
"""Aggregate non-authoritative candidate state deltas from Event IR evidence.

The result describes candidate before→after transitions for verification and
review. It does not mutate Project state and does not grant Settlement authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_candidate_state_delta_v1"
EVENT_DOMAINS = {
    "state_delta": "state",
    "knowledge_delta": "knowledge",
    "relationship_delta": "relationship",
    "resource_delta": "resource",
}
ALLOWED_DOMAINS = {"state", "knowledge", "relationship", "resource", "obligation", "location"}


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


def build_delta(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    base_fingerprint = _sha(payload.get("base_state_fingerprint"), "base_state_fingerprint")
    candidate_fingerprint = _sha(payload.get("candidate_fingerprint"), "candidate_fingerprint")

    changes: list[dict[str, Any]] = []
    events = payload.get("events", [])
    if not isinstance(events, list):
        raise ValueError("events must be list")
    normalized_events: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict) or event.get("schema") != "novelforge_event_ir_v1":
            raise ValueError("events must be normalized Event IR")
        if event.get("subject_fingerprint") != base_fingerprint:
            raise ValueError("event subject fingerprint mismatch")
        story_order = event.get("story_order")
        if isinstance(story_order, bool) or not isinstance(story_order, int) or story_order < 0:
            raise ValueError("event.story_order invalid")
        normalized_events.append(event)

    for event in sorted(normalized_events, key=lambda item: (item["story_order"], item.get("event_id", ""))):
        event_id = _text(event.get("event_id"), "event.event_id")
        for key, domain in EVENT_DOMAINS.items():
            rows = event.get(key, [])
            if not isinstance(rows, list):
                raise ValueError(f"event.{key} must be list")
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError(f"event.{key} row must be object")
                evidence_refs = row.get("evidence_refs", [])
                if not isinstance(evidence_refs, list) or not evidence_refs or not all(isinstance(ref, str) and ref.strip() for ref in evidence_refs):
                    raise ValueError(f"event.{key} evidence_refs required")
                changes.append({
                    "domain": domain,
                    "subject_id": _text(row.get("subject_id"), f"{key}.subject_id"),
                    "field": _text(row.get("field"), f"{key}.field"),
                    "before": row.get("before"),
                    "after": row.get("after"),
                    "evidence_refs": [ref.strip() for ref in evidence_refs],
                    "event_ids": [event_id],
                })

    supplemental = payload.get("supplemental_changes", [])
    if not isinstance(supplemental, list):
        raise ValueError("supplemental_changes must be list")
    for row in supplemental:
        if not isinstance(row, dict) or row.get("domain") not in ALLOWED_DOMAINS:
            raise ValueError("invalid supplemental change domain")
        evidence_refs = row.get("evidence_refs", [])
        if not isinstance(evidence_refs, list) or not evidence_refs or not all(isinstance(ref, str) and ref.strip() for ref in evidence_refs):
            raise ValueError("supplemental change evidence_refs required")
        event_ids = row.get("event_ids", [])
        if not isinstance(event_ids, list) or not all(isinstance(event_id, str) and event_id.strip() for event_id in event_ids):
            raise ValueError("supplemental change event_ids must be string list")
        changes.append({
            "domain": row["domain"],
            "subject_id": _text(row.get("subject_id"), "supplemental.subject_id"),
            "field": _text(row.get("field"), "supplemental.field"),
            "before": row.get("before"),
            "after": row.get("after"),
            "evidence_refs": [ref.strip() for ref in evidence_refs],
            "event_ids": [event_id.strip() for event_id in event_ids],
        })

    aggregated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for change in changes:
        key = (change["domain"], change["subject_id"], change["field"])
        if key not in aggregated:
            aggregated[key] = json.loads(json.dumps(change))
            continue
        current = aggregated[key]
        if current["after"] != change["before"]:
            raise ValueError(
                f"non-causal delta chain for {key}: expected before={current['after']!r}, got {change['before']!r}"
            )
        current["after"] = change["after"]
        current["evidence_refs"] = list(dict.fromkeys(current["evidence_refs"] + change["evidence_refs"]))
        current["event_ids"] = list(dict.fromkeys(current["event_ids"] + change["event_ids"]))

    normalized = sorted(aggregated.values(), key=lambda change: (change["domain"], change["subject_id"], change["field"]))
    core = {
        "artifact_ref": _text(payload.get("artifact_ref"), "artifact_ref"),
        "base_state_fingerprint": base_fingerprint,
        "candidate_fingerprint": candidate_fingerprint,
        "changes": normalized,
        "source_event_ids": sorted({_text(event.get("event_id"), "event.event_id") for event in normalized_events}),
    }
    return {
        "schema": SCHEMA,
        **core,
        "delta_fingerprint": fingerprint(core),
        "change_count": len(normalized),
        "authority": False,
        "canon_write": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    base = "sha256:" + "a" * 64
    event1 = {
        "schema": "novelforge_event_ir_v1", "event_id": "E1", "story_order": 1, "subject_fingerprint": base,
        "state_delta": [{"subject_id": "CHAR-A", "field": "location", "before": "hall", "after": "door", "evidence_refs": ["e1"]}],
        "knowledge_delta": [], "relationship_delta": [], "resource_delta": [],
    }
    event2 = {
        "schema": "novelforge_event_ir_v1", "event_id": "E2", "story_order": 2, "subject_fingerprint": base,
        "state_delta": [{"subject_id": "CHAR-A", "field": "location", "before": "door", "after": "street", "evidence_refs": ["e2"]}],
        "knowledge_delta": [], "relationship_delta": [], "resource_delta": [],
    }
    report = build_delta({
        "artifact_ref": "candidate:CH1",
        "base_state_fingerprint": base,
        "candidate_fingerprint": "sha256:" + "b" * 64,
        "events": [event2, event1],
        "supplemental_changes": [{
            "domain": "obligation", "subject_id": "OBL-1", "field": "status", "before": "open", "after": "tightened", "evidence_refs": ["candidate:p4"],
        }],
    })
    location = next(change for change in report["changes"] if change["domain"] == "state" and change["field"] == "location")
    chain = location["before"] == "hall" and location["after"] == "street" and location["event_ids"] == ["E1", "E2"]
    noncanon = report["authority"] is False and report["settlement_authority"] is False
    guard = False
    bad_event2 = json.loads(json.dumps(event2))
    bad_event2["state_delta"][0]["before"] = "wrong"
    try:
        build_delta({
            "artifact_ref": "candidate:CH1",
            "base_state_fingerprint": base,
            "candidate_fingerprint": "sha256:" + "b" * 64,
            "events": [event1, bad_event2],
        })
    except ValueError:
        guard = True
    obligation = any(change["domain"] == "obligation" for change in report["changes"])
    ok = chain and noncanon and guard and obligation
    print(json.dumps({
        "candidate_state_delta_contract": "PASS" if ok else "FAIL",
        "causal_chain_collapsed": chain,
        "supplemental_obligation_supported": obligation,
        "before_state_chain_guard": guard,
        "non_authoritative": noncanon,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge candidate state delta aggregator")
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--input", required=True)
    build_parser.add_argument("--output")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    report = build_delta(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
