#!/usr/bin/env python3
"""Execute an explicitly human-authorized Quillframe session termination.

The command terminates the Session and, when present, its single active latest
Run as one exact runtime-state CAS. It performs no model execution and cannot
write Project, Canon, Framework, or Settlement state.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONTROL_ROOT = HERE.parent / "control_plane"
for candidate in (HERE, CONTROL_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import runtime_command_executor as receipt_runtime  # noqa: E402
import session_runtime  # noqa: E402
import terminate_authorization  # noqa: E402
import terminate_command  # noqa: E402
import terminate_preflight  # noqa: E402
from control_plane import ControlPlane  # noqa: E402

RESULT_SCHEMA = receipt_runtime.RESULT_SCHEMA
RECEIPT_SCHEMA = receipt_runtime.RECEIPT_SCHEMA
DEFAULT_DB = receipt_runtime.DEFAULT_DB


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def _duplicate_or_conflict(row: sqlite3.Row, receipt: dict[str, Any], command: dict[str, Any], authorization: dict[str, Any]) -> dict[str, Any]:
    command_fp = terminate_command.fingerprint(command)
    intent_fp = terminate_command.fingerprint(terminate_command.intent_payload(command))
    authorization_fp = terminate_command.fingerprint(authorization)
    exact = (
        row["command_fingerprint"] == command_fp
        and row["intent_fingerprint"] == intent_fp
        and row["authorization_fingerprint"] == authorization_fp
        and row["command_id"] == command.get("command_id")
        and row["operation"] == "session.terminate"
    )
    if exact:
        return receipt_runtime._result(
            "duplicate",
            receipt=receipt,
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
            replayed_receipt=True,
        )
    return receipt_runtime._result(
        "conflict",
        failure_class="idempotency_conflict",
        errors=["idempotency_key_or_command_id_already_bound_to_different_command"],
        command_fingerprint=command_fp,
        intent_fingerprint=intent_fp,
        authorization_fingerprint=authorization_fp,
    )


def execute(command: dict[str, Any], authorization: dict[str, Any], *, db_path: Path, project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    db_path = db_path.resolve()
    command_fp = terminate_command.fingerprint(command)
    intent_fp = terminate_command.fingerprint(terminate_command.intent_payload(command))
    authorization_fp = terminate_command.fingerprint(authorization)

    command_shape = terminate_command.shape_errors(command)
    auth_shape = terminate_authorization.shape_errors(authorization)
    if command_shape or auth_shape:
        return receipt_runtime._result(
            "rejected", failure_class="typed_contract", errors=[*command_shape, *auth_shape],
            command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
        )
    if authorization.get("decision") != "allow":
        return receipt_runtime._result(
            "rejected", failure_class="authorization", errors=["authorization_decision_not_allow"],
            command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
        )
    if authorization.get("command_fingerprint") != command_fp or authorization.get("intent_fingerprint") != intent_fp:
        return receipt_runtime._result(
            "rejected", failure_class="authorization", errors=["authorization_binding_mismatch"],
            command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
        )

    try:
        conn = receipt_runtime._connect_readonly(db_path)
        try:
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='command_receipts'").fetchone()
            prior = receipt_runtime._lookup_receipt(conn, idempotency_key=command["idempotency_key"]) if exists else None
        finally:
            conn.close()
    except (OSError, sqlite3.Error, ValueError) as exc:
        return receipt_runtime._result(
            "rejected", failure_class="runtime_store", errors=[str(exc)],
            command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
        )
    if prior:
        return _duplicate_or_conflict(prior[0], prior[1], command, authorization)

    before = command["expected_before_state"]
    fresh = terminate_preflight.inspect(
        db_path=db_path,
        project_root=project_root,
        session_id=command["session_id"],
        expected_session_version=before["session_version"],
    )
    command_validation = terminate_command.validate(command, fresh)
    if command_validation.get("valid") is not True:
        return receipt_runtime._result(
            "rejected", failure_class="precondition", errors=list(command_validation.get("errors", [])), preflight=fresh,
            command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
        )
    auth_validation = terminate_authorization.validate(authorization, command, fresh)
    if auth_validation.get("authorization_granted") is not True:
        return receipt_runtime._result(
            "rejected", failure_class="authorization", errors=list(auth_validation.get("errors", [])) or ["authorization_not_granted"], preflight=fresh,
            command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
        )

    conn = receipt_runtime._connect_write(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        receipt_runtime._ensure_receipt_table(conn)
        prior = receipt_runtime._lookup_receipt(conn, idempotency_key=command["idempotency_key"])
        if prior:
            conn.execute("COMMIT")
            return _duplicate_or_conflict(prior[0], prior[1], command, authorization)

        row = conn.execute(
            "SELECT payload_json,payload_hash,version,status FROM sessions WHERE session_id=?",
            (command["session_id"],),
        ).fetchone()
        if not row:
            conn.execute("ROLLBACK")
            return receipt_runtime._result(
                "conflict", failure_class="before_state_conflict", errors=["session_not_found_at_commit"], preflight=fresh,
                command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
            )
        if (
            row["version"] != before["session_version"]
            or row["payload_hash"] != before["session_payload_hash"]
            or row["status"] != before["session_status"]
        ):
            conn.execute("ROLLBACK")
            return receipt_runtime._result(
                "conflict", failure_class="before_state_conflict", errors=["session_compare_and_swap_failed"], preflight=fresh,
                command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
            )

        session = json.loads(row["payload_json"])
        if not isinstance(session, dict):
            raise ValueError("durable session payload must be an object")
        run_id = before.get("run_id")
        if run_id:
            transitioned = session_runtime.terminate_run(
                session,
                run_id,
                detail=f"runtime-command:{command['command_id']}",
            )
        else:
            transitioned = session_runtime.transition(
                session,
                "terminated",
                detail=f"runtime-command:{command['command_id']}",
            )

        after_run = next((run for run in transitioned.get("runs", []) if isinstance(run, dict) and run.get("run_id") == run_id), None) if run_id else None
        after_body = receipt_runtime.canonical(transitioned)
        after_hash = receipt_runtime.fingerprint(transitioned)
        after_version = int(row["version"]) + 1
        ts = receipt_runtime.now_iso()

        event_id = "EV-TERMINATE-" + terminate_command.fingerprint(command)[7:31]
        event = {
            "schema": "quillframe_event_v1",
            "event_id": event_id,
            "event_type": "session.terminate_requested",
            "source": {"kind": "runtime_command_executor", "actor": "runtime-command"},
            "resource_id": session["resource_id"],
            "session_id": command["session_id"],
            "run_id": run_id,
            "handoff_id": None,
            "authority_scope": "request",
            "idempotency_key": "runtime-command:" + command["idempotency_key"],
            "artifact_fingerprints": [],
            "created_at": ts,
            "payload": {
                "command_id": command["command_id"],
                "command_fingerprint": command_fp,
                "intent_fingerprint": intent_fp,
                "authorization_fingerprint": authorization_fp,
                "preflight_fingerprint": fresh["result_fingerprint"],
                "before_session_status": before["session_status"],
                "before_run_status": before.get("run_status"),
            },
        }
        ControlPlane.validate_event(event)
        event_hash = receipt_runtime.fingerprint(event)

        updated = conn.execute(
            """UPDATE sessions SET status=?, payload_json=?, payload_hash=?, version=?, updated_at=?
               WHERE session_id=? AND version=? AND payload_hash=? AND status=?""",
            (
                "terminated", after_body, after_hash, after_version, ts, command["session_id"],
                before["session_version"], before["session_payload_hash"], before["session_status"],
            ),
        )
        if updated.rowcount != 1:
            conn.execute("ROLLBACK")
            return receipt_runtime._result(
                "conflict", failure_class="before_state_conflict", errors=["session_compare_and_swap_failed"], preflight=fresh,
                command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
            )

        existing_event = conn.execute("SELECT event_id,payload_hash FROM events WHERE idempotency_key=?", (event["idempotency_key"],)).fetchone()
        if existing_event:
            if existing_event["event_id"] != event_id or existing_event["payload_hash"] != event_hash:
                conn.execute("ROLLBACK")
                return receipt_runtime._result(
                    "conflict", failure_class="idempotency_conflict", errors=["terminate_event_idempotency_conflict"], preflight=fresh,
                    command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
                )
        else:
            conn.execute(
                """INSERT INTO events(event_id,event_type,resource_id,session_id,run_id,handoff_id,
                   idempotency_key,payload_json,payload_hash,received_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    event_id, event["event_type"], event["resource_id"], event["session_id"], event["run_id"], None,
                    event["idempotency_key"], receipt_runtime.canonical(event), event_hash, ts,
                ),
            )

        receipt = receipt_runtime._finish_receipt({
            "schema": RECEIPT_SCHEMA,
            "command_id": command["command_id"],
            "operation": "session.terminate",
            "session_id": command["session_id"],
            "idempotency_key": command["idempotency_key"],
            "command_fingerprint": command_fp,
            "intent_fingerprint": intent_fp,
            "authorization_fingerprint": authorization_fp,
            "authorization_source_kind": authorization.get("source", {}).get("kind"),
            "preflight_fingerprint": fresh["result_fingerprint"],
            "before_state": {
                "session_version": before["session_version"],
                "session_payload_hash": before["session_payload_hash"],
                "session_status": before["session_status"],
                "checkpoint_id": None,
                "run_id": before.get("run_id"),
                "run_status": before.get("run_status"),
                "run_ended_at": fresh.get("run", {}).get("ended_at") if isinstance(fresh.get("run"), dict) else None,
            },
            "after_state": {
                "session_version": after_version,
                "session_payload_hash": after_hash,
                "session_status": "terminated",
                "checkpoint_id": None,
                "run_id": after_run.get("run_id") if after_run else None,
                "run_status": after_run.get("status") if after_run else None,
                "run_ended_at": after_run.get("ended_at") if after_run else None,
            },
            "event": {"event_id": event_id, "event_fingerprint": event_hash},
            "applied_at": ts,
            "runtime_mutation_performed": True,
            "model_execution": False,
            "authority": False,
            "project_write_authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
            "settlement_authority": False,
        })
        conn.execute(
            """INSERT INTO command_receipts(command_id,operation,session_id,idempotency_key,intent_fingerprint,
               command_fingerprint,authorization_fingerprint,receipt_json,receipt_hash,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                command["command_id"], "session.terminate", command["session_id"], command["idempotency_key"],
                intent_fp, command_fp, authorization_fp, receipt_runtime.canonical(receipt), receipt["receipt_fingerprint"], ts,
            ),
        )
        conn.execute("COMMIT")
        return receipt_runtime._result(
            "applied", receipt=receipt, preflight=fresh,
            command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
        )
    except Exception as exc:
        try:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        return receipt_runtime._result(
            "failed", failure_class="executor_internal", errors=[f"{type(exc).__name__}: {exc}"],
            command_fingerprint=command_fp, intent_fingerprint=intent_fp, authorization_fingerprint=authorization_fp,
        )
    finally:
        conn.close()


def execute_terminate(*, db_path: Path, project_root: Path, session_id: str, expected_session_version: int, authorization_ref: str, command_id: str | None = None) -> dict[str, Any]:
    preflight = terminate_preflight.inspect(
        db_path=db_path,
        project_root=project_root,
        session_id=session_id,
        expected_session_version=expected_session_version,
    )
    if preflight.get("ready") is not True:
        return receipt_runtime._result(
            "rejected", failure_class="preflight", errors=list(preflight.get("blockers", [])), preflight=preflight,
        )
    command = terminate_command.make_command(
        preflight=preflight,
        command_id=command_id or "CMD-TERMINATE-" + uuid.uuid4().hex,
    )
    authorization = terminate_authorization.make_authorization(
        command=command,
        preflight=preflight,
        decision="allow",
        source_kind="user",
        evidence_ref=authorization_ref,
        authorization_id="AUTH-TERMINATE-" + uuid.uuid4().hex,
        issued_at=receipt_runtime.now_iso(),
    )
    return execute(command, authorization, db_path=db_path, project_root=project_root)


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="quillframe-terminate-executor-") as tmp:
        root = Path(tmp)
        (root / ".quillframe").mkdir()
        (root / "quillframe.toml").write_text(
            'schema="quillframe_project_v1_0"\nid="BOOK-STOP"\ntitle="Stop"\nlanguage="en"\n', encoding="utf-8")

        db = root / ".quillframe" / "runtime.db"
        cp = ControlPlane(db); cp.init()
        session = session_runtime.new_session("BOOK-STOP", "manager", "chat_session", "self_test", project_id="BOOK-STOP", usage_class="ordinary_chat", memory_policy="session", resume_policy="checkpoint_revalidate")
        session = session_runtime.start_run(session, "RUN-STOP", [])
        put = cp.put_session(session, expected_version=0)
        preflight = terminate_preflight.inspect(db_path=db, project_root=root, session_id=session["session_id"], expected_session_version=put["version"])
        command = terminate_command.make_command(preflight=preflight, command_id="CMD-STOP-1")
        deny = terminate_authorization.make_authorization(command=command, preflight=preflight, decision="deny", source_kind="user", evidence_ref="urn:quillframe:self-test:stop", authorization_id="AUTH-STOP-DENY", issued_at=receipt_runtime.now_iso())
        allow = terminate_authorization.make_authorization(command=command, preflight=preflight, decision="allow", source_kind="user", evidence_ref="urn:quillframe:self-test:stop", authorization_id="AUTH-STOP-ALLOW", issued_at=receipt_runtime.now_iso())

        denied = execute(command, deny, db_path=db, project_root=root)
        after_deny = cp.get_session(session["session_id"])
        applied = execute(command, allow, db_path=db, project_root=root)
        after_apply = cp.get_session(session["session_id"])
        duplicate = execute(command, allow, db_path=db, project_root=root)
        receipts = receipt_runtime.get_receipts(db, command_id="CMD-STOP-1")
        tampered = json.loads(json.dumps(allow)); tampered["authorization_id"] = "AUTH-STOP-OTHER"
        conflict = execute(command, tampered, db_path=db, project_root=root)

        stopped_run = after_apply["session"]["runs"][-1] if after_apply else {}
        ok = (
            preflight["ready"] is True
            and denied["status"] == "rejected" and denied["runtime_mutation_performed"] is False
            and after_deny is not None and after_deny["version"] == 1 and after_deny["session"]["status"] == "running"
            and applied["status"] == "applied" and applied["runtime_mutation_performed"] is True
            and after_apply is not None and after_apply["version"] == 2 and after_apply["session"]["status"] == "terminated"
            and stopped_run.get("status") == "terminated" and isinstance(stopped_run.get("ended_at"), str)
            and applied["receipt"]["operation"] == "session.terminate"
            and applied["receipt"]["after_state"]["run_status"] == "terminated"
            and duplicate["status"] == "duplicate" and duplicate["replayed_receipt"] is True
            and receipts["count"] == 1
            and conflict["status"] == "conflict" and conflict["failure_class"] == "idempotency_conflict"
            and applied["receipt"]["model_execution"] is False and applied["receipt"]["authority"] is False
        )
        dump({
            "session_terminate_executor_contract": "PASS" if ok else "FAIL",
            "terminate_applied": applied["status"] == "applied",
            "active_run_closed": stopped_run.get("status") == "terminated",
            "cas_version_advanced_once": bool(after_apply and after_apply["version"] == 2),
            "denied_did_not_mutate": bool(after_deny and after_deny["version"] == 1),
            "idempotent_retry_replayed_receipt": duplicate["status"] == "duplicate",
            "conflicting_retry_rejected": conflict["status"] == "conflict",
            "durable_receipt_query": receipts["count"] == 1,
            "model_execution": False,
            "authority": False,
        })
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe guarded session terminate executor")
    parser.add_argument("--db", default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)
    execute_p = sub.add_parser("execute")
    execute_p.add_argument("--project-root", required=True)
    execute_p.add_argument("--command", required=True)
    execute_p.add_argument("--authorization", required=True)
    shortcut = sub.add_parser("execute-terminate")
    shortcut.add_argument("--project-root", required=True)
    shortcut.add_argument("--session-id", required=True)
    shortcut.add_argument("--expected-session-version", required=True, type=int)
    shortcut.add_argument("--authorization-ref", required=True)
    shortcut.add_argument("--command-id")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test": return self_test()
    if args.command == "execute":
        value = execute(load_object(Path(args.command)), load_object(Path(args.authorization)), db_path=Path(args.db), project_root=Path(args.project_root))
    else:
        value = execute_terminate(
            db_path=Path(args.db), project_root=Path(args.project_root), session_id=args.session_id,
            expected_session_version=args.expected_session_version, authorization_ref=args.authorization_ref, command_id=args.command_id,
        )
    dump(value)
    return 0 if value.get("status") in {"applied", "duplicate"} else (2 if value.get("status") in {"rejected", "conflict"} else 1)


if __name__ == "__main__":
    raise SystemExit(main())
