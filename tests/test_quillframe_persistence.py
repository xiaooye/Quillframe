from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from persistence.quillframe_sqlite import ConflictError, QuillframeStore, fingerprint_text


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

if __name__=="__main__": unittest.main()
