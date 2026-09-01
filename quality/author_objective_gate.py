"""Mechanical binding for model-owned assessments of current author objectives.

The model decides whether prose meets an objective and supplies evidence.  This
module only checks exact objective identity, typed assessment fields, payload
fingerprints, and conjunctive result consistency.  It never inspects prose or
turns lexical/statistical measurements into literary judgments.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

SCHEMA = "quillframe_current_author_objectives_v1"
ASSESSMENT_STATUSES = {"met", "not_met", "uncertain"}
IMPACT_SCOPES = {"sentence", "paragraph", "scene", "chapter", "whole_candidate"}
REPAIR_ROUTES = {"no_change", "local_edit", "scene_realization", "fresh_realization"}


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def validate_author_objectives(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError(f"author_objectives must use {SCHEMA}")
    if value.get("priority") != "current_explicit_author_direction" or value.get("authority") is not False:
        raise ValueError("author_objectives priority/authority invalid")
    _sha(value.get("source_fingerprint"), "author_objectives.source_fingerprint")
    supplied_fingerprint = _sha(value.get("objectives_fingerprint"), "author_objectives.objectives_fingerprint")
    expected_fingerprint = _fingerprint({key: item for key, item in value.items() if key != "objectives_fingerprint"})
    if supplied_fingerprint != expected_fingerprint:
        raise ValueError("author_objectives fingerprint mismatch")
    items = value.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("author_objectives.items must be a non-empty array")
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"objective_id", "statement", "source_refs", "hard"}:
            raise ValueError(f"author_objectives.items[{index}] fields invalid")
        objective_id = item.get("objective_id")
        if not isinstance(objective_id, str) or not objective_id.strip() or objective_id in seen:
            raise ValueError(f"author_objectives.items[{index}].objective_id must be unique and non-empty")
        seen.add(objective_id)
        if not isinstance(item.get("statement"), str) or not item["statement"].strip():
            raise ValueError(f"author_objectives.items[{index}].statement required")
        refs = item.get("source_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
            raise ValueError(f"author_objectives.items[{index}].source_refs must be a non-empty string array")
        if not isinstance(item.get("hard"), bool):
            raise ValueError(f"author_objectives.items[{index}].hard must be boolean")
    return deepcopy(value)


def validate_objective_assessments(author_objectives: Any, judgment: Any) -> dict[str, Any]:
    objectives = validate_author_objectives(author_objectives)
    if not isinstance(judgment, dict):
        raise ValueError("objective judgment must be object")
    result = judgment.get("result")
    if result not in {"pass", "fail", "insufficient_evidence"}:
        raise ValueError("objective judgment.result invalid")
    assessments = judgment.get("objective_assessments")
    if not isinstance(assessments, list):
        raise ValueError("objective_assessments must be array")
    expected = {item["objective_id"]: item for item in objectives["items"]}
    observed: dict[str, dict[str, Any]] = {}
    required = {"objective_id", "status", "evidence_refs", "impact_scope", "repair_route", "report"}
    for index, assessment in enumerate(assessments):
        if not isinstance(assessment, dict) or set(assessment) != required:
            raise ValueError(f"objective_assessments[{index}] fields invalid")
        objective_id = assessment.get("objective_id")
        if objective_id not in expected or objective_id in observed:
            raise ValueError(f"objective_assessments[{index}].objective_id must bind one supplied objective exactly once")
        if assessment.get("status") not in ASSESSMENT_STATUSES:
            raise ValueError(f"objective_assessments[{index}].status invalid")
        if assessment.get("impact_scope") not in IMPACT_SCOPES:
            raise ValueError(f"objective_assessments[{index}].impact_scope invalid")
        if assessment.get("repair_route") not in REPAIR_ROUTES:
            raise ValueError(f"objective_assessments[{index}].repair_route invalid")
        if assessment["status"] == "met" and assessment["repair_route"] != "no_change":
            raise ValueError(
                f"objective_assessments[{index}] met objective must use repair_route=no_change"
            )
        if assessment["status"] != "met" and assessment["repair_route"] == "no_change":
            raise ValueError(
                f"objective_assessments[{index}] unmet/uncertain objective requires a repair route"
            )
        refs = assessment.get("evidence_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
            raise ValueError(f"objective_assessments[{index}].evidence_refs must be a non-empty string array")
        if not isinstance(assessment.get("report"), str) or not assessment["report"].strip():
            raise ValueError(f"objective_assessments[{index}].report required")
        observed[objective_id] = deepcopy(assessment)
    if set(observed) != set(expected):
        raise ValueError("objective_assessments must cover the exact supplied objective set")

    hard_statuses = [observed[item["objective_id"]]["status"] for item in objectives["items"] if item["hard"]]
    if "not_met" in hard_statuses and result != "fail":
        raise ValueError("a hard author objective marked not_met requires result=fail")
    if "not_met" not in hard_statuses and "uncertain" in hard_statuses and result != "insufficient_evidence":
        raise ValueError("an uncertain hard author objective requires result=insufficient_evidence")
    if result == "pass" and any(status != "met" for status in hard_statuses):
        raise ValueError("result=pass requires every hard author objective to be met")

    objective_status = "fail" if "not_met" in hard_statuses else (
        "pending" if "uncertain" in hard_statuses else "pass"
    )
    return {
        "objectives_fingerprint": objectives["objectives_fingerprint"],
        "status": objective_status,
        "assessments": [observed[item["objective_id"]] for item in objectives["items"]],
    }
