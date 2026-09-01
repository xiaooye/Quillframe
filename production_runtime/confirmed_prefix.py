"""Core-owned recovery from a quiescent, confirmed production prefix.

The caller supplies identities and fingerprints only.  This module re-reads
the original immutable journal, validates the exact repair candidate and
terminal syntax failure, and freezes references for a fresh run.  Historical
AgentJob/AgentResult rows are never copied into the new run or charged again.
"""
from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

from harness.context_runtime import fingerprint
from harness.semantic_workers.registered_contract_binding import validate_registered_job
from harness.semantic_workers.semantic_worker_router import validate_result
from persistence.quillframe_sqlite import canonical_json, fingerprint_text
from quality.author_objective_gate import validate_author_objectives

from .contracts import ProductionRunError, parse_json_object, validate_bundle_integrity
from .craft_guidance import validate_craft_snapshot
from .reading_positioning import build_reading_positioning, reading_positioning_fields
from .semantic import semantic_status


SCHEMA = "quillframe_production_confirmed_prefix_source_v1"
REUSE_SCHEMA = "quillframe_production_confirmed_prefix_reuse_v1"
REFERENCE_KEYS = {
    "source_run_id",
    "terminal_call_id",
    "expected_candidate_fingerprint",
    "expected_prefix_fingerprint",
}
PREFIX_ROLES = (
    "registered_repair_editor",
    "surface_realization",
    "registered_reader_engagement",
    "continuity",
)
TERMINAL_ROLE = "registered_candidate_self_audit"
_FP = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _reject(message: str, *, code: str = "confirmed_prefix_invalid") -> None:
    raise ProductionRunError(code, message)


def _object(raw: Any, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        _reject(f"{label} is not valid persisted JSON")
    if not isinstance(value, dict) or canonical_json(value) != raw:
        _reject(f"{label} is not one canonical persisted object")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _FP.fullmatch(value):
        _reject(f"{label} must be one exact SHA-256 fingerprint")
    return value


def validate_reference(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != REFERENCE_KEYS:
        _reject("confirmed_prefix_source requires only its four exact identity fields")
    result: dict[str, str] = {}
    for key in ("source_run_id", "terminal_call_id"):
        item = value.get(key)
        if (not isinstance(item, str) or not item or item != item.strip()
                or len(item) > 512 or any(ord(char) < 32 for char in item)):
            _reject("confirmed prefix identity is invalid")
        result[key] = item
    for key in ("expected_candidate_fingerprint", "expected_prefix_fingerprint"):
        result[key] = _sha(value.get(key), key)
    return result


def _target(value: Any) -> dict[str, Any]:
    from .repair_source import _target as repair_target

    return repair_target(value)


def _unique_checkpoint(conn, run_id: str, kind: str, label: str) -> dict[str, Any]:  # noqa: ANN001
    rows = [dict(row) for row in conn.execute(
        "SELECT checkpoint_id,state_json,artifact_fingerprint FROM checkpoints "
        "WHERE run_id=? AND checkpoint_kind=? ORDER BY rowid",
        (run_id, kind),
    )]
    if not rows:
        _reject(f"{label} checkpoint is missing")
    variants = {(row["state_json"], row["artifact_fingerprint"]) for row in rows}
    if len(variants) != 1:
        _reject(f"{label} checkpoints conflict")
    row = rows[0]
    row["state"] = _object(row["state_json"], label)
    return row


def context_compatibility_projection(bundle: dict[str, Any]) -> dict[str, Any]:
    """Project cross-run-equivalent Context without run-scoped identities."""
    validate_bundle_integrity(bundle)
    freeze = bundle["freeze"]
    greenlights = freeze.get("stage_greenlights")
    if not isinstance(greenlights, dict):
        _reject("confirmed prefix Context freeze has no stage Greenlights")
    stages: dict[str, Any] = {}
    for stage_id, greenlight in sorted(greenlights.items()):
        if not isinstance(greenlight, dict) or not isinstance(greenlight.get("selected"), list):
            _reject("confirmed prefix Context Greenlight is malformed")
        stages[str(stage_id)] = {
            "hard_budget": greenlight.get("hard_budget"),
            "selected": [
                {
                    key: deepcopy(item.get(key))
                    for key in (
                        "profile_id", "object_id", "source_fingerprint", "profile_fingerprint",
                        "pinned", "priority", "reason_code", "required_for_grounding",
                    )
                    if key in item
                }
                for item in greenlight["selected"]
                if isinstance(item, dict)
            ],
        }
    target = bundle.get("target_context") or {}
    author_model = target.get("author_model") if isinstance(target, dict) else {}
    return {
        "source_universe_fingerprint": bundle.get("source_universe_fingerprint"),
        "source_fingerprints": deepcopy(freeze.get("source_fingerprints")),
        "source_state_fingerprints": deepcopy(freeze.get("source_state_fingerprints")),
        "profile_fingerprints": deepcopy(freeze.get("profile_fingerprints")),
        "target": _target(target),
        "author_preferences": {
            key: deepcopy((author_model or {}).get(key))
            for key in ("selected_hypothesis_ids", "active_preferences")
        },
        "stages": stages,
    }


def context_compatibility_fingerprint(bundle: dict[str, Any]) -> str:
    return fingerprint(context_compatibility_projection(bundle))


def _registered_binding(call: tuple[dict[str, Any], dict[str, Any], dict[str, Any]], *,
                        contract_id: str, role: str) -> dict[str, Any]:
    row, agent_job, agent_result = call
    if row.get("runtime_role") != role:
        _reject(f"confirmed prefix expected {role}")
    context = agent_job.get("context")
    semantic_job = (
        context[0].get("registered_semantic_job")
        if isinstance(context, list) and len(context) == 1 and isinstance(context[0], dict)
        else None
    )
    if (not isinstance(semantic_job, dict) or validate_registered_job(semantic_job)
            or semantic_job.get("input", {}).get("model_contract_id") != contract_id):
        _reject(f"confirmed prefix {contract_id} job changed")
    judgment = parse_json_object(agent_result.get("final_text"), label=f"confirmed prefix {contract_id}")
    semantic_result = {
        "job_id": semantic_job["job_id"],
        "subject_id": semantic_job["subject_id"],
        "kind": semantic_job["kind"],
        "input_fingerprint": semantic_job["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": "quillframe_model_service",
            "model_or_reviewer": agent_result.get("model_id"),
            "model_service_id": agent_result.get("model_service_id"),
            "protocol": agent_result.get("protocol"),
            "model_version_fingerprint": agent_result.get("model_version_fingerprint"),
            "agent_job_id": agent_job.get("job_id"),
            "agent_input_fingerprint": agent_job.get("input_fingerprint"),
        },
        "judgment": judgment,
        "proposals": [],
        "errors": [],
        "execution": {
            "source_session_id": semantic_job.get("execution", {}).get("source_session_id"),
            "handoff_id": semantic_job.get("execution", {}).get("handoff_id"),
        },
    }
    errors = validate_result(semantic_job, semantic_result)
    if errors:
        _reject(f"confirmed prefix {contract_id} result changed")
    return {
        "contract_id": contract_id,
        "job": semantic_job,
        "result": semantic_result,
        "binding_fingerprint": fingerprint({"job": semantic_job, "result": semantic_result}),
        "authority": False,
    }


def _call_ref(call: tuple[dict[str, Any], dict[str, Any], dict[str, Any]], ordinal: int) -> dict[str, Any]:
    row, _job, _result = call
    return {
        "ordinal": ordinal,
        "call_id": row["call_id"],
        "stage_key": row["stage_key"],
        "runtime_role": row["runtime_role"],
        "input_fingerprint": row["input_fingerprint"],
        "result_fingerprint": row["result_fingerprint"],
    }


def _stage_receipts(conn, run_id: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:  # noqa: ANN001
    by_mechanism: dict[str, dict[str, Any]] = {}
    refs: list[dict[str, Any]] = []
    for raw in conn.execute(
        "SELECT receipt_id,payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage' ORDER BY rowid",
        (run_id,),
    ):
        receipt = _object(raw["payload_json"], "confirmed prefix stage receipt")
        mechanism = receipt.get("mechanism")
        if mechanism in by_mechanism or mechanism not in {"surface_realization", "reader_engagement", "continuity"}:
            _reject("confirmed prefix has an unexpected or duplicate stage receipt")
        expected = fingerprint({key: value for key, value in receipt.items() if key != "stage_result_fingerprint"})
        if receipt.get("stage_result_fingerprint") != expected:
            _reject("confirmed prefix stage receipt fingerprint changed")
        by_mechanism[str(mechanism)] = receipt
        refs.append({
            "receipt_id": raw["receipt_id"],
            "mechanism": mechanism,
            "stage_result_fingerprint": expected,
            "payload_fingerprint": fingerprint_text(raw["payload_json"]),
        })
    if set(by_mechanism) != {"surface_realization", "reader_engagement", "continuity"}:
        _reject("confirmed prefix requires exact surface, Reader and continuity receipts")
    return by_mechanism, refs


def _derive(conn, source_run_id: str) -> tuple[dict[str, Any], dict[str, Any]]:  # noqa: ANN001
    from . import repair_source as source

    row = conn.execute("SELECT * FROM runs WHERE run_id=?", (source_run_id,)).fetchone()
    if row is None:
        _reject("confirmed prefix source run does not exist", code="confirmed_prefix_not_found")
    run = dict(row)
    if run.get("task_mode") != "REVISE" or run.get("status") != "semantic_pending":
        _reject("confirmed prefix requires one quiescent semantic-pending REVISE run")
    execution_row = conn.execute(
        "SELECT * FROM production_executions WHERE run_id=?", (source_run_id,),
    ).fetchone()
    if execution_row is None or execution_row["cancel_requested"]:
        _reject("confirmed prefix source execution is missing or cancelled")
    if execution_row["owner_token"] and (execution_row["lease_expires_at_ms"] or 0) > int(time.time() * 1000):
        _reject("confirmed prefix source still has an active executor")
    request = _object(execution_row["request_json"], "confirmed prefix execution request")
    if fingerprint(request) != execution_row["request_fingerprint"]:
        _reject("confirmed prefix execution request fingerprint changed")
    source_target, author_request_fp = source._author_request(conn, run)
    repair = source.load_repair_source(conn, source_run_id, _recorded=True)
    calls, _native_journal_fp = source._confirmed_calls(conn, run, request)
    if tuple(row[0]["runtime_role"] for row in calls) != PREFIX_ROLES + (TERMINAL_ROLE,):
        _reject("confirmed prefix call graph is not the exact closed recovery topology")

    if conn.execute("SELECT 1 FROM candidates WHERE run_id=? LIMIT 1", (source_run_id,)).fetchone():
        _reject("confirmed prefix source already has a visible candidate")
    forbidden = conn.execute(
        "SELECT checkpoint_kind FROM checkpoints WHERE run_id=? AND checkpoint_kind IN "
        "('production_qualified_candidate','production_independent_handoff','production_narrative_proposal') LIMIT 1",
        (source_run_id,),
    ).fetchone()
    if forbidden:
        _reject("confirmed prefix source advanced past its terminal self-audit failure")
    if conn.execute(
        "SELECT 1 FROM receipts WHERE run_id=? AND receipt_kind='production_release' LIMIT 1",
        (source_run_id,),
    ).fetchone():
        _reject("confirmed prefix source already has release evidence")

    context_row = _unique_checkpoint(conn, source_run_id, "production_context_bundle", "confirmed prefix Context")
    bundle = context_row["state"]
    validate_bundle_integrity(bundle)
    if (bundle.get("run_id") != source_run_id
            or bundle.get("target_context") != source_target
            or context_row["artifact_fingerprint"] != bundle.get("bundle_fingerprint")):
        _reject("confirmed prefix Context binding changed")

    plan_row = _unique_checkpoint(conn, source_run_id, "production_repair_plan", "confirmed prefix repair plan")
    plan_state = plan_row["state"]
    plan = plan_state.get("generation_plan")
    editor_binding = plan_state.get("editor_binding")
    if (not isinstance(plan, dict) or not isinstance(editor_binding, dict)
            or plan_row["artifact_fingerprint"] != fingerprint(plan)
            or editor_binding.get("binding_fingerprint") != fingerprint({
                "job": editor_binding.get("job"), "result": editor_binding.get("result"),
            })):
        _reject("confirmed prefix repair plan changed")
    source._registered_call(
        editor_binding.get("job"), editor_binding.get("result"),
        role="registered_repair_editor", calls=calls, recorded=True,
    )

    reuse_row = _unique_checkpoint(
        conn, source_run_id, "production_local_revision_reuse", "confirmed prefix local revision reuse",
    )
    reuse = reuse_row["state"]
    if (reuse.get("schema") != "quillframe_local_author_revision_reuse_v1"
            or reuse.get("source_context_exact") is not True
            or reuse.get("source_candidate_fingerprint") != repair.get("candidate_fingerprint")
            or reuse.get("reuse_fingerprint") != fingerprint({
                key: value for key, value in reuse.items() if key != "reuse_fingerprint"
            })
            or reuse_row["artifact_fingerprint"] != reuse.get("reuse_fingerprint")):
        _reject("confirmed prefix local revision reuse changed")

    reader_binding = _registered_binding(
        calls[2], contract_id="reader.engagement_audit", role="registered_reader_engagement",
    )
    reader_payload = reader_binding["job"]["input"]["payload"]
    text = reader_payload.get("candidate_text")
    candidate_fp = reader_payload.get("candidate_fingerprint")
    if (not isinstance(text, str) or not text.strip()
            or candidate_fp != fingerprint_text(text)
            or semantic_status(reader_binding) != "pass"):
        _reject("confirmed prefix Reader does not pass the exact candidate")

    surface_job, surface_result = calls[1][1], calls[1][2]
    surface = parse_json_object(surface_result.get("final_text"), label="confirmed prefix surface realization")
    if surface.get("status") == "pass" and surface.get("text") != text:
        surface = source._validated_derived_surface(conn, calls, surface, text)
    if surface.get("status") != "pass" or surface.get("text") != text:
        _reject("confirmed prefix surface realization did not pass")
    surface_context = surface_job.get("context")
    writer_pack = (
        surface_context[0].get("writer_pack")
        if isinstance(surface_context, list) and len(surface_context) == 1 and isinstance(surface_context[0], dict)
        else None
    )
    from .repair import (
        author_objective_projection,
        writer_context as materialize_repair_context,
    )
    expected_repair_context = materialize_repair_context(repair, plan, {})
    expected_author_objectives = author_objective_projection(
        repair["source_request"]["instruction"], plan,
    )
    try:
        writer_author_objectives = validate_author_objectives(
            writer_pack.get("author_objectives") if isinstance(writer_pack, dict) else None,
        )
    except ValueError:
        _reject("confirmed prefix Surface Writer author objectives are invalid")
    if (
        not isinstance(writer_pack, dict)
        or writer_pack.get("writer_pack_fingerprint") != fingerprint({
            key: value for key, value in writer_pack.items() if key != "writer_pack_fingerprint"
        })
        or writer_pack.get("repair_context") != expected_repair_context
        or writer_author_objectives != expected_author_objectives
    ):
        _reject("confirmed prefix Surface Writer changed its exact bounded repair context or author objectives")

    continuity_job, continuity_result = calls[3][1], calls[3][2]
    continuity = parse_json_object(continuity_result.get("final_text"), label="confirmed prefix continuity")
    continuity_context = continuity_job.get("context")
    continuity_candidate = (
        continuity_context[0].get("upstream_artifacts", {}).get("candidate")
        if isinstance(continuity_context, list) and len(continuity_context) == 1 and isinstance(continuity_context[0], dict)
        else None
    )
    if (continuity.get("status") != "pass"
            or continuity_candidate != {"text": text, "artifact_fingerprint": candidate_fp}):
        _reject("confirmed prefix continuity does not pass the exact candidate")

    terminal_row, terminal_job, terminal_result = calls[4]
    terminal_context = terminal_job.get("context")
    terminal_semantic = (
        terminal_context[0].get("registered_semantic_job")
        if isinstance(terminal_context, list) and len(terminal_context) == 1 and isinstance(terminal_context[0], dict)
        else None
    )
    terminal_payload = terminal_semantic.get("input", {}).get("payload", {}) if isinstance(terminal_semantic, dict) else {}
    if (not isinstance(terminal_semantic, dict) or validate_registered_job(terminal_semantic)
            or terminal_semantic.get("input", {}).get("model_contract_id") != "quality.candidate_self_audit"
            or terminal_payload.get("candidate_fingerprint") != candidate_fp
            or terminal_payload.get("candidate_text") != text
            or terminal_payload.get("author_objectives") != expected_author_objectives):
        _reject("confirmed prefix terminal self-audit changed its candidate or author-objective binding")
    try:
        json.loads(terminal_result.get("final_text"))
    except (TypeError, json.JSONDecodeError):
        pass
    else:
        _reject("confirmed prefix terminal result is not a JSON syntax failure")

    failures = []
    for event in conn.execute(
        "SELECT event_id,payload_json FROM runtime_events WHERE run_id=? AND event_kind='production_stage_failed' ORDER BY rowid",
        (source_run_id,),
    ):
        payload = _object(event["payload_json"], "confirmed prefix failure event")
        if payload.get("call_id") == terminal_row["call_id"]:
            failures.append((event["event_id"], payload))
    if len(failures) != 1:
        _reject("confirmed prefix requires one exact terminal failure event")
    failure_id, failure = failures[0]
    if (failure.get("code") != "semantic_output_invalid"
            or failure.get("result_fingerprint") != terminal_row["result_fingerprint"]
            or failure.get("automatic_model_retry") is not False):
        _reject("confirmed prefix terminal failure evidence changed")

    receipts, receipt_refs = _stage_receipts(conn, source_run_id)
    call_by_mechanism = {
        "surface_realization": calls[1],
        "reader_engagement": calls[2],
        "continuity": calls[3],
    }
    for mechanism, receipt in receipts.items():
        call = call_by_mechanism[mechanism]
        expected_input_fingerprint = (
            reader_binding["job"]["input_fingerprint"]
            if mechanism == "reader_engagement"
            else call[1]["input_fingerprint"]
        )
        if (receipt.get("context_bundle_fingerprint") != bundle["bundle_fingerprint"]
                or receipt.get("freeze_fingerprint") != bundle["freeze"]["freeze_fingerprint"]
                or receipt.get("agent_input_fingerprint") != expected_input_fingerprint
                or receipt.get("judgment", {}).get("status") != "pass"
                or (mechanism in {"surface_realization", "reader_engagement"}
                    and receipt.get("judgment", {}).get("artifact_fingerprint") != candidate_fp)):
            _reject("confirmed prefix stage receipt changed its candidate or Context binding")

    positioning = build_reading_positioning(
        target_context=source_target,
        reader_grip=request.get("reader_grip"),
        execution_request_fingerprint=execution_row["request_fingerprint"],
    )
    expected_reader_fields = reading_positioning_fields(
        positioning,
        target_context=source_target,
        reader_grip=request.get("reader_grip"),
        execution_request_fingerprint=execution_row["request_fingerprint"],
    )
    if any(reader_payload.get(key) != value for key, value in expected_reader_fields.items()):
        _reject("confirmed prefix Reader positioning changed")
    if reader_payload.get("reader_visible_context") != request.get("reader_visible_context", []):
        _reject("confirmed prefix Reader-visible history changed")

    craft = request.get("craft_guidance")
    validate_craft_snapshot(craft)
    state = {
        "schema": SCHEMA,
        "source_run_id": source_run_id,
        "source_run_fingerprint": fingerprint(run),
        "source_execution_request_fingerprint": execution_row["request_fingerprint"],
        "source_author_request_fingerprint": author_request_fp,
        "source_repair_source_fingerprint": repair["source_fingerprint"],
        "source_context": {
            "checkpoint_id": context_row["checkpoint_id"],
            "bundle_fingerprint": bundle["bundle_fingerprint"],
            "state_fingerprint": fingerprint_text(context_row["state_json"]),
            "compatibility_fingerprint": context_compatibility_fingerprint(bundle),
        },
        "source_craft_snapshot_fingerprint": craft["snapshot_fingerprint"],
        "source_repair_plan": {
            "artifact_fingerprint": plan_row["artifact_fingerprint"],
            "state_fingerprint": fingerprint_text(plan_row["state_json"]),
            "editor_binding_fingerprint": editor_binding["binding_fingerprint"],
        },
        "source_local_revision_reuse_fingerprint": reuse["reuse_fingerprint"],
        "source_author_objectives_fingerprint": expected_author_objectives["objectives_fingerprint"],
        "candidate_fingerprint": candidate_fp,
        "ordered_call_refs": [_call_ref(call, index + 1) for index, call in enumerate(calls[:4])],
        "source_stage_receipts": receipt_refs,
        "terminal_failure": {
            "event_id": failure_id,
            "call_id": terminal_row["call_id"],
            "result_fingerprint": terminal_row["result_fingerprint"],
            "code": "semantic_output_invalid",
            "failure_class": "json_syntax_invalid",
        },
        "next_contract_id": "quality.candidate_self_audit",
        "authority": False,
    }
    state["prefix_fingerprint"] = fingerprint(state)
    private = {
        "run": run,
        "request": request,
        "target": source_target,
        "repair_source": repair,
        "bundle": bundle,
        "repair_plan_state": plan_state,
        "local_revision_reuse": reuse,
        "calls": calls,
        "surface_text": text,
        "author_objectives": deepcopy(expected_author_objectives),
        "reader_binding": reader_binding,
        "continuity_result": continuity,
        "stage_receipts": receipts,
        "reading_positioning": positioning,
    }
    return state, private


def build_reference(conn, source_run_id: str) -> dict[str, str]:  # noqa: ANN001
    state, _private = _derive(conn, source_run_id)
    return {
        "source_run_id": source_run_id,
        "terminal_call_id": state["terminal_failure"]["call_id"],
        "expected_candidate_fingerprint": state["candidate_fingerprint"],
        "expected_prefix_fingerprint": state["prefix_fingerprint"],
    }


def freeze_confirmed_prefix(
    conn, *, reference: Any, target: dict[str, Any], repair_source: dict[str, Any],  # noqa: ANN001
    authorization_receipt_fingerprint: str,
) -> dict[str, Any]:
    ref = validate_reference(reference)
    state, _private = _derive(conn, ref["source_run_id"])
    if (_target(target) != _target(_private["target"])
            or repair_source.get("source_fingerprint") != state["source_repair_source_fingerprint"]):
        _reject("confirmed prefix belongs to another target or repair source")
    if (ref["terminal_call_id"] != state["terminal_failure"]["call_id"]
            or ref["expected_candidate_fingerprint"] != state["candidate_fingerprint"]
            or ref["expected_prefix_fingerprint"] != state["prefix_fingerprint"]):
        _reject("confirmed prefix reference does not match Core evidence")
    frozen = {
        **state,
        "authorization_receipt_fingerprint": _sha(
            authorization_receipt_fingerprint, "authorization_receipt_fingerprint",
        ),
    }
    frozen["checkpoint_fingerprint"] = fingerprint(frozen)
    return frozen


def _stored_repair_source(conn, run_id: str) -> dict[str, Any]:  # noqa: ANN001
    row = _unique_checkpoint(conn, run_id, "production_repair_source", "recovery repair source")
    value = row["state"]
    if (value.get("source_fingerprint") != fingerprint({
            key: item for key, item in value.items() if key != "source_fingerprint"
    }) or row["artifact_fingerprint"] != value.get("source_fingerprint")):
        _reject("recovery repair source checkpoint changed")
    return value


def load_confirmed_prefix(
    conn, run_id: str, *, target: dict[str, Any], repair_source: dict[str, Any] | None = None,  # noqa: ANN001
) -> tuple[dict[str, Any], dict[str, Any]]:
    ref = (target.get("payload") or {}).get("confirmed_prefix_source") if isinstance(target, dict) else None
    if ref is None:
        _reject("run has no confirmed prefix source", code="confirmed_prefix_missing")
    reference = validate_reference(ref)
    row = _unique_checkpoint(
        conn, run_id, "production_confirmed_prefix_source", "confirmed prefix source",
    )
    frozen = row["state"]
    if (frozen.get("schema") != SCHEMA
            or frozen.get("checkpoint_fingerprint") != fingerprint({
                key: value for key, value in frozen.items() if key != "checkpoint_fingerprint"
            })
            or row["artifact_fingerprint"] != frozen.get("checkpoint_fingerprint")):
        _reject("confirmed prefix source checkpoint changed")
    auth_rows = [dict(item) for item in conn.execute(
        "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='confirmed_prefix_recovery_authorization'",
        (run_id,),
    )]
    if len(auth_rows) != 1:
        _reject("confirmed prefix recovery authorization receipt is missing")
    authorization = _object(auth_rows[0]["payload_json"], "confirmed prefix authorization receipt")
    auth_fp = authorization.get("receipt_fingerprint")
    if (auth_fp != fingerprint({key: value for key, value in authorization.items() if key != "receipt_fingerprint"})
            or authorization.get("run_id") != run_id
            or authorization.get("prefix_fingerprint") != reference["expected_prefix_fingerprint"]
            or auth_fp != frozen.get("authorization_receipt_fingerprint")):
        _reject("confirmed prefix recovery authorization changed")
    actual_repair = repair_source or _stored_repair_source(conn, run_id)
    expected = freeze_confirmed_prefix(
        conn,
        reference=reference,
        target=target,
        repair_source=actual_repair,
        authorization_receipt_fingerprint=auth_fp,
    )
    if expected != frozen:
        _reject("confirmed prefix source changed after registration")
    _state, private = _derive(conn, reference["source_run_id"])
    return frozen, private


def logical_journal_fingerprint(native_journal_fingerprint: str, frozen: dict[str, Any],
                                reuse_receipts: list[dict[str, Any]]) -> str:
    return fingerprint({
        "native_journal_fingerprint": native_journal_fingerprint,
        "confirmed_prefix_fingerprint": frozen["prefix_fingerprint"],
        "stage_reuse_receipt_fingerprints": [
            receipt["stage_result_fingerprint"] for receipt in reuse_receipts
        ],
    })
