from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import QuillframeStore, canonical_json, fingerprint_text, now_iso


class _BeginImmediateBarrierConnection:
    def __init__(self, connection, barrier):
        self._connection = connection
        self._barrier = barrier

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self._connection.__exit__(exc_type, exc, traceback)

    def execute(self, sql, parameters=()):
        if sql.strip().upper() == "BEGIN IMMEDIATE":
            self._barrier.wait(timeout=5)
        return self._connection.execute(sql, parameters)


class _BeginImmediateBarrierStore(QuillframeStore):
    def __init__(self, root, barrier):
        super().__init__(root)
        self._barrier = barrier

    def open_project(self, project_id):
        return _BeginImmediateBarrierConnection(super().open_project(project_id), self._barrier)


class _FailingReceiptConnection:
    def __init__(self, connection):
        self._connection = connection
        self.in_transaction_before_exit = None

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.in_transaction_before_exit = self._connection.in_transaction
        return self._connection.__exit__(exc_type, exc, traceback)

    def execute(self, sql, parameters=()):
        if sql.strip().upper().startswith("INSERT INTO RECEIPTS") and parameters[1] == "settlement":
            raise RuntimeError("injected settlement receipt failure")
        return self._connection.execute(sql, parameters)


class _FailingReceiptStore(QuillframeStore):
    def __init__(self, root):
        super().__init__(root)
        self.last_connection = None

    def open_project(self, project_id):
        self.last_connection = _FailingReceiptConnection(super().open_project(project_id))
        return self.last_connection


class _InjectedCoreFailureConnection:
    def __init__(self, connection, failure_kind):
        self._connection = connection
        self._failure_kind = failure_kind
        self.in_transaction_before_exit = None

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.in_transaction_before_exit = self._connection.in_transaction
        return self._connection.__exit__(exc_type, exc, traceback)

    def execute(self, sql, parameters=()):
        normalized = sql.strip().upper()
        if self._failure_kind == "receipt" and normalized.startswith("INSERT INTO RECEIPTS"):
            raise RuntimeError("Q1-RECEIPT-SENTINEL")
        if self._failure_kind == "event" and normalized.startswith("INSERT INTO RUNTIME_EVENTS"):
            raise RuntimeError("Q1-EVENT-SENTINEL")
        return self._connection.execute(sql, parameters)


class _InjectedCoreFailureStore(QuillframeStore):
    def __init__(self, root, failure_kind):
        super().__init__(root)
        self.failure_kind = failure_kind
        self.last_connection = None

    def open_project(self, project_id):
        self.last_connection = _InjectedCoreFailureConnection(super().open_project(project_id), self.failure_kind)
        return self.last_connection


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
        self.assertEqual(projects["items"][0]["id"], "P")
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
        replay = self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "reject"}, idempotency_key="reject-1", reason="not right")
        self.assertEqual(result, replay)
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["canon_mutated"])
        with self.assertRaises(OperationError) as stale:
            self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user", authorization={"intent": "reject"}, idempotency_key="reject-2")
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

    def test_concurrent_settlement_competitors_have_one_winner_and_one_incomplete_loser(self):
        acceptance = self.ops.accept_candidate(
            "P",
            candidate_id="C",
            candidate_fingerprint=self.second["content_fingerprint"],
            authorized_by="user",
            authorization={"intent": "accept"},
            idempotency_key="accept-concurrent",
        )
        barrier = threading.Barrier(2)
        concurrent_ops = CoreOperations(_BeginImmediateBarrierStore(self.store.root, barrier))
        results = []
        errors = []

        def settle_with_key(idempotency_key):
            try:
                results.append(
                    concurrent_ops.settle(
                        "P",
                        acceptance_id=acceptance["acceptance_id"],
                        target_ref="chapter:DOC",
                        expected_before_fingerprint="absent",
                        user_authorized=True,
                        idempotency_key=idempotency_key,
                    )
                )
            except Exception as exc:  # pragma: no cover - failure is asserted below
                errors.append(exc)

        threads = [
            threading.Thread(target=settle_with_key, args=("settle-concurrent-a",)),
            threading.Thread(target=settle_with_key, args=("settle-concurrent-b",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(errors)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(result["status"] for result in results), ["settled", "settlement_incomplete"])
        loser = next(result for result in results if result["status"] == "settlement_incomplete")
        self.assertFalse(loser["canon_mutated"])
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM canon_state WHERE state_key='chapter:DOC'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM settlements WHERE target_ref='chapter:DOC'").fetchone()[0], 2)

    def test_settlement_write_exception_rolls_back_raw_connection_and_partial_rows(self):
        acceptance = self.ops.accept_candidate(
            "P",
            candidate_id="C",
            candidate_fingerprint=self.second["content_fingerprint"],
            authorized_by="user",
            authorization={"intent": "accept"},
            idempotency_key="accept-rollback",
        )
        failing_store = _FailingReceiptStore(self.store.root)
        failing_ops = CoreOperations(failing_store)
        with self.assertRaisesRegex(RuntimeError, "injected settlement receipt failure"):
            failing_ops.settle(
                "P",
                acceptance_id=acceptance["acceptance_id"],
                target_ref="chapter:DOC",
                expected_before_fingerprint="absent",
                user_authorized=True,
                idempotency_key="settle-rollback",
            )
        self.assertFalse(failing_store.last_connection.in_transaction_before_exit)
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM canon_state WHERE state_key='chapter:DOC'").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM settlements").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE idempotency_key='settle-rollback'").fetchone()[0], 0)

    def test_candidate_actions_fail_closed_on_wrong_fingerprint(self):
        with self.assertRaises(OperationError) as rejected:
            self.ops.reject_candidate("P", candidate_id="C", candidate_fingerprint="sha256:wrong", authorized_by="user", authorization={"intent": "reject"}, idempotency_key="bad-reject")
        self.assertEqual(rejected.exception.code, "candidate_fingerprint_mismatch")
        with self.assertRaises(OperationError) as revision:
            self.ops.request_candidate_revision("P", candidate_id="C", candidate_fingerprint="sha256:wrong", revision_request={"instruction": "x"}, authorized_by="user", authorization={"intent": "request_revision"}, idempotency_key="bad-revision")
        self.assertEqual(revision.exception.code, "candidate_fingerprint_mismatch")

    def _run_two_barrier(self, callback):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def worker():
            try:
                results.append(callback(CoreOperations(_BeginImmediateBarrierStore(self.store.root, barrier))))
            except Exception as exc:  # pragma: no cover - asserted by caller
                errors.append(exc)

        threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        return results, errors

    def test_q1_same_key_replay_is_serialized_for_all_four_write_operations(self):
        results, errors = self._run_two_barrier(
            lambda ops: ops.start_author_run(
                "P", task_mode="DRAFT", target_ref="chapter:CH001",
                payload={"chapter_id": "CH001", "instruction": "same"},
                idempotency_key="q1-start-concurrent",
            )
        )
        self.assertFalse(errors)
        self.assertEqual(results[0], results[1])
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs WHERE request_fingerprint=?", (results[0]["request_fingerprint"],)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE idempotency_key='q1-start-concurrent'").fetchone()[0], 1)

        acceptance_results, acceptance_errors = self._run_two_barrier(
            lambda ops: ops.accept_candidate(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"],
                authorized_by="user", authorization={"source": "studio", "explicit_action": "accept", "observed_gate": None},
                idempotency_key="q1-accept-concurrent",
            )
        )
        self.assertFalse(acceptance_errors)
        self.assertEqual(acceptance_results[0], acceptance_results[1])
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM acceptance_evidence WHERE candidate_id='C'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE idempotency_key='q1-accept-concurrent'").fetchone()[0], 1)

        # Use a fresh candidate for each remaining terminal operation so the
        # replay path is tested without a stale-state shortcut.
        self.tearDown()
        self.setUp()
        reject_results, reject_errors = self._run_two_barrier(
            lambda ops: ops.reject_candidate(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"],
                authorized_by="user", authorization={"source": "studio", "explicit_action": "reject"},
                idempotency_key="q1-reject-concurrent", reason="not ready",
            )
        )
        self.assertFalse(reject_errors)
        self.assertEqual(reject_results[0], reject_results[1])
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT status FROM candidates WHERE candidate_id='C'").fetchone()[0], "rejected")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE idempotency_key='q1-reject-concurrent'").fetchone()[0], 1)

        self.tearDown()
        self.setUp()
        revision_results, revision_errors = self._run_two_barrier(
            lambda ops: ops.request_candidate_revision(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"],
                revision_request={"instruction": "tighten the scene", "source": "studio"},
                authorized_by="user", authorization={"source": "studio", "explicit_action": "request_revision"},
                idempotency_key="q1-revision-concurrent",
            )
        )
        self.assertFalse(revision_errors)
        self.assertEqual(revision_results[0], revision_results[1])
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE idempotency_key='q1-revision-concurrent'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runtime_events WHERE event_kind='candidate_revision_requested'").fetchone()[0], 1)

    def test_q1_same_key_different_request_is_typed_conflict_for_all_four_operations(self):
        first = self.ops.start_author_run(
            "P", task_mode="DRAFT", target_ref="chapter:CH001",
            payload={"chapter_id": "CH001", "instruction": "first"}, idempotency_key="q1-start-conflict",
        )
        with self.assertRaises(OperationError) as start_conflict:
            self.ops.start_author_run(
                "P", task_mode="DRAFT", target_ref="chapter:CH001",
                payload={"chapter_id": "CH001", "instruction": "second"}, idempotency_key="q1-start-conflict",
            )
        self.assertEqual(start_conflict.exception.code, "idempotency_conflict")
        self.assertIsNotNone(first)

        self.tearDown()
        self.setUp()
        self.ops.accept_candidate(
            "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
            authorization={"intent": "accept"}, idempotency_key="q1-accept-conflict",
        )
        with self.assertRaises(OperationError) as accept_conflict:
            self.ops.accept_candidate(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="other",
                authorization={"intent": "accept"}, idempotency_key="q1-accept-conflict",
            )
        self.assertEqual(accept_conflict.exception.code, "idempotency_conflict")

        self.tearDown()
        self.setUp()
        self.ops.reject_candidate(
            "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
            authorization={"intent": "reject"}, idempotency_key="q1-reject-conflict", reason="first",
        )
        with self.assertRaises(OperationError) as reject_conflict:
            self.ops.reject_candidate(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
                authorization={"intent": "reject"}, idempotency_key="q1-reject-conflict", reason="second",
            )
        self.assertEqual(reject_conflict.exception.code, "idempotency_conflict")

        self.tearDown()
        self.setUp()
        self.ops.request_candidate_revision(
            "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"],
            revision_request={"instruction": "first"}, authorized_by="user", authorization={"intent": "request_revision"},
            idempotency_key="q1-revision-conflict",
        )
        with self.assertRaises(OperationError) as revision_conflict:
            self.ops.request_candidate_revision(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"],
                revision_request={"instruction": "second"}, authorized_by="user", authorization={"intent": "request_revision"},
                idempotency_key="q1-revision-conflict",
            )
        self.assertEqual(revision_conflict.exception.code, "idempotency_conflict")

    def test_q1_global_same_key_across_operations_never_leaks_integrity_error(self):
        self.ops.start_author_run(
            "P", task_mode="DRAFT", target_ref="chapter:CH001",
            payload={"chapter_id": "CH001", "instruction": "cross"}, idempotency_key="q1-cross-operation",
        )
        with self.assertRaises(OperationError) as conflict:
            self.ops.reject_candidate(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
                authorization={"intent": "reject"}, idempotency_key="q1-cross-operation", reason="cross",
            )
        self.assertEqual(conflict.exception.code, "idempotency_conflict")

    def test_q1_authorization_and_revision_request_are_strict_secret_free_contracts(self):
        invalid_authorizations = (
            {},
            {"reason": "reason-only"},
            {"intent": "reject", "nested": {"x": "y"}},
            {"intent": "reject", "nested": ["x"]},
            {"intent": "reject", "unknown": "x"},
            {"intent": "reject", "api_key": "Q1-AUTH-SENTINEL"},
            {"intent": "reject", "reason": "Bearer Q1-AUTH-SENTINEL"},
            {"intent": "reject", "reason": "-----BEGIN PRIVATE KEY-----"},
        )
        for index, authorization in enumerate(invalid_authorizations):
            with self.assertRaises(OperationError) as invalid:
                self.ops.reject_candidate(
                    "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
                    authorization=authorization, idempotency_key=f"q1-invalid-auth-{index}", reason="ordinary",
                )
            self.assertEqual(invalid.exception.code, "invalid_authorization")
            self.assertNotIn("Q1-AUTH-SENTINEL", str(invalid.exception))

        invalid_revision_requests = (
            {},
            {"instruction": ["nested"]},
            {"instruction": "x", "unknown": "y"},
            {"instruction": "x", "token": "Q1-REVISION-SENTINEL"},
            {"instruction": {"nested": "x"}},
        )
        for index, revision_request in enumerate(invalid_revision_requests):
            with self.assertRaises(OperationError) as invalid:
                self.ops.request_candidate_revision(
                    "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"],
                    revision_request=revision_request, authorized_by="user", authorization={"intent": "request_revision"},
                    idempotency_key=f"q1-invalid-revision-{index}",
                )
            self.assertEqual(invalid.exception.code, "invalid_revision_request")
            self.assertNotIn("Q1-REVISION-SENTINEL", str(invalid.exception))

        canonical = self.ops.reject_candidate(
            "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
            authorization={"Source": "studio", "Explicit_Action": "reject", "Observed_Gate": None},
            idempotency_key="q1-canonical-auth", reason="ordinary",
        )
        self.assertEqual(canonical["authorization"], {"source": "studio", "explicit_action": "reject", "observed_gate": None})

    def test_q1_all_four_write_operations_rollback_receipt_failure_without_partial_rows(self):
        operations = (
            ("start", lambda ops: ops.start_author_run(
                "P", task_mode="DRAFT", target_ref="chapter:CH001", payload={"chapter_id": "CH001"},
                idempotency_key="q1-rollback-start",
            )),
            ("accept", lambda ops: ops.accept_candidate(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
                authorization={"intent": "accept"}, idempotency_key="q1-rollback-accept",
            )),
            ("reject", lambda ops: ops.reject_candidate(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
                authorization={"intent": "reject"}, idempotency_key="q1-rollback-reject",
            )),
            ("revision", lambda ops: ops.request_candidate_revision(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], revision_request={"instruction": "x"},
                authorized_by="user", authorization={"intent": "request_revision"}, idempotency_key="q1-rollback-revision",
            )),
        )
        for name, callback in operations:
            if name != "start":
                self.tearDown()
                self.setUp()
            failing_store = _InjectedCoreFailureStore(self.store.root, "receipt")
            with self.assertRaisesRegex(RuntimeError, "Q1-RECEIPT-SENTINEL"):
                callback(CoreOperations(failing_store))
            self.assertFalse(failing_store.last_connection.in_transaction_before_exit)
            with self.store.open_project("P") as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE idempotency_key LIKE 'q1-rollback-%'").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM runtime_events WHERE event_kind IN ('author_run_requested','candidate_rejected','candidate_revision_requested')").fetchone()[0], 0)
                if name == "start":
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs WHERE request_fingerprint LIKE 'sha256:%'").fetchone()[0], 1)
                if name in {"reject", "revision"}:
                    self.assertEqual(conn.execute("SELECT status FROM candidates WHERE candidate_id='C'").fetchone()[0], "review_draft")
                if name == "accept":
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM acceptance_evidence").fetchone()[0], 0)

    def test_q1_event_failure_rolls_back_receipt_and_candidate_mutation(self):
        failing_store = _InjectedCoreFailureStore(self.store.root, "event")
        with self.assertRaisesRegex(RuntimeError, "Q1-EVENT-SENTINEL"):
            CoreOperations(failing_store).reject_candidate(
                "P", candidate_id="C", candidate_fingerprint=self.second["content_fingerprint"], authorized_by="user",
                authorization={"intent": "reject"}, idempotency_key="q1-event-rollback",
            )
        self.assertFalse(failing_store.last_connection.in_transaction_before_exit)
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT status FROM candidates WHERE candidate_id='C'").fetchone()[0], "review_draft")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE idempotency_key='q1-event-rollback'").fetchone()[0], 0)



if __name__ == "__main__":
    unittest.main()
