from __future__ import annotations

import json
import unittest

from model_runtime.routing import (
    ModelRoute,
    ModelTaskProfile,
    RouteError,
    explicit_fallback,
    preview_route,
)
from production_runtime.workflow import (
    CHAPTER_SCOPE,
    WORKFLOW_STAGES,
    NovelWorkflowEngine,
    WorkflowError,
)
from production_runtime.types import (
    CharacterIntent,
    GenerationPacket,
    SceneIntent,
    TransitionConstraints,
)


FP_A = "sha256:" + "a" * 64
FP_B = "sha256:" + "b" * 64


class NovelWorkflowEngineTests(unittest.TestCase):
    def test_ch001_is_rejected_before_any_event_is_created(self):
        with self.assertRaises(WorkflowError) as blocked:
            NovelWorkflowEngine.start(
                project_id="P",
                run_id="R",
                chapter_id="CH002",
                author_profile="guided",
            )
        self.assertEqual(blocked.exception.code, "chapter_scope_violation")
        self.assertEqual(CHAPTER_SCOPE, "CH001")

    def test_stage_order_is_exact_and_illegal_skip_fails_closed(self):
        engine = NovelWorkflowEngine.start(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            author_profile="guided",
        )
        self.assertEqual(engine.stage, WORKFLOW_STAGES[0])
        first = engine.advance(
            stage=WORKFLOW_STAGES[0],
            evidence={"artifact_fingerprint": FP_A},
        )
        self.assertEqual(first["event_type"], "stage_completed")
        self.assertEqual(engine.stage, WORKFLOW_STAGES[1])
        with self.assertRaises(WorkflowError) as blocked:
            engine.advance(stage=WORKFLOW_STAGES[3], evidence={})
        self.assertEqual(blocked.exception.code, "invalid_stage_transition")

    def test_pause_resume_cancel_are_cursor_bound_and_idempotent(self):
        engine = NovelWorkflowEngine.start(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            author_profile="expert",
        )
        paused = engine.pause(reason="author requested pause", idempotency_key="pause-1")
        self.assertEqual(paused["event_type"], "paused")
        with self.assertRaises(WorkflowError):
            engine.advance(stage=engine.stage, evidence={})
        resumed = engine.resume(
            expected_cursor=engine.cursor,
            idempotency_key="resume-1",
        )
        self.assertEqual(resumed["event_type"], "resumed")
        replay = engine.resume(
            expected_cursor=paused["cursor"],
            idempotency_key="resume-1",
        )
        self.assertEqual(replay, resumed)
        self.assertEqual(engine.cursor, resumed["cursor"])
        with self.assertRaises(WorkflowError) as stale:
            engine.cancel(
                expected_cursor=0,
                idempotency_key="cancel-stale",
                user_authorized=True,
            )
        self.assertEqual(stale.exception.code, "cursor_conflict")
        cancelled = engine.cancel(
            expected_cursor=engine.cursor,
            idempotency_key="cancel-1",
            user_authorized=True,
        )
        self.assertEqual(cancelled["event_type"], "cancelled")
        self.assertEqual(engine.status, "cancelled")

    def test_snapshot_restore_and_event_subscription_are_deterministic(self):
        engine = NovelWorkflowEngine.start(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            author_profile="guided",
        )
        engine.advance(stage=engine.stage, evidence={"artifact_fingerprint": FP_A})
        snapshot = engine.snapshot()
        restored = NovelWorkflowEngine.restore(snapshot)
        self.assertEqual(restored.snapshot(), snapshot)
        batch = restored.events_after(0)
        self.assertEqual(batch["schema"], "quillframe_author_run_event_batch_v1")
        self.assertTrue(all(item["cursor"] > 0 for item in batch["events"]))
        self.assertEqual(batch["next_cursor"], restored.cursor)
        self.assertNotIn("secret", json.dumps(batch).lower())

    def test_candidate_mutation_invalidates_bound_review(self):
        engine = NovelWorkflowEngine.start(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            author_profile="guided",
        )
        while engine.stage != "candidate_freeze":
            engine.advance(stage=engine.stage, evidence={})
        engine.bind_candidate(FP_A)
        engine.advance(stage="candidate_freeze", evidence={})
        engine.advance(stage="pre_independent_qualification", evidence={})
        engine.bind_review(
            candidate_fingerprint=FP_A,
            review_fingerprint=FP_B,
            independent=True,
            result="pass",
        )
        invalidated = engine.replace_candidate(FP_B, reason="targeted repair")
        self.assertEqual(invalidated["invalidated_review_count"], 1)
        self.assertEqual(engine.candidate_fingerprint, FP_B)
        self.assertEqual(engine.active_reviews, [])

    def test_independent_review_is_bound_and_reject_routes_back_to_repair(self):
        engine = NovelWorkflowEngine.start(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            author_profile="guided",
        )
        while engine.stage != "candidate_freeze":
            engine.advance(stage=engine.stage, evidence={})
        engine.bind_candidate(FP_A)
        engine.advance(stage="candidate_freeze", evidence={})
        engine.advance(stage="pre_independent_qualification", evidence={})

        with self.assertRaises(WorkflowError) as missing:
            engine.advance(stage="independent_review", evidence={})
        self.assertEqual(missing.exception.code, "independent_review_required")

        engine.bind_review(
            candidate_fingerprint=FP_A,
            review_fingerprint=FP_B,
            independent=True,
            result="reject",
        )
        with self.assertRaises(WorkflowError) as duplicate:
            engine.bind_review(
                candidate_fingerprint=FP_A,
                review_fingerprint=FP_A,
                independent=True,
                result="pass",
            )
        self.assertEqual(duplicate.exception.code, "independent_attempt_already_bound")
        routed = engine.advance(stage="independent_review", evidence={})
        self.assertEqual(routed["event_type"], "repair_required")
        self.assertEqual(engine.stage, "local_repair")
        self.assertEqual(engine.status, "running")

        engine.replace_candidate(FP_B, reason="independent review repair")
        engine.advance(stage="local_repair", evidence={})
        engine.advance(stage="candidate_freeze", evidence={})
        engine.advance(stage="pre_independent_qualification", evidence={})
        engine.bind_review(
            candidate_fingerprint=FP_B,
            review_fingerprint=FP_A,
            independent=True,
            result="pass",
        )
        engine.advance(stage="independent_review", evidence={})
        self.assertEqual(engine.stage, "human_review")
        self.assertEqual(engine.status, "awaiting_user")

    def test_secret_shaped_event_payload_is_rejected(self):
        engine = NovelWorkflowEngine.start(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            author_profile="guided",
        )
        with self.assertRaises(WorkflowError) as blocked:
            engine.advance(stage=engine.stage, evidence={"nested": {"api_key": "sentinel"}})
        self.assertEqual(blocked.exception.code, "secret_boundary_violation")

    def test_accept_settlement_and_publish_are_three_explicit_actions(self):
        engine = NovelWorkflowEngine.start(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            author_profile="guided",
        )
        while engine.stage != "candidate_freeze":
            engine.advance(stage=engine.stage, evidence={})
        engine.bind_candidate(FP_A)
        engine.advance(stage="candidate_freeze", evidence={})
        engine.advance(stage="pre_independent_qualification", evidence={})
        engine.bind_review(
            candidate_fingerprint=FP_A,
            review_fingerprint=FP_B,
            independent=True,
            result="pass",
        )
        engine.advance(stage="independent_review", evidence={})
        with self.assertRaises(WorkflowError) as blocked:
            engine.accept(
                candidate_fingerprint=FP_A,
                authorized_by="author",
                idempotency_key="accept-no",
                user_authorized=False,
            )
        self.assertEqual(blocked.exception.code, "authorization_required")
        accepted = engine.accept(
            candidate_fingerprint=FP_A,
            authorized_by="author",
            idempotency_key="accept-1",
            user_authorized=True,
        )
        self.assertEqual(accepted["action"], "accept")
        self.assertEqual(engine.stage, "accept")
        settled = engine.settle(
            acceptance_id=accepted["acceptance_id"],
            idempotency_key="settle-1",
            user_authorized=True,
        )
        self.assertEqual(settled["action"], "settlement")
        self.assertEqual(engine.stage, "settlement")
        published = engine.publish(
            settlement_id=settled["settlement_id"],
            idempotency_key="publish-1",
            user_authorized=True,
        )
        self.assertEqual(published["action"], "publish")
        self.assertEqual(engine.status, "completed")


class WorkflowTypeTests(unittest.TestCase):
    def test_generation_packet_is_typed_ch001_and_fingerprint_stable(self):
        scene = SceneIntent(
            project_id="P",
            chapter_id="CH001",
            scene_id="SC001",
            purpose="force a choice",
            desired_change="the promise becomes costly",
            constraints=("preserve POV",),
        )
        character = CharacterIntent(
            project_id="P",
            chapter_id="CH001",
            scene_id="SC001",
            character_id="C1",
            private_goal="hide the cost",
            perceived_state={"promise": "safe"},
            action_candidates=("deflect", "confess"),
        )
        transition = TransitionConstraints(
            project_id="P",
            chapter_id="CH001",
            from_state_fingerprint=FP_A,
            allowed_changes=("promise.status",),
            forbidden_changes=("identity.name",),
        )
        packet_a = GenerationPacket.build(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            context_freeze_fingerprint=FP_B,
            scene_intents=(scene,),
            character_intents=(character,),
            transition_constraints=transition,
            task_profile_id="writer-high",
        )
        packet_b = GenerationPacket.build(
            project_id="P",
            run_id="R",
            chapter_id="CH001",
            context_freeze_fingerprint=FP_B,
            scene_intents=(scene,),
            character_intents=(character,),
            transition_constraints=transition,
            task_profile_id="writer-high",
        )
        self.assertEqual(packet_a.to_dict(), packet_b.to_dict())
        self.assertEqual(packet_a.to_dict()["schema"], "quillframe_generation_packet_v1")

    def test_typed_contracts_reject_ch002(self):
        with self.assertRaises(WorkflowError) as blocked:
            SceneIntent(
                project_id="P",
                chapter_id="CH002",
                scene_id="SC002",
                purpose="out of scope",
                desired_change="none",
                constraints=(),
            )
        self.assertEqual(blocked.exception.code, "chapter_scope_violation")


class ModelRoutingTests(unittest.TestCase):
    def profile(self, *, independent: bool = False) -> ModelTaskProfile:
        return ModelTaskProfile(
            profile_id="writer-high",
            role="independent_reviewer" if independent else "writer",
            required_capabilities=("long_context", "structured_output"),
            context_budget_tokens=12000,
            max_cost_micros=1000,
            quality_floor="high",
            independence="required" if independent else "none",
            privacy="project",
            latency_preference="quality_first",
        )

    def routes(self) -> list[ModelRoute]:
        return [
            ModelRoute(
                route_id="fast",
                capabilities=frozenset({"long_context", "structured_output"}),
                context_limit_tokens=32000,
                estimated_cost_micros=200,
                quality_rank=2,
                privacy_levels=frozenset({"project"}),
                invocation_id="worker-fast",
                independent_eligible=True,
            ),
            ModelRoute(
                route_id="quality",
                capabilities=frozenset({"long_context", "structured_output"}),
                context_limit_tokens=64000,
                estimated_cost_micros=900,
                quality_rank=3,
                privacy_levels=frozenset({"project"}),
                invocation_id="worker-quality",
                independent_eligible=True,
            ),
        ]

    def test_quality_first_route_preview_is_stable_and_non_authoritative(self):
        first = preview_route(
            project_id="P",
            profile=self.profile(),
            routes=self.routes(),
            manager_invocation_id="manager",
        )
        second = preview_route(
            project_id="P",
            profile=self.profile(),
            routes=list(reversed(self.routes())),
            manager_invocation_id="manager",
        )
        self.assertEqual(first, second)
        self.assertEqual(first["selected_route_id"], "quality")
        self.assertFalse(first["fallback"]["used"])
        self.assertFalse(first["authority"])

    def test_budget_capability_and_independence_fail_closed(self):
        same_invocation = ModelRoute(
            route_id="same-session",
            capabilities=frozenset({"long_context", "structured_output"}),
            context_limit_tokens=64000,
            estimated_cost_micros=500,
            quality_rank=3,
            privacy_levels=frozenset({"project"}),
            invocation_id="manager",
            independent_eligible=True,
        )
        with self.assertRaises(RouteError) as blocked:
            preview_route(
                project_id="P",
                profile=self.profile(independent=True),
                routes=[same_invocation],
                manager_invocation_id="manager",
            )
        self.assertEqual(blocked.exception.code, "no_eligible_model_route")

    def test_fallback_is_explicit_and_excludes_failed_route(self):
        original = preview_route(
            project_id="P",
            profile=self.profile(),
            routes=self.routes(),
            manager_invocation_id="manager",
        )
        fallback = explicit_fallback(
            prior_receipt=original,
            failed_route_id="quality",
            reason_code="provider_timeout",
            profile=self.profile(),
            routes=self.routes(),
            manager_invocation_id="manager",
        )
        self.assertEqual(fallback["selected_route_id"], "fast")
        self.assertEqual(
            fallback["fallback"],
            {
                "used": True,
                "from_route_id": "quality",
                "reason_code": "provider_timeout",
            },
        )


if __name__ == "__main__":
    unittest.main()
