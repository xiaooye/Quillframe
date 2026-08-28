"""Private exact-call journal for resumable production execution.

An intent is committed before the model is invoked. Only an exact confirmed
response is reusable; an abandoned or timed-out intent never authorizes another
model invocation. Public projections contain identities and hashes, not prompts,
private character state, raw drafts or unqualified manuscript text.
"""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from typing import Any

from .quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso

EXECUTION_LEASE_SECONDS = 45.0
JOURNAL_SCHEMA = "quillframe_production_execution_journal_v1"


class ProductionStageError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


def _fingerprint(value: Any) -> str:
    return fingerprint_text(canonical_json(value))


class ProductionStageRepository:
    def __init__(
        self,
        store: QuillframeStore,
        *,
        clock: Callable[[], float] | None = None,
        lease_seconds: float = EXECUTION_LEASE_SECONDS,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self.store = store
        self.clock = clock or time.time
        self.lease_seconds = lease_seconds

    def _now_ms(self) -> int:
        return int(self.clock() * 1000)

    @staticmethod
    def _event_locked(conn, run_id: str, kind: str, payload: dict[str, Any]) -> None:  # noqa: ANN001
        conn.execute(
            "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
            ("evt_" + uuid.uuid4().hex, run_id, kind, canonical_json(payload), now_iso()),
        )

    @staticmethod
    def assert_not_cancelled_locked(conn, run_id: str) -> None:  # noqa: ANN001
        run = conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            raise ProductionStageError("run_not_found", run_id)
        execution = conn.execute(
            "SELECT cancel_requested FROM production_executions WHERE run_id=?", (run_id,)
        ).fetchone()
        if run["status"] == "cancelled" or (execution and execution["cancel_requested"]):
            raise ProductionStageError("run_cancelled", "production execution was cancelled")

    def guard_locked(self, conn, run_id: str, owner_token: str | None = None) -> None:  # noqa: ANN001
        self.assert_not_cancelled_locked(conn, run_id)
        if owner_token is None:
            return
        row = conn.execute(
            "SELECT owner_token,lease_expires_at_ms FROM production_executions WHERE run_id=?", (run_id,)
        ).fetchone()
        if not row or row["owner_token"] != owner_token or (row["lease_expires_at_ms"] or 0) <= self._now_ms():
            raise ProductionStageError("execution_lease_lost", "production execution no longer owns its write lease")

    def acquire(self, project_id: str, run_id: str, request: dict[str, Any]) -> str:
        budget = request.get("max_model_calls")
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1 or budget > 64:
            raise ProductionStageError("invalid_model_call_budget", "max_model_calls must be an integer from 1 to 64")
        request_json = canonical_json(request)
        request_fp = fingerprint_text(request_json)
        stamp = now_iso()
        owner = "exec_" + uuid.uuid4().hex
        now = self._now_ms()
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.assert_not_cancelled_locked(conn, run_id)
            row = conn.execute("SELECT * FROM production_executions WHERE run_id=?", (run_id,)).fetchone()
            if row:
                if row["request_fingerprint"] != request_fp or row["request_json"] != request_json:
                    raise ProductionStageError(
                        "execution_request_conflict", "resume must use the exact frozen production request"
                    )
                if row["owner_token"] and (row["lease_expires_at_ms"] or 0) > now:
                    raise ProductionStageError("run_in_progress", "production execution has an active owner")
                # Taking over a dead executor does not replay its external calls.
                conn.execute(
                    "UPDATE production_stage_calls SET state='unconfirmed',error_code='executor_interrupted',updated_at=? "
                    "WHERE run_id=? AND state='dispatched'",
                    (stamp, run_id),
                )
                conn.execute(
                    "UPDATE production_executions SET owner_token=?,lease_expires_at_ms=?,updated_at=? WHERE run_id=?",
                    (owner, now + int(self.lease_seconds * 1000), stamp, run_id),
                )
            else:
                conn.execute(
                    "INSERT INTO production_executions(run_id,request_fingerprint,request_json,owner_token,lease_expires_at_ms,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (run_id, request_fp, request_json, owner, now + int(self.lease_seconds * 1000), stamp, stamp),
                )
            self._event_locked(conn, run_id, "production_execution_acquired", {
                "request_fingerprint": request_fp, "resumed": row is not None, "authority": False,
            })
            conn.commit()
        return owner

    def renew(self, project_id: str, run_id: str, owner_token: str) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.guard_locked(conn, run_id, owner_token)
            conn.execute(
                "UPDATE production_executions SET lease_expires_at_ms=?,updated_at=? WHERE run_id=? AND owner_token=?",
                (self._now_ms() + int(self.lease_seconds * 1000), now_iso(), run_id, owner_token),
            )
            conn.commit()

    def release(self, project_id: str, run_id: str, owner_token: str) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT owner_token FROM production_executions WHERE run_id=?", (run_id,)).fetchone()
            if row and row["owner_token"] == owner_token:
                conn.execute(
                    "UPDATE production_stage_calls SET state='unconfirmed',error_code=COALESCE(error_code,'executor_interrupted'),updated_at=? "
                    "WHERE run_id=? AND owner_token=? AND state='dispatched'", (now_iso(), run_id, owner_token),
                )
                conn.execute(
                    "UPDATE production_executions SET owner_token=NULL,lease_expires_at_ms=NULL,updated_at=? WHERE run_id=?",
                    (now_iso(), run_id),
                )
            conn.commit()

    def begin_call(
        self, project_id: str, run_id: str, owner_token: str, *, stage_key: str, job: dict[str, Any],
    ) -> dict[str, Any]:
        job_json = canonical_json(job)
        input_fp = str(job.get("input_fingerprint") or "")
        without_fp = {key: value for key, value in job.items() if key != "input_fingerprint"}
        if job.get("run_id") != run_id or input_fp != _fingerprint(without_fp):
            raise ProductionStageError("stage_input_invalid", "stage job identity or input fingerprint is invalid")
        budget_ms = job.get("budgets", {}).get("max_elapsed_ms")
        if job.get("budgets", {}).get("max_model_requests") != 1:
            raise ProductionStageError("stage_input_invalid", "each journaled stage must reserve exactly one model request")
        if not isinstance(budget_ms, int) or isinstance(budget_ms, bool) or budget_ms <= 0:
            raise ProductionStageError("stage_input_invalid", "stage deadline budget is invalid")
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.guard_locked(conn, run_id, owner_token)
            prior = conn.execute(
                "SELECT * FROM production_stage_calls WHERE run_id=? AND stage_key=?", (run_id, stage_key)
            ).fetchone()
            if prior:
                if prior["input_fingerprint"] != input_fp or prior["job_json"] != job_json:
                    raise ProductionStageError("stage_input_conflict", "a stage key already binds a different exact input")
                if prior["state"] != "confirmed":
                    raise ProductionStageError("stage_result_unconfirmed", "external stage result is not confirmed", detail={
                        "call_id": prior["call_id"], "stage_key": stage_key, "state": prior["state"],
                    })
                result = json.loads(prior["result_json"])
                if _fingerprint(result) != prior["result_fingerprint"]:
                    raise ProductionStageError("stage_result_corrupt", "confirmed stage result fingerprint does not match")
                conn.commit()
                return {"call_id": prior["call_id"], "replayed": True, "result": result}
            pending = conn.execute(
                "SELECT call_id,stage_key,state FROM production_stage_calls WHERE run_id=? AND state IN ('dispatched','unconfirmed') LIMIT 1",
                (run_id,),
            ).fetchone()
            if pending:
                raise ProductionStageError("stage_result_unconfirmed", "another external stage has an unconfirmed result", detail=dict(pending))
            execution = conn.execute("SELECT request_json FROM production_executions WHERE run_id=?", (run_id,)).fetchone()
            limit = json.loads(execution["request_json"])["max_model_calls"]
            calls = conn.execute("SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?", (run_id,)).fetchone()[0]
            if calls >= limit:
                raise ProductionStageError("model_call_budget_exhausted", "frozen production model-call budget is exhausted", detail={
                    "dispatched_call_count": calls, "max_model_calls": limit,
                })
            call_id = "pcall_" + uuid.uuid4().hex
            stamp = now_iso()
            deadline = self._now_ms() + budget_ms
            conn.execute(
                "INSERT INTO production_stage_calls(call_id,run_id,stage_key,runtime_role,input_fingerprint,job_json,owner_token,state,deadline_at_ms,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,'dispatched',?,?,?)",
                (call_id, run_id, stage_key, job["runtime_role"], input_fp, job_json, owner_token, deadline, stamp, stamp),
            )
            self._event_locked(conn, run_id, "production_stage_dispatched", {
                "call_id": call_id, "stage_key": stage_key, "runtime_role": job["runtime_role"],
                "input_fingerprint": input_fp, "deadline_at_ms": deadline, "authority": False,
            })
            conn.commit()
            return {"call_id": call_id, "replayed": False, "deadline_at_ms": deadline}

    def confirm_call(
        self, project_id: str, run_id: str, owner_token: str, *, call_id: str, result: dict[str, Any],
    ) -> None:
        result_json = canonical_json(result)
        result_fp = fingerprint_text(result_json)
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.guard_locked(conn, run_id, owner_token)
            row = conn.execute("SELECT * FROM production_stage_calls WHERE run_id=? AND call_id=?", (run_id, call_id)).fetchone()
            if not row or row["owner_token"] != owner_token:
                raise ProductionStageError("stage_call_owner_mismatch", "stage confirmation has no matching owned intent")
            job = json.loads(row["job_json"])
            if any(result.get(key) != job.get(key) for key in ("job_id", "session_id", "run_id", "input_fingerprint")):
                raise ProductionStageError("stage_result_binding_mismatch", "model response does not bind the exact frozen AgentJob")
            if result.get("model_service_id") != job.get("service_id"):
                raise ProductionStageError("stage_result_binding_mismatch", "model response changed its service identity")
            if row["state"] == "confirmed":
                if row["result_fingerprint"] != result_fp or row["result_json"] != result_json:
                    raise ProductionStageError("stage_result_conflict", "a confirmed result cannot be replaced")
                conn.commit()
                return
            if row["state"] != "dispatched":
                raise ProductionStageError("stage_result_unconfirmed", "a closed stage intent cannot accept a late response")
            if self._now_ms() >= row["deadline_at_ms"]:
                conn.execute(
                    "UPDATE production_stage_calls SET state='unconfirmed',error_code='stage_deadline_exceeded',updated_at=? WHERE call_id=?",
                    (now_iso(), call_id),
                )
                conn.commit()
                raise ProductionStageError("stage_deadline_exceeded", "stage response arrived after its frozen deadline")
            conn.execute(
                "UPDATE production_stage_calls SET state='confirmed',result_json=?,result_fingerprint=?,updated_at=? WHERE call_id=?",
                (result_json, result_fp, now_iso(), call_id),
            )
            self._event_locked(conn, run_id, "production_stage_result_confirmed", {
                "call_id": call_id, "stage_key": row["stage_key"], "input_fingerprint": row["input_fingerprint"],
                "result_fingerprint": result_fp, "agent_status": result.get("status"), "authority": False,
            })
            conn.commit()

    def mark_unconfirmed(self, project_id: str, run_id: str, owner_token: str, call_id: str, code: str) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute(
                "UPDATE production_stage_calls SET state='unconfirmed',error_code=?,updated_at=? "
                "WHERE run_id=? AND call_id=? AND owner_token=? AND state='dispatched'",
                (code, now_iso(), run_id, call_id, owner_token),
            )
            conn.commit()

    @staticmethod
    def cancel_locked(conn, run_id: str) -> None:  # noqa: ANN001
        """Join the caller's existing authorized cancel transaction; never commit it."""
        run = conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            raise ProductionStageError("run_not_found", run_id)
        if run["status"] == "completed":
            raise ProductionStageError("run_terminal", "a completed production run cannot be cancelled")
        stamp = now_iso()
        conn.execute("UPDATE runs SET status='cancelled',updated_at=? WHERE run_id=?", (stamp, run_id))
        conn.execute(
            "UPDATE production_executions SET cancel_requested=1,owner_token=NULL,lease_expires_at_ms=NULL,updated_at=? WHERE run_id=?",
            (stamp, run_id),
        )
        conn.execute(
            "UPDATE production_stage_calls SET state='cancelled',error_code='run_cancelled',updated_at=? "
            "WHERE run_id=? AND state IN ('dispatched','unconfirmed')", (stamp, run_id),
        )

    def load_request(self, project_id: str, run_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            row = conn.execute("SELECT request_json,request_fingerprint FROM production_executions WHERE run_id=?", (run_id,)).fetchone()
        if not row:
            raise ProductionStageError("execution_request_missing", "no production execute request has been frozen")
        value = json.loads(row["request_json"])
        if _fingerprint(value) != row["request_fingerprint"]:
            raise ProductionStageError("execution_request_corrupt", "frozen execute request fingerprint does not match")
        return value

    def projection(self, project_id: str, run_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            execution = conn.execute(
                "SELECT request_fingerprint,request_json,owner_token,lease_expires_at_ms,cancel_requested FROM production_executions WHERE run_id=?", (run_id,)
            ).fetchone()
            rows = conn.execute(
                "SELECT call_id,stage_key,runtime_role,input_fingerprint,state,deadline_at_ms,result_fingerprint,error_code,created_at,updated_at "
                "FROM production_stage_calls WHERE run_id=? ORDER BY rowid", (run_id,)
            ).fetchall()
        active = bool(execution and execution["owner_token"] and (execution["lease_expires_at_ms"] or 0) > self._now_ms())
        calls = [dict(row) for row in rows]
        pending = [row["call_id"] for row in calls if row["state"] in {"dispatched", "unconfirmed"}]
        return {
            "schema": JOURNAL_SCHEMA, "run_id": run_id,
            "request_fingerprint": execution["request_fingerprint"] if execution else None,
            "active_executor": active, "cancel_requested": bool(execution and execution["cancel_requested"]),
            "calls": calls, "unconfirmed_call_ids": pending,
            "confirmed_call_count": sum(row["state"] == "confirmed" for row in calls),
            "dispatched_call_count": len(calls),
            "model_call_budget": json.loads(execution["request_json"])["max_model_calls"] if execution else None,
            "safe_to_resume_confirmed_only": bool(execution and not active and not pending and not execution["cancel_requested"]),
            "private_payloads_visible": False, "authority": False,
        }
