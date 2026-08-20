#!/usr/bin/env python3
"""Operation-specific Quillframe 1.0 Core/Product commands.

This module deliberately has no generic invoke-anything mutation surface.
Every mutation preserves explicit authority boundaries and emits durable
fingerprint-bound state/receipts in the canonical Project SQLite database.
"""
from __future__ import annotations

import json
import hashlib
import re
import uuid
from pathlib import Path
from typing import Any

from persistence.quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso
from publication.recovery import PublicationRecovery, PublicationRecoveryError

AUTHOR_RUN_MODES = {
    "DESIGN-BOOK", "DESIGN-VOLUME", "PLAN-UNIT", "PLAN-CHAPTER",
    "DRAFT", "REVISE", "AUDIT", "RESEARCH", "CORPUS-INGEST", "LEARN",
}
MUTATION_KEYS = {"rewrite", "replacement_text", "apply_changes", "auto_fix", "settle", "accept"}
CHAPTER_SCOPE = "CH001"
CHAPTER_REF_RE = re.compile(r"(?<![A-Za-z0-9])CH\d{3}(?![A-Za-z0-9])")

AUTHORIZATION_KEY_ORDER = (
    "intent",
    "source",
    "explicit_action",
    "observed_gate",
    "reason",
    "provenance_ref",
)
AUTHORIZATION_KEYS = set(AUTHORIZATION_KEY_ORDER)
REVISION_REQUEST_KEYS = {"instruction", "source"}
MAX_SAFE_SCALAR_LENGTH = 512
MAX_SAFE_OBJECT_LENGTH = 4096
_CREDENTIAL_KEY_RE = re.compile(
    r"(?:access|refresh)[_-]?token|\btoken\b|api[_-]?key|apikey|password|passwd|secret|credential|authorization|private[_-]?key|bearer|basic|oauth|cookie|session[_-]?token",
    re.IGNORECASE,
)
_CREDENTIAL_VALUE_RE = re.compile(
    r"(?:\bbearer\b|\bbasic\b|-----BEGIN [^-\n]*PRIVATE KEY-----|"
    r"\b(?:sk|pk|rk|ak|ghp|gho|github_pat|xox[baprs])[-_][A-Za-z0-9_-]+|"
    r"\bAIza[0-9A-Za-z_-]{20,}|\b(?:api[_-]?key|access[_-]?token)\s*[:=])",
    re.IGNORECASE,
)


class OperationError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


class CoreOperations:
    def __init__(self, store: QuillframeStore | None = None) -> None:
        self.store = store or QuillframeStore()

    def project_inspect(self, project_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            identity = conn.execute("SELECT * FROM project_identity").fetchone()
            counts = {}
            for table in (
                "story_nodes", "documents", "document_revisions", "characters", "relationships",
                "plans", "canon_claims", "candidates", "review_evidence", "acceptance_evidence",
                "settlements", "runs", "learning_evidence", "corpus_references", "publication_builds",
                "publication_build_attempts",
            ):
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if not identity:
            raise OperationError("project_invalid", "project identity is missing")
        manifest = self._native_manifest(dict(identity))
        return {
            "schema": "quillframe_project_inspection_v1_0",
            "manifest": manifest,
            "manifest_fingerprint": self._native_fingerprint(manifest),
            "chapter_scope": CHAPTER_SCOPE,
            "data_boundary": ".quillframe/data",
            "authority": False,
            "counts": counts,
        }

    def project_list(self, *, limit: int = 100) -> dict[str, Any]:
        items = []
        for row in self.store.list_projects(limit):
            manifest = self._native_manifest(row)
            items.append({
                "schema": "quillframe_project_registry_item_v1_0",
                "id": manifest["id"],
                "title": manifest["title"],
                "language": manifest["language"],
                "chapter_scope": manifest["chapter_scope"],
                "manifest_fingerprint": self._native_fingerprint(manifest),
                "data_boundary": ".quillframe/data",
                "last_opened_at": row.get("last_opened_at"),
            })
        return {
            "schema": "quillframe_project_list_v1_0",
            "items": items,
            "authority": False,
        }

    @staticmethod
    def _native_manifest(identity: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema": "quillframe_project_v1_0",
            "id": str(identity["project_id"]),
            "title": str(identity["title"]),
            "language": str(identity["language"]),
            "chapter_scope": CHAPTER_SCOPE,
        }

    @staticmethod
    def _native_fingerprint(manifest: dict[str, Any]) -> str:
        return "sha256:" + hashlib.sha256(
            canonical_json(manifest).encode("utf-8")
        ).hexdigest()

    def document_list(self, project_id: str, *, document_kind: str | None = None, limit: int = 500) -> dict[str, Any]:
        bounded = max(1, min(int(limit), 500))
        with self.store.open_project(project_id) as conn:
            if document_kind is not None:
                rows = conn.execute(
                    """SELECT d.document_id,d.story_node_id,d.document_kind,d.title,d.created_at,
                    r.revision_id AS latest_revision_id,r.content_fingerprint AS latest_content_fingerprint,
                    r.authority_class AS latest_authority_class,r.created_at AS latest_revision_created_at
                    FROM documents d
                    LEFT JOIN document_revisions r ON r.revision_id=(
                      SELECT rr.revision_id FROM document_revisions rr
                      WHERE rr.document_id=d.document_id ORDER BY rr.created_at DESC,rr.rowid DESC LIMIT 1
                    )
                    WHERE d.document_kind=? ORDER BY d.created_at,d.document_id LIMIT ?""",
                    (document_kind, bounded),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT d.document_id,d.story_node_id,d.document_kind,d.title,d.created_at,
                    r.revision_id AS latest_revision_id,r.content_fingerprint AS latest_content_fingerprint,
                    r.authority_class AS latest_authority_class,r.created_at AS latest_revision_created_at
                    FROM documents d
                    LEFT JOIN document_revisions r ON r.revision_id=(
                      SELECT rr.revision_id FROM document_revisions rr
                      WHERE rr.document_id=d.document_id ORDER BY rr.created_at DESC,rr.rowid DESC LIMIT 1
                    )
                    ORDER BY d.created_at,d.document_id LIMIT ?""",
                    (bounded,),
                ).fetchall()
        return {
            "schema": "quillframe_document_list_projection_v1",
            "project_id": project_id,
            "document_kind": document_kind,
            "items": [dict(row) for row in rows],
            "authority": False,
            "canon_authority": False,
        }

    @staticmethod
    def _candidate_revision_request_receipt(conn, candidate_id: str) -> dict[str, Any] | None:  # noqa: ANN001
        rows = conn.execute(
            "SELECT payload_json FROM receipts WHERE receipt_kind='candidate_revision_request' ORDER BY created_at DESC,rowid DESC"
        ).fetchall()
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if payload.get("candidate_id") == candidate_id:
                return payload
        return None

    @staticmethod
    def _validated_production_release(conn, candidate: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
        run_id = candidate.get("run_id")
        if candidate.get("user_visible_gate") != "PASS" or not run_id:
            raise OperationError("production_release_required", "Candidate has no releasable user-visible execution binding")
        run = conn.execute("SELECT status,result_fingerprint FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not run or run["status"] != "completed":
            raise OperationError("production_release_required", "Candidate run is not completed")
        row = conn.execute(
            "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_release' ORDER BY created_at DESC,rowid DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        if not row:
            raise OperationError("production_release_required", "Candidate has no production release receipt")
        try:
            release = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise OperationError("production_release_invalid", "Production release receipt is not valid JSON") from exc
        if release.get("schema") != "quillframe_production_release_v1":
            raise OperationError("production_release_invalid", "Production release schema mismatch")
        if release.get("candidate_fingerprint") != candidate.get("content_fingerprint"):
            raise OperationError("production_release_invalid", "Production release candidate fingerprint mismatch")
        if release.get("ready_for_user_visible_review") is not True:
            raise OperationError("production_release_required", "Production release did not authorize user-visible review")
        declared = release.get("release_fingerprint")
        body = {key: value for key, value in release.items() if key != "release_fingerprint"}
        if not isinstance(declared, str) or fingerprint_text(canonical_json(body)) != declared:
            raise OperationError("production_release_invalid", "Production release fingerprint is invalid")
        if run["result_fingerprint"] and run["result_fingerprint"] != candidate.get("content_fingerprint"):
            raise OperationError("production_release_invalid", "Completed run result fingerprint does not match candidate")
        return release

    def candidate_visible_get(self, project_id: str, *, candidate_id: str) -> dict[str, Any]:
        """Return manuscript text only after exact production release validation."""
        with self.store.open_project(project_id) as conn:
            row = conn.execute(
                """SELECT c.*,r.content AS candidate_content,r.content_fingerprint AS revision_fingerprint,
                r.authority_class AS revision_authority_class
                FROM candidates c LEFT JOIN document_revisions r ON r.revision_id=c.revision_id
                WHERE c.candidate_id=?""",
                (candidate_id,),
            ).fetchone()
            if not row:
                raise OperationError("candidate_not_found", candidate_id)
            candidate = dict(row)
            if not candidate.get("revision_id") or candidate.get("revision_fingerprint") != candidate.get("content_fingerprint"):
                raise OperationError("stale_review", "Candidate revision no longer matches its release fingerprint")
            release = self._validated_production_release(conn, candidate)
        return {
            "schema": "quillframe_user_visible_candidate_v1",
            "project_id": project_id,
            "candidate_id": candidate["candidate_id"],
            "candidate_fingerprint": candidate["content_fingerprint"],
            "document_id": candidate.get("document_id"),
            "revision_id": candidate.get("revision_id"),
            "content": candidate["candidate_content"],
            "authority_class": candidate.get("revision_authority_class"),
            "production_release": release,
            "content_access": "production_release_only",
            "accepted": candidate.get("status") == "accepted",
            "settled": False,
            "private_reasoning_exposed": False,
            "authority": False,
            "canon_authority": False,
        }

    def candidate_review_get(self, project_id: str, *, candidate_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            candidate = conn.execute(
                """SELECT c.*,r.parent_revision_id,r.content AS candidate_content,
                r.content_fingerprint AS revision_fingerprint,r.authority_class AS revision_authority_class
                FROM candidates c LEFT JOIN document_revisions r ON r.revision_id=c.revision_id
                WHERE c.candidate_id=?""",
                (candidate_id,),
            ).fetchone()
            if not candidate:
                raise OperationError("candidate_not_found", candidate_id)
            c = dict(candidate)
            if not c.get("revision_id") or c.get("revision_fingerprint") != c.get("content_fingerprint"):
                raise OperationError("stale_review", "Candidate revision no longer matches its review fingerprint")
            release = self._validated_production_release(conn, c)
            parent = None
            if c.get("parent_revision_id"):
                row = conn.execute(
                    "SELECT revision_id,document_id,content,content_fingerprint,authority_class,created_at FROM document_revisions WHERE revision_id=?",
                    (c["parent_revision_id"],),
                ).fetchone()
                parent = dict(row) if row else None
            current_review_rows = conn.execute(
                "SELECT * FROM review_evidence WHERE candidate_id=? AND candidate_fingerprint=? AND independent=1 AND stale=0 ORDER BY created_at DESC,rowid DESC",
                (candidate_id, c["content_fingerprint"]),
            ).fetchall()
            any_review = conn.execute("SELECT COUNT(*) FROM review_evidence WHERE candidate_id=?", (candidate_id,)).fetchone()[0]
            if not current_review_rows:
                raise OperationError("stale_review" if any_review else "review_pending", "fresh fingerprint-bound independent Review evidence is unavailable")
            independent = json.loads(current_review_rows[0]["result_json"])
            stage_rows = conn.execute(
                "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage' ORDER BY created_at,rowid",
                (c.get("run_id"),),
            ).fetchall() if c.get("run_id") else []
            stage_receipts = []
            for row in stage_rows:
                try:
                    stage_receipts.append(json.loads(row["payload_json"]))
                except (TypeError, json.JSONDecodeError):
                    continue
            by_mechanism = {row.get("mechanism"): row for row in stage_receipts if isinstance(row, dict)}
            required = ("reader_engagement", "character_simulation", "continuity", "independent_semantic_gate", "user_visible_gate")
            if any(name not in by_mechanism for name in required):
                raise OperationError("review_pending", "Candidate Review evidence is not complete")
            revision_request = self._candidate_revision_request_receipt(conn, candidate_id)

        diff = None
        if parent:
            diff = self.store.compare_revisions(project_id, parent["revision_id"], c["revision_id"])
        return {
            "schema": "quillframe_candidate_review_projection_v1",
            "project_id": project_id,
            "candidate": {
                "candidate_id": c["candidate_id"],
                "candidate_fingerprint": c["content_fingerprint"],
                "document_id": c.get("document_id"),
                "run_id": c.get("run_id"),
                "task_mode": c.get("task_mode"),
                "candidate_kind": c.get("candidate_kind"),
                "persisted_status": c.get("status"),
                "effective_status": "revision_requested" if revision_request and c.get("status") == "review_draft" else c.get("status"),
                "user_visible_gate": c.get("user_visible_gate"),
            },
            "candidate_revision": {
                "revision_id": c["revision_id"],
                "content": c["candidate_content"],
                "content_fingerprint": c["revision_fingerprint"],
                "authority_class": c["revision_authority_class"],
            },
            "incumbent_revision": parent,
            "diff": diff,
            "evidence": {
                "reader": by_mechanism["reader_engagement"],
                "character": by_mechanism["character_simulation"],
                "continuity": by_mechanism["continuity"],
                "independent": independent,
                "production_readiness": independent.get("production_readiness"),
                "user_visible_gate": by_mechanism["user_visible_gate"],
                "production_release": release,
            },
            "revision_request": revision_request,
            "private_reasoning_exposed": False,
            "authority": False,
            "canon_authority": False,
            "settlement_authority": False,
        }

    @staticmethod
    def _invalid_authorization() -> OperationError:
        return OperationError("invalid_authorization", "authorization must be a bounded, canonical, secret-free object")

    @staticmethod
    def _invalid_revision_request() -> OperationError:
        return OperationError("invalid_revision_request", "revision_request must be a bounded, canonical, secret-free object")

    @staticmethod
    def _safe_scalar(value: Any, *, error_factory, allow_none: bool = False) -> str | None:
        if allow_none and value is None:
            return None
        if not isinstance(value, str) or not value.strip() or len(value) > MAX_SAFE_SCALAR_LENGTH or "\x00" in value:
            raise error_factory()
        if _CREDENTIAL_VALUE_RE.search(value):
            raise error_factory()
        return value

    @staticmethod
    def _normalized_contract_key(key: Any, *, error_factory) -> str:
        if not isinstance(key, str):
            raise error_factory()
        normalized = key.lower()
        if not normalized or len(normalized) > MAX_SAFE_SCALAR_LENGTH or _CREDENTIAL_KEY_RE.search(normalized):
            raise error_factory()
        return normalized

    @classmethod
    def _validate_authorization(cls, authorization: Any) -> dict[str, Any]:
        if not isinstance(authorization, dict) or not authorization:
            raise cls._invalid_authorization()
        normalized: dict[str, Any] = {}
        try:
            for raw_key, value in authorization.items():
                key = cls._normalized_contract_key(raw_key, error_factory=cls._invalid_authorization)
                if key not in AUTHORIZATION_KEYS or key in normalized:
                    raise cls._invalid_authorization()
                if isinstance(value, (dict, list, tuple, set)):
                    raise cls._invalid_authorization()
                if key == "observed_gate":
                    normalized[key] = cls._safe_scalar(
                        value,
                        error_factory=cls._invalid_authorization,
                        allow_none=True,
                    )
                else:
                    normalized[key] = cls._safe_scalar(value, error_factory=cls._invalid_authorization)
        except OperationError:
            raise
        except Exception as exc:  # fail closed without reflecting caller data
            raise cls._invalid_authorization() from exc
        if not normalized.get("intent") and not normalized.get("explicit_action"):
            raise cls._invalid_authorization()
        try:
            if len(canonical_json(normalized)) > MAX_SAFE_OBJECT_LENGTH:
                raise cls._invalid_authorization()
        except OperationError:
            raise
        except Exception as exc:
            raise cls._invalid_authorization() from exc
        return {key: normalized[key] for key in AUTHORIZATION_KEY_ORDER if key in normalized}

    @classmethod
    def _validate_revision_request(cls, revision_request: Any) -> dict[str, str]:
        if not isinstance(revision_request, dict) or not revision_request:
            raise cls._invalid_revision_request()
        normalized: dict[str, str] = {}
        try:
            for raw_key, value in revision_request.items():
                key = cls._normalized_contract_key(raw_key, error_factory=cls._invalid_revision_request)
                if key not in REVISION_REQUEST_KEYS or key in normalized:
                    raise cls._invalid_revision_request()
                if isinstance(value, (dict, list, tuple, set)):
                    raise cls._invalid_revision_request()
                normalized[key] = cls._safe_scalar(value, error_factory=cls._invalid_revision_request)  # type: ignore[assignment]
        except OperationError:
            raise
        except Exception as exc:
            raise cls._invalid_revision_request() from exc
        if not normalized.get("instruction"):
            raise cls._invalid_revision_request()
        try:
            if len(canonical_json(normalized)) > MAX_SAFE_OBJECT_LENGTH:
                raise cls._invalid_revision_request()
        except OperationError:
            raise
        except Exception as exc:
            raise cls._invalid_revision_request() from exc
        return {key: normalized[key] for key in ("instruction", "source") if key in normalized}

    @classmethod
    def _validate_write_identity(cls, *, authorized_by: Any, idempotency_key: Any) -> tuple[str, str]:
        actor = cls._safe_scalar(authorized_by, error_factory=cls._invalid_authorization)
        key = cls._safe_scalar(idempotency_key, error_factory=lambda: OperationError("invalid_args", "idempotency key is invalid"))
        if actor is None or key is None:
            raise OperationError("invalid_args", "write identity is invalid")
        return actor, key

    @staticmethod
    def _idempotency_replay_or_conflict(conn, *, idempotency_key: str | None, receipt_kind: str, request_fingerprint: str) -> dict[str, Any] | None:  # noqa: ANN001
        if idempotency_key is None:
            return None
        row = conn.execute(
            "SELECT receipt_kind,payload_json FROM receipts WHERE idempotency_key=?",
            (idempotency_key,),
        ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise OperationError("idempotency_conflict", "idempotency key is already bound to another request") from exc
        if (
            row["receipt_kind"] != receipt_kind
            or not isinstance(payload, dict)
            or payload.get("request_fingerprint") != request_fingerprint
        ):
            raise OperationError("idempotency_conflict", "idempotency key is already bound to another request")
        return payload

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
        if payload.get("chapter_id") != CHAPTER_SCOPE:
            raise OperationError(
                "chapter_scope_violation",
                f"author.run.start requires chapter_id={CHAPTER_SCOPE}",
            )
        target_chapters = CHAPTER_REF_RE.findall(target_ref or "")
        if any(chapter != CHAPTER_SCOPE for chapter in target_chapters):
            raise OperationError(
                "chapter_scope_violation",
                f"author.run.start target_ref must remain within {CHAPTER_SCOPE}",
            )
        if task_mode == "AUDIT" and MUTATION_KEYS.intersection(payload):
            raise OperationError("audit_is_non_mutating", "AUDIT reports findings and cannot request rewrite/apply actions")
        if task_mode == "DRAFT" and {"settle", "accept"}.intersection(payload):
            raise OperationError("draft_cannot_settle", "DRAFT cannot accept or settle its own result")
        if idempotency_key is not None:
            idempotency_key = self._safe_scalar(
                idempotency_key,
                error_factory=lambda: OperationError("invalid_args", "idempotency key is invalid"),
            )
        if session_id is not None:
            session_id = self._safe_scalar(
                session_id,
                error_factory=lambda: OperationError("invalid_args", "session_id is invalid"),
            )
        request = {
            "operation": "author.run.start",
            "project_id": project_id,
            "task_mode": task_mode,
            "target_ref": target_ref,
            "payload": payload,
        }
        request["session_id"] = session_id
        request_fp = fingerprint_text(canonical_json(request))
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                prior = self._idempotency_replay_or_conflict(
                    conn,
                    idempotency_key=idempotency_key,
                    receipt_kind="author_run_start",
                    request_fingerprint=request_fp,
                )
                if prior is not None:
                    conn.commit()
                    return prior
                if session_id is not None:
                    session = conn.execute("SELECT session_id FROM sessions WHERE session_id=?", (session_id,)).fetchone()
                    if not session:
                        raise OperationError("unknown_session", "session_id does not exist")
                run_id = "run_" + uuid.uuid4().hex
                stamp = now_iso()
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
                result = json.loads(canonical_json(result))
                conn.execute(
                    "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                    ("rcpt_" + uuid.uuid4().hex, run_id, "author_run_start", idempotency_key, canonical_json(result), stamp),
                )
                conn.commit()
                return result
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

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
        if idempotency_key is None or idempotency_key == "":
            raise OperationError("idempotency_required", "candidate acceptance requires an idempotency key")
        authorized_by, idempotency_key = self._validate_write_identity(
            authorized_by=authorized_by,
            idempotency_key=idempotency_key,
        )
        safe_authorization = self._validate_authorization(authorization)
        candidate_fingerprint = self._safe_scalar(
            candidate_fingerprint,
            error_factory=lambda: OperationError("invalid_args", "candidate fingerprint is invalid"),
        )
        assert candidate_fingerprint is not None
        request = {
            "operation": "candidate.accept",
            "project_id": project_id,
            "candidate_id": candidate_id,
            "candidate_fingerprint": candidate_fingerprint,
            "authorized_by": authorized_by,
            "authorization": safe_authorization,
        }
        request_fp = fingerprint_text(canonical_json(request))
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                prior = self._idempotency_replay_or_conflict(
                    conn,
                    idempotency_key=idempotency_key,
                    receipt_kind="candidate_accept",
                    request_fingerprint=request_fp,
                )
                if prior is not None:
                    conn.commit()
                    return prior
                candidate = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
                if not candidate:
                    raise OperationError("candidate_not_found", "candidate does not exist")
                if candidate["status"] != "review_draft" or candidate["user_visible_gate"] != "PASS":
                    raise OperationError("candidate_not_acceptable", "only a user-visible-gate PASS Review Draft may be accepted")
                if candidate["content_fingerprint"] != candidate_fingerprint:
                    raise OperationError("candidate_fingerprint_mismatch", "candidate changed since review")
                self._validated_production_release(conn, dict(candidate))
                if self._candidate_revision_request_receipt(conn, candidate_id):
                    raise OperationError("candidate_revision_requested", "Candidate has a durable revision request and cannot be accepted")
                evidence = conn.execute(
                    "SELECT COUNT(*) FROM review_evidence WHERE candidate_id=? AND candidate_fingerprint=? AND independent=1 AND stale=0",
                    (candidate_id, candidate_fingerprint),
                ).fetchone()[0]
                if evidence < 1:
                    raise OperationError("independent_review_required", "fresh fingerprint-bound independent review evidence is required")
                acceptance_id = "accept_" + uuid.uuid4().hex
                stamp = now_iso()
                conn.execute(
                    "INSERT INTO acceptance_evidence(acceptance_id,candidate_id,candidate_fingerprint,authorized_by,authorization_json,created_at) VALUES(?,?,?,?,?,?)",
                    (acceptance_id, candidate_id, candidate_fingerprint, authorized_by, canonical_json(safe_authorization), stamp),
                )
                conn.execute("UPDATE candidates SET status='accepted' WHERE candidate_id=?", (candidate_id,))
                if candidate["revision_id"]:
                    conn.execute("UPDATE document_revisions SET authority_class='accepted' WHERE revision_id=?", (candidate["revision_id"],))
                result = {
                    "schema": "quillframe_candidate_acceptance_result_v1",
                    "acceptance_id": acceptance_id,
                    "candidate_id": candidate_id,
                    "candidate_fingerprint": candidate_fingerprint,
                    "authorized_by": authorized_by,
                    "authorization": safe_authorization,
                    "accepted": True,
                    "settled": False,
                    "canon_mutated": False,
                    "request_fingerprint": request_fp,
                }
                result = json.loads(canonical_json(result))
                conn.execute(
                    "INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?)",
                    ("rcpt_" + uuid.uuid4().hex, "candidate_accept", idempotency_key, canonical_json(result), stamp),
                )
                conn.commit()
                return result
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

    def reject_candidate(
        self,
        project_id: str,
        *,
        candidate_id: str,
        candidate_fingerprint: str,
        authorized_by: str,
        authorization: dict[str, Any],
        idempotency_key: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key is None or idempotency_key == "":
            raise OperationError("idempotency_required", "Candidate rejection requires an idempotency key")
        authorized_by, idempotency_key = self._validate_write_identity(
            authorized_by=authorized_by,
            idempotency_key=idempotency_key,
        )
        safe_authorization = self._validate_authorization(authorization)
        candidate_fingerprint = self._safe_scalar(
            candidate_fingerprint,
            error_factory=lambda: OperationError("invalid_args", "candidate fingerprint is invalid"),
        )
        reason = self._safe_scalar(
            reason,
            error_factory=lambda: OperationError("invalid_args", "reason is invalid"),
            allow_none=True,
        )
        assert candidate_fingerprint is not None
        request = {
            "operation": "candidate.reject",
            "project_id": project_id,
            "candidate_id": candidate_id,
            "candidate_fingerprint": candidate_fingerprint,
            "authorized_by": authorized_by,
            "authorization": safe_authorization,
            "reason": reason,
        }
        request_fp = fingerprint_text(canonical_json(request))
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                prior = self._idempotency_replay_or_conflict(
                    conn,
                    idempotency_key=idempotency_key,
                    receipt_kind="candidate_reject",
                    request_fingerprint=request_fp,
                )
                if prior is not None:
                    conn.commit()
                    return prior
                candidate = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
                if not candidate:
                    raise OperationError("candidate_not_found", "candidate does not exist")
                if candidate["content_fingerprint"] != candidate_fingerprint:
                    raise OperationError("candidate_fingerprint_mismatch", "candidate changed since Review")
                accepted = conn.execute("SELECT 1 FROM acceptance_evidence WHERE candidate_id=? LIMIT 1", (candidate_id,)).fetchone()
                if candidate["status"] == "accepted" or accepted:
                    raise OperationError("already_accepted", "Accepted Candidate cannot be rejected")
                if candidate["status"] != "review_draft" or self._candidate_revision_request_receipt(conn, candidate_id):
                    raise OperationError("stale_state", "Candidate is no longer an actionable Review Draft")
                conn.execute("UPDATE candidates SET status='rejected' WHERE candidate_id=?", (candidate_id,))
                stamp = now_iso()
                result = {
                    "schema": "quillframe_candidate_rejection_result_v1",
                    "candidate_id": candidate_id,
                    "candidate_fingerprint": candidate_fingerprint,
                    "before_status": "review_draft",
                    "status": "rejected",
                    "authorized_by": authorized_by,
                    "authorization": safe_authorization,
                    "reason": reason,
                    "canon_mutated": False,
                    "settled": False,
                    "authority": False,
                    "request_fingerprint": request_fp,
                }
                result = json.loads(canonical_json(result))
                conn.execute(
                    "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                    ("rcpt_" + uuid.uuid4().hex, candidate["run_id"], "candidate_reject", idempotency_key, canonical_json(result), stamp),
                )
                if candidate["run_id"]:
                    conn.execute(
                        "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                        ("evt_" + uuid.uuid4().hex, candidate["run_id"], "candidate_rejected", canonical_json({"candidate_id": candidate_id, "candidate_fingerprint": candidate_fingerprint}), stamp),
                    )
                conn.commit()
                return result
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

    def request_candidate_revision(
        self,
        project_id: str,
        *,
        candidate_id: str,
        candidate_fingerprint: str,
        revision_request: dict[str, Any],
        authorized_by: str,
        authorization: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        if idempotency_key is None or idempotency_key == "":
            raise OperationError("idempotency_required", "Request Revision requires an idempotency key")
        authorized_by, idempotency_key = self._validate_write_identity(
            authorized_by=authorized_by,
            idempotency_key=idempotency_key,
        )
        safe_authorization = self._validate_authorization(authorization)
        safe_revision_request = self._validate_revision_request(revision_request)
        candidate_fingerprint = self._safe_scalar(
            candidate_fingerprint,
            error_factory=lambda: OperationError("invalid_args", "candidate fingerprint is invalid"),
        )
        assert candidate_fingerprint is not None
        request = {
            "operation": "candidate.revision.request",
            "project_id": project_id,
            "candidate_id": candidate_id,
            "candidate_fingerprint": candidate_fingerprint,
            "revision_request": safe_revision_request,
            "authorized_by": authorized_by,
            "authorization": safe_authorization,
        }
        request_fp = fingerprint_text(canonical_json(request))
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                prior = self._idempotency_replay_or_conflict(
                    conn,
                    idempotency_key=idempotency_key,
                    receipt_kind="candidate_revision_request",
                    request_fingerprint=request_fp,
                )
                if prior is not None:
                    conn.commit()
                    return prior
                candidate = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
                if not candidate:
                    raise OperationError("candidate_not_found", "candidate does not exist")
                if candidate["content_fingerprint"] != candidate_fingerprint:
                    raise OperationError("candidate_fingerprint_mismatch", "candidate changed since Review")
                accepted = conn.execute("SELECT 1 FROM acceptance_evidence WHERE candidate_id=? LIMIT 1", (candidate_id,)).fetchone()
                if candidate["status"] == "accepted" or accepted:
                    raise OperationError("already_accepted", "Accepted Candidate cannot request revision")
                if candidate["status"] != "review_draft" or self._candidate_revision_request_receipt(conn, candidate_id):
                    raise OperationError("stale_state", "Candidate is no longer an actionable Review Draft")
                stamp = now_iso()
                request_id = "revreq_" + uuid.uuid4().hex
                result = {
                    "schema": "quillframe_candidate_revision_request_result_v1",
                    "revision_request_id": request_id,
                    "candidate_id": candidate_id,
                    "candidate_fingerprint": candidate_fingerprint,
                    "persisted_candidate_status": candidate["status"],
                    "effective_status": "revision_requested",
                    "revision_request": safe_revision_request,
                    "authorized_by": authorized_by,
                    "authorization": safe_authorization,
                    "next_action": {
                        "operation": "author.run.start",
                        "task_mode": "REVISE",
                        "target_ref": candidate["document_id"],
                        "requires_explicit_user_action": True,
                        "auto_started": False,
                        "source_candidate_id": candidate_id,
                        "source_candidate_fingerprint": candidate_fingerprint,
                    },
                    "canon_mutated": False,
                    "settled": False,
                    "authority": False,
                    "request_fingerprint": request_fp,
                }
                result = json.loads(canonical_json(result))
                conn.execute(
                    "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                    ("rcpt_" + uuid.uuid4().hex, candidate["run_id"], "candidate_revision_request", idempotency_key, canonical_json(result), stamp),
                )
                if candidate["run_id"]:
                    conn.execute(
                        "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                        ("evt_" + uuid.uuid4().hex, candidate["run_id"], "candidate_revision_requested", canonical_json({"candidate_id": candidate_id, "candidate_fingerprint": candidate_fingerprint, "revision_request_id": request_id}), stamp),
                    )
                conn.commit()
                return result
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

    def settlement_preflight(self, project_id: str, *, acceptance_id: str, target_ref: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            acceptance = conn.execute(
                """SELECT a.acceptance_id,a.candidate_id,a.candidate_fingerprint,c.status AS candidate_status,
                c.revision_id,c.content_fingerprint,c.document_id
                FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id
                WHERE a.acceptance_id=?""",
                (acceptance_id,),
            ).fetchone()
            if not acceptance:
                raise OperationError("acceptance_not_found", acceptance_id)
            if acceptance["candidate_status"] != "accepted" or acceptance["candidate_fingerprint"] != acceptance["content_fingerprint"]:
                raise OperationError("not_settleable", "Acceptance/Candidate binding is not settleable")
            if not acceptance["revision_id"]:
                raise OperationError("not_settleable", "Accepted Candidate has no document revision")
            revision = conn.execute(
                "SELECT revision_id,document_id,content_fingerprint,authority_class FROM document_revisions WHERE revision_id=?",
                (acceptance["revision_id"],),
            ).fetchone()
            if not revision or revision["authority_class"] != "accepted" or revision["content_fingerprint"] != acceptance["candidate_fingerprint"]:
                raise OperationError("not_settleable", "Accepted source revision is missing or no longer matches the Acceptance")
            settled = conn.execute(
                "SELECT settlement_id,status,after_fingerprint FROM settlements WHERE acceptance_id=? AND target_ref=? AND status='settled' ORDER BY created_at DESC LIMIT 1",
                (acceptance_id, target_ref),
            ).fetchone()
            if settled:
                raise OperationError("not_settleable", "Acceptance is already settled to this target", detail=dict(settled))
            current = conn.execute("SELECT content_fingerprint FROM canon_state WHERE state_key=?", (target_ref,)).fetchone()
            before = current["content_fingerprint"] if current else "absent"
        return {
            "schema": "quillframe_settlement_preflight_v1",
            "project_id": project_id,
            "acceptance_id": acceptance_id,
            "candidate_id": acceptance["candidate_id"],
            "candidate_fingerprint": acceptance["candidate_fingerprint"],
            "document_id": acceptance["document_id"],
            "revision_id": acceptance["revision_id"],
            "target_ref": target_ref,
            "expected_before_fingerprint": before,
            "current_before_fingerprint": before,
            "settleable": True,
            "mutation_performed": False,
            "canon_mutated": False,
            "authority": False,
        }

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
            try:
                conn.execute("BEGIN IMMEDIATE")
                prior = conn.execute("SELECT payload_json FROM receipts WHERE receipt_kind='settlement' AND idempotency_key=?", (idempotency_key,)).fetchone()
                if prior:
                    result = json.loads(prior["payload_json"])
                    conn.commit()
                    return result
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
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

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
            raise OperationError("unsupported_export_format", "Quillframe 1.0 supports only md and txt publication exports")
        try:
            return PublicationRecovery(self.store).build(project_id, acceptance_id, fmt)
        except PublicationRecoveryError as exc:
            raise OperationError(exc.code, exc.message) from exc

    def publication_recover(
        self,
        project_id: str,
        *,
        build_id: str | None = None,
        limit: int = 32,
    ) -> dict[str, Any]:
        try:
            return PublicationRecovery(self.store).recover(project_id, build_id=build_id, limit=limit)
        except PublicationRecoveryError as exc:
            raise OperationError(exc.code, exc.message) from exc
