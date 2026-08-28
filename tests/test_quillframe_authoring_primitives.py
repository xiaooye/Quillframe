from __future__ import annotations

import tempfile
import json
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
        with self.store.open_project("P") as conn:
            conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title) VALUES('CH001','chapter',1,'Chapter')")
            conn.commit()
        self.store.create_document("P", "DOC", "Chapter", story_node_id="CH001")
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

    def test_author_run_start_bootstraps_a_durable_manager_and_replays_without_duplicates(self):
        request = {
            "task_mode": "DRAFT",
            "target_ref": "chapter:CH001",
            "payload": {"chapter_id": "CH001", "instruction": "draft chapter"},
            "idempotency_key": "start-with-manager",
        }
        result = self.ops.start_author_run("P", **request)
        replay = CoreOperations(QuillframeStore(self.store.root)).start_author_run("P", **request)
        self.assertEqual(result, replay)
        self.assertEqual(result["request_fingerprint"], fingerprint_text(canonical_json({
            "operation": "author.run.start", "project_id": "P",
            "task_mode": request["task_mode"], "target_ref": request["target_ref"],
            "payload": request["payload"], "session_id": None,
        })))
        with self.store.open_project("P") as conn:
            sessions = conn.execute("SELECT * FROM sessions").fetchall()
            run = conn.execute("SELECT session_id,created_at FROM runs WHERE run_id=?", (result["run_id"],)).fetchone()
            receipt = conn.execute("SELECT payload_json FROM receipts WHERE idempotency_key=?", (request["idempotency_key"],)).fetchone()
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs WHERE session_id=?", (result["session_id"],)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runtime_events WHERE run_id=?", (result["run_id"],)).fetchone()[0], 1)
        self.assertEqual(len(sessions), 1)
        manager = sessions[0]
        self.assertEqual(manager["session_id"], result["session_id"])
        self.assertEqual(run["session_id"], manager["session_id"])
        self.assertEqual(manager["status"], "running")
        self.assertEqual(manager["version"], 1)
        self.assertEqual(manager["created_at"], run["created_at"])
        self.assertIsNone(manager["provider_session_ref"])
        self.assertIsNone(manager["framework_fingerprint"])
        self.assertEqual(receipt["payload_json"], canonical_json(result))

        # Naming the generated session is a different caller request, even
        # though the original run resolved to that same execution identity.
        with self.assertRaises(OperationError) as conflict:
            self.ops.start_author_run("P", session_id=result["session_id"], **request)
        self.assertEqual(conflict.exception.code, "idempotency_conflict")
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs WHERE session_id=?", (result["session_id"],)).fetchone()[0], 1)

    def test_author_run_start_preserves_an_explicit_session_without_bootstrapping_another(self):
        session_id = "SES-EXPLICIT"
        stamp = now_iso()
        with self.store.open_project("P") as conn:
            conn.execute(
                "INSERT INTO sessions(session_id,status,version,created_at,updated_at) VALUES(?,?,3,?,?)",
                (session_id, "running", stamp, stamp),
            )
            conn.commit()
            before = dict(conn.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone())
        result = self.ops.start_author_run(
            "P", task_mode="DRAFT", target_ref="chapter:CH001",
            payload={"chapter_id": "CH001"}, session_id=session_id, idempotency_key="start-explicit-session",
        )
        self.assertEqual(result["session_id"], session_id)
        with self.store.open_project("P") as conn:
            self.assertEqual([dict(row) for row in conn.execute("SELECT * FROM sessions")], [before])
            self.assertEqual(conn.execute("SELECT session_id FROM runs WHERE run_id=?", (result["run_id"],)).fetchone()[0], session_id)

    def test_author_run_start_invalid_explicit_session_does_not_write_or_bootstrap(self):
        tables = ("sessions", "runs", "receipts", "runtime_events")
        with self.store.open_project("P") as conn:
            before = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
        for session_id, code in (("SES-MISSING", "unknown_session"), ("", "invalid_args"), (" ", "invalid_args"), (42, "invalid_args")):
            with self.subTest(session_id=session_id):
                with self.assertRaises(OperationError) as invalid:
                    self.ops.start_author_run(
                        "P", task_mode="DRAFT", target_ref="chapter:CH001",
                        payload={"chapter_id": "CH001"}, session_id=session_id, idempotency_key="start-invalid-session",
                    )
                self.assertEqual(invalid.exception.code, code)
                with self.store.open_project("P") as conn:
                    after = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
                self.assertEqual(after, before)

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
        preflight = self.ops.settlement_preflight("P", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:CH001")
        self.assertEqual(preflight["expected_before_fingerprint"], "absent")
        self.assertTrue(preflight["settleable"])
        self.assertFalse(preflight["mutation_performed"])
        with self.store.open_project("P") as conn:
            after_counts = (conn.execute("SELECT COUNT(*) FROM settlements").fetchone()[0], conn.execute("SELECT COUNT(*) FROM canon_state").fetchone()[0])
        self.assertEqual(before_counts, after_counts)
        settled = self.ops.settle("P", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:CH001", expected_before_fingerprint=preflight["expected_before_fingerprint"], user_authorized=True, idempotency_key="settle-1")
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
                        target_ref="chapter:CH001",
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
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM canon_state WHERE state_key='chapter:CH001'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM settlements WHERE target_ref='chapter:CH001'").fetchone()[0], 2)

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
                target_ref="chapter:CH001",
                expected_before_fingerprint="absent",
                user_authorized=True,
                idempotency_key="settle-rollback",
            )
        self.assertFalse(failing_store.last_connection.in_transaction_before_exit)
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM canon_state WHERE state_key='chapter:CH001'").fetchone()[0], 0)
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
            self.assertEqual([row["session_id"] for row in conn.execute("SELECT session_id FROM sessions")], [results[0]["session_id"]])
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
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)

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
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs WHERE request_fingerprint LIKE 'sha256:%'").fetchone()[0], 1)
                if name in {"reject", "revision"}:
                    self.assertEqual(conn.execute("SELECT status FROM candidates WHERE candidate_id='C'").fetchone()[0], "review_draft")
                if name == "accept":
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM acceptance_evidence").fetchone()[0], 0)

    def test_author_run_start_event_failure_rolls_back_the_manager_session(self):
        failing_store = _InjectedCoreFailureStore(self.store.root, "event")
        with self.assertRaisesRegex(RuntimeError, "Q1-EVENT-SENTINEL"):
            CoreOperations(failing_store).start_author_run(
                "P", task_mode="DRAFT", target_ref="chapter:CH001",
                payload={"chapter_id": "CH001"}, idempotency_key="start-event-rollback",
            )
        self.assertFalse(failing_store.last_connection.in_transaction_before_exit)
        with self.store.open_project("P") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runtime_events").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE idempotency_key='start-event-rollback'").fetchone()[0], 0)

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

    def test_settlement_rejects_an_unrelated_chapter_without_writing(self):
        accepted = self.ops.accept_candidate('P', candidate_id='C', candidate_fingerprint=self.second['content_fingerprint'],
            authorized_by='author', authorization={'intent': 'accept'}, idempotency_key='target-accept')
        for target in ('chapter:DOC', 'chapter:CH999', 'book'):
            with self.subTest(target=target), self.assertRaises(OperationError) as error:
                self.ops.settle('P', acceptance_id=accepted['acceptance_id'], target_ref=target,
                    expected_before_fingerprint='absent', user_authorized=True, idempotency_key='target:' + target)
            self.assertEqual(error.exception.code, 'settlement_target_mismatch')
        with self.store.open_project('P') as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM settlements').fetchone()[0], 0)

    def test_document_open_and_compare_cannot_bypass_private_or_tampered_candidate(self):
        with self.store.open_project('P') as conn:
            conn.execute("DELETE FROM receipts WHERE receipt_kind='production_release'")
            conn.commit()
        opened = self.ops.document_open('P', 'DOC')
        self.assertEqual(opened['latest_revision']['content'], 'incumbent')
        with self.assertRaises(OperationError) as blocked:
            self.ops.revision_compare('P', self.first['revision_id'], self.second['revision_id'])
        self.assertEqual(blocked.exception.code, 'revision_not_visible')
        with self.store.open_project('P') as conn:
            conn.execute('UPDATE document_revisions SET content=? WHERE revision_id=?', ('tampered', self.second['revision_id']))
            conn.commit()
        with self.assertRaises(OperationError) as tampered:
            self.ops.candidate_visible_get('P', candidate_id='C')
        self.assertEqual(tampered.exception.code, 'stale_review')

    def test_settlement_idempotency_key_cannot_replay_a_changed_target(self):
        accepted = self.ops.accept_candidate('P', candidate_id='C', candidate_fingerprint=self.second['content_fingerprint'],
            authorized_by='author', authorization={'intent': 'accept'}, idempotency_key='idem-accept')
        args = dict(acceptance_id=accepted['acceptance_id'], target_ref='chapter:CH001', expected_before_fingerprint='absent',
                    user_authorized=True, idempotency_key='chapter-settle')
        result = self.ops.settle('P', **args)
        self.assertEqual(result, self.ops.settle('P', **args))
        with self.assertRaises(OperationError) as changed:
            self.ops.settle('P', **{**args, 'target_ref': 'chapter:CH002'})
        self.assertEqual(changed.exception.code, 'idempotency_conflict')


class NovelProductionPrimitiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='quillframe-novel-primitives-')
        self.addCleanup(self.temp.cleanup)
        self.store = QuillframeStore(Path(self.temp.name))
        self.ops = CoreOperations(self.store)
        self.ops.project_create('BOOK', 'Synthetic novel')

    def test_native_creation_is_exclusive_and_twelve_chapters_are_real_rows(self):
        self.assertEqual(set(self.ops.project_inspect('BOOK')['manifest']), {'schema', 'id', 'title', 'language'})
        for ordinal in range(2, 13):
            args = dict(title=f'Chapter {ordinal}', idempotency_key=f'chapter-{ordinal}', user_authorized=True)
            created = self.ops.chapter_create('BOOK', **args)
            self.assertEqual(created, self.ops.chapter_create('BOOK', **args))
        items = self.ops.chapter_list('BOOK')['items']
        self.assertEqual([item['chapter_id'] for item in items], [f'CH{i:03}' for i in range(1, 13)])
        self.assertEqual(len({item['document_id'] for item in items}), 12)
        with self.assertRaises(FileExistsError):
            self.ops.project_create('BOOK', 'Must not replace')
        self.assertEqual(self.ops.project_inspect('BOOK')['manifest']['title'], 'Synthetic novel')

    def test_plan_versions_use_real_horizon_and_compare_and_swap(self):
        args = dict(target_ref='chapter:CH001', title='Opening promise', content='A choice has a visible cost.',
                    reader_intent={'reader_question': 'Can the choice be reversed?'}, expected_version=0,
                    idempotency_key='plan-v1', user_authorized=True)
        first = self.ops.plan_save('BOOK', **args)
        self.assertEqual(first, self.ops.plan_save('BOOK', **args))
        self.assertEqual(first['version'], 1)
        self.assertEqual(first['horizon']['region']['commitment_strength'], 'hard')
        with self.assertRaises(OperationError) as stale:
            self.ops.plan_save('BOOK', **{**args, 'content': 'Changed.', 'idempotency_key': 'stale-plan'})
        self.assertEqual(stale.exception.code, 'plan_version_conflict')
        second = self.ops.plan_save('BOOK', **{**args, 'content': 'New cost.', 'expected_version': 1, 'idempotency_key': 'plan-v2'})
        self.assertEqual(second['version'], 2)
        with self.store.open_project('BOOK') as conn:
            versions = conn.execute('SELECT version,payload_json FROM plan_versions ORDER BY version').fetchall()
            self.assertEqual([row['version'] for row in versions], [1, 2])
            self.assertEqual(json.loads(versions[0]['payload_json'])['content'], args['content'])
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM canon_state').fetchone()[0], 0)

    def test_book_plan_stays_open_and_cannot_reference_an_unknown_expectation(self):
        result = self.ops.plan_save('BOOK', target_ref='book', title='Volume direction', content='A long conflict.',
            expected_version=0, idempotency_key='book-plan', user_authorized=True)
        self.assertEqual(result['horizon']['region']['commitment_strength'], 'open')
        with self.assertRaises(OperationError) as missing:
            self.ops.plan_save('BOOK', target_ref='chapter:CH001', title='Chapter', content='A payoff.', expected_version=0,
                expectation_refs=['invented-reader-memory'], idempotency_key='bad-ref', user_authorized=True)
        self.assertEqual(missing.exception.code, 'expectation_not_found')

    def test_run_freezes_actual_target_and_missing_prior_acceptance_stops_next_chapter(self):
        args = dict(task_mode='DRAFT', target_ref='DOC-CH001', payload={'chapter_id': 'CH001'}, idempotency_key='first-run')
        run = self.ops.start_author_run('BOOK', **args)
        self.assertEqual(run, self.ops.start_author_run('BOOK', **args))
        with self.store.open_project('BOOK') as conn:
            row = conn.execute("SELECT state_json,artifact_fingerprint FROM checkpoints WHERE run_id=? AND checkpoint_kind='author_run_request'", (run['run_id'],)).fetchone()
            target = json.loads(row['state_json'])
            self.assertEqual((target['chapter_id'], target['document_id'], target['current_reading_order']), ('CH001', 'DOC-CH001', 1))
            self.assertEqual(fingerprint_text(canonical_json(target)), row['artifact_fingerprint'])
        self.ops.chapter_create('BOOK', title='Chapter 2', idempotency_key='second-chapter', user_authorized=True)
        with self.assertRaises(OperationError) as pending:
            self.ops.start_author_run('BOOK', task_mode='DRAFT', target_ref='DOC-CH002', payload={'chapter_id': 'CH002'})
        self.assertEqual(pending.exception.code, 'prior_chapter_not_ready')
        with self.store.open_project('BOOK') as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 1)

    def test_run_cannot_bind_another_chapters_document(self):
        self.ops.chapter_create('BOOK', title='Chapter 2', idempotency_key='chapter-two', user_authorized=True)
        with self.assertRaises(OperationError) as mismatch:
            self.ops.start_author_run('BOOK', task_mode='DRAFT', target_ref='DOC-CH002', payload={'chapter_id': 'CH001'})
        self.assertEqual(mismatch.exception.code, 'chapter_document_mismatch')
        with self.store.open_project('BOOK') as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 0)



class ProjectLearningCoreIntegrationTests(unittest.TestCase):
    """Native Core/Bridge storage with synthetic workers; never live model proof."""

    def setUp(self):
        from types import SimpleNamespace
        from production_runtime import ProductionRunExecutor
        from production_runtime.workflow_service import NovelWorkflowService
        from tests.test_quillframe_production_runtime import (
            FakeAgentRuntime, PROVENANCE, RULE_MATERIAL, frozen_packet, peer_result, project_bridge_receipt,
        )
        self.temp = tempfile.TemporaryDirectory(prefix="quillframe-learning-core-")
        self.addCleanup(self.temp.cleanup)
        self.store = QuillframeStore(Path(self.temp.name))
        self.ops = CoreOperations(self.store)
        self.ops.project_create("PROD", "Synthetic learning integration")
        self.run = self.ops.start_author_run("PROD", task_mode="DRAFT", target_ref="DOC-CH001",
                                             payload={"chapter_id": "CH001", "instruction": "draft chapter"})
        NovelWorkflowService(self.store).start(project_id="PROD", run_id=self.run["run_id"], chapter_id="CH001", author_profile="guided")
        production = ProductionRunExecutor(self.store, FakeAgentRuntime())
        handoff = production.execute("PROD", self.run["run_id"], service_id="synthetic-production",
                                     instruction="draft chapter", reader_grip="very_high", rule_material=RULE_MATERIAL,
                                     independent_provenance=PROVENANCE)
        self.assertEqual("awaiting_external", handoff["status"])
        packet = frozen_packet(self.store, self.run["run_id"])
        review = peer_result(packet, "pass")
        completed = production.submit_independent("PROD", self.run["run_id"], peer_packet=packet, result=review,
                                                   independence_receipt=project_bridge_receipt(packet, review))
        self.assertEqual("completed", completed["status"])
        self.candidate = completed["candidate"]
        self.learning = self.ops.learning()
        self.semantic_calls = []
        self.on_semantic_call = None
        self.runtime = SimpleNamespace(run=self.semantic_run)
        with self.store.open_project("PROD") as conn:
            self.release_receipt = dict(conn.execute("SELECT * FROM receipts WHERE run_id=? AND receipt_kind='production_release'",
                                                     (self.run["run_id"],)).fetchone())

    def semantic_run(self, job):
        from agent_runtime import AgentResult
        from learning.feedback_intake import CONTRACT_ID
        from tests.test_quillframe_project_learning import interpretation, promotion
        self.semantic_calls.append(job)
        prepared = job.context[0]["registered_semantic_job"]
        contract_id = prepared["input"]["model_contract_id"]
        if contract_id == CONTRACT_ID:
            judgment = interpretation()
        else:
            self.assertEqual("learning.promotion_review", contract_id)
            judgment = promotion(prepared)["judgment"]
        if self.on_semantic_call:
            self.on_semantic_call(job)
        return AgentResult(job_id=job.job_id, session_id=job.session_id, run_id=job.run_id, status="completed",
                           model_service_id=job.service_id, model_id="synthetic-learning", protocol="fixture",
                           input_fingerprint=job.input_fingerprint, final_text=json.dumps(judgment), steps=1, model_requests=1)

    def bridge(self, operation, args, *, surface="local_app"):
        from unittest.mock import patch
        from studio import host_bridge
        request = {"schema": host_bridge.REQUEST_SCHEMA, "bridge_version": host_bridge.BRIDGE_VERSION,
                   "request_id": operation + ":fixture", "operation": operation, "surface": surface,
                   "args": {"project_id": "PROD", **args}, "authority": False}
        with patch.object(host_bridge, "ops", side_effect=lambda **_: CoreOperations(self.store)), \
                patch.object(host_bridge, "agent_runtime", return_value=self.runtime):
            return host_bridge.invoke(request)

    def observe_args(self, event_id="FB-CORE", **changes):
        return {"event_id": event_id, "feedback_text": "The speakers should have different knowledge.",
                "evidence_kind": "human_review", "candidate_id": self.candidate["candidate_id"],
                "candidate_fingerprint": self.candidate["candidate_fingerprint"], "document_id": "DOC-CH001",
                "run_id": self.run["run_id"], "source_type": "author", "source_id": "fixture-author", **changes}

    def observe(self, event_id="FB-CORE", **changes):
        result = self.bridge("learning.feedback.observe", self.observe_args(event_id, **changes))
        self.assertEqual("ok", result["status"], result)
        return result["data"]

    def capture(self, event_id="FB-CORE"):
        result = self.bridge("learning.feedback.execute", {"event_id": event_id, "service_id": "learning-fixture"})
        self.assertEqual("ok", result["status"], result)
        self.assertEqual("persisted", result["data"]["status"])
        return self.learning.get_preference("PROD", hypothesis_id=result["data"]["intake"]["hypothesis_id"])

    def revoke_release(self, _job=None):
        with self.store.open_project("PROD") as conn:
            conn.execute("DELETE FROM receipts WHERE receipt_id=?", (self.release_receipt["receipt_id"],))
            conn.commit()

    def restore_release(self):
        keys = ("receipt_id", "run_id", "receipt_kind", "idempotency_key", "payload_json", "created_at")
        with self.store.open_project("PROD") as conn:
            conn.execute("INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                         tuple(self.release_receipt[key] for key in keys))
            conn.commit()

    def test_feedback_session_is_core_bound_and_drift_rejected_before_model(self):
        observed = self.observe(session_id="FORGED-CALLER-SESSION")
        self.assertEqual(self.run["session_id"], observed["session_id"])
        with self.store.open_project("PROD") as conn:
            self.assertIsNotNone(conn.execute("SELECT 1 FROM sessions WHERE session_id=?", (observed["session_id"],)).fetchone())
            stamp = now_iso()
            conn.execute("INSERT INTO sessions(session_id,status,version,created_at,updated_at) VALUES('OTHER-SESSION','running',1,?,?)", (stamp, stamp))
            conn.execute("UPDATE runs SET session_id='OTHER-SESSION' WHERE run_id=?", (self.run["run_id"],))
            conn.commit()
        result = self.bridge("learning.feedback.execute", {"event_id": "FB-CORE", "service_id": "learning-fixture"})
        self.assertEqual("failed", result["status"])
        self.assertEqual("feedback_source_mismatch", result["error"]["code"])
        self.assertEqual([], self.semantic_calls)
        self.assertEqual([], self.learning.list_preferences("PROD")["items"])

    def test_changed_candidate_or_missing_release_cannot_enter_learning(self):
        self.observe()
        with self.store.open_project("PROD") as conn:
            content = conn.execute("SELECT content FROM document_revisions WHERE revision_id=?", (self.candidate["revision_id"],)).fetchone()[0]
            conn.execute("UPDATE document_revisions SET content='changed bytes without a new review' WHERE revision_id=?", (self.candidate["revision_id"],))
            conn.commit()
        changed = self.bridge("learning.feedback.execute", {"event_id": "FB-CORE", "service_id": "learning-fixture"})
        self.assertEqual("feedback_source_mismatch", changed["error"]["code"])
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE document_revisions SET content=? WHERE revision_id=?", (content, self.candidate["revision_id"]))
            conn.commit()
        self.revoke_release()
        for operation, args in (
            ("learning.feedback.observe", self.observe_args("FB-NO-RELEASE")),
            ("learning.feedback.resume", {"event_id": "FB-CORE", "service_id": "learning-fixture"}),
        ):
            with self.subTest(operation=operation):
                result = self.bridge(operation, args)
                self.assertEqual("failed", result["status"])
                self.assertEqual("production_release_required", result["error"]["code"])
        self.assertEqual(["FB-CORE"], [item["event_id"] for item in self.learning.list_feedback("PROD")["items"]])
        self.assertEqual([], self.semantic_calls)
        self.assertEqual([], self.learning.list_preferences("PROD")["items"])

    def test_release_revoked_during_feedback_and_promotion_model_wait_blocks_result(self):
        self.observe()
        self.on_semantic_call = self.revoke_release
        result = self.bridge("learning.feedback.execute", {"event_id": "FB-CORE", "service_id": "learning-fixture"})
        self.assertEqual("failed", result["status"])
        self.assertEqual("production_release_required", result["error"]["code"])
        self.assertEqual(1, len(self.semantic_calls))
        self.assertEqual([], self.learning.list_preferences("PROD")["items"])
        self.restore_release()
        self.on_semantic_call = None
        replay = self.bridge("learning.feedback.resume", {"event_id": "FB-CORE", "service_id": "learning-fixture"})
        self.assertEqual("ok", replay["status"])
        self.assertEqual("awaiting_external", replay["data"]["status"])
        self.assertEqual(1, len(self.semantic_calls))
        self.observe("FB-REVIEW")
        preference = self.capture("FB-REVIEW")
        self.on_semantic_call = self.revoke_release
        review = self.bridge("learning.preference.review", {"hypothesis_id": preference["hypothesis_id"],
                              "expected_version": preference["version"], "service_id": "learning-fixture"})
        self.assertEqual("failed", review["status"])
        self.assertEqual("production_release_required", review["error"]["code"])
        current = self.learning.get_preference("PROD", hypothesis_id=preference["hypothesis_id"])
        self.assertEqual("candidate", current["state"])
        self.assertIsNone(current["activation_review"]["judgment"])

    def test_model_reader_cannot_be_relabelled_or_used_for_preference_activation(self):
        from learning.learning_store import LearningStore
        advisory = self.observe("FB-MODEL", source_type="model_reader", source_id="reader-model")
        self.assertEqual("advisory", advisory["status"])
        self.assertIsNone(advisory["semantic_call"])
        denied = self.bridge("learning.feedback.execute", {"event_id": "FB-MODEL", "service_id": "learning-fixture"})
        self.assertEqual("failed", denied["status"])
        relabelled = self.bridge("learning.feedback.observe", self.observe_args("FB-MODEL", source_id="reader-model"))
        self.assertEqual("failed", relabelled["status"])
        self.assertEqual("model_reader", self.learning.get_feedback("PROD", event_id="FB-MODEL")["source_type"])
        self.assertEqual([], self.semantic_calls)
        self.observe("FB-HUMAN")
        preference = self.capture("FB-HUMAN")
        reviewed = self.bridge("learning.preference.review", {"hypothesis_id": preference["hypothesis_id"],
                                "expected_version": preference["version"], "service_id": "learning-fixture"})
        self.assertEqual("ok", reviewed["status"], reviewed)
        # Simulate contaminated imported evidence after a prior passing review.
        # Neither the bridge nor Core may treat that old pass as human consent.
        with LearningStore(self.ops.project_learning().learning_db).transaction() as conn:
            row = conn.execute("SELECT evidence_id,payload_json FROM preference_evidence WHERE evidence_id=?", (preference["evidence_ids"][0],)).fetchone()
            payload = json.loads(row["payload_json"])
            payload["feedback_event_ref"] = "FB-MODEL"
            conn.execute("UPDATE preference_evidence SET payload_json=? WHERE evidence_id=?", (canonical_json(payload), row["evidence_id"]))
        activated = self.bridge("learning.preference.activate", {"hypothesis_id": preference["hypothesis_id"],
                                 "expected_version": preference["version"], "user_authorized": True,
                                 "authorized_by": "fixture-author", "idempotency_key": "forbidden-model-activation"})
        self.assertEqual("failed", activated["status"])
        self.assertEqual("human_feedback_required", activated["error"]["code"])
        self.assertEqual("candidate", self.learning.get_preference("PROD", hypothesis_id=preference["hypothesis_id"])["state"])

    def test_bridge_executes_original_prepared_job_and_resume_reuses_result(self):
        from harness.semantic_workers.semantic_worker_router import worker_job_view
        from learning.learning_store import LearningStore
        self.observe()
        database = LearningStore(self.ops.project_learning().learning_db)
        with database.connect() as conn:
            before = conn.execute("SELECT job_json FROM project_learning_calls WHERE call_key='feedback:FB-CORE'").fetchone()[0]
        prepared = json.loads(before)
        caller_result = {"judgment": {"statement": "caller must not overwrite the prepared evidence"}}
        executed = self.bridge("learning.feedback.execute", {"event_id": "FB-CORE", "service_id": "learning-fixture",
                                                             "semantic_result": caller_result, "session_id": "FORGED"})
        self.assertEqual("ok", executed["status"], executed)
        self.assertEqual("persisted", executed["data"]["status"])
        self.assertEqual(1, len(self.semantic_calls))
        agent_job = self.semantic_calls[0]
        self.assertEqual(worker_job_view(prepared), agent_job.context[0]["registered_semantic_job"])
        self.assertEqual((self.run["session_id"], self.run["run_id"], "LEARN"), (agent_job.session_id, agent_job.run_id, agent_job.task_mode))
        resumed = self.bridge("learning.feedback.resume", {"event_id": "FB-CORE", "service_id": "learning-fixture"})
        self.assertEqual("ok", resumed["status"])
        self.assertEqual("persisted", resumed["data"]["status"])
        self.assertFalse(resumed["data"]["model_execution"])
        self.assertEqual(1, len(self.semantic_calls))
        with database.connect() as conn:
            self.assertEqual(before, conn.execute("SELECT job_json FROM project_learning_calls WHERE call_key='feedback:FB-CORE'").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM preference_evidence").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM preference_hypotheses WHERE state='candidate'").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
