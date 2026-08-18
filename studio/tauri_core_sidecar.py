from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC = ROOT / "harness" / "semantic_workers"
QUALITY = ROOT / "quality"
for path in (ROOT, SEMANTIC, QUALITY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from model_runtime.persistence import SQLiteModelServiceRepository  # noqa: E402
from model_runtime.secrets import SecretStore  # noqa: E402
from persistence.quillframe_sqlite import QuillframeStore  # noqa: E402
from studio import host_bridge  # noqa: E402

SIDECAR_SCHEMA = "quillframe_tauri_sidecar_result_v1"
SECRET_REF_PREFIX = "keyring:qf:"


class TauriInjectedSecretStore(SecretStore):
    """Per-invocation SecretStore hydrated from the Tauri host keychain."""

    def __init__(self, seeded: dict[str, str] | None = None, *, prepared_ref: str | None = None) -> None:
        self._values = dict(seeded or {})
        self._prepared_ref = prepared_ref
        self._prepared_used = False
        self._actions: list[dict[str, str]] = []

    def checkpoint(self) -> tuple[dict[str, str], bool, list[dict[str, str]]]:
        return copy.deepcopy(self._values), self._prepared_used, copy.deepcopy(self._actions)

    def rollback(self, checkpoint: tuple[dict[str, str], bool, list[dict[str, str]]]) -> None:
        self._values, self._prepared_used, self._actions = copy.deepcopy(checkpoint)

    def put(self, secret: str) -> str:
        if not isinstance(secret, str) or not secret:
            raise ValueError("credential secret must be a non-empty string")
        if self._prepared_ref is None or self._prepared_used:
            raise RuntimeError("Tauri host did not preallocate a durable credential reference")
        if not self._prepared_ref.startswith(SECRET_REF_PREFIX):
            raise ValueError("prepared credential reference has an invalid namespace")
        self._prepared_used = True
        self._values[self._prepared_ref] = secret
        self._actions.append({"kind": "put", "credential_ref": self._prepared_ref})
        return self._prepared_ref

    def resolve(self, reference: str) -> str:
        try:
            return self._values[reference]
        except KeyError as exc:
            raise KeyError("credential reference unavailable") from exc

    def delete(self, reference: str) -> None:
        self._values.pop(reference, None)
        self._actions.append({"kind": "delete", "credential_ref": reference})

    def present(self, reference: str | None) -> bool:
        return bool(reference and reference in self._values)

    @property
    def prepared_used(self) -> bool:
        return self._prepared_used

    @property
    def actions(self) -> list[dict[str, str]]:
        return copy.deepcopy(self._actions)


def _credential_refs() -> dict[str, Any]:
    store = QuillframeStore()
    repository = SQLiteModelServiceRepository(store)
    refs: set[str] = set()
    for public in repository.list_services():
        service_id = str(public.get("service_id") or "")
        if not service_id:
            continue
        internal = repository.get_internal(service_id)
        reference = internal.get("credential_ref")
        if isinstance(reference, str) and reference:
            refs.add(reference)
    return {
        "schema": "quillframe_tauri_credential_refs_v1",
        "credential_refs": sorted(refs),
        "secret_values_exposed": False,
        "authority": False,
    }


def _scrub(value: Any, secrets: set[str]) -> Any:
    if isinstance(value, dict):
        return {str(key): _scrub(child, secrets) for key, child in value.items()}
    if isinstance(value, list):
        return [_scrub(child, secrets) for child in value]
    if isinstance(value, str):
        out = value
        for secret in sorted(secrets, key=len, reverse=True):
            if secret:
                out = out.replace(secret, "<redacted>")
        return out
    return value


def _invoke(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload.get("request")
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    credentials = payload.get("credential_secrets") or {}
    if not isinstance(credentials, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in credentials.items()):
        raise ValueError("credential_secrets must be a string map")
    prepared_ref = payload.get("prepared_secret_ref")
    if prepared_ref is not None and not isinstance(prepared_ref, str):
        raise ValueError("prepared_secret_ref must be a string")

    secret_values = {value for value in credentials.values() if value}
    args = request.get("args") if isinstance(request.get("args"), dict) else {}
    request_token = args.get("access_token")
    if isinstance(request_token, str) and request_token:
        secret_values.add(request_token)

    secret_store = TauriInjectedSecretStore(credentials, prepared_ref=prepared_ref)
    checkpoint = secret_store.checkpoint()
    host_bridge.configure_secret_store(secret_store)
    result = host_bridge.invoke(request)
    if not isinstance(result, dict):
        secret_store.rollback(checkpoint)
        raise RuntimeError("Host Bridge returned a non-object result")

    ok = result.get("status") == "ok"
    if not ok:
        secret_store.rollback(checkpoint)

    wrapper = {
        "schema": SIDECAR_SCHEMA,
        "bridge_result": result,
        "secret_actions": secret_store.actions if ok else [],
        "prepared_secret_consumed": bool(secret_store.prepared_used) if ok else False,
        "secret_values_exposed": False,
        "authority": False,
    }
    return _scrub(wrapper, secret_values)


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.readline()
    if not raw.strip():
        raise ValueError("stdin JSON payload required")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("stdin payload must be an object")
    return value


def _self_test() -> dict[str, Any]:
    sentinel = "TAURI-SECRET-SENTINEL"
    prepared_ref = SECRET_REF_PREFIX + uuid.uuid4().hex
    store = TauriInjectedSecretStore({"keyring:qf:existing": "existing"}, prepared_ref=prepared_ref)
    checkpoint = store.checkpoint()
    returned = store.put(sentinel)
    assert returned == prepared_ref
    assert store.resolve(prepared_ref) == sentinel
    assert store.present("keyring:qf:existing")
    assert store.actions == [{"kind": "put", "credential_ref": prepared_ref}]
    store.delete("keyring:qf:existing")
    assert store.actions[-1] == {"kind": "delete", "credential_ref": "keyring:qf:existing"}
    store.rollback(checkpoint)
    assert not store.present(prepared_ref)
    assert store.present("keyring:qf:existing")

    with tempfile.TemporaryDirectory() as temp:
        old = os.environ.get("QUILLFRAME_DATA_DIR")
        os.environ["QUILLFRAME_DATA_DIR"] = temp
        try:
            host_bridge.configure_secret_store(TauriInjectedSecretStore())
            request = {
                "schema": host_bridge.REQUEST_SCHEMA,
                "request_id": "tauri-sidecar-self-test",
                "operation": "bridge.describe",
                "surface": "local_app",
                "args": {},
                "authority": False,
            }
            result = host_bridge.invoke(request)
            assert result["status"] == "ok"
            assert result["data"]["contract_version"] == "8"
            refs = _credential_refs()
            assert refs["credential_refs"] == []
        finally:
            if old is None:
                os.environ.pop("QUILLFRAME_DATA_DIR", None)
            else:
                os.environ["QUILLFRAME_DATA_DIR"] = old

    serialized = json.dumps({"ref": prepared_ref, "actions": store.actions})
    assert sentinel not in serialized
    return {
        "schema": "quillframe_tauri_sidecar_self_test_v1",
        "status": "PASS",
        "host_bridge_v8": True,
        "prepared_reference_contract": True,
        "rollback_contract": True,
        "secret_values_exposed": False,
        "authority": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    command = args[0] if args else "invoke"
    try:
        if command == "credential-refs":
            output = _credential_refs()
        elif command == "invoke":
            output = _invoke(_read_stdin_json())
        elif command == "self-test":
            output = _self_test()
        else:
            raise ValueError(f"unknown sidecar command: {command}")
        print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        safe = {
            "schema": "quillframe_tauri_sidecar_error_v1",
            "status": "failed",
            "code": type(exc).__name__,
            "message": str(exc),
            "secret_values_exposed": False,
            "authority": False,
        }
        print(json.dumps(safe, ensure_ascii=False, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
