#!/usr/bin/env python3
"""Side-effect-free public runtime observability projections for NovelForge.

This module is the read boundary for delivery surfaces and external agents. It
opens the Control Plane store read-only, returns versioned safe projections,
and never initializes persistence, acquires leases, resumes sessions, runs a
model, or grants Canon/Framework/Settlement authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

CONTROL_PLANE_SCHEMA = "novelforge_control_plane_v1"
QUERY_SCHEMA = "novelforge_runtime_query_v1"
SESSIONS_SCHEMA = "novelforge_runtime_sessions_projection_v1"
SESSION_SCHEMA = "novelforge_runtime_session_projection_v1"
EVENTS_SCHEMA = "novelforge_runtime_events_projection_v1"
HANDOFF_SCHEMA = "novelforge_runtime_handoff_projection_v1"
RECEIPTS_SCHEMA = "novelforge_run_receipts_projection_v1"
ERROR_SCHEMA = "novelforge_runtime_query_error_v1"
DEFAULT_DB = ".novelforge/runtime.db"
REQUIRED_TABLES = {"meta", "sessions", "events", "handoffs", "consumptions"}


class RuntimeQueryError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def finish(schema: str, **payload: Any) -> dict[str, Any]:
    out = {
        "schema": schema,
        **payload,
        "query_only": True,
        "mutation_performed": False,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "model_execution": False,
    }
    out["projection_fingerprint"] = fingerprint(out)
    return out


def _object(raw: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeQueryError("runtime_store_invalid", f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeQueryError("runtime_store_invalid", f"{label} must be an object")
    return value


@contextmanager
def readonly_connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise RuntimeQueryError("runtime_store_unavailable", "runtime store does not exist")
    try:
        conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if not REQUIRED_TABLES.issubset(tables):
            raise RuntimeQueryError("runtime_store_invalid", "runtime store is missing required Control Plane tables")
        schema_row = conn.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
        if not schema_row or schema_row["value"] != CONTROL_PLANE_SCHEMA:
            raise RuntimeQueryError("runtime_store_invalid", "runtime store schema is not supported")
        try:
            yield conn
        finally:
            conn.close()
    except RuntimeQueryError:
        raise
    except sqlite3.Error as exc:
        raise RuntimeQueryError("runtime_store_unavailable", "runtime store could not be opened read-only") from exc


def _safe_session_summary(row: sqlite3.Row) -> dict[str, Any]:
    session = _object(row["payload_json"], "session payload")
    runs = session.get("runs") if isinstance(session.get("runs"), list) else []
    checkpoints = session.get("checkpoints") if isinstance(session.get("checkpoints"), list) else []
    events = session.get("events") if isinstance(session.get("events"), list) else []
    latest_run = runs[-1] if runs and isinstance(runs[-1], dict) else None
    return {
        "session_id": row["session_id"],
        "resource_id": row["resource_id"],
        "project_id": row["project_id"],
        "parent_session_id": session.get("parent_session_id"),
        "role": row["role"],
        "task_mode": session.get("task_mode"),
        "transport": session.get("transport"),
        "backend": session.get("backend"),
        "usage_class": session.get("usage_class"),
        "status": row["status"],
        "memory_policy": session.get("memory_policy"),
        "resume_policy": session.get("resume_policy"),
        "run_count": len(runs),
        "checkpoint_count": len(checkpoints),
        "session_event_count": len(events),
        "latest_run_id": latest_run.get("run_id") if latest_run else None,
        "latest_run_status": latest_run.get("status") if latest_run else None,
        "version": row["version"],
        "payload_hash": row["payload_hash"],
        "updated_at": row["updated_at"],
    }


def list_sessions(db_path: str | Path, resource_id: str | None = None) -> dict[str, Any]:
    with readonly_connection(db_path) as conn:
        if resource_id:
            rows = conn.execute(
                """SELECT session_id,resource_id,project_id,role,status,payload_json,payload_hash,version,updated_at
                   FROM sessions WHERE resource_id=? ORDER BY updated_at DESC, session_id""",
                (resource_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT session_id,resource_id,project_id,role,status,payload_json,payload_hash,version,updated_at
                   FROM sessions ORDER BY updated_at DESC, session_id"""
            ).fetchall()
    sessions = [_safe_session_summary(row) for row in rows]
    return finish(SESSIONS_SCHEMA, filter={"resource_id": resource_id}, count=len(sessions), sessions=sessions)


def _safe_run(run: Any) -> dict[str, Any] | None:
    if not isinstance(run, dict):
        return None
    return {
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "ended_at": run.get("ended_at"),
        "usage_class": run.get("usage_class"),
        "input_artifact_fingerprints": list(run.get("input_artifact_fingerprints", [])) if isinstance(run.get("input_artifact_fingerprints"), list) else [],
        "output_artifact_fingerprints": list(run.get("output_artifact_fingerprints", [])) if isinstance(run.get("output_artifact_fingerprints"), list) else [],
    }


def _safe_checkpoint(checkpoint: Any) -> dict[str, Any] | None:
    if not isinstance(checkpoint, dict):
        return None
    return {
        "checkpoint_id": checkpoint.get("checkpoint_id"),
        "run_id": checkpoint.get("run_id"),
        "workflow_step": checkpoint.get("workflow_step"),
        "artifact_fingerprints": list(checkpoint.get("artifact_fingerprints", [])) if isinstance(checkpoint.get("artifact_fingerprints"), list) else [],
        "pending_gate": checkpoint.get("pending_gate"),
        "pending_handoff": checkpoint.get("pending_handoff"),
        "resume_policy": checkpoint.get("resume_policy"),
        "created_at": checkpoint.get("created_at"),
    }


def _safe_session_event(event: Any) -> dict[str, Any] | None:
    if not isinstance(event, dict):
        return None
    return {
        "event_id": event.get("event_id"),
        "type": event.get("type"),
        "run_id": event.get("run_id"),
        "artifact_fingerprints": list(event.get("artifact_fingerprints", [])) if isinstance(event.get("artifact_fingerprints"), list) else [],
        "created_at": event.get("created_at"),
    }


def get_session(db_path: str | Path, session_id: str) -> dict[str, Any]:
    if not session_id.strip():
        raise RuntimeQueryError("invalid_selector", "session_id is required")
    with readonly_connection(db_path) as conn:
        row = conn.execute(
            """SELECT session_id,resource_id,project_id,role,status,payload_json,payload_hash,version,updated_at
               FROM sessions WHERE session_id=?""",
            (session_id,),
        ).fetchone()
    if not row:
        raise RuntimeQueryError("session_not_found", "session was not found")
    session = _object(row["payload_json"], "session payload")
    runs = [item for item in (_safe_run(value) for value in session.get("runs", [])) if item is not None] if isinstance(session.get("runs"), list) else []
    checkpoints = [item for item in (_safe_checkpoint(value) for value in session.get("checkpoints", [])) if item is not None] if isinstance(session.get("checkpoints"), list) else []
    session_events = [item for item in (_safe_session_event(value) for value in session.get("events", [])) if item is not None] if isinstance(session.get("events"), list) else []
    context = session.get("context_policy") if isinstance(session.get("context_policy"), dict) else {}
    projection = {
        **_safe_session_summary(row),
        "context_policy": {
            "hidden_gold": context.get("hidden_gold"),
            "forbidden_context_classes": list(context.get("forbidden_context_classes", [])) if isinstance(context.get("forbidden_context_classes"), list) else [],
            "allowed_artifact_ref_count": len(context.get("allowed_artifact_refs", [])) if isinstance(context.get("allowed_artifact_refs"), list) else 0,
            "allowed_path_count": len(context.get("allowed_paths", [])) if isinstance(context.get("allowed_paths"), list) else 0,
            "authority_snapshot_present": context.get("authority_snapshot") is not None,
            "context_manifest_ref_present": context.get("context_manifest_ref") is not None,
        },
        "runs": runs,
        "checkpoints": checkpoints,
        "session_events": session_events,
        "provider_session_id_exposed": False,
        "external_session_ref_exposed": False,
        "absolute_paths_exposed": False,
    }
    return finish(SESSION_SCHEMA, session=projection)


def list_events(db_path: str | Path, *, session_id: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if session_id:
        clauses.append("session_id=?")
        params.append(session_id)
    if run_id:
        clauses.append("run_id=?")
        params.append(run_id)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with readonly_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT event_id,event_type,resource_id,session_id,run_id,handoff_id,payload_json,payload_hash,received_at
               FROM events""" + where + " ORDER BY received_at, event_id",
            params,
        ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        payload = _object(row["payload_json"], "event payload")
        source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        events.append({
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "resource_id": row["resource_id"],
            "session_id": row["session_id"],
            "run_id": row["run_id"],
            "handoff_id": row["handoff_id"],
            "authority_scope": payload.get("authority_scope"),
            "source_kind": source.get("kind"),
            "artifact_fingerprints": list(payload.get("artifact_fingerprints", [])) if isinstance(payload.get("artifact_fingerprints"), list) else [],
            "payload_hash": row["payload_hash"],
            "created_at": payload.get("created_at"),
            "received_at": row["received_at"],
        })
    return finish(EVENTS_SCHEMA, filter={"session_id": session_id, "run_id": run_id}, count=len(events), events=events)


def inspect_handoff(db_path: str | Path, handoff_id: str) -> dict[str, Any]:
    if not handoff_id.strip():
        raise RuntimeQueryError("invalid_selector", "handoff_id is required")
    with readonly_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM handoffs WHERE handoff_id=?", (handoff_id,)).fetchone()
    if not row:
        raise RuntimeQueryError("handoff_not_found", "handoff was not found")
    payload = _object(row["payload_json"], "handoff payload")
    context = payload.get("context_policy") if isinstance(payload.get("context_policy"), dict) else {}
    permissions = payload.get("permissions") if isinstance(payload.get("permissions"), dict) else {}
    return_contract = payload.get("return_contract") if isinstance(payload.get("return_contract"), dict) else {}
    handoff = {
        "handoff_id": row["handoff_id"],
        "source_session_id": row["source_session_id"],
        "target_session_class": row["target_session_class"],
        "resource_id": row["resource_id"],
        "task_mode": row["task_mode"],
        "state": row["state"],
        "artifact_fingerprints": list(payload.get("artifact_fingerprints", [])) if isinstance(payload.get("artifact_fingerprints"), list) else [],
        "artifact_ref_count": len(payload.get("artifact_refs", [])) if isinstance(payload.get("artifact_refs"), list) else 0,
        "context_policy": {
            "hidden_gold": context.get("hidden_gold"),
            "allowed_artifact_ref_count": len(context.get("allowed_artifact_refs", [])) if isinstance(context.get("allowed_artifact_refs"), list) else 0,
        },
        "permissions": {
            "canon_write": permissions.get("canon_write"),
            "framework_behavior_write": permissions.get("framework_behavior_write"),
            "durable_user_taste_write": permissions.get("durable_user_taste_write"),
            "allowed_result_scope": permissions.get("allowed_result_scope"),
        },
        "return_contract": {
            "schema": return_contract.get("schema"),
            "fingerprint_required": return_contract.get("fingerprint_required"),
        },
        "attempts": row["attempts"],
        "payload_hash": row["payload_hash"],
        "result_present": row["result_json"] is not None,
        "result_hash": row["result_hash"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "lease_owner_exposed": False,
        "result_payload_exposed": False,
    }
    return finish(HANDOFF_SCHEMA, handoff=handoff)


def get_receipts(db_path: str | Path, *, receipt_id: str | None = None, run_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    if not any(value and value.strip() for value in (receipt_id, run_id, session_id)):
        raise RuntimeQueryError("invalid_selector", "receipt_id, run_id, or session_id is required")
    clauses = ["event_type='run.receipt_recorded'"]
    params: list[Any] = []
    if run_id:
        clauses.append("run_id=?")
        params.append(run_id)
    if session_id:
        clauses.append("session_id=?")
        params.append(session_id)
    with readonly_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_json,payload_hash,received_at FROM events WHERE " + " AND ".join(clauses) + " ORDER BY received_at, event_id",
            params,
        ).fetchall()

    try:
        from run_receipt import validate_receipt
    except ImportError as exc:
        raise RuntimeQueryError("receipt_contract_unavailable", "run receipt contract could not be loaded") from exc

    receipts: list[dict[str, Any]] = []
    for row in rows:
        event = _object(row["payload_json"], "receipt event payload")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        receipt = payload.get("receipt")
        if not isinstance(receipt, dict):
            raise RuntimeQueryError("runtime_store_invalid", "run receipt event is missing receipt payload")
        errors = validate_receipt(receipt)
        if errors:
            raise RuntimeQueryError("runtime_store_invalid", "stored run receipt failed its public schema")
        if receipt_id and receipt.get("receipt_id") != receipt_id:
            continue
        receipts.append({**receipt, "event_payload_hash": row["payload_hash"], "received_at": row["received_at"]})
    return finish(
        RECEIPTS_SCHEMA,
        filter={"receipt_id": receipt_id, "run_id": run_id, "session_id": session_id},
        count=len(receipts),
        receipts=receipts,
    )


def self_test() -> dict[str, Any]:
    from control_plane import ControlPlane, EVENT_SCHEMA, HANDOFF_SCHEMA as CONTROL_HANDOFF_SCHEMA, now_iso
    from run_receipt import fixture as receipt_fixture, record_receipt

    with tempfile.TemporaryDirectory(prefix="novelforge-runtime-query-") as temp:
        root = Path(temp)
        db = root / "runtime.db"
        cp = ControlPlane(db)
        cp.init()
        session = {
            "schema": "novelforge_agent_session_v1",
            "resource_id": "BOOK-QUERY",
            "project_id": "BOOK-QUERY",
            "session_id": "SES-QUERY",
            "provider_session_id": "PRIVATE-PROVIDER-ID",
            "external_session_ref": "/private/provider/session",
            "parent_session_id": None,
            "role": "manager",
            "task_mode": "DRAFT",
            "transport": "chat_session",
            "backend": "self_test",
            "usage_class": "ordinary_chat",
            "status": "awaiting_external",
            "memory_policy": "session",
            "resume_policy": "checkpoint_revalidate",
            "context_policy": {
                "authority_snapshot": {"fingerprint": "sha256:" + "f" * 64},
                "context_manifest_ref": "/private/context.json",
                "allowed_artifact_refs": ["ART-1"],
                "allowed_paths": ["/private/path"],
                "forbidden_context_classes": ["hidden_gold"],
                "hidden_gold": "forbidden",
            },
            "runs": [{"run_id": "RUN-QUERY", "started_at": now_iso(), "ended_at": None, "status": "running", "input_artifact_fingerprints": ["sha256:" + "a" * 64], "output_artifact_fingerprints": [], "usage_class": "ordinary_chat"}],
            "checkpoints": [{"checkpoint_id": "CP-QUERY", "run_id": "RUN-QUERY", "workflow_step": "draft-frozen", "artifact_fingerprints": ["sha256:" + "a" * 64], "pending_gate": "semantic", "pending_handoff": "HO-QUERY", "resume_policy": "checkpoint_revalidate", "created_at": now_iso()}],
            "events": [{"event_id": "EV-SESSION-QUERY", "type": "session.created", "run_id": None, "artifact_refs": ["/private/ref"], "artifact_fingerprints": [], "created_at": now_iso(), "detail": "/private/detail"}],
            "provenance": {"runtime": "session_runtime.py", "version": "2", "durable_store": "control_plane"},
        }
        cp.put_session(session, expected_version=0)
        cp.ingest_event({
            "schema": EVENT_SCHEMA,
            "event_id": "EV-QUERY",
            "event_type": "semantic.requested",
            "source": {"kind": "self_test", "actor": "private-actor", "external_ref": "/private/event"},
            "resource_id": "BOOK-QUERY",
            "session_id": "SES-QUERY",
            "run_id": "RUN-QUERY",
            "handoff_id": "HO-QUERY",
            "authority_scope": "request",
            "idempotency_key": "runtime-query-self-test",
            "artifact_fingerprints": ["sha256:" + "a" * 64],
            "created_at": now_iso(),
            "payload": {"private": "/private/event/payload"},
        })
        handoff = {
            "schema": CONTROL_HANDOFF_SCHEMA,
            "handoff_id": "HO-QUERY",
            "source_session_id": "SES-QUERY",
            "target_session_class": "semantic_reviewer",
            "resource_id": "BOOK-QUERY",
            "task_mode": "DRAFT",
            "artifact_refs": ["/private/artifact"],
            "artifact_fingerprints": ["sha256:" + "a" * 64],
            "instructions_ref": "/private/instructions",
            "context_policy": {"hidden_gold": "forbidden", "allowed_artifact_refs": ["ART-1"]},
            "permissions": {"canon_write": False, "framework_behavior_write": False, "durable_user_taste_write": False, "allowed_result_scope": "observation"},
            "return_contract": {"schema": "semantic_worker_result", "fingerprint_required": True, "private": "/private/return"},
        }
        cp.submit_handoff(handoff)
        claim = cp.claim_handoff("PRIVATE-WORKER", target_session_class="semantic_reviewer", lease_seconds=60)
        assert claim is not None
        cp.complete_handoff("HO-QUERY", "PRIVATE-WORKER", {"private_result": "/private/result"})

        receipt = receipt_fixture()
        receipt["resource_id"] = "BOOK-QUERY"
        receipt["session_id"] = "SES-QUERY"
        receipt["run_id"] = "RUN-QUERY"
        record_receipt(db, receipt, source_kind="self_test", actor="runtime_query.py")

        before = db.stat().st_mtime_ns
        sessions = list_sessions(db)
        session_view = get_session(db, "SES-QUERY")
        events = list_events(db, session_id="SES-QUERY")
        handoff_view = inspect_handoff(db, "HO-QUERY")
        receipts = get_receipts(db, run_id="RUN-QUERY")
        after = db.stat().st_mtime_ns

        serialized = canonical({"sessions": sessions, "session": session_view, "events": events, "handoff": handoff_view, "receipts": receipts})
        safe_projection = all(secret not in serialized for secret in ("PRIVATE-PROVIDER-ID", "/private/path", "/private/detail", "PRIVATE-WORKER", "/private/result", "/private/instructions"))
        schema_checks = {
            "sessions": sessions["schema"] == SESSIONS_SCHEMA,
            "session": session_view["schema"] == SESSION_SCHEMA,
            "events": events["schema"] == EVENTS_SCHEMA,
            "handoff": handoff_view["schema"] == HANDOFF_SCHEMA,
            "receipts": receipts["schema"] == RECEIPTS_SCHEMA,
        }
        schemas_ok = all(schema_checks.values()) and receipts["count"] == 1
        no_write_on_read = before == after

        missing_db = root / "missing" / "runtime.db"
        unavailable_ok = False
        try:
            list_sessions(missing_db)
        except RuntimeQueryError as exc:
            unavailable_ok = exc.code == "runtime_store_unavailable" and not missing_db.exists() and not missing_db.parent.exists()

    ok = schemas_ok and safe_projection and no_write_on_read and unavailable_ok
    return {
        "runtime_query_contract": "PASS" if ok else "FAIL",
        "schema": QUERY_SCHEMA,
        "projection_schema_checks": schema_checks,
        "side_effect_free_missing_store": unavailable_ok,
        "read_does_not_modify_store": no_write_on_read,
        "safe_projection": safe_projection,
        "receipt_retrieval": receipts["count"] == 1,
        "authority": False,
        "model_execution": False,
    }


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge side-effect-free runtime query boundary")
    parser.add_argument("--db", default=os.getenv("NOVELFORGE_DB", DEFAULT_DB))
    sub = parser.add_subparsers(dest="command", required=True)
    sessions = sub.add_parser("session-list"); sessions.add_argument("--resource-id")
    session = sub.add_parser("session-get"); session.add_argument("--session-id", required=True)
    events = sub.add_parser("event-list"); events.add_argument("--session-id"); events.add_argument("--run-id")
    handoff = sub.add_parser("handoff-get"); handoff.add_argument("--handoff-id", required=True)
    receipt = sub.add_parser("receipt-get"); receipt.add_argument("--receipt-id"); receipt.add_argument("--run-id"); receipt.add_argument("--session-id")
    sub.add_parser("self-test")
    args = parser.parse_args()

    try:
        if args.command == "session-list": value = list_sessions(args.db, args.resource_id)
        elif args.command == "session-get": value = get_session(args.db, args.session_id)
        elif args.command == "event-list": value = list_events(args.db, session_id=args.session_id, run_id=args.run_id)
        elif args.command == "handoff-get": value = inspect_handoff(args.db, args.handoff_id)
        elif args.command == "receipt-get": value = get_receipts(args.db, receipt_id=args.receipt_id, run_id=args.run_id, session_id=args.session_id)
        else:
            value = self_test()
            dump(value)
            return 0 if value["runtime_query_contract"] == "PASS" else 1
        dump(value)
        return 0
    except RuntimeQueryError as exc:
        dump({"schema": ERROR_SCHEMA, "code": exc.code, "message": exc.message, "mutation_performed": False, "authority": False})
        return 2
    except Exception as exc:
        dump({"schema": ERROR_SCHEMA, "code": "runtime_query_internal_error", "message": type(exc).__name__, "mutation_performed": False, "authority": False})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
