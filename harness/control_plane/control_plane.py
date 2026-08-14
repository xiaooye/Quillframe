#!/usr/bin/env python3
"""Novel Production OS v6.6 durable runtime control plane.

Stdlib-only. This module persists operational execution state:
sessions, events, handoffs, leases, and exactly-once consumption receipts.

It does NOT run an LLM, mutate Canon, or grant OS/project authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

CONTROL_PLANE_SCHEMA = "novel_os_control_plane_v1"
EVENT_SCHEMA = "novel_os_event_v1"
HANDOFF_SCHEMA = "novel_os_handoff_v1"
DEFAULT_DB = ".novel-os/runtime.db"
EVENT_TYPES = {
    "session.resume_requested",
    "semantic.requested",
    "semantic.result_received",
    "eval.requested",
    "maintenance.requested",
    "research.refresh_requested",
    "feedback.observed",
    "artifact.acceptance_observed",
}
TARGET_SESSION_CLASSES = {
    "manager", "writer", "specialist", "semantic_reviewer",
    "human_reviewer", "other",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError("JSON file must contain one object")
    return value


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


class ControlPlane:
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self.db_path = Path(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def init(self) -> dict[str, Any]:
        with self.connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                resource_id TEXT NOT NULL,
                project_id TEXT,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_resource
                ON sessions(resource_id, updated_at);

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                session_id TEXT,
                run_id TEXT,
                handoff_id TEXT,
                idempotency_key TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                received_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_session
                ON events(session_id, received_at);

            CREATE TABLE IF NOT EXISTS handoffs (
                handoff_id TEXT PRIMARY KEY,
                source_session_id TEXT NOT NULL,
                target_session_class TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                task_mode TEXT,
                state TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                lease_owner TEXT,
                lease_until REAL,
                attempts INTEGER NOT NULL DEFAULT 0,
                result_json TEXT,
                result_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_handoffs_claim
                ON handoffs(state, target_session_class, created_at);

            CREATE TABLE IF NOT EXISTS consumptions (
                consumption_key TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                consumer TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                consumed_at TEXT NOT NULL
            );
            """)
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('schema',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (CONTROL_PLANE_SCHEMA,),
            )
        return {"schema": CONTROL_PLANE_SCHEMA, "db": str(self.db_path), "initialized": True}

    def put_session(self, session: dict[str, Any], *, expected_version: int | None = None) -> dict[str, Any]:
        required = ("session_id", "resource_id", "role", "status")
        missing = [k for k in required if not session.get(k)]
        if missing:
            raise ValueError("session missing: " + ", ".join(missing))
        body = canonical_json(session)
        h = digest(session)
        ts = now_iso()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT version,payload_hash FROM sessions WHERE session_id=?",
                (session["session_id"],),
            ).fetchone()
            if row:
                if expected_version is not None and row["version"] != expected_version:
                    conn.execute("ROLLBACK")
                    raise ValueError(
                        f"session version mismatch expected={expected_version} actual={row['version']}"
                    )
                if row["payload_hash"] == h:
                    conn.execute("COMMIT")
                    return {"session_id": session["session_id"], "version": row["version"], "duplicate": True, "payload_hash": h}
                version = row["version"] + 1
                conn.execute(
                    """UPDATE sessions SET resource_id=?, project_id=?, role=?, status=?, payload_json=?,
                       payload_hash=?, version=?, updated_at=? WHERE session_id=?""",
                    (session["resource_id"], session.get("project_id"), session["role"], session["status"], body, h, version, ts, session["session_id"]),
                )
            else:
                if expected_version not in (None, 0):
                    conn.execute("ROLLBACK")
                    raise ValueError("cannot apply nonzero expected_version to new session")
                version = 1
                conn.execute(
                    """INSERT INTO sessions(session_id,resource_id,project_id,role,status,payload_json,payload_hash,
                       version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (session["session_id"], session["resource_id"], session.get("project_id"), session["role"], session["status"], body, h, version, ts, ts),
                )
            conn.execute("COMMIT")
        return {"session_id": session["session_id"], "version": version, "duplicate": False, "payload_hash": h}

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        if not row:
            return None
        return {"session": json.loads(row["payload_json"]), "version": row["version"], "payload_hash": row["payload_hash"], "updated_at": row["updated_at"]}

    def list_sessions(self, resource_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if resource_id:
                rows = conn.execute(
                    """SELECT session_id,resource_id,project_id,role,status,version,updated_at
                       FROM sessions WHERE resource_id=? ORDER BY updated_at DESC""", (resource_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT session_id,resource_id,project_id,role,status,version,updated_at
                       FROM sessions ORDER BY updated_at DESC"""
                ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def validate_event(event: dict[str, Any]) -> None:
        required = ("schema", "event_id", "event_type", "source", "resource_id", "authority_scope", "idempotency_key", "created_at", "payload")
        missing = [k for k in required if k not in event]
        if missing:
            raise ValueError("event missing: " + ", ".join(missing))
        if event["schema"] != EVENT_SCHEMA:
            raise ValueError("invalid event schema")
        if event["event_type"] not in EVENT_TYPES:
            raise ValueError(f"unsupported event_type {event['event_type']}")
        if event["authority_scope"] not in {"observation", "request", "result"}:
            raise ValueError("invalid authority_scope")
        if not isinstance(event["source"], dict) or not event["source"].get("kind"):
            raise ValueError("event.source.kind required")
        if not isinstance(event["payload"], dict):
            raise ValueError("event.payload must be object")
        if not isinstance(event.get("artifact_fingerprints", []), list):
            raise ValueError("artifact_fingerprints must be array")

    def ingest_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self.validate_event(event)
        h = digest(event)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT event_id,payload_hash FROM events WHERE idempotency_key=?", (event["idempotency_key"],)).fetchone()
            if existing:
                conn.execute("COMMIT")
                if existing["payload_hash"] != h:
                    raise ValueError("idempotency_key conflict with different event payload")
                return {"event_id": existing["event_id"], "accepted": True, "duplicate": True, "payload_hash": h}
            collision = conn.execute("SELECT payload_hash FROM events WHERE event_id=?", (event["event_id"],)).fetchone()
            if collision:
                conn.execute("ROLLBACK")
                raise ValueError("event_id already exists with different idempotency key")
            conn.execute(
                """INSERT INTO events(event_id,event_type,resource_id,session_id,run_id,handoff_id,
                   idempotency_key,payload_json,payload_hash,received_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (event["event_id"], event["event_type"], event["resource_id"], event.get("session_id"), event.get("run_id"), event.get("handoff_id"), event["idempotency_key"], canonical_json(event), h, now_iso()),
            )
            conn.execute("COMMIT")
        return {"event_id": event["event_id"], "accepted": True, "duplicate": False, "payload_hash": h}

    def list_events(self, session_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if session_id:
                rows = conn.execute(
                    """SELECT event_id,event_type,resource_id,session_id,run_id,handoff_id,idempotency_key,payload_hash,received_at
                       FROM events WHERE session_id=? ORDER BY received_at""", (session_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT event_id,event_type,resource_id,session_id,run_id,handoff_id,idempotency_key,payload_hash,received_at
                       FROM events ORDER BY received_at"""
                ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def validate_handoff(handoff: dict[str, Any]) -> None:
        required = ("schema", "handoff_id", "source_session_id", "target_session_class", "resource_id", "artifact_refs", "artifact_fingerprints", "context_policy", "permissions", "return_contract")
        missing = [k for k in required if k not in handoff]
        if missing:
            raise ValueError("handoff missing: " + ", ".join(missing))
        if handoff["schema"] != HANDOFF_SCHEMA:
            raise ValueError("invalid handoff schema")
        if handoff["target_session_class"] not in TARGET_SESSION_CLASSES:
            raise ValueError("invalid target_session_class")
        for key in ("artifact_refs", "artifact_fingerprints"):
            if not isinstance(handoff[key], list):
                raise ValueError(f"{key} must be array")
        if not isinstance(handoff["context_policy"], dict):
            raise ValueError("context_policy must be object")
        p = handoff["permissions"]
        if not isinstance(p, dict):
            raise ValueError("permissions must be object")
        for forbidden in ("canon_write", "os_behavior_write", "durable_user_taste_write"):
            if p.get(forbidden) is not False:
                raise ValueError(f"handoff permission {forbidden} must be false")
        if not isinstance(handoff["return_contract"], dict):
            raise ValueError("return_contract must be object")

    def submit_handoff(self, handoff: dict[str, Any]) -> dict[str, Any]:
        self.validate_handoff(handoff)
        h = digest(handoff)
        ts = now_iso()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT payload_hash,state FROM handoffs WHERE handoff_id=?", (handoff["handoff_id"],)).fetchone()
            if existing:
                conn.execute("COMMIT")
                if existing["payload_hash"] != h:
                    raise ValueError("handoff_id conflict with different payload")
                return {"handoff_id": handoff["handoff_id"], "state": existing["state"], "duplicate": True, "payload_hash": h}
            conn.execute(
                """INSERT INTO handoffs(handoff_id,source_session_id,target_session_class,resource_id,task_mode,
                   state,payload_json,payload_hash,created_at,updated_at) VALUES(?,?,?,?,?,'queued',?,?,?,?)""",
                (handoff["handoff_id"], handoff["source_session_id"], handoff["target_session_class"], handoff["resource_id"], handoff.get("task_mode"), canonical_json(handoff), h, ts, ts),
            )
            conn.execute("COMMIT")
        return {"handoff_id": handoff["handoff_id"], "state": "queued", "duplicate": False, "payload_hash": h}

    def claim_handoff(self, worker_id: str, *, target_session_class: str | None = None, lease_seconds: int = 300) -> dict[str, Any] | None:
        if lease_seconds < 1 or lease_seconds > 86400:
            raise ValueError("lease_seconds must be 1..86400")
        if target_session_class and target_session_class not in TARGET_SESSION_CLASSES:
            raise ValueError("invalid target_session_class")
        now_epoch = time.time()
        lease_until = now_epoch + lease_seconds
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            params: list[Any] = [now_epoch]
            where = "(state='queued' OR (state='claimed' AND lease_until IS NOT NULL AND lease_until < ?))"
            if target_session_class:
                where += " AND target_session_class=?"
                params.append(target_session_class)
            row = conn.execute(f"SELECT * FROM handoffs WHERE {where} ORDER BY created_at ASC LIMIT 1", params).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            conn.execute(
                """UPDATE handoffs SET state='claimed', lease_owner=?, lease_until=?, attempts=attempts+1, updated_at=?
                   WHERE handoff_id=?""", (worker_id, lease_until, now_iso(), row["handoff_id"])
            )
            conn.execute("COMMIT")
        return {"handoff_id": row["handoff_id"], "payload": json.loads(row["payload_json"]), "state": "claimed", "lease_owner": worker_id, "lease_until": lease_until, "attempt": row["attempts"] + 1}

    def complete_handoff(self, handoff_id: str, worker_id: str, result: dict[str, Any], *, failed: bool = False) -> dict[str, Any]:
        result_hash = digest(result)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM handoffs WHERE handoff_id=?", (handoff_id,)).fetchone()
            if not row:
                conn.execute("ROLLBACK")
                raise ValueError("unknown handoff_id")
            if row["state"] == "completed":
                conn.execute("COMMIT")
                if row["result_hash"] != result_hash:
                    raise ValueError("completed handoff already has a different result")
                return {"handoff_id": handoff_id, "state": "completed", "duplicate": True, "result_hash": result_hash}
            if row["state"] != "claimed" or row["lease_owner"] != worker_id:
                conn.execute("ROLLBACK")
                raise ValueError("handoff must be claimed by this worker")
            if row["lease_until"] is None or row["lease_until"] < time.time():
                conn.execute("ROLLBACK")
                raise ValueError("handoff lease expired; reclaim before completion")
            state = "failed" if failed else "completed"
            conn.execute(
                """UPDATE handoffs SET state=?, result_json=?, result_hash=?, lease_owner=NULL,
                   lease_until=NULL, updated_at=? WHERE handoff_id=?""",
                (state, canonical_json(result), result_hash, now_iso(), handoff_id),
            )
            conn.execute("COMMIT")
        return {"handoff_id": handoff_id, "state": state, "duplicate": False, "result_hash": result_hash}

    def get_handoff(self, handoff_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM handoffs WHERE handoff_id=?", (handoff_id,)).fetchone()
        if not row:
            return None
        return {"handoff_id": row["handoff_id"], "source_session_id": row["source_session_id"], "target_session_class": row["target_session_class"], "resource_id": row["resource_id"], "task_mode": row["task_mode"], "state": row["state"], "payload": json.loads(row["payload_json"]), "payload_hash": row["payload_hash"], "lease_owner": row["lease_owner"], "lease_until": row["lease_until"], "attempts": row["attempts"], "result": json.loads(row["result_json"]) if row["result_json"] else None, "result_hash": row["result_hash"], "created_at": row["created_at"], "updated_at": row["updated_at"]}

    def consume_once(self, source_type: str, source_id: str, consumer: str, payload_hash: str) -> dict[str, Any]:
        if not all((source_type, source_id, consumer, payload_hash)):
            raise ValueError("source_type/source_id/consumer/payload_hash required")
        key = f"{source_type}:{source_id}:{consumer}"
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT payload_hash,consumed_at FROM consumptions WHERE consumption_key=?", (key,)).fetchone()
            if row:
                conn.execute("COMMIT")
                if row["payload_hash"] != payload_hash:
                    raise ValueError("consumption conflict: same logical result has different payload hash")
                return {"consumption_key": key, "consumed": False, "already_consumed": True, "consumed_at": row["consumed_at"]}
            ts = now_iso()
            conn.execute(
                """INSERT INTO consumptions(consumption_key,source_type,source_id,consumer,payload_hash,consumed_at)
                   VALUES(?,?,?,?,?,?)""", (key, source_type, source_id, consumer, payload_hash, ts)
            )
            conn.execute("COMMIT")
        return {"consumption_key": key, "consumed": True, "already_consumed": False, "consumed_at": ts}

    def status(self) -> dict[str, Any]:
        with self.connect() as conn:
            counts = {table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"] for table in ("sessions", "events", "handoffs", "consumptions")}
            handoff_states = {row["state"]: row["n"] for row in conn.execute("SELECT state,COUNT(*) AS n FROM handoffs GROUP BY state").fetchall()}
        return {"schema": CONTROL_PLANE_SCHEMA, "db": str(self.db_path), "counts": counts, "handoff_states": handoff_states}


def self_test(db_path: str | Path) -> dict[str, Any]:
    path = Path(db_path)
    if path.exists():
        path.unlink()
    cp = ControlPlane(path)
    cp.init()
    session = {"schema": "novel_os_agent_session_v1", "resource_id": "BOOK-TEST", "project_id": "BOOK-TEST", "session_id": "SES-TEST-MANAGER", "role": "manager", "status": "awaiting_external"}
    first_session = cp.put_session(session, expected_version=0)
    duplicate_session = cp.put_session(session, expected_version=1)
    event = {"schema": EVENT_SCHEMA, "event_id": "EV-TEST-1", "event_type": "semantic.requested", "source": {"kind": "self_test", "actor": "control_plane.py"}, "resource_id": "BOOK-TEST", "session_id": "SES-TEST-MANAGER", "run_id": "RUN-TEST", "handoff_id": "HO-TEST-1", "authority_scope": "request", "idempotency_key": "selftest-semantic-request", "artifact_fingerprints": ["sha256:" + "a" * 64], "created_at": now_iso(), "payload": {"job_id": "SEM-TEST"}}
    first_event = cp.ingest_event(event)
    duplicate_event = cp.ingest_event(event)
    handoff = {"schema": HANDOFF_SCHEMA, "handoff_id": "HO-TEST-1", "source_session_id": "SES-TEST-MANAGER", "target_session_class": "semantic_reviewer", "resource_id": "BOOK-TEST", "task_mode": "DRAFT", "artifact_refs": ["ART-TEST"], "artifact_fingerprints": ["sha256:" + "a" * 64], "instructions_ref": "SEM-TEST", "context_policy": {"hidden_gold": "forbidden", "allowed_artifact_refs": ["ART-TEST"]}, "permissions": {"canon_write": False, "os_behavior_write": False, "durable_user_taste_write": False, "allowed_result_scope": "observation"}, "return_contract": {"schema": "semantic_worker_result", "fingerprint_required": True}, "relay_nonce": None}
    submitted = cp.submit_handoff(handoff)
    claimed = cp.claim_handoff("WORKER-1", target_session_class="semantic_reviewer", lease_seconds=60)
    result = {"job_id": "SEM-TEST", "input_fingerprint": "sha256:" + "a" * 64, "status": "completed", "judgment": {"verdict": "accept"}}
    completed = cp.complete_handoff("HO-TEST-1", "WORKER-1", result)
    consumed = cp.consume_once("handoff", "HO-TEST-1", "semantic_gate", completed["result_hash"])
    consumed_again = cp.consume_once("handoff", "HO-TEST-1", "semantic_gate", completed["result_hash"])
    bad_handoff_blocked = False
    bad = dict(handoff)
    bad["handoff_id"] = "HO-BAD"
    bad["permissions"] = dict(handoff["permissions"])
    bad["permissions"]["canon_write"] = True
    try:
        cp.submit_handoff(bad)
    except ValueError:
        bad_handoff_blocked = True
    ok = all([first_session["version"] == 1, duplicate_session["duplicate"] is True, first_event["duplicate"] is False, duplicate_event["duplicate"] is True, submitted["state"] == "queued", claimed is not None and claimed["lease_owner"] == "WORKER-1", completed["state"] == "completed", consumed["consumed"] is True, consumed_again["already_consumed"] is True, bad_handoff_blocked])
    return {"control_plane_contract": "PASS" if ok else "FAIL", "sqlite_durable_store": True, "idempotent_event_ingress": duplicate_event["duplicate"], "lease_claim": claimed is not None, "exactly_once_consumption": consumed_again["already_consumed"], "authority_guard": bad_handoff_blocked, "status": cp.status()}


def main() -> int:
    p = argparse.ArgumentParser(description="Novel Production OS v6.6 control plane")
    p.add_argument("--db", default=os.getenv("NOVEL_OS_DB", DEFAULT_DB))
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("self-test")
    ps = sub.add_parser("session-put"); ps.add_argument("--session", required=True); ps.add_argument("--expected-version", type=int)
    pg = sub.add_parser("session-get"); pg.add_argument("--session-id", required=True)
    pl = sub.add_parser("session-list"); pl.add_argument("--resource-id")
    pe = sub.add_parser("event-ingest"); pe.add_argument("--event", required=True)
    pel = sub.add_parser("event-list"); pel.add_argument("--session-id")
    ph = sub.add_parser("handoff-submit"); ph.add_argument("--handoff", required=True)
    phc = sub.add_parser("handoff-claim"); phc.add_argument("--worker-id", required=True); phc.add_argument("--target-session-class", choices=sorted(TARGET_SESSION_CLASSES)); phc.add_argument("--lease-seconds", type=int, default=300)
    phg = sub.add_parser("handoff-get"); phg.add_argument("--handoff-id", required=True)
    phd = sub.add_parser("handoff-complete"); phd.add_argument("--handoff-id", required=True); phd.add_argument("--worker-id", required=True); phd.add_argument("--result", required=True); phd.add_argument("--failed", action="store_true")
    pc = sub.add_parser("consume"); pc.add_argument("--source-type", required=True); pc.add_argument("--source-id", required=True); pc.add_argument("--consumer", required=True); pc.add_argument("--payload-hash", required=True)
    args = p.parse_args()
    cp = ControlPlane(args.db)
    try:
        cp.init()
        if args.command == "init": dump(cp.init())
        elif args.command == "status": dump(cp.status())
        elif args.command == "self-test": dump(self_test(args.db))
        elif args.command == "session-put": dump(cp.put_session(load_json(args.session), expected_version=args.expected_version))
        elif args.command == "session-get":
            value = cp.get_session(args.session_id)
            if value is None: raise ValueError("session not found")
            dump(value)
        elif args.command == "session-list": dump({"sessions": cp.list_sessions(args.resource_id)})
        elif args.command == "event-ingest": dump(cp.ingest_event(load_json(args.event)))
        elif args.command == "event-list": dump({"events": cp.list_events(args.session_id)})
        elif args.command == "handoff-submit": dump(cp.submit_handoff(load_json(args.handoff)))
        elif args.command == "handoff-claim": dump({"claim": cp.claim_handoff(args.worker_id, target_session_class=args.target_session_class, lease_seconds=args.lease_seconds)})
        elif args.command == "handoff-get":
            value = cp.get_handoff(args.handoff_id)
            if value is None: raise ValueError("handoff not found")
            dump(value)
        elif args.command == "handoff-complete": dump(cp.complete_handoff(args.handoff_id, args.worker_id, load_json(args.result), failed=args.failed))
        elif args.command == "consume": dump(cp.consume_once(args.source_type, args.source_id, args.consumer, args.payload_hash))
        return 0
    except Exception as exc:
        dump({"error": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
