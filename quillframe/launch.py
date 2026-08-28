"""Canonical all-in-one launch flow for Quillframe 1.0."""
from __future__ import annotations

import argparse
import json
import hashlib
import os
import sqlite3
import stat
import sys
import tempfile
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from persistence.quillframe_sqlite import (
    ProjectIdentityMismatchError,
    ProjectStateError,
    QuillframeStore,
    now_iso,
)
from project_resolution import resolve_contract, validate_project_id
from studio.local_server import DEFAULT_DIST, StudioServer, create_server


PROJECT_SCHEMA = "quillframe_project_v1_0"
LAUNCH_SCHEMA = "quillframe_launch_receipt_v1"
PROJECT_SCOPE = "novel"
NEW_RESERVATION_NAME = ".quillframe-new.lock"
_FileToken = tuple[int, int, int]


class LaunchError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class _Reservation:
    path: Path
    token: _FileToken
    fd: int | None
    root: Path
    root_token: _FileToken
    created_root: bool


@dataclass(frozen=True)
class _DatabaseGuard:
    path: Path
    fd: int
    token: _FileToken


@dataclass(frozen=True)
class _ManifestGuard:
    path: Path
    fd: int
    token: _FileToken
    fingerprint: str


@dataclass(frozen=True)
class _CreatedProject:
    root: Path
    context: dict[str, Any]
    manifest_path: Path
    manifest_token: _FileToken
    reservation: _Reservation
    manifest_fingerprint: str
    baseline_paths: frozenset[Path]
    owned_artifacts: dict[Path, _FileToken]


def _text(value: str | None, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LaunchError("invalid_launch_args", f"{field} is required")
    return value.strip()


def _project_id(value: str | None) -> str:
    if not isinstance(value, str) or not value:
        raise LaunchError("invalid_launch_args", "project_id is required")
    try:
        return validate_project_id(value)
    except ValueError as exc:
        raise LaunchError("invalid_launch_args", str(exc)) from exc


def _file_token_from_stat(value: os.stat_result) -> _FileToken:
    return (int(value.st_dev), int(value.st_ino), int(stat.S_IFMT(value.st_mode)))


def _lstat_token(path: Path) -> _FileToken:
    return _file_token_from_stat(os.lstat(path))


def _fstat_token(fd: int) -> _FileToken:
    return _file_token_from_stat(os.fstat(fd))


def _fingerprint_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _path_has_token(path: Path, token: _FileToken) -> bool:
    try:
        return _lstat_token(path) == token
    except OSError:
        return False


def _unlink_owned(path: Path, token: _FileToken) -> bool:
    """Unlink only when the destination still names our exact inode."""
    if not _path_has_token(path, token):
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False


def _unlink_owned_file(path: Path, token: _FileToken, fingerprint: str | None = None) -> bool:
    """Unlink our inode only when optional bytes identity also remains ours."""
    if not _path_has_token(path, token):
        return False
    if fingerprint is not None:
        try:
            if _fingerprint_bytes(path.read_bytes()) != fingerprint:
                return False
        except OSError:
            return False
    return _unlink_owned(path, token)


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short write while publishing Project state")
        view = view[written:]


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _remove_empty_created_root(reservation: _Reservation) -> None:
    if not reservation.created_root or not _path_has_token(reservation.root, reservation.root_token):
        return
    try:
        if not any(reservation.root.iterdir()):
            reservation.root.rmdir()
    except OSError:
        return


def _release_reservation(reservation: _Reservation) -> None:
    try:
        if _reservation_owns_current_path(reservation):
            _unlink_owned(reservation.path, reservation.token)
    finally:
        if reservation.fd is not None:
            try:
                os.close(reservation.fd)
            except OSError:
                pass


def _reservation_owns_current_path(reservation: _Reservation) -> bool:
    """Bind the reservation path to the still-open inode, including unlink state."""
    if reservation.fd is None:
        return False
    try:
        descriptor = os.fstat(reservation.fd)
    except OSError:
        return False
    return (
        descriptor.st_nlink > 0
        and _file_token_from_stat(descriptor) == reservation.token
        and _path_has_token(reservation.path, reservation.token)
    )


def _reserve_new_target(root: Path) -> _Reservation:
    """Atomically reserve a new target and retain the reservation inode token."""
    root.parent.mkdir(parents=True, exist_ok=True)
    created_root = False
    try:
        root.mkdir()
        created_root = True
    except FileExistsError:
        try:
            root_stat = os.lstat(root)
        except OSError as exc:
            raise LaunchError("project_directory_not_empty", f"unable to inspect {root}") from exc
        if not stat.S_ISDIR(root_stat.st_mode) or any(root.iterdir()):
            raise LaunchError("project_directory_not_empty", f"{root} must be absent or genuinely empty for --new")
    root_token = _lstat_token(root)

    lock_path = root / NEW_RESERVATION_NAME
    fd: int | None = None
    lock_token: _FileToken | None = None
    try:
        try:
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_CLOEXEC", 0)
            fd = os.open(lock_path, flags, 0o600)
            lock_token = _fstat_token(fd)
        except FileExistsError as exc:
            raise LaunchError("project_directory_not_empty", f"{root} is already reserved for --new") from exc
        _write_all(fd, f"pid={os.getpid()}\n".encode("ascii"))
        os.fsync(fd)
    except Exception:
        if lock_token is not None:
            failed = _Reservation(lock_path, lock_token, fd, root, root_token, created_root)
            _release_reservation(failed)
            fd = None
            _remove_empty_created_root(failed)
        elif fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            fd = None
        if lock_token is None and created_root and _path_has_token(root, root_token):
            try:
                if not any(root.iterdir()):
                    root.rmdir()
            except OSError:
                pass
        raise
    assert lock_token is not None
    assert fd is not None
    return _Reservation(lock_path, lock_token, fd, root, root_token, created_root)


def _write_new_manifest(path: Path, content: str) -> _FileToken:
    """Publish a manifest exactly once and return its published inode token."""
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{threading.get_ident()}")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(temporary, flags, 0o600)
    published_token: _FileToken | None = None
    try:
        _write_all(fd, content.encode("utf-8"))
        os.fsync(fd)
        published_token = _fstat_token(fd)
        os.close(fd)
        fd = -1
        # Hard-link publication is atomic and fails if the destination exists;
        # unlike os.replace it cannot overwrite a competing manifest.
        os.link(temporary, path)
        return published_token
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            temporary.unlink()
        except OSError:
            pass


def _launch_state_path() -> Path:
    configured = os.environ.get("QUILLFRAME_LAUNCH_STATE")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".quillframe" / "launch-state.json").resolve()


def _last_project() -> Path | None:
    try:
        value = json.loads(_launch_state_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if value.get("schema") != "quillframe_launch_state_v1":
        return None
    path = value.get("last_project_root")
    if not isinstance(path, str) or not path:
        return None
    root = Path(path).expanduser().resolve()
    return root if (root / "quillframe.toml").is_file() else None


def _record_last_project(root: Path) -> None:
    try:
        _atomic_write(
            _launch_state_path(),
            json.dumps(
                {
                    "schema": "quillframe_launch_state_v1",
                    "last_project_root": str(root),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
        )
    except OSError:
        # A read-only host profile must not prevent an explicitly resolved local launch.
        return


def resolve_project_root(start: Path) -> Path | None:
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "quillframe.toml").is_file():
            return candidate
    return None


def _resolve_context(root: Path) -> dict[str, Any]:
    try:
        return resolve_contract(root)
    except ValueError as exc:
        message = str(exc)
        if "missing quillframe.toml" in message:
            code = "project_resolution_required"
        elif "chapter_scope" in message:
            code = "chapter_scope_violation"
        elif "schema" in message:
            code = "project_schema_rejected"
        elif "legacy metadata" in message:
            code = "project_legacy_metadata_rejected"
        else:
            code = "project_manifest_invalid"
        raise LaunchError(code, message) from exc


def _manifest(root: Path) -> dict[str, Any]:
    return _resolve_context(root)["manifest"]


def _assert_context_current(root: Path, expected: dict[str, Any]) -> dict[str, Any]:
    current = _resolve_context(root)
    if current != expected:
        raise LaunchError(
            "project_manifest_changed",
            "Project manifest context changed during launch",
        )
    return current


def _open_manifest_guard(root: Path, expected_fingerprint: str | None = None) -> _ManifestGuard:
    path = root / "quillframe.toml"
    close_on_exec = getattr(os, "O_CLOEXEC", 0)
    flags = os.O_RDONLY | (close_on_exec if isinstance(close_on_exec, int) else 0)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is not None:
        flags |= nofollow
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise LaunchError("project_manifest_changed", "unable to hold Project manifest descriptor") from exc
    try:
        token = _fstat_token(fd)
        if not stat.S_ISREG(os.fstat(fd).st_mode) or not _path_has_token(path, token):
            raise LaunchError("project_manifest_changed", "Project manifest changed during guarded open")
        payload = os.pread(fd, os.fstat(fd).st_size, 0)
        raw_fingerprint = _fingerprint_bytes(payload)
        if expected_fingerprint is not None and raw_fingerprint != expected_fingerprint:
            raise LaunchError("project_manifest_changed", "Project manifest changed during guarded open")
        return _ManifestGuard(path, fd, token, raw_fingerprint)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _assert_manifest_guard_current(guard: _ManifestGuard) -> None:
    try:
        if _fstat_token(guard.fd) != guard.token or not _path_has_token(guard.path, guard.token):
            raise LaunchError("project_manifest_changed", "Project manifest changed during launch")
        payload = os.pread(guard.fd, os.fstat(guard.fd).st_size, 0)
    except LaunchError:
        raise
    except OSError as exc:
        raise LaunchError("project_manifest_changed", "Project manifest guard is no longer valid") from exc
    if _fingerprint_bytes(payload) != guard.fingerprint:
        raise LaunchError("project_manifest_changed", "Project manifest changed during launch")


def _cleanup_created_project(created: _CreatedProject, *, remove_manifest: bool) -> None:
    if remove_manifest:
        _unlink_owned_file(created.manifest_path, created.manifest_token, created.manifest_fingerprint)
        for path, token in sorted(created.owned_artifacts.items(), key=lambda item: len(item[0].parts), reverse=True):
            if path.is_dir() and not path.is_symlink():
                if _path_has_token(path, token):
                    try:
                        path.rmdir()
                    except OSError:
                        pass
            else:
                _unlink_owned(path, token)
    _release_reservation(created.reservation)
    if remove_manifest:
        _remove_empty_created_root(created.reservation)


def _core_artifact_paths(root: Path, project_id: str) -> set[Path]:
    data = root / ".quillframe" / "data"
    project = data / "projects" / project_id
    return {
        root / ".quillframe",
        data,
        data / "quillframe.sqlite",
        data / "quillframe.sqlite-wal",
        data / "quillframe.sqlite-shm",
        data / "quillframe.sqlite-journal",
        data / "projects",
        data / "backups",
        data / "cache",
        project,
        project / "project.sqlite",
        project / "project.sqlite-wal",
        project / "project.sqlite-shm",
        project / "project.sqlite-journal",
        project / "blobs",
        project / "exports",
    }


def _record_owned_core_artifacts(root: Path, project_id: str, created: _CreatedProject) -> None:
    candidates = _core_artifact_paths(root, project_id)
    for path in candidates:
        if path in created.baseline_paths or path in created.owned_artifacts:
            continue
        try:
            token = _lstat_token(path)
        except FileNotFoundError:
            continue
        except OSError:
            continue
        created.owned_artifacts[path] = token


def _create_project(root: Path, *, project_id: str, title: str, language: str) -> _CreatedProject:
    project_id = _project_id(project_id)
    title = _text(title, "title")
    language = _text(language, "language")
    reservation = _reserve_new_target(root)
    manifest_path = root / "quillframe.toml"
    manifest = {
        "schema": PROJECT_SCHEMA,
        "id": project_id,
        "title": title,
        "language": language,
    }
    toml = (
        f"schema = {json.dumps(manifest['schema'])}\n"
        f"id = {json.dumps(manifest['id'], ensure_ascii=False)}\n"
        f"title = {json.dumps(manifest['title'], ensure_ascii=False)}\n"
        f"language = {json.dumps(manifest['language'], ensure_ascii=False)}\n"
    )
    manifest_token: _FileToken | None = None
    try:
        manifest_token = _write_new_manifest(manifest_path, toml)
        _assert_reservation_current(reservation)
        # The generated artifact must cross the same canonical parser boundary
        # before any local core/database initialization is allowed.
        context = _resolve_context(root)
        _assert_reservation_current(reservation)
        baseline_paths = frozenset(root.rglob("*"))
        return _CreatedProject(
            root,
            context,
            manifest_path,
            manifest_token,
            reservation,
            _fingerprint_bytes(toml.encode("utf-8")),
            baseline_paths,
            {},
        )
    except Exception:
        if manifest_token is not None:
            _unlink_owned_file(manifest_path, manifest_token, _fingerprint_bytes(toml.encode("utf-8")))
        _release_reservation(reservation)
        _remove_empty_created_root(reservation)
        raise


def _assert_safe_project_database_path(data: Path, database: Path) -> _FileToken | None:
    """Reject symlinked or escaping Project SQLite paths before opening them."""
    try:
        canonical_data = data.resolve(strict=False)
        project_root = data.parent.parent
        cursor = project_root
        for component in (*data.relative_to(project_root).parts, *database.relative_to(data).parts):
            cursor = cursor / component
            if cursor.is_symlink():
                raise LaunchError(
                    "project_state_path_invalid",
                    f"Project state path may not contain symlinks: {cursor}",
                )
        resolved_database = database.resolve(strict=False)
    except LaunchError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise LaunchError("project_state_path_invalid", f"invalid Project state path: {exc}") from exc
    if resolved_database != canonical_data and canonical_data not in resolved_database.parents:
        raise LaunchError(
            "project_state_path_invalid",
            f"Project database escapes the canonical data root: {database}",
        )
    try:
        database_stat = os.lstat(database)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LaunchError("project_state_path_invalid", f"unable to inspect Project database: {exc}") from exc
    if not stat.S_ISREG(database_stat.st_mode):
        raise LaunchError("project_state_path_invalid", "Project database must be a regular file")
    return _file_token_from_stat(database_stat)


def _open_database_guard(database: Path, expected_token: _FileToken | None) -> _DatabaseGuard | None:
    required = getattr(os, "O_NOFOLLOW", None)
    close_on_exec = getattr(os, "O_CLOEXEC", None)
    if (
        not isinstance(required, int)
        or required == 0
        or not isinstance(close_on_exec, int)
        or close_on_exec == 0
        or not Path("/proc/self/fd").is_dir()
    ):
        try:
            current_token = _lstat_token(database)
        except FileNotFoundError:
            current_token = None
        except OSError as exc:
            raise LaunchError("project_state_path_invalid", f"unable to inspect Project database: {exc}") from exc
        if expected_token is None and current_token is None:
            return None
        raise LaunchError(
            "project_state_path_invalid",
            "existing Project state requires descriptor-bound SQLite support",
        )
    flags = os.O_RDWR | required | close_on_exec
    try:
        fd = os.open(database, flags)
    except FileNotFoundError as exc:
        if expected_token is not None:
            raise LaunchError("project_state_path_invalid", "Project database changed before guarded open") from exc
        return None
    except OSError as exc:
        raise LaunchError("project_state_path_invalid", f"unable to guard Project database: {exc}") from exc
    try:
        token = _fstat_token(fd)
        if (
            not stat.S_ISREG(os.fstat(fd).st_mode)
            or expected_token is None
            or token != expected_token
            or not _path_has_token(database, token)
        ):
            raise LaunchError("project_state_path_invalid", "Project database changed during guarded open")
        return _DatabaseGuard(database, fd, token)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _assert_database_guard_current(data: Path, guard: _DatabaseGuard) -> None:
    _assert_safe_project_database_path(data, guard.path)
    try:
        fd_token = _fstat_token(guard.fd)
    except OSError as exc:
        raise LaunchError("project_state_path_invalid", "Project database guard is no longer valid") from exc
    if fd_token != guard.token or not _path_has_token(guard.path, guard.token):
        raise LaunchError("project_state_path_invalid", "Project database changed during launch")


def _assert_reservation_current(reservation: _Reservation | None) -> None:
    if reservation is not None and not _reservation_owns_current_path(reservation):
        raise LaunchError("project_reservation_lost", "Project creation reservation changed during launch")


def _before_ensure_local_core(root: Path, context: dict[str, Any]) -> None:
    """Test seam between manifest parse and local-core initialization."""
    return None


def _after_existing_identity_check(conn: sqlite3.Connection) -> None:
    """Test seam executed while the strict existing-state write lock is held."""
    return None


def _before_existing_commit(conn: sqlite3.Connection) -> None:
    """Test seam immediately before the strict existing-state commit."""
    return None


def _before_new_commit(conn: sqlite3.Connection) -> None:
    """Test seam immediately before the strict new-state commit."""
    return None


def _validate_existing_project_identity(
    data: Path, manifest: dict[str, Any], guard: _DatabaseGuard
) -> sqlite3.Connection:
    """Open an existing Project in one identity-checked write transaction."""
    try:
        return QuillframeStore(data).open_existing_project_strict(
            manifest["id"], manifest["title"], manifest["language"], database_fd=guard.fd
        )
    except ProjectIdentityMismatchError as exc:
        raise LaunchError("project_state_identity_mismatch", str(exc)) from exc
    except (ProjectStateError, FileNotFoundError, OSError, sqlite3.DatabaseError) as exc:
        raise LaunchError("project_state_invalid", f"unable to read current Project state: {exc}") from exc


def _assert_native_novel(conn: sqlite3.Connection) -> None:
    try:
        QuillframeStore.assert_native_project(conn)
    except ProjectStateError as exc:
        raise LaunchError("project_state_invalid", str(exc)) from exc


def _ensure_local_core(
    root: Path,
    context: dict[str, Any],
    *,
    reservation: _Reservation | None = None,
    created: _CreatedProject | None = None,
    manifest_guard: _ManifestGuard | None = None,
) -> Path:
    _assert_context_current(root, context)
    if manifest_guard is not None:
        _assert_manifest_guard_current(manifest_guard)
    manifest = context["manifest"]
    # Keep the lexical boundary for symlink checks; the resolver's canonical
    # data_root alone would hide an in-root symlink before lstat inspection.
    data = root / ".quillframe" / "data"
    store = QuillframeStore(data)
    location = store.location(manifest["id"])
    expected_token = _assert_safe_project_database_path(data, location.database)
    _assert_reservation_current(reservation)
    guard = _open_database_guard(location.database, expected_token)
    if guard is not None:
        try:
            # Re-check parent symlinks and the destination token after the
            # descriptor is acquired, before SQLite is allowed to inspect it.
            _assert_database_guard_current(data, guard)
            conn = _validate_existing_project_identity(data, manifest, guard)
        except Exception:
            try:
                os.close(guard.fd)
            except OSError:
                pass
            raise
        try:
            _assert_context_current(root, context)
            _assert_database_guard_current(data, guard)
            _after_existing_identity_check(conn)
            _assert_context_current(root, context)
            _assert_database_guard_current(data, guard)
            try:
                store.assert_existing_project_identity(
                    conn, manifest["id"], manifest["title"], manifest["language"]
                )
            except ProjectIdentityMismatchError as exc:
                raise LaunchError("project_state_identity_mismatch", str(exc)) from exc
            except ProjectStateError as exc:
                raise LaunchError("project_state_invalid", str(exc)) from exc
            _assert_native_novel(conn)
            _assert_context_current(root, context)
            _assert_database_guard_current(data, guard)
            if manifest_guard is not None:
                _assert_manifest_guard_current(manifest_guard)
            _before_existing_commit(conn)
            conn.commit()
            if manifest_guard is not None:
                _assert_manifest_guard_current(manifest_guard)
            _assert_context_current(root, context)
        except LaunchError:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise LaunchError("project_state_invalid", f"unable to update current Project state: {exc}") from exc
        finally:
            conn.close()
            try:
                os.close(guard.fd)
            except OSError:
                pass
    else:
        _assert_context_current(root, context)
        if manifest_guard is not None:
            _assert_manifest_guard_current(manifest_guard)
        _assert_reservation_current(reservation)
        try:
            def before_commit(conn: sqlite3.Connection) -> None:
                _assert_context_current(root, context)
                if manifest_guard is not None:
                    _assert_manifest_guard_current(manifest_guard)
                _assert_reservation_current(reservation)
                _before_new_commit(conn)
                _assert_reservation_current(reservation)
                if manifest_guard is not None:
                    _assert_manifest_guard_current(manifest_guard)
                _assert_context_current(root, context)

            try:
                store.create_native_project(
                    manifest["id"], manifest["title"], manifest["language"],
                    before_commit=before_commit,
                )
            finally:
                if created is not None:
                    _record_owned_core_artifacts(root, manifest["id"], created)
            _assert_reservation_current(reservation)
            if manifest_guard is not None:
                _assert_manifest_guard_current(manifest_guard)
            _assert_context_current(root, context)
        except LaunchError:
            raise
        except Exception as exc:
            raise LaunchError("project_state_invalid", f"unable to initialize current Project state: {exc}") from exc
    return data


@dataclass
class LaunchedProduct:
    receipt: dict[str, Any]
    server: StudioServer | None
    _previous_data_dir: str | None

    def serve_forever(self) -> None:
        if self.server is None:
            return
        try:
            self.server.serve_forever(poll_interval=0.5)
        finally:
            self.close()

    def close(self) -> None:
        if self.server is not None:
            self.server.server_close()
            self.server = None
        if self._previous_data_dir is None:
            os.environ.pop("QUILLFRAME_DATA_DIR", None)
        else:
            os.environ["QUILLFRAME_DATA_DIR"] = self._previous_data_dir


def launch_project(
    *,
    project: Path | None,
    new: bool,
    profile: str,
    project_id: str | None,
    title: str | None,
    language: str,
    port: int,
    no_browser: bool,
    dist: Path | None = None,
    serve: bool = True,
    interactive: bool | None = None,
) -> LaunchedProduct:
    if profile not in {"local", "cloud"}:
        raise LaunchError("invalid_launch_args", "profile must be local|cloud")
    if not isinstance(port, int) or port < 0 or port > 65535:
        raise LaunchError("invalid_launch_args", "port must be 0..65535")
    interactive = os.isatty(0) if interactive is None else interactive
    start = (project or Path.cwd()).expanduser().resolve()
    previous_data_dir = os.environ.get("QUILLFRAME_DATA_DIR")
    server: StudioServer | None = None
    browser_opened = False
    created: _CreatedProject | None = None
    core_initialized = False
    manifest_guard: _ManifestGuard | None = None
    try:
        if new:
            requested_id = _project_id(project_id)
            root = start if project is not None else start / requested_id
            created = _create_project(
                root,
                project_id=requested_id,
                title=_text(title, "title"),
                language=_text(language, "language"),
            )
            context = created.context
        else:
            root = resolve_project_root(start)
            if root is None and project is None:
                root = _last_project()
            if root is None:
                if interactive:
                    wizard_id = _project_id(input("Project ID: ").strip())
                    wizard_title = _text(input("Title: ").strip(), "title")
                    wizard_language = input(f"Language [{language}]: ").strip() or language
                    root = Path.cwd().resolve() / wizard_id
                    created = _create_project(
                        root,
                        project_id=wizard_id,
                        title=wizard_title,
                        language=wizard_language,
                    )
                    context = created.context
                else:
                    raise LaunchError(
                        "project_resolution_required",
                        "no current or last Quillframe 1.0 project; pass PROJECT or --new --id --title",
                    )
            else:
                context = _resolve_context(root)

        manifest_guard = _open_manifest_guard(root, context.get("manifest_raw_fingerprint"))
        _assert_context_current(root, context)
        _before_ensure_local_core(root, context)
        data = _ensure_local_core(
            root,
            context,
            reservation=created.reservation if created is not None else None,
            created=created,
            manifest_guard=manifest_guard,
        )
        core_initialized = True
        os.environ["QUILLFRAME_DATA_DIR"] = str(data)
        manifest = context["manifest"]
        if profile == "local":
            app_dist = (dist or DEFAULT_DIST).expanduser().resolve()
            server = create_server(app_dist, port=port)
            url = f"http://127.0.0.1:{server.server_port}/"
            status = "ready"
            storage_boundary = "project_local_sqlite"
        else:
            url = (
                "https://studio.quillframe.wei-dev.com/auth/start"
                f"?project={quote(manifest['id'])}"
            )
            status = "awaiting_authentication"
            storage_boundary = "encrypted_cloud_bundle"
        if not no_browser and serve:
            browser_opened = bool(webbrowser.open(url, new=1, autoraise=True))
        receipt = {
            "schema": LAUNCH_SCHEMA,
            "status": status,
            "profile": profile,
            "project_id": manifest["id"],
            "project_root": str(root),
            "url": url,
            "process_id": os.getpid(),
            "storage_boundary": storage_boundary,
            "browser_opened": browser_opened,
            "cloud_upload_started": False,
            "authority": False,
        }
        _record_last_project(root)
        return LaunchedProduct(receipt=receipt, server=server, _previous_data_dir=previous_data_dir)
    except Exception:
        if server is not None:
            server.server_close()
        if previous_data_dir is None:
            os.environ.pop("QUILLFRAME_DATA_DIR", None)
        else:
            os.environ["QUILLFRAME_DATA_DIR"] = previous_data_dir
        raise
    finally:
        if manifest_guard is not None:
            try:
                os.close(manifest_guard.fd)
            except OSError:
                pass
        if created is not None:
            _cleanup_created_project(created, remove_manifest=not core_initialized)


def self_test() -> dict[str, Any]:
    """Exercise the native creation/parser boundary without opening SQLite."""
    with tempfile.TemporaryDirectory(prefix="quillframe-launch-self-test-") as temporary:
        root = Path(temporary) / "project"
        created = _create_project(root, project_id="PROJECT-LAUNCH-SELFTEST", title="Launch fixture", language="en")
        try:
            context = created.context
            legacy = root / "quillframe.lock.json"
            legacy.write_text("{}\n", encoding="utf-8")
            legacy_rejected = False
            try:
                _resolve_context(root)
            except LaunchError as exc:
                legacy_rejected = exc.code == "project_legacy_metadata_rejected"
            legacy.unlink()
            checks = {
                "native_context": context["context_schema"] == "quillframe_project_context_v1_0",
                "exact_four_key_manifest": set(context["manifest"]) == {"schema", "id", "title", "language"},
                "project_schema": context["manifest"]["schema"] == PROJECT_SCHEMA,
                "scope": context["scope"] == PROJECT_SCOPE,
                "data_boundary": context["data_root"].endswith("/.quillframe/data"),
                "legacy_metadata_rejected": legacy_rejected,
                "no_lock_created": not (root / "quillframe.lock.json").exists(),
                "no_attestation_created": not (root / "framework.attestation.json").exists(),
            }
            return {
                "launch_contract": "PASS" if all(checks.values()) else "FAIL",
                "checks": checks,
                "project_schema": PROJECT_SCHEMA,
                "scope": PROJECT_SCOPE,
                "context_schema": context["context_schema"],
            }
        finally:
            _cleanup_created_project(created, remove_manifest=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe native Project launch contract")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["launch_contract"] == "PASS" else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
