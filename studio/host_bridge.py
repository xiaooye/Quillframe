#!/usr/bin/env python3
"""Typed Quillframe Host Bridge v11.

Transports may be local HTTP, hosted HTTP or Tauri-local IPC, but semantic
operations are shared here. The delivery surface never becomes the authority;
operation-specific Core code performs any authorized state transition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_runtime import QuillframeAgentRuntime
from core_operations import CoreOperations, OperationError
from model_runtime import (
    MemorySecretStore,
    ModelRoute,
    ModelRuntimeError,
    ModelTaskProfile,
    RouteError,
    SecretStore,
    preview_route,
)
from model_runtime.service_facade import ModelServiceFacade
from persistence.context_repository import ContextRepository
from persistence.quillframe_sqlite import ConflictError, IntegrityError, QuillframeStore
from production_runtime import NovelWorkflowEngine, ProductionRunError, ProductionRunExecutor, WorkflowError
from production_runtime.workflow_service import NovelWorkflowService

CONTRACT_PATH = Path(__file__).with_name("host_bridge_contract.json")
BRIDGE_VERSION = "11"
REQUEST_SCHEMA = "quillframe_host_bridge_request_v11"
RESULT_SCHEMA = "quillframe_host_bridge_result_v11"

_SECRET_REQUEST_KEYS = {"access_token", "api_key", "apikey", "password", "secret", "token"}
_SECRET_OPERATIONS = {"model.service.add", "model.service.token.replace"}
_PUBLIC_ERROR_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_secret_store: SecretStore = MemorySecretStore()
_agent_runtime_instance: QuillframeAgentRuntime | None = None


class BridgeError(RuntimeError):
    def __init__(self, code: str, message: str, detail: Any = None):
        super().__init__(message)
        self.code = code
        self.detail = detail


def canonical(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fp(v: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(v).encode()).hexdigest()


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
    """Remove credential keys and scrub their values from nested strings.

    Business authorization evidence remains fingerprint-bound because only values
    originating from explicitly credential-bearing fields are treated as secrets.
    """
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


def contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def store(*, read_only: bool = False) -> QuillframeStore:
    return QuillframeStore(read_only=read_only)


def ops(*, read_only: bool = False) -> CoreOperations:
    return CoreOperations(store(read_only=read_only))


def configure_secret_store(secret_store: SecretStore) -> None:
    """Host injection point: Tauri keychain / server-side secure secret facility."""
    global _secret_store, _agent_runtime_instance
    _secret_store = secret_store
    _agent_runtime_instance = None


def agent_runtime(*, read_only: bool = False) -> QuillframeAgentRuntime:
    global _agent_runtime_instance
    if read_only:
        return QuillframeAgentRuntime(secret_store=_secret_store, store=store(read_only=True))
    if _agent_runtime_instance is None:
        _agent_runtime_instance = QuillframeAgentRuntime(secret_store=_secret_store, store=store())
    return _agent_runtime_instance


def model_services(*, read_only: bool = False) -> ModelServiceFacade:
    return ModelServiceFacade(agent_runtime(read_only=read_only))


def production_runtime(*, read_only: bool = False) -> ProductionRunExecutor:
    return ProductionRunExecutor(store(read_only=read_only), agent_runtime(read_only=read_only))


def workflow_service(*, read_only: bool = False) -> NovelWorkflowService:
    return NovelWorkflowService(store(read_only=read_only))


def require(args: dict[str, Any], key: str, typ: type | tuple[type, ...] = str):
    value = args.get(key)
    if not isinstance(value, typ) or (isinstance(value, str) and not value.strip()):
        raise BridgeError("invalid_args", f"{key} is required")
    return value


def _describe(_: dict[str, Any], surface: str):
    c = contract()
    operation_contracts = {
        name: {
            "kind": metadata["kind"],
            "required_args": list(metadata.get("required_args", [])),
            **({"allowed_surfaces": list(metadata["allowed_surfaces"])} if "allowed_surfaces" in metadata else {}),
        }
        for name, metadata in c["operations"].items()
    }
    return {
        "schema": "quillframe_host_bridge_description_v11",
        "framework_version": "1.0.0-dev.0",
        "contract_version": c["version"],
        "surface": surface,
        "operations": sorted(operation_contracts),
        "operation_contracts": operation_contracts,
        "deferred_operations": c.get("deferred_operations", {}),
        "secret_boundary": c.get("secret_boundary", {}),
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "direct_core_store_access": False,
    }


def _doctor(args: dict[str, Any], surface: str):
    if args.get("fix") is True:
        raise BridgeError("invalid_args", "database.doctor is read-only; fix is not supported")
    return store(read_only=surface == "agent_package").doctor(args.get("project_id"), fix=False)


def _project_list(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").project_list(limit=int(args.get("limit") or 100))


def _project_create(args: dict[str, Any], _: str):
    loc = store().create_project(require(args, "project_id"), require(args, "title"), args.get("language") or "zh-CN")
    context = ops().project_inspect(loc.project_id)
    return {
        "schema": "quillframe_project_create_result_v1_0",
        "manifest": context["manifest"],
        "manifest_fingerprint": context["manifest_fingerprint"],
        "chapter_scope": "CH001",
        "data_boundary": ".quillframe/data",
        "created": True,
        "authority": False,
    }


def _project_inspect(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").project_inspect(require(args, "project_id"))


def _project_search(args: dict[str, Any], surface: str):
    return {"schema": "quillframe_search_results_v1", "results": store(read_only=surface == "agent_package").search(require(args, "project_id"), require(args, "query"), int(args.get("limit") or 30)), "authority": False}


def _project_backup(args: dict[str, Any], _: str):
    path = store().backup_project(require(args, "project_id"))
    return {"schema": "quillframe_backup_result_v1", "project_id": args["project_id"], "bundle_ref": path.name, "verified": True, "authority": False}


def _project_restore(args: dict[str, Any], _: str):
    loc = store().restore_project(Path(require(args, "bundle_path")), replace=args.get("replace") is True)
    return {"schema": "quillframe_restore_result_v1", "project_id": loc.project_id, "restored": True, "authority": False}


def _document_list(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").document_list(
        require(args, "project_id"),
        document_kind=args.get("document_kind") if isinstance(args.get("document_kind"), str) else None,
        limit=int(args.get("limit") or 500),
    )


def _document_create(args: dict[str, Any], _: str):
    store().create_document(require(args, "project_id"), require(args, "document_id"), require(args, "title"), args.get("document_kind") or "manuscript", args.get("story_node_id"))
    return {"schema": "quillframe_document_create_result_v1", "created": True, "document_id": args["document_id"], "authority": False}


def _document_open(args: dict[str, Any], surface: str):
    project_id = require(args, "project_id")
    document_id = require(args, "document_id")
    with store(read_only=surface == "agent_package").open_project(project_id) as conn:
        doc = conn.execute("SELECT document_id,story_node_id,document_kind,title,created_at FROM documents WHERE document_id=?", (document_id,)).fetchone()
        if not doc:
            raise KeyError(document_id)
        revision = store(read_only=surface == "agent_package").latest_revision(conn, document_id)
    latest = dict(revision) if revision else None
    if latest:
        latest["provenance"] = json.loads(latest.pop("provenance_json") or "{}")
    return {"schema": "quillframe_document_projection_v1", "project_id": project_id, "document": dict(doc), "latest_revision": latest, "authority": False}


def _revisions_list(args: dict[str, Any], surface: str):
    project_id = require(args, "project_id")
    document_id = require(args, "document_id")
    limit = max(1, min(int(args.get("limit") or 100), 500))
    with store(read_only=surface == "agent_package").open_project(project_id) as conn:
        rows = [dict(row) for row in conn.execute("SELECT revision_id,document_id,parent_revision_id,content_fingerprint,created_at,source,authority_class,provenance_json FROM document_revisions WHERE document_id=? ORDER BY created_at DESC,rowid DESC LIMIT ?", (document_id, limit))]
    for row in rows:
        row["provenance"] = json.loads(row.pop("provenance_json") or "{}")
    return {"schema": "quillframe_document_revision_list_v1", "project_id": project_id, "document_id": document_id, "items": rows, "authority": False}


def _revision_save(args: dict[str, Any], _: str):
    source = require(args, "source")
    if source == "production_runtime":
        raise BridgeError("reserved_provenance", "production_runtime provenance is Core-owned and cannot be supplied through document.revision.save")
    return store().save_revision(require(args, "project_id"), require(args, "document_id"), require(args, "content"), expected_parent_revision_id=args.get("expected_parent_revision_id"), source=source, authority_class=args.get("authority_class") or "proposal", provenance=args.get("provenance") if isinstance(args.get("provenance"), dict) else {})


def _revision_compare(args: dict[str, Any], surface: str):
    return store(read_only=surface == "agent_package").compare_revisions(require(args, "project_id"), require(args, "left_revision_id"), require(args, "right_revision_id"))


def _author_run(args: dict[str, Any], _: str):
    project_id = require(args, "project_id")
    payload = require(args, "payload", dict)
    chapter_id = require(payload, "chapter_id")
    author_profile = payload.get("author_profile") or "guided"
    # Validate the hard chapter/profile boundary before Core persists a run row.
    NovelWorkflowEngine.start(
        project_id=project_id,
        run_id="preflight",
        chapter_id=chapter_id,
        author_profile=author_profile,
    )
    result = ops().start_author_run(
        project_id,
        task_mode=require(args, "task_mode"),
        target_ref=args.get("target_ref"),
        payload=payload,
        session_id=args.get("session_id"),
        idempotency_key=args.get("idempotency_key"),
    )
    result["workflow"] = workflow_service().start(
        project_id=project_id,
        run_id=result["run_id"],
        chapter_id=chapter_id,
        author_profile=author_profile,
    )
    return result


def _author_run_status(args: dict[str, Any], surface: str):
    return production_runtime(read_only=surface == "agent_package").status(require(args, "project_id"), require(args, "run_id"))


def _author_run_resume(args: dict[str, Any], _: str):
    return workflow_service().resume(
        project_id=require(args, "project_id"),
        run_id=require(args, "run_id"),
        cursor=require(args, "cursor", int),
        idempotency_key=require(args, "idempotency_key"),
    )


def _author_run_cancel(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError("authorization_required", "author.run.cancel requires an explicit user action")
    return workflow_service().cancel(
        project_id=require(args, "project_id"),
        run_id=require(args, "run_id"),
        cursor=require(args, "cursor", int),
        idempotency_key=require(args, "idempotency_key"),
        user_authorized=True,
    )


def _author_run_events(args: dict[str, Any], surface: str):
    return workflow_service(read_only=surface == "agent_package").events(
        run_id=require(args, "run_id"),
        cursor=require(args, "cursor", int),
    )


def _author_run_execute(args: dict[str, Any], _: str):
    return production_runtime().execute(
        require(args, "project_id"),
        require(args, "run_id"),
        service_id=require(args, "service_id"),
        instruction=require(args, "instruction"),
        document_id=args.get("document_id"),
        model_preference=args.get("model_id"),
        stage_budgets=args.get("stage_budgets") if isinstance(args.get("stage_budgets"), dict) else None,
        reader_grip=require(args, "reader_grip"),
        rule_material=require(args, "rule_material", list),
        reader_visible_context=args.get("reader_visible_context") if isinstance(args.get("reader_visible_context"), list) else None,
        independent_provenance=require(args, "independent_provenance", dict),
        repair_preservation=args.get("repair_preservation") if isinstance(args.get("repair_preservation"), dict) else None,
    )


def _author_independent_submit(args: dict[str, Any], _: str):
    return production_runtime().submit_independent(
        require(args, "project_id"),
        require(args, "run_id"),
        peer_packet=require(args, "peer_packet", dict),
        result=require(args, "result", dict),
        independence_receipt=require(args, "independence_receipt", dict),
    )


def _author_independent_dispatch_prepare(args: dict[str, Any], _: str):
    return production_runtime().prepare_independent_dispatch(
        require(args, "project_id"),
        require(args, "run_id"),
        provider=require(args, "provider"),
        parent_session_id=require(args, "parent_session_id"),
    )


def _author_context_refresh(args: dict[str, Any], _: str):
    bundle = production_runtime().refresh_context(
        require(args, "project_id"), require(args, "run_id"), service_id=require(args, "service_id"), instruction=require(args, "instruction"),
        model_preference=args.get("model_id"), stage_budgets=args.get("stage_budgets") if isinstance(args.get("stage_budgets"), dict) else None,
        reason=args.get("reason") or "explicit_refresh",
    )
    return {"schema": "quillframe_production_context_refresh_result_v1", "run_id": args["run_id"], "bundle_fingerprint": bundle["bundle_fingerprint"], "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"], "supersedes_bundle_fingerprint": bundle.get("supersedes_bundle_fingerprint"), "authority": False}


def _model_add(args: dict[str, Any], _: str):
    return model_services().connect(require(args, "endpoint"), require(args, "access_token"))


def _model_list(_: dict[str, Any], surface: str):
    return model_services(read_only=surface == "agent_package").list()


def _model_get(args: dict[str, Any], surface: str):
    return model_services(read_only=surface == "agent_package").get(require(args, "service_id"))


def _model_discover(args: dict[str, Any], _: str):
    return model_services().discover(require(args, "service_id"))


def _model_test(args: dict[str, Any], _: str):
    return model_services().test(require(args, "service_id"), model_id=args.get("model_id"), verify_tools=args.get("verify_tools") is True)


def _model_capabilities(args: dict[str, Any], surface: str):
    return model_services(read_only=surface == "agent_package").capabilities(require(args, "service_id"))


def _model_route_preview(args: dict[str, Any], _: str):
    profile = ModelTaskProfile.from_dict(require(args, "task_profile", dict))
    routes = [
        ModelRoute.from_dict(item)
        for item in require(args, "available_routes", list)
    ]
    return preview_route(
        project_id=require(args, "project_id"),
        profile=profile,
        routes=routes,
        manager_invocation_id=require(args, "manager_invocation_id"),
    )


def _model_token_replace(args: dict[str, Any], _: str):
    return agent_runtime().replace_access_token(require(args, "service_id"), require(args, "access_token"))


def _model_token_remove(args: dict[str, Any], _: str):
    return agent_runtime().remove_access_token(require(args, "service_id"))


def _model_delete(args: dict[str, Any], _: str):
    return agent_runtime().delete_model_service(require(args, "service_id"))


def _candidate_review_get(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").candidate_review_get(require(args, "project_id"), candidate_id=require(args, "candidate_id"))

def _candidate_visible_get(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").candidate_visible_get(require(args, "project_id"), candidate_id=require(args, "candidate_id"))


def _candidate_reject(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError("authorization_required", "candidate.reject requires an explicit user action")
    return ops().reject_candidate(
        require(args, "project_id"), candidate_id=require(args, "candidate_id"),
        candidate_fingerprint=require(args, "candidate_fingerprint"), authorized_by=require(args, "authorized_by"),
        authorization=require(args, "authorization", dict), idempotency_key=require(args, "idempotency_key"),
        reason=args.get("reason") if isinstance(args.get("reason"), str) else None,
    )


def _candidate_revision_request(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError("authorization_required", "candidate.revision.request requires an explicit user action")
    return ops().request_candidate_revision(
        require(args, "project_id"), candidate_id=require(args, "candidate_id"),
        candidate_fingerprint=require(args, "candidate_fingerprint"), revision_request=require(args, "revision_request", dict),
        authorized_by=require(args, "authorized_by"), authorization=require(args, "authorization", dict),
        idempotency_key=require(args, "idempotency_key"),
    )


def _settlement_preflight(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").settlement_preflight(
        require(args, "project_id"), acceptance_id=require(args, "acceptance_id"), target_ref=require(args, "target_ref")
    )


def _candidate_accept(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError("authorization_required", "candidate.accept requires an explicit user action")
    return ops().accept_candidate(require(args, "project_id"), candidate_id=require(args, "candidate_id"), candidate_fingerprint=require(args, "candidate_fingerprint"), authorized_by=require(args, "authorized_by"), authorization=require(args, "authorization", dict), idempotency_key=require(args, "idempotency_key"))


def _settle(args: dict[str, Any], _: str):
    return ops().settle(require(args, "project_id"), acceptance_id=require(args, "acceptance_id"), target_ref=require(args, "target_ref"), expected_before_fingerprint=require(args, "expected_before_fingerprint"), user_authorized=args.get("user_authorized") is True, idempotency_key=require(args, "idempotency_key"))


def _feedback(args: dict[str, Any], _: str):
    return ops().observe_feedback(require(args, "project_id"), evidence_kind=require(args, "evidence_kind"), payload=require(args, "payload", dict), source_ref=args.get("source_ref"))


def _pub_preview(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").publication_preview(require(args, "project_id"), require(args, "acceptance_id"))


def _pub_build(args: dict[str, Any], _: str):
    return ops().publication_build(require(args, "project_id"), require(args, "acceptance_id"), args.get("format") or "md")


def _context_projection(args: dict[str, Any], surface: str):
    return ContextRepository(store(read_only=surface == "agent_package")).inspector_projection(require(args, "project_id"), require(args, "run_id"))


def _fixed_list(table: str, order_by: str = "rowid DESC", limit_default: int = 100) -> Callable[[dict[str, Any], str], dict[str, Any]]:
    def handler(args: dict[str, Any], surface: str):
        project_id = require(args, "project_id")
        limit = max(1, min(int(args.get("limit") or limit_default), 500))
        with store(read_only=surface == "agent_package").open_project(project_id) as conn:
            rows = [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY {order_by} LIMIT ?", (limit,))]
        for row in rows:
            for key in list(row):
                normalized = key.lower().replace("-", "_")
                if normalized in _SECRET_REQUEST_KEYS or "credential" in normalized:
                    row.pop(key, None)
        return {"schema": "quillframe_inspector_projection_v1", "kind": table, "project_id": project_id, "items": rows, "authority": False}
    return handler


DISPATCH: dict[str, Callable[[dict[str, Any], str], dict[str, Any]]] = {
    "bridge.describe": _describe,
    "database.doctor": _doctor,
    "project.create": _project_create,
    "project.list": _project_list,
    "project.open": _project_inspect,
    "project.inspect": _project_inspect,
    "project.search": _project_search,
    "project.backup": _project_backup,
    "project.restore": _project_restore,
    "document.create": _document_create,
    "document.list": _document_list,
    "document.open": _document_open,
    "document.revisions.list": _revisions_list,
    "document.revision.save": _revision_save,
    "document.revision.compare": _revision_compare,
    "author.run.start": _author_run,
    "author.run.status": _author_run_status,
    "author.run.resume": _author_run_resume,
    "author.run.cancel": _author_run_cancel,
    "author.run.events": _author_run_events,
    "author.run.execute": _author_run_execute,
    "author.run.independent.submit": _author_independent_submit,
    "author.run.independent.dispatch.prepare": _author_independent_dispatch_prepare,
    "author.run.context.refresh": _author_context_refresh,
    "model.service.add": _model_add,
    "model.service.list": _model_list,
    "model.service.get": _model_get,
    "model.service.discover": _model_discover,
    "model.service.test": _model_test,
    "model.service.token.replace": _model_token_replace,
    "model.service.token.remove": _model_token_remove,
    "model.service.delete": _model_delete,
    "model.capabilities": _model_capabilities,
    "model.route.preview": _model_route_preview,
    "candidate.review.get": _candidate_review_get,
    "candidate.visible.get": _candidate_visible_get,
    "candidate.accept": _candidate_accept,
    "candidate.reject": _candidate_reject,
    "candidate.revision.request": _candidate_revision_request,
    "settlement.preflight": _settlement_preflight,
    "settlement.apply": _settle,
    "feedback.observe": _feedback,
    "publication.preview": _pub_preview,
    "publication.build": _pub_build,
    "inspector.context.runtime": _context_projection,
    "inspector.sessions.list": _fixed_list("sessions", "updated_at DESC"),
    "inspector.runs.list": _fixed_list("runs", "updated_at DESC"),
    "inspector.checkpoints.list": _fixed_list("checkpoints", "created_at DESC"),
    "inspector.context.list": _fixed_list("context_manifests", "created_at DESC"),
    "inspector.receipts.list": _fixed_list("receipts", "created_at DESC"),
    "inspector.candidates.list": _fixed_list("candidates", "created_at DESC"),
    "inspector.learning.list": _fixed_list("learning_evidence", "created_at DESC"),
}


def validate_request(req: dict[str, Any]) -> list[str]:
    c = contract()
    errors: list[str] = []
    if req.get("schema") != REQUEST_SCHEMA:
        errors.append(f"schema must be {REQUEST_SCHEMA}")
    if req.get("bridge_version") != BRIDGE_VERSION:
        errors.append(f"bridge_version must be exactly {BRIDGE_VERSION}")
    if not isinstance(req.get("request_id"), str) or not req["request_id"].strip():
        errors.append("request_id must be non-empty string")
    op = req.get("operation")
    if op not in c["operations"]:
        errors.append("unknown operation")
    if req.get("surface") not in c["surfaces"]:
        errors.append("unsupported surface")
    if not isinstance(req.get("args"), dict):
        errors.append("args must be object")
    if req.get("authority") is not False:
        errors.append("request authority must be false")
    if op in c["operations"] and isinstance(req.get("args"), dict):
        metadata = c["operations"][op]
        if req.get("surface") == "agent_package" and metadata.get("kind") != "query":
            errors.append("agent_package only permits query operations")
        if op == "database.doctor" and req["args"].get("fix") is True:
            errors.append("database.doctor is read-only; fix is not supported")
        missing = [key for key in c["operations"][op].get("required_args", []) if req["args"].get(key) in (None, "")]
        if missing:
            errors.append("missing args: " + ", ".join(missing))
        allowed = c["operations"][op].get("allowed_surfaces")
        if allowed and req.get("surface") not in allowed:
            errors.append("operation is not authorized on this surface")
    return errors


def result(req: dict[str, Any], status: str, *, data: Any = None, error: Any = None) -> dict[str, Any]:
    secrets = _secret_values(req)
    safe_req = _redact(req, secrets)
    safe_data = _redact(data, secrets)
    safe_error = _redact(error, secrets)
    out = {
        "schema": RESULT_SCHEMA,
        "bridge_version": BRIDGE_VERSION,
        "request_id": safe_req.get("request_id"),
        "operation": safe_req.get("operation"),
        "surface": safe_req.get("surface"),
        "status": status,
        "data": safe_data,
        "error": safe_error,
        "request_fingerprint": fp(safe_req),
        "secret_values_persisted": False,
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    out["result_fingerprint"] = fp(out)
    return out


def _public_error(code: Any, fallback: str) -> dict[str, Any]:
    """Return the entire public failure body without exception-derived prose."""
    stable = code if isinstance(code, str) and _PUBLIC_ERROR_CODE_RE.fullmatch(code) else fallback
    return {"code": stable, "mutation_performed": False}


def invoke(req: dict[str, Any]) -> dict[str, Any]:
    errors = validate_request(req)
    if errors:
        return result(req, "invalid", error={"code": "invalid_request", "messages": errors, "mutation_performed": False})
    try:
        return result(req, "ok", data=DISPATCH[req["operation"]](req["args"], req["surface"]))
    except (BridgeError, OperationError, ProductionRunError, WorkflowError, RouteError, ModelRuntimeError, ConflictError, IntegrityError, FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        return result(req, "failed", error=_public_error(getattr(exc, "code", None), "bridge_operation_failed"))
    except Exception:
        return result(req, "failed", error=_public_error(None, "bridge_internal_error"))


def self_test() -> dict[str, Any]:
    base = {"schema": REQUEST_SCHEMA, "bridge_version": BRIDGE_VERSION, "surface": "agent_package", "authority": False}
    desc = invoke({**base, "request_id": "self", "operation": "bridge.describe", "args": {}})
    generic = invoke({**base, "request_id": "bad", "operation": "command.invoke", "args": {}})
    first = invoke({**base, "request_id": "secret-a", "operation": "model.service.add", "args": {"endpoint": "https://example.invalid/v1", "access_token": "A"}})
    second = invoke({**base, "request_id": "secret-a", "operation": "model.service.add", "args": {"endpoint": "https://example.invalid/v1", "access_token": "B"}})
    ok = desc["status"] == "ok" and generic["status"] == "invalid" and desc["authority"] is False and first["request_fingerprint"] == second["request_fingerprint"] and first["secret_values_persisted"] is False
    return {"quillframe_host_bridge_contract": "PASS" if ok else "FAIL", "contract_version": contract()["version"], "generic_mutation_dispatch": False, "secret_value_fingerprint_independent": first["request_fingerprint"] == second["request_fingerprint"], "authority": False}


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
        report = self_test()
        print(json.dumps(report, indent=2))
        return 0 if report["quillframe_host_bridge_contract"] == "PASS" else 1
    raw = Path(args.request).read_text(encoding="utf-8") if args.request else sys.stdin.read()
    req = json.loads(raw)
    out = invoke(req)
    # `invoke` emits only the credential-scrubbed public bridge result. Raw request
    # payloads and credential-bearing exception text are never written to stdout.
    # codeql[py/clear-text-logging-sensitive-data]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
