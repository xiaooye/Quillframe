#!/usr/bin/env python3
"""Scenario fork/replay ledger for Quillframe.

Creates non-Canon exploration branches from a checkpoint or artifact state. A
branch may carry explicit state mutations and generated artifact fingerprints,
but selecting a branch only marks an exploration preference; it never mutates
Project Canon or active plans automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_scenario_fork_v1"
STATUSES = {"exploring", "selected", "discarded"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS branches(
          branch_id TEXT PRIMARY KEY,
          parent_branch_id TEXT,
          base_checkpoint_id TEXT NOT NULL,
          base_state_fingerprint TEXT NOT NULL,
          mutation_json TEXT NOT NULL,
          status TEXT NOT NULL,
          branch_fingerprint TEXT NOT NULL,
          version INTEGER NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS branch_artifacts(
          branch_id TEXT NOT NULL,
          artifact_ref TEXT NOT NULL,
          artifact_fingerprint TEXT NOT NULL,
          role TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY(branch_id, artifact_ref, artifact_fingerprint)
        );
        CREATE TABLE IF NOT EXISTS branch_events(
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          branch_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try: int(value[7:], 16)
    except ValueError as exc: raise ValueError(f"{name} invalid hex") from exc
    return value


def _branch_payload(branch_id: str, parent_branch_id: str | None, checkpoint: str,
                    base_state_fingerprint: str, mutation: dict[str, Any]) -> dict[str, Any]:
    return {
        "branch_id": branch_id,
        "parent_branch_id": parent_branch_id,
        "base_checkpoint_id": checkpoint,
        "base_state_fingerprint": base_state_fingerprint,
        "mutation": mutation,
    }


def _event(conn: sqlite3.Connection, branch_id: str, event_type: str, detail: dict[str, Any]) -> None:
    conn.execute("INSERT INTO branch_events(branch_id,event_type,detail_json,created_at) VALUES(?,?,?,?)", (branch_id, event_type, canonical(detail), now()))


def get_branch(conn: sqlite3.Connection, branch_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM branches WHERE branch_id=?", (branch_id,)).fetchone()
    if row is None: raise ValueError(f"unknown branch_id {branch_id}")
    artifacts = conn.execute("SELECT artifact_ref,artifact_fingerprint,role,created_at FROM branch_artifacts WHERE branch_id=? ORDER BY created_at,artifact_ref", (branch_id,)).fetchall()
    return {
        "schema": SCHEMA,
        "branch_id": row["branch_id"],
        "parent_branch_id": row["parent_branch_id"],
        "base_checkpoint_id": row["base_checkpoint_id"],
        "base_state_fingerprint": row["base_state_fingerprint"],
        "mutation": json.loads(row["mutation_json"]),
        "status": row["status"],
        "branch_fingerprint": row["branch_fingerprint"],
        "version": row["version"],
        "artifacts": [dict(x) for x in artifacts],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "authority": False,
    }


def create_branch(conn: sqlite3.Connection, *, branch_id: str, base_checkpoint_id: str,
                  base_state_fingerprint: str, mutation: dict[str, Any] | None = None,
                  parent_branch_id: str | None = None) -> dict[str, Any]:
    if not branch_id or not base_checkpoint_id:
        raise ValueError("branch_id/base_checkpoint_id required")
    _sha(base_state_fingerprint, "base_state_fingerprint")
    if not isinstance(mutation or {}, dict):
        raise ValueError("mutation must be object")
    mutation = mutation or {}
    if parent_branch_id is not None:
        parent = get_branch(conn, parent_branch_id)
        if parent["status"] == "discarded":
            raise ValueError("cannot fork discarded branch")
        if base_checkpoint_id != parent["base_checkpoint_id"]:
            raise ValueError("child branch must retain parent base checkpoint")
        if base_state_fingerprint != parent["base_state_fingerprint"]:
            raise ValueError("child branch must retain parent base state fingerprint")
    payload = _branch_payload(branch_id, parent_branch_id, base_checkpoint_id, base_state_fingerprint, mutation)
    branch_fingerprint = fp(payload)
    stamp = now()
    conn.execute("INSERT INTO branches VALUES(?,?,?,?,?,?,?,?,?,?)", (branch_id, parent_branch_id, base_checkpoint_id, base_state_fingerprint, canonical(mutation), "exploring", branch_fingerprint, 1, stamp, stamp))
    _event(conn, branch_id, "branch.created", payload)
    conn.commit()
    return get_branch(conn, branch_id)


def add_artifact(conn: sqlite3.Connection, *, branch_id: str, artifact_ref: str,
                 artifact_fingerprint: str, role: str) -> dict[str, Any]:
    branch = get_branch(conn, branch_id)
    if branch["status"] == "discarded": raise ValueError("cannot add artifact to discarded branch")
    if not artifact_ref or not role: raise ValueError("artifact_ref/role required")
    _sha(artifact_fingerprint, "artifact_fingerprint")
    stamp = now()
    conn.execute("INSERT OR IGNORE INTO branch_artifacts VALUES(?,?,?,?,?)", (branch_id, artifact_ref, artifact_fingerprint, role, stamp))
    _event(conn, branch_id, "artifact.recorded", {"artifact_ref": artifact_ref, "artifact_fingerprint": artifact_fingerprint, "role": role})
    conn.commit()
    return get_branch(conn, branch_id)


def set_status(conn: sqlite3.Connection, *, branch_id: str, status: str,
               expected_version: int | None = None) -> dict[str, Any]:
    if status not in STATUSES: raise ValueError("invalid status")
    row = conn.execute("SELECT * FROM branches WHERE branch_id=?", (branch_id,)).fetchone()
    if row is None: raise ValueError(f"unknown branch_id {branch_id}")
    if expected_version is not None and row["version"] != expected_version:
        raise ValueError(f"before-state mismatch: expected version {expected_version}, actual {row['version']}")
    current = row["status"]
    if current == "discarded": raise ValueError("discarded branch is final")
    if current == status: return get_branch(conn, branch_id)
    if current == "selected" and status == "exploring": raise ValueError("selected branch cannot silently revert to exploring")
    stamp = now()
    conn.execute("UPDATE branches SET status=?,version=version+1,updated_at=? WHERE branch_id=?", (status, stamp, branch_id))
    _event(conn, branch_id, f"branch.{status}", {"from": current, "to": status, "canon_write": False})
    conn.commit()
    return get_branch(conn, branch_id)


def replay_packet(conn: sqlite3.Connection, branch_id: str) -> dict[str, Any]:
    branch = get_branch(conn, branch_id)
    return {
        "schema": "quillframe_scenario_replay_packet_v1",
        "branch_id": branch_id,
        "branch_fingerprint": branch["branch_fingerprint"],
        "base_checkpoint_id": branch["base_checkpoint_id"],
        "base_state_fingerprint": branch["base_state_fingerprint"],
        "state_mutation": branch["mutation"],
        "prior_artifacts": branch["artifacts"],
        "instruction": "Resume from the referenced checkpoint/state in an isolated exploration branch. Revalidate authority and capabilities before any external/tool work.",
        "branch_is_canon": False,
        "selected_is_canon": False,
        "model_execution": False,
    }


def lineage(conn: sqlite3.Connection, branch_id: str) -> list[str]:
    out = []
    seen = set()
    current: str | None = branch_id
    while current is not None:
        if current in seen: raise ValueError("branch cycle detected")
        seen.add(current); out.append(current)
        row = conn.execute("SELECT parent_branch_id FROM branches WHERE branch_id=?", (current,)).fetchone()
        if row is None: raise ValueError(f"unknown branch_id {current}")
        current = row["parent_branch_id"]
    return list(reversed(out))


def self_test(path: Path) -> int:
    if path.exists(): path.unlink()
    conn = connect(path)
    base_fp = "sha256:" + "a" * 64
    root = create_branch(conn, branch_id="BR-A", base_checkpoint_id="CP-1", base_state_fingerprint=base_fp, mutation={"choice": "door-a"})
    child = create_branch(conn, branch_id="BR-B", parent_branch_id="BR-A", base_checkpoint_id="CP-1", base_state_fingerprint=base_fp, mutation={"choice": "door-b"})
    child2 = add_artifact(conn, branch_id="BR-B", artifact_ref="candidate:CH10-B", artifact_fingerprint="sha256:" + "b" * 64, role="review_candidate")
    stale_guard = False
    try: set_status(conn, branch_id="BR-B", status="selected", expected_version=99)
    except ValueError: stale_guard = True
    selected = set_status(conn, branch_id="BR-B", status="selected", expected_version=child2["version"])
    replay = replay_packet(conn, "BR-B")
    parent_unchanged = get_branch(conn, "BR-A")["mutation"] == {"choice": "door-a"} and get_branch(conn, "BR-A")["status"] == "exploring"
    lineage_ok = lineage(conn, "BR-B") == ["BR-A", "BR-B"]
    noncanon = replay["branch_is_canon"] is False and replay["selected_is_canon"] is False and selected["authority"] is False
    fp_bound = selected["branch_fingerprint"] == fp(_branch_payload("BR-B", "BR-A", "CP-1", base_fp, {"choice": "door-b"}))
    ok = stale_guard and parent_unchanged and lineage_ok and noncanon and fp_bound and len(selected["artifacts"]) == 1
    print(json.dumps({
        "scenario_fork_contract": "PASS" if ok else "FAIL",
        "before_state_guard": stale_guard,
        "parent_history_preserved": parent_unchanged,
        "branch_lineage": lineage_ok,
        "branch_fingerprint_bound": fp_bound,
        "selection_does_not_grant_canon": noncanon,
        "replay_packet_model_execution": False,
    }, ensure_ascii=False, indent=2))
    conn.close(); return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe scenario fork/replay ledger")
    p.add_argument("--db", default=".quillframe/scenario-forks.db")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create"); c.add_argument("--branch-id", required=True); c.add_argument("--base-checkpoint-id", required=True); c.add_argument("--base-state-fingerprint", required=True); c.add_argument("--mutation-json"); c.add_argument("--parent-branch-id")
    a = sub.add_parser("artifact"); a.add_argument("--branch-id", required=True); a.add_argument("--artifact-ref", required=True); a.add_argument("--artifact-fingerprint", required=True); a.add_argument("--role", required=True)
    s = sub.add_parser("status"); s.add_argument("--branch-id", required=True); s.add_argument("--to", choices=sorted(STATUSES), required=True); s.add_argument("--expected-version", type=int)
    r = sub.add_parser("replay"); r.add_argument("--branch-id", required=True)
    l = sub.add_parser("lineage"); l.add_argument("--branch-id", required=True)
    g = sub.add_parser("get"); g.add_argument("--branch-id", required=True)
    st = sub.add_parser("self-test"); st.add_argument("--path", default="/tmp/quillframe-scenario-fork-selftest.db")
    args = p.parse_args()
    if args.command == "self-test": return self_test(Path(args.path))
    conn = connect(Path(args.db))
    try:
        if args.command == "create":
            mutation = json.loads(Path(args.mutation_json).read_text(encoding="utf-8")) if args.mutation_json else {}
            value = create_branch(conn, branch_id=args.branch_id, base_checkpoint_id=args.base_checkpoint_id, base_state_fingerprint=args.base_state_fingerprint, mutation=mutation, parent_branch_id=args.parent_branch_id)
        elif args.command == "artifact": value = add_artifact(conn, branch_id=args.branch_id, artifact_ref=args.artifact_ref, artifact_fingerprint=args.artifact_fingerprint, role=args.role)
        elif args.command == "status": value = set_status(conn, branch_id=args.branch_id, status=args.to, expected_version=args.expected_version)
        elif args.command == "replay": value = replay_packet(conn, args.branch_id)
        elif args.command == "lineage": value = {"branch_id": args.branch_id, "lineage": lineage(conn, args.branch_id), "authority": False}
        else: value = get_branch(conn, args.branch_id)
        print(json.dumps(value, ensure_ascii=False, indent=2)); return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
