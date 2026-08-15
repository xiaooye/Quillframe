#!/usr/bin/env python3
"""Deterministic conjunctive user-visible prose readiness gate.

Semantic systems produce the underlying Surface, Reader Engagement, continuity
and independent-review judgments. This module only binds those gate receipts to
one candidate fingerprint and applies fail-closed release policy. It never
averages literary scores and never grants Canon authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_production_readiness_v1"
CATEGORIES = {"surface", "reader_engagement", "continuity", "semantic_independent"}
STATUSES = {"pass", "fail", "pending"}
READER_GRIP = {"low", "medium", "high", "very_high"}


def _fp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("readiness payload must be object")
    candidate = _fp(payload.get("candidate_fingerprint"), "candidate_fingerprint")
    policy = payload.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("policy object required")
    grip = policy.get("reader_grip")
    if grip not in READER_GRIP:
        raise ValueError("policy.reader_grip invalid")
    require_continuity = policy.get("require_continuity", True)
    require_semantic = policy.get("require_independent_semantic", False)
    if not isinstance(require_continuity, bool) or not isinstance(require_semantic, bool):
        raise ValueError("policy requirement flags must be boolean")

    required = ["surface", "reader_engagement"]
    if require_continuity:
        required.append("continuity")
    if require_semantic:
        required.append("semantic_independent")

    raw_gates = payload.get("gates")
    if not isinstance(raw_gates, list):
        raise ValueError("gates list required")
    gates: dict[str, dict[str, Any]] = {}
    for raw in raw_gates:
        if not isinstance(raw, dict):
            raise ValueError("gate must be object")
        category = raw.get("category")
        if category not in CATEGORIES:
            raise ValueError(f"unknown gate category: {category}")
        if category in gates:
            raise ValueError(f"duplicate gate category: {category}")
        gate_fp = _fp(raw.get("candidate_fingerprint"), f"{category}.candidate_fingerprint")
        if gate_fp != candidate:
            raise ValueError(f"candidate fingerprint mismatch: {category}")
        status = raw.get("status")
        if status not in STATUSES:
            raise ValueError(f"invalid gate status: {category}")
        codes = raw.get("codes", [])
        refs = raw.get("evidence_refs", [])
        if not isinstance(codes, list) or not all(isinstance(x, str) and x for x in codes):
            raise ValueError(f"{category}.codes must be string list")
        if not isinstance(refs, list) or not all(isinstance(x, str) and x for x in refs):
            raise ValueError(f"{category}.evidence_refs must be string list")
        if category == "reader_engagement" and "RG-15" in codes and status == "pass":
            raise ValueError("RG-15 SAFE-BUT-FLAT cannot pass reader_engagement")
        gates[category] = {
            "category": category,
            "status": status,
            "candidate_fingerprint": gate_fp,
            "codes": list(codes),
            "evidence_refs": list(refs),
        }

    missing = [x for x in required if x not in gates]
    blocking = [x for x in required if x in gates and gates[x]["status"] == "fail"]
    pending = missing + [x for x in required if x in gates and gates[x]["status"] == "pending"]
    ready = not blocking and not pending and all(gates[x]["status"] == "pass" for x in required)
    return {
        "schema": SCHEMA,
        "candidate_fingerprint": candidate,
        "policy": {
            "reader_grip": grip,
            "require_continuity": require_continuity,
            "require_independent_semantic": require_semantic,
        },
        "required_gates": required,
        "gates": [gates[k] for k in sorted(gates)],
        "blocking_gates": blocking,
        "pending_gates": pending,
        "ready_for_user_visible_review": ready,
        "conjunctive_gate": True,
        "numeric_quality_aggregation": False,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }


def self_test() -> int:
    fp = "sha256:" + "a" * 64
    def packet(surface: str = "pass", reader: str = "pass", continuity: str = "pass", semantic: str = "pass", reader_codes: list[str] | None = None) -> dict[str, Any]:
        return {
            "candidate_fingerprint": fp,
            "policy": {"reader_grip": "very_high", "require_continuity": True, "require_independent_semantic": True},
            "gates": [
                {"category": "surface", "status": surface, "candidate_fingerprint": fp, "codes": [], "evidence_refs": ["surface:a"]},
                {"category": "reader_engagement", "status": reader, "candidate_fingerprint": fp, "codes": reader_codes or [], "evidence_refs": ["reader:a"]},
                {"category": "continuity", "status": continuity, "candidate_fingerprint": fp, "codes": [], "evidence_refs": ["continuity:a"]},
                {"category": "semantic_independent", "status": semantic, "candidate_fingerprint": fp, "codes": [], "evidence_refs": ["semantic:a"]},
            ],
        }
    green = evaluate(packet())
    flat = evaluate(packet(reader="fail", reader_codes=["RG-15"]))
    surface_fail = evaluate(packet(surface="fail"))
    pending = evaluate(packet(semantic="pending"))
    mismatch_guard = False
    bad = packet(); bad["gates"][0]["candidate_fingerprint"] = "sha256:" + "b" * 64
    try:
        evaluate(bad)
    except ValueError:
        mismatch_guard = True
    contradictory_flat_guard = False
    try:
        evaluate(packet(reader="pass", reader_codes=["RG-15"]))
    except ValueError:
        contradictory_flat_guard = True
    ok = all((
        green["ready_for_user_visible_review"] is True,
        flat["ready_for_user_visible_review"] is False and flat["blocking_gates"] == ["reader_engagement"],
        surface_fail["ready_for_user_visible_review"] is False and surface_fail["blocking_gates"] == ["surface"],
        pending["ready_for_user_visible_review"] is False and pending["pending_gates"] == ["semantic_independent"],
        mismatch_guard,
        contradictory_flat_guard,
        green["numeric_quality_aggregation"] is False,
    ))
    print(json.dumps({
        "production_readiness_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "surface_and_reader_are_conjunctive": True,
        "safe_but_flat_blocks": True,
        "candidate_fingerprint_bound": mismatch_guard,
        "pending_gate_blocks": True,
        "numeric_quality_aggregation": False,
        "authority": False,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge production-readiness gate")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    ev = sub.add_parser("evaluate"); ev.add_argument("--input", required=True); ev.add_argument("--output")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    value = evaluate(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
