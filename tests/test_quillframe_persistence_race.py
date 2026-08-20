import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import persistence.quillframe_sqlite as q


GOOD = b"GOOD"
EVIL = b"EVIL"


def _overwrite_same_inode(path: Path) -> None:
    with path.open("r+b") as handle:
        handle.seek(0)
        handle.write(EVIL)
        handle.flush()
        os.fsync(handle.fileno())


class PersistenceOverwriteRaceTests(unittest.TestCase):
    def test_read_regular_rejects_same_inode_same_size_overwrite_after_read(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "source"
            path.write_bytes(GOOD)
            real_fstat = os.fstat
            calls = 0

            def hooked_fstat(fd: int):
                nonlocal calls
                result = real_fstat(fd)
                calls += 1
                if calls == 2:
                    _overwrite_same_inode(path)
                return result

            with mock.patch.object(q.os, "fstat", side_effect=hooked_fstat):
                with self.assertRaises(q.BundlePathError):
                    q._read_regular_nofollow(path, limit=64, label="source")
            self.assertEqual(path.read_bytes(), EVIL)

    def test_read_blob_entry_rejects_same_inode_same_size_overwrite_after_read(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fingerprint = q.fingerprint_bytes(GOOD)
            name = fingerprint.split(":", 1)[1][2:]
            path = root / name
            path.write_bytes(GOOD)
            directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            real_fstat = os.fstat
            calls = 0
            try:
                def hooked_fstat(fd: int):
                    nonlocal calls
                    result = real_fstat(fd)
                    calls += 1
                    if calls == 2:
                        _overwrite_same_inode(path)
                    return result

                with mock.patch.object(q.os, "fstat", side_effect=hooked_fstat):
                    with self.assertRaises(q.IntegrityError):
                        q._read_blob_entry_at(directory_fd, name, fingerprint)
            finally:
                os.close(directory_fd)
            self.assertEqual(path.read_bytes(), EVIL)

    def test_put_blob_does_not_record_metadata_for_same_inode_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = q.QuillframeStore(Path(td) / "store")
            store.create_project("P1", "Title")
            fingerprint = q.fingerprint_bytes(GOOD)
            digest = fingerprint.split(":", 1)[1]
            target = store.location("P1").blobs / digest[:2] / digest[2:]
            real_fstat = os.fstat
            calls = 0

            def hooked_fstat(fd: int):
                nonlocal calls
                result = real_fstat(fd)
                calls += 1
                if calls == 2:
                    _overwrite_same_inode(target)
                return result

            with mock.patch.object(q.os, "fstat", side_effect=hooked_fstat):
                with self.assertRaises(q.IntegrityError):
                    store.put_blob("P1", GOOD, media_type="text/plain")
            self.assertEqual(target.read_bytes(), EVIL)
            with store.open_project("P1") as conn:
                self.assertIsNone(conn.execute("SELECT 1 FROM blob_refs LIMIT 1").fetchone())

    def test_backup_rejects_source_blob_overwrite_before_publish(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "store"
            store = q.QuillframeStore(root)
            store.create_project("P1", "Title")
            row = store.put_blob("P1", GOOD, media_type="text/plain")
            source = store.location("P1").directory / row["relative_path"]
            destination = Path(td) / "backups" / "backup.qfbackup"
            real_fstat = os.fstat
            source_calls = 0

            def hooked_fstat(fd: int):
                nonlocal source_calls
                result = real_fstat(fd)
                try:
                    descriptor_path = Path(os.readlink(f"/proc/self/fd/{fd}").split(" (deleted)", 1)[0])
                except (FileNotFoundError, OSError):
                    descriptor_path = None
                if descriptor_path == source:
                    source_calls += 1
                    if source_calls == 2:
                        _overwrite_same_inode(source)
                return result

            with mock.patch.object(q.os, "fstat", side_effect=hooked_fstat):
                with self.assertRaises(q.BundlePathError):
                    store.backup_project("P1", destination)
            self.assertEqual(source.read_bytes(), EVIL)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
