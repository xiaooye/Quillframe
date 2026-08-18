#!/usr/bin/env python3
"""Typed Quillframe 0.9 Studio/Core bridge.

All hosts invoke the same operation names and envelopes. Transport never grants
story authority; operation-specific Core code owns every durable transition.
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

from authority_projections import settlement_preflight
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
    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _SECRET_KEYS:
                result[str(key)] = "<secret-present>" if child not in (None, "") else child
            else:
                result[str(key)] = redact(child)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def require(args: dict[str, Any], key: str, typ: type | tuple[type, ...] = str):
    value = args.get(key)
    if not isinstance(value, typ) or (isinstance(value, str) and not value.strip()):
        raise BridgeError("invalid_args", f"{key} is required")
    return value


def describe(_: dict[str, Any], surface: str) -> dict[str, Any]:
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


def doctor(args: dict[str, Any], _: str):
    return _STORE.doctor(args.get("project_id"), fix=args.get("fix") is True)


def project_list(args: dict[str, Any], _: str):
    return _PRODUCT.project_list_portable()


def project_create(args: dict[str, Any], _: str):
    loc = _STORE.create_project(require(args, "project_id"), require(args, "title"), args.get("language") or "zh-CN")
    return {"schema": "quillframe_project_create_result_v1", "project_id": loc.project_id, "created": True, "authority": False}


def project_inspect(args: dict[str, Any], _: str):
    return _CORE.project_inspect(require(args, "project_id"))


def project_search(args: dict[str, Any], _: str):
    project_id = require(args, "project_id")
    return {"schema": "quillframe_search_results_v1", "project_id": project_id, "results": _STORE.search(project_id, require(args, "query"), int(args.get("limit") or 30)), "authority": False}


def project_backup(args: dict[str, Any], _: str):
    project_id = require(args, "project_id")
    path = _STORE.backup_project(project_id)
    return {"schema": "quillframe_backup_result_v1", "project_id": project_id, "bundle_ref": path.name, "verified": True, "authority": False}


def project_export(args: dict[str, Any], _: str):
    return _PRODUCT.project_export(require(args, "project_id"))


def project_import(args: dict[str, Any], _: str):
    replace = args.get("replace") is True
    if replace and args.get("user_authorized") is not True:
        raise BridgeError("authorization_required", "Replacing a project during import requires explicit user authorization")
    return _PRODUCT.project_import(require(args, "artifact_ref"), replace=replace)


def project_delete(args: dict[str, Any], _: str):
    return _PRODUCT.project_delete(
        require(args, "project_id"),
        confirm_project_id=require(args, "confirm_project_id"),
        user_authorized=args.get("user_authorized") is True,
        backup_first=args.get("backup_first") is not False,
    )


def artifact_read(args: dict[str, Any], _: str):
    return _PRODUCT.artifact_read(require(args, "artifact_ref"))


def artifact_upload(args: dict[str, Any], _: str):
    return _PRODUCT.artifact_upload(require(args, "file_name"), require(args, "payload_base64"))


def document_list(args: dict[str, Any], _: str):
    return _PRODUCT.document_list(require(args, "project_id"), args.get("document_kind"))


def document_get(args: dict[str, Any], _: str):
    return _PRODUCT.document_get(require(args, "project_id"), require(args, "document_id"))


def document_create(args: dict[str, Any], _: str):
    _STORE.create_document(
        require(args, "project_id"), require(args, "document_id"), require(args, "title"),
        args.get("document_kind") or "manuscript", args.get("story_node_id"),
    )
    return {"schema": "quillframe_document_create_result_v1", "document_id": args["document_id"], "created": True, "authority": False}


def revision_list(args: dict[str, Any], _: str):
    return _PRODUCT.revision_list(require(args, "project_id"), require(args, "document_id"), int(args.get("limit") or 100))


def revision_save(args: dict[str, Any], _: str):
    value = _STORE.save_revision(
        require(args, "project_id"), require(args, "document_id"), require(args, "content"),
        expected_parent_revision_id=args.get("expected_parent_revision_id"), source=require(args, "source"),
        authority_class=args.get("authority_class") or "proposal",
        provenance=args.get("provenance") if isinstance(args.get("provenance"), dict) else {},
    )
    return {"schema": "quillframe_document_revision_save_result_v1", **value, "authority": False}


def revision_compare(args: dict[str, Any], _: str):
    value = _STORE.compare_revisions(require(args, "project_id"), require(args, "left_revision_id"), require(args, "right_revision_id"))
    return {"schema": "quillframe_document_revision_compare_result_v1", **value, "authority": False}


def story_inspect(args: dict[str, Any], _: str):
    return _PRODUCT.story_projection(require(args, "project_id"))


def plan_inspect(args: dict[str, Any], _: str):
    return _PRODUCT.plan_projection(require(args, "project_id"))


def research_inspect(args: dict[str, Any], _: str):
    return _PRODUCT.research_projection(require(args, "project_id"))


def model_connect(args: dict[str, Any], _: str):
    return _PRODUCT.model_connect(require(args, "endpoint"), require(args, "access_token"))


def model_list(args: dict[str, Any], _: str):
    return _PRODUCT.model_list()


def model_get(args: dict[str, Any], _: str):
    return _PRODUCT.model_get(require(args, "service_id"))


def author_run(args: dict[str, Any], _: str):
    return _CORE.start_author_run(
        require(args, "project_id"), task_mode=require(args, "task_mode"), target_ref=args.get("target_ref"),
        payload=require(args, "payload", dict), session_id=args.get("session_id"), idempotency_key=args.get("idempotency_key"),
    )


def candidate_list(args: dict[str, Any], _: str):
    return _PRODUCT.candidate_list(require(args, "project_id"), int(args.get("limit") or 100))


def candidate_get(args: dict[str, Any], _: str):
    return _PRODUCT.candidate_get(require(args, "project_id"), require(args, "candidate_id"))


def candidate_accept(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError("authorization_required", "candidate.accept requires explicit user action")
    return _CORE.accept_candidate(
        require(args, "project_id"), candidate_id=require(args, "candidate_id"),
        candidate_fingerprint=require(args, "candidate_fingerprint"), authorized_by=require(args, "authorized_by"),
        authorization=require(args, "authorization", dict), idempotency_key=require(args, "idempotency_key"),
    )


def settlement_prepare(args: dict[str, Any], _: str):
    return settlement_preflight(_STORE, require(args, "project_id"), require(args, "acceptance_id"), require(args, "target_ref"))


def settlement_apply(args: dict[str, Any], _: str):
    return _CORE.settle(
        require(args, "project_id"), acceptance_id=require(args, "acceptance_id"), target_ref=require(args, "target_ref"),
        expected_before_fingerprint=require(args, "expected_before_fingerprint"), user_authorized=args.get("user_authorized") is True,
        idempotency_key=require(args, "idempotency_key"),
    )


def feedback_observe(args: dict[str, Any], _: str):
    return _CORE.observe_feedback(require(args, "project_id"), evidence_kind=require(args, "evidence_kind"), payload=require(args, "payload", dict), source_ref=args.get("source_ref"))


def publication_preview(args: dict[str, Any], _: str):
    return _CORE.publication_preview(require(args, "project_id"), require(args, "acceptance_id"))


def publication_build(args: dict[str, Any], _: str):
    return _CORE.publication_build(require(args, "project_id"), require(args, "acceptance_id"), args.get("format") or "md")


def inspector(table: str) -> Callable[[dict[str, Any], str], dict[str, Any]]:
    return lambda args, _: _PRODUCT.inspector_table(require(args, "project_id"), table, limit=int(args.get("limit") or 100))


DISPATCH: dict[str, Callable[[dict[str, Any], str], dict[str, Any]]] = {
    "bridge.describe": describe, "database.doctor": doctor,
    "project.list": project_list, "project.create": project_create, "project.inspect": project_inspect,
    "project.search": project_search, "project.backup": project_backup, "project.export": project_export,
    "project.import": project_import, "project.delete": project_delete, "artifact.read": artifact_read, "artifact.upload": artifact_upload,
    "document.list": document_list, "document.get": document_get, "document.create": document_create,
    "document.revisions.list": revision_list, "document.revision.save": revision_save, "document.revision.compare": revision_compare,
    "story.inspect": story_inspect, "plan.inspect": plan_inspect, "research.inspect": research_inspect,
    "model.connect": model_connect, "model.list": model_list, "model.get": model_get,
    "author.run.start": author_run, "candidate.list": candidate_list, "candidate.get": candidate_get,
    "candidate.accept": candidate_accept, "settlement.preflight": settlement_prepare, "settlement.apply": settlement_apply,
    "feedback.observe": feedback_observe, "publication.preview": publication_preview, "publication.build": publication_build,
    "inspector.sessions.list": inspector("sessions"), "inspector.runs.list": inspector("runs"),
    "inspector.checkpoints.list": inspector("checkpoints"), "inspector.context.list": inspector("context_manifests"),
    "inspector.receipts.list": inspector("receipts"), "inspector.candidates.list": inspector("candidates"),
    "inspector.learning.list": inspector("learning_evidence"), "inspector.reviews.list": inspector("review_evidence"),
    "inspector.settlements.list": inspector("settlements"),
}


def validate_request(request: dict[str, Any]) -> list[str]:
    value = contract()
    errors: list[str] = []
    if request.get("schema") != REQUEST_SCHEMA:
        errors.append(f"schema must be {REQUEST_SCHEMA}")
    if not isinstance(request.get("request_id"), str) or not request["request_id"].strip():
        errors.append("request_id must be non-empty string")
    operation = request.get("operation")
    known = operation in value["operations"] or operation in value.get("deferred_operations", {})
    if not known:
        errors.append("unknown operation")
    if request.get("surface") not in value["surfaces"]:
        errors.append("unsupported surface")
    if not isinstance(request.get("args"), dict):
        errors.append("args must be object")
    if request.get("authority") is not False:
        errors.append("request authority must be false")
    if operation in value["operations"] and isinstance(request.get("args"), dict):
        missing = [key for key in value["operations"][operation].get("required_args", []) if request["args"].get(key) in (None, "")]
        if missing:
            errors.append("missing args: " + ", ".join(missing))
        allowed = value["operations"][operation].get("allowed_surfaces")
        if allowed and request.get("surface") not in allowed:
            errors.append("operation is not authorized on this surface")
    return errors


def envelope(request: dict[str, Any], status: str, *, data: Any = None, error: Any = None) -> dict[str, Any]:
    result = {
        "schema": RESULT_SCHEMA,
        "request_id": request.get("request_id"),
        "operation": request.get("operation"),
        "surface": request.get("surface"),
        "status": status,
        "data": data,
        "error": redact(error),
        "request_fingerprint": fingerprint(redact(request)),
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    result["result_fingerprint"] = fingerprint(result)
    return result


def invoke(request: dict[str, Any]) -> dict[str, Any]:
    errors = validate_request(request)
    if errors:
        return envelope(request, "invalid", error={"code": "invalid_request", "messages": errors, "mutation_performed": False})
    deferred = contract().get("deferred_operations", {})
    if request.get("operation") in deferred:
        return envelope(request, "unsupported", error={"code": "operation_deferred", "message": deferred[request["operation"]], "mutation_performed": False})
    try:
        return envelope(request, "ok", data=DISPATCH[request["operation"]](request["args"], request["surface"]))
    except (BridgeError, ProductOperationError, OperationError, ConflictError, IntegrityError, FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        return envelope(request, "failed", error={"code": getattr(exc, "code", type(exc).__name__), "message": str(exc), "detail": getattr(exc, "detail", None), "mutation_performed": False})
    except Exception as exc:
        return envelope(request, "failed", error={"code": "bridge_internal_error", "message": f"{type(exc).__name__}: {exc}", "mutation_performed": False})


def self_test() -> dict[str, Any]:
    description = invoke({"schema": REQUEST_SCHEMA, "request_id": "self", "operation": "bridge.describe", "surface": "agent_package", "args": {}, "authority": False})
    generic = invoke({"schema": REQUEST_SCHEMA, "request_id": "bad", "operation": "command.invoke", "surface": "agent_package", "args": {}, "authority": False})
    deferred = invoke({"schema": REQUEST_SCHEMA, "request_id": "deferred", "operation": "document.revision.restore", "surface": "local_app", "args": {}, "authority": False})
    a = envelope({"schema": REQUEST_SCHEMA, "request_id": "secret", "operation": "model.connect", "surface": "local_app", "args": {"endpoint": "http://localhost:1", "access_token": "alpha"}, "authority": False}, "failed")["request_fingerprint"]
    b = envelope({"schema": REQUEST_SCHEMA, "request_id": "secret", "operation": "model.connect", "surface": "local_app", "args": {"endpoint": "http://localhost:1", "access_token": "beta"}, "authority": False}, "failed")["request_fingerprint"]
    ok = description["status"] == "ok" and generic["status"] == "invalid" and deferred["status"] == "unsupported" and a == b
    return {
        "quillframe_host_bridge_contract": "PASS" if ok else "FAIL",
        "contract_version": "5",
        "generic_mutation_dispatch": False,
        "deferred_fails_closed": deferred["status"] == "unsupported",
        "secret_value_affects_request_fingerprint": a != b,
        "authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("describe")
    sub.add_parser("self-test")
    invoke_parser = sub.add_parser("invoke")
    invoke_parser.add_argument("--request")
    args = parser.parse_args()
    if args.cmd == "describe":
        print(json.dumps(describe({}, "cli"), ensure_ascii=False, indent=2)); return 0
    if args.cmd == "self-test":
        value = self_test(); print(json.dumps(value, indent=2)); return 0 if value["quillframe_host_bridge_contract"] == "PASS" else 1
    raw = Path(args.request).read_text(encoding="utf-8") if args.request else sys.stdin.read()
    output = invoke(json.loads(raw)); print(json.dumps(output, ensure_ascii=False, indent=2)); return 0 if output["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
