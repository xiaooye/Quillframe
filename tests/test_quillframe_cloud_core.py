from __future__ import annotations

import json
import base64
import hashlib
import hmac
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from quillframe.cloud_core import CoreHandler, CoreProofError, PROJECT_REQUIRED, PROJECT_NULL, _parse_canonical_body, _project_id, configure_core_security
from persistence.quillframe_sqlite import QuillframeStore


class CloudCoreBoundaryTests(unittest.TestCase):
    key = bytes([7]) * 32

    def test_operation_matrix_matches_native_contract(self) -> None:
        with open("studio/host_bridge_contract.json", encoding="utf-8") as handle:
            contract = json.load(handle)
        hosted = {name: meta for name, meta in contract["operations"].items() if "hosted_web" in meta.get("allowed_surfaces", ["hosted_web"])}
        required = {name for name, meta in hosted.items() if "project_id" in meta.get("required_args", [])}
        null_scoped = {name for name, meta in hosted.items() if "project_id" not in meta.get("required_args", []) and name != "project.restore"}
        self.assertEqual(PROJECT_REQUIRED, required)
        self.assertEqual(PROJECT_NULL, null_scoped)
        for name in sorted(required):
            self.assertIsInstance(_project_id(name, {"args": {"project_id": "project_1"}}), str)
        for name in sorted(null_scoped):
            self.assertIsNone(_project_id(name, {"args": {}}))
        with self.assertRaises(Exception):
            _project_id("project.restore", {"args": {"project_id": "project_1"}})

    def setUp(self) -> None:
        self._env = {key: os.environ.get(key) for key in ("QUILLFRAME_CORE_PROOF_KEY_ID", "QUILLFRAME_CORE_PROOF_KEY_B64")}
        os.environ["QUILLFRAME_CORE_PROOF_KEY_ID"] = "current"
        os.environ["QUILLFRAME_CORE_PROOF_KEY_B64"] = base64.urlsafe_b64encode(self.key).decode().rstrip("=")
        self.nonce_calls = []
        configure_core_security(nonce_consumer=self._nonce_consumer, clock=lambda: int(__import__("time").time() * 1000))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), CoreHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.origin = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        configure_core_security(nonce_consumer=None, clock=None)

    def _nonce_consumer(self, *, session_id, nonce, proof_digest, project_id, issued_at, expires_at, now):
        self.nonce_calls.append((session_id, nonce, proof_digest, project_id, issued_at, expires_at, now))
        if len(self.nonce_calls) > 1:
            raise CoreProofError("core_nonce_replayed")

    def _request(self, body: bytes, *, proof: str | None, path: str = "/bridge", headers: dict[str, str] | None = None):
        request_headers = {"Content-Type": "application/json"}
        if proof:
            request_headers["X-Qf-Core-Proof"] = proof
        request_headers.update(headers or {})
        return urllib.request.Request(f"{self.origin}{path}", data=body, headers=request_headers, method="POST")

    def _native_request(self, body: bytes, *, proof: str | None, path: str = "/native/project-backup/verify?operation=project.upload&project_id=P1", headers: dict[str, str] | None = None):
        request_headers = {"Content-Type": "application/zip", "Content-Length": str(len(body))}
        if proof:
            request_headers["X-Qf-Core-Proof"] = proof
        request_headers.update(headers or {})
        return urllib.request.Request(f"{self.origin}{path}", data=body, headers=request_headers, method="POST")

    def _proof(self, body: bytes, *, project_id: str | None = None, path: str = "/bridge", nonce: str = "nonce_test_1", **overrides) -> str:
        now = int(__import__("time").time() * 1000)
        claims = {
            "schema": "quillframe_core_proof_v1", "key_id": "current", "method": "POST", "path": path,
            "body_sha256": "sha256:" + hashlib.sha256(body).hexdigest(), "workspace_id": "workspace_test",
            "session_id": "session_test", "project_id": project_id, "chapter_scope": "CH001",
            "issued_at": now, "expires_at": now + 30_000, "nonce": nonce,
            **overrides,
        }
        claims_bytes = json.dumps(claims, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        encoded = base64.urlsafe_b64encode(claims_bytes).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(hmac.new(self.key, claims_bytes, hashlib.sha256).digest()).decode().rstrip("=")
        return f"qfcp1.current.{encoded}.{signature}"

    def _body(self, *, operation: str = "bridge.describe", args: dict | None = None, **overrides) -> bytes:
        request = {
            "schema": "quillframe_host_bridge_request_v11",
            "bridge_version": "11",
            "request_id": "cloud-core-test",
            "operation": operation,
            "surface": "hosted_web",
            "args": {} if args is None else args,
            "authority": False,
            **overrides,
        }
        return json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def test_health_is_non_authoritative_and_no_store(self):
        with urllib.request.urlopen(f"{self.origin}/health", timeout=2) as response:
            payload = json.load(response)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(payload["schema"], "quillframe_cloud_core_health_v1")
        self.assertEqual(payload["chapter_scope"], "CH001")
        self.assertIs(payload["authority"], False)

    def test_native_backup_route_returns_exact_verified_receipt_for_c3a_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            store = QuillframeStore(Path(directory))
            store.create_project("P1", "Native project", "en")
            bundle = store.backup_project("P1").read_bytes()
        path = "/native/project-backup/verify?operation=project.upload&project_id=P1"
        with urllib.request.urlopen(self._native_request(bundle, proof=self._proof(bundle, project_id="P1", path=path)), timeout=3) as response:
            payload = json.load(response)
        self.assertEqual(
            set(payload),
            {"schema", "bundle_schema", "body_fingerprint", "bundle_fingerprint", "project_id", "chapter_scope", "database_fingerprint", "database_bytes", "blob_count", "byte_size", "verified", "authority"},
        )
        expected = "sha256:" + hashlib.sha256(bundle).hexdigest()
        self.assertEqual(payload["body_fingerprint"], expected)
        self.assertEqual(payload["bundle_fingerprint"], expected)
        self.assertEqual(payload["project_id"], "P1")
        self.assertEqual(payload["chapter_scope"], "CH001")
        self.assertIs(payload["verified"], True)
        self.assertIs(payload["authority"], False)

    def test_native_read_route_binds_exact_version_and_object_key_query(self):
        with tempfile.TemporaryDirectory() as directory:
            store = QuillframeStore(Path(directory))
            store.create_project("P1", "Native project", "en")
            bundle = store.backup_project("P1").read_bytes()
        version_id = "sha256:" + hashlib.sha256(bundle).hexdigest()
        object_key = f"v2/{hashlib.sha256(b'workspace_test').hexdigest()}/P1/versions/{version_id}.qfbundle"
        path = "/native/project-backup/verify?operation=project.read&project_id=P1&version_id=" + version_id + "&object_key_sha256=sha256:" + hashlib.sha256(object_key.encode()).hexdigest() + "&pointer_version=1"
        with urllib.request.urlopen(self._native_request(bundle, proof=self._proof(bundle, project_id="P1", path=path, nonce="native_read_valid"), path=path), timeout=3) as response:
            payload = json.load(response)
        self.assertEqual(payload["body_fingerprint"], version_id)

    def test_native_read_route_rejects_body_version_mismatch_after_burning_nonce(self):
        with tempfile.TemporaryDirectory() as directory:
            store = QuillframeStore(Path(directory))
            store.create_project("P1", "Native project", "en")
            bundle = store.backup_project("P1").read_bytes()
        wrong_version = "sha256:" + "f" * 64
        object_key = f"v2/{hashlib.sha256(b'workspace_test').hexdigest()}/P1/versions/{wrong_version}.qfbundle"
        path = "/native/project-backup/verify?operation=project.read&project_id=P1&version_id=" + wrong_version + "&object_key_sha256=sha256:" + hashlib.sha256(object_key.encode()).hexdigest() + "&pointer_version=1"
        with self.assertRaises(urllib.error.HTTPError) as rejected:
            urllib.request.urlopen(self._native_request(bundle, proof=self._proof(bundle, project_id="P1", path=path, nonce="native_read_wrong_version"), path=path), timeout=3)
        self.assertEqual(rejected.exception.code, 400)
        self.assertEqual(json.load(rejected.exception)["code"], "native_version_mismatch")
        rejected.exception.close()

    def test_native_backup_route_rejects_legacy_headers_identity_and_transport_before_verifier(self):
        body = b"not-a-zip"
        path = "/native/project-backup/verify?operation=project.upload&project_id=P1"
        for headers in ({"X-Quillframe-Internal": "bff-v1"}, {"Content-Type": "application/json"}):
            with self.assertRaises(urllib.error.HTTPError) as rejected:
                urllib.request.urlopen(self._native_request(body, proof=self._proof(body, project_id="P1", path=path, nonce="native_reject_" + str(len(headers))), path=path, headers=headers), timeout=2)
            self.assertIn(rejected.exception.code, {400, 403})
            rejected.exception.close()
        oversized = self._native_request(body, proof=self._proof(body, project_id="P1", path=path, nonce="native_oversized"), path=path, headers={"Content-Length": str(128 * 1024 * 1024 + 1)})
        with self.assertRaises(urllib.error.HTTPError) as rejected:
            urllib.request.urlopen(oversized, timeout=2)
        self.assertEqual(rejected.exception.code, 400)
        rejected.exception.close()

    def test_native_invalid_bundle_burns_proof_nonce_before_c3a_and_replay_fails(self):
        body = b"well-framed-but-not-a-zip"
        path = "/native/project-backup/verify?operation=project.upload&project_id=P1"
        proof = self._proof(body, project_id="P1", path=path, nonce="native_invalid_zip")
        with self.assertRaises(urllib.error.HTTPError) as first:
            urllib.request.urlopen(self._native_request(body, proof=proof, path=path), timeout=2)
        self.assertEqual(first.exception.code, 400)
        first.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as replay:
            urllib.request.urlopen(self._native_request(body, proof=proof, path=path), timeout=2)
        self.assertEqual(replay.exception.code, 400)
        self.assertEqual(json.load(replay.exception)["code"], "core_nonce_replayed")
        replay.exception.close()

    def test_bridge_requires_proof_and_rejects_legacy_headers(self):
        body = json.dumps(
            {
                "schema": "quillframe_host_bridge_request_v11",
                "bridge_version": "11",
                "request_id": "cloud-core-test",
                "operation": "bridge.describe",
                "surface": "hosted_web",
                "args": {},
                "authority": False,
            }
        , ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        blocked = self._request(body, proof=None)
        with self.assertRaises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(blocked, timeout=2)
        self.assertEqual(denied.exception.code, 403)
        self.assertEqual(json.load(denied.exception)["code"], "container_boundary_forbidden")
        denied.exception.close()

        allowed = self._request(body, proof=self._proof(body), headers={"X-Quillframe-Internal": "bff-v1"})
        with self.assertRaises(urllib.error.HTTPError) as denied_legacy:
            urllib.request.urlopen(allowed, timeout=2)
        self.assertEqual(denied_legacy.exception.code, 403)
        denied_legacy.exception.close()
        allowed = self._request(body, proof=self._proof(body))
        with urllib.request.urlopen(allowed, timeout=2) as response:
            payload = json.load(response)
        self.assertEqual(payload["schema"], "quillframe_host_bridge_result_v11")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["data"]["contract_version"], "11")
        self.assertIs(payload["authority"], False)
        with self.assertRaises(urllib.error.HTTPError) as replay:
            urllib.request.urlopen(self._request(body, proof=self._proof(body)), timeout=2)
        self.assertEqual(replay.exception.code, 400)
        replay.exception.close()
        changed = body.replace(b"cloud-core-test", b"cloud-core-tesx")
        with self.assertRaises(urllib.error.HTTPError) as tampered:
            urllib.request.urlopen(self._request(changed, proof=self._proof(body)), timeout=2)
        self.assertEqual(tampered.exception.code, 400)
        tampered.exception.close()

    def test_query_is_signed_as_received_without_reordering(self):
        body = self._body()
        path = "/bridge?b=2&a=1"
        with urllib.request.urlopen(self._request(body, proof=self._proof(body, path=path, nonce="nonce_query"), path=path), timeout=2) as response:
            self.assertEqual(json.load(response)["status"], "ok")
        with self.assertRaises(urllib.error.HTTPError) as reordered:
            urllib.request.urlopen(self._request(body, proof=self._proof(body, path=path, nonce="nonce_query_bad"), path="/bridge?a=1&b=2"), timeout=2)
        self.assertEqual(reordered.exception.code, 400)
        reordered.exception.close()

    def test_invalid_body_forms_do_not_consume_injected_nonce(self):
        valid = self._body()
        invalid_forms = [
            b'{"schema":"quillframe_host_bridge_request_v11","schema":"quillframe_host_bridge_request_v11"}',
            b'{ "authority":false,"args":{},"bridge_version":"11","operation":"bridge.describe","request_id":"cloud-core-test","schema":"quillframe_host_bridge_request_v11","surface":"hosted_web"}',
            b'{"authority":false,"args":{"project_id":"p"},"bridge_version":"11","operation":"bridge.describe","request_id":"cloud-core-test","schema":"quillframe_host_bridge_request_v11","surface":"hosted_web"}',
            self._body(args={"project_id": None}),
            valid[:-1] + b',"extra":1}',
            b'{"authority":false,"args":{},"bridge_version":"11","operation":"bridge.describe","request_id":"cloud-core-test","schema":"quillframe_host_bridge_request_v11","surface":"hosted_web","bad":NaN}',
        ]
        for index, candidate in enumerate(invalid_forms):
            with self.assertRaises(urllib.error.HTTPError) as rejected:
                urllib.request.urlopen(self._request(candidate, proof=self._proof(candidate, nonce=f"nonce_invalid_{index}")), timeout=2)
            self.assertEqual(rejected.exception.code, 400)
            rejected.exception.close()
        self.assertEqual(self.nonce_calls, [])

    def test_alias_headers_and_invoke_exception_are_redacted(self):
        body = self._body()
        aliases = [
            "X-Qf-Workspace-Id", "X-Qf-Session-Id", "X-Qf-Project-Id", "X-Qf-Identity", "X-Qf-Authority",
        ]
        for index, name in enumerate(aliases):
            with self.assertRaises(urllib.error.HTTPError) as rejected:
                urllib.request.urlopen(self._request(body, proof=self._proof(body, nonce=f"nonce_alias_{index}"), headers={name: "secret-sentinel"}), timeout=2)
            self.assertEqual(rejected.exception.code, 403)
            payload = json.load(rejected.exception)
            self.assertNotIn("secret-sentinel", json.dumps(payload))
            rejected.exception.close()
        with patch("quillframe.cloud_core.invoke", side_effect=RuntimeError("body-claims-nonce-key-sentinel")):
            with self.assertRaises(urllib.error.HTTPError) as failed:
                urllib.request.urlopen(self._request(body, proof=self._proof(body, nonce="nonce_invoke_failure")), timeout=2)
            self.assertEqual(failed.exception.code, 500)
            payload = json.load(failed.exception)
            self.assertEqual(payload["code"], "core_invoke_failed")
            self.assertNotIn("sentinel", json.dumps(payload))
            failed.exception.close()

    def test_parser_rejects_invalid_utf8_nonfinite_and_wrong_root_types(self):
        for raw in [b"\xff", b"{\"x\":NaN}", b"[]", b"null"]:
            with self.assertRaises(CoreProofError):
                _parse_canonical_body(raw)


if __name__ == "__main__":
    unittest.main()
