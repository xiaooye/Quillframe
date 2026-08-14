#!/usr/bin/env python3
"""Durable reader-expectation ledger for NovelForge.

Tracks questions, promises, setups and other reader-facing obligations across
long horizons. This is diagnostic/editorial state, not Project Canon. It does
not infer expectations from prose by itself and performs no model execution.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "novelforge_reader_expectation_v1"
KINDS = {"question", "promise", "setup", "relationship", "goal", "mystery"}
STATUSES = {"open", "partial", "paid", "invalidated", "abandoned"}
FINAL = {"paid", "invalidated", "abandoned"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS expectations(
          expectation_id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          scope TEXT NOT NULL,
          description TEXT NOT NULL,
          opened_order INTEGER NOT NULL,
          due_by_order INTEGER,
          last_touched_order INTEGER NOT NULL,
          salience REAL NOT NULL,
          status TEXT NOT NULL,
          source_ref TEXT NOT NULL,
          source_fingerprint TEXT,
          version INTEGER NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS expectation_events(
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          expectation_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          at_order INTEGER NOT NULL,
          detail TEXT,
          evidence_ref TEXT,
          created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def _row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "expectation_id": row["expectation_id"],
        "kind": row["kind"],
        "scope": row["scope"],
        "description": row["description"],
        "opened_order": row["opened_order"],
        "due_by_order": row["due_by_order"],
        "last_touched_order": row["last_touched_order"],
        "salience": row["salience"],
        "status": row["status"],
        "source_ref": row["source_ref"],
        "source_fingerprint": row["source_fingerprint"],
        "version": row["version"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "authority": False,
    }


def _order(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _salience(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("salience must be numeric")
    value = float(value)
    if value < 0 or value > 1:
        raise ValueError("salience must be between 0 and 1")
    return value


def open_expectation(conn: sqlite3.Connection, *, expectation_id: str, kind: str, scope: str,
                     description: str, opened_order: int, source_ref: str,
                     due_by_order: int | None = None, salience: float = 0.5,
                     source_fingerprint: str | None = None) -> dict[str, Any]:
    if not expectation_id or not scope or not description or not source_ref:
        raise ValueError("expectation_id/scope/description/source_ref required")
    if kind not in KINDS:
        raise ValueError("invalid kind")
    opened = _order(opened_order, "opened_order")
    due = None if due_by_order is None else _order(due_by_order, "due_by_order")
    if due is not None and due < opened:
        raise ValueError("due_by_order precedes opened_order")
    salience = _salience(salience)
    stamp = now()
    conn.execute(
        "INSERT INTO expectations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (expectation_id, kind, scope, description, opened, due, opened, salience, "open",
         source_ref, source_fingerprint, 1, stamp, stamp),
    )
    conn.execute(
        "INSERT INTO expectation_events(expectation_id,event_type,at_order,detail,evidence_ref,created_at) VALUES(?,?,?,?,?,?)",
        (expectation_id, "opened", opened, description, source_ref, stamp),
    )
    conn.commit()
    return get_expectation(conn, expectation_id)


def get_expectation(conn: sqlite3.Connection, expectation_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM expectations WHERE expectation_id=?", (expectation_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown expectation_id {expectation_id}")
    return _row(row)


def _guard(row: sqlite3.Row, expected_version: int | None) -> None:
    if expected_version is not None and row["version"] != expected_version:
        raise ValueError(f"before-state mismatch: expected version {expected_version}, actual {row['version']}")


def touch(conn: sqlite3.Connection, *, expectation_id: str, at_order: int, evidence_ref: str,
          detail: str | None = None, salience: float | None = None,
          expected_version: int | None = None) -> dict[str, Any]:
    at = _order(at_order, "at_order")
    row = conn.execute("SELECT * FROM expectations WHERE expectation_id=?", (expectation_id,)).fetchone()
    if row is None: raise ValueError(f"unknown expectation_id {expectation_id}")
    _guard(row, expected_version)
    if row["status"] in FINAL: raise ValueError("cannot touch final expectation")
    if at < row["opened_order"] or at < row["last_touched_order"]:
        raise ValueError("touch order cannot move backward")
    next_salience = row["salience"] if salience is None else _salience(salience)
    stamp = now()
    conn.execute("UPDATE expectations SET last_touched_order=?,salience=?,version=version+1,updated_at=? WHERE expectation_id=?", (at, next_salience, stamp, expectation_id))
    conn.execute("INSERT INTO expectation_events(expectation_id,event_type,at_order,detail,evidence_ref,created_at) VALUES(?,?,?,?,?,?)", (expectation_id, "touched", at, detail, evidence_ref, stamp))
    conn.commit()
    return get_expectation(conn, expectation_id)


def resolve(conn: sqlite3.Connection, *, expectation_id: str, status: str, at_order: int,
            evidence_ref: str, detail: str | None = None,
            expected_version: int | None = None) -> dict[str, Any]:
    if status not in {"partial", "paid", "invalidated", "abandoned"}:
        raise ValueError("invalid resolution status")
    at = _order(at_order, "at_order")
    row = conn.execute("SELECT * FROM expectations WHERE expectation_id=?", (expectation_id,)).fetchone()
    if row is None: raise ValueError(f"unknown expectation_id {expectation_id}")
    _guard(row, expected_version)
    if row["status"] in FINAL:
        raise ValueError("expectation already final")
    if at < row["last_touched_order"]:
        raise ValueError("resolution order cannot move backward")
    stamp = now()
    conn.execute("UPDATE expectations SET status=?,last_touched_order=?,version=version+1,updated_at=? WHERE expectation_id=?", (status, at, stamp, expectation_id))
    conn.execute("INSERT INTO expectation_events(expectation_id,event_type,at_order,detail,evidence_ref,created_at) VALUES(?,?,?,?,?,?)", (expectation_id, status, at, detail, evidence_ref, stamp))
    conn.commit()
    return get_expectation(conn, expectation_id)


def pressure_report(conn: sqlite3.Connection, *, current_order: int, dormant_after: int = 3) -> dict[str, Any]:
    current = _order(current_order, "current_order")
    dormant_after = _order(dormant_after, "dormant_after")
    rows = conn.execute("SELECT * FROM expectations WHERE status IN ('open','partial') ORDER BY salience DESC,opened_order,expectation_id").fetchall()
    overdue = []; dormant = []; active = []
    for row in rows:
        item = _row(row)
        gap = current - row["last_touched_order"]
        item["silence_gap"] = gap
        due = row["due_by_order"]
        if due is not None and current > due:
            item["pressure_reason"] = "past_due"
            overdue.append(item)
        elif gap > dormant_after:
            item["pressure_reason"] = "dormant"
            dormant.append(item)
        else:
            item["pressure_reason"] = "active"
            active.append(item)
    return {
        "schema": "novelforge_reader_pressure_ledger_v1",
        "current_order": current,
        "overdue": overdue,
        "dormant": dormant,
        "active": active,
        "counts": {"overdue": len(overdue), "dormant": len(dormant), "active": len(active)},
        "authority": False,
        "model_execution": False,
    }


def events(conn: sqlite3.Connection, expectation_id: str) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM expectation_events WHERE expectation_id=? ORDER BY event_id", (expectation_id,)).fetchall()
    return [dict(row) for row in rows]


def self_test(path: Path) -> int:
    if path.exists(): path.unlink()
    conn = connect(path)
    q = open_expectation(conn, expectation_id="EXP-Q1", kind="question", scope="unit", description="Who betrayed them?", opened_order=1, due_by_order=4, salience=0.9, source_ref="canon:CH1")
    s = open_expectation(conn, expectation_id="EXP-S1", kind="setup", scope="arc", description="Locked drawer", opened_order=1, salience=0.7, source_ref="canon:CH1")
    stale_guard = False
    try:
        touch(conn, expectation_id="EXP-Q1", at_order=2, evidence_ref="canon:CH2", expected_version=99)
    except ValueError:
        stale_guard = True
    q2 = touch(conn, expectation_id="EXP-Q1", at_order=2, evidence_ref="canon:CH2", expected_version=q["version"])
    report = pressure_report(conn, current_order=5, dormant_after=2)
    overdue = [x["expectation_id"] for x in report["overdue"]] == ["EXP-Q1"]
    dormant = [x["expectation_id"] for x in report["dormant"]] == ["EXP-S1"]
    paid = resolve(conn, expectation_id="EXP-Q1", status="paid", at_order=5, evidence_ref="canon:CH5", expected_version=q2["version"])
    after = pressure_report(conn, current_order=5, dormant_after=2)
    removed_after_payoff = all(x["expectation_id"] != "EXP-Q1" for bucket in (after["overdue"], after["dormant"], after["active"]) for x in bucket)
    history_ok = [x["event_type"] for x in events(conn, "EXP-Q1")] == ["opened", "touched", "paid"]
    ok = stale_guard and overdue and dormant and paid["status"] == "paid" and removed_after_payoff and history_ok
    print(json.dumps({
        "reader_expectation_contract": "PASS" if ok else "FAIL",
        "before_state_guard": stale_guard,
        "overdue_detection": overdue,
        "dormancy_detection": dormant,
        "payoff_lifecycle": paid["status"] == "paid" and removed_after_payoff,
        "event_history": history_ok,
        "authority": False,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    conn.close()
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge reader expectation ledger")
    p.add_argument("--db", default=".novelforge/reader-expectations.db")
    sub = p.add_subparsers(dest="command", required=True)
    o = sub.add_parser("open"); o.add_argument("--id", required=True); o.add_argument("--kind", choices=sorted(KINDS), required=True); o.add_argument("--scope", required=True); o.add_argument("--description", required=True); o.add_argument("--opened-order", type=int, required=True); o.add_argument("--due-by-order", type=int); o.add_argument("--salience", type=float, default=0.5); o.add_argument("--source-ref", required=True); o.add_argument("--source-fingerprint")
    t = sub.add_parser("touch"); t.add_argument("--id", required=True); t.add_argument("--at-order", type=int, required=True); t.add_argument("--evidence-ref", required=True); t.add_argument("--detail"); t.add_argument("--salience", type=float); t.add_argument("--expected-version", type=int)
    r = sub.add_parser("resolve"); r.add_argument("--id", required=True); r.add_argument("--status", choices=["partial", "paid", "invalidated", "abandoned"], required=True); r.add_argument("--at-order", type=int, required=True); r.add_argument("--evidence-ref", required=True); r.add_argument("--detail"); r.add_argument("--expected-version", type=int)
    g = sub.add_parser("get"); g.add_argument("--id", required=True)
    pr = sub.add_parser("pressure"); pr.add_argument("--current-order", type=int, required=True); pr.add_argument("--dormant-after", type=int, default=3)
    ev = sub.add_parser("events"); ev.add_argument("--id", required=True)
    st = sub.add_parser("self-test"); st.add_argument("--path", default="/tmp/novelforge-reader-expectation-selftest.db")
    args = p.parse_args()
    if args.command == "self-test": return self_test(Path(args.path))
    conn = connect(Path(args.db))
    try:
        if args.command == "open": value = open_expectation(conn, expectation_id=args.id, kind=args.kind, scope=args.scope, description=args.description, opened_order=args.opened_order, due_by_order=args.due_by_order, salience=args.salience, source_ref=args.source_ref, source_fingerprint=args.source_fingerprint)
        elif args.command == "touch": value = touch(conn, expectation_id=args.id, at_order=args.at_order, evidence_ref=args.evidence_ref, detail=args.detail, salience=args.salience, expected_version=args.expected_version)
        elif args.command == "resolve": value = resolve(conn, expectation_id=args.id, status=args.status, at_order=args.at_order, evidence_ref=args.evidence_ref, detail=args.detail, expected_version=args.expected_version)
        elif args.command == "get": value = get_expectation(conn, args.id)
        elif args.command == "pressure": value = pressure_report(conn, current_order=args.current_order, dormant_after=args.dormant_after)
        else: value = events(conn, args.id)
        print(json.dumps(value, ensure_ascii=False, indent=2)); return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
