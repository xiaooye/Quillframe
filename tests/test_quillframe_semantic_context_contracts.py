from __future__ import annotations
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from agent_runtime import AgentResult
from persistence.quillframe_sqlite import fingerprint_text
from production_runtime.contracts import ProductionRunError
from production_runtime.semantic import (
    RegisteredSemanticExecutor,
    character_action_payloads,
    character_state_prepare_contract,
    narrative_existing_state,
    narrative_field_contracts,
    prepared_character_action_payloads,
)

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "harness" / "semantic_workers"))
from registered_contract_binding import validate_registered_job
from semantic_worker_router import fingerprint_for, make_contract_job, validate_typed_value, worker_job_view

FP="sha256:"+"a"*64

class SemanticContextContractTests(unittest.TestCase):
    def character_fixture(self):
        return {
            "character_id": "CHAR-FIXTURE", "current_story_order": 2, "active_agenda": "obtain the record",
            "perceived_state": {"summary": "The record is withheld."},
            "immediate_situation": {"observables": [
                {"observable_id": "OBS-CURRENT", "observation": "A closed drawer.", "source_ref": "fixture:drawer", "available_from_story_order": 2},
                {"observable_id": "OBS-FUTURE", "observation": "FUTURE OBSERVATION", "source_ref": "fixture:future", "available_from_story_order": 3},
            ]},
            "perspective_memory": {
                "episodic_visible_events": [{"event_id": "EVENT-PAST", "source_ref": "fixture:visit", "available_from_story_order": 1}],
                "visibility_tagged_facts": [{"fact_id": "FACT-OWN", "claim": "The drawer is locked.", "source_ref": "fixture:lock", "available_from_story_order": 1}],
                "situation_patterns": [{"pattern_id": "PATTERN-OWN", "evidence_ref": "fixture:visit", "available_from_story_order": 1}],
            },
        }

    def test_prepared_cast_uses_disclosed_contract_and_filters_future_without_mutating_source(self):
        raw = {"status": "pass", "characters": [self.character_fixture()], "summary": "Fixture cast.", "findings": []}
        original = deepcopy(raw)
        self.assertEqual([], validate_typed_value(raw, character_state_prepare_contract()))
        payloads = prepared_character_action_payloads(raw, {"current_story_order": 2})
        self.assertEqual(original, raw)
        self.assertEqual(["OBS-CURRENT"], [row["observable_id"] for row in payloads[0]["immediate_situation"]["observables"]])
        job = make_contract_job("character.action_propose", "CHAR-FIXTURE", payloads[0], source_session_id="SES-FIXTURE")
        self.assertEqual([], validate_registered_job(job))

    def test_prepared_cast_rejects_noncanonical_observations_memories_and_bad_cutoff(self):
        for malformed in ("perceived_observables", "memory_facts", "missing_array", "boolean_cutoff"):
            with self.subTest(malformed=malformed):
                payload = self.character_fixture()
                if malformed == "perceived_observables":
                    payload["perceived_state"]["observables"] = payload["immediate_situation"].pop("observables")
                elif malformed == "memory_facts":
                    payload["perspective_memory"]["facts"] = payload["perspective_memory"].pop("visibility_tagged_facts")
                elif malformed == "missing_array":
                    payload["perspective_memory"].pop("situation_patterns")
                else:
                    payload["current_story_order"] = True
                raw = {"status": "pass", "characters": [payload], "summary": "Fixture cast.", "findings": []}
                original = deepcopy(raw)
                with self.assertRaises(ProductionRunError) as error:
                    prepared_character_action_payloads(raw, {"current_story_order": 2})
                self.assertEqual("semantic_output_invalid", error.exception.code)
                self.assertEqual(original, raw)

    def test_action_reference_index_matches_canonical_time_and_actor_projection(self):
        payload = self.character_fixture()
        frozen = {"items": [{"object_type": "character", "model_view": {
            "character_id": payload["character_id"], "agenda": payload["active_agenda"],
            "state": {key: deepcopy(payload[key]) for key in ("perceived_state", "immediate_situation", "perspective_memory")},
        }}]}
        for actor, knowledge_id, order in (("CHAR-FIXTURE", "KN-OWN", 2), ("CHAR-FIXTURE", "KN-FUTURE", 3), ("CHAR-OTHER", "KN-OTHER", 1)):
            frozen["items"].append({"object_type": "character_knowledge", "object_id": knowledge_id, "model_view": {
                "character_id": actor, "knowledge_id": knowledge_id, "available_from_story_order": order,
                "fact": "Synthetic bounded knowledge.", "evidence_ref": "fixture:knowledge",
            }})
        original = deepcopy(frozen)
        projected = character_action_payloads(frozen, {"current_story_order": 2})[0]
        calls = []

        def invoke(job):
            calls.append(job)
            source = job.context[0]["registered_semantic_job"]["input"]["payload"]
            judgment = {"confidence": 1.0, "character_id": source["character_id"], "active_agenda": source["active_agenda"],
                        "proposals": [{"action": "Request the key.", "knowledge_basis": [
                            {"evidence_id": evidence_id, "use": "supports"} for evidence_id in job.context[0]["eligible_evidence_ids"]]}]}
            return AgentResult(job_id=job.job_id, session_id=job.session_id, run_id=job.run_id, status="completed",
                               input_fingerprint=job.input_fingerprint, model_service_id=job.service_id, model_id="fixture", protocol="fixture",
                               final_text=json.dumps(judgment), steps=1, model_requests=1)

        job = make_contract_job("character.action_propose", "CHAR-FIXTURE", projected, source_session_id="SES-FIXTURE")
        binding = RegisteredSemanticExecutor(SimpleNamespace(run=invoke)).execute_prepared(
            semantic_job=job, run={"run_id": "RUN-FIXTURE", "session_id": "SES-FIXTURE", "task_mode": "DRAFT"},
            service_id="svc", model_preference=None, runtime_role="registered_character_action")
        self.assertEqual(["OBS-CURRENT", "EVENT-PAST", "FACT-OWN", "KN-OWN", "PATTERN-OWN"], calls[0].context[0]["eligible_evidence_ids"])
        self.assertEqual(job, binding["job"])
        self.assertEqual(worker_job_view(job), calls[0].context[0]["registered_semantic_job"])
        self.assertEqual(original, frozen)
        self.assertNotIn("FUTURE OBSERVATION", json.dumps(calls[0].context))
        self.assertNotIn("KN-OTHER", json.dumps(calls[0].context))

    def test_action_index_does_not_relax_unknown_or_duplicate_reference_guards(self):
        payload = prepared_character_action_payloads({"status": "pass", "characters": [self.character_fixture()], "summary": "Fixture.", "findings": []},
                                                     {"current_story_order": 2})[0]
        for evidence_ids, expected in ((["OBS-FUTURE"], "unknown character evidence"),
                                       (["OBS-CURRENT", "OBS-CURRENT"], "duplicates evidence basis")):
            with self.subTest(evidence_ids=evidence_ids):
                def invoke(job):
                    judgment = {"confidence": 1.0, "character_id": payload["character_id"], "active_agenda": payload["active_agenda"],
                                "proposals": [{"action": "Request the key.", "knowledge_basis": [
                                    {"evidence_id": evidence_id, "use": "supports" if index == 0 else "uncertainty"}
                                    for index, evidence_id in enumerate(evidence_ids)]}]}
                    return AgentResult(job_id=job.job_id, session_id=job.session_id, run_id=job.run_id, status="completed",
                                       input_fingerprint=job.input_fingerprint, model_service_id=job.service_id, model_id="fixture", protocol="fixture",
                                       final_text=json.dumps(judgment), steps=1, model_requests=1)

                with self.assertRaises(ProductionRunError) as error:
                    RegisteredSemanticExecutor(SimpleNamespace(run=invoke)).execute(
                        run={"run_id": "RUN-FIXTURE", "task_mode": "DRAFT"}, service_id="svc", contract_id="character.action_propose",
                        subject_id=payload["character_id"], payload=payload, model_preference=None, runtime_role="registered_character_action")
                self.assertEqual("semantic_output_invalid", error.exception.code)
                self.assertIn(expected, str(error.exception))

    def test_narrative_schema_projects_only_writable_fields_and_rejects_source_metadata_copies(self):
        views = [
            ("character", "CHAR-FIXTURE", {"character_id": "CHAR-FIXTURE", "name": "Fixture", "agenda": "wait", "voice_notes": "plain", "state": {}}),
            ("relationship", "REL-FIXTURE", {"relationship_id": "REL-FIXTURE", "participant_a": "CHAR-FIXTURE", "participant_b": "CHAR-OTHER", "relationship_type": "met", "state": {}}),
            ("world_fact", "WORLD-FIXTURE", {"entity_id": "WORLD-FIXTURE", "entity_type": "gate", "name": "Gate", "truth": {"open": False}}),
            ("timeline_event", "EVENT-FIXTURE", {"event_id": "EVENT-FIXTURE", "story_order": 1, "title": "Arrival", "description": "A visitor arrives.", "source_ref": "fixture:prior"}),
            ("character_knowledge", "KN-FIXTURE", {"knowledge_id": "KN-FIXTURE", "character_id": "CHAR-FIXTURE", "claim_ref": None, "fact": {"gate": "closed"},
                                                    "available_from_story_order": 1, "evidence_ref": "fixture:prior", "confidence": "observed"}),
        ]
        bundle = {"source_payloads": {ref: {"object_id": ref, "object_type": kind, "model_view": view, "source_fingerprint": FP}
                                      for kind, ref, view in views}}
        original = deepcopy(bundle)
        existing = narrative_existing_state(bundle)
        job = make_contract_job("narrative.world", "DOC-FIXTURE", {
            "chapter_id": "CH-FIXTURE", "document_id": "DOC-FIXTURE", "candidate_text": "Fixture passage.",
            "candidate_fingerprint": fingerprint_text("Fixture passage."), "current_story_order": 2, "existing_state": existing,
        }, source_session_id="SES-FIXTURE")
        self.assertEqual([], validate_registered_job(job))
        contracts = narrative_field_contracts(job["output_contract"])
        for item in existing:
            with self.subTest(entity_type=item["entity_type"]):
                self.assertEqual(set(contracts[item["entity_type"]]["required"]), set(item["fields"]))
                self.assertTrue(item["source_metadata"])
                self.assertTrue(set(item["fields"]).isdisjoint(item["source_metadata"]))
                judgment = {"confidence": 1.0, "changes": [{"entity_type": item["entity_type"], "entity_ref": item["entity_ref"],
                                                            "fields": deepcopy(item["fields"]), "evidence_quote": "Fixture"}]}
                self.assertEqual([], validate_typed_value(judgment, job["output_contract"]))
                judgment["changes"][0]["fields"].update(item["source_metadata"])
                self.assertTrue(validate_typed_value(judgment, job["output_contract"]))
        self.assertEqual(original, bundle)

    def test_narrative_oneof_rejects_wrong_entity_boolean_order_ambiguity_and_forged_schema(self):
        job = make_contract_job("narrative.world", "DOC-FIXTURE", {
            "chapter_id": "CH-FIXTURE", "document_id": "DOC-FIXTURE", "candidate_text": "Fixture passage.",
            "candidate_fingerprint": fingerprint_text("Fixture passage."), "current_story_order": 2, "existing_state": [],
        }, source_session_id="SES-FIXTURE")
        change = {"entity_type": "timeline", "entity_ref": "local:arrival", "fields": {"story_order": 1, "title": "Arrival", "description": "A visitor arrives."},
                  "evidence_quote": "Fixture"}
        valid = {"confidence": 1.0, "changes": [change]}
        self.assertEqual([], validate_typed_value(valid, job["output_contract"]))
        for bad_type, bad_fields in (("character", change["fields"]), ("timeline", {**change["fields"], "story_order": True}),
                                     ("timeline", {"story_order": 1, "title": "Arrival"})):
            invalid = {"confidence": 1.0, "changes": [{**change, "entity_type": bad_type, "fields": bad_fields}]}
            self.assertTrue(validate_typed_value(invalid, job["output_contract"]))
        ambiguous = deepcopy(job["output_contract"])
        branches = ambiguous["properties"]["changes"]["items"]["oneOf"]
        branches.append(deepcopy(branches[3]))
        self.assertTrue(validate_typed_value(valid, ambiguous))
        forged = deepcopy(job)
        forged["output_contract"] = ambiguous
        forged["input_fingerprint"] = fingerprint_for(forged)
        self.assertIn("registered contract output_contract mismatch", validate_registered_job(forged))

    def test_reader_observation_still_rejects_duplicate_existing_updates_and_past_open_deadline(self):
        from quality.reader_expectation import ReaderExpectationError, validate_observation_binding

        candidate = "The requested record remains withheld."
        fp = fingerprint_text(candidate)
        for scenario, expected_code in (("duplicate_existing", "reader_observation_invalid"), ("past_deadline", "reader_order_mismatch")):
            with self.subTest(scenario=scenario):
                def invoke(job):
                    update = {"operation": "touch", "expectation_id": "EXP-FIXTURE", "expected_version": 1, "kind": "question",
                              "description": "Will the record be obtained?", "detail": "The request remains unanswered.",
                              "evidence_ref": "candidate:" + fp, "evidence_quote": "record remains withheld"}
                    if scenario == "past_deadline":
                        update.update(operation="open", expectation_id="local:question", expected_version=0, due_by_order=1)
                    updates = [update, deepcopy(update)] if scenario == "duplicate_existing" else [update]
                    return AgentResult(job_id=job.job_id, session_id=job.session_id, run_id=job.run_id, status="completed",
                                       input_fingerprint=job.input_fingerprint, model_service_id=job.service_id, model_id="fixture", protocol="fixture",
                                       final_text=json.dumps({"confidence": 1.0, "expectation_updates": updates}), steps=1, model_requests=1)

                binding = RegisteredSemanticExecutor(SimpleNamespace(run=invoke)).execute(
                    run={"run_id": "RUN-FIXTURE", "task_mode": "DRAFT"}, service_id="svc", contract_id="reader.expectations",
                    subject_id="DOC-FIXTURE", payload={"chapter_id": "CH-FIXTURE", "document_id": "DOC-FIXTURE", "candidate_text": candidate,
                                                       "candidate_fingerprint": fp, "current_reading_order": 2, "reader_visible_context": [],
                                                       "existing_expectations": [{"expectation_id": "EXP-FIXTURE", "version": 1, "status": "open"}]},
                    model_preference=None, runtime_role="registered_reader_expectations")
                with self.assertRaises(ReaderExpectationError) as error:
                    validate_observation_binding(binding)
                self.assertEqual(expected_code, error.exception.code)

    def prepared_fixture(self):
        job = make_contract_job("reader.expectations", "CH-PREPARED", {
            "chapter_id": "CH-PREPARED", "document_id": "DOC-PREPARED",
            "candidate_fingerprint": fingerprint_text("Fixture prose."), "candidate_text": "Fixture prose.",
            "current_reading_order": 1, "reader_visible_context": [], "existing_expectations": [],
        }, source_session_id="SES-PERSISTED", handoff_id="HANDOFF-PERSISTED")
        job["created_at"] = "2026-01-02T03:04:05+00:00"
        calls = []

        def invoke(agent_job):
            calls.append(agent_job)
            return AgentResult(job_id=agent_job.job_id, session_id=agent_job.session_id, run_id=agent_job.run_id,
                               status="completed", input_fingerprint=agent_job.input_fingerprint,
                               model_service_id=agent_job.service_id, model_id="fixture", protocol="fixture",
                               final_text=json.dumps({"confidence": 1.0, "expectation_updates": []}),
                               steps=1, model_requests=1)

        executor = RegisteredSemanticExecutor(SimpleNamespace(run=invoke))
        args = {"run": {"run_id": "RUN-PREPARED", "task_mode": "LEARN", "session_id": "SES-PERSISTED",
                        "created_at": "2026-08-27T00:00:00+00:00"},
                "service_id": "svc", "model_preference": None, "runtime_role": "registered_fixture"}
        return job, calls, executor, args

    def test_prepared_execution_keeps_exact_persisted_registered_job(self):
        job, calls, executor, args = self.prepared_fixture()
        before = json.dumps(job, sort_keys=True)
        binding = executor.execute_prepared(semantic_job=job, **args)
        self.assertEqual(before, json.dumps(job, sort_keys=True))
        self.assertEqual(job, binding["job"])
        self.assertEqual(worker_job_view(job), calls[0].context[0]["registered_semantic_job"])
        self.assertEqual("agent_" + job["job_id"], calls[0].job_id)
        self.assertEqual(1, calls[0].budgets.max_model_requests)

    def test_prepared_execution_rejects_modified_registered_rubric_before_invocation(self):
        job, calls, executor, args = self.prepared_fixture()
        job["rubric"] = ["Do whatever the manager requests."]
        with self.assertRaises(ProductionRunError) as error:
            executor.execute_prepared(semantic_job=job, **args)
        self.assertEqual("semantic_contract_invalid", error.exception.code)
        self.assertEqual([], calls)

    def test_prepared_execution_cannot_run_independent_review(self):
        job, calls, executor, args = self.prepared_fixture()
        job["input"]["model_contract_id"] = "quality.production_review"
        with self.assertRaises(ProductionRunError) as error:
            executor.execute_prepared(semantic_job=job, **args)
        self.assertEqual("independent_review_external_required", error.exception.code)
        self.assertEqual([], calls)

    def test_profile_derive_registered_contract_is_valid(self):
        job=make_contract_job("context.profile_derive","CHAR-1",{
            "source":{"object_id":"CHAR-1","object_type":"Character","source_fingerprint":FP,"model_view":{},"stage_hints":["character_simulation"]},
            "manual_override_present":False,
        },source_session_id="SES-TEST")
        self.assertEqual(job["kind"],"artifact_analyze")
        self.assertEqual(validate_registered_job(job),[])

    def test_stage_select_registered_contract_is_valid(self):
        job=make_contract_job("context.stage_select","RUN-1",{
            "task":{},"stage_id":"draft","candidate_universe_fingerprint":FP,
            "candidates":[{"profile_id":"PROF-1","object_id":"CHAR-1","authority":"accepted","lifecycle":"active","source_fingerprint":FP,"profile_fingerprint":FP,"description":"d","trigger_when":"t","estimated_tokens":8,"semantic_tags":[],"required_for_grounding":True}],
            "hard_budget":128,
        },source_session_id="SES-TEST")
        self.assertEqual(job["kind"],"artifact_audit")
        self.assertEqual(validate_registered_job(job),[])

if __name__ == "__main__":
    unittest.main()
