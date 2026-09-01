from __future__ import annotations
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent_runtime import AgentResult, AgentRunner, ToolRuntime
from harness.context_runtime import fingerprint
from model_runtime import ModelTurn
from model_runtime.deadlines import DURABLE_REQUEST_TIMEOUT_MS
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
from semantic_worker_router import fingerprint_for, make_contract_job, validate_contract_result_bindings, validate_result, validate_typed_value, worker_job_view

FP="sha256:"+"a"*64
READER_CANDIDATE = "The promised answer remains unknown."

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

    def character_action_execution_fixture(self, *, agenda, action="Wait rather than press the request.", echo_changes=None):
        payload = self.character_fixture()
        payload["active_agenda"] = agenda
        payload = prepared_character_action_payloads(
            {"status": "pass", "characters": [payload], "summary": "Synthetic cast.", "findings": []},
            {"current_story_order": 2},
        )[0]
        job = make_contract_job("character.action_propose", payload["character_id"], payload,
                                source_session_id="SES-ECHO-FIXTURE", handoff_id="HANDOFF-ECHO-FIXTURE")
        judgment = {"confidence": 0.8, "character_id": payload["character_id"], "active_agenda": agenda,
                    "private_state": {"current_belief": "The record is withheld.", "current_misperception": "Waiting is harmless.",
                                      "desired_gain": "Obtain the record.", "feared_loss": "Lose access.", "expectations_of_others": []},
                    "proposals": [
                        {"strategy_id": "STRATEGY-WAIT", "action": action, "gain": "Preserve access.",
                         "risk_or_cost": "The record may disappear.", "rejection_reason": None,
                         "knowledge_basis": [{"evidence_id": "OBS-CURRENT", "use": "uncertainty"}]},
                        {"strategy_id": "STRATEGY-PRESS", "action": "Press for the key now.", "gain": "Gain the record quickly.",
                         "risk_or_cost": "Trigger refusal.", "rejection_reason": "The closed drawer provides too little leverage.",
                         "knowledge_basis": [{"evidence_id": "FACT-OWN", "use": "challenges"}]},
                    ],
                    "selected_strategy_id": "STRATEGY-WAIT", "relationship_specific_interaction": [],
                    **(echo_changes or {})}
        raw = " \n" + json.dumps(judgment, ensure_ascii=False, indent=2) + "\n"
        model = SimpleNamespace(
            select_model=Mock(return_value=SimpleNamespace(
                model_id="fixture-model", display_name=None, protocol="openai_chat_completions", metadata={}
            )),
            invoke=Mock(return_value=ModelTurn("openai_chat_completions", "fixture-model", text=raw, finish_reason="stop")),
        )
        calls, results = [], []

        def invoke(agent_job):
            calls.append(agent_job)
            result = AgentRunner(model, ToolRuntime()).run(agent_job)
            results.append(result)
            return result

        return SimpleNamespace(job=job, judgment=judgment, raw=raw, model=model, calls=calls, results=results,
            executor=RegisteredSemanticExecutor(SimpleNamespace(run=invoke)),
            args={"run": {"run_id": "RUN-ECHO-FIXTURE", "session_id": "SES-ECHO-FIXTURE", "task_mode": "DRAFT"},
                  "service_id": "fixture-service", "model_preference": None, "runtime_role": "registered_character_action"})

    def test_character_native_echo_preserves_exact_strings_without_selecting_the_action(self):
        agenda = " 保留合成目标“甲”；暂缓决定。\n下一步由角色判断。 "
        actions = ("Wait despite the earlier urgency.", "Refuse the offered route because the evidence remains uncertain.",
                   "Pursue a side objective before returning to the request.")
        for action in actions:
            with self.subTest(action=action):
                fixture = self.character_action_execution_fixture(agenda=agenda, action=action)
                original_job = deepcopy(fixture.job)
                raw_fingerprint = fingerprint_text(fixture.raw)
                binding = fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
                actual = fixture.calls[0]
                for field in ("character_id", "active_agenda"):
                    self.assertEqual([original_job["input"]["payload"][field]], actual.output_schema["properties"][field]["enum"])
                    self.assertNotIn("enum", original_job["output_contract"]["properties"][field])
                self.assertEqual(fixture.judgment, binding["result"]["judgment"])
                self.assertEqual(action, binding["result"]["judgment"]["proposals"][0]["action"])
                self.assertEqual([], validate_result(binding["job"], binding["result"]))
                self.assertEqual(original_job, fixture.job)
                self.assertEqual(original_job, binding["job"])
                self.assertEqual(worker_job_view(original_job), actual.context[0]["registered_semantic_job"])
                self.assertEqual(fixture.raw, fixture.results[0].final_text)
                self.assertEqual(raw_fingerprint, fingerprint_text(fixture.results[0].final_text))
                self.assertEqual(actual.output_schema, fixture.model.invoke.call_args.kwargs["output_schema"])
                self.assertIn("do not make that baseline permanent Canon", actual.instruction)
                self.assertIn("Judge the action semantically", actual.instruction)

    def test_character_native_echo_rejects_rephrasing_or_wrong_id_once_without_repair(self):
        agenda = "Keep the synthetic target; wait. "
        changes = [{"active_agenda": value} for value in (
            "Preserve the synthetic objective and pause.", "Keep the synthetic target, wait. ", agenda.rstrip(),
        )]
        changes.append({"character_id": "CHAR-OTHER"})
        for changed in changes:
            with self.subTest(changed=changed):
                fixture = self.character_action_execution_fixture(agenda=agenda, echo_changes=changed)
                original_job = deepcopy(fixture.job)
                # These strings fit the unchanged registered shape but fail its
                # original exact binding. Native output now exposes that bound.
                self.assertEqual([], validate_typed_value(fixture.judgment, fixture.job["output_contract"]))
                field = next(iter(changed))
                self.assertIn("character action result mismatch: " + field,
                              validate_contract_result_bindings(fixture.job, fixture.judgment))
                with self.assertRaises(ProductionRunError) as error:
                    fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
                self.assertEqual("semantic_pending", error.exception.code)
                self.assertEqual("model_failed", error.exception.detail["agent_status"])
                self.assertEqual("model_output_schema_invalid", error.exception.detail["errors"][0]["code"])
                self.assertEqual(1, fixture.model.invoke.call_count)
                self.assertEqual(1, fixture.model.select_model.call_count)
                self.assertFalse(fixture.model.select_model.call_args.kwargs["allow_probe"])
                self.assertEqual(1, fixture.results[0].model_requests)
                self.assertEqual(0, fixture.results[0].tool_calls)
                self.assertEqual(fixture.raw, fixture.results[0].final_text)
                self.assertEqual(original_job, fixture.job)

    def test_character_native_echo_binds_new_inputs_and_rejects_oversized_profile_before_dispatch(self):
        fixtures = [self.character_action_execution_fixture(agenda=agenda) for agenda in ("First synthetic goal.", "Second synthetic goal.")]
        for fixture in fixtures:
            fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
        first, second = (fixture.calls[0] for fixture in fixtures)
        self.assertNotEqual(first.output_schema, second.output_schema)
        self.assertNotEqual(first.input_fingerprint, second.input_fingerprint)
        self.assertNotEqual(first.input_fingerprint, replace(first, output_schema=second.output_schema).input_fingerprint)
        oversized = self.character_action_execution_fixture(agenda="x" * 120_000)
        self.assertEqual([], validate_registered_job(oversized.job))
        with self.assertRaises(ProductionRunError) as error:
            oversized.executor.execute_prepared(semantic_job=oversized.job, **oversized.args)
        self.assertEqual("semantic_output_schema_unsupported", error.exception.code)
        self.assertEqual([], oversized.calls)
        oversized.model.select_model.assert_not_called()
        oversized.model.invoke.assert_not_called()

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
                        "private_state": {"current_belief": "The key may be available.", "current_misperception": "A request has no cost.",
                                          "desired_gain": "Open the drawer.", "feared_loss": "Lose the record.", "expectations_of_others": []},
                        "proposals": [
                            {"strategy_id": "REQUEST", "action": "Request the key.", "gain": "Open the drawer.",
                             "risk_or_cost": "Expose the search.", "rejection_reason": None, "knowledge_basis": [
                                {"evidence_id": evidence_id, "use": "supports"} for evidence_id in job.context[0]["eligible_evidence_ids"]]},
                            {"strategy_id": "WAIT", "action": "Wait for access.", "gain": "Avoid notice.",
                             "risk_or_cost": "Lose time.", "rejection_reason": "Delay threatens the active agenda.", "knowledge_basis": []},
                        ], "selected_strategy_id": "REQUEST", "relationship_specific_interaction": []}
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
        self.assertEqual(set(job["output_contract"]["properties"]["proposals"]["items"]["required"]),
                         set(schema["properties"]["proposals"]["items"]["properties"]))
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
                                "private_state": {"current_belief": "The key may be available.", "current_misperception": "A request is safe.",
                                                  "desired_gain": "Open the drawer.", "feared_loss": "Lose the record.", "expectations_of_others": []},
                                "proposals": [
                                    {"strategy_id": "REQUEST", "action": "Request the key.", "gain": "Open the drawer.",
                                     "risk_or_cost": "Expose the search.", "rejection_reason": None, "knowledge_basis": [
                                        {"evidence_id": evidence_id, "use": "supports" if index == 0 else "uncertainty"}
                                        for index, evidence_id in enumerate(evidence_ids)]},
                                    {"strategy_id": "WAIT", "action": "Wait.", "gain": "Avoid notice.",
                                     "risk_or_cost": "Lose time.", "rejection_reason": "Delay threatens the agenda.", "knowledge_basis": []},
                                ], "selected_strategy_id": "REQUEST", "relationship_specific_interaction": []}
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

    def reader_expectation_update(self, **changes):
        return {"operation": "open", "expectation_id": "local:question", "expected_version": 0, "kind": "question",
                "description": "Will an answer arrive?", "detail": "The answer is still withheld.",
                "evidence_ref": "candidate:" + fingerprint_text(READER_CANDIDATE),
                "evidence_quote": "answer remains unknown", **changes}

    def reader_expectation_fixture(self, existing=(), updates=(), *, suffix="", reader_visible_context=()):
        job = make_contract_job("reader.expectations", "DOC-READER-FIXTURE", {
            "chapter_id": "CH-READER-FIXTURE", "document_id": "DOC-READER-FIXTURE",
            "candidate_text": READER_CANDIDATE, "candidate_fingerprint": fingerprint_text(READER_CANDIDATE),
            "current_reading_order": 2, "reader_visible_context": list(reader_visible_context), "existing_expectations": list(existing),
        }, source_session_id="SES-READER-FIXTURE", handoff_id="HANDOFF-READER-FIXTURE")
        judgment = {"confidence": 0.8, "expectation_updates": list(updates)}
        raw = " \n" + json.dumps(judgment, ensure_ascii=False, indent=2) + "\n" + suffix
        model = SimpleNamespace(
            select_model=Mock(return_value=SimpleNamespace(
                model_id="fixture-model", display_name=None, protocol="openai_chat_completions", metadata={}
            )),
            invoke=Mock(return_value=ModelTurn("openai_chat_completions", "fixture-model", text=raw, finish_reason="stop")),
        )
        calls, results = [], []

        def invoke(agent_job):
            calls.append(agent_job)
            result = AgentRunner(model, ToolRuntime()).run(agent_job)
            results.append(result)
            return result

        return SimpleNamespace(job=job, judgment=judgment, raw=raw, model=model, calls=calls, results=results,
            executor=RegisteredSemanticExecutor(SimpleNamespace(run=invoke)),
            args={"run": {"run_id": "RUN-READER-FIXTURE", "session_id": "SES-READER-FIXTURE", "task_mode": "DRAFT"},
                  "service_id": "fixture-service", "model_preference": None, "runtime_role": "registered_reader_expectations"})

    def test_reader_empty_ledger_native_profile_allows_only_new_open_zero_or_empty(self):
        from quality.reader_expectation import validate_observation_binding

        for updates in ([], [self.reader_expectation_update()]):
            with self.subTest(updates=updates):
                fixture = self.reader_expectation_fixture(updates=updates)
                binding = fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
                actual = fixture.calls[0]
                self.assertEqual(fixture.judgment, binding["result"]["judgment"])
                self.assertEqual([], validate_result(binding["job"], binding["result"]))
                _, normalized = validate_observation_binding(binding)
                self.assertEqual(len(updates), len(normalized))
                self.assertEqual(actual.output_schema, fixture.model.invoke.call_args.kwargs["output_schema"])
                constraints = actual.context[0]["reader_expectation_operation_constraints"]
                self.assertEqual([], constraints["live_existing_expectations"])
                self.assertEqual({"operation": "open", "expected_version": 0}, constraints["new_expectation"])
                self.assertIn("introduced and fully resolved within this chapter", actual.instruction)
                for operation in ("touch", "partial", "paid", "abandoned"):
                    invalid = {"confidence": 0.8, "expectation_updates": [self.reader_expectation_update(operation=operation)]}
                    self.assertEqual([], validate_typed_value(invalid, fixture.job["output_contract"]))
                    with self.assertRaises(ValueError):
                        validate_structured_text(json.dumps(invalid), actual.output_schema)
                with self.assertRaises(ValueError):
                    validate_structured_text(json.dumps({"confidence": 0.8, "expectation_updates": [
                        self.reader_expectation_update(expected_version=1)]}), actual.output_schema)

    def test_reader_live_native_profile_binds_each_id_to_its_exact_version(self):
        from quality.reader_expectation import validate_observation_binding

        live = [{"expectation_id": "EXP-OPEN", "version": 1, "status": "open"},
                {"expectation_id": "EXP-OPEN-SECOND", "version": 1, "status": "open"},
                {"expectation_id": "EXP-PARTIAL", "version": 3, "status": "partial"}]
        terminal = [{"expectation_id": "EXP-" + status.upper(), "version": 3, "status": status}
                    for status in ("paid", "invalidated", "abandoned")]
        updates = [self.reader_expectation_update(operation="touch", expectation_id="EXP-OPEN", expected_version=1),
                   self.reader_expectation_update(operation="paid", expectation_id="EXP-PARTIAL", expected_version=3)]
        fixture = self.reader_expectation_fixture(live + terminal, updates)
        binding = fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
        self.assertEqual(updates, validate_observation_binding(binding)[1])
        actual = fixture.calls[0]
        self.assertEqual([{"expectation_id": row["expectation_id"], "expected_version": row["version"]} for row in live],
                         actual.context[0]["reader_expectation_operation_constraints"]["live_existing_expectations"])
        for row in live:
            for operation in ("touch", "partial", "paid", "abandoned"):
                valid = {"confidence": 0.8, "expectation_updates": [self.reader_expectation_update(
                    operation=operation, expectation_id=row["expectation_id"], expected_version=row["version"])]}
                self.assertEqual(valid, validate_structured_text(json.dumps(valid), actual.output_schema))
                self.assertEqual([], validate_typed_value(valid, fixture.job["output_contract"]))
                valid["expectation_updates"][0]["due_by_order"] = 5
                self.assertEqual(valid, validate_structured_text(json.dumps(valid), actual.output_schema))
        invalid_pairs = [("EXP-UNKNOWN", 1), ("EXP-OPEN", 3), ("EXP-PARTIAL", 1), ("EXP-OPEN", 0)]
        invalid_pairs.extend((row["expectation_id"], row["version"]) for row in terminal)
        for identity, version in invalid_pairs:
            with self.subTest(identity=identity, version=version), self.assertRaises(ValueError):
                validate_structured_text(json.dumps({"confidence": 0.8, "expectation_updates": [self.reader_expectation_update(
                    operation="paid", expectation_id=identity, expected_version=version)]}), actual.output_schema)

    def test_reader_native_optional_deadline_preserves_exact_output_and_registered_contract(self):
        from quality.reader_expectation import validate_observation_binding

        for deadline in ({}, {"due_by_order": 2}, {"due_by_order": 5}):
            with self.subTest(deadline=deadline):
                fixture = self.reader_expectation_fixture(updates=[self.reader_expectation_update(
                    description="仅用于测试的未解问题。", **deadline)])
                original = deepcopy(fixture.job)
                original_raw_fingerprint = fingerprint_text(fixture.raw)
                binding = fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
                actual = fixture.calls[0]
                _, normalized = validate_observation_binding(binding)
                self.assertNotEqual("local:question", normalized[0]["expectation_id"])
                self.assertEqual("local:question", binding["result"]["judgment"]["expectation_updates"][0]["expectation_id"])
                self.assertEqual(fixture.judgment, binding["result"]["judgment"])
                self.assertEqual(fixture.raw, fixture.results[0].final_text)
                self.assertEqual(original_raw_fingerprint, fingerprint_text(fixture.results[0].final_text))
                self.assertEqual(original, fixture.job)
                self.assertEqual(original, binding["job"])
                self.assertEqual(worker_job_view(original), actual.context[0]["registered_semantic_job"])
                self.assertEqual([], validate_result(binding["job"], binding["result"]))
                self.assertNotIn("due_by_order", original["output_contract"]["properties"]["expectation_updates"]["items"]["required"])
                self.assertEqual(actual.input_fingerprint, binding["result"]["worker"]["agent_input_fingerprint"])
                self.assertEqual(actual.output_schema, actual.to_dict()["output_schema"])
                self.assertNotEqual(actual.input_fingerprint, replace(actual, output_schema=None).input_fingerprint)
                for invalid_deadline in (None, -1, True):
                    invalid = {"confidence": 0.8, "expectation_updates": [self.reader_expectation_update(due_by_order=invalid_deadline)]}
                    with self.assertRaises(ValueError):
                        validate_structured_text(json.dumps(invalid), actual.output_schema)

    def test_reader_native_schema_and_context_are_bound_to_frozen_ledger_only(self):
        other_context = [{"expectation_id": "EXP-NOT-IN-LEDGER", "version": 1, "status": "open"}]
        first = self.reader_expectation_fixture([{"expectation_id": "EXP-LIVE", "version": 1, "status": "open"}],
                                                reader_visible_context=other_context)
        second = self.reader_expectation_fixture([{"expectation_id": "EXP-LIVE", "version": 2, "status": "open"}])
        for fixture in (first, second):
            fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
            actual = fixture.calls[0]
            constraints = actual.context[0]["reader_expectation_operation_constraints"]
            self.assertEqual(fingerprint(fixture.job["input"]["payload"]["existing_expectations"]), constraints["source_fingerprint"])
            self.assertEqual("registered_semantic_job.input.payload.existing_expectations", constraints["source"])
        self.assertNotEqual(first.calls[0].output_schema, second.calls[0].output_schema)
        # Isolate the transport constraint from job ids/timestamps/context: the
        # schema itself changes the AgentJob fingerprint, not just its payload.
        self.assertNotEqual(first.calls[0].input_fingerprint,
                            replace(first.calls[0], output_schema=second.calls[0].output_schema).input_fingerprint)
        with self.assertRaises(ValueError):
            validate_structured_text(json.dumps({"confidence": 0.8, "expectation_updates": [self.reader_expectation_update(
                operation="paid", expectation_id="EXP-NOT-IN-LEDGER", expected_version=1)]}), first.calls[0].output_schema)

    def test_reader_native_rejects_fabricated_history_and_chaining_without_retry_or_byte_repair(self):
        opened = self.reader_expectation_update()
        paid = self.reader_expectation_update(operation="paid")
        for updates, suffix in (([paid], ""), ([opened, paid], ""), ([opened], "]}")):
            with self.subTest(updates=updates, suffix=suffix):
                fixture = self.reader_expectation_fixture(updates=updates, suffix=suffix)
                original = deepcopy(fixture.job)
                with self.assertRaises(ProductionRunError) as error:
                    fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
                self.assertEqual("semantic_pending", error.exception.code)
                self.assertEqual("model_failed", error.exception.detail["agent_status"])
                self.assertEqual("model_output_schema_invalid", error.exception.detail["errors"][0]["code"])
                self.assertEqual(1, fixture.model.invoke.call_count)
                self.assertEqual(1, fixture.model.select_model.call_count)
                self.assertFalse(fixture.model.select_model.call_args.kwargs["allow_probe"])
                self.assertEqual(1, len(fixture.results))
                self.assertEqual(1, fixture.results[0].model_requests)
                self.assertEqual(0, fixture.results[0].tool_calls)
                self.assertEqual(fixture.raw, fixture.results[0].final_text)
                self.assertEqual(original, fixture.job)

    def test_reader_native_rejects_malformed_or_oversized_frozen_ledger_before_dispatch(self):
        row = {"expectation_id": "EXP-LIVE", "version": 1, "status": "open"}
        invalid_rows = [[{**row, "version": value}] for value in (0, -1, True, "1")]
        invalid_rows.extend([
            [{**row, "expectation_id": ""}], [{**row, "status": "unknown"}], [row, deepcopy(row)],
            [{"expectation_id": "EXP-LIVE", "version": 1}],
            [{**row, "expectation_id": f"EXP-{index}"} for index in range(500)],
        ])
        for rows in invalid_rows:
            with self.subTest(count=len(rows), first=rows[0]):
                fixture = self.reader_expectation_fixture(rows)
                with self.assertRaises(ProductionRunError) as error:
                    fixture.executor.execute_prepared(semantic_job=fixture.job, **fixture.args)
                self.assertEqual("semantic_output_schema_unsupported", error.exception.code)
                self.assertEqual([], fixture.calls)
                fixture.model.select_model.assert_not_called()
                fixture.model.invoke.assert_not_called()

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

    def test_registered_self_audit_preserves_valid_response_regardless_of_observed_usage(self):
        candidate = "A bounded synthetic passage."
        author_objectives = {
            "schema": "quillframe_current_author_objectives_v1",
            "items": [{"objective_id": "OBJ-FIXTURE", "statement": "Keep the passage bounded.",
                       "source_refs": ["fixture:request"], "hard": True}],
            "source_fingerprint": fingerprint({"instruction": "Keep the passage bounded."}),
            "priority": "current_explicit_author_direction", "authority": False,
        }
        author_objectives["objectives_fingerprint"] = fingerprint(author_objectives)
        judgment = {
            "confidence": 1.0, "result": "pass", "report": "Synthetic self-audit result.",
            "dimensions": {name: "pass" for name in (
                "surface", "regression", "character_or_ownership", "natural_realization", "cluster")},
            "findings": [], "evidence_refs": ["candidate:" + fingerprint_text(candidate)],
            "objective_assessments": [{"objective_id": "OBJ-FIXTURE", "status": "met",
                "evidence_refs": ["candidate:paragraph-1"], "impact_scope": "whole_candidate",
                "repair_route": "no_change", "report": "The exact candidate is bounded."}],
        }
        args = {
            "run": {"run_id": "RUN-TOKEN-BUDGET", "session_id": "SES-TOKEN-BUDGET", "task_mode": "DRAFT"},
            "service_id": "fixture-service", "contract_id": "quality.candidate_self_audit",
            "subject_id": "DOC-TOKEN-BUDGET", "model_preference": None,
            "runtime_role": "registered_candidate_self_audit",
            "payload": {"candidate_text": candidate, "candidate_fingerprint": fingerprint_text(candidate),
                        "rule_material": [{"id": "RULE-FIXTURE", "authority": "framework", "statement": "A bounded synthetic rule."}],
                        "author_objectives": author_objectives},
        }
        for total_tokens in (40_000, 64_000, 64_001):
            with self.subTest(total_tokens=total_tokens):
                model = SimpleNamespace(
                    select_model=Mock(return_value=SimpleNamespace(
                        model_id="fixture-model", display_name=None, protocol="openai_chat_completions", metadata={}
                    )),
                    invoke=Mock(return_value=ModelTurn("openai_chat_completions", "fixture-model",
                        text=json.dumps(judgment), finish_reason="stop",
                        usage={"input_tokens": total_tokens - 2_000, "output_tokens": 2_000})),
                )
                invoke = Mock(wraps=AgentRunner(model, ToolRuntime()).run)
                executor = RegisteredSemanticExecutor(SimpleNamespace(run=invoke))
                with patch("agent_runtime.runner.time.monotonic", return_value=100.0):
                    binding = executor.execute(**args)
                    self.assertEqual(judgment, binding["result"]["judgment"])
                    self.assertEqual([], validate_result(binding["job"], binding["result"]))
                self.assertEqual(1, invoke.call_count)
                self.assertEqual(1, model.invoke.call_count)
                actual_job = invoke.call_args.args[0]
                self.assertEqual(1, actual_job.budgets.max_model_requests)
                self.assertEqual(1, actual_job.budgets.max_steps)
                self.assertEqual(DURABLE_REQUEST_TIMEOUT_MS, actual_job.budgets.max_elapsed_ms)
                self.assertEqual(4200, model.invoke.call_args.kwargs["max_output_tokens"])
                self.assertEqual(DURABLE_REQUEST_TIMEOUT_MS / 1000.0, model.invoke.call_args.kwargs["timeout_seconds"])
                self.assertIsNotNone(model.invoke.call_args.kwargs["output_schema"])
                self.assertEqual([], model.invoke.call_args.args[3])

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
        judgment = {"confidence": 1.0, "repair_owner": "reader_pressure", "revision_route": "voice_contamination",
                    "generation_mode": "fresh_realization",
                    "fix": "Advance the active question.", "repair_plan": "Reconstruct the current situation.",
                    "preserve": ["The active question."], "targets": [{"target_id": "TARGET-1",
                        "route": "fresh_realization", "scene_ref": None, "evidence_quote": "合成旧稿。",
                        "edit_window_quote": None}], "comparison_required": True}
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
