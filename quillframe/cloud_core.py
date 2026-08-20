"""Private HTTP adapter for the Cloudflare Quillframe Core Container."""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from persistence.quillframe_sqlite import BundleValidationError, QuillframeStore, fingerprint_bytes

from studio.host_bridge import invoke


MAX_BODY = 4 * 1024 * 1024
MAX_NATIVE_BACKUP_BODY = 128 * 1024 * 1024
NATIVE_BACKUP_PATH = "/native/project-backup/verify"
SKEW_MS = 5_000
MAX_LIFETIME_MS = 30_000
PROJECT_REQUIRED = {
    "project.create", "project.open", "project.inspect", "project.search", "project.backup",
    "document.create", "document.open", "document.revisions.list", "document.revision.save", "document.revision.compare",
    "author.run.start", "author.run.status", "author.run.resume", "author.run.cancel", "author.run.execute",
    "author.run.independent.submit", "author.run.independent.dispatch.prepare", "author.run.context.refresh",
    "model.route.preview", "candidate.accept", "candidate.reject", "candidate.revision.request",
    "settlement.apply", "settlement.preflight", "feedback.observe", "publication.preview", "publication.build",
    "inspector.sessions.list", "inspector.runs.list", "inspector.checkpoints.list", "inspector.context.list",
    "inspector.receipts.list", "inspector.candidates.list", "inspector.learning.list", "inspector.context.runtime",
    "document.list", "candidate.review.get", "candidate.visible.get",
}
PROJECT_NULL = {
    "bridge.describe", "database.doctor", "project.list", "author.run.events", "model.service.add",
    "model.service.list", "model.service.get", "model.service.discover", "model.service.test",
    "model.service.token.replace", "model.service.token.remove", "model.service.delete", "model.capabilities",
}
_nonce_lock = threading.Lock()
_nonce_records: dict[str, tuple[str, str, str | None, int, int]] = {}
_active_clock: Callable[[], int] = lambda: int(time.time() * 1000)
_active_nonce_consumer: Callable[..., None] | None = None


class CoreProofError(ValueError):
    def __init__(self, code: str, message: str = "core proof is invalid"):
        super().__init__(message)
        self.code = code


def _canonical(value: Any) -> bytes:
    def validate(node: Any) -> None:
        if isinstance(node, bool) or node is None:
            return
        if isinstance(node, str):
            if any(0xD800 <= ord(char) <= 0xDFFF for char in node):
                raise CoreProofError("body_json_invalid")
            return
        if isinstance(node, int):
            if not (-2**53 < node < 2**53):
                raise CoreProofError("body_json_invalid")
            return
        if isinstance(node, float):
            raise CoreProofError("body_json_invalid")
        if isinstance(node, list):
            for item in node:
                validate(item)
            return
        if isinstance(node, dict):
            for key, item in node.items():
                if not key.isascii():
                    raise CoreProofError("body_json_invalid")
                validate(item)
            return
        raise CoreProofError("body_json_invalid")

    validate(value)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (UnicodeEncodeError, TypeError, ValueError):
        raise CoreProofError("body_json_invalid")


def _parse_canonical_body(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_BODY:
        raise CoreProofError("body_size_invalid")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CoreProofError("body_json_invalid")
    if not isinstance(value, dict):
        raise CoreProofError("body_json_invalid")
    if _canonical(value) != raw:
        raise CoreProofError("body_not_canonical")
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CoreProofError("body_duplicate_key")
        result[key] = value
    return result


def _b64url(value: str, label: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise CoreProofError("proof_invalid", f"{label} encoding is invalid")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        raw = base64.urlsafe_b64decode(value + padding)
    except (ValueError, base64.binascii.Error):
        raise CoreProofError("proof_invalid")
    if base64.urlsafe_b64encode(raw).decode().rstrip("=") != value:
        raise CoreProofError("proof_invalid")
    return raw


def _project_id(operation: str, request: dict[str, Any]) -> str | None:
    args = request.get("args")
    if not isinstance(args, dict):
        raise CoreProofError("proof_project_invalid")
    if operation in PROJECT_REQUIRED:
        value = args.get("project_id")
        if not isinstance(value, str) or not value or len(value) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
            raise CoreProofError("proof_project_invalid")
        return value
    if operation in PROJECT_NULL:
        if "project_id" in args:
            raise CoreProofError("proof_project_invalid")
        return None
    raise CoreProofError("proof_operation_invalid")


def _consume_nonce(*, session_id: str, project_id: str | None, nonce: str, proof_digest: str, issued_at: int, expires_at: int, now: int) -> None:
    """Consume the local fallback nonce cache using nonce hash as its identity.

    The hosted durable consumer has the same contract.  The fallback is only a
    bounded defense-in-depth cache; it deliberately binds a nonce to the full
    session/project/digest tuple so a replay under another identity cannot
    silently succeed.
    """
    nonce_hash = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    replay_expires_at = expires_at + SKEW_MS
    with _nonce_lock:
        expired = [key for key, (_digest, _session, _project, replay_until, _consumed) in _nonce_records.items() if replay_until <= now]
        for key in expired:
            _nonce_records.pop(key, None)
        previous = _nonce_records.get(nonce_hash)
        if previous is not None:
            previous_digest, previous_session, previous_project, replay_until, _consumed = previous
            if replay_until > now:
                if previous_digest == proof_digest and previous_session == session_id and previous_project == project_id:
                    raise CoreProofError("core_nonce_replayed")
                raise CoreProofError("core_nonce_digest_conflict")
        if len(_nonce_records) >= 256:
            raise CoreProofError("core_nonce_capacity")
        _nonce_records[nonce_hash] = (proof_digest, session_id, project_id, replay_expires_at, now)


def configure_core_security(*, nonce_consumer: Callable[..., None] | None = None, clock: Callable[[], int] | None = None) -> None:
    """Install the durable nonce seam and clock used by the private adapter.

    Tests and the hosted adapter inject a transaction-backed consumer here.
    Passing ``None`` restores the bounded local cache.  Resetting the local
    cache is intentional: it prevents state leaking across adapter lifetimes.
    """
    global _active_clock, _active_nonce_consumer
    _active_clock = clock or (lambda: int(time.time() * 1000))
    _active_nonce_consumer = nonce_consumer
    with _nonce_lock:
        _nonce_records.clear()


def _verify_core_proof(value: str, body: bytes, method: str, path: str, now: int, *, consume_nonce: bool = True) -> dict[str, Any]:
    if not isinstance(value, str) or len(value) > 32_768:
        raise CoreProofError("proof_invalid")
    parts = value.split(".")
    if len(parts) != 4 or parts[0] != "qfcp1":
        raise CoreProofError("proof_invalid")
    key_id = parts[1]
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", key_id):
        raise CoreProofError("proof_invalid")
    current_id = os.environ.get("QUILLFRAME_CORE_PROOF_KEY_ID", "")
    current_value = os.environ.get("QUILLFRAME_CORE_PROOF_KEY_B64", "")
    previous_id = os.environ.get("QUILLFRAME_CORE_PROOF_PREVIOUS_KEY_ID")
    previous_value = os.environ.get("QUILLFRAME_CORE_PROOF_PREVIOUS_KEY_B64")
    if (
        not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", current_id)
        or not current_value
        or (previous_id is None) != (previous_value is None)
        or previous_id == current_id
        or previous_id is not None and not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", previous_id)
    ):
        raise CoreProofError("proof_key_config_invalid")

    def strict_key(raw: str) -> bytes:
        try:
            decoded = _b64url(raw, "proof key")
        except CoreProofError:
            raise CoreProofError("proof_key_config_invalid")
        if len(decoded) != 32:
            raise CoreProofError("proof_key_config_invalid")
        return decoded

    keys = {current_id: strict_key(current_value)}
    if previous_id is not None and previous_value is not None:
        keys[previous_id] = strict_key(previous_value)
    if key_id not in keys:
        raise CoreProofError("proof_key_unknown")

    claims_raw = _b64url(parts[2], "claims")
    signature = _b64url(parts[3], "signature")
    if len(signature) != 32:
        raise CoreProofError("proof_signature_invalid")
    try:
        claims = json.loads(claims_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CoreProofError("proof_claims_invalid")
    expected_keys = {"schema", "key_id", "method", "path", "body_sha256", "workspace_id", "session_id", "project_id", "chapter_scope", "issued_at", "expires_at", "nonce"}
    if not isinstance(claims, dict) or set(claims) != expected_keys:
        raise CoreProofError("proof_claims_invalid")
    try:
        canonical_claims = _canonical(claims)
    except CoreProofError:
        raise CoreProofError("proof_claims_invalid")
    if canonical_claims != claims_raw:
        raise CoreProofError("proof_claims_invalid")

    schema = claims["schema"]
    claim_method = claims["method"]
    claim_path = claims["path"]
    workspace_id = claims["workspace_id"]
    session_id = claims["session_id"]
    body_sha256 = claims["body_sha256"]
    project_id = claims["project_id"]
    nonce = claims["nonce"]
    if schema != "quillframe_core_proof_v1" or claims["key_id"] != key_id or claims["chapter_scope"] != "CH001":
        raise CoreProofError("proof_claims_invalid")
    if not isinstance(claim_method, str) or not re.fullmatch(r"[A-Z][A-Z0-9-]{0,15}", claim_method):
        raise CoreProofError("proof_claims_invalid")
    if not isinstance(claim_path, str) or not 0 < len(claim_path) <= 2_048 or not claim_path.startswith("/") or any(ord(char) < 0x20 or ord(char) == 0x7F or char == "#" for char in claim_path):
        raise CoreProofError("proof_claims_invalid")
    if claim_method != method or claim_path != path:
        raise CoreProofError("proof_binding_invalid")
    if not isinstance(workspace_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", workspace_id):
        raise CoreProofError("proof_claims_invalid")
    if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", session_id):
        raise CoreProofError("proof_claims_invalid")
    if not isinstance(body_sha256, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", body_sha256):
        raise CoreProofError("proof_claims_invalid")
    if project_id is not None and (not isinstance(project_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", project_id)):
        raise CoreProofError("proof_claims_invalid")
    if not isinstance(nonce, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", nonce):
        raise CoreProofError("proof_claims_invalid")
    issued_at = claims["issued_at"]
    expires_at = claims["expires_at"]
    if type(issued_at) is not int or type(expires_at) is not int or not 0 <= issued_at <= 100_000_000_000_000 or not 0 <= expires_at <= 100_000_000_000_000:
        raise CoreProofError("proof_time_invalid")
    if expires_at <= issued_at or expires_at - issued_at > MAX_LIFETIME_MS:
        raise CoreProofError("proof_time_invalid")
    if type(now) is not int or not 0 <= now <= 100_000_000_000_000 or now < issued_at - SKEW_MS or now > expires_at + SKEW_MS:
        raise CoreProofError("proof_time_invalid")
    actual_hash = "sha256:" + hashlib.sha256(body).hexdigest()
    if not hmac.compare_digest(actual_hash, body_sha256):
        raise CoreProofError("proof_body_invalid")
    expected = hmac.new(keys[key_id], claims_raw, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, signature):
        raise CoreProofError("proof_signature_invalid")
    if consume_nonce:
        consumer = _active_nonce_consumer or _consume_nonce
        consumer(
            session_id=session_id,
            project_id=project_id,
            nonce=nonce,
            proof_digest="sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest(),
            issued_at=issued_at,
            expires_at=expires_at,
            now=now,
        )
    return claims


def _read_exact_body(reader: Any, length: int, *, limit: int = MAX_BODY) -> bytes:
    if type(length) is not int or length <= 0 or length > limit:
        raise CoreProofError("body_size_invalid")
    raw = bytearray()
    remaining = length
    while remaining:
        try:
            chunk = reader.read(min(64 * 1024, remaining))
        except Exception:
            raise CoreProofError("body_read_failed")
        if not isinstance(chunk, (bytes, bytearray)):
            raise CoreProofError("body_read_failed")
        if not chunk or len(chunk) > remaining:
            raise CoreProofError("body_size_invalid")
        raw.extend(chunk)
        remaining -= len(chunk)
    return bytes(raw)


def _parse_content_length(declared: str | None, *, transfer_encoding: bool = False, limit: int = MAX_BODY) -> int:
    if transfer_encoding or declared is None or not re.fullmatch(r"[0-9]+", declared):
        raise CoreProofError("body_size_invalid")
    length = int(declared)
    if length <= 0 or length > limit:
        raise CoreProofError("body_size_invalid")
    return length


def _native_query(path: str) -> dict[str, str | int]:
    try:
        pairs = parse_qsl(urlsplit(path).query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise CoreProofError("proof_query_invalid")
    if any(not key or key not in {"operation", "project_id", "version_id", "object_key_sha256", "pointer_version"} for key, _ in pairs):
        raise CoreProofError("proof_query_invalid")
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise CoreProofError("proof_query_invalid")
    query = dict(pairs)
    operation = query.get("operation")
    project_id = query.get("project_id")
    if operation not in {"project.upload", "project.read"} or not isinstance(project_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", project_id):
        raise CoreProofError("proof_project_invalid")
    expected = {"operation", "project_id"} if operation == "project.upload" else {"operation", "project_id", "version_id", "object_key_sha256", "pointer_version"}
    if set(keys) != expected:
        raise CoreProofError("proof_query_invalid")
    if operation == "project.read":
        version_id = query.get("version_id")
        object_key_sha256 = query.get("object_key_sha256")
        pointer_version = query.get("pointer_version")
        if not isinstance(version_id, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", version_id) or not isinstance(object_key_sha256, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", object_key_sha256) or not isinstance(pointer_version, str) or not re.fullmatch(r"[0-9]{1,10}", pointer_version) or int(pointer_version) < 1 or int(pointer_version) > 2**31:
            raise CoreProofError("proof_query_invalid")
        return {"operation": operation, "project_id": project_id, "version_id": version_id, "object_key_sha256": object_key_sha256, "pointer_version": int(pointer_version)}
    return {"operation": operation, "project_id": project_id}


class CoreHandler(BaseHTTPRequestHandler):
    server_version = "QuillframeCore/1.0"
    # Tests and the hosted adapter may inject the durable nonce transaction at
    # the server boundary; the bounded cache remains the local default.
    nonce_consumer = staticmethod(_consume_nonce)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"schema": "quillframe_cloud_core_health_v1", "status": "ok", "chapter_scope": "CH001", "authority": False})
            return
        self._json(404, {"schema": "quillframe_cloud_core_error_v1", "code": "not_found", "authority": False})

    def _native_backup_verify(self) -> None:
        forbidden = (
            "X-Qf-Core-Proof-Alias", "X-Qf-Workspace-Id", "X-Qf-Session-Id", "X-Qf-Project-Id", "X-Qf-Identity", "X-Qf-Authority",
            "X-Qf-Chapter-Scope", "X-Quillframe-Internal", "X-Quillframe-Workspace-Id", "X-Quillframe-Session-Id",
            "X-Quillframe-Project-Id", "X-Quillframe-Identity", "X-Quillframe-Authority", "X-Quillframe-Chapter-Scope", "Authorization", "Cookie",
        )
        if "X-Qf-Core-Proof" not in self.headers or any(name in self.headers for name in forbidden) or self.headers.get("Content-Type") != "application/zip":
            self._json(403, {"schema": "quillframe_cloud_core_error_v1", "code": "container_boundary_forbidden", "authority": False})
            return
        try:
            query = _native_query(self.path)
        except CoreProofError as exc:
            self._json(400, {"schema": "quillframe_cloud_core_error_v1", "code": exc.code, "authority": False})
            return
        declared = self.headers.get("Content-Length")
        try:
            length = _parse_content_length(declared, transfer_encoding="Transfer-Encoding" in self.headers, limit=MAX_NATIVE_BACKUP_BODY)
            raw = _read_exact_body(self.rfile, length, limit=MAX_NATIVE_BACKUP_BODY)
            now = _active_clock()
            proof = self.headers["X-Qf-Core-Proof"]
            claims = _verify_core_proof(proof, raw, self.command, self.path, now, consume_nonce=False)
            if claims["project_id"] != query["project_id"] or claims["project_id"] is None or claims["chapter_scope"] != "CH001": raise CoreProofError("proof_project_invalid")
            if query["operation"] == "project.read":
                version_id = query["version_id"]
                expected_key = f"v2/{hashlib.sha256(claims['workspace_id'].encode('utf-8')).hexdigest()}/{claims['project_id']}/versions/{version_id}.qfbundle"
                expected_object_key_sha256 = "sha256:" + hashlib.sha256(expected_key.encode("utf-8")).hexdigest()
                if not hmac.compare_digest(str(query["object_key_sha256"]), expected_object_key_sha256): raise CoreProofError("proof_object_key_invalid")
            consumer = _active_nonce_consumer or _consume_nonce
            # Native verification burns a valid, identity-bound proof attempt
            # before C3A parses the ZIP; malformed bundles cannot be retried.
            consumer(
                session_id=claims["session_id"], project_id=claims["project_id"], nonce=claims["nonce"],
                proof_digest="sha256:" + hashlib.sha256(proof.encode("utf-8")).hexdigest(),
                issued_at=claims["issued_at"], expires_at=claims["expires_at"], now=now,
            )
            verified = QuillframeStore(read_only=True).verify_backup_bytes(raw)
            manifest = verified["manifest"]
            if manifest.get("project_id") != claims["project_id"] or manifest.get("chapter_scope") != "CH001" or manifest.get("schema") != "quillframe_backup_bundle_v1": raise BundleValidationError("native backup identity mismatch", code="bundle_identity")
            database_fingerprint = manifest.get("database_fingerprint")
            if not isinstance(database_fingerprint, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", database_fingerprint): raise BundleValidationError("native database fingerprint invalid", code="bundle_schema")
            body_fingerprint = fingerprint_bytes(raw)
            if query["operation"] == "project.read" and body_fingerprint != query["version_id"]: raise BundleValidationError("native version mismatch", code="native_version_mismatch")
            receipt = {
                "schema": "quillframe_native_backup_verification_v1", "bundle_schema": "quillframe_backup_bundle_v1",
                "body_fingerprint": body_fingerprint, "bundle_fingerprint": body_fingerprint, "project_id": claims["project_id"],
                "chapter_scope": "CH001", "database_fingerprint": database_fingerprint, "database_bytes": verified["database_bytes"],
                "blob_count": verified["blob_count"], "byte_size": len(raw), "verified": True, "authority": False,
            }
            self._json(200, receipt)
        except CoreProofError as exc:
            self._json(400, {"schema": "quillframe_cloud_core_error_v1", "code": exc.code, "authority": False})
        except BundleValidationError as exc:
            self._json(400, {"schema": "quillframe_cloud_core_error_v1", "code": getattr(exc, "code", "native_backup_invalid"), "authority": False})
        except Exception:
            self._json(400, {"schema": "quillframe_cloud_core_error_v1", "code": "native_backup_verification_failed", "authority": False})

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path == NATIVE_BACKUP_PATH:
            if self.command != "POST":
                self._json(405, {"schema": "quillframe_cloud_core_error_v1", "code": "method_not_allowed", "authority": False})
                return
            self._native_backup_verify()
            return
        forbidden = (
            "X-Qf-Core-Proof-Alias", "X-Qf-Workspace-Id", "X-Qf-Session-Id", "X-Qf-Project-Id", "X-Qf-Identity", "X-Qf-Authority",
            "X-Qf-Chapter-Scope", "X-Quillframe-Internal", "X-Quillframe-Workspace-Id", "X-Quillframe-Session-Id",
            "X-Quillframe-Project-Id", "X-Quillframe-Identity", "X-Quillframe-Authority", "X-Quillframe-Chapter-Scope",
            "Authorization", "Cookie",
        )
        if urlsplit(self.path).path != "/bridge" or "X-Qf-Core-Proof" not in self.headers or any(name in self.headers for name in forbidden):
            self._json(403, {"schema": "quillframe_cloud_core_error_v1", "code": "container_boundary_forbidden", "authority": False})
            return
        declared = self.headers.get("Content-Length")
        try:
            length = _parse_content_length(declared, transfer_encoding="Transfer-Encoding" in self.headers)
        except CoreProofError:
            bounded = declared is not None and re.fullmatch(r"[0-9]+", declared) and (int(declared) <= 0 or int(declared) > MAX_BODY)
            self._json(413 if bounded else 400, {"schema": "quillframe_cloud_core_error_v1", "code": "body_size_invalid", "authority": False})
            return
        try:
            raw = _read_exact_body(self.rfile, length)
            now = _active_clock()
            claims = _verify_core_proof(self.headers["X-Qf-Core-Proof"], raw, self.command, self.path, now, consume_nonce=False)
            request = _parse_canonical_body(raw)
            if set(request) != {"schema", "bridge_version", "request_id", "operation", "surface", "args", "authority"} or request.get("schema") != "quillframe_host_bridge_request_v11" or request.get("bridge_version") != "11" or request.get("surface") != "hosted_web" or request.get("authority") is not False or not isinstance(request.get("args"), dict):
                raise CoreProofError("bridge_request_invalid")
            operation = request.get("operation")
            if not isinstance(operation, str) or _project_id(operation, request) != claims["project_id"]:
                raise CoreProofError("proof_project_invalid")
            consumer = _active_nonce_consumer or _consume_nonce
            consumer(
                session_id=claims["session_id"], project_id=claims["project_id"], nonce=claims["nonce"],
                proof_digest="sha256:" + hashlib.sha256(self.headers["X-Qf-Core-Proof"].encode("utf-8")).hexdigest(),
                issued_at=claims["issued_at"], expires_at=claims["expires_at"], now=now,
            )
        except CoreProofError as exc:
            self._json(400, {"schema": "quillframe_cloud_core_error_v1", "code": exc.code, "authority": False})
            return
        except Exception:
            self._json(400, {"schema": "quillframe_cloud_core_error_v1", "code": "body_read_failed", "authority": False})
            return
        try:
            result = invoke(request)
        except Exception:
            self._json(500, {"schema": "quillframe_cloud_core_error_v1", "code": "core_invoke_failed", "authority": False})
            return
        self._json(200 if result.get("status") == "ok" else 400, result)

    def log_message(self, _format: str, *_args: object) -> None:
        # Request bodies, cookies, tokens, and headers must never reach logs.
        return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    ThreadingHTTPServer((args.host, args.port), CoreHandler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
