from __future__ import annotations

import tempfile
import json
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from agent_runtime import AgentBudget, AgentJob, AgentRunner, ControlPlaneExecutionHooks, ToolRuntime, ToolSpec
from harness.control_plane.control_plane import ControlPlane
from harness.session_runtime.session_runtime import new_session, start_run
from model_runtime import CapabilityEvidence, DiscoveredModel, ModelTurn, ToolCall, TransportError, UrllibTransport
from model_runtime.contracts import now_iso
from model_runtime.transport import _NoRedirect
from model_runtime.contracts import fingerprint


class FakeModelRuntime:
    def __init__(self, turns: list[ModelTurn]) -> None:
        self.turns = list(turns)
        self.timeouts = []
        self.output_schemas = []
        self.selection_probe_flags = []
        stamp = now_iso()
        self.model = DiscoveredModel(
            "fixture-model",
            protocol="openai_chat_completions",
            capabilities={
                "text": CapabilityEvidence("text", "verified", "verified", stamp),
                "tool_calling": CapabilityEvidence("tool_calling", "verified", "verified", stamp),
            },
        )

    def select_model(self, service_id, requirements, *, preference=None, allow_probe=True):  # noqa: ANN001
        self.selection_probe_flags.append(allow_probe)
        return self.model

    def invoke(self, service_id, model_id, history, tools, *, max_output_tokens=2048, timeout_seconds=180.0, output_schema=None):  # noqa: ANN001
        self.timeouts.append(timeout_seconds)
        self.output_schemas.append(output_schema)
        if not self.turns:
            raise AssertionError("fixture model invoked too many times")
        return self.turns.pop(0)


class TransportSecurityTests(unittest.TestCase):
    def test_dns_resolved_private_address_is_denied(self):
        transport = UrllibTransport(allow_loopback=True, allow_private_network=False)
        fake = [(2, 1, 6, "", ("169.254.169.254", 443))]
        with patch("model_runtime.transport.socket.getaddrinfo", return_value=fake):
            with self.assertRaises(TransportError) as denied:
                transport._validate_destination("https://example.test/v1/models")
        self.assertEqual(denied.exception.code, "private_destination_denied")

    def test_loopback_and_explicit_private_policy(self):
        loopback = UrllibTransport(allow_loopback=True, allow_private_network=False)
        with patch("model_runtime.transport.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 11434))]):
            loopback._validate_destination("http://localhost:11434/v1/models")
        private = UrllibTransport(allow_loopback=True, allow_private_network=True)
        with patch("model_runtime.transport.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("192.168.1.10", 1234))]):
            private._validate_destination("http://models.lan:1234/v1/models")

    def test_redirect_handler_refuses_followup_request(self):
        handler = _NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://other.test/v1"))


class SideEffectCheckpointTests(unittest.TestCase):
    def _job(self) -> AgentJob:
        return AgentJob(
            "JOB-GUARD",
            "SES-GUARD",
            "RUN-GUARD",
            "SYSTEM-IMPROVE",
            "coding_implementer",
            "SERVICE-GUARD",
            "Perform the bounded write.",
            tool_grants={"fixture.write"},
            required_model_capabilities={"text", "tool_calling"},
            authority={"filesystem_write": True},
            budgets=AgentBudget(max_steps=4, max_model_requests=4, max_tool_calls=2, max_parallel_tool_calls=1, max_output_tokens_per_request=64, max_total_tokens=1000, max_elapsed_ms=30000),
            idempotency_key="JOB-GUARD-IDEM",
        )

    def test_side_effect_never_executes_without_checkpoint_hook(self):
        executed = {"value": False}
        tools = ToolRuntime(host_capabilities={"filesystem_write"})

        def handler(args):  # noqa: ANN001
            executed["value"] = True
            return {"ok": True}

        tools.register(ToolSpec(
            "fixture.write",
            "fixture",
            {"type": "object", "additionalProperties": False, "required": ["value"], "properties": {"value": {"type": "string"}}},
            handler,
            "filesystem_write",
            required_authority="filesystem_write",
            side_effect=True,
            idempotency_required=True,
        ))
        model = FakeModelRuntime([
            ModelTurn("openai_chat_completions", "fixture-model", tool_calls=[ToolCall("CALL-1", "fixture.write", {"value": "x"})]),
        ])
        result = AgentRunner(model, tools).run(self._job())
        self.assertEqual(result.status, "checkpoint_failed")
        self.assertEqual(result.errors[0]["code"], "checkpoint_required")
        self.assertFalse(executed["value"])

    def test_optional_schema_binds_new_jobs_without_changing_legacy_fingerprints(self):
        legacy = self._job()
        payload = legacy.to_dict(include_fingerprint=False)
        self.assertNotIn("output_schema", payload)
        self.assertEqual(fingerprint(payload), replace(legacy, output_schema=None).input_fingerprint)
        schema = {"type": "object", "properties": {"verdict": {"type": "string"}}, "required": ["verdict"], "additionalProperties": False}
        with self.assertRaisesRegex(ValueError, "tool-free"):
            replace(legacy, output_schema=schema)
        constrained = replace(legacy, tool_grants=set(), required_model_capabilities={"text"}, output_schema=schema)
        self.assertEqual(schema, constrained.to_dict()["output_schema"])
        self.assertNotEqual(constrained.input_fingerprint, replace(constrained, output_schema=None).input_fingerprint)
        narrowed = {**schema, "properties": {"verdict": {"type": "string", "enum": ["fail"]}}}
        self.assertNotEqual(constrained.input_fingerprint, replace(constrained, output_schema=narrowed).input_fingerprint)

    def test_schema_job_sends_explicit_constraint_and_preserves_a_valid_failure_verdict(self):
        schema = {"type": "object", "properties": {"verdict": {"type": "string", "enum": ["pass", "fail"]}}, "required": ["verdict"], "additionalProperties": False}
        job = replace(self._job(), tool_grants=set(), required_model_capabilities={"text"}, output_schema=schema)
        text = ' {"verdict":"fail"}\n'
        model = FakeModelRuntime([ModelTurn("openai_chat_completions", "fixture-model", text=text, finish_reason="stop")])
        result = AgentRunner(model, ToolRuntime()).run(job)
        self.assertEqual("completed", result.status)
        self.assertEqual(text, result.final_text)
        self.assertEqual([schema], model.output_schemas)
        self.assertEqual([False], model.selection_probe_flags)
        self.assertEqual(1, result.model_requests)

    def test_invalid_truncated_or_refused_schema_output_is_preserved_without_retry(self):
        schema = {"type": "object", "properties": {"verdict": {"type": "string"}}, "required": ["verdict"], "additionalProperties": False}
        job = replace(self._job(), tool_grants=set(), required_model_capabilities={"text"}, output_schema=schema)
        good = json.dumps({"verdict": "fail"})
        for text, reason in ((good + "]}", "stop"), (good, "length"), (good, "incomplete"), (good, "refusal"), (good, None)):
            with self.subTest(reason=reason, text=text):
                model = FakeModelRuntime([ModelTurn("openai_chat_completions", "fixture-model", text=text, finish_reason=reason)])
                result = AgentRunner(model, ToolRuntime()).run(job)
                self.assertEqual("model_failed", result.status)
                self.assertEqual("model_output_schema_invalid", result.errors[0]["code"])
                self.assertEqual(text, result.final_text)
                self.assertEqual(1, result.model_requests)
                self.assertEqual(1, len(model.output_schemas))

    def test_model_request_deadline_uses_remaining_job_budget_and_discards_late_output(self):
        model = FakeModelRuntime([ModelTurn('openai_chat_completions', 'fixture-model', text='late private result')])
        with patch('agent_runtime.runner.time.monotonic', side_effect=[100.0, 101.0, 131.0]):
            result = AgentRunner(model, ToolRuntime()).run(self._job())
        self.assertEqual(model.timeouts, [29.0])
        self.assertEqual(result.status, 'budget_exhausted')
        self.assertEqual(result.final_text, '')
        self.assertEqual(result.model_requests, 1)

    def test_cancel_during_model_call_does_not_release_returned_text(self):
        from agent_runtime.runner import CancellationToken
        cancellation = CancellationToken()
        model = FakeModelRuntime([ModelTurn('openai_chat_completions', 'fixture-model', text='unreleased text')])
        original = model.invoke
        def invoke(*args, **kwargs):
            cancellation.cancel()
            return original(*args, **kwargs)
        model.invoke = invoke
        result = AgentRunner(model, ToolRuntime()).run(self._job(), cancellation=cancellation)
        self.assertEqual(result.status, 'cancelled')
        self.assertEqual(result.final_text, '')

    def test_control_plane_hook_persists_before_after_and_consume_once(self):
        with tempfile.TemporaryDirectory() as td:
            cp = ControlPlane(Path(td) / "runtime.db")
            cp.init()
            session = new_session(
                "FRAMEWORK",
                "manager",
                "model_api",
                "quillframe_agent_runtime",
                task_mode="SYSTEM-IMPROVE",
                usage_class="api_metered",
                memory_policy="bounded",
                resume_policy="checkpoint_revalidate",
            )
            session["session_id"] = "SES-GUARD"
            session = start_run(session, "RUN-GUARD", [])
            cp.put_session(session, expected_version=0)

            hooks = ControlPlaneExecutionHooks(cp)
            job = self._job()
            call = ToolCall("CALL-1", "fixture.write", {"value": "x"})
            spec = ToolSpec(
                "fixture.write", "fixture",
                {"type": "object", "properties": {"value": {"type": "string"}}},
                lambda args: args,
                "filesystem_write",
                required_authority="filesystem_write",
                side_effect=True,
                idempotency_required=True,
            )
            checkpoint_ref = hooks.before_side_effect(job, call, spec, "JOB-GUARD-IDEM:CALL-1")
            first = cp.get_session("SES-GUARD")
            self.assertEqual(first["session"]["checkpoints"][-1]["checkpoint_id"], checkpoint_ref)
            self.assertEqual(first["session"]["checkpoints"][-1]["pending_gate"], "agent_tool:CALL-1")

            receipt = {
                "tool_call_id": "CALL-1",
                "tool": "fixture.write",
                "arguments_fingerprint": "sha256:" + "a" * 64,
                "output_fingerprint": "sha256:" + "b" * 64,
                "authority": False,
            }
            hooks.after_side_effect(job, call, checkpoint_ref, receipt)
            second = cp.get_session("SES-GUARD")
            self.assertEqual(second["session"]["checkpoints"][-1]["pending_gate"], None)
            duplicate = cp.consume_once("agent_tool", "RUN-GUARD:CALL-1", "agent_runtime", receipt["output_fingerprint"])
            self.assertTrue(duplicate["already_consumed"])


if __name__ == "__main__":
    unittest.main()
