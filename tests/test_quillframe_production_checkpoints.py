from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from agent_runtime import AgentBudget, AgentJob, AgentResult
from core_operations import CoreOperations
from harness.context_runtime import fingerprint
from persistence.production_stage_repository import (
    EXECUTION_LEASE_SECONDS,
    ProductionStageError,
    ProductionStageRepository,
)
from persistence.quillframe_sqlite import QuillframeStore
from production_runtime.coordinator import ProductionCoordinator
from production_runtime.build_identity import BUILD_ROOTS, ROOT_FILES, framework_build_identity
from production_runtime.runtime import ProductionRunExecutor


class Clock:
    def __init__(self) -> None:
        self.value = 1_000.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class ProductionCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = QuillframeStore(Path(self.temp.name))
        self.store.create_project("CHECKPOINT", "Checkpoint Fixture")
        with self.store.open_project("CHECKPOINT") as connection:
            connection.execute(
                "INSERT INTO story_nodes(node_id,kind,ordinal,title,metadata_json) "
                "VALUES('CH001','chapter',1,'Chapter','{}')"
            )
            connection.commit()
        self.store.create_document(
            "CHECKPOINT", "DOC-1", "Chapter", story_node_id="CH001"
        )
        self.store.save_revision(
            "CHECKPOINT", "DOC-1", "seed", expected_parent_revision_id=None, source="test"
        )
        self.run_id = CoreOperations(self.store).start_author_run(
            "CHECKPOINT",
            task_mode="DRAFT",
            target_ref="DOC-1",
            payload={"instruction": "fixture", "chapter_id": "CH001"},
        )["run_id"]
        self.clock = Clock()
        self.repository = ProductionStageRepository(
            self.store, clock=self.clock, lease_seconds=20
        )
        self.request = {
            "max_model_calls": 8,
            "run_cost_budget": 100,
            "framework_build": {
                "schema": "quillframe_framework_build_identity_v1",
                "build_fingerprint": fingerprint("build-fixture"),
            },
        }
        self.owner = self.repository.acquire(
            "CHECKPOINT", self.run_id, self.request
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def job(self, stage: str) -> AgentJob:
        return AgentJob(
            job_id="JOB-" + stage,
            session_id="SESSION-CHECKPOINT",
            run_id=self.run_id,
            task_mode="DRAFT",
            runtime_role=stage,
            service_id="SERVICE-CHECKPOINT",
            instruction="Execute exact fixture stage " + stage,
            context=[{"stage": stage, "upstream_fingerprint": fingerprint(stage)}],
            required_model_capabilities={"text"},
            budgets=AgentBudget(
                max_steps=1,
                max_model_requests=1,
                max_tool_calls=1,
                max_parallel_tool_calls=1,
                model_context_limit=10_000,
                max_output_tokens=100,
                run_cost_budget=100,
                max_elapsed_ms=100,
            ),
            idempotency_key=self.run_id + ":" + stage,
        )

    @staticmethod
    def result(job: AgentJob, *, cost: int = 0) -> AgentResult:
        receipt = {
            "schema": "quillframe_model_cost_receipt_v1",
            "status": "provider_confirmed",
            "model_requests": 1,
            "cost_micros": cost,
            "request_receipts": [{
                "request_ordinal": 1,
                "response_id_fingerprint": fingerprint("checkpoint-response"),
                "usage_fingerprint": fingerprint({"cost_micros": cost}),
                "cost_reported": True,
                "cost_micros": cost,
            }],
        }
        receipt["receipt_fingerprint"] = fingerprint(receipt)
        return AgentResult(
            job_id=job.job_id,
            session_id=job.session_id,
            run_id=job.run_id,
            status="completed",
            model_service_id=job.service_id,
            model_id="MODEL-CHECKPOINT",
            model_version_fingerprint=fingerprint("model-version"),
            protocol="fixture",
            input_fingerprint=job.input_fingerprint,
            final_text='{"status":"pass"}',
            steps=1,
            model_requests=1,
            usage={"cost_micros": cost, "billing_receipt": receipt},
        )

    def dispatch_and_confirm(self, stage: str, *, cost: int = 0) -> tuple[AgentJob, dict]:
        job = self.job(stage)
        intent = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key=stage, job=job.to_dict(),
        )
        self.repository.confirm_call(
            "CHECKPOINT", self.run_id, self.owner,
            call_id=intent["call_id"], result=self.result(job, cost=cost).to_dict(),
        )
        return job, intent

    def test_exact_valid_response_survives_deadline_and_lease_expiry_without_takeover(self) -> None:
        job = self.job("late-stage")
        intent = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="late-stage", job=job.to_dict(),
        )
        self.clock.advance(25)
        self.repository.confirm_call(
            "CHECKPOINT", self.run_id, self.owner,
            call_id=intent["call_id"], result=self.result(job).to_dict(),
        )
        projection = self.repository.projection("CHECKPOINT", self.run_id)
        self.assertEqual("confirmed", projection["calls"][0]["state"])

    def test_confirmed_replay_requires_intact_node_checkpoint_and_semantic_receipt(self) -> None:
        job, intent = self.dispatch_and_confirm("validated-stage")
        checkpoint = self.repository.confirm_node_validation(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="validated-stage",
            input_fingerprint=job.input_fingerprint,
            validation_kind="fixture-semantic-contract",
            validation_fingerprint=fingerprint({"status": "pass"}),
        )
        self.assertEqual(
            "semantic_validation_confirmed",
            checkpoint["validation_receipt"]["status"],
        )
        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        self.owner = self.repository.acquire("CHECKPOINT", self.run_id, self.request)
        replay = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="validated-stage", job=job.to_dict(),
        )
        self.assertTrue(replay["replayed"])
        with self.store.open_project("CHECKPOINT") as connection:
            connection.execute(
                "DELETE FROM checkpoints WHERE checkpoint_id=?",
                ("node:" + intent["call_id"],),
            )
            connection.commit()
        with self.assertRaises(ProductionStageError) as missing:
            self.repository.begin_call(
                "CHECKPOINT", self.run_id, self.owner,
                stage_key="validated-stage", job=job.to_dict(),
            )
        self.assertEqual("node_checkpoint_missing", missing.exception.code)

    def test_wake_acknowledges_only_events_captured_before_attempt(self) -> None:
        self.dispatch_and_confirm("first")
        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        captured = self.repository.ready_runs("CHECKPOINT")
        self.assertEqual(1, len(captured))
        self.owner = self.repository.acquire("CHECKPOINT", self.run_id, self.request)
        self.dispatch_and_confirm("second")
        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        self.repository.consume_wakes(
            "CHECKPOINT", self.run_id,
            wake_event_ids=captured[0]["wake_event_ids"],
        )
        remaining = self.repository.ready_runs("CHECKPOINT")
        self.assertEqual(1, len(remaining))
        self.assertEqual(1, len(remaining[0]["wake_event_ids"]))
        self.assertNotEqual(
            captured[0]["wake_event_ids"][0], remaining[0]["wake_event_ids"][0]
        )

    def test_response_crossing_cost_budget_stays_confirmed_and_blocks_next_dispatch(self) -> None:
        first, _ = self.dispatch_and_confirm("expensive", cost=150)
        replay = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="expensive", job=first.to_dict(),
        )
        self.assertTrue(replay["replayed"])
        with self.assertRaises(ProductionStageError) as exhausted:
            self.repository.begin_call(
                "CHECKPOINT", self.run_id, self.owner,
                stage_key="next", job=self.job("next").to_dict(),
            )
        self.assertEqual("run_cost_budget_exhausted", exhausted.exception.code)
        self.assertEqual(
            1, self.repository.projection("CHECKPOINT", self.run_id)["confirmed_call_count"]
        )

    def test_missing_provider_cost_preserves_result_then_requires_exact_reconciliation(self) -> None:
        job = self.job("unpriced")
        intent = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="unpriced", job=job.to_dict(),
        )
        result = self.result(job).to_dict()
        result["usage"] = {"input_tokens": 20, "output_tokens": 5}
        self.repository.confirm_call(
            "CHECKPOINT", self.run_id, self.owner,
            call_id=intent["call_id"], result=result,
        )
        projection = self.repository.projection("CHECKPOINT", self.run_id)
        self.assertEqual([intent["call_id"]], projection["billing_reconciliation_call_ids"])
        replay = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="unpriced", job=job.to_dict(),
        )
        self.assertTrue(replay["replayed"])
        with self.assertRaises(ProductionStageError) as blocked:
            self.repository.begin_call(
                "CHECKPOINT", self.run_id, self.owner,
                stage_key="next", job=self.job("next").to_dict(),
            )
        self.assertEqual("billing_reconciliation_required", blocked.exception.code)

        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        result_fingerprint = self.repository.projection(
            "CHECKPOINT", self.run_id
        )["calls"][0]["result_fingerprint"]
        receipt = self.repository.reconcile_billing_receipt(
            "CHECKPOINT",
            self.run_id,
            call_id=intent["call_id"],
            expected_result_fingerprint=result_fingerprint,
            cost_micros=12,
            evidence_ref="provider-ledger:fixture-entry",
            evidence_fingerprint=fingerprint({"provider-ledger": "fixture-entry", "cost": 12}),
        )
        self.assertEqual("authorized_reconciliation", receipt["receipt_source"])
        after = self.repository.projection("CHECKPOINT", self.run_id)
        self.assertEqual([], after["billing_reconciliation_call_ids"])
        self.assertEqual(12, after["observed_cost_micros"])
        self.owner = self.repository.acquire("CHECKPOINT", self.run_id, self.request)
        next_intent = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="next", job=self.job("next").to_dict(),
        )
        self.assertFalse(next_intent["replayed"])

    def test_invalid_provider_billing_shapes_require_reconciliation(self) -> None:
        base = self.result(self.job("billing-shape"), cost=7).to_dict()
        mutations = []
        for bad_cost in (-1, True, 0.9, 2**63):
            value = json.loads(json.dumps(base))
            value["usage"]["cost_micros"] = bad_cost
            value["usage"]["billing_receipt"]["cost_micros"] = bad_cost
            value["usage"]["billing_receipt"]["request_receipts"][0]["cost_micros"] = bad_cost
            mutations.append(value)
        missing_response = json.loads(json.dumps(base))
        missing_response["usage"]["billing_receipt"]["request_receipts"][0][
            "response_id_fingerprint"
        ] = None
        mutations.append(missing_response)
        duplicate_ordinal = json.loads(json.dumps(base))
        duplicate_ordinal["model_requests"] = 2
        duplicate_ordinal["usage"]["cost_micros"] = 14
        duplicate_ordinal["usage"]["billing_receipt"].update(
            {"model_requests": 2, "cost_micros": 14}
        )
        duplicate_ordinal["usage"]["billing_receipt"]["request_receipts"] *= 2
        mutations.append(duplicate_ordinal)
        row_sum_mismatch = json.loads(json.dumps(base))
        row_sum_mismatch["usage"]["cost_micros"] = 8
        row_sum_mismatch["usage"]["billing_receipt"]["cost_micros"] = 8
        mutations.append(row_sum_mismatch)
        completed_without_request = json.loads(json.dumps(base))
        completed_without_request["model_requests"] = 0
        completed_without_request["usage"] = {}
        mutations.append(completed_without_request)

        for value in mutations:
            receipt = value.get("usage", {}).get("billing_receipt")
            if isinstance(receipt, dict):
                receipt["receipt_fingerprint"] = fingerprint({
                    key: item for key, item in receipt.items()
                    if key != "receipt_fingerprint"
                })
            result_fp = fingerprint(value)
            self.assertIsNone(
                self.repository._result_billing_evidence(value, result_fp), value
            )

    def test_oversized_provider_cost_cannot_rollback_returned_result(self) -> None:
        job = self.job("oversized-cost")
        intent = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="oversized-cost", job=job.to_dict(),
        )
        value = self.result(job, cost=0).to_dict()
        value["usage"]["cost_micros"] = 2**63
        receipt = value["usage"]["billing_receipt"]
        receipt["cost_micros"] = 2**63
        receipt["request_receipts"][0]["cost_micros"] = 2**63
        receipt["receipt_fingerprint"] = fingerprint({
            key: item for key, item in receipt.items()
            if key != "receipt_fingerprint"
        })
        self.repository.confirm_call(
            "CHECKPOINT", self.run_id, self.owner,
            call_id=intent["call_id"], result=value,
        )
        projection = self.repository.projection("CHECKPOINT", self.run_id)
        self.assertEqual("confirmed", projection["calls"][0]["state"])
        self.assertEqual(
            [intent["call_id"]], projection["billing_reconciliation_call_ids"]
        )

    def test_billing_binding_rejects_tamper_and_cancelled_run_can_reconcile(self) -> None:
        job = self.job("cancelled-accounting")
        intent = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="cancelled-accounting", job=job.to_dict(),
        )
        value = self.result(job).to_dict()
        value["usage"] = {}
        self.repository.confirm_call(
            "CHECKPOINT", self.run_id, self.owner,
            call_id=intent["call_id"], result=value,
        )
        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        with self.store.open_project("CHECKPOINT") as connection:
            connection.execute("BEGIN IMMEDIATE")
            self.repository.cancel_locked(connection, self.run_id)
            connection.commit()
        with self.store.open_project("CHECKPOINT") as connection:
            before = connection.execute(
                "SELECT COUNT(*) FROM runtime_events WHERE run_id=? "
                "AND event_kind='production_run_wake_requested'",
                (self.run_id,),
            ).fetchone()[0]
        result_fingerprint = self.repository.projection(
            "CHECKPOINT", self.run_id
        )["calls"][0]["result_fingerprint"]
        record = self.repository.reconcile_billing_receipt(
            "CHECKPOINT", self.run_id,
            call_id=intent["call_id"],
            expected_result_fingerprint=result_fingerprint,
            cost_micros=4,
            evidence_ref="provider-ledger:cancelled-fixture",
            evidence_fingerprint=fingerprint("cancelled-fixture"),
        )
        self.assertEqual(4, record["cost_micros"])
        with self.store.open_project("CHECKPOINT") as connection:
            after = connection.execute(
                "SELECT COUNT(*) FROM runtime_events WHERE run_id=? "
                "AND event_kind='production_run_wake_requested'",
                (self.run_id,),
            ).fetchone()[0]
        self.assertEqual(before, after)

    def test_billing_projection_fails_closed_if_stored_run_binding_is_tampered(self) -> None:
        self.dispatch_and_confirm("bound-receipt", cost=3)
        other_run = CoreOperations(self.store).start_author_run(
            "CHECKPOINT",
            task_mode="DRAFT",
            target_ref="DOC-1",
            payload={"instruction": "other fixture", "chapter_id": "CH001"},
        )["run_id"]
        with self.store.open_project("CHECKPOINT") as connection:
            connection.execute("DROP TRIGGER production_billing_receipt_update_binding")
            connection.execute(
                "UPDATE production_billing_receipts SET run_id=? WHERE run_id=?",
                (other_run, self.run_id),
            )
            with self.assertRaises(ProductionStageError) as corrupt:
                self.repository._billing_summary_locked(connection, self.run_id)
            self.assertEqual("billing_receipt_corrupt", corrupt.exception.code)

    def test_framework_build_migration_reuses_only_exact_regression_bound_checkpoints(self) -> None:
        job, _ = self.dispatch_and_confirm("before-fix")
        self.assertTrue(self.repository.mark_framework_bug_blocked(
            "CHECKPOINT", self.run_id, self.owner,
            error_type="FixtureFrameworkBug",
            error_fingerprint=fingerprint("fixture-framework-bug"),
        ))
        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        new_build = {
            "schema": "quillframe_framework_build_identity_v1",
            "build_fingerprint": fingerprint("build-after-regression"),
        }
        preview = self.repository.build_migration_preview(
            "CHECKPOINT", self.run_id, new_framework_build=new_build
        )
        receipt = self.repository._record_offline_regression_receipt(
            "CHECKPOINT", self.run_id, new_framework_build=new_build,
            test_command_fingerprint=fingerprint("fixed-offline-command"),
            test_output_fingerprint=fingerprint("fixed-offline-output"),
            test_evidence_fingerprints=[fingerprint("focused-regression-pass")],
        )
        migration = self.repository.migrate_framework_build(
            "CHECKPOINT",
            self.run_id,
            expected_request_fingerprint=preview["from_request_fingerprint"],
            new_framework_build=new_build,
            regression_receipt_id=receipt["receipt_id"],
            authorization_ref="user-approved:fixture-build-migration",
        )
        self.assertEqual(new_build["build_fingerprint"], migration["to_build_fingerprint"])
        migrated_request = {**self.request, "framework_build": new_build}
        self.owner = self.repository.acquire(
            "CHECKPOINT", self.run_id, migrated_request
        )
        replay = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="before-fix", job=job.to_dict(),
        )
        self.assertTrue(replay["replayed"])

        self.repository.confirm_node_validation(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="before-fix", input_fingerprint=job.input_fingerprint,
            validation_kind="post-migration-semantic-validation",
            validation_fingerprint=fingerprint("post-migration-pass"),
        )
        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        self.owner = self.repository.acquire("CHECKPOINT", self.run_id, migrated_request)
        replay_after_validation = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="before-fix", job=job.to_dict(),
        )
        self.assertTrue(replay_after_validation["replayed"])
        versions = self.repository.execution_request_versions("CHECKPOINT", self.run_id)
        self.assertEqual([1, 2], [row["version"] for row in versions])
        self.assertEqual(self.request, versions[0]["request"])
        self.assertEqual(migrated_request, versions[1]["request"])

        changed = self.job("before-fix")
        changed.instruction = "Different input after migration"
        with self.assertRaises(ProductionStageError) as conflict:
            self.repository.begin_call(
                "CHECKPOINT", self.run_id, self.owner,
                stage_key="before-fix", job=changed.to_dict(),
            )
        self.assertEqual("stage_input_conflict", conflict.exception.code)

    def test_build_migration_cannot_resurrect_failed_gate(self) -> None:
        self.dispatch_and_confirm("failed-gate-stage")
        with self.store.open_project("CHECKPOINT") as connection:
            connection.execute(
                "UPDATE runs SET status='failed_gate' WHERE run_id=?", (self.run_id,)
            )
            connection.commit()
        self.assertFalse(self.repository.mark_framework_bug_blocked(
            "CHECKPOINT", self.run_id, self.owner,
            error_type="LateFixtureError",
            error_fingerprint=fingerprint("late-fixture-error"),
        ))
        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        with self.assertRaises(ProductionStageError) as rejected:
            self.repository.build_migration_preview(
                "CHECKPOINT", self.run_id,
                new_framework_build={
                    "schema": "quillframe_framework_build_identity_v1",
                    "build_fingerprint": fingerprint("forbidden-build"),
                },
            )
        self.assertEqual("build_migration_not_framework_bug", rejected.exception.code)

    def test_fabricated_unpersisted_regression_receipt_id_is_rejected(self) -> None:
        self.dispatch_and_confirm("fabrication-stage")
        self.assertTrue(self.repository.mark_framework_bug_blocked(
            "CHECKPOINT", self.run_id, self.owner,
            error_type="FixtureFrameworkBug",
            error_fingerprint=fingerprint("fabrication-framework-bug"),
        ))
        self.repository.release("CHECKPOINT", self.run_id, self.owner)
        new_build = {
            "schema": "quillframe_framework_build_identity_v1",
            "build_fingerprint": fingerprint("unpersisted-receipt-build"),
        }
        preview = self.repository.build_migration_preview(
            "CHECKPOINT", self.run_id, new_framework_build=new_build
        )
        with self.assertRaises(ProductionStageError) as rejected:
            self.repository.migrate_framework_build(
                "CHECKPOINT", self.run_id,
                expected_request_fingerprint=preview["from_request_fingerprint"],
                new_framework_build=new_build,
                regression_receipt_id="buildreg_" + "0" * 32,
                authorization_ref="user-approved:must-not-be-enough",
            )
        self.assertEqual("build_migration_regression_invalid", rejected.exception.code)

    def test_expired_pollable_lease_is_ready_within_thirty_seconds(self) -> None:
        job = self.job("pollable")
        intent = self.repository.begin_call(
            "CHECKPOINT", self.run_id, self.owner,
            stage_key="pollable", job=job.to_dict(),
        )
        self.repository.mark_pollable(
            "CHECKPOINT", self.run_id, self.owner, intent["call_id"]
        )
        self.clock.advance(21)
        self.assertIn(self.run_id, self.repository.ready_run_ids("CHECKPOINT"))
        self.assertLessEqual(EXECUTION_LEASE_SECONDS + 5, 30)

    def test_wake_query_uses_covering_runtime_event_index(self) -> None:
        with self.store.open_project("CHECKPOINT") as connection:
            indexes = {
                row["name"] for row in connection.execute(
                    "PRAGMA index_list(runtime_events)"
                ).fetchall()
            }
        self.assertIn("idx_runtime_events_run_kind_id", indexes)


class CoordinatorLifecycleTests(unittest.TestCase):
    def test_ninth_wake_is_scheduled_while_eight_model_waiters_are_blocked(self) -> None:
        release = threading.Event()
        ninth_started = threading.Event()

        class FakeStore:
            root = Path("C:/quillframe-coordinator-fixture")

        class FakeRepository:
            def __init__(self) -> None:
                self.ready = [
                    {"run_id": f"RUN-{index}", "wake_event_ids": [f"evt_wake_{index}"]}
                    for index in range(8)
                ]

            def ready_runs(self, project_id: str, *, limit: int):  # noqa: ANN001
                return list(self.ready[:limit])

            @staticmethod
            def consume_wakes(project_id: str, run_id: str, *, wake_event_ids):  # noqa: ANN001
                return None

        class FakeExecutor:
            store = FakeStore()

            def __init__(self) -> None:
                self.stage_repository = FakeRepository()

            @staticmethod
            def resume_execution(project_id: str, run_id: str) -> dict:
                if run_id == "RUN-8":
                    ninth_started.set()
                    return {"status": "semantic_pending"}
                release.wait(3)
                return {"status": "semantic_pending"}

        executor = FakeExecutor()
        first = ProductionRunExecutor.resume_ready_runs(executor, "PROJECT")
        self.assertEqual(8, len(first["scheduled_run_ids"]))
        executor.stage_repository.ready.append(
            {"run_id": "RUN-8", "wake_event_ids": ["evt_wake_8"]}
        )
        second = ProductionRunExecutor.resume_ready_runs(executor, "PROJECT")
        self.assertIn("RUN-8", second["scheduled_run_ids"])
        self.assertTrue(ninth_started.wait(2))
        release.set()
        time.sleep(0.05)
        ProductionRunExecutor.resume_ready_runs(executor, "PROJECT")

    def test_stop_timeout_does_not_allow_a_second_live_coordinator(self) -> None:
        entered = threading.Event()
        release = threading.Event()

        class BlockingRuntime:
            @staticmethod
            def resume_ready_runs(project_id: str) -> dict:
                entered.set()
                release.wait(2)
                return {"project_id": project_id}

        coordinator = ProductionCoordinator(
            BlockingRuntime, lambda: ["PROJECT"], interval_seconds=0.5
        )
        coordinator.start()
        self.assertTrue(entered.wait(1))
        original = coordinator._thread
        coordinator.stop(timeout=0.01)
        self.assertIs(coordinator._thread, original)
        coordinator.start()
        self.assertIs(coordinator._thread, original)
        release.set()
        original.join(timeout=2)
        coordinator.stop(timeout=1)
        self.assertIsNone(coordinator._thread)


class FrameworkBuildIdentityTests(unittest.TestCase):
    def test_learning_harness_surface_and_root_contract_changes_rotate_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for directory in BUILD_ROOTS:
                (root / directory).mkdir(parents=True)
                (root / directory / "fixture.py").write_text(
                    "VALUE = 1\n", encoding="utf-8"
                )
            for relative in ROOT_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "1.0.0-dev.0\n" if relative == "VERSION" else "fixture\n",
                    encoding="utf-8",
                )
            baseline = framework_build_identity(root)["build_fingerprint"]
            for relative in (
                "learning/fixture.py",
                "harness/fixture.py",
                "surface/fixture.py",
                "HARNESS_MANIFEST.yaml",
            ):
                path = root / relative
                original = path.read_text(encoding="utf-8")
                path.write_text(original + "changed\n", encoding="utf-8")
                self.assertNotEqual(
                    baseline, framework_build_identity(root)["build_fingerprint"], relative
                )
                path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
