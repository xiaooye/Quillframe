from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

import persistence.quillframe_sqlite as sqlite_module
from persistence.quillframe_sqlite import IntegrityError, QuillframeStore, fingerprint_bytes


class PersistenceC3ABundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = QuillframeStore(self.root)
        self.store.create_project("P1", "Project", "en")
        self.blob = self.store.put_blob("P1", b"C3A blob fixture", "text/plain")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _base_members(self) -> tuple[dict[str, bytes], dict[str, object]]:
        source = self.store.backup_project("P1")
        with zipfile.ZipFile(source) as archive:
            members = {info.filename: archive.read(info) for info in archive.infolist()}
        manifest = json.loads(members["manifest.json"])
        manifest["project_schema"] = "quillframe_project_v1_0"
        manifest["chapter_scope"] = "CH001"
        return members, manifest

    def _write_bundle(
        self,
        *,
        mutate_manifest=None,
        database_bytes: bytes | None = None,
        extra_members: dict[str, bytes] | None = None,
        extra_infos: list[zipfile.ZipInfo] | None = None,
        duplicate_name: str | None = None,
    ) -> Path:
        members, manifest = self._base_members()
        if database_bytes is not None:
            members["project.sqlite"] = database_bytes
            manifest["database_fingerprint"] = fingerprint_bytes(database_bytes)
        if mutate_manifest is not None:
            mutate_manifest(manifest)
        output = self.root / "fixture.qfbackup"
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(members):
                if name == "manifest.json":
                    archive.writestr(name, json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n")
                else:
                    archive.writestr(name, members[name])
            for name, payload in (extra_members or {}).items():
                archive.writestr(name, payload)
            for info in extra_infos or []:
                archive.writestr(info, b"member")
            if duplicate_name is not None:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr(duplicate_name, members[duplicate_name])
        return output

    def _mutated_database(self, mutate) -> bytes:
        members, _ = self._base_members()
        with tempfile.TemporaryDirectory() as td:
            database = Path(td) / "project.sqlite"
            database.write_bytes(members["project.sqlite"])
            conn = sqlite3.connect(database)
            try:
                conn.execute("PRAGMA journal_mode=DELETE")
                mutate(conn)
                conn.commit()
            finally:
                conn.close()
            return database.read_bytes()

    def _metadata_count(self) -> int:
        with self.store._connect(self.store.global_db) as conn:
            return conn.execute("SELECT COUNT(*) FROM backup_metadata").fetchone()[0]

    def test_backup_manifest_has_one_exact_native_shape(self) -> None:
        bundle = self.store.backup_project("P1")
        with zipfile.ZipFile(bundle) as archive:
            manifest = json.loads(archive.read("manifest.json"))
        self.assertEqual(
            set(manifest),
            {
                "schema",
                "project_schema",
                "chapter_scope",
                "backup_id",
                "project_id",
                "created_at",
                "database_fingerprint",
                "blobs",
            },
        )
        self.assertEqual(manifest["schema"], "quillframe_backup_bundle_v1")
        self.assertEqual(manifest["project_schema"], "quillframe_project_v1_0")
        self.assertEqual(manifest["chapter_scope"], "CH001")
        self.assertIsInstance(manifest["backup_id"], str)
        self.assertIsInstance(manifest["project_id"], str)
        self.assertTrue(manifest["created_at"].endswith("+00:00"))
        self.assertTrue(manifest["database_fingerprint"].startswith("sha256:"))
        self.assertEqual(set(manifest["blobs"][0]), {"fingerprint", "relative_path", "byte_size"})

    def test_verify_rejects_legacy_manifest_shape(self) -> None:
        bundle = self._write_bundle(mutate_manifest=lambda value: value.pop("project_schema"))
        result = self.store.verify_backup(bundle)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"]["code"], "bundle_schema")

    def test_verify_rejects_manifest_type_and_extra_key_drift(self) -> None:
        bundle = self._write_bundle(
            mutate_manifest=lambda value: value.update(
                {"unexpected": True, "blobs": [{**value["blobs"][0], "byte_size": True}]}
            )
        )
        result = self.store.verify_backup(bundle)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"]["code"], "bundle_schema")

    def test_verify_rejects_unknown_duplicate_and_path_members(self) -> None:
        cases = [
            (dict(extra_members={"extra.txt": b"unknown"}), "bundle_members"),
            (dict(duplicate_name="manifest.json"), "bundle_members"),
            (dict(extra_members={"../escape": b"outside"}), "bundle_path"),
            (dict(extra_members={"blobs\\escape": b"outside"}), "bundle_path"),
        ]
        for kwargs, code in cases:
            with self.subTest(kwargs=kwargs):
                result = self.store.verify_backup(self._write_bundle(**kwargs))
                self.assertFalse(result["valid"])
                self.assertEqual(result["error"]["code"], code)

    def test_verify_rejects_directory_symlink_and_file_dir_collision(self) -> None:
        symlink = zipfile.ZipInfo("link")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        for kwargs, code in (
            ({"extra_infos": [zipfile.ZipInfo("blobs/")]}, "bundle_path"),
            ({"extra_infos": [symlink]}, "bundle_path"),
            ({"extra_members": {"blobs": b"file"}}, "bundle_path"),
        ):
            with self.subTest(code=code):
                result = self.store.verify_backup(self._write_bundle(**kwargs))
                self.assertFalse(result["valid"])
                self.assertEqual(result["error"]["code"], code)

    def test_verify_rejects_blob_size_limit_before_payload_read(self) -> None:
        bundle = self._write_bundle(
            mutate_manifest=lambda value: value["blobs"][0].update({"byte_size": 10**9})
        )
        result = self.store.verify_backup(bundle)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"]["code"], "bundle_limit")

    def test_verify_rejects_database_schema_identity_and_blob_ref_drift(self) -> None:
        cases = [
            lambda conn: conn.execute("DROP INDEX document_revisions_doc_idx"),
            lambda conn: conn.execute("UPDATE project_identity SET project_id='P2' WHERE project_id='P1'"),
            lambda conn: conn.execute("UPDATE blob_refs SET byte_size=byte_size+1"),
        ]
        for mutate in cases:
            with self.subTest(mutate=mutate):
                result = self.store.verify_backup(self._write_bundle(database_bytes=self._mutated_database(mutate)))
                self.assertFalse(result["valid"])
                self.assertIn(result["error"]["code"], {"bundle_schema", "bundle_identity", "bundle_blob"})

    def test_verify_rejects_non_ch001_manifest(self) -> None:
        bundle = self._write_bundle(mutate_manifest=lambda value: value.update({"chapter_scope": "CH002"}))
        result = self.store.verify_backup(bundle)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"]["code"], "bundle_schema")

    def test_backup_rejects_source_blob_symlink_without_reading_external_file(self) -> None:
        location = self.store.location("P1")
        blob_path = location.directory / self.blob["relative_path"]
        external = self.root / "external-sentinel.bin"
        external.write_bytes(b"C3A blob fixture")
        blob_path.unlink()
        blob_path.symlink_to(external)
        before_metadata = self._metadata_count()
        before_bundles = sorted((self.root / "backups").glob("*.qfbackup"))
        with self.assertRaises(IntegrityError):
            self.store.backup_project("P1")
        self.assertEqual(external.read_bytes(), b"C3A blob fixture")
        self.assertEqual(self._metadata_count(), before_metadata)
        self.assertEqual(sorted((self.root / "backups").glob("*.qfbackup")), before_bundles)

    def test_backup_rejects_source_blob_size_mismatch_without_publish_or_metadata(self) -> None:
        location = self.store.location("P1")
        blob_path = location.directory / self.blob["relative_path"]
        with self.store.open_project("P1") as conn:
            conn.execute("UPDATE blob_refs SET byte_size=byte_size+1")
            conn.commit()
        before_metadata = self._metadata_count()
        before_bundles = sorted((self.root / "backups").glob("*.qfbackup"))
        with self.assertRaises(IntegrityError):
            self.store.backup_project("P1")
        self.assertTrue(blob_path.is_file())
        self.assertEqual(self._metadata_count(), before_metadata)
        self.assertEqual(sorted((self.root / "backups").glob("*.qfbackup")), before_bundles)

    def test_restore_rejects_malicious_bundle_before_layout_or_extractall(self) -> None:
        bundle = self._write_bundle(extra_members={"../escape": b"do not write"})
        restored_root = self.root / "restored"
        outside = self.root / "escape"
        with self.assertRaises(IntegrityError):
            QuillframeStore(restored_root).restore_project(bundle)
        self.assertFalse(restored_root.exists())
        self.assertFalse(outside.exists())

    def test_backup_rejects_symlink_destination_ancestor_without_external_write(self) -> None:
        for index, symlink_parent in enumerate(
            (self.root / "destination-link", self.root / "destination" / "nested-link")
        ):
            with self.subTest(symlink_parent=symlink_parent):
                outside = self.root / f"destination-outside-{index}"
                outside.mkdir()
                sentinel = outside / "sentinel.txt"
                sentinel.write_bytes(b"must remain untouched")
                if symlink_parent.name == "nested-link":
                    symlink_parent.parent.mkdir(parents=True, exist_ok=True)
                symlink_parent.symlink_to(outside, target_is_directory=True)
                destination = symlink_parent / "deeper" / "published.qfbackup"
                with self.assertRaises(IntegrityError) as raised:
                    self.store.backup_project("P1", destination)
                self.assertEqual(getattr(raised.exception, "code", None), "bundle_target_path")
                self.assertEqual(sentinel.read_bytes(), b"must remain untouched")
                self.assertFalse((outside / "deeper").exists())
                symlink_parent.unlink()

    def test_backup_creates_missing_destination_chain_as_real_directories(self) -> None:
        destination = self.root / "new" / "nested" / "published.qfbackup"
        bundle = self.store.backup_project("P1", destination)
        self.assertEqual(bundle, destination)
        self.assertTrue(bundle.is_file())
        self.assertTrue((destination.parent.parent).is_dir())
        self.assertFalse(destination.parent.is_symlink())

    def test_backup_rejects_source_blob_hardlink_without_touching_external_sentinel(self) -> None:
        location = self.store.location("P1")
        blob_path = location.directory / self.blob["relative_path"]
        external = self.root / "external-hardlink-sentinel.bin"
        external.hardlink_to(blob_path)
        before = external.read_bytes()
        with self.assertRaises(IntegrityError) as raised:
            self.store.backup_project("P1")
        self.assertEqual(getattr(raised.exception, "code", None), "bundle_path")
        self.assertEqual(external.read_bytes(), before)
        self.assertEqual(self._metadata_count(), 0)

    def test_backup_rejects_source_blob_rename_replacement_before_open(self) -> None:
        location = self.store.location("P1")
        blob_path = location.directory / self.blob["relative_path"]
        replacement = self.root / "replacement.bin"
        replacement.write_bytes(b"replacement content")
        sentinel = self.root / "external-sentinel.bin"
        sentinel.write_bytes(b"must remain untouched")
        original_open = sqlite_module.os.open
        replaced = False

        def replace_before_open(path, *args, **kwargs):
            nonlocal replaced
            if not replaced and Path(path) == blob_path:
                replaced = True
                os.replace(replacement, blob_path)
            return original_open(path, *args, **kwargs)

        with patch.object(sqlite_module.os, "open", side_effect=replace_before_open):
            with self.assertRaises(IntegrityError) as raised:
                self.store.backup_project("P1")
        self.assertTrue(replaced)
        self.assertEqual(getattr(raised.exception, "code", None), "bundle_path")
        self.assertEqual(sentinel.read_bytes(), b"must remain untouched")
        self.assertEqual(self._metadata_count(), 0)

    def test_verify_and_restore_redact_paths_from_public_bundle_errors(self) -> None:
        sentinel_name = "private-sentinel-name.qfbackup"
        malformed = self._write_bundle(extra_members={"/" + sentinel_name: b"bad"})
        verified = self.store.verify_backup(malformed)
        self.assertFalse(verified["valid"])
        self.assertEqual(verified["error"]["code"], "bundle_path")
        self.assertEqual(verified["error"]["message"], "backup bundle path is not allowed")
        self.assertNotIn(sentinel_name, verified["error"]["message"])
        restored_root = self.root / "restored-public-errors"
        with self.assertRaises(IntegrityError) as raised:
            QuillframeStore(restored_root).restore_project(malformed)
        self.assertEqual(getattr(raised.exception, "code", None), "bundle_path")
        self.assertEqual(str(raised.exception), "backup bundle path is not allowed")
        self.assertNotIn(sentinel_name, str(raised.exception))
        self.assertNotIn(str(self.root), str(raised.exception))

    def test_backup_target_created_after_check_is_never_clobbered(self) -> None:
        destination = self.root / "race" / "published.qfbackup"
        competitor = b"competitor owns this target"
        original_linkat = sqlite_module._linkat_empty_path
        injected = False

        def create_competitor_before_linkat(source_fd, parent_fd, target_name):
            nonlocal injected
            if not injected:
                injected = True
                destination.write_bytes(competitor)
            return original_linkat(source_fd, parent_fd, target_name)

        with patch.object(sqlite_module, "_linkat_empty_path", side_effect=create_competitor_before_linkat):
            with self.assertRaises(IntegrityError) as raised:
                self.store.backup_project("P1", destination)
        self.assertTrue(injected)
        self.assertEqual(getattr(raised.exception, "code", None), "backup_target_exists")
        self.assertEqual(destination.read_bytes(), competitor)
        self.assertEqual(list(destination.parent.glob(".quillframe-backup-*")), [])
        self.assertEqual(self._metadata_count(), 0)

    def test_metadata_failure_cleanup_preserves_competitor_replacement(self) -> None:
        destination = self.root / "metadata-race" / "published.qfbackup"
        competitor = b"replacement competitor owns this target"

        def fail_after_competitor_replaces_target(*args, **kwargs):
            destination.unlink()
            destination.write_bytes(competitor)
            raise RuntimeError("injected metadata failure")

        with patch.object(
            self.store,
            "_record_backup_metadata",
            side_effect=fail_after_competitor_replaces_target,
        ):
            with self.assertRaises(IntegrityError) as raised:
                self.store.backup_project("P1", destination)
        self.assertIsInstance(raised.exception, sqlite_module.BackupPublishError)
        self.assertEqual(getattr(raised.exception, "code", None), "backup_metadata")
        self.assertEqual(
            str(raised.exception),
            "backup metadata recording failed; published bundle retained",
        )
        self.assertEqual(destination.read_bytes(), competitor)
        self.assertEqual(self._metadata_count(), 0)

    def test_metadata_failure_retains_valid_bundle_without_target_unlink(self) -> None:
        destination = self.root / "metadata-failure" / "published.qfbackup"
        original_unlink = sqlite_module.os.unlink
        target_unlinks: list[str] = []

        def monitor_unlink(path, *args, **kwargs):
            if path == destination.name:
                target_unlinks.append(path)
            return original_unlink(path, *args, **kwargs)

        with patch.object(
            self.store,
            "_record_backup_metadata",
            side_effect=RuntimeError("injected metadata failure"),
        ):
            with patch.object(sqlite_module.os, "unlink", side_effect=monitor_unlink):
                with self.assertRaises(sqlite_module.BackupPublishError) as raised:
                    self.store.backup_project("P1", destination)
        self.assertEqual(getattr(raised.exception, "code", None), "backup_metadata")
        self.assertEqual(
            str(raised.exception),
            "backup metadata recording failed; published bundle retained",
        )
        self.assertEqual(target_unlinks, [])
        self.assertTrue(destination.is_file())
        self.assertTrue(self.store.verify_backup(destination)["valid"])
        self.assertEqual(self._metadata_count(), 0)

    def test_backup_publish_uses_unnamed_inode_without_temp_unlink(self) -> None:
        destination = self.root / "anonymous" / "published.qfbackup"
        original_open = sqlite_module.os.open
        original_unlink = sqlite_module.os.unlink
        tmpfile_flags = getattr(os, "O_TMPFILE", 0)
        opened_flags: list[int] = []
        unlink_calls: list[object] = []

        def monitor_open(path, flags, *args, **kwargs):
            if kwargs.get("dir_fd") is not None:
                opened_flags.append(flags)
            return original_open(path, flags, *args, **kwargs)

        def monitor_unlink(path, *args, **kwargs):
            unlink_calls.append(path)
            return original_unlink(path, *args, **kwargs)

        with patch.object(sqlite_module.os, "open", side_effect=monitor_open):
            with patch.object(sqlite_module.os, "unlink", side_effect=monitor_unlink):
                bundle = self.store.backup_project("P1", destination)
        self.assertTrue(tmpfile_flags)
        self.assertTrue(any((flags & tmpfile_flags) == tmpfile_flags for flags in opened_flags))
        self.assertFalse(any(str(path).startswith(".quillframe-backup-") for path in unlink_calls))
        self.assertEqual(list(destination.parent.glob(".quillframe-backup-*")), [])
        self.assertTrue(self.store.verify_backup(bundle)["valid"])

    def test_backup_unnamed_fd_closes_on_metadata_failure(self) -> None:
        destination = self.root / "anonymous-failure" / "published.qfbackup"
        original_open = sqlite_module.os.open
        unnamed_fd: int | None = None
        tmpfile_flags = getattr(os, "O_TMPFILE", 0)

        def capture_unnamed_open(path, flags, *args, **kwargs):
            nonlocal unnamed_fd
            fd = original_open(path, flags, *args, **kwargs)
            if tmpfile_flags and (flags & tmpfile_flags) == tmpfile_flags:
                unnamed_fd = fd
            return fd

        with patch.object(sqlite_module.os, "open", side_effect=capture_unnamed_open):
            with patch.object(
                self.store,
                "_record_backup_metadata",
                side_effect=RuntimeError("injected metadata failure"),
            ):
                with self.assertRaises(sqlite_module.BackupPublishError):
                    self.store.backup_project("P1", destination)
        self.assertIsNotNone(unnamed_fd)
        with self.assertRaises(OSError):
            os.fstat(unnamed_fd)
        self.assertTrue(destination.is_file())
        self.assertTrue(self.store.verify_backup(destination)["valid"])

    def test_backup_fails_closed_when_unnamed_native_support_is_unavailable(self) -> None:
        destination = self.root / "anonymous-unavailable" / "published.qfbackup"
        with patch.object(sqlite_module.os, "O_TMPFILE", 0):
            with self.assertRaises(sqlite_module.BackupPublishError) as raised:
                self.store.backup_project("P1", destination)
        self.assertEqual(getattr(raised.exception, "code", None), "backup_native_unavailable")
        self.assertEqual(
            str(raised.exception),
            "native unnamed backup publication is unavailable",
        )
        self.assertFalse(destination.exists())
        self.assertEqual(self._metadata_count(), 0)


if __name__ == "__main__":
    unittest.main()
