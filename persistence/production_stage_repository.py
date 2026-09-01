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

EXECUTION_LEASE_SECONDS = 20.0
JOURNAL_SCHEMA = "quillframe_production_execution_journal_v1"
POLLABLE_ERROR_CODES = {"idempotent_model_request", "model_pending"}
MAX_SQLITE_INTEGER = (1 << 63) - 1


class ProductionStageError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


def _fingerprint(value: Any) -> str:
    return fingerprint_text(canonical_json(value))


def _valid_fingerprint(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        return False
    try:
        int(value[7:], 16)
    except ValueError:
        return False
    return True


def _billing_record_payload(
    *, call_id: str, run_id: str, result_fingerprint: str, cost_micros: int,
    receipt_source: str, evidence_ref: str, evidence_fingerprint: str,
) -> dict[str, Any]:
    return {
        "schema": "quillframe_production_billing_receipt_v1",
        "call_id": call_id,
        "run_id": run_id,
        "result_fingerprint": result_fingerprint,
        "cost_micros": cost_micros,
        "receipt_source": receipt_source,
        "evidence_ref": evidence_ref,
        "evidence_fingerprint": evidence_fingerprint,
        "authority": False,
    }


def _build_migration_payload(
    *, migration_id: str, run_id: str, from_request_fingerprint: str,
    to_request_fingerprint: str, from_build_fingerprint: str,
    to_build_fingerprint: str, regression_receipt_id: str,
    regression_receipt_fingerprint: str,
    confirmed_checkpoint_core_fingerprints: list[str], prior_run_status: str,
    from_request_version: int, to_request_version: int, authorization_ref: str,
) -> dict[str, Any]:
    return {
        "schema": "quillframe_production_build_migration_v1",
        "migration_id": migration_id,
        "run_id": run_id,
        "from_request_fingerprint": from_request_fingerprint,
        "to_request_fingerprint": to_request_fingerprint,
        "from_build_fingerprint": from_build_fingerprint,
        "to_build_fingerprint": to_build_fingerprint,
        "regression_receipt_id": regression_receipt_id,
        "regression_receipt_fingerprint": regression_receipt_fingerprint,
        "confirmed_checkpoint_core_fingerprints": confirmed_checkpoint_core_fingerprints,
        "prior_run_status": prior_run_status,
        "from_request_version": from_request_version,
        "to_request_version": to_request_version,
        "authorization_ref": authorization_ref,
        "authority": False,
    }


def _checkpoint_core_payload(checkpoint: dict[str, Any]) -> dict[str, Any]:
    """Immutable transport/input/output identity, excluding derived receipts."""

    return {
        "schema": "quillframe_production_node_checkpoint_core_v1",
        "run_id": checkpoint.get("run_id"),
        "node_id": checkpoint.get("node_id"),
        "call_id": checkpoint.get("call_id"),
        "runtime_role": checkpoint.get("runtime_role"),
        "framework_build_fingerprint": checkpoint.get("framework_build_fingerprint"),
        "execution_request_fingerprint": checkpoint.get("execution_request_fingerprint"),
        "input_fingerprint": checkpoint.get("input_fingerprint"),
        "output_fingerprint": checkpoint.get("output_fingerprint"),
        "prompt_binding": checkpoint.get("prompt_binding"),
        "upstream_dependencies": checkpoint.get("upstream_dependencies"),
        "model_request": checkpoint.get("model_request"),
        "authority": False,
    }


def _fingerprint_dependencies(value: Any, *, path: str = "$") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(child, str) and key.endswith("fingerprint") and child.startswith("sha256:"):
                rows.append({"path": child_path, "fingerprint": child})
            else:
                rows.extend(_fingerprint_dependencies(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(_fingerprint_dependencies(child, path=f"{path}[{index}]"))
    return rows


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
    def _result_billing_evidence(result: dict[str, Any], result_fp: str) -> dict[str, Any] | None:
        """Validate provider billing evidence without fabricating a zero charge."""

        requests = result.get("model_requests")
        if not isinstance(requests, int) or isinstance(requests, bool) or requests < 0:
            raise ProductionStageError("billing_receipt_invalid", "model request count is invalid")
        if requests == 0:
            if result.get("status") == "completed":
                # A completed model job cannot be represented as a free
                # pre-dispatch terminal result. Preserve it, but require an
                # authoritative accounting reconciliation.
                return None
            return {
                "cost_micros": 0,
                "receipt_source": "no_model_request",
                "evidence_ref": "agent_result:" + result_fp,
                "evidence_fingerprint": result_fp,
            }
        usage = result.get("usage")
        receipt = usage.get("billing_receipt") if isinstance(usage, dict) else None
        if not isinstance(receipt, dict):
            return None
        supplied = receipt.get("receipt_fingerprint")
        expected = _fingerprint({
            key: value for key, value in receipt.items() if key != "receipt_fingerprint"
        })
        rows = receipt.get("request_receipts")
        cost = receipt.get("cost_micros")
        valid_rows = (
            isinstance(rows, list)
            and len(rows) == requests
            and [row.get("request_ordinal") if isinstance(row, dict) else None for row in rows]
            == list(range(1, requests + 1))
            and all(
                isinstance(row, dict)
                and row.get("cost_reported") is True
                and isinstance(row.get("cost_micros"), int)
                and not isinstance(row.get("cost_micros"), bool)
                and 0 <= row["cost_micros"] <= MAX_SQLITE_INTEGER
                and _valid_fingerprint(row.get("response_id_fingerprint"))
                and _valid_fingerprint(row.get("usage_fingerprint"))
                for row in rows
            )
        )
        if (
            receipt.get("schema") != "quillframe_model_cost_receipt_v1"
            or receipt.get("status") != "provider_confirmed"
            or supplied != expected
            or receipt.get("model_requests") != requests
            or not isinstance(cost, int) or isinstance(cost, bool)
            or cost < 0 or cost > MAX_SQLITE_INTEGER
            or not valid_rows
            or sum(row["cost_micros"] for row in rows) != cost
            or not isinstance(usage.get("cost_micros"), int)
            or isinstance(usage.get("cost_micros"), bool)
            or usage.get("cost_micros") != cost
        ):
            return None
        return {
            "cost_micros": cost,
            "receipt_source": "provider_result",
            "evidence_ref": "agent_result_usage:" + supplied,
            "evidence_fingerprint": supplied,
        }

    @staticmethod
    def _insert_billing_receipt_locked(
        conn, *, call_id: str, run_id: str, result_fingerprint: str,
        cost_micros: int, receipt_source: str, evidence_ref: str,
        evidence_fingerprint: str,
    ) -> dict[str, Any]:  # noqa: ANN001
        payload = _billing_record_payload(
            call_id=call_id,
            run_id=run_id,
            result_fingerprint=result_fingerprint,
            cost_micros=cost_micros,
            receipt_source=receipt_source,
            evidence_ref=evidence_ref,
            evidence_fingerprint=evidence_fingerprint,
        )
        receipt_fp = _fingerprint(payload)
        conn.execute(
            "INSERT INTO production_billing_receipts("
            "call_id,run_id,result_fingerprint,cost_micros,receipt_source,evidence_ref,"
            "evidence_fingerprint,receipt_fingerprint,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                call_id, run_id, result_fingerprint, cost_micros, receipt_source,
                evidence_ref, evidence_fingerprint, receipt_fp, now_iso(),
            ),
        )
        return {**payload, "receipt_fingerprint": receipt_fp}

    @staticmethod
    def _billing_summary_locked(conn, run_id: str) -> dict[str, Any]:  # noqa: ANN001
        rows = conn.execute(
            "SELECT c.call_id,c.result_fingerprint,c.result_json,b.run_id AS billing_run_id,"
            "b.result_fingerprint AS billing_result_fingerprint,b.cost_micros,"
            "b.receipt_source,b.evidence_ref,b.evidence_fingerprint,b.receipt_fingerprint "
            "FROM production_stage_calls c LEFT JOIN production_billing_receipts b "
            "ON b.call_id=c.call_id WHERE c.run_id=? AND c.state='confirmed' ORDER BY c.rowid",
            (run_id,),
        ).fetchall()
        total = 0
        missing: list[str] = []
        for row in rows:
            if row["receipt_fingerprint"] is None:
                missing.append(str(row["call_id"]))
                continue
            payload = _billing_record_payload(
                call_id=str(row["call_id"]),
                run_id=run_id,
                result_fingerprint=str(row["result_fingerprint"]),
                cost_micros=int(row["cost_micros"]),
                receipt_source=str(row["receipt_source"]),
                evidence_ref=str(row["evidence_ref"]),
                evidence_fingerprint=str(row["evidence_fingerprint"]),
            )
            if (
                not _valid_fingerprint(row["result_fingerprint"])
                or not _valid_fingerprint(row["evidence_fingerprint"])
                or row["billing_run_id"] != run_id
                or row["billing_result_fingerprint"] != row["result_fingerprint"]
                or row["receipt_fingerprint"] != _fingerprint(payload)
            ):
                raise ProductionStageError(
                    "billing_receipt_corrupt", "stored production billing receipt changed"
                )
            total += int(row["cost_micros"])
        return {"observed_cost_micros": total, "reconciliation_call_ids": missing}

    @staticmethod
    def _node_checkpoint_locked(conn, row) -> dict[str, Any]:  # noqa: ANN001
        checkpoint_row = conn.execute(
            "SELECT state_json,artifact_fingerprint FROM checkpoints "
            "WHERE checkpoint_id=? AND run_id=? AND checkpoint_kind='production_node_checkpoint'",
            ("node:" + row["call_id"], row["run_id"]),
        ).fetchone()
        if checkpoint_row is None:
            raise ProductionStageError(
                "node_checkpoint_missing",
                "confirmed stage has no atomic node checkpoint",
                detail={"call_id": row["call_id"], "stage_key": row["stage_key"]},
            )
        try:
            checkpoint = json.loads(checkpoint_row["state_json"])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProductionStageError("node_checkpoint_corrupt", "node checkpoint JSON is invalid") from exc
        supplied = checkpoint.get("checkpoint_fingerprint") if isinstance(checkpoint, dict) else None
        expected = _fingerprint({key: value for key, value in checkpoint.items() if key != "checkpoint_fingerprint"}) if isinstance(checkpoint, dict) else None
        expected_core = _fingerprint(_checkpoint_core_payload(checkpoint)) if isinstance(checkpoint, dict) else None
        if (
            not isinstance(checkpoint, dict)
            or checkpoint.get("schema") != "quillframe_production_node_checkpoint_v1"
            or supplied != expected
            or checkpoint_row["artifact_fingerprint"] != supplied
            or checkpoint.get("run_id") != row["run_id"]
            or checkpoint.get("node_id") != row["stage_key"]
            or checkpoint.get("call_id") != row["call_id"]
            or checkpoint.get("input_fingerprint") != row["input_fingerprint"]
            or checkpoint.get("output_fingerprint") != row["result_fingerprint"]
            or checkpoint.get("checkpoint_core_fingerprint") != expected_core
        ):
            raise ProductionStageError(
                "node_checkpoint_corrupt", "confirmed node checkpoint binding changed"
            )
        return checkpoint

    @staticmethod
    def _checkpoint_allowed_for_request_locked(
        conn, row, checkpoint: dict[str, Any], current_request_fingerprint: str,
    ) -> None:  # noqa: ANN001
        historical_request = checkpoint.get("execution_request_fingerprint")
        if historical_request == current_request_fingerprint:
            return
        migration = conn.execute(
            "SELECT * FROM production_build_migrations WHERE run_id=? "
            "AND to_request_fingerprint=? ORDER BY rowid DESC LIMIT 1",
            (row["run_id"], current_request_fingerprint),
        ).fetchone()
        if migration is None:
            raise ProductionStageError(
                "checkpoint_build_migration_missing",
                "historical checkpoint is not authorized for the current Framework request",
            )
        receipt_row = conn.execute(
            "SELECT * FROM production_verified_regression_receipts WHERE receipt_id=?",
            (migration["regression_receipt_id"],),
        ).fetchone()
        try:
            receipt = json.loads(receipt_row["receipt_json"]) if receipt_row is not None else None
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProductionStageError(
                "checkpoint_build_migration_corrupt", "migration regression receipt is invalid"
            ) from exc
        supplied = receipt.get("receipt_fingerprint") if isinstance(receipt, dict) else None
        expected = _fingerprint({
            key: value for key, value in receipt.items() if key != "receipt_fingerprint"
        }) if isinstance(receipt, dict) else None
        try:
            authorized_checkpoints = json.loads(
                migration["confirmed_checkpoint_core_fingerprints_json"]
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProductionStageError(
                "checkpoint_build_migration_corrupt", "migration checkpoint identities are invalid"
            ) from exc
        migration_payload = _build_migration_payload(
            migration_id=str(migration["migration_id"]),
            run_id=str(migration["run_id"]),
            from_request_fingerprint=str(migration["from_request_fingerprint"]),
            to_request_fingerprint=str(migration["to_request_fingerprint"]),
            from_build_fingerprint=str(migration["from_build_fingerprint"]),
            to_build_fingerprint=str(migration["to_build_fingerprint"]),
            regression_receipt_id=str(migration["regression_receipt_id"]),
            regression_receipt_fingerprint=str(migration["regression_receipt_fingerprint"]),
            confirmed_checkpoint_core_fingerprints=authorized_checkpoints,
            prior_run_status=str(migration["prior_run_status"]),
            from_request_version=int(migration["from_request_version"]),
            to_request_version=int(migration["to_request_version"]),
            authorization_ref=str(migration["authorization_ref"]),
        )
        if (
            not isinstance(receipt, dict)
            or supplied != expected
            or receipt_row is None
            or receipt_row["receipt_fingerprint"] != supplied
            or receipt_row["preview_fingerprint"] != receipt.get("preview_fingerprint")
            or migration["regression_receipt_fingerprint"] != supplied
            or migration["migration_fingerprint"] != _fingerprint(migration_payload)
            or receipt.get("status") != "passed"
            or not isinstance(authorized_checkpoints, list)
            or checkpoint.get("checkpoint_core_fingerprint") not in authorized_checkpoints
        ):
            raise ProductionStageError(
                "checkpoint_build_migration_corrupt",
                "migration no longer binds this exact confirmed checkpoint",
            )

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
        # Expiry makes the lease available for atomic takeover; it does not by
        # itself erase the recorded owner. If no takeover occurred, that exact
        # owner may still durably confirm a response that already returned.
        if not row or row["owner_token"] != owner_token:
            raise ProductionStageError("execution_lease_lost", "production execution no longer owns its write lease")

    def acquire(self, project_id: str, run_id: str, request: dict[str, Any]) -> str:
        budget = request.get("max_model_calls")
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1 or budget > 64:
            raise ProductionStageError("invalid_model_call_budget", "max_model_calls must be an integer from 1 to 64")
        cost_budget = request.get("run_cost_budget")
        if not isinstance(cost_budget, int) or isinstance(cost_budget, bool) or cost_budget < 1:
            raise ProductionStageError("invalid_run_cost_budget", "run_cost_budget must be a positive integer in micros")
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
                    "WHERE run_id=? AND state='dispatched' "
                    "AND COALESCE(error_code,'') NOT IN ('idempotent_model_request','model_pending')",
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
                    "WHERE run_id=? AND owner_token=? AND state='dispatched' "
                    "AND COALESCE(error_code,'') NOT IN ('idempotent_model_request','model_pending')",
                    (now_iso(), run_id, owner_token),
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
                if prior["state"] == "dispatched" and prior["error_code"] in POLLABLE_ERROR_CODES:
                    conn.execute(
                        "UPDATE production_stage_calls SET owner_token=?,updated_at=? "
                        "WHERE call_id=? AND state='dispatched' "
                        "AND error_code IN ('idempotent_model_request','model_pending')",
                        (owner_token, now_iso(), prior["call_id"]),
                    )
                    conn.commit()
                    return {
                        "call_id": prior["call_id"], "replayed": False,
                        "pending": True, "deadline_at_ms": prior["deadline_at_ms"],
                    }
                if prior["state"] != "confirmed":
                    raise ProductionStageError("stage_result_unconfirmed", "external stage result is not confirmed", detail={
                        "call_id": prior["call_id"], "stage_key": stage_key, "state": prior["state"],
                    })
                result = json.loads(prior["result_json"])
                if _fingerprint(result) != prior["result_fingerprint"]:
                    raise ProductionStageError("stage_result_corrupt", "confirmed stage result fingerprint does not match")
                checkpoint = self._node_checkpoint_locked(conn, prior)
                execution = conn.execute(
                    "SELECT request_fingerprint FROM production_executions WHERE run_id=?",
                    (run_id,),
                ).fetchone()
                self._checkpoint_allowed_for_request_locked(
                    conn, prior, checkpoint, str(execution["request_fingerprint"])
                )
                conn.commit()
                return {"call_id": prior["call_id"], "replayed": True, "pending": False, "result": result}
            pending = conn.execute(
                "SELECT call_id,stage_key,state FROM production_stage_calls WHERE run_id=? "
                "AND state IN ('dispatched','unconfirmed') LIMIT 1",
                (run_id,),
            ).fetchone()
            if pending:
                raise ProductionStageError("stage_result_unconfirmed", "another external stage has an unconfirmed result", detail=dict(pending))
            execution = conn.execute("SELECT request_json FROM production_executions WHERE run_id=?", (run_id,)).fetchone()
            frozen_request = json.loads(execution["request_json"])
            limit = frozen_request["max_model_calls"]
            calls = conn.execute("SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?", (run_id,)).fetchone()[0]
            if calls >= limit:
                raise ProductionStageError("model_call_budget_exhausted", "frozen production model-call budget is exhausted", detail={
                    "dispatched_call_count": calls, "max_model_calls": limit,
                })
            billing = self._billing_summary_locked(conn, run_id)
            if billing["reconciliation_call_ids"]:
                raise ProductionStageError(
                    "billing_reconciliation_required",
                    "a confirmed model result has no authoritative cost receipt",
                    detail={"call_ids": billing["reconciliation_call_ids"]},
                )
            observed_cost = billing["observed_cost_micros"]
            if observed_cost >= frozen_request["run_cost_budget"]:
                raise ProductionStageError(
                    "run_cost_budget_exhausted",
                    "frozen production cost budget is exhausted before dispatch",
                    detail={"observed_cost_micros": observed_cost,
                            "run_cost_budget": frozen_request["run_cost_budget"]},
                )
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
            return {"call_id": call_id, "replayed": False, "pending": False, "deadline_at_ms": deadline}

    def remaining_cost_budget(self, project_id: str, run_id: str) -> int:
        with self.store.open_project(project_id) as conn:
            execution = conn.execute(
                "SELECT request_json FROM production_executions WHERE run_id=?", (run_id,)
            ).fetchone()
            if not execution:
                raise ProductionStageError("execution_request_missing", "no production execute request has been frozen")
            budget = json.loads(execution["request_json"])["run_cost_budget"]
            billing = self._billing_summary_locked(conn, run_id)
        if billing["reconciliation_call_ids"]:
            raise ProductionStageError(
                "billing_reconciliation_required",
                "a confirmed model result has no authoritative cost receipt",
                detail={"call_ids": billing["reconciliation_call_ids"]},
            )
        return max(0, budget - billing["observed_cost_micros"])

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
            # The deadline bounds waiter admission, never validity. Once an
            # exact result has returned for the frozen intent, persist it even
            # if the HTTP waiter or stage soft deadline elapsed meanwhile.
            conn.execute(
                "UPDATE production_stage_calls SET state='confirmed',result_json=?,result_fingerprint=?,error_code=NULL,updated_at=? WHERE call_id=?",
                (result_json, result_fp, now_iso(), call_id),
            )
            billing_evidence = self._result_billing_evidence(result, result_fp)
            billing_record = None
            if billing_evidence is not None:
                billing_record = self._insert_billing_receipt_locked(
                    conn,
                    call_id=call_id,
                    run_id=run_id,
                    result_fingerprint=result_fp,
                    **billing_evidence,
                )
            execution = conn.execute(
                "SELECT request_fingerprint,request_json FROM production_executions WHERE run_id=?", (run_id,)
            ).fetchone()
            request = json.loads(execution["request_json"])
            registered = ((job.get("context") or [{}])[0].get("registered_semantic_job")
                          if isinstance((job.get("context") or [{}])[0], dict) else None)
            provenance = registered.get("provenance") if isinstance(registered, dict) else {}
            contract_input = registered.get("input") if isinstance(registered, dict) else {}
            checkpoint = {
                "schema": "quillframe_production_node_checkpoint_v1",
                "run_id": run_id,
                "node_id": row["stage_key"],
                "call_id": call_id,
                "runtime_role": row["runtime_role"],
                "framework_build_fingerprint": (request.get("framework_build") or {}).get("build_fingerprint"),
                "execution_request_fingerprint": execution["request_fingerprint"],
                "input_fingerprint": row["input_fingerprint"],
                "output_fingerprint": result_fp,
                "prompt_binding": {
                    "instruction_fingerprint": _fingerprint(job.get("instruction")),
                    "output_schema_fingerprint": _fingerprint(job.get("output_schema")) if job.get("output_schema") is not None else None,
                    "model_contract_id": contract_input.get("model_contract_id") if isinstance(contract_input, dict) else None,
                    "registry_schema": provenance.get("registry_schema") if isinstance(provenance, dict) else None,
                    "registry_version": provenance.get("registry_version") if isinstance(provenance, dict) else None,
                    "pack_id": provenance.get("pack_id") if isinstance(provenance, dict) else None,
                },
                "upstream_dependencies": _fingerprint_dependencies(job.get("context", [])),
                "model_request": {
                    "idempotency_key": job.get("idempotency_key"),
                    "service_id": result.get("model_service_id"),
                    "model_id": result.get("model_id"),
                    "model_version_fingerprint": result.get("model_version_fingerprint"),
                    "model_version_identity_strength": result.get(
                        "model_version_identity_strength"
                    ),
                    "protocol": result.get("protocol"),
                },
                "validation_receipt": {
                    "status": "transport_and_agent_contract_confirmed",
                    "exact_job_binding": True,
                    "native_output_schema_requested": job.get("output_schema") is not None,
                    "semantic_revalidation_on_resume_required": True,
                },
                "billing_receipt": {
                    "charged_call_id": call_id,
                    "model_requests": result.get("model_requests"),
                    "status": (
                        "confirmed" if billing_record is not None else "reconciliation_required"
                    ),
                    "cost_micros": billing_record.get("cost_micros") if billing_record else None,
                    "receipt_source": billing_record.get("receipt_source") if billing_record else None,
                    "receipt_fingerprint": billing_record.get("receipt_fingerprint") if billing_record else None,
                    "replay_may_charge": False,
                },
                "authority": False,
            }
            checkpoint["checkpoint_core_fingerprint"] = _fingerprint(
                _checkpoint_core_payload(checkpoint)
            )
            checkpoint["checkpoint_fingerprint"] = _fingerprint(checkpoint)
            prior_checkpoint = conn.execute(
                "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE checkpoint_id=?",
                ("node:" + call_id,),
            ).fetchone()
            checkpoint_json = canonical_json(checkpoint)
            if prior_checkpoint:
                if (prior_checkpoint["state_json"] != checkpoint_json
                        or prior_checkpoint["artifact_fingerprint"] != checkpoint["checkpoint_fingerprint"]):
                    raise ProductionStageError("node_checkpoint_conflict", "confirmed node checkpoint changed")
            else:
                conn.execute(
                    "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) "
                    "VALUES(?,?,'production_node_checkpoint',?,?,?)",
                    ("node:" + call_id, run_id, checkpoint_json, checkpoint["checkpoint_fingerprint"], now_iso()),
                )
            self._event_locked(conn, run_id, "production_stage_result_confirmed", {
                "call_id": call_id, "stage_key": row["stage_key"], "input_fingerprint": row["input_fingerprint"],
                "result_fingerprint": result_fp, "agent_status": result.get("status"), "authority": False,
            })
            conn.execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) "
                "VALUES(?,?,'production_run_wake_requested',?,?) ON CONFLICT(event_id) DO NOTHING",
                ("evt_wake_" + call_id, run_id, canonical_json({
                    "call_id": call_id, "stage_key": row["stage_key"],
                    "checkpoint_fingerprint": checkpoint["checkpoint_fingerprint"], "authority": False,
                }), now_iso()),
            )
            conn.commit()

    def confirm_node_validation(
        self,
        project_id: str,
        run_id: str,
        owner_token: str,
        *,
        stage_key: str,
        input_fingerprint: str,
        validation_kind: str,
        validation_fingerprint: str,
    ) -> dict[str, Any]:
        """Attach final semantic/stage validation to the atomic node boundary."""

        if not isinstance(validation_kind, str) or not validation_kind.strip():
            raise ProductionStageError("node_validation_invalid", "validation kind is required")
        if (
            not isinstance(validation_fingerprint, str)
            or len(validation_fingerprint) != 71
            or not validation_fingerprint.startswith("sha256:")
        ):
            raise ProductionStageError(
                "node_validation_invalid", "validation fingerprint must be sha256:<64 hex>"
            )
        try:
            int(validation_fingerprint[7:], 16)
        except ValueError as exc:
            raise ProductionStageError(
                "node_validation_invalid", "validation fingerprint must be sha256:<64 hex>"
            ) from exc
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.guard_locked(conn, run_id, owner_token)
            row = conn.execute(
                "SELECT * FROM production_stage_calls WHERE run_id=? AND stage_key=?",
                (run_id, stage_key),
            ).fetchone()
            if (
                row is None
                or row["state"] != "confirmed"
                or row["input_fingerprint"] != input_fingerprint
            ):
                raise ProductionStageError(
                    "node_validation_invalid", "validation does not bind a confirmed exact stage"
                )
            checkpoint = self._node_checkpoint_locked(conn, row)
            existing = checkpoint.get("validation_receipt", {})
            completed = {
                "status": "semantic_validation_confirmed",
                "exact_job_binding": True,
                "native_output_schema_requested": existing.get(
                    "native_output_schema_requested", False
                ),
                "validation_kind": validation_kind,
                "validation_fingerprint": validation_fingerprint,
                "semantic_revalidation_on_resume_required": True,
            }
            if existing.get("status") == "semantic_validation_confirmed" and existing != completed:
                raise ProductionStageError(
                    "node_validation_conflict", "confirmed node validation cannot be replaced"
                )
            checkpoint["validation_receipt"] = completed
            checkpoint["checkpoint_fingerprint"] = _fingerprint(
                {key: value for key, value in checkpoint.items() if key != "checkpoint_fingerprint"}
            )
            checkpoint_json = canonical_json(checkpoint)
            conn.execute(
                "UPDATE checkpoints SET state_json=?,artifact_fingerprint=? WHERE checkpoint_id=?",
                (checkpoint_json, checkpoint["checkpoint_fingerprint"], "node:" + row["call_id"]),
            )
            conn.execute(
                "UPDATE runtime_events SET payload_json=? WHERE event_id=? "
                "AND event_kind='production_run_wake_requested'",
                (
                    canonical_json({
                        "call_id": row["call_id"],
                        "stage_key": stage_key,
                        "checkpoint_fingerprint": checkpoint["checkpoint_fingerprint"],
                        "authority": False,
                    }),
                    "evt_wake_" + row["call_id"],
                ),
            )
            conn.commit()
        return checkpoint

    def reconcile_billing_receipt(
        self,
        project_id: str,
        run_id: str,
        *,
        call_id: str,
        expected_result_fingerprint: str,
        cost_micros: int,
        evidence_ref: str,
        evidence_fingerprint: str,
    ) -> dict[str, Any]:
        """Bind an authorized external billing receipt without changing the result."""

        if (
            not isinstance(cost_micros, int)
            or isinstance(cost_micros, bool)
            or cost_micros < 0
            or cost_micros > MAX_SQLITE_INTEGER
            or not isinstance(evidence_ref, str)
            or not evidence_ref.strip()
            or not _valid_fingerprint(expected_result_fingerprint)
            or not _valid_fingerprint(evidence_fingerprint)
        ):
            raise ProductionStageError(
                "billing_reconciliation_invalid", "billing reconciliation fields are invalid"
            )
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            run = conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            execution = conn.execute(
                "SELECT owner_token,lease_expires_at_ms,cancel_requested "
                "FROM production_executions WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if execution is None or run is None:
                raise ProductionStageError(
                    "execution_request_missing", "no production execute request has been frozen"
                )
            cancelled = run["status"] == "cancelled" or bool(execution["cancel_requested"])
            if (
                not cancelled
                and execution["owner_token"]
                and (execution["lease_expires_at_ms"] or 0) > self._now_ms()
            ):
                raise ProductionStageError(
                    "run_in_progress", "billing cannot be reconciled while an executor is active"
                )
            row = conn.execute(
                "SELECT * FROM production_stage_calls WHERE run_id=? AND call_id=?",
                (run_id, call_id),
            ).fetchone()
            if (
                row is None
                or row["state"] != "confirmed"
                or row["result_fingerprint"] != expected_result_fingerprint
            ):
                raise ProductionStageError(
                    "billing_reconciliation_invalid",
                    "receipt does not bind the exact confirmed model result",
                )
            existing = conn.execute(
                "SELECT * FROM production_billing_receipts WHERE call_id=?", (call_id,)
            ).fetchone()
            if existing is not None:
                if (
                    existing["result_fingerprint"] != expected_result_fingerprint
                    or int(existing["cost_micros"]) != cost_micros
                    or existing["evidence_ref"] != evidence_ref
                    or existing["evidence_fingerprint"] != evidence_fingerprint
                ):
                    raise ProductionStageError(
                        "billing_reconciliation_conflict",
                        "a confirmed billing receipt cannot be replaced",
                    )
                conn.commit()
                return dict(existing)
            record = self._insert_billing_receipt_locked(
                conn,
                call_id=call_id,
                run_id=run_id,
                result_fingerprint=expected_result_fingerprint,
                cost_micros=cost_micros,
                receipt_source="authorized_reconciliation",
                evidence_ref=evidence_ref,
                evidence_fingerprint=evidence_fingerprint,
            )
            checkpoint = self._node_checkpoint_locked(conn, row)
            checkpoint["billing_receipt"] = {
                "charged_call_id": call_id,
                "model_requests": json.loads(row["result_json"]).get("model_requests"),
                "status": "confirmed",
                "cost_micros": cost_micros,
                "receipt_source": "authorized_reconciliation",
                "receipt_fingerprint": record["receipt_fingerprint"],
                "replay_may_charge": False,
            }
            checkpoint["checkpoint_fingerprint"] = _fingerprint(
                {key: value for key, value in checkpoint.items() if key != "checkpoint_fingerprint"}
            )
            conn.execute(
                "UPDATE checkpoints SET state_json=?,artifact_fingerprint=? WHERE checkpoint_id=?",
                (
                    canonical_json(checkpoint), checkpoint["checkpoint_fingerprint"],
                    "node:" + call_id,
                ),
            )
            self._event_locked(conn, run_id, "production_billing_reconciled", {
                "call_id": call_id,
                "result_fingerprint": expected_result_fingerprint,
                "cost_micros": cost_micros,
                "receipt_fingerprint": record["receipt_fingerprint"],
                "authority": False,
            })
            if not cancelled:
                wake_id = "evt_wake_" + call_id + "_billing_" + record["receipt_fingerprint"][7:23]
                conn.execute(
                    "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) "
                    "VALUES(?,?,'production_run_wake_requested',?,?) ON CONFLICT(event_id) DO NOTHING",
                    (
                        wake_id, run_id,
                        canonical_json({
                            "call_id": call_id,
                            "stage_key": row["stage_key"],
                            "checkpoint_fingerprint": checkpoint["checkpoint_fingerprint"],
                            "reason": "billing_reconciled",
                            "authority": False,
                        }),
                        now_iso(),
                    ),
                )
            conn.commit()
        return record

    def mark_framework_bug_blocked(
        self, project_id: str, run_id: str, owner_token: str, *,
        error_type: str, error_fingerprint: str,
    ) -> bool:
        """Stop only a cleanly checkpointed run after an internal Framework fault."""

        if not isinstance(error_type, str) or not error_type.strip() or not _valid_fingerprint(error_fingerprint):
            raise ProductionStageError("framework_bug_evidence_invalid", "Framework bug evidence is invalid")
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.guard_locked(conn, run_id, owner_token)
            run = conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            unresolved = conn.execute(
                "SELECT call_id FROM production_stage_calls WHERE run_id=? "
                "AND state IN ('dispatched','unconfirmed') ORDER BY rowid", (run_id,),
            ).fetchall()
            billing = self._billing_summary_locked(conn, run_id)
            eligible = (
                run is not None
                and run["status"] not in {"completed", "cancelled", "awaiting_external", "failed_gate", "budget_exhausted"}
                and not unresolved
                and not billing["reconciliation_call_ids"]
            )
            if eligible:
                conn.execute(
                    "UPDATE runs SET status='framework_bug_blocked',updated_at=? WHERE run_id=?",
                    (now_iso(), run_id),
                )
            self._event_locked(conn, run_id, "production_framework_bug_detected", {
                "error_type": error_type,
                "error_fingerprint": error_fingerprint,
                "checkpoint_clean": eligible,
                "unresolved_call_ids": [str(row["call_id"]) for row in unresolved],
                "billing_reconciliation_call_ids": billing["reconciliation_call_ids"],
                "authority": False,
            })
            conn.commit()
        return eligible

    def build_migration_preview(
        self, project_id: str, run_id: str, *, new_framework_build: dict[str, Any]
    ) -> dict[str, Any]:
        """Describe the immutable checkpoint cores an offline regression must cover."""

        if (
            not isinstance(new_framework_build, dict)
            or new_framework_build.get("schema") != "quillframe_framework_build_identity_v1"
            or not _valid_fingerprint(new_framework_build.get("build_fingerprint"))
        ):
            raise ProductionStageError("build_migration_invalid", "new Framework build identity is invalid")
        with self.store.open_project(project_id) as conn:
            execution = conn.execute(
                "SELECT * FROM production_executions WHERE run_id=?", (run_id,)
            ).fetchone()
            run = conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if execution is None or run is None:
                raise ProductionStageError("execution_request_missing", "no production execute request has been frozen")
            if run["status"] != "framework_bug_blocked":
                raise ProductionStageError(
                    "build_migration_not_framework_bug",
                    "only an explicitly Framework-bug-blocked run can migrate builds",
                )
            if execution["owner_token"] and (execution["lease_expires_at_ms"] or 0) > self._now_ms():
                raise ProductionStageError("run_in_progress", "Framework build cannot migrate while an executor is active")
            request = json.loads(execution["request_json"])
            if _fingerprint(request) != execution["request_fingerprint"]:
                raise ProductionStageError("execution_request_corrupt", "frozen execute request fingerprint does not match")
            old_build = request.get("framework_build")
            if not isinstance(old_build, dict) or not _valid_fingerprint(old_build.get("build_fingerprint")):
                raise ProductionStageError("build_migration_invalid", "frozen Framework build identity is invalid")
            unresolved = conn.execute(
                "SELECT call_id FROM production_stage_calls WHERE run_id=? "
                "AND state IN ('dispatched','unconfirmed') ORDER BY rowid", (run_id,),
            ).fetchall()
            if unresolved:
                raise ProductionStageError(
                    "build_migration_unconfirmed_stage",
                    "all dispatched stages must be exactly confirmed before migration",
                    detail={"call_ids": [str(row["call_id"]) for row in unresolved]},
                )
            billing = self._billing_summary_locked(conn, run_id)
            if billing["reconciliation_call_ids"]:
                raise ProductionStageError(
                    "billing_reconciliation_required", "billing must be reconciled before a build migration",
                    detail={"call_ids": billing["reconciliation_call_ids"]},
                )
            checkpoint_rows = conn.execute(
                "SELECT * FROM production_stage_calls WHERE run_id=? AND state='confirmed' ORDER BY rowid",
                (run_id,),
            ).fetchall()
            checkpoint_cores = sorted(
                self._node_checkpoint_locked(conn, row)["checkpoint_core_fingerprint"]
                for row in checkpoint_rows
            )
            from_request_fingerprint = str(execution["request_fingerprint"])
        new_request = {**request, "framework_build": new_framework_build}
        preview = {
            "schema": "quillframe_framework_build_migration_preview_v2",
            "run_id": run_id,
            "from_request_fingerprint": from_request_fingerprint,
            "to_request_fingerprint": _fingerprint(new_request),
            "from_build_fingerprint": str(old_build["build_fingerprint"]),
            "to_build_fingerprint": str(new_framework_build["build_fingerprint"]),
            "confirmed_checkpoint_core_fingerprints": checkpoint_cores,
            "required_compatibility": "exact_input_output_checkpoint_core_replay_only",
            "authority": False,
        }
        preview["preview_fingerprint"] = _fingerprint(preview)
        return preview

    def _record_offline_regression_receipt(
        self, project_id: str, run_id: str, *, new_framework_build: dict[str, Any],
        test_command_fingerprint: str, test_output_fingerprint: str,
        test_evidence_fingerprints: list[str],
    ) -> dict[str, Any]:
        """Persist evidence emitted by the fixed offline regression runner."""

        if (
            not _valid_fingerprint(test_command_fingerprint)
            or not _valid_fingerprint(test_output_fingerprint)
            or not isinstance(test_evidence_fingerprints, list)
            or not test_evidence_fingerprints
            or len(test_evidence_fingerprints) != len(set(test_evidence_fingerprints))
            or any(not _valid_fingerprint(value) for value in test_evidence_fingerprints)
        ):
            raise ProductionStageError("build_migration_regression_invalid", "offline regression evidence is invalid")
        preview = self.build_migration_preview(project_id, run_id, new_framework_build=new_framework_build)
        receipt_id = "buildreg_" + uuid.uuid4().hex
        receipt = {
            "schema": "quillframe_framework_migration_regression_v2",
            "receipt_id": receipt_id,
            "run_id": run_id,
            "preview_fingerprint": preview["preview_fingerprint"],
            "status": "passed",
            "runner_kind": "quillframe_offline_regression_runner",
            "from_request_fingerprint": preview["from_request_fingerprint"],
            "to_request_fingerprint": preview["to_request_fingerprint"],
            "from_build_fingerprint": preview["from_build_fingerprint"],
            "to_build_fingerprint": preview["to_build_fingerprint"],
            "confirmed_checkpoint_core_fingerprints": preview["confirmed_checkpoint_core_fingerprints"],
            "test_evidence_fingerprints": test_evidence_fingerprints,
            "test_command_fingerprint": test_command_fingerprint,
            "test_output_fingerprint": test_output_fingerprint,
            "authority": False,
        }
        receipt["receipt_fingerprint"] = _fingerprint(receipt)
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO production_verified_regression_receipts("
                "receipt_id,run_id,preview_fingerprint,from_request_fingerprint,to_request_fingerprint,"
                "from_build_fingerprint,to_build_fingerprint,confirmed_checkpoint_core_fingerprints_json,"
                "test_evidence_fingerprints_json,test_command_fingerprint,test_output_fingerprint,"
                "runner_kind,status,receipt_json,receipt_fingerprint,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    receipt_id, run_id, preview["preview_fingerprint"], preview["from_request_fingerprint"],
                    preview["to_request_fingerprint"], preview["from_build_fingerprint"],
                    preview["to_build_fingerprint"], canonical_json(preview["confirmed_checkpoint_core_fingerprints"]),
                    canonical_json(test_evidence_fingerprints), test_command_fingerprint,
                    test_output_fingerprint, "quillframe_offline_regression_runner", "passed",
                    canonical_json(receipt), receipt["receipt_fingerprint"], now_iso(),
                ),
            )
            conn.commit()
        return receipt

    def migrate_framework_build(
        self, project_id: str, run_id: str, *, expected_request_fingerprint: str,
        new_framework_build: dict[str, Any], regression_receipt_id: str,
        authorization_ref: str,
    ) -> dict[str, Any]:
        """Atomically activate a tested build while retaining every request version."""

        if (
            not _valid_fingerprint(expected_request_fingerprint)
            or not isinstance(regression_receipt_id, str) or not regression_receipt_id.startswith("buildreg_")
            or not isinstance(authorization_ref, str) or not authorization_ref.strip()
        ):
            raise ProductionStageError("build_migration_invalid", "migration authorization fields are invalid")
        preview = self.build_migration_preview(project_id, run_id, new_framework_build=new_framework_build)
        if expected_request_fingerprint != preview["from_request_fingerprint"]:
            raise ProductionStageError("build_migration_conflict", "frozen execution request changed after preview")
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            execution = conn.execute("SELECT * FROM production_executions WHERE run_id=?", (run_id,)).fetchone()
            run = conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if (
                execution is None or run is None
                or execution["request_fingerprint"] != expected_request_fingerprint
                or run["status"] != "framework_bug_blocked"
            ):
                raise ProductionStageError("build_migration_conflict", "run is no longer the exact blocked migration source")
            if execution["owner_token"] and (execution["lease_expires_at_ms"] or 0) > self._now_ms():
                raise ProductionStageError("run_in_progress", "Framework build cannot migrate while an executor is active")
            unresolved = conn.execute(
                "SELECT call_id FROM production_stage_calls WHERE run_id=? AND state IN ('dispatched','unconfirmed') LIMIT 1",
                (run_id,),
            ).fetchone()
            billing = self._billing_summary_locked(conn, run_id)
            checkpoint_rows = conn.execute(
                "SELECT * FROM production_stage_calls WHERE run_id=? AND state='confirmed' ORDER BY rowid", (run_id,),
            ).fetchall()
            checkpoint_cores = sorted(
                self._node_checkpoint_locked(conn, row)["checkpoint_core_fingerprint"]
                for row in checkpoint_rows
            )
            if unresolved is not None or billing["reconciliation_call_ids"] or checkpoint_cores != preview["confirmed_checkpoint_core_fingerprints"]:
                raise ProductionStageError("build_migration_conflict", "stage, billing, or checkpoint core changed after preview")
            receipt_row = conn.execute(
                "SELECT * FROM production_verified_regression_receipts WHERE receipt_id=? AND run_id=?",
                (regression_receipt_id, run_id),
            ).fetchone()
            try:
                receipt = json.loads(receipt_row["receipt_json"]) if receipt_row is not None else None
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ProductionStageError("build_migration_regression_invalid", "stored regression receipt is invalid") from exc
            supplied = receipt.get("receipt_fingerprint") if isinstance(receipt, dict) else None
            expected_receipt = _fingerprint({key: value for key, value in receipt.items() if key != "receipt_fingerprint"}) if isinstance(receipt, dict) else None
            if (
                receipt_row is None or not isinstance(receipt, dict)
                or supplied != expected_receipt or receipt_row["receipt_fingerprint"] != supplied
                or receipt.get("schema") != "quillframe_framework_migration_regression_v2"
                or receipt.get("runner_kind") != "quillframe_offline_regression_runner"
                or receipt.get("status") != "passed"
                or receipt.get("preview_fingerprint") != preview["preview_fingerprint"]
                or receipt.get("confirmed_checkpoint_core_fingerprints") != checkpoint_cores
                or any(receipt.get(key) != preview[key] for key in (
                    "from_request_fingerprint", "to_request_fingerprint",
                    "from_build_fingerprint", "to_build_fingerprint",
                ))
                or not _valid_fingerprint(receipt.get("test_command_fingerprint"))
                or not _valid_fingerprint(receipt.get("test_output_fingerprint"))
                or not isinstance(receipt.get("test_evidence_fingerprints"), list)
                or not receipt["test_evidence_fingerprints"]
            ):
                raise ProductionStageError(
                    "build_migration_regression_invalid",
                    "only a persisted exact offline regression receipt can authorize migration",
                )
            request = json.loads(execution["request_json"])
            if _fingerprint(request) != expected_request_fingerprint:
                raise ProductionStageError("execution_request_corrupt", "frozen execute request fingerprint does not match")
            old_build = request.get("framework_build") or {}
            request["framework_build"] = new_framework_build
            if _fingerprint(request) != preview["to_request_fingerprint"]:
                raise ProductionStageError("build_migration_conflict", "migration target changed after preview")
            versions = conn.execute(
                "SELECT * FROM production_execution_request_versions WHERE run_id=? ORDER BY version", (run_id,),
            ).fetchall()
            if not versions:
                from_version = 1
                conn.execute(
                    "INSERT INTO production_execution_request_versions("
                    "run_id,version,request_fingerprint,request_json,framework_build_fingerprint,"
                    "run_status_at_activation,activation_kind,migration_id,created_at) VALUES(?,?,?,?,?,?, 'initial',NULL,?)",
                    (run_id, 1, expected_request_fingerprint, execution["request_json"],
                     old_build.get("build_fingerprint"), "framework_bug_blocked", execution["created_at"]),
                )
            else:
                last = versions[-1]
                if last["request_fingerprint"] != expected_request_fingerprint or last["request_json"] != execution["request_json"]:
                    raise ProductionStageError("build_migration_history_corrupt", "active request no longer matches append-only history")
                from_version = int(last["version"])
            to_version = from_version + 1
            migration_id = "buildmig_" + uuid.uuid4().hex
            migration_payload = _build_migration_payload(
                migration_id=migration_id, run_id=run_id,
                from_request_fingerprint=preview["from_request_fingerprint"],
                to_request_fingerprint=preview["to_request_fingerprint"],
                from_build_fingerprint=preview["from_build_fingerprint"],
                to_build_fingerprint=preview["to_build_fingerprint"],
                regression_receipt_id=regression_receipt_id,
                regression_receipt_fingerprint=supplied,
                confirmed_checkpoint_core_fingerprints=checkpoint_cores,
                prior_run_status="framework_bug_blocked",
                from_request_version=from_version, to_request_version=to_version,
                authorization_ref=authorization_ref,
            )
            migration_fp = _fingerprint(migration_payload)
            conn.execute(
                "INSERT INTO production_build_migrations("
                "migration_id,run_id,from_request_fingerprint,to_request_fingerprint,from_build_fingerprint,"
                "to_build_fingerprint,regression_receipt_id,regression_receipt_fingerprint,"
                "confirmed_checkpoint_core_fingerprints_json,prior_run_status,from_request_version,"
                "to_request_version,authorization_ref,migration_fingerprint,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (migration_id, run_id, preview["from_request_fingerprint"], preview["to_request_fingerprint"],
                 preview["from_build_fingerprint"], preview["to_build_fingerprint"], regression_receipt_id,
                 supplied, canonical_json(checkpoint_cores), "framework_bug_blocked", from_version,
                 to_version, authorization_ref, migration_fp, now_iso()),
            )
            conn.execute(
                "INSERT INTO production_execution_request_versions("
                "run_id,version,request_fingerprint,request_json,framework_build_fingerprint,"
                "run_status_at_activation,activation_kind,migration_id,created_at) VALUES(?,?,?,?,?,?, 'framework_migration',?,?)",
                (run_id, to_version, preview["to_request_fingerprint"], canonical_json(request),
                 new_framework_build["build_fingerprint"], "semantic_pending", migration_id, now_iso()),
            )
            conn.execute(
                "UPDATE production_executions SET request_json=?,request_fingerprint=?,owner_token=NULL,"
                "lease_expires_at_ms=NULL,updated_at=? WHERE run_id=?",
                (canonical_json(request), preview["to_request_fingerprint"], now_iso(), run_id),
            )
            conn.execute("UPDATE runs SET status='semantic_pending',updated_at=? WHERE run_id=?", (now_iso(), run_id))
            self._event_locked(conn, run_id, "production_framework_build_migrated", {
                "migration_id": migration_id, "migration_fingerprint": migration_fp,
                "from_build_fingerprint": preview["from_build_fingerprint"],
                "to_build_fingerprint": preview["to_build_fingerprint"],
                "regression_receipt_id": regression_receipt_id,
                "regression_receipt_fingerprint": supplied,
                "from_request_version": from_version, "to_request_version": to_version,
                "authority": False,
            })
            conn.execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) "
                "VALUES(?,?,'production_run_wake_requested',?,?)",
                ("evt_wake_migration_" + migration_id, run_id, canonical_json({
                    "call_id": None, "migration_id": migration_id,
                    "migration_fingerprint": migration_fp, "reason": "framework_build_migrated",
                    "authority": False,
                }), now_iso()),
            )
            conn.commit()
        return {**migration_payload, "migration_fingerprint": migration_fp}

    def execution_request_versions(self, project_id: str, run_id: str) -> list[dict[str, Any]]:
        """Return verified immutable request versions for audit and rollback planning."""

        with self.store.open_project(project_id) as conn:
            rows = conn.execute(
                "SELECT * FROM production_execution_request_versions WHERE run_id=? ORDER BY version", (run_id,),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            request = json.loads(row["request_json"])
            if (
                _fingerprint(request) != row["request_fingerprint"]
                or (request.get("framework_build") or {}).get("build_fingerprint") != row["framework_build_fingerprint"]
            ):
                raise ProductionStageError("build_migration_history_corrupt", "stored request version changed")
            result.append({**dict(row), "request": request})
        return result

    def ready_runs(self, project_id: str, *, limit: int = 32) -> list[dict[str, Any]]:
        """Snapshot ready runs and only the wake IDs this attempt may consume."""
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 256:
            raise ValueError("limit must be an integer from 1 to 256")
        now = self._now_ms()
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN")
            rows = conn.execute(
                "SELECT DISTINCT r.run_id FROM runs r "
                "JOIN production_executions x ON x.run_id=r.run_id "
                "WHERE r.status NOT IN ('completed','cancelled','awaiting_external') "
                "AND (x.owner_token IS NULL OR COALESCE(x.lease_expires_at_ms,0)<=?) "
                "AND x.cancel_requested=0 AND ("
                "EXISTS (SELECT 1 FROM runtime_events w LEFT JOIN runtime_events c "
                "ON c.event_id='evt_wake_consumed_'||substr(w.event_id,10) "
                "WHERE w.run_id=r.run_id AND w.event_kind='production_run_wake_requested' AND c.event_id IS NULL) "
                "OR EXISTS (SELECT 1 FROM production_stage_calls s WHERE s.run_id=r.run_id "
                "AND s.state='dispatched' AND s.error_code IN ('idempotent_model_request','model_pending'))) "
                "ORDER BY r.updated_at,r.run_id LIMIT ?",
                (now, limit),
            ).fetchall()
            ready: list[dict[str, Any]] = []
            for row in rows:
                run_id = str(row["run_id"])
                wakes = conn.execute(
                    "SELECT w.event_id FROM runtime_events w LEFT JOIN runtime_events c "
                    "ON c.event_id='evt_wake_consumed_'||substr(w.event_id,10) "
                    "WHERE w.run_id=? AND w.event_kind='production_run_wake_requested' "
                    "AND c.event_id IS NULL ORDER BY w.rowid",
                    (run_id,),
                ).fetchall()
                ready.append({
                    "run_id": run_id,
                    "wake_event_ids": [str(wake["event_id"]) for wake in wakes],
                })
            conn.commit()
        return ready

    def ready_run_ids(self, project_id: str, *, limit: int = 32) -> list[str]:
        """Compatibility projection of :meth:`ready_runs`."""

        return [item["run_id"] for item in self.ready_runs(project_id, limit=limit)]

    def consume_wakes(
        self, project_id: str, run_id: str, *, wake_event_ids: list[str]
    ) -> None:
        """Acknowledge only wakes captured before this coordinator attempt."""

        if (
            not isinstance(wake_event_ids, list)
            or len(wake_event_ids) != len(set(wake_event_ids))
            or any(not isinstance(value, str) or not value.startswith("evt_wake_") for value in wake_event_ids)
        ):
            raise ValueError("wake_event_ids must be unique production wake event IDs")
        if not wake_event_ids:
            return
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            wakes = conn.execute(
                "SELECT event_id,payload_json FROM runtime_events WHERE run_id=? "
                "AND event_kind='production_run_wake_requested' AND event_id IN ({})".format(
                    ",".join("?" for _ in wake_event_ids)
                ),
                (run_id, *wake_event_ids),
            ).fetchall()
            if {str(wake["event_id"]) for wake in wakes} != set(wake_event_ids):
                conn.execute("ROLLBACK")
                raise ProductionStageError(
                    "wake_claim_invalid", "coordinator wake claim no longer binds exact events"
                )
            for wake in wakes:
                call_id = json.loads(wake["payload_json"])["call_id"]
                conn.execute(
                    "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) "
                    "VALUES(?,?,'production_run_wake_consumed',?,?) ON CONFLICT(event_id) DO NOTHING",
                    ("evt_wake_consumed_" + str(wake["event_id"])[len("evt_wake_"):], run_id,
                     canonical_json({"call_id": call_id, "authority": False}), now_iso()),
                )
            conn.commit()

    def mark_unconfirmed(self, project_id: str, run_id: str, owner_token: str, call_id: str, code: str) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute(
                "UPDATE production_stage_calls SET state='unconfirmed',error_code=?,updated_at=? "
                "WHERE run_id=? AND call_id=? AND owner_token=? AND state='dispatched'",
                (code, now_iso(), run_id, call_id, owner_token),
            )
            conn.commit()

    def mark_pending(self, project_id: str, run_id: str, owner_token: str, call_id: str) -> None:
        """Keep one charged intent pollable while its exact external worker continues."""
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.guard_locked(conn, run_id, owner_token)
            row = conn.execute(
                "SELECT state,owner_token FROM production_stage_calls WHERE run_id=? AND call_id=?",
                (run_id, call_id),
            ).fetchone()
            if not row or row["owner_token"] != owner_token or row["state"] != "dispatched":
                raise ProductionStageError("stage_call_owner_mismatch", "pending stage has no matching owned intent")
            conn.execute(
                "UPDATE production_stage_calls SET error_code='model_pending',updated_at=? "
                "WHERE call_id=? AND state='dispatched'",
                (now_iso(), call_id),
            )
            conn.commit()

    def mark_pollable(self, project_id: str, run_id: str, owner_token: str, call_id: str) -> None:
        """Persist the stable keyed intent before any loopback transport dispatch."""
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.guard_locked(conn, run_id, owner_token)
            row = conn.execute(
                "SELECT state,owner_token,error_code FROM production_stage_calls WHERE run_id=? AND call_id=?",
                (run_id, call_id),
            ).fetchone()
            if not row or row["owner_token"] != owner_token or row["state"] != "dispatched":
                raise ProductionStageError("stage_call_owner_mismatch", "pollable stage has no matching owned intent")
            if row["error_code"] not in {None, *POLLABLE_ERROR_CODES}:
                raise ProductionStageError("stage_result_unconfirmed", "stage intent is no longer safely pollable")
            conn.execute(
                "UPDATE production_stage_calls SET error_code=COALESCE(error_code,'idempotent_model_request'),updated_at=? "
                "WHERE call_id=? AND state='dispatched'",
                (now_iso(), call_id),
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
                "SELECT call_id,stage_key,runtime_role,input_fingerprint,state,deadline_at_ms,"
                "result_fingerprint,result_json,error_code,created_at,updated_at "
                "FROM production_stage_calls WHERE run_id=? ORDER BY rowid", (run_id,)
            ).fetchall()
            billing = self._billing_summary_locked(conn, run_id) if execution else {
                "observed_cost_micros": 0, "reconciliation_call_ids": [],
            }
        active = bool(execution and execution["owner_token"] and (execution["lease_expires_at_ms"] or 0) > self._now_ms())
        calls = [
            {key: value for key, value in dict(row).items() if key != "result_json"}
            for row in rows
        ]
        frozen_request = json.loads(execution["request_json"]) if execution else {}
        observed_cost = billing["observed_cost_micros"]
        billing_missing = billing["reconciliation_call_ids"]
        pending = [
            row["call_id"] for row in calls
            if row["state"] == "dispatched" and row["error_code"] in POLLABLE_ERROR_CODES
        ]
        hard_unconfirmed = [
            row["call_id"] for row in calls
            if row["state"] == "unconfirmed"
            or (row["state"] == "dispatched" and (
                row["error_code"] not in POLLABLE_ERROR_CODES
            ))
        ]
        unresolved = [row["call_id"] for row in calls if row["state"] in {"dispatched", "unconfirmed"}]
        return {
            "schema": JOURNAL_SCHEMA, "run_id": run_id,
            "request_fingerprint": execution["request_fingerprint"] if execution else None,
            "active_executor": active, "cancel_requested": bool(execution and execution["cancel_requested"]),
            "calls": calls, "unconfirmed_call_ids": unresolved,
            "hard_unconfirmed_call_ids": hard_unconfirmed, "pending_call_ids": pending,
            "confirmed_call_count": sum(row["state"] == "confirmed" for row in calls),
            "dispatched_call_count": len(calls),
            "model_call_budget": frozen_request.get("max_model_calls"),
            "run_cost_budget": frozen_request.get("run_cost_budget"),
            "observed_cost_micros": observed_cost,
            "remaining_cost_budget": (
                max(0, frozen_request.get("run_cost_budget", 0) - observed_cost)
                if execution and not billing_missing else None
            ),
            "billing_reconciliation_call_ids": billing_missing,
            "framework_build_fingerprint": (frozen_request.get("framework_build") or {}).get("build_fingerprint"),
            "safe_to_resume_confirmed_only": bool(
                execution and not active and not unresolved and not billing_missing
                and not execution["cancel_requested"]
            ),
            "safe_to_poll_pending": bool(execution and not active and pending and not hard_unconfirmed
                                          and not execution["cancel_requested"]),
            "private_payloads_visible": False, "authority": False,
        }
