#!/usr/bin/env python3
"""Operation-specific Quillframe 0.9 Core/Product commands.

This module deliberately has no generic invoke-anything mutation surface.
Every mutation preserves explicit authority boundaries and emits durable
fingerprint-bound state/receipts in the canonical Project SQLite database.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from persistence.quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso

AUTHOR_RUN_MODES = {
    "DESIGN-BOOK", "DESIGN-VOLUME", "PLAN-UNIT", "PLAN-CHAPTER",
    "DRAFT", "REVISE", "AUDIT", "RESEARCH", "CORPUS-INGEST", "LEARN",
}
MUTATION_KEYS = {"rewrite", "replacement_text", "apply_changes", "auto_fix", "settle", "accept"}


class OperationError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


class CoreOperations:
    def __init__(self, store: QuillframeStore | None = None) -> None:
        self.store = store or QuillframeStore()

    def bridge_description(self) -> dict[str, Any]:
        return {
            "schema": "quillframe_host_bridge_description_v1",
            "version": "0.9.0",
            "authority": False,
            "canon_authority": False,
            "framework_write_authority": False,
            "settlement_authority": False,
            "direct_core_store_access": False,
            "operations": [
                "project.create", "project.inspect", "project.search", "project.backup",
                "document.create", "document.revision.save", "document.revision.compare",
                "author.run.start", "candidate.accept", "settlement.apply",
                "feedback.observe", "publication.preview", "publication.build",
                "database.doctor",
            ],
        }

    def project_inspect(self, project_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            identity = conn.execute("SELECT * FROM project_identity").fetchone()
            counts = {}
            for table in (
                "story_nodes", "documents", "document_revisions", "characters", "relationships",
                "plans", "canon_claims", "candidates", "review_evidence", "acceptance_evidence",
                "settlements", "runs", "learning_evidence", "corpus_references", "publication_builds",
            ):
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if not identity:
            raise OperationError("project_invalid", "project identity is missing")
        return {
            "schema": "quillframe_project_projection_v1",
            "authority": False,
            "project": dict(identity),
            "counts": counts,
        }

    def start_author_run(
        self,
        project_id: str,
        *,
        task_mode: str,
        target_ref: str | None,
        payload: dict[str, Any],
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if task_mode not in AUTHOR_RUN_MODES:
            raise OperationError("unsupported_task_mode", "author.run.start requires one supported author task mode")
        if not isinstance(payload, dict):
            raise OperationError("invalid_args", "payload must be an object")
        if task_mode == "AUDIT" and MUTATION_KEYS.intersection(payload):
            raise OperationError("audit_is_non_mutating", "AUDIT reports findings and cannot request rewrite/apply actions")
        if task_mode == "DRAFT" and {"settle", "accept"}.intersection(payload):
            raise OperationError("draft_cannot_settle", "DRAFT cannot accept or settle its own result")
        request = {"project_id": project_id, "task_mode": task_mode, "target_ref": target_ref, "payload": payload}
        request_fp = fingerprint_text(canonical_json(request))
        with self.store.open_project(project_id) as conn:
            if idempotency_key:
                row = conn.execute(
                    "SELECT payload_json FROM receipts WHERE receipt_kind='author_run_start' AND idempotency_key=?",
                    (idempotency_key,),
                ).fetchone()
                if row:
                    return json.loads(row["payload_json"])
            if session_id:
                session = conn.execute("SELECT session_id FROM sessions WHERE session_id=?", (session_id,)).fetchone()
                if not session:
                    raise OperationError("unknown_session", "session_id does not exist")
            run_id = "run_" + uuid.uuid4().hex
            stamp = now_iso()
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO runs(run_id,session_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (run_id, session_id, task_mode, target_ref, "awaiting_semantic", request_fp, stamp, stamp),
            )
            event_id = "evt_" + uuid.uuid4().hex
            conn.execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                (event_id, run_id, "author_run_requested", canonical_json({"task_mode": task_mode, "target_ref": target_ref}), stamp),
            )
            result = {
                "schema": "quillframe_author_run_start_result_v1",
                "run_id": run_id,
                "task_mode": task_mode,
                "target_ref": target_ref,
                "status": "awaiting_semantic",
                "request_fingerprint": request_fp,
                "raw_draft_visible": False,
                "candidate_visible": False,
                "authority": False,
                "canon_authority": False,
                "settlement_authority": False,
                "message": "Run is durably registered; a semantic worker must execute the exact task contract before a gated candidate/result can appear.",
            }
            conn.execute(
                "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                ("rcpt_" + uuid.uuid4().hex, run_id, "author_run_start", idempotency_key, canonical_json(result), stamp),
            )
            conn.commit()
            return result

    def accept_candidate(
        self,
        project_id: str,
        *,
        candidate_id: str,
        candidate_fingerprint: str,
        authorized_by: str,
        authorization: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise OperationError("idempotency_required", "candidate acceptance requires an idempotency key")
        with self.store.open_project(project_id) as conn:
            prior = conn.execute(
                "SELECT payload_json FROM receipts WHERE receipt_kind='candidate_accept' AND idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if prior:
                return json.loads(prior["payload_json"])
            candidate = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
            if not candidate:
                raise OperationError("candidate_not_found", candidate_id)
            if candidate["status"] != "review_draft" or candidate["user_visible_gate"] != "PASS":
                raise OperationError("candidate_not_acceptable", "only a user-visible-gate PASS Review Draft may be accepted")
            if candidate["content_fingerprint"] != candidate_fingerprint:
                raise OperationError("candidate_fingerprint_mismatch", "candidate changed since review")
            evidence = conn.execute(
                "SELECT COUNT(*) FROM review_evidence WHERE candidate_id=? AND candidate_fingerprint=? AND independent=1 AND stale=0",
                (candidate_id, candidate_fingerprint),
            ).fetchone()[0]
            if evidence < 1:
                raise OperationError("independent_review_required", "fresh fingerprint-bound independent review evidence is required")
            acceptance_id = "accept_" + uuid.uuid4().hex
            stamp = now_iso()
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO acceptance_evidence(acceptance_id,candidate_id,candidate_fingerprint,authorized_by,authorization_json,created_at) VALUES(?,?,?,?,?,?)",
                (acceptance_id, candidate_id, candidate_fingerprint, authorized_by, canonical_json(authorization), stamp),
            )
            conn.execute("UPDATE candidates SET status='accepted' WHERE candidate_id=?", (candidate_id,))
            if candidate["revision_id"]:
                conn.execute("UPDATE document_revisions SET authority_class='accepted' WHERE revision_id=?", (candidate["revision_id"],))
            result = {
                "schema": "quillframe_candidate_acceptance_result_v1",
                "acceptance_id": acceptance_id,
                "candidate_id": candidate_id,
                "candidate_fingerprint": candidate_fingerprint,
                "accepted": True,
                "settled": False,
                "canon_mutated": False,
            }
            conn.execute(
                "INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?)",
                ("rcpt_" + uuid.uuid4().hex, "candidate_accept", idempotency_key, canonical_json(result), stamp),
            )
            conn.commit()
            return result

    def settle(
        self,
        project_id: str,
        *,
        acceptance_id: str,
        target_ref: str,
        expected_before_fingerprint: str,
        user_authorized: bool,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not user_authorized:
            raise OperationError("authorization_required", "Settlement requires explicit user authorization")
        if not idempotency_key:
            raise OperationError("idempotency_required", "Settlement requires an idempotency key")
        with self.store.open_project(project_id) as conn:
            prior = conn.execute("SELECT payload_json FROM receipts WHERE receipt_kind='settlement' AND idempotency_key=?", (idempotency_key,)).fetchone()
            if prior:
                return json.loads(prior["payload_json"])
            acceptance = conn.execute(
                """SELECT a.*, c.revision_id, c.content_fingerprint, c.document_id
                FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id
                WHERE a.acceptance_id=?""",
                (acceptance_id,),
            ).fetchone()
            if not acceptance:
                raise OperationError("acceptance_not_found", acceptance_id)
            current = conn.execute("SELECT * FROM canon_state WHERE state_key=?", (target_ref,)).fetchone()
            before = current["content_fingerprint"] if current else "absent"
            stamp = now_iso()
            settlement_id = "settle_" + uuid.uuid4().hex
            if before != expected_before_fingerprint:
                result = {
                    "schema": "quillframe_settlement_result_v1",
                    "settlement_id": settlement_id,
                    "status": "settlement_incomplete",
                    "target_ref": target_ref,
                    "expected_before_fingerprint": expected_before_fingerprint,
                    "actual_before_fingerprint": before,
                    "canon_mutated": False,
                }
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO settlements(settlement_id,acceptance_id,target_ref,before_fingerprint,state_delta_json,status,receipt_json,created_at) VALUES(?,?,?,?,?,'settlement_incomplete',?,?)",
                    (settlement_id, acceptance_id, target_ref, before, canonical_json({}), canonical_json(result), stamp),
                )
                conn.execute(
                    "INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?)",
                    ("rcpt_" + uuid.uuid4().hex, "settlement", idempotency_key, canonical_json(result), stamp),
                )
                conn.commit()
                return result
            if not acceptance["revision_id"]:
                raise OperationError("settlement_source_missing", "accepted candidate has no document revision")
            revision = conn.execute("SELECT * FROM document_revisions WHERE revision_id=?", (acceptance["revision_id"],)).fetchone()
            if not revision or revision["authority_class"] != "accepted":
                raise OperationError("settlement_source_not_accepted", "source revision is not Accepted")
            value = {
                "acceptance_id": acceptance_id,
                "candidate_id": acceptance["candidate_id"],
                "document_id": acceptance["document_id"],
                "revision_id": revision["revision_id"],
                "content_fingerprint": revision["content_fingerprint"],
            }
            after = fingerprint_text(canonical_json(value))
            delta = {"before": dict(current) if current else None, "after": value}
            result = {
                "schema": "quillframe_settlement_result_v1",
                "settlement_id": settlement_id,
                "status": "settled",
                "target_ref": target_ref,
                "before_fingerprint": before,
                "after_fingerprint": after,
                "state_delta": delta,
                "canon_mutated": True,
            }
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO canon_state(state_key,value_json,authority_class,evidence_ref,content_fingerprint,updated_at)
                VALUES(?,?,'accepted',?,?,?)
                ON CONFLICT(state_key) DO UPDATE SET value_json=excluded.value_json,authority_class='accepted',evidence_ref=excluded.evidence_ref,content_fingerprint=excluded.content_fingerprint,updated_at=excluded.updated_at""",
                (target_ref, canonical_json(value), acceptance_id, after, stamp),
            )
            conn.execute(
                "INSERT INTO settlements(settlement_id,acceptance_id,target_ref,before_fingerprint,after_fingerprint,state_delta_json,status,receipt_json,created_at,completed_at) VALUES(?,?,?,?,?,?,'settled',?,?,?)",
                (settlement_id, acceptance_id, target_ref, before, after, canonical_json(delta), canonical_json(result), stamp, stamp),
            )
            conn.execute(
                "INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?)",
                ("rcpt_" + uuid.uuid4().hex, "settlement", idempotency_key, canonical_json(result), stamp),
            )
            conn.commit()
            return result

    def observe_feedback(
        self,
        project_id: str,
        *,
        evidence_kind: str,
        payload: dict[str, Any],
        source_ref: str | None = None,
    ) -> dict[str, Any]:
        evidence_id = "learn_" + uuid.uuid4().hex
        with self.store.open_project(project_id) as conn:
            conn.execute(
                "INSERT INTO learning_evidence(evidence_id,evidence_kind,source_ref,payload_json,state,promotion_eligible,created_at) VALUES(?,?,?,?, 'captured',0,?)",
                (evidence_id, evidence_kind, source_ref, canonical_json(payload), now_iso()),
            )
            conn.commit()
        return {
            "schema": "quillframe_feedback_intake_result_v1",
            "evidence_id": evidence_id,
            "captured": True,
            "promotion_state": "not_promoted",
            "promotion_eligible": False,
            "canon_write": False,
            "framework_write": False,
        }

    def publication_preview(self, project_id: str, acceptance_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            row = conn.execute(
                """SELECT a.acceptance_id,a.candidate_fingerprint,c.document_id,c.revision_id,r.content,r.content_fingerprint
                FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id
                JOIN document_revisions r ON r.revision_id=c.revision_id WHERE a.acceptance_id=?""",
                (acceptance_id,),
            ).fetchone()
            if not row or row["content_fingerprint"] != row["candidate_fingerprint"]:
                raise OperationError("publication_source_invalid", "publication source must be an intact Accepted artifact")
            return {
                "schema": "quillframe_publication_preview_v1",
                "persistent": False,
                "source_acceptance_id": acceptance_id,
                "source_fingerprint": row["content_fingerprint"],
                "document_id": row["document_id"],
                "content": row["content"],
            }

    def publication_build(self, project_id: str, acceptance_id: str, fmt: str = "md") -> dict[str, Any]:
        if fmt not in {"md", "txt"}:
            raise OperationError("unsupported_export_format", "0.9 currently supports only md and txt publication exports")
        preview = self.publication_preview(project_id, acceptance_id)
        loc = self.store.location(project_id)
        loc.exports.mkdir(parents=True, exist_ok=True)
        build_id = "pub_" + uuid.uuid4().hex
        target = loc.exports / f"{build_id}.{fmt}"
        target.write_text(preview["content"], encoding="utf-8")
        with self.store.open_project(project_id) as conn:
            conn.execute(
                "INSERT INTO publication_builds(build_id,source_acceptance_id,format,output_ref,source_fingerprint,validation_json,persistent,created_at) VALUES(?,?,?,?,?,?,1,?)",
                (build_id, acceptance_id, fmt, target.relative_to(loc.directory).as_posix(), preview["source_fingerprint"], canonical_json({"source_intact": True}), now_iso()),
            )
            conn.commit()
        return {
            "schema": "quillframe_publication_build_v1",
            "build_id": build_id,
            "persistent": True,
            "source_acceptance_id": acceptance_id,
            "source_fingerprint": preview["source_fingerprint"],
            "output_ref": target.relative_to(loc.directory).as_posix(),
            "format": fmt,
        }
