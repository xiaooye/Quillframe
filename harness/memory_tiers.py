#!/usr/bin/env python3
"""Deterministic context-budget packer for NovelForge.

The model owns semantic relevance through the `context.select` contract. This
module owns explicit visibility boundaries, authority/pin constraints,
fingerprint binding and hard whole-block budgets. Perspective-incompatible
blocks never enter the semantic packet; task-aware support remains observation,
not story truth or Canon.
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

SCHEMA = "novelforge_memory_tiers_v3"
PERSPECTIVE_SCOPES = {"manager", "reader", "character", "narrator", "research", "other"}
VISIBILITY_SCOPES = {"shared", *PERSPECTIVE_SCOPES}
QUESTION_KINDS = {"concept", "behavior", "state", "continuity", "relationship", "other"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string or null")
    return value.strip()


def normalize_task(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("task")
    if not isinstance(raw, dict):
        raise ValueError("task object required")
    task_mode = raw.get("task_mode")
    task_goal = raw.get("task_goal")
    if not isinstance(task_mode, str) or not task_mode.strip():
        raise ValueError("task.task_mode required")
    if not isinstance(task_goal, str) or not task_goal.strip():
        raise ValueError("task.task_goal required")
    perspective = raw.get("perspective")
    if not isinstance(perspective, dict):
        raise ValueError("task.perspective object required")
    scope = perspective.get("scope")
    if scope not in PERSPECTIVE_SCOPES:
        raise ValueError(f"invalid task perspective scope: {scope!r}")
    perspective_id = _optional_text(perspective.get("perspective_id"), "task.perspective.perspective_id")
    if scope == "character" and not perspective_id:
        raise ValueError("character task perspective requires perspective_id")

    raw_questions = raw.get("active_questions")
    if not isinstance(raw_questions, list):
        raise ValueError("task.active_questions must be list")
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for q in raw_questions:
        if not isinstance(q, dict):
            raise ValueError("active question must be object")
        qid = q.get("question_id")
        text = q.get("question")
        kind = q.get("kind")
        if not isinstance(qid, str) or not qid.strip():
            raise ValueError("active question question_id required")
        qid = qid.strip()
        if qid in seen:
            raise ValueError(f"duplicate active question_id: {qid}")
        seen.add(qid)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"active question {qid} requires question")
        if kind not in QUESTION_KINDS:
            raise ValueError(f"active question {qid} has invalid kind")
        questions.append({
            "question_id": qid,
            "question": text.strip(),
            "kind": kind,
            "as_of_story_point": _optional_text(q.get("as_of_story_point"), f"{qid}.as_of_story_point"),
        })
    return {
        "task_mode": task_mode.strip(),
        "task_goal": task_goal.strip(),
        "current_story_point": _optional_text(raw.get("current_story_point"), "task.current_story_point"),
        "perspective": {"scope": scope, "perspective_id": perspective_id},
        "active_questions": questions,
    }


def normalize_visibility(raw: Any, item_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"memory visibility object required: {item_id}")
    scope = raw.get("scope")
    if scope not in VISIBILITY_SCOPES:
        raise ValueError(f"invalid visibility scope for {item_id}: {scope!r}")
    perspective_id = _optional_text(raw.get("perspective_id"), f"{item_id}.visibility.perspective_id")
    if scope == "character" and not perspective_id:
        raise ValueError(f"character visibility requires perspective_id: {item_id}")
    return {"scope": scope, "perspective_id": perspective_id}


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    item_id = raw.get("id") or raw.get("item_id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("memory item id required")
    item_id = item_id.strip()
    cost = raw.get("cost")
    if isinstance(cost, bool) or not isinstance(cost, int) or cost <= 0:
        raise ValueError(f"memory cost must be positive integer: {item_id}")
    derived = bool(raw.get("derived", True))
    authority = raw.get("authority", False)
    if derived and authority is not False:
        raise ValueError(f"derived memory must have authority=false: {item_id}")
    if not derived and not isinstance(authority, (str, bool)):
        raise ValueError(f"non-derived authority must be string|boolean: {item_id}")
    source_refs = raw.get("source_refs", [])
    source_fingerprints = raw.get("source_fingerprints", [])
    if not isinstance(source_refs, list) or not all(isinstance(x, str) and x.strip() for x in source_refs):
        raise ValueError(f"source_refs must contain strings: {item_id}")
    if derived:
        if not source_refs:
            raise ValueError(f"derived memory requires source_refs: {item_id}")
        if not isinstance(source_fingerprints, list) or not source_fingerprints or not all(isinstance(x, str) and x.startswith("sha256:") for x in source_fingerprints):
            raise ValueError(f"derived memory requires source_fingerprints: {item_id}")
    elif not isinstance(source_fingerprints, list):
        raise ValueError(f"source_fingerprints must be list: {item_id}")
    model_view = raw.get("model_view", {})
    if not isinstance(model_view, dict):
        raise ValueError(f"model_view must be object: {item_id}")
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata must be object: {item_id}")
    return {
        "id": item_id,
        "cost": cost,
        "pinned": bool(raw.get("pinned", False)),
        "derived": derived,
        "authority": False if derived else authority,
        "source_refs": [x.strip() for x in source_refs],
        "source_fingerprints": list(source_fingerprints),
        "story_point": _optional_text(raw.get("story_point"), f"{item_id}.story_point"),
        "visibility": normalize_visibility(raw.get("visibility"), item_id),
        "invalidated": bool(raw.get("invalidated", False)),
        "model_view": model_view,
        "payload_ref": raw.get("payload_ref"),
        "metadata": metadata,
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


def visible_to_task(item: dict[str, Any], task: dict[str, Any]) -> bool:
    visibility = item["visibility"]
    if visibility["scope"] == "shared":
        return True
    perspective = task["perspective"]
    if visibility["scope"] != perspective["scope"]:
        return False
    required_id = visibility.get("perspective_id")
    return required_id is None or required_id == perspective.get("perspective_id")


def partition_visibility(items: list[dict[str, Any]], task: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    visible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for item in items:
        if item["invalidated"]:
            continue
        if visible_to_task(item, task):
            visible.append(item)
        else:
            if item["pinned"]:
                raise ValueError(f"pinned memory violates task perspective boundary: {item['id']}")
            excluded.append(item)
    return visible, excluded


def prepare_selection_job(payload: dict[str, Any], *, subject_id: str,
                          source_session_id: str | None = None) -> dict[str, Any]:
    task = normalize_task(payload)
    items = normalized_items(payload)
    visible, _ = partition_visibility(items, task)
    candidates = [
        {
            "block_id": item["id"],
            "pinned": item["pinned"],
            "authority": item["authority"],
            "derived": item["derived"],
            "source_refs": item["source_refs"],
            "story_point": item["story_point"],
            "visibility": item["visibility"],
            "model_view": item["model_view"],
        }
        for item in visible
    ]
    return make_contract_job(
        "context.select",
        subject_id,
        {"task": task, "memory_blocks": candidates},
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


def _validate_question_support(task: dict[str, Any], judgment: dict[str, Any], visible_ids: set[str], selected_ids: set[str]) -> tuple[list[dict[str, Any]], list[str]]:
    active_ids = [q["question_id"] for q in task["active_questions"]]
    active_set = set(active_ids)
    support = judgment.get("question_support")
    unresolved = judgment.get("unresolved_questions")
    if not isinstance(support, list):
        raise ValueError("selection.question_support must be list")
    unresolved_ids = _ordered_ids(unresolved, "unresolved_questions")
    if len(unresolved_ids) != len(set(unresolved_ids)):
        raise ValueError("selection.unresolved_questions contains duplicates")
    unknown_unresolved = sorted(set(unresolved_ids) - active_set)
    if unknown_unresolved:
        raise ValueError("unresolved_questions references unknown question ids: " + ", ".join(unknown_unresolved))

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in support:
        if not isinstance(row, dict):
            raise ValueError("question_support item must be object")
        qid = row.get("question_id")
        state = row.get("support")
        block_ids = _ordered_ids(row.get("block_ids"), "question_support.block_ids")
        if qid not in active_set:
            raise ValueError(f"question_support references unknown question_id: {qid}")
        if qid in seen:
            raise ValueError(f"duplicate question_support question_id: {qid}")
        seen.add(qid)
        if state not in {"sufficient", "partial", "none"}:
            raise ValueError(f"invalid question support state: {qid}")
        if len(block_ids) != len(set(block_ids)):
            raise ValueError(f"duplicate support block ids: {qid}")
        unknown_blocks = sorted(set(block_ids) - visible_ids)
        if unknown_blocks:
            raise ValueError(f"question {qid} references invisible/unknown blocks: " + ", ".join(unknown_blocks))
        unselected_blocks = sorted(set(block_ids) - selected_ids)
        if unselected_blocks:
            raise ValueError(f"question {qid} support blocks must be hot|working selections: " + ", ".join(unselected_blocks))
        if state == "none" and block_ids:
            raise ValueError(f"question {qid} support=none requires empty block_ids")
        if state in {"sufficient", "partial"} and not block_ids:
            raise ValueError(f"question {qid} support={state} requires block_ids")
        normalized.append({"question_id": qid, "support": state, "block_ids": block_ids})
    if seen != active_set:
        missing = sorted(active_set - seen)
        raise ValueError("question_support must cover every active question: " + ", ".join(missing))
    expected_unresolved = {row["question_id"] for row in normalized if row["support"] != "sufficient"}
    if set(unresolved_ids) != expected_unresolved:
        raise ValueError("unresolved_questions must exactly match partial|none question_support states")
    return normalized, unresolved_ids


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

    task = normalize_task(payload)
    items = normalized_items(payload)
    visible, excluded = partition_visibility(items, task)
    by_id = {item["id"]: item for item in visible}
    judgment = result.get("judgment", {})
    hot_ids = _ordered_ids(judgment.get("hot_ids"), "hot_ids")
    working_ids = _ordered_ids(judgment.get("working_ids"), "working_ids")
    archive_ids = _ordered_ids(judgment.get("archive_ids"), "archive_ids")
    proposed = hot_ids + working_ids + archive_ids
    unknown = sorted(set(proposed) - set(by_id))
    if unknown:
        raise ValueError("selection references unknown/invisible memory ids: " + ", ".join(unknown))
    if len(proposed) != len(set(proposed)):
        raise ValueError("selection contains duplicate memory ids across tiers")
    if set(proposed) != set(by_id):
        missing = sorted(set(by_id) - set(proposed))
        raise ValueError("selection must classify every visible memory block: " + ", ".join(missing))

    semantic_loaded_ids = set(hot_ids + working_ids)
    question_support, unresolved_questions = _validate_question_support(task, judgment, set(by_id), semantic_loaded_ids)

    pinned_ids = [item["id"] for item in visible if item["pinned"]]
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
    archive = [item["id"] for item in visible if item["id"] not in loaded_ids]
    invalidated = [item["id"] for item in items if item["invalidated"]]

    grounding: list[dict[str, Any]] = []
    budget_incomplete: list[str] = []
    for row in question_support:
        support_ids = row["block_ids"]
        loaded_support = [item_id for item_id in support_ids if item_id in loaded_ids]
        dropped_support = [item_id for item_id in support_ids if item_id not in loaded_ids]
        if not support_ids:
            loading_status = "no_support_identified"
        elif not dropped_support:
            loading_status = "all_loaded"
        elif loaded_support:
            loading_status = "partially_loaded"
        else:
            loading_status = "not_loaded"
        if dropped_support:
            budget_incomplete.append(row["question_id"])
        grounding.append({
            "question_id": row["question_id"],
            "model_support": row["support"],
            "support_block_ids": support_ids,
            "loaded_support_block_ids": loaded_support,
            "dropped_support_block_ids": dropped_support,
            "loading_status": loading_status,
        })

    return {
        "schema": SCHEMA,
        "selection_fingerprint": result.get("input_fingerprint"),
        "task": task,
        "budgets": {"hot": hot_budget, "working": working_budget},
        "used": {"hot": hot_used, "working": working_used},
        "selected": {"hot": hot_selected, "working": working_selected},
        "archive": archive,
        "visibility_excluded": [item["id"] for item in excluded],
        "skipped": {"hot": hot_skipped, "working": working_skipped},
        "invalidated": invalidated,
        "question_grounding": grounding,
        "model_unresolved_questions": unresolved_questions,
        "grounding_incomplete_due_budget": sorted(set(budget_incomplete)),
        "selection_owner": "model",
        "visibility_owner": "deterministic_runtime",
        "budget_owner": "deterministic_runtime",
        "pin_override": True,
        "whole_item_or_skip": True,
        "authority": False,
        "model_execution": False,
    }


def self_test() -> int:
    payload = {
        "task": {
            "task_mode": "DRAFT",
            "task_goal": "Resolve the negotiation from CHAR-A's current knowledge without leaking CHAR-B's private facts.",
            "current_story_point": "SCN-9",
            "perspective": {"scope": "character", "perspective_id": "CHAR-A"},
            "active_questions": [
                {"question_id": "Q-REL", "question": "What does CHAR-A currently believe about the relationship?", "kind": "relationship", "as_of_story_point": "SCN-9"},
                {"question_id": "Q-CLUE", "question": "Which old clue might affect the immediate tactic?", "kind": "continuity", "as_of_story_point": "SCN-9"},
            ],
        },
        "items": [
            {"id": "M-PIN", "cost": 2, "pinned": True, "derived": True, "authority": False, "source_refs": ["accepted:A"], "source_fingerprints": ["sha256:" + "a" * 64], "story_point": "SCN-9", "visibility": {"scope": "shared"}, "model_view": {"label": "current-goal", "description": "Immediate scene goal", "value": "Get out alive."}},
            {"id": "M-B", "cost": 3, "derived": True, "authority": False, "source_refs": ["accepted:B"], "source_fingerprints": ["sha256:" + "b" * 64], "story_point": "SCN-8", "visibility": {"scope": "character", "perspective_id": "CHAR-A"}, "model_view": {"label": "relationship", "description": "CHAR-A's relationship state", "value": "Trust is damaged."}},
            {"id": "M-C", "cost": 4, "derived": True, "authority": False, "source_refs": ["accepted:C"], "source_fingerprints": ["sha256:" + "c" * 64], "story_point": "SCN-3", "visibility": {"scope": "character", "perspective_id": "CHAR-A"}, "model_view": {"label": "old-clue", "description": "A clue CHAR-A observed earlier", "value": "The seal was replaced."}},
            {"id": "M-HIDDEN", "cost": 1, "derived": True, "authority": False, "source_refs": ["accepted:H"], "source_fingerprints": ["sha256:" + "d" * 64], "story_point": "SCN-8", "visibility": {"scope": "character", "perspective_id": "CHAR-B"}, "model_view": {"label": "private", "value": "CHAR-B's private motive."}},
            {"id": "M-X", "cost": 1, "derived": True, "authority": False, "source_refs": ["accepted:X"], "source_fingerprints": ["sha256:" + "e" * 64], "invalidated": True, "visibility": {"scope": "shared"}, "model_view": {"label": "invalid", "value": "stale"}},
        ],
    }
    job = prepare_selection_job(payload, subject_id="SCN-9")
    packet_ids = [x["block_id"] for x in job["input"]["payload"]["memory_blocks"]]
    hidden_never_in_packet = "M-HIDDEN" not in packet_ids and "M-X" not in packet_ids
    result = {
        "job_id": job["job_id"], "subject_id": job["subject_id"], "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"], "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "fixture"},
        "judgment": {
            "confidence": 0.9,
            "hot_ids": ["M-B"],
            "working_ids": ["M-C"],
            "archive_ids": ["M-PIN"],
            "reasons": [
                {"block_id": "M-B", "tier": "hot", "reason": "Directly answers Q-REL."},
                {"block_id": "M-C", "tier": "working", "reason": "Potential tactic evidence for Q-CLUE."},
                {"block_id": "M-PIN", "tier": "archive", "reason": "Runtime pin will still force it hot."},
            ],
            "question_support": [
                {"question_id": "Q-REL", "support": "sufficient", "block_ids": ["M-B"]},
                {"question_id": "Q-CLUE", "support": "partial", "block_ids": ["M-C"]},
            ],
            "unresolved_questions": ["Q-CLUE"],
        },
        "proposals": [], "errors": [],
    }
    report = pack_selection(payload, job, result, hot_budget=5, working_budget=3)
    hot_ids = [x["id"] for x in report["selected"]["hot"]]
    pin_override = hot_ids == ["M-PIN", "M-B"]
    hard_budget = report["used"] == {"hot": 5, "working": 0}
    whole_skip = report["skipped"]["working"] and report["skipped"]["working"][0]["id"] == "M-C"
    visibility_excluded = report["visibility_excluded"] == ["M-HIDDEN"]
    invalidated_excluded = "M-X" in report["invalidated"] and "M-X" not in report["archive"]
    grounding_budget_truthful = report["grounding_incomplete_due_budget"] == ["Q-CLUE"] and report["question_grounding"][1]["loading_status"] == "not_loaded"

    unknown_guard = False
    bad = json.loads(json.dumps(result)); bad["judgment"]["hot_ids"] = ["UNKNOWN"]
    try:
        pack_selection(payload, job, bad, hot_budget=5, working_budget=3)
    except ValueError:
        unknown_guard = True
    question_guard = False
    bad_q = json.loads(json.dumps(result)); bad_q["judgment"]["question_support"][0]["question_id"] = "Q-UNKNOWN"
    try:
        pack_selection(payload, job, bad_q, hot_budget=5, working_budget=3)
    except ValueError:
        question_guard = True
    authority_guard = False
    try:
        normalize_item({"id": "BAD", "cost": 1, "derived": True, "authority": True, "source_refs": ["x"], "source_fingerprints": ["sha256:" + "f" * 64], "visibility": {"scope": "shared"}})
    except ValueError:
        authority_guard = True
    pin_visibility_guard = False
    conflict = json.loads(json.dumps(payload))
    conflict["items"].append({"id": "M-BAD-PIN", "cost": 1, "pinned": True, "derived": True, "authority": False, "source_refs": ["accepted:Z"], "source_fingerprints": ["sha256:" + "1" * 64], "visibility": {"scope": "character", "perspective_id": "CHAR-B"}, "model_view": {"label": "private"}})
    try:
        prepare_selection_job(conflict, subject_id="SCN-9")
    except ValueError:
        pin_visibility_guard = True
    catalog_resolved = job.get("provenance", {}).get("pack_id") == "context-research"
    typed_input = job.get("provenance", {}).get("input_contract_validated") is True
    ok = all((catalog_resolved, typed_input, hidden_never_in_packet, pin_override, hard_budget, whole_skip,
              visibility_excluded, invalidated_excluded, grounding_budget_truthful, unknown_guard,
              question_guard, authority_guard, pin_visibility_guard))
    dump({
        "memory_tiers_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "semantic_relevance_owner": "model",
        "task_aware_questions": True,
        "catalog_resolved_contract_pack": catalog_resolved,
        "typed_input_contract": typed_input,
        "perspective_incompatible_never_enters_semantic_packet": hidden_never_in_packet,
        "pin_visibility_conflict_fail_closed": pin_visibility_guard,
        "pin_override": pin_override,
        "hard_budget": hard_budget,
        "whole_item_or_skip": bool(whole_skip),
        "visibility_excluded": visibility_excluded,
        "invalidated_excluded": invalidated_excluded,
        "grounding_reports_budget_drop": grounding_budget_truthful,
        "unknown_selection_guard": unknown_guard,
        "question_identity_guard": question_guard,
        "derived_authority_false_enforced": authority_guard,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge perspective-safe model-selected context packer")
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
