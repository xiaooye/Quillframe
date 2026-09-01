from __future__ import annotations

import ipaddress
import hashlib
import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

from .deadlines import DEADLINE_HEADER, REQUEST_KEY_HEADER, validate_request_timeout


class TransportError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class TransportResponse:
    status: int
    headers: dict[str, str]
    body: dict[str, Any] | list[Any] | None
    text: str


class ModelTransport(Protocol):
    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str,
        auth_style: str,
        body: dict[str, Any] | None = None,
        timeout: float = 30.0,
        request_key: str | None = None,
    ) -> TransportResponse: ...


def auth_headers(token: str, auth_style: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if not token:
        return headers
    if auth_style == "bearer":
        headers["Authorization"] = f"Bearer {token}"
    elif auth_style == "x_api_key":
        headers["x-api-key"] = token
        headers["anthropic-version"] = "2023-06-01"
    elif auth_style == "none":
        pass
    else:
        raise ValueError(f"unsupported auth style: {auth_style}")
    return headers


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _address_class(value: str) -> str:
    ip = ipaddress.ip_address(value)
    if ip.is_loopback:
        return "loopback"
    if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_unspecified or ip.is_multicast:
        return "private"
    return "public"


def _literal_loopback(url: str) -> bool:
    host = urlsplit(url).hostname
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


class UrllibTransport:
    """Minimal HTTP JSON transport with SSRF and credential-redirect hardening."""

    def __init__(self, *, allow_loopback: bool = True, allow_private_network: bool = False) -> None:
        self.allow_loopback = allow_loopback
        self.allow_private_network = allow_private_network
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _validate_destination(self, url: str) -> None:
        parts = urlsplit(url)
        host = parts.hostname
        if not host:
            raise TransportError("invalid_destination", "request URL has no hostname")
        port = parts.port or (443 if parts.scheme == "https" else 80)
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise TransportError("dns_resolution_failed", f"cannot resolve model API hostname: {host}") from exc
        addresses = {info[4][0].split("%", 1)[0] for info in infos if info and info[4]}
        if not addresses:
            raise TransportError("dns_resolution_failed", f"hostname resolved to no usable address: {host}")
        for address in addresses:
            try:
                category = _address_class(address)
            except ValueError as exc:
                raise TransportError("dns_address_invalid", f"resolver returned an invalid address for {host}") from exc
            if category == "loopback" and not self.allow_loopback:
                raise TransportError("loopback_destination_denied", f"loopback model API destination is not allowed: {host}")
            if category == "private" and not self.allow_private_network:
                raise TransportError("private_destination_denied", f"private/link-local model API destination is not allowed: {host}")

    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str,
        auth_style: str,
        body: dict[str, Any] | None = None,
        timeout: float = 30.0,
        request_key: str | None = None,
    ) -> TransportResponse:
        try:
            timeout = validate_request_timeout(timeout)
        except ValueError as exc:
            raise TransportError("invalid_request_timeout", str(exc)) from exc
        # Freeze both clocks before DNS, JSON encoding or request preparation.
        # A backward wall-clock adjustment cannot extend this process's budget.
        monotonic_deadline = time.monotonic() + timeout
        deadline_unix_ms = int((time.time() + timeout) * 1000)

        def remaining_seconds(local_request: urllib.request.Request | None = None) -> float:
            wall_now = time.time()
            remaining = min(monotonic_deadline - time.monotonic(), deadline_unix_ms / 1000.0 - wall_now)
            if remaining <= 0:
                raise TransportError("request_deadline_exceeded", "model API request deadline has expired")
            if local_request is not None:
                # A preparation-time wall-clock rollback must not grant the relay
                # more time than this process's still-running monotonic budget.
                wire_deadline = min(deadline_unix_ms, int((wall_now + remaining) * 1000))
                local_request.add_header(DEADLINE_HEADER, str(wire_deadline))
            return remaining

        self._validate_destination(url)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        headers = auth_headers(token, auth_style)
        loopback_post = method.upper() == "POST" and _literal_loopback(url)
        if loopback_post:
            headers[DEADLINE_HEADER] = str(deadline_unix_ms)
            if request_key is not None:
                if not isinstance(request_key, str) or not request_key.strip():
                    raise TransportError("invalid_request_key", "model request key must be a non-empty string")
                headers[REQUEST_KEY_HEADER] = hashlib.sha256(request_key.encode("utf-8")).hexdigest()
        request = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
        try:
            try:
                response = self._opener.open(request, timeout=remaining_seconds(request if loopback_post else None))
            except urllib.error.HTTPError as exc:
                response = exc
            with response as handle:
                remaining_seconds()
                raw = handle.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw) if raw.strip() else None
                except json.JSONDecodeError:
                    parsed = None
                remaining_seconds()
                return TransportResponse(int(handle.status), {k.lower(): v for k, v in handle.headers.items()}, parsed, raw)
        except TimeoutError as exc:
            raise TransportError("request_deadline_exceeded", "model API request timed out") from exc
        except urllib.error.URLError as exc:
            raise TransportError("network_request_failed", f"model API request failed: {exc.reason}") from exc


class MockTransport:
    """Deterministic scripted HTTP transport used by normal CI."""

    def __init__(self, routes: dict[tuple[str, str, str], list[TransportResponse] | TransportResponse]) -> None:
        self.routes = routes
        self.requests: list[dict[str, Any]] = []

    def request_json(self, method: str, url: str, *, token: str, auth_style: str, body: dict[str, Any] | None = None,
                     timeout: float = 30.0, request_key: str | None = None) -> TransportResponse:
        self.requests.append({"method": method.upper(), "url": url, "auth_style": auth_style, "body": body,
                              "token_present": bool(token), "request_key_present": request_key is not None})
        key = (method.upper(), url, auth_style)
        if key not in self.routes:
            return TransportResponse(404, {}, {"error": "fixture route missing"}, "")
        value = self.routes[key]
        if isinstance(value, list):
            if not value:
                raise AssertionError(f"fixture route exhausted: {key}")
            return value.pop(0)
        return value
