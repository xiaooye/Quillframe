"""Native, retryable publication artifacts for Core Q2-B.

Publication is a non-authoritative projection of an Accepted artifact.  The
SQLite attempt ledger is the durable protocol; filesystem publication is
deliberately no-clobber and never pretends to be one transaction with SQLite.
"""
from __future__ import annotations

import base64
import errno
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

from persistence.quillframe_sqlite import (
    BackupPublishError,
    QuillframeStore,
    RestoreConflictError,
    RestoreIncompleteError,
    _linkat_empty_path,
    _rename_noreplace,
    canonical_json,
    fingerprint_bytes,
    now_iso,
)


COMPILER_CONTRACT = "quillframe_core_publication_text_v1"
SUPPORTED_FORMATS = frozenset({"md", "txt"})
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_RECOVERY_ATTEMPTS = 32
_BUILD_ID_RE = re.compile(r"\Apub_[0-9a-f]{64}\Z")
_NAME_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


class PublicationRecoveryError(RuntimeError):
    """Stable public error for the Core publication protocol."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        self.message = message or _PUBLIC_MESSAGES.get(code, "publication operation failed")
        super().__init__(self.message)


_PUBLIC_MESSAGES = {
    "publication_source_invalid": "publication source is not an intact Accepted artifact",
    "publication_identity_conflict": "publication identity conflicts with committed evidence",
    "publication_attempt_invalid": "publication attempt ledger is invalid",
    "publication_artifact_invalid": "publication artifact is invalid",
    "publication_stage_invalid": "publication stage is invalid",
    "publication_target_exists": "publication target already exists",
    "publication_path_invalid": "publication path is not a native project path",
    "publication_native_unavailable": "native publication is unavailable",
    "publication_durability": "publication durability could not be established",
    "publication_db": "publication ledger transaction failed",
    "publication_fault": "publication failure was injected",
    "publication_recovery_bounded": "publication recovery exceeded its bound",
    "publication_recovery_required": "publication recovery requires preserved evidence",
    "publication_missing": "publication evidence is missing",
    "publication_source_changed": "publication source changed after staging",
    "publication_ambiguous": "publication ownership is ambiguous",
    "publication_attempt_failed": "publication attempt is failed evidence",
    "publication_authorization_required": "publication collection build requires author authorization",
    "publication_idempotency_required": "publication collection build requires a bounded idempotency key",
    "unsupported_export_format": "Quillframe 1.0 supports only md and txt publication exports",
}


@dataclass(frozen=True)
class _Source:
    project_id: str
    source_key: str
    source_fingerprint: str
    content: str
    document_id: str
    revision_id: str
    candidate_id: str


@dataclass(frozen=True)
class _Plan:
    project_id: str
    source_key: str
    fmt: str
    compiler_contract: str
    source_fingerprint: str
    content: bytes
    artifact_fingerprint: str
    byte_size: int
    identity_fingerprint: str
    build_id: str
    owner_token: str
    stage_ref: str
    final_ref: str


def _fault_safe(injector: Callable[[str, str], Any] | None, phase: str, build_id: str) -> None:
    if injector is None:
        return
    try:
        injector(phase, build_id)
    except PublicationRecoveryError:
        raise
    except Exception as exc:
        raise PublicationRecoveryError("publication_fault") from exc


def _is_linux_native() -> bool:
    return sys.platform == "linux" and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")


def _safe_lstat(directory_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.lstat(name, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PublicationRecoveryError("publication_path_invalid") from exc


def _safe_ref(ref: Any, *, build_id: str, fmt: str, stage: bool) -> str:
    if not isinstance(ref, str) or "\x00" in ref or "\\" in ref:
        raise PublicationRecoveryError("publication_attempt_invalid")
    try:
        parts = PurePosixPath(ref).parts
    except (TypeError, ValueError) as exc:
        raise PublicationRecoveryError("publication_attempt_invalid") from exc
    if parts[0:1] != ("exports",) or len(parts) != 2 or any(part in {"", ".", ".."} for part in parts):
        raise PublicationRecoveryError("publication_attempt_invalid")
    expected = f".{build_id}.stage" if stage else f"{build_id}.{fmt}"
    name_for_re = parts[1][1:] if stage and parts[1].startswith(".") else parts[1]
    if parts[1] != expected or not _NAME_RE.fullmatch(name_for_re):
        raise PublicationRecoveryError("publication_attempt_invalid")
    return parts[1]


def _file_signature(value: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _safe_file_bytes(
    directory_fd: int,
    name: str,
    *,
    expected_fingerprint: str,
    expected_size: int,
    expected_inode: tuple[int, int] | None,
    stage: bool,
    mutation_hook: Callable[[str], Any] | None = None,
    capture: bool = False,
) -> os.stat_result | tuple[os.stat_result, bytes]:
    """Read one regular no-follow inode and prove it did not change."""

    fd: int | None = None
    try:
        before = _safe_lstat(directory_fd, name)
        if before is None or stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
        if expected_inode is not None and (before.st_dev, before.st_ino) != expected_inode:
            raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
        if _file_signature(opened) != _file_signature(before):
            raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
        if opened.st_size != expected_size or expected_size > MAX_ARTIFACT_BYTES:
            raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, MAX_ARTIFACT_BYTES + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ARTIFACT_BYTES:
                raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
            digest.update(chunk)
        if mutation_hook is not None:
            try:
                mutation_hook("after_first_read")
            except PublicationRecoveryError:
                raise
            except Exception as exc:
                raise PublicationRecoveryError("publication_fault") from exc
        after = os.fstat(fd)
        latest = _safe_lstat(directory_fd, name)
        if latest is None or _file_signature(after) != _file_signature(opened) or _file_signature(latest) != _file_signature(opened):
            raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
        if after.st_size != expected_size or latest.st_size != expected_size or total != expected_size or "sha256:" + digest.hexdigest() != expected_fingerprint:
            raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
        os.lseek(fd, 0, os.SEEK_SET)
        if mutation_hook is not None:
            try:
                mutation_hook("before_second_read")
            except PublicationRecoveryError:
                raise
            except Exception as exc:
                raise PublicationRecoveryError("publication_fault") from exc
        second_digest = hashlib.sha256()
        second_total = 0
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, min(1024 * 1024, MAX_ARTIFACT_BYTES + 1))
            if not chunk:
                break
            second_total += len(chunk)
            if second_total > MAX_ARTIFACT_BYTES:
                raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
            second_digest.update(chunk)
            if capture:
                chunks.append(chunk)
        if mutation_hook is not None:
            try:
                mutation_hook("after_second_read")
            except PublicationRecoveryError:
                raise
            except Exception as exc:
                raise PublicationRecoveryError("publication_fault") from exc
        after_second = os.fstat(fd)
        latest_second = _safe_lstat(directory_fd, name)
        if (
            latest_second is None
            or _file_signature(after_second) != _file_signature(opened)
            or _file_signature(latest_second) != _file_signature(opened)
            or after_second.st_size != expected_size
            or latest_second.st_size != expected_size
            or second_total != expected_size
            or second_digest.digest() != digest.digest()
            or "sha256:" + second_digest.hexdigest() != expected_fingerprint
        ):
            raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid")
        return (after_second, b"".join(chunks)) if capture else after_second
    except PublicationRecoveryError:
        raise
    except (OSError, ValueError) as exc:
        raise PublicationRecoveryError("publication_stage_invalid" if stage else "publication_artifact_invalid") from exc
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _assert_real_path(path: Path) -> None:
    current = path
    missing = False
    chain: list[Path] = []
    while True:
        chain.append(current)
        if current == current.parent:
            break
        current = current.parent
    for item in reversed(chain):
        try:
            value = os.lstat(item)
        except FileNotFoundError as exc:
            missing = True
            raise PublicationRecoveryError("publication_path_invalid") from exc
        except OSError as exc:
            raise PublicationRecoveryError("publication_path_invalid") from exc
        if stat.S_ISLNK(value.st_mode) or not stat.S_ISDIR(value.st_mode):
            raise PublicationRecoveryError("publication_path_invalid")
    if missing:  # pragma: no cover - defensive branch for static analyzers
        raise PublicationRecoveryError("publication_path_invalid")


def _open_existing_directory_chain(path: Path) -> int:
    """Open an existing directory chain using only descriptor-relative steps."""

    absolute = Path(os.path.abspath(os.fspath(path)))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    current: int | None = None
    try:
        current = os.open(absolute.anchor or os.sep, flags)
        for part in absolute.parts[1:]:
            if part in {"", ".", ".."}:
                raise PublicationRecoveryError("publication_path_invalid")
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
        result = current
        current = None
        return result
    except PublicationRecoveryError:
        raise
    except OSError as exc:
        raise PublicationRecoveryError("publication_path_invalid") from exc
    finally:
        if current is not None:
            try:
                os.close(current)
            except OSError:
                pass


class PublicationRecovery:
    """Core-owned publication build and bounded recovery protocol."""

    attempts_table = "publication_build_attempts"
    builds_table = "publication_builds"
    source_column = "source_acceptance_id"
    compiler_contract = COMPILER_CONTRACT

    def __init__(
        self,
        store: QuillframeStore,
        *,
        fault_injector: Callable[[str, str], Any] | None = None,
    ) -> None:
        self.store = store
        self.fault_injector = fault_injector

    def _file_hook(self, phase: str, build_id: str) -> Callable[[str], Any] | None:
        if self.fault_injector is None:
            return None
        return lambda point: _fault_safe(self.fault_injector, f"file_{phase}_{point}", build_id)

    @contextmanager
    def _project_lock(self, project_id: str) -> Iterator[Any]:
        if not _is_linux_native():
            raise PublicationRecoveryError("publication_native_unavailable")
        try:
            loc = self.store.location(project_id)
        except (TypeError, ValueError) as exc:
            raise PublicationRecoveryError("publication_path_invalid") from exc
        try:
            db_stat = os.lstat(loc.database)
            if stat.S_ISLNK(db_stat.st_mode) or not stat.S_ISREG(db_stat.st_mode):
                raise PublicationRecoveryError("publication_path_invalid")
            _assert_real_path(loc.directory)
            _assert_real_path(loc.exports)
            parent_fd = _open_existing_directory_chain(loc.database.parent)
            try:
                fd = os.open(loc.database.name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), dir_fd=parent_fd)
            finally:
                os.close(parent_fd)
        except PublicationRecoveryError:
            raise
        except OSError as exc:
            raise PublicationRecoveryError("publication_path_invalid") from exc
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
            except OSError as exc:
                raise PublicationRecoveryError("publication_native_unavailable") from exc
            yield loc
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(fd)
            except OSError:
                pass

    @staticmethod
    def _exports_fd(loc: Any) -> int:
        try:
            return _open_existing_directory_chain(loc.exports)
        except (OSError, PublicationRecoveryError) as exc:
            if isinstance(exc, PublicationRecoveryError):
                raise
            raise PublicationRecoveryError("publication_path_invalid") from exc

    @staticmethod
    def _source(conn: Any, project_id: str, acceptance_id: str) -> _Source:
        row = conn.execute(
            """SELECT a.acceptance_id,a.candidate_id,a.candidate_fingerprint,c.status,c.document_id,c.revision_id,
            r.content,r.content_fingerprint,r.authority_class,
            c.content_fingerprint AS candidate_content_fingerprint,r.document_id AS revision_document_id
            FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id
            JOIN document_revisions r ON r.revision_id=c.revision_id
            WHERE a.acceptance_id=?""",
            (acceptance_id,),
        ).fetchone()
        if not row:
            raise PublicationRecoveryError("publication_source_invalid")
        try:
            content_fingerprint = fingerprint_bytes(row["content"].encode("utf-8")) if isinstance(row["content"], str) else None
        except UnicodeError as exc:
            raise PublicationRecoveryError("publication_source_invalid") from exc
        if (
            row["status"] != "accepted"
            or row["authority_class"] != "accepted"
            or row["candidate_fingerprint"] != row["content_fingerprint"]
            or row["candidate_content_fingerprint"] != row["content_fingerprint"]
            or row["document_id"] != row["revision_document_id"]
            or not isinstance(row["content"], str)
            or content_fingerprint != row["content_fingerprint"]
        ):
            raise PublicationRecoveryError("publication_source_invalid")
        return _Source(
            project_id=project_id,
            source_key=acceptance_id,
            source_fingerprint=row["content_fingerprint"],
            content=row["content"],
            document_id=row["document_id"],
            revision_id=row["revision_id"],
            candidate_id=row["candidate_id"],
        )

    def _plan(self, source: _Source, fmt: str) -> _Plan:
        if fmt not in SUPPORTED_FORMATS:
            raise PublicationRecoveryError("publication_source_invalid")
        try:
            content = source.content.encode("utf-8")
        except UnicodeError as exc:
            raise PublicationRecoveryError("publication_source_invalid") from exc
        if len(content) > MAX_ARTIFACT_BYTES:
            raise PublicationRecoveryError("publication_artifact_invalid")
        identity_payload = {
            "project_id": source.project_id,
            self.source_column: source.source_key,
            "format": fmt,
            "source_fingerprint": source.source_fingerprint,
            "compiler_contract": self.compiler_contract,
        }
        identity_fingerprint = fingerprint_bytes(canonical_json(identity_payload).encode("utf-8"))
        build_id = "pub_" + identity_fingerprint.split(":", 1)[1]
        return _Plan(
            project_id=source.project_id,
            source_key=source.source_key,
            fmt=fmt,
            compiler_contract=self.compiler_contract,
            source_fingerprint=source.source_fingerprint,
            content=content,
            artifact_fingerprint=fingerprint_bytes(content),
            byte_size=len(content),
            identity_fingerprint=identity_fingerprint,
            build_id=build_id,
            owner_token="qfpub:" + identity_fingerprint,
            stage_ref=f"exports/.{build_id}.stage",
            final_ref=f"exports/{build_id}.{fmt}",
        )

    def _validate_row(self, row: Any, plan: _Plan) -> None:
        if not row:
            raise PublicationRecoveryError("publication_attempt_invalid")
        expected = {
            "build_id": plan.build_id,
            "identity_fingerprint": plan.identity_fingerprint,
            "project_id": plan.project_id,
            self.source_column: plan.source_key,
            "format": plan.fmt,
            "compiler_contract": plan.compiler_contract,
            "source_fingerprint": plan.source_fingerprint,
            "artifact_fingerprint": plan.artifact_fingerprint,
            "byte_size": plan.byte_size,
            "owner_token": plan.owner_token,
            "stage_ref": plan.stage_ref,
            "final_ref": plan.final_ref,
        }
        for key, value in expected.items():
            if row[key] != value:
                raise PublicationRecoveryError("publication_attempt_invalid")
        if row["state"] not in {"staged", "published", "committed", "failed"}:
            raise PublicationRecoveryError("publication_attempt_invalid")
        _safe_ref(row["stage_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=True)
        _safe_ref(row["final_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=False)

    def _validate_committed_row(self, row: Any, plan: _Plan) -> None:
        if not row or row["build_id"] != plan.build_id or row[self.source_column] != plan.source_key:
            raise PublicationRecoveryError("publication_identity_conflict")
        if (
            row["format"] != plan.fmt
            or row["compiler_contract"] != plan.compiler_contract
            or row["output_ref"] != plan.final_ref
            or row["source_fingerprint"] != plan.source_fingerprint
        ):
            raise PublicationRecoveryError("publication_identity_conflict")
        if row["persistent"] != 1:
            raise PublicationRecoveryError("publication_attempt_invalid")
        try:
            validation = json.loads(row["validation_json"])
        except (TypeError, ValueError) as exc:
            raise PublicationRecoveryError("publication_attempt_invalid") from exc
        expected = {
            "compiler_contract": self.compiler_contract,
            "identity_fingerprint": plan.identity_fingerprint,
            "artifact_fingerprint": plan.artifact_fingerprint,
            "byte_size": plan.byte_size,
            "final_ref": plan.final_ref,
        }
        if not isinstance(validation, dict) or any(validation.get(key) != value for key, value in expected.items()):
            raise PublicationRecoveryError("publication_attempt_invalid")

    def _stage_transaction(self, project_id: str, acceptance_id: str, fmt: str) -> tuple[_Plan, Any, bool]:
        with self.store.open_project(project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                source = self._source(conn, project_id, acceptance_id)
                plan = self._plan(source, fmt)
                self._before_stage(conn, plan)
                committed = conn.execute(
                    f"SELECT * FROM {self.builds_table} WHERE {self.source_column}=? AND format=? AND source_fingerprint=? AND compiler_contract=?",
                    (acceptance_id, fmt, source.source_fingerprint, self.compiler_contract),
                ).fetchone()
                if committed:
                    if committed["build_id"] != plan.build_id or committed["output_ref"] != plan.final_ref:
                        raise PublicationRecoveryError("publication_identity_conflict")
                    attempt = conn.execute(f"SELECT * FROM {self.attempts_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                    if not attempt:
                        raise PublicationRecoveryError("publication_attempt_invalid")
                    self._validate_row(attempt, plan)
                    if attempt["state"] != "committed":
                        raise PublicationRecoveryError("publication_attempt_invalid")
                    self._validate_committed_row(committed, plan)
                    conn.commit()
                    return plan, attempt, True
                row = conn.execute(f"SELECT * FROM {self.attempts_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                created = row is None
                stamp = now_iso()
                if row:
                    self._validate_row(row, plan)
                    if row["state"] == "failed":
                        raise PublicationRecoveryError("publication_attempt_failed")
                else:
                    conn.execute(
                        f"""INSERT INTO {self.attempts_table}(
                        build_id,identity_fingerprint,project_id,{self.source_column},format,compiler_contract,
                        source_fingerprint,artifact_fingerprint,byte_size,stage_ref,final_ref,owner_token,state,
                        error_code,created_at,updated_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?, 'staged',NULL,?,?)""",
                        (
                            plan.build_id,
                            plan.identity_fingerprint,
                            plan.project_id,
                            plan.source_key,
                            plan.fmt,
                            plan.compiler_contract,
                            plan.source_fingerprint,
                            plan.artifact_fingerprint,
                            plan.byte_size,
                            plan.stage_ref,
                            plan.final_ref,
                            plan.owner_token,
                            stamp,
                            stamp,
                        ),
                    )
                    self._new_attempt(conn, plan)
                    row = conn.execute(f"SELECT * FROM {self.attempts_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                conn.commit()
                return plan, row, created
            except PublicationRecoveryError:
                if conn.in_transaction:
                    conn.rollback()
                raise
            except Exception as exc:
                if conn.in_transaction:
                    conn.rollback()
                raise PublicationRecoveryError("publication_db") from exc

    def _before_stage(self, conn: Any, plan: _Plan) -> None:
        """Extension point for a source-specific request receipt in this transaction."""

    def _new_attempt(self, conn: Any, plan: _Plan) -> None:
        """Extension point for normalized source membership in this transaction."""

    def _artifact_source(self, conn: Any, project_id: str, source_key: str) -> Any:
        return self._source(conn, project_id, source_key)

    def _source_acceptance_ids(self, plan: _Plan) -> list[str]:
        return [plan.source_key]

    def artifact(self, project_id: str, build_id: str) -> dict[str, Any]:
        """Return only fingerprint-verified bytes from an exact committed build."""
        if not isinstance(build_id, str) or not _BUILD_ID_RE.fullmatch(build_id):
            raise PublicationRecoveryError("publication_attempt_invalid")
        # Collection builds have their own ledger and normalized membership;
        # never represent them as a made-up singleton acceptance.
        if self.__class__ is PublicationRecovery:
            with self.store.open_project(project_id) as conn:
                collection = conn.execute("SELECT 1 FROM publication_collection_builds WHERE build_id=?", (build_id,)).fetchone()
            if collection:
                from .collection import CollectionPublicationRecovery
                return CollectionPublicationRecovery(self.store, fault_injector=self.fault_injector).artifact(project_id, build_id)
        with self._project_lock(project_id) as loc:
            with self.store.open_project(project_id) as conn:
                row = conn.execute(f"SELECT * FROM {self.attempts_table} WHERE project_id=? AND build_id=?", (project_id, build_id)).fetchone()
                if not row:
                    raise PublicationRecoveryError("publication_missing")
                if row["state"] != "committed":
                    raise PublicationRecoveryError("publication_recovery_required")
                source = self._artifact_source(conn, project_id, row[self.source_column])
                plan = self._plan(source, row["format"])
                self._validate_row(row, plan)
                committed = conn.execute(f"SELECT * FROM {self.builds_table} WHERE build_id=?", (build_id,)).fetchone()
                self._validate_committed_row(committed, plan)
            if row["final_dev"] is None or row["final_ino"] is None:
                raise PublicationRecoveryError("publication_attempt_invalid")
            exports_fd = self._exports_fd(loc)
            try:
                name = _safe_ref(plan.final_ref, build_id=plan.build_id, fmt=plan.fmt, stage=False)
                _, content = _safe_file_bytes(
                    exports_fd, name,
                    expected_fingerprint=plan.artifact_fingerprint,
                    expected_size=plan.byte_size,
                    expected_inode=(row["final_dev"], row["final_ino"]),
                    stage=False, capture=True,
                    mutation_hook=self._file_hook("download", plan.build_id),
                )
            finally:
                os.close(exports_fd)
        return {
            "schema": "quillframe_publication_artifact_v1",
            "project_id": project_id,
            "build_id": build_id,
            "filename": name,
            "media_type": "text/markdown;charset=utf-8" if plan.fmt == "md" else "text/plain;charset=utf-8",
            "byte_size": len(content),
            "artifact_fingerprint": fingerprint_bytes(content),
            "content_base64": base64.b64encode(content).decode("ascii"),
            "source_acceptance_ids": self._source_acceptance_ids(plan),
            "authority": False,
        }

    def build_collection(
        self, project_id: str, acceptance_ids: list[str], fmt: str = "md", *,
        idempotency_key: str, user_authorized: bool,
    ) -> dict[str, Any]:
        from .collection import CollectionPublicationRecovery
        return CollectionPublicationRecovery(self.store, fault_injector=self.fault_injector).build_collection(
            project_id, acceptance_ids, fmt,
            idempotency_key=idempotency_key, user_authorized=user_authorized,
        )

    def _record_stage_owner(self, plan: _Plan, value: os.stat_result) -> Any:
        with self.store.open_project(plan.project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(f"SELECT * FROM {self.attempts_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                self._validate_row(row, plan)
                if row["state"] != "staged":
                    conn.commit()
                    return row
                conn.execute(
                    f"UPDATE {self.attempts_table} SET stage_dev=?,stage_ino=?,updated_at=? WHERE build_id=?",
                    (value.st_dev, value.st_ino, now_iso(), plan.build_id),
                )
                conn.commit()
                return conn.execute(f"SELECT * FROM {self.attempts_table} WHERE build_id=?", (plan.build_id,)).fetchone()
            except PublicationRecoveryError:
                if conn.in_transaction:
                    conn.rollback()
                raise
            except Exception as exc:
                if conn.in_transaction:
                    conn.rollback()
                raise PublicationRecoveryError("publication_db") from exc

    def _create_stage(self, loc: Any, plan: _Plan) -> Any:
        fd: int | None = None
        exports_fd = self._exports_fd(loc)
        stage_name = _safe_ref(plan.stage_ref, build_id=plan.build_id, fmt=plan.fmt, stage=True)
        try:
            try:
                fd = QuillframeStore._create_unnamed_backup_fd(exports_fd)
            except BackupPublishError as exc:
                if getattr(exc, "code", "") == "backup_target_exists":
                    raise PublicationRecoveryError("publication_target_exists") from exc
                raise PublicationRecoveryError("publication_native_unavailable") from exc
            view = memoryview(plan.content)
            offset = 0
            while offset < len(view):
                written = os.write(fd, view[offset:])
                if written <= 0:
                    raise PublicationRecoveryError("publication_durability")
                offset += written
            os.fsync(fd)
            value = os.fstat(fd)
            if not stat.S_ISREG(value.st_mode) or value.st_size != plan.byte_size:
                raise PublicationRecoveryError("publication_stage_invalid")
            _fault_safe(self.fault_injector, "after_temp_fsync", plan.build_id)
            try:
                _linkat_empty_path(fd, exports_fd, stage_name)
            except BackupPublishError as exc:
                if getattr(exc, "code", "") == "backup_target_exists":
                    raise PublicationRecoveryError("publication_target_exists") from exc
                raise PublicationRecoveryError("publication_native_unavailable") from exc
            except Exception as exc:
                raise PublicationRecoveryError("publication_native_unavailable") from exc
            try:
                os.fsync(exports_fd)
            except OSError as exc:
                raise PublicationRecoveryError("publication_durability") from exc
            linked = os.fstat(fd)
            if linked.st_nlink != 1:
                raise PublicationRecoveryError("publication_stage_invalid")
            return linked
        except PublicationRecoveryError:
            raise
        except OSError as exc:
            raise PublicationRecoveryError("publication_durability") from exc
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            try:
                os.close(exports_fd)
            except OSError:
                pass

    def _stage_or_reuse(self, loc: Any, plan: _Plan, row: Any) -> Any:
        exports_fd = self._exports_fd(loc)
        stage_name = _safe_ref(row["stage_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=True)
        final_name = _safe_ref(row["final_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=False)
        try:
            stage = _safe_lstat(exports_fd, stage_name)
            final = _safe_lstat(exports_fd, final_name)
            if stage is not None and final is not None:
                raise PublicationRecoveryError("publication_target_exists")
            if final is not None:
                if row["stage_dev"] is None or row["stage_ino"] is None:
                    raise PublicationRecoveryError("publication_target_exists")
                _safe_file_bytes(
                    exports_fd,
                    final_name,
                    expected_fingerprint=plan.artifact_fingerprint,
                    expected_size=plan.byte_size,
                    expected_inode=(row["stage_dev"], row["stage_ino"]),
                    stage=False,
                    mutation_hook=self._file_hook("final", plan.build_id),
                )
                return self._record_published(plan, final)
            if stage is not None:
                if row["stage_dev"] is None or row["stage_ino"] is None:
                    raise PublicationRecoveryError("publication_stage_invalid")
                _safe_file_bytes(
                    exports_fd,
                    stage_name,
                    expected_fingerprint=plan.artifact_fingerprint,
                    expected_size=plan.byte_size,
                    expected_inode=(row["stage_dev"], row["stage_ino"]),
                    stage=True,
                    mutation_hook=self._file_hook("stage", plan.build_id),
                )
                return row
            value = self._create_stage(loc, plan)
        finally:
            try:
                os.close(exports_fd)
            except OSError:
                pass
        owned = self._record_stage_owner(plan, value)
        return owned

    def _publish(self, loc: Any, plan: _Plan, row: Any) -> Any:
        exports_fd = self._exports_fd(loc)
        stage_name = _safe_ref(row["stage_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=True)
        final_name = _safe_ref(row["final_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=False)
        try:
            if row["stage_dev"] is None or row["stage_ino"] is None:
                raise PublicationRecoveryError("publication_stage_invalid")
            _safe_file_bytes(
                exports_fd,
                stage_name,
                expected_fingerprint=plan.artifact_fingerprint,
                expected_size=plan.byte_size,
                expected_inode=(row["stage_dev"], row["stage_ino"]),
                stage=True,
                mutation_hook=self._file_hook("stage", plan.build_id),
            )
            if _safe_lstat(exports_fd, final_name) is not None:
                raise PublicationRecoveryError("publication_target_exists")
            try:
                _rename_noreplace(exports_fd, stage_name, exports_fd, final_name)
            except RestoreConflictError as exc:
                raise PublicationRecoveryError("publication_target_exists") from exc
            except RestoreIncompleteError as exc:
                raise PublicationRecoveryError("publication_native_unavailable") from exc
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    raise PublicationRecoveryError("publication_target_exists") from exc
                raise PublicationRecoveryError("publication_native_unavailable") from exc
            except Exception as exc:
                raise PublicationRecoveryError("publication_native_unavailable") from exc
            try:
                os.fsync(exports_fd)
            except OSError as exc:
                raise PublicationRecoveryError("publication_durability") from exc
            _fault_safe(self.fault_injector, "after_publish", plan.build_id)
            final = _safe_file_bytes(
                exports_fd,
                final_name,
                expected_fingerprint=plan.artifact_fingerprint,
                expected_size=plan.byte_size,
                expected_inode=(row["stage_dev"], row["stage_ino"]),
                stage=False,
                mutation_hook=self._file_hook("final", plan.build_id),
            )
            return self._record_published(plan, final)
        finally:
            try:
                os.close(exports_fd)
            except OSError:
                pass

    def _record_published(self, plan: _Plan, value: os.stat_result) -> Any:
        with self.store.open_project(plan.project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(f"SELECT * FROM {self.attempts_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                self._validate_row(row, plan)
                if row["state"] == "published":
                    conn.commit()
                    return row
                if row["state"] != "staged":
                    raise PublicationRecoveryError("publication_attempt_invalid")
                conn.execute(
                    f"UPDATE {self.attempts_table} SET state='published',final_dev=?,final_ino=?,updated_at=? WHERE build_id=?",
                    (value.st_dev, value.st_ino, now_iso(), plan.build_id),
                )
                conn.commit()
                return conn.execute(f"SELECT * FROM {self.attempts_table} WHERE build_id=?", (plan.build_id,)).fetchone()
            except PublicationRecoveryError:
                if conn.in_transaction:
                    conn.rollback()
                raise
            except Exception as exc:
                if conn.in_transaction:
                    conn.rollback()
                raise PublicationRecoveryError("publication_db") from exc

    def _finalize(self, loc: Any, plan: _Plan, row: Any) -> dict[str, Any]:
        exports_fd = self._exports_fd(loc)
        final_name = _safe_ref(row["final_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=False)
        expected_inode = None
        if row["final_dev"] is not None and row["final_ino"] is not None:
            expected_inode = (row["final_dev"], row["final_ino"])
        elif row["stage_dev"] is not None and row["stage_ino"] is not None:
            expected_inode = (row["stage_dev"], row["stage_ino"])
        try:
            final = _safe_file_bytes(
                exports_fd,
                final_name,
                expected_fingerprint=plan.artifact_fingerprint,
                expected_size=plan.byte_size,
                expected_inode=expected_inode,
                stage=False,
                mutation_hook=self._file_hook("final", plan.build_id),
            )
        finally:
            try:
                os.close(exports_fd)
            except OSError:
                pass
        with self.store.open_project(plan.project_id) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                source = self._source(conn, plan.project_id, plan.source_key)
                current = self._plan(source, plan.fmt)
                if current.identity_fingerprint != plan.identity_fingerprint:
                    raise PublicationRecoveryError("publication_source_changed")
                current_row = conn.execute(f"SELECT * FROM {self.attempts_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                self._validate_row(current_row, plan)
                if current_row["state"] == "committed":
                    committed = conn.execute(f"SELECT * FROM {self.builds_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                    self._validate_committed_row(committed, plan)
                    conn.commit()
                    return self._result(plan, committed)
                if current_row["state"] not in {"published", "staged"}:
                    raise PublicationRecoveryError("publication_attempt_invalid")
                committed = conn.execute(
                    f"SELECT * FROM {self.builds_table} WHERE {self.source_column}=? AND format=? AND source_fingerprint=? AND compiler_contract=?",
                    (plan.source_key, plan.fmt, plan.source_fingerprint, plan.compiler_contract),
                ).fetchone()
                if committed:
                    self._validate_committed_row(committed, plan)
                    conn.execute(
                        f"UPDATE {self.attempts_table} SET state='committed',final_dev=?,final_ino=?,updated_at=? WHERE build_id=?",
                        (final.st_dev, final.st_ino, now_iso(), plan.build_id),
                    )
                    conn.commit()
                    return self._result(plan, committed)
                _fault_safe(self.fault_injector, "before_finalize_insert", plan.build_id)
                validation = {
                    "source_intact": True,
                    "compiler_contract": self.compiler_contract,
                    "identity_fingerprint": plan.identity_fingerprint,
                    "artifact_fingerprint": plan.artifact_fingerprint,
                    "byte_size": plan.byte_size,
                    "stage_ref": plan.stage_ref,
                    "final_ref": plan.final_ref,
                    "authority": False,
                }
                try:
                    conn.execute(
                        f"""INSERT INTO {self.builds_table}(
                        build_id,{self.source_column},format,compiler_contract,output_ref,source_fingerprint,validation_json,persistent,created_at)
                        VALUES(?,?,?,?,?,?,?,1,?)""",
                        (
                            plan.build_id,
                            plan.source_key,
                            plan.fmt,
                            plan.compiler_contract,
                            plan.final_ref,
                            plan.source_fingerprint,
                            canonical_json(validation),
                            now_iso(),
                        ),
                    )
                except Exception as exc:
                    raise PublicationRecoveryError("publication_identity_conflict") from exc
                conn.execute(
                    f"UPDATE {self.attempts_table} SET state='committed',final_dev=?,final_ino=?,error_code=NULL,updated_at=? WHERE build_id=?",
                    (final.st_dev, final.st_ino, now_iso(), plan.build_id),
                )
                _fault_safe(self.fault_injector, "before_finalize_commit", plan.build_id)
                conn.commit()
                committed = conn.execute(f"SELECT * FROM {self.builds_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                return self._result(plan, committed)
            except PublicationRecoveryError:
                if conn.in_transaction:
                    conn.rollback()
                raise
            except Exception as exc:
                if conn.in_transaction:
                    conn.rollback()
                raise PublicationRecoveryError("publication_db") from exc

    def _result(self, plan: _Plan, row: Any) -> dict[str, Any]:
        return {
            "schema": "quillframe_publication_build_v1",
            "build_id": plan.build_id,
            "persistent": True,
            self.source_column: plan.source_key,
            "source_fingerprint": plan.source_fingerprint,
            "output_ref": plan.final_ref,
            "format": plan.fmt,
            "compiler_contract": self.compiler_contract,
            "identity_fingerprint": plan.identity_fingerprint,
            "artifact_fingerprint": plan.artifact_fingerprint,
            "byte_size": plan.byte_size,
        }

    def build(self, project_id: str, acceptance_id: str, fmt: str = "md") -> dict[str, Any]:
        if fmt not in SUPPORTED_FORMATS:
            raise PublicationRecoveryError("unsupported_export_format")
        with self._project_lock(project_id) as loc:
            plan, row, _created = self._stage_transaction(project_id, acceptance_id, fmt)
            if row["state"] == "committed":
                try:
                    exports_fd = self._exports_fd(loc)
                    final_name = _safe_ref(row["final_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=False)
                    expected_inode = (row["final_dev"], row["final_ino"]) if row["final_dev"] is not None and row["final_ino"] is not None else None
                    _safe_file_bytes(
                        exports_fd,
                        final_name,
                        expected_fingerprint=plan.artifact_fingerprint,
                        expected_size=plan.byte_size,
                        expected_inode=expected_inode,
                        stage=False,
                        mutation_hook=self._file_hook("final", plan.build_id),
                    )
                    with self.store.open_project(project_id) as conn:
                        committed = conn.execute(f"SELECT * FROM {self.builds_table} WHERE build_id=?", (plan.build_id,)).fetchone()
                    self._validate_committed_row(committed, plan)
                    return self._result(plan, committed)
                finally:
                    try:
                        os.close(exports_fd)
                    except (UnboundLocalError, OSError):
                        pass
            _fault_safe(self.fault_injector, "after_stage_commit", plan.build_id)
            row = self._stage_or_reuse(loc, plan, row)
            if row["state"] == "staged":
                row = self._publish(loc, plan, row)
            return self._finalize(loc, plan, row)

    def _mark_failed(self, project_id: str, build_id: str, code: str) -> None:
        try:
            with self.store.open_project(project_id) as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    f"UPDATE {self.attempts_table} SET state='failed',error_code=?,updated_at=? WHERE build_id=? AND state<>'committed'",
                    (code, now_iso(), build_id),
                )
                conn.commit()
        except Exception:
            # Evidence remains on disk and in the ledger even when this
            # best-effort diagnostic update cannot be committed.
            return

    def _recover_one(self, loc: Any, row: Any) -> dict[str, Any]:
        project_id = row["project_id"]
        with self.store.open_project(project_id) as conn:
            source = self._source(conn, project_id, row[self.source_column])
        if source.source_fingerprint != row["source_fingerprint"]:
            raise PublicationRecoveryError("publication_source_changed")
        plan = self._plan(source, row["format"])
        self._validate_row(row, plan)
        exports_fd = self._exports_fd(loc)
        stage_name = _safe_ref(row["stage_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=True)
        final_name = _safe_ref(row["final_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=False)
        try:
            stage = _safe_lstat(exports_fd, stage_name)
            final = _safe_lstat(exports_fd, final_name)
            if stage is not None and final is not None:
                raise PublicationRecoveryError("publication_ambiguous")
            if row["state"] == "staged":
                if final is not None:
                    if row["stage_dev"] is None or row["stage_ino"] is None:
                        raise PublicationRecoveryError("publication_target_exists")
                    _safe_file_bytes(
                        exports_fd,
                        final_name,
                        expected_fingerprint=plan.artifact_fingerprint,
                        expected_size=plan.byte_size,
                        expected_inode=(row["stage_dev"], row["stage_ino"]),
                        stage=False,
                        mutation_hook=self._file_hook("final", plan.build_id),
                    )
                    row = self._record_published(plan, final)
                elif stage is not None:
                    if row["stage_dev"] is None or row["stage_ino"] is None:
                        raise PublicationRecoveryError("publication_stage_invalid")
                    _safe_file_bytes(
                        exports_fd,
                        stage_name,
                        expected_fingerprint=plan.artifact_fingerprint,
                        expected_size=plan.byte_size,
                        expected_inode=(row["stage_dev"], row["stage_ino"]),
                        stage=True,
                        mutation_hook=self._file_hook("stage", plan.build_id),
                    )
                    try:
                        _rename_noreplace(exports_fd, stage_name, exports_fd, final_name)
                    except RestoreConflictError as exc:
                        raise PublicationRecoveryError("publication_target_exists") from exc
                    except RestoreIncompleteError as exc:
                        raise PublicationRecoveryError("publication_native_unavailable") from exc
                    except OSError as exc:
                        if exc.errno == errno.EEXIST:
                            raise PublicationRecoveryError("publication_target_exists") from exc
                        raise PublicationRecoveryError("publication_native_unavailable") from exc
                    except Exception as exc:
                        raise PublicationRecoveryError("publication_native_unavailable") from exc
                    try:
                        os.fsync(exports_fd)
                    except OSError as exc:
                        raise PublicationRecoveryError("publication_durability") from exc
                    final = _safe_lstat(exports_fd, final_name)
                    if final is None:
                        raise PublicationRecoveryError("publication_artifact_invalid")
                    row = self._record_published(plan, final)
                else:
                    raise PublicationRecoveryError("publication_missing")
            elif row["state"] == "published":
                if stage is not None or final is None:
                    raise PublicationRecoveryError("publication_missing" if final is None else "publication_ambiguous")
                expected_inode = (row["final_dev"], row["final_ino"]) if row["final_dev"] is not None and row["final_ino"] is not None else (row["stage_dev"], row["stage_ino"])
                _safe_file_bytes(
                    exports_fd,
                    final_name,
                    expected_fingerprint=plan.artifact_fingerprint,
                    expected_size=plan.byte_size,
                    expected_inode=expected_inode,
                    stage=False,
                    mutation_hook=self._file_hook("final", plan.build_id),
                )
            else:
                raise PublicationRecoveryError("publication_attempt_failed")
        finally:
            try:
                os.close(exports_fd)
            except OSError:
                pass
        return self._finalize(loc, plan, row)

    def retry(self, project_id: str, build_id: str) -> dict[str, Any]:
        """Explicitly reopen one failed attempt; ordinary build never does this."""

        if not isinstance(build_id, str) or not _BUILD_ID_RE.fullmatch(build_id):
            raise PublicationRecoveryError("publication_attempt_invalid")
        if self.__class__ is PublicationRecovery:
            with self.store.open_project(project_id) as conn:
                collection = conn.execute("SELECT 1 FROM publication_collection_attempts WHERE build_id=?", (build_id,)).fetchone()
            if collection:
                from .collection import CollectionPublicationRecovery
                return CollectionPublicationRecovery(self.store, fault_injector=self.fault_injector).retry(project_id, build_id)
        with self._project_lock(project_id):
            with self.store.open_project(project_id) as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    row = conn.execute(
                        f"SELECT * FROM {self.attempts_table} WHERE project_id=? AND build_id=?",
                        (project_id, build_id),
                    ).fetchone()
                    if not row:
                        raise PublicationRecoveryError("publication_missing")
                    if row["state"] != "failed":
                        raise PublicationRecoveryError("publication_attempt_invalid")
                    source = self._source(conn, project_id, row[self.source_column])
                    if source.source_fingerprint != row["source_fingerprint"]:
                        raise PublicationRecoveryError("publication_source_changed")
                    plan = self._plan(source, row["format"])
                    self._validate_row(row, plan)
                    conn.execute(
                        f"UPDATE {self.attempts_table} SET state='staged',error_code=NULL,stage_dev=NULL,stage_ino=NULL,final_dev=NULL,final_ino=NULL,updated_at=? WHERE build_id=?",
                        (now_iso(), build_id),
                    )
                    conn.commit()
                except PublicationRecoveryError:
                    if conn.in_transaction:
                        conn.rollback()
                    raise
                except Exception as exc:
                    if conn.in_transaction:
                        conn.rollback()
                    raise PublicationRecoveryError("publication_db") from exc
        return self.build(project_id, plan.source_key, plan.fmt)

    def recover(self, project_id: str, *, build_id: str | None = None, limit: int = MAX_RECOVERY_ATTEMPTS) -> dict[str, Any]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > MAX_RECOVERY_ATTEMPTS:
            raise PublicationRecoveryError("publication_recovery_bounded")
        if build_id is not None and (not isinstance(build_id, str) or not _BUILD_ID_RE.fullmatch(build_id)):
            raise PublicationRecoveryError("publication_attempt_invalid")
        if self.__class__ is not PublicationRecovery:
            return self._recover_ledger(project_id, build_id=build_id, limit=limit)
        from .collection import CollectionPublicationRecovery
        collection_runtime = CollectionPublicationRecovery(self.store, fault_injector=self.fault_injector)
        with self.store.open_project(project_id) as conn:
            if build_id is not None:
                collection = conn.execute("SELECT 1 FROM publication_collection_attempts WHERE build_id=?", (build_id,)).fetchone()
                if collection:
                    return collection_runtime._recover_ledger(project_id, build_id=build_id, limit=limit)
            else:
                single_count = conn.execute("SELECT COUNT(*) FROM publication_build_attempts WHERE state IN ('staged','published')").fetchone()[0]
                collection_count = conn.execute("SELECT COUNT(*) FROM publication_collection_attempts WHERE state IN ('staged','published')").fetchone()[0]
                if single_count + collection_count > limit:
                    raise PublicationRecoveryError("publication_recovery_bounded")
        result = self._recover_ledger(project_id, build_id=build_id, limit=limit)
        if build_id is None and collection_count:
            remaining = limit - len(result["items"])
            if remaining < 1:
                raise PublicationRecoveryError("publication_recovery_bounded")
            collected = collection_runtime._recover_ledger(project_id, limit=remaining)
            result["items"].extend(collected["items"])
        return result

    def _recover_ledger(self, project_id: str, *, build_id: str | None = None, limit: int = MAX_RECOVERY_ATTEMPTS) -> dict[str, Any]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > MAX_RECOVERY_ATTEMPTS:
            raise PublicationRecoveryError("publication_recovery_bounded")
        if build_id is not None and not _BUILD_ID_RE.fullmatch(build_id):
            raise PublicationRecoveryError("publication_attempt_invalid")
        with self._project_lock(project_id) as loc:
            with self.store.open_project(project_id) as conn:
                if build_id is None:
                    rows = conn.execute(
                        f"SELECT * FROM {self.attempts_table} WHERE project_id=? AND state IN ('staged','published') ORDER BY created_at,build_id LIMIT ?",
                        (project_id, limit + 1),
                    ).fetchall()
                else:
                    all_rows = conn.execute(
                        f"SELECT * FROM {self.attempts_table} WHERE project_id=? AND build_id=?",
                        (project_id, build_id),
                    ).fetchall()
                    if not all_rows:
                        raise PublicationRecoveryError("publication_missing")
                    if all_rows[0]["state"] == "failed":
                        raise PublicationRecoveryError("publication_attempt_failed")
                    if all_rows[0]["state"] == "committed":
                        row = all_rows[0]
                        with self.store.open_project(project_id) as verify_conn:
                            source = self._source(verify_conn, project_id, row[self.source_column])
                            if source.source_fingerprint != row["source_fingerprint"]:
                                raise PublicationRecoveryError("publication_source_changed")
                            plan = self._plan(source, row["format"])
                            self._validate_row(row, plan)
                            committed = verify_conn.execute(f"SELECT * FROM {self.builds_table} WHERE build_id=?", (build_id,)).fetchone()
                        self._validate_committed_row(committed, plan)
                        exports_fd = self._exports_fd(loc)
                        try:
                            final_name = _safe_ref(row["final_ref"], build_id=plan.build_id, fmt=plan.fmt, stage=False)
                            expected_inode = (row["final_dev"], row["final_ino"]) if row["final_dev"] is not None and row["final_ino"] is not None else None
                            _safe_file_bytes(
                                exports_fd,
                                final_name,
                                expected_fingerprint=plan.artifact_fingerprint,
                                expected_size=plan.byte_size,
                                expected_inode=expected_inode,
                                stage=False,
                                mutation_hook=self._file_hook("final", plan.build_id),
                            )
                        finally:
                            try:
                                os.close(exports_fd)
                            except OSError:
                                pass
                        return {
                            "schema": "quillframe_publication_recovery_result_v1",
                            "project_id": project_id,
                            "items": [self._result(plan, committed)],
                            "limit": limit,
                            "authority": False,
                            "replayed": True,
                        }
                    rows = all_rows if all_rows[0]["state"] in {"staged", "published"} else []
            if len(rows) > limit:
                raise PublicationRecoveryError("publication_recovery_bounded")
            items = []
            for row in rows:
                try:
                    items.append(self._recover_one(loc, row))
                except PublicationRecoveryError as exc:
                    self._mark_failed(project_id, row["build_id"], exc.code)
                    raise
        return {
            "schema": "quillframe_publication_recovery_result_v1",
            "project_id": project_id,
            "items": items,
            "limit": limit,
            "authority": False,
        }
