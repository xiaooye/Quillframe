"""Core-owned, immutable evidence for repairing an internal rejected candidate.

Only exact references cross the authoring boundary. This module reads the native
Project database, verifies the original confirmed calls, and returns private
evidence. It never revises a source run, judges prose, or grants release authority.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from harness.context_runtime import fingerprint
from harness.semantic_workers.registered_contract_binding import validate_registered_job, validate_recorded_registered_job
from harness.semantic_workers.semantic_worker_router import validate_result, worker_job_view
from persistence.quillframe_sqlite import canonical_json, fingerprint_text
from quality.candidate_qualification import validate_qualification_receipt

from .contracts import ProductionRunError, assert_secret_free, parse_json_object, validate_bundle_integrity
from .semantic import build_pre_independent_qualification

SCHEMA = "quillframe_production_repair_source_v1"
REFERENCE_KEYS = {"source_run_id", "source_checkpoint_id", "expected_candidate_fingerprint"}
AUTHOR_REFERENCE_KEYS = {"source_candidate_id", "revision_request_id", "expected_candidate_fingerprint"}
TARGET_KEYS = ("chapter_id", "document_id", "current_story_order", "current_reading_order")


def _reject(message: str, *, code: str = "repair_source_invalid") -> None:
    raise ProductionRunError(code, message)


def _object(raw: Any, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ProductionRunError("repair_source_invalid", f"{label} is not valid persisted JSON") from exc
    if not isinstance(value, dict) or canonical_json(value) != raw:
        _reject(f"{label} is not a canonical persisted object")
    return value


def _reference(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) not in (REFERENCE_KEYS, AUTHOR_REFERENCE_KEYS):
        _reject("repair_source requires only the three exact source references")
    for key in set(value) - {"expected_candidate_fingerprint"}:
        item = value[key]
        if not isinstance(item, str) or not item or item != item.strip() or len(item) > 512 or any(ord(c) < 32 for c in item):
            _reject("repair_source identity is invalid")
    if not isinstance(value["expected_candidate_fingerprint"], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value["expected_candidate_fingerprint"]):
        _reject("repair_source requires the exact candidate SHA-256")
    assert_secret_free(value, label="repair source reference")
    return dict(value)


def _target(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        _reject("repair source requires an exact chapter/document target")
    for key in TARGET_KEYS[:2]:
        if not isinstance(value.get(key), str) or not value[key].strip():
            _reject("repair source target identity is invalid")
    for key in TARGET_KEYS[2:]:
        if type(value.get(key)) is not int or value[key] < 0:
            _reject("repair source target orders are invalid")
    return {key: value[key] for key in TARGET_KEYS}


def _author_request(conn, run: dict[str, Any]) -> tuple[dict[str, Any], str]:
    rows = conn.execute(
        "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE run_id=? AND checkpoint_kind='author_run_request'",
        (run["run_id"],),
    ).fetchall()
    if len(rows) != 1:
        _reject("repair source requires one immutable author request")
    row = rows[0]
    request = _object(row["state_json"], "author request")
    if request.get("schema") != "quillframe_author_run_request_v1" or fingerprint(request) != row["artifact_fingerprint"]:
        _reject("repair source author request fingerprint is invalid")
    if request.get("task_mode") != run["task_mode"] or request.get("target_ref") != run["target_ref"] or not isinstance(request.get("payload"), dict):
        _reject("repair source author request changed its run binding")
    _target(request)
    return request, row["artifact_fingerprint"]


def _confirmed_calls(conn, run: dict[str, Any], request: dict[str, Any]) -> tuple[list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]], str]:
    rows = [dict(row) for row in conn.execute(
        "SELECT * FROM production_stage_calls WHERE run_id=? ORDER BY rowid", (run["run_id"],)
    )]
    if not rows or any(row["state"] != "confirmed" for row in rows):
        _reject("repair source has missing or unconfirmed model calls", code="repair_source_unconfirmed")
    calls = []
    for row in rows:
        job = _object(row["job_json"], "confirmed AgentJob")
        result = _object(row["result_json"], "confirmed AgentResult")
        if job.get("schema") != "quillframe_agent_job_v1" or job.get("input_fingerprint") != row["input_fingerprint"] or fingerprint({key: value for key, value in job.items() if key != "input_fingerprint"}) != row["input_fingerprint"]:
            _reject("repair source confirmed AgentJob fingerprint is invalid")
        if any(job.get(key) != run[key] for key in ("run_id", "session_id", "task_mode")) or job.get("runtime_role") != row["runtime_role"] or job.get("service_id") != request.get("service_id"):
            _reject("repair source confirmed AgentJob identity is invalid")
        if result.get("schema") != "quillframe_agent_result_v1" or fingerprint(result) != row["result_fingerprint"] or result.get("status") != "completed":
            _reject("repair source confirmed AgentResult is invalid")
        if any(result.get(key) != job.get(key) for key in ("job_id", "session_id", "run_id", "input_fingerprint")) or result.get("model_service_id") != job.get("service_id"):
            _reject("repair source confirmed AgentResult changed its job binding")
        calls.append((row, job, result))
    return calls, fingerprint(rows)


def _call_for_role(calls, role: str):
    found = [(job, result) for row, job, result in calls if row["runtime_role"] == role]
    if len(found) != 1:
        _reject("repair source requires one exact confirmed call for each candidate gate")
    return found[0]


def _validated_derived_surface(conn, calls, raw_surface: dict[str, Any], text: str) -> dict[str, Any]:  # noqa: ANN001
    """Verify Core's checkpointed bounded-edit materialization, not model prose claims."""

    found = [(row, result) for row, _job, result in calls if row["runtime_role"] == "surface_realization"]
    if len(found) != 1:
        _reject("repair source requires one exact Surface Writer call")
    row, _result = found[0]
    checkpoint_row = conn.execute(
        "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE checkpoint_id=? "
        "AND run_id=? AND checkpoint_kind='production_node_checkpoint'",
        ("node:" + row["call_id"], row["run_id"]),
    ).fetchone()
    if checkpoint_row is None:
        _reject("repair source Surface Writer checkpoint is missing")
    checkpoint = _object(checkpoint_row["state_json"], "Surface Writer node checkpoint")
    supplied = checkpoint.get("checkpoint_fingerprint")
    if (
        supplied != fingerprint({key: value for key, value in checkpoint.items() if key != "checkpoint_fingerprint"})
        or checkpoint_row["artifact_fingerprint"] != supplied
        or checkpoint.get("input_fingerprint") != row["input_fingerprint"]
        or checkpoint.get("output_fingerprint") != row["result_fingerprint"]
    ):
        _reject("repair source Surface Writer checkpoint binding changed")
    derived = {**raw_surface, "text": text, "artifact_fingerprint": fingerprint_text(text)}
    validation = checkpoint.get("validation_receipt")
    if (
        not isinstance(validation, dict)
        or validation.get("status") != "semantic_validation_confirmed"
        or validation.get("validation_kind") != "production_stage:surface_realization"
        or validation.get("validation_fingerprint") != fingerprint(derived)
    ):
        _reject("repair source bounded Writer materialization is not checkpoint-confirmed")
    return derived


def _registered_call(job, result, *, role: str, calls, recorded: bool = False) -> None:
    if not isinstance(job, dict) or not isinstance(result, dict):
        _reject("repair source registered job/result are missing")
    validator = validate_recorded_registered_job if recorded else validate_registered_job
    if validator(job) or validate_result(job, result) or result.get("status") != "completed":
        _reject("repair source registered contract validation failed")
    agent_job, agent_result = _call_for_role(calls, role)
    if agent_job.get("context") != [{"registered_semantic_job": worker_job_view(job)}]:
        _reject("repair source registered job differs from its confirmed input")
    expected_worker = {
        "provider": "quillframe_model_service", "model_or_reviewer": agent_result.get("model_id"),
        "model_service_id": agent_result.get("model_service_id"), "protocol": agent_result.get("protocol"),
        "model_version_fingerprint": agent_result.get("model_version_fingerprint"),
        "agent_job_id": agent_job.get("job_id"), "agent_input_fingerprint": agent_job.get("input_fingerprint"),
    }
    if result.get("worker") != expected_worker or result.get("judgment") != parse_json_object(agent_result.get("final_text"), label="repair source confirmed judgment"):
        _reject(f"repair source {role} registered result differs from its confirmed response")
    if result.get("proposals") != [] or result.get("errors") != [] or result.get("execution") != {
        "source_session_id": job.get("execution", {}).get("source_session_id"),
        "handoff_id": job.get("execution", {}).get("handoff_id"),
    }:
        _reject("repair source registered result lineage is invalid")


def _registered_binding(binding: Any, *, contract_id: str, role: str, calls, candidate: str, text: str, subject: str, recorded: bool = False) -> None:
    if not isinstance(binding, dict) or binding.get("contract_id") != contract_id or binding.get("authority") is not False:
        _reject("repair source registered binding is missing or invalid")
    job, result = binding.get("job"), binding.get("result")
    _registered_call(job, result, role=role, calls=calls, recorded=recorded)
    if binding.get("binding_fingerprint") != fingerprint({"job": job, "result": result}):
        _reject("repair source registered binding fingerprint is invalid")
    payload = job.get("input", {}).get("payload", {})
    if job.get("input", {}).get("model_contract_id") != contract_id or job.get("subject_id") != subject or payload.get("candidate_fingerprint") != candidate or payload.get("candidate_text") != text:
        _reject("repair source registered gate does not bind the exact candidate")


def _confirmed_prefix_evidence(conn, run, request, state) -> dict[str, Any] | None:  # noqa: ANN001
    target, _target_fp = _author_request(conn, run)
    reference = (target.get("payload") or {}).get("confirmed_prefix_source")
    if reference is None:
        return None
    from .confirmed_prefix import (
        REUSE_SCHEMA,
        load_confirmed_prefix,
        logical_journal_fingerprint,
    )

    frozen, private = load_confirmed_prefix(conn, run["run_id"], target=target)
    if request.get("confirmed_prefix_fingerprint") != frozen["prefix_fingerprint"]:
        _reject("repair source execution lost its confirmed prefix binding")
    rows = conn.execute(
        "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE run_id=? "
        "AND checkpoint_kind='production_confirmed_prefix_reuse' ORDER BY rowid",
        (run["run_id"],),
    ).fetchall()
    if len(rows) != 1:
        _reject("repair source requires one confirmed prefix reuse checkpoint")
    reuse = _object(rows[0]["state_json"], "confirmed prefix reuse")
    expected_reuse = fingerprint({key: value for key, value in reuse.items() if key != "reuse_fingerprint"})
    if (reuse.get("schema") != REUSE_SCHEMA
            or reuse.get("run_id") != run["run_id"]
            or reuse.get("source_prefix_fingerprint") != frozen["prefix_fingerprint"]
            or reuse.get("candidate_fingerprint") != state.get("candidate_fingerprint")
            or reuse.get("current_context_bundle_fingerprint") != state.get("context_bundle_fingerprint")
            or reuse.get("current_freeze_fingerprint") != state.get("freeze_fingerprint")
            or reuse.get("reuse_fingerprint") != expected_reuse
            or rows[0]["artifact_fingerprint"] != expected_reuse):
        _reject("repair source confirmed prefix reuse changed")
    reuse_receipts = []
    for row in conn.execute(
        "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage' ORDER BY rowid",
        (run["run_id"],),
    ):
        receipt = _object(row["payload_json"], "confirmed prefix reuse receipt")
        if receipt.get("evidence_kind") == "confirmed_prefix_reuse":
            reuse_receipts.append(receipt)
    if ([item.get("mechanism") for item in reuse_receipts]
            != ["surface_realization", "reader_engagement", "continuity"]
            or [item.get("stage_result_fingerprint") for item in reuse_receipts]
            != reuse.get("stage_reuse_receipt_fingerprints")):
        _reject("repair source confirmed prefix stage receipts changed")
    for receipt in reuse_receipts:
        expected = fingerprint({key: value for key, value in receipt.items() if key != "stage_result_fingerprint"})
        if (receipt.get("stage_result_fingerprint") != expected
                or receipt.get("confirmed_prefix_fingerprint") != frozen["prefix_fingerprint"]
                or receipt.get("source_run_id") != frozen["source_run_id"]
                or receipt.get("current_run_model_invoked") is not False
                or receipt.get("source_model_invocation_referenced") is not True):
            _reject("repair source confirmed prefix receipt binding changed")
    return {
        "frozen": frozen,
        "private": private,
        "reuse": reuse,
        "reuse_receipts": reuse_receipts,
        "logical_journal_fingerprint": lambda native: logical_journal_fingerprint(
            native, frozen, reuse_receipts,
        ),
    }


def _context_and_continuity(conn, run, state, target, calls, *,
                            confirmed_prefix: dict[str, Any] | None = None) -> tuple[str, str]:
    row = conn.execute(
        "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_context_bundle' ORDER BY created_at DESC,rowid DESC LIMIT 1",
        (run["run_id"],),
    ).fetchone()
    if row is None:
        _reject("repair source context bundle is missing")
    bundle = _object(row["state_json"], "source context bundle")
    validate_bundle_integrity(bundle)
    freeze = bundle.get("freeze")
    if bundle.get("run_id") != run["run_id"] or bundle.get("task_mode") != run["task_mode"] or bundle.get("target_context") != target:
        _reject("repair source context bundle changed its target")
    if row["artifact_fingerprint"] != state.get("context_bundle_fingerprint") or bundle.get("bundle_fingerprint") != state.get("context_bundle_fingerprint") or not isinstance(freeze, dict) or freeze.get("freeze_fingerprint") != state.get("freeze_fingerprint") or bundle.get("freeze_fingerprint") != state.get("freeze_fingerprint"):
        _reject("repair source candidate is not bound to its context freeze")
    greenlights = freeze.get("stage_greenlights")
    if not isinstance(greenlights, dict) or any(not isinstance(item, dict) for item in greenlights.values()):
        _reject("repair source context freeze is malformed")
    freeze_binding = {key: freeze.get(key) for key in (
        "run_id", "task_mode", "candidate_universes", "source_fingerprints",
        "source_state_fingerprints", "profile_fingerprints",
    )}
    freeze_binding["stage_selections"] = {stage: item.get("selection_fingerprint") for stage, item in greenlights.items()}
    if fingerprint(freeze_binding) != state["freeze_fingerprint"]:
        _reject("repair source context freeze fingerprint is invalid")
    receipts = []
    for item in conn.execute("SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage'", (run["run_id"],)):
        receipt = _object(item["payload_json"], "source stage receipt")
        if receipt.get("mechanism") == "continuity":
            receipts.append(receipt)
    if len(receipts) != 1:
        _reject("repair source requires its exact continuity receipt")
    receipt = receipts[0]
    receipt_fp = fingerprint({key: value for key, value in receipt.items() if key != "stage_result_fingerprint"})
    if confirmed_prefix is None:
        job, result = _call_for_role(calls, "continuity")
    else:
        source_call = confirmed_prefix["private"]["calls"][3]
        source_row, job, result = source_call
        if (receipt.get("evidence_kind") != "confirmed_prefix_reuse"
                or receipt.get("confirmed_prefix_fingerprint")
                    != confirmed_prefix["frozen"]["prefix_fingerprint"]
                or receipt.get("source_call_id") != source_row["call_id"]
                or receipt.get("source_result_fingerprint") != source_row["result_fingerprint"]
                or receipt.get("source_stage_result_fingerprint")
                    != confirmed_prefix["private"]["stage_receipts"]["continuity"]["stage_result_fingerprint"]):
            _reject("repair source continuity reuse reference changed")
    if receipt.get("stage_result_fingerprint") != receipt_fp or state.get("continuity_receipt_fingerprint") != receipt_fp or receipt.get("agent_input_fingerprint") != job.get("input_fingerprint") or receipt.get("judgment", {}).get("status") != "pass" or parse_json_object(result.get("final_text"), label="source continuity").get("status") != "pass":
        _reject("repair source continuity evidence is inconsistent")
    if receipt.get("context_bundle_fingerprint") != state["context_bundle_fingerprint"] or receipt.get("freeze_fingerprint") != state["freeze_fingerprint"]:
        _reject("repair source continuity context binding changed")
    context = job.get("context")
    if not isinstance(context, list) or len(context) != 1 or not isinstance(context[0], dict) or context[0].get("upstream_artifacts", {}).get("candidate") != {"text": state["candidate_text"], "artifact_fingerprint": state["candidate_fingerprint"]}:
        _reject("repair source continuity call does not bind the candidate")
    return fingerprint_text(row["state_json"]), receipt_fp


def freeze_repair_source(conn, *, source_ref: Any, target: dict[str, Any], _seen: frozenset[str] = frozenset(), _recorded: bool = False) -> dict[str, Any]:
    """Read and validate a private source inside the caller's transaction."""
    reference = _reference(source_ref)
    if set(reference) == AUTHOR_REFERENCE_KEYS:
        from .author_revision import freeze_author_revision_source
        return freeze_author_revision_source(conn, reference=reference, target=target, seen=_seen)
    if reference["source_run_id"] in _seen:
        _reject("repair source ancestry contains a cycle", code="repair_lineage_invalid")
    seen = _seen | {reference["source_run_id"]}
    exact_target = _target(target)
    identity = conn.execute("SELECT project_id FROM project_identity").fetchall()
    if len(identity) != 1:
        _reject("repair source requires one native project identity")
    row = conn.execute("SELECT * FROM runs WHERE run_id=?", (reference["source_run_id"],)).fetchone()
    if row is None:
        _reject("repair source run is not in this project", code="repair_source_not_found")
    run = dict(row)
    if run["status"] != "failed_gate" or run["task_mode"] not in {"DRAFT", "REVISE"}:
        _reject("repair source must be a terminal rejected production run")
    execution = conn.execute("SELECT * FROM production_executions WHERE run_id=?", (run["run_id"],)).fetchone()
    if execution is None or execution["cancel_requested"]:
        _reject("repair source has no completed execution request")
    if execution["owner_token"] and (execution["lease_expires_at_ms"] or 0) > int(time.time() * 1000):
        _reject("repair source still has an active executor", code="repair_source_active")
    request = _object(execution["request_json"], "source production request")
    if fingerprint(request) != execution["request_fingerprint"] or request.get("document_id") != exact_target["document_id"]:
        _reject("repair source execution request binding is invalid")
    source_target, target_fp = _author_request(conn, run)
    if _target(source_target) != exact_target:
        _reject("repair source belongs to a different chapter, document or order", code="repair_source_target_mismatch")
    checkpoint = conn.execute(
        "SELECT * FROM checkpoints WHERE checkpoint_id=? AND run_id=? AND checkpoint_kind='production_qualified_candidate'",
        (reference["source_checkpoint_id"], run["run_id"]),
    ).fetchone()
    if checkpoint is None:
        _reject("repair source candidate checkpoint is not in the source run", code="repair_source_not_found")
    state = _object(checkpoint["state_json"], "source diagnostic candidate")
    candidate = reference["expected_candidate_fingerprint"]
    text = state.get("candidate_text")
    if state.get("schema") != "quillframe_qualified_diagnostic_candidate_v1" or state.get("run_id") != run["run_id"] or state.get("document_id") != exact_target["document_id"] or state.get("subject_id") != exact_target["document_id"] or state.get("authority") is not False:
        _reject("repair source candidate identity is invalid")
    if not isinstance(text, str) or not text.strip() or fingerprint_text(text) != candidate or state.get("candidate_fingerprint") != candidate or checkpoint["artifact_fingerprint"] != candidate:
        _reject("repair source candidate bytes or fingerprint changed")
    if conn.execute("SELECT 1 FROM candidates WHERE run_id=? LIMIT 1", (run["run_id"],)).fetchone():
        _reject("repair source must remain an internal candidate")
    calls, native_journal_fp = _confirmed_calls(conn, run, request)
    confirmed_prefix = _confirmed_prefix_evidence(conn, run, request, state)
    prefix_calls = confirmed_prefix["private"]["calls"] if confirmed_prefix else calls
    journal_fp = (
        confirmed_prefix["logical_journal_fingerprint"](native_journal_fp)
        if confirmed_prefix else native_journal_fp
    )
    _, surface_result = _call_for_role(prefix_calls, "surface_realization")
    surface = parse_json_object(surface_result.get("final_text"), label="source surface realization")
    if surface.get("status") == "pass" and surface.get("text") != text and run["task_mode"] == "REVISE":
        surface = _validated_derived_surface(conn, prefix_calls, surface, text)
    if surface.get("status") != "pass" or surface.get("text") != text:
        _reject("repair source prose differs from its confirmed surface response")
    _registered_binding(
        state.get("reader_binding"), contract_id="reader.engagement_audit",
        role="registered_reader_engagement", calls=prefix_calls, candidate=candidate,
        text=text, subject=exact_target["document_id"],
        recorded=(_recorded or confirmed_prefix is not None),
    )
    _registered_binding(
        state.get("self_audit_binding"), contract_id="quality.candidate_self_audit",
        role="registered_candidate_self_audit", calls=calls, candidate=candidate,
        text=text, subject=exact_target["document_id"], recorded=_recorded,
    )
    context_fp, continuity_fp = _context_and_continuity(
        conn, run, state, source_target, calls, confirmed_prefix=confirmed_prefix,
    )
    qualification = state.get("qualification_receipt")
    if validate_qualification_receipt(qualification, candidate_fingerprint=candidate, subject_id=exact_target["document_id"], require_qualified=False) or qualification.get("qualification_status") != "repair_required":
        _reject("repair source is not a valid repair_required qualification")
    preservation = state.get("repair_preservation")
    if run["task_mode"] == "REVISE":
        if type(qualification.get("repair_cycle")) is not int or qualification["repair_cycle"] < 1 or not isinstance(preservation, dict) or not isinstance(preservation.get("semantic_binding"), dict):
            _reject("a rejected REVISE source requires its actual repair comparison")
        comparison = preservation["semantic_binding"]
        _registered_call(comparison.get("job"), comparison.get("result"), role="registered_repair_comparison", calls=calls, recorded=_recorded)
        comparison_payload = comparison["job"]["input"]["payload"]
        if comparison["job"]["input"]["model_contract_id"] != "quality.compare" or comparison_payload.get("evolution_subject_id") != exact_target["document_id"] or comparison_payload.get("challenger", {}).get("content_fingerprint") != candidate:
            _reject("repair source comparison does not bind its challenger")
    elif qualification.get("repair_cycle") != 0 or preservation is not None:
        _reject("DRAFT repair source cannot carry a repair comparison")
    expected = build_pre_independent_qualification(
        subject_id=exact_target["document_id"], candidate_fingerprint=candidate,
        self_audit_binding=state["self_audit_binding"], reader_binding=state["reader_binding"],
        continuity_receipt_fingerprint=continuity_fp, repair_cycle=qualification["repair_cycle"],
        repair_preservation=preservation,
        _recorded=_recorded,
    )
    if expected != qualification:
        _reject("repair source qualification does not match its confirmed diagnostics")
    lineage = state.get("repair_lineage")
    if run["task_mode"] == "REVISE" and (not isinstance(lineage, dict) or not lineage):
        _reject("a rejected REVISE source requires its existing repair lineage")
    if lineage is not None and not isinstance(lineage, dict):
        _reject("repair source lineage is invalid")
    from .repair import prior_lineage
    if run["task_mode"] == "REVISE":
        parent = load_repair_source(conn, run["run_id"], _seen=seen, _recorded=_recorded)
        evolution_run_id, parent_nodes = prior_lineage(parent)
        if (lineage.get("source_fingerprint") != parent["source_fingerprint"]
                or lineage.get("evolution_run_id") != evolution_run_id
                or not isinstance(lineage.get("nodes"), list)
                or lineage["nodes"][:-1] != parent_nodes
                or qualification["repair_cycle"] != len(lineage["nodes"]) - 1):
            _reject("repair lineage differs from its verified parent source", code="repair_lineage_invalid")
    frozen = {
        "schema": SCHEMA, "source_project_id": identity[0]["project_id"],
        "source_run_id": run["run_id"], "source_task_mode": run["task_mode"],
        "source_run_fingerprint": fingerprint(run),
        "source_checkpoint_id": checkpoint["checkpoint_id"],
        "source_checkpoint_fingerprint": fingerprint_text(checkpoint["state_json"]),
        "candidate_text": text, "candidate_fingerprint": candidate,
        "reader_binding": state["reader_binding"], "self_audit_binding": state["self_audit_binding"],
        "qualification_receipt": qualification,
        "source_context_bundle_fingerprint": state["context_bundle_fingerprint"],
        "source_freeze_fingerprint": state["freeze_fingerprint"],
        "source_context_checkpoint_fingerprint": context_fp,
        "source_request": request, "source_request_fingerprint": execution["request_fingerprint"],
        "source_target_context": source_target, "source_target_context_fingerprint": target_fp,
        "source_journal_fingerprint": journal_fp, "source_lineage": lineage,
        "source_repair_preservation": preservation, "authority": False,
    }
    assert_secret_free(frozen, label="private repair source")
    frozen["source_fingerprint"] = fingerprint(frozen)
    # A losing challenger remains diagnostic evidence, never the next incumbent.
    # This boundary deliberately does not guess a different repair source.
    prior_lineage(frozen)
    return frozen


def load_repair_source(conn, run_id: str, *, _seen: frozenset[str] = frozenset(), _recorded: bool = False) -> dict[str, Any]:
    """Recheck the exact frozen source and its original immutable evidence."""
    row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if row is None or row["task_mode"] != "REVISE":
        _reject("repair source can only belong to a registered REVISE run")
    target, _ = _author_request(conn, dict(row))
    if "repair_source" not in target["payload"]:
        _reject("REVISE requires a Core-frozen repair source", code="repair_source_missing")
    reference = _reference(target["payload"].get("repair_source"))
    rows = conn.execute(
        "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_repair_source'",
        (run_id,),
    ).fetchall()
    if len(rows) != 1:
        _reject("REVISE requires one Core-frozen repair source", code="repair_source_missing")
    frozen = _object(rows[0]["state_json"], "frozen repair source")
    source_fp = fingerprint({key: value for key, value in frozen.items() if key != "source_fingerprint"})
    if frozen.get("schema") != SCHEMA or frozen.get("source_fingerprint") != source_fp or rows[0]["artifact_fingerprint"] != source_fp:
        _reject("frozen repair source fingerprint is invalid")
    current = freeze_repair_source(conn, source_ref=reference, target=target, _seen=_seen | {run_id}, _recorded=_recorded)
    if current != frozen:
        _reject("the original repair source changed after registration", code="repair_source_changed")
    source_model = frozen["source_target_context"].get("author_model")
    target_model = target.get("author_model")
    if not isinstance(source_model, dict) or not isinstance(target_model, dict):
        _reject("repair preference projections are missing", code="repair_objective_changed")
    preference_keys = ("selected_hypothesis_ids", "active_preferences")
    if ({key: source_model.get(key) for key in preference_keys} != {key: target_model.get(key) for key in preference_keys}
            or target["payload"].get("selected_preference_ids", []) != source_model.get("selected_hypothesis_ids")):
        _reject("repair preference selection differs from its frozen source", code="repair_objective_changed")
    return frozen
