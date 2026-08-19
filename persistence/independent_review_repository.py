"""Durable lease and cross-transport attempt ownership for independent review."""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from typing import Any

from .quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso

PROVIDER_TRANSPORT = {
    "codex_native_subagent": "codex_native",
    "claude_native_subagent": "claude_code_native",
}
DEPRECATED_PROVIDER_ALIASES = {
    "codex": "codex_native_subagent",
    "claude": "claude_native_subagent",
}
ASSURANCE_CLASS = "host_native_separate_context"
REVIEWER_AGENT_TYPE = "quillframe-independent-reviewer"
PROCESSING_LEASE_SECONDS = 30.0


class IndependentReviewError(RuntimeError):
    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IndependentReviewError("invalid_args", f"{name} is required")
    return value.strip()


def normalize_provider(value: Any) -> str:
    provider = _required(value, "provider")
    provider = DEPRECATED_PROVIDER_ALIASES.get(provider, provider)
    if provider not in PROVIDER_TRANSPORT:
        raise IndependentReviewError(
            "independent_provider_invalid",
            "provider must be codex_native_subagent|claude_native_subagent",
        )
    return provider


class IndependentReviewRepository:
    def __init__(
        self,
        store: QuillframeStore,
        *,
        clock: Callable[[], float] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        processing_lease_seconds: float = PROCESSING_LEASE_SECONDS,
    ) -> None:
        if processing_lease_seconds <= 0:
            raise ValueError("processing_lease_seconds must be positive")
        self.store = store
        self.clock = clock or time.time
        self.monotonic_clock = monotonic_clock or time.monotonic
        self.sleeper = sleeper or time.sleep
        self.processing_lease_seconds = processing_lease_seconds

    @staticmethod
    def _assert_project_identity_row(identity: Any, project_id: str) -> None:
        if not identity or identity["project_id"] != project_id:
            raise IndependentReviewError(
                "independent_project_mismatch",
                "runtime Project identity does not match the requested Project",
            )

    def assert_project_identity(self, project_id: str) -> None:
        with self.store.open_project(project_id) as conn:
            identity = conn.execute("SELECT project_id FROM project_identity").fetchone()
        self._assert_project_identity_row(identity, project_id)

    @staticmethod
    def _event(
        *,
        lease_id: str,
        run_id: str,
        event_kind: str,
        payload: dict[str, Any],
        event_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": event_id or "irevt_" + uuid.uuid4().hex,
            "lease_id": lease_id,
            "run_id": run_id,
            "event_kind": event_kind,
            "payload": payload,
            "created_at": created_at or now_iso(),
        }
        event["event_fingerprint"] = fingerprint_text(canonical_json(event))
        return event

    @staticmethod
    def _insert_event(conn, event: dict[str, Any]) -> None:  # noqa: ANN001
        conn.execute(
            "INSERT INTO independent_review_lifecycle_events(event_id,lease_id,run_id,event_kind,event_fingerprint,payload_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (
                event["event_id"],
                event["lease_id"],
                event["run_id"],
                event["event_kind"],
                event["event_fingerprint"],
                canonical_json(event["payload"]),
                event["created_at"],
            ),
        )

    def ensure_attempt(self, project_id: str, run_id: str, candidate_fingerprint: str) -> None:
        stamp = now_iso()
        with self.store.open_project(project_id) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO independent_review_attempts(run_id,candidate_fingerprint,status,created_at,updated_at) VALUES(?,?,'available',?,?)",
                (run_id, candidate_fingerprint, stamp, stamp),
            )
            conn.commit()

    def prepare(
        self,
        project_id: str,
        run_id: str,
        *,
        candidate_fingerprint: str,
        packet_bytes: str,
        job_id: str,
        input_fingerprint: str,
        relay_nonce: str,
        provider: str,
        parent_session_id: str,
    ) -> dict[str, Any]:
        provider = normalize_provider(provider)
        parent_session_id = _required(parent_session_id, "parent_session_id")
        packet_bytes = _required(packet_bytes, "packet_bytes")
        self.ensure_attempt(project_id, run_id, candidate_fingerprint)
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            identity = conn.execute("SELECT project_id FROM project_identity").fetchone()
            run = conn.execute("SELECT session_id,status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            self._assert_project_identity_row(identity, project_id)
            if not run:
                raise IndependentReviewError("run_not_found", run_id)
            if run["session_id"] != parent_session_id:
                raise IndependentReviewError("independent_parent_session_mismatch", "parent session does not own the production run")
            attempt = conn.execute(
                "SELECT status FROM independent_review_attempts WHERE run_id=? AND candidate_fingerprint=?",
                (run_id, candidate_fingerprint),
            ).fetchone()
            if attempt and attempt["status"] == "terminal":
                raise IndependentReviewError("independent_attempt_consumed", "independent review attempt is already terminal")
            if attempt and attempt["status"] == "processing":
                raise IndependentReviewError("independent_submission_in_progress", "independent review submission is processing")
            if run["status"] != "awaiting_external":
                raise IndependentReviewError(
                    "independent_submission_not_expected",
                    f"run status is {run['status']}, not awaiting_external",
                )
            active = conn.execute(
                "SELECT * FROM independent_review_leases WHERE run_id=? AND candidate_fingerprint=? AND status IN ('pending','claimed') ORDER BY created_at,rowid",
                (run_id, candidate_fingerprint),
            ).fetchall()
            if active:
                row = active[0]
                if row["provider"] == provider and row["parent_session_id"] == parent_session_id and row["status"] == "pending":
                    conn.commit()
                    return self._dispatch_projection(dict(row))
                raise IndependentReviewError("independent_native_lease_active", "a native independent-review lease is already active")
            lease_id = "irlease_" + uuid.uuid4().hex
            stamp = now_iso()
            transport = PROVIDER_TRANSPORT[provider]
            packet_fingerprint = fingerprint_text(packet_bytes)
            conn.execute(
                """INSERT INTO independent_review_leases(
                lease_id,project_id,run_id,candidate_fingerprint,job_id,input_fingerprint,packet_bytes,packet_fingerprint,relay_nonce,
                provider,transport,assurance_class,parent_session_id,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'pending',?,?)""",
                (
                    lease_id,
                    project_id,
                    run_id,
                    candidate_fingerprint,
                    job_id,
                    input_fingerprint,
                    packet_bytes.encode("utf-8"),
                    packet_fingerprint,
                    relay_nonce,
                    provider,
                    transport,
                    ASSURANCE_CLASS,
                    parent_session_id,
                    stamp,
                    stamp,
                ),
            )
            event = self._event(
                lease_id=lease_id,
                run_id=run_id,
                event_kind="prepared",
                payload={
                    "project_id": project_id,
                    "candidate_fingerprint": candidate_fingerprint,
                    "packet_fingerprint": packet_fingerprint,
                    "provider": provider,
                    "transport": transport,
                    "parent_session_id": parent_session_id,
                },
                created_at=stamp,
            )
            self._insert_event(conn, event)
            conn.commit()
            row = conn.execute("SELECT * FROM independent_review_leases WHERE lease_id=?", (lease_id,)).fetchone()
        return self._dispatch_projection(dict(row))

    @staticmethod
    def _dispatch_projection(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema": "quillframe_independent_dispatch_v1",
            "lease_id": row["lease_id"],
            "project_id": row["project_id"],
            "run_id": row["run_id"],
            "candidate_fingerprint": row["candidate_fingerprint"],
            "provider": row["provider"],
            "transport": row["transport"],
            "assurance_class": row["assurance_class"],
            "status": row["status"],
            "packet_fingerprint": row["packet_fingerprint"],
            "authority": False,
        }

    def claim(
        self,
        project_id: str,
        *,
        provider: str,
        parent_session_id: str,
        agent_type: str,
        host_agent_id: str,
        host_invocation_id: str,
    ) -> dict[str, Any]:
        provider = normalize_provider(provider)
        parent_session_id = _required(parent_session_id, "parent_session_id")
        agent_type = _required(agent_type, "agent_type")
        if agent_type != REVIEWER_AGENT_TYPE:
            raise IndependentReviewError(
                "independent_agent_type_invalid",
                f"agent_type must be {REVIEWER_AGENT_TYPE}",
            )
        host_agent_id = _required(host_agent_id, "host_agent_id")
        host_invocation_id = _required(host_invocation_id, "host_invocation_id")
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._assert_project_identity_row(
                conn.execute("SELECT project_id FROM project_identity").fetchone(),
                project_id,
            )
            reused = conn.execute(
                "SELECT lease_id FROM independent_review_leases WHERE host_agent_id=? OR host_invocation_id=? LIMIT 1",
                (host_agent_id, host_invocation_id),
            ).fetchone()
            if reused:
                raise IndependentReviewError("independent_host_identity_reused", "host agent or invocation ID was already used")
            rows = conn.execute(
                "SELECT * FROM independent_review_leases WHERE provider=? AND parent_session_id=? AND status='pending' ORDER BY created_at,rowid",
                (provider, parent_session_id),
            ).fetchall()
            if len(rows) != 1:
                code = "independent_lease_not_pending" if not rows else "independent_lease_ambiguous"
                raise IndependentReviewError(code, "trusted lifecycle fields do not identify one pending lease")
            row = rows[0]
            reviewer_session_id = "ses_review_" + uuid.uuid4().hex
            stamp = now_iso()
            conn.execute(
                "INSERT INTO sessions(session_id,provider_session_ref,status,version,created_at,updated_at) VALUES(?,?,?,1,?,?)",
                (reviewer_session_id, host_agent_id, "independent_review", stamp, stamp),
            )
            conn.execute(
                """UPDATE independent_review_leases SET status='claimed',reviewer_session_id=?,agent_type=?,host_agent_id=?,
                host_invocation_id=?,claimed_at=?,updated_at=? WHERE lease_id=? AND status='pending'""",
                (reviewer_session_id, agent_type, host_agent_id, host_invocation_id, stamp, stamp, row["lease_id"]),
            )
            event = self._event(
                lease_id=row["lease_id"],
                run_id=row["run_id"],
                event_kind="claimed",
                payload={
                    "provider": provider,
                    "parent_session_id": parent_session_id,
                    "reviewer_session_id": reviewer_session_id,
                    "agent_type": agent_type,
                    "host_agent_id": host_agent_id,
                    "host_invocation_id": host_invocation_id,
                },
                created_at=stamp,
            )
            self._insert_event(conn, event)
            conn.commit()
            claimed = conn.execute("SELECT * FROM independent_review_leases WHERE lease_id=?", (row["lease_id"],)).fetchone()
        packet_bytes = bytes(claimed["packet_bytes"]).decode("utf-8")
        return {
            "schema": "quillframe_independent_dispatch_claim_v1",
            "lease_id": claimed["lease_id"],
            "project_id": claimed["project_id"],
            "run_id": claimed["run_id"],
            "provider": claimed["provider"],
            "transport": claimed["transport"],
            "assurance_class": claimed["assurance_class"],
            "parent_session_id": claimed["parent_session_id"],
            "reviewer_session_id": claimed["reviewer_session_id"],
            "host_agent_id": claimed["host_agent_id"],
            "host_invocation_id": claimed["host_invocation_id"],
            "packet_bytes": packet_bytes,
            "peer_packet": json.loads(packet_bytes),
            "authority": False,
        }

    def lease(self, project_id: str, lease_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            row = conn.execute("SELECT * FROM independent_review_leases WHERE lease_id=?", (lease_id,)).fetchone()
        if not row:
            raise IndependentReviewError("independent_lease_not_found", lease_id)
        value = dict(row)
        value["packet_bytes"] = bytes(value["packet_bytes"]).decode("utf-8")
        return value

    def lifecycle_events(self, project_id: str, lease_id: str) -> list[dict[str, Any]]:
        with self.store.open_project(project_id) as conn:
            rows = conn.execute(
                "SELECT event_id,event_kind,event_fingerprint,payload_json,created_at FROM independent_review_lifecycle_events WHERE lease_id=? ORDER BY created_at,rowid",
                (lease_id,),
            ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "event_kind": row["event_kind"],
                "event_fingerprint": row["event_fingerprint"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def planned_completion_event(self, project_id: str, lease_id: str, result_fingerprint: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            lease = conn.execute(
                "SELECT * FROM independent_review_leases WHERE lease_id=?",
                (lease_id,),
            ).fetchone()
            if not lease:
                raise IndependentReviewError("independent_lease_not_found", lease_id)
            if lease["status"] != "claimed":
                raise IndependentReviewError("independent_lease_not_claimed", "native completion requires a claimed lease")
            if lease["completion_event_json"]:
                if lease["completion_result_fingerprint"] != result_fingerprint:
                    raise IndependentReviewError(
                        "independent_attempt_consumed",
                        "a different result cannot replace the planned native completion",
                    )
                event = json.loads(lease["completion_event_json"])
                conn.commit()
                return event
            event = self._event(
                lease_id=lease_id,
                run_id=lease["run_id"],
                event_kind="completed",
                payload={
                    "result_fingerprint": result_fingerprint,
                    "provider": lease["provider"],
                    "reviewer_session_id": lease["reviewer_session_id"],
                    "host_agent_id": lease["host_agent_id"],
                    "host_invocation_id": lease["host_invocation_id"],
                },
            )
            conn.execute(
                "UPDATE independent_review_leases SET completion_event_json=?,completion_result_fingerprint=?,updated_at=? WHERE lease_id=? AND status='claimed'",
                (canonical_json(event), result_fingerprint, now_iso(), lease_id),
            )
            conn.commit()
        return event

    def fail(
        self,
        project_id: str,
        *,
        lease_id: str,
        reviewer_session_id: str,
        host_agent_id: str,
        host_invocation_id: str,
        error: dict[str, Any],
    ) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM independent_review_leases WHERE lease_id=?", (lease_id,)).fetchone()
            if not row:
                raise IndependentReviewError("independent_lease_not_found", lease_id)
            if row["status"] == "infrastructure_failed":
                conn.commit()
                return self._dispatch_projection(dict(row))
            if row["status"] != "claimed":
                raise IndependentReviewError("independent_lease_not_claimed", "only a claimed lease can fail")
            if (
                row["reviewer_session_id"] != reviewer_session_id
                or row["host_agent_id"] != host_agent_id
                or row["host_invocation_id"] != host_invocation_id
            ):
                raise IndependentReviewError("independent_lifecycle_mismatch", "infrastructure failure identity mismatch")
            stamp = now_iso()
            conn.execute(
                "UPDATE independent_review_leases SET status='infrastructure_failed',infrastructure_error_json=?,updated_at=? WHERE lease_id=?",
                (canonical_json(error), stamp, lease_id),
            )
            event = self._event(
                lease_id=lease_id,
                run_id=row["run_id"],
                event_kind="infrastructure_failed",
                payload={"error": error, "reviewer_session_id": reviewer_session_id},
                created_at=stamp,
            )
            self._insert_event(conn, event)
            conn.commit()
            failed = conn.execute("SELECT * FROM independent_review_leases WHERE lease_id=?", (lease_id,)).fetchone()
        return self._dispatch_projection(dict(failed))

    def begin_attempt(
        self,
        project_id: str,
        run_id: str,
        candidate_fingerprint: str,
        *,
        evidence_fingerprint: str,
        transport: str,
        native_lease_id: str | None = None,
        wait_seconds: float = 3.0,
    ) -> dict[str, Any]:
        self.assert_project_identity(project_id)
        self.ensure_attempt(project_id, run_id, candidate_fingerprint)
        deadline = self.monotonic_clock() + wait_seconds
        while True:
            with self.store.open_project(project_id) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._assert_project_identity_row(
                    conn.execute("SELECT project_id FROM project_identity").fetchone(),
                    project_id,
                )
                row = conn.execute(
                    "SELECT * FROM independent_review_attempts WHERE run_id=? AND candidate_fingerprint=?",
                    (run_id, candidate_fingerprint),
                ).fetchone()
                if row["status"] == "terminal":
                    if row["terminal_evidence_fingerprint"] != evidence_fingerprint:
                        raise IndependentReviewError("independent_attempt_consumed", "different evidence cannot replay a terminal attempt")
                    response = json.loads(row["terminal_response_json"])
                    conn.commit()
                    return {"owner": False, "response": response}
                if row["status"] == "processing":
                    if row["processing_evidence_fingerprint"] != evidence_fingerprint:
                        raise IndependentReviewError("independent_attempt_consumed", "different evidence cannot replace a processing attempt")
                    now_value = self.clock()
                    expires_at = row["processing_expires_at"]
                    if expires_at is None or float(expires_at) <= now_value:
                        token = "irproc_" + uuid.uuid4().hex
                        epoch = int(row["processing_epoch"] or 0) + 1
                        conn.execute(
                            """UPDATE independent_review_attempts SET processing_token=?,processing_epoch=?,processing_expires_at=?,
                            updated_at=? WHERE run_id=? AND candidate_fingerprint=? AND status='processing' AND processing_evidence_fingerprint=?""",
                            (
                                token,
                                epoch,
                                now_value + self.processing_lease_seconds,
                                now_iso(),
                                run_id,
                                candidate_fingerprint,
                                evidence_fingerprint,
                            ),
                        )
                        conn.commit()
                        return {
                            "owner": True,
                            "processing_token": token,
                            "processing_epoch": epoch,
                            "recovered": True,
                        }
                    conn.commit()
                else:
                    active = conn.execute(
                        "SELECT lease_id FROM independent_review_leases WHERE run_id=? AND candidate_fingerprint=? AND status IN ('pending','claimed')",
                        (run_id, candidate_fingerprint),
                    ).fetchall()
                    active_ids = {item["lease_id"] for item in active}
                    if active_ids and (native_lease_id is None or active_ids != {native_lease_id}):
                        raise IndependentReviewError("independent_native_lease_active", "legacy submission is blocked by an active native lease")
                    token = "irproc_" + uuid.uuid4().hex
                    epoch = int(row["processing_epoch"] or 0) + 1
                    now_value = self.clock()
                    conn.execute(
                        """UPDATE independent_review_attempts SET status='processing',processing_token=?,processing_evidence_fingerprint=?,
                        processing_transport=?,processing_epoch=?,processing_expires_at=?,processing_phase='reserved',updated_at=?
                        WHERE run_id=? AND candidate_fingerprint=? AND status='available'""",
                        (
                            token,
                            evidence_fingerprint,
                            transport,
                            epoch,
                            now_value + self.processing_lease_seconds,
                            now_iso(),
                            run_id,
                            candidate_fingerprint,
                        ),
                    )
                    conn.commit()
                    return {
                        "owner": True,
                        "processing_token": token,
                        "processing_epoch": epoch,
                        "recovered": False,
                    }
            if self.monotonic_clock() >= deadline:
                raise IndependentReviewError("independent_submission_in_progress", "identical independent submission did not reach terminal state in time")
            self.sleeper(0.01)

    def mark_attempt_effects_started(
        self,
        project_id: str,
        run_id: str,
        candidate_fingerprint: str,
        processing_token: str,
    ) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                """UPDATE independent_review_attempts SET processing_phase='effects_started',processing_expires_at=?,updated_at=?
                WHERE run_id=? AND candidate_fingerprint=? AND status='processing' AND processing_token=?""",
                (
                    self.clock() + self.processing_lease_seconds,
                    now_iso(),
                    run_id,
                    candidate_fingerprint,
                    processing_token,
                ),
            ).rowcount
            if updated != 1:
                raise IndependentReviewError("independent_processing_owner_lost", "attempt processing owner changed")
            conn.commit()

    def abandon_attempt(
        self,
        project_id: str,
        run_id: str,
        candidate_fingerprint: str,
        processing_token: str,
    ) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT processing_phase FROM independent_review_attempts WHERE run_id=? AND candidate_fingerprint=? AND status='processing' AND processing_token=?",
                (run_id, candidate_fingerprint, processing_token),
            ).fetchone()
            if not row:
                conn.commit()
                return
            if row["processing_phase"] == "effects_started":
                conn.execute(
                    "UPDATE independent_review_attempts SET processing_expires_at=?,updated_at=? WHERE run_id=? AND candidate_fingerprint=? AND processing_token=?",
                    (self.clock(), now_iso(), run_id, candidate_fingerprint, processing_token),
                )
            else:
                conn.execute(
                    """UPDATE independent_review_attempts SET status='available',processing_token=NULL,processing_evidence_fingerprint=NULL,
                    processing_transport=NULL,processing_expires_at=NULL,processing_phase=NULL,updated_at=?
                    WHERE run_id=? AND candidate_fingerprint=? AND status='processing' AND processing_token=?""",
                    (now_iso(), run_id, candidate_fingerprint, processing_token),
                )
            conn.commit()

    def release_attempt(
        self,
        project_id: str,
        run_id: str,
        candidate_fingerprint: str,
        processing_token: str,
    ) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """UPDATE independent_review_attempts SET status='available',processing_token=NULL,processing_evidence_fingerprint=NULL,
                processing_transport=NULL,processing_expires_at=NULL,processing_phase=NULL,updated_at=?
                WHERE run_id=? AND candidate_fingerprint=? AND status='processing' AND processing_token=? AND processing_phase='reserved'""",
                (now_iso(), run_id, candidate_fingerprint, processing_token),
            )
            conn.commit()

    def terminalize_attempt(
        self,
        project_id: str,
        run_id: str,
        candidate_fingerprint: str,
        *,
        processing_token: str,
        evidence_fingerprint: str,
        response: dict[str, Any],
    ) -> None:
        response_json = canonical_json(response)
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                """UPDATE independent_review_attempts SET status='terminal',processing_token=NULL,processing_evidence_fingerprint=NULL,
                processing_transport=NULL,processing_expires_at=NULL,processing_phase=NULL,
                terminal_evidence_fingerprint=?,terminal_response_json=?,terminal_response_fingerprint=?,terminal_status=?,
                updated_at=? WHERE run_id=? AND candidate_fingerprint=? AND status='processing' AND processing_token=?""",
                (
                    evidence_fingerprint,
                    response_json,
                    fingerprint_text(response_json),
                    response.get("status"),
                    now_iso(),
                    run_id,
                    candidate_fingerprint,
                    processing_token,
                ),
            ).rowcount
            if updated != 1:
                raise IndependentReviewError("independent_processing_owner_lost", "attempt processing owner changed")
            conn.commit()

    def finalize_native(
        self,
        project_id: str,
        *,
        lease_id: str,
        completion_event: dict[str, Any],
        receipt: dict[str, Any],
        result_fingerprint: str,
        processing_token: str,
        evidence_fingerprint: str,
        response: dict[str, Any],
    ) -> None:
        response_json = canonical_json(response)
        receipt_json = canonical_json(receipt)
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            lease = conn.execute("SELECT * FROM independent_review_leases WHERE lease_id=?", (lease_id,)).fetchone()
            if not lease or lease["status"] != "claimed":
                raise IndependentReviewError("independent_lease_not_claimed", "native finalization lost its claimed lease")
            if (
                lease["completion_result_fingerprint"] != result_fingerprint
                or lease["completion_event_json"] != canonical_json(completion_event)
            ):
                raise IndependentReviewError("independent_lifecycle_mismatch", "native finalization differs from its durable completion plan")
            attempt = conn.execute(
                "SELECT status,processing_token FROM independent_review_attempts WHERE run_id=? AND candidate_fingerprint=?",
                (lease["run_id"], lease["candidate_fingerprint"]),
            ).fetchone()
            if not attempt or attempt["status"] != "processing" or attempt["processing_token"] != processing_token:
                raise IndependentReviewError("independent_processing_owner_lost", "native finalization lost attempt ownership")
            stamp = now_iso()
            self._insert_event(conn, completion_event)
            conn.execute(
                """UPDATE independent_review_leases SET status='completed',result_fingerprint=?,receipt_json=?,receipt_fingerprint=?,
                completed_at=?,updated_at=? WHERE lease_id=?""",
                (result_fingerprint, receipt_json, receipt["receipt_fingerprint"], stamp, stamp, lease_id),
            )
            conn.execute(
                """UPDATE independent_review_attempts SET status='terminal',processing_token=NULL,processing_evidence_fingerprint=NULL,
                processing_transport=NULL,processing_expires_at=NULL,processing_phase=NULL,
                terminal_evidence_fingerprint=?,terminal_response_json=?,terminal_response_fingerprint=?,terminal_status=?,
                updated_at=? WHERE run_id=? AND candidate_fingerprint=?""",
                (
                    evidence_fingerprint,
                    response_json,
                    fingerprint_text(response_json),
                    response.get("status"),
                    stamp,
                    lease["run_id"],
                    lease["candidate_fingerprint"],
                ),
            )
            conn.commit()
