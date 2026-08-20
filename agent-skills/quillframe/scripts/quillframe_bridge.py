#!/usr/bin/env python3
"""Portable read-only Agent Package client for the Quillframe Host Bridge v11."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED_DESCRIPTION = "quillframe_host_bridge_description_v11"
REQUEST_SCHEMA = "quillframe_host_bridge_request_v11"
BRIDGE_VERSION = "11"
AGENT_SURFACE = "agent_package"
OPERATION_KINDS = {
    "query", "command", "authority_command", "semantic_command", "secret_command",
    "external_query", "external_handoff_prepare", "external_handoff", "external_handoff_result",
}
SURFACES = {"cli", "local_app", "hosted_web", "agent_package"}


def candidate_roots() -> list[Path]:
    roots: list[Path] = []
    env = os.getenv("QUILLFRAME_ROOT")
    if env:
        roots.append(Path(env).expanduser())
    roots.extend([Path.cwd(), *Path.cwd().parents])
    here = Path(__file__).resolve()
    roots.extend([here.parent, *here.parents])
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = root.resolve()
        if str(resolved) not in seen:
            seen.add(str(resolved))
            unique.append(resolved)
    return unique


def find_root() -> Path:
    for root in candidate_roots():
        if (root / "quillframe.py").is_file() and (root / "studio" / "host_bridge.py").is_file():
            return root
    raise SystemExit("Quillframe checkout not found. Run inside the checkout or set QUILLFRAME_ROOT.")


def run_bridge(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    root = find_root()
    return subprocess.run(
        [sys.executable, str(root / "studio" / "host_bridge.py"), *args],
        cwd=str(root),
        text=True,
        capture_output=capture,
        check=False,
    )


def live_description() -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    proc = run_bridge(["describe"], capture=True)
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError:
        value = {}
    return value, proc


def validate_description(description: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if description.get("schema") != EXPECTED_DESCRIPTION:
        errors.append(f"description schema must be {EXPECTED_DESCRIPTION}")
    if description.get("contract_version") != BRIDGE_VERSION:
        errors.append(f"description contract_version must be exactly {BRIDGE_VERSION}")
    for field in ("authority", "canon_authority", "framework_write_authority", "settlement_authority", "direct_core_store_access"):
        if description.get(field) is not False:
            errors.append(f"description {field} must be false")
    contracts = description.get("operation_contracts")
    if not isinstance(contracts, dict):
        errors.append("live description operation_contracts must be an object")
        return errors
    if "bridge.describe" not in contracts:
        errors.append("live description operation_contracts must include bridge.describe")
    for operation, metadata in contracts.items():
        if not isinstance(operation, str) or not operation.strip():
            errors.append("operation metadata keys must be non-empty strings")
            continue
        if not isinstance(metadata, dict):
            errors.append(f"operation metadata must be an object: {operation}")
            continue
        kind = metadata.get("kind")
        if kind not in OPERATION_KINDS:
            errors.append(f"operation metadata kind is invalid: {operation}")
        required = metadata.get("required_args")
        if not isinstance(required, list) or any(not isinstance(arg, str) or not arg.strip() for arg in required):
            errors.append(f"operation metadata required_args must be non-empty strings: {operation}")
        allowed = metadata.get("allowed_surfaces")
        if allowed is not None and (
            not isinstance(allowed, list)
            or any(not isinstance(surface, str) or surface not in SURFACES for surface in allowed)
            or len(set(allowed)) != len(allowed)
        ):
            errors.append(f"operation metadata allowed_surfaces is invalid: {operation}")
    return errors


def preflight(request: dict[str, Any], description: dict[str, Any]) -> list[str]:
    errors: list[str] = validate_description(description)
    if request.get("schema") != REQUEST_SCHEMA:
        errors.append(f"request schema must be {REQUEST_SCHEMA}")
    if request.get("bridge_version") != BRIDGE_VERSION:
        errors.append(f"bridge_version must be exactly {BRIDGE_VERSION}")
    if request.get("surface") != AGENT_SURFACE:
        errors.append("surface must be agent_package")
    if request.get("authority") is not False:
        errors.append("authority must be false")
    if not isinstance(request.get("operation"), str) or not request["operation"].strip():
        errors.append("operation must be a non-empty string")
        return errors
    if not isinstance(request.get("args"), dict):
        errors.append("args must be an object")
        return errors
    contracts = description.get("operation_contracts")
    if not isinstance(contracts, dict):
        return errors
    metadata = contracts.get(request["operation"])
    if not isinstance(metadata, dict):
        errors.append("operation is not advertised by live v11 description")
        return errors
    if metadata.get("kind") != "query":
        errors.append("agent_package only permits query operations")
    allowed = metadata.get("allowed_surfaces")
    if isinstance(allowed, list) and AGENT_SURFACE not in allowed:
        errors.append("operation is not authorized on agent_package")
    required = metadata.get("required_args")
    if not isinstance(required, list) or any(not isinstance(key, str) for key in required):
        errors.append("operation metadata has invalid required_args")
    else:
        missing = [key for key in required if request["args"].get(key) in (None, "")]
        if missing:
            errors.append("missing args: " + ", ".join(missing))
    return errors


def self_test() -> dict[str, Any]:
    description, proc = live_description()
    description_errors = validate_description(description)
    contracts = description.get("operation_contracts") if isinstance(description.get("operation_contracts"), dict) else {}
    malformed = [
        name for name, metadata in contracts.items()
        if not isinstance(metadata, dict) or not isinstance(metadata.get("required_args"), list)
    ]
    non_queries = [
        name for name, metadata in contracts.items()
        if isinstance(metadata, dict) and metadata.get("kind") != "query"
    ]
    query_contracts = [
        name for name, metadata in contracts.items()
        if isinstance(metadata, dict) and metadata.get("kind") == "query"
    ]
    checks = {
        "bridge_found": proc.returncode == 0,
        "description_schema": description.get("schema") == EXPECTED_DESCRIPTION,
        "contract_version": description.get("contract_version") == BRIDGE_VERSION,
        "authority_false": description.get("authority") is False,
        "operation_metadata_complete": not malformed,
        "description_contract_valid": not description_errors,
        "agent_package_query_only": all(
            isinstance(contracts[name], dict)
            and contracts[name].get("kind") == "query"
            for name in query_contracts
        ),
        "query_surface_present": "bridge.describe" in query_contracts and "project.list" in query_contracts,
        "non_query_operations_advertised_for_host_validation": bool(non_queries),
    }
    return {
        "quillframe_agent_skill_contract": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "bridge_version": BRIDGE_VERSION,
        "surface": AGENT_SURFACE,
        "runtime_mutation_allowed": False,
        "authority": False,
        "model_execution": False,
        "query_operation_count": len(query_contracts),
        "non_query_operation_count": len(non_queries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Quillframe read-only Agent Package bridge v11 client")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("describe")
    inv = sub.add_parser("invoke")
    inv.add_argument("--request", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        report = self_test()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["quillframe_agent_skill_contract"] == "PASS" else 1
    if args.command == "describe":
        proc = run_bridge(["describe"])
        return proc.returncode

    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    description, proc = live_description()
    if proc.returncode != 0:
        print("agent-package preflight could not read live Host Bridge v11 description", file=sys.stderr)
        return 2
    errors = preflight(request, description)
    if errors:
        print("agent-package preflight rejected request: " + "; ".join(errors), file=sys.stderr)
        return 2
    result = run_bridge(["invoke", "--request", args.request])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
