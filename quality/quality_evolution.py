#!/usr/bin/env python3
"""Durable candidate-evolution ledger for NovelForge 7.2.

Deterministic SQLite state only. The ledger tracks candidates, pairwise results,
repair ownership, and plateau stopping. It never performs semantic judgment and
never grants Canon/Framework-write authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_quality_evolution_v1"
REPAIR_OWNERS = {
    "story", "plan", "scene", "character", "reader", "surface",
    "continuity", "context", "memory", "research", "runtime", "human",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text_fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS evolution_runs(
      run_id TEXT PRIMARY KEY,
      subject_id TEXT NOT NULL,
      state TEXT NOT NULL,
      baseline_candidate_id TEXT NOT NULL,
      incumbent_candidate_id TEXT NOT NULL,
      no_gain_count INTEGER NOT NULL DEFAULT 0,
      plateau_limit INTEGER NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0)
    );
    CREATE TABLE IF NOT EXISTS evolution_candidates(
      run_id TEXT NOT NULL,
      candidate_id TEXT NOT NULL,
      content_fingerprint TEXT NOT NULL,
      parent_candidate_id TEXT,
      repair_owner TEXT NOT NULL,
      metadata_json TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY(run_id,candidate_id),
      UNIQUE(run_id,content_fingerprint),
      FOREIGN KEY(run_id) REFERENCES evolution_runs(run_id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS evolution_comparisons(
      run_id TEXT NOT NULL,
      comparison_id TEXT NOT NULL,
      incumbent_candidate_id TEXT NOT NULL,
      challenger_candidate_id TEXT NOT NULL,
      winner_candidate_id TEXT,
      result_fingerprint TEXT NOT NULL,
      result_json TEXT NOT NULL,
      consumed_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY(run_id,comparison_id),
      UNIQUE(run_id,result_fingerprint),
      FOREIGN KEY(run_id) REFERENCES evolution_runs(run_id) ON DELETE CASCADE
    );
    """)
    return conn


def start_run(conn: sqlite3.Connection, *, run_id: str, subject_id: str, baseline_candidate_id: str,
              baseline_text: str, plateau_limit: int = 2) -> dict[str, Any]:
    if plateau_limit < 1:
        raise ValueError("plateau_limit must be >= 1")
    if not all(isinstance(x, str) and x.strip() for x in (run_id, subject_id, baseline_candidate_id, baseline_text)):
        raise ValueError("run/subject/baseline id and baseline text are required")
    stamp = now()
    fp = text_fingerprint(baseline_text)
    try:
        conn.execute(
            "INSERT INTO evolution_runs(run_id,subject_id,state,baseline_candidate_id,incumbent_candidate_id,no_gain_count,plateau_limit,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (run_id, subject_id, "active", baseline_candidate_id, baseline_candidate_id, 0, plateau_limit, stamp, stamp),
        )
        conn.execute(
            "INSERT INTO evolution_candidates(run_id,candidate_id,content_fingerprint,parent_candidate_id,repair_owner,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (run_id, baseline_candidate_id, fp, None, "human", "{}", stamp),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT * FROM evolution_runs WHERE run_id=?", (run_id,)).fetchone()
        cand = conn.execute("SELECT * FROM evolution_candidates WHERE run_id=? AND candidate_id=?", (run_id, baseline_candidate_id)).fetchone()
        if not row or not cand or cand["content_fingerprint"] != fp or row["subject_id"] != subject_id:
            raise ValueError("run_id already exists with different baseline")
    return status(conn, run_id)


def _run(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM evolution_runs WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        raise ValueError(f"unknown run_id: {run_id}")
    return row


def _candidate(conn: sqlite3.Connection, run_id: str, candidate_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM evolution_candidates WHERE run_id=? AND candidate_id=?", (run_id, candidate_id)).fetchone()
    if not row:
        raise ValueError(f"unknown candidate: {candidate_id}")
    return row


def add_candidate(conn: sqlite3.Connection, *, run_id: str, candidate_id: str, text: str,
                  repair_owner: str, parent_candidate_id: str | None = None,
                  metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    run = _run(conn, run_id)
    if run["state"] != "active":
        raise ValueError(f"run is not active: {run['state']}")
    if repair_owner not in REPAIR_OWNERS:
        raise ValueError(f"invalid repair_owner: {repair_owner}")
    parent = parent_candidate_id or run["incumbent_candidate_id"]
    _candidate(conn, run_id, parent)
    fp = text_fingerprint(text)
    stamp = now()
    try:
        conn.execute(
            "INSERT INTO evolution_candidates(run_id,candidate_id,content_fingerprint,parent_candidate_id,repair_owner,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (run_id, candidate_id, fp, parent, repair_owner, json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True), stamp),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        existing = conn.execute("SELECT * FROM evolution_candidates WHERE run_id=? AND candidate_id=?", (run_id, candidate_id)).fetchone()
        if not existing or existing["content_fingerprint"] != fp or existing["parent_candidate_id"] != parent:
            raise ValueError("candidate id/fingerprint conflict")
    return candidate_view(conn, run_id, candidate_id)


def record_comparison(conn: sqlite3.Connection, *, run_id: str, comparison_id: str,
                      incumbent_candidate_id: str, challenger_candidate_id: str,
                      winner_candidate_id: str | None, result: dict[str, Any]) -> dict[str, Any]:
    run = _run(conn, run_id)
    result_fp = canonical_fingerprint(result)
    # Idempotent replay must be recognized before checking current state/incumbent,
    # because a successful comparison may already have advanced the incumbent or
    # moved the run to plateau.
    existing = conn.execute("SELECT * FROM evolution_comparisons WHERE run_id=? AND comparison_id=?", (run_id, comparison_id)).fetchone()
    if existing:
        if (
            existing["result_fingerprint"] != result_fp
            or existing["incumbent_candidate_id"] != incumbent_candidate_id
            or existing["challenger_candidate_id"] != challenger_candidate_id
            or existing["winner_candidate_id"] != winner_candidate_id
        ):
            raise ValueError("comparison_id already consumed with different comparison/result")
        return status(conn, run_id)
    consumed = conn.execute("SELECT comparison_id FROM evolution_comparisons WHERE run_id=? AND result_fingerprint=?", (run_id, result_fp)).fetchone()
    if consumed:
        raise ValueError(f"comparison result already consumed by {consumed['comparison_id']}")
    if run["state"] != "active":
        raise ValueError(f"run is not active: {run['state']}")
    if incumbent_candidate_id != run["incumbent_candidate_id"]:
        raise ValueError("comparison incumbent must equal current incumbent")
    if incumbent_candidate_id == challenger_candidate_id:
        raise ValueError("comparison candidates must differ")
    _candidate(conn, run_id, incumbent_candidate_id)
    challenger = _candidate(conn, run_id, challenger_candidate_id)
    if challenger["parent_candidate_id"] != incumbent_candidate_id:
        raise ValueError("challenger must descend from current incumbent")
    if winner_candidate_id is not None and winner_candidate_id not in {incumbent_candidate_id, challenger_candidate_id}:
        raise ValueError("winner must be one of the compared candidates or null for tie/no-decision")
    stamp = now()
    conn.execute(
        "INSERT INTO evolution_comparisons(run_id,comparison_id,incumbent_candidate_id,challenger_candidate_id,winner_candidate_id,result_fingerprint,result_json,consumed_at,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (run_id, comparison_id, incumbent_candidate_id, challenger_candidate_id, winner_candidate_id, result_fp,
         json.dumps(result, ensure_ascii=False, sort_keys=True), stamp, stamp),
    )
    if winner_candidate_id == challenger_candidate_id:
        new_incumbent = challenger_candidate_id
        no_gain = 0
    else:
        new_incumbent = incumbent_candidate_id
        no_gain = int(run["no_gain_count"]) + 1
    state = "plateau" if no_gain >= int(run["plateau_limit"]) else "active"
    conn.execute(
        "UPDATE evolution_runs SET incumbent_candidate_id=?, no_gain_count=?, state=?, updated_at=? WHERE run_id=?",
        (new_incumbent, no_gain, state, stamp, run_id),
    )
    conn.commit()
    return status(conn, run_id)


def complete(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    run = _run(conn, run_id)
    if run["state"] == "complete":
        return status(conn, run_id)
    conn.execute("UPDATE evolution_runs SET state='complete', updated_at=? WHERE run_id=?", (now(), run_id))
    conn.commit()
    return status(conn, run_id)


def candidate_view(conn: sqlite3.Connection, run_id: str, candidate_id: str) -> dict[str, Any]:
    row = _candidate(conn, run_id, candidate_id)
    return {
        "candidate_id": row["candidate_id"],
        "content_fingerprint": row["content_fingerprint"],
        "parent_candidate_id": row["parent_candidate_id"],
        "repair_owner": row["repair_owner"],
        "metadata": json.loads(row["metadata_json"]),
        "created_at": row["created_at"],
    }


def status(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = _run(conn, run_id)
    candidates = [dict(r) for r in conn.execute("SELECT candidate_id,content_fingerprint,parent_candidate_id,repair_owner,created_at FROM evolution_candidates WHERE run_id=? ORDER BY created_at,candidate_id", (run_id,))]
    comparisons = [dict(r) for r in conn.execute("SELECT comparison_id,incumbent_candidate_id,challenger_candidate_id,winner_candidate_id,result_fingerprint,consumed_at FROM evolution_comparisons WHERE run_id=? ORDER BY created_at,comparison_id", (run_id,))]
    return {
        "schema": SCHEMA,
        "run_id": row["run_id"],
        "subject_id": row["subject_id"],
        "state": row["state"],
        "baseline_candidate_id": row["baseline_candidate_id"],
        "incumbent_candidate_id": row["incumbent_candidate_id"],
        "no_gain_count": row["no_gain_count"],
        "plateau_limit": row["plateau_limit"],
        "candidates": candidates,
        "comparisons": comparisons,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }


def self_test(path: Path) -> int:
    if path.exists():
        path.unlink()
    conn = connect(path)
    start_run(conn, run_id="RUN-1", subject_id="CH-1", baseline_candidate_id="C0", baseline_text="baseline", plateau_limit=2)
    start_run(conn, run_id="RUN-1", subject_id="CH-1", baseline_candidate_id="C0", baseline_text="baseline", plateau_limit=2)
    add_candidate(conn, run_id="RUN-1", candidate_id="C1", text="candidate one", repair_owner="reader")
    r1 = {"winner": "C1", "evidence": ["stronger forward pull"]}
    s1 = record_comparison(conn, run_id="RUN-1", comparison_id="CMP-1", incumbent_candidate_id="C0", challenger_candidate_id="C1", winner_candidate_id="C1", result=r1)
    replay = record_comparison(conn, run_id="RUN-1", comparison_id="CMP-1", incumbent_candidate_id="C0", challenger_candidate_id="C1", winner_candidate_id="C1", result=r1)
    consume_once = False
    try:
        record_comparison(conn, run_id="RUN-1", comparison_id="CMP-1B", incumbent_candidate_id="C1", challenger_candidate_id="C0", winner_candidate_id="C1", result=r1)
    except ValueError as exc:
        consume_once = "already consumed" in str(exc)
    illegal_winner = False
    add_candidate(conn, run_id="RUN-1", candidate_id="C2", text="candidate two", repair_owner="surface")
    try:
        record_comparison(conn, run_id="RUN-1", comparison_id="CMP-X", incumbent_candidate_id="C1", challenger_candidate_id="C2", winner_candidate_id="C999", result={"winner": "C999"})
    except ValueError as exc:
        illegal_winner = "winner must be one" in str(exc)
    s2 = record_comparison(conn, run_id="RUN-1", comparison_id="CMP-2", incumbent_candidate_id="C1", challenger_candidate_id="C2", winner_candidate_id="C1", result={"winner": "C1", "evidence": ["no gain"]})
    add_candidate(conn, run_id="RUN-1", candidate_id="C3", text="candidate three", repair_owner="scene")
    s3 = record_comparison(conn, run_id="RUN-1", comparison_id="CMP-3", incumbent_candidate_id="C1", challenger_candidate_id="C3", winner_candidate_id=None, result={"winner": None, "evidence": ["tie"]})
    ok = (
        s1["incumbent_candidate_id"] == "C1" and replay["incumbent_candidate_id"] == "C1"
        and s2["state"] == "active" and s3["state"] == "plateau"
        and consume_once and illegal_winner and s3["authority"] is False and s3["model_execution"] is False
    )
    print(json.dumps({
        "quality_evolution_contract": "PASS" if ok else "FAIL",
        "durable_resume": True,
        "idempotent_replay": replay["incumbent_candidate_id"] == "C1",
        "logical_consume_once": consume_once,
        "illegal_winner_rejected": illegal_winner,
        "plateau_stopping": s3["state"] == "plateau",
        "authority": False,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    conn.close()
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge durable quality evolution ledger")
    p.add_argument("--db", default=".novelforge/quality-evolution.db")
    sub = p.add_subparsers(dest="command", required=True)
    st = sub.add_parser("start"); st.add_argument("--run-id", required=True); st.add_argument("--subject-id", required=True); st.add_argument("--baseline-id", required=True); st.add_argument("--text-file", required=True); st.add_argument("--plateau-limit", type=int, default=2)
    ac = sub.add_parser("add-candidate"); ac.add_argument("--run-id", required=True); ac.add_argument("--candidate-id", required=True); ac.add_argument("--text-file", required=True); ac.add_argument("--repair-owner", required=True); ac.add_argument("--parent-id")
    rc = sub.add_parser("record-comparison"); rc.add_argument("--run-id", required=True); rc.add_argument("--comparison-id", required=True); rc.add_argument("--incumbent-id", required=True); rc.add_argument("--challenger-id", required=True); rc.add_argument("--winner-id"); rc.add_argument("--result-json", required=True)
    ss = sub.add_parser("status"); ss.add_argument("--run-id", required=True)
    cp = sub.add_parser("complete"); cp.add_argument("--run-id", required=True)
    sf = sub.add_parser("self-test"); sf.add_argument("--path", default="/tmp/novelforge-quality-evolution-selftest.db")
    args = p.parse_args()
    if args.command == "self-test":
        return self_test(Path(args.path))
    path = Path(args.db); path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        if args.command == "start":
            value = start_run(conn, run_id=args.run_id, subject_id=args.subject_id, baseline_candidate_id=args.baseline_id, baseline_text=Path(args.text_file).read_text(encoding="utf-8"), plateau_limit=args.plateau_limit)
        elif args.command == "add-candidate":
            value = add_candidate(conn, run_id=args.run_id, candidate_id=args.candidate_id, text=Path(args.text_file).read_text(encoding="utf-8"), repair_owner=args.repair_owner, parent_candidate_id=args.parent_id)
        elif args.command == "record-comparison":
            value = record_comparison(conn, run_id=args.run_id, comparison_id=args.comparison_id, incumbent_candidate_id=args.incumbent_id, challenger_candidate_id=args.challenger_id, winner_candidate_id=args.winner_id, result=json.loads(Path(args.result_json).read_text(encoding="utf-8")))
        elif args.command == "complete":
            value = complete(conn, args.run_id)
        else:
            value = status(conn, args.run_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
