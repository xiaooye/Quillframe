#!/usr/bin/env python3
"""Validate and consume unsolicited author steering at explicit NovelForge safe points.

This module is deterministic runtime plumbing. It does not interpret literary intent,
run a model, mutate Project/Canon state, or execute the follow-up operation selected
by the manager. Transport and exactly-once persistence are delegated to the existing
Control Plane (`feedback.observed` envelope + consume_once receipt).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import control_plane  # type: ignore  # noqa: E402

REQUEST_SCHEMA = "novelforge_author_steering_request_v1"
SAFE_POINT_SCHEMA = "novelforge_author_steering_safe_point_v1"
DECISION_SCHEMA = "novelforge_author_steering_decision_v1"
VALIDATION_SCHEMA = "novelforge_author_steering_validation_v1"
CONSUMPTION_SCHEMA = "novelforge_author_steering_consumption_v1"
TRANSPORT_EVENT_TYPE = "feedback.observed"
SOURCE_KINDS = {"user", "authorized_human"}
SCOPES = {"current_run", "future_only"}
TIMINGS = {"next_safe_point", "before_draft", "before_review", "future_only"}
SAFE_POINT_KINDS = {
    "between_operations",
    "before_context_rebuild",
    "before_draft",
    "before_review",
    "after_handoff",
    "before_runtime_command",
}
ROUTES = {
    "continue",
    "rebuild_context",
    "replan",
    "regenerate",
    "cancel_handoff",
    "await_user",
    "defer_future",
}
BINDING_MODES = {"exact", "drift_acknowledged"}
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value))


def nonempty(value: Any, field: str, *, max_len: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_len:
        raise ValueError(f"{field} must be a non-empty string <= {max_len} chars")
    return value.strip()


def fingerprint(value: Any) -> str:
    return control_plane.digest(value)


def _sha_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    if any(not is_sha(x) for x in value):
        raise ValueError(f"{field} must contain sha256 fingerprints only")
    if value != sorted(set(value)):
        raise ValueError(f"{field} must be sorted and unique")
    return list(value)


def _str_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError(f"{field} must be an array of non-empty strings")
    if value != sorted(set(value)):
        raise ValueError(f"{field} must be sorted and unique")
    return list(value)


def validate_request_event(event: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        control_plane.ControlPlane.validate_event(event)
    except Exception as exc:
        errors.append("control_plane_event_invalid:" + str(exc))

    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    if event.get("event_type") != TRANSPORT_EVENT_TYPE:
        errors.append("transport_event_type_must_be_feedback_observed")
    if event.get("authority_scope") != "request":
        errors.append("authority_scope_must_be_request")
    source = event.get("source") if isinstance(event.get("source"), dict) else {}
    if source.get("kind") not in SOURCE_KINDS:
        errors.append("steering_source_must_be_user_or_authorized_human")
    if payload.get("schema") != REQUEST_SCHEMA:
        errors.append("steering_request_schema_invalid")
    if payload.get("authority") is not False:
        errors.append("steering_request_authority_must_be_false")
    try:
        steering_id = nonempty(payload.get("steering_id"), "payload.steering_id", max_len=160)
        if steering_id != event.get("event_id"):
            errors.append("steering_id_must_equal_event_id")
        scope = payload.get("scope")
        if scope not in SCOPES:
            errors.append("scope_invalid")
        instruction = nonempty(payload.get("instruction"), "payload.instruction", max_len=20000)
        target = payload.get("target")
        authored = payload.get("authored_against")
        if not isinstance(target, dict):
            raise ValueError("payload.target must be object")
        if not isinstance(authored, dict):
            raise ValueError("payload.authored_against must be object")
        target_fields = {"resource_id", "session_id", "run_id", "authored_checkpoint_id", "timing", "future_ref"}
        if set(target) - target_fields:
            errors.append("target_has_unsupported_fields")
        resource_id = nonempty(target.get("resource_id"), "target.resource_id")
        session_id = nonempty(target.get("session_id"), "target.session_id")
        run_id = nonempty(target.get("run_id"), "target.run_id")
        checkpoint_id = nonempty(target.get("authored_checkpoint_id"), "target.authored_checkpoint_id")
        timing = target.get("timing")
        if timing not in TIMINGS:
            errors.append("timing_invalid")
        if resource_id != event.get("resource_id"):
            errors.append("resource_id_mismatch")
        if session_id != event.get("session_id"):
            errors.append("session_id_mismatch")
        if run_id != event.get("run_id"):
            errors.append("run_id_mismatch")
        if scope == "future_only":
            if timing != "future_only":
                errors.append("future_only_scope_requires_future_only_timing")
            try:
                nonempty(target.get("future_ref"), "target.future_ref")
            except ValueError as exc:
                errors.append(str(exc))
        else:
            if timing == "future_only":
                errors.append("current_run_scope_cannot_use_future_only_timing")
            if target.get("future_ref") not in (None, ""):
                errors.append("current_run_scope_cannot_set_future_ref")
        artifacts = _sha_list(authored.get("artifact_fingerprints"), "authored_against.artifact_fingerprints")
        if artifacts != event.get("artifact_fingerprints"):
            errors.append("event_artifact_fingerprints_must_equal_authored_against")
        context_fp = authored.get("context_manifest_fingerprint")
        if context_fp is not None and not is_sha(context_fp):
            errors.append("context_manifest_fingerprint_invalid")
    except ValueError as exc:
        errors.append(str(exc))
        instruction = None
        checkpoint_id = None
        artifacts = []
        context_fp = None
        scope = payload.get("scope")
        timing = None

    errors = list(dict.fromkeys(errors))
    valid = not errors
    return {
        "schema": VALIDATION_SCHEMA,
        "kind": "request_event",
        "valid": valid,
        "errors": errors,
        "event_fingerprint": fingerprint(event),
        "request_fingerprint": fingerprint(payload) if isinstance(payload, dict) else None,
        "scope": scope,
        "timing": timing,
        "authored_checkpoint_id": checkpoint_id,
        "artifact_fingerprints": artifacts,
        "context_manifest_fingerprint": context_fp,
        "instruction_present": bool(instruction),
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "project_write_authority": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def validate_safe_point(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    allowed = {
        "schema", "resource_id", "session_id", "run_id", "checkpoint_id", "safe_point_id",
        "safe_point_kind", "artifact_fingerprints", "context_manifest_fingerprint",
        "session_payload_hash", "pending_handoffs", "in_consequential_write_transaction", "authority",
    }
    if set(value) - allowed:
        errors.append("safe_point_has_unsupported_fields")
    if value.get("schema") != SAFE_POINT_SCHEMA:
        errors.append("safe_point_schema_invalid")
    try:
        for field in ("resource_id", "session_id", "run_id", "checkpoint_id", "safe_point_id"):
            nonempty(value.get(field), field, max_len=200)
        if value.get("safe_point_kind") not in SAFE_POINT_KINDS:
            errors.append("safe_point_kind_invalid")
        artifacts = _sha_list(value.get("artifact_fingerprints"), "artifact_fingerprints")
        context_fp = value.get("context_manifest_fingerprint")
        if context_fp is not None and not is_sha(context_fp):
            errors.append("context_manifest_fingerprint_invalid")
        if not is_sha(value.get("session_payload_hash")):
            errors.append("session_payload_hash_invalid")
        pending = value.get("pending_handoffs")
        if not isinstance(pending, list):
            errors.append("pending_handoffs_must_be_array")
            pending = []
        seen: set[str] = set()
        for item in pending:
            if not isinstance(item, dict) or set(item) != {"handoff_id", "artifact_fingerprints"}:
                errors.append("pending_handoff_shape_invalid")
                continue
            hid = nonempty(item.get("handoff_id"), "pending_handoff.handoff_id", max_len=200)
            if hid in seen:
                errors.append("pending_handoff_duplicate")
            seen.add(hid)
            _sha_list(item.get("artifact_fingerprints"), "pending_handoff.artifact_fingerprints")
        if value.get("in_consequential_write_transaction") is not False:
            errors.append("consequential_write_transaction_is_not_interruptible")
        if value.get("authority") is not False:
            errors.append("safe_point_authority_must_be_false")
    except ValueError as exc:
        errors.append(str(exc))
        artifacts = []
        context_fp = None
    errors = list(dict.fromkeys(errors))
    return {
        "schema": VALIDATION_SCHEMA,
        "kind": "safe_point",
        "valid": not errors,
        "errors": errors,
        "safe_point_fingerprint": fingerprint(value),
        "artifact_fingerprints": artifacts,
        "context_manifest_fingerprint": context_fp,
        "authority": False,
        "model_execution": False,
    }


def _timing_matches(timing: str, safe_point_kind: str) -> bool:
    if timing == "next_safe_point":
        return safe_point_kind in SAFE_POINT_KINDS
    if timing == "before_draft":
        return safe_point_kind == "before_draft"
    if timing == "before_review":
        return safe_point_kind == "before_review"
    return False


def validate_decision(event: dict[str, Any], safe_point: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    req = validate_request_event(event)
    sp = validate_safe_point(safe_point)
    errors: list[str] = []
    if not req["valid"]:
        errors.append("steering_request_invalid")
    if not sp["valid"]:
        errors.append("safe_point_invalid")

    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    target = payload.get("target") if isinstance(payload.get("target"), dict) else {}
    authored = payload.get("authored_against") if isinstance(payload.get("authored_against"), dict) else {}

    allowed = {
        "schema", "decision_id", "steering_event_id", "steering_event_fingerprint", "session_id", "run_id",
        "safe_point_fingerprint", "route", "binding_mode", "authored_against_artifact_fingerprints",
        "observed_current_artifact_fingerprints", "invalidate_artifact_fingerprints", "cancel_handoff_ids",
        "rationale_ref", "authority",
    }
    if set(decision) - allowed:
        errors.append("decision_has_unsupported_fields")
    if decision.get("schema") != DECISION_SCHEMA:
        errors.append("decision_schema_invalid")
    try:
        nonempty(decision.get("decision_id"), "decision_id", max_len=160)
        if decision.get("steering_event_id") != event.get("event_id"):
            errors.append("decision_event_id_mismatch")
        if decision.get("steering_event_fingerprint") != req.get("event_fingerprint"):
            errors.append("decision_event_fingerprint_mismatch")
        if decision.get("session_id") != event.get("session_id") or decision.get("session_id") != safe_point.get("session_id"):
            errors.append("decision_session_mismatch")
        if decision.get("run_id") != event.get("run_id") or decision.get("run_id") != safe_point.get("run_id"):
            errors.append("decision_run_mismatch")
        if safe_point.get("resource_id") != event.get("resource_id"):
            errors.append("safe_point_resource_mismatch")
        if decision.get("safe_point_fingerprint") != sp.get("safe_point_fingerprint"):
            errors.append("decision_safe_point_fingerprint_mismatch")
        route = decision.get("route")
        if route not in ROUTES:
            errors.append("route_invalid")
        binding_mode = decision.get("binding_mode")
        if binding_mode not in BINDING_MODES:
            errors.append("binding_mode_invalid")
        authored_list = _sha_list(decision.get("authored_against_artifact_fingerprints"), "authored_against_artifact_fingerprints")
        current_list = _sha_list(decision.get("observed_current_artifact_fingerprints"), "observed_current_artifact_fingerprints")
        invalidate = _sha_list(decision.get("invalidate_artifact_fingerprints"), "invalidate_artifact_fingerprints")
        cancel_ids = _str_list(decision.get("cancel_handoff_ids"), "cancel_handoff_ids")
        expected_authored = authored.get("artifact_fingerprints") if isinstance(authored.get("artifact_fingerprints"), list) else []
        if authored_list != expected_authored:
            errors.append("decision_authored_against_mismatch")
        if current_list != safe_point.get("artifact_fingerprints"):
            errors.append("decision_current_artifacts_mismatch")
        drift = authored_list != current_list or authored.get("context_manifest_fingerprint") != safe_point.get("context_manifest_fingerprint")
        if drift and binding_mode != "drift_acknowledged":
            errors.append("artifact_or_context_drift_requires_acknowledgement")
        if not drift and binding_mode != "exact":
            errors.append("exact_binding_required_when_no_drift")
        if payload.get("scope") == "future_only":
            errors.append("future_only_steering_cannot_be_consumed_in_current_run")
        if payload.get("scope") == "current_run" and not _timing_matches(target.get("timing"), safe_point.get("safe_point_kind")):
            errors.append("safe_point_does_not_match_requested_timing")
        if route == "defer_future":
            errors.append("defer_future_is_not_a_current_run_consumption_route")
        if route == "continue" and (invalidate or cancel_ids):
            errors.append("continue_route_cannot_invalidate_or_cancel")
        if route == "cancel_handoff" and not cancel_ids:
            errors.append("cancel_handoff_route_requires_handoff")
        nonempty(decision.get("rationale_ref"), "rationale_ref", max_len=512)
        if decision.get("authority") is not False:
            errors.append("decision_authority_must_be_false")

        pending = safe_point.get("pending_handoffs") if isinstance(safe_point.get("pending_handoffs"), list) else []
        pending_map = {
            x.get("handoff_id"): set(x.get("artifact_fingerprints", []))
            for x in pending if isinstance(x, dict) and isinstance(x.get("handoff_id"), str)
        }
        unknown_cancel = sorted(set(cancel_ids) - set(pending_map))
        if unknown_cancel:
            errors.append("cancel_handoff_not_pending:" + ",".join(unknown_cancel))
        invalidated = set(invalidate)
        affected_pending = sorted(hid for hid, fps in pending_map.items() if invalidated.intersection(fps))
        missing_cancel = sorted(set(affected_pending) - set(cancel_ids))
        if missing_cancel:
            errors.append("invalidated_candidate_has_uncancelled_handoff:" + ",".join(missing_cancel))
    except ValueError as exc:
        errors.append(str(exc))
        route = decision.get("route")
        binding_mode = decision.get("binding_mode")
        drift = None
        invalidate = []
        cancel_ids = []
        affected_pending = []

    errors = list(dict.fromkeys(errors))
    required_ops: list[str] = []
    if route == "rebuild_context":
        required_ops.append("context.rebuild")
    elif route == "replan":
        required_ops.append("plan.reconcile")
    elif route == "regenerate":
        required_ops.append("candidate.regenerate")
    elif route == "cancel_handoff":
        required_ops.append("handoff.cancel_or_reclaim")
    elif route == "await_user":
        required_ops.append("session.await_user")
    for fp_value in invalidate:
        required_ops.append("invalidate_artifact:" + fp_value)
    for hid in cancel_ids:
        required_ops.append("cancel_handoff:" + hid)

    valid = not errors
    return {
        "schema": VALIDATION_SCHEMA,
        "kind": "decision",
        "valid": valid,
        "errors": errors,
        "decision_fingerprint": fingerprint(decision),
        "event_fingerprint": req.get("event_fingerprint"),
        "safe_point_fingerprint": sp.get("safe_point_fingerprint"),
        "route": route,
        "binding_mode": binding_mode,
        "drift_detected": drift,
        "affected_pending_handoffs": affected_pending,
        "required_follow_up_ops": required_ops,
        "follow_up_executed": False,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "project_write_authority": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def ingest(cp: control_plane.ControlPlane, event: dict[str, Any]) -> dict[str, Any]:
    validation = validate_request_event(event)
    if not validation["valid"]:
        raise ValueError("invalid author steering event: " + ";".join(validation["errors"]))
    result = cp.ingest_event(event)
    return {
        "schema": "novelforge_author_steering_ingest_v1",
        **result,
        "steering_event_fingerprint": validation["event_fingerprint"],
        "authority": False,
        "model_execution": False,
    }


def current_run_applicability(event: dict[str, Any], *, session_id: str, run_id: str) -> dict[str, Any]:
    validation = validate_request_event(event)
    if not validation["valid"]:
        return {"applicable": False, "reason": "invalid", "validation": validation}
    payload = event["payload"]
    if payload.get("scope") == "future_only":
        return {"applicable": False, "reason": "future_only", "validation": validation}
    if event.get("session_id") != session_id or event.get("run_id") != run_id:
        return {"applicable": False, "reason": "different_run", "validation": validation}
    return {"applicable": True, "reason": "current_run", "validation": validation}


def consume(
    cp: control_plane.ControlPlane,
    event: dict[str, Any],
    safe_point: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    validation = validate_decision(event, safe_point, decision)
    if not validation["valid"]:
        raise ValueError("author steering decision invalid: " + ";".join(validation["errors"]))
    binding_hash = fingerprint({
        "event_fingerprint": validation["event_fingerprint"],
        "safe_point_fingerprint": validation["safe_point_fingerprint"],
        "decision_fingerprint": validation["decision_fingerprint"],
    })
    consumer = f"author_steering:{event['session_id']}:{event['run_id']}"
    receipt = cp.consume_once("author_steering", event["event_id"], consumer, binding_hash)
    return {
        "schema": CONSUMPTION_SCHEMA,
        "steering_event_id": event["event_id"],
        "steering_event_fingerprint": validation["event_fingerprint"],
        "decision_fingerprint": validation["decision_fingerprint"],
        "safe_point_fingerprint": validation["safe_point_fingerprint"],
        "binding_fingerprint": binding_hash,
        "session_id": event["session_id"],
        "run_id": event["run_id"],
        "route": validation["route"],
        "consumed": receipt["consumed"],
        "already_consumed": receipt["already_consumed"],
        "required_follow_up_ops": validation["required_follow_up_ops"],
        "follow_up_executed": False,
        "replay_safe": True,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "project_write_authority": False,
        "settlement_authority": False,
        "model_execution": False,
    }


def _fixture_event(*, scope: str = "current_run", timing: str = "next_safe_point", instruction: str = "Change the next draft to Mei's POV.") -> dict[str, Any]:
    artifacts = ["sha256:" + "a" * 64]
    target = {
        "resource_id": "BOOK-STEER",
        "session_id": "SES-MANAGER",
        "run_id": "RUN-1",
        "authored_checkpoint_id": "CP-7",
        "timing": timing,
        "future_ref": "CH-010" if scope == "future_only" else None,
    }
    request = {
        "schema": REQUEST_SCHEMA,
        "steering_id": "EV-STEER-1" if scope == "current_run" else "EV-STEER-FUTURE",
        "scope": scope,
        "instruction": instruction,
        "target": target,
        "authored_against": {
            "artifact_fingerprints": artifacts,
            "context_manifest_fingerprint": "sha256:" + "b" * 64,
        },
        "authority": False,
    }
    return {
        "schema": control_plane.EVENT_SCHEMA,
        "event_id": request["steering_id"],
        "event_type": TRANSPORT_EVENT_TYPE,
        "source": {"kind": "user", "actor": "author", "transport": "current_chat", "external_ref": None},
        "resource_id": "BOOK-STEER",
        "session_id": "SES-MANAGER",
        "run_id": "RUN-1",
        "handoff_id": None,
        "authority_scope": "request",
        "idempotency_key": request["steering_id"],
        "artifact_fingerprints": artifacts,
        "created_at": "2026-08-16T00:00:00+02:00",
        "payload": request,
    }


def _fixture_safe(*, drift: bool = False, write_tx: bool = False, kind: str = "between_operations") -> dict[str, Any]:
    return {
        "schema": SAFE_POINT_SCHEMA,
        "resource_id": "BOOK-STEER",
        "session_id": "SES-MANAGER",
        "run_id": "RUN-1",
        "checkpoint_id": "CP-8",
        "safe_point_id": "SAFE-8",
        "safe_point_kind": kind,
        "artifact_fingerprints": ["sha256:" + ("c" if drift else "a") * 64],
        "context_manifest_fingerprint": "sha256:" + ("d" if drift else "b") * 64,
        "session_payload_hash": "sha256:" + "e" * 64,
        "pending_handoffs": [{"handoff_id": "HO-REVIEW-1", "artifact_fingerprints": ["sha256:" + "a" * 64]}],
        "in_consequential_write_transaction": write_tx,
        "authority": False,
    }


def _fixture_decision(event: dict[str, Any], safe: dict[str, Any], *, route: str = "regenerate", drift: bool = False) -> dict[str, Any]:
    invalidated = ["sha256:" + "a" * 64] if route != "continue" else []
    cancel = ["HO-REVIEW-1"] if invalidated else []
    return {
        "schema": DECISION_SCHEMA,
        "decision_id": "STEER-DECISION-1",
        "steering_event_id": event["event_id"],
        "steering_event_fingerprint": fingerprint(event),
        "session_id": "SES-MANAGER",
        "run_id": "RUN-1",
        "safe_point_fingerprint": fingerprint(safe),
        "route": route,
        "binding_mode": "drift_acknowledged" if drift else "exact",
        "authored_against_artifact_fingerprints": ["sha256:" + "a" * 64],
        "observed_current_artifact_fingerprints": safe["artifact_fingerprints"],
        "invalidate_artifact_fingerprints": invalidated,
        "cancel_handoff_ids": cancel,
        "rationale_ref": "manager:steering-impact-classification",
        "authority": False,
    }


def self_test(path: Path) -> dict[str, Any]:
    if path.exists():
        path.unlink()
    cp = control_plane.ControlPlane(path)
    cp.init()
    event = _fixture_event()
    valid_request = validate_request_event(event)
    first_ingest = ingest(cp, event)
    duplicate_ingest = ingest(cp, event)

    conflict = json.loads(json.dumps(event))
    conflict["payload"]["instruction"] = "Different instruction under same idempotency key."
    conflicting_delivery_blocked = False
    try:
        ingest(cp, conflict)
    except ValueError:
        conflicting_delivery_blocked = True

    future = _fixture_event(scope="future_only", timing="future_only", instruction="In CH-010, revisit the election promise.")
    ingest(cp, future)
    future_not_current = current_run_applicability(future, session_id="SES-MANAGER", run_id="RUN-1")

    safe = _fixture_safe()
    decision = _fixture_decision(event, safe)
    decision_validation = validate_decision(event, safe, decision)
    consumed = consume(cp, event, safe, decision)
    replay = consume(cp, event, safe, decision)

    changed_decision = json.loads(json.dumps(decision))
    changed_decision["decision_id"] = "STEER-DECISION-DIFFERENT"
    changed_decision["route"] = "replan"
    conflicting_replay_blocked = False
    try:
        consume(cp, event, safe, changed_decision)
    except ValueError:
        conflicting_replay_blocked = True

    drift_safe = _fixture_safe(drift=True)
    drift_bad = _fixture_decision(event, drift_safe, drift=False)
    drift_without_ack_blocked = not validate_decision(event, drift_safe, drift_bad)["valid"]
    drift_good = _fixture_decision(event, drift_safe, drift=True)
    drift_ack_allowed = validate_decision(event, drift_safe, drift_good)["valid"]

    write_safe = _fixture_safe(write_tx=True)
    write_decision = _fixture_decision(event, write_safe)
    write_transaction_blocked = not validate_decision(event, write_safe, write_decision)["valid"]

    before_review_event = _fixture_event(timing="before_review")
    before_review_event["event_id"] = before_review_event["payload"]["steering_id"] = "EV-BEFORE-REVIEW"
    before_review_event["idempotency_key"] = "EV-BEFORE-REVIEW"
    wrong_safe = _fixture_safe(kind="before_draft")
    wrong_timing_blocked = not validate_decision(before_review_event, wrong_safe, _fixture_decision(before_review_event, wrong_safe))["valid"]

    uncancelled = _fixture_decision(event, safe)
    uncancelled["cancel_handoff_ids"] = []
    stale_handoff_blocked = not validate_decision(event, safe, uncancelled)["valid"]

    wrong_run = json.loads(json.dumps(decision))
    wrong_run["run_id"] = "RUN-2"
    wrong_run_blocked = not validate_decision(event, safe, wrong_run)["valid"]

    checks = {
        "request_validation": valid_request["valid"],
        "control_plane_ingress_reused": first_ingest["duplicate"] is False and duplicate_ingest["duplicate"] is True,
        "conflicting_delivery_fails_closed": conflicting_delivery_blocked,
        "future_only_note_does_not_apply_to_current_run": future_not_current["applicable"] is False and future_not_current["reason"] == "future_only",
        "decision_binds_event_run_safe_point_and_artifacts": decision_validation["valid"],
        "consume_once": consumed["consumed"] is True and replay["already_consumed"] is True,
        "conflicting_replay_fails_closed": conflicting_replay_blocked,
        "drift_requires_explicit_acknowledgement": drift_without_ack_blocked and drift_ack_allowed,
        "consequential_write_transaction_not_interruptible": write_transaction_blocked,
        "requested_safe_point_timing_is_enforced": wrong_timing_blocked,
        "invalidated_candidate_requires_pending_handoff_cancellation": stale_handoff_blocked,
        "wrong_run_rebinding_fails_closed": wrong_run_blocked,
        "no_follow_up_side_effects_are_executed_here": consumed["follow_up_executed"] is False,
        "authority_is_always_false": all(
            x is False for x in [
                consumed["authority"], consumed["canon_authority"], consumed["framework_write_authority"],
                consumed["project_write_authority"], consumed["settlement_authority"], consumed["model_execution"],
            ]
        ),
    }
    ok = all(checks.values())
    return {
        "author_steering_contract": "PASS" if ok else "FAIL",
        "schema": REQUEST_SCHEMA,
        "transport_event_type": TRANSPORT_EVENT_TYPE,
        "routes": sorted(ROUTES),
        **checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge author steering runtime contract")
    parser.add_argument("--db", default=".novelforge/runtime.db")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    pv = sub.add_parser("validate-event"); pv.add_argument("--event", required=True)
    pi = sub.add_parser("ingest"); pi.add_argument("--event", required=True)
    pc = sub.add_parser("consume"); pc.add_argument("--event", required=True); pc.add_argument("--safe-point", required=True); pc.add_argument("--decision", required=True)
    args = parser.parse_args()
    try:
        if args.command == "self-test":
            with tempfile.TemporaryDirectory() as td:
                out = self_test(Path(td) / "runtime.db")
            dump(out)
            return 0 if out["author_steering_contract"] == "PASS" else 1
        if args.command == "validate-event":
            out = validate_request_event(load_object(Path(args.event)))
            dump(out)
            return 0 if out["valid"] else 1
        cp = control_plane.ControlPlane(args.db); cp.init()
        if args.command == "ingest":
            dump(ingest(cp, load_object(Path(args.event)))); return 0
        if args.command == "consume":
            dump(consume(cp, load_object(Path(args.event)), load_object(Path(args.safe_point)), load_object(Path(args.decision)))); return 0
    except Exception as exc:
        dump({"error": str(exc), "authority": False, "model_execution": False})
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
