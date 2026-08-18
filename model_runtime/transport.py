from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit


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
    ) -> TransportResponse:
        self._validate_destination(url)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method.upper(), headers=auth_headers(token, auth_style))
        try:
            with self._opener.open(request, timeout=timeout) as handle:
                raw = handle.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw) if raw.strip() else None
                except json.JSONDecodeError:
                    parsed = None
                return TransportResponse(int(handle.status), {k.lower(): v for k, v in handle.headers.items()}, parsed, raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw.strip() else None
            except json.JSONDecodeError:
                parsed = None
            return TransportResponse(int(exc.code), {k.lower(): v for k, v in exc.headers.items()}, parsed, raw)
        except urllib.error.URLError as exc:
            raise TransportError("network_request_failed", f"model API request failed: {exc.reason}") from exc


class MockTransport:
    """Deterministic scripted HTTP transport used by normal CI."""

    def __init__(self, routes: dict[tuple[str, str, str], list[TransportResponse] | TransportResponse]) -> None:
        self.routes = routes
        self.requests: list[dict[str, Any]] = []

    def request_json(self, method: str, url: str, *, token: str, auth_style: str, body: dict[str, Any] | None = None, timeout: float = 30.0) -> TransportResponse:
        self.requests.append({"method": method.upper(), "url": url, "auth_style": auth_style, "body": body, "token_present": bool(token)})
        key = (method.upper(), url, auth_style)
        if key not in self.routes:
            return TransportResponse(404, {}, {"error": "fixture route missing"}, "")
        value = self.routes[key]
        if isinstance(value, list):
            if not value:
                raise AssertionError(f"fixture route exhausted: {key}")
            return value.pop(0)
        return value
