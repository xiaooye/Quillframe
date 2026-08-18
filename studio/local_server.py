#!/usr/bin/env python3
"""Loopback-only HTTP transport for the Quillframe Studio product shell.

This server is transport, not authority. It serves the built SolidJS app and
forwards one typed POST endpoint to studio/host_bridge.py. It does not read
Core persistence, expose CORS, poll, mutate project state, or add a second
runtime model.
"""
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import secrets
import tempfile
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from host_bridge import invoke

HERE = Path(__file__).resolve().parent
DEFAULT_DIST = HERE / "app" / "dist"
TOKEN_PLACEHOLDER = "__QUILLFRAME_STUDIO_TOKEN__"
MAX_REQUEST_BYTES = 128 * 1024
SERVER_SCHEMA = "quillframe_studio_local_server_v1"


class StudioServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], dist: Path, token: str, verbose: bool = False):
        super().__init__(address, StudioHandler)
        self.dist = dist.resolve()
        self.token = token
        self.verbose = verbose


class StudioHandler(BaseHTTPRequestHandler):
    server: StudioServer
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        if self.server.verbose:
            super().log_message(fmt, *args)

    @property
    def allowed_hosts(self) -> set[str]:
        port = self.server.server_port
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    @property
    def allowed_origins(self) -> set[str]:
        port = self.server.server_port
        return {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: dict[str, Any]) -> None:
        body = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def _transport_error(self, status: int, code: str, message: str) -> None:
        self._json(status, {"schema": "quillframe_studio_transport_error_v1", "code": code, "message": message, "authority": False})

    def _host_allowed(self) -> bool:
        return self.headers.get("Host", "") in self.allowed_hosts

    def _request_origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        if origin and origin not in self.allowed_origins:
            return False
        fetch_site = self.headers.get("Sec-Fetch-Site")
        return fetch_site in {None, "same-origin", "none"}

    def _index(self) -> bytes:
        index = self.server.dist / "index.html"
        if not index.is_file():
            raise FileNotFoundError(index)
        rendered = index.read_text(encoding="utf-8").replace(TOKEN_PLACEHOLDER, self.server.token)
        return rendered.encode("utf-8")

    def _safe_static_path(self, request_path: str) -> Path | None:
        clean = unquote(urlsplit(request_path).path).lstrip("/")
        if not clean:
            return None
        candidate = (self.server.dist / clean).resolve()
        if candidate == self.server.dist or self.server.dist not in candidate.parents:
            return None
        return candidate

    def do_GET(self) -> None:  # noqa: N802
        if not self._host_allowed():
            self._transport_error(HTTPStatus.BAD_REQUEST, "invalid_host", "Host is not the loopback Studio origin")
            return
        if urlsplit(self.path).path.startswith("/api/"):
            self._transport_error(HTTPStatus.NOT_FOUND, "api_not_found", "Unknown Studio API endpoint")
            return
        path = self._safe_static_path(self.path)
        try:
            if path and path.is_file() and path.name != "index.html":
                body = path.read_bytes()
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                if mime.startswith("text/") or mime in {"application/javascript", "application/json", "image/svg+xml"}:
                    mime += "; charset=utf-8"
                self._send_bytes(HTTPStatus.OK, body, mime)
            else:
                self._send_bytes(HTTPStatus.OK, self._index(), "text/html; charset=utf-8")
        except FileNotFoundError:
            self._transport_error(HTTPStatus.SERVICE_UNAVAILABLE, "app_not_built", "Studio app dist/index.html is unavailable")

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/api/bridge/invoke":
            self._transport_error(HTTPStatus.NOT_FOUND, "api_not_found", "Only /api/bridge/invoke is exposed")
            return
        if not self._host_allowed() or not self._request_origin_allowed():
            self._transport_error(HTTPStatus.FORBIDDEN, "origin_rejected", "Request is not from the loopback Studio origin")
            return
        supplied = self.headers.get("X-Quillframe-Studio-Token", "")
        if not supplied or not hmac.compare_digest(supplied, self.server.token):
            self._transport_error(HTTPStatus.FORBIDDEN, "token_rejected", "Studio transport token is missing or invalid")
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._transport_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content_type_rejected", "Content-Type must be application/json")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._transport_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request_size_rejected", f"Request body must be 1..{MAX_REQUEST_BYTES} bytes")
            return
        raw = self.rfile.read(length)
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            self._transport_error(HTTPStatus.BAD_REQUEST, "invalid_json", "Request body must be valid JSON")
            return
        if not isinstance(request, dict):
            self._transport_error(HTTPStatus.BAD_REQUEST, "invalid_request", "Bridge request root must be an object")
            return
        result = invoke(request)
        self._json(HTTPStatus.OK, result)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._transport_error(HTTPStatus.METHOD_NOT_ALLOWED, "cors_disabled", "Cross-origin API access is not supported")


def create_server(dist: Path, *, port: int = 0, token: str | None = None, verbose: bool = False) -> StudioServer:
    dist = dist.resolve()
    if not dist.is_dir():
        raise ValueError(f"Studio dist directory not found: {dist}")
    return StudioServer(("127.0.0.1", port), dist, token or secrets.token_urlsafe(32), verbose=verbose)


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="quillframe-studio-server-") as temp:
        dist = Path(temp)
        (dist / "index.html").write_text(f"<meta name='quillframe-studio-token' content='{TOKEN_PLACEHOLDER}'>", encoding="utf-8")
        (dist / "asset.txt").write_text("asset-ok", encoding="utf-8")
        server = create_server(dist, token="self-test-token")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        checks: dict[str, bool] = {}
        try:
            index = urllib.request.urlopen(base + "/", timeout=3).read().decode("utf-8")
            checks["index_token_injected"] = "self-test-token" in index and TOKEN_PLACEHOLDER not in index
            checks["spa_fallback"] = "self-test-token" in urllib.request.urlopen(base + "/project", timeout=3).read().decode("utf-8")
            checks["static_asset"] = urllib.request.urlopen(base + "/asset.txt", timeout=3).read() == b"asset-ok"

            request_body = json.dumps({
                "schema": "quillframe_studio_host_bridge_request_v1",
                "request_id": "local-server-self-test",
                "operation": "bridge.describe",
                "surface": "local_app",
                "args": {},
                "authority": False,
            }).encode("utf-8")
            good = urllib.request.Request(
                base + "/api/bridge/invoke",
                method="POST",
                data=request_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Quillframe-Studio-Token": "self-test-token",
                    "Origin": base,
                    "Sec-Fetch-Site": "same-origin",
                },
            )
            result = json.loads(urllib.request.urlopen(good, timeout=5).read())
            checks["bridge_envelope"] = result.get("schema") == "quillframe_studio_host_bridge_result_v1" and result.get("status") == "ok"
            checks["authority_false"] = all(result.get(key) is False for key in ("authority", "canon_authority", "framework_write_authority", "settlement_authority"))

            bad = urllib.request.Request(base + "/api/bridge/invoke", method="POST", data=request_body, headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(bad, timeout=3)
                checks["token_required"] = False
            except urllib.error.HTTPError as exc:
                checks["token_required"] = exc.code == HTTPStatus.FORBIDDEN
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    return {
        "schema": "quillframe_studio_local_server_self_test_v1",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "bind_host": "127.0.0.1",
        "max_request_bytes": MAX_REQUEST_BYTES,
        "cors_enabled": False,
        "mutation_endpoint_exposed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Quillframe Studio app on a loopback-only transport")
    parser.add_argument("--dist", default=str(DEFAULT_DIST))
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "pass" else 1

    server = create_server(Path(args.dist), port=args.port, verbose=args.verbose)
    print(json.dumps({
        "schema": SERVER_SCHEMA,
        "status": "serving",
        "url": f"http://127.0.0.1:{server.server_port}/",
        "authority": False,
        "cors_enabled": False,
        "max_request_bytes": MAX_REQUEST_BYTES,
    }, ensure_ascii=False), flush=True)
    try:
        server.serve_forever(poll_interval=1.0)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
