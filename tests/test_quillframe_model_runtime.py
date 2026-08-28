from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from model_runtime import EndpointPolicy, MemorySecretStore, MockTransport, ModelRuntime, ModelRuntimeError, TransportResponse, normalize_endpoint
from model_runtime.manager import ModelServiceManager
from model_runtime.protocols import AnthropicMessagesCodec, OpenAIChatCodec, OpenAIResponsesCodec


def response(status: int, body: dict | list | None) -> TransportResponse:
    return TransportResponse(status, {}, body, json.dumps(body) if body is not None else "")


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


class MemoryRepository:
    def __init__(self) -> None:
        self.services: dict[str, dict] = {}

    def save_snapshot(self, snapshot):
        self.services[snapshot.service_id] = {
            "service_id": snapshot.service_id,
            "endpoint": snapshot.endpoint,
            "credential_ref": snapshot.credential_ref,
            "credential_present": snapshot.credential_ref is not None,
            "models": [m.to_dict() for m in snapshot.models],
        }
        return self.services[snapshot.service_id]

    def find_service_by_endpoint(self, endpoint):
        return next((dict(v) for v in self.services.values() if v["endpoint"] == endpoint), None)

    def get_internal(self, service_id):
        return dict(self.services[service_id])

    def get_service(self, service_id):
        value = dict(self.services[service_id])
        value.pop("credential_ref", None)
        return value

    def set_credential_ref(self, service_id, credential_ref):
        self.services[service_id]["credential_ref"] = credential_ref
        self.services[service_id]["credential_present"] = credential_ref is not None

    def delete_service(self, service_id):
        del self.services[service_id]

    def list_services(self):
        return [self.get_service(key) for key in self.services]


class ModelRuntimeTests(unittest.TestCase):
    def test_endpoint_normalization_and_exact_surface(self):
        layout = normalize_endpoint("https://api.example.test/v1/chat/completions/")
        self.assertEqual(layout.base_url, "https://api.example.test/v1")
        self.assertEqual(layout.exact_surface, "openai_chat_completions")
        self.assertEqual(layout.url_for("models"), "https://api.example.test/v1/models")

    def test_endpoint_security(self):
        with self.assertRaises(ValueError):
            normalize_endpoint("https://user:pass@example.test/v1")
        with self.assertRaises(ValueError):
            normalize_endpoint("http://example.test/v1")
        self.assertEqual(normalize_endpoint("http://localhost:11434/v1").base_url, "http://localhost:11434/v1")
        with self.assertRaises(ValueError):
            normalize_endpoint("http://192.168.1.5:1234/v1")
        private = normalize_endpoint("http://192.168.1.5:1234/v1", EndpointPolicy(allow_private_network=True, require_https_for_remote=False))
        self.assertEqual(private.base_url, "http://192.168.1.5:1234/v1")

    def test_chat_codec_tool_roundtrip(self):
        codec = OpenAIChatCodec()
        turn = codec.normalize("m", {"id": "r1", "choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "echo", "arguments": "{\"value\":\"ok\"}"}}]}}]})
        self.assertEqual(turn.tool_calls[0].arguments, {"value": "ok"})
        history = [{"role": "assistant", "content": "", "tool_calls": [turn.tool_calls[0].to_dict()]}, {"role": "tool", "call_id": "c1", "content": "ok"}]
        body = codec.request_body("m", history, [], 32)
        self.assertEqual(body["messages"][-1]["tool_call_id"], "c1")

    def test_responses_and_anthropic_tool_normalization(self):
        responses = OpenAIResponsesCodec().normalize("m", {"id": "r", "output": [{"type": "function_call", "call_id": "c", "name": "echo", "arguments": "{\"value\":1}"}]})
        anthropic = AnthropicMessagesCodec().normalize("m", {"id": "a", "content": [{"type": "tool_use", "id": "c2", "name": "echo", "input": {"value": 2}}]})
        self.assertEqual(responses.tool_calls[0].arguments["value"], 1)
        self.assertEqual(anthropic.tool_calls[0].arguments["value"], 2)

    def test_connect_only_serializes_secret_reference_and_sanitizes_nested_metadata(self):
        endpoint = "https://api.example.test/v1"
        routes = {
            ("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m1", "nested": {"api_key": "DO-NOT-STORE", "safe": "x"}}]})
        }
        secrets = MemorySecretStore()
        runtime = ModelRuntime(secrets, MockTransport(routes))
        snapshot = runtime.connect(endpoint, "TOP-SECRET")
        serialized = json.dumps(snapshot.to_dict())
        self.assertNotIn("TOP-SECRET", serialized)
        self.assertNotIn("DO-NOT-STORE", serialized)
        self.assertTrue(snapshot.credential_ref.startswith("memory:"))
        self.assertTrue(snapshot.secret_present)

    def test_mixed_protocol_models_are_per_model_evidence_not_provider_inference(self):
        endpoint = "https://go.example.test/v1"
        models = {"data": [
            {"id": "glm", "endpoint": endpoint + "/chat/completions"},
            {"id": "gpt", "endpoint": endpoint + "/responses"},
            {"id": "qwen", "endpoint": endpoint + "/messages"},
        ]}
        runtime = ModelRuntime(MemorySecretStore(), MockTransport({("GET", endpoint + "/models", "bearer"): response(200, models)}))
        snapshot = runtime.connect(endpoint, "t")
        self.assertEqual({m.model_id: m.protocol for m in snapshot.models}, {"glm": "openai_chat_completions", "gpt": "openai_responses", "qwen": "anthropic_messages"})

    def test_lazy_tool_call_probe_records_verified_evidence(self):
        endpoint = "https://api.example.test/v1"
        routes = {
            ("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m", "protocol": "openai_chat_completions"}]}),
            ("POST", endpoint + "/chat/completions", "bearer"): [
                response(200, {"choices": [{"finish_reason": "stop", "message": {"content": "OK"}}]}),
                response(200, {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [{"id": "p", "function": {"name": "quillframe_capability_probe", "arguments": "{\"value\":\"ok\"}"}}]}}]}),
            ],
        }
        runtime = ModelRuntime(MemorySecretStore(), MockTransport(routes))
        snapshot = runtime.connect(endpoint, "t")
        model = runtime.probe_model(snapshot.service_id, "m", verify_tools=True)
        self.assertEqual(model.capability_state("text"), "verified")
        self.assertEqual(model.capability_state("tool_calling"), "verified")

    def test_model_service_reconnect_canonicalizes_endpoint_and_rotates_secret(self):
        endpoint = "https://api.example.test/v1"
        transport = MockTransport({
            ("GET", endpoint + "/models", "bearer"): [response(200, {"data": [{"id": "m"}]}), response(200, {"data": [{"id": "m"}]})]
        })
        secrets = MemorySecretStore()
        repo = MemoryRepository()
        manager = ModelServiceManager(ModelRuntime(secrets, transport), repo, secrets)
        first = manager.connect(endpoint + "/", "old-token")
        old_ref = repo.services[first["service_id"]]["credential_ref"]
        second = manager.connect(endpoint, "new-token")
        new_ref = repo.services[second["service_id"]]["credential_ref"]
        self.assertEqual(first["service_id"], second["service_id"])
        self.assertNotEqual(old_ref, new_ref)
        self.assertFalse(secrets.present(old_ref))
        self.assertTrue(secrets.present(new_ref))

    def test_model_service_empty_token_reconnect_preserves_secret_and_refreshes_with_authentication(self):
        endpoint = "https://api.example.test/v1"
        transport = MockTransport({
            ("GET", endpoint + "/models", "bearer"): [
                response(200, {"data": [{"id": "original"}]}),
                response(200, {"data": [{"id": "refreshed"}]}),
            ],
            ("GET", endpoint + "/models", "none"): response(200, {"data": [{"id": "public"}]}),
        })
        secrets = MemorySecretStore()
        repo = MemoryRepository()
        runtime = ModelRuntime(secrets, transport)
        manager = ModelServiceManager(runtime, repo, secrets)
        first = manager.connect(endpoint + "/", "stored-token")
        service_id = first["service_id"]
        old_ref = repo.get_internal(service_id)["credential_ref"]

        reconnected = manager.connect(endpoint, "")

        self.assertEqual(reconnected["service_id"], service_id)
        self.assertEqual(repo.get_internal(service_id)["credential_ref"], old_ref)
        self.assertTrue(secrets.present(old_ref))
        self.assertEqual([model["model_id"] for model in reconnected["models"]], ["refreshed"])
        self.assertEqual(runtime.snapshot(service_id).auth_style, "bearer")
        self.assertEqual([(item["auth_style"], item["token_present"]) for item in transport.requests], [("bearer", True)] * 2)

        manager.remove_token(service_id)
        self.assertFalse(secrets.present(old_ref))
        self.assertIsNone(repo.get_internal(service_id)["credential_ref"])
        self.assertFalse(manager.get(service_id)["credential_present"])

    def test_model_service_new_anonymous_endpoint_connects_and_reconnects_without_secret(self):
        endpoint = "http://127.0.0.1:8765/v1"
        transport = MockTransport({
            ("GET", endpoint + "/models", "none"): response(200, {"data": [{"id": "local"}]}),
        })
        secrets = MemorySecretStore()
        repo = MemoryRepository()
        manager = ModelServiceManager(ModelRuntime(secrets, transport), repo, secrets)
        first = manager.connect(endpoint, "")
        second = manager.connect(endpoint + "/", "")

        self.assertEqual(first["service_id"], second["service_id"])
        self.assertFalse(second["credential_present"])
        self.assertIsNone(repo.get_internal(second["service_id"])["credential_ref"])
        self.assertEqual([(item["auth_style"], item["token_present"]) for item in transport.requests], [("none", False)] * 2)

    def test_model_service_failed_empty_token_reconnect_retains_secret_and_snapshot(self):
        endpoint = "https://api.example.test/v1"
        transport = MockTransport({
            ("GET", endpoint + "/models", "bearer"): [
                response(200, {"data": [{"id": "original"}]}),
                response(503, {"error": "discovery unavailable"}),
            ],
            ("GET", endpoint + "/models", "none"): response(200, {"data": [{"id": "public"}]}),
        })
        secrets = MemorySecretStore()
        repo = MemoryRepository()
        runtime = ModelRuntime(secrets, transport)
        manager = ModelServiceManager(runtime, repo, secrets)
        first = manager.connect(endpoint, "stored-token")
        service_id = first["service_id"]
        before = repo.get_internal(service_id)
        snapshot = runtime.snapshot(service_id).to_dict()

        with self.assertRaises(ModelRuntimeError) as failed:
            manager.connect(endpoint, "")

        self.assertEqual(failed.exception.code, "model_discovery_failed")
        self.assertEqual(repo.get_internal(service_id), before)
        self.assertEqual(runtime.snapshot(service_id).to_dict(), snapshot)
        self.assertTrue(secrets.present(before["credential_ref"]))
        self.assertEqual(transport.requests[-1]["auth_style"], "bearer")
        self.assertTrue(transport.requests[-1]["token_present"])

    def test_tool_runtime_separates_capability_authority_before_state_and_replay(self):
        from agent_runtime import RepositoryToolset, ToolRuntime
        from agent_runtime.tools import ToolRuntimeError

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "a.txt"
            path.write_text("old", encoding="utf-8")
            before = sha(b"old")
            tools = ToolRuntime(host_capabilities={"filesystem_read", "filesystem_write"})
            RepositoryToolset(root).register(tools, include_write=True)
            with self.assertRaises(ToolRuntimeError) as denied:
                tools.execute("c1", "repo.write", {"path": "a.txt", "content": "new", "expected_before_fingerprint": before}, grants={"repo.write"}, authority={}, idempotency_key="id:c1")
            self.assertEqual(denied.exception.code, "tool_authority_denied")
            receipt = tools.execute("c1", "repo.write", {"path": "a.txt", "content": "new", "expected_before_fingerprint": before}, grants={"repo.write"}, authority={"filesystem_write": True}, idempotency_key="id:c1")
            duplicate = tools.execute("c1", "repo.write", {"path": "a.txt", "content": "new", "expected_before_fingerprint": before}, grants={"repo.write"}, authority={"filesystem_write": True}, idempotency_key="id:c1")
            self.assertEqual(receipt, duplicate)
            with self.assertRaises(ToolRuntimeError) as conflict:
                tools.execute("c1", "repo.write", {"path": "a.txt", "content": "other", "expected_before_fingerprint": before}, grants={"repo.write"}, authority={"filesystem_write": True}, idempotency_key="id:c1")
            self.assertEqual(conflict.exception.code, "tool_call_replay_conflict")

    def test_agent_loop_is_quillframe_owned_model_tool_model(self):
        from agent_runtime import AgentBudget, AgentJob, AgentRunner, ToolRuntime, ToolSpec

        endpoint = "https://api.example.test/v1"
        post = [
            response(200, {"choices": [{"finish_reason": "stop", "message": {"content": "OK"}}], "usage": {"prompt_tokens": 2, "completion_tokens": 1}}),
            response(200, {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [{"id": "probe", "function": {"name": "quillframe_capability_probe", "arguments": "{\"value\":\"ok\"}"}}]}}]}),
            response(200, {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [{"id": "echo1", "function": {"name": "echo", "arguments": "{\"value\":\"hello\"}"}}]}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}),
            response(200, {"choices": [{"finish_reason": "stop", "message": {"content": "done"}}], "usage": {"prompt_tokens": 12, "completion_tokens": 3}}),
        ]
        transport = MockTransport({
            ("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m", "protocol": "openai_chat_completions"}]}),
            ("POST", endpoint + "/chat/completions", "bearer"): post,
        })
        runtime = ModelRuntime(MemorySecretStore(), transport)
        service = runtime.connect(endpoint, "t")
        tools = ToolRuntime(host_capabilities={"test_tool"})
        tools.register(ToolSpec("echo", "echo", {"type": "object", "additionalProperties": False, "required": ["value"], "properties": {"value": {"type": "string"}}}, lambda args: {"value": args["value"]}, "test_tool"))
        runner = AgentRunner(runtime, tools)
        job = AgentJob("job", "session", "run", "SYSTEM-IMPROVE", "coding_planner", service.service_id, "Use echo once and finish.", tool_grants={"echo"}, required_model_capabilities={"text", "tool_calling"}, budgets=AgentBudget(max_steps=6, max_model_requests=6, max_tool_calls=4, max_parallel_tool_calls=2, max_output_tokens_per_request=128, max_total_tokens=1000, max_elapsed_ms=30000))
        result = runner.run(job)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.final_text, "done")
        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(result.tool_receipts[0]["tool"], "echo")
        self.assertEqual(result.usage, {"input_tokens": 22, "output_tokens": 8})
        self.assertFalse(result.to_dict()["authority"])

    def test_pre_1_0_global_state_is_rejected_instead_of_migrated(self):
        from persistence.quillframe_sqlite import Pre10StateRejectedError, apply_schema

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "global.sqlite"
            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            conn.execute("CREATE TABLE provider_configuration(provider_id TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO provider_configuration(provider_id) VALUES('p')")
            conn.commit()
            with self.assertRaises(Pre10StateRejectedError):
                apply_schema(conn, "global")
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables, {"provider_configuration"})
            conn.close()

    def test_fresh_1_0_global_schema_has_no_pre_1_0_provider_tables(self):
        from persistence.quillframe_sqlite import apply_schema

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "global.sqlite"
            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            apply_schema(conn, "global")
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("model_services", tables)
            self.assertIn("discovered_models", tables)
            self.assertIn("model_capability_evidence", tables)
            self.assertNotIn("provider_configuration", tables)
            self.assertNotIn("model_registry", tables)
            self.assertEqual(tuple(conn.execute("SELECT scope,release FROM quillframe_schema_identity").fetchone()), ("global", "1.0"))
            conn.close()

    def test_sqlite_repository_never_projects_credential_reference_as_secret_value(self):
        from persistence.quillframe_sqlite import QuillframeStore

        endpoint = "https://api.example.test/v1"
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            store.initialize_global()
            from model_runtime.persistence import SQLiteModelServiceRepository
            secrets = MemorySecretStore()
            runtime = ModelRuntime(secrets, MockTransport({("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m"}]})}))
            snapshot = runtime.connect(endpoint, "TOP-SECRET")
            repo = SQLiteModelServiceRepository(store)
            repo.save_snapshot(snapshot)
            public = repo.get_service(snapshot.service_id)
            serialized = json.dumps(public)
            self.assertNotIn("TOP-SECRET", serialized)
            self.assertNotIn("credential_ref", public)
            self.assertEqual(public["credential_present"], 1)


if __name__ == "__main__":
    unittest.main()
