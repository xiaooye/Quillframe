from __future__ import annotations
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent_runtime import AgentResult
from model_runtime.structured_output import validate_structured_text
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
from semantic_worker_router import fingerprint_for, make_contract_job, validate_result, validate_typed_value, worker_job_view

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
        schema = calls[0].output_schema
        self.assertEqual(set(job["output_contract"]["required"]), set(schema["properties"]))
        self.assertEqual({"action", "knowledge_basis"}, set(schema["properties"]["proposals"]["items"]["properties"]))
        self.assertIn("free-text action", calls[0].instruction)
        self.assertEqual(binding["result"]["judgment"], validate_structured_text(json.dumps(binding["result"]["judgment"]), schema))
        self.assertEqual(original, frozen)
        self.assertNotIn("FUTURE OBSERVATION", json.dumps(calls[0].context))
        self.assertNotIn("KN-OTHER", json.dumps(calls[0].context))

    def test_scene_native_shape_retains_blocking_repair_routes_and_original_contract(self):
        calls = []
        judgment = {"confidence": 0.7, "interaction_trace": "Two supplied observations conflict.",
                    "observable_trajectory": "The interaction cannot yet resolve.", "unresolved_pressures": ["A choice is open."],
                    "repair_routes": [{"owner": "continuity", "reason": "The object has incompatible locations."}]}

        def invoke(job):
            calls.append(job)
            return AgentResult(job_id=job.job_id, session_id=job.session_id, run_id=job.run_id, status="completed",
                               input_fingerprint=job.input_fingerprint, model_service_id=job.service_id, model_id="fixture", protocol="fixture",
                               final_text=json.dumps(judgment), steps=1, model_requests=1)

        job = make_contract_job("scene.resolve_actions", "SCENE-FIXTURE", {"scene": "Synthetic conflict"}, source_session_id="SES-FIXTURE")
        original = deepcopy(job)
        binding = RegisteredSemanticExecutor(SimpleNamespace(run=invoke)).execute_prepared(
            semantic_job=job, run={"run_id": "RUN-FIXTURE", "session_id": "SES-FIXTURE", "task_mode": "REVISE"},
            service_id="svc", model_preference=None, runtime_role="registered_scene_resolution")
        self.assertEqual(original, binding["job"])
        self.assertEqual(judgment, validate_structured_text(json.dumps(judgment), calls[0].output_schema))
        self.assertEqual(judgment, binding["result"]["judgment"])
        self.assertEqual([], validate_typed_value(judgment, job["output_contract"]))
        self.assertEqual([], validate_registered_job(original))

    def test_registered_schema_response_rejects_extra_closers_even_for_completed_adapter(self):
        calls = []
        raw = '{"confidence":1,"interaction_trace":"A collision.","observable_trajectory":"A delay.","unresolved_pressures":[],"repair_routes":[]}]}'

        def invoke(job):
            calls.append(job)
            return AgentResult(job_id=job.job_id, session_id=job.session_id, run_id=job.run_id, status="completed",
                               input_fingerprint=job.input_fingerprint, model_service_id=job.service_id, model_id="fixture", protocol="fixture",
                               final_text=raw, steps=1, model_requests=1)

        with self.assertRaises(ProductionRunError) as error:
            RegisteredSemanticExecutor(SimpleNamespace(run=invoke)).execute(
                run={"run_id": "RUN-FIXTURE", "task_mode": "DRAFT"}, service_id="svc", contract_id="scene.resolve_actions",
                subject_id="SCENE-FIXTURE", payload={}, model_preference=None, runtime_role="registered_scene_resolution")
        self.assertEqual("semantic_output_invalid", error.exception.code)
        self.assertEqual(1, len(calls))

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

class RepairContractBindingTests(unittest.TestCase):
    def comparison_payload(self):
        from quality.objective_envelope import build

        incumbent = "合成旧稿。\r\nA bounded question remains.\r\n"
        challenger = "合成修订。\r\nA bounded question advances.\r\n"
        envelope = build({
            "subject_id": "CH-COMPARE", "run_id": "RUN-COMPARE", "authority_cutoff": "synthetic",
            "objective_items": [{"id": "OBJ-COMPARE", "category": "reader", "statement": "Preserve the active question.", "source_refs": ["fixture:plan"]}],
            "must_preserve": ["The active question."], "derived_from_rejected_realization": False,
        })
        return {"evolution_run_id": "RUN-COMPARE", "evolution_subject_id": "CH-COMPARE", "comparison_id": "CMP-FIXTURE",
                "incumbent": {"candidate_id": "C0", "content_fingerprint": fingerprint_text(incumbent), "text": incumbent},
                "challenger": {"candidate_id": "C1", "content_fingerprint": fingerprint_text(challenger), "text": challenger, "repair_owner": "reader_pressure"},
                "repair_context": {"repair_target": "Advance the active question.", "objective_envelope": envelope}}

    def test_compare_worker_receives_both_exact_texts_and_unmodified_owner(self):
        from quality.quality_evolution import _fixture_result

        payload = self.comparison_payload()
        original = deepcopy(payload)
        job = make_contract_job("quality.compare", payload["comparison_id"], payload)
        self.assertEqual([], validate_registered_job(job))
        self.assertEqual([], validate_result(job, _fixture_result(job, "challenger", "Synthetic comparison.")))
        self.assertEqual(original, worker_job_view(job)["input"]["payload"])
        self.assertEqual(original, payload)

    def test_compare_rejects_missing_malformed_or_changed_exact_text_before_job_creation(self):
        for side in ("incumbent", "challenger"):
            for defect in ("missing", "empty", "wrong_type", "changed", "newline_normalized", "bad_hash", "invalid_utf8"):
                with self.subTest(side=side, defect=defect):
                    payload = self.comparison_payload()
                    candidate = payload[side]
                    if defect == "missing":
                        del candidate["text"]
                    elif defect == "empty":
                        candidate["text"] = ""
                    elif defect == "wrong_type":
                        candidate["text"] = {"text": candidate["text"]}
                    elif defect == "changed":
                        candidate["text"] += "Changed."
                    elif defect == "newline_normalized":
                        candidate["text"] = candidate["text"].replace("\r\n", "\n")
                    elif defect == "bad_hash":
                        candidate["content_fingerprint"] = FP
                    else:
                        candidate["text"] = "\ud800"
                    with self.assertRaises(ValueError):
                        make_contract_job("quality.compare", payload["comparison_id"], payload)

    def test_rehashed_hash_only_or_changed_comparison_cannot_accept_a_typed_pass(self):
        from quality.quality_evolution import _fixture_result

        for defect in ("incumbent_missing", "challenger_missing", "changed_text", "malformed_payload"):
            with self.subTest(defect=defect):
                payload = self.comparison_payload()
                job = make_contract_job("quality.compare", payload["comparison_id"], payload)
                if defect.endswith("_missing"):
                    del job["input"]["payload"][defect.split("_")[0]]["text"]
                elif defect == "changed_text":
                    job["input"]["payload"]["challenger"]["text"] += "Changed."
                else:
                    job["input"]["payload"] = []
                job["input_fingerprint"] = fingerprint_for(job)
                result = _fixture_result(job, "challenger", "Synthetic successful repair.")
                self.assertTrue(validate_registered_job(job))
                self.assertTrue(validate_result(job, result))

    def test_editor_optional_text_is_exactly_bound_when_supplied(self):
        compare = self.comparison_payload()
        payload = {"candidate_fingerprint": compare["incumbent"]["content_fingerprint"], "reader_assessment": {},
                   "objective_envelope": compare["repair_context"]["objective_envelope"]}
        self.assertEqual([], validate_registered_job(make_contract_job("editor.repair_spec", "C0", payload)))
        payload["candidate_text"] = compare["incumbent"]["text"]
        job = make_contract_job("editor.repair_spec", "C0", payload)
        self.assertEqual([], validate_registered_job(job))
        self.assertEqual(payload["candidate_text"], worker_job_view(job)["input"]["payload"]["candidate_text"])
        for invalid in (None, "", 42, payload["candidate_text"].replace("\r\n", "\n"), "\ud800"):
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaises(ValueError):
                    make_contract_job("editor.repair_spec", "C0", {**payload, "candidate_text": invalid})
        with self.assertRaises(ValueError):
            make_contract_job("editor.repair_spec", "C0", {**payload, "candidate_fingerprint": FP})

    def test_rehashed_editor_job_with_changed_text_cannot_accept_repair_spec(self):
        compare = self.comparison_payload()
        job = make_contract_job("editor.repair_spec", "C0", {
            "candidate_fingerprint": compare["incumbent"]["content_fingerprint"], "candidate_text": compare["incumbent"]["text"],
            "reader_assessment": {}, "objective_envelope": compare["repair_context"]["objective_envelope"],
        })
        judgment = {"confidence": 1.0, "repair_owner": "reader_pressure", "generation_mode": "fresh_realization",
                    "fix": "Advance the active question.", "repair_plan": "Reconstruct the current situation.",
                    "preserve": ["The active question."], "comparison_required": True}
        result = {**{key: job[key] for key in ("job_id", "subject_id", "kind", "input_fingerprint")},
                  "status": "completed", "worker": {"provider": "self_test", "model_or_reviewer": "fixture"},
                  "judgment": judgment, "proposals": [], "errors": []}
        self.assertEqual([], validate_result(job, result))
        job["input"]["payload"]["candidate_text"] += "Changed."
        job["input_fingerprint"] = fingerprint_for(job)
        result["input_fingerprint"] = job["input_fingerprint"]
        self.assertTrue(validate_result(job, result))

    def test_lineage_pure_validation_preserves_distinct_comparison_and_prose_parents(self):
        from quality.candidate_lineage import validate_derivation

        for origin, comparison, prose in (("draft", None, None), ("repair", "C0", "C0"),
                                          ("fresh_regeneration", "C0", None), ("user_edit", "C0", None), ("user_edit", "C0", "C1")):
            self.assertIsNone(validate_derivation(origin=origin, comparison_parent_candidate_id=comparison, prose_parent_candidate_id=prose))
        for origin, comparison, prose in (("draft", "C0", None), ("draft", None, "C0"), ("repair", None, None),
                                          ("repair", "C0", None), ("repair", "C0", "C1"), ("fresh_regeneration", None, None),
                                          ("fresh_regeneration", "C0", "C0"), ("user_edit", None, None), ("unknown", None, None),
                                          ([], None, None), ("repair", "", ""), ("repair", True, True), ("user_edit", "C0", 1)):
            with self.subTest(origin=origin, comparison=comparison, prose=prose):
                with self.assertRaises(ValueError):
                    validate_derivation(origin=origin, comparison_parent_candidate_id=comparison, prose_parent_candidate_id=prose)

    def test_comparison_gate_projection_keeps_preservation_and_pending_precedence(self):
        from quality.candidate_qualification import comparison_gate_status

        passed = {"target_outcome": "improved", "objective_preservation": "preserved", "reader_value": "unchanged",
                  "character_relationship_energy": "preserved", "outcome_class": "successful_repair"}
        for reader in ("improved", "unchanged"):
            for energy in ("preserved", "not_applicable"):
                self.assertEqual("pass", comparison_gate_status({**passed, "reader_value": reader, "character_relationship_energy": energy}))
        for changed in ({"target_outcome": "unchanged", "outcome_class": "target_not_fixed"},
                        {"objective_preservation": "degraded", "outcome_class": "objective_regression"},
                        {"reader_value": "degraded"}, {"character_relationship_energy": "degraded"}):
            self.assertEqual("fail", comparison_gate_status({**passed, **changed}))
        for field in ("target_outcome", "objective_preservation", "reader_value", "character_relationship_energy"):
            self.assertEqual("pending", comparison_gate_status({**passed, "objective_preservation": "degraded", field: "insufficient_evidence"}))
        self.assertEqual("pending", comparison_gate_status({**passed, "outcome_class": "inconclusive"}))
        self.assertEqual("fail", comparison_gate_status({}))

    def test_evolution_cli_reads_explicit_utf8_bytes_and_checks_stored_fingerprints(self):
        from quality import candidate_lineage_runtime, quality_evolution

        payload = self.comparison_payload()
        for module in (quality_evolution, candidate_lineage_runtime):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                incumbent = root / "incumbent.txt"
                challenger = root / "challenger.txt"
                context = root / "repair.json"
                incumbent.write_bytes(payload["incumbent"]["text"].encode("utf-8"))
                challenger.write_bytes(payload["challenger"]["text"].encode("utf-8"))
                context.write_text(json.dumps(payload["repair_context"], ensure_ascii=False), encoding="utf-8")
                base_args = [module.__name__, "--db", str(root / "ledger.db")]

                def invoke(*args):
                    output = io.StringIO()
                    with patch.object(sys, "argv", base_args + list(args)), redirect_stdout(output):
                        self.assertEqual(0, module.main())
                    return json.loads(output.getvalue())

                lineage = module is candidate_lineage_runtime
                invoke("start", "--run-id", "RUN-COMPARE", "--subject-id", "CH-COMPARE", "--baseline-id", "C0", "--text-file", str(incumbent),
                       *(["--created-by-run-id", "RUN-DRAFT"] if lineage else []))
                invoke("add-candidate", "--run-id", "RUN-COMPARE", "--candidate-id", "C1", "--text-file", str(challenger), "--repair-owner", "reader_pressure",
                       *(["--created-by-run-id", "RUN-REPAIR", "--origin", "repair", "--prose-parent-id", "C0"] if lineage else []))
                prepare = ["prepare-comparison", "--run-id", "RUN-COMPARE", "--comparison-id", "CMP-FIXTURE", "--challenger-id", "C1",
                           "--incumbent-text-file", str(incumbent), "--challenger-text-file", str(challenger), "--repair-context-json", str(context)]
                job = invoke(*prepare)
                self.assertEqual(payload, job["input"]["payload"])
                self.assertEqual([], validate_registered_job(job))
                before = invoke("status", "--run-id", "RUN-COMPARE")
                for path in (incumbent, challenger):
                    original = path.read_bytes()
                    path.write_bytes(original.replace(b"\r\n", b"\n"))
                    with self.assertRaisesRegex(ValueError, "stored candidate fingerprint"):
                        invoke(*prepare)
                    path.write_bytes(original)
                self.assertEqual(before, invoke("status", "--run-id", "RUN-COMPARE"))


if __name__ == "__main__":
    unittest.main()
