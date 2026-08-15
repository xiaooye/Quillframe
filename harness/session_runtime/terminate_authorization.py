#!/usr/bin/env python3
"""Validate explicit human authorization for session termination.

Unlike resume, termination has no manager-runtime-policy shortcut. A terminating
command must be explicitly allowed by a user or authorized human and remains
strictly limited to runtime Session/Run state.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import terminate_command

AUTH_SCHEMA = "novelforge_session_terminate_authorization_v1"
VALIDATION_SCHEMA = "novelforge_session_terminate_authorization_validation_v1"
SOURCE_KINDS = {"user", "authorized_human"}
TOP_FIELDS = {
    "schema", "authorization_id", "operation", "command_fingerprint",
    "intent_fingerprint", "decision", "source", "scope", "issued_at", "authority",
}
SOURCE_FIELDS = {"kind", "evidence_ref"}
SCOPE_FIELDS = {"runtime_state_mutation", "model_execution", "project_write", "canon_write", "framework_write", "settlement"}
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ABS_WIN_RE = re.compile(r"^[A-Za-z]:[\\/]")


def dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def timestamp_valid(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def evidence_ref_safe(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 512:
        return False
    return not value.startswith("/") and not bool(ABS_WIN_RE.match(value))


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value))


def shape_errors(authorization: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    extra = sorted(set(authorization) - TOP_FIELDS)
    missing = sorted(TOP_FIELDS - set(authorization))
    if extra: errors.append("unexpected_top_fields:" + ",".join(extra))
    if missing: errors.append("missing_top_fields:" + ",".join(missing))
    if authorization.get("schema") != AUTH_SCHEMA: errors.append("authorization_schema_invalid")
    authorization_id = authorization.get("authorization_id")
    if not isinstance(authorization_id, str) or not authorization_id or len(authorization_id) > 160:
        errors.append("authorization_id_invalid")
    if authorization.get("operation") != "session.terminate": errors.append("operation_invalid")
    if not is_sha(authorization.get("command_fingerprint")): errors.append("command_fingerprint_invalid")
    if not is_sha(authorization.get("intent_fingerprint")): errors.append("intent_fingerprint_invalid")
    if authorization.get("decision") not in {"allow", "deny"}: errors.append("decision_invalid")
    if authorization.get("authority") is not False: errors.append("authorization_authority_must_be_false")
    if not timestamp_valid(authorization.get("issued_at")): errors.append("issued_at_invalid")

    source = authorization.get("source")
    if not isinstance(source, dict):
        errors.append("source_invalid")
    else:
        if set(source) != SOURCE_FIELDS: errors.append("source_fields_invalid")
        if source.get("kind") not in SOURCE_KINDS: errors.append("source_kind_invalid")
        if not evidence_ref_safe(source.get("evidence_ref")): errors.append("source_evidence_ref_invalid")

    scope = authorization.get("scope")
    expected = {
        "runtime_state_mutation": True,
        "model_execution": False,
        "project_write": False,
        "canon_write": False,
        "framework_write": False,
        "settlement": False,
    }
    if not isinstance(scope, dict):
        errors.append("scope_invalid")
    else:
        if set(scope) != SCOPE_FIELDS: errors.append("scope_fields_invalid")
        if any(scope.get(key) is not value for key, value in expected.items()): errors.append("scope_escalation_forbidden")
    return errors


def validate(authorization: dict[str, Any], command: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    errors = shape_errors(authorization)
    checks: dict[str, bool] = {}
    command_validation = terminate_command.validate(command, preflight)
    checks["terminate_command_valid"] = command_validation.get("valid") is True
    if not checks["terminate_command_valid"]: errors.append("terminate_command_candidate_invalid")
    checks["operation_matches_command"] = authorization.get("operation") == command.get("action") == "session.terminate"
    if not checks["operation_matches_command"]: errors.append("authorization_operation_mismatch")
    checks["command_fingerprint_matches"] = authorization.get("command_fingerprint") == command_validation.get("command_fingerprint")
    if not checks["command_fingerprint_matches"]: errors.append("authorization_command_fingerprint_mismatch")
    checks["intent_fingerprint_matches"] = authorization.get("intent_fingerprint") == command_validation.get("intent_fingerprint")
    if not checks["intent_fingerprint_matches"]: errors.append("authorization_intent_fingerprint_mismatch")
    source = authorization.get("source") if isinstance(authorization.get("source"), dict) else {}
    checks["explicit_human_source"] = source.get("kind") in SOURCE_KINDS
    if not checks["explicit_human_source"]: errors.append("terminate_requires_explicit_human_authorization")
    checks["fresh_preflight_required"] = command_validation.get("preflight_revalidation_required_at_execute") is True
    if not checks["fresh_preflight_required"]: errors.append("fresh_preflight_requirement_missing")

    errors = list(dict.fromkeys(errors))
    valid = not errors and all(checks.values())
    granted = valid and authorization.get("decision") == "allow"
    return {
        "schema": VALIDATION_SCHEMA,
        "valid": valid,
        "authorization_granted": granted,
        "decision": authorization.get("decision"),
        "source_kind": source.get("kind"),
        "errors": errors,
        "checks": checks,
        "authorization_fingerprint": terminate_command.fingerprint(authorization),
        "command_fingerprint": command_validation.get("command_fingerprint"),
        "intent_fingerprint": command_validation.get("intent_fingerprint"),
        "executor_may_attempt_revalidation": granted,
        "preflight_revalidation_required_at_execute": True,
        "execution_performed": False,
        "runtime_mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "project_write_authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }


def make_authorization(*, command: dict[str, Any], preflight: dict[str, Any], decision: str, source_kind: str, evidence_ref: str, authorization_id: str, issued_at: str) -> dict[str, Any]:
    command_validation = terminate_command.validate(command, preflight)
    return {
        "schema": AUTH_SCHEMA,
        "authorization_id": authorization_id,
        "operation": "session.terminate",
        "command_fingerprint": command_validation["command_fingerprint"],
        "intent_fingerprint": command_validation["intent_fingerprint"],
        "decision": decision,
        "source": {"kind": source_kind, "evidence_ref": evidence_ref},
        "scope": {
            "runtime_state_mutation": True,
            "model_execution": False,
            "project_write": False,
            "canon_write": False,
            "framework_write": False,
            "settlement": False,
        },
        "issued_at": issued_at,
        "authority": False,
    }


def self_test() -> int:
    checks = {name: True for name in terminate_command.REQUIRED_PREFLIGHT_CHECKS}
    preflight = {
        "schema": "novelforge_session_terminate_preflight_v1",
        "status": "READY",
        "ready": True,
        "checks": checks,
        "blockers": [],
        "unresolved": [],
        "session": {"session_id": "SES-AUTH-STOP", "project_id": "BOOK-STOP", "status": "running", "expected_version": 2, "current_version": 2, "payload_hash": "sha256:" + "a" * 64},
        "run": {"run_id": "RUN-AUTH-STOP", "status": "running", "started_at": "2026-01-01T00:00:00+00:00", "ended_at": None},
        "mutation_performed": False,
        "model_execution": False,
        "authority": False,
        "project_write_authority": False,
        "canon_authority": False,
        "framework_write_authority": False,
        "settlement_authority": False,
    }
    preflight["result_fingerprint"] = terminate_command.fingerprint(preflight)
    command = terminate_command.make_command(preflight=preflight, command_id="CMD-AUTH-STOP")
    allow = make_authorization(command=command, preflight=preflight, decision="allow", source_kind="user", evidence_ref="urn:novelforge:user-action:stop", authorization_id="AUTH-STOP", issued_at="2026-01-01T00:00:00+00:00")
    deny = make_authorization(command=command, preflight=preflight, decision="deny", source_kind="user", evidence_ref="urn:novelforge:user-action:stop", authorization_id="AUTH-STOP-DENY", issued_at="2026-01-01T00:00:00+00:00")
    forged = json.loads(json.dumps(allow)); forged["source"]["kind"] = "manager_runtime_policy"
    allow_result = validate(allow, command, preflight)
    deny_result = validate(deny, command, preflight)
    forged_result = validate(forged, command, preflight)
    schema = load_object(Path(__file__).with_name("terminate_authorization_schema.json"))
    ok = (
        schema.get("$id") == AUTH_SCHEMA
        and allow_result["authorization_granted"] is True
        and deny_result["valid"] is True and deny_result["authorization_granted"] is False
        and forged_result["valid"] is False and "source_kind_invalid" in forged_result["errors"]
        and allow_result["runtime_mutation_performed"] is False and allow_result["authority"] is False
    )
    dump({
        "session_terminate_authorization_contract": "PASS" if ok else "FAIL",
        "explicit_user_allow": allow_result["authorization_granted"],
        "deny_blocks_execution": deny_result["authorization_granted"] is False,
        "manager_policy_forbidden": forged_result["valid"] is False,
        "runtime_mutation_performed": False,
        "model_execution": False,
        "authority": False,
    })
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge session terminate authorization validator")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_p = sub.add_parser("validate")
    validate_p.add_argument("--authorization", required=True)
    validate_p.add_argument("--command", required=True)
    validate_p.add_argument("--preflight", required=True)
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test": return self_test()
    value = validate(load_object(Path(args.authorization)), load_object(Path(args.command)), load_object(Path(args.preflight)))
    dump(value)
    return 0 if value["authorization_granted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
