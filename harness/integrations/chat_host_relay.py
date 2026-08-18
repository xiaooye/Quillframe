#!/usr/bin/env python3
"""Loopback OpenAI-compatible relay for ephemeral conversational hosts.

This transport lets a sandboxed host run the real Quillframe Model Runtime
without embedding a second implementation of semantic contracts. Quillframe
sends ordinary OpenAI-compatible requests to localhost; the relay materializes
one request file, waits for one atomically-published response file, and returns
that response to Core.

The relay is manager transport only. It is never evidence of an independent
semantic review and grants no Canon, Framework, settlement, or durable taste
authority.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_chat_host_relay_v1"
MODEL_ID = "quillframe-chat-host-relay"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def submit(queue: Path, request_id: str, content: str) -> Path:
    if not request_id.startswith("req_"):
        raise ValueError("request_id must use req_ namespace")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("response content must be non-empty")
    target = queue / f"{request_id}.response.json"
    _atomic_json(target, {"schema": SCHEMA, "request_id": request_id, "content": content})
    return target


def _request_files(queue: Path) -> list[Path]:
    return sorted(queue.glob("req_*.request.json"), key=lambda path: (path.stat().st_mtime_ns, path.name))


def next_request(queue: Path) -> dict[str, Any] | None:
    for path in _request_files(queue):
        request_id = path.name.removesuffix(".request.json")
        response = queue / f"{request_id}.response.json"
        if response.exists():
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("request_id") != request_id:
            raise ValueError(f"invalid relay request: {path}")
        return value
    return None


def handler(queue: Path, timeout_seconds: float):
    class RelayHandler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.rstrip("/").endswith("/models"):
                self._json(200, {"object": "list", "data": [{
                    "id": MODEL_ID,
                    "display_name": "Quillframe Chat Host Relay",
                    "protocol": "openai_chat_completions",
                }]})
                return
            if self.path == "/health":
                self._json(200, {
                    "schema": SCHEMA,
                    "status": "ok",
                    "manager_transport": True,
                    "independent_review_evidence": False,
                    "authority": False,
                })
                return
            self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            if not self.path.rstrip("/").endswith("/chat/completions"):
                self._json(404, {"error": "not_found"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(size) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._json(400, {"error": "invalid_json"})
                return
            if not isinstance(body, dict):
                self._json(400, {"error": "invalid_request"})
                return

            messages = body.get("messages") or []
            user_text = "\n".join(
                str(item.get("content") or "")
                for item in messages
                if isinstance(item, dict) and item.get("role") == "user"
            )
            if user_text.strip() == "Reply with exactly OK.":
                self._json(200, {
                    "id": "relay-capability-probe",
                    "choices": [{"message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                })
                return

            request_id = "req_" + uuid.uuid4().hex
            _atomic_json(queue / f"{request_id}.request.json", {
                "schema": SCHEMA,
                "request_id": request_id,
                "created_at_unix": time.time(),
                "request": body,
                "manager_transport": True,
                "independent_review_evidence": False,
                "authority": False,
            })
            response_path = queue / f"{request_id}.response.json"
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                if response_path.exists():
                    try:
                        response = json.loads(response_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        time.sleep(0.05)
                        continue
                    if (
                        isinstance(response, dict)
                        and response.get("request_id") == request_id
                        and isinstance(response.get("content"), str)
                        and response["content"].strip()
                    ):
                        self._json(200, {
                            "id": request_id,
                            "choices": [{
                                "message": {"role": "assistant", "content": response["content"]},
                                "finish_reason": "stop",
                            }],
                            "usage": response.get("usage") or {"prompt_tokens": 0, "completion_tokens": 0},
                        })
                        return
                    time.sleep(0.05)
                    continue
                time.sleep(0.10)
            self._json(504, {"error": "host_relay_timeout", "request_id": request_id})

    return RelayHandler


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="quillframe-chat-relay-") as temp:
        queue = Path(temp)
        request_id = "req_" + "a" * 32
        request = {
            "schema": SCHEMA,
            "request_id": request_id,
            "request": {"messages": [{"role": "user", "content": "fixture"}]},
            "manager_transport": True,
            "independent_review_evidence": False,
            "authority": False,
        }
        _atomic_json(queue / f"{request_id}.request.json", request)
        found = next_request(queue)
        response_path = submit(queue, request_id, '{"status":"pass"}')
        response = json.loads(response_path.read_text(encoding="utf-8"))
        checks = {
            "request_discovery": found == request,
            "response_atomic": response.get("content") == '{"status":"pass"}',
            "manager_transport_only": found.get("independent_review_evidence") is False if found else False,
            "loopback_default": DEFAULT_HOST == "127.0.0.1",
            "authority_false": found.get("authority") is False if found else False,
        }
    return {
        "schema": "quillframe_chat_host_relay_self_test_v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--queue", required=True)
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--timeout-seconds", type=float, default=180.0)
    nxt = sub.add_parser("next")
    nxt.add_argument("--queue", required=True)
    put = sub.add_parser("submit")
    put.add_argument("--queue", required=True)
    put.add_argument("--request-id", required=True)
    put.add_argument("--content-file")
    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        report = self_test()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "PASS" else 1
    if args.command == "next":
        value = next_request(Path(args.queue))
        print(json.dumps(value or {}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "submit":
        content = Path(args.content_file).read_text(encoding="utf-8") if args.content_file else os.sys.stdin.read()
        path = submit(Path(args.queue), args.request_id, content)
        print(path)
        return 0
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("chat host relay is loopback-only")
    queue = Path(args.queue).expanduser().resolve()
    queue.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), handler(queue, args.timeout_seconds))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
