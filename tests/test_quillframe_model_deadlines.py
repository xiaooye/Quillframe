from __future__ import annotations

import io
import json
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch

from model_runtime.deadlines import DEADLINE_HEADER
from model_runtime.transport import TransportError, UrllibTransport


class Clock:
    def __init__(self) -> None:
        self.wall = 1000.0
        self.monotonic = 10.0

    def advance(self, seconds: float, *, wall_seconds: float | None = None) -> None:
        self.monotonic += seconds
        self.wall += seconds if wall_seconds is None else wall_seconds


@contextmanager
def frozen_clock(clock: Clock):
    with patch("model_runtime.transport.time.monotonic", side_effect=lambda: clock.monotonic), \
            patch("model_runtime.transport.time.time", side_effect=lambda: clock.wall):
        yield


class Response:
    status = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, *, on_read=None) -> None:
        self.on_read = on_read
        self.closed = False

    def read(self) -> bytes:
        if self.on_read is not None:
            self.on_read()
        return b' {"result":"unchanged"}\n'

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True


def dns_answer(address: str = "127.0.0.1"):
    return [(2, 1, 6, "", (address, 80))]


class TransportDeadlineTests(unittest.TestCase):
    def test_only_literal_loopback_post_receives_deadline_and_body_is_unchanged(self):
        body = {"model": "fixture", "messages": [{"role": "user", "content": "原始消息\n"}],
                "max_tokens": 64, "response_format": {"type": "json_object"}}
        original = deepcopy(body)
        destinations = (
            ("POST", "http://localhost:8765/v1/chat/completions", "127.0.0.1", True),
            ("post", "http://LOCALHOST:8765/v1/chat/completions", "127.0.0.1", True),
            ("POST", "http://127.0.0.2:8765/v1/chat/completions", "127.0.0.2", True),
            ("POST", "http://[::1]:8765/v1/chat/completions", "::1", True),
            ("GET", "http://localhost:8765/v1/models", "127.0.0.1", False),
            ("POST", "https://api.example.test/v1/chat/completions", "93.184.216.34", False),
            ("POST", "https://alias.example.test/v1/chat/completions", "127.0.0.1", False),
            ("POST", "https://localhost.example.test/v1/chat/completions", "93.184.216.34", False),
            ("POST", "http://localhost.:8765/v1/chat/completions", "127.0.0.1", False),
            ("POST", "http://2130706433:8765/v1/chat/completions", "127.0.0.1", False),
            ("POST", "https://127.0.0.1.example.test/v1/chat/completions", "93.184.216.34", False),
        )
        for method, url, address, local_header in destinations:
            with self.subTest(method=method, url=url):
                transport = UrllibTransport()
                with frozen_clock(Clock()), \
                        patch("model_runtime.transport.socket.getaddrinfo", return_value=dns_answer(address)), \
                        patch.object(transport._opener, "open", return_value=Response()) as opened:
                    result = transport.request_json(method, url, token="fixture-key", auth_style="bearer", body=body, timeout=180)
                opened.assert_called_once()
                request = opened.call_args.args[0]
                headers = {key.lower(): value for key, value in request.header_items()}
                self.assertEqual(local_header, DEADLINE_HEADER.lower() in headers)
                if local_header:
                    self.assertEqual("1180000", headers[DEADLINE_HEADER.lower()])
                self.assertEqual("Bearer fixture-key", headers["authorization"])
                self.assertEqual(json.dumps(original, ensure_ascii=False).encode("utf-8"), request.data)
                self.assertEqual(original, body)
                self.assertEqual(180.0, opened.call_args.kwargs["timeout"])
                self.assertEqual(' {"result":"unchanged"}\n', result.text)

    def test_dns_body_and_request_preparation_consume_the_original_deadline(self):
        clock = Clock()
        transport = UrllibTransport()
        original_dumps, original_request = json.dumps, urllib.request.Request

        def resolve(*args, **kwargs):
            clock.advance(11)
            return dns_answer()

        def encode(*args, **kwargs):
            clock.advance(7)
            return original_dumps(*args, **kwargs)

        def prepare(*args, **kwargs):
            clock.advance(3)
            return original_request(*args, **kwargs)

        with frozen_clock(clock), patch("model_runtime.transport.socket.getaddrinfo", side_effect=resolve), \
                patch("model_runtime.transport.json.dumps", side_effect=encode), \
                patch("model_runtime.transport.urllib.request.Request", side_effect=prepare), \
                patch.object(transport._opener, "open", return_value=Response()) as opened:
            transport.request_json("POST", "http://localhost:8765/v1/chat/completions", token="", auth_style="none",
                                   body={"messages": []}, timeout=600)
        self.assertEqual(579.0, opened.call_args.kwargs["timeout"])
        self.assertEqual("1600000", opened.call_args.args[0].get_header(DEADLINE_HEADER.capitalize()))

    def test_expiry_during_any_preparation_step_prevents_dispatch(self):
        for stage in ("dns", "body", "request"):
            with self.subTest(stage=stage):
                clock = Clock()
                transport = UrllibTransport()
                original_dumps, original_request = json.dumps, urllib.request.Request

                def resolve(*args, **kwargs):
                    if stage == "dns":
                        clock.advance(180)
                    return dns_answer()

                def encode(*args, **kwargs):
                    if stage == "body":
                        clock.advance(180)
                    return original_dumps(*args, **kwargs)

                def prepare(*args, **kwargs):
                    if stage == "request":
                        clock.advance(180)
                    return original_request(*args, **kwargs)

                with frozen_clock(clock), patch("model_runtime.transport.socket.getaddrinfo", side_effect=resolve), \
                        patch("model_runtime.transport.json.dumps", side_effect=encode), \
                        patch("model_runtime.transport.urllib.request.Request", side_effect=prepare), \
                        patch.object(transport._opener, "open") as opened:
                    with self.assertRaises(TransportError) as error:
                        transport.request_json("POST", "http://localhost:8765/v1/chat/completions", token="", auth_style="none",
                                               body={"messages": []}, timeout=180)
                self.assertEqual("request_deadline_exceeded", error.exception.code)
                opened.assert_not_called()

    def test_clock_changes_cannot_extend_or_restart_the_request(self):
        for monotonic_elapsed, wall_elapsed, expected in ((60, -120, 120.0), (1, 60, 120.0), (180, -120, None), (1, 180, None)):
            with self.subTest(monotonic_elapsed=monotonic_elapsed, wall_elapsed=wall_elapsed):
                clock = Clock()
                transport = UrllibTransport()

                def resolve(*args, **kwargs):
                    clock.advance(monotonic_elapsed, wall_seconds=wall_elapsed)
                    return dns_answer()

                with frozen_clock(clock), patch("model_runtime.transport.socket.getaddrinfo", side_effect=resolve), \
                        patch.object(transport._opener, "open", return_value=Response()) as opened:
                    if expected is None:
                        with self.assertRaises(TransportError) as error:
                            transport.request_json("POST", "http://localhost:8765/v1/chat/completions", token="", auth_style="none", timeout=180)
                        self.assertEqual("request_deadline_exceeded", error.exception.code)
                        opened.assert_not_called()
                    else:
                        transport.request_json("POST", "http://localhost:8765/v1/chat/completions", token="", auth_style="none", timeout=180)
                        self.assertEqual(expected, opened.call_args.kwargs["timeout"])
                        wire_deadline = int(opened.call_args.args[0].get_header(DEADLINE_HEADER.capitalize()))
                        self.assertEqual(1000000 if wall_elapsed == -120 else 1180000, wire_deadline)
                        self.assertLessEqual(wire_deadline, 1180000)
                        self.assertLessEqual(wire_deadline / 1000.0 - clock.wall, opened.call_args.kwargs["timeout"])

    def test_invalid_timeout_is_rejected_before_dns_or_dispatch(self):
        for value in (True, False, 0, -1, 600.001, 10 ** 1000, float("nan"), float("inf"), None, "600", []):
            with self.subTest(timeout=value):
                transport = UrllibTransport()
                with patch("model_runtime.transport.socket.getaddrinfo") as dns, patch.object(transport._opener, "open") as opened:
                    with self.assertRaises(TransportError) as error:
                        transport.request_json("POST", "http://localhost:8765/v1/chat/completions", token="", auth_style="none", timeout=value)
                self.assertEqual("invalid_request_timeout", error.exception.code)
                dns.assert_not_called()
                opened.assert_not_called()

    def test_late_response_is_closed_and_never_returned_as_success(self):
        clock = Clock()
        response = Response(on_read=lambda: clock.advance(600, wall_seconds=-100))
        transport = UrllibTransport()
        with frozen_clock(clock), patch("model_runtime.transport.socket.getaddrinfo", return_value=dns_answer()), \
                patch.object(transport._opener, "open", return_value=response) as opened:
            with self.assertRaises(TransportError) as error:
                transport.request_json("POST", "http://localhost:8765/v1/chat/completions", token="", auth_style="none", timeout=600)
        self.assertEqual("request_deadline_exceeded", error.exception.code)
        self.assertTrue(response.closed)
        opened.assert_called_once()

    def test_socket_timeout_and_network_failure_do_not_retry(self):
        for failure, expected in ((TimeoutError("fixture timed out"), "request_deadline_exceeded"),
                                  (urllib.error.URLError("fixture disconnected"), "network_request_failed")):
            with self.subTest(failure=type(failure).__name__):
                transport = UrllibTransport()
                with frozen_clock(Clock()), patch("model_runtime.transport.socket.getaddrinfo", return_value=dns_answer()), \
                        patch.object(transport._opener, "open", side_effect=failure) as opened:
                    with self.assertRaises(TransportError) as error:
                        transport.request_json("POST", "http://localhost:8765/v1/chat/completions", token="", auth_style="none", timeout=600)
                self.assertEqual(expected, error.exception.code)
                opened.assert_called_once()

    def test_expiry_during_open_closes_the_response_without_reading_it(self):
        clock = Clock()
        response = Response()
        transport = UrllibTransport()

        def open_late(*args, **kwargs):
            clock.advance(600)
            return response

        with frozen_clock(clock), patch("model_runtime.transport.socket.getaddrinfo", return_value=dns_answer()), \
                patch.object(transport._opener, "open", side_effect=open_late) as opened, \
                patch.object(response, "read", wraps=response.read) as read:
            with self.assertRaises(TransportError) as error:
                transport.request_json("POST", "http://localhost:8765/v1/chat/completions", token="", auth_style="none", timeout=600)
        self.assertEqual("request_deadline_exceeded", error.exception.code)
        self.assertTrue(response.closed)
        read.assert_not_called()
        opened.assert_called_once()

    def test_normal_and_http_error_body_timeouts_are_closed_without_retry(self):
        url = "http://localhost:8765/v1/chat/completions"
        for is_http_error in (False, True):
            with self.subTest(http_error=is_http_error):
                response = urllib.error.HTTPError(url, 504, "Timeout", {}, io.BytesIO()) if is_http_error else Response()
                transport = UrllibTransport()
                options = {"side_effect": response} if is_http_error else {"return_value": response}
                with frozen_clock(Clock()), patch("model_runtime.transport.socket.getaddrinfo", return_value=dns_answer()), \
                        patch.object(transport._opener, "open", **options) as opened, \
                        patch.object(response, "read", side_effect=TimeoutError("fixture body stalled")):
                    with self.assertRaises(TransportError) as error:
                        transport.request_json("POST", url, token="", auth_style="none", timeout=600)
                self.assertEqual("request_deadline_exceeded", error.exception.code)
                self.assertTrue(response.closed)
                opened.assert_called_once()

    def test_http_failure_is_returned_once_without_changing_its_body(self):
        url = "http://localhost:8765/v1/chat/completions"
        raw = b' {"error":"host_relay_timeout","request_id":"fixture"}\n'
        failure = urllib.error.HTTPError(url, 504, "Timeout", {}, io.BytesIO(raw))
        transport = UrllibTransport()
        with frozen_clock(Clock()), patch("model_runtime.transport.socket.getaddrinfo", return_value=dns_answer()), \
                patch.object(transport._opener, "open", side_effect=failure) as opened:
            result = transport.request_json("POST", url, token="", auth_style="none", timeout=600)
        self.assertEqual(504, result.status)
        self.assertEqual(raw.decode("utf-8"), result.text)
        self.assertTrue(failure.closed)
        opened.assert_called_once()


if __name__ == "__main__":
    unittest.main()
