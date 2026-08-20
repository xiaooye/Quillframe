"""Durable adapter for the Quillframe 1.0 novel workflow snapshot/event contract."""
from __future__ import annotations

import json
import re
from typing import Any

from persistence.quillframe_sqlite import (
    MAX_INTERNAL_REGISTRY_PROJECTS,
    ProjectLookupLimitError,
    ProjectRegistryUnavailableError,
    QuillframeStore,
    SCHEMA_VERSION,
    canonical_json,
    fingerprint_text,
    now_iso,
)

from .workflow import CHAPTER_SCOPE, NovelWorkflowEngine, WorkflowError


CHECKPOINT_KIND = "novel_workflow_v1"
EVENT_KIND = "novel_workflow_event_v1"
RUN_ID_RE = re.compile(r"\Arun_[0-9a-f]{32}\Z")
MAX_WORKFLOW_PROJECTS = MAX_INTERNAL_REGISTRY_PROJECTS


class NovelWorkflowService:
    def __init__(self, store: QuillframeStore):
        self.store = store

    @staticmethod
    def _validate_project_id(project_id: Any) -> str:
        if not isinstance(project_id, str) or not project_id.strip():
            raise WorkflowError("invalid_workflow_input", "project_id must be non-empty")
        return project_id.strip()

    @staticmethod
    def _validate_run_id(run_id: Any) -> str:
        if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
            raise WorkflowError("workflow_invalid_run_id", "run_id is invalid")
        return run_id

    @staticmethod
    def _validate_cursor(cursor: Any) -> int:
        if type(cursor) is not int or cursor < -1:
            raise WorkflowError("invalid_cursor", "cursor must be integer >= -1")
        return cursor

    @staticmethod
    def _validate_idempotency_key(idempotency_key: Any) -> str:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise WorkflowError("invalid_workflow_input", "idempotency_key must be non-empty")
        return idempotency_key.strip()

    @staticmethod
    def _canonical_event(event: dict[str, Any]) -> dict[str, Any]:
        return json.loads(canonical_json(event))

    @staticmethod
    def _latest_checkpoint(conn, run_id: str):  # noqa: ANN001
        return conn.execute(
            """SELECT run_id,checkpoint_kind,state_json,artifact_fingerprint
            FROM checkpoints WHERE run_id=? AND checkpoint_kind=?
            ORDER BY rowid DESC LIMIT 1""",
            (run_id, CHECKPOINT_KIND),
        ).fetchone()

    @classmethod
    def _restore_checkpoint_row(cls, row, *, project_id: str, run_id: str) -> NovelWorkflowEngine:  # noqa: ANN001
        if not row:
            raise WorkflowError("workflow_not_found", "workflow was not found")
        if row["run_id"] != run_id or row["checkpoint_kind"] != CHECKPOINT_KIND:
            raise WorkflowError("workflow_identity_mismatch", "workflow checkpoint identity is invalid")
        try:
            snapshot = json.loads(row["state_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise WorkflowError("workflow_snapshot_invalid", "workflow checkpoint is not valid JSON") from exc
        if not isinstance(snapshot, dict):
            raise WorkflowError("workflow_snapshot_invalid", "workflow checkpoint is not an object")
        if row["artifact_fingerprint"] != snapshot.get("snapshot_fingerprint"):
            raise WorkflowError("workflow_snapshot_invalid", "workflow checkpoint fingerprint mismatch")
        if snapshot.get("project_id") != project_id or snapshot.get("run_id") != run_id:
            raise WorkflowError("workflow_identity_mismatch", "workflow snapshot identity is invalid")
        if snapshot.get("chapter_id") != CHAPTER_SCOPE:
            raise WorkflowError("chapter_scope_violation", f"workflow is limited to {CHAPTER_SCOPE}")
        if snapshot.get("authority") is not False:
            raise WorkflowError("workflow_snapshot_invalid", "workflow snapshot must be non-authoritative")
        try:
            engine = NovelWorkflowEngine.restore(snapshot)
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError("workflow_snapshot_invalid", "workflow checkpoint could not be restored") from exc
        if engine.project_id != project_id or engine.run_id != run_id or engine.chapter_id != CHAPTER_SCOPE:
            raise WorkflowError("workflow_identity_mismatch", "restored workflow identity is invalid")
        return engine

    @classmethod
    def _event_for_idempotency(
        cls,
        engine: NovelWorkflowEngine,
        idempotency_key: str,
        *,
        action: str,
        expected_cursor: int,
    ) -> dict[str, Any] | None:
        snapshot = engine.snapshot()
        idempotency = snapshot.get("idempotency")
        if not isinstance(idempotency, dict) or idempotency_key not in idempotency:
            return None
        cursor = idempotency[idempotency_key]
        events = engine.events_after(-1)["events"]
        if type(cursor) is not int or cursor < 0 or cursor >= len(events):
            raise WorkflowError("workflow_snapshot_invalid", "workflow idempotency binding is invalid")
        event = events[cursor]
        expected_event_type = "resumed" if action == "resume" else "cancelled"
        expected_field = "resumed_from_cursor" if action == "resume" else "cancelled_from_cursor"
        payload = event.get("payload")
        if (
            event.get("event_type") != expected_event_type
            or not isinstance(payload, dict)
            or payload.get(expected_field) != expected_cursor
        ):
            raise WorkflowError("idempotency_conflict", "idempotency key is bound to a different workflow request")
        return cls._canonical_event(event)

    @classmethod
    def _save_locked(cls, conn, project_id: str, engine: NovelWorkflowEngine) -> dict[str, Any]:  # noqa: ANN001
        if project_id != engine.project_id:
            raise WorkflowError("workflow_identity_mismatch", "project_id does not match workflow")
        snapshot = engine.snapshot()
        if snapshot.get("project_id") != project_id or snapshot.get("chapter_id") != CHAPTER_SCOPE or snapshot.get("authority") is not False:
            raise WorkflowError("workflow_snapshot_invalid", "workflow snapshot identity or authority is invalid")
        checkpoint_id = f"workflow:{engine.run_id}:{engine.cursor}"
        existing = conn.execute(
            "SELECT run_id,checkpoint_kind,state_json,artifact_fingerprint FROM checkpoints WHERE checkpoint_id=?",
            (checkpoint_id,),
        ).fetchone()
        snapshot_json = canonical_json(snapshot)
        if existing:
            if (
                existing["run_id"] != engine.run_id
                or existing["checkpoint_kind"] != CHECKPOINT_KIND
                or existing["artifact_fingerprint"] != snapshot["snapshot_fingerprint"]
                or canonical_json(json.loads(existing["state_json"])) != snapshot_json
            ):
                raise WorkflowError("workflow_replay_conflict", "checkpoint cursor already binds different state")
        else:
            conn.execute(
                """INSERT INTO checkpoints(
                checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at
                ) VALUES(?,?,?,?,?,?)""",
                (
                    checkpoint_id,
                    engine.run_id,
                    CHECKPOINT_KIND,
                    snapshot_json,
                    snapshot["snapshot_fingerprint"],
                    now_iso(),
                ),
            )
        for event in engine.events_after(-1)["events"]:
            event_id = f"workflow:{engine.run_id}:event:{event['cursor']}"
            payload = canonical_json(event)
            prior = conn.execute(
                "SELECT run_id,event_kind,payload_json FROM runtime_events WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if prior:
                if (
                    prior["run_id"] != engine.run_id
                    or prior["event_kind"] != EVENT_KIND
                    or canonical_json(json.loads(prior["payload_json"])) != payload
                ):
                    raise WorkflowError("workflow_replay_conflict", "event cursor already binds different payload")
            else:
                conn.execute(
                    "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                    (event_id, engine.run_id, EVENT_KIND, payload, event["created_at"]),
                )
        return {
            "schema": "quillframe_novel_workflow_projection_v1",
            "project_id": project_id,
            "run_id": engine.run_id,
            "chapter_id": engine.chapter_id,
            "stage": engine.stage,
            "status": engine.status,
            "cursor": engine.cursor,
            "snapshot_fingerprint": snapshot["snapshot_fingerprint"],
            "authority": False,
        }

    def save(self, project_id: str, engine: NovelWorkflowEngine) -> dict[str, Any]:
        project_id = self._validate_project_id(project_id)
        if not isinstance(engine, NovelWorkflowEngine):
            raise WorkflowError("invalid_workflow_input", "engine is invalid")
        if project_id != engine.project_id:
            raise WorkflowError("workflow_identity_mismatch", "project_id does not match workflow")
        try:
            with self.store.open_project(project_id) as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    projection = self._save_locked(conn, project_id, engine)
                    conn.commit()
                    return projection
                except WorkflowError:
                    if conn.in_transaction:
                        conn.rollback()
                    raise
                except Exception as exc:
                    if conn.in_transaction:
                        conn.rollback()
                    raise WorkflowError("workflow_persistence_failed", "workflow persistence failed") from exc
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError("workflow_project_unavailable", "workflow project is unavailable") from exc

    def load(self, project_id: str, run_id: str) -> NovelWorkflowEngine:
        project_id = self._validate_project_id(project_id)
        run_id = self._validate_run_id(run_id)
        try:
            with self.store.open_project(project_id) as conn:
                row = self._latest_checkpoint(conn, run_id)
                return self._restore_checkpoint_row(row, project_id=project_id, run_id=run_id)
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError("workflow_project_unavailable", "workflow project is unavailable") from exc

    def resolve_project(self, run_id: str) -> str:
        if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
            raise WorkflowError("workflow_invalid_run_id", "run_id is invalid")
        matches: list[str] = []
        try:
            project_ids = self.store.iter_project_ids_internal(
                page_size=100,
                max_projects=MAX_WORKFLOW_PROJECTS,
            )
            for project_id in project_ids:
                try:
                    with self.store.open_project(project_id) as conn:
                        identity_rows = conn.execute(
                            "SELECT project_id,title,language,project_schema_version FROM project_identity"
                        ).fetchall()
                        if len(identity_rows) != 1:
                            raise ValueError("project identity is not singular")
                        identity = identity_rows[0]
                        if (
                            identity["project_id"] != project_id
                            or not isinstance(identity["title"], str)
                            or not identity["title"].strip()
                            or not isinstance(identity["language"], str)
                            or not identity["language"].strip()
                            or identity["project_schema_version"] != SCHEMA_VERSION
                        ):
                            raise ValueError("project identity is not canonical")
                        row = conn.execute(
                            "SELECT 1 FROM checkpoints WHERE run_id=? AND checkpoint_kind=? LIMIT 1",
                            (run_id, CHECKPOINT_KIND),
                        ).fetchone()
                except Exception as exc:
                    raise WorkflowError(
                        "workflow_project_unavailable",
                        f"registered project {project_id} is unavailable",
                    ) from exc
                if row:
                    matches.append(project_id)
        except ProjectLookupLimitError as exc:
            raise WorkflowError(
                "workflow_project_lookup_bounded",
                "project registry lookup exceeded its bounded limit",
            ) from exc
        except ProjectRegistryUnavailableError as exc:
            raise WorkflowError(
                "workflow_project_registry_unavailable",
                "canonical project registry is unavailable",
            ) from exc
        if len(matches) != 1:
            raise WorkflowError(
                "workflow_identity_ambiguous" if matches else "workflow_not_found",
                "workflow resolves to multiple projects" if matches else "workflow was not found",
            )
        return matches[0]

    def start(
        self,
        *,
        project_id: str,
        run_id: str,
        chapter_id: str,
        author_profile: str,
    ) -> dict[str, Any]:
        engine = NovelWorkflowEngine.start(
            project_id=project_id,
            run_id=run_id,
            chapter_id=chapter_id,
            author_profile=author_profile,
        )
        return self.save(project_id, engine)

    def events(self, *, run_id: str, cursor: int) -> dict[str, Any]:
        run_id = self._validate_run_id(run_id)
        cursor = self._validate_cursor(cursor)
        project_id = self.resolve_project(run_id)
        return self.load(project_id, run_id).events_after(cursor)

    def _mutate_cursor_bound(
        self,
        *,
        project_id: str,
        run_id: str,
        cursor: int,
        idempotency_key: str,
        action: str,
        user_authorized: bool | None = None,
    ) -> dict[str, Any]:
        project_id = self._validate_project_id(project_id)
        run_id = self._validate_run_id(run_id)
        cursor = self._validate_cursor(cursor)
        idempotency_key = self._validate_idempotency_key(idempotency_key)
        if action not in {"resume", "cancel"}:
            raise WorkflowError("invalid_workflow_input", "workflow mutation is invalid")
        if action == "cancel" and user_authorized is not True:
            raise WorkflowError("authorization_required", "cancel requires explicit user action")
        try:
            with self.store.open_project(project_id) as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    row = self._latest_checkpoint(conn, run_id)
                    engine = self._restore_checkpoint_row(row, project_id=project_id, run_id=run_id)
                    replay = self._event_for_idempotency(
                        engine,
                        idempotency_key,
                        action=action,
                        expected_cursor=cursor,
                    )
                    if replay is not None:
                        conn.commit()
                        return replay
                    if cursor != engine.cursor:
                        raise WorkflowError("cursor_conflict", "workflow cursor does not match the latest checkpoint")
                    if action == "resume":
                        event = engine.resume(expected_cursor=cursor, idempotency_key=idempotency_key)
                    else:
                        event = engine.cancel(
                            expected_cursor=cursor,
                            idempotency_key=idempotency_key,
                            user_authorized=True,
                        )
                    self._save_locked(conn, project_id, engine)
                    conn.commit()
                    return self._canonical_event(event)
                except WorkflowError:
                    if conn.in_transaction:
                        conn.rollback()
                    raise
                except Exception as exc:
                    if conn.in_transaction:
                        conn.rollback()
                    raise WorkflowError("workflow_persistence_failed", "workflow persistence failed") from exc
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError("workflow_project_unavailable", "workflow project is unavailable") from exc

    def resume(
        self,
        *,
        project_id: str,
        run_id: str,
        cursor: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._mutate_cursor_bound(
            project_id=project_id,
            run_id=run_id,
            cursor=cursor,
            idempotency_key=idempotency_key,
            action="resume",
        )

    def cancel(
        self,
        *,
        project_id: str,
        run_id: str,
        cursor: int,
        idempotency_key: str,
        user_authorized: bool,
    ) -> dict[str, Any]:
        return self._mutate_cursor_bound(
            project_id=project_id,
            run_id=run_id,
            cursor=cursor,
            idempotency_key=idempotency_key,
            action="cancel",
            user_authorized=user_authorized,
        )
