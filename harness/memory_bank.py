#!/usr/bin/env python3
"""Quillframe durable editable memory bank.

Stores source-bound memory entries and explicit author/runtime controls. It never
assigns semantic relevance: task-specific selection belongs to the model-facing
`context.select` contract. Protected Canon references cannot be mutated through
this bank; edits become proposals instead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_memory_bank_v1"
AUTHORITIES = {"locked", "accepted", "active_plan", "review", "proposal", "runtime", "learning", "corpus", "derived"}
PROTECTED = {"locked", "accepted"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS memory_entries(
          entry_id TEXT PRIMARY KEY,
          bank TEXT NOT NULL,
          authority TEXT NOT NULL,
          content_json TEXT NOT NULL,
          source_refs_json TEXT NOT NULL,
          source_fingerprints_json TEXT NOT NULL,
          parent_entry_id TEXT,
          pinned INTEGER NOT NULL DEFAULT 0,
          priority REAL NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'active',
          version INTEGER NOT NULL,
          entry_fingerprint TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memory_events(
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          entry_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          before_fingerprint TEXT,
          after_fingerprint TEXT,
          detail_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def _entry_payload(*, entry_id: str, bank: str, authority: str, content: dict[str, Any],
                   source_refs: list[str], source_fingerprints: list[str],
                   parent_entry_id: str | None, version: int) -> dict[str, Any]:
    return {
        "entry_id": entry_id,
        "bank": bank,
        "authority": authority,
        "content": content,
        "source_refs": source_refs,
        "source_fingerprints": source_fingerprints,
        "parent_entry_id": parent_entry_id,
        "version": version,
    }


def _validate_entry(*, entry_id: str, bank: str, authority: str, content: dict[str, Any],
                    source_refs: list[str], source_fingerprints: list[str]) -> None:
    if not all(isinstance(x, str) and x.strip() for x in (entry_id, bank, authority)):
        raise ValueError("entry_id/bank/authority required")
    if authority not in AUTHORITIES:
        raise ValueError("invalid authority")
    if not isinstance(content, dict):
        raise ValueError("content must be object")
    if authority == "derived":
        if not source_refs or not all(isinstance(x, str) and x.strip() for x in source_refs):
            raise ValueError("derived memory requires source_refs")
        if not source_fingerprints or not all(isinstance(x, str) and x.startswith("sha256:") for x in source_fingerprints):
            raise ValueError("derived memory requires source_fingerprints")


def add_entry(conn: sqlite3.Connection, *, entry_id: str, bank: str, authority: str,
              content: dict[str, Any], source_refs: list[str], source_fingerprints: list[str],
              parent_entry_id: str | None = None, pinned: bool = False,
              priority: float = 0) -> dict[str, Any]:
    _validate_entry(entry_id=entry_id, bank=bank, authority=authority, content=content,
                    source_refs=source_refs, source_fingerprints=source_fingerprints)
    payload = _entry_payload(entry_id=entry_id, bank=bank, authority=authority, content=content,
                             source_refs=source_refs, source_fingerprints=source_fingerprints,
                             parent_entry_id=parent_entry_id, version=1)
    fp = canonical_fingerprint(payload); stamp = now()
    try:
        conn.execute(
            "INSERT INTO memory_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (entry_id, bank, authority, json.dumps(content, ensure_ascii=False, sort_keys=True),
             json.dumps(source_refs, ensure_ascii=False), json.dumps(source_fingerprints, ensure_ascii=False),
             parent_entry_id, int(pinned), float(priority), "active", 1, fp, stamp, stamp),
        )
        conn.execute(
            "INSERT INTO memory_events(entry_id,event_type,before_fingerprint,after_fingerprint,detail_json,created_at) VALUES(?,?,?,?,?,?)",
            (entry_id, "created", None, fp, "{}", stamp),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        existing = view_entry(conn, entry_id)
        if existing["entry_fingerprint"] != fp:
            raise ValueError("entry_id already exists with different content")
    return view_entry(conn, entry_id)


def view_entry(conn: sqlite3.Connection, entry_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM memory_entries WHERE entry_id=?", (entry_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown entry_id {entry_id}")
    return {
        "schema": SCHEMA,
        "entry_id": row["entry_id"], "bank": row["bank"], "authority": row["authority"],
        "content": json.loads(row["content_json"]), "source_refs": json.loads(row["source_refs_json"]),
        "source_fingerprints": json.loads(row["source_fingerprints_json"]), "parent_entry_id": row["parent_entry_id"],
        "pinned": bool(row["pinned"]), "priority": row["priority"], "status": row["status"], "version": row["version"],
        "entry_fingerprint": row["entry_fingerprint"], "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def list_entries(conn: sqlite3.Connection, *, bank: str | None = None, authority: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT entry_id FROM memory_entries WHERE 1=1"; args: list[Any] = []
    if bank is not None: sql += " AND bank=?"; args.append(bank)
    if authority is not None: sql += " AND authority=?"; args.append(authority)
    sql += " ORDER BY pinned DESC,priority DESC,entry_id"
    return [view_entry(conn, row["entry_id"]) for row in conn.execute(sql, args)]


def _write_edit(conn: sqlite3.Connection, row: sqlite3.Row, *, content: dict[str, Any],
                expected_fingerprint: str) -> dict[str, Any]:
    if row["entry_fingerprint"] != expected_fingerprint:
        raise ValueError("before-state mismatch")
    version = int(row["version"]) + 1
    payload = _entry_payload(entry_id=row["entry_id"], bank=row["bank"], authority=row["authority"], content=content,
                             source_refs=json.loads(row["source_refs_json"]), source_fingerprints=json.loads(row["source_fingerprints_json"]),
                             parent_entry_id=row["parent_entry_id"], version=version)
    fp = canonical_fingerprint(payload); stamp = now()
    conn.execute("UPDATE memory_entries SET content_json=?,version=?,entry_fingerprint=?,updated_at=? WHERE entry_id=?", (json.dumps(content, ensure_ascii=False, sort_keys=True), version, fp, stamp, row["entry_id"]))
    conn.execute("INSERT INTO memory_events(entry_id,event_type,before_fingerprint,after_fingerprint,detail_json,created_at) VALUES(?,?,?,?,?,?)", (row["entry_id"], "edited", expected_fingerprint, fp, "{}", stamp))
    conn.commit(); return view_entry(conn, row["entry_id"])


def edit_entry(conn: sqlite3.Connection, *, entry_id: str, new_content: dict[str, Any],
               expected_fingerprint: str, proposal_id: str | None = None) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM memory_entries WHERE entry_id=?", (entry_id,)).fetchone()
    if row is None: raise ValueError(f"unknown entry_id {entry_id}")
    if row["entry_fingerprint"] != expected_fingerprint: raise ValueError("before-state mismatch")
    if row["authority"] in PROTECTED:
        pid = proposal_id or f"PROP-{entry_id}-{canonical_fingerprint(new_content)[7:15]}"
        proposal = add_entry(conn, entry_id=pid, bank=row["bank"], authority="proposal", content=new_content,
                             source_refs=[f"memory:{entry_id}"], source_fingerprints=[row["entry_fingerprint"]],
                             parent_entry_id=entry_id)
        conn.execute("UPDATE memory_entries SET status='proposal' WHERE entry_id=?", (pid,)); conn.commit()
        proposal = view_entry(conn, pid)
        return {"status": "proposal_created", "protected_entry_unchanged": True, "proposal": proposal}
    updated = _write_edit(conn, row, content=new_content, expected_fingerprint=expected_fingerprint)
    return {"status": "updated", "entry": updated}


def set_control(conn: sqlite3.Connection, *, entry_id: str, pinned: bool | None = None, priority: float | None = None) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM memory_entries WHERE entry_id=?", (entry_id,)).fetchone()
    if row is None: raise ValueError(f"unknown entry_id {entry_id}")
    next_pin = row["pinned"] if pinned is None else int(pinned)
    next_priority = row["priority"] if priority is None else float(priority)
    conn.execute("UPDATE memory_entries SET pinned=?,priority=?,updated_at=? WHERE entry_id=?", (next_pin, next_priority, now(), entry_id)); conn.commit()
    return view_entry(conn, entry_id)


def invalidate(conn: sqlite3.Connection, *, entry_id: str, evidence_ref: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM memory_entries WHERE entry_id=?", (entry_id,)).fetchone()
    if row is None: raise ValueError(f"unknown entry_id {entry_id}")
    if row["authority"] != "derived": raise ValueError("only derived memory can be invalidated")
    stamp = now(); conn.execute("UPDATE memory_entries SET status='invalidated',updated_at=? WHERE entry_id=?", (stamp, entry_id))
    conn.execute("INSERT INTO memory_events(entry_id,event_type,before_fingerprint,after_fingerprint,detail_json,created_at) VALUES(?,?,?,?,?,?)", (entry_id, "invalidated", row["entry_fingerprint"], row["entry_fingerprint"], json.dumps({"evidence_ref": evidence_ref}), stamp)); conn.commit()
    return view_entry(conn, entry_id)


def _default_stages(authority: str) -> list[str]:
    if authority == "proposal": return ["never"]
    if authority in {"learning", "corpus"}: return ["reader_engagement"]
    return ["draft"]


def export_context(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute("SELECT * FROM memory_entries WHERE status IN ('active','proposal') ORDER BY pinned DESC,priority DESC,entry_id").fetchall()
    items = []
    for row in rows:
        items.append({
            "id": f"MEM-{row['entry_id']}", "class": f"memory:{row['bank']}", "source": f"memory-bank:{row['entry_id']}",
            "source_fingerprint": row["entry_fingerprint"], "authority": row["authority"],
            "inclusion_reason": "memory_bank_export", "stages": _default_stages(row["authority"]),
            "priority": row["priority"], "pinned": bool(row["pinned"]),
            "derived": row["authority"] == "derived", "metadata": {"bank": row["bank"], "entry_version": row["version"]},
        })
    return {"schema": "quillframe_context_manifest_v1", "manifest_id": "memory-bank-export", "items": items, "authority": False}


def self_test(path: Path) -> int:
    if path.exists(): path.unlink()
    conn = connect(path)
    protected = add_entry(conn, entry_id="CANON-REF", bank="character", authority="accepted", content={"name": "A"}, source_refs=["canon:CHAR-A"], source_fingerprints=["sha256:" + "a" * 64])
    derived = add_entry(conn, entry_id="DER-1", bank="derived", authority="derived", content={"summary": "A waits outside."}, source_refs=["canon:SCN-1"], source_fingerprints=["sha256:" + "b" * 64])
    protected_edit = edit_entry(conn, entry_id="CANON-REF", new_content={"name": "B"}, expected_fingerprint=protected["entry_fingerprint"])
    original_after = view_entry(conn, "CANON-REF")
    editable = edit_entry(conn, entry_id="DER-1", new_content={"summary": "A waits in the yard."}, expected_fingerprint=derived["entry_fingerprint"])
    stale_rejected = False
    try:
        edit_entry(conn, entry_id="DER-1", new_content={"summary": "stale"}, expected_fingerprint=derived["entry_fingerprint"])
    except ValueError:
        stale_rejected = True
    set_control(conn, entry_id="DER-1", pinned=True, priority=9)
    exported = export_context(conn)
    proposal_id = protected_edit["proposal"]["entry_id"]
    proposal_item = next(x for x in exported["items"] if x["id"] == f"MEM-{proposal_id}")
    proposal_isolated = proposal_item["stages"] == ["never"]
    no_fake_relevance = all("relevance" not in x for x in exported["items"])
    ok = (
        protected_edit["status"] == "proposal_created" and protected_edit["protected_entry_unchanged"]
        and original_after["content"] == {"name": "A"} and editable["status"] == "updated"
        and stale_rejected and any(x["id"] == "MEM-DER-1" and x["pinned"] for x in exported["items"])
        and proposal_isolated and no_fake_relevance
    )
    print(json.dumps({
        "memory_bank_contract": "PASS" if ok else "FAIL", "protected_edit_to_proposal": protected_edit["status"] == "proposal_created",
        "before_state_guard": stale_rejected, "editable_derived_memory": editable["status"] == "updated",
        "proposal_pre_draft_isolation": proposal_isolated, "semantic_relevance_emitted": False,
        "context_export": True, "canon_write": False, "model_execution": False,
    }, ensure_ascii=False, indent=2))
    conn.close(); return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe durable editable memory bank")
    p.add_argument("--db", default=".quillframe/memory-bank.db")
    sub = p.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add"); add.add_argument("--entry-id", required=True); add.add_argument("--bank", required=True); add.add_argument("--authority", required=True); add.add_argument("--content-json", required=True); add.add_argument("--source-ref", action="append", dest="source_refs"); add.add_argument("--source-fingerprint", action="append", dest="source_fps"); add.add_argument("--parent-entry-id"); add.add_argument("--pinned", action="store_true"); add.add_argument("--priority", type=float, default=0)
    ls = sub.add_parser("list"); ls.add_argument("--bank"); ls.add_argument("--authority")
    ed = sub.add_parser("edit"); ed.add_argument("--entry-id", required=True); ed.add_argument("--content-json", required=True); ed.add_argument("--expected-fingerprint", required=True); ed.add_argument("--proposal-id")
    ctl = sub.add_parser("control"); ctl.add_argument("--entry-id", required=True); ctl.add_argument("--pin", action="store_true"); ctl.add_argument("--unpin", action="store_true"); ctl.add_argument("--priority", type=float)
    inv = sub.add_parser("invalidate"); inv.add_argument("--entry-id", required=True); inv.add_argument("--evidence-ref", required=True)
    sub.add_parser("export-context")
    st = sub.add_parser("self-test"); st.add_argument("--path", default="/tmp/quillframe-memory-bank-selftest.db")
    args = p.parse_args()
    if args.command == "self-test": return self_test(Path(args.path))
    conn = connect(Path(args.db))
    try:
        if args.command == "add": value = add_entry(conn, entry_id=args.entry_id, bank=args.bank, authority=args.authority, content=json.loads(args.content_json), source_refs=args.source_refs or [], source_fingerprints=args.source_fps or [], parent_entry_id=args.parent_entry_id, pinned=args.pinned)
        elif args.command == "list": value = list_entries(conn, bank=args.bank, authority=args.authority)
        elif args.command == "edit": value = edit_entry(conn, entry_id=args.entry_id, new_content=json.loads(args.content_json), expected_fingerprint=args.expected_fingerprint, proposal_id=args.proposal_id)
        elif args.command == "control":
            pin = True if args.pin else (False if args.unpin else None); value = set_control(conn, entry_id=args.entry_id, pinned=pin, priority=args.priority)
        elif args.command == "invalidate": value = invalidate(conn, entry_id=args.entry_id, evidence_ref=args.evidence_ref)
        else: value = export_context(conn)
        print(json.dumps(value, ensure_ascii=False, indent=2)); return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
