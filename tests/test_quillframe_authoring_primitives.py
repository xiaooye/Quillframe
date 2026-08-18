from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso


class AuthoringPrimitiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = QuillframeStore(Path(self.temp.name))
        self.ops = CoreOperations(self.store)
        self.store.create_project("P", "Project P", "zh-CN")
        self.store.create_document("P", "DOC", "Chapter")
        first = self.store.save_revision("P", "DOC", "incumbent", expected_parent_revision_id=None, source="test")
        second = self.store.save_revision("P", "DOC", "candidate", expected_parent_revision_id=first["revision_id"], source="test", authority_class="review")
        self.first = first
        self.second = second
        stamp = now_iso()
        with self.store.open_project("P") as conn:
            conn.execute("INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", ("RUN", "DRAFT", "DOC", "completed", "sha256:req", stamp, stamp))
            conn.execute("INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ("C", "DOC", second["revision_id"], "RUN", "DRAFT", "draft", "review_draft", second["content_fingerprint"], "PASS", stamp))
            for mechanism in ("reader_engagement", "character_simulation", "continuity", "independent_semantic_gate", "user_visible_gate"):
                payload = {"mechanism": mechanism, "stage_result_fingerprint": f"sha256:{mechanism}", "judgment": {"status": "pass"}, "private_reasoning_exposed": False}
                conn.execute("INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)", (f"R-{mechanism}", "RUN", "production_stage", f"RUN:{mechanism}", canonical_json(payload), stamp))
            review = {"model_contract_id": "quality.production_review", "production_readiness": {"ready_for_user_visible_review": True}, "private_reasoning_exposed": False}
            conn.execute("INSERT INTO review_evidence(review_id,candidate_id,evidence_kind,result_json,candidate_fingerprint,reviewer_fingerprint,independent,stale,created_at) VALUES(?,?,?,?,?,?,1,0,?)", ("REV", "C", "quality.production_review", canonical_json(review), second["content_fingerprint"], "sha256:peer", stamp))
            release = {
                "schema": "quillframe_production_release_v1",
                "candidate_fingerprint": second["content_fingerprint"],
                "production_readiness_fingerprint": "sha256:" + "a" * 64,
                "base_production_readiness": True,
                "pre_independent_qualification_required": True,
                "pre_independent_qualification_fingerprint": "sha256:" + "b" * 64,
                "independent_pass_can_override_qualification_failure": False,
                "required_structural_receipts": ["context_assembly", "user_visible_gate"],
                "structural_receipts": [],
                "missing_structural_receipts": [],
                "blocking_structural_receipts": [],
                "pending_structural_receipts": [],
                "structural_ready": True,
                "ready_for_user_visible_review": True,
                "semantic_pass_can_override_missing_structural_receipt": False,
                "authority": False,
                "permissions": {"canon_write": False, "framework_write": False},
                "model_execution": False,
            }
            release["release_fingerprint"] = fingerprint_text(canonical_json(release))
            conn.execute("INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)", ("R-RELEASE", "RUN", "production_release", "RUN:production_release", canonical_json(release), stamp))
            conn.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_project_and_document_registry_are_core_owned_read_only_projections(self):
        projects = self.ops.project_list()
        self.assertEqual(projects["items"][0]["project_id"], "P")
        self.assertFalse(projects["authority"])
        docs = self.ops.document_list("P")
        self.assertEqual(docs["items"][0]["document_id"], "DOC")
        self.assertEqual(docs["items"][0]["latest_revision_id"], self.second["revision_id"])
        self.assertEqual(docs["items"][0]["latest_content_fingerprint"], self.second["content_fingerprint"])
        self.assertFalse(docs["authority"])

    def test_candidate_review_projection_is_exact_and_contains_safe_required_evidence(self):
        review = self.ops.candidate_review_get("P", candidate_id="C")
        self.assertEqual(review["candidate"]["candidate_fingerprint"], self.second["content_fingerprint"])
        self.assertEqual(review["candidate_revision"]["content"], "candidate")
        self.assertEqual(review["incumbent_revision"]["content"], "incumbent")
        self.assertTrue(review["diff"]["diff"])
        self.assertEqual(set(review["evidence"]), {"reader", "character", "continuity", "independent", "production_readiness", "user_visible_gate", "production_release"})
        self.assertFalse(review["private_reasoning_exposed"])


    def test_candidate_visible_get_returns_content_only_with_valid_release(self):
        visible = self.ops.candidate_visible_get("P", candidate_id="C")
        self.assertEqual(visible["content"], "candidate")
        self.assertEqual(visible["content_access"], "production_release_only")
        self.assertTrue(visible["production_release"]["ready_for_user_visible_review"])

    def test_candidate_visible_get_fails_closed_when_release_is_missing_or_tampered(self):
        with self.store.open_project("P") as conn:
            conn.execute("DELETE FROM receipts WHERE receipt_kind='production_release'")
            conn.commit()
        with self.assertRaises(OperationError) as missing:
            self.ops.candidate_visible_get("P", candidate_id="C")
        self.assertEqual(missing.exception.code, "production_release_required")

    def test_candidate_reject_is_idempotent_exact_and_terminal(self):
        result = self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "reject"}, idempotency_key="reject-1", reason="not right")
        replay = self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "reject"}, idempotency_key="reject-1")
        self.assertEqual(result, replay)
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["canon_mutated"])
        with self.assertRaises(OperationError) as stale:
            self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={}, idempotency_key="reject-2")
        self.assertEqual(stale.exception.code, "stale_state")

    def test_request_revision_is_durable_does_not_auto_start_revise_and_blocks_accept(self):
        result = self.ops.request_candidate_revision("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], revision_request={"instruction": "fix pacing"}, authorized_by="user", authorization={"intent": "request_revision"}, idempotency_key="rr-1")
        self.assertEqual(result["effective_status"], "revision_requested")
        self.assertFalse(result["next_action"]["auto_started"])
        self.assertEqual(result["next_action"]["task_mode"], "REVISE")
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT status FROM candidates WHERE candidate_id='C'").fetchone()[0], "review_draft")
        review = self.ops.candidate_review_get("P", candidate_id="C")
        self.assertEqual(review["candidate"]["effective_status"], "revision_requested")
        with self.assertRaises(OperationError) as blocked:
            self.ops.accept_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "accept"}, idempotency_key="accept-after-rr")
        self.assertEqual(blocked.exception.code, "candidate_revision_requested")

    def test_settlement_preflight_is_authoritative_and_read_only_then_apply_uses_exact_before(self):
        acceptance = self.ops.accept_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "accept"}, idempotency_key="accept-1")
        with self.store.open_project("P") as conn:
            before_counts = (conn.execute("SELECT COUNT(*) FROM settlements").fetchone()[0], conn.execute("SELECT COUNT(*) FROM canon_state").fetchone()[0])
        preflight = self.ops.settlement_preflight("P", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:DOC")
        self.assertEqual(preflight["expected_before_fingerprint"], "absent")
        self.assertTrue(preflight["settleable"])
        self.assertFalse(preflight["mutation_performed"])
        with self.store.open_project("P") as conn:
            after_counts = (conn.execute("SELECT COUNT(*) FROM settlements").fetchone()[0], conn.execute("SELECT COUNT(*) FROM canon_state").fetchone()[0])
        self.assertEqual(before_counts, after_counts)
        settled = self.ops.settle("P", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:DOC", expected_before_fingerprint=preflight["expected_before_fingerprint"], user_authorized=True, idempotency_key="settle-1")
        self.assertEqual(settled["status"], "settled")

    def test_candidate_actions_fail_closed_on_wrong_fingerprint(self):
        with self.assertRaises(OperationError) as rejected:
            self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint="sha256:wrong", authorized_by="user", authorization={}, idempotency_key="bad-reject")
        self.assertEqual(rejected.exception.code, "candidate_fingerprint_mismatch")
        with self.assertRaises(OperationError) as revision:
            self.ops.request_candidate_revision("P", candidate_id="C", candidate_fingerprint="sha256:wrong", revision_request={"instruction": "x"}, authorized_by="user", authorization={}, idempotency_key="bad-revision")
        self.assertEqual(revision.exception.code, "candidate_fingerprint_mismatch")


if __name__ == "__main__":
    unittest.main()
