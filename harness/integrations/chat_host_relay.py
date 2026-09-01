#!/usr/bin/env python3
"""Loopback OpenAI-compatible relay for ephemeral conversational hosts.

This transport lets a sandboxed host run the real Quillframe Model Runtime
without embedding a second implementation of semantic contracts. Quillframe
sends ordinary OpenAI-compatible requests to localhost; the relay materializes
one request file, waits for one exclusively-published response file, and returns
that response to Core.

The relay is manager transport only. It is never evidence of an independent
semantic review and grants no Canon, Framework, settlement, or durable taste
authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from model_runtime.deadlines import (
    DEADLINE_HEADER,
    DEFAULT_RELAY_RESPONSE_WAIT_SECONDS,
    DEFAULT_RELAY_TIMEOUT_SECONDS,
    MAX_RELAY_TIMEOUT_SECONDS,
    REQUEST_KEY_HEADER,
    RELAY_RESPONSE_RESERVE_SECONDS,
)

SCHEMA = "quillframe_chat_host_relay_v3"
MODEL_ID = "quillframe-chat-host-relay"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
# Deliberately narrow every published packet so sub-millisecond wall/monotonic
# drift during JSON encoding cannot look like a clock rollback or enlarge time.
PACKET_HANDOFF_MARGIN_SECONDS = 0.01


def _positive_finite(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid_deadline_number")
    try:
        number = float(value)
    except OverflowError:
        raise ValueError("invalid_deadline_number") from None
    if not math.isfinite(number) or number <= 0:
        raise ValueError("invalid_deadline_number")
    return number


def validate_server_timeout(value: Any) -> float:
    timeout = _positive_finite(value)
    if timeout > MAX_RELAY_TIMEOUT_SECONDS:
        raise ValueError("invalid_relay_timeout")
    return timeout


def validate_response_wait(value: Any) -> float:
    wait = _positive_finite(value)
    if wait > MAX_RELAY_TIMEOUT_SECONDS:
        raise ValueError("invalid_response_wait")
    return wait


def deadline_fields(created_at_unix: float, server_timeout_seconds: float,
                    caller_deadline_unix_ms: int | None) -> dict[str, Any]:
    """Freeze one request's bounds; a server cap never enlarges its caller."""
    created = _positive_finite(created_at_unix)
    server_timeout = validate_server_timeout(server_timeout_seconds)
    if caller_deadline_unix_ms is None:
        timeout = min(server_timeout, DEFAULT_RELAY_TIMEOUT_SECONDS)
    else:
        if type(caller_deadline_unix_ms) is not int:
            raise ValueError("invalid_caller_deadline")
        caller_deadline = _positive_finite(caller_deadline_unix_ms) / 1000.0
        timeout = min(server_timeout, caller_deadline - created - RELAY_RESPONSE_RESERVE_SECONDS)
    if timeout <= 0:
        raise ValueError("caller_deadline_exhausted")
    deadline = created + timeout
    if not math.isfinite(deadline) or deadline <= created:
        raise ValueError("invalid_request_deadline")
    return {
        "created_at_unix": created, "timeout_seconds": timeout,
        "deadline_at_unix": deadline, "server_timeout_seconds": server_timeout,
        "caller_deadline_unix_ms": caller_deadline_unix_ms,
    }


def validate_packet_deadline(packet: dict[str, Any]) -> dict[str, Any]:
    """Reject missing, non-finite, or inconsistent frozen v2 timing fields."""
    required = {"created_at_unix", "timeout_seconds", "deadline_at_unix",
                "server_timeout_seconds", "caller_deadline_unix_ms"}
    if not required.issubset(packet):
        raise ValueError("missing_request_deadline")
    expected = deadline_fields(packet["created_at_unix"], packet["server_timeout_seconds"],
                               packet["caller_deadline_unix_ms"])
    timeout = _positive_finite(packet["timeout_seconds"])
    deadline = _positive_finite(packet["deadline_at_unix"])
    if (timeout > expected["timeout_seconds"] or deadline <= expected["created_at_unix"]
            or deadline != expected["created_at_unix"] + timeout):
        raise ValueError("inconsistent_request_deadline")
    # A relay may narrow its original cap before handing the packet off. Every
    # consumer must use these actual bounds, never reconstruct a wider window.
    return {**expected, "timeout_seconds": timeout, "deadline_at_unix": deadline}


def is_durable_packet(packet: dict[str, Any]) -> bool:
    """Return whether one keyed v3 packet may outlive its HTTP waiter."""
    return (
        packet.get("schema") == SCHEMA
        and packet.get("durable_pending") is True
        and isinstance(packet.get("request_key_fingerprint"), str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", packet["request_key_fingerprint"]))
    )


def _atomic_json(path: Path, payload: dict[str, Any], *, before_publish: Callable[[], None] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if before_publish is not None:
        before_publish()
    os.replace(temp, path)


def _exclusive_json(path: Path, payload: dict[str, Any], *, before_publish: Callable[[], None] | None = None) -> None:
    """Publish one immutable packet without exposing partial JSON or replacing a peer."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        if before_publish is not None:
            before_publish()
        os.link(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def submit(queue: Path, request_id: str, content: str) -> Path:
    admitted_monotonic, admitted_unix = time.monotonic(), time.time()
    if not re.fullmatch(r"req_[0-9a-f]{32}", request_id):
        raise ValueError("request_id must use req_ namespace")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("response content must be non-empty")
    target = queue / f"{request_id}.response.json"
    packet = json.loads((queue / f"{request_id}.request.json").read_bytes())
    if not isinstance(packet, dict) or packet.get("schema") != SCHEMA or packet.get("request_id") != request_id:
        raise ValueError("invalid_request_identity")
    timing = validate_packet_deadline(packet)
    durable = is_durable_packet(packet)
    remaining = min(timing["timeout_seconds"], timing["deadline_at_unix"] - admitted_unix)
    raw = (json.dumps({"schema": SCHEMA, "request_id": request_id, "content": content},
                      ensure_ascii=False) + "\n").encode("utf-8")
    if not durable and min(timing["deadline_at_unix"] - time.time(),
                           admitted_monotonic + remaining - time.monotonic()) <= 0:
        raise ValueError("request_deadline_exhausted")
    # No replacement of an existing result, including a failed/late result.
    # The receiver retries incomplete JSON during this exclusive write.
    with target.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if not durable and min(timing["deadline_at_unix"] - time.time(),
                           admitted_monotonic + remaining - time.monotonic()) <= 0:
        # Keep late bytes as evidence, but never report a successful submission.
        raise ValueError("response_published_after_deadline")
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
        if value.get("schema") != SCHEMA:
            continue  # Historical packets are not an execution compatibility path.
        timing = validate_packet_deadline(value)
        if time.time() >= timing["deadline_at_unix"] and not is_durable_packet(value):
            continue
        return value
    return None


def handler(
    queue: Path,
    timeout_seconds: float,
    response_wait_seconds: float = DEFAULT_RELAY_RESPONSE_WAIT_SECONDS,
):
    server_timeout = validate_server_timeout(timeout_seconds)
    response_wait = validate_response_wait(response_wait_seconds)

    class RelayHandler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _json(self, status: int, payload: dict[str, Any], *,
                  deadline_remaining: Callable[[], float] | None = None) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            # Encoding a full assistant response is part of the original
            # allowance too; never begin a late HTTP success response.
            if deadline_remaining is not None and deadline_remaining() <= 0:
                error = {"error": "host_relay_timeout"}
                if isinstance(payload.get("id"), str):
                    error["request_id"] = payload["id"]
                self._json(504, error)
                return
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
            admitted_monotonic, created = time.monotonic(), time.time()
            values = self.headers.get_all(DEADLINE_HEADER, [])
            request_keys = self.headers.get_all(REQUEST_KEY_HEADER, [])
            try:
                if len(values) > 1 or (values and not re.fullmatch(r"[0-9]+", values[0])):
                    raise ValueError("invalid_caller_deadline")
                if len(request_keys) > 1 or (request_keys and not re.fullmatch(r"[0-9a-f]{64}", request_keys[0])):
                    raise ValueError("invalid_request_key")
                caller_deadline = int(values[0]) if values else None
                timing = deadline_fields(created, server_timeout, caller_deadline)
            except ValueError:
                self._json(400, {"error": "invalid_or_expired_caller_deadline"})
                return
            monotonic_deadline = admitted_monotonic + timing["timeout_seconds"]

            def remaining() -> float:
                return min(timing["deadline_at_unix"] - time.time(), monotonic_deadline - time.monotonic())

            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size < 0:
                    raise ValueError("negative_content_length")
                allowance = remaining()
                if allowance <= 0:
                    raise TimeoutError("request_deadline_exhausted")
                self.connection.settimeout(allowance)
                body = json.loads(self.rfile.read(size) or b"{}")
            except (TimeoutError, OSError):
                self._json(504, {"error": "host_relay_timeout"})
                return
            except (ValueError, json.JSONDecodeError):
                self._json(400, {"error": "invalid_json"})
                return
            if not isinstance(body, dict):
                self._json(400, {"error": "invalid_request"})
                return
            if remaining() <= 0:
                self._json(504, {"error": "host_relay_timeout"})
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
                }, deadline_remaining=remaining)
                return

            request_key = request_keys[0] if request_keys else None
            request_id = "req_" + (request_key[:32] if request_key else uuid.uuid4().hex)
            request_path = queue / f"{request_id}.request.json"
            response_path = queue / f"{request_id}.response.json"
            worker_state_path = queue / "worker-state" / f"{request_id}.json"
            packet_timing: dict[str, Any]
            durable_packet = False
            if request_path.exists():
                try:
                    packet = json.loads(request_path.read_text(encoding="utf-8"))
                    packet_timing = validate_packet_deadline(packet)
                except (OSError, ValueError, json.JSONDecodeError):
                    self._json(409, {"error": "model_request_state_invalid", "request_id": request_id})
                    return
                if (request_key is None or packet.get("schema") != SCHEMA
                        or packet.get("request_id") != request_id
                        or packet.get("request_key_fingerprint") != request_key
                        or packet.get("durable_pending") is not True
                        or packet.get("request") != body):
                    self._json(409, {"error": "model_request_idempotency_conflict", "request_id": request_id})
                    return
                durable_packet = is_durable_packet(packet)
                # The frozen deadline governs initial admission, not the
                # lifetime of an already launched keyed worker. A response or
                # worker-state record proves admission and remains joinable.
                if (time.time() >= packet_timing["deadline_at_unix"]
                        and not (durable_packet and (response_path.exists() or worker_state_path.exists()))):
                    self._json(504, {"error": "model_request_expired", "request_id": request_id})
                    return
            else:
                wall_now, monotonic_now = time.time(), time.monotonic()
                allowance = min(
                    timing["deadline_at_unix"] - wall_now,
                    monotonic_deadline - monotonic_now,
                ) - PACKET_HANDOFF_MARGIN_SECONDS
                clipped_deadline = min(timing["deadline_at_unix"], wall_now + allowance)
                if allowance <= 0 or clipped_deadline <= created:
                    self._json(504, {"error": "host_relay_timeout"})
                    return
                if clipped_deadline < timing["deadline_at_unix"]:
                    timing = {**timing, "timeout_seconds": clipped_deadline - created,
                              "deadline_at_unix": clipped_deadline}
                packet_timing = timing
                # Keep the original monotonic bound. Re-anchoring it here would
                # grant body/preparation time again to this handler or its worker.

                def before_packet_publish() -> None:
                    # Sample monotonic first, then wall, so sampling overhead does
                    # not look like a rollback. Encoding/writing the temporary file
                    # must not reopen the same wall/monotonic handoff gap.
                    publish_monotonic, publish_unix = time.monotonic(), time.time()
                    wall_remaining = timing["deadline_at_unix"] - publish_unix
                    monotonic_remaining = monotonic_deadline - publish_monotonic
                    # Compare absolute projections at the same float precision;
                    # subtracting a large Unix timestamp can make a valid small
                    # cap (for example 0.2 seconds) appear slightly oversized.
                    if (min(wall_remaining, monotonic_remaining) <= 0
                            or timing["deadline_at_unix"] > publish_unix + monotonic_remaining):
                        raise ValueError("request_packet_deadline_exhausted_or_clock_rolled_back")

                try:
                    publisher = _exclusive_json if request_key else _atomic_json
                    publisher(request_path, {
                        "schema": SCHEMA,
                        "request_id": request_id,
                        **timing,
                        **({"request_key_fingerprint": request_key} if request_key else {}),
                        "durable_pending": request_key is not None,
                        "request": body,
                        "manager_transport": True,
                        "independent_review_evidence": False,
                        "authority": False,
                    }, before_publish=before_packet_publish)
                except FileExistsError:
                    # A simultaneous first poll may have published the exact
                    # same immutable packet. Join that request instead of
                    # turning an idempotent race into a false failure.
                    try:
                        packet = json.loads(request_path.read_text(encoding="utf-8"))
                        packet_timing = validate_packet_deadline(packet)
                    except (OSError, ValueError, json.JSONDecodeError):
                        self._json(409, {"error": "model_request_state_invalid", "request_id": request_id})
                        return
                    if (
                        packet.get("schema") != SCHEMA
                        or packet.get("request_id") != request_id
                        or packet.get("request_key_fingerprint") != request_key
                        or packet.get("durable_pending") is not True
                        or packet.get("request") != body
                    ):
                        self._json(409, {"error": "model_request_idempotency_conflict", "request_id": request_id})
                        return
                    durable_packet = is_durable_packet(packet)
                except ValueError:
                    self._json(504, {"error": "host_relay_timeout", "request_id": request_id})
                    return
                except OSError:
                    self._json(500, {"error": "model_request_publication_failed", "request_id": request_id})
                    return
                durable_packet = request_key is not None
            try:
                request_sha256 = hashlib.sha256(request_path.read_bytes()).hexdigest()
            except OSError:
                self._json(409, {"error": "model_request_state_invalid", "request_id": request_id})
                return

            def packet_remaining() -> float:
                if durable_packet:
                    return remaining()
                return min(remaining(), packet_timing["deadline_at_unix"] - time.time())

            response_deadline = time.monotonic() + (
                min(response_wait, packet_remaining()) if request_key else packet_remaining()
            )
            while packet_remaining() > 0 and time.monotonic() < response_deadline:
                if response_path.exists():
                    try:
                        response = json.loads(response_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        time.sleep(0.05)
                        continue
                    if (
                        isinstance(response, dict)
                        and response.get("schema") == SCHEMA
                        and response.get("request_id") == request_id
                        and isinstance(response.get("content"), str)
                        and response["content"].strip()
                    ):
                        if packet_remaining() <= 0:
                            break
                        self._json(200, {
                            "id": request_id,
                            "choices": [{
                                "message": {"role": "assistant", "content": response["content"]},
                                "finish_reason": "stop",
                            }],
                            "usage": response.get("usage") or {"prompt_tokens": 0, "completion_tokens": 0},
                        }, deadline_remaining=packet_remaining)
                        return
                    time.sleep(0.05)
                    continue
                if worker_state_path.exists():
                    try:
                        worker_state = json.loads(worker_state_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        time.sleep(0.05)
                        continue
                    if (
                        not isinstance(worker_state, dict)
                        or worker_state.get("schema") != "quillframe_codex_cli_worker_state_v1"
                        or worker_state.get("request_id") != request_id
                        or worker_state.get("request_sha256") != request_sha256
                    ):
                        self._json(409, {"error": "model_worker_state_invalid", "request_id": request_id})
                        return
                    worker_status = worker_state.get("state")
                    if worker_status in {"failed", "completed"}:
                        self._json(502, {
                            "schema": SCHEMA, "status": "model_failed", "request_id": request_id,
                            "failure_code": (
                                "model_worker_failed" if worker_status == "failed"
                                else "model_response_missing"
                            ),
                            "same_request_poll_only": False, "manager_transport": True,
                            "independent_review_evidence": False, "authority": False,
                        }, deadline_remaining=packet_remaining)
                        return
                time.sleep(0.10)
            if request_key and packet_remaining() > 0:
                self._json(202, {
                    "schema": SCHEMA, "status": "model_pending", "request_id": request_id,
                    "same_request_poll_only": True, "manager_transport": True,
                    "independent_review_evidence": False, "authority": False,
                }, deadline_remaining=packet_remaining)
                return
            self._json(504, {"error": "host_relay_timeout", "request_id": request_id})

    return RelayHandler


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="quillframe-chat-relay-") as temp:
        queue = Path(temp)
        request_id = "req_" + "a" * 32
        request = {
            "schema": SCHEMA,
            "request_id": request_id,
            **deadline_fields(time.time(), DEFAULT_RELAY_TIMEOUT_SECONDS, None),
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
        "schema": "quillframe_chat_host_relay_self_test_v2",
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
    serve.add_argument("--timeout-seconds", type=float, default=MAX_RELAY_TIMEOUT_SECONDS)
    serve.add_argument("--response-wait-seconds", type=float, default=DEFAULT_RELAY_RESPONSE_WAIT_SECONDS)
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
    try:
        validate_server_timeout(args.timeout_seconds)
        validate_response_wait(args.response_wait_seconds)
    except ValueError:
        raise SystemExit(
            f"relay timeout must be finite, positive and at most {MAX_RELAY_TIMEOUT_SECONDS:g} seconds"
        ) from None
    queue = Path(args.queue).expanduser().resolve()
    queue.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(
        (args.host, args.port),
        handler(queue, args.timeout_seconds, args.response_wait_seconds),
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
