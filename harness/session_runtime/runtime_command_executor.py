#!/usr/bin/env python3
"""Execute explicitly authorized Quillframe runtime commands.

V1 exposes one mutation only: ``session.resume``. The executor consumes the
public resume preflight, typed resume command candidate, and runtime command
authorization contracts. It revalidates current Project/runtime evidence, uses
an exact session version + payload-hash compare-and-swap, records a durable
idempotent command receipt, and never runs a model or grants Project/Canon/
Framework/Settlement authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONTROL_ROOT = HERE.parent / "control_plane"
for candidate in (HERE, CONTROL_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import resume_command  # noqa: E402
import resume_preflight  # noqa: E402
import runtime_command_authorization as command_authorization  # noqa: E402
import session_runtime  # noqa: E402
from control_plane import ControlPlane  # noqa: E402

RECEIPT_SCHEMA = "quillframe_runtime_command_receipt_v1"
RESULT_SCHEMA = "quillframe_runtime_command_execution_result_v1"
QUERY_SCHEMA = "quillframe_runtime_command_receipt_projection_v1"
DEFAULT_DB = ".quillframe/runtime.db"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def _receipt_basis(receipt: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in receipt.items() if key != "receipt_fingerprint"}


def _finish_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    out = dict(receipt)
    out["receipt_fingerprint"] = fingerprint(_receipt_basis(out))
    return out


def _result(
    status: str,
    *,
    failure_class: str | None = None,
    errors: list[str] | None = None,
    receipt: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    command_fingerprint: str | None = None,
    intent_fingerprint: str | None = None,
    authorization_fingerprint: str | None = None,
    replayed_receipt: bool = False,
) -> dict[str, Any]:
    out = {
        "schema": RESULT_SCHEMA,
        "status": status,
        "failure_class": failure_class,
        "errors": list(dict.fromkeys(errors or [])),
        "receipt": receipt,
        "preflight": preflight,
        "command_fingerprint": command_fingerprint,
        "intent_fingerprint": intent_fingerprint,
        "authorization_fingerprint": authorization_fingerprint,
        "replayed_receipt": replayed_receipt,
        "runtime_mutation_performed": status == "applied",
        "model_execution": False,
        "authority": False,
        "project_write_authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    out["result_fingerprint"] = fingerprint(out)
    return out


def _connect_write(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise ValueError("runtime store does not exist")
    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise ValueError("runtime store does not exist")
    conn = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _ensure_receipt_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS command_receipts (
            command_id TEXT PRIMARY KEY,
            operation TEXT NOT NULL,
            session_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            intent_fingerprint TEXT NOT NULL,
            command_fingerprint TEXT NOT NULL,
            authorization_fingerprint TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            receipt_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_command_receipts_session ON command_receipts(session_id, created_at)"
    )


def _decode_receipt(row: sqlite3.Row) -> dict[str, Any]:
    receipt = json.loads(row["receipt_json"])
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("stored runtime command receipt is invalid")
    if fingerprint(_receipt_basis(receipt)) != receipt.get("receipt_fingerprint"):
        raise ValueError("stored runtime command receipt fingerprint mismatch")
    if row["receipt_hash"] != receipt["receipt_fingerprint"]:
        raise ValueError("stored runtime command receipt hash mismatch")
    return receipt


def _lookup_receipt(
    conn: sqlite3.Connection,
    *,
    command_id: str | None = None,
    idempotency_key: str | None = None,
) -> tuple[sqlite3.Row, dict[str, Any]] | None:
    if command_id:
        row = conn.execute("SELECT * FROM command_receipts WHERE command_id=?", (command_id,)).fetchone()
    elif idempotency_key:
        row = conn.execute("SELECT * FROM command_receipts WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    else:
        raise ValueError("command_id or idempotency_key is required")
    return (row, _decode_receipt(row)) if row else None


def get_receipts(
    db_path: Path,
    *,
    command_id: str | None = None,
    idempotency_key: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    if not any((command_id, idempotency_key, session_id)):
        raise ValueError("command_id, idempotency_key, or session_id is required")
    conn = _connect_readonly(db_path)
    try:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='command_receipts'").fetchone()
        if not exists:
            rows: list[sqlite3.Row] = []
        elif command_id:
            rows = conn.execute("SELECT * FROM command_receipts WHERE command_id=?", (command_id,)).fetchall()
        elif idempotency_key:
            rows = conn.execute("SELECT * FROM command_receipts WHERE idempotency_key=?", (idempotency_key,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM command_receipts WHERE session_id=? ORDER BY created_at, command_id",
                (session_id,),
            ).fetchall()
        receipts = [_decode_receipt(row) for row in rows]
    finally:
        conn.close()
    out = {
        "schema": QUERY_SCHEMA,
        "filter": {"command_id": command_id, "idempotency_key": idempotency_key, "session_id": session_id},
        "count": len(receipts),
        "receipts": receipts,
        "query_only": True,
        "mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "project_write_authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    out["projection_fingerprint"] = fingerprint(out)
    return out


def _duplicate_or_conflict(
    row: sqlite3.Row,
    receipt: dict[str, Any],
    command: dict[str, Any],
    authorization: dict[str, Any],
) -> dict[str, Any]:
    command_fp = fingerprint(command)
    intent_fp = fingerprint(resume_command.intent_payload(command))
    authorization_fp = fingerprint(authorization)
    exact = (
        row["command_fingerprint"] == command_fp
        and row["intent_fingerprint"] == intent_fp
        and row["authorization_fingerprint"] == authorization_fp
        and row["command_id"] == command.get("command_id")
    )
    if exact:
        return _result(
            "duplicate",
            receipt=receipt,
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
            replayed_receipt=True,
        )
    return _result(
        "conflict",
        failure_class="idempotency_conflict",
        errors=["idempotency_key_or_command_id_already_bound_to_different_command"],
        command_fingerprint=command_fp,
        intent_fingerprint=intent_fp,
        authorization_fingerprint=authorization_fp,
    )


def execute(
    command: dict[str, Any],
    authorization: dict[str, Any],
    *,
    db_path: Path,
    project_root: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    db_path = db_path.resolve()

    command_shape = resume_command.shape_errors(command)
    authorization_shape = command_authorization.shape_errors(authorization)
    command_fp = fingerprint(command)
    intent_fp = fingerprint(resume_command.intent_payload(command))
    authorization_fp = fingerprint(authorization)
    if command_shape or authorization_shape:
        return _result(
            "rejected",
            failure_class="typed_contract",
            errors=[*command_shape, *authorization_shape],
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )
    if authorization.get("decision") != "allow":
        return _result(
            "rejected",
            failure_class="authorization",
            errors=["authorization_decision_not_allow"],
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )
    if authorization.get("command_fingerprint") != command_fp or authorization.get("intent_fingerprint") != intent_fp:
        return _result(
            "rejected",
            failure_class="authorization",
            errors=["authorization_binding_mismatch"],
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )

    # Successful retries are answered from the exact durable receipt before a
    # fresh preflight, because the successful mutation intentionally makes the
    # old resumable before-state no longer current.
    try:
        conn = _connect_readonly(db_path)
        try:
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='command_receipts'").fetchone()
            prior = _lookup_receipt(conn, idempotency_key=command["idempotency_key"]) if exists else None
        finally:
            conn.close()
    except (OSError, sqlite3.Error, ValueError) as exc:
        return _result(
            "rejected",
            failure_class="runtime_store",
            errors=[str(exc)],
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )
    if prior:
        return _duplicate_or_conflict(prior[0], prior[1], command, authorization)

    binding = command.get("preflight") if isinstance(command.get("preflight"), dict) else {}
    evidence_path = resume_command.project_file(project_root, binding.get("authority_evidence_ref"))
    if evidence_path is None:
        return _result(
            "rejected",
            failure_class="precondition",
            errors=["authority_evidence_scope_invalid"],
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )
    before = command["expected_before_state"]
    fresh = resume_preflight.inspect(
        db_path=db_path,
        project_root=project_root,
        session_id=command["session_id"],
        checkpoint_id=before["checkpoint_id"],
        expected_session_version=before["session_version"],
        authority_evidence_path=evidence_path,
    )
    command_validation = resume_command.validate(command, fresh, project_root)
    if command_validation.get("valid") is not True:
        return _result(
            "rejected",
            failure_class="precondition",
            errors=list(command_validation.get("errors", [])),
            preflight=fresh,
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )
    authorization_validation = command_authorization.validate(authorization, command, fresh, project_root)
    if authorization_validation.get("authorization_granted") is not True:
        return _result(
            "rejected",
            failure_class="authorization",
            errors=list(authorization_validation.get("errors", [])) or ["authorization_not_granted"],
            preflight=fresh,
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )

    conn = _connect_write(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_receipt_table(conn)
        prior = _lookup_receipt(conn, idempotency_key=command["idempotency_key"])
        if prior:
            conn.execute("COMMIT")
            return _duplicate_or_conflict(prior[0], prior[1], command, authorization)

        row = conn.execute(
            "SELECT payload_json,payload_hash,version,status FROM sessions WHERE session_id=?",
            (command["session_id"],),
        ).fetchone()
        if not row:
            conn.execute("ROLLBACK")
            return _result(
                "conflict",
                failure_class="before_state_conflict",
                errors=["session_not_found_at_commit"],
                preflight=fresh,
                command_fingerprint=command_fp,
                intent_fingerprint=intent_fp,
                authorization_fingerprint=authorization_fp,
            )
        if row["version"] != before["session_version"] or row["payload_hash"] != before["session_payload_hash"]:
            conn.execute("ROLLBACK")
            return _result(
                "conflict",
                failure_class="before_state_conflict",
                errors=["session_compare_and_swap_failed"],
                preflight=fresh,
                command_fingerprint=command_fp,
                intent_fingerprint=intent_fp,
                authorization_fingerprint=authorization_fp,
            )

        session = json.loads(row["payload_json"])
        if not isinstance(session, dict):
            raise ValueError("durable session payload must be an object")
        transitioned = session_runtime.transition(
            session,
            "running",
            detail=f"runtime-command:{command['command_id']}:{before['checkpoint_id']}",
        )
        after_body = canonical(transitioned)
        after_hash = fingerprint(transitioned)
        after_version = int(row["version"]) + 1
        ts = now_iso()

        event_id = "EV-RESUME-" + hashlib.sha256(command["command_id"].encode("utf-8")).hexdigest()[:24]
        event = {
            "schema": "quillframe_event_v1",
            "event_id": event_id,
            "event_type": "session.resume_requested",
            "source": {"kind": "runtime_command_executor", "actor": "runtime-command"},
            "resource_id": session["resource_id"],
            "session_id": command["session_id"],
            "run_id": fresh.get("checkpoint", {}).get("run_id"),
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
                "preflight_fingerprint": fingerprint(fresh),
                "checkpoint_id": before["checkpoint_id"],
            },
        }
        ControlPlane.validate_event(event)
        event_hash = fingerprint(event)

        updated = conn.execute(
            """UPDATE sessions SET status=?, payload_json=?, payload_hash=?, version=?, updated_at=?
               WHERE session_id=? AND version=? AND payload_hash=?""",
            (
                "running",
                after_body,
                after_hash,
                after_version,
                ts,
                command["session_id"],
                before["session_version"],
                before["session_payload_hash"],
            ),
        )
        if updated.rowcount != 1:
            conn.execute("ROLLBACK")
            return _result(
                "conflict",
                failure_class="before_state_conflict",
                errors=["session_compare_and_swap_failed"],
                preflight=fresh,
                command_fingerprint=command_fp,
                intent_fingerprint=intent_fp,
                authorization_fingerprint=authorization_fp,
            )

        existing_event = conn.execute(
            "SELECT event_id,payload_hash FROM events WHERE idempotency_key=?",
            (event["idempotency_key"],),
        ).fetchone()
        if existing_event:
            if existing_event["event_id"] != event_id or existing_event["payload_hash"] != event_hash:
                conn.execute("ROLLBACK")
                return _result(
                    "conflict",
                    failure_class="idempotency_conflict",
                    errors=["resume_event_idempotency_conflict"],
                    preflight=fresh,
                    command_fingerprint=command_fp,
                    intent_fingerprint=intent_fp,
                    authorization_fingerprint=authorization_fp,
                )
        else:
            conn.execute(
                """INSERT INTO events(event_id,event_type,resource_id,session_id,run_id,handoff_id,
                   idempotency_key,payload_json,payload_hash,received_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    event_id,
                    event["event_type"],
                    event["resource_id"],
                    event["session_id"],
                    event["run_id"],
                    None,
                    event["idempotency_key"],
                    canonical(event),
                    event_hash,
                    ts,
                ),
            )

        receipt = _finish_receipt({
            "schema": RECEIPT_SCHEMA,
            "command_id": command["command_id"],
            "operation": "session.resume",
            "session_id": command["session_id"],
            "idempotency_key": command["idempotency_key"],
            "command_fingerprint": command_fp,
            "intent_fingerprint": intent_fp,
            "authorization_fingerprint": authorization_fp,
            "authorization_source_kind": authorization.get("source", {}).get("kind"),
            "preflight_fingerprint": fingerprint(fresh),
            "before_state": {
                "session_version": before["session_version"],
                "session_payload_hash": before["session_payload_hash"],
                "session_status": row["status"],
                "checkpoint_id": before["checkpoint_id"],
            },
            "after_state": {
                "session_version": after_version,
                "session_payload_hash": after_hash,
                "session_status": "running",
                "checkpoint_id": before["checkpoint_id"],
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
                command["command_id"],
                "session.resume",
                command["session_id"],
                command["idempotency_key"],
                intent_fp,
                command_fp,
                authorization_fp,
                canonical(receipt),
                receipt["receipt_fingerprint"],
                ts,
            ),
        )
        conn.execute("COMMIT")
        return _result(
            "applied",
            receipt=receipt,
            preflight=fresh,
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )
    except Exception as exc:
        try:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        return _result(
            "failed",
            failure_class="executor_internal",
            errors=[f"{type(exc).__name__}: {exc}"],
            command_fingerprint=command_fp,
            intent_fingerprint=intent_fp,
            authorization_fingerprint=authorization_fp,
        )
    finally:
        conn.close()


def execute_resume(
    *,
    db_path: Path,
    project_root: Path,
    session_id: str,
    checkpoint_id: str,
    expected_session_version: int,
    authority_evidence_ref: str,
    authorization_source: str,
    authorization_ref: str,
    command_id: str | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    evidence_path = resume_command.project_file(project_root, authority_evidence_ref)
    if evidence_path is None:
        return _result("rejected", failure_class="precondition", errors=["authority_evidence_scope_invalid"])
    initial = resume_preflight.inspect(
        db_path=db_path,
        project_root=project_root,
        session_id=session_id,
        checkpoint_id=checkpoint_id,
        expected_session_version=expected_session_version,
        authority_evidence_path=evidence_path,
    )
    if initial.get("ready") is not True:
        return _result(
            "rejected",
            failure_class="preflight",
            errors=list(initial.get("blockers", [])) + list(initial.get("unresolved", [])),
            preflight=initial,
        )
    evidence = load_object(evidence_path)
    command = resume_command.make_command(
        session_id=session_id,
        version=expected_session_version,
        payload_hash=initial["session"]["payload_hash"],
        checkpoint_id=checkpoint_id,
        preflight=initial,
        evidence_ref=authority_evidence_ref,
        evidence=evidence,
        command_id=command_id or "CMD-RESUME-" + uuid.uuid4().hex,
    )
    authorization = command_authorization.make_authorization(
        command=command,
        preflight=initial,
        project_root=project_root,
        decision="allow",
        source_kind=authorization_source,
        evidence_ref=authorization_ref,
        authorization_id="AUTH-RESUME-" + uuid.uuid4().hex,
    )
    authorization["issued_at"] = now_iso()
    return execute(command, authorization, db_path=db_path, project_root=project_root)


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="quillframe-runtime-command-") as tmp:
        root = Path(tmp)
        (root / ".quillframe").mkdir()
        artifact = root / "draft.txt"
        artifact.write_text("frozen candidate\n", encoding="utf-8")
        artifact_fp = resume_preflight.sha_bytes(artifact.read_bytes())
        authority = {"canon_write": "settlement_only", "framework_write": "forbidden"}
        authority_fp = resume_preflight.fingerprint(authority)
        framework = {
            "name": "Quillframe",
            "version": "0.9.1",
            "commit": "fixture-commit",
            "bundle_fingerprint": "sha256:" + "a" * 64,
        }
        (root / "quillframe.toml").write_text(
            '[quillframe]\nschema="quillframe_project_v1"\n[project]\nid="BOOK-COMMAND"\ntitle="Command Test"\nlanguage="en"\nversion="0.1.0"\nstatus="active"\n[authority]\ncanon_write="settlement_only"\nframework_write="forbidden"\n',
            encoding="utf-8",
        )
        (root / "quillframe.lock.json").write_text(json.dumps({"schema": "quillframe_lock_v1", "framework": framework}), encoding="utf-8")
        (root / "framework.attestation.json").write_text(json.dumps({"framework": framework}), encoding="utf-8")
        evidence = {
            "schema": resume_command.AUTHORITY_EVIDENCE_SCHEMA,
            "project_id": "BOOK-COMMAND",
            "project_authority_fingerprint": authority_fp,
            "framework": {key: framework[key] for key in resume_preflight.FRAMEWORK_KEYS},
            "artifact_bindings": [{"path": "draft.txt", "fingerprint": artifact_fp}],
            "required_capabilities": [],
            "approval_refs": [],
        }
        evidence_ref = "resume-authority.json"
        (root / evidence_ref).write_text(json.dumps(evidence), encoding="utf-8")

        db = root / ".quillframe" / "runtime.db"
        cp = ControlPlane(db)
        cp.init()
        session = {
            "schema": "quillframe_agent_session_v1",
            "resource_id": "BOOK-COMMAND",
            "project_id": "BOOK-COMMAND",
            "session_id": "SES-COMMAND",
            "provider_session_id": None,
            "external_session_ref": None,
            "parent_session_id": None,
            "role": "manager",
            "task_mode": "DRAFT",
            "transport": "chat_session",
            "backend": "self_test",
            "usage_class": "ordinary_chat",
            "status": "idle",
            "memory_policy": "session",
            "context_policy": {"authority_snapshot": None, "context_manifest_ref": None, "allowed_artifact_refs": [], "allowed_paths": [], "forbidden_context_classes": [], "hidden_gold": "forbidden"},
            "resume_policy": "checkpoint_revalidate",
            "runs": [{"run_id": "RUN-COMMAND", "started_at": "2026-01-01T00:00:00+00:00", "ended_at": None, "status": "running", "input_artifact_fingerprints": [artifact_fp], "output_artifact_fingerprints": [], "usage_class": "ordinary_chat"}],
            "checkpoints": [{"checkpoint_id": "CP-COMMAND", "run_id": "RUN-COMMAND", "workflow_step": "context-frozen", "artifact_fingerprints": [artifact_fp], "pending_gate": None, "pending_handoff": None, "resume_policy": "checkpoint_revalidate", "created_at": "2026-01-01T00:00:00+00:00"}],
            "events": [],
            "provenance": {"runtime": "self_test", "version": "1", "durable_store": "control_plane"},
        }
        put = cp.put_session(session, expected_version=0)
        preflight = resume_preflight.inspect(
            db_path=db,
            project_root=root,
            session_id="SES-COMMAND",
            checkpoint_id="CP-COMMAND",
            expected_session_version=put["version"],
            authority_evidence_path=root / evidence_ref,
        )
        command = resume_command.make_command(
            session_id="SES-COMMAND",
            version=put["version"],
            payload_hash=preflight["session"]["payload_hash"],
            checkpoint_id="CP-COMMAND",
            preflight=preflight,
            evidence_ref=evidence_ref,
            evidence=evidence,
            command_id="CMD-COMMAND-1",
        )
        allow = command_authorization.make_authorization(
            command=command,
            preflight=preflight,
            project_root=root,
            decision="allow",
            source_kind="user",
            evidence_ref="urn:quillframe:self-test:user-resume",
            authorization_id="AUTH-COMMAND-ALLOW",
        )
        deny = command_authorization.make_authorization(
            command=command,
            preflight=preflight,
            project_root=root,
            decision="deny",
            source_kind="user",
            evidence_ref="urn:quillframe:self-test:user-resume",
            authorization_id="AUTH-COMMAND-DENY",
        )
        denied = execute(command, deny, db_path=db, project_root=root)
        after_deny = cp.get_session("SES-COMMAND")
        applied = execute(command, allow, db_path=db, project_root=root)
        after_apply = cp.get_session("SES-COMMAND")
        duplicate = execute(command, allow, db_path=db, project_root=root)
        receipts = get_receipts(db, command_id="CMD-COMMAND-1")

        tampered = json.loads(json.dumps(allow))
        tampered["authorization_id"] = "AUTH-COMMAND-OTHER"
        conflict = execute(command, tampered, db_path=db, project_root=root)

        ok = (
            preflight["ready"] is True
            and denied["status"] == "rejected" and denied["runtime_mutation_performed"] is False
            and after_deny is not None and after_deny["version"] == 1 and after_deny["session"]["status"] == "idle"
            and applied["status"] == "applied" and applied["runtime_mutation_performed"] is True
            and after_apply is not None and after_apply["version"] == 2 and after_apply["session"]["status"] == "running"
            and applied["receipt"]["before_state"]["session_version"] == 1
            and applied["receipt"]["after_state"]["session_version"] == 2
            and applied["receipt"]["model_execution"] is False and applied["receipt"]["authority"] is False
            and duplicate["status"] == "duplicate" and duplicate["replayed_receipt"] is True
            and cp.get_session("SES-COMMAND")["version"] == 2
            and receipts["count"] == 1 and receipts["query_only"] is True
            and conflict["status"] == "conflict" and conflict["failure_class"] == "idempotency_conflict"
        )
        result = {
            "runtime_command_executor_contract": "PASS" if ok else "FAIL",
            "resume_applied": applied["status"] == "applied",
            "cas_version_advanced_once": bool(after_apply and after_apply["version"] == 2),
            "denied_did_not_mutate": bool(after_deny and after_deny["version"] == 1),
            "idempotent_retry_replayed_receipt": duplicate["status"] == "duplicate",
            "conflicting_retry_rejected": conflict["status"] == "conflict",
            "durable_receipt_query": receipts["count"] == 1,
            "model_execution": False,
            "authority": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe typed runtime command executor")
    parser.add_argument("--db", default=os.getenv("QUILLFRAME_DB", DEFAULT_DB))
    sub = parser.add_subparsers(dest="command", required=True)

    execute_p = sub.add_parser("execute")
    execute_p.add_argument("--project-root", required=True)
    execute_p.add_argument("--command", required=True)
    execute_p.add_argument("--authorization", required=True)

    resume_p = sub.add_parser("execute-resume")
    resume_p.add_argument("--project-root", required=True)
    resume_p.add_argument("--session-id", required=True)
    resume_p.add_argument("--checkpoint-id", required=True)
    resume_p.add_argument("--expected-session-version", required=True, type=int)
    resume_p.add_argument("--authority-evidence", required=True)
    resume_p.add_argument("--authorization-source", required=True, choices=sorted(command_authorization.SOURCE_KINDS))
    resume_p.add_argument("--authorization-ref", required=True)
    resume_p.add_argument("--command-id")

    receipt_p = sub.add_parser("receipt-get")
    receipt_p.add_argument("--command-id")
    receipt_p.add_argument("--idempotency-key")
    receipt_p.add_argument("--session-id")
    sub.add_parser("self-test")
    args = parser.parse_args()

    try:
        db = Path(args.db)
        if args.command == "execute":
            value = execute(
                load_object(Path(args.command)),
                load_object(Path(args.authorization)),
                db_path=db,
                project_root=Path(args.project_root),
            )
        elif args.command == "execute-resume":
            value = execute_resume(
                db_path=db,
                project_root=Path(args.project_root),
                session_id=args.session_id,
                checkpoint_id=args.checkpoint_id,
                expected_session_version=args.expected_session_version,
                authority_evidence_ref=args.authority_evidence,
                authorization_source=args.authorization_source,
                authorization_ref=args.authorization_ref,
                command_id=args.command_id,
            )
        elif args.command == "receipt-get":
            value = get_receipts(
                db,
                command_id=args.command_id,
                idempotency_key=args.idempotency_key,
                session_id=args.session_id,
            )
        else:
            return self_test()
        print(json.dumps(value, ensure_ascii=False, indent=2))
        if args.command == "receipt-get":
            return 0
        return 0 if value.get("status") in {"applied", "duplicate"} else (2 if value.get("status") in {"rejected", "conflict"} else 1)
    except Exception as exc:
        value = _result("failed", failure_class="executor_cli", errors=[f"{type(exc).__name__}: {exc}"])
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
