#!/usr/bin/env python3
"""Portable read-only product bridge for NovelForge Studio.

This module exposes a small versioned request/result envelope over public
NovelForge CLI contracts. It is a product adapter only: no Canon, Settlement,
Framework-write, semantic, or workflow authority is created here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLI = ROOT / "novelforge.py"
CONTRACT_PATH = HERE / "host_bridge_contract.json"

REQUEST_SCHEMA = "novelforge_studio_host_bridge_request_v1"
RESULT_SCHEMA = "novelforge_studio_host_bridge_result_v1"
DESCRIPTION_SCHEMA = "novelforge_studio_host_bridge_description_v1"
CONTRACT_SCHEMA = "novelforge_studio_host_bridge_contract_v1"

try:
    from project_hub_projection import build_projection
except ImportError as exc:  # pragma: no cover - startup guard
    raise SystemExit(f"cannot load Studio Project Hub projection: {exc}")

ABS_WIN_RE = re.compile(r"^[A-Za-z]:[\\/]")
REDACT_KEYS = {"project_root", "framework_root", "absolute", "db", "database_path"}


class BridgeError(Exception):
    def __init__(self, code: str, message: str, *, detail: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BridgeError("invalid_json", "JSON root must be an object")
    return value


def load_contract() -> dict[str, Any]:
    value = load_json(CONTRACT_PATH)
    if value.get("schema") != CONTRACT_SCHEMA:
        raise BridgeError("invalid_bridge_contract", f"expected {CONTRACT_SCHEMA}")
    if value.get("authority") is not False:
        raise BridgeError("invalid_bridge_contract", "bridge contract authority must be false")
    return value


def _looks_absolute_path(value: str) -> bool:
    if value.startswith(("http://", "https://", "urn:", "sha256:")):
        return False
    return value.startswith("/") or bool(ABS_WIN_RE.match(value))


def sanitize(value: Any) -> Any:
    """Default-deny host-private path material from external result envelopes."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in REDACT_KEYS:
                continue
            out[str(key)] = sanitize(item)
        return out
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str) and _looks_absolute_path(value):
        return "<host-path-redacted>"
    return value


def _root() -> Path:
    if not CLI.exists():
        raise BridgeError("framework_unavailable", "novelforge.py not found beside Studio")
    return ROOT


def _run_cli(args: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    root = _root()
    proc = subprocess.run(
        [sys.executable, str(root / "novelforge.py"), *args],
        cwd=str(cwd or root),
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise BridgeError(
            "core_cli_invalid_output",
            "NovelForge CLI did not return a JSON object",
            detail={"returncode": proc.returncode, "stderr": proc.stderr[-2000:]},
        )
    if not isinstance(value, dict):
        raise BridgeError("core_cli_invalid_output", "NovelForge CLI JSON root must be an object")
    if proc.returncode != 0:
        error_code = value.get("code") if isinstance(value.get("code"), str) else "core_cli_failed"
        raise BridgeError(
            error_code,
            value.get("message") if isinstance(value.get("message"), str) else "NovelForge CLI query failed",
            detail={"returncode": proc.returncode, "result": sanitize(value)},
        )
    return value


def _project_root(args: dict[str, Any]) -> Path:
    raw = args.get("project_root")
    if not isinstance(raw, str) or not raw.strip():
        raise BridgeError("invalid_args", "project_root is required")
    root = Path(raw).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise BridgeError("project_unavailable", "project_root must be an existing directory")
    return root


def _scoped_path(project_root: Path, raw: Any, field: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise BridgeError("invalid_args", f"{field} is required")
    candidate = Path(raw)
    if candidate.is_absolute() or ABS_WIN_RE.match(raw):
        raise BridgeError("path_scope_violation", f"{field} must be project-relative")
    resolved = (project_root / candidate).resolve()
    if resolved != project_root and project_root not in resolved.parents:
        raise BridgeError("path_scope_violation", f"{field} escapes project_root")
    if not resolved.exists() or not resolved.is_file():
        raise BridgeError("path_unavailable", f"{field} does not resolve to an existing file")
    return resolved


def _safe_doctor(_: dict[str, Any], __: str) -> dict[str, Any]:
    return sanitize(_run_cli(["doctor"]))


def _project_inspect(args: dict[str, Any], surface: str) -> dict[str, Any]:
    project_root = _project_root(args)
    validation = _run_cli(["adapter", "validate", str(project_root)], cwd=project_root)
    if validation.get("valid") is not True or not isinstance(validation.get("resolution"), dict):
        raise BridgeError("project_invalid", "Project Adapter validation did not produce a valid resolution")
    projection = build_projection(validation["resolution"], surface)
    return sanitize({"valid": True, "errors": validation.get("errors", []), "project": projection})


def _capabilities_inspect(args: dict[str, Any], _: str) -> dict[str, Any]:
    cwd = _project_root(args) if args.get("project_root") is not None else _root()
    return sanitize(_run_cli(["capabilities", "probe-local"], cwd=cwd))


def _context_inspect(args: dict[str, Any], _: str) -> dict[str, Any]:
    project_root = _project_root(args)
    manifest = _scoped_path(project_root, args.get("manifest"), "manifest")
    argv = ["context-inspect", "inspect", "--manifest", str(manifest)]
    if args.get("overlay") is not None:
        overlay = _scoped_path(project_root, args.get("overlay"), "overlay")
        argv += ["--overlay", str(overlay)]
    stage = args.get("stage")
    if stage is not None:
        if stage not in {"writer_pre_draft", "post_draft_critic", "independent_reviewer", "never"}:
            raise BridgeError("invalid_args", "unsupported Context Inspector stage")
        argv += ["--stage", stage]
    return sanitize(_run_cli(argv, cwd=project_root))


def _semantic_catalog(_: dict[str, Any], __: str) -> dict[str, Any]:
    return sanitize(_run_cli(["semantic", "catalog"]))


def _runtime_args(args: dict[str, Any], *query_args: str) -> tuple[Path, list[str]]:
    project_root = _project_root(args)
    runtime_db = project_root / ".novelforge" / "runtime.db"
    return project_root, ["runtime-query", "--db", str(runtime_db), *query_args]


def _runtime_sessions_list(args: dict[str, Any], _: str) -> dict[str, Any]:
    project_root, argv = _runtime_args(args, "session-list")
    resource_id = args.get("resource_id")
    if resource_id is not None:
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise BridgeError("invalid_args", "resource_id must be a non-empty string")
        argv += ["--resource-id", resource_id]
    return sanitize(_run_cli(argv, cwd=project_root))


def _runtime_session_get(args: dict[str, Any], _: str) -> dict[str, Any]:
    session_id = args.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise BridgeError("invalid_args", "session_id is required")
    project_root, argv = _runtime_args(args, "session-get", "--session-id", session_id)
    return sanitize(_run_cli(argv, cwd=project_root))


def _runtime_events_list(args: dict[str, Any], _: str) -> dict[str, Any]:
    project_root, argv = _runtime_args(args, "event-list")
    for field, flag in (("session_id", "--session-id"), ("run_id", "--run-id")):
        value = args.get(field)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise BridgeError("invalid_args", f"{field} must be a non-empty string")
            argv += [flag, value]
    return sanitize(_run_cli(argv, cwd=project_root))


def _runtime_handoff_inspect(args: dict[str, Any], _: str) -> dict[str, Any]:
    handoff_id = args.get("handoff_id")
    if not isinstance(handoff_id, str) or not handoff_id.strip():
        raise BridgeError("invalid_args", "handoff_id is required")
    project_root, argv = _runtime_args(args, "handoff-get", "--handoff-id", handoff_id)
    return sanitize(_run_cli(argv, cwd=project_root))


def _run_receipt_get(args: dict[str, Any], _: str) -> dict[str, Any]:
    selectors: list[tuple[str, str]] = []
    for field, flag in (("receipt_id", "--receipt-id"), ("run_id", "--run-id"), ("session_id", "--session-id")):
        value = args.get(field)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise BridgeError("invalid_args", f"{field} must be a non-empty string")
            selectors.append((flag, value))
    if not selectors:
        raise BridgeError("invalid_args", "receipt_id, run_id, or session_id is required")
    project_root, argv = _runtime_args(args, "receipt-get")
    for flag, value in selectors:
        argv += [flag, value]
    return sanitize(_run_cli(argv, cwd=project_root))


DISPATCH = {
    "bridge.describe": lambda args, surface: description(surface=surface),
    "framework.doctor": _safe_doctor,
    "project.inspect": _project_inspect,
    "capabilities.inspect": _capabilities_inspect,
    "context.inspect": _context_inspect,
    "semantic.catalog": _semantic_catalog,
    "runtime.sessions.list": _runtime_sessions_list,
    "runtime.session.get": _runtime_session_get,
    "runtime.events.list": _runtime_events_list,
    "runtime.handoff.inspect": _runtime_handoff_inspect,
    "run.receipt.get": _run_receipt_get,
}


def description(*, surface: str | None = None) -> dict[str, Any]:
    contract = load_contract()
    return {
        "schema": DESCRIPTION_SCHEMA,
        "contract_schema": contract["schema"],
        "request_schema": REQUEST_SCHEMA,
        "result_schema": RESULT_SCHEMA,
        "product_model": "one_product_many_hosts",
        "surface": surface,
        "supported_operations": sorted(contract["operations"]["supported"]),
        "deferred_operations": contract["operations"]["deferred"],
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
        "direct_core_store_access": False,
    }


def validate_request(request: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = {"schema", "request_id", "operation", "surface", "args", "authority"}
    extra = sorted(set(request) - allowed)
    if extra:
        errors.append("unexpected fields: " + ", ".join(extra))
    if request.get("schema") != REQUEST_SCHEMA:
        errors.append(f"schema must be {REQUEST_SCHEMA}")
    if not isinstance(request.get("request_id"), str) or not request["request_id"].strip():
        errors.append("request_id must be non-empty string")
    if not isinstance(request.get("operation"), str) or not request["operation"].strip():
        errors.append("operation must be non-empty string")
    contract = load_contract()
    if request.get("surface") not in contract.get("surfaces", []):
        errors.append("surface is not supported")
    if not isinstance(request.get("args"), dict):
        errors.append("args must be object")
    if request.get("authority") is not False:
        errors.append("request authority must be false")
    return errors


def _base_result(request: dict[str, Any], *, status: str, data: Any = None, error: Any = None) -> dict[str, Any]:
    out = {
        "schema": RESULT_SCHEMA,
        "request_id": request.get("request_id"),
        "operation": request.get("operation"),
        "surface": request.get("surface"),
        "status": status,
        "request_fingerprint": fingerprint(request),
        "data": sanitize(data),
        "error": sanitize(error),
        "authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    out["result_fingerprint"] = fingerprint(out)
    return out


def invoke(request: dict[str, Any]) -> dict[str, Any]:
    errors = validate_request(request)
    if errors:
        return _base_result(request, status="invalid", error={"code": "invalid_request", "messages": errors})

    operation = request["operation"]
    contract = load_contract()
    deferred = contract["operations"]["deferred"]
    if operation in deferred:
        info = deferred[operation]
        return _base_result(
            request,
            status="unsupported",
            error={"code": "operation_deferred", "reason": info.get("reason"), "dependency": info.get("dependency"), "mutation_performed": False},
        )
    if operation not in contract["operations"]["supported"] or operation not in DISPATCH:
        return _base_result(request, status="invalid", error={"code": "unknown_operation", "mutation_performed": False})

    required_args = contract["operations"]["supported"][operation].get("required_args", [])
    missing_args = [name for name in required_args if request["args"].get(name) in {None, ""}]
    if missing_args:
        return _base_result(request, status="invalid", error={"code": "missing_args", "fields": missing_args, "mutation_performed": False})

    try:
        data = DISPATCH[operation](request["args"], request["surface"])
        return _base_result(request, status="ok", data=data)
    except BridgeError as exc:
        return _base_result(request, status="failed", error={"code": exc.code, "message": exc.message, "detail": exc.detail, "mutation_performed": False})
    except Exception as exc:
        return _base_result(request, status="failed", error={"code": "bridge_internal_error", "message": f"{type(exc).__name__}: {exc}", "mutation_performed": False})


def _request(request_id: str, operation: str, args: dict[str, Any] | None = None, *, surface: str = "agent_package") -> dict[str, Any]:
    return {"schema": REQUEST_SCHEMA, "request_id": request_id, "operation": operation, "surface": surface, "args": args or {}, "authority": False}


def _run_setup(argv: list[str], *, cwd: Path) -> bool:
    proc = subprocess.run([sys.executable, str(CLI), *argv], cwd=str(cwd), text=True, capture_output=True, check=False)
    return proc.returncode == 0


def self_test() -> dict[str, Any]:
    contract = load_contract()
    desc_req = _request("REQ-DESC", "bridge.describe")
    desc_a = invoke(desc_req)
    desc_b = invoke(desc_req)
    desc_without_fp = {k: v for k, v in desc_a.items() if k != "result_fingerprint"}
    deterministic_envelope = desc_a == desc_b and desc_a["request_fingerprint"] == fingerprint(desc_req) and desc_a["result_fingerprint"] == fingerprint(desc_without_fp)

    unknown = invoke(_request("REQ-UNKNOWN", "project.delete"))
    deferred_resume = invoke(_request("REQ-RESUME", "session.resume"))
    deferred_write = invoke(_request("REQ-WRITE", "command.invoke"))
    wrong_authority = _request("REQ-AUTH", "bridge.describe")
    wrong_authority["authority"] = True
    authority_rejected = invoke(wrong_authority)
    doctor = invoke(_request("REQ-DOCTOR", "framework.doctor"))
    capabilities = invoke(_request("REQ-CAP", "capabilities.inspect"))

    temp_root = Path(tempfile.mkdtemp(prefix="novelforge-host-bridge-"))
    project_ready = project_safe = context_safe = runtime_safe = False
    runtime_queries_ok = False
    try:
        setup = subprocess.run([sys.executable, str(ROOT / "project_adapter.py"), "self-test", "--tmp", str(temp_root)], cwd=str(ROOT), text=True, capture_output=True, check=False)
        project_ready = setup.returncode == 0
        project = invoke(_request("REQ-PROJECT", "project.inspect", {"project_root": str(temp_root)}))
        serialized_project = canonical(project)
        project_safe = project["status"] == "ok" and str(temp_root) not in serialized_project and "<host-path-redacted>" not in canonical(project["data"].get("project", {})) and project["data"]["project"]["authority"] is False

        context_path = temp_root / "context-manifest.json"
        context_path.write_text(json.dumps({"manifest_id": "CTX-BRIDGE-SELF", "items": [{"id": "CTX-A", "class": "summary", "source": str(temp_root / "private-source.txt"), "authority": "derived", "derived": True, "stages": ["writer_pre_draft"], "priority": 1}]}), encoding="utf-8")
        context = invoke(_request("REQ-CONTEXT", "context.inspect", {"project_root": str(temp_root), "manifest": "context-manifest.json", "stage": "writer_pre_draft"}))
        context_safe = context["status"] == "ok" and str(temp_root) not in canonical(context) and context["data"]["authority"] is False

        runtime_db = temp_root / ".novelforge" / "runtime.db"
        runtime_db.parent.mkdir(parents=True, exist_ok=True)
        runtime_init = _run_setup(["runtime", "--db", str(runtime_db), "init"], cwd=temp_root)

        session_path = temp_root / "session.json"
        session_path.write_text(json.dumps({
            "schema": "novelforge_agent_session_v1",
            "resource_id": "BOOK-BRIDGE",
            "project_id": "BOOK-BRIDGE",
            "session_id": "SES-BRIDGE",
            "role": "manager",
            "status": "awaiting_external",
            "transport": "chat_session",
            "backend": "self_test",
            "usage_class": "ordinary_chat",
            "memory_policy": "session",
            "resume_policy": "checkpoint_revalidate",
            "context_policy": {"hidden_gold": "forbidden", "allowed_artifact_refs": [], "allowed_paths": [str(temp_root / "private")], "forbidden_context_classes": []},
            "runs": [{"run_id": "RUN-BRIDGE", "started_at": "2026-01-01T00:00:00+00:00", "ended_at": None, "status": "running", "input_artifact_fingerprints": [], "output_artifact_fingerprints": [], "usage_class": "ordinary_chat"}],
            "checkpoints": [],
            "events": [],
            "provenance": {"runtime": "self_test", "version": "1", "durable_store": "control_plane"},
        }), encoding="utf-8")
        session_put = _run_setup(["runtime", "--db", str(runtime_db), "session-put", "--session", str(session_path), "--expected-version", "0"], cwd=temp_root)

        event_path = temp_root / "event.json"
        event_path.write_text(json.dumps({
            "schema": "novelforge_event_v1",
            "event_id": "EV-BRIDGE",
            "event_type": "semantic.requested",
            "source": {"kind": "self_test", "actor": "host_bridge.py"},
            "resource_id": "BOOK-BRIDGE",
            "session_id": "SES-BRIDGE",
            "run_id": "RUN-BRIDGE",
            "handoff_id": "HO-BRIDGE",
            "authority_scope": "request",
            "idempotency_key": "host-bridge-runtime-self-test",
            "artifact_fingerprints": [],
            "created_at": "2026-01-01T00:00:01+00:00",
            "payload": {"private_path": str(temp_root / "private-event")},
        }), encoding="utf-8")
        event_put = _run_setup(["runtime", "--db", str(runtime_db), "event-ingest", "--event", str(event_path)], cwd=temp_root)

        handoff_path = temp_root / "handoff.json"
        handoff_path.write_text(json.dumps({
            "schema": "novelforge_handoff_v1",
            "handoff_id": "HO-BRIDGE",
            "source_session_id": "SES-BRIDGE",
            "target_session_class": "semantic_reviewer",
            "resource_id": "BOOK-BRIDGE",
            "task_mode": "DRAFT",
            "artifact_refs": [str(temp_root / "private-artifact")],
            "artifact_fingerprints": [],
            "context_policy": {"hidden_gold": "forbidden", "allowed_artifact_refs": []},
            "permissions": {"canon_write": False, "framework_behavior_write": False, "durable_user_taste_write": False, "allowed_result_scope": "observation"},
            "return_contract": {"schema": "semantic_worker_result", "fingerprint_required": True},
        }), encoding="utf-8")
        handoff_put = _run_setup(["runtime", "--db", str(runtime_db), "handoff-submit", "--handoff", str(handoff_path)], cwd=temp_root)

        sessions = invoke(_request("REQ-SESSIONS", "runtime.sessions.list", {"project_root": str(temp_root)}))
        session = invoke(_request("REQ-SESSION", "runtime.session.get", {"project_root": str(temp_root), "session_id": "SES-BRIDGE"}))
        events = invoke(_request("REQ-EVENTS", "runtime.events.list", {"project_root": str(temp_root), "session_id": "SES-BRIDGE"}))
        handoff = invoke(_request("REQ-HANDOFF", "runtime.handoff.inspect", {"project_root": str(temp_root), "handoff_id": "HO-BRIDGE"}))
        receipts = invoke(_request("REQ-RECEIPTS", "run.receipt.get", {"project_root": str(temp_root), "run_id": "RUN-BRIDGE"}))
        runtime_results = [sessions, session, events, handoff, receipts]
        runtime_queries_ok = all(item["status"] == "ok" for item in runtime_results)
        runtime_serialized = canonical(runtime_results)
        runtime_safe = runtime_queries_ok and str(temp_root) not in runtime_serialized and all(item["data"]["authority"] is False for item in runtime_results)
        runtime_queries_ok = runtime_queries_ok and runtime_init and session_put and event_put and handoff_put and sessions["data"]["count"] == 1 and events["data"]["count"] == 1 and receipts["data"]["count"] == 0
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    checks = {
        "contract_dispatch_match": set(contract["operations"]["supported"]) == set(DISPATCH),
        "authority_false": contract.get("authority") is False and desc_a.get("authority") is False,
        "deterministic_envelope": deterministic_envelope,
        "unknown_operation_fails_closed": unknown["status"] == "invalid",
        "resume_command_deferred": deferred_resume["status"] == "unsupported",
        "write_command_deferred": deferred_write["status"] == "unsupported",
        "request_authority_rejected": authority_rejected["status"] == "invalid",
        "doctor_query": doctor["status"] == "ok",
        "capability_query": capabilities["status"] == "ok",
        "project_fixture_ready": project_ready,
        "project_projection_safe": project_safe,
        "context_projection_safe": context_safe,
        "runtime_queries_supported": runtime_queries_ok,
        "runtime_projection_safe": runtime_safe,
    }
    return {"studio_host_bridge_contract": "PASS" if all(checks.values()) else "FAIL", "schema": CONTRACT_SCHEMA, "checks": checks, "authority": False, "model_execution": False}


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge Studio portable read-only host bridge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("describe")
    inv = sub.add_parser("invoke")
    inv.add_argument("--request", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "describe":
        dump(description())
        return 0
    if args.command == "self-test":
        result = self_test()
        dump(result)
        return 0 if result["studio_host_bridge_contract"] == "PASS" else 1
    try:
        result = invoke(load_json(Path(args.request)))
    except BridgeError as exc:
        result = _base_result({"request_id": None, "operation": None, "surface": None}, status="invalid", error={"code": exc.code, "message": exc.message, "mutation_performed": False})
    dump(result)
    return 0 if result["status"] == "ok" else (2 if result["status"] in {"invalid", "unsupported"} else 1)


if __name__ == "__main__":
    raise SystemExit(main())
