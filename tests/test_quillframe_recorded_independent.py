"""Synthetic local evidence tests; no model or consumer project is used."""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import test_quillframe_production_runtime as fixtures
from test_quillframe_production_runtime import (
    FakeAgentRuntime, ProductionRunExecutor, frozen_packet, native_result, peer_result, project_bridge_receipt,
)
from harness.context_runtime import fingerprint
from harness.semantic_workers.peer_bridge_receipt import validate_receipt, validate_recorded_receipt
from harness.semantic_workers.registered_contract_binding import validate_registered_job
from persistence.quillframe_sqlite import canonical_json
from production_runtime.contracts import ProductionRunError
from production_runtime.recorded_independent import EVIDENCE_KIND, validate_recorded_independent


@contextmanager
def historical_quality_registry():
    """Simulate an old runtime at fixture creation, never rewrite its verdicts."""
    archive = json.loads((ROOT / "harness/semantic_workers/contracts/history/quality.v7.json").read_text(encoding="utf-8"))
    original_path = (ROOT / "harness/semantic_workers/contracts/quality.json").resolve()
    with ExitStack() as stack:
        for name in ("semantic_worker_router", "harness.semantic_workers.semantic_worker_router",
                     "registered_contract_binding", "harness.semantic_workers.registered_contract_binding"):
            module = sys.modules[name]
            original = module.load_contract_registry
            def load(path=None, *, _original=original):
                return deepcopy(archive) if path is not None and Path(path).resolve() == original_path else _original(path)
            stack.enter_context(patch.object(module, "load_contract_registry", side_effect=load))
        yield


class RecordedIndependentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {}
        for name in ("bridge", "native", "bridge_extended", "historic_bridge"):
            fixture = fixtures.NativeIndependentReviewRuntimeTests() if name == "native" else fixtures.ProductionRuntimeTests()
            fixture.setUp()
            cls.addClassCleanup(fixture.tearDown)
            runtime = ProductionRunExecutor(fixture.store, FakeAgentRuntime())
            with ExitStack() as stack:
                if name == "historic_bridge":
                    stack.enter_context(historical_quality_registry())
                run_id = fixture.start_native() if name == "native" else fixture.start()
                if name == "native":
                    fixture.prepare_native(runtime, run_id)
                    claim = fixture.claim_native(runtime)
                    completed = runtime.complete_independent_judgment(
                        "PROD", lease_id=claim["lease_id"], reviewer_session_id=claim["reviewer_session_id"],
                        host_agent_id=claim["host_agent_id"], host_invocation_id=claim["host_invocation_id"],
                        judgment=native_result(claim)["judgment"],
                    )
                else:
                    fixture.execute_to_handoff(runtime, run_id)
                    packet = frozen_packet(fixture.store, run_id)
                    result = peer_result(packet)
                    if name == "bridge_extended":
                        result["execution"] = {"run_reference": packet["relay_nonce"], "transport_note": "synthetic_exact_metadata"}
                    completed = runtime.submit_independent(
                        "PROD", run_id, peer_packet=packet, result=result,
                        independence_receipt=project_bridge_receipt(packet, result),
                    )
            cls.sources[name] = (fixture, runtime, run_id, completed)

    def setUp(self):
        self.conn = None
        self.use_source("bridge")

    def tearDown(self):
        if self.conn is not None:
            self.conn.close()

    def use_source(self, name):
        if self.conn is not None:
            self.conn.close()
        fixture, self.runtime, self.run_id, completed = self.sources[name]
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        with fixture.store.open_project("PROD") as original:
            original.backup(self.conn)
        self.run = dict(self.conn.execute("SELECT * FROM runs WHERE run_id=?", (self.run_id,)).fetchone())
        self.state = json.loads(self.checkpoint("production_qualified_candidate")["state_json"])
        self.release = deepcopy(completed["production_release"])
        self.candidate_id = completed["candidate"]["candidate_id"]

    def checkpoint(self, kind):
        return dict(self.conn.execute("SELECT * FROM checkpoints WHERE run_id=? AND checkpoint_kind=?", (self.run_id, kind)).fetchone())

    def verify(self):
        return validate_recorded_independent(self.conn, run=self.run, state=self.state,
                                            release=self.release, candidate_id=self.candidate_id)

    def test_exact_original_results_and_safe_evidence_projection(self):
        for name in ("bridge", "native", "bridge_extended"):
            with self.subTest(source=name):
                self.use_source(name)
                before = list(self.conn.iterdump())
                proof = json.loads(self.checkpoint(EVIDENCE_KIND)["state_json"])
                evidence = self.verify()
                self.assertEqual("persisted_exact_result", evidence["original_result_source"])
                self.assertEqual(fingerprint(proof["result"]), evidence["result_fingerprint"])
                self.assertEqual(name == "native", evidence["native_lifecycle_fingerprint"] is not None)
                self.assertFalse(evidence["authority"])
                self.assertNotIn(proof["result"]["judgment"]["report"], json.dumps(evidence))
                self.assertNotIn(self.state["candidate_text"], json.dumps(evidence))
                self.assertEqual(before, list(self.conn.iterdump()))
        self.assertEqual("synthetic_exact_metadata", proof["result"]["execution"]["transport_note"])

    def test_trusted_v7_original_release_verifies_without_opening_current_gate(self):
        self.use_source("historic_bridge")
        handoff = json.loads(self.checkpoint("production_independent_handoff")["state_json"])
        proof = json.loads(self.checkpoint(EVIDENCE_KIND)["state_json"])
        self.assertEqual("7", handoff["independent_job"]["input"]["model_contract_version"])
        self.assertEqual("7", self.state["reader_binding"]["job"]["input"]["model_contract_version"])
        self.assertTrue(validate_registered_job(handoff["independent_job"]))
        self.assertTrue(validate_receipt(proof["independence_receipt"], handoff["peer_packet"], proof["result"]))
        self.assertEqual([], validate_recorded_receipt(proof["independence_receipt"], handoff["peer_packet"], proof["result"]))
        self.assertEqual("persisted_exact_result", self.verify()["original_result_source"])

    def test_known_legacy_envelopes_require_exact_original_result_fingerprint(self):
        for name in ("bridge", "native", "historic_bridge"):
            with self.subTest(source=name):
                self.use_source(name)
                original = json.loads(self.checkpoint(EVIDENCE_KIND)["state_json"])["result"]
                self.conn.execute("DELETE FROM checkpoints WHERE run_id=? AND checkpoint_kind=?", (self.run_id, EVIDENCE_KIND))
                evidence = self.verify()
                self.assertEqual("legacy_exact_standard_envelope", evidence["original_result_source"])
                self.assertEqual(fingerprint(original), evidence["result_fingerprint"])
                self.assertIsNone(evidence["exact_result_checkpoint_fingerprint"])

    def test_unknown_legacy_result_metadata_is_not_guessed_from_summary(self):
        self.use_source("bridge_extended")
        self.conn.execute("DELETE FROM checkpoints WHERE run_id=? AND checkpoint_kind=?", (self.run_id, EVIDENCE_KIND))
        with self.assertRaisesRegex(ProductionRunError, "cannot be recovered"):
            self.verify()

    def test_changed_full_result_cannot_fall_back_to_legacy_projection(self):
        row = self.checkpoint(EVIDENCE_KIND)
        value = json.loads(row["state_json"])
        value["result"]["judgment"]["report"] = "Synthetic replacement."
        value["evidence_fingerprint"] = fingerprint({key: child for key, child in value.items() if key != "evidence_fingerprint"})
        self.conn.execute("UPDATE checkpoints SET state_json=?,artifact_fingerprint=? WHERE checkpoint_id=?",
                          (canonical_json(value), value["evidence_fingerprint"], row["checkpoint_id"]))
        with self.assertRaisesRegex(ProductionRunError, "differs from its original receipt"):
            self.verify()

    def test_original_handoff_review_attempt_and_native_lifecycle_cannot_be_omitted(self):
        mutations = (
            ("bridge", "DELETE FROM checkpoints WHERE checkpoint_kind='production_independent_handoff'"),
            ("bridge", "DELETE FROM review_evidence"),
            ("bridge", "DELETE FROM independent_review_attempts"),
            ("native", "DELETE FROM independent_review_leases"),
            ("native", "DELETE FROM independent_review_lifecycle_events WHERE event_kind='claimed'"),
        )
        for name, sql in mutations:
            with self.subTest(source=name, mutation=sql):
                self.use_source(name)
                self.conn.execute(sql)
                with self.assertRaises(ProductionRunError):
                    self.verify()

    def test_duplicate_handoff_is_not_resolved_by_latest_row(self):
        row = self.checkpoint("production_independent_handoff")
        row["checkpoint_id"] = "synthetic-ambiguous-handoff"
        self.conn.execute("INSERT INTO checkpoints(" + ",".join(row) + ") VALUES(" + ",".join("?" for _ in row) + ")", list(row.values()))
        with self.assertRaisesRegex(ProductionRunError, "one original independent handoff"):
            self.verify()

    def test_candidate_qualification_and_packet_bytes_cannot_be_replaced(self):
        for field in ("candidate", "qualification", "packet_bytes"):
            with self.subTest(field=field):
                self.use_source("bridge")
                row = self.checkpoint("production_independent_handoff")
                handoff = json.loads(row["state_json"])
                if field == "candidate":
                    handoff["independent_job"]["input"]["payload"]["candidate_text"] = "Synthetic different prose."
                elif field == "qualification":
                    handoff["qualification_receipt"]["receipt_fingerprint"] = "sha256:" + "e" * 64
                else:
                    handoff["peer_packet_bytes"] += " "
                self.conn.execute("UPDATE checkpoints SET state_json=? WHERE checkpoint_id=?", (canonical_json(handoff), row["checkpoint_id"]))
                with self.assertRaises(ProductionRunError):
                    self.verify()

    def test_stale_review_and_changed_original_judgment_are_rejected(self):
        for defect in ("stale", "judgment", "fingerprint"):
            with self.subTest(defect=defect):
                self.use_source("bridge")
                row = self.conn.execute("SELECT * FROM review_evidence WHERE candidate_id=?", (self.candidate_id,)).fetchone()
                if defect == "stale":
                    self.conn.execute("UPDATE review_evidence SET stale=1")
                elif defect == "fingerprint":
                    self.conn.execute("UPDATE review_evidence SET reviewer_fingerprint=?", ("sha256:" + "e" * 64,))
                else:
                    review = json.loads(row["result_json"])
                    review["judgment"]["result"] = "fail"
                    self.conn.execute("UPDATE review_evidence SET result_json=?", (canonical_json(review),))
                with self.assertRaises(ProductionRunError):
                    self.verify()

    def test_rehashed_lifecycle_payload_cannot_change_host_identity(self):
        self.use_source("native")
        row = dict(self.conn.execute("SELECT * FROM independent_review_lifecycle_events WHERE event_kind='claimed'").fetchone())
        payload = json.loads(row["payload_json"])
        payload["host_invocation_id"] = "synthetic-other-host"
        event = {key: row[key] for key in ("event_id", "lease_id", "run_id", "event_kind", "created_at")}
        event["payload"] = payload
        self.conn.execute("UPDATE independent_review_lifecycle_events SET payload_json=?,event_fingerprint=? WHERE event_id=?",
                          (canonical_json(payload), fingerprint(event), row["event_id"]))
        with self.assertRaisesRegex(ProductionRunError, "lifecycle event changed"):
            self.verify()

    def test_changed_readiness_and_terminal_submission_binding_are_rejected(self):
        for defect in ("readiness", "terminal_evidence", "terminal_response"):
            with self.subTest(defect=defect):
                self.use_source("bridge")
                if defect == "readiness":
                    row = self.conn.execute("SELECT result_json FROM review_evidence").fetchone()
                    review = json.loads(row[0])
                    review["production_readiness"]["gates"][0]["status"] = "fail"
                    self.conn.execute("UPDATE review_evidence SET result_json=?", (canonical_json(review),))
                elif defect == "terminal_evidence":
                    self.conn.execute("UPDATE independent_review_attempts SET terminal_evidence_fingerprint=?", ("sha256:" + "f" * 64,))
                else:
                    self.conn.execute("UPDATE independent_review_attempts SET terminal_response_fingerprint=?", ("sha256:" + "f" * 64,))
                with self.assertRaises(ProductionRunError):
                    self.verify()

    def test_private_checkpoint_is_not_in_public_status(self):
        fixture, runtime, run_id, _ = self.sources["bridge_extended"]
        encoded = json.dumps(runtime.status("PROD", run_id))
        self.assertNotIn("synthetic_exact_metadata", encoded)
        self.assertNotIn("production_independent_evidence", encoded)

    def test_exact_result_checkpoint_replay_is_fenced_before_any_write(self):
        fixture, runtime, run_id, _ = self.sources["bridge"]
        with fixture.store.open_project("PROD") as conn:
            before = [tuple(row) for row in conn.execute("SELECT * FROM checkpoints WHERE checkpoint_kind=?", (EVIDENCE_KIND,))]
            proof = json.loads(before[0][3])
            handoff = json.loads(conn.execute("SELECT state_json FROM checkpoints WHERE checkpoint_kind='production_independent_handoff'").fetchone()[0])
        calls = []
        def lost_owner(conn):
            calls.append(conn.in_transaction)
            raise ProductionRunError("independent_processing_owner_lost", "synthetic expired owner")
        with self.assertRaisesRegex(ProductionRunError, "synthetic expired owner"):
            runtime._persist_independent_evidence(
                "PROD", run_id, handoff=handoff, result=proof["result"], independence_receipt=proof["independence_receipt"],
                submission_evidence_fingerprint=proof["submission_evidence_fingerprint"], effect_guard=lost_owner,
            )
        self.assertEqual([True], calls)
        with fixture.store.open_project("PROD") as conn:
            after = [tuple(row) for row in conn.execute("SELECT * FROM checkpoints WHERE checkpoint_kind=?", (EVIDENCE_KIND,))]
        self.assertEqual(before, after)

    def test_invalid_submission_cannot_persist_but_valid_fail_keeps_exact_result(self):
        fixture = fixtures.ProductionRuntimeTests()
        fixture.setUp()
        try:
            runtime = ProductionRunExecutor(fixture.store, FakeAgentRuntime())
            run_id = fixture.start()
            fixture.execute_to_handoff(runtime, run_id)
            packet = frozen_packet(fixture.store, run_id)
            result = peer_result(packet, "fail")
            result["execution"] = {"run_reference": packet["relay_nonce"], "transport_note": "synthetic_fail_metadata"}
            receipt = project_bridge_receipt(packet, result)
            invalid = deepcopy(result)
            invalid["input_fingerprint"] = "sha256:" + "d" * 64
            with self.assertRaises(ProductionRunError):
                runtime.submit_independent("PROD", run_id, peer_packet=packet, result=invalid, independence_receipt=receipt)
            with fixture.store.open_project("PROD") as conn:
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM checkpoints WHERE checkpoint_kind=?", (EVIDENCE_KIND,)).fetchone()[0])
            failed = runtime.submit_independent("PROD", run_id, peer_packet=packet, result=result, independence_receipt=receipt)
            self.assertEqual("failed_gate", failed["status"])
            with fixture.store.open_project("PROD") as conn:
                proof = json.loads(conn.execute("SELECT state_json FROM checkpoints WHERE checkpoint_kind=?", (EVIDENCE_KIND,)).fetchone()[0])
                self.assertEqual(result, proof["result"])
                self.assertEqual(receipt, proof["independence_receipt"])
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0])
        finally:
            fixture.tearDown()

    def test_completed_candidate_crash_recovery_preserves_verifiable_original_evidence(self):
        fixture = fixtures.ProductionRuntimeTests()
        fixture.setUp()
        try:
            runtime = ProductionRunExecutor(fixture.store, FakeAgentRuntime())
            run_id = fixture.start()
            fixture.execute_to_handoff(runtime, run_id)
            packet = frozen_packet(fixture.store, run_id)
            result = peer_result(packet)
            receipt = project_bridge_receipt(packet, result)
            with patch("production_runtime.runtime.IndependentReviewRepository.terminalize_attempt", side_effect=RuntimeError("synthetic terminal crash")):
                with self.assertRaisesRegex(RuntimeError, "synthetic terminal crash"):
                    runtime.submit_independent("PROD", run_id, peer_packet=packet, result=result, independence_receipt=receipt)
            completed = runtime.submit_independent("PROD", run_id, peer_packet=packet, result=result, independence_receipt=receipt)
            self.assertTrue(completed["replayed"])
            self.assertNotIn("production_readiness", completed)
            with fixture.store.open_project("PROD") as conn:
                run = dict(conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())
                state = json.loads(conn.execute("SELECT state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_qualified_candidate'", (run_id,)).fetchone()[0])
                evidence = validate_recorded_independent(conn, run=run, state=state, release=completed["production_release"],
                                                         candidate_id=completed["candidate"]["candidate_id"])
                self.assertEqual(fingerprint(result), evidence["result_fingerprint"])
                self.assertEqual("persisted_exact_result", evidence["original_result_source"])
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
