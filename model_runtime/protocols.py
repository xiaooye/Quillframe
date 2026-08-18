from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from .contracts import ModelTurn, ToolCall


def _tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    return {"name": tool["name"], "description": tool.get("description", ""), "parameters": tool["input_schema"]}


class ProtocolCodec(ABC):
    protocol: str
    surface: str
    auth_style: str

    @abstractmethod
    def request_body(self, model_id: str, history: list[dict[str, Any]], tools: list[dict[str, Any]], max_output_tokens: int) -> dict[str, Any]: ...

    @abstractmethod
    def normalize(self, model_id: str, payload: dict[str, Any]) -> ModelTurn: ...


class OpenAIChatCodec(ProtocolCodec):
    protocol = "openai_chat_completions"
    surface = "openai_chat_completions"
    auth_style = "bearer"

    def request_body(self, model_id: str, history: list[dict[str, Any]], tools: list[dict[str, Any]], max_output_tokens: int) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        for item in history:
            role = item["role"]
            if role in {"system", "user"}:
                messages.append({"role": role, "content": item.get("content", "")})
            elif role == "assistant":
                message: dict[str, Any] = {"role": "assistant", "content": item.get("content") or None}
                if item.get("tool_calls"):
                    message["tool_calls"] = [
                        {"id": c["call_id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["arguments"], ensure_ascii=False, separators=(",", ":"))}}
                        for c in item["tool_calls"]
                    ]
                messages.append(message)
            elif role == "tool":
                messages.append({"role": "tool", "tool_call_id": item["call_id"], "content": item.get("content", "")})
        body: dict[str, Any] = {"model": model_id, "messages": messages, "max_tokens": max_output_tokens}
        if tools:
            body["tools"] = [{"type": "function", "function": _tool_schema(t)} for t in tools]
        return body

    def normalize(self, model_id: str, payload: dict[str, Any]) -> ModelTurn:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("chat completions response has no choices")
        choice = choices[0]
        message = choice.get("message") or {}
        text = message.get("content") or ""
        calls: list[ToolCall] = []
        for raw in message.get("tool_calls") or []:
            fn = raw.get("function") or {}
            args = fn.get("arguments") or "{}"
            if isinstance(args, str):
                args = json.loads(args)
            if not isinstance(args, dict):
                raise ValueError("tool arguments must be object")
            calls.append(ToolCall(str(raw.get("id") or ""), str(fn.get("name") or ""), args))
        return ModelTurn(self.protocol, model_id, text=text, tool_calls=calls, finish_reason=choice.get("finish_reason"), usage=payload.get("usage") or {}, response_id=payload.get("id"))


class OpenAIResponsesCodec(ProtocolCodec):
    protocol = "openai_responses"
    surface = "openai_responses"
    auth_style = "bearer"

    def request_body(self, model_id: str, history: list[dict[str, Any]], tools: list[dict[str, Any]], max_output_tokens: int) -> dict[str, Any]:
        input_items: list[dict[str, Any]] = []
        instructions: list[str] = []
        for item in history:
            role = item["role"]
            if role == "system":
                instructions.append(item.get("content", ""))
            elif role == "user":
                input_items.append({"role": "user", "content": item.get("content", "")})
            elif role == "assistant":
                opaque = item.get("opaque_continuation")
                if isinstance(opaque, list):
                    input_items.extend(dict(output_item) for output_item in opaque if isinstance(output_item, dict))
                else:
                    if item.get("content"):
                        input_items.append({"role": "assistant", "content": item["content"]})
                    for call in item.get("tool_calls") or []:
                        input_items.append({"type": "function_call", "call_id": call["call_id"], "name": call["name"], "arguments": json.dumps(call["arguments"], ensure_ascii=False, separators=(",", ":"))})
            elif role == "tool":
                input_items.append({"type": "function_call_output", "call_id": item["call_id"], "output": item.get("content", "")})
        body: dict[str, Any] = {"model": model_id, "input": input_items, "max_output_tokens": max_output_tokens, "store": False}
        if instructions:
            body["instructions"] = "\n\n".join(instructions)
        if tools:
            body["tools"] = [{"type": "function", "name": t["name"], "description": t.get("description", ""), "parameters": t["input_schema"]} for t in tools]
        return body

    def normalize(self, model_id: str, payload: dict[str, Any]) -> ModelTurn:
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        output_items = [dict(item) for item in payload.get("output") or [] if isinstance(item, dict)]
        for item in output_items:
            if item.get("type") == "function_call":
                args = item.get("arguments") or "{}"
                if isinstance(args, str):
                    args = json.loads(args)
                if not isinstance(args, dict):
                    raise ValueError("function_call arguments must be object")
                calls.append(ToolCall(str(item.get("call_id") or item.get("id") or ""), str(item.get("name") or ""), args))
            for content in item.get("content") or []:
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                    text_parts.append(content["text"])
        if not text_parts and isinstance(payload.get("output_text"), str):
            text_parts.append(payload["output_text"])
        return ModelTurn(
            self.protocol, model_id, text="\n".join(text_parts), tool_calls=calls,
            finish_reason=payload.get("status"), usage=payload.get("usage") or {}, response_id=payload.get("id"),
            opaque_continuation=output_items,
        )


class AnthropicMessagesCodec(ProtocolCodec):
    protocol = "anthropic_messages"
    surface = "anthropic_messages"
    auth_style = "x_api_key"

    def request_body(self, model_id: str, history: list[dict[str, Any]], tools: list[dict[str, Any]], max_output_tokens: int) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        systems: list[str] = []
        pending_tool_results: list[dict[str, Any]] = []

        def flush_tool_results() -> None:
            nonlocal pending_tool_results
            if pending_tool_results:
                messages.append({"role": "user", "content": pending_tool_results})
                pending_tool_results = []

        for item in history:
            role = item["role"]
            if role == "tool":
                pending_tool_results.append({"type": "tool_result", "tool_use_id": item["call_id"], "content": item.get("content", "")})
                continue
            flush_tool_results()
            if role == "system":
                systems.append(item.get("content", "")); continue
            if role == "user":
                messages.append({"role": "user", "content": item.get("content", "")})
            elif role == "assistant":
                opaque = item.get("opaque_continuation")
                if isinstance(opaque, list):
                    blocks = [dict(block) for block in opaque if isinstance(block, dict)]
                else:
                    blocks: list[dict[str, Any]] = []
                    if item.get("content"):
                        blocks.append({"type": "text", "text": item["content"]})
                    for call in item.get("tool_calls") or []:
                        blocks.append({"type": "tool_use", "id": call["call_id"], "name": call["name"], "input": call["arguments"]})
                messages.append({"role": "assistant", "content": blocks})
        flush_tool_results()
        body: dict[str, Any] = {"model": model_id, "messages": messages, "max_tokens": max_output_tokens}
        if systems:
            body["system"] = "\n\n".join(systems)
        if tools:
            body["tools"] = [{"name": t["name"], "description": t.get("description", ""), "input_schema": t["input_schema"]} for t in tools]
        return body

    def normalize(self, model_id: str, payload: dict[str, Any]) -> ModelTurn:
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        content_blocks = [dict(item) for item in payload.get("content") or [] if isinstance(item, dict)]
        for item in content_blocks:
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                text_parts.append(item["text"])
            elif item.get("type") == "tool_use":
                args = item.get("input") or {}
                if not isinstance(args, dict):
                    raise ValueError("tool_use input must be object")
                calls.append(ToolCall(str(item.get("id") or ""), str(item.get("name") or ""), args))
        return ModelTurn(
            self.protocol, model_id, text="\n".join(text_parts), tool_calls=calls,
            finish_reason=payload.get("stop_reason"), usage=payload.get("usage") or {}, response_id=payload.get("id"),
            opaque_continuation=content_blocks,
        )


CODECS: dict[str, ProtocolCodec] = {
    "openai_chat_completions": OpenAIChatCodec(),
    "openai_responses": OpenAIResponsesCodec(),
    "anthropic_messages": AnthropicMessagesCodec(),
}
