"""Read exact historical independent evidence without granting new authority.

The source reader owns authorization and confirmed generation-call checks. This
module binds the old release to its own frozen job, result, receipt and durable
submission. It never dispatches a reviewer or changes a historical judgment.
"""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from harness.context_runtime import fingerprint
from harness.semantic_workers.independent_invocation_receipt import SCHEMA as NATIVE_SCHEMA, validate_receipt as validate_native_receipt
from harness.semantic_workers.peer_bridge_receipt import SCHEMA as BRIDGE_SCHEMA, validate_recorded_receipt
from harness.semantic_workers.peer_chat_relay import validate_peer_result
from harness.semantic_workers.registered_contract_binding import validate_recorded_registered_job
from harness.semantic_workers.semantic_worker_router import worker_job_view
from persistence.quillframe_sqlite import canonical_json, fingerprint_text
from quality.author_objective_gate import validate_objective_assessments
from quality.candidate_qualification import validate_qualification_receipt

from .contracts import PRODUCTION_EXECUTION_SCHEMA, PRODUCTION_STAGE_RESULT_SCHEMA, ProductionRunError, assert_secret_free

EVIDENCE_SCHEMA = "quillframe_recorded_independent_evidence_v1"
EVIDENCE_KIND = "production_independent_evidence"
PACKET_JOB_KEYS = ("job_id", "kind", "subject_id", "created_at", "input_fingerprint", "input", "rubric", "output_contract", "permissions", "provenance")


def _reject(message: str) -> None:
    raise ProductionRunError("repair_source_independent_invalid", message)


def _object(raw: Any, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ProductionRunError("repair_source_independent_invalid", f"recorded {label} is not JSON") from exc
    if not isinstance(value, dict) or canonical_json(value) != raw:
        _reject(f"recorded {label} is not a canonical object")
    return value


def _snapshot(*, run_id: str, handoff: dict[str, Any], result: dict[str, Any],
              receipt: dict[str, Any], submission_fingerprint: str) -> dict[str, Any]:
    """Snapshot only after live submission validation, inside its effect guard."""
    value = {
        "schema": EVIDENCE_SCHEMA, "run_id": run_id,
        "candidate_fingerprint": handoff["candidate_fingerprint"], "subject_id": handoff["subject_id"],
        "handoff_fingerprint": fingerprint(handoff), "peer_packet_fingerprint": fingerprint(handoff["peer_packet"]),
        "qualification_receipt_fingerprint": handoff["qualification_receipt"]["receipt_fingerprint"],
        "result": deepcopy(result), "independence_receipt": deepcopy(receipt),
        "submission_evidence_fingerprint": submission_fingerprint, "authority": False,
    }
    assert_secret_free(value, label="private independent evidence")
    value["evidence_fingerprint"] = fingerprint(value)
    return value


def _handoff(conn, run, state, project_id):
    rows = conn.execute(
        "SELECT * FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_independent_handoff'", (run["run_id"],)
    ).fetchall()
    if len(rows) != 1:
        _reject("released source requires one original independent handoff")
    row = dict(rows[0])
    handoff = _object(row["state_json"], "independent handoff")
    if handoff.get("schema") != "quillframe_independent_review_handoff_v1" or handoff.get("authority") is not False:
        _reject("recorded independent handoff schema or authority changed")
    for key in ("subject_id", "candidate_fingerprint", "qualification_receipt", "reader_binding", "reader_grip",
                "author_objectives",
                "reader_visible_context", "continuity_receipt_fingerprint", "context_bundle_fingerprint", "freeze_fingerprint", "document_id"):
        if handoff.get(key) != state.get(key):
            _reject("recorded independent handoff changed its qualified candidate")
    if row["artifact_fingerprint"] != state["candidate_fingerprint"]:
        _reject("recorded independent handoff artifact changed")
    job, packet = handoff.get("independent_job"), handoff.get("peer_packet")
    if not isinstance(job, dict) or not isinstance(packet, dict) or validate_recorded_registered_job(job):
        _reject("recorded independent job is not its trusted registered contract")
    if job["input"]["model_contract_id"] != "quality.production_review" or job["subject_id"] != state["subject_id"]:
        _reject("recorded independent job changed its review role or subject")
    if job.get("dispatch_proof") != state["qualification_receipt"] or job.get("execution") != {
        "source_session_id": run["session_id"], "worker_session_id": None,
        "handoff_id": run["run_id"] + ":quality.production_review", "attempt_id": None,
    }:
        _reject("recorded independent job changed its qualification or source session")
    if job["provenance"].get("project_id") != project_id:
        _reject("recorded independent job belongs to another project")
    reader_payload = state["reader_binding"]["job"]["input"]["payload"]
    expected_payload = {
        "candidate_fingerprint": state["candidate_fingerprint"], "candidate_text": state["candidate_text"],
        "reader_visible_context": state["reader_visible_context"], "reader_grip": state["reader_grip"],
        **{key: reader_payload[key] for key in ("genre_profile", "platform_profile", "chapter_position") if key in reader_payload},
    }
    objective_presence = (
        "author_objectives" in state,
        "author_objectives" in handoff,
        "author_objectives" in job["input"]["payload"],
    )
    if len(set(objective_presence)) != 1:
        _reject("recorded independent objective binding is only partially present")
    if objective_presence[0]:
        expected_payload["author_objectives"] = state["author_objectives"]
    if job["input"]["payload"] != expected_payload:
        _reject("recorded independent review did not read the exact frozen prose and positioning")
    visible = worker_job_view(job)
    if packet.get("job") != {key: visible.get(key) for key in PACKET_JOB_KEYS}:
        _reject("recorded peer packet differs from the frozen independent job")
    if not isinstance(handoff.get("peer_packet_bytes"), str) or canonical_json(packet) != handoff["peer_packet_bytes"]:
        _reject("recorded peer packet bytes changed")
    if packet.get("return_binding") != {"run_reference": packet.get("relay_nonce"), "fresh_conversation_required": True,
                                        "same_project_writer_chat_forbidden": True} or packet.get("execution_permissions") != {
        key: False for key in ("project_read", "filesystem", "shell", "network", "memory", "write")
    }:
        _reject("recorded independent packet changed its isolation boundary")
    if validate_recorded_registered_job(packet["job"]):
        _reject("recorded independent packet contract changed")
    return row, handoff


def _original_result(conn, run, handoff, review):
    receipt = review.get("independence_receipt")
    if not isinstance(receipt, dict):
        _reject("recorded review has no independence receipt")
    expected_fp = receipt.get("result_fingerprint")
    rows = conn.execute("SELECT * FROM checkpoints WHERE run_id=? AND checkpoint_kind=?", (run["run_id"], EVIDENCE_KIND)).fetchall()
    if len(rows) > 1:
        _reject("recorded independent result is ambiguous")
    proof_row = dict(rows[0]) if rows else None
    if proof_row:
        proof = _object(proof_row["state_json"], "independent result evidence")
        result = proof.get("result")
        if not isinstance(result, dict) or fingerprint(result) != expected_fp:
            _reject("persisted independent result differs from its original receipt")
        expected = _snapshot(run_id=run["run_id"], handoff=handoff, result=result, receipt=receipt,
                             submission_fingerprint=review.get("submission_evidence_fingerprint"))
        if proof != expected or proof_row["artifact_fingerprint"] != expected["evidence_fingerprint"]:
            _reject("persisted independent evidence changed its source binding")
        return result, receipt, proof_row, "persisted_exact_result"

    # Legacy Review projections did not retain schema/execution. Only these
    # standard envelopes are recoverable, and only an exact original result
    # fingerprint can establish which one was actually submitted. Unknown
    # metadata is never invented, and summaries cannot replace judgments.
    job, packet = handoff["independent_job"], handoff["peer_packet"]
    base = {
        "job_id": review.get("job_id"), "subject_id": job["subject_id"], "kind": job["kind"],
        "input_fingerprint": review.get("input_fingerprint"), "status": "completed",
        "worker": deepcopy(review.get("worker")), "judgment": deepcopy(review.get("judgment")), "proposals": [], "errors": [],
    }
    matches = []
    for schema in (None, "quillframe_peer_review_result_v1"):
        for include_execution in (False, True):
            value = deepcopy(base)
            if schema is not None:
                value["schema"] = schema
            if include_execution:
                value["execution"] = {"run_reference": packet["relay_nonce"]}
            if fingerprint(value) == expected_fp:
                matches.append(value)
    if len(matches) != 1:
        _reject("original independent result cannot be recovered from its recorded fingerprint")
    return matches[0], receipt, None, "legacy_exact_standard_envelope"


def _native_lifecycle(conn, *, run, project_id, handoff, result, receipt):
    errors = validate_native_receipt(receipt, handoff["peer_packet"], result)
    if errors:
        _reject("recorded native independence receipt is invalid")
    row = conn.execute("SELECT * FROM independent_review_leases WHERE lease_id=?", (receipt["lease_id"],)).fetchone()
    if row is None:
        _reject("recorded native independence lease is missing")
    lease = dict(row)
    lease["packet_bytes"] = bytes(lease["packet_bytes"]).decode("utf-8")
    expected = {
        "project_id": project_id, "run_id": run["run_id"], "candidate_fingerprint": handoff["candidate_fingerprint"],
        "job_id": handoff["independent_job"]["job_id"], "input_fingerprint": handoff["independent_job"]["input_fingerprint"],
        "packet_fingerprint": fingerprint(handoff["peer_packet"]), "result_fingerprint": fingerprint(result),
        "relay_nonce": handoff["peer_packet"]["relay_nonce"], "parent_session_id": run["session_id"],
    }
    for key in ("provider", "transport", "assurance_class", "reviewer_session_id", "host_agent_id", "host_invocation_id"):
        expected[key] = receipt.get(key)
    if any(lease.get(key) != value or receipt.get(key) != value for key, value in expected.items()):
        _reject("recorded native lease changed its invocation identity")
    if (lease.get("status") != "completed" or lease["packet_bytes"] != handoff["peer_packet_bytes"]
            or lease.get("receipt_json") != canonical_json(receipt) or lease.get("receipt_fingerprint") != receipt["receipt_fingerprint"]
            or lease.get("completion_result_fingerprint") != fingerprint(result)):
        _reject("recorded native lease has not completed with this exact result")
    session = conn.execute("SELECT provider_session_ref FROM sessions WHERE session_id=?", (lease["reviewer_session_id"],)).fetchone()
    if session is None or session["provider_session_ref"] != lease["host_agent_id"]:
        _reject("recorded native reviewer session is not its host invocation")
    rows = [dict(row) for row in conn.execute(
        "SELECT * FROM independent_review_lifecycle_events WHERE lease_id=? ORDER BY created_at,rowid", (lease["lease_id"],)
    )]
    if [row["event_kind"] for row in rows] != ["prepared", "claimed", "completed"]:
        _reject("recorded native lifecycle must retain its three original events")
    expected_payloads = [
        {key: lease[key] for key in ("project_id", "candidate_fingerprint", "packet_fingerprint", "provider", "transport", "parent_session_id")},
        {key: lease[key] for key in ("provider", "parent_session_id", "reviewer_session_id", "agent_type", "host_agent_id", "host_invocation_id")},
        {key: lease[key] for key in ("result_fingerprint", "provider", "reviewer_session_id", "host_agent_id", "host_invocation_id")},
    ]
    events = []
    for row, payload in zip(rows, expected_payloads):
        event = {key: row[key] for key in ("event_id", "lease_id", "run_id", "event_kind", "created_at")}
        event["payload"] = _object(row["payload_json"], "native lifecycle payload")
        if (event["run_id"] != run["run_id"] or event["payload"] != payload
                or fingerprint(event) != row["event_fingerprint"]):
            _reject("recorded native lifecycle event changed")
        events.append({**event, "event_fingerprint": row["event_fingerprint"]})
    if (receipt.get("lifecycle_events") != [{key: event[key] for key in ("event_id", "event_kind", "event_fingerprint")} for event in events]
            or lease.get("completion_event_json") != canonical_json(events[-1])):
        _reject("recorded native receipt is not bound to its durable lifecycle")
    return fingerprint({"lease": lease, "events": events})


def _independence_summary(receipt):
    if receipt["schema"] == NATIVE_SCHEMA:
        return {"mode": "host_native_lifecycle", **{key: receipt[key] for key in (
            "project_id", "provider", "transport", "assurance_class", "parent_session_id", "reviewer_session_id",
            "host_agent_id", "host_invocation_id", "result_fingerprint", "receipt_fingerprint",
        )}}
    return {
        "mode": "project_owned_peer_bridge", **{key: receipt[key] for key in (
            "project_id", "project_repo", "framework_repo", "framework_commit", "issue_number", "result_fingerprint", "relay_nonce_fingerprint",
        )}, "provider": receipt["worker_provider"], "transport": "github_actions", "assurance_class": "project_owned_automation_receipt",
    }


def _semantic_summary(category, job, result, independence=None):
    provenance, worker = job["provenance"], result["worker"]
    value = {
        "category": category, "status": "pass", "candidate_fingerprint": job["input"]["payload"]["candidate_fingerprint"], "evidence_refs": [],
        "semantic_contract": {
            "model_contract_id": job["input"]["model_contract_id"], **{key: provenance[key] for key in ("registry_schema", "registry_version", "pack_id")},
            "release_role": category, "independent_gate": provenance["independent_gate"], "job_fingerprint": job["input_fingerprint"],
            "worker_provider": worker.get("provider"), "model_or_reviewer": worker.get("model_or_reviewer"), "independence": independence,
        }, "semantic_content_reinterpreted_by_runtime": False,
    }
    if category == "semantic_independent" and "author_objectives" in job["input"]["payload"]:
        try:
            objective_summary = validate_objective_assessments(
                job["input"]["payload"]["author_objectives"],
                result["judgment"],
            )
        except ValueError as exc:
            _reject("recorded independent objective evidence is invalid")
        value.update({
            "author_objective_status": objective_summary["status"],
            "author_objectives_fingerprint": objective_summary["objectives_fingerprint"],
            "objective_assessments": objective_summary["assessments"],
        })
    return value


def _readiness(readiness, *, state, handoff, result, receipt):
    if not isinstance(readiness, dict):
        _reject("recorded independent review has no original readiness")
    qualification = state["qualification_receipt"]
    reader = state["reader_binding"]
    if (qualification.get("surface_audit_status") != "pass" or validate_recorded_registered_job(reader["job"])
            or reader["result"].get("judgment", {}).get("result") != "pass"
            or reader["job"]["input"]["payload"].get("candidate_fingerprint") != state["candidate_fingerprint"]):
        _reject("recorded readiness Reader binding changed")
    gates = [
        {"category": "surface", "candidate_fingerprint": state["candidate_fingerprint"], "status": "pass",
         "evidence_refs": ["qualification:" + qualification["receipt_fingerprint"]]},
        {"category": "continuity", "candidate_fingerprint": state["candidate_fingerprint"], "status": "pass",
         "evidence_refs": ["continuity:" + state["continuity_receipt_fingerprint"]]},
        _semantic_summary("reader_engagement", reader["job"], reader["result"]),
        _semantic_summary("semantic_independent", handoff["independent_job"], result, _independence_summary(receipt)),
    ]
    # Rebind the stored v1 projection to its actual component evidence. This is
    # not a fresh quality evaluation or a way to dispatch historical contracts.
    expected = {
        "schema": "quillframe_production_readiness_v1", "candidate_fingerprint": state["candidate_fingerprint"],
        "policy": {"reader_grip": state["reader_grip"], "require_continuity": True, "require_semantic_rules": False, "require_independent_semantic": True},
        "required_gates": ["surface", "reader_engagement", "continuity", "semantic_independent"],
        "gates": sorted(gates, key=lambda gate: gate["category"]), "blocking_gates": [], "pending_gates": [],
        "ready_for_user_visible_review": True, "conjunctive_gate": True, "numeric_quality_aggregation": False,
        "registered_reader_engagement_required": True, "registered_semantic_rule_audit_required": False,
        "registered_independent_release_contract_required": True, "project_bridge_receipt_required_for_independence": False,
        "independence_receipt_required": True, "native_lifecycle_receipt_supported": True, "pre_independent_qualification_required": True,
        "pre_independent_qualification": {key: qualification[key] for key in ("receipt_fingerprint", "qualification_status", "candidate_fingerprint", "independent")},
        "independent_pass_can_override_qualification_failure": False, "semantic_content_reinterpreted_by_runtime": False,
        "authority": False, "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False}, "model_execution": False,
    }
    if readiness != expected:
        _reject("recorded readiness does not match its actual independent and Reader evidence")


def _stage(conn, run_id, mechanism, state):
    matches = []
    for row in conn.execute("SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage'", (run_id,)):
        value = _object(row["payload_json"], "production stage receipt")
        if value.get("mechanism") == mechanism:
            matches.append(value)
    if len(matches) != 1:
        _reject("released source requires one exact independent and visible stage receipt")
    value = matches[0]
    if (value.get("schema") != PRODUCTION_STAGE_RESULT_SCHEMA
            or value.get("stage_result_fingerprint") != fingerprint({key: item for key, item in value.items() if key != "stage_result_fingerprint"})
            or any(value.get(key) != state[key] for key in ("context_bundle_fingerprint", "freeze_fingerprint"))
            or value.get("judgment", {}).get("status") != "pass"
            or value.get("judgment", {}).get("artifact_fingerprint") != state["candidate_fingerprint"] or value.get("authority") is not False):
        _reject("recorded release stage receipt changed")
    return value


def validate_recorded_independent(conn, *, run, state, release, candidate_id) -> dict[str, Any]:
    """Return only identity/fingerprint evidence after exact historical checks.

    The caller must already validate the source's authorization, generation
    journal and qualification components. No returned field is new release or
    independent-review authority, and no old judgment is exposed to a reviewer.
    """
    try:
        return _validate(conn, run=run, state=state, release=release, candidate_id=candidate_id)
    except ProductionRunError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ProductionRunError("repair_source_independent_invalid", "recorded independent evidence is malformed") from exc


def _validate(conn, *, run, state, release, candidate_id):
    candidate_fp = state["candidate_fingerprint"]
    if (run.get("status") != "completed" or run.get("result_fingerprint") != candidate_fp or state.get("run_id") != run["run_id"]
            or fingerprint_text(state["candidate_text"]) != candidate_fp
            or validate_qualification_receipt(state.get("qualification_receipt"), candidate_fingerprint=candidate_fp,
                                               subject_id=state.get("subject_id"), require_qualified=True)):
        _reject("recorded source is not an exact completed qualified candidate")
    identity = conn.execute("SELECT project_id FROM project_identity").fetchall()
    if len(identity) != 1:
        _reject("recorded independent evidence requires one native project identity")
    project_id = identity[0]["project_id"]
    candidate = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
    if (candidate is None or candidate["run_id"] != run["run_id"] or candidate["content_fingerprint"] != candidate_fp
            or candidate["document_id"] != state["document_id"] or candidate["user_visible_gate"] != "PASS"):
        _reject("recorded independent candidate binding changed")
    handoff_row, handoff = _handoff(conn, run, state, project_id)
    rows = conn.execute("SELECT * FROM review_evidence WHERE candidate_id=? AND independent=1", (candidate_id,)).fetchall()
    if len(rows) != 1:
        _reject("released source requires one original independent review")
    review_row = dict(rows[0])
    if review_row["candidate_fingerprint"] != candidate_fp or review_row["stale"] != 0 or review_row["evidence_kind"] != "quality.production_review":
        _reject("recorded independent review is stale or belongs to another candidate")
    review = _object(review_row["result_json"], "independent review")
    if review.get("model_contract_id") != "quality.production_review" or review.get("authority") is not False:
        _reject("recorded independent review changed its role or authority")
    result, receipt, proof_row, source_kind = _original_result(conn, run, handoff, review)
    if (validate_peer_result(handoff["peer_packet"], result) or result.get("status") != "completed"
            or result.get("judgment", {}).get("result") != "pass" or result.get("proposals") != [] or result.get("errors") != []):
        _reject("released source does not retain a completed independent PASS")
    if any(review.get(key) != result.get(key) for key in ("judgment", "worker", "job_id", "input_fingerprint")):
        _reject("recorded Review projection differs from the exact independent result")
    if receipt.get("project_id") != project_id or review_row["reviewer_fingerprint"] != fingerprint(result):
        _reject("recorded independent result changed its project or fingerprint")
    lifecycle_fp = None
    if receipt.get("schema") == NATIVE_SCHEMA:
        lifecycle_fp = _native_lifecycle(conn, run=run, project_id=project_id, handoff=handoff, result=result, receipt=receipt)
    elif receipt.get("schema") != BRIDGE_SCHEMA or validate_recorded_receipt(receipt, handoff["peer_packet"], result):
        _reject("recorded project peer independence receipt is invalid")
    submission_fp = fingerprint({"packet_bytes": handoff["peer_packet_bytes"], "result": result, "independence_receipt": receipt})
    if review.get("submission_evidence_fingerprint") != submission_fp:
        _reject("recorded independent submission fingerprint changed")
    readiness = review.get("production_readiness")
    _readiness(readiness, state=state, handoff=handoff, result=result, receipt=receipt)
    independent = _stage(conn, run["run_id"], "independent_semantic_gate", state)
    visible = _stage(conn, run["run_id"], "user_visible_gate", state)
    if (independent.get("agent_input_fingerprint") != handoff["independent_job"]["input_fingerprint"]
            or independent.get("model_contract_id") != "quality.production_review"
            or independent.get("independence_result_fingerprint") != fingerprint(result)
            or visible.get("agent_input_fingerprint") != fingerprint(readiness)):
        _reject("recorded release stages do not bind the actual independent result and readiness")
    from .semantic import final_release
    expected_release = final_release(
        production_readiness=readiness, qualification_receipt=state["qualification_receipt"], candidate_fingerprint=candidate_fp,
        context_bundle_fingerprint=state["context_bundle_fingerprint"], freeze_fingerprint=state["freeze_fingerprint"],
        user_visible_gate_receipt_fingerprint=visible["stage_result_fingerprint"],
    )
    releases = conn.execute("SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_release'", (run["run_id"],)).fetchall()
    if len(releases) != 1 or _object(releases[0]["payload_json"], "production release") != release or release != expected_release:
        _reject("recorded release is not the exact aggregation of its original evidence")
    row = conn.execute("SELECT * FROM independent_review_attempts WHERE run_id=? AND candidate_fingerprint=?", (run["run_id"], candidate_fp)).fetchone()
    if row is None:
        _reject("recorded independent submission has no durable attempt")
    attempt = dict(row)
    response = _object(attempt.get("terminal_response_json"), "terminal independent response")
    # A crash after candidate persistence can terminalize via the existing
    # completed projection, which carries the same release but omits readiness.
    response_readiness_matches = response.get("production_readiness") == readiness or (
        "production_readiness" not in response and response.get("replayed") is True
    )
    if (attempt.get("status") != "terminal" or attempt.get("terminal_status") != "completed"
            or attempt.get("terminal_evidence_fingerprint") != submission_fp
            or attempt.get("terminal_response_fingerprint") != fingerprint(response)
            or response.get("schema") != PRODUCTION_EXECUTION_SCHEMA
            or response.get("status") != "completed" or response.get("run_id") != run["run_id"]
            or response.get("project_id") != project_id or response.get("candidate", {}).get("candidate_id") != candidate_id
            or response.get("candidate", {}).get("candidate_fingerprint") != candidate_fp
            or response.get("production_release") != release or not response_readiness_matches):
        _reject("recorded independent attempt is not the completed exact submission")
    projection = {
        "schema": "quillframe_recorded_independent_binding_v1", "candidate_fingerprint": candidate_fp,
        "handoff_checkpoint_id": handoff_row["checkpoint_id"], "handoff_fingerprint": fingerprint(handoff),
        "review_evidence_id": review_row["review_id"], "review_evidence_fingerprint": fingerprint(review_row),
        "result_fingerprint": fingerprint(result), "independence_receipt_fingerprint": fingerprint(receipt),
        "submission_evidence_fingerprint": submission_fp, "original_result_source": source_kind,
        "exact_result_checkpoint_fingerprint": fingerprint(proof_row) if proof_row else None,
        "readiness_fingerprint": fingerprint(readiness), "release_fingerprint": release["release_fingerprint"],
        "terminal_attempt_fingerprint": fingerprint(attempt), "native_lifecycle_fingerprint": lifecycle_fp, "authority": False,
    }
    assert_secret_free(projection, label="recorded independent evidence projection")
    projection["evidence_fingerprint"] = fingerprint(projection)
    return projection
