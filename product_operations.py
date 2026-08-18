#!/usr/bin/env python3
"""Quillframe 0.9 product-facing Core operations.

This module exposes authoring/product projections that were previously either
missing from the Host Bridge or reconstructed in browser code. It is still Core:
all durable state is SQLite-native and every authority transition remains in the
existing operation-specific Core implementation.
"""
from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path
from typing import Any

from agent_runtime.runtime import QuillframeAgentRuntime
from model_runtime.secrets import MemorySecretStore
from persistence.portable_project import MAX_PORTABLE_BYTES, PortableProjectService
from persistence.quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso


class ProductOperationError(RuntimeError):
    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


class ProductOperations:
    """Thin public product boundary over canonical Quillframe Core state."""

    def __init__(self, store: QuillframeStore | None = None) -> None:
        self.store = store or QuillframeStore()
        self.portable = PortableProjectService(self.store)
        # Web/local-host default is session/process memory only. SQLite receives
        # opaque refs through Model Runtime, never credential values.
        self._secrets = MemorySecretStore()
        self.agent_runtime = QuillframeAgentRuntime(secret_store=self._secrets, store=self.store)

    def project_list(self) -> dict[str, Any]:
        self.store.initialize_global()
        with self.store._connect(self.store.global_db) if hasattr(self.store, "_connect") else _global_connection(self.store) as conn:  # pragma: no cover - compatibility guard
            rows = [dict(row) for row in conn.execute(
                "SELECT project_id,title,language,project_schema_version,registered_at,last_opened_at FROM project_registry ORDER BY last_opened_at DESC, project_id"
            )]
        return {"schema": "quillframe_project_list_v1", "items": rows, "authority": False}

    def project_list_portable(self) -> dict[str, Any]:
        # Avoid reliance on private Store helpers: model repository already uses
        # the same SQLite pragmas; here only a read projection is needed.
        import sqlite3
        self.store.initialize_global()
        with sqlite3.connect(self.store.global_db, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(
                "SELECT project_id,title,language,project_schema_version,registered_at,last_opened_at FROM project_registry ORDER BY last_opened_at DESC, project_id"
            )]
        return {"schema": "quillframe_project_list_v1", "items": rows, "authority": False}

    def project_delete(self, project_id: str, *, confirm_project_id: str, user_authorized: bool, backup_first: bool = True) -> dict[str, Any]:
        if not user_authorized or confirm_project_id != project_id:
            raise ProductOperationError("authorization_required", "project.delete requires explicit user authorization and exact project id confirmation")
        loc = self.store.location(project_id)
        if not loc.directory.exists():
            return {"schema": "quillframe_project_delete_result_v1", "project_id": project_id, "deleted": False, "already_absent": True, "authority": False}
        backup_ref = None
        if backup_first:
            backup_ref = self.store.backup_project(project_id).name
        shutil.rmtree(loc.directory)
        import sqlite3
        self.store.initialize_global()
        with sqlite3.connect(self.store.global_db, timeout=5.0) as conn:
            conn.execute("DELETE FROM project_registry WHERE project_id=?", (project_id,))
            conn.commit()
        return {"schema": "quillframe_project_delete_result_v1", "project_id": project_id, "deleted": True, "backup_ref": backup_ref, "authority": False}

    def project_export(self, project_id: str) -> dict[str, Any]:
        return self.portable.export_project(project_id)

    def artifact_read(self, artifact_ref: str) -> dict[str, Any]:
        path = self.portable.resolve_export_artifact(artifact_ref)
        payload = path.read_bytes()
        if len(payload) > MAX_PORTABLE_BYTES:
            raise ProductOperationError("artifact_too_large", "portable project exceeds product transfer limit")
        return {
            "schema": "quillframe_artifact_read_result_v1",
            "artifact_ref": artifact_ref,
            "file_name": path.name,
            "media_type": "application/vnd.quillframe.project+zip",
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "byte_size": len(payload),
            "authority": False,
        }

    def artifact_upload(self, file_name: str, payload_base64: str) -> dict[str, Any]:
        try:
            payload = base64.b64decode(payload_base64, validate=True)
        except Exception as exc:
            raise ProductOperationError("invalid_base64", "artifact payload is not valid base64") from exc
        ref = self.portable.stage_import_payload(file_name, payload)
        return {"schema": "quillframe_artifact_upload_result_v1", "artifact_ref": ref, "file_name": file_name, "byte_size": len(payload), "authority": False}

    def project_import(self, artifact_ref: str, *, replace: bool = False) -> dict[str, Any]:
        path = self.portable.resolve_import_artifact(artifact_ref)
        try:
            return self.portable.import_project(path, replace=replace)
        finally:
            path.unlink(missing_ok=True)

    def document_list(self, project_id: str, document_kind: str | None = None) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            sql = """SELECT d.document_id,d.story_node_id,d.document_kind,d.title,d.created_at,
                r.revision_id AS latest_revision_id,r.content_fingerprint AS latest_content_fingerprint,
                r.authority_class AS latest_authority_class,r.created_at AS latest_revision_at
                FROM documents d LEFT JOIN document_revisions r ON r.revision_id=(
                  SELECT revision_id FROM document_revisions x WHERE x.document_id=d.document_id ORDER BY x.created_at DESC,x.rowid DESC LIMIT 1
                )"""
            params: tuple[Any, ...] = ()
            if document_kind:
                sql += " WHERE d.document_kind=?"
                params = (document_kind,)
            sql += " ORDER BY d.created_at,d.document_id"
            items = [dict(row) for row in conn.execute(sql, params)]
        return {"schema": "quillframe_document_list_v1", "project_id": project_id, "items": items, "authority": False}

    def document_get(self, project_id: str, document_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            document = conn.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
            if not document:
                raise ProductOperationError("document_not_found", document_id)
            revision = self.store.latest_revision(conn, document_id)
        return {
            "schema": "quillframe_document_projection_v1",
            "project_id": project_id,
            "document": dict(document),
            "latest_revision": dict(revision) if revision else None,
            "authority": False,
        }

    def revision_list(self, project_id: str, document_id: str, limit: int = 100) -> dict[str, Any]:
        bounded = max(1, min(int(limit), 500))
        with self.store.open_project(project_id) as conn:
            rows = [dict(row) for row in conn.execute(
                "SELECT revision_id,document_id,parent_revision_id,content_fingerprint,created_at,source,authority_class,provenance_json FROM document_revisions WHERE document_id=? ORDER BY created_at DESC,rowid DESC LIMIT ?",
                (document_id, bounded),
            )]
        for row in rows:
            row["provenance"] = json.loads(row.pop("provenance_json") or "{}")
        return {"schema": "quillframe_document_revision_list_v1", "project_id": project_id, "document_id": document_id, "items": rows, "authority": False}

    def revision_restore(self, project_id: str, document_id: str, revision_id: str, *, expected_parent_revision_id: str | None, source: str = "user_restore") -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            row = conn.execute("SELECT content FROM document_revisions WHERE document_id=? AND revision_id=?", (document_id, revision_id)).fetchone()
            if not row:
                raise ProductOperationError("revision_not_found", revision_id)
        result = self.store.save_revision(
            project_id,
            document_id,
            row["content"],
            expected_parent_revision_id=expected_parent_revision_id,
            source=source,
            authority_class="proposal",
            provenance={"restored_from_revision_id": revision_id},
        )
        return {"schema": "quillframe_document_revision_restore_result_v1", "document_id": document_id, "restored_from_revision_id": revision_id, **result, "authority_class": "proposal", "authority": False}

    def story_projection(self, project_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            nodes = [dict(r) for r in conn.execute("SELECT * FROM story_nodes ORDER BY parent_id,ordinal,node_id")]
            characters = [dict(r) for r in conn.execute("SELECT * FROM characters ORDER BY name,character_id")]
            relationships = [dict(r) for r in conn.execute("SELECT * FROM relationships ORDER BY relationship_id")]
            world = [dict(r) for r in conn.execute("SELECT * FROM world_entities ORDER BY entity_type,name,entity_id")]
            timeline = [dict(r) for r in conn.execute("SELECT * FROM timeline_events ORDER BY story_order,event_id")]
            claims = [dict(r) for r in conn.execute("SELECT * FROM canon_claims ORDER BY authority_class,subject_ref,predicate,claim_id")]
        return {"schema": "quillframe_story_projection_v1", "project_id": project_id, "story_nodes": nodes, "characters": characters, "relationships": relationships, "world_entities": world, "timeline_events": timeline, "canon_claims": claims, "authority": False}

    def plan_projection(self, project_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            plans = [dict(r) for r in conn.execute("SELECT * FROM plans ORDER BY updated_at DESC,plan_id")]
            cards = [dict(r) for r in conn.execute("SELECT * FROM scene_cards ORDER BY plan_id,scene_card_id")]
        for plan in plans:
            plan["plan"] = json.loads(plan.pop("plan_json") or "{}")
        for card in cards:
            for key in ("plotlines_json", "dependencies_json", "card_json"):
                card[key.removesuffix("_json")] = json.loads(card.pop(key) or ("[]" if key != "card_json" else "{}"))
        return {"schema": "quillframe_plan_projection_v1", "project_id": project_id, "plans": plans, "scene_cards": cards, "authority": False}

    def candidate_list(self, project_id: str, limit: int = 100) -> dict[str, Any]:
        bounded = max(1, min(int(limit), 500))
        with self.store.open_project(project_id) as conn:
            rows = [dict(r) for r in conn.execute(
                """SELECT c.*,a.acceptance_id,a.created_at AS accepted_at,
                (SELECT status FROM settlements s WHERE s.acceptance_id=a.acceptance_id ORDER BY s.created_at DESC LIMIT 1) AS settlement_status
                FROM candidates c LEFT JOIN acceptance_evidence a ON a.candidate_id=c.candidate_id
                ORDER BY c.created_at DESC LIMIT ?""", (bounded,)
            )]
        return {"schema": "quillframe_candidate_list_v1", "project_id": project_id, "items": rows, "authority": False}

    def candidate_get(self, project_id: str, candidate_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            candidate = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
            if not candidate:
                raise ProductOperationError("candidate_not_found", candidate_id)
            revision = conn.execute("SELECT * FROM document_revisions WHERE revision_id=?", (candidate["revision_id"],)).fetchone() if candidate["revision_id"] else None
            reviews = [dict(r) for r in conn.execute("SELECT * FROM review_evidence WHERE candidate_id=? ORDER BY created_at", (candidate_id,))]
            acceptance = conn.execute("SELECT * FROM acceptance_evidence WHERE candidate_id=? ORDER BY created_at DESC LIMIT 1", (candidate_id,)).fetchone()
            settlements = [dict(r) for r in conn.execute("SELECT * FROM settlements WHERE acceptance_id=? ORDER BY created_at", (acceptance["acceptance_id"],))] if acceptance else []
        for review in reviews:
            review["result"] = json.loads(review.pop("result_json") or "{}")
        return {"schema": "quillframe_candidate_projection_v1", "project_id": project_id, "candidate": dict(candidate), "revision": dict(revision) if revision else None, "reviews": reviews, "acceptance": dict(acceptance) if acceptance else None, "settlements": settlements, "authority": False}

    def model_connect(self, endpoint: str, access_token: str) -> dict[str, Any]:
        if not access_token.strip():
            raise ProductOperationError("invalid_args", "access_token is required")
        result = self.agent_runtime.connect(endpoint, access_token)
        result["credential_persistence"] = "session_only"
        result["credential_value_persisted"] = False
        return result

    def model_list(self) -> dict[str, Any]:
        result = self.agent_runtime.list_model_services()
        for item in result.get("items", []):
            service_id = item.get("service_id")
            present = False
            if service_id and self.agent_runtime.repository is not None:
                try:
                    internal = self.agent_runtime.repository.get_internal(str(service_id))
                    present = self._secrets.present(internal.get("credential_ref"))
                except Exception:
                    present = False
            item["credential_present"] = present
            item["credential_persistence"] = "session_only"
        return result

    def model_get(self, service_id: str) -> dict[str, Any]:
        result = self.agent_runtime.get_model_service(service_id)
        present = False
        if self.agent_runtime.repository is not None:
            try:
                internal = self.agent_runtime.repository.get_internal(service_id)
                present = self._secrets.present(internal.get("credential_ref"))
            except Exception:
                present = False
        result["credential_present"] = present
        result["credential_persistence"] = "session_only"
        return result

    def inspector_table(self, project_id: str, table: str, order_by: str = "rowid DESC", limit: int = 100) -> dict[str, Any]:
        allowed = {
            "sessions", "runs", "checkpoints", "context_manifests", "receipts",
            "candidates", "learning_evidence", "review_evidence", "settlements",
        }
        if table not in allowed:
            raise ProductOperationError("unsupported_projection", table)
        bounded = max(1, min(int(limit), 500))
        safe_order = {
            "sessions": "updated_at DESC", "runs": "updated_at DESC", "checkpoints": "created_at DESC",
            "context_manifests": "created_at DESC", "receipts": "created_at DESC", "candidates": "created_at DESC",
            "learning_evidence": "created_at DESC", "review_evidence": "created_at DESC", "settlements": "created_at DESC",
        }[table]
        with self.store.open_project(project_id) as conn:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY {safe_order} LIMIT ?", (bounded,))]
        for row in rows:
            for key in list(row):
                normalized = key.lower()
                if any(term in normalized for term in ("secret", "credential", "provider_session")):
                    row.pop(key, None)
        return {"schema": "quillframe_inspector_projection_v1", "kind": table, "project_id": project_id, "items": rows, "authority": False}


def _global_connection(store: QuillframeStore):
    import sqlite3
    store.initialize_global()
    conn = sqlite3.connect(store.global_db, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn
