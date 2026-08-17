#!/usr/bin/env python3
"""Side-effect-free feedback-learning observability.

Unlike feedback_intake's mutating lifecycle owner, this module opens the existing
Learning DB read-only. It never creates tables, updates timestamps, consumes
receipts, executes a model, or exposes bounded feedback text/private reasoning.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_feedback_intake_projection_v1"
STATES = {"observed", "awaiting_semantic", "interpreted", "skipped", "persisted", "blocked", "failed"}


def _connect_ro(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).resolve()
    if not path.exists():
        raise ValueError("learning database does not exist")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _projection(row: sqlite3.Row) -> dict[str, Any]:
    normalized = json.loads(row["normalized_json"])
    target = normalized.get("target", {}) if isinstance(normalized.get("target"), dict) else {}
    return {
        "schema": SCHEMA,
        "event_id": row["event_id"],
        "event_hash": row["event_hash"],
        "status": row["status"],
        "consumer": row["consumer"],
        "project_id": row["project_id"],
        "resource_id": row["resource_id"],
        "session_id": row["session_id"],
        "run_id": row["run_id"],
        "feedback_ref": row["feedback_ref"],
        "target_ref": target.get("target_ref"),
        "artifact_ref": target.get("artifact_ref"),
        "artifact_fingerprint": target.get("artifact_fingerprint"),
        "semantic_job_fingerprint": row["semantic_job_fingerprint"],
        "semantic_result_hash": row["semantic_result_hash"],
        "capture_decision": row["capture_decision"],
        "skip_reason": row["skip_reason"],
        "evidence_id": row["evidence_id"],
        "hypothesis_id": row["hypothesis_id"],
        "hypothesis_action": row["hypothesis_action"],
        "target_hypothesis_id": row["target_hypothesis_id"],
        "version": row["version"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "side_effect_free": True,
        "feedback_text_exposed": False,
        "private_reasoning_exposed": False,
        "permissions": {
            "canon_write": False,
            "framework_write": False,
            "project_profile_write": False,
            "durable_user_taste_write": False,
        },
        "model_execution": False,
    }


def get_status(db_path: str | Path, event_id: str) -> dict[str, Any]:
    with _connect_ro(db_path) as conn:
        row = conn.execute("SELECT * FROM feedback_intake WHERE event_id=?", (event_id,)).fetchone()
    if not row:
        raise ValueError("unknown feedback intake event")
    return _projection(row)


def list_status(db_path: str | Path, *, status: str | None = None, limit: int = 50) -> dict[str, Any]:
    if status is not None and status not in STATES:
        raise ValueError("invalid status")
    limit = max(1, min(int(limit), 200))
    with _connect_ro(db_path) as conn:
        if status:
            rows = conn.execute("SELECT * FROM feedback_intake WHERE status=? ORDER BY updated_at DESC LIMIT ?", (status, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM feedback_intake ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    return {
        "schema": "novelforge_feedback_intake_list_projection_v1",
        "items": [_projection(row) for row in rows],
        "side_effect_free": True,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only NovelForge feedback-learning query")
    p.add_argument("--db", default=".novelforge/learning.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("status"); g.add_argument("--event-id", required=True)
    ls = sub.add_parser("list"); ls.add_argument("--status"); ls.add_argument("--limit", type=int, default=50)
    a = p.parse_args()
    out = get_status(a.db, a.event_id) if a.cmd == "status" else list_status(a.db, status=a.status, limit=a.limit)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
