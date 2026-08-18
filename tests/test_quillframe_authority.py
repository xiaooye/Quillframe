from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import QuillframeStore


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.store=QuillframeStore(Path(self.tmp.name)); self.store.create_project("P1","Book")
        self.ops=CoreOperations(self.store)
    def tearDown(self): self.tmp.cleanup()

    def test_audit_cannot_rewrite(self):
        with self.assertRaises(OperationError): self.ops.start_author_run("P1",task_mode="AUDIT",target_ref="chapter:1",payload={"rewrite":True})

    def test_draft_cannot_settle(self):
        with self.assertRaises(OperationError): self.ops.start_author_run("P1",task_mode="DRAFT",target_ref="chapter:1",payload={"settle":True})

    def test_feedback_capture_does_not_promote(self):
        result=self.ops.observe_feedback("P1",evidence_kind="rejection",payload={"text":"不要用作者总结"})
        self.assertTrue(result["captured"]); self.assertFalse(result["promotion_eligible"]); self.assertFalse(result["canon_write"])

    def test_author_run_is_exact_and_non_authoritative(self):
        result=self.ops.start_author_run("P1",task_mode="REVISE",target_ref="scene:S1",payload={"fix":["pacing"],"preserve":["voice"]})
        self.assertEqual(result["task_mode"],"REVISE"); self.assertEqual(result["status"],"awaiting_semantic"); self.assertFalse(result["authority"])

if __name__=="__main__": unittest.main()
