#!/usr/bin/env python3
"""Durable, non-authoritative progress evidence and bounded stall detection.

NovelForge does not ask deterministic code to decide whether a creative task is
"complete". This module only reduces inspectable runtime evidence: whether a
declared work-state changed, repeated exactly, is waiting on user/external input,
or is a replay-safe transport retry. Crossing a bounded no-op policy produces a
stable replan *request identity*; it never mutates a plan or executes follow-up
work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import control_plane  # noqa: E402

EVENT_TYPE = "feedback.observed"
PAYLOAD_KIND = "runtime_progress"
OBSERVATION_SCHEMA = "novelforge_progress_observation_v1"
STATE_SCHEMA = "novelforge_progress_state_v1"
REPLAN_REQUEST_SCHEMA = "novelforge_progress_replan_request_v1"
EXECUTION_STATES = {"executed", "awaiting_user", "awaiting_external"}
LIFECYCLE_STATES = {"no_evidence", "advancing", "uncertain", "stalled", "replan_required"}
CLASSIFICATIONS = {"advancing", "exact_no_op", "waiting", "transport_retry_no_op"}
SHA_PREFIX = "sha256:"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return SHA_PREFIX + hashlib.sha256(canonical(value)).hexdigest()


def nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty string")
    return value.strip()


def is_sha(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith(SHA_PREFIX):
        return False
    try:
        int(value[7:], 16)
    except ValueError:
        return False
    return True


def exact_fields(value: dict[str, Any], expected: set[str], field: str) -> None:
    if set(value) != expected:
        raise ValueError(
            f"{field} fields mismatch missing={sorted(expected-set(value))} extra={sorted(set(value)-expected)}"
        )


def normalize_bindings(value: Any, field: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be array")
    normalized: list[dict[str, str]] = []
    refs: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{field}[{index}] must be object")
        exact_fields(item, {"ref", "fingerprint"}, f"{field}[{index}]")
        ref = nonempty(item.get("ref"), f"{field}[{index}].ref")
        fingerprint = item.get("fingerprint")
        if not is_sha(fingerprint):
            raise ValueError(f"{field}[{index}].fingerprint must be sha256:<64 hex>")
        if ref in refs:
            raise ValueError(f"{field} duplicate ref: {ref}")
        refs.add(ref)
        normalized.append({"ref": ref, "fingerprint": fingerprint})
    return sorted(normalized, key=lambda row: row["ref"])


def binding_fingerprint(bindings: list[dict[str, str]]) -> str:
    return digest(bindings)


def validate_progress_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("event must be object")
    control_plane.ControlPlane.validate_event(event)
    if event.get("event_type") != EVENT_TYPE:
        raise ValueError("progress transport must be feedback.observed")
    if event.get("authority_scope") != "observation":
        raise ValueError("progress authority_scope must be observation")
    resource_id = nonempty(event.get("resource_id"), "resource_id")
    session_id = nonempty(event.get("session_id"), "session_id")
    run_id = nonempty(event.get("run_id"), "run_id")

    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    expected = {
        "schema", "kind", "progress_scope_id", "checkpoint_id", "workflow_cursor",
        "operation_kind", "operation_input_fingerprint", "predecessor_event_id",
        "retry_of_event_id", "execution_state", "before_work", "after_work",
        "evidence_bindings", "authority", "canon_authority", "project_write_authority",
        "framework_write_authority", "settlement_authority",
        "production_readiness_authority", "model_execution",
    }
    exact_fields(payload, expected, "payload")
    if payload.get("schema") != OBSERVATION_SCHEMA or payload.get("kind") != PAYLOAD_KIND:
        raise ValueError("invalid progress payload identity")
    progress_scope_id = nonempty(payload.get("progress_scope_id"), "progress_scope_id")
    checkpoint_id = nonempty(payload.get("checkpoint_id"), "checkpoint_id")
    workflow_cursor = nonempty(payload.get("workflow_cursor"), "workflow_cursor")
    operation_kind = nonempty(payload.get("operation_kind"), "operation_kind")
    operation_input_fingerprint = payload.get("operation_input_fingerprint")
    if not is_sha(operation_input_fingerprint):
        raise ValueError("operation_input_fingerprint must be sha256:<64 hex>")
    predecessor = payload.get("predecessor_event_id")
    if predecessor is not None:
        predecessor = nonempty(predecessor, "predecessor_event_id")
    retry_of = payload.get("retry_of_event_id")
    if retry_of is not None:
        retry_of = nonempty(retry_of, "retry_of_event_id")
    execution_state = payload.get("execution_state")
    if execution_state not in EXECUTION_STATES:
        raise ValueError(f"execution_state must be one of {sorted(EXECUTION_STATES)}")

    before_work = normalize_bindings(payload.get("before_work"), "before_work")
    after_work = normalize_bindings(payload.get("after_work"), "after_work")
    evidence_bindings = normalize_bindings(payload.get("evidence_bindings"), "evidence_bindings")
    before_fp = binding_fingerprint(before_work)
    after_fp = binding_fingerprint(after_work)

    if execution_state in {"awaiting_user", "awaiting_external"} and before_fp != after_fp:
        raise ValueError("waiting observation cannot mutate declared work state")

    authority_fields = (
        "authority", "canon_authority", "project_write_authority",
        "framework_write_authority", "settlement_authority",
        "production_readiness_authority", "model_execution",
    )
    if any(payload.get(key) is not False for key in authority_fields):
        raise ValueError("progress observation cannot grant durable/release authority")

    expected_artifacts = sorted({
        row["fingerprint"] for row in before_work + after_work + evidence_bindings
    })
    envelope_artifacts = event.get("artifact_fingerprints", [])
    if not isinstance(envelope_artifacts, list) or any(not is_sha(x) for x in envelope_artifacts):
        raise ValueError("artifact_fingerprints must be sha256 array")
    if sorted(set(envelope_artifacts)) != expected_artifacts:
        raise ValueError("event artifact_fingerprints must exactly bind work/evidence fingerprints")

    return {
        "event_id": nonempty(event.get("event_id"), "event_id"),
        "resource_id": resource_id,
        "session_id": session_id,
        "run_id": run_id,
        "progress_scope_id": progress_scope_id,
        "checkpoint_id": checkpoint_id,
        "workflow_cursor": workflow_cursor,
        "operation_kind": operation_kind,
        "operation_input_fingerprint": operation_input_fingerprint,
        "predecessor_event_id": predecessor,
        "retry_of_event_id": retry_of,
        "execution_state": execution_state,
        "before_work": before_work,
        "after_work": after_work,
        "before_work_fingerprint": before_fp,
        "after_work_fingerprint": after_fp,
        "evidence_bindings": evidence_bindings,
    }


def classify(normalized: dict[str, Any]) -> str:
    if normalized["before_work_fingerprint"] != normalized["after_work_fingerprint"]:
        return "advancing"
    if normalized["execution_state"] in {"awaiting_user", "awaiting_external"}:
        return "waiting"
    if normalized["retry_of_event_id"] is not None:
        return "transport_retry_no_op"
    return "exact_no_op"


def _stored_event(cp: control_plane.ControlPlane, event_id: str) -> dict[str, Any] | None:
    with cp.connect() as conn:
        row = conn.execute(
            "SELECT event_id,payload_json,payload_hash,received_at FROM events WHERE event_id=?",
            (event_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "event": json.loads(row["payload_json"]),
        "payload_hash": row["payload_hash"],
        "received_at": row["received_at"],
    }


def _scope_events(cp: control_plane.ControlPlane, session_id: str, progress_scope_id: str) -> list[dict[str, Any]]:
    with cp.connect() as conn:
        rows = conn.execute(
            """SELECT event_id,payload_json,payload_hash,received_at FROM events
               WHERE session_id=? AND event_type=? ORDER BY received_at,event_id""",
            (session_id, EVENT_TYPE),
        ).fetchall()
    result = []
    for row in rows:
        event = json.loads(row["payload_json"])
        payload = event.get("payload") if isinstance(event, dict) else None
        if not isinstance(payload, dict):
            continue
        if payload.get("schema") != OBSERVATION_SCHEMA or payload.get("kind") != PAYLOAD_KIND:
            continue
        if payload.get("progress_scope_id") != progress_scope_id:
            continue
        normalized = validate_progress_event(event)
        result.append({
            "event": event,
            "normalized": normalized,
            "payload_hash": row["payload_hash"],
            "received_at": row["received_at"],
        })
    return result


def _ordered_chain(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        return []
    by_id = {row["normalized"]["event_id"]: row for row in events}
    if len(by_id) != len(events):
        raise ValueError("duplicate progress event identity")
    roots = []
    children: dict[str, list[str]] = {}
    for row in events:
        event_id = row["normalized"]["event_id"]
        predecessor = row["normalized"]["predecessor_event_id"]
        if predecessor is None:
            roots.append(event_id)
        else:
            if predecessor not in by_id:
                raise ValueError(f"progress predecessor missing: {predecessor}")
            children.setdefault(predecessor, []).append(event_id)
    if len(roots) != 1:
        raise ValueError("progress scope must contain exactly one lineage root")
    if any(len(ids) != 1 for ids in children.values()):
        raise ValueError("progress lineage branch detected")
    ordered = []
    current = roots[0]
    seen: set[str] = set()
    while current:
        if current in seen:
            raise ValueError("progress lineage cycle detected")
        seen.add(current)
        ordered.append(by_id[current])
        next_ids = children.get(current, [])
        current = next_ids[0] if next_ids else ""
    if len(ordered) != len(events):
        raise ValueError("progress lineage contains disconnected events")
    return ordered


def record_observation(cp: control_plane.ControlPlane, event: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_progress_event(event)
    existing = _stored_event(cp, normalized["event_id"])
    if existing is not None:
        ingested = cp.ingest_event(event)
        return {
            "schema": OBSERVATION_SCHEMA,
            "event_id": ingested["event_id"],
            "recorded": ingested["accepted"],
            "duplicate": ingested["duplicate"],
            "classification": classify(normalized),
            "payload_hash": ingested["payload_hash"],
            "authority": False,
            "model_execution": False,
        }

    chain = _ordered_chain(_scope_events(cp, normalized["session_id"], normalized["progress_scope_id"]))
    latest = chain[-1]["normalized"] if chain else None
    expected_predecessor = latest["event_id"] if latest else None
    if normalized["predecessor_event_id"] != expected_predecessor:
        raise ValueError(
            f"stale progress predecessor expected={expected_predecessor} actual={normalized['predecessor_event_id']}"
        )
    if latest is not None:
        if normalized["resource_id"] != latest["resource_id"]:
            raise ValueError("progress scope cannot switch resource")
        if normalized["before_work_fingerprint"] != latest["after_work_fingerprint"]:
            raise ValueError("progress work-state lineage mismatch")
    if normalized["retry_of_event_id"] is not None:
        if latest is None or normalized["retry_of_event_id"] != latest["event_id"]:
            raise ValueError("transport retry must retry the immediate predecessor")
        if normalized["operation_input_fingerprint"] != latest["operation_input_fingerprint"]:
            raise ValueError("transport retry must preserve operation input fingerprint")

    ingested = cp.ingest_event(event)
    return {
        "schema": OBSERVATION_SCHEMA,
        "event_id": ingested["event_id"],
        "recorded": ingested["accepted"],
        "duplicate": ingested["duplicate"],
        "classification": classify(normalized),
        "payload_hash": ingested["payload_hash"],
        "authority": False,
        "model_execution": False,
    }


def summarize(cp: control_plane.ControlPlane, session_id: str, progress_scope_id: str, max_stalls: int = 3) -> dict[str, Any]:
    session_id = nonempty(session_id, "session_id")
    progress_scope_id = nonempty(progress_scope_id, "progress_scope_id")
    if not isinstance(max_stalls, int) or max_stalls < 2 or max_stalls > 20:
        raise ValueError("max_stalls must be integer between 2 and 20")
    chain = _ordered_chain(_scope_events(cp, session_id, progress_scope_id))
    lifecycle = "no_evidence"
    stall_count = 0
    stall_evidence: list[str] = []
    classifications: list[dict[str, Any]] = []
    current_work_fingerprint = None
    current_run_id = None
    for row in chain:
        normalized = row["normalized"]
        classification = classify(normalized)
        current_run_id = normalized["run_id"]
        current_work_fingerprint = normalized["after_work_fingerprint"]
        if classification == "advancing":
            stall_count = 0
            stall_evidence = []
            lifecycle = "advancing"
        elif classification == "exact_no_op":
            stall_count += 1
            stall_evidence.append(normalized["event_id"])
            if stall_count >= max_stalls:
                lifecycle = "replan_required"
            elif stall_count == 1:
                lifecycle = "uncertain"
            else:
                lifecycle = "stalled"
        elif classification in {"waiting", "transport_retry_no_op"}:
            pass
        classifications.append({
            "event_id": normalized["event_id"],
            "run_id": normalized["run_id"],
            "checkpoint_id": normalized["checkpoint_id"],
            "workflow_cursor": normalized["workflow_cursor"],
            "operation_kind": normalized["operation_kind"],
            "classification": classification,
            "before_work_fingerprint": normalized["before_work_fingerprint"],
            "after_work_fingerprint": normalized["after_work_fingerprint"],
        })

    replan_request = None
    followups: list[dict[str, Any]] = []
    if lifecycle == "replan_required":
        request_body = {
            "schema": REPLAN_REQUEST_SCHEMA,
            "session_id": session_id,
            "run_id": current_run_id,
            "progress_scope_id": progress_scope_id,
            "current_work_fingerprint": current_work_fingerprint,
            "stall_evidence_event_ids": list(stall_evidence),
            "max_stalls": max_stalls,
            "authority": False,
            "plan_mutation_performed": False,
        }
        replan_request = {**request_body, "request_fingerprint": digest(request_body)}
        followups.append({
            "op": "request_replan",
            "request_fingerprint": replan_request["request_fingerprint"],
            "progress_scope_id": progress_scope_id,
            "stall_evidence_event_ids": list(stall_evidence),
            "execution_performed": False,
        })

    return {
        "schema": STATE_SCHEMA,
        "session_id": session_id,
        "run_id": current_run_id,
        "progress_scope_id": progress_scope_id,
        "max_stalls": max_stalls,
        "lifecycle_state": lifecycle,
        "stall_count": stall_count,
        "stall_evidence_event_ids": stall_evidence,
        "current_work_fingerprint": current_work_fingerprint,
        "observation_count": len(chain),
        "observations": classifications,
        "replan_request": replan_request,
        "required_followup_operations": followups,
        "followup_execution_performed": False,
        "authority": False,
        "canon_authority": False,
        "project_write_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "production_readiness_authority": False,
        "acceptance_authority": False,
        "completion_authority": False,
        "model_execution": False,
    }


def _binding(ref: str, char: str) -> dict[str, str]:
    return {"ref": ref, "fingerprint": SHA_PREFIX + char * 64}


def fixture_event(
    event_id: str,
    before: str,
    after: str,
    *,
    predecessor: str | None,
    operation_input: str,
    execution_state: str = "executed",
    retry_of: str | None = None,
    run_id: str = "RUN-P",
    checkpoint: str = "CKP-P",
    scope: str = "draft-loop",
) -> dict[str, Any]:
    before_work = [_binding("WORK-CANDIDATE", before)]
    after_work = [_binding("WORK-CANDIDATE", after)]
    evidence = [_binding("RECEIPT-" + event_id, event_id[-1].lower() if event_id[-1].lower() in "abcdef" else "f")]
    artifacts = sorted({row["fingerprint"] for row in before_work + after_work + evidence})
    return {
        "schema": control_plane.EVENT_SCHEMA,
        "event_id": event_id,
        "event_type": EVENT_TYPE,
        "source": {"kind": "self_test", "actor": "progress_stall.py", "transport": "local", "external_ref": None},
        "resource_id": "BOOK-P",
        "session_id": "SES-P",
        "run_id": run_id,
        "handoff_id": None,
        "authority_scope": "observation",
        "idempotency_key": "progress:" + event_id,
        "artifact_fingerprints": artifacts,
        "created_at": control_plane.now_iso(),
        "payload": {
            "schema": OBSERVATION_SCHEMA,
            "kind": PAYLOAD_KIND,
            "progress_scope_id": scope,
            "checkpoint_id": checkpoint,
            "workflow_cursor": "draft.repair",
            "operation_kind": "repair_attempt",
            "operation_input_fingerprint": SHA_PREFIX + operation_input * 64,
            "predecessor_event_id": predecessor,
            "retry_of_event_id": retry_of,
            "execution_state": execution_state,
            "before_work": before_work,
            "after_work": after_work,
            "evidence_bindings": evidence,
            "authority": False,
            "canon_authority": False,
            "project_write_authority": False,
            "framework_write_authority": False,
            "settlement_authority": False,
            "production_readiness_authority": False,
            "model_execution": False,
        },
    }


def blocked(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def self_test(path: Path) -> int:
    if path.exists():
        path.unlink()
    cp = control_plane.ControlPlane(path)
    cp.init()

    first = fixture_event("EV-P-A", "a", "b", predecessor=None, operation_input="1")
    r1 = record_observation(cp, first)
    no_op_1 = fixture_event("EV-P-B", "b", "b", predecessor="EV-P-A", operation_input="2")
    r2 = record_observation(cp, no_op_1)
    duplicate = record_observation(cp, no_op_1)

    conflicting = json.loads(json.dumps(no_op_1))
    conflicting["payload"]["operation_kind"] = "different_attempt"
    conflict_blocked = blocked(lambda: record_observation(cp, conflicting))

    stale = fixture_event("EV-P-C", "b", "b", predecessor="EV-P-A", operation_input="3")
    stale_predecessor_blocked = blocked(lambda: record_observation(cp, stale))

    retry = fixture_event(
        "EV-P-D", "b", "b", predecessor="EV-P-B", operation_input="2", retry_of="EV-P-B"
    )
    retry_record = record_observation(cp, retry)
    waiting = fixture_event(
        "EV-P-E", "b", "b", predecessor="EV-P-D", operation_input="4", execution_state="awaiting_user"
    )
    wait_record = record_observation(cp, waiting)
    no_op_2 = fixture_event("EV-P-F", "b", "b", predecessor="EV-P-E", operation_input="5")
    record_observation(cp, no_op_2)
    stalled = summarize(cp, "SES-P", "draft-loop", max_stalls=2)
    repeated_summary = summarize(cp, "SES-P", "draft-loop", max_stalls=2)

    advancing = fixture_event("EV-P-A2", "b", "c", predecessor="EV-P-F", operation_input="6", run_id="RUN-P2", checkpoint="CKP-P2")
    record_observation(cp, advancing)
    recovered = summarize(cp, "SES-P", "draft-loop", max_stalls=2)
    slow_advancing = fixture_event("EV-P-A3", "c", "d", predecessor="EV-P-A2", operation_input="7", run_id="RUN-P2", checkpoint="CKP-P3")
    record_observation(cp, slow_advancing)
    still_advancing = summarize(cp, "SES-P", "draft-loop", max_stalls=2)

    wrong_retry = fixture_event("EV-P-X", "d", "d", predecessor="EV-P-A3", operation_input="9", retry_of="EV-P-A3")
    wrong_retry["payload"]["operation_input_fingerprint"] = SHA_PREFIX + "8" * 64
    wrong_retry_blocked = blocked(lambda: record_observation(cp, wrong_retry))

    completion_claim = fixture_event("EV-P-Y", "d", "d", predecessor="EV-P-A3", operation_input="8")
    completion_claim["payload"]["complete"] = True
    completion_claim_blocked = blocked(lambda: validate_progress_event(completion_claim))

    cp_restarted = control_plane.ControlPlane(path)
    restart_state = summarize(cp_restarted, "SES-P", "draft-loop", max_stalls=2)

    checks = {
        "advancing_change_is_detected": r1["classification"] == "advancing",
        "exact_no_op_is_detected": r2["classification"] == "exact_no_op",
        "identical_replay_is_idempotent": duplicate["duplicate"] is True,
        "conflicting_replay_fails_closed": conflict_blocked,
        "stale_predecessor_fails_closed": stale_predecessor_blocked,
        "transport_retry_no_op_does_not_increment_stall": retry_record["classification"] == "transport_retry_no_op",
        "awaiting_user_does_not_increment_stall": wait_record["classification"] == "waiting",
        "bounded_no_op_triggers_replan_request": (
            stalled["lifecycle_state"] == "replan_required"
            and stalled["stall_count"] == 2
            and len(stalled["required_followup_operations"]) == 1
            and stalled["required_followup_operations"][0]["execution_performed"] is False
        ),
        "replan_request_identity_is_stable": (
            stalled["replan_request"]["request_fingerprint"]
            == repeated_summary["replan_request"]["request_fingerprint"]
        ),
        "new_work_state_resets_stall": recovered["lifecycle_state"] == "advancing" and recovered["stall_count"] == 0,
        "slow_but_changing_work_is_not_stalled": still_advancing["lifecycle_state"] == "advancing" and still_advancing["stall_count"] == 0,
        "retry_must_preserve_operation_input": wrong_retry_blocked,
        "completion_claim_is_not_in_contract": completion_claim_blocked,
        "restart_reduces_same_durable_evidence": (
            restart_state["current_work_fingerprint"] == still_advancing["current_work_fingerprint"]
            and restart_state["stall_count"] == still_advancing["stall_count"]
            and restart_state["observation_count"] == still_advancing["observation_count"]
        ),
        "progress_never_grants_release_or_write_authority": all(
            stalled[key] is False for key in (
                "authority", "canon_authority", "project_write_authority",
                "framework_write_authority", "settlement_authority",
                "production_readiness_authority", "acceptance_authority", "completion_authority",
            )
        ),
        "no_followup_is_auto_executed": stalled["followup_execution_performed"] is False,
    }
    ok = all(checks.values())
    print(json.dumps({
        "progress_stall_contract": "PASS" if ok else "FAIL",
        "observation_schema": OBSERVATION_SCHEMA,
        "state_schema": STATE_SCHEMA,
        "replan_request_schema": REPLAN_REQUEST_SCHEMA,
        "classifications": sorted(CLASSIFICATIONS),
        "lifecycle_states": sorted(LIFECYCLE_STATES),
        **checks,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge durable progress/stall reducer")
    parser.add_argument("--db", default=control_plane.DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--event", required=True)
    record = sub.add_parser("record")
    record.add_argument("--event", required=True)
    summary = sub.add_parser("summary")
    summary.add_argument("--session-id", required=True)
    summary.add_argument("--scope", required=True)
    summary.add_argument("--max-stalls", type=int, default=3)
    selftest = sub.add_parser("self-test")
    selftest.add_argument("--path")
    args = parser.parse_args()

    if args.command == "self-test":
        target = Path(args.path) if args.path else Path(tempfile.gettempdir()) / "novelforge-progress-stall.db"
        return self_test(target)

    cp = control_plane.ControlPlane(args.db)
    cp.init()
    if args.command == "validate":
        normalized = validate_progress_event(load(args.event))
        out = {"valid": True, **normalized, "classification": classify(normalized), "authority": False}
    elif args.command == "record":
        out = record_observation(cp, load(args.event))
    else:
        out = summarize(cp, args.session_id, args.scope, args.max_stalls)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
