from __future__ import annotations
import json
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import persistence.quillframe_sqlite as persistence_module
from persistence.quillframe_sqlite import ConflictError, IntegrityError, QuillframeStore, fingerprint_bytes


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.store=QuillframeStore(self.root)
        self.store.create_project("P1","测试长篇","zh-CN")
        self.store.create_document("P1","DOC1","第一章")
    def tearDown(self): self.tmp.cleanup()

    def test_revision_conflict_and_search(self):
        r1=self.store.save_revision("P1","DOC1","夜里十点，雨落在窗上。",expected_parent_revision_id=None,source="autosave")
        with self.assertRaises(ConflictError):
            self.store.save_revision("P1","DOC1","冲突版本",expected_parent_revision_id=None,source="autosave")
        r2=self.store.save_revision("P1","DOC1","夜里十点，雨落在窗上。门开了。",expected_parent_revision_id=r1["revision_id"],source="user_edit")
        self.assertNotEqual(r1["content_fingerprint"],r2["content_fingerprint"])
        self.assertTrue(self.store.search("P1","门开"))

    def test_blob_backup_restore_and_doctor(self):
        self.store.put_blob("P1",b"binary-fixture","application/octet-stream")
        bundle=self.store.backup_project("P1")
        self.assertTrue(self.store.verify_backup(bundle)["valid"])
        report=self.store.doctor("P1")
        self.assertTrue(report["ok"],json.dumps(report,ensure_ascii=False))
        restore=QuillframeStore(self.root/"restored")
        restore.restore_project(bundle)
        self.assertTrue(restore.doctor("P1")["ok"])

    def test_blob_publish_ignores_predictable_temp_symlink_without_external_write(self):
        payload = b"new blob payload"
        digest = fingerprint_bytes(payload).split(":", 1)[1]
        target = self.store.location("P1").blobs / digest[:2] / digest[2:]
        target.parent.mkdir(parents=True, exist_ok=True)
        outside = self.root / "outside-sentinel"
        outside.write_bytes(b"DO-NOT-CHANGE")
        legacy_temp = target.with_suffix(".tmp")
        legacy_temp.symlink_to(outside)

        receipt = self.store.put_blob("P1", payload, "application/octet-stream")

        self.assertEqual(receipt["fingerprint"], fingerprint_bytes(payload))
        self.assertEqual(outside.read_bytes(), b"DO-NOT-CHANGE")
        self.assertTrue(legacy_temp.is_symlink())
        self.assertTrue(target.is_file())
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_bytes(), payload)

    def test_blob_target_symlink_is_rejected_even_when_external_content_matches(self):
        payload = b"matching external payload"
        digest = fingerprint_bytes(payload).split(":", 1)[1]
        target = self.store.location("P1").blobs / digest[:2] / digest[2:]
        target.parent.mkdir(parents=True, exist_ok=True)
        outside = self.root / "outside-matching"
        outside.write_bytes(payload)
        target.symlink_to(outside)

        with self.assertRaises(IntegrityError):
            self.store.put_blob("P1", payload, "application/octet-stream")

        self.assertTrue(target.is_symlink())
        self.assertEqual(outside.read_bytes(), payload)
        with self.store.open_project("P1") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM blob_refs").fetchone()[0], 0)

    def test_blob_parent_symlink_is_rejected_without_external_write(self):
        payload = b"parent symlink payload"
        digest = fingerprint_bytes(payload).split(":", 1)[1]
        prefix = self.store.location("P1").blobs / digest[:2]
        outside = self.root / "outside-directory"
        outside.mkdir()
        prefix.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(IntegrityError):
            self.store.put_blob("P1", payload, "application/octet-stream")

        self.assertEqual(list(outside.iterdir()), [])
        with self.store.open_project("P1") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM blob_refs").fetchone()[0], 0)

    @unittest.skipUnless(hasattr(os, "link"), "hard links are unavailable")
    def test_blob_existing_hard_link_is_rejected(self):
        payload = b"hard-linked payload"
        digest = fingerprint_bytes(payload).split(":", 1)[1]
        target = self.store.location("P1").blobs / digest[:2] / digest[2:]
        target.parent.mkdir(parents=True, exist_ok=True)
        outside = self.root / "outside-hard-link"
        outside.write_bytes(payload)
        os.link(outside, target)

        with self.assertRaises(IntegrityError):
            self.store.put_blob("P1", payload, "application/octet-stream")

        self.assertEqual(outside.read_bytes(), payload)
        with self.store.open_project("P1") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM blob_refs").fetchone()[0], 0)

    def test_concurrent_blob_publishers_converge_on_one_owned_inode(self):
        payload = b"concurrent content-addressed payload"
        barrier = threading.Barrier(2, timeout=10)
        original_publish = persistence_module._linkat_empty_path

        def synchronized_publish(source_fd: int, parent_fd: int, target_name: str) -> None:
            barrier.wait()
            original_publish(source_fd, parent_fd, target_name)

        with patch.object(persistence_module, "_linkat_empty_path", side_effect=synchronized_publish):
            with ThreadPoolExecutor(max_workers=2) as pool:
                receipts = list(pool.map(lambda _: self.store.put_blob("P1", payload), range(2)))

        self.assertEqual(receipts[0], receipts[1])
        target = self.store.location("P1").directory / receipts[0]["relative_path"]
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.stat().st_nlink, 1)
        self.assertEqual(target.read_bytes(), payload)
        with self.store.open_project("P1") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM blob_refs").fetchone()[0], 1)

if __name__=="__main__": unittest.main()
