#!/usr/bin/env python3
"""Durable non-authoritative downstream propagation-debt ledger for Quillframe."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_propagation_debt_v1"
OPEN_SCHEMA = "quillframe_propagation_debt_open_v1"
DISCHARGE_SCHEMA = "quillframe_propagation_debt_discharge_v1"
WAIVER_SCHEMA = "quillframe_propagation_debt_waiver_v1"
SUPERSEDE_SCHEMA = "quillframe_propagation_debt_supersede_v1"
ACTIONS = {"revalidate", "rebuild", "replan", "resimulate", "human_review"}
STATUSES = {"open", "discharged", "superseded", "waived_with_evidence"}
AUTHORITIES = {"locked", "accepted", "settled", "active_plan"}
WAIVER_ACTORS = {"user", "authorized_human", "registered_semantic_result", "deterministic_contract"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty string")
    return value.strip()


def sha(value: Any, field: str) -> str:
    value = nonempty(value, field)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be sha256:<64 hex>") from exc
    return value


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS propagation_debts(
      debt_id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      source_ref TEXT NOT NULL,
      source_authority TEXT NOT NULL,
      source_before_fingerprint TEXT NOT NULL,
      source_after_fingerprint TEXT NOT NULL,
      change_evidence_ref TEXT NOT NULL,
      change_evidence_fingerprint TEXT NOT NULL,
      dependent_ref TEXT NOT NULL,
      dependent_before_fingerprint TEXT NOT NULL,
      dependency_ref TEXT NOT NULL,
      dependency_fingerprint TEXT NOT NULL,
      required_action TEXT NOT NULL,
      reason TEXT NOT NULL,
      status TEXT NOT NULL,
      superseded_by TEXT,
      closure_evidence_ref TEXT,
      closure_evidence_fingerprint TEXT,
      dependent_after_fingerprint TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0),
      UNIQUE(project_id,source_ref,source_before_fingerprint,source_after_fingerprint,
             dependent_ref,dependent_before_fingerprint,dependency_ref,dependency_fingerprint,required_action)
    );
    CREATE TABLE IF NOT EXISTS propagation_debt_events(
      event_fingerprint TEXT PRIMARY KEY,
      debt_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY(debt_id) REFERENCES propagation_debts(debt_id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    return conn


def record_event(conn: sqlite3.Connection, debt_id: str, event_type: str, payload: dict[str, Any]) -> str:
    event_fp = fp({"debt_id": debt_id, "event_type": event_type, "payload": payload})
    try:
        conn.execute(
            "INSERT INTO propagation_debt_events VALUES(?,?,?,?,?)",
            (event_fp, debt_id, event_type, json.dumps(payload, ensure_ascii=False, sort_keys=True), now()),
        )
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT * FROM propagation_debt_events WHERE event_fingerprint=?", (event_fp,)).fetchone()
        if not row or row["debt_id"] != debt_id or row["event_type"] != event_type or json.loads(row["payload_json"]) != payload:
            raise ValueError("event fingerprint collision")
    return event_fp


def normalize_open(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != OPEN_SCHEMA:
        raise ValueError(f"request.schema must be {OPEN_SCHEMA}")
    if set(value) - {"schema", "project_id", "source_change", "dependency"}:
        raise ValueError("open request has unsupported fields")
    project_id = nonempty(value.get("project_id"), "project_id")
    change, dep = value.get("source_change"), value.get("dependency")
    if not isinstance(change, dict) or not isinstance(dep, dict):
        raise ValueError("source_change and dependency objects required")
    change_allowed = {"source_ref", "source_authority", "before_fingerprint", "after_fingerprint", "evidence_ref", "evidence_fingerprint"}
    dep_allowed = {"dependency_ref", "dependency_fingerprint", "source_ref", "dependent_ref", "dependent_fingerprint", "required_action", "reason"}
    if set(change) - change_allowed or set(dep) - dep_allowed:
        raise ValueError("source_change/dependency has unsupported fields")
    source_ref = nonempty(change.get("source_ref"), "source_change.source_ref")
    authority = nonempty(change.get("source_authority"), "source_change.source_authority")
    if authority not in AUTHORITIES:
        raise ValueError(f"source_authority must be one of {sorted(AUTHORITIES)}")
    if dep.get("source_ref") != source_ref:
        raise ValueError("dependency.source_ref must match source_change.source_ref")
    action = nonempty(dep.get("required_action"), "dependency.required_action")
    if action not in ACTIONS:
        raise ValueError(f"required_action must be one of {sorted(ACTIONS)}")
    return {
        "schema": OPEN_SCHEMA,
        "project_id": project_id,
        "source_change": {
            "source_ref": source_ref,
            "source_authority": authority,
            "before_fingerprint": sha(change.get("before_fingerprint"), "source_change.before_fingerprint"),
            "after_fingerprint": sha(change.get("after_fingerprint"), "source_change.after_fingerprint"),
            "evidence_ref": nonempty(change.get("evidence_ref"), "source_change.evidence_ref"),
            "evidence_fingerprint": sha(change.get("evidence_fingerprint"), "source_change.evidence_fingerprint"),
        },
        "dependency": {
            "dependency_ref": nonempty(dep.get("dependency_ref"), "dependency.dependency_ref"),
            "dependency_fingerprint": sha(dep.get("dependency_fingerprint"), "dependency.dependency_fingerprint"),
            "source_ref": source_ref,
            "dependent_ref": nonempty(dep.get("dependent_ref"), "dependency.dependent_ref"),
            "dependent_fingerprint": sha(dep.get("dependent_fingerprint"), "dependency.dependent_fingerprint"),
            "required_action": action,
            "reason": nonempty(dep.get("reason"), "dependency.reason"),
        },
    }


def identity(req: dict[str, Any]) -> dict[str, Any]:
    c, d = req["source_change"], req["dependency"]
    return {
        "project_id": req["project_id"],
        "source_ref": c["source_ref"],
        "source_before_fingerprint": c["before_fingerprint"],
        "source_after_fingerprint": c["after_fingerprint"],
        "dependent_ref": d["dependent_ref"],
        "dependent_before_fingerprint": d["dependent_fingerprint"],
        "dependency_ref": d["dependency_ref"],
        "dependency_fingerprint": d["dependency_fingerprint"],
        "required_action": d["required_action"],
    }


def debt_id(req: dict[str, Any]) -> str:
    return "DEBT-" + fp(identity(req))[7:31].upper()


def view(conn: sqlite3.Connection, debt: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM propagation_debts WHERE debt_id=?", (debt,)).fetchone()
    if row is None:
        raise ValueError(f"unknown debt_id: {debt}")
    keys = [
        "debt_id", "project_id", "source_ref", "source_authority",
        "source_before_fingerprint", "source_after_fingerprint",
        "change_evidence_ref", "change_evidence_fingerprint", "dependent_ref",
        "dependent_before_fingerprint", "dependency_ref", "dependency_fingerprint",
        "required_action", "reason", "status", "superseded_by",
        "closure_evidence_ref", "closure_evidence_fingerprint",
        "dependent_after_fingerprint", "created_at", "updated_at",
    ]
    out = {"schema": SCHEMA, **{key: row[key] for key in keys}}
    out.update(authority=False, canon_authority=False, framework_write_authority=False, auto_action_performed=False, model_execution=False)
    return out


def open_debt(conn: sqlite3.Connection, raw: Any) -> dict[str, Any]:
    req = normalize_open(raw)
    c, d = req["source_change"], req["dependency"]
    if c["before_fingerprint"] == c["after_fingerprint"]:
        return {
            "schema": "quillframe_propagation_debt_open_result_v1",
            "status": "not_created", "reason": "source_fingerprint_unchanged", "debt_id": None,
            "authority": False, "canon_authority": False, "framework_write_authority": False, "model_execution": False,
        }
    did, stamp = debt_id(req), now()
    try:
        conn.execute(
            """INSERT INTO propagation_debts(
            debt_id,project_id,source_ref,source_authority,source_before_fingerprint,source_after_fingerprint,
            change_evidence_ref,change_evidence_fingerprint,dependent_ref,dependent_before_fingerprint,
            dependency_ref,dependency_fingerprint,required_action,reason,status,created_at,updated_at,authority)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
            (did, req["project_id"], c["source_ref"], c["source_authority"], c["before_fingerprint"], c["after_fingerprint"],
             c["evidence_ref"], c["evidence_fingerprint"], d["dependent_ref"], d["dependent_fingerprint"],
             d["dependency_ref"], d["dependency_fingerprint"], d["required_action"], d["reason"], "open", stamp, stamp),
        )
        record_event(conn, did, "opened", req)
        conn.commit()
        created = True
    except sqlite3.IntegrityError:
        conn.rollback()
        existing = view(conn, did)
        if any(existing[k] != v for k, v in identity(req).items()):
            raise ValueError("deterministic debt identity collision")
        evidence = {
            "source_authority": c["source_authority"],
            "change_evidence_ref": c["evidence_ref"],
            "change_evidence_fingerprint": c["evidence_fingerprint"],
            "reason": d["reason"],
        }
        if any(existing[k] != v for k, v in evidence.items()):
            raise ValueError("same debt identity replayed with conflicting evidence")
        created = False
    out = view(conn, did)
    out["open_result"] = "created" if created else "already_exists"
    return out


def list_debts(conn: sqlite3.Connection, status: str | None = None, project_id: str | None = None) -> list[dict[str, Any]]:
    sql, args = "SELECT debt_id FROM propagation_debts WHERE 1=1", []
    if status is not None:
        if status not in STATUSES:
            raise ValueError(f"invalid status: {status}")
        sql += " AND status=?"; args.append(status)
    if project_id is not None:
        sql += " AND project_id=?"; args.append(nonempty(project_id, "project_id"))
    sql += " ORDER BY created_at,debt_id"
    return [view(conn, row["debt_id"]) for row in conn.execute(sql, args)]


def discharge(conn: sqlite3.Connection, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != DISCHARGE_SCHEMA:
        raise ValueError(f"receipt.schema must be {DISCHARGE_SCHEMA}")
    allowed = {"schema", "debt_id", "source_after_fingerprint", "required_action", "result_ref", "result_fingerprint", "dependent_after_fingerprint"}
    if set(raw) - allowed:
        raise ValueError("discharge receipt has unsupported fields")
    did = nonempty(raw.get("debt_id"), "debt_id")
    cur = view(conn, did)
    rec = {
        "schema": DISCHARGE_SCHEMA, "debt_id": did,
        "source_after_fingerprint": sha(raw.get("source_after_fingerprint"), "source_after_fingerprint"),
        "required_action": nonempty(raw.get("required_action"), "required_action"),
        "result_ref": nonempty(raw.get("result_ref"), "result_ref"),
        "result_fingerprint": sha(raw.get("result_fingerprint"), "result_fingerprint"),
        "dependent_after_fingerprint": sha(raw.get("dependent_after_fingerprint"), "dependent_after_fingerprint"),
    }
    if rec["required_action"] not in ACTIONS or rec["required_action"] != cur["required_action"]:
        raise ValueError("discharge required_action does not match debt")
    if rec["source_after_fingerprint"] != cur["source_after_fingerprint"]:
        raise ValueError("discharge source fingerprint does not match debt")
    if cur["status"] == "discharged":
        if (cur["closure_evidence_ref"], cur["closure_evidence_fingerprint"], cur["dependent_after_fingerprint"]) == (
            rec["result_ref"], rec["result_fingerprint"], rec["dependent_after_fingerprint"]
        ):
            return cur
        raise ValueError("debt already discharged with different evidence")
    if cur["status"] != "open":
        raise ValueError(f"debt is not open: {cur['status']}")
    conn.execute(
        """UPDATE propagation_debts SET status='discharged',closure_evidence_ref=?,
        closure_evidence_fingerprint=?,dependent_after_fingerprint=?,updated_at=? WHERE debt_id=?""",
        (rec["result_ref"], rec["result_fingerprint"], rec["dependent_after_fingerprint"], now(), did),
    )
    record_event(conn, did, "discharged", rec); conn.commit()
    return view(conn, did)


def waive(conn: sqlite3.Connection, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != WAIVER_SCHEMA:
        raise ValueError(f"receipt.schema must be {WAIVER_SCHEMA}")
    allowed = {"schema", "debt_id", "source_after_fingerprint", "actor_class", "evidence_ref", "evidence_fingerprint", "reason"}
    if set(raw) - allowed:
        raise ValueError("waiver receipt has unsupported fields")
    did = nonempty(raw.get("debt_id"), "debt_id")
    cur = view(conn, did)
    actor = nonempty(raw.get("actor_class"), "actor_class")
    if actor not in WAIVER_ACTORS:
        raise ValueError(f"actor_class must be one of {sorted(WAIVER_ACTORS)}")
    rec = {
        "schema": WAIVER_SCHEMA, "debt_id": did,
        "source_after_fingerprint": sha(raw.get("source_after_fingerprint"), "source_after_fingerprint"),
        "actor_class": actor, "evidence_ref": nonempty(raw.get("evidence_ref"), "evidence_ref"),
        "evidence_fingerprint": sha(raw.get("evidence_fingerprint"), "evidence_fingerprint"),
        "reason": nonempty(raw.get("reason"), "reason"),
    }
    if rec["source_after_fingerprint"] != cur["source_after_fingerprint"]:
        raise ValueError("waiver source fingerprint does not match debt")
    if cur["status"] == "waived_with_evidence":
        if (cur["closure_evidence_ref"], cur["closure_evidence_fingerprint"]) == (rec["evidence_ref"], rec["evidence_fingerprint"]):
            return cur
        raise ValueError("debt already waived with different evidence")
    if cur["status"] != "open":
        raise ValueError(f"debt is not open: {cur['status']}")
    conn.execute(
        "UPDATE propagation_debts SET status='waived_with_evidence',closure_evidence_ref=?,closure_evidence_fingerprint=?,updated_at=? WHERE debt_id=?",
        (rec["evidence_ref"], rec["evidence_fingerprint"], now(), did),
    )
    record_event(conn, did, "waived_with_evidence", rec); conn.commit()
    return view(conn, did)


def supersede(conn: sqlite3.Connection, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != SUPERSEDE_SCHEMA:
        raise ValueError(f"receipt.schema must be {SUPERSEDE_SCHEMA}")
    allowed = {"schema", "debt_id", "new_debt_id", "evidence_ref", "evidence_fingerprint"}
    if set(raw) - allowed:
        raise ValueError("supersede receipt has unsupported fields")
    old_id, new_id = nonempty(raw.get("debt_id"), "debt_id"), nonempty(raw.get("new_debt_id"), "new_debt_id")
    old, new = view(conn, old_id), view(conn, new_id)
    evidence_ref, evidence_fp = nonempty(raw.get("evidence_ref"), "evidence_ref"), sha(raw.get("evidence_fingerprint"), "evidence_fingerprint")
    if old_id == new_id:
        raise ValueError("debt cannot supersede itself")
    if any(old[k] != new[k] for k in ("project_id", "source_ref", "dependent_ref", "dependency_ref")):
        raise ValueError("superseding debt must describe same explicit dependency")
    if new["source_before_fingerprint"] != old["source_after_fingerprint"]:
        raise ValueError("superseding debt source lineage is not contiguous")
    if old["status"] == "superseded":
        if (old["superseded_by"], old["closure_evidence_ref"], old["closure_evidence_fingerprint"]) == (new_id, evidence_ref, evidence_fp):
            return old
        raise ValueError("debt already superseded differently")
    if old["status"] != "open" or new["status"] != "open":
        raise ValueError("old and new debts must be open")
    rec = {"schema": SUPERSEDE_SCHEMA, "debt_id": old_id, "new_debt_id": new_id, "evidence_ref": evidence_ref, "evidence_fingerprint": evidence_fp}
    conn.execute(
        "UPDATE propagation_debts SET status='superseded',superseded_by=?,closure_evidence_ref=?,closure_evidence_fingerprint=?,updated_at=? WHERE debt_id=?",
        (new_id, evidence_ref, evidence_fp, now(), old_id),
    )
    record_event(conn, old_id, "superseded", rec); conn.commit()
    return view(conn, old_id)


def summary(conn: sqlite3.Connection, project_id: str | None = None) -> dict[str, Any]:
    items = list_debts(conn, project_id=project_id)
    counts = {status: sum(item["status"] == status for item in items) for status in sorted(STATUSES)}
    return {
        "schema": "quillframe_propagation_debt_summary_v1", "project_id": project_id,
        "counts": counts, "open_debt_ids": [x["debt_id"] for x in items if x["status"] == "open"],
        "authority": False, "canon_authority": False, "framework_write_authority": False,
        "auto_action_performed": False, "model_execution": False,
    }


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe propagation-debt ledger")
    parser.add_argument("--db", default=".quillframe/propagation-debt.db")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("open"); p.add_argument("--request", required=True)
    p = sub.add_parser("status"); p.add_argument("--debt-id", required=True)
    p = sub.add_parser("list"); p.add_argument("--status", choices=sorted(STATUSES)); p.add_argument("--project-id")
    p = sub.add_parser("discharge"); p.add_argument("--receipt", required=True)
    p = sub.add_parser("waive"); p.add_argument("--receipt", required=True)
    p = sub.add_parser("supersede"); p.add_argument("--receipt", required=True)
    p = sub.add_parser("summary"); p.add_argument("--project-id")
    p = sub.add_parser("self-test"); p.add_argument("--path")
    args = parser.parse_args()
    if args.command == "self-test":
        from propagation_debt_selftest import run_self_test
        path = Path(args.path) if args.path else Path(tempfile.gettempdir()) / "quillframe-propagation-debt-selftest.db"
        return run_self_test(path)
    conn = connect(Path(args.db))
    try:
        if args.command == "open": out = open_debt(conn, load(Path(args.request)))
        elif args.command == "status": out = view(conn, args.debt_id)
        elif args.command == "list": out = {"schema": "quillframe_propagation_debt_list_v1", "items": list_debts(conn, args.status, args.project_id)}
        elif args.command == "discharge": out = discharge(conn, load(Path(args.receipt)))
        elif args.command == "waive": out = waive(conn, load(Path(args.receipt)))
        elif args.command == "supersede": out = supersede(conn, load(Path(args.receipt)))
        else: out = summary(conn, args.project_id)
        dump(out); return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
