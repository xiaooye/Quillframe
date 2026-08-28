from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from model_runtime import EndpointPolicy, MemorySecretStore, MockTransport, ModelRuntime, ModelRuntimeError, TransportResponse, normalize_endpoint
from model_runtime.manager import ModelServiceManager
from model_runtime.protocols import AnthropicMessagesCodec, OpenAIChatCodec, OpenAIResponsesCodec
from model_runtime.structured_output import required_only_output_schema, validate_output_schema, validate_structured_text


OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["status", "report"],
    "properties": {"status": {"type": "string", "enum": ["pass", "fail"]}, "report": {"type": "string"}},
}


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


class StructuredOutputTests(unittest.TestCase):
    def test_required_only_profile_is_a_subset_without_mutating_the_contract(self):
        contract = {"type": "object", "additionalProperties": False, "required": ["decision"], "properties": {
            "optional_report": {"type": "string"}, "decision": {
                "type": "object", "additionalProperties": False, "required": ["result", "reason"], "properties": {
                    "result": {"enum": ["pass", "fail", "repair"]}, "reason": {"type": "string", "minLength": 1},
                    "optional_map": {"type": "object"},
                },
            },
        }}
        original = deepcopy(contract)
        schema = required_only_output_schema(contract)
        self.assertEqual({"decision"}, set(schema["properties"]))
        self.assertEqual({"result", "reason"}, set(schema["properties"]["decision"]["properties"]))
        for result in ("pass", "fail", "repair"):
            output = {"decision": {"result": result, "reason": "A bounded semantic finding."}}
            self.assertEqual(output, validate_structured_text(json.dumps(output), schema))
        self.assertEqual(original, contract)
        with self.assertRaises(ValueError):
            required_only_output_schema({**contract, "required": ["optional_report", "decision"], "additionalProperties": True})

    def test_strict_schema_rejects_unsupported_or_unverifiable_shapes(self):
        invalid = [
            {"type": "object"}, {**OUTPUT_SCHEMA, "required": ["status"]},
            {**OUTPUT_SCHEMA, "additionalProperties": True}, {**OUTPUT_SCHEMA, "allOf": []},
            {**OUTPUT_SCHEMA, "$ref": "#/$defs/value"},
            {**OUTPUT_SCHEMA, "properties": {"status": {"type": "string", "pattern": "x"}, "report": {"type": "string"}}},
            {**OUTPUT_SCHEMA, "properties": {"status": {"type": "number", "minimum": True}, "report": {"type": "string"}}},
        ]
        for schema in invalid:
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                validate_output_schema(schema)

    def test_exact_json_rejects_extra_closers_duplicate_keys_and_nonfinite_numbers(self):
        valid = ' {"status":"fail","report":"需要修复"}\n'
        self.assertEqual("fail", validate_structured_text(valid, OUTPUT_SCHEMA)["status"])
        for raw in (valid + "]}", valid + "{}", '```json\n' + valid + '```',
                    '{"status":"fail","status":"pass","report":"x"}',
                    '{"status":"pass","report":NaN}', '{"status":"pass","report":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                validate_structured_text(raw, OUTPUT_SCHEMA)

    def test_nested_anyof_uses_complete_closed_branches_without_rewriting_output(self):
        with_deadline = deepcopy(OUTPUT_SCHEMA)
        with_deadline["properties"]["due"] = {"type": "integer", "minimum": 0}
        with_deadline["required"].append("due")
        schema = {"type": "object", "additionalProperties": False, "required": ["updates"], "properties": {
            "updates": {"type": "array", "items": {"anyOf": [deepcopy(OUTPUT_SCHEMA), with_deadline]}}}}
        original = deepcopy(schema)
        for updates in ([], [{"status": "fail", "report": "需要修复"}], [{"status": "pass", "report": "bounded", "due": 2}]):
            value = {"updates": updates}
            raw = " \n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n"
            self.assertEqual(value, validate_structured_text(raw, schema))
        self.assertEqual(original, schema)
        for update in ({"status": "fail"}, {"status": "unknown", "report": "x"},
                       {"status": "pass", "report": "x", "due": None}, {"status": "pass", "report": "x", "extra": 1}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate_structured_text(json.dumps({"updates": [update]}), schema)
        raw = '{"updates":[{"status":"fail","status":"pass","report":"x"}]}'
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_structured_text(raw, schema)
        # anyOf requires at least one matching branch, not exactly one.
        overlapping = deepcopy(schema)
        overlapping["properties"]["updates"]["items"]["anyOf"].append(deepcopy(OUTPUT_SCHEMA))
        validate_structured_text('{"updates":[{"status":"fail","report":"x"}]}', overlapping)
        chat = OpenAIChatCodec().request_body("m", [], [], 64, output_schema=schema)
        responses = OpenAIResponsesCodec().request_body("m", [], [], 64, output_schema=schema)
        self.assertEqual(original, chat["response_format"]["json_schema"]["schema"])
        self.assertEqual(original, responses["text"]["format"]["schema"])

    def test_nested_anyof_cannot_admit_root_unions_partial_objects_or_unsupported_keywords(self):
        def wrap(value):
            return {"type": "object", "additionalProperties": False, "required": ["value"], "properties": {"value": value}}

        invalid_unions = [
            {"anyOf": []}, {"anyOf": {}}, {"anyOf": [True]},
            {"anyOf": [{"type": "string"}], "type": "string"},
            {"anyOf": [deepcopy(OUTPUT_SCHEMA)], "description": "Siblings are outside this profile."},
            {"anyOf": [{**OUTPUT_SCHEMA, "additionalProperties": True}]},
            {"anyOf": [{**OUTPUT_SCHEMA, "required": ["status"]}]},
            {"anyOf": [{"type": "string", "pattern": ".+"}]},
            {"anyOf": [{**OUTPUT_SCHEMA, "allOf": []}]},
        ]
        for union in invalid_unions:
            with self.subTest(union=union), self.assertRaises(ValueError):
                validate_output_schema(wrap(union))
        for root in ({"anyOf": [deepcopy(OUTPUT_SCHEMA)]}, {**OUTPUT_SCHEMA, "anyOf": [deepcopy(OUTPUT_SCHEMA)]}):
            with self.assertRaises(ValueError):
                validate_output_schema(root)

    def test_nested_anyof_preserves_aggregate_enum_string_property_and_depth_limits(self):
        def wrap(value):
            return {"type": "object", "additionalProperties": False, "required": ["value"], "properties": {"value": value}}

        many_properties = {f"key_{index}": {"type": "string"} for index in range(2500)}
        object_branch = {"type": "object", "additionalProperties": False,
                         "required": list(many_properties), "properties": many_properties}
        unions = [
            {"anyOf": [{"type": "integer", "enum": list(range(600))}] * 2},
            {"anyOf": [{"type": "string", "enum": ["x" * 60_000]}] * 2},
            {"anyOf": [object_branch, object_branch]},
        ]
        for union in unions:
            with self.assertRaises(ValueError):
                validate_output_schema(wrap(union))
        at_limit = {"type": "string"}
        for _ in range(9):
            at_limit = {"anyOf": [at_limit]}
        validate_output_schema(wrap(at_limit))
        with self.assertRaisesRegex(ValueError, "depth"):
            validate_output_schema(wrap({"anyOf": [at_limit]}))

    def test_native_schema_size_and_enum_limits_are_checked_locally(self):
        def wrap(value):
            return {"type": "object", "additionalProperties": False, "required": ["value"], "properties": {"value": value}}
        invalid = [
            wrap({"type": "integer", "enum": list(range(1001))}),
            wrap({"type": "string", "enum": [str(index) + "x" * 60 for index in range(251)]}),
            wrap({"type": "string", "enum": ["x" * 120_000]}),
            wrap({"type": "integer", "enum": [1, 1.0]}),
        ]
        for schema in invalid:
            with self.assertRaises(ValueError):
                validate_output_schema(schema)

    def test_scalar_bounds_nullable_fields_and_enum_types_are_enforced(self):
        schema = {"type": "object", "additionalProperties": False, "required": ["count", "note", "items"], "properties": {
            "count": {"type": "integer", "minimum": 1, "maximum": 2, "enum": [1, 2]},
            "note": {"type": ["string", "null"], "minLength": 1, "maxLength": 3},
            "items": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "boolean"}},
        }}
        good = {"count": 1, "note": None, "items": [True]}
        self.assertEqual(good, validate_structured_text(json.dumps(good), schema))
        self.assertEqual(1.0, validate_structured_text(json.dumps({**good, "count": 1.0}), schema)["count"])
        invalid = [{**good, "count": True}, {**good, "count": 3}, {**good, "count": 1.5},
                   {**good, "note": ""}, {**good, "note": "long"}, {**good, "items": []},
                   {**good, "items": [1]}, {**good, "extra": "not allowed"}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_structured_text(json.dumps(value), schema)


class ModelRuntimeTests(unittest.TestCase):
    def test_native_schema_is_explicit_in_both_openai_protocols(self):
        history = [{"role": "user", "content": "Return the bounded judgment."}]
        original = deepcopy(OUTPUT_SCHEMA)
        chat = OpenAIChatCodec().request_body("m", history, [], 64, output_schema=OUTPUT_SCHEMA)
        responses = OpenAIResponsesCodec().request_body("m", history, [], 64, output_schema=OUTPUT_SCHEMA)
        self.assertEqual({"type": "json_schema", "json_schema": {"name": "quillframe_output", "strict": True, "schema": original}}, chat["response_format"])
        self.assertEqual({"format": {"type": "json_schema", "name": "quillframe_output", "strict": True, "schema": original}}, responses["text"])
        self.assertEqual(history, chat["messages"])
        self.assertNotIn("response_format", OpenAIChatCodec().request_body("m", history, [], 64))
        self.assertNotIn("text", OpenAIResponsesCodec().request_body("m", history, [], 64))
        chat["response_format"]["json_schema"]["schema"]["properties"].clear()
        self.assertEqual(original, OUTPUT_SCHEMA)
        with self.assertRaisesRegex(ValueError, "not supported"):
            AnthropicMessagesCodec().request_body("m", history, [], 64, output_schema=OUTPUT_SCHEMA)

    def test_schema_transport_rejection_does_not_probe_retry_or_fall_back(self):
        endpoint = "https://api.example.test/v1"
        transport = MockTransport({
            ("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m", "protocol": "openai_chat_completions"}]}),
            ("POST", endpoint + "/chat/completions", "bearer"): response(400, {"error": "schema unsupported"}),
        })
        runtime = ModelRuntime(MemorySecretStore(), transport)
        snapshot = runtime.connect(endpoint, "t")
        with self.assertRaises(ModelRuntimeError) as error:
            runtime.invoke(snapshot.service_id, "m", [{"role": "user", "content": "Bounded judgment"}], [], output_schema=OUTPUT_SCHEMA)
        self.assertEqual("model_request_failed", error.exception.code)
        posts = [r for r in transport.requests if r["method"] == "POST"]
        self.assertEqual(1, len(posts))
        self.assertEqual(OUTPUT_SCHEMA, posts[0]["body"]["response_format"]["json_schema"]["schema"])
        self.assertNotEqual("verified", snapshot.models[0].capability_state("json_schema"))
        for invalid in ({"type": "object"}, {**OUTPUT_SCHEMA, "anyOf": []}):
            with self.assertRaises(ModelRuntimeError) as blocked:
                runtime.invoke(snapshot.service_id, "m", [], [], output_schema=invalid)
            self.assertEqual("model_output_schema_unsupported", blocked.exception.code)
        self.assertEqual(1, len([r for r in transport.requests if r["method"] == "POST"]))

    def test_unresolved_schema_protocol_cannot_issue_an_unbudgeted_probe(self):
        endpoint = "https://api.example.test/v1"
        transport = MockTransport({("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m"}]})})
        runtime = ModelRuntime(MemorySecretStore(), transport)
        service = runtime.connect(endpoint, "t")
        with self.assertRaises(ModelRuntimeError) as error:
            runtime.invoke(service.service_id, "m", [], [], output_schema=OUTPUT_SCHEMA)
        self.assertEqual("model_protocol_unresolved", error.exception.code)
        self.assertEqual(["GET"], [request["method"] for request in transport.requests])

    def test_protocol_normalization_keeps_refusal_distinct_from_valid_json(self):
        text = '{"status":"fail","report":"blocked"}'
        chat = OpenAIChatCodec().normalize("m", {"choices": [{"finish_reason": "stop", "message": {"content": text, "refusal": "refused"}}]})
        responses = OpenAIResponsesCodec().normalize("m", {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "refused"}, {"type": "output_text", "text": text}]}]})
        self.assertEqual("refusal", chat.finish_reason)
        self.assertEqual("refusal", responses.finish_reason)
        self.assertEqual(text, chat.text)
        self.assertEqual(text, responses.text)

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
