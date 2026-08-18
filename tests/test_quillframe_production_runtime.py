from __future__ import annotations

import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path

from agent_runtime import AgentJob, AgentResult
from core_operations import CoreOperations
from harness.context_runtime import MANDATORY_PRODUCTION_MECHANISMS
from persistence.quillframe_sqlite import QuillframeStore, now_iso
from production_runtime import PRODUCTION_MECHANISMS, ProductionRunError, ProductionRunExecutor

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


def peer_result(handoff: dict, verdict: str = "pass") -> dict:
    packet = handoff["independent_review_request"]["peer_packet"]
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


def project_bridge_receipt(handoff: dict, result: dict) -> dict:
    packet = handoff["independent_review_request"]["peer_packet"]
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


class ProductionRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = QuillframeStore(Path(self.temp.name))
        self.store.create_project("PROD", "Production Fixture")
        self.store.create_document("PROD", "DOC-1", "Chapter")
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

    def start(self) -> str:
        return CoreOperations(self.store).start_author_run(
            "PROD",
            task_mode="DRAFT",
            target_ref="DOC-1",
            payload={"instruction": "draft chapter"},
        )["run_id"]

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

    def submit(self, runtime: ProductionRunExecutor, run_id: str, handoff: dict, verdict: str = "pass") -> dict:
        result = peer_result(handoff, verdict)
        return runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=handoff["independent_review_request"]["peer_packet"],
            result=result,
            bridge_receipt=project_bridge_receipt(handoff, result),
        )

    def test_full_graph_uses_frozen_context_and_real_external_independent_boundary(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        handoff = self.execute_to_handoff(runtime, run_id)

        self.assertEqual(handoff["status"], "awaiting_external")
        self.assertEqual(handoff["awaiting"], "independent_semantic_review")
        self.assertFalse(handoff["candidate_visible"])
        self.assertFalse(any(job.runtime_role == "independent_semantic_gate" for job in fake.calls))
        self.assertIn("registered_reader_engagement", [job.runtime_role for job in fake.calls])
        self.assertIn("registered_candidate_self_audit", [job.runtime_role for job in fake.calls])
        packet = handoff["independent_review_request"]["peer_packet"]
        self.assertTrue(packet["return_binding"]["fresh_conversation_required"])
        self.assertTrue(packet["return_binding"]["same_project_writer_chat_forbidden"])
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 0)

        completed = self.submit(runtime, run_id, handoff)
        self.assertEqual(completed["status"], "completed")
        self.assertTrue(completed["candidate_visible"])
        self.assertFalse(completed["raw_draft_visible"])
        self.assertFalse(completed["accepted"])
        self.assertFalse(completed["settled"])
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

    def test_stage_materializer_has_no_database_access_path(self):
        source = inspect.getsource(ProductionRunExecutor.materialize_stage_context).lower()
        self.assertNotIn("sqlite", source)
        self.assertNotIn("open_project", source)
        self.assertNotIn("self.store", source)

    def test_character_simulation_excludes_research_but_keeps_character_knowledge(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        bundle = runtime.prepare_context("PROD", self.start(), service_id="svc", instruction="draft")
        character = runtime.materialize_stage_context(bundle, "character_simulation")
        draft = runtime.materialize_stage_context(bundle, "event_first_raw_draft")
        self.assertIn("character_knowledge", {row["domain"] for row in character["items"]})
        self.assertNotIn("research", {row["domain"] for row in character["items"]})
        self.assertIn("research", {row["domain"] for row in draft["items"]})
        self.assertFalse(character["db_fetch_performed"])

    def test_invalid_selector_id_is_rejected_not_guessed(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime(invalid_selector=True))
        with self.assertRaises(ProductionRunError) as caught:
            runtime.prepare_context("PROD", self.start(), service_id="svc", instruction="draft")
        self.assertEqual(caught.exception.code, "semantic_invalid")

    def test_mutation_after_freeze_blocks_before_stage_worker(self):
        fake = FakeAgentRuntime()
        runtime = ProductionRunExecutor(self.store, fake)
        run_id = self.start()
        runtime.prepare_context("PROD", run_id, service_id="svc", instruction="draft")
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
        runtime.prepare_context("PROD", run_id, service_id="svc", instruction="draft")
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

    def test_explicit_refresh_supersedes_old_bundle_with_new_fingerprint(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start()
        old = runtime.prepare_context("PROD", run_id, service_id="svc", instruction="draft")
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE characters SET agenda=?,updated_at=? WHERE character_id='CHAR-A'", ("changed", now_iso()))
            conn.commit()
        new = runtime.refresh_context(
            "PROD",
            run_id,
            service_id="svc",
            instruction="draft",
            reason="user_requested_refresh",
        )
        self.assertNotEqual(old["bundle_fingerprint"], new["bundle_fingerprint"])
        self.assertNotEqual(old["freeze"]["freeze_fingerprint"], new["freeze"]["freeze_fingerprint"])
        self.assertEqual(new["supersedes_bundle_fingerprint"], old["bundle_fingerprint"])

    def test_mutation_after_handoff_blocks_independent_submission(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start()
        handoff = self.execute_to_handoff(runtime, run_id)
        with self.store.open_project("PROD") as conn:
            conn.execute("UPDATE characters SET agenda=?,updated_at=? WHERE character_id='CHAR-A'", ("post-handoff mutation", now_iso()))
            conn.commit()
        result = peer_result(handoff, "pass")
        blocked = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=handoff["independent_review_request"]["peer_packet"],
            result=result,
            bridge_receipt=project_bridge_receipt(handoff, result),
        )
        self.assertEqual(blocked["status"], "stale_conflict")
        self.assertTrue(blocked["new_context_fingerprint_required"])

    def test_independent_reject_is_not_reviewer_shopped_and_creates_no_candidate(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start()
        handoff = self.execute_to_handoff(runtime, run_id)
        rejected = self.submit(runtime, run_id, handoff, "fail")
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
        first = self.submit(runtime, run_id, handoff)
        calls = len(fake.calls)
        second = self.execute_to_handoff(runtime, run_id)
        self.assertTrue(second["replayed"])
        self.assertEqual(first["candidate"]["candidate_id"], second["candidate"]["candidate_id"])
        self.assertEqual(calls, len(fake.calls))
        with self.store.open_project("PROD") as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates WHERE run_id=?", (run_id,)).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
