from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from agent_runtime import RepositoryToolset, SubprocessToolset, ToolRuntime
from agent_runtime.tools import ToolRuntimeError
from model_runtime import MemorySecretStore, MockTransport, ModelRuntime, TransportResponse
from model_runtime.manager import ModelServiceManager
from model_runtime.persistence import SQLiteModelServiceRepository
from model_runtime.protocols import AnthropicMessagesCodec, OpenAIResponsesCodec
from persistence.quillframe_sqlite import QuillframeStore


def response(status: int, body: dict | list | None) -> TransportResponse:
    return TransportResponse(status, {}, body, json.dumps(body) if body is not None else "")


class ProtocolContinuationTests(unittest.TestCase):
    def test_responses_replays_prior_output_items_before_tool_result(self):
        codec = OpenAIResponsesCodec()
        payload = {
            "id": "resp-1",
            "status": "completed",
            "output": [
                {"id": "reason-1", "type": "reasoning", "summary": []},
                {"id": "call-1", "type": "function_call", "call_id": "call-1", "name": "echo", "arguments": "{\"value\":\"x\"}"},
            ],
        }
        turn = codec.normalize("m", payload)
        self.assertTrue(turn.opaque_continuation)
        body = codec.request_body(
            "m",
            [
                {"role": "user", "content": "go"},
                {"role": "assistant", "content": turn.text, "tool_calls": [c.to_dict() for c in turn.tool_calls], "opaque_continuation": turn.opaque_continuation},
                {"role": "tool", "call_id": "call-1", "content": "done"},
            ],
            [],
            64,
        )
        self.assertEqual(body["input"][1]["type"], "reasoning")
        self.assertEqual(body["input"][2]["type"], "function_call")
        self.assertEqual(body["input"][3], {"type": "function_call_output", "call_id": "call-1", "output": "done"})
        self.assertFalse(body["store"])

    def test_anthropic_groups_multiple_tool_results_immediately_after_tool_use(self):
        codec = AnthropicMessagesCodec()
        turn = codec.normalize("m", {
            "id": "msg-1",
            "stop_reason": "tool_use",
            "content": [
                {"type": "tool_use", "id": "t1", "name": "a", "input": {"x": 1}},
                {"type": "tool_use", "id": "t2", "name": "b", "input": {"x": 2}},
            ],
        })
        body = codec.request_body(
            "m",
            [
                {"role": "user", "content": "go"},
                {"role": "assistant", "content": "", "tool_calls": [c.to_dict() for c in turn.tool_calls], "opaque_continuation": turn.opaque_continuation},
                {"role": "tool", "call_id": "t1", "content": "one"},
                {"role": "tool", "call_id": "t2", "content": "two"},
            ],
            [],
            64,
        )
        self.assertEqual(body["messages"][-2]["role"], "assistant")
        result_message = body["messages"][-1]
        self.assertEqual(result_message["role"], "user")
        self.assertEqual([block["tool_use_id"] for block in result_message["content"]], ["t1", "t2"])


class ToolIsolationTests(unittest.TestCase):
    def test_repository_tools_deny_secret_bearing_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env").write_text("VERYSECRET=1", encoding="utf-8")
            (root / "safe.txt").write_text("hello", encoding="utf-8")
            runtime = ToolRuntime(host_capabilities={"filesystem_read"})
            RepositoryToolset(root).register(runtime)
            with self.assertRaises(ToolRuntimeError) as denied:
                runtime.execute("r1", "repo.read", {"path": ".env"}, grants={"repo.read"}, authority={})
            self.assertEqual(denied.exception.code, "repo_sensitive_path_denied")
            result = runtime.execute("s1", "repo.search", {"query": "VERYSECRET"}, grants={"repo.search"}, authority={})
            self.assertEqual(result["output"]["matches"], [])

    def test_subprocess_does_not_inherit_model_api_token(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runtime = ToolRuntime(host_capabilities={"subprocess"})
            SubprocessToolset(root, {sys.executable}).register(runtime)
            old = os.environ.get("QUILLFRAME_MODEL_API_TOKEN")
            os.environ["QUILLFRAME_MODEL_API_TOKEN"] = "DO-NOT-INHERIT"
            try:
                receipt = runtime.execute(
                    "p1",
                    "process.run",
                    {"argv": [sys.executable, "-c", "import os; print(os.getenv('QUILLFRAME_MODEL_API_TOKEN'))"]},
                    grants={"process.run"},
                    authority={"subprocess_execute": True},
                    idempotency_key="job:p1",
                )
            finally:
                if old is None:
                    os.environ.pop("QUILLFRAME_MODEL_API_TOKEN", None)
                else:
                    os.environ["QUILLFRAME_MODEL_API_TOKEN"] = old
            self.assertEqual(receipt["output"]["returncode"], 0)
            self.assertEqual(receipt["output"]["stdout"].strip(), "None")


class DurableModelServiceTests(unittest.TestCase):
    def test_durable_snapshot_hydrates_without_model_execution(self):
        endpoint = "https://api.example.test/v1"
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            repo = SQLiteModelServiceRepository(store)
            secrets = MemorySecretStore()
            transport = MockTransport({("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m"}]})})
            first_runtime = ModelRuntime(secrets, transport)
            first = ModelServiceManager(first_runtime, repo, secrets).connect(endpoint, "TOKEN")
            second_runtime = ModelRuntime(secrets, MockTransport({}))
            second_manager = ModelServiceManager(second_runtime, repo, secrets)
            restored = second_manager.hydrate(first["service_id"])
            self.assertEqual(restored.service_id, first["service_id"])
            self.assertEqual(restored.models[0].model_id, "m")
            self.assertEqual(second_manager.hydrate_all()["stale"], [])

    def test_failed_refresh_never_deletes_existing_credential(self):
        endpoint = "https://api.example.test/v1"
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            repo = SQLiteModelServiceRepository(store)
            secrets = MemorySecretStore()
            transport = MockTransport({
                ("GET", endpoint + "/models", "bearer"): [
                    response(200, {"data": [{"id": "m"}]}),
                    response(500, {"error": "temporary"}),
                ]
            })
            runtime = ModelRuntime(secrets, transport)
            manager = ModelServiceManager(runtime, repo, secrets)
            connected = manager.connect(endpoint, "TOKEN")
            credential_ref = repo.get_internal(connected["service_id"])["credential_ref"]
            with self.assertRaises(Exception):
                manager.refresh(connected["service_id"])
            self.assertTrue(secrets.present(credential_ref))


if __name__ == "__main__":
    unittest.main()
