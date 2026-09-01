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
from harness.semantic_workers.semantic_worker_router import validate_typed_value
from model_runtime import CapabilityEvidence, DiscoveredModel, ModelRuntimeError, ModelTurn, ToolCall, TransportError, UrllibTransport
from model_runtime.contracts import now_iso
from model_runtime.transport import _NoRedirect
from model_runtime.contracts import fingerprint, model_version_fingerprint


class FakeModelRuntime:
    def __init__(self, turns: list[ModelTurn]) -> None:
        self.turns = list(turns)
        self.timeouts = []
        self.output_schemas = []
        self.request_keys = []
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

    def invoke(self, service_id, model_id, history, tools, *, max_output_tokens=2048,
               timeout_seconds=180.0, output_schema=None, request_key=None,
               expected_model_version_fingerprint=None):  # noqa: ANN001
        self.timeouts.append(timeout_seconds)
        self.output_schemas.append(output_schema)
        self.request_keys.append(request_key)
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
            budgets=AgentBudget(max_steps=4, max_model_requests=4, max_tool_calls=2, max_parallel_tool_calls=1, model_context_limit=1000, max_output_tokens=64, run_cost_budget=1000, max_elapsed_ms=30000),
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

    def test_optional_request_deadline_preserves_the_exact_legacy_job_and_fingerprint(self):
        legacy = self._job()
        expected = {
            "schema": "quillframe_agent_job_v1", "job_id": "JOB-GUARD", "session_id": "SES-GUARD",
            "run_id": "RUN-GUARD", "task_mode": "SYSTEM-IMPROVE", "runtime_role": "coding_implementer",
            "service_id": "SERVICE-GUARD", "instruction": "Perform the bounded write.", "context": [],
            "tool_grants": ["fixture.write"], "model_preference": None,
            "required_model_capabilities": ["text", "tool_calling"], "authority": {"filesystem_write": True},
            "budgets": {"max_steps": 4, "max_model_requests": 4, "max_tool_calls": 2,
                        "max_parallel_tool_calls": 1, "model_context_limit": 1000,
                        "max_output_tokens": 64, "run_cost_budget": 1000, "max_elapsed_ms": 30000},
            "idempotency_key": "JOB-GUARD-IDEM",
        }
        self.assertEqual(expected, legacy.to_dict(include_fingerprint=False))
        self.assertEqual(fingerprint(expected), legacy.input_fingerprint)
        explicit_none = replace(legacy, budgets=replace(legacy.budgets, max_model_request_ms=None))
        self.assertEqual(legacy.to_dict(), explicit_none.to_dict())
        extended = replace(legacy, budgets=replace(legacy.budgets, max_model_request_ms=600000))
        expected["budgets"]["max_model_request_ms"] = 600000
        self.assertEqual(expected, extended.to_dict(include_fingerprint=False))
        self.assertEqual(fingerprint(expected), extended.input_fingerprint)
        self.assertNotEqual(legacy.input_fingerprint, extended.input_fingerprint)
        self.assertNotEqual(extended.input_fingerprint,
                            replace(extended, budgets=replace(extended.budgets, max_model_request_ms=180000)).input_fingerprint)

    def test_request_deadline_budget_and_public_schema_enforce_the_same_optional_integer_bound(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / "agent_runtime" / "agent_job.schema.json").read_text(encoding="utf-8"))
        self.assertNotIn("max_model_request_ms", schema["properties"]["budgets"]["required"])
        legacy = self._job()
        self.assertEqual([], validate_typed_value(legacy.to_dict(include_fingerprint=False), schema))
        for value in (1, 180000, 600000, 86400000):
            with self.subTest(value=value):
                job = replace(legacy, budgets=replace(legacy.budgets, max_model_request_ms=value))
                self.assertEqual([], validate_typed_value(job.to_dict(include_fingerprint=False), schema))
                self.assertEqual(value, job.budgets.to_dict()["max_model_request_ms"])
        for value in (True, False, 0, -1, 86400001, 10 ** 1000, 1.0, "86400000", float("nan"), float("inf"), [], {}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    replace(legacy.budgets, max_model_request_ms=value)
                payload = legacy.to_dict(include_fingerprint=False)
                payload["budgets"]["max_model_request_ms"] = value
                self.assertTrue(validate_typed_value(payload, schema))
        payload = legacy.to_dict(include_fingerprint=False)
        payload["budgets"]["max_model_request_ms"] = None
        self.assertTrue(validate_typed_value(payload, schema))

    def test_request_timeout_is_default_or_explicit_and_clamped_by_remaining_job_time(self):
        original_history = None
        for request_ms, elapsed_ms, expected in ((None, 900000, 180.0), (600000, 900000, 600.0),
                                                 (600000, 600000, 599.0), (600000, 30000, 29.0),
                                                 (120000, 900000, 120.0)):
            with self.subTest(request_ms=request_ms, elapsed_ms=elapsed_ms):
                job = self._job()
                job = replace(job, tool_grants=set(), required_model_capabilities={"text"},
                              budgets=replace(job.budgets, max_elapsed_ms=elapsed_ms, max_model_request_ms=request_ms))
                model = FakeModelRuntime([ModelTurn("openai_chat_completions", "fixture-model", text=" 原始返回\n")])
                with patch.object(model, "invoke", wraps=model.invoke) as invoke, \
                        patch("agent_runtime.runner.time.monotonic", side_effect=[100.0, 101.0, 102.0]):
                    result = AgentRunner(model, ToolRuntime()).run(job)
                self.assertEqual("completed", result.status)
                self.assertEqual(" 原始返回\n", result.final_text)
                self.assertEqual([expected], model.timeouts)
                self.assertEqual(1, result.model_requests)
                self.assertEqual(64, invoke.call_args.kwargs["max_output_tokens"])
                history = invoke.call_args.args[2]
                if original_history is None:
                    original_history = history
                self.assertEqual(original_history, history)

    def test_extended_request_preserves_valid_late_or_over_budget_output_but_honors_cancellation(self):
        from agent_runtime.runner import CancellationToken
        for failure in ("elapsed", "cancelled", "tokens"):
            with self.subTest(failure=failure):
                job = self._job()
                job = replace(job, tool_grants=set(), required_model_capabilities={"text"},
                              budgets=replace(job.budgets, max_elapsed_ms=600000, max_model_request_ms=600000))
                cancellation = CancellationToken()
                model = FakeModelRuntime([ModelTurn("openai_chat_completions", "fixture-model", text="bounded result",
                                                    usage={"input_tokens": 1001 if failure == "tokens" else 1})])
                original = model.invoke

                def invoke(*args, **kwargs):
                    if failure == "cancelled":
                        cancellation.cancel()
                    return original(*args, **kwargs)

                with patch.object(model, "invoke", side_effect=invoke), \
                        patch("agent_runtime.runner.time.monotonic", side_effect=[100.0, 101.0, 700.0 if failure == "elapsed" else 102.0]):
                    result = AgentRunner(model, ToolRuntime()).run(job, cancellation=cancellation)
                self.assertEqual("cancelled" if failure == "cancelled" else "completed", result.status)
                self.assertEqual([599.0], model.timeouts)
                self.assertEqual(1, result.model_requests)
                if failure == "cancelled":
                    self.assertEqual("", result.final_text)
                else:
                    self.assertEqual("bounded result", result.final_text)
                    self.assertEqual([], result.errors)

    def test_extended_request_failure_is_charged_once_without_retry(self):
        job = self._job()
        job = replace(job, tool_grants=set(), required_model_capabilities={"text"},
                      budgets=replace(job.budgets, max_elapsed_ms=600000, max_model_request_ms=600000))
        model = FakeModelRuntime([])
        with patch.object(model, "invoke", side_effect=ModelRuntimeError("request_deadline_exceeded", "timed out")) as invoke:
            result = AgentRunner(model, ToolRuntime()).run(job)
        self.assertEqual("model_failed", result.status)
        self.assertEqual("", result.final_text)
        self.assertEqual("request_deadline_exceeded", result.errors[0]["code"])
        self.assertEqual(1, result.model_requests)
        invoke.assert_called_once()

    def test_pending_model_result_preserves_stable_request_identity_for_polling(self):
        job = replace(
            self._job(), tool_grants=set(), required_model_capabilities={"text"},
            budgets=replace(self._job().budgets, max_model_requests=1),
        )
        model = FakeModelRuntime([])
        with patch.object(
            model, "invoke",
            side_effect=ModelRuntimeError(
                "model_pending", "still running",
                detail={"request_id": "req_" + "a" * 32, "automatic_retry": False},
            ),
        ) as invoke:
            result = AgentRunner(model, ToolRuntime()).run(job)
        self.assertEqual("model_pending", result.status)
        self.assertEqual("model_pending", result.errors[0]["code"])
        self.assertEqual("JOB-GUARD-IDEM:model:1", invoke.call_args.kwargs["request_key"])
        self.assertEqual(1, result.model_requests)

    def test_extended_deadline_does_not_increase_the_model_call_budget(self):
        job = self._job()
        job = replace(job, tool_grants={"fixture.echo"}, budgets=replace(
            job.budgets, max_model_request_ms=600000, max_elapsed_ms=900000, max_model_requests=1))
        tools = ToolRuntime(host_capabilities={"fixture_read"})
        tools.register(ToolSpec("fixture.echo", "Bounded fixture read", {"type": "object"},
                                lambda args: args, "fixture_read"))
        model = FakeModelRuntime([
            ModelTurn("openai_chat_completions", "fixture-model", tool_calls=[ToolCall("CALL-1", "fixture.echo", {})]),
            ModelTurn("openai_chat_completions", "fixture-model", text="must not be requested"),
        ])
        result = AgentRunner(model, tools).run(job)
        self.assertEqual("budget_exhausted", result.status)
        self.assertEqual(1, result.model_requests)
        self.assertEqual(1, result.tool_calls)
        self.assertEqual([600.0], model.timeouts)
        self.assertEqual(1, len(model.turns))

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

    def test_durable_unstructured_job_never_allows_an_unjournaled_capability_probe(self):
        job = replace(
            self._job(),
            tool_grants=set(),
            required_model_capabilities={"text"},
            output_schema=None,
        )
        model = FakeModelRuntime([
            ModelTurn("openai_chat_completions", "fixture-model", text="durable result")
        ])
        result = AgentRunner(model, ToolRuntime()).run(job)
        self.assertEqual("completed", result.status)
        self.assertEqual([False], model.selection_probe_flags)
        self.assertEqual(["JOB-GUARD-IDEM:model:1"], model.request_keys)
        self.assertEqual(1, result.model_requests)

    def test_unresolved_selected_protocol_fails_before_any_model_request(self):
        job = replace(
            self._job(),
            tool_grants=set(),
            required_model_capabilities={"text"},
        )
        model = FakeModelRuntime([
            ModelTurn("openai_chat_completions", "fixture-model", text="must not run")
        ])
        model.model.protocol = None
        result = AgentRunner(model, ToolRuntime()).run(job)
        self.assertEqual("model_failed", result.status)
        self.assertEqual("model_protocol_unresolved", result.errors[0]["code"])
        self.assertEqual(0, result.model_requests)
        self.assertEqual([], model.request_keys)
        self.assertEqual([False], model.selection_probe_flags)

    def test_result_keeps_the_exact_pre_dispatch_model_descriptor_identity(self):
        job = replace(
            self._job(),
            tool_grants=set(),
            required_model_capabilities={"text"},
        )
        model = FakeModelRuntime([
            ModelTurn("openai_chat_completions", "fixture-model", text="bound result")
        ])
        expected = model_version_fingerprint(job.service_id, model.model)
        original = model.invoke

        def invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            # Simulate a concurrent discovery refresh/removal after selection.
            # The returned result must remain bound to what was selected.
            model.model.metadata["provider_revision"] = "changed-after-dispatch"
            model.model.model_id = "changed-model-after-dispatch"
            return original(*args, **kwargs)

        with patch.object(model, "invoke", side_effect=invoke):
            result = AgentRunner(model, ToolRuntime()).run(job)
        self.assertEqual("completed", result.status)
        self.assertEqual("fixture-model", result.model_id)
        self.assertEqual(expected, result.model_version_fingerprint)
        self.assertEqual(
            "selected_model_descriptor",
            result.model_version_identity_strength,
        )
        self.assertNotEqual(
            model_version_fingerprint(job.service_id, model.model),
            result.model_version_fingerprint,
        )

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

    def test_model_request_deadline_uses_remaining_job_budget_and_preserves_late_output(self):
        model = FakeModelRuntime([ModelTurn('openai_chat_completions', 'fixture-model', text='late private result')])
        with patch('agent_runtime.runner.time.monotonic', side_effect=[100.0, 101.0, 131.0]):
            result = AgentRunner(model, ToolRuntime()).run(self._job())
        self.assertEqual(model.timeouts, [29.0])
        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.final_text, 'late private result')
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
