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
PROJECT_SCOPE = "novel"

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
            "scope": PROJECT_SCOPE,
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
                "scope": PROJECT_SCOPE,
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
        }

    @staticmethod
    def _native_fingerprint(manifest: dict[str, Any]) -> str:
        return "sha256:" + hashlib.sha256(
            canonical_json(manifest).encode("utf-8")
        ).hexdigest()

    def project_create(self, project_id: str, title: str, language: str = "zh-CN") -> dict[str, Any]:
        self.store.create_native_project(project_id, title, language)
        context = self.project_inspect(project_id)
        return {"schema": "quillframe_project_create_result_v1_0", "manifest": context["manifest"],
                "manifest_fingerprint": context["manifest_fingerprint"], "scope": PROJECT_SCOPE,
                "data_boundary": ".quillframe/data", "created": True, "authority": False}

    def novel(self):
        from quillframe.novel import NovelOperations
        return NovelOperations(self.store)

    def project_learning(self):
        from learning.project_learning import ProjectLearning
        return ProjectLearning(learning_db=self.store.root / "learning" / "author.sqlite",
                               runtime_db=self.store.root / "runtime" / "learning-intake.sqlite")

    def learning(self):
        from quillframe.project_learning import ProjectLearningOperations
        return ProjectLearningOperations(self.store, self.project_learning())

    def chapter_list(self, project_id: str) -> dict[str, Any]:
        return self.novel().chapter_list(project_id)

    def chapter_create(self, project_id: str, **args: Any) -> dict[str, Any]:
        return self.novel().chapter_create(project_id, **args)

    def plan_inspect(self, project_id: str, *, target_ref: str | None = None) -> dict[str, Any]:
        return self.novel().plan_inspect(project_id, target_ref=target_ref)

    def plan_save(self, project_id: str, **args: Any) -> dict[str, Any]:
        return self.novel().plan_save(project_id, **args)

    def story_inspect(self, project_id: str) -> dict[str, Any]:
        return self.novel().story_inspect(project_id)

    @classmethod
    def _revision_is_visible(cls, conn, revision: dict[str, Any]) -> bool:
        if not isinstance(revision.get("content"), str) or fingerprint_text(revision["content"]) != revision.get("content_fingerprint"):
            return False
        candidates = conn.execute("SELECT * FROM candidates WHERE revision_id=?", (revision["revision_id"],)).fetchall()
        if revision.get("source") != "production_runtime" and not candidates:
            return True
        for candidate in candidates:
            try:
                cls._validated_production_release(conn, dict(candidate))
                return True
            except OperationError:
                continue
        return False

    def document_open(self, project_id: str, document_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            document = conn.execute("SELECT document_id,story_node_id,document_kind,title,created_at FROM documents WHERE document_id=?", (document_id,)).fetchone()
            if document is None:
                raise OperationError("document_not_found", "document is not registered")
            latest = None
            for row in conn.execute("SELECT * FROM document_revisions WHERE document_id=? ORDER BY created_at DESC,rowid DESC", (document_id,)):
                revision = dict(row)
                if self._revision_is_visible(conn, revision):
                    latest = revision
                    latest["provenance"] = json.loads(latest.pop("provenance_json") or "{}")
                    break
        return {"schema": "quillframe_document_projection_v1", "project_id": project_id,
                "document": dict(document), "latest_revision": latest, "authority": False}

    def revision_compare(self, project_id: str, left_revision_id: str, right_revision_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            for revision_id in (left_revision_id, right_revision_id):
                row = conn.execute("SELECT * FROM document_revisions WHERE revision_id=?", (revision_id,)).fetchone()
                if row is None or not self._revision_is_visible(conn, dict(row)):
                    raise OperationError("revision_not_visible", "revision is not available through the Core release boundary")
        return self.store.compare_revisions(project_id, left_revision_id, right_revision_id)

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
            if (not candidate.get("revision_id") or candidate.get("revision_fingerprint") != candidate.get("content_fingerprint")
                    or not isinstance(candidate.get("candidate_content"), str)
                    or fingerprint_text(candidate["candidate_content"]) != candidate.get("content_fingerprint")):
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
            if (not c.get("revision_id") or c.get("revision_fingerprint") != c.get("content_fingerprint")
                    or not isinstance(c.get("candidate_content"), str)
                    or fingerprint_text(c["candidate_content"]) != c.get("content_fingerprint")):
                raise OperationError("stale_review", "Candidate revision no longer matches its review fingerprint")
            release = self._validated_production_release(conn, c)
            parent = None
            if c.get("parent_revision_id"):
                row = conn.execute(
                    "SELECT * FROM document_revisions WHERE revision_id=?",
                    (c["parent_revision_id"],),
                ).fetchone()
                parent = dict(row) if row and self._revision_is_visible(conn, dict(row)) else None
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
            reader_report = independent.get("reader_engagement")
            if isinstance(reader_report, dict):
                reader = by_mechanism["reader_engagement"]
                reader["judgment"] = {**(reader.get("judgment") or {}),
                    **{key: reader_report[key] for key in ("report", "strongest_positive", "strongest_problem", "evidence_refs") if key in reader_report}}
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
        if "reader_positioning" in payload:
            from production_runtime.contracts import ProductionRunError
            from production_runtime.reading_positioning import validate_reader_positioning
            try:
                validate_reader_positioning(payload["reader_positioning"])
            except ProductionRunError as exc:
                raise OperationError(exc.code, str(exc), detail=exc.detail) from exc
        if "repair_source" in payload and task_mode != "REVISE":
            raise OperationError("repair_source_requires_revise", "only REVISE may bind an internal repair source")
        if "repair_source" in payload and {
            "candidate_text", "candidate_fingerprint", "reader_binding", "self_audit_binding",
            "reader_assessment", "semantic_rule_assessment", "qualification_receipt",
            "qualification_status", "repair_preservation", "repair_lineage", "source_request",
            "source_target_context", "source_fingerprint", "status", "pass",
            "source_release", "source_kind", "author_revision_request", "author_revision_request_fingerprint",
        }.intersection(payload):
            raise OperationError("repair_source_invalid", "repair evidence must come from Core, not the author payload")
        from quillframe.novel import resolve_chapter_target, bind_prior_dependencies
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
                target = resolve_chapter_target(conn, payload.get("chapter_id"), payload.get("document_id"), target_ref)
                repair_source = None
                if "repair_source" in payload:
                    from production_runtime.contracts import ProductionRunError
                    from production_runtime.repair_source import freeze_repair_source
                    try:
                        repair_source = freeze_repair_source(conn, source_ref=payload["repair_source"], target=target)
                    except ProductionRunError as exc:
                        raise OperationError(exc.code, str(exc), detail=exc.detail) from exc
                source_author_model = None
                if repair_source is not None:
                    source_author_model = repair_source["source_target_context"].get("author_model")
                    if not isinstance(source_author_model, dict) or not isinstance(source_author_model.get("selected_hypothesis_ids"), list):
                        raise OperationError("repair_objective_changed", "repair source has no valid frozen preference selection")
                inherited_selection = source_author_model["selected_hypothesis_ids"] if source_author_model is not None else []
                selected = payload.get("selected_preference_ids", inherited_selection)
                if not isinstance(selected, list) or len(selected) > 100 or any(not isinstance(value, str) or not value for value in selected) or len(set(selected)) != len(selected):
                    raise OperationError("invalid_args", "selected_preference_ids must contain unique preference IDs")
                if source_author_model is not None and selected != inherited_selection:
                    raise OperationError("repair_objective_changed", "repair must retain its source preference selection")
                try:
                    author_model = self.project_learning().project_context(project_id=project_id, selected_hypothesis_ids=selected)
                except ValueError as exc:
                    if source_author_model is not None:
                        raise OperationError("repair_objective_changed", "a source preference is no longer available for this repair") from exc
                    raise
                target_payload = payload
                if source_author_model is not None:
                    preference_keys = ("selected_hypothesis_ids", "active_preferences")
                    if {key: author_model.get(key) for key in preference_keys} != {key: source_author_model.get(key) for key in preference_keys}:
                        raise OperationError("repair_objective_changed", "the selected source preferences changed before repair registration")
                    # Keep the caller request/idempotency fingerprint intact;
                    # the derived target records the actual inherited selection.
                    target_payload = {**payload, "selected_preference_ids": list(selected)}
                    inherited_positioning = repair_source["source_target_context"].get("payload", {}).get("reader_positioning")
                    if (repair_source.get("source_kind") != "author_revision"
                            and "reader_positioning" in payload and payload["reader_positioning"] != inherited_positioning):
                        raise OperationError("repair_objective_changed", "internal repair must retain its source reading positioning")
                    if inherited_positioning is not None and "reader_positioning" not in target_payload:
                        from production_runtime.reading_positioning import validate_reader_positioning
                        target_payload["reader_positioning"] = validate_reader_positioning(inherited_positioning)
                if session_id is not None:
                    session = conn.execute("SELECT session_id FROM sessions WHERE session_id=?", (session_id,)).fetchone()
                    if not session:
                        raise OperationError("unknown_session", "session_id does not exist")
                run_id = "run_" + uuid.uuid4().hex
                stamp = now_iso()
                if session_id is None:
                    # Bootstrap only after replay resolution, in the same
                    # transaction as the run. The request fingerprint remains
                    # bound to the caller's omitted session, not this identity.
                    session_id = "ses_manager_" + uuid.uuid4().hex
                    conn.execute(
                        "INSERT INTO sessions(session_id,status,version,created_at,updated_at) VALUES(?,?,1,?,?)",
                        (session_id, "running", stamp, stamp),
                    )
                conn.execute(
                    "INSERT INTO runs(run_id,session_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (run_id, session_id, task_mode, target_ref, "awaiting_semantic", request_fp, stamp, stamp),
                )
                target_context = {"schema": "quillframe_author_run_request_v1", **target,
                                  "task_mode": task_mode, "target_ref": target_ref, "payload": target_payload,
                                  "author_model": author_model}
                conn.execute(
                    "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) VALUES(?,?,'author_run_request',?,?,?)",
                    ("request:" + run_id, run_id, canonical_json(target_context), fingerprint_text(canonical_json(target_context)), stamp),
                )
                if repair_source is not None:
                    conn.execute(
                        "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) VALUES(?,?,'production_repair_source',?,?,?)",
                        ("repair-source:" + run_id, run_id, canonical_json(repair_source), repair_source["source_fingerprint"], stamp),
                    )
                if task_mode in {"DRAFT", "REVISE"}:
                    bind_prior_dependencies(conn, target, run_id)
                event_id = "evt_" + uuid.uuid4().hex
                conn.execute(
                    "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                    (event_id, run_id, "author_run_requested", canonical_json({"task_mode": task_mode, "target_ref": target_ref}), stamp),
                )
                result = {
                    "schema": "quillframe_author_run_start_result_v1",
                    "run_id": run_id,
                    "chapter_id": target["chapter_id"],
                    "document_id": target["document_id"],
                    "session_id": session_id,
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
                        "payload": {
                            "document_id": candidate["document_id"],
                            "repair_source": {
                                "source_candidate_id": candidate_id,
                                "revision_request_id": request_id,
                                "expected_candidate_fingerprint": candidate_fingerprint,
                            },
                        },
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
        from quillframe.settlement import ChapterSettlement
        return ChapterSettlement(self.store).preflight(project_id, acceptance_id=acceptance_id, target_ref=target_ref)

    def settle(self, project_id: str, *, acceptance_id: str, target_ref: str,
               expected_before_fingerprint: str, user_authorized: bool, idempotency_key: str,
               expected_preflight_fingerprint: str | None = None) -> dict[str, Any]:
        from quillframe.settlement import ChapterSettlement
        return ChapterSettlement(self.store).settle(project_id, acceptance_id=acceptance_id, target_ref=target_ref,
            expected_before_fingerprint=expected_before_fingerprint, user_authorized=user_authorized,
            idempotency_key=idempotency_key, expected_preflight_fingerprint=expected_preflight_fingerprint)

    def reader_expectations_inspect(self, project_id: str, *, current_order: int | None = None) -> dict[str, Any]:
        from quality.reader_expectation import inspect_project
        with self.store.open_project(project_id) as conn:
            return {**inspect_project(conn, current_order=current_order), 'project_id': project_id}

    def reader_expectations_apply(self, project_id: str, **args: Any) -> dict[str, Any]:
        from quality.reader_expectation import apply_observation
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute('BEGIN IMMEDIATE')
                result = apply_observation(conn, **args)
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

    def publication_artifact_get(self, project_id: str, *, build_id: str) -> dict[str, Any]:
        try:
            return PublicationRecovery(self.store).artifact(project_id, build_id)
        except PublicationRecoveryError as exc:
            raise OperationError(exc.code, exc.message) from exc

    def publication_collection_build(self, project_id: str, *, acceptance_ids: list[str], fmt: str = 'md',
                                     idempotency_key: str, user_authorized: bool) -> dict[str, Any]:
        try:
            return PublicationRecovery(self.store).build_collection(project_id, acceptance_ids, fmt,
                idempotency_key=idempotency_key, user_authorized=user_authorized)
        except PublicationRecoveryError as exc:
            raise OperationError(exc.code, exc.message) from exc
