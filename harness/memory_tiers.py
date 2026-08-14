#!/usr/bin/env python3
"""Tiered derived-memory allocation for NovelForge 7.2.

This module allocates already-derived/project-provided memory under hard budgets.
It does not summarize Canon or infer new story truth. Derived memory remains
non-authoritative and rebuildable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_memory_tiers_v1"
TIERS = ("hot", "working", "archival")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    item_id = raw.get("id") or raw.get("item_id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("memory item id required")
    cost = raw.get("cost")
    if isinstance(cost, bool) or not isinstance(cost, int) or cost <= 0:
        raise ValueError(f"memory cost must be positive integer: {item_id}")
    relevance = raw.get("relevance", 0.0)
    if isinstance(relevance, bool) or not isinstance(relevance, (int, float)) or not 0 <= float(relevance) <= 1:
        raise ValueError(f"relevance must be 0..1: {item_id}")
    priority = raw.get("priority", 0.0)
    if isinstance(priority, bool) or not isinstance(priority, (int, float)):
        raise ValueError(f"priority must be numeric: {item_id}")
    derived = bool(raw.get("derived", True))
    authority = raw.get("authority", False)
    if derived and authority is not False:
        raise ValueError(f"derived memory must have authority=false: {item_id}")
    source_refs = raw.get("source_refs", [])
    source_fingerprints = raw.get("source_fingerprints", [])
    if derived:
        if not isinstance(source_refs, list) or not source_refs or not all(isinstance(x, str) and x.strip() for x in source_refs):
            raise ValueError(f"derived memory requires source_refs: {item_id}")
        if not isinstance(source_fingerprints, list) or not source_fingerprints or not all(isinstance(x, str) and x.startswith("sha256:") for x in source_fingerprints):
            raise ValueError(f"derived memory requires source_fingerprints: {item_id}")
    events = raw.get("event_ids", [])
    participants = raw.get("participant_ids", [])
    if not isinstance(events, list) or not isinstance(participants, list):
        raise ValueError(f"event_ids/participant_ids must be lists: {item_id}")
    return {
        "id": item_id,
        "cost": cost,
        "relevance": float(relevance),
        "priority": float(priority),
        "pinned": bool(raw.get("pinned", False)),
        "derived": derived,
        "authority": False if derived else authority,
        "source_refs": source_refs,
        "source_fingerprints": source_fingerprints,
        "event_ids": [str(x) for x in events],
        "participant_ids": [str(x) for x in participants],
        "invalidated": bool(raw.get("invalidated", False)),
        "payload_ref": raw.get("payload_ref"),
        "metadata": raw.get("metadata", {}),
    }


def classify(item: dict[str, Any], *, current_event_ids: set[str], participant_ids: set[str]) -> tuple[str, tuple[Any, ...]]:
    event_overlap = len(current_event_ids.intersection(item["event_ids"]))
    participant_overlap = len(participant_ids.intersection(item["participant_ids"]))
    if item["pinned"] or event_overlap or participant_overlap:
        tier = "hot"
    elif item["relevance"] >= 0.5 or item["priority"] > 0:
        tier = "working"
    else:
        tier = "archival"
    score = (
        1 if item["pinned"] else 0,
        event_overlap,
        participant_overlap,
        item["relevance"],
        item["priority"],
        -item["cost"],
        item["id"],
    )
    return tier, score


def _pack(items: list[dict[str, Any]], budget: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    used = 0
    for item in items:
        if used + item["cost"] <= budget:
            selected.append(item)
            used += item["cost"]
        else:
            skipped.append({"id": item["id"], "reason": "whole_item_exceeds_remaining_budget", "cost": item["cost"], "remaining": max(0, budget - used)})
    return selected, skipped, used


def allocate(payload: dict[str, Any], *, hot_budget: int, working_budget: int,
             current_event_ids: list[str] | None = None, participant_ids: list[str] | None = None) -> dict[str, Any]:
    if hot_budget < 0 or working_budget < 0:
        raise ValueError("budgets must be >= 0")
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("items must be a list")
    current_events = set(current_event_ids or [])
    participants = set(participant_ids or [])
    buckets: dict[str, list[dict[str, Any]]] = {tier: [] for tier in TIERS}
    invalidated: list[str] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("memory item must be object")
        item = normalize_item(raw)
        if item["invalidated"]:
            invalidated.append(item["id"])
            continue
        tier, score = classify(item, current_event_ids=current_events, participant_ids=participants)
        item["tier"] = tier
        item["selection_score"] = list(score[:-1])
        buckets[tier].append(item)
    for tier in TIERS:
        buckets[tier].sort(key=lambda x: classify(x, current_event_ids=current_events, participant_ids=participants)[1], reverse=True)
    hot_selected, hot_skipped, hot_used = _pack(buckets["hot"], hot_budget)
    working_selected, working_skipped, working_used = _pack(buckets["working"], working_budget)
    return {
        "schema": SCHEMA,
        "current_event_ids": sorted(current_events),
        "participant_ids": sorted(participants),
        "budgets": {"hot": hot_budget, "working": working_budget},
        "used": {"hot": hot_used, "working": working_used},
        "selected": {"hot": hot_selected, "working": working_selected},
        "archival": [item["id"] for item in buckets["archival"]],
        "skipped": {"hot": hot_skipped, "working": working_skipped},
        "invalidated": invalidated,
        "whole_item_or_skip": True,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    payload = {
        "items": [
            {"id": "M-PIN", "cost": 4, "relevance": 0.2, "priority": 0, "pinned": True, "derived": True, "authority": False, "source_refs": ["canon:A"], "source_fingerprints": ["sha256:" + "a" * 64], "event_ids": [], "participant_ids": []},
            {"id": "M-EVT", "cost": 5, "relevance": 0.1, "priority": 0, "derived": True, "authority": False, "source_refs": ["canon:B"], "source_fingerprints": ["sha256:" + "b" * 64], "event_ids": ["EV-9"], "participant_ids": []},
            {"id": "M-WORK", "cost": 3, "relevance": 0.8, "priority": 0, "derived": True, "authority": False, "source_refs": ["canon:C"], "source_fingerprints": ["sha256:" + "c" * 64], "event_ids": [], "participant_ids": []},
            {"id": "M-ARCH", "cost": 2, "relevance": 0.1, "priority": 0, "derived": True, "authority": False, "source_refs": ["canon:D"], "source_fingerprints": ["sha256:" + "d" * 64], "event_ids": [], "participant_ids": []},
        ]
    }
    report = allocate(payload, hot_budget=5, working_budget=3, current_event_ids=["EV-9"])
    hot_ids = [x["id"] for x in report["selected"]["hot"]]
    working_ids = [x["id"] for x in report["selected"]["working"]]
    hard_budget = report["used"]["hot"] <= 5 and report["used"]["working"] <= 3
    pin_first = hot_ids and hot_ids[0] == "M-PIN"
    event_relevance = any(x["id"] == "M-EVT" for x in report["skipped"]["hot"])
    whole_skip = report["whole_item_or_skip"] and report["skipped"]["hot"][0]["reason"] == "whole_item_exceeds_remaining_budget"
    bad_authority = False
    try:
        normalize_item({"id": "BAD", "cost": 1, "derived": True, "authority": True, "source_refs": ["x"], "source_fingerprints": ["sha256:" + "e" * 64]})
    except ValueError:
        bad_authority = True
    ok = hard_budget and pin_first and event_relevance and whole_skip and working_ids == ["M-WORK"] and bad_authority
    dump({
        "memory_tiers_contract": "PASS" if ok else "FAIL",
        "hard_budget": hard_budget,
        "whole_item_or_skip": whole_skip,
        "event_relevance": event_relevance,
        "pin_first": pin_first,
        "derived_authority_false_enforced": bad_authority,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge tiered derived-memory allocator")
    sub = p.add_subparsers(dest="command", required=True)
    al = sub.add_parser("allocate"); al.add_argument("--input", required=True); al.add_argument("--hot-budget", type=int, required=True); al.add_argument("--working-budget", type=int, required=True); al.add_argument("--event-id", action="append", dest="event_ids"); al.add_argument("--participant-id", action="append", dest="participant_ids"); al.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    report = allocate(load_json(Path(args.input)), hot_budget=args.hot_budget, working_budget=args.working_budget, current_event_ids=args.event_ids, participant_ids=args.participant_ids)
    dump(report, Path(args.output) if args.output else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
