"""Deterministic tests for one-fresh-chapter author review; no literary verdicts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evals.craft_chapter_review import (
    advance_sequence,
    bind_visible_chapter,
    chapter_observation,
    prepare_review,
    save_new,
    start_sequence,
    validate_artifact,
    validate_plan,
    validate_sequence,
)
from harness.context_runtime import fingerprint
from production_runtime.craft_guidance import freeze_craft_library
from quality.production_release import aggregate


def chapter_case(case_id="fresh-market-night"):
    return {
        "schema": "quillframe_craft_chapter_case_v1",
        "case_id": case_id,
        "unit_kind": "chapter",
        "title": "夜市封摊前",
        "generation_request": "写一个可独立阅读的中文网络小说章节；只使用给定事实和计划。",
        "reader_context": {
            "genre_profile": "现代都市成长",
            "platform_profile": "中文网络连载，强调人物现场与行动后果",
            "chapter_position": "主角第一次独立处理摊位纠纷",
            "reader_grip": "high",
        },
        "planning": {
            "overall_outline": "主角试着保住家里的夜市摊位。",
            "chapter_outline": "封摊前发现公共冰柜里的货被挪走，必须当场查清并保住明日位置。",
            "scene_details": "摊主们各有急事；主角的第一次办法会碰到另一个摊主的现实利益。",
        },
        "writer_safe_facts": [
            "主角今天第一次独自看摊。",
            "市场十点统一断电封门。",
            "公共冰柜按摊位编号分格。",
        ],
        "pov_boundary": {"person": "third_limited", "viewpoint": "主角", "private_state_access": ["主角"]},
        "provenance": {
            "authorship": "original_evaluation_case",
            "fresh_for_reviewer": True,
            "derived_from_rejected_prose": False,
            "consumer_content_committed_to_framework": False,
        },
    }


def text_fingerprint(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def visible_projection(text="这是单篇测试章节。人物在封门前处理了冰柜纠纷。"):
    candidate = text_fingerprint(text)
    release = aggregate({
        "production_readiness": {
            "schema": "quillframe_production_readiness_v1",
            "candidate_fingerprint": candidate,
            "ready_for_user_visible_review": True,
        },
        "structural_policy": {"required_receipts": []},
        "structural_receipts": [],
    })
    return {
        "schema": "quillframe_user_visible_candidate_v1",
        "project_id": "SYNTHETIC",
        "candidate_id": "CANDIDATE-1",
        "candidate_fingerprint": candidate,
        "document_id": "DOC-1",
        "revision_id": "REV-1",
        "content": text,
        "authority_class": "review",
        "production_release": release,
        "content_access": "production_release_only",
        "accepted": False,
        "settled": False,
        "private_reasoning_exposed": False,
        "authority": False,
        "canon_authority": False,
    }


def stage_receipt(mechanism, bundle="sha256:" + "b" * 64):
    receipt = {
        "mechanism": mechanism,
        "context_bundle_fingerprint": bundle,
        "judgment": {"status": "pass", "summary": "Synthetic stage pass."},
    }
    receipt["stage_result_fingerprint"] = fingerprint(receipt)
    return receipt


class CraftChapterReviewTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = freeze_craft_library("outline_driven")
        self.state = start_sequence("synthetic-sequence", created_at="2026-08-29T00:00:00+00:00")
        self.settings = {"service_id": "fixture-service", "model_id": "fixture-model", "reasoning_effort": "test-only"}
        self.plan = prepare_review(
            self.state, chapter_case(), settings=self.settings, craft_snapshot=self.snapshot,
            created_at="2026-08-29T00:01:00+00:00",
        )
        self.execution = {
            "run_id": "fixture-run",
            "task_mode": "DRAFT",
            "craft_guidance_mode": "outline_driven",
            "craft_snapshot_fingerprint": self.snapshot["snapshot_fingerprint"],
            "stage_receipts": [stage_receipt("character_simulation"), stage_receipt("reader_pressure")],
            "candidate_visible_operation": "candidate.visible.get",
        }
        self.artifact = bind_visible_chapter(
            self.plan, visible_projection(), execution_evidence=self.execution,
            synthetic_test_only=True, created_at="2026-08-29T00:02:00+00:00",
        )

    def test_preparation_freezes_one_candidate_and_dispatches_nothing(self):
        with patch("production_runtime.runtime.ProductionRunExecutor.execute",
                   side_effect=AssertionError("preparation cannot execute production")):
            plan = prepare_review(
                self.state, chapter_case(), settings=self.settings, craft_snapshot=self.snapshot,
                created_at="2026-08-29T00:01:00+00:00",
            )
        validate_plan(plan)
        self.assertEqual(1, plan["review_contract"]["visible_chapter_count"])
        self.assertFalse(plan["review_contract"]["comparative_review"])
        self.assertFalse(plan["review_contract"]["baseline_companion"])
        self.assertTrue(plan["required_execution"]["full_production_runtime"])
        self.assertTrue(plan["required_execution"]["character_simulation_required"])
        self.assertTrue(plan["required_execution"]["reader_pressure_required"])
        self.assertFalse(plan["model_execution"])
        self.assertNotIn("arms", plan)
        self.assertNotIn("order_seed", plan)

    def test_public_artifact_contains_one_released_chapter_and_no_private_case_material(self):
        validate_artifact(self.artifact)
        self.assertEqual("这是单篇测试章节。人物在封门前处理了冰柜纠纷。", self.artifact["chapter"])
        self.assertEqual(self.artifact["candidate_fingerprint"], text_fingerprint(self.artifact["chapter"]))
        encoded = json.dumps(self.artifact, ensure_ascii=False)
        for excluded in ("planning", "writer_safe_facts", "pov_boundary", "craft_snapshot", "settings", "run_id"):
            self.assertNotIn(excluded, encoded)
        self.assertNotIn("A", self.artifact)
        self.assertNotIn("B", self.artifact)

    def test_release_and_full_pipeline_bindings_fail_closed(self):
        changed = visible_projection()
        changed["content"] += "篡改"
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            bind_visible_chapter(self.plan, changed, execution_evidence=self.execution)
        for mechanism in ("character_simulation", "reader_pressure"):
            evidence = deepcopy(self.execution)
            evidence["stage_receipts"] = [row for row in evidence["stage_receipts"] if row["mechanism"] != mechanism]
            with self.subTest(mechanism=mechanism), self.assertRaisesRegex(ValueError, "receipts required"):
                bind_visible_chapter(self.plan, visible_projection(), execution_evidence=evidence)
        evidence = deepcopy(self.execution)
        evidence["craft_snapshot_fingerprint"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "full production"):
            bind_visible_chapter(self.plan, visible_projection(), execution_evidence=evidence)

    def test_feedback_is_single_chapter_evidence_not_authority_or_promotion(self):
        for outcome in ("continue", "revise", "reject", "insufficient_evidence"):
            observation = chapter_observation(
                self.artifact, outcome=outcome, reason="Synthetic author-shaped feedback.",
                reviewer_ref="synthetic-reviewer", created_at="2026-08-29T00:03:00+00:00",
            )
            self.assertEqual(outcome, observation["outcome"])
            self.assertFalse(observation["review_eligible"])
            self.assertFalse(observation["authority"])
            self.assertFalse(observation["taste_activation"])
            self.assertFalse(observation["framework_promotion"])
            self.assertEqual(outcome in {"revise", "reject"},
                             observation["requires_candidate_change_before_next_generation"])

    def test_next_chapter_requires_feedback_fresh_case_and_changed_rejected_candidate(self):
        observation = chapter_observation(
            self.artifact, outcome="reject", reason="Synthetic rejection.", reviewer_ref="synthetic-reviewer",
            created_at="2026-08-29T00:03:00+00:00",
        )
        next_state = advance_sequence(
            self.state, self.plan, self.artifact, observation,
            created_at="2026-08-29T00:04:00+00:00",
        )
        validate_sequence(next_state)
        self.assertEqual(2, next_state["next_iteration"])
        self.assertEqual(self.snapshot["snapshot_fingerprint"], next_state["blocked_craft_snapshot_fingerprint"])
        with self.assertRaisesRegex(ValueError, "rejected craft snapshot"):
            prepare_review(next_state, chapter_case("another-fresh-case"), settings=self.settings,
                           craft_snapshot=self.snapshot)

        changed_snapshot = deepcopy(self.snapshot)
        changed_snapshot["registry_version"] = "synthetic-next"
        changed_snapshot["snapshot_fingerprint"] = fingerprint({
            key: value for key, value in changed_snapshot.items() if key != "snapshot_fingerprint"
        })
        next_plan = prepare_review(
            next_state, chapter_case("another-fresh-case"), settings=self.settings,
            craft_snapshot=changed_snapshot, created_at="2026-08-29T00:05:00+00:00",
        )
        self.assertEqual(2, next_plan["iteration"])
        with self.assertRaisesRegex(ValueError, "already reviewed"):
            prepare_review(next_state, chapter_case(), settings=self.settings, craft_snapshot=changed_snapshot)

    def test_mismatched_feedback_cannot_advance_sequence(self):
        observation = chapter_observation(
            self.artifact, outcome="continue", reason="Synthetic continuation.", reviewer_ref="synthetic-reviewer",
            created_at="2026-08-29T00:03:00+00:00",
        )
        changed = deepcopy(observation)
        changed["candidate_fingerprint"] = "sha256:" + "f" * 64
        changed["observation_fingerprint"] = fingerprint({
            key: value for key, value in changed.items() if key != "observation_fingerprint"
        })
        with self.assertRaisesRegex(ValueError, "another chapter"):
            advance_sequence(self.state, self.plan, self.artifact, changed)

    def test_append_only_storage_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "review" / "artifact.json"
            save_new(path, self.artifact)
            self.assertEqual(self.artifact, json.loads(path.read_text(encoding="utf-8")))
            with self.assertRaises(FileExistsError):
                save_new(path, self.artifact)


if __name__ == "__main__":
    unittest.main()
