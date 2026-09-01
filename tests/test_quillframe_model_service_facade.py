from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_runtime import QuillframeAgentRuntime
from model_runtime import MemorySecretStore, MockTransport, ModelRuntimeError, TransportError, TransportResponse
from model_runtime.service_facade import ModelServiceFacade
from persistence.quillframe_sqlite import QuillframeStore


def response(status: int, body: dict | list | None) -> TransportResponse:
    return TransportResponse(status, {}, body, json.dumps(body) if body is not None else "")


class FailingTransport:
    def request_json(self, method, url, *, token, auth_style, body=None, timeout=30.0,
                     request_key=None):  # noqa: ANN001
        raise TransportError("network_request_failed", "fixture network failure")


class ModelServiceFacadeTests(unittest.TestCase):
    def test_only_the_exact_loopback_chat_relay_is_durable_request_keyed(self):
        endpoint = "http://127.0.0.1:8765/v1"
        routes = {
            ("GET", endpoint + "/models", "none"): response(200, {"data": [{
                "id": "quillframe-chat-host-relay", "protocol": "openai_chat_completions",
            }]}),
        }
        with tempfile.TemporaryDirectory() as td:
            runtime = QuillframeAgentRuntime(
                secret_store=MemorySecretStore(), transport=MockTransport(routes),
                store=QuillframeStore(Path(td)),
            )
            service_id = ModelServiceFacade(runtime).connect(endpoint, "")["service_id"]
            self.assertTrue(runtime.supports_durable_model_request(
                service_id, "quillframe-chat-host-relay",
            ))
            self.assertFalse(runtime.supports_durable_model_request(service_id, "another-model"))

    def test_endpoint_token_discovery_probe_and_capabilities_are_secret_safe(self):
        endpoint = "https://api.example.test/v1"
        routes = {
            ("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m", "protocol": "openai_chat_completions"}]}),
            ("POST", endpoint + "/chat/completions", "bearer"): [
                response(200, {"choices": [{"finish_reason": "stop", "message": {"content": "OK"}}]}),
                response(200, {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [{"id": "p", "function": {"name": "quillframe_capability_probe", "arguments": "{\"value\":\"ok\"}"}}]}}]}),
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            store = QuillframeStore(Path(td))
            secrets = MemorySecretStore()
            runtime = QuillframeAgentRuntime(secret_store=secrets, transport=MockTransport(routes), store=store)
            facade = ModelServiceFacade(runtime)
            service = facade.connect(endpoint, "TOP-SECRET")
            service_id = service["service_id"]
            public = json.dumps(service)
            self.assertNotIn("TOP-SECRET", public)
            self.assertNotIn("credential_ref", public)
            tested = facade.test(service_id, model_id="m", verify_tools=True)
            self.assertEqual(tested["status"], "verified")
            caps = facade.capabilities(service_id)
            serialized = json.dumps(caps)
            self.assertNotIn("TOP-SECRET", serialized)
            self.assertNotIn("credential_ref", serialized)
            model = caps["models"][0]
            self.assertEqual(model["capabilities"]["text"]["state"], "verified")
            self.assertEqual(model["capabilities"]["tool_calling"]["state"], "verified")
            self.assertFalse(caps["capability_grants_authority"])
            self.assertFalse(caps["authority"])

    def test_unknown_capability_remains_unknown_not_supported(self):
        endpoint = "https://api.example.test/v1"
        with tempfile.TemporaryDirectory() as td:
            runtime = QuillframeAgentRuntime(
                secret_store=MemorySecretStore(),
                transport=MockTransport({("GET", endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m"}]})}),
                store=QuillframeStore(Path(td)),
            )
            facade = ModelServiceFacade(runtime)
            service_id = facade.connect(endpoint, "t")["service_id"]
            caps = facade.capabilities(service_id)
            self.assertEqual(caps["models"][0]["capabilities"], {})
            self.assertFalse(caps["unknown_is_not_supported"])

    def test_bad_endpoint_bad_token_network_and_unsupported_protocol_are_truthful_failures(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                ModelServiceFacade(QuillframeAgentRuntime(secret_store=MemorySecretStore(), transport=MockTransport({}), store=QuillframeStore(Path(td) / "bad"))).connect("ftp://bad.example/v1", "x")

            endpoint = "https://auth.example.test/v1"
            auth_routes = {
                ("GET", endpoint + "/models", "bearer"): response(401, {"error": "unauthorized"}),
                ("GET", endpoint + "/models", "x_api_key"): response(401, {"error": "unauthorized"}),
                ("GET", endpoint + "/models", "none"): response(401, {"error": "unauthorized"}),
            }
            auth = ModelServiceFacade(QuillframeAgentRuntime(secret_store=MemorySecretStore(), transport=MockTransport(auth_routes), store=QuillframeStore(Path(td) / "auth")))
            with self.assertRaises(ModelRuntimeError) as bad_token:
                auth.connect(endpoint, "wrong")
            self.assertEqual(bad_token.exception.code, "model_discovery_failed")

            network = ModelServiceFacade(QuillframeAgentRuntime(secret_store=MemorySecretStore(), transport=FailingTransport(), store=QuillframeStore(Path(td) / "network")))
            with self.assertRaises(ModelRuntimeError) as net:
                network.connect("https://network.example.test/v1", "t")
            self.assertEqual(net.exception.code, "network_request_failed")

            unsupported_endpoint = "https://unknown.example.test/v1"
            unsupported_routes = {
                ("GET", unsupported_endpoint + "/models", "bearer"): response(200, {"data": [{"id": "m"}]}),
                ("POST", unsupported_endpoint + "/chat/completions", "bearer"): response(404, {}),
                ("POST", unsupported_endpoint + "/responses", "bearer"): response(404, {}),
                ("POST", unsupported_endpoint + "/messages", "bearer"): response(404, {}),
            }
            unsupported = ModelServiceFacade(QuillframeAgentRuntime(secret_store=MemorySecretStore(), transport=MockTransport(unsupported_routes), store=QuillframeStore(Path(td) / "unsupported")))
            service_id = unsupported.connect(unsupported_endpoint, "t")["service_id"]
            with self.assertRaises(ModelRuntimeError) as protocol:
                unsupported.test(service_id, model_id="m")
            self.assertEqual(protocol.exception.code, "model_protocol_unresolved")


if __name__ == "__main__":
    unittest.main()
