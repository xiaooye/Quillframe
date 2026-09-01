from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any

from model_runtime import ModelRuntime, ModelRuntimeError
from model_runtime.contracts import canonical_json, fingerprint, model_version_fingerprint
from model_runtime.deadlines import DEFAULT_REQUEST_TIMEOUT_SECONDS
from model_runtime.structured_output import validate_structured_text

from .contracts import AgentJob, AgentResult
from .hooks import AgentExecutionHooks
from .tools import ToolRuntime, ToolRuntimeError

MAX_SQLITE_INTEGER = (1 << 63) - 1


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


def _usage_cost(usage: dict[str, Any]) -> tuple[int, bool]:
    for key in ("cost_micros", "cost_micro_usd", "total_cost_micros"):
        value = usage.get(key)
        if value is None:
            continue
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or value > MAX_SQLITE_INTEGER
        ):
            return 0, False
        return value, True
    return 0, False


def _usage_receipt(
    *, input_tokens: int, output_tokens: int, model_requests: int,
    total_cost: int, request_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return exact usage without inventing a zero-cost provider receipt."""

    if model_requests == 0:
        status = "no_model_request"
        authoritative = True
    else:
        authoritative = (
            len(request_receipts) == model_requests
            and [row.get("request_ordinal") for row in request_receipts]
            == list(range(1, model_requests + 1))
            and all(
                row.get("cost_reported") is True
                and isinstance(row.get("cost_micros"), int)
                and not isinstance(row.get("cost_micros"), bool)
                and 0 <= row["cost_micros"] <= MAX_SQLITE_INTEGER
                and isinstance(row.get("response_id_fingerprint"), str)
                and row["response_id_fingerprint"].startswith("sha256:")
                and isinstance(row.get("usage_fingerprint"), str)
                and row["usage_fingerprint"].startswith("sha256:")
                for row in request_receipts
            )
            and sum(row["cost_micros"] for row in request_receipts) == total_cost
            and total_cost <= MAX_SQLITE_INTEGER
        )
        status = "provider_confirmed" if authoritative else "reconciliation_required"
    receipt = {
        "schema": "quillframe_model_cost_receipt_v1",
        "status": status,
        "model_requests": model_requests,
        "cost_micros": total_cost if authoritative else None,
        "request_receipts": request_receipts,
    }
    receipt["receipt_fingerprint"] = fingerprint(receipt)
    usage: dict[str, Any] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "billing_receipt": receipt,
    }
    if authoritative:
        usage["cost_micros"] = total_cost
    elif total_cost:
        # A partial amount is diagnostic evidence only. It cannot authorize
        # another paid dispatch or be mistaken for the final charged amount.
        usage["observed_cost_micros"] = total_cost
    return usage


def _estimated_context_tokens(history: list[dict[str, Any]], tools: list[dict[str, Any]]) -> int:
    """Conservative provider-neutral pre-dispatch packing estimate.

    This is a mechanical context-limit guard, never a billing claim or prose
    judgment. Providers remain authoritative for actual usage receipts.
    """
    payload = canonical_json({"history": history, "tools": tools})
    return max(1, (len(payload.encode("utf-8")) + 3) // 4)


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
            model = self.model_runtime.select_model(
                job.service_id,
                required,
                preference=job.model_preference,
                # Capability discovery is a separate operation. A durable,
                # idempotent job cannot hide that extra provider request
                # outside its own request/billing journal.
                allow_probe=job.idempotency_key is None and job.output_schema is None,
            )
        except ModelRuntimeError as exc:
            return self._result(job, "model_failed", "", "", "", 0, 0, 0, [], {}, [{"code": exc.code, "message": str(exc), "detail": exc.detail}])

        selected_model_id = model.model_id
        selected_protocol = model.protocol
        selected_model_version_fingerprint = model_version_fingerprint(job.service_id, model)
        selected_model_identity_strength = "selected_model_descriptor"

        def finish(
            status: str,
            final_text: str,
            protocol_value: str,
            steps: int,
            model_requests: int,
            tool_calls: int,
            receipts: list[dict[str, Any]],
            usage: dict[str, Any],
            errors: list[dict[str, Any] | str],
        ) -> AgentResult:
            return self._result(
                job, status, final_text, selected_model_id, protocol_value, steps,
                model_requests, tool_calls, receipts, usage, errors,
                version_fingerprint=selected_model_version_fingerprint,
                version_identity_strength=selected_model_identity_strength,
            )
        if not selected_protocol:
            return finish(
                "model_failed", "", "unknown", 0, 0, 0, [],
                _usage_receipt(
                    input_tokens=0,
                    output_tokens=0,
                    model_requests=0,
                    total_cost=0,
                    request_receipts=[],
                ),
                [{
                    "code": "model_protocol_unresolved",
                    "message": "selected model has no verified protocol; implicit probing is not a production request",
                }],
            )
        protocol = selected_protocol
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
        total_input = total_output = total_cost = 0
        request_receipts: list[dict[str, Any]] = []
        final_text = ""

        def current_usage() -> dict[str, Any]:
            return _usage_receipt(
                input_tokens=total_input,
                output_tokens=total_output,
                model_requests=model_requests,
                total_cost=total_cost,
                request_receipts=list(request_receipts),
            )

        while True:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if cancellation.cancelled:
                return finish("cancelled", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [])
            if elapsed_ms >= job.budgets.max_elapsed_ms or steps >= job.budgets.max_steps or model_requests >= job.budgets.max_model_requests:
                return finish("budget_exhausted", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "agent_budget_exhausted", "elapsed_ms": elapsed_ms}])
            if total_cost >= job.budgets.run_cost_budget:
                return finish("budget_exhausted", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "run_cost_budget_exhausted"}])
            estimated_context = _estimated_context_tokens(history, model_tools)
            if estimated_context > job.budgets.model_context_limit:
                return finish("budget_exhausted", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "model_context_limit_exceeded", "estimated_context_tokens": estimated_context}])

            steps += 1
            model_requests += 1
            try:
                output_options = {"output_schema": job.output_schema} if job.output_schema is not None else {}
                request_timeout = (DEFAULT_REQUEST_TIMEOUT_SECONDS if job.budgets.max_model_request_ms is None
                                   else job.budgets.max_model_request_ms / 1000.0)
                turn = self.model_runtime.invoke(job.service_id, selected_model_id, history, model_tools,
                    max_output_tokens=job.budgets.max_output_tokens,
                    timeout_seconds=min(request_timeout, (job.budgets.max_elapsed_ms - elapsed_ms) / 1000.0),
                    request_key=(f"{job.idempotency_key}:model:{model_requests}" if job.idempotency_key else None),
                    expected_model_version_fingerprint=selected_model_version_fingerprint,
                    **output_options)
            except ModelRuntimeError as exc:
                status = "model_pending" if exc.code == "model_pending" else "model_failed"
                return finish(status, final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": exc.code, "message": str(exc), "detail": exc.detail}])

            protocol = turn.protocol
            in_tokens, out_tokens = _usage_counts(turn.usage)
            total_input += in_tokens
            total_output += out_tokens
            turn_cost, cost_reported = _usage_cost(turn.usage)
            total_cost += turn_cost
            request_receipts.append({
                "request_ordinal": model_requests,
                "response_id_fingerprint": fingerprint(turn.response_id) if turn.response_id else None,
                "usage_fingerprint": fingerprint(turn.usage),
                "cost_reported": cost_reported,
                "cost_micros": turn_cost if cost_reported else None,
            })
            if cancellation.cancelled:
                return finish("cancelled", "", protocol, steps, model_requests, tool_calls, receipts, current_usage(), [])
            if turn.text:
                final_text = turn.text

            if not turn.tool_calls:
                if job.output_schema is not None:
                    try:
                        if turn.finish_reason not in {"stop", "completed"}:
                            raise ValueError("structured response was not a complete non-refusal turn")
                        validate_structured_text(final_text, job.output_schema)
                    except (ValueError, TypeError, RecursionError) as exc:
                        # Preserve the exact received text in the failed result.
                        return finish("model_failed", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "model_output_schema_invalid", "message": str(exc)}])
                return finish("completed", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [])

            if len(turn.tool_calls) > job.budgets.max_parallel_tool_calls:
                return finish("budget_exhausted", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "parallel_tool_call_budget_exceeded", "requested": len(turn.tool_calls)}])
            if tool_calls + len(turn.tool_calls) > job.budgets.max_tool_calls:
                return finish("budget_exhausted", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "tool_call_budget_exhausted"}])

            history.append({
                "role": "assistant",
                "content": turn.text,
                "tool_calls": [c.to_dict() for c in turn.tool_calls],
                "opaque_continuation": turn.opaque_continuation,
            })
            for call in turn.tool_calls:
                if cancellation.cancelled:
                    return finish("cancelled", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [])
                per_call_idempotency = f"{job.idempotency_key}:{call.call_id}" if job.idempotency_key else None
                try:
                    spec = self.tool_runtime.spec(call.name)
                except ToolRuntimeError as exc:
                    return finish("tool_failed", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": exc.code, "message": str(exc), "tool_call_id": call.call_id}])

                checkpoint_ref: str | None = None
                if spec.side_effect:
                    if self.execution_hooks is None:
                        return finish("checkpoint_failed", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "checkpoint_required", "tool_call_id": call.call_id, "tool": call.name}])
                    try:
                        checkpoint_ref = self.execution_hooks.before_side_effect(job, call, spec, per_call_idempotency)
                    except Exception as exc:
                        return finish("checkpoint_failed", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "checkpoint_persist_failed", "message": str(exc), "tool_call_id": call.call_id, "tool": call.name}])

                try:
                    receipt = self.tool_runtime.execute(call.call_id, call.name, call.arguments, grants=job.tool_grants, authority=job.authority, idempotency_key=per_call_idempotency)
                except ToolRuntimeError as exc:
                    return finish("tool_failed", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": exc.code, "message": str(exc), "detail": exc.detail, "tool_call_id": call.call_id}])
                receipts.append(receipt)
                tool_calls += 1

                if spec.side_effect:
                    try:
                        assert checkpoint_ref is not None
                        self.execution_hooks.after_side_effect(job, call, checkpoint_ref, receipt)  # type: ignore[union-attr]
                    except Exception as exc:
                        return finish("side_effect_unconfirmed", final_text, protocol, steps, model_requests, tool_calls, receipts, current_usage(), [{"code": "side_effect_receipt_persist_failed", "message": str(exc), "tool_call_id": call.call_id, "tool": call.name, "checkpoint_ref": checkpoint_ref}])

                history.append({"role": "tool", "call_id": call.call_id, "content": json.dumps(receipt["output"], ensure_ascii=False, separators=(",", ":"))})

    def _result(self, job: AgentJob, status: str, final_text: str, model_id: str, protocol: str, steps: int, model_requests: int,
                tool_calls: int, receipts: list[dict[str, Any]], usage: dict[str, Any], errors: list[dict[str, Any] | str],
                *, version_fingerprint: str | None = None,
                version_identity_strength: str | None = None) -> AgentResult:
        return AgentResult(
            job_id=job.job_id, session_id=job.session_id, run_id=job.run_id, status=status, final_text=final_text,
            model_service_id=job.service_id, model_id=model_id, protocol=protocol, input_fingerprint=job.input_fingerprint,
            model_version_fingerprint=version_fingerprint,
            model_version_identity_strength=version_identity_strength,
            steps=steps, model_requests=model_requests, tool_calls=tool_calls, tool_receipts=receipts, usage=usage, errors=errors,
        )
