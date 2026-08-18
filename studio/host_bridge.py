#!/usr/bin/env python3
"""Typed Quillframe 0.9 Core/Product bridge.

Transport adapters may be loopback HTTP, hosted HTTP, Tauri-local IPC or CLI,
but they all invoke the same operation contract. This module is not an authority:
operation-specific Core code owns persistence and every authorized transition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core_operations import CoreOperations, OperationError
from persistence.quillframe_sqlite import ConflictError, IntegrityError, QuillframeStore
from product_operations import ProductOperationError, ProductOperations

CONTRACT_PATH = Path(__file__).with_name("host_bridge_contract.json")
REQUEST_SCHEMA = "quillframe_studio_host_bridge_request_v1"
RESULT_SCHEMA = "quillframe_studio_host_bridge_result_v1"
_SECRET_KEYS = {"token", "access_token", "api_key", "apikey", "password", "secret", "authorization", "credential"}

_STORE = QuillframeStore()
_CORE = CoreOperations(_STORE)
_PRODUCT = ProductOperations(_STORE)


class BridgeError(RuntimeError):
    def __init__(self, code: str, message: str, detail: Any = None):
        super().__init__(message)
        self.code = code
        self.detail = detail


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            out[str(key)] = "<secret-present>" if normalized in _SECRET_KEYS and child not in (None, "") else _redact(child)
        return out
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def require(args: dict[str, Any], key: str, typ: type | tuple[type, ...] = str):
    value = args.get(key)
    if not isinstance(value, typ) or (isinstance(value, str) and not value.strip()):
        raise BridgeError("invalid_args", f"{key} is required")
    return value


def _describe(_: dict[str, Any], surface: str) -> dict[str, Any]:
    value = contract()
    return {
        "schema": "quillframe_studio_host_bridge_description_v1",
        "framework_version": value["framework_version"],
        "contract_schema": value["schema"],
        "contract_version": value["version"],
        "product_model": value["product_model"],
        "surface": surface,
        "supported_operations": sorted(value["operations"]),
        "operation_contracts": value["operations"],
        "deferred_operations": value.get("deferred_operations", {}),
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "direct_core_store_access": False,
    }


def _doctor(args: dict[str, Any], _: str):
    return _STORE.doctor(args.get("project_id"), fix=args.get("fix") is True)


def _project_list(args: dict[str, Any], _: str):
    return _PRODUCT.project_list_portable()


def _project_create(args: dict[str, Any], _: str):
    loc = _STORE.create_project(require(args, "project_id"), require(args, "title"), args.get("language") or "zh-CN")
    return {"schema": "quillframe_project_create_result_v1", "project_id": loc.project_id, "created": True, "authority": False}


def _project_inspect(args: dict[str, Any], _: str):
    return _CORE.project_inspect(require(args, "project_id"))


def _project_search(args: dict[str, Any], _: str):
    return {"schema": "quillframe_search_results_v1", "project_id": require(args, "project_id"), "results": _STORE.search(args["project_id"], require(args, "query"), int(args.get("limit") or 30)), "authority": False}


def _project_backup(args: dict[str, Any], _: str):
    path = _STORE.backup_project(require(args, "project_id"))
    return {"schema": "quillframe_backup_result_v1", "project_id": args["project_id"], "bundle_ref": path.name, "verified": True, "authority": False}


def _project_export(args: dict[str, Any], _: str):
    return _PRODUCT.project_export(require(args, "project_id"))


def _project_import(args: dict[str, Any], _: str):
    replace = args.get("replace") is True
    if replace and args.get("user_authorized") is not True:
        raise BridgeError("authorization_required", "Replacing an existing project during import requires explicit user authorization")
    return _PRODUCT.project_import(require(args, "artifact_ref"), replace=replace)


def _project_delete(args: dict[str, Any], _: str):
    return _PRODUCT.project_delete(
        require(args, "project_id"),
        confirm_project_id=require(args, "confirm_project_id"),
        user_authorized=args.get("user_authorized") is True,
        backup_first=args.get("backup_first") is not False,
    )


def _artifact_read(args: dict[str, Any], _: str):
    return _PRODUCT.artifact_read(require(args, "artifact_ref"))


def _artifact_upload(args: dict[str, Any], _: str):
    return _PRODUCT.artifact_upload(require(args, "file_name"), require(args, "payload_base64"))


def _document_list(args: dict[str, Any], _: str):
    return _PRODUCT.document_list(require(args, "project_id"), args.get("document_kind"))


def _document_get(args: dict[str, Any], _: str):
    return _PRODUCT.document_get(require(args, "project_id"), require(args, "document_id"))


def _document_create(args: dict[str, Any], _: str):
    _STORE.create_document(
        require(args, "project_id"), require(args, "document_id"), require(args, "title"),
        args.get("document_kind") or "manuscript", args.get("story_node_id"),
    )
    return {"schema": "quillframe_document_create_result_v1", "created": True, "document_id": args["document_id"], "authority": False}


def _revision_list(args: dict[str, Any], _: str):
    return _PRODUCT.revision_list(require(args, "project_id"), require(args, "document_id"), int(args.get("limit") or 100))


def _revision_save(args: dict[str, Any], _: str):
    result = _STORE.save_revision(
        require(args, "project_id"), require(args, "document_id"), require(args, "content"),
        expected_parent_revision_id=args.get("expected_parent_revision_id"),
        source=require(args, "source"), authority_class=args.get("authority_class") or "proposal",
        provenance=args.get("provenance") if isinstance(args.get("provenance"), dict) else {},
    )
    return {"schema": "quillframe_document_revision_save_result_v1", **result, "authority": False}


def _revision_compare(args: dict[str, Any], _: str):
    return {"schema": "quillframe_document_revision_compare_result_v1", **_STORE.compare_revisions(require(args, "project_id"), require(args, "left_revision_id"), require(args, "right_revision_id")), "authority": False}


def _revision_restore(args: dict[str, Any], _: str):
    return _PRODUCT.revision_restore(
        require(args, "project_id"), require(args, "document_id"), require(args, "revision_id"),
        expected_parent_revision_id=args.get("expected_parent_revision_id"), source=args.get("source") or "user_restore",
    )


def _story(args: dict[str, Any], _: str):
    return _PRODUCT.story_projection(require(args, "project_id"))


def _plan(args: dict[str, Any], _: str):
    return _PRODUCT.plan_projection(require(args, "project_id"))


def _model_connect(args: dict[str, Any], _: str):
    return _PRODUCT.model_connect(require(args, "endpoint"), require(args, "access_token"))


def _model_list(args: dict[str, Any], _: str):
    return _PRODUCT.model_list()


def _model_get(args: dict[str, Any], _: str):
    return _PRODUCT.model_get(require(args, "service_id"))


def _author_run(args: dict[str, Any], _: str):
    payload = require(args, "payload", dict)
    return _CORE.start_author_run(
        require(args, "project_id"), task_mode=require(args, "task_mode"), target_ref=args.get("target_ref"),
        payload=payload, session_id=args.get("session_id"), idempotency_key=args.get("idempotency_key"),
    )


def _candidate_list(args: dict[str, Any], _: str):
    return _PRODUCT.candidate_list(require(args, "project_id"), int(args.get("limit") or 100))


def _candidate_get(args: dict[str, Any], _: str):
    return _PRODUCT.candidate_get(require(args, "project_id"), require(args, "candidate_id"))


def _candidate_accept(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError("authorization_required", "candidate.accept requires an explicit user action")
    return _CORE.accept_candidate(
        require(args, "project_id"), candidate_id=require(args, "candidate_id"),
        candidate_fingerprint=require(args, "candidate_fingerprint"), authorized_by=require(args, "authorized_by"),
        authorization=require(args, "authorization", dict), idempotency_key=require(args, "idempotency_key"),
    )


def _settle(args: dict[str, Any], _: str):
    return _CORE.settle(
        require(args, "project_id"), acceptance_id=require(args, "acceptance_id"), target_ref=require(args, "target_ref"),
        expected_before_fingerprint=require(args, "expected_before_fingerprint"), user_authorized=args.get("user_authorized") is True,
        idempotency_key=require(args, "idempotency_key"),
    )


def _feedback(args: dict[str, Any], _: str):
    return _CORE.observe_feedback(require(args, "project_id"), evidence_kind=require(args, "evidence_kind"), payload=require(args, "payload", dict), source_ref=args.get("source_ref"))


def _pub_preview(args: dict[str, Any], _: str):
    return _CORE.publication_preview(require(args, "project_id"), require(args, "acceptance_id"))


def _pub_build(args: dict[str, Any], _: str):
    return _CORE.publication_build(require(args, "project_id"), require(args, "acceptance_id"), args.get("format") or "md")


def _inspector(table: str) -> Callable[[dict[str, Any], str], dict[str, Any]]:
    return lambda args, _: _PRODUCT.inspector_table(require(args, "project_id"), table, limit=int(args.get("limit") or 100))


DISPATCH: dict[str, Callable[[dict[str, Any], str], dict[str, Any]]] = {
    "bridge.describe": _describe, "database.doctor": _doctor,
    "project.list": _project_list, "project.create": _project_create, "project.inspect": _project_inspect,
    "project.search": _project_search, "project.backup": _project_backup, "project.export": _project_export,
    "project.import": _project_import, "project.delete": _project_delete,
    "artifact.read": _artifact_read, "artifact.upload": _artifact_upload,
    "document.list": _document_list, "document.get": _document_get, "document.create": _document_create,
    "document.revisions.list": _revision_list, "document.revision.save": _revision_save,
    "document.revision.compare": _revision_compare, "document.revision.restore": _revision_restore,
    "story.inspect": _story, "plan.inspect": _plan,
    "model.connect": _model_connect, "model.list": _model_list, "model.get": _model_get,
    "author.run.start": _author_run, "candidate.list": _candidate_list, "candidate.get": _candidate_get,
    "candidate.accept": _candidate_accept, "settlement.apply": _settle, "feedback.observe": _feedback,
    "publication.preview": _pub_preview, "publication.build": _pub_build,
    "inspector.sessions.list": _inspector("sessions"), "inspector.runs.list": _inspector("runs"),
    "inspector.checkpoints.list": _inspector("checkpoints"), "inspector.context.list": _inspector("context_manifests"),
    "inspector.receipts.list": _inspector("receipts"), "inspector.candidates.list": _inspector("candidates"),
    "inspector.learning.list": _inspector("learning_evidence"), "inspector.reviews.list": _inspector("review_evidence"),
    "inspector.settlements.list": _inspector("settlements"),
}


def validate_request(req: dict[str, Any]) -> list[str]:
    value = contract()
    errors: list[str] = []
    if req.get("schema") != REQUEST_SCHEMA:
        errors.append(f"schema must be {REQUEST_SCHEMA}")
    if not isinstance(req.get("request_id"), str) or not req["request_id"].strip():
        errors.append("request_id must be non-empty string")
    op = req.get("operation")
    known = op in value["operations"] or op in value.get("deferred_operations", {})
    if not known:
        errors.append("unknown operation")
    if req.get("surface") not in value["surfaces"]:
        errors.append("unsupported surface")
    if not isinstance(req.get("args"), dict):
        errors.append("args must be object")
    if req.get("authority") is not False:
        errors.append("request authority must be false")
    if op in value["operations"] and isinstance(req.get("args"), dict):
        missing = [key for key in value["operations"][op].get("required_args", []) if req["args"].get(key) in (None, "")]
        if missing:
            errors.append("missing args: " + ", ".join(missing))
        allowed = value["operations"][op].get("allowed_surfaces")
        if allowed and req.get("surface") not in allowed:
            errors.append("operation is not authorized on this surface")
    return errors


def result(req: dict[str, Any], status: str, *, data: Any = None, error: Any = None) -> dict[str, Any]:
    # Credential values are deliberately removed before fingerprinting so even
    # deterministic request evidence cannot become a token-dependent side channel.
    request_evidence = _redact(req)
    out = {
        "schema": RESULT_SCHEMA, "request_id": req.get("request_id"), "operation": req.get("operation"),
        "surface": req.get("surface"), "status": status, "data": data, "error": _redact(error),
        "request_fingerprint": fp(request_evidence), "authority": False, "canon_authority": False,
        "framework_write_authority": False, "settlement_authority": False,
    }
    out["result_fingerprint"] = fp(out)
    return out


def invoke(req: dict[str, Any]) -> dict[str, Any]:
    errors = validate_request(req)
    if errors:
        return result(req, "invalid", error={"code": "invalid_request", "messages": errors, "mutation_performed": False})
    deferred = contract().get("deferred_operations", {})
    if req.get("operation") in deferred:
        return result(req, "unsupported", error={"code": "operation_deferred", "message": deferred[req["operation"]], "mutation_performed": False})
    try:
        return result(req, "ok", data=DISPATCH[req["operation"]](req["args"], req["surface"]))
    except (BridgeError, ProductOperationError, OperationError, ConflictError, IntegrityError, FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        return result(req, "failed", error={"code": getattr(exc, "code", type(exc).__name__), "message": str(exc), "detail": getattr(exc, "detail", None), "mutation_performed": False})
    except Exception as exc:
        return result(req, "failed", error={"code": "bridge_internal_error", "message": f"{type(exc).__name__}: {exc}", "mutation_performed": False})


def self_test() -> dict[str, Any]:
    desc = invoke({"schema": REQUEST_SCHEMA, "request_id": "self", "operation": "bridge.describe", "surface": "agent_package", "args": {}, "authority": False})
    generic = invoke({"schema": REQUEST_SCHEMA, "request_id": "bad", "operation": "command.invoke", "surface": "agent_package", "args": {}, "authority": False})
    deferred = invoke({"schema": REQUEST_SCHEMA, "request_id": "deferred", "operation": "author.run.execute", "surface": "local_app", "args": {}, "authority": False})
    secret_fp_a = result({"schema": REQUEST_SCHEMA, "request_id": "secret", "operation": "model.connect", "surface": "local_app", "args": {"endpoint": "http://localhost:1", "access_token": "alpha"}, "authority": False}, "failed")["request_fingerprint"]
    secret_fp_b = result({"schema": REQUEST_SCHEMA, "request_id": "secret", "operation": "model.connect", "surface": "local_app", "args": {"endpoint": "http://localhost:1", "access_token": "beta"}, "authority": False}, "failed")["request_fingerprint"]
    ok = (
        desc["status"] == "ok" and generic["status"] == "invalid" and deferred["status"] == "unsupported"
        and desc["authority"] is False and secret_fp_a == secret_fp_b
    )
    return {
        "quillframe_host_bridge_contract": "PASS" if ok else "FAIL",
        "contract_version": "5", "generic_mutation_dispatch": False,
        "deferred_fails_closed": deferred["status"] == "unsupported",
        "secret_value_affects_request_fingerprint": secret_fp_a != secret_fp_b,
        "authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("describe")
    sub.add_parser("self-test")
    inv = sub.add_parser("invoke")
    inv.add_argument("--request")
    args = parser.parse_args()
    if args.cmd == "describe":
        print(json.dumps(_describe({}, "cli"), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "self-test":
        value = self_test()
        print(json.dumps(value, indent=2))
        return 0 if value["quillframe_host_bridge_contract"] == "PASS" else 1
    raw = Path(args.request).read_text(encoding="utf-8") if args.request else sys.stdin.read()
    request = json.loads(raw)
    output = invoke(request)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
