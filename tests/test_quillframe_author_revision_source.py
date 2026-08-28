"""Synthetic Core revision evidence tests; no live literary acceptance claims."""
from __future__ import annotations

import json
import unittest
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

from core_operations import CoreOperations, OperationError
from harness.context_runtime import fingerprint
from persistence.quillframe_sqlite import canonical_json
from production_runtime import ProductionRunExecutor
from production_runtime.contracts import assert_secret_free
from production_runtime.repair_source import load_repair_source
from production_runtime.workflow_service import NovelWorkflowService
from harness.semantic_workers.registered_contract_binding import validate_registered_job
from tests import test_quillframe_production_runtime as fixtures


REVISION_INSTRUCTION = "Make the synthetic scene's choices and reactions legible while preserving its events."
FAILED_REVISION_TEXT = "The first synthetic author revision still has a blocking defect."
CONTINUED_REVISION_TEXT = "The next synthetic revision resolves the remaining fixture defect."


class RevisionChainFixtureRuntime(fixtures.RepairFixtureRuntime):
    """Distinct fake manuscripts make old-prose isolation assertions meaningful."""

    def __init__(self, *, candidate_text, audit_fails=False):
        super().__init__(generation_mode="fresh_realization", repair_audit_fails=audit_fails)
        self.candidate_text = candidate_text

    def run(self, job, *, cancellation=None):
        result = super().run(job, cancellation=cancellation)
        if job.runtime_role == "surface_realization":
            judgment = json.loads(result.final_text)
            judgment["text"] = self.candidate_text
            return replace(result, final_text=json.dumps(judgment))
        return result


class AuthorRevisionSourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ProductionRuntimeTests(
            methodName="test_full_graph_uses_frozen_context_and_real_external_independent_boundary"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.store = self.fixture.store
        self.ops = CoreOperations(self.store)

    def release(self, *, revised=False):
        if revised:
            fake, runtime, parent, run_id = self.fixture.repair_fixture()
            handoff = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True,
                                      independent_provenance=fixtures.PROVENANCE)
        else:
            fake = fixtures.FakeAgentRuntime()
            runtime = ProductionRunExecutor(self.store, fake)
            run_id = self.fixture.start()
            handoff = self.fixture.execute_to_handoff(runtime, run_id)
            parent = None
        self.assertEqual("awaiting_external", handoff["status"])
        result = self.fixture.submit(runtime, run_id)
        self.assertEqual("completed", result["status"])
        return fake, runtime, run_id, result["candidate"], parent

    def request(self, candidate, *, instruction=REVISION_INSTRUCTION, idempotency_key="author-revision-fixture"):
        return self.ops.request_candidate_revision(
            "PROD", candidate_id=candidate["candidate_id"],
            candidate_fingerprint=candidate["candidate_fingerprint"],
            revision_request={"instruction": instruction}, authorized_by="user",
            authorization={"intent": "request_revision"}, idempotency_key=idempotency_key,
        )

    def start_revision(self, request, **extra):
        payload = {**request["next_action"]["payload"], "chapter_id": "CH001", **extra}
        return self.ops.start_author_run("PROD", task_mode="REVISE", target_ref="DOC-1", payload=payload)["run_id"]

    def execute_fresh_revision(self, run_id, *, candidate_text, audit_fails=False):
        NovelWorkflowService(self.store).start(project_id="PROD", run_id=run_id, chapter_id="CH001", author_profile="guided")
        fake = RevisionChainFixtureRuntime(candidate_text=candidate_text, audit_fails=audit_fails)
        runtime = ProductionRunExecutor(self.store, fake)
        result = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True,
                                 independent_provenance=fixtures.PROVENANCE)
        return fake, runtime, result

    def continue_failed_author_revision(self, *, instruction=REVISION_INSTRUCTION):
        _, _, _, candidate, _ = self.release()
        request = self.request(candidate, instruction=instruction)
        first_id = self.start_revision(request)
        first_fake, first_runtime, failed = self.execute_fresh_revision(
            first_id, candidate_text=FAILED_REVISION_TEXT, audit_fails=True,
        )
        self.assertEqual("failed_gate", failed["status"])
        first_editor = next(job for job in first_fake.calls if job.runtime_role == "registered_repair_editor")
        self.assertIn(instruction, json.dumps(first_editor.context))
        source_ref = first_runtime.status("PROD", first_id)["repair_source"]
        second_id = self.ops.start_author_run(
            "PROD", task_mode="REVISE", target_ref="DOC-1",
            payload={"chapter_id": "CH001", "repair_source": source_ref},
        )["run_id"]
        fake, runtime, result = self.execute_fresh_revision(second_id, candidate_text=CONTINUED_REVISION_TEXT)
        self.assertEqual("awaiting_external", result["status"])
        return request, fake, runtime, second_id

    def assert_revision_input_boundaries(self, fake, run_id, *, requests, candidate_text, old_prose):
        expected_instructions = [request["revision_request"]["instruction"] for request in requests]
        expected_refs = [["author-revision:" + fingerprint(request)] for request in requests]
        envelopes = {}
        for role in ("registered_repair_editor", "event_first_raw_draft", "surface_realization", "registered_repair_comparison"):
            job = next(job for job in fake.calls if job.runtime_role == role)
            if role in {"event_first_raw_draft", "surface_realization"}:
                envelope = job.context[0]["repair"]["objective_envelope"]
                writer_input = json.dumps({"context": job.context, "instruction": job.instruction})
                for private in (*old_prose, "PRIVATE SYNTHETIC DIAGNOSIS", "PRIVATE EDITOR TRAJECTORY"):
                    self.assertNotIn(private, writer_input, role)
            else:
                payload = job.context[0]["registered_semantic_job"]["input"]["payload"]
                envelope = (payload if role == "registered_repair_editor" else payload["repair_context"])["objective_envelope"]
            objectives = [item for item in envelope["objective_items"] if item["category"] == "user_direction"
                          and any(ref.startswith("author-revision:") for ref in item["source_refs"])]
            self.assertEqual(expected_instructions, [item["statement"] for item in objectives], role)
            self.assertEqual(expected_refs, [item["source_refs"] for item in objectives], role)
            self.assertTrue(all(item["id"] in envelope["must_preserve"] for item in objectives), role)
            self.assertIn("later author revisions take precedence on conflict", envelope["authority_cutoff"], role)
            self.assertFalse(envelope["derived_from_rejected_realization"])
            envelopes[role] = envelope
        reference = envelopes["registered_repair_editor"]
        self.assertTrue(all(envelope == reference for envelope in envelopes.values()))

        reader = next(job for job in fake.calls if job.runtime_role == "registered_reader_engagement")
        packet = fixtures.frozen_packet(self.store, run_id)
        reader_payload = reader.context[0]["registered_semantic_job"]["input"]["payload"]
        for payload in (reader_payload, packet["job"]["input"]["payload"]):
            self.assertEqual(candidate_text, payload["candidate_text"])
        for label, value in (("Reader", {"context": reader.context, "instruction": reader.instruction}), ("independent", packet)):
            serialized = json.dumps(value)
            for private in (*expected_instructions, *old_prose, "PRIVATE SYNTHETIC DIAGNOSIS", "PRIVATE EDITOR TRAJECTORY"):
                self.assertNotIn(private, serialized, label)
        return reference

    def test_internal_repair_keeps_author_revision_objective_without_leaking_it_to_reviewers(self):
        request, fake, runtime, run_id = self.continue_failed_author_revision()
        envelope = self.assert_revision_input_boundaries(
            fake, run_id, requests=[request], candidate_text=CONTINUED_REVISION_TEXT,
            old_prose=[fixtures.PRE_RELEASE_MANUSCRIPT, FAILED_REVISION_TEXT],
        )
        self.assertIsNone(envelope["supersedes_fingerprint"])
        self.assertIsNone(envelope["change_authority_ref"])
        plan = runtime._latest_checkpoint("PROD", run_id, "production_repair_plan")["generation_plan"]
        self.assertTrue(plan["policy"]["candidate_rejected"])
        self.assertFalse(plan["policy"]["author_revision_requested"])

    def test_later_author_revision_retains_ordered_requests_and_explicit_conflict_precedence(self):
        first_instruction = "Use first-person narration in the synthetic revision; preserve the original events."
        first_request, _, runtime, source_id = self.continue_failed_author_revision(instruction=first_instruction)
        previous = runtime._latest_checkpoint("PROD", source_id, "production_repair_plan")["generation_plan"]["objective_envelope"]
        completed = self.fixture.submit(runtime, source_id)
        self.assertEqual("completed", completed["status"])
        next_instruction = "Use third-person narration instead of the earlier first-person direction; preserve the original events."
        next_request = self.request(completed["candidate"], instruction=next_instruction,
                                    idempotency_key="later-author-revision-fixture")
        run_id = self.start_revision(next_request)
        next_text = "A later synthetic manuscript follows the new author direction."
        fake, _, result = self.execute_fresh_revision(run_id, candidate_text=next_text)
        self.assertEqual("awaiting_external", result["status"])
        envelope = self.assert_revision_input_boundaries(
            fake, run_id, requests=[first_request, next_request], candidate_text=next_text,
            old_prose=[fixtures.PRE_RELEASE_MANUSCRIPT, FAILED_REVISION_TEXT, CONTINUED_REVISION_TEXT],
        )
        self.assertEqual(previous["fingerprint"], envelope["supersedes_fingerprint"])
        self.assertEqual("author-revision:" + fingerprint(next_request), envelope["change_authority_ref"])
        self.assertEqual(previous, runtime._latest_checkpoint("PROD", source_id, "production_repair_plan")["generation_plan"]["objective_envelope"])

    def test_authorized_released_draft_freezes_safe_instruction_without_rewriting_old_pass(self):
        _, runtime, source_id, candidate, _ = self.release()
        before = runtime._latest_checkpoint("PROD", source_id, "production_qualified_candidate")
        request = self.request(candidate)
        run_id = self.start_revision(request)
        with self.store.open_project("PROD") as conn:
            source = load_repair_source(conn, run_id)
            old_candidate = dict(conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate["candidate_id"],)).fetchone())
        assert_secret_free(source, label="synthetic revision source")
        self.assertEqual("author_revision", source["source_kind"])
        self.assertEqual(REVISION_INSTRUCTION, source["author_revision_request"]["revision_request"]["instruction"])
        self.assertNotIn("authorization", source["author_revision_request"])
        self.assertEqual(fingerprint(request), source["author_revision_request_fingerprint"])
        self.assertEqual("review_draft", old_candidate["status"])
        self.assertEqual(before, runtime._latest_checkpoint("PROD", source_id, "production_qualified_candidate"))
        self.assertEqual("pass", source["reader_binding"]["result"]["judgment"]["result"])
        self.assertEqual("qualified_for_independent", source["qualification_receipt"]["qualification_status"])

    def test_fresh_author_revision_uses_new_review_and_no_old_prose_in_writer_or_reader(self):
        _, original_runtime, source_id, candidate, _ = self.release()
        before = original_runtime._latest_checkpoint("PROD", source_id, "production_qualified_candidate")
        run_id = self.start_revision(self.request(candidate), reader_positioning=fixtures.READER_POSITIONING)
        NovelWorkflowService(self.store).start(project_id="PROD", run_id=run_id, chapter_id="CH001", author_profile="guided")
        fake = fixtures.RepairFixtureRuntime(generation_mode="fresh_realization")
        runtime = ProductionRunExecutor(self.store, fake)
        result = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True,
                                 independent_provenance=fixtures.PROVENANCE)
        self.assertEqual("awaiting_external", result["status"])
        plan = runtime._latest_checkpoint("PROD", run_id, "production_repair_plan")["generation_plan"]
        self.assertEqual("fresh_realization", plan["policy"]["generation_mode"])
        self.assertFalse(plan["policy"]["candidate_rejected"])
        self.assertTrue(plan["policy"]["author_revision_requested"])
        editor = next(job for job in fake.calls if job.runtime_role == "registered_repair_editor")
        self.assertIn(REVISION_INSTRUCTION, json.dumps(editor.context))
        for role in ("event_first_raw_draft", "surface_realization", "registered_reader_engagement"):
            job = next(job for job in fake.calls if job.runtime_role == role)
            self.assertNotIn(fixtures.PRE_RELEASE_MANUSCRIPT, json.dumps(job.context))
        packet = fixtures.frozen_packet(self.store, run_id)
        self.assertNotIn(fixtures.PRE_RELEASE_MANUSCRIPT, json.dumps(packet))
        self.assertEqual(fixtures.READER_POSITIONING["genre_profile"], packet["job"]["input"]["payload"]["genre_profile"])
        self.assertNotEqual(fixtures.frozen_packet(self.store, source_id)["relay_nonce"], packet["relay_nonce"])
        completed = self.fixture.submit(runtime, run_id)
        self.assertEqual("completed", completed["status"])
        self.assertNotEqual(candidate["candidate_id"], completed["candidate"]["candidate_id"])
        self.assertFalse(completed["accepted"])
        self.assertFalse(completed["settled"])
        self.assertEqual(before, original_runtime._latest_checkpoint("PROD", source_id, "production_qualified_candidate"))

    def test_missing_or_forged_revision_receipt_blocks_before_run_or_model(self):
        fake, _, source_id, candidate, _ = self.release()
        request = self.request(candidate)
        before_calls = len(fake.calls)
        with self.store.open_project("PROD") as conn:
            before_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            row = conn.execute("SELECT receipt_id,payload_json FROM receipts WHERE run_id=? AND receipt_kind='candidate_revision_request'", (source_id,)).fetchone()
            original = row["payload_json"]
        variants = []
        for field in ("authorization", "candidate_fingerprint", "request_fingerprint"):
            changed = json.loads(original)
            if field == "authorization":
                changed.pop(field)
            else:
                changed[field] = "sha256:" + "0" * 64
            variants.append(changed)
        for variant in variants:
            with self.subTest(variant=variant.get("request_fingerprint")):
                with self.store.open_project("PROD") as conn:
                    conn.execute("UPDATE receipts SET payload_json=? WHERE receipt_id=?", (canonical_json(variant), row["receipt_id"]))
                    conn.commit()
                with self.assertRaises(OperationError):
                    self.start_revision(request)
        with self.store.open_project("PROD") as conn:
            conn.execute("DELETE FROM receipts WHERE receipt_id=?", (row["receipt_id"],))
            conn.commit()
        with self.assertRaises(OperationError):
            self.start_revision(request)
        with self.store.open_project("PROD") as conn:
            self.assertEqual(before_runs, conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
        self.assertEqual(before_calls, len(fake.calls))

    def test_changed_candidate_or_accepted_state_cannot_be_a_revision_source(self):
        _, _, _, candidate, _ = self.release()
        request = self.request(candidate)
        forged = deepcopy(request)
        forged["next_action"]["payload"]["repair_source"]["expected_candidate_fingerprint"] = "sha256:" + "0" * 64
        with self.assertRaises(OperationError):
            self.start_revision(forged)
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE candidates SET status='accepted' WHERE candidate_id=?", (candidate["candidate_id"],))
            conn.commit()
        with self.assertRaises(OperationError):
            self.start_revision(request)

    def test_current_story_can_change_but_old_frozen_bundle_cannot_be_rewritten(self):
        _, _, source_id, candidate, _ = self.release()
        request = self.request(candidate)
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE characters SET agenda='new author direction' WHERE character_id='CHAR-A'")
            conn.commit()
        run_id = self.start_revision(request)
        fake = fixtures.RepairFixtureRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        NovelWorkflowService(self.store).start(project_id="PROD", run_id=run_id, chapter_id="CH001", author_profile="guided")
        result = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True,
                                 independent_provenance=fixtures.PROVENANCE)
        self.assertEqual("awaiting_external", result["status"])
        with self.store.open_project("PROD") as conn:
            row = conn.execute("SELECT checkpoint_id,state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_context_bundle'", (source_id,)).fetchone()
            bundle = json.loads(row["state_json"])
            bundle["authority"] = True
            conn.execute("UPDATE checkpoints SET state_json=? WHERE checkpoint_id=?", (canonical_json(bundle), row["checkpoint_id"]))
            conn.commit()
        with self.assertRaises(OperationError):
            self.start_revision(request)

    def test_released_revision_rechecks_its_original_parent_evidence(self):
        _, _, _, candidate, parent = self.release(revised=True)
        request = self.request(candidate)
        self.start_revision(request)
        with self.store.open_project("PROD") as conn:
            conn.execute("DELETE FROM production_stage_calls WHERE run_id=? AND runtime_role='registered_reader_engagement'", (parent,))
            conn.commit()
        with self.assertRaises(OperationError):
            self.start_revision(request)

    def test_missing_original_independent_review_blocks_author_run_registration(self):
        fake, _, _, candidate, _ = self.release()
        request = self.request(candidate)
        before_calls = len(fake.calls)
        with self.store.open_project("PROD") as conn:
            before_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            conn.execute("DELETE FROM review_evidence WHERE candidate_id=? AND independent=1", (candidate["candidate_id"],))
            conn.commit()
        with self.assertRaises(OperationError) as caught:
            self.start_revision(request)
        self.assertEqual("repair_source_independent_invalid", caught.exception.code)
        with self.store.open_project("PROD") as conn:
            self.assertEqual(before_runs, conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
        self.assertEqual(before_calls, len(fake.calls))

    def test_historical_quality_v7_parent_chain_is_readable_but_not_new_gate_evidence(self):
        # Build the synthetic historical run under the exact old registry,
        # rather than editing its verdicts, persisted jobs or receipt hashes.
        archive = Path(__file__).resolve().parents[1] / "harness/semantic_workers/contracts/history/quality.v7.json"
        old_registry = json.loads(archive.read_text(encoding="utf-8"))
        router = import_module("harness.semantic_workers.semantic_worker_router")
        original_load = router.load_contract_registry

        def historical_registry(path):
            return deepcopy(old_registry) if Path(path).name == "quality.json" else original_load(path)

        with ExitStack() as stack:
            for name in ("harness.semantic_workers.semantic_worker_router", "semantic_worker_router",
                         "harness.semantic_workers.registered_contract_binding", "registered_contract_binding",
                         "production_runtime.semantic"):
                stack.enter_context(patch.object(import_module(name), "load_contract_registry", historical_registry))
            _, runtime, source_id, candidate, _ = self.release(revised=True)
        old_state = runtime._latest_checkpoint("PROD", source_id, "production_qualified_candidate")
        self.assertEqual("7", old_state["reader_binding"]["job"]["provenance"]["registry_version"])
        self.assertTrue(validate_registered_job(old_state["reader_binding"]["job"]))
        run_id = self.start_revision(self.request(candidate))
        with self.store.open_project("PROD") as conn:
            frozen = load_repair_source(conn, run_id)
        self.assertEqual(old_state["reader_binding"], frozen["reader_binding"])
        self.assertEqual(old_state["qualification_receipt"], frozen["qualification_receipt"])
        self.assertEqual(old_state, runtime._latest_checkpoint("PROD", source_id, "production_qualified_candidate"))


if __name__ == "__main__":
    unittest.main()
