#!/usr/bin/env python3
"""Non-destructive lifecycle controls for NovelForge derived memory.

Models may propose that memory is stale, contradictory, or superseded. This
module does not make that semantic judgment. It only applies an explicit,
fingerprint-bound lifecycle operation while preserving the original memory
content and source evidence.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from memory_bank import (  # noqa: E402
    add_entry,
    canonical_fingerprint,
    connect,
    export_context,
    now,
    view_entry,
)

SCHEMA = "novelforge_memory_lifecycle_v1"
OP_SCHEMA = "novelforge_memory_lifecycle_operation_v1"
DERIVED = "derived"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_lifecycle_ops(
          operation_id TEXT PRIMARY KEY,
          operation_type TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} required")
    return value.strip()


def _row(conn: sqlite3.Connection, entry_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM memory_entries WHERE entry_id=?", (entry_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown entry_id {entry_id}")
    return row


def _derived(row: sqlite3.Row) -> None:
    if row["authority"] != DERIVED:
        raise ValueError("lifecycle operations only apply to derived memory")


def _before(
    row: sqlite3.Row,
    *,
    expected_fingerprint: str,
    expected_status: str,
) -> None:
    if row["entry_fingerprint"] != expected_fingerprint:
        raise ValueError("before-state fingerprint mismatch")
    if row["status"] != expected_status:
        raise ValueError(
            f"before-state status mismatch: expected {expected_status!r}, got {row['status']!r}"
        )


def _operation_payload(operation_type: str, body: dict[str, Any]) -> dict[str, Any]:
    return {"schema": OP_SCHEMA, "operation_type": operation_type, **body}


def _operation_id(payload: dict[str, Any]) -> str:
    return "MEMOP-" + canonical_fingerprint(payload)[7:23]


def _existing_operation(
    conn: sqlite3.Connection, operation_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM memory_lifecycle_ops WHERE operation_id=?", (operation_id,)
    ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload_json"])
    return {
        **payload,
        "operation_id": row["operation_id"],
        "created_at": row["created_at"],
        "authority": False,
    }


def _record_operation(
    conn: sqlite3.Connection,
    *,
    operation_id: str,
    payload: dict[str, Any],
) -> None:
    conn.execute(
        "INSERT INTO memory_lifecycle_ops VALUES(?,?,?,?)",
        (
            operation_id,
            payload["operation_type"],
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            now(),
        ),
    )


def _record_event(
    conn: sqlite3.Connection,
    *,
    entry_id: str,
    event_type: str,
    fingerprint: str,
    detail: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO memory_events(
          entry_id,event_type,before_fingerprint,after_fingerprint,detail_json,created_at
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            entry_id,
            event_type,
            fingerprint,
            fingerprint,
            json.dumps(detail, ensure_ascii=False, sort_keys=True),
            now(),
        ),
    )


def contest(
    conn: sqlite3.Connection,
    *,
    entry_id: str,
    expected_fingerprint: str,
    evidence_ref: str,
) -> dict[str, Any]:
    """Quarantine one derived memory without changing its content or evidence."""
    evidence_ref = _text(evidence_ref, "evidence_ref")
    payload = _operation_payload(
        "contest",
        {
            "entry_id": entry_id,
            "expected_fingerprint": expected_fingerprint,
            "expected_status": "active",
            "evidence_refs": [evidence_ref],
        },
    )
    operation_id = _operation_id(payload)
    existing = _existing_operation(conn, operation_id)
    if existing:
        return {
            "schema": SCHEMA,
            "status": "already_contested",
            "idempotent": True,
            "operation": existing,
            "entry": view_entry(conn, entry_id),
            "authority": False,
        }

    row = _row(conn, entry_id)
    _derived(row)
    _before(row, expected_fingerprint=expected_fingerprint, expected_status="active")
    try:
        conn.execute("BEGIN IMMEDIATE")
        live = _row(conn, entry_id)
        _before(live, expected_fingerprint=expected_fingerprint, expected_status="active")
        conn.execute(
            "UPDATE memory_entries SET status='contested',updated_at=? WHERE entry_id=?",
            (now(), entry_id),
        )
        _record_operation(conn, operation_id=operation_id, payload=payload)
        _record_event(
            conn,
            entry_id=entry_id,
            event_type="contested",
            fingerprint=expected_fingerprint,
            detail={
                "operation_id": operation_id,
                "evidence_ref": evidence_ref,
                "content_mutated": False,
            },
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {
        "schema": SCHEMA,
        "status": "contested",
        "idempotent": False,
        "operation": _existing_operation(conn, operation_id),
        "entry": view_entry(conn, entry_id),
        "authority": False,
    }


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
    """Replace context eligibility, not evidence: both memory entries remain stored."""
    evidence_refs = [_text(x, "evidence_ref") for x in evidence_refs]
    if not evidence_refs:
        raise ValueError("at least one evidence_ref required")
    if len(evidence_refs) != len(set(evidence_refs)):
        raise ValueError("duplicate evidence_ref")
    if successor_entry_id == predecessor_entry_id:
        raise ValueError("memory cannot supersede itself")
    if expected_predecessor_status not in {"active", "contested"}:
        raise ValueError("predecessor status must be active or contested")

    payload = _operation_payload(
        "supersede",
        {
            "successor_entry_id": successor_entry_id,
            "predecessor_entry_id": predecessor_entry_id,
            "expected_successor_fingerprint": expected_successor_fingerprint,
            "expected_successor_status": "active",
            "expected_predecessor_fingerprint": expected_predecessor_fingerprint,
            "expected_predecessor_status": expected_predecessor_status,
            "evidence_refs": evidence_refs,
        },
    )
    operation_id = _operation_id(payload)
    existing = _existing_operation(conn, operation_id)
    if existing:
        return {
            "schema": SCHEMA,
            "status": "already_superseded",
            "idempotent": True,
            "operation": existing,
            "successor": view_entry(conn, successor_entry_id),
            "predecessor": view_entry(conn, predecessor_entry_id),
            "authority": False,
        }

    successor = _row(conn, successor_entry_id)
    predecessor = _row(conn, predecessor_entry_id)
    _derived(successor)
    _derived(predecessor)
    if successor["bank"] != predecessor["bank"]:
        raise ValueError("supersession requires the same memory bank")
    _before(
        successor,
        expected_fingerprint=expected_successor_fingerprint,
        expected_status="active",
    )
    _before(
        predecessor,
        expected_fingerprint=expected_predecessor_fingerprint,
        expected_status=expected_predecessor_status,
    )

    try:
        conn.execute("BEGIN IMMEDIATE")
        successor = _row(conn, successor_entry_id)
        predecessor = _row(conn, predecessor_entry_id)
        _before(
            successor,
            expected_fingerprint=expected_successor_fingerprint,
            expected_status="active",
        )
        _before(
            predecessor,
            expected_fingerprint=expected_predecessor_fingerprint,
            expected_status=expected_predecessor_status,
        )
        conn.execute(
            "UPDATE memory_entries SET status='superseded',updated_at=? WHERE entry_id=?",
            (now(), predecessor_entry_id),
        )
        _record_operation(conn, operation_id=operation_id, payload=payload)
        detail = {
            "operation_id": operation_id,
            "successor_entry_id": successor_entry_id,
            "predecessor_entry_id": predecessor_entry_id,
            "evidence_refs": evidence_refs,
            "content_mutated": False,
        }
        _record_event(
            conn,
            entry_id=predecessor_entry_id,
            event_type="superseded",
            fingerprint=expected_predecessor_fingerprint,
            detail=detail,
        )
        _record_event(
            conn,
            entry_id=successor_entry_id,
            event_type="supersedes",
            fingerprint=expected_successor_fingerprint,
            detail=detail,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return {
        "schema": SCHEMA,
        "status": "superseded",
        "idempotent": False,
        "operation": _existing_operation(conn, operation_id),
        "successor": view_entry(conn, successor_entry_id),
        "predecessor": view_entry(conn, predecessor_entry_id),
        "authority": False,
    }


def operations(
    conn: sqlite3.Connection,
    *,
    entry_id: str | None = None,
) -> list[dict[str, Any]]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM memory_lifecycle_ops ORDER BY created_at,operation_id"
    ).fetchall()
    result = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        if entry_id and entry_id not in {
            payload.get("entry_id"),
            payload.get("successor_entry_id"),
            payload.get("predecessor_entry_id"),
        }:
            continue
        result.append(
            {
                **payload,
                "operation_id": row["operation_id"],
                "created_at": row["created_at"],
                "authority": False,
            }
        )
    return result


def self_test(path: Path) -> int:
    if path.exists():
        path.unlink()
    conn = connect(path)
    ensure_schema(conn)
    accepted = add_entry(
        conn,
        entry_id="CANON",
        bank="character",
        authority="accepted",
        content={"name": "A"},
        source_refs=["canon:CHAR-A"],
        source_fingerprints=["sha256:" + "a" * 64],
    )
    old = add_entry(
        conn,
        entry_id="OLD",
        bank="character",
        authority="derived",
        content={"summary": "A avoids B."},
        source_refs=["canon:S1"],
        source_fingerprints=["sha256:" + "b" * 64],
    )
    new = add_entry(
        conn,
        entry_id="NEW",
        bank="character",
        authority="derived",
        content={"summary": "A distrusts B but still works with B."},
        source_refs=["canon:S1", "canon:S2"],
        source_fingerprints=["sha256:" + "b" * 64, "sha256:" + "c" * 64],
    )
    other = add_entry(
        conn,
        entry_id="OTHER",
        bank="relationship",
        authority="derived",
        content={"summary": "other bank"},
        source_refs=["canon:R1"],
        source_fingerprints=["sha256:" + "d" * 64],
    )

    first = contest(
        conn,
        entry_id="OLD",
        expected_fingerprint=old["entry_fingerprint"],
        evidence_ref="accepted:S2",
    )
    retry = contest(
        conn,
        entry_id="OLD",
        expected_fingerprint=old["entry_fingerprint"],
        evidence_ref="accepted:S2",
    )
    protected_blocked = False
    try:
        contest(
            conn,
            entry_id="CANON",
            expected_fingerprint=accepted["entry_fingerprint"],
            evidence_ref="review:x",
        )
    except ValueError:
        protected_blocked = True

    replacement = supersede(
        conn,
        successor_entry_id="NEW",
        predecessor_entry_id="OLD",
        expected_successor_fingerprint=new["entry_fingerprint"],
        expected_predecessor_fingerprint=old["entry_fingerprint"],
        expected_predecessor_status="contested",
        evidence_refs=["accepted:S2"],
    )
    replacement_retry = supersede(
        conn,
        successor_entry_id="NEW",
        predecessor_entry_id="OLD",
        expected_successor_fingerprint=new["entry_fingerprint"],
        expected_predecessor_fingerprint=old["entry_fingerprint"],
        expected_predecessor_status="contested",
        evidence_refs=["accepted:S2"],
    )
    cross_bank_blocked = False
    try:
        supersede(
            conn,
            successor_entry_id="OTHER",
            predecessor_entry_id="NEW",
            expected_successor_fingerprint=other["entry_fingerprint"],
            expected_predecessor_fingerprint=new["entry_fingerprint"],
            expected_predecessor_status="active",
            evidence_refs=["review:x"],
        )
    except ValueError:
        cross_bank_blocked = True

    old_after = view_entry(conn, "OLD")
    exported_ids = {x["id"] for x in export_context(conn)["items"]}
    evidence_preserved = (
        old_after["content"] == old["content"]
        and old_after["source_refs"] == old["source_refs"]
        and old_after["entry_fingerprint"] == old["entry_fingerprint"]
    )
    operation_log = operations(conn)
    ok = all(
        [
            first["status"] == "contested",
            retry["idempotent"] is True,
            protected_blocked,
            replacement["status"] == "superseded",
            replacement_retry["idempotent"] is True,
            cross_bank_blocked,
            old_after["status"] == "superseded",
            evidence_preserved,
            "MEM-OLD" not in exported_ids,
            "MEM-NEW" in exported_ids,
            len(operation_log) == 2,
        ]
    )
    print(
        json.dumps(
            {
                "memory_lifecycle_contract": "PASS" if ok else "FAIL",
                "non_destructive_contest": evidence_preserved,
                "fingerprint_bound_supersession": replacement["operation"] is not None,
                "idempotent_retry": retry["idempotent"] and replacement_retry["idempotent"],
                "protected_memory_blocked": protected_blocked,
                "cross_bank_supersession_blocked": cross_bank_blocked,
                "superseded_excluded_from_context_export": "MEM-OLD" not in exported_ids,
                "successor_context_eligible": "MEM-NEW" in exported_ids,
                "raw_evidence_preserved": evidence_preserved,
                "semantic_relevance_assigned": False,
                "content_rewritten": False,
                "canon_write": False,
                "model_execution": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    conn.close()
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(
        description="NovelForge non-destructive derived-memory lifecycle"
    )
    p.add_argument("--db", default=".novelforge/memory-bank.db")
    sub = p.add_subparsers(dest="command", required=True)

    contest_cmd = sub.add_parser("contest")
    contest_cmd.add_argument("--entry-id", required=True)
    contest_cmd.add_argument("--expected-fingerprint", required=True)
    contest_cmd.add_argument("--evidence-ref", required=True)

    supersede_cmd = sub.add_parser("supersede")
    supersede_cmd.add_argument("--successor-entry-id", required=True)
    supersede_cmd.add_argument("--predecessor-entry-id", required=True)
    supersede_cmd.add_argument("--expected-successor-fingerprint", required=True)
    supersede_cmd.add_argument("--expected-predecessor-fingerprint", required=True)
    supersede_cmd.add_argument("--expected-predecessor-status", required=True)
    supersede_cmd.add_argument(
        "--evidence-ref", action="append", dest="evidence_refs", required=True
    )

    ops_cmd = sub.add_parser("operations")
    ops_cmd.add_argument("--entry-id")

    test_cmd = sub.add_parser("self-test")
    test_cmd.add_argument(
        "--path", default="/tmp/novelforge-memory-lifecycle-selftest.db"
    )

    args = p.parse_args()
    if args.command == "self-test":
        return self_test(Path(args.path))

    conn = connect(Path(args.db))
    ensure_schema(conn)
    try:
        if args.command == "contest":
            value = contest(
                conn,
                entry_id=args.entry_id,
                expected_fingerprint=args.expected_fingerprint,
                evidence_ref=args.evidence_ref,
            )
        elif args.command == "supersede":
            value = supersede(
                conn,
                successor_entry_id=args.successor_entry_id,
                predecessor_entry_id=args.predecessor_entry_id,
                expected_successor_fingerprint=args.expected_successor_fingerprint,
                expected_predecessor_fingerprint=args.expected_predecessor_fingerprint,
                expected_predecessor_status=args.expected_predecessor_status,
                evidence_refs=args.evidence_refs,
            )
        else:
            value = operations(conn, entry_id=args.entry_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
