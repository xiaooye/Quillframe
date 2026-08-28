from __future__ import annotations

import inspect
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from agent_runtime import AgentJob, AgentResult
from core_operations import CoreOperations, OperationError
from harness.context_runtime import MANDATORY_PRODUCTION_MECHANISMS, fingerprint
from harness.semantic_workers.independent_invocation_receipt import (
    build_receipt as build_native_receipt,
    fingerprint as native_fingerprint,
    validate_receipt as validate_native_receipt,
)
from persistence.independent_review_repository import IndependentReviewError, IndependentReviewRepository
from persistence.quillframe_sqlite import QuillframeStore, fingerprint_text, now_iso
from production_runtime import PRODUCTION_MECHANISMS, ProductionRunError, ProductionRunExecutor
from production_runtime.context import ProductionContextRuntime
from production_runtime.reading_positioning import (
    DECLARATION_SCHEMA, READER_FIELDS, build_reading_positioning, reading_positioning_fields,
)
from production_runtime.workflow_service import NovelWorkflowService

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_ROOT = ROOT / "harness" / "semantic_workers"
if str(SEMANTIC_ROOT) not in sys.path:
    sys.path.insert(0, str(SEMANTIC_ROOT))
from peer_bridge_receipt import build_receipt  # noqa: E402

RULE_MATERIAL = [
    {
        "id": "HF-CI",
        "authority": "framework",
        "statement": "Synthetic production-runtime contract rule only.",
    }
]
PROVENANCE = {
    "project_id": "PROD",
    "project_repo": "owner/project",
    "framework_repo": "owner/framework",
    "framework_commit": "f" * 40,
}
READER_POSITIONING = {
    "schema": DECLARATION_SCHEMA, "visibility": "reader_eligible",
    "genre_profile": "都市关系小说", "platform_profile": "中文移动端连载",
}

PUBLIC_MANUSCRIPT_KEYS = {"peer_packet", "peer_packet_bytes", "candidate_text"}
PRE_RELEASE_MANUSCRIPT = "Review prose ready for the user-visible gate."


def assert_public_execution_safe(case: unittest.TestCase, value: object) -> None:
    def visit(node: object) -> None:
        if isinstance(node, dict):
            case.assertTrue(PUBLIC_MANUSCRIPT_KEYS.isdisjoint(node), node)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    serialized = json.dumps(value, ensure_ascii=False)
    case.assertNotIn(PRE_RELEASE_MANUSCRIPT, serialized)
    case.assertNotIn("INTERNAL RAW DRAFT", serialized)


class FakeAgentRuntime:
    """Deterministic contract fixture; explicitly not live-provider acceptance."""

    def __init__(self, *, reject_mechanism: str | None = None, invalid_selector: bool = False) -> None:
        self.reject_mechanism = reject_mechanism
        self.invalid_selector = invalid_selector
        self.calls: list[AgentJob] = []

    def run(self, job: AgentJob, *, cancellation=None) -> AgentResult:  # noqa: ANN001
        self.calls.append(job)
        role = job.runtime_role
        if role == "context_profile_deriver":
            packet = job.context[0]
            payload = {
                "description": f"profile for {packet['source_object_id']}",
                "trigger_when": "when relevant to the current production stage",
                "estimated_tokens": 16,
                "semantic_tags": [packet["source_object_type"]],
                "stage_affinities": list(packet["allowed_stage_ids"]),
            }
        elif role == "context_selector":
            packet = job.context[0]
            eligible = packet["eligible"]
            if self.invalid_selector:
                selections = [
                    {
                        "profile_id": "CTXPROF-NOT-IN-UNIVERSE",
                        "stage_id": packet["stage_id"],
                        "priority": 100,
                        "reason_code": "bad",
                        "reason": "invalid test id",
                        "required_for_grounding": False,
                    }
                ]
            else:
                selections = [
                    {
                        "profile_id": row["profile_id"],
                        "stage_id": packet["stage_id"],
                        "priority": 100 - index,
                        "reason_code": "eligible",
                        "reason": "fixture selects eligible source",
                        "required_for_grounding": False,
                    }
                    for index, row in enumerate(eligible)
                ]
            payload = {"selections": selections}
        elif role == "character_state_prepare":
            payload = {"status": "pass", "characters": [], "summary": "No synthetic cast needed.", "findings": []}
        elif role == "registered_character_action":
            source = job.context[0]["registered_semantic_job"]["input"]["payload"]
            payload = {"confidence": 1.0, "character_id": source["character_id"], "active_agenda": source["active_agenda"],
                       "proposals": [{"action": "A requests the disputed document.", "knowledge_basis": []}]}
        elif role == "registered_scene_resolution":
            payload = {"confidence": 1.0, "interaction_trace": "A requests the document; the clerk delays.",
                       "observable_trajectory": "The unanswered request remains on the desk.",
                       "unresolved_pressures": ["The requested document remains withheld."],
                       "repair_routes": [{"owner": "scene", "reason": "fixture rejection"}] if self.reject_mechanism == "scene_simulation" else []}
        elif role == "registered_scene_projection":
            source = job.context[0]["registered_semantic_job"]["input"]["payload"]
            payload = {"confidence": 1.0, "scene_id": source["scene_id"],
                       "interaction_trace": "A requests the document; the clerk delays.",
                       "writer_context": "Show the refused request and its observable cost.",
                       "observable_event_refs": [], "unresolved_pressures": ["The document is withheld."]}
        elif role == "registered_reader_pressure":
            source = job.context[0]["registered_semantic_job"]["input"]["payload"]
            payload = {"confidence": 1.0, "status": "pass", "summary": "The refused request has a cost.",
                       "pressure_points": [{"question": "Will the request succeed?", "expected_reward": "An answer to the request.",
                                            "delay_cost": "The meeting ends.", "evidence_refs": [source["sources"][0]["source_ref"]]}],
                       "proposed_net_change": "The request acquires a deadline.", "next_chapter_pull": "A decision remains."}
        elif role == "registered_reader_expectations":
            payload = {"confidence": 1.0, "expectation_updates": []}
        elif role == "registered_narrative_state":
            payload = {"confidence": 1.0, "changes": []}
        elif role == "registered_reader_engagement":
            payload = {
                "confidence": 1.0,
                "result": "pass",
                "report": "Synthetic Blind Reader pass.",
                "strongest_positive": "The candidate is coherent.",
                "strongest_problem": None,
                "evidence_refs": ["candidate:synthetic"],
            }
        elif role == "registered_candidate_self_audit":
            payload = {
                "confidence": 1.0,
                "result": "pass",
                "report": "Synthetic manager audit pass.",
                "dimensions": {
                    "surface": "pass",
                    "regression": "pass",
                    "character_or_ownership": "pass",
                    "natural_realization": "pass",
                    "cluster": "pass",
                },
                "findings": [],
                "evidence_refs": ["candidate:synthetic"],
            }
        elif role == "event_first_raw_draft":
            payload = {
                "status": "fail" if self.reject_mechanism == role else "pass",
                "text": "INTERNAL RAW DRAFT",
                "summary": "event-first draft",
                "findings": [],
            }
        elif role == "surface_realization":
            payload = {
                "status": "fail" if self.reject_mechanism == role else "pass",
                "text": "Review prose ready for the user-visible gate.",
                "summary": "surface candidate",
                "findings": [],
            }
        else:
            payload = {
                "status": "fail" if self.reject_mechanism == role else "pass",
                "summary": role,
                "findings": ["fixture rejection"] if self.reject_mechanism == role else [],
                "artifact": {"role": role},
            }
        return AgentResult(
            job_id=job.job_id,
            session_id=job.session_id,
            run_id=job.run_id,
            status="completed",
            model_service_id=job.service_id,
            model_id="fixture-model",
            protocol="fixture_protocol",
            input_fingerprint=job.input_fingerprint,
            final_text=json.dumps(payload),
            steps=1,
            model_requests=1,
        )


REPAIRED_FIXTURE_TEXT = "Repaired synthetic candidate with the original objective intact."


class RepairFixtureRuntime(FakeAgentRuntime):
    """Synthetic repair judgments only; never live acceptance evidence."""

    def __init__(self, *, generation_mode="local_or_bounded_repair", comparison_outcome="successful_repair", repair_audit_fails=False,
                 draft_reader_result=None):
        super().__init__()
        self.generation_mode = generation_mode
        self.comparison_outcome = comparison_outcome
        self.repair_audit_fails = repair_audit_fails
        self.draft_reader_result = draft_reader_result

    def run(self, job, *, cancellation=None):
        result = super().run(job, cancellation=cancellation)
        payload = json.loads(result.final_text)
        if job.runtime_role == "registered_reader_engagement" and job.task_mode == "DRAFT" and self.draft_reader_result is not None:
            payload.update({"result": self.draft_reader_result, "report": "PRIVATE READER DIAGNOSIS",
                            "strongest_problem": "Synthetic Reader concern."})
        elif job.runtime_role == "registered_candidate_self_audit" and (
                (job.task_mode == "DRAFT" and self.draft_reader_result is None) or self.repair_audit_fails):
            payload.update({"result": "fail", "report": "PRIVATE SYNTHETIC DIAGNOSIS",
                            "dimensions": {**payload["dimensions"], "surface": "fail"},
                            "findings": [{"finding_id": "F-SYN", "mechanism_id": "synthetic_continuity", "severity": "high",
                                          "scope": "paragraph", "repair_owner": "continuity", "blocking": True,
                                          "report": "PRIVATE SYNTHETIC DIAGNOSIS", "function_assessment": "pass",
                                          "ownership_assessment": "pass", "natural_realization_assessment": "fail",
                                          "evidence_refs": ["candidate:synthetic"]}]})
        elif job.runtime_role == "registered_repair_editor":
            payload = {"confidence": 1.0, "repair_owner": "continuity", "generation_mode": self.generation_mode,
                       "fix": "Resolve the synthetic continuity defect.", "preserve": ["The explicit author objective."],
                       "repair_plan": "PRIVATE EDITOR TRAJECTORY", "comparison_required": True}
        elif job.runtime_role == "registered_repair_comparison":
            regression = self.comparison_outcome == "objective_regression"
            payload = {"confidence": 1.0, "winner": "incumbent" if regression else "challenger", "reason": "Synthetic comparison.",
                       "target_outcome": "improved", "objective_preservation": "degraded" if regression else "preserved",
                       "reader_value": "unchanged", "character_relationship_energy": "preserved",
                       "outcome_class": self.comparison_outcome, "repaired_findings": ["F-SYN"],
                       "introduced_regressions": ["reader"] if regression else [], "regressed_dimensions": ["reader"] if regression else [],
                       "preserved_strengths": ["author objective"], "evidence": ["candidate:synthetic"]}
        elif job.runtime_role == "surface_realization" and job.task_mode == "REVISE":
            payload["text"] = REPAIRED_FIXTURE_TEXT
        return replace(result, final_text=json.dumps(payload))


class PreparedCastFixtureRuntime(FakeAgentRuntime):
    """Exercise a nonempty producer/consumer boundary without a real model."""

    def __init__(self, *, malformed=False):
        super().__init__()
        self.malformed = malformed
        self.preparation = None

    def run(self, job: AgentJob, *, cancellation=None) -> AgentResult:
        result = super().run(job, cancellation=cancellation)
        if job.runtime_role == "character_state_prepare":
            order = job.context[0]["target_context"]["current_story_order"]
            character = {
                "character_id": "CHAR-PROPOSED", "current_story_order": order, "active_agenda": "obtain the record",
                "perceived_state": {"summary": "The record is withheld."},
                "immediate_situation": {"observables": [
                    {"observable_id": "OBS-NOW", "observation": "The drawer is closed.", "source_ref": "fixture:drawer", "available_from_story_order": order},
                    {"observable_id": "OBS-FUTURE", "observation": "UNAVAILABLE FUTURE OBSERVATION", "source_ref": "fixture:future", "available_from_story_order": order + 1},
                ]},
                "perspective_memory": {
                    "episodic_visible_events": [], "situation_patterns": [],
                    "visibility_tagged_facts": [{"fact_id": "FACT-OWN", "claim": "PRIVATE INITIAL MEMORY: I saw the clerk pocket the drawer key.", "source_ref": "fixture:firsthand-witness", "available_from_story_order": order}],
                },
            }
            if self.malformed:
                character["perceived_state"]["observables"] = character["immediate_situation"].pop("observables")
                character["perspective_memory"]["facts"] = character["perspective_memory"].pop("visibility_tagged_facts")
            self.preparation = {"status": "pass", "characters": [character], "summary": "Synthetic cast proposal.", "findings": []}
            result.final_text = json.dumps(self.preparation)
        elif job.runtime_role == "registered_character_action":
            judgment = json.loads(result.final_text)
            judgment["proposals"][0]["knowledge_basis"] = [
                {"evidence_id": evidence_id, "use": "supports"} for evidence_id in job.context[0]["eligible_evidence_ids"]
            ]
            result.final_text = json.dumps(judgment)
        return result


class FinalStateFixtureRuntime(FakeAgentRuntime):
    """Nonempty typed state fixtures, never evidence of model quality."""

    def __init__(self, *, narrative=True, reader_operation="open", candidate_text=PRE_RELEASE_MANUSCRIPT,
                 invalid_quote=False):
        super().__init__()
        self.narrative = narrative
        self.reader_operation = reader_operation
        self.candidate_text = candidate_text
        self.invalid_quote = invalid_quote

    def run(self, job: AgentJob, *, cancellation=None) -> AgentResult:
        result = super().run(job, cancellation=cancellation)
        if job.runtime_role == "surface_realization":
            judgment = json.loads(result.final_text)
            judgment["text"] = self.candidate_text
            result.final_text = json.dumps(judgment)
        if job.runtime_role not in {"registered_reader_expectations", "registered_narrative_state"}:
            return result
        source = job.context[0]["registered_semantic_job"]["input"]["payload"]
        quote = "unwritten future payoff" if self.invalid_quote else source["candidate_text"][:12]
        if job.runtime_role == "registered_reader_expectations":
            existing = source["existing_expectations"]
            prior = existing[0] if existing and self.reader_operation != "open" else None
            update = {"operation": self.reader_operation, "expectation_id": prior["expectation_id"] if prior else "local:question",
                      "expected_version": prior["version"] if prior else 0, "kind": "question",
                      "description": "Synthetic unresolved request.", "detail": "Fixture final-text observation.",
                      "evidence_ref": "candidate:" + source["candidate_fingerprint"], "evidence_quote": quote}
            if self.reader_operation == "open":
                update["due_by_order"] = source["current_reading_order"] + 2
            result.final_text = json.dumps({"confidence": 1.0, "expectation_updates": [update]})
        elif self.narrative:
            changes = [
                {"entity_type": "character", "entity_ref": "CHAR-A", "fields": {
                    "name": "A", "agenda": "seek a reply", "voice_notes": "precise", "state": {"perceived_state": {"location": "gate"}}}},
                {"entity_type": "character", "entity_ref": "local:visitor", "fields": {
                    "name": "Fixture visitor", "agenda": "seek entry", "voice_notes": "plain", "state": {}}},
                {"entity_type": "relationship", "entity_ref": "local:meeting", "fields": {
                    "participant_a": "CHAR-A", "participant_b": "local:visitor", "relationship_type": "met", "state": {"public": True}}},
                {"entity_type": "world", "entity_ref": "local:gate", "fields": {
                    "entity_type": "fixture_gate", "name": "Gate", "truth": {"open": False}}},
                {"entity_type": "timeline", "entity_ref": "local:arrival", "fields": {
                    "story_order": source["current_story_order"], "title": "Arrival", "description": "Fixture arrival at the gate."}},
                {"entity_type": "knowledge", "entity_ref": "local:visible_gate", "fields": {
                    "character_id": "local:visitor", "fact": {"gate_visible": True},
                    "available_from_story_order": source["current_story_order"], "confidence": "observed"}},
            ]
            result.final_text = json.dumps({"confidence": 1.0, "changes": [{**item, "evidence_quote": quote} for item in changes]})
        return result


class ManualClock:
    def __init__(self, value: float = 1_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def frozen_handoff(store: QuillframeStore, run_id: str) -> dict:
    with store.open_project("PROD") as conn:
        row = conn.execute(
            "SELECT state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_independent_handoff' ORDER BY created_at DESC,rowid DESC LIMIT 1",
            (run_id,),
        ).fetchone()
    if not row:
        raise AssertionError("internal independent handoff fixture is missing")
    return json.loads(row["state_json"])


def frozen_packet(store: QuillframeStore, run_id: str) -> dict:
    return frozen_handoff(store, run_id)["peer_packet"]


def peer_result(packet: dict, verdict: str = "pass") -> dict:
    job = packet["job"]
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": "chatgpt_peer_chat",
            "model_or_reviewer": "synthetic-independent-fixture",
            "run_reference": packet["relay_nonce"],
        },
        "judgment": {
            "confidence": 1.0,
            "result": verdict,
            "report": f"Synthetic independent {verdict}.",
            "evidence_refs": ["candidate:synthetic"],
        },
        "proposals": [],
        "errors": [],
    }


def project_bridge_receipt(packet: dict, result: dict) -> dict:
    return build_receipt(
        packet,
        result,
        project_id=PROVENANCE["project_id"],
        project_repo=PROVENANCE["project_repo"],
        framework_repo=PROVENANCE["framework_repo"],
        framework_commit=PROVENANCE["framework_commit"],
        issue_number=1,
        runtime_trace={
            "github_run_id": 1,
            "github_run_attempt": 1,
            "github_event_name": "issue_comment",
            "result_comment_id": 1,
            "workflow_name": "Synthetic project peer bridge fixture",
            "framework_action_ref": PROVENANCE["framework_commit"],
        },
    )


def native_result(claim: dict, verdict: str = "pass") -> dict:
    packet = claim["peer_packet"]
    job = packet["job"]
    provider = claim["provider"]
    return {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {
            "provider": provider,
            "model_or_reviewer": f"synthetic-{provider}-fixture",
            "run_reference": packet["relay_nonce"],
        },
        "judgment": {
            "confidence": 1.0,
            "result": verdict,
            "report": f"Synthetic native independent {verdict}.",
            "evidence_refs": ["candidate:synthetic"],
        },
        "proposals": [],
        "errors": [],
    }


class ProductionRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = QuillframeStore(Path(self.temp.name))
        self.store.create_project("PROD", "Production Fixture")
        with self.store.open_project("PROD") as conn:
            conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) VALUES('CH001','chapter',1,'Chapter','{}')")
            conn.commit()
        self.store.create_document("PROD", "DOC-1", "Chapter", story_node_id="CH001")
        self.store.save_revision("PROD", "DOC-1", "seed", expected_parent_revision_id=None, source="test")
        stamp = now_iso()
        with self.store.open_project("PROD") as conn:
            conn.execute(
                "INSERT INTO characters(character_id,name,agenda,voice_notes,state_json,updated_at) VALUES(?,?,?,?,?,?)",
                ("CHAR-A", "A", "protect the deal", "precise", "{}", stamp),
            )
            conn.execute(
                "INSERT INTO character_knowledge(knowledge_id,character_id,claim_ref,fact_json,available_from_story_order,evidence_ref,confidence) VALUES(?,?,?,?,?,?,?)",
                ("KN-A", "CHAR-A", None, '{"fact":"private knowledge"}', 1, "accepted", "known"),
            )
            conn.execute(
                "INSERT INTO research_sources(source_id,title,source_uri,source_kind,rights_json,provenance_json,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                ("RS-1", "Research", None, "fixture", "{}", "{}", "active", stamp),
            )
            conn.execute(
                "INSERT INTO research_claims(research_claim_id,source_id,claim_text,citation_json,fictionalization_notes,character_knowledge_boundary_json,canon_status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                ("RC-1", "RS-1", "external fact", "{}", None, "{}", "research_only", stamp),
            )
            conn.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def start(self, *, chapter_id="CH001", document_id="DOC-1", selected_preference_ids=None, reader_positioning=None) -> str:
        payload = {"instruction": "draft chapter", "chapter_id": chapter_id}
        if selected_preference_ids is not None:
            payload["selected_preference_ids"] = selected_preference_ids
        if reader_positioning is not None:
            payload["reader_positioning"] = reader_positioning
        run_id = CoreOperations(self.store).start_author_run(
            "PROD",
            task_mode="DRAFT",
            target_ref=document_id,
            payload=payload,
        )["run_id"]
        NovelWorkflowService(self.store).start(
            project_id="PROD",
            run_id=run_id,
            chapter_id=chapter_id,
            author_profile="guided",
        )
        return run_id

    def execute_to_handoff(self, runtime: ProductionRunExecutor, run_id: str) -> dict:
        return runtime.execute(
            "PROD",
            run_id,
            service_id="svc",
            instruction="draft chapter",
            reader_grip="very_high",
            rule_material=RULE_MATERIAL,
            independent_provenance=PROVENANCE,
        )

    def submit(self, runtime: ProductionRunExecutor, run_id: str, verdict: str = "pass") -> dict:
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, verdict)
        return runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=project_bridge_receipt(packet, result),
        )

    def test_full_graph_uses_frozen_context_and_real_external_independent_boundary(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        handoff = self.execute_to_handoff(runtime, run_id)

        self.assertEqual(handoff["status"], "awaiting_external")
        self.assertEqual(handoff["awaiting"], "independent_semantic_review")
        self.assertFalse(handoff["candidate_visible"])
        assert_public_execution_safe(self, handoff)
        replay = self.execute_to_handoff(runtime, run_id)
        assert_public_execution_safe(self, replay)
        self.assertEqual(handoff, replay)
        self.assertFalse(any(job.runtime_role == "independent_semantic_gate" for job in fake.calls))
        self.assertIn("registered_reader_engagement", [job.runtime_role for job in fake.calls])
        self.assertIn("registered_candidate_self_audit", [job.runtime_role for job in fake.calls])
        target = runtime._target_context(runtime._latest_bundle("PROD", run_id))
        for job in fake.calls:
            if job.runtime_role in {"story_canon_preflight", "event_first_raw_draft", "surface_realization", "continuity"}:
                self.assertEqual(job.context[0]["target_context"], target)
                self.assertFalse(job.context[0]["frozen_stage_context"]["authority"])
                self.assertFalse(job.context[0]["frozen_stage_context"]["db_fetch_performed"])
                self.assertEqual(job.authority, {})
        packet = frozen_packet(self.store, run_id)
        self.assertTrue(packet["return_binding"]["fresh_conversation_required"])
        self.assertTrue(packet["return_binding"]["same_project_writer_chat_forbidden"])
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 0)

        completed = self.submit(runtime, run_id)
        self.assertEqual(completed["status"], "completed")
        self.assertTrue(completed["candidate_visible"])
        self.assertFalse(completed["raw_draft_visible"])
        self.assertFalse(completed["accepted"])
        self.assertFalse(completed["settled"])
        self.assertTrue(completed["production_release"]["ready_for_user_visible_review"])
        self.assertEqual(completed["production_release"]["candidate_fingerprint"], completed["candidate"]["candidate_fingerprint"])
        self.assertEqual(
            tuple(PRODUCTION_MECHANISMS),
            tuple(x for x in MANDATORY_PRODUCTION_MECHANISMS if x != "context_freeze"),
        )
        self.assertNotIn("INTERNAL RAW DRAFT", json.dumps(completed))
        for receipt in completed["stage_receipts"]:
            self.assertIs(receipt["private_reasoning_exposed"], False)
            self.assertIs(receipt["raw_draft_visible"], False)
        with self.store.open_project("PROD") as conn:
            candidate = conn.execute("SELECT * FROM candidates WHERE run_id=?", (run_id,)).fetchone()
            evidence = conn.execute("SELECT * FROM review_evidence WHERE candidate_id=?", (candidate["candidate_id"],)).fetchone()
            self.assertEqual(candidate["status"], "review_draft")
            self.assertEqual(candidate["user_visible_gate"], "PASS")
            self.assertEqual(evidence["independent"], 1)
            self.assertEqual(evidence["evidence_kind"], "quality.production_review")
            release_rows = conn.execute("SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_release'", (run_id,)).fetchall()
            self.assertEqual(len(release_rows), 1)
        visible = CoreOperations(self.store).candidate_visible_get("PROD", candidate_id=completed["candidate"]["candidate_id"])
        self.assertEqual(visible["content"], "Review prose ready for the user-visible gate.")

    def test_stage_materializer_has_no_database_access_path(self):
        source = inspect.getsource(ProductionRunExecutor.materialize_stage_context).lower()
        self.assertNotIn("sqlite", source)
        self.assertNotIn("open_project", source)
        self.assertNotIn("self.store", source)

    def test_reading_positioning_reaches_actual_writer_pressure_reader_and_independent_jobs(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start(reader_positioning=READER_POSITIONING)
        self.assertEqual("awaiting_external", self.execute_to_handoff(runtime, run_id)["status"])
        expected = {
            "reader_grip": "very_high", "chapter_position": "reading_order=1",
            "genre_profile": READER_POSITIONING["genre_profile"],
            "platform_profile": READER_POSITIONING["platform_profile"],
        }
        writers = [job for job in fake.calls if job.runtime_role in {"event_first_raw_draft", "surface_realization"}]
        self.assertEqual(2, len(writers))
        for writer in writers:
            self.assertEqual(expected, writer.context[0]["reading_positioning"])
            for guidance in (
                "causal constraints, not the shape of the prose", "Choose narrative time deliberately",
                "Within the authorized viewpoint", "relationship context and distinct voice",
                "interchangeable bodily reactions", "There are no sentence-length",
                "A quiet or procedural scene can be rewarding", "not a license to imitate a named author",
            ):
                self.assertIn(guidance, writer.instruction)
            altered = deepcopy(writer.context)
            altered[0]["reading_positioning"]["genre_profile"] = "另一个明确定位"
            self.assertNotEqual(writer.input_fingerprint, replace(writer, context=altered).input_fingerprint)
        for role in ("registered_reader_pressure", "registered_reader_engagement"):
            job = next(job for job in fake.calls if job.runtime_role == role)
            payload = job.context[0]["registered_semantic_job"]["input"]["payload"]
            self.assertEqual(expected, {key: payload[key] for key in READER_FIELDS if key in payload})
        independent = frozen_packet(self.store, run_id)["job"]["input"]["payload"]
        self.assertEqual(expected, {key: independent[key] for key in READER_FIELDS if key in independent})
        self.assertNotIn("source_binding", independent)
        self.assertNotIn("author_model", independent)
        qualified = runtime._latest_checkpoint("PROD", run_id, "production_qualified_candidate")
        bundle = runtime._latest_bundle("PROD", run_id)
        positioning = qualified["reading_positioning"]
        self.assertEqual(fingerprint(bundle["target_context"]), positioning["source_binding"]["author_request_fingerprint"])
        self.assertEqual(fingerprint(runtime.stage_repository.load_request("PROD", run_id)),
                         positioning["source_binding"]["execution_request_fingerprint"])
        self.assertEqual(expected, reading_positioning_fields(
            positioning, target_context=bundle["target_context"], reader_grip="very_high",
        ))
        before = len(fake.calls)
        packet = frozen_packet(self.store, run_id)
        runtime.resume_execution("PROD", run_id)
        self.assertEqual(before, len(fake.calls))
        self.assertEqual(packet, frozen_packet(self.store, run_id))

    def test_plan_labels_and_private_state_are_not_promoted_to_blind_reader_positioning(self):
        plan = {
            "content": "FUTURE PLAN SENTINEL: an unrevealed later outcome.",
            "reader_positioning": {**READER_POSITIONING, "genre_profile": "PRIVATE PLAN LABEL"},
            "genre_profile": "PRIVATE UNTYPED GENRE", "platform_profile": "PRIVATE UNTYPED PLATFORM",
        }
        stamp = now_iso()
        with self.store.open_project("PROD") as conn:
            conn.execute(
                "INSERT INTO plans(plan_id,task_mode,target_id,status,plan_json,content_fingerprint,created_at,updated_at) "
                "VALUES('PLAN-POSITIONING','DESIGN-BOOK','book','active',?,?,?,?)",
                (json.dumps(plan), fingerprint(plan), stamp, stamp),
            )
            conn.commit()
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        self.execute_to_handoff(runtime, run_id)
        writer = next(job for job in fake.calls if job.runtime_role == "event_first_raw_draft")
        pressure = next(job for job in fake.calls if job.runtime_role == "registered_reader_pressure")
        for value in (writer.context, pressure.context):
            serialized = json.dumps(value)
            self.assertIn("FUTURE PLAN SENTINEL", serialized)  # Authorized generation context is retained.
            self.assertNotIn("private knowledge", serialized)
        self.assertEqual({"reader_grip": "very_high", "chapter_position": "reading_order=1"},
                         writer.context[0]["reading_positioning"])
        reader = next(job for job in fake.calls if job.runtime_role == "registered_reader_engagement")
        for value in (reader.context, frozen_packet(self.store, run_id)):
            serialized = json.dumps(value)
            for excluded in ("FUTURE PLAN SENTINEL", "PRIVATE PLAN LABEL", "PRIVATE UNTYPED", "private knowledge"):
                self.assertNotIn(excluded, serialized)
        for payload in (reader.context[0]["registered_semantic_job"]["input"]["payload"],
                        frozen_packet(self.store, run_id)["job"]["input"]["payload"]):
            self.assertNotIn("genre_profile", payload)
            self.assertNotIn("platform_profile", payload)

    def test_reader_positioning_rejects_private_or_untyped_fields_before_model_dispatch(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        invalid = [None, "an untyped profile", {"genre_profile": "unknown provenance"},
                   {**READER_POSITIONING, "visibility": "creator_private"},
                   {**READER_POSITIONING, "genre_profile": {"future_plan": "private"}},
                   {**READER_POSITIONING, "genre_profile": True},
                   {**READER_POSITIONING, "platform_profile": "two\nlines"},
                   {**READER_POSITIONING, "platform_profile": "x" * 161}]
        invalid.extend({**READER_POSITIONING, key: "PRIVATE INPUT"} for key in (
            "future_plan", "prior_review", "author_intent", "hidden_expected", "private_character_state",
            "chapter_position", "reader_grip",
        ))
        for declaration in invalid:
            with self.subTest(declaration=declaration):
                run_id = self.start()
                # Exercise runtime revalidation even if a malformed value was
                # present in durable input before the current Core validator.
                with self.store.open_project("PROD") as conn:
                    target = json.loads(conn.execute("SELECT state_json FROM checkpoints WHERE checkpoint_id=?", ("request:" + run_id,)).fetchone()[0])
                    target["payload"]["reader_positioning"] = declaration
                    conn.execute("UPDATE checkpoints SET state_json=?,artifact_fingerprint=? WHERE checkpoint_id=?",
                                 (json.dumps(target), fingerprint(target), "request:" + run_id))
                    conn.commit()
                with self.assertRaises(ProductionRunError) as caught:
                    self.execute_to_handoff(runtime, run_id)
                self.assertEqual("reader_positioning_invalid", caught.exception.code)
        self.assertEqual([], fake.calls)

    def test_reading_positioning_changes_invalidate_bundle_and_projection_fingerprints(self):
        from production_runtime.contracts import validate_bundle_integrity
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start(reader_positioning=READER_POSITIONING)
        self.execute_to_handoff(runtime, run_id)
        bundle = runtime._latest_bundle("PROD", run_id)
        qualified = runtime._latest_checkpoint("PROD", run_id, "production_qualified_candidate")
        changed = deepcopy(bundle)
        changed["target_context"]["payload"]["reader_positioning"]["genre_profile"] = "different public label"
        with self.assertRaises(ProductionRunError) as caught:
            validate_bundle_integrity(changed)
        self.assertEqual("context_bundle_invalid", caught.exception.code)
        original = qualified["reading_positioning"]
        altered = deepcopy(original)
        altered["reader_fields"]["genre_profile"] = "PRIVATE REPLACEMENT"
        altered["positioning_fingerprint"] = fingerprint({key: value for key, value in altered.items() if key != "positioning_fingerprint"})
        with self.assertRaises(ProductionRunError) as caught:
            reading_positioning_fields(altered, target_context=bundle["target_context"], reader_grip="very_high")
        self.assertEqual("reader_positioning_mismatch", caught.exception.code)
        with self.assertRaises(ProductionRunError) as caught:
            reading_positioning_fields(original, target_context=bundle["target_context"], reader_grip="very_high",
                                       execution_request_fingerprint="sha256:" + "0" * 64)
        self.assertEqual("reader_positioning_mismatch", caught.exception.code)
        rebuilt = build_reading_positioning(target_context=changed["target_context"], reader_grip="very_high",
                                            execution_request_fingerprint=original["source_binding"]["execution_request_fingerprint"])
        self.assertNotEqual(original["positioning_fingerprint"], rebuilt["positioning_fingerprint"])

    def test_qualified_reader_positioning_cannot_be_dropped_or_rewritten_before_independent_dispatch(self):
        for mutation in ("drop", "rewrite"):
            with self.subTest(mutation=mutation):
                fake = FakeAgentRuntime()
                runtime = ProductionRunExecutor(self.store, fake)
                run_id = self.start(reader_positioning=READER_POSITIONING)
                result = runtime.execute("PROD", run_id, service_id="svc", instruction="draft chapter",
                                         reader_grip="very_high", rule_material=RULE_MATERIAL)
                self.assertEqual("independent_provenance", result["awaiting"])
                with self.store.open_project("PROD") as conn:
                    row = conn.execute("SELECT checkpoint_id,state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_qualified_candidate'", (run_id,)).fetchone()
                    qualified = json.loads(row["state_json"])
                    if mutation == "drop":
                        del qualified["reading_positioning"]
                    else:
                        qualified["reading_positioning"]["reader_fields"]["genre_profile"] = "different public label"
                    conn.execute("UPDATE checkpoints SET state_json=? WHERE checkpoint_id=?", (json.dumps(qualified), row["checkpoint_id"]))
                    conn.commit()
                before = len(fake.calls)
                with self.assertRaises(ProductionRunError) as caught:
                    self.execute_to_handoff(runtime, run_id)
                self.assertEqual("reader_positioning_missing" if mutation == "drop" else "reader_positioning_mismatch", caught.exception.code)
                self.assertEqual(before, len(fake.calls))
                self.assertIsNone(runtime._latest_checkpoint("PROD", run_id, "production_independent_handoff"))

    def test_character_simulation_excludes_research_but_keeps_character_knowledge(self):
        context_runtime = ProductionContextRuntime(self.store, FakeAgentRuntime())
        bundle = context_runtime.prepare_context("PROD", self.start(), service_id="svc", instruction="draft")
        character = ProductionRunExecutor.materialize_stage_context(bundle, "character_simulation")
        draft = ProductionRunExecutor.materialize_stage_context(bundle, "event_first_raw_draft")
        self.assertIn("character_knowledge", {row["domain"] for row in character["items"]})
        self.assertNotIn("research", {row["domain"] for row in character["items"]})
        self.assertIn("research", {row["domain"] for row in draft["items"]})
        self.assertFalse(character["db_fetch_performed"])

    def test_invalid_selector_id_is_rejected_not_guessed(self):
        runtime = ProductionContextRuntime(self.store, FakeAgentRuntime(invalid_selector=True))
        with self.assertRaises(ProductionRunError) as caught:
            runtime.prepare_context("PROD", self.start(), service_id="svc", instruction="draft")
        self.assertEqual(caught.exception.code, "semantic_invalid")

    def test_mutation_after_freeze_blocks_before_stage_worker(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        ProductionContextRuntime(self.store, fake).prepare_context("PROD", run_id, service_id="svc", instruction="draft")
        fake.calls.clear()
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE characters SET agenda=?,updated_at=? WHERE character_id='CHAR-A'", ("changed", now_iso()))
            conn.commit()
        result = self.execute_to_handoff(runtime, run_id)
        self.assertEqual(result["status"], "stale_conflict")
        self.assertTrue(result["new_context_fingerprint_required"])
        self.assertEqual(fake.calls, [])

    def test_new_source_after_freeze_changes_source_universe_and_blocks(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        ProductionContextRuntime(self.store, fake).prepare_context("PROD", run_id, service_id="svc", instruction="draft")
        fake.calls.clear()
        with self.store.open_project("PROD") as conn:
            conn.execute(
                "INSERT INTO characters(character_id,name,agenda,voice_notes,state_json,updated_at) VALUES(?,?,?,?,?,?)",
                ("CHAR-B", "B", "new agenda", None, "{}", now_iso()),
            )
            conn.commit()
        result = self.execute_to_handoff(runtime, run_id)
        self.assertEqual(result["status"], "stale_conflict")
        self.assertTrue(result["validation"].get("source_universe_changed"))
        self.assertEqual(fake.calls, [])

    def test_explicit_refresh_requires_fresh_budgeted_run(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        self.execute_to_handoff(runtime, run_id)
        calls = len(fake.calls)
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE characters SET agenda=?,updated_at=? WHERE character_id='CHAR-A'", ("changed", now_iso()))
            conn.commit()
        with self.assertRaises(ProductionRunError) as caught:
            runtime.refresh_context("PROD", run_id, service_id="svc", instruction="draft", reason="user_requested_refresh")
        self.assertEqual(caught.exception.code, "fresh_run_required")
        self.assertEqual(len(fake.calls), calls)

    def test_unleased_context_and_direct_model_calls_cannot_bypass_budget(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        with self.assertRaises(ProductionRunError) as context_error:
            runtime.prepare_context("PROD", run_id, service_id="svc", instruction="draft")
        self.assertEqual("execution_lease_required", context_error.exception.code)
        job = AgentJob(job_id="UNLEASED", session_id="fixture", run_id=run_id, task_mode="DRAFT",
                       runtime_role="surface_realization", service_id="svc", instruction="fixture")
        with self.assertRaises(ProductionRunError) as direct_error:
            runtime._invoke_agent(job)
        self.assertEqual("execution_lease_required", direct_error.exception.code)
        self.assertEqual([], fake.calls)
        with self.store.open_project("PROD") as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM checkpoints WHERE checkpoint_kind='production_context_bundle'").fetchone()[0])

    def test_mutation_after_handoff_blocks_independent_submission(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start()
        handoff = self.execute_to_handoff(runtime, run_id)
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE characters SET agenda=?,updated_at=? WHERE character_id='CHAR-A'", ("post-handoff mutation", now_iso()))
            conn.commit()
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        blocked = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=project_bridge_receipt(packet, result),
        )
        self.assertEqual(blocked["status"], "stale_conflict")
        self.assertTrue(blocked["new_context_fingerprint_required"])

    def test_independent_reject_is_not_reviewer_shopped_and_creates_no_candidate(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start()
        handoff = self.execute_to_handoff(runtime, run_id)
        rejected = self.submit(runtime, run_id, "fail")
        self.assertEqual(rejected["status"], "failed_gate")
        self.assertEqual(rejected["failed_mechanism"], "independent_semantic_gate")
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 0)
        with self.assertRaises(ProductionRunError) as caught:
            self.execute_to_handoff(runtime, run_id)
        self.assertEqual(caught.exception.code, "failed_gate_requires_fresh_run")

    def test_completed_run_replay_is_idempotent(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        handoff = self.execute_to_handoff(runtime, run_id)
        first = self.submit(runtime, run_id)
        calls = len(fake.calls)
        second = self.execute_to_handoff(runtime, run_id)
        assert_public_execution_safe(self, first)
        assert_public_execution_safe(self, second)
        self.assertTrue(second["replayed"])
        self.assertEqual(first["candidate"]["candidate_id"], second["candidate"]["candidate_id"])
        self.assertEqual(calls, len(fake.calls))
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 1)

    def test_missing_core_target_checkpoint_never_invokes_model(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        with self.store.open_project("PROD") as conn:
            conn.execute("DELETE FROM checkpoints WHERE run_id=? AND checkpoint_kind='author_run_request'", (run_id,))
            conn.commit()
        with self.assertRaises(ProductionRunError) as caught:
            self.execute_to_handoff(runtime, run_id)
        self.assertEqual(caught.exception.code, "target_context_missing")
        self.assertEqual(fake.calls, [])

    def repair_fixture(self, *, reader_positioning=None, **kwargs):
        fake = RepairFixtureRuntime(**kwargs)
        runtime = ProductionRunExecutor(self.store, fake)
        source_id = self.start(reader_positioning=reader_positioning)
        failed = self.execute_to_handoff(runtime, source_id)
        self.assertEqual(failed["status"], "failed_gate")
        source = runtime.status("PROD", source_id)["repair_source"]
        run_id = CoreOperations(self.store).start_author_run("PROD", task_mode="REVISE", target_ref="DOC-1",
                    payload={"chapter_id": "CH001", "repair_source": source})["run_id"]
        NovelWorkflowService(self.store).start(project_id="PROD", run_id=run_id, chapter_id="CH001", author_profile="guided")
        return fake, runtime, source_id, run_id

    def test_reader_fail_collects_diagnostics_for_fresh_repair_without_releasing_the_source(self):
        fake, runtime, source_id, run_id = self.repair_fixture(
            draft_reader_result="fail", generation_mode="fresh_realization",
        )
        source = runtime._latest_checkpoint("PROD", source_id, "production_qualified_candidate")
        qualification = source["qualification_receipt"]
        self.assertEqual("repair_required", qualification["qualification_status"])
        self.assertEqual(["reader_engagement"], qualification["failed_gates"])
        self.assertEqual("fail", source["reader_binding"]["result"]["judgment"]["result"])
        self.assertEqual("pass", source["self_audit_binding"]["result"]["judgment"]["result"])
        self.assertEqual(["registered_reader_engagement", "continuity", "registered_candidate_self_audit"],
                         [job.runtime_role for job in fake.calls if job.run_id == source_id][-3:])
        with self.assertRaises(ProductionRunError) as rejected:
            runtime._build_handoff_from_qualified(
                "PROD", runtime._run_row("PROD", source_id), runtime._latest_bundle("PROD", source_id), source, PROVENANCE,
            )
        self.assertEqual("not_qualified_for_independent", rejected.exception.code)

        repaired = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True,
                                   independent_provenance=PROVENANCE)
        self.assertEqual("awaiting_external", repaired["status"])
        calls = [job for job in fake.calls if job.run_id == run_id]
        editor = next(job for job in calls if job.runtime_role == "registered_repair_editor")
        self.assertEqual(source["reader_binding"]["result"]["judgment"],
                         editor.context[0]["registered_semantic_job"]["input"]["payload"]["reader_assessment"])
        isolated = [job.to_dict() for job in calls if job.runtime_role in {
            "event_first_raw_draft", "surface_realization", "registered_reader_engagement",
        }]
        isolated.append(frozen_packet(self.store, run_id))
        for value in isolated:
            for private in (PRE_RELEASE_MANUSCRIPT, "PRIVATE READER DIAGNOSIS", "PRIVATE EDITOR TRAJECTORY"):
                self.assertNotIn(private, json.dumps(value))
        self.assertEqual("completed", self.submit(runtime, run_id)["status"])
        self.assertEqual(source, runtime._latest_checkpoint("PROD", source_id, "production_qualified_candidate"))
        with self.store.open_project("PROD") as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (source_id,)).fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM receipts WHERE run_id=? AND receipt_kind='production_release'", (source_id,)).fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_independent_handoff'", (source_id,)).fetchone()[0])
            reader_receipt = next(json.loads(row[0]) for row in conn.execute(
                "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage'", (source_id,),
            ) if json.loads(row[0])["mechanism"] == "reader_engagement")
            self.assertEqual("fail", reader_receipt["judgment"]["status"])

    def test_reader_fail_repair_requires_original_confirmed_reader_evidence(self):
        fake, runtime, source_id, run_id = self.repair_fixture(draft_reader_result="fail")
        source_ref = runtime.status("PROD", source_id)["repair_source"]
        before = len(fake.calls)
        with self.store.open_project("PROD") as conn:
            conn.execute("DELETE FROM production_stage_calls WHERE run_id=? AND runtime_role='registered_reader_engagement'", (source_id,))
            conn.commit()
        with self.assertRaises(OperationError):
            CoreOperations(self.store).start_author_run(
                "PROD", task_mode="REVISE", target_ref="DOC-1", payload={"chapter_id": "CH001", "repair_source": source_ref},
            )
        with self.assertRaises(ProductionRunError):
            runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True)
        self.assertEqual(before, len(fake.calls))
        self.assertNotIn("repair_source", runtime.status("PROD", source_id))

    def test_nonfinal_reader_result_does_not_enter_repair_diagnostics(self):
        for verdict in ("insufficient_evidence", "needs_author"):
            with self.subTest(verdict=verdict):
                fake = RepairFixtureRuntime(draft_reader_result=verdict)
                runtime = ProductionRunExecutor(self.store, fake)
                run_id = self.start()
                # Reader's current contract admits only an explicit pass/fail.
                with self.assertRaises(ProductionRunError) as invalid:
                    self.execute_to_handoff(runtime, run_id)
                self.assertEqual("semantic_output_invalid", invalid.exception.code)
                self.assertEqual("registered_reader_engagement", fake.calls[-1].runtime_role)
                self.assertIsNone(runtime._latest_checkpoint("PROD", run_id, "production_qualified_candidate"))
                self.assertNotIn("repair_source", runtime.status("PROD", run_id))

    def test_reader_fail_does_not_bypass_a_continuity_failure(self):
        fake = RepairFixtureRuntime(draft_reader_result="fail")
        fake.reject_mechanism = "continuity"
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        failed = self.execute_to_handoff(runtime, run_id)
        self.assertEqual("continuity", failed["failed_mechanism"])
        self.assertEqual("continuity", fake.calls[-1].runtime_role)
        self.assertIsNone(runtime._latest_checkpoint("PROD", run_id, "production_qualified_candidate"))
        self.assertNotIn("repair_source", runtime.status("PROD", run_id))

    def test_reader_fail_diagnostic_resume_reuses_confirmed_reader_and_continuity(self):
        fake = RepairFixtureRuntime(draft_reader_result="fail")
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        original = runtime._persist_stage_receipt

        def interrupt(project_id, current_run, receipt, **kwargs):
            if receipt["mechanism"] == "continuity":
                raise OSError("synthetic interruption while saving Reader-fail diagnostics")
            return original(project_id, current_run, receipt, **kwargs)

        with patch.object(runtime, "_persist_stage_receipt", side_effect=interrupt), self.assertRaises(OSError):
            self.execute_to_handoff(runtime, run_id)
        resumed = runtime.resume_execution("PROD", run_id)
        self.assertEqual(["reader_engagement"], resumed["qualification"]["failed_gates"])
        for role in ("registered_reader_engagement", "continuity", "registered_candidate_self_audit"):
            self.assertEqual(1, sum(job.runtime_role == role for job in fake.calls))
        self.assertIn("repair_source", runtime.status("PROD", run_id))

    def test_internal_repair_inherits_positioning_and_cannot_replace_it(self):
        fake, runtime, source_id, run_id = self.repair_fixture(reader_positioning=READER_POSITIONING)
        target = runtime._run_row("PROD", run_id)["target_context"]
        self.assertEqual(READER_POSITIONING, target["payload"]["reader_positioning"])
        before = len(fake.calls)
        source_ref = runtime.status("PROD", source_id)["repair_source"]
        with self.assertRaises(OperationError) as caught:
            CoreOperations(self.store).start_author_run(
                "PROD", task_mode="REVISE", target_ref="DOC-1",
                payload={"chapter_id": "CH001", "repair_source": source_ref,
                         "reader_positioning": {**READER_POSITIONING, "genre_profile": "a replaced objective"}},
            )
        self.assertEqual("repair_objective_changed", caught.exception.code)
        self.assertEqual(before, len(fake.calls))
        result = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True,
                                 independent_provenance=PROVENANCE)
        self.assertEqual("awaiting_external", result["status"])
        qualified = runtime._latest_checkpoint("PROD", run_id, "production_qualified_candidate")
        expected = qualified["reading_positioning"]["reader_fields"]
        self.assertEqual(READER_POSITIONING["genre_profile"], expected["genre_profile"])
        calls = [job for job in fake.calls if job.run_id == run_id]
        for role in ("event_first_raw_draft", "surface_realization"):
            writer = next(job for job in calls if job.runtime_role == role)
            self.assertEqual(expected, writer.context[0]["reading_positioning"])
        reader = next(job for job in calls if job.runtime_role == "registered_reader_engagement")
        for payload in (reader.context[0]["registered_semantic_job"]["input"]["payload"],
                        frozen_packet(self.store, run_id)["job"]["input"]["payload"]):
            self.assertEqual(expected, {key: payload[key] for key in READER_FIELDS if key in payload})
            serialized = json.dumps(payload)
            for private in (PRE_RELEASE_MANUSCRIPT, "PRIVATE SYNTHETIC DIAGNOSIS", "PRIVATE EDITOR TRAJECTORY"):
                self.assertNotIn(private, serialized)
        editor = next(job for job in calls if job.runtime_role == "registered_repair_editor")
        objective = editor.context[0]["registered_semantic_job"]["input"]["payload"]["objective_envelope"]
        self.assertIn("OBJ-CURRENT-READING-POSITIONING", json.dumps(objective))

    def test_repair_executes_editor_and_exact_prose_compare_before_fresh_independent_review(self):
        fake, runtime, source_id, run_id = self.repair_fixture()
        with self.store.open_project("PROD") as conn:
            before = [tuple(row) for row in conn.execute("SELECT * FROM production_stage_calls WHERE run_id=? ORDER BY rowid", (source_id,))]
        result = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True, independent_provenance=PROVENANCE)
        self.assertEqual(result["status"], "awaiting_external")
        self.assertFalse(result["candidate_visible"])
        calls = [job for job in fake.calls if job.run_id == run_id]
        roles = [job.runtime_role for job in calls]
        self.assertLess(roles.index("registered_repair_editor"), roles.index("event_first_raw_draft"))
        self.assertLess(roles.index("surface_realization"), roles.index("registered_repair_comparison"))
        comparison = next(job for job in calls if job.runtime_role == "registered_repair_comparison").context[0]["registered_semantic_job"]["input"]["payload"]
        self.assertEqual(comparison["incumbent"]["text"], PRE_RELEASE_MANUSCRIPT)
        self.assertEqual(comparison["challenger"]["text"], REPAIRED_FIXTURE_TEXT)
        for side in ("incumbent", "challenger"):
            self.assertEqual(comparison[side]["content_fingerprint"], fingerprint_text(comparison[side]["text"]))
        qualified = runtime._latest_checkpoint("PROD", run_id, "production_qualified_candidate")
        self.assertEqual(qualified["qualification_receipt"]["repair_preservation_status"], "pass")
        self.assertEqual(qualified["repair_lineage"]["nodes"][-1]["origin"], "repair")
        self.assertEqual(qualified["repair_lineage"]["nodes"][-1]["prose_parent_candidate_id"], "diagnostic:" + source_id)
        blind = next(job for job in calls if job.runtime_role == "registered_reader_engagement")
        for value in (blind.context, frozen_packet(self.store, run_id)):
            serialized = json.dumps(value)
            self.assertNotIn(PRE_RELEASE_MANUSCRIPT, serialized)
            self.assertNotIn("PRIVATE SYNTHETIC DIAGNOSIS", serialized)
            self.assertNotIn("PRIVATE EDITOR TRAJECTORY", serialized)
        replay = runtime.resume_execution("PROD", run_id)
        self.assertEqual(replay["status"], "awaiting_external")
        self.assertEqual(len(calls), len([job for job in fake.calls if job.run_id == run_id]))
        with self.store.open_project("PROD") as conn:
            self.assertEqual(before, [tuple(row) for row in conn.execute("SELECT * FROM production_stage_calls WHERE run_id=? ORDER BY rowid", (source_id,))])
            self.assertEqual(conn.execute("SELECT status FROM runs WHERE run_id=?", (source_id,)).fetchone()[0], "failed_gate")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0], 0)

    def test_fresh_repair_omits_incumbent_and_critique_from_writer_but_keeps_comparison_parent(self):
        fake, runtime, source_id, run_id = self.repair_fixture(generation_mode="fresh_realization")
        result = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True)
        self.assertEqual(result["status"], "awaiting_external")
        writers = [job for job in fake.calls if job.run_id == run_id and job.runtime_role in {"event_first_raw_draft", "surface_realization"}]
        for writer in writers:
            serialized = json.dumps(writer.to_dict())
            for excluded in (PRE_RELEASE_MANUSCRIPT, "PRIVATE SYNTHETIC DIAGNOSIS", "PRIVATE EDITOR TRAJECTORY", "bounded_repair_evidence"):
                self.assertNotIn(excluded, serialized)
            self.assertIn("objective_envelope", serialized)
            self.assertIn("reconstructed_current_story_state", serialized)
        lineage = runtime._latest_checkpoint("PROD", run_id, "production_qualified_candidate")["repair_lineage"]
        self.assertEqual(lineage["nodes"][-1]["origin"], "fresh_regeneration")
        self.assertIsNone(lineage["nodes"][-1]["prose_parent_candidate_id"])
        self.assertEqual(lineage["nodes"][-1]["comparison_parent_candidate_id"], "diagnostic:" + source_id)

    def test_repair_objective_regression_cannot_replace_the_comparison_incumbent(self):
        fake, runtime, source_id, run_id = self.repair_fixture(comparison_outcome="objective_regression")
        failed = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True)
        self.assertEqual(failed["status"], "failed_gate")
        self.assertIn("repair_preservation", failed["qualification"]["failed_gates"])
        with self.assertRaises(ProductionRunError) as caught:
            runtime.resume_execution("PROD", run_id)
        self.assertEqual(caught.exception.code, "failed_gate_requires_fresh_run")
        self.assertFalse(any(job.run_id == run_id and job.runtime_role == "registered_narrative_state" for job in fake.calls))
        self.assertNotIn("repair_source", runtime.status("PROD", run_id))
        with self.store.open_project("PROD") as conn:
            row = conn.execute("SELECT checkpoint_id,artifact_fingerprint FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_qualified_candidate'", (run_id,)).fetchone()
        rejected_ref = {"source_run_id": run_id, "source_checkpoint_id": row["checkpoint_id"],
                        "expected_candidate_fingerprint": row["artifact_fingerprint"]}
        before = len(fake.calls)
        with self.assertRaises(OperationError) as caught:
            CoreOperations(self.store).start_author_run("PROD", task_mode="REVISE", target_ref="DOC-1",
                        payload={"chapter_id": "CH001", "repair_source": rejected_ref})
        self.assertEqual(caught.exception.code, "repair_incumbent_retained")
        self.assertEqual(len(fake.calls), before)
        self.assertEqual(runtime.status("PROD", source_id)["status"], "failed_gate")

    def test_passing_comparison_can_continue_repair_only_with_intact_parent_evidence(self):
        fake, runtime, source_id, run_id = self.repair_fixture(repair_audit_fails=True)
        failed = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True)
        self.assertEqual(failed["status"], "failed_gate")
        self.assertEqual(failed["qualification"]["failed_gates"], ["self_audit"])
        second_source = runtime.status("PROD", run_id)["repair_source"]
        next_run = CoreOperations(self.store).start_author_run("PROD", task_mode="REVISE", target_ref="DOC-1",
                    payload={"chapter_id": "CH001", "repair_source": second_source})["run_id"]
        NovelWorkflowService(self.store).start(project_id="PROD", run_id=next_run, chapter_id="CH001", author_profile="guided")
        before = len(fake.calls)
        with self.store.open_project("PROD") as conn:
            parent = dict(conn.execute("SELECT * FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_repair_source'", (run_id,)).fetchone())
            conn.execute("DELETE FROM checkpoints WHERE checkpoint_id=?", (parent["checkpoint_id"],))
            conn.commit()
        with self.assertRaises(ProductionRunError) as caught:
            runtime.execute("PROD", next_run, service_id="svc", inherit_repair_request=True)
        self.assertEqual(caught.exception.code, "repair_source_missing")
        self.assertEqual(len(fake.calls), before)
        self.assertNotIn("repair_source", runtime.status("PROD", run_id))
        with self.store.open_project("PROD") as conn:
            columns = ",".join(parent)
            placeholders = ",".join("?" for _ in parent)
            conn.execute(f"INSERT INTO checkpoints({columns}) VALUES({placeholders})", list(parent.values()))
            conn.commit()
        fake.repair_audit_fails = False
        result = runtime.execute("PROD", next_run, service_id="svc", inherit_repair_request=True)
        self.assertEqual(result["status"], "awaiting_external")
        qualified = runtime._latest_checkpoint("PROD", next_run, "production_qualified_candidate")
        self.assertEqual(qualified["repair_lineage"]["evolution_run_id"], source_id)
        self.assertEqual([node["created_by_run_id"] for node in qualified["repair_lineage"]["nodes"]], [source_id, run_id, next_run])
        self.assertEqual(qualified["qualification_receipt"]["repair_cycle"], 2)

    def test_repair_rejects_caller_pass_or_objective_replacement_before_model_dispatch(self):
        fake, runtime, _, run_id = self.repair_fixture()
        before = len(fake.calls)
        for inputs, code in (
            ({"inherit_repair_request": True, "repair_preservation": {"status": "pass"}}, "repair_preservation_core_owned"),
            ({"inherit_repair_request": True, "instruction": "Replace objectives"}, "repair_request_conflict"),
            ({"instruction": "Replace objectives", "reader_grip": "very_high", "rule_material": RULE_MATERIAL}, "repair_objective_changed"),
            ({"instruction": "draft chapter", "reader_grip": "very_high", "rule_material": RULE_MATERIAL,
              "reader_visible_context": [{"id": "unbound-extra-context"}]}, "repair_objective_changed"),
        ):
            with self.subTest(code=code), self.assertRaises(ProductionRunError) as caught:
                runtime.execute("PROD", run_id, service_id="svc", **inputs)
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(len(fake.calls), before)
        unbound = CoreOperations(self.store).start_author_run("PROD", task_mode="REVISE", target_ref="DOC-1", payload={"chapter_id": "CH001"})["run_id"]
        NovelWorkflowService(self.store).start(project_id="PROD", run_id=unbound, chapter_id="CH001", author_profile="guided")
        with self.assertRaises(ProductionRunError) as caught:
            runtime.execute("PROD", unbound, service_id="svc", inherit_repair_request=True)
        self.assertEqual(caught.exception.code, "repair_source_required")
        self.assertEqual(len(fake.calls), before)

    def test_repair_confirmed_editor_is_not_rerun_after_checkpoint_interruption(self):
        fake, runtime, _, run_id = self.repair_fixture()
        checkpoint = runtime._checkpoint

        def interrupt(project_id, current_run, kind, state, artifact_fingerprint):
            if kind == "production_repair_plan":
                raise OSError("synthetic repair checkpoint interruption")
            return checkpoint(project_id, current_run, kind, state, artifact_fingerprint)

        with patch.object(runtime, "_checkpoint", side_effect=interrupt), self.assertRaises(OSError):
            runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True)
        result = runtime.resume_execution("PROD", run_id)
        self.assertEqual(result["status"], "awaiting_external")
        calls = [job for job in fake.calls if job.run_id == run_id]
        self.assertEqual(sum(job.runtime_role == "registered_repair_editor" for job in calls), 1)
        self.assertEqual(len(calls), len({job.input_fingerprint for job in calls}))

    def test_repair_budget_charges_editor_and_stops_before_unfunded_generation(self):
        fake, runtime, _, run_id = self.repair_fixture()
        result = runtime.execute("PROD", run_id, service_id="svc", inherit_repair_request=True, max_model_calls=9)
        self.assertEqual(result["status"], "budget_exhausted")
        calls = [job for job in fake.calls if job.run_id == run_id]
        self.assertEqual(len(calls), 9)
        self.assertEqual(sum(job.runtime_role == "registered_repair_editor" for job in calls), 1)
        self.assertFalse(any(job.runtime_role == "surface_realization" for job in calls))

    def test_confirmed_stage_response_is_reused_after_checkpoint_failure(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        original = runtime._persist_stage_receipt

        def fail_once(project_id, current_run, receipt, **kwargs):
            if receipt["mechanism"] == "event_first_raw_draft":
                raise OSError("synthetic process failure after confirmed model response")
            return original(project_id, current_run, receipt, **kwargs)

        with patch.object(runtime, "_persist_stage_receipt", side_effect=fail_once):
            with self.assertRaises(OSError):
                self.execute_to_handoff(runtime, run_id)
        resumed = ProductionRunExecutor(self.store, fake).resume_execution("PROD", run_id)
        self.assertEqual(resumed["status"], "awaiting_external")
        inputs = [job.input_fingerprint for job in fake.calls]
        self.assertEqual(len(inputs), len(set(inputs)))
        self.assertEqual(sum(job.runtime_role == "event_first_raw_draft" for job in fake.calls), 1)
        journal = runtime.status("PROD", run_id)["execution_journal"]
        self.assertEqual(journal["confirmed_call_count"], len(fake.calls))
        self.assertEqual(journal["unconfirmed_call_ids"], [])
        assert_public_execution_safe(self, journal)

    def test_unknown_model_outcome_is_not_automatically_retried(self):
        class LostResponse(FakeAgentRuntime):
            def run(self, job, *, cancellation=None):
                if job.runtime_role == "event_first_raw_draft":
                    self.calls.append(job)
                    raise OSError("synthetic disconnected model response")
                return super().run(job, cancellation=cancellation)

        fake = LostResponse()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        result = self.execute_to_handoff(runtime, run_id)
        self.assertEqual(result["status"], "semantic_pending")
        self.assertFalse(result["automatic_model_retry"])
        calls = len(fake.calls)
        resumed = ProductionRunExecutor(self.store, fake).resume_execution("PROD", run_id)
        self.assertEqual(resumed["awaiting"], "stage_result_confirmation")
        self.assertEqual(len(fake.calls), calls)
        self.assertEqual(len(resumed["execution_journal"]["unconfirmed_call_ids"]), 1)
        assert_public_execution_safe(self, resumed)

    def test_cancelled_run_rejects_a_late_model_response(self):
        run_id = self.start()

        class CancelDuringCall(FakeAgentRuntime):
            def run(inner, job, *, cancellation=None):
                result = super().run(job, cancellation=cancellation)
                if job.runtime_role == "event_first_raw_draft":
                    runtime.cancel_execution("PROD", run_id, user_authorized=True)
                return result

        fake = CancelDuringCall()
        runtime = ProductionRunExecutor(self.store, fake)
        result = self.execute_to_handoff(runtime, run_id)
        self.assertEqual(result["status"], "cancelled")
        journal = runtime.status("PROD", run_id)["execution_journal"]
        raw = [row for row in journal["calls"] if row["runtime_role"] == "event_first_raw_draft"]
        self.assertEqual([row["state"] for row in raw], ["cancelled"])
        self.assertTrue(all(row["result_fingerprint"] is None for row in raw))
        self.assertFalse(any(job.runtime_role == "surface_realization" for job in fake.calls))
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 0)

    def test_total_model_budget_includes_profile_derivation(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        result = runtime.execute("PROD", run_id, service_id="svc", instruction="draft chapter", reader_grip="very_high",
                                 rule_material=RULE_MATERIAL, max_model_calls=2)
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertEqual([job.runtime_role for job in fake.calls], ["context_profile_deriver", "context_profile_deriver"])
        self.assertEqual(result["execution_journal"]["dispatched_call_count"], 2)
        replay = runtime.resume_execution("PROD", run_id)
        self.assertEqual(replay["status"], "budget_exhausted")
        self.assertEqual(len(fake.calls), 2)

    def test_resume_rejects_changed_model_or_generation_request(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start()
        self.execute_to_handoff(runtime, run_id)
        with self.assertRaises(ProductionRunError) as caught:
            runtime.execute("PROD", run_id, service_id="different", instruction="draft chapter", reader_grip="very_high", rule_material=RULE_MATERIAL)
        self.assertEqual(caught.exception.code, "execution_request_conflict")

    def test_writer_uses_causal_outputs_without_private_character_state(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        self.execute_to_handoff(runtime, run_id)
        action = next(job for job in fake.calls if job.runtime_role == "registered_character_action")
        scene = next(job for job in fake.calls if job.runtime_role == "registered_scene_resolution")
        projection = next(job for job in fake.calls if job.runtime_role == "registered_scene_projection")
        action_job = action.context[0]["registered_semantic_job"]
        scene_evidence = scene.context[0]["registered_semantic_job"]["input"]["payload"]["character_action_evidence"]
        self.assertEqual(action_job["input"]["payload"], scene_evidence[0]["bounded_input"])
        self.assertEqual(action_job["input_fingerprint"], scene_evidence[0]["input_fingerprint"])
        self.assertFalse(scene_evidence[0]["input_is_proposed_cast"])
        self.assertFalse(scene_evidence[0]["authority"])
        self.assertEqual(scene_evidence, projection.context[0]["registered_semantic_job"]["input"]["payload"]["character_action_evidence"])
        with self.store.open_project("PROD") as conn:
            receipts = [json.loads(row[0]) for row in conn.execute(
                "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage'", (run_id,))]
        character_receipt = next(row for row in receipts if row["mechanism"] == "character_simulation")
        self.assertEqual(character_receipt["registered_contracts"][0]["result_fingerprint"], scene_evidence[0]["result_fingerprint"])
        draft = next(job for job in fake.calls if job.runtime_role == "event_first_raw_draft")
        action_text = json.dumps(action.context)
        draft_text = json.dumps(draft.context)
        self.assertIn("private knowledge", action_text)
        self.assertIn("private knowledge", json.dumps(scene_evidence))
        for role in ("registered_reader_pressure", "event_first_raw_draft", "surface_realization", "registered_reader_engagement"):
            context_text = json.dumps(next(job for job in fake.calls if job.runtime_role == role).context)
            self.assertNotIn("bounded_input", context_text)
            self.assertNotIn("private knowledge", context_text)
            self.assertNotIn("protect the deal", context_text)
        self.assertIn("writer_projection", draft_text)
        self.assertIn("expected_reward", draft_text)
        reader = next(job for job in fake.calls if job.runtime_role == "registered_reader_engagement")
        self.assertNotIn("frozen_stage_context", json.dumps(reader.context))
        self.assertNotIn("protect the deal", json.dumps(reader.context))

    def test_new_cast_nonempty_evidence_flows_through_registered_action_and_budget(self):
        with self.store.open_project("PROD") as conn:
            conn.execute("DELETE FROM character_knowledge")
            conn.execute("DELETE FROM characters")
            conn.commit()
        fake = PreparedCastFixtureRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        self.assertEqual("awaiting_external", self.execute_to_handoff(runtime, run_id)["status"])
        preparation = next(job for job in fake.calls if job.runtime_role == "character_state_prepare")
        self.assertIn("output_contract", preparation.context[0])
        action = next(job for job in fake.calls if job.runtime_role == "registered_character_action")
        self.assertEqual(["OBS-NOW", "FACT-OWN"], action.context[0]["eligible_evidence_ids"])
        self.assertNotIn("UNAVAILABLE FUTURE OBSERVATION", json.dumps(action.context))
        scene = next(job for job in fake.calls if job.runtime_role == "registered_scene_resolution")
        evidence = scene.context[0]["registered_semantic_job"]["input"]["payload"]["character_action_evidence"][0]
        self.assertEqual(action.context[0]["registered_semantic_job"]["input"]["payload"], evidence["bounded_input"])
        self.assertTrue(evidence["input_is_proposed_cast"])
        self.assertFalse(evidence["authority"])
        self.assertIn("fixture:firsthand-witness", json.dumps(evidence))
        self.assertNotIn("UNAVAILABLE FUTURE OBSERVATION", json.dumps(scene.context))
        for role in ("event_first_raw_draft", "surface_realization", "registered_reader_engagement"):
            context_text = json.dumps(next(job for job in fake.calls if job.runtime_role == role).context)
            self.assertNotIn("PRIVATE INITIAL MEMORY", context_text)
            self.assertNotIn("fixture:firsthand-witness", context_text)
        journal = runtime.status("PROD", run_id)["execution_journal"]
        self.assertEqual(len(fake.calls), journal["confirmed_call_count"])
        self.assertEqual([], journal["unconfirmed_call_ids"])
        with self.store.open_project("PROD") as conn:
            stored = json.loads(conn.execute("SELECT result_json FROM production_stage_calls WHERE run_id=? AND runtime_role='character_state_prepare'", (run_id,)).fetchone()[0])
            self.assertEqual(fake.preparation, json.loads(stored["final_text"]))
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM character_knowledge").fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM canon_claims").fetchone()[0])

    def test_scene_blocking_repair_does_not_force_plan_success_or_start_writer(self):
        refusal = "A refuses to surrender the record without the missing owner's permission."
        blocker = "The planned transfer cannot occur within the supplied permission boundary; revise the plan instead of overriding the refusal."

        class RefusedTransfer(FakeAgentRuntime):
            def run(inner, job, *, cancellation=None):
                result = super().run(job, cancellation=cancellation)
                judgment = json.loads(result.final_text)
                if job.runtime_role == "registered_character_action":
                    judgment["proposals"][0]["action"] = refusal
                elif job.runtime_role == "registered_scene_resolution":
                    judgment["repair_routes"] = [{"owner": "plan", "reason": blocker}]
                result.final_text = json.dumps(judgment)
                return result

        CoreOperations(self.store).plan_save(
            "PROD", target_ref="chapter:CH001", title="Requested transfer",
            content="The record changes hands, with the owner's permission required.",
            expected_version=0, idempotency_key="scene-refusal-plan", user_authorized=True,
        )
        fake = RefusedTransfer()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        result = self.execute_to_handoff(runtime, run_id)
        self.assertEqual("failed_gate", result["status"])
        self.assertEqual("scene_simulation", result["failed_mechanism"])
        self.assertFalse(result["candidate_visible"])
        roles = [job.runtime_role for job in fake.calls]
        self.assertEqual("registered_scene_resolution", roles[-1])
        self.assertNotIn("registered_scene_projection", roles)
        self.assertNotIn("event_first_raw_draft", roles)
        scene = fake.calls[-1].context[0]["registered_semantic_job"]["input"]["payload"]
        self.assertEqual(refusal, scene["character_action_evidence"][0]["judgment"]["proposals"][0]["action"])
        self.assertIn("The record changes hands", json.dumps(scene["frozen_scene_context"]))
        calls = len(fake.calls)
        with self.assertRaises(ProductionRunError) as replay:
            runtime.resume_execution("PROD", run_id)
        self.assertEqual("failed_gate_requires_fresh_run", replay.exception.code)
        self.assertEqual(calls, len(fake.calls))
        with self.store.open_project("PROD") as conn:
            stored = json.loads(conn.execute(
                "SELECT result_json FROM production_stage_calls WHERE run_id=? AND runtime_role='registered_scene_resolution'", (run_id,)).fetchone()[0])
            self.assertEqual([{"owner": "plan", "reason": blocker}], json.loads(stored["final_text"])["repair_routes"])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0])
        assert_public_execution_safe(self, result)

    def test_noncanonical_new_cast_stops_before_action_and_resume_does_not_rewrite_or_retry(self):
        with self.store.open_project("PROD") as conn:
            conn.execute("DELETE FROM character_knowledge")
            conn.execute("DELETE FROM characters")
            conn.commit()
        fake = PreparedCastFixtureRuntime(malformed=True)
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        with self.assertRaises(ProductionRunError) as error:
            self.execute_to_handoff(runtime, run_id)
        self.assertEqual("semantic_output_invalid", error.exception.code)
        self.assertFalse(any(job.runtime_role == "registered_character_action" for job in fake.calls))
        calls = len(fake.calls)
        self.assertEqual("semantic_pending", runtime.status("PROD", run_id)["status"])
        with self.assertRaises(ProductionRunError) as replay_error:
            runtime.resume_execution("PROD", run_id)
        self.assertEqual("semantic_output_invalid", replay_error.exception.code)
        self.assertEqual(calls, len(fake.calls))
        journal = runtime.status("PROD", run_id)["execution_journal"]
        self.assertEqual(calls, journal["confirmed_call_count"])
        self.assertEqual([], journal["unconfirmed_call_ids"])
        with self.store.open_project("PROD") as conn:
            stored = json.loads(conn.execute("SELECT result_json FROM production_stage_calls WHERE run_id=? AND runtime_role='character_state_prepare'", (run_id,)).fetchone()[0])
            self.assertEqual(fake.preparation, json.loads(stored["final_text"]))
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM runtime_events WHERE run_id=? AND event_kind='production_stage_failed'", (run_id,)).fetchone()[0])

    def test_noncanonical_stage_status_cannot_advance_or_release(self):
        for mechanism, malformed_status in (("story_canon_preflight", "FAIL"), ("event_first_raw_draft", " fail "),
                                             ("surface_realization", "PASS"), ("continuity", ["fail"])):
            with self.subTest(mechanism=mechanism, status=malformed_status):
                class InvalidStatus(FakeAgentRuntime):
                    def run(inner, job, *, cancellation=None):
                        result = super().run(job, cancellation=cancellation)
                        if job.runtime_role == mechanism:
                            judgment = json.loads(result.final_text)
                            judgment["status"] = malformed_status
                            result.final_text = json.dumps(judgment)
                        return result

                fake = InvalidStatus()
                runtime = ProductionRunExecutor(self.store, fake)
                run_id = self.start()
                with self.assertRaises(ProductionRunError) as error:
                    self.execute_to_handoff(runtime, run_id)
                self.assertEqual("semantic_output_invalid", error.exception.code)
                self.assertEqual(mechanism, fake.calls[-1].runtime_role)
                self.assertEqual("semantic_pending", runtime.status("PROD", run_id)["status"])
                with self.store.open_project("PROD") as conn:
                    stored = json.loads(conn.execute("SELECT result_json FROM production_stage_calls WHERE run_id=? AND runtime_role=?", (run_id, mechanism)).fetchone()[0])
                    self.assertEqual(malformed_status, json.loads(stored["final_text"])["status"])
                    self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0])
                    failures = [json.loads(row[0]) for row in conn.execute("SELECT payload_json FROM runtime_events WHERE run_id=? AND event_kind='production_stage_failed'", (run_id,))]
                    self.assertEqual(1, len(failures))
                    self.assertEqual(mechanism, failures[0]["mechanism"])
                    assert_public_execution_safe(self, failures)
        for mechanism in ("story_canon_preflight", "continuity"):
            with self.subTest(rejected_mechanism=mechanism):
                fake = FakeAgentRuntime(reject_mechanism=mechanism)
                runtime = ProductionRunExecutor(self.store, fake)
                run_id = self.start()
                self.assertEqual("failed_gate", self.execute_to_handoff(runtime, run_id)["status"])
                self.assertEqual(mechanism, fake.calls[-1].runtime_role)
                calls = len(fake.calls)
                with self.assertRaises(ProductionRunError) as rejected:
                    runtime.resume_execution("PROD", run_id)
                self.assertEqual("failed_gate_requires_fresh_run", rejected.exception.code)
                self.assertEqual("failed_gate", runtime.status("PROD", run_id)["status"])
                self.assertEqual(calls, len(fake.calls))
                with self.store.open_project("PROD") as conn:
                    stored = json.loads(conn.execute("SELECT result_json FROM production_stage_calls WHERE run_id=? AND runtime_role=?", (run_id, mechanism)).fetchone()[0])
                    self.assertEqual("fail", json.loads(stored["final_text"])["status"])
                    self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0])

    def test_narrative_source_metadata_cannot_be_copied_into_replacement_fields(self):
        from production_runtime.semantic import narrative_field_contracts

        class CopyReadOnlySource(FinalStateFixtureRuntime):
            def run(inner, job, *, cancellation=None):
                result = super().run(job, cancellation=cancellation)
                if job.runtime_role == "registered_narrative_state":
                    source = job.context[0]["registered_semantic_job"]["input"]["payload"]
                    actor = next(row for row in source["existing_state"] if row["entity_ref"] == "CHAR-A")
                    judgment = json.loads(result.final_text)
                    judgment["changes"][0]["fields"].update(actor["source_metadata"])
                    result.final_text = json.dumps(judgment)
                return result

        fake = CopyReadOnlySource()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        with self.assertRaises(ProductionRunError) as error:
            self.execute_to_handoff(runtime, run_id)
        self.assertEqual("semantic_output_invalid", error.exception.code)
        self.assertIn("oneOf", str(error.exception))
        self.assertEqual("semantic_pending", runtime.status("PROD", run_id)["status"])
        calls = len(fake.calls)
        with self.store.open_project("PROD") as conn:
            original_result = conn.execute("SELECT result_json FROM production_stage_calls WHERE run_id=? AND runtime_role='registered_narrative_state'", (run_id,)).fetchone()[0]
        with self.assertRaises(ProductionRunError) as resumed:
            runtime.resume_execution("PROD", run_id)
        self.assertEqual("semantic_output_invalid", resumed.exception.code)
        self.assertEqual(calls, len(fake.calls))
        dispatched = fake.calls[-1]
        self.assertEqual("registered_narrative_state", dispatched.runtime_role)
        registered = dispatched.context[0]["registered_semantic_job"]
        self.assertEqual(narrative_field_contracts(registered["output_contract"]), dispatched.context[0]["writable_field_contracts"])
        with self.store.open_project("PROD") as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM checkpoints WHERE run_id=? AND checkpoint_kind IN ('production_narrative_proposal','production_independent_handoff')", (run_id,)).fetchone()[0])
            self.assertEqual("semantic_pending", conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()[0])
            self.assertEqual(original_result, conn.execute("SELECT result_json FROM production_stage_calls WHERE run_id=? AND runtime_role='registered_narrative_state'", (run_id,)).fetchone()[0])
            failures = [json.loads(row[0]) for row in conn.execute("SELECT payload_json FROM runtime_events WHERE run_id=? AND event_kind='production_stage_failed'", (run_id,))]
            self.assertEqual(1, len(failures))
            self.assertEqual("registered_narrative_state", failures[0]["mechanism"])
            assert_public_execution_safe(self, failures)

    def test_final_reader_or_narrative_pending_records_safe_failure_without_retry(self):
        for role in ("registered_reader_expectations", "registered_narrative_state"):
            with self.subTest(role=role):
                class IncompleteFinalStage(FakeAgentRuntime):
                    def run(inner, job, *, cancellation=None):
                        result = super().run(job, cancellation=cancellation)
                        if job.runtime_role == role:
                            result.status = "model_failed"
                            result.errors = ["PRIVATE MODEL ERROR DETAIL"]
                        return result

                fake = IncompleteFinalStage()
                runtime = ProductionRunExecutor(self.store, fake)
                run_id = self.start()
                with self.assertRaises(ProductionRunError) as error:
                    self.execute_to_handoff(runtime, run_id)
                self.assertEqual("semantic_pending", error.exception.code)
                self.assertEqual("semantic_pending", runtime.status("PROD", run_id)["status"])
                calls = len(fake.calls)
                with self.assertRaises(ProductionRunError) as replay:
                    runtime.resume_execution("PROD", run_id)
                self.assertEqual("semantic_pending", replay.exception.code)
                self.assertEqual(calls, len(fake.calls))
                with self.store.open_project("PROD") as conn:
                    failures = [json.loads(row[0]) for row in conn.execute("SELECT payload_json FROM runtime_events WHERE run_id=? AND event_kind='production_stage_failed'", (run_id,))]
                    self.assertEqual(1, len(failures))
                    self.assertEqual(role, failures[0]["mechanism"])
                    self.assertNotIn("PRIVATE MODEL ERROR DETAIL", json.dumps(failures))
                    self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0])

    def test_reader_cannot_be_given_caller_injected_future_plan(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        with self.assertRaises(ProductionRunError) as caught:
            runtime.execute("PROD", self.start(), service_id="svc", instruction="draft chapter", reader_grip="very_high",
                            rule_material=RULE_MATERIAL, reader_visible_context=[{"future_plan": "the unrevealed ending"}])
        self.assertEqual(caught.exception.code, "reader_context_untrusted")
        self.assertFalse(any(job.runtime_role == "registered_reader_engagement" for job in fake.calls))

    def release_and_accept(self, fake=None, *, chapter_id="CH001", document_id="DOC-1"):
        fake = fake or FinalStateFixtureRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start(chapter_id=chapter_id, document_id=document_id)
        self.assertEqual("awaiting_external", self.execute_to_handoff(runtime, run_id)["status"])
        completed = self.submit(runtime, run_id)
        acceptance = CoreOperations(self.store).accept_candidate(
            "PROD", candidate_id=completed["candidate"]["candidate_id"],
            candidate_fingerprint=completed["candidate"]["candidate_fingerprint"],
            authorized_by="fixture-author", authorization={"intent": "accept"}, idempotency_key="accept:" + run_id,
        )
        return completed, acceptance

    def settle_accepted(self, acceptance, *, chapter_id="CH001", idempotency_key="settle-fixture"):
        ops = CoreOperations(self.store)
        preflight = ops.settlement_preflight("PROD", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:" + chapter_id)
        result = ops.settle("PROD", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:" + chapter_id,
                            expected_before_fingerprint=preflight["current_before_fingerprint"], user_authorized=True,
                            expected_preflight_fingerprint=preflight["preflight_fingerprint"], idempotency_key=idempotency_key)
        return preflight, result

    def add_chapter(self, chapter_id="CH002", document_id="DOC-2", ordinal=2):
        with self.store.open_project("PROD") as conn:
            conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) VALUES(?,'chapter',?,?,'{}')",
                         (chapter_id, ordinal, chapter_id))
            conn.commit()
        self.store.create_document("PROD", document_id, chapter_id, story_node_id=chapter_id)
        self.store.save_revision("PROD", document_id, "unaccepted private chapter " + chapter_id,
                                 expected_parent_revision_id=None, source="test")

    def seed_preference(self, hypothesis_id="PREF-SELECTED", *, state="active", statement="Selected fixture preference."):
        from learning.learning_store import LearningStore
        learning = LearningStore(CoreOperations(self.store).project_learning().learning_db)
        learning.init()
        return learning.upsert_hypothesis({"hypothesis_id": hypothesis_id, "subject_scope": "project", "project_id": "PROD",
                                           "dimension": "dialogue", "mechanism": "knowledge asymmetry", "statement": statement,
                                           "confidence": 1.0, "state": state})

    def test_nonempty_reader_and_narrative_state_require_author_settlement(self):
        from quality.reader_expectation import inspect_project
        fake = FinalStateFixtureRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        self.execute_to_handoff(runtime, run_id)
        with self.store.open_project("PROD") as conn:
            self.assertEqual([], inspect_project(conn)["observations"])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM expectations").fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM narrative_state_sources").fetchone()[0])
        completed = self.submit(runtime, run_id)
        ops = CoreOperations(self.store)
        with self.store.open_project("PROD") as conn:
            inspection = inspect_project(conn)
            self.assertEqual("proposed", inspection["observations"][0]["state"])
            self.assertNotIn("binding_json", json.dumps(inspection))
            self.assertEqual([], inspection["items"])
        acceptance = ops.accept_candidate("PROD", candidate_id=completed["candidate"]["candidate_id"],
                                           candidate_fingerprint=completed["candidate"]["candidate_fingerprint"],
                                           authorized_by="fixture-author", authorization={"intent": "accept"}, idempotency_key="accept-memory")
        preflight = ops.settlement_preflight("PROD", acceptance_id=acceptance["acceptance_id"], target_ref="chapter:CH001")
        self.assertEqual(6, len(preflight["narrative_proposal"]["changes"]))
        self.assertEqual(1, len(preflight["reader_observations"]))
        args = {"acceptance_id": acceptance["acceptance_id"], "target_ref": "chapter:CH001",
                "expected_before_fingerprint": preflight["current_before_fingerprint"], "idempotency_key": "settle-memory"}
        with self.assertRaises(OperationError) as denied:
            ops.settle("PROD", **args, user_authorized=False, expected_preflight_fingerprint=preflight["preflight_fingerprint"])
        self.assertEqual("authorization_required", denied.exception.code)
        with self.assertRaises(OperationError) as missing_review:
            ops.settle("PROD", **args, user_authorized=True)
        self.assertEqual("settlement_preflight_changed", missing_review.exception.code)
        result = ops.settle("PROD", **args, user_authorized=True, expected_preflight_fingerprint=preflight["preflight_fingerprint"])
        replay = ops.settle("PROD", **args, user_authorized=True, expected_preflight_fingerprint=preflight["preflight_fingerprint"])
        self.assertEqual(result, replay)
        with self.store.open_project("PROD") as conn:
            self.assertEqual("seek a reply", conn.execute("SELECT agenda FROM characters WHERE character_id='CHAR-A'").fetchone()[0])
            self.assertEqual(2, conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0])
            self.assertEqual(6, conn.execute("SELECT COUNT(*) FROM narrative_state_sources WHERE state='current'").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM expectations WHERE status='open' AND version=1").fetchone()[0])
            self.assertEqual("applied", inspect_project(conn)["observations"][0]["state"])
            self.assertEqual([], conn.execute("PRAGMA foreign_key_check").fetchall())

    def test_settlement_rolls_back_head_facts_and_reader_effects_together(self):
        _, acceptance = self.release_and_accept()
        with patch("quality.reader_expectation.apply_observation", side_effect=RuntimeError("fixture reader write failure")):
            with self.assertRaisesRegex(RuntimeError, "fixture reader write failure"):
                self.settle_accepted(acceptance)
        with self.store.open_project("PROD") as conn:
            for table in ("canon_state", "settlements", "narrative_state_sources", "expectations", "reader_expectation_effects"):
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], table)
            self.assertEqual("protect the deal", conn.execute("SELECT agenda FROM characters WHERE character_id='CHAR-A'").fetchone()[0])
            self.assertEqual("proposed", conn.execute("SELECT state FROM reader_expectation_observations").fetchone()[0])
        self.assertEqual("settled", self.settle_accepted(acceptance)[1]["status"])

    def test_settlement_rejects_changed_narrative_before_state(self):
        _, acceptance = self.release_and_accept()
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE characters SET agenda='author changed the character' WHERE character_id='CHAR-A'")
            conn.commit()
        with self.assertRaises(OperationError) as conflict:
            self.settle_accepted(acceptance)
        self.assertEqual("narrative_state_conflict", conflict.exception.code)
        with self.store.open_project("PROD") as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM canon_state").fetchone()[0])

    def test_final_memory_rejects_evidence_not_in_candidate_text(self):
        fake = FinalStateFixtureRuntime(invalid_quote=True)
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        with self.assertRaises(ProductionRunError) as invalid:
            self.execute_to_handoff(runtime, run_id)
        self.assertEqual("semantic_output_invalid", invalid.exception.code)
        self.assertEqual("semantic_pending", runtime.status("PROD", run_id)["status"])
        with self.store.open_project("PROD") as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM expectations").fetchone()[0])
            failure = json.loads(conn.execute("SELECT payload_json FROM runtime_events WHERE run_id=? AND event_kind='production_stage_failed'", (run_id,)).fetchone()[0])
            self.assertEqual("registered_reader_expectations", failure["mechanism"])
            assert_public_execution_safe(self, failure)

    def test_changed_bundle_cannot_be_rebound_as_final_narrative_evidence(self):
        from production_runtime.semantic import build_narrative_state_proposal
        fake = FinalStateFixtureRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        self.execute_to_handoff(runtime, run_id)
        state = runtime._latest_checkpoint("PROD", run_id, "production_narrative_proposal")
        bundle = runtime._latest_bundle("PROD", run_id)
        bundle["target_context"]["payload"]["instruction"] = "tampered request"
        with self.assertRaises(ProductionRunError) as invalid:
            build_narrative_state_proposal(state["registered_binding"], bundle)
        self.assertEqual("context_bundle_invalid", invalid.exception.code)

    def test_selected_preference_deactivation_stops_before_model_dispatch(self):
        self.seed_preference()
        fake = FakeAgentRuntime()
        run_id = self.start(selected_preference_ids=["PREF-SELECTED"])
        self.seed_preference(state="deprecated")
        result = self.execute_to_handoff(ProductionRunExecutor(self.store, fake), run_id)
        self.assertEqual("stale_conflict", result["status"])
        self.assertEqual([], fake.calls)

    def test_selected_preference_version_change_stops_resume_without_new_calls(self):
        self.seed_preference()
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start(selected_preference_ids=["PREF-SELECTED"])
        self.execute_to_handoff(runtime, run_id)
        count = len(fake.calls)
        self.seed_preference(statement="Changed selected preference.")
        result = runtime.resume_execution("PROD", run_id)
        self.assertEqual("stale_conflict", result["status"])
        self.assertEqual(count, len(fake.calls))

    def test_unselected_preference_changes_do_not_stale_or_enter_writer(self):
        self.seed_preference()
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start(selected_preference_ids=["PREF-SELECTED"])
        self.seed_preference("PREF-UNSELECTED", statement="UNSELECTED SECRET PREFERENCE")
        self.assertEqual("awaiting_external", self.execute_to_handoff(runtime, run_id)["status"])
        writer = next(job for job in fake.calls if job.runtime_role == "event_first_raw_draft")
        self.assertIn("Selected fixture preference.", json.dumps(writer.context))
        self.assertNotIn("UNSELECTED SECRET PREFERENCE", json.dumps(writer.context))
        self.assertNotIn("PREF-UNSELECTED", json.dumps(writer.context))

    def test_prior_history_excludes_unaccepted_current_future_and_stale_narrative(self):
        completed, acceptance = self.release_and_accept()
        self.settle_accepted(acceptance)
        self.add_chapter()
        self.add_chapter("CH003", "DOC-3", 3)
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        sources = runtime.loader.load("PROD", chapter_id="CH002", document_id="DOC-2", current_story_order=2, current_reading_order=2)
        history = [item["model_view"] for item in sources if item["object_type"] == "accepted_manuscript"]
        self.assertEqual(["CH001"], [item["story_node_id"] for item in history])
        self.assertEqual(completed["candidate"]["candidate_fingerprint"], history[0]["content_fingerprint"])
        self.assertNotIn("unaccepted private chapter", json.dumps(sources))
        self.assertIn("CHAR-A", [item["object_id"] for item in sources])
        early = runtime.loader.load("PROD", chapter_id="CH001", document_id="DOC-1", current_story_order=1, current_reading_order=1)
        self.assertNotIn("CHAR-A", [item["object_id"] for item in early])
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE narrative_state_sources SET state='stale'")
            conn.execute("INSERT INTO characters(character_id,name,agenda,voice_notes,state_json,updated_at) VALUES('CHAR-MANUAL','Manual','manual agenda','plain','{}',?)", (now_iso(),))
            conn.commit()
        filtered = runtime.loader.load("PROD", chapter_id="CH002", document_id="DOC-2", current_story_order=2, current_reading_order=2)
        self.assertNotIn("CHAR-A", [item["object_id"] for item in filtered])
        self.assertIn("CHAR-MANUAL", [item["object_id"] for item in filtered])

    def test_prior_rewrite_invalidates_dependent_reader_memory_and_chapter(self):
        from quality.reader_expectation import inspect_project
        _, first_acceptance = self.release_and_accept()
        self.settle_accepted(first_acceptance)
        self.add_chapter()
        _, second_acceptance = self.release_and_accept(FinalStateFixtureRuntime(narrative=False, reader_operation="touch"), chapter_id="CH002", document_id="DOC-2")
        self.settle_accepted(second_acceptance, chapter_id="CH002", idempotency_key="settle-second")
        with self.store.open_project("PROD") as conn:
            original = inspect_project(conn)["items"][0]
            self.assertEqual(2, original["version"])
        _, replacement = self.release_and_accept(FinalStateFixtureRuntime(narrative=False, candidate_text="Changed review prose has different final bytes."))
        self.settle_accepted(replacement, idempotency_key="settle-replacement")
        with self.store.open_project("PROD") as conn:
            items = {item["expectation_id"]: item for item in inspect_project(conn)["items"]}
            self.assertEqual("invalidated", items[original["expectation_id"]]["status"])
            self.assertEqual(2, conn.execute("SELECT COUNT(*) FROM reader_expectation_observations WHERE state='invalidated'").fetchone()[0])
            self.assertEqual("stale", conn.execute("SELECT status FROM chapter_dependencies WHERE chapter_id='CH002'").fetchone()[0])
            self.assertEqual(6, conn.execute("SELECT COUNT(*) FROM narrative_state_sources WHERE state='stale'").fetchone()[0])
        self.add_chapter("CH003", "DOC-3", 3)
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        with self.assertRaises(ProductionRunError) as stale:
            runtime.loader.load("PROD", chapter_id="CH003", document_id="DOC-3", current_story_order=3, current_reading_order=3)
        self.assertEqual("settled_source_stale", stale.exception.code)


class NativeIndependentReviewRuntimeTests(unittest.TestCase):
    """Spec 022 Task 1 contracts; host hooks/adapters remain Task 2."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = QuillframeStore(Path(self.temp.name))
        self.store.create_project("PROD", "Production Fixture")
        with self.store.open_project("PROD") as conn:
            conn.execute("INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) VALUES('CH001','chapter',1,'Chapter','{}')")
            conn.commit()
        self.store.create_document("PROD", "DOC-1", "Chapter", story_node_id="CH001")
        self.store.save_revision("PROD", "DOC-1", "seed", expected_parent_revision_id=None, source="test")
        stamp = now_iso()
        with self.store.open_project("PROD") as conn:
            conn.execute(
                "INSERT INTO characters(character_id,name,agenda,voice_notes,state_json,updated_at) VALUES(?,?,?,?,?,?)",
                ("CHAR-A", "A", "protect the deal", "precise", "{}", stamp),
            )
            conn.execute(
                "INSERT INTO character_knowledge(knowledge_id,character_id,claim_ref,fact_json,available_from_story_order,evidence_ref,confidence) VALUES(?,?,?,?,?,?,?)",
                ("KN-A", "CHAR-A", None, '{"fact":"private knowledge"}', 1, "accepted", "known"),
            )
            conn.execute(
                "INSERT INTO research_sources(source_id,title,source_uri,source_kind,rights_json,provenance_json,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                ("RS-1", "Research", None, "fixture", "{}", "{}", "active", stamp),
            )
            conn.execute(
                "INSERT INTO research_claims(research_claim_id,source_id,claim_text,citation_json,fictionalization_notes,character_knowledge_boundary_json,canon_status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                ("RC-1", "RS-1", "external fact", "{}", None, "{}", "research_only", stamp),
            )
            conn.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def execute_to_handoff(self, runtime: ProductionRunExecutor, run_id: str) -> dict:
        return runtime.execute(
            "PROD",
            run_id,
            service_id="svc",
            instruction="draft chapter",
            reader_grip="very_high",
            rule_material=RULE_MATERIAL,
            independent_provenance=PROVENANCE,
        )

    def submit(self, runtime: ProductionRunExecutor, run_id: str, verdict: str = "pass") -> dict:
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, verdict)
        return runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=project_bridge_receipt(packet, result),
        )

    def start_native(self, session_id: str = "SES-MANAGER") -> str:
        stamp = now_iso()
        with self.store.open_project("PROD") as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions(session_id,status,version,created_at,updated_at) VALUES(?,?,?,?,?)",
                (session_id, "running", 1, stamp, stamp),
            )
            conn.commit()
        run_id = CoreOperations(self.store).start_author_run(
            "PROD",
            task_mode="DRAFT",
            target_ref="DOC-1",
            payload={"instruction": "draft chapter", "chapter_id": "CH001"},
            session_id=session_id,
        )["run_id"]
        NovelWorkflowService(self.store).start(
            project_id="PROD",
            run_id=run_id,
            chapter_id="CH001",
            author_profile="guided",
        )
        return run_id

    def prepare_native(
        self,
        runtime: ProductionRunExecutor,
        run_id: str,
        *,
        provider: str = "codex_native_subagent",
        parent_session_id: str = "SES-MANAGER",
    ) -> tuple[dict, dict]:
        handoff = self.execute_to_handoff(runtime, run_id)
        if not hasattr(runtime, "prepare_independent_dispatch"):
            self.fail("ProductionRunExecutor.prepare_independent_dispatch is required")
        dispatch = runtime.prepare_independent_dispatch(
            "PROD",
            run_id,
            provider=provider,
            parent_session_id=parent_session_id,
        )
        return handoff, dispatch

    def claim_native(
        self,
        runtime: ProductionRunExecutor,
        *,
        provider: str = "codex_native_subagent",
        parent_session_id: str = "SES-MANAGER",
        host_agent_id: str = "agent-native-1",
        host_invocation_id: str = "inv-native-1",
    ) -> dict:
        if not hasattr(runtime, "claim_independent_dispatch"):
            self.fail("ProductionRunExecutor.claim_independent_dispatch is required")
        return runtime.claim_independent_dispatch(
            "PROD",
            provider=provider,
            parent_session_id=parent_session_id,
            agent_type="quillframe-independent-reviewer",
            host_agent_id=host_agent_id,
            host_invocation_id=host_invocation_id,
        )

    def complete_native(self, runtime: ProductionRunExecutor, claim: dict, verdict: str = "pass") -> dict:
        if not hasattr(runtime, "complete_independent_dispatch"):
            self.fail("ProductionRunExecutor.complete_independent_dispatch is required")
        return runtime.complete_independent_dispatch(
            "PROD",
            lease_id=claim["lease_id"],
            reviewer_session_id=claim["reviewer_session_id"],
            host_agent_id=claim["host_agent_id"],
            host_invocation_id=claim["host_invocation_id"],
            result=native_result(claim, verdict),
        )

    def require_generic_submit(self, runtime: ProductionRunExecutor) -> None:
        if "independence_receipt" not in inspect.signature(runtime.submit_independent).parameters:
            self.fail("ProductionRunExecutor.submit_independent must accept independence_receipt")

    def assert_stale_owner_fenced_at_effect_boundary(self, boundary: str) -> None:
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        clock = ManualClock()
        repository = IndependentReviewRepository(
            self.store,
            clock=clock,
            monotonic_clock=clock,
            sleeper=lambda _: None,
            processing_lease_seconds=10.0,
        )
        method_name = "_persist_stage_receipt" if boundary == "receipt" else "_persist_candidate"
        original = getattr(runtime, method_name)
        takeover_started = False
        stale_boundary_returned = False
        recovered_outputs: list[dict] = []
        recovered_errors: list[BaseException] = []

        def recovered_submit() -> None:
            try:
                recovered_outputs.append(runtime.submit_independent(
                    "PROD",
                    run_id,
                    peer_packet=packet,
                    result=result,
                    independence_receipt=receipt,
                ))
            except BaseException as exc:  # pragma: no cover - asserted below
                recovered_errors.append(exc)

        def interleave(*args, **kwargs):  # noqa: ANN002,ANN003,ANN202
            nonlocal takeover_started, stale_boundary_returned
            is_main_owner = threading.current_thread() is threading.main_thread()
            is_target_receipt = boundary != "receipt" or args[2].get("mechanism") == "independent_semantic_gate"
            if not is_main_owner or takeover_started or not is_target_receipt:
                return original(*args, **kwargs)
            takeover_started = True
            with self.store.open_project("PROD") as conn:
                owner_a = conn.execute(
                    "SELECT processing_epoch,processing_phase FROM independent_review_attempts WHERE run_id=?",
                    (run_id,),
                ).fetchone()
            self.assertEqual(owner_a["processing_epoch"], 1)
            self.assertEqual(owner_a["processing_phase"], "effects_started")
            clock.advance(11.0)
            thread = threading.Thread(target=recovered_submit, name=f"recovered-{boundary}")
            thread.start()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertFalse(recovered_errors)
            self.assertEqual(len(recovered_outputs), 1)
            self.assertEqual(recovered_outputs[0]["status"], "completed")
            try:
                value = original(*args, **kwargs)
            except ProductionRunError:
                raise
            stale_boundary_returned = True
            return value

        with patch("production_runtime.runtime.IndependentReviewRepository", return_value=repository):
            with patch.object(runtime, method_name, side_effect=interleave):
                with self.assertRaises(ProductionRunError) as stale:
                    runtime.submit_independent(
                        "PROD",
                        run_id,
                        peer_packet=packet,
                        result=result,
                        independence_receipt=receipt,
                    )
        self.assertEqual(stale.exception.code, "independent_processing_owner_lost")
        self.assertTrue(takeover_started)
        self.assertFalse(stale_boundary_returned)
        with self.store.open_project("PROD") as conn:
            attempt = conn.execute(
                "SELECT status,processing_epoch FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
            candidates = conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0]
            evidence = conn.execute("SELECT COUNT(*) FROM review_evidence").fetchone()[0]
            releases = conn.execute(
                "SELECT COUNT(*) FROM receipts WHERE run_id=? AND receipt_kind='production_release'",
                (run_id,),
            ).fetchone()[0]
            ready_events = conn.execute(
                "SELECT COUNT(*) FROM runtime_events WHERE run_id=? AND event_kind='production_candidate_ready'",
                (run_id,),
            ).fetchone()[0]
            stage_payloads = [
                json.loads(row["payload_json"])
                for row in conn.execute(
                    "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage'",
                    (run_id,),
                )
            ]
        self.assertEqual(dict(attempt), {"status": "terminal", "processing_epoch": 2})
        self.assertEqual(candidates, 1)
        self.assertEqual(evidence, 1)
        self.assertEqual(releases, 1)
        self.assertEqual(ready_events, 1)
        self.assertEqual(sum(item.get("mechanism") == "independent_semantic_gate" for item in stage_payloads), 1)
        self.assertEqual(sum(item.get("mechanism") == "user_visible_gate" for item in stage_payloads), 1)

    def test_clean_install_schema_uses_final_provider_ids_and_processing_fence(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        schema_fragments = ROOT / "persistence" / "schema" / "project"
        for name in ("001_initial.sql", "002_semantic_context_runtime.sql", "003_native_independent_review.sql"):
            conn.executescript((schema_fragments / name).read_text(encoding="utf-8"))
        stamp = "2026-08-19T00:00:00+00:00"
        conn.execute(
            "INSERT INTO project_identity(project_id,title,language,project_schema_version,created_at,updated_at) VALUES('PROD','Fixture','en','1',?,?)",
            (stamp, stamp),
        )
        conn.execute(
            "INSERT INTO sessions(session_id,status,version,created_at,updated_at) VALUES('SES','active',1,?,?)",
            (stamp, stamp),
        )
        conn.execute(
            "INSERT INTO runs(run_id,session_id,task_mode,status,request_fingerprint,created_at,updated_at) VALUES('RUN','SES','DRAFT','awaiting_external','sha256:req',?,?)",
            (stamp, stamp),
        )
        conn.execute(
            "INSERT INTO independent_review_attempts(run_id,candidate_fingerprint,status,created_at,updated_at) VALUES('RUN','sha256:candidate','available',?,?)",
            (stamp, stamp),
        )
        try:
            conn.execute(
                """INSERT INTO independent_review_leases(
                lease_id,project_id,run_id,candidate_fingerprint,job_id,input_fingerprint,packet_bytes,
                packet_fingerprint,relay_nonce,provider,transport,assurance_class,parent_session_id,status,created_at,updated_at
                ) VALUES('LEASE','PROD','RUN','sha256:candidate','JOB','sha256:input',X'7B7D','sha256:packet','NONCE',
                'codex_native_subagent','codex_native','host_native_separate_context','SES','pending',?,?)""",
                (stamp, stamp),
            )
        except sqlite3.IntegrityError as exc:
            self.fail(f"1.0 schema rejected the final native provider ID: {exc}")
        conn.execute(
            "INSERT INTO independent_review_lifecycle_events(event_id,lease_id,run_id,event_kind,event_fingerprint,payload_json,created_at) VALUES('EVENT','LEASE','RUN','prepared','sha256:event','{\"provider\":\"codex_native_subagent\"}',?)",
            (stamp,),
        )
        conn.executescript((schema_fragments / "004_independent_review_processing_lease.sql").read_text(encoding="utf-8"))
        lease = conn.execute("SELECT provider,transport FROM independent_review_leases WHERE lease_id='LEASE'").fetchone()
        event = conn.execute("SELECT payload_json FROM independent_review_lifecycle_events WHERE event_id='EVENT'").fetchone()
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(independent_review_attempts)")}
        triggers = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='candidates'")
        }
        self.assertEqual(dict(lease), {"provider": "codex_native_subagent", "transport": "codex_native"})
        self.assertEqual(json.loads(event["payload_json"])["provider"], "codex_native_subagent")
        self.assertTrue({"processing_epoch", "processing_expires_at", "processing_phase"} <= columns)
        self.assertIn("production_candidate_one_pass_per_run_insert", triggers)
        self.assertIn("production_candidate_one_pass_per_run_update", triggers)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("UPDATE independent_review_leases SET provider='codex' WHERE lease_id='LEASE'")

    def test_stale_owner_is_fenced_at_receipt_write_after_identical_takeover(self):
        self.assert_stale_owner_fenced_at_effect_boundary("receipt")

    def test_stale_owner_is_fenced_at_candidate_write_after_identical_takeover(self):
        self.assert_stale_owner_fenced_at_effect_boundary("candidate")

    def test_default_author_run_session_can_prepare_and_claim_native_review(self):
        started = CoreOperations(self.store).start_author_run(
            "PROD", task_mode="DRAFT", target_ref="DOC-1",
            payload={"instruction": "draft chapter", "chapter_id": "CH001"},
        )
        run_id = started["run_id"]
        parent_session_id = started["session_id"]
        NovelWorkflowService(self.store).start(
            project_id="PROD", run_id=run_id, chapter_id="CH001", author_profile="guided",
        )
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        _, dispatch = self.prepare_native(runtime, run_id, parent_session_id=parent_session_id)
        claim = self.claim_native(runtime, parent_session_id=parent_session_id)

        self.assertEqual(claim["lease_id"], dispatch["lease_id"])
        self.assertEqual(claim["parent_session_id"], parent_session_id)
        self.assertNotEqual(claim["reviewer_session_id"], parent_session_id)
        self.assertEqual(claim["peer_packet"], frozen_packet(self.store, run_id))
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT session_id FROM runs WHERE run_id=?", (run_id,)).fetchone()[0], parent_session_id)
            self.assertEqual({row["session_id"] for row in conn.execute("SELECT session_id FROM sessions")}, {parent_session_id, claim["reviewer_session_id"]})

    def test_native_dispatch_withholds_packet_and_claim_is_one_time_with_distinct_session(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff, dispatch = self.prepare_native(runtime, run_id, provider="codex_native_subagent")

        self.assertEqual(dispatch["schema"], "quillframe_independent_dispatch_v1")
        self.assertEqual(dispatch["provider"], "codex_native_subagent")
        self.assertEqual(dispatch["transport"], "codex_native")
        self.assertEqual(dispatch["assurance_class"], "host_native_separate_context")
        self.assertNotIn("peer_packet", dispatch)
        self.assertNotIn("packet_bytes", dispatch)
        self.assertNotIn("candidate_text", json.dumps(dispatch))
        with self.store.open_project("PROD") as conn:
            persisted = conn.execute(
                "SELECT provider,transport FROM independent_review_leases WHERE lease_id=?",
                (dispatch["lease_id"],),
            ).fetchone()
            prepared_payload = conn.execute(
                "SELECT payload_json FROM independent_review_lifecycle_events WHERE lease_id=? AND event_kind='prepared'",
                (dispatch["lease_id"],),
            ).fetchone()["payload_json"]
        self.assertEqual(dict(persisted), {"provider": "codex_native_subagent", "transport": "codex_native"})
        self.assertEqual(json.loads(prepared_payload)["provider"], "codex_native_subagent")
        self.assertNotIn('"provider":"codex"', prepared_payload)

        claim = self.claim_native(runtime, provider="codex_native_subagent")
        self.assertEqual(claim["peer_packet"], frozen_packet(self.store, run_id))
        self.assertEqual(
            claim["packet_bytes"],
            json.dumps(claim["peer_packet"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
        self.assertEqual(
            claim["peer_packet"].get("execution_permissions"),
            {
                "project_read": False,
                "filesystem": False,
                "shell": False,
                "network": False,
                "memory": False,
                "write": False,
            },
        )
        self.assertEqual(claim["parent_session_id"], "SES-MANAGER")
        self.assertNotEqual(claim["reviewer_session_id"], claim["parent_session_id"])
        with self.assertRaises(ProductionRunError) as caught:
            self.claim_native(runtime, host_agent_id="agent-native-2", host_invocation_id="inv-native-2")
        self.assertEqual(caught.exception.code, "independent_lease_not_pending")

    def test_native_receipt_is_durable_exact_and_surfaces_provider_transport_assurance(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        completed = self.complete_native(runtime, claim)

        self.assertEqual(completed["status"], "completed")
        gate = next(g for g in completed["production_readiness"]["gates"] if g["category"] == "semantic_independent")
        independence = gate["semantic_contract"]["independence"]
        self.assertEqual(independence["provider"], "codex_native_subagent")
        self.assertEqual(independence["transport"], "codex_native")
        self.assertEqual(independence["assurance_class"], "host_native_separate_context")
        with self.store.open_project("PROD") as conn:
            lease = conn.execute(
                "SELECT status,receipt_json FROM independent_review_leases WHERE lease_id=?", (claim["lease_id"],)
            ).fetchone()
            events = conn.execute(
                "SELECT event_kind FROM independent_review_lifecycle_events WHERE lease_id=? ORDER BY rowid",
                (claim["lease_id"],),
            ).fetchall()
        receipt = json.loads(lease["receipt_json"])
        self.assertEqual(lease["status"], "completed")
        self.assertEqual(receipt["schema"], "quillframe_independent_invocation_receipt_v1")
        self.assertEqual(receipt["project_id"], "PROD")
        self.assertEqual(receipt["run_id"], run_id)
        self.assertEqual(receipt["provider"], "codex_native_subagent")
        self.assertEqual(receipt["parent_session_id"], "SES-MANAGER")
        self.assertEqual(receipt["reviewer_session_id"], claim["reviewer_session_id"])
        for permission in ("project_read", "filesystem", "shell", "network", "memory", "write"):
            self.assertIs(receipt["permissions"][permission], False)
        self.assertEqual([row["event_kind"] for row in events], ["prepared", "claimed", "completed"])
        self.assertTrue(receipt["receipt_fingerprint"].startswith("sha256:"))

        malformed = {**receipt, "host_agent_id": ""}
        malformed["receipt_fingerprint"] = native_fingerprint(
            {key: value for key, value in malformed.items() if key != "receipt_fingerprint"}
        )
        self.assertTrue(any("host_agent_id" in error for error in validate_native_receipt(
            malformed,
            claim["peer_packet"],
            native_result(claim),
        )))

    def test_native_judgment_completion_rehydrates_exact_packet_only_inside_core(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        judgment = native_result(claim, "pass")["judgment"]

        completed = runtime.complete_independent_judgment(
            "PROD",
            lease_id=claim["lease_id"],
            reviewer_session_id=claim["reviewer_session_id"],
            host_agent_id=claim["host_agent_id"],
            host_invocation_id=claim["host_invocation_id"],
            judgment=judgment,
        )

        self.assertEqual(completed["status"], "completed")
        with self.store.open_project("PROD") as conn:
            lease = conn.execute(
                "SELECT status,receipt_json FROM independent_review_leases WHERE lease_id=?",
                (claim["lease_id"],),
            ).fetchone()
        receipt = json.loads(lease["receipt_json"])
        self.assertEqual(lease["status"], "completed")
        self.assertEqual(receipt["job_id"], claim["peer_packet"]["job"]["job_id"])
        self.assertEqual(receipt["relay_nonce"], claim["peer_packet"]["relay_nonce"])

    def test_invalid_native_result_does_not_consume_completion_plan(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        invalid = native_result(claim, "pass")
        invalid["worker"]["provider"] = "claude_native_subagent"
        with self.assertRaises(ProductionRunError) as caught:
            runtime.complete_independent_dispatch(
                "PROD",
                lease_id=claim["lease_id"],
                reviewer_session_id=claim["reviewer_session_id"],
                host_agent_id=claim["host_agent_id"],
                host_invocation_id=claim["host_invocation_id"],
                result=invalid,
            )
        self.assertEqual(caught.exception.code, "independent_result_invalid")

        completed = self.complete_native(runtime, claim)
        self.assertEqual(completed["status"], "completed")

    def test_fabricated_native_completion_event_is_rejected_before_side_effects(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        result = native_result(claim, "pass")
        repository = IndependentReviewRepository(self.store)
        planned = repository.planned_completion_event(
            "PROD",
            claim["lease_id"],
            native_fingerprint(result),
        )
        fabricated = {**planned, "event_id": "irevt_fabricated"}
        fabricated["event_fingerprint"] = native_fingerprint(
            {key: value for key, value in fabricated.items() if key != "event_fingerprint"}
        )
        durable = repository.lifecycle_events("PROD", claim["lease_id"])
        receipt = build_native_receipt(
            claim["peer_packet"],
            result,
            lease_id=claim["lease_id"],
            project_id="PROD",
            run_id=run_id,
            provider="codex_native_subagent",
            parent_session_id=claim["parent_session_id"],
            reviewer_session_id=claim["reviewer_session_id"],
            host_agent_id=claim["host_agent_id"],
            host_invocation_id=claim["host_invocation_id"],
            lifecycle_events=[
                *[runtime._lifecycle_receipt_event(event) for event in durable],
                runtime._lifecycle_receipt_event(fabricated),
            ],
        )
        with self.assertRaises(ProductionRunError) as caught:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=claim["peer_packet"],
                result=result,
                independence_receipt=receipt,
                _native_lease_id=claim["lease_id"],
                _native_completion_event=fabricated,
            )
        self.assertEqual(caught.exception.code, "independent_invocation_receipt_invalid")
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 0)

    def test_claim_rejects_untrusted_agent_type_without_consuming_lease(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.prepare_native(runtime, run_id)
        with self.assertRaises(ProductionRunError) as caught:
            runtime.claim_independent_dispatch(
                "PROD",
                provider="codex_native_subagent",
                parent_session_id="SES-MANAGER",
                agent_type="writer",
                host_agent_id="agent-writer",
                host_invocation_id="inv-writer",
            )
        self.assertEqual(caught.exception.code, "independent_agent_type_invalid")
        claim = self.claim_native(runtime)
        self.assertEqual(claim["host_agent_id"], "agent-native-1")

    def test_reused_host_agent_or_invocation_id_is_rejected_across_runs(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        first = self.start_native("SES-MANAGER")
        self.prepare_native(runtime, first)
        claim = self.claim_native(runtime, host_agent_id="agent-reuse", host_invocation_id="inv-reuse")
        if not hasattr(runtime, "fail_independent_dispatch"):
            self.fail("ProductionRunExecutor.fail_independent_dispatch is required")
        runtime.fail_independent_dispatch(
            "PROD",
            lease_id=claim["lease_id"],
            reviewer_session_id=claim["reviewer_session_id"],
            host_agent_id="agent-reuse",
            host_invocation_id="inv-reuse",
            error={"code": "fixture_infrastructure_failure"},
        )

        second = self.start_native("SES-MANAGER")
        self.prepare_native(runtime, second)
        with self.assertRaises(ProductionRunError) as agent_error:
            self.claim_native(runtime, host_agent_id="agent-reuse", host_invocation_id="inv-new")
        self.assertEqual(agent_error.exception.code, "independent_host_identity_reused")
        with self.assertRaises(ProductionRunError) as invocation_error:
            self.claim_native(runtime, host_agent_id="agent-new", host_invocation_id="inv-reuse")
        self.assertEqual(invocation_error.exception.code, "independent_host_identity_reused")

    def test_project_identity_drift_blocks_native_infrastructure_failure_mutation(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native("SES-MANAGER")
        self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE project_identity SET project_id='FOREIGN'")
            conn.commit()

        with self.assertRaises(ProductionRunError) as caught:
            runtime.fail_independent_dispatch(
                "PROD",
                lease_id=claim["lease_id"],
                reviewer_session_id=claim["reviewer_session_id"],
                host_agent_id=claim["host_agent_id"],
                host_invocation_id=claim["host_invocation_id"],
                error={"code": "transport_failed"},
            )
        self.assertEqual(caught.exception.code, "independent_project_mismatch")
        with self.store.open_project("PROD") as conn:
            lease = conn.execute(
                "SELECT status,infrastructure_error_json FROM independent_review_leases WHERE lease_id=?",
                (claim["lease_id"],),
            ).fetchone()
            failed_events = conn.execute(
                "SELECT COUNT(*) FROM independent_review_lifecycle_events WHERE lease_id=? AND event_kind='infrastructure_failed'",
                (claim["lease_id"],),
            ).fetchone()[0]
        self.assertEqual(dict(lease), {"status": "claimed", "infrastructure_error_json": None})
        self.assertEqual(failed_events, 0)

    def test_active_native_lease_blocks_peer_transport_but_infrastructure_failure_allows_takeover(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff, _ = self.prepare_native(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        peer_submission = peer_result(packet, "pass")
        peer_receipt = project_bridge_receipt(packet, peer_submission)
        with self.assertRaises(ProductionRunError) as blocked:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=peer_submission,
                independence_receipt=peer_receipt,
            )
        self.assertEqual(blocked.exception.code, "independent_native_lease_active")

        claim = self.claim_native(runtime)
        runtime.fail_independent_dispatch(
            "PROD",
            lease_id=claim["lease_id"],
            reviewer_session_id=claim["reviewer_session_id"],
            host_agent_id=claim["host_agent_id"],
            host_invocation_id=claim["host_invocation_id"],
            error={"code": "invalid_json"},
        )
        completed = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=peer_submission,
            independence_receipt=peer_receipt,
        )
        self.assertEqual(completed["status"], "completed")

    def test_native_fail_consumes_attempt_and_exact_fail_replays(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff, _ = self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        native_failure = native_result(claim, "fail")
        failed = runtime.complete_independent_dispatch(
            "PROD",
            lease_id=claim["lease_id"],
            reviewer_session_id=claim["reviewer_session_id"],
            host_agent_id=claim["host_agent_id"],
            host_invocation_id=claim["host_invocation_id"],
            result=native_failure,
        )
        replay = runtime.complete_independent_dispatch(
            "PROD",
            lease_id=claim["lease_id"],
            reviewer_session_id=claim["reviewer_session_id"],
            host_agent_id=claim["host_agent_id"],
            host_invocation_id=claim["host_invocation_id"],
            result=native_failure,
        )
        self.assertEqual(failed, replay)
        self.assertEqual(failed["status"], "failed_gate")

        packet = frozen_packet(self.store, run_id)
        peer_submission = peer_result(packet, "pass")
        with self.assertRaises(ProductionRunError) as consumed:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=peer_submission,
                independence_receipt=project_bridge_receipt(packet, peer_submission),
            )
        self.assertEqual(consumed.exception.code, "independent_attempt_consumed")

    def test_peer_pass_consumes_attempt_and_blocks_native_dispatch(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff = self.execute_to_handoff(runtime, run_id)
        completed = self.submit(runtime, run_id)
        self.assertEqual(completed["status"], "completed")
        if not hasattr(runtime, "prepare_independent_dispatch"):
            self.fail("ProductionRunExecutor.prepare_independent_dispatch is required")
        with self.assertRaises(ProductionRunError) as consumed:
            runtime.prepare_independent_dispatch(
                "PROD", run_id, provider="claude_native_subagent", parent_session_id="SES-MANAGER"
            )
        self.assertEqual(consumed.exception.code, "independent_attempt_consumed")

    def test_handoff_without_1_0_packet_bytes_is_rejected_without_rewrite(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        with self.store.open_project("PROD") as conn:
            row = conn.execute(
                "SELECT checkpoint_id,state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_independent_handoff' ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            invalid = json.loads(row["state_json"])
            invalid.pop("peer_packet_bytes")
            conn.execute(
                "UPDATE checkpoints SET state_json=? WHERE checkpoint_id=?",
                (json.dumps(invalid, sort_keys=True, separators=(",", ":")), row["checkpoint_id"]),
            )
            conn.commit()
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        with self.assertRaises(ProductionRunError) as rejected:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=result,
                independence_receipt=receipt,
            )
        self.assertEqual(rejected.exception.code, "independent_handoff_invalid")
        with self.store.open_project("PROD") as conn:
            rows = conn.execute(
                "SELECT state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_independent_handoff' ORDER BY created_at,rowid",
                (run_id,),
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("peer_packet_bytes", json.loads(rows[0]["state_json"]))

    def test_foreign_project_provenance_and_fabricated_native_receipt_fail_closed(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        foreign = {**PROVENANCE, "project_id": "FOREIGN"}
        with self.assertRaises(ProductionRunError) as provenance_error:
            runtime.execute(
                "PROD",
                run_id,
                service_id="svc",
                instruction="draft chapter",
                reader_grip="very_high",
                rule_material=RULE_MATERIAL,
                independent_provenance=foreign,
            )
        self.assertEqual(provenance_error.exception.code, "independent_project_mismatch")

        second = self.start_native()
        handoff = self.execute_to_handoff(runtime, second)
        packet = frozen_packet(self.store, second)
        result = peer_result(packet, "pass")
        fabricated = project_bridge_receipt(packet, result)
        fabricated["schema"] = "quillframe_independent_invocation_receipt_v1"
        fabricated["receipt_fingerprint"] = "sha256:" + "0" * 64
        with self.assertRaises(ProductionRunError) as receipt_error:
            runtime.submit_independent(
                "PROD",
                second,
                peer_packet=packet,
                result=result,
                independence_receipt=fabricated,
            )
        self.assertEqual(receipt_error.exception.code, "independent_invocation_receipt_invalid")

    def test_actual_project_identity_is_rechecked_before_packet_creation(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        awaiting = runtime.execute(
            "PROD",
            run_id,
            service_id="svc",
            instruction="draft chapter",
            reader_grip="very_high",
            rule_material=RULE_MATERIAL,
        )
        self.assertEqual(awaiting["awaiting"], "independent_provenance")
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE project_identity SET project_id='FOREIGN'")
            conn.commit()
        with self.assertRaises(ProductionRunError) as mismatch:
            self.execute_to_handoff(runtime, run_id)
        self.assertEqual(mismatch.exception.code, "independent_project_mismatch")
        with self.store.open_project("PROD") as conn:
            checkpoints = conn.execute(
                "SELECT COUNT(*) FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_independent_handoff'",
                (run_id,),
            ).fetchone()[0]
        self.assertEqual(checkpoints, 0)

    def test_actual_project_identity_drift_blocks_peer_submission_before_attempt_or_release(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE project_identity SET project_id='FOREIGN'")
            conn.commit()
        with self.assertRaises(ProductionRunError) as mismatch:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=result,
                independence_receipt=receipt,
            )
        self.assertEqual(mismatch.exception.code, "independent_project_mismatch")
        with self.store.open_project("PROD") as conn:
            attempt = conn.execute(
                "SELECT status,terminal_response_json FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
            releases = conn.execute(
                "SELECT COUNT(*) FROM receipts WHERE run_id=? AND receipt_kind='production_release'",
                (run_id,),
            ).fetchone()[0]
            candidates = conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0]
        self.assertEqual(attempt["status"], "available")
        self.assertIsNone(attempt["terminal_response_json"])
        self.assertEqual(releases, 0)
        self.assertEqual(candidates, 0)

    def test_actual_project_identity_drift_blocks_native_before_attempt_or_release(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        result = native_result(claim, "pass")
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE project_identity SET project_id='FOREIGN'")
            conn.commit()
        with self.assertRaises(ProductionRunError) as mismatch:
            runtime.complete_independent_dispatch(
                "PROD",
                lease_id=claim["lease_id"],
                reviewer_session_id=claim["reviewer_session_id"],
                host_agent_id=claim["host_agent_id"],
                host_invocation_id=claim["host_invocation_id"],
                result=result,
            )
        self.assertEqual(mismatch.exception.code, "independent_project_mismatch")
        with self.store.open_project("PROD") as conn:
            attempt = conn.execute(
                "SELECT status,terminal_response_json FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
            lease = conn.execute(
                "SELECT status FROM independent_review_leases WHERE lease_id=?",
                (claim["lease_id"],),
            ).fetchone()
            releases = conn.execute(
                "SELECT COUNT(*) FROM receipts WHERE run_id=? AND receipt_kind='production_release'",
                (run_id,),
            ).fetchone()[0]
            candidates = conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0]
        self.assertEqual(attempt["status"], "available")
        self.assertIsNone(attempt["terminal_response_json"])
        self.assertEqual(lease["status"], "claimed")
        self.assertEqual(releases, 0)
        self.assertEqual(candidates, 0)

    def test_tampered_completed_replay_is_rejected(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff = self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        self.require_generic_submit(runtime)
        first = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=receipt,
        )
        self.assertEqual(first["status"], "completed")
        tampered = json.loads(json.dumps(result))
        tampered["judgment"]["report"] = "tampered replay"
        with self.assertRaises(ProductionRunError) as conflict:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=tampered,
                independence_receipt=receipt,
            )
        self.assertIn(
            conflict.exception.code,
            {"independent_attempt_consumed", "independent_bridge_receipt_invalid"},
        )

    def test_two_synchronized_identical_pass_submissions_share_terminal_response_and_side_effects(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff = self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        self.require_generic_submit(runtime)
        barrier = threading.Barrier(3)
        outputs: list[dict] = []
        failures: list[BaseException] = []

        def submit() -> None:
            try:
                barrier.wait(timeout=3)
                outputs.append(runtime.submit_independent(
                    "PROD",
                    run_id,
                    peer_packet=packet,
                    result=result,
                    independence_receipt=receipt,
                ))
            except BaseException as exc:  # pragma: no cover - asserted below
                failures.append(exc)

        threads = [threading.Thread(target=submit), threading.Thread(target=submit)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=3)
        for thread in threads:
            thread.join(timeout=5)
        self.assertFalse(failures)
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0], outputs[1])
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM review_evidence").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE run_id=? AND receipt_kind='production_release'", (run_id,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM receipts WHERE run_id=? AND receipt_kind='production_stage' AND idempotency_key LIKE '%independent_semantic_gate'", (run_id,)).fetchone()[0], 1)

    def test_two_synchronized_identical_native_completions_share_terminal_response(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        result = native_result(claim, "pass")
        barrier = threading.Barrier(2)
        original = IndependentReviewRepository.begin_attempt
        outputs: list[dict] = []
        failures: list[BaseException] = []

        def synchronized_begin(repository, *args, **kwargs):  # noqa: ANN001
            barrier.wait(timeout=3)
            return original(repository, *args, **kwargs)

        def complete() -> None:
            try:
                outputs.append(runtime.complete_independent_dispatch(
                    "PROD",
                    lease_id=claim["lease_id"],
                    reviewer_session_id=claim["reviewer_session_id"],
                    host_agent_id=claim["host_agent_id"],
                    host_invocation_id=claim["host_invocation_id"],
                    result=result,
                ))
            except BaseException as exc:  # pragma: no cover - asserted below
                failures.append(exc)

        with patch.object(IndependentReviewRepository, "begin_attempt", new=synchronized_begin):
            threads = [threading.Thread(target=complete), threading.Thread(target=complete)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
        self.assertFalse(failures)
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0], outputs[1])
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM independent_review_lifecycle_events WHERE lease_id=? AND event_kind='completed'", (claim["lease_id"],)).fetchone()[0], 1)

    def test_native_finalization_crash_releases_and_exact_result_resumes(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.prepare_native(runtime, run_id)
        claim = self.claim_native(runtime)
        result = native_result(claim, "pass")

        with patch.object(
            IndependentReviewRepository,
            "finalize_native",
            side_effect=RuntimeError("fixture finalization crash"),
        ):
            with self.assertRaises(RuntimeError):
                runtime.complete_independent_dispatch(
                    "PROD",
                    lease_id=claim["lease_id"],
                    reviewer_session_id=claim["reviewer_session_id"],
                    host_agent_id=claim["host_agent_id"],
                    host_invocation_id=claim["host_invocation_id"],
                    result=result,
                )

        resumed = runtime.complete_independent_dispatch(
            "PROD",
            lease_id=claim["lease_id"],
            reviewer_session_id=claim["reviewer_session_id"],
            host_agent_id=claim["host_agent_id"],
            host_invocation_id=claim["host_invocation_id"],
            result=result,
        )
        self.assertEqual(resumed["status"], "completed")
        with self.store.open_project("PROD") as conn:
            attempt = conn.execute(
                "SELECT status FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
            lease = conn.execute(
                "SELECT status FROM independent_review_leases WHERE lease_id=?",
                (claim["lease_id"],),
            ).fetchone()
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 1)
        self.assertEqual(attempt["status"], "terminal")
        self.assertEqual(lease["status"], "completed")

    def test_post_candidate_processing_crash_resumes_without_duplicate_candidate(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff = self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        original = runtime._set_independent_run
        failed_once = False

        def crash_after_candidate(project_id, target_run_id, status, **kwargs):  # noqa: ANN001
            nonlocal failed_once
            if status == "completed" and not failed_once:
                failed_once = True
                raise RuntimeError("fixture post-candidate crash")
            return original(project_id, target_run_id, status, **kwargs)

        with patch.object(runtime, "_set_independent_run", side_effect=crash_after_candidate):
            with self.assertRaises(RuntimeError):
                runtime.submit_independent(
                    "PROD",
                    run_id,
                    peer_packet=packet,
                    result=result,
                    independence_receipt=receipt,
                )
        resumed = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=receipt,
        )
        self.assertEqual(resumed["status"], "completed")
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM review_evidence").fetchone()[0], 1)

    def test_pass_side_effect_crash_blocks_different_fail_and_exact_pass_recovers(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff = self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        pass_result = peer_result(packet, "pass")
        pass_receipt = project_bridge_receipt(packet, pass_result)
        with patch.object(
            runtime,
            "_persist_candidate_ready_event",
            side_effect=RuntimeError("fixture event crash"),
        ):
            with self.assertRaises(RuntimeError):
                runtime.submit_independent(
                    "PROD",
                    run_id,
                    peer_packet=packet,
                    result=pass_result,
                    independence_receipt=pass_receipt,
                )
        fail_result = peer_result(packet, "fail")
        fail_receipt = project_bridge_receipt(packet, fail_result)
        with self.assertRaises(ProductionRunError) as different:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=fail_result,
                independence_receipt=fail_receipt,
            )
        self.assertEqual(different.exception.code, "independent_attempt_consumed")
        resumed = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=pass_result,
            independence_receipt=pass_receipt,
        )
        self.assertEqual(resumed["status"], "completed")
        with self.store.open_project("PROD") as conn:
            events = conn.execute(
                "SELECT payload_json FROM runtime_events WHERE run_id=? AND event_kind='production_candidate_ready'",
                (run_id,),
            ).fetchall()
            attempt = conn.execute(
                "SELECT status,terminal_evidence_fingerprint FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
            candidate_count = conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0]
            evidence_count = conn.execute("SELECT COUNT(*) FROM review_evidence").fetchone()[0]
            release_count = conn.execute(
                "SELECT COUNT(*) FROM receipts WHERE run_id=? AND receipt_kind='production_release'",
                (run_id,),
            ).fetchone()[0]
            stage_payloads = [
                json.loads(row["payload_json"])
                for row in conn.execute(
                    "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage'",
                    (run_id,),
                )
            ]
        self.assertEqual(len(events), 1)
        self.assertEqual(candidate_count, 1)
        self.assertEqual(evidence_count, 1)
        self.assertEqual(release_count, 1)
        self.assertEqual(sum(item.get("mechanism") == "independent_semantic_gate" for item in stage_payloads), 1)
        self.assertEqual(sum(item.get("mechanism") == "user_visible_gate" for item in stage_payloads), 1)
        self.assertEqual(attempt["status"], "terminal")

    def test_fresh_run_rejects_pre_1_0_peer_receipt_before_attempt_acquisition(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        receipt["schema"] = "quillframe_project_peer_validation_receipt_v1"
        with self.assertRaises(ProductionRunError) as blocked:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=result,
                independence_receipt=receipt,
            )
        self.assertEqual(blocked.exception.code, "independent_bridge_receipt_invalid")
        with self.store.open_project("PROD") as conn:
            run = conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            attempt = conn.execute(
                "SELECT status FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM review_evidence").fetchone()[0], 0)
        self.assertEqual(run["status"], "awaiting_external")
        self.assertEqual(attempt["status"], "available")

    def test_completed_recovery_verifies_exact_persisted_submission_evidence(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        with patch.object(
            runtime,
            "_persist_candidate_ready_event",
            side_effect=RuntimeError("fixture event crash"),
        ):
            with self.assertRaises(RuntimeError):
                runtime.submit_independent(
                    "PROD",
                    run_id,
                    peer_packet=packet,
                    result=result,
                    independence_receipt=receipt,
                )
        with self.store.open_project("PROD") as conn:
            row = conn.execute(
                "SELECT review_id,result_json FROM review_evidence WHERE independent=1",
            ).fetchone()
            persisted = json.loads(row["result_json"])
            self.assertIn("submission_evidence_fingerprint", persisted)
            persisted["submission_evidence_fingerprint"] = "sha256:" + "0" * 64
            conn.execute(
                "UPDATE review_evidence SET result_json=? WHERE review_id=?",
                (json.dumps(persisted, sort_keys=True, separators=(",", ":")), row["review_id"]),
            )
            conn.commit()
        with self.assertRaises(ProductionRunError) as mismatch:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=result,
                independence_receipt=receipt,
            )
        self.assertEqual(mismatch.exception.code, "independent_recovery_evidence_mismatch")
        with self.store.open_project("PROD") as conn:
            attempt = conn.execute(
                "SELECT status,terminal_response_json FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
        self.assertEqual(attempt["status"], "processing")
        self.assertIsNone(attempt["terminal_response_json"])

    def test_abandoned_processing_lease_only_allows_identical_evidence_to_reclaim_after_expiry(self):
        if "clock" not in inspect.signature(IndependentReviewRepository).parameters:
            self.fail("IndependentReviewRepository requires an injectable processing-lease clock")
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        self.execute_to_handoff(runtime, run_id)
        handoff = frozen_handoff(self.store, run_id)
        clock = ManualClock()
        repository = IndependentReviewRepository(
            self.store,
            clock=clock,
            monotonic_clock=clock,
            sleeper=lambda _: None,
            processing_lease_seconds=10.0,
        )
        first = repository.begin_attempt(
            "PROD",
            run_id,
            handoff["candidate_fingerprint"],
            evidence_fingerprint="evidence:A",
            transport="github_actions",
            wait_seconds=0,
        )
        self.assertTrue(first["owner"])
        with self.assertRaises(IndependentReviewError) as live_same:
            repository.begin_attempt(
                "PROD",
                run_id,
                handoff["candidate_fingerprint"],
                evidence_fingerprint="evidence:A",
                transport="github_actions",
                wait_seconds=0,
            )
        self.assertEqual(getattr(live_same.exception, "code", None), "independent_submission_in_progress")
        with self.assertRaises(IndependentReviewError) as different:
            repository.begin_attempt(
                "PROD",
                run_id,
                handoff["candidate_fingerprint"],
                evidence_fingerprint="evidence:B",
                transport="github_actions",
                wait_seconds=0,
            )
        self.assertEqual(different.exception.code, "independent_attempt_consumed")

        clock.advance(11.0)
        with self.assertRaises(IndependentReviewError) as expired_different:
            repository.begin_attempt(
                "PROD",
                run_id,
                handoff["candidate_fingerprint"],
                evidence_fingerprint="evidence:B",
                transport="github_actions",
                wait_seconds=0,
            )
        self.assertEqual(expired_different.exception.code, "independent_attempt_consumed")
        recovered = repository.begin_attempt(
            "PROD",
            run_id,
            handoff["candidate_fingerprint"],
            evidence_fingerprint="evidence:A",
            transport="github_actions",
            wait_seconds=0,
        )
        self.assertTrue(recovered["owner"])
        self.assertTrue(recovered["recovered"])
        self.assertNotEqual(first["processing_token"], recovered["processing_token"])
        self.assertGreater(recovered["processing_epoch"], first["processing_epoch"])
        with self.assertRaises(IndependentReviewError) as stale_heartbeat:
            repository.mark_attempt_effects_started(
                "PROD",
                run_id,
                handoff["candidate_fingerprint"],
                first["processing_token"],
                first["processing_epoch"],
            )
        self.assertEqual(stale_heartbeat.exception.code, "independent_processing_owner_lost")
        repository.abandon_attempt(
            "PROD",
            run_id,
            handoff["candidate_fingerprint"],
            first["processing_token"],
            first["processing_epoch"],
        )
        with self.store.open_project("PROD") as conn:
            current = conn.execute(
                "SELECT processing_token,processing_epoch,status FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
        self.assertEqual(
            dict(current),
            {
                "processing_token": recovered["processing_token"],
                "processing_epoch": recovered["processing_epoch"],
                "status": "processing",
            },
        )
        with self.assertRaises(IndependentReviewError) as stale_release:
            repository.release_attempt(
                "PROD",
                run_id,
                handoff["candidate_fingerprint"],
                first["processing_token"],
                first["processing_epoch"],
            )
        self.assertEqual(stale_release.exception.code, "independent_processing_owner_lost")
        repository.terminalize_attempt(
            "PROD",
            run_id,
            handoff["candidate_fingerprint"],
            processing_token=recovered["processing_token"],
            processing_epoch=recovered["processing_epoch"],
            evidence_fingerprint="evidence:A",
            response={"status": "completed", "candidate_visible": False},
        )
        replay = repository.begin_attempt(
            "PROD",
            run_id,
            handoff["candidate_fingerprint"],
            evidence_fingerprint="evidence:A",
            transport="github_actions",
            wait_seconds=0,
        )
        self.assertFalse(replay["owner"])
        self.assertEqual(replay["response"], {"status": "completed", "candidate_visible": False})

    def test_failed_processing_releases_claim_and_exact_evidence_resumes(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff = self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        self.require_generic_submit(runtime)
        original = runtime._persist_candidate
        with patch.object(runtime, "_persist_candidate", side_effect=RuntimeError("fixture processing crash")):
            with self.assertRaises(RuntimeError):
                runtime.submit_independent(
                    "PROD",
                    run_id,
                    peer_packet=packet,
                    result=result,
                    independence_receipt=receipt,
                )
        runtime._persist_candidate = original
        resumed = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=receipt,
        )
        self.assertEqual(resumed["status"], "completed")
        with self.store.open_project("PROD") as conn:
            attempt = conn.execute(
                "SELECT status,terminal_response_json FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
        self.assertEqual(attempt["status"], "terminal")
        self.assertEqual(json.loads(attempt["terminal_response_json"]), resumed)


if __name__ == "__main__":
    unittest.main()
