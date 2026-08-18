#!/usr/bin/env python3
"""Quillframe typed host-capability contract.

The framework may route work only to capabilities that are explicitly declared
or locally provable. This module never probes remote services, never reads
credentials, and never treats a provider name as proof of tool availability.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "quillframe_host_capabilities_v1"
KNOWN = {
    "filesystem_read", "filesystem_write", "subprocess", "git_cli", "github_cli",
    "codex_cli", "claude_cli", "web_search", "github_search", "user_files",
    "file_library", "mcp_client", "mcp_server", "provider_api", "semantic_model",
    "peer_chat_relay", "human_reviewer", "network_http",
}
PERMISSIONS = {"none", "read", "write", "execute", "review"}
USAGE_CLASSES = {"none", "local", "subscription", "api_metered", "human", "unknown"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dump(v: Any) -> None:
    print(json.dumps(v, ensure_ascii=False, indent=2))


def capability(*, available: bool, source: str, permission: str = "none",
               usage_class: str = "none", user_interaction: bool = False,
               model_execution: bool = False, detail: str | None = None) -> dict[str, Any]:
    if permission not in PERMISSIONS:
        raise ValueError("invalid permission")
    if usage_class not in USAGE_CLASSES:
        raise ValueError("invalid usage_class")
    return {
        "available": bool(available),
        "source": source,
        "permission": permission,
        "usage_class": usage_class,
        "user_interaction": bool(user_interaction),
        "model_execution": bool(model_execution),
        "detail": detail,
    }


def probe_local() -> dict[str, Any]:
    """Probe facts that are safe and locally observable only."""
    cwd = Path.cwd()
    caps = {
        "filesystem_read": capability(available=os.access(cwd, os.R_OK), source="local_probe", permission="read", usage_class="local"),
        "filesystem_write": capability(available=os.access(cwd, os.W_OK), source="local_probe", permission="write", usage_class="local"),
        "subprocess": capability(available=True, source="python_runtime", permission="execute", usage_class="local"),
        "git_cli": capability(available=shutil.which("git") is not None, source="path_probe", permission="execute", usage_class="local", detail=shutil.which("git")),
        "github_cli": capability(available=shutil.which("gh") is not None, source="path_probe", permission="execute", usage_class="local", detail=shutil.which("gh")),
        "codex_cli": capability(available=shutil.which("codex") is not None, source="path_probe", permission="execute", usage_class="subscription", model_execution=True, detail=shutil.which("codex")),
        "claude_cli": capability(available=shutil.which("claude") is not None, source="path_probe", permission="execute", usage_class="subscription", model_execution=True, detail=shutil.which("claude")),
    }
    # Network socket support is not proof that a specific remote service is authorized.
    caps["network_http"] = capability(
        available=hasattr(socket, "create_connection"), source="python_runtime",
        permission="execute", usage_class="unknown",
        detail="transport primitive only; does not prove remote authorization",
    )
    for name in sorted(KNOWN - set(caps)):
        caps[name] = capability(available=False, source="not_locally_proven")
    return {
        "schema": SCHEMA,
        "manifest_id": "HC-" + uuid.uuid4().hex,
        "host": {"runtime_class": "local_process", "identity": sys.platform},
        "capabilities": caps,
        "generated_at": now_iso(),
        "secrets_embedded": False,
    }


def validate_manifest(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    caps = value.get("capabilities")
    if not isinstance(caps, dict):
        return errors + ["capabilities must be object"]
    for name, item in caps.items():
        if not isinstance(name, str) or not name:
            errors.append("capability name must be non-empty string"); continue
        if not isinstance(item, dict):
            errors.append(f"capability {name} must be object"); continue
        if not isinstance(item.get("available"), bool):
            errors.append(f"capability {name}.available must be boolean")
        if not str(item.get("source") or "").strip():
            errors.append(f"capability {name}.source required")
        if item.get("permission", "none") not in PERMISSIONS:
            errors.append(f"capability {name}.permission invalid")
        if item.get("usage_class", "unknown") not in USAGE_CLASSES:
            errors.append(f"capability {name}.usage_class invalid")
        if not isinstance(item.get("user_interaction", False), bool):
            errors.append(f"capability {name}.user_interaction must be boolean")
        if not isinstance(item.get("model_execution", False), bool):
            errors.append(f"capability {name}.model_execution must be boolean")
        # Capability manifests are metadata, never a secret transport.
        forbidden = {"api_key", "token", "password", "secret", "authorization"}
        if forbidden.intersection(k.lower() for k in item):
            errors.append(f"capability {name} embeds forbidden credential field")
    if value.get("secrets_embedded") not in {False, None}:
        errors.append("secrets_embedded must be false")
    return errors


def normalize(value: dict[str, Any]) -> dict[str, Any]:
    """Normalize a host-supplied declaration without inventing missing capability."""
    if value.get("schema") not in {None, SCHEMA}:
        raise ValueError("unsupported capability schema")
    supplied = value.get("capabilities", {})
    if not isinstance(supplied, dict):
        raise ValueError("capabilities must be object")
    caps: dict[str, Any] = {}
    for name in sorted(KNOWN | set(supplied)):
        raw = supplied.get(name)
        if raw is None:
            caps[name] = capability(available=False, source="undeclared")
            continue
        if isinstance(raw, bool):
            caps[name] = capability(available=raw, source="host_declared", permission="execute" if raw else "none", usage_class="unknown")
            continue
        if not isinstance(raw, dict):
            raise ValueError(f"capability {name} must be boolean or object")
        caps[name] = capability(
            available=bool(raw.get("available", False)),
            source=str(raw.get("source") or "host_declared"),
            permission=str(raw.get("permission") or "none"),
            usage_class=str(raw.get("usage_class") or "unknown"),
            user_interaction=bool(raw.get("user_interaction", False)),
            model_execution=bool(raw.get("model_execution", False)),
            detail=str(raw["detail"]) if raw.get("detail") is not None else None,
        )
    out = {
        "schema": SCHEMA,
        "manifest_id": str(value.get("manifest_id") or "HC-" + uuid.uuid4().hex),
        "host": value.get("host", {"runtime_class": "declared_host"}),
        "capabilities": caps,
        "generated_at": str(value.get("generated_at") or now_iso()),
        "secrets_embedded": False,
    }
    errors = validate_manifest(out)
    if errors:
        raise ValueError("; ".join(errors))
    return out


def resolve(manifest: dict[str, Any], requirements: list[str], *, allow_user_interaction: bool = True,
            allow_model_execution: bool = True, forbidden_usage: set[str] | None = None) -> dict[str, Any]:
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("invalid host capability manifest: " + "; ".join(errors))
    forbidden_usage = forbidden_usage or set()
    selected: list[dict[str, Any]] = []
    missing: list[str] = []
    rejected: list[dict[str, str]] = []
    for req in requirements:
        item = manifest["capabilities"].get(req)
        if not item or not item.get("available"):
            missing.append(req); continue
        if item.get("user_interaction") and not allow_user_interaction:
            rejected.append({"capability": req, "reason": "user_interaction_forbidden"}); continue
        if item.get("model_execution") and not allow_model_execution:
            rejected.append({"capability": req, "reason": "model_execution_forbidden"}); continue
        if item.get("usage_class") in forbidden_usage:
            rejected.append({"capability": req, "reason": "usage_class_forbidden"}); continue
        selected.append({"capability": req, **item})
    return {
        "schema": "quillframe_capability_resolution_v1",
        "manifest_id": manifest.get("manifest_id"),
        "requirements": requirements,
        "satisfied": not missing and not rejected,
        "selected": selected,
        "missing": missing,
        "rejected": rejected,
        "authority_granted": False,
    }


def self_test() -> dict[str, Any]:
    declared = normalize({
        "host": {"runtime_class": "test_chat"},
        "capabilities": {
            "web_search": {"available": True, "source": "fixture", "permission": "read", "usage_class": "subscription"},
            "peer_chat_relay": {"available": True, "source": "fixture", "permission": "review", "usage_class": "subscription", "user_interaction": True, "model_execution": True},
        },
    })
    web = resolve(declared, ["web_search"])
    undeclared = resolve(declared, ["github_search"])
    no_model = resolve(declared, ["peer_chat_relay"], allow_model_execution=False)
    no_user = resolve(declared, ["peer_chat_relay"], allow_user_interaction=False)
    ok = (
        web["satisfied"] is True
        and undeclared["satisfied"] is False and undeclared["missing"] == ["github_search"]
        and no_model["satisfied"] is False and no_model["rejected"][0]["reason"] == "model_execution_forbidden"
        and no_user["satisfied"] is False and no_user["rejected"][0]["reason"] == "user_interaction_forbidden"
        and declared["secrets_embedded"] is False
    )
    return {
        "runtime_capabilities_contract": "PASS" if ok else "FAIL",
        "undeclared_capability_never_selected": undeclared["satisfied"] is False,
        "model_usage_constraint_enforced": no_model["satisfied"] is False,
        "user_interaction_constraint_enforced": no_user["satisfied"] is False,
        "secrets_embedded": False,
    }


def load_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe host capability contract")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("probe-local"); pr.add_argument("--output")
    no = sub.add_parser("normalize"); no.add_argument("--input", required=True); no.add_argument("--output")
    rs = sub.add_parser("resolve"); rs.add_argument("--manifest", required=True); rs.add_argument("--require", action="append", default=[]); rs.add_argument("--no-user-interaction", action="store_true"); rs.add_argument("--no-model", action="store_true"); rs.add_argument("--forbid-usage", action="append", default=[])
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test(); dump(result); return 0 if result["runtime_capabilities_contract"] == "PASS" else 1
    if args.cmd == "probe-local":
        result = probe_local()
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output: Path(args.output).write_text(text, encoding="utf-8")
        else: print(text, end="")
        return 0
    if args.cmd == "normalize":
        result = normalize(load_json(args.input)); text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output: Path(args.output).write_text(text, encoding="utf-8")
        else: print(text, end="")
        return 0
    result = resolve(
        load_json(args.manifest), args.require,
        allow_user_interaction=not args.no_user_interaction,
        allow_model_execution=not args.no_model,
        forbidden_usage=set(args.forbid_usage),
    )
    dump(result); return 0 if result["satisfied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
