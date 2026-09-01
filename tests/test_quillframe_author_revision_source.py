"""Synthetic Core revision evidence tests; no live literary acceptance claims."""
from __future__ import annotations

import json
import hashlib
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from core_operations import CoreOperations, OperationError
from harness.context_runtime import fingerprint
from persistence.quillframe_sqlite import canonical_json, fingerprint_text, now_iso
from production_runtime import ProductionRunExecutor
from production_runtime.confirmed_prefix import build_reference as build_confirmed_prefix_reference
from production_runtime.contracts import ProductionRunError, assert_secret_free
from production_runtime.repair_source import load_repair_source
from production_runtime.workflow_service import NovelWorkflowService
from tests import test_quillframe_production_runtime as fixtures


REVISION_INSTRUCTION = "Make the synthetic scene's choices and reactions legible while preserving its events."
FAILED_REVISION_TEXT = "The first synthetic author revision still has a blocking defect."
CONTINUED_REVISION_TEXT = "The next synthetic revision resolves the remaining fixture defect."


class RevisionChainFixtureRuntime(fixtures.RepairFixtureRuntime):
    """Distinct fake manuscripts make old-prose isolation assertions meaningful."""

    def __init__(
        self, *, candidate_text, audit_fails=False, generation_mode="fresh_realization",
        malformed_self_audit=False, bad_narrative_evidence=False,
    ):
        super().__init__(generation_mode=generation_mode, repair_audit_fails=audit_fails)
        self.candidate_text = candidate_text
        self.malformed_self_audit = malformed_self_audit
        self.bad_narrative_evidence = bad_narrative_evidence

    def run(self, job, *, cancellation=None):
        result = super().run(job, cancellation=cancellation)
        if job.runtime_role == "surface_realization":
            judgment = json.loads(result.final_text)
            judgment["text"] = self.candidate_text
            return replace(result, final_text=json.dumps(judgment))
        if job.runtime_role == "registered_candidate_self_audit" and self.malformed_self_audit:
            return replace(result, final_text='{"result":"pass","report":"truncated"')
        if job.runtime_role == "registered_narrative_state" and self.bad_narrative_evidence:
            judgment = json.loads(result.final_text)
            if not judgment["changes"]:
                judgment["changes"] = [{
                    "entity_type": "world",
                    "entity_ref": "local:unsupported",
                    "fields": {
                        "entity_type": "fixture",
                        "name": "Unsupported",
                        "truth": {},
                    },
                    "evidence_quote": "not present in the candidate",
                }]
            else:
                for change in judgment["changes"]:
                    change["evidence_quote"] = "not present in the candidate"
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
        for role in ("registered_repair_editor", "registered_repair_comparison"):
            job = next(job for job in fake.calls if job.runtime_role == role)
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

        surface = next(job for job in fake.calls if job.runtime_role == "surface_realization")
        pack = surface.context[0]["writer_pack"]
        self.assertEqual(
            fingerprint({key: value for key, value in pack.items() if key != "writer_pack_fingerprint"}),
            pack["writer_pack_fingerprint"],
        )
        self.assertEqual(reference["fingerprint"], pack["repair_context"]["objective_envelope_fingerprint"])
        writer_objectives = pack["author_objectives"]
        revision_objectives = [
            item for item in writer_objectives["items"]
            if any(ref.startswith("author-revision:") for ref in item["source_refs"])
        ]
        self.assertEqual(expected_instructions, [item["statement"] for item in revision_objectives])
        self.assertEqual(expected_refs, [item["source_refs"] for item in revision_objectives])
        self.assertEqual(
            fingerprint({key: value for key, value in writer_objectives.items() if key != "objectives_fingerprint"}),
            writer_objectives["objectives_fingerprint"],
        )
        writer_input = json.dumps({"context": surface.context, "instruction": surface.instruction})
        for private in (*old_prose, "PRIVATE SYNTHETIC DIAGNOSIS", "PRIVATE EDITOR TRAJECTORY"):
            self.assertNotIn(private, writer_input, "Surface Writer")

        reader = next(job for job in fake.calls if job.runtime_role == "registered_reader_engagement")
        audit = next(job for job in fake.calls if job.runtime_role == "registered_candidate_self_audit")
        packet = fixtures.frozen_packet(self.store, run_id)
        reader_payload = reader.context[0]["registered_semantic_job"]["input"]["payload"]
        audit_payload = audit.context[0]["registered_semantic_job"]["input"]["payload"]
        independent_payload = packet["job"]["input"]["payload"]
        for payload in (reader_payload, audit_payload, independent_payload):
            self.assertEqual(candidate_text, payload["candidate_text"])
        self.assertEqual(writer_objectives, audit_payload["author_objectives"])
        self.assertEqual(writer_objectives, independent_payload["author_objectives"])
        for label, value in (("Reader", {"context": reader.context, "instruction": reader.instruction}),):
            serialized = json.dumps(value)
            for private in (*expected_instructions, *old_prose, "PRIVATE SYNTHETIC DIAGNOSIS", "PRIVATE EDITOR TRAJECTORY"):
                self.assertNotIn(private, serialized, label)
        independent_serialized = json.dumps(packet)
        for private in (*old_prose, "PRIVATE SYNTHETIC DIAGNOSIS", "PRIVATE EDITOR TRAJECTORY"):
            self.assertNotIn(private, independent_serialized, "independent")
        return reference

    def test_local_author_revision_reuses_upstream_checkpoints_and_calls_only_fresh_prose_gates(self):
        _, _, _, candidate, _ = self.release()
        request = self.request(candidate, instruction=REVISION_INSTRUCTION,
                               idempotency_key="local-author-revision-fixture")
        run_id = self.start_revision(request)
        NovelWorkflowService(self.store).start(
            project_id="PROD", run_id=run_id, chapter_id="CH001", author_profile="guided",
        )
        fake = RevisionChainFixtureRuntime(
            candidate_text=CONTINUED_REVISION_TEXT, generation_mode="local_or_bounded_repair",
        )
        runtime = ProductionRunExecutor(self.store, fake)
        result = runtime.execute(
            "PROD", run_id, service_id="svc", inherit_repair_request=True,
            independent_provenance=fixtures.PROVENANCE,
        )
        self.assertEqual("awaiting_external", result["status"])
        roles = [job.runtime_role for job in fake.calls if job.run_id == run_id]
        self.assertEqual(8, len(roles))
        self.assertEqual({
            "registered_repair_editor", "surface_realization", "registered_reader_engagement",
            "continuity", "registered_candidate_self_audit", "registered_reader_expectations",
            "registered_narrative_state", "registered_repair_comparison",
        }, set(roles))
        self.assertFalse(any(role in roles for role in (
            "context_selector", "story_canon_preflight", "character_state_prepare",
            "registered_character_action", "registered_scene_resolution",
            "registered_scene_projection", "registered_reader_pressure", "event_first_raw_draft",
        )))
        surface_job = next(job for job in fake.calls if job.runtime_role == "surface_realization")
        writer_pack = surface_job.context[0]["writer_pack"]
        repair_context = writer_pack["repair_context"]
        self.assertNotIn("authority_constraints", repair_context)
        bindings = repair_context["authority_constraint_bindings"]
        self.assertTrue(bindings)
        self.assertTrue(all(
            "statement" not in item
            and item["statement_fingerprint"].startswith("sha256:")
            and item["statement_utf8_bytes"] > 0
            for item in bindings
        ))
        plan = runtime._latest_checkpoint("PROD", run_id, "production_repair_plan")["generation_plan"]
        envelope = plan["objective_envelope"]
        self.assertEqual(envelope["fingerprint"], repair_context["objective_envelope_fingerprint"])
        self.assertNotIn("objective_envelope", repair_context)
        self.assertNotIn(canonical_json(envelope), surface_job.instruction)
        self.assertEqual(envelope["fingerprint"], writer_pack["author_objectives"]["source_fingerprint"])
        bounded = repair_context["bounded_repair_evidence"]
        self.assertNotIn("candidate_text", bounded)
        self.assertEqual(candidate["candidate_fingerprint"], bounded["candidate_fingerprint"])
        self.assertFalse(bounded["full_candidate_visible"])
        self.assertTrue(bounded["bounded_edit_windows"])
        self.assertTrue(all(
            window["edit_window_fingerprint"] == fingerprint_text(window["edit_window_quote"])
            for window in bounded["bounded_edit_windows"]
        ))
        audit_job = next(job for job in fake.calls if job.runtime_role == "registered_candidate_self_audit")
        audit_rules = audit_job.context[0]["registered_semantic_job"]["input"]["payload"]["rule_material"]
        expected_bindings = [{
            **{key: deepcopy(item[key]) for key in ("id", "authority", "exceptions") if key in item},
            "statement_fingerprint": fingerprint_text(item["statement"]),
            "statement_utf8_bytes": len(item["statement"].encode("utf-8")),
        } for item in audit_rules]
        self.assertEqual(expected_bindings, bindings)
        self.assertTrue(all(isinstance(item["statement"], str) and item["statement"] for item in audit_rules))
        reuse = runtime._latest_checkpoint("PROD", run_id, "production_local_revision_reuse")
        self.assertEqual(candidate["candidate_fingerprint"], reuse["source_candidate_fingerprint"])
        selectors = [green["selector"]["kind"] for green in
                     runtime._latest_bundle("PROD", run_id)["freeze"]["stage_greenlights"].values()]
        self.assertTrue(all(kind == "author_revision_checkpoint_reuse" for kind in selectors))

    def test_writer_authority_binding_size_does_not_scale_with_rule_statement_length(self):
        from production_runtime.repair import writer_context

        repair = {
            "policy": {
                "repair_owner": "surface",
                "revision_route": "isolated_defect",
                "generation_mode": "local_or_bounded_repair",
                "targets": [{
                    "target_id": "TARGET-SYNTHETIC",
                    "scene_ref": "SCENE-SYNTHETIC",
                    "route": "local_edit",
                    "evidence_quote": "Synthetic evidence.",
                    "edit_window_quote": "Synthetic edit window.",
                }],
            },
            "objective_envelope": {"fingerprint": "sha256:" + "1" * 64},
            "editor_fix_and_preserve_plan": {"fix": [], "preserve": [], "repair_plan": []},
            "editor_binding_fingerprint": "sha256:" + "2" * 64,
            "authority": False,
        }
        sizes = []
        for length in (100, 100_000):
            context = writer_context({
                "source_request": {"rule_material": [{
                    "id": "RULE-SYNTHETIC", "authority": "framework", "statement": "x" * length,
                }]},
                "candidate_fingerprint": "sha256:" + "3" * 64,
                "candidate_text": "Synthetic candidate.",
            }, repair, {})
            serialized = canonical_json(context)
            self.assertNotIn("x" * min(length, 100), serialized)
            sizes.append(len(serialized.encode("utf-8")))
        self.assertLess(abs(sizes[1] - sizes[0]), 16)

    def test_confirmed_prefix_recovery_reuses_only_predecessor_evidence_and_calls_four_remaining_gates(self):
        _, _, _, candidate, _ = self.release()
        request = self.request(
            candidate,
            instruction=REVISION_INSTRUCTION,
            idempotency_key="confirmed-prefix-author-revision-fixture",
        )
        source_id = self.start_revision(request)
        NovelWorkflowService(self.store).start(
            project_id="PROD", run_id=source_id, chapter_id="CH001", author_profile="guided",
        )
        failed_runtime = ProductionRunExecutor(
            self.store,
            RevisionChainFixtureRuntime(
                candidate_text=CONTINUED_REVISION_TEXT,
                generation_mode="local_or_bounded_repair",
                malformed_self_audit=True,
            ),
        )
        with self.assertRaisesRegex(ProductionRunError, "quality.candidate_self_audit"):
            failed_runtime.execute(
                "PROD", source_id, service_id="svc", inherit_repair_request=True,
                independent_provenance=fixtures.PROVENANCE, max_model_calls=8,
            )
        source_status = failed_runtime.status("PROD", source_id)
        self.assertEqual("semantic_pending", source_status["status"])
        with self.store.open_project("PROD") as conn:
            prefix_ref = build_confirmed_prefix_reference(conn, source_id)
            source_calls_before = [tuple(row) for row in conn.execute(
                "SELECT call_id,stage_key,runtime_role,input_fingerprint,result_fingerprint,state "
                "FROM production_stage_calls WHERE run_id=? ORDER BY rowid",
                (source_id,),
            )]
        self.assertEqual(prefix_ref, source_status["confirmed_prefix_source"])

        payload = {
            **request["next_action"]["payload"],
            "chapter_id": "CH001",
            "confirmed_prefix_source": prefix_ref,
        }
        with self.store.open_project("PROD") as conn:
            counts_before = (
                conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM production_stage_calls").fetchone()[0],
            )
        changed_prefix = {
            **prefix_ref,
            "expected_prefix_fingerprint": "sha256:" + "0" * 64,
        }
        with self.assertRaisesRegex(OperationError, "does not match Core evidence"):
            self.ops.start_author_run(
                "PROD", task_mode="REVISE", target_ref="DOC-1",
                payload={**payload, "confirmed_prefix_source": changed_prefix},
                recovery_authorized_by="user",
                recovery_authorization={"intent": "confirmed_prefix_recovery"},
                idempotency_key="confirmed-prefix-changed-reference-fixture",
            )
        with self.store.open_project("PROD") as conn:
            self.assertEqual(counts_before, (
                conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM production_stage_calls").fetchone()[0],
            ))
        recovered_id = self.ops.start_author_run(
            "PROD",
            task_mode="REVISE",
            target_ref="DOC-1",
            payload=payload,
            recovery_authorized_by="user",
            recovery_authorization={
                "intent": "confirmed_prefix_recovery",
                "explicit_action": "reuse four confirmed predecessor stages",
                "observed_gate": "quality.candidate_self_audit JSON syntax failure",
            },
            idempotency_key="confirmed-prefix-recovery-fixture",
        )["run_id"]
        NovelWorkflowService(self.store).start(
            project_id="PROD", run_id=recovered_id, chapter_id="CH001", author_profile="guided",
        )
        fake = RevisionChainFixtureRuntime(
            candidate_text="THIS MUST NOT BE GENERATED",
            generation_mode="local_or_bounded_repair",
            bad_narrative_evidence=True,
        )
        runtime = ProductionRunExecutor(self.store, fake)
        result = runtime.execute(
            "PROD", recovered_id, service_id="svc", inherit_repair_request=True,
            independent_provenance=fixtures.PROVENANCE, max_model_calls=4,
        )
        self.assertEqual("awaiting_external", result["status"])
        self.assertEqual([
            "registered_candidate_self_audit",
            "registered_repair_comparison",
            "registered_reader_expectations",
            "registered_narrative_state",
        ], [job.runtime_role for job in fake.calls])
        with self.store.open_project("PROD") as conn:
            self.assertEqual(source_calls_before, [tuple(row) for row in conn.execute(
                "SELECT call_id,stage_key,runtime_role,input_fingerprint,result_fingerprint,state "
                "FROM production_stage_calls WHERE run_id=? ORDER BY rowid",
                (source_id,),
            )])
            self.assertEqual(4, conn.execute(
                "SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?",
                (recovered_id,),
            ).fetchone()[0])
            reuse_receipts = [json.loads(row[0]) for row in conn.execute(
                "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage' "
                "AND idempotency_key LIKE ? ORDER BY rowid",
                (recovered_id, recovered_id + ":stage:%"),
            )]
            self.assertEqual(0, conn.execute(
                "SELECT COUNT(*) FROM checkpoints WHERE run_id=? "
                "AND checkpoint_kind='production_narrative_proposal'",
                (recovered_id,),
            ).fetchone()[0])
            omitted = json.loads(conn.execute(
                "SELECT payload_json FROM runtime_events WHERE run_id=? "
                "AND event_kind='production_narrative_proposal_omitted'",
                (recovered_id,),
            ).fetchone()[0])
        self.assertEqual(
            ["surface_realization", "reader_engagement", "continuity"],
            [receipt["mechanism"] for receipt in reuse_receipts],
        )
        self.assertTrue(all(
            receipt["evidence_kind"] == "confirmed_prefix_reuse"
            and receipt["current_run_model_invoked"] is False
            for receipt in reuse_receipts
        ))
        self.assertEqual(
            "unsupported_exact_candidate_quote_at_model_budget_boundary",
            omitted["reason"],
        )
        self.assertFalse(omitted["repair_model_call_dispatched"])
        self.assertFalse(omitted["authority"])

        calls_before_replay = len(fake.calls)
        replay = runtime.resume_execution("PROD", recovered_id)
        self.assertEqual("awaiting_external", replay["status"])
        self.assertEqual(calls_before_replay, len(fake.calls))

        completed = self.fixture.submit(runtime, recovered_id)
        self.assertEqual("completed", completed["status"])
        followup_request = self.request(
            completed["candidate"], instruction="Tighten the recovered chapter once more.",
            idempotency_key="confirmed-prefix-followup-revision-fixture",
        )
        followup_id = self.start_revision(followup_request)
        NovelWorkflowService(self.store).start(
            project_id="PROD", run_id=followup_id, chapter_id="CH001", author_profile="guided",
        )
        followup_fake = RevisionChainFixtureRuntime(
            candidate_text="A subsequent revision remains causally grounded.",
            generation_mode="local_or_bounded_repair",
        )
        followup_runtime = ProductionRunExecutor(self.store, followup_fake)
        followup = followup_runtime.execute(
            "PROD", followup_id, service_id="svc", inherit_repair_request=True,
            independent_provenance=fixtures.PROVENANCE,
        )
        self.assertEqual("awaiting_external", followup["status"])
        self.assertEqual(8, len(followup_fake.calls))
        self.assertNotIn(
            "registered_scene_projection", [job.runtime_role for job in followup_fake.calls],
        )

    def test_local_author_revision_rebuilds_causal_context_when_the_candidate_universe_changes(self):
        _, _, _, candidate, _ = self.release()
        request = self.request(
            candidate, instruction=REVISION_INSTRUCTION,
            idempotency_key="local-author-revision-universe-change-fixture",
        )
        stamp = now_iso()
        with self.store.open_project("PROD") as conn:
            conn.execute(
                "INSERT INTO research_sources(source_id,title,source_uri,source_kind,rights_json,provenance_json,status,created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                ("RS-NEW", "New research", None, "fixture", "{}", "{}", "active", stamp),
            )
            conn.execute(
                "INSERT INTO research_claims(research_claim_id,source_id,claim_text,citation_json,fictionalization_notes,"
                "character_knowledge_boundary_json,canon_status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                ("RC-NEW", "RS-NEW", "new optional evidence", "{}", None, "{}", "research_only", stamp),
            )
            conn.commit()
        run_id = self.start_revision(request)
        NovelWorkflowService(self.store).start(
            project_id="PROD", run_id=run_id, chapter_id="CH001", author_profile="guided",
        )
        fake = RevisionChainFixtureRuntime(
            candidate_text=CONTINUED_REVISION_TEXT, generation_mode="local_or_bounded_repair",
        )
        runtime = ProductionRunExecutor(self.store, fake)
        result = runtime.execute(
            "PROD", run_id, service_id="svc", inherit_repair_request=True,
            independent_provenance=fixtures.PROVENANCE,
        )
        self.assertEqual("awaiting_external", result["status"])
        roles = [job.runtime_role for job in fake.calls if job.run_id == run_id]
        self.assertIn("context_profile_deriver", roles)
        self.assertIn("context_selector", roles)
        self.assertIn("registered_repair_editor", roles)
        self.assertIn("registered_scene_projection", roles)
        self.assertIn("registered_reader_pressure", roles)
        self.assertNotIn("event_first_raw_draft", roles)
        self.assertIn("surface_realization", roles)
        reuse = runtime._latest_checkpoint("PROD", run_id, "production_local_revision_reuse")
        self.assertFalse(reuse["source_context_exact"])
        self.assertEqual([], reuse["reused_mechanisms"])

    def test_internal_repair_keeps_author_revision_objective_out_of_blind_reader_context(self):
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
        roles = [job.runtime_role for job in fake.calls]
        self.assertNotIn("event_first_raw_draft", roles)
        for role in ("surface_realization", "registered_reader_engagement"):
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

    def test_historical_quality_v7_is_immutable_evidence_not_a_live_generation_contract(self):
        archive = Path(__file__).resolve().parents[1] / "harness/semantic_workers/contracts/history/quality.v7.json"
        archive_bytes = archive.read_bytes()
        old_registry = json.loads(archive_bytes)
        history = json.loads((archive.parent / "index.json").read_text(encoding="utf-8"))
        entry = next(item for item in history["entries"] if item["pack_id"] == "quality" and item["version"] == "7")
        current = json.loads((archive.parents[1] / "quality.json").read_text(encoding="utf-8"))
        self.assertEqual("7", old_registry["version"])
        self.assertEqual(hashlib.sha256(archive_bytes).hexdigest(), entry["sha256"])
        self.assertNotEqual("7", current["version"])
        old_properties = old_registry["contracts"]["quality.candidate_self_audit"]["input_contract"]["properties"]
        current_properties = current["contracts"]["quality.candidate_self_audit"]["input_contract"]["properties"]
        self.assertNotIn("author_objectives", old_properties)
        self.assertIn("author_objectives", current_properties)


if __name__ == "__main__":
    unittest.main()
