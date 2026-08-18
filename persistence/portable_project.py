from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .quillframe_sqlite import (
    IntegrityError,
    QuillframeStore,
    canonical_json,
    fingerprint_bytes,
    now_iso,
)

PORTABLE_SCHEMA = "quillframe_portable_project_v1"
PORTABLE_FORMAT_VERSION = 1
MAX_PORTABLE_BYTES = 32 * 1024 * 1024


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "" not in path.parts


def _sqlite_snapshot(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(source, timeout=5.0)
    dst = sqlite3.connect(destination)
    try:
        src.execute("PRAGMA wal_checkpoint(PASSIVE)")
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    with sqlite3.connect(destination) as check:
        if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise IntegrityError("portable project snapshot failed quick_check")


def _read_identity(database: Path) -> dict[str, Any]:
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise IntegrityError("portable project database failed integrity_check")
        row = conn.execute("SELECT * FROM project_identity").fetchone()
    if not row:
        raise IntegrityError("portable project database has no project identity")
    return dict(row)


class PortableProjectService:
    """Portable Web↔Tauri project packages.

    The package deliberately excludes global SQLite state, provider/model service
    configuration, credentials, caches, backups and publication exports. It is a
    project transfer format, not another live authority.
    """

    def __init__(self, store: QuillframeStore | None = None) -> None:
        self.store = store or QuillframeStore()

    def export_project(self, project_id: str) -> dict[str, Any]:
        loc = self.store.location(project_id)
        if not loc.database.is_file():
            raise FileNotFoundError(project_id)
        loc.exports.mkdir(parents=True, exist_ok=True)
        export_id = "portable_" + uuid.uuid4().hex
        target = loc.exports / f"{project_id}-{export_id}.qfproject"
        with tempfile.TemporaryDirectory(prefix="quillframe-portable-export-") as td:
            temp = Path(td)
            db_copy = temp / "project.sqlite"
            _sqlite_snapshot(loc.database, db_copy)
            identity = _read_identity(db_copy)
            if identity.get("project_id") != project_id:
                raise IntegrityError("portable export project identity mismatch")

            blobs: list[dict[str, Any]] = []
            with self.store.open_project(project_id) as conn:
                rows = list(conn.execute("SELECT fingerprint,relative_path,byte_size FROM blob_refs ORDER BY relative_path"))
            for row in rows:
                relative = str(row["relative_path"])
                if not _safe_member(relative) or not relative.startswith("blobs/"):
                    raise IntegrityError(f"invalid blob path in project: {relative}")
                source = loc.directory / relative
                if not source.is_file():
                    raise IntegrityError(f"missing portable blob: {relative}")
                payload = source.read_bytes()
                if fingerprint_bytes(payload) != row["fingerprint"]:
                    raise IntegrityError(f"portable blob fingerprint mismatch: {relative}")
                blobs.append({"relative_path": relative, "fingerprint": row["fingerprint"], "byte_size": len(payload)})

            manifest = {
                "schema": PORTABLE_SCHEMA,
                "format_version": PORTABLE_FORMAT_VERSION,
                "framework_line": "0.9.x",
                "project_id": project_id,
                "title": identity.get("title"),
                "language": identity.get("language"),
                "project_schema_version": identity.get("project_schema_version"),
                "created_at": now_iso(),
                "database": {
                    "path": "project.sqlite",
                    "fingerprint": fingerprint_bytes(db_copy.read_bytes()),
                },
                "blobs": blobs,
                "credentials_included": False,
                "global_database_included": False,
                "authority": False,
            }
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_copy, "project.sqlite")
                zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
                for blob in blobs:
                    zf.write(loc.directory / blob["relative_path"], blob["relative_path"])
        verification = self.verify(target)
        if not verification["valid"]:
            target.unlink(missing_ok=True)
            raise IntegrityError("portable export verification failed: " + "; ".join(verification["errors"]))
        return {
            "schema": "quillframe_portable_export_result_v1",
            "project_id": project_id,
            "artifact_ref": f"project-export:{project_id}:{target.name}",
            "file_name": target.name,
            "bundle_fingerprint": fingerprint_bytes(target.read_bytes()),
            "byte_size": target.stat().st_size,
            "credentials_included": False,
            "authority": False,
        }

    def verify(self, bundle: Path) -> dict[str, Any]:
        errors: list[str] = []
        manifest: dict[str, Any] | None = None
        try:
            if not bundle.is_file():
                raise FileNotFoundError(bundle)
            if bundle.stat().st_size > MAX_PORTABLE_BYTES:
                raise IntegrityError("portable project exceeds maximum supported size")
            with zipfile.ZipFile(bundle) as zf:
                names = zf.namelist()
                if any(not _safe_member(name) for name in names):
                    errors.append("archive contains unsafe path")
                if len(names) != len(set(names)):
                    errors.append("archive contains duplicate paths")
                if "manifest.json" not in names or "project.sqlite" not in names:
                    errors.append("archive is missing manifest.json or project.sqlite")
                if errors:
                    return {"valid": False, "errors": errors, "manifest": None}
                manifest = json.loads(zf.read("manifest.json"))
                if manifest.get("schema") != PORTABLE_SCHEMA or manifest.get("format_version") != PORTABLE_FORMAT_VERSION:
                    errors.append("unsupported portable project schema/version")
                if manifest.get("credentials_included") is not False or manifest.get("global_database_included") is not False:
                    errors.append("portable manifest violates credential/global-state exclusion")
                db = zf.read("project.sqlite")
                database = manifest.get("database") if isinstance(manifest.get("database"), dict) else {}
                if database.get("path") != "project.sqlite" or fingerprint_bytes(db) != database.get("fingerprint"):
                    errors.append("database fingerprint mismatch")
                for blob in manifest.get("blobs", []):
                    if not isinstance(blob, dict):
                        errors.append("invalid blob manifest entry")
                        continue
                    relative = str(blob.get("relative_path") or "")
                    if not _safe_member(relative) or not relative.startswith("blobs/"):
                        errors.append(f"unsafe blob path: {relative}")
                        continue
                    try:
                        payload = zf.read(relative)
                    except KeyError:
                        errors.append(f"missing blob: {relative}")
                        continue
                    if fingerprint_bytes(payload) != blob.get("fingerprint"):
                        errors.append(f"blob fingerprint mismatch: {relative}")
                with tempfile.NamedTemporaryFile(suffix=".sqlite") as temp:
                    temp.write(db)
                    temp.flush()
                    identity = _read_identity(Path(temp.name))
                if identity.get("project_id") != manifest.get("project_id"):
                    errors.append("embedded project identity mismatch")
                allowed = {"manifest.json", "project.sqlite", *[str(x.get("relative_path")) for x in manifest.get("blobs", []) if isinstance(x, dict)]}
                unexpected = sorted(set(names) - allowed)
                if unexpected:
                    errors.append("unexpected portable project members: " + ", ".join(unexpected[:10]))
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
        return {"valid": not errors, "errors": errors, "manifest": manifest if not errors else None}

    def import_project(self, bundle: Path, *, replace: bool = False) -> dict[str, Any]:
        verification = self.verify(bundle)
        if not verification["valid"]:
            raise IntegrityError("invalid portable project: " + "; ".join(verification["errors"]))
        manifest = verification["manifest"] or {}
        project_id = str(manifest["project_id"])
        loc = self.store.location(project_id)
        if loc.directory.exists() and not replace:
            raise FileExistsError(f"project already exists: {project_id}")
        self.store.ensure_layout()
        rollback: Path | None = None
        with zipfile.ZipFile(bundle) as zf, tempfile.TemporaryDirectory(prefix="quillframe-portable-import-", dir=self.store.root) as td:
            stage = Path(td) / project_id
            stage.mkdir(parents=True, exist_ok=True)
            for name in zf.namelist():
                destination = stage / PurePosixPath(name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(zf.read(name))
            (stage / "manifest.json").unlink(missing_ok=True)
            identity = _read_identity(stage / "project.sqlite")
            if identity.get("project_id") != project_id:
                raise IntegrityError("staged portable project identity mismatch")
            if loc.directory.exists():
                rollback = loc.directory.with_name(loc.directory.name + ".portable-rollback-" + uuid.uuid4().hex)
                os.replace(loc.directory, rollback)
            loc.directory.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(stage, loc.directory)
            except Exception:
                if rollback and rollback.exists() and not loc.directory.exists():
                    os.replace(rollback, loc.directory)
                raise
        try:
            self.store.create_project(project_id, str(identity["title"]), str(identity["language"]))
            doctor = self.store.doctor(project_id)
            if not doctor.get("ok"):
                raise IntegrityError("imported project failed doctor")
        except Exception:
            if rollback and rollback.exists():
                if loc.directory.exists():
                    shutil.rmtree(loc.directory)
                os.replace(rollback, loc.directory)
            raise
        if rollback and rollback.exists():
            shutil.rmtree(rollback)
        return {
            "schema": "quillframe_portable_import_result_v1",
            "project_id": project_id,
            "imported": True,
            "replaced": replace,
            "bundle_fingerprint": fingerprint_bytes(bundle.read_bytes()),
            "credentials_imported": False,
            "authority": False,
        }

    def resolve_export_artifact(self, artifact_ref: str) -> Path:
        parts = artifact_ref.split(":", 2)
        if len(parts) != 3 or parts[0] != "project-export":
            raise ValueError("unsupported artifact_ref")
        project_id, file_name = parts[1], parts[2]
        if Path(file_name).name != file_name or not file_name.endswith(".qfproject"):
            raise ValueError("invalid export artifact_ref")
        path = self.store.location(project_id).exports / file_name
        if not path.is_file():
            raise FileNotFoundError(artifact_ref)
        return path

    def stage_import_payload(self, file_name: str, payload: bytes) -> str:
        if Path(file_name).name != file_name or not file_name.endswith(".qfproject"):
            raise ValueError("import file must be a .qfproject filename")
        if not payload or len(payload) > MAX_PORTABLE_BYTES:
            raise ValueError("portable import payload size is invalid")
        root = self.store.cache_root / "portable-imports"
        root.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        target = root / f"{token}.qfproject"
        target.write_bytes(payload)
        verification = self.verify(target)
        if not verification["valid"]:
            target.unlink(missing_ok=True)
            raise IntegrityError("invalid uploaded portable project: " + "; ".join(verification["errors"]))
        return f"project-import:{token}"

    def resolve_import_artifact(self, artifact_ref: str) -> Path:
        prefix = "project-import:"
        if not artifact_ref.startswith(prefix):
            raise ValueError("unsupported import artifact_ref")
        token = artifact_ref[len(prefix):]
        if not token or any(ch not in "0123456789abcdef" for ch in token):
            raise ValueError("invalid import artifact_ref")
        target = self.store.cache_root / "portable-imports" / f"{token}.qfproject"
        if not target.is_file():
            raise FileNotFoundError(artifact_ref)
        return target
