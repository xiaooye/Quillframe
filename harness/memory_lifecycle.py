#!/usr/bin/env python3
"""Fingerprint-bound, non-destructive lifecycle operations for derived memory."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "harness") not in sys.path:
    sys.path.insert(0, str(ROOT / "harness"))
from memory_bank import add_entry, canonical_fingerprint, connect, export_context, now, view_entry  # noqa: E402

SCHEMA = "novelforge_memory_lifecycle_v1"
OP_SCHEMA = "novelforge_memory_lifecycle_operation_v1"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS memory_lifecycle_ops(
        operation_id TEXT PRIMARY KEY,
        operation_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.commit()


def _row(conn: sqlite3.Connection, entry_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM memory_entries WHERE entry_id=?", (entry_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown entry_id {entry_id}")
    return row


def _require_derived(row: sqlite3.Row) -> None:
    if row["authority"] != "derived":
        raise ValueError("lifecycle operations only apply to derived memory")


def _require_before(row: sqlite3.Row, fingerprint: str, status: str) -> None:
    if row["entry_fingerprint"] != fingerprint:
        raise ValueError("before-state fingerprint mismatch")
    if row["status"] != status:
        raise ValueError(f"before-state status mismatch: expected {status!r}, got {row['status']!r}")


def _evidence(values: list[str]) -> list[str]:
    values = [v.strip() for v in values if isinstance(v, str) and v.strip()]
    if not values:
        raise ValueError("at least one evidence_ref required")
    if len(values) != len(set(values)):
        raise ValueError("duplicate evidence_ref")
    return values


def _payload(kind: str, body: dict[str, Any]) -> dict[str, Any]:
    return {"schema": OP_SCHEMA, "operation_type": kind, **body}


def _op_id(payload: dict[str, Any]) -> str:
    return "MEMOP-" + canonical_fingerprint(payload)[7:23]


def _read_op(conn: sqlite3.Connection, operation_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM memory_lifecycle_ops WHERE operation_id=?", (operation_id,)).fetchone()
    if row is None:
        return None
    return {
        **json.loads(row["payload_json"]),
        "operation_id": row["operation_id"],
        "created_at": row["created_at"],
        "authority": False,
    }


def _record(conn: sqlite3.Connection, operation_id: str, payload: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO memory_lifecycle_ops VALUES(?,?,?,?)",
        (operation_id, payload["operation_type"], json.dumps(payload, ensure_ascii=False, sort_keys=True), now()),
    )


def _event(conn: sqlite3.Connection, entry_id: str, event_type: str, fp: str, detail: dict[str, Any]) -> None:
    conn.execute(
        """INSERT INTO memory_events(
        entry_id,event_type,before_fingerprint,after_fingerprint,detail_json,created_at
        ) VALUES(?,?,?,?,?,?)""",
        (entry_id, event_type, fp, fp, json.dumps(detail, ensure_ascii=False, sort_keys=True), now()),
    )


def contest(conn: sqlite3.Connection, *, entry_id: str, expected_fingerprint: str, evidence_ref: str) -> dict[str, Any]:
    """Quarantine active derived memory; content and source evidence remain unchanged."""
    evidence_refs = _evidence([evidence_ref])
    payload = _payload("contest", {
        "entry_id": entry_id,
        "expected_fingerprint": expected_fingerprint,
        "expected_status": "active",
        "evidence_refs": evidence_refs,
    })
    operation_id = _op_id(payload)

    row = _row(conn, entry_id)
    _require_derived(row)
    existing = _read_op(conn, operation_id)
    if existing:
        return {"schema": SCHEMA, "status": "already_contested", "idempotent": True,
                "operation": existing, "entry": view_entry(conn, entry_id), "authority": False}
    _require_before(row, expected_fingerprint, "active")

    try:
        conn.execute("BEGIN IMMEDIATE")
        _require_before(_row(conn, entry_id), expected_fingerprint, "active")
        conn.execute("UPDATE memory_entries SET status='contested',updated_at=? WHERE entry_id=?", (now(), entry_id))
        _record(conn, operation_id, payload)
        _event(conn, entry_id, "contested", expected_fingerprint, {
            "operation_id": operation_id, "evidence_refs": evidence_refs, "content_mutated": False,
        })
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"schema": SCHEMA, "status": "contested", "idempotent": False,
            "operation": _read_op(conn, operation_id), "entry": view_entry(conn, entry_id), "authority": False}


def supersede(
    conn: sqlite3.Connection,
    *,
    successor_entry_id: str,
    predecessor_entry_id: str,
    expected_successor_fingerprint: str,
    expected_predecessor_fingerprint: str,
    expected_predecessor_status: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    """Retire predecessor context eligibility while preserving both entries and their evidence."""
    evidence_refs = _evidence(evidence_refs)
    if successor_entry_id == predecessor_entry_id:
        raise ValueError("memory cannot supersede itself")
    if expected_predecessor_status not in {"active", "contested"}:
        raise ValueError("predecessor status must be active or contested")

    payload = _payload("supersede", {
        "successor_entry_id": successor_entry_id,
        "predecessor_entry_id": predecessor_entry_id,
        "expected_successor_fingerprint": expected_successor_fingerprint,
        "expected_successor_status": "active",
        "expected_predecessor_fingerprint": expected_predecessor_fingerprint,
        "expected_predecessor_status": expected_predecessor_status,
        "evidence_refs": evidence_refs,
    })
    operation_id = _op_id(payload)

    successor, predecessor = _row(conn, successor_entry_id), _row(conn, predecessor_entry_id)
    _require_derived(successor)
    _require_derived(predecessor)
    existing = _read_op(conn, operation_id)
    if existing:
        return {"schema": SCHEMA, "status": "already_superseded", "idempotent": True,
                "operation": existing, "successor": view_entry(conn, successor_entry_id),
                "predecessor": view_entry(conn, predecessor_entry_id), "authority": False}
    if successor["bank"] != predecessor["bank"]:
        raise ValueError("supersession requires the same memory bank")
    _require_before(successor, expected_successor_fingerprint, "active")
    _require_before(predecessor, expected_predecessor_fingerprint, expected_predecessor_status)

    try:
        conn.execute("BEGIN IMMEDIATE")
        _require_before(_row(conn, successor_entry_id), expected_successor_fingerprint, "active")
        _require_before(_row(conn, predecessor_entry_id), expected_predecessor_fingerprint, expected_predecessor_status)
        conn.execute("UPDATE memory_entries SET status='superseded',updated_at=? WHERE entry_id=?",
                     (now(), predecessor_entry_id))
        _record(conn, operation_id, payload)
        detail = {
            "operation_id": operation_id,
            "successor_entry_id": successor_entry_id,
            "predecessor_entry_id": predecessor_entry_id,
            "evidence_refs": evidence_refs,
            "content_mutated": False,
        }
        _event(conn, predecessor_entry_id, "superseded", expected_predecessor_fingerprint, detail)
        _event(conn, successor_entry_id, "supersedes", expected_successor_fingerprint, detail)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"schema": SCHEMA, "status": "superseded", "idempotent": False,
            "operation": _read_op(conn, operation_id), "successor": view_entry(conn, successor_entry_id),
            "predecessor": view_entry(conn, predecessor_entry_id), "authority": False}


def operations(conn: sqlite3.Connection, entry_id: str | None = None) -> list[dict[str, Any]]:
    ensure_schema(conn)
    result = []
    for row in conn.execute("SELECT * FROM memory_lifecycle_ops ORDER BY created_at,operation_id"):
        payload = json.loads(row["payload_json"])
        participants = {payload.get("entry_id"), payload.get("successor_entry_id"), payload.get("predecessor_entry_id")}
        if entry_id and entry_id not in participants:
            continue
        result.append({**payload, "operation_id": row["operation_id"], "created_at": row["created_at"], "authority": False})
    return result


def self_test(path: Path) -> int:
    if path.exists():
        path.unlink()
    conn = connect(path)
    ensure_schema(conn)
    accepted = add_entry(conn, entry_id="CANON", bank="character", authority="accepted", content={"name": "A"},
                         source_refs=["canon:CHAR-A"], source_fingerprints=["sha256:" + "a" * 64])
    old = add_entry(conn, entry_id="OLD", bank="character", authority="derived", content={"summary": "A avoids B."},
                    source_refs=["canon:S1"], source_fingerprints=["sha256:" + "b" * 64])
    new = add_entry(conn, entry_id="NEW", bank="character", authority="derived",
                    content={"summary": "A distrusts B but still works with B."},
                    source_refs=["canon:S1", "canon:S2"],
                    source_fingerprints=["sha256:" + "b" * 64, "sha256:" + "c" * 64])
    other = add_entry(conn, entry_id="OTHER", bank="relationship", authority="derived", content={"summary": "other"},
                      source_refs=["canon:R1"], source_fingerprints=["sha256:" + "d" * 64])

    first = contest(conn, entry_id="OLD", expected_fingerprint=old["entry_fingerprint"], evidence_ref="accepted:S2")
    retry = contest(conn, entry_id="OLD", expected_fingerprint=old["entry_fingerprint"], evidence_ref="accepted:S2")
    protected_blocked = False
    try:
        contest(conn, entry_id="CANON", expected_fingerprint=accepted["entry_fingerprint"], evidence_ref="review:x")
    except ValueError:
        protected_blocked = True

    replacement = supersede(
        conn, successor_entry_id="NEW", predecessor_entry_id="OLD",
        expected_successor_fingerprint=new["entry_fingerprint"],
        expected_predecessor_fingerprint=old["entry_fingerprint"],
        expected_predecessor_status="contested", evidence_refs=["accepted:S2"])
    replacement_retry = supersede(
        conn, successor_entry_id="NEW", predecessor_entry_id="OLD",
        expected_successor_fingerprint=new["entry_fingerprint"],
        expected_predecessor_fingerprint=old["entry_fingerprint"],
        expected_predecessor_status="contested", evidence_refs=["accepted:S2"])

    cross_bank_blocked = False
    try:
        supersede(
            conn, successor_entry_id="OTHER", predecessor_entry_id="NEW",
            expected_successor_fingerprint=other["entry_fingerprint"],
            expected_predecessor_fingerprint=new["entry_fingerprint"],
            expected_predecessor_status="active", evidence_refs=["review:x"])
    except ValueError:
        cross_bank_blocked = True

    old_after = view_entry(conn, "OLD")
    exported_ids = {x["id"] for x in export_context(conn)["items"]}
    preserved = (old_after["content"] == old["content"] and
                 old_after["source_refs"] == old["source_refs"] and
                 old_after["entry_fingerprint"] == old["entry_fingerprint"])
    ok = all([
        first["status"] == "contested", retry["idempotent"], protected_blocked,
        replacement["status"] == "superseded", replacement_retry["idempotent"], cross_bank_blocked,
        old_after["status"] == "superseded", preserved, "MEM-OLD" not in exported_ids,
        "MEM-NEW" in exported_ids, len(operations(conn)) == 2,
    ])
    print(json.dumps({
        "memory_lifecycle_contract": "PASS" if ok else "FAIL",
        "non_destructive_contest": preserved,
        "fingerprint_bound_supersession": replacement["operation"] is not None,
        "idempotent_retry": retry["idempotent"] and replacement_retry["idempotent"],
        "protected_memory_blocked": protected_blocked,
        "cross_bank_supersession_blocked": cross_bank_blocked,
        "superseded_excluded_from_context_export": "MEM-OLD" not in exported_ids,
        "successor_context_eligible": "MEM-NEW" in exported_ids,
        "raw_evidence_preserved": preserved,
        "semantic_relevance_assigned": False,
        "content_rewritten": False,
        "canon_write": False,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    conn.close()
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge non-destructive derived-memory lifecycle")
    p.add_argument("--db", default=".novelforge/memory-bank.db")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("contest")
    c.add_argument("--entry-id", required=True)
    c.add_argument("--expected-fingerprint", required=True)
    c.add_argument("--evidence-ref", required=True)
    s = sub.add_parser("supersede")
    s.add_argument("--successor-entry-id", required=True)
    s.add_argument("--predecessor-entry-id", required=True)
    s.add_argument("--expected-successor-fingerprint", required=True)
    s.add_argument("--expected-predecessor-fingerprint", required=True)
    s.add_argument("--expected-predecessor-status", required=True)
    s.add_argument("--evidence-ref", action="append", dest="evidence_refs", required=True)
    o = sub.add_parser("operations")
    o.add_argument("--entry-id")
    t = sub.add_parser("self-test")
    t.add_argument("--path", default="/tmp/novelforge-memory-lifecycle-selftest.db")
    args = p.parse_args()

    if args.command == "self-test":
        return self_test(Path(args.path))
    conn = connect(Path(args.db))
    ensure_schema(conn)
    try:
        if args.command == "contest":
            result = contest(conn, entry_id=args.entry_id, expected_fingerprint=args.expected_fingerprint,
                             evidence_ref=args.evidence_ref)
        elif args.command == "supersede":
            result = supersede(
                conn, successor_entry_id=args.successor_entry_id, predecessor_entry_id=args.predecessor_entry_id,
                expected_successor_fingerprint=args.expected_successor_fingerprint,
                expected_predecessor_fingerprint=args.expected_predecessor_fingerprint,
                expected_predecessor_status=args.expected_predecessor_status, evidence_refs=args.evidence_refs)
        else:
            result = operations(conn, args.entry_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
