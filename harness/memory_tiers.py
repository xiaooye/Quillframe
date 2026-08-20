#!/usr/bin/env python3
"""Deterministic context-budget packer for Quillframe.

The model owns semantic relevance and sufficiency through the `context.select`
contract. This module owns only mechanical execution truth: visibility,
story-time eligibility, pin constraints, authorized search capabilities,
fingerprint-bound semantic-result validation, and hard whole-block budgets.

A model-selected block that cannot fit a hard budget is reported as budget
loss, never silently reclassified as semantically irrelevant. Likewise, an
unselected eligible block is only model-rejected for the current bounded task;
that decision does not alter Canon, authority, or durable memory state.
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

# v4 is the only declared pack envelope and includes explicit
# semantic-selection ownership and provenance fields.
SCHEMA = "quillframe_memory_tiers_v4"
PERSPECTIVE_SCOPES = {"manager", "reader", "character", "narrator", "research", "other"}
VISIBILITY_SCOPES = {"shared", *PERSPECTIVE_SCOPES}
QUESTION_KINDS = {"concept", "behavior", "state", "continuity", "relationship", "other"}
SEARCH_CAPABILITIES = {"project_search", "web_search", "github_search", "user_files", "file_library", "mcp_client"}


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


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be non-negative integer")
    return value


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

    current_story_order = _nonnegative_int(raw.get("current_story_order"), "task.current_story_order")
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
        as_of_story_order = _nonnegative_int(
            q.get("as_of_story_order", current_story_order),
            f"{qid}.as_of_story_order",
        )
        if as_of_story_order > current_story_order:
            raise ValueError(f"active question {qid} cannot be later than task.current_story_order")
        questions.append({
            "question_id": qid,
            "question": text.strip(),
            "kind": kind,
            "as_of_story_point": _optional_text(q.get("as_of_story_point"), f"{qid}.as_of_story_point"),
            "as_of_story_order": as_of_story_order,
        })

    return {
        "task_mode": task_mode.strip(),
        "task_goal": task_goal.strip(),
        "current_story_point": _optional_text(raw.get("current_story_point"), "task.current_story_point"),
        "current_story_order": current_story_order,
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
        if (
            not isinstance(source_fingerprints, list)
            or not source_fingerprints
            or not all(isinstance(x, str) and x.startswith("sha256:") for x in source_fingerprints)
        ):
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
        "available_from_story_order": _nonnegative_int(raw.get("available_from_story_order"), f"{item_id}.available_from_story_order"),
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
    items: list[dict[str, Any]] = []
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


def partition_eligibility(
    items: list[dict[str, Any]],
    task: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    visible: list[dict[str, Any]] = []
    perspective_excluded: list[dict[str, Any]] = []
    temporal_excluded: list[dict[str, Any]] = []
    current_order = task["current_story_order"]
    for item in items:
        if item["invalidated"]:
            continue
        if item["available_from_story_order"] > current_order:
            if item["pinned"]:
                raise ValueError(f"pinned memory violates task story-order boundary: {item['id']}")
            temporal_excluded.append(item)
            continue
        if not visible_to_task(item, task):
            if item["pinned"]:
                raise ValueError(f"pinned memory violates task perspective boundary: {item['id']}")
            perspective_excluded.append(item)
            continue
        visible.append(item)
    return visible, perspective_excluded, temporal_excluded


def _normalize_context_controls(payload: dict[str, Any]) -> dict[str, Any]:
    controls: dict[str, Any] = {}
    if "allowed_search_capabilities" in payload:
        caps = payload["allowed_search_capabilities"]
        if not isinstance(caps, list) or not all(isinstance(x, str) and x in SEARCH_CAPABILITIES for x in caps):
            raise ValueError("allowed_search_capabilities contains invalid capability")
        if len(caps) != len(set(caps)):
            raise ValueError("allowed_search_capabilities contains duplicates")
        controls["allowed_search_capabilities"] = list(caps)
    if "search_history" in payload:
        history = payload["search_history"]
        if not isinstance(history, list) or not all(isinstance(x, dict) for x in history):
            raise ValueError("search_history must be object list")
        controls["search_history"] = history
    if "resource_budget" in payload:
        budget = payload["resource_budget"]
        if not isinstance(budget, dict):
            raise ValueError("resource_budget must be object")
        controls["resource_budget"] = budget
    return controls


def prepare_selection_job(
    payload: dict[str, Any],
    *,
    subject_id: str,
    source_session_id: str | None = None,
) -> dict[str, Any]:
    task = normalize_task(payload)
    items = normalized_items(payload)
    visible, _, _ = partition_eligibility(items, task)
    candidates = [
        {
            "block_id": item["id"],
            "pinned": item["pinned"],
            "authority": item["authority"],
            "derived": item["derived"],
            "source_refs": item["source_refs"],
            "story_point": item["story_point"],
            "available_from_story_order": item["available_from_story_order"],
            "visibility": item["visibility"],
            "model_view": item["model_view"],
        }
        for item in visible
    ]
    semantic_payload = {"task": task, "memory_blocks": candidates}
    semantic_payload.update(_normalize_context_controls(payload))
    return make_contract_job(
        "context.select",
        subject_id,
        semantic_payload,
        source_session_id=source_session_id,
    )


def _ordered_ids(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
        raise ValueError(f"selection.{name} must be string list")
    return [x.strip() for x in value]


def _validate_semantic_selection(
    task: dict[str, Any],
    judgment: dict[str, Any],
    visible_by_id: dict[str, dict[str, Any]],
    allowed_search_capabilities: set[str],
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    selected_ids = _ordered_ids(judgment.get("selected_ids"), "selected_ids")
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selection.selected_ids contains duplicates")
    unknown = sorted(set(selected_ids) - set(visible_by_id))
    if unknown:
        raise ValueError("selection references unknown/invisible memory ids: " + ", ".join(unknown))

    pinned_ids = {item_id for item_id, item in visible_by_id.items() if item["pinned"]}
    missing_pins = sorted(pinned_ids - set(selected_ids))
    if missing_pins:
        raise ValueError("context.select omitted runtime-pinned memory ids: " + ", ".join(missing_pins))

    active_question_ids = {q["question_id"] for q in task["active_questions"]}
    unresolved = _ordered_ids(judgment.get("unresolved_questions"), "unresolved_questions")
    if len(unresolved) != len(set(unresolved)):
        raise ValueError("selection.unresolved_questions contains duplicates")
    unknown_questions = sorted(set(unresolved) - active_question_ids)
    if unknown_questions:
        raise ValueError("unresolved_questions references unknown question ids: " + ", ".join(unknown_questions))

    decision = judgment.get("decision")
    search_requests = judgment.get("search_requests")
    if not isinstance(search_requests, list):
        raise ValueError("selection.search_requests must be list")
    if decision == "enough" and search_requests:
        raise ValueError("decision=enough requires no search_requests")
    if decision == "search_more" and not search_requests:
        raise ValueError("decision=search_more requires at least one search_request")
    for request in search_requests:
        capability = request.get("capability") if isinstance(request, dict) else None
        if capability not in allowed_search_capabilities:
            raise ValueError(f"semantic search request uses unavailable capability: {capability}")
    return selected_ids, unresolved, search_requests


def _budget_pack(
    selected_ids: list[str],
    visible_by_id: dict[str, dict[str, Any]],
    *,
    hot_budget: int,
    working_budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int, int]:
    pinned = [visible_by_id[item_id] for item_id in selected_ids if visible_by_id[item_id]["pinned"]]
    hot: list[dict[str, Any]] = []
    working: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    hot_used = 0
    working_used = 0

    for item in pinned:
        if hot_used + item["cost"] > hot_budget:
            raise ValueError("pinned memory blocks exceed hot budget")
        hot.append(item)
        hot_used += item["cost"]

    pinned_ids = {item["id"] for item in pinned}
    for item_id in selected_ids:
        if item_id in pinned_ids:
            continue
        item = visible_by_id[item_id]
        if hot_used + item["cost"] <= hot_budget:
            hot.append(item)
            hot_used += item["cost"]
        else:
            deferred.append({
                "id": item_id,
                "reason": "deferred_to_working_tier",
                "cost": item["cost"],
                "remaining": max(0, hot_budget - hot_used),
            })
            if working_used + item["cost"] <= working_budget:
                working.append(item)
                working_used += item["cost"]
            else:
                dropped.append({
                    "id": item_id,
                    "reason": "whole_item_exceeds_remaining_budget",
                    "cost": item["cost"],
                    "remaining": max(0, working_budget - working_used),
                })
    return hot, working, deferred, dropped, hot_used, working_used


def pack_selection(
    payload: dict[str, Any],
    job: dict[str, Any],
    result: dict[str, Any],
    *,
    hot_budget: int,
    working_budget: int,
) -> dict[str, Any]:
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
    visible, perspective_excluded, temporal_excluded = partition_eligibility(items, task)
    visible_by_id = {item["id"]: item for item in visible}
    judgment = result.get("judgment", {})
    allowed_caps = set(_normalize_context_controls(payload).get("allowed_search_capabilities", []))
    selected_ids, unresolved_questions, search_requests = _validate_semantic_selection(
        task,
        judgment,
        visible_by_id,
        allowed_caps,
    )

    hot, working, hot_deferred, working_dropped, hot_used, working_used = _budget_pack(
        selected_ids,
        visible_by_id,
        hot_budget=hot_budget,
        working_budget=working_budget,
    )
    loaded_ids = {item["id"] for item in hot + working}
    model_selected = set(selected_ids)
    archive = [item["id"] for item in visible if item["id"] not in loaded_ids]
    model_rejected = [item["id"] for item in visible if item["id"] not in model_selected]
    budget_dropped = [row["id"] for row in working_dropped]
    invalidated = [item["id"] for item in items if item["invalidated"]]
    decision = judgment["decision"]
    incomplete = bool(unresolved_questions or budget_dropped or decision == "search_more")

    return {
        "schema": SCHEMA,
        "selection_fingerprint": result.get("input_fingerprint"),
        "task": task,
        "budgets": {"hot": hot_budget, "working": working_budget},
        "used": {"hot": hot_used, "working": working_used},
        "selected": {"hot": hot, "working": working},
        "archive": archive,
        "visibility_excluded": [item["id"] for item in perspective_excluded],
        "temporal_excluded": [item["id"] for item in temporal_excluded],
        "skipped": {"hot": hot_deferred, "working": working_dropped},
        "invalidated": invalidated,
        "model_selected_ids": selected_ids,
        "model_rejected_ids": model_rejected,
        "budget_dropped_selected_ids": budget_dropped,
        "semantic_sufficiency_decision": decision,
        "semantic_report": judgment["report"],
        "search_requests": search_requests,
        "model_unresolved_questions": unresolved_questions,
        "selection_incomplete_due_budget": bool(budget_dropped),
        "grounding_incomplete_due_budget": [],
        "grounding_incomplete_questions": unresolved_questions,
        "grounding_incomplete": incomplete,
        "question_grounding": [],
        "selection_owner": "model",
        "sufficiency_owner": "model",
        "search_intent_owner": "model",
        "visibility_owner": "deterministic_runtime",
        "budget_owner": "deterministic_runtime",
        "pin_owner": "deterministic_runtime",
        "search_authorization_owner": "deterministic_runtime",
        "whole_item_or_skip": True,
        "authority": False,
        "model_execution": False,
    }


def _fixture_result(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "fixture"},
        "judgment": {
            "confidence": 0.9,
            "decision": "enough",
            "selected_ids": ["M-PIN", "M-B", "M-C"],
            "report": "The pinned current goal and two character-visible facts are useful; no additional search is needed for this fixture.",
            "search_requests": [],
            "unresolved_questions": ["Q-CLUE"],
        },
        "proposals": [],
        "errors": [],
    }


def self_test() -> int:
    payload = {
        "task": {
            "task_mode": "DRAFT",
            "task_goal": "Resolve the negotiation from CHAR-A's current knowledge without leaking CHAR-B's private facts.",
            "current_story_point": "SCN-9",
            "current_story_order": 9,
            "perspective": {"scope": "character", "perspective_id": "CHAR-A"},
            "active_questions": [
                {"question_id": "Q-REL", "question": "What does CHAR-A currently believe about the relationship?", "kind": "relationship", "as_of_story_point": "SCN-9", "as_of_story_order": 9},
                {"question_id": "Q-CLUE", "question": "Which old clue might affect the immediate tactic?", "kind": "continuity", "as_of_story_point": "SCN-3", "as_of_story_order": 3},
            ],
        },
        "allowed_search_capabilities": ["project_search"],
        "items": [
            {"id": "M-PIN", "cost": 2, "pinned": True, "derived": True, "authority": False, "source_refs": ["accepted:A"], "source_fingerprints": ["sha256:" + "a" * 64], "story_point": "SCN-9", "available_from_story_order": 9, "visibility": {"scope": "shared"}, "model_view": {"label": "current-goal", "description": "Immediate scene goal", "value": "Get out alive."}},
            {"id": "M-B", "cost": 3, "derived": True, "authority": False, "source_refs": ["accepted:B"], "source_fingerprints": ["sha256:" + "b" * 64], "story_point": "SCN-8", "available_from_story_order": 8, "visibility": {"scope": "character", "perspective_id": "CHAR-A"}, "model_view": {"label": "relationship", "description": "CHAR-A's relationship state", "value": "Trust is damaged."}},
            {"id": "M-C", "cost": 4, "derived": True, "authority": False, "source_refs": ["accepted:C"], "source_fingerprints": ["sha256:" + "c" * 64], "story_point": "SCN-3", "available_from_story_order": 3, "visibility": {"scope": "character", "perspective_id": "CHAR-A"}, "model_view": {"label": "old-clue", "description": "A clue CHAR-A observed earlier", "value": "The seal was replaced."}},
            {"id": "M-HIDDEN", "cost": 1, "derived": True, "authority": False, "source_refs": ["accepted:H"], "source_fingerprints": ["sha256:" + "d" * 64], "story_point": "SCN-8", "available_from_story_order": 8, "visibility": {"scope": "character", "perspective_id": "CHAR-B"}, "model_view": {"label": "private", "value": "CHAR-B's private motive."}},
            {"id": "M-LATE", "cost": 1, "derived": True, "authority": False, "source_refs": ["accepted:L"], "source_fingerprints": ["sha256:" + "e" * 64], "story_point": "SCN-8", "available_from_story_order": 8, "visibility": {"scope": "character", "perspective_id": "CHAR-A"}, "model_view": {"label": "late-clue", "value": "Visible now but not selected by the model."}},
            {"id": "M-FUTURE", "cost": 1, "derived": True, "authority": False, "source_refs": ["accepted:F"], "source_fingerprints": ["sha256:" + "f" * 64], "story_point": "SCN-10", "available_from_story_order": 10, "visibility": {"scope": "shared"}, "model_view": {"label": "future", "value": "Must never enter the current packet."}},
            {"id": "M-X", "cost": 1, "derived": True, "authority": False, "source_refs": ["accepted:X"], "source_fingerprints": ["sha256:" + "0" * 64], "available_from_story_order": 0, "invalidated": True, "visibility": {"scope": "shared"}, "model_view": {"label": "invalid", "value": "stale"}},
        ],
    }
    job = prepare_selection_job(payload, subject_id="SCN-9")
    packet_ids = [x["block_id"] for x in job["input"]["payload"]["memory_blocks"]]
    hidden_never_in_packet = all(x not in packet_ids for x in ("M-HIDDEN", "M-FUTURE", "M-X"))
    result = _fixture_result(job)
    report = pack_selection(payload, job, result, hot_budget=5, working_budget=3)

    hot_ids = [x["id"] for x in report["selected"]["hot"]]
    pin_and_order = hot_ids == ["M-PIN", "M-B"]
    hard_budget = report["used"] == {"hot": 5, "working": 0}
    whole_skip = report["skipped"]["working"] and report["skipped"]["working"][0]["id"] == "M-C"
    semantic_vs_budget_truth = (
        report["model_selected_ids"] == ["M-PIN", "M-B", "M-C"]
        and report["model_rejected_ids"] == ["M-LATE"]
        and report["budget_dropped_selected_ids"] == ["M-C"]
        and report["selection_incomplete_due_budget"] is True
    )
    grounding_reports_budget_drop = (
        report["budget_dropped_selected_ids"] == ["M-C"]
        and report["selection_incomplete_due_budget"] is True
        and report["grounding_incomplete"] is True
    )
    visibility_excluded = report["visibility_excluded"] == ["M-HIDDEN"]
    temporal_excluded = report["temporal_excluded"] == ["M-FUTURE"]
    invalidated_excluded = "M-X" in report["invalidated"] and "M-X" not in report["archive"]

    unknown_guard = False
    bad = json.loads(json.dumps(result))
    bad["judgment"]["selected_ids"] = ["M-PIN", "UNKNOWN"]
    try:
        pack_selection(payload, job, bad, hot_budget=5, working_budget=3)
    except ValueError:
        unknown_guard = True

    pin_omission_guard = False
    bad_pin = json.loads(json.dumps(result))
    bad_pin["judgment"]["selected_ids"] = ["M-B", "M-C"]
    try:
        pack_selection(payload, job, bad_pin, hot_budget=5, working_budget=3)
    except ValueError:
        pin_omission_guard = True

    question_guard = False
    bad_q = json.loads(json.dumps(result))
    bad_q["judgment"]["unresolved_questions"] = ["Q-UNKNOWN"]
    try:
        pack_selection(payload, job, bad_q, hot_budget=5, working_budget=3)
    except ValueError:
        question_guard = True

    question_as_of_story_order_guard = False
    future_q = json.loads(json.dumps(payload))
    future_q["task"]["active_questions"][0]["as_of_story_order"] = 10
    try:
        prepare_selection_job(future_q, subject_id="SCN-9")
    except ValueError:
        question_as_of_story_order_guard = True

    search_authorization_guard = False
    bad_search = json.loads(json.dumps(result))
    bad_search["judgment"].update({
        "decision": "search_more",
        "search_requests": [{"capability": "web_search", "query": "missing clue", "reason": "Need outside evidence."}],
    })
    try:
        pack_selection(payload, job, bad_search, hot_budget=5, working_budget=3)
    except ValueError:
        search_authorization_guard = True

    search_more_supported = False
    good_search = json.loads(json.dumps(result))
    good_search["judgment"].update({
        "decision": "search_more",
        "search_requests": [{"capability": "project_search", "query": "SCN-3 seal clue", "reason": "Need project evidence before stopping."}],
    })
    try:
        search_report = pack_selection(payload, job, good_search, hot_budget=5, working_budget=10)
        search_more_supported = (
            search_report["semantic_sufficiency_decision"] == "search_more"
            and search_report["search_requests"][0]["capability"] == "project_search"
            and search_report["grounding_incomplete"] is True
        )
    except ValueError:
        search_more_supported = False

    authority_guard = False
    try:
        normalize_item({"id": "BAD", "cost": 1, "derived": True, "authority": True, "source_refs": ["x"], "source_fingerprints": ["sha256:" + "f" * 64], "available_from_story_order": 0, "visibility": {"scope": "shared"}})
    except ValueError:
        authority_guard = True

    pin_visibility_guard = False
    conflict = json.loads(json.dumps(payload))
    conflict["items"].append({"id": "M-BAD-PIN", "cost": 1, "pinned": True, "derived": True, "authority": False, "source_refs": ["accepted:Z"], "source_fingerprints": ["sha256:" + "1" * 64], "available_from_story_order": 9, "visibility": {"scope": "character", "perspective_id": "CHAR-B"}, "model_view": {"label": "private"}})
    try:
        prepare_selection_job(conflict, subject_id="SCN-9")
    except ValueError:
        pin_visibility_guard = True

    pin_temporal_guard = False
    future_pin = json.loads(json.dumps(payload))
    future_pin["items"].append({"id": "M-FUTURE-PIN", "cost": 1, "pinned": True, "derived": True, "authority": False, "source_refs": ["accepted:FP"], "source_fingerprints": ["sha256:" + "2" * 64], "available_from_story_order": 10, "visibility": {"scope": "shared"}, "model_view": {"label": "future-pin"}})
    try:
        prepare_selection_job(future_pin, subject_id="SCN-9")
    except ValueError:
        pin_temporal_guard = True

    catalog_resolved = job.get("provenance", {}).get("pack_id") == "context-research"
    typed_input = job.get("provenance", {}).get("input_contract_validated") is True
    ok = all((
        catalog_resolved,
        typed_input,
        hidden_never_in_packet,
        pin_and_order,
        hard_budget,
        bool(whole_skip),
        semantic_vs_budget_truth,
        grounding_reports_budget_drop,
        visibility_excluded,
        temporal_excluded,
        invalidated_excluded,
        unknown_guard,
        pin_omission_guard,
        question_guard,
        question_as_of_story_order_guard,
        search_authorization_guard,
        search_more_supported,
        authority_guard,
        pin_visibility_guard,
        pin_temporal_guard,
    ))
    dump({
        "memory_tiers_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "semantic_relevance_owner": "model",
        "semantic_sufficiency_owner": "model",
        "semantic_search_intent_owner": "model",
        "catalog_resolved_contract_pack": catalog_resolved,
        "typed_input_contract": typed_input,
        "perspective_incompatible_never_enters_semantic_packet": hidden_never_in_packet,
        "future_block_never_enters_semantic_packet": temporal_excluded,
        "question_as_of_story_order_guard": question_as_of_story_order_guard,
        "pin_visibility_conflict_fail_closed": pin_visibility_guard,
        "pin_temporal_conflict_fail_closed": pin_temporal_guard,
        "pin_omission_fail_closed": pin_omission_guard,
        "hard_budget": hard_budget,
        "whole_item_or_skip": bool(whole_skip),
        "semantic_vs_budget_drop_distinguished": semantic_vs_budget_truth,
        "grounding_reports_budget_drop": grounding_reports_budget_drop,
        "visibility_excluded": visibility_excluded,
        "invalidated_excluded": invalidated_excluded,
        "unknown_selection_guard": unknown_guard,
        "unresolved_question_identity_guard": question_guard,
        "search_capability_authorization_guard": search_authorization_guard,
        "authorized_search_more_supported": search_more_supported,
        "derived_authority_false_enforced": authority_guard,
        "model_execution": False,
    })
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe perspective-safe model-selected context packer")
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--input", required=True)
    prep.add_argument("--subject-id", required=True)
    prep.add_argument("--source-session-id")
    prep.add_argument("--output")
    pack = sub.add_parser("pack")
    pack.add_argument("--input", required=True)
    pack.add_argument("--job", required=True)
    pack.add_argument("--result", required=True)
    pack.add_argument("--hot-budget", type=int, required=True)
    pack.add_argument("--working-budget", type=int, required=True)
    pack.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test()
    if args.command == "prepare":
        value = prepare_selection_job(
            load_json(Path(args.input)),
            subject_id=args.subject_id,
            source_session_id=args.source_session_id,
        )
    else:
        value = pack_selection(
            load_json(Path(args.input)),
            load_json(Path(args.job)),
            load_json(Path(args.result)),
            hot_budget=args.hot_budget,
            working_budget=args.working_budget,
        )
    dump(value, Path(args.output) if args.output else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
