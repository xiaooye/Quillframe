from __future__ import annotations

import inspect
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_runtime import AgentJob, AgentResult
from core_operations import CoreOperations
from harness.context_runtime import MANDATORY_PRODUCTION_MECHANISMS, fingerprint
from harness.semantic_workers.independent_invocation_receipt import (
    build_receipt as build_native_receipt,
    fingerprint as native_fingerprint,
    validate_receipt as validate_native_receipt,
)
from persistence.independent_review_repository import IndependentReviewError, IndependentReviewRepository
from persistence.quillframe_sqlite import QuillframeStore, fingerprint_text, now_iso
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

    def submit(self, runtime: ProductionRunExecutor, run_id: str, verdict: str = "pass") -> dict:
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, verdict)
        return runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            bridge_receipt=project_bridge_receipt(packet, result),
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
        packet = frozen_packet(self.store, run_id)
        result = peer_result(packet, "pass")
        blocked = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            bridge_receipt=project_bridge_receipt(packet, result),
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


class NativeIndependentReviewRuntimeTests(unittest.TestCase):
    """Spec 022 Task 1 contracts; host hooks/adapters remain Task 2."""

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
            bridge_receipt=project_bridge_receipt(packet, result),
        )

    def start_native(self, session_id: str = "SES-MANAGER") -> str:
        stamp = now_iso()
        with self.store.open_project("PROD") as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions(session_id,status,version,created_at,updated_at) VALUES(?,?,?,?,?)",
                (session_id, "running", 1, stamp, stamp),
            )
            conn.commit()
        return CoreOperations(self.store).start_author_run(
            "PROD",
            task_mode="DRAFT",
            target_ref="DOC-1",
            payload={"instruction": "draft chapter"},
            session_id=session_id,
        )["run_id"]

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

    def make_released_v9_completed_fixture(
        self,
        runtime: ProductionRunExecutor,
    ) -> tuple[str, dict, dict, dict, dict, str]:
        """Create the completed GitHub-review shape released before native v10.

        Released v9 persisted the exact bridge receipt/result fields but did not
        persist the later submission-evidence fingerprint or native attempt row.
        """
        run_id = self.start_native()
        self.execute_to_handoff(runtime, run_id)
        handoff = frozen_handoff(self.store, run_id)
        packet = handoff["peer_packet"]
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        completed = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=receipt,
        )
        self.assertEqual(completed["status"], "completed")
        with self.store.open_project("PROD") as conn:
            row = conn.execute(
                """SELECT review_id,result_json FROM review_evidence
                WHERE candidate_id=(SELECT candidate_id FROM candidates WHERE run_id=?)
                AND independent=1""",
                (run_id,),
            ).fetchone()
            legacy_review = json.loads(row["result_json"])
            legacy_review.pop("submission_evidence_fingerprint")
            conn.execute(
                "UPDATE review_evidence SET result_json=? WHERE review_id=?",
                (json.dumps(legacy_review, sort_keys=True, separators=(",", ":")), row["review_id"]),
            )
            conn.execute("DELETE FROM independent_review_attempts WHERE run_id=?", (run_id,))
            conn.execute(
                "DELETE FROM runtime_events WHERE run_id=? AND event_kind='production_candidate_ready'",
                (run_id,),
            )
            conn.commit()
        return run_id, handoff, packet, result, receipt, row["review_id"]

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

    def test_clean_install_migrations_use_final_provider_ids_and_processing_fence(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        migrations = ROOT / "persistence" / "migrations" / "project"
        for name in ("001_initial.sql", "002_semantic_context_runtime.sql", "003_native_independent_review.sql"):
            conn.executescript((migrations / name).read_text(encoding="utf-8"))
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
            self.fail(f"migration 003 rejected the final native provider ID: {exc}")
        conn.execute(
            "INSERT INTO independent_review_lifecycle_events(event_id,lease_id,run_id,event_kind,event_fingerprint,payload_json,created_at) VALUES('EVENT','LEASE','RUN','prepared','sha256:event','{\"provider\":\"codex_native_subagent\"}',?)",
            (stamp,),
        )
        conn.executescript((migrations / "004_independent_review_processing_lease.sql").read_text(encoding="utf-8"))
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

    def test_released_v9_duplicate_pass_candidates_migrate_without_rewriting_history(self):
        with tempfile.TemporaryDirectory() as legacy_root:
            legacy_store = QuillframeStore(Path(legacy_root))
            legacy_store.ensure_layout()
            location = legacy_store.location("PROD")
            location.directory.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(location.database)
            migrations = ROOT / "persistence" / "migrations" / "project"
            migration_paths = [migrations / "001_initial.sql", migrations / "002_semantic_context_runtime.sql"]
            for path in migration_paths:
                conn.executescript(path.read_text(encoding="utf-8"))
            conn.execute(
                """CREATE TABLE schema_migrations (
                scope TEXT NOT NULL,version INTEGER NOT NULL,name TEXT NOT NULL,checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL,PRIMARY KEY(scope,version))"""
            )
            stamp = "2026-08-19T00:00:00+00:00"
            for path in migration_paths:
                conn.execute(
                    "INSERT INTO schema_migrations(scope,version,name,checksum,applied_at) VALUES('project',?,?,?,?)",
                    (
                        int(path.name.split("_", 1)[0]),
                        path.name,
                        fingerprint_text(path.read_text(encoding="utf-8")),
                        stamp,
                    ),
                )
            conn.execute(
                "INSERT INTO project_identity(project_id,title,language,project_schema_version,created_at,updated_at) VALUES('PROD','Fixture','en',1,?,?)",
                (stamp, stamp),
            )
            conn.execute(
                "INSERT INTO sessions(session_id,status,version,created_at,updated_at) VALUES('SES','completed',1,?,?)",
                (stamp, stamp),
            )
            conn.execute(
                "INSERT INTO runs(run_id,session_id,task_mode,status,request_fingerprint,created_at,updated_at) VALUES('RUN','SES','DRAFT','completed','sha256:req',?,?)",
                (stamp, stamp),
            )
            candidate_values = (
                None,
                None,
                "RUN",
                "DRAFT",
                "draft",
                "review_draft",
                "PASS",
                stamp,
            )
            conn.execute(
                """INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at)
                VALUES('CAND-A',?,?,?,?,?,?,'sha256:candidate-a',?,?)""",
                candidate_values,
            )
            conn.execute(
                """INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at)
                VALUES('CAND-B',?,?,?,?,?,?,'sha256:candidate-b',?,?)""",
                candidate_values,
            )
            conn.commit()
            conn.close()

            with legacy_store.open_project("PROD") as upgraded:
                self.assertEqual(
                    upgraded.execute(
                        "SELECT COUNT(*) FROM candidates WHERE run_id='RUN' AND user_visible_gate='PASS'"
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(upgraded.execute("PRAGMA foreign_key_check").fetchall(), [])
                with self.assertRaises(sqlite3.IntegrityError):
                    upgraded.execute(
                        """INSERT INTO candidates(candidate_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at)
                        VALUES('CAND-C','RUN','DRAFT','draft','review_draft','sha256:candidate-c','PASS',?)""",
                        (stamp,),
                    )
                upgraded.execute(
                    """INSERT INTO candidates(candidate_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at)
                    VALUES('CAND-U1','RUN-UPDATE','DRAFT','draft','review_draft','sha256:update-a','FAIL',?)""",
                    (stamp,),
                )
                upgraded.execute(
                    """INSERT INTO candidates(candidate_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at)
                    VALUES('CAND-U2','RUN-UPDATE','DRAFT','draft','review_draft','sha256:update-b','FAIL',?)""",
                    (stamp,),
                )
                upgraded.execute("UPDATE candidates SET user_visible_gate='PASS' WHERE candidate_id='CAND-U1'")
                with self.assertRaises(sqlite3.IntegrityError):
                    upgraded.execute("UPDATE candidates SET user_visible_gate='PASS' WHERE candidate_id='CAND-U2'")

    def test_stale_owner_is_fenced_at_receipt_write_after_identical_takeover(self):
        self.assert_stale_owner_fenced_at_effect_boundary("receipt")

    def test_stale_owner_is_fenced_at_candidate_write_after_identical_takeover(self):
        self.assert_stale_owner_fenced_at_effect_boundary("candidate")

    def test_native_dispatch_withholds_packet_and_claim_is_one_time_with_distinct_session(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff, dispatch = self.prepare_native(runtime, run_id, provider="codex")

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

        claim = self.claim_native(runtime, provider="codex")
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

    def test_active_native_lease_blocks_legacy_but_infrastructure_failure_allows_takeover(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff, _ = self.prepare_native(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        legacy = peer_result(packet, "pass")
        legacy_receipt = project_bridge_receipt(packet, legacy)
        with self.assertRaises(ProductionRunError) as blocked:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=legacy,
                bridge_receipt=legacy_receipt,
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
            result=legacy,
            independence_receipt=legacy_receipt,
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
        legacy = peer_result(packet, "pass")
        with self.assertRaises(ProductionRunError) as consumed:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=legacy,
                bridge_receipt=project_bridge_receipt(packet, legacy),
            )
        self.assertEqual(consumed.exception.code, "independent_attempt_consumed")

    def test_legacy_pass_consumes_attempt_and_blocks_native_dispatch(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id = self.start_native()
        handoff = self.execute_to_handoff(runtime, run_id)
        completed = self.submit(runtime, run_id)
        self.assertEqual(completed["status"], "completed")
        if not hasattr(runtime, "prepare_independent_dispatch"):
            self.fail("ProductionRunExecutor.prepare_independent_dispatch is required")
        with self.assertRaises(ProductionRunError) as consumed:
            runtime.prepare_independent_dispatch(
                "PROD", run_id, provider="claude", parent_session_id="SES-MANAGER"
            )
        self.assertEqual(consumed.exception.code, "independent_attempt_consumed")

    def test_pre_v10_handoff_backfills_exact_packet_bytes_once_without_renonce(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        if not hasattr(runtime, "_latest_independent_handoff"):
            self.fail("runtime requires deterministic pre-v10 independent handoff backfill")
        run_id = self.start_native()
        self.execute_to_handoff(runtime, run_id)
        packet = frozen_packet(self.store, run_id)
        expected_bytes = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        nonce = packet["relay_nonce"]
        with self.store.open_project("PROD") as conn:
            row = conn.execute(
                "SELECT checkpoint_id,state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_independent_handoff' ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            legacy = json.loads(row["state_json"])
            legacy.pop("peer_packet_bytes")
            conn.execute(
                "UPDATE checkpoints SET state_json=? WHERE checkpoint_id=?",
                (json.dumps(legacy, sort_keys=True, separators=(",", ":")), row["checkpoint_id"]),
            )
            conn.commit()
        result = peer_result(packet, "pass")
        receipt = project_bridge_receipt(packet, result)
        completed = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=receipt,
        )
        replay = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=receipt,
        )
        self.assertEqual(completed, replay)
        with self.store.open_project("PROD") as conn:
            rows = conn.execute(
                "SELECT state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_independent_handoff' ORDER BY created_at,rowid",
                (run_id,),
            ).fetchall()
        self.assertEqual(len(rows), 2)
        upgraded = json.loads(rows[-1]["state_json"])
        self.assertEqual(upgraded["peer_packet_bytes"], expected_bytes)
        self.assertEqual(upgraded["peer_packet"]["relay_nonce"], nonce)

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

    def test_actual_project_identity_drift_blocks_legacy_before_attempt_or_release(self):
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

    def test_released_v9_completed_github_replay_binds_exact_evidence_once(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id, handoff, packet, result, receipt, review_id = self.make_released_v9_completed_fixture(runtime)
        expected_submission_fingerprint = fingerprint(
            {
                "packet_bytes": handoff["peer_packet_bytes"],
                "result": result,
                "independence_receipt": receipt,
            }
        )
        with self.store.open_project("PROD") as conn:
            before = json.loads(
                conn.execute("SELECT result_json FROM review_evidence WHERE review_id=?", (review_id,)).fetchone()[0]
            )
            self.assertNotIn("submission_evidence_fingerprint", before)
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM runtime_events WHERE run_id=? AND event_kind='production_candidate_ready'",
                    (run_id,),
                ).fetchone()[0],
                0,
            )

        first = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=receipt,
        )
        second = runtime.submit_independent(
            "PROD",
            run_id,
            peer_packet=packet,
            result=result,
            independence_receipt=receipt,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "completed")
        self.assertTrue(first["replayed"])
        with self.store.open_project("PROD") as conn:
            after = json.loads(
                conn.execute("SELECT result_json FROM review_evidence WHERE review_id=?", (review_id,)).fetchone()[0]
            )
            attempt = conn.execute(
                "SELECT status,terminal_evidence_fingerprint FROM independent_review_attempts WHERE run_id=?",
                (run_id,),
            ).fetchone()
            ready_events = conn.execute(
                "SELECT COUNT(*) FROM runtime_events WHERE run_id=? AND event_kind='production_candidate_ready'",
                (run_id,),
            ).fetchone()[0]
        self.assertEqual(after, {**before, "submission_evidence_fingerprint": expected_submission_fingerprint})
        self.assertEqual(dict(attempt), {
            "status": "terminal",
            "terminal_evidence_fingerprint": expected_submission_fingerprint,
        })
        self.assertEqual(ready_events, 1)

    def test_released_v9_completed_github_replay_rejects_tampered_evidence_without_binding(self):
        for tamper in ("result", "receipt", "candidate"):
            with self.subTest(tamper=tamper):
                runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
                run_id, _handoff, packet, result, receipt, review_id = self.make_released_v9_completed_fixture(runtime)
                submitted_result = json.loads(json.dumps(result))
                submitted_receipt = json.loads(json.dumps(receipt))
                if tamper == "result":
                    submitted_result["judgment"]["report"] = "tampered historical replay"
                    submitted_receipt = project_bridge_receipt(packet, submitted_result)
                elif tamper == "receipt":
                    submitted_receipt["issue_number"] = 2
                else:
                    with self.store.open_project("PROD") as conn:
                        conn.execute(
                            "UPDATE candidates SET content_fingerprint='sha256:tampered-candidate' WHERE run_id=?",
                            (run_id,),
                        )
                        conn.commit()
                with self.assertRaises(ProductionRunError) as mismatch:
                    runtime.submit_independent(
                        "PROD",
                        run_id,
                        peer_packet=packet,
                        result=submitted_result,
                        independence_receipt=submitted_receipt,
                    )
                self.assertEqual(mismatch.exception.code, "independent_recovery_evidence_mismatch")
                with self.store.open_project("PROD") as conn:
                    persisted = json.loads(
                        conn.execute("SELECT result_json FROM review_evidence WHERE review_id=?", (review_id,)).fetchone()[0]
                    )
                    ready_events = conn.execute(
                        "SELECT COUNT(*) FROM runtime_events WHERE run_id=? AND event_kind='production_candidate_ready'",
                        (run_id,),
                    ).fetchone()[0]
                self.assertNotIn("submission_evidence_fingerprint", persisted)
                self.assertEqual(ready_events, 0)

    def test_released_v9_completed_replay_fails_closed_on_ambiguous_candidates(self):
        runtime = ProductionRunExecutor(self.store, FakeAgentRuntime())
        run_id, _handoff, packet, result, receipt, review_id = self.make_released_v9_completed_fixture(runtime)
        with self.store.open_project("PROD") as conn:
            original = conn.execute("SELECT * FROM candidates WHERE run_id=?", (run_id,)).fetchone()
            conn.execute("DROP INDEX IF EXISTS production_candidate_one_per_run_idx")
            conn.execute("DROP TRIGGER IF EXISTS production_candidate_one_pass_per_run_insert")
            conn.execute(
                """INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,
                content_fingerprint,user_visible_gate,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    "cand_ambiguous",
                    original["document_id"],
                    original["revision_id"],
                    run_id,
                    original["task_mode"],
                    original["candidate_kind"],
                    original["status"],
                    original["content_fingerprint"],
                    original["user_visible_gate"],
                    original["created_at"],
                ),
            )
            conn.commit()
        with self.assertRaises(ProductionRunError) as ambiguous:
            runtime.submit_independent(
                "PROD",
                run_id,
                peer_packet=packet,
                result=result,
                independence_receipt=receipt,
            )
        self.assertEqual(ambiguous.exception.code, "independent_recovery_evidence_mismatch")
        with self.store.open_project("PROD") as conn:
            persisted = json.loads(
                conn.execute("SELECT result_json FROM review_evidence WHERE review_id=?", (review_id,)).fetchone()[0]
            )
        self.assertNotIn("submission_evidence_fingerprint", persisted)

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
