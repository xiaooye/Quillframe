"""Bind one fresh released chapter to one author review; never run a model.

This is an absolute, sequential review protocol. It deliberately has no arm,
baseline companion, pair ordering or comparative choice. Generation remains the
responsibility of the full production runtime and its release boundary.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from harness.context_runtime import fingerprint
from production_runtime.craft_guidance import (
    freeze_craft_library,
    validate_craft_snapshot,
)


CASE_SCHEMA = "quillframe_craft_chapter_case_v1"
SEQUENCE_SCHEMA = "quillframe_craft_chapter_review_sequence_v1"
PLAN_SCHEMA = "quillframe_craft_chapter_review_plan_v1"
ARTIFACT_SCHEMA = "quillframe_craft_chapter_review_artifact_v1"
OBSERVATION_SCHEMA = "quillframe_craft_chapter_observation_v1"
OUTCOMES = ("continue", "revise", "reject", "insufficient_evidence")
READER_FIELDS = {"genre_profile", "platform_profile", "chapter_position", "reader_grip"}
PLANNING_FIELDS = {"overall_outline", "chapter_outline", "scene_details"}
PROVENANCE_FIELDS = {
    "authorship", "fresh_for_reviewer", "derived_from_rejected_prose",
    "consumer_content_committed_to_framework",
}
SETTINGS_FIELDS = {"service_id", "model_id", "reasoning_effort"}
EXECUTION_EVIDENCE_FIELDS = {
    "run_id", "task_mode", "craft_guidance_mode", "craft_snapshot_fingerprint",
    "stage_receipts", "candidate_visible_operation",
}
SEQUENCE_FIELDS = {
    "schema", "sequence_id", "next_iteration", "reviewed_case_fingerprints",
    "latest_observation_fingerprint", "blocked_craft_snapshot_fingerprint",
    "predecessor_state_fingerprint", "created_at", "authority", "state_fingerprint",
}
PLAN_FIELDS = {
    "schema", "sequence_id", "sequence_state_fingerprint", "iteration", "review_id",
    "created_at", "case", "case_fingerprint", "craft_snapshot", "settings",
    "required_execution", "review_contract", "status", "model_execution", "authority",
    "taste_activation", "framework_promotion", "plan_fingerprint",
}
ARTIFACT_FIELDS = {
    "schema", "sequence_id", "iteration", "review_id", "plan_fingerprint",
    "case_fingerprint", "unit_kind", "chapter_title", "reader_context", "chapter",
    "candidate_fingerprint", "production_release_fingerprint", "created_at",
    "synthetic_test_only", "quality_claim", "authority", "taste_activation",
    "framework_promotion", "artifact_fingerprint",
}
OBSERVATION_FIELDS = {
    "schema", "sequence_id", "iteration", "review_id", "artifact_fingerprint",
    "case_fingerprint", "candidate_fingerprint", "outcome", "reason", "reviewer_ref",
    "prior_exposure", "review_eligible", "requires_candidate_change_before_next_generation",
    "created_at", "quality_claim_scope", "authority", "taste_activation",
    "framework_promotion", "observation_fingerprint",
}
_FP_PREFIX = "sha256:"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_fingerprint(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith(_FP_PREFIX) or len(value) != 71:
        return False
    try:
        int(value[7:], 16)
    except ValueError:
        return False
    return True


def _seal(value: dict[str, Any], field: str) -> dict[str, Any]:
    value[field] = fingerprint({key: item for key, item in value.items() if key != field})
    return value


def _check(value: dict[str, Any], field: str) -> None:
    _require(value.get(field) == fingerprint({key: item for key, item in value.items() if key != field}), field + " changed")


def _text_fingerprint(text: str) -> str:
    return _FP_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _when(created_at: str | None) -> str:
    value = created_at or datetime.now(timezone.utc).isoformat()
    _require(_nonempty(value), "created_at required")
    return value


def validate_case(case: Any) -> None:
    _require(isinstance(case, dict) and set(case) == {
        "schema", "case_id", "unit_kind", "title", "generation_request", "reader_context",
        "planning", "writer_safe_facts", "pov_boundary", "provenance",
    }, "chapter case must be closed and complete")
    _require(case["schema"] == CASE_SCHEMA, "invalid chapter case schema")
    _require(case["unit_kind"] == "chapter", "review unit must be a chapter, not an excerpt")
    _require(all(_nonempty(case[key]) for key in ("case_id", "title", "generation_request")), "chapter identity and request required")
    reader = case["reader_context"]
    _require(isinstance(reader, dict) and set(reader) == READER_FIELDS
             and all(_nonempty(value) for value in reader.values()), "explicit reader context required")
    planning = case["planning"]
    _require(isinstance(planning, dict) and set(planning) == PLANNING_FIELDS
             and all(_nonempty(value) for value in planning.values()), "three planning levels required")
    facts = case["writer_safe_facts"]
    _require(isinstance(facts, list) and bool(facts) and all(_nonempty(value) for value in facts), "writer-safe facts required")
    _require(isinstance(case["pov_boundary"], dict) and bool(case["pov_boundary"]), "POV boundary required")
    provenance = case["provenance"]
    _require(isinstance(provenance, dict) and set(provenance) == PROVENANCE_FIELDS, "closed provenance required")
    _require(provenance["authorship"] in {"original_evaluation_case", "authorized_project_material"}, "invalid case authorship")
    _require(provenance["fresh_for_reviewer"] is True, "review case must be fresh")
    _require(provenance["derived_from_rejected_prose"] is False, "rejected prose cannot seed a new Writer case")
    _require(provenance["consumer_content_committed_to_framework"] is False, "consumer material cannot enter generic framework source")


def start_sequence(sequence_id: str, *, blocked_craft_snapshot_fingerprint: str | None = None,
                   created_at: str | None = None) -> dict[str, Any]:
    """Create immutable genesis state for a one-chapter-at-a-time review chain."""
    _require(_nonempty(sequence_id), "sequence_id required")
    _require(blocked_craft_snapshot_fingerprint is None or _is_fingerprint(blocked_craft_snapshot_fingerprint),
             "blocked snapshot must be a fingerprint")
    state = {
        "schema": SEQUENCE_SCHEMA,
        "sequence_id": sequence_id,
        "next_iteration": 1,
        "reviewed_case_fingerprints": [],
        "latest_observation_fingerprint": None,
        "blocked_craft_snapshot_fingerprint": blocked_craft_snapshot_fingerprint,
        "predecessor_state_fingerprint": None,
        "created_at": _when(created_at),
        "authority": False,
    }
    return _seal(state, "state_fingerprint")


def validate_sequence(state: Any) -> None:
    _require(isinstance(state, dict) and set(state) == SEQUENCE_FIELDS
             and state.get("schema") == SEQUENCE_SCHEMA and state.get("authority") is False,
             "invalid review sequence")
    _check(state, "state_fingerprint")
    _require(_nonempty(state.get("sequence_id")) and isinstance(state.get("next_iteration"), int)
             and state["next_iteration"] >= 1, "invalid review sequence identity")
    reviewed = state.get("reviewed_case_fingerprints")
    _require(isinstance(reviewed, list) and len(reviewed) == len(set(reviewed))
             and all(_is_fingerprint(value) for value in reviewed), "invalid reviewed case lineage")
    for field in ("latest_observation_fingerprint", "blocked_craft_snapshot_fingerprint", "predecessor_state_fingerprint"):
        _require(state.get(field) is None or _is_fingerprint(state[field]), "invalid sequence fingerprint field")


def prepare_review(state: dict[str, Any], case: dict[str, Any], *, settings: dict[str, Any],
                   craft_snapshot: dict[str, Any] | None = None,
                   created_at: str | None = None) -> dict[str, Any]:
    """Freeze one fresh case and one candidate edition. This performs zero model calls."""
    validate_sequence(state)
    validate_case(case)
    _require(isinstance(settings, dict) and set(settings) == SETTINGS_FIELDS
             and all(_nonempty(value) for value in settings.values()), "exact host model settings required")
    case_fingerprint = fingerprint(case)
    _require(case_fingerprint not in state["reviewed_case_fingerprints"], "chapter case was already reviewed")
    snapshot = deepcopy(craft_snapshot) if craft_snapshot is not None else freeze_craft_library("outline_driven")
    validate_craft_snapshot(snapshot)
    _require(snapshot["mode"] == "outline_driven" and snapshot["authority"] is False, "candidate craft snapshot required")
    blocked = state["blocked_craft_snapshot_fingerprint"]
    _require(blocked is None or snapshot["snapshot_fingerprint"] != blocked,
             "the rejected craft snapshot must change before another chapter")
    review_id = "chapter-review-" + fingerprint([
        state["sequence_id"], state["next_iteration"], case_fingerprint, snapshot["snapshot_fingerprint"],
    ])[7:23]
    plan = {
        "schema": PLAN_SCHEMA,
        "sequence_id": state["sequence_id"],
        "sequence_state_fingerprint": state["state_fingerprint"],
        "iteration": state["next_iteration"],
        "review_id": review_id,
        "created_at": _when(created_at),
        "case": deepcopy(case),
        "case_fingerprint": case_fingerprint,
        "craft_snapshot": snapshot,
        "settings": deepcopy(settings),
        "required_execution": {
            "task_mode": "DRAFT",
            "craft_guidance_mode": "outline_driven",
            "full_production_runtime": True,
            "character_simulation_required": True,
            "reader_pressure_required": True,
            "user_visible_operation": "candidate.visible.get",
        },
        "review_contract": {
            "visible_chapter_count": 1,
            "comparative_review": False,
            "baseline_companion": False,
            "author_feedback_before_next_iteration": True,
            "rejected_prose_in_writer_context": False,
        },
        "status": "prepared_not_executed",
        "model_execution": False,
        "authority": False,
        "taste_activation": False,
        "framework_promotion": False,
    }
    return _seal(plan, "plan_fingerprint")


def validate_plan(plan: Any) -> None:
    _require(isinstance(plan, dict) and set(plan) == PLAN_FIELDS
             and plan.get("schema") == PLAN_SCHEMA and plan.get("authority") is False,
             "invalid chapter review plan")
    _check(plan, "plan_fingerprint")
    validate_case(plan.get("case"))
    _require(plan.get("case_fingerprint") == fingerprint(plan["case"]), "chapter case binding changed")
    validate_craft_snapshot(plan.get("craft_snapshot"))
    _require(isinstance(plan.get("settings"), dict) and set(plan["settings"]) == SETTINGS_FIELDS
             and all(_nonempty(value) for value in plan["settings"].values()), "invalid frozen host settings")
    contract = plan.get("review_contract", {})
    _require(contract.get("visible_chapter_count") == 1 and contract.get("comparative_review") is False
             and contract.get("baseline_companion") is False
             and contract.get("author_feedback_before_next_iteration") is True
             and contract.get("rejected_prose_in_writer_context") is False, "invalid single-chapter review contract")
    execution = plan.get("required_execution", {})
    _require(execution == {
        "task_mode": "DRAFT", "craft_guidance_mode": "outline_driven",
        "full_production_runtime": True, "character_simulation_required": True,
        "reader_pressure_required": True, "user_visible_operation": "candidate.visible.get",
    }, "full production execution is required")
    _require(plan.get("status") == "prepared_not_executed" and plan.get("model_execution") is False,
             "preparation cannot claim model execution")


def _validate_release(visible: dict[str, Any]) -> None:
    required = {
        "schema", "candidate_id", "candidate_fingerprint", "content", "production_release",
        "content_access", "accepted", "settled", "private_reasoning_exposed", "authority", "canon_authority",
    }
    _require(isinstance(visible, dict) and required <= set(visible), "Core visible candidate projection required")
    _require(visible["schema"] == "quillframe_user_visible_candidate_v1"
             and visible["content_access"] == "production_release_only", "invalid visible candidate boundary")
    _require(_nonempty(visible["content"]) and visible["candidate_fingerprint"] == _text_fingerprint(visible["content"]),
             "visible chapter fingerprint changed")
    _require(visible["accepted"] is False and visible["settled"] is False
             and visible["private_reasoning_exposed"] is False
             and visible["authority"] is False and visible["canon_authority"] is False,
             "review draft must remain non-authoritative and private-reasoning safe")
    release = visible["production_release"]
    _require(isinstance(release, dict) and release.get("schema") == "quillframe_production_release_v1"
             and release.get("candidate_fingerprint") == visible["candidate_fingerprint"]
             and release.get("ready_for_user_visible_review") is True, "valid production release required")
    _check(release, "release_fingerprint")


def bind_visible_chapter(plan: dict[str, Any], visible: dict[str, Any], *,
                         execution_evidence: dict[str, Any], synthetic_test_only: bool = False,
                         created_at: str | None = None) -> dict[str, Any]:
    """Export only one released chapter and its declared reader context."""
    validate_plan(plan)
    _validate_release(visible)
    _require(isinstance(execution_evidence, dict) and set(execution_evidence) == EXECUTION_EVIDENCE_FIELDS,
             "closed full-production execution evidence required")
    _require(_nonempty(execution_evidence["run_id"])
             and execution_evidence["task_mode"] == "DRAFT"
             and execution_evidence["craft_guidance_mode"] == "outline_driven"
             and execution_evidence["craft_snapshot_fingerprint"] == plan["craft_snapshot"]["snapshot_fingerprint"]
             and execution_evidence["candidate_visible_operation"] == "candidate.visible.get",
             "chapter was not bound to the required full production execution")
    receipts = execution_evidence["stage_receipts"]
    _require(isinstance(receipts, list) and bool(receipts), "full production stage receipts required")
    by_mechanism: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        _require(isinstance(receipt, dict) and _nonempty(receipt.get("mechanism"))
                 and receipt["mechanism"] not in by_mechanism, "duplicate or invalid production stage receipt")
        _check(receipt, "stage_result_fingerprint")
        judgment = receipt.get("judgment")
        _require(isinstance(judgment, dict) and judgment.get("status") == "pass"
                 and _is_fingerprint(receipt.get("context_bundle_fingerprint")),
                 "production stage did not pass against a frozen bundle")
        by_mechanism[receipt["mechanism"]] = receipt
    required_mechanisms = {"character_simulation", "reader_pressure"}
    _require(required_mechanisms <= set(by_mechanism), "Character Simulation and Reader Pressure receipts required")
    _require(len({by_mechanism[name]["context_bundle_fingerprint"] for name in required_mechanisms}) == 1,
             "required production stages belong to different context bundles")
    _require(isinstance(synthetic_test_only, bool), "synthetic_test_only must be boolean")
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "sequence_id": plan["sequence_id"],
        "iteration": plan["iteration"],
        "review_id": plan["review_id"],
        "plan_fingerprint": plan["plan_fingerprint"],
        "case_fingerprint": plan["case_fingerprint"],
        "unit_kind": "chapter",
        "chapter_title": plan["case"]["title"],
        "reader_context": deepcopy(plan["case"]["reader_context"]),
        "chapter": visible["content"],
        "candidate_fingerprint": visible["candidate_fingerprint"],
        "production_release_fingerprint": visible["production_release"]["release_fingerprint"],
        "created_at": _when(created_at),
        "synthetic_test_only": synthetic_test_only,
        "quality_claim": False,
        "authority": False,
        "taste_activation": False,
        "framework_promotion": False,
    }
    return _seal(artifact, "artifact_fingerprint")


def validate_artifact(artifact: Any) -> None:
    _require(isinstance(artifact, dict) and set(artifact) == ARTIFACT_FIELDS
             and artifact.get("schema") == ARTIFACT_SCHEMA
             and artifact.get("authority") is False, "invalid chapter review artifact")
    _check(artifact, "artifact_fingerprint")
    _require(artifact.get("unit_kind") == "chapter" and _nonempty(artifact.get("chapter"))
             and artifact.get("candidate_fingerprint") == _text_fingerprint(artifact["chapter"]),
             "review chapter changed")
    _require(set(artifact.get("reader_context", {})) == READER_FIELDS, "reader context changed")
    _require(artifact.get("quality_claim") is False and artifact.get("taste_activation") is False
             and artifact.get("framework_promotion") is False, "review artifact cannot promote itself")


def chapter_observation(artifact: dict[str, Any], *, outcome: str, reason: str,
                        reviewer_ref: str, prior_exposure: bool = False,
                        created_at: str | None = None) -> dict[str, Any]:
    validate_artifact(artifact)
    _require(outcome in OUTCOMES, "invalid chapter review outcome")
    _require(_nonempty(reason) and _nonempty(reviewer_ref) and isinstance(prior_exposure, bool),
             "attributed author feedback required")
    observation = {
        "schema": OBSERVATION_SCHEMA,
        "sequence_id": artifact["sequence_id"],
        "iteration": artifact["iteration"],
        "review_id": artifact["review_id"],
        "artifact_fingerprint": artifact["artifact_fingerprint"],
        "case_fingerprint": artifact["case_fingerprint"],
        "candidate_fingerprint": artifact["candidate_fingerprint"],
        "outcome": outcome,
        "reason": reason,
        "reviewer_ref": reviewer_ref,
        "prior_exposure": prior_exposure,
        "review_eligible": not prior_exposure and not artifact["synthetic_test_only"],
        "requires_candidate_change_before_next_generation": outcome in {"revise", "reject"},
        "created_at": _when(created_at),
        "quality_claim_scope": "this_chapter_only",
        "authority": False,
        "taste_activation": False,
        "framework_promotion": False,
    }
    return _seal(observation, "observation_fingerprint")


def _validate_observation(observation: Any) -> None:
    _require(isinstance(observation, dict) and set(observation) == OBSERVATION_FIELDS
             and observation.get("schema") == OBSERVATION_SCHEMA
             and observation.get("outcome") in OUTCOMES and observation.get("authority") is False,
             "invalid chapter observation")
    _check(observation, "observation_fingerprint")
    _require(observation.get("taste_activation") is False and observation.get("framework_promotion") is False,
             "chapter observation cannot promote itself")


def advance_sequence(state: dict[str, Any], plan: dict[str, Any], artifact: dict[str, Any],
                     observation: dict[str, Any], *, created_at: str | None = None) -> dict[str, Any]:
    """Permit the next chapter only after feedback bound to the current chapter."""
    validate_sequence(state)
    validate_plan(plan)
    validate_artifact(artifact)
    _validate_observation(observation)
    _require(plan["sequence_state_fingerprint"] == state["state_fingerprint"]
             and plan["iteration"] == state["next_iteration"], "plan does not continue this sequence state")
    _require(artifact["plan_fingerprint"] == plan["plan_fingerprint"]
             and observation["artifact_fingerprint"] == artifact["artifact_fingerprint"],
             "chapter feedback lineage changed")
    _require(observation["case_fingerprint"] == plan["case_fingerprint"]
             and observation["candidate_fingerprint"] == artifact["candidate_fingerprint"],
             "observation belongs to another chapter")
    reviewed = [*state["reviewed_case_fingerprints"], plan["case_fingerprint"]]
    next_state = {
        "schema": SEQUENCE_SCHEMA,
        "sequence_id": state["sequence_id"],
        "next_iteration": state["next_iteration"] + 1,
        "reviewed_case_fingerprints": reviewed,
        "latest_observation_fingerprint": observation["observation_fingerprint"],
        "blocked_craft_snapshot_fingerprint": (
            plan["craft_snapshot"]["snapshot_fingerprint"]
            if observation["requires_candidate_change_before_next_generation"] else None
        ),
        "predecessor_state_fingerprint": state["state_fingerprint"],
        "created_at": _when(created_at),
        "authority": False,
    }
    return _seal(next_state, "state_fingerprint")


def save_new(path: Path, value: dict[str, Any]) -> None:
    """Create an append-only review artifact and refuse replacement."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
