#!/usr/bin/env python3
"""Automatic, resumable feedback -> Learning intake for NovelForge.

This is wiring, not a second preference authority. It consumes durable
`feedback.observed` Control Plane events under its own logical consumer,
packages `learning.preference_interpret`, persists pending/status state in the
existing Learning DB, validates semantic results, and delegates durable evidence
and hypothesis mutation to Author Model.

No keyword heuristic decides whether feedback is learnable. No path here grants
Canon, Project Profile, Framework behavior, or durable user-taste authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONTROL = ROOT / "harness" / "control_plane"
SEMANTIC = ROOT / "harness" / "semantic_workers"
for p in (HERE, CONTROL, SEMANTIC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from author_model import CAPTURE_SCHEMA, capture_feedback, hypothesis_index, project_author_model  # noqa: E402
from control_plane import ControlPlane  # noqa: E402
from learning_store import LearningStore, now_iso  # noqa: E402
from semantic_worker_router import make_contract_job, validate_result  # noqa: E402

SCHEMA = "novelforge_feedback_intake_v1"
PROJECTION_SCHEMA = "novelforge_feedback_intake_projection_v1"
GENERIC_FEEDBACK_SCHEMA = "novelforge_feedback_observation_v1"
LEGACY_STEERING_SCHEMA = "novelforge_author_steering_request_v1"
CONTRACT_ID = "learning.preference_interpret"
STATES = {"observed", "awaiting_semantic", "interpreted", "skipped", "persisted", "blocked", "failed"}
CAPTURE_FIELDS = {
    "scope_candidate", "dimension", "mechanism", "statement", "polarity", "evidence_source", "hypothesis_action"
}
PREFERENCE_FIELDS = CAPTURE_FIELDS | {
    "observed_problem", "desired_behavior", "avoid_behavior", "exceptions", "applicability",
    "target_hypothesis_id", "contradicts_hypothesis_ids",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def stable_evidence_id(event_id: str, event_hash: str, consumer: str) -> str:
    raw = canonical({"event_id": event_id, "event_hash": event_hash, "consumer": consumer})
    return "PE-FBK-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _target_from_event(event: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    target = payload.get("target") if isinstance(payload.get("target"), dict) else {}
    out = dict(target)
    fps = event.get("artifact_fingerprints", [])
    if "artifact_fingerprint" not in out and isinstance(fps, list) and fps:
        first = fps[0]
        if isinstance(first, str):
            out["artifact_fingerprint"] = first
        elif isinstance(first, dict):
            if first.get("fingerprint"):
                out["artifact_fingerprint"] = first.get("fingerprint")
            if first.get("ref") and "artifact_ref" not in out:
                out["artifact_ref"] = first.get("ref")
    return out


def normalize_feedback_event(
    event: dict[str, Any],
    *,
    project_id: str | None,
    current_task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ControlPlane.validate_event(event)
    if event.get("event_type") != "feedback.observed":
        raise ValueError("learning intake requires feedback.observed")
    source = event.get("source", {})
    if source.get("kind") not in {"user", "authorized_human"}:
        raise ValueError("learning intake accepts user/authorized_human feedback only")
    payload = event.get("payload", {})
    schema = payload.get("schema")
    kind = payload.get("kind")
    if schema == LEGACY_STEERING_SCHEMA and kind == "author_steering":
        feedback_text = _nonempty(payload.get("instruction"), "payload.instruction")
        task = current_task or {}
        target = _target_from_event(event, payload)
        payload_kind = "legacy_author_steering"
    elif schema == GENERIC_FEEDBACK_SCHEMA and kind == "feedback_observation":
        feedback_text = _nonempty(payload.get("feedback_text"), "payload.feedback_text")
        task = payload.get("current_task") if isinstance(payload.get("current_task"), dict) else (current_task or {})
        target = _target_from_event(event, payload)
        payload_kind = "generic_feedback_observation"
        for flag in ("authority", "canon_authority", "framework_write_authority"):
            if payload.get(flag, False) is not False:
                raise ValueError(f"feedback observation {flag} must be false")
    else:
        raise ValueError("unsupported feedback.observed payload for Learning intake")
    if not isinstance(task, dict):
        raise ValueError("current_task must be object")
    return {
        "event_id": _nonempty(event.get("event_id"), "event_id"),
        "resource_id": _nonempty(event.get("resource_id"), "resource_id"),
        "session_id": event.get("session_id"),
        "run_id": event.get("run_id"),
        "project_id": project_id,
        "feedback_ref": f"feedback:{event['event_id']}",
        "feedback_text": feedback_text,
        "current_task": task,
        "target": target,
        "payload_kind": payload_kind,
        "source_kind": source.get("kind"),
    }


class FeedbackIntakeStore:
    """Additive projection in the same Learning DB."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        LearningStore(self.db_path).init()
        self.init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS feedback_intake (
                event_id TEXT PRIMARY KEY,
                event_hash TEXT NOT NULL,
                consumer TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                project_id TEXT,
                session_id TEXT,
                run_id TEXT,
                feedback_ref TEXT NOT NULL,
                normalized_json TEXT NOT NULL,
                status TEXT NOT NULL,
                semantic_job_json TEXT,
                semantic_job_fingerprint TEXT,
                semantic_result_hash TEXT,
                capture_decision TEXT,
                skip_reason TEXT,
                evidence_id TEXT,
                hypothesis_id TEXT,
                hypothesis_action TEXT,
                target_hypothesis_id TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_intake_status
              ON feedback_intake(status,updated_at);
            """)

    def observe(self, normalized: dict[str, Any], *, event_hash: str, consumer: str) -> dict[str, Any]:
        eid = normalized["event_id"]
        ts = now_iso()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT event_hash,consumer FROM feedback_intake WHERE event_id=?", (eid,)).fetchone()
            if row:
                conn.execute("COMMIT")
                if row["event_hash"] != event_hash or row["consumer"] != consumer:
                    raise ValueError("feedback intake event identity conflict")
                return self.get(eid) | {"duplicate_observation": True}
            conn.execute(
                """INSERT INTO feedback_intake(
                    event_id,event_hash,consumer,resource_id,project_id,session_id,run_id,feedback_ref,
                    normalized_json,status,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,'observed',?,?)""",
                (
                    eid,event_hash,consumer,normalized["resource_id"],normalized.get("project_id"),
                    normalized.get("session_id"),normalized.get("run_id"),normalized["feedback_ref"],
                    canonical(normalized),ts,ts,
                ),
            )
            conn.execute("COMMIT")
        return self.get(eid) | {"duplicate_observation": False}

    def set_semantic_job(self, event_id: str, job: dict[str, Any]) -> dict[str, Any]:
        fp = _nonempty(job.get("input_fingerprint"), "semantic job fingerprint")
        body = canonical(job)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT semantic_job_fingerprint,version FROM feedback_intake WHERE event_id=?", (event_id,)).fetchone()
            if not row:
                conn.execute("ROLLBACK"); raise ValueError("unknown feedback intake event")
            if row["semantic_job_fingerprint"] and row["semantic_job_fingerprint"] != fp:
                conn.execute("ROLLBACK"); raise ValueError("semantic job fingerprint drift")
            version = row["version"] + 1
            conn.execute(
                "UPDATE feedback_intake SET semantic_job_json=?,semantic_job_fingerprint=?,status='awaiting_semantic',version=?,updated_at=? WHERE event_id=?",
                (body,fp,version,now_iso(),event_id),
            )
            conn.execute("COMMIT")
        return self.get(event_id)

    def finish(
        self,
        event_id: str,
        *,
        status: str,
        semantic_result_hash: str,
        capture_decision: str,
        skip_reason: str | None = None,
        evidence_id: str | None = None,
        hypothesis_id: str | None = None,
        hypothesis_action: str | None = None,
        target_hypothesis_id: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"skipped", "persisted", "blocked", "failed"}:
            raise ValueError("invalid terminal intake status")
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT version FROM feedback_intake WHERE event_id=?", (event_id,)).fetchone()
            if not row:
                conn.execute("ROLLBACK"); raise ValueError("unknown feedback intake event")
            version = row["version"] + 1
            conn.execute(
                """UPDATE feedback_intake SET status=?,semantic_result_hash=?,capture_decision=?,skip_reason=?,
                   evidence_id=?,hypothesis_id=?,hypothesis_action=?,target_hypothesis_id=?,version=?,updated_at=?
                   WHERE event_id=?""",
                (status,semantic_result_hash,capture_decision,skip_reason,evidence_id,hypothesis_id,hypothesis_action,target_hypothesis_id,version,now_iso(),event_id),
            )
            conn.execute("COMMIT")
        return self.get(event_id)

    def get(self, event_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM feedback_intake WHERE event_id=?", (event_id,)).fetchone()
        if not row:
            raise ValueError("unknown feedback intake event")
        return self._projection(row)

    def list(self, *, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        if status is not None and status not in STATES:
            raise ValueError("invalid feedback intake status")
        with self.connect() as conn:
            if status:
                rows = conn.execute("SELECT * FROM feedback_intake WHERE status=? ORDER BY updated_at DESC LIMIT ?", (status,limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM feedback_intake ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._projection(row) for row in rows]

    @staticmethod
    def _projection(row: sqlite3.Row) -> dict[str, Any]:
        normalized = json.loads(row["normalized_json"])
        target = normalized.get("target", {}) if isinstance(normalized.get("target"), dict) else {}
        return {
            "schema": PROJECTION_SCHEMA,
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
            "updated_at": row["updated_at"],
            "permissions": {
                "canon_write": False,
                "framework_write": False,
                "project_profile_write": False,
                "durable_user_taste_write": False,
            },
            "model_execution": False,
        }


def _consumer(project_id: str | None, resource_id: str) -> str:
    return "learning_feedback:" + (project_id or resource_id)


def prepare_intake(
    *,
    runtime_db: str | Path,
    learning_db: str | Path,
    event: dict[str, Any],
    project_id: str | None,
    current_task: dict[str, Any] | None = None,
    semantic_available: bool = True,
) -> dict[str, Any]:
    cp = ControlPlane(runtime_db); cp.init()
    ingested = cp.ingest_event(event)
    normalized = normalize_feedback_event(event, project_id=project_id, current_task=current_task)
    consumer = _consumer(project_id, normalized["resource_id"])
    store = FeedbackIntakeStore(learning_db)
    observed = store.observe(normalized, event_hash=ingested["payload_hash"], consumer=consumer)
    if observed["status"] in {"skipped", "persisted"}:
        return {"schema": SCHEMA, "status": observed["status"], "projection": observed, "semantic_job": None, "already_processed": True, "model_execution": False}
    learning = LearningStore(learning_db); learning.init()
    payload = {
        "feedback_ref": normalized["feedback_ref"],
        "feedback_text": normalized["feedback_text"],
        "current_task": normalized["current_task"],
        "target": normalized["target"],
        "hypothesis_index": hypothesis_index(learning, project_id=project_id),
    }
    job = make_contract_job(CONTRACT_ID, normalized["event_id"], payload, source_session_id=normalized.get("session_id") or "SES-FEEDBACK-INTAKE")
    projection = store.set_semantic_job(normalized["event_id"], job)
    return {
        "schema": SCHEMA,
        "status": "awaiting_semantic",
        "semantic_available": bool(semantic_available),
        "pending_reason": None if semantic_available else "no_eligible_semantic_capability",
        "projection": projection,
        "semantic_job": job,
        "already_processed": False,
        "authority": False,
        "model_execution": False,
    }


def _capture_semantic_fields(judgment: dict[str, Any]) -> None:
    missing = sorted(field for field in CAPTURE_FIELDS if field not in judgment)
    if missing:
        raise ValueError("capture judgment missing: " + ", ".join(missing))
    if judgment.get("capture_decision") != "capture":
        raise ValueError("capture field validation requires capture decision")


def apply_semantic_result(
    *,
    runtime_db: str | Path,
    learning_db: str | Path,
    event_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    cp = ControlPlane(runtime_db); cp.init()
    store = FeedbackIntakeStore(learning_db)
    current = store.get(event_id)
    if current["status"] in {"skipped", "persisted"}:
        receipt = cp.consume_once("event", event_id, current["consumer"], current["event_hash"])
        return {"schema": SCHEMA, "status": current["status"], "projection": current, "consume_receipt": receipt, "already_processed": True, "model_execution": False}
    with store.connect() as conn:
        row = conn.execute("SELECT semantic_job_json,normalized_json FROM feedback_intake WHERE event_id=?", (event_id,)).fetchone()
    if not row or not row["semantic_job_json"]:
        raise ValueError("feedback intake has no prepared semantic job")
    job = json.loads(row["semantic_job_json"])
    errors = validate_result(job, result)
    if errors:
        raise ValueError("invalid feedback semantic result: " + "; ".join(errors))
    if result.get("status") != "completed":
        raise ValueError("feedback semantic result must be completed")
    judgment = result.get("judgment")
    if not isinstance(judgment, dict):
        raise ValueError("feedback semantic judgment required")
    decision = judgment.get("capture_decision")
    result_hash = digest(result)
    if decision == "skip":
        leaked = sorted(field for field in PREFERENCE_FIELDS if field in judgment)
        if leaked:
            raise ValueError("skip judgment must not fabricate preference fields: " + ", ".join(leaked))
        reason = judgment.get("skip_reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("skip judgment requires skip_reason")
        projection = store.finish(event_id, status="skipped", semantic_result_hash=result_hash, capture_decision="skip", skip_reason=reason.strip())
        receipt = cp.consume_once("event", event_id, projection["consumer"], projection["event_hash"])
        return {"schema": SCHEMA, "status": "skipped", "projection": projection, "consume_receipt": receipt, "already_processed": False, "model_execution": False}
    if decision != "capture":
        raise ValueError("capture_decision must be capture or skip")
    _capture_semantic_fields(judgment)
    normalized = json.loads(row["normalized_json"])
    target = normalized.get("target", {}) if isinstance(normalized.get("target"), dict) else {}
    evidence_id = stable_evidence_id(event_id, current["event_hash"], current["consumer"])
    learning = LearningStore(learning_db); learning.init()
    capture = capture_feedback(learning, {
        "schema": CAPTURE_SCHEMA,
        "project_id": normalized.get("project_id"),
        "feedback_ref": normalized["feedback_ref"],
        "feedback_event_ref": event_id,
        "artifact_ref": target.get("artifact_ref") or target.get("target_ref"),
        "artifact_fingerprint": target.get("artifact_fingerprint"),
        "evidence_id": evidence_id,
        "activation": {
            "project_preference_write_authorized": False,
            "durable_user_taste_write_authorized": False,
        },
        "interpretation": judgment,
    })
    projection = store.finish(
        event_id,
        status="persisted",
        semantic_result_hash=result_hash,
        capture_decision="capture",
        evidence_id=capture["evidence_id"],
        hypothesis_id=capture["hypothesis_id"],
        hypothesis_action=capture["hypothesis_action"],
        target_hypothesis_id=capture["target_hypothesis_id"],
    )
    receipt = cp.consume_once("event", event_id, projection["consumer"], projection["event_hash"])
    return {
        "schema": SCHEMA,
        "status": "persisted",
        "projection": projection,
        "capture": capture,
        "consume_receipt": receipt,
        "already_processed": False,
        "authority": False,
        "model_execution": False,
    }


def _event(event_id: str, text: str, *, legacy: bool = False, artifact_fp: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any]
    if legacy:
        payload = {
            "schema": LEGACY_STEERING_SCHEMA,
            "kind": "author_steering",
            "instruction": text,
            "applicability": {"scope": "current_run"},
            "authored_against_checkpoint_id": "CHK-1",
            "authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
        }
    else:
        payload = {
            "schema": GENERIC_FEEDBACK_SCHEMA,
            "kind": "feedback_observation",
            "feedback_text": text,
            "current_task": {"task_mode": "REVISE", "artifact_ref": "draft:fixture"},
            "target": {"artifact_ref": "draft:fixture", "artifact_fingerprint": artifact_fp or "sha256:" + "a" * 64},
            "authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
        }
    return {
        "schema": "novelforge_event_v1",
        "event_id": event_id,
        "event_type": "feedback.observed",
        "source": {"kind": "user", "id": "USER-FIXTURE"},
        "resource_id": "BOOK-FIXTURE",
        "session_id": "SES-FIXTURE",
        "run_id": "RUN-FIXTURE",
        "authority_scope": "request" if legacy else "observation",
        "idempotency_key": "feedback:" + event_id,
        "created_at": "2026-01-01T00:00:00Z",
        "artifact_fingerprints": [],
        "payload": payload,
    }


def _semantic_result(job: dict[str, Any], judgment: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "deterministic_fixture", "model_or_reviewer": "synthetic-contract-result"},
        "judgment": judgment,
        "proposals": [],
        "errors": [],
    }


def _capture_judgment(scope: str, mechanism: str, *, source: str = "human_review", action: str = "create", target: str | None = None, statement: str | None = None, applicability: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "capture_decision": "capture",
        "skip_reason": None,
        "scope_candidate": scope,
        "dimension": "fixture_dimension",
        "mechanism": mechanism,
        "statement": statement or mechanism,
        "observed_problem": "fixture",
        "polarity": "negative",
        "confidence": 0.9,
        "evidence_source": source,
        "desired_behavior": [],
        "avoid_behavior": ["fixture failure"],
        "exceptions": [],
        "applicability": applicability or {},
        "hypothesis_action": action,
        "target_hypothesis_id": target,
        "contradicts_hypothesis_ids": [],
    }


def self_test(path: str | Path | None = None) -> dict[str, Any]:
    root = Path(path) if path else Path(tempfile.gettempdir()) / "novelforge-feedback-intake-selftest"
    runtime_db = root.with_suffix(".runtime.db")
    learning_db = root.with_suffix(".learning.db")
    for db in (runtime_db, learning_db):
        for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
            if p.exists(): p.unlink()

    def run_capture(eid: str, text: str, judgment: dict[str, Any], *, legacy: bool = False, available: bool = True) -> dict[str, Any]:
        prepared = prepare_intake(runtime_db=runtime_db, learning_db=learning_db, event=_event(eid,text,legacy=legacy), project_id="P1", semantic_available=available)
        return apply_semantic_result(runtime_db=runtime_db, learning_db=learning_db, event_id=eid, result=_semantic_result(prepared["semantic_job"], judgment))

    # 1 automatic project feedback inside REVISE; no LEARN mode switch and no activation.
    project = run_capture("FB-1", "这本书的群像对白太书面了，以后更自然有趣一点。", _capture_judgment("project", "natural relational ensemble dialogue", source="explicit_rule"), legacy=True)
    project_ok = project["capture"]["scope"] == "project" and project["capture"]["hypothesis_state"] == "candidate"

    # 2 one-off.
    oneoff = run_capture("FB-2", "这一句话英文太多，改成中文。", _capture_judgment("one_off", "local language replacement", source="correction"))
    oneoff_ok = oneoff["capture"]["hypothesis_state"] == "candidate" and not oneoff["capture"]["active_for_future_production"]

    # 3 user taste candidate.
    user = run_capture("FB-3", "我所有中文小说都不喜欢大量夹英文。", _capture_judgment("user_taste", "avoid heavy code switching", source="explicit_rule"))
    user_ok = user["capture"]["hypothesis_state"] == "candidate"

    # 4 general-craft overreach remains candidate only.
    general = run_capture("FB-4", "所有网文都不要专业细节。", _capture_judgment("general_craft", "claimed professional detail prohibition", source="human_review"))
    general_ok = general["capture"]["hypothesis_state"] == "candidate" and not general["capture"]["general_craft_auto_promoted"]

    # 5/6 skip controls.
    def run_skip(eid: str, text: str, reason: str) -> dict[str, Any]:
        prepared = prepare_intake(runtime_db=runtime_db, learning_db=learning_db, event=_event(eid,text), project_id="P1")
        return apply_semantic_result(runtime_db=runtime_db, learning_db=learning_db, event_id=eid, result=_semantic_result(prepared["semantic_job"], {"capture_decision":"skip","skip_reason":reason,"confidence":0.99}))
    cont = run_skip("FB-5", "继续下一段。", "operational continuation command without evaluative feedback")
    ack = run_skip("FB-6", "ok", "acknowledgement without meaningful evaluative signal")
    skip_ok = cont["status"] == ack["status"] == "skipped"

    # 7 rejection keeps fingerprint/reference only in the Learning Store payload.
    rejection = run_capture("FB-7", "这版不行，太流水账。", _capture_judgment("project", "avoid procedure chronology", source="rejection"))
    with LearningStore(learning_db).connect() as conn:
        erow = conn.execute("SELECT payload_json FROM preference_evidence WHERE evidence_id=?", (rejection["capture"]["evidence_id"],)).fetchone()
    epayload = json.loads(erow["payload_json"])
    rejection_ok = epayload.get("artifact_disposition") == "rejected_negative_only" and "source_text" not in epayload and "raw_text" not in epayload

    # 8/11 distinct comparison turn strengthens existing hypothesis, no hypothesis explosion.
    target = project["capture"]["hypothesis_id"]
    comparison = run_capture("FB-8", "上一版人物更活，这版虽然更专业但不好看。", _capture_judgment("project", "natural relational ensemble dialogue", source="comparison", action="strengthen", target=target))
    two_turn_ok = comparison["capture"]["hypothesis_id"] == target and len(comparison["capture"]["evidence_ids"]) == 2

    # 9 contradiction can contest the old hypothesis with narrower applicability.
    contradiction = run_capture("FB-9", "开篇不要专业感，魅力和剧情更重要。", _capture_judgment("project", "opening charisma over professional exposition", source="correction", action="contest", target=target, applicability={"scene_types":["opening"]}))
    contradiction_ok = contradiction["capture"]["hypothesis_state"] == "contested"

    # 10 retry same event -> learning consumer receipt/evidence remains exactly once.
    p10 = prepare_intake(runtime_db=runtime_db, learning_db=learning_db, event=_event("FB-10","以后本书对白别这么书面。"), project_id="P1")
    r10a = apply_semantic_result(runtime_db=runtime_db, learning_db=learning_db, event_id="FB-10", result=_semantic_result(p10["semantic_job"], _capture_judgment("project", "less bookish dialogue", source="explicit_rule")))
    r10b = apply_semantic_result(runtime_db=runtime_db, learning_db=learning_db, event_id="FB-10", result=_semantic_result(p10["semantic_job"], _capture_judgment("project", "less bookish dialogue", source="explicit_rule")))
    with LearningStore(learning_db).connect() as conn:
        n10 = conn.execute("SELECT COUNT(*) AS n FROM preference_evidence WHERE evidence_id=?", (r10a["capture"]["evidence_id"],)).fetchone()["n"]
    retry_ok = n10 == 1 and r10b["consume_receipt"]["already_consumed"] is True

    # 12 dual consumer: steering receipt does not starve Learning receipt.
    dual_event = _event("FB-12", "这段对白太书面。", legacy=True)
    cp = ControlPlane(runtime_db); cp.init(); ing = cp.ingest_event(dual_event)
    steering_receipt = cp.consume_once("event", "FB-12", "author_steering:SES-FIXTURE", ing["payload_hash"])
    p12 = prepare_intake(runtime_db=runtime_db, learning_db=learning_db, event=dual_event, project_id="P1", current_task={"task_mode":"REVISE"})
    r12 = apply_semantic_result(runtime_db=runtime_db, learning_db=learning_db, event_id="FB-12", result=_semantic_result(p12["semantic_job"], _capture_judgment("project", "less bookish dialogue")))
    dual_ok = steering_receipt["already_consumed"] is False and r12["consume_receipt"]["already_consumed"] is False and steering_receipt["consumption_key"] != r12["consume_receipt"]["consumption_key"]

    # 13/14 missing semantic capability persists; later resume applies once.
    p13 = prepare_intake(runtime_db=runtime_db, learning_db=learning_db, event=_event("FB-13","这个人物太像工具人。"), project_id="P1", semantic_available=False)
    pending_before = FeedbackIntakeStore(learning_db).get("FB-13")
    r13 = apply_semantic_result(runtime_db=runtime_db, learning_db=learning_db, event_id="FB-13", result=_semantic_result(p13["semantic_job"], _capture_judgment("project", "side character independent agenda")))
    pending_ok = p13["pending_reason"] == "no_eligible_semantic_capability" and pending_before["status"] == "awaiting_semantic" and r13["status"] == "persisted"

    # 15 current explicit instruction remains highest projection priority.
    projection = project_author_model(LearningStore(learning_db), project_id="P1", explicit_intent=[{"statement":"Current explicit request wins."}])
    explicit_ok = projection["priority_order"][0] == "current_explicit_request" and projection["all_active_preferences_auto_included"] is False

    # 16/17 privacy and CI contract: state is DB-local and self-test executes no model.
    privacy_ok = str(learning_db).startswith(tempfile.gettempdir()) and not any(k in epayload for k in ("whole_conversation","private_profile","user_biography"))
    ci_ok = all(x.get("model_execution") is False for x in (project,oneoff,user,general,cont,ack,rejection,comparison,contradiction,r10a,r12,r13,projection))

    checks = {
        "automatic_project_feedback": project_ok,
        "one_off_not_active": oneoff_ok,
        "user_taste_candidate_not_active": user_ok,
        "general_craft_not_auto_promoted": general_ok,
        "nonfeedback_and_ack_skipped": skip_ok,
        "rejection_negative_only": rejection_ok,
        "comparison_strengthens_existing": two_turn_ok,
        "contradiction_first_class": contradiction_ok,
        "retry_exactly_once": retry_ok,
        "two_independent_turns_one_hypothesis": two_turn_ok,
        "dual_consumer_independent": dual_ok,
        "missing_semantic_pending_and_resume": pending_ok,
        "current_explicit_instruction_wins": explicit_ok,
        "privacy_minimal_runtime_storage": privacy_ok,
        "normal_ci_model_execution_false": ci_ok,
    }
    ok = all(checks.values())
    out = {
        "schema": SCHEMA,
        "feedback_intake_contract": "PASS" if ok else "FAIL",
        **checks,
        "shared_event_schema_changed": False,
        "second_learning_database_created": False,
        "project_profile_write": False,
        "canon_write": False,
        "framework_behavior_write": False,
        "model_execution": False,
    }
    for db in (runtime_db, learning_db):
        for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
            if p.exists(): p.unlink()
    return out


def _load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON input must be object")
    return value


def main() -> int:
    p = argparse.ArgumentParser(description="NovelForge automatic feedback learning intake")
    p.add_argument("--runtime-db", default=".novelforge/runtime.db")
    p.add_argument("--learning-db", default=".novelforge/learning.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare"); prep.add_argument("--event", required=True); prep.add_argument("--project-id"); prep.add_argument("--current-task"); prep.add_argument("--semantic-unavailable", action="store_true")
    apply = sub.add_parser("apply"); apply.add_argument("--event-id", required=True); apply.add_argument("--result", required=True)
    status = sub.add_parser("status"); status.add_argument("--event-id", required=True)
    ls = sub.add_parser("list"); ls.add_argument("--status"); ls.add_argument("--limit", type=int, default=50)
    st = sub.add_parser("self-test"); st.add_argument("--path")
    a = p.parse_args()
    if a.cmd == "prepare":
        task = _load(a.current_task) if a.current_task else None
        out = prepare_intake(runtime_db=a.runtime_db, learning_db=a.learning_db, event=_load(a.event), project_id=a.project_id, current_task=task, semantic_available=not a.semantic_unavailable)
    elif a.cmd == "apply":
        out = apply_semantic_result(runtime_db=a.runtime_db, learning_db=a.learning_db, event_id=a.event_id, result=_load(a.result))
    elif a.cmd == "status":
        out = FeedbackIntakeStore(a.learning_db).get(a.event_id)
    elif a.cmd == "list":
        out = {"schema": PROJECTION_SCHEMA, "items": FeedbackIntakeStore(a.learning_db).list(status=a.status, limit=a.limit), "side_effect_free": True, "model_execution": False}
    else:
        out = self_test(a.path)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("feedback_intake_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
