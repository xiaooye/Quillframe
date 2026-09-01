"""Rights-bound, author-confirmed voice assets for fiction generation.

Models may compile a structured voice hypothesis.  This service owns only
source eligibility, exact bindings, author confirmation, versioning and
activation.  It never scores prose, infers style or promotes rejected model
text into a positive example.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator

from harness.context_runtime import fingerprint
from harness.semantic_workers.registered_contract_binding import validate_registered_job
from harness.semantic_workers.semantic_worker_router import validate_result
from learning.learning_store import canonical_json, now_iso


SOURCE_SCHEMA = "quillframe_author_voice_source_v1"
SHEET_SCHEMA = "quillframe_author_voice_sheet_v1"
SNAPSHOT_SCHEMA = "quillframe_author_voice_snapshot_v1"
RECEIPT_SCHEMA = "quillframe_author_voice_activation_receipt_v1"
SCOPES = {"project", "user"}
USER_SCOPE_ID = "current_user"
LEGACY_UNBOUND_PROJECT_SCOPE_ID = "legacy_unbound_project"
SOURCE_KINDS = {
    "user_authored_prose",
    "author_edited_approved_prose",
    "explicit_author_feedback",
    "explicitly_authorized_prose",
}
ANCHOR_KINDS = SOURCE_KINDS - {"explicit_author_feedback"}
VOICE_FIELDS = (
    "narrative_distance_and_pov_attention",
    "syntax_and_paragraph_rhythm",
    "information_release",
    "dialogue_and_relationship_differences",
    "humor_under_pressure",
    "emotion_through_action_judgment_and_cost",
    "reader_inference",
    "language_switching_and_terminology",
    "applicability_boundaries",
)


def _text(value: Any, label: str, *, maximum: int = 20_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be non-empty text of at most {maximum} characters")
    return value.strip()


def _sha(value: Any, label: str) -> str:
    value = _text(value, label, maximum=71)
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{label} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be sha256:<64 hex>") from exc
    return value


def _ids(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    result = [_text(item, label, maximum=160) for item in value]
    if len(result) != len(set(result)):
        raise ValueError(f"{label} must contain unique values")
    return result


def _default_snapshot() -> dict[str, Any]:
    value = {
        "schema": SNAPSHOT_SCHEMA,
        "status": "disabled",
        "active_sheet": None,
        "eligible_anchors": [],
        "degraded_reasons": ["no_author_confirmed_active_voice_sheet"],
        "authority": False,
    }
    value["snapshot_fingerprint"] = fingerprint(value)
    return value


def _scope_id(payload: dict[str, Any], scope: str) -> str:
    """Resolve the durable owner of a voice asset without guessing."""

    if scope == "user":
        if payload.get("project_id") not in {None, ""}:
            raise ValueError("user-scoped Author Voice assets cannot bind project_id")
        return USER_SCOPE_ID
    return _text(payload.get("project_id"), "project_id", maximum=160)


class AuthorVoiceService:
    """Explicit mutation service plus side-effect-free runtime snapshots."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._ensure_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
        finally:
            connection.close()

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS author_voice_sources (
                    source_id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    content_text TEXT NOT NULL,
                    content_fingerprint TEXT NOT NULL,
                    rights_class TEXT NOT NULL,
                    rights_basis TEXT NOT NULL,
                    storage_intent TEXT NOT NULL,
                    excerpt_purpose TEXT,
                    writer_use_authorized INTEGER NOT NULL,
                    author_confirmed INTEGER NOT NULL,
                    living_author_imitation INTEGER NOT NULL,
                    model_generated INTEGER NOT NULL,
                    rejected_candidate INTEGER NOT NULL,
                    applicability_json TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS author_voice_sheets (
                    sheet_id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    fields_json TEXT NOT NULL,
                    source_ids_json TEXT NOT NULL,
                    anchor_source_ids_json TEXT NOT NULL,
                    uncertainties_json TEXT NOT NULL,
                    compiler_binding_fingerprint TEXT NOT NULL,
                    author_confirmation_ref TEXT,
                    author_confirmed_at TEXT,
                    sheet_fingerprint TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS author_voice_activation_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    sheet_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    before_version INTEGER NOT NULL,
                    after_version INTEGER NOT NULL,
                    confirmation_ref TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(sheet_id) REFERENCES author_voice_sheets(sheet_id)
                );
                """
            )
            # Development databases created before project ownership was
            # explicit are migrated to an inert sentinel. Never guess which
            # project owns an old sheet: that would leak voice across projects.
            for table in ("author_voice_sources", "author_voice_sheets"):
                columns = {
                    row[1] for row in connection.execute(f"PRAGMA table_info({table})")
                }
                if "scope_id" not in columns:
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN scope_id TEXT NOT NULL DEFAULT ''"
                    )
                connection.execute(
                    f"UPDATE {table} SET scope_id=CASE WHEN scope='user' THEN ? ELSE ? END "
                    "WHERE scope_id=''",
                    (USER_SCOPE_ID, LEGACY_UNBOUND_PROJECT_SCOPE_ID),
                )
            receipt_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(author_voice_activation_receipts)"
                )
            }
            if "scope_id" not in receipt_columns:
                connection.execute(
                    "ALTER TABLE author_voice_activation_receipts "
                    "ADD COLUMN scope_id TEXT NOT NULL DEFAULT ''"
                )
                connection.execute(
                    "UPDATE author_voice_activation_receipts SET scope_id=? WHERE scope_id=''",
                    (LEGACY_UNBOUND_PROJECT_SCOPE_ID,),
                )
            connection.execute("DROP INDEX IF EXISTS author_voice_one_active_per_scope")
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS author_voice_one_active_per_owner "
                "ON author_voice_sheets(scope,scope_id) WHERE state='active'"
            )

    @staticmethod
    def _source(row: sqlite3.Row, *, include_text: bool = True) -> dict[str, Any]:
        value = {
            "schema": SOURCE_SCHEMA,
            "source_id": row["source_id"],
            "scope": row["scope"],
            "scope_id": row["scope_id"],
            "source_kind": row["source_kind"],
            "source_ref": row["source_ref"],
            "content_fingerprint": row["content_fingerprint"],
            "rights": {
                "rights_class": row["rights_class"],
                "rights_basis": row["rights_basis"],
                "storage_intent": row["storage_intent"],
                "excerpt_purpose": row["excerpt_purpose"],
                "writer_use_authorized": bool(row["writer_use_authorized"]),
            },
            "author_confirmed": bool(row["author_confirmed"]),
            "living_author_imitation": bool(row["living_author_imitation"]),
            "model_generated": bool(row["model_generated"]),
            "rejected_candidate": bool(row["rejected_candidate"]),
            "applicability": json.loads(row["applicability_json"]),
            "version": row["version"],
            "state": row["state"],
            "authority": False,
        }
        if include_text:
            value["content_text"] = row["content_text"]
        value["source_fingerprint"] = fingerprint(value)
        return value

    @staticmethod
    def _sheet_body(row: sqlite3.Row) -> dict[str, Any]:
        value = {
            "sheet_id": row["sheet_id"],
            "scope": row["scope"],
            "scope_id": row["scope_id"],
            "state": row["state"],
            "version": row["version"],
            "fields": json.loads(row["fields_json"]),
            "source_ids": json.loads(row["source_ids_json"]),
            "anchor_source_ids": json.loads(row["anchor_source_ids_json"]),
            "uncertainties": json.loads(row["uncertainties_json"]),
            "compiler_binding_fingerprint": row["compiler_binding_fingerprint"],
        }
        if row["author_confirmation_ref"] is not None:
            value["author_confirmation_ref"] = row["author_confirmation_ref"]
            value["author_confirmed_at"] = row["author_confirmed_at"]
        return value

    @classmethod
    def _assert_sheet_integrity(cls, row: sqlite3.Row) -> None:
        if row["sheet_fingerprint"] != fingerprint(cls._sheet_body(row)):
            raise ValueError("Author Voice Sheet fingerprint changed")

    @staticmethod
    def _sheet(row: sqlite3.Row) -> dict[str, Any]:
        value = {
            "schema": SHEET_SCHEMA,
            "sheet_id": row["sheet_id"],
            "scope": row["scope"],
            "scope_id": row["scope_id"],
            "state": row["state"],
            "version": row["version"],
            "fields": json.loads(row["fields_json"]),
            "source_ids": json.loads(row["source_ids_json"]),
            "anchor_source_ids": json.loads(row["anchor_source_ids_json"]),
            "uncertainties": json.loads(row["uncertainties_json"]),
            "compiler_binding_fingerprint": row["compiler_binding_fingerprint"],
            "author_confirmation_ref": row["author_confirmation_ref"],
            "author_confirmed_at": row["author_confirmed_at"],
            "sheet_fingerprint": row["sheet_fingerprint"],
            "authority": False,
        }
        return value

    def register_source(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("voice source must be an object")
        scope = payload.get("scope")
        source_kind = payload.get("source_kind")
        if scope not in SCOPES:
            raise ValueError("scope must be project|user")
        if source_kind not in SOURCE_KINDS:
            raise ValueError("source_kind is not eligible for author voice")
        scope_id = _scope_id(payload, scope)
        text = _text(payload.get("content_text"), "content_text")
        content_fingerprint = _sha(payload.get("content_fingerprint"), "content_fingerprint")
        if fingerprint(text) != content_fingerprint:
            raise ValueError("content_fingerprint does not bind content_text")
        rights = payload.get("rights")
        if not isinstance(rights, dict):
            raise ValueError("rights must be an object")
        if rights.get("rights_class") != "redistributable":
            raise ValueError("positive voice sources require redistributable or author-owned rights")
        rights_basis = _text(rights.get("rights_basis"), "rights.rights_basis", maximum=1000)
        storage_intent = rights.get("storage_intent")
        if storage_intent not in {"full_text", "short_excerpt"}:
            raise ValueError("rights.storage_intent must be full_text|short_excerpt")
        excerpt_purpose = rights.get("excerpt_purpose")
        if storage_intent == "short_excerpt":
            excerpt_purpose = _text(excerpt_purpose, "rights.excerpt_purpose", maximum=1000)
        elif excerpt_purpose is not None:
            excerpt_purpose = _text(excerpt_purpose, "rights.excerpt_purpose", maximum=1000)
        if rights.get("writer_use_authorized") is not True:
            raise ValueError("rights.writer_use_authorized must be explicit")
        if payload.get("author_confirmed") is not True:
            raise ValueError("author_confirmed must be explicit")
        if payload.get("living_author_imitation") is not False:
            raise ValueError("living-author imitation cannot be a voice source")
        if payload.get("model_generated") is not False or payload.get("rejected_candidate") is not False:
            raise ValueError("model-generated or rejected prose cannot be a positive voice source")
        applicability = payload.get("applicability", {})
        if not isinstance(applicability, dict):
            raise ValueError("applicability must be an object")
        source_ref = _text(payload.get("source_ref"), "source_ref", maximum=1000)
        source_id = payload.get("source_id") or ("AVS-" + content_fingerprint[7:31])
        source_id = _text(source_id, "source_id", maximum=160)
        stamp = now_iso()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM author_voice_sources WHERE source_id=?", (source_id,)
            ).fetchone()
            identity = {
                "scope": scope,
                "scope_id": scope_id,
                "source_kind": source_kind,
                "source_ref": source_ref,
                "content_text": text,
                "content_fingerprint": content_fingerprint,
                "rights_class": "redistributable",
                "rights_basis": rights_basis,
                "storage_intent": storage_intent,
                "excerpt_purpose": excerpt_purpose,
                "writer_use_authorized": 1,
                "author_confirmed": 1,
                "living_author_imitation": 0,
                "model_generated": 0,
                "rejected_candidate": 0,
                "applicability_json": canonical_json(applicability),
            }
            if existing is not None:
                current = {key: existing[key] for key in identity}
                if current != identity:
                    connection.execute("ROLLBACK")
                    raise ValueError("source_id already binds different evidence")
                connection.execute("COMMIT")
                return self._source(existing)
            connection.execute(
                """INSERT INTO author_voice_sources(
                    source_id,scope,scope_id,source_kind,source_ref,content_text,content_fingerprint,
                    rights_class,rights_basis,storage_intent,excerpt_purpose,
                    writer_use_authorized,author_confirmed,living_author_imitation,
                    model_generated,rejected_candidate,applicability_json,version,state,
                    created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,'eligible',?,?)""",
                (
                    source_id, scope, scope_id, source_kind, source_ref, text, content_fingerprint,
                    "redistributable", rights_basis, storage_intent, excerpt_purpose,
                    1, 1, 0, 0, 0, canonical_json(applicability), stamp, stamp,
                ),
            )
            row = connection.execute(
                "SELECT * FROM author_voice_sources WHERE source_id=?", (source_id,)
            ).fetchone()
            connection.execute("COMMIT")
        assert row is not None
        return self._source(row)

    @staticmethod
    def _validate_compiler_binding(
        binding: Any,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        if not isinstance(binding, dict):
            raise ValueError("registered compiler binding is required")
        job, result = binding.get("job"), binding.get("result")
        if (
            not isinstance(job, dict)
            or not isinstance(result, dict)
            or binding.get("binding_fingerprint") != fingerprint({"job": job, "result": result})
        ):
            raise ValueError("compiler binding fingerprint does not match")
        errors = validate_registered_job(job) + validate_result(job, result)
        if errors:
            raise ValueError("; ".join(errors))
        if job.get("input", {}).get("model_contract_id") != "learning.author_voice_compile":
            raise ValueError("learning.author_voice_compile binding is required")
        if result.get("status") != "completed":
            raise ValueError("author voice compiler did not complete")
        judgment = result.get("judgment")
        if not isinstance(judgment, dict):
            raise ValueError("author voice compiler judgment is required")
        compiler_payload = job.get("input", {}).get("payload")
        if not isinstance(compiler_payload, dict):
            raise ValueError("author voice compiler payload is required")
        return judgment, compiler_payload, binding["binding_fingerprint"]

    def create_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("voice sheet candidate must be an object")
        scope = payload.get("scope")
        if scope not in SCOPES:
            raise ValueError("scope must be project|user")
        scope_id = _scope_id(payload, scope)
        judgment, compiler_payload, binding_fingerprint = self._validate_compiler_binding(
            payload.get("compiler_binding")
        )
        if compiler_payload.get("scope") != scope:
            raise ValueError("author voice compiler scope does not match the candidate")
        fields = judgment.get("fields")
        if not isinstance(fields, dict) or set(fields) != set(VOICE_FIELDS):
            raise ValueError("compiled voice fields do not match the Author Voice Sheet")
        fields = {key: _text(fields[key], f"fields.{key}", maximum=4000) for key in VOICE_FIELDS}
        source_ids = _ids(judgment.get("source_ids"), "source_ids")
        anchor_ids = _ids(judgment.get("anchor_source_ids"), "anchor_source_ids")
        if not source_ids or not set(anchor_ids).issubset(source_ids) or len(anchor_ids) > 4:
            raise ValueError("anchor_source_ids must be a zero-to-four subset of source_ids")
        uncertainties = _ids(judgment.get("uncertainties", []), "uncertainties")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM author_voice_sources WHERE source_id IN ({})".format(
                    ",".join("?" for _ in source_ids)
                ),
                source_ids,
            ).fetchall()
            found = {row["source_id"]: row for row in rows}
            if set(found) != set(source_ids):
                raise ValueError("compiled voice sheet references an unknown source")
            for source_id, row in found.items():
                if (
                    row["scope"] != scope
                    or row["scope_id"] != scope_id
                    or row["state"] != "eligible"
                    or not row["writer_use_authorized"]
                    or not row["author_confirmed"]
                    or row["model_generated"]
                    or row["rejected_candidate"]
                    or row["living_author_imitation"]
                ):
                    raise ValueError(f"voice source is ineligible: {source_id}")
                if source_id in anchor_ids and row["source_kind"] not in ANCHOR_KINDS:
                    raise ValueError("explicit feedback is not a positive prose anchor")
            compiler_sources = judgment.get("source_fingerprints")
            expected_sources = {
                source_id: found[source_id]["content_fingerprint"] for source_id in source_ids
            }
            if compiler_sources != expected_sources:
                raise ValueError("compiler result does not bind exact source fingerprints")
            compiler_inputs = compiler_payload.get("sources")
            if not isinstance(compiler_inputs, list):
                raise ValueError("author voice compiler sources are required")
            compiler_by_id = {
                item.get("source_id"): item for item in compiler_inputs if isinstance(item, dict)
            }
            if (
                len(compiler_by_id) != len(compiler_inputs)
                or set(compiler_by_id) != set(source_ids)
            ):
                raise ValueError("compiler input does not bind the exact source set")
            for source_id in source_ids:
                row = found[source_id]
                compiler_source = compiler_by_id[source_id]
                expected_input = {
                    "source_id": source_id,
                    "source_kind": row["source_kind"],
                    "content_text": row["content_text"],
                    "content_fingerprint": row["content_fingerprint"],
                    "rights_binding": {
                        "rights_class": row["rights_class"],
                        "rights_basis": row["rights_basis"],
                        "storage_intent": row["storage_intent"],
                        "excerpt_purpose": row["excerpt_purpose"],
                        "writer_use_authorized": bool(row["writer_use_authorized"]),
                    },
                    "author_confirmed": True,
                    "applicability": json.loads(row["applicability_json"]),
                }
                if compiler_source != expected_input:
                    raise ValueError(
                        f"compiler input does not bind registered source evidence: {source_id}"
                    )
            sheet_id = _text(
                payload.get("sheet_id") or ("AV-" + uuid.uuid4().hex),
                "sheet_id",
                maximum=160,
            )
            body = {
                "sheet_id": sheet_id,
                "scope": scope,
                "scope_id": scope_id,
                "state": "candidate",
                "version": 1,
                "fields": fields,
                "source_ids": source_ids,
                "anchor_source_ids": anchor_ids,
                "uncertainties": uncertainties,
                "compiler_binding_fingerprint": binding_fingerprint,
            }
            sheet_fingerprint = fingerprint(body)
            stamp = now_iso()
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO author_voice_sheets(
                    sheet_id,scope,scope_id,state,version,fields_json,source_ids_json,
                    anchor_source_ids_json,uncertainties_json,
                    compiler_binding_fingerprint,author_confirmation_ref,
                    author_confirmed_at,sheet_fingerprint,created_at,updated_at
                ) VALUES(?,?,?,'candidate',1,?,?,?,?,?,NULL,NULL,?,?,?)""",
                (
                    sheet_id, scope, scope_id, canonical_json(fields), canonical_json(source_ids),
                    canonical_json(anchor_ids), canonical_json(uncertainties),
                    binding_fingerprint, sheet_fingerprint, stamp, stamp,
                ),
            )
            row = connection.execute(
                "SELECT * FROM author_voice_sheets WHERE sheet_id=?", (sheet_id,)
            ).fetchone()
            connection.execute("COMMIT")
        assert row is not None
        return self._sheet(row)

    def activate(
        self,
        sheet_id: str,
        *,
        expected_version: int,
        expected_sheet_fingerprint: str,
        confirmation_ref: str,
    ) -> dict[str, Any]:
        sheet_id = _text(sheet_id, "sheet_id", maximum=160)
        if type(expected_version) is not int or expected_version < 1:
            raise ValueError("expected_version must be a positive integer")
        expected_sheet_fingerprint = _sha(
            expected_sheet_fingerprint, "expected_sheet_fingerprint"
        )
        confirmation_ref = _text(confirmation_ref, "confirmation_ref", maximum=1000)
        stamp = now_iso()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM author_voice_sheets WHERE sheet_id=?", (sheet_id,)
            ).fetchone()
            if row is None:
                connection.execute("ROLLBACK")
                raise ValueError("unknown Author Voice Sheet")
            if row["state"] != "candidate" or row["version"] != expected_version:
                connection.execute("ROLLBACK")
                raise ValueError("voice sheet state or version changed")
            try:
                self._assert_sheet_integrity(row)
            except ValueError:
                connection.execute("ROLLBACK")
                raise
            if row["sheet_fingerprint"] != expected_sheet_fingerprint:
                connection.execute("ROLLBACK")
                raise ValueError("author confirmation does not bind this voice sheet")
            source_ids = json.loads(row["source_ids_json"])
            source_rows = connection.execute(
                "SELECT * FROM author_voice_sources WHERE source_id IN ({})".format(
                    ",".join("?" for _ in source_ids)
                ),
                source_ids,
            ).fetchall()
            if len(source_rows) != len(source_ids):
                connection.execute("ROLLBACK")
                raise ValueError("voice source eligibility changed")
            for source_row in source_rows:
                if (
                    source_row["scope"] != row["scope"]
                    or source_row["scope_id"] != row["scope_id"]
                    or source_row["state"] != "eligible"
                    or not source_row["author_confirmed"]
                    or not source_row["writer_use_authorized"]
                    or source_row["living_author_imitation"]
                    or source_row["model_generated"]
                    or source_row["rejected_candidate"]
                    or fingerprint(source_row["content_text"])
                    != source_row["content_fingerprint"]
                ):
                    connection.execute("ROLLBACK")
                    raise ValueError("voice source eligibility changed")
            previous_rows = connection.execute(
                "SELECT * FROM author_voice_sheets WHERE scope=? AND scope_id=? "
                "AND state='active'",
                (row["scope"], row["scope_id"]),
            ).fetchall()
            for previous in previous_rows:
                self._assert_sheet_integrity(previous)
                previous_body = self._sheet_body(previous)
                previous_body["state"] = "superseded"
                previous_body["version"] = previous["version"] + 1
                connection.execute(
                    "UPDATE author_voice_sheets SET state='superseded',version=?,"
                    "sheet_fingerprint=?,updated_at=? WHERE sheet_id=?",
                    (
                        previous_body["version"],
                        fingerprint(previous_body),
                        stamp,
                        previous["sheet_id"],
                    ),
                )
            after_version = expected_version + 1
            body = {
                "sheet_id": sheet_id,
                "scope": row["scope"],
                "scope_id": row["scope_id"],
                "state": "active",
                "version": after_version,
                "fields": json.loads(row["fields_json"]),
                "source_ids": source_ids,
                "anchor_source_ids": json.loads(row["anchor_source_ids_json"]),
                "uncertainties": json.loads(row["uncertainties_json"]),
                "compiler_binding_fingerprint": row["compiler_binding_fingerprint"],
                "author_confirmation_ref": confirmation_ref,
                "author_confirmed_at": stamp,
            }
            sheet_fingerprint = fingerprint(body)
            connection.execute(
                "UPDATE author_voice_sheets SET state='active',version=?,author_confirmation_ref=?,"
                "author_confirmed_at=?,sheet_fingerprint=?,updated_at=? WHERE sheet_id=?",
                (after_version, confirmation_ref, stamp, sheet_fingerprint, stamp, sheet_id),
            )
            receipt = {
                "schema": RECEIPT_SCHEMA,
                "receipt_id": "AVR-" + uuid.uuid4().hex,
                "sheet_id": sheet_id,
                "scope": row["scope"],
                "scope_id": row["scope_id"],
                "before_version": expected_version,
                "after_version": after_version,
                "candidate_sheet_fingerprint": expected_sheet_fingerprint,
                "active_sheet_fingerprint": sheet_fingerprint,
                "confirmation_ref": confirmation_ref,
                "author_confirmed": True,
                "authority": False,
            }
            receipt["receipt_fingerprint"] = fingerprint(receipt)
            connection.execute(
                """INSERT INTO author_voice_activation_receipts(
                    receipt_id,sheet_id,scope,scope_id,before_version,after_version,
                    confirmation_ref,payload_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    receipt["receipt_id"], sheet_id, row["scope"], row["scope_id"], expected_version,
                    after_version, confirmation_ref, canonical_json(receipt), stamp,
                ),
            )
            active = connection.execute(
                "SELECT * FROM author_voice_sheets WHERE sheet_id=?", (sheet_id,)
            ).fetchone()
            connection.execute("COMMIT")
        assert active is not None
        return {"sheet": self._sheet(active), "receipt": receipt}

    @classmethod
    def snapshot_readonly(
        cls, db_path: str | Path, *, project_id: str | None = None
    ) -> dict[str, Any]:
        path = Path(db_path)
        if not path.is_file():
            return _default_snapshot()
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('author_voice_sheets','author_voice_sources')"
                )
            }
            if tables != {"author_voice_sheets", "author_voice_sources"}:
                return _default_snapshot()
            row = None
            if project_id is not None:
                project_id = _text(project_id, "project_id", maximum=160)
                row = connection.execute(
                    "SELECT * FROM author_voice_sheets WHERE state='active' "
                    "AND scope='project' AND scope_id=? ORDER BY updated_at DESC LIMIT 1",
                    (project_id,),
                ).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT * FROM author_voice_sheets WHERE state='active' "
                    "AND scope='user' AND scope_id=? ORDER BY updated_at DESC LIMIT 1",
                    (USER_SCOPE_ID,),
                ).fetchone()
            if row is None or not row["author_confirmation_ref"] or not row["author_confirmed_at"]:
                return _default_snapshot()
            try:
                cls._assert_sheet_integrity(row)
            except ValueError:
                return _default_snapshot()
            sheet = cls._sheet(row)
            anchor_ids = sheet["anchor_source_ids"]
            anchors: list[dict[str, Any]] = []
            if anchor_ids:
                rows = connection.execute(
                    "SELECT * FROM author_voice_sources WHERE source_id IN ({})".format(
                        ",".join("?" for _ in anchor_ids)
                    ),
                    anchor_ids,
                ).fetchall()
                by_id = {item["source_id"]: item for item in rows}
                if set(by_id) != set(anchor_ids):
                    return _default_snapshot()
                for source_id in anchor_ids:
                    source = cls._source(by_id[source_id])
                    if (
                        source["scope"] != row["scope"]
                        or source["scope_id"] != row["scope_id"]
                        or source["state"] != "eligible"
                        or not source["author_confirmed"]
                        or not source["rights"]["writer_use_authorized"]
                        or source["model_generated"]
                        or source["rejected_candidate"]
                        or source["living_author_imitation"]
                        or fingerprint(source["content_text"])
                        != source["content_fingerprint"]
                    ):
                        return _default_snapshot()
                    anchors.append(source)
            degraded = [] if len(anchors) >= 2 else ["fewer_than_two_author_confirmed_positive_anchors"]
            value = {
                "schema": SNAPSHOT_SCHEMA,
                "status": "active" if not degraded else "active_degraded",
                "active_sheet": sheet,
                "eligible_anchors": anchors,
                "degraded_reasons": degraded,
                "authority": False,
            }
            value["snapshot_fingerprint"] = fingerprint(value)
            return value
        finally:
            connection.close()


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("Author Voice snapshot schema mismatch")
    expected = fingerprint({key: value for key, value in snapshot.items() if key != "snapshot_fingerprint"})
    if snapshot.get("snapshot_fingerprint") != expected:
        raise ValueError("Author Voice snapshot fingerprint changed")
    status = snapshot.get("status")
    if status not in {"disabled", "active", "active_degraded"}:
        raise ValueError("Author Voice snapshot status is invalid")
    sheet = snapshot.get("active_sheet")
    anchors = snapshot.get("eligible_anchors")
    if not isinstance(anchors, list) or len(anchors) > 4:
        raise ValueError("Author Voice anchors must contain at most four items")
    if status == "disabled":
        if sheet is not None or anchors:
            raise ValueError("disabled Author Voice snapshot cannot expose a sheet")
        return
    if not isinstance(sheet, dict) or sheet.get("state") != "active":
        raise ValueError("active Author Voice snapshot requires an active sheet")
    if not sheet.get("author_confirmation_ref") or not sheet.get("author_confirmed_at"):
        raise ValueError("active Author Voice Sheet lacks author confirmation")
    if [item.get("source_id") for item in anchors] != sheet.get("anchor_source_ids"):
        raise ValueError("Author Voice anchors do not match the active sheet")
    for item in anchors:
        if (
            item.get("source_kind") not in ANCHOR_KINDS
            or item.get("rights", {}).get("rights_class") != "redistributable"
            or item.get("rights", {}).get("writer_use_authorized") is not True
            or item.get("author_confirmed") is not True
            or item.get("model_generated") is not False
            or item.get("rejected_candidate") is not False
            or item.get("living_author_imitation") is not False
        ):
            raise ValueError("Author Voice anchor is not Writer-eligible")
