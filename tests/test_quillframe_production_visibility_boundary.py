from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso
from studio import host_bridge


class ProductionVisibilityBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = QuillframeStore(Path(self.temp.name))
        self.ops = CoreOperations(self.store)
        self.store.create_project("P", "Project P", "zh-CN")
        self.store.create_document("P", "DOC", "Chapter")
        revision = self.store.save_revision(
            "P",
            "DOC",
            "released candidate manuscript",
            expected_parent_revision_id=None,
            source="production_runtime",
            authority_class="review",
        )
        self.revision = revision
        stamp = now_iso()
        with self.store.open_project("P") as conn:
            conn.execute(
                "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,result_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                ("RUN", "DRAFT", "DOC", "completed", "sha256:req", revision["content_fingerprint"], stamp, stamp),
            )
            conn.execute(
                "INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("C", "DOC", revision["revision_id"], "RUN", "DRAFT", "draft", "review_draft", revision["content_fingerprint"], "PASS", stamp),
            )
            release = self._release(revision["content_fingerprint"])
            conn.execute(
                "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                ("RELEASE", "RUN", "production_release", "RUN:production_release", canonical_json(release), stamp),
            )
            conn.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _release(candidate_fingerprint: str) -> dict[str, object]:
        release: dict[str, object] = {
            "schema": "quillframe_production_release_v1",
            "candidate_fingerprint": candidate_fingerprint,
            "ready_for_user_visible_review": True,
            "authority": False,
        }
        release["release_fingerprint"] = fingerprint_text(canonical_json(release))
        return release

    def _replace_release(self, release: dict[str, object]) -> None:
        with self.store.open_project("P") as conn:
            conn.execute(
                "UPDATE receipts SET payload_json=? WHERE receipt_kind='production_release' AND run_id='RUN'",
                (canonical_json(release),),
            )
            conn.commit()

    def test_agent_package_cannot_read_raw_checkpoint_rows(self) -> None:
        out = host_bridge.invoke(
            {
                "schema": host_bridge.REQUEST_SCHEMA,
                "request_id": "checkpoint-private",
                "operation": "inspector.checkpoints.list",
                "surface": "agent_package",
                "args": {"project_id": "P"},
                "authority": False,
            }
        )
        self.assertEqual(out["status"], "invalid")
        self.assertIn("not authorized", " ".join(out["error"]["messages"]))
        self.assertNotIn("candidate_text", json.dumps(out))
        self.assertNotIn("released candidate manuscript", json.dumps(out))

    def test_candidate_visible_get_rejects_tampered_release_fingerprint(self) -> None:
        release = self._release(self.revision["content_fingerprint"])
        release["authority"] = True
        self._replace_release(release)
        with self.assertRaises(OperationError) as blocked:
            self.ops.candidate_visible_get("P", candidate_id="C")
        self.assertEqual(blocked.exception.code, "production_release_invalid")

    def test_candidate_visible_get_rejects_release_for_different_candidate(self) -> None:
        release = self._release("sha256:" + "f" * 64)
        self._replace_release(release)
        with self.assertRaises(OperationError) as blocked:
            self.ops.candidate_visible_get("P", candidate_id="C")
        self.assertEqual(blocked.exception.code, "production_release_invalid")

    def test_candidate_visible_get_returns_exact_released_content(self) -> None:
        visible = self.ops.candidate_visible_get("P", candidate_id="C")
        self.assertEqual(visible["candidate_fingerprint"], self.revision["content_fingerprint"])
        self.assertEqual(visible["content"], "released candidate manuscript")
        self.assertEqual(visible["content_access"], "production_release_only")
        self.assertTrue(visible["production_release"]["ready_for_user_visible_review"])


if __name__ == "__main__":
    unittest.main()
