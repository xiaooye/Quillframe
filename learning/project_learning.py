"""Project learning service used by Core, not a second Canon or runtime store.

Core validates candidate/run/document ownership before ``observe``. The service
freezes that binding, executes registered jobs through a supplied trusted host,
and owns only Learning-domain mutations. Returned semantic results are never a
public authorization mechanism. Runtime event consumption remains a separate,
recoverable transaction after the Learning transaction commits.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from harness.semantic_workers.registered_contract_binding import validate_registered_job
from harness.semantic_workers.semantic_worker_router import make_contract_job, validate_result
from learning.author_model import project_author_model
from learning.feedback_intake import FeedbackIntakeStore, apply_semantic_result, prepare_intake
from learning.feedback_query import _projection as intake_projection
from learning.learning_store import LearningStore, canonical_json, digest, now_iso
from learning.promotion_gate import SCHEMA as PROMOTION_SCHEMA, evaluate as evaluate_promotion
from learning.user_taste import UserTasteService
from learning.author_voice import AuthorVoiceService

SCHEMA = "quillframe_project_learning_v1"
PREFERENCE_SCHEMA = "quillframe_project_preference_v1"
RECEIPT_SCHEMA = "quillframe_project_preference_receipt_v1"
SemanticRunner = Callable[[dict[str, Any]], dict[str, Any]]
_FINGERPRINT = re.compile(r"sha256:[0-9a-f]{64}\Z")
_NO_AUTHORITY = {"authority": False, "canon_write": False, "framework_write": False, "durable_user_taste_write": False}
_SOURCE_KINDS = {"author": "user", "human_reader": "authorized_human", "model_reader": "model"}


def _text(value: Any, label: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be non-empty text of at most {maximum} characters")
    return value.strip()


def _version(value: Any) -> int:
    if type(value) is not int or value < 1:
        raise ValueError("expected_version must be a positive integer")
    return value


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _source_type(event: dict[str, Any]) -> str:
    value = event.get("payload", {}).get("source_type")
    if not isinstance(value, str) or value not in _SOURCE_KINDS or event.get("source", {}).get("kind") != _SOURCE_KINDS[value]:
        raise ValueError("feedback source_type does not match its bound source")
    return value


def _require_human_feedback(event: dict[str, Any]) -> None:
    if _source_type(event) == "model_reader":
        raise ValueError("model_reader feedback is advisory only and cannot enter human learning intake")


class ProjectLearning:
    def __init__(self, *, learning_db: str | Path, runtime_db: str | Path):
        self.learning_db = Path(learning_db).resolve()
        self.runtime_db = Path(runtime_db).resolve()
        if self.learning_db == self.runtime_db:
            raise ValueError("Learning and runtime databases must be separate")

    def _init(self) -> None:
        FeedbackIntakeStore(self.learning_db)
        with LearningStore(self.learning_db).connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS project_feedback_events (
                    event_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL, event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_project_feedback_events_project
                    ON project_feedback_events(project_id,created_at);
                CREATE TABLE IF NOT EXISTS project_learning_calls (
                    call_key TEXT PRIMARY KEY, project_id TEXT NOT NULL,
                    contract_id TEXT NOT NULL, subject_id TEXT NOT NULL,
                    job_json TEXT NOT NULL, job_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL, call_id TEXT, result_json TEXT,
                    result_hash TEXT, pending_reason TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_preference_receipts (
                    receipt_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL,
                    receipt_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(project_id,idempotency_key)
                );
            """)

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection | None]:
        if not self.learning_db.exists():
            yield None
            return
        conn = sqlite3.connect(self.learning_db.as_uri() + "?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _has_table(conn: sqlite3.Connection | None, name: str) -> bool:
        return conn is not None and conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    def observe(
        self, *, project_id: str, event_id: str, feedback_text: str,
        evidence_kind: str, candidate_id: str, candidate_fingerprint: str,
        run_id: str, document_id: str, session_id: str, source_id: str = "author",
        source_type: str = "author",
        current_task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist one exact event; model readers remain advisory observations.

        A candidate fingerprint is required but is not independently attested
        here. Core must resolve the candidate and verify all these identifiers.
        """
        project_id = _text(project_id, "project_id")
        event_id = _text(event_id, "event_id")
        feedback_text = _text(feedback_text, "feedback_text", 12000)
        evidence_kind = _text(evidence_kind, "evidence_kind")
        if not isinstance(source_type, str) or source_type not in _SOURCE_KINDS:
            raise ValueError("source_type must be author|human_reader|model_reader")
        if evidence_kind not in {"explicit_rule", "user_edit", "rejection", "acceptance", "comparison", "correction", "human_review"}:
            raise ValueError("unsupported feedback evidence_kind")
        if not isinstance(candidate_fingerprint, str) or not _FINGERPRINT.fullmatch(candidate_fingerprint):
            raise ValueError("exact candidate_fingerprint required")
        target = {
            "candidate_id": _text(candidate_id, "candidate_id"),
            "artifact_ref": "candidate:" + _text(candidate_id, "candidate_id"),
            "artifact_fingerprint": candidate_fingerprint,
            "document_id": _text(document_id, "document_id"),
            "target_ref": document_id,
        }
        if current_task is not None and not isinstance(current_task, dict):
            raise ValueError("current_task must be an object")
        task = _copy(current_task or {})
        for key, value in {"project_id": project_id, "run_id": _text(run_id, "run_id"), "document_id": target["document_id"]}.items():
            if key in task and task[key] != value:
                raise ValueError("current_task binding mismatch: " + key)
            task[key] = value
        request = {
            "project_id": project_id, "event_id": event_id, "feedback_text": feedback_text,
            "evidence_kind": evidence_kind, "target": target, "run_id": run_id,
            "session_id": _text(session_id, "session_id"), "source_id": _text(source_id, "source_id"),
            "source_type": source_type,
            "current_task": task,
        }
        request_hash = digest(request)
        self._init()
        with LearningStore(self.learning_db).transaction() as conn:
            existing = conn.execute("SELECT project_id,request_hash,event_json FROM project_feedback_events WHERE event_id=?", (event_id,)).fetchone()
            if existing:
                if existing["project_id"] != project_id or existing["request_hash"] != request_hash:
                    raise ValueError("feedback event identity conflict")
                event = json.loads(existing["event_json"])
            else:
                event = {
                    "schema": "quillframe_event_v1", "event_id": event_id,
                    "event_type": "feedback.observed", "source": {"kind": _SOURCE_KINDS[source_type], "id": request["source_id"]},
                    "resource_id": project_id, "session_id": request["session_id"], "run_id": run_id,
                    "authority_scope": "observation", "idempotency_key": "project-feedback:" + event_id,
                    "created_at": now_iso(), "artifact_fingerprints": [candidate_fingerprint],
                    "payload": {
                        "schema": "quillframe_feedback_observation_v1", "kind": "feedback_observation",
                        "feedback_text": feedback_text, "evidence_kind": evidence_kind,
                        "source_type": source_type,
                        "current_task": task, "target": target,
                        "authority": False, "canon_authority": False, "framework_write_authority": False,
                    },
                }
                conn.execute("INSERT INTO project_feedback_events VALUES(?,?,?,?,?)", (event_id, project_id, request_hash, canonical_json(event), event["created_at"]))
        if source_type != "model_reader":
            self._prepare_feedback(project_id, event)
        return self.get_feedback(project_id=project_id, event_id=event_id)

    def _event(self, project_id: str, event_id: str) -> dict[str, Any]:
        with self._read() as conn:
            if not self._has_table(conn, "project_feedback_events"):
                raise ValueError("unknown Project feedback event")
            row = conn.execute("SELECT event_json FROM project_feedback_events WHERE project_id=? AND event_id=?", (project_id, event_id)).fetchone()
        if not row:
            raise ValueError("unknown Project feedback event")
        return json.loads(row["event_json"])

    def _prepare_feedback(self, project_id: str, event: dict[str, Any]) -> dict[str, Any]:
        _require_human_feedback(event)
        out = prepare_intake(runtime_db=self.runtime_db, learning_db=self.learning_db, event=event, project_id=project_id)
        if out["semantic_job"] is not None:
            self._put_job(project_id, "feedback:" + event["event_id"], out["semantic_job"])
        return out

    def _put_job(self, project_id: str, key: str, job: dict[str, Any], *, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        errors = validate_registered_job(job)
        if errors:
            raise ValueError("registered learning job invalid: " + "; ".join(errors))
        with LearningStore(self.learning_db, connection=connection).transaction() as conn:
            row = conn.execute("SELECT * FROM project_learning_calls WHERE call_key=?", (key,)).fetchone()
            if row:
                if row["project_id"] != project_id or row["job_fingerprint"] != job["input_fingerprint"]:
                    raise ValueError("learning job identity conflict")
                return dict(row)
            ts = now_iso()
            conn.execute(
                """INSERT INTO project_learning_calls(call_key,project_id,contract_id,subject_id,job_json,
                   job_fingerprint,state,created_at,updated_at) VALUES(?,?,?,?,?,?,'pending',?,?)""",
                (key, project_id, job["input"]["model_contract_id"], job["subject_id"], canonical_json(job), job["input_fingerprint"], ts, ts),
            )
            return dict(conn.execute("SELECT * FROM project_learning_calls WHERE call_key=?", (key,)).fetchone())

    def _call(self, project_id: str, key: str) -> dict[str, Any]:
        with self._read() as conn:
            if not self._has_table(conn, "project_learning_calls"):
                raise ValueError("learning job has not been prepared")
            row = conn.execute("SELECT * FROM project_learning_calls WHERE call_key=? AND project_id=?", (key, project_id)).fetchone()
        if not row:
            raise ValueError("learning job has not been prepared")
        return dict(row)

    def _execute(self, project_id: str, key: str, run_semantic: SemanticRunner) -> bool:
        if not callable(run_semantic):
            raise ValueError("a trusted semantic runner is required")
        with LearningStore(self.learning_db).transaction() as conn:
            row = conn.execute("SELECT * FROM project_learning_calls WHERE call_key=? AND project_id=?", (key, project_id)).fetchone()
            if not row:
                raise ValueError("learning job has not been prepared")
            if row["state"] != "pending":
                return False
            call_id = "LEARN-CALL-" + uuid.uuid4().hex
            conn.execute("UPDATE project_learning_calls SET state='running',call_id=?,pending_reason='semantic_call_in_progress',updated_at=? WHERE call_key=?", (call_id, now_iso(), key))
            job = json.loads(row["job_json"])
        try:
            result = run_semantic(_copy(job))
        except BaseException:
            # Timeout/process loss cannot prove whether the provider ran. Never
            # automatically spend a second call or reinterpret the same event.
            with LearningStore(self.learning_db).transaction() as conn:
                conn.execute("UPDATE project_learning_calls SET state='uncertain',pending_reason='semantic_result_unknown',updated_at=? WHERE call_key=? AND call_id=? AND state='running'", (now_iso(), key, call_id))
            raise
        self._record_result(project_id, key, result)
        return True

    def _record_result(self, project_id: str, key: str, result: dict[str, Any]) -> None:
        if not isinstance(result, dict):
            raise ValueError("learning semantic result must be an object")
        with LearningStore(self.learning_db).transaction() as conn:
            row = conn.execute("SELECT * FROM project_learning_calls WHERE call_key=? AND project_id=?", (key, project_id)).fetchone()
            if not row:
                raise ValueError("learning job has not been prepared")
            job = json.loads(row["job_json"])
            errors = validate_registered_job(job) + validate_result(job, result)
            if errors or result.get("status") != "completed":
                raise ValueError("invalid completed learning result: " + "; ".join(errors))
            result_hash = digest(result)
            if row["result_hash"]:
                if row["result_hash"] != result_hash:
                    raise ValueError("learning result identity conflict")
                return
            conn.execute("UPDATE project_learning_calls SET state='result_ready',result_json=?,result_hash=?,pending_reason=NULL,updated_at=? WHERE call_key=?", (canonical_json(result), result_hash, now_iso(), key))

    def execute(self, *, project_id: str, event_id: str, run_semantic: SemanticRunner) -> dict[str, Any]:
        event = self._event(project_id, event_id)
        self._prepare_feedback(project_id, event)
        key = "feedback:" + event_id
        executed = self._execute(project_id, key, run_semantic)
        call = self._call(project_id, key)
        if call["result_json"] is not None:
            self.apply_feedback_result(project_id=project_id, event_id=event_id, result=json.loads(call["result_json"]))
        return self.get_feedback(project_id=project_id, event_id=event_id) | {"model_execution": executed}

    def resume(self, *, project_id: str, event_id: str, run_semantic: SemanticRunner) -> dict[str, Any]:
        """Reuse a recorded result; an unknown in-flight result stays blocked."""
        return self.execute(project_id=project_id, event_id=event_id, run_semantic=run_semantic)

    def apply_feedback_result(self, *, project_id: str, event_id: str, result: dict[str, Any]) -> dict[str, Any]:
        """Trusted-host completion; never expose as arbitrary browser JSON ingress."""
        _require_human_feedback(self._event(project_id, event_id))
        key = "feedback:" + event_id
        self._record_result(project_id, key, result)
        try:
            apply_semantic_result(
                runtime_db=self.runtime_db, learning_db=self.learning_db, event_id=event_id, result=result,
                expected_project_id=project_id, allowed_scopes={"one_off", "project"},
            )
        except ValueError:
            with LearningStore(self.learning_db).transaction() as conn:
                conn.execute("UPDATE project_learning_calls SET state='blocked',pending_reason='semantic_application_rejected',updated_at=? WHERE call_key=?", (now_iso(), key))
            raise
        with LearningStore(self.learning_db).transaction() as conn:
            conn.execute("UPDATE project_learning_calls SET state='applied',pending_reason=NULL,updated_at=? WHERE call_key=?", (now_iso(), key))
        return self.get_feedback(project_id=project_id, event_id=event_id)

    @staticmethod
    def _call_projection(row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        return {key: row[key] for key in ("contract_id", "state", "call_id", "job_fingerprint", "result_hash", "pending_reason")}

    def get_feedback(self, *, project_id: str, event_id: str) -> dict[str, Any]:
        event = self._event(project_id, event_id)
        source_type = _source_type(event)
        with self._read() as conn:
            row = conn.execute("SELECT * FROM feedback_intake WHERE event_id=? AND project_id=?", (event_id, project_id)).fetchone()
            call = conn.execute("SELECT * FROM project_learning_calls WHERE call_key=? AND project_id=?", ("feedback:" + event_id, project_id)).fetchone()
        intake = intake_projection(row) if row else None
        state = intake["status"] if intake else "observed"
        if state not in {"skipped", "persisted"} and call:
            state = {"pending": "awaiting_semantic", "running": "awaiting_external", "uncertain": "awaiting_external", "result_ready": "ready_to_apply", "blocked": "blocked"}.get(call["state"], state)
        judgment = json.loads(call["result_json"])["judgment"] if call and call["result_json"] else None
        if source_type == "model_reader":
            if row is not None or call is not None:
                raise ValueError("model_reader feedback must not have a human intake or semantic call")
            state = "advisory"
        return {
            "schema": SCHEMA, "project_id": project_id, "event_id": event_id, "status": state,
            "run_id": event["run_id"], "session_id": event["session_id"],
            "candidate_id": event["payload"]["target"]["candidate_id"],
            "candidate_fingerprint": event["payload"]["target"]["artifact_fingerprint"],
            "document_id": event["payload"]["target"]["document_id"],
            "feedback_text": event["payload"]["feedback_text"], "evidence_kind": event["payload"]["evidence_kind"],
            "source_type": source_type, "source_id": event["source"]["id"],
            "advisory_only": source_type == "model_reader",
            "intake": intake, "semantic_call": self._call_projection(call), "interpretation": judgment,
            "side_effect_free": True, "model_execution": False, **_NO_AUTHORITY,
        }

    def list_feedback(self, *, project_id: str, limit: int = 50) -> dict[str, Any]:
        limit = max(1, min(_version(limit), 200))
        with self._read() as conn:
            rows = conn.execute("SELECT event_id FROM project_feedback_events WHERE project_id=? ORDER BY created_at DESC,event_id LIMIT ?", (project_id, limit)).fetchall() if self._has_table(conn, "project_feedback_events") else []
        items = []
        for row in rows:
            item = self.get_feedback(project_id=project_id, event_id=row["event_id"])
            item.pop("feedback_text")
            item.pop("interpretation")
            items.append(item)
        return {"schema": SCHEMA, "project_id": project_id, "items": items, "side_effect_free": True, "model_execution": False, **_NO_AUTHORITY}

    @staticmethod
    def _hypothesis(conn: sqlite3.Connection, project_id: str, hypothesis_id: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM preference_hypotheses WHERE project_id=? AND subject_scope='project' AND hypothesis_id=?", (project_id, hypothesis_id)).fetchone()
        if not row:
            raise ValueError("unknown Project preference")
        return row

    @staticmethod
    def _preference(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "schema": PREFERENCE_SCHEMA, "hypothesis_id": row["hypothesis_id"], "project_id": row["project_id"],
            "scope": row["subject_scope"], "dimension": row["dimension"], "statement": row["statement"],
            "mechanism": row["mechanism"], "state": row["state"], "version": row["version"],
            "confidence": row["confidence"], "applicability": json.loads(row["applicability_json"]),
            "evidence_ids": json.loads(row["evidence_ids_json"]), "contradiction_ids": json.loads(row["contradiction_ids_json"]),
            "active_for_future_production": row["state"] == "active", **_NO_AUTHORITY,
        }

    def list_preferences(self, *, project_id: str, limit: int = 100) -> dict[str, Any]:
        limit = max(1, min(_version(limit), 200))
        with self._read() as conn:
            rows = conn.execute("SELECT * FROM preference_hypotheses WHERE project_id=? AND subject_scope='project' ORDER BY updated_at DESC,hypothesis_id LIMIT ?", (project_id, limit)).fetchall() if self._has_table(conn, "preference_hypotheses") else []
        return {"schema": SCHEMA, "project_id": project_id, "items": [self._preference(row) for row in rows], "side_effect_free": True, "model_execution": False, **_NO_AUTHORITY}

    @staticmethod
    def _review_key(project_id: str, hypothesis_id: str, version: int) -> str:
        return "promotion:" + digest([project_id, hypothesis_id, version])

    @staticmethod
    def _assert_human_evidence(conn: sqlite3.Connection, project_id: str, evidence_ids: list[str]) -> None:
        if not evidence_ids or len(evidence_ids) > 64:
            raise ValueError("activation review requires 1..64 exact evidence references")
        for evidence_id in evidence_ids:
            row = conn.execute("SELECT payload_json FROM preference_evidence WHERE project_id=? AND evidence_id=?", (project_id, evidence_id)).fetchone()
            if row is None:
                raise ValueError("preference evidence missing or belongs to another Project")
            payload = json.loads(row["payload_json"])
            original = conn.execute("SELECT event_json FROM project_feedback_events WHERE project_id=? AND event_id=?", (project_id, payload.get("feedback_event_ref"))).fetchone()
            if original is None:
                raise ValueError("activation review requires the original bound human feedback")
            _require_human_feedback(json.loads(original["event_json"]))

    def get_preference(self, *, project_id: str, hypothesis_id: str) -> dict[str, Any]:
        with self._read() as conn:
            if not self._has_table(conn, "preference_hypotheses"):
                raise ValueError("unknown Project preference")
            row = self._hypothesis(conn, project_id, hypothesis_id)
            out = self._preference(row)
            call = conn.execute("SELECT * FROM project_learning_calls WHERE call_key=? AND project_id=?", (self._review_key(project_id, hypothesis_id, row["version"]), project_id)).fetchone() if self._has_table(conn, "project_learning_calls") else None
            evidence = []
            for eid in out["evidence_ids"]:
                item = conn.execute("SELECT * FROM preference_evidence WHERE evidence_id=? AND project_id=?", (eid, project_id)).fetchone()
                if item:
                    payload = json.loads(item["payload_json"])
                    evidence.append({key: payload.get(key) for key in ("evidence_id", "source", "polarity", "mechanism", "feedback_event_ref", "artifact_ref", "artifact_fingerprint")})
        judgment = json.loads(call["result_json"])["judgment"] if call and call["result_json"] else None
        out.update({"evidence": evidence, "activation_review": {"semantic_call": self._call_projection(call), "judgment": judgment}, "side_effect_free": True, "model_execution": False})
        return out

    def prepare_activation_review(self, *, project_id: str, hypothesis_id: str, expected_version: int) -> dict[str, Any]:
        expected_version = _version(expected_version)
        self._init()
        with LearningStore(self.learning_db).transaction() as conn:
            row = self._hypothesis(conn, project_id, hypothesis_id)
            if row["version"] != expected_version:
                raise ValueError("hypothesis version mismatch")
            if row["state"] in {"active", "superseded"}:
                raise ValueError("preference is not eligible for activation review")
            self._assert_human_evidence(conn, project_id, json.loads(row["evidence_ids_json"]))
            key = self._review_key(project_id, hypothesis_id, expected_version)
            saved = conn.execute("SELECT * FROM project_learning_calls WHERE call_key=?", (key,)).fetchone()
            if saved:
                return {"schema": SCHEMA, "project_id": project_id, "hypothesis_id": hypothesis_id, "expected_version": expected_version, "semantic_job": json.loads(saved["job_json"]), "semantic_call": self._call_projection(saved), **_NO_AUTHORITY}
            preference = self._preference(row)
            refs = preference["evidence_ids"]
            if not refs or len(refs) > 64:
                raise ValueError("activation review requires 1..64 exact evidence references")
            evidence = []
            text_size = 0
            for eid in refs:
                erow = conn.execute("SELECT payload_json FROM preference_evidence WHERE evidence_id=? AND project_id=?", (eid, project_id)).fetchone()
                if not erow:
                    raise ValueError("preference evidence missing or belongs to another Project")
                payload = json.loads(erow["payload_json"])
                summary = {key: payload.get(key) for key in ("evidence_id", "source", "polarity", "observed_problem", "mechanism", "artifact_ref", "artifact_fingerprint", "feedback_event_ref")}
                event = conn.execute("SELECT event_json FROM project_feedback_events WHERE event_id=? AND project_id=?", (payload.get("feedback_event_ref"), project_id)).fetchone()
                if not event:
                    raise ValueError("activation review requires the original bound human feedback")
                original = json.loads(event["event_json"])
                summary["feedback_text"] = original["payload"]["feedback_text"]
                text_size += len(summary["feedback_text"])
                evidence.append(summary)
            if text_size > 24000:
                raise ValueError("activation evidence exceeds bounded review input")
            payload = {
                "candidate_id": hypothesis_id + ":v" + str(expected_version), "scope": "project",
                "mechanism": row["mechanism"], "statement": row["statement"], "evidence_refs": refs,
                "evidence_summary": evidence, "applicability_boundary": preference["applicability"],
                "contradiction_evidence": [item for item in evidence if item["evidence_id"] in preference["contradiction_ids"]],
            }
            job = make_contract_job("learning.promotion_review", payload["candidate_id"], payload)
            call = self._put_job(project_id, key, job, connection=conn)
        return {"schema": SCHEMA, "project_id": project_id, "hypothesis_id": hypothesis_id, "expected_version": expected_version, "semantic_job": job, "semantic_call": self._call_projection(call), **_NO_AUTHORITY}

    def execute_activation_review(self, *, project_id: str, hypothesis_id: str, expected_version: int, run_semantic: SemanticRunner) -> dict[str, Any]:
        self.prepare_activation_review(project_id=project_id, hypothesis_id=hypothesis_id, expected_version=expected_version)
        executed = self._execute(project_id, self._review_key(project_id, hypothesis_id, expected_version), run_semantic)
        return self.get_preference(project_id=project_id, hypothesis_id=hypothesis_id) | {"model_execution": executed}

    def apply_activation_review(self, *, project_id: str, hypothesis_id: str, expected_version: int, result: dict[str, Any]) -> dict[str, Any]:
        """Trusted-host completion of the already prepared promotion review."""
        _version(expected_version)
        self._record_result(project_id, self._review_key(project_id, hypothesis_id, expected_version), result)
        return self.get_preference(project_id=project_id, hypothesis_id=hypothesis_id)

    def activate(self, *, project_id: str, hypothesis_id: str, expected_version: int, user_authorized: bool, authorized_by: str, idempotency_key: str) -> dict[str, Any]:
        return self._change_state(project_id=project_id, hypothesis_id=hypothesis_id, expected_version=expected_version, user_authorized=user_authorized, authorized_by=authorized_by, idempotency_key=idempotency_key, action="activate")

    def deactivate(self, *, project_id: str, hypothesis_id: str, expected_version: int, user_authorized: bool, authorized_by: str, idempotency_key: str) -> dict[str, Any]:
        return self._change_state(project_id=project_id, hypothesis_id=hypothesis_id, expected_version=expected_version, user_authorized=user_authorized, authorized_by=authorized_by, idempotency_key=idempotency_key, action="deactivate")

    def _change_state(self, *, project_id: str, hypothesis_id: str, expected_version: int, user_authorized: bool, authorized_by: str, idempotency_key: str, action: str) -> dict[str, Any]:
        if user_authorized is not True:
            raise ValueError("explicit user authorization required")
        request = {"project_id": _text(project_id, "project_id"), "hypothesis_id": _text(hypothesis_id, "hypothesis_id"), "expected_version": _version(expected_version), "authorized_by": _text(authorized_by, "authorized_by"), "user_authorized": True, "action": action, "idempotency_key": _text(idempotency_key, "idempotency_key")}
        request_hash = digest(request)
        self._init()
        with LearningStore(self.learning_db).transaction() as conn:
            previous = conn.execute("SELECT request_hash,receipt_json FROM project_preference_receipts WHERE project_id=? AND idempotency_key=?", (project_id, idempotency_key)).fetchone()
            if previous:
                if previous["request_hash"] != request_hash:
                    raise ValueError("preference idempotency conflict")
                return {"receipt": json.loads(previous["receipt_json"]), "replayed": True, **_NO_AUTHORITY}
            row = self._hypothesis(conn, project_id, hypothesis_id)
            if row["version"] != expected_version:
                raise ValueError("hypothesis version mismatch")
            before = self._preference(row)
            review_fp = None
            review_result_hash = None
            if action == "activate":
                if row["state"] in {"active", "superseded"}:
                    raise ValueError("preference cannot be activated from its current state")
                self._assert_human_evidence(conn, project_id, before["evidence_ids"])
                call = conn.execute("SELECT * FROM project_learning_calls WHERE call_key=? AND project_id=?", (self._review_key(project_id, hypothesis_id, expected_version), project_id)).fetchone()
                if not call or not call["result_json"]:
                    raise ValueError("completed registered promotion review required")
                job = json.loads(call["job_json"])
                result = json.loads(call["result_json"])
                if job["input"]["payload"].get("statement") != row["statement"] or job["input"]["payload"].get("applicability_boundary") != before["applicability"]:
                    raise ValueError("promotion review no longer matches this preference")
                candidate = {"schema": PROMOTION_SCHEMA, "candidate_id": hypothesis_id + ":v" + str(expected_version), "scope": "project", "mechanism": row["mechanism"], "evidence": {"evidence_refs": before["evidence_ids"], "explicit_project_authority": True}, "semantic_review_binding": {"job": job, "result": result}}
                report = evaluate_promotion(candidate)
                if report["status"] != "ready_for_activation":
                    raise ValueError("promotion review does not support activation")
                review_fp = call["job_fingerprint"]
                review_result_hash = call["result_hash"]
                after_state = "active"
            else:
                if row["state"] in {"deprecated", "superseded"}:
                    raise ValueError("preference is already inactive")
                after_state = "deprecated"
            conn.execute("UPDATE preference_hypotheses SET state=?,version=version+1,updated_at=? WHERE hypothesis_id=? AND project_id=? AND version=?", (after_state, now_iso(), hypothesis_id, project_id, expected_version))
            after = self._preference(self._hypothesis(conn, project_id, hypothesis_id))
            receipt = {
                "schema": RECEIPT_SCHEMA, "receipt_id": "PREF-" + uuid.uuid4().hex, **request,
                "before_state": before["state"], "after_state": after_state,
                "before_version": expected_version, "after_version": after["version"],
                "before_fingerprint": digest(before), "after_fingerprint": digest(after),
                "review_job_fingerprint": review_fp, "review_result_hash": review_result_hash,
                "transaction_scope": "learning_database", "cross_database_atomic": False,
                "created_at": now_iso(), **_NO_AUTHORITY,
            }
            conn.execute("INSERT INTO project_preference_receipts VALUES(?,?,?,?,?,?)", (receipt["receipt_id"], project_id, idempotency_key, request_hash, canonical_json(receipt), receipt["created_at"]))
        return {"receipt": receipt, "replayed": False, **_NO_AUTHORITY}

    def project_context(self, *, project_id: str, explicit_intent: list[dict[str, Any]] | None = None, selected_hypothesis_ids: list[str] | None = None) -> dict[str, Any]:
        selected = selected_hypothesis_ids or []
        taste_snapshot = UserTasteService.snapshot_readonly(self.learning_db)
        voice_snapshot = AuthorVoiceService.snapshot_readonly(
            self.learning_db, project_id=project_id
        )
        with self._read() as conn:
            if not self._has_table(conn, "preference_hypotheses"):
                if selected:
                    raise ValueError("selected preference is not active for this Project")
                projection = {"schema": "quillframe_author_model_projection_v2", "project_id": project_id, "priority_order": ["current_explicit_request", "selected_user_taste_active", "selected_project_active"], "explicit_intent": explicit_intent or [], "available_active_hypothesis_ids": [], "active_preference_index": [], "selected_hypothesis_ids": [], "active_preferences": [], "user_taste_snapshot": taste_snapshot, "user_taste_selection_mode": "semantic_per_run" if taste_snapshot["policy"]["enabled"] else "disabled", "author_voice_snapshot": voice_snapshot, "author_voice_status": voice_snapshot["status"], "all_active_preferences_auto_included": False, "candidate_hypotheses_included": False, **_NO_AUTHORITY}
                projection["projection_fingerprint"] = digest(projection)
                return projection
            for hypothesis_id in selected:
                row = self._hypothesis(conn, project_id, hypothesis_id)
                if row["state"] != "active":
                    raise ValueError("selected preference is not active for this Project")
            projection = project_author_model(LearningStore(self.learning_db, connection=conn), project_id=project_id, explicit_intent=explicit_intent, selected_hypothesis_ids=selected)
        projection["active_preference_index"] = [item for item in projection["active_preference_index"] if item["scope"] == "project" and item["project_id"] == project_id]
        projection["available_active_hypothesis_ids"] = [item["hypothesis_id"] for item in projection["active_preference_index"]]
        projection["priority_order"] = ["current_explicit_request", "selected_user_taste_active", "selected_project_active"]
        projection["user_taste_snapshot"] = taste_snapshot
        projection["user_taste_selection_mode"] = "semantic_per_run" if taste_snapshot["policy"]["enabled"] else "disabled"
        projection["author_voice_snapshot"] = voice_snapshot
        projection["author_voice_status"] = voice_snapshot["status"]
        projection["projection_fingerprint"] = digest(projection)
        return projection
