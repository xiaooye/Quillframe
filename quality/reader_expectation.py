#!/usr/bin/env python3
"""Durable reader-expectation lifecycle ledger for Quillframe.

Tracks explicit reader-facing obligations and their evidence-backed lifecycle.
It does not infer reader importance, assign salience scores, or perform model
execution. Semantic prioritization belongs to model contracts.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_reader_expectation_v2"
KINDS = {"question", "promise", "setup", "relationship", "goal", "mystery"}
STATUSES = {"open", "partial", "paid", "invalidated", "abandoned"}
FINAL = {"paid", "invalidated", "abandoned"}


def now() -> str: return datetime.now(timezone.utc).isoformat()

def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
    conn.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS expectations(
      expectation_id TEXT PRIMARY KEY,
      kind TEXT NOT NULL,
      scope TEXT NOT NULL,
      description TEXT NOT NULL,
      opened_order INTEGER NOT NULL,
      due_by_order INTEGER,
      last_touched_order INTEGER NOT NULL,
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
    """); conn.commit(); return conn

def _row(row: sqlite3.Row) -> dict[str, Any]:
    return {"schema":SCHEMA,"expectation_id":row["expectation_id"],"kind":row["kind"],"scope":row["scope"],"description":row["description"],"opened_order":row["opened_order"],"due_by_order":row["due_by_order"],"last_touched_order":row["last_touched_order"],"status":row["status"],"source_ref":row["source_ref"],"source_fingerprint":row["source_fingerprint"],"version":row["version"],"created_at":row["created_at"],"updated_at":row["updated_at"],"authority":False}

def _order(value: Any, name: str) -> int:
    if isinstance(value,bool) or not isinstance(value,int) or value<0: raise ValueError(f"{name} must be a non-negative integer")
    return value

def open_expectation(conn: sqlite3.Connection, *, expectation_id: str, kind: str, scope: str, description: str, opened_order: int, source_ref: str, due_by_order: int | None=None, source_fingerprint: str | None=None, commit: bool=True) -> dict[str, Any]:
    if not expectation_id or not scope or not description or not source_ref: raise ValueError("expectation_id/scope/description/source_ref required")
    if kind not in KINDS: raise ValueError("invalid kind")
    opened=_order(opened_order,"opened_order"); due=None if due_by_order is None else _order(due_by_order,"due_by_order")
    if due is not None and due<opened: raise ValueError("due_by_order precedes opened_order")
    stamp=now()
    conn.execute("INSERT INTO expectations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(expectation_id,kind,scope,description,opened,due,opened,"open",source_ref,source_fingerprint,1,stamp,stamp))
    conn.execute("INSERT INTO expectation_events(expectation_id,event_type,at_order,detail,evidence_ref,created_at) VALUES(?,?,?,?,?,?)",(expectation_id,"opened",opened,description,source_ref,stamp))
    if commit: conn.commit()
    return get_expectation(conn,expectation_id)

def get_expectation(conn: sqlite3.Connection, expectation_id: str) -> dict[str, Any]:
    row=conn.execute("SELECT * FROM expectations WHERE expectation_id=?",(expectation_id,)).fetchone()
    if row is None: raise ValueError(f"unknown expectation_id {expectation_id}")
    return _row(row)

def _guard(row: sqlite3.Row, expected_version: int | None) -> None:
    if expected_version is not None and row["version"]!=expected_version: raise ValueError(f"before-state mismatch: expected version {expected_version}, actual {row['version']}")

def touch(conn: sqlite3.Connection, *, expectation_id: str, at_order: int, evidence_ref: str, detail: str | None=None, expected_version: int | None=None, commit: bool=True) -> dict[str, Any]:
    at=_order(at_order,"at_order"); row=conn.execute("SELECT * FROM expectations WHERE expectation_id=?",(expectation_id,)).fetchone()
    if row is None: raise ValueError(f"unknown expectation_id {expectation_id}")
    _guard(row,expected_version)
    if row["status"] in FINAL: raise ValueError("cannot touch final expectation")
    if at<row["opened_order"] or at<row["last_touched_order"]: raise ValueError("touch order cannot move backward")
    stamp=now(); conn.execute("UPDATE expectations SET last_touched_order=?,version=version+1,updated_at=? WHERE expectation_id=?",(at,stamp,expectation_id))
    conn.execute("INSERT INTO expectation_events(expectation_id,event_type,at_order,detail,evidence_ref,created_at) VALUES(?,?,?,?,?,?)",(expectation_id,"touched",at,detail,evidence_ref,stamp))
    if commit: conn.commit()
    return get_expectation(conn,expectation_id)

def resolve(conn: sqlite3.Connection, *, expectation_id: str, status: str, at_order: int, evidence_ref: str, detail: str | None=None, expected_version: int | None=None, commit: bool=True) -> dict[str, Any]:
    if status not in {"partial","paid","invalidated","abandoned"}: raise ValueError("invalid resolution status")
    at=_order(at_order,"at_order"); row=conn.execute("SELECT * FROM expectations WHERE expectation_id=?",(expectation_id,)).fetchone()
    if row is None: raise ValueError(f"unknown expectation_id {expectation_id}")
    _guard(row,expected_version)
    if row["status"] in FINAL: raise ValueError("expectation already final")
    if at<row["last_touched_order"]: raise ValueError("resolution order cannot move backward")
    stamp=now(); conn.execute("UPDATE expectations SET status=?,last_touched_order=?,version=version+1,updated_at=? WHERE expectation_id=?",(status,at,stamp,expectation_id))
    conn.execute("INSERT INTO expectation_events(expectation_id,event_type,at_order,detail,evidence_ref,created_at) VALUES(?,?,?,?,?,?)",(expectation_id,status,at,detail,evidence_ref,stamp))
    if commit: conn.commit()
    return get_expectation(conn,expectation_id)

def pressure_report(conn: sqlite3.Connection, *, current_order: int, dormant_after: int=3) -> dict[str, Any]:
    current=_order(current_order,"current_order"); dormant_after=_order(dormant_after,"dormant_after")
    rows=conn.execute("SELECT * FROM expectations WHERE status IN ('open','partial') AND opened_order<=? AND last_touched_order<=? ORDER BY opened_order,expectation_id", (current, current)).fetchall()
    overdue=[]; dormant=[]; active=[]
    for row in rows:
        item=_row(row); gap=current-row["last_touched_order"]; item["silence_gap"]=gap; due=row["due_by_order"]
        if due is not None and current>due: item["pressure_reason"]="past_due"; overdue.append(item)
        elif gap>dormant_after: item["pressure_reason"]="dormant"; dormant.append(item)
        else: item["pressure_reason"]="active"; active.append(item)
    return {"schema":"quillframe_reader_pressure_ledger_v2","current_order":current,"overdue":overdue,"dormant":dormant,"active":active,"counts":{"overdue":len(overdue),"dormant":len(dormant),"active":len(active)},"semantic_priority_owner":"model","semantic_salience_stored":False,"authority":False,"model_execution":False}

def events(conn: sqlite3.Connection, expectation_id: str) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute("SELECT * FROM expectation_events WHERE expectation_id=? ORDER BY event_id",(expectation_id,)).fetchall()]


class ReaderExpectationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require_transaction(conn: sqlite3.Connection) -> None:
    if not conn.in_transaction:
        raise ReaderExpectationError("transaction_required", "reader memory writes must join a Core-owned transaction")


def _fingerprint(value: Any) -> str:
    from persistence.quillframe_sqlite import canonical_json, fingerprint_text
    return fingerprint_text(canonical_json(value))


def _canonical(value: Any) -> str:
    from persistence.quillframe_sqlite import canonical_json
    return canonical_json(value)


def validate_observation_binding(binding: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify exact model evidence, then normalize proposals without judging them."""
    from harness.semantic_workers.registered_contract_binding import validate_registered_job
    from harness.semantic_workers.semantic_worker_router import validate_result
    if binding.get("contract_id") != "reader.expectations" or binding.get("authority") is not False:
        raise ReaderExpectationError("reader_observation_invalid", "registered reader.expectations binding is required")
    job = binding.get("job")
    result = binding.get("result")
    if not isinstance(job, dict) or not isinstance(result, dict) or binding.get("binding_fingerprint") != _fingerprint({"job": job, "result": result}):
        raise ReaderExpectationError("reader_observation_invalid", "reader observation binding fingerprint does not match")
    errors = validate_registered_job(job) + validate_result(job, result)
    if errors or job.get("input", {}).get("model_contract_id") != "reader.expectations" or result.get("status") != "completed":
        raise ReaderExpectationError("reader_observation_invalid", "; ".join(errors) or "reader observation is not completed")
    payload = job["input"]["payload"]
    from persistence.quillframe_sqlite import fingerprint_text
    if fingerprint_text(payload["candidate_text"]) != payload["candidate_fingerprint"]:
        raise ReaderExpectationError("reader_source_mismatch", "reader candidate text does not bind its fingerprint")
    existing = {row["expectation_id"]: row for row in payload["existing_expectations"]}
    updates = []
    seen = set()
    for index, raw in enumerate(result["judgment"]["expectation_updates"]):
        update = dict(raw)
        if update["evidence_ref"] != "candidate:" + payload["candidate_fingerprint"] \
                or not update["evidence_quote"].strip() or update["evidence_quote"] not in payload["candidate_text"]:
            raise ReaderExpectationError("reader_evidence_mismatch", "expectation updates require an exact quote from the bound candidate")
        if update["operation"] == "open":
            if update["expected_version"] != 0:
                raise ReaderExpectationError("reader_version_mismatch", "new expectations require expected_version 0")
            update["expectation_id"] = "REXP-" + binding["binding_fingerprint"][7:31] + "-" + str(index + 1)
            due = update.get("due_by_order")
            if due is not None and due < payload["current_reading_order"]:
                raise ReaderExpectationError("reader_order_mismatch", "a new expected payoff cannot be due before its source")
        else:
            prior = existing.get(update["expectation_id"])
            if not prior or prior["version"] != update["expected_version"] or prior["status"] in FINAL:
                raise ReaderExpectationError("reader_version_mismatch", "update does not bind a live supplied expectation version")
        if update["expectation_id"] in seen:
            raise ReaderExpectationError("reader_observation_invalid", "one observation cannot update an expectation twice")
        seen.add(update["expectation_id"])
        updates.append(update)
    return payload, updates


def record_observation(conn: sqlite3.Connection, *, run_id: str, candidate_id: str, binding: dict[str, Any]) -> str:
    """Called only by the trusted production release path; never commits."""
    _require_transaction(conn)
    payload, updates = validate_observation_binding(binding)
    candidate = conn.execute(
        "SELECT c.*,d.story_node_id FROM candidates c JOIN documents d ON d.document_id=c.document_id WHERE c.candidate_id=?",
        (candidate_id,),
    ).fetchone()
    if not candidate or candidate["run_id"] != run_id or candidate["document_id"] != payload["document_id"] \
            or candidate["story_node_id"] != payload["chapter_id"] or candidate["content_fingerprint"] != payload["candidate_fingerprint"]:
        raise ReaderExpectationError("reader_source_mismatch", "observation does not match its released production candidate")
    observation_id = "ROBS-" + binding["binding_fingerprint"][7:39]
    prior = conn.execute("SELECT observation_id,binding_fingerprint FROM reader_expectation_observations WHERE run_id=? AND candidate_fingerprint=?",
                         (run_id, payload["candidate_fingerprint"])).fetchone()
    if prior:
        if prior["binding_fingerprint"] != binding["binding_fingerprint"]:
            raise ReaderExpectationError("reader_observation_conflict", "candidate already has a different immutable reader observation")
        return prior["observation_id"]
    stamp = now()
    conn.execute(
        "INSERT INTO reader_expectation_observations(observation_id,run_id,chapter_id,document_id,candidate_id,candidate_fingerprint,reading_order,binding_fingerprint,binding_json,updates_json,state,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,'proposed',?,?)",
        (observation_id, run_id, payload["chapter_id"], payload["document_id"], candidate_id, payload["candidate_fingerprint"],
         payload["current_reading_order"], binding["binding_fingerprint"], _canonical(binding), _canonical(updates), stamp, stamp),
    )
    sources = {payload["chapter_id"]: payload["candidate_fingerprint"]}
    for row in payload["reader_visible_context"]:
        chapter = row.get("chapter_id")
        source_fp = row.get("content_fingerprint")
        if not isinstance(chapter, str) or not isinstance(source_fp, str) or chapter in sources:
            raise ReaderExpectationError("reader_source_mismatch", "reader history must contain distinct Core-bound chapter sources")
        sources[chapter] = source_fp
    conn.executemany("INSERT INTO reader_observation_sources(observation_id,source_chapter_id,source_fingerprint) VALUES(?,?,?)",
                     [(observation_id, chapter, source_fp) for chapter, source_fp in sources.items()])
    conn.executemany("INSERT INTO reader_observation_expectation_dependencies(observation_id,expectation_id,expected_version) VALUES(?,?,?)",
                     [(observation_id, row["expectation_id"], row["version"]) for row in payload["existing_expectations"]])
    return observation_id


def _candidate_released(conn: sqlite3.Connection, row: sqlite3.Row) -> bool:
    from core_operations import CoreOperations, OperationError
    from persistence.quillframe_sqlite import fingerprint_text
    candidate = conn.execute(
        "SELECT c.*,r.content,r.content_fingerprint AS revision_fingerprint,r.document_id AS revision_document_id "
        "FROM candidates c LEFT JOIN document_revisions r ON r.revision_id=c.revision_id WHERE c.candidate_id=?",
        (row["candidate_id"],),
    ).fetchone()
    if not candidate or candidate["status"] not in {"review_draft", "accepted"} \
            or candidate["run_id"] != row["run_id"] or candidate["document_id"] != row["document_id"] \
            or candidate["revision_document_id"] != row["document_id"] \
            or candidate["content_fingerprint"] != row["candidate_fingerprint"] \
            or candidate["revision_fingerprint"] != row["candidate_fingerprint"] \
            or not isinstance(candidate["content"], str) or fingerprint_text(candidate["content"]) != row["candidate_fingerprint"]:
        return False
    try:
        value = CoreOperations._validated_production_release(conn, dict(candidate))
    except (OperationError, ValueError, TypeError):
        return False
    return value.get("authority") is False and conn.execute(
        "SELECT 1 FROM review_evidence WHERE candidate_id=? AND candidate_fingerprint=? AND independent=1 AND stale=0",
        (row["candidate_id"], row["candidate_fingerprint"]),
    ).fetchone() is not None


def inspect_project(conn: sqlite3.Connection, *, current_order: int | None = None) -> dict[str, Any]:
    if current_order is not None:
        _order(current_order, "current_order")
    items = [_row(row) for row in conn.execute("SELECT * FROM expectations ORDER BY opened_order,expectation_id")
             if current_order is None or row["last_touched_order"] <= current_order]
    observations = []
    for row in conn.execute("SELECT * FROM reader_expectation_observations ORDER BY reading_order,created_at,observation_id"):
        if (current_order is not None and row["reading_order"] > current_order) or not _candidate_released(conn, row):
            continue
        observations.append({**{key: row[key] for key in ("observation_id", "run_id", "chapter_id", "document_id", "candidate_id",
                                                        "candidate_fingerprint", "reading_order", "state")},
                             "updates": json.loads(row["updates_json"]), "source_type": "model_proxy", "authority": False})
    return {"schema": "quillframe_reader_expectations_inspection_v1", "items": items, "observations": observations,
            "measured_retention": False, "authority": False}


def apply_observation(conn: sqlite3.Connection, *, observation_id: str, acceptance_id: str, user_authorized: bool,
                      authorized_by: str, idempotency_key: str) -> dict[str, Any]:
    _require_transaction(conn)
    if user_authorized is not True or not isinstance(authorized_by, str) or not authorized_by.strip() or not isinstance(idempotency_key, str) or not idempotency_key:
        raise ReaderExpectationError("authorization_required", "applying reader memory requires an explicit author action and idempotency key")
    request_fp = _fingerprint({"observation_id": observation_id, "acceptance_id": acceptance_id, "authorized_by": authorized_by})
    prior = conn.execute("SELECT receipt_kind,payload_json FROM receipts WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    if prior:
        value = json.loads(prior["payload_json"])
        if prior["receipt_kind"] != "reader_expectations_apply" or value.get("request_fingerprint") != request_fp:
            raise ReaderExpectationError("idempotency_conflict", "reader memory idempotency key belongs to another request")
        return value
    row = conn.execute("SELECT * FROM reader_expectation_observations WHERE observation_id=?", (observation_id,)).fetchone()
    if not row or row["state"] != "proposed" or not _candidate_released(conn, row):
        raise ReaderExpectationError("reader_observation_not_applicable", "reader observation is missing, not current, or not released")
    binding = json.loads(row["binding_json"])
    _, updates = validate_observation_binding(binding)
    if row["binding_fingerprint"] != binding["binding_fingerprint"] or _canonical(updates) != row["updates_json"]:
        raise ReaderExpectationError("reader_observation_invalid", "stored reader observation was modified")
    acceptance = conn.execute("SELECT candidate_id,candidate_fingerprint FROM acceptance_evidence WHERE acceptance_id=?", (acceptance_id,)).fetchone()
    if not acceptance or acceptance["candidate_id"] != row["candidate_id"] or acceptance["candidate_fingerprint"] != row["candidate_fingerprint"]:
        raise ReaderExpectationError("reader_source_not_accepted", "reader observation must bind this explicit acceptance")
    for source in conn.execute("SELECT * FROM reader_observation_sources WHERE observation_id=?", (observation_id,)):
        from quillframe.novel import current_head
        head = conn.execute("SELECT value_json,content_fingerprint FROM canon_state WHERE state_key=?", ("chapter:" + source["source_chapter_id"],)).fetchone()
        value = json.loads(head["value_json"]) if head else {}
        if not head or head["content_fingerprint"] != _fingerprint(value) or value.get("content_fingerprint") != source["source_fingerprint"]:
            raise ReaderExpectationError("reader_source_stale", "reader observation source is not the current settled chapter head")
        live_head, _ = current_head(conn, source["source_chapter_id"], value.get("document_id"))
        if live_head is None or live_head["head_fingerprint"] != head["content_fingerprint"]:
            raise ReaderExpectationError("reader_source_stale", "reader observation source has been superseded or invalidated")
        if source["source_chapter_id"] == row["chapter_id"] and value.get("acceptance_id") != acceptance_id:
            raise ReaderExpectationError("reader_source_not_settled", "author acceptance has not been settled for the source chapter")
    for dependency in conn.execute("SELECT * FROM reader_observation_expectation_dependencies WHERE observation_id=?", (observation_id,)):
        current = get_expectation(conn, dependency["expectation_id"])
        if current["version"] != dependency["expected_version"] or current["status"] in FINAL:
            raise ReaderExpectationError("reader_version_mismatch", "expectation state changed since the observation")
    results = []
    for update in updates:
        expectation_id = update["expectation_id"]
        before = None if update["operation"] == "open" else get_expectation(conn, expectation_id)
        if update["operation"] == "open":
            after = open_expectation(conn, expectation_id=expectation_id, kind=update["kind"], scope="project", description=update["description"],
                                     opened_order=row["reading_order"], due_by_order=update.get("due_by_order"),
                                     source_ref="chapter:" + row["chapter_id"], source_fingerprint=row["candidate_fingerprint"], commit=False)
        else:
            args = {"expectation_id": expectation_id, "at_order": row["reading_order"], "evidence_ref": "chapter:" + row["chapter_id"],
                    "detail": update["detail"], "expected_version": update["expected_version"], "commit": False}
            after = touch(conn, **args) if update["operation"] == "touch" else resolve(conn, status=update["operation"], **args)
        conn.execute("INSERT INTO reader_expectation_effects(observation_id,expectation_id,before_json,after_json) VALUES(?,?,?,?)",
                     (observation_id, expectation_id, _canonical(before) if before else None, _canonical(after)))
        results.append(after)
    stamp = now()
    conn.execute("UPDATE reader_expectation_observations SET state='applied',updated_at=? WHERE observation_id=?", (stamp, observation_id))
    result = {"schema": "quillframe_reader_expectations_apply_result_v1", "observation_id": observation_id, "state": "applied",
              "items": results, "request_fingerprint": request_fp, "source_type": "model_proxy", "canon_mutated": False, "authority": False}
    conn.execute("INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                 ("RREC-" + request_fp[7:39], row["run_id"], "reader_expectations_apply", idempotency_key, _canonical(result), stamp))
    return result


def invalidate_source(conn: sqlite3.Connection, *, chapter_id: str, source_fingerprint: str | None = None,
                      reason: str = "source_revision_changed") -> dict[str, Any]:
    _require_transaction(conn)
    affected = {row["observation_id"] for row in conn.execute(
        "SELECT observation_id FROM reader_observation_sources WHERE source_chapter_id=? AND (? IS NULL OR source_fingerprint=?)",
        (chapter_id, source_fingerprint, source_fingerprint))}
    pending = set(affected)
    invalidated_expectations = set()
    stamp = now()
    while pending:
        observation_id = pending.pop()
        conn.execute("UPDATE reader_expectation_observations SET state='invalidated',updated_at=? WHERE observation_id=?", (stamp, observation_id))
        for effect in conn.execute("SELECT expectation_id FROM reader_expectation_effects WHERE observation_id=?", (observation_id,)):
            expectation_id = effect["expectation_id"]
            if expectation_id in invalidated_expectations:
                continue
            invalidated_expectations.add(expectation_id)
            prior = get_expectation(conn, expectation_id)
            if prior["status"] != "invalidated":
                conn.execute("UPDATE expectations SET status='invalidated',version=version+1,updated_at=? WHERE expectation_id=?", (stamp, expectation_id))
                conn.execute("INSERT INTO expectation_events(expectation_id,event_type,at_order,detail,evidence_ref,created_at) VALUES(?,?,?,?,?,?)",
                             (expectation_id, "source_invalidated", prior["last_touched_order"], reason, "chapter:" + chapter_id, stamp))
            downstream = {row["observation_id"] for row in conn.execute("SELECT observation_id FROM reader_observation_expectation_dependencies WHERE expectation_id=?", (expectation_id,))}
            pending.update(downstream - affected)
            affected.update(downstream)
    return {"observation_ids": sorted(affected), "expectation_ids": sorted(invalidated_expectations), "authority": False}

def self_test(path: Path) -> int:
    if path.exists(): path.unlink()
    conn=connect(path)
    q=open_expectation(conn,expectation_id="EXP-Q1",kind="question",scope="unit",description="Who betrayed them?",opened_order=1,due_by_order=4,source_ref="canon:CH1")
    open_expectation(conn,expectation_id="EXP-S1",kind="setup",scope="arc",description="Locked drawer",opened_order=1,source_ref="canon:CH1")
    stale=False
    try: touch(conn,expectation_id="EXP-Q1",at_order=2,evidence_ref="canon:CH2",expected_version=99)
    except ValueError: stale=True
    q2=touch(conn,expectation_id="EXP-Q1",at_order=2,evidence_ref="canon:CH2",expected_version=q["version"])
    report=pressure_report(conn,current_order=5,dormant_after=2)
    overdue=[x["expectation_id"] for x in report["overdue"]]==["EXP-Q1"]
    dormant=[x["expectation_id"] for x in report["dormant"]]==["EXP-S1"]
    paid=resolve(conn,expectation_id="EXP-Q1",status="paid",at_order=5,evidence_ref="canon:CH5",expected_version=q2["version"])
    after=pressure_report(conn,current_order=5,dormant_after=2)
    removed=all(x["expectation_id"]!="EXP-Q1" for bucket in (after["overdue"],after["dormant"],after["active"]) for x in bucket)
    history=[x["event_type"] for x in events(conn,"EXP-Q1")]==["opened","touched","paid"]
    no_salience=all("salience" not in x for bucket in (report["overdue"],report["dormant"],report["active"]) for x in bucket)
    ok=stale and overdue and dormant and paid["status"]=="paid" and removed and history and no_salience
    print(json.dumps({"reader_expectation_contract":"PASS" if ok else "FAIL","before_state_guard":stale,"overdue_detection":overdue,"dormancy_detection":dormant,"payoff_lifecycle":paid["status"]=="paid" and removed,"event_history":history,"semantic_salience_stored":False,"semantic_priority_owner":"model","authority":False,"model_execution":False},ensure_ascii=False,indent=2)); conn.close(); return 0 if ok else 1

def main() -> int:
    p=argparse.ArgumentParser(description="Quillframe reader expectation lifecycle ledger"); p.add_argument("--db",default=".quillframe/reader-expectations.db"); sub=p.add_subparsers(dest="command",required=True)
    o=sub.add_parser("open"); o.add_argument("--id",required=True); o.add_argument("--kind",choices=sorted(KINDS),required=True); o.add_argument("--scope",required=True); o.add_argument("--description",required=True); o.add_argument("--opened-order",type=int,required=True); o.add_argument("--due-by-order",type=int); o.add_argument("--source-ref",required=True); o.add_argument("--source-fingerprint")
    t=sub.add_parser("touch"); t.add_argument("--id",required=True); t.add_argument("--at-order",type=int,required=True); t.add_argument("--evidence-ref",required=True); t.add_argument("--detail"); t.add_argument("--expected-version",type=int)
    r=sub.add_parser("resolve"); r.add_argument("--id",required=True); r.add_argument("--status",choices=["partial","paid","invalidated","abandoned"],required=True); r.add_argument("--at-order",type=int,required=True); r.add_argument("--evidence-ref",required=True); r.add_argument("--detail"); r.add_argument("--expected-version",type=int)
    g=sub.add_parser("get"); g.add_argument("--id",required=True)
    pr=sub.add_parser("pressure"); pr.add_argument("--current-order",type=int,required=True); pr.add_argument("--dormant-after",type=int,default=3)
    ev=sub.add_parser("events"); ev.add_argument("--id",required=True)
    st=sub.add_parser("self-test"); st.add_argument("--path",default="/tmp/quillframe-reader-expectation-selftest.db")
    args=p.parse_args()
    if args.command=="self-test": return self_test(Path(args.path))
    conn=connect(Path(args.db))
    try:
        if args.command=="open": value=open_expectation(conn,expectation_id=args.id,kind=args.kind,scope=args.scope,description=args.description,opened_order=args.opened_order,due_by_order=args.due_by_order,source_ref=args.source_ref,source_fingerprint=args.source_fingerprint)
        elif args.command=="touch": value=touch(conn,expectation_id=args.id,at_order=args.at_order,evidence_ref=args.evidence_ref,detail=args.detail,expected_version=args.expected_version)
        elif args.command=="resolve": value=resolve(conn,expectation_id=args.id,status=args.status,at_order=args.at_order,evidence_ref=args.evidence_ref,detail=args.detail,expected_version=args.expected_version)
        elif args.command=="get": value=get_expectation(conn,args.id)
        elif args.command=="pressure": value=pressure_report(conn,current_order=args.current_order,dormant_after=args.dormant_after)
        else: value=events(conn,args.id)
        print(json.dumps(value,ensure_ascii=False,indent=2)); return 0
    finally: conn.close()

if __name__=="__main__": raise SystemExit(main())
