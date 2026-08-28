from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any

from model_runtime import ModelRuntime, ModelRuntimeError
from model_runtime.contracts import canonical_json
from model_runtime.deadlines import DEFAULT_REQUEST_TIMEOUT_SECONDS
from model_runtime.structured_output import validate_structured_text

from .contracts import AgentJob, AgentResult
from .hooks import AgentExecutionHooks
from .tools import ToolRuntime, ToolRuntimeError


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


def _usage_counts(usage: dict[str, Any]) -> tuple[int, int]:
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
    try:
        return max(0, int(input_tokens or 0)), max(0, int(output_tokens or 0))
    except (TypeError, ValueError):
        return 0, 0


@dataclass
class AgentRunner:
    model_runtime: ModelRuntime
    tool_runtime: ToolRuntime
    execution_hooks: AgentExecutionHooks | None = None

    def run(self, job: AgentJob, *, cancellation: CancellationToken | None = None) -> AgentResult:
        cancellation = cancellation or CancellationToken()
        started = time.monotonic()
        required = set(job.required_model_capabilities) | {"text"}
        if job.tool_grants:
            required.add("tool_calling")
        try:
            # A constrained production request must not add unbudgeted capability
            # probes. Requesting a schema is not evidence of provider support.
            model = self.model_runtime.select_model(job.service_id, required, preference=job.model_preference, allow_probe=job.output_schema is None)
        except ModelRuntimeError as exc:
            return self._result(job, "model_failed", "", "", "", 0, 0, 0, [], {}, [{"code": exc.code, "message": str(exc), "detail": exc.detail}])

        protocol = model.protocol or "unknown"
        history: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are executing one bounded Quillframe AgentJob. Quillframe owns tools, permissions, authority, budgets, "
                    "session state and durable side effects. Use only the supplied tools. Never claim a tool succeeded unless its "
                    "tool result says so. Do not expose private chain-of-thought or credentials."
                ),
            },
            {"role": "user", "content": job.instruction + ("\n\nBounded context:\n" + canonical_json(job.context) if job.context else "")},
        ]
        model_tools = self.tool_runtime.model_tools(job.tool_grants)
        receipts: list[dict[str, Any]] = []
        steps = model_requests = tool_calls = 0
        total_input = total_output = 0
        final_text = ""

        while True:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if cancellation.cancelled:
                return self._result(job, "cancelled", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [])
            if elapsed_ms >= job.budgets.max_elapsed_ms or steps >= job.budgets.max_steps or model_requests >= job.budgets.max_model_requests:
                return self._result(job, "budget_exhausted", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "agent_budget_exhausted", "elapsed_ms": elapsed_ms}])
            if total_input + total_output >= job.budgets.max_total_tokens:
                return self._result(job, "budget_exhausted", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "token_budget_exhausted"}])

            steps += 1
            model_requests += 1
            try:
                output_options = {"output_schema": job.output_schema} if job.output_schema is not None else {}
                request_timeout = (DEFAULT_REQUEST_TIMEOUT_SECONDS if job.budgets.max_model_request_ms is None
                                   else job.budgets.max_model_request_ms / 1000.0)
                turn = self.model_runtime.invoke(job.service_id, model.model_id, history, model_tools,
                    max_output_tokens=job.budgets.max_output_tokens_per_request,
                    timeout_seconds=min(request_timeout, (job.budgets.max_elapsed_ms - elapsed_ms) / 1000.0),
                    **output_options)
            except ModelRuntimeError as exc:
                return self._result(job, "model_failed", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": exc.code, "message": str(exc), "detail": exc.detail}])

            protocol = turn.protocol
            in_tokens, out_tokens = _usage_counts(turn.usage)
            total_input += in_tokens
            total_output += out_tokens
            if cancellation.cancelled:
                return self._result(job, "cancelled", "", model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [])
            if int((time.monotonic() - started) * 1000) >= job.budgets.max_elapsed_ms:
                return self._result(job, "budget_exhausted", "", model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "elapsed_budget_exhausted_after_response"}])
            if turn.text:
                final_text = turn.text
            if total_input + total_output > job.budgets.max_total_tokens:
                return self._result(job, "budget_exhausted", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "token_budget_exhausted_after_response"}])

            if not turn.tool_calls:
                if job.output_schema is not None:
                    try:
                        if turn.finish_reason not in {"stop", "completed"}:
                            raise ValueError("structured response was not a complete non-refusal turn")
                        validate_structured_text(final_text, job.output_schema)
                    except (ValueError, TypeError, RecursionError) as exc:
                        # Preserve the exact received text in the failed result.
                        return self._result(job, "model_failed", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "model_output_schema_invalid", "message": str(exc)}])
                return self._result(job, "completed", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [])

            if len(turn.tool_calls) > job.budgets.max_parallel_tool_calls:
                return self._result(job, "budget_exhausted", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "parallel_tool_call_budget_exceeded", "requested": len(turn.tool_calls)}])
            if tool_calls + len(turn.tool_calls) > job.budgets.max_tool_calls:
                return self._result(job, "budget_exhausted", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "tool_call_budget_exhausted"}])

            history.append({
                "role": "assistant",
                "content": turn.text,
                "tool_calls": [c.to_dict() for c in turn.tool_calls],
                "opaque_continuation": turn.opaque_continuation,
            })
            for call in turn.tool_calls:
                if cancellation.cancelled:
                    return self._result(job, "cancelled", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [])
                per_call_idempotency = f"{job.idempotency_key}:{call.call_id}" if job.idempotency_key else None
                try:
                    spec = self.tool_runtime.spec(call.name)
                except ToolRuntimeError as exc:
                    return self._result(job, "tool_failed", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": exc.code, "message": str(exc), "tool_call_id": call.call_id}])

                checkpoint_ref: str | None = None
                if spec.side_effect:
                    if self.execution_hooks is None:
                        return self._result(job, "checkpoint_failed", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "checkpoint_required", "tool_call_id": call.call_id, "tool": call.name}])
                    try:
                        checkpoint_ref = self.execution_hooks.before_side_effect(job, call, spec, per_call_idempotency)
                    except Exception as exc:
                        return self._result(job, "checkpoint_failed", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "checkpoint_persist_failed", "message": str(exc), "tool_call_id": call.call_id, "tool": call.name}])

                try:
                    receipt = self.tool_runtime.execute(call.call_id, call.name, call.arguments, grants=job.tool_grants, authority=job.authority, idempotency_key=per_call_idempotency)
                except ToolRuntimeError as exc:
                    return self._result(job, "tool_failed", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": exc.code, "message": str(exc), "detail": exc.detail, "tool_call_id": call.call_id}])
                receipts.append(receipt)
                tool_calls += 1

                if spec.side_effect:
                    try:
                        assert checkpoint_ref is not None
                        self.execution_hooks.after_side_effect(job, call, checkpoint_ref, receipt)  # type: ignore[union-attr]
                    except Exception as exc:
                        return self._result(job, "side_effect_unconfirmed", final_text, model.model_id, protocol, steps, model_requests, tool_calls, receipts, {"input_tokens": total_input, "output_tokens": total_output}, [{"code": "side_effect_receipt_persist_failed", "message": str(exc), "tool_call_id": call.call_id, "tool": call.name, "checkpoint_ref": checkpoint_ref}])

                history.append({"role": "tool", "call_id": call.call_id, "content": json.dumps(receipt["output"], ensure_ascii=False, separators=(",", ":"))})

    @staticmethod
    def _result(job: AgentJob, status: str, final_text: str, model_id: str, protocol: str, steps: int, model_requests: int,
                tool_calls: int, receipts: list[dict[str, Any]], usage: dict[str, Any], errors: list[dict[str, Any] | str]) -> AgentResult:
        return AgentResult(
            job_id=job.job_id, session_id=job.session_id, run_id=job.run_id, status=status, final_text=final_text,
            model_service_id=job.service_id, model_id=model_id, protocol=protocol, input_fingerprint=job.input_fingerprint,
            steps=steps, model_requests=model_requests, tool_calls=tool_calls, tool_receipts=receipts, usage=usage, errors=errors,
        )
