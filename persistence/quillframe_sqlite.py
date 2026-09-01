#!/usr/bin/env python3
"""Canonical SQLite persistence for Quillframe 1.0.

The database owns durable product state. Persistence never grants Canon,
acceptance, settlement, learning-promotion, or framework-write authority by
itself; those transitions remain operation-specific Core decisions.
"""
from __future__ import annotations

import hashlib
import ctypes
import errno
import json
import os
import re
import sqlite3
import stat
import sys
import tempfile
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

try:  # POSIX-only; native restore already fails closed on unsupported hosts.
    import fcntl
except ImportError:  # pragma: no cover - exercised by the Windows import test
    fcntl = None  # type: ignore[assignment]

from project_resolution import validate_project_id

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FRAGMENTS_ROOT = Path(__file__).resolve().parent / "schema"
SCHEMA_VERSION = 1
SCHEMA_RELEASE = "1.0"
BUNDLE_SCHEMA = "quillframe_backup_bundle_v1"
PROJECT_SCHEMA = "quillframe_project_v1_0"
PROJECT_SCOPE = "novel"
INITIAL_CHAPTER_ID = "CH001"
BUNDLE_MANIFEST_KEYS = {
    "schema",
    "project_schema",
    "scope",
    "backup_id",
    "project_id",
    "created_at",
    "database_fingerprint",
    "blobs",
}
BUNDLE_BLOB_KEYS = {"fingerprint", "relative_path", "byte_size"}
BUNDLE_FINGERPRINT_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
BUNDLE_BACKUP_ID_RE = re.compile(r"backup_[0-9a-f]{32}\Z")
BUNDLE_BLOB_PATH_RE = re.compile(r"blobs/[0-9a-f]{2}/[0-9a-f]{62}\Z")
MAX_BUNDLE_MEMBERS = 1024
MAX_BUNDLE_MANIFEST_BYTES = 1024 * 1024
MAX_BUNDLE_DATABASE_BYTES = 128 * 1024 * 1024
MAX_BUNDLE_BLOB_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_MEMBER_BYTES = max(MAX_BUNDLE_DATABASE_BYTES, MAX_BUNDLE_BLOB_BYTES)
MAX_BUNDLE_TOTAL_BYTES = MAX_BUNDLE_DATABASE_BYTES + MAX_BUNDLE_BLOB_BYTES * 16
MAX_BUNDLE_COMPRESSED_BYTES = MAX_BUNDLE_TOTAL_BYTES
LINUX_AT_EMPTY_PATH = 0x1000
LINUX_RENAME_NOREPLACE = 1
RESTORE_JOURNAL_SCHEMA = "quillframe_restore_journal_v1"
RESTORE_JOURNAL_RE = re.compile(r"\A\.(?P<project>[A-Za-z0-9][A-Za-z0-9._-]{0,63})\.restore-(?P<nonce>[0-9a-f]{32})-(?P<sequence>[0-9]{4})\.journal\Z")
RESTORE_PHASES = ("STAGING", "PREPARED", "NEW_SWAPPED", "REGISTRY_UPSERTED", "COMMITTED", "ABORTED")
RESTORE_TERMINAL_PHASES = {"COMMITTED", "ABORTED"}
# The active cap is intentionally separate from retained terminal audit
# evidence. Terminal files still have bounded parsing limits below, but they
# cannot consume the cap that protects live recovery work.
MAX_RESTORE_JOURNAL_RECORDS = 256
MAX_RESTORE_ACTIVE_OPERATIONS = 256
MAX_RESTORE_TERMINAL_RECORDS = 4096
MAX_RESTORE_JOURNAL_BYTES = 64 * 1024 * 1024
# Bound the complete restore-root enumeration, including unrelated entries;
# this is separate from the journal payload and active-operation limits.
MAX_RESTORE_DIRECTORY_ENTRIES = 4096
MAX_INTERNAL_REGISTRY_PAGE_SIZE = 500
MAX_INTERNAL_REGISTRY_PROJECTS = 10_000
RESTORE_RETENTION = {
    "policy": "append_only_audit",
    "authority": False,
    "contains_secret": False,
    "contains_absolute_path": False,
}
SCHEMA_LEDGER_DDL = """CREATE TABLE schema_fragments (
    scope TEXT NOT NULL,
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    PRIMARY KEY(scope, version)
)"""


class ProjectStateError(RuntimeError):
    """Existing Project state cannot be safely opened under the current contract."""


class SchemaContractError(ProjectStateError):
    """An existing SQLite schema is not exactly the current native contract."""


class SchemaChecksumError(SchemaContractError):
    pass


class Pre10StateRejectedError(SchemaContractError):
    pass


class ProjectRegistryUnavailableError(ProjectStateError):
    """Canonical global Project registry cannot be read safely."""


class ProjectLookupLimitError(ProjectStateError):
    """Canonical Project registry traversal exceeded its bounded limit."""


class ConflictError(RuntimeError):
    pass


class IntegrityError(RuntimeError):
    pass


class ProjectIdentityMismatchError(ProjectStateError):
    """Existing Project identity differs from the manifest-bound identity."""


class BundleValidationError(IntegrityError):
    """A backup bundle is not trusted under the native 1.0 contract."""

    code = "bundle_invalid"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class BundleFormatError(BundleValidationError):
    code = "bundle_format"


class BundlePathError(BundleValidationError):
    code = "bundle_path"


class BundleSchemaError(BundleValidationError):
    code = "bundle_schema"


class BundleLimitError(BundleValidationError):
    code = "bundle_limit"


class BundleDatabaseError(BundleValidationError):
    code = "bundle_database"


class BundleIdentityError(BundleValidationError):
    code = "bundle_identity"


class BundleBlobError(BundleValidationError):
    code = "bundle_blob"


class BackupPublishError(IntegrityError):
    """A native backup could not be published without losing ownership."""

    code = "backup_publish"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class BackupRestoreError(IntegrityError):
    """A restore was rejected at the native backup trust boundary."""

    code = "backup_invalid"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class RestoreError(BackupRestoreError):
    """A native restore failed after bundle validation."""

    code = "restore_failed"


class RestorePathError(RestoreError):
    code = "restore_path"


class RestoreConflictError(RestoreError):
    code = "restore_target_exists"


class RestoreReplacementUnavailable(RestoreError):
    """C3B1 deliberately does not replace an existing Project tree."""

    code = "restore_replacement_unavailable"


class RestoreIncompleteError(RestoreError):
    """Restore ownership or durable recovery could not be proven."""

    code = "restore_incomplete"


_BUNDLE_PUBLIC_ERROR_MESSAGES = {
    "bundle_format": "backup bundle format is invalid",
    "bundle_members": "backup bundle members are invalid",
    "bundle_path": "backup bundle path is not allowed",
    "bundle_schema": "backup bundle schema is invalid",
    "bundle_limit": "backup bundle exceeds native limits",
    "bundle_database": "backup project database is invalid",
    "bundle_identity": "backup project identity is invalid",
    "bundle_blob": "backup blob content is invalid",
    "bundle_target_path": "backup destination path is not allowed",
}

_RESTORE_PUBLIC_ERROR_MESSAGES = {
    "restore_failed": "native restore failed",
    "restore_path": "restore destination path is not allowed",
    "restore_target_exists": "restore target already exists",
    "restore_replacement_unavailable": "native Project replacement is not available in C3B1",
    "restore_native_unavailable": "native restore publication is unavailable",
    "restore_incomplete": "native restore requires recovery",
    "restore_bundle": "backup bundle could not be restored",
}


def _public_bundle_error_message(code: str) -> str:
    return _BUNDLE_PUBLIC_ERROR_MESSAGES.get(code, "backup bundle validation failed")


def _public_restore_error_message(code: str) -> str:
    return _RESTORE_PUBLIC_ERROR_MESSAGES.get(code, "native restore failed")


def _linkat_empty_path(source_fd: int, parent_fd: int, target_name: str) -> None:
    """Publish an unnamed inode with Linux linkat(AT_EMPTY_PATH), fail closed."""

    if sys.platform != "linux":
        raise BackupPublishError(
            "native unnamed backup publication is unavailable",
            code="backup_native_unavailable",
        )
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        linkat = libc.linkat
    except (AttributeError, OSError) as exc:
        raise BackupPublishError(
            "native unnamed backup publication is unavailable",
            code="backup_native_unavailable",
        ) from exc
    linkat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    linkat.restype = ctypes.c_int
    result = linkat(
        source_fd,
        ctypes.c_char_p(b""),
        parent_fd,
        ctypes.c_char_p(os.fsencode(target_name)),
        LINUX_AT_EMPTY_PATH,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise BackupPublishError("backup target already exists", code="backup_target_exists")
    if error_number in {
        errno.EINVAL,
        errno.ENOSYS,
        errno.EOPNOTSUPP,
        getattr(errno, "ENOTSUP", errno.EOPNOTSUPP),
    }:
        raise BackupPublishError(
            "native unnamed backup publication is unavailable",
            code="backup_native_unavailable",
        )
    raise BackupPublishError("backup target could not be published", code="backup_publish")


def _rename_noreplace(
    source_directory_fd: int,
    source_name: str,
    target_directory_fd: int,
    target_name: str,
) -> None:
    """Atomically rename without replacing an inode; fail closed if unavailable."""

    if sys.platform != "linux":
        raise RestoreIncompleteError(
            _public_restore_error_message("restore_native_unavailable"),
            code="restore_native_unavailable",
        )
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError) as exc:
        raise RestoreIncompleteError(
            _public_restore_error_message("restore_native_unavailable"),
            code="restore_native_unavailable",
        ) from exc
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        source_directory_fd,
        ctypes.c_char_p(os.fsencode(source_name)),
        target_directory_fd,
        ctypes.c_char_p(os.fsencode(target_name)),
        LINUX_RENAME_NOREPLACE,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise RestoreConflictError(
            _public_restore_error_message("restore_target_exists"),
            code="restore_target_exists",
        )
    if error_number in {
        errno.EINVAL,
        errno.ENOSYS,
        errno.EOPNOTSUPP,
        getattr(errno, "ENOTSUP", errno.EOPNOTSUPP),
        getattr(errno, "EXDEV", errno.EINVAL),
    }:
        raise RestoreIncompleteError(
            _public_restore_error_message("restore_native_unavailable"),
            code="restore_native_unavailable",
        )
    raise RestoreIncompleteError(
        _public_restore_error_message("restore_failed"),
        code="restore_publish",
    )


@dataclass(frozen=True)
class _ValidatedProjectDatabase:
    identity: dict[str, Any]
    blobs: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class _ValidatedBundle:
    manifest: dict[str, Any]
    database: bytes
    blobs: tuple[tuple[str, bytes], ...]
    identity: dict[str, Any]


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
    project_id = validate_project_id(project_id)
    return (root or data_root()) / "projects" / project_id


def _connect(path: Path, *, configure_journal: bool = True) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(path, timeout=5.0, factory=_ClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        if configure_journal:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
        return conn
    except Exception:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        raise


def _connect_existing_fd(fd: int) -> sqlite3.Connection:
    """Bind SQLite to an already-open inode; fail closed without Linux procfs."""
    if sys.platform != "linux" or not Path("/proc/self/fd").is_dir():
        raise ProjectStateError("descriptor-bound existing Project SQLite requires Linux /proc/self/fd")
    try:
        os.fstat(fd)
    except OSError as exc:
        raise ProjectStateError("existing Project database guard is invalid") from exc
    uri = f"file:/proc/self/fd/{fd}?mode=rw"
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=5.0, factory=_ClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
    except Exception:
        if conn is not None:
            conn.close()
        raise


def _connect_readonly(path: Path) -> sqlite3.Connection:
    """Open an existing SQLite file without creating parents or write journals."""
    if not path.is_file():
        raise FileNotFoundError(f"database does not exist: {path}")
    wal = path.with_name(path.name + "-wal")
    shm = path.with_name(path.name + "-shm")
    if wal.exists() and not shm.exists():
        raise sqlite3.OperationalError("read-only SQLite WAL shared-memory sidecar is missing")
    # An active WAL must use the normal read-only VFS so SQLite can consume its
    # committed frames.  SQLite may update only ephemeral lock bytes in an
    # existing SHM sidecar while doing so.  Without a WAL, immutable mode
    # prevents SQLite from creating fresh journal/SHM sidecars for inspection.
    options = "mode=ro" if wal.exists() else "mode=ro&immutable=1"
    uri = f"file:{path.resolve().as_posix()}?{options}"
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=5.0, factory=_ClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
    except Exception:
        if conn is not None:
            conn.close()
        raise


def _reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BundleSchemaError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise BundleSchemaError(f"non-finite JSON number is not allowed: {value}")


def _validate_fingerprint(value: Any, field: str) -> str:
    if not isinstance(value, str) or not BUNDLE_FINGERPRINT_RE.fullmatch(value):
        raise BundleSchemaError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def _validate_blob_metadata(value: Any, *, index: int | None = None) -> dict[str, Any]:
    label = f"blob[{index}]" if index is not None else "blob"
    if not isinstance(value, dict) or set(value) != BUNDLE_BLOB_KEYS:
        raise BundleSchemaError(f"{label} must contain exactly fingerprint, relative_path, byte_size")
    fingerprint = _validate_fingerprint(value["fingerprint"], f"{label}.fingerprint")
    relative_path = value["relative_path"]
    if not isinstance(relative_path, str) or not BUNDLE_BLOB_PATH_RE.fullmatch(relative_path):
        raise BundlePathError(f"{label}.relative_path is not a canonical content-addressed blob path")
    digest = fingerprint.split(":", 1)[1]
    if "/".join(relative_path.split("/")[1:]) != f"{digest[:2]}/{digest[2:]}":
        raise BundleBlobError(f"{label} path does not match its fingerprint")
    byte_size = value["byte_size"]
    if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 0:
        raise BundleSchemaError(f"{label}.byte_size must be a non-negative integer")
    if byte_size > MAX_BUNDLE_BLOB_BYTES:
        raise BundleLimitError(f"{label}.byte_size exceeds the native bundle limit")
    return {"fingerprint": fingerprint, "relative_path": relative_path, "byte_size": byte_size}


def _parse_bundle_manifest(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_pairs,
            parse_constant=_reject_json_constant,
        )
    except BundleValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise BundleSchemaError(f"manifest.json is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict) or set(value) != BUNDLE_MANIFEST_KEYS:
        raise BundleSchemaError("manifest.json keys do not match the native bundle contract")
    if value["schema"] != BUNDLE_SCHEMA:
        raise BundleSchemaError(f"schema must be exactly {BUNDLE_SCHEMA}")
    if value["project_schema"] != PROJECT_SCHEMA:
        raise BundleSchemaError(f"project_schema must be exactly {PROJECT_SCHEMA}")
    if value["scope"] != PROJECT_SCOPE:
        raise BundleSchemaError(f"scope must be exactly {PROJECT_SCOPE}")
    backup_id = value["backup_id"]
    if not isinstance(backup_id, str) or not BUNDLE_BACKUP_ID_RE.fullmatch(backup_id):
        raise BundleSchemaError("backup_id must match backup_[0-9a-f]{32}")
    try:
        project_id = validate_project_id(value["project_id"])
    except (TypeError, ValueError) as exc:
        raise BundleIdentityError(f"project_id is not a valid native Project id: {exc}") from exc
    created_at = value["created_at"]
    if not isinstance(created_at, str):
        raise BundleSchemaError("created_at must be an ISO-8601 UTC string")
    try:
        parsed_created_at = datetime.fromisoformat(created_at)
    except ValueError as exc:
        raise BundleSchemaError("created_at must be an ISO-8601 UTC string") from exc
    if (
        parsed_created_at.tzinfo is None
        or parsed_created_at.utcoffset() != timedelta(0)
        or parsed_created_at.isoformat() != created_at
    ):
        raise BundleSchemaError("created_at must be canonical ISO-8601 UTC with +00:00 offset")
    database_fingerprint = _validate_fingerprint(value["database_fingerprint"], "database_fingerprint")
    blobs_value = value["blobs"]
    if not isinstance(blobs_value, list):
        raise BundleSchemaError("blobs must be an array")
    blobs = [_validate_blob_metadata(blob, index=index) for index, blob in enumerate(blobs_value)]
    paths = [blob["relative_path"] for blob in blobs]
    if len(paths) != len(set(paths)):
        raise BundleSchemaError("manifest blob paths must be unique")
    if paths != sorted(paths):
        raise BundleSchemaError("manifest blobs must be sorted by relative_path")
    return {
        "schema": BUNDLE_SCHEMA,
        "project_schema": PROJECT_SCHEMA,
        "scope": PROJECT_SCOPE,
        "backup_id": backup_id,
        "project_id": project_id,
        "created_at": created_at,
        "database_fingerprint": database_fingerprint,
        "blobs": blobs,
    }


def _validate_zip_member_name(name: Any) -> str:
    if not isinstance(name, str) or not name:
        raise BundlePathError("ZIP member name must be a non-empty string")
    if "\x00" in name or "\\" in name:
        raise BundlePathError(f"unsafe ZIP member path: {name!r}")
    if unicodedata.normalize("NFC", name) != name:
        raise BundlePathError(f"non-canonical ZIP member path: {name!r}")
    if name.startswith("/") or name.endswith("/"):
        raise BundlePathError(f"absolute or directory ZIP member path: {name!r}")
    parts = name.split("/")
    if any(not part or part in {".", ".."} for part in parts):
        raise BundlePathError(f"traversal or empty ZIP member path: {name!r}")
    if ":" in parts[0]:
        raise BundlePathError(f"drive-like ZIP member path: {name!r}")
    return name


def _inspect_zip_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    if not infos:
        raise BundleFormatError("backup ZIP is empty")
    if len(infos) > MAX_BUNDLE_MEMBERS:
        raise BundleLimitError("backup ZIP has too many members")
    members: dict[str, zipfile.ZipInfo] = {}
    total_size = 0
    for info in infos:
        name = _validate_zip_member_name(info.filename)
        if name in members:
            raise BundleFormatError(f"duplicate ZIP member: {name}", code="bundle_members")
        if info.is_dir():
            raise BundlePathError(f"directory ZIP member is not allowed: {name}")
        mode = (info.external_attr >> 16) & 0xFFFF
        file_type = stat.S_IFMT(mode)
        if file_type not in {0, stat.S_IFREG}:
            raise BundlePathError(f"non-regular ZIP member is not allowed: {name}")
        if info.file_size < 0 or info.compress_size < 0:
            raise BundleFormatError(f"negative ZIP member size: {name}")
        if info.file_size > MAX_BUNDLE_MEMBER_BYTES:
            raise BundleLimitError(f"ZIP member exceeds size limit: {name}")
        if info.compress_size > MAX_BUNDLE_COMPRESSED_BYTES:
            raise BundleLimitError(f"compressed ZIP member exceeds size limit: {name}")
        total_size += info.file_size
        if total_size > MAX_BUNDLE_TOTAL_BYTES:
            raise BundleLimitError("backup ZIP uncompressed size exceeds the native limit")
        members[name] = info
    names = set(members)
    for name in names:
        parts = name.split("/")
        for index in range(1, len(parts)):
            prefix = "/".join(parts[:index])
            if prefix in names:
                raise BundlePathError(f"ZIP file/directory path collision: {prefix}")
    return members


def _read_zip_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    limit: int,
    label: str,
) -> bytes:
    if info.file_size > limit:
        raise BundleLimitError(f"{label} exceeds its native size limit")
    try:
        with archive.open(info, "r") as handle:
            payload = handle.read(limit + 1)
    except (KeyError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise BundleFormatError(f"unable to read ZIP member {label}: {exc}") from exc
    if len(payload) != info.file_size:
        raise BundleFormatError(f"ZIP member size mismatch: {label}")
    return payload


def _stat_signature(value: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    """Return the complete metadata identity used across one read window.

    Device/inode/mode/size alone cannot detect an in-place overwrite that
    preserves the length.  Link count and nanosecond timestamps close that
    same-inode/same-size window; the readers below also perform a second byte
    pass so an overwrite that races a stat call cannot be accepted merely
    because a stale stat result was returned.
    """
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _validate_stat_continuity(
    before: os.stat_result,
    after: os.stat_result,
    *,
    label: str,
    require_single_link: bool,
) -> None:
    if _stat_signature(before) != _stat_signature(after):
        raise BundlePathError(f"{label} changed while it was read")
    if require_single_link and after.st_nlink != 1:
        raise BundlePathError(f"{label} must have exactly one hard link")


def _read_regular_nofollow(
    path: Path,
    *,
    limit: int,
    label: str,
    require_single_link: bool = False,
) -> bytes:
    try:
        initial = os.lstat(path)
    except OSError as exc:
        raise BundlePathError(f"unable to stat {label}: {exc}") from exc
    if stat.S_ISLNK(initial.st_mode) or not stat.S_ISREG(initial.st_mode):
        raise BundlePathError(f"{label} must be a regular non-symlink file")
    if require_single_link and initial.st_nlink != 1:
        raise BundlePathError(f"{label} must have exactly one hard link")
    if initial.st_size > limit:
        raise BundleLimitError(f"{label} exceeds its native size limit")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow:
        raise BundlePathError("native no-follow file reads are unavailable")
    fd: int | None = None
    try:
        fd = os.open(path, os.O_RDONLY | nofollow)
        opened = os.fstat(fd)
        if stat.S_ISLNK(opened.st_mode) or not stat.S_ISREG(opened.st_mode):
            raise BundlePathError(f"{label} changed to a non-regular file")
        _validate_stat_continuity(
            initial,
            opened,
            label=label,
            require_single_link=require_single_link,
        )
        if opened.st_size > limit:
            raise BundleLimitError(f"{label} exceeds its native size limit")
        with os.fdopen(fd, "rb") as handle:
            fd = None
            payload = handle.read(limit + 1)
            after_read = os.fstat(handle.fileno())
            _validate_stat_continuity(
                opened,
                after_read,
                label=label,
                require_single_link=require_single_link,
            )
            # A stat after the first read can itself race an in-place write.
            # Re-read from the same no-follow descriptor and require both
            # bytes and the complete descriptor signature to agree before
            # returning any data to the caller.
            handle.seek(0)
            confirmation = handle.read(limit + 1)
            latest = os.fstat(handle.fileno())
            _validate_stat_continuity(
                after_read,
                latest,
                label=label,
                require_single_link=require_single_link,
            )
        if len(payload) != initial.st_size or len(confirmation) != latest.st_size:
            raise BundlePathError(f"{label} changed while it was read")
        if payload != confirmation:
            raise BundlePathError(f"{label} bytes changed while it was read")
        return confirmation
    except BundleValidationError:
        raise
    except OSError as exc:
        raise BundlePathError(f"unable to read {label}: {exc}") from exc
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _absolute_lexical_path(path: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    # abspath performs only lexical normalization; it does not follow links.
    return Path(os.path.abspath(os.fspath(candidate)))


def _open_real_directory_chain(path: Path) -> tuple[Path, int]:
    """Create/open every directory component with no symlink traversal."""

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory:
        raise BundlePathError("native no-follow directory access is unavailable", code="bundle_target_path")
    absolute = _absolute_lexical_path(path)
    flags = os.O_RDONLY | nofollow | directory
    current_fd: int | None = None
    try:
        current_fd = os.open(absolute.anchor or os.sep, flags)
        for part in absolute.parts[1:]:
            if part in {"", ".", ".."}:
                raise BundlePathError("backup destination path is not canonical", code="bundle_target_path")
            try:
                child_fd = os.open(part, flags, dir_fd=current_fd)
            except FileNotFoundError:
                try:
                    os.mkdir(part, 0o700, dir_fd=current_fd)
                except FileExistsError:
                    pass
                child_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = child_fd
        result_fd = current_fd
        current_fd = None
        return absolute, result_fd
    except BundleValidationError:
        raise
    except OSError as exc:
        raise BundlePathError("backup destination path is not a real directory", code="bundle_target_path") from exc
    finally:
        if current_fd is not None:
            try:
                os.close(current_fd)
            except OSError:
                pass


def _read_blob_entry_at(directory_fd: int, name: str, expected_fingerprint: str) -> os.stat_result:
    """Read and verify one content-addressed blob without following links."""

    if not re.fullmatch(r"[0-9a-f]{62}\Z", name):
        raise IntegrityError("blob path is invalid")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow:
        raise IntegrityError("native no-follow blob access is unavailable")
    try:
        initial = os.lstat(name, dir_fd=directory_fd)
    except OSError as exc:
        raise IntegrityError("blob path could not be inspected") from exc
    if stat.S_ISLNK(initial.st_mode) or not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
        raise IntegrityError("blob path must be one owned regular file")
    if initial.st_size > MAX_BUNDLE_BLOB_BYTES:
        raise IntegrityError("blob exceeds the native size limit")

    fd: int | None = None
    try:
        fd = os.open(
            name,
            os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_fd,
        )
        opened = os.fstat(fd)
        if stat.S_ISLNK(opened.st_mode) or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise IntegrityError("blob path changed to an unowned file")
        if _stat_signature(initial) != _stat_signature(opened):
            raise IntegrityError("blob path changed while it was opened")
        with os.fdopen(fd, "rb") as handle:
            fd = None
            payload = handle.read(MAX_BUNDLE_BLOB_BYTES + 1)
            after_read = os.fstat(handle.fileno())
            if _stat_signature(opened) != _stat_signature(after_read) or after_read.st_nlink != 1:
                raise IntegrityError("blob changed while it was read")
            # Confirm bytes from the same descriptor after the first stat.
            # This catches same-inode/same-size overwrites even when the
            # intervening stat result was stale at the injection boundary.
            handle.seek(0)
            confirmation = handle.read(MAX_BUNDLE_BLOB_BYTES + 1)
            latest = os.fstat(handle.fileno())
        if _stat_signature(after_read) != _stat_signature(latest) or latest.st_nlink != 1:
            raise IntegrityError("blob changed while it was read")
        if payload != confirmation:
            raise IntegrityError("blob bytes changed while it was read")
        if len(confirmation) != latest.st_size or fingerprint_bytes(confirmation) != expected_fingerprint:
            raise IntegrityError("blob path exists with fingerprint mismatch")
        return latest
    except IntegrityError:
        raise
    except OSError as exc:
        raise IntegrityError("blob could not be read safely") from exc
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _assert_contained_regular_path(root: Path, relative_path: str, *, label: str) -> Path:
    try:
        root_stat = os.lstat(root)
    except OSError as exc:
        raise BundlePathError(f"unable to stat {label} root: {exc}") from exc
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        raise BundlePathError(f"{label} root must be a real directory")
    parts = relative_path.split("/")
    current = root
    for index, part in enumerate(parts):
        current = current / part
        try:
            current_stat = os.lstat(current)
        except OSError as exc:
            raise BundlePathError(f"unable to stat {label}: {exc}") from exc
        if stat.S_ISLNK(current_stat.st_mode):
            raise BundlePathError(f"{label} contains a symlink")
        if index < len(parts) - 1 and not stat.S_ISDIR(current_stat.st_mode):
            raise BundlePathError(f"{label} contains a non-directory parent")
    try:
        resolved_root = root.resolve(strict=True)
        resolved_current = current.resolve(strict=True)
        resolved_current.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise BundlePathError(f"{label} escapes its project directory") from exc
    if not stat.S_ISREG(os.lstat(current).st_mode):
        raise BundlePathError(f"{label} must be a regular file")
    return current


def _restore_fsync_directory(directory_fd: int) -> None:
    try:
        os.fsync(directory_fd)
    except OSError as exc:
        raise RestoreIncompleteError(
            _public_restore_error_message("restore_failed"),
            code="restore_durability",
        ) from exc


def _restore_open_or_create_directory(directory_fd: int, name: str, *, label: str) -> int:
    if not name or "/" in name or name in {".", ".."}:
        raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory:
        raise RestoreIncompleteError(
            _public_restore_error_message("restore_native_unavailable"),
            code="restore_native_unavailable",
        )
    try:
        before = os.lstat(name, dir_fd=directory_fd)
    except FileNotFoundError:
        try:
            os.mkdir(name, 0o700, dir_fd=directory_fd)
            _restore_fsync_directory(directory_fd)
        except FileExistsError:
            pass
        except OSError as exc:
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
        try:
            before = os.lstat(name, dir_fd=directory_fd)
        except OSError as exc:
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
    except OSError as exc:
        raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
    try:
        child_fd = os.open(
            name,
            os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_fd,
        )
        after = os.fstat(child_fd)
    except OSError as exc:
        raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
    if (before.st_dev, before.st_ino, before.st_mode) != (after.st_dev, after.st_ino, after.st_mode):
        os.close(child_fd)
        raise RestoreIncompleteError(
            _public_restore_error_message("restore_incomplete"),
            code="restore_incomplete",
        )
    return child_fd


def _restore_write_bytes_at(directory_fd: int, relative_path: str, payload: bytes) -> None:
    parts = relative_path.split("/")
    if not parts or any(not part or part in {".", ".."} for part in parts):
        raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
    current_fd = directory_fd
    opened: list[int] = []
    try:
        for part in parts[:-1]:
            child_fd = _restore_open_or_create_directory(current_fd, part, label=relative_path)
            opened.append(child_fd)
            current_fd = child_fd
        filename = parts[-1]
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if not nofollow:
            raise RestoreIncompleteError(
                _public_restore_error_message("restore_native_unavailable"),
                code="restore_native_unavailable",
            )
        try:
            fd = os.open(
                filename,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | nofollow
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=current_fd,
            )
        except FileExistsError as exc:
            raise RestoreConflictError(
                _public_restore_error_message("restore_target_exists"),
                code="restore_target_exists",
            ) from exc
        except OSError as exc:
            raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_write") from exc
        try:
            view = memoryview(payload)
            offset = 0
            while offset < len(view):
                offset += os.write(fd, view[offset:])
            os.fsync(fd)
        finally:
            os.close(fd)
        _restore_fsync_directory(current_fd)
    finally:
        for fd in reversed(opened):
            try:
                os.close(fd)
            except OSError:
                pass


def _restore_owned_inode(value: os.stat_result) -> tuple[int, int]:
    return (value.st_dev, value.st_ino)


def _restore_write_journal(directory_fd: int, name: str, record: dict[str, Any]) -> None:
    temporary_fd: int | None = None
    try:
        temporary_fd = QuillframeStore._create_unnamed_backup_fd(directory_fd)
        payload = (canonical_json(record) + "\n").encode("utf-8")
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            offset += os.write(temporary_fd, view[offset:])
        os.fsync(temporary_fd)
        try:
            _linkat_empty_path(temporary_fd, directory_fd, name)
        except BackupPublishError as exc:
            raise RestoreIncompleteError(
                _public_restore_error_message("restore_native_unavailable"),
                code="restore_native_unavailable",
            ) from exc
        _restore_fsync_directory(directory_fd)
    except RestoreError:
        raise
    except OSError as exc:
        raise RestoreIncompleteError(
            _public_restore_error_message("restore_durability"),
            code="restore_durability",
        ) from exc
    finally:
        if temporary_fd is not None:
            try:
                os.close(temporary_fd)
            except OSError:
                pass


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
        raise ValueError("incomplete SQL schema fragment")


@dataclass(frozen=True)
class _SchemaFragment:
    version: int
    name: str
    sql: str
    checksum: str


def _schema_fragments(scope: str) -> list[_SchemaFragment]:
    directory = SCHEMA_FRAGMENTS_ROOT / scope
    fragments: list[_SchemaFragment] = []
    seen_versions: set[int] = set()
    for path in sorted(directory.glob("*.sql")):
        prefix = path.name.split("_", 1)[0]
        if not prefix.isdigit():
            raise SchemaContractError(f"schema fragment filename must start with an integer: {path.name}")
        version = int(prefix)
        if version < 1 or version in seen_versions:
            raise SchemaContractError(f"schema fragment version is duplicated or invalid: {path.name}")
        seen_versions.add(version)
        sql = path.read_text(encoding="utf-8")
        fragments.append(_SchemaFragment(version, path.name, sql, fingerprint_text(sql)))
    if not fragments:
        raise SchemaContractError(f"no schema fragments found for scope: {scope}")
    expected_versions = list(range(1, len(fragments) + 1))
    actual_versions = [fragment.version for fragment in fragments]
    if actual_versions != expected_versions:
        raise SchemaContractError(
            f"schema fragment versions must be continuous from 1 for {scope}: "
            f"expected={expected_versions}, actual={actual_versions}"
        )
    return fragments


def _normalize_sql(sql: str | None) -> str:
    return " ".join((sql or "").split())


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _schema_object_map(conn: sqlite3.Connection) -> dict[str, tuple[str, str, str]]:
    return {
        str(row[1]): (str(row[0]), str(row[2] or ""), _normalize_sql(row[3]))
        for row in conn.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        )
    }


def _schema_details(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    objects = _schema_object_map(conn)
    tables = {name for name, (kind, _, _) in objects.items() if kind == "table"}
    columns = {
        name: tuple(tuple(row) for row in conn.execute(f"PRAGMA table_info({_quote_identifier(name)})"))
        for name in tables
    }
    foreign_keys = {
        name: tuple(tuple(row) for row in conn.execute(f"PRAGMA foreign_key_list({_quote_identifier(name)})"))
        for name in tables
    }
    indexes = {
        name: tuple(tuple(row) for row in conn.execute(f"PRAGMA index_info({_quote_identifier(name)})"))
        for name, (kind, _, _) in objects.items()
        if kind == "index"
    }
    return {"objects": objects, "columns": columns, "foreign_keys": foreign_keys, "indexes": indexes}


def _expected_schema_details(fragments: list[_SchemaFragment]) -> dict[str, dict[str, Any]]:
    expected = sqlite3.connect(":memory:")
    try:
        expected.execute(SCHEMA_LEDGER_DDL)
        for fragment in fragments:
            for statement in _statements(fragment.sql):
                expected.execute(statement)
        return _schema_details(expected)
    finally:
        expected.close()


def _optional_search_details() -> dict[str, dict[str, Any]]:
    optional = sqlite3.connect(":memory:")
    try:
        optional.execute(
            """CREATE VIRTUAL TABLE search_trigram USING fts5(
            entity_type UNINDEXED, entity_id UNINDEXED, title, body, tokenize='trigram')"""
        )
        return _schema_details(optional)
    except sqlite3.DatabaseError:
        return {"objects": {}, "columns": {}, "foreign_keys": {}, "indexes": {}}
    finally:
        optional.close()


def _raise_schema_contract(message: str) -> None:
    raise SchemaContractError(message)


def _validate_current_schema(
    conn: sqlite3.Connection,
    scope: str,
    fragments: list[_SchemaFragment],
) -> None:
    actual = _schema_details(conn)
    expected = _expected_schema_details(fragments)
    optional = _optional_search_details() if scope == "project" else {"objects": {}, "columns": {}, "foreign_keys": {}, "indexes": {}}
    actual_objects = actual["objects"]
    expected_objects = expected["objects"]
    optional_objects = optional["objects"]
    actual_optional_names = set(actual_objects) & set(optional_objects)
    if actual_optional_names and actual_optional_names != set(optional_objects):
        _raise_schema_contract("optional search schema is incomplete")
    allowed_objects = set(expected_objects)
    if actual_optional_names:
        allowed_objects.update(optional_objects)
    if set(actual_objects) != allowed_objects:
        missing = sorted(allowed_objects - set(actual_objects))
        extra = sorted(set(actual_objects) - allowed_objects)
        _raise_schema_contract(f"SQLite schema objects differ from current contract; missing={missing}, extra={extra}")

    expected_details = expected
    if actual_optional_names:
        expected_details = {
            "objects": {**expected["objects"], **optional["objects"]},
            "columns": {**expected["columns"], **optional["columns"]},
            "foreign_keys": {**expected["foreign_keys"], **optional["foreign_keys"]},
            "indexes": {**expected["indexes"], **optional["indexes"]},
        }
    if actual["objects"] != expected_details["objects"]:
        _raise_schema_contract("SQLite schema object definitions differ from current contract")
    if actual["columns"] != expected_details["columns"]:
        _raise_schema_contract("SQLite table columns differ from current contract")
    if actual["foreign_keys"] != expected_details["foreign_keys"]:
        _raise_schema_contract("SQLite foreign-key structure differs from current contract")
    if actual["indexes"] != expected_details["indexes"]:
        _raise_schema_contract("SQLite index structure differs from current contract")

    try:
        identity = [tuple(row) for row in conn.execute("SELECT scope,release FROM quillframe_schema_identity")]
        expected_identity = [(scope, SCHEMA_RELEASE)]
        if identity != expected_identity:
            _raise_schema_contract(f"SQLite schema identity must be exactly {scope}:{SCHEMA_RELEASE}")
        ledger_rows = [
            tuple(row)
            for row in conn.execute(
                "SELECT scope,version,name,checksum,applied_at FROM schema_fragments ORDER BY scope,version"
            )
        ]
    except sqlite3.DatabaseError as exc:
        raise SchemaContractError(f"unable to validate current SQLite schema: {exc}") from exc

    expected_ledger = sorted(
        [(scope, fragment.version, fragment.name, fragment.checksum) for fragment in fragments],
        key=lambda row: (row[0], row[1]),
    )
    actual_ledger = [row[:4] for row in ledger_rows]
    if len(actual_ledger) != len(expected_ledger) or any(
        not isinstance(row[4], str) or not row[4].strip() for row in ledger_rows
    ):
        _raise_schema_contract("schema_fragments ledger is not an exact current ledger")
    for actual_row, expected_row in zip(actual_ledger, expected_ledger):
        if actual_row[:3] != expected_row[:3]:
            _raise_schema_contract("schema_fragments ledger scope/version/name is not exact")
        if actual_row[3] != expected_row[3]:
            raise SchemaChecksumError(
                f"{scope} schema fragment {expected_row[1]} checksum mismatch: "
                f"{actual_row[3]} != {expected_row[3]}"
            )


def _validated_schema_prefix(
    conn: sqlite3.Connection,
    scope: str,
    fragments: list[_SchemaFragment],
) -> int:
    """Return the exact installed fragment prefix, rejecting gaps and drift."""

    try:
        rows = conn.execute(
            "SELECT scope,version,name,checksum,applied_at FROM schema_fragments "
            "ORDER BY scope,version"
        ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise SchemaContractError(f"unable to read schema fragment ledger: {exc}") from exc
    if not rows or len(rows) > len(fragments):
        _raise_schema_contract("schema_fragments ledger is not a supported release prefix")
    for index, row in enumerate(rows):
        fragment = fragments[index]
        if (
            tuple(row[:3]) != (scope, fragment.version, fragment.name)
            or not isinstance(row[4], str)
            or not row[4].strip()
        ):
            _raise_schema_contract("schema_fragments ledger is not a continuous release prefix")
        if row[3] != fragment.checksum:
            raise SchemaChecksumError(
                f"{scope} schema fragment {fragment.name} checksum mismatch: "
                f"{row[3]} != {fragment.checksum}"
            )
    _validate_current_schema(conn, scope, fragments[: len(rows)])
    return len(rows)


def _apply_schema_upgrade(
    conn: sqlite3.Connection,
    fragments: list[_SchemaFragment],
    scope: str,
) -> list[dict[str, Any]]:
    """Atomically append missing, checksum-known schema fragments."""

    if conn.in_transaction:
        raise SchemaContractError("schema upgrade requires an idle SQLite connection")
    applied: list[dict[str, Any]] = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        applied = _append_schema_fragments_locked(conn, fragments, scope)
        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    return applied


def _append_schema_fragments_locked(
    conn: sqlite3.Connection,
    fragments: list[_SchemaFragment],
    scope: str,
) -> list[dict[str, Any]]:
    """Append a verified release suffix inside the caller's write transaction."""

    if not conn.in_transaction:
        raise SchemaContractError("locked schema upgrade requires a write transaction")
    prefix = _validated_schema_prefix(conn, scope, fragments)
    stamp = now_iso()
    applied: list[dict[str, Any]] = []
    for fragment in fragments[prefix:]:
        for statement in _statements(fragment.sql):
            conn.execute(statement)
        conn.execute(
            "INSERT INTO schema_fragments(scope,version,name,checksum,applied_at) "
            "VALUES(?,?,?,?,?)",
            (scope, fragment.version, fragment.name, fragment.checksum, stamp),
        )
        applied.append({
            "scope": scope,
            "version": fragment.version,
            "name": fragment.name,
            "checksum": fragment.checksum,
        })
    _validate_current_schema(conn, scope, fragments)
    return applied


def _assert_fresh_or_current_schema(conn: sqlite3.Connection, scope: str) -> bool:
    objects = _schema_object_map(conn)
    if not objects:
        return True
    if "quillframe_schema_identity" not in objects:
        raise Pre10StateRejectedError(
            "pre-1.0 SQLite state is not imported; create a new Quillframe 1.0 project"
        )
    return False


def _apply_fresh_schema(
    conn: sqlite3.Connection,
    fragments: list[_SchemaFragment],
    scope: str,
) -> list[dict[str, Any]]:
    if conn.in_transaction:
        raise SchemaContractError("fresh schema initialization requires an idle SQLite connection")
    applied: list[dict[str, Any]] = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(SCHEMA_LEDGER_DDL)
        stamp = now_iso()
        for fragment in fragments:
            for statement in _statements(fragment.sql):
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_fragments(scope,version,name,checksum,applied_at) VALUES(?,?,?,?,?)",
                (scope, fragment.version, fragment.name, fragment.checksum, stamp),
            )
            applied.append({"scope": scope, "version": fragment.version, "name": fragment.name, "checksum": fragment.checksum})
        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    return applied


def apply_schema(conn: sqlite3.Connection, scope: str) -> list[dict[str, Any]]:
    if scope not in {"global", "project"}:
        raise ValueError("scope must be global|project")
    fragments = _schema_fragments(scope)
    if _assert_fresh_or_current_schema(conn, scope):
        return _apply_fresh_schema(conn, fragments, scope)
    return _apply_schema_upgrade(conn, fragments, scope)


def _validate_project_chapter_rows(conn: sqlite3.Connection) -> None:
    """Prove actual novel topology and document ownership without repairing it."""
    try:
        story_rows = conn.execute("SELECT node_id,parent_id,kind,ordinal,metadata_json FROM story_nodes").fetchall()
        document_rows = conn.execute("SELECT document_id,story_node_id,document_kind FROM documents").fetchall()
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise BundleIdentityError("project contains dangling foreign-key references")
    except sqlite3.DatabaseError as exc:
        raise BundleSchemaError(f"unable to inspect chapter relationships: {exc}") from exc
    nodes = {row["node_id"]: row for row in story_rows}
    chapters = {key for key, row in nodes.items() if row["kind"] == "chapter"}
    positions: set[tuple[Any, ...]] = set()
    for node_id, row in nodes.items():
        if not isinstance(node_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", node_id):
            raise BundleIdentityError("story node identifier is not a bounded native identifier")
        if not isinstance(row["ordinal"], int) or row["ordinal"] < 0:
            raise BundleIdentityError("story node ordinal must be non-negative")
        position = (row["parent_id"], row["kind"], row["ordinal"])
        if position in positions:
            raise BundleIdentityError("story node sibling positions are ambiguous")
        positions.add(position)
        seen = {node_id}
        parent = row["parent_id"]
        while parent is not None:
            if parent not in nodes or parent in seen:
                raise BundleIdentityError("story node ancestry is missing or cyclic")
            seen.add(parent)
            parent = nodes[parent]["parent_id"]
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, ValueError) as exc:
            raise BundleSchemaError("story node metadata must be valid JSON") from exc
        if not isinstance(metadata, dict):
            raise BundleSchemaError("story node metadata must be an object")
        if "chapter_scope" in metadata:
            raise BundleIdentityError("legacy chapter_scope metadata is not a native novel contract")
        if metadata.get("chapter_id") is not None and metadata["chapter_id"] not in chapters:
            raise BundleIdentityError("story node metadata refers to an unknown chapter")
    manuscript_chapters: set[str] = set()
    for row in document_rows:
        linked = row["story_node_id"]
        if linked is not None and linked not in nodes:
            raise BundleIdentityError("document refers to an unknown story node")
        if row["document_kind"] == "manuscript":
            if linked not in chapters or linked in manuscript_chapters:
                raise BundleIdentityError("manuscript must belong to one distinct chapter")
            manuscript_chapters.add(linked)
    if chapters != manuscript_chapters:
        raise BundleIdentityError("each chapter must own exactly one manuscript")


def _validate_project_database_file(path: Path, project_id: str, scope: str) -> tuple[_ValidatedProjectDatabase, bytes]:
    database = _read_regular_nofollow(path, limit=MAX_BUNDLE_DATABASE_BYTES, label="project.sqlite")
    if scope != PROJECT_SCOPE:
        raise BundleSchemaError(f"scope must be exactly {PROJECT_SCOPE}")
    try:
        with _connect_readonly(path) as conn:
            objects = _schema_object_map(conn)
            if not objects or "quillframe_schema_identity" not in objects:
                raise BundleSchemaError("project.sqlite is not an existing native 1.0 database")
            try:
                _validated_schema_prefix(conn, "project", _schema_fragments("project"))
            except SchemaContractError as exc:
                raise BundleSchemaError(f"project schema is not a known exact release: {exc}") from exc
            except (sqlite3.DatabaseError, ValueError) as exc:
                raise BundleDatabaseError(f"project schema could not be validated: {exc}") from exc
            for pragma in ("quick_check", "integrity_check"):
                try:
                    result = conn.execute(f"PRAGMA {pragma}").fetchone()[0]
                except sqlite3.DatabaseError as exc:
                    raise BundleDatabaseError(f"project {pragma} failed to execute: {exc}") from exc
                if result != "ok":
                    raise BundleDatabaseError(f"project {pragma} failed: {result}")
            try:
                identity_rows = conn.execute(
                    "SELECT project_id,title,language,project_schema_version,created_at,updated_at FROM project_identity"
                ).fetchall()
            except sqlite3.DatabaseError as exc:
                raise BundleSchemaError(f"project_identity is unreadable: {exc}") from exc
            if len(identity_rows) != 1:
                raise BundleIdentityError("project_identity must contain exactly one row")
            identity = dict(identity_rows[0])
            if identity["project_id"] != project_id:
                raise BundleIdentityError(
                    f"project identity mismatch: {identity['project_id']!r} != {project_id!r}"
                )
            if (
                not isinstance(identity["title"], str)
                or not identity["title"].strip()
                or not isinstance(identity["language"], str)
                or not identity["language"].strip()
                or identity["project_schema_version"] != SCHEMA_VERSION
            ):
                raise BundleIdentityError("project_identity fields are not native 1.0 values")
            _validate_project_chapter_rows(conn)
            try:
                blob_rows = conn.execute(
                    "SELECT fingerprint,relative_path,byte_size FROM blob_refs ORDER BY relative_path"
                ).fetchall()
            except sqlite3.DatabaseError as exc:
                raise BundleSchemaError(f"blob_refs is unreadable: {exc}") from exc
            blobs = tuple(_validate_blob_metadata(dict(row)) for row in blob_rows)
    except BundleValidationError:
        raise
    except (sqlite3.DatabaseError, OSError, ValueError) as exc:
        raise BundleDatabaseError(f"project.sqlite could not be opened read-only: {exc}") from exc
    return _ValidatedProjectDatabase(identity=identity, blobs=blobs), database


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
    def __init__(self, root: Path | None = None, *, read_only: bool = False) -> None:
        requested_root = (root or data_root()).expanduser()
        self._requested_root = _absolute_lexical_path(requested_root)
        self.root = requested_root.resolve()
        self.read_only = read_only
        self.global_db = self.root / "quillframe.sqlite"
        self.projects_root = self.root / "projects"
        self.backups_root = self.root / "backups"
        self.cache_root = self.root / "cache"

    def ensure_layout(self) -> None:
        for path in (self.root, self.projects_root, self.backups_root, self.cache_root):
            path.mkdir(parents=True, exist_ok=True)

    def initialize_global(self) -> list[dict[str, Any]]:
        if self.read_only:
            return []
        self.ensure_layout()
        with _connect(self.global_db) as conn:
            return apply_schema(conn, "global")

    def location(self, project_id: str) -> ProjectLocation:
        d = project_dir(project_id, self.root)
        return ProjectLocation(project_id, d, d / "project.sqlite", d / "blobs", d / "exports")

    def list_projects(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the canonical global Project registry projection."""
        if not self.global_db.exists():
            return []
        bounded = max(1, min(int(limit), 500))
        with self._connect(self.global_db) as conn:
            rows = conn.execute(
                "SELECT project_id,title,language,project_schema_version,registered_at,last_opened_at "
                "FROM project_registry ORDER BY last_opened_at DESC, project_id LIMIT ?",
                (bounded,),
            ).fetchall()
        return [dict(row) for row in rows]

    def iter_project_ids_internal(
        self,
        *,
        page_size: int = 100,
        max_projects: int = MAX_INTERNAL_REGISTRY_PROJECTS,
    ) -> Iterator[str]:
        """Traverse the canonical registry for correctness-sensitive lookups.

        This deliberately returns only registry keys.  Project paths are
        reconstructed by ``location()`` at the call site; ``project_dir`` is
        never a locator.  The generator keeps a read/validation connection
        open for the traversal and uses keyset pagination so a public list
        projection limit cannot hide later Projects.
        """

        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or page_size < 1
            or page_size > MAX_INTERNAL_REGISTRY_PAGE_SIZE
        ):
            raise ValueError("page_size must be an integer between 1 and 500")
        if (
            isinstance(max_projects, bool)
            or not isinstance(max_projects, int)
            or max_projects < 1
            or max_projects > MAX_INTERNAL_REGISTRY_PROJECTS
        ):
            raise ValueError("max_projects must be an integer between 1 and 10000")

        try:
            value = os.lstat(self.global_db)
        except FileNotFoundError as exc:
            raise ProjectRegistryUnavailableError("canonical project registry is unavailable") from exc
        except OSError as exc:
            raise ProjectRegistryUnavailableError("canonical project registry is unavailable") from exc
        if stat.S_ISLNK(value.st_mode) or not stat.S_ISREG(value.st_mode):
            raise ProjectRegistryUnavailableError("canonical project registry is unavailable")

        conn: sqlite3.Connection | None = None
        try:
            conn = self._connect(self.global_db, configure_journal=False)
            # One explicit read transaction makes all keyset pages observe a
            # single registry snapshot.  Without it, a concurrent insert or
            # delete between pages could silently change the lookup universe.
            conn.execute("BEGIN")
            objects = _schema_object_map(conn)
            if not objects or "quillframe_schema_identity" not in objects:
                raise ProjectRegistryUnavailableError("canonical project registry is unavailable")
            fragments = _schema_fragments("global")
            _validate_current_schema(conn, "global", fragments)

            last_project_id = ""
            total = 0
            while True:
                rows = conn.execute(
                    "SELECT project_id FROM project_registry "
                    "WHERE project_id > ? ORDER BY project_id LIMIT ?",
                    (last_project_id, page_size),
                ).fetchall()
                if not rows:
                    break
                for row in rows:
                    project_id = row["project_id"]
                    try:
                        project_id = validate_project_id(project_id)
                    except (TypeError, ValueError) as exc:
                        raise ProjectRegistryUnavailableError(
                            "canonical project registry is unavailable"
                        ) from exc
                    if total >= max_projects:
                        raise ProjectLookupLimitError("canonical project registry lookup exceeded its bound")
                    total += 1
                    yield project_id
                last_project_id = rows[-1]["project_id"]
                if len(rows) < page_size:
                    break
        except (ProjectRegistryUnavailableError, ProjectLookupLimitError):
            raise
        except (OSError, sqlite3.DatabaseError, SchemaContractError, TypeError, ValueError) as exc:
            raise ProjectRegistryUnavailableError("canonical project registry is unavailable") from exc
        finally:
            if conn is not None:
                conn.close()

    def create_project(self, project_id: str, title: str, language: str = "zh-CN") -> ProjectLocation:
        if not title.strip():
            raise ValueError("title is required")
        self.initialize_global()
        loc = self.location(project_id)
        loc.blobs.mkdir(parents=True, exist_ok=True)
        loc.exports.mkdir(parents=True, exist_ok=True)
        with _connect(loc.database) as conn:
            apply_schema(conn, "project")
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

    def create_native_project(
        self,
        project_id: str,
        title: str,
        language: str = "zh-CN",
        *,
        before_commit: Callable[[sqlite3.Connection], None] | None = None,
    ) -> ProjectLocation:
        """Exclusively create a novel; identity and initial chapter commit together.

        An existing path or registry entry is a conflict, including incomplete
        earlier creations. No existing state is overwritten or repaired. The
        registry is a separate durable domain, registered only after the
        Project transaction commits. Launch owns cleanup of its reserved root.
        """
        if self.read_only:
            raise ProjectStateError("native creation requires a writable store")
        validate_project_id(project_id)
        if not isinstance(title, str) or not title.strip() or not isinstance(language, str) or not language.strip():
            raise ValueError("title and language must be non-empty strings")
        title, language = title.strip(), language.strip()
        _, root_fd = _open_real_directory_chain(self._requested_root)
        projects_fd: int | None = None
        project_fd: int | None = None
        database_fd: int | None = None
        global_fd: int | None = None
        try:
            for name in ("projects", "backups", "cache"):
                try:
                    os.mkdir(name, 0o700, dir_fd=root_fd)
                except FileExistsError:
                    pass
                child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
                os.close(child_fd)
            _, projects_fd = _open_real_directory_chain(self.projects_root)
            loc = self.location(project_id)
            global_fd = os.open("quillframe.sqlite", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=root_fd)
            global_token = os.fstat(global_fd)
            if not stat.S_ISREG(global_token.st_mode) or global_token.st_nlink != 1:
                raise ProjectStateError("native registry must be an owned regular file")
            with _connect_existing_fd(global_fd) as registry:
                if global_token.st_size == 0:
                    registry.execute("PRAGMA journal_mode=WAL")
                    registry.execute("PRAGMA synchronous=FULL")
                apply_schema(registry, "global")
                registry.execute("BEGIN IMMEDIATE")
                if registry.execute("SELECT 1 FROM project_registry WHERE project_id=?", (project_id,)).fetchone():
                    raise FileExistsError(f"project already exists: {project_id}")
                os.mkdir(project_id, 0o700, dir_fd=projects_fd)
                project_fd = os.open(project_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=projects_fd)
                project_token = os.fstat(project_fd)
                for name in ("blobs", "exports"):
                    os.mkdir(name, 0o700, dir_fd=project_fd)
                database_fd = os.open("project.sqlite", os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=project_fd)
                database_token = os.fstat(database_fd)

                def assert_owned() -> None:
                    current_registry = os.stat("quillframe.sqlite", dir_fd=root_fd, follow_symlinks=False)
                    current_project = os.stat(project_id, dir_fd=projects_fd, follow_symlinks=False)
                    current_database = os.stat("project.sqlite", dir_fd=project_fd, follow_symlinks=False)
                    if (
                        not stat.S_ISREG(current_registry.st_mode)
                        or current_registry.st_nlink != 1
                        or (current_registry.st_dev, current_registry.st_ino) != (global_token.st_dev, global_token.st_ino)
                        or not stat.S_ISDIR(current_project.st_mode)
                        or (current_project.st_dev, current_project.st_ino) != (project_token.st_dev, project_token.st_ino)
                        or not stat.S_ISREG(current_database.st_mode)
                        or current_database.st_nlink != 1
                        or (current_database.st_dev, current_database.st_ino) != (database_token.st_dev, database_token.st_ino)
                    ):
                        raise ProjectStateError("native creation reservation changed")
                    _, current_fd = _open_real_directory_chain(loc.directory)
                    try:
                        current = os.fstat(current_fd)
                        if (current.st_dev, current.st_ino) != (project_token.st_dev, project_token.st_ino):
                            raise ProjectStateError("native creation path changed")
                    finally:
                        os.close(current_fd)

                assert_owned()
                with _connect_existing_fd(database_fd) as conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=FULL")
                    apply_schema(conn, "project")
                    self._ensure_optional_search(conn)
                    conn.execute("BEGIN IMMEDIATE")
                    stamp = now_iso()
                    conn.execute(
                        "INSERT INTO project_identity(project_id,title,language,project_schema_version,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                        (project_id, title, language, SCHEMA_VERSION, stamp, stamp),
                    )
                    conn.execute(
                        "INSERT INTO story_nodes(node_id,parent_id,kind,ordinal,title,metadata_json) VALUES(?,NULL,'chapter',1,?,'{}')",
                        (INITIAL_CHAPTER_ID, title),
                    )
                    conn.execute(
                        "INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES(?,?,'manuscript',?,?)",
                        (f"DOC-{INITIAL_CHAPTER_ID}", INITIAL_CHAPTER_ID, title, stamp),
                    )
                    self.index_search(conn, "document", f"DOC-{INITIAL_CHAPTER_ID}", title, "", commit=False)
                    if before_commit is not None:
                        before_commit(conn)
                    assert_owned()
                    self.assert_native_project(conn)
                    conn.commit()
                assert_owned()
                registry.execute(
                    "INSERT INTO project_registry(project_id,title,language,project_schema_version,project_dir,registered_at,last_opened_at) VALUES(?,?,?,?,?,?,?)",
                    (project_id, title, language, SCHEMA_VERSION, str(loc.directory), stamp, stamp),
                )
                registry.commit()
            os.fsync(project_fd)
            os.fsync(projects_fd)
            return loc
        finally:
            for fd in (database_fd, project_fd, projects_fd, global_fd, root_fd):
                if fd is not None:
                    os.close(fd)

    @staticmethod
    def assert_native_project(conn: sqlite3.Connection) -> None:
        """Validate the current novel graph, never creation-time titles or plans."""
        try:
            _validate_project_chapter_rows(conn)
            chapters = {row[0] for row in conn.execute("SELECT node_id FROM story_nodes WHERE kind='chapter'")}
            manuscripts = {row[0] for row in conn.execute("SELECT story_node_id FROM documents WHERE document_kind='manuscript'")}
            if not chapters or chapters != manuscripts:
                raise ProjectStateError("native novel requires exactly one manuscript for each chapter")
        except BundleValidationError as exc:
            raise ProjectStateError(str(exc)) from exc

    def open_project(self, project_id: str) -> sqlite3.Connection:
        loc = self.location(project_id)
        if not loc.database.exists():
            raise FileNotFoundError(f"project database does not exist: {project_id}")
        # Existing project open is validation-only: preserve its current
        # journal mode and sidecars. Native create_project is the only path
        # that establishes WAL as part of initialization.
        conn = self._connect(loc.database, configure_journal=False)
        if not self.read_only:
            apply_schema(conn, "project")
        return conn

    def open_existing_project_strict(
        self,
        project_id: str,
        title: str,
        language: str,
        *,
        database_fd: int | None = None,
    ) -> sqlite3.Connection:
        """Begin an identity-checked write transaction and known-prefix upgrade.

        The returned connection remains inside ``BEGIN IMMEDIATE`` so callers
        can perform the first Project business writes on this same locked
        connection. An exact older 1.0 release prefix is upgraded only after
        the manifest identity is proven, and rolls back with the transaction.
        """
        if self.read_only:
            raise ValueError("strict existing Project open requires a writable store")
        if database_fd is None:
            raise ProjectStateError("strict existing Project open requires an inode guard")
        loc = self.location(project_id)
        if not loc.database.exists():
            raise FileNotFoundError(f"project database does not exist: {project_id}")
        # Do not change journal mode or otherwise initialize an existing DB
        # before its manifest-bound identity is checked in the write lock.
        conn = _connect_existing_fd(database_fd)
        try:
            conn.execute("BEGIN IMMEDIATE")
            schema_rows = conn.execute(
                "SELECT scope,release FROM quillframe_schema_identity"
            ).fetchall()
            identity_rows = conn.execute(
                "SELECT project_id,title,language,project_schema_version FROM project_identity"
            ).fetchall()
            if len(schema_rows) != 1 or tuple(schema_rows[0]) != ("project", SCHEMA_RELEASE):
                raise ProjectStateError(
                    f"SQLite schema identity must be exactly project:{SCHEMA_RELEASE}"
                )
            if len(identity_rows) != 1:
                raise ProjectStateError("SQLite project_identity must contain exactly one row")
            if tuple(identity_rows[0]) != (project_id, title, language, SCHEMA_VERSION):
                raise ProjectIdentityMismatchError(
                    "SQLite project_identity does not match the Project manifest"
                )
            _append_schema_fragments_locked(conn, _schema_fragments("project"), "project")
            self.assert_existing_project_identity(conn, project_id, title, language)
            return conn
        except Exception:
            try:
                conn.rollback()
            finally:
                conn.close()
            raise

    @staticmethod
    def assert_existing_project_identity(
        conn: sqlite3.Connection,
        project_id: str,
        title: str,
        language: str,
    ) -> None:
        try:
            schema_rows = conn.execute(
                "SELECT scope,release FROM quillframe_schema_identity"
            ).fetchall()
            if len(schema_rows) != 1 or tuple(schema_rows[0]) != ("project", SCHEMA_RELEASE):
                raise ProjectStateError(
                    f"SQLite schema identity must be exactly project:{SCHEMA_RELEASE}"
                )
            try:
                _validate_current_schema(conn, "project", _schema_fragments("project"))
            except SchemaContractError as exc:
                raise ProjectStateError("existing Project schema is not the exact current native contract") from exc
            identity_rows = conn.execute(
                "SELECT project_id,title,language,project_schema_version FROM project_identity"
            ).fetchall()
            if len(identity_rows) != 1:
                raise ProjectStateError("SQLite project_identity must contain exactly one row")
            if tuple(identity_rows[0]) != (project_id, title, language, SCHEMA_VERSION):
                raise ProjectIdentityMismatchError(
                    "SQLite project_identity does not match the Project manifest"
                )
        except (ProjectStateError, ProjectIdentityMismatchError):
            raise
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            raise ProjectStateError(f"unable to read current Project identity: {exc}") from exc

    def _connect(self, path: Path, *, configure_journal: bool = True) -> sqlite3.Connection:
        return _connect_readonly(path) if self.read_only else _connect(path, configure_journal=configure_journal)

    def _ensure_optional_search(self, conn: sqlite3.Connection) -> None:
        if not _fts5_available(conn):
            raise IntegrityError("SQLite FTS5 is required by Quillframe 1.0")
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
        if not isinstance(document_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", document_id):
            raise ValueError("document_id must be a bounded native identifier")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be non-empty")
        with self.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            node = conn.execute("SELECT kind FROM story_nodes WHERE node_id=?", (story_node_id,)).fetchone() if story_node_id is not None else None
            if story_node_id is not None and node is None:
                raise ValueError("document story_node_id must reference an existing story node")
            if document_kind == "manuscript":
                if node is None or node["kind"] != "chapter":
                    raise ValueError("manuscript story_node_id must reference an existing chapter")
                if conn.execute("SELECT 1 FROM documents WHERE story_node_id=? AND document_kind='manuscript'", (story_node_id,)).fetchone():
                    raise ConflictError("chapter already has a manuscript")
            conn.execute(
                "INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES(?,?,?,?,?)",
                (document_id, story_node_id, document_kind, title, now_iso()),
            )
            self.index_search(conn, "document", document_id, title, "", commit=False)
            conn.commit()

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
            conn.execute("BEGIN IMMEDIATE")
            title_row = conn.execute("SELECT title FROM documents WHERE document_id=?", (document_id,)).fetchone()
            if not title_row:
                raise KeyError(f"unknown document: {document_id}")
            fp = fingerprint_text(content)
            existing = conn.execute(
                "SELECT revision_id FROM document_revisions WHERE document_id=? AND content_fingerprint=?",
                (document_id, fp),
            ).fetchone()
            if existing:
                conn.rollback()
                return {"revision_id": existing["revision_id"], "content_fingerprint": fp, "deduplicated": True}
            latest = self.latest_revision(conn, document_id)
            actual = latest["revision_id"] if latest else None
            if actual != expected_parent_revision_id:
                raise ConflictError(f"revision conflict: expected parent {expected_parent_revision_id!r}, current {actual!r}")
            revision_id = "rev_" + uuid.uuid4().hex
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
        payload = bytes(data)
        if len(payload) > MAX_BUNDLE_BLOB_BYTES:
            raise IntegrityError("blob exceeds the native size limit")
        fp = fingerprint_bytes(payload)
        hex_digest = fp.split(":", 1)[1]
        loc = self.location(project_id)
        target = loc.blobs / hex_digest[:2] / hex_digest[2:]
        prefix_fd: int | None = None
        temporary_fd: int | None = None
        try:
            _, prefix_fd = _open_real_directory_chain(target.parent)
            name = target.name
            try:
                existing = os.lstat(name, dir_fd=prefix_fd)
            except FileNotFoundError:
                existing = None
            except OSError as exc:
                raise IntegrityError("blob path could not be inspected") from exc

            if existing is not None:
                _read_blob_entry_at(prefix_fd, name, fp)
            else:
                temporary_fd = self._create_unnamed_backup_fd(prefix_fd)
                view = memoryview(payload)
                offset = 0
                while offset < len(view):
                    written = os.write(temporary_fd, view[offset:])
                    if written <= 0:
                        raise IntegrityError("blob write did not make progress")
                    offset += written
                os.fsync(temporary_fd)
                published_by_this_call = False
                try:
                    _linkat_empty_path(temporary_fd, prefix_fd, name)
                    published_by_this_call = True
                except BackupPublishError as exc:
                    if exc.code != "backup_target_exists":
                        raise IntegrityError("blob could not be published safely") from exc
                if published_by_this_call:
                    try:
                        os.fsync(prefix_fd)
                    except OSError as exc:
                        raise IntegrityError("blob publication durability sync failed") from exc
                verified = _read_blob_entry_at(prefix_fd, name, fp)
                if published_by_this_call:
                    owned = os.fstat(temporary_fd)
                    if (owned.st_dev, owned.st_ino) != (verified.st_dev, verified.st_ino):
                        raise IntegrityError("published blob ownership changed before verification")
        except IntegrityError:
            raise
        except OSError as exc:
            raise IntegrityError("blob publication failed") from exc
        finally:
            if temporary_fd is not None:
                try:
                    os.close(temporary_fd)
                except OSError:
                    pass
            if prefix_fd is not None:
                try:
                    os.close(prefix_fd)
                except OSError:
                    pass
        rel = target.relative_to(loc.directory).as_posix()
        with self.open_project(project_id) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO blob_refs(fingerprint,relative_path,media_type,byte_size,created_at) VALUES(?,?,?,?,?)",
                (fp, rel, media_type, len(payload), now_iso()),
            )
            conn.commit()
        return {"fingerprint": fp, "relative_path": rel, "byte_size": len(payload)}

    def _snapshot(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with _connect_readonly(source) as src, sqlite3.connect(destination, factory=_ClosingConnection) as dst:
            src.backup(dst)
        with sqlite3.connect(destination, factory=_ClosingConnection) as check:
            if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise BundleDatabaseError("backup snapshot failed quick_check")

    @staticmethod
    def _read_project_blobs(loc: ProjectLocation, blobs: tuple[dict[str, Any], ...]) -> tuple[tuple[str, bytes], ...]:
        payloads: list[tuple[str, bytes]] = []
        for row in blobs:
            path = _assert_contained_regular_path(loc.directory, row["relative_path"], label="source blob")
            payload = _read_regular_nofollow(
                path,
                limit=MAX_BUNDLE_BLOB_BYTES,
                label=f"source blob {row['relative_path']}",
                require_single_link=True,
            )
            if len(payload) != row["byte_size"]:
                raise BundleBlobError(f"source blob size mismatch: {row['relative_path']}")
            if fingerprint_bytes(payload) != row["fingerprint"]:
                raise BundleBlobError(f"source blob fingerprint mismatch: {row['relative_path']}")
            payloads.append((row["relative_path"], payload))
        return tuple(payloads)

    def _validate_backup_archive(self, source: Any) -> _ValidatedBundle:
        try:
            with zipfile.ZipFile(source) as archive:
                members = _inspect_zip_members(archive)
                if "manifest.json" not in members or "project.sqlite" not in members:
                    raise BundleFormatError("backup ZIP must contain manifest.json and project.sqlite")
                manifest_raw = _read_zip_member(
                    archive,
                    members["manifest.json"],
                    limit=MAX_BUNDLE_MANIFEST_BYTES,
                    label="manifest.json",
                )
                manifest = _parse_bundle_manifest(manifest_raw)
                expected = {"manifest.json", "project.sqlite"} | {
                    row["relative_path"] for row in manifest["blobs"]
                }
                actual = set(members)
                if actual != expected:
                    missing = sorted(expected - actual)
                    unknown = sorted(actual - expected)
                    raise BundleFormatError(
                        f"backup ZIP member set is not exact; missing={missing}, unknown={unknown}",
                        code="bundle_members",
                    )
                database_info = members["project.sqlite"]
                database = _read_zip_member(
                    archive,
                    database_info,
                    limit=MAX_BUNDLE_DATABASE_BYTES,
                    label="project.sqlite",
                )
                if fingerprint_bytes(database) != manifest["database_fingerprint"]:
                    raise BundleDatabaseError("project.sqlite fingerprint mismatch")
                with tempfile.TemporaryDirectory(prefix="quillframe-bundle-verify-") as td:
                    database_path = Path(td) / "project.sqlite"
                    database_path.write_bytes(database)
                    database_result, _ = _validate_project_database_file(
                        database_path,
                        manifest["project_id"],
                        manifest["scope"],
                    )
                manifest_blobs = tuple(
                    {
                        "fingerprint": row["fingerprint"],
                        "relative_path": row["relative_path"],
                        "byte_size": row["byte_size"],
                    }
                    for row in manifest["blobs"]
                )
                if database_result.blobs != manifest_blobs:
                    raise BundleBlobError("manifest blobs do not exactly match project blob_refs")
                payloads: list[tuple[str, bytes]] = []
                for row in manifest["blobs"]:
                    info = members[row["relative_path"]]
                    payload = _read_zip_member(
                        archive,
                        info,
                        limit=MAX_BUNDLE_BLOB_BYTES,
                        label=row["relative_path"],
                    )
                    if len(payload) != row["byte_size"]:
                        raise BundleBlobError(f"blob size mismatch: {row['relative_path']}")
                    if fingerprint_bytes(payload) != row["fingerprint"]:
                        raise BundleBlobError(f"blob fingerprint mismatch: {row['relative_path']}")
                    payloads.append((row["relative_path"], payload))
                return _ValidatedBundle(
                    manifest=manifest,
                    database=database,
                    blobs=tuple(payloads),
                    identity=database_result.identity,
                )
        except BundleValidationError:
            raise
        except zipfile.BadZipFile as exc:
            raise BundleFormatError(f"invalid backup ZIP: {exc}") from exc
        except (OSError, ValueError) as exc:
            raise BundleFormatError(f"unable to validate backup bundle: {exc}") from exc

    def _validate_backup_bundle(self, bundle: Path) -> _ValidatedBundle:
        bundle = Path(bundle)
        try:
            bundle_stat = os.lstat(bundle)
        except OSError as exc:
            raise BundleFormatError(f"unable to stat backup bundle: {exc}") from exc
        if stat.S_ISLNK(bundle_stat.st_mode) or not stat.S_ISREG(bundle_stat.st_mode):
            raise BundlePathError("backup bundle must be a regular non-symlink file")
        if bundle_stat.st_size > MAX_BUNDLE_TOTAL_BYTES:
            raise BundleLimitError("backup bundle exceeds the native compressed-size limit")
        return self._validate_backup_archive(bundle)

    def _validate_backup_fd(self, descriptor: int) -> _ValidatedBundle:
        try:
            bundle_stat = os.fstat(descriptor)
        except OSError as exc:
            raise BundleFormatError("unable to stat unnamed backup bundle") from exc
        if not stat.S_ISREG(bundle_stat.st_mode):
            raise BundlePathError("unnamed backup bundle must be a regular file")
        if bundle_stat.st_size > MAX_BUNDLE_TOTAL_BYTES:
            raise BundleLimitError("backup bundle exceeds the native compressed-size limit")
        duplicate: int | None = None
        try:
            duplicate = os.dup(descriptor)
            os.lseek(duplicate, 0, os.SEEK_SET)
            with os.fdopen(duplicate, "rb") as handle:
                duplicate = None
                return self._validate_backup_archive(handle)
        except BundleValidationError:
            raise
        except OSError as exc:
            raise BundleFormatError("unable to read unnamed backup bundle") from exc
        finally:
            if duplicate is not None:
                try:
                    os.close(duplicate)
                except OSError:
                    pass

    @staticmethod
    def _stat_directory_entry(directory_fd: int, name: str, *, label: str) -> os.stat_result | None:
        try:
            value = os.lstat(name, dir_fd=directory_fd)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise BundlePathError(f"unable to inspect {label}", code="bundle_target_path") from exc
        if stat.S_ISLNK(value.st_mode):
            raise BundlePathError(f"{label} must not be a symlink", code="bundle_target_path")
        return value

    @staticmethod
    def _create_unnamed_backup_fd(directory_fd: int) -> int:
        unnamed = getattr(os, "O_TMPFILE", 0)
        if sys.platform != "linux" or not unnamed:
            raise BackupPublishError(
                "native unnamed backup publication is unavailable",
                code="backup_native_unavailable",
            )
        flags = os.O_RDWR | unnamed | getattr(os, "O_CLOEXEC", 0)
        try:
            return os.open(".", flags, 0o600, dir_fd=directory_fd)
        except OSError as exc:
            raise BackupPublishError(
                "native unnamed backup publication is unavailable",
                code="backup_native_unavailable",
            ) from exc

    @staticmethod
    def _record_backup_metadata(
        global_db: Path,
        *,
        backup_id: str,
        project_id: str,
        bundle: Path,
        manifest: dict[str, Any],
    ) -> None:
        with _connect(global_db) as conn:
            conn.execute(
                "INSERT INTO backup_metadata(backup_id,project_id,bundle_path,manifest_json,verified,created_at) VALUES(?,?,?,?,1,?)",
                (backup_id, project_id, str(bundle), canonical_json(manifest), now_iso()),
            )
            conn.commit()

    def backup_project(self, project_id: str, destination: Path | None = None) -> Path:
        try:
            project_id = validate_project_id(project_id)
        except (TypeError, ValueError) as exc:
            raise BundleIdentityError(f"invalid project id for backup: {exc}") from exc
        loc = self.location(project_id)
        if not loc.database.exists():
            raise FileNotFoundError(project_id)
        source_result, _ = _validate_project_database_file(loc.database, project_id, PROJECT_SCOPE)
        if not self.global_db.is_file() or self.global_db.is_symlink():
            raise IntegrityError("global database is required before publishing backup metadata")
        backup_id = "backup_" + uuid.uuid4().hex
        target = _absolute_lexical_path(
            Path(destination) if destination is not None else self.backups_root / f"{project_id}-{backup_id}.qfbackup"
        )
        with tempfile.TemporaryDirectory(prefix="quillframe-backup-") as td:
            temp = Path(td)
            db_copy = temp / "project.sqlite"
            self._snapshot(loc.database, db_copy)
            snapshot_result, database = _validate_project_database_file(db_copy, project_id, PROJECT_SCOPE)
            if snapshot_result.identity != source_result.identity or snapshot_result.blobs != source_result.blobs:
                raise BundleDatabaseError("source project changed during read-only backup snapshot")
            payloads = self._read_project_blobs(loc, snapshot_result.blobs)
            manifest = {
                "schema": BUNDLE_SCHEMA,
                "project_schema": PROJECT_SCHEMA,
                "scope": PROJECT_SCOPE,
                "backup_id": backup_id,
                "project_id": project_id,
                "created_at": now_iso(),
                "database_fingerprint": fingerprint_bytes(database),
                "blobs": [dict(row) for row in snapshot_result.blobs],
            }
            manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            parent, parent_fd = _open_real_directory_chain(target.parent)
            try:
                existing = self._stat_directory_entry(parent_fd, target.name, label="backup target")
                if existing is not None:
                    raise FileExistsError("backup target already exists")
                temporary_fd = self._create_unnamed_backup_fd(parent_fd)
                try:
                    writer_fd: int | None = None
                    try:
                        writer_fd = os.dup(temporary_fd)
                        with os.fdopen(writer_fd, "w+b") as handle:
                            writer_fd = None
                            with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                                archive.writestr("manifest.json", manifest_bytes)
                                archive.writestr("project.sqlite", database)
                                for relative_path, payload in payloads:
                                    archive.writestr(relative_path, payload)
                            handle.flush()
                            os.fsync(handle.fileno())
                    finally:
                        if writer_fd is not None:
                            try:
                                os.close(writer_fd)
                            except OSError:
                                pass
                    self._validate_backup_fd(temporary_fd)
                    _linkat_empty_path(temporary_fd, parent_fd, target.name)
                    try:
                        os.fsync(parent_fd)
                    except OSError as exc:
                        raise BackupPublishError(
                            "backup publish durability sync failed; published bundle retained",
                            code="backup_publish",
                        ) from exc
                    try:
                        self._record_backup_metadata(
                            self.global_db,
                            backup_id=backup_id,
                            project_id=project_id,
                            bundle=target,
                            manifest=manifest,
                        )
                    except Exception as exc:
                        raise BackupPublishError(
                            "backup metadata recording failed; published bundle retained",
                            code="backup_metadata",
                        ) from exc
                    return target
                finally:
                    try:
                        os.close(temporary_fd)
                    except OSError:
                        pass
            finally:
                os.close(parent_fd)

    def verify_backup(self, bundle: Path) -> dict[str, Any]:
        try:
            validated = self._validate_backup_bundle(Path(bundle))
        except BundleValidationError as exc:
            message = _public_bundle_error_message(exc.code)
            error = {"code": exc.code, "type": type(exc).__name__, "message": message}
            return {"valid": False, "errors": [message], "error": error}
        return {
            "valid": True,
            "errors": [],
            "error": None,
            "manifest": validated.manifest,
            "database_fingerprint": validated.manifest["database_fingerprint"],
            "blob_count": len(validated.blobs),
        }

    def verify_backup_bytes(self, bundle: bytes | bytearray | memoryview) -> dict[str, Any]:
        """Validate an exact native bundle from a bounded, unnamed file object.

        This is a narrow adapter for hosted raw-body verification.  It delegates
        all ZIP/SQLite/blob checks to the C3A fd validator and exposes only the
        fields required by the caller; it never creates a project or writes
        persistence state.
        """
        if not isinstance(bundle, (bytes, bytearray, memoryview)):
            raise BundleFormatError("backup bundle bytes are invalid")
        raw = bytes(bundle)
        if not raw or len(raw) > MAX_BUNDLE_TOTAL_BYTES:
            raise BundleLimitError("backup bundle exceeds the native compressed-size limit")
        with tempfile.TemporaryFile(mode="w+b") as handle:
            handle.write(raw)
            handle.flush()
            handle.seek(0)
            validated = self._validate_backup_fd(handle.fileno())
        return {
            "manifest": validated.manifest,
            "database_bytes": len(validated.database),
            "blob_count": len(validated.blobs),
        }

    def _restore_fault_inject(self, phase: str) -> None:
        """Deterministic test seam; production has no injected failures."""

    @staticmethod
    def _restore_inode(value: os.stat_result | None) -> list[int] | None:
        if value is None:
            return None
        return [int(value.st_dev), int(value.st_ino)]

    @staticmethod
    def _restore_inode_tuple(value: Any) -> tuple[int, int] | None:
        if value is None:
            return None
        if (
            not isinstance(value, list)
            or len(value) != 2
            or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value)
        ):
            raise RestoreIncompleteError(
                _public_restore_error_message("restore_incomplete"),
                code="restore_incomplete",
            )
        return (value[0], value[1])

    def _restore_preflight_target(self, project_id: str, *, replace: bool) -> Path:
        """Read-only target/ancestor validation before any Quillframe write."""

        requested_root = self._requested_root
        current_root = Path(requested_root.anchor or os.sep)
        for part in requested_root.parts[1:]:
            current_root = current_root / part
            try:
                root_value = os.lstat(current_root)
            except FileNotFoundError:
                break
            except OSError as exc:
                raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
            if stat.S_ISLNK(root_value.st_mode) or not stat.S_ISDIR(root_value.st_mode):
                raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
        target = _absolute_lexical_path(self.location(project_id).directory)
        current = Path(target.anchor or os.sep)
        for part in target.parts[1:]:
            current = current / part
            try:
                value = os.lstat(current)
            except FileNotFoundError:
                break
            except OSError as exc:
                raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
            if stat.S_ISLNK(value.st_mode):
                raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
            if current != target and not stat.S_ISDIR(value.st_mode):
                raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
            if current == target:
                if not stat.S_ISDIR(value.st_mode):
                    raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
                if replace:
                    raise RestoreReplacementUnavailable(
                        _public_restore_error_message("restore_replacement_unavailable"),
                        code="restore_replacement_unavailable",
                    )
                raise FileExistsError("project already exists")
        return target

    @staticmethod
    def _restore_open_lock(projects_fd: int, project_id: str) -> int:
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if not nofollow or fcntl is None:
            raise RestoreIncompleteError(
                _public_restore_error_message("restore_native_unavailable"),
                code="restore_native_unavailable",
            )
        name = f".{project_id}.restore.lock"
        try:
            fd = os.open(
                name,
                os.O_RDWR | os.O_CREAT | nofollow | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=projects_fd,
            )
            value = os.fstat(fd)
            if not stat.S_ISREG(value.st_mode):
                os.close(fd)
                raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
            fcntl.flock(fd, fcntl.LOCK_EX)
            return fd
        except RestoreError:
            raise
        except OSError as exc:
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc

    @staticmethod
    def _restore_close_lock(lock_fd: int | None) -> None:
        if lock_fd is None:
            return
        try:
            if fcntl is not None:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)

    @staticmethod
    def _restore_create_stage(projects_fd: int, project_id: str, nonce: str) -> tuple[str, int]:
        name = f".{project_id}.restore-stage-{nonce}"
        try:
            os.mkdir(name, 0o700, dir_fd=projects_fd)
            _restore_fsync_directory(projects_fd)
            fd = _restore_open_or_create_directory(projects_fd, name, label="restore stage")
            return name, fd
        except FileExistsError as exc:
            raise RestoreConflictError(
                _public_restore_error_message("restore_target_exists"),
                code="restore_target_exists",
            ) from exc

    @staticmethod
    def _restore_expected_tree(
        root: Path,
        *,
        project_id: str,
        blob_rows: tuple[dict[str, Any], ...],
        database_fingerprint: str,
        database_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        try:
            root_stat = os.lstat(root)
        except OSError as exc:
            raise RestoreIncompleteError(
                _public_restore_error_message("restore_incomplete"),
                code="restore_incomplete",
            ) from exc
        if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
        files: set[str] = set()
        directories: set[str] = set()

        def walk(directory: Path, prefix: str) -> None:
            try:
                entries = list(os.scandir(directory))
            except OSError as exc:
                raise RestoreIncompleteError(
                    _public_restore_error_message("restore_incomplete"),
                    code="restore_incomplete",
                ) from exc
            for entry in entries:
                child = Path(entry.path)
                relative = f"{prefix}/{entry.name}" if prefix else entry.name
                try:
                    value = os.lstat(child)
                except OSError as exc:
                    raise RestoreIncompleteError(
                        _public_restore_error_message("restore_incomplete"),
                        code="restore_incomplete",
                    ) from exc
                if stat.S_ISLNK(value.st_mode):
                    raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
                if stat.S_ISDIR(value.st_mode):
                    directories.add(relative)
                    walk(child, relative)
                elif stat.S_ISREG(value.st_mode):
                    files.add(relative)
                else:
                    raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")

        walk(root, "")
        expected_files = {"project.sqlite"} | {row["relative_path"] for row in blob_rows}
        expected_directories: set[str] = set()
        for relative in expected_files:
            parts = relative.split("/")[:-1]
            for index in range(1, len(parts) + 1):
                expected_directories.add("/".join(parts[:index]))
        if files != expected_files or directories != expected_directories:
            raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_tree")
        database_path = root / "project.sqlite"
        database = _read_regular_nofollow(
            database_path,
            limit=MAX_BUNDLE_DATABASE_BYTES,
            label="restored project database",
            require_single_link=True,
        )
        if database_bytes is not None and database != database_bytes:
            raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_database")
        if fingerprint_bytes(database) != database_fingerprint:
            raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_database")
        try:
            result, _ = _validate_project_database_file(database_path, project_id, PROJECT_SCOPE)
        except BundleValidationError as exc:
            raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_database") from exc
        expected_blobs = tuple(_validate_blob_metadata(row) for row in blob_rows)
        if result.blobs != expected_blobs:
            raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_blob")
        for row in blob_rows:
            path = root / row["relative_path"]
            payload = _read_regular_nofollow(
                path,
                limit=MAX_BUNDLE_BLOB_BYTES,
                label="restored blob",
                require_single_link=True,
            )
            if len(payload) != row["byte_size"] or fingerprint_bytes(payload) != row["fingerprint"]:
                raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_blob")
        return result.identity

    @staticmethod
    def _restore_record(
        *,
        project_id: str,
        nonce: str,
        sequence: int,
        phase: str,
        stage_name: str,
        stage_inode: list[int] | None,
        target_inode: list[int] | None,
        identity: dict[str, Any],
        database_fingerprint: str,
        blob_rows: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        return {
            "schema": RESTORE_JOURNAL_SCHEMA,
            "project_id": project_id,
            "nonce": nonce,
            "sequence": sequence,
            "phase": phase,
            "stage_name": stage_name,
            "stage_inode": stage_inode,
            "target_name": project_id,
            "target_inode": target_inode,
            "identity": {
                "project_id": identity["project_id"],
                "title": identity["title"],
                "language": identity["language"],
                "project_schema_version": identity["project_schema_version"],
            },
            "project_schema": PROJECT_SCHEMA,
            "scope": PROJECT_SCOPE,
            "database_fingerprint": database_fingerprint,
            "blobs": [dict(row) for row in blob_rows],
            "registry_prestate": None,
            "retention": dict(RESTORE_RETENTION),
        }

    @staticmethod
    def _restore_validate_record(record: Any, *, filename: str) -> dict[str, Any]:
        keys = {
            "schema",
            "project_id",
            "nonce",
            "sequence",
            "phase",
            "stage_name",
            "stage_inode",
            "target_name",
            "target_inode",
            "identity",
            "project_schema",
            "scope",
            "database_fingerprint",
            "blobs",
            "registry_prestate",
            "retention",
        }
        if not isinstance(record, dict) or set(record) != keys:
            raise RestoreIncompleteError(
                _public_restore_error_message("restore_incomplete"),
                code="restore_incomplete",
            )
        match = RESTORE_JOURNAL_RE.fullmatch(filename)
        if not match or record["schema"] != RESTORE_JOURNAL_SCHEMA:
            raise RestoreIncompleteError(
                _public_restore_error_message("restore_incomplete"),
                code="restore_incomplete",
            )
        project_id = match.group("project")
        if record["project_id"] != project_id or record["target_name"] != project_id:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        nonce = match.group("nonce")
        if record["nonce"] != nonce:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        sequence = record["sequence"]
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence != int(match.group("sequence")):
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        if record["phase"] not in set(RESTORE_PHASES):
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        if record["stage_name"] != f".{project_id}.restore-stage-{nonce}":
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        if record["project_schema"] != PROJECT_SCHEMA or record["scope"] != PROJECT_SCOPE:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        try:
            validate_project_id(project_id)
            database_fingerprint = _validate_fingerprint(record["database_fingerprint"], "database_fingerprint")
            blob_rows = tuple(_validate_blob_metadata(row) for row in record["blobs"])
        except (BundleValidationError, TypeError, ValueError) as exc:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete") from exc
        if record["registry_prestate"] is not None:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        if record["retention"] != RESTORE_RETENTION:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        identity = record["identity"]
        if (
            not isinstance(identity, dict)
            or set(identity) != {"project_id", "title", "language", "project_schema_version"}
            or identity["project_id"] != project_id
            or not isinstance(identity["title"], str)
            or not identity["title"].strip()
            or not isinstance(identity["language"], str)
            or not identity["language"].strip()
            or identity["project_schema_version"] != SCHEMA_VERSION
        ):
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        stage_inode = QuillframeStore._restore_inode_tuple(record["stage_inode"])
        target_inode = QuillframeStore._restore_inode_tuple(record["target_inode"])
        if record["phase"] in {"STAGING", "PREPARED", "ABORTED"} and target_inode is not None:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        if record["phase"] in {"NEW_SWAPPED", "REGISTRY_UPSERTED", "COMMITTED"} and target_inode is None:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        result = dict(record)
        result["database_fingerprint"] = database_fingerprint
        result["blobs"] = blob_rows
        result["stage_inode_tuple"] = stage_inode
        result["target_inode_tuple"] = target_inode
        return result

    def _restore_publish_journal(
        self,
        root_fd: int,
        _previous_name: str | None,
        record: dict[str, Any],
    ) -> str:
        filename = (
            f".{record['project_id']}.restore-{record['nonce']}-{int(record['sequence']):04d}.journal"
        )
        _restore_write_journal(root_fd, filename, record)
        return filename

    def _restore_append_aborted(
        self,
        root_fd: int,
        previous_name: str | None,
        record: dict[str, Any],
    ) -> str:
        aborted = {
            "schema": RESTORE_JOURNAL_SCHEMA,
            "project_id": record["project_id"],
            "nonce": record["nonce"],
            "sequence": int(record["sequence"]) + 1,
            "phase": "ABORTED",
            "stage_name": record["stage_name"],
            "stage_inode": record.get("stage_inode"),
            "target_name": record["target_name"],
            "target_inode": None,
            "identity": dict(record["identity"]),
            "project_schema": PROJECT_SCHEMA,
            "scope": PROJECT_SCOPE,
            "database_fingerprint": record["database_fingerprint"],
            "blobs": [dict(row) for row in record["blobs"]],
            "registry_prestate": None,
            "retention": dict(RESTORE_RETENTION),
        }
        return self._restore_publish_journal(root_fd, previous_name, aborted)

    def _restore_global_connection(self) -> sqlite3.Connection:
        try:
            value = os.lstat(self.global_db)
        except FileNotFoundError:
            value = None
        except OSError as exc:
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
        if value is not None and (stat.S_ISLNK(value.st_mode) or not stat.S_ISREG(value.st_mode)):
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
        conn: sqlite3.Connection | None = None
        succeeded = False
        try:
            conn = self._connect(self.global_db)
            apply_schema(conn, "global")
            conn.execute("BEGIN IMMEDIATE")
            succeeded = True
            return conn
        except RestoreError:
            raise
        except (OSError, sqlite3.DatabaseError, SchemaContractError, ValueError) as exc:
            raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_global") from exc
        finally:
            if conn is not None and not succeeded:
                # A failed schema/open path must not leave a live handle.  A
                # returned transaction remains owned by the caller.
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def _restore_registry_row(conn: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
        row = conn.execute(
            "SELECT project_id,title,language,project_schema_version,project_dir,registered_at,last_opened_at "
            "FROM project_registry WHERE project_id=?",
            (project_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def _restore_registry_matches(
        self,
        row: dict[str, Any],
        identity: dict[str, Any],
        target: Path,
    ) -> bool:
        return (
            row["project_id"] == identity["project_id"]
            and row["title"] == identity["title"]
            and row["language"] == identity["language"]
            and row["project_schema_version"] == SCHEMA_VERSION
            and row["project_dir"] == str(target)
        )

    def _restore_insert_registry(
        self,
        conn: sqlite3.Connection,
        identity: dict[str, Any],
        target: Path,
    ) -> None:
        if self._restore_registry_row(conn, identity["project_id"]) is not None:
            raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_registry_conflict")
        stamp = now_iso()
        conn.execute(
            "INSERT INTO project_registry(project_id,title,language,project_schema_version,project_dir,registered_at,last_opened_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                identity["project_id"],
                identity["title"],
                identity["language"],
                SCHEMA_VERSION,
                str(target),
                stamp,
                stamp,
            ),
        )

    def _restore_recovery_records(self) -> list[tuple[Path, dict[str, Any]]]:
        if not os.path.lexists(self.root):
            return []
        try:
            root_stat = os.lstat(self.root)
        except OSError as exc:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete") from exc
        if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
        records: list[tuple[Path, dict[str, Any]]] = []
        terminal_records = 0
        journal_bytes = 0
        directory_entries = 0
        try:
            with os.scandir(self.root) as entries:
                for entry in entries:
                    directory_entries += 1
                    if directory_entries > MAX_RESTORE_DIRECTORY_ENTRIES:
                        raise RestoreIncompleteError(
                            _public_restore_error_message("restore_incomplete"),
                            code="restore_incomplete",
                        )
                    if ".restore-" not in entry.name or not entry.name.endswith(".journal"):
                        continue
                    match = RESTORE_JOURNAL_RE.fullmatch(entry.name)
                    if match is None:
                        raise RestoreIncompleteError(
                            _public_restore_error_message("restore_incomplete"),
                            code="restore_incomplete",
                        )
                    try:
                        raw = _read_regular_nofollow(
                            Path(entry.path),
                            limit=MAX_BUNDLE_MANIFEST_BYTES,
                            label="restore journal",
                            require_single_link=True,
                        )
                        journal_bytes += len(raw)
                        if journal_bytes > MAX_RESTORE_JOURNAL_BYTES:
                            raise RestoreIncompleteError(
                                _public_restore_error_message("restore_incomplete"),
                                code="restore_incomplete",
                            )
                        record = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_pairs)
                    except Exception as exc:
                        if isinstance(exc, RestoreError):
                            raise
                        raise RestoreIncompleteError(
                            _public_restore_error_message("restore_incomplete"),
                            code="restore_incomplete",
                        ) from exc
                    validated_record = self._restore_validate_record(record, filename=entry.name)
                    records.append((Path(entry.path), validated_record))
                    if validated_record["phase"] in RESTORE_TERMINAL_PHASES:
                        terminal_records += 1
                        if terminal_records > MAX_RESTORE_TERMINAL_RECORDS:
                            raise RestoreIncompleteError(
                                _public_restore_error_message("restore_incomplete"),
                                code="restore_incomplete",
                            )
        except OSError as exc:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete") from exc
        records.sort(key=lambda item: (item[1]["project_id"], item[1]["nonce"], item[1]["sequence"]))
        seen: set[tuple[str, str, int]] = set()
        for _, record in records:
            key = (record["project_id"], record["nonce"], record["sequence"])
            if key in seen:
                raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
            seen.add(key)
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for _, record in records:
            latest[(record["project_id"], record["nonce"])] = record
        active_operations = {
            operation
            for operation, record in latest.items()
            if record["phase"] not in RESTORE_TERMINAL_PHASES
        }
        active_records = sum(
            1
            for _, record in records
            if (record["project_id"], record["nonce"]) in active_operations
            and record["phase"] not in RESTORE_TERMINAL_PHASES
        )
        if active_records > MAX_RESTORE_JOURNAL_RECORDS or len(active_operations) > MAX_RESTORE_ACTIVE_OPERATIONS:
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
        return records

    def _restore_validate_record_tree(self, path: Path, record: dict[str, Any]) -> dict[str, Any]:
        return self._restore_expected_tree(
            path,
            project_id=record["project_id"],
            blob_rows=record["blobs"],
            database_fingerprint=record["database_fingerprint"],
        )

    def restore_project(self, bundle: Path, *, replace: bool = False) -> ProjectLocation:
        try:
            validated = self._validate_backup_bundle(Path(bundle))
        except BundleValidationError as exc:
            raise BackupRestoreError(_public_bundle_error_message(exc.code), code=exc.code) from exc
        manifest = validated.manifest
        project_id = manifest["project_id"]
        target = self._restore_preflight_target(project_id, replace=replace)
        nonce = uuid.uuid4().hex
        root_fd: int | None = None
        try:
            root_path, root_fd = _open_real_directory_chain(self.root)
            projects_path, projects_fd = _open_real_directory_chain(self.projects_root)
        except BundleValidationError as exc:
            if root_fd is not None:
                os.close(root_fd)
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
        lock_fd: int | None = None
        stage_fd: int | None = None
        global_conn: sqlite3.Connection | None = None
        journal_name: str | None = None
        published = False
        record: dict[str, Any] | None = None
        stage_name = f".{project_id}.restore-stage-{nonce}"
        try:
            self._restore_fault_inject("BEFORE_GLOBAL_LOCK")
            lock_fd = self._restore_open_lock(projects_fd, project_id)
            try:
                existing = os.lstat(project_id, dir_fd=projects_fd)
            except FileNotFoundError:
                existing = None
            if existing is not None:
                if stat.S_ISLNK(existing.st_mode) or not stat.S_ISDIR(existing.st_mode):
                    raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path")
                raise RestoreConflictError(_public_restore_error_message("restore_target_exists"), code="restore_target_exists")
            stage_name, stage_fd = self._restore_create_stage(projects_fd, project_id, nonce)
            stage_stat = os.fstat(stage_fd)
            blob_rows = tuple(dict(row) for row in manifest["blobs"])
            record = self._restore_record(
                project_id=project_id,
                nonce=nonce,
                sequence=1,
                phase="STAGING",
                stage_name=stage_name,
                stage_inode=self._restore_inode(stage_stat),
                target_inode=None,
                identity=validated.identity,
                database_fingerprint=manifest["database_fingerprint"],
                blob_rows=blob_rows,
            )
            journal_name = self._restore_publish_journal(root_fd, None, record)
            self._restore_fault_inject("STAGING")
            _restore_write_bytes_at(stage_fd, "project.sqlite", validated.database)
            for relative_path, payload in validated.blobs:
                _restore_write_bytes_at(stage_fd, relative_path, payload)
            os.fsync(stage_fd)
            stage_stat = os.fstat(stage_fd)
            identity = self._restore_expected_tree(
                projects_path / stage_name,
                project_id=project_id,
                blob_rows=blob_rows,
                database_fingerprint=manifest["database_fingerprint"],
                database_bytes=validated.database,
            )
            record = self._restore_record(
                project_id=project_id,
                nonce=nonce,
                sequence=2,
                phase="PREPARED",
                stage_name=stage_name,
                stage_inode=self._restore_inode(stage_stat),
                target_inode=None,
                identity=identity,
                database_fingerprint=manifest["database_fingerprint"],
                blob_rows=blob_rows,
            )
            journal_name = self._restore_publish_journal(root_fd, journal_name, record)
            self._restore_fault_inject("PREPARED")
            global_conn = self._restore_global_connection()
            if self._restore_registry_row(global_conn, project_id) is not None:
                raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_registry_conflict")
            try:
                existing = os.lstat(project_id, dir_fd=projects_fd)
            except FileNotFoundError:
                existing = None
            if existing is not None:
                raise RestoreConflictError(_public_restore_error_message("restore_target_exists"), code="restore_target_exists")
            _rename_noreplace(projects_fd, stage_name, projects_fd, project_id)
            stage_fd = None
            published = True
            _restore_fsync_directory(projects_fd)
            target_stat = os.lstat(project_id, dir_fd=projects_fd)
            record = self._restore_record(
                project_id=project_id,
                nonce=nonce,
                sequence=3,
                phase="NEW_SWAPPED",
                stage_name=stage_name,
                stage_inode=None,
                target_inode=self._restore_inode(target_stat),
                identity=identity,
                database_fingerprint=manifest["database_fingerprint"],
                blob_rows=blob_rows,
            )
            journal_name = self._restore_publish_journal(root_fd, journal_name, record)
            self._restore_expected_tree(
                target,
                project_id=project_id,
                blob_rows=blob_rows,
                database_fingerprint=manifest["database_fingerprint"],
                database_bytes=validated.database,
            )
            self._restore_fault_inject("NEW_SWAPPED")
            self._restore_insert_registry(global_conn, identity, target)
            record = self._restore_record(
                project_id=project_id,
                nonce=nonce,
                sequence=4,
                phase="REGISTRY_UPSERTED",
                stage_name=stage_name,
                stage_inode=None,
                target_inode=self._restore_inode(target_stat),
                identity=identity,
                database_fingerprint=manifest["database_fingerprint"],
                blob_rows=blob_rows,
            )
            journal_name = self._restore_publish_journal(root_fd, journal_name, record)
            self._restore_fault_inject("REGISTRY_UPSERTED")
            global_conn.commit()
            record = self._restore_record(
                project_id=project_id,
                nonce=nonce,
                sequence=5,
                phase="COMMITTED",
                stage_name=stage_name,
                stage_inode=None,
                target_inode=self._restore_inode(target_stat),
                identity=identity,
                database_fingerprint=manifest["database_fingerprint"],
                blob_rows=blob_rows,
            )
            journal_name = self._restore_publish_journal(root_fd, journal_name, record)
            self._restore_fault_inject("COMMITTED")
            return self.location(project_id)
        except FileExistsError:
            raise
        except RestoreReplacementUnavailable:
            raise
        except RestoreError:
            if global_conn is not None and global_conn.in_transaction:
                global_conn.rollback()
            if not published:
                if stage_fd is not None:
                    os.close(stage_fd)
                    stage_fd = None
                if record is not None and journal_name is not None:
                    journal_name = self._restore_append_aborted(root_fd, journal_name, record)
            raise
        except Exception as exc:
            if global_conn is not None and global_conn.in_transaction:
                global_conn.rollback()
            if not published:
                if stage_fd is not None:
                    os.close(stage_fd)
                    stage_fd = None
                if record is not None and journal_name is not None:
                    journal_name = self._restore_append_aborted(root_fd, journal_name, record)
                elif record is None:
                    raise RestoreIncompleteError(
                        _public_restore_error_message("restore_incomplete"),
                        code="restore_incomplete",
                    ) from exc
                raise RestoreError(_public_restore_error_message("restore_failed"), code="restore_failed") from exc
            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete") from exc
        finally:
            if stage_fd is not None:
                os.close(stage_fd)
            if global_conn is not None:
                global_conn.close()
            self._restore_close_lock(lock_fd)
            os.close(projects_fd)
            os.close(root_fd)

    def restore_recovery(self) -> list[str]:
        records = self._restore_recovery_records()
        if not records:
            return []
        by_operation: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
        for path, record in records:
            operation = (record["project_id"], record["nonce"])
            current = by_operation.get(operation)
            if current is None or record["sequence"] > current[1]["sequence"]:
                by_operation[operation] = (path, record)
        root_fd: int | None = None
        try:
            root_path, root_fd = _open_real_directory_chain(self.root)
            projects_path, projects_fd = _open_real_directory_chain(self.projects_root)
        except BundleValidationError as exc:
            if root_fd is not None:
                os.close(root_fd)
            raise RestorePathError(_public_restore_error_message("restore_path"), code="restore_path") from exc
        recovered: list[str] = []
        try:
            for (project_id, _nonce), (journal_path, record) in sorted(by_operation.items()):
                if record["phase"] == "ABORTED":
                    recovered.append(project_id)
                    continue
                lock_fd: int | None = None
                conn: sqlite3.Connection | None = None
                try:
                    lock_fd = self._restore_open_lock(projects_fd, project_id)
                    conn = self._restore_global_connection()
                    target = projects_path / project_id
                    stage = projects_path / record["stage_name"]
                    try:
                        target_stat = os.lstat(project_id, dir_fd=projects_fd)
                    except FileNotFoundError:
                        target_stat = None
                    try:
                        stage_stat = os.lstat(record["stage_name"], dir_fd=projects_fd)
                    except FileNotFoundError:
                        stage_stat = None
                    if record["phase"] in {"STAGING", "PREPARED"}:
                        if target_stat is not None:
                            self._restore_append_aborted(root_fd, journal_path.name, record)
                            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                        if stage_stat is None or record["stage_inode_tuple"] != _restore_owned_inode(stage_stat):
                            self._restore_append_aborted(root_fd, journal_path.name, record)
                            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                        try:
                            self._restore_validate_record_tree(stage, record)
                        except RestoreError:
                            self._restore_append_aborted(root_fd, journal_path.name, record)
                            raise
                        _rename_noreplace(projects_fd, record["stage_name"], projects_fd, project_id)
                        _restore_fsync_directory(projects_fd)
                        target_stat = os.lstat(project_id, dir_fd=projects_fd)
                        identity = self._restore_validate_record_tree(target, record)
                        record = self._restore_record(
                            project_id=project_id,
                            nonce=record["nonce"],
                            sequence=record["sequence"] + 1,
                            phase="NEW_SWAPPED",
                            stage_name=record["stage_name"],
                            stage_inode=None,
                            target_inode=self._restore_inode(target_stat),
                            identity=identity,
                            database_fingerprint=record["database_fingerprint"],
                            blob_rows=record["blobs"],
                        )
                        journal_path = Path(
                            self._restore_publish_journal(root_fd, journal_path.name, record)
                        )
                        stage_stat = None
                    if record["phase"] == "COMMITTED":
                        if target_stat is None or stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISDIR(target_stat.st_mode):
                            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                        if record["target_inode_tuple"] != _restore_owned_inode(target_stat):
                            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                        identity = self._restore_validate_record_tree(target, record)
                        identity_bound = {key: identity[key] for key in ("project_id", "title", "language", "project_schema_version")}
                        if identity_bound != record["identity"]:
                            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                        row = self._restore_registry_row(conn, project_id)
                        if row is None or not self._restore_registry_matches(row, identity, target):
                            raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                        conn.rollback()
                        recovered.append(project_id)
                        continue
                    if target_stat is None or stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISDIR(target_stat.st_mode):
                        raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                    if record["target_inode_tuple"] != _restore_owned_inode(target_stat):
                        raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                    if stage_stat is not None:
                        raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                    identity = self._restore_validate_record_tree(target, record)
                    identity_bound = {key: identity[key] for key in ("project_id", "title", "language", "project_schema_version")}
                    if identity_bound != record["identity"]:
                        raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                    row = self._restore_registry_row(conn, project_id)
                    if row is None:
                        self._restore_insert_registry(conn, identity, target)
                        record = self._restore_record(
                            project_id=project_id,
                            nonce=record["nonce"],
                            sequence=record["sequence"] + 1,
                            phase="REGISTRY_UPSERTED",
                            stage_name=record["stage_name"],
                            stage_inode=None,
                            target_inode=self._restore_inode(target_stat),
                            identity=identity,
                            database_fingerprint=record["database_fingerprint"],
                            blob_rows=record["blobs"],
                        )
                        journal_path = Path(self._restore_publish_journal(root_fd, journal_path.name, record))
                    elif not self._restore_registry_matches(row, identity, target):
                        raise RestoreIncompleteError(_public_restore_error_message("restore_incomplete"), code="restore_incomplete")
                    conn.commit()
                    record = self._restore_record(
                        project_id=project_id,
                        nonce=record["nonce"],
                        sequence=record["sequence"] + 1,
                        phase="COMMITTED",
                        stage_name=record["stage_name"],
                        stage_inode=None,
                        target_inode=self._restore_inode(target_stat),
                        identity=identity,
                        database_fingerprint=record["database_fingerprint"],
                        blob_rows=record["blobs"],
                    )
                    self._restore_publish_journal(root_fd, journal_path.name, record)
                    recovered.append(project_id)
                except RestoreError:
                    if conn is not None and conn.in_transaction:
                        conn.rollback()
                    raise
                finally:
                    if conn is not None:
                        conn.close()
                    self._restore_close_lock(lock_fd)
            return recovered
        finally:
            os.close(projects_fd)
            os.close(root_fd)

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
                with self._connect(path) as conn:
                    if not self.read_only:
                        apply_schema(conn, scope)
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
            with self._connect(self.global_db) as conn:
                stale = [dict(r) for r in conn.execute("SELECT project_id,project_dir FROM project_registry") if not Path(r["project_dir"]).exists()]
                if fix:
                    for row in stale:
                        conn.execute("DELETE FROM project_registry WHERE project_id=?", (row["project_id"],))
                    conn.commit()
                checks.append({"check": "project_registry", "status": "ok" if not stale or fix else "warning", "stale": stale, "fixed": bool(stale and fix)})
        return {"schema": "quillframe_doctor_v1", "ok": not errors, "fix": fix, "data_root": str(self.root), "checks": checks, "errors": errors}
