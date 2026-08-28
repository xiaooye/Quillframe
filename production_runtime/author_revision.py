"""Freeze an explicitly requested revision of an exact Core-released draft.

Historical judgments remain evidence from their original contract version. This
path never requalifies a candidate, changes a verdict, accepts prose, or supplies
release authority to the new run.
"""
from __future__ import annotations

import time
from typing import Any

from harness.context_runtime import fingerprint
from persistence.quillframe_sqlite import fingerprint_text
from quality.candidate_qualification import validate_qualification_receipt

from .contracts import ProductionRunError, assert_secret_free, parse_json_object


def freeze_author_revision_source(conn, *, reference: dict[str, str], target: dict[str, Any], seen: frozenset[str]) -> dict[str, Any]:
    from core_operations import CoreOperations, OperationError
    from . import repair_source as source
    from .repair import prior_lineage
    from .semantic import build_pre_independent_qualification
    from .recorded_independent import validate_recorded_independent

    exact_target = source._target(target)
    row = conn.execute(
        "SELECT c.*,r.content AS candidate_content,r.content_fingerprint AS revision_fingerprint "
        "FROM candidates c JOIN document_revisions r ON r.revision_id=c.revision_id WHERE c.candidate_id=?",
        (reference["source_candidate_id"],),
    ).fetchone()
    if row is None:
        source._reject("author revision candidate does not exist", code="repair_source_not_found")
    candidate = dict(row)
    text, candidate_fp = candidate["candidate_content"], reference["expected_candidate_fingerprint"]
    if candidate["status"] != "review_draft" or conn.execute(
        "SELECT 1 FROM acceptance_evidence WHERE candidate_id=? LIMIT 1", (candidate["candidate_id"],)
    ).fetchone():
        source._reject("only an unaccepted Review Draft can become an author revision source")
    if not isinstance(text, str) or not text.strip() or any(value != candidate_fp for value in (
        candidate["content_fingerprint"], candidate["revision_fingerprint"], fingerprint_text(text)
    )):
        source._reject("author revision candidate bytes or fingerprint changed")
    try:
        release = CoreOperations._validated_production_release(conn, candidate)
    except OperationError as exc:
        raise ProductionRunError("repair_source_release_invalid", str(exc)) from exc
    run_id = candidate["run_id"]
    if run_id in seen:
        source._reject("author revision ancestry contains a cycle", code="repair_lineage_invalid")
    run = dict(conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())
    if run["task_mode"] not in {"DRAFT", "REVISE"}:
        source._reject("author revision source is not a production run")
    identity = conn.execute("SELECT project_id FROM project_identity").fetchall()
    if len(identity) != 1:
        source._reject("author revision source requires one native project identity")
    project_id = identity[0]["project_id"]
    source_target, target_fp = source._author_request(conn, run)
    if source._target(source_target) != exact_target or candidate["document_id"] != exact_target["document_id"]:
        source._reject("author revision target changed", code="repair_source_target_mismatch")

    revision_matches = []
    for receipt in conn.execute(
        "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='candidate_revision_request'", (run_id,)
    ):
        value = source._object(receipt["payload_json"], "author revision receipt")
        if value.get("revision_request_id") == reference["revision_request_id"]:
            revision_matches.append(value)
    if len(revision_matches) != 1:
        source._reject("author revision requires one exact authorization receipt", code="revision_authorization_required")
    revision = revision_matches[0]
    if (revision.get("schema") != "quillframe_candidate_revision_request_result_v1"
            or revision.get("candidate_id") != candidate["candidate_id"]
            or revision.get("candidate_fingerprint") != candidate_fp
            or revision.get("effective_status") != "revision_requested"
            or revision.get("canon_mutated") is not False or revision.get("settled") is not False
            or revision.get("authority") is not False):
        source._reject("author revision receipt changed its candidate binding")
    try:
        authorized_by, _ = CoreOperations._validate_write_identity(
            authorized_by=revision.get("authorized_by"), idempotency_key="validate-recorded-revision"
        )
        authorization = CoreOperations._validate_authorization(revision.get("authorization"))
        instruction = CoreOperations._validate_revision_request(revision.get("revision_request"))
    except OperationError as exc:
        raise ProductionRunError("revision_authorization_required", "author revision authorization is invalid") from exc
    original_request = {
        "operation": "candidate.revision.request", "project_id": project_id,
        "candidate_id": candidate["candidate_id"], "candidate_fingerprint": candidate_fp,
        "revision_request": instruction, "authorized_by": authorized_by, "authorization": authorization,
    }
    if revision.get("request_fingerprint") != fingerprint(original_request):
        source._reject("author revision request fingerprint changed")

    execution = conn.execute("SELECT * FROM production_executions WHERE run_id=?", (run_id,)).fetchone()
    if execution is None or execution["cancel_requested"]:
        source._reject("author revision source has no completed execution request")
    if execution["owner_token"] and (execution["lease_expires_at_ms"] or 0) > int(time.time() * 1000):
        source._reject("author revision source still has an active executor", code="repair_source_active")
    request = source._object(execution["request_json"], "source production request")
    if fingerprint(request) != execution["request_fingerprint"] or request.get("document_id") != exact_target["document_id"]:
        source._reject("author revision execution request changed")
    rows = conn.execute(
        "SELECT * FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_qualified_candidate'", (run_id,)
    ).fetchall()
    if len(rows) != 1:
        source._reject("author revision requires its exact qualified candidate checkpoint")
    checkpoint = rows[0]
    state = source._object(checkpoint["state_json"], "released diagnostic candidate")
    if (state.get("schema") != "quillframe_qualified_diagnostic_candidate_v1"
            or state.get("run_id") != run_id or state.get("candidate_text") != text
            or state.get("candidate_fingerprint") != candidate_fp
            or state.get("document_id") != exact_target["document_id"]
            or state.get("subject_id") != exact_target["document_id"]
            or checkpoint["artifact_fingerprint"] != candidate_fp or state.get("authority") is not False):
        source._reject("author revision checkpoint differs from the released candidate")
    calls, journal_fp = source._confirmed_calls(conn, run, request)
    _, surface_response = source._call_for_role(calls, "surface_realization")
    surface = parse_json_object(surface_response.get("final_text"), label="released surface realization")
    if surface.get("status") != "pass" or surface.get("text") != text:
        source._reject("author revision prose differs from its actual model response")
    qualification = state.get("qualification_receipt")
    if (validate_qualification_receipt(qualification, candidate_fingerprint=candidate_fp,
                                      subject_id=exact_target["document_id"], require_qualified=True)
            or release.get("pre_independent_qualification_fingerprint") != qualification.get("receipt_fingerprint")):
        source._reject("author revision original qualification does not bind the release")
    gates = {gate["gate"]: gate for gate in qualification["gates"]}
    for key, gate, contract_id, role in (
        ("reader_binding", "reader_engagement", "reader.engagement_audit", "registered_reader_engagement"),
        ("self_audit_binding", "self_audit", "quality.candidate_self_audit", "registered_candidate_self_audit"),
    ):
        binding = state.get(key)
        source._registered_binding(binding, contract_id=contract_id, role=role, calls=calls,
                                   candidate=candidate_fp, text=text, subject=exact_target["document_id"], recorded=True)
        if (gates[gate].get("job_fingerprint") != binding["job"]["input_fingerprint"]
                or gates[gate].get("result_fingerprint") != fingerprint(binding["result"])
                or binding["result"]["judgment"].get("result") != "pass"):
            source._reject("author revision historical qualification binding changed")
    context_fp, continuity_fp = source._context_and_continuity(conn, run, state, source_target, calls)
    if gates["continuity"].get("receipt_fingerprint") != continuity_fp:
        source._reject("author revision historical continuity binding changed")
    preservation = state.get("repair_preservation")
    lineage = state.get("repair_lineage")
    if run["task_mode"] == "REVISE":
        if (not isinstance(preservation, dict) or not isinstance(preservation.get("semantic_binding"), dict)
                or not isinstance(lineage, dict) or not isinstance(lineage.get("nodes"), list)
                or qualification.get("repair_cycle") != len(lineage["nodes"]) - 1):
            source._reject("released revision must retain its original comparison")
        comparison = preservation["semantic_binding"]
        source._registered_call(comparison.get("job"), comparison.get("result"),
                                role="registered_repair_comparison", calls=calls, recorded=True)
        comparison_payload = comparison["job"]["input"]["payload"]
        if (comparison["job"]["input"]["model_contract_id"] != "quality.compare"
                or comparison_payload.get("evolution_subject_id") != exact_target["document_id"]
                or comparison_payload.get("challenger", {}).get("content_fingerprint") != candidate_fp
                or gates["repair_preservation"].get("job_fingerprint") != comparison["job"]["input_fingerprint"]
                or gates["repair_preservation"].get("result_fingerprint") != fingerprint(comparison["result"])):
            source._reject("author revision historical comparison binding changed")
        parent = source.load_repair_source(conn, run_id, _seen=seen | {run_id}, _recorded=True)
        evolution_run_id, parent_nodes = prior_lineage(parent)
        if (lineage.get("source_fingerprint") != parent["source_fingerprint"]
                or lineage.get("evolution_run_id") != evolution_run_id
                or lineage["nodes"][:-1] != parent_nodes):
            source._reject("released revision lineage differs from its verified parent", code="repair_lineage_invalid")
    elif preservation is not None or lineage is not None or qualification.get("repair_cycle") != 0:
        source._reject("released draft cannot invent a repair history")
    expected_qualification = build_pre_independent_qualification(
        subject_id=exact_target["document_id"], candidate_fingerprint=candidate_fp,
        self_audit_binding=state["self_audit_binding"], reader_binding=state["reader_binding"],
        continuity_receipt_fingerprint=continuity_fp, repair_cycle=qualification["repair_cycle"],
        repair_preservation=preservation, _recorded=True,
    )
    if expected_qualification != qualification:
        source._reject("author revision qualification differs from the original gate evidence")
    independent_evidence = validate_recorded_independent(
        conn, run=run, state=state, release=release, candidate_id=candidate["candidate_id"],
    )

    # Authorization stays at the Core boundary. Only the explicit instruction
    # and its immutable receipt identity may enter private production context.
    revision_projection = {
        "revision_request_id": revision["revision_request_id"],
        "candidate_id": revision["candidate_id"], "candidate_fingerprint": candidate_fp,
        "revision_request": instruction, "request_fingerprint": revision["request_fingerprint"],
        "authority": False,
    }

    frozen = {
        "schema": source.SCHEMA, "source_kind": "author_revision", "source_project_id": project_id,
        "source_run_id": run_id, "source_task_mode": run["task_mode"], "source_run_fingerprint": fingerprint(run),
        "source_checkpoint_id": checkpoint["checkpoint_id"], "source_checkpoint_fingerprint": fingerprint_text(checkpoint["state_json"]),
        "candidate_text": text, "candidate_fingerprint": candidate_fp,
        "reader_binding": state["reader_binding"], "self_audit_binding": state["self_audit_binding"],
        "qualification_receipt": qualification, "source_release": release,
        "source_independent_evidence": independent_evidence,
        "source_candidate_id": candidate["candidate_id"], "source_revision_id": candidate["revision_id"],
        "author_revision_request": revision_projection, "author_revision_request_fingerprint": fingerprint(revision),
        "source_context_bundle_fingerprint": state["context_bundle_fingerprint"],
        "source_freeze_fingerprint": state["freeze_fingerprint"], "source_context_checkpoint_fingerprint": context_fp,
        "source_request": request, "source_request_fingerprint": execution["request_fingerprint"],
        "source_target_context": source_target, "source_target_context_fingerprint": target_fp,
        "source_journal_fingerprint": journal_fp, "source_lineage": state.get("repair_lineage"),
        "source_repair_preservation": preservation, "authority": False,
    }
    assert_secret_free(frozen, label="private author revision source")
    frozen["source_fingerprint"] = fingerprint(frozen)
    prior_lineage(frozen)
    return frozen
