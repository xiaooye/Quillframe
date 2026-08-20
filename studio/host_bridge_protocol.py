"""Runtime-independent Host Bridge v11 envelope primitives.

This module is intentionally limited to the wire contract. Frontend build and
verification environments can validate cross-language fingerprints without
loading Quillframe's SQLite-backed execution runtime.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

BRIDGE_VERSION = "11"
REQUEST_SCHEMA = "quillframe_host_bridge_request_v11"
RESULT_SCHEMA = "quillframe_host_bridge_result_v11"

_SECRET_REQUEST_KEYS = {"access_token", "api_key", "apikey", "password", "secret", "token"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def _secret_values(value: Any) -> set[str]:
    """Collect credential values only from explicitly secret-bearing request fields."""
    found: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                normalized = str(key).lower().replace("-", "_")
                if normalized in _SECRET_REQUEST_KEYS:
                    if isinstance(child, str) and child:
                        found.add(child)
                    continue
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return found


def _redact(value: Any, secret_values: set[str] | None = None) -> Any:
    """Remove credential keys and scrub their values from nested strings."""
    secrets = secret_values or set()
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            out[str(key)] = "<redacted>" if normalized in _SECRET_REQUEST_KEYS else _redact(child, secrets)
        return out
    if isinstance(value, list):
        return [_redact(child, secrets) for child in value]
    if isinstance(value, str):
        scrubbed = value
        for secret in sorted(secrets, key=len, reverse=True):
            if secret:
                scrubbed = scrubbed.replace(secret, "<redacted>")
        return scrubbed
    return value


def result(request: dict[str, Any], status: str, *, data: Any = None, error: Any = None) -> dict[str, Any]:
    secrets = _secret_values(request)
    safe_request = _redact(request, secrets)
    output = {
        "schema": RESULT_SCHEMA,
        "bridge_version": BRIDGE_VERSION,
        "request_id": safe_request.get("request_id"),
        "operation": safe_request.get("operation"),
        "surface": safe_request.get("surface"),
        "status": status,
        "data": _redact(data, secrets),
        "error": _redact(error, secrets),
        "request_fingerprint": fingerprint(safe_request),
        "secret_values_persisted": False,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    output["result_fingerprint"] = fingerprint(output)
    return output
