#!/usr/bin/env python3
"""Durable authority-aware memory bank for NovelForge 7.2.

The bank stores editable runtime/derived/project-proposal memory without turning
memory into Canon. Protected `locked`/`accepted` entries are reference snapshots:
an edit creates a proposal entry instead of mutating the protected row.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_memory_bank_v1"
AUTHORITIES = {"locked", "accepted", "active_plan", "review", "proposal", "runtime", "learning", "corpus", "derived"}
PROTECTED = {"locked", "accepted"}
BANKS = {"context", "character", "relationship", "thread", "style", "learning", "runtime", "corpus", "derived"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS memory_entries(
      entry_id TEXT PRIMARY KEY,
      bank TEXT NOT NULL,
      authority TEXT NOT NULL,
      status TEXT NOT NULL,
      content_json TEXT NOT NULL,
      source_refs_json TEXT NOT NULL,
      source_fingerprints_json TEXT NOT NULL,
      entry_fingerprint TEXT NOT NULL,
      version INTEGER NOT NULL,
      parent_entry_id TEXT,
      pinned INTEGER NOT NULL DEFAULT 0,
      priority REAL NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(parent_entry_id) REFERENCES memory_entries(entry_id)
    );
    CREATE TABLE IF NOT EXISTS memory_edits(
      edit_id TEXT PRIMARY KEY,
      entry_id TEXT NOT NULL,
      before_fingerprint TEXT NOT NULL,
      after_fingerprint TEXT,
      action TEXT NOT NULL,
      proposal_entry_id TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY(entry_id) REFERENCES memory_entries(entry_id)
    );
    """)
    return conn


def _normalize_sources(source_refs: Any, source_fingerprints: Any, authority: str) -> tuple[list[str], list[str]]:
    refs = source_refs or []
    fps = source_fingerprints or []
    if not isinstance(refs, list) or not all(isinstance(x, str) and x.strip() for x in refs):
        raise ValueError("source_refs must be a list of non-empty strings")
    if not isinstance(fps, list) or not all(isinstance(x, str) and x.startswith("sha256:") for x in fps):
        raise ValueError("source_fingerprints must be sha256 strings")
    if authority in {"locked", "accepted", "derived"} and (not refs or not fps):
        raise ValueError(f"{authority} memory requires provenance refs + fingerprints")
    return refs, fps


def _payload(bank: str, authority: str, content: Any, refs: list[str], fps: list[str], parent: str | None) -> dict[str, Any]:
    return {"bank": bank, "authority": authority, "content": content, "source_refs": refs, "source_fingerprints": fps, "parent_entry_id": parent}


def add_entry(conn: sqlite3.Connection, *, entry_id: str, bank: str, authority: str, content: Any,
              source_refs: list[str] | None = None, source_fingerprints: list[str] | None = None,
              parent_entry_id: str | None = None, pinned: bool = False, priority: float = 0.0,
              status: str = "active") -> dict[str, Any]:
    if bank not in BANKS:
        raise ValueError(f"invalid bank: {bank}")
    if authority not in AUTHORITIES:
        raise ValueError(f"invalid authority: {authority}")
    if not isinstance(entry_id, str) or not entry_id.strip():
        raise ValueError("entry_id required")
    if isinstance(priority, bool) or not isinstance(priority, (int, float)):
        raise ValueError("priority must be numeric")
    refs, fps = _normalize_sources(source_refs, source_fingerprints, authority)
    if parent_entry_id:
        _entry(conn, parent_entry_id)
    fp = fingerprint(_payload(bank, authority, content, refs, fps, parent_entry_id))
    stamp = now()
    try:
        conn.execute(
            "INSERT INTO memory_entries(entry_id,bank,authority,status,content_json,source_refs_json,source_fingerprints_json,entry_fingerprint,version,parent_entry_id,pinned,priority,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (entry_id, bank, authority, status, json.dumps(content, ensure_ascii=False, sort_keys=True), json.dumps(refs, ensure_ascii=False), json.dumps(fps), fp, 1, parent_entry_id, 1 if pinned else 0, float(priority), stamp, stamp),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        existing = _entry(conn, entry_id)
        if existing["entry_fingerprint"] != fp:
            raise ValueError("entry_id already exists with different content")
    return view_entry(conn, entry_id)


def _entry(conn: sqlite3.Connection, entry_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM memory_entries WHERE entry_id=?", (entry_id,)).fetchone()
    if not row:
        raise ValueError(f"unknown memory entry: {entry_id}")
    return row


def view_entry(conn: sqlite3.Connection, entry_id: str) -> dict[str, Any]:
    r = _entry(conn, entry_id)
    return {
        "entry_id": r["entry_id"], "bank": r["bank"], "authority": r["authority"], "status": r["status"],
        "content": json.loads(r["content_json"]), "source_refs": json.loads(r["source_refs_json"]),
        "source_fingerprints": json.loads(r["source_fingerprints_json"]), "entry_fingerprint": r["entry_fingerprint"],
        "version": r["version"], "parent_entry_id": r["parent_entry_id"], "pinned": bool(r["pinned"]),
        "priority": r["priority"], "created_at": r["created_at"], "updated_at": r["updated_at"],
        "canon_authority": False, "direct_canon_write": False,
    }


def list_entries(conn: sqlite3.Connection, bank: str | None = None, authority: str | None = None) -> dict[str, Any]:
    clauses: list[str] = []; params: list[Any] = []
    if bank:
        if bank not in BANKS: raise ValueError(f"invalid bank: {bank}")
        clauses.append("bank=?"); params.append(bank)
    if authority:
        if authority not in AUTHORITIES: raise ValueError(f"invalid authority: {authority}")
        clauses.append("authority=?"); params.append(authority)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = conn.execute("SELECT entry_id FROM memory_entries" + where + " ORDER BY pinned DESC,priority DESC,updated_at DESC,entry_id", params).fetchall()
    return {"schema": SCHEMA, "entries": [view_entry(conn, r["entry_id"]) for r in rows], "authority": False, "model_execution": False}


def edit_entry(conn: sqlite3.Connection, *, entry_id: str, new_content: Any, expected_fingerprint: str,
               proposal_id: str | None = None) -> dict[str, Any]:
    row = _entry(conn, entry_id)
    if row["entry_fingerprint"] != expected_fingerprint:
        raise ValueError("before-state fingerprint mismatch")
    if row["authority"] in PROTECTED:
        proposal_entry_id = proposal_id or f"PROP-{entry_id}-{row['version'] + 1}"
        result = add_entry(
            conn, entry_id=proposal_entry_id, bank=row["bank"], authority="proposal", content=new_content,
            source_refs=[f"memory:{entry_id}"], source_fingerprints=[row["entry_fingerprint"]],
            parent_entry_id=entry_id, pinned=bool(row["pinned"]), priority=float(row["priority"]), status="proposal",
        )
        edit_id = f"EDIT-{fingerprint({'entry': entry_id, 'proposal': proposal_entry_id})[7:19]}"
        conn.execute(
            "INSERT OR IGNORE INTO memory_edits(edit_id,entry_id,before_fingerprint,after_fingerprint,action,proposal_entry_id,created_at) VALUES(?,?,?,?,?,?,?)",
            (edit_id, entry_id, row["entry_fingerprint"], result["entry_fingerprint"], "protected_edit_to_proposal", proposal_entry_id, now()),
        ); conn.commit()
        return {"status": "proposal_created", "protected_entry_unchanged": True, "proposal": result, "canon_write": False}
    refs = json.loads(row["source_refs_json"]); fps = json.loads(row["source_fingerprints_json"])
    new_fp = fingerprint(_payload(row["bank"], row["authority"], new_content, refs, fps, row["parent_entry_id"]))
    stamp = now(); version = int(row["version"]) + 1
    conn.execute("UPDATE memory_entries SET content_json=?,entry_fingerprint=?,version=?,updated_at=? WHERE entry_id=?", (json.dumps(new_content, ensure_ascii=False, sort_keys=True), new_fp, version, stamp, entry_id))
    edit_id = f"EDIT-{fingerprint({'entry': entry_id, 'before': expected_fingerprint, 'after': new_fp})[7:19]}"
    conn.execute("INSERT OR IGNORE INTO memory_edits(edit_id,entry_id,before_fingerprint,after_fingerprint,action,proposal_entry_id,created_at) VALUES(?,?,?,?,?,?,?)", (edit_id, entry_id, expected_fingerprint, new_fp, "edit", None, stamp))
    conn.commit()
    return {"status": "updated", "entry": view_entry(conn, entry_id), "canon_write": False}


def set_control(conn: sqlite3.Connection, *, entry_id: str, pinned: bool | None = None, priority: float | None = None) -> dict[str, Any]:
    row = _entry(conn, entry_id)
    values = {"pinned": bool(row["pinned"]), "priority": float(row["priority"])}
    if pinned is not None: values["pinned"] = bool(pinned)
    if priority is not None:
        if isinstance(priority, bool) or not isinstance(priority, (int, float)): raise ValueError("priority must be numeric")
        values["priority"] = float(priority)
    conn.execute("UPDATE memory_entries SET pinned=?,priority=?,updated_at=? WHERE entry_id=?", (1 if values["pinned"] else 0, values["priority"], now(), entry_id)); conn.commit()
    return view_entry(conn, entry_id)


def export_context(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute("SELECT * FROM memory_entries WHERE status IN ('active','proposal') ORDER BY pinned DESC,priority DESC,entry_id").fetchall()
    items = []
    for row in rows:
        items.append({
            "id": f"MEM-{row['entry_id']}", "class": f"memory:{row['bank']}", "source": f"memory-bank:{row['entry_id']}",
            "source_fingerprint": row["entry_fingerprint"], "authority": row["authority"],
            "inclusion_reason": "memory_bank_export", "stages": ["writer_pre_draft"] if row["authority"] not in {"learning", "corpus"} else ["post_draft_critic"],
            "relevance": 0.5, "priority": row["priority"], "pinned": bool(row["pinned"]),
            "derived": row["authority"] == "derived", "metadata": {"bank": row["bank"], "entry_version": row["version"]},
        })
    return {"schema": "novelforge_context_manifest_v1", "manifest_id": "memory-bank-export", "items": items, "authority": False}


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
    ok = (
        protected_edit["status"] == "proposal_created" and protected_edit["protected_entry_unchanged"]
        and original_after["content"] == {"name": "A"} and editable["status"] == "updated"
        and stale_rejected and any(x["id"] == "MEM-DER-1" and x["pinned"] for x in exported["items"])
    )
    print(json.dumps({
        "memory_bank_contract": "PASS" if ok else "FAIL", "protected_edit_to_proposal": protected_edit["status"] == "proposal_created",
        "before_state_guard": stale_rejected, "editable_derived_memory": editable["status"] == "updated",
        "context_export": True, "canon_write": False, "model_execution": False,
    }, ensure_ascii=False, indent=2))
    conn.close(); return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge durable editable memory bank")
    p.add_argument("--db", default=".novelforge/memory-bank.db")
    sub = p.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add"); add.add_argument("--entry-id", required=True); add.add_argument("--bank", required=True); add.add_argument("--authority", required=True); add.add_argument("--content-json", required=True); add.add_argument("--source-ref", action="append", dest="source_refs"); add.add_argument("--source-fingerprint", action="append", dest="source_fps"); add.add_argument("--parent-entry-id"); add.add_argument("--pinned", action="store_true"); add.add_argument("--priority", type=float, default=0)
    ls = sub.add_parser("list"); ls.add_argument("--bank"); ls.add_argument("--authority")
    ed = sub.add_parser("edit"); ed.add_argument("--entry-id", required=True); ed.add_argument("--content-json", required=True); ed.add_argument("--expected-fingerprint", required=True); ed.add_argument("--proposal-id")
    ctl = sub.add_parser("control"); ctl.add_argument("--entry-id", required=True); ctl.add_argument("--pin", action="store_true"); ctl.add_argument("--unpin", action="store_true"); ctl.add_argument("--priority", type=float)
    sub.add_parser("export-context")
    st = sub.add_parser("self-test"); st.add_argument("--path", default="/tmp/novelforge-memory-bank-selftest.db")
    args = p.parse_args()
    if args.command == "self-test": return self_test(Path(args.path))
    path = Path(args.db); path.parent.mkdir(parents=True, exist_ok=True); conn = connect(path)
    try:
        if args.command == "add":
            value = add_entry(conn, entry_id=args.entry_id, bank=args.bank, authority=args.authority, content=json.loads(Path(args.content_json).read_text(encoding="utf-8")), source_refs=args.source_refs, source_fingerprints=args.source_fps, parent_entry_id=args.parent_entry_id, pinned=args.pinned, priority=args.priority)
        elif args.command == "list": value = list_entries(conn, bank=args.bank, authority=args.authority)
        elif args.command == "edit": value = edit_entry(conn, entry_id=args.entry_id, new_content=json.loads(Path(args.content_json).read_text(encoding="utf-8")), expected_fingerprint=args.expected_fingerprint, proposal_id=args.proposal_id)
        elif args.command == "control":
            if args.pin and args.unpin: raise ValueError("choose --pin or --unpin, not both")
            value = set_control(conn, entry_id=args.entry_id, pinned=True if args.pin else (False if args.unpin else None), priority=args.priority)
        else: value = export_context(conn)
        print(json.dumps(value, ensure_ascii=False, indent=2)); return 0
    finally: conn.close()


if __name__ == "__main__": raise SystemExit(main())
