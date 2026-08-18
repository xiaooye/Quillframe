#!/usr/bin/env python3
"""Canonical SQLite persistence for Quillframe 0.9.

The database owns durable product state. Persistence never grants Canon,
acceptance, settlement, learning-promotion, or framework-write authority by
itself; those transitions remain operation-specific Core decisions.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = Path(__file__).resolve().parent / "migrations"
SCHEMA_VERSION = 1


class MigrationChecksumError(RuntimeError):
    pass


class ConflictError(RuntimeError):
    pass


class IntegrityError(RuntimeError):
    pass


class _ClosingConnection(sqlite3.Connection):
    """Transaction context manager that also closes the SQLite handle."""

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fingerprint_text(text: str) -> str:
    return fingerprint_bytes(text.encode("utf-8"))


def data_root() -> Path:
    configured = os.environ.get("QUILLFRAME_DATA_DIR")
    return Path(configured).expanduser().resolve() if configured else (Path.home() / ".quillframe").resolve()


def project_dir(project_id: str, root: Path | None = None) -> Path:
    if not project_id or any(x in project_id for x in ("/", "\\", "..")):
        raise ValueError("project_id must be a simple stable identifier")
    return (root or data_root()) / "projects" / project_id


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0, factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    return conn


def _statements(sql: str) -> Iterable[str]:
    buf = ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            statement = buf.strip()
            if statement:
                yield statement
            buf = ""
    if buf.strip():
        raise ValueError("incomplete SQL migration")


def _ensure_migration_ledger(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
        scope TEXT NOT NULL,
        version INTEGER NOT NULL,
        name TEXT NOT NULL,
        checksum TEXT NOT NULL,
        applied_at TEXT NOT NULL,
        PRIMARY KEY(scope, version)
        )"""
    )
    conn.commit()


def apply_migrations(conn: sqlite3.Connection, scope: str) -> list[dict[str, Any]]:
    if scope not in {"global", "project"}:
        raise ValueError("scope must be global|project")
    _ensure_migration_ledger(conn)
    directory = MIGRATIONS / scope
    applied: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.sql")):
        prefix = path.name.split("_", 1)[0]
        if not prefix.isdigit():
            raise ValueError(f"migration filename must start with an integer: {path.name}")
        version = int(prefix)
        sql = path.read_text(encoding="utf-8")
        checksum = fingerprint_text(sql)
        row = conn.execute(
            "SELECT checksum FROM schema_migrations WHERE scope=? AND version=?", (scope, version)
        ).fetchone()
        if row:
            if row["checksum"] != checksum:
                raise MigrationChecksumError(
                    f"{scope} migration {version} checksum mismatch: {row['checksum']} != {checksum}"
                )
            continue
        try:
            conn.execute("BEGIN IMMEDIATE")
            for statement in _statements(sql):
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations(scope,version,name,checksum,applied_at) VALUES(?,?,?,?,?)",
                (scope, version, path.name, checksum, now_iso()),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        applied.append({"scope": scope, "version": version, "name": path.name, "checksum": checksum})
    return applied


def _fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp.__qf_fts_probe USING fts5(value)")
        conn.execute("DROP TABLE temp.__qf_fts_probe")
        return True
    except sqlite3.DatabaseError:
        return False


def _trigram_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp.__qf_tri_probe USING fts5(value, tokenize='trigram')")
        conn.execute("DROP TABLE temp.__qf_tri_probe")
        return True
    except sqlite3.DatabaseError:
        return False


@dataclass(frozen=True)
class ProjectLocation:
    project_id: str
    directory: Path
    database: Path
    blobs: Path
    exports: Path


class QuillframeStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or data_root()).expanduser().resolve()
        self.global_db = self.root / "quillframe.sqlite"
        self.projects_root = self.root / "projects"
        self.backups_root = self.root / "backups"
        self.cache_root = self.root / "cache"

    def ensure_layout(self) -> None:
        for path in (self.root, self.projects_root, self.backups_root, self.cache_root):
            path.mkdir(parents=True, exist_ok=True)

    def initialize_global(self) -> list[dict[str, Any]]:
        self.ensure_layout()
        with _connect(self.global_db) as conn:
            return apply_migrations(conn, "global")

    def location(self, project_id: str) -> ProjectLocation:
        d = project_dir(project_id, self.root)
        return ProjectLocation(project_id, d, d / "project.sqlite", d / "blobs", d / "exports")

    def list_projects(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the canonical global Project registry projection."""
        self.initialize_global()
        bounded = max(1, min(int(limit), 500))
        with _connect(self.global_db) as conn:
            rows = conn.execute(
                "SELECT project_id,title,language,project_schema_version,registered_at,last_opened_at "
                "FROM project_registry ORDER BY last_opened_at DESC, project_id LIMIT ?",
                (bounded,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_project(self, project_id: str, title: str, language: str = "zh-CN") -> ProjectLocation:
        if not title.strip():
            raise ValueError("title is required")
        self.initialize_global()
        loc = self.location(project_id)
        loc.blobs.mkdir(parents=True, exist_ok=True)
        loc.exports.mkdir(parents=True, exist_ok=True)
        with _connect(loc.database) as conn:
            apply_migrations(conn, "project")
            existing = conn.execute("SELECT project_id FROM project_identity").fetchone()
            if existing and existing["project_id"] != project_id:
                raise IntegrityError("project database identity mismatch")
            stamp = now_iso()
            conn.execute(
                """INSERT INTO project_identity(project_id,title,language,project_schema_version,created_at,updated_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(project_id) DO UPDATE SET title=excluded.title,language=excluded.language,updated_at=excluded.updated_at""",
                (project_id, title.strip(), language, SCHEMA_VERSION, stamp, stamp),
            )
            conn.commit()
            self._ensure_optional_search(conn)
        with _connect(self.global_db) as conn:
            stamp = now_iso()
            conn.execute(
                """INSERT INTO project_registry(project_id,title,language,project_schema_version,project_dir,registered_at,last_opened_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(project_id) DO UPDATE SET title=excluded.title,language=excluded.language,
                project_schema_version=excluded.project_schema_version,project_dir=excluded.project_dir,last_opened_at=excluded.last_opened_at""",
                (project_id, title.strip(), language, SCHEMA_VERSION, str(loc.directory), stamp, stamp),
            )
            conn.commit()
        return loc

    def open_project(self, project_id: str) -> sqlite3.Connection:
        loc = self.location(project_id)
        if not loc.database.exists():
            raise FileNotFoundError(f"project database does not exist: {project_id}")
        conn = _connect(loc.database)
        apply_migrations(conn, "project")
        self._ensure_optional_search(conn)
        return conn

    def _ensure_optional_search(self, conn: sqlite3.Connection) -> None:
        if not _fts5_available(conn):
            raise IntegrityError("SQLite FTS5 is required by Quillframe 0.9")
        if _trigram_available(conn):
            conn.execute(
                """CREATE VIRTUAL TABLE IF NOT EXISTS search_trigram USING fts5(
                entity_type UNINDEXED, entity_id UNINDEXED, title, body, tokenize='trigram')"""
            )
            conn.commit()

    def create_document(
        self,
        project_id: str,
        document_id: str,
        title: str,
        document_kind: str = "manuscript",
        story_node_id: str | None = None,
    ) -> None:
        with self.open_project(project_id) as conn:
            conn.execute(
                "INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES(?,?,?,?,?)",
                (document_id, story_node_id, document_kind, title, now_iso()),
            )
            conn.commit()
            self.index_search(conn, "document", document_id, title, "")

    def latest_revision(self, conn: sqlite3.Connection, document_id: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM document_revisions WHERE document_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (document_id,),
        ).fetchone()

    def save_revision(
        self,
        project_id: str,
        document_id: str,
        content: str,
        *,
        expected_parent_revision_id: str | None,
        source: str,
        authority_class: str = "proposal",
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if authority_class not in {"proposal", "review"}:
            raise ValueError("ordinary revision persistence may only create proposal or review state")
        with self.open_project(project_id) as conn:
            latest = self.latest_revision(conn, document_id)
            actual = latest["revision_id"] if latest else None
            if actual != expected_parent_revision_id:
                raise ConflictError(f"revision conflict: expected parent {expected_parent_revision_id!r}, current {actual!r}")
            fp = fingerprint_text(content)
            existing = conn.execute(
                "SELECT revision_id FROM document_revisions WHERE document_id=? AND content_fingerprint=?",
                (document_id, fp),
            ).fetchone()
            if existing:
                return {"revision_id": existing["revision_id"], "content_fingerprint": fp, "deduplicated": True}
            revision_id = "rev_" + uuid.uuid4().hex
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO document_revisions(
                revision_id,document_id,parent_revision_id,content,content_fingerprint,created_at,source,authority_class,provenance_json)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    revision_id,
                    document_id,
                    expected_parent_revision_id,
                    content,
                    fp,
                    now_iso(),
                    source,
                    authority_class,
                    canonical_json(provenance or {}),
                ),
            )
            title_row = conn.execute("SELECT title FROM documents WHERE document_id=?", (document_id,)).fetchone()
            if not title_row:
                conn.rollback()
                raise KeyError(f"unknown document: {document_id}")
            self.index_search(conn, "document", document_id, title_row["title"], content, commit=False)
            conn.commit()
            return {"revision_id": revision_id, "content_fingerprint": fp, "deduplicated": False}

    def compare_revisions(self, project_id: str, left_revision_id: str, right_revision_id: str) -> dict[str, Any]:
        import difflib
        with self.open_project(project_id) as conn:
            rows = conn.execute(
                "SELECT revision_id,content,content_fingerprint FROM document_revisions WHERE revision_id IN (?,?)",
                (left_revision_id, right_revision_id),
            ).fetchall()
        by_id = {row["revision_id"]: row for row in rows}
        if set(by_id) != {left_revision_id, right_revision_id}:
            raise KeyError("revision not found")
        left = by_id[left_revision_id]
        right = by_id[right_revision_id]
        diff = list(
            difflib.unified_diff(
                left["content"].splitlines(), right["content"].splitlines(),
                fromfile=left_revision_id, tofile=right_revision_id, lineterm=""
            )
        )
        return {
            "left_fingerprint": left["content_fingerprint"],
            "right_fingerprint": right["content_fingerprint"],
            "diff": diff,
        }

    def index_search(
        self,
        conn: sqlite3.Connection,
        entity_type: str,
        entity_id: str,
        title: str,
        body: str,
        *,
        commit: bool = True,
    ) -> None:
        conn.execute("DELETE FROM search_index WHERE entity_type=? AND entity_id=?", (entity_type, entity_id))
        conn.execute(
            "INSERT INTO search_index(entity_type,entity_id,title,body) VALUES(?,?,?,?)",
            (entity_type, entity_id, title, body),
        )
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "search_trigram" in tables:
            conn.execute("DELETE FROM search_trigram WHERE entity_type=? AND entity_id=?", (entity_type, entity_id))
            conn.execute(
                "INSERT INTO search_trigram(entity_type,entity_id,title,body) VALUES(?,?,?,?)",
                (entity_type, entity_id, title, body),
            )
        if commit:
            conn.commit()

    @staticmethod
    def _literal_search_rows(conn: sqlite3.Connection, query: str, limit: int) -> list[sqlite3.Row]:
        escaped = query.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        return conn.execute(
            "SELECT entity_type,entity_id,title,body AS snippet,0.0 AS rank "
            "FROM search_index WHERE lower(title) LIKE ? ESCAPE '\\' OR lower(body) LIKE ? ESCAPE '\\' LIMIT ?",
            (pattern, pattern, limit),
        ).fetchall()

    def search(self, project_id: str, query: str, limit: int = 30) -> list[dict[str, Any]]:
        needle = query.strip()
        if not needle:
            return []
        bounded_limit = max(1, min(limit, 100))
        with self.open_project(project_id) as conn:
            tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            use_trigram = "search_trigram" in tables and len(needle) >= 3
            table = "search_trigram" if use_trigram else "search_index"
            try:
                rows = conn.execute(
                    f"SELECT entity_type,entity_id,title,snippet({table},3,'‹','›','…',18) AS snippet,rank "
                    f"FROM {table} WHERE {table} MATCH ? ORDER BY rank LIMIT ?",
                    (needle, bounded_limit),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
            # FTS unicode tokenization is not a substring guarantee. In particular,
            # short CJK queries such as "门开" may legally produce no MATCH rows.
            # A bounded literal fallback preserves predictable manuscript search
            # without pretending tokenizer failure means the text is absent.
            if not rows:
                rows = self._literal_search_rows(conn, needle, bounded_limit)
            return [dict(row) for row in rows]

    def put_blob(self, project_id: str, data: bytes, media_type: str | None = None) -> dict[str, Any]:
        fp = fingerprint_bytes(data)
        hex_digest = fp.split(":", 1)[1]
        loc = self.location(project_id)
        loc.blobs.mkdir(parents=True, exist_ok=True)
        target = loc.blobs / hex_digest[:2] / hex_digest[2:]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and fingerprint_bytes(target.read_bytes()) != fp:
            raise IntegrityError("blob path exists with fingerprint mismatch")
        if not target.exists():
            tmp = target.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, target)
        rel = target.relative_to(loc.directory).as_posix()
        with self.open_project(project_id) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO blob_refs(fingerprint,relative_path,media_type,byte_size,created_at) VALUES(?,?,?,?,?)",
                (fp, rel, media_type, len(data), now_iso()),
            )
            conn.commit()
        return {"fingerprint": fp, "relative_path": rel, "byte_size": len(data)}

    def _snapshot(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with _connect(source) as src, sqlite3.connect(destination, factory=_ClosingConnection) as dst:
            src.execute("PRAGMA wal_checkpoint(PASSIVE)")
            src.backup(dst)
        with sqlite3.connect(destination, factory=_ClosingConnection) as check:
            if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise IntegrityError("backup snapshot failed quick_check")

    def backup_project(self, project_id: str, destination: Path | None = None) -> Path:
        loc = self.location(project_id)
        if not loc.database.exists():
            raise FileNotFoundError(project_id)
        self.backups_root.mkdir(parents=True, exist_ok=True)
        backup_id = "backup_" + uuid.uuid4().hex
        target = destination or (self.backups_root / f"{project_id}-{backup_id}.qfbackup")
        with tempfile.TemporaryDirectory(prefix="quillframe-backup-") as td:
            temp = Path(td)
            db_copy = temp / "project.sqlite"
            self._snapshot(loc.database, db_copy)
            blobs: list[dict[str, Any]] = []
            with self.open_project(project_id) as conn:
                for row in conn.execute("SELECT fingerprint,relative_path,byte_size FROM blob_refs ORDER BY relative_path"):
                    p = loc.directory / row["relative_path"]
                    if not p.exists() or fingerprint_bytes(p.read_bytes()) != row["fingerprint"]:
                        raise IntegrityError(f"cannot back up invalid blob: {row['relative_path']}")
                    blobs.append(dict(row))
            manifest = {
                "schema": "quillframe_backup_bundle_v1",
                "backup_id": backup_id,
                "project_id": project_id,
                "created_at": now_iso(),
                "database_fingerprint": fingerprint_bytes(db_copy.read_bytes()),
                "blobs": blobs,
            }
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_copy, "project.sqlite")
                zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
                for row in blobs:
                    zf.write(loc.directory / row["relative_path"], row["relative_path"])
        if not self.verify_backup(target)["valid"]:
            raise IntegrityError("backup verification failed")
        with _connect(self.global_db) as conn:
            conn.execute(
                "INSERT INTO backup_metadata(backup_id,project_id,bundle_path,manifest_json,verified,created_at) VALUES(?,?,?,?,1,?)",
                (backup_id, project_id, str(target), canonical_json(manifest), now_iso()),
            )
            conn.commit()
        return target

    def verify_backup(self, bundle: Path) -> dict[str, Any]:
        errors: list[str] = []
        try:
            with zipfile.ZipFile(bundle) as zf:
                manifest = json.loads(zf.read("manifest.json"))
                db = zf.read("project.sqlite")
                if fingerprint_bytes(db) != manifest.get("database_fingerprint"):
                    errors.append("database fingerprint mismatch")
                for row in manifest.get("blobs", []):
                    try:
                        payload = zf.read(row["relative_path"])
                    except KeyError:
                        errors.append(f"missing blob {row['relative_path']}")
                        continue
                    if fingerprint_bytes(payload) != row["fingerprint"]:
                        errors.append(f"blob fingerprint mismatch {row['relative_path']}")
                with tempfile.NamedTemporaryFile(suffix=".sqlite") as temp:
                    temp.write(db); temp.flush()
                    with sqlite3.connect(temp.name, factory=_ClosingConnection) as conn:
                        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                            errors.append("database quick_check failed")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
        return {"valid": not errors, "errors": errors}

    def restore_project(self, bundle: Path, *, replace: bool = False) -> ProjectLocation:
        verification = self.verify_backup(bundle)
        if not verification["valid"]:
            raise IntegrityError("invalid backup: " + "; ".join(verification["errors"]))
        self.ensure_layout()
        with zipfile.ZipFile(bundle) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            project_id = manifest["project_id"]
            loc = self.location(project_id)
            if loc.directory.exists() and not replace:
                raise FileExistsError(f"project already exists: {project_id}")
            with tempfile.TemporaryDirectory(prefix="quillframe-restore-", dir=self.root) as td:
                stage = Path(td) / project_id
                zf.extractall(stage)
                with sqlite3.connect(stage / "project.sqlite", factory=_ClosingConnection) as conn:
                    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise IntegrityError("restored database failed integrity_check")
                if loc.directory.exists():
                    rollback = loc.directory.with_name(loc.directory.name + ".restore-rollback")
                    if rollback.exists(): shutil.rmtree(rollback)
                    os.replace(loc.directory, rollback)
                loc.directory.parent.mkdir(parents=True, exist_ok=True)
                os.replace(stage, loc.directory)
        self.initialize_global()
        with self.open_project(project_id) as conn:
            identity = conn.execute("SELECT * FROM project_identity").fetchone()
        if not identity:
            raise IntegrityError("restored project has no identity")
        self.create_project(project_id, identity["title"], identity["language"])
        return loc

    def doctor(self, project_id: str | None = None, *, fix: bool = False) -> dict[str, Any]:
        if fix:
            self.ensure_layout()
            self.initialize_global()
        checks: list[dict[str, Any]] = []
        errors: list[str] = []

        def check_db(label: str, path: Path, scope: str, blobs_root: Path | None = None) -> None:
            if not path.exists():
                checks.append({"check": label, "status": "missing"})
                if scope == "project": errors.append(f"missing project database: {path}")
                return
            try:
                with _connect(path) as conn:
                    apply_migrations(conn, scope)
                    quick = conn.execute("PRAGMA quick_check").fetchone()[0]
                    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                    foreign = [dict(r) for r in conn.execute("PRAGMA foreign_key_check")]
                    journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
                    if fix: conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    status = "ok" if quick == "ok" and integrity == "ok" and not foreign and journal.lower() == "wal" else "error"
                    detail: dict[str, Any] = {"quick_check": quick, "integrity_check": integrity, "foreign_keys": foreign, "journal_mode": journal}
                    if blobs_root is not None:
                        missing: list[str] = []; mismatched: list[str] = []; referenced: set[Path] = set()
                        for row in conn.execute("SELECT fingerprint,relative_path FROM blob_refs"):
                            p = blobs_root.parent / row["relative_path"]
                            referenced.add(p.resolve())
                            if not p.exists(): missing.append(row["relative_path"])
                            elif fingerprint_bytes(p.read_bytes()) != row["fingerprint"]: mismatched.append(row["relative_path"])
                        orphan = []
                        if blobs_root.exists():
                            for p in blobs_root.rglob("*"):
                                if p.is_file() and p.resolve() not in referenced: orphan.append(p.relative_to(blobs_root.parent).as_posix())
                        detail.update({"missing_blobs": missing, "mismatched_blobs": mismatched, "orphan_blobs": orphan})
                        if missing or mismatched: status = "error"
                    checks.append({"check": label, "status": status, "detail": detail})
                    if status == "error": errors.append(f"{label} failed")
            except Exception as exc:
                checks.append({"check": label, "status": "error", "error": f"{type(exc).__name__}: {exc}"})
                errors.append(f"{label}: {exc}")

        check_db("global_database", self.global_db, "global")
        if project_id:
            loc = self.location(project_id)
            check_db("project_database", loc.database, "project", loc.blobs)
        if self.global_db.exists():
            with _connect(self.global_db) as conn:
                stale = [dict(r) for r in conn.execute("SELECT project_id,project_dir FROM project_registry") if not Path(r["project_dir"]).exists()]
                if fix:
                    for row in stale:
                        conn.execute("DELETE FROM project_registry WHERE project_id=?", (row["project_id"],))
                    conn.commit()
                checks.append({"check": "project_registry", "status": "ok" if not stale or fix else "warning", "stale": stale, "fixed": bool(stale and fix)})
        return {"schema": "quillframe_doctor_v1", "ok": not errors, "fix": fix, "data_root": str(self.root), "checks": checks, "errors": errors}
