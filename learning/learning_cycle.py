#!/usr/bin/env python3
"""Quillframe durable adaptive-learning cycle.

The cycle coordinates learning work across host/session boundaries without
performing semantic judgment itself. It stores operational learning progress in
the Learning Store database, separate from runtime/session state and Project
Canon, and provides logical consume-once receipts for returned artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from learning.learning_store import LearningStore

SCHEMA = "quillframe_learning_cycle_v1"
STATES = {
    "created", "discovery_planned", "awaiting_discovery", "discovery_ready",
    "analysis_queued", "awaiting_analysis", "analysis_ready",
    "eval_queued", "awaiting_eval", "eval_ready", "candidate_ready",
    "completed", "blocked", "failed",
}
TRANSITIONS = {
    "created": {"discovery_planned", "blocked", "failed"},
    "discovery_planned": {"awaiting_discovery", "discovery_ready", "blocked", "failed"},
    "awaiting_discovery": {"discovery_ready", "blocked", "failed"},
    "discovery_ready": {"analysis_queued", "blocked", "failed"},
    "analysis_queued": {"awaiting_analysis", "analysis_ready", "blocked", "failed"},
    "awaiting_analysis": {"analysis_ready", "blocked", "failed"},
    "analysis_ready": {"eval_queued", "candidate_ready", "blocked", "failed"},
    "eval_queued": {"awaiting_eval", "eval_ready", "blocked", "failed"},
    "awaiting_eval": {"eval_ready", "blocked", "failed"},
    "eval_ready": {"candidate_ready", "blocked", "failed"},
    "candidate_ready": {"completed", "blocked", "failed"},
    "blocked": {"discovery_planned", "analysis_queued", "eval_queued", "candidate_ready", "failed"},
    "failed": set(),
    "completed": set(),
}
ARTIFACT_KINDS = {
    "discovery_queue", "dispatch_plan", "discovery_results", "verified_discovery",
    "analysis_jobs", "analysis_results", "eval_jobs", "eval_results", "promotion_candidate",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class LearningCycleStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        LearningStore(self.db_path).init()
        self.init()

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

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS learning_cycles (
                cycle_id TEXT PRIMARY KEY,
                subject_scope TEXT NOT NULL,
                project_id TEXT,
                hypothesis_id TEXT,
                gap_id TEXT NOT NULL,
                state TEXT NOT NULL,
                current_step TEXT NOT NULL,
                version INTEGER NOT NULL,
                context_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_learning_cycle_state
              ON learning_cycles(state, updated_at);
            CREATE TABLE IF NOT EXISTS learning_cycle_artifacts (
                cycle_id TEXT NOT NULL,
                artifact_kind TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(cycle_id, artifact_kind, artifact_id),
                FOREIGN KEY(cycle_id) REFERENCES learning_cycles(cycle_id)
            );
            CREATE TABLE IF NOT EXISTS learning_cycle_receipts (
                cycle_id TEXT NOT NULL,
                logical_key TEXT NOT NULL,
                consumer TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                consumed_at TEXT NOT NULL,
                PRIMARY KEY(cycle_id, logical_key, consumer),
                FOREIGN KEY(cycle_id) REFERENCES learning_cycles(cycle_id)
            );
            """)

    def _gap(self, gap_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            r = conn.execute("SELECT * FROM corpus_gaps WHERE gap_id=?", (gap_id,)).fetchone()
        if not r:
            raise ValueError(f"unknown corpus gap: {gap_id}")
        return dict(r)

    def start(self, gap_id: str, *, cycle_id: str | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        gap = self._gap(gap_id)
        cid = cycle_id or "LC-" + uuid.uuid4().hex
        ts = now_iso()
        payload = context or {}
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM learning_cycles WHERE cycle_id=?", (cid,)).fetchone()
            if row:
                conn.execute("COMMIT")
                if row["gap_id"] != gap_id:
                    raise ValueError("cycle_id conflict")
                return self.get(cid) | {"duplicate": True}
            conn.execute(
                """INSERT INTO learning_cycles(
                    cycle_id,subject_scope,project_id,hypothesis_id,gap_id,state,current_step,version,context_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    cid, gap["subject_scope"], None, gap["hypothesis_id"], gap_id,
                    "created", "start", 1, canonical(payload), ts, ts,
                ),
            )
            conn.execute("COMMIT")
        return self.get(cid) | {"duplicate": False}

    def get(self, cycle_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            r = conn.execute("SELECT * FROM learning_cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
            if not r:
                raise ValueError(f"unknown learning cycle: {cycle_id}")
            counts = conn.execute(
                "SELECT artifact_kind,COUNT(*) AS n FROM learning_cycle_artifacts WHERE cycle_id=? GROUP BY artifact_kind",
                (cycle_id,),
            ).fetchall()
            receipts = conn.execute("SELECT COUNT(*) AS n FROM learning_cycle_receipts WHERE cycle_id=?", (cycle_id,)).fetchone()["n"]
        return {
            "schema": SCHEMA,
            "cycle_id": r["cycle_id"],
            "subject_scope": r["subject_scope"],
            "project_id": r["project_id"],
            "hypothesis_id": r["hypothesis_id"],
            "gap_id": r["gap_id"],
            "state": r["state"],
            "current_step": r["current_step"],
            "version": r["version"],
            "context": json.loads(r["context_json"]),
            "artifact_counts": {x["artifact_kind"]: x["n"] for x in counts},
            "consumption_receipts": receipts,
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "canon_authority": False,
            "framework_write_authority": False,
            "durable_user_taste_write_authority": False,
        }

    def transition(self, cycle_id: str, target: str, *, expected_version: int | None = None, step: str | None = None) -> dict[str, Any]:
        if target not in STATES:
            raise ValueError("invalid learning cycle state")
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            r = conn.execute("SELECT state,version FROM learning_cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
            if not r:
                conn.execute("ROLLBACK"); raise ValueError("unknown learning cycle")
            if expected_version is not None and r["version"] != expected_version:
                conn.execute("ROLLBACK"); raise ValueError("learning cycle version mismatch")
            current = r["state"]
            if target == current:
                conn.execute("COMMIT"); return self.get(cycle_id) | {"duplicate_transition": True}
            if target not in TRANSITIONS[current]:
                conn.execute("ROLLBACK"); raise ValueError(f"illegal learning cycle transition: {current} -> {target}")
            version = r["version"] + 1
            conn.execute(
                "UPDATE learning_cycles SET state=?,current_step=?,version=?,updated_at=? WHERE cycle_id=?",
                (target, step or target, version, now_iso(), cycle_id),
            )
            conn.execute("COMMIT")
        return self.get(cycle_id) | {"duplicate_transition": False}

    def attach(self, cycle_id: str, kind: str, artifact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if kind not in ARTIFACT_KINDS:
            raise ValueError("invalid artifact kind")
        if not artifact_id:
            raise ValueError("artifact_id required")
        ph = digest(payload)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute("SELECT 1 FROM learning_cycles WHERE cycle_id=?", (cycle_id,)).fetchone():
                conn.execute("ROLLBACK"); raise ValueError("unknown learning cycle")
            r = conn.execute(
                "SELECT payload_hash FROM learning_cycle_artifacts WHERE cycle_id=? AND artifact_kind=? AND artifact_id=?",
                (cycle_id, kind, artifact_id),
            ).fetchone()
            if r:
                conn.execute("COMMIT")
                if r["payload_hash"] != ph:
                    raise ValueError("artifact identity conflict")
                return {"cycle_id": cycle_id, "artifact_kind": kind, "artifact_id": artifact_id, "payload_hash": ph, "duplicate": True}
            conn.execute(
                "INSERT INTO learning_cycle_artifacts(cycle_id,artifact_kind,artifact_id,payload_hash,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                (cycle_id, kind, artifact_id, ph, canonical(payload), now_iso()),
            )
            conn.execute("COMMIT")
        return {"cycle_id": cycle_id, "artifact_kind": kind, "artifact_id": artifact_id, "payload_hash": ph, "duplicate": False}

    def consume(self, cycle_id: str, kind: str, artifact_id: str, consumer: str) -> dict[str, Any]:
        logical_key = f"{kind}:{artifact_id}"
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            r = conn.execute(
                "SELECT payload_hash FROM learning_cycle_artifacts WHERE cycle_id=? AND artifact_kind=? AND artifact_id=?",
                (cycle_id, kind, artifact_id),
            ).fetchone()
            if not r:
                conn.execute("ROLLBACK"); raise ValueError("artifact not registered")
            existing = conn.execute(
                "SELECT payload_hash FROM learning_cycle_receipts WHERE cycle_id=? AND logical_key=? AND consumer=?",
                (cycle_id, logical_key, consumer),
            ).fetchone()
            if existing:
                conn.execute("COMMIT")
                if existing["payload_hash"] != r["payload_hash"]:
                    raise ValueError("consume receipt hash conflict")
                return {"cycle_id": cycle_id, "logical_key": logical_key, "consumer": consumer, "payload_hash": r["payload_hash"], "already_consumed": True}
            conn.execute(
                "INSERT INTO learning_cycle_receipts(cycle_id,logical_key,consumer,payload_hash,consumed_at) VALUES(?,?,?,?,?)",
                (cycle_id, logical_key, consumer, r["payload_hash"], now_iso()),
            )
            conn.execute("COMMIT")
        return {"cycle_id": cycle_id, "logical_key": logical_key, "consumer": consumer, "payload_hash": r["payload_hash"], "already_consumed": False}

    def artifact(self, cycle_id: str, kind: str, artifact_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            r = conn.execute(
                "SELECT * FROM learning_cycle_artifacts WHERE cycle_id=? AND artifact_kind=? AND artifact_id=?",
                (cycle_id, kind, artifact_id),
            ).fetchone()
        if not r:
            raise ValueError("artifact not registered")
        return {"payload_hash": r["payload_hash"], "payload": json.loads(r["payload_json"]), "created_at": r["created_at"]}


def self_test(path: str | Path) -> dict[str, Any]:
    db = Path(path)
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        if p.exists(): p.unlink()
    ls = LearningStore(db); ls.init()
    ev = ls.add_evidence({
        "subject_scope": "user_taste", "source": "explicit_rule", "polarity": "negative",
        "mechanism": "pace comes from state change rather than fragmentation", "confidence": 1.0,
    })
    hyp = ls.upsert_hypothesis({
        "subject_scope": "user_taste", "dimension": "paragraph_rhythm", "statement": "fixture",
        "mechanism": "pace comes from state change", "confidence": 0.8, "evidence_ids": [ev["evidence_id"]],
    }, expected_version=0)
    gap = ls.add_gap({
        "subject_scope": "user_taste", "hypothesis_id": hyp["hypothesis_id"], "question": "fixture gap", "priority": 0.9,
    })
    store = LearningCycleStore(db)
    started = store.start(gap["gap_id"], cycle_id="LC-TEST")
    dup_start = store.start(gap["gap_id"], cycle_id="LC-TEST")
    q = store.attach("LC-TEST", "discovery_queue", "DQ-1", {"schema": "fixture", "items": [1]})
    dup_q = store.attach("LC-TEST", "discovery_queue", "DQ-1", {"schema": "fixture", "items": [1]})
    t1 = store.transition("LC-TEST", "discovery_planned", expected_version=started["version"])
    t2 = store.transition("LC-TEST", "awaiting_discovery", expected_version=t1["version"])
    receipt1 = store.consume("LC-TEST", "discovery_queue", "DQ-1", "dispatcher")
    receipt2 = store.consume("LC-TEST", "discovery_queue", "DQ-1", "dispatcher")
    illegal_guard = False
    try:
        store.transition("LC-TEST", "completed", expected_version=t2["version"])
    except ValueError:
        illegal_guard = True
    conflict_guard = False
    try:
        store.attach("LC-TEST", "discovery_queue", "DQ-1", {"schema": "different"})
    except ValueError:
        conflict_guard = True
    resumed = LearningCycleStore(db).get("LC-TEST")
    ok = (
        started["state"] == "created" and dup_start["duplicate"] is True
        and q["duplicate"] is False and dup_q["duplicate"] is True
        and receipt1["already_consumed"] is False and receipt2["already_consumed"] is True
        and illegal_guard and conflict_guard and resumed["state"] == "awaiting_discovery"
        and resumed["canon_authority"] is False and resumed["framework_write_authority"] is False
    )
    return {
        "learning_cycle_contract": "PASS" if ok else "FAIL",
        "durable_resume": resumed["state"] == "awaiting_discovery",
        "illegal_transition_guard": illegal_guard,
        "artifact_identity_guard": conflict_guard,
        "logical_consume_once": receipt2["already_consumed"] is True,
        "canon_authority": False,
        "framework_write_authority": False,
    }


def load_json(path: str) -> dict[str, Any]:
    v = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(v, dict): raise ValueError("JSON root must be object")
    return v


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe durable learning cycle")
    p.add_argument("--db", default=".quillframe/learning.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start"); st.add_argument("--gap-id", required=True); st.add_argument("--cycle-id"); st.add_argument("--context")
    ge = sub.add_parser("get"); ge.add_argument("--cycle-id", required=True)
    tr = sub.add_parser("transition"); tr.add_argument("--cycle-id", required=True); tr.add_argument("--to", required=True, choices=sorted(STATES)); tr.add_argument("--expected-version", type=int); tr.add_argument("--step")
    at = sub.add_parser("attach"); at.add_argument("--cycle-id", required=True); at.add_argument("--kind", required=True, choices=sorted(ARTIFACT_KINDS)); at.add_argument("--artifact-id", required=True); at.add_argument("--json", required=True)
    co = sub.add_parser("consume"); co.add_argument("--cycle-id", required=True); co.add_argument("--kind", required=True, choices=sorted(ARTIFACT_KINDS)); co.add_argument("--artifact-id", required=True); co.add_argument("--consumer", required=True)
    sf = sub.add_parser("self-test"); sf.add_argument("--path", default="/tmp/quillframe-learning-cycle-selftest.db")
    args = p.parse_args(); store = LearningCycleStore(args.db) if args.cmd != "self-test" else None
    if args.cmd == "self-test":
        result = self_test(args.path); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["learning_cycle_contract"] == "PASS" else 1
    if args.cmd == "start":
        context = load_json(args.context) if args.context else None; result = store.start(args.gap_id, cycle_id=args.cycle_id, context=context)
    elif args.cmd == "get": result = store.get(args.cycle_id)
    elif args.cmd == "transition": result = store.transition(args.cycle_id, args.to, expected_version=args.expected_version, step=args.step)
    elif args.cmd == "attach": result = store.attach(args.cycle_id, args.kind, args.artifact_id, load_json(args.json))
    else: result = store.consume(args.cycle_id, args.kind, args.artifact_id, args.consumer)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
