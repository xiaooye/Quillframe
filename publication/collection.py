"""Ordered novel publication using the shared native file recovery protocol."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from persistence.quillframe_sqlite import canonical_json, fingerprint_bytes, now_iso
from .recovery import MAX_ARTIFACT_BYTES, PublicationRecovery, PublicationRecoveryError, _Plan


MAX_COLLECTION_CHAPTERS = 10_000


@dataclass(frozen=True)
class _CollectionSource:
    project_id: str
    source_key: str
    source_fingerprint: str
    content: str


def _acceptance_ids(value: Any) -> list[str]:
    if (
        not isinstance(value, list) or not value or len(value) > MAX_COLLECTION_CHAPTERS
        or any(not isinstance(item, str) or not item or len(item) > 128 for item in value)
        or len(set(value)) != len(value)
    ):
        raise PublicationRecoveryError("publication_source_invalid")
    return value


class CollectionPublicationRecovery(PublicationRecovery):
    attempts_table = "publication_collection_attempts"
    builds_table = "publication_collection_builds"
    source_column = "source_acceptance_ids_json"
    compiler_contract = "quillframe_core_publication_collection_text_v1"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._request: tuple[str, str] | None = None

    def _source(self, conn: Any, project_id: str, source_key: str, *, require_current: bool = True) -> _CollectionSource:
        try:
            ids = _acceptance_ids(json.loads(source_key))
        except (TypeError, ValueError) as exc:
            raise PublicationRecoveryError("publication_source_invalid") from exc
        if canonical_json(ids) != source_key:
            raise PublicationRecoveryError("publication_source_invalid")
        nodes = {row["node_id"]: dict(row) for row in conn.execute("SELECT node_id,parent_id,kind,ordinal FROM story_nodes")}

        chapters: list[str] = []
        contents: list[str] = []
        bindings: list[dict[str, Any]] = []
        byte_count = 0
        for acceptance_id in ids:
            source = super()._source(conn, project_id, acceptance_id)
            document = conn.execute("SELECT story_node_id,document_kind FROM documents WHERE document_id=?", (source.document_id,)).fetchone()
            chapter_id = document["story_node_id"] if document else None
            if (
                not document or document["document_kind"] != "manuscript"
                or chapter_id not in nodes or nodes[chapter_id]["kind"] != "chapter"
                or chapter_id in chapters
            ):
                raise PublicationRecoveryError("publication_source_invalid")
            if require_current:
                latest = conn.execute(
                    """SELECT a.acceptance_id FROM acceptance_evidence a
                    JOIN candidates c ON c.candidate_id=a.candidate_id
                    WHERE c.document_id=?
                    ORDER BY a.created_at DESC,a.rowid DESC LIMIT 1""", (source.document_id,),
                ).fetchone()
                head = conn.execute("SELECT value_json,authority_class,content_fingerprint FROM canon_state WHERE state_key=?", (f"chapter:{chapter_id}",)).fetchone()
                settled = conn.execute("SELECT 1 FROM settlements WHERE acceptance_id=? AND target_ref=? AND status='settled' AND after_fingerprint=?", (acceptance_id, f"chapter:{chapter_id}", head["content_fingerprint"] if head else None)).fetchone()
                if not latest or latest["acceptance_id"] != acceptance_id or not head or not settled:
                    raise PublicationRecoveryError("publication_source_changed")
                try:
                    state = json.loads(head["value_json"])
                except (TypeError, ValueError) as exc:
                    raise PublicationRecoveryError("publication_source_invalid") from exc
                expected = {
                    "acceptance_id": acceptance_id, "document_id": source.document_id,
                    "revision_id": source.revision_id, "content_fingerprint": source.source_fingerprint,
                    "candidate_id": source.candidate_id,
                }
                if (
                    head["authority_class"] not in {"accepted", "locked"}
                    or not isinstance(state, dict) or any(state.get(key) != value for key, value in expected.items())
                    or fingerprint_bytes(canonical_json(state).encode("utf-8")) != head["content_fingerprint"]
                ):
                    raise PublicationRecoveryError("publication_source_changed")
                dependencies = conn.execute(
                    """SELECT d.status,d.source_fingerprint,s.content_fingerprint AS current_fingerprint
                    FROM chapter_dependencies d
                    JOIN candidates c ON c.run_id=d.run_id
                    JOIN acceptance_evidence a ON a.candidate_id=c.candidate_id
                    LEFT JOIN canon_state s ON s.state_key='chapter:' || d.source_chapter_id
                    WHERE d.chapter_id=? AND a.acceptance_id=?""",
                    (chapter_id, acceptance_id),
                ).fetchall()
                if any(item["status"] != "current" or item["source_fingerprint"] != item["current_fingerprint"] for item in dependencies):
                    raise PublicationRecoveryError("publication_source_changed")
            byte_count += len(source.content.encode("utf-8")) + (2 if contents else 0)
            if byte_count > MAX_ARTIFACT_BYTES:
                raise PublicationRecoveryError("publication_artifact_invalid")
            chapters.append(chapter_id)
            contents.append(source.content)
            bindings.append({
                "acceptance_id": acceptance_id, "chapter_id": chapter_id,
                "document_id": source.document_id, "revision_id": source.revision_id,
                "content_fingerprint": source.source_fingerprint,
            })
        # Chapter ordinal is the novel-wide reading order, including volumes.
        # Match chapter.list and the frozen target's current_reading_order.
        if require_current and chapters != sorted(chapters, key=lambda chapter: (nodes[chapter]["ordinal"], chapter)):
            raise PublicationRecoveryError("publication_source_invalid")
        return _CollectionSource(
            project_id=project_id, source_key=source_key,
            source_fingerprint=fingerprint_bytes(canonical_json(bindings).encode("utf-8")),
            content="\n\n".join(contents),
        )

    def _artifact_source(self, conn: Any, project_id: str, source_key: str) -> _CollectionSource:
        return self._source(conn, project_id, source_key, require_current=False)

    def _before_stage(self, conn: Any, plan: _Plan) -> None:
        if self._request is None:
            return
        key, request_fingerprint = self._request
        row = conn.execute("SELECT request_fingerprint,build_id FROM publication_collection_requests WHERE idempotency_key=?", (key,)).fetchone()
        if row:
            if row["request_fingerprint"] != request_fingerprint or row["build_id"] != plan.build_id:
                raise PublicationRecoveryError("publication_identity_conflict")
        else:
            conn.execute(
                "INSERT INTO publication_collection_requests(idempotency_key,request_fingerprint,build_id,created_at) VALUES(?,?,?,?)",
                (key, request_fingerprint, plan.build_id, now_iso()),
            )

    def _new_attempt(self, conn: Any, plan: _Plan) -> None:
        conn.executemany(
            "INSERT INTO publication_collection_members(build_id,ordinal,acceptance_id) VALUES(?,?,?)",
            [(plan.build_id, index, acceptance_id) for index, acceptance_id in enumerate(json.loads(plan.source_key))],
        )

    def _validate_row(self, row: Any, plan: _Plan) -> None:
        super()._validate_row(row, plan)
        with self.store.open_project(plan.project_id) as conn:
            actual = [tuple(item) for item in conn.execute("SELECT ordinal,acceptance_id FROM publication_collection_members WHERE build_id=? ORDER BY ordinal", (plan.build_id,))]
        if actual != list(enumerate(json.loads(plan.source_key))):
            raise PublicationRecoveryError("publication_attempt_invalid")

    def _source_acceptance_ids(self, plan: _Plan) -> list[str]:
        return list(json.loads(plan.source_key))

    def _result(self, plan: _Plan, row: Any) -> dict[str, Any]:
        return {
            "schema": "quillframe_publication_collection_result_v1",
            "project_id": plan.project_id, "build_id": plan.build_id,
            "source_acceptance_ids": self._source_acceptance_ids(plan),
            "format": plan.fmt, "artifact_fingerprint": plan.artifact_fingerprint,
            "byte_size": plan.byte_size, "output_ref": plan.final_ref,
            "persistent": True, "authority": False,
        }

    def build_collection(self, project_id: str, acceptance_ids: list[str], fmt: str = "md", *, idempotency_key: str, user_authorized: bool) -> dict[str, Any]:
        if user_authorized is not True:
            raise PublicationRecoveryError("publication_authorization_required")
        ids = _acceptance_ids(acceptance_ids)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 256:
            raise PublicationRecoveryError("publication_idempotency_required")
        request_fingerprint = fingerprint_bytes(canonical_json({
            "operation": "publication.collection.build", "project_id": project_id,
            "source_acceptance_ids": ids, "format": fmt,
        }).encode("utf-8"))
        self._request = (idempotency_key, request_fingerprint)
        return super().build(project_id, canonical_json(ids), fmt)
