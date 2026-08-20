from __future__ import annotations

import os
import tempfile
import unittest

from core_operations import CoreOperations
from persistence.quillframe_sqlite import QuillframeStore
from production_runtime import ProductionRunError, ProductionRunExecutor
from studio import host_bridge


class BridgeV11RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="qf-v11-")
        os.environ["QUILLFRAME_DATA_DIR"] = self.temp.name
        host_bridge._agent_runtime_instance = None

    def tearDown(self) -> None:
        host_bridge._agent_runtime_instance = None
        os.environ.pop("QUILLFRAME_DATA_DIR", None)
        self.temp.cleanup()

    def request(self, operation: str, args: dict, *, surface: str = "local_app") -> dict:
        return host_bridge.invoke(
            {
                "schema": host_bridge.REQUEST_SCHEMA,
                "bridge_version": host_bridge.BRIDGE_VERSION,
                "request_id": operation,
                "operation": operation,
                "surface": surface,
                "args": args,
                "authority": False,
            }
        )

    def test_start_events_and_explicit_cancel_share_one_durable_workflow(self):
        self.assertEqual(
            self.request("project.create", {"project_id": "P", "title": "Novel"})["status"],
            "ok",
        )
        started = self.request(
            "author.run.start",
            {
                "project_id": "P",
                "task_mode": "DRAFT",
                "payload": {"chapter_id": "CH001", "author_profile": "guided"},
            },
        )
        self.assertEqual(started["status"], "ok")
        run_id = started["data"]["run_id"]
        self.assertEqual(started["data"]["workflow"]["chapter_id"], "CH001")

        events = self.request("author.run.events", {"run_id": run_id, "cursor": -1})
        self.assertEqual(events["status"], "ok")
        self.assertEqual(events["data"]["events"][0]["event_type"], "run_started")
        cursor = events["data"]["next_cursor"]

        cancelled = self.request(
            "author.run.cancel",
            {
                "project_id": "P",
                "run_id": run_id,
                "cursor": cursor,
                "idempotency_key": "cancel-1",
                "user_authorized": True,
            },
        )
        self.assertEqual(cancelled["status"], "ok")
        self.assertEqual(cancelled["data"]["event_type"], "cancelled")
        replay = self.request(
            "author.run.cancel",
            {
                "project_id": "P",
                "run_id": run_id,
                "cursor": cursor,
                "idempotency_key": "cancel-1",
                "user_authorized": True,
            },
        )
        self.assertEqual(replay["data"], cancelled["data"])

    def test_ch002_start_fails_before_workflow_persistence(self):
        self.request("project.create", {"project_id": "P", "title": "Novel"})
        blocked = self.request(
            "author.run.start",
            {
                "project_id": "P",
                "task_mode": "DRAFT",
                "payload": {"chapter_id": "CH002", "author_profile": "guided"},
            },
        )
        self.assertEqual(blocked["status"], "failed")
        self.assertEqual(blocked["error"]["code"], "chapter_scope_violation")

    def test_model_route_preview_invokes_no_provider_and_returns_v1_receipt(self):
        preview = self.request(
            "model.route.preview",
            {
                "project_id": "P",
                "manager_invocation_id": "manager",
                "task_profile": {
                    "schema": "quillframe_model_task_profile_v1",
                    "profile_id": "writer",
                    "role": "writer",
                    "required_capabilities": ["structured_output"],
                    "context_budget_tokens": 8000,
                    "max_cost_micros": 1000,
                    "quality_floor": "high",
                    "independence": "none",
                    "privacy": "project",
                    "latency_preference": "quality_first",
                },
                "available_routes": [
                    {
                        "route_id": "quality",
                        "capabilities": ["structured_output"],
                        "context_limit_tokens": 32000,
                        "estimated_cost_micros": 700,
                        "quality_rank": 3,
                        "privacy_levels": ["project"],
                        "invocation_id": "worker",
                        "independent_eligible": True,
                    }
                ],
            },
        )
        self.assertEqual(preview["status"], "ok")
        self.assertEqual(preview["data"]["schema"], "quillframe_model_route_receipt_v1")
        self.assertEqual(preview["data"]["selected_route_id"], "quality")
        self.assertFalse(preview["data"]["authority"])

    def test_production_executor_rejects_run_without_ch001_workflow_binding(self):
        store = QuillframeStore()
        store.create_project("RAW", "Bypass attempt")
        run_id = CoreOperations(store).start_author_run(
            "RAW",
            task_mode="DRAFT",
            target_ref="CH001",
            payload={"chapter_id": "CH001", "instruction": "bypass Host Bridge"},
        )["run_id"]

        class NeverCallModel:
            def run(self, *_args, **_kwargs):
                raise AssertionError("model must not run before workflow scope validation")

        with self.assertRaises(ProductionRunError) as blocked:
            ProductionRunExecutor(store, NeverCallModel()).execute(
                "RAW",
                run_id,
                service_id="S",
                instruction="draft",
                reader_grip="high",
                rule_material=[
                    {
                        "id": "R",
                        "authority": "framework",
                        "statement": "fixture rule",
                    }
                ],
                independent_provenance={},
            )
        self.assertEqual(blocked.exception.code, "workflow_scope_required")


if __name__ == "__main__":
    unittest.main()
