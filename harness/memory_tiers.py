#!/usr/bin/env python3
"""Deterministic context-budget packer for NovelForge.

The model owns semantic relevance through the `context.select` contract. This
module never scores literary/story relevance. It only validates bounded memory
blocks, enforces authority/pin constraints, binds a semantic result to its exact
job fingerprint, and packs whole blocks under hard budgets.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))
from semantic_worker_router import make_contract_job, validate_result  # noqa: E402

SCHEMA = "novelforge_memory_tiers_v2"


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
    model_view = raw.get("model_view", {})
    if not isinstance(model_view, dict):
        raise ValueError(f"model_view must be object: {item_id}")
    return {
        "id": item_id.strip(),
        "cost": cost,
        "pinned": bool(raw.get("pinned", False)),
        "derived": derived,
        "authority": False if derived else authority,
        "source_refs": list(source_refs),
        "source_fingerprints": list(source_fingerprints),
        "invalidated": bool(raw.get("invalidated", False)),
        "model_view": model_view,
        "payload_ref": raw.get("payload_ref"),
        "metadata": raw.get("metadata", {}),
    }


def normalized_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("items must be a list")
    items = []
    seen: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("memory item must be object")
        item = normalize_item(raw)
        if item["id"] in seen:
            raise ValueError(f"duplicate memory id: {item['id']}")
        seen.add(item["id"])
        items.append(item)
    return items


def prepare_selection_job(payload: dict[str, Any], *, subject_id: str,
                          source_session_id: str | None = None) -> dict[str, Any]:
    task_context = payload.get("task_context", {})
    if not isinstance(task_context, dict):
        raise ValueError("task_context must be object")
    items = [item for item in normalized_items(payload) if not item["invalidated"]]
    candidates = [
        {
            "id": item["id"],
            "cost": item["cost"],
            "pinned": item["pinned"],
            "authority": item["authority"],
            "derived": item["derived"],
            "model_view": item["model_view"],
        }
        for item in items
    ]
    return make_contract_job(
        "context.select",
        subject_id,
        {"task_context": task_context, "memory_blocks": candidates},
        source_session_id=source_session_id,
    )


def _ordered_ids(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
        raise ValueError(f"selection.{name} must be string list")
    return [x.strip() for x in value]


def _pack(items: list[dict[str, Any]], budget: int, *, fail_if_over: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    used = 0
    for item in items:
        if used + item["cost"] <= budget:
            selected.append(item)
            used += item["cost"]
        elif fail_if_over:
            raise ValueError("pinned memory blocks exceed hot budget")
        else:
            skipped.append({
                "id": item["id"],
                "reason": "whole_item_exceeds_remaining_budget",
                "cost": item["cost"],
                "remaining": max(0, budget - used),
            })
    return selected, skipped, used


def pack_selection(payload: dict[str, Any], job: dict[str, Any], result: dict[str, Any], *,
                   hot_budget: int, working_budget: int) -> dict[str, Any]:
    if hot_budget < 0 or working_budget < 0:
        raise ValueError("budgets must be >= 0")
    errors = validate_result(job, result)
    if errors:
        raise ValueError("semantic selection result invalid: " + "; ".join(errors))
    if job.get("input", {}).get("model_contract_id") != "context.select":
        raise ValueError("job must use context.select contract")
    if result.get("status") != "completed":
        raise ValueError("context selection must be completed")

    items = normalized_items(payload)
    valid = [item for item in items if not item["invalidated"]]
    by_id = {item["id"]: item for item in valid}
    judgment = result.get("judgment", {})
    hot_ids = _ordered_ids(judgment.get("hot_ids"), "hot_ids")
    working_ids = _ordered_ids(judgment.get("working_ids"), "working_ids")
    archive_ids = _ordered_ids(judgment.get("archive_ids"), "archive_ids")
    proposed = hot_ids + working_ids + archive_ids
    unknown = sorted(set(proposed) - set(by_id))
    if unknown:
        raise ValueError("selection references unknown/invalidated memory ids: " + ", ".join(unknown))
    if len(proposed) != len(set(proposed)):
        raise ValueError("selection contains duplicate memory ids across tiers")

    pinned_ids = [item["id"] for item in valid if item["pinned"]]
    ordered_hot_ids = pinned_ids + [item_id for item_id in hot_ids if item_id not in set(pinned_ids)]
    hot_set = set(ordered_hot_ids)
    ordered_working_ids = [item_id for item_id in working_ids if item_id not in hot_set]

    pinned_items = [by_id[item_id] for item_id in pinned_ids]
    _, _, pinned_used = _pack(pinned_items, hot_budget, fail_if_over=True)
    nonpinned_hot = [by_id[item_id] for item_id in ordered_hot_ids if item_id not in set(pinned_ids)]
    hot_extra, hot_skipped, hot_extra_used = _pack(nonpinned_hot, hot_budget - pinned_used)
    hot_selected = pinned_items + hot_extra
    hot_used = pinned_used + hot_extra_used

    working_candidates = [by_id[item_id] for item_id in ordered_working_ids]
    working_selected, working_skipped, working_used = _pack(working_candidates, working_budget)
    loaded_ids = {item["id"] for item in hot_selected + working_selected}
    archive = [item["id"] for item in valid if item["id"] not in loaded_ids]
    invalidated = [item["id"] for item in items if item["invalidated"]]

    return {
        "schema": SCHEMA,
        "selection_fingerprint": result.get("input_fingerprint"),
        "budgets": {"hot": hot_budget, "working": working_budget},
        "used": {"hot": hot_used, "working": working_used},
        "selected": {"hot": hot_selected, "working": working_selected},
        "archive": archive,
        "skipped": {"hot": hot_skipped, "working": working_skipped},
        "invalidated": invalidated,
        "selection_owner": "model",
        "budget_owner": "deterministic_runtime",
        "pin_override": True,
        "whole_item_or_skip": True,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    payload = {
        "task_context": {"mode": "DRAFT", "scene": "SCN-9"},
        "items": [
            {"id": "M-PIN", "cost": 2, "pinned": True, "derived": True, "authority": False, "source_refs": ["canon:A"], "source_fingerprints": ["sha256:" + "a" * 64], "model_view": {"label": "current-goal", "description": "Immediate scene goal", "value": "Get out alive."}},
            {"id": "M-B", "cost": 3, "derived": True, "authority": False, "source_refs": ["canon:B"], "source_fingerprints": ["sha256:" + "b" * 64], "model_view": {"label": "relationship", "description": "Relevant relationship state", "value": "Trust is damaged."}},
            {"id": "M-C", "cost": 4, "derived": True, "authority": False, "source_refs": ["canon:C"], "source_fingerprints": ["sha256:" + "c" * 64], "model_view": {"label": "old-thread", "description": "Potentially irrelevant thread", "value": "Old clue."}},
            {"id": "M-X", "cost": 1, "derived": True, "authority": False, "source_refs": ["canon:X"], "source_fingerprints": ["sha256:" + "d" * 64], "invalidated": True, "model_view": {"label": "invalid", "value": "stale"}},
        ],
    }
    job = prepare_selection_job(payload, subject_id="SCN-9")
    result = {
        "job_id": job["job_id"], "subject_id": job["subject_id"], "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"], "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "fixture"},
        "judgment": {"confidence": 0.9, "hot_ids": ["M-B"], "working_ids": ["M-C"], "archive_ids": ["M-PIN"], "reasons": []},
        "proposals": [], "errors": [],
    }
    report = pack_selection(payload, job, result, hot_budget=5, working_budget=3)
    hot_ids = [x["id"] for x in report["selected"]["hot"]]
    pin_override = hot_ids == ["M-PIN", "M-B"]
    hard_budget = report["used"] == {"hot": 5, "working": 0}
    whole_skip = report["skipped"]["working"] and report["skipped"]["working"][0]["id"] == "M-C"
    invalidated_excluded = "M-X" in report["invalidated"] and "M-X" not in report["archive"]
    unknown_guard = False
    bad = json.loads(json.dumps(result)); bad["judgment"]["hot_ids"] = ["UNKNOWN"]
    try:
        pack_selection(payload, job, bad, hot_budget=5, working_budget=3)
    except ValueError:
        unknown_guard = True
    authority_guard = False
    try:
        normalize_item({"id": "BAD", "cost": 1, "derived": True, "authority": True, "source_refs": ["x"], "source_fingerprints": ["sha256:" + "e" * 64]})
    except ValueError:
        authority_guard = True
    catalog_resolved = job.get("provenance", {}).get("pack_id") == "context-research"
    ok = pin_override and hard_budget and whole_skip and invalidated_excluded and unknown_guard and authority_guard and catalog_resolved
    dump({
        "memory_tiers_contract": "PASS" if ok else "FAIL",
        "semantic_relevance_owner": "model",
        "catalog_resolved_contract_pack": catalog_resolved,
        "pin_override": pin_override,
        "hard_budget": hard_budget,
        "whole_item_or_skip": bool(whole_skip),
        "invalidated_excluded": invalidated_excluded,
        "unknown_selection_guard": unknown_guard,
        "derived_authority_false_enforced": authority_guard,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge model-selected deterministic context packer")
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--input", required=True); prep.add_argument("--subject-id", required=True); prep.add_argument("--source-session-id"); prep.add_argument("--output")
    pack = sub.add_parser("pack")
    pack.add_argument("--input", required=True); pack.add_argument("--job", required=True); pack.add_argument("--result", required=True); pack.add_argument("--hot-budget", type=int, required=True); pack.add_argument("--working-budget", type=int, required=True); pack.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "prepare":
        value = prepare_selection_job(load_json(Path(args.input)), subject_id=args.subject_id, source_session_id=args.source_session_id)
    else:
        value = pack_selection(load_json(Path(args.input)), load_json(Path(args.job)), load_json(Path(args.result)), hot_budget=args.hot_budget, working_budget=args.working_budget)
    dump(value, Path(args.output) if args.output else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
