"""Deterministic Project learning tests; these fixtures execute no model."""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from learning.feedback_intake import FeedbackIntakeStore
from learning.learning_store import LearningStore, digest
from learning.project_learning import ProjectLearning


def semantic_result(job, judgment):
    return {
        "job_id": job["job_id"], "subject_id": job["subject_id"], "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"], "status": "completed",
        "worker": {"provider": "deterministic_fixture", "model_or_reviewer": "unit-test"},
        "judgment": judgment, "proposals": [], "errors": [],
    }


def interpretation(*, scope="project", action="create", target=None, statement="Dialogue should reflect unequal knowledge."):
    return {
        "capture_decision": "capture", "skip_reason": None, "scope_candidate": scope,
        "dimension": "dialogue", "mechanism": "asymmetric knowledge", "statement": statement,
        "polarity": "negative", "confidence": 0.8, "evidence_source": "human_review",
        "hypothesis_action": action, "target_hypothesis_id": target,
        "contradicts_hypothesis_ids": [], "desired_behavior": [], "avoid_behavior": [],
        "exceptions": [], "applicability": {"scene_types": ["negotiation"]},
    }


def promotion(job, *, verdict="pass", supported_scope="project"):
    return semantic_result(job, {
        "confidence": 0.8, "result": verdict, "supported_scope": supported_scope,
        "report": "Synthetic test judgment, not a live semantic evaluation.",
        "evidence_refs": job["input"]["payload"]["evidence_refs"],
        "unresolved_contradictions": [], "recommended_boundary": {},
    })


class ProjectLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = ProjectLearning(learning_db=self.root / "learning.db", runtime_db=self.root / "runtime.db")

    def observe(self, event_id="FB-1", **changes):
        request = {
            "project_id": "P1", "event_id": event_id, "feedback_text": "This negotiation sounds like both speakers know the same secret.",
            "evidence_kind": "human_review", "candidate_id": "C1", "candidate_fingerprint": "sha256:" + "a" * 64,
            "run_id": "R1", "document_id": "D1", "session_id": "S1", "source_id": "author-1",
        }
        request.update(changes)
        return self.service.observe(**request)

    def capture(self, event_id="FB-1", judgment=None):
        self.observe(event_id)
        out = self.service.execute(project_id="P1", event_id=event_id, run_semantic=lambda job: semantic_result(job, judgment or interpretation()))
        return self.service.get_preference(project_id="P1", hypothesis_id=out["intake"]["hypothesis_id"])

    def review(self, preference, **changes):
        return self.service.execute_activation_review(
            project_id="P1", hypothesis_id=preference["hypothesis_id"], expected_version=preference["version"],
            run_semantic=lambda job: promotion(job, **changes),
        )

    def activate(self, preference, **changes):
        args = {"project_id": "P1", "hypothesis_id": preference["hypothesis_id"], "expected_version": preference["version"], "user_authorized": True, "authorized_by": "author-1", "idempotency_key": "activate-1"}
        args.update(changes)
        return self.service.activate(**args)

    def counts(self):
        with LearningStore(self.service.learning_db).connect() as conn:
            return {table: conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] for table in ("preference_evidence", "preference_hypotheses", "project_preference_receipts")}

    def test_readonly_empty_project_does_not_create_storage(self):
        self.assertEqual([], self.service.list_feedback(project_id="P1")["items"])
        self.assertEqual([], self.service.list_preferences(project_id="P1")["items"])
        projection = self.service.project_context(project_id="P1")
        self.assertEqual([], projection["active_preferences"])
        self.assertEqual(digest({key: value for key, value in projection.items() if key != "projection_fingerprint"}), projection["projection_fingerprint"])
        self.assertEqual([], list(self.root.iterdir()))

    def test_event_retry_preserves_exact_timestamp_binding_and_job(self):
        first = self.observe()
        duplicate = self.observe()
        self.assertEqual(first, duplicate)
        self.assertEqual("awaiting_semantic", first["status"])
        self.assertEqual("C1", first["candidate_id"])
        for change in ({"feedback_text": "different"}, {"run_id": "R2"}, {"candidate_fingerprint": "sha256:" + "b" * 64}, {"project_id": "P2"}, {"source_type": "model_reader"}, {"source_id": "another-author"}):
            with self.assertRaisesRegex(ValueError, "identity conflict"):
                self.observe(**change)

    def test_feedback_source_kind_survives_reopen_and_list_projection(self):
        self.observe("FB-A", source_type="author", source_id="author-1")
        self.observe("FB-H", source_type="human_reader", source_id="reader-1")
        reopened = ProjectLearning(learning_db=self.service.learning_db, runtime_db=self.service.runtime_db)
        items = {item["event_id"]: item for item in reopened.list_feedback(project_id="P1")["items"]}
        self.assertEqual(("author", "author-1"), (items["FB-A"]["source_type"], items["FB-A"]["source_id"]))
        self.assertEqual(("human_reader", "reader-1"), (items["FB-H"]["source_type"], items["FB-H"]["source_id"]))
        self.assertEqual("authorized_human", reopened._event("P1", "FB-H")["source"]["kind"])
        done = reopened.execute(project_id="P1", event_id="FB-H", run_semantic=lambda job: semantic_result(job, interpretation()))
        self.assertEqual("persisted", done["status"])

    def test_model_reader_is_persisted_advisory_but_never_enters_human_learning(self):
        first = self.observe(source_type="model_reader", source_id="reader-agent-1")
        self.assertEqual("advisory", first["status"])
        self.assertTrue(first["advisory_only"])
        self.assertIsNone(first["intake"])
        self.assertIsNone(first["semantic_call"])
        self.assertFalse(self.service.runtime_db.exists())
        self.assertEqual(first, self.observe(source_type="model_reader", source_id="reader-agent-1"))
        for action in (self.service.execute, self.service.resume):
            with self.assertRaisesRegex(ValueError, "advisory"):
                action(project_id="P1", event_id="FB-1", run_semantic=lambda job: self.fail("advisory must not call a model"))
        with self.assertRaisesRegex(ValueError, "advisory"):
            self.service.apply_feedback_result(project_id="P1", event_id="FB-1", result={})
        with LearningStore(self.service.learning_db).connect() as conn:
            for table in ("feedback_intake", "project_learning_calls", "preference_evidence", "preference_hypotheses"):
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])

    def test_model_feedback_cannot_activate_even_with_an_older_passing_review(self):
        preference = self.capture()
        self.review(preference)
        with LearningStore(self.service.learning_db).connect() as conn:
            row = conn.execute("SELECT event_json FROM project_feedback_events WHERE event_id='FB-1'").fetchone()
            event = json.loads(row["event_json"])
            event["source"]["kind"] = "model"
            event["payload"]["source_type"] = "model_reader"
            conn.execute("UPDATE project_feedback_events SET event_json=? WHERE event_id='FB-1'", (json.dumps(event),))
        with self.assertRaisesRegex(ValueError, "advisory"):
            self.activate(preference)
        with self.assertRaisesRegex(ValueError, "advisory"):
            self.service.prepare_activation_review(project_id="P1", hypothesis_id=preference["hypothesis_id"], expected_version=preference["version"])
        self.assertEqual("candidate", self.service.get_preference(project_id="P1", hypothesis_id=preference["hypothesis_id"])["state"])

    def test_feedback_is_processed_once_and_cannot_be_reinterpreted(self):
        self.observe()
        jobs = []
        def run(job):
            jobs.append(job)
            return semantic_result(job, interpretation())
        first = self.service.execute(project_id="P1", event_id="FB-1", run_semantic=run)
        replay = self.service.resume(project_id="P1", event_id="FB-1", run_semantic=run)
        self.assertEqual("persisted", first["status"])
        self.assertFalse(replay["model_execution"])
        self.assertEqual(1, len(jobs))
        self.assertEqual({"preference_evidence": 1, "preference_hypotheses": 1, "project_preference_receipts": 0}, self.counts())
        with self.assertRaisesRegex(ValueError, "identity conflict"):
            self.service.apply_feedback_result(project_id="P1", event_id="FB-1", result=semantic_result(jobs[0], interpretation(statement="Another rule")))

    def test_pending_job_keeps_frozen_index_after_other_feedback_arrives(self):
        first = self.observe()
        self.capture("FB-2")
        duplicate = self.observe()
        self.assertEqual(first["semantic_call"]["job_fingerprint"], duplicate["semantic_call"]["job_fingerprint"])
        captured_jobs = []
        self.service.execute(project_id="P1", event_id="FB-1", run_semantic=lambda job: captured_jobs.append(job) or semantic_result(job, interpretation()))
        self.assertEqual([], captured_jobs[0]["input"]["payload"]["hypothesis_index"])

    def test_unknown_model_call_never_automatically_retries(self):
        self.observe()
        jobs = []
        def uncertain(job):
            jobs.append(job)
            raise TimeoutError("provider may have completed")
        with self.assertRaises(TimeoutError):
            self.service.execute(project_id="P1", event_id="FB-1", run_semantic=uncertain)
        reopened = ProjectLearning(learning_db=self.service.learning_db, runtime_db=self.service.runtime_db)
        out = reopened.resume(project_id="P1", event_id="FB-1", run_semantic=uncertain)
        self.assertEqual("awaiting_external", out["status"])
        self.assertEqual(1, len(jobs))
        done = reopened.apply_feedback_result(project_id="P1", event_id="FB-1", result=semantic_result(jobs[0], interpretation()))
        self.assertEqual("persisted", done["status"])

    def test_skip_does_not_invent_learning_evidence(self):
        self.observe(feedback_text="Continue the next paragraph.")
        out = self.service.execute(project_id="P1", event_id="FB-1", run_semantic=lambda job: semantic_result(job, {"capture_decision": "skip", "skip_reason": "Operational instruction", "confidence": 0.9}))
        self.assertEqual("skipped", out["status"])
        self.assertEqual(0, self.counts()["preference_evidence"])

    def test_cross_project_and_general_scope_are_not_mutated(self):
        self.observe()
        with self.assertRaisesRegex(ValueError, "boundary"):
            self.service.execute(project_id="P1", event_id="FB-1", run_semantic=lambda job: semantic_result(job, interpretation(scope="general_craft")))
        self.assertEqual("blocked", self.service.get_feedback(project_id="P1", event_id="FB-1")["status"])
        self.assertEqual(0, self.counts()["preference_evidence"])
        with self.assertRaisesRegex(ValueError, "unknown"):
            self.service.get_feedback(project_id="P2", event_id="FB-1")

    def test_learning_effects_rollback_together_on_capture_failure(self):
        self.observe()
        with patch.object(LearningStore, "upsert_hypothesis", side_effect=RuntimeError("injected write failure")):
            with self.assertRaises(RuntimeError):
                self.service.execute(project_id="P1", event_id="FB-1", run_semantic=lambda job: semantic_result(job, interpretation()))
        self.assertEqual(0, self.counts()["preference_evidence"])
        self.assertEqual("awaiting_semantic", FeedbackIntakeStore(self.service.learning_db).get("FB-1")["status"])
        done = self.service.resume(project_id="P1", event_id="FB-1", run_semantic=lambda job: self.fail("must reuse stored result"))
        self.assertEqual("persisted", done["status"])

    def test_runtime_receipt_failure_recovers_after_learning_commit(self):
        self.observe()
        with patch("learning.feedback_intake.ControlPlane.consume_once", side_effect=RuntimeError("separate runtime DB unavailable")):
            with self.assertRaises(RuntimeError):
                self.service.execute(project_id="P1", event_id="FB-1", run_semantic=lambda job: semantic_result(job, interpretation()))
        self.assertEqual("persisted", FeedbackIntakeStore(self.service.learning_db).get("FB-1")["status"])
        done = self.service.resume(project_id="P1", event_id="FB-1", run_semantic=lambda job: self.fail("must not call model twice"))
        self.assertEqual("persisted", done["status"])
        self.assertEqual(1, self.counts()["preference_evidence"])

    def test_candidate_needs_real_bound_review_and_explicit_authority(self):
        preference = self.capture()
        with self.assertRaisesRegex(ValueError, "authorization"):
            self.activate(preference, user_authorized=False)
        with self.assertRaisesRegex(ValueError, "promotion review"):
            self.activate(preference)
        self.review(preference)
        receipt = self.activate(preference)["receipt"]
        self.assertEqual("active", receipt["after_state"])
        self.assertEqual("learning_database", receipt["transaction_scope"])
        self.assertFalse(receipt["cross_database_atomic"])
        self.assertTrue(receipt["review_job_fingerprint"].startswith("sha256:"))

    def test_review_rejection_or_narrower_scope_blocks_activation(self):
        preference = self.capture()
        self.review(preference, verdict="fail")
        with self.assertRaisesRegex(ValueError, "does not support"):
            self.activate(preference)
        second = self.capture("FB-2")
        self.review(second, supported_scope="one_off")
        with self.assertRaisesRegex(ValueError, "does not support"):
            self.activate(second, idempotency_key="activate-2")
        self.assertEqual(0, self.counts()["project_preference_receipts"])

    def test_activation_and_receipt_are_atomic_with_cas_and_exact_replay(self):
        preference = self.capture()
        self.review(preference)
        with LearningStore(self.service.learning_db).connect() as conn:
            conn.execute("CREATE TRIGGER prevent_receipt BEFORE INSERT ON project_preference_receipts BEGIN SELECT RAISE(ABORT,'injected receipt failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.activate(preference)
        unchanged = self.service.get_preference(project_id="P1", hypothesis_id=preference["hypothesis_id"])
        self.assertEqual("candidate", unchanged["state"])
        self.assertEqual(1, unchanged["version"])
        with LearningStore(self.service.learning_db).connect() as conn:
            conn.execute("DROP TRIGGER prevent_receipt")
        first = self.activate(preference)
        duplicate = self.activate(preference)
        self.assertEqual(first["receipt"], duplicate["receipt"])
        self.assertTrue(duplicate["replayed"])
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            self.activate(preference, idempotency_key="another-key")
        with self.assertRaisesRegex(ValueError, "idempotency conflict"):
            self.activate(preference, authorized_by="another-author")
        self.assertEqual(1, self.counts()["project_preference_receipts"])

    def test_selected_active_projection_and_deactivation_need_no_model(self):
        preference = self.capture()
        self.review(preference)
        active = self.activate(preference)["receipt"]
        self.assertEqual([], self.service.project_context(project_id="P1")["active_preferences"])
        selected = self.service.project_context(project_id="P1", explicit_intent=[{"statement": "Current request wins"}], selected_hypothesis_ids=[preference["hypothesis_id"]])
        self.assertEqual("current_explicit_request", selected["priority_order"][0])
        self.assertEqual(active["after_version"], selected["active_preferences"][0]["version"])
        self.assertEqual("project", selected["active_preferences"][0]["scope"])
        off = self.service.deactivate(project_id="P1", hypothesis_id=preference["hypothesis_id"], expected_version=active["after_version"], user_authorized=True, authorized_by="author-1", idempotency_key="off-1")
        self.assertIsNone(off["receipt"]["review_job_fingerprint"])
        self.assertEqual("deprecated", off["receipt"]["after_state"])
        with self.assertRaisesRegex(ValueError, "not active"):
            self.service.project_context(project_id="P1", selected_hypothesis_ids=[preference["hypothesis_id"]])
        self.assertEqual(active["after_version"], selected["active_preferences"][0]["version"], "a previously frozen projection is unchanged")

    def test_new_feedback_can_not_rewrite_active_preference_without_approval(self):
        preference = self.capture()
        self.review(preference)
        self.activate(preference)
        updated = self.capture("FB-2", interpretation(action="strengthen", target=preference["hypothesis_id"], statement="Keep each speaker's knowledge distinct during negotiation."))
        self.assertEqual("candidate", updated["state"])
        self.assertGreater(updated["version"], preference["version"])
        self.assertEqual([], self.service.project_context(project_id="P1")["available_active_hypothesis_ids"])
        with self.assertRaisesRegex(ValueError, "promotion review"):
            self.activate(updated, idempotency_key="activate-updated")

    def test_stale_semantic_target_cannot_mutate_new_hypothesis_version(self):
        preference = self.capture()
        self.observe("FB-2")
        self.capture("FB-3", interpretation(action="strengthen", target=preference["hypothesis_id"]))
        with self.assertRaisesRegex(ValueError, "changed since"):
            self.service.execute(project_id="P1", event_id="FB-2", run_semantic=lambda job: semantic_result(job, interpretation(action="strengthen", target=preference["hypothesis_id"])))
        self.assertEqual(2, self.counts()["preference_evidence"])

    def test_parallel_duplicate_activation_has_one_receipt(self):
        preference = self.capture()
        self.review(preference)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.activate(preference), range(2)))
        self.assertEqual(results[0]["receipt"], results[1]["receipt"])
        self.assertEqual({False, True}, {item["replayed"] for item in results})
        self.assertEqual(1, self.counts()["project_preference_receipts"])

    def test_imports_use_installed_packages_not_eval_or_corpus(self):
        repository = Path(__file__).resolve().parents[1]
        source = self.root / "source"
        ignore_generated = shutil.ignore_patterns(
            ".git", ".quillframe", "build", "dist", "node_modules", "*.egg-info",
            "__pycache__", "*.pyc", ".venv", "venv", ".pytest_cache", ".mypy_cache",
            ".ruff_cache", ".astro", ".vite",
        )

        def ignore_source_artifacts(directory, names):
            return set(ignore_generated(directory, names)) | {
                name for name in names if (Path(directory) / name).is_symlink()
            }

        # An existing build/lib can be newer than synchronized source timestamps.
        # Always build from a fresh tree, without following repository symlinks.
        shutil.copytree(repository, source, ignore=ignore_source_artifacts)
        wheels, installed = self.root / "wheels", self.root / "installed"
        build = subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--no-index", "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheels), str(source)],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(0, build.returncode, build.stdout + build.stderr)
        wheel_files = list(wheels.glob("quillframe-*.whl"))
        self.assertEqual(1, len(wheel_files))
        install = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-index", "--no-deps", "--target", str(installed), str(wheel_files[0])],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(0, install.returncode, install.stdout + install.stderr)
        probe = subprocess.run(
            [sys.executable, "-I", "-S", "-c", """
import importlib.resources, json, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
import learning.project_learning
schema = json.loads(importlib.resources.files('learning').joinpath('feedback_intake.schema.json').read_text(encoding='utf-8'))
module = pathlib.Path(learning.project_learning.__file__).resolve()
print(json.dumps({'schema_id': schema['$id'], 'installed': module.is_relative_to(root),
    'sources': schema['$defs']['feedbackObservationPayload']['properties']['source_type']['enum'],
    'forbidden_imports': sorted(name for name in sys.modules if name.split('.')[0] in {'evals', 'corpus'})}))
""", str(installed)], cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(0, probe.returncode, probe.stdout + probe.stderr)
        result = json.loads(probe.stdout)
        self.assertEqual("quillframe_feedback_intake_v1", result["schema_id"])
        self.assertTrue(result["installed"])
        self.assertEqual(["author", "human_reader", "model_reader"], result["sources"])
        self.assertEqual([], result["forbidden_imports"])

    def test_author_model_self_test_uses_explicit_capture_contract(self):
        from learning.author_model import self_test
        self.assertEqual("PASS", self_test(self.root / "author-model-test.db")["author_model_contract"])


if __name__ == "__main__":
    unittest.main()
