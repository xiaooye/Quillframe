#!/usr/bin/env python3
"""Typed Quillframe Host Bridge v11.

Transports may be local HTTP, hosted HTTP or Tauri-local IPC, but semantic
operations are shared here. The delivery surface never becomes the authority;
operation-specific Core code performs any authorized state transition.
"""
from __future__ import annotations

import argparse
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
from production_runtime import (
    NovelWorkflowEngine, ProductionCoordinator, ProductionRunError, ProductionRunExecutor, WorkflowError,
)
from production_runtime.semantic import RegisteredSemanticExecutor
from production_runtime.workflow_service import NovelWorkflowService
from studio import host_bridge_protocol as _protocol

CONTRACT_PATH = Path(__file__).with_name("host_bridge_contract.json")
BRIDGE_VERSION = _protocol.BRIDGE_VERSION
REQUEST_SCHEMA = _protocol.REQUEST_SCHEMA
RESULT_SCHEMA = _protocol.RESULT_SCHEMA

_SECRET_REQUEST_KEYS = _protocol._SECRET_REQUEST_KEYS
_SECRET_OPERATIONS = {"model.service.add", "model.service.token.replace"}
_PUBLIC_ERROR_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_CORPUS_LEGACY_PROTOCOL = "quillframe_corpus_three_window_benchmark_v1"
_CORPUS_STYLE_PROTOCOL = "quillframe_corpus_style_learning_v1"
_secret_store: SecretStore = MemorySecretStore()
_agent_runtime_instance: QuillframeAgentRuntime | None = None
_production_coordinator_instance: ProductionCoordinator | None = None


class BridgeError(RuntimeError):
    def __init__(self, code: str, message: str, detail: Any = None):
        super().__init__(message)
        self.code = code
        self.detail = detail


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


def start_production_coordinator(*, interval_seconds: float = 5.0) -> ProductionCoordinator:
    """Start host-owned continuation for existing durable production requests."""
    global _production_coordinator_instance
    if _production_coordinator_instance is None:
        def project_ids() -> list[str]:
            projection = ops(read_only=True).project_list(limit=1000)
            rows = projection.get("items") if isinstance(projection, dict) else []
            return [row["id"] for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)]

        _production_coordinator_instance = ProductionCoordinator(
            lambda: production_runtime(), project_ids, interval_seconds=interval_seconds,
        )
    _production_coordinator_instance.start()
    return _production_coordinator_instance


def stop_production_coordinator() -> None:
    global _production_coordinator_instance
    if _production_coordinator_instance is not None:
        _production_coordinator_instance.stop()
        _production_coordinator_instance = None


def workflow_service(*, read_only: bool = False) -> NovelWorkflowService:
    return NovelWorkflowService(store(read_only=read_only))


def require(args: dict[str, Any], key: str, typ: type | tuple[type, ...] = str):
    value = args.get(key)
    if not isinstance(value, typ) or (typ is int and isinstance(value, bool)) or (isinstance(value, str) and not value.strip()):
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
    return ops().project_create(require(args, "project_id"), require(args, "title"), args.get("language") or "zh-CN")


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
    return ops(read_only=surface == "agent_package").document_open(require(args, "project_id"), require(args, "document_id"))


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
    return ops(read_only=surface == "agent_package").revision_compare(require(args, "project_id"), require(args, "left_revision_id"), require(args, "right_revision_id"))


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
    event = workflow_service().resume(
        project_id=require(args, "project_id"),
        run_id=require(args, "run_id"),
        cursor=require(args, "cursor", int),
        idempotency_key=require(args, "idempotency_key"),
    )
    execution = production_runtime().resume_execution(require(args, "project_id"), require(args, "run_id"))
    return {**event, "execution": execution}


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
    independent_provenance = args.get("independent_provenance")
    if independent_provenance is not None and not isinstance(independent_provenance, dict):
        raise BridgeError("invalid_args", "independent_provenance must be an object when provided")
    inherit = args.get("inherit_repair_request", False)
    if not isinstance(inherit, bool):
        raise BridgeError("invalid_args", "inherit_repair_request must be boolean")
    if args.get("repair_preservation") is not None:
        raise BridgeError("repair_preservation_core_owned", "repair comparison evidence must be generated by Core")
    return production_runtime().execute(
        require(args, "project_id"),
        require(args, "run_id"),
        service_id=require(args, "service_id"),
        instruction=args.get("instruction") if inherit else require(args, "instruction"),
        document_id=args.get("document_id"),
        model_preference=args.get("model_id"),
        stage_budgets=args.get("stage_budgets") if isinstance(args.get("stage_budgets"), dict) else None,
        reader_grip=args.get("reader_grip") if inherit else require(args, "reader_grip"),
        rule_material=args.get("rule_material") if inherit else require(args, "rule_material", list),
        reader_visible_context=args.get("reader_visible_context") if isinstance(args.get("reader_visible_context"), list) else None,
        independent_provenance=independent_provenance,
        inherit_repair_request=inherit,
        craft_guidance_mode=args.get("craft_guidance_mode"),
        max_model_calls=args.get("max_model_calls", 64),
        run_cost_budget=args.get("run_cost_budget", 10_000_000),
    )


def _author_run_billing_reconcile(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError(
            "authorization_required",
            "billing reconciliation requires an explicit user action",
        )
    return production_runtime().reconcile_billing(
        require(args, "project_id"),
        require(args, "run_id"),
        call_id=require(args, "call_id"),
        expected_result_fingerprint=require(args, "expected_result_fingerprint"),
        cost_micros=require(args, "cost_micros", int),
        evidence_ref=require(args, "evidence_ref"),
        evidence_fingerprint=require(args, "evidence_fingerprint"),
    )


def _author_run_build_migration_preview(args: dict[str, Any], _: str):
    return production_runtime().framework_build_migration_preview(
        require(args, "project_id"), require(args, "run_id")
    )


def _author_run_build_migration_regression(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError(
            "authorization_required",
            "offline Framework regression requires an explicit user action",
        )
    return production_runtime().run_framework_build_migration_regression(
        require(args, "project_id"), require(args, "run_id")
    )


def _author_run_build_migrate(args: dict[str, Any], _: str):
    if args.get("user_authorized") is not True:
        raise BridgeError(
            "authorization_required",
            "Framework build migration requires an explicit user action",
        )
    return production_runtime().migrate_framework_build(
        require(args, "project_id"),
        require(args, "run_id"),
        expected_request_fingerprint=require(args, "expected_request_fingerprint"),
        regression_receipt_id=require(args, "regression_receipt_id", str),
        authorization_ref=require(args, "authorization_ref"),
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
    access_token = args.get("access_token", "")
    if not isinstance(access_token, str):
        raise BridgeError("invalid_args", "access_token must be a string when provided")
    return model_services().connect(require(args, "endpoint"), access_token)


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


def _model_fiction_confirm(args: dict[str, Any], _: str):
    return model_services().confirm_fiction_writing(require(args, "confirmation", dict))


def _model_fiction_revoke(args: dict[str, Any], _: str):
    return model_services().revoke_fiction_writing(require(args, "service_id"), require(args, "model_id"))


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
    return ops().settle(require(args, "project_id"), acceptance_id=require(args, "acceptance_id"), target_ref=require(args, "target_ref"), expected_before_fingerprint=require(args, "expected_before_fingerprint"), user_authorized=args.get("user_authorized") is True, idempotency_key=require(args, "idempotency_key"), expected_preflight_fingerprint=args.get("expected_preflight_fingerprint"))


def _feedback(args: dict[str, Any], _: str):
    return ops().observe_feedback(require(args, "project_id"), evidence_kind=require(args, "evidence_kind"), payload=require(args, "payload", dict), source_ref=args.get("source_ref"))


def _pub_preview(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").publication_preview(require(args, "project_id"), require(args, "acceptance_id"))


def _pub_build(args: dict[str, Any], _: str):
    return ops().publication_build(require(args, "project_id"), require(args, "acceptance_id"), args.get("format") or "md")


def _pub_artifact(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").publication_artifact_get(require(args, "project_id"), build_id=require(args, "build_id"))


def _pub_collection(args: dict[str, Any], _: str):
    return ops().publication_collection_build(require(args, "project_id"), acceptance_ids=require(args, "acceptance_ids", list),
        fmt=args.get("format") or "md", idempotency_key=require(args, "idempotency_key"), user_authorized=args.get("user_authorized") is True)


def _chapter_list(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").chapter_list(require(args, "project_id"))


def _chapter_create(args: dict[str, Any], _: str):
    return ops().chapter_create(require(args, "project_id"), title=require(args, "title"), parent_id=args.get("parent_id"),
        idempotency_key=require(args, "idempotency_key"), user_authorized=args.get("user_authorized") is True)


def _plan_inspect(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").plan_inspect(require(args, "project_id"), target_ref=args.get("target_ref"))


def _plan_save(args: dict[str, Any], _: str):
    return ops().plan_save(require(args, "project_id"), target_ref=require(args, "target_ref"), title=require(args, "title"),
        content=require(args, "content"), expected_version=require(args, "expected_version", int),
        idempotency_key=require(args, "idempotency_key"), user_authorized=args.get("user_authorized") is True,
        reader_intent=args.get("reader_intent"), expectation_refs=args.get("expectation_refs"))


def _story_inspect(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").story_inspect(require(args, "project_id"))


def _reader_inspect(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").reader_expectations_inspect(require(args, "project_id"), current_order=args.get("current_order"))


def _reader_apply(args: dict[str, Any], _: str):
    return ops().reader_expectations_apply(require(args, "project_id"), observation_id=require(args, "observation_id"),
        acceptance_id=require(args, "acceptance_id"), authorized_by=require(args, "authorized_by"),
        idempotency_key=require(args, "idempotency_key"), user_authorized=args.get("user_authorized") is True)


def _learning_feedback_observe(args: dict[str, Any], _: str):
    return ops().learning().observe(require(args, "project_id"), event_id=require(args, "event_id"),
        feedback_text=require(args, "feedback_text"), evidence_kind=require(args, "evidence_kind"),
        candidate_id=require(args, "candidate_id"), candidate_fingerprint=require(args, "candidate_fingerprint"),
        document_id=require(args, "document_id"), run_id=require(args, "run_id"),
        source_type=args.get("source_type") or "author", source_id=args.get("source_id") or "author")


def _learning_feedback_get(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").learning().get_feedback(require(args, "project_id"), event_id=require(args, "event_id"))


def _learning_feedback_list(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").learning().list_feedback(require(args, "project_id"), limit=args.get("limit") or 50)


def _learning_feedback_execute(args: dict[str, Any], _: str):
    return ops().learning().execute(require(args, "project_id"), event_id=require(args, "event_id"),
        service_id=require(args, "service_id"), model_id=args.get("model_id"), runtime=agent_runtime())


def _learning_preference_list(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").learning().list_preferences(require(args, "project_id"), limit=args.get("limit") or 100)


def _learning_preference_get(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").learning().get_preference(require(args, "project_id"), hypothesis_id=require(args, "hypothesis_id"))


def _learning_preference_review(args: dict[str, Any], _: str):
    return ops().learning().review(require(args, "project_id"), hypothesis_id=require(args, "hypothesis_id"),
        expected_version=require(args, "expected_version", int), service_id=require(args, "service_id"),
        model_id=args.get("model_id"), runtime=agent_runtime())


def _learning_preference_activate(args: dict[str, Any], _: str):
    return ops().learning().activate(require(args, "project_id"), hypothesis_id=require(args, "hypothesis_id"),
        expected_version=require(args, "expected_version", int), authorized_by=require(args, "authorized_by"),
        idempotency_key=require(args, "idempotency_key"), user_authorized=args.get("user_authorized") is True)


def _learning_preference_deactivate(args: dict[str, Any], _: str):
    return ops().learning().deactivate(require(args, "project_id"), hypothesis_id=require(args, "hypothesis_id"),
        expected_version=require(args, "expected_version", int), authorized_by=require(args, "authorized_by"),
        idempotency_key=require(args, "idempotency_key"), user_authorized=args.get("user_authorized") is True)


_CORPUS_HOST_STORAGE_ARGS = {"db_path", "public_root"}
_CORPUS_PROFILES = {"general", "adult_explicit"}
_CORPUS_SEMANTIC_JOB_BUDGET_DEFAULT = 8
_CORPUS_SEMANTIC_JOB_BUDGET_MAX = 64
_PRIVATE_SELECTION_ITEM_FIELDS = {
    "display_label", "title", "display_name", "filename", "creator", "author",
    "relative_locator", "path", "source_path", "local_path",
}
_CORPUS_QUARANTINE_COUNT_KEYS = {
    "identity_unknown", "below_minimum_chars", "ambiguous_profile",
}
_FINGERPRINT_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_STYLE_PREVIEW_TOKEN_RE = re.compile(r"style-preview-[0-9a-f]{64}\Z")
_LOCAL_PATH_VALUE_RE = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|tmp|var|private|etc)(?:/|$))", re.IGNORECASE)


def _contains_path_argument(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized == "path" or normalized.endswith("_path") or "local_path" in normalized:
                return True
            if _contains_path_argument(child):
                return True
    elif isinstance(value, list):
        return any(_contains_path_argument(child) for child in value)
    elif isinstance(value, str):
        return bool(_LOCAL_PATH_VALUE_RE.match(value))
    return False


def _corpus_args(args: dict[str, Any], surface: str) -> dict[str, Any]:
    """Forward typed Corpus kwargs while keeping host storage roots host-owned."""
    if _CORPUS_HOST_STORAGE_ARGS.intersection(args):
        raise BridgeError("invalid_args", "Corpus storage roots are host-owned")
    if surface == "hosted_web" and _contains_path_argument(args):
        raise BridgeError("local_path_forbidden", "hosted_web cannot access local filesystem paths")
    return dict(args)


def _corpus_scan_collection(args: dict[str, Any], surface: str):
    # The contract already excludes hosted_web. Keep the runtime check so a
    # future contract edit cannot accidentally widen access to a local path.
    if surface not in {"cli", "local_app"}:
        raise BridgeError("local_path_forbidden", "local Corpus scanning requires a local host")
    forwarded = _corpus_args(args, surface)
    collection_path = require(forwarded, "collection_path")
    forwarded.pop("collection_path", None)
    rights = forwarded.pop("rights", None)
    if rights is not None:
        if not isinstance(rights, dict):
            raise BridgeError("invalid_args", "rights must be an object")
        unknown = set(rights) - {"rights_class", "rights_basis"}
        if unknown:
            raise BridgeError("invalid_args", "rights contains unsupported fields")
        forwarded.update(rights)
    return ops().corpus_scan_collection(collection_path, **forwarded)


def _corpus_propose_selection(args: dict[str, Any], surface: str):
    profile = require(args, "profile")
    if profile not in _CORPUS_PROFILES:
        raise BridgeError("invalid_args", "profile must be general or adult_explicit")
    collection_id = args.get("collection_id")
    study_id = args.get("study_id")
    collection_supplied = isinstance(collection_id, str) and bool(collection_id.strip())
    study_supplied = isinstance(study_id, str) and bool(study_id.strip())
    if ("collection_id" in args and not collection_supplied) or ("study_id" in args and not study_supplied):
        raise BridgeError("invalid_args", "selection identity must be a non-empty string")
    if collection_supplied == study_supplied:
        raise BridgeError("invalid_args", "provide exactly one of collection_id or study_id")
    forwarded = _corpus_args(args, surface)
    limit = forwarded.get("limit", 120)
    if type(limit) is not int or limit != 120:
        raise BridgeError("invalid_args", "limit must be exactly 120")
    # CorpusLibrary owns the exact 120-work invariant; ``limit`` is a Bridge
    # assertion, not a second selection algorithm or an implementation kwarg.
    forwarded.pop("limit", None)
    core = ops()
    if study_supplied:
        # ``study_id`` is the local-only "load existing proposal" path.  Core's
        # lower-level proposal API also permits callers to choose an ID for a
        # new proposal, so prove existence here before replaying it.  Otherwise
        # a Studio launched against the wrong host-owned Corpus root could
        # silently turn a lookup into a new/insufficient proposal.
        existing = core.corpus_study_status(study_id)
        if not isinstance(existing, dict) or existing.get("study_id") != study_id:
            raise BridgeError(
                "corpus_projection_invalid",
                "Core returned a mismatched existing study identity",
            )
        if existing.get("profile") != profile:
            raise BridgeError(
                "selection_profile_mismatch",
                "profile must match the existing study",
            )
    projection = core.corpus_propose_selection(**forwarded)
    if isinstance(projection, dict):
        projection = dict(projection)
        projection = _project_corpus_eligibility_counts(projection)
        projection = _strip_private_selection_fields(projection)
    if isinstance(projection, dict) and projection.get("study_id"):
        if collection_supplied:
            projection.setdefault("collection_id", collection_id)
        if study_supplied and projection.get("study_id") != study_id:
            raise BridgeError("corpus_projection_invalid", "Core returned a mismatched study identity")
        projection.setdefault("proposal_fingerprint", projection.get("proposal_hash"))
        if projection.get("profile") != profile:
            raise BridgeError("corpus_projection_invalid", "Core returned a mismatched study profile")
        if surface in {"cli", "local_app"}:
            projection = _merge_private_selection_preview(core, projection)
    return projection


def _corpus_refresh_selection(args: dict[str, Any], surface: str):
    study_id = require(args, "study_id")
    profile = require(args, "profile")
    if profile not in _CORPUS_PROFILES:
        raise BridgeError("invalid_args", "profile must be general or adult_explicit")
    expected = require(args, "expected_proposal_hash")
    if not isinstance(expected, str) or not _FINGERPRINT_RE.fullmatch(expected):
        raise BridgeError("invalid_args", "expected_proposal_hash must be a sha256 fingerprint")
    forwarded = _corpus_args(args, surface)
    core = ops()
    projection = core.corpus_refresh_selection(**forwarded)
    if not isinstance(projection, dict):
        raise BridgeError("corpus_projection_invalid", "Core returned an invalid refreshed proposal")
    projection = _project_corpus_eligibility_counts(dict(projection))
    projection = _strip_private_selection_fields(projection)
    if projection.get("study_id") != study_id or projection.get("profile") != profile:
        raise BridgeError("corpus_projection_invalid", "Core returned a mismatched refreshed proposal")
    projection.setdefault("proposal_fingerprint", projection.get("proposal_hash"))
    if projection.get("status") == "proposed" and surface in {"cli", "local_app"}:
        projection = _merge_private_selection_preview(core, projection)
    return projection


def _project_corpus_eligibility_counts(projection: dict[str, Any]) -> dict[str, Any]:
    """Collapse private eligibility reasons into the two permitted aggregates."""
    detailed = projection.get("exclusion_counts")
    existing = projection.get("eligibility_counts")
    aggregate: dict[str, int] | None = None
    if detailed is not None:
        if (not isinstance(detailed, dict) or any(
            not isinstance(key, str) or type(value) is not int or value < 0
            for key, value in detailed.items()
        )):
            raise BridgeError("corpus_projection_invalid", "Core returned invalid eligibility counts")
        quarantined = sum(
            value for key, value in detailed.items() if key in _CORPUS_QUARANTINE_COUNT_KEYS
        )
        aggregate = {
            "excluded": sum(detailed.values()) - quarantined,
            "quarantined": quarantined,
        }
    if existing is not None:
        if (not isinstance(existing, dict) or set(existing) - {"excluded", "quarantined"}
                or any(type(value) is not int or value < 0 for value in existing.values())):
            raise BridgeError("corpus_projection_invalid", "Core returned invalid eligibility aggregates")
        normalized = {
            key: existing[key] for key in ("excluded", "quarantined") if key in existing
        }
        if aggregate is not None and normalized != aggregate:
            raise BridgeError("corpus_projection_invalid", "Core returned conflicting eligibility aggregates")
        aggregate = normalized
    result = dict(projection)
    result.pop("exclusion_counts", None)
    if aggregate is not None:
        result["eligibility_counts"] = aggregate
    return result


def _strip_private_selection_fields(projection: dict[str, Any]) -> dict[str, Any]:
    """Keep the ordinary proposal anonymous on every transport."""
    result = {
        key: value for key, value in projection.items()
        if key not in {"private_local_only", "private_preview", "display_label", "creator", "relative_locator",
                       "collection_path", "source_path", "local_path", "exclusion_counts"}
    }
    works = projection.get("works")
    if isinstance(works, list):
        result["works"] = [
            {key: value for key, value in row.items() if key not in _PRIVATE_SELECTION_ITEM_FIELDS}
            if isinstance(row, dict) else row
            for row in works
        ]
    return result


def _merge_private_selection_preview(core: Any, projection: dict[str, Any]) -> dict[str, Any]:
    """Merge a strict local-only label projection without returning its locator."""
    handler = getattr(core, "corpus_selection_private_preview", None)
    if not callable(handler):
        library_factory = getattr(core, "corpus_library", None)
        library = library_factory() if callable(library_factory) else None
        handler = getattr(library, "selection_private_preview", None)
    if not callable(handler):
        raise BridgeError("corpus_private_preview_unavailable", "local checklist labels are unavailable")
    preview = handler(projection["study_id"])
    if (not isinstance(preview, dict)
            or preview.get("schema") != "quillframe_corpus_selection_private_preview_v1"
            or preview.get("private_local_only") is not True
            or preview.get("redistributable") is not False
            or preview.get("raw_text_included") is not False
            or preview.get("study_id") != projection.get("study_id")
            or preview.get("profile") != projection.get("profile")
            or preview.get("proposal_hash") != projection.get("proposal_hash")):
        raise BridgeError("corpus_private_preview_invalid", "local checklist labels are not safely bound")
    public_works = projection.get("works")
    private_works = preview.get("works")
    if not isinstance(public_works, list) or not isinstance(private_works, list) or len(public_works) != 120 or len(private_works) != 120:
        raise BridgeError("corpus_private_preview_invalid", "local checklist labels must bind exactly 120 works")
    merged: list[dict[str, Any]] = []
    for public, private in zip(public_works, private_works):
        if not isinstance(public, dict) or not isinstance(private, dict):
            raise BridgeError("corpus_private_preview_invalid", "local checklist item is invalid")
        if private.get("public_work_id") != public.get("public_work_id"):
            raise BridgeError("corpus_private_preview_invalid", "local checklist order changed")
        label = private.get("display_label")
        creator = private.get("creator")
        if not isinstance(label, str) or not label.strip():
            raise BridgeError("corpus_private_preview_invalid", "local checklist label is missing")
        if creator is not None and (not isinstance(creator, str) or not creator.strip()):
            raise BridgeError("corpus_private_preview_invalid", "local checklist creator is invalid")
        item = dict(public)
        item["display_label"] = label
        if creator is not None:
            item["creator"] = creator
        merged.append(item)
    return {**projection, "works": merged, "private_local_only": True}


def _corpus_confirm_selection(args: dict[str, Any], surface: str):
    require(args, "study_id")
    profile = require(args, "profile")
    if profile not in _CORPUS_PROFILES:
        raise BridgeError("invalid_args", "profile must be general or adult_explicit")
    work_ids = require(args, "work_ids", list)
    if len(work_ids) != 120 or any(not isinstance(value, str) or not value.strip() for value in work_ids):
        raise BridgeError("invalid_args", "work_ids must contain exactly 120 non-empty identifiers")
    if len(set(work_ids)) != len(work_ids):
        raise BridgeError("invalid_args", "work_ids must be unique")
    proposal_fingerprint = require(args, "proposal_fingerprint")
    if not _FINGERPRINT_RE.fullmatch(proposal_fingerprint):
        raise BridgeError("invalid_args", "proposal_fingerprint must be a sha256 fingerprint")
    forwarded = _corpus_args(args, surface)
    study_id = forwarded.pop("study_id")
    forwarded.pop("work_ids")
    forwarded.pop("proposal_fingerprint")
    forwarded.pop("profile")
    core = ops()
    status = core.corpus_study_status(study_id)
    projected_ids = [
        row.get("public_work_id") for row in status.get("works", []) if isinstance(row, dict)
    ] if isinstance(status, dict) else []
    if projected_ids != work_ids:
        raise BridgeError("selection_membership_mismatch", "work_ids must match the exact 120-work proposal in order")
    if not isinstance(status, dict) or status.get("profile") != profile:
        raise BridgeError("selection_profile_mismatch", "profile must match the proposed study")
    return core.corpus_confirm_selection(
        study_id, expected_hash=proposal_fingerprint, **forwarded
    )


def _corpus_study(operation: str, args: dict[str, Any], surface: str):
    require(args, "study_id")
    forwarded = _corpus_args(args, surface)
    service_id = forwarded.pop("service_id", None)
    model_id = forwarded.pop("model_id", None)
    heldout_model_id = forwarded.pop("heldout_model_id", None)
    legacy_independent_model_id = forwarded.pop("independent_model_id", None)
    semantic_job_budget = forwarded.pop("max_jobs", None)
    if legacy_independent_model_id is not None:
        raise BridgeError(
            "invalid_args",
            "independent_model_id is not a Corpus style-learning gate; use heldout_model_id "
            "for same-run held-out semantic verification",
        )
    execute_semantic = forwarded.pop("execute_semantic", service_id is not None)
    if not isinstance(execute_semantic, bool):
        raise BridgeError("invalid_args", "execute_semantic must be a boolean")
    if operation not in {"start", "resume"} and (
        execute_semantic or service_id is not None or model_id is not None
        or heldout_model_id is not None or semantic_job_budget is not None
    ):
        raise BridgeError("invalid_args", "semantic execution is valid only for study start/resume")
    if semantic_job_budget is not None and (
        type(semantic_job_budget) is not int
        or not 1 <= semantic_job_budget <= _CORPUS_SEMANTIC_JOB_BUDGET_MAX
    ):
        raise BridgeError(
            "invalid_args",
            f"max_jobs must be an integer between 1 and {_CORPUS_SEMANTIC_JOB_BUDGET_MAX}",
        )
    if execute_semantic:
        if not isinstance(service_id, str) or not service_id.strip():
            raise BridgeError("invalid_args", "service_id is required for semantic execution")
        if model_id is not None and (not isinstance(model_id, str) or not model_id.strip()):
            raise BridgeError("invalid_args", "model_id must be a non-empty string")
        if heldout_model_id is not None and (
            not isinstance(heldout_model_id, str) or not heldout_model_id.strip()
        ):
            raise BridgeError("invalid_args", "heldout_model_id must be a non-empty string")
        if (
            heldout_model_id is not None
            and forwarded.get("analysis_protocol_id") != _CORPUS_STYLE_PROTOCOL
        ):
            raise BridgeError(
                "invalid_args",
                "heldout_model_id is valid only for the style-learning protocol",
            )
        executor = RegisteredSemanticExecutor(agent_runtime())

        def run_semantic(job: dict[str, Any]) -> dict[str, Any]:
            if not isinstance(job, dict):
                raise BridgeError("corpus_semantic_job_invalid", "Core supplied an invalid semantic job")
            contract_id = job.get("input", {}).get("model_contract_id") if isinstance(job.get("input"), dict) else None
            execution = job.get("execution") if isinstance(job.get("execution"), dict) else {}
            source_session = execution.get("source_session_id")
            if not isinstance(source_session, str) or not source_session:
                source_session = "SES-CORPUS"
            heldout_verification = contract_id == "learning.style_claim_verify"
            run = {
                "run_id": str(execution.get("handoff_id") or job.get("job_id") or "corpus-style"),
                "session_id": source_session + (
                    ":heldout-verifier" if heldout_verification else ":analysis"
                ),
                "task_mode": "RESEARCH",
                "created_at": job.get("created_at"),
            }
            binding = executor.execute_prepared(
                semantic_job=job,
                run=run,
                service_id=service_id,
                model_preference=(
                    heldout_model_id
                    if heldout_verification and heldout_model_id
                    else model_id
                ),
                runtime_role=(
                    "corpus_style_heldout_verifier"
                    if heldout_verification else "corpus_style_analyst"
                ),
                max_output_tokens=6400,
            )
            result = binding.get("result") if isinstance(binding, dict) else None
            if not isinstance(result, dict):
                raise BridgeError("corpus_semantic_result_invalid", "semantic execution returned no bound result")
            return result

        forwarded["run_semantic"] = run_semantic
        # This budget counts semantic model jobs, not deterministic runner
        # transitions.  The runner continues through any number of mechanical
        # transitions and stops only at this budget or its own terminal/failure
        # boundary, so a default Studio call is a bounded AI research cycle
        # rather than one Python state-machine tick.
        forwarded["max_jobs"] = (
            semantic_job_budget
            if semantic_job_budget is not None
            else _CORPUS_SEMANTIC_JOB_BUDGET_DEFAULT
        )
        if forwarded.get("analysis_protocol_id") == _CORPUS_STYLE_PROTOCOL:
            semantic_config = {
                "executor": "studio_model_service",
                "service_id": service_id,
                "model_preference": model_id or "service_default",
                "heldout_model_preference": heldout_model_id or model_id or "service_default",
                "claim_verification_role": "heldout_semantic_verifier",
            }
            supplied_semantic_config = forwarded.pop("semantic_config", None)
            if (
                supplied_semantic_config is not None
                and supplied_semantic_config != semantic_config
            ):
                raise BridgeError(
                    "invalid_args",
                    "semantic_config is Host-derived from the selected analyst and "
                    "held-out verifier models",
                )
            forwarded["semantic_config"] = semantic_config
    elif (
        service_id is not None or model_id is not None or heldout_model_id is not None
        or semantic_job_budget is not None
    ):
        raise BridgeError("invalid_args", "model service options require execute_semantic:true")
    handler = getattr(ops(read_only=surface == "agent_package"), f"corpus_{operation}_study")
    return handler(**forwarded)


def _corpus_study_start(args: dict[str, Any], surface: str):
    return _corpus_study("start", args, surface)


def _corpus_study_status(args: dict[str, Any], surface: str):
    require(args, "study_id")
    return ops(read_only=surface == "agent_package").corpus_study_status(**_corpus_args(args, surface))


def _corpus_study_resume(args: dict[str, Any], surface: str):
    return _corpus_study("resume", args, surface)


def _corpus_study_cancel(args: dict[str, Any], surface: str):
    return _corpus_study("cancel", args, surface)


def _corpus_public_preview(args: dict[str, Any], surface: str):
    forwarded = _corpus_args(args, surface)
    study_id = require(forwarded, "study_id")
    forwarded.pop("study_id")
    protocol = forwarded.get("analysis_protocol_id", _CORPUS_LEGACY_PROTOCOL)
    corpus_version = forwarded.pop("corpus_version", None)
    if corpus_version is not None and protocol == _CORPUS_LEGACY_PROTOCOL:
        forwarded["release_id"] = corpus_version
    manifest = ops(read_only=surface == "agent_package").corpus_preview_public(study_id, **forwarded)
    if not isinstance(manifest, dict):
        raise BridgeError("corpus_projection_invalid", "Core returned an invalid public preview")
    if protocol == _CORPUS_STYLE_PROTOCOL:
        atlas = manifest.get("atlas") if isinstance(manifest.get("atlas"), dict) else manifest
        preview_fingerprint = manifest.get("preview_fingerprint") or manifest.get("atlas_fingerprint")
        atlas_fingerprint = atlas.get("atlas_fingerprint") if isinstance(atlas, dict) else None
        preview_token = manifest.get("preview_token")
        release_gates = manifest.get("release_gates")
        if (
            not isinstance(atlas, dict)
            or not isinstance(preview_fingerprint, str)
            or not _FINGERPRINT_RE.fullmatch(preview_fingerprint)
            or not isinstance(atlas_fingerprint, str)
            or not _FINGERPRINT_RE.fullmatch(atlas_fingerprint)
            or not isinstance(preview_token, str)
            or not _STYLE_PREVIEW_TOKEN_RE.fullmatch(preview_token)
            or not isinstance(release_gates, dict)
        ):
            raise BridgeError("corpus_projection_invalid", "Core returned an invalid Style Atlas preview")
        return {
            "schema": "quillframe_corpus_style_atlas_preview_v1",
            "analysis_protocol_id": _CORPUS_STYLE_PROTOCOL,
            "study_id": study_id,
            "corpus_version": atlas_fingerprint,
            "preview_fingerprint": preview_fingerprint,
            "preview_token": preview_token,
            "release_gates": release_gates,
            "bundle": atlas,
            "release_performed": False,
            "authority": False,
        }
    return {
        "schema": "quillframe_corpus_public_preview_v1",
        "study_id": study_id,
        "corpus_version": manifest.get("public_study_id"),
        "preview_fingerprint": manifest.get("manifest_fingerprint"),
        "bundle": manifest,
        "authority": False,
    }


def _corpus_public_validate(args: dict[str, Any], surface: str):
    has_bundle = "bundle" in args
    has_fingerprint = "preview_fingerprint" in args
    if has_bundle == has_fingerprint:
        raise BridgeError("invalid_args", "provide exactly one of bundle or preview_fingerprint")
    if has_bundle and not isinstance(args.get("bundle"), dict):
        raise BridgeError("invalid_args", "bundle must be an object")
    if has_fingerprint and (
        not isinstance(args.get("preview_fingerprint"), str)
        or not _FINGERPRINT_RE.fullmatch(args["preview_fingerprint"])
    ):
        raise BridgeError("invalid_args", "preview_fingerprint must be a sha256 fingerprint")
    forwarded = _corpus_args(args, surface)
    if has_bundle:
        protocol = forwarded.pop("analysis_protocol_id", _CORPUS_LEGACY_PROTOCOL)
        return ops(read_only=surface == "agent_package").corpus_validate_public(
            forwarded["bundle"], analysis_protocol_id=protocol
        )
    return {
        "schema": "quillframe_corpus_operation_v1",
        "operation": "public.validate",
        "preview_fingerprint": forwarded["preview_fingerprint"],
        "status": "unsupported",
        "performed": False,
        "authority": False,
    }


def _corpus_public_release(args: dict[str, Any], surface: str):
    protocol = args.get("analysis_protocol_id", _CORPUS_LEGACY_PROTOCOL)
    if protocol == _CORPUS_STYLE_PROTOCOL:
        # Style release is deliberately unavailable through the generic UI
        # until host-trusted completion/gate/manual receipt resolvers are
        # installed.  Never rebuild a preview or infer PASS here.
        forwarded = _corpus_args(args, surface)
        return ops().corpus_release_public(
            analysis_protocol_id=_CORPUS_STYLE_PROTOCOL,
            **{key: value for key, value in forwarded.items() if key != "analysis_protocol_id"},
        )
    study_id = require(args, "study_id")
    corpus_version = require(args, "corpus_version")
    expected = require(args, "expected_preview_fingerprint")
    if not _FINGERPRINT_RE.fullmatch(expected):
        raise BridgeError("invalid_args", "expected_preview_fingerprint must be a sha256 fingerprint")
    forwarded = _corpus_args(args, surface)
    forwarded.pop("study_id")
    forwarded.pop("corpus_version")
    forwarded.pop("expected_preview_fingerprint")
    core = ops()
    manifest = core.corpus_preview_public(study_id)
    if not isinstance(manifest, dict) or manifest.get("manifest_fingerprint") != expected:
        raise BridgeError("preview_fingerprint_mismatch", "public preview changed before release")
    return core.corpus_release_public(
        study_id,
        release_id=corpus_version,
        preview_token=require(manifest, "preview_token"),
        manifest_fingerprint=expected,
        **forwarded,
    )


def _corpus_public_list(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").corpus_list_public(**_corpus_args(args, surface))


def _corpus_public_get(args: dict[str, Any], surface: str):
    forwarded = _corpus_args(args, surface)
    corpus_version = require(forwarded, "corpus_version")
    forwarded.pop("corpus_version")
    return ops(read_only=surface == "agent_package").corpus_get_public(corpus_version, **forwarded)


def _user_taste_policy_get(_: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").user_taste_get_policy()


def _user_taste_policy_set(args: dict[str, Any], _: str):
    return ops().user_taste_set_policy(require(args, "payload", dict))


def _user_taste_list(args: dict[str, Any], surface: str):
    state = args.get("state")
    if state is not None and (not isinstance(state, str) or not state.strip()):
        raise BridgeError("invalid_args", "state must be non-empty text")
    return ops(read_only=surface == "agent_package").user_taste_list_preferences(state=state)


def _user_taste_get(args: dict[str, Any], surface: str):
    return ops(read_only=surface == "agent_package").user_taste_get_preference(require(args, "hypothesis_id"))


def _user_taste_transition(action: str, args: dict[str, Any]):
    hypothesis_id = require(args, "hypothesis_id")
    expected_version = require(args, "expected_version", int)
    reason = require(args, "reason")
    handler = getattr(ops(), f"user_taste_{action}_preference", None)
    if handler is None:
        return {
            "schema": "quillframe_user_taste_operation_v1",
            "operation": action,
            "hypothesis_id": hypothesis_id,
            "status": "unsupported",
            "performed": False,
            "authority": False,
        }
    return handler(hypothesis_id, expected_version=expected_version, reason=reason)


def _user_taste_pause(args: dict[str, Any], _: str):
    return _user_taste_transition("pause", args)


def _user_taste_withdraw(args: dict[str, Any], _: str):
    return _user_taste_transition("withdraw", args)


def _context_projection(args: dict[str, Any], surface: str):
    return ContextRepository(store(read_only=surface == "agent_package")).inspector_projection(require(args, "project_id"), require(args, "run_id"))


def _fixed_list(table: str, order_by: str = "rowid DESC", limit_default: int = 100) -> Callable[[dict[str, Any], str], dict[str, Any]]:
    def handler(args: dict[str, Any], surface: str):
        project_id = require(args, "project_id")
        limit = max(1, min(int(args.get("limit") or limit_default), 500))
        with store(read_only=surface == "agent_package").open_project(project_id) as conn:
            rows = [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY {order_by} LIMIT ?", (limit,))]
        for row in rows:
            if table == "checkpoints" and str(row.get("checkpoint_kind", "")).startswith("production_"):
                # Raw manuscript and worker packets are never an inspector download.
                row.pop("state_json", None)
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
    "chapter.list": _chapter_list,
    "chapter.create": _chapter_create,
    "plan.inspect": _plan_inspect,
    "plan.save": _plan_save,
    "story.inspect": _story_inspect,
    "reader.expectations.inspect": _reader_inspect,
    "reader.expectations.apply": _reader_apply,
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
    "author.run.billing.reconcile": _author_run_billing_reconcile,
    "author.run.build-migration.preview": _author_run_build_migration_preview,
    "author.run.build-migration.regression": _author_run_build_migration_regression,
    "author.run.build-migration.apply": _author_run_build_migrate,
    "author.run.independent.submit": _author_independent_submit,
    "author.run.independent.dispatch.prepare": _author_independent_dispatch_prepare,
    "author.run.context.refresh": _author_context_refresh,
    "model.service.add": _model_add,
    "model.service.list": _model_list,
    "model.service.get": _model_get,
    "model.service.discover": _model_discover,
    "model.service.test": _model_test,
    "model.service.fiction.confirm": _model_fiction_confirm,
    "model.service.fiction.revoke": _model_fiction_revoke,
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
    "publication.artifact.get": _pub_artifact,
    "publication.collection.build": _pub_collection,
    "learning.feedback.observe": _learning_feedback_observe,
    "learning.feedback.get": _learning_feedback_get,
    "learning.feedback.list": _learning_feedback_list,
    "learning.feedback.execute": _learning_feedback_execute,
    "learning.feedback.resume": _learning_feedback_execute,
    "learning.preference.list": _learning_preference_list,
    "learning.preference.get": _learning_preference_get,
    "learning.preference.review": _learning_preference_review,
    "learning.preference.activate": _learning_preference_activate,
    "learning.preference.deactivate": _learning_preference_deactivate,
    "corpus.collection.scan": _corpus_scan_collection,
    "corpus.selection.propose": _corpus_propose_selection,
    "corpus.selection.refresh": _corpus_refresh_selection,
    "corpus.selection.confirm": _corpus_confirm_selection,
    "corpus.study.start": _corpus_study_start,
    "corpus.study.status": _corpus_study_status,
    "corpus.study.resume": _corpus_study_resume,
    "corpus.study.cancel": _corpus_study_cancel,
    "corpus.public.preview": _corpus_public_preview,
    "corpus.public.validate": _corpus_public_validate,
    "corpus.public.release": _corpus_public_release,
    "corpus.public.list": _corpus_public_list,
    "corpus.public.get": _corpus_public_get,
    "learning.auto_activation_policy.get": _user_taste_policy_get,
    "learning.auto_activation_policy.set": _user_taste_policy_set,
    "learning.user_taste.list": _user_taste_list,
    "learning.user_taste.get": _user_taste_get,
    "learning.user_taste.pause": _user_taste_pause,
    "learning.user_taste.withdraw": _user_taste_withdraw,
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
        operation_args = req["args"]
        if isinstance(op, str) and op.startswith("corpus."):
            if _CORPUS_HOST_STORAGE_ARGS.intersection(operation_args):
                errors.append("Corpus storage roots are host-owned")
            if req.get("surface") == "hosted_web" and _contains_path_argument(operation_args):
                errors.append("hosted_web cannot access local filesystem paths")
        if op in {
            "corpus.public.preview", "corpus.public.validate", "corpus.public.release",
            "corpus.public.list", "corpus.public.get",
        } and "analysis_protocol_id" in operation_args:
            if operation_args.get("analysis_protocol_id") not in {
                _CORPUS_LEGACY_PROTOCOL, _CORPUS_STYLE_PROTOCOL,
            }:
                errors.append("analysis_protocol_id is not a registered Corpus protocol")
        if op == "corpus.selection.propose":
            limit = operation_args.get("limit", 120)
            if type(limit) is not int or limit != 120:
                errors.append("limit must be exactly 120")
            collection_id = operation_args.get("collection_id")
            study_id = operation_args.get("study_id")
            collection_supplied = isinstance(collection_id, str) and bool(collection_id.strip())
            study_supplied = isinstance(study_id, str) and bool(study_id.strip())
            if (("collection_id" in operation_args and not collection_supplied)
                    or ("study_id" in operation_args and not study_supplied)):
                errors.append("selection identity must be a non-empty string")
            if collection_supplied == study_supplied:
                errors.append("provide exactly one of collection_id or study_id")
        if op in {"corpus.selection.propose", "corpus.selection.refresh", "corpus.selection.confirm"}:
            if operation_args.get("profile") not in _CORPUS_PROFILES:
                errors.append("profile must be general or adult_explicit")
        if op == "corpus.selection.refresh":
            expected = operation_args.get("expected_proposal_hash")
            if not isinstance(expected, str) or not _FINGERPRINT_RE.fullmatch(expected):
                errors.append("expected_proposal_hash must be a sha256 fingerprint")
        if op == "corpus.selection.confirm":
            work_ids = operation_args.get("work_ids")
            if (not isinstance(work_ids, list) or len(work_ids) != 120
                    or any(not isinstance(value, str) or not value.strip() for value in work_ids)
                    or len(set(work_ids)) != len(work_ids)):
                errors.append("work_ids must contain exactly 120 unique non-empty identifiers")
            proposal = operation_args.get("proposal_fingerprint")
            if not isinstance(proposal, str) or not _FINGERPRINT_RE.fullmatch(proposal):
                errors.append("proposal_fingerprint must be a sha256 fingerprint")
        if op == "corpus.public.validate":
            has_bundle = "bundle" in operation_args
            has_fingerprint = "preview_fingerprint" in operation_args
            if has_bundle == has_fingerprint:
                errors.append("provide exactly one of bundle or preview_fingerprint")
            elif has_bundle and not isinstance(operation_args.get("bundle"), dict):
                errors.append("bundle must be an object")
            elif has_fingerprint and (
                not isinstance(operation_args.get("preview_fingerprint"), str)
                or not _FINGERPRINT_RE.fullmatch(operation_args["preview_fingerprint"])
            ):
                errors.append("preview_fingerprint must be a sha256 fingerprint")
        if op == "corpus.public.release":
            expected = operation_args.get("expected_preview_fingerprint")
            if not isinstance(expected, str) or not _FINGERPRINT_RE.fullmatch(expected):
                errors.append("expected_preview_fingerprint must be a sha256 fingerprint")
        if op == "learning.auto_activation_policy.set" and not isinstance(operation_args.get("payload"), dict):
            errors.append("payload must be an object")
        if op in {"learning.user_taste.pause", "learning.user_taste.withdraw"}:
            version = operation_args.get("expected_version")
            if type(version) is not int or version < 1:
                errors.append("expected_version must be a positive integer")
    return errors


def _public_error(code: Any, fallback: str) -> dict[str, Any]:
    """Return the entire public failure body without exception-derived prose."""
    stable = code if isinstance(code, str) and _PUBLIC_ERROR_CODE_RE.fullmatch(code) else fallback
    return {"code": stable, "mutation_performed": False}


def invoke(req: dict[str, Any]) -> dict[str, Any]:
    errors = validate_request(req)
    if errors:
        return _protocol.result(req, "invalid", error={"code": "invalid_request", "messages": errors, "mutation_performed": False})
    try:
        return _protocol.result(req, "ok", data=DISPATCH[req["operation"]](req["args"], req["surface"]))
    except (BridgeError, OperationError, ProductionRunError, WorkflowError, RouteError, ModelRuntimeError, ConflictError, IntegrityError, FileNotFoundError, FileExistsError, ValueError, KeyError) as exc:
        return _protocol.result(req, "failed", error=_public_error(getattr(exc, "code", None), "bridge_operation_failed"))
    except Exception:
        return _protocol.result(req, "failed", error=_public_error(None, "bridge_internal_error"))


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
